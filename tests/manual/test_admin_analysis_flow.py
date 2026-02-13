"""
Test Admin Process Analysis flow with dynamic loading.

This test mimics the exact code path used by /admin/process-analysis
to ensure PatternDetectionService works with dynamic loader.
"""

import sys
import pandas as pd
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.services.analysis_service import AnalysisService
from src.analysis.patterns.pattern_detection_service import PatternDetectionService
from src.analysis.indicators.loader import IndicatorLoader


def test_admin_analysis_flow():
    """Test the exact flow used by admin process analysis."""
    print("=" * 70)
    print("TEST: Admin Process Analysis Flow")
    print("=" * 70)

    try:
        # Create services (same as admin process analysis)
        timeframe = 'daily'
        analysis_service = AnalysisService()
        pattern_service = analysis_service.pattern_service

        print(f"\n[OK] Services initialized")

        # Create sample OHLC data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100),
            'open': range(100, 200),
            'high': range(105, 205),
            'low': range(95, 195),
            'close': range(102, 202),
            'volume': [1000000] * 100,
        })

        print(f"[OK] Created test data with {len(data)} bars")

        # Test pattern detection (this is where the error occurred)
        print("\nTesting pattern detection...")

        result = pattern_service.detect_pattern(
            pattern_name='doji',
            data=data,
            timeframe=timeframe
        )

        print(f"[OK] Pattern detection succeeded")
        print(f"  Pattern: doji")
        print(f"  Result type: {type(result)}")
        print(f"  Detected: {result.get('detected', 'N/A')}")

        # Test with multiple patterns (like admin does)
        print("\nTesting multiple patterns...")
        patterns = ['doji', 'hammer', 'engulfing']

        for pattern_name in patterns:
            result = pattern_service.detect_pattern(
                pattern_name=pattern_name,
                data=data,
                timeframe=timeframe
            )
            print(f"  [OK] {pattern_name}: detected={result.get('detected', False)}")

        # Test full analysis service (like admin process analysis calls)
        print("\nTesting full analysis service...")

        analysis_result = analysis_service.analyze_symbol(
            symbol='TEST',
            data=data,
            patterns=['doji', 'hammer'],
            indicators=['sma', 'rsi'],
            timeframe=timeframe,
            calculate_all=False
        )

        print(f"[OK] Full analysis succeeded")
        print(f"  Patterns detected: {len(analysis_result.get('patterns', {}))}")
        print(f"  Indicators calculated: {len(analysis_result.get('indicators', {}))}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    success = test_admin_analysis_flow()

    if success:
        print("\n" + "=" * 70)
        print("[SUCCESS] Admin analysis flow test PASSED")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("[FAIL] Admin analysis flow test FAILED")
        print("=" * 70)

    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
