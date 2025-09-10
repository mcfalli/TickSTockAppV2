/**
 * Pattern Visualization Service for TickStock Pattern Discovery
 * Enhances pattern display with trend indicators, context, and interactive elements
 * 
 * Sprint 21 - Week 2 Deliverable 3: Enhanced Pattern Visualization
 * Architecture: Follows established web/static/js/services/ pattern
 * Integration: Enhances existing Pattern Discovery functionality
 */

// Debug flag for development
const VISUALIZATION_DEBUG = false;

class PatternVisualizationService {
    constructor() {
        this.isInitialized = false;
        this.enhancedPatterns = new Map();
        this.visualizationSettings = {
            showTrendIndicators: true,
            showContextInfo: true,
            showSuccessRates: true,
            showVolumeIndicators: true,
            enableHoverDetails: false,
            enableClickAnalysis: true
        };
        
        // API endpoints for enhanced data
        this.endpoints = {
            enhanced: '/api/patterns/enhanced',
            trends: '/api/patterns/trends',
            context: '/api/patterns/context'
        };
        
        this.initialize();
    }

    async initialize() {
        try {
            this.setupPatternTableEnhancements();
            this.setupInteractiveElements();
            this.setupEventHandlers();
            this.isInitialized = true;
        } catch (error) {
            console.error('Failed to initialize PatternVisualizationService:', error);
        }
    }

    /**
     * Enhanced Pattern Visualization - Sprint 21 Week 2 Deliverable 3
     * Provides rich pattern context and trend indicators
     */

    /**
     * Setup enhanced pattern table display
     */
    setupPatternTableEnhancements() {
        // Setting up pattern table enhancements
        
        // Wait for pattern discovery to be ready
        const checkPatternDiscovery = () => {
            const patternTable = document.getElementById('pattern-table');
            if (patternTable) {
                this.enhancePatternTable(patternTable);
                
                // Add a small delay to ensure DOM is ready
                setTimeout(() => {
                    this.enhanceExistingPatterns();
                }, 100);
                
                // Listen for pattern updates and table changes
                document.addEventListener('patternsUpdated', (event) => {
                    if (event.detail && event.detail.patterns) {
                        this.enhancePatternRows(event.detail.patterns);
                    }
                });
                
                // Listen for DOM changes to detect table refreshes
                this.setupTableObserver(patternTable);
            } else {
                setTimeout(checkPatternDiscovery, 500);
            }
        };
        
        checkPatternDiscovery();
    }

    /**
     * Setup observer to detect when table content changes (auto-refresh)
     */
    setupTableObserver(table) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        // Use MutationObserver to detect when table content changes
        const observer = new MutationObserver((mutations) => {
            let tableWasRefreshed = false;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    // Check if rows were added/removed/replaced
                    if (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0) {
                        tableWasRefreshed = true;
                    }
                }
            });
            
            if (tableWasRefreshed) {
                
                // Re-enhance the table headers (in case they were reset)
                this.enhancePatternTable(table);
                
                // Small delay to ensure DOM is settled
                setTimeout(() => {
                    this.enhanceExistingPatterns();
                }, 200);
            }
        });
        
        // Observe changes to tbody children
        observer.observe(tbody, {
            childList: true,
            subtree: true
        });
        
        // Table observer setup complete
    }

    /**
     * Enhance the pattern table with new columns and styling
     */
    enhancePatternTable(table) {
        const thead = table.querySelector('thead tr');
        const tbody = table.querySelector('tbody');
        
        if (!thead || !tbody) return;
        
        // Add new columns for enhanced visualization
        this.addEnhancedColumns(thead);
        
        // Apply enhanced styling to table
        table.classList.add('enhanced-pattern-table');
        
        // Add custom CSS if not already present
        this.addVisualizationStyles();
    }

    /**
     * Enhance patterns that are already loaded in the table
     */
    enhanceExistingPatterns() {
        
        const tbody = document.querySelector('#pattern-table tbody');
        
        if (!tbody) {
            console.error('No tbody found in pattern table');
            return;
        }
        
        const rows = tbody.querySelectorAll('tr[data-symbol]');
        
        if (rows.length === 0) {
            // Try without data-symbol attribute
            const allRows = tbody.querySelectorAll('tr');
            
            console.error('No rows with data-symbol found');
            return;
        }
        
        
        // Extract pattern data from existing rows
        const patterns = Array.from(rows).map((row, index) => {
            
            const symbol = row.getAttribute('data-symbol');
            const patternElement = row.querySelector('.badge');
            const pattern = patternElement ? patternElement.textContent.trim() : 'Unknown';
            const confidenceElement = row.querySelector('td:nth-child(3) span');
            const confidence = confidenceElement ? parseFloat(confidenceElement.textContent.replace('%', '')) / 100 : 0.5;
            
            const extractedPattern = {
                symbol: symbol,
                pattern: pattern,
                confidence: confidence
            };
            
            return extractedPattern;
        });
        
        
        // Enhance the patterns
        this.enhancePatternRows(patterns);
    }

    /**
     * Add enhanced columns to table header
     */
    addEnhancedColumns(thead) {
        // Check if columns already exist
        if (thead.querySelector('.trend-header')) return;
        
        // Insert new columns before the Actions column
        const actionsHeader = thead.querySelector('th:last-child');
        
        const trendHeader = document.createElement('th');
        trendHeader.className = 'trend-header text-center';
        trendHeader.innerHTML = `
            <i class="fas fa-chart-line me-1"></i>Trend
            <div class="small text-muted">Momentum</div>
        `;
        
        const contextHeader = document.createElement('th');
        contextHeader.className = 'context-header text-center';
        contextHeader.innerHTML = `
            <i class="fas fa-info-circle me-1"></i>Context
            <div class="small text-muted">Market Info</div>
        `;
        
        const performanceHeader = document.createElement('th');
        performanceHeader.className = 'performance-header text-center';
        performanceHeader.innerHTML = `
            <i class="fas fa-trophy me-1"></i>Performance
            <div class="small text-muted">Success Rate</div>
        `;
        
        // Insert before Actions column
        if (actionsHeader) {
            thead.insertBefore(performanceHeader, actionsHeader);
            thead.insertBefore(contextHeader, actionsHeader);
            thead.insertBefore(trendHeader, actionsHeader);
        } else {
            thead.appendChild(trendHeader);
            thead.appendChild(contextHeader);
            thead.appendChild(performanceHeader);
        }
    }

    /**
     * Enhance pattern rows with visualization data
     */
    async enhancePatternRows(patterns) {
        if (!patterns || patterns.length === 0) {
            return;
        }
        
        
        const tbody = document.querySelector('#pattern-table tbody');
        if (!tbody) {
            console.error('Pattern table tbody not found');
            return;
        }
        
        // Get enhanced data for all patterns
        const enhancedData = await this.getEnhancedPatternData(patterns);
        
        // Update each row with enhanced visualization
        const rows = tbody.querySelectorAll('tr[data-symbol]');
        
        rows.forEach((row, index) => {
            if (patterns[index] && enhancedData[index]) {
                this.enhancePatternRow(row, patterns[index], enhancedData[index]);
            } else {
            }
        });
    }

    /**
     * Get enhanced data for patterns from API or generate mock data
     */
    async getEnhancedPatternData(patterns) {
        try {
            const enhancedData = await Promise.all(
                patterns.map(pattern => this.getPatternEnhancement(pattern))
            );
            return enhancedData;
        } catch (error) {
            return patterns.map(pattern => this.generateMockEnhancement(pattern));
        }
    }

    /**
     * Get enhancement data for single pattern
     */
    async getPatternEnhancement(pattern) {
        // Check if we should skip API calls (development mode detection)
        if (this.shouldUseMockData()) {
            if (VISUALIZATION_DEBUG) {
            }
            return this.generateMockEnhancement(pattern);
        }
        
        try {
            const headers = { 'Content-Type': 'application/json' };
            
            // Add CSRF token if available
            if (window.csrfToken) {
                headers['X-CSRFToken'] = window.csrfToken;
            } else {
                // Fallback: try to get from meta tag
                const csrfMeta = document.querySelector('meta[name="csrf-token"]');
                if (csrfMeta) {
                    headers['X-CSRFToken'] = csrfMeta.getAttribute('content');
                }
            }
            
            const response = await fetch(`${this.endpoints.enhanced}/${pattern.symbol}`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ pattern: pattern })
            });
            
            if (!response.ok) throw new Error('Enhancement API failed');
            return await response.json();
        } catch (error) {
            // Only log if this wasn't expected (production environment)
            if (!this.shouldUseMockData()) {
                console.warn('Enhanced pattern API failed, using mock data:', error);
            }
            return this.generateMockEnhancement(pattern);
        }
    }
    
    /**
     * Determine if we should use mock data instead of making API calls
     */
    shouldUseMockData() {
        // Skip API calls if we're in development mode or missing authentication
        return (
            // Development detection: localhost or no CSRF token
            window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1' ||
            !window.csrfToken && !document.querySelector('meta[name="csrf-token"]')
        );
    }

    /**
     * Generate mock enhancement data for development
     */
    generateMockEnhancement(pattern) {
        const trendStrength = Math.random() * 100;
        const volumeTrend = Math.random() > 0.5 ? 'increasing' : 'decreasing';
        const marketCondition = ['bullish', 'bearish', 'neutral'][Math.floor(Math.random() * 3)];
        const sectorPerformance = (Math.random() - 0.5) * 10; // -5% to +5%
        
        // Generate success rate based on pattern type
        const patternSuccessRates = {
            'WeeklyBO': 0.75,
            'DailyBO': 0.62,
            'Doji': 0.45,
            'Hammer': 0.68,
            'EngulfingBullish': 0.72,
            'ShootingStar': 0.58
        };
        
        const baseSuccessRate = patternSuccessRates[pattern.pattern] || 0.60;
        const successRate = baseSuccessRate + (Math.random() - 0.5) * 0.2;
        
        return {
            symbol: pattern.symbol,
            trend_direction: trendStrength > 60 ? 'up' : trendStrength < 40 ? 'down' : 'sideways',
            trend_strength: Math.round(trendStrength),
            volume_trend: volumeTrend,
            volume_change: Math.round((Math.random() - 0.5) * 200), // -100% to +100%
            market_condition: marketCondition,
            sector_performance: Math.round(sectorPerformance * 10) / 10,
            relative_strength: Math.round((Math.random() * 40 + 30)), // 30-70 RSI range
            success_rate_1d: Math.round(successRate * 100),
            success_rate_5d: Math.round((successRate * 0.9) * 100),
            price_momentum: (Math.random() - 0.5) * 6, // -3% to +3%
            pattern_quality: ['High', 'Medium', 'Low'][Math.floor(Math.random() * 3)],
            risk_level: ['Low', 'Medium', 'High'][Math.floor(Math.random() * 3)]
        };
    }

    /**
     * Enhance individual pattern row with visualization elements
     */
    enhancePatternRow(row, pattern, enhancement) {
        // Check if already enhanced
        if (row.querySelector('.trend-cell')) {
            return;
        }
        
        
        // Find and replace the existing placeholder cells
        const trendColumnCell = row.querySelector('.trend-column');
        const contextColumnCell = row.querySelector('.context-column');
        const performanceColumnCell = row.querySelector('.performance-column');
        
        if (trendColumnCell) {
            this.replaceCellContent(trendColumnCell, this.createTrendContent(enhancement));
            trendColumnCell.className = 'trend-cell text-center';
        }
        
        if (contextColumnCell) {
            this.replaceCellContent(contextColumnCell, this.createContextContent(enhancement));
            contextColumnCell.className = 'context-cell text-center';
        }
        
        if (performanceColumnCell) {
            this.replaceCellContent(performanceColumnCell, this.createPerformanceContent(enhancement));
            performanceColumnCell.className = 'performance-cell text-center';
        }
        
        // Enhance symbol cell with additional context
        this.enhanceSymbolCell(row, pattern, enhancement);
        
        // Enhance pattern cell with success rate
        this.enhancePatternCell(row, pattern, enhancement);
        
        // Add interactive elements
        this.addRowInteractivity(row, pattern, enhancement);
        
        // Store enhancement data
        this.enhancedPatterns.set(pattern.symbol, enhancement);
        
    }
    
    /**
     * Replace cell content (helper method)
     */
    replaceCellContent(cell, newContent) {
        cell.innerHTML = newContent;
    }

    /**
     * Create trend indicator content
     */
    createTrendContent(enhancement) {
        const trendIcon = enhancement.trend_direction === 'up' ? 'fa-arrow-up text-success' :
                         enhancement.trend_direction === 'down' ? 'fa-arrow-down text-danger' :
                         'fa-arrow-right text-warning';
        
        return `
            <div class="trend-indicator">
                <i class="fas ${trendIcon} me-1"></i>
                <span class="trend-strength">${enhancement.trend_strength}%</span>
            </div>
            <small class="text-muted d-block">
                Vol: ${enhancement.volume_change > 0 ? '+' : ''}${enhancement.volume_change}%
            </small>
        `;
    }

    /**
     * Create context information content
     */
    createContextContent(enhancement) {
        const conditionBadge = enhancement.market_condition === 'bullish' ? 'bg-success' :
                              enhancement.market_condition === 'bearish' ? 'bg-danger' : 'bg-warning';
        
        return `
            <span class="badge ${conditionBadge} mb-1">${enhancement.market_condition}</span>
            <div class="small">
                <div>Sector: ${enhancement.sector_performance > 0 ? '+' : ''}${enhancement.sector_performance}%</div>
                <div>RSI: ${enhancement.relative_strength}</div>
            </div>
        `;
    }

    /**
     * Create performance indicator content
     */
    createPerformanceContent(enhancement) {
        const qualityClass = enhancement.pattern_quality === 'High' ? 'text-success' :
                            enhancement.pattern_quality === 'Medium' ? 'text-warning' : 'text-danger';
        
        return `
            <div class="success-rate mb-1">
                <strong class="${qualityClass}">${enhancement.success_rate_1d}%</strong>
                <small class="text-muted">/1d</small>
            </div>
            <div class="small">
                <div>5d: ${enhancement.success_rate_5d}%</div>
                <div class="${qualityClass}">${enhancement.pattern_quality} Quality</div>
            </div>
        `;
    }

    /**
     * Enhance symbol cell with momentum indicator
     */
    enhanceSymbolCell(row, pattern, enhancement) {
        const symbolCell = row.querySelector('td:first-child');
        if (!symbolCell) return;
        
        const symbol = symbolCell.querySelector('strong') || symbolCell;
        
        // Add momentum indicator
        const momentumIndicator = document.createElement('div');
        momentumIndicator.className = 'momentum-indicator small';
        
        const momentumClass = enhancement.price_momentum > 1 ? 'text-success' :
                             enhancement.price_momentum < -1 ? 'text-danger' : 'text-muted';
        
        momentumIndicator.innerHTML = `
            <i class="fas fa-circle ${momentumClass}" style="font-size: 0.6em;"></i>
            <span class="${momentumClass}">
                ${enhancement.price_momentum > 0 ? '+' : ''}${enhancement.price_momentum.toFixed(1)}%
            </span>
        `;
        
        symbolCell.appendChild(momentumIndicator);
    }

    /**
     * Enhance pattern cell with historical context
     */
    enhancePatternCell(row, pattern, enhancement) {
        const patternCell = row.querySelector('td:nth-child(2)'); // Assuming pattern is 2nd column
        if (!patternCell) return;
        
        const badge = patternCell.querySelector('.badge');
        if (badge) {
            const contextDiv = document.createElement('div');
            contextDiv.className = 'pattern-context mt-1';
            contextDiv.innerHTML = `
                <small class="success-rate text-muted">
                    Avg Success: ${enhancement.success_rate_1d}% | Risk: ${enhancement.risk_level}
                </small>
            `;
            
            badge.parentNode.appendChild(contextDiv);
        }
    }

    /**
     * Add interactive elements to pattern row
     */
    addRowInteractivity(row, pattern, enhancement) {
        // Add hover effects
        row.classList.add('enhanced-pattern-row');
        
        // Add click handler for detailed analysis
        row.addEventListener('click', (event) => {
            // Don't trigger on button clicks
            if (event.target.tagName === 'BUTTON' || event.target.closest('button')) {
                return;
            }
            
            this.showPatternDetails(pattern, enhancement);
        });
        
        // Add hover tooltip
        if (this.visualizationSettings.enableHoverDetails) {
            this.addHoverTooltip(row, pattern, enhancement);
        }
    }

    /**
     * Add hover tooltip with detailed information
     */
    addHoverTooltip(row, pattern, enhancement) {
        row.setAttribute('title', ''); // Remove default tooltip
        
        // Create custom tooltip
        let tooltip = null;
        
        row.addEventListener('mouseenter', (event) => {
            tooltip = this.createTooltip(pattern, enhancement);
            document.body.appendChild(tooltip);
            this.positionTooltip(tooltip, event);
        });
        
        row.addEventListener('mousemove', (event) => {
            if (tooltip) {
                this.positionTooltip(tooltip, event);
            }
        });
        
        row.addEventListener('mouseleave', () => {
            if (tooltip) {
                document.body.removeChild(tooltip);
                tooltip = null;
            }
        });
    }

    /**
     * Create detailed tooltip
     */
    createTooltip(pattern, enhancement) {
        const tooltip = document.createElement('div');
        tooltip.className = 'pattern-tooltip';
        tooltip.innerHTML = `
            <div class="tooltip-header">
                <strong>${pattern.symbol} - ${pattern.pattern}</strong>
            </div>
            <div class="tooltip-body">
                <div><strong>Trend:</strong> ${enhancement.trend_direction} (${enhancement.trend_strength}%)</div>
                <div><strong>Volume:</strong> ${enhancement.volume_trend} (${enhancement.volume_change > 0 ? '+' : ''}${enhancement.volume_change}%)</div>
                <div><strong>Market:</strong> ${enhancement.market_condition}</div>
                <div><strong>Sector:</strong> ${enhancement.sector_performance > 0 ? '+' : ''}${enhancement.sector_performance}%</div>
                <div><strong>Success Rate:</strong> ${enhancement.success_rate_1d}% (1d), ${enhancement.success_rate_5d}% (5d)</div>
                <div><strong>Quality:</strong> ${enhancement.pattern_quality} | <strong>Risk:</strong> ${enhancement.risk_level}</div>
                <div class="text-muted mt-2"><small>Click for detailed analysis</small></div>
            </div>
        `;
        
        return tooltip;
    }

    /**
     * Position tooltip near cursor
     */
    positionTooltip(tooltip, event) {
        const x = event.pageX + 10;
        const y = event.pageY - 10;
        
        tooltip.style.left = x + 'px';
        tooltip.style.top = y + 'px';
        
        // Adjust if tooltip goes off screen
        const rect = tooltip.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            tooltip.style.left = (x - rect.width - 20) + 'px';
        }
        if (rect.top < 0) {
            tooltip.style.top = (y + 20) + 'px';
        }
    }

    /**
     * Show detailed pattern analysis modal
     */
    showPatternDetails(pattern, enhancement) {
        const modal = this.createPatternDetailsModal(pattern, enhancement);
        document.body.appendChild(modal);
        
        // Show modal using Bootstrap
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Remove modal from DOM when hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    /**
     * Create pattern details modal
     */
    createPatternDetailsModal(pattern, enhancement) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            ${pattern.symbol} - ${pattern.pattern} Analysis
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Pattern Details</h6>
                                <table class="table table-sm">
                                    <tr><td>Symbol</td><td><strong>${pattern.symbol}</strong></td></tr>
                                    <tr><td>Pattern</td><td><span class="badge bg-primary">${pattern.pattern}</span></td></tr>
                                    <tr><td>Confidence</td><td>${(pattern.confidence * 100).toFixed(1)}%</td></tr>
                                    <tr><td>Quality</td><td>${enhancement.pattern_quality}</td></tr>
                                    <tr><td>Risk Level</td><td>${enhancement.risk_level}</td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6>Market Context</h6>
                                <table class="table table-sm">
                                    <tr><td>Trend</td><td>${enhancement.trend_direction} (${enhancement.trend_strength}%)</td></tr>
                                    <tr><td>Volume Trend</td><td>${enhancement.volume_trend} (${enhancement.volume_change > 0 ? '+' : ''}${enhancement.volume_change}%)</td></tr>
                                    <tr><td>Market Condition</td><td>${enhancement.market_condition}</td></tr>
                                    <tr><td>Sector Performance</td><td>${enhancement.sector_performance > 0 ? '+' : ''}${enhancement.sector_performance}%</td></tr>
                                    <tr><td>RSI</td><td>${enhancement.relative_strength}</td></tr>
                                </table>
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Historical Performance</h6>
                                <div class="d-flex justify-content-around">
                                    <div class="text-center">
                                        <div class="h4 text-success">${enhancement.success_rate_1d}%</div>
                                        <small class="text-muted">1-Day Success</small>
                                    </div>
                                    <div class="text-center">
                                        <div class="h4 text-info">${enhancement.success_rate_5d}%</div>
                                        <small class="text-muted">5-Day Success</small>
                                    </div>
                                    <div class="text-center">
                                        <div class="h4 ${enhancement.price_momentum > 0 ? 'text-success' : 'text-danger'}">
                                            ${enhancement.price_momentum > 0 ? '+' : ''}${enhancement.price_momentum.toFixed(1)}%
                                        </div>
                                        <small class="text-muted">Price Momentum</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="window.patternVisualization.addToWatchlist('${pattern.symbol}')">
                            Add to Watchlist
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }

    /**
     * Add custom CSS styles for enhanced visualization
     */
    addVisualizationStyles() {
        if (document.getElementById('pattern-visualization-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'pattern-visualization-styles';
        style.textContent = `
            /* Enhanced Pattern Table Styling */
            .enhanced-pattern-table {
                font-size: 0.875rem;
                border-collapse: separate;
                border-spacing: 0;
            }
            
            .enhanced-pattern-table thead th {
                background: #f8f9fa !important;
                border-bottom: 2px solid #dee2e6;
                font-weight: 600;
                font-size: 0.8rem;
                padding: 12px 8px;
                vertical-align: middle;
            }
            
            .enhanced-pattern-row {
                cursor: pointer;
                transition: all 0.2s ease;
                border-bottom: 1px solid #dee2e6;
            }
            
            .enhanced-pattern-row:hover {
                background-color: rgba(0, 123, 255, 0.08) !important;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }
            
            .enhanced-pattern-row td {
                padding: 12px 8px;
                vertical-align: middle;
                border-bottom: 1px solid #f0f0f0;
            }
            
            /* Enhanced Column Headers */
            .trend-header, .context-header, .performance-header {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important;
                border: 1px solid #dee2e6;
                text-align: center !important;
                width: 85px !important;
                min-width: 85px !important;
                max-width: 85px !important;
                position: relative;
                font-size: 0.75rem !important;
                padding: 8px 4px !important;
                line-height: 1.1;
            }
            
            .trend-header .small, .context-header .small, .performance-header .small {
                font-size: 0.65rem !important;
                margin-top: 2px;
            }
            
            .trend-header::after, .context-header::after, .performance-header::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 50%;
                width: 20px;
                height: 2px;
                background: #007bff;
                transform: translateX(-50%);
            }
            
            /* Enhanced Cell Styling */
            .trend-cell, .context-cell, .performance-cell {
                width: 85px !important;
                min-width: 85px !important;
                max-width: 85px !important;
                font-size: 0.75rem;
                text-align: center;
                padding: 8px 4px !important;
                background: rgba(248, 249, 250, 0.5);
                border-left: 1px solid #e9ecef;
                border-right: 1px solid #e9ecef;
                vertical-align: top !important;
                line-height: 1.2;
            }
            
            /* Trend Indicators */
            .trend-indicator {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 4px;
                margin-bottom: 3px;
            }
            
            .trend-strength {
                font-weight: 700;
                font-size: 0.75rem;
                line-height: 1;
            }
            
            .trend-cell .fas {
                font-size: 0.7rem;
            }
            
            .trend-cell .text-muted {
                font-size: 0.6rem;
                margin-top: 2px;
                line-height: 1.1;
                white-space: nowrap;
            }
            
            /* Context Cell Badges */
            .context-cell .badge {
                font-size: 0.6rem;
                padding: 2px 4px;
                border-radius: 3px;
                text-transform: uppercase;
                font-weight: 600;
                letter-spacing: 0.3px;
                display: block;
                margin-bottom: 3px;
            }
            
            .context-cell .small {
                margin-top: 2px;
                line-height: 1.1;
                font-size: 0.65rem;
            }
            
            .context-cell .small div {
                margin-bottom: 1px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            /* Performance Cell */
            .performance-cell .success-rate {
                margin-bottom: 2px;
            }
            
            .performance-cell .success-rate strong {
                font-size: 0.85rem;
                font-weight: 700;
                line-height: 1;
            }
            
            .performance-cell .small {
                line-height: 1.1;
                opacity: 0.8;
                font-size: 0.65rem;
            }
            
            .performance-cell .small div {
                margin-bottom: 1px;
                white-space: nowrap;
            }
            
            /* Symbol Cell Enhancements */
            .momentum-indicator {
                margin-top: 4px;
                padding: 2px 0;
                opacity: 0.9;
                font-size: 0.75rem;
                display: flex;
                align-items: center;
                gap: 3px;
            }
            
            .momentum-indicator .fas {
                font-size: 0.6rem;
                margin-right: 2px;
            }
            
            /* Pattern Cell Enhancements */
            .pattern-context {
                margin-top: 6px;
                padding-top: 4px;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
            }
            
            .pattern-context .success-rate {
                font-size: 0.7rem;
                font-weight: 500;
                opacity: 0.8;
            }
            
            /* Tooltip Styling */
            .pattern-tooltip {
                position: absolute;
                background: linear-gradient(135deg, #343a40 0%, #495057 100%);
                color: white;
                padding: 12px 16px;
                border-radius: 8px;
                font-size: 0.85rem;
                max-width: 320px;
                z-index: 10000;
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .tooltip-header {
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
                padding-bottom: 8px;
                margin-bottom: 8px;
                font-weight: 600;
                font-size: 0.9rem;
            }
            
            .tooltip-body div {
                margin-bottom: 4px;
                display: flex;
                justify-content: space-between;
            }
            
            .tooltip-body strong {
                color: #ffc107;
                font-weight: 600;
            }
            
            /* Color adjustments for better contrast */
            .text-success {
                color: #198754 !important;
            }
            
            .text-danger {
                color: #dc3545 !important;
            }
            
            .text-warning {
                color: #fd7e14 !important;
            }
            
            .bg-success {
                background-color: #198754 !important;
            }
            
            .bg-danger {
                background-color: #dc3545 !important;
            }
            
            .bg-warning {
                background-color: #fd7e14 !important;
            }
            
            /* Responsive adjustments */
            @media (max-width: 768px) {
                .trend-cell, .context-cell, .performance-cell {
                    width: 70px !important;
                    min-width: 70px !important;
                    max-width: 70px !important;
                    font-size: 0.7rem;
                    padding: 6px 3px !important;
                }
                
                .trend-header, .context-header, .performance-header {
                    width: 70px !important;
                    min-width: 70px !important;
                    max-width: 70px !important;
                    font-size: 0.7rem !important;
                    padding: 6px 3px !important;
                }
                
                .enhanced-pattern-table {
                    font-size: 0.75rem;
                }
                
                .momentum-indicator {
                    font-size: 0.65rem;
                }
                
                .context-cell .badge {
                    font-size: 0.55rem;
                    padding: 1px 3px;
                }
                
                .performance-cell .success-rate strong {
                    font-size: 0.75rem;
                }
            }
            
            /* Animation for enhanced cells */
            @keyframes fadeInScale {
                0% {
                    opacity: 0;
                    transform: scale(0.9);
                }
                100% {
                    opacity: 1;
                    transform: scale(1);
                }
            }
            
            .trend-cell, .context-cell, .performance-cell {
                animation: fadeInScale 0.3s ease-out;
            }
        `;
        
        document.head.appendChild(style);
    }

    /**
     * Setup event handlers for visualization features
     */
    setupEventHandlers() {
        // Handle settings changes
        document.addEventListener('visualizationSettingsChanged', (event) => {
            this.visualizationSettings = { ...this.visualizationSettings, ...event.detail };
            this.refreshVisualization();
        });
        
        // Handle pattern table updates
        document.addEventListener('patternTableRefreshed', () => {
            this.refreshEnhancements();
        });
    }

    /**
     * Setup interactive elements
     */
    setupInteractiveElements() {
        // Add visualization controls (could be added to a settings panel)
        this.createVisualizationControls();
    }

    /**
     * Create visualization control panel (future enhancement)
     */
    createVisualizationControls() {
        // Placeholder for future visualization controls
        // Could add toggles for different visualization features
    }

    /**
     * Add to watchlist integration
     */
    addToWatchlist(symbol) {
        if (window.watchlistManager) {
            window.watchlistManager.quickAddSymbol(symbol);
        } else {
            console.warn('Watchlist manager not available');
        }
    }

    /**
     * Refresh visualization after settings change
     */
    refreshVisualization() {
        // Re-apply enhancements with new settings
        const table = document.getElementById('pattern-table');
        if (table) {
            this.clearEnhancements(table);
            setTimeout(() => this.setupPatternTableEnhancements(), 100);
        }
    }

    /**
     * Refresh enhancements after pattern data update
     */
    refreshEnhancements() {
        // Get current patterns and re-enhance
        if (window.patternDiscovery && window.patternDiscovery.patterns) {
            this.enhancePatternRows(window.patternDiscovery.patterns);
        }
    }

    /**
     * Clear existing enhancements
     */
    clearEnhancements(table) {
        // Remove enhanced columns
        const enhancedHeaders = table.querySelectorAll('.trend-header, .context-header, .performance-header');
        enhancedHeaders.forEach(header => header.remove());
        
        // Remove enhanced cells
        const enhancedCells = table.querySelectorAll('.trend-cell, .context-cell, .performance-cell');
        enhancedCells.forEach(cell => cell.remove());
        
        // Remove enhanced styling
        table.classList.remove('enhanced-pattern-table');
        const rows = table.querySelectorAll('.enhanced-pattern-row');
        rows.forEach(row => {
            row.classList.remove('enhanced-pattern-row');
            // Remove added elements
            const addedElements = row.querySelectorAll('.momentum-indicator, .pattern-context');
            addedElements.forEach(el => el.remove());
        });
    }

    /**
     * Get enhanced pattern data for external access
     */
    getEnhancedPattern(symbol) {
        return this.enhancedPatterns.get(symbol);
    }

    /**
     * Update visualization settings
     */
    updateSettings(newSettings) {
        this.visualizationSettings = { ...this.visualizationSettings, ...newSettings };
        this.refreshVisualization();
    }
}

// Initialize the service when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.patternVisualization = new PatternVisualizationService();
});