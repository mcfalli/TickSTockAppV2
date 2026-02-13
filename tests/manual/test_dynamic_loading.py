"""
Manual test for Sprint 74 dynamic loading.

Run: python tests/manual/test_dynamic_loading.py

Tests:
1. Load patterns from database
2. Load indicators from database
3. Verify enabled patterns/indicators
4. Test pattern/indicator instantiation
"""

import sys
import pandas as pd
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.dynamic_loader import get_dynamic_loader
from src.analysis.patterns.loader import get_available_patterns, load_pattern
from src.analysis.indicators.loader import get_available_indicators, load_indicator


def test_dynamic_pattern_loading():
    """Test dynamic pattern loading from database."""
    print("=" * 70)
    print("TEST 1: Dynamic Pattern Loading")
    print("=" * 70)

    try:
        # Get dynamic loader
        loader = get_dynamic_loader()

        # Load patterns for daily timeframe
        patterns = loader.load_patterns_for_timeframe('daily')

        print(f"\n[OK] Loaded {len(patterns)} patterns from database")

        # Display patterns
        for name, meta in patterns.items():
            print(f"  - {name}: {meta['class_name']} ({meta['category']})")

        return True

    except Exception as e:
        print(f"\n[ERROR] Pattern loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dynamic_indicator_loading():
    """Test dynamic indicator loading from database."""
    print("\n" + "=" * 70)
    print("TEST 2: Dynamic Indicator Loading")
    print("=" * 70)

    try:
        # Get dynamic loader
        loader = get_dynamic_loader()

        # Load indicators for daily timeframe
        indicators = loader.load_indicators_for_timeframe('daily')

        print(f"\n[OK] Loaded {len(indicators)} indicators from database")

        # Display indicators
        for name, meta in indicators.items():
            print(f"  - {name}: {meta['class_name']} ({meta['category']})")

        return True

    except Exception as e:
        print(f"\n[ERROR] Indicator loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_loader_integration():
    """Test pattern loader integration with dynamic loader."""
    print("\n" + "=" * 70)
    print("TEST 3: Pattern Loader Integration")
    print("=" * 70)

    try:
        # Get available patterns using loader function
        patterns = get_available_patterns('daily')

        print(f"\n[OK] get_available_patterns() returned {sum(len(v) for v in patterns.values())} patterns")

        for category, pattern_list in patterns.items():
            print(f"\n  {category.upper()}:")
            for pattern_name in pattern_list:
                print(f"    - {pattern_name}")

        # Load a specific pattern
        print("\n  Testing load_pattern('doji')...")
        doji = load_pattern('doji')
        print(f"    [OK] Loaded {doji.__class__.__name__}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Pattern loader integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_indicator_loader_integration():
    """Test indicator loader integration with dynamic loader."""
    print("\n" + "=" * 70)
    print("TEST 4: Indicator Loader Integration")
    print("=" * 70)

    try:
        # Get available indicators using loader function
        indicators = get_available_indicators('daily')

        print(f"\n[OK] get_available_indicators() returned {sum(len(v) for v in indicators.values())} indicators")

        for category, indicator_list in indicators.items():
            print(f"\n  {category.upper()}:")
            for indicator_name in indicator_list:
                print(f"    - {indicator_name}")

        # Load a specific indicator
        print("\n  Testing load_indicator('sma')...")
        sma = load_indicator('sma')
        print(f"    [OK] Loaded {sma.__class__.__name__}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Indicator loader integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_detection():
    """Test pattern detection with dynamically loaded pattern."""
    print("\n" + "=" * 70)
    print("TEST 5: Pattern Detection")
    print("=" * 70)

    try:
        # Create sample OHLC data
        data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [99, 100, 101],
            'close': [103, 104, 105],
            'volume': [1000, 1100, 1200],
        })

        # Load doji pattern
        doji = load_pattern('doji')

        # Detect pattern
        result = doji.detect(data)

        print(f"\n[OK] Pattern detection completed")
        print(f"  Result type: {type(result)}")
        print(f"  Result shape: {result.shape if hasattr(result, 'shape') else 'N/A'}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Pattern detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_indicator_calculation():
    """Test indicator calculation with dynamically loaded indicator."""
    print("\n" + "=" * 70)
    print("TEST 6: Indicator Calculation")
    print("=" * 70)

    try:
        # Create sample OHLC data
        data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115],
            'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            'close': [103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000],
        })

        # Load SMA indicator
        sma = load_indicator('sma')

        # Calculate indicator
        result = sma.calculate(data)

        print(f"\n[OK] Indicator calculation completed")
        print(f"  Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Indicator calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SPRINT 74: DYNAMIC LOADING MANUAL TESTS")
    print("=" * 70)
    print()

    tests = [
        test_dynamic_pattern_loading,
        test_dynamic_indicator_loading,
        test_pattern_loader_integration,
        test_indicator_loader_integration,
        test_pattern_detection,
        test_indicator_calculation,
    ]

    results = []
    for test_func in tests:
        result = test_func()
        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    for i, (test_func, result) in enumerate(zip(tests, results), 1):
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} Test {i}: {test_func.__name__}")

    print()

    return all(results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
