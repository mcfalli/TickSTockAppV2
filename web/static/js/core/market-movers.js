// ==========================================================================
// TICKSTOCK MARKET MOVERS WIDGET - CONSUMER PATTERN IMPLEMENTATION
// ==========================================================================
// VERSION: 1.0.0 - Sprint 10 Market Movers Widget
// PURPOSE: Display top gainers/losers following TickStockApp consumer pattern
// PERFORMANCE TARGET: <100ms WebSocket delivery, <50ms UI updates
// ==========================================================================

class MarketMoversManager {
    constructor() {
        this.refreshInterval = null;
        this.refreshIntervalMs = 60000; // 60 seconds auto-refresh
        this.isLoading = false;
        this.lastUpdateTime = null;
        this.performanceMetrics = {
            apiCalls: 0,
            totalResponseTime: 0,
            errors: 0,
            lastUpdateDuration: 0
        };
        this.retryCount = 0;
        this.maxRetries = 3;
        this.retryDelay = 2000; // 2 seconds
        
        this.init();
    }

    init() {
        console.log('[MarketMoversManager] Initializing...');
        
        // Initial load
        this.loadMarketMovers();
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Setup WebSocket listeners for real-time updates (Sprint 10 Phase 2)
        this.setupWebSocketListeners();
        
        console.log('[MarketMoversManager] Initialized with %dms refresh interval', this.refreshIntervalMs);
    }

    async loadMarketMovers() {
        if (this.isLoading) {
            console.log('[MarketMoversManager] Load already in progress, skipping...');
            return;
        }

        this.isLoading = true;
        const startTime = performance.now();
        
        try {
            this.showLoadingState();
            
            const response = await fetch('/api/market-movers', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken || ''
                },
                cache: 'no-cache' // Ensure fresh data
            });

            const responseTime = performance.now() - startTime;
            this.performanceMetrics.apiCalls++;
            this.performanceMetrics.totalResponseTime += responseTime;
            this.performanceMetrics.lastUpdateDuration = responseTime;

            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    this.renderMarketMovers(data.data);
                    this.lastUpdateTime = new Date();
                    this.retryCount = 0; // Reset retry count on success
                    
                    console.log('[MarketMoversManager] Data loaded: %d gainers, %d losers (%.2fms)', 
                              data.data.gainers.length, 
                              data.data.losers.length, 
                              responseTime);
                } else {
                    throw new Error(data.error || 'API returned error status');
                }
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

        } catch (error) {
            this.performanceMetrics.errors++;
            this.handleLoadError(error);
            console.error('[MarketMoversManager] Load error:', error);
        } finally {
            this.isLoading = false;
        }
    }

    renderMarketMovers(data) {
        const container = document.getElementById('market-movers-content');
        if (!container) {
            console.error('[MarketMoversManager] Container not found');
            return;
        }

        try {
            // Hide loading state
            const loadingState = container.querySelector('.loading-state');
            if (loadingState) {
                loadingState.style.display = 'none';
            }

            // Show market movers list
            let listContainer = container.querySelector('.market-movers-list');
            if (!listContainer) {
                listContainer = document.createElement('div');
                listContainer.className = 'market-movers-list';
                container.appendChild(listContainer);
            }
            listContainer.style.display = 'block';

            // Render the data
            const html = this.generateMarketMoversHTML(data);
            listContainer.innerHTML = html;

            // Update last updated time
            this.updateLastUpdatedTime();

        } catch (error) {
            console.error('[MarketMoversManager] Render error:', error);
            this.showErrorState('Failed to display market movers data');
        }
    }

    generateMarketMoversHTML(data) {
        const gainers = data.gainers || [];
        const losers = data.losers || [];

        if (gainers.length === 0 && losers.length === 0) {
            return `
                <div class="text-center p-3 text-muted">
                    <i class="fas fa-chart-line fa-2x mb-2"></i>
                    <p class="mb-0">No market movers data available</p>
                </div>
            `;
        }

        return `
            <div class="market-movers-tabs">
                <ul class="nav nav-pills nav-fill mb-3" id="market-movers-tabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="gainers-tab" data-bs-toggle="pill" 
                                data-bs-target="#gainers-content" type="button" role="tab">
                            <i class="fas fa-arrow-up text-success me-1"></i>
                            Gainers (${gainers.length})
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="losers-tab" data-bs-toggle="pill" 
                                data-bs-target="#losers-content" type="button" role="tab">
                            <i class="fas fa-arrow-down text-danger me-1"></i>
                            Losers (${losers.length})
                        </button>
                    </li>
                </ul>
                <div class="tab-content" id="market-movers-tab-content">
                    <div class="tab-pane fade show active" id="gainers-content" role="tabpanel">
                        ${this.generateMoversListHTML(gainers, 'gainer')}
                    </div>
                    <div class="tab-pane fade" id="losers-content" role="tabpanel">
                        ${this.generateMoversListHTML(losers, 'loser')}
                    </div>
                </div>
            </div>
            <div class="market-movers-footer mt-2">
                <small class="text-muted">
                    <i class="fas fa-clock me-1"></i>
                    Last updated: <span id="market-movers-last-update">Just now</span>
                </small>
            </div>
        `;
    }

    generateMoversListHTML(movers, type) {
        if (movers.length === 0) {
            return `
                <div class="text-center p-3 text-muted">
                    <p class="mb-0">No ${type}s found</p>
                </div>
            `;
        }

        // Show top 5 movers to fit in widget space
        const topMovers = movers.slice(0, 5);

        return `
            <div class="movers-list">
                ${topMovers.map(mover => this.generateMoverItemHTML(mover, type)).join('')}
            </div>
            ${movers.length > 5 ? `
                <div class="text-center mt-2">
                    <small class="text-muted">Showing top 5 of ${movers.length} ${type}s</small>
                </div>
            ` : ''}
        `;
    }

    generateMoverItemHTML(mover, type) {
        const isGainer = type === 'gainer';
        const changeClass = isGainer ? 'text-success' : 'text-danger';
        const changeIcon = isGainer ? 'fa-arrow-up' : 'fa-arrow-down';
        const changePrefix = isGainer ? '+' : '';

        return `
            <div class="mover-item d-flex align-items-center justify-content-between py-2 px-1 border-bottom border-light">
                <div class="mover-info flex-grow-1">
                    <div class="d-flex align-items-center">
                        <span class="mover-symbol fw-bold me-2">${mover.symbol}</span>
                        <i class="fas ${changeIcon} ${changeClass} me-1" style="font-size: 0.75rem;"></i>
                        <span class="mover-change ${changeClass} fw-bold" style="font-size: 0.85rem;">
                            ${changePrefix}${mover.change_percent.toFixed(2)}%
                        </span>
                    </div>
                    <div class="mover-name text-muted" style="font-size: 0.75rem;">
                        ${this.truncateText(mover.name, 25)}
                    </div>
                </div>
                <div class="mover-price text-end">
                    <div class="current-price fw-bold" style="font-size: 0.9rem;">
                        $${mover.price.toFixed(2)}
                    </div>
                    <div class="price-change ${changeClass}" style="font-size: 0.75rem;">
                        ${changePrefix}${mover.change.toFixed(2)}
                    </div>
                </div>
            </div>
        `;
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }

    showLoadingState() {
        const container = document.getElementById('market-movers-content');
        if (!container) return;

        // Show loading state
        let loadingState = container.querySelector('.loading-state');
        if (loadingState) {
            loadingState.style.display = 'block';
        }

        // Hide market movers list
        const listContainer = container.querySelector('.market-movers-list');
        if (listContainer) {
            listContainer.style.display = 'none';
        }
    }

    showErrorState(message) {
        const container = document.getElementById('market-movers-content');
        if (!container) return;

        container.innerHTML = `
            <div class="error-state text-center p-3">
                <i class="fas fa-exclamation-triangle text-warning fa-2x mb-2"></i>
                <p class="text-muted mb-2">${message}</p>
                <button class="btn btn-sm btn-outline-primary" id="market-movers-retry-btn">
                    <i class="fas fa-redo me-1"></i>Retry
                </button>
            </div>
        `;

        // Add retry button handler
        const retryBtn = container.querySelector('#market-movers-retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.retryLoad();
            });
        }
    }

    async retryLoad() {
        if (this.retryCount >= this.maxRetries) {
            console.warn('[MarketMoversManager] Max retries exceeded');
            this.showErrorState('Failed to load data after multiple attempts');
            return;
        }

        this.retryCount++;
        console.log('[MarketMoversManager] Retrying load (%d/%d)...', this.retryCount, this.maxRetries);
        
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, this.retryDelay));
        
        this.loadMarketMovers();
    }

    handleLoadError(error) {
        console.error('[MarketMoversManager] Error loading market movers:', error);
        
        // Determine error type and show appropriate message
        let errorMessage = 'Failed to load market movers';
        
        if (error.message.includes('fetch')) {
            errorMessage = 'Network error - check connection';
        } else if (error.message.includes('HTTP 40')) {
            errorMessage = 'Authorization error - please refresh page';
        } else if (error.message.includes('HTTP 50')) {
            errorMessage = 'Server error - please try again';
        }

        this.showErrorState(errorMessage);
    }

    updateLastUpdatedTime() {
        const element = document.getElementById('market-movers-last-update');
        if (element && this.lastUpdateTime) {
            element.textContent = this.lastUpdateTime.toLocaleTimeString();
        }
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        this.refreshInterval = setInterval(() => {
            console.log('[MarketMoversManager] Auto-refresh triggered');
            this.loadMarketMovers();
        }, this.refreshIntervalMs);

        console.log('[MarketMoversManager] Auto-refresh started (every %ds)', this.refreshIntervalMs / 1000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('[MarketMoversManager] Auto-refresh stopped');
        }
    }

    setupWebSocketListeners() {
        // Sprint 10 Phase 2: WebSocket integration for real-time updates
        if (window.socket) {
            // Listen for market movers updates from TickStockPL
            window.socket.on('market_movers_update', (data) => {
                console.log('[MarketMoversManager] Real-time update received:', data);
                this.handleRealtimeUpdate(data);
            });

            // Subscribe to market movers updates
            window.socket.emit('subscribe_market_movers', {
                user_id: window.userContext?.userId
            });
        } else {
            console.log('[MarketMoversManager] WebSocket not available - using polling only');
        }
    }

    handleRealtimeUpdate(data) {
        // Sprint 10 Phase 2: Handle real-time market movers updates
        if (data && data.market_movers) {
            console.log('[MarketMoversManager] Applying real-time update');
            this.renderMarketMovers(data.market_movers);
            this.lastUpdateTime = new Date();
        }
    }

    // Performance and metrics
    getPerformanceMetrics() {
        return {
            ...this.performanceMetrics,
            avgResponseTime: this.performanceMetrics.apiCalls > 0 ? 
                (this.performanceMetrics.totalResponseTime / this.performanceMetrics.apiCalls) : 0,
            errorRate: this.performanceMetrics.apiCalls > 0 ? 
                (this.performanceMetrics.errors / this.performanceMetrics.apiCalls) : 0,
            lastUpdate: this.lastUpdateTime,
            refreshInterval: this.refreshIntervalMs,
            isLoading: this.isLoading
        };
    }

    // Manual refresh method
    refresh() {
        console.log('[MarketMoversManager] Manual refresh triggered');
        this.loadMarketMovers();
    }

    // Cleanup method
    destroy() {
        this.stopAutoRefresh();
        
        if (window.socket) {
            window.socket.off('market_movers_update');
            window.socket.emit('unsubscribe_market_movers');
        }
        
        console.log('[MarketMoversManager] Destroyed');
    }
}

// Global market movers manager instance
let marketMoversManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit to ensure other components are initialized
    setTimeout(() => {
        marketMoversManager = new MarketMoversManager();
        
        // Make available globally for debugging and manual control
        window.marketMoversManager = marketMoversManager;
    }, 1000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (marketMoversManager) {
        marketMoversManager.destroy();
    }
});