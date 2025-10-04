# Sprint 32: Error Exception Strategy - Implementation Prompt

## Quick Start Command
Use this prompt to start a fresh Claude chat for implementing the unified error handling system:

---

## PROMPT TO COPY:

I need to implement Sprint 32 Part 2: Unified error handling system for TickStockAppV2 with file logging, database storage, and Redis integration for TickStockPL errors.

Please review `docs/planning/sprints/sprint32/error_exception_strategy.md` and help me implement the simplified error handling architecture.

**Current Status:**
- We have standard Python logging throughout the app
- No file logging configured
- No database storage for errors
- No integration with TickStockPL errors
- Using config_manager for environment variables

**My Goals:**
1. Enhance existing logger (not replace it)
2. Add configurable file logging with rotation
3. Add database storage for errors above threshold
4. Subscribe to Redis channel for TickStockPL errors
5. Keep it simple - no admin UI in this sprint

**Please start by:**
1. Creating the error_logs database table
2. Adding logging configuration to .env
3. Implementing the EnhancedLogger class
4. Setting up the Redis subscriber for TickStockPL errors

Use the error-handling-specialist agent for this work. Focus on the practical implementation from the strategy document.

**Key Requirements:**
- Config-driven via .env and config_manager
- Severity threshold determines DB storage (e.g., only error and above)
- All errors go to file log if enabled
- Same error format for both TickStockAppV2 and TickStockPL
- Must handle TickStockPL errors from Redis channel `tickstock:errors`

**Environment:**
- Windows development machine
- PostgreSQL + TimescaleDB database
- Python 3.x with Flask
- Redis available
- config_manager already in place

Let's start with Phase 1: Core Infrastructure setup from the strategy.

---

## Additional Context (if needed):

This is about creating a simple but effective error handling system that:
- Doesn't become its own project
- Leverages existing infrastructure
- Provides configurable logging thresholds
- Unifies error handling across both systems

The architecture is:
```
AppV2 Errors → Enhanced Logger → File + DB (if threshold met)
                    ↑
PL Errors → Redis → Subscriber
```

## Configuration Example:
```bash
# .env
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/tickstock.log
LOG_DB_ENABLED=true
LOG_DB_SEVERITY_THRESHOLD=error
REDIS_ERROR_CHANNEL=tickstock:errors
```

## Expected Outcome:
After this implementation:
- ✅ All errors logged to file when enabled
- ✅ Critical errors stored in database
- ✅ TickStockPL errors received and processed
- ✅ Configurable severity thresholds working
- ✅ <100ms error processing time
- ✅ No impact on main app performance