"""
Sync Pattern and Indicator Definitions for Sprint 74

This script:
1. Updates existing patterns/indicators with correct TickStockAppV2 paths
2. Adds missing Sprint 68-70 patterns and indicators
3. Sets proper enabled status

Run: python scripts/sync_pattern_indicator_definitions.py
"""

from src.infrastructure.database.tickstock_db import TickStockDatabase
from src.core.services.config_manager import get_config
from sqlalchemy import text

def sync_definitions():
    """Sync pattern and indicator definitions in database."""

    config = get_config()
    db = TickStockDatabase(config)

    with db.get_connection() as conn:
        print("=" * 70)
        print("SYNCING PATTERN AND INDICATOR DEFINITIONS")
        print("=" * 70)
        print()

        # ================================================================
        # PART 1: Update existing patterns with correct paths
        # ================================================================
        print("Part 1: Updating existing pattern paths...")

        pattern_updates = [
            ('doji', 'Doji', 'src.analysis.patterns.candlestick.doji'),
            ('hammer', 'Hammer', 'src.analysis.patterns.candlestick.hammer'),
        ]

        for name, class_name, code_ref in pattern_updates:
            conn.execute(text("""
                UPDATE pattern_definitions
                SET code_reference = :code_ref,
                    class_name = :class_name,
                    name = :name
                WHERE name = :name OR name = :old_name
            """), {'name': name, 'class_name': class_name, 'code_ref': code_ref,
                   'old_name': name.capitalize()})
            print(f"  [OK] Updated {name} -> {code_ref}")

        # ================================================================
        # PART 2: Add missing Sprint 68-69 patterns
        # ================================================================
        print("\nPart 2: Adding missing Sprint 68-69 patterns...")

        new_patterns = [
            ('engulfing', 'Engulfing', 'EngulfingPattern',
             'src.analysis.patterns.candlestick.engulfing', 'candlestick', True, 2),
            ('shooting_star', 'Shooting Star', 'ShootingStarPattern',
             'src.analysis.patterns.candlestick.shooting_star', 'candlestick', True, 1),
            ('hanging_man', 'Hanging Man', 'HangingManPattern',
             'src.analysis.patterns.candlestick.hanging_man', 'candlestick', True, 1),
            ('harami', 'Harami', 'HaramiPattern',
             'src.analysis.patterns.candlestick.harami', 'candlestick', True, 2),
            ('morning_star', 'Morning Star', 'MorningStarPattern',
             'src.analysis.patterns.candlestick.morning_star', 'candlestick', True, 3),
            ('evening_star', 'Evening Star', 'EveningStarPattern',
             'src.analysis.patterns.candlestick.evening_star', 'candlestick', True, 3),
        ]

        for name, display_name, class_name, code_ref, category, enabled, min_bars in new_patterns:
            # Check if exists first
            result = conn.execute(text("""
                SELECT COUNT(*) FROM pattern_definitions WHERE name = :name
            """), {'name': name})

            if result.scalar() == 0:
                conn.execute(text("""
                    INSERT INTO pattern_definitions
                    (name, display_name, class_name, code_reference, category,
                     enabled, min_bars_required, short_description, created_date)
                    VALUES
                    (:name, :display_name, :class_name, :code_ref, :category,
                     :enabled, :min_bars, :desc, NOW())
                """), {
                    'name': name,
                    'display_name': display_name,
                    'class_name': class_name,
                    'code_ref': code_ref,
                    'category': category,
                    'enabled': enabled,
                    'min_bars': min_bars,
                    'desc': f'{display_name} candlestick pattern (Sprint 68-69)'
                })
                print(f"  [OK] Added {name} ({class_name})")
            else:
                print(f"  - Skipped {name} (already exists)")

        # ================================================================
        # PART 3: Update existing indicators with correct paths
        # ================================================================
        print("\nPart 3: Updating existing indicator paths...")

        indicator_updates = [
            ('rsi', 'RSI', 'src.analysis.indicators.rsi'),
            ('macd', 'MACD', 'src.analysis.indicators.macd'),
            ('sma', 'SMA', 'src.analysis.indicators.sma'),
        ]

        for name, class_name, code_ref in indicator_updates:
            conn.execute(text("""
                UPDATE indicator_definitions
                SET code_reference = :code_ref,
                    class_name = :class_name,
                    name = :name
                WHERE name = :name OR name = :old_name
            """), {'name': name, 'class_name': class_name, 'code_ref': code_ref,
                   'old_name': name.upper()})
            print(f"  [OK] Updated {name} -> {code_ref}")

        # ================================================================
        # PART 4: Add missing Sprint 70 indicators
        # ================================================================
        print("\nPart 4: Adding missing Sprint 70 indicators...")

        new_indicators = [
            ('ema', 'EMA', 'EMAIndicator',
             'src.analysis.indicators.trend.ema', 'trend', True, 20),
            ('stochastic', 'Stochastic', 'StochasticIndicator',
             'src.analysis.indicators.momentum.stochastic', 'momentum', True, 14),
            ('bollinger_bands', 'Bollinger Bands', 'BollingerBandsIndicator',
             'src.analysis.indicators.volatility.bollinger_bands', 'volatility', True, 20),
            ('atr', 'ATR', 'ATRIndicator',
             'src.analysis.indicators.volatility.atr', 'volatility', True, 14),
            ('adx', 'ADX', 'ADXIndicator',
             'src.analysis.indicators.directional.adx', 'directional', True, 14),
        ]

        for name, display_name, class_name, code_ref, category, enabled, min_bars in new_indicators:
            # Check if exists first
            result = conn.execute(text("""
                SELECT COUNT(*) FROM indicator_definitions WHERE name = :name
            """), {'name': name})

            if result.scalar() == 0:
                conn.execute(text("""
                    INSERT INTO indicator_definitions
                    (name, display_name, class_name, code_reference, category,
                     enabled, min_bars_required, short_description, created_date)
                    VALUES
                    (:name, :display_name, :class_name, :code_ref, :category,
                     :enabled, :min_bars, :desc, NOW())
                """), {
                    'name': name,
                    'display_name': display_name,
                    'class_name': class_name,
                    'code_ref': code_ref,
                    'category': category,
                    'enabled': enabled,
                    'min_bars': min_bars,
                    'desc': f'{display_name} technical indicator (Sprint 70)'
                })
                print(f"  [OK] Added {name} ({class_name})")
            else:
                print(f"  - Skipped {name} (already exists)")

        # ================================================================
        # PART 5: Disable test patterns/indicators
        # ================================================================
        print("\nPart 5: Disabling test patterns/indicators...")

        conn.execute(text("""
            UPDATE pattern_definitions
            SET enabled = false
            WHERE category = 'test' OR name IN ('AlwaysDetected', 'PriceChange', 'HeadShoulders')
        """))

        conn.execute(text("""
            UPDATE indicator_definitions
            SET enabled = false
            WHERE category = 'test' OR name = 'AlwaysTrue'
        """))

        print("  [OK] Disabled test patterns/indicators")

        # ================================================================
        # PART 6: Cleanup old/invalid indicators
        # ================================================================
        print("\nPart 6: Cleaning up old/invalid indicators...")

        # Disable indicators with old path patterns (src.indicators.*)
        conn.execute(text("""
            UPDATE indicator_definitions
            SET enabled = false
            WHERE code_reference LIKE 'src.indicators.%'
        """))

        print("  [OK] Disabled old indicators with src.indicators.* paths")

        # Commit all changes
        conn.commit()

        # ================================================================
        # PART 7: Verification
        # ================================================================
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        # Count enabled patterns
        result = conn.execute(text("""
            SELECT category, COUNT(*) as count
            FROM pattern_definitions
            WHERE enabled = true
            GROUP BY category
            ORDER BY category
        """))

        print("\nEnabled Patterns by Category:")
        total_patterns = 0
        for row in result:
            print(f"  {row[0]}: {row[1]} patterns")
            total_patterns += row[1]
        print(f"  TOTAL: {total_patterns} patterns")

        # Count enabled indicators
        result = conn.execute(text("""
            SELECT category, COUNT(*) as count
            FROM indicator_definitions
            WHERE enabled = true
            GROUP BY category
            ORDER BY category
        """))

        print("\nEnabled Indicators by Category:")
        total_indicators = 0
        for row in result:
            print(f"  {row[0]}: {row[1]} indicators")
            total_indicators += row[1]
        print(f"  TOTAL: {total_indicators} indicators")

        print("\n" + "=" * 70)
        print("[SUCCESS] SYNC COMPLETE")
        print("=" * 70)
        print(f"\nSummary:")
        print(f"  - {total_patterns} patterns enabled")
        print(f"  - {total_indicators} indicators enabled")
        print(f"  - All Sprint 68-70 patterns/indicators added")
        print(f"  - Test patterns/indicators disabled")
        print()


if __name__ == '__main__':
    try:
        sync_definitions()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        exit(1)
