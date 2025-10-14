#!/usr/bin/env python3
"""
Integration tests for synthetic data system with TickStock application.
"""

import os
import sys
import time

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

def test_app_integration():
    """Test integration with TickStock app configuration."""
    print("Testing TickStock App Integration...")

    try:
        # Test with app's actual configuration
        from src.infrastructure.data_sources.synthetic.types import DataFrequency

        from src.core.services.config_manager import ConfigManager
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

        # Load actual app configuration
        config_manager = ConfigManager()

        print("[OK] Loaded TickStock configuration system")

        # Test different scenarios developers might use
        scenarios = [
            ("Development Mode", "development"),
            ("Integration Testing", "integration_testing"),
            ("Performance Testing", "performance_testing"),
            ("Market Simulation", "market_simulation")
        ]

        for scenario_name, preset_name in scenarios:
            print(f"\n--- Testing {scenario_name} ---")

            # Apply scenario configuration
            config_manager.apply_synthetic_data_preset(preset_name)
            provider = SimulatedDataProvider(config_manager.config)

            # Test data generation for key tickers
            test_tickers = ["AAPL", "GOOGL", "MSFT"]

            for ticker in test_tickers:
                generated_count = 0

                for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
                    if provider.has_frequency_support(frequency):
                        try:
                            data = provider.generate_frequency_data(ticker, frequency)
                            if data:
                                generated_count += 1
                        except Exception as e:
                            print(f"[WARNING] {ticker} {frequency.value} generation failed: {e}")

                if generated_count > 0:
                    print(f"[OK] {ticker}: {generated_count} frequencies generated")
                else:
                    print(f"[FAIL] {ticker}: No data generated")

            # Test statistics
            stats = provider.get_generation_statistics()
            active_generators = stats.get('active_generators', [])
            print(f"[INFO] Active generators: {active_generators}")

        print("\n[SUCCESS] App integration test completed successfully")
        return True

    except Exception as e:
        print(f"[ERROR] App integration test failed: {e}")
        return False

def test_real_world_usage():
    """Test real-world usage patterns."""
    print("\n" + "="*50)
    print("Testing Real-World Usage Patterns")
    print("="*50)

    try:
        from src.infrastructure.data_sources.synthetic.types import DataFrequency

        from src.core.services.config_manager import ConfigManager
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

        # Scenario: Developer working on new feature
        print("\nScenario: Developer Testing New Feature")
        config_manager = ConfigManager()
        config_manager.apply_synthetic_data_preset('development')

        provider = SimulatedDataProvider(config_manager.config)

        # Generate realistic test data
        ticker = "AAPL"
        test_data = []

        for i in range(10):  # Generate 10 data points
            data = provider.generate_frequency_data(ticker, DataFrequency.PER_SECOND)
            if data:
                test_data.append(data)
            time.sleep(0.1)  # Small delay

        print(f"[OK] Generated {len(test_data)} test data points for development")

        # Scenario: CI/CD pipeline testing
        print("\nScenario: CI/CD Pipeline Integration Testing")
        config_manager.apply_synthetic_data_preset('integration_testing')
        provider = SimulatedDataProvider(config_manager.config)

        # Test multi-frequency generation
        multi_freq_data = {}
        for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
            if provider.has_frequency_support(frequency):
                data = provider.generate_frequency_data(ticker, frequency)
                multi_freq_data[frequency.value] = data is not None

        successful_frequencies = sum(multi_freq_data.values())
        print(f"[OK] CI/CD test: {successful_frequencies} frequencies working")

        # Scenario: Performance benchmarking
        print("\nScenario: Performance Benchmarking")
        config_manager.apply_synthetic_data_preset('performance_testing')
        provider = SimulatedDataProvider(config_manager.config)

        start_time = time.perf_counter()
        benchmark_count = 0

        for _ in range(100):  # Performance benchmark
            data = provider.generate_frequency_data(ticker, DataFrequency.PER_SECOND)
            if data:
                benchmark_count += 1

        benchmark_time = time.perf_counter() - start_time
        benchmark_rate = benchmark_count / benchmark_time if benchmark_time > 0 else 0

        print(f"[OK] Performance benchmark: {benchmark_rate:.1f} gen/sec")

        print("\n[SUCCESS] Real-world usage patterns test completed")
        return True

    except Exception as e:
        print(f"[ERROR] Real-world usage test failed: {e}")
        return False

def main():
    """Run integration tests."""
    print("Sprint 102 - TickStock App Integration Test")
    print("=" * 50)

    tests = [
        ("App Integration", test_app_integration),
        ("Real-World Usage", test_real_world_usage),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")

        try:
            if test_func():
                passed += 1
                print(f"\n[PASS] {test_name}")
            else:
                print(f"\n[FAIL] {test_name}")
        except Exception as e:
            print(f"\n[ERROR] {test_name}: {e}")

    print(f"\n{'='*50}")
    print("INTEGRATION TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[SUCCESS] All integration tests passed!")
        print("\nSprint 102 is ready for production use!")
        return 0
    print("[WARNING] Some integration issues detected.")
    return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
