/**
 * Streaming Dashboard Service - Sprint 33 Phase 5
 *
 * Real-time streaming dashboard integrated into SPA model
 * Displays live pattern detections and indicator alerts
 *
 * Features:
 * - WebSocket event handling for streaming data
 * - Pattern detection display with confidence levels
 * - Indicator alerts with visual styling
 * - Health monitoring status
 * - Theme-aware display
 */

class StreamingDashboardService {
    constructor() {
        this.container = null;
        this.socket = window.socket || io();
        this.initialized = false;

        // Counters and state
        this.patternCount = 0;
        this.alertCount = 0;
        this.eventCount = 0;
        this.lastEventTime = Date.now();
        this.currentSession = null;
        this.healthStatus = null;

        // Event handlers
        this.eventHandlers = new Map();

        // Bind methods
        this.handleStreamingSession = this.handleStreamingSession.bind(this);
        this.handleStreamingPattern = this.handleStreamingPattern.bind(this);
        this.handleStreamingPatternsBatch = this.handleStreamingPatternsBatch.bind(this);
        this.handleIndicatorAlert = this.handleIndicatorAlert.bind(this);
        this.handleStreamingHealth = this.handleStreamingHealth.bind(this);
        this.handleCriticalAlert = this.handleCriticalAlert.bind(this);
    }

    /**
     * Initialize the streaming dashboard
     */
    async initialize(containerId = 'main-content') {
        console.log('[StreamingDashboard] Initializing...');

        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[StreamingDashboard] Container not found:', containerId);
            return;
        }

        // Create dashboard structure
        this.render();

        // Setup WebSocket event handlers
        this.setupEventHandlers();

        // Load initial status
        await this.loadStreamingStatus();

        this.initialized = true;
        console.log('[StreamingDashboard] Initialized successfully');
    }

    /**
     * Render the dashboard HTML structure
     */
    render() {
        const html = `
            <div class="streaming-dashboard">
                <!-- Header Section -->
                <div class="streaming-header card mb-3">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div class="session-status d-flex align-items-center gap-3">
                            <span class="session-indicator inactive" id="sessionIndicator"></span>
                            <div>
                                <h4 class="mb-0">Streaming Session</h4>
                                <small id="sessionInfo" class="text-muted">Not Connected</small>
                                <div><small id="lastUpdated" class="text-muted" style="font-size: 0.85em;">Last updated: Never</small></div>
                            </div>
                        </div>
                        <button class="btn btn-primary" onclick="window.streamingDashboard.refresh()">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                    </div>
                </div>

                <!-- Metrics Grid -->
                <div class="row metrics-grid mb-4">
                    <div class="col-md-3 col-sm-6">
                        <div class="metric-card card">
                            <div class="card-body text-center">
                                <div class="metric-value" id="activeSymbols">0</div>
                                <div class="metric-label text-muted">Active Symbols</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="metric-card card">
                            <div class="card-body text-center">
                                <div class="metric-value" id="eventsPerSecond">0</div>
                                <div class="metric-label text-muted">Events/Second</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="metric-card card">
                            <div class="card-body text-center">
                                <div class="metric-value" id="patternsDetected">${this.patternCount}</div>
                                <div class="metric-label text-muted">Patterns Detected</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="metric-card card">
                            <div class="card-body text-center">
                                <div class="metric-value" id="indicatorAlerts">${this.alertCount}</div>
                                <div class="metric-label text-muted">Indicator Alerts</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Streaming Panels -->
                <div class="row streaming-panels">
                    <div class="col-lg-6">
                        <div class="stream-panel card">
                            <div class="card-header panel-header bg-gradient text-white">
                                <div class="d-flex justify-content-between align-items-center">
                                    <span><i class="fas fa-chart-line"></i> Real-time Patterns</span>
                                    <span id="patternCount" class="badge bg-light text-dark">0 patterns</span>
                                </div>
                            </div>
                            <div class="card-body event-stream" id="patternStream" style="max-height: 400px; overflow-y: auto;">
                                <!-- Pattern events will be added here -->
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-6">
                        <div class="stream-panel card">
                            <div class="card-header panel-header bg-gradient text-white">
                                <div class="d-flex justify-content-between align-items-center">
                                    <span><i class="fas fa-bell"></i> Indicator Alerts</span>
                                    <span id="alertCount" class="badge bg-light text-dark">0 alerts</span>
                                </div>
                            </div>
                            <div class="card-body event-stream" id="alertStream" style="max-height: 400px; overflow-y: auto;">
                                <!-- Alert events will be added here -->
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Health Status -->
                <div class="stream-panel card mt-4">
                    <div class="card-header panel-header bg-gradient text-white">
                        <span><i class="fas fa-heartbeat"></i> System Health</span>
                    </div>
                    <div class="card-body" id="healthStatus">
                        <div class="alert alert-success health-status">
                            <i class="fas fa-check-circle"></i> System Healthy - Waiting for streaming data...
                        </div>
                    </div>
                </div>
            </div>

            <style>
                .streaming-dashboard {
                    padding: 20px;
                }

                .session-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                }

                .session-indicator.active {
                    background: #00ff00;
                    box-shadow: 0 0 10px #00ff00;
                }

                .session-indicator.inactive {
                    background: #ff0000;
                    box-shadow: 0 0 10px #ff0000;
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                .metric-value {
                    font-size: 2em;
                    font-weight: bold;
                    color: var(--primary-color, #007bff);
                }

                .panel-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }

                .event-item {
                    padding: 10px;
                    border-bottom: 1px solid var(--border-color, #e9ecef);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    transition: background 0.3s;
                }

                .event-item:hover {
                    background: var(--hover-bg, rgba(0,0,0,0.05));
                }

                .pattern-badge {
                    background: #28a745;
                    color: white;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 0.85em;
                }

                .confidence-high { color: #28a745; font-weight: bold; }
                .confidence-medium { color: #ffc107; }
                .confidence-low { color: #6c757d; }

                .alert-rsi-overbought {
                    background: linear-gradient(135deg, #ff6b6b, #ff8787);
                    color: white;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 8px;
                    animation: slideIn 0.3s ease-out;
                }

                .alert-rsi-oversold {
                    background: linear-gradient(135deg, #51cf66, #69db7c);
                    color: white;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 8px;
                    animation: slideIn 0.3s ease-out;
                }

                @keyframes slideIn {
                    from {
                        transform: translateX(-100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }

                /* Dark theme support */
                body.dark-theme .streaming-dashboard {
                    color: var(--text-primary);
                }

                body.dark-theme .card {
                    background: var(--bg-secondary);
                    border-color: var(--border-color);
                }

                body.dark-theme .event-item {
                    border-color: var(--border-color);
                }
            </style>
        `;

        this.container.innerHTML = html;
    }

    /**
     * Setup WebSocket event handlers
     */
    setupEventHandlers() {
        // Remove old handlers if they exist
        this.removeEventHandlers();

        // Session events
        this.socket.on('streaming_session', this.handleStreamingSession);

        // Pattern events
        this.socket.on('streaming_pattern', this.handleStreamingPattern);
        this.socket.on('streaming_patterns_batch', this.handleStreamingPatternsBatch);

        // Indicator events
        this.socket.on('indicator_alert', this.handleIndicatorAlert);

        // Health events
        this.socket.on('streaming_health', this.handleStreamingHealth);

        // Critical alerts
        this.socket.on('critical_alert', this.handleCriticalAlert);

        console.log('[StreamingDashboard] WebSocket handlers registered');
    }

    /**
     * Remove event handlers
     */
    removeEventHandlers() {
        this.socket.off('streaming_session', this.handleStreamingSession);
        this.socket.off('streaming_pattern', this.handleStreamingPattern);
        this.socket.off('streaming_patterns_batch', this.handleStreamingPatternsBatch);
        this.socket.off('indicator_alert', this.handleIndicatorAlert);
        this.socket.off('streaming_health', this.handleStreamingHealth);
        this.socket.off('critical_alert', this.handleCriticalAlert);
    }

    /**
     * Handle streaming session events
     */
    handleStreamingSession(data) {
        if (data.type === 'streaming_session_started') {
            this.updateSessionStatus(true, data.session);
        } else if (data.type === 'streaming_session_stopped') {
            this.updateSessionStatus(false, null);
        }
    }

    /**
     * Handle pattern detection events
     */
    handleStreamingPattern(data) {
        this.addPatternEvent(data.detection);
        this.patternCount++;
        this.updateMetrics();
        this.updateLastUpdatedTimestamp();
    }

    /**
     * Handle batch pattern events
     */
    handleStreamingPatternsBatch(data) {
        data.patterns.forEach(pattern => {
            this.addPatternEvent(pattern.detection || pattern);
        });
        this.patternCount += data.count;
        this.updateMetrics();
        this.updateLastUpdatedTimestamp();
    }

    /**
     * Handle indicator alert events
     */
    handleIndicatorAlert(data) {
        this.addAlertEvent(data.alert);
        this.alertCount++;
        this.updateMetrics();
        this.updateLastUpdatedTimestamp();
    }

    /**
     * Handle health update events
     */
    handleStreamingHealth(data) {
        this.updateHealthStatus(data.health);
        this.updateSessionMetrics(data.health);
        this.updateLastUpdatedTimestamp();
    }

    /**
     * Handle critical alerts
     */
    handleCriticalAlert(data) {
        this.showCriticalAlert(data.alert);
    }

    /**
     * Update "Last Updated" timestamp
     */
    updateLastUpdatedTimestamp() {
        const lastUpdated = document.getElementById('lastUpdated');
        if (lastUpdated) {
            const now = new Date();
            const timeStr = now.toLocaleTimeString();
            const dateStr = now.toLocaleDateString();
            lastUpdated.textContent = `Last updated: ${dateStr} ${timeStr}`;
            this.lastEventTime = Date.now();
        }
    }

    /**
     * Update session status display
     */
    updateSessionStatus(active, session) {
        const indicator = document.getElementById('sessionIndicator');
        const info = document.getElementById('sessionInfo');

        if (!indicator || !info) return;

        if (active && session) {
            indicator.className = 'session-indicator active';
            const sessionId = session.session_id ? session.session_id.substring(0, 8) : 'Unknown';
            info.textContent = `Session ${sessionId} - Universe: ${session.universe || 'default'}`;
            this.currentSession = session;
        } else {
            indicator.className = 'session-indicator inactive';
            info.textContent = 'Session Stopped';
            this.currentSession = null;
        }

        // Update timestamp
        this.updateLastUpdatedTimestamp();
    }

    /**
     * Add pattern event to display
     */
    addPatternEvent(detection) {
        const stream = document.getElementById('patternStream');
        if (!stream) return;

        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';

        const confidence = detection.confidence || 0;
        const confClass = confidence >= 0.8 ? 'confidence-high' :
                         confidence >= 0.5 ? 'confidence-medium' : 'confidence-low';

        eventItem.innerHTML = `
            <div>
                <span class="pattern-badge">${detection.pattern_type || 'Unknown'}</span>
                <strong class="ms-2">${detection.symbol || 'N/A'}</strong>
            </div>
            <div>
                <span class="${confClass}">${(confidence * 100).toFixed(1)}%</span>
                <small class="ms-2 text-muted">${new Date(detection.timestamp || Date.now()).toLocaleTimeString()}</small>
            </div>
        `;

        // Add to top of stream
        stream.insertBefore(eventItem, stream.firstChild);

        // Limit to 50 items
        while (stream.children.length > 50) {
            stream.removeChild(stream.lastChild);
        }

        // Update counter
        const counter = document.getElementById('patternCount');
        if (counter) {
            counter.textContent = `${this.patternCount} patterns`;
        }
    }

    /**
     * Add alert event to display
     */
    addAlertEvent(alert) {
        const stream = document.getElementById('alertStream');
        if (!stream) return;

        const alertItem = document.createElement('div');

        const alertClass = alert.alert_type?.toLowerCase().includes('overbought') ? 'alert-rsi-overbought' :
                          alert.alert_type?.toLowerCase().includes('oversold') ? 'alert-rsi-oversold' :
                          'alert alert-info';

        alertItem.className = alertClass;
        alertItem.innerHTML = `
            <div class="d-flex justify-content-between">
                <div>
                    <strong>${alert.symbol || 'N/A'}</strong> - ${this.formatAlertType(alert.alert_type)}
                </div>
                <small>${new Date(alert.timestamp || Date.now()).toLocaleTimeString()}</small>
            </div>
            ${alert.data ? `<div class="mt-1"><small>${JSON.stringify(alert.data)}</small></div>` : ''}
        `;

        stream.insertBefore(alertItem, stream.firstChild);

        // Limit to 30 alerts
        while (stream.children.length > 30) {
            stream.removeChild(stream.lastChild);
        }

        // Update counter
        const counter = document.getElementById('alertCount');
        if (counter) {
            counter.textContent = `${this.alertCount} alerts`;
        }
    }

    /**
     * Format alert type for display
     */
    formatAlertType(type) {
        const formats = {
            'RSI_OVERBOUGHT': 'RSI Overbought',
            'RSI_OVERSOLD': 'RSI Oversold',
            'MACD_BULLISH_CROSS': 'MACD Bullish Cross',
            'MACD_BEARISH_CROSS': 'MACD Bearish Cross',
            'BB_UPPER_BREAK': 'Upper Bollinger Break',
            'BB_LOWER_BREAK': 'Lower Bollinger Break'
        };
        return formats[type] || type || 'Alert';
    }

    /**
     * Update health status display
     */
    updateHealthStatus(health) {
        const statusDiv = document.getElementById('healthStatus');
        if (!statusDiv) return;

        const statusClass = health.status === 'healthy' ? 'alert-success' :
                           health.status === 'warning' ? 'alert-warning' : 'alert-danger';

        const icon = health.status === 'healthy' ? 'check-circle' :
                    health.status === 'warning' ? 'exclamation-triangle' : 'times-circle';

        const issues = health.issues && health.issues.length > 0 ?
                      `<br>Issues: ${health.issues.join(', ')}` : '';

        statusDiv.innerHTML = `
            <div class="alert ${statusClass} health-status">
                <i class="fas fa-${icon}"></i>
                <strong>Status: ${(health.status || 'Unknown').toUpperCase()}</strong><br>
                Active Symbols: ${health.active_symbols || 0}<br>
                Data Flow: ${health.data_flow?.ticks_per_second || 0} ticks/sec
                ${issues}
            </div>
        `;

        this.healthStatus = health;
    }

    /**
     * Update session metrics
     */
    updateSessionMetrics(health) {
        if (health.active_symbols !== undefined) {
            const elem = document.getElementById('activeSymbols');
            if (elem) elem.textContent = health.active_symbols;
        }

        if (health.data_flow?.ticks_per_second !== undefined) {
            const elem = document.getElementById('eventsPerSecond');
            if (elem) elem.textContent = Math.round(health.data_flow.ticks_per_second);
        }
    }

    /**
     * Update metrics display
     */
    updateMetrics() {
        const patterns = document.getElementById('patternsDetected');
        if (patterns) patterns.textContent = this.patternCount;

        const alerts = document.getElementById('indicatorAlerts');
        if (alerts) alerts.textContent = this.alertCount;
    }

    /**
     * Show critical alert
     */
    showCriticalAlert(alert) {
        // Show browser notification if permitted
        if (Notification.permission === "granted") {
            new Notification("Critical Alert", {
                body: `${alert.type}: ${alert.message}`,
                icon: '/static/images/alert-icon.png'
            });
        }

        // Update health status to show critical
        const statusDiv = document.getElementById('healthStatus');
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-danger health-status">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>CRITICAL: ${alert.message}</strong>
                </div>
            `;
        }
    }

    /**
     * Load initial streaming status
     */
    async loadStreamingStatus() {
        try {
            const response = await fetch('/streaming/api/status', {
                credentials: 'same-origin'  // Include cookies for authentication
            });
            if (response.ok) {
                const data = await response.json();

                // Check if streaming service is online
                if (data.status === 'offline') {
                    this.showOfflineStatus();
                    return;
                }

                if (data.session) {
                    this.updateSessionStatus(true, data.session);
                } else {
                    // No active session but service is online
                    this.updateSessionStatus(false, null);
                }

                if (data.health) {
                    this.updateHealthStatus(data.health);
                    this.updateSessionMetrics(data.health);
                }
            } else {
                this.showOfflineStatus();
            }
        } catch (error) {
            console.error('[StreamingDashboard] Error loading status:', error);
            this.showOfflineStatus();
        }
    }

    /**
     * Show offline status when TickStockPL is not running
     */
    showOfflineStatus() {
        const indicator = document.getElementById('sessionIndicator');
        const info = document.getElementById('sessionInfo');
        const healthStatus = document.getElementById('healthStatus');

        if (indicator && info) {
            indicator.className = 'session-indicator inactive';
            info.innerHTML = '<span class="text-warning">TickStockPL Service Offline</span>';
        }

        if (healthStatus) {
            healthStatus.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>TickStockPL Service Not Available</strong><br>
                    The pattern detection service (TickStockPL) is not currently running.<br>
                    <small>Streaming data will be available when the service is started during market hours.</small>
                </div>
            `;
        }
    }

    /**
     * Refresh the dashboard
     */
    refresh() {
        this.loadStreamingStatus();
        this.updateLastUpdatedTimestamp();
        console.log('[StreamingDashboard] Refreshed');
    }

    /**
     * Cleanup when leaving the dashboard
     */
    cleanup() {
        this.removeEventHandlers();
        this.initialized = false;
        console.log('[StreamingDashboard] Cleaned up');
    }
}

// Export for use in sidebar navigation
window.StreamingDashboardService = StreamingDashboardService;