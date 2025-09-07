/**
 * Pattern Temporal Analysis Service
 * =================================
 * 
 * Handles time-based pattern analysis including optimal trading windows,
 * hourly performance analysis, and temporal trend visualization for the
 * Sprint 23 advanced analytics dashboard.
 * 
 * Features:
 * - Optimal trading window identification
 * - Hourly pattern performance analysis
 * - Daily success rate trends
 * - Time-based pattern recommendations
 * - Interactive temporal visualizations
 * 
 * Author: TickStock Development Team
 * Date: 2025-09-06
 * Sprint: 23
 */

// Debug flag for development
const TEMPORAL_DEBUG = false;

class PatternTemporalService {
    constructor() {
        this.apiBaseUrl = '/api/analytics/temporal';
        this.charts = {};
        this.currentData = null;
        this.updateInterval = null;
        
        // Chart.js configuration for temporal analysis
        this.chartConfigs = {
            tradingWindows: {
                type: 'bar',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Optimal Trading Windows by Pattern'
                        },
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Time Window (Hours)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Success Rate (%)'
                            },
                            min: 0,
                            max: 100
                        }
                    }
                }
            },
            hourlyPerformance: {
                type: 'line',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Hourly Pattern Performance'
                        },
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Hour of Day (EST)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Average Success Rate (%)'
                            },
                            min: 0,
                            max: 100
                        }
                    },
                    elements: {
                        point: {
                            radius: 4,
                            hoverRadius: 6
                        },
                        line: {
                            tension: 0.2
                        }
                    }
                }
            },
            dailyTrends: {
                type: 'line',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Daily Success Rate Trends'
                        },
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'day',
                                displayFormats: {
                                    day: 'MMM DD'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Success Rate (%)'
                            },
                            min: 0,
                            max: 100
                        }
                    },
                    elements: {
                        point: {
                            radius: 3,
                            hoverRadius: 5
                        },
                        line: {
                            tension: 0.1
                        }
                    }
                }
            }
        };
        
        console.log('PatternTemporalService initialized');
    }

    /**
     * Initialize temporal analysis interface
     * @param {string} containerId - Container element ID
     */
    async initialize(containerId) {
        try {
            const container = document.getElementById(containerId);
            if (!container) {
                throw new Error(`Container ${containerId} not found`);
            }

            // Create temporal analysis interface
            container.innerHTML = this.createTemporalInterface();
            
            // Initialize event handlers
            this.initializeEventHandlers();
            
            // Load initial data
            await this.loadTemporalData();
            
            console.log('Temporal analysis interface initialized');
            
        } catch (error) {
            console.error('Error initializing temporal analysis:', error);
            this.showError('Failed to initialize temporal analysis interface');
        }
    }

    /**
     * Create temporal analysis HTML interface
     * @returns {string} HTML content
     */
    createTemporalInterface() {
        return `
            <!-- Temporal Analysis Controls -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <label for="temporal-pattern-select" class="form-label">Pattern</label>
                    <select class="form-select" id="temporal-pattern-select">
                        <option value="all">All Patterns</option>
                        <option value="WeeklyBO">Weekly Breakout</option>
                        <option value="DailyBO">Daily Breakout</option>
                        <option value="TrendFollower">Trend Follower</option>
                        <option value="MomentumBO">Momentum Breakout</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label for="temporal-timeframe-select" class="form-label">Analysis Period</label>
                    <select class="form-select" id="temporal-timeframe-select">
                        <option value="7">Last 7 Days</option>
                        <option value="14">Last 14 Days</option>
                        <option value="30" selected>Last 30 Days</option>
                        <option value="60">Last 60 Days</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label for="temporal-analysis-type" class="form-label">Analysis Type</label>
                    <select class="form-select" id="temporal-analysis-type">
                        <option value="windows" selected>Trading Windows</option>
                        <option value="hourly">Hourly Performance</option>
                        <option value="daily">Daily Trends</option>
                    </select>
                </div>
                <div class="col-md-3 d-flex align-items-end">
                    <button class="btn btn-primary w-100" id="temporal-refresh-btn">
                        <i class="fas fa-chart-line me-2"></i>Analyze
                    </button>
                </div>
            </div>

            <!-- Temporal Analytics Dashboard -->
            <div class="row">
                <!-- Main Temporal Chart -->
                <div class="col-md-8">
                    <div class="card h-100">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-clock me-2"></i>Temporal Analysis
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="chart-container" style="height: 400px;">
                                <canvas id="temporal-main-chart"></canvas>
                            </div>
                            <div id="temporal-loading" class="text-center py-4 d-none">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading temporal data...</span>
                                </div>
                                <p class="mt-2 text-muted">Analyzing temporal patterns...</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Temporal Insights Panel -->
                <div class="col-md-4">
                    <div class="card h-100">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-lightbulb me-2"></i>Key Insights
                            </h5>
                        </div>
                        <div class="card-body" id="temporal-insights">
                            <div class="d-flex justify-content-center align-items-center" style="height: 100%;">
                                <p class="text-muted">Select analysis parameters to view insights</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Temporal Summary Cards -->
            <div class="row mt-4">
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Best Trading Window</h6>
                            <h3 class="text-success" id="best-window">-</h3>
                            <small class="text-muted" id="best-window-rate">-</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Peak Performance Hour</h6>
                            <h3 class="text-info" id="peak-hour">-</h3>
                            <small class="text-muted" id="peak-hour-rate">-</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Trend Direction</h6>
                            <h3 class="text-primary" id="trend-direction">-</h3>
                            <small class="text-muted" id="trend-strength">-</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Time Consistency</h6>
                            <h3 class="text-warning" id="time-consistency">-</h3>
                            <small class="text-muted" id="consistency-note">-</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Initialize event handlers for temporal analysis controls
     */
    initializeEventHandlers() {
        // Analysis refresh button
        const refreshBtn = document.getElementById('temporal-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadTemporalData());
        }

        // Pattern selection change
        const patternSelect = document.getElementById('temporal-pattern-select');
        if (patternSelect) {
            patternSelect.addEventListener('change', () => this.loadTemporalData());
        }

        // Analysis type change
        const analysisTypeSelect = document.getElementById('temporal-analysis-type');
        if (analysisTypeSelect) {
            analysisTypeSelect.addEventListener('change', () => this.updateVisualization());
        }

        // Timeframe change
        const timeframeSelect = document.getElementById('temporal-timeframe-select');
        if (timeframeSelect) {
            timeframeSelect.addEventListener('change', () => this.loadTemporalData());
        }
    }

    /**
     * Load temporal analysis data from API
     */
    async loadTemporalData() {
        try {
            this.showLoading(true);
            
            const pattern = document.getElementById('temporal-pattern-select')?.value || 'all';
            const timeframe = document.getElementById('temporal-timeframe-select')?.value || '30';
            
            // API endpoints for Sprint 23 temporal analytics
            const endpoints = {
                windows: `${this.apiBaseUrl}/trading-windows?pattern=${pattern}&days=${timeframe}`,
                hourly: `${this.apiBaseUrl}/hourly-performance?pattern=${pattern}&days=${timeframe}`,
                daily: `${this.apiBaseUrl}/daily-trends?pattern=${pattern}&days=${timeframe}`
            };

            // Fetch all temporal data in parallel
            const [windowsData, hourlyData, dailyData] = await Promise.all([
                this.fetchWithFallback(endpoints.windows, this.getMockTradingWindows),
                this.fetchWithFallback(endpoints.hourly, this.getMockHourlyPerformance),
                this.fetchWithFallback(endpoints.daily, this.getMockDailyTrends)
            ]);

            // Store comprehensive temporal data
            this.currentData = {
                tradingWindows: windowsData,
                hourlyPerformance: hourlyData,
                dailyTrends: dailyData,
                pattern: pattern,
                timeframe: parseInt(timeframe)
            };

            // Update visualization based on current analysis type
            this.updateVisualization();
            
            // Update insights and summary cards
            this.updateTemporalInsights();
            this.updateSummaryCards();
            
            if (TEMPORAL_DEBUG) console.log('Temporal data loaded successfully', this.currentData);

        } catch (error) {
            console.error('Error loading temporal data:', error);
            this.showError('Failed to load temporal analysis data');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Update visualization based on selected analysis type
     */
    updateVisualization() {
        if (!this.currentData) return;

        const analysisType = document.getElementById('temporal-analysis-type')?.value || 'windows';
        const canvasId = 'temporal-main-chart';

        // Destroy existing chart
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        // Create new chart based on analysis type
        switch (analysisType) {
            case 'windows':
                this.createTradingWindowsChart(canvasId);
                break;
            case 'hourly':
                this.createHourlyPerformanceChart(canvasId);
                break;
            case 'daily':
                this.createDailyTrendsChart(canvasId);
                break;
        }
    }

    /**
     * Create trading windows analysis chart
     * @param {string} canvasId - Canvas element ID
     */
    createTradingWindowsChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const data = this.currentData.tradingWindows;
        
        this.charts[canvasId] = new Chart(ctx, {
            ...this.chartConfigs.tradingWindows,
            data: {
                labels: data.windows,
                datasets: [{
                    label: 'Success Rate (%)',
                    data: data.success_rates,
                    backgroundColor: 'rgba(54, 162, 235, 0.8)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            }
        });
    }

    /**
     * Create hourly performance chart
     * @param {string} canvasId - Canvas element ID
     */
    createHourlyPerformanceChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const data = this.currentData.hourlyPerformance;
        
        this.charts[canvasId] = new Chart(ctx, {
            ...this.chartConfigs.hourlyPerformance,
            data: {
                labels: data.hours,
                datasets: [{
                    label: 'Success Rate (%)',
                    data: data.success_rates,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    fill: true
                }]
            }
        });
    }

    /**
     * Create daily trends chart
     * @param {string} canvasId - Canvas element ID
     */
    createDailyTrendsChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const data = this.currentData.dailyTrends;
        
        this.charts[canvasId] = new Chart(ctx, {
            ...this.chartConfigs.dailyTrends,
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Success Rate (%)',
                    data: data.success_rates,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    fill: true
                }]
            }
        });
    }

    /**
     * Update temporal insights panel
     */
    updateTemporalInsights() {
        const insightsContainer = document.getElementById('temporal-insights');
        if (!insightsContainer || !this.currentData) return;

        const analysisType = document.getElementById('temporal-analysis-type')?.value || 'windows';
        let insights = '';

        switch (analysisType) {
            case 'windows':
                insights = this.generateTradingWindowInsights();
                break;
            case 'hourly':
                insights = this.generateHourlyInsights();
                break;
            case 'daily':
                insights = this.generateDailyTrendInsights();
                break;
        }

        insightsContainer.innerHTML = insights;
    }

    /**
     * Generate trading window insights
     * @returns {string} HTML insights content
     */
    generateTradingWindowInsights() {
        if (!this.currentData || !this.currentData.tradingWindows) {
            return `
                <div class="mb-3">
                    <h6 class="text-muted">Loading Insights...</h6>
                    <p class="mb-2">Trading window analysis is loading...</p>
                </div>
            `;
        }

        const data = this.currentData.tradingWindows;
        
        // Validate data structure
        if (!data.windows || !data.success_rates || !Array.isArray(data.windows) || !Array.isArray(data.success_rates)) {
            return `
                <div class="mb-3">
                    <h6 class="text-warning">Data Unavailable</h6>
                    <p class="mb-2">Trading window data is not available at this time.</p>
                </div>
            `;
        }

        const bestIndex = data.success_rates.indexOf(Math.max(...data.success_rates));
        const bestWindow = data.windows[bestIndex];
        const bestRate = Math.max(...data.success_rates);
        
        return `
            <div class="mb-3">
                <h6 class="text-primary">Optimal Trading Window</h6>
                <p class="mb-2">The <strong>${bestWindow}</strong> window shows the highest success rate at <strong>${bestRate.toFixed(1)}%</strong>.</p>
            </div>
            <div class="mb-3">
                <h6 class="text-primary">Recommendation</h6>
                <p class="mb-2">Focus pattern detection during ${bestWindow} for maximum efficiency.</p>
            </div>
            <div class="mb-3">
                <h6 class="text-primary">Risk Assessment</h6>
                <p class="mb-0 small">Window analysis based on ${this.currentData.timeframe || 30} days of historical data.</p>
            </div>
        `;
    }

    /**
     * Generate hourly performance insights
     * @returns {string} HTML insights content
     */
    generateHourlyInsights() {
        if (!this.currentData || !this.currentData.hourlyPerformance) {
            return `
                <div class="mb-3">
                    <h6 class="text-muted">Loading Insights...</h6>
                    <p class="mb-2">Hourly performance analysis is loading...</p>
                </div>
            `;
        }

        const data = this.currentData.hourlyPerformance;
        
        // Validate data structure
        if (!data.hours || !data.success_rates || !Array.isArray(data.hours) || !Array.isArray(data.success_rates)) {
            return `
                <div class="mb-3">
                    <h6 class="text-warning">Data Unavailable</h6>
                    <p class="mb-2">Hourly performance data is not available at this time.</p>
                </div>
            `;
        }

        const peakIndex = data.success_rates.indexOf(Math.max(...data.success_rates));
        const peakHour = data.hours[peakIndex];
        const peakRate = Math.max(...data.success_rates);
        
        return `
            <div class="mb-3">
                <h6 class="text-primary">Peak Performance</h6>
                <p class="mb-2">Hour <strong>${peakHour}:00 EST</strong> shows peak performance at <strong>${peakRate.toFixed(1)}%</strong>.</p>
            </div>
            <div class="mb-3">
                <h6 class="text-primary">Market Session</h6>
                <p class="mb-2">Performance varies significantly during different market sessions.</p>
            </div>
            <div class="mb-3">
                <h6 class="text-primary">Trading Strategy</h6>
                <p class="mb-0 small">Schedule pattern monitoring during high-performance hours for better results.</p>
            </div>
        `;
    }

    /**
     * Generate daily trend insights
     * @returns {string} HTML insights content
     */
    generateDailyTrendInsights() {
        if (!this.currentData || !this.currentData.dailyTrends) {
            return `
                <div class="mb-3">
                    <h6 class="text-muted">Loading Insights...</h6>
                    <p class="mb-2">Daily trend analysis is loading...</p>
                </div>
            `;
        }

        const data = this.currentData.dailyTrends;
        
        // Validate data structure
        if (!data.success_rates || !Array.isArray(data.success_rates) || data.success_rates.length === 0) {
            return `
                <div class="mb-3">
                    <h6 class="text-warning">Data Unavailable</h6>
                    <p class="mb-2">Daily trend data is not available at this time.</p>
                </div>
            `;
        }

        const avgRate = data.success_rates.reduce((a, b) => a + b, 0) / data.success_rates.length;
        const trend = data.success_rates[data.success_rates.length - 1] > data.success_rates[0] ? 'Improving' : 'Declining';
        
        return `
            <div class="mb-3">
                <h6 class="text-primary">Trend Analysis</h6>
                <p class="mb-2">Pattern performance is <strong>${trend}</strong> over the analysis period.</p>
            </div>
            <div class="mb-3">
                <h6 class="text-primary">Average Performance</h6>
                <p class="mb-2">Average success rate: <strong>${avgRate.toFixed(1)}%</strong></p>
            </div>
            <div class="mb-3">
                <h6 class="text-primary">Volatility</h6>
                <p class="mb-0 small">Daily success rates show ${this.calculateVolatility(data.success_rates)} volatility.</p>
            </div>
        `;
    }

    /**
     * Update summary cards with temporal metrics
     */
    updateSummaryCards() {
        if (!this.currentData) return;

        // Best trading window
        const windowData = this.currentData.tradingWindows;
        if (windowData && windowData.success_rates && windowData.windows && Array.isArray(windowData.success_rates)) {
            const bestWindowIdx = windowData.success_rates.indexOf(Math.max(...windowData.success_rates));
            const bestWindowElement = document.getElementById('best-window');
            const bestWindowRateElement = document.getElementById('best-window-rate');
            if (bestWindowElement) bestWindowElement.textContent = windowData.windows[bestWindowIdx] || 'N/A';
            if (bestWindowRateElement) bestWindowRateElement.textContent = `${windowData.success_rates[bestWindowIdx].toFixed(1)}% success`;
        }

        // Peak performance hour
        const hourlyData = this.currentData.hourlyPerformance;
        if (hourlyData && hourlyData.success_rates && hourlyData.hours && Array.isArray(hourlyData.success_rates)) {
            const peakHourIdx = hourlyData.success_rates.indexOf(Math.max(...hourlyData.success_rates));
            const peakHourElement = document.getElementById('peak-hour');
            const peakHourRateElement = document.getElementById('peak-hour-rate');
            if (peakHourElement) peakHourElement.textContent = `${hourlyData.hours[peakHourIdx]}:00`;
            if (peakHourRateElement) peakHourRateElement.textContent = `${hourlyData.success_rates[peakHourIdx].toFixed(1)}% success`;
        }

        // Trend direction
        const dailyData = this.currentData.dailyTrends;
        if (dailyData && dailyData.success_rates && Array.isArray(dailyData.success_rates) && dailyData.success_rates.length > 0) {
            const trendDirection = dailyData.success_rates[dailyData.success_rates.length - 1] > dailyData.success_rates[0] ? 'Improving' : 'Declining';
            const trendDirectionElement = document.getElementById('trend-direction');
            const trendStrengthElement = document.getElementById('trend-strength');
            if (trendDirectionElement) trendDirectionElement.textContent = trendDirection;
            if (trendStrengthElement) trendStrengthElement.textContent = `${this.calculateTrendStrength(dailyData.success_rates)}% change`;
        }

        // Time consistency
        const consistency = this.calculateTimeConsistency();
        const timeConsistencyElement = document.getElementById('time-consistency');
        const consistencyNoteElement = document.getElementById('consistency-note');
        if (timeConsistencyElement) timeConsistencyElement.textContent = `${consistency.toFixed(0)}%`;
        if (consistencyNoteElement) consistencyNoteElement.textContent = consistency > 80 ? 'High' : consistency > 60 ? 'Moderate' : 'Low';
    }

    /**
     * Calculate volatility of success rates
     * @param {Array} rates - Success rate array
     * @returns {string} Volatility description
     */
    calculateVolatility(rates) {
        if (!rates || !Array.isArray(rates) || rates.length === 0) {
            return 'unknown';
        }
        
        const mean = rates.reduce((a, b) => a + b, 0) / rates.length;
        const variance = rates.reduce((acc, rate) => acc + Math.pow(rate - mean, 2), 0) / rates.length;
        const stdDev = Math.sqrt(variance);
        
        if (stdDev < 5) return 'low';
        if (stdDev < 10) return 'moderate';
        return 'high';
    }

    /**
     * Calculate trend strength percentage
     * @param {Array} rates - Success rate array
     * @returns {number} Trend strength percentage
     */
    calculateTrendStrength(rates) {
        if (!rates || !Array.isArray(rates) || rates.length < 2) {
            return 0;
        }
        const firstRate = rates[0];
        const lastRate = rates[rates.length - 1];
        if (firstRate === 0) return 0;
        return ((lastRate - firstRate) / firstRate * 100);
    }

    /**
     * Calculate time consistency score
     * @returns {number} Consistency percentage
     */
    calculateTimeConsistency() {
        if (!this.currentData || !this.currentData.hourlyPerformance || !this.currentData.hourlyPerformance.success_rates || !Array.isArray(this.currentData.hourlyPerformance.success_rates)) {
            return 0;
        }
        
        // Simplified consistency calculation based on variance across time periods
        const hourlyRates = this.currentData.hourlyPerformance.success_rates;
        if (hourlyRates.length === 0) return 0;
        
        const mean = hourlyRates.reduce((a, b) => a + b, 0) / hourlyRates.length;
        const variance = hourlyRates.reduce((acc, rate) => acc + Math.pow(rate - mean, 2), 0) / hourlyRates.length;
        
        // Convert variance to consistency percentage (inverse relationship)
        return Math.max(0, 100 - (Math.sqrt(variance) * 2));
    }

    /**
     * Fetch data with mock fallback
     * @param {string} url - API endpoint URL
     * @param {Function} mockFunction - Mock data function
     * @returns {Promise} Data promise
     */
    async fetchWithFallback(url, mockFunction) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.warn(`API call failed for ${url}, using mock data:`, error);
            return mockFunction.call(this);
        }
    }

    /**
     * Show/hide loading state
     * @param {boolean} show - Show loading state
     */
    showLoading(show) {
        const loadingEl = document.getElementById('temporal-loading');
        const chartContainer = document.querySelector('#temporal-main-chart').parentElement;
        
        if (loadingEl) {
            loadingEl.classList.toggle('d-none', !show);
        }
        if (chartContainer) {
            chartContainer.style.opacity = show ? '0.5' : '1';
        }
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        console.error('Temporal Analysis Error:', message);
        // Could implement toast notification or error display here
    }

    /**
     * Clean up resources
     */
    destroy() {
        // Stop any update intervals
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        // Destroy all Chart.js instances
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
        
        console.log('PatternTemporalService destroyed');
    }

    // Mock data methods for development and testing

    /**
     * Generate mock trading windows data
     * @returns {Object} Mock trading windows data
     */
    getMockTradingWindows() {
        return {
            windows: ['4H', '8H', '12H', '24H', '48H', '72H'],
            success_rates: [58.2, 64.7, 69.8, 67.3, 62.1, 59.4]
        };
    }

    /**
     * Generate mock hourly performance data
     * @returns {Object} Mock hourly performance data
     */
    getMockHourlyPerformance() {
        const hours = [];
        const rates = [];
        
        // Generate 24 hours of mock data
        for (let i = 0; i < 24; i++) {
            hours.push(i);
            // Simulate market session patterns
            let rate = 45 + Math.random() * 30;
            if (i >= 9 && i <= 16) rate += 10; // Market hours boost
            if (i >= 14 && i <= 15) rate += 5;  // Peak trading hours
            rates.push(Math.min(85, rate));
        }
        
        return { hours, success_rates: rates };
    }

    /**
     * Generate mock daily trends data
     * @returns {Object} Mock daily trends data
     */
    getMockDailyTrends() {
        const dates = [];
        const rates = [];
        const baseDate = new Date();
        
        // Generate 30 days of mock data
        for (let i = 29; i >= 0; i--) {
            const date = new Date(baseDate);
            date.setDate(date.getDate() - i);
            dates.push(date.toISOString().split('T')[0]);
            
            // Simulate trending pattern with some noise
            const trend = (29 - i) * 0.5; // Slight upward trend
            const noise = (Math.random() - 0.5) * 10; // Random noise
            const rate = Math.max(30, Math.min(80, 55 + trend + noise));
            rates.push(rate);
        }
        
        return { dates, success_rates: rates };
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PatternTemporalService;
}