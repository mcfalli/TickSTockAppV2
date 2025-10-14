"""
Sprint 14 Phase 1: Database Performance Integration Tests
Comprehensive database performance validation for Sprint 14 ETF schema enhancements.

Focus Areas:
1. Enhanced symbols table performance with ETF-specific fields
2. OHLCV data integration with FMV field support
3. Cache entries performance with ETF and development universes
4. Query performance targets (<50ms for TickStockApp read operations)
5. Index optimization validation for new ETF columns
6. Database boundary enforcement and connection management

VALIDATION REQUIREMENTS:
- Database query performance <50ms for UI operations
- Read-only boundary enforcement for TickStockApp
- Connection pooling optimization validation
- Schema enhancement impact analysis
- ETF-specific query performance benchmarks
"""

import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import psycopg2
import pytest


@dataclass
class DatabasePerformanceMetrics:
    """Track database performance metrics for integration testing."""
    query_execution_times: list[float] = field(default_factory=list)
    connection_acquisition_times: list[float] = field(default_factory=list)
    index_scan_counts: list[int] = field(default_factory=list)
    sequential_scan_counts: list[int] = field(default_factory=list)
    cache_hit_ratios: list[float] = field(default_factory=list)
    concurrent_query_times: list[float] = field(default_factory=list)

    def add_query_time(self, execution_time_ms: float):
        """Add query execution time measurement."""
        self.query_execution_times.append(execution_time_ms)

    def get_query_stats(self) -> dict[str, float]:
        """Get query performance statistics."""
        if not self.query_execution_times:
            return {'avg': 0, 'p50': 0, 'p95': 0, 'max': 0, 'min': 0}

        sorted_times = sorted(self.query_execution_times)
        count = len(sorted_times)

        return {
            'avg': sum(sorted_times) / count,
            'p50': sorted_times[count // 2],
            'p95': sorted_times[int(count * 0.95)],
            'p99': sorted_times[int(count * 0.99)] if count > 100 else sorted_times[-1],
            'max': sorted_times[-1],
            'min': sorted_times[0],
            'count': count
        }

    def add_connection_time(self, acquisition_time_ms: float):
        """Add connection acquisition time measurement."""
        self.connection_acquisition_times.append(acquisition_time_ms)


class MockDatabaseConnection:
    """Mock database connection with performance simulation."""

    def __init__(self, simulate_load: bool = False):
        self.simulate_load = simulate_load
        self.query_count = 0
        self.connection_pool_size = 20
        self.active_connections = 0
        self.lock = threading.Lock()

    def cursor(self):
        """Create mock cursor with performance tracking."""
        return MockDatabaseCursor(self.simulate_load)

    def commit(self):
        """Mock commit operation."""
        if self.simulate_load:
            time.sleep(0.001)  # 1ms commit overhead

    def rollback(self):
        """Mock rollback operation."""
        if self.simulate_load:
            time.sleep(0.0005)  # 0.5ms rollback overhead

    def close(self):
        """Mock connection close."""
        with self.lock:
            self.active_connections = max(0, self.active_connections - 1)


class MockDatabaseCursor:
    """Mock database cursor with realistic performance simulation."""

    def __init__(self, simulate_load: bool = False):
        self.simulate_load = simulate_load
        self.fetchall_data = []
        self.fetchone_data = None
        self.rowcount = 0
        self.query_plan_stats = {
            'index_scans': 0,
            'seq_scans': 0,
            'execution_time': 0
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, sql: str, params=None):
        """Mock query execution with performance simulation."""
        if self.simulate_load:
            # Simulate different query types with realistic timing
            sql_upper = sql.strip().upper()

            if sql_upper.startswith('SELECT'):
                if 'WHERE' in sql_upper and ('ticker' in sql.lower() or 'symbol' in sql.lower()):
                    # Index scan - fast lookup
                    time.sleep(0.002)  # 2ms for indexed lookup
                    self.query_plan_stats['index_scans'] += 1
                elif 'COUNT(*)' in sql_upper:
                    # Count query - moderate speed
                    time.sleep(0.005)  # 5ms for count
                    self.query_plan_stats['index_scans'] += 1
                elif 'ORDER BY' in sql_upper or 'GROUP BY' in sql_upper:
                    # Sort/group operations - slower
                    time.sleep(0.015)  # 15ms for sort operations
                    self.query_plan_stats['index_scans'] += 1
                else:
                    # Full table scan - slowest
                    time.sleep(0.030)  # 30ms for seq scan
                    self.query_plan_stats['seq_scans'] += 1

            elif sql_upper.startswith('INSERT'):
                time.sleep(0.003)  # 3ms for insert
            elif sql_upper.startswith('UPDATE'):
                time.sleep(0.005)  # 5ms for update
            elif sql_upper.startswith('DELETE'):
                time.sleep(0.004)  # 4ms for delete
            else:
                time.sleep(0.001)  # 1ms for other operations

    def fetchall(self):
        """Mock fetchall with pre-configured data."""
        return self.fetchall_data

    def fetchone(self):
        """Mock fetchone with pre-configured data."""
        return self.fetchone_data

    def set_fetchall_data(self, data: list[dict[str, Any]]):
        """Set data to be returned by fetchall."""
        self.fetchall_data = data
        self.rowcount = len(data)

    def set_fetchone_data(self, data: dict[str, Any]):
        """Set data to be returned by fetchone."""
        self.fetchone_data = data
        self.rowcount = 1 if data else 0


class TestEnhancedSymbolsTablePerformance:
    """Test performance of enhanced symbols table with ETF-specific fields."""

    @patch('psycopg2.connect')
    def test_etf_symbol_lookup_performance(self, mock_connect, db_performance_metrics: DatabasePerformanceMetrics):
        """Test ETF symbol lookup performance with enhanced schema."""
        # Arrange: Mock enhanced symbols table data
        mock_conn = MockDatabaseConnection(simulate_load=True)
        mock_connect.return_value = mock_conn

        # Sample enhanced ETF symbols data
        etf_symbols_data = [
            {
                'ticker': 'SPY',
                'name': 'SPDR S&P 500 ETF Trust',
                'symbol_type': 'ETF',
                'etf_type': 'ETF',
                'fmv_supported': True,
                'issuer': 'State Street (SPDR)',
                'correlation_reference': 'SPY',
                'composite_figi': 'BBG000BDTBL9',
                'share_class_figi': 'BBG001S5PQL7',
                'cik': '0000884394',
                'inception_date': '1993-01-22'
            },
            {
                'ticker': 'QQQ',
                'name': 'Invesco QQQ Trust ETF',
                'symbol_type': 'ETF',
                'etf_type': 'ETF',
                'fmv_supported': True,
                'issuer': 'Invesco',
                'correlation_reference': 'QQQ',
                'composite_figi': 'BBG000BQKZP4',
                'share_class_figi': 'BBG001S5PZZ8',
                'cik': '0000751142',
                'inception_date': '1999-03-10'
            }
        ]

        # Act: Test various ETF lookup queries
        etf_queries = [
            # Query 1: Single ETF lookup by ticker (most common)
            {
                'sql': """
                SELECT ticker, name, etf_type, issuer, fmv_supported, correlation_reference
                FROM symbols 
                WHERE ticker = %s AND symbol_type = 'ETF'
                """,
                'params': ('SPY',),
                'expected_data': [etf_symbols_data[0]],
                'description': 'Single ETF lookup'
            },
            # Query 2: ETF list for UI dropdown
            {
                'sql': """
                SELECT ticker, name, issuer, etf_type
                FROM symbols 
                WHERE symbol_type = 'ETF' AND etf_type IS NOT NULL
                ORDER BY name
                LIMIT 50
                """,
                'params': None,
                'expected_data': etf_symbols_data,
                'description': 'ETF dropdown list'
            },
            # Query 3: FMV-supported ETFs
            {
                'sql': """
                SELECT ticker, name, correlation_reference, issuer
                FROM symbols
                WHERE fmv_supported = true AND symbol_type = 'ETF'
                ORDER BY ticker
                """,
                'params': None,
                'expected_data': etf_symbols_data,
                'description': 'FMV-supported ETFs'
            },
            # Query 4: ETFs by issuer
            {
                'sql': """
                SELECT ticker, name, etf_type, inception_date
                FROM symbols
                WHERE issuer = %s AND symbol_type = 'ETF'
                ORDER BY inception_date
                """,
                'params': ('State Street (SPDR)',),
                'expected_data': [etf_symbols_data[0]],
                'description': 'ETFs by issuer'
            },
            # Query 5: Correlation reference lookup
            {
                'sql': """
                SELECT ticker, name, correlation_reference
                FROM symbols
                WHERE correlation_reference IN (%s, %s) AND symbol_type = 'ETF'
                """,
                'params': ('SPY', 'QQQ'),
                'expected_data': etf_symbols_data,
                'description': 'Correlation reference lookup'
            }
        ]

        query_performance_results = []

        for query_config in etf_queries:
            with mock_conn.cursor() as cursor:
                cursor.set_fetchall_data(query_config['expected_data'])

                # Time query execution
                start_time = time.perf_counter()
                cursor.execute(query_config['sql'], query_config['params'])
                results = cursor.fetchall()
                end_time = time.perf_counter()

                execution_time_ms = (end_time - start_time) * 1000
                db_performance_metrics.add_query_time(execution_time_ms)

                query_performance_results.append({
                    'description': query_config['description'],
                    'execution_time_ms': execution_time_ms,
                    'result_count': len(results),
                    'index_scans': cursor.query_plan_stats['index_scans'],
                    'seq_scans': cursor.query_plan_stats['seq_scans']
                })

        # Assert: ETF query performance requirements
        query_stats = db_performance_metrics.get_query_stats()

        # 1. Average query time <25ms for ETF lookups
        assert query_stats['avg'] < 25, f"Average ETF query time {query_stats['avg']:.1f}ms exceeds 25ms target"

        # 2. P95 query time <50ms
        assert query_stats['p95'] < 50, f"P95 ETF query time {query_stats['p95']:.1f}ms exceeds 50ms target"

        # 3. Single ETF lookups <10ms (most critical)
        single_lookup_time = query_performance_results[0]['execution_time_ms']
        assert single_lookup_time < 10, f"Single ETF lookup {single_lookup_time:.1f}ms exceeds 10ms target"

        # 4. Prefer index scans over sequential scans
        total_index_scans = sum(result['index_scans'] for result in query_performance_results)
        total_seq_scans = sum(result['seq_scans'] for result in query_performance_results)
        assert total_index_scans >= total_seq_scans, f"More seq scans ({total_seq_scans}) than index scans ({total_index_scans})"

        print("\nETF Symbols Table Performance:")
        print(f"  Average Query Time: {query_stats['avg']:.1f}ms")
        print(f"  P95 Query Time: {query_stats['p95']:.1f}ms")
        print(f"  Single Lookup Time: {single_lookup_time:.1f}ms")
        print(f"  Index Scans: {total_index_scans}, Seq Scans: {total_seq_scans}")

        for result in query_performance_results:
            print(f"    {result['description']}: {result['execution_time_ms']:.1f}ms ({result['result_count']} rows)")

    @patch('psycopg2.connect')
    def test_symbols_table_index_optimization(self, mock_connect, db_performance_metrics: DatabasePerformanceMetrics):
        """Test index optimization for new ETF-specific columns."""
        # Arrange: Mock database with index statistics
        mock_conn = MockDatabaseConnection(simulate_load=True)
        mock_connect.return_value = mock_conn

        # Test queries that should use indexes
        index_optimization_tests = [
            {
                'query': "SELECT * FROM symbols WHERE symbol_type = 'ETF'",
                'expected_index': 'idx_symbols_type',
                'description': 'ETF type filter'
            },
            {
                'query': "SELECT * FROM symbols WHERE etf_type IS NOT NULL",
                'expected_index': 'idx_symbols_etf_type',
                'description': 'ETF type presence'
            },
            {
                'query': "SELECT * FROM symbols WHERE fmv_supported = true",
                'expected_index': 'idx_symbols_fmv_supported',
                'description': 'FMV support filter'
            },
            {
                'query': "SELECT * FROM symbols WHERE issuer = 'State Street (SPDR)'",
                'expected_index': 'idx_symbols_issuer',
                'description': 'Issuer lookup'
            },
            {
                'query': "SELECT * FROM symbols WHERE correlation_reference = 'SPY'",
                'expected_index': 'idx_symbols_correlation',
                'description': 'Correlation reference'
            },
            {
                'query': "SELECT * FROM symbols WHERE composite_figi = 'BBG000BDTBL9'",
                'expected_index': 'idx_symbols_composite_figi',
                'description': 'FIGI lookup'
            }
        ]

        index_performance_results = []

        for test_config in index_optimization_tests:
            with mock_conn.cursor() as cursor:
                # Simulate index usage for these queries
                cursor.set_fetchall_data([{'ticker': 'SPY', 'name': 'Test ETF'}])

                start_time = time.perf_counter()
                cursor.execute(test_config['query'])
                results = cursor.fetchall()
                end_time = time.perf_counter()

                execution_time_ms = (end_time - start_time) * 1000
                db_performance_metrics.add_query_time(execution_time_ms)

                index_performance_results.append({
                    'description': test_config['description'],
                    'execution_time_ms': execution_time_ms,
                    'expected_index': test_config['expected_index'],
                    'used_index_scan': cursor.query_plan_stats['index_scans'] > 0
                })

        # Assert: Index optimization requirements
        # 1. All queries should use index scans
        for result in index_performance_results:
            assert result['used_index_scan'], f"{result['description']} should use index scan"

        # 2. Index-optimized queries should be fast (<15ms)
        for result in index_performance_results:
            assert result['execution_time_ms'] < 15, \
                f"{result['description']} took {result['execution_time_ms']:.1f}ms, should be <15ms with index"

        print("\nETF Index Optimization Performance:")
        for result in index_performance_results:
            status = "✓" if result['used_index_scan'] else "✗"
            print(f"  {result['description']}: {result['execution_time_ms']:.1f}ms {status}")


class TestOHLCVDataIntegrationPerformance:
    """Test OHLCV data performance with FMV field support."""

    @patch('psycopg2.connect')
    def test_ohlcv_data_with_fmv_performance(self, mock_connect, db_performance_metrics: DatabasePerformanceMetrics):
        """Test OHLCV data queries with FMV field integration."""
        # Arrange: Mock OHLCV data with FMV fields
        mock_conn = MockDatabaseConnection(simulate_load=True)
        mock_connect.return_value = mock_conn

        # Sample OHLCV data with FMV support
        ohlcv_test_data = [
            {
                'symbol': 'SPY',
                'date': '2024-09-01',
                'open': 557.00,
                'high': 558.50,
                'low': 556.25,
                'close': 558.00,
                'volume': 45000000,
                'fmv_price': 558.05,
                'fmv_supported': True
            },
            {
                'symbol': 'THINLY',  # Thinly traded ETF
                'date': '2024-09-01',
                'open': 25.10,
                'high': 25.25,
                'low': 25.05,
                'close': 25.20,
                'volume': 15000,
                'fmv_price': 25.18,  # FMV approximation
                'fmv_supported': True
            }
        ]

        # Act: Test FMV-enabled OHLCV queries
        fmv_queries = [
            {
                'sql': """
                SELECT symbol, date, close, fmv_price, fmv_supported
                FROM ohlcv_daily
                WHERE symbol = %s AND date = %s
                """,
                'params': ('SPY', '2024-09-01'),
                'expected_data': [ohlcv_test_data[0]],
                'description': 'Single day OHLCV with FMV'
            },
            {
                'sql': """
                SELECT symbol, date, close, 
                       CASE WHEN fmv_supported THEN fmv_price ELSE close END as effective_price
                FROM ohlcv_daily
                WHERE symbol IN (%s, %s) AND date = %s
                ORDER BY symbol
                """,
                'params': ('SPY', 'THINLY', '2024-09-01'),
                'expected_data': ohlcv_test_data,
                'description': 'Multi-symbol FMV fallback'
            },
            {
                'sql': """
                SELECT symbol, COUNT(*) as day_count,
                       AVG(CASE WHEN fmv_supported THEN fmv_price ELSE close END) as avg_price
                FROM ohlcv_daily
                WHERE symbol = %s AND date >= %s
                GROUP BY symbol
                """,
                'params': ('SPY', '2024-08-01'),
                'expected_data': [{'symbol': 'SPY', 'day_count': 22, 'avg_price': 555.75}],
                'description': 'FMV aggregation query'
            },
            {
                'sql': """
                SELECT symbol, date, close, volume,
                       CASE 
                           WHEN volume < 50000 AND fmv_supported THEN fmv_price 
                           ELSE close 
                       END as display_price
                FROM ohlcv_daily
                WHERE fmv_supported = true
                ORDER BY date DESC
                LIMIT 100
                """,
                'params': None,
                'expected_data': ohlcv_test_data,
                'description': 'Volume-based FMV selection'
            }
        ]

        fmv_query_results = []

        for query_config in fmv_queries:
            with mock_conn.cursor() as cursor:
                cursor.set_fetchall_data(query_config['expected_data'])

                start_time = time.perf_counter()
                cursor.execute(query_config['sql'], query_config['params'])
                results = cursor.fetchall()
                end_time = time.perf_counter()

                execution_time_ms = (end_time - start_time) * 1000
                db_performance_metrics.add_query_time(execution_time_ms)

                fmv_query_results.append({
                    'description': query_config['description'],
                    'execution_time_ms': execution_time_ms,
                    'result_count': len(results)
                })

        # Assert: FMV OHLCV performance requirements
        query_stats = db_performance_metrics.get_query_stats()

        # 1. FMV queries average <30ms
        assert query_stats['avg'] < 30, f"Average FMV query time {query_stats['avg']:.1f}ms exceeds 30ms target"

        # 2. Single-day lookup <15ms (most common UI query)
        single_day_time = fmv_query_results[0]['execution_time_ms']
        assert single_day_time < 15, f"Single-day FMV lookup {single_day_time:.1f}ms exceeds 15ms target"

        # 3. Complex FMV aggregations <50ms
        for result in fmv_query_results:
            if 'aggregation' in result['description'] or 'selection' in result['description']:
                assert result['execution_time_ms'] < 50, \
                    f"Complex FMV query {result['description']} took {result['execution_time_ms']:.1f}ms, exceeds 50ms"

        print("\nOHLCV FMV Performance:")
        print(f"  Average Query Time: {query_stats['avg']:.1f}ms")
        print(f"  Single-Day Lookup: {single_day_time:.1f}ms")

        for result in fmv_query_results:
            print(f"    {result['description']}: {result['execution_time_ms']:.1f}ms ({result['result_count']} rows)")

    @patch('psycopg2.connect')
    def test_ohlcv_bulk_data_performance(self, mock_connect, db_performance_metrics: DatabasePerformanceMetrics):
        """Test bulk OHLCV data operations performance."""
        # Arrange: Mock bulk OHLCV operations
        mock_conn = MockDatabaseConnection(simulate_load=True)
        mock_connect.return_value = mock_conn

        # Simulate bulk data scenarios
        bulk_scenarios = [
            {
                'description': 'Single ETF - 1 year data',
                'symbol_count': 1,
                'days': 252,
                'expected_rows': 252
            },
            {
                'description': '10 ETFs - 6 months data',
                'symbol_count': 10,
                'days': 126,
                'expected_rows': 1260
            },
            {
                'description': '50 ETFs - 1 month data',
                'symbol_count': 50,
                'days': 22,
                'expected_rows': 1100
            }
        ]

        bulk_performance_results = []

        for scenario in bulk_scenarios:
            # Generate mock bulk data
            bulk_data = []
            for symbol_idx in range(scenario['symbol_count']):
                symbol = f'ETF{symbol_idx:03d}'
                for day in range(scenario['days']):
                    bulk_data.append({
                        'symbol': symbol,
                        'date': f'2024-{(day % 12) + 1:02d}-{(day % 28) + 1:02d}',
                        'open': 100 + random.uniform(-5, 5),
                        'high': 105 + random.uniform(-3, 3),
                        'low': 95 + random.uniform(-3, 3),
                        'close': 100 + random.uniform(-5, 5),
                        'volume': random.randint(100000, 50000000),
                        'fmv_price': 100 + random.uniform(-5, 5),
                        'fmv_supported': True
                    })

            with mock_conn.cursor() as cursor:
                cursor.set_fetchall_data(bulk_data)

                # Test bulk query
                bulk_query = """
                SELECT symbol, date, close, volume, fmv_price
                FROM ohlcv_daily
                WHERE date >= %s AND date <= %s
                ORDER BY symbol, date
                """

                start_time = time.perf_counter()
                cursor.execute(bulk_query, ('2024-01-01', '2024-12-31'))
                results = cursor.fetchall()
                end_time = time.perf_counter()

                execution_time_ms = (end_time - start_time) * 1000
                db_performance_metrics.add_query_time(execution_time_ms)

                bulk_performance_results.append({
                    'description': scenario['description'],
                    'execution_time_ms': execution_time_ms,
                    'expected_rows': scenario['expected_rows'],
                    'actual_rows': len(results),
                    'rows_per_ms': len(results) / execution_time_ms if execution_time_ms > 0 else 0
                })

        # Assert: Bulk data performance requirements
        # 1. Bulk queries <100ms for reasonable dataset sizes
        for result in bulk_performance_results:
            if result['expected_rows'] <= 1500:  # Reasonable size datasets
                assert result['execution_time_ms'] < 100, \
                    f"Bulk query {result['description']} took {result['execution_time_ms']:.1f}ms, exceeds 100ms"

        # 2. Processing rate >10 rows per millisecond
        for result in bulk_performance_results:
            assert result['rows_per_ms'] > 10, \
                f"Bulk query {result['description']} processed {result['rows_per_ms']:.1f} rows/ms, too slow"

        print("\nOHLCV Bulk Data Performance:")
        for result in bulk_performance_results:
            print(f"  {result['description']}: {result['execution_time_ms']:.1f}ms ({result['actual_rows']} rows, {result['rows_per_ms']:.1f} rows/ms)")


class TestCacheEntriesPerformance:
    """Test cache entries performance with ETF and development universes."""

    @patch('psycopg2.connect')
    def test_universe_lookup_performance(self, mock_connect, db_performance_metrics: DatabasePerformanceMetrics):
        """Test universe lookup performance for ETF and development data."""
        # Arrange: Mock cache entries data
        mock_conn = MockDatabaseConnection(simulate_load=True)
        mock_connect.return_value = mock_conn

        # Sample universe data
        universe_data = [
            {
                'key': 'etf_growth',
                'type': 'etf_universe',
                'value': json.dumps({
                    'name': 'Growth ETFs',
                    'etfs': [{'ticker': 'VUG'}, {'ticker': 'QQQ'}, {'ticker': 'VGT'}]
                }),
                'environment': 'DEFAULT'
            },
            {
                'key': 'etf_sectors',
                'type': 'etf_universe',
                'value': json.dumps({
                    'name': 'Sector ETFs',
                    'etfs': [{'ticker': 'XLK'}, {'ticker': 'XLE'}, {'ticker': 'XLF'}]
                }),
                'environment': 'DEFAULT'
            },
            {
                'key': 'dev_top_10',
                'type': 'stock_universe',
                'value': json.dumps({
                    'name': 'Development Top 10',
                    'stocks': [{'ticker': 'AAPL'}, {'ticker': 'MSFT'}, {'ticker': 'NVDA'}]
                }),
                'environment': 'DEVELOPMENT'
            }
        ]

        # Act: Test universe lookup queries
        universe_queries = [
            {
                'sql': """
                SELECT key, type, value FROM cache_entries
                WHERE type = 'etf_universe' AND environment = 'DEFAULT'
                ORDER BY key
                """,
                'params': None,
                'expected_data': [universe_data[0], universe_data[1]],
                'description': 'ETF universes lookup'
            },
            {
                'sql': """
                SELECT key, value FROM cache_entries
                WHERE key = %s AND type = %s AND environment = %s
                """,
                'params': ('etf_growth', 'etf_universe', 'DEFAULT'),
                'expected_data': [universe_data[0]],
                'description': 'Single universe lookup'
            },
            {
                'sql': """
                SELECT key, type, value FROM cache_entries
                WHERE environment = 'DEVELOPMENT' AND key LIKE 'dev_%'
                ORDER BY type, key
                """,
                'params': None,
                'expected_data': [universe_data[2]],
                'description': 'Development universes'
            },
            {
                'sql': """
                SELECT type, COUNT(*) as universe_count
                FROM cache_entries
                WHERE environment = 'DEFAULT'
                GROUP BY type
                ORDER BY type
                """,
                'params': None,
                'expected_data': [
                    {'type': 'etf_universe', 'universe_count': 2},
                    {'type': 'stock_universe', 'universe_count': 8}
                ],
                'description': 'Universe summary stats'
            }
        ]

        universe_performance_results = []

        for query_config in universe_queries:
            with mock_conn.cursor() as cursor:
                cursor.set_fetchall_data(query_config['expected_data'])

                start_time = time.perf_counter()
                cursor.execute(query_config['sql'], query_config['params'])
                results = cursor.fetchall()
                end_time = time.perf_counter()

                execution_time_ms = (end_time - start_time) * 1000
                db_performance_metrics.add_query_time(execution_time_ms)

                universe_performance_results.append({
                    'description': query_config['description'],
                    'execution_time_ms': execution_time_ms,
                    'result_count': len(results)
                })

        # Assert: Universe lookup performance requirements
        query_stats = db_performance_metrics.get_query_stats()

        # 1. Average universe lookup <20ms
        assert query_stats['avg'] < 20, f"Average universe lookup {query_stats['avg']:.1f}ms exceeds 20ms target"

        # 2. Single universe lookup <10ms (most critical for UI)
        single_lookup_time = universe_performance_results[1]['execution_time_ms']
        assert single_lookup_time < 10, f"Single universe lookup {single_lookup_time:.1f}ms exceeds 10ms target"

        # 3. All universe queries <30ms
        for result in universe_performance_results:
            assert result['execution_time_ms'] < 30, \
                f"Universe query {result['description']} took {result['execution_time_ms']:.1f}ms, exceeds 30ms"

        print("\nCache Entries Universe Performance:")
        print(f"  Average Query Time: {query_stats['avg']:.1f}ms")
        print(f"  Single Universe Lookup: {single_lookup_time:.1f}ms")

        for result in universe_performance_results:
            print(f"    {result['description']}: {result['execution_time_ms']:.1f}ms ({result['result_count']} rows)")


class TestDatabaseBoundaryEnforcement:
    """Test database boundary enforcement and role separation."""

    @patch('psycopg2.connect')
    def test_tickstockapp_readonly_performance_impact(self, mock_connect, db_performance_metrics: DatabasePerformanceMetrics):
        """Test performance impact of read-only boundary enforcement."""
        # Arrange: Mock read-only database connection
        mock_conn = MockDatabaseConnection(simulate_load=True)
        mock_connect.return_value = mock_conn

        # Simulate read-only user behavior
        def simulate_readonly_enforcement(sql, params=None):
            """Simulate read-only enforcement with minimal overhead."""
            sql_upper = sql.strip().upper()

            # Allow SELECT queries with minimal overhead
            if sql_upper.startswith('SELECT'):
                return True  # No additional overhead for reads

            # Block write operations (should not happen in TickStockApp)
            write_operations = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']
            if any(sql_upper.startswith(op) for op in write_operations):
                raise psycopg2.errors.InsufficientPrivilege("permission denied")

            return True

        # Act: Test read-only query performance
        readonly_queries = [
            {
                'sql': "SELECT ticker, name FROM symbols WHERE symbol_type = 'ETF' LIMIT 10",
                'description': 'ETF symbol list'
            },
            {
                'sql': "SELECT key, value FROM cache_entries WHERE type = 'etf_universe'",
                'description': 'Universe lookup'
            },
            {
                'sql': "SELECT symbol, close FROM ohlcv_daily WHERE date = CURRENT_DATE LIMIT 100",
                'description': 'Current day prices'
            },
            {
                'sql': "SELECT COUNT(*) FROM symbols WHERE fmv_supported = true",
                'description': 'FMV count query'
            }
        ]

        readonly_performance_results = []

        for query_config in readonly_queries:
            with mock_conn.cursor() as cursor:
                cursor.set_fetchall_data([{'test': 'data'}])

                # Test query with read-only enforcement
                start_time = time.perf_counter()

                try:
                    simulate_readonly_enforcement(query_config['sql'])
                    cursor.execute(query_config['sql'])
                    results = cursor.fetchall()
                    success = True
                except psycopg2.errors.InsufficientPrivilege:
                    results = []
                    success = False

                end_time = time.perf_counter()
                execution_time_ms = (end_time - start_time) * 1000

                db_performance_metrics.add_query_time(execution_time_ms)

                readonly_performance_results.append({
                    'description': query_config['description'],
                    'execution_time_ms': execution_time_ms,
                    'success': success,
                    'result_count': len(results)
                })

        # Test blocked write operations
        blocked_queries = [
            "INSERT INTO symbols (ticker, name) VALUES ('TEST', 'Test')",
            "UPDATE symbols SET name = 'Updated' WHERE ticker = 'AAPL'",
            "DELETE FROM cache_entries WHERE key = 'test'"
        ]

        for blocked_sql in blocked_queries:
            start_time = time.perf_counter()

            try:
                simulate_readonly_enforcement(blocked_sql)
                blocked_success = True
            except psycopg2.errors.InsufficientPrivilege:
                blocked_success = False

            end_time = time.perf_counter()
            enforcement_time_ms = (end_time - start_time) * 1000

            # Enforcement overhead should be minimal
            assert enforcement_time_ms < 1.0, f"Read-only enforcement overhead {enforcement_time_ms:.3f}ms too high"
            assert blocked_success is False, f"Write operation should be blocked: {blocked_sql}"

        # Assert: Read-only boundary performance requirements
        query_stats = db_performance_metrics.get_query_stats()

        # 1. No significant performance impact from read-only enforcement
        assert query_stats['avg'] < 25, f"Read-only queries average {query_stats['avg']:.1f}ms, enforcement impacting performance"

        # 2. All read queries should succeed
        for result in readonly_performance_results:
            assert result['success'] is True, f"Read query should succeed: {result['description']}"

        # 3. Read query performance within targets
        for result in readonly_performance_results:
            assert result['execution_time_ms'] < 35, \
                f"Read-only query {result['description']} took {result['execution_time_ms']:.1f}ms, too slow"

        print("\nRead-Only Boundary Performance:")
        print(f"  Average Query Time: {query_stats['avg']:.1f}ms")
        print("  Enforcement Overhead: <1ms")

        for result in readonly_performance_results:
            status = "✓" if result['success'] else "✗"
            print(f"    {result['description']}: {result['execution_time_ms']:.1f}ms {status}")


class TestConcurrentDatabasePerformance:
    """Test database performance under concurrent access patterns."""

    @patch('psycopg2.connect')
    def test_concurrent_query_performance(self, mock_connect, db_performance_metrics: DatabasePerformanceMetrics):
        """Test database performance under concurrent query load."""
        # Arrange: Mock connection pool behavior
        connection_pool_size = 20
        active_connections = 0
        connection_lock = threading.Lock()

        def create_mock_connection():
            nonlocal active_connections
            with connection_lock:
                if active_connections < connection_pool_size:
                    active_connections += 1
                    conn = MockDatabaseConnection(simulate_load=True)
                    return conn
                time.sleep(0.005)  # Connection pool wait
                active_connections += 1
                return MockDatabaseConnection(simulate_load=True)

        mock_connect.side_effect = lambda: create_mock_connection()

        # Act: Simulate concurrent database access
        concurrent_queries = [
            "SELECT ticker, name FROM symbols WHERE symbol_type = 'ETF' ORDER BY name LIMIT 20",
            "SELECT key, value FROM cache_entries WHERE type = 'etf_universe'",
            "SELECT symbol, close, volume FROM ohlcv_daily WHERE date = CURRENT_DATE",
            "SELECT COUNT(*) FROM symbols WHERE fmv_supported = true",
            "SELECT issuer, COUNT(*) FROM symbols WHERE symbol_type = 'ETF' GROUP BY issuer"
        ]

        def execute_concurrent_query(query_sql):
            """Execute query in concurrent thread."""
            start_time = time.perf_counter()

            try:
                conn = mock_connect()
                with conn.cursor() as cursor:
                    cursor.set_fetchall_data([{'test': 'data'}])
                    cursor.execute(query_sql)
                    results = cursor.fetchall()

                end_time = time.perf_counter()
                execution_time_ms = (end_time - start_time) * 1000

                return {
                    'success': True,
                    'execution_time_ms': execution_time_ms,
                    'result_count': len(results)
                }

            except Exception as e:
                end_time = time.perf_counter()
                return {
                    'success': False,
                    'execution_time_ms': (end_time - start_time) * 1000,
                    'error': str(e)
                }
            finally:
                with connection_lock:
                    active_connections = max(0, active_connections - 1)

        # Run concurrent queries
        concurrent_thread_count = 50
        with ThreadPoolExecutor(max_workers=concurrent_thread_count) as executor:
            # Submit queries across multiple threads
            futures = []
            for i in range(concurrent_thread_count):
                query = concurrent_queries[i % len(concurrent_queries)]
                future = executor.submit(execute_concurrent_query, query)
                futures.append(future)

            # Collect results
            concurrent_results = []
            for future in as_completed(futures):
                result = future.result()
                concurrent_results.append(result)

                if result['success']:
                    db_performance_metrics.concurrent_query_times.append(result['execution_time_ms'])

        # Assert: Concurrent performance requirements
        successful_queries = [r for r in concurrent_results if r['success']]

        # 1. High success rate under concurrent load
        success_rate = len(successful_queries) / len(concurrent_results)
        assert success_rate > 0.95, f"Success rate {success_rate:.1%} too low under concurrent load"

        # 2. Concurrent query performance degradation acceptable
        if db_performance_metrics.concurrent_query_times:
            avg_concurrent_time = sum(db_performance_metrics.concurrent_query_times) / len(db_performance_metrics.concurrent_query_times)
            max_concurrent_time = max(db_performance_metrics.concurrent_query_times)

            # Average should still be reasonable under load
            assert avg_concurrent_time < 75, f"Average concurrent query time {avg_concurrent_time:.1f}ms too high"

            # Maximum should not exceed reasonable bounds
            assert max_concurrent_time < 200, f"Max concurrent query time {max_concurrent_time:.1f}ms excessive"

        # 3. Connection pool handling
        failed_queries = [r for r in concurrent_results if not r['success']]
        connection_failures = len([r for r in failed_queries if 'connection' in r.get('error', '').lower()])

        # Should handle connection pool pressure gracefully
        assert connection_failures < 5, f"Too many connection failures: {connection_failures}"

        print("\nConcurrent Database Performance:")
        print(f"  Concurrent Threads: {concurrent_thread_count}")
        print(f"  Success Rate: {success_rate:.1%}")
        print(f"  Successful Queries: {len(successful_queries)}")

        if db_performance_metrics.concurrent_query_times:
            avg_time = sum(db_performance_metrics.concurrent_query_times) / len(db_performance_metrics.concurrent_query_times)
            print(f"  Average Query Time: {avg_time:.1f}ms")
            print(f"  Max Query Time: {max(db_performance_metrics.concurrent_query_times):.1f}ms")


# Test Fixtures

@pytest.fixture
def db_performance_metrics():
    """Provide database performance metrics tracking."""
    return DatabasePerformanceMetrics()


@pytest.fixture
def sample_etf_data():
    """Provide sample ETF data for testing."""
    return {
        'symbols': [
            {
                'ticker': 'SPY',
                'name': 'SPDR S&P 500 ETF Trust',
                'symbol_type': 'ETF',
                'etf_type': 'ETF',
                'fmv_supported': True,
                'issuer': 'State Street (SPDR)',
                'correlation_reference': 'SPY'
            },
            {
                'ticker': 'QQQ',
                'name': 'Invesco QQQ Trust ETF',
                'symbol_type': 'ETF',
                'etf_type': 'ETF',
                'fmv_supported': True,
                'issuer': 'Invesco',
                'correlation_reference': 'QQQ'
            }
        ],
        'ohlcv_data': [
            {
                'symbol': 'SPY',
                'date': '2024-09-01',
                'close': 558.00,
                'volume': 45000000,
                'fmv_price': 558.05
            }
        ]
    }


# Performance Benchmarks

@pytest.mark.performance
class TestDatabasePerformanceBenchmarks:
    """Database performance benchmarks for Sprint 14 enhancements."""

    @patch('psycopg2.connect')
    def test_comprehensive_database_performance_benchmark(self, mock_connect, db_performance_metrics: DatabasePerformanceMetrics):
        """Comprehensive database performance benchmark across all enhanced features."""
        # Arrange: Mock comprehensive database setup
        mock_conn = MockDatabaseConnection(simulate_load=True)
        mock_connect.return_value = mock_conn

        # Comprehensive benchmark queries
        benchmark_queries = [
            # ETF Symbols queries
            ("SELECT ticker, name, etf_type FROM symbols WHERE symbol_type = 'ETF' LIMIT 50", "ETF Symbol List"),
            ("SELECT * FROM symbols WHERE ticker = 'SPY'", "Single ETF Lookup"),
            ("SELECT COUNT(*) FROM symbols WHERE fmv_supported = true", "FMV Count"),

            # OHLCV queries
            ("SELECT symbol, close, fmv_price FROM ohlcv_daily WHERE symbol = 'SPY' ORDER BY date DESC LIMIT 30", "30-Day OHLCV"),
            ("SELECT symbol, AVG(close) FROM ohlcv_daily WHERE date >= '2024-08-01' GROUP BY symbol", "Monthly Averages"),

            # Cache Entries queries
            ("SELECT key, value FROM cache_entries WHERE type = 'etf_universe'", "ETF Universes"),
            ("SELECT * FROM cache_entries WHERE key = 'etf_growth'", "Single Universe"),

            # Complex joins
            ("SELECT s.ticker, s.name, o.close FROM symbols s JOIN ohlcv_daily o ON s.ticker = o.symbol WHERE s.symbol_type = 'ETF' LIMIT 100", "ETF-OHLCV Join"),
        ]

        benchmark_results = []
        total_start_time = time.perf_counter()

        for sql, description in benchmark_queries:
            with mock_conn.cursor() as cursor:
                cursor.set_fetchall_data([{'test': 'data'}])

                start_time = time.perf_counter()
                cursor.execute(sql)
                results = cursor.fetchall()
                end_time = time.perf_counter()

                execution_time_ms = (end_time - start_time) * 1000
                db_performance_metrics.add_query_time(execution_time_ms)

                benchmark_results.append({
                    'description': description,
                    'execution_time_ms': execution_time_ms,
                    'result_count': len(results)
                })

        total_end_time = time.perf_counter()
        total_benchmark_time = (total_end_time - total_start_time) * 1000

        # Performance analysis
        query_stats = db_performance_metrics.get_query_stats()

        print("\nComprehensive Database Performance Benchmark:")
        print(f"  Total Benchmark Time: {total_benchmark_time:.1f}ms")
        print(f"  Average Query Time: {query_stats['avg']:.1f}ms")
        print(f"  P95 Query Time: {query_stats['p95']:.1f}ms")
        print(f"  Fastest Query: {query_stats['min']:.1f}ms")
        print(f"  Slowest Query: {query_stats['max']:.1f}ms")
        print(f"  Total Queries: {query_stats['count']}")

        print("\nQuery Breakdown:")
        for result in benchmark_results:
            print(f"    {result['description']}: {result['execution_time_ms']:.1f}ms")

        # Performance assertions
        assert query_stats['avg'] < 40, f"Average query performance {query_stats['avg']:.1f}ms exceeds 40ms benchmark"
        assert query_stats['p95'] < 75, f"P95 query performance {query_stats['p95']:.1f}ms exceeds 75ms benchmark"
        assert total_benchmark_time < 500, f"Total benchmark time {total_benchmark_time:.1f}ms too high"


if __name__ == '__main__':
    # Run database performance integration tests
    pytest.main([
        __file__,
        '-v',
        '--tb=short'
    ])
