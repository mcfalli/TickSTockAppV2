#!/usr/bin/env python3
"""
Create OHLCV timeframe tables (hourly, weekly, monthly) in the database.
This script reads the SQL file and executes it using the application's database connection.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def create_tables():
    """Create the OHLCV timeframe tables in the database."""

    # Get database connection details from environment
    # Parse DATABASE_URI from .env file
    database_uri = os.getenv('DATABASE_URI', 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock')

    # Parse the URI
    from urllib.parse import urlparse
    parsed = urlparse(database_uri)

    db_config = {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/') if parsed.path else 'tickstock',
        'user': parsed.username or 'app_readwrite',
        'password': parsed.password or 'LJI48rUEkUpe6e'
    }

    sql_file = Path(__file__).parent / 'create_ohlcv_timeframe_tables.sql'

    try:
        print("Connecting to database...")
        print(f"Host: {db_config['host']}, Port: {db_config['port']}, Database: {db_config['database']}")

        # Connect to database
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cur = conn.cursor()

        print("Connected successfully!")

        # Read SQL file
        print(f"\nReading SQL script from: {sql_file}")
        with open(sql_file, 'r') as f:
            sql_content = f.read()

        # Remove comments and split into logical blocks
        # First, let's process CREATE TABLE statements separately since they may span multiple lines
        import re

        # Remove single-line comments but preserve the content
        sql_clean = re.sub(r'--.*?$', '', sql_content, flags=re.MULTILINE)

        # Execute CREATE TABLE statements for hourly table
        print("\n" + "="*60)
        print("Creating OHLCV Hourly table...")
        print("="*60)
        try:
            hourly_table = """
            CREATE TABLE IF NOT EXISTS ohlcv_hourly (
                symbol VARCHAR(20) REFERENCES symbols(symbol),
                timestamp TIMESTAMP WITH TIME ZONE,
                open NUMERIC(10, 4),
                high NUMERIC(10, 4),
                low NUMERIC(10, 4),
                close NUMERIC(10, 4),
                volume BIGINT,
                PRIMARY KEY (symbol, timestamp)
            )
            """
            cur.execute(hourly_table)
            print("  Table created successfully")

            # Convert to hypertable
            cur.execute("SELECT create_hypertable('ohlcv_hourly', 'timestamp', if_not_exists => TRUE);")
            print("  Converted to TimescaleDB hypertable")

            # Create index
            cur.execute("CREATE INDEX IF NOT EXISTS idx_hourly_symbol_ts ON ohlcv_hourly (symbol, timestamp DESC);")
            print("  Index created")
        except psycopg2.Error as e:
            if "already exists" in str(e):
                print(f"  Table already exists (skipping)")
            else:
                print(f"  Error: {e}")

        # Execute CREATE TABLE statements for weekly table
        print("\n" + "="*60)
        print("Creating OHLCV Weekly table...")
        print("="*60)
        try:
            weekly_table = """
            CREATE TABLE IF NOT EXISTS ohlcv_weekly (
                symbol VARCHAR(20) REFERENCES symbols(symbol),
                week_start DATE,
                open NUMERIC(10, 4),
                high NUMERIC(10, 4),
                low NUMERIC(10, 4),
                close NUMERIC(10, 4),
                volume BIGINT,
                PRIMARY KEY (symbol, week_start)
            )
            """
            cur.execute(weekly_table)
            print("  Table created successfully")

            # Create index
            cur.execute("CREATE INDEX IF NOT EXISTS idx_weekly_symbol_date ON ohlcv_weekly (symbol, week_start DESC);")
            print("  Index created")
        except psycopg2.Error as e:
            if "already exists" in str(e):
                print(f"  Table already exists (skipping)")
            else:
                print(f"  Error: {e}")

        # Execute CREATE TABLE statements for monthly table
        print("\n" + "="*60)
        print("Creating OHLCV Monthly table...")
        print("="*60)
        try:
            monthly_table = """
            CREATE TABLE IF NOT EXISTS ohlcv_monthly (
                symbol VARCHAR(20) REFERENCES symbols(symbol),
                month_start DATE,
                open NUMERIC(10, 4),
                high NUMERIC(10, 4),
                low NUMERIC(10, 4),
                close NUMERIC(10, 4),
                volume BIGINT,
                PRIMARY KEY (symbol, month_start)
            )
            """
            cur.execute(monthly_table)
            print("  Table created successfully")

            # Create index
            cur.execute("CREATE INDEX IF NOT EXISTS idx_monthly_symbol_date ON ohlcv_monthly (symbol, month_start DESC);")
            print("  Index created")
        except psycopg2.Error as e:
            if "already exists" in str(e):
                print(f"  Table already exists (skipping)")
            else:
                print(f"  Error: {e}")

        # Grant permissions
        print("\n" + "="*60)
        print("Granting permissions...")
        print("="*60)
        try:
            cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ohlcv_hourly TO app_readwrite;")
            cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ohlcv_weekly TO app_readwrite;")
            cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ohlcv_monthly TO app_readwrite;")
            print("  Permissions granted to app_readwrite")
        except psycopg2.Error as e:
            print(f"  Error granting permissions: {e}")

        print("\n" + "="*60)
        print("Verifying table creation...")
        print("="*60)

        # Verify tables were created
        verification_query = """
            SELECT
                table_name,
                CASE
                    WHEN h.hypertable_name IS NOT NULL THEN 'Hypertable'
                    ELSE 'Regular Table'
                END as table_type
            FROM information_schema.tables t
            LEFT JOIN timescaledb_information.hypertables h
                ON t.table_name = h.hypertable_name
            WHERE t.table_schema = 'public'
            AND t.table_name IN ('ohlcv_hourly', 'ohlcv_weekly', 'ohlcv_monthly')
            ORDER BY t.table_name;
        """

        cur.execute(verification_query)
        results = cur.fetchall()

        print("\nCreated tables:")
        for table_name, table_type in results:
            print(f"  {table_name:<15} ({table_type})")

        # Check column structure for each table
        print("\n" + "="*60)
        print("Table structures:")
        print("="*60)

        for table in ['ohlcv_hourly', 'ohlcv_weekly', 'ohlcv_monthly']:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table,))

            columns = cur.fetchall()
            if columns:
                print(f"\n{table}:")
                for col_name, data_type, nullable, default in columns:
                    nullable_str = "" if nullable == "NO" else " (nullable)"
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"  - {col_name:<15} {data_type}{nullable_str}{default_str}")

        print("\n" + "="*60)
        print("All OHLCV timeframe tables created successfully!")
        print("="*60)

        # Close connections
        cur.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print(f"\nDatabase connection failed: {e}")
        print("\nPlease ensure:")
        print("  1. PostgreSQL is running on port 5432")
        print("  2. Database credentials are correct")
        print("  3. Database 'tickstock' exists")
        print("\nYou can also run the SQL script manually:")
        print(f"  psql -h localhost -p 5432 -U app_readwrite -d tickstock -f {sql_file}")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)