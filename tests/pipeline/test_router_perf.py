#!/usr/bin/env python3
"""
Router Performance Test
Sprint 105: Test routing performance
"""

import asyncio
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_router_performance():
    """Test router performance with multiple channels"""
    try:
        from src.processing.channels.channel_router import DataChannelRouter, RouterConfig
        from src.processing.channels.base_channel import ProcessingChannel, ChannelType, ProcessingResult
        print("SUCCESS: Router imports working")
        
        # Create mock channel
        class MockChannel(ProcessingChannel):
            def __init__(self, name: str):
                from types import SimpleNamespace
                config = SimpleNamespace()
                config.max_queue_size = 1000
                config.circuit_breaker_threshold = 10
                config.circuit_breaker_timeout = 60.0
                config.batching = SimpleNamespace()
                config.batching.strategy = SimpleNamespace()
                config.batching.strategy.value = "immediate"
                config.batching.max_batch_size = 10
                config.batching.max_wait_time_ms = 1000
                self._channel_type = ChannelType.TICK
                super().__init__(name, config)
                
            def get_channel_type(self):
                return self._channel_type
                
            async def initialize(self):
                return True
                
            def validate_data(self, data):
                return True
                
            async def process_data(self, data):
                await asyncio.sleep(0.001)
                return ProcessingResult(success=True, events=[], metadata={'channel': self.name})
                
            async def shutdown(self):
                return True
        
        # Setup router with multiple channels
        router_config = RouterConfig()
        router = DataChannelRouter(router_config)
        
        channels = []
        for i in range(3):
            channel = MockChannel(f"channel_{i}")
            await channel.start()
            router.register_channel(channel)
            channels.append(channel)
        
        print("Testing router with 3 channels...")
        
        # Test data routing performance
        test_data = [
            {'ticker': 'AAPL', 'price': 150.0 + i * 0.1, 'volume': 1000}
            for i in range(50)
        ]
        
        start_time = time.time()
        successful = 0
        
        for data in test_data:
            result = await router.route_data(data)
            if result and result.success:
                successful += 1
        
        elapsed = time.time() - start_time
        throughput = len(test_data) / elapsed
        success_rate = successful / len(test_data)
        
        # Cleanup
        for channel in channels:
            await channel.stop()
        
        print(f"RESULTS:")
        print(f"  Routed: {len(test_data)} items")
        print(f"  Successful: {successful}")
        print(f"  Time: {elapsed:.3f} seconds")
        print(f"  Throughput: {throughput:.1f} items/sec")
        print(f"  Success Rate: {success_rate:.1%}")
        
        # Performance requirements
        if throughput > 30 and success_rate > 0.9:
            print("PASS: Router performance acceptable")
            return True
        else:
            print("FAIL: Router performance below requirements")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Router Performance Test")
    print("=" * 30)
    
    success = asyncio.run(test_router_performance())
    
    if success:
        print("ROUTER TEST: SUCCESS")
        sys.exit(0)
    else:
        print("ROUTER TEST: FAILED")
        sys.exit(1)