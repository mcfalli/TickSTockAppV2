/**
 * TickStockPL Integration - Client-side JavaScript
 * Sprint 10 Phase 2: Enhanced Redis Event Consumption
 * 
 * Handles real-time WebSocket events from TickStockPL services:
 * - Pattern alerts
 * - Backtest progress updates  
 * - Backtest results
 * - System health updates
 */

class TickStockPLIntegration {
    constructor(socket) {
        this.socket = socket;
        this.isConnected = false;
        this.subscriptions = new Set();
        this.eventHandlers = new Map();
        this.stats = {
            eventsReceived: 0,
            patternsReceived: 0,
            backtestUpdates: 0,
            connectionTime: null
        };
        
        this.init();
    }
    
    init() {
        console.log('🔌 Initializing TickStockPL integration...');
        this.setupSocketEventHandlers();
        this.setupHeartbeat();
    }
    
    setupSocketEventHandlers() {
        // Connection management
        this.socket.on('connection_confirmed', (data) => {
            console.log('✅ TickStockPL connection confirmed:', data);
            this.isConnected = true;
            this.stats.connectionTime = new Date(data.server_time * 1000);
            this.updateConnectionStatus('connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('❌ TickStockPL connection lost');
            this.isConnected = false;
            this.updateConnectionStatus('disconnected');
        });
        
        // Pattern alerts
        this.socket.on('pattern_alert', (data) => {
            this.handlePatternAlert(data);
        });
        
        // Backtest updates
        this.socket.on('backtest_progress', (data) => {
            this.handleBacktestProgress(data);
        });
        
        this.socket.on('backtest_result', (data) => {
            this.handleBacktestResult(data);
        });
        
        // System health
        this.socket.on('system_health', (data) => {
            this.handleSystemHealth(data);
        });
        
        // Subscription confirmations
        this.socket.on('subscription_confirmed', (data) => {
            console.log('🎯 Pattern subscriptions confirmed:', data);
            this.updateSubscriptionDisplay(data.patterns);
        });
        
        // Queued messages for returning users
        this.socket.on('queued_message', (data) => {
            console.log('📬 Received queued message:', data);
            this.handleQueuedMessage(data);
        });
        
        // Heartbeat
        this.socket.on('heartbeat_ack', (data) => {
            // Silent heartbeat acknowledgment
        });
        
        // Error handling
        this.socket.on('error', (error) => {
            console.error('🚨 SocketIO error:', error);
            this.updateConnectionStatus('error', error.message);
        });
    }
    
    setupHeartbeat() {
        // Send heartbeat every 30 seconds to maintain connection
        setInterval(() => {
            if (this.isConnected) {
                this.socket.emit('heartbeat');
            }
        }, 30000);
    }
    
    handlePatternAlert(data) {
        try {
            console.log('📈 Pattern alert received:', data);
            this.stats.eventsReceived++;
            this.stats.patternsReceived++;
            
            const eventData = data.event_data || data.event;
            const pattern = data.pattern || eventData?.data?.pattern;
            const symbol = data.symbol || eventData?.data?.symbol;
            const confidence = eventData?.data?.confidence;
            
            if (!pattern || !symbol) {
                console.warn('⚠️ Invalid pattern alert data:', data);
                return;
            }
            
            // Show notification
            this.showPatternNotification(pattern, symbol, confidence);
            
            // Update UI if pattern display exists
            this.updatePatternDisplay(data);
            
            // Call registered handlers
            this.callEventHandlers('pattern_alert', data);
            
        } catch (error) {
            console.error('❌ Error handling pattern alert:', error);
        }
    }
    
    handleBacktestProgress(data) {
        try {
            console.log('⏳ Backtest progress:', data);
            this.stats.eventsReceived++;
            this.stats.backtestUpdates++;
            
            const eventData = data.event_data || data.event;
            const jobId = data.job_id || eventData?.data?.job_id;
            const progress = data.progress || eventData?.data?.progress;
            
            if (!jobId) {
                console.warn('⚠️ Invalid backtest progress data:', data);
                return;
            }
            
            // Update progress display
            this.updateBacktestProgress(jobId, progress, eventData?.data?.status);
            
            // Call registered handlers
            this.callEventHandlers('backtest_progress', data);
            
        } catch (error) {
            console.error('❌ Error handling backtest progress:', error);
        }
    }
    
    handleBacktestResult(data) {
        try {
            console.log('🎯 Backtest result:', data);
            this.stats.eventsReceived++;
            
            const eventData = data.event_data || data.event;
            const jobId = data.job_id || eventData?.data?.job_id;
            const status = data.status || eventData?.data?.status;
            
            if (!jobId) {
                console.warn('⚠️ Invalid backtest result data:', data);
                return;
            }
            
            // Show result notification
            this.showBacktestResultNotification(jobId, status);
            
            // Update results display
            this.updateBacktestResults(jobId, eventData?.data);
            
            // Call registered handlers
            this.callEventHandlers('backtest_result', data);
            
        } catch (error) {
            console.error('❌ Error handling backtest result:', error);
        }
    }
    
    handleSystemHealth(data) {
        try {
            console.log('🏥 System health update:', data);
            this.stats.eventsReceived++;
            
            // Update health indicators in UI
            this.updateHealthIndicators(data.health_data);
            
            // Call registered handlers
            this.callEventHandlers('system_health', data);
            
        } catch (error) {
            console.error('❌ Error handling system health:', error);
        }
    }
    
    handleQueuedMessage(data) {
        try {
            console.log('📬 Processing queued message:', data);
            
            // Process based on message type
            if (data.type === 'pattern_alert') {
                this.handlePatternAlert(data);
            } else if (data.type === 'backtest_progress') {
                this.handleBacktestProgress(data);
            } else if (data.type === 'backtest_result') {
                this.handleBacktestResult(data);
            }
            
        } catch (error) {
            console.error('❌ Error handling queued message:', error);
        }
    }
    
    subscribeToPatterns(patterns) {
        if (!Array.isArray(patterns)) {
            console.error('❌ Patterns must be an array');
            return;
        }
        
        console.log('🎯 Subscribing to patterns:', patterns);
        this.socket.emit('subscribe_patterns', { patterns: patterns });
        
        // Update local subscriptions
        this.subscriptions.clear();
        patterns.forEach(pattern => this.subscriptions.add(pattern));
    }
    
    showPatternNotification(pattern, symbol, confidence) {
        try {
            const confidenceText = confidence ? ` (${(confidence * 100).toFixed(1)}%)` : '';
            const message = `${pattern} pattern detected on ${symbol}${confidenceText}`;
            
            // Create notification element
            const notification = document.createElement('div');
            notification.className = 'tickstockpl-notification pattern-alert';
            notification.innerHTML = `
                <div class="notification-icon">📈</div>
                <div class="notification-content">
                    <div class="notification-title">Pattern Alert</div>
                    <div class="notification-message">${message}</div>
                </div>
                <div class="notification-close">&times;</div>
            `;
            
            // Add to notifications container
            const container = document.getElementById('notifications-container') || document.body;
            container.appendChild(notification);
            
            // Auto-remove after 10 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 10000);
            
            // Close on click
            notification.querySelector('.notification-close').onclick = () => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            };
            
        } catch (error) {
            console.error('❌ Error showing pattern notification:', error);
        }
    }
    
    showBacktestResultNotification(jobId, status) {
        try {
            const message = `Backtest job ${jobId} ${status}`;
            const icon = status === 'completed' ? '✅' : '❌';
            
            // Use browser notification if available
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('TickStock Backtest', {
                    body: message,
                    icon: '/static/images/logo-placeholder.jpg'
                });
            } else {
                // Fallback to in-app notification
                console.log(`${icon} ${message}`);
            }
            
        } catch (error) {
            console.error('❌ Error showing backtest notification:', error);
        }
    }
    
    updateConnectionStatus(status, message = '') {
        const statusElement = document.getElementById('tickstockpl-status');
        if (statusElement) {
            statusElement.className = `tickstockpl-status ${status}`;
            statusElement.textContent = status === 'connected' ? 'TickStockPL Connected' : 
                                     status === 'error' ? 'TickStockPL Error' : 
                                     'TickStockPL Disconnected';
            
            if (message) {
                statusElement.title = message;
            }
        }
    }
    
    updateSubscriptionDisplay(patterns) {
        const subscriptionElement = document.getElementById('pattern-subscriptions');
        if (subscriptionElement) {
            subscriptionElement.textContent = `Subscribed to ${patterns.length} patterns`;
        }
    }
    
    updatePatternDisplay(data) {
        // Placeholder for pattern display updates
        // This would integrate with existing market data display
        console.log('📊 Updating pattern display:', data);
    }
    
    updateBacktestProgress(jobId, progress, status) {
        const progressElement = document.getElementById(`backtest-progress-${jobId}`);
        if (progressElement) {
            const percentage = Math.round(progress * 100);
            progressElement.style.width = `${percentage}%`;
            progressElement.textContent = `${percentage}%`;
            
            const statusElement = document.getElementById(`backtest-status-${jobId}`);
            if (statusElement) {
                statusElement.textContent = status || 'running';
            }
        }
    }
    
    updateBacktestResults(jobId, results) {
        const resultsElement = document.getElementById(`backtest-results-${jobId}`);
        if (resultsElement && results) {
            resultsElement.innerHTML = `
                <div class="backtest-metrics">
                    <div>Win Rate: ${((results.win_rate || 0) * 100).toFixed(1)}%</div>
                    <div>ROI: ${((results.roi || 0) * 100).toFixed(2)}%</div>
                    <div>Sharpe: ${(results.sharpe_ratio || 0).toFixed(2)}</div>
                </div>
            `;
        }
    }
    
    updateHealthIndicators(healthData) {
        // Update health indicators in the UI
        const healthElement = document.getElementById('system-health-indicator');
        if (healthElement && healthData) {
            const overallStatus = healthData.overall_status || 'unknown';
            healthElement.className = `health-indicator ${overallStatus}`;
            healthElement.textContent = overallStatus.toUpperCase();
        }
    }
    
    addEventListener(eventType, handler) {
        if (!this.eventHandlers.has(eventType)) {
            this.eventHandlers.set(eventType, []);
        }
        this.eventHandlers.get(eventType).push(handler);
    }
    
    callEventHandlers(eventType, data) {
        const handlers = this.eventHandlers.get(eventType);
        if (handlers) {
            handlers.forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`❌ Event handler error for ${eventType}:`, error);
                }
            });
        }
    }
    
    getStats() {
        return {
            ...this.stats,
            isConnected: this.isConnected,
            subscriptions: Array.from(this.subscriptions),
            subscribedPatterns: this.subscriptions.size
        };
    }
    
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                console.log('🔔 Notification permission:', permission);
            });
        }
    }
}

// CSS for notifications
const notificationStyles = `
    .tickstockpl-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: #2c3e50;
        color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        max-width: 400px;
        z-index: 10000;
        margin-bottom: 10px;
    }
    
    .tickstockpl-notification.pattern-alert {
        background: #27ae60;
    }
    
    .notification-icon {
        font-size: 24px;
        margin-right: 12px;
    }
    
    .notification-content {
        flex: 1;
    }
    
    .notification-title {
        font-weight: bold;
        margin-bottom: 4px;
    }
    
    .notification-message {
        font-size: 14px;
        opacity: 0.9;
    }
    
    .notification-close {
        cursor: pointer;
        font-size: 20px;
        margin-left: 12px;
        opacity: 0.7;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
    
    .tickstockpl-status {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    
    .tickstockpl-status.connected {
        background: #d5f4e6;
        color: #27ae60;
    }
    
    .tickstockpl-status.disconnected {
        background: #fdf2f2;
        color: #e74c3c;
    }
    
    .tickstockpl-status.error {
        background: #fef7e0;
        color: #f39c12;
    }
    
    .health-indicator {
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: bold;
    }
    
    .health-indicator.healthy {
        background: #d5f4e6;
        color: #27ae60;
    }
    
    .health-indicator.degraded {
        background: #fef7e0;
        color: #f39c12;
    }
    
    .health-indicator.error {
        background: #fdf2f2;
        color: #e74c3c;
    }
`;

// Inject CSS
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Export for use in other modules
window.TickStockPLIntegration = TickStockPLIntegration;