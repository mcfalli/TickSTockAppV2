"""
Test script to verify database write functionality for OHLCV 1-minute data.

Sprint 54: WebSocket Processing Simplification
Tests the new write_ohlcv_1min() method added to TickStockDatabase.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.services.config_manager import get_config
from src.infrastructure.database.tickstock_db import TickStockDatabase


def test_database_write():
    """Test writing OHLCV data to the database."""
    print("=" * 80)
    print("Testing Database Write Functionality")
    print("=" * 80)

    try:
        # Initialize database connection
        print("\n1. Initializing database connection...")
        config = get_config()
        db = TickStockDatabase(config)
        print("   [OK] Database connection initialized")

        # Create test data (use existing symbol to satisfy FK constraint)
        test_symbol = "AAPL"
        test_timestamp = datetime.now(timezone.utc)
        test_open = Decimal("150.25")
        test_high = Decimal("151.50")
        test_low = Decimal("149.75")
        test_close = Decimal("150.80")
        test_volume = 1000000

        print(f"\n2. Writing test OHLCV record...")
        print(f"   Symbol: {test_symbol}")
        print(f"   Timestamp: {test_timestamp}")
        print(f"   OHLCV: O={test_open} H={test_high} L={test_low} C={test_close} V={test_volume}")

        # Write to database
        success = db.write_ohlcv_1min(
            symbol=test_symbol,
            timestamp=test_timestamp,
            open_price=test_open,
            high_price=test_high,
            low_price=test_low,
            close_price=test_close,
            volume=test_volume
        )

        if success:
            print("   [OK] Write successful")
        else:
            print("   [FAIL] Write failed")
            return False

        # Verify the write by reading it back
        print(f"\n3. Verifying write by reading back...")
        with db.get_connection() as conn:
            from sqlalchemy import text
            query = text("""
                SELECT symbol, timestamp, open, high, low, close, volume
                FROM ohlcv_1min
                WHERE symbol = :symbol
                AND timestamp = :timestamp
            """)
            result = conn.execute(query, {
                'symbol': test_symbol,
                'timestamp': test_timestamp
            })
            row = result.fetchone()

        if row:
            print("   [OK] Record found in database")
            print(f"   Retrieved: {row[0]} @ {row[1]}")
            print(f"   OHLCV: O={row[2]} H={row[3]} L={row[4]} C={row[5]} V={row[6]}")

            # Verify values match (compare as Decimal for precision)
            assert Decimal(str(row[2])) == test_open, f"Open price mismatch: {row[2]} != {test_open}"
            assert Decimal(str(row[3])) == test_high, f"High price mismatch: {row[3]} != {test_high}"
            assert Decimal(str(row[4])) == test_low, f"Low price mismatch: {row[4]} != {test_low}"
            assert Decimal(str(row[5])) == test_close, f"Close price mismatch: {row[5]} != {test_close}"
            assert row[6] == test_volume, f"Volume mismatch: {row[6]} != {test_volume}"
            print("   [OK] All values match")
        else:
            print("   [FAIL] Record not found in database")
            return False

        # Test upsert functionality (write same record again with different values)
        print(f"\n4. Testing upsert (ON CONFLICT DO UPDATE)...")
        updated_close = Decimal("151.25")
        updated_volume = 1500000

        success = db.write_ohlcv_1min(
            symbol=test_symbol,
            timestamp=test_timestamp,
            open_price=test_open,
            high_price=test_high,
            low_price=test_low,
            close_price=updated_close,
            volume=updated_volume
        )

        if success:
            print("   [OK] Upsert successful")
        else:
            print("   [FAIL] Upsert failed")
            return False

        # Verify the upsert
        print(f"\n5. Verifying upsert...")
        with db.get_connection() as conn:
            result = conn.execute(query, {
                'symbol': test_symbol,
                'timestamp': test_timestamp
            })
            row = result.fetchone()

        if row:
            print(f"   Retrieved: C={row[5]} V={row[6]}")
            assert Decimal(str(row[5])) == updated_close, f"Close price not updated: {row[5]} != {updated_close}"
            assert row[6] == updated_volume, f"Volume not updated: {row[6]} != {updated_volume}"
            print("   [OK] Upsert values updated correctly")
        else:
            print("   [FAIL] Record not found after upsert")
            return False

        # Clean up test data
        print(f"\n6. Cleaning up test data...")
        with db.get_connection() as conn:
            delete_query = text("DELETE FROM ohlcv_1min WHERE symbol = :symbol AND timestamp = :timestamp")
            conn.execute(delete_query, {'symbol': test_symbol, 'timestamp': test_timestamp})
            conn.commit()
        print("   [OK] Test data cleaned up")

        print("\n" + "=" * 80)
        print("[PASS] ALL TESTS PASSED - Database write functionality working correctly")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_database_write()
    sys.exit(0 if success else 1)
