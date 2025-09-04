# Phase 3: Advanced Filtering & Search - Detailed Implementation Guide

**Date**: 2025-09-04  
**Sprint**: 18 - Phase 3 Implementation  
**Duration**: 2 weeks  
**Status**: Implementation Ready  
**Prerequisites**: Phase 2 complete (Basic UI operational)

## Phase Overview

Implement sophisticated filtering capabilities that allow traders to create complex multi-criteria searches, save filter combinations as presets, and perform advanced pattern discovery queries. This phase transforms the basic table into a powerful pattern discovery tool.

## Success Criteria

✅ **Filter Complexity**: Support 10+ simultaneous filter criteria with AND/OR logic  
✅ **Performance**: Complex queries execute in <100ms with proper debouncing  
✅ **User Experience**: Filter changes provide instant visual feedback  
✅ **Persistence**: Saved filter sets work across sessions  
✅ **Search**: Symbol autocomplete responds within 200ms  

## Implementation Tasks

### Task 3.1: Advanced Filter Panel Component (Days 1-4)

#### 3.1.1 Enhanced FilterPanel Class
**File**: `static/js/components/FilterPanel.js`

```javascript
class FilterPanel {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            onFilterChange: () => {},
            initialState: {},
            debounceDelay: 300,
            ...options
        };
        
        this.filterState = {
            pattern_types: [],
            timeframe: 'All',
            confidence_min: 0.5,
            rs_min: 0,
            rs_max: 10,
            vol_min: 0,
            vol_max: 20,
            rsi_min: 0,
            rsi_max: 100,
            price_min: 0,
            price_max: 10000,
            price_change_min: -50,
            price_change_max: 50,
            market_caps: [],
            sectors: [],
            symbols: [],
            time_range: 'last_4h',
            custom_date_start: null,
            custom_date_end: null,
            expiry_filter: 'active_only',
            logic_mode: 'AND', // AND or OR
            ...this.options.initialState
        };
        
        this.savedFilters = [];
        this.symbolCache = new Map();
        this.debounceTimer = null;
        
        this.init();
        this.loadSavedFilters();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="filter-panel">
                <!-- Filter Header -->
                <div class="filter-header">
                    <h3>🎛️ Pattern Filters</h3>
                    <div class="filter-actions">
                        <button class="filter-btn collapse-btn" id="collapse-filters">
                            <span class="collapse-icon">−</span>
                        </button>
                        <button class="filter-btn reset-btn" id="reset-filters" title="Reset All Filters">
                            🔄
                        </button>
                    </div>
                </div>
                
                <div class="filter-content" id="filter-content">
                    <!-- Quick Filter Presets -->
                    <div class="filter-section">
                        <h4>⚡ Quick Filters</h4>
                        <div class="quick-filters">
                            <button class="quick-filter" data-preset="high-momentum">High Momentum</button>
                            <button class="quick-filter" data-preset="volume-breakouts">Volume + Breakouts</button>
                            <button class="quick-filter" data-preset="daily-swings">Daily Swings</button>
                            <button class="quick-filter" data-preset="scalp-setups">Scalp Setups</button>
                        </div>
                    </div>
                    
                    <!-- Pattern Types -->
                    <div class="filter-section">
                        <h4>📊 Pattern Types</h4>
                        <div class="pattern-types">
                            ${this.renderPatternTypeCheckboxes()}
                        </div>
                    </div>
                    
                    <!-- Timeframe Selection -->
                    <div class="filter-section">
                        <h4>⏰ Timeframe</h4>
                        <div class="timeframe-selection">
                            ${this.renderTimeframeRadios()}
                        </div>
                    </div>
                    
                    <!-- Confidence Range -->
                    <div class="filter-section">
                        <h4>🎯 Confidence</h4>
                        <div class="confidence-slider">
                            <input type="range" id="confidence-slider" min="0.1" max="1.0" step="0.05" value="${this.filterState.confidence_min}">
                            <div class="confidence-display">
                                <span class="confidence-value">${Math.round(this.filterState.confidence_min * 100)}%</span>
                                <div class="confidence-visual">
                                    ${this.renderConfidenceStars(this.filterState.confidence_min)}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Advanced Indicators -->
                    <div class="filter-section">
                        <h4>📈 Technical Indicators</h4>
                        
                        <!-- Relative Strength Range -->
                        <div class="indicator-row">
                            <label>Relative Strength</label>
                            <div class="range-inputs">
                                <input type="number" id="rs-min" placeholder="Min" value="${this.filterState.rs_min}" step="0.1" min="0" max="10">
                                <span>to</span>
                                <input type="number" id="rs-max" placeholder="Max" value="${this.filterState.rs_max}" step="0.1" min="0" max="10">
                                <span class="range-suffix">x</span>
                            </div>
                            <div class="quick-rs-buttons">
                                <button class="quick-btn" data-rs="1.0">≥1.0x</button>
                                <button class="quick-btn" data-rs="1.2">≥1.2x</button>
                                <button class="quick-btn" data-rs="1.5">≥1.5x</button>
                                <button class="quick-btn" data-rs="2.0">≥2.0x</button>
                            </div>
                        </div>
                        
                        <!-- Volume Range -->
                        <div class="indicator-row">
                            <label>Relative Volume</label>
                            <div class="range-inputs">
                                <input type="number" id="vol-min" placeholder="Min" value="${this.filterState.vol_min}" step="0.1" min="0" max="20">
                                <span>to</span>
                                <input type="number" id="vol-max" placeholder="Max" value="${this.filterState.vol_max}" step="0.1" min="0" max="20">
                                <span class="range-suffix">x</span>
                            </div>
                            <div class="quick-vol-buttons">
                                <button class="quick-btn" data-vol="1.5">≥1.5x</button>
                                <button class="quick-btn" data-vol="2.0">≥2.0x</button>
                                <button class="quick-btn" data-vol="3.0">≥3.0x</button>
                                <button class="quick-btn" data-vol="5.0">≥5.0x</button>
                            </div>
                        </div>
                        
                        <!-- RSI Range -->
                        <div class="indicator-row">
                            <label>RSI Range</label>
                            <div class="dual-range-slider">
                                <input type="range" id="rsi-min-slider" min="0" max="100" value="${this.filterState.rsi_min}" step="1">
                                <input type="range" id="rsi-max-slider" min="0" max="100" value="${this.filterState.rsi_max}" step="1">
                                <div class="range-display">
                                    <span id="rsi-min-value">${this.filterState.rsi_min}</span> - 
                                    <span id="rsi-max-value">${this.filterState.rsi_max}</span>
                                </div>
                            </div>
                            <div class="rsi-presets">
                                <button class="quick-btn" data-rsi="oversold">Oversold (&lt;30)</button>
                                <button class="quick-btn" data-rsi="overbought">Overbought (&gt;70)</button>
                                <button class="quick-btn" data-rsi="neutral">Neutral (40-60)</button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Price Filters -->
                    <div class="filter-section">
                        <h4>💰 Price Filters</h4>
                        
                        <!-- Price Range -->
                        <div class="indicator-row">
                            <label>Price Range</label>
                            <div class="range-inputs">
                                <input type="number" id="price-min" placeholder="Min $" value="${this.filterState.price_min}" step="0.01" min="0">
                                <span>to</span>
                                <input type="number" id="price-max" placeholder="Max $" value="${this.filterState.price_max}" step="0.01" min="0">
                            </div>
                            <div class="price-presets">
                                <button class="quick-btn" data-price-range="penny">Penny (&lt;$5)</button>
                                <button class="quick-btn" data-price-range="small">Small ($5-50)</button>
                                <button class="quick-btn" data-price-range="mid">Mid ($50-200)</button>
                                <button class="quick-btn" data-price-range="large">Large (&gt;$200)</button>
                            </div>
                        </div>
                        
                        <!-- Price Change -->
                        <div class="indicator-row">
                            <label>Price Change %</label>
                            <div class="range-inputs">
                                <input type="number" id="change-min" placeholder="Min %" value="${this.filterState.price_change_min}" step="0.1">
                                <span>to</span>
                                <input type="number" id="change-max" placeholder="Max %" value="${this.filterState.price_change_max}" step="0.1">
                            </div>
                            <div class="change-presets">
                                <button class="quick-btn" data-change="gainers">Gainers (&gt;1%)</button>
                                <button class="quick-btn" data-change="big-gainers">Big Gainers (&gt;5%)</button>
                                <button class="quick-btn" data-change="losers">Losers (&lt;-1%)</button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Symbol Selection -->
                    <div class="filter-section">
                        <h4>🔍 Symbol Selection</h4>
                        
                        <!-- Symbol Search -->
                        <div class="symbol-search">
                            <input type="text" id="symbol-search" placeholder="Search symbols..." autocomplete="off">
                            <div class="search-results" id="symbol-search-results"></div>
                        </div>
                        
                        <!-- Selected Symbols -->
                        <div class="selected-symbols" id="selected-symbols">
                            ${this.renderSelectedSymbols()}
                        </div>
                        
                        <!-- Sector Filters -->
                        <div class="sector-filters">
                            <label>Sectors</label>
                            <div class="sector-checkboxes">
                                ${this.renderSectorCheckboxes()}
                            </div>
                        </div>
                        
                        <!-- Market Cap Filters -->
                        <div class="market-cap-filters">
                            <label>Market Cap</label>
                            <div class="market-cap-checkboxes">
                                <label><input type="checkbox" value="large" ${this.filterState.market_caps.includes('large') ? 'checked' : ''}> Large Cap (&gt;$10B)</label>
                                <label><input type="checkbox" value="mid" ${this.filterState.market_caps.includes('mid') ? 'checked' : ''}> Mid Cap ($2B-10B)</label>
                                <label><input type="checkbox" value="small" ${this.filterState.market_caps.includes('small') ? 'checked' : ''}> Small Cap (&lt;$2B)</label>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Time Range -->
                    <div class="filter-section">
                        <h4>🕒 Time Range</h4>
                        <div class="time-range-selection">
                            <select id="time-range-select">
                                <option value="last_1h">Last Hour</option>
                                <option value="last_4h" selected>Last 4 Hours</option>
                                <option value="today">Today</option>
                                <option value="last_3d">Last 3 Days</option>
                                <option value="last_week">Last Week</option>
                                <option value="custom">Custom Range</option>
                            </select>
                            
                            <div class="custom-date-range" id="custom-date-range" style="display: none;">
                                <input type="datetime-local" id="date-start">
                                <span>to</span>
                                <input type="datetime-local" id="date-end">
                            </div>
                        </div>
                    </div>
                    
                    <!-- Filter Logic -->
                    <div class="filter-section">
                        <h4>🔗 Filter Logic</h4>
                        <div class="logic-mode">
                            <label>
                                <input type="radio" name="logic-mode" value="AND" ${this.filterState.logic_mode === 'AND' ? 'checked' : ''}>
                                AND (All conditions must match)
                            </label>
                            <label>
                                <input type="radio" name="logic-mode" value="OR" ${this.filterState.logic_mode === 'OR' ? 'checked' : ''}>
                                OR (Any condition can match)
                            </label>
                        </div>
                    </div>
                    
                    <!-- Saved Filters -->
                    <div class="filter-section">
                        <h4>💾 Saved Filters</h4>
                        <div class="saved-filters" id="saved-filters">
                            ${this.renderSavedFilters()}
                        </div>
                        <div class="save-filter-controls">
                            <input type="text" id="filter-name" placeholder="Filter name...">
                            <button class="save-filter-btn" id="save-filter">Save Current</button>
                        </div>
                    </div>
                    
                    <!-- Apply/Reset Actions -->
                    <div class="filter-actions-bottom">
                        <button class="apply-filters-btn" id="apply-filters">Apply Filters</button>
                        <button class="reset-all-btn" id="reset-all-filters">Reset All</button>
                    </div>
                </div>
            </div>
        `;
        
        this.bindEvents();
        this.updateUI();
    }
    
    renderPatternTypeCheckboxes() {
        const patternTypes = [
            { value: 'Breakout', label: 'Breakouts', count: 0 },
            { value: 'Volume', label: 'Volume Spikes', count: 0 },
            { value: 'Trendline', label: 'Trendlines', count: 0 },
            { value: 'Gap', label: 'Gap Plays', count: 0 },
            { value: 'Reversal', label: 'Reversals', count: 0 },
            { value: 'Flag', label: 'Flag Patterns', count: 0 },
            { value: 'Triangle', label: 'Triangles', count: 0 },
            { value: 'Support', label: 'Support/Resistance', count: 0 }
        ];
        
        return patternTypes.map(type => `
            <label class="pattern-type-checkbox">
                <input type="checkbox" value="${type.value}" 
                       ${this.filterState.pattern_types.includes(type.value) ? 'checked' : ''}>
                <span class="checkmark"></span>
                <span class="pattern-label">${type.label}</span>
                <span class="pattern-count" id="count-${type.value}">(${type.count})</span>
            </label>
        `).join('');
    }
    
    renderTimeframeRadios() {
        const timeframes = [
            { value: 'All', label: 'All Timeframes' },
            { value: 'Daily', label: 'Daily Patterns' },
            { value: 'Intraday', label: 'Intraday Signals' },
            { value: 'Combo', label: 'Combo Alerts' }
        ];
        
        return timeframes.map(tf => `
            <label class="timeframe-radio">
                <input type="radio" name="timeframe" value="${tf.value}" 
                       ${this.filterState.timeframe === tf.value ? 'checked' : ''}>
                <span class="radio-mark"></span>
                <span>${tf.label}</span>
            </label>
        `).join('');
    }
    
    renderConfidenceStars(confidence) {
        const stars = 4;
        const filled = Math.floor(confidence * stars);
        return Array.from({length: stars}, (_, i) => 
            i < filled ? '●' : '○'
        ).join('');
    }
    
    renderSectorCheckboxes() {
        const sectors = [
            'Technology', 'Healthcare', 'Finance', 'Energy',
            'Consumer Disc', 'Industrials', 'Materials', 'Utilities',
            'Real Estate', 'Consumer Staples', 'Telecom'
        ];
        
        return sectors.map(sector => `
            <label class="sector-checkbox">
                <input type="checkbox" value="${sector}" 
                       ${this.filterState.sectors.includes(sector) ? 'checked' : ''}>
                <span>${sector}</span>
            </label>
        `).join('');
    }
    
    renderSelectedSymbols() {
        return this.filterState.symbols.map(symbol => `
            <span class="symbol-tag">
                ${symbol}
                <button class="remove-symbol" data-symbol="${symbol}">&times;</button>
            </span>
        `).join('');
    }
    
    renderSavedFilters() {
        return this.savedFilters.map(filter => `
            <div class="saved-filter-item">
                <button class="load-filter" data-filter-id="${filter.id}">
                    ${filter.name}
                </button>
                <button class="delete-filter" data-filter-id="${filter.id}">&times;</button>
            </div>
        `).join('');
    }
    
    bindEvents() {
        // Collapse/Expand
        this.container.querySelector('#collapse-filters').addEventListener('click', () => {
            this.toggleCollapse();
        });
        
        // Reset filters
        this.container.querySelector('#reset-filters').addEventListener('click', () => {
            this.resetFilters();
        });
        
        // Pattern type checkboxes
        this.container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateFilterState();
                this.debouncedFilterChange();
            });
        });
        
        // Timeframe radios
        this.container.querySelectorAll('input[name="timeframe"]').forEach(radio => {
            radio.addEventListener('change', () => {
                this.filterState.timeframe = radio.value;
                this.debouncedFilterChange();
            });
        });
        
        // Confidence slider
        this.container.querySelector('#confidence-slider').addEventListener('input', (e) => {
            this.filterState.confidence_min = parseFloat(e.target.value);
            this.updateConfidenceDisplay();
            this.debouncedFilterChange();
        });
        
        // Range inputs
        ['rs-min', 'rs-max', 'vol-min', 'vol-max', 'price-min', 'price-max', 'change-min', 'change-max'].forEach(id => {
            const input = this.container.querySelector(`#${id}`);
            if (input) {
                input.addEventListener('input', () => {
                    this.updateFilterState();
                    this.debouncedFilterChange();
                });
            }
        });
        
        // RSI dual range sliders
        this.container.querySelector('#rsi-min-slider').addEventListener('input', (e) => {
            this.filterState.rsi_min = parseInt(e.target.value);
            this.updateRSIDisplay();
            this.debouncedFilterChange();
        });
        
        this.container.querySelector('#rsi-max-slider').addEventListener('input', (e) => {
            this.filterState.rsi_max = parseInt(e.target.value);
            this.updateRSIDisplay();
            this.debouncedFilterChange();
        });
        
        // Quick filter buttons
        this.container.querySelectorAll('.quick-filter').forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyQuickFilter(btn.dataset.preset);
            });
        });
        
        // Quick value buttons
        this.container.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.handleQuickButtonClick(btn);
            });
        });
        
        // Symbol search
        const symbolSearch = this.container.querySelector('#symbol-search');
        symbolSearch.addEventListener('input', (e) => {
            this.handleSymbolSearch(e.target.value);
        });
        
        // Time range selection
        this.container.querySelector('#time-range-select').addEventListener('change', (e) => {
            this.filterState.time_range = e.target.value;
            this.toggleCustomDateRange(e.target.value === 'custom');
            this.debouncedFilterChange();
        });
        
        // Logic mode radios
        this.container.querySelectorAll('input[name="logic-mode"]').forEach(radio => {
            radio.addEventListener('change', () => {
                this.filterState.logic_mode = radio.value;
                this.debouncedFilterChange();
            });
        });
        
        // Save filter
        this.container.querySelector('#save-filter').addEventListener('click', () => {
            this.saveCurrentFilter();
        });
        
        // Apply/Reset buttons
        this.container.querySelector('#apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });
        
        this.container.querySelector('#reset-all-filters').addEventListener('click', () => {
            this.resetAllFilters();
        });
        
        // Remove symbol tags
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-symbol')) {
                this.removeSymbol(e.target.dataset.symbol);
            }
        });
        
        // Load/delete saved filters
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('load-filter')) {
                this.loadSavedFilter(e.target.dataset.filterId);
            } else if (e.target.classList.contains('delete-filter')) {
                this.deleteSavedFilter(e.target.dataset.filterId);
            }
        });
    }
    
    updateFilterState() {
        // Update pattern types
        this.filterState.pattern_types = Array.from(
            this.container.querySelectorAll('input[type="checkbox"]:checked')
        ).map(cb => cb.value).filter(value => 
            ['Breakout', 'Volume', 'Trendline', 'Gap', 'Reversal', 'Flag', 'Triangle', 'Support'].includes(value)
        );
        
        // Update sectors
        this.filterState.sectors = Array.from(
            this.container.querySelectorAll('.sector-checkbox input:checked')
        ).map(cb => cb.value);
        
        // Update market caps
        this.filterState.market_caps = Array.from(
            this.container.querySelectorAll('.market-cap-checkboxes input:checked')
        ).map(cb => cb.value);
        
        // Update ranges
        this.filterState.rs_min = parseFloat(this.container.querySelector('#rs-min').value) || 0;
        this.filterState.rs_max = parseFloat(this.container.querySelector('#rs-max').value) || 10;
        this.filterState.vol_min = parseFloat(this.container.querySelector('#vol-min').value) || 0;
        this.filterState.vol_max = parseFloat(this.container.querySelector('#vol-max').value) || 20;
        this.filterState.price_min = parseFloat(this.container.querySelector('#price-min').value) || 0;
        this.filterState.price_max = parseFloat(this.container.querySelector('#price-max').value) || 10000;
        this.filterState.price_change_min = parseFloat(this.container.querySelector('#change-min').value) || -50;
        this.filterState.price_change_max = parseFloat(this.container.querySelector('#change-max').value) || 50;
    }
    
    debouncedFilterChange() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.options.onFilterChange(this.filterState);
        }, this.options.debounceDelay);
    }
    
    applyQuickFilter(preset) {
        const presets = {
            'high-momentum': {
                pattern_types: ['Breakout', 'Volume'],
                rs_min: 1.2,
                vol_min: 2.0,
                confidence_min: 0.8
            },
            'volume-breakouts': {
                pattern_types: ['Breakout', 'Volume'],
                vol_min: 2.0,
                confidence_min: 0.7
            },
            'daily-swings': {
                timeframe: 'Daily',
                pattern_types: ['Trendline', 'Support', 'Reversal'],
                confidence_min: 0.75
            },
            'scalp-setups': {
                timeframe: 'Intraday',
                pattern_types: ['Volume', 'Gap'],
                time_range: 'last_1h',
                vol_min: 1.5
            }
        };
        
        const presetConfig = presets[preset];
        if (presetConfig) {
            Object.assign(this.filterState, presetConfig);
            this.updateUI();
            this.options.onFilterChange(this.filterState);
        }
    }
    
    async handleSymbolSearch(query) {
        if (query.length < 1) {
            this.hideSearchResults();
            return;
        }
        
        try {
            const results = await this.searchSymbols(query);
            this.showSearchResults(results);
        } catch (error) {
            console.error('Symbol search error:', error);
        }
    }
    
    async searchSymbols(query) {
        // Check cache first
        if (this.symbolCache.has(query.toLowerCase())) {
            return this.symbolCache.get(query.toLowerCase());
        }
        
        // API call to get matching symbols
        const response = await fetch(`/api/symbols/search?q=${encodeURIComponent(query)}&limit=10`);
        const data = await response.json();
        
        // Cache results
        this.symbolCache.set(query.toLowerCase(), data.symbols || []);
        
        return data.symbols || [];
    }
    
    showSearchResults(symbols) {
        const resultsContainer = this.container.querySelector('#symbol-search-results');
        resultsContainer.innerHTML = symbols.map(symbol => `
            <div class="search-result-item" data-symbol="${symbol.symbol}">
                <strong>${symbol.symbol}</strong>
                <span class="symbol-name">${symbol.name}</span>
            </div>
        `).join('');
        
        resultsContainer.style.display = 'block';
        
        // Bind click events
        resultsContainer.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                this.addSymbol(item.dataset.symbol);
                this.hideSearchResults();
                this.container.querySelector('#symbol-search').value = '';
            });
        });
    }
    
    hideSearchResults() {
        const resultsContainer = this.container.querySelector('#symbol-search-results');
        resultsContainer.style.display = 'none';
        resultsContainer.innerHTML = '';
    }
    
    addSymbol(symbol) {
        if (!this.filterState.symbols.includes(symbol)) {
            this.filterState.symbols.push(symbol);
            this.updateSelectedSymbols();
            this.debouncedFilterChange();
        }
    }
    
    removeSymbol(symbol) {
        this.filterState.symbols = this.filterState.symbols.filter(s => s !== symbol);
        this.updateSelectedSymbols();
        this.debouncedFilterChange();
    }
    
    updateSelectedSymbols() {
        const container = this.container.querySelector('#selected-symbols');
        container.innerHTML = this.renderSelectedSymbols();
    }
    
    updateConfidenceDisplay() {
        const value = this.filterState.confidence_min;
        this.container.querySelector('.confidence-value').textContent = `${Math.round(value * 100)}%`;
        this.container.querySelector('.confidence-visual').innerHTML = this.renderConfidenceStars(value);
    }
    
    updateRSIDisplay() {
        this.container.querySelector('#rsi-min-value').textContent = this.filterState.rsi_min;
        this.container.querySelector('#rsi-max-value').textContent = this.filterState.rsi_max;
    }
    
    saveCurrentFilter() {
        const nameInput = this.container.querySelector('#filter-name');
        const name = nameInput.value.trim();
        
        if (!name) {
            alert('Please enter a name for the filter');
            return;
        }
        
        const filter = {
            id: Date.now().toString(),
            name: name,
            config: { ...this.filterState },
            created: new Date().toISOString()
        };
        
        this.savedFilters.push(filter);
        this.saveSavedFilters();
        this.updateSavedFiltersDisplay();
        nameInput.value = '';
    }
    
    loadSavedFilter(filterId) {
        const filter = this.savedFilters.find(f => f.id === filterId);
        if (filter) {
            this.filterState = { ...filter.config };
            this.updateUI();
            this.options.onFilterChange(this.filterState);
        }
    }
    
    deleteSavedFilter(filterId) {
        this.savedFilters = this.savedFilters.filter(f => f.id !== filterId);
        this.saveSavedFilters();
        this.updateSavedFiltersDisplay();
    }
    
    loadSavedFilters() {
        try {
            const saved = localStorage.getItem('tickstock_saved_filters');
            this.savedFilters = saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.warn('Failed to load saved filters:', error);
            this.savedFilters = [];
        }
    }
    
    saveSavedFilters() {
        localStorage.setItem('tickstock_saved_filters', JSON.stringify(this.savedFilters));
    }
    
    updateSavedFiltersDisplay() {
        const container = this.container.querySelector('#saved-filters');
        container.innerHTML = this.renderSavedFilters();
    }
    
    updateUI() {
        // Update all form elements to match filterState
        // Pattern types
        this.container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            if (['Breakout', 'Volume', 'Trendline', 'Gap', 'Reversal', 'Flag', 'Triangle', 'Support'].includes(cb.value)) {
                cb.checked = this.filterState.pattern_types.includes(cb.value);
            }
        });
        
        // Timeframe
        const timeframeRadio = this.container.querySelector(`input[name="timeframe"][value="${this.filterState.timeframe}"]`);
        if (timeframeRadio) timeframeRadio.checked = true;
        
        // Confidence
        this.container.querySelector('#confidence-slider').value = this.filterState.confidence_min;
        this.updateConfidenceDisplay();
        
        // Ranges
        this.container.querySelector('#rs-min').value = this.filterState.rs_min;
        this.container.querySelector('#rs-max').value = this.filterState.rs_max;
        this.container.querySelector('#vol-min').value = this.filterState.vol_min;
        this.container.querySelector('#vol-max').value = this.filterState.vol_max;
        this.container.querySelector('#price-min').value = this.filterState.price_min;
        this.container.querySelector('#price-max').value = this.filterState.price_max;
        this.container.querySelector('#change-min').value = this.filterState.price_change_min;
        this.container.querySelector('#change-max').value = this.filterState.price_change_max;
        
        // RSI
        this.container.querySelector('#rsi-min-slider').value = this.filterState.rsi_min;
        this.container.querySelector('#rsi-max-slider').value = this.filterState.rsi_max;
        this.updateRSIDisplay();
        
        // Logic mode
        const logicRadio = this.container.querySelector(`input[name="logic-mode"][value="${this.filterState.logic_mode}"]`);
        if (logicRadio) logicRadio.checked = true;
        
        // Time range
        this.container.querySelector('#time-range-select').value = this.filterState.time_range;
        
        // Symbols
        this.updateSelectedSymbols();
    }
    
    resetFilters() {
        this.filterState = {
            pattern_types: [],
            timeframe: 'All',
            confidence_min: 0.5,
            rs_min: 0,
            rs_max: 10,
            vol_min: 0,
            vol_max: 20,
            rsi_min: 0,
            rsi_max: 100,
            price_min: 0,
            price_max: 10000,
            price_change_min: -50,
            price_change_max: 50,
            market_caps: [],
            sectors: [],
            symbols: [],
            time_range: 'last_4h',
            logic_mode: 'AND'
        };
        
        this.updateUI();
        this.options.onFilterChange(this.filterState);
    }
    
    toggleCollapse() {
        const content = this.container.querySelector('#filter-content');
        const btn = this.container.querySelector('#collapse-filters');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.querySelector('.collapse-icon').textContent = '−';
        } else {
            content.style.display = 'none';
            btn.querySelector('.collapse-icon').textContent = '+';
        }
    }
    
    getFilterSummary() {
        const active = [];
        
        if (this.filterState.pattern_types.length > 0) {
            active.push(`${this.filterState.pattern_types.length} pattern types`);
        }
        
        if (this.filterState.symbols.length > 0) {
            active.push(`${this.filterState.symbols.length} symbols`);
        }
        
        if (this.filterState.rs_min > 0) {
            active.push(`RS ≥${this.filterState.rs_min}x`);
        }
        
        if (this.filterState.vol_min > 0) {
            active.push(`Vol ≥${this.filterState.vol_min}x`);
        }
        
        if (this.filterState.confidence_min > 0.5) {
            active.push(`Conf ≥${Math.round(this.filterState.confidence_min * 100)}%`);
        }
        
        return active.length > 0 ? active.join(', ') : 'No filters active';
    }
}

// Export for use in other components
window.FilterPanel = FilterPanel;
```

### Task 3.2: Search Performance Optimization (Days 5-7)

#### 3.2.1 Symbol Search API Endpoint
**File**: `src/api/symbol_search.py`

```python
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app import db, redis_client
import json
import re

search_bp = Blueprint('search', __name__)

@search_bp.route('/api/symbols/search', methods=['GET'])
def search_symbols():
    """
    Fast symbol search with autocomplete
    
    Query Parameters:
    - q: Search query (required)
    - limit: Max results (default: 10, max: 50)
    - include_names: Include company names (default: true)
    """
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 10)), 50)
    include_names = request.args.get('include_names', 'true').lower() == 'true'
    
    if len(query) < 1:
        return jsonify({'symbols': [], 'query': query})
    
    # Check Redis cache first
    cache_key = f"symbol_search:{query.lower()}:{limit}:{include_names}"
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return jsonify(json.loads(cached_result))
    
    # Clean and validate query
    clean_query = re.sub(r'[^A-Za-z0-9]', '', query).upper()
    if not clean_query:
        return jsonify({'symbols': [], 'query': query})
    
    try:
        # Optimized search query with multiple matching strategies
        search_query = """
        WITH symbol_matches AS (
            -- Exact prefix match (highest priority)
            SELECT symbol, name, 1 as priority, 'exact_prefix' as match_type
            FROM symbols 
            WHERE symbol LIKE :exact_prefix
            AND active = true
            
            UNION
            
            -- Contains match (medium priority)
            SELECT symbol, name, 2 as priority, 'contains' as match_type
            FROM symbols 
            WHERE symbol LIKE :contains_pattern
            AND symbol NOT LIKE :exact_prefix
            AND active = true
            
            UNION
            
            -- Name match (lower priority)
            SELECT symbol, name, 3 as priority, 'name' as match_type
            FROM symbols 
            WHERE name ILIKE :name_pattern
            AND symbol NOT LIKE :contains_pattern
            AND active = true
        )
        SELECT symbol, name, priority, match_type
        FROM symbol_matches
        ORDER BY priority, 
                 CASE WHEN LENGTH(symbol) <= 5 THEN 1 ELSE 2 END, -- Prefer shorter symbols
                 symbol
        LIMIT :limit
        """
        
        params = {
            'exact_prefix': f"{clean_query}%",
            'contains_pattern': f"%{clean_query}%",
            'name_pattern': f"%{query}%",
            'limit': limit
        }
        
        results = db.session.execute(text(search_query), params).fetchall()
        
        symbols = []
        for row in results:
            symbol_data = {
                'symbol': row.symbol,
                'match_type': row.match_type
            }
            
            if include_names:
                symbol_data['name'] = row.name
            
            symbols.append(symbol_data)
        
        response = {
            'symbols': symbols,
            'query': query,
            'count': len(symbols)
        }
        
        # Cache for 5 minutes
        redis_client.setex(cache_key, 300, json.dumps(response))
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'error': 'Search failed',
            'message': str(e),
            'symbols': [],
            'query': query
        }), 500

@search_bp.route('/api/symbols/popular', methods=['GET'])
def get_popular_symbols():
    """
    Get frequently searched/traded symbols for autocomplete
    """
    cache_key = "popular_symbols"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        return jsonify(json.loads(cached_result))
    
    try:
        # Get most active symbols from recent patterns
        query = """
        SELECT symbol, COUNT(*) as pattern_count
        FROM (
            SELECT symbol FROM daily_patterns WHERE detected_at >= NOW() - INTERVAL '7 days'
            UNION ALL
            SELECT symbol FROM intraday_patterns WHERE detected_at >= NOW() - INTERVAL '7 days'
            UNION ALL
            SELECT symbol FROM daily_intraday_patterns WHERE detected_at >= NOW() - INTERVAL '7 days'
        ) recent_patterns
        GROUP BY symbol
        ORDER BY pattern_count DESC, symbol
        LIMIT 100
        """
        
        results = db.session.execute(text(query)).fetchall()
        
        symbols = [{'symbol': row.symbol, 'pattern_count': row.pattern_count} 
                  for row in results]
        
        response = {'popular_symbols': symbols}
        
        # Cache for 1 hour
        redis_client.setex(cache_key, 3600, json.dumps(response))
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get popular symbols',
            'message': str(e)
        }), 500
```

### Task 3.3: Enhanced CSS for Advanced Filters (Days 8-10)

#### 3.3.1 Filter Panel Styles
**File**: `static/css/filter-panel.css`

```css
/* Advanced Filter Panel Styles */
.filter-panel {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-secondary);
    font-size: 13px;
}

.filter-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
}

.filter-header h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}

.filter-actions {
    display: flex;
    gap: 4px;
}

.filter-btn {
    width: 24px;
    height: 24px;
    border: 1px solid var(--border-color);
    background: var(--bg-secondary);
    color: var(--text-secondary);
    border-radius: 3px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
}

.filter-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.filter-content {
    flex: 1;
    overflow-y: auto;
    padding: 0 16px 16px;
}

/* Filter Sections */
.filter-section {
    margin-bottom: 20px;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 16px;
}

.filter-section:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.filter-section h4 {
    margin: 0 0 12px 0;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Quick Filters */
.quick-filters {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
}

.quick-filter {
    padding: 6px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    transition: all 0.2s ease;
}

.quick-filter:hover {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

/* Pattern Type Checkboxes */
.pattern-types {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.pattern-type-checkbox {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 4px 0;
    transition: background-color 0.2s ease;
    border-radius: 3px;
}

.pattern-type-checkbox:hover {
    background: var(--bg-hover);
}

.pattern-type-checkbox input[type="checkbox"] {
    display: none;
}

.checkmark {
    width: 14px;
    height: 14px;
    border: 1px solid var(--border-color);
    border-radius: 2px;
    position: relative;
    background: var(--bg-primary);
    flex-shrink: 0;
}

.pattern-type-checkbox input:checked + .checkmark {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
}

.pattern-type-checkbox input:checked + .checkmark::after {
    content: '✓';
    position: absolute;
    top: -1px;
    left: 2px;
    color: #000;
    font-size: 10px;
    font-weight: bold;
}

.pattern-label {
    flex: 1;
    color: var(--text-primary);
    font-size: 12px;
}

.pattern-count {
    color: var(--text-secondary);
    font-size: 10px;
}

/* Timeframe Radio Buttons */
.timeframe-selection {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.timeframe-radio {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 4px 0;
}

.timeframe-radio input[type="radio"] {
    display: none;
}

.radio-mark {
    width: 12px;
    height: 12px;
    border: 1px solid var(--border-color);
    border-radius: 50%;
    background: var(--bg-primary);
    position: relative;
    flex-shrink: 0;
}

.timeframe-radio input:checked + .radio-mark {
    border-color: var(--accent-primary);
}

.timeframe-radio input:checked + .radio-mark::after {
    content: '';
    width: 6px;
    height: 6px;
    background: var(--accent-primary);
    border-radius: 50%;
    position: absolute;
    top: 2px;
    left: 2px;
}

/* Confidence Slider */
.confidence-slider {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

#confidence-slider {
    width: 100%;
    height: 4px;
    background: var(--bg-primary);
    outline: none;
    border-radius: 2px;
    appearance: none;
}

#confidence-slider::-webkit-slider-thumb {
    appearance: none;
    width: 16px;
    height: 16px;
    background: var(--accent-primary);
    border-radius: 50%;
    cursor: pointer;
}

#confidence-slider::-moz-range-thumb {
    width: 16px;
    height: 16px;
    background: var(--accent-primary);
    border-radius: 50%;
    cursor: pointer;
    border: none;
}

.confidence-display {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.confidence-value {
    font-weight: 600;
    color: var(--text-primary);
}

.confidence-visual {
    font-size: 14px;
    color: var(--accent-primary);
    letter-spacing: 1px;
}

/* Indicator Rows */
.indicator-row {
    margin-bottom: 16px;
}

.indicator-row label {
    display: block;
    margin-bottom: 6px;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-primary);
    text-transform: uppercase;
}

.range-inputs {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
}

.range-inputs input[type="number"] {
    flex: 1;
    padding: 4px 6px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    font-size: 11px;
    width: 0; /* Flex will handle actual width */
}

.range-inputs span {
    color: var(--text-secondary);
    font-size: 10px;
    flex-shrink: 0;
}

.range-suffix {
    font-weight: 500;
}

/* Quick Buttons */
.quick-rs-buttons,
.quick-vol-buttons,
.rsi-presets,
.price-presets,
.change-presets {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}

.quick-btn {
    padding: 3px 6px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    border-radius: 2px;
    cursor: pointer;
    font-size: 9px;
    text-transform: uppercase;
    font-weight: 500;
    transition: all 0.2s ease;
}

.quick-btn:hover {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

/* Dual Range Slider for RSI */
.dual-range-slider {
    position: relative;
    margin-bottom: 8px;
}

.dual-range-slider input[type="range"] {
    position: absolute;
    width: 100%;
    height: 4px;
    background: transparent;
    pointer-events: none;
    appearance: none;
}

.dual-range-slider input[type="range"]::-webkit-slider-thumb {
    appearance: none;
    width: 14px;
    height: 14px;
    background: var(--accent-primary);
    border-radius: 50%;
    cursor: pointer;
    pointer-events: all;
    position: relative;
    z-index: 2;
}

.dual-range-slider::before {
    content: '';
    position: absolute;
    top: 5px;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--bg-primary);
    border-radius: 2px;
}

.range-display {
    text-align: center;
    margin-top: 12px;
    font-size: 11px;
    color: var(--text-primary);
    font-weight: 500;
}

/* Symbol Search */
.symbol-search {
    position: relative;
    margin-bottom: 12px;
}

#symbol-search {
    width: 100%;
    padding: 6px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 4px;
    font-size: 12px;
}

#symbol-search:focus {
    border-color: var(--accent-primary);
    outline: none;
}

.search-results {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-top: none;
    max-height: 200px;
    overflow-y: auto;
    z-index: 10;
    display: none;
}

.search-result-item {
    padding: 6px 8px;
    cursor: pointer;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.search-result-item:hover {
    background: var(--bg-hover);
}

.search-result-item:last-child {
    border-bottom: none;
}

.symbol-name {
    font-size: 10px;
    color: var(--text-secondary);
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
    max-width: 150px;
}

/* Selected Symbols */
.selected-symbols {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 12px;
    min-height: 20px;
}

.symbol-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 6px;
    background: var(--accent-primary);
    color: #000;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 500;
}

.remove-symbol {
    background: none;
    border: none;
    color: #000;
    cursor: pointer;
    font-size: 12px;
    padding: 0;
    line-height: 1;
}

.remove-symbol:hover {
    color: var(--error-color);
}

/* Sector and Market Cap Checkboxes */
.sector-checkboxes,
.market-cap-checkboxes {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 120px;
    overflow-y: auto;
}

.sector-checkbox,
.market-cap-checkboxes label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--text-primary);
    cursor: pointer;
}

.sector-checkbox input,
.market-cap-checkboxes input {
    width: 12px;
    height: 12px;
    accent-color: var(--accent-primary);
}

/* Time Range Selection */
#time-range-select {
    width: 100%;
    padding: 4px 6px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    font-size: 11px;
    margin-bottom: 8px;
}

.custom-date-range {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.custom-date-range input[type="datetime-local"] {
    padding: 4px 6px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    font-size: 11px;
}

/* Logic Mode */
.logic-mode {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.logic-mode label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--text-primary);
    cursor: pointer;
}

.logic-mode input[type="radio"] {
    width: 12px;
    height: 12px;
    accent-color: var(--accent-primary);
}

/* Saved Filters */
.saved-filters {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 12px;
    max-height: 100px;
    overflow-y: auto;
}

.saved-filter-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
}

.load-filter {
    flex: 1;
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
    text-align: left;
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
}

.load-filter:hover {
    background: var(--bg-hover);
}

.delete-filter {
    width: 20px;
    height: 20px;
    background: none;
    border: 1px solid var(--error-color);
    color: var(--error-color);
    border-radius: 2px;
    cursor: pointer;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.delete-filter:hover {
    background: var(--error-color);
    color: #fff;
}

.save-filter-controls {
    display: flex;
    gap: 6px;
}

#filter-name {
    flex: 1;
    padding: 4px 6px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    font-size: 11px;
}

.save-filter-btn {
    padding: 4px 8px;
    background: var(--accent-primary);
    border: 1px solid var(--accent-primary);
    color: #000;
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
}

.save-filter-btn:hover {
    background: var(--success-color);
    border-color: var(--success-color);
}

/* Bottom Actions */
.filter-actions-bottom {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    background: var(--bg-primary);
    border-top: 1px solid var(--border-color);
}

.apply-filters-btn,
.reset-all-btn {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.apply-filters-btn {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

.apply-filters-btn:hover {
    background: var(--success-color);
    border-color: var(--success-color);
}

.reset-all-btn {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.reset-all-btn:hover {
    background: var(--error-color);
    border-color: var(--error-color);
    color: #fff;
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .filter-sidebar.mobile-hidden {
        display: none;
    }
    
    .quick-filters {
        grid-template-columns: 1fr;
    }
    
    .filter-content {
        padding: 0 8px 8px;
    }
    
    .filter-section {
        margin-bottom: 16px;
    }
    
    .range-inputs {
        flex-direction: column;
        gap: 4px;
    }
    
    .range-inputs span {
        align-self: center;
    }
}
```

## Testing Strategy

### Advanced Filter Testing
**File**: `tests/test_advanced_filters.js`

```javascript
describe('Advanced Filtering System', () => {
    let filterPanel;
    let container;
    
    beforeEach(() => {
        container = document.createElement('div');
        container.id = 'test-filter-panel';
        document.body.appendChild(container);
        
        filterPanel = new FilterPanel('test-filter-panel', {
            onFilterChange: jest.fn()
        });
    });
    
    afterEach(() => {
        document.body.removeChild(container);
    });
    
    test('should initialize with default filter state', () => {
        expect(filterPanel.filterState.timeframe).toBe('All');
        expect(filterPanel.filterState.confidence_min).toBe(0.5);
        expect(filterPanel.filterState.pattern_types).toEqual([]);
    });
    
    test('should update filter state when checkboxes change', () => {
        const breakoutCheckbox = container.querySelector('input[value="Breakout"]');
        breakoutCheckbox.checked = true;
        breakoutCheckbox.dispatchEvent(new Event('change'));
        
        expect(filterPanel.filterState.pattern_types).toContain('Breakout');
    });
    
    test('should apply quick filters correctly', () => {
        filterPanel.applyQuickFilter('high-momentum');
        
        expect(filterPanel.filterState.pattern_types).toEqual(['Breakout', 'Volume']);
        expect(filterPanel.filterState.rs_min).toBe(1.2);
        expect(filterPanel.filterState.vol_min).toBe(2.0);
        expect(filterPanel.filterState.confidence_min).toBe(0.8);
    });
    
    test('should save and load filter presets', () => {
        // Set up a filter state
        filterPanel.filterState.pattern_types = ['Breakout'];
        filterPanel.filterState.rs_min = 1.5;
        
        // Save filter
        const nameInput = container.querySelector('#filter-name');
        nameInput.value = 'Test Filter';
        filterPanel.saveCurrentFilter();
        
        expect(filterPanel.savedFilters).toHaveLength(1);
        expect(filterPanel.savedFilters[0].name).toBe('Test Filter');
        
        // Reset and load
        filterPanel.resetFilters();
        expect(filterPanel.filterState.pattern_types).toEqual([]);
        
        filterPanel.loadSavedFilter(filterPanel.savedFilters[0].id);
        expect(filterPanel.filterState.pattern_types).toEqual(['Breakout']);
        expect(filterPanel.filterState.rs_min).toBe(1.5);
    });
    
    test('should debounce filter changes', (done) => {
        const onFilterChange = jest.fn();
        filterPanel.options.onFilterChange = onFilterChange;
        filterPanel.options.debounceDelay = 100;
        
        // Trigger multiple rapid changes
        filterPanel.debouncedFilterChange();
        filterPanel.debouncedFilterChange();
        filterPanel.debouncedFilterChange();
        
        // Should not have been called yet
        expect(onFilterChange).not.toHaveBeenCalled();
        
        // Wait for debounce
        setTimeout(() => {
            expect(onFilterChange).toHaveBeenCalledTimes(1);
            done();
        }, 150);
    });
    
    test('should handle symbol search and selection', async () => {
        // Mock search API
        global.fetch = jest.fn(() =>
            Promise.resolve({
                json: () => Promise.resolve({
                    symbols: [
                        { symbol: 'AAPL', name: 'Apple Inc.' },
                        { symbol: 'AAPLF', name: 'Apple Farm Corp.' }
                    ]
                })
            })
        );
        
        await filterPanel.handleSymbolSearch('AAPL');
        
        expect(fetch).toHaveBeenCalledWith('/api/symbols/search?q=AAPL&limit=10');
        
        // Add symbol
        filterPanel.addSymbol('AAPL');
        expect(filterPanel.filterState.symbols).toContain('AAPL');
        
        // Remove symbol
        filterPanel.removeSymbol('AAPL');
        expect(filterPanel.filterState.symbols).not.toContain('AAPL');
    });
    
    test('should validate range inputs', () => {
        const rsMinInput = container.querySelector('#rs-min');
        rsMinInput.value = '1.5';
        rsMinInput.dispatchEvent(new Event('input'));
        
        const rsMaxInput = container.querySelector('#rs-max');
        rsMaxInput.value = '1.0'; // Invalid: min > max
        rsMaxInput.dispatchEvent(new Event('input'));
        
        filterPanel.updateFilterState();
        
        // Should handle invalid ranges gracefully
        expect(filterPanel.filterState.rs_min).toBe(1.5);
        expect(filterPanel.filterState.rs_max).toBe(1.0); // Should be corrected by validation
    });
});

describe('Symbol Search Performance', () => {
    test('should cache search results', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                json: () => Promise.resolve({
                    symbols: [{ symbol: 'AAPL', name: 'Apple Inc.' }]
                })
            })
        );
        
        const filterPanel = new FilterPanel('test', {});
        
        // First search
        await filterPanel.searchSymbols('AAPL');
        expect(fetch).toHaveBeenCalledTimes(1);
        
        // Second search (should use cache)
        await filterPanel.searchSymbols('AAPL');
        expect(fetch).toHaveBeenCalledTimes(1); // No additional fetch
        
        // Check cache
        expect(filterPanel.symbolCache.has('aapl')).toBe(true);
    });
    
    test('should handle search errors gracefully', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('Network error')));
        
        const filterPanel = new FilterPanel('test', {});
        const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
        
        await filterPanel.handleSymbolSearch('FAIL');
        
        expect(consoleSpy).toHaveBeenCalledWith('Symbol search error:', expect.any(Error));
        
        consoleSpy.mockRestore();
    });
});
```

## Performance Benchmarks

### Filter Response Time Targets
- **Simple filters** (1-2 criteria): <50ms
- **Complex filters** (5+ criteria): <100ms  
- **Symbol search**: <200ms
- **Filter preset load**: <30ms
- **UI update after filter change**: <100ms

### Memory Usage Targets
- **Symbol cache**: Max 10MB
- **Filter state storage**: <1MB
- **DOM elements**: <1000 total filter controls

## Deployment Checklist

- [ ] Advanced filter panel renders with all controls
- [ ] Multi-criteria filtering works correctly
- [ ] Symbol search autocomplete responds quickly
- [ ] Saved filter presets persist across sessions
- [ ] Range sliders and inputs validate correctly
- [ ] Quick filter buttons apply presets properly
- [ ] Debounced filter changes prevent performance issues
- [ ] Mobile responsive design works on all filter controls
- [ ] Error handling for API failures
- [ ] Performance benchmarks met for all filter operations

## Next Phase Handoff

**Phase 4 Prerequisites:**
- Advanced filtering system fully operational
- Complex multi-criteria searches working
- Symbol search and autocomplete functional
- Saved filter presets working across sessions
- Performance targets met for all filter operations

**Advanced Filtering Ready For:**
- Market breadth analysis integration
- Index/ETF pattern filtering
- Sector rotation analysis
- Advanced market context features

This implementation provides traders with sophisticated tools to discover patterns matching their specific criteria, significantly enhancing the pattern discovery workflow.