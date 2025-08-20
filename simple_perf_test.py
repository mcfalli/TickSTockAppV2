#!/usr/bin/env python3
"""
Simple Channel Performance Test
Sprint 105: Core Channel Infrastructure Validation
"""

import asyncio
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_basic_performance():
    """Test basic channel performance"""
    try:
        from src.processing.channels.base_channel import ProcessingChannel, ChannelType, ProcessingResult
        print("SUCCESS: Imports working")
        
        # Create mock channel for testing
        class TestChannel(ProcessingChannel):
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
                super().__init__(name, config)
                
            def get_channel_type(self):
                return ChannelType.TICK
                
            async def initialize(self):
                return True
                
            def validate_data(self, data):
                return True
                
            async def process_data(self, data):
                await asyncio.sleep(0.001)  # Simulate processing
                return ProcessingResult(success=True, events=[])
                
            async def shutdown(self):
                return True
        
        # Test performance
        channel = TestChannel("perf_test")
        await channel.start()
        
        print("Testing channel performance...")
        start_time = time.time()
        
        # Process 100 items
        for i in range(100):
            success = await channel.submit_data({'ticker': 'AAPL', 'price': 150.0})
            if not success:
                print(f"FAILED: Item {i} not processed")
        
        elapsed = time.time() - start_time
        throughput = 100 / elapsed
        
        await channel.stop()
        
        print(f"RESULTS:")
        print(f"  Processed: 100 items")
        print(f"  Time: {elapsed:.3f} seconds") 
        print(f"  Throughput: {throughput:.1f} items/sec")
        
        # Performance requirement: >50 items/sec
        if throughput > 50:
            print("PASS: Performance requirement met")
            return True
        else:
            print("FAIL: Performance below requirement")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Channel Infrastructure Performance Test")
    print("=" * 50)
    
    success = asyncio.run(test_basic_performance())
    
    if success:
        print("OVERALL: SUCCESS")
        sys.exit(0)
    else:
        print("OVERALL: FAILED")
        sys.exit(1)