"""
TickStock Database Integration Tests - Sprint 10 Phase 1
Tests for TickStockDatabase class including connection management, queries, and health checks.

Test Coverage:
- Connection management and pooling
- Read-only query operations
- Health check functionality
- Error handling and timeouts
- Performance validation (<50ms requirement)
"""

import os
import time
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError

from src.infrastructure.database.tickstock_db import TickStockDatabase


class TestTickStockDatabaseConnection:
    """Test TickStockDatabase connection management and initialization."""

    def test_connection_url_building_with_defaults(self):
        """Test connection URL building with default environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            config = {}
            db = TickStockDatabase.__new__(TickStockDatabase)
            db.config = config

            url = db._build_connection_url()

            assert url == "postgresql://postgres:@localhost:5432/tickstock"

    def test_connection_url_building_with_env_vars(self):
        """Test connection URL building with custom environment variables."""
        env_vars = {
            'TICKSTOCK_DB_HOST': 'production-host',
            'TICKSTOCK_DB_PORT': '5432',
            'TICKSTOCK_DB_USER': 'appv2_user',
            'TICKSTOCK_DB_PASSWORD': 'secure_password'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = {}
            db = TickStockDatabase.__new__(TickStockDatabase)
            db.config = config

            url = db._build_connection_url()

            expected_url = "postgresql://appv2_user:secure_password@production-host:5432/tickstock"
            assert expected_url == url

    def test_fixed_database_name_enforcement(self):
        """Test that database name is always 'tickstock' regardless of config."""
        env_vars = {
            'TICKSTOCK_DB_HOST': 'custom-host',
            'DB_NAME': 'other_database'  # This should be ignored
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = {'database_name': 'ignored_db'}  # This should be ignored
            db = TickStockDatabase.__new__(TickStockDatabase)
            db.config = config

            url = db._build_connection_url()

            assert "/tickstock" in url
            assert "other_database" not in url
            assert "ignored_db" not in url

    def test_engine_initialization_success(self):
        """Test successful engine initialization with proper configuration."""
        with patch('src.infrastructure.database.tickstock_db.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine

            with patch.object(TickStockDatabase, '_test_connection') as mock_test:
                config = {}
                db = TickStockDatabase(config)

                # Verify engine creation with correct parameters
                mock_create_engine.assert_called_once()
                call_args = mock_create_engine.call_args

                assert 'pool_size=5' in str(call_args) or call_args.kwargs.get('pool_size') == 5
                assert 'max_overflow=2' in str(call_args) or call_args.kwargs.get('max_overflow') == 2
                assert 'pool_timeout=10' in str(call_args) or call_args.kwargs.get('pool_timeout') == 10

                # Verify connection test was called
                mock_test.assert_called_once()

    def test_engine_initialization_failure(self):
        """Test engine initialization failure handling."""
        with patch('src.infrastructure.database.tickstock_db.create_engine') as mock_create_engine:
            mock_create_engine.side_effect = SQLAlchemyError("Connection failed")

            config = {}

            with pytest.raises(SQLAlchemyError):
                TickStockDatabase(config)

    def test_connection_test_success(self):
        """Test successful connection test with TimescaleDB detection."""
        mock_engine = Mock()
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.scalar.side_effect = [1, 'timescaledb']  # First call returns 1, second returns extension name
        mock_connection.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        config = {}
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = config
        db.engine = mock_engine

        # Should not raise any exception
        db._test_connection()

        # Verify both queries were executed
        assert mock_connection.execute.call_count == 2

    def test_connection_test_failure(self):
        """Test connection test failure handling."""
        mock_engine = Mock()
        mock_connection = Mock()
        mock_connection.execute.side_effect = SQLAlchemyError("Query failed")
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        config = {}
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = config
        db.engine = mock_engine

        with pytest.raises(SQLAlchemyError):
            db._test_connection()

    def test_connection_context_manager_success(self):
        """Test successful connection context manager usage."""
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.connect.return_value = mock_connection

        config = {}
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = config
        db.engine = mock_engine

        with db.get_connection() as conn:
            assert conn == mock_connection

        mock_connection.close.assert_called_once()

    def test_connection_context_manager_failure(self):
        """Test connection context manager with exception handling."""
        mock_engine = Mock()
        mock_connection = Mock()
        mock_connection.execute.side_effect = SQLAlchemyError("Query error")
        mock_engine.connect.return_value = mock_connection

        config = {}
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = config
        db.engine = mock_engine

        with pytest.raises(SQLAlchemyError), db.get_connection() as conn:
            conn.execute("SELECT 1")

        # Verify rollback and close were called
        mock_connection.rollback.assert_called_once()
        mock_connection.close.assert_called_once()

    def test_connection_without_initialized_engine(self):
        """Test connection attempt when engine is not initialized."""
        config = {}
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = config
        db.engine = None

        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            with db.get_connection():
                pass


class TestTickStockDatabaseQueries:
    """Test TickStockDatabase query operations."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock TickStockDatabase instance for testing."""
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = {}
        db.engine = Mock()
        return db

    def test_get_symbols_for_dropdown_success(self, mock_db):
        """Test successful retrieval of symbols for dropdown."""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([('AAPL',), ('GOOGL',), ('MSFT',)]))
        mock_connection.execute.return_value = mock_result

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            symbols = mock_db.get_symbols_for_dropdown()

            assert symbols == ['AAPL', 'GOOGL', 'MSFT']
            mock_connection.execute.assert_called_once()

    def test_get_symbols_for_dropdown_empty_result(self, mock_db):
        """Test symbols retrieval with empty database result."""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_connection.execute.return_value = mock_result

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            symbols = mock_db.get_symbols_for_dropdown()

            assert symbols == []

    def test_get_symbols_for_dropdown_database_error(self, mock_db):
        """Test symbols retrieval with database error."""
        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.side_effect = SQLAlchemyError("Database connection failed")

            symbols = mock_db.get_symbols_for_dropdown()

            assert symbols == []

    def test_get_basic_dashboard_stats_success(self, mock_db):
        """Test successful retrieval of basic dashboard statistics."""
        mock_connection = Mock()
        mock_results = [Mock(), Mock(), Mock()]
        mock_results[0].scalar.return_value = 4000  # symbols count
        mock_results[1].scalar.return_value = 15000  # events count

        # Mock timestamp for latest event
        from datetime import datetime
        test_time = datetime(2025, 1, 15, 10, 30, 0)
        mock_results[2].scalar.return_value = test_time

        mock_connection.execute.side_effect = mock_results

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            stats = mock_db.get_basic_dashboard_stats()

            assert stats['symbols_count'] == 4000
            assert stats['events_count'] == 15000
            assert stats['latest_event_time'] == test_time.isoformat()
            assert stats['database_status'] == 'connected'

    def test_get_basic_dashboard_stats_events_table_missing(self, mock_db):
        """Test dashboard stats when events table doesn't exist."""
        mock_connection = Mock()

        # First query (symbols count) succeeds, second (events) fails
        def execute_side_effect(query):
            if "COUNT(*) FROM symbols" in str(query):
                result = Mock()
                result.scalar.return_value = 4000
                return result
            if "COUNT(*) FROM events" in str(query):
                raise SQLAlchemyError("Table 'events' doesn't exist")
            raise SQLAlchemyError("Unexpected query")

        mock_connection.execute.side_effect = execute_side_effect

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            stats = mock_db.get_basic_dashboard_stats()

            assert stats['symbols_count'] == 4000
            assert stats['events_count'] == 0
            assert stats['latest_event_time'] is None
            assert stats['database_status'] == 'connected'

    def test_get_user_alert_history_success(self, mock_db):
        """Test successful retrieval of user alert history."""
        mock_connection = Mock()
        mock_result = Mock()

        # Mock database rows
        from datetime import datetime
        test_time = datetime(2025, 1, 15, 10, 30, 0)
        mock_rows = [
            ('AAPL', 'high_low', 0.85, test_time, {'price': 150.0}),
            ('GOOGL', 'trend', 0.92, test_time, {'direction': 'up'})
        ]
        mock_result.__iter__ = Mock(return_value=iter(mock_rows))
        mock_connection.execute.return_value = mock_result

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            alerts = mock_db.get_user_alert_history('user123', limit=50)

            assert len(alerts) == 2
            assert alerts[0]['symbol'] == 'AAPL'
            assert alerts[0]['pattern'] == 'high_low'
            assert alerts[0]['confidence'] == 0.85
            assert alerts[1]['symbol'] == 'GOOGL'

    def test_get_pattern_performance_success(self, mock_db):
        """Test successful retrieval of pattern performance statistics."""
        mock_connection = Mock()
        mock_result = Mock()

        # Mock performance data
        mock_rows = [
            ('high_low', 1500, 0.78, 0.95, 0.45),
            ('trend', 800, 0.82, 0.98, 0.52)
        ]
        mock_result.__iter__ = Mock(return_value=iter(mock_rows))
        mock_connection.execute.return_value = mock_result

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            performance = mock_db.get_pattern_performance()

            assert len(performance) == 2
            assert performance[0]['pattern'] == 'high_low'
            assert performance[0]['detection_count'] == 1500
            assert performance[0]['avg_confidence'] == 0.78

    def test_get_pattern_performance_with_filter(self, mock_db):
        """Test pattern performance with specific pattern filter."""
        mock_connection = Mock()
        mock_result = Mock()

        mock_rows = [('high_low', 1500, 0.78, 0.95, 0.45)]
        mock_result.__iter__ = Mock(return_value=iter(mock_rows))
        mock_connection.execute.return_value = mock_result

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            performance = mock_db.get_pattern_performance('high_low')

            assert len(performance) == 1
            assert performance[0]['pattern'] == 'high_low'

            # Verify the query included the pattern filter
            call_args = mock_connection.execute.call_args
            assert 'pattern_name' in str(call_args)


class TestTickStockDatabaseHealthCheck:
    """Test TickStockDatabase health check functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock TickStockDatabase instance for testing."""
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = {}
        db.engine = Mock()
        return db

    def test_health_check_success(self, mock_db):
        """Test successful health check with good performance."""
        # Mock engine pool status
        mock_db.engine.pool.status.return_value = "Pool status info"
        mock_db.engine.pool.size.return_value = 5
        mock_db.engine.pool.checkedin.return_value = 3
        mock_db.engine.pool.checkedout.return_value = 2
        mock_db.engine.pool.invalid.return_value = 0

        # Mock connection and queries
        mock_connection = Mock()
        mock_results = [Mock(), Mock()]

        # Mock table query result
        table_rows = [('symbols',), ('events',), ('ohlcv_daily',)]
        mock_results[1].__iter__ = Mock(return_value=iter(table_rows))
        mock_connection.execute.side_effect = mock_results

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            with patch('time.time', side_effect=[0.0, 0.025]):  # 25ms response time
                mock_get_conn.return_value.__enter__.return_value = mock_connection

                health = mock_db.health_check()

                assert health['status'] == 'healthy'
                assert health['database'] == 'tickstock'
                assert health['query_performance'] == 25.0
                assert 'symbols' in health['tables_accessible']
                assert 'events' in health['tables_accessible']

    def test_health_check_degraded_performance(self, mock_db):
        """Test health check with degraded performance (>100ms)."""
        # Mock engine pool
        mock_db.engine.pool.status.return_value = "Pool status info"
        mock_db.engine.pool.size.return_value = 5
        mock_db.engine.pool.checkedin.return_value = 3
        mock_db.engine.pool.checkedout.return_value = 2
        mock_db.engine.pool.invalid.return_value = 0

        # Mock slow connection
        mock_connection = Mock()
        mock_results = [Mock(), Mock()]
        mock_results[1].__iter__ = Mock(return_value=iter([('symbols',)]))
        mock_connection.execute.side_effect = mock_results

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            with patch('time.time', side_effect=[0.0, 0.150]):  # 150ms response time
                mock_get_conn.return_value.__enter__.return_value = mock_connection

                health = mock_db.health_check()

                assert health['status'] == 'degraded'
                assert health['query_performance'] == 150.0

    def test_health_check_no_tables_found(self, mock_db):
        """Test health check when no expected tables are found."""
        # Mock engine pool
        mock_db.engine.pool.status.return_value = "Pool status info"
        mock_db.engine.pool.size.return_value = 5
        mock_db.engine.pool.checkedin.return_value = 3
        mock_db.engine.pool.checkedout.return_value = 2
        mock_db.engine.pool.invalid.return_value = 0

        # Mock connection with no tables
        mock_connection = Mock()
        mock_results = [Mock(), Mock()]
        mock_results[1].__iter__ = Mock(return_value=iter([]))  # No tables found
        mock_connection.execute.side_effect = mock_results

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            with patch('time.time', side_effect=[0.0, 0.025]):
                mock_get_conn.return_value.__enter__.return_value = mock_connection

                health = mock_db.health_check()

                assert health['status'] == 'warning'
                assert 'No expected tables found' in health['warning']
                assert health['tables_accessible'] == []

    def test_health_check_engine_not_initialized(self, mock_db):
        """Test health check when database engine is not initialized."""
        mock_db.engine = None

        health = mock_db.health_check()

        assert health['status'] == 'error'
        assert 'Database engine not initialized' in health['error']

    def test_health_check_connection_failure(self, mock_db):
        """Test health check with connection failure."""
        # Mock engine pool
        mock_db.engine.pool.status.return_value = "Pool status info"
        mock_db.engine.pool.size.return_value = 5
        mock_db.engine.pool.checkedin.return_value = 3
        mock_db.engine.pool.checkedout.return_value = 2
        mock_db.engine.pool.invalid.return_value = 0

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.side_effect = SQLAlchemyError("Connection failed")

            health = mock_db.health_check()

            assert health['status'] == 'error'
            assert 'Connection failed' in health['error']

    def test_close_cleanup(self, mock_db):
        """Test proper cleanup when closing database connections."""
        mock_db.close()

        mock_db.engine.dispose.assert_called_once()
        assert mock_db.engine is None


@pytest.mark.performance
class TestTickStockDatabasePerformance:
    """Test TickStockDatabase performance requirements."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock TickStockDatabase instance for performance testing."""
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = {}
        db.engine = Mock()
        return db

    @pytest.mark.performance
    def test_symbols_query_performance(self, mock_db):
        """Test that symbols query meets <50ms performance requirement."""
        mock_connection = Mock()
        mock_result = Mock()

        # Create 4000 test symbols
        test_symbols = [(f'SYMBOL_{i:04d}',) for i in range(4000)]
        mock_result.__iter__ = Mock(return_value=iter(test_symbols))
        mock_connection.execute.return_value = mock_result

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            start_time = time.time()
            symbols = mock_db.get_symbols_for_dropdown()
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            assert len(symbols) == 4000
            assert execution_time < 50.0, f"Query took {execution_time:.2f}ms, should be <50ms"

    @pytest.mark.performance
    def test_dashboard_stats_performance(self, mock_db):
        """Test that dashboard stats query meets <50ms performance requirement."""
        mock_connection = Mock()
        mock_results = [Mock(), Mock(), Mock()]
        mock_results[0].scalar.return_value = 4000
        mock_results[1].scalar.return_value = 50000
        mock_results[2].scalar.return_value = None

        mock_connection.execute.side_effect = mock_results

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            start_time = time.time()
            stats = mock_db.get_basic_dashboard_stats()
            execution_time = (time.time() - start_time) * 1000

            assert stats['symbols_count'] == 4000
            assert execution_time < 50.0, f"Query took {execution_time:.2f}ms, should be <50ms"

    @pytest.mark.performance
    def test_health_check_performance(self, mock_db):
        """Test that health check meets <50ms performance requirement."""
        # Mock all engine pool methods
        mock_db.engine.pool.status.return_value = "status"
        mock_db.engine.pool.size.return_value = 5
        mock_db.engine.pool.checkedin.return_value = 3
        mock_db.engine.pool.checkedout.return_value = 2
        mock_db.engine.pool.invalid.return_value = 0

        mock_connection = Mock()
        mock_results = [Mock(), Mock()]
        mock_results[1].__iter__ = Mock(return_value=iter([('symbols',), ('events',)]))
        mock_connection.execute.side_effect = mock_results

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            start_time = time.time()
            health = mock_db.health_check()
            execution_time = (time.time() - start_time) * 1000

            assert health['status'] in ['healthy', 'degraded', 'warning']
            assert execution_time < 50.0, f"Health check took {execution_time:.2f}ms, should be <50ms"


class TestTickStockDatabaseErrorHandling:
    """Test TickStockDatabase error handling and edge cases."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock TickStockDatabase instance for error testing."""
        db = TickStockDatabase.__new__(TickStockDatabase)
        db.config = {}
        db.engine = Mock()
        return db

    def test_query_timeout_handling(self, mock_db):
        """Test handling of database query timeouts."""
        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.side_effect = TimeoutError("Query timeout")

            symbols = mock_db.get_symbols_for_dropdown()
            assert symbols == []

    def test_connection_pool_exhaustion(self, mock_db):
        """Test handling when connection pool is exhausted."""
        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.side_effect = SQLAlchemyError("QueuePool limit of size 5 overflow 2 reached")

            stats = mock_db.get_basic_dashboard_stats()
            assert stats['database_status'] == 'error'

    def test_invalid_sql_handling(self, mock_db):
        """Test handling of invalid SQL queries."""
        mock_connection = Mock()
        mock_connection.execute.side_effect = SQLAlchemyError("syntax error at or near")

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            alerts = mock_db.get_user_alert_history('test_user')
            assert alerts == []

    def test_database_disconnection_recovery(self, mock_db):
        """Test recovery from database disconnection."""
        mock_connection = Mock()
        mock_connection.execute.side_effect = [
            OperationalError("connection closed", None, None),
            Mock()  # Second attempt succeeds
        ]

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            # First call fails, but the method should handle the error gracefully
            symbols = mock_db.get_symbols_for_dropdown()
            assert symbols == []  # Should return empty list on error

    def test_none_value_handling_in_results(self, mock_db):
        """Test handling of None values in database query results."""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.scalar.side_effect = [None, None, None]  # All None values
        mock_connection.execute.return_value = mock_result

        with patch.object(mock_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection

            stats = mock_db.get_basic_dashboard_stats()

            assert stats['symbols_count'] == 0  # Should default to 0 for None
            assert stats['events_count'] == 0
            assert stats['latest_event_time'] is None
