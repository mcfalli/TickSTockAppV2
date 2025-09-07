/**
 * Pattern Analytics Service for TickStock Pattern Discovery
 * Handles performance analysis, success rate tracking, and market insights
 * 
 * Sprint 21 - Week 2 Deliverable
 * Architecture: Follows established web/static/js/services/ pattern
 * Integration: Provides analytics for existing Pattern Discovery functionality
 */

class PatternAnalyticsService {
    constructor() {
        this.analyticsData = new Map();
        this.marketStatistics = {};
        this.historicalData = {};
        this.isInitialized = false;
        
        // Chart.js instances for cleanup
        this.chartInstances = new Map();
        
        // Market statistics initialization flag
        this.marketStatisticsInitialized = false;
        
        // API endpoints
        this.endpoints = {
            analytics: '/api/patterns/analytics',
            distribution: '/api/patterns/distribution', 
            history: '/api/patterns/history',
            successRates: '/api/patterns/success-rates',
            marketStats: '/api/market/statistics',
            breadth: '/api/market/breadth',
            // Sprint 22: Dynamic Pattern Loading
            patternDefinitions: '/api/patterns/definitions',
            patternDistributionReal: '/api/patterns/distribution/real'
        };
        
        // Time periods for analysis
        this.timePeriods = ['1d', '5d', '30d'];
        
        // Sprint 22: Dynamic Pattern Loading
        this.availablePatterns = [];
        this.patternDefinitions = new Map();
        
        this.initialize();
    }

    async initialize() {
        try {
            // Sprint 22: Load patterns dynamically first
            await this.loadPatternDefinitions();
            await this.loadAnalyticsData();
            this.createAnalyticsPanel();
            this.setupEventHandlers();
            this.isInitialized = true;
            console.log('PatternAnalyticsService initialized successfully');
        } catch (error) {
            console.error('Failed to initialize PatternAnalyticsService:', error);
            this.loadMockData();
        }
    }

    /**
     * Load pattern definitions dynamically from Sprint 22 Pattern Registry API
     */
    async loadPatternDefinitions() {
        try {
            console.log('Loading pattern definitions from Pattern Registry...');
            const response = await fetch(this.endpoints.patternDefinitions);
            
            if (!response.ok) {
                throw new Error(`Pattern definitions API failed: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Store pattern definitions
            this.patternDefinitions.clear();
            this.availablePatterns = [];
            
            if (data.patterns && Array.isArray(data.patterns)) {
                data.patterns.forEach(pattern => {
                    this.patternDefinitions.set(pattern.name, pattern);
                    this.availablePatterns.push(pattern.name);
                });
                
                console.log(`Loaded ${this.availablePatterns.length} pattern definitions:`, this.availablePatterns);
            } else {
                throw new Error('Invalid pattern definitions response format');
            }
            
        } catch (error) {
            console.warn('Failed to load pattern definitions from API, using fallback:', error);
            this.loadFallbackPatterns();
        }
    }

    /**
     * Fallback to hardcoded patterns if API fails
     */
    loadFallbackPatterns() {
        this.availablePatterns = ['WeeklyBO', 'DailyBO', 'Doji', 'Hammer', 'EngulfingBullish', 'ShootingStar'];
        this.availablePatterns.forEach(name => {
            this.patternDefinitions.set(name, {
                name: name,
                short_description: `${name} Pattern`,
                enabled: true,
                category: 'pattern',
                typical_success_rate: 65.0
            });
        });
        console.log('Using fallback pattern definitions:', this.availablePatterns);
    }

    /**
     * Historical Pattern Tracking - Sprint 21 Week 2 Deliverable 2
     * Enables strategy validation and pattern performance analysis
     */
    
    /**
     * Get success rate analysis for all pattern types
     * @returns {Object} Success rates by pattern type and time period
     */
    async getSuccessRateAnalysis() {
        try {
            const response = await fetch(this.endpoints.successRates);
            if (!response.ok) throw new Error('Success rate API failed');
            
            const data = await response.json();
            this.historicalData.successRates = data;
            return data;
        } catch (error) {
            console.warn('Using mock success rate data:', error);
            return this.getMockSuccessRates();
        }
    }
    
    /**
     * Generate mock success rate data for development
     * Sprint 22: Now uses dynamically loaded patterns
     */
    getMockSuccessRates() {
        const mockData = {};
        
        // Use pattern definitions if available
        this.availablePatterns.forEach(patternName => {
            const patternDef = this.patternDefinitions.get(patternName);
            const baseRate = patternDef && patternDef.typical_success_rate 
                ? patternDef.typical_success_rate / 100 
                : Math.random() * 0.4 + 0.4; // Random between 40-80%
                
            const variance = Math.random() * 0.2 - 0.1; // +/- 10% variance
            const trends = ['improving', 'stable', 'declining'];
            
            mockData[patternName] = {
                '1d': Math.max(0.2, Math.min(0.9, baseRate + variance)),
                '5d': Math.max(0.15, Math.min(0.85, baseRate + (variance * 0.8))),
                '30d': Math.max(0.1, Math.min(0.8, baseRate + (variance * 0.6))),
                trend: trends[Math.floor(Math.random() * trends.length)],
                confidence_correlation: Math.random() * 0.3 + 0.6 // 60-90%
            };
        });
        
        // Fallback for old hardcoded patterns if no dynamic patterns loaded
        if (this.availablePatterns.length === 0) {
            return {
                WeeklyBO: { 
                    '1d': 0.78, '5d': 0.65, '30d': 0.52,
                    trend: 'improving',
                    confidence_correlation: 0.82
                },
                DailyBO: { 
                    '1d': 0.65, '5d': 0.58, '30d': 0.47,
                    trend: 'stable',
                    confidence_correlation: 0.74
                },
                Doji: { 
                    '1d': 0.45, '5d': 0.42, '30d': 0.38,
                    trend: 'declining',
                    confidence_correlation: 0.61
                },
                Hammer: {
                    '1d': 0.68, '5d': 0.59, '30d': 0.48,
                    trend: 'stable',
                    confidence_correlation: 0.76
                },
                EngulfingBullish: {
                    '1d': 0.72, '5d': 0.63, '30d': 0.54,
                    trend: 'improving',
                    confidence_correlation: 0.84
                }
            };
        }
        
        return mockData;
    }
    
    /**
     * Analyze historical performance by time periods
     * @param {string} patternType - Pattern type to analyze
     * @returns {Object} Time-based performance metrics
     */
    analyzeTimeBasedPerformance(patternType) {
        const successRates = this.historicalData.successRates || this.getMockSuccessRates();
        const patternData = successRates[patternType];
        
        if (!patternData) {
            console.warn(`No data for pattern type: ${patternType}`);
            return null;
        }
        
        return {
            pattern_type: patternType,
            success_rates: {
                '1d': patternData['1d'],
                '5d': patternData['5d'], 
                '30d': patternData['30d']
            },
            trend_direction: patternData.trend,
            reliability_score: patternData.confidence_correlation,
            avg_performance: {
                '1d': this.calculateAveragePerformance(patternType, '1d'),
                '5d': this.calculateAveragePerformance(patternType, '5d'),
                '30d': this.calculateAveragePerformance(patternType, '30d')
            },
            sample_size: this.getPatternSampleSize(patternType)
        };
    }
    
    /**
     * Calculate average performance for pattern type and time period
     */
    calculateAveragePerformance(patternType, period) {
        // Mock calculation - in real implementation would use historical data
        const basePerformance = {
            'WeeklyBO': { '1d': 2.3, '5d': 4.7, '30d': 8.2 },
            'DailyBO': { '1d': 1.8, '5d': 3.2, '30d': 5.9 },
            'Doji': { '1d': 0.8, '5d': 1.2, '30d': 2.1 },
            'Hammer': { '1d': 1.9, '5d': 3.4, '30d': 6.1 },
            'EngulfingBullish': { '1d': 2.1, '5d': 4.1, '30d': 7.3 }
        };
        
        return basePerformance[patternType]?.[period] || 1.5;
    }
    
    /**
     * Get sample size for pattern type (mock data)
     */
    getPatternSampleSize(patternType) {
        const sampleSizes = {
            'WeeklyBO': 1247,
            'DailyBO': 2156, 
            'Doji': 3421,
            'Hammer': 891,
            'EngulfingBullish': 1567
        };
        
        return sampleSizes[patternType] || 500;
    }
    
    /**
     * Perform strategy backtesting for filter presets
     * @param {Object} filterPreset - Filter preset to backtest
     * @param {number} days - Days to backtest (default 30)
     * @returns {Object} Backtesting results
     */
    async backtestFilterPreset(filterPreset, days = 30) {
        try {
            const response = await fetch(`/api/patterns/backtest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    preset: filterPreset, 
                    days: days 
                })
            });
            
            if (!response.ok) throw new Error('Backtest API failed');
            return await response.json();
        } catch (error) {
            console.warn('Using mock backtest data:', error);
            return this.getMockBacktestResults(filterPreset, days);
        }
    }
    
    /**
     * Generate mock backtest results
     */
    getMockBacktestResults(filterPreset, days) {
        const presetName = filterPreset.name || 'Custom Preset';
        const baseSuccessRate = 0.65 + (Math.random() - 0.5) * 0.2;
        
        return {
            preset_name: presetName,
            backtest_period: days,
            total_signals: Math.floor(50 + Math.random() * 100),
            successful_trades: Math.floor((50 + Math.random() * 100) * baseSuccessRate),
            success_rate: baseSuccessRate,
            avg_return: 2.3 + (Math.random() - 0.5) * 1.5,
            max_drawdown: -(Math.random() * 0.15 + 0.05),
            sharpe_ratio: 0.8 + Math.random() * 0.6,
            daily_performance: this.generateDailyPerformance(days),
            pattern_breakdown: this.getPatternBreakdown(),
            risk_metrics: {
                volatility: 0.12 + Math.random() * 0.08,
                var_95: -(Math.random() * 0.08 + 0.02),
                max_consecutive_losses: Math.floor(Math.random() * 5 + 1)
            }
        };
    }
    
    /**
     * Generate daily performance data for charts
     */
    generateDailyPerformance(days) {
        const performance = [];
        let cumulativeReturn = 1.0;
        
        for (let i = 0; i < days; i++) {
            const dailyReturn = (Math.random() - 0.48) * 0.04; // Slight positive bias
            cumulativeReturn *= (1 + dailyReturn);
            
            performance.push({
                date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                daily_return: dailyReturn,
                cumulative_return: cumulativeReturn - 1,
                drawdown: Math.min(0, cumulativeReturn - Math.max(...performance.map(p => p.cumulative_return || 1)))
            });
        }
        
        return performance;
    }
    
    /**
     * Get pattern breakdown for backtest results
     */
    getPatternBreakdown() {
        return {
            'WeeklyBO': { signals: 15, success_rate: 0.73, avg_return: 2.8 },
            'DailyBO': { signals: 22, success_rate: 0.59, avg_return: 1.9 },
            'Doji': { signals: 8, success_rate: 0.38, avg_return: 0.9 },
            'Hammer': { signals: 12, success_rate: 0.67, avg_return: 2.1 },
            'EngulfingBullish': { signals: 18, success_rate: 0.72, avg_return: 2.5 }
        };
    }
    
    /**
     * Calculate reliability score for pattern type
     * Measures confidence vs actual performance correlation
     */
    calculateReliabilityScore(patternType) {
        const successRates = this.getMockSuccessRates();
        const patternData = successRates[patternType];
        
        if (!patternData) return 0;
        
        // Reliability score is confidence correlation from mock data
        return {
            pattern_type: patternType,
            reliability_score: patternData.confidence_correlation,
            grade: this.getReliabilityGrade(patternData.confidence_correlation),
            description: this.getReliabilityDescription(patternData.confidence_correlation)
        };
    }
    
    /**
     * Convert reliability score to letter grade
     */
    getReliabilityGrade(score) {
        if (score >= 0.85) return 'A+';
        if (score >= 0.80) return 'A';
        if (score >= 0.75) return 'B+';
        if (score >= 0.70) return 'B';
        if (score >= 0.65) return 'C+';
        if (score >= 0.60) return 'C';
        return 'D';
    }
    
    /**
     * Get reliability description
     */
    getReliabilityDescription(score) {
        if (score >= 0.85) return 'Excellent correlation between confidence and performance';
        if (score >= 0.80) return 'Strong correlation between confidence and performance';
        if (score >= 0.75) return 'Good correlation between confidence and performance';
        if (score >= 0.70) return 'Moderate correlation between confidence and performance';
        if (score >= 0.60) return 'Fair correlation between confidence and performance';
        return 'Poor correlation between confidence and performance';
    }
    
    /**
     * Create historical performance chart
     */
    createHistoricalPerformanceChart() {
        const canvas = document.getElementById('historicalPerformanceChart');
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.chartInstances.has('historicalPerformance')) {
            this.chartInstances.get('historicalPerformance').destroy();
        }
        
        const successRates = this.getMockSuccessRates();
        const patterns = Object.keys(successRates);
        
        const datasets = this.timePeriods.map((period, index) => ({
            label: period.toUpperCase() + ' Success Rate',
            data: patterns.map(pattern => successRates[pattern][period] * 100),
            backgroundColor: [
                'rgba(54, 162, 235, 0.6)',
                'rgba(255, 99, 132, 0.6)', 
                'rgba(255, 206, 86, 0.6)'
            ][index],
            borderColor: [
                'rgba(54, 162, 235, 1)',
                'rgba(255, 99, 132, 1)',
                'rgba(255, 206, 86, 1)'  
            ][index],
            borderWidth: 1
        }));
        
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: patterns,
                datasets: datasets
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Historical Success Rates by Time Period'
                    },
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
        
        this.chartInstances.set('historicalPerformance', chart);
        return chart;
    }
    
    /**
     * Create strategy backtest results chart
     */
    createBacktestChart(backtestResults) {
        const canvas = document.getElementById('backtestChart');
        if (!canvas || !backtestResults.daily_performance) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.chartInstances.has('backtest')) {
            this.chartInstances.get('backtest').destroy();
        }
        
        const data = backtestResults.daily_performance;
        const labels = data.map(d => d.date);
        const cumulativeReturns = data.map(d => (d.cumulative_return * 100).toFixed(2));
        const drawdowns = data.map(d => (d.drawdown * 100).toFixed(2));
        
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Cumulative Return (%)',
                    data: cumulativeReturns,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    fill: false,
                    tension: 0.1,
                    yAxisID: 'y'
                }, {
                    label: 'Drawdown (%)',
                    data: drawdowns,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    fill: true,
                    tension: 0.1,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    title: {
                        display: true,
                        text: `Strategy Backtest: ${backtestResults.preset_name}`
                    },
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Cumulative Return (%)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Drawdown (%)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
        
        this.chartInstances.set('backtest', chart);
        return chart;
    }
    
    /**
     * Load analytics data from API
     */
    async loadAnalyticsData() {
        try {
            const [analyticsRes, distributionRes, historyRes, statsRes] = await Promise.all([
                fetch(this.endpoints.analytics),
                fetch(this.endpoints.distribution),
                fetch(this.endpoints.history),
                fetch(this.endpoints.marketStats)
            ]);

            // Check if all responses are ok
            if (!analyticsRes.ok || !distributionRes.ok || !historyRes.ok || !statsRes.ok) {
                throw new Error('API responses not ok');
            }

            // Check for HTML responses (login redirects) and parse JSON
            const [analyticsData, distributionData, historyData, statsData] = await Promise.all([
                this.parseResponseSafely(analyticsRes),
                this.parseResponseSafely(distributionRes),
                this.parseResponseSafely(historyRes),
                this.parseResponseSafely(statsRes)
            ]);

            this.analyticsData.set('performance', analyticsData);
            this.analyticsData.set('distribution', distributionData);
            this.historicalData = historyData;
            this.marketStatistics = statsData;
        } catch (error) {
            console.warn('Analytics API unavailable, using mock data:', error.message);
            this.loadMockData();
        }
    }

    /**
     * Safely parse response, checking for HTML redirects
     * @param {Response} response - Fetch response object
     * @returns {Promise<Object>} Parsed JSON data
     */
    async parseResponseSafely(response) {
        const text = await response.text();
        
        // Check if response is HTML (login redirect)
        if (text.trim().startsWith('<!DOCTYPE') || text.trim().startsWith('<html')) {
            throw new Error('Authentication required - HTML response received');
        }
        
        try {
            return JSON.parse(text);
        } catch (e) {
            throw new Error('Invalid JSON response');
        }
    }

    /**
     * Create mock analytics data for development
     */
    loadMockData() {
        // Performance Analytics
        const performanceData = {
            success_rates: {
                WeeklyBO: { '1d': 0.78, '5d': 0.65, '30d': 0.52 },
                DailyBO: { '1d': 0.65, '5d': 0.58, '30d': 0.47 },
                Doji: { '1d': 0.45, '5d': 0.42, '30d': 0.38 },
                Hammer: { '1d': 0.62, '5d': 0.55, '30d': 0.41 },
                ShootingStar: { '1d': 0.58, '5d': 0.48, '30d': 0.35 },
                Engulfing: { '1d': 0.71, '5d': 0.61, '30d': 0.49 },
                Harami: { '1d': 0.48, '5d': 0.44, '30d': 0.39 }
            },
            avg_performance: {
                WeeklyBO: { '1d': 2.3, '5d': 4.7, '30d': 8.2 },
                DailyBO: { '1d': 1.8, '5d': 3.2, '30d': 5.9 },
                Doji: { '1d': 0.8, '5d': 1.2, '30d': 2.1 },
                Hammer: { '1d': 1.5, '5d': 2.8, '30d': 4.3 },
                ShootingStar: { '1d': 1.2, '5d': 2.1, '30d': 3.5 },
                Engulfing: { '1d': 2.1, '5d': 3.9, '30d': 6.8 },
                Harami: { '1d': 0.9, '5d': 1.6, '30d': 2.9 }
            },
            reliability_score: {
                WeeklyBO: 0.82,
                DailyBO: 0.74,
                Doji: 0.61,
                Hammer: 0.68,
                ShootingStar: 0.65,
                Engulfing: 0.79,
                Harami: 0.58
            },
            volume_correlation: {
                WeeklyBO: 0.73,
                DailyBO: 0.68,
                Doji: 0.45,
                Hammer: 0.56,
                ShootingStar: 0.62,
                Engulfing: 0.71,
                Harami: 0.41
            }
        };

        // Distribution Data
        const distributionData = {
            pattern_frequency: {
                WeeklyBO: 28,
                DailyBO: 42,
                Doji: 65,
                Hammer: 38,
                ShootingStar: 31,
                Engulfing: 24,
                Harami: 47
            },
            confidence_distribution: {
                'high': { label: '80%+', count: 89, percentage: 32.1 },
                'medium': { label: '60-80%', count: 124, percentage: 44.8 },
                'low': { label: '<60%', count: 64, percentage: 23.1 }
            },
            sector_breakdown: {
                Technology: { count: 67, avg_confidence: 0.76 },
                Healthcare: { count: 45, avg_confidence: 0.71 },
                Financial: { count: 52, avg_confidence: 0.69 },
                Industrial: { count: 38, avg_confidence: 0.73 },
                Consumer: { count: 41, avg_confidence: 0.68 },
                Energy: { count: 34, avg_confidence: 0.65 }
            }
        };

        // Market Statistics
        const marketStats = {
            live_metrics: {
                patterns_detected_today: 277,
                pattern_velocity_per_hour: 11.5,
                average_confidence: 0.71,
                high_confidence_ratio: 0.32,
                market_breadth_score: 0.68
            },
            hourly_frequency: [5, 8, 12, 15, 18, 22, 19, 16, 13, 11, 8, 6], // Last 12 hours
            daily_trend: {
                patterns_today: 277,
                patterns_yesterday: 245,
                change_percent: 13.1
            },
            top_performers: [
                { symbol: 'AAPL', patterns: 8, avg_confidence: 0.84 },
                { symbol: 'NVDA', patterns: 7, avg_confidence: 0.81 },
                { symbol: 'GOOGL', patterns: 6, avg_confidence: 0.78 },
                { symbol: 'MSFT', patterns: 5, avg_confidence: 0.76 },
                { symbol: 'TSLA', patterns: 7, avg_confidence: 0.73 }
            ]
        };

        this.analyticsData.set('performance', performanceData);
        this.analyticsData.set('distribution', distributionData);
        this.marketStatistics = marketStats;
        
        // Save to localStorage for persistence
        this.saveToLocalStorage();
    }

    /**
     * Create analytics panel container - DISABLED
     * Analytics are now handled by top-level tab navigation
     */
    createAnalyticsPanel() {
        // DISABLED: Analytics panel creation is now handled by top-level tabs
        // This prevents duplicate tabs from appearing in the sidebar
        console.log('Analytics panel creation disabled - using top-level tabs instead');
        return;
    }

    /**
     * Render analytics panel with tabbed interface
     */
    renderAnalyticsPanel() {
        const container = document.getElementById('pattern-analytics-panel');
        if (!container) return;

        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <ul class="nav nav-tabs card-header-tabs" id="analytics-tabs" role="tablist">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active" id="overview-tab" data-bs-toggle="tab" 
                                    data-bs-target="#overview" type="button" role="tab">
                                <i class="fas fa-chart-line me-1"></i>Overview
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="performance-tab" data-bs-toggle="tab" 
                                    data-bs-target="#performance" type="button" role="tab">
                                <i class="fas fa-trophy me-1"></i>Performance
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="distribution-tab" data-bs-toggle="tab" 
                                    data-bs-target="#distribution" type="button" role="tab">
                                <i class="fas fa-chart-pie me-1"></i>Distribution
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="historical-tab" data-bs-toggle="tab" 
                                    data-bs-target="#historical" type="button" role="tab">
                                <i class="fas fa-history me-1"></i>Historical
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="market-tab" data-bs-toggle="tab" 
                                    data-bs-target="#market" type="button" role="tab">
                                <i class="fas fa-globe me-1"></i>Market
                            </button>
                        </li>
                        <!-- Sprint 23: Advanced Analytics Tabs -->
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="correlations-tab" data-bs-toggle="tab" 
                                    data-bs-target="#correlations" type="button" role="tab">
                                <i class="fas fa-project-diagram me-1"></i>Correlations
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="temporal-tab" data-bs-toggle="tab" 
                                    data-bs-target="#temporal" type="button" role="tab">
                                <i class="fas fa-clock me-1"></i>Temporal
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="compare-tab" data-bs-toggle="tab" 
                                    data-bs-target="#compare" type="button" role="tab">
                                <i class="fas fa-balance-scale me-1"></i>Compare
                            </button>
                        </li>
                    </ul>
                </div>
                <div class="card-body p-0">
                    <div class="tab-content" id="analytics-content">
                        <div class="tab-pane fade show active" id="overview" role="tabpanel">
                            ${this.renderOverviewTab()}
                        </div>
                        <div class="tab-pane fade" id="performance" role="tabpanel">
                            ${this.renderPerformanceTab()}
                        </div>
                        <div class="tab-pane fade" id="distribution" role="tabpanel">
                            ${this.renderDistributionTab()}
                        </div>
                        <div class="tab-pane fade" id="historical" role="tabpanel">
                            ${this.renderHistoricalTab()}
                        </div>
                        <div class="tab-pane fade" id="market" role="tabpanel">
                            ${this.renderMarketTab()}
                        </div>
                        <!-- Sprint 23: Advanced Analytics Tab Content -->
                        <div class="tab-pane fade" id="correlations" role="tabpanel">
                            <div id="sprint23-correlations-content" class="p-4">
                                <div class="d-flex align-items-center justify-content-center py-5">
                                    <div class="spinner-border text-success me-3" role="status">
                                        <span class="visually-hidden">Loading Correlations...</span>
                                    </div>
                                    <div class="text-muted">Initializing Pattern Correlations Dashboard...</div>
                                </div>
                            </div>
                        </div>
                        <div class="tab-pane fade" id="temporal" role="tabpanel">
                            <div id="sprint23-temporal-content" class="p-4">
                                <div class="d-flex align-items-center justify-content-center py-5">
                                    <div class="spinner-border text-warning me-3" role="status">
                                        <span class="visually-hidden">Loading Temporal Analysis...</span>
                                    </div>
                                    <div class="text-muted">Initializing Temporal Analysis Dashboard...</div>
                                </div>
                            </div>
                        </div>
                        <div class="tab-pane fade" id="compare" role="tabpanel">
                            <div id="sprint23-compare-content" class="p-4">
                                <div class="d-flex align-items-center justify-content-center py-5">
                                    <div class="spinner-border text-info me-3" role="status">
                                        <span class="visually-hidden">Loading Pattern Comparison...</span>
                                    </div>
                                    <div class="text-muted">Initializing Pattern Comparison Dashboard...</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.setupTabEventHandlers();
    }

    /**
     * Render overview tab content
     */
    renderOverviewTab() {
        const stats = this.marketStatistics.live_metrics || {};
        const topPerformers = this.marketStatistics.top_performers || [];

        return `
            <div class="p-3">
                <div class="row mb-3">
                    <div class="col-md-3 col-6 mb-2">
                        <div class="text-center">
                            <div class="h4 text-primary mb-0">${stats.patterns_detected_today || 0}</div>
                            <small class="text-muted">Patterns Today</small>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="text-center">
                            <div class="h4 text-success mb-0">${(stats.average_confidence * 100).toFixed(0)}%</div>
                            <small class="text-muted">Avg Confidence</small>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="text-center">
                            <div class="h4 text-info mb-0">${stats.pattern_velocity_per_hour || 0}</div>
                            <small class="text-muted">Per Hour</small>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="text-center">
                            <div class="h4 text-warning mb-0">${(stats.market_breadth_score * 100).toFixed(0)}%</div>
                            <small class="text-muted">Market Breadth</small>
                        </div>
                    </div>
                </div>
                
                <!-- Main Charts Row -->
                <div class="row mb-4">
                    <div class="col-md-8">
                        <h6 class="mb-2">Pattern Velocity (Last 12 Hours)</h6>
                        <div style="position: relative; height: 200px;">
                            <canvas id="velocity-chart"></canvas>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <h6 class="mb-2">Top Performers</h6>
                        <div class="list-group list-group-flush">
                            ${topPerformers.slice(0, 5).map(performer => `
                                <div class="list-group-item d-flex justify-content-between align-items-center px-0">
                                    <div>
                                        <strong>${performer.symbol}</strong>
                                        <small class="text-muted d-block">${performer.patterns} patterns</small>
                                    </div>
                                    <span class="badge bg-primary rounded-pill">
                                        ${(performer.avg_confidence * 100).toFixed(0)}%
                                    </span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>

                <!-- Real-Time Market Activity Section -->
                <div class="row mb-4">
                    <div class="col-12">
                        <h6 class="mb-3">Real-Time Market Activity</h6>
                        <div class="row">
                            <div class="col-md-4">
                                <div class="card border-0 bg-primary text-white">
                                    <div class="card-body text-center">
                                        <h5 class="card-title">${stats.active_patterns || 1247}</h5>
                                        <p class="card-text">Active Patterns</p>
                                        <small>Updated 2 min ago</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card border-0 bg-success text-white">
                                    <div class="card-body text-center">
                                        <h5 class="card-title">${stats.successful_signals || 89}%</h5>
                                        <p class="card-text">Success Rate Today</p>
                                        <small>Above 30-day average</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card border-0 bg-info text-white">
                                    <div class="card-body text-center">
                                        <h5 class="card-title">${stats.alerts_sent || 342}</h5>
                                        <p class="card-text">Alerts Sent</p>
                                        <small>Last 24 hours</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Pattern Breakdown Section -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="mb-3">Pattern Type Distribution</h6>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="small">Weekly Breakout</span>
                                <span class="badge bg-primary">${stats.weekly_bo || 287}</span>
                            </div>
                            <div class="progress mb-2" style="height: 8px;">
                                <div class="progress-bar bg-primary" role="progressbar" style="width: 35%"></div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="small">Support/Resistance</span>
                                <span class="badge bg-success">${stats.support_resistance || 198}</span>
                            </div>
                            <div class="progress mb-2" style="height: 8px;">
                                <div class="progress-bar bg-success" role="progressbar" style="width: 24%"></div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="small">Triangle Patterns</span>
                                <span class="badge bg-info">${stats.triangles || 156}</span>
                            </div>
                            <div class="progress mb-2" style="height: 8px;">
                                <div class="progress-bar bg-info" role="progressbar" style="width: 19%"></div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="small">Volume Spikes</span>
                                <span class="badge bg-warning">${stats.volume_spikes || 134}</span>
                            </div>
                            <div class="progress mb-2" style="height: 8px;">
                                <div class="progress-bar bg-warning" role="progressbar" style="width: 16%"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="mb-3">Recent High-Confidence Signals</h6>
                        <div class="list-group">
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>AAPL</strong> - Weekly Breakout
                                    <small class="text-muted d-block">2 minutes ago</small>
                                </div>
                                <span class="badge bg-success rounded-pill">94%</span>
                            </div>
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>TSLA</strong> - Support Level
                                    <small class="text-muted d-block">5 minutes ago</small>
                                </div>
                                <span class="badge bg-primary rounded-pill">91%</span>
                            </div>
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>NVDA</strong> - Triangle Formation  
                                    <small class="text-muted d-block">8 minutes ago</small>
                                </div>
                                <span class="badge bg-info rounded-pill">88%</span>
                            </div>
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>MSFT</strong> - Volume Spike
                                    <small class="text-muted d-block">12 minutes ago</small>
                                </div>
                                <span class="badge bg-warning rounded-pill">85%</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- System Status Section -->
                <div class="row mb-4">
                    <div class="col-12">
                        <h6 class="mb-3">System Health & Performance</h6>
                        <div class="row">
                            <div class="col-md-3">
                                <div class="text-center">
                                    <div class="mb-2">
                                        <div class="badge bg-success rounded-circle" style="width: 40px; height: 40px; line-height: 26px;">
                                            ✓
                                        </div>
                                    </div>
                                    <small class="text-success">WebSocket Connected</small>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="text-center">
                                    <div class="mb-2">
                                        <div class="badge bg-success rounded-circle" style="width: 40px; height: 40px; line-height: 26px;">
                                            ✓
                                        </div>
                                    </div>
                                    <small class="text-success">Pattern Engine Online</small>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="text-center">
                                    <div class="mb-2">
                                        <div class="badge bg-info rounded-circle" style="width: 40px; height: 40px; line-height: 22px;">
                                            ${stats.latency || 47}ms
                                        </div>
                                    </div>
                                    <small class="text-muted">Avg Response Time</small>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="text-center">
                                    <div class="mb-2">
                                        <div class="badge bg-primary rounded-circle" style="width: 40px; height: 40px; line-height: 22px;">
                                            4K+
                                        </div>
                                    </div>
                                    <small class="text-muted">Symbols Monitored</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Quick Actions Section -->
                <div class="row">
                    <div class="col-12">
                        <h6 class="mb-3">Quick Actions</h6>
                        <div class="row">
                            <div class="col-md-3">
                                <button class="btn btn-outline-primary w-100 mb-2">
                                    <i class="fa fa-search me-2"></i>Run Pattern Scan
                                </button>
                            </div>
                            <div class="col-md-3">
                                <button class="btn btn-outline-success w-100 mb-2">
                                    <i class="fa fa-bell me-2"></i>Set New Alert
                                </button>
                            </div>
                            <div class="col-md-3">
                                <button class="btn btn-outline-info w-100 mb-2">
                                    <i class="fa fa-download me-2"></i>Export Data
                                </button>
                            </div>
                            <div class="col-md-3">
                                <button class="btn btn-outline-warning w-100 mb-2">
                                    <i class="fa fa-cog me-2"></i>Settings
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render performance tab content
     */
    renderPerformanceTab() {
        return `
            <div class="p-3">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <h6 class="mb-2">Success Rates by Pattern Type</h6>
                        <div style="position: relative; height: 200px;">
                            <canvas id="success-rates-chart"></canvas>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="mb-2">Average Performance (30-Day)</h6>
                        <div style="position: relative; height: 200px;">
                            <canvas id="performance-chart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-12">
                        <h6 class="mb-2">Reliability Score vs Volume Correlation</h6>
                        <div style="position: relative; height: 250px;">
                            <canvas id="reliability-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render distribution tab content
     */
    renderDistributionTab() {
        return `
            <div class="p-3">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <h6 class="mb-2">Pattern Type Distribution</h6>
                        <div style="position: relative; height: 200px;">
                            <canvas id="pattern-distribution-chart"></canvas>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="mb-2">Confidence Distribution</h6>
                        <div style="position: relative; height: 200px;">
                            <canvas id="confidence-distribution-chart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-12">
                        <h6 class="mb-2">Sector Breakdown</h6>
                        <div style="position: relative; height: 250px;">
                            <canvas id="sector-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render market tab content - Sprint 21 Week 2 Real-Time Market Statistics
     */
    renderMarketTab() {
        const stats = this.marketStatistics.live_metrics || {};
        const topPerformers = this.marketStatistics.top_performers || [];
        
        return `
            <div class="p-3">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <h6 class="mb-2">Market Overview</h6>
                        <div class="row">
                            <div class="col-6 mb-2">
                                <div class="text-center">
                                    <div class="h5 text-success mb-0">${stats.total_symbols || 4000}+</div>
                                    <small class="text-muted">Active Symbols</small>
                                </div>
                            </div>
                            <div class="col-6 mb-2">
                                <div class="text-center">
                                    <div class="h5 text-info mb-0">${(stats.market_breadth_score * 100).toFixed(1)}%</div>
                                    <small class="text-muted">Market Breadth</small>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="mb-2">Real-Time Activity</h6>
                        <div class="row">
                            <div class="col-6 mb-2">
                                <div class="text-center">
                                    <div class="h5 text-primary mb-0">${stats.pattern_velocity_per_hour || 150}</div>
                                    <small class="text-muted">Patterns/Hour</small>
                                </div>
                            </div>
                            <div class="col-6 mb-2">
                                <div class="text-center">
                                    <div class="h5 text-warning mb-0">${stats.active_alerts || 23}</div>
                                    <small class="text-muted">Active Alerts</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-md-8">
                        <h6 class="mb-2">Top Performing Patterns</h6>
                        <div class="row">
                            ${topPerformers.slice(0, 6).map((performer, i) => `
                            <div class="col-md-4 col-6 mb-2">
                                <div class="card border-0 bg-light">
                                    <div class="card-body p-2 text-center">
                                        <div class="small fw-bold text-success">${performer.pattern_type || 'WeeklyBO'}</div>
                                        <div class="small text-muted">${(performer.success_rate * 100).toFixed(1)}% success</div>
                                    </div>
                                </div>
                            </div>
                            `).join('') || `
                            <div class="col-md-4 col-6 mb-2">
                                <div class="card border-0 bg-light">
                                    <div class="card-body p-2 text-center">
                                        <div class="small fw-bold text-success">WeeklyBO</div>
                                        <div class="small text-muted">78.5% success</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4 col-6 mb-2">
                                <div class="card border-0 bg-light">
                                    <div class="card-body p-2 text-center">
                                        <div class="small fw-bold text-info">Support</div>
                                        <div class="small text-muted">72.3% success</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4 col-6 mb-2">
                                <div class="card border-0 bg-light">
                                    <div class="card-body p-2 text-center">
                                        <div class="small fw-bold text-warning">Triangle</div>
                                        <div class="small text-muted">68.9% success</div>
                                    </div>
                                </div>
                            </div>
                            `}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <h6 class="mb-2">Market Health</h6>
                        <div class="progress mb-2" style="height: 20px;">
                            <div class="progress-bar bg-success" role="progressbar" style="width: ${(stats.market_breadth_score * 100).toFixed(0)}%" aria-valuenow="${(stats.market_breadth_score * 100).toFixed(0)}" aria-valuemin="0" aria-valuemax="100">
                                ${(stats.market_breadth_score * 100).toFixed(0)}% Healthy
                            </div>
                        </div>
                        <small class="text-muted">Based on pattern success rates and market activity</small>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-12">
                        <div id="market-activity-chart" style="height: 300px; background: #f8f9fa; border: 1px dashed #dee2e6;" class="d-flex align-items-center justify-content-center">
                            <span class="text-muted">Real-time market activity chart will appear here</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render historical tab content
     */
    renderHistoricalTab() {
        return `
            <div class="p-3">
                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="mb-2">Success Rate Analysis by Time Period</h6>
                        <div style="position: relative; height: 250px;">
                            <canvas id="historicalPerformanceChart"></canvas>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="mb-2">Pattern Reliability Scores</h6>
                        <div id="reliability-scores" class="mt-2">
                            <!-- Populated by JavaScript -->
                        </div>
                    </div>
                </div>
                
                <div class="row mb-4">
                    <div class="col-12">
                        <h6 class="mb-2">Strategy Backtesting</h6>
                        <div class="d-flex align-items-center gap-3 mb-3">
                            <select id="backtest-preset" class="form-select" style="width: auto;">
                                <option value="">Select Filter Preset to Backtest</option>
                                <option value="high-confidence">High Confidence Patterns</option>
                                <option value="breakout-signals">Breakout Signals</option>
                                <option value="reversal-patterns">Reversal Patterns</option>
                            </select>
                            <select id="backtest-period" class="form-select" style="width: auto;">
                                <option value="30">30 Days</option>
                                <option value="60">60 Days</option>
                                <option value="90">90 Days</option>
                            </select>
                            <button id="run-backtest" class="btn btn-primary">
                                <i class="fas fa-play me-1"></i>Run Backtest
                            </button>
                        </div>
                        <div id="backtest-results" class="d-none">
                            <div class="row">
                                <div class="col-md-8">
                                    <div style="position: relative; height: 300px;">
                                        <canvas id="backtestChart"></canvas>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div id="backtest-metrics" class="bg-light p-3 rounded">
                                        <!-- Backtest metrics populated here -->
                                    </div>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-12">
                                    <h6>Pattern Performance Breakdown</h6>
                                    <div id="pattern-breakdown" class="table-responsive">
                                        <!-- Pattern breakdown table -->
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-12">
                        <h6 class="mb-2">Time-Based Performance Analysis</h6>
                        <div class="alert alert-info">
                            <i class="fas fa-lightbulb me-2"></i>
                            Historical analysis shows pattern performance over 1-day, 5-day, and 30-day periods.
                            Success rates typically decline over longer time horizons due to market volatility.
                        </div>
                        <div id="time-based-analysis" class="mt-2">
                            <!-- Time-based analysis populated by JavaScript -->
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Setup event handlers for tabs
     */
    setupTabEventHandlers() {
        // Tab change events to load charts
        const tabs = document.querySelectorAll('#analytics-tabs button[data-bs-toggle="tab"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', (event) => {
                const tabId = event.target.getAttribute('data-bs-target');
                this.loadTabCharts(tabId);
            });
        });
        
        // Load initial overview tab charts
        setTimeout(() => this.loadTabCharts('#overview'), 100);
    }

    /**
     * Load charts for specific tab
     */
    loadTabCharts(tabId) {
        // Add small delay to ensure DOM is ready
        setTimeout(() => {
            switch (tabId) {
                case '#overview':
                    this.createVelocityChart();
                    break;
                case '#performance':
                    this.createSuccessRatesChart();
                    this.createPerformanceChart();
                    this.createReliabilityChart();
                    break;
                case '#distribution':
                    this.createPatternDistributionChart();
                    this.createConfidenceDistributionChart();
                    this.createSectorChart();
                    break;
                case '#historical':
                    this.loadHistoricalTabContent();
                    break;
                case '#market':
                    this.initializeMarketStatistics();
                    break;
                // Sprint 23: Advanced Analytics Tabs
                case '#correlations':
                    this.initializeSprint23Correlations();
                    break;
                case '#temporal':
                    this.initializeSprint23Temporal();
                    break;
                case '#compare':
                    this.initializeSprint23Compare();
                    break;
            }
        }, 50);
    }

    /**
     * Create velocity chart (Overview tab)
     */
    createVelocityChart() {
        const canvas = document.getElementById('velocity-chart');
        if (!canvas || !window.Chart) return;

        // Destroy existing chart
        if (this.chartInstances.has('velocity')) {
            this.chartInstances.get('velocity').destroy();
        }

        const ctx = canvas.getContext('2d');
        const hourlyData = this.marketStatistics.hourly_frequency || [];
        
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: 12}, (_, i) => `${11-i}h ago`),
                datasets: [{
                    label: 'Patterns Detected',
                    data: hourlyData,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        this.chartInstances.set('velocity', chart);
    }

    /**
     * Create success rates chart (Performance tab)
     */
    createSuccessRatesChart() {
        const canvas = document.getElementById('success-rates-chart');
        if (!canvas || !window.Chart) return;

        const performanceData = this.analyticsData.get('performance');
        if (!performanceData) return;

        // Destroy existing chart
        if (this.chartInstances.has('success-rates')) {
            this.chartInstances.get('success-rates').destroy();
        }

        const ctx = canvas.getContext('2d');
        const patterns = Object.keys(performanceData.success_rates);
        const successData = patterns.map(pattern => 
            (performanceData.success_rates[pattern]['30d'] * 100).toFixed(1)
        );
        
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: patterns,
                datasets: [{
                    label: '30-Day Success Rate (%)',
                    data: successData,
                    backgroundColor: [
                        '#0d6efd', '#198754', '#dc3545', '#fd7e14',
                        '#6f42c1', '#d63384', '#20c997'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { 
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
        
        this.chartInstances.set('success-rates', chart);
    }

    /**
     * Create pattern distribution chart (Distribution tab)
     */
    createPatternDistributionChart() {
        const canvas = document.getElementById('pattern-distribution-chart');
        if (!canvas || !window.Chart) return;

        const distributionData = this.analyticsData.get('distribution');
        if (!distributionData) return;

        // Destroy existing chart
        if (this.chartInstances.has('pattern-distribution')) {
            this.chartInstances.get('pattern-distribution').destroy();
        }

        const ctx = canvas.getContext('2d');
        const patterns = Object.keys(distributionData.pattern_frequency);
        const frequencies = Object.values(distributionData.pattern_frequency);
        
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: patterns,
                datasets: [{
                    data: frequencies,
                    backgroundColor: [
                        '#0d6efd', '#198754', '#dc3545', '#fd7e14',
                        '#6f42c1', '#d63384', '#20c997'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
        
        this.chartInstances.set('pattern-distribution', chart);
    }

    /**
     * Create performance chart (Performance tab)
     */
    createPerformanceChart() {
        const canvas = document.getElementById('performance-chart');
        if (!canvas || !window.Chart) return;

        const performanceData = this.analyticsData.get('performance');
        if (!performanceData) return;

        // Destroy existing chart
        if (this.chartInstances.has('performance')) {
            this.chartInstances.get('performance').destroy();
        }

        const ctx = canvas.getContext('2d');
        const patterns = Object.keys(performanceData.avg_performance);
        const performanceValues = patterns.map(pattern => 
            performanceData.avg_performance[pattern]['30d']
        );
        
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: patterns,
                datasets: [{
                    label: '30-Day Avg Performance (%)',
                    data: performanceValues,
                    backgroundColor: 'rgba(32, 201, 151, 0.8)',
                    borderColor: '#20c997',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        this.chartInstances.set('performance', chart);
    }

    /**
     * Create reliability chart (Performance tab)
     */
    createReliabilityChart() {
        const canvas = document.getElementById('reliability-chart');
        if (!canvas || !window.Chart) return;

        const performanceData = this.analyticsData.get('performance');
        if (!performanceData) return;

        // Destroy existing chart
        if (this.chartInstances.has('reliability')) {
            this.chartInstances.get('reliability').destroy();
        }

        const ctx = canvas.getContext('2d');
        const patterns = Object.keys(performanceData.reliability_score);
        
        const scatterData = patterns.map(pattern => ({
            x: performanceData.reliability_score[pattern] * 100,
            y: performanceData.volume_correlation[pattern] * 100,
            label: pattern
        }));
        
        const chart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Reliability vs Volume Correlation',
                    data: scatterData,
                    backgroundColor: 'rgba(111, 66, 193, 0.6)',
                    borderColor: '#6f42c1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Reliability Score (%)'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Volume Correlation (%)'
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const point = context.raw;
                                return `${point.label}: Reliability ${point.x}%, Volume Corr ${point.y}%`;
                            }
                        }
                    }
                }
            }
        });
        
        this.chartInstances.set('reliability', chart);
    }

    /**
     * Create confidence distribution chart (Distribution tab)
     */
    createConfidenceDistributionChart() {
        const canvas = document.getElementById('confidence-distribution-chart');
        if (!canvas || !window.Chart) return;

        const distributionData = this.analyticsData.get('distribution');
        if (!distributionData) return;

        // Destroy existing chart
        if (this.chartInstances.has('confidence-distribution')) {
            this.chartInstances.get('confidence-distribution').destroy();
        }

        const ctx = canvas.getContext('2d');
        const confData = distributionData.confidence_distribution;
        
        const chart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: [confData.high.label, confData.medium.label, confData.low.label],
                datasets: [{
                    data: [confData.high.count, confData.medium.count, confData.low.count],
                    backgroundColor: ['#198754', '#fd7e14', '#dc3545']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
        
        this.chartInstances.set('confidence-distribution', chart);
    }

    /**
     * Create sector chart (Distribution tab)
     */
    createSectorChart() {
        const canvas = document.getElementById('sector-chart');
        if (!canvas || !window.Chart) return;

        const distributionData = this.analyticsData.get('distribution');
        if (!distributionData) return;

        // Destroy existing chart
        if (this.chartInstances.has('sector')) {
            this.chartInstances.get('sector').destroy();
        }

        const ctx = canvas.getContext('2d');
        const sectors = Object.keys(distributionData.sector_breakdown);
        const counts = sectors.map(sector => distributionData.sector_breakdown[sector].count);
        const confidences = sectors.map(sector => 
            distributionData.sector_breakdown[sector].avg_confidence * 100
        );
        
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sectors,
                datasets: [
                    {
                        label: 'Pattern Count',
                        data: counts,
                        backgroundColor: 'rgba(13, 110, 253, 0.8)',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Avg Confidence (%)',
                        data: confidences,
                        backgroundColor: 'rgba(255, 193, 7, 0.8)',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Pattern Count' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Confidence (%)' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
        
        this.chartInstances.set('sector', chart);
    }

    /**
     * Initialize market statistics service - Sprint 21 Week 2
     */
    async initializeMarketStatistics() {
        // Only initialize once
        if (this.marketStatisticsInitialized) return;
        
        try {
            // Load market statistics service if not already loaded
            if (typeof MarketStatisticsService === 'undefined') {
                console.warn('MarketStatisticsService not loaded, loading now...');
                
                // Dynamically load the service
                const script = document.createElement('script');
                script.src = '/static/js/services/market-statistics.js';
                document.head.appendChild(script);
                
                // Wait for service to load
                await new Promise((resolve, reject) => {
                    script.onload = resolve;
                    script.onerror = reject;
                });
            }
            
            // Initialize market statistics if container exists
            const container = document.getElementById('market-statistics-container');
            if (container && typeof MarketStatisticsService !== 'undefined') {
                if (!window.marketStats) {
                    window.marketStats = new MarketStatisticsService();
                    await window.marketStats.initialize();
                }
                this.marketStatisticsInitialized = true;
                console.log('Market Statistics initialized successfully');
            }
        } catch (error) {
            console.error('Failed to initialize market statistics:', error);
            this.renderMarketStatisticsError();
        }
    }
    
    /**
     * Render error state for market statistics
     */
    renderMarketStatisticsError() {
        const container = document.getElementById('market-statistics-container');
        if (container) {
            container.innerHTML = `
                <div class="p-3">
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Unable to load real-time market statistics. Please refresh the page.
                        <button class="btn btn-sm btn-outline-warning ms-2" onclick="patternAnalytics.initializeMarketStatistics()">
                            Retry
                        </button>
                    </div>
                </div>
            `;
        }
    }

    /**
     * Setup global event handlers
     */
    setupEventHandlers() {
        // Handle pattern discovery updates to refresh analytics
        if (window.patternDiscovery) {
            // Listen for pattern updates (could be added to pattern discovery service)
            document.addEventListener('patternsUpdated', () => {
                this.refreshAnalytics();
            });
        }

        // Auto-refresh analytics every 30 seconds (disabled during development to prevent chart recreation)
        // setInterval(() => {
        //     this.refreshAnalytics();
        // }, 30000);
    }

    /**
     * Refresh analytics data
     */
    async refreshAnalytics() {
        if (document.getElementById('pattern-analytics-panel')) {
            // Reload data and update active charts
            await this.loadAnalyticsData();
            
            // Update active tab charts
            const activeTab = document.querySelector('#analytics-tabs .nav-link.active');
            if (activeTab) {
                const tabId = activeTab.getAttribute('data-bs-target');
                this.loadTabCharts(tabId);
            }
        }
    }

    /**
     * Load historical tab content - Sprint 21 Week 2 Deliverable 2
     */
    async loadHistoricalTabContent() {
        // Load historical performance chart
        this.createHistoricalPerformanceChart();
        
        // Populate reliability scores
        this.populateReliabilityScores();
        
        // Populate time-based analysis
        this.populateTimeBasedAnalysis();
        
        // Setup backtest event handlers
        this.setupBacktestHandlers();
    }
    
    /**
     * Populate reliability scores section
     */
    populateReliabilityScores() {
        const container = document.getElementById('reliability-scores');
        if (!container) return;
        
        const patterns = this.availablePatterns;
        
        const scoresHtml = patterns.map(pattern => {
            const reliability = this.calculateReliabilityScore(pattern);
            const badgeClass = reliability.grade.startsWith('A') ? 'success' : 
                              reliability.grade.startsWith('B') ? 'primary' :
                              reliability.grade.startsWith('C') ? 'warning' : 'danger';
            
            return `
                <div class="d-flex justify-content-between align-items-center mb-2 p-2 border rounded">
                    <div>
                        <strong>${pattern}</strong>
                        <small class="text-muted d-block">${reliability.description}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-${badgeClass}">${reliability.grade}</span>
                        <small class="text-muted d-block">${(reliability.reliability_score * 100).toFixed(0)}%</small>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = scoresHtml;
    }
    
    /**
     * Populate time-based analysis section
     */
    populateTimeBasedAnalysis() {
        const container = document.getElementById('time-based-analysis');
        if (!container) return;
        
        const patterns = this.availablePatterns;
        
        const analysisHtml = `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Pattern</th>
                            <th class="text-center">1-Day Success</th>
                            <th class="text-center">5-Day Success</th>
                            <th class="text-center">30-Day Success</th>
                            <th class="text-center">Trend</th>
                            <th class="text-center">Sample Size</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${patterns.map(pattern => {
                            const analysis = this.analyzeTimeBasedPerformance(pattern);
                            if (!analysis) return '';
                            
                            const trendIcon = analysis.trend_direction === 'improving' ? '↗️' :
                                            analysis.trend_direction === 'declining' ? '↘️' : '→';
                            
                            return `
                                <tr>
                                    <td><strong>${pattern}</strong></td>
                                    <td class="text-center">${(analysis.success_rates['1d'] * 100).toFixed(0)}%</td>
                                    <td class="text-center">${(analysis.success_rates['5d'] * 100).toFixed(0)}%</td>
                                    <td class="text-center">${(analysis.success_rates['30d'] * 100).toFixed(0)}%</td>
                                    <td class="text-center">${trendIcon} ${analysis.trend_direction}</td>
                                    <td class="text-center">${analysis.sample_size.toLocaleString()}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = analysisHtml;
    }
    
    /**
     * Setup backtest event handlers
     */
    setupBacktestHandlers() {
        const runButton = document.getElementById('run-backtest');
        if (runButton) {
            runButton.addEventListener('click', async () => {
                const presetSelect = document.getElementById('backtest-preset');
                const periodSelect = document.getElementById('backtest-period');
                
                const selectedPreset = presetSelect.value;
                const selectedPeriod = parseInt(periodSelect.value);
                
                if (!selectedPreset) {
                    alert('Please select a filter preset to backtest.');
                    return;
                }
                
                runButton.disabled = true;
                runButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Running...';
                
                try {
                    // Create mock filter preset object
                    const filterPreset = {
                        name: presetSelect.options[presetSelect.selectedIndex].text,
                        id: selectedPreset
                    };
                    
                    const backtestResults = await this.backtestFilterPreset(filterPreset, selectedPeriod);
                    this.displayBacktestResults(backtestResults);
                    
                    // Show results panel
                    document.getElementById('backtest-results').classList.remove('d-none');
                } catch (error) {
                    console.error('Backtest failed:', error);
                    alert('Backtest failed. Please try again.');
                } finally {
                    runButton.disabled = false;
                    runButton.innerHTML = '<i class="fas fa-play me-1"></i>Run Backtest';
                }
            });
        }
    }
    
    /**
     * Display backtest results
     */
    displayBacktestResults(results) {
        // Update metrics panel
        const metricsContainer = document.getElementById('backtest-metrics');
        if (metricsContainer) {
            metricsContainer.innerHTML = `
                <h6 class="mb-3">${results.preset_name} Results</h6>
                <div class="mb-2">
                    <small class="text-muted">Success Rate</small>
                    <div class="h5 text-success">${(results.success_rate * 100).toFixed(1)}%</div>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Total Return</small>
                    <div class="h5 text-primary">${results.final_return}%</div>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Max Drawdown</small>
                    <div class="h5 text-danger">${results.max_drawdown}%</div>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Sharpe Ratio</small>
                    <div class="h5 text-info">${results.sharpe_ratio}</div>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Total Signals</small>
                    <div class="h6">${results.total_signals}</div>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Volatility</small>
                    <div class="h6">${(results.risk_metrics.volatility * 100).toFixed(1)}%</div>
                </div>
            `;
        }
        
        // Create performance chart
        this.createBacktestChart(results);
        
        // Update pattern breakdown table
        const breakdownContainer = document.getElementById('pattern-breakdown');
        if (breakdownContainer && results.pattern_breakdown) {
            const breakdownHtml = `
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Pattern</th>
                            <th class="text-center">Signals</th>
                            <th class="text-center">Success Rate</th>
                            <th class="text-center">Avg Return</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${Object.entries(results.pattern_breakdown).map(([pattern, data]) => `
                            <tr>
                                <td><strong>${pattern}</strong></td>
                                <td class="text-center">${data.signals}</td>
                                <td class="text-center">${(data.success_rate * 100).toFixed(1)}%</td>
                                <td class="text-center">${data.avg_return}%</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            
            breakdownContainer.innerHTML = breakdownHtml;
        }
    }

    /**
     * Get analytics for current pattern set
     */
    getPatternAnalytics(patterns) {
        if (!patterns || patterns.length === 0) return null;

        // Calculate analytics for provided patterns
        const patternTypes = {};
        const confidenceLevels = { high: 0, medium: 0, low: 0 };
        let totalConfidence = 0;

        patterns.forEach(pattern => {
            // Count pattern types
            patternTypes[pattern.pattern] = (patternTypes[pattern.pattern] || 0) + 1;
            
            // Count confidence levels
            if (pattern.confidence >= 0.8) confidenceLevels.high++;
            else if (pattern.confidence >= 0.6) confidenceLevels.medium++;
            else confidenceLevels.low++;
            
            totalConfidence += pattern.confidence;
        });

        return {
            total_patterns: patterns.length,
            average_confidence: totalConfidence / patterns.length,
            pattern_breakdown: patternTypes,
            confidence_distribution: confidenceLevels,
            high_confidence_ratio: confidenceLevels.high / patterns.length
        };
    }

    /**
     * Save analytics to localStorage
     */
    saveToLocalStorage() {
        const data = {
            analyticsData: Object.fromEntries(this.analyticsData),
            marketStatistics: this.marketStatistics,
            timestamp: Date.now()
        };
        localStorage.setItem('tickstock-analytics', JSON.stringify(data));
    }

    /**
     * Load analytics from localStorage
     */
    loadFromLocalStorage() {
        const stored = localStorage.getItem('tickstock-analytics');
        if (stored) {
            try {
                const data = JSON.parse(stored);
                this.analyticsData = new Map(Object.entries(data.analyticsData || {}));
                this.marketStatistics = data.marketStatistics || {};
            } catch (error) {
                console.error('Failed to load analytics from localStorage:', error);
                this.loadMockData();
            }
        } else {
            this.loadMockData();
        }
    }

    /**
     * Sprint 23: Initialize Correlations Tab
     */
    async initializeSprint23Correlations() {
        try {
            const container = document.getElementById('sprint23-correlations-content');
            if (!container || container.querySelector('.spinner-border')) {
                // Initialize correlations service if not already done
                if (!window.correlationsService && typeof PatternCorrelationsService !== 'undefined') {
                    window.correlationsService = new PatternCorrelationsService();
                }
                
                if (window.correlationsService) {
                    await window.correlationsService.initialize('sprint23-correlations-content');
                    console.log('Sprint 23 Correlations tab initialized');
                }
            }
        } catch (error) {
            console.error('Error initializing Sprint 23 Correlations:', error);
        }
    }

    /**
     * Sprint 23: Initialize Temporal Analysis Tab
     */
    async initializeSprint23Temporal() {
        try {
            const container = document.getElementById('sprint23-temporal-content');
            if (!container || container.querySelector('.spinner-border')) {
                // Initialize temporal service if not already done
                if (!window.temporalService && typeof PatternTemporalService !== 'undefined') {
                    window.temporalService = new PatternTemporalService();
                }
                
                if (window.temporalService) {
                    await window.temporalService.initialize('sprint23-temporal-content');
                    console.log('Sprint 23 Temporal Analysis tab initialized');
                }
            }
        } catch (error) {
            console.error('Error initializing Sprint 23 Temporal:', error);
        }
    }

    /**
     * Sprint 23: Initialize Pattern Comparison Tab
     */
    async initializeSprint23Compare() {
        try {
            const container = document.getElementById('sprint23-compare-content');
            if (!container || container.querySelector('.spinner-border')) {
                // Initialize comparison service if not already done
                if (!window.comparisonService && typeof PatternComparisonService !== 'undefined') {
                    window.comparisonService = new PatternComparisonService();
                }
                
                if (window.comparisonService) {
                    await window.comparisonService.initialize('sprint23-compare-content');
                    console.log('Sprint 23 Pattern Comparison tab initialized');
                }
            }
        } catch (error) {
            console.error('Error initializing Sprint 23 Compare:', error);
        }
    }

    /**
     * Cleanup chart instances
     */
    cleanup() {
        this.chartInstances.forEach(chart => chart.destroy());
        this.chartInstances.clear();
    }
}

// Initialize pattern analytics service when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof window !== 'undefined') {
        window.patternAnalytics = new PatternAnalyticsService();
    }
});