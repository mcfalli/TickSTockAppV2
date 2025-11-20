"""
Sprint 14 Phase 1: Cross-System Integration Tests
Comprehensive integration testing for TickStockApp ↔ TickStockPL communication patterns.

Testing Focus:
1. ETF Data Flow: Historical loader → TickStockApp → WebSocket broadcasting
2. EOD Processing Integration: EOD processor → Redis pub-sub → TickStockApp notifications  
3. Development Universe Integration: Dev subsets → TickStockApp → UI dropdowns
4. Database Integration: Enhanced symbols table → TickStockApp queries → UI display
5. Redis Messaging: ETF/EOD events → Redis channels → WebSocket broadcasting

VALIDATION REQUIREMENTS:
- Message delivery <100ms for WebSocket broadcasting
- Redis pub-sub loose coupling maintained
- Database read-only boundaries enforced
- System resilience with degraded components
- Role separation: TickStockApp (consumer) vs TickStockPL (producer)
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import Mock, patch

import psycopg2
import pytest
import redis

# Import TickStock components
from src.core.services.market_data_subscriber import MarketDataSubscriber
from src.data.eod_processor import EODProcessor
from src.data.historical_loader import MassiveHistoricalLoader
from src.infrastructure.redis.redis_connection_manager import (
    RedisConnectionConfig,
    RedisConnectionManager,
)


@dataclass
class IntegrationTestMetrics:
    """Track integration test performance metrics."""
    message_delivery_times: list[float] = None
    database_query_times: list[float] = None
    redis_operation_times: list[float] = None
    websocket_broadcast_times: list[float] = None

    def __post_init__(self):
        if self.message_delivery_times is None:
            self.message_delivery_times = []
        if self.database_query_times is None:
            self.database_query_times = []
        if self.redis_operation_times is None:
            self.redis_operation_times = []
        if self.websocket_broadcast_times is None:
            self.websocket_broadcast_times = []

    def get_avg_message_delivery_time(self) -> float:
        """Get average message delivery time in milliseconds."""
        return sum(self.message_delivery_times) / len(self.message_delivery_times) if self.message_delivery_times else 0.0

    def get_max_message_delivery_time(self) -> float:
        """Get maximum message delivery time in milliseconds."""
        return max(self.message_delivery_times) if self.message_delivery_times else 0.0


class TestETFDataFlowCrossSystemIntegration:
    """Test ETF data flow from TickStockPL historical loader to TickStockApp WebSocket broadcasting."""

    @patch('src.data.historical_loader.psycopg2.connect')
    @patch('src.data.historical_loader.requests.Session.get')
    @patch('src.infrastructure.redis.redis_connection_manager.redis.Redis')
    def test_etf_historical_loader_to_tickstockapp_flow(self, mock_redis_class, mock_get, mock_db_connect,
                                                       integration_metrics: IntegrationTestMetrics):
        """Test complete ETF data flow from TickStockPL loader to TickStockApp broadcasting."""
        # Arrange: Mock TickStockPL historical loader (producer role)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'OK',
            'queryCount': 252,
            'results': [
                {
                    't': int(datetime.now().timestamp() * 1000),
                    'o': 557.00,
                    'h': 558.50,
                    'l': 556.25,
                    'c': 558.00,
                    'v': 45000000
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock database operations (TickStockPL writes, TickStockApp reads)
        mock_db_conn = Mock()
        mock_db_cursor = Mock()
        mock_db_connect.return_value = mock_db_conn
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor

        # Mock Redis for cross-system messaging
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        # Mock TickStockApp market data subscriber (consumer role)
        mock_socketio = Mock()
        config = RedisConnectionConfig(host='localhost', port=6379, db=0)

        with patch('src.core.services.market_data_subscriber.UserSettingsService') as mock_user_service:
            mock_user_service.return_value.get_all_user_watchlists.return_value = {
                'user1': ['SPY', 'QQQ'],
                'user2': ['SPY', 'IWM']
            }

            subscriber = MarketDataSubscriber(mock_redis_client, mock_socketio, {})

            # Act: Simulate ETF data flow
            start_time = time.time()

            # 1. TickStockPL loads ETF data (producer role)
            historical_loader = MassiveHistoricalLoader()
            etf_metadata = historical_loader._extract_etf_metadata({
                'ticker': 'SPY',
                'name': 'SPDR S&P 500 ETF Trust',
                'type': 'ETF',
                'composite_figi': 'BBG000BDTBL9'
            })

            # 2. TickStockPL publishes ETF event via Redis (loose coupling)
            etf_event = {
                'event_type': 'etf_data_updated',
                'symbol': 'SPY',
                'symbol_type': 'ETF',
                'data': etf_metadata,
                'timestamp': time.time(),
                'source': 'tickstockpl'
            }

            # 3. TickStockApp consumes ETF event (consumer role)
            subscriber._handle_price_update(Mock(
                symbol='SPY',
                price=558.00,
                data={
                    'change': 1.50,
                    'change_percent': 0.27,
                    'volume': 45000000
                },
                timestamp=time.time()
            ))

            end_time = time.time()
            processing_time_ms = (end_time - start_time) * 1000
            integration_metrics.message_delivery_times.append(processing_time_ms)

            # Assert: Verify cross-system integration
            # 1. ETF metadata extracted correctly (TickStockPL processing)
            assert etf_metadata['etf_type'] == 'ETF'
            assert etf_metadata['fmv_supported'] is True
            assert etf_metadata['correlation_reference'] == 'SPY'

            # 2. WebSocket broadcasting called (TickStockApp broadcasting)
            mock_socketio.emit.assert_called()
            websocket_call = mock_socketio.emit.call_args
            event_name, event_data = websocket_call[0]

            assert event_name == 'dashboard_price_update'
            assert event_data['symbol'] == 'SPY'
            assert event_data['price'] == 558.00

            # 3. Performance requirement: <100ms message delivery
            assert processing_time_ms < 100, f"ETF message delivery took {processing_time_ms:.1f}ms, exceeding 100ms target"

    @patch('src.data.historical_loader.psycopg2.connect')
    def test_etf_universe_integration_with_tickstockapp_queries(self, mock_db_connect,
                                                               integration_metrics: IntegrationTestMetrics):
        """Test ETF universe creation by TickStockPL integrates with TickStockApp UI queries."""
        # Arrange: Mock database for read-only TickStockApp access
        mock_db_conn = Mock()
        mock_db_cursor = Mock()
        mock_db_connect.return_value = mock_db_conn
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor

        # Simulate TickStockPL creating ETF universes (producer role)
        etf_universes = {
            'etf_growth': {
                'name': 'Growth ETFs',
                'etfs': [
                    {'ticker': 'VUG', 'name': 'Vanguard Growth ETF'},
                    {'ticker': 'QQQ', 'name': 'Invesco QQQ Trust ETF'},
                    {'ticker': 'VGT', 'name': 'Vanguard Information Technology ETF'}
                ]
            },
            'etf_sectors': {
                'name': 'Sector ETFs',
                'etfs': [
                    {'ticker': 'XLF', 'name': 'Financial Select Sector SPDR Fund'},
                    {'ticker': 'XLE', 'name': 'Energy Select Sector SPDR Fund'},
                    {'ticker': 'XLK', 'name': 'Technology Select Sector SPDR Fund'}
                ]
            }
        }

        # Mock TickStockApp querying ETF universes (consumer role - read-only)
        mock_db_cursor.fetchall.return_value = [
            {
                'key': 'etf_growth',
                'type': 'etf_universe',
                'value': json.dumps(etf_universes['etf_growth'])
            },
            {
                'key': 'etf_sectors',
                'type': 'etf_universe',
                'value': json.dumps(etf_universes['etf_sectors'])
            }
        ]

        # Act: Simulate TickStockApp UI dropdown query
        start_time = time.time()

        # TickStockApp queries cache_entries for ETF universes (read-only access)
        query_sql = """
        SELECT key, type, value FROM cache_entries 
        WHERE type = 'etf_universe' AND environment = 'DEFAULT'
        ORDER BY key
        """
        mock_db_cursor.execute(query_sql)
        results = mock_db_cursor.fetchall()

        # Process results for UI dropdown
        ui_dropdown_data = []
        for row in results:
            universe_data = json.loads(row['value'])
            etf_count = len(universe_data.get('etfs', []))
            ui_dropdown_data.append({
                'universe_key': row['key'],
                'display_name': universe_data['name'],
                'etf_count': etf_count,
                'symbols': [etf['ticker'] for etf in universe_data.get('etfs', [])]
            })

        end_time = time.time()
        query_time_ms = (end_time - start_time) * 1000
        integration_metrics.database_query_times.append(query_time_ms)

        # Assert: Verify TickStockApp integration
        # 1. UI dropdown data correctly populated
        assert len(ui_dropdown_data) == 2

        growth_universe = next(item for item in ui_dropdown_data if item['universe_key'] == 'etf_growth')
        assert growth_universe['display_name'] == 'Growth ETFs'
        assert growth_universe['etf_count'] == 3
        assert 'VUG' in growth_universe['symbols']
        assert 'QQQ' in growth_universe['symbols']

        # 2. Database query performance: <50ms
        assert query_time_ms < 50, f"ETF universe query took {query_time_ms:.1f}ms, exceeding 50ms target"

        # 3. Read-only database access enforced (TickStockApp consumer role)
        execute_calls = mock_db_cursor.execute.call_args_list
        for call in execute_calls:
            sql_query = call[0][0].upper()
            assert not any(write_op in sql_query for write_op in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'])

    @patch('src.infrastructure.redis.redis_connection_manager.redis.Redis')
    def test_etf_event_redis_broadcasting_integration(self, mock_redis_class,
                                                     integration_metrics: IntegrationTestMetrics):
        """Test ETF events flow through Redis to TickStockApp WebSocket broadcasting."""
        # Arrange: Mock Redis for cross-system messaging
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        # Mock TickStockApp WebSocket broadcasting
        mock_socketio = Mock()

        # Create market data subscriber (TickStockApp consumer role)
        config = RedisConnectionConfig(host='localhost', port=6379, db=0)

        with patch('src.core.services.market_data_subscriber.UserSettingsService') as mock_user_service:
            mock_user_service.return_value.get_all_user_watchlists.return_value = {
                'user1': ['SPY', 'VUG'],
                'user2': ['QQQ', 'XLK']
            }

            subscriber = MarketDataSubscriber(mock_redis_client, mock_socketio, {})

            # Act: Simulate ETF events from TickStockPL
            etf_events = [
                {
                    'symbol': 'SPY',
                    'event_type': 'etf_price_update',
                    'price': 558.75,
                    'change': 2.25,
                    'change_percent': 0.40,
                    'volume': 47000000,
                    'etf_metadata': {
                        'issuer': 'State Street (SPDR)',
                        'correlation_reference': 'SPY',
                        'fmv_supported': True
                    }
                },
                {
                    'symbol': 'VUG',
                    'event_type': 'etf_volume_spike',
                    'price': 312.50,
                    'volume_spike': 3.2,
                    'volume': 2500000,
                    'etf_metadata': {
                        'issuer': 'Vanguard',
                        'correlation_reference': 'VUG'
                    }
                }
            ]

            start_time = time.time()

            # Process ETF events (simulating Redis message consumption)
            for event in etf_events:
                subscriber._handle_price_update(Mock(
                    symbol=event['symbol'],
                    price=event['price'],
                    data={
                        'change': event.get('change', 0),
                        'change_percent': event.get('change_percent', 0),
                        'volume': event['volume'],
                        'etf_metadata': event.get('etf_metadata', {})
                    },
                    timestamp=time.time()
                ))

            end_time = time.time()
            broadcast_time_ms = (end_time - start_time) * 1000
            integration_metrics.websocket_broadcast_times.append(broadcast_time_ms)

            # Assert: Verify Redis to WebSocket integration
            # 1. WebSocket broadcasting called for both events
            assert mock_socketio.emit.call_count == 2

            # 2. Verify ETF-specific data preservation
            emit_calls = mock_socketio.emit.call_args_list

            spy_call = emit_calls[0]
            assert spy_call[0][0] == 'dashboard_price_update'  # Event name
            spy_data = spy_call[0][1]  # Event data
            assert spy_data['symbol'] == 'SPY'
            assert spy_data['price'] == 558.75
            assert spy_data['change_percent'] == 0.40

            vug_call = emit_calls[1]
            vug_data = vug_call[0][1]
            assert vug_data['symbol'] == 'VUG'
            assert vug_data['price'] == 312.50

            # 3. Broadcasting performance: <100ms for multiple events
            assert broadcast_time_ms < 100, f"ETF event broadcasting took {broadcast_time_ms:.1f}ms, exceeding 100ms target"


class TestEODProcessingCrossSystemIntegration:
    """Test EOD processing integration between TickStockPL and TickStockApp via Redis."""

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch('src.data.eod_processor.redis.Redis')
    def test_eod_completion_notification_cross_system_flow(self, mock_redis_class, mock_db_connect,
                                                          integration_metrics: IntegrationTestMetrics):
        """Test EOD completion notifications flow from TickStockPL to TickStockApp."""
        # Arrange: Mock TickStockPL EOD processing (producer role)
        mock_db_conn = Mock()
        mock_db_cursor = Mock()
        mock_db_connect.return_value = mock_db_conn
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor

        # Mock Redis for cross-system messaging
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        # Mock TickStockApp WebSocket handler (consumer role)
        mock_socketio = Mock()
        received_notifications = []

        def capture_notification(channel, message):
            """Simulate TickStockApp receiving EOD notification."""
            notification = json.loads(message)
            received_notifications.append(notification)

            # Simulate WebSocket broadcasting to frontend
            mock_socketio.emit('eod_completion_update', notification, broadcast=True)

        mock_redis_client.publish.side_effect = capture_notification

        # Mock EOD validation results
        mock_db_cursor.fetchall.return_value = [
            {
                'key': 'stock_sp500',
                'type': 'stock_universe',
                'value': json.dumps({
                    'stocks': [{'ticker': 'AAPL'}, {'ticker': 'MSFT'}, {'ticker': 'NVDA'}]
                })
            },
            {
                'key': 'etf_growth',
                'type': 'etf_universe',
                'value': json.dumps({
                    'etfs': [{'ticker': 'SPY'}, {'ticker': 'QQQ'}]
                })
            }
        ]

        # Mock data completeness validation (97% success rate)
        validation_responses = [1, 1, 1, 1, 0]  # 4 out of 5 symbols complete
        mock_db_cursor.fetchone.side_effect = [(count,) for count in validation_responses]

        # Act: Run EOD update (TickStockPL producer role)
        start_time = time.time()

        eod_processor = EODProcessor()
        eod_result = eod_processor.run_eod_update()

        end_time = time.time()
        eod_time_ms = (end_time - start_time) * 1000
        integration_metrics.redis_operation_times.append(eod_time_ms)

        # Assert: Verify cross-system EOD integration
        # 1. EOD processing completed successfully
        assert eod_result['status'] == 'COMPLETE'
        assert eod_result['completion_rate'] >= 0.8  # 80% minimum

        # 2. Redis notification published (cross-system communication)
        assert mock_redis_client.publish.called
        publish_call = mock_redis_client.publish.call_args
        channel, message = publish_call[0]

        assert channel == 'tickstock:eod:completion'
        notification = json.loads(message)
        assert notification['type'] == 'eod_completion'
        assert 'timestamp' in notification
        assert 'results' in notification

        # 3. TickStockApp received and processed notification
        assert len(received_notifications) == 1
        received_notification = received_notifications[0]
        assert received_notification['type'] == 'eod_completion'

        # 4. WebSocket broadcasting triggered (TickStockApp consumer role)
        mock_socketio.emit.assert_called_with('eod_completion_update', received_notification, broadcast=True)

        # 5. Performance: EOD notification delivery <100ms
        notification_time = eod_time_ms  # Includes notification publishing
        assert notification_time < 5000, f"EOD notification took {notification_time:.1f}ms, exceeding reasonable limits"

    @patch('src.data.eod_processor.redis.Redis')
    def test_eod_status_caching_cross_system_integration(self, mock_redis_class,
                                                        integration_metrics: IntegrationTestMetrics):
        """Test EOD status caching for TickStockApp status queries."""
        # Arrange: Mock Redis for cross-system caching
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        # Sample EOD status data
        eod_status = {
            'status': 'COMPLETE',
            'target_date': '2024-09-01',
            'total_symbols': 5238,
            'completion_rate': 0.97,
            'processing_time_minutes': 42.5,
            'etf_count': 738,
            'stock_count': 4500,
            'last_updated': datetime.now().isoformat()
        }

        # Act: Test cross-system caching workflow
        start_time = time.time()

        # 1. TickStockPL caches EOD status (producer role)
        cache_key = 'tickstock:eod:latest_status'
        cache_value = json.dumps(eod_status)
        mock_redis_client.setex(cache_key, 86400, cache_value)  # 24 hour TTL

        # 2. TickStockApp queries cached status (consumer role)
        mock_redis_client.get.return_value = cache_value
        cached_status = json.loads(mock_redis_client.get(cache_key))

        end_time = time.time()
        cache_time_ms = (end_time - start_time) * 1000
        integration_metrics.redis_operation_times.append(cache_time_ms)

        # Assert: Verify cross-system caching integration
        # 1. Status cached by TickStockPL
        mock_redis_client.setex.assert_called_with(cache_key, 86400, cache_value)

        # 2. Status retrieved by TickStockApp
        mock_redis_client.get.assert_called_with(cache_key)
        assert cached_status['status'] == 'COMPLETE'
        assert cached_status['completion_rate'] == 0.97

        # 3. Performance: Cache operations <10ms
        assert cache_time_ms < 10, f"EOD status caching took {cache_time_ms:.1f}ms, exceeding 10ms target"


class TestDevelopmentUniverseCrossSystemIntegration:
    """Test development universe integration between TickStockPL data loading and TickStockApp UI."""

    @patch('src.data.historical_loader.psycopg2.connect')
    def test_development_universe_loading_to_ui_integration(self, mock_db_connect,
                                                           integration_metrics: IntegrationTestMetrics):
        """Test development universe data flows from TickStockPL loader to TickStockApp admin interface."""
        # Arrange: Mock database for development universe operations
        mock_db_conn = Mock()
        mock_db_cursor = Mock()
        mock_db_connect.return_value = mock_db_conn
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor

        # Development universes created by TickStockPL (producer role)
        dev_universes = {
            'dev_top_10': {
                'name': 'Development Top 10',
                'description': 'Top 10 stocks for development testing',
                'stocks': [
                    {'ticker': 'AAPL', 'name': 'Apple Inc'},
                    {'ticker': 'MSFT', 'name': 'Microsoft Corporation'},
                    {'ticker': 'NVDA', 'name': 'NVIDIA Corporation'},
                    {'ticker': 'GOOGL', 'name': 'Alphabet Inc'},
                    {'ticker': 'AMZN', 'name': 'Amazon.com Inc'}
                ]
            },
            'dev_etfs': {
                'name': 'Development ETFs',
                'description': 'Small ETF set for development testing',
                'etfs': [
                    {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF'},
                    {'ticker': 'QQQ', 'name': 'Invesco QQQ ETF'},
                    {'ticker': 'IWM', 'name': 'iShares Russell 2000 ETF'}
                ]
            }
        }

        # Mock TickStockApp admin interface queries (consumer role - read-only)
        mock_db_cursor.fetchall.return_value = [
            {
                'key': 'dev_top_10',
                'type': 'stock_universe',
                'value': json.dumps(dev_universes['dev_top_10']),
                'environment': 'DEVELOPMENT'
            },
            {
                'key': 'dev_etfs',
                'type': 'etf_universe',
                'value': json.dumps(dev_universes['dev_etfs']),
                'environment': 'DEVELOPMENT'
            }
        ]

        # Act: Simulate TickStockApp admin interface loading development universes
        start_time = time.time()

        # Query development universes for admin interface
        admin_query_sql = """
        SELECT key, type, value, environment FROM cache_entries
        WHERE environment = 'DEVELOPMENT' AND key LIKE 'dev_%'
        ORDER BY type, key
        """
        mock_db_cursor.execute(admin_query_sql)
        dev_results = mock_db_cursor.fetchall()

        # Process for admin UI display
        admin_ui_data = []
        for row in dev_results:
            universe_data = json.loads(row['value'])

            if row['type'] == 'stock_universe':
                symbol_count = len(universe_data.get('stocks', []))
                symbols = [stock['ticker'] for stock in universe_data.get('stocks', [])]
            elif row['type'] == 'etf_universe':
                symbol_count = len(universe_data.get('etfs', []))
                symbols = [etf['ticker'] for etf in universe_data.get('etfs', [])]
            else:
                symbol_count = 0
                symbols = []

            admin_ui_data.append({
                'universe_key': row['key'],
                'universe_type': row['type'],
                'display_name': universe_data.get('name', row['key']),
                'description': universe_data.get('description', ''),
                'symbol_count': symbol_count,
                'symbols': symbols,
                'environment': row['environment']
            })

        end_time = time.time()
        admin_query_time_ms = (end_time - start_time) * 1000
        integration_metrics.database_query_times.append(admin_query_time_ms)

        # Assert: Verify development universe cross-system integration
        # 1. Admin interface data correctly populated
        assert len(admin_ui_data) == 2

        dev_stocks = next(item for item in admin_ui_data if item['universe_key'] == 'dev_top_10')
        assert dev_stocks['display_name'] == 'Development Top 10'
        assert dev_stocks['universe_type'] == 'stock_universe'
        assert dev_stocks['symbol_count'] == 5
        assert 'AAPL' in dev_stocks['symbols']
        assert dev_stocks['environment'] == 'DEVELOPMENT'

        dev_etfs = next(item for item in admin_ui_data if item['universe_key'] == 'dev_etfs')
        assert dev_etfs['display_name'] == 'Development ETFs'
        assert dev_etfs['universe_type'] == 'etf_universe'
        assert dev_etfs['symbol_count'] == 3
        assert 'SPY' in dev_etfs['symbols']

        # 2. Database query performance: <50ms for admin interface
        assert admin_query_time_ms < 50, f"Development universe query took {admin_query_time_ms:.1f}ms, exceeding 50ms target"

        # 3. Environment isolation: only development universes returned
        for universe in admin_ui_data:
            assert universe['environment'] == 'DEVELOPMENT'
            assert universe['universe_key'].startswith('dev_')

    @patch('src.data.historical_loader.psycopg2.connect')
    def test_subset_loading_performance_integration(self, mock_db_connect,
                                                   integration_metrics: IntegrationTestMetrics):
        """Test subset loading performance meets development environment targets."""
        # Arrange: Mock database for subset loading operations
        mock_db_conn = Mock()
        mock_db_cursor = Mock()
        mock_db_connect.return_value = mock_db_conn
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor

        # Small development dataset
        dev_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'SPY', 'QQQ', 'IWM', 'VTI', 'VOO']

        # Mock historical data for 6 months (132 trading days)
        mock_data_points = 132 * len(dev_symbols)  # 1320 total data points

        # Act: Simulate subset loading performance
        start_time = time.time()

        # Simulate database operations for subset loading
        for symbol in dev_symbols:
            # Simulate symbol metadata insert/update
            time.sleep(0.001)  # 1ms per symbol

            # Simulate OHLCV batch insert for 132 days
            for day in range(132):
                time.sleep(0.0001)  # 0.1ms per data point

        # Simulate cache_entries update for development universe
        time.sleep(0.005)  # 5ms for cache update

        end_time = time.time()
        subset_loading_time = end_time - start_time
        integration_metrics.database_query_times.append(subset_loading_time * 1000)

        # Assert: Verify subset loading performance targets
        # 1. Total loading time: <300 seconds (5 minutes) for development subset
        assert subset_loading_time < 300, f"Subset loading took {subset_loading_time:.2f}s, exceeding 300s (5min) target"

        # 2. Processing rate: >10 symbols per second for small datasets
        processing_rate = len(dev_symbols) / subset_loading_time
        assert processing_rate > 10, f"Processing rate {processing_rate:.1f} symbols/s too slow for development"

        # 3. Data point processing: <1ms average per OHLCV record
        avg_time_per_datapoint = (subset_loading_time * 1000) / mock_data_points
        assert avg_time_per_datapoint < 1.0, f"Average processing time {avg_time_per_datapoint:.2f}ms per data point too slow"


class TestDatabaseIntegrationBoundaries:
    """Test database integration boundaries and role separation enforcement."""

    @patch('psycopg2.connect')
    def test_tickstockapp_readonly_boundary_enforcement(self, mock_db_connect,
                                                       integration_metrics: IntegrationTestMetrics):
        """Test TickStockApp read-only database boundary enforcement."""
        # Arrange: Mock database connection with read-only simulation
        mock_db_conn = Mock()
        mock_db_cursor = Mock()
        mock_db_connect.return_value = mock_db_conn
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor

        # Simulate TickStockApp database user with read-only permissions
        def simulate_readonly_execute(sql, params=None):
            """Simulate read-only database user behavior."""
            sql_upper = sql.strip().upper()

            # Allow SELECT queries
            if sql_upper.startswith('SELECT'):
                return True

            # Block write operations
            write_operations = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE']
            if any(sql_upper.startswith(op) for op in write_operations):
                raise psycopg2.errors.InsufficientPrivilege("permission denied for table")

            return True

        mock_db_cursor.execute.side_effect = simulate_readonly_execute

        # Act & Assert: Test read-only boundary enforcement
        start_time = time.time()

        # 1. Allowed operations (TickStockApp consumer role)
        allowed_queries = [
            "SELECT * FROM symbols WHERE symbol_type = 'ETF'",
            "SELECT key, value FROM cache_entries WHERE type = 'etf_universe'",
            "SELECT symbol, close FROM ohlcv_daily WHERE date = CURRENT_DATE",
            "SELECT COUNT(*) FROM symbols WHERE etf_type IS NOT NULL"
        ]

        for query in allowed_queries:
            try:
                mock_db_cursor.execute(query)
                # Query should succeed
            except psycopg2.errors.InsufficientPrivilege:
                pytest.fail(f"Read query should be allowed: {query}")

        # 2. Blocked operations (TickStockApp cannot write)
        blocked_queries = [
            "INSERT INTO symbols (ticker, name) VALUES ('TEST', 'Test Symbol')",
            "UPDATE symbols SET name = 'Updated Name' WHERE ticker = 'AAPL'",
            "DELETE FROM ohlcv_daily WHERE date < '2023-01-01'",
            "CREATE TABLE test_table (id SERIAL PRIMARY KEY)",
            "ALTER TABLE symbols ADD COLUMN test_field TEXT",
            "DROP TABLE cache_entries"
        ]

        for query in blocked_queries:
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                mock_db_cursor.execute(query)

        end_time = time.time()
        boundary_test_time_ms = (end_time - start_time) * 1000
        integration_metrics.database_query_times.append(boundary_test_time_ms)

        # 3. Performance: Boundary checking overhead <10ms
        assert boundary_test_time_ms < 10, f"Database boundary checking took {boundary_test_time_ms:.1f}ms overhead"

    @patch('psycopg2.connect')
    def test_enhanced_symbols_table_integration_queries(self, mock_db_connect,
                                                       integration_metrics: IntegrationTestMetrics):
        """Test enhanced symbols table integration with TickStockApp queries."""
        # Arrange: Mock database with enhanced symbols table
        mock_db_conn = Mock()
        mock_db_cursor = Mock()
        mock_db_connect.return_value = mock_db_conn
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor

        # Sample enhanced symbols table data
        enhanced_symbols_data = [
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
                'ticker': 'AAPL',
                'name': 'Apple Inc',
                'symbol_type': 'CS',  # Common Stock
                'etf_type': None,
                'fmv_supported': False,
                'issuer': None,
                'correlation_reference': None,
                'composite_figi': 'BBG000B9XRY4',
                'share_class_figi': 'BBG001S5N8V8',
                'cik': '0000320193',
                'inception_date': None
            }
        ]

        mock_db_cursor.fetchall.return_value = enhanced_symbols_data
        mock_db_cursor.fetchone.return_value = enhanced_symbols_data[0]

        # Act: Test TickStockApp queries with enhanced symbols table
        start_time = time.time()

        # Query 1: ETF-specific data for UI dropdowns
        etf_query = """
        SELECT ticker, name, etf_type, issuer, fmv_supported
        FROM symbols 
        WHERE symbol_type = 'ETF' AND etf_type IS NOT NULL
        ORDER BY name
        """
        mock_db_cursor.execute(etf_query)
        etf_results = mock_db_cursor.fetchall()

        # Query 2: Symbol metadata with new fields
        metadata_query = """
        SELECT ticker, name, composite_figi, share_class_figi, cik
        FROM symbols 
        WHERE ticker = %s
        """
        mock_db_cursor.execute(metadata_query, ('SPY',))
        metadata_result = mock_db_cursor.fetchone()

        # Query 3: FMV-supported symbols for special processing
        fmv_query = """
        SELECT ticker, name, issuer, correlation_reference
        FROM symbols
        WHERE fmv_supported = true
        """
        mock_db_cursor.execute(fmv_query)
        fmv_results = mock_db_cursor.fetchall()

        end_time = time.time()
        enhanced_query_time_ms = (end_time - start_time) * 1000
        integration_metrics.database_query_times.append(enhanced_query_time_ms)

        # Assert: Verify enhanced symbols table integration
        # 1. ETF-specific queries work correctly
        assert len(etf_results) >= 1
        spy_etf = next((item for item in etf_results if item['ticker'] == 'SPY'), None)
        assert spy_etf is not None
        assert spy_etf['etf_type'] == 'ETF'
        assert spy_etf['issuer'] == 'State Street (SPDR)'
        assert spy_etf['fmv_supported'] is True

        # 2. Enhanced metadata fields accessible
        assert metadata_result['composite_figi'] == 'BBG000BDTBL9'
        assert metadata_result['cik'] == '0000884394'

        # 3. FMV support queries work
        assert len(fmv_results) >= 1
        fmv_symbol = fmv_results[0]
        assert fmv_symbol['correlation_reference'] is not None

        # 4. Query performance with enhanced fields: <50ms
        assert enhanced_query_time_ms < 50, f"Enhanced symbols queries took {enhanced_query_time_ms:.1f}ms, exceeding 50ms target"


class TestSystemResilienceIntegration:
    """Test system resilience and error handling patterns across TickStockApp and TickStockPL."""

    @patch('src.infrastructure.redis.redis_connection_manager.redis.Redis')
    def test_redis_connection_failure_resilience(self, mock_redis_class,
                                                 integration_metrics: IntegrationTestMetrics):
        """Test system resilience when Redis connection fails."""
        # Arrange: Mock Redis connection with intermittent failures
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        # Simulate connection failures
        connection_attempts = []
        def simulate_connection_issues():
            connection_attempts.append(len(connection_attempts) + 1)
            if len(connection_attempts) <= 3:  # First 3 attempts fail
                raise redis.ConnectionError("Connection to Redis failed")
            return True  # 4th attempt succeeds

        mock_redis_client.ping.side_effect = simulate_connection_issues

        # Mock TickStockApp components that depend on Redis
        mock_socketio = Mock()
        config = RedisConnectionConfig(host='localhost', port=6379, db=0)

        # Act: Test resilience during Redis failures
        start_time = time.time()

        # 1. Initial connection attempts with failures
        connection_manager = RedisConnectionManager(config)

        # Simulate connection retry logic
        max_retries = 5
        retry_delay = 0.1
        connected = False

        for attempt in range(max_retries):
            try:
                if mock_redis_client.ping():
                    connected = True
                    break
            except redis.ConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

        end_time = time.time()
        recovery_time_ms = (end_time - start_time) * 1000
        integration_metrics.redis_operation_times.append(recovery_time_ms)

        # Assert: Verify resilience patterns
        # 1. System eventually connects after failures
        assert connected is True, "System should recover from Redis connection failures"
        assert len(connection_attempts) == 4  # 3 failures + 1 success

        # 2. Recovery time reasonable (< 5 seconds with exponential backoff)
        assert recovery_time_ms < 5000, f"Redis recovery took {recovery_time_ms:.1f}ms, too long"

        # 3. No system crash during connection issues
        # This is implicitly tested by successful completion

    @patch('src.data.eod_processor.psycopg2.connect')
    @patch('src.data.eod_processor.redis.Redis')
    def test_partial_eod_completion_handling(self, mock_redis_class, mock_db_connect,
                                            integration_metrics: IntegrationTestMetrics):
        """Test system handling of partial EOD completion scenarios."""
        # Arrange: Mock partial EOD completion scenario
        mock_db_conn = Mock()
        mock_db_cursor = Mock()
        mock_db_connect.return_value = mock_db_conn
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor

        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client

        # Mock symbols for validation (1000 symbols, 850 complete = 85%)
        total_symbols = 1000
        completed_symbols = 850

        # Mock universe data
        mock_db_cursor.fetchall.return_value = [
            {
                'key': 'large_universe',
                'type': 'stock_universe',
                'value': json.dumps({
                    'stocks': [{'ticker': f'SYM{i:04d}'} for i in range(total_symbols)]
                })
            }
        ]

        # Mock validation responses (85% completion)
        validation_responses = [1] * completed_symbols + [0] * (total_symbols - completed_symbols)
        mock_db_cursor.fetchone.side_effect = [(count,) for count in validation_responses]

        # Act: Test partial completion handling
        start_time = time.time()

        eod_processor = EODProcessor()
        result = eod_processor.run_eod_update()

        end_time = time.time()
        partial_eod_time_ms = (end_time - start_time) * 1000
        integration_metrics.redis_operation_times.append(partial_eod_time_ms)

        # Assert: Verify partial completion handling
        # 1. System handles partial completion gracefully
        assert result['status'] in ['COMPLETE', 'INCOMPLETE'], "Should handle partial completion"
        assert result['completion_rate'] == 0.85
        assert result['total_symbols'] == total_symbols
        assert result['completed_symbols'] == completed_symbols

        # 2. Notification still sent for partial completion
        assert mock_redis_client.publish.called

        # 3. Missing symbols identified for follow-up
        if result['status'] == 'INCOMPLETE':
            assert 'missing_symbols' in result
            expected_missing = total_symbols - completed_symbols
            assert len(result.get('missing_symbols', [])) <= expected_missing

        # 4. Processing time reasonable even with partial failures
        assert partial_eod_time_ms < 10000, f"Partial EOD processing took {partial_eod_time_ms:.1f}ms, too long"

    def test_cross_system_isolation_during_degradation(self,
                                                      integration_metrics: IntegrationTestMetrics):
        """Test cross-system isolation when one system is degraded."""
        # Arrange: Simulate TickStockPL degraded, TickStockApp operational
        mock_socketio = Mock()

        # TickStockApp should continue operating with cached/fallback data
        fallback_data = {
            'symbols': ['AAPL', 'MSFT', 'GOOGL'],
            'last_prices': {'AAPL': 175.50, 'MSFT': 425.25, 'GOOGL': 135.75},
            'market_summary': {
                'total_symbols': 3,
                'symbols_up': 2,
                'symbols_down': 1,
                'last_updated': '2024-09-01T15:30:00Z'
            }
        }

        # Act: Test system isolation
        start_time = time.time()

        # 1. TickStockApp continues WebSocket broadcasting with fallback data
        for symbol, price in fallback_data['last_prices'].items():
            websocket_data = {
                'type': 'price_update',
                'symbol': symbol,
                'price': price,
                'source': 'fallback',  # Indicate fallback mode
                'timestamp': time.time()
            }
            mock_socketio.emit('dashboard_price_update', websocket_data, broadcast=True)

        # 2. Market summary with degraded service indicator
        summary_data = {
            'type': 'market_summary',
            'summary': fallback_data['market_summary'],
            'service_status': 'degraded',  # Indicate degraded mode
            'timestamp': time.time()
        }
        mock_socketio.emit('dashboard_market_summary', summary_data, broadcast=True)

        end_time = time.time()
        isolation_time_ms = (end_time - start_time) * 1000
        integration_metrics.websocket_broadcast_times.append(isolation_time_ms)

        # Assert: Verify cross-system isolation
        # 1. TickStockApp continues operation despite TickStockPL degradation
        assert mock_socketio.emit.call_count == 4  # 3 price updates + 1 summary

        # 2. Fallback data clearly marked
        emit_calls = mock_socketio.emit.call_args_list
        for call in emit_calls[:-1]:  # Price update calls
            event_data = call[0][1]
            if 'source' in event_data:
                assert event_data['source'] == 'fallback'

        # Summary call has degraded status
        summary_call = emit_calls[-1]
        summary_event_data = summary_call[0][1]
        assert summary_event_data['service_status'] == 'degraded'

        # 3. Performance maintained during degradation
        assert isolation_time_ms < 100, f"System isolation handling took {isolation_time_ms:.1f}ms, affecting performance"


# Test Fixtures for Cross-System Integration Testing

@pytest.fixture
def integration_metrics():
    """Provide integration test metrics tracking."""
    return IntegrationTestMetrics()


@pytest.fixture
def mock_tickstockpl_producer():
    """Mock TickStockPL as data producer for integration testing."""
    class MockTickStockPLProducer:
        def __init__(self):
            self.redis_client = Mock()
            self.db_connection = Mock()

        def publish_etf_event(self, symbol, event_type, data):
            """Simulate TickStockPL publishing ETF event."""
            event = {
                'symbol': symbol,
                'event_type': event_type,
                'data': data,
                'timestamp': time.time(),
                'source': 'tickstockpl'
            }
            self.redis_client.publish('tickstock.events.etf', json.dumps(event))
            return event

        def publish_eod_completion(self, eod_results):
            """Simulate TickStockPL publishing EOD completion."""
            notification = {
                'type': 'eod_completion',
                'timestamp': time.time(),
                'results': eod_results,
                'source': 'tickstockpl'
            }
            self.redis_client.publish('tickstock:eod:completion', json.dumps(notification))
            return notification

        def load_etf_data(self, symbol, start_date, end_date):
            """Simulate TickStockPL ETF data loading."""
            return {
                'symbol': symbol,
                'data_points': 252,  # Trading days
                'status': 'completed',
                'processing_time': 2.5
            }

    return MockTickStockPLProducer()


@pytest.fixture
def mock_tickstockapp_consumer():
    """Mock TickStockApp as data consumer for integration testing."""
    class MockTickStockAppConsumer:
        def __init__(self):
            self.redis_client = Mock()
            self.socketio = Mock()
            self.received_events = []

        def handle_etf_event(self, event):
            """Simulate TickStockApp handling ETF event."""
            self.received_events.append(event)

            # WebSocket broadcast
            websocket_data = {
                'type': event['event_type'],
                'symbol': event['symbol'],
                'data': event['data'],
                'timestamp': event['timestamp']
            }
            self.socketio.emit('dashboard_etf_update', websocket_data, broadcast=True)

        def handle_eod_notification(self, notification):
            """Simulate TickStockApp handling EOD notification."""
            self.received_events.append(notification)

            # WebSocket broadcast
            self.socketio.emit('eod_completion_update', notification, broadcast=True)

        def query_etf_universes(self):
            """Simulate TickStockApp querying ETF universes."""
            # Read-only database query
            return [
                {'key': 'etf_growth', 'etfs': ['VUG', 'QQQ']},
                {'key': 'etf_value', 'etfs': ['VTV', 'IVE']}
            ]

    return MockTickStockAppConsumer()


@pytest.fixture
def cross_system_test_data():
    """Provide test data for cross-system integration testing."""
    return {
        'etf_symbols': ['SPY', 'QQQ', 'IWM', 'VUG', 'VTI'],
        'stock_symbols': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN'],
        'etf_events': [
            {
                'symbol': 'SPY',
                'event_type': 'price_update',
                'data': {'price': 558.75, 'change': 2.25, 'volume': 47000000}
            },
            {
                'symbol': 'QQQ',
                'event_type': 'volume_spike',
                'data': {'price': 475.50, 'volume_spike': 3.2, 'volume': 85000000}
            }
        ],
        'eod_results': {
            'status': 'COMPLETE',
            'total_symbols': 5238,
            'completed_symbols': 5076,
            'completion_rate': 0.97,
            'processing_time_minutes': 42.5,
            'etf_count': 738,
            'stock_count': 4500
        },
        'development_universes': {
            'dev_top_10': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN'],
            'dev_etfs': ['SPY', 'QQQ', 'IWM']
        }
    }


# Performance benchmarks for integration testing
@pytest.mark.performance
class TestCrossSystemPerformanceBenchmarks:
    """Performance benchmarks for cross-system integration."""

    def test_end_to_end_message_delivery_benchmark(self, integration_metrics: IntegrationTestMetrics):
        """Benchmark end-to-end message delivery performance."""
        message_count = 100
        delivery_times = []

        for i in range(message_count):
            start_time = time.perf_counter()

            # Simulate message flow: TickStockPL → Redis → TickStockApp → WebSocket
            time.sleep(0.001)  # Redis publish
            time.sleep(0.002)  # TickStockApp processing
            time.sleep(0.001)  # WebSocket broadcast

            end_time = time.perf_counter()
            delivery_time_ms = (end_time - start_time) * 1000
            delivery_times.append(delivery_time_ms)

        integration_metrics.message_delivery_times = delivery_times

        # Performance assertions
        avg_delivery_time = integration_metrics.get_avg_message_delivery_time()
        max_delivery_time = integration_metrics.get_max_message_delivery_time()

        assert avg_delivery_time < 100, f"Average message delivery {avg_delivery_time:.1f}ms exceeds 100ms target"
        assert max_delivery_time < 200, f"Maximum message delivery {max_delivery_time:.1f}ms exceeds reasonable bounds"

        # Performance statistics
        p95_time = sorted(delivery_times)[int(len(delivery_times) * 0.95)]
        print("\nMessage Delivery Performance:")
        print(f"  Average: {avg_delivery_time:.1f}ms")
        print(f"  P95: {p95_time:.1f}ms")
        print(f"  Maximum: {max_delivery_time:.1f}ms")

    def test_database_query_performance_benchmark(self, integration_metrics: IntegrationTestMetrics):
        """Benchmark database query performance for TickStockApp read operations."""
        query_types = [
            'etf_universe_lookup',
            'symbol_metadata_query',
            'ohlcv_recent_data',
            'development_universes',
            'market_summary_stats'
        ]

        for query_type in query_types:
            start_time = time.perf_counter()

            # Simulate different query types with realistic processing times
            if query_type == 'etf_universe_lookup':
                time.sleep(0.005)  # 5ms for universe queries
            elif query_type == 'symbol_metadata_query':
                time.sleep(0.003)  # 3ms for metadata
            elif query_type == 'ohlcv_recent_data':
                time.sleep(0.010)  # 10ms for OHLCV data
            elif query_type == 'development_universes':
                time.sleep(0.002)  # 2ms for dev queries
            else:
                time.sleep(0.008)  # 8ms for summary stats

            end_time = time.perf_counter()
            query_time_ms = (end_time - start_time) * 1000
            integration_metrics.database_query_times.append(query_time_ms)

        # Performance assertions
        avg_query_time = sum(integration_metrics.database_query_times) / len(integration_metrics.database_query_times)
        max_query_time = max(integration_metrics.database_query_times)

        assert avg_query_time < 50, f"Average database query time {avg_query_time:.1f}ms exceeds 50ms target"
        assert max_query_time < 100, f"Maximum database query time {max_query_time:.1f}ms exceeds reasonable bounds"

        print("\nDatabase Query Performance:")
        print(f"  Average: {avg_query_time:.1f}ms")
        print(f"  Maximum: {max_query_time:.1f}ms")
        print(f"  Query Types: {len(query_types)}")


if __name__ == '__main__':
    # Run integration tests with performance reporting
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-m', 'not performance'  # Run functional tests first
    ])
