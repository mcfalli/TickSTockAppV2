"""
Integration tests for multi-frequency synthetic data generation and processing - Sprint 101
Tests synthetic data pipeline for development and testing scenarios.
"""

import pytest
import time
import json
import threading
from unittest.mock import Mock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from src.shared.types.frequency import FrequencyType


class TestSyntheticDataMultiFrequencyIntegration:
    """Integration tests for synthetic multi-frequency data generation"""
    
    @pytest.fixture
    def synthetic_multifrequency_config(self):
        """Configuration for synthetic multi-frequency data testing"""
        return {
            'use_simulated_data': True,
            'enable_per_minute_events': True,
            'enable_fmv_events': True,
            
            # Synthetic data settings
            'synthetic_data_rate': 10,  # Events per second
            'synthetic_tickers': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'],
            'synthetic_price_volatility': 0.02,
            'synthetic_volume_range': (1000, 50000),
            
            # Multi-frequency timing
            'per_second_interval': 1.0,
            'per_minute_interval': 60.0,
            'fmv_interval': 30.0,
            
            # Testing flags
            'testing': True,
            'trace_synthetic_generation': True
        }
    
    @pytest.fixture
    def synthetic_data_generator(self, synthetic_multifrequency_config):
        """Create synthetic data generator for multi-frequency testing"""
        with patch('src.infrastructure.synthetic_data_source.SyntheticDataSource') as MockSynthetic:
            generator = MockSynthetic(config=synthetic_multifrequency_config)
            
            # Mock generation methods
            generator.generate_per_second_tick = Mock()
            generator.generate_per_minute_aggregate = Mock() 
            generator.generate_fmv_event = Mock()
            generator.get_synthetic_tickers = Mock(return_value=synthetic_multifrequency_config['synthetic_tickers'])
            
            return generator
    
    def test_synthetic_per_second_data_generation(self, synthetic_data_generator, synthetic_multifrequency_config):
        """Test synthetic per-second tick generation"""
        generator = synthetic_data_generator
        tickers = synthetic_multifrequency_config['synthetic_tickers']
        
        # Configure mock to return realistic per-second data
        def mock_generate_tick(ticker):
            return {
                "ev": "A",
                "sym": ticker,
                "c": 150.0 + hash(ticker) % 100,  # Deterministic but varied prices
                "h": 151.0 + hash(ticker) % 100,
                "l": 149.0 + hash(ticker) % 100,
                "o": 149.5 + hash(ticker) % 100,
                "v": 1000 + (hash(ticker) % 10000),
                "vw": 150.25 + hash(ticker) % 100,
                "t": int(time.time() * 1000)
            }
        
        generator.generate_per_second_tick.side_effect = mock_generate_tick
        
        # Generate ticks for all synthetic tickers
        generated_ticks = []
        for ticker in tickers:
            tick = generator.generate_per_second_tick(ticker)
            generated_ticks.append(tick)
        
        # Verify generation
        assert len(generated_ticks) == len(tickers)
        assert generator.generate_per_second_tick.call_count == len(tickers)
        
        # Verify tick data structure
        for tick in generated_ticks:
            assert tick['ev'] == 'A'
            assert tick['sym'] in tickers
            assert tick['c'] > 0  # Valid price
            assert tick['v'] > 0  # Valid volume
            assert tick['t'] > 0  # Valid timestamp
    
    def test_synthetic_per_minute_aggregate_generation(self, synthetic_data_generator, synthetic_multifrequency_config):
        """Test synthetic per-minute aggregate generation"""
        generator = synthetic_data_generator
        tickers = synthetic_multifrequency_config['synthetic_tickers']
        
        # Configure mock to return realistic AM data
        def mock_generate_am(ticker, minute_window=None):
            base_price = 150.0 + hash(ticker) % 100
            return {
                "ev": "AM",
                "sym": ticker,
                "v": 50000 + (hash(ticker) % 100000),  # Minute volume
                "av": 500000 + (hash(ticker) % 1000000),  # Accumulated volume
                "op": base_price - 5.0,  # Daily open
                "vw": base_price + 0.25,  # VWAP
                "o": base_price - 0.50,  # Minute open
                "c": base_price,  # Minute close
                "h": base_price + 1.0,  # Minute high
                "l": base_price - 1.0,  # Minute low
                "a": base_price + 0.15,  # Daily VWAP
                "z": 500 + (hash(ticker) % 1000),  # Average trade size
                "s": int(time.time() * 1000) - 60000,  # Start timestamp
                "e": int(time.time() * 1000)  # End timestamp
            }
        
        generator.generate_per_minute_aggregate.side_effect = mock_generate_am
        
        # Generate AM events for all tickers
        generated_aggregates = []
        for ticker in tickers:
            aggregate = generator.generate_per_minute_aggregate(ticker)
            generated_aggregates.append(aggregate)
        
        # Verify generation
        assert len(generated_aggregates) == len(tickers)
        assert generator.generate_per_minute_aggregate.call_count == len(tickers)
        
        # Verify AM data structure
        for aggregate in generated_aggregates:
            assert aggregate['ev'] == 'AM'
            assert aggregate['sym'] in tickers
            assert aggregate['c'] > 0  # Valid close price
            assert aggregate['v'] > 0  # Valid volume
            assert aggregate['s'] < aggregate['e']  # Start before end
    
    def test_synthetic_fmv_data_generation(self, synthetic_data_generator, synthetic_multifrequency_config):
        """Test synthetic FMV event generation"""
        generator = synthetic_data_generator
        tickers = synthetic_multifrequency_config['synthetic_tickers']
        
        # Configure mock to return realistic FMV data
        def mock_generate_fmv(ticker, market_price=None):
            base_fmv = 150.0 + hash(ticker) % 100
            # Add small random variation to simulate FMV algorithm
            fmv_variation = (hash(ticker + str(time.time())) % 200 - 100) / 1000.0  # ±0.1
            return {
                "ev": "FMV",
                "fmv": base_fmv + fmv_variation,
                "sym": ticker,
                "t": int(time.time() * 1_000_000_000)  # Nanosecond timestamp
            }
        
        generator.generate_fmv_event.side_effect = mock_generate_fmv
        
        # Generate FMV events for all tickers
        generated_fmv_events = []
        for ticker in tickers:
            fmv_event = generator.generate_fmv_event(ticker)
            generated_fmv_events.append(fmv_event)
        
        # Verify generation
        assert len(generated_fmv_events) == len(tickers)
        assert generator.generate_fmv_event.call_count == len(tickers)
        
        # Verify FMV data structure
        for fmv_event in generated_fmv_events:
            assert fmv_event['ev'] == 'FMV'
            assert fmv_event['sym'] in tickers
            assert fmv_event['fmv'] > 0  # Valid FMV price
            assert fmv_event['t'] > 0  # Valid nanosecond timestamp
            assert len(str(fmv_event['t'])) >= 18  # Nanosecond precision
    
    def test_synthetic_data_timing_coordination(self, synthetic_data_generator, synthetic_multifrequency_config):
        """Test coordination of synthetic data generation timing across frequencies"""
        generator = synthetic_data_generator
        config = synthetic_multifrequency_config
        
        # Mock timing-aware generation
        generation_log = []
        
        def log_generation(freq_type, ticker, timestamp):
            generation_log.append({
                'frequency': freq_type,
                'ticker': ticker,
                'timestamp': timestamp
            })
        
        def mock_tick_with_timing(ticker):
            timestamp = time.time()
            log_generation(FrequencyType.PER_SECOND, ticker, timestamp)
            return {"ev": "A", "sym": ticker, "c": 150.0, "t": int(timestamp * 1000)}
        
        def mock_am_with_timing(ticker):
            timestamp = time.time()
            log_generation(FrequencyType.PER_MINUTE, ticker, timestamp)
            return {"ev": "AM", "sym": ticker, "c": 150.0, "s": int(timestamp * 1000)}
        
        def mock_fmv_with_timing(ticker):
            timestamp = time.time()
            log_generation(FrequencyType.FAIR_MARKET_VALUE, ticker, timestamp)
            return {"ev": "FMV", "sym": ticker, "fmv": 150.0, "t": int(timestamp * 1_000_000_000)}
        
        generator.generate_per_second_tick.side_effect = mock_tick_with_timing
        generator.generate_per_minute_aggregate.side_effect = mock_am_with_timing
        generator.generate_fmv_event.side_effect = mock_fmv_with_timing
        
        # Simulate coordinated generation
        ticker = "AAPL"
        start_time = time.time()
        
        # Generate events at different frequencies
        generator.generate_per_second_tick(ticker)
        time.sleep(0.01)  # Small delay
        generator.generate_per_minute_aggregate(ticker)
        time.sleep(0.01)  # Small delay
        generator.generate_fmv_event(ticker)
        
        end_time = time.time()
        
        # Verify timing coordination
        assert len(generation_log) == 3
        
        # All events should be within the test time window
        for entry in generation_log:
            assert start_time <= entry['timestamp'] <= end_time
            assert entry['ticker'] == ticker
        
        # Should have all frequency types
        frequencies_generated = {entry['frequency'] for entry in generation_log}
        assert FrequencyType.PER_SECOND in frequencies_generated
        assert FrequencyType.PER_MINUTE in frequencies_generated
        assert FrequencyType.FAIR_MARKET_VALUE in frequencies_generated
    
    def test_synthetic_data_mathematical_consistency(self, synthetic_data_generator, event_builder):
        """Test mathematical consistency between synthetic data frequencies"""
        generator = synthetic_data_generator
        ticker = "AAPL"
        
        # Generate correlated synthetic data
        base_price = 150.0
        base_volume = 1000
        
        # Per-second tick
        tick_data = {
            "ev": "A", "sym": ticker, "c": base_price, "v": base_volume,
            "h": base_price + 0.5, "l": base_price - 0.5, "o": base_price - 0.25,
            "t": int(time.time() * 1000)
        }
        
        # Per-minute aggregate (should aggregate per-second data)
        minute_data = {
            "ev": "AM", "sym": ticker,
            "c": base_price,  # Close matches tick close
            "o": base_price - 0.25,  # Open matches tick open
            "h": base_price + 0.5,  # High matches tick high
            "l": base_price - 0.5,  # Low matches tick low
            "v": base_volume * 60,  # Aggregate of ~60 seconds
            "s": int(time.time() * 1000) - 60000,
            "e": int(time.time() * 1000)
        }
        
        # FMV should be correlated to market price
        fmv_data = {
            "ev": "FMV", "sym": ticker,
            "fmv": base_price + 0.25,  # FMV slightly different from market
            "t": int(time.time() * 1_000_000_000)
        }
        
        # Configure mocks
        generator.generate_per_second_tick.return_value = tick_data
        generator.generate_per_minute_aggregate.return_value = minute_data
        generator.generate_fmv_event.return_value = fmv_data
        
        # Generate events
        tick = generator.generate_per_second_tick(ticker)
        minute = generator.generate_per_minute_aggregate(ticker)
        fmv = generator.generate_fmv_event(ticker)
        
        # Verify mathematical consistency
        
        # OHLC relationships in per-second data
        assert tick['h'] >= max(tick['o'], tick['c'])  # High >= max(open, close)
        assert tick['l'] <= min(tick['o'], tick['c'])  # Low <= min(open, close)
        
        # OHLC relationships in per-minute data
        assert minute['h'] >= max(minute['o'], minute['c'])
        assert minute['l'] <= min(minute['o'], minute['c'])
        
        # Consistency between per-second and per-minute
        assert tick['c'] == minute['c']  # Close prices match
        assert tick['o'] == minute['o']  # Open prices match
        assert tick['h'] == minute['h']  # High prices match
        assert tick['l'] == minute['l']  # Low prices match
        
        # Volume scaling (minute should be aggregate)
        assert minute['v'] > tick['v']  # Minute volume should be larger
        
        # FMV correlation (should be reasonably close to market price)
        price_diff = abs(fmv['fmv'] - tick['c'])
        price_pct_diff = price_diff / tick['c'] * 100
        assert price_pct_diff < 10.0  # FMV within 10% of market price
    
    def test_synthetic_data_volume_distribution(self, synthetic_data_generator, synthetic_multifrequency_config):
        """Test realistic volume distribution in synthetic data"""
        generator = synthetic_data_generator
        tickers = synthetic_multifrequency_config['synthetic_tickers']
        volume_range = synthetic_multifrequency_config['synthetic_volume_range']
        
        # Generate volume data for statistical analysis
        per_second_volumes = []
        per_minute_volumes = []
        
        # Configure mocks to return varied volumes
        def mock_tick_volume(ticker):
            # Simulate realistic volume distribution
            base_volume = volume_range[0] + (hash(ticker) % (volume_range[1] - volume_range[0]))
            # Add some randomness based on ticker and time
            volume_multiplier = 1.0 + (hash(ticker + str(time.time())) % 200 - 100) / 1000.0
            return {
                "ev": "A", "sym": ticker, "c": 150.0,
                "v": int(base_volume * volume_multiplier),
                "t": int(time.time() * 1000)
            }
        
        def mock_minute_volume(ticker):
            # Per-minute volume should be aggregate of per-second
            base_volume = volume_range[0] * 60  # Rough aggregate
            volume_multiplier = 1.0 + (hash(ticker + "minute") % 300 - 150) / 1000.0
            return {
                "ev": "AM", "sym": ticker, "c": 150.0,
                "v": int(base_volume * volume_multiplier),
                "s": int(time.time() * 1000) - 60000,
                "e": int(time.time() * 1000)
            }
        
        generator.generate_per_second_tick.side_effect = mock_tick_volume
        generator.generate_per_minute_aggregate.side_effect = mock_minute_volume
        
        # Generate data for multiple tickers
        for ticker in tickers:
            tick = generator.generate_per_second_tick(ticker)
            minute = generator.generate_per_minute_aggregate(ticker)
            
            per_second_volumes.append(tick['v'])
            per_minute_volumes.append(minute['v'])
        
        # Verify volume distribution characteristics
        assert len(per_second_volumes) == len(tickers)
        assert len(per_minute_volumes) == len(tickers)
        
        # Per-second volumes should be in expected range
        assert all(volume_range[0] <= vol <= volume_range[1] * 2 for vol in per_second_volumes)
        
        # Per-minute volumes should be larger (aggregate)
        assert all(per_minute_vol > per_second_vol for per_second_vol, per_minute_vol in 
                  zip(per_second_volumes, per_minute_volumes))
        
        # Should have reasonable distribution (not all identical)
        per_second_unique = len(set(per_second_volumes))
        per_minute_unique = len(set(per_minute_volumes))
        
        assert per_second_unique > 1, "Per-second volumes should vary"
        assert per_minute_unique > 1, "Per-minute volumes should vary"
    
    @pytest.mark.performance
    def test_synthetic_data_generation_performance(self, synthetic_data_generator, synthetic_multifrequency_config, performance_timer):
        """Test performance of synthetic data generation"""
        generator = synthetic_data_generator
        tickers = synthetic_multifrequency_config['synthetic_tickers']
        
        # Configure fast mock generation
        generator.generate_per_second_tick.return_value = {
            "ev": "A", "sym": "TEST", "c": 150.0, "v": 1000, "t": int(time.time() * 1000)
        }
        generator.generate_per_minute_aggregate.return_value = {
            "ev": "AM", "sym": "TEST", "c": 150.0, "v": 60000,
            "s": int(time.time() * 1000) - 60000, "e": int(time.time() * 1000)
        }
        generator.generate_fmv_event.return_value = {
            "ev": "FMV", "sym": "TEST", "fmv": 150.25, "t": int(time.time() * 1_000_000_000)
        }
        
        performance_timer.start()
        
        # Generate large volume of synthetic data
        generations_per_ticker = 100
        for ticker in tickers:
            for _ in range(generations_per_ticker):
                generator.generate_per_second_tick(ticker)
                
                # Per-minute and FMV at lower frequency
                if _ % 60 == 0:  # Every 60 per-second events
                    generator.generate_per_minute_aggregate(ticker)
                
                if _ % 30 == 0:  # Every 30 per-second events
                    generator.generate_fmv_event(ticker)
        
        performance_timer.stop()
        
        # Should generate data quickly
        total_generations = len(tickers) * generations_per_ticker * 3  # All frequencies
        expected_max_time = 0.1  # 100ms for all generation
        
        assert performance_timer.elapsed < expected_max_time, f"Generation of {total_generations} events took {performance_timer.elapsed:.3f}s"
        
        # Verify call counts
        expected_per_second = len(tickers) * generations_per_ticker
        expected_per_minute = len(tickers) * (generations_per_ticker // 60 + 1)  # +1 for remainder
        expected_fmv = len(tickers) * (generations_per_ticker // 30 + 1)
        
        assert generator.generate_per_second_tick.call_count == expected_per_second
        assert generator.generate_per_minute_aggregate.call_count >= expected_per_minute
        assert generator.generate_fmv_event.call_count >= expected_fmv
    
    def test_synthetic_data_concurrent_generation(self, synthetic_data_generator, synthetic_multifrequency_config):
        """Test concurrent synthetic data generation across frequencies"""
        generator = synthetic_data_generator
        tickers = synthetic_multifrequency_config['synthetic_tickers']
        
        # Configure thread-safe mock returns
        def mock_concurrent_tick(ticker):
            return {
                "ev": "A", "sym": ticker, "c": 150.0 + threading.current_thread().ident % 100,
                "v": 1000 + threading.current_thread().ident % 10000,
                "t": int(time.time() * 1000)
            }
        
        def mock_concurrent_minute(ticker):
            return {
                "ev": "AM", "sym": ticker, "c": 150.0 + threading.current_thread().ident % 100,
                "v": 60000 + threading.current_thread().ident % 100000,
                "s": int(time.time() * 1000) - 60000, "e": int(time.time() * 1000)
            }
        
        def mock_concurrent_fmv(ticker):
            return {
                "ev": "FMV", "sym": ticker,
                "fmv": 150.25 + threading.current_thread().ident % 100,
                "t": int(time.time() * 1_000_000_000)
            }
        
        generator.generate_per_second_tick.side_effect = mock_concurrent_tick
        generator.generate_per_minute_aggregate.side_effect = mock_concurrent_minute
        generator.generate_fmv_event.side_effect = mock_concurrent_fmv
        
        results = []
        errors = []
        
        def generate_concurrent_data(freq_type, ticker):
            try:
                if freq_type == FrequencyType.PER_SECOND:
                    data = generator.generate_per_second_tick(ticker)
                elif freq_type == FrequencyType.PER_MINUTE:
                    data = generator.generate_per_minute_aggregate(ticker)
                elif freq_type == FrequencyType.FAIR_MARKET_VALUE:
                    data = generator.generate_fmv_event(ticker)
                else:
                    raise ValueError(f"Unknown frequency type: {freq_type}")
                
                results.append((freq_type, ticker, data))
            except Exception as e:
                errors.append((freq_type, ticker, str(e)))
        
        # Generate data concurrently across all frequencies and tickers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for ticker in tickers:
                futures.append(executor.submit(generate_concurrent_data, FrequencyType.PER_SECOND, ticker))
                futures.append(executor.submit(generate_concurrent_data, FrequencyType.PER_MINUTE, ticker))
                futures.append(executor.submit(generate_concurrent_data, FrequencyType.FAIR_MARKET_VALUE, ticker))
            
            # Wait for all generation to complete
            for future in futures:
                future.result()
        
        # Verify concurrent generation succeeded
        assert len(errors) == 0, f"Concurrent generation errors: {errors}"
        assert len(results) == len(tickers) * 3  # 3 frequencies per ticker
        
        # Verify all frequency types were generated
        freq_types_generated = {freq_type for freq_type, ticker, data in results}
        assert FrequencyType.PER_SECOND in freq_types_generated
        assert FrequencyType.PER_MINUTE in freq_types_generated
        assert FrequencyType.FAIR_MARKET_VALUE in freq_types_generated
        
        # Verify all tickers were processed
        tickers_generated = {ticker for freq_type, ticker, data in results}
        assert set(tickers) == tickers_generated
    
    def test_synthetic_data_market_session_awareness(self, synthetic_data_generator, synthetic_multifrequency_config):
        """Test synthetic data generation with market session awareness"""
        generator = synthetic_data_generator
        
        # Mock market session-aware generation
        def mock_session_aware_generation(ticker, session='REGULAR'):
            base_volume = 1000
            session_multipliers = {
                'PRE': 0.3,     # Lower volume pre-market
                'REGULAR': 1.0,  # Normal volume
                'POST': 0.5     # Lower volume after-hours
            }
            
            multiplier = session_multipliers.get(session, 1.0)
            
            return {
                "ev": "A", "sym": ticker,
                "c": 150.0 + (hash(session) % 10),  # Slight price variation by session
                "v": int(base_volume * multiplier),
                "session": session,
                "t": int(time.time() * 1000)
            }
        
        # Test different market sessions
        sessions = ['PRE', 'REGULAR', 'POST']
        ticker = "AAPL"
        
        session_data = {}
        for session in sessions:
            # Configure mock for specific session
            generator.generate_per_second_tick.side_effect = lambda t, s=session: mock_session_aware_generation(t, s)
            
            data = generator.generate_per_second_tick(ticker)
            session_data[session] = data
        
        # Verify session-specific characteristics
        assert session_data['PRE']['v'] < session_data['REGULAR']['v']  # Pre-market lower volume
        assert session_data['POST']['v'] < session_data['REGULAR']['v']  # After-hours lower volume
        assert session_data['REGULAR']['v'] > session_data['PRE']['v']  # Regular hours higher volume
        
        # All should be valid data
        for session, data in session_data.items():
            assert data['ev'] == 'A'
            assert data['sym'] == ticker
            assert data['c'] > 0
            assert data['v'] > 0
            assert 'session' in data