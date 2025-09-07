/**
 * Pattern Discovery Service - TickStock.ai
 * Sprint 20 Phase 2: UI Layer for Pattern Discovery Dashboard
 * 
 * Integrates with existing TickStock JavaScript architecture
 * Consumes Sprint 19 Pattern Discovery APIs
 * Uses established Bootstrap + jQuery patterns
 */

class PatternDiscoveryService {
    constructor() {
        this.apiBaseUrl = '/api';
        this.patterns = [];
        this.filters = {
            universe: 'sp500',
            confidence_min: 0.7,
            limit: 100
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
        console.log('Initializing Pattern Discovery Service');
        this.setupWebSocket();
        this.loadPatternDefinitions().then(() => {
            this.renderUI();
            this.loadPatterns();
        });
        
        // Auto-refresh every 30 seconds
        setInterval(() => this.loadPatterns(), 30000);
    }

    /**
     * Sprint 22: Load pattern definitions dynamically from Pattern Registry API
     */
    async loadPatternDefinitions() {
        try {
            console.log('Loading pattern definitions from Pattern Registry...');
            const response = await fetch('/api/patterns/definitions');
            
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
                
                console.log(`Pattern Discovery: Loaded ${this.availablePatterns.length} pattern definitions:`, this.availablePatterns);
            } else {
                throw new Error('Invalid pattern definitions response format');
            }
            
        } catch (error) {
            console.warn('Failed to load pattern definitions from API, using fallback:', error);
            this.availablePatterns = ['WeeklyBO', 'DailyBO', 'Doji', 'Hammer', 'ShootingStar', 'Engulfing'];
            this.availablePatterns.forEach(name => {
                this.patternDefinitions.set(name, {
                    name: name,
                    short_description: `${name} Pattern`,
                    enabled: true
                });
            });
        }
    }
    
    setupWebSocket() {
        if (typeof io !== 'undefined') {
            this.socket = io();
            
            this.socket.on('pattern_alert', (data) => {
                console.log('New pattern alert:', data);
                this.handleNewPattern(data);
                this.showNotification(`New ${data.event.data.pattern} pattern on ${data.event.data.symbol}`, 'success');
            });
            
            this.socket.on('connect', () => {
                console.log('WebSocket connected to Pattern Discovery');
                this.updateConnectionStatus(true);
            });
            
            this.socket.on('disconnect', () => {
                console.log('WebSocket disconnected from Pattern Discovery');
                this.updateConnectionStatus(false);
            });
        }
    }
    
    renderUI() {
        const contentArea = document.getElementById('pattern-discovery-content');
        if (!contentArea) return;
        
        contentArea.innerHTML = `
            <div class="pattern-discovery-dashboard">
                <!-- Header -->
                <div class="d-flex justify-content-between align-items-center mb-4 p-3 bg-light rounded">
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
                        <button id="test-alert-btn" class="btn btn-outline-warning btn-sm me-3">
                            <i class="fas fa-bell me-1"></i>
                            Test Alert
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
                <div class="row">
                    <!-- Filters -->
                    <div class="col-lg-3 col-md-4 mb-4">
                        <div class="card h-100">
                            <div class="card-header bg-primary text-white">
                                <h5 class="card-title mb-0">
                                    <i class="fas fa-filter me-2"></i>
                                    Filters
                                </h5>
                            </div>
                            <div class="card-body">
                                <!-- Watchlist Panel Container -->
                                <div id="watchlist-panel" class="mb-3">
                                    <!-- Watchlist management will be rendered here -->
                                </div>
                                
                                <!-- Filter Presets Panel Container -->
                                <div id="filter-presets-panel" class="mb-3">
                                    <!-- Filter presets will be rendered here -->
                                </div>
                                
                                <div id="pattern-filters">
                                    <!-- Filters will be rendered here -->
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Results -->
                    <div class="col-lg-9 col-md-8">
                        <div class="card h-100">
                            <div class="card-header bg-white border-bottom">
                                <h5 class="card-title mb-0">
                                    <i class="fas fa-table me-2"></i>
                                    Pattern Results
                                    <small class="text-muted ms-2" id="live-indicator">Live Data</small>
                                </h5>
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
                                        <thead class="bg-light sticky-top">
                                            <tr>
                                                <th>Symbol</th>
                                                <th>Pattern</th>
                                                <th>Confidence</th>
                                                <th>Price</th>
                                                <th>Change</th>
                                                <th>RS</th>
                                                <th>Volume</th>
                                                <th>Detected</th>
                                                <th>Actions</th>
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
            </div>
        `;
        
        this.renderFilters();
        this.setupEventHandlers();
        
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
        const filtersContainer = document.getElementById('pattern-filters');
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
        
        // Test alert button
        const testAlertBtn = document.getElementById('test-alert-btn');
        if (testAlertBtn) {
            testAlertBtn.addEventListener('click', () => this.testAlert());
        }
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
    }
    
    async loadPatterns() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading(true);
        this.hideError();
        
        try {
            const params = new URLSearchParams();
            Object.entries(this.filters).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    params.append(key, value.toString());
                }
            });
            
            const response = await fetch(`${this.apiBaseUrl}/patterns/scan?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.patterns = data.patterns || [];
            this.renderPatterns();
            this.updatePatternCount();
            
        } catch (error) {
            console.error('Failed to load patterns:', error);
            this.showError(error.message);
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
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
        }
    }
    
    renderPatternRow(pattern) {
        const changeClass = pattern.change_percent >= 0 ? 'text-success' : 'text-danger';
        const changeIcon = pattern.change_percent >= 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down';
        
        return `
            <tr data-symbol="${pattern.symbol}">
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
                <td>
                    <small class="text-muted">${this.formatTime(pattern.timestamp)}</small>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary add-to-watchlist-btn" 
                            data-symbol="${pattern.symbol}" 
                            title="Add ${pattern.symbol} to watchlist">
                        <i class="fas fa-plus"></i>
                    </button>
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
    
    showLoading(show) {
        const spinner = document.getElementById('loading-spinner');
        const refreshBtn = document.getElementById('refresh-btn');
        const refreshIcon = refreshBtn?.querySelector('.fa-sync-alt');
        
        if (spinner) {
            spinner.classList.toggle('d-none', !show);
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
    
    async testAlert() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/patterns/simulate-alert`);
            if (response.ok) {
                const data = await response.json();
                console.log('Test alert triggered:', data);
                this.showNotification('Test alert sent! Check for incoming pattern alert.', 'info');
            }
        } catch (error) {
            console.error('Failed to trigger test alert:', error);
            this.showNotification('Failed to send test alert', 'error');
        }
    }
    
    clearFilters() {
        this.filters = {
            universe: 'sp500',
            confidence_min: 0.7,
            limit: 100
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
        
        console.log(`Filtering patterns by watchlist: ${watchlist.name} (${watchlist.symbols.length} symbols)`);
        
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
     * Get patterns for display (filtered or all)
     */
    getPatternsForDisplay() {
        return this.filteredPatterns || this.patterns;
    }
}

// Initialize Pattern Discovery Service globally
window.patternDiscovery = new PatternDiscoveryService();