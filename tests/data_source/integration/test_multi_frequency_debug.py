"""
Focused debug test for multi-frequency data generation issues.

This test directly tests the multi-frequency generation logic without 
circular import issues to identify why data isn't reaching the frontend.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.infrastructure.data_sources.synthetic.types import DataFrequency
from src.core.domain.market.tick import TickData


class TestMultiFrequencyDebug:
    """Debug tests for multi-frequency data generation."""

    @pytest.fixture
    def mock_config(self):
        """Configuration matching user's .env settings."""
        return {
            'USE_SYNTHETIC_DATA': True,
            'ENABLE_MULTI_FREQUENCY': True,
            'WEBSOCKET_PER_SECOND_ENABLED': False,
            'WEBSOCKET_PER_MINUTE_ENABLED': True, 
            'WEBSOCKET_FAIR_VALUE_ENABLED': True,
            'ENABLE_PER_SECOND_EVENTS': False,
            'ENABLE_PER_MINUTE_EVENTS': True,
            'ENABLE_FMV_EVENTS': False,
            'SYNTHETIC_MINUTE_WINDOW': 60,
            'SYNTHETIC_FMV_UPDATE_INTERVAL': 15,
        }

    @pytest.fixture
    def mock_data_provider(self):
        """Mock data provider that returns realistic data."""
        provider = Mock()
        
        def mock_generate_frequency_data(ticker: str, frequency: DataFrequency):
            if frequency == DataFrequency.PER_MINUTE:
                return {
                    'c': 150.25,  # close price
                    'v': 5000,    # volume
                    'h': 151.0,   # high
                    'l': 149.5,   # low
                    'o': 150.0,   # open
                    'timestamp': time.time()
                }
            elif frequency == DataFrequency.FAIR_VALUE:
                return {
                    'fmv': 150.15,
                    'confidence': 0.85,
                    'timestamp': time.time()
                }
            return None
            
        provider.generate_frequency_data.side_effect = mock_generate_frequency_data
        return provider

    @pytest.fixture 
    def tick_callback_capture(self):
        """Capture all tick callbacks for analysis."""
        captured_ticks = []
        callback_count = {'count': 0}
        
        def capture_tick(tick_data: TickData):
            callback_count['count'] += 1
            captured_ticks.append({
                'ticker': tick_data.ticker,
                'price': tick_data.price,
                'volume': tick_data.volume,
                'source': tick_data.source,
                'event_type': tick_data.event_type,
                'timestamp': tick_data.timestamp
            })
            print(f"[DEBUG] Captured tick #{callback_count['count']}: {tick_data.ticker} @ ${tick_data.price}")
        
        return capture_tick, captured_ticks, callback_count

    def test_data_provider_factory_direct(self, mock_config):
        """Test DataProviderFactory directly to see if it works."""
        # Import inside test to avoid circular imports
        from src.infrastructure.data_sources.factory import DataProviderFactory
        
        try:
            provider = DataProviderFactory.get_provider(mock_config)
            assert provider is not None, "DataProviderFactory should return a provider"
            print(f"[DEBUG] DataProviderFactory returned: {type(provider)}")
            
            # Test data generation directly
            per_minute_data = provider.generate_frequency_data('AAPL', DataFrequency.PER_MINUTE)
            print(f"[DEBUG] Per-minute data for AAPL: {per_minute_data}")
            assert per_minute_data is not None, "Should generate per-minute data"
            
            fmv_data = provider.generate_frequency_data('AAPL', DataFrequency.FAIR_VALUE)
            print(f"[DEBUG] FMV data for AAPL: {fmv_data}")
            
        except Exception as e:
            print(f"[ERROR] DataProviderFactory failed: {e}")
            raise

    def test_multi_frequency_logic_isolated(self, mock_config, mock_data_provider, tick_callback_capture):
        """Test the multi-frequency generation logic in isolation."""
        tick_callback, captured_ticks, callback_count = tick_callback_capture
        
        # Simulate the _simulate_multi_frequency_events method logic
        universe = ['AAPL', 'GOOGL', 'MSFT']
        per_minute_interval = mock_config.get('SYNTHETIC_MINUTE_WINDOW', 60)
        fmv_interval = mock_config.get('SYNTHETIC_FMV_UPDATE_INTERVAL', 30)
        
        print(f"[DEBUG] Testing with intervals: per_minute={per_minute_interval}s, fmv={fmv_interval}s")
        
        current_time = time.time()
        
        # Test per-minute data generation
        if mock_config.get('WEBSOCKET_PER_MINUTE_ENABLED', False):
            print("[DEBUG] Per-minute generation enabled, generating data...")
            for ticker in universe[:3]:  # Test with 3 tickers
                try:
                    print(f"[DEBUG] Calling generate_frequency_data for {ticker}")
                    minute_data = mock_data_provider.generate_frequency_data(ticker, DataFrequency.PER_MINUTE)
                    print(f"[DEBUG] Got minute_data for {ticker}: {minute_data}")
                    
                    if minute_data:
                        # Convert to TickData (same logic as adapter)
                        tick_data = TickData(
                            ticker=ticker,
                            price=minute_data.get('c', 150.0),
                            volume=minute_data.get('v', 1000),
                            timestamp=current_time,
                            source='multi_frequency_per_minute',
                            event_type='AM'
                        )
                        print(f"[DEBUG] Created TickData: {tick_data}")
                        print(f"[DEBUG] Calling tick_callback...")
                        tick_callback(tick_data)
                        print(f"[DEBUG] tick_callback completed for {ticker}")
                    else:
                        print(f"[ERROR] No minute_data returned for {ticker}")
                except Exception as e:
                    print(f"[ERROR] Error generating per-minute data for {ticker}: {e}")
                    raise
        
        # Verify results
        print(f"[DEBUG] Total callbacks made: {callback_count['count']}")
        print(f"[DEBUG] Total ticks captured: {len(captured_ticks)}")
        
        assert callback_count['count'] > 0, "Should have made tick callbacks"
        assert len(captured_ticks) > 0, "Should have captured tick data"
        
        # Verify data structure
        first_tick = captured_ticks[0]
        print(f"[DEBUG] First captured tick: {first_tick}")
        
        assert first_tick['ticker'] in universe
        assert first_tick['price'] == 150.25  # From mock data
        assert first_tick['source'] == 'multi_frequency_per_minute'
        assert first_tick['event_type'] == 'AM'

    def test_adapter_connect_method_direct(self, mock_config, mock_data_provider, tick_callback_capture):
        """Test SyntheticDataAdapter connect method directly."""
        # Import inside test to avoid circular imports at module level
        from src.infrastructure.data_sources.adapters.realtime_adapter import SyntheticDataAdapter
        
        tick_callback, captured_ticks, callback_count = tick_callback_capture
        
        # Create adapter
        adapter = SyntheticDataAdapter(mock_config, tick_callback, Mock())
        
        # Patch the factory to return our mock provider
        with patch('src.infrastructure.data_sources.adapters.realtime_adapter.DataProviderFactory') as mock_factory:
            mock_factory.get_provider.return_value = mock_data_provider
            
            print("[DEBUG] Calling adapter.connect(['AAPL'])...")
            success = adapter.connect(['AAPL'])
            print(f"[DEBUG] Adapter connect returned: {success}")
            
            assert success, "Adapter should connect successfully"
            assert adapter.connected, "Adapter should be connected"
            
            # Wait for background thread to generate data
            print("[DEBUG] Waiting for background data generation...")
            time.sleep(3)
            
            print(f"[DEBUG] After 3 seconds - callbacks: {callback_count['count']}, captured: {len(captured_ticks)}")
            
            # Verify data provider was called
            call_count = mock_data_provider.generate_frequency_data.call_count
            print(f"[DEBUG] Data provider called {call_count} times")
            assert call_count > 0, "Data provider should have been called"
            
            # Verify tick callbacks were made
            assert callback_count['count'] > 0, "Should have made tick callbacks"
            
        # Clean up
        adapter.disconnect()
        print("[DEBUG] Adapter disconnected")

    def test_configuration_validation(self, mock_config):
        """Test that our configuration matches what the adapter expects."""
        print("[DEBUG] Configuration validation:")
        print(f"  ENABLE_MULTI_FREQUENCY: {mock_config.get('ENABLE_MULTI_FREQUENCY')}")
        print(f"  WEBSOCKET_PER_MINUTE_ENABLED: {mock_config.get('WEBSOCKET_PER_MINUTE_ENABLED')}")
        print(f"  WEBSOCKET_FAIR_VALUE_ENABLED: {mock_config.get('WEBSOCKET_FAIR_VALUE_ENABLED')}")
        print(f"  SYNTHETIC_MINUTE_WINDOW: {mock_config.get('SYNTHETIC_MINUTE_WINDOW')}")
        print(f"  SYNTHETIC_FMV_UPDATE_INTERVAL: {mock_config.get('SYNTHETIC_FMV_UPDATE_INTERVAL')}")
        
        # These should match user's .env settings
        assert mock_config.get('ENABLE_MULTI_FREQUENCY') == True
        assert mock_config.get('WEBSOCKET_PER_MINUTE_ENABLED') == True
        assert mock_config.get('WEBSOCKET_FAIR_VALUE_ENABLED') == True
        
        print("[DEBUG] Configuration validation passed")