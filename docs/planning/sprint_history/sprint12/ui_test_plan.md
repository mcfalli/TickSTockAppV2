#### ui_test_plan.md

# TickStock.ai UI Test Plan

**Document**: Plan for UI Quality Assurance  
**Last Updated**: 2025-08-30  
**Status**: For Sprint 12 and Beyond  
**Related**: Sprint 8-9 testing frameworks, user stories 1-3.x.

---

## Overview
This plan ensures UI reliability: 80% coverage, perf targets met. Ties to our 637+ backend tests.

## Test Types
- **Unit**: JS functions (e.g., tab switching with Jest).
- **Integration**: WebSockets with mocks (e.g., simulate pattern events).
- **E2E**: Browser automation (Selenium/Puppeteer) for flows (e.g., add symbol → table update).
- **Performance**: Load tests for <1s charts, <200ms alerts.
- **Accessibility**: Manual/automated checks (ARIA, screen readers).

## Key Scenarios
- Dashboard: Sort/filter watchlist; export CSV (3.x).
- Charts: Overlay rendering on historical data (2.x, 0.1).
- Alerts: High-volume handling without lag (1.x).
- Edge: Mobile resize, WS disconnects.

## Tools & CI/CD
- Pytest for JS; integrate with existing pipeline.
- Coverage: Aim 80%; run in Sprint 12.

## Acceptance
Pass all before merge; link to production readiness.
