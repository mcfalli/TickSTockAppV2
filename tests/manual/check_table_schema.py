"""
Check the schema of ohlcv_daily table.
"""
import sys
sys.path.insert(0, 'C:/Users/McDude/TickStockAppV2')

from src.infrastructure.database.tickstock_db import TickStockDatabase
from src.core.services.config_manager import get_config
from sqlalchemy import text

def main():
    print("\n" + "="*70)
    print("Checking ohlcv_daily Table Schema")
    print("="*70)

    try:
        config = get_config()
        db = TickStockDatabase(config)

        # Get column information for ohlcv_daily
        print("\n[1] Checking ohlcv_daily columns...")
        query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'ohlcv_daily'
            ORDER BY ordinal_position
        """)

        with db.get_connection() as conn:
            result = conn.execute(query)
            columns = result.fetchall()

        if not columns:
            print("    Table 'ohlcv_daily' not found")
        else:
            print(f"    Found {len(columns)} columns:")
            for col_name, data_type, nullable in columns:
                print(f"        {col_name:20s} {data_type:20s} {'NULL' if nullable == 'YES' else 'NOT NULL'}")

        # Check sample data
        print("\n[2] Checking sample data (first row)...")
        query = text("""
            SELECT *
            FROM ohlcv_daily
            LIMIT 1
        """)

        with db.get_connection() as conn:
            result = conn.execute(query)
            row = result.fetchone()

            if row:
                print("    Sample row:")
                for idx, col_name in enumerate(result.keys()):
                    print(f"        {col_name:20s} = {row[idx]}")
            else:
                print("    No data in table")

        print("\n" + "="*70)
        return True

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
