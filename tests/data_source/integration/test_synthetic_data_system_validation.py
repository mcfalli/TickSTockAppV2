#!/usr/bin/env python3
"""
System validation tests for multi-frequency synthetic data system.
Windows-compatible version without unicode characters.
"""

import sys
import os
import time
from typing import Dict, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

def test_basic_functionality():
    """Test basic functionality of the multi-frequency system."""
    print("Testing basic functionality...")
    
    try:
        # Test imports
        from src.infrastructure.data_sources.synthetic.types import DataFrequency
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
        from src.core.services.config_manager import ConfigManager
        print("[OK] Imports successful")
        
        # Test configuration
        config_manager = ConfigManager()
        presets = config_manager.get_synthetic_data_presets()
        print(f"[OK] Found {len(presets)} configuration presets")
        
        # Apply development preset
        success = config_manager.apply_synthetic_data_preset('development')
        print(f"[OK] Applied development preset: {success}")
        
        # Create provider
        provider = SimulatedDataProvider(config_manager.config)
        supported_frequencies = provider.get_supported_frequencies()
        print(f"[OK] Provider supports {len(supported_frequencies)} frequencies")
        
        # Test data generation
        ticker = "AAPL"
        generation_results = {}
        
        for frequency in [DataFrequency.PER_SECOND, DataFrequency.PER_MINUTE, DataFrequency.FAIR_VALUE]:
            if provider.has_frequency_support(frequency):
                try:
                    data = provider.generate_frequency_data(ticker, frequency)
                    success = data is not None
                    generation_results[frequency.value] = success
                    status = "SUCCESS" if success else "FAILED"
                    print(f"[{status}] {frequency.value} generation")
                except Exception as e:
                    generation_results[frequency.value] = False
                    print(f"[ERROR] {frequency.value} generation: {e}")
            else:
                print(f"[SKIP] {frequency.value} not supported")
        
        successful_generations = sum(generation_results.values())
        print(f"[RESULT] {successful_generations} frequency types generated successfully")
        
        return successful_generations > 0
        
    except Exception as e:
        print(f"[CRITICAL ERROR] Basic functionality test failed: {e}")
        return False

def test_performance():
    """Test basic performance."""
    print("\nTesting performance...")
    
    try:
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
        from src.infrastructure.data_sources.synthetic.types import DataFrequency
        from src.core.services.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        config_manager.apply_synthetic_data_preset('performance_testing')
        
        provider = SimulatedDataProvider(config_manager.config)
        ticker = "AAPL"
        
        # Performance test
        start_time = time.perf_counter()
        successful_generations = 0
        
        for _ in range(50):  # Reduced for quick test
            try:
                data = provider.generate_frequency_data(ticker, DataFrequency.PER_SECOND)
                if data:
                    successful_generations += 1
            except Exception:
                continue
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        rate = successful_generations / duration if duration > 0 else 0
        
        print(f"[PERF] Generated {successful_generations} ticks in {duration:.3f}s")
        print(f"[PERF] Rate: {rate:.1f} generations/second")
        
        performance_ok = rate > 5  # Lower threshold for quick test
        status = "OK" if performance_ok else "SLOW"
        print(f"[{status}] Performance test")
        
        return performance_ok
        
    except Exception as e:
        print(f"[ERROR] Performance test failed: {e}")
        return False

def test_configuration_presets():
    """Test all configuration presets."""
    print("\nTesting configuration presets...")
    
    try:
        from src.core.services.config_manager import ConfigManager
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
        
        config_manager = ConfigManager()
        presets = config_manager.get_synthetic_data_presets()
        
        successful_presets = 0
        
        for preset_name in presets.keys():
            try:
                # Apply preset
                success = config_manager.apply_synthetic_data_preset(preset_name)
                if not success:
                    print(f"[FAIL] Could not apply preset: {preset_name}")
                    continue
                
                # Validate configuration
                is_valid, errors = config_manager.validate_synthetic_data_config()
                if not is_valid:
                    print(f"[FAIL] Invalid config for preset {preset_name}: {errors[:3]}")
                    continue
                
                # Try to create provider
                provider = SimulatedDataProvider(config_manager.config)
                supported = provider.get_supported_frequencies()
                
                print(f"[OK] Preset '{preset_name}': {len(supported)} frequencies")
                successful_presets += 1
                
            except Exception as e:
                print(f"[ERROR] Preset '{preset_name}' failed: {e}")
        
        print(f"[RESULT] {successful_presets}/{len(presets)} presets working")
        return successful_presets >= len(presets) * 0.8  # 80% success threshold
        
    except Exception as e:
        print(f"[ERROR] Preset test failed: {e}")
        return False

def main():
    """Run simple tests."""
    print("Sprint 102 Multi-Frequency Synthetic Data - Simple Test")
    print("=" * 60)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Performance", test_performance),
        ("Configuration Presets", test_configuration_presets),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"[PASS] {test_name}")
            else:
                print(f"[FAIL] {test_name}")
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY: {passed}/{total} passed ({passed/total:.1%})")
    
    if passed == total:
        print("[SUCCESS] All tests passed! System is working.")
        return 0
    elif passed >= total * 0.7:
        print("[WARNING] Most tests passed, some issues detected.")
        return 1
    else:
        print("[CRITICAL] Multiple test failures.")
        return 2

if __name__ == "__main__":
    exit_code = main()
    print(f"\nTest completed with exit code: {exit_code}")
    sys.exit(exit_code)