function createSidebarState() {
    return {
        showSidebar: false,
        sidebarFeatures: [
            {
                icon: 'sparkles',
                label: 'Legal AI Assistant',
                description: 'Get legal advice, draft documents, and fact-check claims with AI',
                action: 'ai',
            },
            {
                icon: 'file-check',
                label: 'Document Verification',
                description: "Verify a document's authenticity against our official registry",
                action: 'verify',
            },
            {
                icon: 'file-signature',
                label: 'Legal Drafting',
                description: 'Browse templates for contracts, petitions, corporate filings & more',
                action: 'drafting',
            },
        ],

        handleSidebarFeature(action) {
            this.showSidebar = false;
            if (action === 'ai') {
                window.location.href = '/assistant';
                return;
            }
            if (action === 'drafting') {
                window.location.href = '/drafting';
                return;
            }
            // Feature screens wired up later
            if (action === 'verify') {
                return;
            }
        },

        initSidebar() {
            this.$watch('showSidebar', (open) => {
                if (open) {
                    this.$nextTick(() => lucide.createIcons());
                }
            });
        },
    };
}
