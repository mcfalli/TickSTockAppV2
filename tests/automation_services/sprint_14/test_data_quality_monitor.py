"""
Sprint 14 Phase 2: Data Quality Monitoring Service Test Suite

Tests for automated data quality monitoring including price anomaly detection,
volume spike/drought analysis, data gap identification, and Redis alerting.

Date: 2025-09-01
Sprint: 14 Phase 2
Status: Comprehensive Test Coverage
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import redis
import numpy as np
from typing import Dict, List, Any, Tuple
import time

from src.automation.services.data_quality_monitor import (
    DataQualityMonitor, 
    PriceAnomalyError, 
    VolumeAnomalyError,
    DataQualityAlert
)


class TestDataQualityMonitorInitialization:
    """Test data quality monitor service initialization"""
    
    def test_monitor_initialization_default_config(self):
        """Test monitor initializes with default quality thresholds"""
        monitor = DataQualityMonitor()
        
        # Verify price anomaly thresholds
        assert monitor.price_anomaly_threshold == 0.20  # 20% single-day move
        assert monitor.price_spike_threshold == 0.25     # 25% spike threshold
        assert monitor.price_drop_threshold == -0.20     # 20% drop threshold
        
        # Verify volume anomaly thresholds
        assert monitor.volume_spike_threshold == 5.0     # 5x average volume
        assert monitor.volume_drought_threshold == 0.2   # 20% of average volume
        assert monitor.volume_analysis_days == 30        # 30-day average baseline
        
        # Verify data gap thresholds
        assert monitor.max_data_gap_hours == 24          # 24-hour gap alert
        assert monitor.staleness_threshold_hours == 2    # 2-hour staleness alert
        
    def test_monitor_initialization_custom_config(self):
        """Test monitor with custom configuration"""
        config = {
            'price_anomaly_threshold': 0.15,
            'volume_spike_threshold': 3.0,
            'volume_drought_threshold': 0.1,
            'max_data_gap_hours': 12,
            'staleness_threshold_hours': 1,
            'redis_channel': 'custom:quality:alerts'
        }
        
        monitor = DataQualityMonitor(config)
        
        assert monitor.price_anomaly_threshold == 0.15
        assert monitor.volume_spike_threshold == 3.0
        assert monitor.volume_drought_threshold == 0.1
        assert monitor.max_data_gap_hours == 12
        assert monitor.staleness_threshold_hours == 1
        assert monitor.redis_channel == 'custom:quality:alerts'
        
    def test_monitor_service_dependencies(self):
        """Test monitor has required service dependencies"""
        monitor = DataQualityMonitor()
        
        # Verify database connection
        assert monitor.db_connection is not None
        assert monitor.has_read_access is True
        
        # Verify Redis connection for alerts
        assert monitor.redis_client is not None
        assert monitor.redis_channel == 'tickstock:data_quality:alerts'
        
        # Verify service operates independently
        assert monitor.service_mode == 'standalone'
        assert monitor.service_role == 'producer'


class TestPriceAnomalyDetection:
    """Test price anomaly detection for >20% single-day moves"""
    
    @pytest.fixture
    def mock_price_data(self):
        """Mock historical price data for anomaly testing"""
        return [
            {'date': '2025-08-25', 'close': 100.00},
            {'date': '2025-08-26', 'close': 102.00},  # 2% normal move
            {'date': '2025-08-27', 'close': 125.00},  # 22.5% spike - anomaly
            {'date': '2025-08-28', 'close': 95.00},   # 24% drop - anomaly
            {'date': '2025-08-29', 'close': 97.00},   # 2.1% recovery - normal
        ]
    
    def test_detect_price_spikes(self, mock_price_data):
        """Test detection of significant price increases"""
        monitor = DataQualityMonitor()
        
        anomalies = monitor.detect_price_anomalies("TESTSPIKE", mock_price_data)
        
        # Should detect the 22.5% spike
        spikes = [a for a in anomalies if a['anomaly_type'] == 'price_spike']
        assert len(spikes) == 1
        
        spike = spikes[0]
        assert spike['symbol'] == 'TESTSPIKE'
        assert spike['date'] == '2025-08-27'
        assert abs(spike['price_change'] - 0.225) < 0.001  # 22.5% change
        assert spike['severity'] == 'high'
        assert spike['trigger_price'] == 125.00
        
    def test_detect_price_drops(self, mock_price_data):
        """Test detection of significant price decreases"""
        monitor = DataQualityMonitor()
        
        anomalies = monitor.detect_price_anomalies("TESTDROP", mock_price_data)
        
        # Should detect the 24% drop
        drops = [a for a in anomalies if a['anomaly_type'] == 'price_drop']
        assert len(drops) == 1
        
        drop = drops[0]
        assert drop['symbol'] == 'TESTDROP'
        assert drop['date'] == '2025-08-28'
        assert abs(drop['price_change'] + 0.24) < 0.001  # -24% change
        assert drop['severity'] == 'high'
        assert drop['trigger_price'] == 95.00
        
    def test_price_anomaly_threshold_filtering(self):
        """Test price changes below threshold are not flagged"""
        monitor = DataQualityMonitor()
        
        normal_data = [
            {'date': '2025-08-25', 'close': 100.00},
            {'date': '2025-08-26', 'close': 105.00},  # 5% move - normal
            {'date': '2025-08-27', 'close': 110.00},  # 4.8% move - normal
            {'date': '2025-08-28', 'close': 108.00},  # -1.8% move - normal
        ]
        
        anomalies = monitor.detect_price_anomalies("NORMAL", normal_data)
        
        # Should not detect any anomalies
        assert len(anomalies) == 0
        
    def test_price_anomaly_severity_classification(self):
        """Test price anomaly severity classification"""
        monitor = DataQualityMonitor()
        
        test_data = [
            {'date': '2025-08-25', 'close': 100.00},
            {'date': '2025-08-26', 'close': 122.00},  # 22% - high severity
            {'date': '2025-08-27', 'close': 135.00},  # 10.7% - medium severity
            {'date': '2025-08-28', 'close': 155.00},  # 14.8% - medium severity
            {'date': '2025-08-29', 'close': 200.00},  # 29% - critical severity
        ]
        
        anomalies = monitor.detect_price_anomalies("SEVERITY", test_data)
        
        # Verify severity levels
        critical = [a for a in anomalies if a['severity'] == 'critical']
        high = [a for a in anomalies if a['severity'] == 'high']
        
        assert len(critical) >= 1  # 29% move should be critical
        assert len(high) >= 1      # 22% move should be high
        
    @pytest.mark.performance
    def test_price_anomaly_detection_performance(self):
        """Test price anomaly detection performance for large datasets"""
        monitor = DataQualityMonitor()
        
        # Generate 1000 days of price data
        large_dataset = []
        base_price = 100.0
        
        for i in range(1000):
            # Mostly normal moves with occasional anomalies
            if i % 100 == 0:
                change = 0.25 if i % 200 == 0 else -0.22  # Inject anomalies
            else:
                change = np.random.normal(0, 0.02)  # Normal 2% std dev
                
            base_price *= (1 + change)
            large_dataset.append({
                'date': f'2023-{(i%365)+1:03d}',
                'close': round(base_price, 2)
            })
            
        start_time = time.perf_counter()
        anomalies = monitor.detect_price_anomalies("PERFORMANCE", large_dataset)
        elapsed_time = time.perf_counter() - start_time
        
        # Should process 1000 days in <1 second
        assert elapsed_time < 1.0
        assert len(anomalies) >= 8  # Should find injected anomalies
        
    def test_price_data_validation(self):
        """Test price data validation before anomaly detection"""
        monitor = DataQualityMonitor()
        
        # Test invalid data
        invalid_data = [
            {'date': '2025-08-25'},  # Missing close price
            {'date': '2025-08-26', 'close': None},  # Null close price
            {'date': '2025-08-27', 'close': -10.00},  # Negative price
            {'date': '2025-08-28', 'close': 'invalid'},  # Non-numeric price
        ]
        
        with pytest.raises(PriceAnomalyError) as exc_info:
            monitor.detect_price_anomalies("INVALID", invalid_data)
            
        assert "Invalid price data" in str(exc_info.value)
        
        # Test insufficient data
        insufficient_data = [{'date': '2025-08-25', 'close': 100.00}]
        
        anomalies = monitor.detect_price_anomalies("INSUFFICIENT", insufficient_data)
        assert len(anomalies) == 0  # Can't detect anomalies with one data point


class TestVolumeAnomalyDetection:
    """Test volume spike and drought detection with 5x thresholds"""
    
    @pytest.fixture
    def mock_volume_data(self):
        """Mock volume data with spikes and droughts"""
        # 30 days of volume data with average around 1M shares
        base_volume = 1000000
        data = []
        
        for i in range(30):
            if i == 10:
                volume = base_volume * 6  # 6x spike
            elif i == 20:
                volume = base_volume * 0.15  # 15% drought
            else:
                volume = base_volume + np.random.randint(-200000, 200000)
                
            data.append({
                'date': f'2025-08-{i+1:02d}',
                'volume': volume
            })
            
        return data
    
    def test_detect_volume_spikes(self, mock_volume_data):
        """Test detection of volume spikes >5x average"""
        monitor = DataQualityMonitor()
        
        anomalies = monitor.detect_volume_anomalies("VOLSPIKE", mock_volume_data)
        
        # Should detect the 6x volume spike
        spikes = [a for a in anomalies if a['anomaly_type'] == 'volume_spike']
        assert len(spikes) == 1
        
        spike = spikes[0]
        assert spike['symbol'] == 'VOLSPIKE'
        assert spike['date'] == '2025-08-11'  # Day 10 (0-indexed)
        assert spike['volume_multiplier'] >= 5.0
        assert spike['severity'] == 'high'
        
    def test_detect_volume_droughts(self, mock_volume_data):
        """Test detection of volume droughts <20% average"""
        monitor = DataQualityMonitor()
        
        anomalies = monitor.detect_volume_anomalies("VOLDROUGHT", mock_volume_data)
        
        # Should detect the 15% volume drought
        droughts = [a for a in anomalies if a['anomaly_type'] == 'volume_drought']
        assert len(droughts) == 1
        
        drought = droughts[0]
        assert drought['symbol'] == 'VOLDROUGHT'
        assert drought['date'] == '2025-08-21'  # Day 20
        assert drought['volume_ratio'] <= 0.20
        assert drought['severity'] in ['medium', 'high']
        
    def test_volume_baseline_calculation(self):
        """Test volume baseline calculation for anomaly detection"""
        monitor = DataQualityMonitor()
        
        # Test with known volume pattern
        consistent_data = [
            {'date': f'2025-08-{i+1:02d}', 'volume': 1000000 + i*10000}
            for i in range(30)
        ]
        
        baseline = monitor._calculate_volume_baseline(consistent_data)
        
        # Should calculate reasonable baseline (~1.15M average)
        assert 1100000 < baseline < 1200000
        
    def test_volume_anomaly_severity_levels(self):
        """Test volume anomaly severity classification"""
        monitor = DataQualityMonitor()
        
        test_data = []
        base_volume = 1000000
        
        # Add 30 days with varying anomaly severities
        for i in range(30):
            if i == 5:
                volume = base_volume * 8    # 8x - critical spike
            elif i == 10:
                volume = base_volume * 6    # 6x - high spike
            elif i == 15:
                volume = base_volume * 0.05 # 5% - critical drought
            elif i == 20:
                volume = base_volume * 0.15 # 15% - high drought
            else:
                volume = base_volume
                
            test_data.append({
                'date': f'2025-08-{i+1:02d}',
                'volume': volume
            })
            
        anomalies = monitor.detect_volume_anomalies("SEVERITY", test_data)
        
        # Verify severity classifications
        critical = [a for a in anomalies if a['severity'] == 'critical']
        high = [a for a in anomalies if a['severity'] == 'high']
        
        assert len(critical) >= 1  # Should detect critical anomalies
        assert len(high) >= 2      # Should detect high severity anomalies
        
    @pytest.mark.performance
    def test_volume_anomaly_performance(self):
        """Test volume anomaly detection performance"""
        monitor = DataQualityMonitor()
        
        # Generate large volume dataset
        large_volume_data = []
        base_volume = 1000000
        
        for i in range(365):  # Full year of data
            # Add anomalies every 50 days
            if i % 50 == 0:
                volume = base_volume * (7 if i % 100 == 0 else 0.1)
            else:
                volume = base_volume + np.random.randint(-300000, 300000)
                
            large_volume_data.append({
                'date': f'2024-{i+1:03d}',
                'volume': volume
            })
            
        start_time = time.perf_counter()
        anomalies = monitor.detect_volume_anomalies("PERF365", large_volume_data)
        elapsed_time = time.perf_counter() - start_time
        
        # Should process full year in <2 seconds
        assert elapsed_time < 2.0
        assert len(anomalies) >= 6  # Should detect injected anomalies
        
    def test_volume_data_validation(self):
        """Test volume data validation and error handling"""
        monitor = DataQualityMonitor()
        
        # Test invalid volume data
        invalid_data = [
            {'date': '2025-08-25', 'volume': -1000},  # Negative volume
            {'date': '2025-08-26'},  # Missing volume
            {'date': '2025-08-27', 'volume': None},   # Null volume
        ]
        
        with pytest.raises(VolumeAnomalyError) as exc_info:
            monitor.detect_volume_anomalies("INVALID", invalid_data)
            
        assert "Invalid volume data" in str(exc_info.value)
        
        # Test insufficient data for baseline
        insufficient_data = [
            {'date': '2025-08-25', 'volume': 1000000}
        ] * 5  # Less than minimum required days
        
        with pytest.raises(VolumeAnomalyError) as exc_info:
            monitor.detect_volume_anomalies("INSUFFICIENT", insufficient_data)
            
        assert "Insufficient data for baseline" in str(exc_info.value)


class TestDataGapIdentification:
    """Test data gap and staleness monitoring"""
    
    @pytest.fixture
    def mock_timestamp_data(self):
        """Mock timestamp data with gaps and staleness"""
        now = datetime.now()
        data = []
        
        # Recent data (1 hour ago)
        data.append({'symbol': 'FRESH', 'last_update': now - timedelta(hours=1)})
        
        # Stale data (3 hours ago)
        data.append({'symbol': 'STALE', 'last_update': now - timedelta(hours=3)})
        
        # Very old data (30 hours ago)
        data.append({'symbol': 'GAPPED', 'last_update': now - timedelta(hours=30)})
        
        # Current data
        data.append({'symbol': 'CURRENT', 'last_update': now - timedelta(minutes=15)})
        
        return data
    
    def test_detect_data_staleness(self, mock_timestamp_data):
        """Test detection of stale data beyond threshold"""
        monitor = DataQualityMonitor()
        
        stale_symbols = monitor.detect_data_staleness(mock_timestamp_data)
        
        # Should detect STALE (3h) but not FRESH (1h) or CURRENT (15m)
        stale_symbol_names = [s['symbol'] for s in stale_symbols]
        
        assert 'STALE' in stale_symbol_names
        assert 'FRESH' not in stale_symbol_names
        assert 'CURRENT' not in stale_symbol_names
        
        # Verify staleness details
        stale_entry = next(s for s in stale_symbols if s['symbol'] == 'STALE')
        assert stale_entry['staleness_hours'] >= 2.5
        assert stale_entry['severity'] in ['medium', 'high']
        
    def test_detect_data_gaps(self, mock_timestamp_data):
        """Test detection of data gaps beyond 24-hour threshold"""
        monitor = DataQualityMonitor()
        
        gapped_symbols = monitor.detect_data_gaps(mock_timestamp_data)
        
        # Should detect GAPPED (30h) but not others
        gapped_symbol_names = [s['symbol'] for s in gapped_symbols]
        
        assert 'GAPPED' in gapped_symbol_names
        assert 'STALE' not in gapped_symbol_names  # 3h is not a gap
        assert 'FRESH' not in gapped_symbol_names
        
        # Verify gap details
        gap_entry = next(s for s in gapped_symbols if s['symbol'] == 'GAPPED')
        assert gap_entry['gap_hours'] >= 24
        assert gap_entry['severity'] == 'high'
        
    def test_data_continuity_analysis(self):
        """Test analysis of data continuity patterns"""
        monitor = DataQualityMonitor()
        
        # Create test data with regular gaps
        now = datetime.now()
        continuity_data = []
        
        for i in range(10):
            if i in [3, 7]:  # Create gaps at positions 3 and 7
                timestamp = now - timedelta(hours=i*2 + 25)  # >24h gap
            else:
                timestamp = now - timedelta(hours=i*2)  # Regular 2h intervals
                
            continuity_data.append({
                'symbol': 'GAPPY',
                'timestamp': timestamp,
                'has_data': i not in [3, 7]
            })
            
        gaps = monitor.analyze_data_continuity('GAPPY', continuity_data)
        
        # Should detect the injected gaps
        assert len(gaps) == 2
        
        for gap in gaps:
            assert gap['symbol'] == 'GAPPY'
            assert gap['gap_hours'] >= 24
            
    def test_staleness_severity_classification(self):
        """Test staleness severity levels"""
        monitor = DataQualityMonitor()
        
        now = datetime.now()
        test_data = [
            {'symbol': 'MEDIUM1', 'last_update': now - timedelta(hours=4)},   # 4h - medium
            {'symbol': 'HIGH1', 'last_update': now - timedelta(hours=12)},    # 12h - high
            {'symbol': 'CRITICAL1', 'last_update': now - timedelta(hours=48)}, # 48h - critical
        ]
        
        stale_data = monitor.detect_data_staleness(test_data)
        
        # Verify severity assignments
        medium = [s for s in stale_data if s['severity'] == 'medium']
        high = [s for s in stale_data if s['severity'] == 'high']
        critical = [s for s in stale_data if s['severity'] == 'critical']
        
        assert len(medium) >= 1
        assert len(high) >= 1
        assert len(critical) >= 1
        
    @pytest.mark.performance
    def test_gap_detection_performance(self):
        """Test gap detection performance for large symbol sets"""
        monitor = DataQualityMonitor()
        
        # Generate test data for 5000 symbols
        now = datetime.now()
        large_dataset = []
        
        for i in range(5000):
            # Create various staleness patterns
            if i % 100 == 0:
                last_update = now - timedelta(hours=30)  # Gap
            elif i % 50 == 0:
                last_update = now - timedelta(hours=5)   # Stale
            else:
                last_update = now - timedelta(minutes=30) # Fresh
                
            large_dataset.append({
                'symbol': f'SYM{i:04d}',
                'last_update': last_update
            })
            
        start_time = time.perf_counter()
        
        stale_symbols = monitor.detect_data_staleness(large_dataset)
        gapped_symbols = monitor.detect_data_gaps(large_dataset)
        
        elapsed_time = time.perf_counter() - start_time
        
        # Should process 5000 symbols in <5 seconds
        assert elapsed_time < 5.0
        assert len(stale_symbols) >= 50   # ~100 stale symbols expected
        assert len(gapped_symbols) >= 40  # ~50 gapped symbols expected


class TestRedisQualityAlerting:
    """Test Redis pub-sub quality alert system"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing"""
        mock_client = Mock()
        mock_client.publish = Mock(return_value=1)
        mock_client.ping = Mock(return_value=True)
        return mock_client
    
    def test_publish_price_anomaly_alert(self, mock_redis_client):
        """Test publishing price anomaly alerts to Redis"""
        monitor = DataQualityMonitor()
        monitor.redis_client = mock_redis_client
        
        anomaly_data = {
            'symbol': 'AAPL',
            'anomaly_type': 'price_spike',
            'price_change': 0.25,
            'trigger_price': 175.00,
            'severity': 'high',
            'date': '2025-09-01'
        }
        
        result = monitor.publish_quality_alert(anomaly_data)
        
        assert result is True
        mock_redis_client.publish.assert_called_once()
        
        # Verify alert message structure
        call_args = mock_redis_client.publish.call_args
        assert call_args[0][0] == 'tickstock:data_quality:alerts'
        
        message = json.loads(call_args[0][1])
        assert message['alert_type'] == 'price_anomaly'
        assert message['symbol'] == 'AAPL'
        assert message['severity'] == 'high'
        assert message['anomaly_type'] == 'price_spike'
        assert 'timestamp' in message
        assert 'alert_id' in message
        
    def test_publish_volume_anomaly_alert(self, mock_redis_client):
        """Test publishing volume anomaly alerts"""
        monitor = DataQualityMonitor()
        monitor.redis_client = mock_redis_client
        
        volume_anomaly = {
            'symbol': 'TSLA',
            'anomaly_type': 'volume_spike',
            'volume_multiplier': 7.5,
            'baseline_volume': 50000000,
            'actual_volume': 375000000,
            'severity': 'critical'
        }
        
        result = monitor.publish_quality_alert(volume_anomaly)
        
        assert result is True
        
        # Verify volume alert structure
        call_args = mock_redis_client.publish.call_args
        message = json.loads(call_args[0][1])
        
        assert message['alert_type'] == 'volume_anomaly'
        assert message['symbol'] == 'TSLA'
        assert message['severity'] == 'critical'
        assert message['volume_multiplier'] == 7.5
        
    def test_publish_data_gap_alert(self, mock_redis_client):
        """Test publishing data gap alerts"""
        monitor = DataQualityMonitor()
        monitor.redis_client = mock_redis_client
        
        gap_alert = {
            'symbol': 'NVDA',
            'alert_type': 'data_gap',
            'gap_hours': 26,
            'last_update': '2025-08-31T10:00:00Z',
            'severity': 'high'
        }
        
        result = monitor.publish_quality_alert(gap_alert)
        
        assert result is True
        
        # Verify gap alert structure
        call_args = mock_redis_client.publish.call_args
        message = json.loads(call_args[0][1])
        
        assert message['alert_type'] == 'data_gap'
        assert message['symbol'] == 'NVDA'
        assert message['gap_hours'] == 26
        assert message['severity'] == 'high'
        
    def test_batch_alert_publishing(self, mock_redis_client):
        """Test batch publishing of multiple quality alerts"""
        monitor = DataQualityMonitor()
        monitor.redis_client = mock_redis_client
        
        alerts = [
            {'symbol': 'AAPL', 'anomaly_type': 'price_spike', 'severity': 'high'},
            {'symbol': 'GOOGL', 'anomaly_type': 'volume_drought', 'severity': 'medium'},
            {'symbol': 'MSFT', 'alert_type': 'data_gap', 'severity': 'high'}
        ]
        
        result = monitor.publish_batch_alerts(alerts)
        
        assert result is True
        assert mock_redis_client.publish.call_count == 3
        
    def test_alert_message_formatting(self):
        """Test quality alert message formatting"""
        monitor = DataQualityMonitor()
        
        raw_anomaly = {
            'symbol': 'TEST',
            'anomaly_type': 'price_spike',
            'price_change': 0.22,
            'severity': 'high'
        }
        
        formatted_alert = monitor._format_quality_alert(raw_anomaly)
        
        # Verify required fields
        required_fields = [
            'alert_id', 'timestamp', 'alert_type', 'symbol',
            'severity', 'anomaly_type', 'processing_priority'
        ]
        
        for field in required_fields:
            assert field in formatted_alert
            
        # Verify field values
        assert formatted_alert['alert_type'] == 'price_anomaly'
        assert formatted_alert['symbol'] == 'TEST'
        assert formatted_alert['severity'] == 'high'
        assert formatted_alert['processing_priority'] in ['high', 'critical']
        
    @pytest.mark.performance
    def test_alert_publishing_performance(self, mock_redis_client):
        """Test alert publishing meets <100ms delivery requirement"""
        monitor = DataQualityMonitor()
        monitor.redis_client = mock_redis_client
        
        test_alert = {
            'symbol': 'PERF',
            'anomaly_type': 'price_spike',
            'severity': 'high'
        }
        
        # Test single alert performance
        start_time = time.perf_counter()
        result = monitor.publish_quality_alert(test_alert)
        elapsed_time = time.perf_counter() - start_time
        
        assert result is True
        assert elapsed_time < 0.1  # Less than 100ms
        
        # Test batch alert performance
        batch_alerts = [
            {'symbol': f'BATCH{i}', 'anomaly_type': 'volume_spike', 'severity': 'medium'}
            for i in range(100)
        ]
        
        start_time = time.perf_counter()
        result = monitor.publish_batch_alerts(batch_alerts)
        elapsed_time = time.perf_counter() - start_time
        
        assert result is True
        assert elapsed_time < 10.0  # 100 alerts in <10 seconds
        
    def test_redis_connection_failure_handling(self):
        """Test handling of Redis connection failures"""
        monitor = DataQualityMonitor()
        
        # Mock Redis connection failure
        mock_client = Mock()
        mock_client.publish = Mock(side_effect=redis.ConnectionError("Connection failed"))
        monitor.redis_client = mock_client
        
        alert_data = {'symbol': 'TEST', 'anomaly_type': 'price_spike'}
        
        # Should handle connection failure gracefully
        result = monitor.publish_quality_alert(alert_data)
        
        assert result is False  # Alert failed but didn't crash service
        
        # Verify error was logged
        assert hasattr(monitor, 'connection_errors')
        assert monitor.connection_errors > 0


class TestDataQualityServiceIntegration:
    """Integration tests for complete data quality monitoring workflow"""
    
    @pytest.mark.integration
    def test_end_to_end_quality_monitoring(self):
        """Test complete quality monitoring workflow"""
        monitor = DataQualityMonitor()
        
        with patch.object(monitor, 'get_market_data') as mock_data, \
             patch.object(monitor, 'publish_quality_alert') as mock_alert:
            
            # Mock market data with various quality issues
            mock_data.return_value = {
                'AAPL': {
                    'price_data': [
                        {'date': '2025-08-30', 'close': 100.0},
                        {'date': '2025-08-31', 'close': 125.0}  # 25% spike
                    ],
                    'volume_data': [
                        {'date': '2025-08-30', 'volume': 1000000},
                        {'date': '2025-08-31', 'volume': 7000000}  # 7x spike
                    ],
                    'last_update': datetime.now() - timedelta(hours=3)  # Stale
                }
            }
            
            mock_alert.return_value = True
            
            # Run complete quality scan
            results = monitor.run_quality_scan(['AAPL'])
            
            # Verify comprehensive results
            assert results['symbols_analyzed'] == 1
            assert results['price_anomalies'] >= 1
            assert results['volume_anomalies'] >= 1
            assert results['data_quality_issues'] >= 1
            assert results['alerts_published'] >= 3
            
    @pytest.mark.integration
    def test_4000_symbol_quality_analysis(self):
        """Test quality monitoring capacity for 4,000+ symbols"""
        monitor = DataQualityMonitor()
        
        # Mock large symbol set
        symbol_list = [f'SYM{i:04d}' for i in range(4000)]
        
        with patch.object(monitor, 'analyze_symbol_quality') as mock_analyze:
            mock_analyze.return_value = {
                'price_anomalies': 0,
                'volume_anomalies': 0,
                'data_issues': 0
            }
            
            start_time = time.perf_counter()
            results = monitor.run_quality_scan(symbol_list)
            elapsed_time = time.perf_counter() - start_time
            
            # Should handle 4,000 symbols efficiently
            assert elapsed_time < 600  # Within 10 minutes
            assert results['symbols_analyzed'] == 4000
            assert mock_analyze.call_count == 4000
            
    @pytest.mark.integration
    def test_quality_alert_false_positive_rates(self):
        """Test false positive rates for anomaly detection"""
        monitor = DataQualityMonitor()
        
        # Generate normal market data (should have minimal anomalies)
        normal_symbols = []
        for i in range(100):
            price_data = []
            volume_data = []
            
            base_price = 100.0
            base_volume = 1000000
            
            for j in range(30):
                # Generate normal market movements
                price_change = np.random.normal(0, 0.015)  # 1.5% std dev
                volume_change = np.random.normal(0, 0.3)   # 30% volume variation
                
                base_price *= (1 + price_change)
                volume = max(100000, int(base_volume * (1 + volume_change)))
                
                price_data.append({'date': f'2025-08-{j+1:02d}', 'close': base_price})
                volume_data.append({'date': f'2025-08-{j+1:02d}', 'volume': volume})
                
            normal_symbols.append({
                'symbol': f'NORMAL{i:03d}',
                'price_data': price_data,
                'volume_data': volume_data
            })
            
        # Analyze false positive rate
        false_positives = 0
        total_analyzed = 0
        
        for symbol_data in normal_symbols:
            price_anomalies = monitor.detect_price_anomalies(
                symbol_data['symbol'], 
                symbol_data['price_data']
            )
            volume_anomalies = monitor.detect_volume_anomalies(
                symbol_data['symbol'],
                symbol_data['volume_data']
            )
            
            if len(price_anomalies) + len(volume_anomalies) > 0:
                false_positives += 1
            total_analyzed += 1
            
        false_positive_rate = false_positives / total_analyzed
        
        # False positive rate should be <5%
        assert false_positive_rate < 0.05
        
    @pytest.mark.integration 
    @pytest.mark.slow
    def test_continuous_quality_monitoring(self):
        """Test continuous quality monitoring service operation"""
        monitor = DataQualityMonitor()
        
        # Test service can run continuously
        assert hasattr(monitor, 'start_monitoring')
        assert hasattr(monitor, 'stop_monitoring')
        assert hasattr(monitor, 'is_running')
        
        # Test monitoring cycle
        with patch.object(monitor, 'run_quality_scan') as mock_scan:
            mock_scan.return_value = {'symbols_analyzed': 1000, 'alerts_published': 5}
            
            # Start monitoring service
            monitor.start_monitoring()
            
            # Allow one monitoring cycle
            time.sleep(2.0)
            
            # Stop monitoring
            monitor.stop_monitoring()
            
            # Verify monitoring executed
            assert mock_scan.call_count >= 1
            assert not monitor.is_running()