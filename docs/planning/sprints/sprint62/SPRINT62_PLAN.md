# Sprint 62 - Historical Data Loading Migration to RelationshipCache

**Created**: December 22, 2025
**Status**: Planning
**Priority**: High
**Dependencies**: Sprint 61 (RelationshipCache universe loading)

---

## Sprint Goal

Migrate historical data admin interface from hardcoded universe lists (CacheControl) to dynamic universe loading via RelationshipCache (definition_groups/group_memberships), enabling selection of 1-N universe groups for multi-timeframe data loading.

---

## Business Value

- **Dynamic Universe Selection**: No code changes needed to add new universes
- **Multi-Universe Loading**: Load SPY:nasdaq100 (518 stocks) with single click
- **Single Source of Truth**: definition_groups/group_memberships for all universe metadata
- **Improved UX**: Rich universe metadata (descriptions, member counts) in dropdowns
- **Consistency**: Same universe system across WebSocket (Sprint 61) and Historical Data loading

---

## Current State Analysis

### Current Implementation (`src/api/rest/admin_historical_data_redis.py`)

**Hardcoded Universes** (lines 77-82):
```python
available_universes = {
    'SP500': 'S&P 500 Components',
    'NASDAQ100': 'NASDAQ 100 Components',
    'ETF': 'Major ETFs',
    'CUSTOM': 'Custom Symbol List'
}
```

**Problems**:
- ❌ Hardcoded - requires code changes to add universes
- ❌ Not synced with definition_groups database
- ❌ No multi-universe join support
- ❌ No member count or metadata
- ❌ Different from WebSocket universe system (Sprint 61)

### Current Data Flow

```
User selects universe in UI
    ↓
POST /admin/historical-data/trigger-load
    ↓
Hardcoded universe lookup
    ↓
Submit job to Redis (tickstock.jobs.data_load)
    ↓
TickStockPL processes job
    ↓
Loads: ohlcv_1min, ohlcv_hourly, ohlcv_daily, ohlcv_weekly, ohlcv_monthly
```

### Available Universes (from Sprint 61)

**Database State**:
- **UNIVERSE types**: nasdaq100 (102), dow30 (30)
- **ETF holdings**: 24 ETFs (SPY=504, VOO=505, QQQ=102, etc.)
- **Total**: 3,757 unique stock symbols, 15,834 relationships

---

## Sprint 62 Design

### Target Data Flow

```
Page Load:
    GET /admin/historical-data/universes
        ↓
    RelationshipCache.get_available_universes()
        ↓
    Query definition_groups (UNIVERSE + ETF types)
        ↓
    Return [{name, type, description, member_count}, ...]
        ↓
    JavaScript populates dropdown with metadata

User selects universe(s):
    UI: "SPY:nasdaq100" (Multi-select or text input)
    ↓
POST /admin/historical-data/trigger-universe-load
    {
        "universe_key": "SPY:nasdaq100",
        "timeframes": ["1min", "hour", "day", "week", "month"],
        "years": 2
    }
    ↓
RelationshipCache.get_universe_symbols("SPY:nasdaq100")
    ↓
Returns 518 distinct symbols
    ↓
Submit job to Redis with resolved symbol list
    ↓
TickStockPL loads all timeframes
```

---

## Implementation Plan

### Phase 1: Extend RelationshipCache with Universe Metadata ✅

**Goal**: Add method to retrieve available universes with metadata

**File**: `src/core/services/relationship_cache.py`

**Add Method**:
```python
def get_available_universes(self, types: List[str] = None) -> List[Dict[str, Any]]:
    """
    Get list of available universes with metadata.

    Args:
        types: Optional filter by type (e.g., ['UNIVERSE', 'ETF'])
               Default: ['UNIVERSE', 'ETF']

    Returns:
        List of universe metadata:
        [
            {
                'name': 'nasdaq100',
                'type': 'UNIVERSE',
                'description': 'NASDAQ-100 Index Components',
                'member_count': 102,
                'environment': 'DEFAULT'
            },
            ...
        ]
    """
    if types is None:
        types = ['UNIVERSE', 'ETF']

    # Check cache first
    cache_key = f"available_universes:{':'.join(sorted(types))}"
    with self._lock:
        if cache_key in self._universe_metadata_cache:
            metadata, timestamp = self._universe_metadata_cache[cache_key]
            if not self._is_expired(timestamp):
                self._stats['hits'] += 1
                return metadata.copy()
        self._stats['misses'] += 1

    # Query database
    try:
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                dg.name,
                dg.type,
                dg.description,
                COUNT(gm.symbol) as member_count,
                dg.environment,
                dg.created_at,
                dg.updated_at
            FROM definition_groups dg
            LEFT JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = ANY(%s)
              AND dg.environment = %s
            GROUP BY dg.id, dg.name, dg.type, dg.description, dg.environment
            ORDER BY dg.type, dg.name
        """

        cursor.execute(query, (types, self.environment))

        universes = []
        for row in cursor.fetchall():
            universes.append({
                'name': row[0],
                'type': row[1],
                'description': row[2] or f"{row[1]}: {row[0]}",
                'member_count': row[3],
                'environment': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None
            })

        conn.close()

        # Cache result
        with self._lock:
            self._universe_metadata_cache[cache_key] = (universes, datetime.now())
            self._stats['loads'] += 1

        return universes

    except Exception as e:
        logger.error(f"Error loading available universes: {e}")
        return []
```

**Add Cache Storage**:
```python
self._universe_metadata_cache: Dict[str, tuple[List[Dict], datetime]] = {}
```

**Update `invalidate()` method**:
```python
if cache_type is None or cache_type == 'all':
    self._universe_metadata_cache.clear()
```

---

### Phase 2: Add Admin API Endpoint for Universes

**Goal**: Create REST endpoint to fetch available universes

**File**: `src/api/rest/admin_historical_data_redis.py`

**Add Endpoint**:
```python
@app.route('/admin/historical-data/universes', methods=['GET'])
@login_required
@admin_required
def admin_get_universes():
    """Get available universes from RelationshipCache"""
    try:
        from src.core.services.relationship_cache import get_relationship_cache

        cache = get_relationship_cache()

        # Get universe types filter from query params
        types_param = request.args.get('types', 'UNIVERSE,ETF')
        types = [t.strip() for t in types_param.split(',') if t.strip()]

        # Get universes with metadata
        universes = cache.get_available_universes(types=types)

        # Format for frontend
        response = {
            'universes': universes,
            'total_count': len(universes),
            'types': types
        }

        return jsonify(response), 200

    except Exception as e:
        app.logger.error(f"Error fetching universes: {str(e)}")
        return jsonify({'error': str(e)}), 500
```

**Add Universe Load Endpoint**:
```python
@app.route('/admin/historical-data/trigger-universe-load', methods=['POST'])
@login_required
@admin_required
def admin_trigger_universe_load():
    """
    Submit historical data load job for universe(s).

    Request Body:
    {
        "universe_key": "SPY:nasdaq100",  // Single or multi-universe join
        "timeframes": ["1min", "hour", "day", "week", "month"],
        "years": 2
    }
    """
    try:
        from src.core.services.relationship_cache import get_relationship_cache

        # Get request data
        data = request.get_json()
        universe_key = data.get('universe_key', '').strip()
        timeframes = data.get('timeframes', ['day'])
        years = int(data.get('years', 1))

        if not universe_key:
            return jsonify({'error': 'universe_key required'}), 400

        # Resolve universe to symbols via RelationshipCache
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols(universe_key)

        if not symbols:
            return jsonify({'error': f'No symbols found for universe: {universe_key}'}), 404

        # Create job
        job_id = str(uuid.uuid4())
        job_data = {
            'job_id': job_id,
            'job_type': 'universe_historical_load',
            'universe_key': universe_key,
            'symbols': symbols,
            'timeframes': timeframes,
            'years': years,
            'requested_by': current_user.username if current_user.is_authenticated else 'admin',
            'timestamp': datetime.now().isoformat()
        }

        # Submit to Redis
        redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))

        # Store job status
        initial_status = {
            'status': 'submitted',
            'progress': '0',
            'message': f'Loading {len(symbols)} symbols from {universe_key}',
            'submitted_at': datetime.now().isoformat()
        }

        job_key = f'tickstock.jobs.status:{job_id}'
        redis_client.hset(job_key, mapping=initial_status)
        redis_client.expire(job_key, 86400)

        # Add to job history
        job_history.append({
            'job_id': job_id,
            'type': 'universe_historical_load',
            'universe_key': universe_key,
            'symbol_count': len(symbols),
            'timeframes': timeframes,
            'submitted_at': datetime.now(),
            'submitted_by': current_user.username if current_user.is_authenticated else 'admin'
        })

        return jsonify({
            'job_id': job_id,
            'symbol_count': len(symbols),
            'universe_key': universe_key,
            'message': f'Job submitted: Loading {len(symbols)} symbols'
        }), 200

    except Exception as e:
        app.logger.error(f"Error triggering universe load: {str(e)}")
        return jsonify({'error': str(e)}), 500
```

---

### Phase 3: Update Admin Dashboard HTML

**Goal**: Add universe selection UI with multi-select support

**File**: `web/templates/admin/historical_data_dashboard.html`

**Find Section**: Universe selection section (around line 280-350)

**Replace With**:
```html
<!-- Universe-based Load -->
<div id="universe-section" style="display: none;">
    <h4>Universe Selection</h4>
    <p>Select a universe from the dropdown, or use the advanced field to combine multiple universes.</p>

    <div class="form-row">
        <div class="form-group">
            <label for="universe-select">Select Universe</label>
            <select id="universe-select" class="form-control">
                <option value="" disabled selected>Loading universes...</option>
            </select>
            <small class="form-text">Select one universe to load</small>
        </div>

        <div class="form-group">
            <label for="universe-key-input">Advanced: Multi-Universe Join</label>
            <input type="text"
                   id="universe-key-input"
                   class="form-control"
                   placeholder="e.g., SPY:nasdaq100:dow30">
            <small class="form-text">
                <strong>Optional:</strong> Use colon (:) to combine multiple universes.
                <br>Example: SPY:nasdaq100 loads 518 distinct stocks (overrides dropdown).
            </small>
        </div>
    </div>

    <div class="form-row">
        <div class="form-group">
            <label for="universe-timeframes">Timeframes</label>
            <div id="universe-timeframes">
                <label><input type="checkbox" name="timeframe" value="1min" checked> 1-Minute</label>
                <label><input type="checkbox" name="timeframe" value="hour" checked> Hourly</label>
                <label><input type="checkbox" name="timeframe" value="day" checked> Daily</label>
                <label><input type="checkbox" name="timeframe" value="week" checked> Weekly</label>
                <label><input type="checkbox" name="timeframe" value="month" checked> Monthly</label>
            </div>
            <small class="form-text">Select all timeframes to load (default: all)</small>
        </div>

        <div class="form-group">
            <label for="universe-years">Years of Data</label>
            <select id="universe-years" class="form-control">
                <option value="1">1 Year</option>
                <option value="2" selected>2 Years</option>
                <option value="3">3 Years</option>
                <option value="5">5 Years</option>
                <option value="10">10 Years</option>
            </select>
        </div>
    </div>

    <div class="form-group">
        <label>Selected Universe Preview</label>
        <div id="universe-preview" style="padding: 10px; background: #f8f9fa; border-radius: 4px; min-height: 60px;">
            <em>Select universes to see preview</em>
        </div>
    </div>

    <button type="button" class="btn btn-primary" id="trigger-universe-load">
        Load Historical Data for Universe(s)
    </button>
</div>
```

---

### Phase 4: Update JavaScript for Dynamic Universe Loading

**Goal**: Fetch universes from API and handle selection

**File**: `web/static/js/admin/historical_data.js`

**Add Method** (in HistoricalDataManager class):
```javascript
async initializeUniverseHandlers() {
    // Fetch available universes on page load
    await this.loadAvailableUniverses();

    // Universe select change handler
    const universeSelect = document.getElementById('universe-select');
    if (universeSelect) {
        universeSelect.addEventListener('change', () => this.handleUniverseSelectionChange());
    }

    // Manual universe key input handler
    const universeKeyInput = document.getElementById('universe-key-input');
    if (universeKeyInput) {
        universeKeyInput.addEventListener('input', () => this.handleUniverseKeyInput());
    }

    // Universe load button
    const triggerUniverseLoadBtn = document.getElementById('trigger-universe-load');
    if (triggerUniverseLoadBtn) {
        triggerUniverseLoadBtn.addEventListener('click', () => this.submitUniverseLoad());
    }
}

async loadAvailableUniverses() {
    try {
        const response = await fetch('/admin/historical-data/universes?types=UNIVERSE,ETF');
        const data = await response.json();

        if (response.ok) {
            this.availableUniverses = data.universes;
            this.populateUniverseDropdown(data.universes);
        } else {
            console.error('Error loading universes:', data.error);
            this.showError('Failed to load universes');
        }
    } catch (error) {
        console.error('Error fetching universes:', error);
        this.showError('Failed to fetch universe list');
    }
}

populateUniverseDropdown(universes) {
    const select = document.getElementById('universe-select');
    if (!select) return;

    // Clear existing options
    select.innerHTML = '';

    // Group by type
    const grouped = universes.reduce((acc, u) => {
        if (!acc[u.type]) acc[u.type] = [];
        acc[u.type].push(u);
        return acc;
    }, {});

    // Add optgroups
    Object.keys(grouped).sort().forEach(type => {
        const optgroup = document.createElement('optgroup');
        optgroup.label = `${type} (${grouped[type].length})`;

        grouped[type].forEach(universe => {
            const option = document.createElement('option');
            option.value = universe.name;
            option.textContent = `${universe.name} (${universe.member_count} stocks)`;
            option.dataset.type = universe.type;
            option.dataset.count = universe.member_count;
            option.dataset.description = universe.description;
            optgroup.appendChild(option);
        });

        select.appendChild(optgroup);
    });
}

handleUniverseSelectionChange() {
    const select = document.getElementById('universe-select');
    const universeKeyInput = document.getElementById('universe-key-input');
    const preview = document.getElementById('universe-preview');

    if (!select || !universeKeyInput || !preview) return;

    // Get selected option (single select)
    const selectedOption = select.selectedOptions[0];

    if (!selectedOption || !selectedOption.value) {
        preview.innerHTML = '<em>Select a universe to see preview</em>';
        return;
    }

    // Set universe key from dropdown selection
    const universeKey = selectedOption.value;
    const symbolCount = parseInt(selectedOption.dataset.count || 0);
    const type = selectedOption.dataset.type;
    const description = selectedOption.dataset.description;

    // Only update text input if it's empty (don't override manual input)
    if (!universeKeyInput.value.trim()) {
        universeKeyInput.value = universeKey;
    }

    // Build preview
    const previewHTML = `
        <strong>Selected Universe:</strong> ${universeKey}<br>
        <strong>Type:</strong> ${type}<br>
        <strong>Symbol Count:</strong> ${symbolCount} stocks<br>
        <strong>Description:</strong> ${description}
    `;

    preview.innerHTML = previewHTML;
}

handleUniverseKeyInput() {
    const universeKeyInput = document.getElementById('universe-key-input');
    const select = document.getElementById('universe-select');

    if (!universeKeyInput || !select) return;

    // If user manually edits the key, clear multi-select
    const manualKey = universeKeyInput.value.trim();
    if (manualKey) {
        // Deselect all options
        Array.from(select.options).forEach(opt => opt.selected = false);

        // Update preview
        const preview = document.getElementById('universe-preview');
        if (preview) {
            preview.innerHTML = `
                <strong>Manual Universe Key:</strong> ${manualKey}<br>
                <em>Symbol count will be calculated when job is submitted</em>
            `;
        }
    }
}

async submitUniverseLoad() {
    const universeKeyInput = document.getElementById('universe-key-input');
    const yearsSelect = document.getElementById('universe-years');
    const timeframeCheckboxes = document.querySelectorAll('#universe-timeframes input[name="timeframe"]:checked');

    // Validate
    const universeKey = universeKeyInput?.value?.trim();
    if (!universeKey) {
        this.showError('Please select a universe or enter a universe key');
        return;
    }

    const years = parseInt(yearsSelect?.value || 2);
    const timeframes = Array.from(timeframeCheckboxes).map(cb => cb.value);

    if (timeframes.length === 0) {
        this.showError('Please select at least one timeframe');
        return;
    }

    // Prepare request
    const requestData = {
        universe_key: universeKey,
        timeframes: timeframes,
        years: years
    };

    try {
        this.showStatus('Submitting universe load job...', 'info');

        const response = await fetch('/admin/historical-data/trigger-universe-load', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();

        if (response.ok) {
            this.showStatus(
                `Job submitted successfully! Loading ${result.symbol_count} symbols from ${result.universe_key}. Job ID: ${result.job_id.substring(0, 8)}...`,
                'success'
            );

            // Start polling for this job
            this.startJobPolling(result.job_id);

            // Refresh job list
            setTimeout(() => window.location.reload(), 2000);
        } else {
            this.showError(result.error || 'Failed to submit job');
        }
    } catch (error) {
        console.error('Error submitting universe load:', error);
        this.showError('Failed to submit universe load job');
    }
}
```

---

### Phase 5: Testing & Validation

**Goal**: Comprehensive testing of universe loading

**Test Cases**:

1. **Single Universe Load**
   - Select nasdaq100 (102 stocks)
   - Select all timeframes (1min, hour, day, week, month)
   - Verify job submission
   - Verify all 5 OHLCV tables populated

2. **Multi-Universe Load**
   - Select SPY:nasdaq100 (518 stocks)
   - Select daily + weekly timeframes only
   - Verify distinct union calculated correctly
   - Verify only selected timeframes loaded

3. **ETF Universe Load**
   - Select QQQ ETF (102 holdings)
   - Select all timeframes
   - Verify ETF holdings resolved

4. **Three-Universe Join**
   - Manual input: SPY:QQQ:dow30
   - Select daily timeframe only
   - Verify ~522 distinct symbols loaded

5. **Edge Cases**
   - Empty universe selection → error message
   - Invalid universe key → error message
   - No timeframes selected → error message
   - Job status polling works correctly
   - Progress updates display

**Test Script**:
```python
# tests/integration/test_sprint62_historical_load.py
import pytest
from src.core.services.relationship_cache import get_relationship_cache

class TestHistoricalLoadUniverses:
    def test_get_available_universes(self):
        cache = get_relationship_cache()
        universes = cache.get_available_universes()

        assert len(universes) > 0
        assert all('name' in u for u in universes)
        assert all('member_count' in u for u in universes)

    def test_universe_load_endpoint(self, client, admin_user):
        # Login as admin
        client.post('/login', data={'username': 'admin', 'password': 'test'})

        # Test GET /admin/historical-data/universes
        response = client.get('/admin/historical-data/universes')
        assert response.status_code == 200

        data = response.get_json()
        assert 'universes' in data
        assert len(data['universes']) > 0

    def test_trigger_universe_load(self, client, admin_user):
        client.post('/login', data={'username': 'admin', 'password': 'test'})

        # Submit universe load
        response = client.post('/admin/historical-data/trigger-universe-load', json={
            'universe_key': 'nasdaq100',
            'timeframes': ['day', 'week'],
            'years': 1
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'job_id' in data
        assert data['symbol_count'] == 102
```

---

## Success Criteria

- [ ] RelationshipCache has `get_available_universes()` method
- [ ] API endpoint `/admin/historical-data/universes` returns universe metadata
- [ ] API endpoint `/admin/historical-data/trigger-universe-load` accepts multi-universe joins
- [ ] Admin UI shows dynamic universe dropdown populated from database
- [ ] Multi-universe join UI working (SPY:nasdaq100 syntax)
- [ ] Universe preview shows symbol counts and metadata
- [ ] All 5 timeframes load correctly: 1min, hourly, daily, weekly, monthly
- [ ] Job submission to TickStockPL via Redis works
- [ ] Job status polling displays progress
- [ ] Integration tests pass (3+ test cases)
- [ ] Zero regression: Existing historical load functionality preserved

---

## Files to Modify

### Core Services (2 files)
1. `src/core/services/relationship_cache.py` (+100 lines)
   - Add `get_available_universes()` method
   - Add `_universe_metadata_cache` storage
   - Update `invalidate()` method

### API Routes (1 file)
2. `src/api/rest/admin_historical_data_redis.py` (+150 lines)
   - Add `admin_get_universes()` endpoint
   - Add `admin_trigger_universe_load()` endpoint
   - Remove hardcoded universe list (lines 77-82)

### Frontend Templates (1 file)
3. `web/templates/admin/historical_data_dashboard.html` (update universe section)
   - Replace universe selection HTML
   - Add multi-select dropdown
   - Add universe key input
   - Add timeframe checkboxes
   - Add preview section

### Frontend JavaScript (1 file)
4. `web/static/js/admin/historical_data.js` (+200 lines)
   - Add `initializeUniverseHandlers()` method
   - Add `loadAvailableUniverses()` method
   - Add `populateUniverseDropdown()` method
   - Add `handleUniverseSelectionChange()` method
   - Add `handleUniverseKeyInput()` method
   - Add `submitUniverseLoad()` method

### Testing (1 file)
5. `tests/integration/test_sprint62_historical_load.py` (NEW, ~200 lines)
   - Test `get_available_universes()`
   - Test API endpoints
   - Test universe load workflow
   - Test multi-universe joins

### Documentation (2 files)
6. `docs/planning/sprints/sprint62/SPRINT62_PLAN.md` (this file)
7. `docs/planning/sprints/sprint62/SPRINT62_COMPLETE.md` (after completion)

---

## Configuration

No `.env` changes required - uses existing RelationshipCache configuration.

---

## Performance Targets

| Operation | Target | Critical Path |
|-----------|--------|---------------|
| Get Available Universes | <50ms | No |
| Resolve Universe Symbols | <1ms (cached) | No |
| API /universes endpoint | <100ms | No |
| Job Submission | <200ms | No |
| UI Universe Dropdown Load | <500ms | No |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| TickStockPL job handler not compatible | Test job format in Phase 5 |
| Large universe loads timeout | Implement progress tracking via Redis |
| Multi-universe join UI confusing | Add clear examples and preview |
| Breaking existing load workflow | Keep backward compatibility, thorough testing |

---

## Dependencies

### Sprint 61 (COMPLETE ✅)
- RelationshipCache with `get_universe_symbols()` method
- definition_groups/group_memberships tables populated
- Multi-universe join syntax (colon separator)

### External Systems
- TickStockPL job handler for `tickstock.jobs.data_load` channel
- Redis pub-sub for job submission
- TimescaleDB for OHLCV storage (5 tables)

---

## Next Steps (Post-Sprint 62)

1. **Sprint 63**: Add bulk universe management UI (create/edit/delete universes)
2. **Sprint 64**: Historical data quality dashboard (gaps, outliers)
3. **Sprint 65**: Scheduled universe loads (daily refresh automation)

---

## References

- **Sprint 61**: `docs/planning/sprints/sprint61/SPRINT61_COMPLETE.md`
- **RelationshipCache**: `src/core/services/relationship_cache.py`
- **WebSocket Integration**: `docs/architecture/websockets-integration.md`
- **Historical Data API**: `src/api/rest/admin_historical_data_redis.py`

---

**Ready for Implementation** ✅

All dependencies met (Sprint 61 complete), clear design, testable success criteria.
