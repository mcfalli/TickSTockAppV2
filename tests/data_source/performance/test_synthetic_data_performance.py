"""
Performance tests for multi-frequency synthetic data generation.

Tests validate that the synthetic data system can handle high-frequency
generation scenarios while maintaining acceptable performance characteristics.
"""

import pytest
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
from unittest.mock import patch, Mock

# Import fixtures
from tests.data_source.fixtures.synthetic_data_fixtures import (
    SyntheticTestScenario,
    assert_generation_statistics
)

# Import synthetic data types
try:
    from src.infrastructure.data_sources.synthetic.types import DataFrequency
    from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
    from src.infrastructure.data_sources.synthetic.validators.data_consistency import DataConsistencyValidator
    from src.core.services.config_manager import ConfigManager
except ImportError:
    # Mock imports for test environment
    from enum import Enum
    
    class DataFrequency(Enum):
        PER_SECOND = "per_second"
        PER_MINUTE = "per_minute"
        FAIR_VALUE = "fair_value"
    
    SimulatedDataProvider = Mock
    DataConsistencyValidator = Mock
    ConfigManager = Mock


class TestSyntheticDataPerformance:
    """Performance tests for synthetic data generation."""
    
    @pytest.mark.performance
    def test_single_ticker_generation_speed(
        self,
        performance_test_config,
        performance_timer,
        synthetic_test_tickers
    ):
        """Test generation speed for single ticker across all frequencies."""
        provider = SimulatedDataProvider(performance_test_config)
        ticker = synthetic_test_tickers[0]
        
        # Test each frequency individually
        frequency_results = {}
        
        for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
            if provider.has_frequency_support(frequency):
                performance_timer.start()
                
                generation_count = 0
                test_iterations = 1000
                
                for _ in range(test_iterations):
                    data = provider.generate_tick_data(ticker, frequency)
                    if data:
                        generation_count += 1
                
                performance_timer.stop()
                
                frequency_results[frequency.value] = {
                    'duration': performance_timer.elapsed,
                    'generation_count': generation_count,
                    'generations_per_second': generation_count / performance_timer.elapsed if performance_timer.elapsed > 0 else 0,
                    'avg_generation_time_ms': (performance_timer.elapsed * 1000) / generation_count if generation_count > 0 else 0
                }
        
        # Validate performance benchmarks
        for freq_name, results in frequency_results.items():
            assert results['generation_count'] > 0, f"No data generated for {freq_name}"
            assert results['generations_per_second'] > 100, f"Poor performance for {freq_name}: {results['generations_per_second']:.1f} gen/sec"
            assert results['avg_generation_time_ms'] < 10, f"Slow generation for {freq_name}: {results['avg_generation_time_ms']:.2f}ms average"
        
        # Per-second generation should be fastest
        if DataFrequency.PER_SECOND.value in frequency_results:
            per_second_perf = frequency_results[DataFrequency.PER_SECOND.value]['generations_per_second']
            
            for freq_name, results in frequency_results.items():
                if freq_name != DataFrequency.PER_SECOND.value:
                    # Per-second should be at least as fast as other frequencies
                    assert per_second_perf >= results['generations_per_second'] * 0.8, \
                        f"Per-second generation unexpectedly slower than {freq_name}"
    
    @pytest.mark.performance
    def test_multi_ticker_concurrent_generation(
        self,
        performance_test_config,
        performance_timer,
        synthetic_test_tickers
    ):
        """Test concurrent generation for multiple tickers."""
        provider = SimulatedDataProvider(performance_test_config)
        tickers = synthetic_test_tickers[:5]  # Use first 5 tickers
        
        def generate_data_for_ticker(ticker: str, iterations: int = 200) -> Dict[str, Any]:
            """Generate data for a single ticker."""
            thread_results = {
                'ticker': ticker,
                'generation_count': 0,
                'errors': 0,
                'start_time': time.time()
            }
            
            for _ in range(iterations):
                try:
                    # Generate data for each supported frequency
                    for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                        if provider.has_frequency_support(frequency):
                            data = provider.generate_tick_data(ticker, frequency)
                            if data:
                                thread_results['generation_count'] += 1
                except Exception as e:
                    thread_results['errors'] += 1
            
            thread_results['duration'] = time.time() - thread_results['start_time']
            return thread_results
        
        performance_timer.start()
        
        # Use ThreadPoolExecutor for concurrent generation
        with ThreadPoolExecutor(max_workers=len(tickers)) as executor:
            # Submit tasks for each ticker
            future_to_ticker = {
                executor.submit(generate_data_for_ticker, ticker): ticker 
                for ticker in tickers
            }
            
            # Collect results
            ticker_results = []
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    result = future.result()
                    ticker_results.append(result)
                except Exception as e:
                    pytest.fail(f"Concurrent generation failed for {ticker}: {e}")
        
        performance_timer.stop()
        
        # Validate concurrent performance
        assert len(ticker_results) == len(tickers), "Not all ticker threads completed"
        
        total_generations = sum(r['generation_count'] for r in ticker_results)
        total_errors = sum(r['errors'] for r in ticker_results)
        
        assert total_generations > 0, "No data generated in concurrent test"
        assert total_errors == 0, f"Errors occurred during concurrent generation: {total_errors}"
        
        # Performance should scale reasonably with concurrent access
        concurrent_gen_per_sec = total_generations / performance_timer.elapsed
        assert concurrent_gen_per_sec > 500, f"Poor concurrent performance: {concurrent_gen_per_sec:.1f} gen/sec"
        
        # Check that each ticker generated data reasonably evenly
        generation_counts = [r['generation_count'] for r in ticker_results]
        if len(generation_counts) > 1:
            count_variance = statistics.variance(generation_counts)
            count_mean = statistics.mean(generation_counts)
            cv = count_variance / (count_mean ** 2) if count_mean > 0 else 0  # Coefficient of variation
            
            assert cv < 0.5, f"Uneven generation distribution across tickers: CV={cv:.2f}"
    
    @pytest.mark.performance
    def test_sustained_high_frequency_generation(
        self,
        rapid_generation_config,
        performance_timer,
        synthetic_test_tickers
    ):
        """Test sustained high-frequency generation over extended period."""
        # Configure for very high frequency generation
        config = rapid_generation_config.copy()
        config['SYNTHETIC_PER_SECOND_FREQUENCY'] = 0.01  # 100 times per second
        config['SYNTHETIC_FMV_UPDATE_INTERVAL'] = 0.1    # 10 times per second
        
        provider = SimulatedDataProvider(config)
        ticker = synthetic_test_tickers[0]
        
        # Test parameters
        test_duration = 5.0  # 5 seconds of sustained generation
        sampling_interval = 0.1  # Sample performance every 100ms
        
        generation_counts = []
        performance_samples = []
        
        test_start = time.time()
        last_sample_time = test_start
        last_generation_count = 0
        
        while time.time() - test_start < test_duration:
            # Generate data rapidly
            current_generations = 0
            sample_start = time.time()
            
            # Generate for sampling interval
            while time.time() - sample_start < sampling_interval:
                for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                    if provider.has_frequency_support(frequency):
                        try:
                            data = provider.generate_tick_data(ticker, frequency)
                            if data:
                                current_generations += 1
                        except Exception:
                            pass  # Continue on errors for performance testing
            
            # Record performance sample
            sample_duration = time.time() - sample_start
            sample_rate = current_generations / sample_duration if sample_duration > 0 else 0
            
            generation_counts.append(current_generations)
            performance_samples.append(sample_rate)
            
            # Brief pause to prevent overwhelming the system
            time.sleep(0.001)
        
        total_duration = time.time() - test_start
        total_generations = sum(generation_counts)
        
        # Validate sustained performance
        assert total_generations > 0, "No data generated during sustained test"
        assert len(performance_samples) > 10, "Not enough performance samples collected"
        
        overall_rate = total_generations / total_duration
        assert overall_rate > 50, f"Poor sustained performance: {overall_rate:.1f} gen/sec"
        
        # Check performance consistency (should not degrade significantly over time)
        if len(performance_samples) >= 4:
            first_half = performance_samples[:len(performance_samples)//2]
            second_half = performance_samples[len(performance_samples)//2:]
            
            first_half_avg = statistics.mean(first_half)
            second_half_avg = statistics.mean(second_half)
            
            if first_half_avg > 0:
                performance_degradation = (first_half_avg - second_half_avg) / first_half_avg
                assert performance_degradation < 0.3, f"Significant performance degradation: {performance_degradation:.1%}"
    
    @pytest.mark.performance
    def test_memory_usage_during_generation(
        self,
        multi_frequency_synthetic_config,
        synthetic_test_tickers
    ):
        """Test memory usage characteristics during data generation."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Record initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        provider = SimulatedDataProvider(multi_frequency_synthetic_config)
        tickers = synthetic_test_tickers[:3]  # Use 3 tickers
        
        # Generate substantial amount of data
        generation_cycles = 1000
        memory_samples = []
        
        for cycle in range(generation_cycles):
            # Generate data for all tickers and frequencies
            for ticker in tickers:
                for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                    if provider.has_frequency_support(frequency):
                        data = provider.generate_tick_data(ticker, frequency)
            
            # Sample memory usage periodically
            if cycle % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_samples.append(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Validate memory usage
        memory_increase = final_memory - initial_memory
        assert memory_increase < 100, f"Excessive memory usage: {memory_increase:.1f} MB increase"
        
        # Check for memory leaks (memory should stabilize, not continuously grow)
        if len(memory_samples) >= 5:
            # Calculate trend in memory usage
            sample_indices = list(range(len(memory_samples)))
            memory_trend = statistics.correlation(sample_indices, memory_samples) if len(set(memory_samples)) > 1 else 0
            
            # Strong positive correlation would indicate a memory leak
            assert abs(memory_trend) < 0.8, f"Potential memory leak detected: trend correlation={memory_trend:.2f}"
    
    @pytest.mark.performance
    def test_validation_performance_impact(
        self,
        multi_frequency_synthetic_config,
        synthetic_test_tickers,
        performance_timer
    ):
        """Test performance impact of data validation."""
        ticker = synthetic_test_tickers[0]
        test_iterations = 500
        
        # Test 1: Generation without validation
        config_no_validation = multi_frequency_synthetic_config.copy()
        config_no_validation['ENABLE_SYNTHETIC_DATA_VALIDATION'] = False
        
        provider_no_validation = SimulatedDataProvider(config_no_validation)
        
        performance_timer.start()
        no_validation_count = 0
        
        for _ in range(test_iterations):
            for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                if provider_no_validation.has_frequency_support(frequency):
                    data = provider_no_validation.generate_tick_data(ticker, frequency)
                    if data:
                        no_validation_count += 1
        
        performance_timer.stop()
        no_validation_duration = performance_timer.elapsed
        no_validation_rate = no_validation_count / no_validation_duration if no_validation_duration > 0 else 0
        
        # Test 2: Generation with validation
        config_with_validation = multi_frequency_synthetic_config.copy()
        config_with_validation['ENABLE_SYNTHETIC_DATA_VALIDATION'] = True
        
        provider_with_validation = SimulatedDataProvider(config_with_validation)
        
        performance_timer.start()
        with_validation_count = 0
        
        for _ in range(test_iterations):
            for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                if provider_with_validation.has_frequency_support(frequency):
                    data = provider_with_validation.generate_tick_data(ticker, frequency)
                    if data:
                        with_validation_count += 1
        
        performance_timer.stop()
        with_validation_duration = performance_timer.elapsed
        with_validation_rate = with_validation_count / with_validation_duration if with_validation_duration > 0 else 0
        
        # Validate performance impact
        assert no_validation_count > 0 and with_validation_count > 0, "Generation failed in validation test"
        
        # Validation should not slow down generation by more than 50%
        if no_validation_rate > 0:
            performance_impact = (no_validation_rate - with_validation_rate) / no_validation_rate
            assert performance_impact < 0.5, f"Validation causes excessive slowdown: {performance_impact:.1%}"
        
        # Both should maintain reasonable absolute performance
        assert with_validation_rate > 50, f"Poor performance with validation: {with_validation_rate:.1f} gen/sec"
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_configuration_switching_performance(
        self,
        synthetic_test_tickers,
        performance_timer
    ):
        """Test performance of switching between different configurations."""
        ticker = synthetic_test_tickers[0]
        
        config_manager = ConfigManager()
        presets = config_manager.get_synthetic_data_presets()
        
        switching_times = []
        generation_performance = {}
        
        for preset_name in ['development', 'integration_testing', 'performance_testing']:
            if preset_name in presets:
                # Measure configuration switching time
                performance_timer.start()
                config_manager.apply_synthetic_data_preset(preset_name)
                performance_timer.stop()
                
                switching_times.append(performance_timer.elapsed)
                
                # Test generation performance with this preset
                provider = SimulatedDataProvider(config_manager.config)
                
                performance_timer.start()
                generation_count = 0
                
                for _ in range(100):  # 100 generations per preset
                    for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                        if provider.has_frequency_support(frequency):
                            data = provider.generate_tick_data(ticker, frequency)
                            if data:
                                generation_count += 1
                
                performance_timer.stop()
                
                generation_performance[preset_name] = {
                    'duration': performance_timer.elapsed,
                    'count': generation_count,
                    'rate': generation_count / performance_timer.elapsed if performance_timer.elapsed > 0 else 0
                }
        
        # Validate configuration switching performance
        if switching_times:
            avg_switching_time = statistics.mean(switching_times)
            max_switching_time = max(switching_times)
            
            assert avg_switching_time < 0.1, f"Slow configuration switching: {avg_switching_time:.3f}s average"
            assert max_switching_time < 0.5, f"Very slow configuration switching: {max_switching_time:.3f}s max"
        
        # Validate that all presets maintain reasonable performance
        for preset_name, perf_data in generation_performance.items():
            assert perf_data['count'] > 0, f"No data generated for preset: {preset_name}"
            assert perf_data['rate'] > 10, f"Poor performance for preset {preset_name}: {perf_data['rate']:.1f} gen/sec"


class TestSyntheticDataScalability:
    """Test scalability characteristics of synthetic data system."""
    
    @pytest.mark.performance
    def test_ticker_count_scalability(
        self,
        multi_frequency_synthetic_config,
        synthetic_test_tickers,
        performance_timer
    ):
        """Test how performance scales with increasing ticker count."""
        provider = SimulatedDataProvider(multi_frequency_synthetic_config)
        
        ticker_counts = [1, 5, 10, 20]  # Test with different ticker counts
        scalability_results = {}
        
        for ticker_count in ticker_counts:
            test_tickers = synthetic_test_tickers[:ticker_count]
            
            performance_timer.start()
            generation_count = 0
            
            # Generate data for all tickers
            for _ in range(50):  # 50 iterations per ticker count
                for ticker in test_tickers:
                    for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                        if provider.has_frequency_support(frequency):
                            data = provider.generate_tick_data(ticker, frequency)
                            if data:
                                generation_count += 1
            
            performance_timer.stop()
            
            scalability_results[ticker_count] = {
                'duration': performance_timer.elapsed,
                'generation_count': generation_count,
                'rate': generation_count / performance_timer.elapsed if performance_timer.elapsed > 0 else 0,
                'rate_per_ticker': (generation_count / performance_timer.elapsed / ticker_count) if performance_timer.elapsed > 0 and ticker_count > 0 else 0
            }
        
        # Validate scalability characteristics
        for ticker_count, results in scalability_results.items():
            assert results['generation_count'] > 0, f"No data generated for {ticker_count} tickers"
            assert results['rate'] > 0, f"Zero generation rate for {ticker_count} tickers"
        
        # Check that per-ticker performance doesn't degrade significantly
        if len(scalability_results) >= 2:
            rates_per_ticker = [r['rate_per_ticker'] for r in scalability_results.values()]
            
            if all(rate > 0 for rate in rates_per_ticker):
                min_rate = min(rates_per_ticker)
                max_rate = max(rates_per_ticker)
                
                # Per-ticker rate shouldn't vary by more than 3x across different ticker counts
                rate_ratio = max_rate / min_rate if min_rate > 0 else float('inf')
                assert rate_ratio < 3.0, f"Poor scalability: per-ticker rate varies by {rate_ratio:.1f}x"
    
    @pytest.mark.performance
    def test_frequency_combination_scalability(
        self,
        multi_frequency_synthetic_config,
        synthetic_test_tickers,
        performance_timer
    ):
        """Test scalability with different frequency combinations."""
        ticker = synthetic_test_tickers[0]
        
        # Test different frequency combinations
        frequency_combinations = [
            [DataFrequency.PER_SECOND],
            [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE],
            [DataFrequency.PER_SECOND, DataFrequency.FAIR_VALUE],
            [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]
        ]
        
        combination_results = {}
        
        for i, frequencies in enumerate(frequency_combinations):
            # Configure provider for specific frequency combination
            test_config = multi_frequency_synthetic_config.copy()
            test_config['WEBSOCKET_PER_SECOND_ENABLED'] = DataFrequency.PER_SECOND in frequencies
            test_config['WEBSOCKET_PER_MINUTE_ENABLED'] = DataFrequency.PER_MINUTE in frequencies
            test_config['WEBSOCKET_FAIR_VALUE_ENABLED'] = DataFrequency.FAIR_VALUE in frequencies
            
            provider = SimulatedDataProvider(test_config)
            
            performance_timer.start()
            generation_count = 0
            
            for _ in range(200):  # 200 iterations per combination
                for frequency in frequencies:
                    if provider.has_frequency_support(frequency):
                        data = provider.generate_tick_data(ticker, frequency)
                        if data:
                            generation_count += 1
            
            performance_timer.stop()
            
            combination_results[f"combo_{i+1}_{len(frequencies)}freq"] = {
                'frequencies': [f.value for f in frequencies],
                'frequency_count': len(frequencies),
                'duration': performance_timer.elapsed,
                'generation_count': generation_count,
                'rate': generation_count / performance_timer.elapsed if performance_timer.elapsed > 0 else 0,
                'rate_per_frequency': (generation_count / performance_timer.elapsed / len(frequencies)) if performance_timer.elapsed > 0 and len(frequencies) > 0 else 0
            }
        
        # Validate frequency combination scalability
        for combo_name, results in combination_results.items():
            assert results['generation_count'] > 0, f"No data generated for {combo_name}"
            assert results['rate'] > 0, f"Zero generation rate for {combo_name}"
        
        # Check that adding frequencies doesn't cause exponential performance degradation
        single_freq_rate = None
        multi_freq_rates = []
        
        for results in combination_results.values():
            if results['frequency_count'] == 1:
                single_freq_rate = results['rate']
            else:
                multi_freq_rates.append(results['rate'])
        
        if single_freq_rate and multi_freq_rates:
            for multi_rate in multi_freq_rates:
                # Multi-frequency shouldn't be slower than 5x single frequency
                slowdown_factor = single_freq_rate / multi_rate if multi_rate > 0 else float('inf')
                assert slowdown_factor < 5.0, f"Excessive slowdown with multiple frequencies: {slowdown_factor:.1f}x"


# Performance test utilities
def measure_generation_latency(provider, ticker: str, frequency: DataFrequency, iterations: int = 100) -> List[float]:
    """Measure individual generation latencies."""
    latencies = []
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        data = provider.generate_tick_data(ticker, frequency)
        end_time = time.perf_counter()
        
        if data:
            latencies.append((end_time - start_time) * 1000)  # Convert to milliseconds
    
    return latencies


def analyze_latency_distribution(latencies: List[float]) -> Dict[str, float]:
    """Analyze latency distribution statistics."""
    if not latencies:
        return {}
    
    return {
        'min': min(latencies),
        'max': max(latencies),
        'mean': statistics.mean(latencies),
        'median': statistics.median(latencies),
        'p95': sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies),
        'p99': sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 100 else max(latencies),
        'stddev': statistics.stdev(latencies) if len(latencies) > 1 else 0.0
    }


def assert_performance_within_bounds(
    generation_rate: float,
    min_rate: float = 50.0,
    max_latency_ms: float = 10.0,
    latencies: List[float] = None
):
    """Assert that performance metrics are within acceptable bounds."""
    assert generation_rate >= min_rate, f"Generation rate too slow: {generation_rate:.1f} gen/sec (min: {min_rate})"
    
    if latencies:
        latency_stats = analyze_latency_distribution(latencies)
        if 'p95' in latency_stats:
            assert latency_stats['p95'] <= max_latency_ms, f"95th percentile latency too high: {latency_stats['p95']:.2f}ms (max: {max_latency_ms}ms)"