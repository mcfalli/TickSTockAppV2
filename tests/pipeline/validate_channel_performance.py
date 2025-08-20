#!/usr/bin/env python3
"""
Channel Infrastructure Performance Validation Script.

Validates performance characteristics of the multi-channel processing system
and identifies optimization opportunities.

Sprint 105: Core Channel Infrastructure Testing
"""

import asyncio
import time
import sys
import os
from typing import List, Dict, Any
from dataclasses import dataclass
from statistics import mean, stdev

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import channel infrastructure components
try:
    from src.processing.channels.base_channel import ProcessingChannel, ChannelType, ProcessingResult
    from src.processing.channels.channel_router import DataChannelRouter, RoutingStrategy
    from src.processing.channels.channel_metrics import ChannelMetrics
    print("SUCCESS: Channel infrastructure imports successful")
except ImportError as e:
    print(f"ERROR: Import error: {e}")
    sys.exit(1)


@dataclass
class PerformanceResult:
    """Performance test result"""
    test_name: str
    throughput: float  # items/second
    avg_latency_ms: float
    success_rate: float
    memory_usage_mb: float
    passed: bool


class MockTickChannel(ProcessingChannel):
    """Lightweight mock channel for performance testing"""
    
    def __init__(self, name: str):
        # Create minimal config
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
        self.process_calls = []
        
    def get_channel_type(self) -> ChannelType:
        return ChannelType.TICK
    
    async def initialize(self) -> bool:
        await asyncio.sleep(0.001)  # Simulate minimal initialization
        return True
    
    def validate_data(self, data: Any) -> bool:
        return isinstance(data, dict) and 'ticker' in data and 'price' in data
    
    async def process_data(self, data: Any) -> ProcessingResult:
        self.process_calls.append(data)
        await asyncio.sleep(0.001)  # Simulate minimal processing time
        
        # Create mock event
        mock_event = type('MockEvent', (), {
            'ticker': data.get('ticker', 'TEST'),
            'type': 'tick',
            'price': data.get('price', 0.0),
            'event_id': f"mock_{len(self.process_calls)}",
            'time': time.time()
        })()
        
        return ProcessingResult(
            success=True,
            events=[mock_event],
            metadata={'channel': self.name, 'processed_at': time.time()}
        )
    
    async def shutdown(self) -> bool:
        await asyncio.sleep(0.001)  # Simulate cleanup
        return True


async def test_single_channel_throughput() -> PerformanceResult:
    """Test throughput of a single channel"""
    print("🧪 Testing single channel throughput...")
    
    channel = MockTickChannel("throughput_test")
    await channel.start()
    
    # Generate test data
    test_data = [
        {'ticker': 'AAPL', 'price': 150.0 + i * 0.1, 'volume': 1000}
        for i in range(1000)
    ]
    
    start_time = time.time()
    successful_count = 0
    latencies = []
    
    for data in test_data:
        item_start = time.time()
        result = await channel.process_with_metrics(data)
        latency_ms = (time.time() - item_start) * 1000
        latencies.append(latency_ms)
        
        if result.success:
            successful_count += 1
    
    elapsed = time.time() - start_time
    
    await channel.stop()
    
    throughput = len(test_data) / elapsed
    avg_latency = mean(latencies)
    success_rate = successful_count / len(test_data)
    
    return PerformanceResult(
        test_name="Single Channel Throughput",
        throughput=throughput,
        avg_latency_ms=avg_latency,
        success_rate=success_rate,
        memory_usage_mb=0.0,  # Simplified for this test
        passed=throughput > 500 and success_rate > 0.95  # Requirements
    )


async def test_multi_channel_routing() -> PerformanceResult:
    """Test routing performance across multiple channels"""
    print("🧪 Testing multi-channel routing...")
    
    router = DataChannelRouter()
    
    # Add multiple channels
    channels = []
    for i in range(3):
        channel = MockTickChannel(f"routing_test_{i}")
        await channel.start()
        router.add_channel(channel)
        channels.append(channel)
    
    # Generate test data
    test_data = [
        {'ticker': f'STOCK{i%10}', 'price': 100.0 + i * 0.1, 'volume': 1000}
        for i in range(500)
    ]
    
    start_time = time.time()
    successful_count = 0
    latencies = []
    
    for data in test_data:
        item_start = time.time()
        result = await router.route_data(data)
        latency_ms = (time.time() - item_start) * 1000
        latencies.append(latency_ms)
        
        if result and result.success:
            successful_count += 1
    
    elapsed = time.time() - start_time
    
    # Cleanup
    for channel in channels:
        await channel.stop()
    
    throughput = len(test_data) / elapsed
    avg_latency = mean(latencies)
    success_rate = successful_count / len(test_data)
    
    return PerformanceResult(
        test_name="Multi-Channel Routing",
        throughput=throughput,
        avg_latency_ms=avg_latency,
        success_rate=success_rate,
        memory_usage_mb=0.0,
        passed=throughput > 300 and success_rate > 0.90  # Lower requirements due to routing overhead
    )


async def test_concurrent_processing() -> PerformanceResult:
    """Test concurrent processing capabilities"""
    print("🧪 Testing concurrent processing...")
    
    channels = []
    for i in range(5):
        channel = MockTickChannel(f"concurrent_test_{i}")
        await channel.start()
        channels.append(channel)
    
    # Generate concurrent tasks
    test_data = [
        {'ticker': f'CONC{i%20}', 'price': 200.0 + i * 0.05, 'volume': 1000}
        for i in range(1000)
    ]
    
    async def process_batch(channel, batch_data):
        results = []
        for data in batch_data:
            result = await channel.process_with_metrics(data)
            results.append(result)
        return results
    
    # Split data across channels
    batch_size = len(test_data) // len(channels)
    tasks = []
    
    start_time = time.time()
    
    for i, channel in enumerate(channels):
        start_idx = i * batch_size
        end_idx = start_idx + batch_size if i < len(channels) - 1 else len(test_data)
        batch_data = test_data[start_idx:end_idx]
        
        task = process_batch(channel, batch_data)
        tasks.append(task)
    
    results_batches = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time
    
    # Analyze results
    all_results = []
    for batch in results_batches:
        all_results.extend(batch)
    
    successful_count = sum(1 for r in all_results if r.success)
    avg_latency = mean(r.processing_time_ms for r in all_results if r.processing_time_ms > 0)
    
    # Cleanup
    for channel in channels:
        await channel.stop()
    
    throughput = len(test_data) / elapsed
    success_rate = successful_count / len(test_data)
    
    return PerformanceResult(
        test_name="Concurrent Processing",
        throughput=throughput,
        avg_latency_ms=avg_latency,
        success_rate=success_rate,
        memory_usage_mb=0.0,
        passed=throughput > 800 and success_rate > 0.95  # Higher throughput expected
    )


async def test_load_balancing_efficiency() -> PerformanceResult:
    """Test load balancing efficiency"""
    print("🧪 Testing load balancing efficiency...")
    
    router = DataChannelRouter()
    router.set_routing_strategy(RoutingStrategy.ROUND_ROBIN)
    
    # Add channels with simulated different loads
    channels = []
    for i in range(4):
        channel = MockTickChannel(f"lb_test_{i}")
        await channel.start()
        router.add_channel(channel)
        channels.append(channel)
    
    test_data = [
        {'ticker': f'LB{i%5}', 'price': 50.0 + i * 0.02, 'volume': 1000}
        for i in range(400)
    ]
    
    start_time = time.time()
    successful_count = 0
    
    for data in test_data:
        result = await router.route_data(data)
        if result and result.success:
            successful_count += 1
    
    elapsed = time.time() - start_time
    
    # Check load distribution
    call_counts = [len(channel.process_calls) for channel in channels]
    max_calls = max(call_counts)
    min_calls = min(call_counts)
    load_balance_ratio = min_calls / max_calls if max_calls > 0 else 0
    
    # Cleanup
    for channel in channels:
        await channel.stop()
    
    throughput = len(test_data) / elapsed
    success_rate = successful_count / len(test_data)
    
    return PerformanceResult(
        test_name="Load Balancing Efficiency",
        throughput=throughput,
        avg_latency_ms=1.0,  # Simplified for this test
        success_rate=success_rate,
        memory_usage_mb=0.0,
        passed=success_rate > 0.90 and load_balance_ratio > 0.7  # Well-balanced load
    )


async def run_performance_validation():
    """Run complete performance validation suite"""
    print("🚀 Sprint 105 Channel Infrastructure Performance Validation")
    print("=" * 70)
    
    # Run all performance tests
    tests = [
        test_single_channel_throughput(),
        test_multi_channel_routing(),
        test_concurrent_processing(),
        test_load_balancing_efficiency()
    ]
    
    results = await asyncio.gather(*tests)
    
    # Generate report
    print("\n📊 Performance Test Results")
    print("=" * 70)
    
    passed_tests = 0
    
    for result in results:
        status_emoji = "✅" if result.passed else "❌"
        print(f"{status_emoji} {result.test_name}")
        print(f"   Throughput: {result.throughput:.1f} items/sec")
        print(f"   Avg Latency: {result.avg_latency_ms:.2f} ms")
        print(f"   Success Rate: {result.success_rate:.2%}")
        
        if result.passed:
            passed_tests += 1
        print()
    
    # Summary
    overall_success = passed_tests == len(results)
    success_rate = (passed_tests / len(results)) * 100
    
    print("📈 Overall Performance Summary:")
    print(f"   Tests Passed: {passed_tests}/{len(results)}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    if overall_success:
        print("🎉 All performance tests passed!")
        print("✅ Sprint 105 channel infrastructure meets performance requirements")
    else:
        print("⚠️  Some performance tests failed")
        print("🔧 Optimization opportunities identified")
    
    return overall_success


if __name__ == "__main__":
    try:
        success = asyncio.run(run_performance_validation())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Performance validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)