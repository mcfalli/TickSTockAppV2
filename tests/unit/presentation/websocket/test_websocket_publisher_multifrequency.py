"""
Unit tests for multi-frequency WebSocketPublisher functionality - Sprint 101
Tests WebSocketPublisher enhancements for multi-frequency event processing.
"""

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
from src.presentation.websocket.publisher import WebSocketPublisher
from src.shared.types.frequency import FrequencyType


class TestWebSocketPublisherMultiFrequency:
    """Test WebSocketPublisher multi-frequency functionality"""
    
    @pytest.fixture
    def mock_websocket_mgr(self):
        """Create mock WebSocket manager"""
        mgr = Mock()
        mgr.emit_to_user = Mock(return_value=True)
        mgr.emit_to_all = Mock(return_value=True)
        return mgr
    
    @pytest.fixture
    def mock_cache_control(self):
        """Create mock cache control"""
        cache = Mock()
        cache.get_universe_definitions = Mock(return_value={})
        return cache
    
    @pytest.fixture
    def publisher(self, mock_websocket_mgr, multi_frequency_config, mock_cache_control):
        """Create WebSocketPublisher with multi-frequency support"""
        with patch('src.presentation.websocket.publisher.UserFiltersService'), \
             patch('src.presentation.websocket.publisher.UserSettingsService'), \
             patch('src.presentation.websocket.publisher.WebSocketFilterCache'), \
             patch('src.presentation.websocket.publisher.WebSocketDataFilter'), \
             patch('src.presentation.websocket.publisher.WebSocketAnalytics'), \
             patch('src.presentation.websocket.publisher.WebSocketDisplayConverter'), \
             patch('src.presentation.websocket.publisher.WebSocketUniverseCache'), \
             patch('src.presentation.websocket.publisher.WebSocketStatistics'):
            
            publisher = WebSocketPublisher(
                mock_websocket_mgr,
                multi_frequency_config,
                mock_cache_control
            )
            return publisher
    
    def test_frequency_initialization(self, publisher, multi_frequency_config):
        """Test that frequency support is initialized correctly"""
        # Check default enabled frequencies
        assert FrequencyType.PER_SECOND in publisher.enabled_frequencies
        
        # Check configuration-based frequencies
        if multi_frequency_config.get('ENABLE_PER_MINUTE_EVENTS'):
            assert FrequencyType.PER_MINUTE in publisher.enabled_frequencies
        
        if multi_frequency_config.get('ENABLE_FMV_EVENTS'):
            assert FrequencyType.FAIR_MARKET_VALUE in publisher.enabled_frequencies
        
        # Check frequency emission config
        assert publisher.frequency_emission_config[FrequencyType.PER_SECOND.value]['enabled'] is True
        assert publisher.frequency_emission_config[FrequencyType.PER_SECOND.value]['default_enabled'] is True
    
    def test_enable_frequency(self, publisher):
        """Test enabling frequency types at runtime"""
        # Initially disable per-minute frequency
        publisher.enabled_frequencies.discard(FrequencyType.PER_MINUTE)
        publisher.frequency_emission_config[FrequencyType.PER_MINUTE.value]['enabled'] = False
        
        # Enable per-minute frequency
        publisher.enable_frequency(FrequencyType.PER_MINUTE)
        
        # Verify it's enabled
        assert FrequencyType.PER_MINUTE in publisher.enabled_frequencies
        assert publisher.frequency_emission_config[FrequencyType.PER_MINUTE.value]['enabled'] is True
    
    def test_disable_frequency(self, publisher):
        """Test disabling frequency types at runtime"""
        # Enable FMV frequency first
        publisher.enabled_frequencies.add(FrequencyType.FAIR_MARKET_VALUE)
        
        # Disable FMV frequency
        publisher.disable_frequency(FrequencyType.FAIR_MARKET_VALUE)
        
        # Verify it's disabled
        assert FrequencyType.FAIR_MARKET_VALUE not in publisher.enabled_frequencies
        assert publisher.frequency_emission_config[FrequencyType.FAIR_MARKET_VALUE.value]['enabled'] is False
    
    def test_cannot_disable_per_second_frequency(self, publisher):
        """Test that PER_SECOND frequency cannot be disabled"""
        # Attempt to disable per-second frequency
        publisher.disable_frequency(FrequencyType.PER_SECOND)
        
        # Should still be enabled
        assert FrequencyType.PER_SECOND in publisher.enabled_frequencies
        assert publisher.frequency_emission_config[FrequencyType.PER_SECOND.value]['enabled'] is True
    
    def test_get_enabled_frequencies(self, publisher):
        """Test getting currently enabled frequencies"""
        enabled = publisher.get_enabled_frequencies()
        
        # Should return a copy, not the original
        assert enabled is not publisher.enabled_frequencies
        assert FrequencyType.PER_SECOND in enabled
    
    def test_is_frequency_enabled(self, publisher):
        """Test checking if specific frequency is enabled"""
        # PER_SECOND should always be enabled
        assert publisher.is_frequency_enabled(FrequencyType.PER_SECOND) is True
        
        # Add PER_MINUTE and test
        publisher.enabled_frequencies.add(FrequencyType.PER_MINUTE)
        assert publisher.is_frequency_enabled(FrequencyType.PER_MINUTE) is True
        
        # Remove and test
        publisher.enabled_frequencies.discard(FrequencyType.PER_MINUTE)
        assert publisher.is_frequency_enabled(FrequencyType.PER_MINUTE) is False
    
    def test_get_user_frequency_preferences(self, publisher):
        """Test retrieving user frequency preferences"""
        user_id = 123
        
        # Mock user settings service
        mock_settings = {
            'enable_per_second_events': True,
            'enable_per_minute_events': True,
            'enable_fmv_events': False
        }
        
        with patch.object(publisher, 'user_settings_service') as mock_service:
            mock_service.get_user_settings.return_value = mock_settings
            
            preferences = publisher._get_user_frequency_preferences(user_id)
            
            assert preferences[FrequencyType.PER_SECOND.value] is True
            assert preferences[FrequencyType.PER_MINUTE.value] is True
            assert preferences[FrequencyType.FAIR_MARKET_VALUE.value] is False
    
    def test_get_user_frequency_preferences_fallback(self, publisher):
        """Test frequency preferences fallback to defaults"""
        user_id = 123
        
        # Mock service returning None
        with patch.object(publisher, 'user_settings_service') as mock_service:
            mock_service.get_user_settings.return_value = None
            
            preferences = publisher._get_user_frequency_preferences(user_id)
            
            # Should return defaults from config
            assert preferences[FrequencyType.PER_SECOND.value] is True
            expected_per_minute = publisher.frequency_emission_config[FrequencyType.PER_MINUTE.value]['default_enabled']
            expected_fmv = publisher.frequency_emission_config[FrequencyType.FAIR_MARKET_VALUE.value]['default_enabled']
            
            assert preferences[FrequencyType.PER_MINUTE.value] is expected_per_minute
            assert preferences[FrequencyType.FAIR_MARKET_VALUE.value] is expected_fmv
    
    def test_filter_per_second_events(self, publisher, event_builder):
        """Test per-second event filtering"""
        user_tickers = {'AAPL', 'GOOGL'}
        
        freq_data = {
            'highs': [
                event_builder.high_low_event(ticker="AAPL", event_type="high"),
                event_builder.high_low_event(ticker="MSFT", event_type="high"),  # Should be filtered
                event_builder.high_low_event(ticker="GOOGL", event_type="high")
            ],
            'lows': [
                event_builder.high_low_event(ticker="AAPL", event_type="low"),
                event_builder.high_low_event(ticker="TSLA", event_type="low")  # Should be filtered
            ],
            'trending': {
                'up': [event_builder.trend_event(ticker="AAPL", direction="up")],
                'down': [event_builder.trend_event(ticker="NVDA", direction="down")]  # Should be filtered
            },
            'surging': {
                'up': [event_builder.surge_event(ticker="GOOGL")],
                'down': []
            }
        }
        
        filtered = publisher._filter_per_second_events(freq_data, user_tickers)
        
        # Check filtering results
        assert len(filtered['highs']) == 2  # AAPL and GOOGL
        assert len(filtered['lows']) == 1   # Only AAPL
        assert len(filtered['trending']['up']) == 1  # Only AAPL
        assert len(filtered['trending']['down']) == 0  # NVDA filtered out
        assert len(filtered['surging']['up']) == 1  # Only GOOGL
        assert len(filtered['surging']['down']) == 0
    
    def test_filter_per_minute_events(self, publisher, event_builder):
        """Test per-minute event filtering"""
        user_tickers = {'AAPL', 'GOOGL'}
        
        freq_data = {
            'aggregates': [
                event_builder.per_minute_aggregate_event(ticker="AAPL"),
                event_builder.per_minute_aggregate_event(ticker="MSFT"),  # Should be filtered
                event_builder.per_minute_aggregate_event(ticker="GOOGL")
            ],
            'highs': [event_builder.high_low_event(ticker="AAPL", event_type="high")],
            'lows': [event_builder.high_low_event(ticker="TSLA", event_type="low")],  # Should be filtered
            'trending': {'up': [], 'down': []},
            'surging': {'up': [], 'down': []}
        }
        
        filtered = publisher._filter_per_minute_events(freq_data, user_tickers)
        
        # Check aggregate filtering
        assert len(filtered['aggregates']) == 2  # AAPL and GOOGL
        
        # Check that per-second events are also filtered
        assert len(filtered['highs']) == 1  # Only AAPL
        assert len(filtered['lows']) == 0   # TSLA filtered out
    
    def test_filter_fmv_events(self, publisher, event_builder):
        """Test FMV event filtering"""
        user_tickers = {'AAPL', 'GOOGL'}
        
        freq_data = {
            'fmv_events': [
                event_builder.fair_market_value_event(ticker="AAPL"),
                event_builder.fair_market_value_event(ticker="MSFT"),  # Should be filtered
                event_builder.fair_market_value_event(ticker="GOOGL")
            ],
            'valuation_alerts': [
                {'ticker': 'AAPL', 'alert': 'undervalued'},
                {'ticker': 'TSLA', 'alert': 'overvalued'}  # Should be filtered
            ]
        }
        
        filtered = publisher._filter_fmv_events(freq_data, user_tickers)
        
        # Check FMV filtering
        assert len(filtered['fmv_events']) == 2  # AAPL and GOOGL
        assert len(filtered['valuation_alerts']) == 1  # Only AAPL
    
    def test_process_user_data_multifrequency(self, publisher, event_builder):
        """Test multi-frequency user data processing"""
        user_id = 123
        user_tickers = {'AAPL', 'GOOGL'}
        
        # Mock dependencies
        with patch.object(publisher, 'universe_cache') as mock_universe_cache, \
             patch.object(publisher, '_resolve_user_universes_to_tickers') as mock_resolve, \
             patch.object(publisher, '_apply_user_specific_filters') as mock_filters, \
             patch.object(publisher, 'analytics') as mock_analytics:
            
            mock_universe_cache.get_or_load_user_universes.return_value = ['universe1']
            mock_resolve.return_value = user_tickers
            mock_filters.side_effect = lambda user_id, data: data  # Pass through
            mock_analytics.prepare_enhanced_dual_universe_data.return_value = {'processed': True}
            
            # Prepare stock data
            stock_data = {
                'frequencies': {
                    FrequencyType.PER_SECOND.value: {
                        'highs': [event_builder.high_low_event(ticker="AAPL")],
                        'lows': [],
                        'trending': {'up': [], 'down': []},
                        'surging': {'up': [], 'down': []}
                    },
                    FrequencyType.PER_MINUTE.value: {
                        'aggregates': [event_builder.per_minute_aggregate_event(ticker="AAPL")],
                        'highs': [],
                        'lows': [],
                        'trending': {'up': [], 'down': []},
                        'surging': {'up': [], 'down': []}
                    }
                }
            }
            
            user_prefs = {
                FrequencyType.PER_SECOND.value: True,
                FrequencyType.PER_MINUTE.value: True,
                FrequencyType.FAIR_MARKET_VALUE.value: False
            }
            
            result = publisher._process_user_data_multifrequency(
                user_id, stock_data, None, user_prefs
            )
            
            # Verify processing occurred
            mock_universe_cache.get_or_load_user_universes.assert_called_once_with(user_id)
            mock_resolve.assert_called_once()
            mock_analytics.prepare_enhanced_dual_universe_data.assert_called_once()
            assert result == {'processed': True}
    
    def test_apply_user_specific_filters(self, publisher, event_builder):
        """Test application of user-specific filters across frequencies"""
        user_id = 123
        
        # Create filtered data with low events that need filtering
        filtered_data = {
            'lows': [
                {'ticker': 'AAPL', 'count': 1},  # Below threshold
                {'ticker': 'GOOGL', 'count': 3}  # Above threshold
            ],
            'frequencies': {
                FrequencyType.PER_SECOND.value: {
                    'lows': [
                        {'ticker': 'AAPL', 'count': 1},  # Below threshold
                        {'ticker': 'MSFT', 'count': 5}   # Above threshold
                    ]
                }
            }
        }
        
        # Mock user filters
        user_filters = {
            'low_event_filtering': {
                'enabled': True,
                'min_low_count': 2
            }
        }
        
        with patch.object(publisher, 'filter_cache') as mock_cache:
            mock_cache.get_or_load_user_filters.return_value = user_filters
            
            result = publisher._apply_user_specific_filters(user_id, filtered_data)
            
            # Check legacy structure filtering
            assert len(result['lows']) == 1  # Only GOOGL should remain
            assert result['lows'][0]['ticker'] == 'GOOGL'
            
            # Check frequency-specific filtering
            per_second_lows = result['frequencies'][FrequencyType.PER_SECOND.value]['lows']
            assert len(per_second_lows) == 1  # Only MSFT should remain
            assert per_second_lows[0]['ticker'] == 'MSFT'
    
    def test_thread_safety_frequency_management(self, publisher):
        """Test thread safety of frequency enable/disable operations"""
        results = []
        errors = []
        
        def toggle_frequency():
            try:
                for _ in range(100):
                    publisher.enable_frequency(FrequencyType.PER_MINUTE)
                    is_enabled = publisher.is_frequency_enabled(FrequencyType.PER_MINUTE)
                    results.append(is_enabled)
                    
                    publisher.disable_frequency(FrequencyType.PER_MINUTE)
                    is_disabled = not publisher.is_frequency_enabled(FrequencyType.PER_MINUTE)
                    results.append(is_disabled)
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = [threading.Thread(target=toggle_frequency) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # All operations should succeed
        assert all(results), f"Some operations failed: {results.count(False)} out of {len(results)}"
    
    @pytest.mark.performance
    def test_multifrequency_processing_performance(self, publisher, event_builder, performance_timer):
        """Test multi-frequency processing performance"""
        user_id = 123
        
        # Create large dataset
        stock_data = {
            'frequencies': {
                FrequencyType.PER_SECOND.value: {
                    'highs': [event_builder.high_low_event(ticker=f"TICK{i}") for i in range(100)],
                    'lows': [event_builder.high_low_event(ticker=f"TICK{i}", event_type="low") for i in range(100)],
                    'trending': {'up': [], 'down': []},
                    'surging': {'up': [], 'down': []}
                },
                FrequencyType.PER_MINUTE.value: {
                    'aggregates': [event_builder.per_minute_aggregate_event(ticker=f"TICK{i}") for i in range(50)],
                    'highs': [],
                    'lows': [],
                    'trending': {'up': [], 'down': []},
                    'surging': {'up': [], 'down': []}
                }
            }
        }
        
        user_prefs = {
            FrequencyType.PER_SECOND.value: True,
            FrequencyType.PER_MINUTE.value: True,
            FrequencyType.FAIR_MARKET_VALUE.value: False
        }
        
        # Mock dependencies for performance test
        with patch.object(publisher, 'universe_cache') as mock_cache, \
             patch.object(publisher, '_resolve_user_universes_to_tickers') as mock_resolve, \
             patch.object(publisher, '_apply_user_specific_filters') as mock_filters, \
             patch.object(publisher, 'analytics') as mock_analytics:
            
            mock_cache.get_or_load_user_universes.return_value = []
            mock_resolve.return_value = {f"TICK{i}" for i in range(100)}
            mock_filters.side_effect = lambda uid, data: data
            mock_analytics.prepare_enhanced_dual_universe_data.return_value = {'test': True}
            
            performance_timer.start()
            
            # Process multi-frequency data
            result = publisher._process_user_data_multifrequency(
                user_id, stock_data, None, user_prefs
            )
            
            performance_timer.stop()
            
            # Should process in under 50ms
            assert performance_timer.elapsed < 0.05, f"Multi-frequency processing took {performance_timer.elapsed:.3f}s"
            assert result is not None


class TestMultiFrequencyEmissionControl:
    """Test emission control for multi-frequency events"""
    
    @pytest.fixture
    def publisher_with_data_publisher(self, mock_websocket_mgr, multi_frequency_config, mock_cache_control):
        """Create publisher with mock data publisher"""
        with patch('src.presentation.websocket.publisher.UserFiltersService'), \
             patch('src.presentation.websocket.publisher.UserSettingsService'), \
             patch('src.presentation.websocket.publisher.WebSocketFilterCache'), \
             patch('src.presentation.websocket.publisher.WebSocketDataFilter'), \
             patch('src.presentation.websocket.publisher.WebSocketAnalytics'), \
             patch('src.presentation.websocket.publisher.WebSocketDisplayConverter'), \
             patch('src.presentation.websocket.publisher.WebSocketUniverseCache'), \
             patch('src.presentation.websocket.publisher.WebSocketStatistics'):
            
            publisher = WebSocketPublisher(
                mock_websocket_mgr,
                multi_frequency_config,
                mock_cache_control
            )
            
            # Mock data publisher
            mock_data_publisher = Mock()
            mock_data_publisher.get_collected_data.return_value = {
                'frequencies': {
                    'per_second': {'highs': [], 'lows': [], 'trending': {'up': [], 'down': []}, 'surging': {'up': [], 'down': []}},
                    'per_minute': {'aggregates': []},
                    'fmv': {'fmv_events': []}
                }
            }
            publisher.data_publisher = mock_data_publisher
            
            return publisher
    
    def test_emission_lock_usage(self, publisher_with_data_publisher):
        """Test that emission operations use thread locks correctly"""
        publisher = publisher_with_data_publisher
        
        # Should have emission lock
        assert hasattr(publisher, 'emission_lock')
        assert isinstance(publisher.emission_lock, threading.Lock)
        
        # Test that frequency changes use the lock
        with patch.object(publisher.emission_lock, 'acquire') as mock_acquire:
            with patch.object(publisher.emission_lock, 'release') as mock_release:
                publisher.enable_frequency(FrequencyType.PER_MINUTE)
                
                # Lock should have been used in context manager
                mock_acquire.assert_called()
                mock_release.assert_called()
    
    def test_emission_timing_configuration(self, publisher_with_data_publisher, multi_frequency_config):
        """Test emission timing configuration"""
        publisher = publisher_with_data_publisher
        
        # Check emission interval is set from config
        expected_interval = multi_frequency_config.get('EMISSION_INTERVAL', 1.0)
        assert publisher.emission_interval == expected_interval
        
        # Should have emission control attributes
        assert hasattr(publisher, 'emission_in_progress')
        assert hasattr(publisher, 'last_emission_time')
        assert publisher.emission_in_progress is False
        assert publisher.last_emission_time == 0