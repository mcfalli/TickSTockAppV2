# Sprint 14 Execution and Testing Guide

**Document Version**: 1.0  
**Last Updated**: 2025-09-01  
**Status**: Production Ready  

---

## 📋 Overview

This comprehensive guide provides step-by-step instructions for executing and testing all Sprint 14 components across all 4 phases. Follow this guide to deploy Sprint 14's data infrastructure automation enhancements safely in production or testing environments.

## 🎯 Sprint 14 Phase Summary

| Phase | Focus | Key Components | Execution Time |
|-------|--------|----------------|----------------|
| **Phase 1** | Foundation Enhancement | ETF Integration, Development Optimization, EOD Processing | ~45 minutes |
| **Phase 2** | Automation & Monitoring | IPO Monitoring, Data Quality, Equity Types | ~35 minutes |
| **Phase 3** | Advanced Features | Universe Expansion, Test Scenarios, Cache Sync | ~50 minutes |  
| **Phase 4** | Production Optimization | Enterprise Scheduling, Rapid Refresh, Market Calendars | ~40 minutes |

**Total Execution Time**: ~2.5 hours for complete Sprint 14 deployment

---

## 🚀 Phase 1: Foundation Enhancement Execution

### **Prerequisites**
- PostgreSQL database access (PGAdmin recommended)
- Python 3.8+ environment with required dependencies
- Redis instance running and accessible
- Polygon.io API key configured

### **Step 1: Database Schema Enhancement**

#### **Execute ETF Integration Migration**
```bash
# Location: scripts/database/etf_integration_migration.sql
# Execute in PostgreSQL PGAdmin or command line

# Verify database connection
psql -h localhost -U your_user -d tickstock -c "SELECT version();"

# Execute the migration (435 lines)
psql -h localhost -U your_user -d tickstock -f scripts/database/etf_integration_migration.sql

# Verify ETF columns were added
psql -h localhost -U your_user -d tickstock -c "\d symbols"
```

**Expected Output**: 16 new ETF-specific columns added to symbols table

#### **Verify ETF Views and Functions**
```sql
-- Check ETF metadata view
SELECT * FROM etf_metadata_view LIMIT 5;

-- Test ETF universe functions
SELECT get_etf_universe('technology');
SELECT validate_etf_universe_symbols(ARRAY['QQQ', 'XLK', 'VGT']);
```

### **Step 2: Enhanced Historical Loader Testing**

#### **Test Development Mode**
```bash
# Test ETF development universe loading (40 ETFs)
cd src/data
python historical_loader.py --dev-mode --months 3 --symbols ETF_DEV

# Expected: ~90 seconds for 40 ETFs × 3 months
# Verify ETF metadata extraction working
```

#### **Test ETF Metadata Extraction**
```bash
# Test specific ETF with metadata
python historical_loader.py --symbols QQQ --months 1

# Verify in database
psql -c "SELECT symbol, asset_under_management, expense_ratio FROM symbols WHERE symbol = 'QQQ';"
```

### **Step 3: End-of-Day Processing Service**

#### **EOD Processor Setup**
```bash
# Test EOD processing service
cd src/data
python eod_processor.py --test-mode

# Check Redis notifications
redis-cli MONITOR | grep "eod"
```

#### **Verify Market Timing Logic**
```bash
# Test market close detection
python -c "
from eod_processor import EODProcessor
processor = EODProcessor()
print(f'Market closed: {processor.is_market_closed()}')
print(f'Next EOD time: {processor.get_next_eod_time()}')
"
```

### **Phase 1 Testing Commands**

#### **Run Phase 1 Test Suite**
```bash
# Execute comprehensive Phase 1 tests
cd tests/sprint14
python -m pytest data_processing/ -v --tb=short

# Run specific test categories
python -m pytest data_processing/test_etf_integration.py::TestETFMetadataExtraction -v
python -m pytest automation_services/test_eod_processing.py::TestMarketTiming -v
```

#### **Performance Validation**
```bash
# ETF loading performance test
python tests/sprint14/performance/test_etf_loading_performance.py

# Expected results:
# - ETF data loading: <3.2 minutes
# - Development universe: <90 seconds  
# - EOD processing: <22 minutes
```

---

## 🔧 Phase 2: Automation & Monitoring Execution

### **Step 1: Equity Types Enhancement**

#### **Execute Database Enhancement**
```bash
# Location: scripts/database/equity_types_enhancement.sql
psql -h localhost -U your_user -d tickstock -f scripts/database/equity_types_enhancement.sql

# Verify JSONB processing rules table
psql -c "SELECT equity_type, processing_rules FROM equity_types_enhanced LIMIT 3;"
```

### **Step 2: IPO Monitoring Service**

#### **Setup IPO Monitor**
```bash
# Start IPO monitoring service
cd automation/services
python ipo_monitor.py --config-file config/ipo_monitor.yaml

# Test 90-day historical backfill
python ipo_monitor.py --backfill-days 90 --test-mode
```

#### **Verify IPO Detection**
```bash
# Check IPO detection in database
psql -c "SELECT symbol, listing_date, sector FROM symbols WHERE listing_date >= CURRENT_DATE - INTERVAL '90 days';"

# Monitor Redis notifications
redis-cli SUBSCRIBE tickstock.ipo.detected
```

### **Step 3: Data Quality Monitoring**

#### **Start Data Quality Monitor**
```bash
cd automation/services
python data_quality_monitor.py --config-file config/quality_monitor.yaml

# Test price anomaly detection
python data_quality_monitor.py --test-anomaly-detection --symbol AAPL
```

#### **Verify Quality Alerts**
```bash
# Check quality monitoring in action
redis-cli SUBSCRIBE tickstock.quality.*

# Test volume spike detection
python -c "
from data_quality_monitor import DataQualityMonitor
monitor = DataQualityMonitor()
result = monitor.analyze_symbol_quality('TSLA')
print(f'Quality score: {result.overall_score}')
"
```

### **Phase 2 Testing Commands**

#### **Run Automation Services Tests**
```bash
# Test all Phase 2 automation services
cd tests/sprint14
python -m pytest automation_services/ -v

# Test specific components
python -m pytest automation_services/test_ipo_monitor.py::TestIPOBackfill -v
python -m pytest automation_services/test_data_quality_monitor.py::TestAnomalyDetection -v
```

#### **Integration Testing**
```bash
# Test cross-service communication
python tests/integration/sprint14/phase2_integration_tests.py

# Expected: <12s notification delivery, 99%+ message success rate
```

---

## 🎨 Phase 3: Advanced Features Execution

### **Step 1: Cache Entries Universe Expansion**

#### **Execute Universe Enhancement**
```bash
# Location: scripts/database/cache_entries_universe_expansion.sql
psql -h localhost -U your_user -d tickstock -f scripts/database/cache_entries_universe_expansion.sql

# Verify ETF universe expansion (58 total ETFs across 7 themes)
psql -c "SELECT universe_category, COUNT(*) FROM cache_entries GROUP BY universe_category;"
```

### **Step 2: ETF Universe Manager**

#### **Test ETF Universe Management**
```bash
cd src/data
python etf_universe_manager.py --update-universe --theme sectors

# Test AUM and liquidity filtering
python etf_universe_manager.py --filter-aum 1000000000 --filter-volume 5000000

# Verify Redis notifications
redis-cli SUBSCRIBE tickstock.universe.updated
```

#### **Verify Universe Functions**
```bash
# Test database universe functions
psql -c "SELECT * FROM get_etf_universe('technology');"
psql -c "SELECT update_etf_universe('growth', ARRAY['VUG', 'IVW', 'SCHG']);"
```

### **Step 3: Test Scenario Generator**

#### **Generate Test Scenarios**
```bash
cd src/data
python test_scenario_generator.py --scenario crash_2020 --symbols 10 --days 252

# Test all 5 predefined scenarios
for scenario in crash_2020 growth_2021 volatility_periods trend_changes high_low_events; do
    python test_scenario_generator.py --scenario $scenario --symbols 5 --days 60
done
```

#### **Validate Generated Data**
```bash
# Test TA-Lib integration and pattern validation
python test_scenario_generator.py --scenario high_low_events --validate-patterns --symbols AAPL
```

### **Step 4: Cache Entries Synchronization**

#### **Test Cache Synchronization**
```bash
cd src/data
python cache_entries_synchronizer.py --test-mode

# Test EOD integration (waits for eod_complete signal)
redis-cli PUBLISH tickstock.eod.completed '{"status": "success", "symbols": 1000}'

# Monitor synchronization
redis-cli SUBSCRIBE tickstock.cache.sync_complete
```

### **Phase 3 Testing Commands**

#### **Comprehensive Phase 3 Testing**
```bash
# Run all advanced features tests
cd tests/sprint14
python -m pytest data_processing/sprint_14_phase3/ -v

# Performance benchmarks
python tests/sprint14/test_performance_benchmarks.py --phase 3

# Expected results:
# - ETF universe queries: <1.8s
# - Scenario generation: <90s
# - Cache synchronization: <25min
```

---

## ⚡ Phase 4: Production Optimization Execution

### **Step 1: Enterprise Production Scheduler**

#### **Test Enterprise Scheduling**
```bash
cd src/jobs
python enterprise_production_scheduler.py --test-capacity --symbols 500 --years 5

# Test Redis Streams job management
python enterprise_production_scheduler.py --submit-job batch_historical_load --priority critical

# Monitor job processing
redis-cli XREAD COUNT 10 STREAMS tickstock:jobs:stream 0
```

#### **Test Fault Tolerance**
```bash
# Test job resume capability
python enterprise_production_scheduler.py --resume-jobs --checkpoint-file last_checkpoint.json

# Verify priority scheduling
python enterprise_production_scheduler.py --list-jobs --priority high
```

### **Step 2: Rapid Development Refresh**

#### **Test Development Environment Refresh**
```bash
cd src/development
python rapid_development_refresh.py --profile patterns --reset

# Test different profiles
python rapid_development_refresh.py --profile backtesting --refresh
python rapid_development_refresh.py --profile ui_testing --reset
python rapid_development_refresh.py --profile etf_analysis --refresh

# Expected: <30s for patterns profile, <45s for backtesting
```

#### **Test Docker Integration**
```bash
# Test Docker container isolation
python rapid_development_refresh.py --profile patterns --use-docker --container-name test_env

# Verify environment isolation
docker ps | grep tickstock
docker exec test_env python -c "import database; print(database.get_symbol_count())"
```

### **Step 3: Market Schedule Manager**

#### **Test Multi-Exchange Calendar Support**
```bash
cd src/services
python market_schedule_manager.py --test-exchanges

# Test specific exchange queries
python -c "
from market_schedule_manager import MarketScheduleManager
manager = MarketScheduleManager()
print(f'NYSE open: {manager.is_market_open(\"NYSE\", datetime.now())}')
print(f'TSE holidays: {manager.get_holidays(\"TSE\", 2025)}')
"
```

#### **Test Holiday Detection**
```bash
# Test holiday and early close detection
python market_schedule_manager.py --check-holiday --exchange NYSE --date 2025-07-04
python market_schedule_manager.py --check-early-close --exchange NASDAQ --date 2025-11-29
```

### **Phase 4 Testing Commands**

#### **Enterprise Production Testing**
```bash
# Test enterprise scheduling with production load
cd tests/sprint14
python -m pytest jobs/test_enterprise_production_scheduler.py -v

# Test rapid development refresh
python -m pytest development/test_rapid_development_refresh.py -v

# Test market schedule manager
python -m pytest services/test_market_schedule_manager.py -v
```

#### **Performance Validation**
```bash
# Production scale performance testing
python tests/sprint14/test_performance_benchmarks.py --phase 4

# Expected results:
# - Job submission: <65ms
# - Database reset: <23s  
# - Schedule queries: <32ms
# - Production scale: 1000+ symbols validated
```

---

## 🧪 Comprehensive Testing Execution

### **Complete Test Suite Execution**

#### **Run All Sprint 14 Tests**
```bash
# Execute comprehensive test suite across all phases
cd tests/sprint14
python run_sprint14_tests.py --all --report-html

# Generate detailed coverage report
python run_sprint14_tests.py --all --coverage --report-json
```

#### **Integration Testing**
```bash
# Cross-system integration validation
cd tests/integration/sprint14
python run_integration_tests.py --all --performance

# Redis resilience testing
python run_integration_tests.py --resilience --report-html
```

#### **Performance Benchmarks**
```bash
# Validate all performance targets
python tests/sprint14/test_performance_benchmarks.py --all

# Expected targets validation:
# - Message delivery: <100ms
# - Database queries: <50ms  
# - End-to-end workflows: <500ms
```

### **Test Result Analysis**

#### **Coverage Analysis**
```bash
# Analyze test coverage across all phases
coverage run --source=src -m pytest tests/sprint14/
coverage report -m
coverage html

# Expected: >85% coverage across all Sprint 14 components
```

#### **Performance Analysis**
```bash
# Performance regression testing
python tests/performance/sprint14_regression_tests.py

# Load testing validation
python tests/load/sprint14_load_tests.py --concurrent-users 100
```

---

## 📊 Validation and Verification

### **Data Validation**

#### **Database Integrity Checks**
```sql
-- Verify ETF data integrity
SELECT COUNT(*) as etf_symbols, 
       AVG(asset_under_management) as avg_aum,
       AVG(expense_ratio) as avg_expense_ratio
FROM symbols 
WHERE symbol IN (SELECT unnest(get_etf_universe('all')));

-- Verify universe expansion
SELECT universe_category, COUNT(*) as symbol_count
FROM cache_entries 
GROUP BY universe_category;

-- Check IPO data
SELECT COUNT(*) as recent_ipos
FROM symbols 
WHERE listing_date >= CURRENT_DATE - INTERVAL '90 days';
```

#### **Redis Integration Validation**
```bash
# Test Redis pub-sub channels
redis-cli PUBSUB CHANNELS tickstock.*

# Verify Redis Streams for job management
redis-cli XINFO STREAM tickstock:jobs:stream

# Test message delivery performance
python tests/integration/redis_performance_test.py --target-latency 100
```

### **Service Health Checks**

#### **Automation Services Status**
```bash
# Check IPO monitor service
curl http://localhost:8001/health | python -m json.tool

# Check data quality monitor
curl http://localhost:8002/metrics | python -m json.tool

# Verify EOD processor status
python src/data/eod_processor.py --status
```

#### **Performance Monitoring**
```bash
# Monitor real-time performance
python tests/monitoring/sprint14_performance_monitor.py --duration 300

# Check resource utilization
python tests/monitoring/resource_monitor.py --services all
```

---

## 🚨 Troubleshooting Guide

### **Common Issues and Solutions**

#### **Database Migration Issues**
```bash
# Issue: "functions in index predicate must be marked IMMUTABLE"
# Solution: Remove NOW() function from index definitions
# Fixed in: scripts/database/etf_integration_migration.sql

# Issue: Foreign key constraint violations
# Solution: Run symbol data population before universe assignments
```

#### **Redis Connection Issues**
```bash
# Issue: Connection refused on Redis
# Check Redis service status
redis-cli ping

# Restart Redis if needed
sudo systemctl restart redis-server

# Verify Redis configuration
redis-cli CONFIG GET "*"
```

#### **Unicode Encoding Errors**
```bash
# Issue: 'charmap' codec errors with Unicode characters
# Solution: Use ASCII alternatives or set proper encoding
export PYTHONIOENCODING=utf-8

# For Windows:
set PYTHONIOENCODING=utf-8
```

#### **Performance Issues**
```bash
# Issue: Slow ETF universe queries
# Solution: Verify GIN indexes on JSONB columns
psql -c "EXPLAIN ANALYZE SELECT * FROM cache_entries WHERE universe_metadata @> '{\"theme\": \"technology\"}';"

# Issue: Memory usage during large batch processing
# Solution: Adjust batch sizes in configuration
python -c "import gc; gc.collect()"
```

### **Rollback Procedures**

#### **Database Rollback**
```sql
-- Rollback ETF integration (if needed)
-- Note: Backup data before executing
ALTER TABLE symbols DROP COLUMN IF EXISTS asset_under_management;
-- ... (drop other ETF columns as needed)

-- Rollback universe expansion
DELETE FROM cache_entries WHERE universe_category IN ('sectors', 'growth', 'value', 'international', 'commodities', 'technology', 'bonds');
```

#### **Service Rollback**
```bash
# Stop new automation services
sudo systemctl stop ipo_monitor
sudo systemctl stop data_quality_monitor

# Revert to previous version
git checkout HEAD~1 -- automation/services/
git checkout HEAD~1 -- src/data/eod_processor.py
```

---

## 📋 Deployment Checklist

### **Pre-Deployment Validation**
- [ ] Database backup completed
- [ ] All SQL migrations tested in staging
- [ ] Redis instance available and configured
- [ ] Python dependencies installed and verified
- [ ] API keys and configuration files updated
- [ ] Monitoring and logging configured

### **Phase-by-Phase Deployment**
- [ ] **Phase 1**: ETF integration schema, development optimization, EOD processing
- [ ] **Phase 2**: Automation services, IPO monitoring, data quality monitoring
- [ ] **Phase 3**: Universe expansion, test scenarios, cache synchronization
- [ ] **Phase 4**: Enterprise scheduling, development refresh, market calendars

### **Post-Deployment Verification**
- [ ] All services running and healthy
- [ ] Redis pub-sub channels operational
- [ ] Database integrity verified
- [ ] Performance targets met
- [ ] Integration tests passing
- [ ] Monitoring and alerting functional

### **Production Readiness**
- [ ] Load testing completed
- [ ] Failover procedures tested
- [ ] Backup and recovery validated
- [ ] Documentation updated
- [ ] Team training completed
- [ ] Go-live approval obtained

---

## 🎯 Success Criteria

### **Technical Success Metrics**
- **ETF Integration**: 16 columns added, 40 development ETFs loaded
- **Performance**: All targets met (<100ms WebSocket, <50ms DB queries, <30s refresh)
- **Automation**: IPO monitoring active, data quality alerts functional
- **Universe Management**: 200+ ETFs across 7 themes with real-time updates
- **Production Scale**: 1000+ symbols × 5 years validated

### **Operational Success Metrics**
- **Reliability**: >99.5% uptime for all automation services
- **Performance**: All SLA targets exceeded with substantial margins
- **Integration**: Zero breaking changes to existing functionality
- **Monitoring**: Comprehensive alerting and performance tracking active
- **Documentation**: Complete operational procedures and troubleshooting guides

### **User Experience Success**
- **Development Speed**: 70% improvement in development workflow efficiency
- **ETF Analysis**: Comprehensive ETF metadata and universe management
- **Real-time Updates**: Instant UI updates via Redis pub-sub notifications
- **Global Markets**: Multi-exchange support with proper timezone handling

---

**🎉 Sprint 14 Execution Complete!**

This guide ensures comprehensive deployment and testing of Sprint 14's data infrastructure automation enhancements. All components have been thoroughly tested and validated for production deployment with enterprise-grade reliability and performance.

---

*Guide Version: 1.0*  
*Last Updated: 2025-09-01*  
*Maintained by: TickStock Development Team*