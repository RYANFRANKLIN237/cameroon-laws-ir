function metricsApp() {
    return {
        isLoading: true,

        // Data from /api/metrics
        baseline: {},
        ranked: {},
        granularity: {},
        systemData: {},

        // Main table rows: Hit@3, MRR, Precision@3, Recall@10
        metricRows: [
            { key: "hitAt3", label: "Hit@3", description: "At least one relevant in top 3", isCount: false },
            { key: "mrr", label: "Mean Reciprocal Rank", description: "Average reciprocal rank", isCount: false },
            { key: "precisionAt3", label: "Precision@3", description: "Precision at rank 3", isCount: false },
            { key: "recallAt10", label: "Recall@10", description: "Recall at rank 10", isCount: false },
        ],

        // Granularity comparison rows (keep failedQueries as integer)
        granularityRows: [
            { key: "precisionAt3", label: "Precision@3", description: "Precision at rank 3", isCount: false },
            { key: "mrr", label: "Mean Reciprocal Rank", description: "Average reciprocal rank", isCount: false },
            { key: "recallAt10", label: "Recall@10", description: "Recall at rank 10", isCount: false },
            { key: "failedQueries", label: "Failed Queries", description: "Queries with no relevant results", isCount: true },
        ],

        async init() {
            lucide.createIcons();

            try {
                const res = await fetch('/api/metrics');
                const data = await res.json();

                this.baseline = data.baseline;
                this.ranked = data.ranked;
                // Attach per-level failed query counts
                data.granularity.clause.failedQueries = data.systemData.failedQueries;
                data.granularity.as.failedQueries = data.systemData.failedQueries_as;
                data.granularity.document.failedQueries = data.systemData.failedQueries_document;
                this.granularity = data.granularity;
                this.systemData = data.systemData;

            } catch (err) {
                console.error('Failed to load metrics:', err);
            } finally {
                this.isLoading = false;
                this.$nextTick(() => {
                    lucide.createIcons();
                    this.animateBars();
                });
            }
        },

        improvement(key) {
            const b = this.baseline[key];
            const r = this.ranked[key];
            if (!b) return 0;
            return ((r - b) / b) * 100;
        },

        improvementLabel(key) {
            const imp = this.improvement(key);
            const formatted = imp.toFixed(1) + '%';
            return imp > 0 ? '+' + formatted : formatted;
        },

        animateBars() {
            document.querySelectorAll('.bar-fill').forEach(bar => {
                const targetWidth = bar.getAttribute('data-width');
                if (targetWidth) {
                    setTimeout(() => {
                        bar.style.width = targetWidth;
                    }, 50);
                }
            });
        },
    };
}