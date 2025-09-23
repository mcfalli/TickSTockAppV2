#!/usr/bin/env python3
"""
Analyze all tables in the database to document their structure.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def analyze_all_tables():
    """Analyze all tables in the database."""

    # Parse DATABASE_URI from .env file
    database_uri = os.getenv('DATABASE_URI', 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock')
    parsed = urlparse(database_uri)

    db_config = {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/') if parsed.path else 'tickstock',
        'user': parsed.username or 'app_readwrite',
        'password': parsed.password or 'LJI48rUEkUpe6e'
    }

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        print("Connected successfully!\n")

        # Get all tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)

        all_tables = [row[0] for row in cur.fetchall()]

        print(f"Found {len(all_tables)} tables in database\n")
        print("="*80)

        # Categorize tables
        categories = {
            'OHLCV Data Tables': [],
            'Symbol & Universe Tables': [],
            'Pattern Tables': [],
            'Indicator Tables': [],
            'Analytics Tables': [],
            'Backtesting Tables': [],
            'User & Preferences Tables': [],
            'System & Monitoring Tables': [],
            'Integration Tables': [],
            'Market Context Tables': [],
            'Unknown/Other Tables': []
        }

        # Categorize each table
        for table_name in all_tables:
            if 'ohlcv' in table_name:
                categories['OHLCV Data Tables'].append(table_name)
            elif 'symbol' in table_name or 'universe' in table_name or 'cache_entries' in table_name:
                categories['Symbol & Universe Tables'].append(table_name)
            elif 'pattern' in table_name:
                categories['Pattern Tables'].append(table_name)
            elif 'indicator' in table_name:
                categories['Indicator Tables'].append(table_name)
            elif 'analytics' in table_name or 'correlation' in table_name:
                categories['Analytics Tables'].append(table_name)
            elif 'backtest' in table_name:
                categories['Backtesting Tables'].append(table_name)
            elif 'user' in table_name or 'preference' in table_name or 'alert' in table_name:
                categories['User & Preferences Tables'].append(table_name)
            elif 'integration' in table_name or 'heartbeat' in table_name:
                categories['Integration Tables'].append(table_name)
            elif 'market' in table_name:
                categories['Market Context Tables'].append(table_name)
            else:
                categories['Unknown/Other Tables'].append(table_name)

        # Output results
        for category, tables in categories.items():
            if tables:
                print(f"\n### {category}")
                print("-"*60)

                for table_name in sorted(tables):
                    print(f"\n**{table_name}**")

                    # Get table comment
                    cur.execute("""
                        SELECT obj_description(c.oid)
                        FROM pg_class c
                        WHERE c.relname = %s
                        AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
                    """, (table_name,))

                    comment = cur.fetchone()
                    if comment and comment[0]:
                        print(f"Purpose: {comment[0]}")

                    # Get columns
                    cur.execute("""
                        SELECT
                            column_name,
                            data_type,
                            character_maximum_length,
                            is_nullable,
                            column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = %s
                        ORDER BY ordinal_position;
                    """, (table_name,))

                    columns = cur.fetchall()

                    print("Fields:")
                    for col_name, data_type, max_len, nullable, default in columns:
                        # Format data type
                        if max_len:
                            type_str = f"{data_type}({max_len})"
                        elif data_type == 'numeric' or data_type == 'double precision':
                            type_str = data_type
                        elif data_type == 'timestamp with time zone':
                            type_str = 'timestamptz'
                        elif data_type == 'timestamp without time zone':
                            type_str = 'timestamp'
                        else:
                            type_str = data_type

                        # Format nullable
                        null_str = "" if nullable == "NO" else " (nullable)"

                        print(f"  - {col_name}: {type_str}{null_str}")

                    # Check if table is used (has data or recent activity)
                    cur.execute(f"SELECT COUNT(*) FROM {table_name} LIMIT 1;")
                    row_count = cur.fetchone()[0]

                    if row_count == 0:
                        print(f"Usage: Empty table")
                    else:
                        print(f"Usage: Active ({row_count:,} records)")

        # Close connections
        cur.close()
        conn.close()

        print("\n" + "="*80)
        print("Analysis complete!")

    except psycopg2.OperationalError as e:
        print(f"\nDatabase connection failed: {e}")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = analyze_all_tables()
    sys.exit(0 if success else 1)