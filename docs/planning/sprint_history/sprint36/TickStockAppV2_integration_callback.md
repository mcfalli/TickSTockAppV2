# TickStockAppV2 Integration Callback

**Sprint**: 36
**Date**: 2025-01-25
**Status**: Cache Synchronization Successfully Migrated to TickStockPL

## 1. New API Endpoints in TickStockPL

### 1.1 Manual Trigger Endpoint

**URL**: `POST http://tickstockpl:8080/api/processing/cache-sync/trigger`

**Headers**:
```
X-API-Key: tickstock-cache-sync-2025
Content-Type: application/json
```

**Request Body**:
```json
{
    "mode": "full",     // Options: "full", "market_cap", "themes", "ipos"
    "force": false      // Skip validation checks if true
}
```

**Response** (202 Accepted):
```json
{
    "success": true,
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "mode": "full",
    "message": "Cache synchronization (full) started"
}
```

### 1.2 Status Check Endpoint

**URL**: `GET http://tickstockpl:8080/api/processing/cache-sync/status/{job_id}`

**Headers**:
```
X-API-Key: tickstock-cache-sync-2025
```

**Response** (200 OK):
```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "mode": "full",
    "status": "completed",  // pending, running, completed, failed, error
    "created_at": "2025-01-25T16:10:00Z",
    "start_time": "2025-01-25T16:10:01Z",
    "end_time": "2025-01-25T16:35:00Z",
    "duration_seconds": 1499.5,
    "triggered_by": "api",
    "error_details": null,
    "progress": null  // Populated when status is "running"
}
```

### 1.3 History Endpoint

**URL**: `GET http://tickstockpl:8080/api/processing/cache-sync/history?limit=10&offset=0`

**Headers**:
```
X-API-Key: tickstock-cache-sync-2025
```

**Response** (200 OK):
```json
{
    "jobs": [
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "mode": "full",
            "status": "completed",
            "created_at": "2025-01-25T16:10:00Z",
            "start_time": "2025-01-25T16:10:01Z",
            "end_time": "2025-01-25T16:35:00Z",
            "duration_seconds": 1499.5,
            "triggered_by": "scheduler",
            "has_errors": false
        }
    ],
    "total": 15,
    "limit": 10,
    "offset": 0
}
```

### 1.4 Statistics Endpoint

**URL**: `GET http://tickstockpl:8080/api/processing/cache-sync/stats`

**Headers**:
```
X-API-Key: tickstock-cache-sync-2025
```

**Response** (200 OK):
```json
{
    "universes": [
        {
            "universe": "mega_cap",
            "type": "market_cap",
            "symbol_count": 50,
            "last_updated": "2025-01-25T16:35:00Z"
        },
        {
            "universe": "large_cap",
            "type": "market_cap",
            "symbol_count": 250,
            "last_updated": "2025-01-25T16:35:00Z"
        }
    ],
    "job_statistics": {
        "total_jobs_7d": 28,
        "successful_jobs_7d": 27,
        "failed_jobs_7d": 1,
        "avg_duration_seconds": 1450.3
    }
}
```

## 2. Updated Admin Page Integration

Replace the existing cache sync trigger in `src/api/rest/admin_historical_data.py` (lines 645-685):

```python
import requests
from flask import current_app

def trigger_cache_sync_tickstockpl(mode='full', force=False):
    """
    Trigger cache synchronization in TickStockPL.

    Args:
        mode: Sync mode - 'full', 'market_cap', 'themes', or 'ipos'
        force: Skip validation checks if True

    Returns:
        dict: Response from TickStockPL API
    """
    try:
        # Get configuration
        tickstockpl_host = current_app.config.get('TICKSTOCKPL_HOST', 'localhost')
        tickstockpl_port = current_app.config.get('TICKSTOCKPL_PORT', 8080)
        api_key = current_app.config.get('TICKSTOCKPL_API_KEY', 'tickstock-cache-sync-2025')

        # Make API call
        response = requests.post(
            f'http://{tickstockpl_host}:{tickstockpl_port}/api/processing/cache-sync/trigger',
            headers={'X-API-Key': api_key},
            json={'mode': mode, 'force': force},
            timeout=10
        )

        if response.status_code == 202:
            result = response.json()

            # Store job ID for status tracking
            session['cache_sync_job_id'] = result.get('job_id')

            return {
                'success': True,
                'message': f'Cache sync triggered successfully',
                'job_id': result.get('job_id')
            }
        else:
            return {
                'success': False,
                'message': f'Failed to trigger cache sync: {response.status_code}'
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call TickStockPL API: {e}")
        return {
            'success': False,
            'message': f'API call failed: {str(e)}'
        }

def get_cache_sync_status(job_id):
    """
    Get cache sync job status from TickStockPL.

    Args:
        job_id: The job ID to check

    Returns:
        dict: Job status information
    """
    try:
        tickstockpl_host = current_app.config.get('TICKSTOCKPL_HOST', 'localhost')
        tickstockpl_port = current_app.config.get('TICKSTOCKPL_PORT', 8080)
        api_key = current_app.config.get('TICKSTOCKPL_API_KEY', 'tickstock-cache-sync-2025')

        response = requests.get(
            f'http://{tickstockpl_host}:{tickstockpl_port}/api/processing/cache-sync/status/{job_id}',
            headers={'X-API-Key': api_key},
            timeout=5
        )

        if response.status_code == 200:
            return response.json()
        else:
            return None

    except requests.exceptions.RequestException:
        return None

# Update the admin route (replace lines 645-685)
@admin_bp.route('/admin/trigger-cache-sync', methods=['POST'])
@require_admin
def trigger_cache_sync():
    """Trigger cache synchronization via TickStockPL API."""
    mode = request.json.get('mode', 'full')
    force = request.json.get('force', False)

    result = trigger_cache_sync_tickstockpl(mode, force)

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500
```

## 3. Redis Events to Subscribe

### 3.1 Event Channels

Subscribe to these Redis channels in TickStockAppV2:

```python
CACHE_SYNC_CHANNELS = {
    'sync_triggered': 'tickstock:cache:sync_triggered',
    'sync_complete': 'tickstock:cache:sync_complete',
    'universe_updated': 'tickstock:universe:updated',
    'ipo_assignment': 'tickstock:cache:ipo_assignment',
    'delisting_cleanup': 'tickstock:cache:delisting_cleanup'
}
```

### 3.2 Event Formats

#### Sync Triggered Event
```json
{
    "event": "cache_sync_triggered",
    "timestamp": "2025-01-25T16:10:00Z",
    "source": "cache_sync_api",
    "version": "1.0",
    "payload": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "mode": "full",
        "force": false,
        "triggered_by": "api"
    }
}
```

#### Sync Complete Event
```json
{
    "event": "cache_sync_completed",
    "timestamp": "2025-01-25T16:35:00Z",
    "source": "daily_cache_sync_job",
    "version": "1.0",
    "payload": {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "completed",
        "mode": "full",
        "total_changes": 1250,
        "universes_updated": ["mega_cap", "large_cap", "mid_cap"],
        "duration_seconds": 1499.5
    }
}
```

### 3.3 Redis Subscriber Implementation

Add to TickStockAppV2's Redis subscriber:

```python
import redis
import json
import threading

class CacheSyncEventListener:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()
        self.running = False

    def start(self):
        """Start listening for cache sync events."""
        self.running = True

        # Subscribe to channels
        self.pubsub.subscribe(
            'tickstock:cache:sync_triggered',
            'tickstock:cache:sync_complete',
            'tickstock:universe:updated'
        )

        # Start listener thread
        thread = threading.Thread(target=self._listen)
        thread.daemon = True
        thread.start()

    def _listen(self):
        """Listen for Redis events."""
        for message in self.pubsub.listen():
            if not self.running:
                break

            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    self._handle_event(data)
                except json.JSONDecodeError:
                    pass

    def _handle_event(self, event):
        """Handle cache sync events."""
        event_type = event.get('event')

        if event_type == 'cache_sync_triggered':
            # Update UI to show sync in progress
            self._update_ui_sync_started(event['payload'])

        elif event_type == 'cache_sync_completed':
            # Update UI to show sync complete
            self._update_ui_sync_completed(event['payload'])

            # Refresh cache in application
            if event['payload']['status'] == 'completed':
                self._refresh_local_cache()

        elif event_type == 'universe_updated':
            # Update specific universe in local cache
            self._update_universe_cache(event['payload']['universe'])

    def _update_ui_sync_started(self, payload):
        """Update UI when sync starts."""
        # Emit websocket event to admin dashboard
        socketio.emit('cache_sync_started', {
            'job_id': payload['job_id'],
            'mode': payload['mode']
        }, namespace='/admin')

    def _update_ui_sync_completed(self, payload):
        """Update UI when sync completes."""
        # Emit websocket event to admin dashboard
        socketio.emit('cache_sync_completed', {
            'job_id': payload['job_id'],
            'status': payload['status'],
            'duration': payload.get('duration_seconds')
        }, namespace='/admin')

    def _refresh_local_cache(self):
        """Refresh local cache from database."""
        # Trigger cache refresh in your application
        from src.data.cache_manager import cache_manager
        cache_manager.refresh_all_universes()
```

## 4. Configuration Updates

Add to TickStockAppV2's configuration:

```python
# config/production.py or .env
TICKSTOCKPL_HOST = 'tickstockpl'  # or 'localhost' for development
TICKSTOCKPL_PORT = 8080
TICKSTOCKPL_API_KEY = 'tickstock-cache-sync-2025'  # Store securely in production
```

## 5. Admin Dashboard Updates

Update `web/templates/admin/historical_data_dashboard.html`:

```javascript
// Replace existing cache sync button handler
$('#sync-cache-btn').click(function() {
    const btn = $(this);
    btn.prop('disabled', true).text('Syncing...');

    $.ajax({
        url: '/admin/trigger-cache-sync',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            mode: $('#sync-mode').val() || 'full',
            force: $('#force-sync').is(':checked')
        }),
        success: function(response) {
            if (response.job_id) {
                // Store job ID for status tracking
                window.cacheSyncJobId = response.job_id;

                // Start polling for status
                pollCacheSyncStatus(response.job_id);

                showNotification('success', 'Cache sync started');
            }
        },
        error: function(xhr) {
            showNotification('error', 'Failed to start cache sync');
            btn.prop('disabled', false).text('Sync Cache');
        }
    });
});

function pollCacheSyncStatus(jobId) {
    const interval = setInterval(function() {
        $.ajax({
            url: '/admin/cache-sync-status/' + jobId,
            method: 'GET',
            success: function(data) {
                updateSyncProgress(data);

                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(interval);
                    $('#sync-cache-btn').prop('disabled', false).text('Sync Cache');

                    if (data.status === 'completed') {
                        showNotification('success', 'Cache sync completed');
                        // Refresh universe dropdowns
                        refreshUniverseSelectors();
                    } else {
                        showNotification('error', 'Cache sync failed');
                    }
                }
            }
        });
    }, 2000);  // Poll every 2 seconds
}
```

## 6. Files to Delete from TickStockAppV2

After successful testing, DELETE these files:

1. `src/data/cache_entries_synchronizer.py` (881 lines)
2. `scripts/cache_management/run_cache_synchronization.py`
3. `tests/test_cache_entries_synchronizer.py` (if exists)

## 7. Files to Update in TickStockAppV2

1. **`src/api/rest/admin_historical_data.py`**
   - Remove lines 645-685 (old cache sync implementation)
   - Add new API integration code above

2. **`web/templates/admin/historical_data_dashboard.html`**
   - Update JavaScript to use new API endpoints
   - Add job status polling

3. **`requirements.txt`**
   - Can remove any cache-sync specific dependencies if not used elsewhere

## 8. Database Migration

The cache sync now runs in TickStockPL but still uses the same `cache_entries` table. No database migration needed for TickStockAppV2.

## 9. Testing Checklist

Before removing old code:

- [ ] Test manual trigger from admin dashboard
- [ ] Verify Redis events are received
- [ ] Check cache_entries table is updated correctly
- [ ] Confirm universe dropdowns refresh after sync
- [ ] Test all sync modes (full, market_cap, themes, ipos)
- [ ] Verify job status tracking works
- [ ] Check error handling for API failures
- [ ] Test with TickStockPL service down (graceful degradation)

## 10. Performance Metrics

Expected performance from TickStockPL:
- Full sync: 15-30 minutes (same as before)
- Market cap only: 5-10 minutes
- Themes rebalancing: 10-15 minutes
- IPO assignment: 2-5 minutes

## 11. Rollback Plan

If issues arise:
1. Keep backup of `cache_entries_synchronizer.py`
2. Can temporarily restore old code
3. Switch admin dashboard back to local function
4. TickStockPL cache sync can run independently without breaking TickStockAppV2

## 12. Support Contact

For issues or questions:
- Check logs in TickStockPL: `/var/log/tickstockpl/cache_sync.log`
- Monitor Redis channel: `tickstock:errors` for error events
- API health check: `GET http://tickstockpl:8080/health`

## Migration Complete

Once you've successfully tested the integration:
1. Confirm all tests pass
2. Remove old code from TickStockAppV2
3. Update deployment documentation
4. Monitor first few automatic daily runs at 4:10 PM ET