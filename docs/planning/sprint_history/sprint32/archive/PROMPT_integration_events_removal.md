# Sprint 32: Integration Events Removal - Implementation Prompt

## Quick Start Command
Use this prompt to start a fresh Claude chat for implementing the integration events removal:

---

## PROMPT TO COPY:

I need to implement Sprint 32 Part 1: Removing the integration_events table and DatabaseIntegrationLogger from TickStockAppV2 to improve performance.

Please review `docs/planning/sprints/sprint32/integration_events_removal_plan.md` and help me execute the removal plan safely.

**Current Status:**
- integration_events table exists in database
- DatabaseIntegrationLogger is initialized in app.py
- Multiple test files reference integration events
- This removal will improve latency by 5-10ms per event

**My Goals:**
1. Remove all integration_events references from code
2. Delete DatabaseIntegrationLogger class
3. Clean up test files
4. Drop database table after code deployment
5. Verify no performance regression

**Please start by:**
1. Running safety checks to see if integration_events has any data worth preserving
2. Showing me the exact code changes needed in app.py
3. Identifying all files that need updates
4. Creating a checklist for safe removal

Use the error-handling-specialist agent for this work. The plan is already approved - we're removing this because it adds overhead without value (tracks flow, not errors).

**Environment:**
- Windows development machine
- PostgreSQL + TimescaleDB database
- Python 3.x application
- Redis available

Let's start with the pre-removal safety checks from Phase 1 of the plan.

---

## Additional Context (if needed):

The integration_events table was designed to track successful flow through the system but:
- Adds 5-10ms latency to critical path
- Generates thousands of unnecessary DB writes/minute
- Doesn't help with actual error diagnosis
- Redundant with standard logging

This is a performance optimization, not a feature removal. All the same visibility can be achieved through structured logging.

## Expected Outcome:
After this implementation:
- ✅ No integration_events references in production code
- ✅ Test suite passes without integration logging
- ✅ Pattern processing latency reduced by 5-10ms
- ✅ Database write load significantly decreased
- ✅ Cleaner, simpler codebase
**TickStockPL Instructions** are there any instructions to provide TickStockPL developer to do same within TickStockPL architecture for removal?