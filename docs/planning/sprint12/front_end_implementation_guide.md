#### front_end_implementation_guide.md

# TickStock.ai Front-End Implementation Guide

**Document**: Guide for Building Index.html UI  
**Last Updated**: 2025-08-30  
**Status**: Ready for Sprint 12  
**Related**: ui_design_spec.md, user stories 1-3.x, tickstockpl-integration-guide.md.

---

## Overview
This guide provides step-by-step instructions to implement the tabbed hub on index.html, integrating with TickStockApp's WebSockets and TickStockPL's events. Keep bootstrap-friendly: Minimal deps, focus on HTML/JS. Phase 1: Tabs; Phase 2: Grid/pop-outs.

## Tech Stack & Setup
- **Bootstrap**: CDN for tabs (`<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">`, similar for JS).
- **Charts**: Chart.js CDN for OHLCV embeds.
- **Grid**: Gridstack.js CDN (Phase 2).
- **WebSockets**: Native JS in TickStockApp to subscribe to Redis channels (e.g., tickstock.events.patterns).

## Step-by-Step Implementation
### Phase 1: Tabs
1. Add tab structure to index.html (see ui_design_spec.md snippet).
2. Populate Dashboard: Use JS to fetch watchlist from DB via TickStockApp API; render table with sorting (e.g., `table.sortable()`).
3. Charts: Embed `<canvas id="ohlcvChart">`; JS: `new Chart(ctx, {type: 'candlestick', data: blendedDataFromDataBlender});` Add overlays via annotations plugin.
4. Alerts: JS listener: `const ws = new WebSocket('ws://tickstockapp:port'); ws.onmessage = (event) => { addToast(JSON.parse(event.data)); }`
5. Handle user prefs: Store filters in localStorage; sync to TimescaleDB (users table).

### Phase 2: Grid & Pop-Outs
1. Add gridstack: `<div class="grid-stack"> <div class="grid-stack-item">Panel Content</div> </div>`
2. Pop-Outs: `function popOut(id) { window.open('view.html?id=' + id, '_blank'); }` – view.html loads isolated component with WS.

## Integration with Backend
- Real-Time: Subscribe to Redis via TickStockApp (e.g., for pattern events).
- Historical: Trigger 0.1 jobs for data loads; blend in DataBlender for charts.
- Error Handling: Fallback UI messages for WS disconnects.

## Deployment Notes
Host index.html statically; dynamic parts via TickStockApp. Test perf: <200ms updates.
