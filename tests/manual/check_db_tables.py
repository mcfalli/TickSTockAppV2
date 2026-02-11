"""
Check what tables exist in the database.
"""
import sys
sys.path.insert(0, 'C:/Users/McDude/TickStockAppV2')

from src.infrastructure.database.tickstock_db import TickStockDatabase
from src.core.services.config_manager import get_config
from sqlalchemy import text

def main():
    print("\n" + "="*70)
    print("Checking Database Tables")
    print("="*70)

    try:
        config = get_config()
        db = TickStockDatabase(config)

        # Check database connection
        print("\n[1] Testing connection...")
        health = db.health_check()
        print(f"    Status: {health['status']}")
        print(f"    Database: {health.get('database', 'N/A')}")
        print(f"    Version: {health.get('version', 'N/A')}")

        # List all tables
        print("\n[2] Listing all tables in database...")
        query = text("""
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)

        with db.get_connection() as conn:
            result = conn.execute(query)
            tables = result.fetchall()

        if not tables:
            print("    No tables found in database")
        else:
            print(f"    Found {len(tables)} tables:")
            for schema, name, ttype in tables:
                print(f"        {schema}.{name} ({ttype})")

        # Check for stock price tables specifically
        print("\n[3] Checking for stock price tables...")
        stock_tables = [t for t in tables if 'stock' in t[1].lower() or 'price' in t[1].lower()]

        if not stock_tables:
            print("    No stock price tables found")
            print("    Expected tables: stock_prices_1day, stock_prices_1hour, stock_prices_1min")
        else:
            print(f"    Found {len(stock_tables)} stock-related tables:")
            for schema, name, ttype in stock_tables:
                print(f"        {schema}.{name}")

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
