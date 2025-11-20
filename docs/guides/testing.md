# Testing Guide

**Version**: 3.0.0
**Last Updated**: September 26, 2025

## Overview

This guide covers testing strategies, test execution, and quality assurance for TickStockAppV2.

## Quick Start

### Run All Tests
```bash
# Recommended: Full test suite
python run_tests.py

# Alternative: Integration tests only
python tests/integration/run_integration_tests.py
```

### Test Specific Components
```bash
# Redis integration
python tests/integration/test_tickstockpl_integration.py

# Error handling
python tests/test_enhanced_error_handling.py

# Pattern flow
python tests/integration/test_pattern_flow_complete.py
```

## Test Structure

```
tests/
├── integration/           # End-to-end integration tests
│   ├── sprint*/          # Sprint-specific tests
│   └── test_*.py         # Component integration tests
├── unit/                 # Unit tests (if applicable)
├── fixtures/             # Test data and fixtures
└── conftest.py          # Pytest configuration
```

## Test Categories

### 1. Integration Tests
**Purpose**: Verify components work together correctly

```python
# Example: Redis pub-sub integration
def test_redis_pattern_consumption():
    """Test that AppV2 correctly consumes pattern events from Redis"""
    # Publish test pattern event
    redis_client.publish('tickstock.events.patterns', pattern_data)

    # Verify WebSocket broadcast
    assert websocket_received_event(pattern_data)

    # Verify UI update
    assert dashboard_shows_pattern(pattern_data)
```

**Key Test Files**:
- `test_tickstockpl_integration.py`: TickStockPL integration
- `test_phase3_redis_flows.py`: Redis message flows
- `test_pattern_flow_complete.py`: Pattern detection flow

### 2. API Tests
**Purpose**: Validate REST endpoints

```python
def test_pattern_discovery_api():
    """Test pattern discovery endpoint"""
    response = client.get('/api/pattern-discovery/patterns')
    assert response.status_code == 200
    assert response.json['cache_hit'] == True
    assert response.json['response_time_ms'] < 50
```

**Coverage Areas**:
- Authentication endpoints
- Pattern discovery API
- Admin endpoints
- Monitoring endpoints

### 3. WebSocket Tests
**Purpose**: Verify real-time communication

```python
def test_websocket_pattern_broadcast():
    """Test WebSocket broadcasts pattern events"""
    # Connect WebSocket client
    ws_client = socketio.test_client(app)

    # Trigger pattern event
    publish_pattern_event(test_pattern)

    # Verify broadcast
    received = ws_client.get_received()
    assert received[0]['name'] == 'pattern_detected'
    assert received[0]['args'][0]['symbol'] == 'AAPL'
```

### 4. Performance Tests
**Purpose**: Ensure performance targets are met

```python
def test_api_response_time():
    """Test API responds within target time"""
    start = time.time()
    response = client.get('/api/monitoring/metrics')
    duration = (time.time() - start) * 1000

    assert response.status_code == 200
    assert duration < 50  # Target: <50ms
```

**Performance Targets**:
- API Response: <50ms
- WebSocket Delivery: <100ms
- Redis Operation: <10ms
- Cache Hit Rate: >90%

### 5. Error Handling Tests
**Purpose**: Verify graceful error handling

```python
def test_database_connection_failure():
    """Test handling of database connection failure"""
    # Simulate database outage
    with mock_database_failure():
        response = client.get('/api/symbols')

        assert response.status_code == 503
        assert 'database' in response.json['error']
        assert redis_error_published()
```

## Test Configuration

### Test Environment (.env.test)
```bash
# Test database (separate from development)
DATABASE_URL=postgresql://test_user:password@localhost:5432/tickstock_test

# Test Redis (use different DB)
REDIS_DB=1

# Disable external services
DATA_SOURCE_TYPE=synthetic
MONITORING_ENABLED=false
ALERT_EMAIL_ENABLED=false

# Speed up tests
CACHE_TTL=1
HEALTH_CHECK_INTERVAL=1
```

### Pytest Configuration (pytest.ini)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    -p no:cacheprovider
markers =
    integration: Integration tests
    api: API tests
    websocket: WebSocket tests
    performance: Performance tests
    slow: Slow running tests
```

## Running Tests

### Run by Category
```bash
# Integration tests only
pytest -m integration

# API tests only
pytest -m api

# Performance tests
pytest -m performance

# Exclude slow tests
pytest -m "not slow"
```

### Run with Coverage
```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View coverage
open htmlcov/index.html
```

### Run in Parallel
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto
```

## Test Data Management

### Fixtures
```python
@pytest.fixture
def sample_pattern_event():
    """Sample pattern event for testing"""
    return {
        'symbol': 'AAPL',
        'pattern': 'bullish_engulfing',
        'timestamp': datetime.now().isoformat(),
        'confidence': 0.85,
        'timeframe': 'daily'
    }

@pytest.fixture
def redis_client():
    """Test Redis client"""
    client = redis.Redis(host='localhost', port=6379, db=1)
    yield client
    client.flushdb()  # Cleanup
```

### Test Database
```bash
# Create test database
createdb tickstock_test

# Run migrations
DATABASE_URL=postgresql://localhost/tickstock_test python model_migrations_run.py upgrade

# Seed test data
python scripts/dev_tools/seed_test_data.py
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:latest
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v2

    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest-cov

    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/tickstock_test
        REDIS_HOST: localhost
      run: |
        python run_tests.py
```

## Test Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Clean up test data after each test

### 2. Mocking External Services
```python
@mock.patch('src.data.massive_client.MassiveClient')
def test_with_mocked_massive(mock_massive):
    """Test without hitting real Massive API"""
    mock_massive.get_ticker.return_value = test_data
    # Test logic here
```

### 3. Async Testing
```python
@pytest.mark.asyncio
async def test_websocket_async():
    """Test async WebSocket operations"""
    async with websocket_client() as ws:
        await ws.send_json({'type': 'subscribe', 'symbol': 'AAPL'})
        response = await ws.receive_json()
        assert response['status'] == 'subscribed'
```

### 4. Performance Assertions
```python
def test_performance_benchmark():
    """Ensure operation meets performance target"""
    with benchmark(max_time=0.05):  # 50ms max
        result = expensive_operation()
    assert result is not None
```

## Troubleshooting Tests

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Ensure test database exists
   createdb tickstock_test

   # Check connection
   psql tickstock_test -c "SELECT 1"
   ```

2. **Redis Connection Errors**
   ```bash
   # Ensure Redis is running
   redis-cli ping

   # Check test database is clean
   redis-cli -n 1 FLUSHDB
   ```

3. **Flaky Tests**
   ```python
   # Add retries for unstable tests
   @pytest.mark.flaky(reruns=3, reruns_delay=1)
   def test_occasionally_fails():
       # Test that sometimes fails due to timing
   ```

4. **Slow Tests**
   ```python
   # Mark slow tests
   @pytest.mark.slow
   def test_heavy_processing():
       # Long-running test

   # Skip slow tests during development
   pytest -m "not slow"
   ```

## Test Metrics

### Coverage Goals
- Overall: >80%
- Critical paths: >90%
- API endpoints: 100%
- Error handlers: 100%

### Performance Benchmarks
- Unit tests: <1s each
- Integration tests: <5s each
- Full suite: <5 minutes

### Quality Metrics
- Zero failing tests in main branch
- All PRs must pass tests
- Performance regression detection
- Security vulnerability scanning