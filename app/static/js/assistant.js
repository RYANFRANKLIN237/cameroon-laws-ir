function assistantApp() {
    const SERVICES = [
        {
            id: 'advice',
            icon: 'scale',
            label: 'Legal Advice',
            color: 'text-[#007A5E]',
            bg: 'bg-[#007A5E]/10',
            border: 'border-[#007A5E]/25',
            placeholder: 'Ask a legal question…  e.g. What are my rights as a tenant?',
            hints: [
                'What are my rights if I am arrested?',
                'How do I file a complaint with the courts?',
                'What does the labour code say about wrongful dismissal?',
                'Can my employer reduce my salary without notice?',
            ],
        },
        {
            id: 'drafting',
            icon: 'gavel',
            label: 'Legal Drafting',
            color: 'text-[#CE1126]',
            bg: 'bg-[#CE1126]/10',
            border: 'border-[#CE1126]/25',
            placeholder: 'Describe the document you need…  e.g. Draft a residential lease agreement',
            hints: [
                'Draft a non-disclosure agreement (NDA)',
                'Write an employment contract clause for remote work',
                'Help me write a formal complaint letter',
                'Draft a power of attorney document',
            ],
        },
        {
            id: 'misinfo',
            icon: 'shield-alert',
            label: 'Fact-check',
            color: 'text-[#B8860B]',
            bg: 'bg-[#FCD116]/20',
            border: 'border-[#FCD116]/60',
            placeholder: 'Submit a claim to verify…  e.g. Is it true you can be detained 72 hours without charge?',
            hints: [
                'Employers must give 30 days notice before termination — true?',
                'Verify: dual citizenship is illegal in Cameroon',
                'Fact-check: marriages must be registered within 60 days',
                'Is it legal for police to seize a phone without a warrant?',
            ],
        },
    ];

    const DEMO_RESPONSES = {
        advice: [
            "Based on Cameroon's Labour Code (Article 39), an employee who is wrongfully dismissed is entitled to compensation equivalent to the notice period plus severance pay calculated on years of service. You should formally request a written statement of reasons from your employer before taking further action.\n\nWould you like me to explain the steps for filing a labour dispute?",
            "Under the Constitution of Cameroon (Article 9), every person has the right to liberty and security. You must be informed of the charges against you at the time of arrest. Detention without charge may not exceed 48 hours without a judge's order, extendable once under exceptional circumstances.\n\nDo you want details on how to request legal aid?",
        ],
        drafting: [
            "Here's a draft clause for your document:\n\n**CONFIDENTIALITY**\nThe Receiving Party agrees to hold all Confidential Information in strict confidence, to use the Confidential Information solely for the purposes outlined in this Agreement, and not to disclose the Confidential Information to any third party without the prior written consent of the Disclosing Party.\n\nThis obligation shall survive termination of this Agreement for a period of **five (5) years**.\n\nShall I draft the full NDA, or adjust this clause first?",
            "Below is a standard remote work clause compliant with Cameroon's Labour Code:\n\n**REMOTE WORK ARRANGEMENT**\nThe Employee may perform duties remotely from an agreed location. The Employer shall provide necessary equipment and bear reasonable connectivity costs. Standard working hours apply (Article 80, Labour Code). The Employee consents to reasonable oversight measures for output verification.\n\nWould you like me to add a data security provision?",
        ],
        misinfo: [
            "**Claim verified — PARTIALLY TRUE**\n\nCameroon's Labour Code (Article 41) does require employers to give notice before termination, but the notice period varies by employment category:\n- Managerial staff: 3 months\n- Supervisory staff: 1 month\n- Other employees: typically 8–15 days\n\nThe blanket \"30 days\" figure is a simplification. Always check your employment category and applicable collective agreement.\n\n*Source: Labour Code of Cameroon, Articles 39–42*",
            "**Claim assessed — FALSE**\n\nDual citizenship in Cameroon is nuanced. The Nationality Code (Ordinance No. 68/LF/3) does not explicitly prohibit it in all cases. However, acquisition of a foreign nationality may result in loss of Cameroonian nationality unless an exemption applies.\n\n*Source: Ordinance No. 68/LF/3, Article 31*",
        ],
    };

    return {
        services: SERVICES,
        mode: 'advice',
        messages: [],
        input: '',
        loading: false,
        modePickerOpen: false,

        get hasMessages() {
            return this.messages.length > 0;
        },

        get activeService() {
            return this.services.find((s) => s.id === this.mode) || this.services[0];
        },

        init() {
            const params = new URLSearchParams(window.location.search);
            const initial = params.get('mode');
            if (this.services.some((s) => s.id === initial)) {
                this.mode = initial;
            }
            const prompt = params.get('prompt');
            if (prompt) {
                this.input = prompt;
            }

            this.$nextTick(() => lucide.createIcons());

            this.$watch('mode', () => {
                this.$nextTick(() => lucide.createIcons());
            });

            this.$watch('messages', () => {
                this.scrollToEnd();
                this.$nextTick(() => lucide.createIcons());
            });

            this.$watch('loading', () => {
                this.scrollToEnd();
                this.$nextTick(() => lucide.createIcons());
            });

            this.$watch('modePickerOpen', (open) => {
                if (open) this.$nextTick(() => lucide.createIcons());
            });
        },

        serviceById(id) {
            return this.services.find((s) => s.id === id) || this.services[0];
        },

        selectMode(id) {
            this.mode = id;
            this.modePickerOpen = false;
            this.$nextTick(() => {
                lucide.createIcons();
                this.$refs.textarea?.focus();
            });
        },

        useHint(svcId, hint) {
            this.mode = svcId;
            this.input = hint;
            this.$nextTick(() => {
                this.autoResize(this.$refs.textarea);
                this.$refs.textarea?.focus();
                lucide.createIcons();
            });
        },

        formatMessage(text) {
            const escaped = String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            return escaped
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.+?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');
        },

        formatTime(iso) {
            return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        },

        autoResize(el) {
            if (!el) return;
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, 128) + 'px';
        },

        resetTextarea() {
            const el = this.$refs.textarea;
            if (!el) return;
            el.style.height = 'auto';
        },

        scrollToEnd() {
            this.$nextTick(() => {
                this.$refs.messagesEnd?.scrollIntoView({ behavior: 'smooth' });
            });
        },

        handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.sendMessage(this.input);
            }
        },

        async sendMessage(text) {
            const trimmed = (text || '').trim();
            if (!trimmed || this.loading) return;

            this.messages.push({
                id: Date.now(),
                role: 'user',
                text: trimmed,
                mode: this.mode,
                timestamp: new Date().toISOString(),
            });
            this.input = '';
            this.resetTextarea();
            this.loading = true;

            await new Promise((resolve) => setTimeout(resolve, 1500 + Math.random() * 700));

            const pool = DEMO_RESPONSES[this.mode] || DEMO_RESPONSES.advice;
            this.messages.push({
                id: Date.now() + 1,
                role: 'assistant',
                text: pool[Math.floor(Math.random() * pool.length)],
                mode: this.mode,
                timestamp: new Date().toISOString(),
            });
            this.loading = false;
        },
    };
}
