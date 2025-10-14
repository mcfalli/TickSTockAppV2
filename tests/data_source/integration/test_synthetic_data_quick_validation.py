#!/usr/bin/env python3
"""
Quick validation tests for multi-frequency synthetic data system.
Run this to verify the implementation works correctly.
"""

import os
import sys
import time

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

def test_imports():
    """Test that all components can be imported."""
    print("🔍 Testing imports...")

    try:
        from src.infrastructure.data_sources.synthetic.types import (
            DataFrequency,
            FrequencyGenerator,
        )

        from src.core.services.config_manager import ConfigManager
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration_system():
    """Test the configuration system and presets."""
    print("\n🔍 Testing configuration system...")

    try:
        from src.core.services.config_manager import ConfigManager

        config_manager = ConfigManager()

        # Test getting synthetic data configuration
        config = config_manager.get_synthetic_data_config()
        print(f"✅ Retrieved synthetic data config with {len(config)} settings")

        # Test getting presets
        presets = config_manager.get_synthetic_data_presets()
        print(f"✅ Found {len(presets)} configuration presets: {list(presets.keys())}")

        # Test applying a preset
        success = config_manager.apply_synthetic_data_preset('development')
        print(f"✅ Applied development preset: {success}")

        # Test configuration validation
        is_valid, errors = config_manager.validate_synthetic_data_config()
        print(f"✅ Configuration validation: {is_valid} (errors: {len(errors)})")

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_provider_initialization():
    """Test SimulatedDataProvider initialization."""
    print("\n🔍 Testing provider initialization...")

    try:
        from src.infrastructure.data_sources.synthetic.types import DataFrequency

        from src.core.services.config_manager import ConfigManager
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

        # Use development preset for testing
        config_manager = ConfigManager()
        config_manager.apply_synthetic_data_preset('development')

        provider = SimulatedDataProvider(config_manager.config)

        # Check supported frequencies
        supported = provider.get_supported_frequencies()
        print(f"✅ Provider supports {len(supported)} frequencies: {[f.value for f in supported]}")

        # Check frequency support
        for freq in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
            has_support = provider.has_frequency_support(freq)
            print(f"  {freq.value}: {'✅' if has_support else '❌'}")

        return True

    except Exception as e:
        print(f"❌ Provider initialization failed: {e}")
        return False

def test_data_generation():
    """Test actual data generation."""
    print("\n🔍 Testing data generation...")

    try:
        from src.infrastructure.data_sources.synthetic.types import DataFrequency

        from src.core.services.config_manager import ConfigManager
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

        config_manager = ConfigManager()
        config_manager.apply_synthetic_data_preset('integration_testing')

        provider = SimulatedDataProvider(config_manager.config)

        ticker = "AAPL"
        generation_results = {}

        # Test each frequency
        for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
            if provider.has_frequency_support(frequency):
                try:
                    data = provider.generate_frequency_data(ticker, frequency)
                    generation_results[frequency.value] = {
                        'success': data is not None,
                        'type': type(data).__name__ if data else 'None',
                        'has_ticker': hasattr(data, 'ticker') or (isinstance(data, dict) and 'sym' in data) if data else False
                    }
                    print(f"✅ {frequency.value}: Generated {type(data).__name__}")
                except Exception as e:
                    generation_results[frequency.value] = {'success': False, 'error': str(e)}
                    print(f"❌ {frequency.value}: Generation failed - {e}")
            else:
                generation_results[frequency.value] = {'success': False, 'error': 'Not supported'}
                print(f"⚠️  {frequency.value}: Not supported")

        # Check statistics
        stats = provider.get_generation_statistics()
        print(f"✅ Generation statistics: {stats.get('active_generators', [])}")

        successful_generations = sum(1 for result in generation_results.values() if result.get('success', False))
        print(f"✅ Successfully generated data for {successful_generations} frequencies")

        return successful_generations > 0

    except Exception as e:
        print(f"❌ Data generation test failed: {e}")
        return False

def test_performance_basic():
    """Basic performance test."""
    print("\n🔍 Testing basic performance...")

    try:
        from src.infrastructure.data_sources.synthetic.types import DataFrequency

        from src.core.services.config_manager import ConfigManager
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

        config_manager = ConfigManager()
        config_manager.apply_synthetic_data_preset('performance_testing')

        provider = SimulatedDataProvider(config_manager.config)

        # Test per-second generation speed
        ticker = "AAPL"
        test_iterations = 100

        start_time = time.perf_counter()
        successful_generations = 0

        for _ in range(test_iterations):
            try:
                data = provider.generate_frequency_data(ticker, DataFrequency.PER_SECOND)
                if data:
                    successful_generations += 1
            except Exception:
                continue

        end_time = time.perf_counter()
        duration = end_time - start_time
        rate = successful_generations / duration if duration > 0 else 0

        print(f"✅ Generated {successful_generations}/{test_iterations} ticks in {duration:.3f}s")
        print(f"✅ Performance: {rate:.1f} generations/second")

        # Performance should be reasonable (>10 gen/sec for basic test)
        performance_ok = rate > 10
        print(f"{'✅' if performance_ok else '⚠️'} Performance {'acceptable' if performance_ok else 'needs attention'}")

        return performance_ok

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def test_validation_system():
    """Test the data validation system."""
    print("\n🔍 Testing validation system...")

    try:
        from src.infrastructure.data_sources.synthetic.types import DataFrequency

        from src.core.services.config_manager import ConfigManager
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

        config_manager = ConfigManager()
        # Use a preset with validation enabled
        config_manager.apply_synthetic_data_preset('integration_testing')

        provider = SimulatedDataProvider(config_manager.config)

        # Check if validation is enabled
        has_validator = provider._validator is not None
        print(f"✅ Validation system {'enabled' if has_validator else 'disabled'}")

        if has_validator:
            # Generate some data to test validation
            ticker = "AAPL"

            # Generate per-second data
            if provider.has_frequency_support(DataFrequency.PER_SECOND):
                tick_data = provider.generate_frequency_data(ticker, DataFrequency.PER_SECOND)
                if tick_data:
                    provider._validator.add_tick_data(ticker, tick_data)
                    print("✅ Added tick data to validator")

            # Generate per-minute data and validate
            if provider.has_frequency_support(DataFrequency.PER_MINUTE):
                minute_data = provider.generate_frequency_data(ticker, DataFrequency.PER_MINUTE)
                if minute_data:
                    provider._validator.add_minute_bar(ticker, minute_data)
                    validation_result = provider._validator.validate_minute_bar_consistency(ticker, minute_data)
                    print(f"✅ Minute bar validation: {'PASS' if validation_result.is_valid else 'FAIL'}")
                    if not validation_result.is_valid:
                        print(f"  Errors: {validation_result.errors[:3]}...")  # Show first 3 errors

            # Get validation summary
            summary = provider.get_validation_summary()
            if summary:
                print(f"✅ Validation summary: {summary.get('total_validations', 0)} total, "
                      f"{summary.get('success_rate', 0):.1%} success rate")

        return True

    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Sprint 102 Multi-Frequency Synthetic Data System - Quick Test")
    print("=" * 70)

    tests = [
        ("Import Test", test_imports),
        ("Configuration System", test_configuration_system),
        ("Provider Initialization", test_provider_initialization),
        ("Data Generation", test_data_generation),
        ("Basic Performance", test_performance_basic),
        ("Validation System", test_validation_system),
    ]

    passed_tests = 0
    total_tests = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")

        try:
            if test_func():
                passed_tests += 1
                print(f"[PASS] {test_name}: PASSED")
            else:
                print(f"[FAIL] {test_name}: FAILED")
        except Exception as e:
            print(f"[ERROR] {test_name}: ERROR - {e}")

    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {passed_tests/total_tests:.1%}")

    if passed_tests == total_tests:
        print("[SUCCESS] ALL TESTS PASSED! Sprint 102 system is working correctly.")
        return 0
    if passed_tests >= total_tests * 0.8:
        print("[WARNING] MOSTLY WORKING - Some issues need attention.")
        return 1
    print("[CRITICAL] SIGNIFICANT ISSUES - System needs debugging.")
    return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
