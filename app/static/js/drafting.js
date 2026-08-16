function draftingApp() {
    const COMPLEXITY_STYLE = {
        Simple: 'bg-green-50 text-green-700 border-green-200',
        Moderate: 'bg-[#FCD116]/15 text-gray-800 border-[#FCD116]/40',
        Complex: 'bg-red-50 text-red-700 border-red-200',
    };

    return {
        categories: [],
        templates: [],
        activeCategory: 'all',
        searchQuery: '',
        selectedTemplate: null,
        loaded: false,
        downloadNotice: '',

        get filtered() {
            const q = this.searchQuery.trim().toLowerCase();
            return this.templates.filter((t) => {
                const matchCat = this.activeCategory === 'all' || t.category === this.activeCategory;
                const matchSearch = !q
                    || t.title.toLowerCase().includes(q)
                    || t.description.toLowerCase().includes(q);
                return matchCat && matchSearch;
            });
        },

        get popular() {
            return this.templates.filter((t) => t.popular);
        },

        get showMostUsed() {
            return this.activeCategory === 'all' && !this.searchQuery.trim();
        },

        get sectionTitle() {
            if (this.searchQuery.trim()) {
                return `Results for "${this.searchQuery.trim()}"`;
            }
            const cat = this.categories.find((c) => c.id === this.activeCategory);
            return cat ? cat.label : 'All Templates';
        },

        complexityClass(level) {
            return COMPLEXITY_STYLE[level] || COMPLEXITY_STYLE.Simple;
        },

        categoryCount(id) {
            if (id === 'all') return this.templates.length;
            return this.templates.filter((t) => t.category === id).length;
        },

        async init() {
            this.$watch('selectedTemplate', () => {
                this.downloadNotice = '';
                this.$nextTick(() => lucide.createIcons());
            });

            this.$watch('searchQuery', () => {
                this.$nextTick(() => lucide.createIcons());
            });

            this.$watch('activeCategory', () => {
                this.$nextTick(() => lucide.createIcons());
            });

            try {
                const res = await fetch('/api/templates');
                const data = await res.json();
                this.categories = data.categories || [];
                this.templates = (data.templates || []).map((t) => ({
                    popular: false,
                    ...t,
                }));
            } catch (err) {
                console.error('Failed to load templates:', err);
            } finally {
                this.loaded = true;
                this.$nextTick(() => lucide.createIcons());
            }
        },

        openTemplate(template) {
            this.selectedTemplate = template;
        },

        closeTemplate() {
            this.selectedTemplate = null;
        },

        useTemplate() {
            if (!this.selectedTemplate) return;
            const prompt = `Draft a ${this.selectedTemplate.title}`;
            window.location.href = `/assistant?mode=drafting&prompt=${encodeURIComponent(prompt)}`;
        },

        downloadTemplate() {
            this.downloadNotice = 'DOCX export will be available in a later release.';
        },
    };
}
