### User Stories for Sprint 13+

#### Sprint 13: Daily Pattern Detection Display
**Epic: Daily Pattern Detection Display**  
This epic focuses on a new display in the Charts or Dashboard tab, allowing users to select pattern interests (e.g., from our 11+ library like Doji, Hammer) and view daily detections on historical/aggregated data (from ohlcv_daily, post-0.1 loads). Builds on Sprint 12 UI for user selection via dropdowns/filters.

**User Story 13.1:**  
As a swing trader, I want a daily pattern detection display where I can select specific patterns of interest (e.g., MA Crossover, HeadAndShoulders), so that I can focus on relevant signals from historical daily data for long-term analysis.  
*Acceptance Criteria:*  
- UI: Dropdown/multi-select in Dashboard/Charts tab for patterns (pulled from patterns_library_patterns.md).  
- Display: Table or overlaid chart showing detections (symbol, date, pattern, strength, direction).  
- Data: From ohlcv_daily via DataBlender; filter by user selection.  
- Interactive: Click to view details/explanations (links to docs).  
- Perf: <50ms rendering for 100 symbols.  
- Test: Simulate detections on 5 symbols over 1 year.

**User Story 13.2:**  
As an analyst, I want to filter and sort the daily pattern display by criteria like confidence or timeframe, so that I can prioritize high-quality signals.  
*Acceptance Criteria:*  
- Filters: Min confidence, date range, direction (bullish/bearish).  
- Sorting: By strength/date; persists in user prefs DB.  
- Integration: Ties to PatternScanner for batch processing.  
- Edge: Handle no detections (show message).

#### Sprint 14: Intra-Day with Blended Daily and Real-Time
**Epic: Intra-Day Blended Display**  
This epic adds intra-day views blending daily historical (ohlcv_daily) with real-time (WebSockets/ticks via DataBlender), for patterns like Day1Breakout or TrendingUp. Evolves UI with pop-outs for independent monitoring.

**User Story 14.1:**  
As a day trader, I want an intra-day pattern display that blends daily historical data with real-time updates, so that I can see evolving signals (e.g., Hammer in 1min) in context of daily trends.  
*Acceptance Criteria:*  
- Blending: Use DataBlender to merge ohlcv_daily with live ticks (sub-1s latency).  
- UI: Dedicated panel/pop-out in Charts tab; real-time overlays updating via WS.  
- Patterns: Focus on intra-day (e.g., ClosedInTopRange, TrendingUp).  
- Perf: <200ms updates; scalable to 1000+ symbols.

**User Story 14.2:**  
As a professional trader, I want to pop out intra-day displays for independent monitoring, so that I can track multiple real-time blended views without tab switching.  
*Acceptance Criteria:*  
- Pop-Out: Isolated window with WS persistence; includes user-selected patterns.  
- Blending Validation: Test with simulated real-time data on historical base.  
- Edge: Handle data gaps (notifications).