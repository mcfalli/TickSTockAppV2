# ETF Integration Testing Strategy
## Sprint 14 Phase 1 - Database Testing and Validation Plan

**Generated**: 2025-09-01  
**Target Environment**: PostgreSQL + TimescaleDB ("tickstock" database)  
**Performance Requirement**: <50ms query response times

---

## Testing Overview

This comprehensive testing strategy validates the Enhanced ETF Integration database modifications, ensuring performance targets are met while maintaining system reliability and data integrity.

### Testing Phases
1. **Unit Testing**: Individual query and method validation
2. **Integration Testing**: Cross-system functionality verification  
3. **Performance Testing**: Load testing and benchmarking
4. **Regression Testing**: Existing functionality preservation
5. **Production Readiness**: Deployment validation testing

---

## Phase 1: Unit Testing

### Database Schema Validation

#### Test 1.1: Column Addition Verification
```sql
-- Verify all ETF columns exist with correct data types
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'symbols' 
  AND table_schema = 'public'
  AND column_name IN (
    'etf_type', 'aum_millions', 'expense_ratio', 'underlying_index',
    'correlation_reference', 'fmv_supported', 'creation_unit_size',
    'dividend_frequency', 'inception_date', 'net_assets', 
    'primary_exchange', 'issuer', 'average_spread', 
    'daily_volume_avg', 'premium_discount_avg', 'tracking_error'
  )
ORDER BY ordinal_position;

-- Expected: 16 rows with correct data types
-- PASS CRITERIA: All columns present with expected types
```

#### Test 1.2: Index Creation Verification  
```sql
-- Verify ETF-specific indexes were created
SELECT 
    indexname, 
    indexdef,
    idx_scan,
    idx_tup_read
FROM pg_indexes pi
LEFT JOIN pg_stat_user_indexes psi ON pi.indexname = psi.indexname
WHERE pi.tablename = 'symbols' 
  AND pi.indexname LIKE '%etf%'
ORDER BY pi.indexname;

-- Expected: 6 ETF-specific indexes
-- PASS CRITERIA: idx_etf_classification, idx_etf_aum_size, etc. all present
```

#### Test 1.3: Hypertable Creation Verification
```sql
-- Verify ETF FMV cache hypertable
SELECT 
    hypertable_name,
    num_dimensions,
    num_chunks,
    compression_enabled
FROM timescaledb_information.hypertables 
WHERE hypertable_name = 'etf_fmv_cache';

-- Expected: 1 row with 2 dimensions (time + symbol partitioning)
-- PASS CRITERIA: Hypertable created with proper partitioning
```

#### Test 1.4: View Creation Verification
```sql
-- Verify ETF analysis views exist
SELECT 
    viewname, 
    viewowner
FROM pg_views 
WHERE schemaname = 'public' 
  AND viewname IN ('v_etf_summary', 'v_etf_performance_ranking', 'v_etf_correlation_groups')
ORDER BY viewname;

-- Expected: 3 ETF analysis views
-- PASS CRITERIA: All views created and accessible
```

### ETF Query Method Testing

#### Test 1.5: ETF Symbol Filtering Performance
```python
def test_etf_symbol_filtering():
    """Test ETF symbol filtering with various parameters."""
    db = TickStockDatabase(config)
    
    # Test basic ETF filtering
    start_time = time.time()
    etfs = db.get_etf_symbols_for_dropdown(etf_type='ETF')
    duration_ms = (time.time() - start_time) * 1000
    
    assert len(etfs) > 0, "Should return ETF symbols"
    assert duration_ms < 20, f"Query too slow: {duration_ms:.2f}ms"
    assert all(etf['etf_type'] == 'ETF' for etf in etfs), "All results should be ETFs"
    
    # Test AUM filtering
    large_etfs = db.get_etf_symbols_for_dropdown(min_aum=1000)
    assert len(large_etfs) < len(etfs), "AUM filter should reduce results"
    
    # Test expense ratio filtering  
    low_cost_etfs = db.get_etf_symbols_for_dropdown(max_expense_ratio=0.01)
    assert all(etf['expense_ratio'] <= 0.01 for etf in low_cost_etfs 
               if etf['expense_ratio']), "Expense ratio filter validation"
```

#### Test 1.6: FMV Lookup Performance
```python  
def test_etf_fmv_lookup():
    """Test Fair Market Value lookup performance."""
    db = TickStockDatabase(config)
    
    # Insert test FMV data
    test_symbol = 'TESTF'
    with db.get_connection() as conn:
        conn.execute(text("""
            INSERT INTO etf_fmv_cache 
            (symbol, timestamp, nav_estimate, premium_discount, confidence_score)
            VALUES (:symbol, NOW(), 100.50, 0.0025, 0.95)
        """), {'symbol': test_symbol})
        conn.commit()
    
    # Test current FMV lookup
    start_time = time.time()
    fmv_data = db.get_etf_fmv_current(test_symbol)
    duration_ms = (time.time() - start_time) * 1000
    
    assert fmv_data is not None, "Should return FMV data"
    assert duration_ms < 15, f"FMV lookup too slow: {duration_ms:.2f}ms"
    assert fmv_data['symbol'] == test_symbol, "Correct symbol returned"
    assert fmv_data['nav_estimate'] == 100.50, "Correct NAV estimate"
```

### Data Integrity Testing

#### Test 1.7: ETF Data Validation
```sql
-- Test data constraints and relationships
WITH etf_validation AS (
  SELECT 
    symbol,
    etf_type IS NOT NULL as has_etf_type,
    expense_ratio BETWEEN 0 AND 1 as valid_expense_ratio,
    aum_millions >= 0 as valid_aum,
    creation_unit_size > 0 as valid_creation_unit,
    inception_date <= CURRENT_DATE as valid_inception
  FROM symbols 
  WHERE etf_type IS NOT NULL
)
SELECT 
  COUNT(*) as total_etfs,
  COUNT(*) FILTER (WHERE has_etf_type) as with_etf_type,
  COUNT(*) FILTER (WHERE valid_expense_ratio) as valid_expense_ratios,
  COUNT(*) FILTER (WHERE valid_aum) as valid_aums,
  COUNT(*) FILTER (WHERE NOT valid_inception) as invalid_inception_dates
FROM etf_validation;

-- PASS CRITERIA: All validation counts should equal total_etfs
```

---

## Phase 2: Integration Testing

### Cross-System Functionality

#### Test 2.1: UI Integration Testing
```python
def test_etf_dashboard_integration():
    """Test ETF data integration with dashboard UI."""
    from src.api.rest.api import app
    
    with app.test_client() as client:
        # Test ETF dashboard endpoint
        response = client.get('/api/etf/dashboard-stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_etfs' in data
        assert 'etf_types' in data
        assert 'avg_expense_ratio' in data
        
        # Test ETF filtering endpoint
        response = client.get('/api/etf/symbols?etf_type=ETF&min_aum=100')
        assert response.status_code == 200
        
        symbols = response.get_json()
        assert isinstance(symbols, list)
        assert len(symbols) > 0
```

#### Test 2.2: WebSocket ETF Updates
```python
def test_etf_websocket_integration():
    """Test ETF data delivery via WebSocket."""
    import socketio
    
    sio = socketio.SimpleClient()
    sio.connect('http://localhost:5000')
    
    # Request ETF correlation data
    sio.emit('get_etf_correlation', {'reference': 'SPY'})
    
    # Wait for response
    event_data = sio.receive(timeout=5)
    assert event_data[0] == 'etf_correlation_data'
    
    correlation_data = event_data[1]
    assert 'correlation_reference' in correlation_data
    assert correlation_data['correlation_reference'] == 'SPY'
    
    sio.disconnect()
```

### Database Connection Pool Testing

#### Test 2.3: Connection Pool Stress Testing
```python
def test_connection_pool_etf_load():
    """Test connection pool under ETF query load."""
    import concurrent.futures
    import threading
    
    db = TickStockDatabase(config)
    results = []
    errors = []
    
    def etf_query_worker():
        """Worker function for concurrent ETF queries."""
        try:
            # Mix of ETF query types
            db.get_etf_symbols_for_dropdown(etf_type='ETF')
            db.get_etf_correlation_groups(limit=10)
            db.get_etf_performance_ranking(limit=20)
            results.append(threading.current_thread().ident)
        except Exception as e:
            errors.append(str(e))
    
    # Launch 10 concurrent ETF query threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(etf_query_worker) for _ in range(10)]
        concurrent.futures.wait(futures)
    
    assert len(errors) == 0, f"Connection pool errors: {errors}"
    assert len(results) == 10, "All ETF queries should complete"
    
    # Verify connection pool health
    pool_health = db.health_check()
    assert pool_health['status'] == 'healthy', "Connection pool should remain healthy"
```

---

## Phase 3: Performance Testing

### Query Performance Benchmarks

#### Test 3.1: ETF Query Response Time Testing
```python
def benchmark_etf_queries():
    """Comprehensive ETF query performance benchmarking."""
    db = TickStockDatabase(config)
    benchmarks = {}
    
    # ETF symbol dropdown (most frequent query)
    times = []
    for _ in range(100):
        start = time.time()
        db.get_etf_symbols_for_dropdown()
        times.append((time.time() - start) * 1000)
    
    benchmarks['etf_dropdown'] = {
        'avg_ms': sum(times) / len(times),
        'max_ms': max(times),
        'p95_ms': sorted(times)[95]
    }
    
    # ETF correlation analysis
    times = []
    for _ in range(50):
        start = time.time()
        db.get_etf_correlation_groups(limit=20)
        times.append((time.time() - start) * 1000)
    
    benchmarks['etf_correlation'] = {
        'avg_ms': sum(times) / len(times),
        'max_ms': max(times),
        'p95_ms': sorted(times)[48]  # 95th percentile
    }
    
    # FMV lookup (real-time critical)
    times = []
    for _ in range(200):
        start = time.time()
        db.get_etf_fmv_current('SPY')  # Assuming SPY has FMV data
        times.append((time.time() - start) * 1000)
    
    benchmarks['fmv_lookup'] = {
        'avg_ms': sum(times) / len(times),
        'max_ms': max(times),
        'p95_ms': sorted(times)[190]  # 95th percentile
    }
    
    # Validate performance targets
    assert benchmarks['etf_dropdown']['p95_ms'] < 20, "ETF dropdown P95 > 20ms"
    assert benchmarks['etf_correlation']['p95_ms'] < 30, "ETF correlation P95 > 30ms"  
    assert benchmarks['fmv_lookup']['p95_ms'] < 15, "FMV lookup P95 > 15ms"
    
    return benchmarks
```

#### Test 3.2: Index Effectiveness Testing
```sql
-- Monitor index usage for ETF queries
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan::FLOAT / (seq_scan + idx_scan) * 100 AS index_usage_pct
FROM pg_stat_user_indexes 
WHERE tablename IN ('symbols', 'etf_fmv_cache', 'etf_classifications')
  AND indexname LIKE '%etf%'
ORDER BY idx_scan DESC;

-- PASS CRITERIA: ETF indexes should show > 80% usage for relevant queries
```

### Load Testing with Sample Data

#### Test 3.3: Large Dataset Performance
```python
def test_etf_large_dataset_performance():
    """Test ETF queries with large dataset simulation."""
    db = TickStockDatabase(config)
    
    # Generate test ETF data (1000 ETFs)
    test_etfs = []
    for i in range(1000):
        test_etfs.append({
            'symbol': f'TEST{i:04d}',
            'name': f'Test ETF {i}',
            'etf_type': 'ETF',
            'aum_millions': random.uniform(10, 50000),
            'expense_ratio': random.uniform(0.001, 0.02),
            'active': True
        })
    
    # Bulk insert test data
    with db.get_connection() as conn:
        for etf in test_etfs:
            conn.execute(text("""
                INSERT INTO symbols (symbol, name, etf_type, aum_millions, expense_ratio, active)
                VALUES (:symbol, :name, :etf_type, :aum_millions, :expense_ratio, :active)
                ON CONFLICT (symbol) DO NOTHING
            """), etf)
        conn.commit()
    
    # Test query performance with large dataset
    start_time = time.time()
    large_etfs = db.get_etf_symbols_for_dropdown(min_aum=1000)
    duration_ms = (time.time() - start_time) * 1000
    
    assert len(large_etfs) > 0, "Should return filtered ETFs"
    assert duration_ms < 50, f"Large dataset query too slow: {duration_ms:.2f}ms"
    
    # Cleanup test data
    with db.get_connection() as conn:
        conn.execute(text("DELETE FROM symbols WHERE symbol LIKE 'TEST%'"))
        conn.commit()
```

---

## Phase 4: Regression Testing

### Existing Functionality Preservation

#### Test 4.1: Original Symbol Queries Unchanged
```python
def test_original_symbol_queries_preserved():
    """Verify existing symbol queries maintain performance."""
    db = TickStockDatabase(config)
    
    # Test original get_symbols_for_dropdown method
    start_time = time.time()
    symbols = db.get_symbols_for_dropdown()
    duration_ms = (time.time() - start_time) * 1000
    
    assert len(symbols) > 0, "Should return symbols"
    assert duration_ms < 10, f"Original symbol query degraded: {duration_ms:.2f}ms"
    
    # Verify structure unchanged for backward compatibility
    if symbols:
        symbol = symbols[0]
        required_fields = ['symbol', 'name', 'exchange', 'market', 'type', 'active']
        for field in required_fields:
            assert field in symbol, f"Missing required field: {field}"
```

#### Test 4.2: Dashboard Statistics Backward Compatibility
```python
def test_dashboard_stats_backward_compatibility():
    """Test existing dashboard statistics remain unchanged."""
    db = TickStockDatabase(config)
    
    # Test original dashboard stats method
    stats = db.get_basic_dashboard_stats()
    
    # Verify original fields exist
    required_fields = [
        'symbols_count', 'active_symbols_count', 'symbols_by_market',
        'events_count', 'database_status'
    ]
    
    for field in required_fields:
        assert field in stats, f"Missing required dashboard field: {field}"
    
    # Verify performance not degraded
    start_time = time.time()
    db.get_basic_dashboard_stats()
    duration_ms = (time.time() - start_time) * 1000
    
    assert duration_ms < 25, f"Dashboard stats query degraded: {duration_ms:.2f}ms"
```

---

## Phase 5: Production Readiness Testing

### Deployment Validation

#### Test 5.1: Migration Script Execution
```bash
#!/bin/bash
# Production migration test script

echo "Starting ETF Integration Migration Test..."

# 1. Backup current database
pg_dump tickstock > backup_pre_etf_$(date +%Y%m%d_%H%M%S).sql

# 2. Execute migration script  
psql -d tickstock -f scripts/database/etf_integration_migration.sql > migration_log.txt 2>&1

# 3. Verify migration success
if [ $? -eq 0 ]; then
    echo "Migration completed successfully"
    
    # 4. Run verification queries
    psql -d tickstock -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'symbols' AND column_name LIKE '%etf%';"
    
    # 5. Test basic ETF query
    psql -d tickstock -c "SELECT COUNT(*) FROM symbols WHERE etf_type IS NOT NULL;"
    
else
    echo "Migration failed - check migration_log.txt"
    exit 1
fi
```

#### Test 5.2: Production Performance Validation
```python
def production_readiness_check():
    """Final production readiness validation."""
    db = TickStockDatabase(config)
    
    # Health check
    health = db.health_check()
    assert health['status'] == 'healthy', f"Database not healthy: {health}"
    assert health['query_performance'] < 50, "Health check query too slow"
    
    # ETF functionality check
    etfs = db.get_etf_symbols_for_dropdown()
    assert len(etfs) >= 0, "ETF query should execute without errors"
    
    # Connection pool stability
    for i in range(20):
        db.get_basic_dashboard_stats()
        if i % 5 == 0:
            db.get_etf_dashboard_stats()
    
    final_health = db.health_check()
    assert final_health['status'] == 'healthy', "Connection pool degraded after load"
    
    # FMV system check (if applicable)
    try:
        fmv_data = db.get_etf_fmv_current('SPY', max_age_minutes=60)
        # Should not error even if no data
        assert isinstance(fmv_data, (dict, type(None))), "FMV query structure valid"
    except Exception as e:
        # Log but don't fail if FMV not populated yet
        logger.warning(f"FMV system not ready: {e}")
    
    return True
```

### Monitoring and Alerting Setup

#### Test 5.3: Performance Monitoring Configuration
```python
def setup_etf_performance_monitoring():
    """Configure ETF-specific performance monitoring."""
    
    # Query performance thresholds
    monitoring_config = {
        'etf_dropdown_max_ms': 20,
        'etf_correlation_max_ms': 30, 
        'fmv_lookup_max_ms': 15,
        'connection_pool_max_utilization': 70,
        'index_usage_min_pct': 80
    }
    
    # Database monitoring queries
    monitoring_queries = {
        'slow_etf_queries': """
            SELECT query, calls, mean_time, total_time 
            FROM pg_stat_statements 
            WHERE query LIKE '%etf_%' 
              AND mean_time > 50 
            ORDER BY mean_time DESC;
        """,
        
        'etf_index_usage': """
            SELECT indexname, idx_scan, idx_tup_read,
                   idx_scan::FLOAT / (seq_scan + idx_scan) * 100 as usage_pct
            FROM pg_stat_user_indexes 
            WHERE tablename = 'symbols' 
              AND indexname LIKE '%etf%'
              AND (idx_scan::FLOAT / (seq_scan + idx_scan) * 100) < 80;
        """,
        
        'connection_pool_health': """
            SELECT 
                numbackends as active_connections,
                xact_commit + xact_rollback as total_transactions
            FROM pg_stat_database 
            WHERE datname = 'tickstock';
        """
    }
    
    return monitoring_config, monitoring_queries
```

---

## Test Execution Strategy

### Automated Testing Pipeline

#### CI/CD Integration
```yaml
# .github/workflows/etf-integration-tests.yml
name: ETF Integration Tests

on:
  pull_request:
    paths:
      - 'scripts/database/**'
      - 'src/infrastructure/database/**'

jobs:
  database-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: tickstock_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements/test.txt
        pip install psycopg2-binary
    
    - name: Run database migration
      run: |
        psql -h localhost -U postgres -d tickstock_test -f scripts/database/etf_integration_migration.sql
    
    - name: Run ETF integration tests
      run: |
        python -m pytest tests/database/test_etf_integration.py -v
    
    - name: Run performance benchmarks
      run: |
        python -m pytest tests/database/test_etf_performance.py -v --benchmark-only
```

### Manual Testing Checklist

#### Pre-Deployment Validation
- [ ] Execute migration script in staging environment
- [ ] Verify all ETF indexes created successfully
- [ ] Confirm ETF views accessible and return data
- [ ] Test ETF query methods with sample data
- [ ] Validate query performance meets <50ms targets
- [ ] Check connection pool stability under load
- [ ] Verify existing functionality unchanged
- [ ] Test ETF dashboard UI integration
- [ ] Confirm FMV lookup system operational (if applicable)
- [ ] Run comprehensive performance benchmarks

#### Post-Deployment Monitoring
- [ ] Monitor query performance for 48 hours
- [ ] Track connection pool utilization patterns
- [ ] Verify index usage statistics
- [ ] Check error rates and query failures
- [ ] Validate ETF data accuracy and completeness
- [ ] Monitor storage growth and compression effectiveness
- [ ] Test ETF features end-to-end in production
- [ ] Collect user feedback on ETF functionality performance

---

## Success Criteria

### Performance Targets
- **ETF Dropdown Queries**: <20ms average, <30ms P95
- **ETF Correlation Analysis**: <30ms average, <40ms P95  
- **FMV Lookups**: <15ms average, <25ms P95
- **Connection Pool Utilization**: <70% average, <85% peak
- **Index Effectiveness**: >80% usage for ETF-specific indexes

### Functional Requirements
- All ETF database methods execute without errors
- ETF filtering and searching work correctly
- FMV data can be stored and retrieved efficiently  
- ETF dashboard statistics display accurately
- Integration with existing UI components seamless
- Backward compatibility with existing symbol queries maintained

### Quality Assurance
- Zero degradation in existing query performance
- Database migration completes without data loss
- All ETF indexes created and utilized effectively
- Connection pool remains stable under mixed query load
- TimescaleDB compression and retention policies active
- ETF data integrity constraints enforced properly

The ETF Integration testing strategy ensures comprehensive validation of database modifications while maintaining TickStock's high performance and reliability standards. All tests should pass before production deployment to guarantee seamless ETF functionality integration.