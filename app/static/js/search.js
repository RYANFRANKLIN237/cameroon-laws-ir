function loadAppLanguages() {
    const el = document.getElementById('app-languages');
    if (!el) return [];
    try {
        return JSON.parse(el.textContent);
    } catch {
        return [];
    }
}

let searchAppInstance = null;

function searchApp() {
    const app = Alpine.reactive({
        ...createSidebarState(),
        // ── State ──────────────────────────────────────────
        query: '',
        lastQuery: '',
        results: [],
        hasSearched: false,
        isLoading: false,
        searchTime: '0.000',
        translatedIds: new Set(),
        expandedRefs: {}, // Map: resultId -> expandedRefIndex

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

            // Event delegation for cross-reference clicks — single global listener
            if (!window.__lexAfriqueXrefListenerAdded) {
                window.__lexAfriqueXrefListenerAdded = true;
                document.addEventListener('click', (e) => {
                    const button = e.target.closest('[data-xref-click]');
                    if (!button) return;
                    e.preventDefault();
                    const refIndex = parseInt(button.dataset.refIndex, 10);
                    const resultId = button.dataset.resultId;
                    const app = window.searchAppInstance || null;
                    if (!Number.isNaN(refIndex) && resultId && app && typeof app.toggleRefExpansion === 'function') {
                        app.toggleRefExpansion(resultId, refIndex);
                    }
                });
            }
            // expose for inline onclick fallback
            window._lexToggleRef = (resultId, refIndex) => {
                const app = window.searchAppInstance;
                if (app) app.toggleRefExpansion(String(resultId), Number(refIndex));
            };
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
            this.expandedRefs = {};
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

        // Render content with cross-reference links
        renderContentWithRefs(text, refs, resultId, isTranslated, highlight) {
            if (!refs || refs.length === 0 || isTranslated) {
                return this.highlightText(text, highlight);
            }

            // Sort refs by start position (descending) to replace from end to start
            const sortedRefs = [...refs].sort((a, b) => b.start - a.start);

            let rendered = text;
            for (const ref of sortedRefs) {
                const before = rendered.substring(0, ref.start);
                const after = rendered.substring(ref.end);
                const refText = rendered.substring(ref.start, ref.end);

                const refIndex = refs.indexOf(ref);

                // Use a simpler approach with data attributes and event delegation
                const refHtml = `<button type="button"
                    data-xref-click
                    data-ref-index="${refIndex}"
                    data-result-id="${resultId}"
                    class="xref-link inline font-semibold underline underline-offset-2 decoration-[#007A5E] transition-colors"
                >${this.escapeHtml(refText)}</button>`;

                rendered = before + refHtml + after;
            }

            // Apply yellow highlighting AFTER cross-reference links
            return this.highlightText(rendered, highlight);
        },

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        // Toggle cross-reference expansion — single source of truth in parent
        async toggleRefExpansion(resultId, refIndex) {
            const rid = String(resultId);
            const idx = Number(refIndex);
            const result = this.results.find((r) => String(r.id) === rid);
            if (!result || !result.refs || !result.refs[idx]) return;
            const ref = result.refs[idx];
            if (ref.isLoading) return;

            // Toggle close if same ref is already open (check both string and numeric key)
            const current = this.expandedRefs[rid] ?? this.expandedRefs[result.id];
            if (current === idx) {
                const next = { ...this.expandedRefs };
                delete next[rid];
                delete next[result.id];
                delete next[String(result.id)];
                this.expandedRefs = next;
                this.$nextTick(() => lucide.createIcons());
                return;
            }

            // Fetch on first open
            if (!ref.expandedData) {
                ref.isLoading = true;
                try {
                    const resp = await fetch(`/api/unit?id=${encodeURIComponent(ref.target_unit_id)}`);
                    const data = await resp.json();
                    ref.expandedData = data;
                } catch (err) {
                    console.error('Failed to fetch cross-reference:', err);
                } finally {
                    ref.isLoading = false;
                }
            }

            this.expandedRefs = { ...this.expandedRefs, [rid]: idx };
            this.$nextTick(() => lucide.createIcons());
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
    });

    searchAppInstance = app;
    window.searchAppInstance = app;
    return app;
}
