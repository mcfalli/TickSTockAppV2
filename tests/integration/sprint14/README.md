# Sprint 14 Integration Testing Suite

Comprehensive integration testing for Sprint 14 cross-system validation between TickStockApp (consumer) and TickStockPL (producer) via Redis pub-sub architecture.

## Overview

This integration testing suite validates the loose coupling architecture and ensures proper communication patterns across all 4 phases of Sprint 14 implementation:

- **Phase 1**: Foundation Enhancement (ETF, EOD, Historical)
- **Phase 2**: Automation & Monitoring (IPO, Quality, Equity Types)  
- **Phase 3**: Advanced Features (Cache, Universe, Test Scenarios)
- **Phase 4**: Production Optimization (Scheduler, Refresh, Schedule)

## Performance Requirements

- **Message Delivery**: <100ms end-to-end Redis pub-sub delivery
- **Database Queries**: <50ms for integration scenarios  
- **Redis Operations**: <10ms for basic operations
- **WebSocket Broadcast**: <50ms for UI updates
- **End-to-End Workflows**: <500ms for complete scenarios

## Test Categories

### Phase-Specific Tests

#### Phase 1: Foundation Enhancement (`phase1_integration_tests.py`)
- ETF integration workflow validation
- End-of-day processing integration
- Historical data loading with subset support
- Cross-system data flow validation

#### Phase 2: Automation & Monitoring (`phase2_integration_tests.py`)
- IPO detection and notification workflows
- Data quality monitoring and automated remediation
- Equity type classification and processing rules
- Cross-system automation validation

#### Phase 3: Advanced Features (`phase3_integration_tests.py`)
- Cache entries expansion and synchronization
- ETF universe manager with AUM/liquidity tracking
- Test scenario generation and validation
- Advanced feature integration workflows

#### Phase 4: Production Optimization (`phase4_integration_tests.py`)
- Enterprise scheduler with Redis Streams job distribution
- Development environment refresh capabilities
- Market schedule integration and automated timing
- Production-grade workflow validation

### Cross-System Tests

#### Cross-Phase Workflows (`cross_phase_workflows.py`)
- Complete end-to-end workflows spanning multiple phases
- System-wide data consistency validation
- High-volume scalability testing
- Concurrent operations across all phases

#### Redis Resilience (`redis_resilience_tests.py`)
- Connection failure and recovery scenarios
- Message queue overflow handling
- Network partition resilience
- Service restart and failover scenarios

#### Performance Integration (`performance_integration_tests.py`)
- Message delivery latency validation (<100ms)
- High-frequency message performance
- Database query performance (<50ms)
- End-to-end workflow performance (<500ms)

## Quick Start

### Prerequisites

1. **Redis Server**: Running on localhost:6379 with database 15 available for testing
   ```bash
   redis-server
   ```

2. **Test Database**: PostgreSQL/TimescaleDB with test database configured
   ```bash
   createdb tickstock_test
   ```

3. **Python Dependencies**: Install required packages
   ```bash
   pip install pytest redis sqlalchemy psycopg2-binary
   ```

### Running Tests

#### Run All Integration Tests
```bash
cd tests/integration/sprint14/
python run_integration_tests.py --all
```

#### Run Specific Phase Tests
```bash
# Phase 1: Foundation Enhancement
python run_integration_tests.py --phase 1

# Phase 2: Automation & Monitoring  
python run_integration_tests.py --phase 2

# Phase 3: Advanced Features
python run_integration_tests.py --phase 3

# Phase 4: Production Optimization
python run_integration_tests.py --phase 4
```

#### Run Specific Test Categories
```bash
# Cross-phase workflows
python run_integration_tests.py --cross-phase

# Redis resilience tests
python run_integration_tests.py --resilience

# Performance validation
python run_integration_tests.py --performance
```

#### Generate Reports
```bash
# JSON report
python run_integration_tests.py --all --report-json

# HTML report  
python run_integration_tests.py --all --report-html

# Custom output file
python run_integration_tests.py --all --report-html --output sprint14_results.json
```

### Direct pytest Usage

You can also run tests directly with pytest:

```bash
# Run specific test file
pytest phase1_integration_tests.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run with performance benchmarks
pytest performance_integration_tests.py --benchmark-sort=mean

# Run specific test method
pytest phase1_integration_tests.py::TestETFIntegrationWorkflow::test_etf_universe_loading_integration
```

## Test Configuration

### Environment Variables

- `TEST_DATABASE_URL`: Test database connection string
- `REDIS_URL`: Redis connection string for testing
- `TESTING`: Set to 'true' to enable test mode

### Configuration Files

- `conftest.py`: Shared fixtures and test configuration
- Test databases use dedicated instances (Redis DB 15, separate PostgreSQL database)

## Integration Architecture Validation

### Role Boundary Enforcement

Tests validate that:
- **TickStockApp (Consumer Role)**: Subscribes to events, triggers jobs, read-only database access
- **TickStockPL (Producer Role)**: Publishes events, processes jobs, full database read/write access
- **No Direct API Calls**: All communication via Redis pub-sub messaging

### Message Flow Patterns

```
TickStockPL (Producer)     Redis Pub-Sub        TickStockApp (Consumer)
├─ Pattern Events      →   tickstock.events.*   → ├─ Pattern Alerts
├─ Backtest Results    →   tickstock.events.*   → ├─ Result Display  
├─ Job Processing      ←   tickstock.jobs.*     ← ├─ Job Submission
└─ Data Updates        →   tickstock.events.*   → └─ UI Updates
```

### Performance Validation

Tests enforce strict performance requirements:
- Message delivery latency tracking with statistical analysis
- Database query performance monitoring  
- End-to-end workflow timing validation
- System degradation testing under load

## Test Data Management

### Mock Services

- `MockTickStockPLProducer`: Simulates TickStockPL event publishing
- `MockTickStockAppConsumer`: Simulates TickStockApp job submissions
- `UnstableRedisClient`: Simulates Redis connection failures for resilience testing

### Test Isolation

- Each test uses isolated Redis database (DB 15)
- Database transactions are rolled back after each test
- No cross-test data contamination

## Troubleshooting

### Common Issues

1. **Redis Connection Error**: Ensure Redis is running on localhost:6379
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. **Database Connection Error**: Verify test database exists and is accessible
   ```bash
   psql -d tickstock_test -c "SELECT 1;"
   ```

3. **Permission Issues**: Ensure database user has required permissions
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE tickstock_test TO app_readwrite;
   ```

4. **Port Conflicts**: Check for conflicting services on default ports
   ```bash
   lsof -i :6379  # Redis
   lsof -i :5432  # PostgreSQL
   ```

### Performance Issues

If tests fail performance requirements:

1. **Check System Resources**: Ensure adequate CPU/memory
2. **Database Optimization**: Verify indexes and query performance
3. **Redis Configuration**: Check Redis memory and connection limits
4. **Network Latency**: Validate local network performance

### Test Failures

For test failures:

1. **Review Logs**: Check detailed error output in test results
2. **Isolation**: Run failing tests individually to identify issues
3. **Timing**: Some tests are timing-sensitive; retry if system is under load
4. **Configuration**: Verify all environment variables are set correctly

## Contributing

When adding new integration tests:

1. **Follow Patterns**: Use existing test structure and fixtures
2. **Performance Focus**: Include performance validation in all tests
3. **Error Handling**: Test both success and failure scenarios
4. **Documentation**: Update this README with new test descriptions
5. **Validation**: Ensure tests validate loose coupling architecture

## Architecture References

- **System Architecture**: `docs/architecture/system-architecture.md`
- **Integration Guide**: `docs/guides/integration-guide.md`  
- **Sprint Documentation**: `docs/planning/sprint14/`
- **Database Schema**: `docs/architecture/database-architecture.md`

## Support

For issues with integration tests:

1. Check this README and troubleshooting section
2. Review Sprint 14 implementation documentation
3. Validate Redis pub-sub architecture patterns
4. Ensure proper role separation (Consumer vs Producer)
5. Verify performance targets are realistic for system configuration