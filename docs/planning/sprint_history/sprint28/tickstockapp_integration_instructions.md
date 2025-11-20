# TickStockAppV2 Integration Update Instructions

**Document Type**: Developer Instructions
**For**: TickStockAppV2 Developer
**Priority**: HIGH - Required for Sprint 28 Completion
**Created**: 2025-01-22

## Overview

The historical data loading functionality has been migrated from TickStockAppV2 to TickStockPL. TickStockAppV2 must now submit data loading jobs via Redis instead of directly calling the MassiveHistoricalLoader.

## What Has Changed

### ❌ OLD Approach (Direct Calls)
TickStockAppV2 was directly importing and calling MassiveHistoricalLoader:
```python
from src.data.historical_loader import MassiveHistoricalLoader
loader = MassiveHistoricalLoader()
result = loader.load_historical_data(symbols, years, timespan)
```

### ✅ NEW Approach (Redis Jobs)
TickStockAppV2 must now submit jobs to Redis for TickStockPL to process:
```python
import redis
import json
import uuid

redis_client = redis.Redis(host='localhost', port=6379, db=0)
job_id = str(uuid.uuid4())
job_data = {
    'job_id': job_id,
    'job_type': 'historical_load',
    'symbols': symbols,
    'years': years,
    'timespan': timespan,
    'requested_by': 'admin_ui',
    'timestamp': datetime.now().isoformat()
}
redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))
```

## Files to Update in TickStockAppV2

### 1. src/api/rest/admin_historical_data.py

**Current Implementation** (lines to replace):
```python
# Look for imports like:
from src.data.historical_loader import MassiveHistoricalLoader

# Look for direct calls like:
loader = MassiveHistoricalLoader()
result = loader.load_historical_data(...)
```

**New Implementation**:
```python
import redis
import json
import uuid
from datetime import datetime
from flask import jsonify, request

# Initialize Redis client (add to module level or constructor)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

@app.route('/api/admin/historical-data/load', methods=['POST'])
def load_historical_data():
    """Submit historical data load job to TickStockPL via Redis"""

    data = request.json
    symbols = data.get('symbols', [])
    years = data.get('years', 1)
    timespan = data.get('timespan', 'day')

    # Create job
    job_id = str(uuid.uuid4())
    job_data = {
        'job_id': job_id,
        'job_type': 'historical_load',
        'symbols': symbols,
        'years': years,
        'timespan': timespan,
        'requested_by': 'admin_ui',
        'timestamp': datetime.now().isoformat()
    }

    # Submit job to TickStockPL
    redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))

    # Store initial status for tracking
    redis_client.setex(
        f'job:status:{job_id}',
        3600,  # 1 hour TTL
        json.dumps({'status': 'submitted', 'progress': 0, 'message': 'Job submitted'})
    )

    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': f'Job submitted for {len(symbols)} symbols'
    })

@app.route('/api/admin/job-status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of a data loading job"""

    status_data = redis_client.get(f'job:status:{job_id}')

    if status_data:
        status = json.loads(status_data)
        return jsonify({
            'success': True,
            'job_id': job_id,
            **status
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Job not found'
        }), 404
```

### 2. static/js/admin/historical_data.js (or equivalent)

**Update JavaScript to poll job status**:

```javascript
// Function to submit data load job
async function submitDataLoad(symbols, years, timespan) {
    const response = await fetch('/api/admin/historical-data/load', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            symbols: symbols,
            years: years,
            timespan: timespan
        })
    });

    const result = await response.json();
    if (result.success) {
        // Start polling for job status
        pollJobStatus(result.job_id);
    }
}

// Function to poll job status
async function pollJobStatus(jobId) {
    const statusDiv = document.getElementById('job-status');
    const progressBar = document.getElementById('progress-bar');

    const interval = setInterval(async () => {
        const response = await fetch(`/api/admin/job-status/${jobId}`);
        const status = await response.json();

        if (status.success) {
            // Update UI with status
            statusDiv.textContent = `${status.status}: ${status.message || ''}`;
            if (progressBar) {
                progressBar.style.width = `${status.progress || 0}%`;
                progressBar.textContent = `${status.progress || 0}%`;
            }

            // Stop polling if job is complete
            if (status.status === 'completed' || status.status === 'failed') {
                clearInterval(interval);

                if (status.status === 'completed') {
                    showSuccessMessage('Data loaded successfully!');
                } else {
                    showErrorMessage(`Job failed: ${status.message}`);
                }
            }
        } else {
            // Job not found
            clearInterval(interval);
            showErrorMessage('Job status not available');
        }
    }, 1000); // Poll every second

    // Stop polling after 5 minutes
    setTimeout(() => clearInterval(interval), 300000);
}
```

### 3. Templates (if applicable)

Add progress display elements to your HTML templates:

```html
<!-- In templates/admin/historical_data.html -->
<div id="job-status-container" style="display: none;">
    <h4>Job Status</h4>
    <div id="job-status">Waiting...</div>
    <div class="progress">
        <div id="progress-bar" class="progress-bar" role="progressbar"
             style="width: 0%;" aria-valuenow="0" aria-valuemin="0"
             aria-valuemax="100">0%</div>
    </div>
</div>
```

## Additional Job Types to Support

### Multi-Timeframe Load
```python
job_data = {
    'job_id': job_id,
    'job_type': 'multi_timeframe_load',
    'symbols': ['AAPL', 'MSFT'],
    'timeframes': ['hour', 'day', 'week', 'month'],
    'years': 2,
    'requested_by': 'admin_ui',
    'timestamp': datetime.now().isoformat()
}
```

### Universe Seeding
```python
job_data = {
    'job_id': job_id,
    'job_type': 'universe_seed',
    'universe_type': 'SP500',  # or 'ETF', 'ALL'
    'requested_by': 'admin_ui',
    'timestamp': datetime.now().isoformat()
}
```

## Files to Remove/Clean Up

After verification that the Redis approach works:

1. **DELETE** from TickStockAppV2:
   - `src/data/historical_loader.py` (now in TickStockPL)
   - `src/data/bulk_universe_seeder.py` (now in TickStockPL)

2. **KEEP BUT UPDATE**:
   - Test scripts that reference the old location
   - Admin endpoints that used direct calls

## Testing Your Changes

### 1. Start TickStockPL Job Handler
In the TickStockPL directory, run:
```bash
python -m src.jobs.data_load_handler
```

### 2. Test Job Submission
Use the test script in TickStockPL to verify Redis communication:
```bash
# In TickStockPL directory
python scripts/testing/test_redis_data_load.py
```

### 3. Test from Admin UI
1. Navigate to the admin historical data page
2. Submit a small test load (e.g., 1 symbol, 1 month)
3. Verify the progress bar updates
4. Check that data appears in the database

## Dependencies to Add

Make sure TickStockAppV2 has Redis client installed:
```bash
pip install redis
```

## Environment Variables

Ensure these are set in TickStockAppV2's `.env` file:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## Error Handling

Add proper error handling for Redis connection failures:

```python
try:
    redis_client.ping()
except redis.ConnectionError:
    return jsonify({
        'success': False,
        'message': 'Redis service unavailable. Please contact administrator.'
    }), 503
```

## Timeline

1. **Day 1**: Update admin endpoints to use Redis
2. **Day 1**: Update JavaScript for job status polling
3. **Day 2**: Test end-to-end workflow
4. **Day 2**: Clean up old files after verification

## Questions or Issues?

If you encounter any issues:

1. Check that Redis is running: `redis-cli ping`
2. Verify TickStockPL job handler is running
3. Check Redis for job data: `redis-cli get "job:status:{job_id}"`
4. Review TickStockPL logs for processing errors

## Success Criteria

- [ ] Admin UI can submit data load jobs
- [ ] Progress bar updates during loading
- [ ] Jobs complete successfully
- [ ] Data appears in database
- [ ] No direct imports of MassiveHistoricalLoader remain
- [ ] All tests pass

---

**Note**: This migration maintains the same functionality while improving architecture by separating concerns between TickStockAppV2 (UI/Consumer) and TickStockPL (Data Processing/Producer).