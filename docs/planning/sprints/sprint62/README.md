# Sprint 62 - Historical Data Loading Migration

**Status**: Ready for Implementation
**Priority**: High
**Dependencies**: Sprint 61 ✅ Complete

---

## Quick Summary

Migrate historical data admin interface to use RelationshipCache (definition_groups/group_memberships) instead of hardcoded universe lists. Enable dynamic universe selection with multi-universe join support for all OHLCV timeframes.

## What's Changing

### Before Sprint 62
```python
# Hardcoded in admin_historical_data_redis.py
available_universes = {
    'SP500': 'S&P 500 Components',
    'NASDAQ100': 'NASDAQ 100 Components',
    'ETF': 'Major ETFs'
}
```

### After Sprint 62
```python
# Dynamic from database via RelationshipCache
GET /admin/historical-data/universes
→ Returns all universes from definition_groups

# Multi-universe join support
POST /admin/historical-data/trigger-universe-load
{
    "universe_key": "SPY:nasdaq100",  // 518 stocks
    "timeframes": ["1min", "hour", "day", "week", "month"],
    "years": 2
}
```

## Key Features

✅ **Dynamic Universe Loading** - No code changes to add universes
✅ **Multi-Universe Joins** - Load SPY:nasdaq100 with single click
✅ **All Timeframes** - ohlcv_1min, hourly, daily, weekly, monthly
✅ **Rich Metadata** - Member counts, descriptions in dropdowns
✅ **Single Source of Truth** - Same as WebSocket universe system (Sprint 61)

## Implementation Phases

1. **Extend RelationshipCache** - Add `get_available_universes()` method
2. **Add API Endpoints** - `/universes` and `/trigger-universe-load`
3. **Update Admin UI** - Dynamic dropdown + multi-select
4. **Update JavaScript** - Fetch universes, handle selection
5. **Testing** - 5 test cases, integration tests

## Files Modified

- `src/core/services/relationship_cache.py` (+100 lines)
- `src/api/rest/admin_historical_data_redis.py` (+150 lines)
- `web/templates/admin/historical_data_dashboard.html` (universe section update)
- `web/static/js/admin/historical_data.js` (+200 lines)
- `tests/integration/test_sprint62_historical_load.py` (NEW)

## Success Criteria

- [ ] Dynamic universe dropdown populated from database
- [ ] Multi-universe join working (SPY:nasdaq100 syntax)
- [ ] All 5 OHLCV timeframes load correctly
- [ ] Job submission to TickStockPL works
- [ ] Integration tests pass
- [ ] Zero regression on existing functionality

## See Also

- **Detailed Plan**: [`SPRINT62_PLAN.md`](SPRINT62_PLAN.md)
- **Sprint 61**: [`../sprint61/SPRINT61_COMPLETE.md`](../sprint61/SPRINT61_COMPLETE.md)
- **Architecture**: [`../../architecture/websockets-integration.md`](../../architecture/websockets-integration.md)
