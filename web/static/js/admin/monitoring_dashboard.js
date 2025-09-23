/**
 * TickStockPL Monitoring Dashboard
 * Real-time system health monitoring via Redis pub/sub
 * Sprint 31 Implementation
 */

class MonitoringDashboard {
    constructor() {
        this.eventSource = null;
        this.updateInterval = null;
        this.metrics = {};
        this.alerts = new Map();
        this.healthStatus = {};
        this.lastUpdate = null;

        this.initializeElements();
        this.startMonitoring();
        this.setupEventHandlers();
        this.initializeGauges();
    }

    initializeElements() {
        // Status indicators
        this.redisStatus = document.getElementById('redis-status');
        this.tickstockStatus = document.getElementById('tickstockpl-status');

        // System metrics
        this.cpuValue = document.getElementById('cpu-value');
        this.cpuTrend = document.getElementById('cpu-trend');
        this.memoryValue = document.getElementById('memory-value');
        this.memoryTrend = document.getElementById('memory-trend');
        this.threadsValue = document.getElementById('threads-value');
        this.uptimeValue = document.getElementById('uptime-value');

        // Processing metrics
        this.patternTime = document.getElementById('pattern-time');
        this.indicatorTime = document.getElementById('indicator-time');
        this.symbolsCount = document.getElementById('symbols-count');
        this.dbQueryTime = document.getElementById('db-query-time');

        // Database & Redis
        this.dbConnections = document.getElementById('db-connections');
        this.slowQueries = document.getElementById('slow-queries');
        this.redisMessages = document.getElementById('redis-messages');
        this.redisClients = document.getElementById('redis-clients');

        // Health
        this.healthScore = document.getElementById('health-score');
        this.healthStatus = document.getElementById('health-status');
        this.alertCount = document.getElementById('alert-count');
        this.alertsContainer = document.getElementById('alerts-container');
    }

    startMonitoring() {
        // Start polling for status
        this.checkMonitoringStatus();

        // Set up regular polling (every 5 seconds)
        this.updateInterval = setInterval(() => {
            this.checkMonitoringStatus();
        }, 5000);

        // Set up Server-Sent Events for real-time updates
        this.connectToEventStream();
    }

    connectToEventStream() {
        // Poll for real metrics from the backend
        // The backend receives events from TickStockPL via Redis subscription
        setInterval(() => {
            this.fetchLatestMetrics();
        }, 5000);
    }

    async checkMonitoringStatus() {
        try {
            const response = await fetch('/api/admin/monitoring/status');
            const data = await response.json();

            if (data.success) {
                this.updateConnectionStatus(data);
            }
        } catch (error) {
            console.error('Error checking monitoring status:', error);
            this.updateConnectionStatus({ redis: 'disconnected' });
        }
    }

    updateConnectionStatus(status) {
        // Update Redis status
        if (status.redis === 'connected') {
            this.redisStatus.className = 'status-indicator status-connected';
            this.redisStatus.innerHTML = '<i class="fas fa-circle me-1"></i> Redis: Connected';
        } else {
            this.redisStatus.className = 'status-indicator status-disconnected';
            this.redisStatus.innerHTML = '<i class="fas fa-circle me-1"></i> Redis: Disconnected';
        }

        // Update TickStockPL status based on recent updates
        if (status.latest_update) {
            const lastUpdate = new Date(status.latest_update);
            const now = new Date();
            const diffSeconds = (now - lastUpdate) / 1000;

            if (diffSeconds < 30) {
                this.tickstockStatus.className = 'status-indicator status-connected';
                this.tickstockStatus.innerHTML = '<i class="fas fa-circle me-1"></i> TickStockPL: Active';
            } else if (diffSeconds < 60) {
                this.tickstockStatus.className = 'status-indicator status-degraded';
                this.tickstockStatus.innerHTML = '<i class="fas fa-circle me-1"></i> TickStockPL: Delayed';
            } else {
                this.tickstockStatus.className = 'status-indicator status-disconnected';
                this.tickstockStatus.innerHTML = '<i class="fas fa-circle me-1"></i> TickStockPL: Inactive';
            }
        }

        // Update alert count
        if (status.active_alerts !== undefined) {
            this.alertCount.textContent = status.active_alerts;
            this.alertCount.style.display = status.active_alerts > 0 ? 'inline-block' : 'none';
        }
    }

    async fetchLatestMetrics() {
        try {
            // Fetch real metrics stored by the monitoring subscriber
            const response = await fetch('/api/admin/monitoring/status');
            const data = await response.json();

            if (data.success && data.latest_metrics && Object.keys(data.latest_metrics).length > 0) {
                // We have real data from TickStockPL!
                console.log('Received real monitoring data from TickStockPL');
                this.handleMetricUpdate(data.latest_metrics);

                // Also update health status if available
                if (data.health_status && Object.keys(data.health_status).length > 0) {
                    this.healthStatus = data.health_status;
                }
            } else {
                console.log('Waiting for monitoring data from TickStockPL...');
            }
        } catch (error) {
            console.error('Error fetching metrics:', error);
        }
    }

    handleMetricUpdate(event) {
        this.metrics = event.metrics || {};
        this.lastUpdate = new Date();

        // Update system metrics
        if (this.metrics.system) {
            this.updateSystemMetrics(this.metrics.system);
        }

        // Update application metrics
        if (this.metrics.application) {
            this.updateApplicationMetrics(this.metrics.application);
        }

        // Update database metrics
        if (this.metrics.database) {
            this.updateDatabaseMetrics(this.metrics.database);
        }

        // Update Redis metrics
        if (this.metrics.redis) {
            this.updateRedisMetrics(this.metrics.redis);
        }

        // Update health score
        if (event.health_score) {
            this.updateHealthScore(event.health_score);
        }

        // Update trends
        if (event.trends) {
            this.updateTrends(event.trends);
        }

        // Update recommendations
        if (event.recommendations) {
            this.updateRecommendations(event.recommendations);
        }
    }

    updateSystemMetrics(system) {
        // CPU
        if (this.cpuValue) {
            this.cpuValue.textContent = `${(system.cpu_percent || 0).toFixed(1)}%`;
            this.cpuValue.style.color = this.getMetricColor(system.cpu_percent, [50, 70, 85]);
        }

        // Memory
        if (this.memoryValue) {
            const memoryGB = ((system.memory_mb || 0) / 1024).toFixed(1);
            this.memoryValue.textContent = `${memoryGB}GB`;
            this.memoryValue.style.color = this.getMetricColor(system.memory_percent || 0, [60, 75, 90]);
        }

        // Threads
        if (this.threadsValue) {
            this.threadsValue.textContent = system.thread_count || '--';
        }

        // Update gauges
        this.updateGauge('patterns-gauge', system.patterns_per_second || 0, 50);
    }

    updateApplicationMetrics(app) {
        // Pattern detection time
        if (this.patternTime) {
            this.patternTime.textContent = `${(app.avg_pattern_detection_ms || 0).toFixed(1)} ms`;
        }

        // Indicator calculation time
        if (this.indicatorTime) {
            this.indicatorTime.textContent = `${(app.avg_indicator_calc_ms || 0).toFixed(1)} ms`;
        }

        // Symbols processed
        if (this.symbolsCount) {
            this.symbolsCount.textContent = (app.symbols_processed || 0).toLocaleString();
        }

        // Update gauges
        if (app.patterns_per_second !== undefined) {
            this.updateGauge('patterns-gauge', app.patterns_per_second, 30);
        }
        if (app.indicators_per_second !== undefined) {
            this.updateGauge('indicators-gauge', app.indicators_per_second, 100);
        }
        if (app.cache_hit_rate !== undefined) {
            this.updateGauge('cache-gauge', app.cache_hit_rate * 100, 100);
        }

        // Update timeframe indicators
        this.updateTimeframes(app.active_timeframes || []);
    }

    updateDatabaseMetrics(db) {
        if (this.dbConnections) {
            this.dbConnections.textContent = db.active_connections || '--';
        }

        if (this.slowQueries) {
            this.slowQueries.textContent = db.slow_queries_count || 0;
            if (db.slow_queries_count > 5) {
                this.slowQueries.style.color = 'var(--status-unhealthy)';
            } else {
                this.slowQueries.style.color = '';
            }
        }

        if (this.dbQueryTime) {
            this.dbQueryTime.textContent = `${(db.query_avg_ms || 0).toFixed(1)} ms`;
        }
    }

    updateRedisMetrics(redis) {
        if (this.redisMessages) {
            this.redisMessages.textContent = (redis.messages_per_second || 0).toFixed(1);
        }

        if (this.redisClients) {
            this.redisClients.textContent = redis.connected_clients || '--';
        }
    }

    updateHealthScore(health) {
        const score = health.overall || 0;
        const status = health.status || 'UNKNOWN';

        if (this.healthScore) {
            this.healthScore.textContent = Math.round(score);
        }

        if (this.healthStatus) {
            this.healthStatus.textContent = status;
        }

        // Update health circle
        const healthCircle = document.querySelector('.health-score-circle');
        if (healthCircle) {
            healthCircle.style.setProperty('--health-percent', `${score}%`);
            const color = this.getHealthColor(score);
            healthCircle.style.background = `conic-gradient(${color} ${score * 3.6}deg, #e9ecef ${score * 3.6}deg)`;
        }

        // Update component health
        if (health.components) {
            this.updateComponentHealth(health.components);
        }
    }

    updateComponentHealth(components) {
        Object.entries(components).forEach(([name, data]) => {
            const fillElement = document.getElementById(`health-${name.toLowerCase().replace('_', '-')}`);
            const scoreElement = document.getElementById(`score-${name.toLowerCase().replace('_', '-')}`);

            if (fillElement && scoreElement) {
                const score = data.score || data;
                fillElement.style.width = `${score}%`;
                fillElement.style.background = this.getHealthColor(score);
                scoreElement.textContent = Math.round(score);
            }
        });
    }

    updateTrends(trends) {
        // CPU trend
        if (trends.cpu && this.cpuTrend) {
            this.updateTrendIndicator(this.cpuTrend, trends.cpu);
        }

        // Memory trend
        if (trends.memory && this.memoryTrend) {
            this.updateTrendIndicator(this.memoryTrend, trends.memory);
        }
    }

    updateTrendIndicator(element, trend) {
        if (trend.direction === 'INCREASING') {
            element.className = 'metric-trend trend-up';
            element.innerHTML = '<i class="fas fa-arrow-up"></i> Increasing';
        } else if (trend.direction === 'DECREASING') {
            element.className = 'metric-trend trend-down';
            element.innerHTML = '<i class="fas fa-arrow-down"></i> Decreasing';
        } else {
            element.className = 'metric-trend trend-stable';
            element.innerHTML = '<i class="fas fa-minus"></i> Stable';
        }

        if (trend.prediction_1h) {
            element.innerHTML += ` (1h: ${trend.prediction_1h.toFixed(1)})`;
        }
    }

    updateTimeframes(activeTimeframes) {
        const allTimeframes = ['1min', '5min', 'hourly', 'daily', 'weekly', 'monthly'];
        const container = document.getElementById('timeframe-indicators');

        if (!container) return;

        container.innerHTML = allTimeframes.map(tf => {
            const displayName = tf === '1min' ? '1min' : tf === '5min' ? '5min' : tf;
            const isActive = activeTimeframes.includes(tf) || activeTimeframes.includes(displayName);
            const className = isActive ? 'timeframe-badge timeframe-active' : 'timeframe-badge timeframe-inactive';
            return `<span class="${className}">${displayName}</span>`;
        }).join('');
    }

    updateRecommendations(recommendations) {
        const container = document.getElementById('recommendations-container');
        const list = document.getElementById('recommendations-list');

        if (!container || !list) return;

        if (recommendations && recommendations.length > 0) {
            container.style.display = 'block';
            list.innerHTML = recommendations.map(rec => `<li><i class="fas fa-info-circle text-info me-1"></i> ${rec}</li>`).join('');
        } else {
            container.style.display = 'none';
        }
    }

    handleAlertTriggered(alert) {
        this.alerts.set(alert.id, alert);
        this.renderAlerts();
        this.showNotification(alert);
    }

    handleAlertResolved(alertId) {
        this.alerts.delete(alertId);
        this.renderAlerts();
    }

    renderAlerts() {
        if (this.alerts.size === 0) {
            this.alertsContainer.innerHTML = '<p class="text-muted">No active alerts</p>';
            this.alertCount.textContent = '0';
            this.alertCount.style.display = 'none';
            return;
        }

        this.alertCount.textContent = this.alerts.size;
        this.alertCount.style.display = 'inline-block';

        // Sort alerts by severity
        const severityOrder = { EMERGENCY: 0, CRITICAL: 1, WARNING: 2, INFO: 3 };
        const sortedAlerts = Array.from(this.alerts.values()).sort((a, b) =>
            (severityOrder[a.level] || 999) - (severityOrder[b.level] || 999)
        );

        this.alertsContainer.innerHTML = sortedAlerts.map(alert => this.renderAlert(alert)).join('');
    }

    renderAlert(alert) {
        const levelClass = `alert-${alert.level.toLowerCase()}`;
        const levelColor = {
            INFO: 'info',
            WARNING: 'warning',
            CRITICAL: 'danger',
            EMERGENCY: 'danger'
        }[alert.level] || 'secondary';

        return `
            <div class="alert-item ${levelClass}">
                <div class="alert-header">
                    <span class="alert-level bg-${levelColor} text-white">${alert.level}</span>
                    <small class="text-muted">${this.formatTime(alert.timestamp)}</small>
                </div>
                <div class="fw-bold mt-2">${alert.message}</div>
                ${alert.details ? `<div class="small text-muted mt-1">${JSON.stringify(alert.details)}</div>` : ''}
                ${alert.suggested_actions ? `
                    <div class="alert-actions">
                        <small><strong>Suggested Actions:</strong></small>
                        <ul class="small mb-0">
                            ${alert.suggested_actions.map(action => `<li>${action}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary" onclick="monitoringDashboard.acknowledgeAlert('${alert.id}')">
                        Acknowledge
                    </button>
                    <button class="btn btn-sm btn-outline-success" onclick="monitoringDashboard.resolveAlert('${alert.id}')">
                        Resolve
                    </button>
                </div>
            </div>
        `;
    }

    async acknowledgeAlert(alertId) {
        try {
            const response = await fetch(`/api/admin/monitoring/alerts/${alertId}/acknowledge`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();
            if (result.success) {
                this.showNotification({ message: 'Alert acknowledged' }, 'success');
            }
        } catch (error) {
            console.error('Error acknowledging alert:', error);
            this.showNotification({ message: 'Failed to acknowledge alert' }, 'error');
        }
    }

    async resolveAlert(alertId) {
        const notes = prompt('Resolution notes (optional):');

        try {
            const response = await fetch(`/api/admin/monitoring/alerts/${alertId}/resolve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ notes })
            });

            const result = await response.json();
            if (result.success) {
                this.handleAlertResolved(alertId);
                this.showNotification({ message: 'Alert resolved' }, 'success');
            }
        } catch (error) {
            console.error('Error resolving alert:', error);
            this.showNotification({ message: 'Failed to resolve alert' }, 'error');
        }
    }

    async forceHealthCheck() {
        try {
            const response = await fetch('/api/admin/monitoring/health-check', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();
            if (result.success) {
                this.showNotification({ message: 'Health check requested' }, 'success');
            }
        } catch (error) {
            console.error('Error requesting health check:', error);
            this.showNotification({ message: 'Failed to request health check' }, 'error');
        }
    }

    async triggerAction(action) {
        if (!confirm(`Are you sure you want to ${action.replace(/_/g, ' ')}?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/admin/monitoring/actions/${action}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();
            if (result.success) {
                this.showNotification({ message: `Action '${action}' triggered` }, 'success');
            } else {
                this.showNotification({ message: result.message || 'Action failed' }, 'error');
            }
        } catch (error) {
            console.error(`Error triggering action ${action}:`, error);
            this.showNotification({ message: 'Failed to trigger action' }, 'error');
        }
    }

    initializeGauges() {
        // Initialize canvas gauges
        this.gauges = {
            patterns: this.createGauge('patterns-gauge'),
            indicators: this.createGauge('indicators-gauge'),
            cache: this.createGauge('cache-gauge')
        };
    }

    createGauge(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');
        return { canvas, ctx };
    }

    updateGauge(gaugeId, value, max) {
        const gauge = this.gauges[gaugeId.replace('-gauge', '')];
        if (!gauge) return;

        const { canvas, ctx } = gauge;
        const width = canvas.width;
        const height = canvas.height;
        const centerX = width / 2;
        const centerY = height - 20;
        const radius = 60;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Draw background arc
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, 2 * Math.PI, false);
        ctx.lineWidth = 15;
        ctx.strokeStyle = '#e9ecef';
        ctx.stroke();

        // Draw value arc
        const percent = Math.min(value / max, 1);
        const endAngle = Math.PI + (Math.PI * percent);

        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, endAngle, false);
        ctx.lineWidth = 15;
        ctx.strokeStyle = this.getHealthColor(percent * 100);
        ctx.stroke();

        // Draw value text
        ctx.font = 'bold 24px Arial';
        ctx.fillStyle = '#333';
        ctx.textAlign = 'center';
        ctx.fillText(value.toFixed(1), centerX, centerY);
    }

    getMetricColor(value, thresholds) {
        if (value <= thresholds[0]) return 'var(--status-healthy)';
        if (value <= thresholds[1]) return 'var(--status-degraded)';
        if (value <= thresholds[2]) return 'var(--status-unhealthy)';
        return 'var(--status-critical)';
    }

    getHealthColor(score) {
        if (score >= 90) return '#00aa00';
        if (score >= 75) return '#88cc00';
        if (score >= 60) return '#ffaa00';
        if (score >= 40) return '#ff6600';
        return '#cc0000';
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = (now - date) / 1000;

        if (diff < 60) return 'just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return date.toLocaleString();
    }

    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        if (days > 0) return `${days}d ${hours}h`;
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    }

    showNotification(alert, type = 'info') {
        const notification = document.getElementById('notification');
        if (!notification) return;

        const message = alert.message || alert;
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.display = 'block';

        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);
    }

    getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) return metaTag.content;

        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrf_token='));

        if (cookieValue) {
            return cookieValue.split('=')[1];
        }

        return '';
    }

    setupEventHandlers() {
        // Handle uptime updates
        setInterval(() => {
            if (this.healthStatus && this.healthStatus.uptime_seconds) {
                this.uptimeValue.textContent = this.formatUptime(this.healthStatus.uptime_seconds);
            }
        }, 1000);
    }

    // Generate test metrics for development
    generateTestMetrics() {
        return {
            event_type: 'METRIC_UPDATE',
            timestamp: new Date().toISOString(),
            metrics: {
                system: {
                    cpu_percent: 30 + Math.random() * 40,
                    memory_percent: 40 + Math.random() * 30,
                    memory_mb: 2000 + Math.random() * 2000,
                    thread_count: Math.floor(8 + Math.random() * 8),
                    patterns_per_second: 10 + Math.random() * 20
                },
                application: {
                    patterns_per_second: 10 + Math.random() * 15,
                    indicators_per_second: 30 + Math.random() * 30,
                    avg_pattern_detection_ms: 5 + Math.random() * 10,
                    avg_indicator_calc_ms: 2 + Math.random() * 5,
                    cache_hit_rate: 0.85 + Math.random() * 0.14,
                    symbols_processed: Math.floor(1000 + Math.random() * 1000),
                    active_timeframes: ['daily', 'hourly', 'minute']
                },
                database: {
                    active_connections: Math.floor(5 + Math.random() * 10),
                    query_avg_ms: 10 + Math.random() * 20,
                    slow_queries_count: Math.floor(Math.random() * 5)
                },
                redis: {
                    messages_per_second: 50 + Math.random() * 100,
                    connected_clients: Math.floor(3 + Math.random() * 5),
                    memory_usage_mb: 32 + Math.random() * 32
                }
            },
            health_score: {
                overall: 85 + Math.random() * 14,
                status: 'HEALTHY',
                components: {
                    pattern_detection: 90 + Math.random() * 9,
                    database: 85 + Math.random() * 10,
                    redis: 95 + Math.random() * 4,
                    memory: 80 + Math.random() * 15
                }
            },
            trends: {
                cpu: {
                    direction: ['STABLE', 'INCREASING', 'DECREASING'][Math.floor(Math.random() * 3)],
                    rate: Math.random() * 2,
                    prediction_1h: 35 + Math.random() * 30
                },
                memory: {
                    direction: ['STABLE', 'INCREASING'][Math.floor(Math.random() * 2)],
                    rate: Math.random() * 1,
                    prediction_1h: 2500 + Math.random() * 1000
                }
            },
            recommendations: Math.random() > 0.7 ? [
                'Consider increasing cache TTL for better hit rate',
                'Database queries averaging above baseline'
            ] : []
        };
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.monitoringDashboard = new MonitoringDashboard();
});