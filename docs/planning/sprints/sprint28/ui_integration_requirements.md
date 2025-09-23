# UI Integration Requirements for Sprint 28

**Date**: 2025-01-22
**Current State**: Backend Redis integration complete, UI updates needed

## Summary

The backend Redis job submission is fully implemented and tested. The UI needs updates to properly integrate with the new Redis-based historical data loading system.

## Current UI State

### ✅ What's Working
1. **Navigation**: Links to `/admin/historical-data` exist in:
   - Main dashboard dropdown (`web/templates/dashboard/index.html`)
   - Admin user dashboard
   - Admin health dashboard

2. **Backend Routes**: Redis-based routes are registered and working:
   - `/admin/historical-data` - Main dashboard
   - `/admin/historical-data/trigger-load` - Job submission
   - `/admin/historical-data/job/<job_id>/status` - Status polling
   - `/api/admin/historical-data/load` - API endpoint

3. **JavaScript**: Created `web/static/js/admin/historical_data.js` with:
   - Job submission functionality
   - Status polling mechanism
   - Progress bar updates
   - Redis connection testing

### ❌ What Needs Updating

1. **Template Location Issue**:
   - Current template renders: `admin/historical_data_dashboard.html`
   - New template created at: `web/templates/admin/historical_data.html`
   - Need to integrate Redis features into existing template

2. **Missing UI Elements**:
   - Redis connection status indicators
   - TickStockPL service status display
   - Job progress visualization
   - Real-time job status updates

3. **JavaScript Integration**:
   - Link the new `historical_data.js` to the template
   - Ensure CSRF token handling
   - Add notification system for job updates

## Required UI Changes

### 1. Update Existing Template
**File**: `web/templates/admin/historical_data_dashboard.html`

Add these elements:

```html
<!-- Add to <head> section -->
<meta name="csrf-token" content="{{ csrf_token() }}">

<!-- Add Redis Status Section (after navigation) -->
<div class="alert alert-info mb-4">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <strong>System Status:</strong>
            <span id="redis-status" class="status-indicator status-disconnected ms-2">Redis Checking...</span>
            <span id="tickstockpl-status" class="status-indicator status-disconnected ms-2">TickStockPL Checking...</span>
        </div>
        <button id="test-redis" class="btn btn-sm btn-outline-primary">Test Connection</button>
    </div>
</div>

<!-- Update Job Submission Form -->
<!-- Replace existing form with Redis-based submission -->
<form id="data-load-form" method="POST" action="/admin/historical-data/trigger-load">
    <!-- Add load type selection (symbols, universe, multi-timeframe) -->
    <!-- Update to use Redis job submission -->
</form>

<!-- Add Job Progress Container -->
<div id="job-status-container" style="display: none;">
    <h5>Job Progress</h5>
    <div id="job-status" class="mb-2">Waiting...</div>
    <div class="progress">
        <div id="progress-bar" class="progress-bar progress-bar-striped progress-bar-animated"
             role="progressbar" style="width: 0%;">0%</div>
    </div>
</div>

<!-- Add at bottom before </body> -->
<script src="{{ url_for('static', filename='js/admin/historical_data.js') }}"></script>
```

### 2. Add Status Indicators CSS
```css
.status-indicator {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}
.status-connected { background: #d4edda; color: #155724; }
.status-disconnected { background: #f8d7da; color: #721c24; }

.job-status-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
}
.status-submitted { background: #cfe2ff; color: #084298; }
.status-running { background: #fff3cd; color: #856404; }
.status-completed { background: #d1e7dd; color: #0f5132; }
.status-failed { background: #f8d7da; color: #842029; }
```

### 3. Update Active Jobs Display
Replace the static job display with dynamic job cards that update via polling:

```html
<div id="active-jobs">
    <!-- Jobs will be dynamically added here by JavaScript -->
</div>
```

### 4. Add Notification System
```html
<div id="notification" class="notification"></div>

<style>
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 8px;
    z-index: 1000;
    display: none;
    max-width: 400px;
}
.notification-success { background: #d4edda; color: #155724; }
.notification-error { background: #f8d7da; color: #721c24; }
</style>
```

## Implementation Steps

1. **Backup existing template**:
   ```bash
   cp web/templates/admin/historical_data_dashboard.html \
      web/templates/admin/historical_data_dashboard_old.html
   ```

2. **Integrate Redis features** into existing template while preserving:
   - Current styling and layout
   - CSV universe loading functionality
   - Cache management features

3. **Test the integration**:
   - Redis connection status display
   - Job submission via UI
   - Real-time progress updates
   - Job cancellation

4. **Update job history display** to show Redis job status

## Alternative Approach (Recommended)

Since the existing template (`historical_data_dashboard.html`) has complex features like CSV loading and cache management, consider:

1. **Add a toggle** between "Direct Load" (old) and "Queue Load" (Redis)
2. **Gradual migration** - Keep both systems temporarily
3. **Feature flag** - Environment variable to switch between modes

```python
# In admin_historical_data_redis.py
USE_REDIS_QUEUE = os.getenv('USE_REDIS_QUEUE', 'true').lower() == 'true'

if USE_REDIS_QUEUE:
    # Redis job submission
else:
    # Direct loader (fallback)
```

## Testing Checklist

- [ ] Redis connection indicator shows green when Redis is running
- [ ] TickStockPL status shows correctly (will show disconnected until PL implements)
- [ ] Job submission creates entry in active jobs
- [ ] Progress bar updates during job execution
- [ ] Job status transitions: submitted → running → completed/failed
- [ ] Notifications appear for job events
- [ ] CSRF token properly handled
- [ ] Mobile responsive design maintained

## Files to Update

1. `web/templates/admin/historical_data_dashboard.html` - Main template
2. `web/static/css/admin.css` - Add status indicator styles (if exists)
3. `src/api/rest/admin_historical_data_redis.py` - Ensure proper data passed to template

## Notes

- The JavaScript (`historical_data.js`) is ready and handles all polling/updates
- Redis backend is fully functional and tested
- Just needs UI integration to complete the sprint
- Consider keeping old direct-load functionality as fallback until TickStockPL is ready