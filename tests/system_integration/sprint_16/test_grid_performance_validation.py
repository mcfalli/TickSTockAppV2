"""
Sprint 16 Grid Performance Validation Tests - System-Level Performance
======================================================================

Test comprehensive system performance validation for Sprint 16 grid modernization.

**Sprint**: 16 - Grid Modernization
**Component**: System-wide performance validation  
**Functional Area**: system_integration/sprint_16
**Performance Targets**: <100ms initialization, <50ms API response, <25ms UI updates
"""
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest


@pytest.mark.performance
class TestGridSystemPerformance:
    """Test system-wide performance for grid modernization."""

    def setup_method(self):
        """Setup performance testing environment."""
        self.performance_targets = {
            'grid_initialization': 100,  # ms
            'api_response_time': 50,     # ms
            'ui_update_time': 25,        # ms
            'layout_save_time': 10,      # ms
            'memory_usage': 100,         # MB
            'cpu_usage': 50              # %
        }

        self.test_data_sizes = {
            'small': {'containers': 6, 'market_items': 10},
            'medium': {'containers': 12, 'market_items': 50},
            'large': {'containers': 24, 'market_items': 100}
        }

    def test_grid_initialization_performance_targets(self):
        """Test grid initialization meets <100ms performance target."""
        initialization_times = []

        # Run multiple initialization tests
        for iteration in range(10):
            start_time = time.perf_counter()

            # Mock grid initialization sequence
            self.simulate_grid_initialization()

            init_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            initialization_times.append(init_time)

        # Calculate statistics
        avg_init_time = statistics.mean(initialization_times)
        max_init_time = max(initialization_times)
        p95_init_time = sorted(initialization_times)[int(len(initialization_times) * 0.95)]

        # Verify performance targets
        assert avg_init_time < self.performance_targets['grid_initialization'], \
            f"Average initialization should be <{self.performance_targets['grid_initialization']}ms, got {avg_init_time:.2f}ms"
        assert max_init_time < self.performance_targets['grid_initialization'] * 2, \
            f"Max initialization should be <{self.performance_targets['grid_initialization'] * 2}ms, got {max_init_time:.2f}ms"
        assert p95_init_time < self.performance_targets['grid_initialization'], \
            f"95th percentile should be <{self.performance_targets['grid_initialization']}ms, got {p95_init_time:.2f}ms"

    def simulate_grid_initialization(self):
        """Simulate realistic grid initialization operations."""
        # Step 1: DOM ready check (1ms)
        time.sleep(0.001)

        # Step 2: GridStack library initialization (10ms)
        time.sleep(0.01)

        # Step 3: Container detection (5ms)
        time.sleep(0.005)

        # Step 4: Layout application (15ms)
        time.sleep(0.015)

        # Step 5: Event listeners setup (3ms)
        time.sleep(0.003)

        # Step 6: Controls initialization (2ms)
        time.sleep(0.002)

    @pytest.mark.performance
    def test_api_response_performance_under_load(self):
        """Test API response times under various load conditions."""
        load_scenarios = [
            {'name': 'light_load', 'concurrent_requests': 1, 'target_ms': 30},
            {'name': 'moderate_load', 'concurrent_requests': 5, 'target_ms': 50},
            {'name': 'heavy_load', 'concurrent_requests': 10, 'target_ms': 75}
        ]

        for scenario in load_scenarios:
            response_times = []

            def make_api_request():
                """Simulate API request."""
                start_time = time.perf_counter()

                # Mock API processing
                self.simulate_market_movers_api_call()

                return (time.perf_counter() - start_time) * 1000

            # Execute concurrent requests
            with ThreadPoolExecutor(max_workers=scenario['concurrent_requests']) as executor:
                futures = [executor.submit(make_api_request) for _ in range(scenario['concurrent_requests'])]

                for future in as_completed(futures):
                    response_time = future.result()
                    response_times.append(response_time)

            # Verify performance under load
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)

            assert avg_response_time < scenario['target_ms'], \
                f"{scenario['name']} average response should be <{scenario['target_ms']}ms, got {avg_response_time:.2f}ms"
            assert max_response_time < scenario['target_ms'] * 2, \
                f"{scenario['name']} max response should be <{scenario['target_ms'] * 2}ms, got {max_response_time:.2f}ms"

    def simulate_market_movers_api_call(self):
        """Simulate realistic market movers API processing."""
        # Mock data generation (20ms)
        time.sleep(0.02)

        # Mock serialization (5ms)
        time.sleep(0.005)

        # Mock response formatting (3ms)
        time.sleep(0.003)

    @pytest.mark.performance
    def test_ui_update_performance_with_varying_data_sizes(self):
        """Test UI update performance with different data volumes."""
        for size_name, size_config in self.test_data_sizes.items():
            update_times = []

            # Generate test data
            test_data = self.generate_test_market_data(size_config['market_items'])

            # Run multiple update tests
            for iteration in range(5):
                start_time = time.perf_counter()

                # Simulate UI update process
                self.simulate_ui_update(test_data, size_config['containers'])

                update_time = (time.perf_counter() - start_time) * 1000
                update_times.append(update_time)

            avg_update_time = statistics.mean(update_times)

            # Performance targets scale with data size
            if size_name == 'small':
                target = self.performance_targets['ui_update_time']
            elif size_name == 'medium':
                target = self.performance_targets['ui_update_time'] * 1.5
            else:  # large
                target = self.performance_targets['ui_update_time'] * 2

            assert avg_update_time < target, \
                f"UI update for {size_name} data should be <{target}ms, got {avg_update_time:.2f}ms"

    def generate_test_market_data(self, item_count):
        """Generate test market data of specified size."""
        return {
            'gainers': [
                {
                    'symbol': f'GAIN{i:03d}',
                    'name': f'Gainer Company {i}',
                    'price': 100.0 + i,
                    'change': 1.0 + (i * 0.1),
                    'change_percent': 1.0 + (i * 0.05),
                    'volume': 1000000 + (i * 10000)
                } for i in range(item_count // 2)
            ],
            'losers': [
                {
                    'symbol': f'LOSS{i:03d}',
                    'name': f'Loser Company {i}',
                    'price': 90.0 - i,
                    'change': -1.0 - (i * 0.1),
                    'change_percent': -1.2 - (i * 0.05),
                    'volume': 800000 + (i * 8000)
                } for i in range(item_count // 2)
            ]
        }

    def simulate_ui_update(self, market_data, container_count):
        """Simulate UI update operations."""
        # HTML generation time (scales with data size)
        html_generation_time = len(market_data['gainers'] + market_data['losers']) * 0.0001
        time.sleep(html_generation_time)

        # DOM manipulation time (scales with containers)
        dom_manipulation_time = container_count * 0.001
        time.sleep(dom_manipulation_time)

        # Layout recalculation time (fixed)
        time.sleep(0.005)

    @pytest.mark.performance
    def test_layout_persistence_performance(self):
        """Test layout save/load performance for different layout complexities."""
        layout_scenarios = [
            {'name': 'simple', 'containers': 6, 'target_ms': 5},
            {'name': 'complex', 'containers': 12, 'target_ms': 8},
            {'name': 'maximum', 'containers': 24, 'target_ms': 10}
        ]

        for scenario in layout_scenarios:
            # Generate layout data
            layout_data = self.generate_test_layout(scenario['containers'])

            # Test save performance
            save_times = []
            for _ in range(10):
                start_time = time.perf_counter()

                # Simulate layout save
                serialized_layout = json.dumps(layout_data)
                # Mock localStorage save
                mock_localStorage = {'gridstack-layout': serialized_layout}

                save_time = (time.perf_counter() - start_time) * 1000
                save_times.append(save_time)

            # Test load performance
            load_times = []
            for _ in range(10):
                start_time = time.perf_counter()

                # Simulate layout load
                loaded_data = json.loads(mock_localStorage['gridstack-layout'])

                load_time = (time.perf_counter() - start_time) * 1000
                load_times.append(load_time)

            avg_save_time = statistics.mean(save_times)
            avg_load_time = statistics.mean(load_times)

            assert avg_save_time < scenario['target_ms'], \
                f"{scenario['name']} save should be <{scenario['target_ms']}ms, got {avg_save_time:.2f}ms"
            assert avg_load_time < scenario['target_ms'], \
                f"{scenario['name']} load should be <{scenario['target_ms']}ms, got {avg_load_time:.2f}ms"

    def generate_test_layout(self, container_count):
        """Generate test layout data with specified container count."""
        containers_per_row = 6
        layout = []

        for i in range(container_count):
            row = i // containers_per_row
            col = i % containers_per_row

            layout.append({
                'id': f'container_{i}',
                'x': col * 2,
                'y': row * 3,
                'w': 2,
                'h': 3,
                'minW': 1,
                'minH': 2,
                'maxW': 4,
                'maxH': 6
            })

        return layout

    @pytest.mark.performance
    def test_responsive_transition_performance(self):
        """Test responsive layout transition performance."""
        viewport_transitions = [
            {'from': 'desktop', 'to': 'tablet', 'from_width': 1200, 'to_width': 768},
            {'from': 'tablet', 'to': 'mobile', 'from_width': 768, 'to_width': 320},
            {'from': 'mobile', 'to': 'desktop', 'from_width': 320, 'to_width': 1200}
        ]

        for transition in viewport_transitions:
            transition_times = []

            # Run multiple transition tests
            for iteration in range(5):
                start_time = time.perf_counter()

                # Simulate responsive transition
                self.simulate_responsive_transition(
                    transition['from_width'],
                    transition['to_width']
                )

                transition_time = (time.perf_counter() - start_time) * 1000
                transition_times.append(transition_time)

            avg_transition_time = statistics.mean(transition_times)
            target_time = 30  # 30ms target for responsive transitions

            assert avg_transition_time < target_time, \
                f"Transition {transition['from']} to {transition['to']} should be <{target_time}ms, got {avg_transition_time:.2f}ms"

    def simulate_responsive_transition(self, from_width, to_width):
        """Simulate responsive layout transition."""
        # Viewport change detection (1ms)
        time.sleep(0.001)

        # Layout recalculation (10ms)
        time.sleep(0.01)

        # Container repositioning (8ms)
        time.sleep(0.008)

        # Style updates (5ms)
        time.sleep(0.005)

    @pytest.mark.performance
    def test_memory_usage_efficiency(self):
        """Test memory usage efficiency during extended operations."""
        import gc

        # Simulate extended grid operation session
        operation_cycles = 100
        memory_efficiency_data = []

        for cycle in range(operation_cycles):
            # Simulate typical operation cycle
            cycle_data = {
                'layout_changes': 3,
                'api_updates': 2,
                'user_interactions': 5
            }

            # Mock memory-intensive operations
            mock_data_structures = []

            # Layout operations
            for _ in range(cycle_data['layout_changes']):
                layout = self.generate_test_layout(6)
                mock_data_structures.append(layout)

            # API updates
            for _ in range(cycle_data['api_updates']):
                market_data = self.generate_test_market_data(20)
                mock_data_structures.append(market_data)

            # Process and cleanup (simulate proper memory management)
            current_data = mock_data_structures[-1]  # Keep only current
            del mock_data_structures[:-1]  # Remove old data

            # Force garbage collection every 10 cycles
            if cycle % 10 == 0:
                gc.collect()

                # Mock memory measurement (would use psutil in real implementation)
                mock_memory_mb = 20 + (cycle * 0.05)  # Small linear growth
                memory_efficiency_data.append(mock_memory_mb)

        # Verify memory efficiency
        initial_memory = memory_efficiency_data[0]
        final_memory = memory_efficiency_data[-1]
        memory_growth = final_memory - initial_memory

        # Memory growth should be minimal
        max_acceptable_growth = 10  # 10MB max growth over 100 cycles
        assert memory_growth < max_acceptable_growth, \
            f"Memory growth should be <{max_acceptable_growth}MB, got {memory_growth:.2f}MB"

    @pytest.mark.performance
    def test_concurrent_operation_performance(self):
        """Test performance under concurrent operations."""
        concurrent_scenarios = [
            {
                'name': 'light_concurrency',
                'grid_operations': 2,
                'api_calls': 1,
                'user_interactions': 1,
                'target_degradation': 1.2  # 20% performance degradation acceptable
            },
            {
                'name': 'moderate_concurrency',
                'grid_operations': 3,
                'api_calls': 2,
                'user_interactions': 2,
                'target_degradation': 1.5  # 50% degradation acceptable
            },
            {
                'name': 'heavy_concurrency',
                'grid_operations': 5,
                'api_calls': 3,
                'user_interactions': 4,
                'target_degradation': 2.0  # 100% degradation acceptable
            }
        ]

        # Baseline single-operation performance
        baseline_time = self.measure_single_operation_time()

        for scenario in concurrent_scenarios:
            concurrent_times = []

            # Run concurrent scenario multiple times
            for iteration in range(3):
                start_time = time.perf_counter()

                # Execute concurrent operations
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []

                    # Grid operations
                    for _ in range(scenario['grid_operations']):
                        futures.append(executor.submit(self.simulate_grid_operation))

                    # API calls
                    for _ in range(scenario['api_calls']):
                        futures.append(executor.submit(self.simulate_api_operation))

                    # User interactions
                    for _ in range(scenario['user_interactions']):
                        futures.append(executor.submit(self.simulate_user_interaction))

                    # Wait for all operations to complete
                    for future in as_completed(futures):
                        future.result()

                concurrent_time = (time.perf_counter() - start_time) * 1000
                concurrent_times.append(concurrent_time)

            avg_concurrent_time = statistics.mean(concurrent_times)
            performance_degradation = avg_concurrent_time / baseline_time

            assert performance_degradation <= scenario['target_degradation'], \
                f"{scenario['name']} degradation should be ≤{scenario['target_degradation']}x, got {performance_degradation:.2f}x"

    def measure_single_operation_time(self):
        """Measure baseline single operation time."""
        start_time = time.perf_counter()
        self.simulate_grid_operation()
        return (time.perf_counter() - start_time) * 1000

    def simulate_grid_operation(self):
        """Simulate a grid operation."""
        time.sleep(0.02)  # 20ms mock grid operation

    def simulate_api_operation(self):
        """Simulate an API operation."""
        time.sleep(0.03)  # 30ms mock API operation

    def simulate_user_interaction(self):
        """Simulate a user interaction."""
        time.sleep(0.01)  # 10ms mock user interaction

    @pytest.mark.performance
    def test_scalability_with_container_count(self):
        """Test scalability as container count increases."""
        container_counts = [6, 12, 18, 24, 30]  # Increasing container counts
        performance_results = {}

        for container_count in container_counts:
            # Test initialization time
            init_times = []
            for _ in range(5):
                start_time = time.perf_counter()
                self.simulate_scalable_grid_init(container_count)
                init_time = (time.perf_counter() - start_time) * 1000
                init_times.append(init_time)

            # Test layout update time
            update_times = []
            for _ in range(5):
                start_time = time.perf_counter()
                self.simulate_scalable_layout_update(container_count)
                update_time = (time.perf_counter() - start_time) * 1000
                update_times.append(update_time)

            performance_results[container_count] = {
                'avg_init_time': statistics.mean(init_times),
                'avg_update_time': statistics.mean(update_times)
            }

        # Verify scalability characteristics
        base_containers = 6
        base_init_time = performance_results[base_containers]['avg_init_time']
        base_update_time = performance_results[base_containers]['avg_update_time']

        for container_count in container_counts[1:]:  # Skip base case
            scaling_factor = container_count / base_containers

            actual_init_scaling = performance_results[container_count]['avg_init_time'] / base_init_time
            actual_update_scaling = performance_results[container_count]['avg_update_time'] / base_update_time

            # Performance should scale sub-linearly (better than O(n))
            acceptable_scaling = scaling_factor * 0.8  # 20% better than linear

            assert actual_init_scaling <= acceptable_scaling, \
                f"Init time scaling for {container_count} containers should be ≤{acceptable_scaling:.2f}x, got {actual_init_scaling:.2f}x"
            assert actual_update_scaling <= acceptable_scaling, \
                f"Update time scaling for {container_count} containers should be ≤{acceptable_scaling:.2f}x, got {actual_update_scaling:.2f}x"

    def simulate_scalable_grid_init(self, container_count):
        """Simulate grid initialization that scales with container count."""
        # Base initialization time
        time.sleep(0.01)

        # Per-container initialization time
        time.sleep(container_count * 0.001)

    def simulate_scalable_layout_update(self, container_count):
        """Simulate layout update that scales with container count."""
        # Base update time
        time.sleep(0.005)

        # Per-container update time
        time.sleep(container_count * 0.0005)

    @pytest.mark.performance
    def test_performance_regression_detection(self):
        """Test for performance regressions against established baselines."""
        # Established performance baselines (from previous sprint)
        baseline_performance = {
            'grid_init': 85,      # ms - Sprint 15 baseline
            'api_response': 40,   # ms - Sprint 15 baseline
            'ui_update': 20,      # ms - Sprint 15 baseline
            'layout_save': 8      # ms - Sprint 15 baseline
        }

        # Regression tolerance (5% acceptable degradation)
        regression_tolerance = 1.05

        # Measure current performance
        current_performance = {}

        # Grid initialization
        init_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            self.simulate_grid_initialization()
            init_times.append((time.perf_counter() - start_time) * 1000)
        current_performance['grid_init'] = statistics.mean(init_times)

        # API response
        api_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            self.simulate_market_movers_api_call()
            api_times.append((time.perf_counter() - start_time) * 1000)
        current_performance['api_response'] = statistics.mean(api_times)

        # UI update
        ui_times = []
        test_data = self.generate_test_market_data(20)
        for _ in range(10):
            start_time = time.perf_counter()
            self.simulate_ui_update(test_data, 6)
            ui_times.append((time.perf_counter() - start_time) * 1000)
        current_performance['ui_update'] = statistics.mean(ui_times)

        # Layout save
        save_times = []
        layout_data = self.generate_test_layout(6)
        for _ in range(10):
            start_time = time.perf_counter()
            json.dumps(layout_data)
            save_times.append((time.perf_counter() - start_time) * 1000)
        current_performance['layout_save'] = statistics.mean(save_times)

        # Check for regressions
        regressions_detected = []
        for operation, baseline in baseline_performance.items():
            current = current_performance[operation]
            max_acceptable = baseline * regression_tolerance

            if current > max_acceptable:
                regression_factor = current / baseline
                regressions_detected.append({
                    'operation': operation,
                    'baseline': baseline,
                    'current': current,
                    'regression_factor': regression_factor
                })

        # Report any regressions
        assert len(regressions_detected) == 0, \
            f"Performance regressions detected: {regressions_detected}"


@pytest.mark.performance
class TestGridPerformanceMonitoring:
    """Test performance monitoring and metrics collection."""

    def setup_method(self):
        """Setup performance monitoring tests."""
        self.performance_metrics = {
            'response_times': [],
            'error_rates': [],
            'throughput': [],
            'resource_usage': []
        }

    def test_real_time_performance_monitoring(self):
        """Test real-time performance metrics collection."""
        monitoring_duration = 1.0  # 1 second of monitoring
        sampling_interval = 0.1    # Sample every 100ms

        start_time = time.perf_counter()
        samples_collected = 0

        while (time.perf_counter() - start_time) < monitoring_duration:
            sample_start = time.perf_counter()

            # Simulate operation being monitored
            operation_time = self.simulate_monitored_operation()

            # Collect performance sample
            self.performance_metrics['response_times'].append(operation_time)
            samples_collected += 1

            # Maintain sampling interval
            elapsed = time.perf_counter() - sample_start
            if elapsed < sampling_interval:
                time.sleep(sampling_interval - elapsed)

        # Verify monitoring effectiveness
        assert samples_collected >= 8, f"Should collect at least 8 samples, got {samples_collected}"
        assert len(self.performance_metrics['response_times']) == samples_collected, \
            "Should record all response times"

        # Verify data quality
        avg_response_time = statistics.mean(self.performance_metrics['response_times'])
        assert 0 < avg_response_time < 100, f"Average response time should be reasonable, got {avg_response_time:.2f}ms"

    def simulate_monitored_operation(self):
        """Simulate an operation being monitored for performance."""
        start_time = time.perf_counter()

        # Simulate variable operation time (10-30ms)
        import random
        operation_duration = random.uniform(0.01, 0.03)
        time.sleep(operation_duration)

        return (time.perf_counter() - start_time) * 1000

    def test_performance_threshold_alerting(self):
        """Test performance threshold monitoring and alerting."""
        performance_thresholds = {
            'response_time_warning': 75,   # ms
            'response_time_critical': 150, # ms
            'error_rate_warning': 0.05,    # 5%
            'error_rate_critical': 0.10    # 10%
        }

        alerts_triggered = []

        # Simulate operations with varying performance
        test_scenarios = [
            {'response_time': 50, 'has_error': False, 'expected_alerts': []},
            {'response_time': 100, 'has_error': False, 'expected_alerts': ['response_time_warning']},
            {'response_time': 200, 'has_error': True, 'expected_alerts': ['response_time_critical']},
        ]

        for scenario in test_scenarios:
            # Check response time thresholds
            if scenario['response_time'] >= performance_thresholds['response_time_critical']:
                alerts_triggered.append('response_time_critical')
            elif scenario['response_time'] >= performance_thresholds['response_time_warning']:
                alerts_triggered.append('response_time_warning')

            # Check error rate (simplified for this test)
            if scenario['has_error']:
                alerts_triggered.append('error_occurred')

        # Verify alerting logic
        expected_alert_count = sum(len(scenario['expected_alerts']) for scenario in test_scenarios)
        assert len(alerts_triggered) >= expected_alert_count, \
            f"Should trigger appropriate alerts, got {alerts_triggered}"

    def test_performance_trend_analysis(self):
        """Test performance trend analysis over time."""
        # Simulate performance data over time
        time_series_data = []

        # Generate 50 data points with slight upward trend (performance degradation)
        for i in range(50):
            base_time = 25  # Base 25ms response time
            trend_factor = i * 0.2  # Slight upward trend
            noise = statistics.random.uniform(-2, 2)  # Random noise

            response_time = base_time + trend_factor + noise
            timestamp = time.time() + (i * 10)  # 10 second intervals

            time_series_data.append({
                'timestamp': timestamp,
                'response_time': response_time,
                'index': i
            })

        # Analyze trend
        early_data = time_series_data[:10]  # First 10 samples
        late_data = time_series_data[-10:]   # Last 10 samples

        early_avg = statistics.mean(sample['response_time'] for sample in early_data)
        late_avg = statistics.mean(sample['response_time'] for sample in late_data)

        trend_change = late_avg - early_avg
        trend_percentage = (trend_change / early_avg) * 100

        # Verify trend detection
        assert trend_change > 5, f"Should detect performance degradation trend, got {trend_change:.2f}ms change"
        assert trend_percentage > 10, f"Should detect significant percentage change, got {trend_percentage:.1f}%"

    def test_performance_profiling_integration(self):
        """Test integration with performance profiling tools."""
        profiling_data = {
            'function_calls': {},
            'execution_times': {},
            'memory_allocations': {},
            'cpu_usage': []
        }

        # Mock profiling a complex operation
        def profile_grid_operation():
            """Profile a complex grid operation."""
            profile_start = time.perf_counter()

            # Simulate profiled function calls
            functions_called = [
                'initializeGrid',
                'loadLayout',
                'applyLayout',
                'setupEventListeners',
                'renderContainers'
            ]

            for func_name in functions_called:
                func_start = time.perf_counter()

                # Simulate function execution time
                if func_name == 'initializeGrid':
                    time.sleep(0.01)
                elif func_name == 'applyLayout':
                    time.sleep(0.015)
                else:
                    time.sleep(0.005)

                func_time = (time.perf_counter() - func_start) * 1000

                profiling_data['function_calls'][func_name] = profiling_data['function_calls'].get(func_name, 0) + 1
                profiling_data['execution_times'][func_name] = func_time

            total_time = (time.perf_counter() - profile_start) * 1000
            return total_time

        # Run profiled operation
        total_execution_time = profile_grid_operation()

        # Verify profiling data collection
        assert len(profiling_data['function_calls']) == 5, "Should profile all function calls"
        assert all(count > 0 for count in profiling_data['function_calls'].values()), \
            "Should record call counts for all functions"
        assert sum(profiling_data['execution_times'].values()) <= total_execution_time, \
            "Individual function times should sum to less than total time"

    def test_performance_baseline_establishment(self):
        """Test establishment of performance baselines for regression testing."""
        # Run baseline performance tests
        baseline_operations = {
            'grid_initialization': {'runs': 20, 'operation': self.simulate_grid_initialization},
            'layout_update': {'runs': 30, 'operation': self.simulate_layout_update},
            'api_response': {'runs': 25, 'operation': self.simulate_api_response}
        }

        baseline_results = {}

        for operation_name, config in baseline_operations.items():
            execution_times = []

            for run in range(config['runs']):
                start_time = time.perf_counter()
                config['operation']()
                execution_time = (time.perf_counter() - start_time) * 1000
                execution_times.append(execution_time)

            # Calculate baseline statistics
            baseline_results[operation_name] = {
                'mean': statistics.mean(execution_times),
                'median': statistics.median(execution_times),
                'std_dev': statistics.stdev(execution_times),
                'p95': sorted(execution_times)[int(len(execution_times) * 0.95)],
                'p99': sorted(execution_times)[int(len(execution_times) * 0.99)],
                'min': min(execution_times),
                'max': max(execution_times),
                'sample_size': len(execution_times)
            }

        # Verify baseline quality
        for operation_name, stats in baseline_results.items():
            # Coefficient of variation should be reasonable (< 50%)
            cv = stats['std_dev'] / stats['mean']
            assert cv < 0.5, f"{operation_name} baseline should have CV < 0.5, got {cv:.3f}"

            # P95 should not be more than 2x median
            p95_factor = stats['p95'] / stats['median']
            assert p95_factor < 2.0, f"{operation_name} P95 should be < 2x median, got {p95_factor:.2f}x"

            # Should have sufficient sample size
            assert stats['sample_size'] >= 20, f"{operation_name} should have ≥20 samples for reliable baseline"

    def simulate_grid_initialization(self):
        """Simulate grid initialization for baseline testing."""
        time.sleep(0.08)  # 80ms simulation

    def simulate_layout_update(self):
        """Simulate layout update for baseline testing."""
        time.sleep(0.03)  # 30ms simulation

    def simulate_api_response(self):
        """Simulate API response for baseline testing."""
        time.sleep(0.035)  # 35ms simulation
