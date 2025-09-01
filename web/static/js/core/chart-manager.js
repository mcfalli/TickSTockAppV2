// ==========================================================================
// TICKSTOCK CHART MANAGER - SPRINT 12
// ==========================================================================
// VERSION: 1.0.0 - Sprint 12 Chart.js Integration
// PURPOSE: Chart.js integration for OHLCV candlestick charts with real-time updates
// ==========================================================================

class ChartManager {
    constructor() {
        this.chart = null;
        this.chartData = [];
        this.currentSymbol = null;
        this.currentTimeframe = '1d';
        this.isInitialized = false;
        this.activeIndicators = new Map(); // Track active technical indicators
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.isInitialized = true;
        console.log('[ChartManager] Initialized');
    }

    setupEventListeners() {
        // Symbol selection
        document.addEventListener('change', (e) => {
            if (e.target.id === 'chart-symbol-select') {
                this.onSymbolChange(e.target.value);
            }
        });

        // Timeframe selection
        document.addEventListener('change', (e) => {
            if (e.target.name === 'chart-timeframe') {
                this.onTimeframeChange(e.target.value);
            }
        });

        // Technical indicators dropdown
        document.addEventListener('click', (e) => {
            if (e.target.closest('#indicators-menu')) {
                const link = e.target.closest('a[data-indicator]');
                if (link) {
                    e.preventDefault();
                    const indicator = link.getAttribute('data-indicator');
                    const period = link.getAttribute('data-period');
                    
                    if (indicator) {
                        const options = period ? { period: parseInt(period) } : {};
                        this.addTechnicalIndicator(indicator, options);
                    }
                }
            }
            
            // Clear all indicators
            if (e.target.id === 'clear-indicators' || e.target.closest('#clear-indicators')) {
                e.preventDefault();
                this.clearAllIndicators();
            }
        });
    }

    onSymbolChange(symbol) {
        if (symbol && symbol !== this.currentSymbol) {
            this.currentSymbol = symbol;
            this.loadChartData();
        }
    }

    onTimeframeChange(timeframe) {
        if (timeframe !== this.currentTimeframe) {
            this.currentTimeframe = timeframe;
            if (this.currentSymbol) {
                this.loadChartData();
            }
        }
    }

    async loadChartData() {
        if (!this.currentSymbol) return;

        try {
            const response = await fetch(`/api/chart-data/${this.currentSymbol}?timeframe=${this.currentTimeframe}`, {
                headers: {
                    'X-CSRFToken': window.csrfToken || ''
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateChart(data.chart_data);
                } else {
                    console.error('[ChartManager] API error:', data.message);
                    this.showChartError('Failed to load chart data');
                }
            } else {
                console.error('[ChartManager] HTTP error:', response.status);
                this.showChartError('Server error loading chart data');
            }
        } catch (error) {
            console.error('[ChartManager] Network error:', error);
            this.showChartError('Network error loading chart data');
        }
    }

    updateChart(data) {
        const ctx = document.getElementById('price-chart');
        if (!ctx) return;

        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
        }

        // Format data for Chart.js
        const chartData = this.formatChartData(data);

        // Create new chart
        this.chart = new Chart(ctx, {
            type: 'candlestick',
            data: {
                datasets: [{
                    label: `${this.currentSymbol} Price`,
                    data: chartData,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: true,
                        text: `${this.currentSymbol} - ${this.currentTimeframe.toUpperCase()}`
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return new Date(context[0].parsed.x).toLocaleString();
                            },
                            label: function(context) {
                                const data = context.raw;
                                return [
                                    `Open: $${data.o?.toFixed(2) || 'N/A'}`,
                                    `High: $${data.h?.toFixed(2) || 'N/A'}`,
                                    `Low: $${data.l?.toFixed(2) || 'N/A'}`,
                                    `Close: $${data.c?.toFixed(2) || 'N/A'}`,
                                    `Volume: ${data.v?.toLocaleString() || 'N/A'}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: this.getTimeUnit(),
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'MMM dd HH:mm',
                                day: 'MMM dd',
                                week: 'MMM dd',
                                month: 'MMM yyyy'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Price ($)'
                        }
                    }
                }
            }
        });

        this.chartData = data;
        console.log(`[ChartManager] Chart updated for ${this.currentSymbol}`);
    }

    formatChartData(rawData) {
        if (!Array.isArray(rawData)) return [];
        
        return rawData.map(item => ({
            x: new Date(item.timestamp).getTime(),
            o: parseFloat(item.open),
            h: parseFloat(item.high),
            l: parseFloat(item.low),
            c: parseFloat(item.close),
            v: parseInt(item.volume)
        }));
    }

    getTimeUnit() {
        switch (this.currentTimeframe) {
            case '1d': return 'hour';
            case '1w': return 'day';
            case '1m': return 'week';
            default: return 'day';
        }
    }

    showChartError(message) {
        const ctx = document.getElementById('price-chart');
        if (!ctx) return;

        if (this.chart) {
            this.chart.destroy();
        }

        // Show error message in chart container
        const container = ctx.parentElement;
        container.innerHTML = `
            <div class="chart-error text-center p-4">
                <i class="fas fa-exclamation-triangle fa-2x text-warning mb-3"></i>
                <p class="mb-0">${message}</p>
                <button class="btn btn-sm btn-outline-primary mt-2" onclick="chartManager.loadChartData()">
                    <i class="fas fa-refresh me-1"></i>Retry
                </button>
            </div>
        `;
    }

    // Update real-time price data
    updateRealTimePrice(symbol, priceData) {
        if (symbol === this.currentSymbol && this.chart && this.chartData.length > 0) {
            // Update the last data point with current price
            const lastIndex = this.chartData.length - 1;
            if (lastIndex >= 0) {
                const lastPoint = this.chart.data.datasets[0].data[lastIndex];
                if (lastPoint) {
                    lastPoint.c = parseFloat(priceData.price);
                    lastPoint.h = Math.max(lastPoint.h, lastPoint.c);
                    lastPoint.l = Math.min(lastPoint.l, lastPoint.c);
                    
                    this.chart.update('none');
                }
            }
        }
    }

    // Add new OHLCV bar (Phase 2 real-time feature)
    addNewOHLCVBar(ohlcvData) {
        if (!this.chart || !this.currentSymbol) return;

        const newDataPoint = {
            x: new Date(ohlcvData.timestamp).getTime(),
            o: parseFloat(ohlcvData.open),
            h: parseFloat(ohlcvData.high),
            l: parseFloat(ohlcvData.low),
            c: parseFloat(ohlcvData.close),
            v: parseInt(ohlcvData.volume)
        };

        // Add new bar to chart data
        this.chart.data.datasets[0].data.push(newDataPoint);
        this.chartData.push({
            timestamp: ohlcvData.timestamp,
            open: ohlcvData.open,
            high: ohlcvData.high,
            low: ohlcvData.low,
            close: ohlcvData.close,
            volume: ohlcvData.volume
        });

        // Limit data points to prevent memory issues (keep last 1000 bars)
        const maxBars = 1000;
        if (this.chart.data.datasets[0].data.length > maxBars) {
            this.chart.data.datasets[0].data.shift();
            this.chartData.shift();
        }

        this.chart.update('active');
        console.log(`[ChartManager] Added new OHLCV bar for ${this.currentSymbol}`);
    }

    // Update symbol metadata (Phase 2 feature)
    updateSymbolMetadata(symbol, metadata) {
        // Update symbol dropdown if this symbol exists
        const select = document.getElementById('chart-symbol-select');
        if (select) {
            const option = Array.from(select.options).find(opt => opt.value === symbol);
            if (option && metadata.name) {
                option.textContent = `${symbol} - ${metadata.name}`;
            }
        }
    }

    // Request real-time chart data (Phase 2 integration)
    async loadChartDataRealTime() {
        if (!this.currentSymbol) return;

        try {
            // Request real-time data via WebSocket
            if (window.dashboardWebSocketHandler) {
                window.dashboardWebSocketHandler.requestChartData(
                    this.currentSymbol, 
                    this.currentTimeframe
                );
            }

            // Also load via HTTP API as fallback
            await this.loadChartData();
        } catch (error) {
            console.error('[ChartManager] Error loading real-time chart data:', error);
            await this.loadChartData(); // Fallback to HTTP API
        }
    }

    // Load available symbols from API
    async loadAvailableSymbols() {
        try {
            const response = await fetch('/api/symbols/search', {
                headers: {
                    'X-CSRFToken': window.csrfToken || ''
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.symbols) {
                    this.populateSymbolDropdown(data.symbols);
                    console.log('[ChartManager] Loaded', data.symbols.length, 'symbols for charts');
                } else {
                    console.warn('[ChartManager] No symbols returned from API');
                }
            }
        } catch (error) {
            console.error('[ChartManager] Error loading symbols:', error);
        }
    }

    // Populate symbol dropdown
    populateSymbolDropdown(symbols) {
        const select = document.getElementById('chart-symbol-select');
        if (!select) return;

        select.innerHTML = '<option value="">Select a symbol...</option>';
        
        symbols.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol.symbol || symbol;
            option.textContent = symbol.name ? 
                `${symbol.symbol || symbol} - ${symbol.name}` : 
                (symbol.symbol || symbol);
            select.appendChild(option);
        });
        
        console.log('[ChartManager] Populated dropdown with', symbols.length, 'symbols');
    }

    // Technical indicator methods (Phase 2)
    addTechnicalIndicator(indicatorType, options = {}) {
        if (!this.chartData || this.chartData.length === 0) {
            console.warn('[ChartManager] No chart data available for indicators');
            return false;
        }

        if (!window.technicalIndicators) {
            console.error('[ChartManager] Technical indicators library not loaded');
            return false;
        }

        try {
            // Validate parameters
            if (!window.technicalIndicators.validateParameters(indicatorType, options)) {
                console.error('[ChartManager] Invalid parameters for', indicatorType);
                return false;
            }

            // Calculate indicator data
            const indicatorData = window.technicalIndicators.applyIndicator(
                indicatorType, 
                this.chartData, 
                options
            );

            if (!indicatorData || (Array.isArray(indicatorData) && indicatorData.length === 0)) {
                console.warn('[ChartManager] No indicator data generated for', indicatorType);
                return false;
            }

            // Handle different indicator types
            this.addIndicatorToChart(indicatorType, indicatorData, options);
            
            // Track active indicator
            this.activeIndicators.set(`${indicatorType}_${JSON.stringify(options)}`, {
                type: indicatorType,
                options: options,
                data: indicatorData
            });

            console.log(`[ChartManager] Added ${indicatorType} indicator`);
            return true;

        } catch (error) {
            console.error('[ChartManager] Error adding technical indicator:', error);
            return false;
        }
    }

    addIndicatorToChart(indicatorType, indicatorData, options) {
        if (!this.chart) return;

        const colors = {
            sma: '#FF6B6B',
            ema: '#4ECDC4', 
            rsi: '#45B7D1',
            macd: '#96CEB4',
            bollinger: '#FFEAA7',
            volume_ma: '#DDA0DD'
        };

        const color = colors[indicatorType] || '#999999';

        switch (indicatorType.toLowerCase()) {
            case 'sma':
            case 'ema':
                this.chart.data.datasets.push({
                    label: `${indicatorType.toUpperCase()} (${options.period || 20})`,
                    data: indicatorData,
                    type: 'line',
                    borderColor: color,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    yAxisID: 'y'
                });
                break;

            case 'bollinger':
                // Add upper, middle, and lower bands
                ['upper', 'middle', 'lower'].forEach((band, index) => {
                    if (indicatorData[band]) {
                        this.chart.data.datasets.push({
                            label: `BB ${band.charAt(0).toUpperCase() + band.slice(1)}`,
                            data: indicatorData[band],
                            type: 'line',
                            borderColor: color,
                            backgroundColor: index === 1 ? 'transparent' : `${color}20`,
                            borderWidth: index === 1 ? 2 : 1,
                            pointRadius: 0,
                            fill: index !== 1 ? '+1' : false,
                            yAxisID: 'y'
                        });
                    }
                });
                break;

            case 'rsi':
                // RSI needs its own scale (0-100)
                this.addRSIScale();
                this.chart.data.datasets.push({
                    label: `RSI (${options.period || 14})`,
                    data: indicatorData,
                    type: 'line',
                    borderColor: color,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    yAxisID: 'rsi'
                });
                break;

            case 'macd':
                // MACD has multiple components
                if (indicatorData.macd) {
                    this.chart.data.datasets.push({
                        label: 'MACD Line',
                        data: indicatorData.macd,
                        type: 'line',
                        borderColor: color,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 0,
                        yAxisID: 'macd'
                    });
                }
                break;

            case 'volume_ma':
                this.chart.data.datasets.push({
                    label: `Volume MA (${options.period || 20})`,
                    data: indicatorData,
                    type: 'line',
                    borderColor: color,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    yAxisID: 'volume'
                });
                break;
        }

        this.chart.update();
    }

    addRSIScale() {
        if (!this.chart.options.scales.rsi) {
            this.chart.options.scales.rsi = {
                type: 'linear',
                position: 'right',
                min: 0,
                max: 100,
                grid: {
                    drawOnChartArea: false,
                },
                ticks: {
                    callback: function(value) {
                        return value + '%';
                    }
                }
            };
        }
    }

    removeTechnicalIndicator(indicatorKey) {
        if (!this.activeIndicators.has(indicatorKey)) return false;

        // Remove datasets related to this indicator
        const indicator = this.activeIndicators.get(indicatorKey);
        const datasets = this.chart.data.datasets;
        
        for (let i = datasets.length - 1; i >= 0; i--) {
            const dataset = datasets[i];
            if (dataset.label && dataset.label.includes(indicator.type.toUpperCase())) {
                datasets.splice(i, 1);
            }
        }

        this.activeIndicators.delete(indicatorKey);
        this.chart.update();
        
        console.log(`[ChartManager] Removed ${indicator.type} indicator`);
        return true;
    }

    clearAllIndicators() {
        // Keep only the main OHLCV dataset
        this.chart.data.datasets = this.chart.data.datasets.filter(
            dataset => dataset.label && dataset.label.includes(this.currentSymbol)
        );
        
        this.activeIndicators.clear();
        this.chart.update();
        
        console.log('[ChartManager] Cleared all technical indicators');
    }

    getActiveIndicators() {
        return Array.from(this.activeIndicators.keys());
    }

    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        this.activeIndicators.clear();
        this.isInitialized = false;
    }
}

// Global chart manager instance
let chartManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart !== 'undefined') {
        // Register Chart.js candlestick controller if available
        if (Chart.CandlestickController) {
            Chart.register(Chart.CandlestickController);
        }
        
        chartManager = new ChartManager();
        
        // Load available symbols for chart dropdown
        chartManager.loadAvailableSymbols();
    } else {
        console.error('[ChartManager] Chart.js not loaded');
    }
});