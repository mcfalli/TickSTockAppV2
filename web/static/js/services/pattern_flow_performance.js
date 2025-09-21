// ==========================================================================
// PATTERN FLOW PERFORMANCE MONITOR - SPRINT 26
// ==========================================================================
// PURPOSE: Performance monitoring and optimization for Pattern Flow Service
// TARGETS: <100ms WebSocket delivery, <50ms UI updates
// ==========================================================================

class PatternFlowPerformanceMonitor {
    constructor(patternFlowService) {
        this.service = patternFlowService;
        this.metrics = {
            websocket: {
                avgLatency: 0,
                maxLatency: 0,
                minLatency: Infinity,
                messagesReceived: 0,
                lastMeasurement: null
            },
            uiUpdates: {
                avgRenderTime: 0,
                maxRenderTime: 0,
                minRenderTime: Infinity,
                updateCount: 0,
                lastMeasurement: null
            },
            memory: {
                heapUsed: 0,
                heapLimit: 0,
                lastMeasurement: null
            },
            performance: {
                fps: 60,
                frameDrops: 0,
                lastFrameTime: performance.now()
            }
        };

        this.thresholds = {
            websocketLatency: 100,    // Target: <100ms
            uiRenderTime: 50,          // Target: <50ms
            memoryLimit: 50 * 1024 * 1024,  // 50MB
            minFPS: 30
        };

        this.monitoring = false;
        this.monitoringInterval = null;
    }

    startMonitoring() {
        if (this.monitoring) return;

        console.log('[Performance Monitor] Starting monitoring...');
        this.monitoring = true;

        // Patch service methods to measure performance
        this.patchServiceMethods();

        // Start periodic monitoring
        this.monitoringInterval = setInterval(() => {
            this.collectMetrics();
            this.checkThresholds();
        }, 5000); // Check every 5 seconds

        // Monitor frame rate
        this.monitorFrameRate();
    }

    stopMonitoring() {
        if (!this.monitoring) return;

        console.log('[Performance Monitor] Stopping monitoring...');
        this.monitoring = false;

        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }

        // Restore original methods
        this.restoreServiceMethods();
    }

    patchServiceMethods() {
        // Store original methods
        this._originalHandleNewPattern = this.service.handleNewPattern;
        this._originalRenderPatterns = this.service.renderPatterns;
        this._originalRefreshAllColumns = this.service.refreshAllColumns;

        // Patch handleNewPattern to measure WebSocket latency
        this.service.handleNewPattern = (data) => {
            const startTime = performance.now();

            // Call original method
            if (this._originalHandleNewPattern) {
                this._originalHandleNewPattern.call(this.service, data);
            }

            // Measure latency
            const latency = performance.now() - startTime;
            this.recordWebSocketLatency(latency);
        };

        // Patch renderPatterns to measure UI update time
        this.service.renderPatterns = (tier) => {
            const startTime = performance.now();

            // Call original method
            if (this._originalRenderPatterns) {
                this._originalRenderPatterns.call(this.service, tier);
            }

            // Measure render time
            const renderTime = performance.now() - startTime;
            this.recordUIRenderTime(renderTime);
        };

        // Patch refreshAllColumns to measure full refresh time
        this.service.refreshAllColumns = async () => {
            const startTime = performance.now();

            // Call original method
            if (this._originalRefreshAllColumns) {
                await this._originalRefreshAllColumns.call(this.service);
            }

            // Measure refresh time
            const refreshTime = performance.now() - startTime;
            console.log(`[Performance Monitor] Full refresh completed in ${refreshTime.toFixed(2)}ms`);
        };
    }

    restoreServiceMethods() {
        if (this._originalHandleNewPattern) {
            this.service.handleNewPattern = this._originalHandleNewPattern;
        }
        if (this._originalRenderPatterns) {
            this.service.renderPatterns = this._originalRenderPatterns;
        }
        if (this._originalRefreshAllColumns) {
            this.service.refreshAllColumns = this._originalRefreshAllColumns;
        }
    }

    recordWebSocketLatency(latency) {
        const ws = this.metrics.websocket;
        ws.messagesReceived++;
        ws.avgLatency = ((ws.avgLatency * (ws.messagesReceived - 1)) + latency) / ws.messagesReceived;
        ws.maxLatency = Math.max(ws.maxLatency, latency);
        ws.minLatency = Math.min(ws.minLatency, latency);
        ws.lastMeasurement = performance.now();

        // Log if exceeds threshold
        if (latency > this.thresholds.websocketLatency) {
            console.warn(`[Performance Monitor] WebSocket latency exceeded threshold: ${latency.toFixed(2)}ms > ${this.thresholds.websocketLatency}ms`);
        }
    }

    recordUIRenderTime(renderTime) {
        const ui = this.metrics.uiUpdates;
        ui.updateCount++;
        ui.avgRenderTime = ((ui.avgRenderTime * (ui.updateCount - 1)) + renderTime) / ui.updateCount;
        ui.maxRenderTime = Math.max(ui.maxRenderTime, renderTime);
        ui.minRenderTime = Math.min(ui.minRenderTime, renderTime);
        ui.lastMeasurement = performance.now();

        // Log if exceeds threshold
        if (renderTime > this.thresholds.uiRenderTime) {
            console.warn(`[Performance Monitor] UI render time exceeded threshold: ${renderTime.toFixed(2)}ms > ${this.thresholds.uiRenderTime}ms`);
        }
    }

    monitorFrameRate() {
        const measureFPS = () => {
            if (!this.monitoring) return;

            const now = performance.now();
            const delta = now - this.metrics.performance.lastFrameTime;
            const fps = 1000 / delta;

            // Update FPS using exponential moving average
            this.metrics.performance.fps = (this.metrics.performance.fps * 0.9) + (fps * 0.1);

            // Check for frame drops
            if (fps < this.thresholds.minFPS) {
                this.metrics.performance.frameDrops++;
            }

            this.metrics.performance.lastFrameTime = now;

            requestAnimationFrame(measureFPS);
        };

        requestAnimationFrame(measureFPS);
    }

    collectMetrics() {
        // Collect memory metrics if available
        if (performance.memory) {
            this.metrics.memory.heapUsed = performance.memory.usedJSHeapSize;
            this.metrics.memory.heapLimit = performance.memory.jsHeapSizeLimit;
            this.metrics.memory.lastMeasurement = performance.now();

            // Check memory usage
            if (this.metrics.memory.heapUsed > this.thresholds.memoryLimit) {
                console.warn(`[Performance Monitor] Memory usage high: ${(this.metrics.memory.heapUsed / 1024 / 1024).toFixed(2)}MB`);
            }
        }
    }

    checkThresholds() {
        const violations = [];

        // Check WebSocket latency
        if (this.metrics.websocket.avgLatency > this.thresholds.websocketLatency) {
            violations.push({
                metric: 'WebSocket Latency',
                value: this.metrics.websocket.avgLatency.toFixed(2),
                threshold: this.thresholds.websocketLatency,
                unit: 'ms'
            });
        }

        // Check UI render time
        if (this.metrics.uiUpdates.avgRenderTime > this.thresholds.uiRenderTime) {
            violations.push({
                metric: 'UI Render Time',
                value: this.metrics.uiUpdates.avgRenderTime.toFixed(2),
                threshold: this.thresholds.uiRenderTime,
                unit: 'ms'
            });
        }

        // Check FPS
        if (this.metrics.performance.fps < this.thresholds.minFPS) {
            violations.push({
                metric: 'Frame Rate',
                value: this.metrics.performance.fps.toFixed(1),
                threshold: this.thresholds.minFPS,
                unit: 'FPS'
            });
        }

        // Log violations
        if (violations.length > 0) {
            console.warn('[Performance Monitor] Threshold violations detected:', violations);
        }
    }

    getPerformanceReport() {
        const ws = this.metrics.websocket;
        const ui = this.metrics.uiUpdates;
        const perf = this.metrics.performance;
        const mem = this.metrics.memory;

        return {
            websocket: {
                avgLatency: `${ws.avgLatency.toFixed(2)}ms`,
                maxLatency: `${ws.maxLatency.toFixed(2)}ms`,
                minLatency: ws.minLatency === Infinity ? 'N/A' : `${ws.minLatency.toFixed(2)}ms`,
                messagesReceived: ws.messagesReceived,
                status: ws.avgLatency <= this.thresholds.websocketLatency ? 'PASS' : 'FAIL'
            },
            uiUpdates: {
                avgRenderTime: `${ui.avgRenderTime.toFixed(2)}ms`,
                maxRenderTime: `${ui.maxRenderTime.toFixed(2)}ms`,
                minRenderTime: ui.minRenderTime === Infinity ? 'N/A' : `${ui.minRenderTime.toFixed(2)}ms`,
                updateCount: ui.updateCount,
                status: ui.avgRenderTime <= this.thresholds.uiRenderTime ? 'PASS' : 'FAIL'
            },
            performance: {
                fps: perf.fps.toFixed(1),
                frameDrops: perf.frameDrops,
                status: perf.fps >= this.thresholds.minFPS ? 'PASS' : 'FAIL'
            },
            memory: {
                heapUsed: `${(mem.heapUsed / 1024 / 1024).toFixed(2)}MB`,
                heapLimit: `${(mem.heapLimit / 1024 / 1024).toFixed(2)}MB`,
                usage: `${((mem.heapUsed / mem.heapLimit) * 100).toFixed(1)}%`,
                status: mem.heapUsed <= this.thresholds.memoryLimit ? 'PASS' : 'FAIL'
            },
            targets: {
                websocketLatency: `<${this.thresholds.websocketLatency}ms`,
                uiRenderTime: `<${this.thresholds.uiRenderTime}ms`,
                minFPS: `>${this.thresholds.minFPS}`,
                memoryLimit: `<${(this.thresholds.memoryLimit / 1024 / 1024).toFixed(0)}MB`
            }
        };
    }

    displayReport() {
        const report = this.getPerformanceReport();
        console.group('[Performance Monitor] Performance Report');
        console.table({
            'WebSocket Latency': {
                Average: report.websocket.avgLatency,
                Max: report.websocket.maxLatency,
                Messages: report.websocket.messagesReceived,
                Status: report.websocket.status
            },
            'UI Rendering': {
                Average: report.uiUpdates.avgRenderTime,
                Max: report.uiUpdates.maxRenderTime,
                Updates: report.uiUpdates.updateCount,
                Status: report.uiUpdates.status
            },
            'Frame Rate': {
                FPS: report.performance.fps,
                Drops: report.performance.frameDrops,
                Status: report.performance.status
            },
            'Memory Usage': {
                Used: report.memory.heapUsed,
                Percentage: report.memory.usage,
                Status: report.memory.status
            }
        });
        console.log('Performance Targets:', report.targets);
        console.groupEnd();
        return report;
    }

    reset() {
        // Reset all metrics
        this.metrics.websocket = {
            avgLatency: 0,
            maxLatency: 0,
            minLatency: Infinity,
            messagesReceived: 0,
            lastMeasurement: null
        };
        this.metrics.uiUpdates = {
            avgRenderTime: 0,
            maxRenderTime: 0,
            minRenderTime: Infinity,
            updateCount: 0,
            lastMeasurement: null
        };
        this.metrics.performance.frameDrops = 0;
        console.log('[Performance Monitor] Metrics reset');
    }
}

// Export for use in Pattern Flow Service
window.PatternFlowPerformanceMonitor = PatternFlowPerformanceMonitor;
console.log('[Performance Monitor] Module loaded');