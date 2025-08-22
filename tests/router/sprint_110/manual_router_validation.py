"""
Sprint 110: Manual Router Delegation Validation Script

This script provides manual testing procedures for validating the 
Channel Router Architecture fixes using synthetic per-minute data
for end-to-end validation.

Usage:
    python manual_router_validation.py

Created: 2025-08-22
Sprint: 110
"""

import asyncio
import sys
import os
import time
import logging
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import router components
from src.processing.channels.channel_router import DataChannelRouter, RouterConfig, RoutingStrategy
from src.processing.channels.tick_channel import TickChannel
from src.processing.channels.channel_config import TickChannelConfig
from src.processing.channels.base_channel import ChannelType, ChannelStatus

# Import test data utilities
from tests.fixtures.market_data_fixtures import create_tick_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('manual_router_validation')

class RouterValidationTester:
    """Manual testing utility for router delegation validation"""
    
    def __init__(self):
        self.router = None
        self.tick_channel = None
        self.test_results = {}
    
    async def setup(self):
        """Initialize router and channel for testing"""
        logger.info("🚀 SPRINT 110: Setting up router validation test environment...")
        
        # Create router configuration
        config = RouterConfig(
            routing_strategy=RoutingStrategy.HEALTH_BASED,
            enable_load_balancing=True,
            routing_timeout_ms=100.0,
            enable_fallback_routing=True,
            health_check_interval=30.0,
            enable_metrics_collection=True
        )
        
        # Initialize router
        self.router = DataChannelRouter(config)
        logger.info(f"✅ Router initialized with config: {config.routing_strategy.value}")
        
        # Create and initialize tick channel
        tick_config = TickChannelConfig(name="validation_tick_config")
        self.tick_channel = TickChannel("validation_tick_channel", tick_config)
        
        # Start channel
        await self.tick_channel.start()
        logger.info(f"✅ TickChannel started - Status: {self.tick_channel.status.value}, Healthy: {self.tick_channel.is_healthy()}")
        
        # Register channel with router
        self.router.register_channel(self.tick_channel)
        
        # Verify registration
        registered_channels = self.router.channels.get(ChannelType.TICK, [])
        logger.info(f"✅ Router registration complete - {len(registered_channels)} tick channels registered")
        
        # Display initial metrics
        self.display_metrics("Initial")
    
    async def test_single_tick_routing(self):
        """Test single tick routing to verify basic functionality"""
        logger.info("\n📊 SPRINT 110 TEST 1: Single Tick Routing")
        
        # Create test tick
        test_tick = create_tick_data(ticker="AAPL", price=150.0, volume=1000)
        logger.info(f"Processing tick: {test_tick.ticker} @ ${test_tick.price}")
        
        # Route through router
        start_time = time.time()
        result = await self.router.route_data(test_tick)
        processing_time = (time.time() - start_time) * 1000
        
        # Analyze result
        if result:
            success = result.success
            events_count = len(result.events) if result.events else 0
            channel_name = result.metadata.get('channel', 'unknown')
            
            logger.info(f"✅ Routing Result: Success={success}, Events={events_count}, Channel={channel_name}, Time={processing_time:.2f}ms")
            
            self.test_results['single_tick'] = {
                'success': success,
                'events_generated': events_count,
                'processing_time_ms': processing_time,
                'channel_used': channel_name
            }
        else:
            logger.error("❌ Routing failed - No result returned")
            self.test_results['single_tick'] = {'success': False, 'error': 'No result returned'}
        
        self.display_metrics("After Single Tick")
    
    async def test_multi_tick_sequence(self):
        """Test multiple tick sequence to verify sustained routing"""
        logger.info("\n📊 SPRINT 110 TEST 2: Multi-Tick Sequence Routing")
        
        # Create sequence of test ticks
        test_ticks = [
            create_tick_data(ticker="AAPL", price=150.0, volume=1000),
            create_tick_data(ticker="AAPL", price=150.5, volume=1200),
            create_tick_data(ticker="AAPL", price=151.0, volume=800),
            create_tick_data(ticker="MSFT", price=300.0, volume=500),
            create_tick_data(ticker="MSFT", price=301.0, volume=600),
            create_tick_data(ticker="GOOGL", price=2500.0, volume=300),
        ]
        
        successful_routes = 0
        total_events = 0
        total_time = 0
        
        logger.info(f"Processing sequence of {len(test_ticks)} ticks...")
        
        for i, tick in enumerate(test_ticks, 1):
            logger.info(f"  Tick {i}/{len(test_ticks)}: {tick.ticker} @ ${tick.price}")
            
            start_time = time.time()
            result = await self.router.route_data(tick)
            processing_time = (time.time() - start_time) * 1000
            total_time += processing_time
            
            if result and result.success:
                successful_routes += 1
                events_count = len(result.events) if result.events else 0
                total_events += events_count
                logger.info(f"    ✅ Success: {events_count} events, {processing_time:.2f}ms")
            else:
                error_msg = result.errors if result and result.errors else ["Unknown error"]
                logger.warning(f"    ❌ Failed: {error_msg}")
        
        # Summary
        success_rate = (successful_routes / len(test_ticks)) * 100
        avg_time = total_time / len(test_ticks)
        
        logger.info(f"\n📈 Multi-Tick Results:")
        logger.info(f"  Success Rate: {successful_routes}/{len(test_ticks)} ({success_rate:.1f}%)")
        logger.info(f"  Total Events: {total_events}")
        logger.info(f"  Avg Time: {avg_time:.2f}ms")
        
        self.test_results['multi_tick'] = {
            'total_ticks': len(test_ticks),
            'successful_routes': successful_routes,
            'success_rate_percent': success_rate,
            'total_events_generated': total_events,
            'avg_processing_time_ms': avg_time
        }
        
        self.display_metrics("After Multi-Tick Sequence")
    
    async def test_delegation_counting(self):
        """Test delegation count tracking to verify Sprint 110 metrics fix"""
        logger.info("\n📊 SPRINT 110 TEST 3: Delegation Count Tracking")
        
        # Get initial delegation count
        initial_delegated = getattr(self.router.metrics, 'delegated_routes', 0)
        initial_successful = self.router.metrics.successful_routes
        
        logger.info(f"Initial Metrics - Delegated: {initial_delegated}, Successful: {initial_successful}")
        
        # Process test ticks
        test_ticks = [
            create_tick_data(ticker="TEST1", price=100.0, volume=500),
            create_tick_data(ticker="TEST2", price=200.0, volume=750),
        ]
        
        for tick in test_ticks:
            result = await self.router.route_data(tick)
            if result:
                logger.info(f"  {tick.ticker}: {'SUCCESS' if result.success else 'FAILED'}")
        
        # Get final delegation count
        final_delegated = getattr(self.router.metrics, 'delegated_routes', 0)
        final_successful = self.router.metrics.successful_routes
        
        delegated_change = final_delegated - initial_delegated
        successful_change = final_successful - initial_successful
        
        logger.info(f"Final Metrics - Delegated: {final_delegated} (+{delegated_change}), Successful: {final_successful} (+{successful_change})")
        
        # Verify delegation tracking works
        if delegated_change > 0:
            logger.info(f"✅ SPRINT 110 SUCCESS: Delegation tracking working - {delegated_change} new delegations")
        else:
            logger.warning(f"❌ SPRINT 110 ISSUE: No delegation count increase detected")
        
        self.test_results['delegation_tracking'] = {
            'initial_delegated': initial_delegated,
            'final_delegated': final_delegated,
            'delegation_increase': delegated_change,
            'successful_increase': successful_change
        }
    
    async def test_health_based_selection(self):
        """Test health-based channel selection to verify health integration fix"""
        logger.info("\n📊 SPRINT 110 TEST 4: Health-Based Channel Selection")
        
        # Get available channels
        available_channels = self.router.channels.get(ChannelType.TICK, [])
        logger.info(f"Available channels: {len(available_channels)}")
        
        for channel in available_channels:
            health = channel.is_healthy()
            status = channel.status.value
            error_count = channel.metrics.error_count if hasattr(channel, 'metrics') else 'N/A'
            processed_count = channel.metrics.processed_count if hasattr(channel, 'metrics') else 'N/A'
            
            logger.info(f"  Channel: {channel.name}")
            logger.info(f"    Status: {status}, Healthy: {health}")
            logger.info(f"    Errors: {error_count}, Processed: {processed_count}")
        
        # Test load balancer selection
        if available_channels:
            selected_channel = await self.router.load_balancer.get_best_channel(
                available_channels,
                RoutingStrategy.HEALTH_BASED
            )
            
            if selected_channel:
                logger.info(f"✅ Health-based selection chose: {selected_channel.name}")
                logger.info(f"  Selected channel healthy: {selected_channel.is_healthy()}")
                
                self.test_results['health_selection'] = {
                    'selected_channel': selected_channel.name,
                    'channel_healthy': selected_channel.is_healthy(),
                    'selection_successful': True
                }
            else:
                logger.warning("❌ Health-based selection returned no channel")
                self.test_results['health_selection'] = {
                    'selection_successful': False,
                    'error': 'No channel selected'
                }
        else:
            logger.warning("❌ No channels available for selection test")
            self.test_results['health_selection'] = {
                'selection_successful': False,
                'error': 'No channels available'
            }
    
    def display_metrics(self, stage: str):
        """Display current router metrics"""
        logger.info(f"\n📊 Router Metrics ({stage}):")
        logger.info(f"  Total Routed: {self.router.metrics.total_routed}")
        logger.info(f"  Successful Routes: {self.router.metrics.successful_routes}")
        logger.info(f"  Failed Routes: {self.router.metrics.failed_routes}")
        logger.info(f"  Fallback Routes: {self.router.metrics.fallback_routes}")
        
        # SPRINT 110: Display delegation tracking
        delegated = getattr(self.router.metrics, 'delegated_routes', 0)
        logger.info(f"  Delegated Routes: {delegated}")
        
        # Success rate
        if self.router.metrics.total_routed > 0:
            success_rate = (self.router.metrics.successful_routes / self.router.metrics.total_routed) * 100
            logger.info(f"  Success Rate: {success_rate:.1f}%")
    
    def display_summary(self):
        """Display test summary"""
        logger.info("\n" + "="*60)
        logger.info("🎯 SPRINT 110 ROUTER VALIDATION SUMMARY")
        logger.info("="*60)
        
        for test_name, results in self.test_results.items():
            logger.info(f"\n📋 {test_name.upper().replace('_', ' ')}:")
            for key, value in results.items():
                logger.info(f"  {key}: {value}")
        
        # Overall assessment
        successful_tests = sum(1 for results in self.test_results.values() 
                             if results.get('success', False) or results.get('selection_successful', False))
        total_tests = len(self.test_results)
        
        logger.info(f"\n🏆 OVERALL RESULTS: {successful_tests}/{total_tests} tests successful")
        
        if successful_tests == total_tests:
            logger.info("✅ SPRINT 110 VALIDATION: ALL TESTS PASSED - Router fixes working correctly!")
        else:
            logger.warning(f"⚠️ SPRINT 110 VALIDATION: {total_tests - successful_tests} tests failed - Review needed")
    
    async def cleanup(self):
        """Clean up test resources"""
        logger.info("\n🧹 Cleaning up test environment...")
        
        try:
            if self.tick_channel:
                await self.tick_channel.stop()
                logger.info("✅ TickChannel stopped")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping TickChannel: {e}")
        
        try:
            if self.router:
                await self.router.shutdown()
                logger.info("✅ Router shutdown")
        except Exception as e:
            logger.warning(f"⚠️ Error shutting down router: {e}")

async def main():
    """Main validation routine"""
    logger.info("🚀 SPRINT 110: Starting Manual Router Validation")
    logger.info("=" * 60)
    
    tester = RouterValidationTester()
    
    try:
        # Setup test environment
        await tester.setup()
        
        # Run validation tests
        await tester.test_single_tick_routing()
        await tester.test_multi_tick_sequence()
        await tester.test_delegation_counting()
        await tester.test_health_based_selection()
        
        # Display summary
        tester.display_summary()
        
    except Exception as e:
        logger.error(f"❌ Validation failed with error: {e}", exc_info=True)
    
    finally:
        # Cleanup
        await tester.cleanup()
        logger.info("\n🎯 SPRINT 110: Manual Router Validation Complete")

if __name__ == "__main__":
    # Run the validation
    asyncio.run(main())