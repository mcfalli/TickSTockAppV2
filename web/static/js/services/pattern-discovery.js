/**
 * Pattern Discovery Service - TickStock.ai
 * Sprint 20 Phase 2: UI Layer for Pattern Discovery Dashboard
 * 
 * Integrates with existing TickStock JavaScript architecture
 * Consumes Sprint 19 Pattern Discovery APIs
 * Uses established Bootstrap + jQuery patterns
 * 
 * ⚠️⚠️⚠️ CRITICAL TECHNICAL DEBT WARNING ⚠️⚠️⚠️
 * 
 * This file contains 5 CRITICAL mock implementations that MUST be replaced
 * before production deployment. See SPRINT_24_TECHNICAL_DEBT.md for details.
 * 
 * BLOCKING PRODUCTION DEPLOYMENT:
 * - Mock chart data (fake stock prices)
 * - Mock performance analytics (fake success rates) 
 * - Mock symbol search (only 25 hardcoded symbols)
 * - Mock sector mapping (hardcoded classifications)
 * - Mock alert creation (no persistence)
 * 
 * Status: 🔴 NOT PRODUCTION READY - API INTEGRATION REQUIRED 🔴
 */

class PatternDiscoveryService {
    constructor() {
        this.apiBaseUrl = '/api';
        this.patterns = [];
        this.filters = {
            universe: 'sp500',
            confidence_min: 0.7,
            limit: 100,
            symbols: [], // Sprint 24: Selected symbols filter
            sector: 'all' // Sprint 24: Sector filter
        };
        this.isLoading = false;
        this.socket = null;
        
        // Sprint 22: Dynamic Pattern Loading
        this.availablePatterns = [];
        this.patternDefinitions = new Map();
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    init() {
        this.setupWebSocket();
        this.loadPatternDefinitions().then(() => {
            this.renderUI();
            this.loadPatterns();
        });
        
        // Auto-refresh every 30 seconds
        setInterval(() => this.loadPatterns(), 30000);
    }

    /**
     * Sprint 22/24: Load pattern definitions with enhanced error handling
     */
    async loadPatternDefinitions(retryCount = 0) {
        try {
            
            // Enhanced fetch with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
            
            const response = await fetch('/api/patterns/definitions', {
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                if (response.status >= 500 && retryCount < 2) {
                    console.warn(`Pattern definitions API failed (${response.status}), retrying...`);
                    await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
                    return this.loadPatternDefinitions(retryCount + 1);
                }
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
                
                
                if (retryCount > 0) {
                    this.showNotification(`Pattern definitions loaded after ${retryCount} ${retryCount === 1 ? 'retry' : 'retries'}`, 'success');
                }
            } else {
                throw new Error('Invalid pattern definitions response format');
            }
            
        } catch (error) {
            console.warn('Failed to load pattern definitions from API, using fallback:', error);
            
            // Use fallback pattern definitions
            this.availablePatterns = ['WeeklyBO', 'DailyBO', 'Doji', 'Hammer', 'ShootingStar', 'Engulfing'];
            this.availablePatterns.forEach(name => {
                this.patternDefinitions.set(name, {
                    name: name,
                    short_description: `${name} Pattern`,
                    enabled: true
                });
            });
            
            // Show warning only if not using fallback intentionally
            if (retryCount === 0 && error.name !== 'AbortError') {
                this.showNotification('Using default pattern types (API unavailable)', 'warning');
            }
        }
    }
    
    setupWebSocket() {
        if (typeof io !== 'undefined') {
            this.socket = io();
            
            this.socket.on('pattern_alert', (data) => {
                this.handleNewPattern(data);
                this.showNotification(`New ${data.event.data.pattern} pattern on ${data.event.data.symbol}`, 'success');
            });
            
            this.socket.on('connect', () => {
                this.updateConnectionStatus(true);
            });
            
            this.socket.on('disconnect', () => {
                this.updateConnectionStatus(false);
            });
        }
    }
    
    renderUI() {
        // Check if we're in sidebar mode (new system) or standalone mode (old system)
        const sidebarSystem = window.sidebarNavigation;
        let contentArea;
        
        if (sidebarSystem) {
            // New sidebar system - render into main content area
            contentArea = document.getElementById('main-content-area');
        } else {
            // Fallback to old system
            contentArea = document.getElementById('pattern-discovery-content');
        }
        
        if (!contentArea) return;
        
        contentArea.innerHTML = `
            <div class="pattern-discovery-dashboard">
                <!-- Header -->
                <div class="d-flex justify-content-between align-items-center mb-4 p-3 rounded" style="background-color: var(--color-background-secondary); border: 1px solid var(--color-border-primary);">
                    <div class="d-flex align-items-center">
                        <h2 class="h4 mb-0 text-primary me-3">
                            <i class="fas fa-chart-line me-2"></i>
                            Pattern Discovery Dashboard
                        </h2>
                        <span id="ws-status" class="badge bg-secondary">Connecting...</span>
                    </div>
                    
                    <div class="d-flex align-items-center">
                        <button id="refresh-btn" class="btn btn-outline-primary btn-sm me-2">
                            <i class="fas fa-sync-alt me-1"></i>
                            Refresh
                        </button>
                        <span id="pattern-count" class="badge bg-info">0 patterns</span>
                    </div>
                </div>
                
                <!-- Error Display -->
                <div id="error-display" class="alert alert-danger d-none" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <span id="error-message"></span>
                    <button class="btn btn-sm btn-outline-danger ms-2" onclick="patternDiscovery.loadPatterns()">
                        Try Again
                    </button>
                </div>
                
                <!-- Main Content -->
                
                <!-- Results Section -->
                <div class="row">
                    <!-- Results -->
                    <div class="col-12">
                        <div class="card h-100">
                            <div class="card-header bg-white border-bottom">
                                <div class="d-flex justify-content-between align-items-center">
                                    <h5 class="card-title mb-0">
                                        <i class="fas fa-table me-2"></i>
                                        Pattern Results
                                        <small class="text-muted ms-2" id="live-indicator">Live Data</small>
                                    </h5>
                                    <!-- Sprint 24: Export Controls -->
                                    <div class="btn-group" role="group" aria-label="Export options">
                                        <button class="btn btn-sm btn-outline-success" id="export-csv-btn" 
                                                title="Export results to CSV">
                                            <i class="fas fa-file-csv me-1"></i>CSV
                                        </button>
                                        <button class="btn btn-sm btn-outline-danger" id="export-pdf-btn" 
                                                title="Export results to PDF">
                                            <i class="fas fa-file-pdf me-1"></i>PDF
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <div class="card-body p-0">
                                <div id="loading-spinner" class="d-flex align-items-center justify-content-center py-5 d-none">
                                    <div class="spinner-border text-primary me-3" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                    <div class="text-muted">Loading pattern data...</div>
                                </div>
                                
                                <div id="no-patterns" class="text-center py-5 d-none">
                                    <i class="fas fa-search fa-3x mb-3 text-secondary"></i>
                                    <h5>No patterns found</h5>
                                    <p class="text-muted">Try adjusting your filters to find more patterns.</p>
                                </div>
                                
                                <div id="pattern-table-container">
                                    <table id="pattern-table" class="table table-striped table-hover mb-0">
                                        <thead class="sticky-top">
                                            <tr>
                                                <th class="sortable text-center" data-sort="symbol" style="cursor: pointer; width: 8%;">
                                                    Symbol <i class="fas fa-sort text-muted ms-1" id="sort-symbol"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="pattern" style="cursor: pointer; width: 10%;">
                                                    Pattern <i class="fas fa-sort text-muted ms-1" id="sort-pattern"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="confidence" style="cursor: pointer; width: 10%;">
                                                    Confidence <i class="fas fa-sort text-muted ms-1" id="sort-confidence"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="price" style="cursor: pointer; width: 8%;">
                                                    Price <i class="fas fa-sort text-muted ms-1" id="sort-price"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="change" style="cursor: pointer; width: 8%;">
                                                    Change <i class="fas fa-sort text-muted ms-1" id="sort-change"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="rs" style="cursor: pointer; width: 6%;">
                                                    RS <i class="fas fa-sort text-muted ms-1" id="sort-rs"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="volume" style="cursor: pointer; width: 8%;">
                                                    Volume <i class="fas fa-sort text-muted ms-1" id="sort-volume"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="trend" style="cursor: pointer; width: 12%;">
                                                    Trend Momentum <i class="fas fa-sort text-muted ms-1" id="sort-trend"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="context" style="cursor: pointer; width: 10%;">
                                                    Context <i class="fas fa-sort text-muted ms-1" id="sort-context"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="performance" style="cursor: pointer; width: 10%;">
                                                    Performance <i class="fas fa-sort text-muted ms-1" id="sort-performance"></i>
                                                </th>
                                                <th class="sortable text-center" data-sort="timestamp" style="cursor: pointer; width: 8%;">
                                                    Detected <i class="fas fa-sort text-muted ms-1" id="sort-timestamp"></i>
                                                </th>
                                                <th style="width: 12%;">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="pattern-table-body">
                                            <!-- Pattern data will be rendered here -->
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Hidden pattern analytics panel for service initialization -->
                <div id="pattern-analytics-panel" style="display: none;">
                    <!-- PatternAnalyticsService will render here but remain hidden -->
                </div>
                
                <!-- Sprint 24: Stock Chart Modal -->
                <div class="modal fade" id="stockChartModal" tabindex="-1" aria-labelledby="stockChartModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="stockChartModalLabel">
                                    <i class="fas fa-chart-line me-2"></i>
                                    <span id="chart-symbol">Stock</span> Chart & Analysis
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <!-- Chart Controls -->
                                <div class="row mb-3">
                                    <div class="col-md-8">
                                        <div class="btn-group chart-timeframe-buttons" role="group" aria-label="Chart timeframe">
                                            <input type="radio" class="btn-check" name="chartTimeframe" id="chart-1d" value="1d" checked>
                                            <label class="btn btn-outline-primary btn-sm" for="chart-1d">1D</label>
                                            
                                            <input type="radio" class="btn-check" name="chartTimeframe" id="chart-5d" value="5d">
                                            <label class="btn btn-outline-primary btn-sm" for="chart-5d">5D</label>
                                            
                                            <input type="radio" class="btn-check" name="chartTimeframe" id="chart-1m" value="1m">
                                            <label class="btn btn-outline-primary btn-sm" for="chart-1m">1M</label>
                                            
                                            <input type="radio" class="btn-check" name="chartTimeframe" id="chart-3m" value="3m">
                                            <label class="btn btn-outline-primary btn-sm" for="chart-3m">3M</label>
                                            
                                            <input type="radio" class="btn-check" name="chartTimeframe" id="chart-1y" value="1y">
                                            <label class="btn btn-outline-primary btn-sm" for="chart-1y">1Y</label>
                                        </div>
                                    </div>
                                    <div class="col-md-4 text-end">
                                        <div class="btn-group" role="group">
                                            <button class="btn btn-sm btn-outline-info" id="refresh-chart-btn" title="Refresh chart data">
                                                <i class="fas fa-sync-alt"></i>
                                            </button>
                                            <button class="btn btn-sm btn-outline-secondary" id="export-chart-btn" title="Export chart">
                                                <i class="fas fa-download"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Stock Info Panel -->
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <div class="card border-0 bg-light">
                                            <div class="card-body py-2">
                                                <div class="row text-center">
                                                    <div class="col-3">
                                                        <div class="h6 mb-0" id="current-price">$0.00</div>
                                                        <small class="text-muted">Price</small>
                                                    </div>
                                                    <div class="col-3">
                                                        <div class="h6 mb-0" id="price-change">+0.00%</div>
                                                        <small class="text-muted">Change</small>
                                                    </div>
                                                    <div class="col-3">
                                                        <div class="h6 mb-0" id="chart-volume">0</div>
                                                        <small class="text-muted">Volume</small>
                                                    </div>
                                                    <div class="col-3">
                                                        <div class="h6 mb-0" id="pattern-confidence">0%</div>
                                                        <small class="text-muted">Pattern</small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="alert alert-info py-2 mb-0">
                                            <i class="fas fa-info-circle me-2"></i>
                                            Pattern: <strong id="detected-pattern">Unknown</strong> detected
                                            <div class="small text-muted mt-1" id="pattern-description">
                                                Real-time pattern analysis with price and volume indicators.
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Chart Loading -->
                                <div id="chart-loading" class="d-flex align-items-center justify-content-center py-5">
                                    <div class="spinner-border text-primary me-3" role="status">
                                        <span class="visually-hidden">Loading chart...</span>
                                    </div>
                                    <div class="text-muted">Loading chart data...</div>
                                </div>
                                
                                <!-- Price Chart -->
                                <div id="chart-container" style="display: none;">
                                    <canvas id="priceChart" width="800" height="400"></canvas>
                                </div>
                                
                                <!-- Volume Chart -->
                                <div id="volume-chart-container" class="mt-3" style="display: none;">
                                    <canvas id="volumeChart" width="800" height="150"></canvas>
                                </div>
                                
                                <!-- Chart Error -->
                                <div id="chart-error" class="alert alert-warning" style="display: none;">
                                    <i class="fas fa-exclamation-triangle me-2"></i>
                                    <span id="chart-error-message">Unable to load chart data</span>
                                    <button class="btn btn-sm btn-outline-warning ms-2" onclick="patternDiscovery.retryChart()">
                                        Try Again
                                    </button>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Close</button>
                                <button type="button" class="btn btn-primary" id="add-to-watchlist-from-chart">
                                    <i class="fas fa-star me-1"></i>Add to Watchlist
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Sprint 24: Pattern Performance History Modal -->
                <div class="modal fade" id="performanceHistoryModal" tabindex="-1" aria-labelledby="performanceHistoryModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="performanceHistoryModalLabel">
                                    <i class="fas fa-history me-2"></i>
                                    <span id="performance-pattern">Pattern</span> Performance History
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <!-- Performance Summary -->
                                <div class="row mb-4">
                                    <div class="col-md-3 text-center">
                                        <div class="card border-0 bg-primary text-white">
                                            <div class="card-body py-2">
                                                <div class="h4 mb-0" id="overall-success-rate">0%</div>
                                                <small>Overall Success Rate</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3 text-center">
                                        <div class="card border-0 bg-success text-white">
                                            <div class="card-body py-2">
                                                <div class="h4 mb-0" id="total-occurrences">0</div>
                                                <small>Total Occurrences</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3 text-center">
                                        <div class="card border-0 bg-info text-white">
                                            <div class="card-body py-2">
                                                <div class="h4 mb-0" id="avg-return">0%</div>
                                                <small>Average Return</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3 text-center">
                                        <div class="card border-0 bg-warning text-dark">
                                            <div class="card-body py-2">
                                                <div class="h4 mb-0" id="confidence-range">0-0%</div>
                                                <small>Confidence Range</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Time Period Selector -->
                                <div class="mb-3">
                                    <div class="btn-group" role="group" aria-label="Performance time periods">
                                        <input type="radio" class="btn-check" name="performancePeriod" id="perf-7d" value="7d">
                                        <label class="btn btn-outline-primary btn-sm" for="perf-7d">7 Days</label>
                                        
                                        <input type="radio" class="btn-check" name="performancePeriod" id="perf-30d" value="30d" checked>
                                        <label class="btn btn-outline-primary btn-sm" for="perf-30d">30 Days</label>
                                        
                                        <input type="radio" class="btn-check" name="performancePeriod" id="perf-90d" value="90d">
                                        <label class="btn btn-outline-primary btn-sm" for="perf-90d">90 Days</label>
                                        
                                        <input type="radio" class="btn-check" name="performancePeriod" id="perf-1y" value="1y">
                                        <label class="btn btn-outline-primary btn-sm" for="perf-1y">1 Year</label>
                                    </div>
                                </div>
                                
                                <!-- Performance Loading -->
                                <div id="performance-loading" class="d-flex align-items-center justify-content-center py-4">
                                    <div class="spinner-border text-primary me-3" role="status">
                                        <span class="visually-hidden">Loading performance data...</span>
                                    </div>
                                    <div class="text-muted">Loading performance history...</div>
                                </div>
                                
                                <!-- Performance Charts -->
                                <div id="performance-charts" style="display: none;">
                                    <!-- Success Rate Trend Chart -->
                                    <div class="mb-4">
                                        <h6>Success Rate Trend</h6>
                                        <canvas id="successRateChart" width="600" height="200"></canvas>
                                    </div>
                                    
                                    <!-- Return Distribution Chart -->
                                    <div class="mb-4">
                                        <h6>Return Distribution</h6>
                                        <canvas id="returnDistributionChart" width="600" height="200"></canvas>
                                    </div>
                                </div>
                                
                                <!-- Performance Table -->
                                <div id="performance-table-container" style="display: none;">
                                    <h6>Recent Performance History</h6>
                                    <div class="table-responsive">
                                        <table class="table table-sm table-striped">
                                            <thead>
                                                <tr>
                                                    <th>Date</th>
                                                    <th>Symbol</th>
                                                    <th>Confidence</th>
                                                    <th>Result</th>
                                                    <th>Return %</th>
                                                    <th>Days Held</th>
                                                </tr>
                                            </thead>
                                            <tbody id="performance-table-body">
                                                <!-- Performance history rows -->
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                                
                                <!-- Performance Error -->
                                <div id="performance-error" class="alert alert-warning" style="display: none;">
                                    <i class="fas fa-exclamation-triangle me-2"></i>
                                    <span id="performance-error-message">Unable to load performance data</span>
                                    <button class="btn btn-sm btn-outline-warning ms-2" onclick="patternDiscovery.retryPerformanceLoad()">
                                        Try Again
                                    </button>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Close</button>
                                <button type="button" class="btn btn-primary" id="export-performance-btn">
                                    <i class="fas fa-download me-1"></i>Export Data
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Sprint 24: Pattern Alert Creation Modal -->
                <div class="modal fade" id="createAlertModal" tabindex="-1" aria-labelledby="createAlertModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="createAlertModalLabel">
                                    <i class="fas fa-bell me-2"></i>
                                    Create Pattern Alert
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <!-- Alert Configuration Form -->
                                <form id="alert-form">
                                    <div class="row">
                                        <!-- Left Column: Basic Settings -->
                                        <div class="col-md-6">
                                            <div class="mb-3">
                                                <label for="alert-name" class="form-label">Alert Name</label>
                                                <input type="text" class="form-control" id="alert-name" 
                                                       placeholder="My Pattern Alert" required>
                                                <small class="form-text text-muted">Give your alert a descriptive name</small>
                                            </div>
                                            
                                            <div class="mb-3">
                                                <label for="alert-symbol" class="form-label">Symbol</label>
                                                <input type="text" class="form-control" id="alert-symbol" 
                                                       placeholder="AAPL" readonly>
                                                <small class="form-text text-muted">Stock symbol for this alert</small>
                                            </div>
                                            
                                            <div class="mb-3">
                                                <label for="alert-pattern" class="form-label">Pattern Type</label>
                                                <select class="form-select" id="alert-pattern">
                                                    <option value="">Any Pattern</option>
                                                    <!-- Pattern options will be populated dynamically -->
                                                </select>
                                                <small class="form-text text-muted">Pattern to watch for</small>
                                            </div>
                                        </div>
                                        
                                        <!-- Right Column: Advanced Settings -->
                                        <div class="col-md-6">
                                            <div class="mb-3">
                                                <label for="alert-confidence" class="form-label">
                                                    Minimum Confidence: <span id="alert-confidence-value">70%</span>
                                                </label>
                                                <input type="range" class="form-range" id="alert-confidence" 
                                                       min="0.1" max="1.0" step="0.05" value="0.7">
                                                <small class="form-text text-muted">Trigger only when confidence is above this level</small>
                                            </div>
                                            
                                            <div class="mb-3">
                                                <label for="alert-frequency" class="form-label">Alert Frequency</label>
                                                <select class="form-select" id="alert-frequency">
                                                    <option value="realtime">Real-time</option>
                                                    <option value="daily" selected>Daily Summary</option>
                                                    <option value="weekly">Weekly Summary</option>
                                                </select>
                                                <small class="form-text text-muted">How often to receive alerts</small>
                                            </div>
                                            
                                            <div class="mb-3">
                                                <label for="alert-channels" class="form-label">Notification Channels</label>
                                                <div class="form-check">
                                                    <input class="form-check-input" type="checkbox" id="alert-email" checked>
                                                    <label class="form-check-label" for="alert-email">
                                                        <i class="fas fa-envelope me-1"></i>Email
                                                    </label>
                                                </div>
                                                <div class="form-check">
                                                    <input class="form-check-input" type="checkbox" id="alert-browser">
                                                    <label class="form-check-label" for="alert-browser">
                                                        <i class="fas fa-bell me-1"></i>Browser Notification
                                                    </label>
                                                </div>
                                                <div class="form-check">
                                                    <input class="form-check-input" type="checkbox" id="alert-webhook">
                                                    <label class="form-check-label" for="alert-webhook">
                                                        <i class="fas fa-link me-1"></i>Webhook
                                                    </label>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <!-- Advanced Options -->
                                    <div class="row mt-3">
                                        <div class="col-12">
                                            <h6>Advanced Options</h6>
                                            <div class="row">
                                                <div class="col-md-6">
                                                    <div class="form-check">
                                                        <input class="form-check-input" type="checkbox" id="alert-active-hours">
                                                        <label class="form-check-label" for="alert-active-hours">
                                                            Only during market hours
                                                        </label>
                                                    </div>
                                                    <div class="form-check">
                                                        <input class="form-check-input" type="checkbox" id="alert-volume-filter">
                                                        <label class="form-check-label" for="alert-volume-filter">
                                                            High volume patterns only
                                                        </label>
                                                    </div>
                                                </div>
                                                <div class="col-md-6">
                                                    <div class="mb-3">
                                                        <label for="alert-expiry" class="form-label">Alert Expiry</label>
                                                        <select class="form-select" id="alert-expiry">
                                                            <option value="never">Never</option>
                                                            <option value="1day">1 Day</option>
                                                            <option value="1week">1 Week</option>
                                                            <option value="1month" selected>1 Month</option>
                                                            <option value="3months">3 Months</option>
                                                        </select>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </form>
                                
                                <!-- Alert Preview -->
                                <div class="mt-4">
                                    <h6>Alert Preview</h6>
                                    <div class="card bg-light">
                                        <div class="card-body">
                                            <div id="alert-preview" class="text-muted">
                                                Configure your alert settings above to see a preview.
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-warning" id="save-alert-btn">
                                    <i class="fas fa-bell me-1"></i>Create Alert
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.renderFilters();
        this.setupEventHandlers();
        
        // Setup retractable filter after DOM is ready (only for old system)
        setTimeout(() => {
            const sidebarSystem = window.sidebarNavigation;
            if (!sidebarSystem) {
                this.setupRetractableFilter();
            } else {
            }
        }, 200);
        
        // Setup pattern type filtering after rendering
        setTimeout(() => {
            this.setupPatternTypeFiltering();
            this.setupChartEventHandlers();
            this.setupTableSorting();
        }, 300);
        
        // Initialize Watchlist and Filter Preset Services
        setTimeout(() => {
            if (window.WatchlistManager && !window.watchlistManager) {
                window.watchlistManager = new WatchlistManager();
            }
            if (window.FilterPresetsService && !window.filterPresets) {
                window.filterPresets = new FilterPresetsService();
            }
        }, 200);
    }
    
    renderFilters() {
        const filtersContainer = document.querySelector('#filters-content .p-3');
        if (!filtersContainer) return;
        
        filtersContainer.innerHTML = `
            <!-- Universe Selection -->
            <div class="mb-3">
                <label class="form-label">Stock Universe</label>
                <select id="universe-filter" class="form-select">
                    <option value="sp500">S&P 500</option>
                    <option value="nasdaq100">NASDAQ 100</option>
                    <option value="russell2000">Russell 2000</option>
                    <option value="all">All Symbols</option>
                </select>
            </div>
            
            <!-- Sprint 24: Advanced Symbol Search -->
            <div class="mb-3">
                <label class="form-label">Symbol Search</label>
                <div class="position-relative">
                    <input type="text" class="form-control" id="symbol-search" 
                           placeholder="Search symbols (e.g., AAPL, GOOGL)" 
                           autocomplete="off">
                    <div class="position-absolute w-100" style="z-index: 1000;">
                        <div id="symbol-suggestions" class="list-group d-none shadow-sm border">
                            <!-- Autocomplete suggestions will appear here -->
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <div id="selected-symbols" class="d-flex flex-wrap gap-1">
                        <!-- Selected symbol badges will appear here -->
                    </div>
                </div>
                <small class="form-text text-muted">
                    Search and select specific symbols to filter results. Leave empty to show all.
                </small>
            </div>
            
            <!-- Sprint 24: Sector Filtering -->
            <div class="mb-3">
                <label class="form-label">Sector Filter</label>
                <select id="sector-filter" class="form-select">
                    <option value="all">All Sectors</option>
                    <option value="technology">Technology</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="financials">Financials</option>
                    <option value="consumer-discretionary">Consumer Discretionary</option>
                    <option value="consumer-staples">Consumer Staples</option>
                    <option value="energy">Energy</option>
                    <option value="utilities">Utilities</option>
                    <option value="industrials">Industrials</option>
                    <option value="materials">Materials</option>
                    <option value="real-estate">Real Estate</option>
                    <option value="communication">Communication Services</option>
                </select>
            </div>
            
            <!-- Confidence Range -->
            <div class="mb-3">
                <label class="form-label">Min Confidence</label>
                <input type="range" class="form-range" id="confidence-filter" 
                       min="0" max="1" step="0.1" value="0.7">
                <div class="d-flex justify-content-between text-muted small">
                    <span>0%</span>
                    <span id="confidence-value">70%</span>
                    <span>100%</span>
                </div>
            </div>
            
            <!-- Pattern Types -->
            <div class="mb-3">
                <label class="form-label">Pattern Types</label>
                <div id="pattern-types">
                    <!-- Pattern checkboxes will be rendered here -->
                </div>
            </div>
            
            <!-- Results Limit -->
            <div class="mb-3">
                <label class="form-label">Results Limit</label>
                <select id="limit-filter" class="form-select">
                    <option value="50">50 results</option>
                    <option value="100" selected>100 results</option>
                    <option value="200">200 results</option>
                </select>
            </div>
            
            <button class="btn btn-secondary w-100" onclick="patternDiscovery.clearFilters()">
                Clear All Filters
            </button>
        `;
        
        this.renderPatternTypes();
        this.setupFilterHandlers();
        
        // Setup collapsible filters (delay to ensure DOM is ready)
        setTimeout(() => {
            this.setupCollapsibleFilters();
        }, 100);
    }
    
    renderPatternTypes() {
        const patternTypes = this.availablePatterns;
        const container = document.getElementById('pattern-types');
        
        if (container) {
            container.innerHTML = patternTypes.map(pattern => `
                <div class="form-check">
                    <input class="form-check-input pattern-type-filter" type="checkbox" value="${pattern}" id="pattern-${pattern}">
                    <label class="form-check-label" for="pattern-${pattern}">
                        ${pattern}
                    </label>
                </div>
            `).join('');
        }
    }
    
    setupEventHandlers() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadPatterns());
        }
        
        
        // Sprint 24: Export functionality
        const exportCsvBtn = document.getElementById('export-csv-btn');
        if (exportCsvBtn) {
            exportCsvBtn.addEventListener('click', () => this.exportToCSV());
        }
        
        const exportPdfBtn = document.getElementById('export-pdf-btn');
        if (exportPdfBtn) {
            exportPdfBtn.addEventListener('click', () => this.exportToPDF());
        }
    }
    
    /**
     * Setup retractable filter system with clean architecture
     */
    setupRetractableFilter() {
        // Verify the container exists before initializing
        const container = document.getElementById('pattern-discovery-dashboard');
        if (!container) {
            console.error('Pattern Discovery Dashboard container not found, retrying...');
            setTimeout(() => {
                this.setupRetractableFilter();
            }, 300);
            return;
        }
        
        
        // Initialize the retractable filter controller
        this.filterController = new RetractableFilterController('pattern-discovery-dashboard', {
            initiallyCollapsed: false,
            rememberState: true,
            storageKey: 'pattern-discovery-filters',
            onToggle: (isCollapsed) => {
            }
        });
        
        // Set up the content after controller is ready
        setTimeout(() => {
            this.setupFilterControllerContent();
        }, 100);
    }
    
    /**
     * Setup content within the retractable filter controller
     */
    setupFilterControllerContent() {
        if (!this.filterController) {
            console.error('Filter controller not initialized');
            return;
        }
        
        
        try {
            // Create filter content
            const filterContent = this.createFilterContent();
            this.filterController.setFilterContent(filterContent);
            
            // Create main content (the existing pattern discovery content without filters)
            const mainContent = this.createMainContent();
            this.filterController.setMainContent(mainContent);
            
            // Update filter count when filters change
            this.updateFilterCount();
            
            // Setup collapsible filter sections
            this.setupCollapsibleFilters();
            
        } catch (error) {
            console.error('Error setting up filter controller content:', error);
        }
    }
    
    /**
     * Create the filter panel content
     */
    createFilterContent() {
        return `
            <!-- Watchlist Panel Container -->
            <div id="watchlist-panel" class="filter-section mb-3">
                <div class="filter-section-header collapsible-header" data-target="watchlist-content">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-chevron-right collapse-caret me-2"></i>
                        <i class="fas fa-star me-2 text-primary"></i>
                        <h6 class="mb-0 filter-section-title">Watchlists</h6>
                    </div>
                </div>
                <div id="watchlist-content" class="filter-section-content collapse">
                    <div class="p-3 border-top">
                        <!-- Watchlist management will be rendered here -->
                        <div class="text-center text-muted py-2">
                            <div class="spinner-border spinner-border-sm me-2" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            Loading watchlists...
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Filter Presets Panel Container -->
            <div id="filter-presets-panel" class="filter-section mb-3">
                <div class="filter-section-header collapsible-header" data-target="presets-content">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-chevron-right collapse-caret me-2"></i>
                        <i class="fas fa-bookmark me-2 text-primary"></i>
                        <h6 class="mb-0 filter-section-title">Presets</h6>
                    </div>
                </div>
                <div id="presets-content" class="filter-section-content collapse">
                    <div class="p-3 border-top">
                        <!-- Filter presets will be rendered here -->
                        <div class="text-center text-muted py-2">
                            <div class="spinner-border spinner-border-sm me-2" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            Loading presets...
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Main Filters Panel Container -->
            <div id="pattern-filters" class="filter-section mb-3">
                <div class="filter-section-header collapsible-header" data-target="filters-content">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-chevron-down collapse-caret me-2"></i>
                        <i class="fas fa-sliders-h me-2 text-primary"></i>
                        <h6 class="mb-0 filter-section-title">Filter Options</h6>
                    </div>
                </div>
                <div id="filters-content" class="filter-section-content collapse show">
                    <div class="p-3 border-top">
                        <!-- Main filters will be rendered here -->
                    </div>
                </div>
            </div>
            
            <!-- Apply Filters Button -->
            <div class="filter-section">
                <div class="p-3">
                    <button id="apply-filters-btn" class="btn btn-primary w-100">
                        <i class="fas fa-check me-2"></i>
                        Apply Filters
                    </button>
                    <button id="clear-filters-btn" class="btn btn-outline-secondary w-100 mt-2">
                        <i class="fas fa-times me-2"></i>
                        Clear All
                    </button>
                </div>
            </div>
        `;
    }
    
    /**
     * Create the main content area
     */
    createMainContent() {
        return `
            <!-- Header -->
            <div class="d-flex justify-content-between align-items-center mb-4 p-3 rounded" style="background-color: var(--color-background-secondary); border: 1px solid var(--color-border-primary);">
                <div class="d-flex align-items-center">
                    <h2 class="h4 mb-0 text-primary me-3">
                        <i class="fas fa-chart-line me-2"></i>
                        Pattern Discovery Dashboard
                    </h2>
                    <span id="ws-status" class="badge bg-secondary">Connecting...</span>
                </div>
                
                <div class="d-flex align-items-center">
                    <button id="refresh-btn" class="btn btn-outline-primary btn-sm me-2">
                        <i class="fas fa-sync-alt me-1"></i>
                        Refresh
                    </button>
                    <span id="pattern-count" class="badge bg-info">0 patterns</span>
                </div>
            </div>
            
            <!-- Error Display -->
            <div id="error-display" class="alert alert-danger d-none" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <span id="error-message"></span>
                <button class="btn btn-sm btn-outline-danger ms-2" onclick="patternDiscovery.loadPatterns()">
                    Try Again
                </button>
            </div>
            
            <!-- Results Section -->
            <div id="results-section">
                <div id="results-loading" class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading patterns...</span>
                    </div>
                    <div class="mt-3 text-muted">Scanning for patterns...</div>
                </div>
                
                <div id="results-content" style="display: none;">
                    <!-- Pattern Results Table -->
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">Pattern Results</h5>
                            <div class="d-flex align-items-center">
                                <span class="badge bg-info me-2" id="results-count">0 patterns</span>
                                <div class="btn-group" role="group">
                                    <button id="export-csv-btn" class="btn btn-sm btn-outline-primary">
                                        <i class="fas fa-file-csv me-1"></i>
                                        CSV
                                    </button>
                                    <button id="export-pdf-btn" class="btn btn-sm btn-outline-primary">
                                        <i class="fas fa-file-pdf me-1"></i>
                                        PDF
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-hover mb-0" id="pattern-table">
                                    <thead>
                                        <tr>
                                            <th class="sortable text-center" data-sort="symbol" style="width: 8%;">Symbol <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="pattern" style="width: 10%;">Pattern <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="confidence" style="width: 10%;">Confidence <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="price" style="width: 8%;">Price <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="change" style="width: 8%;">Change <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="rs" style="width: 6%;">RS <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="volume" style="width: 8%;">Volume <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="trend" style="width: 12%;">Trend Momentum <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="context" style="width: 10%;">Context <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="performance" style="width: 10%;">Performance <i class="fas fa-sort"></i></th>
                                            <th class="sortable text-center" data-sort="detected" style="width: 8%;">Detected <i class="fas fa-sort"></i></th>
                                            <th style="width: 12%;">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="pattern-table-body">
                                        <!-- Pattern rows will be inserted here -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Chart Modal -->
            <div class="modal fade" id="chartModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Stock Chart</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <canvas id="stock-chart" width="800" height="400"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Alert Creation Modal -->
            <div class="modal fade" id="alertModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Create Pattern Alert</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="alert-form">
                                <div class="mb-3">
                                    <label class="form-label">Alert Name</label>
                                    <input type="text" class="form-control" id="alert-name" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Symbol</label>
                                    <input type="text" class="form-control" id="alert-symbol" readonly>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Pattern</label>
                                    <input type="text" class="form-control" id="alert-pattern" readonly>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Minimum Confidence</label>
                                    <input type="range" class="form-range" id="alert-confidence" min="0.5" max="1" step="0.01" value="0.7">
                                    <div class="text-muted"><span id="alert-confidence-value">70%</span></div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="save-alert-btn">Create Alert</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Update filter count in the controller
     */
    updateFilterCount() {
        if (!this.filterController) return;
        
        let activeFilters = 0;
        
        // Count active filters
        if (this.filters.pattern_types && this.filters.pattern_types.length > 0) {
            activeFilters += this.filters.pattern_types.length;
        }
        if (this.filters.symbols && this.filters.symbols.length > 0) {
            activeFilters += this.filters.symbols.length;
        }
        if (this.filters.sector && this.filters.sector !== 'all') {
            activeFilters += 1;
        }
        if (this.filters.confidence_min > 0.7) {
            activeFilters += 1;
        }
        
        this.filterController.updateFilterCount(activeFilters);
    }
    
    /**
     * Legacy method - now redirects to retractable filter system
     */
    setupFilterPanelHandlers() {
        // The new retractable filter controller handles all panel functionality
    }
    
    /**
     * Sprint 24: Setup dynamic pattern type filtering with event listeners
     */
    setupPatternTypeFiltering() {
        // Add selected pattern types to filters
        if (!this.filters.pattern_types) {
            this.filters.pattern_types = [];
        }
        
        // Get all pattern type checkboxes (dynamically created)
        const patternCheckboxes = document.querySelectorAll('.pattern-type-filter');
        
        patternCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const patternType = e.target.value;
                const isChecked = e.target.checked;
                
                if (isChecked) {
                    // Add pattern type to filter (avoid duplicates)
                    if (!this.filters.pattern_types.includes(patternType)) {
                        this.filters.pattern_types.push(patternType);
                    }
                } else {
                    // Remove pattern type from filter
                    const index = this.filters.pattern_types.indexOf(patternType);
                    if (index > -1) {
                        this.filters.pattern_types.splice(index, 1);
                    }
                }
                
                // Apply filtering immediately
                this.applyPatternTypeFilter();
                
                // Show feedback
                const activeCount = this.filters.pattern_types.length;
                const totalCount = this.availablePatterns.length;
                
                if (activeCount === 0) {
                    this.showNotification('All pattern types enabled', 'info');
                } else if (activeCount === totalCount) {
                    this.showNotification('All pattern types enabled', 'info');
                } else {
                    this.showNotification(`${activeCount} of ${totalCount} pattern types selected`, 'info');
                }
            });
        });
        
        // Add "Select All" and "Clear All" functionality
        this.addPatternTypeControls();
        
    }
    
    /**
     * Sprint 24: Add Select All / Clear All controls for pattern types
     */
    addPatternTypeControls() {
        const patternTypesContainer = document.getElementById('pattern-types');
        if (!patternTypesContainer) return;
        
        // Create control buttons container
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'd-flex gap-2 mt-2 pattern-type-controls';
        controlsDiv.innerHTML = `
            <button type="button" class="btn btn-sm btn-outline-primary flex-fill" id="select-all-patterns">
                <i class="fas fa-check-double me-1"></i>All
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary flex-fill" id="clear-all-patterns">
                <i class="fas fa-times me-1"></i>None
            </button>
        `;
        
        // Insert after pattern checkboxes
        patternTypesContainer.appendChild(controlsDiv);
        
        // Add event listeners
        const selectAllBtn = document.getElementById('select-all-patterns');
        const clearAllBtn = document.getElementById('clear-all-patterns');
        
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                const checkboxes = document.querySelectorAll('.pattern-type-filter');
                checkboxes.forEach(cb => {
                    cb.checked = true;
                    cb.dispatchEvent(new Event('change'));
                });
            });
        }
        
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => {
                const checkboxes = document.querySelectorAll('.pattern-type-filter');
                checkboxes.forEach(cb => {
                    cb.checked = false;
                    cb.dispatchEvent(new Event('change'));
                });
            });
        }
    }
    
    /**
     * Sprint 24: Apply pattern type filtering to displayed results
     */
    applyPatternTypeFilter() {
        const displayedPatterns = this.getPatternsForDisplay();
        
        // If no pattern types selected, show all patterns
        if (!this.filters.pattern_types || this.filters.pattern_types.length === 0) {
            this.filteredPatterns = null; // Show all patterns
        } else {
            // Filter patterns by selected types
            this.filteredPatterns = displayedPatterns.filter(pattern => 
                this.filters.pattern_types.includes(pattern.pattern)
            );
        }
        
        // Re-render patterns and update count
        this.renderPatterns();
        this.updatePatternCount();
        
        // Update visual feedback
        this.updatePatternTypeVisualFeedback();
    }
    
    /**
     * Sprint 24: Update visual feedback for pattern type filtering
     */
    updatePatternTypeVisualFeedback() {
        const activeFilters = this.filters.pattern_types || [];
        const patternTypeControls = document.querySelector('.pattern-type-controls');
        
        if (patternTypeControls) {
            const selectAllBtn = document.getElementById('select-all-patterns');
            const clearAllBtn = document.getElementById('clear-all-patterns');
            
            if (activeFilters.length === 0) {
                // No filters active - show all
                if (selectAllBtn) selectAllBtn.classList.add('btn-primary');
                if (selectAllBtn) selectAllBtn.classList.remove('btn-outline-primary');
                if (clearAllBtn) clearAllBtn.classList.remove('btn-secondary');
                if (clearAllBtn) clearAllBtn.classList.add('btn-outline-secondary');
            } else if (activeFilters.length === this.availablePatterns.length) {
                // All patterns selected
                if (selectAllBtn) selectAllBtn.classList.add('btn-primary');
                if (selectAllBtn) selectAllBtn.classList.remove('btn-outline-primary');
                if (clearAllBtn) clearAllBtn.classList.remove('btn-secondary');
                if (clearAllBtn) clearAllBtn.classList.add('btn-outline-secondary');
            } else {
                // Some patterns selected
                if (selectAllBtn) selectAllBtn.classList.remove('btn-primary');
                if (selectAllBtn) selectAllBtn.classList.add('btn-outline-primary');
                if (clearAllBtn) clearAllBtn.classList.add('btn-secondary');
                if (clearAllBtn) clearAllBtn.classList.remove('btn-outline-secondary');
            }
        }
    }
    
    /**
     * Sprint 24: Setup chart event handlers for stock chart display
     */
    setupChartEventHandlers() {
        // Initialize chart variables
        this.currentChart = null;
        this.currentVolumeChart = null;
        this.currentSymbol = null;
        this.currentTimeframe = '1d';
        
        // Chart button click handler (delegated to handle dynamic content)
        document.addEventListener('click', (e) => {
            if (e.target.closest('.chart-btn')) {
                const button = e.target.closest('.chart-btn');
                const symbol = button.dataset.symbol;
                const pattern = button.dataset.pattern;
                const price = button.dataset.price;
                
                this.openStockChart(symbol, pattern, price);
            }
            
            // Performance history button handler
            if (e.target.closest('.performance-history-btn')) {
                const button = e.target.closest('.performance-history-btn');
                const symbol = button.dataset.symbol;
                const pattern = button.dataset.pattern;
                
                this.openPerformanceHistory(symbol, pattern);
            }
            
            // Sprint 24: Create alert button handler
            if (e.target.closest('.create-alert-btn')) {
                const button = e.target.closest('.create-alert-btn');
                const symbol = button.dataset.symbol;
                const pattern = button.dataset.pattern;
                const confidence = parseFloat(button.dataset.confidence);
                
                this.openCreateAlert(symbol, pattern, confidence);
            }
        });
        
        // Timeframe button handlers
        const timeframeButtons = document.querySelectorAll('input[name="chartTimeframe"]');
        timeframeButtons.forEach(button => {
            button.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.currentTimeframe = e.target.value;
                    if (this.currentSymbol) {
                        this.loadChartData(this.currentSymbol, this.currentTimeframe);
                    }
                }
            });
        });
        
        // Chart control handlers
        const refreshChartBtn = document.getElementById('refresh-chart-btn');
        if (refreshChartBtn) {
            refreshChartBtn.addEventListener('click', () => {
                if (this.currentSymbol) {
                    this.loadChartData(this.currentSymbol, this.currentTimeframe);
                }
            });
        }
        
        const exportChartBtn = document.getElementById('export-chart-btn');
        if (exportChartBtn) {
            exportChartBtn.addEventListener('click', () => {
                this.exportChart();
            });
        }
        
        // Modal event handlers
        const chartModal = document.getElementById('stockChartModal');
        if (chartModal) {
            chartModal.addEventListener('hidden.bs.modal', () => {
                this.cleanupCharts();
            });
        }
        
    }
    
    /**
     * Sprint 24: Open stock chart modal and load data
     */
    async openStockChart(symbol, pattern, price) {
        try {
            this.currentSymbol = symbol;
            
            // Update modal title and info
            const chartSymbolElement = document.getElementById('chart-symbol');
            const detectedPatternElement = document.getElementById('detected-pattern');
            const currentPriceElement = document.getElementById('current-price');
            
            if (chartSymbolElement) chartSymbolElement.textContent = symbol;
            if (detectedPatternElement) detectedPatternElement.textContent = pattern;
            if (currentPriceElement) currentPriceElement.textContent = `$${price}`;
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('stockChartModal'));
            modal.show();
            
            // Load chart data
            await this.loadChartData(symbol, this.currentTimeframe);
            
        } catch (error) {
            console.error('Error opening stock chart:', error);
            this.showNotification('Failed to open chart', 'error');
        }
    }
    
    /**
     * Sprint 24: Load chart data for symbol and timeframe
     */
    async loadChartData(symbol, timeframe) {
        const loadingElement = document.getElementById('chart-loading');
        const chartContainer = document.getElementById('chart-container');
        const volumeContainer = document.getElementById('volume-chart-container');
        const errorElement = document.getElementById('chart-error');
        
        try {
            // Show loading state
            if (loadingElement) loadingElement.style.display = 'flex';
            if (chartContainer) chartContainer.style.display = 'none';
            if (volumeContainer) volumeContainer.style.display = 'none';
            if (errorElement) errorElement.style.display = 'none';
            
            // Try to fetch real data first
            let chartData;
            try {
                const response = await fetch(`/api/stocks/chart/${symbol}?timeframe=${timeframe}`);
                if (response.ok) {
                    chartData = await response.json();
                } else {
                    throw new Error('API not available');
                }
            } catch (apiError) {
                // ⚠️ CRITICAL TECHNICAL DEBT - REMOVE BEFORE PRODUCTION ⚠️
                // Fallback to mock data
                chartData = this.generateMockChartData(symbol, timeframe);
            }
            
            // Create charts
            await this.createPriceChart(chartData);
            await this.createVolumeChart(chartData);
            
            // Update stock info
            this.updateStockInfo(chartData);
            
            // Show charts
            if (loadingElement) loadingElement.style.display = 'none';
            if (chartContainer) chartContainer.style.display = 'block';
            if (volumeContainer) volumeContainer.style.display = 'block';
            
        } catch (error) {
            console.error('Error loading chart data:', error);
            
            // Show error state
            if (loadingElement) loadingElement.style.display = 'none';
            if (errorElement) {
                errorElement.style.display = 'block';
                const errorMessage = document.getElementById('chart-error-message');
                if (errorMessage) {
                    errorMessage.textContent = 'Unable to load chart data for ' + symbol;
                }
            }
        }
    }
    
    /**
     * ⚠️ CRITICAL TECHNICAL DEBT - REMOVE BEFORE PRODUCTION ⚠️
     * Sprint 24: Generate mock chart data for development/demo
     * 
     * TODO: Replace with real market data API integration
     * Required: Connect to Polygon.io or existing market data service
     * Impact: All charts show fake data instead of real market prices
     */
    generateMockChartData(symbol, timeframe) {
        const now = new Date();
        const dataPoints = timeframe === '1d' ? 24 : timeframe === '5d' ? 120 : timeframe === '1m' ? 720 : 2160;
        const interval = timeframe === '1d' ? 60 * 60 * 1000 : // 1 hour intervals
                        timeframe === '5d' ? 60 * 60 * 1000 : // 1 hour intervals  
                        60 * 60 * 1000; // 1 hour intervals for all
        
        const basePrice = 100 + Math.random() * 200; // Random base price
        const data = [];
        
        for (let i = dataPoints; i > 0; i--) {
            const time = new Date(now.getTime() - (i * interval));
            const volatility = 0.02; // 2% volatility
            const change = (Math.random() - 0.5) * volatility;
            const price = Math.max(1, basePrice * (1 + change * i / dataPoints));
            
            data.push({
                timestamp: time.toISOString(),
                price: price,
                volume: Math.floor(Math.random() * 1000000) + 100000,
                high: price * (1 + Math.random() * 0.01),
                low: price * (1 - Math.random() * 0.01),
                open: price * (1 + (Math.random() - 0.5) * 0.005),
                close: price
            });
        }
        
        return {
            symbol: symbol,
            timeframe: timeframe,
            data: data,
            currentPrice: data[data.length - 1].price,
            priceChange: data.length > 1 ? 
                ((data[data.length - 1].price - data[0].price) / data[0].price * 100) : 0,
            volume: data[data.length - 1].volume
        };
    }
    
    /**
     * Sprint 24: Create price chart using Chart.js
     */
    async createPriceChart(chartData) {
        const canvas = document.getElementById('priceChart');
        if (!canvas) return;
        
        // Destroy existing chart
        if (this.currentChart) {
            this.currentChart.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        const prices = chartData.data.map(d => d.price);
        const labels = chartData.data.map(d => new Date(d.timestamp).toLocaleDateString());
        
        this.currentChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: `${chartData.symbol} Price`,
                    data: prices,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Price ($)'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                return `Price: $${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                }
            }
        });
    }
    
    /**
     * Sprint 24: Create volume chart using Chart.js
     */
    async createVolumeChart(chartData) {
        const canvas = document.getElementById('volumeChart');
        if (!canvas) return;
        
        // Destroy existing chart
        if (this.currentVolumeChart) {
            this.currentVolumeChart.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        const volumes = chartData.data.map(d => d.volume);
        const labels = chartData.data.map(d => new Date(d.timestamp).toLocaleDateString());
        
        this.currentVolumeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Volume',
                    data: volumes,
                    backgroundColor: 'rgba(32, 201, 151, 0.6)',
                    borderColor: '#20c997',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Volume'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const volume = context.parsed.y;
                                return `Volume: ${volume.toLocaleString()}`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Sprint 24: Update stock info panel with chart data
     */
    updateStockInfo(chartData) {
        const currentPriceElement = document.getElementById('current-price');
        const priceChangeElement = document.getElementById('price-change');
        const chartVolumeElement = document.getElementById('chart-volume');
        
        if (currentPriceElement) {
            currentPriceElement.textContent = `$${chartData.currentPrice.toFixed(2)}`;
        }
        
        if (priceChangeElement) {
            const changeClass = chartData.priceChange >= 0 ? 'text-success' : 'text-danger';
            const changePrefix = chartData.priceChange >= 0 ? '+' : '';
            priceChangeElement.textContent = `${changePrefix}${chartData.priceChange.toFixed(2)}%`;
            priceChangeElement.className = `h6 mb-0 ${changeClass}`;
        }
        
        if (chartVolumeElement) {
            chartVolumeElement.textContent = this.formatVolume(chartData.volume);
        }
    }
    
    /**
     * Sprint 24: Export chart as image
     */
    exportChart() {
        if (this.currentChart && this.currentSymbol) {
            const url = this.currentChart.toBase64Image();
            const link = document.createElement('a');
            link.download = `${this.currentSymbol}_chart.png`;
            link.href = url;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.showNotification(`Chart exported for ${this.currentSymbol}`, 'success');
        }
    }
    
    /**
     * Sprint 24: Retry chart loading
     */
    retryChart() {
        if (this.currentSymbol) {
            this.loadChartData(this.currentSymbol, this.currentTimeframe);
        }
    }
    
    /**
     * Sprint 24: Cleanup charts when modal closes
     */
    cleanupCharts() {
        if (this.currentChart) {
            this.currentChart.destroy();
            this.currentChart = null;
        }
        
        if (this.currentVolumeChart) {
            this.currentVolumeChart.destroy();
            this.currentVolumeChart = null;
        }
        
        this.currentSymbol = null;
    }
    
    /**
     * Sprint 24: Open pattern performance history modal
     */
    async openPerformanceHistory(symbol, pattern) {
        try {
            this.currentPerformancePattern = pattern;
            this.currentPerformanceSymbol = symbol;
            this.currentPerformancePeriod = '30d';
            
            // Update modal title
            const patternElement = document.getElementById('performance-pattern');
            if (patternElement) {
                patternElement.textContent = pattern;
            }
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('performanceHistoryModal'));
            modal.show();
            
            // Setup period change handlers
            this.setupPerformancePeriodHandlers();
            
            // Load performance data
            await this.loadPerformanceHistory(pattern, symbol, this.currentPerformancePeriod);
            
        } catch (error) {
            console.error('Error opening performance history:', error);
            this.showNotification('Failed to open performance history', 'error');
        }
    }
    
    /**
     * Sprint 24: Setup performance period change handlers
     */
    setupPerformancePeriodHandlers() {
        const periodButtons = document.querySelectorAll('input[name="performancePeriod"]');
        periodButtons.forEach(button => {
            button.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.currentPerformancePeriod = e.target.value;
                    if (this.currentPerformancePattern) {
                        this.loadPerformanceHistory(
                            this.currentPerformancePattern, 
                            this.currentPerformanceSymbol, 
                            this.currentPerformancePeriod
                        );
                    }
                }
            });
        });
        
        // Export button handler
        const exportBtn = document.getElementById('export-performance-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportPerformanceData();
            });
        }
    }
    
    /**
     * Sprint 24: Load pattern performance history data
     */
    async loadPerformanceHistory(pattern, symbol, period) {
        const loadingElement = document.getElementById('performance-loading');
        const chartsContainer = document.getElementById('performance-charts');
        const tableContainer = document.getElementById('performance-table-container');
        const errorElement = document.getElementById('performance-error');
        
        try {
            // Show loading state
            if (loadingElement) loadingElement.style.display = 'flex';
            if (chartsContainer) chartsContainer.style.display = 'none';
            if (tableContainer) tableContainer.style.display = 'none';
            if (errorElement) errorElement.style.display = 'none';
            
            // Try to fetch real data first
            let performanceData;
            try {
                const response = await fetch(`/api/patterns/performance/${pattern}?period=${period}&symbol=${symbol}`);
                if (response.ok) {
                    performanceData = await response.json();
                } else {
                    throw new Error('API not available');
                }
            } catch (apiError) {
                // ⚠️ CRITICAL TECHNICAL DEBT - REMOVE BEFORE PRODUCTION ⚠️
                // Fallback to mock data  
                performanceData = this.generateMockPerformanceData(pattern, symbol, period);
            }
            
            // Update performance summary
            this.updatePerformanceSummary(performanceData);
            
            // Create performance charts
            await this.createPerformanceCharts(performanceData);
            
            // Update performance table
            this.updatePerformanceTable(performanceData);
            
            // Show content
            if (loadingElement) loadingElement.style.display = 'none';
            if (chartsContainer) chartsContainer.style.display = 'block';
            if (tableContainer) tableContainer.style.display = 'block';
            
        } catch (error) {
            console.error('Error loading performance history:', error);
            
            // Show error state
            if (loadingElement) loadingElement.style.display = 'none';
            if (errorElement) {
                errorElement.style.display = 'block';
                const errorMessage = document.getElementById('performance-error-message');
                if (errorMessage) {
                    errorMessage.textContent = `Unable to load performance data for ${pattern}`;
                }
            }
        }
    }
    
    /**
     * ⚠️ CRITICAL TECHNICAL DEBT - REMOVE BEFORE PRODUCTION ⚠️
     * Sprint 24: Generate mock performance data for development
     * 
     * TODO: Replace with real TickStockPL pattern analytics integration  
     * Required: Connect to pattern performance database/API
     * Impact: Shows fake success rates instead of real backtesting data
     */
    generateMockPerformanceData(pattern, symbol, period) {
        const days = period === '7d' ? 7 : period === '30d' ? 30 : period === '90d' ? 90 : 365;
        const occurrences = Math.floor(days / 5); // Roughly one occurrence per 5 days
        
        const history = [];
        const trendData = [];
        const returnDistribution = {};
        
        let successCount = 0;
        let totalReturns = 0;
        let minConfidence = 100, maxConfidence = 0;
        
        for (let i = 0; i < occurrences; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (days - (i * Math.floor(days/occurrences))));
            
            const confidence = 60 + Math.random() * 35; // 60-95%
            const success = Math.random() > 0.3; // 70% success rate
            const returnPct = success ? (Math.random() * 15) + 2 : -(Math.random() * 8);
            const daysHeld = Math.floor(Math.random() * 10) + 1;
            
            history.push({
                date: date.toISOString(),
                symbol: symbol,
                confidence: confidence,
                success: success,
                return: returnPct,
                daysHeld: daysHeld
            });
            
            if (success) successCount++;
            totalReturns += returnPct;
            minConfidence = Math.min(minConfidence, confidence);
            maxConfidence = Math.max(maxConfidence, confidence);
            
            // Group for trend analysis
            const weekStart = new Date(date);
            weekStart.setDate(date.getDate() - date.getDay());
            const weekKey = weekStart.toISOString().split('T')[0];
            
            const existingWeek = trendData.find(t => t.week === weekKey);
            if (existingWeek) {
                existingWeek.total++;
                if (success) existingWeek.successful++;
            } else {
                trendData.push({
                    week: weekKey,
                    total: 1,
                    successful: success ? 1 : 0
                });
            }
            
            // Return distribution
            const returnBucket = Math.floor(returnPct / 5) * 5;
            returnDistribution[returnBucket] = (returnDistribution[returnBucket] || 0) + 1;
        }
        
        // Calculate trend success rates
        trendData.forEach(week => {
            week.successRate = (week.successful / week.total) * 100;
        });
        
        return {
            pattern: pattern,
            symbol: symbol,
            period: period,
            summary: {
                successRate: (successCount / occurrences) * 100,
                totalOccurrences: occurrences,
                averageReturn: totalReturns / occurrences,
                confidenceRange: [Math.round(minConfidence), Math.round(maxConfidence)]
            },
            history: history,
            trendData: trendData.sort((a, b) => new Date(a.week) - new Date(b.week)),
            returnDistribution: returnDistribution
        };
    }
    
    /**
     * Sprint 24: Update performance summary cards
     */
    updatePerformanceSummary(data) {
        const summary = data.summary;
        
        const successRateElement = document.getElementById('overall-success-rate');
        const occurrencesElement = document.getElementById('total-occurrences');
        const avgReturnElement = document.getElementById('avg-return');
        const confidenceRangeElement = document.getElementById('confidence-range');
        
        if (successRateElement) {
            successRateElement.textContent = `${Math.round(summary.successRate)}%`;
        }
        
        if (occurrencesElement) {
            occurrencesElement.textContent = summary.totalOccurrences.toString();
        }
        
        if (avgReturnElement) {
            const returnClass = summary.averageReturn >= 0 ? 'text-success' : 'text-danger';
            const returnPrefix = summary.averageReturn >= 0 ? '+' : '';
            avgReturnElement.textContent = `${returnPrefix}${summary.averageReturn.toFixed(1)}%`;
            avgReturnElement.className = `h4 mb-0 ${returnClass}`;
        }
        
        if (confidenceRangeElement) {
            confidenceRangeElement.textContent = `${summary.confidenceRange[0]}-${summary.confidenceRange[1]}%`;
        }
    }
    
    /**
     * Sprint 24: Create performance charts using Chart.js
     */
    async createPerformanceCharts(data) {
        await this.createSuccessRateTrendChart(data.trendData);
        await this.createReturnDistributionChart(data.returnDistribution);
    }
    
    /**
     * Sprint 24: Create success rate trend chart
     */
    async createSuccessRateTrendChart(trendData) {
        const canvas = document.getElementById('successRateChart');
        if (!canvas || !trendData.length) return;
        
        // Destroy existing chart
        if (this.successRateChart) {
            this.successRateChart.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        const labels = trendData.map(d => new Date(d.week).toLocaleDateString());
        const successRates = trendData.map(d => d.successRate);
        
        this.successRateChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Success Rate (%)',
                    data: successRates,
                    borderColor: '#198754',
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Success Rate (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time Period'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Success Rate: ${context.parsed.y.toFixed(1)}%`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Sprint 24: Create return distribution chart
     */
    async createReturnDistributionChart(distribution) {
        const canvas = document.getElementById('returnDistributionChart');
        if (!canvas) return;
        
        // Destroy existing chart
        if (this.returnDistributionChart) {
            this.returnDistributionChart.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        const buckets = Object.keys(distribution).map(Number).sort((a, b) => a - b);
        const counts = buckets.map(bucket => distribution[bucket]);
        const labels = buckets.map(bucket => `${bucket}% to ${bucket + 5}%`);
        
        this.returnDistributionChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Occurrences',
                    data: counts,
                    backgroundColor: buckets.map(bucket => bucket >= 0 ? 'rgba(25, 135, 84, 0.6)' : 'rgba(220, 53, 69, 0.6)'),
                    borderColor: buckets.map(bucket => bucket >= 0 ? '#198754' : '#dc3545'),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Occurrences'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Return Range'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    /**
     * Sprint 24: Update performance history table
     */
    updatePerformanceTable(data) {
        const tbody = document.getElementById('performance-table-body');
        if (!tbody) return;
        
        // Show recent 10 entries
        const recentHistory = data.history.slice(-10).reverse();
        
        tbody.innerHTML = recentHistory.map(entry => {
            const resultClass = entry.success ? 'text-success' : 'text-danger';
            const resultIcon = entry.success ? 'fas fa-check-circle' : 'fas fa-times-circle';
            const returnClass = entry.return >= 0 ? 'text-success' : 'text-danger';
            const returnPrefix = entry.return >= 0 ? '+' : '';
            
            return `
                <tr>
                    <td>${new Date(entry.date).toLocaleDateString()}</td>
                    <td><strong>${entry.symbol}</strong></td>
                    <td>${Math.round(entry.confidence)}%</td>
                    <td class="${resultClass}">
                        <i class="${resultIcon} me-1"></i>
                        ${entry.success ? 'Success' : 'Failed'}
                    </td>
                    <td class="${returnClass}">
                        ${returnPrefix}${entry.return.toFixed(1)}%
                    </td>
                    <td>${entry.daysHeld} days</td>
                </tr>
            `;
        }).join('');
    }
    
    /**
     * Sprint 24: Export performance data
     */
    exportPerformanceData() {
        if (!this.currentPerformancePattern) return;
        
        // Create CSV content
        const csvContent = this.generatePerformanceCSV();
        
        // Create download link
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${this.currentPerformancePattern}_performance_${this.currentPerformancePeriod}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        this.showNotification(`Performance data exported for ${this.currentPerformancePattern}`, 'success');
    }
    
    /**
     * Sprint 24: Generate CSV content for performance data
     */
    generatePerformanceCSV() {
        const headers = ['Date', 'Symbol', 'Pattern', 'Confidence', 'Success', 'Return %', 'Days Held'];
        const rows = [headers.join(',')];
        
        // Add sample data rows (in real implementation, use actual loaded data)
        for (let i = 0; i < 10; i++) {
            const date = new Date();
            date.setDate(date.getDate() - i * 3);
            const success = Math.random() > 0.3;
            const returnPct = success ? Math.random() * 15 + 2 : -(Math.random() * 8);
            
            rows.push([
                date.toLocaleDateString(),
                this.currentPerformanceSymbol || 'SYMBOL',
                this.currentPerformancePattern,
                Math.round(60 + Math.random() * 35),
                success ? 'Yes' : 'No',
                returnPct.toFixed(1),
                Math.floor(Math.random() * 10) + 1
            ].join(','));
        }
        
        return rows.join('\n');
    }
    
    /**
     * Sprint 24: Open create alert modal
     */
    openCreateAlert(symbol, pattern, confidence) {
        // Populate modal with provided values
        const alertSymbol = document.getElementById('alert-symbol');
        const alertPattern = document.getElementById('alert-pattern');
        const alertConfidence = document.getElementById('alert-confidence');
        const alertConfidenceValue = document.getElementById('alert-confidence-value');
        const alertName = document.getElementById('alert-name');
        
        if (alertSymbol) alertSymbol.value = symbol;
        if (alertConfidence) {
            alertConfidence.value = confidence;
            if (alertConfidenceValue) {
                alertConfidenceValue.textContent = `${Math.round(confidence * 100)}%`;
            }
        }
        if (alertName) {
            alertName.value = `${pattern} alert for ${symbol}`;
        }
        
        // Populate pattern dropdown
        this.populatePatternDropdown(pattern);
        
        // Setup alert form handlers
        this.setupAlertFormHandlers();
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('createAlertModal'));
        modal.show();
        
        // Update preview
        this.updateAlertPreview();
    }
    
    /**
     * Sprint 24: Setup alert form event handlers
     */
    setupAlertFormHandlers() {
        // Confidence range handler
        const confidenceRange = document.getElementById('alert-confidence');
        const confidenceValue = document.getElementById('alert-confidence-value');
        
        if (confidenceRange && confidenceValue) {
            confidenceRange.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                confidenceValue.textContent = `${Math.round(value * 100)}%`;
                this.updateAlertPreview();
            });
        }
        
        // Form change handlers for preview update
        const formElements = [
            'alert-name', 'alert-symbol', 'alert-pattern', 'alert-frequency', 
            'alert-email', 'alert-browser', 'alert-webhook', 'alert-active-hours', 
            'alert-volume-filter', 'alert-expiry'
        ];
        
        formElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.updateAlertPreview());
                if (element.type === 'text') {
                    element.addEventListener('input', () => this.updateAlertPreview());
                }
            }
        });
        
        // Save alert button handler
        const saveAlertBtn = document.getElementById('save-alert-btn');
        if (saveAlertBtn) {
            saveAlertBtn.addEventListener('click', () => this.saveAlert());
        }
    }
    
    /**
     * Sprint 24: Populate pattern dropdown with available patterns
     */
    populatePatternDropdown(selectedPattern = '') {
        const patternSelect = document.getElementById('alert-pattern');
        if (!patternSelect) return;
        
        // Clear existing options (except "Any Pattern")
        patternSelect.innerHTML = '<option value="">Any Pattern</option>';
        
        // Add pattern options
        this.availablePatterns.forEach(pattern => {
            const option = document.createElement('option');
            option.value = pattern;
            option.textContent = pattern;
            if (pattern === selectedPattern) {
                option.selected = true;
            }
            patternSelect.appendChild(option);
        });
    }
    
    /**
     * Sprint 24: Update alert preview based on current form values
     */
    updateAlertPreview() {
        const previewElement = document.getElementById('alert-preview');
        if (!previewElement) return;
        
        const name = document.getElementById('alert-name')?.value || 'Unnamed Alert';
        const symbol = document.getElementById('alert-symbol')?.value || 'Any Symbol';
        const pattern = document.getElementById('alert-pattern')?.value || 'Any Pattern';
        const confidence = document.getElementById('alert-confidence')?.value || 0.7;
        const frequency = document.getElementById('alert-frequency')?.value || 'daily';
        
        const channels = [];
        if (document.getElementById('alert-email')?.checked) channels.push('Email');
        if (document.getElementById('alert-browser')?.checked) channels.push('Browser');
        if (document.getElementById('alert-webhook')?.checked) channels.push('Webhook');
        
        const confidencePercent = Math.round(confidence * 100);
        const channelText = channels.length > 0 ? channels.join(', ') : 'No notifications';
        const frequencyText = frequency === 'realtime' ? 'immediately' : `via ${frequency} summary`;
        
        previewElement.innerHTML = `
            <div class="d-flex align-items-start">
                <i class="fas fa-bell text-warning me-2 mt-1"></i>
                <div>
                    <strong>${name}</strong><br>
                    <small class="text-muted">
                        When <strong>${pattern}</strong> patterns are detected on <strong>${symbol}</strong> 
                        with ≥${confidencePercent}% confidence, notify via <strong>${channelText}</strong> 
                        ${frequencyText}.
                    </small>
                </div>
            </div>
        `;
    }
    
    /**
     * Sprint 24: Save alert configuration
     */
    async saveAlert() {
        try {
            // Get form values
            const alertConfig = {
                name: document.getElementById('alert-name')?.value,
                symbol: document.getElementById('alert-symbol')?.value,
                pattern: document.getElementById('alert-pattern')?.value || null,
                confidence_min: parseFloat(document.getElementById('alert-confidence')?.value || 0.7),
                frequency: document.getElementById('alert-frequency')?.value,
                channels: {
                    email: document.getElementById('alert-email')?.checked || false,
                    browser: document.getElementById('alert-browser')?.checked || false,
                    webhook: document.getElementById('alert-webhook')?.checked || false
                },
                options: {
                    active_hours_only: document.getElementById('alert-active-hours')?.checked || false,
                    high_volume_only: document.getElementById('alert-volume-filter')?.checked || false,
                    expiry: document.getElementById('alert-expiry')?.value || 'never'
                },
                created_at: new Date().toISOString(),
                active: true
            };
            
            // Validate required fields
            if (!alertConfig.name || !alertConfig.symbol) {
                this.showNotification('Please fill in required fields (Name, Symbol)', 'warning');
                return;
            }
            
            // Show loading state
            const saveBtn = document.getElementById('save-alert-btn');
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creating...';
            saveBtn.disabled = true;
            
            // ⚠️ CRITICAL TECHNICAL DEBT - REMOVE BEFORE PRODUCTION ⚠️
            // TODO: Replace with real /api/alerts POST endpoint
            // Mock API call (in real implementation, call /api/alerts)
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createAlertModal'));
            if (modal) modal.hide();
            
            // Show success notification
            this.showNotification(`Alert "${alertConfig.name}" created successfully!`, 'success');
            
            // Log alert configuration (for development)
            
        } catch (error) {
            console.error('Failed to save alert:', error);
            this.showNotification('Failed to create alert. Please try again.', 'error');
        } finally {
            // Reset button state
            const saveBtn = document.getElementById('save-alert-btn');
            if (saveBtn) {
                saveBtn.innerHTML = '<i class="fas fa-bell me-1"></i>Create Alert';
                saveBtn.disabled = false;
            }
        }
    }
    
    /**
     * Sprint 24: Export filtered pattern results to CSV
     */
    exportToCSV() {
        const displayPatterns = this.getPatternsForDisplay();
        
        if (displayPatterns.length === 0) {
            this.showNotification('No pattern data to export', 'warning');
            return;
        }
        
        try {
            // Create CSV content
            const csvContent = this.generatePatternResultsCSV(displayPatterns);
            
            // Create download link
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.style.visibility = 'hidden';
            
            // Generate filename with current filters
            const timestamp = new Date().toISOString().split('T')[0];
            const universe = this.filters.universe;
            const confidence = Math.round(this.filters.confidence_min * 100);
            link.download = `pattern_results_${universe}_${confidence}pct_${timestamp}.csv`;
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            this.showNotification(`Exported ${displayPatterns.length} patterns to CSV`, 'success');
        } catch (error) {
            console.error('CSV export failed:', error);
            this.showNotification('Export failed. Please try again.', 'error');
        }
    }
    
    /**
     * Sprint 24: Export filtered pattern results to PDF
     */
    exportToPDF() {
        const displayPatterns = this.getPatternsForDisplay();
        
        if (displayPatterns.length === 0) {
            this.showNotification('No pattern data to export', 'warning');
            return;
        }
        
        try {
            // Check if jsPDF is available
            if (typeof window.jsPDF === 'undefined') {
                this.showNotification('PDF export not available. Please check page dependencies.', 'warning');
                return;
            }
            
            // Initialize jsPDF
            const { jsPDF } = window.jsPDF;
            const doc = new jsPDF();
            
            // Document title and metadata
            const timestamp = new Date().toLocaleString();
            const universe = this.filters.universe.toUpperCase();
            const confidence = Math.round(this.filters.confidence_min * 100);
            
            // Title
            doc.setFontSize(16);
            doc.text('TickStock Pattern Discovery Results', 20, 20);
            
            // Subtitle with filters
            doc.setFontSize(12);
            doc.text(`Universe: ${universe} | Confidence: ≥${confidence}% | Generated: ${timestamp}`, 20, 30);
            
            // Summary stats
            doc.setFontSize(10);
            const avgConfidence = displayPatterns.reduce((sum, p) => sum + p.confidence, 0) / displayPatterns.length;
            doc.text(`Total Patterns: ${displayPatterns.length} | Average Confidence: ${(avgConfidence * 100).toFixed(1)}%`, 20, 40);
            
            // Create table data
            const tableData = displayPatterns.slice(0, 50).map(pattern => [
                pattern.symbol,
                pattern.pattern,
                `${(pattern.confidence * 100).toFixed(1)}%`,
                `$${pattern.price.toFixed(2)}`,
                this.formatVolume(pattern.volume),
                this.formatTime(pattern.timestamp)
            ]);
            
            // Table headers
            const headers = ['Symbol', 'Pattern', 'Confidence', 'Price', 'Volume', 'Time'];
            
            // Add table using autoTable plugin if available
            if (doc.autoTable) {
                doc.autoTable({
                    head: [headers],
                    body: tableData,
                    startY: 50,
                    styles: { fontSize: 8 },
                    headStyles: { fillColor: [13, 110, 253] }
                });
                
                // Add note if data was truncated
                if (displayPatterns.length > 50) {
                    const finalY = doc.lastAutoTable.finalY + 10;
                    doc.text(`Note: Showing first 50 of ${displayPatterns.length} results. Export to CSV for complete data.`, 20, finalY);
                }
            } else {
                // Fallback: simple text table
                let yPos = 50;
                doc.text(headers.join(' | '), 20, yPos);
                yPos += 10;
                
                tableData.slice(0, 20).forEach(row => {
                    doc.text(row.join(' | '), 20, yPos);
                    yPos += 10;
                    if (yPos > 270) return; // Page limit
                });
                
                if (displayPatterns.length > 20) {
                    doc.text(`... and ${displayPatterns.length - 20} more results`, 20, yPos + 10);
                }
            }
            
            // Generate filename and save
            const filename = `pattern_results_${universe.toLowerCase()}_${confidence}pct_${new Date().toISOString().split('T')[0]}.pdf`;
            doc.save(filename);
            
            this.showNotification(`Exported ${Math.min(displayPatterns.length, 50)} patterns to PDF`, 'success');
        } catch (error) {
            console.error('PDF export failed:', error);
            this.showNotification('PDF export failed. Please try again.', 'error');
        }
    }
    
    /**
     * Sprint 24: Generate CSV content for pattern results
     */
    generatePatternResultsCSV(patterns) {
        const headers = [
            'Symbol', 'Pattern', 'Confidence (%)', 'Price ($)', 'Volume', 
            'Change (%)', 'Timestamp', 'Unix Timestamp'
        ];
        
        const rows = [headers.join(',')];
        
        patterns.forEach(pattern => {
            const row = [
                pattern.symbol,
                pattern.pattern,
                (pattern.confidence * 100).toFixed(1),
                pattern.price.toFixed(2),
                pattern.volume,
                pattern.change_pct ? pattern.change_pct.toFixed(2) : '0.00',
                new Date(pattern.timestamp).toLocaleString(),
                pattern.timestamp
            ];
            
            // Handle commas in values by wrapping in quotes
            const escapedRow = row.map(cell => {
                const cellStr = String(cell);
                return cellStr.includes(',') ? `"${cellStr}"` : cellStr;
            });
            
            rows.push(escapedRow.join(','));
        });
        
        return rows.join('\n');
    }
    
    /**
     * Sprint 24: Retry performance data loading
     */
    retryPerformanceLoad() {
        if (this.currentPerformancePattern) {
            this.loadPerformanceHistory(
                this.currentPerformancePattern, 
                this.currentPerformanceSymbol, 
                this.currentPerformancePeriod
            );
        }
    }
    
    /**
     * Sprint 24: Setup table sorting functionality
     */
    setupTableSorting() {
        // Initialize sorting state
        this.sortField = null;
        this.sortDirection = 'asc'; // 'asc' or 'desc'
        
        // Add click handlers for sortable headers
        const sortableHeaders = document.querySelectorAll('.sortable');
        sortableHeaders.forEach(header => {
            header.addEventListener('click', (e) => {
                const field = header.dataset.sort;
                this.handleColumnSort(field);
            });
        });
        
    }
    
    /**
     * Sprint 24: Handle column sort click
     */
    handleColumnSort(field) {
        // Toggle direction if same field, otherwise set to ascending
        if (this.sortField === field) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortField = field;
            this.sortDirection = 'asc';
        }
        
        // Update visual indicators
        this.updateSortIndicators(field, this.sortDirection);
        
        // Sort and re-render patterns
        this.sortAndRenderPatterns();
        
        // Show feedback
        const directionText = this.sortDirection === 'asc' ? 'ascending' : 'descending';
        this.showNotification(`Sorted by ${field} (${directionText})`, 'info');
    }
    
    /**
     * Sprint 24: Update visual sort indicators in table headers
     */
    updateSortIndicators(activeField, direction) {
        // Reset all sort icons
        const allSortIcons = document.querySelectorAll('[id^="sort-"]');
        allSortIcons.forEach(icon => {
            icon.className = 'fas fa-sort text-muted ms-1';
        });
        
        // Update active sort icon
        const activeIcon = document.getElementById(`sort-${activeField}`);
        if (activeIcon) {
            const iconClass = direction === 'asc' ? 'fas fa-sort-up text-primary ms-1' : 'fas fa-sort-down text-primary ms-1';
            activeIcon.className = iconClass;
        }
    }
    
    /**
     * Sprint 24: Sort patterns and re-render table
     */
    sortAndRenderPatterns() {
        const displayPatterns = this.getPatternsForDisplay();
        
        if (!displayPatterns || displayPatterns.length === 0) {
            return;
        }
        
        // Sort patterns based on current sort field and direction
        const sortedPatterns = [...displayPatterns].sort((a, b) => {
            return this.comparePatterns(a, b, this.sortField, this.sortDirection);
        });
        
        // Update the appropriate pattern array
        if (this.filteredPatterns) {
            this.filteredPatterns = sortedPatterns;
        } else {
            this.patterns = sortedPatterns;
        }
        
        // Re-render table
        this.renderPatterns();
    }
    
    /**
     * Sprint 24: Compare two patterns for sorting
     */
    comparePatterns(a, b, field, direction) {
        let valueA, valueB;
        
        switch (field) {
            case 'symbol':
                valueA = a.symbol || '';
                valueB = b.symbol || '';
                return this.compareStrings(valueA, valueB, direction);
                
            case 'pattern':
                valueA = a.pattern || '';
                valueB = b.pattern || '';
                return this.compareStrings(valueA, valueB, direction);
                
            case 'confidence':
                valueA = a.confidence || 0;
                valueB = b.confidence || 0;
                return this.compareNumbers(valueA, valueB, direction);
                
            case 'price':
                valueA = a.price || 0;
                valueB = b.price || 0;
                return this.compareNumbers(valueA, valueB, direction);
                
            case 'change':
                valueA = a.change_percent || 0;
                valueB = b.change_percent || 0;
                return this.compareNumbers(valueA, valueB, direction);
                
            case 'rs':
                valueA = a.rs || 0;
                valueB = b.rs || 0;
                return this.compareNumbers(valueA, valueB, direction);
                
            case 'volume':
                valueA = a.volume || 0;
                valueB = b.volume || 0;
                return this.compareNumbers(valueA, valueB, direction);
                
            case 'timestamp':
                valueA = new Date(a.timestamp).getTime();
                valueB = new Date(b.timestamp).getTime();
                return this.compareNumbers(valueA, valueB, direction);
                
            default:
                return 0;
        }
    }
    
    /**
     * Sprint 24: Compare strings for sorting
     */
    compareStrings(a, b, direction) {
        const result = a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
        return direction === 'asc' ? result : -result;
    }
    
    /**
     * Sprint 24: Compare numbers for sorting
     */
    compareNumbers(a, b, direction) {
        const result = a - b;
        return direction === 'asc' ? result : -result;
    }
    
    /**
     * Sprint 24: Reset table sorting
     */
    resetSorting() {
        this.sortField = null;
        this.sortDirection = 'asc';
        
        // Reset all sort indicators
        const allSortIcons = document.querySelectorAll('[id^="sort-"]');
        allSortIcons.forEach(icon => {
            icon.className = 'fas fa-sort text-muted ms-1';
        });
        
        // Re-render patterns in original order
        this.renderPatterns();
    }
    
    setupFilterHandlers() {
        // Universe filter
        const universeFilter = document.getElementById('universe-filter');
        if (universeFilter) {
            universeFilter.value = this.filters.universe;
            universeFilter.addEventListener('change', (e) => {
                this.filters.universe = e.target.value;
                this.loadPatterns();
            });
        }
        
        // Confidence filter
        const confidenceFilter = document.getElementById('confidence-filter');
        const confidenceValue = document.getElementById('confidence-value');
        if (confidenceFilter && confidenceValue) {
            confidenceFilter.value = this.filters.confidence_min;
            confidenceValue.textContent = Math.round(this.filters.confidence_min * 100) + '%';
            
            confidenceFilter.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                this.filters.confidence_min = value;
                confidenceValue.textContent = Math.round(value * 100) + '%';
            });
            
            confidenceFilter.addEventListener('change', () => this.loadPatterns());
        }
        
        // Limit filter
        const limitFilter = document.getElementById('limit-filter');
        if (limitFilter) {
            limitFilter.value = this.filters.limit;
            limitFilter.addEventListener('change', (e) => {
                this.filters.limit = parseInt(e.target.value);
                this.loadPatterns();
            });
        }
        
        // Sprint 24: Symbol search and sector filter
        this.setupSymbolSearchHandlers();
        this.setupSectorFilterHandlers();
    }
    
    /**
     * Sprint 24: Setup symbol search with autocomplete functionality
     */
    setupSymbolSearchHandlers() {
        const symbolSearch = document.getElementById('symbol-search');
        const symbolSuggestions = document.getElementById('symbol-suggestions');
        const selectedSymbols = document.getElementById('selected-symbols');
        
        if (!symbolSearch || !symbolSuggestions || !selectedSymbols) return;
        
        let searchTimeout;
        
        // Symbol search input handler with debouncing
        symbolSearch.addEventListener('input', (e) => {
            const query = e.target.value.trim().toUpperCase();
            
            clearTimeout(searchTimeout);
            
            if (query.length < 1) {
                this.hideSuggestions();
                return;
            }
            
            // Debounce search to avoid too many API calls
            searchTimeout = setTimeout(() => {
                this.searchSymbols(query);
            }, 300);
        });
        
        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!symbolSearch.contains(e.target) && !symbolSuggestions.contains(e.target)) {
                this.hideSuggestions();
            }
        });
        
        // Handle keyboard navigation
        symbolSearch.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideSuggestions();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                const query = e.target.value.trim().toUpperCase();
                if (query && this.isValidSymbol(query)) {
                    this.addSelectedSymbol(query);
                    symbolSearch.value = '';
                    this.hideSuggestions();
                }
            }
        });
        
        // Render currently selected symbols
        this.renderSelectedSymbols();
    }
    
    /**
     * Sprint 24: Setup sector filter handlers
     */
    setupSectorFilterHandlers() {
        const sectorFilter = document.getElementById('sector-filter');
        if (sectorFilter) {
            sectorFilter.value = this.filters.sector;
            sectorFilter.addEventListener('change', (e) => {
                this.filters.sector = e.target.value;
                this.loadPatterns();
            });
        }
    }
    
    /**
     * Setup collapsible filter sections with caret arrows
     */
    setupCollapsibleFilters() {
        
        // Look for headers in both the main content and filter column
        const collapsibleHeaders = document.querySelectorAll('.collapsible-header, .filter-column .collapsible-header');
        
        collapsibleHeaders.forEach((header, index) => {
            
            // Remove any existing event listeners to prevent duplicates
            const newHeader = header.cloneNode(true);
            header.parentNode.replaceChild(newHeader, header);
            
            newHeader.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const targetId = newHeader.getAttribute('data-target');
                const targetContent = document.getElementById(targetId);
                const caret = newHeader.querySelector('.collapse-caret');
                
                
                if (!targetContent || !caret) {
                    console.warn('Missing target content or caret for:', targetId);
                    return;
                }
                
                // Toggle the collapse state
                const isExpanded = targetContent.classList.contains('show');
                
                if (isExpanded) {
                    // Collapse
                    targetContent.classList.remove('show');
                    caret.classList.remove('fa-chevron-down');
                    caret.classList.add('fa-chevron-right');
                    header.setAttribute('aria-expanded', 'false');
                } else {
                    // Expand
                    targetContent.classList.add('show');
                    caret.classList.remove('fa-chevron-right');
                    caret.classList.add('fa-chevron-down');
                    header.setAttribute('aria-expanded', 'true');
                }
                
                // Add smooth transition
                targetContent.style.transition = 'all 0.3s ease-in-out';
                
            });
            
            // Add hover effect
            header.style.cursor = 'pointer';
            header.addEventListener('mouseenter', () => {
                header.style.backgroundColor = 'rgba(0, 123, 255, 0.1)';
            });
            
            header.addEventListener('mouseleave', () => {
                header.style.backgroundColor = '';
            });
            
            // Set initial aria-expanded state
            const targetId = header.getAttribute('data-target');
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                const isExpanded = targetContent.classList.contains('show');
                header.setAttribute('aria-expanded', isExpanded.toString());
            }
        });
        
    }
    
    /**
     * Public method to reinitialize collapsible filters (for sidebar navigation)
     */
    reinitializeCollapsibleFilters() {
        // Add a small delay to ensure DOM is fully updated
        setTimeout(() => {
            this.setupCollapsibleFilters();
            this.integrateExternalServices();
        }, 200);
    }
    
    /**
     * Integrate external services (watchlists, presets, visualization)
     */
    integrateExternalServices() {
        // Integrate Watchlist Manager
        this.integrateWatchlistService();
        
        // Integrate Filter Presets Service
        this.integratePresetsService();
        
        // Ensure Pattern Visualization Service is working
        this.integrateVisualizationService();
    }
    
    /**
     * Integrate Watchlist Manager service
     */
    integrateWatchlistService() {
        const watchlistContent = document.getElementById('watchlist-content');
        if (watchlistContent && window.watchlistManager && window.watchlistManager.isInitialized) {
            try {
                // The renderWatchlistPanel method updates DOM directly
                window.watchlistManager.renderWatchlistPanel();
            } catch (error) {
                console.error('Failed to integrate Watchlist Manager:', error);
                watchlistContent.innerHTML = `
                    <div class="p-3 border-top">
                        <div class="alert alert-warning mb-0">
                            <small><i class="fas fa-exclamation-triangle me-1"></i> Watchlists temporarily unavailable</small>
                        </div>
                    </div>
                `;
            }
        } else if (watchlistContent) {
            // Service not ready, try again in a moment
            setTimeout(() => this.integrateWatchlistService(), 1000);
        }
    }
    
    /**
     * Integrate Filter Presets Service
     */
    integratePresetsService() {
        const presetsContent = document.getElementById('presets-content');
        if (presetsContent && window.filterPresetsService && window.filterPresetsService.isInitialized) {
            try {
                // The renderPresetsPanel method updates DOM directly
                window.filterPresetsService.renderPresetsPanel();
            } catch (error) {
                console.error('Failed to integrate Filter Presets Service:', error);
                presetsContent.innerHTML = `
                    <div class="p-3 border-top">
                        <div class="alert alert-warning mb-0">
                            <small><i class="fas fa-exclamation-triangle me-1"></i> Filter presets temporarily unavailable</small>
                        </div>
                    </div>
                `;
            }
        } else if (presetsContent) {
            // Service not ready, try again in a moment
            setTimeout(() => this.integratePresetsService(), 1000);
        }
    }
    
    /**
     * Integrate Pattern Visualization Service for enhanced columns
     */
    integrateVisualizationService() {
        if (window.patternVisualizationService && window.patternVisualizationService.isInitialized) {
        } else if (window.patternVisualizationService) {
            // Service exists but not initialized, wait for it
            setTimeout(() => this.integrateVisualizationService(), 500);
        }
    }
    
    /**
     * Sprint 24: Search symbols with autocomplete suggestions
     */
    async searchSymbols(query) {
        try {
            // ⚠️ CRITICAL TECHNICAL DEBT - REMOVE BEFORE PRODUCTION ⚠️
            // TODO: Replace with real /api/symbols?search={query} API call
            // Mock symbol data for demonstration (in real implementation, call /api/symbols)
            const mockSymbols = this.generateMockSymbols();
            
            // Filter symbols based on query
            const matches = mockSymbols
                .filter(symbol => 
                    symbol.symbol.includes(query) || 
                    symbol.company.toUpperCase().includes(query)
                )
                .slice(0, 8); // Limit to 8 suggestions
            
            this.showSuggestions(matches);
            
        } catch (error) {
            console.error('Symbol search failed:', error);
            this.hideSuggestions();
        }
    }
    
    /**
     * Sprint 24: Show autocomplete suggestions
     */
    showSuggestions(symbols) {
        const suggestionsContainer = document.getElementById('symbol-suggestions');
        if (!suggestionsContainer) return;
        
        if (symbols.length === 0) {
            this.hideSuggestions();
            return;
        }
        
        suggestionsContainer.innerHTML = symbols.map(symbol => `
            <button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                    data-symbol="${symbol.symbol}">
                <div>
                    <strong>${symbol.symbol}</strong>
                    <small class="text-muted ms-2">${symbol.company}</small>
                </div>
                <span class="badge bg-secondary">${symbol.sector}</span>
            </button>
        `).join('');
        
        // Add click handlers to suggestions
        const suggestionButtons = suggestionsContainer.querySelectorAll('button');
        suggestionButtons.forEach(button => {
            button.addEventListener('click', () => {
                const symbol = button.dataset.symbol;
                this.addSelectedSymbol(symbol);
                document.getElementById('symbol-search').value = '';
                this.hideSuggestions();
            });
        });
        
        suggestionsContainer.classList.remove('d-none');
    }
    
    /**
     * Sprint 24: Hide autocomplete suggestions
     */
    hideSuggestions() {
        const suggestionsContainer = document.getElementById('symbol-suggestions');
        if (suggestionsContainer) {
            suggestionsContainer.classList.add('d-none');
        }
    }
    
    /**
     * Sprint 24: Add symbol to selected symbols filter
     */
    addSelectedSymbol(symbol) {
        if (!this.filters.symbols.includes(symbol)) {
            this.filters.symbols.push(symbol);
            this.renderSelectedSymbols();
            this.loadPatterns(); // Refresh results with new filter
        }
    }
    
    /**
     * Sprint 24: Remove symbol from selected symbols filter
     */
    removeSelectedSymbol(symbol) {
        this.filters.symbols = this.filters.symbols.filter(s => s !== symbol);
        this.renderSelectedSymbols();
        this.loadPatterns(); // Refresh results with updated filter
    }
    
    /**
     * Sprint 24: Render selected symbol badges
     */
    renderSelectedSymbols() {
        const container = document.getElementById('selected-symbols');
        if (!container) return;
        
        if (this.filters.symbols.length === 0) {
            container.innerHTML = '<span class="text-muted small">No symbols selected</span>';
            return;
        }
        
        container.innerHTML = this.filters.symbols.map(symbol => `
            <span class="badge bg-primary d-flex align-items-center">
                ${symbol}
                <button type="button" class="btn-close btn-close-white ms-1" 
                        data-symbol="${symbol}" aria-label="Remove ${symbol}"></button>
            </span>
        `).join('');
        
        // Add remove handlers
        const removeButtons = container.querySelectorAll('.btn-close');
        removeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const symbol = button.dataset.symbol;
                this.removeSelectedSymbol(symbol);
            });
        });
    }
    
    /**
     * Sprint 24: Check if symbol is valid format
     */
    isValidSymbol(symbol) {
        // Basic symbol validation (1-5 uppercase letters)
        return /^[A-Z]{1,5}$/.test(symbol);
    }
    
    /**
     * ⚠️ CRITICAL TECHNICAL DEBT - REMOVE BEFORE PRODUCTION ⚠️  
     * Sprint 24: Generate mock symbol data for autocomplete
     * 
     * TODO: Replace with real /api/symbols endpoint integration
     * Required: Implement symbol search API with real market data
     * Impact: Autocomplete only shows 25 hardcoded symbols vs full market
     */
    generateMockSymbols() {
        return [
            { symbol: 'AAPL', company: 'Apple Inc.', sector: 'Technology' },
            { symbol: 'GOOGL', company: 'Alphabet Inc.', sector: 'Technology' },
            { symbol: 'MSFT', company: 'Microsoft Corporation', sector: 'Technology' },
            { symbol: 'TSLA', company: 'Tesla Inc.', sector: 'Consumer Discretionary' },
            { symbol: 'AMZN', company: 'Amazon.com Inc.', sector: 'Consumer Discretionary' },
            { symbol: 'META', company: 'Meta Platforms Inc.', sector: 'Technology' },
            { symbol: 'NVDA', company: 'NVIDIA Corporation', sector: 'Technology' },
            { symbol: 'JPM', company: 'JPMorgan Chase & Co.', sector: 'Financials' },
            { symbol: 'JNJ', company: 'Johnson & Johnson', sector: 'Healthcare' },
            { symbol: 'V', company: 'Visa Inc.', sector: 'Financials' },
            { symbol: 'WMT', company: 'Walmart Inc.', sector: 'Consumer Staples' },
            { symbol: 'PG', company: 'Procter & Gamble Co.', sector: 'Consumer Staples' },
            { symbol: 'UNH', company: 'UnitedHealth Group Inc.', sector: 'Healthcare' },
            { symbol: 'HD', company: 'Home Depot Inc.', sector: 'Consumer Discretionary' },
            { symbol: 'BAC', company: 'Bank of America Corp.', sector: 'Financials' },
            { symbol: 'MA', company: 'Mastercard Inc.', sector: 'Financials' },
            { symbol: 'DIS', company: 'Walt Disney Co.', sector: 'Communication' },
            { symbol: 'NFLX', company: 'Netflix Inc.', sector: 'Communication' },
            { symbol: 'CRM', company: 'Salesforce Inc.', sector: 'Technology' },
            { symbol: 'ORCL', company: 'Oracle Corporation', sector: 'Technology' },
            { symbol: 'PFE', company: 'Pfizer Inc.', sector: 'Healthcare' },
            { symbol: 'KO', company: 'Coca-Cola Co.', sector: 'Consumer Staples' },
            { symbol: 'PEP', company: 'PepsiCo Inc.', sector: 'Consumer Staples' },
            { symbol: 'ADBE', company: 'Adobe Inc.', sector: 'Technology' },
            { symbol: 'CMCSA', company: 'Comcast Corporation', sector: 'Communication' }
        ];
    }
    
    /**
     * Sprint 24: Enhanced API call with retry logic and better error handling
     */
    async loadPatterns(retryCount = 0) {
        if (this.isLoading && retryCount === 0) return;
        
        this.isLoading = true;
        this.showLoading(true, retryCount > 0 ? `Retrying... (${retryCount}/3)` : 'Loading patterns...');
        this.hideError();
        
        try {
            const params = new URLSearchParams();
            Object.entries(this.filters).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    if (Array.isArray(value)) {
                        // Handle pattern_types array
                        value.forEach(item => params.append(key, item.toString()));
                    } else {
                        params.append(key, value.toString());
                    }
                }
            });
            
            // Enhanced fetch with timeout and retry logic
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch(`${this.apiBaseUrl}/patterns/scan?${params}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            // Handle different HTTP status codes with specific messages
            if (!response.ok) {
                await this.handleHttpError(response, retryCount);
                return;
            }
            
            const data = await response.json();
            
            // Validate response structure
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid response format from server');
            }
            
            this.patterns = data.patterns || [];
            this.renderPatterns();
            this.updatePatternCount();
            
            // Success feedback for retries
            if (retryCount > 0) {
                this.showNotification(`Successfully loaded patterns after ${retryCount} ${retryCount === 1 ? 'retry' : 'retries'}`, 'success');
            }
            
        } catch (error) {
            console.error('Failed to load patterns:', error);
            await this.handlePatternLoadError(error, retryCount);
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }
    
    /**
     * Sprint 24: Handle HTTP errors with specific user-friendly messages
     */
    async handleHttpError(response, retryCount) {
        let errorMessage = 'Unknown server error';
        let shouldRetry = false;
        
        switch (response.status) {
            case 400:
                errorMessage = 'Invalid filter parameters. Please check your settings.';
                break;
            case 401:
                errorMessage = 'Authentication required. Please refresh the page and try again.';
                break;
            case 403:
                errorMessage = 'Access denied. You may not have permission to view patterns.';
                break;
            case 404:
                errorMessage = 'Pattern service unavailable. The API endpoint may be temporarily down.';
                shouldRetry = true;
                break;
            case 429:
                errorMessage = 'Too many requests. Please wait a moment before trying again.';
                shouldRetry = true;
                break;
            case 500:
            case 502:
            case 503:
            case 504:
                errorMessage = 'Server temporarily unavailable. Retrying automatically...';
                shouldRetry = true;
                break;
            default:
                errorMessage = `Server error (${response.status}). Please try again later.`;
                shouldRetry = response.status >= 500;
        }
        
        if (shouldRetry && retryCount < 3) {
            await this.retryWithBackoff(retryCount);
        } else {
            throw new Error(errorMessage);
        }
    }
    
    /**
     * Sprint 24: Handle pattern loading errors with retry logic
     */
    async handlePatternLoadError(error, retryCount) {
        let userMessage = 'Failed to load patterns';
        let shouldRetry = false;
        
        if (error.name === 'AbortError') {
            userMessage = 'Request timed out. Check your internet connection.';
            shouldRetry = true;
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            userMessage = 'Network connection problem. Please check your internet connection.';
            shouldRetry = true;
        } else if (error.message.includes('Invalid response format')) {
            userMessage = 'Server returned invalid data. This may be a temporary issue.';
            shouldRetry = true;
        } else {
            userMessage = error.message;
            shouldRetry = error.message.includes('temporarily') || error.message.includes('Server error');
        }
        
        if (shouldRetry && retryCount < 3) {
            await this.retryWithBackoff(retryCount);
        } else {
            this.showEnhancedError(userMessage, retryCount >= 3);
        }
    }
    
    /**
     * Sprint 24: Retry with exponential backoff
     */
    async retryWithBackoff(retryCount) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 5000); // 1s, 2s, 4s, max 5s
        
        this.showNotification(`Retrying in ${delay/1000} seconds...`, 'info');
        
        await new Promise(resolve => setTimeout(resolve, delay));
        return this.loadPatterns(retryCount + 1);
    }
    
    renderPatterns() {
        const tbody = document.getElementById('pattern-table-body');
        const noPatterns = document.getElementById('no-patterns');
        const tableContainer = document.getElementById('pattern-table-container');
        const displayPatterns = this.getPatternsForDisplay();
        
        if (displayPatterns.length === 0) {
            if (tableContainer) tableContainer.style.display = 'none';
            if (noPatterns) noPatterns.classList.remove('d-none');
            return;
        }
        
        if (tableContainer) tableContainer.style.display = 'block';
        if (noPatterns) noPatterns.classList.add('d-none');
        
        if (tbody) {
            tbody.innerHTML = displayPatterns.map(pattern => this.renderPatternRow(pattern)).join('');
            
            // Trigger pattern enhancement after DOM is updated
            setTimeout(() => {
                // Enhance patterns with visualization service
                if (window.patternVisualizationService && window.patternVisualizationService.isInitialized) {
                    if (window.patternVisualizationService.enhancePatternRows) {
                        window.patternVisualizationService.enhancePatternRows(displayPatterns);
                    }
                }
                
                // Dispatch event for other services to listen
                const event = new CustomEvent('patternsUpdated', {
                    detail: { patterns: displayPatterns }
                });
                document.dispatchEvent(event);
            }, 100);
        }
    }
    
    renderPatternRow(pattern) {
        const changeClass = pattern.change_percent >= 0 ? 'text-success' : 'text-danger';
        const changeIcon = pattern.change_percent >= 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down';
        
        return `
            <tr data-symbol="${pattern.symbol}" data-pattern="${pattern.pattern}">
                <td><strong>${pattern.symbol}</strong></td>
                <td><span class="badge bg-primary">${pattern.pattern}</span></td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="me-2">${Math.round(pattern.confidence * 100)}%</span>
                        <div class="progress flex-fill" style="height: 4px;">
                            <div class="progress-bar" style="width: ${pattern.confidence * 100}%"></div>
                        </div>
                    </div>
                </td>
                <td>$${pattern.price.toFixed(2)}</td>
                <td class="${changeClass}">
                    <i class="${changeIcon} me-1"></i>
                    ${pattern.change_percent.toFixed(2)}%
                </td>
                <td>${pattern.rs ? pattern.rs.toFixed(0) : 'N/A'}</td>
                <td>${this.formatVolume(pattern.volume)}</td>
                <td class="trend-column">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </td>
                <td class="context-column">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </td>
                <td class="performance-column">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </td>
                <td>
                    <small class="text-muted">${this.formatTime(pattern.timestamp)}</small>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-success chart-btn" 
                                data-symbol="${pattern.symbol}" 
                                data-pattern="${pattern.pattern}"
                                data-price="${pattern.price}"
                                title="View ${pattern.symbol} chart">
                            <i class="fas fa-chart-line"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info performance-history-btn" 
                                data-symbol="${pattern.symbol}" 
                                data-pattern="${pattern.pattern}"
                                title="View ${pattern.pattern} performance history">
                            <i class="fas fa-history"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-primary add-to-watchlist-btn" 
                                data-symbol="${pattern.symbol}" 
                                title="Add ${pattern.symbol} to watchlist">
                            <i class="fas fa-plus"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-warning create-alert-btn" 
                                data-symbol="${pattern.symbol}" 
                                data-pattern="${pattern.pattern}"
                                data-confidence="${pattern.confidence}"
                                title="Create alert for ${pattern.pattern} on ${pattern.symbol}">
                            <i class="fas fa-bell"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    formatVolume(volume) {
        if (!volume) return 'N/A';
        if (volume >= 1000000) return (volume / 1000000).toFixed(1) + 'M';
        if (volume >= 1000) return (volume / 1000).toFixed(1) + 'K';
        return volume.toString();
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
        if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
        return date.toLocaleDateString();
    }
    
    handleNewPattern(alertData) {
        const pattern = alertData.event.data;
        this.patterns.unshift(pattern);
        
        // Keep only the most recent patterns based on limit
        if (this.patterns.length > this.filters.limit) {
            this.patterns = this.patterns.slice(0, this.filters.limit);
        }
        
        this.renderPatterns();
        this.updatePatternCount();
    }
    
    updatePatternCount() {
        const countElement = document.getElementById('pattern-count');
        if (countElement) {
            const displayPatterns = this.getPatternsForDisplay();
            const countText = this.filteredPatterns 
                ? `${displayPatterns.length} of ${this.patterns.length} patterns`
                : `${displayPatterns.length} patterns`;
            countElement.textContent = countText;
        }
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('ws-status');
        if (statusElement) {
            if (connected) {
                statusElement.className = 'badge bg-success';
                statusElement.textContent = 'Live';
            } else {
                statusElement.className = 'badge bg-warning';
                statusElement.textContent = 'Offline';
            }
        }
    }
    
    /**
     * Sprint 24: Enhanced loading display with custom messages
     */
    showLoading(show, customMessage = null) {
        const spinner = document.getElementById('loading-spinner');
        const refreshBtn = document.getElementById('refresh-btn');
        const refreshIcon = refreshBtn?.querySelector('.fa-sync-alt');
        
        if (spinner) {
            spinner.classList.toggle('d-none', !show);
            
            // Update loading message if provided
            if (customMessage) {
                const loadingText = spinner.querySelector('.text-muted');
                if (loadingText) {
                    loadingText.textContent = customMessage;
                }
            } else if (!show) {
                // Reset loading message when hiding
                const loadingText = spinner.querySelector('.text-muted');
                if (loadingText) {
                    loadingText.textContent = 'Loading pattern data...';
                }
            }
        }
        
        if (refreshBtn) {
            refreshBtn.disabled = show;
        }
        
        if (refreshIcon) {
            refreshIcon.classList.toggle('fa-spin', show);
        }
    }
    
    showError(message) {
        const errorDisplay = document.getElementById('error-display');
        const errorMessage = document.getElementById('error-message');
        
        if (errorDisplay && errorMessage) {
            errorMessage.textContent = message;
            errorDisplay.classList.remove('d-none');
        }
    }
    
    hideError() {
        const errorDisplay = document.getElementById('error-display');
        if (errorDisplay) {
            errorDisplay.classList.add('d-none');
        }
    }
    
    /**
     * Sprint 24: Enhanced error display with retry and help options
     */
    showEnhancedError(message, maxRetriesReached = false) {
        const errorDisplay = document.getElementById('error-display');
        const errorMessage = document.getElementById('error-message');
        
        if (errorDisplay && errorMessage) {
            errorMessage.textContent = message;
            errorDisplay.classList.remove('d-none');
            
            // Add enhanced error actions if max retries reached
            if (maxRetriesReached) {
                this.addEnhancedErrorActions(errorDisplay);
            }
        }
        
        // Also show as notification for better visibility
        this.showNotification(message, 'error');
    }
    
    /**
     * Sprint 24: Add enhanced error action buttons
     */
    addEnhancedErrorActions(errorDisplay) {
        // Check if enhanced actions already exist
        let actionsContainer = errorDisplay.querySelector('.enhanced-error-actions');
        
        if (!actionsContainer) {
            actionsContainer = document.createElement('div');
            actionsContainer.className = 'enhanced-error-actions mt-2 d-flex gap-2 flex-wrap';
            
            actionsContainer.innerHTML = `
                <button class="btn btn-sm btn-outline-primary" onclick="patternDiscovery.loadPatterns(0)">
                    <i class="fas fa-redo me-1"></i>Try Again
                </button>
                <button class="btn btn-sm btn-outline-info" onclick="patternDiscovery.checkConnection()">
                    <i class="fas fa-wifi me-1"></i>Check Connection
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="patternDiscovery.resetToDefaults()">
                    <i class="fas fa-undo me-1"></i>Reset Filters
                </button>
                <button class="btn btn-sm btn-outline-warning" onclick="patternDiscovery.showTroubleshooting()">
                    <i class="fas fa-question-circle me-1"></i>Help
                </button>
            `;
            
            errorDisplay.appendChild(actionsContainer);
        }
    }
    
    /**
     * Sprint 24: Check network connection and API availability
     */
    async checkConnection() {
        this.showNotification('Checking connection...', 'info');
        
        try {
            // Test basic connectivity
            const startTime = performance.now();
            const response = await fetch('/api/health', { 
                method: 'HEAD',
                cache: 'no-cache'
            });
            const responseTime = Math.round(performance.now() - startTime);
            
            if (response.ok) {
                this.showNotification(`Connection OK (${responseTime}ms response time)`, 'success');
            } else {
                this.showNotification(`Server responding but API may be down (HTTP ${response.status})`, 'warning');
            }
        } catch (error) {
            this.showNotification('No network connection detected. Please check your internet connection.', 'error');
        }
    }
    
    /**
     * Sprint 24: Reset all filters to defaults and reload
     */
    resetToDefaults() {
        this.clearFilters();
        this.hideError();
        this.showNotification('Filters reset to defaults', 'info');
        
        // Try loading again with defaults
        setTimeout(() => {
            this.loadPatterns(0);
        }, 1000);
    }
    
    /**
     * Sprint 24: Show troubleshooting help dialog
     */
    showTroubleshooting() {
        const troubleshootingSteps = `
        <div class="text-start">
            <h6>Troubleshooting Steps:</h6>
            <ol class="small">
                <li><strong>Check your internet connection</strong><br>
                    Make sure you're connected to the internet and can access other websites.</li>
                
                <li><strong>Refresh the page</strong><br>
                    Sometimes a simple page refresh can resolve temporary issues.</li>
                
                <li><strong>Clear your browser cache</strong><br>
                    Old cached data might be causing problems. Try clearing your browser cache.</li>
                
                <li><strong>Check your filters</strong><br>
                    Very restrictive filters might return no results. Try resetting to defaults.</li>
                
                <li><strong>Server maintenance</strong><br>
                    The pattern service might be temporarily down for maintenance.</li>
                
                <li><strong>Contact support</strong><br>
                    If problems persist, contact technical support with the error details.</li>
            </ol>
            
            <div class="mt-3 p-2 rounded" style="background-color: var(--color-background-secondary); border: 1px solid var(--color-border-primary);">
                <strong>Technical Details:</strong><br>
                <small class="text-muted">
                    • API Base URL: ${this.apiBaseUrl}<br>
                    • Last Attempt: ${new Date().toLocaleString()}<br>
                    • Browser: ${navigator.userAgent.split(' ')[0]}
                </small>
            </div>
        </div>`;
        
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Troubleshooting Help',
                html: troubleshootingSteps,
                icon: 'info',
                width: 600,
                showCloseButton: true,
                focusConfirm: false,
                confirmButtonText: 'Got it!',
                customClass: {
                    popup: 'text-start'
                }
            });
        } else {
            alert('Troubleshooting: Check your internet connection and try refreshing the page.');
        }
    }
    
    showNotification(message, type = 'info') {
        // Use SweetAlert2 which is already loaded
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Pattern Alert',
                text: message,
                icon: type,
                timer: 3000,
                timerProgressBar: true,
                showConfirmButton: false,
                position: 'top-end',
                toast: true
            });
        }
    }
    
    
    clearFilters() {
        this.filters = {
            universe: 'sp500',
            confidence_min: 0.7,
            limit: 100,
            pattern_types: [], // Sprint 24: Clear pattern type filters
            symbols: [], // Sprint 24: Clear symbol filters
            sector: 'all' // Sprint 24: Clear sector filter
        };
        
        // Reset UI elements
        const universeFilter = document.getElementById('universe-filter');
        const confidenceFilter = document.getElementById('confidence-filter');
        const confidenceValue = document.getElementById('confidence-value');
        const limitFilter = document.getElementById('limit-filter');
        const patternTypes = document.querySelectorAll('.pattern-type-filter');
        
        if (universeFilter) universeFilter.value = this.filters.universe;
        if (confidenceFilter) confidenceFilter.value = this.filters.confidence_min;
        if (confidenceValue) confidenceValue.textContent = '70%';
        if (limitFilter) limitFilter.value = this.filters.limit;
        
        patternTypes.forEach(checkbox => checkbox.checked = false);
        
        // Sprint 24: Reset symbol search and sector filter
        const symbolSearch = document.getElementById('symbol-search');
        const sectorFilter = document.getElementById('sector-filter');
        
        if (symbolSearch) symbolSearch.value = '';
        if (sectorFilter) sectorFilter.value = 'all';
        this.renderSelectedSymbols(); // Clear selected symbols display
        this.hideSuggestions(); // Hide any open suggestions
        
        // Sprint 24: Reset pattern type filters and clear filtered results
        this.filteredPatterns = null;
        this.updatePatternTypeVisualFeedback();
        
        // Sprint 24: Reset table sorting
        this.resetSorting();
        
        // Update filter count in retractable filter controller
        this.updateFilterCount();
        
        this.loadPatterns();
    }
    
    /**
     * Filter patterns by watchlist symbols (Sprint 21 Integration)
     */
    filterByWatchlist(watchlistId) {
        if (!window.watchlistManager) {
            console.warn('Watchlist manager not available');
            return;
        }
        
        const watchlist = window.watchlistManager.getWatchlist(watchlistId);
        if (!watchlist) {
            console.warn(`Watchlist ${watchlistId} not found`);
            return;
        }
        
        
        // Filter existing patterns
        this.filteredPatterns = this.patterns.filter(pattern => 
            watchlist.symbols.includes(pattern.symbol)
        );
        
        // Update display
        this.renderPatterns();
        this.updatePatternCount();
        
        // Show filter status
        this.showNotification(
            `Filtered by ${watchlist.name}: ${this.filteredPatterns.length} patterns`, 
            'info'
        );
    }
    
    /**
     * Clear watchlist filter and show all patterns
     */
    clearWatchlistFilter() {
        this.filteredPatterns = null;
        this.renderPatterns();
        this.updatePatternCount();
        this.showNotification('Showing all patterns', 'info');
    }
    
    /**
     * Sprint 24: Get patterns for display with all filters applied (pattern types, symbols, sector)
     */
    getPatternsForDisplay() {
        let patterns = this.filteredPatterns || this.patterns;
        
        // Apply symbol filter
        if (this.filters.symbols && this.filters.symbols.length > 0) {
            patterns = patterns.filter(pattern => 
                this.filters.symbols.includes(pattern.symbol)
            );
        }
        
        // Apply sector filter
        if (this.filters.sector && this.filters.sector !== 'all') {
            patterns = patterns.filter(pattern => {
                // Mock sector mapping for demonstration
                const symbolSectorMap = this.getSymbolSectorMap();
                const patternSector = symbolSectorMap[pattern.symbol];
                return patternSector === this.filters.sector;
            });
        }
        
        return patterns;
    }
    
    /**
     * ⚠️ CRITICAL TECHNICAL DEBT - REMOVE BEFORE PRODUCTION ⚠️
     * Sprint 24: Get symbol to sector mapping for sector filtering
     * 
     * TODO: Replace with real symbol metadata from database/API
     * Required: Use actual sector classifications from symbol data
     * Impact: Sector filtering only works for 30+ hardcoded symbols
     */
    getSymbolSectorMap() {
        // ⚠️ HARDCODED SECTOR MAPPING - REPLACE WITH REAL DATA ⚠️
        return {
            'AAPL': 'technology',
            'GOOGL': 'technology', 
            'MSFT': 'technology',
            'TSLA': 'consumer-discretionary',
            'AMZN': 'consumer-discretionary',
            'META': 'technology',
            'NVDA': 'technology',
            'JPM': 'financials',
            'JNJ': 'healthcare',
            'V': 'financials',
            'WMT': 'consumer-staples',
            'PG': 'consumer-staples',
            'UNH': 'healthcare',
            'HD': 'consumer-discretionary',
            'BAC': 'financials',
            'MA': 'financials',
            'DIS': 'communication',
            'NFLX': 'communication',
            'CRM': 'technology',
            'ORCL': 'technology',
            'PFE': 'healthcare',
            'KO': 'consumer-staples',
            'PEP': 'consumer-staples',
            'ADBE': 'technology',
            'CMCSA': 'communication',
            'XOM': 'energy',
            'CVX': 'energy',
            'NEE': 'utilities',
            'SO': 'utilities',
            'CAT': 'industrials',
            'BA': 'industrials',
            'FCX': 'materials',
            'NEM': 'materials',
            'AMT': 'real-estate',
            'PLD': 'real-estate'
        };
    }
}

// Initialize Pattern Discovery Service globally
window.patternDiscovery = new PatternDiscoveryService();