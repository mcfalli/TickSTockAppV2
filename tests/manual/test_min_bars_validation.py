"""
Test min_bars_required validation and new EMA/SMA indicators.
"""

import sys
import pandas as pd
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.patterns.pattern_detection_service import PatternDetectionService
from src.analysis.indicators.loader import IndicatorLoader
from src.analysis.exceptions import PatternDetectionError, AnalysisError


def test_min_bars_validation():
    """Test that min_bars_required validation works."""
    print("="*70)
    print("TEST: min_bars_required Validation")
    print("="*70)

    pattern_service = PatternDetectionService()
    indicator_loader = IndicatorLoader(timeframe='daily')

    # Test 1: Pattern with insufficient data
    print("\n1. Testing pattern with insufficient data...")

    # Create data with only 1 bar (morning_star needs 3)
    data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=1),
        'open': [100],
        'high': [105],
        'low': [95],
        'close': [102],
        'volume': [1000000],
    })

    try:
        result = pattern_service.detect_pattern(
            pattern_name='morning_star',
            data=data,
            timeframe='daily'
        )
        print("   [FAIL] Should have raised error for insufficient data")
        return False
    except PatternDetectionError as e:
        if "Insufficient data" in str(e) and "need 3" in str(e):
            print(f"   [OK] Correctly rejected: {e}")
        else:
            print(f"   [FAIL] Wrong error: {e}")
            return False

    # Test 2: Pattern with sufficient data
    print("\n2. Testing pattern with sufficient data...")

    data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=10),
        'open': range(100, 110),
        'high': range(105, 115),
        'low': range(95, 105),
        'close': range(102, 112),
        'volume': [1000000] * 10,
    })

    try:
        result = pattern_service.detect_pattern(
            pattern_name='doji',
            data=data,
            timeframe='daily'
        )
        print(f"   [OK] Pattern detection succeeded with {len(data)} bars")
    except Exception as e:
        print(f"   [FAIL] Unexpected error: {e}")
        return False

    # Test 3: Indicator with insufficient data (sma_200 needs 200 bars)
    print("\n3. Testing indicator with insufficient data...")

    data_short = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=50),
        'open': range(100, 150),
        'high': range(105, 155),
        'low': range(95, 145),
        'close': range(102, 152),
        'volume': [1000000] * 50,
    })

    try:
        indicator_meta = indicator_loader.get_indicator_metadata('sma_200')
        indicator = indicator_meta['instance']
        min_bars = indicator_meta.get('min_bars_required', 1)

        if len(data_short) < min_bars:
            print(f"   [OK] Validation would reject: have {len(data_short)} bars, need {min_bars}")
        else:
            print(f"   [FAIL] Should need more bars")
            return False
    except Exception as e:
        print(f"   [FAIL] Error loading indicator: {e}")
        return False

    # Test 4: New EMA/SMA indicators load correctly
    print("\n4. Testing new EMA/SMA indicators...")

    ema_periods = [5, 10, 20, 50, 100, 200]
    sma_periods = [5, 10, 20, 50, 100, 200]

    for period in ema_periods:
        try:
            indicator_meta = indicator_loader.get_indicator_metadata(f'ema_{period}')
            min_bars = indicator_meta.get('min_bars_required', 0)
            if min_bars == period:
                print(f"   [OK] ema_{period}: min_bars={min_bars}")
            else:
                print(f"   [FAIL] ema_{period}: expected min_bars={period}, got {min_bars}")
                return False
        except Exception as e:
            print(f"   [FAIL] ema_{period}: {e}")
            return False

    for period in sma_periods:
        try:
            indicator_meta = indicator_loader.get_indicator_metadata(f'sma_{period}')
            min_bars = indicator_meta.get('min_bars_required', 0)
            if min_bars == period:
                print(f"   [OK] sma_{period}: min_bars={min_bars}")
            else:
                print(f"   [FAIL] sma_{period}: expected min_bars={period}, got {min_bars}")
                return False
        except Exception as e:
            print(f"   [FAIL] sma_{period}: {e}")
            return False

    return True


def main():
    success = test_min_bars_validation()

    if success:
        print("\n" + "="*70)
        print("[SUCCESS] All validation tests PASSED")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("[FAIL] Some tests FAILED")
        print("="*70)

    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
