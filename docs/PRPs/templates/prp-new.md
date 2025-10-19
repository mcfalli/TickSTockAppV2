name: "New Feature PRP Template v1 - Implementation-Focused with Precision Standards"
description: |

---

## Goal

**Feature Goal**: [Specific, measurable end state of what needs to be built]

**Deliverable**: [Concrete artifact - API endpoint, service class, integration, etc.]

**Success Definition**: [How you'll know this is complete and working]

## User Persona (if applicable)

**Target User**: [Specific user type - developer, end user, admin, etc.]

**Use Case**: [Primary scenario when this feature will be used]

**User Journey**: [Step-by-step flow of how user interacts with this feature]

**Pain Points Addressed**: [Specific user frustrations this feature solves]

## Why

- [Business value and user impact]
- [Integration with existing features]
- [Problems this solves and for whom]

## What

[User-visible behavior and technical requirements]

### Success Criteria

- [ ] [Specific measurable outcomes]

## All Needed Context

### Context Completeness Check

_Before writing this PRP, validate: "If someone knew nothing about this codebase, would they have everything needed to implement this successfully?"_

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: [TickStockAppV2 | TickStockPL]
  role: [Consumer | Producer]

  redis_channels:
    # List all relevant channels this feature uses
    - channel: "tickstock:patterns:streaming"
      purpose: "Real-time pattern detections from TickStockPL"
      message_format: "{pattern_name, symbol, timeframe, confidence, ...}"

    - channel: "tickstock:indicators:streaming"
      purpose: "Real-time indicator calculations"
      message_format: "{indicator_name, symbol, timeframe, value, ...}"

    - channel: "tickstock:market:ticks"
      purpose: "Raw tick forwarding (AppV2 → PL)"
      message_format: "{symbol, price, volume, timestamp, ...}"

  database_access:
    mode: [read-only | read-write]
    tables: [List specific tables accessed]
    queries: [Describe query patterns - joins, aggregations, etc.]

  websocket_integration:
    broadcast_to: [Which WebSocket rooms/channels]
    message_format: [Structure of WebSocket messages]
    latency_target: "<100ms end-to-end delivery"

  tickstockpl_api:
    endpoints: [List HTTP endpoints if feature triggers TickStockPL jobs]
    format: "http://localhost:8080/api/v1/{endpoint}"

  performance_targets:
    - metric: "Symbol processing"
      target: "<1ms per symbol"

    - metric: "WebSocket delivery"
      target: "<100ms end-to-end"

    - metric: "Redis operation"
      target: "<10ms"

    - metric: "Database query"
      target: "<50ms"
```

### Documentation & References

```yaml
# MUST READ - Include these in your context window
- url: [Complete URL with section anchor]
  why: [Specific methods/concepts needed for implementation]
  critical: [Key insights that prevent common implementation errors]

- file: [exact/path/to/pattern/file.py]
  why: [Specific pattern to follow - class structure, error handling, etc.]
  pattern: [Brief description of what pattern to extract]
  gotcha: [Known constraints or limitations to avoid]

- docfile: [PRPs/ai_docs/domain_specific.md]
  why: [Custom documentation for complex library/integration patterns]
  section: [Specific section if document is large]

# TickStock-Specific References
- file: src/services/redis_event_subscriber.py
  why: "Pattern for consuming Redis pub-sub events"
  pattern: "Event handling, message parsing, WebSocket broadcasting"
  gotcha: "Always convert typed events to dicts at Worker boundary"

- file: src/services/websocket_service.py
  why: "WebSocket broadcast patterns"
  pattern: "Room management, message formatting, error handling"
  gotcha: "Use emit() with broadcast=True for multi-client updates"

- file: tests/integration/run_integration_tests.py
  why: "Integration test structure"
  pattern: "Test setup, Redis mocking, assertion patterns"
  gotcha: "Tests must complete in ~30 seconds"
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase

```bash

```

### Desired Codebase tree with files to be added and responsibility of file

```bash

```

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: [Library name] requires [specific setup]
# Example: FastAPI requires async functions for endpoints
# Example: This ORM doesn't support batch inserts over 1000 records

# TickStock-Specific Gotchas
# CRITICAL: Never mix typed events and dicts after Worker boundary
# Always convert to dict when crossing process boundaries

# CRITICAL: TickStockAppV2 is CONSUMER ONLY
# - Read from Redis pub-sub channels (patterns, indicators)
# - Query database READ-ONLY (no writes except user/session data)
# - No OHLCV aggregation (belongs in TickStockPL)
# - No pattern detection logic (belongs in TickStockPL)

# CRITICAL: Redis pub-sub message handling
# - Subscribe patterns: 'tickstock:patterns:*', 'tickstock:indicators:*'
# - Always validate message format before processing
# - Use try-except with specific error logging

# CRITICAL: WebSocket delivery requirements
# - Target: <100ms from Redis event to browser delivery
# - Use SocketIO rooms for symbol-based subscriptions
# - Batch updates within 250ms buffer for efficiency

# CRITICAL: Database queries in TickStockAppV2
# - User: app_readwrite (but enforce read-only for pattern data)
# - Never query pattern tables directly (use Redis cache)
# - Query timeout: 50ms maximum
# - Use SELECT with explicit column lists (no SELECT *)

# CRITICAL: Performance monitoring
# - Symbol processing: Must be <1ms per symbol
# - Redis operations: Must be <10ms
# - Track metrics and log performance warnings

# CRITICAL: Flask Application Context (TickStock-Specific)
# Flask stores application state in current_app context at RUNTIME
# Don't assume module-level globals are accessible in routes
# PATTERN: Use `from flask import current_app` then `getattr(current_app, 'attr_name')`
# Example: redis_subscriber = getattr(current_app, 'redis_subscriber', None)

# CRITICAL: Cross-Reference Working Features
# Before implementing, find similar WORKING feature and follow its pattern
# Example: If adding Redis to endpoint, check how streaming_routes.py accesses Redis
# File: src/api/streaming_routes.py line 43-44 shows the pattern
# Pattern: redis_subscriber = getattr(current_app, 'redis_subscriber', None)
#         current_redis_client = redis_subscriber.redis_client if redis_subscriber else None

# CRITICAL: Global Variable Declaration in main()
# If main() assigns to module-level variables, must declare them as global
# Example: main() must have `global app, socketio, redis_client` before assignments
# Without this, assignments create LOCAL variables, module-level stays None
# Location: src/app.py line 2102 - check for complete global declaration
```

## Implementation Blueprint

### Data models and structure

Create the core data models, we ensure type safety and consistency.

```python
Examples:
 - orm models
 - pydantic models
 - pydantic schemas
 - pydantic validators

```

### Implementation Tasks (ordered by dependencies)

**NOTE**: These are TickStock-specific task examples. Customize based on your feature's actual requirements.

```yaml
# Example 1: Adding a new Redis event subscriber
Task 1: CREATE src/core/services/{feature}_subscriber.py
  - IMPLEMENT: Redis pub-sub subscriber for new event type
  - FOLLOW pattern: src/core/services/processing_event_subscriber.py (event handling, message parsing)
  - NAMING: {Feature}Subscriber class, handle_{event_type} methods
  - REDIS CHANNELS: Subscribe to tickstock:{domain}:* pattern
  - PLACEMENT: Core services layer in src/core/services/
  - GOTCHA: Convert typed events to dicts at Worker boundary

Task 2: MODIFY src/core/services/websocket_broadcaster.py
  - INTEGRATE: Add new event type to WebSocket broadcast logic
  - FOLLOW pattern: Existing event handlers in same file
  - NAMING: broadcast_{event_type}(data: dict) method
  - DEPENDENCIES: Consume events from Task 1 subscriber
  - PERFORMANCE: Ensure <100ms delivery to browser

Task 3: CREATE tests/integration/test_{feature}_flow.py
  - IMPLEMENT: End-to-end test for Redis → WebSocket flow
  - FOLLOW pattern: tests/integration/test_pattern_flow_complete.py
  - TEST COVERAGE: Redis event receipt, message parsing, WebSocket delivery
  - MOCK: Redis pub-sub using fakeredis
  - ASSERTIONS: Message format, delivery timing, error handling

# Example 2: Adding a new REST API endpoint
Task 1: CREATE src/api/rest/{feature}.py
  - IMPLEMENT: Flask Blueprint with new endpoint
  - FOLLOW pattern: src/api/rest/tier_patterns.py (route structure, auth decorators)
  - NAMING: {feature}_bp Blueprint, snake_case route functions
  - DATABASE: Read-only queries via connection_pool.get_connection()
  - PLACEMENT: API layer in src/api/rest/

Task 2: MODIFY src/api/rest/main.py
  - INTEGRATE: Register new Blueprint with Flask app
  - FIND pattern: Existing blueprint registrations (app.register_blueprint)
  - ADD: Import and register new blueprint with url_prefix
  - PRESERVE: Existing route registrations

Task 3: CREATE src/core/services/{feature}_service.py (if complex logic)
  - IMPLEMENT: Business logic layer for feature
  - FOLLOW pattern: src/core/services/universe_service.py (service structure)
  - NAMING: {Feature}Service class, get_*, process_*, validate_* methods
  - DATABASE ACCESS: Read-only mode (SELECT only, no writes)
  - DEPENDENCIES: Use connection_pool for database queries

Task 4: CREATE tests/api/rest/test_{feature}.py
  - IMPLEMENT: Unit tests for API endpoint
  - FOLLOW pattern: tests/api/rest/test_tickstockpl_api_refactor.py
  - TEST COVERAGE: Happy path, error cases, auth validation
  - MOCK: Database connections, external dependencies
  - ASSERTIONS: Response status codes, JSON structure, error messages

# Example 3: Adding a new WebSocket event type
Task 1: MODIFY src/presentation/websocket/manager.py
  - IMPLEMENT: New event handler for WebSocket client messages
  - FOLLOW pattern: Existing SocketIO event handlers
  - NAMING: on_{event_name}(data: dict) decorated with @socketio.on
  - ROOM MANAGEMENT: Join/leave rooms based on symbol subscriptions
  - PLACEMENT: WebSocket management layer

Task 2: MODIFY src/core/services/websocket_subscription_manager.py
  - INTEGRATE: Add subscription tracking for new event type
  - FOLLOW pattern: Existing subscription management methods
  - NAMING: subscribe_{resource}(symbol: str, session_id: str)
  - DATABASE: Track subscriptions in ws_subscriptions table
  - CLEANUP: Ensure subscriptions removed on disconnect

Task 3: CREATE tests/integration/test_{feature}_websocket.py
  - IMPLEMENT: WebSocket connection and event flow tests
  - FOLLOW pattern: tests/integration/test_websocket_patterns.py
  - TEST COVERAGE: Connection, subscription, message delivery, disconnection
  - MOCK: Redis events, database queries
  - ASSERTIONS: Room membership, message routing, cleanup

# Example 4: Adding database migration
Task 1: CREATE src/infrastructure/database/migrations/migration_{version}_{description}.sql
  - IMPLEMENT: SQL migration script for schema changes
  - FOLLOW pattern: Existing migration files in migrations/
  - NAMING: migration_{timestamp}_{snake_case_description}.sql
  - INCLUDE: Both UP (apply) and DOWN (rollback) sections
  - VALIDATION: Test on local database before committing

Task 2: UPDATE src/infrastructure/database/migrations/run_migrations.py
  - INTEGRATE: Register new migration in migration runner
  - FOLLOW pattern: Existing migration registrations
  - VERSION: Increment version number sequentially
  - ROLLBACK: Ensure down migration works correctly

Task 3: CREATE tests/integration/test_migration_{description}.py
  - IMPLEMENT: Migration validation tests
  - TEST COVERAGE: Schema changes applied, data integrity, rollback works
  - ASSERTIONS: Table structure, indexes, constraints
```

### Implementation Patterns & Key Details

```python
# TickStock-Specific Implementation Patterns
# Keep concise, focus on non-obvious details

# Pattern 1: Flask REST API Endpoint
# File: src/api/rest/{feature}.py
from flask import Blueprint, jsonify, request
from src.utils.auth_decorators import login_required

{feature}_bp = Blueprint('{feature}', __name__)

@{feature}_bp.route('/api/{resource}', methods=['GET'])
@login_required
def get_{resource}():
    # PATTERN: Always use read-only database access
    # GOTCHA: Use connection_pool.get_connection() for queries
    # CRITICAL: Close connections in finally block

    conn = None
    try:
        from src.infrastructure.database.connection_pool import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        # PATTERN: Explicit column lists (no SELECT *)
        cursor.execute("SELECT col1, col2 FROM table WHERE condition = %s", (param,))
        results = cursor.fetchall()

        return jsonify({"status": "success", "data": results})

    except Exception as e:
        # PATTERN: Log and return structured error
        logger.error(f"Error in get_{resource}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if conn:
            conn.close()

# REGISTER in src/api/rest/main.py:
# from src.api.rest.{feature} import {feature}_bp
# app.register_blueprint({feature}_bp)


# Pattern 2: Redis Event Subscriber
# File: src/core/services/{feature}_subscriber.py
import redis
import json
from typing import Callable

class {Feature}Subscriber:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.pubsub = redis_client.pubsub()

    def subscribe(self, callback: Callable):
        # PATTERN: Subscribe to channel pattern
        self.pubsub.psubscribe('tickstock:{domain}:*')

        for message in self.pubsub.listen():
            if message['type'] == 'pmessage':
                # CRITICAL: Always parse and validate JSON
                try:
                    data = json.loads(message['data'])
                    # GOTCHA: Convert typed events to dicts here
                    event_dict = dict(data) if not isinstance(data, dict) else data
                    callback(event_dict)
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"Error parsing message: {e}")


# Pattern 3: WebSocket Broadcaster
# File: src/core/services/websocket_broadcaster.py (modify existing)
from flask_socketio import emit

def broadcast_{event_type}(data: dict, room: str = None):
    # PATTERN: Always use dict for WebSocket messages
    # PERFORMANCE: Target <100ms delivery
    # GOTCHA: Use broadcast=True for multi-client delivery

    message = {
        "type": "{event_type}",
        "timestamp": time.time(),
        "data": data
    }

    if room:
        emit('{event_type}', message, room=room, broadcast=True)
    else:
        emit('{event_type}', message, broadcast=True)


# Pattern 4: Database Query Service
# File: src/core/services/{feature}_service.py
class {Feature}Service:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_{resource}(self, filters: dict) -> list:
        # PATTERN: Service layer handles business logic
        # CRITICAL: Always use read-only queries for pattern data
        # PERFORMANCE: Target <50ms query time

        conn = None
        try:
            from src.infrastructure.database.connection_pool import get_connection
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # PATTERN: Parameterized queries (prevent SQL injection)
            query = """
                SELECT col1, col2, col3
                FROM table
                WHERE condition = %s
                LIMIT 100
            """
            cursor.execute(query, (filters.get('param'),))
            results = cursor.fetchall()

            return [dict(row) for row in results]

        finally:
            if conn:
                conn.close()


# Pattern 5: WebSocket Event Handler
# File: src/presentation/websocket/manager.py (modify existing)
from flask_socketio import join_room, leave_room

@socketio.on('subscribe_{resource}')
def handle_subscribe_{resource}(data):
    # PATTERN: Room-based subscriptions for symbol filtering
    # CRITICAL: Track subscriptions in database
    # GOTCHA: Clean up on disconnect

    symbol = data.get('symbol')
    session_id = request.sid

    if symbol:
        room = f"{resource}:{symbol}"
        join_room(room)

        # Track subscription in database
        from src.core.services.websocket_subscription_manager import track_subscription
        track_subscription(session_id, symbol, '{resource}')

        emit('subscribed', {'symbol': symbol, 'type': '{resource}'})
```

### Integration Points

```yaml
# TickStock-Specific Integration Points

DATABASE:
  # Migration example
  - migration_file: "src/infrastructure/database/migrations/migration_044_{description}.sql"
  - migration_content: |
      -- UP
      ALTER TABLE table_name ADD COLUMN new_column VARCHAR(100);
      CREATE INDEX idx_{table}_{column} ON table_name(new_column);
      -- DOWN
      DROP INDEX IF EXISTS idx_{table}_{column};
      ALTER TABLE table_name DROP COLUMN IF EXISTS new_column;

  # Query patterns to add
  - query_location: "src/core/services/{feature}_service.py"
  - query_example: "SELECT col1, col2 FROM table WHERE condition = %s LIMIT 100"
  - performance: "<50ms query time (verify with EXPLAIN ANALYZE)"

REDIS_CHANNELS:
  # New channel subscriptions
  - subscribe_in: "src/core/services/{feature}_subscriber.py"
  - channel_pattern: "tickstock:{domain}:*"
  - message_format: "{key1: value1, key2: value2, timestamp: int}"

  # New channel publishing (if TickStockPL integration)
  - publish_from: "TickStockPL (external component)"
  - channel_name: "tickstock:{domain}:{event_type}"
  - consumption: "TickStockAppV2 subscribes and broadcasts via WebSocket"

WEBSOCKET:
  # New event types
  - event_handler: "src/presentation/websocket/manager.py"
  - event_name: "{event_type}"
  - decorator: "@socketio.on('{event_type}')"
  - room_pattern: "{resource}:{symbol}"

  # Broadcast integration
  - broadcaster: "src/core/services/websocket_broadcaster.py"
  - broadcast_method: "broadcast_{event_type}(data: dict, room: str)"
  - latency_target: "<100ms end-to-end"

FLASK_BLUEPRINTS:
  # REST API routes
  - blueprint_file: "src/api/rest/{feature}.py"
  - blueprint_name: "{feature}_bp"
  - register_in: "src/api/rest/main.py"
  - registration_pattern: |
      from src.api.rest.{feature} import {feature}_bp
      app.register_blueprint({feature}_bp)

CONFIG:
  # Environment variables
  - add_to: ".env"
  - variables: |
      {FEATURE}_ENABLED=true
      {FEATURE}_TIMEOUT=30
      REDIS_{FEATURE}_CHANNEL=tickstock:{domain}:events

  # Config file updates
  - config_file: "src/config/redis_config.py"
  - pattern: "Add new channel constants to REDIS_CHANNELS dict"

TICKSTOCKPL_API:
  # HTTP endpoints (if triggering TickStockPL jobs)
  - api_client: "src/core/services/tickstockpl_api_client.py"
  - endpoint: "http://localhost:8080/api/v1/{resource}"
  - method: "POST"
  - payload: "{param1: value1, param2: value2}"
  - response_handling: "Async job trigger, monitor via Redis events"

STARTUP:
  # Service initialization
  - startup_file: "src/core/services/startup_service.py"
  - initialization: "Add {feature}_subscriber.start() to startup sequence"
  - health_check: "Verify Redis connection and channel subscription"
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# Run after each file creation - fix before proceeding

# File-specific validation
ruff check src/{new_files} --fix     # Auto-format and fix linting issues
ruff format src/{new_files}          # Ensure consistent formatting

# Project-wide validation
ruff check src/ --fix
ruff format src/

# Expected: Zero errors. If errors exist, READ output and fix before proceeding.
# Note: TickStock does not use mypy - rely on runtime type checking and tests
```

### Level 2: Unit Tests (Component Validation)

```bash
# TickStock Standard: pytest for all testing
# Test each component as it's created

# Unit tests for specific modules
python -m pytest tests/unit/test_{module}.py -v

# Full unit test suite
python -m pytest tests/unit/ -v

# Coverage validation (if needed)
python -m pytest tests/unit/ --cov=src --cov-report=term-missing

# Expected: All tests pass. If failing, debug root cause and fix implementation.
# TickStock Standard: Aim for >80% coverage on business logic
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

# Primary integration test runner
python run_tests.py

# Alternative detailed runner
python tests/integration/run_integration_tests.py

# Expected Output:
# - 2+ tests passing
# - ~30 second runtime
# - Pattern flow tests passing
# - Core integration may fail if services not running (acceptable in dev)

# NOTE: RLock warning can be ignored (known asyncio quirk)

# Service startup validation (if testing full stack)
python start_all_services.py &
sleep 5  # Allow services to initialize

# Health check validation
curl -f http://localhost:5000/health || echo "TickStockAppV2 health check failed"
curl -f http://localhost:8080/health || echo "TickStockPL health check failed"

# Database connection validation
PGPASSWORD=your_password psql -U app_readwrite -d tickstock -c "SELECT 1;" || echo "Database connection failed"

# Redis connection validation
redis-cli ping || echo "Redis connection failed"

# Expected: All services healthy, connections established
```

### Level 4: TickStock-Specific Validation

```bash
# Architecture Compliance Validation
# CRITICAL: Run architecture-validation-specialist agent if:
# - Modifying Redis pub-sub patterns
# - Adding database queries
# - Changing component roles (Consumer/Producer)

# Security Validation (if security-related changes)
# CRITICAL: Run code-security-specialist agent
# - No hardcoded credentials
# - Proper error handling
# - Input validation present

# Performance Benchmarking
# Verify performance targets are met:

# Symbol processing speed (if applicable)
# Target: <1ms per symbol
# Measure: Add timing logs and verify in output

# WebSocket delivery latency (if applicable)
# Target: <100ms end-to-end
# Test: Monitor browser DevTools Network tab for WebSocket latency

# Redis operation latency (if applicable)
# Target: <10ms
# Measure: Check Redis logs or add timing instrumentation

# Database query performance (if applicable)
# Target: <50ms per query
# Test: EXPLAIN ANALYZE queries in psql

# Redis Channel Monitoring (if Redis pub-sub changes)
python scripts/diagnostics/monitor_redis_channels.py
# Expected: See messages flowing on relevant channels
# Channels to verify:
#   - tickstock:patterns:streaming
#   - tickstock:indicators:streaming
#   - tickstock:market:ticks

# WebSocket Broadcast Testing (if WebSocket changes)
# 1. Start services
# 2. Open http://localhost:5000/streaming in browser
# 3. Verify real-time updates appear
# 4. Check DevTools Console for WebSocket connection status

# Database Read-Only Enforcement (if database changes in TickStockAppV2)
# CRITICAL: Verify no INSERT, UPDATE, DELETE statements for pattern data
# Allowed writes: user_sessions, ws_subscriptions, error_logs
grep -r "INSERT INTO daily_patterns\|UPDATE daily_patterns\|DELETE FROM daily_patterns" src/
# Expected: No matches (pattern writes belong in TickStockPL)

# Agent Execution Validation
# Run domain-specific specialist agents as needed:
# - tickstock-test-specialist: For test coverage validation
# - redis-integration-specialist: For Redis pub-sub changes
# - integration-testing-specialist: MANDATORY at end of implementation
# - database-query-specialist: For database query optimization
# - error-handling-specialist: For error handling validation

# Expected: All validations pass, no architectural violations detected
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No linting errors: `ruff check src/`
- [ ] No formatting issues: `ruff format src/ --check`
- [ ] Unit tests pass: `python -m pytest tests/unit/ -v`

### Feature Validation

- [ ] All success criteria from "What" section met
- [ ] Manual testing successful: [specific commands from Level 3]
- [ ] Error cases handled gracefully with proper error messages
- [ ] Integration points work as specified
- [ ] User persona requirements satisfied (if applicable)

### TickStock Architecture Validation

- [ ] Component role respected (Consumer vs Producer)
- [ ] Redis pub-sub channels used correctly (no direct pattern table queries in AppV2)
- [ ] Database access mode followed (read-only enforcement where applicable)
- [ ] WebSocket latency target met (<100ms end-to-end)
- [ ] Performance targets achieved (see TickStock Architecture Context section)
- [ ] No architectural violations detected by architecture-validation-specialist

### Code Quality Validation

- [ ] Follows existing codebase patterns and naming conventions
- [ ] File placement matches desired codebase tree structure
- [ ] Anti-patterns avoided (check against Anti-Patterns section below)
- [ ] Dependencies properly managed and imported
- [ ] Configuration changes properly integrated
- [ ] Code structure limits followed (max 500 lines/file, 50 lines/function)
- [ ] Naming conventions: snake_case functions, PascalCase classes, UPPER_SNAKE_CASE constants

### Documentation & Deployment

- [ ] Code is self-documenting with clear variable/function names
- [ ] Logs are informative but not verbose
- [ ] Environment variables documented if new ones added
- [ ] No "Generated by Claude" comments in code or commits

---

## Anti-Patterns to Avoid

### Generic Anti-Patterns
- ❌ Don't create new patterns when existing ones work
- ❌ Don't skip validation because "it should work"
- ❌ Don't ignore failing tests - fix them
- ❌ Don't use sync functions in async context
- ❌ Don't hardcode values that should be config
- ❌ Don't catch all exceptions - be specific

### TickStock-Specific Anti-Patterns (CRITICAL)

#### Architecture Violations
- ❌ **Don't mix TickStockApp and TickStockPL roles**
  - AppV2 = Consumer (reads from Redis, queries DB read-only)
  - PL = Producer (writes to Redis, writes to DB)
  - Violation: Adding pattern detection logic to AppV2

- ❌ **Don't create OHLCV aggregation in TickStockAppV2**
  - OHLCV aggregation belongs exclusively in TickStockPL (TickAggregator)
  - Sprint 42 removed this code - don't re-introduce it

- ❌ **Don't query pattern tables directly in TickStockAppV2**
  - Pattern data comes via Redis pub-sub from TickStockPL
  - Exception: Dashboard historical queries are acceptable (read-only)
  - Violation: `SELECT FROM daily_patterns` in real-time processing

- ❌ **Don't use database writes for pattern data in AppV2**
  - Pattern/indicator data writes belong in TickStockPL
  - Allowed writes in AppV2: user_sessions, ws_subscriptions, error_logs
  - Violation: `INSERT INTO daily_patterns` from AppV2

#### Data Handling
- ❌ **Don't mix typed events and dicts after Worker boundary**
  - Always convert to dict when crossing process boundaries
  - Violation: Passing TypedDict across multiprocessing Worker

- ❌ **Don't hardcode bar count minimums globally**
  - Use pattern-specific requirements (Sprint 43 lesson)
  - Single-bar patterns: detect at bar 1
  - Multi-bar patterns: detect at bar 2+
  - Violation: Blanket 5-bar minimum delay

#### Performance
- ❌ **Don't create blocking operations in WebSocket path**
  - Target: <100ms end-to-end delivery
  - Use async operations, batch updates
  - Violation: Synchronous database query before WebSocket emit

- ❌ **Don't skip performance benchmarking**
  - Symbol processing: <1ms
  - Redis operations: <10ms
  - Database queries: <50ms
  - Violation: Adding unbounded loops in hot path

#### Testing & Validation
- ❌ **Don't skip integration tests before commits**
  - `python run_tests.py` is MANDATORY
  - Violation: Committing without running tests

- ❌ **Don't create mock/stub endpoints in production code**
  - Remove ALL mock data before deployment
  - Violation: Hardcoded pattern arrays in API endpoints

#### Code Quality
- ❌ **Don't exceed structure limits**
  - Max 500 lines per file
  - Max 50 lines per function
  - Max complexity <10
  - Violation: 800-line service class

- ❌ **Don't add "Generated by Claude" to code or commits**
  - Keep code and commits clean
  - Violation: Comments like "# Generated with Claude Code"