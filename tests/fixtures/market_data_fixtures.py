"""
Test fixtures for market data and system components.

Provides reusable test data and mock objects for testing the multi-channel
system integration and other market data processing components.
"""

import time
from typing import Any
from unittest.mock import Mock

# Core domain imports
from src.core.domain.market.tick import TickData
from src.shared.models.data_types import FMVData, OHLCVData


def create_tick_data(ticker: str, price: float, volume: int,
                    timestamp: float | None = None) -> TickData:
    """
    Create a TickData object for testing.
    
    Args:
        ticker: Stock ticker symbol
        price: Stock price
        volume: Trade volume
        timestamp: Optional timestamp (defaults to current time)
        
    Returns:
        TickData: Configured tick data object
    """
    if timestamp is None:
        timestamp = time.time()

    return TickData(
        ticker=ticker,
        price=price,
        volume=volume,
        timestamp=timestamp,
        # Add other typical tick data fields
        bid=price - 0.01,
        ask=price + 0.01,
        last_size=volume,
        sequence=1,
        exchange="TEST"
    )


def create_ohlcv_data(ticker: str, open_price: float, high: float,
                     low: float, close: float, volume: int,
                     timestamp: float | None = None) -> OHLCVData:
    """
    Create an OHLCVData object for testing.
    
    Args:
        ticker: Stock ticker symbol
        open_price: Opening price
        high: High price
        low: Low price
        close: Closing price
        volume: Volume
        timestamp: Optional timestamp (defaults to current time)
        
    Returns:
        OHLCVData: Configured OHLCV data object
    """
    if timestamp is None:
        timestamp = time.time()

    return OHLCVData(
        ticker=ticker,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=timestamp,
        # Add typical OHLCV fields
        vwap=(high + low + close) / 3,
        timeframe="1m",
        source="test"
    )


def create_fmv_data(ticker: str, fair_value: float, confidence: float,
                   timestamp: float | None = None) -> FMVData:
    """
    Create an FMVData object for testing.
    
    Args:
        ticker: Stock ticker symbol
        fair_value: Fair market value
        confidence: Confidence score (0.0 to 1.0)
        timestamp: Optional timestamp (defaults to current time)
        
    Returns:
        FMVData: Configured FMV data object
    """
    if timestamp is None:
        timestamp = time.time()

    return FMVData(
        ticker=ticker,
        fair_market_value=fair_value,
        confidence=confidence,
        timestamp=timestamp,
        # Add typical FMV fields
        method="test_valuation",
        source="test_provider",
        currency="USD"
    )


def create_mock_market_service(include_websocket: bool = True,
                              include_event_processor: bool = True,
                              include_priority_manager: bool = True) -> Mock:
    """
    Create a mock MarketDataService for testing.
    
    Args:
        include_websocket: Whether to include WebSocket publisher
        include_event_processor: Whether to include event processor
        include_priority_manager: Whether to include priority manager
        
    Returns:
        Mock: Configured mock market service
    """
    mock_service = Mock()

    # Mock event processor
    if include_event_processor:
        event_processor = Mock()
        event_processor.handle_multi_source_data = Mock(
            return_value=Mock(success=True, events_processed=1, errors=[])
        )
        event_processor.set_channel_router = Mock()
        mock_service.event_processor = event_processor
    else:
        mock_service.event_processor = None

    # Mock WebSocket publisher
    if include_websocket:
        websocket_publisher = Mock()
        websocket_mgr = Mock()
        websocket_mgr.get_active_connections = Mock(return_value=[Mock(), Mock()])

        websocket_publisher.websocket_mgr = websocket_mgr
        websocket_publisher.market_service = mock_service

        mock_service.websocket_publisher = websocket_publisher
        mock_service.websocket_mgr = websocket_mgr
    else:
        mock_service.websocket_publisher = None
        mock_service.websocket_mgr = None

    # Mock priority manager
    if include_priority_manager:
        priority_manager = Mock()
        priority_manager.add_event = Mock()
        mock_service.priority_manager = priority_manager
    else:
        mock_service.priority_manager = None

    # Mock other common components
    mock_service.config = create_test_config()
    mock_service.cache_control = Mock()
    mock_service.market_metrics = Mock()

    return mock_service


def create_test_config() -> dict[str, Any]:
    """
    Create a test configuration dictionary.
    
    Returns:
        Dict: Test configuration with common settings
    """
    return {
        # Channel configuration
        'ENABLE_TICK_CHANNEL': True,
        'ENABLE_OHLCV_CHANNEL': True,
        'ENABLE_FMV_CHANNEL': True,

        # Performance settings
        'ROUTING_TIMEOUT_MS': 50.0,
        'MAX_QUEUE_SIZE': 1000,
        'WORKER_POOL_SIZE': 4,

        # Monitoring settings
        'ENABLE_MONITORING': True,
        'HEALTH_CHECK_INTERVAL': 10.0,
        'METRICS_COLLECTION_INTERVAL': 5.0,

        # Integration settings
        'ENABLE_WEBSOCKET_INTEGRATION': True,
        'ENABLE_PRIORITY_MANAGER_INTEGRATION': True,
        'ENABLE_ANALYTICS_INTEGRATION': True,

        # Performance targets
        'TARGET_OHLCV_SYMBOLS': 8000,
        'TARGET_LATENCY_P99_MS': 50.0,
        'TARGET_MEMORY_LIMIT_GB': 2.0,

        # Data source settings
        'USE_SYNTHETIC_DATA': True,
        'USE_MASSIVE_API': False,
        'DATA_SOURCE': 'synthetic',

        # Market settings
        'MARKET_TIMEZONE': 'US/Eastern',

        # WebSocket settings
        'WEBSOCKET_PORT': 5000,
        'HEARTBEAT_INTERVAL': 2.0,
        'MAX_CONNECTIONS': 100,

        # Event detection thresholds
        'SURGE_MULTIPLIER': 3.0,
        'HIGH_LOW_THRESHOLD': 0.1,
        'TREND_WINDOWS': [180, 360, 600],

        # Sprint 108 specific settings
        'COLLECTION_INTERVAL': 0.5,
        'EMISSION_INTERVAL': 1.0,
        'MAX_BUFFER_SIZE': 1000
    }


def create_mock_channel(channel_name: str, channel_type: str,
                       is_healthy: bool = True) -> Mock:
    """
    Create a mock processing channel for testing.
    
    Args:
        channel_name: Name of the channel
        channel_type: Type of channel (tick, ohlcv, fmv)
        is_healthy: Whether the channel should report as healthy
        
    Returns:
        Mock: Configured mock channel
    """
    mock_channel = Mock()

    # Basic channel properties
    mock_channel.name = channel_name
    mock_channel.channel_id = f"{channel_name}_id"

    # Channel type enum
    from src.processing.channels.base_channel import ChannelType
    if channel_type == "tick":
        mock_channel.channel_type = ChannelType.TICK
    elif channel_type == "ohlcv":
        mock_channel.channel_type = ChannelType.OHLCV
    elif channel_type == "fmv":
        mock_channel.channel_type = ChannelType.FMV
    else:
        mock_channel.channel_type = Mock()
        mock_channel.channel_type.value = channel_type

    # Health and status
    mock_channel.is_healthy = Mock(return_value=is_healthy)

    from src.processing.channels.base_channel import ChannelStatus
    mock_channel.status = ChannelStatus.RUNNING if is_healthy else ChannelStatus.ERROR

    # Processing methods
    async def mock_submit_data(data):
        """Mock data submission that returns success"""
        return True

    mock_channel.submit_data = mock_submit_data

    # Async lifecycle methods
    async def mock_start():
        pass

    async def mock_stop():
        pass

    mock_channel.start = mock_start
    mock_channel.stop = mock_stop

    # Mock metrics
    mock_metrics = Mock()
    mock_metrics.processed_count = 0
    mock_metrics.error_count = 0
    mock_metrics.avg_processing_time_ms = 10.0
    mock_channel.metrics = mock_metrics

    # Mock queue
    mock_queue = Mock()
    mock_queue.qsize = Mock(return_value=0)
    mock_channel.processing_queue = mock_queue

    # Mock configuration
    mock_config = Mock()
    mock_config.max_queue_size = 1000
    mock_channel.config = mock_config

    return mock_channel


def create_mock_event_processor_result(success: bool = True,
                                      events_processed: int = 1,
                                      errors: list | None = None) -> Mock:
    """
    Create a mock EventProcessingResult for testing.
    
    Args:
        success: Whether the processing was successful
        events_processed: Number of events processed
        errors: List of error messages
        
    Returns:
        Mock: Configured mock result object
    """
    result = Mock()
    result.success = success
    result.events_processed = events_processed
    result.errors = errors or []
    result.warnings = []
    result.ticker = "TEST"
    result.processing_time_ms = 10.0

    return result


def create_mock_router_result(success: bool = True,
                             metadata: dict | None = None) -> Mock:
    """
    Create a mock routing result for testing.
    
    Args:
        success: Whether the routing was successful
        metadata: Optional metadata dictionary
        
    Returns:
        Mock: Configured mock routing result
    """
    from src.processing.channels.base_channel import ProcessingResult

    result = Mock(spec=ProcessingResult)
    result.success = success
    result.metadata = metadata or {}
    result.events = []
    result.errors = [] if success else ["Routing failed"]
    result.processing_time_ms = 5.0

    return result


def create_test_market_data_batch(count: int = 100) -> dict[str, list]:
    """
    Create a batch of test market data for load testing.
    
    Args:
        count: Number of data items to create for each type
        
    Returns:
        Dict: Dictionary containing lists of tick, OHLCV, and FMV data
    """
    current_time = time.time()

    tick_data = []
    ohlcv_data = []
    fmv_data = []

    for i in range(count):
        # Create tick data
        tick_data.append(create_tick_data(
            ticker=f"TICK{i:03d}",
            price=100.0 + (i % 50),
            volume=1000 + (i * 10),
            timestamp=current_time + i
        ))

        # Create OHLCV data
        base_price = 100.0 + (i % 50)
        ohlcv_data.append(create_ohlcv_data(
            ticker=f"OHLCV{i:03d}",
            open_price=base_price,
            high=base_price + 2.0,
            low=base_price - 1.5,
            close=base_price + 1.0,
            volume=10000 + (i * 100),
            timestamp=current_time + i
        ))

        # Create FMV data
        fmv_data.append(create_fmv_data(
            ticker=f"FMV{i:03d}",
            fair_value=base_price + 0.5,
            confidence=0.8 + (i % 20) * 0.01,
            timestamp=current_time + i
        ))

    return {
        'tick_data': tick_data,
        'ohlcv_data': ohlcv_data,
        'fmv_data': fmv_data
    }


def create_mock_alert_handler() -> Mock:
    """
    Create a mock alert handler for monitoring tests.
    
    Returns:
        Mock: Configured mock alert handler
    """
    handler = Mock()
    handler.alerts_received = []

    def record_alert(alert):
        handler.alerts_received.append(alert)

    handler.side_effect = record_alert
    return handler


def create_performance_test_data() -> dict[str, Any]:
    """
    Create test data specifically for performance testing.
    
    Returns:
        Dict: Performance test configuration and data
    """
    return {
        'latency_targets': {
            'tick_p99_ms': 50.0,
            'ohlcv_p99_ms': 100.0,
            'fmv_p99_ms': 75.0
        },
        'throughput_targets': {
            'tick_per_second': 1000,
            'ohlcv_per_second': 500,
            'fmv_per_second': 100
        },
        'load_test_config': {
            'duration_seconds': 10.0,
            'symbol_count': 100,
            'concurrent_streams': 3
        },
        'memory_limits': {
            'max_increase_mb': 100.0,
            'max_total_gb': 2.0
        }
    }


# Convenience function for creating complete test scenarios
def create_integration_test_scenario(scenario_name: str) -> dict[str, Any]:
    """
    Create a complete integration test scenario with all necessary components.
    
    Args:
        scenario_name: Name of the test scenario
        
    Returns:
        Dict: Complete test scenario configuration
    """
    scenarios = {
        'basic_integration': {
            'market_service': create_mock_market_service(),
            'config': create_test_config(),
            'test_data': create_test_market_data_batch(10),
            'expected_results': {
                'success_rate': 100.0,
                'max_latency_ms': 100.0,
                'channels_healthy': True
            }
        },
        'high_load': {
            'market_service': create_mock_market_service(),
            'config': {**create_test_config(), 'TARGET_OHLCV_SYMBOLS': 1000},
            'test_data': create_test_market_data_batch(1000),
            'expected_results': {
                'success_rate': 95.0,
                'max_latency_ms': 200.0,
                'memory_increase_mb': 50.0
            }
        },
        'error_recovery': {
            'market_service': create_mock_market_service(),
            'config': create_test_config(),
            'test_data': create_test_market_data_batch(50),
            'error_injection': True,
            'expected_results': {
                'recovery_time_ms': 1000.0,
                'final_success_rate': 90.0
            }
        },
        'monitoring_validation': {
            'market_service': create_mock_market_service(),
            'config': {**create_test_config(), 'ENABLE_MONITORING': True},
            'test_data': create_test_market_data_batch(20),
            'monitoring_enabled': True,
            'expected_results': {
                'alerts_generated': True,
                'metrics_collected': True,
                'health_checks_passed': True
            }
        }
    }

    return scenarios.get(scenario_name, scenarios['basic_integration'])
