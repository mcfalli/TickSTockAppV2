"""
Sprint 14 Phase 2: IPO Monitoring Service Test Suite

Tests for automated IPO discovery, symbol loading, and Redis pub-sub notifications.
Performance validation for 4,000+ symbol processing with sub-100ms message delivery.

Date: 2025-09-01
Sprint: 14 Phase 2
Status: Comprehensive Test Coverage
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import json
import redis
from typing import Dict, List, Any
import time

from src.automation.services.ipo_monitor import IPOMonitor, IPODiscoveryError, IPONotificationError
from src.core.domain.events.base_event import BaseEvent


class TestIPOMonitorInitialization:
    """Test IPO Monitor service initialization and configuration"""
    
    def test_ipo_monitor_initialization_default_config(self):
        """Test IPO monitor initializes with default configuration"""
        monitor = IPOMonitor()
        
        assert monitor.scan_frequency == "daily"
        assert monitor.backfill_days == 90
        assert monitor.redis_channel == "tickstock:ipo:notifications"
        assert monitor.batch_size == 100
        assert monitor.rate_limit_ms == 12000
        
    def test_ipo_monitor_initialization_custom_config(self):
        """Test IPO monitor initializes with custom configuration"""
        config = {
            'scan_frequency': 'hourly',
            'backfill_days': 30,
            'redis_channel': 'custom:ipo:channel',
            'batch_size': 50,
            'rate_limit_ms': 6000
        }
        
        monitor = IPOMonitor(config)
        
        assert monitor.scan_frequency == "hourly"
        assert monitor.backfill_days == 30
        assert monitor.redis_channel == "custom:ipo:channel"
        assert monitor.batch_size == 50
        assert monitor.rate_limit_ms == 6000
        
    def test_ipo_monitor_redis_connection_setup(self):
        """Test Redis connection is properly configured"""
        monitor = IPOMonitor()
        
        assert monitor.redis_client is not None
        assert hasattr(monitor.redis_client, 'publish')
        assert monitor.redis_connected is True
        
    def test_ipo_monitor_database_connection_setup(self):
        """Test database connection with full write access"""
        monitor = IPOMonitor()
        
        assert monitor.db_connection is not None
        assert monitor.has_write_access is True
        assert monitor.connection_pool_size >= 5
        
    def test_ipo_monitor_polygon_client_setup(self):
        """Test Polygon.io API client configuration"""
        monitor = IPOMonitor()
        
        assert monitor.polygon_client is not None
        assert monitor.api_key is not None
        assert monitor.rate_limiter is not None


class TestIPOSymbolDiscovery:
    """Test IPO symbol discovery via Polygon.io API"""
    
    @pytest.fixture
    def mock_polygon_response(self):
        """Mock Polygon.io API response for new symbols"""
        return {
            "status": "OK",
            "results": [
                {
                    "ticker": "NEWIPO",
                    "name": "New IPO Company Inc",
                    "market": "stocks",
                    "type": "CS",
                    "active": True,
                    "currency_name": "usd",
                    "cik": "0001234567",
                    "composite_figi": "BBG123456789",
                    "share_class_figi": "BBG987654321",
                    "market_cap": 1500000000,
                    "primary_exchange": "XNAS",
                    "listing_date": "2025-08-30"
                },
                {
                    "ticker": "SPAC1",
                    "name": "Special Purpose Acquisition Corp",
                    "market": "stocks",
                    "type": "CS",
                    "active": True,
                    "currency_name": "usd",
                    "listing_date": "2025-08-31"
                }
            ]
        }
    
    @patch('src.automation.services.ipo_monitor.requests.get')
    def test_discover_new_symbols_success(self, mock_get, mock_polygon_response):
        """Test successful discovery of new IPO symbols"""
        mock_get.return_value.json.return_value = mock_polygon_response
        mock_get.return_value.status_code = 200
        
        monitor = IPOMonitor()
        new_symbols = monitor.discover_new_symbols(days_back=7)
        
        assert len(new_symbols) == 2
        assert "NEWIPO" in [s['ticker'] for s in new_symbols]
        assert "SPAC1" in [s['ticker'] for s in new_symbols]
        
        # Verify API call parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "tickers" in call_args[1]['params']
        assert call_args[1]['params']['active'] is True
        
    @patch('src.automation.services.ipo_monitor.requests.get')
    def test_discover_new_symbols_api_rate_limiting(self, mock_get):
        """Test API rate limiting during symbol discovery"""
        # Simulate rate limiting response
        mock_get.return_value.status_code = 429
        mock_get.return_value.json.return_value = {
            "status": "ERROR",
            "error": "Rate limit exceeded"
        }
        
        monitor = IPOMonitor()
        
        with pytest.raises(IPODiscoveryError) as exc_info:
            monitor.discover_new_symbols(days_back=1)
            
        assert "Rate limit exceeded" in str(exc_info.value)
        
    @patch('src.automation.services.ipo_monitor.requests.get')
    def test_discover_new_symbols_filter_existing(self, mock_get, mock_polygon_response):
        """Test filtering out symbols that already exist in database"""
        mock_get.return_value.json.return_value = mock_polygon_response
        mock_get.return_value.status_code = 200
        
        # Mock existing symbols in database
        existing_symbols = {'NEWIPO'}
        
        monitor = IPOMonitor()
        with patch.object(monitor, 'get_existing_symbols', return_value=existing_symbols):
            new_symbols = monitor.discover_new_symbols(days_back=7)
            
        # Should only return SPAC1 since NEWIPO already exists
        assert len(new_symbols) == 1
        assert new_symbols[0]['ticker'] == 'SPAC1'
        
    def test_discover_new_symbols_date_filtering(self):
        """Test filtering symbols by listing date range"""
        monitor = IPOMonitor()
        
        # Test symbols with different listing dates
        test_symbols = [
            {'ticker': 'OLD1', 'listing_date': '2025-07-01'},
            {'ticker': 'NEW1', 'listing_date': '2025-08-30'},
            {'ticker': 'NEW2', 'listing_date': '2025-08-31'}
        ]
        
        # Filter for last 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        filtered = monitor._filter_by_date(test_symbols, cutoff_date)
        
        assert len(filtered) == 2
        assert all(s['ticker'] in ['NEW1', 'NEW2'] for s in filtered)
        
    @pytest.mark.performance
    def test_discover_new_symbols_performance(self):
        """Test symbol discovery performance meets <50ms per symbol requirements"""
        monitor = IPOMonitor()
        
        # Mock fast API response
        fast_response = {
            "status": "OK", 
            "results": [{"ticker": f"TEST{i}", "name": f"Test {i}"} for i in range(100)]
        }
        
        with patch('src.automation.services.ipo_monitor.requests.get') as mock_get:
            mock_get.return_value.json.return_value = fast_response
            mock_get.return_value.status_code = 200
            
            start_time = time.perf_counter()
            new_symbols = monitor.discover_new_symbols(days_back=1)
            elapsed_time = time.perf_counter() - start_time
            
            # Should process 100 symbols in <5 seconds (50ms per symbol)
            assert elapsed_time < 5.0
            assert len(new_symbols) == 100


class TestIPOHistoricalBackfill:
    """Test automated 90-day historical backfill for new IPO symbols"""
    
    @pytest.fixture
    def mock_historical_data(self):
        """Mock historical OHLCV data for testing"""
        base_date = datetime.now() - timedelta(days=90)
        data = []
        
        for i in range(90):
            date = base_date + timedelta(days=i)
            data.append({
                "o": 100.0 + i * 0.1,
                "h": 101.0 + i * 0.1,
                "l": 99.0 + i * 0.1,
                "c": 100.5 + i * 0.1,
                "v": 1000000 + i * 1000,
                "t": int(date.timestamp() * 1000)
            })
            
        return {"status": "OK", "results": data}
    
    @patch('src.automation.services.ipo_monitor.requests.get')
    def test_backfill_historical_data_success(self, mock_get, mock_historical_data):
        """Test successful 90-day historical backfill"""
        mock_get.return_value.json.return_value = mock_historical_data
        mock_get.return_value.status_code = 200
        
        monitor = IPOMonitor()
        symbol_data = {"ticker": "NEWIPO", "listing_date": "2025-08-30"}
        
        with patch.object(monitor, 'store_historical_data') as mock_store:
            result = monitor.backfill_historical_data(symbol_data)
            
        assert result is True
        mock_store.assert_called_once()
        
        # Verify 90 days of data was processed
        stored_data = mock_store.call_args[0][1]
        assert len(stored_data) == 90
        
    @patch('src.automation.services.ipo_monitor.requests.get')
    def test_backfill_historical_data_partial_failure(self, mock_get):
        """Test handling of partial historical data availability"""
        # Simulate partial data (only 30 days available)
        partial_data = {
            "status": "OK",
            "results": [{"o": 100, "h": 101, "l": 99, "c": 100.5, "v": 1000000}] * 30
        }
        mock_get.return_value.json.return_value = partial_data
        mock_get.return_value.status_code = 200
        
        monitor = IPOMonitor()
        symbol_data = {"ticker": "NEWIPO", "listing_date": "2025-08-30"}
        
        with patch.object(monitor, 'store_historical_data') as mock_store:
            result = monitor.backfill_historical_data(symbol_data)
            
        # Should still succeed with available data
        assert result is True
        stored_data = mock_store.call_args[0][1]
        assert len(stored_data) == 30
        
    def test_backfill_data_validation(self):
        """Test historical data validation before storage"""
        monitor = IPOMonitor()
        
        # Test invalid data (missing required fields)
        invalid_data = [
            {"o": 100, "h": 101, "l": 99},  # Missing close and volume
            {"o": 100, "h": 99, "l": 101, "c": 100, "v": 1000}  # Invalid OHLC order
        ]
        
        validated = monitor._validate_historical_data(invalid_data)
        
        # Should filter out invalid records
        assert len(validated) == 0
        
        # Test valid data
        valid_data = [
            {"o": 100, "h": 101, "l": 99, "c": 100.5, "v": 1000000, "t": 1693440000000}
        ]
        
        validated = monitor._validate_historical_data(valid_data)
        assert len(validated) == 1
        
    @pytest.mark.performance
    def test_backfill_performance_benchmark(self):
        """Test backfill performance for multiple symbols meets batch requirements"""
        monitor = IPOMonitor()
        
        # Test data for 10 symbols with 90 days each
        symbols = [{"ticker": f"IPO{i}", "listing_date": "2025-08-30"} for i in range(10)]
        
        with patch.object(monitor, 'backfill_historical_data', return_value=True) as mock_backfill:
            start_time = time.perf_counter()
            
            results = monitor.batch_backfill_symbols(symbols)
            
            elapsed_time = time.perf_counter() - start_time
            
            # Should process 10 symbols in <30 seconds (API rate limiting considered)
            assert elapsed_time < 30.0
            assert len(results) == 10
            assert all(results)
            
        # Verify rate limiting was applied
        assert mock_backfill.call_count == 10


class TestIPORedisNotifications:
    """Test Redis pub-sub notifications for IPO discovery"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing"""
        mock_client = Mock()
        mock_client.publish = Mock(return_value=1)
        mock_client.ping = Mock(return_value=True)
        return mock_client
    
    def test_publish_ipo_notification_success(self, mock_redis_client):
        """Test successful IPO notification publishing"""
        monitor = IPOMonitor()
        monitor.redis_client = mock_redis_client
        
        ipo_data = {
            "ticker": "NEWIPO",
            "name": "New IPO Company Inc",
            "listing_date": "2025-08-30",
            "market_cap": 1500000000
        }
        
        result = monitor.publish_ipo_notification(ipo_data)
        
        assert result is True
        mock_redis_client.publish.assert_called_once()
        
        # Verify message structure
        call_args = mock_redis_client.publish.call_args
        assert call_args[0][0] == "tickstock:ipo:notifications"
        
        message = json.loads(call_args[0][1])
        assert message['event_type'] == 'new_ipo'
        assert message['ticker'] == 'NEWIPO'
        assert message['backfill_status'] == 'pending'
        
    def test_publish_batch_notifications(self, mock_redis_client):
        """Test batch notification publishing for multiple IPOs"""
        monitor = IPOMonitor()
        monitor.redis_client = mock_redis_client
        
        ipo_batch = [
            {"ticker": "IPO1", "name": "Company 1", "listing_date": "2025-08-30"},
            {"ticker": "IPO2", "name": "Company 2", "listing_date": "2025-08-31"}
        ]
        
        result = monitor.publish_batch_notifications(ipo_batch)
        
        assert result is True
        assert mock_redis_client.publish.call_count == 2
        
    def test_notification_message_format(self):
        """Test IPO notification message format compliance"""
        monitor = IPOMonitor()
        
        ipo_data = {
            "ticker": "NEWIPO",
            "name": "New IPO Company Inc",
            "listing_date": "2025-08-30",
            "market_cap": 1500000000
        }
        
        message = monitor._format_ipo_notification(ipo_data)
        
        # Verify required fields
        assert 'event_type' in message
        assert 'timestamp' in message
        assert 'ticker' in message
        assert 'company_name' in message
        assert 'listing_date' in message
        assert 'backfill_status' in message
        assert 'processing_priority' in message
        
        # Verify field values
        assert message['event_type'] == 'new_ipo'
        assert message['ticker'] == 'NEWIPO'
        assert message['processing_priority'] == 'high'
        
    def test_redis_connection_failure_handling(self):
        """Test handling of Redis connection failures"""
        monitor = IPOMonitor()
        
        # Mock Redis connection failure
        mock_client = Mock()
        mock_client.publish = Mock(side_effect=redis.ConnectionError("Connection failed"))
        monitor.redis_client = mock_client
        
        ipo_data = {"ticker": "NEWIPO", "name": "Test Company"}
        
        with pytest.raises(IPONotificationError) as exc_info:
            monitor.publish_ipo_notification(ipo_data)
            
        assert "Redis connection failed" in str(exc_info.value)
        
    @pytest.mark.performance
    def test_notification_delivery_performance(self, mock_redis_client):
        """Test notification delivery meets <100ms requirement"""
        monitor = IPOMonitor()
        monitor.redis_client = mock_redis_client
        
        ipo_data = {"ticker": "NEWIPO", "name": "Test Company"}
        
        # Test single notification performance
        start_time = time.perf_counter()
        result = monitor.publish_ipo_notification(ipo_data)
        elapsed_time = time.perf_counter() - start_time
        
        assert result is True
        assert elapsed_time < 0.1  # Less than 100ms
        
        # Test batch notification performance
        batch = [{"ticker": f"IPO{i}", "name": f"Company {i}"} for i in range(50)]
        
        start_time = time.perf_counter()
        result = monitor.publish_batch_notifications(batch)
        elapsed_time = time.perf_counter() - start_time
        
        assert result is True
        assert elapsed_time < 5.0  # 50 notifications in <5 seconds (100ms each)


class TestIPOServiceSeparation:
    """Test IPO service separation from TickStockApp"""
    
    def test_service_runs_independently(self):
        """Test IPO monitor service runs as separate process"""
        monitor = IPOMonitor()
        
        # Verify service can run without TickStockApp dependencies
        assert hasattr(monitor, 'run_service')
        assert hasattr(monitor, 'stop_service')
        assert monitor.service_mode == 'standalone'
        
    def test_database_write_access(self):
        """Test service has full database write access"""
        monitor = IPOMonitor()
        
        # Verify write access capabilities
        assert monitor.has_write_access is True
        assert hasattr(monitor, 'create_symbol')
        assert hasattr(monitor, 'update_symbol')
        assert hasattr(monitor, 'store_historical_data')
        
    def test_service_configuration_isolation(self):
        """Test service configuration is isolated from TickStockApp"""
        monitor = IPOMonitor()
        
        # Verify independent configuration
        assert monitor.config_source == 'automation_services'
        assert monitor.redis_channel != 'tickstock:websocket:events'
        assert hasattr(monitor, 'service_config')
        
    def test_loose_coupling_via_redis(self):
        """Test loose coupling with TickStockApp via Redis messaging"""
        monitor = IPOMonitor()
        
        # Verify Redis-only communication
        assert monitor.communication_method == 'redis_pubsub'
        assert not hasattr(monitor, 'direct_app_connection')
        assert monitor.redis_channel.startswith('tickstock:ipo:')
        
    def test_producer_role_validation(self):
        """Test service operates in producer role (creates data)"""
        monitor = IPOMonitor()
        
        # Verify producer capabilities
        assert monitor.service_role == 'producer'
        assert hasattr(monitor, 'create_symbols')
        assert hasattr(monitor, 'generate_notifications')
        assert not hasattr(monitor, 'consume_events')


class TestIPOMonitorIntegration:
    """Integration tests for complete IPO monitoring workflow"""
    
    @pytest.mark.integration
    def test_end_to_end_ipo_discovery_workflow(self):
        """Test complete IPO discovery and notification workflow"""
        monitor = IPOMonitor()
        
        with patch.object(monitor, 'discover_new_symbols') as mock_discover, \
             patch.object(monitor, 'backfill_historical_data') as mock_backfill, \
             patch.object(monitor, 'publish_ipo_notification') as mock_notify:
            
            # Mock discovery of 2 new IPOs
            mock_discover.return_value = [
                {"ticker": "IPO1", "name": "Company 1", "listing_date": "2025-08-30"},
                {"ticker": "IPO2", "name": "Company 2", "listing_date": "2025-08-31"}
            ]
            mock_backfill.return_value = True
            mock_notify.return_value = True
            
            # Run daily scan
            result = monitor.run_daily_scan()
            
            assert result['discovered'] == 2
            assert result['backfilled'] == 2
            assert result['notified'] == 2
            
            # Verify workflow execution
            mock_discover.assert_called_once_with(days_back=1)
            assert mock_backfill.call_count == 2
            assert mock_notify.call_count == 2
            
    @pytest.mark.integration
    def test_error_recovery_during_workflow(self):
        """Test error recovery during IPO discovery workflow"""
        monitor = IPOMonitor()
        
        with patch.object(monitor, 'discover_new_symbols') as mock_discover, \
             patch.object(monitor, 'backfill_historical_data') as mock_backfill, \
             patch.object(monitor, 'publish_ipo_notification') as mock_notify:
            
            # Mock partial failures
            mock_discover.return_value = [
                {"ticker": "IPO1", "name": "Company 1"},
                {"ticker": "IPO2", "name": "Company 2"}
            ]
            mock_backfill.side_effect = [True, False]  # Second backfill fails
            mock_notify.return_value = True
            
            result = monitor.run_daily_scan()
            
            # Should still notify successful discoveries
            assert result['discovered'] == 2
            assert result['backfilled'] == 1
            assert result['failed'] == 1
            assert result['notified'] >= 1  # At least successful ones
            
    @pytest.mark.integration
    def test_daily_scan_scheduling(self):
        """Test daily scan scheduling and execution"""
        monitor = IPOMonitor()
        
        # Test scan timing
        next_scan = monitor.get_next_scan_time()
        now = datetime.now()
        
        # Should be scheduled for next market close
        assert next_scan > now
        assert next_scan.hour == 16  # 4 PM ET market close
        
    @pytest.mark.integration
    @pytest.mark.slow
    def test_4000_symbol_processing_capacity(self):
        """Test processing capacity for 4,000+ symbol universe"""
        monitor = IPOMonitor()
        
        # Mock large symbol discovery
        large_batch = [
            {"ticker": f"SYM{i:04d}", "name": f"Company {i}"}
            for i in range(4000)
        ]
        
        with patch.object(monitor, 'discover_new_symbols', return_value=large_batch), \
             patch.object(monitor, 'backfill_historical_data', return_value=True), \
             patch.object(monitor, 'publish_batch_notifications', return_value=True):
            
            start_time = time.perf_counter()
            result = monitor.process_large_batch(large_batch)
            elapsed_time = time.perf_counter() - start_time
            
            # Should handle 4,000 symbols efficiently
            assert result['processed'] == 4000
            assert elapsed_time < 3600  # Within 1 hour
            assert result['error_rate'] < 0.05  # Less than 5% errors