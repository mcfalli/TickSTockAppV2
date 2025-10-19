  Based on codebase analysis by the architecture-validation-specialist, here are 7 pattern libraries in priority order:

  ---
  🔴 PRIORITY 1: pytest_patterns.md (CRITICAL)

  Why This First:
  - 147 test files across the codebase
  - 715 pytest fixture occurrences (most complex: conftest.py at 628 lines)
  - Sprint 40/43 lesson: Multiple test fixture failures caused cascading test suite breakage
  - ROI: Prevents "test suite explosion" where fixing one test breaks 10 others

  Patterns to Document:
  1. Fixture Hierarchy Pattern (conftest.py lines ~50-200)
    - Scope levels (function, class, module, session)
    - Dependency chains (mock_redis → app → client)
    - Teardown/cleanup patterns
  2. Mock Strategy Pattern (tests/integration/*)
    - When to mock vs real dependencies
    - unittest.mock.Mock vs pytest-mock
    - Redis/Database mocking best practices
  3. Parametrized Testing Pattern (tests/unit/*)
    - @pytest.mark.parametrize for pattern detection tests
    - Table-driven test data
    - Edge case coverage
  4. Integration Test Pattern (tests/integration/run_integration_tests.py)
    - 30-second runtime target
    - Redis event simulation
    - WebSocket connection testing
  5. Test Coverage Gotchas
    - TickStock target: >80% on business logic
    - What NOT to test (getters/setters, third-party libs)
    - Coverage reporting (pytest --cov)

  Reference Files:
  - tests/conftest.py (628 lines) - fixture hierarchy
  - tests/integration/test_pattern_flow_complete.py - integration patterns
  - tests/unit/test_health_monitor_refactor.py - mocking patterns

  Evidence from Codebase:
  # Test file count
  find tests/ -name "test_*.py" | wc -l  # 147 files

  # Fixture usage
  rg "@pytest.fixture" tests/ | wc -l  # 715 occurrences

  ---
  🔴 PRIORITY 2: database_patterns.md (HIGH)

  Why Second:
  - 48 files with database connections
  - Architecture-critical: Read-only constraint violations = role boundary breach
  - Sprint 42 lesson: OHLCV duplication removed due to read-only enforcement
  - Production risk: Connection leaks cause outages

  Patterns to Document:
  1. Connection Pool Pattern (src/infrastructure/database/connection_pool.py)
    - get_connection() usage
    - Connection lifecycle (acquire → use → release)
    - CRITICAL: ALWAYS close in finally block
    - Pool exhaustion debugging
  2. Read-Only Enforcement Pattern (TickStockAppV2 specific)
    - Allowed tables for writes: user_sessions, ws_subscriptions, error_logs
    - FORBIDDEN: Writes to daily_patterns, indicators, ohlcv_*
    - Consumer vs Producer role boundaries
    - Anti-pattern: INSERT INTO daily_patterns from AppV2
  3. Query Performance Pattern
    - Target: <50ms per query
    - Use EXPLAIN ANALYZE for optimization
    - Cursor factory: RealDictCursor for dict results
    - Explicit column lists (no SELECT *)
  4. Migration Pattern (src/infrastructure/database/migrations/)
    - UP/DOWN sections
    - Rollback testing
    - Version sequencing
  5. TimescaleDB-Specific Patterns
    - Hypertable queries (time-based partitioning)
    - Continuous aggregates
    - Retention policies

  Reference Files:
  - src/infrastructure/database/connection_pool.py - pool management
  - src/core/services/universe_service.py - query patterns
  - src/infrastructure/database/migrations/ - migration examples

  Gotchas:
  # ❌ WRONG: Connection leak
  conn = get_connection()
  cursor.execute("SELECT ...")
  # Exception → connection never closed

  # ✅ CORRECT: Always use finally
  conn = None
  try:
      conn = get_connection()
      cursor.execute("SELECT ...")
  finally:
      if conn:
          conn.close()

  ---
  🔴 PRIORITY 3: error_handling_patterns.md (HIGH)

  Why Third:
  - 1,727 try-except blocks across codebase
  - 2,121 logging statements (many without context)
  - Sprint 43 lesson: 3 debugging iterations due to swallowed exceptions in Redis subscriber
  - ROI: Reduces "invisible failures" debugging time by 50%+

  Patterns to Document:
  1. Structured Logging Pattern (TickStock standard)
    - Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - Contextual logging (include symbol, timeframe, event type)
    - Performance logging (track slow operations >50ms)
    - CRITICAL: Never log sensitive data (credentials, PII)
  2. Exception Hierarchy Pattern
    - Specific exceptions first (JSONDecodeError, KeyError)
    - Generic Exception catch-all last
    - ANTI-PATTERN: Bare except: swallows all errors
  3. Error Propagation Pattern
    - When to swallow (subscriber loops - keep alive)
    - When to re-raise (API endpoints - let Flask handle)
    - When to wrap (add context, convert to domain exception)
  4. Database Error Handling (Sprint 32 error management)
    - Connection errors → retry with backoff
    - Query errors → log + return error response
    - Transaction errors → rollback + cleanup
  5. Redis Error Handling Pattern
    - ConnectionError → reconnect with exponential backoff
    - TimeoutError → log as warning (not critical)
    - Message parsing errors → log + continue subscription
  6. Error Storage Pattern (error_logs table)
    - Severity thresholds (LOG_DB_SEVERITY_THRESHOLD=error)
    - Error context (stack traces, request data)
    - Error aggregation (prevent log spam)

  Reference Files:
  - src/core/services/redis_event_subscriber.py (lines 116-179) - subscriber error handling
  - src/api/rest/tier_patterns.py - API error responses
  - src/infrastructure/database/error_logger.py - database error storage

  Evidence:
  rg "try:" src/ | wc -l  # 1,727 try-except blocks
  rg "logger\.(error|warning|info|debug)" src/ | wc -l  # 2,121 log statements

  ---
  🟡 PRIORITY 4: configuration_patterns.md (MEDIUM)

  Why Fourth:
  - 94 environment variable references
  - Configuration drift between dev/prod causes issues
  - Security risk: Hardcoded credentials vs environment variables

  Patterns to Document:
  1. Environment Variable Pattern (.env + config_manager.py)
    - get_config() usage in services
    - Default values (os.getenv('VAR', 'default'))
    - Type conversion (strings → int, bool, list)
    - CRITICAL: Never commit .env to git
  2. Configuration Layers
    - Environment variables (highest priority)
    - Config files (config/*.py)
    - Defaults (fallback values)
  3. Redis Configuration Pattern
    - REDIS_URL format
    - Channel name constants (REDIS_PATTERN_CHANNEL, etc.)
    - Connection pool settings
  4. Feature Flag Pattern
    - TRACE_ENABLED, LOG_FILE_ENABLED
    - Runtime toggle patterns
    - Configuration validation
  5. Secrets Management
    - Database passwords in env vars only
    - API keys rotation
    - ANTI-PATTERN: Hardcoded credentials

  Reference Files:
  - src/core/services/config_manager.py - config service
  - src/config/redis_config.py - Redis config
  - .env.example - environment template

  ---
  🟡 PRIORITY 5: websocket_patterns.md (MEDIUM)

  Why Fifth:
  - WebSocket-specific gotchas not covered in flask_patterns.md
  - Sub-100ms latency requirement is complex
  - Sprint 43: Streaming buffer implementation (250ms flush)

  Patterns to Document:
  1. SocketIO Lifecycle Pattern
    - @socketio.on('connect') initialization
    - Room management (join/leave)
    - Session tracking (request.sid)
    - Disconnect cleanup
  2. Room-Based Subscription Pattern
    - Symbol-based rooms (patterns:{symbol})
    - Multi-room subscriptions
    - Broadcast scoping (emit(..., room=room))
  3. Performance Patterns
    - Buffered broadcasting (250ms flush interval)
    - Batch message delivery
    - Target: <100ms Redis → browser delivery
  4. Error Handling in WebSocket
    - Client disconnection handling
    - Message parsing errors
    - Reconnection logic (client-side)
  5. Testing WebSocket
    - SocketIO test client
    - Room membership verification
    - Message delivery assertions

  Reference Files:
  - src/presentation/websocket/manager.py - event handlers
  - src/core/services/websocket_broadcaster.py - broadcast patterns
  - tests/integration/test_websocket_patterns.py - testing

  Note: Some overlap with flask_patterns.md (SocketIO basics covered), but focus on TickStock-specific latency targets and buffering.

  ---
  🟢 PRIORITY 6: startup_patterns.md (LOW-MEDIUM)

  Why Sixth:
  - Service initialization order matters (causes Sprint 44's global variable issue)
  - Health check failures if startup incomplete
  - Only affects src/app.py and start_all_services.py

  Patterns to Document:
  1. Service Initialization Order
    - Config → Database → Redis → SocketIO → Subscribers
    - Dependency graph
    - CRITICAL: Global variable declaration in main()
  2. Flask Application Factory Pattern
    - create_app() vs inline initialization
    - Application context setup
    - Blueprint registration order
  3. Background Service Startup
    - Redis subscriber threads
    - Health monitor service
    - Cleanup on shutdown
  4. Graceful Shutdown Pattern
    - Signal handling (SIGTERM, SIGINT)
    - Resource cleanup
    - Connection pool drain

  Reference Files:
  - src/app.py (main function, lines ~2100-2200)
  - start_all_services.py - orchestration
  - src/core/services/startup_service.py - initialization logic

  ---
  🟢 PRIORITY 7: performance_patterns.md (LOW)

  Why Seventh:
  - Performance targets documented but patterns scattered
  - Measurement patterns inconsistent
  - Optimization patterns tribal knowledge

  Patterns to Document:
  1. Performance Measurement Pattern
    - Timing instrumentation (time.time() wrapper)
    - Performance logging thresholds
    - Metrics collection (Prometheus-style)
  2. Optimization Patterns
    - N+1 query elimination (batch queries)
    - Caching strategies (Redis, in-memory)
    - Connection pooling
  3. Performance Targets by Component
    - Symbol processing: <1ms
    - Redis operations: <10ms
    - Database queries: <50ms
    - WebSocket delivery: <100ms
    - API endpoints: <100ms
  4. Profiling Patterns
    - cProfile for CPU profiling
    - Memory profiling (tracemalloc)
    - Database query profiling (EXPLAIN ANALYZE)

  Reference Files:
  - src/core/services/health_monitor.py - performance measurement
  - Performance targets in CLAUDE.md

  ---
  Priority Summary

  | Priority | Pattern Library            | Evidence                        | Sprint Lesson                  | Impact                             |
  |----------|----------------------------|---------------------------------|--------------------------------|------------------------------------|
  | 🔴 1     | pytest_patterns.md         | 147 files, 715 fixtures         | Sprint 40/43 fixture issues    | Prevents test suite explosion      |
  | 🔴 2     | database_patterns.md       | 48 files, architecture-critical | Sprint 42 OHLCV duplication    | Prevents role violations + outages |
  | 🔴 3     | error_handling_patterns.md | 1,727 try blocks, 2,121 logs    | Sprint 43 swallowed exceptions | Reduces debugging iterations 50%   |
  | 🟡 4     | configuration_patterns.md  | 94 env vars                     | Config drift dev/prod          | Prevents credential leaks          |
  | 🟡 5     | websocket_patterns.md      | Sub-100ms latency target        | Sprint 43 buffering            | Specialized patterns for perf      |
  | 🟢 6     | startup_patterns.md        | Sprint 44 global var issue      | Service init order             | Low frequency but high impact      |
  | 🟢 7     | performance_patterns.md    | Scattered targets               | Tribal knowledge               | Nice-to-have consolidation         |

  ---
  Recommended Implementation Order

  Sprint 45 (Immediate):
  1. ✅ pytest_patterns.md - Highest ROI, prevents cascading test failures
  2. ✅ database_patterns.md - Architecture enforcement, production stability

  Sprint 46 (Next):
  3. ✅ error_handling_patterns.md - Reduces debugging time significantly
  4. ✅ configuration_patterns.md - Security + environment consistency

  Sprint 47 (Future):
  5. ✅ websocket_patterns.md - Specialized, less frequent use
  6. ✅ startup_patterns.md - Low frequency, but document Sprint 44 lesson
  7. ✅ performance_patterns.md - Consolidation, not urgent
