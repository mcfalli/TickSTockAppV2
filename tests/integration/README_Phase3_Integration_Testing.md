# Sprint 14 Phase 3 Integration Testing Documentation

**Created**: 2025-09-01  
**Sprint**: 14 Phase 3  
**Integration Testing Specialist**: Cross-system validation for TickStockApp ↔ TickStockPL communication

## Overview

This comprehensive integration testing suite validates the advanced features implemented in Sprint 14 Phase 3, ensuring loose coupling architecture, performance targets, and service boundary enforcement between TickStockApp (consumer) and TickStockPL (producer) systems.

## Integration Testing Architecture

### Core Testing Principles

1. **Loose Coupling Validation**: Ensure no direct API calls between systems - only Redis pub-sub communication
2. **Performance Compliance**: Validate <100ms message delivery, <50ms database queries, <2s ETF operations
3. **Service Boundary Enforcement**: Test that AppV2 stays in consumer role, TickStockPL in producer role
4. **System Resilience**: Validate graceful error handling and recovery patterns
5. **Cross-System Integration**: End-to-end workflow validation from database to UI notifications

## Test Suite Structure

### 1. Primary Integration Test Suite (`test_sprint14_phase3_integration.py`)

**Purpose**: Comprehensive validation of all Phase 3 advanced features integration patterns

**Key Test Categories**:
- **ETF Universe Integration**: Database schema enhancements, Redis notifications, performance validation
- **Test Scenario Integration**: Synthetic data isolation, pattern detection integration, CLI compatibility
- **Cache Synchronization Integration**: EOD completion signals, automated updates, Redis messaging
- **Database Integration**: Enhanced schema compatibility, query performance, concurrent operations
- **Service Boundary Validation**: Loose coupling enforcement, role separation, performance impact

**Performance Targets Validated**:
```python
from src.core.services.config_manager import get_config
config = get_config()
# ETF Universe Operations
ETF_EXPANSION_TIME_TARGET = 2.0  # seconds
ETF_UNIVERSE_QUERY_TARGET = 2.0  # seconds
ETF_VALIDATION_TARGET = 2.0  # seconds

# Test Scenario Operations
SCENARIO_GENERATION_TARGET = 120.0  # seconds (2 minutes)
SCENARIO_LOADING_TARGET = 120.0  # seconds

# Cache Synchronization
CACHE_SYNC_WINDOW_TARGET = 1800.0  # seconds (30 minutes)
REDIS_NOTIFICATION_TARGET = 5.0  # seconds

# Database Performance
UI_QUERY_TARGET = 0.05  # seconds (50ms)
GENERAL_QUERY_TARGET = 0.5  # seconds
```

### 2. Redis Message Flow Tests (`test_phase3_redis_flows.py`)

**Purpose**: Specialized validation of Redis pub-sub integration patterns and message delivery

**Key Test Categories**:
- **Message Delivery Performance**: <100ms latency validation, ordering guarantees
- **Cross-System Communication**: ETF Manager ↔ TickStockApp, Cache Sync ↔ TickStockApp flows  
- **Message Persistence**: Offline consumer support via Redis Streams, catch-up mechanisms
- **High-Volume Handling**: 1000+ message processing, queue overflow handling
- **Error Recovery**: Connection failures, automatic reconnection, resilience patterns

**Redis Integration Patterns**:
```python
# Channel Organization
REDIS_CHANNELS = {
    'universe_updated': 'tickstock.universe.updated',
    'cache_sync_complete': 'tickstock.cache.sync_complete',
    'etf_correlation_update': 'tickstock.etf.correlation_update',
    'ipo_assignment': 'tickstock.cache.ipo_assignment',
    'delisting_cleanup': 'tickstock.cache.delisting_cleanup'
}

# Message Delivery Targets
MESSAGE_DELIVERY_TARGET = 100.0  # milliseconds
MESSAGE_SUCCESS_RATE_TARGET = 95.0  # percentage
HIGH_VOLUME_MESSAGE_COUNT = 1000
CONNECTION_RECOVERY_TARGET = 5.0  # seconds
```

### 3. System Resilience Tests (`test_phase3_system_resilience.py`)

**Purpose**: Comprehensive resilience testing for system failure scenarios and performance under load

**Key Test Categories**:
- **Database Resilience**: Connection recovery, transaction isolation, concurrent operations
- **Redis Resilience**: Failover handling, memory pressure, connection recovery
- **System Load Testing**: Memory usage monitoring, concurrent service operations
- **Error Isolation**: Service boundary error containment, graceful degradation
- **Resource Constraints**: Performance under memory/CPU/disk limitations

**Resilience Targets**:
```python
# Recovery Performance
DATABASE_RECOVERY_TARGET = 10.0  # seconds
REDIS_RECOVERY_TARGET = 5.0  # seconds

# System Performance Under Load
MEMORY_INCREASE_LIMIT = 100.0  # MB under stress
CONCURRENT_OPERATIONS_TARGET = 10  # simultaneous operations
AVERAGE_CPU_LIMIT = 80.0  # percentage under load

# Error Handling
ERROR_ISOLATION_REQUIREMENT = True  # No cross-service propagation
SUCCESS_RATE_UNDER_CONSTRAINTS = 70.0  # percentage minimum
```

## Test Configuration and Setup

### Database Configuration

```python
# Test Database Setup
TEST_DATABASE_CONFIG = {
    'host': config.get('TEST_DB_HOST', 'localhost'),
    'database': config.get('TEST_DB_NAME', 'tickstock_test'),
    'user': config.get('TEST_DB_USER', 'app_readwrite'),
    'password': config.get('TEST_DB_PASSWORD', 'password'),
    'port': int(config.get('TEST_DB_PORT', '5432'))
}

# Required Schema Enhancements
REQUIRED_SCHEMA_COLUMNS = [
    'universe_category',
    'liquidity_filter',
    'universe_metadata',
    'last_universe_update'
]

REQUIRED_DATABASE_FUNCTIONS = [
    'get_etf_universe',
    'update_etf_universe',
    'get_etf_universes_summary',
    'validate_etf_universe_symbols'
]
```

### Redis Configuration

```python
# Test Redis Setup
TEST_REDIS_CONFIG = {
    'host': config.get('TEST_REDIS_HOST', 'localhost'),
    'port': int(config.get('TEST_REDIS_PORT', '6379')),
    'db_main': 13,      # System resilience tests
    'db_flows': 14,     # Message flow tests  
    'db_integration': 15 # Primary integration tests
}

# Channel Validation Patterns
CHANNEL_NAMING_PATTERN = r'^tickstock\.[a-z_]+\.[a-z_]+$'
REQUIRED_CHANNELS = [
    'tickstock.universe.updated',
    'tickstock.cache.sync_complete',
    'tickstock.etf.correlation_update'
]
```

## Running Integration Tests

### Prerequisites

1. **Test Database**: PostgreSQL instance with test database and enhanced schema
2. **Test Redis**: Redis instance with multiple test databases
3. **Test Data**: Clean test environment with sample data
4. **Python Dependencies**: `pytest`, `pytest-asyncio`, `psycopg2`, `redis`, `psutil`

### Environment Setup

```bash
# Environment Variables
export TEST_DB_HOST=localhost
export TEST_DB_NAME=tickstock_test
export TEST_DB_USER=app_readwrite
export TEST_DB_PASSWORD="4pp_U$3r_2024!"
export TEST_DB_PORT=5432

export TEST_REDIS_HOST=localhost
export TEST_REDIS_PORT=6379

# Optional: Massive API for ETF validation
export MASSIVE_API_KEY="your_test_key"
```

### Test Execution

```bash
# Run complete Phase 3 integration test suite
pytest tests/integration/test_sprint14_phase3_integration.py -v --tb=short

# Run Redis message flow tests
pytest tests/integration/test_phase3_redis_flows.py -v --tb=short

# Run system resilience tests
pytest tests/integration/test_phase3_system_resilience.py -v --tb=short

# Run all Phase 3 integration tests
pytest tests/integration/ -k "phase3 or sprint14" -v

# Run with performance monitoring
pytest tests/integration/ --tb=short --durations=10

# Run specific test categories
pytest tests/integration/ -k "etf_universe" -v
pytest tests/integration/ -k "redis_flow" -v
pytest tests/integration/ -k "resilience" -v
```

### Test Categories by Performance Requirements

```bash
# Database performance tests (<50ms UI, <2s ETF operations)
pytest tests/integration/ -k "database and performance" -v

# Redis performance tests (<100ms message delivery)
pytest tests/integration/ -k "redis and latency" -v

# Memory and system performance tests (<100MB increase)
pytest tests/integration/ -k "memory or load" -v

# End-to-end workflow tests (complete system integration)
pytest tests/integration/ -k "workflow or e2e" -v
```

## Integration Validation Checklist

### Phase 3 Feature Integration

- [ ] **ETF Universe Expansion**
  - [ ] Cache_entries schema enhancements maintain compatibility
  - [ ] ETF universe expansion via `etf_universe_manager.py` integrates with historical loader
  - [ ] Redis pub-sub notifications (`tickstock.universe.updated`) reach TickStockApp
  - [ ] Database functions perform within <2s targets
  - [ ] 200+ ETF symbol processing doesn't impact existing operations

- [ ] **Test Scenario Integration**
  - [ ] TestScenarioGenerator creates synthetic data without interfering with production
  - [ ] Generated scenarios integrate with existing pattern detection systems
  - [ ] TA-Lib pattern validation works with generated OHLCV data
  - [ ] CLI integration (--scenario parameter) works with historical loader
  - [ ] <2 minute generation/loading performance maintained

- [ ] **Cache Synchronization Integration**
  - [ ] CacheEntriesSynchronizer waits for EOD completion signals via Redis
  - [ ] Market cap recalculation updates don't conflict with real-time operations
  - [ ] IPO assignment integrates with automation services
  - [ ] Cache update notifications reach TickStockApp via Redis pub-sub
  - [ ] 30-minute sync window maintained

### Cross-System Validation

- [ ] **Database Integration**
  - [ ] Enhanced cache_entries schema backward compatibility
  - [ ] ETF universe queries coexist with stock universe operations
  - [ ] Synthetic test data isolation from production historical_data
  - [ ] Cache synchronization database writes don't block read operations

- [ ] **Redis Integration**
  - [ ] Universe update messages follow existing channel naming conventions
  - [ ] Message persistence for offline TickStockApp instances
  - [ ] Sync completion notifications integrate with existing automation channels
  - [ ] No message queue overflow during high-frequency universe updates

- [ ] **Service Boundaries**
  - [ ] Advanced features respect TickStockApp consumer role boundaries
  - [ ] ETF universe management doesn't trigger analysis in TickStockApp
  - [ ] Test scenario generation maintains separation from production data flows
  - [ ] Cache synchronization maintains loose coupling via Redis messaging only

### Performance Integration

- [ ] **Target Compliance**
  - [ ] Advanced features don't impact existing <100ms message delivery
  - [ ] ETF universe queries maintain <2s performance under concurrent load
  - [ ] Scenario generation doesn't interfere with real-time data processing
  - [ ] Cache synchronization completes within 30-minute window regardless of load

- [ ] **Resilience Validation**
  - [ ] System recovery <5 seconds from database/Redis failures
  - [ ] Concurrent operations handle 10+ simultaneous requests
  - [ ] Memory efficiency maintains <100MB increase under stress
  - [ ] Error isolation prevents cross-service error propagation

## Test Data Management

### Test Database Schema

The integration tests require an enhanced `cache_entries` table with Phase 3 columns:

```sql
-- Required schema enhancements for testing
ALTER TABLE cache_entries 
ADD COLUMN IF NOT EXISTS universe_category VARCHAR(50),
ADD COLUMN IF NOT EXISTS liquidity_filter JSONB,
ADD COLUMN IF NOT EXISTS universe_metadata JSONB,
ADD COLUMN IF NOT EXISTS last_universe_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Required indexes for performance testing
CREATE INDEX IF NOT EXISTS idx_cache_entries_category ON cache_entries (universe_category);
CREATE INDEX IF NOT EXISTS idx_cache_entries_updated ON cache_entries (last_universe_update DESC);
```

### Test Data Cleanup

Integration tests automatically clean up test data:

- **Test Symbols**: All symbols with `TEST_` prefix are removed after tests
- **Cache Entries**: Test cache entries with `test_` prefix are cleaned up
- **Redis Data**: Test databases are flushed before and after test runs
- **Temporary Files**: Any temporary scenario data files are removed

### Performance Baseline Data

Tests may create baseline performance data for comparison:

- **ETF Universe Performance**: Sample universes for expansion timing
- **Message Delivery Baselines**: Latency measurements for regression testing
- **Memory Usage Baselines**: Resource consumption patterns for load testing

## Troubleshooting Integration Tests

### Common Issues

1. **Database Connection Failures**
   - Verify test database exists and is accessible
   - Check database user permissions for schema modifications
   - Ensure enhanced schema is applied

2. **Redis Connection Issues**  
   - Confirm Redis server is running and accessible
   - Verify multiple test databases are available (13, 14, 15)
   - Check Redis memory configuration for high-volume tests

3. **Performance Test Failures**
   - Verify system has sufficient resources for load testing
   - Check for other processes interfering with performance measurements
   - Consider adjusting performance targets for slower test environments

4. **Test Data Conflicts**
   - Ensure test databases are isolated from production
   - Verify test data cleanup completed from previous runs
   - Check for existing test symbols that may conflict

### Debug Configuration

```python
# Enable debug logging for integration tests
import logging
logging.basicConfig(level=logging.DEBUG)

# Add performance monitoring
import cProfile
profiler = cProfile.Profile()
# Use in test setup/teardown
```

### Test Environment Validation

Before running integration tests, validate the environment:

```python
# Run environment validation
pytest tests/integration/test_environment_validation.py -v

# Check database schema
pytest tests/integration/ -k "schema_compatibility" -v

# Verify Redis connectivity
pytest tests/integration/ -k "redis_connection" -v
```

## Integration with CI/CD Pipeline

### Automated Testing

```yaml
# Example GitHub Actions integration testing step
- name: Run Phase 3 Integration Tests
  run: |
    # Set up test environment
    docker-compose -f docker-compose.test.yml up -d postgres redis
    
    # Wait for services
    sleep 10
    
    # Run integration tests
    pytest tests/integration/test_sprint14_phase3_integration.py -v
    pytest tests/integration/test_phase3_redis_flows.py -v
    pytest tests/integration/test_phase3_system_resilience.py -v
    
    # Generate test report
    pytest tests/integration/ --junitxml=phase3_integration_report.xml
  env:
    TEST_DB_HOST: localhost
    TEST_REDIS_HOST: localhost
```

### Performance Regression Detection

Integration tests can be configured for performance regression detection:

```python
# Performance thresholds for regression detection
PERFORMANCE_REGRESSION_THRESHOLDS = {
    'etf_expansion_time': 2.5,  # 25% tolerance on 2s target
    'message_delivery_time': 125.0,  # 25% tolerance on 100ms target
    'database_query_time': 62.5,  # 25% tolerance on 50ms target
    'memory_increase': 125.0  # 25% tolerance on 100MB target
}
```

## Related Documentation

- **[`../../docs/planning/sprint14/sprint14-phase3-implementation-plan.md`](../../docs/planning/sprint14/sprint14-phase3-implementation-plan.md)** - Complete Phase 3 implementation plan
- **[`../../docs/architecture/system-architecture.md`](../../docs/architecture/system-architecture.md)** - System architecture and role separation
- **[`../../docs/architecture/database-architecture.md`](../../docs/architecture/database-architecture.md)** - Database schema and optimization
- **[`../../docs/guides/integration-guide.md`](../../docs/guides/integration-guide.md)** - Technical integration patterns
- **[`../../docs/development/unit_testing.md`](../../docs/development/unit_testing.md)** - Testing standards and organization

---

**Integration Testing Approach**: Comprehensive validation of Sprint 14 Phase 3 advanced features with focus on cross-system integration, performance compliance, and service boundary enforcement in TickStock's loosely-coupled Redis pub-sub architecture.