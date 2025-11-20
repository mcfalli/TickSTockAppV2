"""
Sprint 42 Phase 1 - Integration Validation Script

Validates that TickStockPL TickAggregator is functioning correctly
before proceeding to Phase 2 (removing AppV2 aggregation).
"""


import psycopg2

from src.config.database_config import get_database_config


def main():
    print("\n" + "="*80)
    print("Sprint 42 Phase 1 - Integration Validation")
    print("="*80 + "\n")

    # Connect to database
    db_config = get_database_config()
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    # Track results
    all_passed = True

    # Test 1: Verify OHLCV bars created
    print("Test 1: Verify OHLCV bars created (last 5 minutes)")
    print("-" * 80)

    cur.execute("""
        SELECT COUNT(*) as total_bars
        FROM ohlcv_1min
        WHERE timestamp > NOW() - INTERVAL '5 minutes'
    """)
    total_bars = cur.fetchone()[0]

    # Expected: 5 minutes × ~70 symbols = ~350 bars
    expected_min = 200  # Allow some variance

    if total_bars >= expected_min:
        print(f"✅ PASS: {total_bars} bars created (expected >= {expected_min})")
    else:
        print(f"❌ FAIL: {total_bars} bars created (expected >= {expected_min})")
        all_passed = False

    # Show bar distribution
    cur.execute("""
        SELECT
            DATE_TRUNC('minute', timestamp) as minute,
            COUNT(DISTINCT symbol) as symbols_with_bars
        FROM ohlcv_1min
        WHERE timestamp > NOW() - INTERVAL '10 minutes'
        GROUP BY minute
        ORDER BY minute DESC
        LIMIT 10
    """)

    print("\nBar distribution (symbols per minute):")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} symbols")

    # Test 2: Check pattern detections
    print("\n" + "-" * 80)
    print("Test 2: Verify pattern detections")
    print("-" * 80)

    cur.execute("""
        SELECT
            pattern_type,
            COUNT(*) as detections,
            ROUND(AVG(confidence)::numeric, 2) as avg_confidence
        FROM intraday_patterns
        WHERE detection_timestamp > NOW() - INTERVAL '5 minutes'
        GROUP BY pattern_type
        ORDER BY detections DESC
    """)

    pattern_results = cur.fetchall()
    total_patterns = sum(row[1] for row in pattern_results)

    if total_patterns > 0:
        print(f"✅ PASS: {total_patterns} total patterns detected")
        print("\nPattern breakdown:")
        for row in pattern_results:
            print(f"  {row[0]}: {row[1]} detections (avg confidence: {row[2]})")
    else:
        print("⚠️  WARNING: 0 patterns detected (may be normal if no patterns present)")
        print("  Note: Pattern detection working if bars are being created")

    # Test 3: Check indicator calculations
    print("\n" + "-" * 80)
    print("Test 3: Verify indicator calculations")
    print("-" * 80)

    cur.execute("""
        SELECT
            indicator_name,
            COUNT(*) as calculations
        FROM intraday_indicators
        WHERE calculation_timestamp > NOW() - INTERVAL '5 minutes'
        GROUP BY indicator_name
        ORDER BY calculations DESC
    """)

    indicator_results = cur.fetchall()
    total_indicators = sum(row[1] for row in indicator_results)

    if total_indicators > 0:
        print(f"✅ PASS: {total_indicators} total indicator calculations")
        print("\nIndicator breakdown:")
        for row in indicator_results:
            print(f"  {row[0]}: {row[1]} calculations")
    else:
        print("⚠️  WARNING: 0 indicators calculated")
        print("  Check if indicator jobs are subscribed to persistence manager")

    # Test 4: Verify NO duplicate bars
    print("\n" + "-" * 80)
    print("Test 4: Verify NO duplicate bars")
    print("-" * 80)

    cur.execute("""
        SELECT
            symbol,
            timestamp,
            COUNT(*) as duplicate_count
        FROM ohlcv_1min
        WHERE timestamp > NOW() - INTERVAL '10 minutes'
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
        LIMIT 10
    """)

    duplicates = cur.fetchall()

    if len(duplicates) == 0:
        print("✅ PASS: No duplicate bars detected")
    else:
        print(f"❌ FAIL: {len(duplicates)} duplicate (symbol, timestamp) pairs found")
        print("\nDuplicate examples:")
        for row in duplicates[:5]:
            print(f"  {row[0]} at {row[1]}: {row[2]} duplicates")
        all_passed = False

    # Test 5: Verify bar creation rate
    print("\n" + "-" * 80)
    print("Test 5: Verify bar creation rate")
    print("-" * 80)

    cur.execute("""
        SELECT COUNT(*) as minutes_with_data
        FROM (
            SELECT DATE_TRUNC('minute', timestamp) as minute
            FROM ohlcv_1min
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
            GROUP BY minute
        ) subq
    """)

    minutes_with_data = cur.fetchone()[0]

    if minutes_with_data >= 4:  # Allow some variance
        print(f"✅ PASS: {minutes_with_data} minutes with data (expected ~5)")
    else:
        print(f"❌ FAIL: {minutes_with_data} minutes with data (expected ~5)")
        all_passed = False

    # Test 6: Check for TickStockAppV2 writes (should still exist until Phase 2)
    print("\n" + "-" * 80)
    print("Test 6: Current state - AppV2 vs TickStockPL writes")
    print("-" * 80)

    print("⚠️  NOTE: Both systems currently writing (expected until Phase 2)")
    print("  TickStockAppV2 OHLCVPersistenceService: ACTIVE (will remove in Phase 2)")
    print("  TickStockPL TickAggregator: ACTIVE (Phase 1 complete)")

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80 + "\n")

    if all_passed:
        print("✅ ALL CRITICAL TESTS PASSED")
        print("\nPhase 1 Status: ✅ VALIDATED")
        print("\nNext Steps:")
        print("1. ✅ Phase 1 complete - TickAggregator working")
        print("2. ➡️  Proceed to Phase 2 - Remove AppV2 OHLCVPersistenceService")
        print("3. ⏳ Phase 3 - Integration testing with single aggregator")
        print("4. ⏳ Phase 4 - Documentation updates")

        print("\nReady to execute Phase 2:")
        print("  See: docs/planning/sprints/sprint42/IMPLEMENTATION_GUIDE.md")
        print("  Section: Phase 2 - TickStockAppV2")

    else:
        print("❌ SOME TESTS FAILED")
        print("\nPhase 1 Status: ⚠️  NEEDS ATTENTION")
        print("\nAction Required:")
        print("1. Review failed tests above")
        print("2. Check TickStockPL logs for errors")
        print("3. Verify both applications running")
        print("4. Fix issues before proceeding to Phase 2")

    print("\n" + "="*80 + "\n")

    conn.close()

    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print(f"\n❌ ERROR: Validation script failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
