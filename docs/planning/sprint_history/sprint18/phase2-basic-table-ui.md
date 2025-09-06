# Phase 2: Basic Table UI - Detailed Implementation Guide

**Date**: 2025-09-04  
**Sprint**: 18 - Phase 2 Implementation  
**Duration**: 2 weeks  
**Status**: Implementation Ready  
**Prerequisites**: Phase 1 complete (API endpoints operational)

## Phase Overview

Build the core user interface components focusing on high-density data display, basic filtering, and GoldenLayout integration. This phase establishes the visual foundation that users will interact with daily, prioritizing information density and scanning efficiency over visual polish.

## Success Criteria

✅ **Performance**: Table renders 1,000+ patterns smoothly with virtual scrolling  
✅ **Usability**: Users can scan and sort patterns in <3 seconds  
✅ **Responsive**: Layout works on desktop (1920px+), tablet (768-1200px), and mobile (320-767px)  
✅ **GoldenLayout**: Tab system functional with state persistence  
✅ **Integration**: Real-time WebSocket updates populate table without page refresh  

## Implementation Tasks

### Task 2.1: Project Structure Setup (Day 1)

#### 2.1.1 Frontend Directory Structure
```
static/
├── js/
│   ├── components/
│   │   ├── PatternScanner.js       # Main pattern table component
│   │   ├── MarketBreadth.js        # Market breadth tab
│   │   ├── MyFocus.js              # Personal watchlist tab
│   │   ├── FilterPanel.js          # Left sidebar filters
│   │   ├── DataTable.js            # Reusable table component
│   │   └── ChartPanel.js           # Chart display component
│   ├── services/
│   │   ├── PatternAPI.js           # API client service
│   │   ├── WebSocketClient.js      # Real-time updates
│   │   └── StateManager.js         # Application state management
│   ├── utils/
│   │   ├── formatters.js           # Data formatting utilities
│   │   ├── validators.js           # Input validation
│   │   └── constants.js            # Application constants
│   └── app.js                      # Main application entry point
├── css/
│   ├── components/                 # Component-specific styles
│   ├── layout.css                  # GoldenLayout customizations
│   ├── table.css                   # Data table styles
│   └── responsive.css              # Mobile/tablet styles
└── libs/                          # Third-party libraries
    ├── goldenlayout/
    └── socket.io/
```

#### 2.1.2 HTML Template Structure
**File**: `templates/pattern_discovery.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pattern Discovery - TickStock.ai</title>
    
    <!-- GoldenLayout CSS -->
    <link rel="stylesheet" href="/static/libs/goldenlayout/css/goldenlayout-base.css">
    <link rel="stylesheet" href="/static/libs/goldenlayout/css/goldenlayout-dark-theme.css">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="/static/css/layout.css">
    <link rel="stylesheet" href="/static/css/table.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
</head>
<body>
    <!-- Loading Screen -->
    <div id="loading-screen" class="loading-overlay">
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <p>Loading Pattern Discovery Dashboard...</p>
        </div>
    </div>
    
    <!-- Main Application Container -->
    <div id="app-container" class="hidden">
        <!-- Header -->
        <header class="app-header">
            <div class="header-left">
                <h1 class="app-title">📊 TickStock Pattern Discovery</h1>
                <div class="connection-status">
                    <span id="connection-indicator" class="status-dot disconnected"></span>
                    <span id="connection-text">Connecting...</span>
                </div>
            </div>
            <div class="header-right">
                <button id="refresh-data" class="btn btn-secondary">🔄 Refresh</button>
                <button id="export-data" class="btn btn-secondary">📥 Export</button>
                <button id="settings" class="btn btn-secondary">⚙️ Settings</button>
            </div>
        </header>
        
        <!-- GoldenLayout Container -->
        <div id="golden-layout-container"></div>
    </div>
    
    <!-- Pattern Details Modal -->
    <div id="pattern-modal" class="modal hidden">
        <div class="modal-content">
            <span class="modal-close">&times;</span>
            <div id="pattern-modal-body">
                <!-- Pattern details loaded here -->
            </div>
        </div>
    </div>
    
    <!-- Scripts -->
    <script src="/static/libs/socket.io/socket.io.min.js"></script>
    <script src="/static/libs/goldenlayout/js/goldenlayout.min.js"></script>
    
    <!-- Application Scripts -->
    <script src="/static/js/utils/constants.js"></script>
    <script src="/static/js/utils/formatters.js"></script>
    <script src="/static/js/services/PatternAPI.js"></script>
    <script src="/static/js/services/WebSocketClient.js"></script>
    <script src="/static/js/services/StateManager.js"></script>
    
    <!-- Components -->
    <script src="/static/js/components/DataTable.js"></script>
    <script src="/static/js/components/FilterPanel.js"></script>
    <script src="/static/js/components/ChartPanel.js"></script>
    <script src="/static/js/components/PatternScanner.js"></script>
    <script src="/static/js/components/MarketBreadth.js"></script>
    <script src="/static/js/components/MyFocus.js"></script>
    
    <!-- Main Application -->
    <script src="/static/js/app.js"></script>
</body>
</html>
```

### Task 2.2: Core Data Table Component (Days 2-3)

#### 2.2.1 High-Performance Data Table
**File**: `static/js/components/DataTable.js`

```javascript
class DataTable {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            pageSize: 30,
            virtualScrolling: true,
            sortable: true,
            selectable: true,
            ...options
        };
        
        this.data = [];
        this.filteredData = [];
        this.sortState = { column: null, direction: 'asc' };
        this.selectedRows = new Set();
        this.virtualStart = 0;
        this.virtualEnd = this.options.pageSize;
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="data-table-wrapper">
                <div class="table-controls">
                    <div class="table-info">
                        <span class="result-count">0 patterns</span>
                        <span class="last-updated">Updated: Never</span>
                    </div>
                    <div class="table-actions">
                        <select class="page-size-selector">
                            <option value="20">20 per page</option>
                            <option value="30" selected>30 per page</option>
                            <option value="50">50 per page</option>
                            <option value="100">100 per page</option>
                        </select>
                        <button class="export-btn">Export CSV</button>
                    </div>
                </div>
                
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr class="table-header">
                                ${this.options.columns.map(col => `
                                    <th class="sortable" data-column="${col.key}">
                                        ${col.title}
                                        <span class="sort-indicator"></span>
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>
                        <tbody class="table-body">
                            <!-- Rows populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
                
                <div class="table-pagination">
                    <div class="pagination-info">
                        Showing <span class="start-record">0</span>-<span class="end-record">0</span> 
                        of <span class="total-records">0</span>
                    </div>
                    <div class="pagination-controls">
                        <button class="pagination-btn" data-action="first">First</button>
                        <button class="pagination-btn" data-action="prev">Previous</button>
                        <span class="page-numbers"></span>
                        <button class="pagination-btn" data-action="next">Next</button>
                        <button class="pagination-btn" data-action="last">Last</button>
                    </div>
                </div>
            </div>
        `;
        
        this.bindEvents();
    }
    
    bindEvents() {
        // Sorting
        this.container.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', () => {
                const column = header.dataset.column;
                this.sort(column);
            });
        });
        
        // Page size change
        this.container.querySelector('.page-size-selector').addEventListener('change', (e) => {
            this.options.pageSize = parseInt(e.target.value);
            this.virtualEnd = this.options.pageSize;
            this.render();
        });
        
        // Pagination
        this.container.querySelectorAll('.pagination-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.handlePagination(action);
            });
        });
        
        // Row selection
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('chart-btn')) {
                const symbol = e.target.closest('tr').dataset.symbol;
                this.onRowChart?.(symbol);
            } else if (e.target.closest('tr.table-row')) {
                const row = e.target.closest('tr');
                this.selectRow(row);
            }
        });
        
        // Export
        this.container.querySelector('.export-btn').addEventListener('click', () => {
            this.exportData();
        });
        
        // Virtual scrolling (if enabled)
        if (this.options.virtualScrolling) {
            this.container.querySelector('.table-container').addEventListener('scroll', 
                this.throttle(this.handleScroll.bind(this), 16));
        }
    }
    
    setData(data, totalCount = null) {
        this.data = data;
        this.filteredData = [...data];
        this.totalCount = totalCount || data.length;
        this.updateStats();
        this.render();
    }
    
    updateData(newData) {
        // Merge with existing data, avoiding duplicates
        const existingSymbols = new Set(this.data.map(row => `${row.symbol}_${row.pattern}`));
        const uniqueNew = newData.filter(row => 
            !existingSymbols.has(`${row.symbol}_${row.pattern}`)
        );
        
        if (uniqueNew.length > 0) {
            this.data = [...uniqueNew, ...this.data];
            this.filteredData = [...this.data];
            this.render();
            this.showUpdateNotification(`${uniqueNew.length} new patterns detected`);
        }
    }
    
    render() {
        const tbody = this.container.querySelector('.table-body');
        const startIndex = this.virtualStart;
        const endIndex = Math.min(this.virtualEnd, this.filteredData.length);
        const visibleData = this.filteredData.slice(startIndex, endIndex);
        
        tbody.innerHTML = visibleData.map((row, index) => `
            <tr class="table-row ${this.selectedRows.has(startIndex + index) ? 'selected' : ''}" 
                data-symbol="${row.symbol}" data-index="${startIndex + index}">
                ${this.options.columns.map(col => {
                    const value = row[col.key];
                    const formatted = col.formatter ? col.formatter(value, row) : value;
                    return `<td class="${col.className || ''}">${formatted}</td>`;
                }).join('')}
            </tr>
        `).join('');
        
        this.updatePagination();
        this.updateStats();
    }
    
    sort(column) {
        if (this.sortState.column === column) {
            this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortState.column = column;
            this.sortState.direction = 'asc';
        }
        
        this.filteredData.sort((a, b) => {
            const aVal = a[column];
            const bVal = b[column];
            const mult = this.sortState.direction === 'asc' ? 1 : -1;
            
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return (aVal - bVal) * mult;
            }
            return String(aVal).localeCompare(String(bVal)) * mult;
        });
        
        this.updateSortIndicators();
        this.render();
    }
    
    updateSortIndicators() {
        this.container.querySelectorAll('.sort-indicator').forEach(indicator => {
            indicator.textContent = '';
            indicator.className = 'sort-indicator';
        });
        
        if (this.sortState.column) {
            const header = this.container.querySelector(`[data-column="${this.sortState.column}"]`);
            const indicator = header.querySelector('.sort-indicator');
            indicator.textContent = this.sortState.direction === 'asc' ? '↑' : '↓';
            indicator.className = `sort-indicator sort-${this.sortState.direction}`;
        }
    }
    
    updateStats() {
        this.container.querySelector('.result-count').textContent = 
            `${this.filteredData.length.toLocaleString()} patterns`;
        this.container.querySelector('.last-updated').textContent = 
            `Updated: ${new Date().toLocaleTimeString()}`;
    }
    
    updatePagination() {
        const totalPages = Math.ceil(this.filteredData.length / this.options.pageSize);
        const currentPage = Math.floor(this.virtualStart / this.options.pageSize) + 1;
        
        this.container.querySelector('.start-record').textContent = 
            (this.virtualStart + 1).toLocaleString();
        this.container.querySelector('.end-record').textContent = 
            Math.min(this.virtualEnd, this.filteredData.length).toLocaleString();
        this.container.querySelector('.total-records').textContent = 
            this.filteredData.length.toLocaleString();
        
        // Generate page numbers
        const pageNumbers = this.generatePageNumbers(currentPage, totalPages);
        this.container.querySelector('.page-numbers').innerHTML = pageNumbers.map(page => {
            if (page === '...') {
                return '<span class="page-ellipsis">...</span>';
            }
            return `<button class="page-btn ${page === currentPage ? 'active' : ''}" 
                    data-page="${page}">${page}</button>`;
        }).join('');
        
        // Bind page number clicks
        this.container.querySelectorAll('.page-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = parseInt(btn.dataset.page);
                this.goToPage(page);
            });
        });
        
        // Update button states
        const prevBtn = this.container.querySelector('[data-action="prev"]');
        const nextBtn = this.container.querySelector('[data-action="next"]');
        const firstBtn = this.container.querySelector('[data-action="first"]');
        const lastBtn = this.container.querySelector('[data-action="last"]');
        
        prevBtn.disabled = firstBtn.disabled = currentPage === 1;
        nextBtn.disabled = lastBtn.disabled = currentPage === totalPages;
    }
    
    generatePageNumbers(current, total) {
        if (total <= 7) {
            return Array.from({length: total}, (_, i) => i + 1);
        }
        
        if (current <= 4) {
            return [1, 2, 3, 4, 5, '...', total];
        }
        
        if (current >= total - 3) {
            return [1, '...', total - 4, total - 3, total - 2, total - 1, total];
        }
        
        return [1, '...', current - 1, current, current + 1, '...', total];
    }
    
    goToPage(page) {
        this.virtualStart = (page - 1) * this.options.pageSize;
        this.virtualEnd = this.virtualStart + this.options.pageSize;
        this.render();
    }
    
    handlePagination(action) {
        const currentPage = Math.floor(this.virtualStart / this.options.pageSize) + 1;
        const totalPages = Math.ceil(this.filteredData.length / this.options.pageSize);
        
        switch (action) {
            case 'first':
                this.goToPage(1);
                break;
            case 'prev':
                if (currentPage > 1) this.goToPage(currentPage - 1);
                break;
            case 'next':
                if (currentPage < totalPages) this.goToPage(currentPage + 1);
                break;
            case 'last':
                this.goToPage(totalPages);
                break;
        }
    }
    
    selectRow(row) {
        const index = parseInt(row.dataset.index);
        
        if (this.selectedRows.has(index)) {
            this.selectedRows.delete(index);
            row.classList.remove('selected');
        } else {
            if (!this.options.multiSelect) {
                this.selectedRows.clear();
                this.container.querySelectorAll('.table-row').forEach(r => 
                    r.classList.remove('selected'));
            }
            this.selectedRows.add(index);
            row.classList.add('selected');
        }
        
        this.onSelectionChange?.(Array.from(this.selectedRows));
    }
    
    exportData() {
        const headers = this.options.columns.map(col => col.title);
        const rows = this.filteredData.map(row => 
            this.options.columns.map(col => row[col.key])
        );
        
        const csv = [headers, ...rows].map(row => 
            row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
        ).join('\n');
        
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `patterns-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    showUpdateNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'update-notification';
        notification.textContent = message;
        this.container.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }
    
    // Event handlers (override in implementation)
    onSelectionChange(selectedIndices) {
        // Override this method
    }
    
    onRowChart(symbol) {
        // Override this method
    }
}
```

### Task 2.3: Pattern Scanner Component (Days 4-6)

#### 2.3.1 Pattern Scanner Main Component
**File**: `static/js/components/PatternScanner.js`

```javascript
class PatternScanner {
    constructor(container) {
        this.container = container;
        this.filterState = {
            pattern_types: [],
            rs_min: 0,
            vol_min: 0,
            rsi_range: '0,100',
            timeframe: 'All',
            confidence_min: 0.5,
            symbols: [],
            sectors: []
        };
        
        this.table = null;
        this.filterPanel = null;
        this.lastUpdate = null;
        this.autoRefreshInterval = null;
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="pattern-scanner">
                <div class="scanner-layout">
                    <!-- Filter Panel -->
                    <div class="filter-sidebar" id="filter-panel">
                        <!-- Populated by FilterPanel component -->
                    </div>
                    
                    <!-- Main Content -->
                    <div class="scanner-content">
                        <!-- Table Container -->
                        <div class="table-section">
                            <div id="patterns-table">
                                <!-- Populated by DataTable component -->
                            </div>
                        </div>
                        
                        <!-- Chart Section (Initially Hidden) -->
                        <div class="chart-section collapsed" id="chart-section">
                            <div class="chart-header">
                                <h3>📈 Chart: <span id="chart-symbol">Select a pattern</span></h3>
                                <button class="chart-toggle" id="chart-toggle">Collapse</button>
                            </div>
                            <div class="chart-content" id="chart-content">
                                <!-- Chart loaded here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.initializeComponents();
        this.bindEvents();
        this.loadInitialData();
        this.startAutoRefresh();
    }
    
    initializeComponents() {
        // Initialize filter panel
        this.filterPanel = new FilterPanel('filter-panel', {
            onFilterChange: this.handleFilterChange.bind(this),
            initialState: this.filterState
        });
        
        // Initialize data table
        this.table = new DataTable('patterns-table', {
            columns: [
                {
                    key: 'symbol',
                    title: 'Symbol',
                    className: 'symbol-col',
                    formatter: (value) => `<strong>${value}</strong>`
                },
                {
                    key: 'pattern',
                    title: 'Pattern',
                    className: 'pattern-col',
                    formatter: (value, row) => `
                        <span class="pattern-badge pattern-${value.toLowerCase()}">
                            ${value}
                        </span>
                    `
                },
                {
                    key: 'conf',
                    title: 'Conf',
                    className: 'confidence-col',
                    formatter: (value) => `
                        <span class="confidence-value conf-${this.getConfidenceClass(value)}">
                            ${value}
                        </span>
                    `
                },
                {
                    key: 'rs',
                    title: 'RS',
                    className: 'rs-col',
                    formatter: (value) => `
                        <span class="rs-value ${parseFloat(value) > 1.2 ? 'rs-high' : ''}">
                            ${value}
                        </span>
                    `
                },
                {
                    key: 'vol',
                    title: 'Vol',
                    className: 'vol-col',
                    formatter: (value) => `
                        <span class="vol-value ${parseFloat(value) > 2.0 ? 'vol-high' : ''}">
                            ${value}
                        </span>
                    `
                },
                {
                    key: 'price',
                    title: 'Price',
                    className: 'price-col'
                },
                {
                    key: 'chg',
                    title: 'Chg',
                    className: 'change-col',
                    formatter: (value) => {
                        const isPositive = parseFloat(value) >= 0;
                        return `
                            <span class="price-change ${isPositive ? 'positive' : 'negative'}">
                                ${value}
                            </span>
                        `;
                    }
                },
                {
                    key: 'time',
                    title: 'Time',
                    className: 'time-col'
                },
                {
                    key: 'exp',
                    title: 'Exp',
                    className: 'expiration-col',
                    formatter: (value) => {
                        const isExpiring = value === 'Expired' || 
                                         (value.includes('m') && parseInt(value) < 60);
                        return `
                            <span class="expiration ${isExpiring ? 'expiring' : ''}">
                                ${value}
                            </span>
                        `;
                    }
                },
                {
                    key: 'chart',
                    title: 'Chart',
                    className: 'chart-col',
                    formatter: (value, row) => `
                        <button class="chart-btn" data-symbol="${row.symbol}" title="View Chart">
                            📊
                        </button>
                    `
                }
            ],
            pageSize: 30,
            sortable: true
        });
        
        // Set table event handlers
        this.table.onRowChart = this.handleChartRequest.bind(this);
        this.table.onSelectionChange = this.handleRowSelection.bind(this);
    }
    
    bindEvents() {
        // Chart toggle
        document.getElementById('chart-toggle').addEventListener('click', () => {
            this.toggleChart();
        });
        
        // Window resize handler
        window.addEventListener('resize', this.throttle(this.handleResize.bind(this), 250));
    }
    
    async loadInitialData() {
        try {
            this.showLoading(true);
            const response = await PatternAPI.scanPatterns(this.filterState);
            this.table.setData(response.patterns, response.pagination?.total);
            this.lastUpdate = new Date();
        } catch (error) {
            this.showError('Failed to load pattern data: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async handleFilterChange(newFilters) {
        this.filterState = { ...this.filterState, ...newFilters };
        await this.refreshData();
    }
    
    async refreshData() {
        try {
            const response = await PatternAPI.scanPatterns(this.filterState);
            this.table.setData(response.patterns, response.pagination?.total);
            this.lastUpdate = new Date();
        } catch (error) {
            this.showError('Failed to refresh data: ' + error.message);
        }
    }
    
    handleChartRequest(symbol) {
        this.loadChart(symbol);
        this.expandChart();
    }
    
    handleRowSelection(selectedIndices) {
        // Handle row selection for bulk operations
        console.log('Selected rows:', selectedIndices);
    }
    
    async loadChart(symbol) {
        const chartSection = document.getElementById('chart-section');
        const chartContent = document.getElementById('chart-content');
        const chartSymbol = document.getElementById('chart-symbol');
        
        chartSymbol.textContent = symbol;
        chartContent.innerHTML = '<div class="chart-loading">Loading chart...</div>';
        
        try {
            // For Phase 2, use placeholder chart
            // In Phase 6, this will be replaced with real charting library
            setTimeout(() => {
                chartContent.innerHTML = `
                    <div class="chart-placeholder">
                        <h3>📈 ${symbol} Chart</h3>
                        <p>Chart integration coming in Phase 6</p>
                        <div class="chart-mock">
                            <div class="chart-bar" style="height: 60%"></div>
                            <div class="chart-bar" style="height: 80%"></div>
                            <div class="chart-bar" style="height: 45%"></div>
                            <div class="chart-bar" style="height: 90%"></div>
                            <div class="chart-bar" style="height: 70%"></div>
                            <div class="chart-bar" style="height: 95%"></div>
                            <div class="chart-bar" style="height: 85%"></div>
                        </div>
                    </div>
                `;
            }, 500);
        } catch (error) {
            chartContent.innerHTML = `<div class="chart-error">Failed to load chart: ${error.message}</div>`;
        }
    }
    
    expandChart() {
        const chartSection = document.getElementById('chart-section');
        chartSection.classList.remove('collapsed');
        document.getElementById('chart-toggle').textContent = 'Collapse';
    }
    
    toggleChart() {
        const chartSection = document.getElementById('chart-section');
        const toggle = document.getElementById('chart-toggle');
        
        if (chartSection.classList.contains('collapsed')) {
            chartSection.classList.remove('collapsed');
            toggle.textContent = 'Collapse';
        } else {
            chartSection.classList.add('collapsed');
            toggle.textContent = 'Expand';
        }
    }
    
    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(async () => {
            // Check for new patterns without full refresh
            try {
                const response = await PatternAPI.scanPatterns({
                    ...this.filterState,
                    since: this.lastUpdate?.toISOString()
                });
                
                if (response.patterns && response.patterns.length > 0) {
                    this.table.updateData(response.patterns);
                    this.lastUpdate = new Date();
                }
            } catch (error) {
                console.warn('Auto-refresh failed:', error);
            }
        }, 30000); // 30 second intervals
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
    
    getConfidenceClass(confidence) {
        if (confidence >= 0.9) return 'very-high';
        if (confidence >= 0.8) return 'high';
        if (confidence >= 0.7) return 'medium';
        return 'low';
    }
    
    showLoading(show) {
        const existing = this.container.querySelector('.loading-overlay');
        if (show && !existing) {
            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="loading-spinner"></div>
                    <p>Loading patterns...</p>
                </div>
            `;
            this.container.appendChild(overlay);
        } else if (!show && existing) {
            existing.remove();
        }
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <div class="error-content">
                <span class="error-icon">⚠️</span>
                <span class="error-text">${message}</span>
                <button class="error-close">&times;</button>
            </div>
        `;
        
        this.container.appendChild(errorDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
        
        // Manual close
        errorDiv.querySelector('.error-close').addEventListener('click', () => {
            errorDiv.remove();
        });
    }
    
    handleResize() {
        // Handle responsive layout changes
        const sidebar = this.container.querySelector('.filter-sidebar');
        const content = this.container.querySelector('.scanner-content');
        
        if (window.innerWidth < 768) {
            sidebar.classList.add('mobile-hidden');
        } else {
            sidebar.classList.remove('mobile-hidden');
        }
    }
    
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }
    
    destroy() {
        this.stopAutoRefresh();
        // Clean up other resources
    }
}

// Register component for GoldenLayout
window.PatternScanner = PatternScanner;
```

### Task 2.4: GoldenLayout Integration (Days 7-10)

#### 2.4.1 GoldenLayout Configuration
**File**: `static/js/services/LayoutManager.js`

```javascript
class LayoutManager {
    constructor() {
        this.layout = null;
        this.components = {};
        this.defaultConfig = {
            settings: {
                hasHeaders: true,
                constrainDragToContainer: true,
                reorderEnabled: true,
                selectionEnabled: false,
                popoutWholeStack: false,
                blockedPopoutsThrowError: true,
                closePopoutsOnUnload: true,
                showPopoutIcon: true,
                showMaximiseIcon: true,
                showCloseIcon: true
            },
            dimensions: {
                borderWidth: 5,
                minItemHeight: 200,
                minItemWidth: 200,
                headerHeight: 30,
                dragProxyWidth: 300,
                dragProxyHeight: 200
            },
            labels: {
                close: 'Close',
                maximise: 'Maximize',
                minimise: 'Minimize',
                popout: 'Pop Out'
            },
            content: [{
                type: 'tabset',
                children: [
                    {
                        type: 'component',
                        componentName: 'PatternScanner',
                        title: 'Pattern Scanner',
                        isClosable: false
                    },
                    {
                        type: 'component',
                        componentName: 'MarketBreadth',
                        title: 'Market Breadth',
                        isClosable: false
                    },
                    {
                        type: 'component',
                        componentName: 'MyFocus',
                        title: 'My Focus',
                        isClosable: false
                    }
                ]
            }]
        };
        
        this.init();
    }
    
    init() {
        // Register components
        this.registerComponent('PatternScanner', (container, state) => {
            return new PatternScanner(container.getElement()[0]);
        });
        
        this.registerComponent('MarketBreadth', (container, state) => {
            return new MarketBreadth(container.getElement()[0]);
        });
        
        this.registerComponent('MyFocus', (container, state) => {
            return new MyFocus(container.getElement()[0]);
        });
        
        // Load saved layout or use default
        const savedLayout = this.loadLayout();
        const config = savedLayout || this.defaultConfig;
        
        // Initialize GoldenLayout
        this.layout = new GoldenLayout(config, $('#golden-layout-container'));
        
        // Register components with GoldenLayout
        Object.keys(this.components).forEach(name => {
            this.layout.registerComponent(name, this.components[name]);
        });
        
        // Bind events
        this.bindEvents();
        
        // Initialize layout
        this.layout.init();
        
        // Auto-save layout changes
        this.layout.on('stateChanged', () => {
            this.saveLayout();
        });
    }
    
    registerComponent(name, factory) {
        this.components[name] = factory;
    }
    
    bindEvents() {
        this.layout.on('initialised', () => {
            console.log('Layout initialized');
            this.onLayoutReady?.();
        });
        
        this.layout.on('windowOpened', (window) => {
            console.log('Window opened:', window);
        });
        
        this.layout.on('windowClosed', () => {
            console.log('Window closed');
        });
        
        this.layout.on('stackCreated', (stack) => {
            // Customize tab behavior
            stack.on('activeContentItemChanged', (contentItem) => {
                console.log('Tab changed:', contentItem.config.title);
            });
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            if (this.layout) {
                this.layout.updateSize();
            }
        });
    }
    
    saveLayout() {
        if (this.layout && this.layout.isInitialised) {
            const state = JSON.stringify(this.layout.toConfig());
            localStorage.setItem('tickstock_layout', state);
        }
    }
    
    loadLayout() {
        try {
            const saved = localStorage.getItem('tickstock_layout');
            return saved ? JSON.parse(saved) : null;
        } catch (error) {
            console.warn('Failed to load saved layout:', error);
            return null;
        }
    }
    
    resetLayout() {
        localStorage.removeItem('tickstock_layout');
        this.layout.destroy();
        this.init();
    }
    
    addTab(config) {
        const activeTabset = this.layout.root.getItemsById('tabset')[0] || 
                            this.layout.root.contentItems[0];
        activeTabset.addChild(config);
    }
    
    closeTab(title) {
        const item = this.layout.root.getItemsByFilter(item => 
            item.config.title === title)[0];
        if (item) {
            item.remove();
        }
    }
    
    focusTab(title) {
        const item = this.layout.root.getItemsByFilter(item => 
            item.config.title === title)[0];
        if (item && item.parent) {
            item.parent.setActiveContentItem(item);
        }
    }
    
    getActiveTab() {
        const activeItem = this.layout.selectedItem;
        return activeItem ? activeItem.config.title : null;
    }
    
    destroy() {
        if (this.layout) {
            this.layout.destroy();
            this.layout = null;
        }
    }
}

// Global instance
window.layoutManager = new LayoutManager();
```

### Task 2.5: Responsive CSS Framework (Days 8-10)

#### 2.5.1 Core Layout Styles
**File**: `static/css/layout.css`

```css
/* GoldenLayout Base Customization */
.lm_root {
    background: var(--bg-primary);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.lm_header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    height: 32px;
}

.lm_header .lm_tab {
    background: var(--bg-secondary);
    border: none;
    color: var(--text-secondary);
    font-weight: 500;
    padding: 0 12px;
    margin-right: 1px;
    transition: all 0.2s ease;
}

.lm_header .lm_tab.lm_active {
    background: var(--bg-primary);
    color: var(--text-primary);
}

.lm_header .lm_tab:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

/* Custom Variables */
:root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --bg-hover: #3d3d3d;
    --text-primary: #ffffff;
    --text-secondary: #cccccc;
    --border-color: #444444;
    --accent-primary: #00d4aa;
    --accent-secondary: #ff6b6b;
    --success-color: #51cf66;
    --warning-color: #ffd43b;
    --error-color: #ff6b6b;
}

/* Application Header */
.app-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    height: 60px;
    box-sizing: border-box;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.app-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
}

.connection-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-secondary);
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    transition: background-color 0.3s ease;
}

.status-dot.connected {
    background-color: var(--success-color);
}

.status-dot.disconnected {
    background-color: var(--error-color);
}

.status-dot.connecting {
    background-color: var(--warning-color);
    animation: pulse 1.5s ease-in-out infinite;
}

/* Header Actions */
.header-right {
    display: flex;
    gap: 8px;
}

.btn {
    padding: 6px 12px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn:hover {
    background: var(--bg-hover);
    border-color: var(--accent-primary);
}

.btn.btn-primary {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: #000;
}

.btn.btn-secondary {
    background: var(--bg-secondary);
}

/* Main Layout Container */
#golden-layout-container {
    height: calc(100vh - 60px);
    width: 100%;
}

#app-container {
    height: 100vh;
    background: var(--bg-primary);
    color: var(--text-primary);
}

.hidden {
    display: none !important;
}

/* Loading Screen */
.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--bg-primary);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}

.loading-content {
    text-align: center;
    color: var(--text-primary);
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--border-color);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 16px;
}

/* Animations */
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Pattern Scanner Layout */
.pattern-scanner {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.scanner-layout {
    display: flex;
    flex: 1;
    min-height: 0;
}

.filter-sidebar {
    width: 280px;
    min-width: 280px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    overflow-y: auto;
}

.scanner-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.table-section {
    flex: 1;
    min-height: 0;
}

.chart-section {
    height: 300px;
    border-top: 1px solid var(--border-color);
    background: var(--bg-secondary);
    transition: height 0.3s ease;
    overflow: hidden;
}

.chart-section.collapsed {
    height: 40px;
}

.chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    height: 40px;
    box-sizing: border-box;
}

.chart-header h3 {
    margin: 0;
    font-size: 14px;
    color: var(--text-primary);
}

.chart-toggle {
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 4px 8px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
}

.chart-toggle:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.chart-content {
    height: calc(100% - 40px);
    overflow: auto;
}

/* Modal Styles */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
}

.modal-content {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    width: 90%;
    max-width: 800px;
    max-height: 80%;
    overflow: auto;
    position: relative;
}

.modal-close {
    position: absolute;
    top: 12px;
    right: 16px;
    font-size: 24px;
    color: var(--text-secondary);
    cursor: pointer;
    z-index: 1;
}

.modal-close:hover {
    color: var(--text-primary);
}
```

#### 2.5.2 Data Table Styles
**File**: `static/css/table.css`

```css
/* Data Table Styles */
.data-table-wrapper {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
}

.table-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
}

.table-info {
    display: flex;
    gap: 16px;
    align-items: center;
}

.result-count {
    font-weight: 600;
    color: var(--text-primary);
}

.last-updated {
    font-size: 12px;
    color: var(--text-secondary);
}

.table-actions {
    display: flex;
    gap: 8px;
    align-items: center;
}

.page-size-selector {
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    font-size: 12px;
}

.export-btn {
    padding: 4px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    cursor: pointer;
    font-size: 12px;
}

.export-btn:hover {
    background: var(--bg-hover);
}

/* Table Container */
.table-container {
    flex: 1;
    overflow: auto;
    min-height: 0;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

/* Table Header */
.table-header {
    background: var(--bg-secondary);
    position: sticky;
    top: 0;
    z-index: 10;
}

.table-header th {
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-color);
    white-space: nowrap;
    user-select: none;
    position: relative;
}

.table-header th.sortable {
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.table-header th.sortable:hover {
    background: var(--bg-hover);
}

.sort-indicator {
    font-size: 10px;
    margin-left: 4px;
    opacity: 0.6;
}

.sort-indicator.sort-asc,
.sort-indicator.sort-desc {
    opacity: 1;
    color: var(--accent-primary);
}

/* Table Body */
.table-body tr {
    border-bottom: 1px solid var(--border-color);
    transition: background-color 0.15s ease;
}

.table-body tr:hover {
    background: var(--bg-hover);
}

.table-body tr.selected {
    background: rgba(0, 212, 170, 0.1);
    border-color: var(--accent-primary);
}

.table-body td {
    padding: 6px 12px;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Column-specific styles */
.symbol-col {
    width: 80px;
    min-width: 80px;
}

.pattern-col {
    width: 120px;
    min-width: 120px;
}

.confidence-col {
    width: 60px;
    min-width: 60px;
    text-align: center;
}

.rs-col,
.vol-col {
    width: 50px;
    min-width: 50px;
    text-align: right;
}

.price-col {
    width: 80px;
    min-width: 80px;
    text-align: right;
}

.change-col {
    width: 60px;
    min-width: 60px;
    text-align: right;
}

.time-col {
    width: 50px;
    min-width: 50px;
    text-align: center;
}

.expiration-col {
    width: 50px;
    min-width: 50px;
    text-align: center;
}

.chart-col {
    width: 50px;
    min-width: 50px;
    text-align: center;
}

/* Data value styling */
.pattern-badge {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 500;
    background: var(--bg-hover);
    color: var(--text-primary);
}

.confidence-value {
    font-weight: 600;
}

.conf-very-high {
    color: #51cf66;
}

.conf-high {
    color: #74c0fc;
}

.conf-medium {
    color: #ffd43b;
}

.conf-low {
    color: #ff8787;
}

.rs-value.rs-high,
.vol-value.vol-high {
    color: var(--success-color);
    font-weight: 600;
}

.price-change.positive {
    color: var(--success-color);
}

.price-change.negative {
    color: var(--error-color);
}

.expiration.expiring {
    color: var(--warning-color);
    font-weight: 600;
}

.chart-btn {
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 2px 6px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s ease;
}

.chart-btn:hover {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

/* Pagination */
.table-pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    flex-shrink: 0;
}

.pagination-info {
    font-size: 12px;
    color: var(--text-secondary);
}

.pagination-controls {
    display: flex;
    gap: 4px;
    align-items: center;
}

.pagination-btn,
.page-btn {
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
    min-width: 24px;
    text-align: center;
}

.pagination-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.pagination-btn:hover:not(:disabled),
.page-btn:hover {
    background: var(--bg-hover);
}

.page-btn.active {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

.page-ellipsis {
    padding: 4px 2px;
    color: var(--text-secondary);
}

.page-numbers {
    display: flex;
    gap: 2px;
    align-items: center;
}

/* Notifications */
.update-notification {
    position: absolute;
    top: 16px;
    right: 16px;
    background: var(--success-color);
    color: #000;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    z-index: 1000;
    animation: slideIn 0.3s ease;
}

.update-notification.fade-out {
    animation: slideOut 0.3s ease forwards;
}

.error-message {
    position: absolute;
    top: 16px;
    right: 16px;
    background: var(--error-color);
    color: #fff;
    border-radius: 4px;
    z-index: 1000;
    animation: slideIn 0.3s ease;
}

.error-content {
    display: flex;
    align-items: center;
    padding: 8px 16px;
    gap: 8px;
}

.error-close {
    background: none;
    border: none;
    color: #fff;
    font-size: 16px;
    cursor: pointer;
    padding: 0;
    margin-left: 8px;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOut {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(100%);
        opacity: 0;
    }
}
```

## Testing Strategy

### Component Testing
**File**: `tests/test_pattern_scanner_ui.js`

```javascript
// Jest tests for Pattern Scanner UI components
describe('PatternScanner Component', () => {
    let container;
    let patternScanner;
    
    beforeEach(() => {
        container = document.createElement('div');
        document.body.appendChild(container);
        patternScanner = new PatternScanner(container);
    });
    
    afterEach(() => {
        document.body.removeChild(container);
        patternScanner.destroy();
    });
    
    test('should initialize with default filter state', () => {
        expect(patternScanner.filterState.timeframe).toBe('All');
        expect(patternScanner.filterState.confidence_min).toBe(0.5);
    });
    
    test('should render table with correct columns', () => {
        const table = container.querySelector('.data-table');
        expect(table).toBeTruthy();
        
        const headers = table.querySelectorAll('th');
        expect(headers.length).toBe(10); // All columns present
    });
    
    test('should handle filter changes', async () => {
        const newFilters = { pattern_types: ['Breakout'], rs_min: 1.2 };
        await patternScanner.handleFilterChange(newFilters);
        
        expect(patternScanner.filterState.pattern_types).toEqual(['Breakout']);
        expect(patternScanner.filterState.rs_min).toBe(1.2);
    });
    
    test('should expand chart when row clicked', () => {
        patternScanner.handleChartRequest('AAPL');
        const chartSection = container.querySelector('.chart-section');
        expect(chartSection.classList.contains('collapsed')).toBe(false);
    });
});

describe('DataTable Component', () => {
    let container;
    let dataTable;
    
    beforeEach(() => {
        container = document.createElement('div');
        container.id = 'test-table';
        document.body.appendChild(container);
        
        dataTable = new DataTable('test-table', {
            columns: [
                { key: 'symbol', title: 'Symbol' },
                { key: 'price', title: 'Price' }
            ]
        });
    });
    
    afterEach(() => {
        document.body.removeChild(container);
    });
    
    test('should render empty table initially', () => {
        const tbody = container.querySelector('.table-body');
        expect(tbody.children.length).toBe(0);
    });
    
    test('should populate data correctly', () => {
        const testData = [
            { symbol: 'AAPL', price: '$150.00' },
            { symbol: 'GOOGL', price: '$2800.00' }
        ];
        
        dataTable.setData(testData);
        
        const rows = container.querySelectorAll('.table-row');
        expect(rows.length).toBe(2);
        expect(rows[0].textContent).toContain('AAPL');
        expect(rows[1].textContent).toContain('GOOGL');
    });
    
    test('should handle sorting', () => {
        const testData = [
            { symbol: 'GOOGL', price: 2800 },
            { symbol: 'AAPL', price: 150 }
        ];
        
        dataTable.setData(testData);
        dataTable.sort('symbol');
        
        const rows = container.querySelectorAll('.table-row');
        expect(rows[0].textContent).toContain('AAPL');
        expect(rows[1].textContent).toContain('GOOGL');
    });
    
    test('should handle pagination', () => {
        const testData = Array.from({length: 100}, (_, i) => ({
            symbol: `SYM${i}`,
            price: i * 10
        }));
        
        dataTable.options.pageSize = 20;
        dataTable.setData(testData);
        
        const visibleRows = container.querySelectorAll('.table-row');
        expect(visibleRows.length).toBe(20);
        
        dataTable.goToPage(2);
        const secondPageRows = container.querySelectorAll('.table-row');
        expect(secondPageRows[0].textContent).toContain('SYM20');
    });
});
```

## Deployment Checklist

- [ ] All UI components render correctly
- [ ] GoldenLayout tabs functional with state persistence
- [ ] Table performance tested with 1,000+ rows
- [ ] Responsive design works on all target devices
- [ ] WebSocket integration receives real-time updates
- [ ] Filter panel applies filters correctly
- [ ] Chart placeholder displays when row clicked
- [ ] Export functionality works
- [ ] Error handling displays user-friendly messages
- [ ] Loading states implemented
- [ ] Unit tests achieve 90%+ coverage

## Next Phase Handoff

**Phase 3 Prerequisites:**
- Basic table UI fully functional
- GoldenLayout system operational
- Real-time updates working via WebSocket
- Responsive design implemented and tested

**UI Foundation Ready For:**
- Advanced filtering system (Phase 3)
- Saved filter sets and presets
- Complex multi-criteria searches
- Enhanced user interaction patterns

This foundation provides a solid, performant base for building advanced filtering capabilities in Phase 3.