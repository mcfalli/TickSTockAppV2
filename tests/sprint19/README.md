# Sprint 19 Phase 1 Pattern Discovery API Test Suite

This comprehensive test suite validates the Pattern Discovery API components for Sprint 19 Phase 1, focusing on Redis-based pattern caching, Consumer API endpoints, and performance benchmarks.

## Test Organization

### Test Files Overview

- **`conftest.py`** - Shared fixtures and utilities for Sprint 19 testing
- **`test_redis_pattern_cache.py`** - RedisPatternCache functionality and performance
- **`test_pattern_consumer_api.py`** - Pattern Consumer API endpoints and integration
- **`test_user_universe_api.py`** - User Universe API for symbols and user data
- **`test_pattern_discovery_service.py`** - Pattern Discovery Service orchestration
- **`test_performance_benchmarks.py`** - Comprehensive performance validation

## Performance Targets

### API Response Times
- **Pattern Consumer API**: <50ms for 95th percentile
- **User Universe API**: <50ms for database queries  
- **Redis Cache Operations**: <25ms for pattern scans
- **End-to-End Workflows**: <300ms for complete user workflows

### Cache Performance
- **Cache Hit Ratio**: >70% after warm-up period
- **Pattern Processing**: <25ms per pattern event
- **Memory Stability**: No memory leaks during sustained processing

### Load Testing
- **Concurrent Requests**: Support 100+ simultaneous API requests
- **Throughput**: Minimum 50 requests/second sustained
- **Success Rate**: >95% under concurrent load

## Running Tests

### Basic Test Execution

```bash
# Run all Sprint 19 tests
pytest tests/sprint19/ -v

# Run specific test file
pytest tests/sprint19/test_redis_pattern_cache.py -v

# Run with coverage reporting
pytest tests/sprint19/ -v --cov=src --cov-report=html
```

### Performance Testing

```bash
# Run all performance benchmarks
pytest tests/sprint19/ -v -m performance

# Run specific performance tests
pytest tests/sprint19/test_performance_benchmarks.py -v -m performance

# Run load testing
pytest tests/sprint19/ -v -m load

# Run integration tests
pytest tests/sprint19/ -v -m integration
```

### Test Categories

#### By Marker
```bash
pytest tests/sprint19/ -m redis          # Redis-related tests
pytest tests/sprint19/ -m database       # Database access tests
pytest tests/sprint19/ -m performance    # Performance benchmarks
pytest tests/sprint19/ -m integration    # Integration tests
pytest tests/sprint19/ -m load           # Load/stress tests
```

#### By Component
```bash
# Redis Pattern Cache tests
pytest tests/sprint19/test_redis_pattern_cache.py

# API endpoint tests
pytest tests/sprint19/test_pattern_consumer_api.py
pytest tests/sprint19/test_user_universe_api.py

# Service integration tests
pytest tests/sprint19/test_pattern_discovery_service.py

# Performance validation
pytest tests/sprint19/test_performance_benchmarks.py
```

## Test Requirements

### Dependencies

The test suite requires these additional packages for comprehensive testing:

```bash
# Install testing dependencies
pip install fakeredis psutil pytest-mock pytest-cov
```

### Environment Setup

1. **Redis Test Database**: Tests use database 1 for isolation
2. **Mock Services**: Most tests use mocked external dependencies
3. **Performance Monitoring**: Uses psutil for memory and performance tracking

## Test Coverage Areas

### RedisPatternCache Tests (`test_redis_pattern_cache.py`)

**Functional Coverage:**
- Pattern event processing from TickStockPL
- Multi-layer caching (pattern entries, API responses, indexes)
- Query filtering and sorting through Redis operations
- Cache hit ratio tracking and optimization
- Background cleanup of expired patterns
- Error handling and edge cases

**Performance Coverage:**
- Pattern caching speed (<25ms per operation)
- Scan performance under various filter combinations
- Cache effectiveness and hit ratio validation
- Memory usage under sustained load
- Concurrent access patterns

### Pattern Consumer API Tests (`test_pattern_consumer_api.py`)

**Functional Coverage:**
- `/api/patterns/scan` endpoint with comprehensive filtering
- `/api/patterns/stats` cache statistics reporting
- `/api/patterns/summary` high-level pattern overview
- `/api/patterns/health` system health monitoring
- Parameter validation and error handling
- API response format compliance

**Performance Coverage:**
- API response times (<50ms target)
- Concurrent request handling
- Load testing with 100+ simultaneous requests
- Throughput capacity measurement
- API response caching effectiveness

### User Universe API Tests (`test_user_universe_api.py`)

**Functional Coverage:**
- `/api/symbols` symbol listing and search
- `/api/symbols/<symbol>` detailed symbol information
- `/api/users/universe` universe management
- User watchlists and filter presets (TODO implementations)
- Dashboard statistics and health monitoring
- Read-only database access compliance

**Performance Coverage:**
- Database query performance validation
- Cache operations performance
- End-to-end user workflow timing
- Authentication and authorization handling

### Pattern Discovery Service Tests (`test_pattern_discovery_service.py`)

**Integration Coverage:**
- Service orchestration and component initialization
- Redis event consumption from TickStockPL channels
- Cross-component communication and data flow
- Health monitoring across all components
- Service startup and shutdown procedures
- Global service instance management

**Performance Coverage:**
- Component integration performance
- Event processing throughput
- Health monitoring response times
- Service lifecycle performance
- Resource cleanup and memory management

### Performance Benchmarks (`test_performance_benchmarks.py`)

**Comprehensive Performance Validation:**
- System-wide performance benchmarks
- Scalability limits identification
- Memory leak detection
- Performance regression analysis
- Full workflow end-to-end timing
- Resource utilization monitoring

## Performance Analysis

### Interpreting Results

#### Response Time Metrics
- **Average**: Mean response time across all requests
- **P95**: 95th percentile - 95% of requests complete within this time
- **P99**: 99th percentile - 99% of requests complete within this time
- **Target Met %**: Percentage of requests meeting performance targets

#### Cache Performance
- **Hit Ratio**: Percentage of requests served from cache
- **Hit Time**: Average response time for cache hits
- **Miss Time**: Average response time for cache misses

#### Load Testing Results
- **Success Rate**: Percentage of requests completing successfully
- **Throughput**: Requests processed per second
- **Concurrent Users**: Number of simultaneous active requests

### Performance Optimization Tips

#### For Redis Operations
1. Ensure Redis is properly configured for real-time operations
2. Monitor memory usage and adjust TTL values appropriately
3. Use Redis pipelining for batch operations
4. Optimize index structures for common query patterns

#### For API Performance
1. Enable API response caching for repeated queries
2. Optimize database queries with proper indexing
3. Use connection pooling for database and Redis connections
4. Monitor and log slow operations for optimization

#### For Load Performance
1. Configure appropriate connection limits
2. Use load balancing for horizontal scaling
3. Monitor system resources (CPU, memory, network)
4. Implement proper error handling and circuit breakers

## Troubleshooting

### Common Test Failures

#### Import Errors
```bash
# Ensure src directory is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

#### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Use test database
redis-cli -n 1 ping
```

#### Performance Test Failures
- **Slow CI Environment**: Adjust performance targets for CI/CD
- **Resource Constraints**: Monitor system resources during tests
- **Mock Overhead**: Consider using lighter mocks for performance tests

#### Memory Test Issues
- **Background Processes**: Ensure consistent test environment
- **Garbage Collection**: Tests include explicit GC calls
- **Platform Differences**: Memory behavior may vary by platform

### Debug Options

```bash
# Verbose output with detailed timing
pytest tests/sprint19/ -v -s

# Show performance metrics
pytest tests/sprint19/ -v -s --tb=short -m performance

# Debug specific test
pytest tests/sprint19/test_redis_pattern_cache.py::TestCachedPattern::test_pattern_to_api_dict_conversion -v -s
```

## Contributing to Tests

### Adding New Tests

1. **Follow Naming Conventions**: Use descriptive test names with component prefixes
2. **Use Appropriate Markers**: Mark tests with `@pytest.mark.performance`, etc.
3. **Include Performance Validation**: Add timing assertions for new features
4. **Mock External Dependencies**: Use provided fixtures for consistent testing
5. **Document Test Purpose**: Include docstrings explaining test objectives

### Performance Test Guidelines

1. **Set Realistic Targets**: Base targets on actual system requirements
2. **Measure Multiple Iterations**: Use statistical significance
3. **Include Error Handling**: Test performance under error conditions
4. **Monitor Resource Usage**: Track memory and CPU utilization
5. **Validate Regression**: Compare against baseline metrics

### Test Data Management

1. **Use Fixtures**: Leverage conftest.py fixtures for consistent test data
2. **Realistic Data**: Use realistic symbol names and market data patterns
3. **Scalable Generators**: Use pattern_data_generator for large datasets
4. **Clean Up**: Ensure tests clean up created data

## Continuous Integration

### CI/CD Integration

```yaml
# Example GitHub Actions configuration
- name: Run Sprint 19 Tests
  run: |
    pytest tests/sprint19/ -v --cov=src --cov-report=xml
    pytest tests/sprint19/ -m performance --tb=short

- name: Performance Regression Check
  run: |
    pytest tests/sprint19/test_performance_benchmarks.py::TestPerformanceRegression -v
```

### Quality Gates

1. **Test Coverage**: Maintain >80% coverage for Sprint 19 components
2. **Performance Targets**: All performance tests must pass
3. **Load Testing**: System must handle expected concurrent load
4. **Memory Stability**: No memory leaks detected
5. **Error Handling**: Comprehensive error scenario coverage

---

## Sprint 19 Test Results Summary

After running the complete test suite, you should see results similar to:

```
============== Sprint 19 Pattern Discovery API Test Results ==============

tests/sprint19/test_redis_pattern_cache.py ................... PASSED (42 tests)
tests/sprint19/test_pattern_consumer_api.py ................. PASSED (38 tests)  
tests/sprint19/test_user_universe_api.py .................... PASSED (45 tests)
tests/sprint19/test_pattern_discovery_service.py ........... PASSED (35 tests)
tests/sprint19/test_performance_benchmarks.py .............. PASSED (28 tests)

Performance Summary:
- API Response Times: All endpoints <50ms (P95)
- Redis Cache Operations: <25ms average
- Cache Hit Ratio: >70% achieved
- Concurrent Load: 100+ requests supported
- Memory Stability: No leaks detected

Total: 188 tests passed
Coverage: 85% of Sprint 19 components
```

For any issues or questions about the test suite, refer to the comprehensive test documentation or contact the development team.