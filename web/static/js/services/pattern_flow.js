// ==========================================================================
// PATTERN FLOW SERVICE - SPRINT 26
// ==========================================================================
// VERSION: 2.0.0 - Sprint 26 Pattern Flow Implementation
// PURPOSE: Real-time pattern flow display with 4-column layout and auto-refresh
// ==========================================================================

class PatternFlowService {
    constructor() {
        this.name = 'PatternFlowService';
        this.container = null;
        this.socket = null;
        this.tierPatternService = null;
        this.isActive = false;

        // Configuration
        this.config = {
            refreshInterval: 15000,      // 15 seconds
            maxPatternsPerColumn: 30,    // Memory management
            rowHeight: 60,               // Minimal design
            animationDuration: 300,      // Smooth transitions
            enableCountdown: true,       // Show countdown timer
            enableWebSocket: true,       // Real-time updates
            enablePolling: true          // Hybrid approach
        };

        // State management
        this.state = {
            patterns: {
                daily: [],
                hourly: [],
                intraday: [],
                weekly: [],
                monthly: [],
                daily_intraday: [],
                indicators: []
            },
            lastRefresh: null,
            countdown: 15,
            isRefreshing: false,
            connectionStatus: 'disconnected'
        };

        // UI elements
        this.elements = {
            columns: {},
            refreshTimer: null,
            countdownDisplay: null,
            statusIndicator: null
        };

        // Timers
        this.refreshTimer = null;
        this.countdownTimer = null;

        // Test mode
        this.testMode = false;
        this.testDataInterval = null;

        console.log('[PatternFlowService] Service initialized');
    }

    async initialize(containerSelector) {
        try {
            console.log('[PatternFlowService] Starting initialization...');

            this.container = document.querySelector(containerSelector);
            if (!this.container) {
                throw new Error('Container not found');
            }

            // Setup UI structure
            await this.setupUI();

            // Initialize tier pattern service
            await this.initializeTierPatternService();

            // Setup WebSocket integration
            if (this.config.enableWebSocket) {
                this.setupWebSocketHandlers();
            }

            // Start auto-refresh
            if (this.config.enablePolling) {
                this.startAutoRefresh();
            }

            // Load initial data
            await this.loadInitialData();

            this.isActive = true;
            console.log('[PatternFlowService] Initialization complete');

        } catch (error) {
            console.error('[PatternFlowService] Initialization failed:', error);
            this.showError('Failed to initialize Pattern Flow');
        }
    }

    async setupUI() {
        // Clear container
        this.container.innerHTML = '';

        // Create header with refresh timer
        const header = document.createElement('div');
        header.className = 'pattern-flow-header mb-3';
        header.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <h3 class="mb-0">
                    <i class="fas fa-stream me-2"></i>Pattern Flow
                </h3>
                <div class="d-flex align-items-center gap-3">
                    <button class="btn btn-sm btn-outline-primary" onclick="window.patternFlowService?.toggleTestMode()">
                        <i class="fas fa-flask me-1"></i>
                        <span id="test-mode-label">Enable Test Mode</span>
                    </button>
                    <div class="refresh-indicator">
                        <span class="refresh-label">Next refresh in: </span>
                        <span class="countdown-display fw-bold">${this.state.countdown}s</span>
                    </div>
                    <div class="connection-status">
                        <i class="fas fa-circle text-secondary" title="Disconnected"></i>
                    </div>
                </div>
            </div>
        `;
        this.container.appendChild(header);

        // Store header elements
        this.elements.countdownDisplay = header.querySelector('.countdown-display');
        this.elements.statusIndicator = header.querySelector('.connection-status i');

        // Create 4-column layout
        const columnsContainer = document.createElement('div');
        columnsContainer.className = 'pattern-flow-columns';

        const columns = [
            { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },
            { id: 'hourly', title: 'Hourly', icon: '⏰', color: '#6f42c1' },
            { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
            { id: 'weekly', title: 'Weekly', icon: '📈', color: '#20c997' },
            { id: 'monthly', title: 'Monthly', icon: '📅', color: '#e83e8c' },
            { id: 'daily_intraday', title: 'Combo', icon: '🔗', color: '#17a2b8' },
            { id: 'indicators', title: 'Indicators', icon: '📊', color: '#fd7e14' }
        ];

        columns.forEach(col => {
            const column = document.createElement('div');
            column.className = 'pattern-column-wrapper';
            column.innerHTML = `
                <div class="pattern-column" data-tier="${col.id}">
                    <div class="column-header" style="background-color: ${col.color}15; border-left: 3px solid ${col.color}">
                        <h5 class="mb-0">
                            <span>${col.icon}</span> ${col.title}
                            <span class="pattern-count badge bg-secondary ms-2">0</span>
                        </h5>
                    </div>
                    <div class="column-body">
                        <div class="pattern-list"></div>
                    </div>
                </div>
            `;
            columnsContainer.appendChild(column);

            // Store column references
            this.elements.columns[col.id] = {
                container: column.querySelector('.pattern-column'),
                list: column.querySelector('.pattern-list'),
                count: column.querySelector('.pattern-count')
            };
        });

        this.container.appendChild(columnsContainer);

        // Add CSS if not already present
        this.injectStyles();
    }

    injectStyles() {
        if (document.getElementById('pattern-flow-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'pattern-flow-styles';
        styles.innerHTML = `
            /* Pattern Flow Header - Using TickStock CSS Variables */
            .pattern-flow-header {
                padding: 15px;
                background: var(--color-background-secondary);
                border-radius: var(--border-radius-base);
                border: 1px solid var(--color-border-light);
                box-shadow: var(--shadow-subtle);
                margin-bottom: 15px;
            }

            .pattern-flow-header h3 {
                color: var(--color-text-primary);
                font-size: var(--font-size-xl);
                font-weight: var(--font-weight-semibold);
            }

            /* Force 4-column layout */
            .pattern-flow-columns {
                display: flex !important;
                flex-wrap: nowrap !important;
                gap: 15px;
                margin: 0;
                padding: 0;
            }

            .pattern-column-wrapper {
                flex: 1 1 25%;
                min-width: 0;
            }

            /* Pattern Column Layout */
            .pattern-column {
                background: var(--color-background-primary);
                border-radius: var(--border-radius-base);
                border: 1px solid var(--color-border-light);
                box-shadow: var(--shadow-subtle);
                height: calc(100vh - 250px);
                display: flex;
                flex-direction: column;
                transition: var(--transition-base);
                width: 100%;
            }

            .column-header {
                flex-shrink: 0;
                border-radius: var(--border-radius-base) var(--border-radius-base) 0 0;
                padding: 10px;
                border-bottom: 1px solid var(--color-border-light);
            }

            .column-header h5 {
                color: var(--color-text-primary);
                font-size: 14px;
                font-weight: var(--font-weight-semibold);
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .pattern-count {
                background: var(--color-border-secondary) !important;
                color: var(--color-text-primary) !important;
                font-size: var(--font-size-sm);
            }

            .column-body {
                flex: 1;
                overflow-y: auto;
                overflow-x: hidden;
                padding: var(--spacing-sm);
                background: var(--color-background-tertiary);
            }

            .pattern-list {
                display: flex;
                flex-direction: column;
                gap: var(--spacing-xs);
            }

            /* Pattern Row Styling - Single Line */
            .pattern-row {
                height: 40px;
                padding: 8px 10px;
                background: var(--color-background-primary);
                border: 1px solid var(--color-border-light);
                border-radius: var(--border-radius-small);
                display: flex;
                align-items: center;
                transition: var(--transition-base);
                cursor: pointer;
                animation: slideIn 0.3s ease;
                overflow: hidden;
            }

            .pattern-row:hover {
                background: var(--color-background-secondary);
                border-color: var(--color-border-primary);
                transform: translateX(3px);
                box-shadow: var(--shadow-subtle);
            }

            .pattern-row.new-pattern {
                animation: pulseIn 0.5s ease;
                background: var(--color-success-light);
                border-color: var(--color-success);
            }

            .pattern-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
                width: 100%;
                gap: 8px;
            }

            .pattern-symbol {
                font-weight: 600;
                font-size: 13px;
                color: var(--color-text-primary);
                min-width: 45px;
            }

            .pattern-type {
                font-size: 12px;
                color: var(--color-text-secondary);
                flex: 1;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .pattern-time {
                font-size: 11px;
                color: var(--color-text-muted);
                white-space: nowrap;
                margin-left: auto;
            }

            /* Confidence Badges */
            .confidence-badge {
                font-size: var(--font-size-xs);
                padding: 2px 6px;
                border-radius: 12px;
                font-weight: var(--font-weight-semibold);
            }

            .confidence-badge.high {
                background: var(--color-success);
                color: var(--color-text-white);
            }

            .confidence-badge.low {
                background: var(--color-warning);
                color: var(--color-text-white);
            }

            .confidence-badge:not(.high):not(.low) {
                background: var(--color-info);
                color: var(--color-text-white);
            }

            /* Status Indicators */
            .refresh-indicator {
                font-size: var(--font-size-sm);
                color: var(--color-text-secondary);
            }

            .countdown-display {
                color: var(--color-primary);
                min-width: 30px;
                display: inline-block;
                text-align: center;
                font-weight: var(--font-weight-semibold);
            }

            .connection-status .fa-circle {
                font-size: 10px;
            }

            .connection-status .fa-circle.text-success {
                color: var(--color-success);
                animation: pulse 2s infinite;
            }

            .connection-status .fa-circle.text-secondary {
                color: var(--color-text-muted);
            }

            /* Animations */
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes pulseIn {
                0%, 100% {
                    transform: scale(1);
                }
                50% {
                    transform: scale(1.02);
                }
            }

            @keyframes pulse {
                0%, 100% {
                    opacity: 1;
                }
                50% {
                    opacity: 0.5;
                }
            }

            /* Theme-specific overrides for Light Theme */
            .theme-light .pattern-flow-header {
                background: #ffffff;
                border-color: #dee2e6;
            }

            .theme-light .pattern-column {
                background: #ffffff;
                border-color: #dee2e6;
            }

            .theme-light .column-header {
                border-bottom-color: #dee2e6;
            }

            .theme-light .column-body {
                background: #f8f9fa;
            }

            .theme-light .pattern-row {
                background: #ffffff;
                border-color: #e9ecef;
            }

            .theme-light .pattern-row:hover {
                background: #f8f9fa;
                border-color: #dee2e6;
            }

            /* Theme-specific overrides for Dark Theme */
            .theme-dark .pattern-flow-header {
                background: #2d2d2d;
                border-color: #444444;
            }

            .theme-dark .pattern-column {
                background: #1a1a1a;
                border-color: #444444;
            }

            .theme-dark .column-header {
                background: #242424;
                border-bottom-color: #444444;
            }

            .theme-dark .column-body {
                background: #1a1a1a;
            }

            .theme-dark .pattern-row {
                background: #2d2d2d;
                border-color: #333333;
            }

            .theme-dark .pattern-row:hover {
                background: #3a3a3a;
                border-color: #555555;
            }

            .theme-dark .pattern-row.new-pattern {
                background: #1e3a1e;
                border-color: #4caf50;
            }

            .theme-dark .pattern-count {
                background: #444444 !important;
                color: #ffffff !important;
            }

            .theme-dark .confidence-badge.high {
                background: #4caf50;
            }

            .theme-dark .confidence-badge.low {
                background: #ff9800;
            }

            .theme-dark .confidence-badge:not(.high):not(.low) {
                background: #2196f3;
            }

            /* Scrollbar styling for dark theme */
            .theme-dark .column-body::-webkit-scrollbar {
                width: 8px;
            }

            .theme-dark .column-body::-webkit-scrollbar-track {
                background: #1a1a1a;
            }

            .theme-dark .column-body::-webkit-scrollbar-thumb {
                background: #444444;
                border-radius: 4px;
            }

            .theme-dark .column-body::-webkit-scrollbar-thumb:hover {
                background: #555555;
            }

            /* Scrollbar styling for light theme */
            .theme-light .column-body::-webkit-scrollbar {
                width: 8px;
            }

            .theme-light .column-body::-webkit-scrollbar-track {
                background: #f8f9fa;
            }

            .theme-light .column-body::-webkit-scrollbar-thumb {
                background: #dee2e6;
                border-radius: 4px;
            }

            .theme-light .column-body::-webkit-scrollbar-thumb:hover {
                background: #ccc;
            }
        `;
        document.head.appendChild(styles);
    }

    async initializeTierPatternService() {
        try {
            // Check if TierPatternService exists
            if (typeof TierPatternService === 'undefined') {
                console.warn('[PatternFlowService] TierPatternService not found, using mock data');
                this.tierPatternService = this.createMockService();
                return;
            }

            // Initialize the service
            if (!window.tierPatternService) {
                window.tierPatternService = new TierPatternService();
                await window.tierPatternService.init();
            }

            this.tierPatternService = window.tierPatternService;
            console.log('[PatternFlowService] TierPatternService connected');

        } catch (error) {
            console.error('[PatternFlowService] Failed to initialize TierPatternService:', error);
            this.tierPatternService = this.createMockService();
        }
    }

    setupWebSocketHandlers() {
        this.socket = window.socket || io();

        // Pattern detection events
        this.socket.on('pattern_detected', (data) => {
            if (this.isActive) {
                this.handleNewPattern(data);
            }
        });

        // Indicator updates
        this.socket.on('indicator_update', (data) => {
            if (this.isActive) {
                this.handleIndicatorUpdate(data);
            }
        });

        // Connection status
        this.socket.on('connect', () => {
            this.updateConnectionStatus('connected');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus('disconnected');
        });

        // Subscribe to pattern channels
        this.socket.emit('subscribe', {
            channels: ['patterns.intraday', 'patterns.hourly', 'patterns.daily', 'patterns.weekly', 'patterns.monthly', 'patterns.daily_intraday', 'indicators']
        });

        console.log('[PatternFlowService] WebSocket handlers configured');
    }

    startAutoRefresh() {
        // Clear any existing timers
        this.stopAutoRefresh();

        // Start refresh timer
        this.refreshTimer = setInterval(() => {
            this.refreshAllColumns();
        }, this.config.refreshInterval);

        // Start countdown timer
        if (this.config.enableCountdown) {
            this.startCountdown();
        }

        console.log('[PatternFlowService] Auto-refresh started');
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }

        if (this.countdownTimer) {
            clearInterval(this.countdownTimer);
            this.countdownTimer = null;
        }
    }

    startCountdown() {
        this.state.countdown = Math.floor(this.config.refreshInterval / 1000);
        this.updateCountdownDisplay();

        this.countdownTimer = setInterval(() => {
            this.state.countdown--;

            if (this.state.countdown <= 0) {
                this.state.countdown = Math.floor(this.config.refreshInterval / 1000);
            }

            this.updateCountdownDisplay();
        }, 1000);
    }

    updateCountdownDisplay() {
        if (this.elements.countdownDisplay) {
            this.elements.countdownDisplay.textContent = `${this.state.countdown}s`;
        }
    }

    async loadInitialData() {
        console.log('[PatternFlowService] Loading initial data...');

        try {
            // Load all tiers in parallel
            const promises = ['intraday', 'hourly', 'daily', 'weekly', 'monthly', 'daily_intraday', 'indicators'].map(tier =>
                this.loadPatternsByTier(tier)
            );

            await Promise.all(promises);

            console.log('[PatternFlowService] Initial data loaded');

        } catch (error) {
            console.error('[PatternFlowService] Failed to load initial data:', error);
        }
    }

    async loadPatternsByTier(tier) {
        try {
            // Map tier IDs to tier-specific API endpoints (query database tables directly)
            const endpointMap = {
                daily: '/api/patterns/daily',
                hourly: '/api/patterns/hourly',
                intraday: '/api/patterns/intraday',
                weekly: '/api/patterns/weekly',
                monthly: '/api/patterns/monthly',
                daily_intraday: '/api/patterns/daily_intraday',
                indicators: '/api/patterns/indicators/latest'
            };

            const endpoint = endpointMap[tier];
            if (!endpoint) {
                throw new Error(`Unknown tier: ${tier}`);
            }

            // Call tier-specific endpoint with appropriate parameters
            const response = await fetch(`${endpoint}?limit=50&confidence_min=0.5`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Handle indicators endpoint (returns 'indicators' array instead of 'patterns')
            let rawData = tier === 'indicators' ? (data.indicators || []) : (data.patterns || []);

            // Transform data to match expected format
            const transformedPatterns = rawData.map(p => {
                // Handle indicators format (different field names)
                if (tier === 'indicators') {
                    return {
                        id: p.id,
                        symbol: p.symbol,
                        type: p.indicator_type || 'Indicator',
                        confidence: 1.0,  // Indicators don't have confidence
                        timestamp: p.calculation_timestamp || p.timestamp,
                        value: p.value,
                        value_data: p.value_data,
                        timeframe: p.timeframe,
                        metadata: p.metadata,
                        tier: tier
                    };
                }

                // Handle pattern format
                return {
                    id: p.id,
                    symbol: p.symbol,
                    type: p.pattern_type || p.type,
                    confidence: p.confidence,
                    timestamp: p.detection_timestamp || p.timestamp,
                    pattern_data: p.pattern_data,
                    levels: p.levels,
                    metadata: p.metadata,
                    tier: p.tier || tier
                };
            });

            // Update state and UI
            this.state.patterns[tier] = transformedPatterns;
            this.renderPatterns(tier);

        } catch (error) {
            console.warn(`[PatternFlowService] Using mock data for ${tier}:`, error);

            // Use mock data as fallback
            this.state.patterns[tier] = this.generateMockPatterns(tier, 10);
            this.renderPatterns(tier);
        }
    }

    renderPatterns(tier) {
        const column = this.elements.columns[tier];
        if (!column) return;

        const patterns = this.state.patterns[tier];
        const list = column.list;

        // Clear existing content
        list.innerHTML = '';

        // Limit to max patterns
        const displayPatterns = patterns.slice(0, this.config.maxPatternsPerColumn);

        // Create pattern rows
        displayPatterns.forEach((pattern, index) => {
            const row = this.createPatternRow(pattern, tier);

            // Add slight delay for animation
            setTimeout(() => {
                list.appendChild(row);
            }, index * 50);
        });

        // Update count
        column.count.textContent = displayPatterns.length;
    }

    createPatternRow(pattern, tier) {
        const row = document.createElement('div');
        row.className = 'pattern-row';
        row.dataset.patternId = pattern.id;

        // Determine confidence level
        const confidenceClass = pattern.confidence > 0.8 ? 'high' :
                               pattern.confidence > 0.6 ? '' : 'low';

        // Format timestamp
        const time = this.formatTime(pattern.timestamp);

        row.innerHTML = `
            <div class="pattern-content">
                <span class="pattern-symbol">${pattern.symbol}</span>
                <span class="pattern-type">${pattern.type}</span>
                <span class="confidence-badge ${confidenceClass}">
                    ${Math.round(pattern.confidence * 100)}%
                </span>
                <span class="pattern-time">${time}</span>
            </div>
        `;

        // Add click handler
        row.addEventListener('click', () => {
            this.showPatternDetails(pattern);
        });

        return row;
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) {
            return 'just now';
        } else if (diff < 3600000) {
            return `${Math.floor(diff / 60000)}m ago`;
        } else if (diff < 86400000) {
            return `${Math.floor(diff / 3600000)}h ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    handleNewPattern(data) {
        const { tier, pattern } = data;

        if (!this.state.patterns[tier]) return;

        // Add to beginning of array
        this.state.patterns[tier].unshift(pattern);

        // Trim to max size
        if (this.state.patterns[tier].length > this.config.maxPatternsPerColumn) {
            this.state.patterns[tier] = this.state.patterns[tier].slice(0, this.config.maxPatternsPerColumn);
        }

        // Render with animation
        this.renderPatternsWithHighlight(tier, pattern.id);
    }

    handleIndicatorUpdate(data) {
        // Treat indicators as patterns in the indicators column
        this.handleNewPattern({
            tier: 'indicators',
            pattern: data
        });
    }

    renderPatternsWithHighlight(tier, highlightId) {
        this.renderPatterns(tier);

        // Highlight new pattern
        setTimeout(() => {
            const row = this.elements.columns[tier].list.querySelector(`[data-pattern-id="${highlightId}"]`);
            if (row) {
                row.classList.add('new-pattern');
                setTimeout(() => {
                    row.classList.remove('new-pattern');
                }, 2000);
            }
        }, 100);
    }

    async refreshAllColumns() {
        if (this.state.isRefreshing) return;

        console.log('[PatternFlowService] Refreshing all columns...');
        this.state.isRefreshing = true;

        try {
            await this.loadInitialData();
            this.state.lastRefresh = new Date();
        } catch (error) {
            console.error('[PatternFlowService] Refresh failed:', error);
        } finally {
            this.state.isRefreshing = false;
        }
    }

    updateConnectionStatus(status) {
        this.state.connectionStatus = status;

        if (this.elements.statusIndicator) {
            const icon = this.elements.statusIndicator;

            if (status === 'connected') {
                icon.className = 'fas fa-circle text-success';
                icon.title = 'Connected';
            } else {
                icon.className = 'fas fa-circle text-secondary';
                icon.title = 'Disconnected';
            }
        }
    }

    showPatternDetails(pattern) {
        // Create modal for pattern details
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Pattern Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <h6>${pattern.symbol} - ${pattern.type}</h6>
                        <p>Confidence: ${Math.round(pattern.confidence * 100)}%</p>
                        <p>Time: ${new Date(pattern.timestamp).toLocaleString()}</p>
                        ${pattern.details ? `<pre>${JSON.stringify(pattern.details, null, 2)}</pre>` : ''}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Clean up on close
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    showError(message) {
        console.error('[PatternFlowService]', message);

        if (this.container) {
            this.container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            `;
        }
    }

    // Mock service for development/testing
    createMockService() {
        return {
            getPatternsByTier: async (tier) => {
                return this.generateMockPatterns(tier, 10);
            }
        };
    }

    generateMockPatterns(tier, count) {
        const patterns = [];
        const symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'AMD'];
        const types = {
            daily: ['Bull Flag', 'Bear Flag', 'Cup and Handle', 'Head and Shoulders'],
            hourly: ['Hourly Breakout', 'Momentum Build', 'Range Break', 'Trend Shift'],
            intraday: ['Momentum Shift', 'Volume Spike', 'Support Break', 'Resistance Test'],
            weekly: ['Weekly Trend', 'Long-term Break', 'Major Support', 'Key Resistance'],
            monthly: ['Monthly Pattern', 'Long Trend', 'Major Level', 'Cycle Turn'],
            daily_intraday: ['Multi-TF Bull', 'Cross-Tier Confirm', 'Divergence Signal'],
            indicators: ['RSI Oversold', 'MACD Cross', 'MA Golden Cross', 'Volume Surge']
        };

        for (let i = 0; i < count; i++) {
            patterns.push({
                id: `${tier}_${Date.now()}_${i}`,
                symbol: symbols[Math.floor(Math.random() * symbols.length)],
                type: types[tier][Math.floor(Math.random() * types[tier].length)],
                timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
                confidence: 0.5 + Math.random() * 0.5,
                tier: tier,
                details: {
                    entry: (100 + Math.random() * 100).toFixed(2),
                    target: (110 + Math.random() * 100).toFixed(2),
                    stop: (90 + Math.random() * 100).toFixed(2)
                }
            });
        }

        return patterns.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }

    cleanup() {
        console.log('[PatternFlowService] Cleaning up...');

        // Stop timers
        this.stopAutoRefresh();
        this.stopTestMode();

        // Remove WebSocket handlers
        if (this.socket) {
            this.socket.off('pattern_detected');
            this.socket.off('indicator_update');
            this.socket.off('connect');
            this.socket.off('disconnect');
        }

        // Clear container
        if (this.container) {
            this.container.innerHTML = '';
        }

        this.isActive = false;
    }

    // Test Mode Methods
    toggleTestMode() {
        if (this.testMode) {
            this.stopTestMode();
        } else {
            this.startTestMode();
        }
    }

    startTestMode() {
        console.log('[PatternFlowService] Starting test mode...');
        this.testMode = true;

        // Update button label
        const label = document.getElementById('test-mode-label');
        if (label) {
            label.textContent = 'Disable Test Mode';
        }

        // Show test mode indicator
        this.showTestModeIndicator();

        // Generate initial batch of patterns
        this.generateTestPatterns();

        // Start continuous pattern generation
        this.testDataInterval = setInterval(() => {
            this.generateSingleTestPattern();
        }, 3000); // Generate a new pattern every 3 seconds

        // Update connection status to show test mode
        this.updateConnectionStatus('connected');
    }

    stopTestMode() {
        console.log('[PatternFlowService] Stopping test mode...');
        this.testMode = false;

        // Update button label
        const label = document.getElementById('test-mode-label');
        if (label) {
            label.textContent = 'Enable Test Mode';
        }

        // Remove test mode indicator
        this.hideTestModeIndicator();

        // Stop pattern generation
        if (this.testDataInterval) {
            clearInterval(this.testDataInterval);
            this.testDataInterval = null;
        }

        // Clear existing patterns
        Object.keys(this.state.patterns).forEach(tier => {
            this.state.patterns[tier] = [];
            this.renderPatterns(tier);
        });
    }

    showTestModeIndicator() {
        // Add a visual indicator that test mode is active
        const header = this.container.querySelector('.pattern-flow-header h3');
        if (header && !header.querySelector('.test-mode-badge')) {
            const badge = document.createElement('span');
            badge.className = 'badge bg-warning text-dark ms-2 test-mode-badge';
            badge.textContent = 'TEST MODE';
            badge.style.fontSize = '12px';
            header.appendChild(badge);
        }
    }

    hideTestModeIndicator() {
        const badge = this.container.querySelector('.test-mode-badge');
        if (badge) {
            badge.remove();
        }
    }

    generateTestPatterns() {
        const tiers = ['intraday', 'hourly', 'daily', 'weekly', 'monthly', 'daily_intraday', 'indicators'];
        const symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'AMD', 'SPY', 'QQQ'];

        // Generate 5-8 patterns for each tier
        tiers.forEach(tier => {
            const patternCount = 5 + Math.floor(Math.random() * 4);

            for (let i = 0; i < patternCount; i++) {
                const pattern = this.createTestPattern(tier, symbols);

                // Add to state with slight delay for animation
                setTimeout(() => {
                    this.state.patterns[tier].unshift(pattern);

                    // Keep only max patterns
                    if (this.state.patterns[tier].length > this.config.maxPatternsPerColumn) {
                        this.state.patterns[tier] = this.state.patterns[tier].slice(0, this.config.maxPatternsPerColumn);
                    }

                    this.renderPatterns(tier);
                }, i * 200);
            }
        });
    }

    generateSingleTestPattern() {
        const tiers = ['intraday', 'hourly', 'daily', 'weekly', 'monthly', 'daily_intraday', 'indicators'];
        const tier = tiers[Math.floor(Math.random() * tiers.length)];
        const symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'AMD', 'SPY', 'QQQ'];

        const pattern = this.createTestPattern(tier, symbols);

        // Simulate new pattern detection
        this.handleNewPattern({
            tier: tier,
            pattern: pattern
        });
    }

    createTestPattern(tier, symbols) {
        const patternTypes = {
            daily: ['Bull Flag', 'Bear Flag', 'Cup & Handle', 'Head & Shoulders', 'Double Top', 'Double Bottom', 'Triangle', 'Wedge'],
            hourly: ['Hourly Breakout', 'Momentum Build', 'Range Break', 'Trend Shift', 'Support Test', 'Volume Pattern'],
            intraday: ['Momentum Burst', 'Volume Spike', 'Support Break', 'Resistance Test', 'Gap Fill', 'Reversal', 'Breakout'],
            weekly: ['Weekly Trend', 'Long-term Break', 'Major Support', 'Key Resistance', 'Cycle Pattern', 'Swing Setup'],
            monthly: ['Monthly Pattern', 'Long Trend', 'Major Level', 'Cycle Turn', 'Position Build', 'Investment Signal'],
            daily_intraday: ['Multi-TF Bullish', 'Cross-Tier Confirm', 'Divergence Signal', 'Convergence Setup', 'Trend Alignment'],
            indicators: ['RSI Oversold', 'RSI Overbought', 'MACD Cross', 'MA Golden Cross', 'Volume Surge', 'Bollinger Squeeze', 'Stochastic Signal']
        };

        const symbol = symbols[Math.floor(Math.random() * symbols.length)];
        const types = patternTypes[tier] || patternTypes.daily;
        const type = types[Math.floor(Math.random() * types.length)];

        // Generate realistic confidence based on tier
        let confidence;
        if (tier === 'combo') {
            confidence = 0.75 + Math.random() * 0.2; // 75-95% for combo patterns
        } else if (tier === 'indicators') {
            confidence = 0.6 + Math.random() * 0.35; // 60-95% for indicators
        } else {
            confidence = 0.5 + Math.random() * 0.45; // 50-95% for others
        }

        // Generate timestamp (recent times)
        const minutesAgo = Math.floor(Math.random() * 60);
        const timestamp = new Date(Date.now() - minutesAgo * 60000);

        return {
            id: `test_${tier}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            symbol: symbol,
            type: type,
            timestamp: timestamp.toISOString(),
            confidence: confidence,
            tier: tier,
            details: {
                entry: (100 + Math.random() * 300).toFixed(2),
                target: (110 + Math.random() * 300).toFixed(2),
                stop: (90 + Math.random() * 300).toFixed(2),
                volume: Math.floor(1000000 + Math.random() * 5000000),
                change_pct: (-5 + Math.random() * 10).toFixed(2)
            },
            isTest: true
        };
    }
}

// Register service globally
window.PatternFlowService = PatternFlowService;
console.log('[PatternFlowService] Service registered globally');