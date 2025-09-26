# TickStockPL HTTP API Integration Questions

**Date**: 2025-09-26
**Sprint**: 33 Phase 4
**From**: TickStockAppV2 Team
**To**: TickStockPL Development Team

## Context

We've implemented the Sprint 33 Phase 4 integration based on the architecture you provided:
- **Commands**: HTTP API to TickStockPL at `http://localhost:8080`
- **Events**: Redis pub-sub from TickStockPL

## Current Issue

When running `start_both_services.py`, TickStockAppV2 starts successfully but cannot connect to TickStockPL's HTTP API endpoints. We're getting connection timeouts on port 8080.

## Questions

### 1. HTTP API Server Implementation
**Does TickStockPL currently have an HTTP API server implemented?**

We're trying to connect to these endpoints as described in your integration response:
```
POST   http://localhost:8080/api/processing/trigger-manual
GET    http://localhost:8080/api/processing/status
GET    http://localhost:8080/api/processing/history
DELETE http://localhost:8080/api/processing/cancel
GET    http://localhost:8080/api/processing/schedule
POST   http://localhost:8080/api/processing/schedule
POST   http://localhost:8080/api/processing/trigger-import
POST   http://localhost:8080/api/processing/trigger-indicators
POST   http://localhost:8080/api/processing/retry-imports
GET    http://localhost:8080/health
```

### 2. Service Startup
**What needs to be running on the TickStockPL side?**

Currently `start_both_services.py` launches:
```python
# TickStockPL service
service_script = TICKSTOCKPL_PATH / "src" / "services" / "pattern_detection_service.py"
```

Should this script be starting an HTTP server on port 8080? Or is there a different service we should be launching?

### 3. Alternative Integration Approach
**If the HTTP API isn't implemented yet, what's the current way to trigger processing?**

Should we:
- A) Use Redis commands to trigger processing (publish to specific channels)?
- B) Import TickStockPL modules directly and call functions?
- C) Wait for HTTP API implementation?
- D) Implement a temporary bridge/adapter?

### 4. Redis Event Publishing
**Are the Redis events currently being published?**

We're subscribing to these channels (colon notation as you specified):
- `tickstock:processing:status`
- `tickstock:import:started/progress/completed`
- `tickstock:cache:started/progress/completed`
- `tickstock:indicators:started/progress/completed/calculated`
- `tickstock:patterns:started/progress/completed/detected`
- `tickstock:monitoring`
- `tickstock:errors`

### 5. Current TickStockPL Capabilities
**What's currently working in TickStockPL that we can integrate with?**

Please let us know:
- Which integration points are implemented and ready
- Which are planned but not yet implemented
- Any alternative methods we should use in the meantime

## Our Implementation Status

✅ **Completed on TickStockAppV2 side:**
- HTTP API client (`tickstockpl_api_client.py`) ready to call endpoints
- Redis event subscriber (`processing_event_subscriber.py`) listening on all channels
- Database table (`processing_runs`) created for history storage
- Admin dashboard updated to use real integration (no mocks)

We're ready to integrate as soon as we understand what's available on the TickStockPL side.

## Proposed Next Steps

Please advise on:
1. What we should expect to be running when we start TickStockPL
2. Whether the HTTP API exists or if we should use a different approach
3. Any configuration or startup changes needed

Thank you for your guidance on completing this integration!