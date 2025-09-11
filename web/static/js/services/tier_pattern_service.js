// ==========================================================================
// TIER PATTERN SERVICE - SPRINT 25 WEEK 2
// ==========================================================================
// VERSION: 1.0.0 - Sprint 25 Week 2 Implementation  
// PURPOSE: WebSocket integration service for tier-specific pattern events
// ==========================================================================

// Debug flag for development
const TIER_PATTERN_DEBUG = true;

class TierPatternService {
    constructor(options = {}) {
        this.options = {
            enableWebSocket: true,
            apiEndpoint: '/api/patterns',
            reconnectDelay: 5000,
            maxRetries: 3,
            batchUpdates: true,
            batchDelay: 100,
            ...options
        };
        
        // WebSocket connection
        this.socket = window.socket;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        
        // Subscription management
        this.subscriptions = new Map();
        this.eventHandlers = new Map();
        this.updateQueue = [];
        this.batchTimer = null;
        
        // Performance tracking
        this.metrics = {
            messagesReceived: 0,
            avgLatency: 0,
            lastMessageTime: null,
            connectionUptime: 0,
            connectionStartTime: null
        };
        
        // Tier configuration
        this.tierConfig = {
            daily: {
                endpoint: '/api/patterns/daily',
                wsEvent: 'tier_pattern_daily',
                alertEvent: 'tier_pattern_alert_daily',
                maxPatterns: 50
            },
            intraday: {
                endpoint: '/api/patterns/intraday', 
                wsEvent: 'tier_pattern_intraday',
                alertEvent: 'tier_pattern_alert_intraday',
                maxPatterns: 100
            },
            combo: {
                endpoint: '/api/patterns/combo',
                wsEvent: 'tier_pattern_combo',
                alertEvent: 'tier_pattern_alert_combo',
                maxPatterns: 30
            }
        };
        
        if (TIER_PATTERN_DEBUG) console.log('[TierPatternService] Initialized with options:', this.options);
    }
    
    async initialize() {
        try {
            await this.setupWebSocketConnection();
            await this.setupEventHandlers();
            await this.requestInitialData();
            
            if (TIER_PATTERN_DEBUG) console.log('[TierPatternService] Service initialized successfully');
            return true;
        } catch (error) {
            console.error('[TierPatternService] Initialization failed:', error);
            return false;
        }
    }
    
    async setupWebSocketConnection() {
        if (!this.options.enableWebSocket || !this.socket) {
            console.warn('[TierPatternService] WebSocket disabled or not available');
            return;
        }
        
        // Connection event handlers
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.metrics.connectionStartTime = Date.now();
            this.onConnectionEstablished();
            if (TIER_PATTERN_DEBUG) console.log('[TierPatternService] WebSocket connected');
        });
        
        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.onConnectionLost();
            if (TIER_PATTERN_DEBUG) console.log('[TierPatternService] WebSocket disconnected');
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('[TierPatternService] WebSocket connection error:', error);
            this.handleConnectionError(error);
        });
        
        // Check if already connected
        if (this.socket.connected) {
            this.isConnected = true;
            this.metrics.connectionStartTime = Date.now();
            this.onConnectionEstablished();
        }
    }
    
    setupEventHandlers() {
        if (!this.socket) return;
        
        // Set up tier-specific pattern event handlers
        Object.keys(this.tierConfig).forEach(tier => {
            const config = this.tierConfig[tier];
            
            // Pattern update events
            this.socket.on(config.wsEvent, (data) => {
                this.handlePatternUpdate(tier, data);
            });
            
            // Pattern alert events
            this.socket.on(config.alertEvent, (data) => {
                this.handlePatternAlert(tier, data);
            });
        });
        
        // Global pattern events
        this.socket.on('pattern_batch_update', (data) => {
            this.handleBatchUpdate(data);
        });
        
        this.socket.on('pattern_health_metrics', (data) => {
            this.updateHealthMetrics(data);
        });
        
        this.socket.on('subscription_status', (data) => {
            this.handleSubscriptionStatus(data);
        });
        
        // Real-time pattern alerts from TickStockPL via Redis
        this.socket.on('pattern_alert', (data) => {
            this.handleRealTimePatternAlert(data);
        });
        
        // Backtest progress and results
        this.socket.on('backtest_progress', (data) => {
            this.handleBacktestProgress(data);
        });
        
        this.socket.on('backtest_result', (data) => {
            this.handleBacktestResult(data);
        });
        
        // System health updates
        this.socket.on('system_health', (data) => {
            this.handleSystemHealth(data);
        });
        
        if (TIER_PATTERN_DEBUG) console.log('[TierPatternService] Event handlers configured');
    }
    
    async requestInitialData() {
        // Request initial pattern data for all tiers
        const requests = Object.keys(this.tierConfig).map(tier => 
            this.getTierPatterns(tier)
        );
        
        try {
            const results = await Promise.all(requests);
            if (TIER_PATTERN_DEBUG) console.log('[TierPatternService] Initial data loaded for all tiers');
            return results;
        } catch (error) {
            console.error('[TierPatternService] Failed to load initial data:', error);
            throw error;
        }
    }
    
    // Public API methods
    
    async getTierPatterns(tier, filters = {}) {
        const config = this.tierConfig[tier];
        if (!config) {
            throw new Error(`Unknown tier: ${tier}`);
        }
        
        try {
            const response = await fetch(`${config.endpoint}?${new URLSearchParams(filters)}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (TIER_PATTERN_DEBUG) {
                console.log(`[TierPatternService] Loaded ${data.patterns?.length || 0} patterns for ${tier}`);
            }
            
            return data.patterns || [];
            
        } catch (error) {
            console.error(`[TierPatternService] Failed to fetch ${tier} patterns:`, error);
            throw error;
        }
    }
    
    subscribeToTierPatterns(tier, callback, filters = {}) {
        if (!this.tierConfig[tier]) {
            throw new Error(`Unknown tier: ${tier}`);
        }
        
        // Store subscription
        if (!this.subscriptions.has(tier)) {
            this.subscriptions.set(tier, new Set());
        }
        this.subscriptions.get(tier).add(callback);
        
        // Store event handler
        const handlerKey = `${tier}_${Date.now()}`;
        this.eventHandlers.set(handlerKey, callback);
        
        // Request WebSocket subscription
        if (this.socket && this.isConnected) {
            this.socket.emit('subscribe_tier_patterns', {
                tier: tier,
                filters: filters,
                subscription_id: handlerKey
            });
        }
        
        if (TIER_PATTERN_DEBUG) {
            console.log(`[TierPatternService] Subscribed to ${tier} patterns with filters:`, filters);
        }
        
        return handlerKey; // Return subscription ID for unsubscribing
    }
    
    unsubscribeFromTierPatterns(tier, subscriptionId = null) {
        if (subscriptionId) {
            // Remove specific subscription
            this.eventHandlers.delete(subscriptionId);
            
            if (this.subscriptions.has(tier)) {
                const callback = this.eventHandlers.get(subscriptionId);
                if (callback) {
                    this.subscriptions.get(tier).delete(callback);
                }
            }
            
            // Unsubscribe from WebSocket
            if (this.socket && this.isConnected) {
                this.socket.emit('unsubscribe_tier_patterns', {
                    tier: tier,
                    subscription_id: subscriptionId
                });
            }
        } else {
            // Remove all subscriptions for tier
            this.subscriptions.delete(tier);
            
            // Remove all event handlers for tier
            for (const [key, handler] of this.eventHandlers.entries()) {
                if (key.startsWith(tier)) {
                    this.eventHandlers.delete(key);
                }
            }
            
            // Unsubscribe all from WebSocket
            if (this.socket && this.isConnected) {
                this.socket.emit('unsubscribe_tier_patterns', { tier: tier });
            }
        }
        
        if (TIER_PATTERN_DEBUG) {
            console.log(`[TierPatternService] Unsubscribed from ${tier} patterns`);
        }
    }
    
    async subscribeToPatternAlerts(user_id, preferences) {
        try {
            if (this.socket && this.isConnected) {
                this.socket.emit('subscribe_pattern_alerts', {
                    user_id: user_id,
                    preferences: preferences
                });
                
                if (TIER_PATTERN_DEBUG) {
                    console.log('[TierPatternService] Subscribed to pattern alerts for user:', user_id);
                }
                
                return true;
            }
            
            return false;
        } catch (error) {
            console.error('[TierPatternService] Failed to subscribe to pattern alerts:', error);
            return false;
        }
    }
    
    // Event handling methods
    
    handlePatternUpdate(tier, data) {
        const startTime = performance.now();
        
        try {
            // Update metrics
            this.metrics.messagesReceived++;
            this.metrics.lastMessageTime = Date.now();
            
            // Calculate latency if timestamp provided
            if (data.timestamp) {
                const latency = Date.now() - data.timestamp;
                this.metrics.avgLatency = (this.metrics.avgLatency + latency) / 2;
            }
            
            // Queue update for batching
            if (this.options.batchUpdates) {
                this.queueUpdate(tier, data);
            } else {
                this.processPatternUpdate(tier, data);
            }
            
            const processingTime = performance.now() - startTime;
            if (TIER_PATTERN_DEBUG) {
                console.log(`[TierPatternService] Processed ${tier} update in ${processingTime.toFixed(2)}ms`);
            }
            
        } catch (error) {
            console.error(`[TierPatternService] Error handling ${tier} pattern update:`, error);
        }
    }
    
    queueUpdate(tier, data) {
        this.updateQueue.push({ tier, data, timestamp: Date.now() });
        
        // Clear existing timer
        if (this.batchTimer) {
            clearTimeout(this.batchTimer);
        }
        
        // Set new timer for batch processing
        this.batchTimer = setTimeout(() => {
            this.processBatchedUpdates();
        }, this.options.batchDelay);
    }
    
    processBatchedUpdates() {
        if (this.updateQueue.length === 0) return;
        
        const updates = [...this.updateQueue];
        this.updateQueue = [];
        this.batchTimer = null;
        
        // Group updates by tier
        const tierUpdates = updates.reduce((acc, update) => {
            if (!acc[update.tier]) acc[update.tier] = [];
            acc[update.tier].push(update.data);
            return acc;
        }, {});
        
        // Process each tier's updates
        Object.keys(tierUpdates).forEach(tier => {
            this.processPatternUpdate(tier, { patterns: tierUpdates[tier] });
        });
        
        if (TIER_PATTERN_DEBUG) {
            console.log(`[TierPatternService] Processed ${updates.length} batched updates`);
        }
    }
    
    processPatternUpdate(tier, data) {
        const callbacks = this.subscriptions.get(tier);
        if (!callbacks) return;
        
        // Notify all subscribers
        callbacks.forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`[TierPatternService] Error in ${tier} callback:`, error);
            }
        });
    }
    
    handlePatternAlert(tier, data) {
        // Handle pattern alerts with high priority
        this.processPatternUpdate(tier, { alert: true, ...data });
        
        // Show browser notification if enabled
        if (data.priority === 'CRITICAL' && 'Notification' in window) {
            this.showBrowserNotification(tier, data);
        }
        
        if (TIER_PATTERN_DEBUG) {
            console.log(`[TierPatternService] Pattern alert received for ${tier}:`, data);
        }
    }
    
    handleBatchUpdate(data) {
        if (data.tiers) {
            Object.keys(data.tiers).forEach(tier => {
                this.handlePatternUpdate(tier, { patterns: data.tiers[tier] });
            });
        }
    }
    
    handleSubscriptionStatus(data) {
        if (TIER_PATTERN_DEBUG) {
            console.log('[TierPatternService] Subscription status update:', data);
        }
    }
    
    handleRealTimePatternAlert(data) {
        /**
         * Handle real-time pattern alerts from TickStockPL via Redis WebSocket
         * These are live pattern detections as they happen
         */
        try {
            const eventData = data.event_data || data.event || data;
            const patternData = eventData.data || eventData;
            
            // Extract pattern information
            const pattern_type = patternData.pattern || patternData.pattern_type;
            const symbol = patternData.symbol;
            const confidence = patternData.confidence || 0;
            const detection_timestamp = patternData.timestamp || patternData.detection_timestamp || Date.now();
            
            if (!pattern_type || !symbol) {
                console.warn('[TierPatternService] Incomplete pattern alert data:', data);
                return;
            }
            
            // Determine tier based on pattern characteristics or metadata
            const tier = this.determineTierFromPattern(patternData);
            
            // Create standardized pattern alert
            const alertData = {
                id: patternData.id || `alert_${Date.now()}`,
                symbol: symbol,
                pattern_type: pattern_type,
                confidence: confidence,
                detection_timestamp: new Date(detection_timestamp).toISOString(),
                pattern_data: patternData,
                tier: tier,
                priority: this.calculatePriority(confidence),
                alert: true,
                real_time: true,
                source: 'tickstockpl'
            };
            
            // Update metrics
            this.metrics.messagesReceived++;
            this.metrics.lastMessageTime = Date.now();
            
            // Broadcast to tier-specific subscribers
            this.handlePatternAlert(tier, alertData);
            
            // Show critical alerts as browser notifications
            if (confidence >= 0.9 && 'Notification' in window) {
                this.showBrowserNotification(tier, alertData);
            }
            
            if (TIER_PATTERN_DEBUG) {
                console.log(`[TierPatternService] Real-time pattern alert processed: ${pattern_type} on ${symbol} (${tier} tier, confidence: ${confidence})`);
            }
            
        } catch (error) {
            console.error('[TierPatternService] Error handling real-time pattern alert:', error);
        }
    }
    
    handleBacktestProgress(data) {
        /**
         * Handle backtest progress updates from TickStockPL
         */
        try {
            const eventData = data.event_data || data.event || data;
            const progressData = eventData.data || eventData;
            
            const job_id = progressData.job_id || eventData.job_id;
            const progress = progressData.progress || eventData.progress || 0;
            const current_symbol = progressData.current_symbol || eventData.current_symbol;
            
            // Emit backtest progress to any registered handlers
            this.subscriptions.forEach((callbacks) => {
                callbacks.forEach(callback => {
                    try {
                        callback({
                            type: 'backtest_progress',
                            job_id: job_id,
                            progress: progress,
                            current_symbol: current_symbol,
                            timestamp: Date.now()
                        });
                    } catch (error) {
                        console.error('[TierPatternService] Error in backtest progress callback:', error);
                    }
                });
            });
            
            if (TIER_PATTERN_DEBUG) {
                console.log(`[TierPatternService] Backtest progress: ${job_id} - ${(progress * 100).toFixed(1)}%`);
            }
            
        } catch (error) {
            console.error('[TierPatternService] Error handling backtest progress:', error);
        }
    }
    
    handleBacktestResult(data) {
        /**
         * Handle completed backtest results from TickStockPL
         */
        try {
            const eventData = data.event_data || data.event || data;
            const resultData = eventData.data || eventData;
            
            const job_id = resultData.job_id || eventData.job_id;
            const status = resultData.status || eventData.status;
            const results = resultData.results || eventData.results;
            
            // Emit backtest result to any registered handlers
            this.subscriptions.forEach((callbacks) => {
                callbacks.forEach(callback => {
                    try {
                        callback({
                            type: 'backtest_result',
                            job_id: job_id,
                            status: status,
                            results: results,
                            timestamp: Date.now()
                        });
                    } catch (error) {
                        console.error('[TierPatternService] Error in backtest result callback:', error);
                    }
                });
            });
            
            if (TIER_PATTERN_DEBUG) {
                console.log(`[TierPatternService] Backtest result: ${job_id} - ${status}`);
            }
            
        } catch (error) {
            console.error('[TierPatternService] Error handling backtest result:', error);
        }
    }
    
    handleSystemHealth(data) {
        /**
         * Handle system health updates from TickStockPL
         */
        try {
            const healthData = data.health_data || data.event_data || data;
            
            // Store health information
            this.systemHealth = {
                ...healthData,
                last_update: Date.now()
            };
            
            // Update health metrics if available
            if (healthData) {
                this.updateHealthMetrics(healthData);
            }
            
            if (TIER_PATTERN_DEBUG) {
                console.log('[TierPatternService] System health update received:', healthData);
            }
            
        } catch (error) {
            console.error('[TierPatternService] Error handling system health update:', error);
        }
    }
    
    determineTierFromPattern(patternData) {
        /**
         * Determine the appropriate tier based on pattern characteristics
         */
        const pattern_type = patternData.pattern || patternData.pattern_type || '';
        const timeframe = patternData.timeframe || patternData.interval;
        const category = patternData.category;
        
        // Check for explicit tier information
        if (patternData.tier) {
            return patternData.tier;
        }
        
        // Infer tier based on pattern characteristics
        if (timeframe) {
            if (timeframe.includes('1m') || timeframe.includes('5m') || timeframe.includes('15m')) {
                return 'intraday';
            } else if (timeframe.includes('1d') || timeframe.includes('daily')) {
                return 'daily';
            }
        }
        
        // Check for combo patterns based on category
        if (category === 'combo' || pattern_type.toLowerCase().includes('combo')) {
            return 'combo';
        }
        
        // Check for intraday patterns
        if (pattern_type.toLowerCase().includes('intraday') || 
            pattern_type.toLowerCase().includes('scalp') ||
            pattern_type.toLowerCase().includes('momentum')) {
            return 'intraday';
        }
        
        // Check for daily patterns
        if (pattern_type.toLowerCase().includes('daily') ||
            pattern_type.toLowerCase().includes('swing') ||
            pattern_type.toLowerCase().includes('breakout')) {
            return 'daily';
        }
        
        // Default to daily for most patterns
        return 'daily';
    }
    
    calculatePriority(confidence) {
        /**
         * Calculate priority level based on confidence
         */
        if (confidence >= 0.9) {
            return 'CRITICAL';
        } else if (confidence >= 0.8) {
            return 'HIGH';
        } else if (confidence >= 0.7) {
            return 'MEDIUM';
        } else {
            return 'LOW';
        }
    }
    
    updateHealthMetrics(data) {
        // Update connection uptime
        if (this.metrics.connectionStartTime) {
            this.metrics.connectionUptime = Date.now() - this.metrics.connectionStartTime;
        }
        
        // Store additional health metrics
        if (data) {
            this.healthMetrics = data;
        }
    }
    
    // Connection management
    
    onConnectionEstablished() {
        // Re-subscribe to all active subscriptions
        this.subscriptions.forEach((callbacks, tier) => {
            if (callbacks.size > 0) {
                this.socket.emit('subscribe_tier_patterns', { tier: tier });
            }
        });
        
        // Emit connection status to subscribers
        this.notifyConnectionStatus(true);
    }
    
    onConnectionLost() {
        // Emit connection status to subscribers
        this.notifyConnectionStatus(false);
        
        // Attempt reconnection
        this.attemptReconnection();
    }
    
    handleConnectionError(error) {
        console.error('[TierPatternService] Connection error:', error);
        this.attemptReconnection();
    }
    
    attemptReconnection() {
        if (this.reconnectAttempts >= this.options.maxRetries) {
            console.error('[TierPatternService] Max reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        
        setTimeout(() => {
            if (!this.isConnected && this.socket) {
                if (TIER_PATTERN_DEBUG) {
                    console.log(`[TierPatternService] Attempting reconnection (${this.reconnectAttempts}/${this.options.maxRetries})`);
                }
                this.socket.connect();
            }
        }, this.options.reconnectDelay);
    }
    
    notifyConnectionStatus(connected) {
        this.subscriptions.forEach((callbacks) => {
            callbacks.forEach(callback => {
                try {
                    callback({ connectionStatus: connected });
                } catch (error) {
                    console.error('[TierPatternService] Error notifying connection status:', error);
                }
            });
        });
    }
    
    // Utility methods
    
    showBrowserNotification(tier, data) {
        if (Notification.permission === 'granted') {
            const notification = new Notification(`${tier.toUpperCase()} Pattern Alert`, {
                body: `${data.pattern_type} detected on ${data.symbol}`,
                icon: '/static/images/tickstock-icon.png',
                tag: `tier-pattern-${tier}`
            });
            
            setTimeout(() => notification.close(), 5000);
        }
    }
    
    
    // Public utility methods
    
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            uptime: this.metrics.connectionUptime,
            reconnectAttempts: this.reconnectAttempts
        };
    }
    
    getPerformanceMetrics() {
        return {
            ...this.metrics,
            subscriptionCount: this.subscriptions.size,
            eventHandlerCount: this.eventHandlers.size,
            queueLength: this.updateQueue.length
        };
    }
    
    getSubscriptionInfo() {
        const info = {};
        this.subscriptions.forEach((callbacks, tier) => {
            info[tier] = {
                subscriberCount: callbacks.size,
                config: this.tierConfig[tier]
            };
        });
        return info;
    }
    
    enablePatternAlerts() {
        /**
         * Enable browser notifications for pattern alerts
         */
        if ('Notification' in window) {
            if (Notification.permission === 'default') {
                Notification.requestPermission().then(permission => {
                    if (TIER_PATTERN_DEBUG) {
                        console.log('[TierPatternService] Notification permission:', permission);
                    }
                });
            }
        }
    }
    
    subscribeToRealTimeAlerts(patterns = [], callback = null) {
        /**
         * Subscribe to real-time pattern alerts from TickStockPL
         * @param {Array} patterns - List of pattern names to subscribe to (empty = all)
         * @param {Function} callback - Optional callback for alerts
         */
        if (this.socket && this.isConnected) {
            // Send subscription request to server
            this.socket.emit('subscribe_patterns', {
                patterns: patterns,
                user_id: this.getUserId(),
                timestamp: Date.now()
            });
            
            // Add callback if provided
            if (callback && typeof callback === 'function') {
                if (!this.subscriptions.has('realtime_alerts')) {
                    this.subscriptions.set('realtime_alerts', new Set());
                }
                this.subscriptions.get('realtime_alerts').add(callback);
            }
            
            if (TIER_PATTERN_DEBUG) {
                console.log('[TierPatternService] Subscribed to real-time alerts for patterns:', patterns);
            }
            
            return true;
        }
        return false;
    }
    
    unsubscribeFromRealTimeAlerts() {
        /**
         * Unsubscribe from real-time pattern alerts
         */
        if (this.socket && this.isConnected) {
            this.socket.emit('unsubscribe_patterns', {
                user_id: this.getUserId(),
                timestamp: Date.now()
            });
            
            // Remove realtime alert subscriptions
            this.subscriptions.delete('realtime_alerts');
            
            if (TIER_PATTERN_DEBUG) {
                console.log('[TierPatternService] Unsubscribed from real-time alerts');
            }
        }
    }
    
    getUserId() {
        /**
         * Get current user ID (if available)
         */
        if (typeof window.current_user !== 'undefined' && window.current_user) {
            return window.current_user.id || window.current_user.user_id || 'anonymous';
        }
        return 'anonymous';
    }
    
    getSystemHealth() {
        /**
         * Get latest system health information
         */
        return this.systemHealth || {
            status: 'unknown',
            last_update: null
        };
    }
    
    testWebSocketConnection() {
        /**
         * Test WebSocket connection and real-time capabilities
         */
        if (this.socket && this.isConnected) {
            // Send test message
            this.socket.emit('test_connection', {
                timestamp: Date.now(),
                user_id: this.getUserId(),
                service: 'TierPatternService'
            });
            
            // Setup one-time response handler
            this.socket.once('test_response', (data) => {
                if (TIER_PATTERN_DEBUG) {
                    const latency = Date.now() - data.timestamp;
                    console.log(`[TierPatternService] WebSocket test successful - latency: ${latency}ms`);
                }
            });
            
            return true;
        }
        return false;
    }
    
    // Enhanced utility methods
    
    getRealTimeStats() {
        /**
         * Get real-time service statistics
         */
        return {
            ...this.getPerformanceMetrics(),
            connectionStatus: this.getConnectionStatus(),
            systemHealth: this.getSystemHealth(),
            subscriptionInfo: this.getSubscriptionInfo(),
            realTimeAlertsEnabled: this.subscriptions.has('realtime_alerts')
        };
    }
    
    
    
    
    destroy() {
        // Clear all subscriptions
        this.subscriptions.clear();
        this.eventHandlers.clear();
        
        // Clear timers
        if (this.batchTimer) {
            clearTimeout(this.batchTimer);
        }
        
        // Unsubscribe from WebSocket events
        if (this.socket) {
            Object.keys(this.tierConfig).forEach(tier => {
                const config = this.tierConfig[tier];
                this.socket.off(config.wsEvent);
                this.socket.off(config.alertEvent);
            });
            
            this.socket.off('pattern_batch_update');
            this.socket.off('pattern_health_metrics');
            this.socket.off('subscription_status');
        }
        
        if (TIER_PATTERN_DEBUG) console.log('[TierPatternService] Service destroyed');
    }
}

// Initialize as global service
let tierPatternService = null;

// Auto-initialization when DOM is ready (only if not already initialized)
document.addEventListener('DOMContentLoaded', function() {
    if (typeof window.socket !== 'undefined' && !window.tierPatternService) {
        tierPatternService = new TierPatternService();
        tierPatternService.initialize();
        
        // Make available globally
        window.tierPatternService = tierPatternService;
        window.TierPatternService = TierPatternService;
    }
});

// Make class available globally immediately
if (typeof window !== 'undefined') {
    window.TierPatternService = TierPatternService;
}

// Export for module usage  
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TierPatternService;
}