# TickStock.ai Sprint Plan: Sprint 4 - TickStockApp Cleanup & Refactoring

## Overview
Sprint 4 is the major gutting sprint where you remove legacy code from TickStockApp to prepare it as a clean shell for the new architecture. This aligns with Phase 2: Cleanup & Prep, focusing on streamlining TickStockApp to act purely as a data ingestion and event consumption hub, with all heavy pattern detection offloaded to TickStockPL.

☐ Sprint 4: TickStockApp Cleanup & Refactoring

**Phase 2: Cleanup & Prep (Sprint 4)**  
- Sprint 4: TickStockApp Cleanup & Refactoring  
**Milestone:** Validate cleaned TickStockApp shell with basic WebSockets forwarding.

## What Gets Removed
- Universe filtering logic (deprecated)
- User filtering mechanisms (outdated)
- Old event detection systems (being replaced by TickStockPL)
- Legacy event handlers
- Unused modules and dependencies

## What Gets Refactored
- WebSockets handler - Align with websockets_integration.md spec for Polygon.io integration
- Processing architecture - Strip down to core pub-sub event consumption
- Database interactions - Simplify to user data and event logging only

## What Remains (Core Shell)
- WebSockets/REST ingestion - Clean data ingestion pipeline
- Event subscriber - Redis pub-sub for pattern events from TickStockPL
- UI hooks - Frontend integration points
- User authentication & management
- Basic dashboard framework

## Key Tasks
1. Audit codebase - Identify all deprecated/legacy components
2. Remove junk - Delete unused filtering logic and old event systems
3. Refactor WebSockets - Implement new Polygon.io per-minute OHLCV pipeline
4. Streamline architecture - Reduce to essential components only
5. Update documentation - Document the new clean shell in architecture_overview.md

**Outcome:** TickStockApp becomes a lightweight shell focused purely on user interface and event consumption, with all heavy pattern detection moved to TickStockPL.

## Expanded Key Activities
- **Audit & Remove Bloat (Days 1-2):** Dive into TickStockApp's codebase (e.g., app.py, handlers/, models/) to identify and excise outdated components. Target junk like legacy universe filtering (e.g., symbol lists/users), old in-app detectors (e.g., any built-in pattern logic—migrate to TickStockPL), and deprecated events (e.g., non-Redis pub-sub). Use git for safe branching; grep for terms like "filter", "detect", "legacy" to spot cruft. Tie to our vision: Keep only essentials for data hub role—user auth, dashboard stubs, and portfolio basics if they align with signal consumption. Goal: Reduce code footprint by 30-50% for faster loads/scalability (per User Story 7).
- **Refactor WebSockets for Integration (Days 2-3):** Update the WebSockets handler (e.g., websockets_integration.md refs) to ingest Polygon per-minute OHLCV, append ticks, and forward to Redis "tickstock_data" channel as JSON (e.g., {'symbol': 'AAPL', 'timestamp': '...', 'open': ..., etc.}). Ensure modular swaps (e.g., config for Polygon/yfinance fallback per User Story 6). Add lightweight validation (e.g., timestamp UTC, handle partial bars) and retries for outages (exponential backoff per User Story 13). No heavy processing here—keep latency <50ms by offloading blends to TickStockPL's DataBlender.
- **Event Subscriber Integration (Days 3-4):** Implement a Redis subscriber for "tickstock_patterns" channel; on event receipt (e.g., Doji detection JSON), process for UI alerts/trades (e.g., dashboard push via Flask/SocketIO) and log to 'events' DB table (SQLAlchemy insert with JSONB details, tying to User Story 11). Stub visuals (e.g., call visuals.py for chart gen per User Story 10) without full impl. Ensure loose coupling: Subscriber runs async, no direct calls to TickStockPL.
- **Basic Forwarding Tests (Day 4):** Run manual/smoke tests: Mock Polygon WS input (e.g., sample AAPL tick) --> forward to Redis --> confirm TickStockPL can consume (use redis-cli to verify). Test event sub: Publish mock pattern event --> check UI/log/DB update. Cover edges like API disconnect (fallback/skip per Story 13). Use pytest for basics if time—no 80% coverage yet (save for Sprint 8).
- **Docs & Config Updates (Day 5):** Refresh architecture_overview.md with refactored TickStockApp diagram/flow (e.g., emphasize Redis as bridge). Add README notes on env vars (e.g., REDIS_URL, POLYGON_KEY). Review for alignment: Cross-check user stories (e.g., Story 5 for param UI stubs, Story 8 for timeframe dropdowns feeding scanner via Redis).
- **Review & Wrap (End of Week):** Quick team session to demo forwarding (e.g., live WS --> Redis --> mock sub). Confirm no regressions; milestone: TickStockApp as clean shell, ready for Sprint 5's patterns.