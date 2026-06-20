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
            { key: "avg_result_length", label: "Avg Length (words)", description: "Average result length in words", isCount: false, isLength: true },
        ],

        async init() {
            lucide.createIcons();

            // 1. Try to load from sessionStorage cache
            const cached = sessionStorage.getItem('metricsData');
            if (cached) {
                try {
                    const data = JSON.parse(cached);
                    this.applyMetricsData(data);
                    return;
                } catch (e) {
                    console.warn('Failed to parse cached metrics data', e);
                }
            }

            // 2. No cache or invalid – fetch from API
            try {
                const res = await fetch('/api/metrics');
                const data = await res.json();
                sessionStorage.setItem('metricsData', JSON.stringify(data));
                this.applyMetricsData(data);
            } catch (err) {
                console.error('Failed to load metrics:', err);
                this.isLoading = false;
            }
        },

        // Helper to apply data to component state and trigger animations
        applyMetricsData(data) {
            this.baseline = data.baseline;
            this.ranked = data.ranked;

            data.granularity.clause.failedQueries = data.systemData.failedQueries;
            data.granularity.as.failedQueries = data.systemData.failedQueries_as;
            data.granularity.document.failedQueries = data.systemData.failedQueries_document;
            this.granularity = data.granularity;
            this.systemData = data.systemData;

            this.isLoading = false;
            this.$nextTick(() => {
                lucide.createIcons();
                this.animateBars();
            });
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