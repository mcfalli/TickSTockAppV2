// ==========================================================================
// MULTI-TIER DASHBOARD COMPONENT - SPRINT 25 WEEK 2
// ==========================================================================
// VERSION: 1.0.0 - Sprint 25 Week 2 Implementation
// PURPOSE: Multi-tier pattern dashboard with real-time WebSocket updates
// ==========================================================================

// Debug flag for development
const MULTI_TIER_DEBUG = true;

class MultiTierDashboard {
    constructor(containerSelector, options = {}) {
        this.container = document.querySelector(containerSelector);
        this.options = {
            enableRealTime: true,
            maxPatternsPerTier: 50,
            updateInterval: 100, // ms
            enableTooltips: true,
            enableFiltering: true,
            ...options
        };
        
        // Tier configuration
        this.tiers = {
            daily: {
                label: 'Daily Patterns',
                icon: '📊',
                color: '#007bff',
                patterns: new Map(),
                lastUpdate: null,
                stats: { count: 0, avgConfidence: 0, highPriority: 0 }
            },
            intraday: {
                label: 'Intraday Patterns', 
                icon: '⚡',
                color: '#28a745',
                patterns: new Map(),
                lastUpdate: null,
                stats: { count: 0, avgConfidence: 0, highPriority: 0 }
            },
            combo: {
                label: 'Combo Patterns',
                icon: '🔗',
                color: '#17a2b8',
                patterns: new Map(),
                lastUpdate: null,
                stats: { count: 0, avgConfidence: 0, highPriority: 0 }
            }
        };
        
        // WebSocket integration
        this.socket = window.socket;
        this.tierPatternService = null;
        this.subscriptions = new Set();
        
        // UI state
        this.selectedTier = null;
        this.filterState = {
            symbols: [],
            confidence: 0.6,
            priority: 'MEDIUM',
            patterns: []
        };
        
        // Performance tracking
        this.metrics = {
            renderTime: 0,
            updateCount: 0,
            lastRenderTime: null,
            avgRenderTime: 0
        };
        
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Initializing with options:', this.options);
        this.init();
    }
    
    async init() {
        try {
            if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Starting initialization...');
            
            await this.setupUI();
            if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] UI setup complete');
            
            await this.initializeTierPatternService();
            if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] TierPatternService initialized');
            
            await this.setupWebSocketIntegration();
            if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] WebSocket integration setup complete');
            
            await this.loadInitialData();
            if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Initial data loaded');
            
            if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Initialization complete');
        } catch (error) {
            console.error('[MultiTierDashboard] Initialization failed:', error);
            console.error('[MultiTierDashboard] Error details:', {
                container: !!this.container,
                tierPatternService: !!this.tierPatternService,
                globalService: !!window.tierPatternService,
                TierPatternServiceClass: typeof TierPatternService
            });
            this.showErrorState('Failed to initialize multi-tier dashboard');
        }
    }
    
    async setupUI() {
        if (!this.container) {
            throw new Error('Container element not found');
        }
        
        this.container.innerHTML = this.generateDashboardHTML();
        this.setupEventListeners();
        this.initializeTooltips();
        
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] UI setup complete');
    }
    
    generateDashboardHTML() {
        return `
            <div class="multi-tier-dashboard" data-component="multi-tier-dashboard">
                <!-- Dashboard Header -->
                <div class="dashboard-header mb-3">
                    <div class="row align-items-center">
                        <div class="col-md-6">
                            <h4 class="mb-0">
                                <i class="fas fa-layer-group me-2"></i>
                                Multi-Tier Pattern Dashboard
                            </h4>
                            <small class="text-muted">Real-time pattern monitoring across all tiers</small>
                        </div>
                        <div class="col-md-6 text-end">
                            <div class="dashboard-controls">
                                ${this.generateControlsHTML()}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Performance Metrics Bar -->
                <div class="performance-metrics mb-3">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="metric-card">
                                <small class="text-muted">Total Patterns</small>
                                <div class="metric-value" id="total-patterns">0</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-card">
                                <small class="text-muted">Avg Confidence</small>
                                <div class="metric-value" id="avg-confidence">0%</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-card">
                                <small class="text-muted">High Priority</small>
                                <div class="metric-value" id="high-priority">0</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-card">
                                <small class="text-muted">Last Update</small>
                                <div class="metric-value" id="last-update">--</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Three-Column Tier Layout -->
                <div class="tier-columns">
                    <div class="row">
                        ${Object.keys(this.tiers).map(tierKey => this.generateTierColumnHTML(tierKey)).join('')}
                    </div>
                </div>
                
                <!-- Pattern Detail Modal -->
                ${this.generatePatternModalHTML()}
            </div>
        `;
    }
    
    generateControlsHTML() {
        return `
            <div class="btn-group me-2" role="group">
                <button type="button" class="btn btn-outline-primary btn-sm" id="filter-toggle">
                    <i class="fas fa-filter"></i> Filters
                </button>
                <button type="button" class="btn btn-outline-success btn-sm" id="real-time-toggle">
                    <i class="fas fa-broadcast-tower"></i> Real-time
                </button>
                <button type="button" class="btn btn-outline-info btn-sm" id="export-data">
                    <i class="fas fa-download"></i> Export
                </button>
            </div>
            <div class="connection-status">
                <span class="status-indicator" id="connection-status" title="WebSocket Connection">
                    <i class="fas fa-circle text-success"></i>
                </span>
            </div>
        `;
    }
    
    generateTierColumnHTML(tierKey) {
        const tier = this.tiers[tierKey];
        return `
            <div class="col-md-4">
                <div class="tier-column" data-tier="${tierKey}">
                    <!-- Tier Header -->
                    <div class="tier-header" style="border-left: 4px solid ${tier.color}">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="tier-title">
                                <span class="tier-icon">${tier.icon}</span>
                                <span class="tier-label">${tier.label}</span>
                            </div>
                            <div class="tier-stats">
                                <span class="badge bg-primary" id="${tierKey}-count">0</span>
                            </div>
                        </div>
                        <div class="tier-metrics mt-2">
                            <small class="text-muted">
                                Avg: <span id="${tierKey}-avg-confidence">0%</span> | 
                                High: <span id="${tierKey}-high-priority">0</span> |
                                Updated: <span id="${tierKey}-last-update">--</span>
                            </small>
                        </div>
                    </div>
                    
                    <!-- Pattern List -->
                    <div class="pattern-list" id="${tierKey}-patterns">
                        <div class="loading-state text-center py-4">
                            <div class="spinner-border spinner-border-sm" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <div class="mt-2">Loading ${tier.label}...</div>
                        </div>
                    </div>
                    
                    <!-- Tier Footer -->
                    <div class="tier-footer">
                        <button class="btn btn-outline-primary btn-sm w-100" 
                                onclick="multiTierDashboard.showMorePatterns('${tierKey}')">
                            <i class="fas fa-chevron-down"></i> Show More
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    generatePatternModalHTML() {
        return `
            <div class="modal fade" id="patternDetailModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Pattern Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="pattern-detail-content">
                            <!-- Pattern details populated dynamically -->
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" id="subscribe-pattern">
                                <i class="fas fa-bell"></i> Subscribe to Alerts
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    async initializeTierPatternService() {
        try {
            // Use existing global tier pattern service if available
            if (window.tierPatternService) {
                this.tierPatternService = window.tierPatternService;
                if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Using existing global TierPatternService');
            } else if (typeof TierPatternService !== 'undefined') {
                // Create new service if no global one exists
                this.tierPatternService = new TierPatternService();
                await this.tierPatternService.initialize();
                if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Created new TierPatternService');
            } else {
                // Create minimal service if not available
                this.tierPatternService = this.createMockTierPatternService();
                if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Using mock TierPatternService');
            }
            
            if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Tier pattern service initialized');
        } catch (error) {
            console.error('[MultiTierDashboard] Failed to initialize tier pattern service:', error);
            this.tierPatternService = this.createMockTierPatternService();
        }
    }
    
    createMockTierPatternService() {
        return {
            initialize: async () => {},
            subscribeToTierPatterns: (tier, callback) => {
                if (MULTI_TIER_DEBUG) console.log(`[MockService] Subscribed to ${tier} patterns`);
            },
            unsubscribeFromTierPatterns: (tier) => {
                if (MULTI_TIER_DEBUG) console.log(`[MockService] Unsubscribed from ${tier} patterns`);
            },
            getTierPatterns: async (tier) => {
                return this.generateMockPatterns(tier);
            }
        };
    }
    
    async setupWebSocketIntegration() {
        if (!this.socket) {
            console.warn('[MultiTierDashboard] No WebSocket connection available');
            return;
        }
        
        // Subscribe to tier-specific pattern events
        Object.keys(this.tiers).forEach(tierKey => {
            this.socket.on(`tier_pattern_${tierKey}`, (data) => {
                this.handleTierPatternUpdate(tierKey, data);
            });
            
            this.socket.on(`tier_pattern_alert_${tierKey}`, (data) => {
                this.handleTierPatternAlert(tierKey, data);
            });
        });
        
        // Global pattern events
        this.socket.on('pattern_health_update', (data) => {
            this.updateHealthMetrics(data);
        });
        
        this.socket.on('connection_status', (data) => {
            this.updateConnectionStatus(data.connected);
        });
        
        // Request initial subscription
        this.requestTierSubscriptions();
        
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] WebSocket integration complete');
    }
    
    requestTierSubscriptions() {
        if (!this.socket) return;
        
        Object.keys(this.tiers).forEach(tierKey => {
            this.socket.emit('subscribe_tier_patterns', {
                tier: tierKey,
                filters: this.filterState,
                maxPatterns: this.options.maxPatternsPerTier
            });
            
            this.subscriptions.add(tierKey);
        });
        
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Requested tier subscriptions:', this.subscriptions);
    }
    
    async loadInitialData() {
        const startTime = performance.now();
        
        try {
            // Load patterns for each tier
            const loadPromises = Object.keys(this.tiers).map(async (tierKey) => {
                const patterns = await this.tierPatternService.getTierPatterns(tierKey);
                this.updateTierPatterns(tierKey, patterns);
            });
            
            await Promise.all(loadPromises);
            this.updateGlobalMetrics();
            
            const loadTime = performance.now() - startTime;
            if (MULTI_TIER_DEBUG) console.log(`[MultiTierDashboard] Initial data loaded in ${loadTime.toFixed(2)}ms`);
            
        } catch (error) {
            console.error('[MultiTierDashboard] Failed to load initial data:', error);
            this.showErrorState('Failed to load pattern data');
        }
    }
    
    handleTierPatternUpdate(tierKey, data) {
        const startTime = performance.now();
        
        try {
            if (data.pattern) {
                this.addPatternToTier(tierKey, data.pattern);
            } else if (data.patterns) {
                this.updateTierPatterns(tierKey, data.patterns);
            }
            
            this.updateTierStats(tierKey);
            this.updateGlobalMetrics();
            
            // Performance tracking
            const renderTime = performance.now() - startTime;
            this.metrics.renderTime = renderTime;
            this.metrics.updateCount++;
            this.metrics.lastRenderTime = Date.now();
            this.metrics.avgRenderTime = (this.metrics.avgRenderTime + renderTime) / 2;
            
            if (MULTI_TIER_DEBUG) {
                console.log(`[MultiTierDashboard] Updated ${tierKey} patterns in ${renderTime.toFixed(2)}ms`);
            }
            
        } catch (error) {
            console.error(`[MultiTierDashboard] Error handling ${tierKey} update:`, error);
        }
    }
    
    handleTierPatternAlert(tierKey, data) {
        this.showPatternAlert(tierKey, data);
        this.highlightPattern(tierKey, data.pattern_id);
    }
    
    addPatternToTier(tierKey, pattern) {
        const tier = this.tiers[tierKey];
        
        // Add pattern with timestamp
        pattern.addedAt = Date.now();
        tier.patterns.set(pattern.event_id || pattern.id, pattern);
        tier.lastUpdate = Date.now();
        
        // Limit patterns per tier
        if (tier.patterns.size > this.options.maxPatternsPerTier) {
            const oldestKey = Array.from(tier.patterns.keys())[0];
            tier.patterns.delete(oldestKey);
        }
        
        this.renderTierPatterns(tierKey);
    }
    
    updateTierPatterns(tierKey, patterns) {
        const tier = this.tiers[tierKey];
        
        // Clear existing patterns
        tier.patterns.clear();
        
        // Add new patterns
        patterns.forEach(pattern => {
            pattern.addedAt = Date.now();
            tier.patterns.set(pattern.event_id || pattern.id, pattern);
        });
        
        tier.lastUpdate = Date.now();
        this.renderTierPatterns(tierKey);
    }
    
    renderTierPatterns(tierKey) {
        const patternsContainer = document.getElementById(`${tierKey}-patterns`);
        if (!patternsContainer) return;
        
        const tier = this.tiers[tierKey];
        const patterns = Array.from(tier.patterns.values())
            .sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
        
        if (patterns.length === 0) {
            patternsContainer.innerHTML = `
                <div class="empty-state text-center py-4">
                    <div class="text-muted">
                        <i class="fas fa-search fa-2x mb-2"></i>
                        <div>No ${tier.label.toLowerCase()} found</div>
                        <small>Patterns will appear here when detected</small>
                    </div>
                </div>
            `;
            return;
        }
        
        patternsContainer.innerHTML = patterns.map(pattern => 
            this.generatePatternCardHTML(tierKey, pattern)
        ).join('');
    }
    
    generatePatternCardHTML(tierKey, pattern) {
        const confidenceColor = this.getConfidenceColor(pattern.confidence);
        const priorityBadge = this.getPriorityBadge(pattern.priority);
        const timeAgo = this.formatTimeAgo(pattern.timestamp || pattern.addedAt);
        
        return `
            <div class="pattern-card mb-2" data-pattern-id="${pattern.event_id || pattern.id}">
                <div class="card">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="pattern-info flex-grow-1">
                                <div class="pattern-header">
                                    <span class="pattern-type fw-bold">${pattern.pattern_type || 'Unknown'}</span>
                                    ${priorityBadge}
                                </div>
                                <div class="pattern-symbol">
                                    <i class="fas fa-chart-line me-1"></i>
                                    ${pattern.symbol || 'N/A'}
                                </div>
                                <div class="pattern-details mt-1">
                                    <small class="text-muted">
                                        Confidence: <span style="color: ${confidenceColor}">
                                            ${(pattern.confidence * 100).toFixed(1)}%
                                        </span> | 
                                        ${timeAgo}
                                    </small>
                                </div>
                            </div>
                            <div class="pattern-actions">
                                <button class="btn btn-outline-primary btn-sm" 
                                        onclick="multiTierDashboard.showPatternDetails('${tierKey}', '${pattern.event_id || pattern.id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateTierStats(tierKey) {
        const tier = this.tiers[tierKey];
        const patterns = Array.from(tier.patterns.values());
        
        // Calculate statistics
        tier.stats.count = patterns.length;
        tier.stats.avgConfidence = patterns.length > 0 
            ? patterns.reduce((sum, p) => sum + (p.confidence || 0), 0) / patterns.length
            : 0;
        tier.stats.highPriority = patterns.filter(p => 
            p.priority === 'HIGH' || p.priority === 'CRITICAL'
        ).length;
        
        // Update UI elements
        this.updateTierStatsUI(tierKey);
    }
    
    updateTierStatsUI(tierKey) {
        const tier = this.tiers[tierKey];
        const stats = tier.stats;
        
        // Update tier header stats
        const countElement = document.getElementById(`${tierKey}-count`);
        const avgConfidenceElement = document.getElementById(`${tierKey}-avg-confidence`);
        const highPriorityElement = document.getElementById(`${tierKey}-high-priority`);
        const lastUpdateElement = document.getElementById(`${tierKey}-last-update`);
        
        if (countElement) countElement.textContent = stats.count;
        if (avgConfidenceElement) avgConfidenceElement.textContent = `${(stats.avgConfidence * 100).toFixed(1)}%`;
        if (highPriorityElement) highPriorityElement.textContent = stats.highPriority;
        if (lastUpdateElement) lastUpdateElement.textContent = this.formatTimeAgo(tier.lastUpdate);
    }
    
    updateGlobalMetrics() {
        const totalPatterns = Object.values(this.tiers).reduce((sum, tier) => sum + tier.stats.count, 0);
        const avgConfidence = Object.values(this.tiers).reduce((sum, tier) => 
            sum + (tier.stats.avgConfidence * tier.stats.count), 0) / Math.max(totalPatterns, 1);
        const totalHighPriority = Object.values(this.tiers).reduce((sum, tier) => sum + tier.stats.highPriority, 0);
        const lastUpdate = Math.max(...Object.values(this.tiers).map(tier => tier.lastUpdate || 0));
        
        // Update global metrics UI
        const totalPatternsElement = document.getElementById('total-patterns');
        const avgConfidenceElement = document.getElementById('avg-confidence');
        const highPriorityElement = document.getElementById('high-priority');
        const lastUpdateElement = document.getElementById('last-update');
        
        if (totalPatternsElement) totalPatternsElement.textContent = totalPatterns;
        if (avgConfidenceElement) avgConfidenceElement.textContent = `${(avgConfidence * 100).toFixed(1)}%`;
        if (highPriorityElement) highPriorityElement.textContent = totalHighPriority;
        if (lastUpdateElement) lastUpdateElement.textContent = this.formatTimeAgo(lastUpdate);
    }
    
    setupEventListeners() {
        // Filter toggle
        const filterToggle = document.getElementById('filter-toggle');
        if (filterToggle) {
            filterToggle.addEventListener('click', () => this.toggleFilterPanel());
        }
        
        // Real-time toggle
        const realTimeToggle = document.getElementById('real-time-toggle');
        if (realTimeToggle) {
            realTimeToggle.addEventListener('click', () => this.toggleRealTimeUpdates());
        }
        
        // Export data
        const exportButton = document.getElementById('export-data');
        if (exportButton) {
            exportButton.addEventListener('click', () => this.exportPatternData());
        }
        
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Event listeners setup complete');
    }
    
    initializeTooltips() {
        // Initialize Bootstrap tooltips if enabled
        if (this.options.enableTooltips) {
            // Find all elements with title attributes and enable tooltips
            const tooltipElements = this.container.querySelectorAll('[title]');
            
            tooltipElements.forEach(element => {
                // Use native browser tooltip behavior for now
                // Can be enhanced with Bootstrap tooltips later if needed
                element.setAttribute('data-bs-toggle', 'tooltip');
            });
            
            if (MULTI_TIER_DEBUG) {
                console.log(`[MultiTierDashboard] Initialized tooltips for ${tooltipElements.length} elements`);
            }
        }
    }
    
    // Utility methods
    getConfidenceColor(confidence) {
        if (confidence >= 0.8) return '#28a745'; // Green
        if (confidence >= 0.6) return '#ffc107'; // Yellow
        return '#dc3545'; // Red
    }
    
    getPriorityBadge(priority) {
        const badges = {
            'CRITICAL': '<span class="badge bg-danger">Critical</span>',
            'HIGH': '<span class="badge bg-warning">High</span>',
            'MEDIUM': '<span class="badge bg-info">Medium</span>',
            'LOW': '<span class="badge bg-secondary">Low</span>'
        };
        return badges[priority] || badges['MEDIUM'];
    }
    
    formatTimeAgo(timestamp) {
        if (!timestamp) return '--';
        
        const now = Date.now();
        const diff = now - timestamp;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return new Date(timestamp).toLocaleDateString();
    }
    
    generateMockPatterns(tier) {
        // Generate mock patterns for testing
        const symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN'];
        const patternTypes = ['BreakoutBO', 'TrendReversal', 'SurgeDetection', 'SupportBreak'];
        const priorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
        
        return Array.from({ length: 5 + Math.floor(Math.random() * 10) }, (_, i) => ({
            event_id: `${tier}_${Date.now()}_${i}`,
            pattern_type: patternTypes[Math.floor(Math.random() * patternTypes.length)],
            symbol: symbols[Math.floor(Math.random() * symbols.length)],
            tier: tier.toUpperCase(),
            confidence: 0.5 + Math.random() * 0.5,
            priority: priorities[Math.floor(Math.random() * priorities.length)],
            timestamp: Date.now() - Math.random() * 3600000 // Within last hour
        }));
    }
    
    showErrorState(message) {
        if (this.container) {
            this.container.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            `;
        }
    }
    
    // Public API methods
    showPatternDetails(tierKey, patternId) {
        // Implementation for pattern detail modal
        if (MULTI_TIER_DEBUG) console.log(`[MultiTierDashboard] Show details for ${tierKey}:${patternId}`);
    }
    
    showMorePatterns(tierKey) {
        // Implementation for showing more patterns
        if (MULTI_TIER_DEBUG) console.log(`[MultiTierDashboard] Show more patterns for ${tierKey}`);
    }
    
    toggleFilterPanel() {
        // Implementation for filter panel
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Toggle filter panel');
    }
    
    toggleRealTimeUpdates() {
        this.options.enableRealTime = !this.options.enableRealTime;
        const button = document.getElementById('real-time-toggle');
        if (button) {
            button.classList.toggle('active');
        }
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Real-time updates:', this.options.enableRealTime);
    }
    
    exportPatternData() {
        // Implementation for data export
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Export pattern data');
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('connection-status');
        if (statusIndicator) {
            const icon = statusIndicator.querySelector('i');
            if (connected) {
                icon.className = 'fas fa-circle text-success';
                statusIndicator.title = 'Connected to WebSocket';
            } else {
                icon.className = 'fas fa-circle text-danger';
                statusIndicator.title = 'Disconnected from WebSocket';
            }
        }
    }
    
    destroy() {
        // Cleanup WebSocket subscriptions
        if (this.socket) {
            Object.keys(this.tiers).forEach(tierKey => {
                this.socket.off(`tier_pattern_${tierKey}`);
                this.socket.off(`tier_pattern_alert_${tierKey}`);
            });
            this.socket.off('pattern_health_update');
            this.socket.off('connection_status');
        }
        
        // Clear subscriptions
        this.subscriptions.clear();
        
        if (MULTI_TIER_DEBUG) console.log('[MultiTierDashboard] Component destroyed');
    }
}

// Initialize as global variable for easy access
let multiTierDashboard = null;

// Auto-initialization when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const dashboardContainer = document.querySelector('[data-component="multi-tier-dashboard-container"]');
    if (dashboardContainer) {
        multiTierDashboard = new MultiTierDashboard('[data-component="multi-tier-dashboard-container"]');
    }
});

// Make available globally
if (typeof window !== 'undefined') {
    window.MultiTierDashboard = MultiTierDashboard;
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MultiTierDashboard;
}