"""
Unit tests for ProcessingChannel abstract base class.

Tests comprehensive functionality including:
- Channel lifecycle management
- Async processing with metrics
- Circuit breaker patterns
- Batch processing and queuing
- Error handling and recovery

Sprint 105: Core Channel Infrastructure Testing
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass
from typing import List, Any

from src.processing.channels.base_channel import (
    ProcessingChannel,
    ChannelType,
    ChannelStatus,
    ProcessingResult
)
from src.processing.channels.channel_config import ChannelConfig, BatchingConfig, BatchingStrategy
from src.core.domain.events.base import BaseEvent


@dataclass
class MockChannelConfig(ChannelConfig):
    """Mock configuration for testing"""
    max_queue_size: int = 100
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0
    batching: BatchingConfig = BatchingConfig(
        strategy=BatchingStrategy.IMMEDIATE,
        max_batch_size=10,
        max_wait_time_ms=1000
    )


class ConcreteTestChannel(ProcessingChannel):
    """Concrete implementation for testing abstract base class"""
    
    def __init__(self, name: str = "test_channel", config: ChannelConfig = None):
        if config is None:
            config = MockChannelConfig()
        super().__init__(name, config)
        self.initialize_called = False
        self.shutdown_called = False
        self.process_data_calls = []
        self.validation_result = True
        self.processing_should_fail = False

    def get_channel_type(self) -> ChannelType:
        return ChannelType.TICK

    async def initialize(self) -> bool:
        self.initialize_called = True
        await asyncio.sleep(0.01)  # Simulate initialization work
        return True

    def validate_data(self, data: Any) -> bool:
        return self.validation_result

    async def process_data(self, data: Any) -> ProcessingResult:
        self.process_data_calls.append(data)
        await asyncio.sleep(0.01)  # Simulate processing time
        
        if self.processing_should_fail:
            return ProcessingResult(
                success=False,
                errors=["Simulated processing failure"]
            )
        
        # Create mock event
        mock_event = Mock(spec=BaseEvent)
        mock_event.ticker = "AAPL"
        mock_event.type = "test"
        mock_event.price = 150.0
        
        return ProcessingResult(
            success=True,
            events=[mock_event],
            metadata={"processed_data": str(data)}
        )

    async def shutdown(self) -> bool:
        self.shutdown_called = True
        await asyncio.sleep(0.01)  # Simulate shutdown work
        return True


class TestProcessingChannelLifecycle:
    """Test channel lifecycle management"""

    @pytest.fixture
    def channel(self):
        return ConcreteTestChannel()

    @pytest.mark.asyncio
    async def test_channel_initialization(self, channel):
        """Test channel initialization process"""
        assert channel.status == ChannelStatus.INITIALIZING
        assert not channel.initialize_called
        
        success = await channel.start()
        
        assert success
        assert channel.initialize_called
        assert channel.status == ChannelStatus.ACTIVE
        assert channel.metrics.start_time is not None

    @pytest.mark.asyncio
    async def test_channel_shutdown(self, channel):
        """Test graceful channel shutdown"""
        await channel.start()
        assert channel.status == ChannelStatus.ACTIVE
        
        success = await channel.stop()
        
        assert success
        assert channel.shutdown_called
        assert channel.status == ChannelStatus.SHUTDOWN

    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test handling of initialization failure"""
        class FailingChannel(ConcreteTestChannel):
            async def initialize(self) -> bool:
                return False
        
        channel = FailingChannel()
        success = await channel.start()
        
        assert not success
        assert channel.status == ChannelStatus.ERROR

    @pytest.mark.asyncio
    async def test_shutdown_with_exception(self):
        """Test shutdown handling when shutdown method raises exception"""
        class ExceptionShutdownChannel(ConcreteTestChannel):
            async def shutdown(self) -> bool:
                raise Exception("Shutdown failed")
        
        channel = ExceptionShutdownChannel()
        await channel.start()
        
        success = await channel.stop()
        
        assert not success
        assert channel.status == ChannelStatus.SHUTDOWN


class TestProcessingChannelProcessing:
    """Test core data processing functionality"""

    @pytest.fixture
    def channel(self):
        return ConcreteTestChannel()

    @pytest.fixture
    async def active_channel(self, channel):
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_immediate_processing_success(self, active_channel):
        """Test successful immediate data processing"""
        test_data = {"ticker": "AAPL", "price": 150.0}
        
        result = await active_channel.process_with_metrics(test_data)
        
        assert result.success
        assert len(result.events) == 1
        assert result.processing_time_ms > 0
        assert len(result.errors) == 0
        assert active_channel.metrics.processed_count == 1

    @pytest.mark.asyncio
    async def test_data_validation_failure(self, active_channel):
        """Test data validation failure handling"""
        active_channel.validation_result = False
        test_data = {"invalid": "data"}
        
        result = await active_channel.process_with_metrics(test_data)
        
        assert not result.success
        assert len(result.errors) == 1
        assert "Invalid data format" in result.errors[0]
        assert active_channel.metrics.error_count == 1

    @pytest.mark.asyncio
    async def test_processing_failure(self, active_channel):
        """Test handling of processing failures"""
        active_channel.processing_should_fail = True
        test_data = {"ticker": "AAPL"}
        
        result = await active_channel.process_with_metrics(test_data)
        
        assert not result.success
        assert len(result.errors) == 1
        assert "Simulated processing failure" in result.errors[0]
        assert active_channel.metrics.error_count == 1

    @pytest.mark.asyncio
    async def test_processing_exception_handling(self, active_channel):
        """Test exception handling during processing"""
        class ExceptionChannel(ConcreteTestChannel):
            async def process_data(self, data: Any) -> ProcessingResult:
                raise ValueError("Processing exception")
        
        channel = ExceptionChannel()
        await channel.start()
        
        result = await channel.process_with_metrics({"test": "data"})
        
        assert not result.success
        assert len(result.errors) == 1
        assert "Processing exception" in result.errors[0]
        assert result.metadata.get("exception") == "Processing exception"

    @pytest.mark.asyncio
    async def test_inactive_channel_processing(self, channel):
        """Test that inactive channels reject processing"""
        # Don't start the channel
        success = await channel.submit_data({"test": "data"})
        
        assert not success
        assert channel.metrics.processed_count == 0


class TestCircuitBreakerPattern:
    """Test circuit breaker functionality"""

    @pytest.fixture
    def channel(self):
        config = MockChannelConfig()
        config.circuit_breaker_threshold = 3
        config.circuit_breaker_timeout = 1.0
        return ConcreteTestChannel(config=config)

    @pytest.fixture
    async def active_channel(self, channel):
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self, active_channel):
        """Test circuit breaker opens after consecutive errors"""
        active_channel.processing_should_fail = True
        
        # Trigger failures to open circuit breaker
        for _ in range(3):
            await active_channel.process_with_metrics({"test": "data"})
        
        assert active_channel.is_circuit_open
        assert active_channel._consecutive_errors == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_processing(self, active_channel):
        """Test circuit breaker rejects processing when open"""
        # Force circuit breaker open
        active_channel._circuit_open = True
        
        result = await active_channel.process_with_metrics({"test": "data"})
        
        assert not result.success
        assert "Circuit breaker is open" in result.errors[0]
        assert result.metadata.get("circuit_breaker") is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_auto_closes(self, active_channel):
        """Test circuit breaker auto-closes after timeout"""
        # Open circuit breaker
        active_channel._circuit_open = True
        active_channel._circuit_open_time = time.time() - 2.0  # 2 seconds ago
        
        # Check if circuit breaker closes automatically
        is_open_before = active_channel.is_circuit_open
        is_open_after = active_channel.is_circuit_open
        
        assert not is_open_after  # Should be closed now

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self, active_channel):
        """Test circuit breaker resets after successful processing"""
        # Accumulate some errors
        active_channel.processing_should_fail = True
        await active_channel.process_with_metrics({"test": "data"})
        assert active_channel._consecutive_errors == 1
        
        # Successful processing should reset
        active_channel.processing_should_fail = False
        await active_channel.process_with_metrics({"test": "data"})
        
        assert active_channel._consecutive_errors == 0


class TestBatchProcessing:
    """Test batch processing functionality"""

    @pytest.fixture
    def batch_channel(self):
        config = MockChannelConfig()
        config.batching.strategy = BatchingStrategy.SIZE_BASED
        config.batching.max_batch_size = 3
        config.batching.max_wait_time_ms = 100
        return ConcreteTestChannel(config=config)

    @pytest.fixture
    async def active_batch_channel(self, batch_channel):
        await batch_channel.start()
        return batch_channel

    @pytest.mark.asyncio
    async def test_size_based_batching(self, active_batch_channel):
        """Test size-based batch processing"""
        # Submit data that should trigger batch processing
        for i in range(3):
            success = await active_batch_channel.submit_data(f"data_{i}")
            assert success
        
        # Wait for batch processing
        await asyncio.sleep(0.1)
        
        # Check that data was processed
        assert len(active_batch_channel.process_data_calls) >= 3
        assert active_batch_channel.metrics.batches_processed > 0

    @pytest.mark.asyncio
    async def test_time_based_batching(self, active_batch_channel):
        """Test time-based batch processing"""
        # Submit single item and wait for timeout
        await active_batch_channel.submit_data("single_item")
        
        # Wait for timeout-based processing
        await asyncio.sleep(0.2)
        
        # Check that item was processed despite not reaching batch size
        assert "single_item" in active_batch_channel.process_data_calls

    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self, active_batch_channel):
        """Test handling of queue overflow"""
        # Fill the queue beyond capacity
        config = active_batch_channel.config
        for i in range(config.max_queue_size + 5):
            await active_batch_channel.submit_data(f"overflow_data_{i}")
        
        # Check metrics for queue overflow
        await asyncio.sleep(0.1)
        assert active_batch_channel.metrics.queue_overflows > 0

    @pytest.mark.asyncio
    async def test_drain_queues_on_shutdown(self, active_batch_channel):
        """Test that queues are drained during shutdown"""
        # Add items to queue
        for i in range(5):
            await active_batch_channel.submit_data(f"drain_test_{i}")
        
        # Shutdown should drain queues
        await active_batch_channel.stop()
        
        # Check that items were processed
        assert len(active_batch_channel.process_data_calls) >= 5


class TestChannelMetrics:
    """Test metrics tracking functionality"""

    @pytest.fixture
    async def active_channel(self):
        channel = ConcreteTestChannel()
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, active_channel):
        """Test comprehensive metrics tracking"""
        initial_count = active_channel.metrics.processed_count
        
        # Process some data
        await active_channel.process_with_metrics({"test": "data1"})
        await active_channel.process_with_metrics({"test": "data2"})
        
        metrics = active_channel.metrics
        assert metrics.processed_count == initial_count + 2
        assert metrics.avg_processing_time_ms > 0
        assert metrics.events_generated == 2

    @pytest.mark.asyncio
    async def test_error_metrics_tracking(self, active_channel):
        """Test error metrics tracking"""
        active_channel.processing_should_fail = True
        
        await active_channel.process_with_metrics({"test": "data"})
        
        assert active_channel.metrics.error_count == 1
        assert active_channel.metrics.processed_count == 1

    @pytest.mark.asyncio
    async def test_processing_time_metrics(self, active_channel):
        """Test processing time metrics calculation"""
        # Process data and check timing metrics
        result = await active_channel.process_with_metrics({"test": "data"})
        
        assert result.processing_time_ms > 0
        assert active_channel.metrics.avg_processing_time_ms > 0


class TestChannelHealthMonitoring:
    """Test health monitoring functionality"""

    @pytest.fixture
    async def active_channel(self):
        channel = ConcreteTestChannel()
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_healthy_channel_status(self, active_channel):
        """Test healthy channel reports correct status"""
        # Process successful data
        await active_channel.process_with_metrics({"test": "data"})
        
        assert active_channel.is_healthy()
        
        health_status = active_channel.get_health_status()
        assert health_status.is_healthy
        assert health_status.status == ChannelStatus.ACTIVE
        assert health_status.error_rate < 0.1

    @pytest.mark.asyncio
    async def test_unhealthy_channel_high_error_rate(self, active_channel):
        """Test channel reports unhealthy with high error rate"""
        # Generate high error rate
        active_channel.processing_should_fail = True
        for _ in range(10):
            await active_channel.process_with_metrics({"test": "data"})
        
        assert not active_channel.is_healthy()
        
        health_status = active_channel.get_health_status()
        assert not health_status.is_healthy
        assert health_status.error_rate > 0.5

    @pytest.mark.asyncio
    async def test_unhealthy_channel_circuit_breaker(self, active_channel):
        """Test channel reports unhealthy when circuit breaker is open"""
        # Force circuit breaker open
        active_channel._circuit_open = True
        
        assert not active_channel.is_healthy()
        
        health_status = active_channel.get_health_status()
        assert not health_status.is_healthy
        assert health_status.circuit_breaker_open


class TestChannelConfiguration:
    """Test channel configuration functionality"""

    def test_channel_configuration_dict(self):
        """Test channel configuration export"""
        config = MockChannelConfig()
        channel = ConcreteTestChannel("test_config", config)
        
        config_dict = channel.get_configuration()
        
        assert config_dict['name'] == 'test_config'
        assert config_dict['type'] == 'tick'
        assert config_dict['status'] == 'initializing'
        assert 'channel_id' in config_dict

    def test_channel_string_representation(self):
        """Test channel string representations"""
        channel = ConcreteTestChannel("test_repr")
        
        str_repr = str(channel)
        assert "TICKChannel[test_repr:" in str_repr
        
        repr_str = repr(channel)
        assert "ConcreteTestChannel(name='test_repr'" in repr_str
        assert "status=initializing" in repr_str


class TestChannelPerformance:
    """Test channel performance characteristics"""

    @pytest.fixture
    async def active_channel(self):
        channel = ConcreteTestChannel()
        await channel.start()
        return channel

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, active_channel):
        """Test concurrent processing capabilities"""
        # Submit multiple concurrent processing tasks
        tasks = []
        for i in range(10):
            task = active_channel.process_with_metrics(f"concurrent_data_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(result.success for result in results)
        assert active_channel.metrics.processed_count == 10

    @pytest.mark.asyncio
    async def test_processing_performance(self, active_channel, performance_timer):
        """Test processing performance meets requirements"""
        performance_timer.start()
        
        # Process batch of data
        for i in range(100):
            await active_channel.process_with_metrics(f"perf_data_{i}")
        
        performance_timer.stop()
        
        # Should complete within reasonable time (< 2 seconds for 100 items)
        assert performance_timer.elapsed < 2.0
        assert active_channel.metrics.avg_processing_time_ms < 100

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, active_channel):
        """Test memory efficiency during processing"""
        import gc
        import sys
        
        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Process significant amount of data
        for i in range(1000):
            await active_channel.process_with_metrics(f"memory_test_{i}")
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable (< 50% increase)
        memory_growth = (final_objects - initial_objects) / initial_objects
        assert memory_growth < 0.5, f"Memory growth too high: {memory_growth:.2%}"


# Integration test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.channels
]