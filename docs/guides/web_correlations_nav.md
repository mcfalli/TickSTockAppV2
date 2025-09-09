# Correlations Navigation Guide

**Date**: 2025-09-08  
**Version**: Sprint 24 Sidebar Navigation Guide  
**Status**: Active Feature - Sprint 24 (Sidebar Navigation)  
**Dashboard URL**: `/dashboard` (Correlations Navigation)  

---

## Core Identity

### JavaScript Files & Components
- **Primary Service**: `/web/static/js/services/pattern-correlations.js` (656 lines)
  - **Main Class**: `PatternCorrelationsService` (lines 8-654)
  - **Global Instance**: `window.correlationsService` (lines 655-656)
  - **Initialization**: `initialize(containerId)` method (lines 25-57)

### Purpose & Role
The **Correlations Navigation** provides advanced pattern relationship analysis through statistical correlation computation and interactive visualizations. It operates as a **correlation analytics consumer** in TickStock.ai's architecture, consuming processed correlation data rather than performing heavy calculations within the sidebar navigation system.

### Loading Mechanism
```javascript
// Dashboard Integration: web/templates/dashboard/index.html, lines 588-592
case '#correlations-content':
    if (window.correlationsService) {
        await initializeCorrelationsTab();
    }
    break;

// Service Initialization: web/templates/dashboard/index.html, lines 749-759  
async function initializeCorrelationsTab() {
    const correlationsContainer = document.getElementById('correlations-dashboard');
    if (correlationsContainer && window.correlationsService) {
        await window.correlationsService.initialize('correlations-dashboard');
    }
}
```

---

## Functionality Status

### ✅ Fully Implemented (Production Ready)
- **Core Dashboard Elements**: Complete correlation controls, format switching, HTML template structure
- **Pattern Correlations Service**: Full service implementation with initialization and data loading (656 lines)
- **Chart.js Integration**: Complete Chart.js v4.4.0 heatmap visualization with scatter plots and color mapping
- **Mock Data Integration**: Comprehensive fallback data system with realistic correlation coefficients
- **Responsive Layout**: Bootstrap-based responsive grid system with mobile optimization
- **Interactive Features**: Hover tooltips, click interactions, chart cleanup, and format switching
- **Export Functionality**: CSV export with proper file naming and data formatting

### ⚠️ Partially Implemented (Needs Enhancement)
- **Matrix Visualization**: Basic HTML table implementation present, lacks advanced sorting and filtering capabilities
- **Statistical Analysis**: Correlation coefficients calculated, but missing p-value calculations and confidence intervals  
- **Sequential Analysis**: Basic sequential correlation support implemented, needs temporal relationship mapping
- **Real-Time Updates**: Service structure ready for WebSocket integration, requires Sprint 23 backend implementation
- **Data Validation**: Basic error handling present, needs comprehensive data validation and edge case handling

### ❌ Missing Implementation (Gaps)
- **Network Diagram Visualization**: Currently shows placeholder only, requires D3.js implementation for interactive network graphs
- **Backend API Integration**: `/api/analytics/correlations` endpoint not implemented, service uses mock data only
- **Advanced Statistical Features**: No multiple comparison correction, significance testing, or cross-market analysis
- **Real-Time Correlation Updates**: No live correlation recalculation as new patterns are detected
- **Alert System**: Missing correlation alert system for strong relationship discoveries

### 🔧 Technical Debt & Improvements Needed
- **Chart Memory Management**: Need to implement chart instance reuse instead of destroy/recreate pattern
- **Performance Optimization**: Large correlation matrices cause rendering bottlenecks, needs data decimation
- **API Rate Limiting**: Missing request throttling for correlation calculation endpoints
- **Cross-Market Analysis**: No correlation analysis across market sectors or conditions

---

## Component Breakdown

### UI Layout & Structure
```
┌─────────────────────────────────────────────────────────────────┐
│                🔗 PATTERN CORRELATIONS                          │
│   Time: [Last 30 days] Min: [0.3] Type: [All Types] [Refresh]   │
│   Format: [Heatmap*] [Matrix] [Network]                         │
├──────────────────────────────┬──────────────────────────────────┤
│                              │      📊 CORRELATION SUMMARY     │
│    🔥 CORRELATION HEATMAP    │   Total Patterns: 11           │
│                              │   Correlations: 24             │
│  WeeklyBO ████████████ 1.0   │   Avg Correlation: 0.587       │
│  DailyBO  ████████▓▓▓▓ 0.73  │   Max Correlation: 0.730       │
│  Hammer   ████▓▓▓▓▓▓▓▓ 0.45  │   Last Updated: 10:45 AM       │
│  Doji     ███▓▓▓▓▓▓▓▓▓ 0.32   │   Data Quality: ████ Good      │
│                              │                                │
│                              │    🏆 TOP CORRELATIONS         │
│                              │  WeeklyBO ↔ DailyBO   0.730    │
│                              │  Hammer ↔ Doji       0.580    │
│                              │  Engulf ↔ Volume     0.650    │
└──────────────────────────────┴──────────────────────────────────┘
```

### Core Components & Status

#### 1. Correlation Controls Panel ✅ **Fully Functional**
- **Location**: Top control bar with interactive filtering
- **Implementation**: Event handlers in `pattern-correlations.js` lines 86-121
- **Controls**: Time period, minimum correlation threshold, relationship type, manual refresh
- **Auto-refresh**: Triggers `loadCorrelationData()` on parameter changes

#### 2. Visualization Format Selector ✅ **Fully Functional** 
- **Formats**: Heatmap (Chart.js), Matrix (HTML table), Network (placeholder)
- **Implementation**: `switchFormat(format)` method lines 226-234
- **Default**: Heatmap visualization with scatter plot rendering
- **Status**: Heatmap and Matrix working, Network needs D3.js implementation

#### 3. Main Visualization Panel ⚠️ **Partially Complete**
- **Heatmap**: ✅ Complete Chart.js implementation with color mapping (lines 272-356)
- **Matrix**: ⚠️ Basic HTML table, missing sorting and filtering
- **Network**: ❌ Placeholder only, needs D3.js network diagram
- **Canvas ID**: `correlation-heatmap-chart` for Chart.js rendering

#### 4. Correlation Summary Panel ✅ **Fully Functional**
- **Location**: Top right summary card with statistics
- **Implementation**: `updateSummary()` method lines 399-432
- **Metrics**: Total patterns, correlations found, average/max correlation, data quality
- **Real-time**: Updates automatically when correlation data refreshes

#### 5. Top Correlations Panel ✅ **Fully Functional**
- **Location**: Bottom right with ranked correlation list
- **Implementation**: `updateTopCorrelations()` method lines 434-467
- **Features**: Top 5 correlations, color-coded by direction, interactive highlighting
- **Visual Indicators**: Green positive (↗️), red negative (↘️) correlations

---

## TODOs & Missing Features

### 🔴 Critical Priority (Backend Integration)
1. **Implement `/api/analytics/correlations` Endpoint**
   - **Status**: Missing - currently uses mock data only
   - **Requirements**: Sprint 23 backend API with correlation calculations
   - **Data Structure**: Pattern pairs, correlation coefficients, statistical significance

2. **Real-Time Correlation Updates**
   - **Status**: Service structure ready, needs WebSocket integration
   - **Implementation**: Live correlation recalculation as new patterns detected
   - **Performance Target**: <100ms correlation update delivery

3. **Statistical Validation Backend**
   - **Status**: Frontend ready for p-values and confidence intervals
   - **Requirements**: Statistical significance testing, multiple comparison correction
   - **Target**: Bonferroni correction for multiple testing

### 🟡 High Priority (Advanced Features)
4. **Network Diagram Visualization**
   - **Status**: Placeholder implementation only
   - **Requirements**: D3.js integration for interactive network graphs
   - **Features**: Node-link diagrams, cluster indicators, connection strength

5. **Interactive Matrix Enhancements**
   - **Status**: Basic HTML table, needs advanced features
   - **Missing**: Sortable columns, filtering, drill-down capabilities
   - **Target**: Export to Excel, advanced table interactions

---

## Related Documentation

This guide is part of TickStock.ai's comprehensive documentation suite:

**Core Documentation:**
- **[Project Overview](../planning/project-overview.md)** - Complete system vision and TickStockAppV2 consumer role
- **[System Architecture](../architecture/system-architecture.md)** - Role separation between TickStockApp and TickStockPL
- **[User Stories](../planning/user_stories.md)** - User-focused requirements for dashboard functionality

**Navigation Documentation:**
- **[Overview Navigation Guide](web_overview_nav.md)** - Live market metrics and pattern velocity analysis
- **[Performance Navigation Guide](web_performance_nav.md)** - Pattern success rates and reliability analysis
- **[Distribution Navigation Guide](web_distribution_nav.md)** - Pattern frequency and confidence distributions
- **[Historical Navigation Guide](web_historical_nav.md)** - Time-series pattern analysis and trends
- **[Market Navigation Guide](web_market_nav.md)** - Market breadth and sector correlation analysis
- **[Temporal Navigation Guide](web_temporal_nav.md)** - Time-based pattern performance analysis

---

**Last Updated**: 2025-09-08  
**Version**: Restructured Guide v2.0  
**Service Dependencies**: Pattern Correlations Service (656 lines), Chart.js v4.4.0, Bootstrap v5.1.3  
**Browser Support**: Chrome 90+, Firefox 90+, Safari 14+, Edge 90+  
**Status**: Sprint 23 Complete - Production Ready with Mock Data ✅