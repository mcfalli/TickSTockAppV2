#!/usr/bin/env python3
"""
Analyze indicator and pattern tables in the database to provide definitions.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def analyze_tables():
    """Analyze the structure of indicator and pattern tables."""

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

    tables_to_analyze = [
        'indicator_definitions',
        'daily_indicators',
        'intraday_indicators',
        'combo_indicators',
        'pattern_definitions',
        'daily_patterns',
        'intraday_patterns',
        'daily_intraday_patterns'
    ]

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        print("Connected successfully!\n")
        print("="*80)

        for table_name in tables_to_analyze:
            print(f"\n### {table_name.upper()}")
            print("-"*60)

            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                );
            """, (table_name,))

            exists = cur.fetchone()[0]

            if not exists:
                print(f"  [WARNING] Table does not exist")
                continue

            # Get table comment
            cur.execute("""
                SELECT obj_description(c.oid)
                FROM pg_class c
                WHERE c.relname = %s
                AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
            """, (table_name,))

            comment = cur.fetchone()
            if comment and comment[0]:
                print(f"  Description: {comment[0]}")

            # Get columns and their types
            cur.execute("""
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default,
                    col_description(pgc.oid, a.attnum) as column_comment
                FROM information_schema.columns c
                LEFT JOIN pg_class pgc ON pgc.relname = c.table_name
                LEFT JOIN pg_attribute a ON a.attrelid = pgc.oid AND a.attname = c.column_name
                WHERE table_schema = 'public'
                AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))

            columns = cur.fetchall()

            print(f"\n  Columns ({len(columns)} total):")
            for col_name, data_type, max_len, nullable, default, col_comment in columns:
                # Format data type
                if max_len:
                    type_str = f"{data_type}({max_len})"
                else:
                    type_str = data_type

                # Add nullable indicator
                null_str = "" if nullable == "NO" else " NULL"

                # Add default if exists
                default_str = f" DEFAULT {default[:30]}" if default else ""

                # Add comment if exists
                comment_str = f" -- {col_comment}" if col_comment else ""

                print(f"    - {col_name:<25} {type_str:<20}{null_str}{default_str}{comment_str}")

            # Get row count
            cur.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cur.fetchone()[0]
            print(f"\n  Row Count: {row_count:,} records")

            # Get indexes
            cur.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename = %s;
            """, (table_name,))

            indexes = cur.fetchall()
            if indexes:
                print(f"\n  Indexes:")
                for idx_name, idx_def in indexes:
                    if 'PRIMARY KEY' not in idx_def:
                        print(f"    - {idx_name}")

            # Get foreign keys
            cur.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = %s;
            """, (table_name,))

            foreign_keys = cur.fetchall()
            if foreign_keys:
                print(f"\n  Foreign Keys:")
                for col, ref_table, ref_col in foreign_keys:
                    print(f"    - {col} -> {ref_table}({ref_col})")

            # Sample data for JSONB columns
            if table_name in ['daily_indicators', 'intraday_indicators', 'combo_indicators']:
                # Check for value_data column
                cur.execute(f"""
                    SELECT value_data
                    FROM {table_name}
                    WHERE value_data IS NOT NULL
                    LIMIT 1;
                """)
                sample = cur.fetchone()
                if sample and sample[0]:
                    print(f"\n  Sample value_data JSONB:")
                    import json
                    print(f"    {json.dumps(sample[0], indent=2)[:200]}...")

            if table_name in ['daily_patterns', 'intraday_patterns', 'daily_intraday_patterns']:
                # Check for pattern_data column
                cur.execute(f"""
                    SELECT pattern_data
                    FROM {table_name}
                    WHERE pattern_data IS NOT NULL
                    LIMIT 1;
                """)
                sample = cur.fetchone()
                if sample and sample[0]:
                    print(f"\n  Sample pattern_data JSONB:")
                    import json
                    print(f"    {json.dumps(sample[0], indent=2)[:200]}...")

        print("\n" + "="*80)
        print("Analysis complete!")

        # Close connections
        cur.close()
        conn.close()

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
    success = analyze_tables()
    sys.exit(0 if success else 1)