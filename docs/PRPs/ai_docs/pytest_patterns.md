# pytest_patterns.md - TickStock Testing Pattern Library

**Version**: 1.0.0
**Last Updated**: January 2025
**Evidence**: 147 test files, 715 fixture occurrences
**Sprint Lesson**: Sprint 40/43 fixture failures caused cascading test breakage

---

## Overview

This pattern library documents TickStock's pytest testing patterns to prevent **test suite explosion** where fixing one test breaks 10 others. Focuses on fixture hierarchy management, mocking strategies, and integration test patterns that maintain the 30-second runtime target.

**When to Use This Library**:
- ✅ Creating new test files
- ✅ Debugging fixture-related test failures
- ✅ Deciding between mock vs real dependencies
- ✅ Writing integration tests
- ✅ Sprint retrospectives (test failures)

---

## Pattern 1: Fixture Hierarchy Pattern

**Problem**: Fixture dependency chains break when one fixture fails, causing cascading test suite breakage (Sprint 40/43).

**Solution**: Use explicit fixture scopes and dependency injection to create stable, predictable test environments.

### Fixture Scope Levels

```python
# Session scope - Created ONCE for entire test session
@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings - shared across all tests"""
    return {
        "TESTING": True,
        "DATABASE_URI": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/15",  # Test database
        "USE_SIMULATED_DATA": True,
        "LOG_LEVEL": "DEBUG"
    }

# Module scope - Created ONCE per test file
@pytest.fixture(scope="module")
def database_connection():
    """Database connection - shared across tests in one file"""
    conn = create_connection()
    yield conn
    conn.close()

# Function scope (default) - Created for EACH test function
@pytest.fixture
def mock_tick():
    """Fresh mock tick for each test"""
    return MockTick.create()
```

**Scope Decision Matrix**:

| Scope | Use When | Example | Pros | Cons |
|-------|----------|---------|------|------|
| `session` | Immutable config, expensive setup | test_config | Fast, shared | Can't modify |
| `module` | File-level shared state | DB connection | Fewer setups | State leaks |
| `function` | Test isolation needed | mock_tick | Clean slate | Slower |

### Dependency Chains

**Reference**: `tests/conftest.py:63-106`

```python
# PATTERN: Explicit fixture dependencies via parameters
@pytest.fixture
def app():
    """Create Flask application for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app

@pytest.fixture
def client(app):  # ← Depends on 'app' fixture
    """Create Flask test client."""
    return app.test_client()

# Usage in test
def test_api_endpoint(client):  # ← Gets 'client', which auto-gets 'app'
    response = client.get('/api/test')
    assert response.status_code == 200
```

**Dependency Chain Visualization**:
```
test_config (session)
    ↓
setup_test_environment (autouse, function) ← Sets env vars
    ↓
app (function) ← Creates Flask app with test config
    ↓
client (function) ← Creates test client from app
    ↓
test_api_endpoint() ← Uses client
```

### Teardown/Cleanup Patterns

**Reference**: `tests/conftest.py:503-514`

```python
# PATTERN 1: yield for teardown (recommended)
@pytest.fixture
def redis_client():
    """Test Redis client with automatic cleanup"""
    client = redis.Redis(host='localhost', port=6379, db=15)  # Test DB
    yield client
    # Cleanup after test
    client.flushdb()  # Clear test data
    client.close()

# PATTERN 2: finalizer for complex cleanup
@pytest.fixture
def temp_trace_file(request):
    """Temporary trace file with cleanup"""
    temp_file = create_temp_file()

    def cleanup():
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    request.addfinalizer(cleanup)
    return temp_file

# PATTERN 3: autouse fixture for environment setup
@pytest.fixture(autouse=True)
def setup_test_environment(test_config):
    """Automatically set up test environment for ALL tests"""
    # Setup
    for key, value in test_config.items():
        os.environ[key] = str(value)

    yield

    # Teardown
    for key in test_config.keys():
        os.environ.pop(key, None)
```

**Cleanup Best Practices**:
- ✅ **Always** clean up external resources (Redis, files, connections)
- ✅ Use `yield` for simple cleanup (most common)
- ✅ Use `finalizer` when cleanup must happen even if test fails
- ✅ Use `autouse=True` for environment-wide setup
- ❌ **Never** leave test data in shared resources (Redis DB 0, production DB)

### Gotcha: Fixture Dependency Cycles

**ANTI-PATTERN** ❌:
```python
@pytest.fixture
def service_a(service_b):
    return ServiceA(service_b)

@pytest.fixture
def service_b(service_a):  # ← Circular dependency!
    return ServiceB(service_a)
```

**CORRECT PATTERN** ✅:
```python
# Break cycle by using factory pattern
@pytest.fixture
def service_factory():
    def _create_service(dep):
        return Service(dep)
    return _create_service

def test_service_integration(service_factory):
    service_a = service_factory(None)
    service_b = service_factory(service_a)
    # Test interaction
```

---

## Pattern 2: Mock Strategy Pattern

**Problem**: Unclear when to use real vs mock dependencies causes slow tests and flaky failures.

**Solution**: Use **real dependencies for integration tests**, **mocks for unit tests**, and **never mock what you don't own**.

### Decision Matrix: Mock vs Real

| Component | Unit Tests | Integration Tests | Reason |
|-----------|------------|-------------------|--------|
| Redis | Mock (`mock_redis`) | Real (DB 15) | Integration tests validate pub-sub flow |
| Database | Mock (`mock_database`) | Real (test schema) | Integration tests validate queries |
| WebSocket | Mock (`mock_websocket_manager`) | Real (SocketIO test client) | Integration tests validate broadcast |
| Massive API | **Always mock** | **Always mock** | External, rate-limited, costs money |
| Time (`time.time()`) | Mock (freeze time) | Real | Unit tests need deterministic time |

### Mock Fixtures

**Reference**: `tests/conftest.py:456-487`

```python
# PATTERN 1: Mock with unittest.mock.Mock
@pytest.fixture
def mock_database():
    """Mock database connection for unit testing"""
    db_mock = Mock()
    db_mock.execute.return_value = Mock()
    db_mock.fetchall.return_value = []
    db_mock.fetchone.return_value = None
    db_mock.commit.return_value = None
    db_mock.rollback.return_value = None
    return db_mock

# Usage in test
def test_query_error_handling(mock_database):
    mock_database.execute.side_effect = Exception("Connection lost")

    with pytest.raises(Exception, match="Connection lost"):
        service = DatabaseService(mock_database)
        service.query("SELECT * FROM symbols")
```

```python
# PATTERN 2: Mock Redis for unit tests
@pytest.fixture
def mock_redis():
    """Mock Redis connection for unit testing"""
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    redis_mock.expire.return_value = True

    # Mock publish (for event testing)
    redis_mock.publish.return_value = 1  # Number of subscribers

    return redis_mock

# Usage
def test_pattern_caching(mock_redis):
    cache = PatternCache(mock_redis)
    cache.set_pattern('AAPL', 'Doji', {'confidence': 0.85})

    mock_redis.set.assert_called_once_with(
        'tickstock:patterns:AAPL:Doji',
        json.dumps({'confidence': 0.85}),
        ex=300
    )
```

### Real Dependencies for Integration Tests

**Reference**: `tests/integration/test_pattern_flow_complete.py:32-54`

```python
class TestPatternFlowComplete:
    """Integration test using REAL Redis and Database"""

    def __init__(self):
        # Real Redis on test database
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=15,  # ← Test DB (not production DB 0)
            decode_responses=True
        )

        # Real database connection
        self.db_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='tickstock_test',  # ← Test database
            user='test_user',
            password='test_password'
        )
        self.db_conn.autocommit = True
```

**Why Real Dependencies?**
- ✅ Validates actual Redis pub-sub behavior
- ✅ Tests real database query performance
- ✅ Catches serialization/deserialization bugs
- ✅ Ensures configuration is correct

### Mocking External APIs

**Reference**: `docs/guides/testing.md:312-317`

```python
# ALWAYS mock external APIs (Massive, external services)
@mock.patch('src.data.massive_client.MassiveClient')
def test_with_mocked_massive(mock_massive):
    """Test without hitting real Massive API"""
    # Set up mock response
    mock_massive.get_ticker.return_value = {
        'ticker': 'AAPL',
        'name': 'Apple Inc.',
        'market': 'stocks',
        'last_price': 150.25
    }

    # Test service that uses Massive
    service = MarketDataService(mock_massive)
    ticker_info = service.get_ticker_info('AAPL')

    assert ticker_info['ticker'] == 'AAPL'
    mock_massive.get_ticker.assert_called_once_with('AAPL')
```

### Gotcha: Never Mock What You Don't Own

**ANTI-PATTERN** ❌:
```python
# DON'T mock third-party library internals
@mock.patch('redis.Redis.connection_pool')
def test_redis_connection(mock_pool):
    # This is testing Redis internals, not your code!
    pass
```

**CORRECT PATTERN** ✅:
```python
# Mock YOUR interface to Redis
@pytest.fixture
def mock_redis_client():
    """Mock your Redis client wrapper"""
    mock = Mock(spec=RedisClient)  # ← Your wrapper class
    mock.get_pattern.return_value = {'confidence': 0.85}
    return mock

def test_pattern_retrieval(mock_redis_client):
    service = PatternService(mock_redis_client)
    pattern = service.get_pattern('AAPL', 'Doji')
    assert pattern['confidence'] == 0.85
```

---

## Pattern 3: Integration Test Pattern

**Problem**: Integration tests are slow, flaky, or break when services aren't running.

**Solution**: Use real dependencies, implement proper cleanup, and target 30-second runtime for the full suite.

### Integration Test Structure

**Reference**: `tests/integration/test_pattern_flow_complete.py:307-351`

```python
class TestPatternFlowComplete:
    """Integration test class structure"""

    def __init__(self):
        # 1. Initialize REAL dependencies
        self.redis_client = redis.Redis(host='localhost', port=6379, db=15)
        self.db_conn = psycopg2.connect(...)
        self.db_conn.autocommit = True

    def test_pattern_with_numpy_data(self):
        """Test single scenario with real data"""
        flow_id = str(uuid.uuid4())

        # 2. Setup: Create test data
        pattern_event = {
            'event_type': 'pattern_detected',
            'source': 'TickStockPL',
            'flow_id': flow_id,
            'data': {...}
        }

        # 3. Execute: Trigger real system
        self.redis_client.publish(
            'tickstock.events.patterns',
            json.dumps(pattern_event)
        )

        # 4. Verify: Check real results
        time.sleep(0.1)  # Allow async processing
        assert self.verify_pattern_received(flow_id)

        return flow_id

    def cleanup(self):
        """5. Teardown: Clean up connections"""
        self.redis_client.flushdb()  # Clear test data
        self.redis_client.close()
        self.db_conn.close()

# Main runner function
def run_pattern_flow_tests():
    """Run complete pattern flow tests."""
    test = TestPatternFlowComplete()

    try:
        # Run test scenarios
        test.test_pattern_with_numpy_data()
        test.test_multi_tier_patterns()
        return True

    except Exception as e:
        print(f"Test failed: {e}")
        return False

    finally:
        test.cleanup()  # ← ALWAYS cleanup
```

### Performance Target: 30-Second Runtime

**Reference**: `docs/guides/testing.md:389-391`

**Current Status** (CLAUDE.md):
```bash
python run_tests.py
# Expected: 2 tests total
# Expected runtime: ~30 seconds
# Tests: Core Integration, Pattern Flow
```

**Performance Best Practices**:
- ✅ **Parallel test execution**: Use `pytest -n auto` (requires `pytest-xdist`)
- ✅ **Test data reuse**: Use session-scoped fixtures for expensive setup
- ✅ **Avoid `time.sleep()`**: Use polling with timeouts instead
- ✅ **Database cleanup**: Truncate tables, don't recreate schema
- ❌ **Don't wait unnecessarily**: 3-second waits add up fast

```python
# ANTI-PATTERN: Fixed sleep
def test_async_processing():
    publish_event(event)
    time.sleep(5)  # ← Wastes 5 seconds even if processing takes 0.1s
    assert check_result()

# CORRECT PATTERN: Poll with timeout
def test_async_processing():
    publish_event(event)

    # Poll for result with 5s timeout
    for _ in range(50):  # 50 * 0.1s = 5s max
        if check_result():
            return  # ✅ Exit early on success
        time.sleep(0.1)

    pytest.fail("Result not received within 5s")
```

### Integration Test Checklist

Before creating an integration test:
- [ ] Do I need real Redis? (If testing pub-sub flow → Yes)
- [ ] Do I need real Database? (If testing queries → Yes)
- [ ] Do I need real WebSocket? (If testing broadcast → Yes)
- [ ] Can I use test database (not production)? (Always → Yes)
- [ ] Do I clean up test data in `finally` block? (Always → Yes)
- [ ] Does the test run in <5 seconds? (Target → Yes)

### Gotcha: Test Isolation with Real Dependencies

**Problem**: Test data from previous test affects current test.

**Solution**: Clean up test data in Redis/Database between tests.

```python
# PATTERN: Cleanup in fixture with yield
@pytest.fixture
def clean_redis():
    """Redis client with automatic cleanup"""
    client = redis.Redis(host='localhost', port=6379, db=15)
    client.flushdb()  # Clean BEFORE test

    yield client

    client.flushdb()  # Clean AFTER test
    client.close()

# Usage
def test_pattern_caching(clean_redis):
    # Redis is clean at start
    assert clean_redis.keys('*') == []

    # Test logic...

    # Redis will be cleaned after this test
```

---

## Pattern 4: Test Coverage Gotchas

**Problem**: Chasing 100% coverage wastes time testing trivial code. Focus on high-value business logic.

**Solution**: Target >80% overall, >90% on critical paths, 100% on API endpoints and error handlers.

### Coverage Targets

**Reference**: `docs/guides/testing.md:382-386`

| Component | Target | Reason |
|-----------|--------|--------|
| Overall | >80% | Industry standard |
| Business Logic | >90% | Core value, high risk |
| API Endpoints | 100% | User-facing, must work |
| Error Handlers | 100% | Failure modes critical |
| Getters/Setters | 0-20% | Low value, low risk |
| Third-party wrappers | 50-70% | Integration points only |

### What NOT to Test

```python
# ❌ DON'T TEST: Simple getters/setters
class Symbol:
    def __init__(self, ticker):
        self._ticker = ticker

    @property
    def ticker(self):  # ← Don't test this
        return self._ticker

# ❌ DON'T TEST: Third-party library behavior
def test_redis_set_works():
    """Testing Redis library, not your code"""
    redis_client = redis.Redis()
    redis_client.set('key', 'value')
    assert redis_client.get('key') == 'value'  # ← This tests Redis, not you

# ❌ DON'T TEST: Configuration constants
def test_redis_channel_name():
    """Testing a string constant"""
    assert REDIS_PATTERN_CHANNEL == 'tickstock.events.patterns'
```

### What TO Test

```python
# ✅ TEST: Business logic with edge cases
@pytest.mark.parametrize("confidence,expected", [
    (0.79, False),  # Below threshold
    (0.80, True),   # At threshold
    (0.85, True),   # Above threshold
    (1.00, True),   # Maximum
    (0.00, False),  # Minimum
])
def test_pattern_confidence_threshold(confidence, expected):
    """Test pattern filtering logic"""
    pattern = {'confidence': confidence}
    result = should_publish_pattern(pattern)
    assert result == expected

# ✅ TEST: Error handling paths
def test_database_connection_failure(mock_database):
    """Test graceful handling of database failure"""
    mock_database.execute.side_effect = ConnectionError("Database unavailable")

    service = PatternService(mock_database)
    result = service.get_patterns('AAPL')

    # Should return empty list, not crash
    assert result == []
    # Should log error (verify logging)
    assert "Database unavailable" in caplog.text

# ✅ TEST: Integration between components
def test_redis_to_websocket_flow(redis_client, websocket_manager):
    """Test pattern flows from Redis to WebSocket"""
    # Publish pattern event
    redis_client.publish('tickstock.events.patterns', json.dumps({
        'pattern': 'Doji',
        'symbol': 'AAPL'
    }))

    # Verify WebSocket broadcast
    time.sleep(0.1)
    broadcasts = websocket_manager.get_broadcasts()
    assert len(broadcasts) == 1
    assert broadcasts[0]['pattern'] == 'Doji'
```

### Coverage Reporting

**Reference**: `docs/guides/testing.md:199-205`

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View coverage (opens browser)
open htmlcov/index.html

# Coverage with missing lines
pytest --cov=src --cov-report=term-missing

# Example output:
# Name                         Stmts   Miss  Cover   Missing
# ----------------------------------------------------------
# src/core/services/pattern_service.py    45      3    93%   12-14
# src/api/rest/patterns.py                 30      0   100%
# src/utils/helpers.py                     20     15    25%   5-20
```

### Gotcha: High Coverage ≠ Good Tests

**ANTI-PATTERN** ❌:
```python
# 100% line coverage, but tests nothing
def test_pattern_service():
    service = PatternService()
    service.get_pattern('AAPL', 'Doji')  # ← No assertions!
    # "Test" passes but validates nothing
```

**CORRECT PATTERN** ✅:
```python
# Test behavior, not just execution
def test_pattern_service():
    service = PatternService()
    pattern = service.get_pattern('AAPL', 'Doji')

    # Assert expected behavior
    assert pattern is not None
    assert pattern['symbol'] == 'AAPL'
    assert pattern['pattern'] == 'Doji'
    assert pattern['confidence'] >= 0.80
    assert 'timestamp' in pattern
```

---

## Quick Reference

### Fixture Scope Decision Tree
```
Is the fixture immutable (config, constants)?
  YES → scope="session"
  NO ↓

Is the fixture expensive to create (DB connection)?
  YES → scope="module"
  NO ↓

Does the fixture need isolation (mock objects)?
  YES → scope="function" (default)
```

### Mock vs Real Decision Tree
```
Is it an external API (Massive, third-party)?
  YES → ALWAYS mock
  NO ↓

Is it a unit test (testing single function)?
  YES → Mock dependencies
  NO ↓

Is it an integration test (testing flow)?
  YES → Use real dependencies (with test DB/Redis)
```

### Integration Test Checklist
- [ ] Uses real Redis on DB 15 (not DB 0)
- [ ] Uses real Database with test schema
- [ ] Cleans up data in `finally` block
- [ ] Runs in <5 seconds per test
- [ ] Targets 30-second runtime for full suite

### Coverage Priority
1. **100%**: API endpoints, error handlers
2. **>90%**: Business logic, critical paths
3. **>80%**: Overall codebase
4. **Skip**: Getters/setters, third-party library behavior

---

## References

### Documentation
- [`docs/guides/testing.md`](../../guides/testing.md) - Testing strategies and execution
- [`.claude/agents/integration-testing-specialist.md`](../../../.claude/agents/integration-testing-specialist.md) - Integration testing patterns
- [`CLAUDE.md`](../../../CLAUDE.md) - Testing requirements and current status

### Code Examples
- [`tests/conftest.py`](../../../tests/conftest.py) - Fixture hierarchy (628 lines)
- [`tests/integration/test_pattern_flow_complete.py`](../../../tests/integration/test_pattern_flow_complete.py) - Integration test example
- [`tests/integration/run_integration_tests.py`](../../../tests/integration/run_integration_tests.py) - Test runner

### Tools
- [pytest documentation](https://docs.pytest.org/en/stable/) - Official pytest docs
- [pytest-mock](https://pytest-mock.readthedocs.io/) - Mocking with pytest
- [pytest-cov](https://pytest-cov.readthedocs.io/) - Coverage reporting
- [pytest-xdist](https://pytest-xdist.readthedocs.io/) - Parallel test execution

---

**Pattern Library Status**: ✅ Active
**Next Review**: After Sprint 45 retrospective
**Maintainer**: Development Team
