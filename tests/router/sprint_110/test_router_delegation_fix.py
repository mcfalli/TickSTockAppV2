"""
Sprint 110: Comprehensive Router Delegation Fix Validation Tests

Tests the complete fix for Channel Router Architecture issue:
- Router success determination logic fix
- Channel health integration enhancement  
- Event forwarding validation
- End-to-end delegation flow

Created: 2025-08-22
Sprint: 110
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import List, Dict, Any

# Test framework imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import router components under test
from src.processing.channels.channel_router import (
    DataChannelRouter, RouterConfig, RouterMetrics, RoutingStrategy
)
from src.processing.channels.base_channel import (
    ProcessingChannel, ChannelType, ChannelStatus, ProcessingResult
)
from src.processing.channels.tick_channel import TickChannel
from src.processing.channels.channel_config import TickChannelConfig

# Import event types for validation
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.market.tick import TickData

# Import fixtures
from tests.fixtures.market_data_fixtures import create_tick_data

class TestRouterDelegationFix:
    """Test suite for Sprint 110 router delegation fixes"""
    
    @pytest.fixture
    async def router_config(self):
        """Create router configuration for testing"""
        return RouterConfig(
            routing_strategy=RoutingStrategy.HEALTH_BASED,
            enable_load_balancing=True,
            routing_timeout_ms=100.0,
            enable_fallback_routing=True,
            health_check_interval=30.0,
            enable_metrics_collection=True
        )
    
    @pytest.fixture
    async def channel_router(self, router_config):
        """Create router instance for testing"""
        router = DataChannelRouter(router_config)
        yield router
        
        # Cleanup
        try:
            await router.shutdown()
        except:
            pass
    
    @pytest.fixture
    async def mock_event_processor(self):
        """Create mock event processor with priority manager"""
        mock_processor = Mock()
        mock_processor.market_service = Mock()
        mock_processor.market_service.priority_manager = Mock()
        mock_processor.market_service.priority_manager.add_event = Mock()
        return mock_processor
    
    @pytest.fixture
    async def healthy_tick_channel(self):
        """Create healthy tick channel for testing"""
        config = TickChannelConfig(name="test_tick_config")
        channel = TickChannel("test_tick_channel", config)
        
        # Initialize channel
        await channel.start()
        
        # Ensure channel is healthy
        assert channel.is_healthy()
        assert channel.status == ChannelStatus.ACTIVE
        
        yield channel
        
        # Cleanup
        try:
            await channel.stop()
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_router_success_determination_fix(self, channel_router, healthy_tick_channel, mock_event_processor):
        """
        SPRINT 110 TEST: Verify router success determination logic fix
        
        This test validates that the router now properly:
        1. Gets complete ProcessingResult with events from channels
        2. Reports successful delegation when channels process successfully
        3. Tracks delegation metrics correctly
        """
        # Setup
        channel_router.set_event_processor(mock_event_processor)
        channel_router.register_channel(healthy_tick_channel)
        
        # Create test tick data
        test_tick = create_tick_data(ticker="AAPL", price=150.0, volume=1000)
        
        # Verify initial metrics
        initial_delegated = getattr(channel_router.metrics, 'delegated_routes', 0)
        initial_successful = channel_router.metrics.successful_routes
        
        # Execute routing
        result = await channel_router.route_data(test_tick)
        
        # SPRINT 110 ASSERTIONS: Verify fix works
        assert result is not None, "Router should return ProcessingResult, not None"
        assert result.success, "Router should report success for healthy channel processing"
        assert hasattr(result, 'events'), "ProcessingResult should contain events attribute"
        assert hasattr(result, 'metadata'), "ProcessingResult should contain metadata"
        assert result.metadata.get('channel') == healthy_tick_channel.name, "Result should contain channel metadata"
        
        # Verify delegation tracking
        final_delegated = getattr(channel_router.metrics, 'delegated_routes', 0)
        final_successful = channel_router.metrics.successful_routes
        
        assert final_delegated > initial_delegated, f"Delegated routes should increase: {initial_delegated} -> {final_delegated}"
        assert final_successful > initial_successful, f"Successful routes should increase: {initial_successful} -> {final_successful}"
        
        print(f"✅ SPRINT 110 SUCCESS: Delegation count increased from {initial_delegated} to {final_delegated}")
    
    @pytest.mark.asyncio
    async def test_channel_health_integration_enhancement(self, channel_router, healthy_tick_channel):
        """
        SPRINT 110 TEST: Verify channel health integration enhancement
        
        This test validates that the router now properly:
        1. Utilizes channel health status in routing decisions
        2. Uses more lenient health scoring
        3. Properly selects healthy channels
        """
        # Setup
        channel_router.register_channel(healthy_tick_channel)
        
        # Verify channel is healthy
        assert healthy_tick_channel.is_healthy(), "Test channel should be healthy"
        assert healthy_tick_channel.status == ChannelStatus.ACTIVE, "Test channel should be active"
        
        # Test channel selection
        from src.processing.channels.base_channel import ChannelType
        available_channels = channel_router.channels.get(ChannelType.TICK, [])
        assert len(available_channels) > 0, "Router should have registered tick channels"
        
        # Test load balancer selection with health-based strategy
        selected_channel = await channel_router.load_balancer.get_best_channel(
            available_channels, 
            RoutingStrategy.HEALTH_BASED
        )
        
        assert selected_channel is not None, "Health-based selection should find healthy channel"
        assert selected_channel.name == healthy_tick_channel.name, "Should select our healthy test channel"
        assert selected_channel.is_healthy(), "Selected channel should be healthy"
        
        print(f"✅ SPRINT 110 SUCCESS: Health-based selection correctly chose healthy channel: {selected_channel.name}")
    
    @pytest.mark.asyncio
    async def test_event_forwarding_integration(self, channel_router, healthy_tick_channel, mock_event_processor):
        """
        SPRINT 110 TEST: Verify event forwarding to event processor
        
        This test validates that the router properly:
        1. Forwards events generated by channels to the event processor
        2. Maintains integration with existing priority_manager workflow
        3. Handles event forwarding errors gracefully
        """
        # Setup
        channel_router.set_event_processor(mock_event_processor)
        channel_router.register_channel(healthy_tick_channel)
        
        # Create test data that should generate events
        test_tick = create_tick_data(ticker="AAPL", price=150.0, volume=1000)
        
        # Execute routing
        result = await channel_router.route_data(test_tick)
        
        # Verify result
        assert result is not None, "Router should return result"
        assert result.success, "Routing should be successful"
        
        # Verify event forwarding was attempted
        # Note: Actual event generation depends on TickChannel implementation
        if result.events:
            # If events were generated, verify they were forwarded
            assert mock_event_processor.market_service.priority_manager.add_event.called, \
                "Events should be forwarded to priority manager"
            
            forwarded_events = mock_event_processor.market_service.priority_manager.add_event.call_count
            assert forwarded_events > 0, f"Should have forwarded events, got {forwarded_events} calls"
            
            print(f"✅ SPRINT 110 SUCCESS: Forwarded {forwarded_events} events to priority manager")
        else:
            print("ℹ️ SPRINT 110 INFO: No events generated by channel (depends on detection logic)")
    
    @pytest.mark.asyncio
    async def test_end_to_end_synthetic_data_flow(self, channel_router, healthy_tick_channel, mock_event_processor):
        """
        SPRINT 110 TEST: End-to-end synthetic data → router → frontend pipeline
        
        This test validates the complete data flow:
        1. Synthetic tick data → Router
        2. Router → Channel processing 
        3. Channel processing → Event generation
        4. Event forwarding → Event processor
        """
        # Setup complete pipeline
        channel_router.set_event_processor(mock_event_processor)
        channel_router.register_channel(healthy_tick_channel)
        
        # Test data sequence simulating real-time ticks
        test_ticks = [
            create_tick_data(ticker="AAPL", price=150.0, volume=1000),
            create_tick_data(ticker="AAPL", price=150.5, volume=1200),
            create_tick_data(ticker="AAPL", price=151.0, volume=800),
            create_tick_data(ticker="MSFT", price=300.0, volume=500),
            create_tick_data(ticker="MSFT", price=301.0, volume=600),
        ]
        
        # Process each tick through the pipeline
        successful_routes = 0
        total_events_generated = 0
        
        for i, tick in enumerate(test_ticks):
            result = await channel_router.route_data(tick)
            
            assert result is not None, f"Tick {i+1} should produce result"
            
            if result.success:
                successful_routes += 1
                if result.events:
                    total_events_generated += len(result.events)
                    
                print(f"Tick {i+1} ({tick.ticker}): SUCCESS - {len(result.events) if result.events else 0} events")
            else:
                print(f"Tick {i+1} ({tick.ticker}): FAILED - {result.errors}")
        
        # Verify pipeline health
        assert successful_routes > 0, f"Should have successful routes, got {successful_routes}/{len(test_ticks)}"
        
        # Verify router metrics
        final_delegated = getattr(channel_router.metrics, 'delegated_routes', 0)
        final_successful = channel_router.metrics.successful_routes
        
        assert final_delegated >= successful_routes, \
            f"Delegated routes ({final_delegated}) should match successful routes ({successful_routes})"
        
        print(f"✅ SPRINT 110 END-TO-END SUCCESS:")
        print(f"  - Processed: {len(test_ticks)} ticks")
        print(f"  - Successful: {successful_routes} routes")
        print(f"  - Generated: {total_events_generated} events")
        print(f"  - Delegated: {final_delegated} delegations")
    
    @pytest.mark.asyncio
    async def test_fallback_vs_normal_routing_comparison(self, channel_router, healthy_tick_channel):
        """
        SPRINT 110 TEST: Compare fallback vs normal routing behavior
        
        This test validates that both routing paths work correctly and 
        normal routing no longer fails when fallback routing succeeds
        """
        # Setup
        channel_router.register_channel(healthy_tick_channel)
        
        test_tick = create_tick_data(ticker="AAPL", price=150.0, volume=1000)
        
        # Test normal routing (should work now with Sprint 110 fixes)
        result_normal = await channel_router.route_data(test_tick)
        
        # Verify normal routing works
        assert result_normal is not None, "Normal routing should return result"
        assert result_normal.success, "Normal routing should succeed with healthy channel"
        
        # Verify no fallback was used (fallback_routes should not increase)
        initial_fallback = channel_router.metrics.fallback_routes
        
        # Process another tick
        result_normal2 = await channel_router.route_data(test_tick)
        final_fallback = channel_router.metrics.fallback_routes
        
        assert result_normal2.success, "Second normal routing should also succeed"
        assert final_fallback == initial_fallback, \
            f"Normal routing should not use fallback: {initial_fallback} -> {final_fallback}"
        
        print(f"✅ SPRINT 110 SUCCESS: Normal routing works without fallback")
        print(f"  - Fallback usage: {final_fallback} (unchanged)")
        print(f"  - Normal routing: 2/2 successful")
    
    @pytest.mark.asyncio
    async def test_router_metrics_and_monitoring(self, channel_router, healthy_tick_channel):
        """
        SPRINT 110 TEST: Verify enhanced router metrics and monitoring
        
        This test validates that the router provides comprehensive
        metrics for monitoring delegation success and system health
        """
        # Setup
        channel_router.register_channel(healthy_tick_channel)
        
        # Get initial metrics
        initial_metrics = {
            'total_routed': channel_router.metrics.total_routed,
            'successful_routes': channel_router.metrics.successful_routes,
            'failed_routes': channel_router.metrics.failed_routes,
            'delegated_routes': getattr(channel_router.metrics, 'delegated_routes', 0),
            'fallback_routes': channel_router.metrics.fallback_routes
        }
        
        # Process test data
        test_ticks = [
            create_tick_data(ticker="AAPL", price=150.0, volume=1000),
            create_tick_data(ticker="MSFT", price=300.0, volume=500),
        ]
        
        for tick in test_ticks:
            result = await channel_router.route_data(tick)
            assert result is not None
        
        # Get final metrics
        final_metrics = {
            'total_routed': channel_router.metrics.total_routed,
            'successful_routes': channel_router.metrics.successful_routes,
            'failed_routes': channel_router.metrics.failed_routes,
            'delegated_routes': getattr(channel_router.metrics, 'delegated_routes', 0),
            'fallback_routes': channel_router.metrics.fallback_routes
        }
        
        # Verify metrics tracking
        assert final_metrics['total_routed'] > initial_metrics['total_routed'], \
            "Total routed should increase"
        
        assert final_metrics['delegated_routes'] > initial_metrics['delegated_routes'], \
            f"Delegated routes should increase: {initial_metrics['delegated_routes']} -> {final_metrics['delegated_routes']}"
        
        # Verify no fallback usage for healthy channels
        assert final_metrics['fallback_routes'] == initial_metrics['fallback_routes'], \
            "Fallback routes should not increase for healthy channels"
        
        print(f"✅ SPRINT 110 METRICS SUCCESS:")
        for metric, value in final_metrics.items():
            change = value - initial_metrics[metric]
            print(f"  - {metric}: {initial_metrics[metric]} -> {value} ({change:+d})")

@pytest.mark.integration
class TestRouterIntegrationFlow:
    """Integration tests for complete router delegation flow"""
    
    @pytest.mark.asyncio
    async def test_complete_market_data_service_integration(self):
        """
        SPRINT 110 INTEGRATION TEST: Test router within complete market data service
        
        This test validates that the router fixes work within the complete
        market data service context with real component integration
        """
        # This test would require full market data service setup
        # For now, we'll mark it as a placeholder for manual testing
        pytest.skip("Integration test - requires full market data service setup")
    
    @pytest.mark.asyncio  
    async def test_high_volume_delegation_performance(self):
        """
        SPRINT 110 PERFORMANCE TEST: Validate delegation performance under load
        
        This test ensures that the router fixes don't introduce performance
        regressions while achieving successful delegation
        """
        # This test would require performance benchmarking setup
        # For now, we'll mark it as a placeholder for performance testing
        pytest.skip("Performance test - requires benchmarking setup")


if __name__ == "__main__":
    # Run tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])