#### ui_design_spec.md

# TickStock.ai UI Design Specification

**Document**: UI Design Spec for Index.html Hub  
**Last Updated**: 2025-08-30  
**Status**: Draft for Sprint 12 Implementation  
**Related**: Ties to user stories 1.x (alerts), 2.x (charts), 3.x (dashboards), and 0.1 (historical data feeds).

---

## Overview
This spec outlines the visual and functional design for the primary index.html page as a tabbed hub, evolving to modular grids and pop-outs. It ensures a fantastic user experience: intuitive for beginners (tooltips/explanations), powerful for pros (customization for 1000+ symbols), and performant (<1s loads). Design principles: Clean hierarchy with white space, color-coding (green bullish, red bearish), mobile-responsive, and accessibility (ARIA labels). Start with tabs to avoid overload; phase in modularity for 10+ controls.

## High-Level Wireframe (Text-Based)
```
[Top Nav: Logo | Search Bar | User Settings (Watchlist Prefs) | Customize Button]

[Tabs: Dashboard* | Charts | Alerts | Backtest (Placeholder)]

[Active Tab Content: e.g., Dashboard]
  [Grid Container (Phase 2: Draggable)]
    [Panel 1: Watchlist Table (Sortable, Filterable)]
    | Symbol | Price | Pattern | Timeframe | Strength | Update |
    |--------|--------|---------|-----------|----------|---------|
    | AAPL  | $150  | Hammer | Daily    | 92%     | Now    |

    [Panel 2: Similar Stocks Sub-Table (Correlated, per 3.2)]

[Footer: Links to Docs | Version Info]
```
- Pop-Out Example: Click ⤢ on a panel → New window with isolated view (e.g., full-screen chart).

## Component Breakdowns
### Tabs (Phase 1 Core)
- **Dashboard Tab (3.x Stories)**: Watchlist table (5-10 rows init) with columns from 3.1; sub-section for similar stocks (3.2). Interactive: Add/remove symbols, export CSV (3.3).
- **Charts Tab (2.x Stories)**: Embed Chart.js for OHLCV; overlays (arrows/tooltips with explanations, per 2.1-2.2). Controls: Timeframe dropdown, zoom/pan.
- **Alerts Tab (1.x Stories)**: Scrolling feed/toasts; filters for day/swing traders (1.1-1.2), config for email/SMS (1.3).
- **Visuals**: Tabs with subtle fade animations; max 4-5 for simplicity.

### Modular Grid & Pop-Outs (Phase 2)
- Grid: Draggable/resizable panels within tabs (e.g., watchlist next to charts).
- Pop-Outs: Independent windows for views like intra-day patterns; persist WebSocket connections.
- Customization: "Customize" button unlocks grid mode; save layouts in localStorage/DB.

## UX Principles & Decisions
- **Hierarchy**: Bold headers, icons for actions (e.g., + for add symbol).
- **Colors/Fonts**: Green/red signals, sans-serif fonts, dark mode toggle.
- **Responsiveness**: Stack tabs vertically on mobile.
- **Alternatives Considered**: Single-page (too cluttered); full SPA (overkill for bootstrap).
- **Ties to Architecture**: WebSocket updates for real-time; historical data from 0.1 feeds charts.

## Next Steps
Prototype in Sprint 12; test with synthetic data before real-time integration.
