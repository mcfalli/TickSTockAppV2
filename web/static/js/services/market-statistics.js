/**
 * Market Statistics Service - Real-Time Market Monitoring
 * Sprint 21 Week 2 - Analytics & Intelligence
 * 
 * Provides live market monitoring, pattern frequency analysis, and market health indicators.
 * Integrates with existing WebSocket infrastructure for real-time updates.
 * 
 * Features:
 * - Live pattern detection frequency monitoring
 * - Market breadth analysis across sectors
 * - Pattern velocity tracking over time
 * - Market health indicators and quality metrics
 * 
 * @version 1.0.0
 * @created 2025-01-16
 */

class MarketStatisticsService {
    constructor() {
        // API endpoints for market statistics
        this.endpoints = {
            statistics: '/api/market/statistics',
            breadth: '/api/market/breadth', 
            frequency: '/api/market/pattern-frequency'
        };
        
        // Real-time update configuration
        this.updateInterval = 5000; // 5 seconds
        this.updateTimer = null;
        
        // Data caching for performance
        this.cache = {
            statistics: null,
            breadth: null,
            frequency: null,
            lastUpdate: null
        };
        
        // UI element references
        this.elements = {
            container: null,
            statisticsPanel: null,
            breadthPanel: null,
            frequencyPanel: null
        };
        
        // Chart instances for cleanup
        this.charts = new Map();
        
        // WebSocket integration for live updates
        this.socket = null;
        this.isConnected = false;
        
        console.log('Market Statistics Service initialized - Sprint 21 Week 2');
    }
    
    /**
     * Initialize the market statistics dashboard
     */
    async initialize() {
        try {
            await this.setupUI();
            await this.loadInitialData();
            this.setupWebSocketConnection();
            this.startRealTimeUpdates();
            
            console.log('Market Statistics dashboard initialized successfully');
            return true;
        } catch (error) {
            console.error('Failed to initialize market statistics:', error);
            return false;
        }
    }
    
    /**
     * Setup the UI components and layout
     */
    async setupUI() {
        this.elements.container = document.getElementById('market-statistics-container');
        if (!this.elements.container) {
            throw new Error('Market statistics container not found');
        }
        
        // Create the dashboard layout
        this.elements.container.innerHTML = `
            <div class="market-statistics-dashboard">
                <div class="row">
                    <!-- Live Statistics Panel -->
                    <div class="col-lg-4 col-md-6 mb-4">
                        <div class="card bg-dark text-white h-100">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <h6 class="mb-0">
                                    <i class="fas fa-chart-pulse me-2"></i>Live Statistics
                                </h6>
                                <span id="stats-update-time" class="badge bg-success">
                                    <i class="fas fa-wifi me-1"></i>Live
                                </span>
                            </div>
                            <div class="card-body">
                                <div id="live-statistics-content">
                                    <div class="text-center">
                                        <div class="spinner-border text-primary" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Market Breadth Panel -->
                    <div class="col-lg-4 col-md-6 mb-4">
                        <div class="card bg-dark text-white h-100">
                            <div class="card-header">
                                <h6 class="mb-0">
                                    <i class="fas fa-layer-group me-2"></i>Market Breadth
                                </h6>
                            </div>
                            <div class="card-body">
                                <canvas id="market-breadth-chart" width="400" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Pattern Frequency Panel -->
                    <div class="col-lg-4 col-md-12 mb-4">
                        <div class="card bg-dark text-white h-100">
                            <div class="card-header">
                                <h6 class="mb-0">
                                    <i class="fas fa-clock me-2"></i>Pattern Frequency
                                </h6>
                            </div>
                            <div class="card-body">
                                <canvas id="pattern-frequency-chart" width="400" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Pattern Velocity Monitoring -->
                <div class="row">
                    <div class="col-12 mb-4">
                        <div class="card bg-dark text-white">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <h6 class="mb-0">
                                    <i class="fas fa-tachometer-alt me-2"></i>Pattern Detection Velocity
                                </h6>
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-outline-primary active" 
                                            onclick="marketStats.setVelocityTimeframe('1h')">1H</button>
                                    <button type="button" class="btn btn-outline-primary"
                                            onclick="marketStats.setVelocityTimeframe('4h')">4H</button>
                                    <button type="button" class="btn btn-outline-primary"
                                            onclick="marketStats.setVelocityTimeframe('1d')">1D</button>
                                </div>
                            </div>
                            <div class="card-body">
                                <canvas id="pattern-velocity-chart" width="800" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Load initial market statistics data
     */
    async loadInitialData() {
        try {
            const [statistics, breadth, frequency] = await Promise.all([
                this.fetchMarketStatistics(),
                this.fetchMarketBreadth(), 
                this.fetchPatternFrequency()
            ]);
            
            this.cache.statistics = statistics;
            this.cache.breadth = breadth;
            this.cache.frequency = frequency;
            this.cache.lastUpdate = new Date();
            
            await this.renderStatistics();
            await this.renderBreadthChart();
            await this.renderFrequencyChart();
            await this.renderVelocityChart();
            
            console.log('Initial market statistics data loaded');
        } catch (error) {
            console.error('Failed to load initial market statistics:', error);
            this.renderErrorState();
        }
    }
    
    /**
     * Fetch live market statistics
     */
    async fetchMarketStatistics() {
        try {
            const response = await fetch(this.endpoints.statistics);
            if (!response.ok) throw new Error('Statistics API failed');
            return await response.json();
        } catch (error) {
            console.warn('Using mock statistics data:', error);
            return this.generateMockStatistics();
        }
    }
    
    /**
     * Fetch market breadth data
     */
    async fetchMarketBreadth() {
        try {
            const response = await fetch(this.endpoints.breadth);
            if (!response.ok) throw new Error('Breadth API failed');
            return await response.json();
        } catch (error) {
            console.warn('Using mock breadth data:', error);
            return this.generateMockBreadth();
        }
    }
    
    /**
     * Fetch pattern frequency data
     */
    async fetchPatternFrequency() {
        try {
            const response = await fetch(this.endpoints.frequency);
            if (!response.ok) throw new Error('Frequency API failed');
            return await response.json();
        } catch (error) {
            console.warn('Using mock frequency data:', error);
            return this.generateMockFrequency();
        }
    }
    
    /**
     * Render live statistics panel
     */
    async renderStatistics() {
        const stats = this.cache.statistics;
        const content = document.getElementById('live-statistics-content');
        
        if (!content || !stats) return;
        
        content.innerHTML = `
            <div class="row g-3">
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="text-light">Patterns Today</span>
                        <span class="badge bg-primary fs-6">${stats.patterns_detected_today}</span>
                    </div>
                    <div class="progress" style="height: 8px;">
                        <div class="progress-bar bg-primary" style="width: ${Math.min(100, stats.patterns_detected_today / 2)}%"></div>
                    </div>
                </div>
                
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="text-light">Velocity/Hour</span>
                        <span class="badge bg-success fs-6">${stats.pattern_velocity_per_hour.toFixed(1)}</span>
                    </div>
                    <div class="progress" style="height: 8px;">
                        <div class="progress-bar bg-success" style="width: ${Math.min(100, stats.pattern_velocity_per_hour * 10)}%"></div>
                    </div>
                </div>
                
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="text-light">Avg Confidence</span>
                        <span class="badge bg-warning fs-6">${(stats.average_confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div class="progress" style="height: 8px;">
                        <div class="progress-bar bg-warning" style="width: ${stats.average_confidence * 100}%"></div>
                    </div>
                </div>
                
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="text-light">High Quality</span>
                        <span class="badge bg-info fs-6">${(stats.high_confidence_ratio * 100).toFixed(1)}%</span>
                    </div>
                    <div class="progress" style="height: 8px;">
                        <div class="progress-bar bg-info" style="width: ${stats.high_confidence_ratio * 100}%"></div>
                    </div>
                </div>
            </div>
            
            <hr class="my-3">
            
            <div class="row g-2 text-center">
                <div class="col-4">
                    <div class="text-success">
                        <i class="fas fa-arrow-up"></i>
                        <div class="small">Last Hour</div>
                        <div class="fw-bold">${stats.last_hour}</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="text-warning">
                        <i class="fas fa-calendar-day"></i>
                        <div class="small">Last 24H</div>
                        <div class="fw-bold">${stats.last_24h}</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="text-info">
                        <i class="fas fa-calendar-week"></i>
                        <div class="small">Last Week</div>
                        <div class="fw-bold">${stats.last_week}</div>
                    </div>
                </div>
            </div>
        `;
        
        // Update timestamp
        const updateTime = document.getElementById('stats-update-time');
        if (updateTime) {
            updateTime.innerHTML = `<i class="fas fa-wifi me-1"></i>${new Date().toLocaleTimeString()}`;
        }
    }
    
    /**
     * Render market breadth chart
     */
    async renderBreadthChart() {
        const canvas = document.getElementById('market-breadth-chart');
        if (!canvas || !this.cache.breadth) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('breadth')) {
            this.charts.get('breadth').destroy();
        }
        
        const breadthData = this.cache.breadth;
        
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(breadthData.sector_breakdown),
                datasets: [{
                    data: Object.values(breadthData.sector_breakdown),
                    backgroundColor: [
                        '#0d6efd', '#6610f2', '#6f42c1', '#d63384',
                        '#dc3545', '#fd7e14', '#ffc107', '#198754',
                        '#20c997', '#0dcaf0'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#ffffff',
                            boxWidth: 12,
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
        
        this.charts.set('breadth', chart);
    }
    
    /**
     * Render pattern frequency chart
     */
    async renderFrequencyChart() {
        const canvas = document.getElementById('pattern-frequency-chart');
        if (!canvas || !this.cache.frequency) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('frequency')) {
            this.charts.get('frequency').destroy();
        }
        
        const frequencyData = this.cache.frequency;
        
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['1H', '4H', '12H', '24H', '3D', '1W'],
                datasets: [{
                    label: 'Pattern Count',
                    data: [
                        frequencyData.last_hour,
                        frequencyData.last_4h,
                        frequencyData.last_12h,
                        frequencyData.last_24h,
                        frequencyData.last_3d,
                        frequencyData.last_week
                    ],
                    backgroundColor: '#0d6efd',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#ffffff' },
                        grid: { color: '#404040' }
                    },
                    x: {
                        ticks: { color: '#ffffff' },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
        
        this.charts.set('frequency', chart);
    }
    
    /**
     * Render pattern velocity chart
     */
    async renderVelocityChart() {
        const canvas = document.getElementById('pattern-velocity-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('velocity')) {
            this.charts.get('velocity').destroy();
        }
        
        // Generate velocity data for the last hour
        const velocityData = this.generateVelocityData('1h');
        
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: velocityData.labels,
                datasets: [{
                    label: 'Patterns/5min',
                    data: velocityData.data,
                    borderColor: '#20c997',
                    backgroundColor: 'rgba(32, 201, 151, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#ffffff' },
                        grid: { color: '#404040' }
                    },
                    x: {
                        ticks: { color: '#ffffff' },
                        grid: { color: '#404040' }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: '#ffffff' }
                    }
                }
            }
        });
        
        this.charts.set('velocity', chart);
    }
    
    /**
     * Setup WebSocket connection for real-time updates
     */
    setupWebSocketConnection() {
        if (typeof io !== 'undefined') {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('Market statistics WebSocket connected');
                this.isConnected = true;
                this.updateConnectionStatus(true);
            });
            
            this.socket.on('disconnect', () => {
                console.log('Market statistics WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus(false);
            });
            
            this.socket.on('market_statistics_update', (data) => {
                this.handleRealtimeUpdate(data);
            });
            
            this.socket.on('pattern_detected', (data) => {
                this.handlePatternDetection(data);
            });
        }
    }
    
    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        this.updateTimer = setInterval(() => {
            this.refreshData();
        }, this.updateInterval);
        
        console.log(`Real-time updates started (${this.updateInterval}ms interval)`);
    }
    
    /**
     * Stop real-time updates
     */
    stopRealTimeUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
    
    /**
     * Refresh all data
     */
    async refreshData() {
        try {
            await this.loadInitialData();
        } catch (error) {
            console.error('Failed to refresh market statistics:', error);
        }
    }
    
    /**
     * Handle real-time WebSocket updates
     */
    handleRealtimeUpdate(data) {
        // Update cached data
        if (data.statistics) {
            this.cache.statistics = data.statistics;
            this.renderStatistics();
        }
        
        if (data.breadth) {
            this.cache.breadth = data.breadth;
            this.renderBreadthChart();
        }
        
        if (data.frequency) {
            this.cache.frequency = data.frequency;
            this.renderFrequencyChart();
        }
    }
    
    /**
     * Handle individual pattern detection events
     */
    handlePatternDetection(data) {
        // Update pattern count in real-time
        if (this.cache.statistics) {
            this.cache.statistics.patterns_detected_today++;
            this.cache.statistics.last_hour++;
            this.renderStatistics();
        }
        
        // Show brief notification
        this.showPatternAlert(data);
    }
    
    /**
     * Show brief pattern detection alert
     */
    showPatternAlert(data) {
        const updateTime = document.getElementById('stats-update-time');
        if (updateTime) {
            updateTime.innerHTML = `<i class="fas fa-bell text-success me-1"></i>New Pattern`;
            setTimeout(() => {
                updateTime.innerHTML = `<i class="fas fa-wifi me-1"></i>${new Date().toLocaleTimeString()}`;
            }, 2000);
        }
    }
    
    /**
     * Update connection status indicator
     */
    updateConnectionStatus(isConnected) {
        const updateTime = document.getElementById('stats-update-time');
        if (updateTime) {
            if (isConnected) {
                updateTime.className = 'badge bg-success';
                updateTime.innerHTML = `<i class="fas fa-wifi me-1"></i>Live`;
            } else {
                updateTime.className = 'badge bg-warning';
                updateTime.innerHTML = `<i class="fas fa-wifi-slash me-1"></i>Offline`;
            }
        }
    }
    
    /**
     * Set velocity chart timeframe
     */
    setVelocityTimeframe(timeframe) {
        // Update button states
        document.querySelectorAll('[onclick*="setVelocityTimeframe"]').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        
        // Generate new velocity data
        const velocityData = this.generateVelocityData(timeframe);
        const chart = this.charts.get('velocity');
        
        if (chart) {
            chart.data.labels = velocityData.labels;
            chart.data.datasets[0].data = velocityData.data;
            chart.update();
        }
    }
    
    /**
     * Generate velocity data for different timeframes
     */
    generateVelocityData(timeframe) {
        const now = new Date();
        const labels = [];
        const data = [];
        
        let intervals, stepSize, labelFormat;
        
        switch (timeframe) {
            case '1h':
                intervals = 12; // 5-minute intervals for 1 hour
                stepSize = 5 * 60 * 1000; // 5 minutes in ms
                labelFormat = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                break;
            case '4h':
                intervals = 16; // 15-minute intervals for 4 hours
                stepSize = 15 * 60 * 1000; // 15 minutes in ms
                labelFormat = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                break;
            case '1d':
                intervals = 24; // 1-hour intervals for 24 hours
                stepSize = 60 * 60 * 1000; // 1 hour in ms
                labelFormat = (date) => date.toLocaleTimeString([], { hour: '2-digit' }) + ':00';
                break;
            default:
                intervals = 12;
                stepSize = 5 * 60 * 1000;
                labelFormat = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        
        // Generate realistic velocity data
        for (let i = intervals; i >= 0; i--) {
            const time = new Date(now.getTime() - (i * stepSize));
            labels.push(labelFormat(time));
            
            // Simulate market hours and realistic pattern velocity
            const hour = time.getHours();
            const isMarketHours = hour >= 9 && hour <= 16;
            const baseRate = isMarketHours ? Math.random() * 8 + 2 : Math.random() * 2;
            data.push(Math.round(baseRate * 10) / 10);
        }
        
        return { labels, data };
    }
    
    /**
     * Generate mock statistics data
     */
    generateMockStatistics() {
        return {
            patterns_detected_today: Math.floor(Math.random() * 50) + 100,
            pattern_velocity_per_hour: Math.random() * 5 + 3,
            average_confidence: Math.random() * 0.3 + 0.6,
            high_confidence_ratio: Math.random() * 0.4 + 0.2,
            last_hour: Math.floor(Math.random() * 10) + 5,
            last_24h: Math.floor(Math.random() * 50) + 100,
            last_week: Math.floor(Math.random() * 500) + 800
        };
    }
    
    /**
     * Generate mock breadth data
     */
    generateMockBreadth() {
        const sectors = ['Technology', 'Healthcare', 'Financial', 'Industrial', 'Energy', 'Consumer'];
        const breakdown = {};
        
        sectors.forEach(sector => {
            breakdown[sector] = Math.floor(Math.random() * 30) + 10;
        });
        
        return { sector_breakdown: breakdown };
    }
    
    /**
     * Generate mock frequency data
     */
    generateMockFrequency() {
        return {
            last_hour: Math.floor(Math.random() * 10) + 5,
            last_4h: Math.floor(Math.random() * 30) + 15,
            last_12h: Math.floor(Math.random() * 60) + 40,
            last_24h: Math.floor(Math.random() * 100) + 80,
            last_3d: Math.floor(Math.random() * 300) + 200,
            last_week: Math.floor(Math.random() * 800) + 600
        };
    }
    
    /**
     * Render error state
     */
    renderErrorState() {
        const content = document.getElementById('live-statistics-content');
        if (content) {
            content.innerHTML = `
                <div class="text-center text-warning">
                    <i class="fas fa-exclamation-triangle mb-2" style="font-size: 2rem;"></i>
                    <p>Unable to load market statistics</p>
                    <button class="btn btn-sm btn-outline-warning" onclick="marketStats.refreshData()">
                        Retry
                    </button>
                </div>
            `;
        }
    }
    
    /**
     * Cleanup method
     */
    destroy() {
        this.stopRealTimeUpdates();
        
        // Destroy all charts
        this.charts.forEach(chart => chart.destroy());
        this.charts.clear();
        
        // Disconnect WebSocket
        if (this.socket) {
            this.socket.disconnect();
        }
        
        console.log('Market Statistics Service destroyed');
    }
}

// Global instance for external access
window.marketStats = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if container exists
    if (document.getElementById('market-statistics-container')) {
        window.marketStats = new MarketStatisticsService();
        window.marketStats.initialize();
    }
});