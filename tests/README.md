# TickStock Test Suites - Simplified Architecture

**Version**: 2.0.0-simplified  
**Last Updated**: August 25, 2025  
**Status**: Post-Cleanup Test Organization

## Overview

Test suites for the simplified TickStock architecture after major cleanup (Phases 6-11). Tests focus on the core components and essential functionality.

## Test Organization

### Data Source Tests (`/data_source/`)
- **Unit Tests**: Data provider interfaces and implementations
- **Integration Tests**: End-to-end data flow validation
- **Performance Tests**: Data generation and processing performance

### Relevant Test Categories
- **Unit Tests**: Component-level testing for simplified architecture
- **Integration Tests**: Data flow testing for core components  
- **Performance Tests**: Basic performance validation

### Test Execution
```bash
# Run all tests
pytest tests/

# Run data source tests only
pytest tests/data_source/

# Run with performance markers
pytest tests/ -m performance
```

## Removed Test Categories
- Analytics tests (removed with analytics components)
- Event detection tests (removed with event detection system)
- Multi-frequency processing tests (removed with complex processing)
- Complex pipeline and routing tests (removed with routing system)

---

Tests now align with the simplified 3-component architecture: Market Data Service, Data Publisher, and WebSocket Publisher.