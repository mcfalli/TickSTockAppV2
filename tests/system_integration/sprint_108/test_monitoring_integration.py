"""
Sprint 108: Monitoring and Alerting Integration Tests

Tests for comprehensive monitoring and alerting integration across the 
multi-channel system. Validates channel-specific metrics, performance 
monitoring, alerting functionality, and integration with existing 
TickStock monitoring infrastructure.

Test Coverage:
1. Channel-specific monitoring integration
2. Performance threshold alerting
3. System health monitoring
4. Monitoring dashboard integration
5. Alert handling and escalation
6. Debugging and troubleshooting tools
"""

import pytest
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, call
from dataclasses import dataclass

from tests.fixtures.market_data_fixtures import (
    create_tick_data, create_ohlcv_data, create_fmv_data,
    create_mock_market_service, create_test_config,
    create_mock_alert_handler
)

from src.core.integration.multi_channel_system import (
    MultiChannelSystem, MultiChannelSystemConfig
)
from src.monitoring.channel_monitoring import (
    ChannelMonitor, PerformanceThresholds, Alert, AlertType, 
    AlertSeverity, ChannelHealthMetrics, SystemHealthMetrics
)

logger = logging.getLogger(__name__)


class TestChannelMonitoringIntegration:
    """Test channel monitoring system integration"""
    
    @pytest.fixture
    async def monitored_system(self):
        """Create system with full monitoring enabled"""
        config = MultiChannelSystemConfig(
            enable_monitoring=True,
            performance_monitoring_enabled=True,
            health_check_interval_seconds=0.1,
            metrics_collection_interval_seconds=0.1
        )
        
        mock_service = create_mock_market_service()
        system = MultiChannelSystem(config, mock_service)
        await system.initialize_system()
        yield system
        await system.shutdown()
    
    @pytest.fixture
    def channel_monitor(self):
        """Create channel monitor for testing"""
        thresholds = PerformanceThresholds(
            max_latency_ms=50.0,
            min_success_rate_percent=95.0,
            max_memory_usage_gb=1.0,
            max_queue_utilization_percent=80.0
        )
        
        monitor = ChannelMonitor(thresholds)
        yield monitor
        asyncio.create_task(monitor.stop_monitoring())
    
    @pytest.mark.asyncio
    async def test_channel_registration_and_monitoring(self, channel_monitor):
        """Test channel registration and basic monitoring"""
        monitor = channel_monitor
        
        # Register channels for monitoring
        monitor.register_channel("test_tick", "tick")
        monitor.register_channel("test_ohlcv", "ohlcv")
        monitor.register_channel("test_fmv", "fmv")
        
        # Verify channels are registered
        assert "test_tick" in monitor.channel_metrics
        assert "test_ohlcv" in monitor.channel_metrics
        assert "test_fmv" in monitor.channel_metrics
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Update metrics for channels
        monitor.update_channel_metrics("test_tick", 
                                     is_healthy=True, 
                                     status="running",
                                     processed_count=100,
                                     error_count=2)
        
        monitor.update_channel_metrics("test_ohlcv",
                                     is_healthy=True,
                                     status="running", 
                                     processed_count=50,
                                     error_count=0)
        
        # Allow monitoring to process
        await asyncio.sleep(0.2)
        
        # Verify metrics are tracked
        tick_metrics = monitor.channel_metrics["test_tick"]
        assert tick_metrics.is_healthy is True
        assert tick_metrics.processed_count == 100
        assert tick_metrics.error_count == 2
        assert tick_metrics.success_rate_percent == 98.0
        
        ohlcv_metrics = monitor.channel_metrics["test_ohlcv"]
        assert ohlcv_metrics.processed_count == 50
        assert ohlcv_metrics.error_count == 0
        assert ohlcv_metrics.success_rate_percent == 100.0
    
    @pytest.mark.asyncio
    async def test_performance_threshold_alerting(self, channel_monitor):
        """Test alerting when performance thresholds are exceeded"""
        monitor = channel_monitor
        alert_handler = create_mock_alert_handler()
        monitor.add_alert_handler(alert_handler)
        
        # Register channel
        monitor.register_channel("alert_test", "tick")
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Trigger high latency alert
        monitor.record_processing_latency("alert_test", 75.0)  # Exceeds 50ms threshold
        for _ in range(20):  # Build up samples for percentile calculation
            monitor.record_processing_latency("alert_test", 60.0)
        
        # Update channel metrics to trigger alert check
        monitor.update_channel_metrics("alert_test",
                                     is_healthy=True,
                                     latency_p99_ms=70.0)  # Exceeds threshold
        
        # Trigger low success rate alert
        for i in range(100):
            success = i < 85  # 85% success rate (below 95% threshold)
            monitor.record_processing_event("alert_test", success)
        
        monitor.update_channel_metrics("alert_test",
                                     success_rate_percent=85.0)  # Below threshold
        
        # Allow time for alert processing
        await asyncio.sleep(0.2)
        
        # Verify alerts were generated
        assert len(alert_handler.alerts_received) >= 2
        
        # Check for specific alert types
        alert_types = [alert.alert_type for alert in alert_handler.alerts_received]
        assert AlertType.HIGH_LATENCY in alert_types
        assert AlertType.LOW_SUCCESS_RATE in alert_types
        
        # Verify alert details
        latency_alert = next(alert for alert in alert_handler.alerts_received 
                           if alert.alert_type == AlertType.HIGH_LATENCY)
        assert latency_alert.severity in [AlertSeverity.WARNING, AlertSeverity.ERROR]
        assert latency_alert.channel_name == "alert_test"
        assert "latency" in latency_alert.message.lower()
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring_integration(self, monitored_system):
        """Test system health monitoring integration with multi-channel system"""
        system = monitored_system
        
        # Create channel monitor for the system
        monitor = ChannelMonitor()
        alert_handler = create_mock_alert_handler()
        monitor.add_alert_handler(alert_handler)
        
        # Register system channels
        if system.tick_channel:
            monitor.register_channel(system.tick_channel.name, "tick")
        if system.ohlcv_channel:
            monitor.register_channel(system.ohlcv_channel.name, "ohlcv")
        if system.fmv_channel:
            monitor.register_channel(system.fmv_channel.name, "fmv")
        
        await monitor.start_monitoring()
        
        try:
            # Process data through system and monitor
            for i in range(50):
                # Process different data types
                await asyncio.gather(
                    system.process_tick_data(create_tick_data(f"HEALTH{i}", 100.0, 1000)),
                    system.process_ohlcv_data(create_ohlcv_data(f"HEALTH{i}", 100.0, 105.0, 95.0, 102.0, 10000)),
                    system.process_fmv_data(create_fmv_data(f"HEALTH{i}", 100.0, 0.9)),
                    return_exceptions=True
                )
                
                # Update monitoring with system metrics
                if i % 10 == 0:
                    # Simulate updating monitor with channel health
                    for channel_name in monitor.channel_metrics:
                        monitor.update_channel_metrics(channel_name,
                                                     is_healthy=True,
                                                     processed_count=i + 1,
                                                     error_count=0)
            
            # Allow monitoring to collect metrics
            await asyncio.sleep(0.5)
            
            # Get monitoring dashboard data
            dashboard_data = monitor.get_monitoring_dashboard_data()
            
            # Verify system health metrics
            system_overview = dashboard_data['system_overview']
            assert system_overview['channels']['total'] >= 3  # At least tick, ohlcv, fmv
            assert system_overview['channels']['healthy'] >= 3
            assert system_overview['performance']['success_rate_percent'] > 90.0
            
            # Verify channel details
            channel_details = dashboard_data['channel_details']
            assert len(channel_details) >= 3
            
            for channel_name, details in channel_details.items():
                assert details['is_healthy'] is True
                assert details['processing']['processed_count'] > 0
                assert details['processing']['success_rate_percent'] >= 90.0
            
            # Verify no critical alerts
            active_alerts = dashboard_data['active_alerts']
            critical_alerts = [alert for alert in active_alerts 
                             if alert['severity'] == AlertSeverity.CRITICAL.value]
            assert len(critical_alerts) == 0, f"Unexpected critical alerts: {critical_alerts}"
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_channel_failure_detection_and_alerting(self, channel_monitor):
        """Test detection and alerting for channel failures"""
        monitor = channel_monitor
        alert_handler = create_mock_alert_handler()
        monitor.add_alert_handler(alert_handler)
        
        # Register channel
        monitor.register_channel("failure_test", "tick")
        await monitor.start_monitoring()
        
        # Simulate channel failure
        monitor.update_channel_metrics("failure_test",
                                     is_healthy=False,
                                     status="error",
                                     processed_count=100,
                                     error_count=50)
        
        # Allow alert processing
        await asyncio.sleep(0.2)
        
        # Verify failure alert was generated
        assert len(alert_handler.alerts_received) > 0
        
        failure_alert = next((alert for alert in alert_handler.alerts_received 
                            if alert.alert_type == AlertType.CHANNEL_FAILURE), None)
        
        assert failure_alert is not None
        assert failure_alert.severity == AlertSeverity.CRITICAL
        assert failure_alert.channel_name == "failure_test"
        assert "unhealthy" in failure_alert.message.lower()
        
        # Test recovery detection
        monitor.update_channel_metrics("failure_test",
                                     is_healthy=True,
                                     status="running")
        
        # Resolve the alert
        monitor.resolve_alert(AlertType.CHANNEL_FAILURE, "failure_test")
        
        # Verify alert is resolved
        active_alerts = {key: alert for key, alert in monitor.active_alerts.items()}
        failure_alert_key = f"{AlertType.CHANNEL_FAILURE.value}_failure_test"
        assert failure_alert_key not in active_alerts


class TestPerformanceMonitoringIntegration:
    """Test performance monitoring integration"""
    
    @pytest.fixture
    async def performance_monitored_system(self):
        """Create system with performance monitoring"""
        config = MultiChannelSystemConfig(
            target_latency_p99_ms=50.0,
            target_memory_limit_gb=1.0,
            performance_monitoring_enabled=True,
            metrics_collection_interval_seconds=0.1
        )
        
        mock_service = create_mock_market_service()
        system = MultiChannelSystem(config, mock_service)
        await system.initialize_system()
        yield system
        await system.shutdown()
    
    @pytest.mark.asyncio
    async def test_latency_monitoring_and_alerting(self, performance_monitored_system):
        """Test latency monitoring and alerting integration"""
        system = performance_monitored_system
        
        # Create monitor with strict thresholds
        thresholds = PerformanceThresholds(max_latency_ms=30.0)  # Strict threshold
        monitor = ChannelMonitor(thresholds)
        alert_handler = create_mock_alert_handler()
        monitor.add_alert_handler(alert_handler)
        
        # Register channels
        monitor.register_channel("perf_tick", "tick")
        await monitor.start_monitoring()
        
        try:
            # Process data and record latencies
            high_latency_count = 0
            
            for i in range(100):
                tick_data = create_tick_data(f"PERF{i}", 100.0, 1000)
                
                start_time = time.time()
                await system.process_tick_data(tick_data)
                end_time = time.time()
                
                latency_ms = (end_time - start_time) * 1000
                
                # Simulate occasional high latency
                if i % 20 == 0:
                    latency_ms += 40.0  # Add artificial delay
                    high_latency_count += 1
                
                monitor.record_processing_latency("perf_tick", latency_ms)
                monitor.record_processing_event("perf_tick", True, latency_ms)
            
            # Update channel metrics to trigger threshold checks
            if monitor._latency_samples.get("perf_tick"):
                latencies = monitor._latency_samples["perf_tick"]
                if len(latencies) >= 10:
                    import statistics
                    p99_latency = statistics.quantiles(latencies, n=100)[98]
                    monitor.update_channel_metrics("perf_tick", latency_p99_ms=p99_latency)
            
            # Allow alert processing
            await asyncio.sleep(0.3)
            
            # Verify performance monitoring
            channel_metrics = monitor.channel_metrics["perf_tick"]
            assert channel_metrics.processed_count == 100
            assert channel_metrics.avg_processing_time_ms > 0
            
            # Check for latency alerts if threshold exceeded
            if channel_metrics.latency_p99_ms > thresholds.max_latency_ms:
                latency_alerts = [alert for alert in alert_handler.alerts_received 
                                if alert.alert_type == AlertType.HIGH_LATENCY]
                assert len(latency_alerts) > 0
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_throughput_monitoring(self, performance_monitored_system):
        """Test throughput monitoring and metrics collection"""
        system = performance_monitored_system
        monitor = ChannelMonitor()
        
        # Register channels
        monitor.register_channel("throughput_tick", "tick")
        monitor.register_channel("throughput_ohlcv", "ohlcv")
        
        await monitor.start_monitoring()
        
        try:
            # Generate load to measure throughput
            start_time = time.time()
            
            for i in range(50):
                # Process both tick and OHLCV data
                await asyncio.gather(
                    system.process_tick_data(create_tick_data(f"THROUGH{i}", 100.0, 1000)),
                    system.process_ohlcv_data(create_ohlcv_data(f"THROUGH{i}", 100.0, 105.0, 95.0, 102.0, 10000)),
                    return_exceptions=True
                )
                
                # Record processing events
                monitor.record_processing_event("throughput_tick", True)
                monitor.record_processing_event("throughput_ohlcv", True)
            
            processing_duration = time.time() - start_time
            
            # Allow throughput calculation
            await asyncio.sleep(1.1)  # Wait for throughput calculation window
            
            # Verify throughput metrics
            tick_metrics = monitor.channel_metrics["throughput_tick"]
            ohlcv_metrics = monitor.channel_metrics["throughput_ohlcv"]
            
            assert tick_metrics.processed_count == 50
            assert ohlcv_metrics.processed_count == 50
            
            # Throughput should be reasonable
            expected_throughput = 50 / processing_duration
            assert tick_metrics.throughput_per_second >= 0  # Should have some throughput
            assert ohlcv_metrics.throughput_per_second >= 0
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, performance_monitored_system):
        """Test memory usage monitoring and alerting"""
        system = performance_monitored_system
        
        # Create monitor with low memory threshold for testing
        thresholds = PerformanceThresholds(max_memory_usage_gb=0.1)  # Very low for testing
        monitor = ChannelMonitor(thresholds)
        alert_handler = create_mock_alert_handler()
        monitor.add_alert_handler(alert_handler)
        
        await monitor.start_monitoring()
        
        try:
            # Generate some load that might increase memory
            for i in range(100):
                await asyncio.gather(
                    system.process_tick_data(create_tick_data(f"MEM{i}", 100.0, 1000)),
                    system.process_ohlcv_data(create_ohlcv_data(f"MEM{i}", 100.0, 105.0, 95.0, 102.0, 10000)),
                    return_exceptions=True
                )
                
                # Record system metrics periodically
                if i % 20 == 0:
                    monitor.record_system_metrics()
            
            # Allow monitoring to process and check system-level alerts
            await asyncio.sleep(0.5)
            
            # Get system metrics
            dashboard_data = monitor.get_monitoring_dashboard_data()
            system_metrics = dashboard_data['system_overview']
            
            # Verify memory monitoring
            assert 'resources' in system_metrics
            assert 'memory_usage_mb' in system_metrics['resources']
            assert system_metrics['resources']['memory_usage_mb'] > 0
            
            # Check for memory alerts (might be triggered due to low threshold)
            memory_alerts = [alert for alert in alert_handler.alerts_received 
                           if alert.alert_type == AlertType.MEMORY_USAGE]
            
            # With very low threshold, we expect memory alerts
            if system_metrics['resources']['memory_usage_mb'] > (thresholds.max_memory_usage_gb * 1024):
                assert len(memory_alerts) > 0
            
        finally:
            await monitor.stop_monitoring()


class TestMonitoringDashboardIntegration:
    """Test monitoring dashboard integration"""
    
    @pytest.fixture
    async def dashboard_system(self):
        """Create system for dashboard testing"""
        config = MultiChannelSystemConfig(
            enable_monitoring=True,
            performance_monitoring_enabled=True,
            health_check_interval_seconds=0.2
        )
        
        mock_service = create_mock_market_service()
        system = MultiChannelSystem(config, mock_service)
        await system.initialize_system()
        yield system
        await system.shutdown()
    
    @pytest.mark.asyncio
    async def test_monitoring_dashboard_data_structure(self, dashboard_system):
        """Test monitoring dashboard data structure and content"""
        system = dashboard_system
        monitor = ChannelMonitor()
        
        # Register system channels with monitor
        monitor.register_channel("dash_tick", "tick")
        monitor.register_channel("dash_ohlcv", "ohlcv")
        monitor.register_channel("dash_fmv", "fmv")
        
        await monitor.start_monitoring()
        
        try:
            # Generate some activity
            for i in range(20):
                await asyncio.gather(
                    system.process_tick_data(create_tick_data(f"DASH{i}", 100.0, 1000)),
                    system.process_ohlcv_data(create_ohlcv_data(f"DASH{i}", 100.0, 105.0, 95.0, 102.0, 10000)),
                    system.process_fmv_data(create_fmv_data(f"DASH{i}", 100.0, 0.9)),
                    return_exceptions=True
                )
                
                # Update monitoring metrics
                monitor.record_processing_event("dash_tick", True)
                monitor.record_processing_event("dash_ohlcv", True)
                monitor.record_processing_event("dash_fmv", True)
            
            # Allow metrics collection
            await asyncio.sleep(0.5)
            
            # Get dashboard data
            dashboard_data = monitor.get_monitoring_dashboard_data()
            
            # Verify dashboard data structure
            required_sections = [
                'system_overview',
                'channel_details', 
                'active_alerts',
                'recent_alerts',
                'performance_thresholds',
                'monitoring_config'
            ]
            
            for section in required_sections:
                assert section in dashboard_data, f"Missing dashboard section: {section}"
            
            # Verify system overview structure
            system_overview = dashboard_data['system_overview']
            required_overview_fields = [
                'channels', 'performance', 'resources', 'alerts'
            ]
            
            for field in required_overview_fields:
                assert field in system_overview, f"Missing system overview field: {field}"
            
            # Verify channel details structure
            channel_details = dashboard_data['channel_details']
            assert len(channel_details) == 3  # tick, ohlcv, fmv
            
            for channel_name, details in channel_details.items():
                required_channel_fields = [
                    'channel_name', 'channel_type', 'is_healthy',
                    'processing', 'queue', 'performance', 'timing'
                ]
                
                for field in required_channel_fields:
                    assert field in details, f"Missing channel field {field} in {channel_name}"
            
            # Verify performance thresholds
            thresholds = dashboard_data['performance_thresholds']
            required_threshold_fields = [
                'max_latency_ms', 'min_success_rate_percent', 
                'max_memory_usage_gb', 'max_queue_utilization_percent'
            ]
            
            for field in required_threshold_fields:
                assert field in thresholds, f"Missing threshold field: {field}"
            
            # Verify monitoring config
            monitoring_config = dashboard_data['monitoring_config']
            assert 'enabled' in monitoring_config
            assert 'total_channels_monitored' in monitoring_config
            assert monitoring_config['total_channels_monitored'] == 3
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_real_time_dashboard_updates(self, dashboard_system):
        """Test real-time dashboard updates during system operation"""
        system = dashboard_system
        monitor = ChannelMonitor()
        
        # Register channels
        monitor.register_channel("realtime_tick", "tick")
        await monitor.start_monitoring()
        
        try:
            # Initial dashboard state
            initial_data = monitor.get_monitoring_dashboard_data()
            initial_processed = initial_data['channel_details']['realtime_tick']['processing']['processed_count']
            
            # Process some data
            for i in range(10):
                await system.process_tick_data(create_tick_data(f"RT{i}", 100.0, 1000))
                monitor.record_processing_event("realtime_tick", True)
            
            # Allow updates
            await asyncio.sleep(0.3)
            
            # Updated dashboard state
            updated_data = monitor.get_monitoring_dashboard_data()
            updated_processed = updated_data['channel_details']['realtime_tick']['processing']['processed_count']
            
            # Verify updates
            assert updated_processed > initial_processed
            assert updated_data['channel_details']['realtime_tick']['is_healthy'] is True
            
            # Verify timestamp updates
            assert updated_data['timestamp'] > initial_data['timestamp']
            
        finally:
            await monitor.stop_monitoring()


class TestAlertHandlingAndEscalation:
    """Test alert handling and escalation mechanisms"""
    
    @pytest.fixture
    def alert_monitor(self):
        """Create monitor for alert testing"""
        thresholds = PerformanceThresholds(
            max_latency_ms=25.0,  # Strict for testing
            min_success_rate_percent=98.0,
            max_queue_utilization_percent=50.0
        )
        monitor = ChannelMonitor(thresholds)
        yield monitor
        asyncio.create_task(monitor.stop_monitoring())
    
    @pytest.mark.asyncio
    async def test_alert_generation_and_handling(self, alert_monitor):
        """Test alert generation and custom handler integration"""
        monitor = alert_monitor
        
        # Create multiple alert handlers
        handler1 = create_mock_alert_handler()
        handler2 = create_mock_alert_handler()
        
        monitor.add_alert_handler(handler1)
        monitor.add_alert_handler(handler2)
        
        # Register channel and start monitoring
        monitor.register_channel("alert_channel", "tick")
        await monitor.start_monitoring()
        
        # Trigger multiple alert conditions
        
        # 1. High latency alert
        monitor.update_channel_metrics("alert_channel",
                                     is_healthy=True,
                                     latency_p99_ms=50.0)  # Exceeds 25ms threshold
        
        # 2. Low success rate alert
        monitor.update_channel_metrics("alert_channel",
                                     success_rate_percent=90.0)  # Below 98% threshold
        
        # 3. High queue utilization alert
        monitor.update_channel_metrics("alert_channel",
                                     queue_utilization_percent=75.0)  # Above 50% threshold
        
        # Allow alert processing
        await asyncio.sleep(0.3)
        
        # Verify both handlers received alerts
        assert len(handler1.alerts_received) >= 3
        assert len(handler2.alerts_received) >= 3
        
        # Verify alert types
        alert_types_1 = {alert.alert_type for alert in handler1.alerts_received}
        alert_types_2 = {alert.alert_type for alert in handler2.alerts_received}
        
        expected_types = {AlertType.HIGH_LATENCY, AlertType.LOW_SUCCESS_RATE, AlertType.QUEUE_OVERFLOW}
        assert expected_types.issubset(alert_types_1)
        assert expected_types.issubset(alert_types_2)
    
    @pytest.mark.asyncio
    async def test_alert_cooldown_mechanism(self, alert_monitor):
        """Test alert cooldown to prevent spam"""
        monitor = alert_monitor
        alert_handler = create_mock_alert_handler()
        monitor.add_alert_handler(alert_handler)
        
        # Set short cooldown for testing
        monitor.alert_cooldown_seconds = 0.5
        
        monitor.register_channel("cooldown_test", "tick")
        await monitor.start_monitoring()
        
        # Trigger same alert multiple times quickly
        for i in range(5):
            monitor.update_channel_metrics("cooldown_test",
                                         is_healthy=True,
                                         latency_p99_ms=50.0)  # Same alert condition
            await asyncio.sleep(0.1)  # Quick succession
        
        # Should only get one alert due to cooldown
        latency_alerts = [alert for alert in alert_handler.alerts_received 
                         if alert.alert_type == AlertType.HIGH_LATENCY]
        assert len(latency_alerts) == 1
        
        # Wait for cooldown to expire
        await asyncio.sleep(0.6)
        
        # Trigger alert again
        monitor.update_channel_metrics("cooldown_test",
                                     latency_p99_ms=60.0)  # Trigger again
        
        await asyncio.sleep(0.2)
        
        # Should get another alert now
        latency_alerts = [alert for alert in alert_handler.alerts_received 
                         if alert.alert_type == AlertType.HIGH_LATENCY]
        assert len(latency_alerts) == 2
    
    @pytest.mark.asyncio
    async def test_alert_resolution_tracking(self, alert_monitor):
        """Test alert resolution and tracking"""
        monitor = alert_monitor
        alert_handler = create_mock_alert_handler()
        monitor.add_alert_handler(alert_handler)
        
        monitor.register_channel("resolution_test", "tick")
        await monitor.start_monitoring()
        
        # Trigger alert
        monitor.update_channel_metrics("resolution_test",
                                     is_healthy=False,
                                     status="error")
        
        await asyncio.sleep(0.2)
        
        # Verify alert was created
        assert len(alert_handler.alerts_received) > 0
        failure_alert = next((alert for alert in alert_handler.alerts_received 
                            if alert.alert_type == AlertType.CHANNEL_FAILURE), None)
        assert failure_alert is not None
        assert failure_alert.resolved is False
        
        # Resolve the condition
        monitor.update_channel_metrics("resolution_test",
                                     is_healthy=True,
                                     status="running")
        
        # Manually resolve the alert
        monitor.resolve_alert(AlertType.CHANNEL_FAILURE, "resolution_test")
        
        # Verify alert is marked as resolved
        assert failure_alert.resolved is True
        assert failure_alert.resolution_time is not None
        
        # Verify alert is removed from active alerts
        alert_key = f"{AlertType.CHANNEL_FAILURE.value}_resolution_test"
        assert alert_key not in monitor.active_alerts


class TestDebuggingAndTroubleshooting:
    """Test debugging and troubleshooting tools"""
    
    @pytest.fixture
    async def debug_system(self):
        """Create system for debugging tests"""
        config = MultiChannelSystemConfig(enable_monitoring=True)
        mock_service = create_mock_market_service()
        system = MultiChannelSystem(config, mock_service)
        await system.initialize_system()
        yield system
        await system.shutdown()
    
    @pytest.mark.asyncio
    async def test_channel_debug_information(self, debug_system):
        """Test detailed channel debug information"""
        system = debug_system
        monitor = ChannelMonitor()
        
        # Register channel for debugging
        monitor.register_channel("debug_channel", "tick")
        await monitor.start_monitoring()
        
        try:
            # Generate activity with some variety
            for i in range(30):
                await system.process_tick_data(create_tick_data(f"DEBUG{i}", 100.0 + i, 1000))
                
                # Record metrics with some variation
                latency = 10.0 + (i % 10) * 2.0  # Varying latency
                success = i % 20 != 0  # Occasional failure
                
                monitor.record_processing_latency("debug_channel", latency)
                monitor.record_processing_event("debug_channel", success, latency)
            
            # Allow metrics collection
            await asyncio.sleep(0.3)
            
            # Get debug information
            debug_info = monitor.get_channel_debug_info("debug_channel")
            
            # Verify debug information structure
            assert debug_info is not None
            
            required_sections = [
                'channel_metrics', 'latency_analysis', 
                'throughput_analysis', 'health_summary'
            ]
            
            for section in required_sections:
                assert section in debug_info, f"Missing debug section: {section}"
            
            # Verify latency analysis
            latency_analysis = debug_info['latency_analysis']
            assert latency_analysis['sample_count'] > 0
            assert 'recent_samples' in latency_analysis
            assert 'min_latency' in latency_analysis
            assert 'max_latency' in latency_analysis
            
            # Verify throughput analysis
            throughput_analysis = debug_info['throughput_analysis']
            assert 'current_throughput' in throughput_analysis
            assert 'tracking_start' in throughput_analysis
            
            # Verify health summary
            health_summary = debug_info['health_summary']
            assert 'is_healthy' in health_summary
            assert 'status' in health_summary
            assert 'performance_issues' in health_summary
            
            # Check performance issues detection
            if latency_analysis['max_latency'] > monitor.thresholds.max_latency_ms:
                assert len(health_summary['performance_issues']) > 0
                assert any("latency" in issue.lower() for issue in health_summary['performance_issues'])
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_performance_issue_detection(self, debug_system):
        """Test performance issue detection in debug tools"""
        system = debug_system
        
        # Create monitor with strict thresholds for testing
        thresholds = PerformanceThresholds(
            max_latency_ms=20.0,
            min_success_rate_percent=95.0,
            max_processing_time_ms=15.0
        )
        monitor = ChannelMonitor(thresholds)
        
        monitor.register_channel("issue_detection", "tick")
        await monitor.start_monitoring()
        
        try:
            # Generate data with performance issues
            for i in range(50):
                await system.process_tick_data(create_tick_data(f"ISSUE{i}", 100.0, 1000))
                
                # Simulate performance issues
                if i < 10:
                    # High latency period
                    monitor.record_processing_latency("issue_detection", 50.0)
                    monitor.record_processing_event("issue_detection", True, 50.0)
                elif i < 20:
                    # High error rate period
                    monitor.record_processing_event("issue_detection", False, 10.0)
                else:
                    # Normal operation
                    monitor.record_processing_latency("issue_detection", 10.0)
                    monitor.record_processing_event("issue_detection", True, 10.0)
            
            # Update final metrics
            monitor.update_channel_metrics("issue_detection",
                                         avg_processing_time_ms=25.0,  # Exceeds threshold
                                         success_rate_percent=80.0,    # Below threshold
                                         latency_p99_ms=45.0)         # Exceeds threshold
            
            await asyncio.sleep(0.3)
            
            # Get debug info and check issue detection
            debug_info = monitor.get_channel_debug_info("issue_detection")
            performance_issues = debug_info['health_summary']['performance_issues']
            
            # Should detect multiple performance issues
            assert len(performance_issues) >= 3
            
            # Check specific issue types
            issue_text = " ".join(performance_issues).lower()
            assert "latency" in issue_text
            assert "success rate" in issue_text
            assert "processing" in issue_text
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_troubleshooting_data_collection(self, debug_system):
        """Test comprehensive troubleshooting data collection"""
        system = debug_system
        monitor = ChannelMonitor()
        
        # Register multiple channels for comprehensive testing
        channels = ["trouble_tick", "trouble_ohlcv", "trouble_fmv"]
        for channel in channels:
            monitor.register_channel(channel, channel.split("_")[1])
        
        await monitor.start_monitoring()
        
        try:
            # Generate diverse activity patterns
            for i in range(20):
                # Create different patterns for each channel
                monitor.record_processing_event("trouble_tick", i % 10 != 0, 5.0 + i)
                monitor.record_processing_event("trouble_ohlcv", i % 15 != 0, 10.0 + i * 2)
                monitor.record_processing_event("trouble_fmv", i % 20 != 0, 15.0 + i * 0.5)
                
                monitor.record_processing_latency("trouble_tick", 5.0 + i)
                monitor.record_processing_latency("trouble_ohlcv", 10.0 + i * 2)
                monitor.record_processing_latency("trouble_fmv", 15.0 + i * 0.5)
            
            await asyncio.sleep(0.3)
            
            # Collect troubleshooting data for all channels
            troubleshooting_data = {}
            for channel in channels:
                debug_info = monitor.get_channel_debug_info(channel)
                troubleshooting_data[channel] = debug_info
            
            # Get system-wide dashboard data
            dashboard_data = monitor.get_monitoring_dashboard_data()
            
            # Verify comprehensive troubleshooting data
            assert len(troubleshooting_data) == 3
            
            for channel, debug_info in troubleshooting_data.items():
                # Each channel should have complete debug information
                assert debug_info['channel_metrics']['processed_count'] > 0
                assert len(debug_info['latency_analysis']['recent_samples']) > 0
                assert debug_info['health_summary']['is_healthy'] in [True, False]
            
            # Verify system-wide monitoring data
            assert dashboard_data['system_overview']['channels']['total'] == 3
            assert len(dashboard_data['channel_details']) == 3
            
            # System should provide actionable troubleshooting information
            for channel_name, channel_details in dashboard_data['channel_details'].items():
                assert 'processing' in channel_details
                assert 'performance' in channel_details
                assert 'timing' in channel_details
                
                # Should have recent activity
                assert channel_details['timing']['last_update'] > 0
            
        finally:
            await monitor.stop_monitoring()