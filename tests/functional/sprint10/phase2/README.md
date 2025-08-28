# Sprint 10 Phase 2 Integration Tests

Comprehensive integration tests for Redis Event Consumption and WebSocket Broadcasting components implemented in Sprint 10 Phase 2.

## Overview

These integration tests validate the complete TickStockApp ↔ TickStockPL communication flow via Redis pub-sub messaging and real-time WebSocket broadcasting to browser clients.

## Test Architecture

### Core Components Tested

1. **RedisEventSubscriber** (`src/core/services/redis_event_subscriber.py`)
   - Redis pub-sub connection and message handling
   - Event processing and transformation to TickStockEvent objects
   - WebSocket broadcasting integration with Flask-SocketIO
   - Error handling and reconnection logic

2. **WebSocketBroadcaster** (`src/core/services/websocket_broadcaster.py`)
   - Flask-SocketIO connection management  
   - Real-time event broadcasting to browser clients
   - User subscription management for pattern filtering
   - Message queuing for offline users

3. **Integration Flow**
   - End-to-end event flow: Redis → Subscriber → Broadcaster → WebSocket clients
   - Event type routing and filtering
   - Performance validation (<100ms message delivery requirement)
   - System resilience and error recovery

## Test Categories

### 1. Redis Event Subscriber Tests (`test_redis_event_subscriber.py`)

**Coverage:**
- Service initialization and startup sequence
- Event processing for all event types (patterns, backtest progress/results, health)
- Message validation and JSON parsing
- Error handling (invalid messages, connection failures)
- Performance requirements (<100ms processing)
- Statistics and health monitoring
- Graceful shutdown

**Key Test Cases:**
- `test_subscriber_initialization_and_startup` - Basic service lifecycle
- `test_pattern_event_processing` - Pattern alert processing with performance validation
- `test_connection_error_and_recovery` - Redis connection resilience
- `test_concurrent_message_processing` - High-throughput event handling

### 2. WebSocket Broadcaster Tests (`test_websocket_broadcaster.py`)

**Coverage:**
- User connection and disconnection handling
- Pattern subscription management
- Real-time broadcasting with user filtering
- Offline message queuing and delivery
- Connection health monitoring
- Statistics tracking

**Key Test Cases:**
- `test_user_connection_flow` - User connection lifecycle
- `test_pattern_alert_broadcasting` - Targeted pattern broadcasting
- `test_offline_message_queueing` - Message persistence for offline users
- `test_stale_connection_cleanup` - Connection health management

### 3. End-to-End Integration Tests (`test_end_to_end_integration.py`)

**Coverage:**
- Complete TickStockPL → Redis → Subscriber → Broadcaster → WebSocket flow
- Mixed event type processing
- User subscription filtering accuracy
- System recovery after failures
- High-throughput processing
- Error isolation between components

**Key Test Cases:**
- `test_complete_pattern_alert_flow` - Full pattern alert workflow
- `test_complete_backtesting_workflow` - Backtest progress and result delivery  
- `test_mixed_event_types_concurrent_processing` - Multi-event-type handling
- `test_high_throughput_event_processing` - Load testing (100 events)

### 4. Performance & Resilience Tests (`test_performance_and_resilience.py`)

**Coverage:**
- <100ms message delivery requirement validation
- High-throughput performance (>20 events/sec burst processing)
- Concurrent user handling (50+ users)
- Redis connection failure recovery
- WebSocket client disconnection handling
- Error rate resilience
- Memory pressure handling

**Key Test Cases:**
- `test_single_event_delivery_latency` - Individual message latency validation
- `test_burst_event_handling_performance` - Burst processing (50 events)
- `test_concurrent_user_performance` - Multi-user performance (50 users)
- `test_redis_connection_failure_recovery` - Connection resilience

### 5. Application Integration Tests (`test_application_integration.py`)

**Coverage:**
- Service initialization sequence
- Configuration validation
- Dependency management
- Health monitoring integration
- Graceful shutdown procedures
- Service restart capability
- Resource management

**Key Test Cases:**
- `test_successful_service_initialization_sequence` - Startup workflow
- `test_redis_unavailable_during_startup` - Graceful degradation
- `test_graceful_service_shutdown_sequence` - Clean shutdown
- `test_loose_coupling_validation` - Architecture compliance

## Test Infrastructure

### Mock Components (`fixtures.py`)

**MockRedisClient**
- Simulates Redis pub-sub functionality
- Connection failure simulation
- Message publishing and delivery
- Subscription management

**MockSocketIO** 
- Simulates Flask-SocketIO behavior
- Client connection tracking
- Event emission handling
- Room-based messaging

**TickStockPLSimulator**
- Generates realistic TickStockPL events
- Pattern detection events
- Backtest progress/result events
- System health updates

**Integration Test Environment**
- Complete test environment setup
- Service connectivity
- Mock user management
- Event tracking and verification

### Performance Validation

All tests include performance assertions:
- **Message Delivery**: <100ms end-to-end requirement
- **Processing Throughput**: >20 events/second under burst load
- **User Scalability**: Support for 50+ concurrent users
- **Memory Efficiency**: Queue limits and cleanup validation

## Running the Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Ensure Redis is available (for real integration tests)
# Tests use mocks by default, but real Redis can be used with configuration
```

### Quick Start

```bash
# Run all integration tests
python test_runner.py --all

# Run smoke tests (quick validation)
python test_runner.py --smoke

# Run specific category
python test_runner.py --category redis_subscriber

# Run performance benchmarks
python test_runner.py --performance
```

### Individual Test Categories

```bash
# Redis Event Subscriber tests
pytest test_redis_event_subscriber.py -v

# WebSocket Broadcaster tests  
pytest test_websocket_broadcaster.py -v

# End-to-end integration tests
pytest test_end_to_end_integration.py -v

# Performance and resilience tests
pytest test_performance_and_resilience.py -v

# Application integration tests
pytest test_application_integration.py -v
```

### Test Runner Options

```bash
python test_runner.py --help

Usage: test_runner.py [-h] [--category {redis_subscriber,websocket_broadcaster,end_to_end,performance,application}] 
                     [--all] [--smoke] [--performance] [--verbose] [--fail-fast] [--test-dir TEST_DIR]

Options:
  --category    Run specific test category
  --all         Run all test categories  
  --smoke       Run quick smoke tests
  --performance Run performance benchmarks
  --verbose     Verbose output
  --fail-fast   Stop on first failure
  --test-dir    Custom test directory path
```

## Performance Requirements Validation

### Message Delivery Latency
- **Target**: <100ms end-to-end delivery
- **Validation**: Individual message timing in `test_single_event_delivery_latency`
- **Metrics**: Average, median, 95th percentile latency tracking

### Processing Throughput  
- **Target**: >20 events/second burst processing
- **Validation**: Bulk event processing in `test_burst_event_handling_performance`
- **Load**: 50-100 events processed in <2.5 seconds

### User Scalability
- **Target**: Support 50+ concurrent users
- **Validation**: Multi-user broadcasting in `test_concurrent_user_performance`
- **Filtering**: Accurate subscription-based message delivery

### System Resilience
- **Connection Recovery**: Automatic Redis reconnection
- **Error Isolation**: Handler failures don't crash system
- **Graceful Degradation**: Continue operation during partial failures

## Event Flow Validation

### Pattern Alert Flow
1. TickStockPL publishes pattern event to Redis
2. RedisEventSubscriber receives and validates event
3. Event transformed to TickStockEvent object
4. WebSocketBroadcaster applies user subscription filtering
5. Event broadcasted to subscribed WebSocket clients
6. **Validation**: Complete flow <100ms, accurate filtering

### Backtest Workflow
1. Progress updates flow through Redis → Subscriber → Broadcaster
2. Final results delivered to all connected users
3. **Validation**: Message ordering, progress tracking, completion handling

### System Health Monitoring
1. Health updates broadcasted to monitoring clients
2. Service health status aggregation
3. **Validation**: Real-time health status delivery

## Architecture Compliance

### Loose Coupling Validation
- Services communicate only through event handlers
- No direct service-to-service references
- Interface-based integration patterns

### Event-Driven Architecture
- All communication through typed events
- Fan-out pattern for multiple handlers
- Event flow traceability

### Resource Management
- Proper thread lifecycle management
- Connection cleanup on shutdown
- Memory usage optimization

## Troubleshooting

### Common Issues

**Redis Connection Failures**
- Verify Redis is running (for real integration tests)
- Check Redis configuration in test_config
- Tests use mocks by default - real Redis optional

**SocketIO Mock Issues**
- Ensure Flask-SocketIO imports available
- Mock clients properly initialized
- Event handler registration validated

**Performance Test Failures**
- Check system load during test execution
- Adjust timeout values for slower systems
- Review performance assertions for environment

### Debug Output

```bash
# Verbose test output
pytest test_redis_event_subscriber.py -v -s

# Specific test debugging
pytest test_end_to_end_integration.py::TestEndToEndIntegration::test_complete_pattern_alert_flow -v -s
```

## Integration with CI/CD

### Automated Test Execution

```yaml
# Example GitHub Actions workflow
- name: Run Sprint 10 Phase 2 Integration Tests
  run: |
    cd tests/functional/sprint10/phase2
    python test_runner.py --all --verbose
```

### Test Categories for Different Stages

- **Smoke Tests**: Fast validation for every commit
- **Integration Tests**: Full validation for pull requests  
- **Performance Tests**: Nightly builds and releases
- **Resilience Tests**: Weekly comprehensive validation

## Coverage and Quality Metrics

### Test Coverage
- **Component Coverage**: 100% of public methods tested
- **Scenario Coverage**: Normal, error, and edge cases
- **Integration Coverage**: All communication paths validated

### Quality Validation
- **Performance Requirements**: <100ms delivery validated
- **Reliability**: Error recovery and resilience tested
- **Scalability**: Multi-user concurrent operation verified
- **Architecture**: Loose coupling and event-driven patterns validated

## Contributing

When adding new integration tests:

1. Follow existing test patterns and naming conventions
2. Include performance assertions where applicable
3. Add error scenario coverage
4. Update test runner categories if needed
5. Document test purpose and validation criteria
6. Ensure tests are deterministic and reliable

## References

- **Architecture Overview**: `/docs/planning/architecture_overview.md`
- **Integration Guide**: `/docs/planning/tickstockpl-integration-guide.md`  
- **Sprint 10 Plan**: `/docs/planning/sprint10/sprint10-appv2-implementation-plan.md`
- **Redis Integration**: `/docs/planning/redis-integration-patterns.md`