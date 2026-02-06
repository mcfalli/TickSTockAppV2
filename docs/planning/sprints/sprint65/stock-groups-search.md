name: "Stock Groups Search - Interactive Multi-Select Interface"
description: |
  Sprint 65: Stock Groups Search Feature PRP
  Interactive table interface for selecting and filtering definition_groups (ETFs, sectors, themes, universes)
  with dynamic search, multi-selection, and group detail display.

---

## Goal

**Feature Goal**: Create an interactive stock groups selector that allows users to search, filter, and select one or more items from the definition_groups table (indexes, sectors, industries, themes) with real-time filtering and multi-selection support.

**Deliverable**:
- REST API endpoint: `GET /api/stock-groups` - Returns filterable definition_groups data
- HTML template: `web/templates/dashboard/market_stock_selector.html` - Interactive selection interface
- JavaScript component: `web/static/js/components/stock-group-selector.js` - Client-side logic
- Integration: Selected groups display details in responsive grid layout

**Success Definition**:
- Users can search and filter 55+ groups (24 ETFs, 11 sectors, 20 themes, 4 universes) in <100ms
- Multi-select checkboxes allow bulk selection
- Dynamic search filters by name, type, or description in real-time
- Selected groups display details (member count, metadata) in grid format
- Responsive design works on desktop and mobile
- All tests passing (API, service, integration)

## User Persona

**Target User**: Traders, analysts, and portfolio managers

**Use Case**: Building watchlists, comparing market segments, analyzing sector correlations

**User Journey**:
1. User navigates to Stock Groups Search page
2. Sees table of all available groups (ETFs, sectors, themes, universes)
3. Uses search bar to filter by keywords (e.g., "tech", "S&P")
4. Applies type filter (e.g., only ETFs or only sectors)
5. Selects multiple groups via checkboxes
6. Clicks "Confirm Selection" to see detailed view
7. Grid displays selected groups with member counts, descriptions, and metadata

**Pain Points Addressed**:
- **Manual symbol entry tedious**: Bulk selection via universe/ETF/sector groupings
- **No visibility into group composition**: Shows member counts and metadata
- **Difficult to compare segments**: Multi-select enables side-by-side comparison
- **Slow navigation**: Real-time filtering without page reloads

## Why

- **Business Value**: Accelerates portfolio analysis and watchlist creation from 10+ minutes to <1 minute
- **Integration**: Leverages Sprint 59-61 RelationshipCache infrastructure (definition_groups/group_memberships tables)
- **User Impact**: Traders can quickly identify market segments matching criteria (sector, theme, liquidity)
- **Problems Solved**:
  - Eliminates manual CSV/symbol list creation
  - Provides unified interface for all grouping types (ETF, sector, theme, universe)
  - Enables bulk operations on related stocks

## What

### User-Visible Behavior

**Table Display**:
- Responsive Bootstrap table with 9 columns:
  - Checkbox (multi-select)
  - Name (e.g., "SPY", "information_technology")
  - Type (ETF, SECTOR, THEME, UNIVERSE)
  - Description (human-readable text)
  - Member Count (number of stocks)
  - Avg Market Cap (dummy/future: "$500B")
  - YTD Performance (dummy/future: "+12.5%")
  - Volatility (dummy/future: "Medium")
  - Last Updated (timestamp)

**Search & Filter**:
- Search bar filters rows by name/type/description (case-insensitive, real-time)
- Type multi-select dropdown (ETF, SECTOR, THEME, UNIVERSE)
- Select All checkbox in table header
- Filter count badge shows active selections

**Actions**:
- "Confirm Selection" button displays selected groups in grid
- "Clear Selection" unchecks all boxes
- "Cancel" returns to previous view

**Detail Grid** (upon selection):
- Responsive card layout (3 columns on desktop, 1 on mobile)
- Each card shows: Name, Type, Description, Member Count, Metadata (JSONB display)

### Technical Requirements

- API response time: <50ms for 55 groups
- Real-time search filtering: <100ms
- Multi-select supports 1-55 simultaneous selections
- Pagination not required (dataset small: 55 rows)
- Mobile-responsive breakpoint: 992px

### Success Criteria

- [ ] API endpoint `/api/stock-groups` returns all definition_groups with metadata
- [ ] Search bar filters table rows in real-time
- [ ] Type filter dropdown narrows results
- [ ] Checkboxes enable multi-selection
- [ ] "Select All" checkbox works correctly
- [ ] Confirm button displays selected groups in grid layout
- [ ] Grid is responsive (mobile/desktop)
- [ ] Performance: API <50ms, search <100ms, UI interactions <100ms
- [ ] All tests passing (14 unit tests, 3 integration tests, 1 E2E test)

## All Needed Context

### Context Completeness Check

_This PRP provides complete context for implementation without prior TickStock knowledge:_
- ✅ Database schema (definition_groups/group_memberships) with exact column types
- ✅ RelationshipCache API with all 10+ methods documented
- ✅ Existing UI patterns (RetractableFilterController, Bootstrap tables, fetch API)
- ✅ Test patterns from Sprint 64 (threshold bars API/E2E tests)
- ✅ JavaScript component architecture (class-based with event delegation)
- ✅ Performance targets and validation gates
- ✅ Anti-patterns: NO Plotly Dash (codebase uses Bootstrap + vanilla JS)

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer (UI/UX, read-only database queries)

  database_access:
    mode: read-only
    tables:
      - definition_groups (55 rows: ETFs, sectors, themes, universes)
      - group_memberships (11,778 rows: symbol-to-group mappings)
    queries:
      - "SELECT dg.name, dg.type, dg.description, COUNT(gm.symbol) as member_count FROM definition_groups dg LEFT JOIN group_memberships gm ON dg.id = gm.group_id WHERE dg.environment = 'DEFAULT' GROUP BY dg.id"
    query_target: "<50ms for 55 groups"

  redis_channels:
    # Not applicable - no real-time updates for this feature

  websocket_integration:
    # Not applicable - no WebSocket broadcasting for this feature

  tickstockpl_api:
    # Not applicable - no TickStockPL integration for this feature

  performance_targets:
    - metric: "API response time"
      target: "<50ms (simple JOIN query)"

    - metric: "JavaScript search filtering"
      target: "<100ms for 55 rows"

    - metric: "UI interactions"
      target: "<100ms (checkbox, button clicks)"

  caching_layer:
    service: RelationshipCache
    methods_used:
      - "get_available_universes(['ETF', 'SECTOR', 'THEME', 'UNIVERSE'])"
    cache_hit_target: "<1ms"
    cache_miss_target: "<10ms"
```

### Documentation & References

```yaml
# MUST READ - Include these in your context window

# Sprint 59: Relational Database Migration (definition_groups created)
- file: docs/planning/sprints/sprint59/SPRINT59_COMPLETE.md
  why: "Understand definition_groups table schema and migration from JSONB cache_entries"
  pattern: "Relational structure with foreign keys, indexes, bidirectional integrity"
  gotcha: "Environment filtering required (WHERE environment = 'DEFAULT')"

# Sprint 60: RelationshipCache Implementation
- file: docs/planning/sprints/sprint60/SPRINT60_PLAN.md
  why: "RelationshipCache API for accessing definition_groups data"
  pattern: "Singleton with TTL-based caching, thread-safe operations"
  gotcha: "Must use get_relationship_cache() factory function, not direct instantiation"

# Sprint 61: Multi-Universe Join Support
- file: docs/planning/sprints/sprint61/SPRINT61_PLAN.md
  why: "Multi-universe loading patterns (colon-separated keys like 'sp500:nasdaq100')"
  pattern: "get_universe_symbols('sp500:nasdaq100') returns distinct union"
  gotcha: "Universe keys are case-insensitive, ETF symbols are uppercased"

# Sprint 64: Threshold Bars (Similar Feature - Follow This Pattern)
- file: src/api/rest/threshold_bars.py
  why: "Recent API endpoint pattern with Pydantic validation, RelationshipCache integration"
  pattern: "Blueprint registration, request validation, error handling, JSON responses"
  gotcha: "Must use @login_required decorator for authentication"

- file: tests/api/rest/test_threshold_bars_api.py
  why: "API test structure with mocking and validation"
  pattern: "pytest fixtures, Mock patching, response structure validation"
  gotcha: "Mock ThresholdBarService, not RelationshipCache (test API layer only)"

- file: tests/integration/test_threshold_bars_e2e.py
  why: "E2E test pattern with real components"
  pattern: "Flask test client, no mocking (except login), performance validation"
  gotcha: "Tests must handle service unavailability gracefully (200 or 500 acceptable)"

# Bootstrap Table Patterns (Existing UI)
- file: web/templates/admin/users_dashboard.html
  why: "Bootstrap table with checkboxes, pagination, inline actions"
  pattern: "table.table.table-striped, checkbox inputs, badge components, action buttons"
  gotcha: "Use data attributes for storing metadata, event delegation for dynamic content"

- file: web/templates/admin/historical_data.html
  why: "Form controls with conditional visibility, dropdown selectors"
  pattern: "Radio button groups toggle section visibility, multi-select checkboxes"
  gotcha: "JavaScript controls display:none/block based on selection"

# JavaScript Filter Component (Existing)
- file: web/static/js/components/retractable-filter-controller.js
  why: "Class-based component architecture with state management"
  pattern: "Constructor initialization, event delegation, localStorage state persistence"
  gotcha: "Clean up event handlers in destroy() method to prevent memory leaks"

# RelationshipCache Implementation
- file: src/core/services/relationship_cache.py
  why: "Primary data access layer for definition_groups"
  pattern: "get_available_universes(types=['ETF', 'SECTOR', 'THEME', 'UNIVERSE']) returns metadata list"
  gotcha: "Returns list of dicts with keys: name, type, description, member_count, environment, created_at, updated_at"

# Market Overview Template (Copy This)
- file: web/templates/dashboard/market_overview.html
  why: "Base template to copy for market_stock_selector.html"
  pattern: "Bootstrap card layout, responsive grid, script initialization function"
  gotcha: "Copy structure but replace threshold bar logic with stock group selection logic"
```

### Current Codebase Tree

```bash
# Relevant existing files (no changes required)
src/
├── core/
│   └── services/
│       └── relationship_cache.py              # Data source (read-only)
├── api/
│   └── rest/
│       ├── threshold_bars.py                  # Similar API pattern (Sprint 64)
│       └── admin_cache.py                     # Cache management endpoints
web/
├── templates/
│   ├── dashboard/
│   │   ├── market_overview.html               # Template to copy
│   │   └── index.html                         # Register new page here
│   └── admin/
│       ├── users_dashboard.html               # Bootstrap table pattern
│       └── historical_data.html               # Form controls pattern
└── static/
    ├── js/
    │   ├── components/
    │   │   ├── retractable-filter-controller.js  # Filter component pattern
    │   │   └── threshold-bar-renderer.js          # Similar JavaScript pattern
    │   └── services/
    │       └── filter-presets.js              # Advanced filtering logic
    └── css/
        └── components/
            └── threshold-bars.css             # Similar styling pattern

tests/
├── api/
│   └── rest/
│       └── test_threshold_bars_api.py         # API test pattern
├── core/
│   └── services/
│       └── test_threshold_bar_service.py      # Service test pattern
└── integration/
    └── test_threshold_bars_e2e.py             # E2E test pattern
```

### Desired Codebase Tree (files to CREATE)

```bash
src/
├── api/
│   └── rest/
│       └── stock_groups.py                    # NEW: API endpoint for stock groups data
├── core/
│   └── services/
│       └── stock_group_service.py             # NEW: Business logic layer (optional if simple)

web/
├── templates/
│   └── dashboard/
│       └── market_stock_selector.html         # NEW: Copied from market_overview.html
└── static/
    ├── js/
    │   └── components/
    │       └── stock-group-selector.js        # NEW: Client-side selection logic
    └── css/
        └── components/
            └── stock-group-selector.css       # NEW: Styling for selector interface

tests/
├── api/
│   └── rest/
│       └── test_stock_groups_api.py           # NEW: API endpoint tests (14 tests)
├── core/
│   └── services/
│       └── test_stock_group_service.py        # NEW: Service layer tests (if service created)
└── integration/
    └── test_stock_groups_e2e.py               # NEW: E2E integration tests (3 tests)
```

**File Responsibilities**:

| File | Responsibility | Lines Est. |
|------|----------------|------------|
| `src/api/rest/stock_groups.py` | REST API endpoint with Pydantic validation | ~150 |
| `web/templates/dashboard/market_stock_selector.html` | HTML structure with Bootstrap table | ~300 |
| `web/static/js/components/stock-group-selector.js` | Search, filter, multi-select logic | ~400 |
| `web/static/css/components/stock-group-selector.css` | Responsive styling | ~150 |
| `tests/api/rest/test_stock_groups_api.py` | API tests (validation, errors, success) | ~350 |
| `tests/integration/test_stock_groups_e2e.py` | E2E tests (API→Service→DB flow) | ~200 |

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: NO PLOTLY DASH IN CODEBASE
# The original design document mentioned Plotly Dash, but the codebase DOES NOT use it.
# Use Bootstrap + vanilla JavaScript + fetch API instead (existing pattern in all dashboards)

# CRITICAL: Flask Application Context
# Flask stores application state in current_app context at RUNTIME
# Pattern: Use `from flask import current_app` then `getattr(current_app, 'attr_name')`

# CRITICAL: RelationshipCache Singleton Pattern
# MUST use factory function: get_relationship_cache()
# NEVER instantiate RelationshipCache() directly (breaks singleton)

# CRITICAL: Database Environment Filtering
# All queries MUST filter by environment (WHERE dg.environment = 'DEFAULT')
# Without this, test data leaks into production queries

# CRITICAL: Definition Groups Table Structure
# definition_groups.type CHECK constraint: ('ETF', 'THEME', 'SECTOR', 'SEGMENT', 'CUSTOM')
# Current data: 24 ETFs, 11 sectors, 20 themes, 4 universes (mapped to 'SEGMENT' type)
# Query pattern: LEFT JOIN group_memberships for member counts (some groups may have 0 members)

# CRITICAL: RelationshipCache get_available_universes() Method
# Returns list of dicts with keys: name, type, description, member_count, environment, created_at, updated_at
# Filter by types parameter: ['ETF', 'SECTOR', 'THEME', 'UNIVERSE']
# Cache hit: <1ms, Cache miss: <10ms (database query + cache population)

# CRITICAL: Bootstrap Table with Checkboxes
# Event delegation required for dynamically rendered rows
# Pattern: Attach listeners to table parent, not individual checkboxes
# Example: table.addEventListener('change', (e) => { if (e.target.type === 'checkbox') { ... } })

# CRITICAL: JavaScript Array Filtering Performance
# For 55 rows, use Array.filter() with toLowerCase() for case-insensitive search
# Pattern: rows.filter(row => row.name.toLowerCase().includes(searchTerm.toLowerCase()))
# Target: <100ms for real-time filtering

# CRITICAL: Fetch API Error Handling
# Always handle both network errors AND HTTP errors
# Pattern:
# fetch(url).then(response => {
#     if (!response.ok) throw new Error(`HTTP ${response.status}`);
#     return response.json();
# }).catch(error => { /* display user-friendly error */ });

# CRITICAL: CSRF Token for POST Requests
# Include CSRF token in headers for all POST/PUT/DELETE requests
# Pattern: headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
# This feature is GET-only, but include for future extensibility

# CRITICAL: Responsive Design Breakpoints
# TickStock uses Bootstrap 5.1.3 default breakpoints
# Mobile: <992px, Desktop: >=992px
# Pattern: Use Bootstrap .col-lg-* classes for responsive grid

# CRITICAL: Test Isolation
# API tests MUST mock service layer (test API only)
# E2E tests SHOULD NOT mock (test full stack)
# Pattern: Use unittest.mock.patch for service mocking in API tests

# CRITICAL: Performance Testing
# All endpoints must complete in <50ms for read queries
# Test with: import time; start = time.time(); result = func(); elapsed = (time.time() - start) * 1000
# Assert: elapsed < 50

# CRITICAL: Authentication Decorators
# User-facing pages: @login_required
# Admin-only pages: @admin_required
# This feature is user-facing, use @login_required
```

## Implementation Blueprint

### Data Models and Structure

```python
# API Response Model (Pydantic)
# File: src/api/rest/stock_groups.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class StockGroupMetadata(BaseModel):
    """Metadata for a single stock group."""
    name: str = Field(..., description="Group name (e.g., 'SPY', 'information_technology')")
    type: str = Field(..., description="Group type: ETF, SECTOR, THEME, UNIVERSE")
    description: Optional[str] = Field(None, description="Human-readable description")
    member_count: int = Field(..., description="Number of stocks in group")
    environment: str = Field(..., description="Environment: DEFAULT, TEST, UAT, PROD")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional metadata (not in database, computed if needed)
    avg_market_cap: Optional[str] = Field(None, description="Average market cap (future)")
    ytd_performance: Optional[str] = Field(None, description="YTD performance (future)")
    volatility: Optional[str] = Field(None, description="Volatility level (future)")

class StockGroupsResponse(BaseModel):
    """API response for /api/stock-groups endpoint."""
    groups: List[StockGroupMetadata]
    total_count: int
    types: List[str]  # Unique types in response
    environment: str

class StockGroupsRequest(BaseModel):
    """Query parameters for stock groups endpoint."""
    types: Optional[List[str]] = Field(None, description="Filter by types: ETF, SECTOR, THEME, UNIVERSE")
    search: Optional[str] = Field(None, description="Search term for name/description")
```

### Implementation Tasks (ordered by dependencies)

```yaml
# Task 1: CREATE REST API Endpoint
Task 1: CREATE src/api/rest/stock_groups.py
  - IMPLEMENT: Flask Blueprint with GET /api/stock-groups endpoint
  - FOLLOW pattern: src/api/rest/threshold_bars.py (Blueprint, Pydantic validation, error handling)
  - NAMING: stock_groups_bp Blueprint, get_stock_groups() route function
  - DATABASE: Read-only via RelationshipCache.get_available_universes()
  - PLACEMENT: API layer in src/api/rest/
  - AUTHENTICATION: @login_required decorator
  - PYDANTIC MODELS: StockGroupMetadata, StockGroupsResponse, StockGroupsRequest
  - QUERY PARAMETERS:
    - types: Optional[str] - Comma-separated types (default: 'ETF,SECTOR,THEME,UNIVERSE')
    - search: Optional[str] - Search filter (applied server-side or client-side)
  - RESPONSE: JSON with groups list, total_count, types, environment
  - ERROR HANDLING: 400 for validation errors, 500 for service errors
  - DEPENDENCIES: RelationshipCache singleton (via get_relationship_cache())
  - GOTCHA: Must filter by environment='DEFAULT' in queries
  - PERFORMANCE: Target <50ms response time
  - VALIDATION: Use Pydantic for request/response validation

# Task 2: MODIFY src/api/rest/main.py
Task 2: MODIFY src/api/rest/main.py
  - INTEGRATE: Register stock_groups_bp Blueprint with Flask app
  - FOLLOW pattern: Existing blueprint registrations (threshold_bars_bp, etc.)
  - ADD: Import and register new blueprint
  - LOCATION: After other blueprint registrations (~line 50)
  - CODE:
    ```python
    from src.api.rest.stock_groups import stock_groups_bp
    app.register_blueprint(stock_groups_bp)
    ```
  - PRESERVE: Existing route registrations

# Task 3: CREATE HTML Template
Task 3: CREATE web/templates/dashboard/market_stock_selector.html
  - IMPLEMENT: Bootstrap table with multi-select checkboxes and search
  - FOLLOW pattern: web/templates/dashboard/market_overview.html (structure, cards, responsive grid)
  - ADDITIONAL patterns: web/templates/admin/users_dashboard.html (table with checkboxes)
  - STRUCTURE:
    - Header with title and refresh button
    - Search bar (text input)
    - Type filter (multi-select dropdown or checkboxes)
    - Bootstrap table (.table.table-striped.table-hover)
    - Columns: Checkbox, Name, Type, Description, Member Count, (dummy columns)
    - Select All checkbox in header row
    - Action buttons: Confirm Selection, Clear Selection, Cancel
    - Detail grid (hidden until selection confirmed)
  - RESPONSIVE: Bootstrap .col-lg-* classes for mobile/desktop
  - SCRIPT SECTION: window.initializeStockGroupSelector() function
  - DEPENDENCIES:
    - <script src="{{ url_for('static', filename='js/components/stock-group-selector.js') }}"></script>
    - <link rel="stylesheet" href="{{ url_for('static', filename='css/components/stock-group-selector.css') }}">
  - GOTCHA: Use event delegation for checkbox handlers (dynamic content)

# Task 4: CREATE JavaScript Component
Task 4: CREATE web/static/js/components/stock-group-selector.js
  - IMPLEMENT: StockGroupSelector class with search, filter, multi-select logic
  - FOLLOW pattern: web/static/js/components/retractable-filter-controller.js (class-based, event delegation)
  - ADDITIONAL patterns: web/static/js/components/threshold-bar-renderer.js (fetch API, error handling)
  - CLASS STRUCTURE:
    - constructor(config) - Initialize with container ID, API endpoint
    - async loadGroups() - Fetch data from /api/stock-groups
    - renderTable(groups) - Populate Bootstrap table
    - setupEventHandlers() - Attach search, filter, checkbox, button listeners
    - handleSearch(event) - Filter table rows by search term
    - handleTypeFilter(event) - Filter by selected types
    - handleSelectAll(event) - Toggle all checkboxes
    - handleCheckboxChange(event) - Track selected groups
    - handleConfirmSelection() - Display selected groups in grid
    - handleClearSelection() - Uncheck all boxes
    - renderDetailGrid(selectedGroups) - Create responsive card grid
  - PERFORMANCE: Filter 55 rows in <100ms (use Array.filter())
  - ERROR HANDLING: Display user-friendly messages, retry button
  - STATE MANAGEMENT: Track selectedGroups array, filteredGroups array
  - DEPENDENCIES: Bootstrap 5.1.3, Font Awesome 6.0.0
  - GOTCHA: Use event delegation for checkbox listeners (table.addEventListener('change', ...))

# Task 5: CREATE CSS Styling
Task 5: CREATE web/static/css/components/stock-group-selector.css
  - IMPLEMENT: Responsive styling for table, search, filters, detail grid
  - FOLLOW pattern: web/static/css/components/threshold-bars.css (responsive flexbox, theme-aware)
  - STYLES:
    - .stock-group-selector-container - Main container
    - .stock-group-search-bar - Search input styling
    - .stock-group-type-filter - Filter dropdown styling
    - .stock-group-table - Table styling (striped, hover)
    - .stock-group-detail-grid - Responsive card grid (3 cols desktop, 1 col mobile)
    - .stock-group-card - Individual group card
    - .stock-group-actions - Action button group
  - RESPONSIVE: @media (max-width: 992px) for mobile
  - THEME SUPPORT: Use CSS variables for light/dark mode (--bs-body-color, --bs-body-bg)
  - GOTCHA: Use flexbox for responsive grid, not CSS Grid (better browser support)

# Task 6: MODIFY Dashboard Index (Optional)
Task 6: MODIFY web/templates/dashboard/index.html
  - INTEGRATE: Add link to Stock Groups Search page in sidebar
  - FOLLOW pattern: Existing sidebar navigation items
  - ADD: Menu item after "Market Overview" (3rd position)
  - CODE:
    ```html
    <li class="nav-item">
        <a href="/stock-groups" class="nav-link">
            <i class="fas fa-layer-group"></i> Stock Groups
        </a>
    </li>
    ```
  - ROUTE: Need to create Flask route in src/app.py:
    ```python
    @app.route('/stock-groups')
    @login_required
    def stock_groups_page():
        return render_template('dashboard/market_stock_selector.html')
    ```

# Task 7: CREATE API Unit Tests
Task 7: CREATE tests/api/rest/test_stock_groups_api.py
  - IMPLEMENT: 14 unit tests for API endpoint
  - FOLLOW pattern: tests/api/rest/test_threshold_bars_api.py (pytest, mocking, fixtures)
  - TEST COVERAGE:
    1. test_blueprint_registration - Blueprint registers successfully
    2. test_blueprint_has_routes - Blueprint has expected routes
    3. test_successful_get_all_groups - GET request returns all groups
    4. test_successful_get_filtered_by_type - Filter by single type (ETF)
    5. test_successful_get_multiple_types - Filter by multiple types (ETF,SECTOR)
    6. test_successful_get_with_search - Search term filters results
    7. test_empty_result_set - No groups match criteria (returns empty list)
    8. test_invalid_type_parameter - Invalid type returns 400
    9. test_authentication_required - Unauthenticated request returns 401
    10. test_service_error_handling - Service exception returns 500
    11. test_response_structure_validation - Response matches Pydantic schema
    12. test_member_count_accuracy - Member counts match group_memberships
    13. test_environment_filtering - Only DEFAULT environment returned
    14. test_performance_under_50ms - Response time <50ms (mocked)
  - MOCKING: Mock RelationshipCache.get_available_universes() with sample data
  - FIXTURES: app, client, sample_groups_data
  - ASSERTIONS: Response status, JSON structure, data accuracy
  - GOTCHA: Mock at function level, not module level (patch 'src.api.rest.stock_groups.get_relationship_cache')

# Task 8: CREATE E2E Integration Tests
Task 8: CREATE tests/integration/test_stock_groups_e2e.py
  - IMPLEMENT: 3 end-to-end tests with real components
  - FOLLOW pattern: tests/integration/test_threshold_bars_e2e.py (Flask test client, no mocking)
  - TEST COVERAGE:
    1. test_e2e_get_all_stock_groups - Full flow with real RelationshipCache
    2. test_e2e_filter_by_type_etf - Type filtering end-to-end
    3. test_e2e_search_term_filtering - Search filtering end-to-end (if server-side search implemented)
  - NO MOCKING: Test real API → RelationshipCache → Database flow
  - FIXTURES: app, client (with test config)
  - VALIDATION:
    - Response status 200 or 500 (acceptable if DB unavailable)
    - JSON structure matches schema
    - Member counts accurate (if DB available)
    - Performance <50ms (if DB available)
  - GOTCHA: Tests must handle service unavailability gracefully (don't fail on 500)

# Task 9: MODIFY Sidebar Navigation Controller (Optional)
Task 9: MODIFY web/static/js/components/sidebar-navigation-controller.js
  - INTEGRATE: Add active state for Stock Groups page
  - FOLLOW pattern: Existing active state logic for dashboard sections
  - ADD: Check for window.location.pathname === '/stock-groups'
  - HIGHLIGHT: Corresponding sidebar menu item
  - PRESERVE: Existing navigation logic

# Task 10: CREATE Service Layer (Optional - if complex logic needed)
Task 10: CREATE src/core/services/stock_group_service.py (OPTIONAL)
  - IMPLEMENT: Business logic layer if API needs more than simple RelationshipCache calls
  - FOLLOW pattern: src/core/services/threshold_bar_service.py (class-based service)
  - METHODS:
    - get_stock_groups(types=None, search=None) - Returns filtered list
    - get_group_details(group_name, group_type) - Returns detailed metadata
  - DEPENDENCIES: RelationshipCache via get_relationship_cache()
  - DECISION: Only create if API needs complex filtering/aggregation logic
  - NOTE: For simple queries, direct RelationshipCache usage in API is sufficient
```

### Implementation Patterns & Key Details

```python
# Pattern 1: REST API Endpoint with Pydantic Validation
# File: src/api/rest/stock_groups.py

from flask import Blueprint, jsonify, request
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
from datetime import datetime
import logging

from src.core.services.relationship_cache import get_relationship_cache
from src.utils.auth_decorators import login_required

logger = logging.getLogger(__name__)

stock_groups_bp = Blueprint('stock_groups', __name__)

# Pydantic Models (defined in Data Models section above)
class StockGroupMetadata(BaseModel):
    # ... (see Data Models section)

class StockGroupsResponse(BaseModel):
    # ... (see Data Models section)

@stock_groups_bp.route('/api/stock-groups', methods=['GET'])
@login_required
def get_stock_groups():
    """
    Get filterable list of stock groups (ETFs, sectors, themes, universes).

    Query Parameters:
        types: Comma-separated list (default: 'ETF,SECTOR,THEME,UNIVERSE')
        search: Search term for name/description (optional)

    Returns:
        JSON: {groups: [...], total_count: int, types: [...], environment: str}
    """
    try:
        # Parse query parameters
        types_param = request.args.get('types', 'ETF,SECTOR,THEME,UNIVERSE')
        search_term = request.args.get('search', None)

        # Convert comma-separated types to list
        types_list = [t.strip().upper() for t in types_param.split(',')]

        # Validate types
        valid_types = {'ETF', 'SECTOR', 'THEME', 'UNIVERSE', 'SEGMENT', 'CUSTOM'}
        if not all(t in valid_types for t in types_list):
            return jsonify({
                "error": "Invalid type parameter",
                "valid_types": list(valid_types)
            }), 400

        # Get data from RelationshipCache
        cache = get_relationship_cache()
        groups_data = cache.get_available_universes(types=types_list)

        # Apply search filter (server-side, case-insensitive)
        if search_term:
            search_lower = search_term.lower()
            groups_data = [
                g for g in groups_data
                if search_lower in g['name'].lower()
                or (g.get('description') and search_lower in g['description'].lower())
                or search_lower in g['type'].lower()
            ]

        # Build response
        response = StockGroupsResponse(
            groups=[StockGroupMetadata(**g) for g in groups_data],
            total_count=len(groups_data),
            types=types_list,
            environment='DEFAULT'
        )

        return jsonify(response.dict()), 200

    except ValidationError as e:
        logger.error(f"Validation error in get_stock_groups: {e}")
        return jsonify({"error": "Validation error", "details": str(e)}), 400

    except Exception as e:
        logger.error(f"Error in get_stock_groups: {e}")
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


# Pattern 2: JavaScript Component with Search and Multi-Select
# File: web/static/js/components/stock-group-selector.js

class StockGroupSelector {
    constructor(config) {
        this.containerId = config.containerId;
        this.apiEndpoint = config.apiEndpoint || '/api/stock-groups';
        this.csrfToken = config.csrfToken || '';

        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error(`StockGroupSelector: Container '${this.containerId}' not found`);
            return;
        }

        // State
        this.allGroups = [];
        this.filteredGroups = [];
        this.selectedGroups = [];
        this.searchTerm = '';
        this.selectedTypes = ['ETF', 'SECTOR', 'THEME', 'UNIVERSE'];

        // Initialize
        this.init();
    }

    async init() {
        console.log('StockGroupSelector: Initializing...');

        // Load data
        await this.loadGroups();

        // Render table
        this.renderTable();

        // Setup event handlers
        this.setupEventHandlers();

        console.log('StockGroupSelector: Initialized successfully');
    }

    async loadGroups() {
        try {
            const url = `${this.apiEndpoint}?types=${this.selectedTypes.join(',')}`;
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.allGroups = data.groups;
            this.filteredGroups = [...this.allGroups];

            console.log(`Loaded ${this.allGroups.length} stock groups`);

        } catch (error) {
            console.error('Error loading stock groups:', error);
            this.displayError('Failed to load stock groups. Please try again.');
        }
    }

    renderTable() {
        // Find table body
        const tbody = this.container.querySelector('.stock-group-table tbody');
        if (!tbody) {
            console.error('Table body not found');
            return;
        }

        // Clear existing rows
        tbody.innerHTML = '';

        // Render filtered groups
        this.filteredGroups.forEach((group, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="checkbox" class="form-check-input group-checkbox" data-index="${index}" data-name="${group.name}" data-type="${group.type}"></td>
                <td>${group.name}</td>
                <td><span class="badge bg-primary">${group.type}</span></td>
                <td>${group.description || '-'}</td>
                <td>${group.member_count}</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>${new Date(group.updated_at).toLocaleDateString()}</td>
            `;
            tbody.appendChild(row);
        });

        // Update count badge
        this.updateFilterBadge();
    }

    setupEventHandlers() {
        // Search bar
        const searchInput = this.container.querySelector('.stock-group-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.handleSearch(e));
        }

        // Type filter checkboxes
        const typeFilters = this.container.querySelectorAll('.type-filter-checkbox');
        typeFilters.forEach(cb => {
            cb.addEventListener('change', (e) => this.handleTypeFilter(e));
        });

        // Select All checkbox
        const selectAllCheckbox = this.container.querySelector('#select-all-checkbox');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => this.handleSelectAll(e));
        }

        // Table checkboxes (event delegation)
        const table = this.container.querySelector('.stock-group-table');
        if (table) {
            table.addEventListener('change', (e) => {
                if (e.target.classList.contains('group-checkbox')) {
                    this.handleCheckboxChange(e);
                }
            });
        }

        // Action buttons
        const confirmBtn = this.container.querySelector('.confirm-selection-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.handleConfirmSelection());
        }

        const clearBtn = this.container.querySelector('.clear-selection-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.handleClearSelection());
        }
    }

    handleSearch(event) {
        this.searchTerm = event.target.value.toLowerCase();
        this.applyFilters();
    }

    handleTypeFilter(event) {
        const type = event.target.value;
        if (event.target.checked) {
            this.selectedTypes.push(type);
        } else {
            this.selectedTypes = this.selectedTypes.filter(t => t !== type);
        }
        this.applyFilters();
    }

    applyFilters() {
        // Filter by type
        let filtered = this.allGroups.filter(group =>
            this.selectedTypes.includes(group.type)
        );

        // Filter by search term
        if (this.searchTerm) {
            filtered = filtered.filter(group =>
                group.name.toLowerCase().includes(this.searchTerm) ||
                (group.description && group.description.toLowerCase().includes(this.searchTerm)) ||
                group.type.toLowerCase().includes(this.searchTerm)
            );
        }

        this.filteredGroups = filtered;
        this.renderTable();
    }

    handleSelectAll(event) {
        const checkboxes = this.container.querySelectorAll('.group-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = event.target.checked;
        });
        this.updateSelectedGroups();
    }

    handleCheckboxChange(event) {
        this.updateSelectedGroups();
    }

    updateSelectedGroups() {
        const checkboxes = this.container.querySelectorAll('.group-checkbox:checked');
        this.selectedGroups = Array.from(checkboxes).map(cb => {
            const name = cb.dataset.name;
            const type = cb.dataset.type;
            return this.allGroups.find(g => g.name === name && g.type === type);
        });

        console.log(`Selected ${this.selectedGroups.length} groups`);
    }

    handleConfirmSelection() {
        if (this.selectedGroups.length === 0) {
            alert('Please select at least one group');
            return;
        }

        console.log('Confirming selection:', this.selectedGroups);
        this.renderDetailGrid(this.selectedGroups);
    }

    handleClearSelection() {
        const checkboxes = this.container.querySelectorAll('.group-checkbox');
        checkboxes.forEach(cb => { cb.checked = false; });
        this.selectedGroups = [];

        // Hide detail grid
        const detailGrid = this.container.querySelector('.stock-group-detail-grid');
        if (detailGrid) {
            detailGrid.style.display = 'none';
        }
    }

    renderDetailGrid(groups) {
        // Find or create detail grid container
        let detailGrid = this.container.querySelector('.stock-group-detail-grid');
        if (!detailGrid) {
            detailGrid = document.createElement('div');
            detailGrid.className = 'stock-group-detail-grid row mt-4';
            this.container.appendChild(detailGrid);
        }

        // Clear existing cards
        detailGrid.innerHTML = '';

        // Create cards for selected groups
        groups.forEach(group => {
            const card = document.createElement('div');
            card.className = 'col-lg-4 col-md-6 mb-3';
            card.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <h5>${group.name} <span class="badge bg-primary">${group.type}</span></h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Description:</strong> ${group.description || 'N/A'}</p>
                        <p><strong>Member Count:</strong> ${group.member_count} stocks</p>
                        <p><strong>Environment:</strong> ${group.environment}</p>
                        <p><strong>Last Updated:</strong> ${new Date(group.updated_at).toLocaleDateString()}</p>
                    </div>
                </div>
            `;
            detailGrid.appendChild(card);
        });

        // Show detail grid
        detailGrid.style.display = 'flex';

        // Scroll to detail grid
        detailGrid.scrollIntoView({ behavior: 'smooth' });
    }

    updateFilterBadge() {
        const badge = this.container.querySelector('.filter-count-badge');
        if (badge) {
            badge.textContent = `${this.filteredGroups.length} groups`;
        }
    }

    displayError(message) {
        // Display user-friendly error message
        const statusEl = this.container.querySelector('.status-message');
        if (statusEl) {
            statusEl.innerHTML = `<i class="fas fa-exclamation-triangle text-danger"></i> ${message}`;
        }
    }
}

// Export for use in template
window.StockGroupSelector = StockGroupSelector;


# Pattern 3: Bootstrap Table with Multi-Select
# File: web/templates/dashboard/market_stock_selector.html (key sections)

<div id="stock-group-selector-content" class="dashboard-content-section">
    <!-- Header -->
    <div class="section-header">
        <h2><i class="fas fa-layer-group"></i> Stock Groups Search</h2>
        <button id="refresh-stock-groups-btn" class="btn btn-sm btn-primary">
            <i class="fas fa-sync-alt"></i> Refresh
        </button>
    </div>

    <!-- Search and Filters -->
    <div class="row mb-3">
        <div class="col-md-6">
            <input type="text" class="form-control stock-group-search-input" placeholder="Search by name, type, or description...">
        </div>
        <div class="col-md-6">
            <div class="btn-group" role="group">
                <input type="checkbox" class="btn-check type-filter-checkbox" id="filter-etf" value="ETF" checked>
                <label class="btn btn-outline-primary" for="filter-etf">ETFs</label>

                <input type="checkbox" class="btn-check type-filter-checkbox" id="filter-sector" value="SECTOR" checked>
                <label class="btn btn-outline-primary" for="filter-sector">Sectors</label>

                <input type="checkbox" class="btn-check type-filter-checkbox" id="filter-theme" value="THEME" checked>
                <label class="btn btn-outline-primary" for="filter-theme">Themes</label>

                <input type="checkbox" class="btn-check type-filter-checkbox" id="filter-universe" value="UNIVERSE" checked>
                <label class="btn btn-outline-primary" for="filter-universe">Universes</label>
            </div>
            <span class="badge bg-secondary filter-count-badge ms-2">55 groups</span>
        </div>
    </div>

    <!-- Bootstrap Table -->
    <div class="table-responsive">
        <table class="table table-striped table-hover stock-group-table">
            <thead>
                <tr>
                    <th><input type="checkbox" class="form-check-input" id="select-all-checkbox"></th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Member Count</th>
                    <th>Avg Market Cap</th>
                    <th>YTD Performance</th>
                    <th>Volatility</th>
                    <th>Last Updated</th>
                </tr>
            </thead>
            <tbody>
                <!-- Populated by JavaScript -->
            </tbody>
        </table>
    </div>

    <!-- Action Buttons -->
    <div class="row mt-3">
        <div class="col-12">
            <button class="btn btn-primary confirm-selection-btn">Confirm Selection</button>
            <button class="btn btn-secondary clear-selection-btn">Clear Selection</button>
            <button class="btn btn-outline-secondary" onclick="history.back()">Cancel</button>
        </div>
    </div>

    <!-- Detail Grid (hidden initially) -->
    <div class="stock-group-detail-grid row mt-4" style="display: none;">
        <!-- Populated by JavaScript -->
    </div>

    <!-- Status Message -->
    <div class="status-message text-center text-muted mt-3">
        <i class="fas fa-spinner fa-spin"></i> Loading stock groups...
    </div>
</div>

<script src="{{ url_for('static', filename='js/components/stock-group-selector.js') }}"></script>
<script>
    window.initializeStockGroupSelector = function() {
        const selector = new StockGroupSelector({
            containerId: 'stock-group-selector-content',
            apiEndpoint: '/api/stock-groups',
            csrfToken: document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
        });
    };

    // Auto-initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
        window.initializeStockGroupSelector();
    });
</script>


# Pattern 4: API Unit Test with Mocking
# File: tests/api/rest/test_stock_groups_api.py (key test)

import pytest
from unittest.mock import Mock, patch
from flask import Flask
from src.api.rest.stock_groups import stock_groups_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'

    # Mock login_required decorator
    with patch('src.api.rest.stock_groups.login_required', lambda f: f):
        app.register_blueprint(stock_groups_bp)

    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_groups_data():
    return [
        {
            'name': 'SPY',
            'type': 'ETF',
            'description': 'SPDR S&P 500 ETF Trust',
            'member_count': 504,
            'environment': 'DEFAULT',
            'created_at': '2025-12-20T10:00:00',
            'updated_at': '2025-12-28T10:00:00'
        },
        {
            'name': 'information_technology',
            'type': 'SECTOR',
            'description': 'Information Technology Sector',
            'member_count': 549,
            'environment': 'DEFAULT',
            'created_at': '2025-12-20T10:00:00',
            'updated_at': '2025-12-28T10:00:00'
        }
    ]

def test_successful_get_all_groups(client, sample_groups_data):
    """Test successful retrieval of all stock groups."""
    with patch('src.api.rest.stock_groups.get_relationship_cache') as mock_cache_factory:
        # Mock RelationshipCache
        mock_cache = Mock()
        mock_cache_factory.return_value = mock_cache
        mock_cache.get_available_universes.return_value = sample_groups_data

        response = client.get('/api/stock-groups')

        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = response.json
        assert 'groups' in data
        assert 'total_count' in data
        assert data['total_count'] == 2
        assert len(data['groups']) == 2
        assert data['groups'][0]['name'] == 'SPY'

def test_successful_get_filtered_by_type(client, sample_groups_data):
    """Test filtering by single type (ETF)."""
    with patch('src.api.rest.stock_groups.get_relationship_cache') as mock_cache_factory:
        mock_cache = Mock()
        mock_cache_factory.return_value = mock_cache
        mock_cache.get_available_universes.return_value = [sample_groups_data[0]]  # Only ETF

        response = client.get('/api/stock-groups?types=ETF')

        assert response.status_code == 200
        data = response.json
        assert data['total_count'] == 1
        assert data['groups'][0]['type'] == 'ETF'

def test_invalid_type_parameter(client):
    """Test invalid type parameter returns 400."""
    response = client.get('/api/stock-groups?types=INVALID_TYPE')

    assert response.status_code == 400
    data = response.json
    assert 'error' in data
    assert 'Invalid type parameter' in data['error']
```

### Integration Points

```yaml
# TickStock-Specific Integration Points

DATABASE:
  # No migrations required - uses existing definition_groups/group_memberships tables

  # Query patterns
  - query_location: "src/core/services/relationship_cache.py"
  - query_method: "get_available_universes(types=['ETF', 'SECTOR', 'THEME', 'UNIVERSE'])"
  - query_returns: "List[Dict] with keys: name, type, description, member_count, environment, created_at, updated_at"
  - performance: "<10ms for cache miss, <1ms for cache hit"

REDIS_CHANNELS:
  # Not applicable - no Redis pub-sub for this feature

WEBSOCKET:
  # Not applicable - no WebSocket broadcasting for this feature

FLASK_BLUEPRINTS:
  # REST API route
  - blueprint_file: "src/api/rest/stock_groups.py"
  - blueprint_name: "stock_groups_bp"
  - register_in: "src/api/rest/main.py"
  - registration_pattern: |
      from src.api.rest.stock_groups import stock_groups_bp
      app.register_blueprint(stock_groups_bp)

  # HTML page route
  - route_file: "src/app.py"
  - route_decorator: "@app.route('/stock-groups')"
  - route_function: "def stock_groups_page():"
  - authentication: "@login_required"
  - template: "render_template('dashboard/market_stock_selector.html')"

CONFIG:
  # No new environment variables required
  # Uses existing DATABASE_URI, ENVIRONMENT settings

TICKSTOCKPL_API:
  # Not applicable - no TickStockPL integration for this feature

STARTUP:
  # No startup service initialization required
  # RelationshipCache is singleton, initialized on first access
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# Run after each file creation

# File-specific validation
ruff check src/api/rest/stock_groups.py --fix
ruff format src/api/rest/stock_groups.py

ruff check web/static/js/components/stock-group-selector.js --fix
ruff format web/static/js/components/stock-group-selector.js

# Project-wide validation
ruff check src/ --fix
ruff format src/

# Expected: Zero errors. If errors exist, fix before proceeding.
```

### Level 2: Unit Tests (Component Validation)

```bash
# Test API endpoint layer (14 tests)
python -m pytest tests/api/rest/test_stock_groups_api.py -v

# Expected output:
# tests/api/rest/test_stock_groups_api.py::test_blueprint_registration PASSED
# tests/api/rest/test_stock_groups_api.py::test_blueprint_has_routes PASSED
# tests/api/rest/test_stock_groups_api.py::test_successful_get_all_groups PASSED
# tests/api/rest/test_stock_groups_api.py::test_successful_get_filtered_by_type PASSED
# ... (10 more tests)
# ====== 14 passed in 2.35s ======

# Coverage validation (optional)
python -m pytest tests/api/rest/test_stock_groups_api.py --cov=src.api.rest.stock_groups --cov-report=term-missing

# Expected: >90% coverage for API endpoint
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# E2E tests with real components (3 tests)
python -m pytest tests/integration/test_stock_groups_e2e.py -v

# Expected output:
# tests/integration/test_stock_groups_e2e.py::test_e2e_get_all_stock_groups PASSED
# tests/integration/test_stock_groups_e2e.py::test_e2e_filter_by_type_etf PASSED
# tests/integration/test_stock_groups_e2e.py::test_e2e_search_term_filtering PASSED
# ====== 3 passed in 1.21s ======

# MANDATORY: Run full integration test suite
python run_tests.py

# Expected output:
# - Pattern flow tests: PASSED
# - Core integration: PASSED (or acceptable failure if services not running)
# - Total runtime: ~30 seconds

# Manual UI testing
# 1. Start Flask app: python src/app.py
# 2. Navigate to http://localhost:5000/stock-groups
# 3. Verify table displays 55 groups
# 4. Test search filtering (type "tech", verify results filter)
# 5. Test type filtering (uncheck ETF, verify ETFs disappear)
# 6. Test multi-select (check 3 boxes, click Confirm, verify detail grid displays 3 cards)
# 7. Test clear selection (click Clear, verify all checkboxes unchecked)
# 8. Test responsive design (resize browser to mobile width, verify layout adapts)
```

### Level 4: TickStock-Specific Validation

```bash
# Architecture Compliance
# SKIP architecture-validation-specialist (no Producer/Consumer boundary changes)

# Performance Benchmarking
# API response time <50ms
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:5000/api/stock-groups"
# Expected: total_time < 0.050 seconds

# JavaScript search performance <100ms
# Manual: Open DevTools Console, type in search bar, check console.time logs
# Expected: Filter operation < 100ms for 55 rows

# Database query performance <10ms (via RelationshipCache)
# Check RelationshipCache statistics
curl -s "http://localhost:5000/admin/cache/stats" | jq .stats
# Expected: avg_query_time < 10ms

# Browser compatibility testing
# Verify in: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
# Test: Search, filter, checkbox selection, responsive layout

# Accessibility validation
# Run Lighthouse accessibility audit in Chrome DevTools
# Expected: Score >90

# Security validation (if needed)
# SKIP code-security-specialist (no security-critical changes)
# Note: @login_required decorator enforces authentication
# Note: No database writes, only reads (safe)
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No linting errors: `ruff check src/`
- [ ] No formatting issues: `ruff format src/ --check`
- [ ] Unit tests pass: 14 API tests, 3 E2E tests

### Feature Validation

- [ ] API endpoint `/api/stock-groups` returns 55 groups in <50ms
- [ ] Search bar filters table rows in real-time (<100ms)
- [ ] Type filter dropdown works correctly (ETF, SECTOR, THEME, UNIVERSE)
- [ ] Checkboxes enable multi-selection (1-55 groups)
- [ ] "Select All" checkbox toggles all checkboxes
- [ ] "Confirm Selection" displays selected groups in responsive grid
- [ ] "Clear Selection" unchecks all boxes
- [ ] Detail grid shows group metadata (name, type, description, member count)
- [ ] Responsive design works on mobile (<992px) and desktop (>=992px)
- [ ] Error messages display for API failures
- [ ] Manual UI testing successful (8 test scenarios from Level 3)

### TickStock Architecture Validation

- [ ] Component role respected (TickStockAppV2 Consumer - read-only database)
- [ ] RelationshipCache used for all data access (no direct DB queries)
- [ ] Performance targets met (API <50ms, search <100ms)
- [ ] No architectural violations (no Producer logic in TickStockAppV2)
- [ ] Authentication enforced (@login_required on routes)

### Code Quality Validation

- [ ] Follows existing codebase patterns (Bootstrap tables, fetch API, class-based JS)
- [ ] File placement matches desired codebase tree structure
- [ ] Anti-patterns avoided (no Plotly Dash, no direct DB queries, no heavy processing)
- [ ] Dependencies properly managed (Bootstrap 5.1.3, Font Awesome 6.0.0)
- [ ] Code structure limits followed (<500 lines/file, <50 lines/function)
- [ ] Naming conventions: snake_case functions, PascalCase classes, kebab-case CSS

### Documentation & Deployment

- [ ] Code is self-documenting (clear variable/function names)
- [ ] Logs are informative but not verbose
- [ ] No "Generated by Claude" comments in code or commits
- [ ] Sidebar navigation updated with Stock Groups link
- [ ] Template extends base dashboard layout
- [ ] CSS follows TickStock theme system (light/dark mode support)

---

## Anti-Patterns to Avoid

### Generic Anti-Patterns
- ❌ Don't use Plotly Dash (codebase uses Bootstrap + vanilla JavaScript)
- ❌ Don't create new patterns when existing ones work (follow threshold bars pattern)
- ❌ Don't skip validation because "it should work"
- ❌ Don't ignore failing tests - fix them
- ❌ Don't hardcode values that should be config
- ❌ Don't catch all exceptions - be specific

### TickStock-Specific Anti-Patterns (CRITICAL)

#### Architecture Violations
- ❌ **Don't query database directly in API layer**
  - Use RelationshipCache for all definition_groups data access
  - Violation: `SELECT FROM definition_groups` in API endpoint

- ❌ **Don't create TickStockPL dependencies**
  - This feature is TickStockAppV2-only (no Producer logic)
  - Violation: Adding Redis pub-sub or TickStockPL API calls

#### Data Handling
- ❌ **Don't miss environment filtering**
  - All queries must filter by environment='DEFAULT'
  - Violation: Returning TEST/UAT data to production users

- ❌ **Don't create new RelationshipCache instances**
  - Must use get_relationship_cache() singleton factory
  - Violation: `cache = RelationshipCache()` (breaks singleton)

#### Performance
- ❌ **Don't use slow JavaScript operations**
  - For 55 rows, Array.filter() is sufficient (<100ms)
  - Violation: Complex regex or DOM manipulation in search loop

- ❌ **Don't create blocking operations**
  - Use async/await for fetch calls
  - Violation: Synchronous XHR or blocking loops

#### Testing & Validation
- ❌ **Don't skip integration tests before commits**
  - `python run_tests.py` is MANDATORY
  - Violation: Committing without running tests

- ❌ **Don't mock RelationshipCache in E2E tests**
  - E2E tests should use real components
  - Violation: Mocking cache in test_stock_groups_e2e.py

#### Code Quality
- ❌ **Don't exceed structure limits**
  - Max 500 lines per file, 50 lines per function
  - Violation: 800-line JavaScript component

- ❌ **Don't add "Generated by Claude" to code or commits**
  - Keep code and commits clean
  - Violation: Comments like "# Generated with Claude Code"

#### UI/UX
- ❌ **Don't ignore mobile responsiveness**
  - Test on <992px viewport
  - Violation: Fixed-width table that breaks on mobile

- ❌ **Don't create inaccessible UI**
  - Include ARIA labels, keyboard navigation
  - Violation: Checkboxes without labels, no keyboard shortcuts

---

## Confidence Score: 9/10

**Rationale for One-Pass Implementation Success**:
- ✅ Complete database schema documented (definition_groups/group_memberships)
- ✅ RelationshipCache API fully documented with all 10+ methods
- ✅ Existing patterns identified (threshold bars Sprint 64, Bootstrap tables, fetch API)
- ✅ Test patterns from similar feature (threshold bars API/E2E tests)
- ✅ JavaScript component architecture matches existing RetractableFilterController
- ✅ Performance targets realistic (<50ms API, <100ms search)
- ✅ NO Plotly Dash confusion (design doc corrected)
- ⚠️ Minor risk: JavaScript event delegation complexity (but pattern exists in codebase)
- ⚠️ Minor risk: First time creating multi-select table (but Bootstrap pattern is standard)

**Validation**: This PRP provides complete context for implementing the Stock Groups Search feature without requiring prior TickStock knowledge. All database schemas, API methods, test patterns, and UI patterns are documented with exact file paths and code examples.
