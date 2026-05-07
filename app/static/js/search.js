function searchApp() {
    return {
        // ── State ──────────────────────────────────────────
        query: '',
        lastQuery: '',       // what was actually searched (so typing doesn't change the label)
        results: [],
        hasSearched: false,
        isLoading: false,
        searchTime: '0.000',
        translatedIds: new Set(),  // tracks which card IDs have translation showing

        loaded: false,

        suggestions: [
            { label: 'Constitution', color: 'bg-[#E8F5E9] text-[#2E7D32] hover:bg-[#C8E6C9]', value: 'constitution' },
            { label: "Droits de l'Homme", color: 'bg-[#FFEBEE] text-[#C62828] hover:bg-[#FFCDD2]', value: 'droits' },
            { label: 'Judicial System', color: 'bg-[#FFFDE7] text-[#F9A825] hover:bg-[#FFF9C4]', value: 'judiciary' },
        ],

        // ── Init ───────────────────────────────────────────
        init() {
            lucide.createIcons();
            setTimeout(() => { this.loaded = true; }, 100);
        },

        // ── Search ─────────────────────────────────────────
        async handleSearch() {
            if (!this.query.trim()) return;

            this.isLoading = true;
            this.lastQuery = this.query;
            this.translatedIds = new Set();  // reset translations on new search

            const startTime = performance.now();

            try {
                const response = await fetch(`/api/search?q=${encodeURIComponent(this.query)}`);
                const data = await response.json();

                const endTime = performance.now();
                this.searchTime = (endTime - startTime).toFixed(3);

                this.results = data.results;
                this.hasSearched = true;

            } catch (err) {
                console.error('Search failed:', err);
                this.results = [];
                this.hasSearched = true;
            } finally {
                this.isLoading = false;
                // Re-run lucide so icons inside dynamic cards get rendered
                this.$nextTick(() => lucide.createIcons());
            }
        },

        // Quick search from suggestion chip
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

        // Toggle translation for a single card
        async toggleTranslation(result) {

            const updated = new Set(this.translatedIds);

            // Toggle OFF
            if (updated.has(result.id)) {
                updated.delete(result.id);
                this.translatedIds = updated;
                return;
            }

            // Already translated → reuse
            if (result.translation) {
                updated.add(result.id);
                this.translatedIds = updated;
                return;
            }

            try {
                result.isTranslating = true;

                const target = result.language === 'en' ? 'fr' : 'en';

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