# Technical Specification: Framework and Architecture for Diverging Threshold Bar and Simple Diverging Bar in Single-Page Application

## Overview

This document provides a comprehensive technical specification for implementing a reusable framework and architecture in a single-page application (SPA) built with Python (backend), CSS, JavaScript, and HTML (frontend). The focus is on rendering "Diverging Threshold Bar" and "Simple Diverging Bar" components, as defined in the reference document ["Diverging and Simple Threshold Bar Definitions.md"](Diverging%20and%20Simple%20Threshold%20Bar%20Definitions.md). These bars visualize advance-decline sentiment in stock market data, supporting both aggregate views (e.g., across sectors, indices, or ETFs) and individual stock views.

The architecture emphasizes modularity for reusability, enabling the rendering of one or multiple instances on a page or UI section. Bars are read-only with no user interactions or events. Data aggregation occurs on the backend to ensure efficiency, with frontend handling rendering via configurable parameters.

### Key Concepts from Reference Document
- **Diverging Threshold Bar**: Partitions data into four segments based on a configurable threshold ($\theta$, default 10%) to highlight minor and significant advances/declines.
- **Simple Diverging Bar**: Simplifies to two segments based on directionality relative to zero, without intensity thresholds.
- Both support horizontal or vertical orientation and use percentage-based mappings for divergence visualization.
- Implementation logic includes population binning, relative frequency calculation, and coordinate mapping, as detailed in the reference.

## Architecture Overview

The framework adopts a client-server model:
- **Backend (Python)**: Handles data retrieval, aggregation, binning, and computation of percentages. Uses libraries like Pandas for data processing and Flask/FastAPI for API endpoints.
- **Frontend (HTML/CSS/JavaScript)**: Renders bars using pure HTML elements (e.g., DIVs for segments) styled with CSS and manipulated via JavaScript for dynamic positioning and widths. Components are encapsulated in reusable JavaScript classes or functions.
- **Communication**: Frontend requests data via RESTful API calls to the backend, passing parameters for customization.
- **Reusability**: A generic "BarRenderer" module abstracts logic, allowing instantiation for single or multiple bars. Configuration objects define type, style, and data sources.
- **Static vs. Dynamic Rendering**:
  - **Static**: Uses pre-aggregated higher-level data (e.g., daily closes); computed once per page load or on schedule.
  - **Dynamic**: Polls intra-day data (e.g., 1-minute OHLCV) via WebSockets or periodic AJAX for real-time updates.
- **Scalability**: Limit instances per page (e.g., <20) to avoid performance issues; use virtualization for scrolling sections.

### Data Handling

Data sources are OHLCV tables in a database (e.g., PostgreSQL or SQLite):
- **Higher-Level Data**: From `ohlcv_daily`, `ohlcv_weekly`, `ohlcv_monthly` tables for periods like daily, weekly, monthly, quarterly, annual. Aggregate changes (e.g., % change from period start).
- **Lower-Level/Intra-Day Data**: From `ohlcv_1min`, `ohlcv_hourly` tables for real-time sentiment (e.g., % change since market open).
- **Aggregation Logic**:
  - For individual stocks: Compute % change ($x$) for the metric (e.g., close vs. previous close).
  - For groups (e.g., S&P 500 constituents): Fetch symbols from a mapping table, compute $x$ per symbol, then bin across the group.
  - Backend performs binning per reference logic to produce JSON output: `{ "segments": { "significant_decline": 25, "minor_decline": 20, ... } }` (percentages).

Example Data Flow:
1. Frontend sends API request: `/api/bars?type=DivergingThresholdBar&data_source=SP500&period=weekly&threshold=0.15&static=true`.
2. Backend queries relevant OHLCV table, aggregates % changes, bins values, and returns pre-mapped percentages.

## Parameters and Configuration

Configurations are passed as JSON objects or query params to the backend API and frontend renderer. Default values ensure minimal setup.

### Core Parameters
- **Type** (string, required): "DivergingThresholdBar" or "SimpleDivergingBar". Extendable for future types (e.g., "CustomBar").
- **Static** (boolean, default: true): True for static (higher-level data); false for dynamic (intra-day, with polling interval e.g., 60s).
- **Threshold** (float, optional): For "DivergingThresholdBar" only; $\theta$ value (default: 0.10). Ignored for "SimpleDivergingBar".
- **Data Source** (string or array, required): 
  - Single stock: e.g., "AAPL".
  - Group: e.g., "SP500" (index), "XLK" (sector ETF), "TECH" (theme), "Semiconductors" (industry). Backend resolves to list of symbols.
- **Period** (string, required): "intraday", "daily", "weekly", "monthly", "quarterly", "annual", "ytd". Maps to data tables and aggregation windows.
- **Metric** (string, default: "percent_change"): The value to bin (e.g., % change in close price). Extendable (e.g., "volume_change").

### Style Configuration
- **Orientation** (string, default: "horizontal"): "horizontal" or "vertical".
- **Dimensions** (object, optional): `{ "width": "100%", "height": "50px" }`. Use relative units for responsiveness.
- **Colors** (object, default standard scheme):
  - For DivergingThresholdBar: `{ "significant_decline": "#B22222" (dark red), "minor_decline": "#FF6347" (light red), "minor_advance": "#90EE90" (light green), "significant_advance": "#228B22" (dark green) }`.
  - For SimpleDivergingBar: `{ "decline": "#FF0000" (red), "advance": "#00FF00" (green) }`.
- **Labels** (boolean, default: true): Show percentage labels on segments.
- **Baseline** (object, optional): `{ "color": "#000000", "width": 1 }` for zero-line styling.

Example Configuration JSON:
```json
{
  "type": "DivergingThresholdBar",
  "static": false,
  "threshold": 0.15,
  "data_source": "SP500",
  "period": "intraday",
  "orientation": "horizontal",
  "colors": { "significant_decline": "#990000", ... }
}
```

## Implementation Instructions

### Backend (Python)
1. **API Endpoint**: Create `/api/bars` (POST/GET) using FastAPI/Flask.
   - Input: Configuration params.
   - Logic:
     - Resolve data source to symbols (e.g., query database for group members).
     - Fetch OHLCV data for period (e.g., using SQLAlchemy: `SELECT close FROM ohlcv_daily WHERE symbol IN symbols AND date >= start_date`).
     - Compute $x$ values (e.g., % change: `(current_close - prev_close) / prev_close`).
     - Apply binning per reference (use if-elif for gates).
     - Calculate percentages.
     - For dynamic: Implement WebSocket endpoint for real-time pushes.
   - Output: JSON with segments and percentages.

2. **Modularity**: Use a `BarAggregator` class:
   ```python
   class BarAggregator:
       def __init__(self, config):
           self.config = config
           # ...

       def aggregate(self):
           # Fetch data, bin, return percentages
           pass
   ```

### Frontend (HTML/CSS/JavaScript)
1. **HTML Structure**: Use a container div per bar instance (e.g., `<div id="bar-1" class="bar-container"></div>`).
2. **CSS**: Define responsive styles:
   ```css
   .bar-container {
       width: 100%;
       height: 50px; /* Configurable */
       position: relative;
       display: flex;
       flex-direction: row; /* For horizontal; change to column for vertical */
       align-items: center;
       overflow: hidden;
   }
   .baseline {
       position: absolute;
       left: 50%; /* For horizontal; top: 50% for vertical */
       height: 100%; /* For horizontal; width: 100% for vertical */
       border-left: 1px solid black; /* Adjust for vertical */
   }
   .segment {
       position: relative;
       text-align: center;
       color: white; /* For readability on colored backgrounds */
   }
   .decline { /* Example for left/negative segments */
       justify-content: flex-end; /* Align labels */
   }
   .advance { /* Example for right/positive segments */
       justify-content: flex-start;
   }
   ```
3. **JavaScript Renderer**: Use pure JavaScript to create and position DIV elements for segments.
   - Create `renderBar(config, containerId)` function:
     ```javascript
     function renderBar(config, containerId) {
         fetch('/api/bars', { method: 'POST', body: JSON.stringify(config) })
             .then(response => response.json())
             .then(data => {
                 const container = document.getElementById(containerId);
                 container.innerHTML = ''; // Clear previous content

                 // Create baseline
                 const baseline = document.createElement('div');
                 baseline.className = 'baseline';
                 baseline.style.backgroundColor = config.baseline?.color || '#000000';
                 baseline.style.width = config.orientation === 'horizontal' ? `${config.baseline?.width || 1}px` : '100%';
                 baseline.style.height = config.orientation === 'horizontal' ? '100%' : `${config.baseline?.width || 1}px`;
                 baseline.style.left = config.orientation === 'horizontal' ? '50%' : '0';
                 baseline.style.top = config.orientation === 'horizontal' ? '0' : '50%';
                 container.appendChild(baseline);

                 // Define segment order for divergence (declines first, then advances)
                 const segmentsOrder = config.type === 'DivergingThresholdBar' 
                     ? ['significant_decline', 'minor_decline', 'minor_advance', 'significant_advance']
                     : ['decline', 'advance'];

                 let currentPosition = 50; // Start at center (percentage)

                 // Render decline segments (negative offset)
                 segmentsOrder.filter(seg => seg.includes('decline')).reverse().forEach(seg => {
                     const percent = data.segments[seg] || 0;
                     if (percent > 0) {
                         const div = document.createElement('div');
                         div.className = `segment decline ${seg}`;
                         div.style.backgroundColor = config.colors[seg];
                         div.style.width = config.orientation === 'horizontal' ? `${percent}%` : '100%';
                         div.style.height = config.orientation === 'horizontal' ? '100%' : `${percent}%`;
                         div.style.position = 'absolute';
                         div.style.right = config.orientation === 'horizontal' ? `${currentPosition}%` : 'auto';
                         div.style.bottom = config.orientation === 'horizontal' ? 'auto' : `${currentPosition}%`;
                         if (config.labels) {
                             div.innerText = `${percent}%`;
                         }
                         container.appendChild(div);
                         currentPosition += percent;
                     }
                 });

                 currentPosition = 50; // Reset for advances

                 // Render advance segments (positive offset)
                 segmentsOrder.filter(seg => seg.includes('advance')).forEach(seg => {
                     const percent = data.segments[seg] || 0;
                     if (percent > 0) {
                         const div = document.createElement('div');
                         div.className = `segment advance ${seg}`;
                         div.style.backgroundColor = config.colors[seg];
                         div.style.width = config.orientation === 'horizontal' ? `${percent}%` : '100%';
                         div.style.height = config.orientation === 'horizontal' ? '100%' : `${percent}%`;
                         div.style.position = 'absolute';
                         div.style.left = config.orientation === 'horizontal' ? `${currentPosition}%` : 'auto';
                         div.style.top = config.orientation === 'horizontal' ? 'auto' : `${currentPosition}%`;
                         if (config.labels) {
                             div.innerText = `${percent}%`;
                         }
                         container.appendChild(div);
                         currentPosition += percent;
                     }
                 });
             });
     }
     ```
   - For multiple bars: Loop over configurations and call `renderBar` for each container.
   - Dynamic Update: Use `setInterval` to refetch if `config.static === false`.

4. **Reusability for Multiple Instances**:
   - In page load: Define an array of configs (e.g., for S&P 500: intraday dynamic, then static weekly/monthly).
   - Dynamically create containers: `document.body.appendChild(div)` for each.
   - Render in parallel: `configs.forEach((cfg, idx) => renderBar(cfg, `bar-${idx}`));`.

## Example Usage

For S&P 500 advance/decline:
- Intraday (dynamic): Config with `period: "intraday"`, `static: false`.
- Weekly (static): Config with `period: "weekly"`.
- Stack vertically with labels like "Intraday Adv/Dec" to the left.

## Testing and Edge Cases
- Test with small groups (1 stock) and large (500+ symbols) for performance.
- Handle zero data: Display empty bar with message.
- Validate configs: Enforce required params on backend.
- Responsiveness: Use media queries for mobile (switch to vertical).

This specification ensures thoroughness by covering data handling, parameters, reusability, and implementation steps, aligned with the reference definitions. If extensions are needed (e.g., more types), update the config schema accordingly.