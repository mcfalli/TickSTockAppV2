// ==========================================================================
// TICKSTOCK DASHBOARD MANAGER - SPRINT 12
// ==========================================================================
// VERSION: 1.0.0 - Sprint 12 Dashboard Tab Implementation
// PURPOSE: Dashboard tab functionality with watchlist and market summary
// ==========================================================================

class DashboardManager {
    constructor() {
        this.watchlist = [];
        this.marketSummary = {
            totalSymbols: 0,
            symbolsUp: 0,
            symbolsDown: 0,
            lastUpdate: null
        };
        this.priceData = new Map();
        this.isInitialized = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadWatchlist();
        this.updateMarketSummary();
        this.isInitialized = true;
        console.log('[DashboardManager] Initialized');
    }

    setupEventListeners() {
        // Add symbol button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'add-symbol-btn' || e.target.closest('#add-symbol-btn')) {
                this.showAddSymbolDialog();
            }
        });

        // Clear alerts button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'clear-alerts-btn' || e.target.closest('#clear-alerts-btn')) {
                this.clearAllAlerts();
            }
        });

        // Watchlist item interactions
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-symbol-btn')) {
                const symbol = e.target.getAttribute('data-symbol');
                this.removeFromWatchlist(symbol);
            }
        });
    }

    async loadWatchlist() {
        try {
            const response = await fetch('/api/watchlist', {
                headers: {
                    'X-CSRFToken': window.csrfToken || ''
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.watchlist = data.symbols || [];
                    console.log('[DashboardManager] Loaded watchlist:', this.watchlist);
                    this.renderWatchlist();
                    this.subscribeToWatchlistUpdates();
                    
                    // Load initial market summary
                    this.loadMarketSummary();
                    
                    // Populate chart symbol dropdown
                    if (window.chartManager) {
                        window.chartManager.populateSymbolDropdown(this.watchlist);
                    }
                } else {
                    console.error('[DashboardManager] Watchlist API error:', data.message);
                }
            }
        } catch (error) {
            console.error('[DashboardManager] Error loading watchlist:', error);
        }
    }

    renderWatchlist() {
        const container = document.getElementById('watchlist-container');
        if (!container) return;

        if (this.watchlist.length === 0) {
            container.innerHTML = `
                <div class="text-center p-3 text-muted">
                    <i class="fas fa-chart-line fa-2x mb-2"></i>
                    <p class="mb-0">Add symbols to start tracking</p>
                </div>
            `;
            return;
        }

        const html = this.watchlist.map(symbol => {
            const priceInfo = this.priceData.get(symbol.symbol) || {};
            const currentPrice = priceInfo.price || symbol.last_price || 0;
            const change = priceInfo.change || 0;
            const changePercent = priceInfo.changePercent || 0;
            const isPositive = change >= 0;

            return `
                <div class="watchlist-item" data-symbol="${symbol.symbol}">
                    <div class="symbol-info">
                        <div class="symbol-name">${symbol.symbol}</div>
                        <div class="symbol-company">${symbol.name || 'Unknown Company'}</div>
                    </div>
                    <div class="price-info">
                        <div class="current-price">$${currentPrice.toFixed(2)}</div>
                        <div class="price-change ${isPositive ? 'positive' : 'negative'}">
                            ${isPositive ? '+' : ''}${change.toFixed(2)} (${isPositive ? '+' : ''}${changePercent.toFixed(2)}%)
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-danger remove-symbol-btn" data-symbol="${symbol.symbol}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    async showAddSymbolDialog() {
        try {
            // Load available symbols
            const response = await fetch('/api/symbols/search', {
                headers: {
                    'X-CSRFToken': window.csrfToken || ''
                }
            });

            let symbols = [];
            if (response.ok) {
                const data = await response.json();
                symbols = data.symbols || [];
            }

            // Show SweetAlert2 dialog
            const { value: selectedSymbol } = await Swal.fire({
                title: 'Add Symbol to Watchlist',
                input: 'select',
                inputOptions: symbols.reduce((options, symbol) => {
                    options[symbol.symbol] = `${symbol.symbol} - ${symbol.name || 'Unknown'}`;
                    return options;
                }, { '': 'Select a symbol...' }),
                inputPlaceholder: 'Select a symbol',
                showCancelButton: true,
                confirmButtonText: 'Add to Watchlist',
                inputValidator: (value) => {
                    if (!value) return 'Please select a symbol';
                    if (this.watchlist.some(s => s.symbol === value)) {
                        return 'Symbol already in watchlist';
                    }
                }
            });

            if (selectedSymbol) {
                await this.addToWatchlist(selectedSymbol);
            }
        } catch (error) {
            console.error('[DashboardManager] Error showing add symbol dialog:', error);
            Swal.fire('Error', 'Failed to load symbols', 'error');
        }
    }

    async addToWatchlist(symbol) {
        try {
            const response = await fetch('/api/watchlist/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken || ''
                },
                body: JSON.stringify({ symbol })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    await this.loadWatchlist(); // Reload watchlist
                    Swal.fire('Success', `${symbol} added to watchlist`, 'success');
                } else {
                    Swal.fire('Error', data.message || 'Failed to add symbol', 'error');
                }
            }
        } catch (error) {
            console.error('[DashboardManager] Error adding symbol:', error);
            Swal.fire('Error', 'Network error adding symbol', 'error');
        }
    }

    async removeFromWatchlist(symbol) {
        try {
            const result = await Swal.fire({
                title: 'Remove Symbol?',
                text: `Remove ${symbol} from your watchlist?`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Remove',
                confirmButtonColor: '#dc3545'
            });

            if (result.isConfirmed) {
                const response = await fetch('/api/watchlist/remove', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.csrfToken || ''
                    },
                    body: JSON.stringify({ symbol })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        await this.loadWatchlist(); // Reload watchlist
                        
                        // Update chart dropdown immediately
                        if (window.chartManager) {
                            window.chartManager.populateSymbolDropdown(this.watchlist);
                        }
                        
                        Swal.fire('Removed', `${symbol} removed from watchlist`, 'success');
                    } else {
                        Swal.fire('Error', data.message || 'Failed to remove symbol', 'error');
                    }
                }
            }
        } catch (error) {
            console.error('[DashboardManager] Error removing symbol:', error);
            Swal.fire('Error', 'Network error removing symbol', 'error');
        }
    }

    subscribeToWatchlistUpdates() {
        // Request real-time updates for watchlist symbols
        if (window.socket && this.watchlist.length > 0) {
            const symbols = this.watchlist.map(s => s.symbol);
            window.socket.emit('subscribe_watchlist', { symbols });
        }
    }

    // Handle real-time price updates from WebSocket
    updatePrice(symbol, priceData) {
        this.priceData.set(symbol, priceData);
        
        // Update watchlist display
        this.renderWatchlist();
        
        // Update market summary
        this.updateMarketSummaryFromPrices();
        
        // Update chart if this symbol is selected
        if (window.chartManager) {
            window.chartManager.updateRealTimePrice(symbol, priceData);
        }
    }

    loadMarketSummary() {
        // Load initial market summary with mock data
        this.marketSummary = {
            totalSymbols: this.watchlist.length,
            symbolsUp: Math.floor(this.watchlist.length * 0.6), // 60% up
            symbolsDown: Math.floor(this.watchlist.length * 0.4), // 40% down
            lastUpdate: new Date().toLocaleTimeString()
        };
        this.updateMarketSummary();
        
        // Start simulated real-time updates
        this.startSimulatedUpdates();
    }

    updateMarketSummary() {
        const elements = {
            totalSymbols: document.getElementById('total-symbols'),
            symbolsUp: document.getElementById('symbols-up'),
            symbolsDown: document.getElementById('symbols-down'),
            lastUpdate: document.getElementById('last-update')
        };

        if (elements.totalSymbols) {
            elements.totalSymbols.textContent = this.marketSummary.totalSymbols.toLocaleString();
        }
        if (elements.symbolsUp) {
            elements.symbolsUp.textContent = this.marketSummary.symbolsUp.toLocaleString();
        }
        if (elements.symbolsDown) {
            elements.symbolsDown.textContent = this.marketSummary.symbolsDown.toLocaleString();
        }
        if (elements.lastUpdate) {
            elements.lastUpdate.textContent = this.marketSummary.lastUpdate || 'Never';
        }
    }

    updateMarketSummaryFromPrices() {
        let up = 0, down = 0;
        
        this.priceData.forEach(priceInfo => {
            if (priceInfo.change > 0) up++;
            else if (priceInfo.change < 0) down++;
        });

        this.marketSummary.symbolsUp = up;
        this.marketSummary.symbolsDown = down;
        this.marketSummary.totalSymbols = this.watchlist.length;
        this.marketSummary.lastUpdate = new Date().toLocaleTimeString();

        this.updateMarketSummary();
    }

    // Alerts functionality
    addAlert(alert) {
        const alertsList = document.getElementById('alerts-list');
        if (!alertsList) return;

        // Remove empty state if present
        if (alertsList.querySelector('.text-center')) {
            alertsList.innerHTML = '';
        }

        const alertHtml = `
            <div class="alert-item" data-alert-id="${alert.id}">
                <div class="alert-icon">
                    <i class="fas ${this.getAlertIcon(alert.type)}"></i>
                </div>
                <div class="alert-content">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-description">${alert.description}</div>
                    <div class="alert-time">${new Date(alert.timestamp).toLocaleString()}</div>
                </div>
            </div>
        `;

        alertsList.insertAdjacentHTML('afterbegin', alertHtml);
    }

    getAlertIcon(alertType) {
        switch (alertType) {
            case 'price_alert': return 'fa-dollar-sign';
            case 'volume_alert': return 'fa-chart-bar';
            case 'trend_alert': return 'fa-chart-line';
            default: return 'fa-bell';
        }
    }

    clearAllAlerts() {
        const alertsList = document.getElementById('alerts-list');
        if (!alertsList) return;

        alertsList.innerHTML = `
            <div class="text-center p-3 text-muted">
                <i class="fas fa-bell-slash fa-2x mb-2"></i>
                <p class="mb-0">No recent alerts</p>
            </div>
        `;
    }

    // Update symbol metadata (Phase 2 feature)
    updateSymbolMetadata(symbol, metadata) {
        // Update watchlist item if it exists
        const watchlistItem = this.watchlist.find(item => item.symbol === symbol);
        if (watchlistItem && metadata.name) {
            watchlistItem.name = metadata.name;
            this.renderWatchlist(); // Re-render to show updated name
        }
    }

    // Enhanced subscription management (Phase 2)
    subscribeToWatchlistUpdates() {
        // Request real-time updates for watchlist symbols
        if (window.socket && this.watchlist.length > 0) {
            const symbols = this.watchlist.map(s => s.symbol);
            
            // Use new TickStockPL subscription event
            window.socket.emit('subscribe_tickstockpl_watchlist', { 
                symbols,
                user_id: window.userContext.userId,
                subscription_types: ['price_update', 'pattern_alert', 'volume_spike']
            });
        }
    }

    // Enhanced price update with performance tracking (Phase 2)
    updatePrice(symbol, priceData) {
        const startTime = performance.now();
        
        this.priceData.set(symbol, priceData);
        
        // Update watchlist display
        this.renderWatchlist();
        
        // Update market summary
        this.updateMarketSummaryFromPrices();
        
        // Update chart if this symbol is selected
        if (window.chartManager) {
            window.chartManager.updateRealTimePrice(symbol, priceData);
        }

        // Performance tracking
        const processingTime = performance.now() - startTime;
        if (processingTime > 25) {
            console.warn(`[DashboardManager] Slow price update processing: ${processingTime.toFixed(2)}ms for ${symbol}`);
        }
    }

    // Get performance metrics (Phase 2)
    getPerformanceMetrics() {
        return {
            watchlistSize: this.watchlist.length,
            priceDataSize: this.priceData.size,
            lastMarketUpdate: this.marketSummary.lastUpdate,
            memoryUsage: this.estimateMemoryUsage()
        };
    }

    estimateMemoryUsage() {
        // Rough estimate of memory usage in KB
        const watchlistMemory = this.watchlist.length * 0.5; // ~500 bytes per symbol
        const priceDataMemory = this.priceData.size * 0.3; // ~300 bytes per price entry
        return Math.round(watchlistMemory + priceDataMemory);
    }

    // Simulated real-time updates for testing
    startSimulatedUpdates() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
        }
        
        // Only start simulation if we have symbols in watchlist
        if (this.watchlist.length === 0) return;
        
        console.log('[DashboardManager] Starting simulated real-time updates');
        
        // Update prices every 3 seconds
        this.simulationInterval = setInterval(() => {
            this.simulateRealTimeUpdates();
        }, 3000);
        
        // Generate a test alert after 5 seconds
        setTimeout(() => {
            this.generateTestAlert();
        }, 5000);
    }
    
    simulateRealTimeUpdates() {
        if (this.watchlist.length === 0) return;
        
        // Simulate price updates for each symbol
        this.watchlist.forEach(symbolData => {
            const symbol = symbolData.symbol || symbolData;
            
            // Generate realistic price movement
            const basePrice = this.getBasePriceForSymbol(symbol);
            const priceChange = (Math.random() - 0.5) * 4; // -2 to +2
            const newPrice = Math.max(0.01, basePrice + priceChange);
            const changePercent = ((newPrice - basePrice) / basePrice) * 100;
            
            const priceData = {
                price: newPrice,
                change: priceChange,
                changePercent: changePercent,
                volume: Math.floor(Math.random() * 1000000) + 100000,
                timestamp: Date.now()
            };
            
            // Update the price display
            this.updatePrice(symbol, priceData);
        });
        
        // Update market summary timestamp
        this.marketSummary.lastUpdate = new Date().toLocaleTimeString();
        this.updateMarketSummary();
    }
    
    getBasePriceForSymbol(symbol) {
        const basePrices = {
            'AAPL': 150,
            'GOOGL': 2500,
            'MSFT': 300,
            'TSLA': 200,
            'AMZN': 3000,
            'NVDA': 400,
            'META': 250,
            'NFLX': 400
        };
        return basePrices[symbol] || 100;
    }
    
    generateTestAlert() {
        if (!this.watchlist.length) return;
        
        const randomSymbol = this.watchlist[Math.floor(Math.random() * this.watchlist.length)];
        const symbol = randomSymbol.symbol || randomSymbol;
        
        const alertTypes = ['bullish_engulfing', 'bearish_reversal', 'volume_spike', 'breakout'];
        const randomAlert = alertTypes[Math.floor(Math.random() * alertTypes.length)];
        
        this.addAlert({
            id: Date.now(),
            type: 'pattern_alert',
            title: `${randomAlert.replace('_', ' ')} - ${symbol}`,
            description: `${randomAlert.replace('_', ' ')} pattern detected in ${symbol}`,
            timestamp: Date.now(),
            symbol: symbol
        });
        
        console.log('[DashboardManager] Generated test alert for', symbol);
        
        // Generate another alert in 30 seconds
        setTimeout(() => {
            this.generateTestAlert();
        }, 30000);
    }

    destroy() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
        }
        this.watchlist = [];
        this.priceData.clear();
        this.isInitialized = false;
    }
}

// Global dashboard manager instance
let dashboardManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    dashboardManager = new DashboardManager();
});