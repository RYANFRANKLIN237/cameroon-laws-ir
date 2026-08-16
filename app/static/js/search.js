function loadAppLanguages() {
    const el = document.getElementById('app-languages');
    if (!el) return [];
    try {
        return JSON.parse(el.textContent);
    } catch {
        return [];
    }
}

function searchApp() {
    return {
        // ── State ──────────────────────────────────────────
        query: '',
        lastQuery: '',
        results: [],
        hasSearched: false,
        isLoading: false,
        searchTime: '0.000',
        translatedIds: new Set(),

        loaded: false,

        // Language picker
        languages: loadAppLanguages(),
        showLangPicker: false,
        langSearch: '',
        selectedLang: { code: 'EN', name: 'English', flag: '🇬🇧', country: 'GB' },

        suggestions: [
            { label: 'Constitution', color: 'bg-[#E8F5E9] text-[#2E7D32] hover:bg-[#C8E6C9]', value: 'constitution' },
            { label: "Droits de l'Homme", color: 'bg-[#FFEBEE] text-[#C62828] hover:bg-[#FFCDD2]', value: 'droits' },
            { label: 'Judicial System', color: 'bg-[#FFFDE7] text-[#F9A825] hover:bg-[#FFF9C4]', value: 'judiciary' },
        ],

        ...createSidebarState(),

        get filteredLanguages() {
            const q = this.langSearch.trim().toLowerCase();
            if (!q) return this.languages;
            return this.languages.filter(
                (l) => l.name.toLowerCase().includes(q) || l.code.toLowerCase().includes(q)
            );
        },

        // ── Init ───────────────────────────────────────────
        init() {
            const english = this.languages.find((l) => l.code === 'EN');
            if (english) this.selectedLang = english;

            lucide.createIcons();
            setTimeout(() => { this.loaded = true; }, 100);

            this.$watch('showLangPicker', (open) => {
                if (open) {
                    this.$nextTick(() => {
                        lucide.createIcons();
                        this.$refs.langSearchInput?.focus();
                    });
                }
            });

            this.initSidebar();
        },

        selectLanguage(lang) {
            this.selectedLang = lang;
            this.showLangPicker = false;
            this.langSearch = '';

            this.translatedIds = new Set();
            this.results.forEach((r) => {
                r.translation = null;
                r.translationTarget = null;
            });
        },

        truncateSource(source) {
            if (!source) return '';
            if (source.length <= 75) return source;
            return source.substring(0, 75) + '...';
        },

        // ── Search ─────────────────────────────────────────
        async handleSearch() {
            if (!this.query.trim()) return;

            this.isLoading = true;
            this.hasSearched = true;
            this.lastQuery = this.query;
            this.translatedIds = new Set();
            this.$nextTick(() => lucide.createIcons());

            const startTime = performance.now();

            try {
                const response = await fetch(`/api/search?q=${encodeURIComponent(this.query)}`);
                const data = await response.json();

                const endTime = performance.now();
                this.searchTime = ((endTime - startTime) / 1000).toFixed(3);

                this.results = data.results;

            } catch (err) {
                console.error('Search failed:', err);
                this.results = [];
            } finally {
                this.isLoading = false;
                this.$nextTick(() => lucide.createIcons());
            }
        },

        quickSearch(value) {
            this.query = value;
            this.handleSearch();
        },

        highlightText(text, highlight) {
            if (!highlight || highlight.length < 2) return text;

            const escaped = highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escaped})`, 'gi');

            return text.replace(regex, '<mark class="bg-yellow-300 px-1 rounded">$1</mark>');
        },

        async toggleTranslation(result) {
            const updated = new Set(this.translatedIds);

            if (updated.has(result.id)) {
                updated.delete(result.id);
                this.translatedIds = updated;
                return;
            }

            if (result.translation) {
                updated.add(result.id);
                this.translatedIds = updated;
                return;
            }

            try {
                result.isTranslating = true;

                let target = this.selectedLang.code.toLowerCase();
                if (target === result.language) {
                    target = result.language === 'en' ? 'fr' : 'en';
                }

                const res = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: result.content.slice(0, 1000),
                        source: result.language,
                        target: target
                    })
                });

                const data = await res.json();

                if (data.translatedText) {
                    result.translation = data.translatedText;
                    result.translationTarget = target;

                    updated.add(result.id);
                    this.translatedIds = updated;
                }

            } catch (err) {
                console.error("Translation failed:", err);
            } finally {
                result.isTranslating = false;
            }
        }

    };
}
