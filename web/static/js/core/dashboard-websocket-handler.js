// ==========================================================================
// TICKSTOCK DASHBOARD WEBSOCKET HANDLER - SPRINT 12 PHASE 2
// ==========================================================================
// VERSION: 1.0.0 - Sprint 12 Phase 2 Real-time Integration
// PURPOSE: Handle real-time WebSocket events for dashboard components
// ==========================================================================

// Debug flag for development
const DASHBOARD_WEBSOCKET_DEBUG = false;

class DashboardWebSocketHandler {
    constructor(dashboardManager, chartManager) {
        this.dashboardManager = dashboardManager;
        this.chartManager = chartManager;
        this.socket = window.socket;
        this.isConnected = false;
        this.messageBuffer = [];
        this.lastUpdateTimes = new Map();
        this.performanceMetrics = {
            messagesReceived: 0,
            averageLatency: 0,
            lastUpdateTime: null
        };
        
        this.init();
    }

    init() {
        if (!this.socket) {
            console.error('[DashboardWebSocketHandler] No socket connection available');
            return;
        }

        this.setupEventHandlers();
        this.subscribeToWatchlist();
        if (DASHBOARD_WEBSOCKET_DEBUG) console.log('[DashboardWebSocketHandler] Initialized with real-time handlers');
    }

    setupEventHandlers() {
        // Real-time price updates from TickStockPL
        this.socket.on('tickstockpl_price_update', (data) => {
            this.handlePriceUpdate(data);
        });

        // OHLCV bar updates for charts
        this.socket.on('tickstockpl_ohlcv_update', (data) => {
            this.handleOHLCVUpdate(data);
        });

        // Pattern-based alerts
        this.socket.on('tickstockpl_pattern_alert', (data) => {
            this.handlePatternAlert(data);
        });

        // Market summary updates
        this.socket.on('tickstockpl_market_summary', (data) => {
            this.handleMarketSummary(data);
        });

        // Volume spike notifications
        this.socket.on('tickstockpl_volume_spike', (data) => {
            this.handleVolumeSpike(data);
        });

        // Symbol metadata updates
        this.socket.on('tickstockpl_symbol_metadata', (data) => {
            this.handleSymbolMetadata(data);
        });

        // Connection status handlers
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.processBufferedMessages();
            this.subscribeToWatchlist();
        });

        this.socket.on('disconnect', () => {
            this.isConnected = false;
        });
    }

    handlePriceUpdate(data) {
        const startTime = performance.now();
        
        try {
            if (!data.symbol || data.price === undefined) {
                console.warn('[DashboardWebSocketHandler] Invalid price update data:', data);
                return;
            }

            // Check if this symbol is in user's watchlist
            if (this.dashboardManager && this.dashboardManager.watchlist) {
                const isWatchlisted = this.dashboardManager.watchlist.some(
                    item => item.symbol === data.symbol
                );

                if (isWatchlisted) {
                    // Update dashboard with real-time price
                    this.dashboardManager.updatePrice(data.symbol, {
                        price: data.price,
                        change: data.change || 0,
                        changePercent: data.change_percent || 0,
                        volume: data.volume || 0,
                        timestamp: data.timestamp || Date.now(),
                        bid: data.bid,
                        ask: data.ask
                    });

                    // Update chart if this symbol is active
                    if (this.chartManager && this.chartManager.currentSymbol === data.symbol) {
                        this.chartManager.updateRealTimePrice(data.symbol, {
                            price: data.price,
                            volume: data.volume,
                            timestamp: data.timestamp
                        });
                    }
                }
            }

            this.updatePerformanceMetrics(startTime, 'price_update');
        } catch (error) {
            console.error('[DashboardWebSocketHandler] Error handling price update:', error);
        }
    }

    handleOHLCVUpdate(data) {
        const startTime = performance.now();

        try {
            if (!data.symbol || !data.ohlcv) {
                console.warn('[DashboardWebSocketHandler] Invalid OHLCV data:', data);
                return;
            }

            // Update chart with new OHLCV bar
            if (this.chartManager && this.chartManager.currentSymbol === data.symbol) {
                this.chartManager.addNewOHLCVBar({
                    timestamp: data.ohlcv.timestamp || data.timestamp,
                    open: data.ohlcv.open,
                    high: data.ohlcv.high,
                    low: data.ohlcv.low,
                    close: data.ohlcv.close,
                    volume: data.ohlcv.volume
                });
            }

            // Update current price in dashboard
            const isWatchlisted = this.dashboardManager && this.dashboardManager.watchlist &&
                this.dashboardManager.watchlist.some(item => item.symbol === data.symbol);

            if (isWatchlisted) {
                this.dashboardManager.updatePrice(data.symbol, {
                    price: data.ohlcv.close,
                    volume: data.ohlcv.volume,
                    timestamp: data.timestamp || Date.now()
                });
            }

            this.updatePerformanceMetrics(startTime, 'ohlcv_update');
        } catch (error) {
            console.error('[DashboardWebSocketHandler] Error handling OHLCV update:', error);
        }
    }

    handlePatternAlert(data) {
        const startTime = performance.now();

        try {
            if (!data.pattern || !data.symbol) {
                console.warn('[DashboardWebSocketHandler] Invalid pattern alert:', data);
                return;
            }

            // Add alert to dashboard alerts tab
            if (this.dashboardManager) {
                this.dashboardManager.addAlert({
                    id: data.alert_id || Date.now(),
                    type: 'pattern_alert',
                    title: `${data.pattern.name} - ${data.symbol}`,
                    description: data.pattern.description || `${data.pattern.name} pattern detected`,
                    timestamp: data.timestamp || Date.now(),
                    symbol: data.symbol,
                    pattern: data.pattern.name,
                    confidence: data.pattern.confidence,
                    show_notification: true
                });
            }

            // Show browser notification if enabled
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification(`TickStock Pattern Alert`, {
                    body: `${data.pattern.name} detected in ${data.symbol}`,
                    icon: '/static/images/tickstock-icon.png',
                    tag: `pattern-${data.symbol}-${data.pattern.name}`
                });
            }

            this.updatePerformanceMetrics(startTime, 'pattern_alert');
        } catch (error) {
            console.error('[DashboardWebSocketHandler] Error handling pattern alert:', error);
        }
    }

    handleMarketSummary(data) {
        const startTime = performance.now();

        try {
            if (!data.summary) {
                console.warn('[DashboardWebSocketHandler] Invalid market summary:', data);
                return;
            }

            // Update market summary in dashboard
            if (this.dashboardManager) {
                this.dashboardManager.marketSummary = {
                    totalSymbols: data.summary.total_symbols || 0,
                    symbolsUp: data.summary.symbols_up || 0,
                    symbolsDown: data.summary.symbols_down || 0,
                    lastUpdate: new Date(data.timestamp || Date.now()).toLocaleTimeString()
                };

                this.dashboardManager.updateMarketSummary();
            }

            this.updatePerformanceMetrics(startTime, 'market_summary');
        } catch (error) {
            console.error('[DashboardWebSocketHandler] Error handling market summary:', error);
        }
    }

    handleVolumeSpike(data) {
        const startTime = performance.now();

        try {
            if (!data.symbol || !data.volume_data) {
                console.warn('[DashboardWebSocketHandler] Invalid volume spike data:', data);
                return;
            }

            // Add volume spike alert
            if (this.dashboardManager) {
                this.dashboardManager.addAlert({
                    id: `volume-${data.symbol}-${Date.now()}`,
                    type: 'volume_alert',
                    title: `Volume Spike - ${data.symbol}`,
                    description: `Volume: ${data.volume_data.current_volume.toLocaleString()} (${data.volume_data.spike_multiple}x average)`,
                    timestamp: data.timestamp || Date.now(),
                    symbol: data.symbol,
                    show_notification: false // Less intrusive for volume spikes
                });
            }

            this.updatePerformanceMetrics(startTime, 'volume_spike');
        } catch (error) {
            console.error('[DashboardWebSocketHandler] Error handling volume spike:', error);
        }
    }

    handleSymbolMetadata(data) {
        const startTime = performance.now();

        try {
            if (!data.symbol || !data.metadata) {
                console.warn('[DashboardWebSocketHandler] Invalid symbol metadata:', data);
                return;
            }

            // Update chart manager symbol dropdown if needed
            if (this.chartManager) {
                this.chartManager.updateSymbolMetadata(data.symbol, data.metadata);
            }

            // Update dashboard manager symbol info
            if (this.dashboardManager) {
                this.dashboardManager.updateSymbolMetadata(data.symbol, data.metadata);
            }

            this.updatePerformanceMetrics(startTime, 'symbol_metadata');
        } catch (error) {
            console.error('[DashboardWebSocketHandler] Error handling symbol metadata:', error);
        }
    }

    subscribeToWatchlist() {
        if (!this.isConnected || !this.dashboardManager) {
            return;
        }

        // Request subscription to user's watchlist symbols
        const watchlistSymbols = this.dashboardManager.watchlist.map(item => item.symbol);
        
        if (watchlistSymbols.length > 0) {
            this.socket.emit('subscribe_tickstockpl_watchlist', {
                symbols: watchlistSymbols,
                user_id: window.userContext.userId,
                subscription_types: ['price_update', 'ohlcv_update', 'pattern_alert']
            });

            if (DASHBOARD_WEBSOCKET_DEBUG) console.log(`[DashboardWebSocketHandler] Subscribed to ${watchlistSymbols.length} watchlist symbols`);
        }
    }

    unsubscribeFromSymbol(symbol) {
        if (!this.isConnected) {
            return;
        }

        this.socket.emit('unsubscribe_tickstockpl_symbol', {
            symbol: symbol,
            user_id: window.userContext.userId
        });

        if (DASHBOARD_WEBSOCKET_DEBUG) console.log(`[DashboardWebSocketHandler] Unsubscribed from ${symbol}`);
    }

    processBufferedMessages() {
        if (this.messageBuffer.length === 0) {
            return;
        }

        if (DASHBOARD_WEBSOCKET_DEBUG) console.log(`[DashboardWebSocketHandler] Processing ${this.messageBuffer.length} buffered messages`);
        
        const messages = [...this.messageBuffer];
        this.messageBuffer = [];

        messages.forEach(message => {
            try {
                switch (message.type) {
                    case 'price_update':
                        this.handlePriceUpdate(message.data);
                        break;
                    case 'ohlcv_update':
                        this.handleOHLCVUpdate(message.data);
                        break;
                    case 'pattern_alert':
                        this.handlePatternAlert(message.data);
                        break;
                    default:
                        if (DASHBOARD_WEBSOCKET_DEBUG) console.warn('[DashboardWebSocketHandler] Unknown buffered message type:', message.type);
                }
            } catch (error) {
                console.error('[DashboardWebSocketHandler] Error processing buffered message:', error);
            }
        });
    }

    updatePerformanceMetrics(startTime, eventType) {
        const latency = performance.now() - startTime;
        this.performanceMetrics.messagesReceived++;
        this.performanceMetrics.lastUpdateTime = new Date();

        // Update rolling average latency
        const alpha = 0.1; // Smoothing factor
        this.performanceMetrics.averageLatency = 
            this.performanceMetrics.averageLatency * (1 - alpha) + latency * alpha;

        // Log slow operations
        if (latency > 50) {
            console.warn(`[DashboardWebSocketHandler] Slow ${eventType} processing: ${latency.toFixed(2)}ms`);
        }

        this.lastUpdateTimes.set(eventType, latency);
    }

    getPerformanceMetrics() {
        return {
            ...this.performanceMetrics,
            connectionStatus: this.isConnected ? 'connected' : 'disconnected',
            bufferedMessages: this.messageBuffer.length,
            lastUpdateTimes: Object.fromEntries(this.lastUpdateTimes)
        };
    }

    // Request chart data for specific symbol and timeframe
    requestChartData(symbol, timeframe) {
        if (!this.isConnected) {
            console.warn('[DashboardWebSocketHandler] Cannot request chart data - not connected');
            return;
        }

        this.socket.emit('request_tickstockpl_chart_data', {
            symbol: symbol,
            timeframe: timeframe,
            user_id: window.userContext.userId
        });

        if (DASHBOARD_WEBSOCKET_DEBUG) console.log(`[DashboardWebSocketHandler] Requested chart data for ${symbol} (${timeframe})`);
    }

    // Cleanup and destroy
    destroy() {
        if (this.socket) {
            this.socket.off('tickstockpl_price_update');
            this.socket.off('tickstockpl_ohlcv_update');
            this.socket.off('tickstockpl_pattern_alert');
            this.socket.off('tickstockpl_market_summary');
            this.socket.off('tickstockpl_volume_spike');
            this.socket.off('tickstockpl_symbol_metadata');
        }
        
        this.messageBuffer = [];
        this.lastUpdateTimes.clear();
        if (DASHBOARD_WEBSOCKET_DEBUG) console.log('[DashboardWebSocketHandler] Destroyed and cleaned up');
    }
}

// Global instance
let dashboardWebSocketHandler = null;

// Initialize after dashboard and chart managers are ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for dashboard and chart managers to initialize first
    setTimeout(() => {
        if (window.dashboardManager && window.chartManager) {
            dashboardWebSocketHandler = new DashboardWebSocketHandler(
                window.dashboardManager,
                window.chartManager
            );
            window.dashboardWebSocketHandler = dashboardWebSocketHandler;
            
            if (DASHBOARD_WEBSOCKET_DEBUG) console.log('[DashboardWebSocketHandler] Real-time integration active');
        } else {
            console.warn('[DashboardWebSocketHandler] Dashboard/Chart managers not ready, retrying...');
            setTimeout(() => {
                if (window.dashboardManager && window.chartManager) {
                    dashboardWebSocketHandler = new DashboardWebSocketHandler(
                        window.dashboardManager,
                        window.chartManager
                    );
                    window.dashboardWebSocketHandler = dashboardWebSocketHandler;
                }
            }, 2000);
        }
    }, 1500);
});