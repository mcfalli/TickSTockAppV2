#!/usr/bin/env python3
"""
Migration Script: Add NOT NULL constraint to code_reference columns
Purpose: Prevent NULL values in code_reference which causes application issues
Date: 2025-10-15

Usage:
    python scripts/migrations/run_code_reference_migration.py

Options:
    --dry-run    : Show what would be done without making changes
    --rollback   : Remove NOT NULL constraints (use with caution)
"""

import argparse
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection from environment"""
    db_uri = os.getenv(
        'DATABASE_URI',
        'postgresql://app_readwrite:LJI48rUEkUpe6e@127.0.0.1:5432/tickstock'
    )

    # Parse URI
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)', db_uri)
    if not match:
        raise ValueError(f"Invalid DATABASE_URI format: {db_uri}")

    user, password, host, port, database = match.groups()
    port = port or '5432'

    return psycopg2.connect(
        host=host,
        port=int(port),
        database=database,
        user=user,
        password=password,
        cursor_factory=RealDictCursor
    )


def check_null_values(conn):
    """Check for NULL code_reference values before migration"""
    with conn.cursor() as cursor:
        # Check pattern_definitions
        cursor.execute("""
            SELECT COUNT(*) as null_count
            FROM pattern_definitions
            WHERE code_reference IS NULL
        """)
        pattern_nulls = cursor.fetchone()['null_count']

        # Check indicator_definitions
        cursor.execute("""
            SELECT COUNT(*) as null_count
            FROM indicator_definitions
            WHERE code_reference IS NULL
        """)
        indicator_nulls = cursor.fetchone()['null_count']

        return {
            'pattern_definitions': pattern_nulls,
            'indicator_definitions': indicator_nulls
        }


def check_current_constraints(conn):
    """Check current nullable status of code_reference columns"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                table_name,
                column_name,
                is_nullable,
                data_type
            FROM information_schema.columns
            WHERE table_name IN ('pattern_definitions', 'indicator_definitions')
            AND column_name = 'code_reference'
            ORDER BY table_name
        """)
        return cursor.fetchall()


def apply_migration(conn, dry_run=False):
    """Apply NOT NULL constraints to code_reference columns"""
    print("\n" + "="*70)
    print("CODE REFERENCE NOT NULL CONSTRAINT MIGRATION")
    print("="*70)

    # Step 1: Check current state
    print("\nStep 1: Checking current constraint status...")
    current_state = check_current_constraints(conn)
    for row in current_state:
        status = "✓ Already NOT NULL" if row['is_nullable'] == 'NO' else "⚠ Currently nullable"
        print(f"  {row['table_name']}.{row['column_name']}: {status}")

    # Step 2: Check for NULL values
    print("\nStep 2: Checking for NULL values...")
    null_counts = check_null_values(conn)

    has_nulls = False
    for table, count in null_counts.items():
        if count > 0:
            print(f"  ❌ {table}: {count} rows with NULL code_reference")
            has_nulls = True
        else:
            print(f"  ✓ {table}: No NULL values found")

    if has_nulls:
        print("\n❌ MIGRATION BLOCKED: NULL values must be fixed before applying constraint")
        print("\nTo fix NULL values, run:")
        print("  UPDATE pattern_definitions SET code_reference = '<module>.<class>' WHERE code_reference IS NULL;")
        print("  UPDATE indicator_definitions SET code_reference = '<module>.<class>' WHERE code_reference IS NULL;")
        return False

    # Step 3: Apply constraints
    print("\nStep 3: Applying NOT NULL constraints...")

    if dry_run:
        print("  [DRY RUN] Would execute:")
        print("    ALTER TABLE pattern_definitions ALTER COLUMN code_reference SET NOT NULL;")
        print("    ALTER TABLE indicator_definitions ALTER COLUMN code_reference SET NOT NULL;")
        return True

    try:
        with conn.cursor() as cursor:
            # Apply constraint to pattern_definitions
            if any(row['table_name'] == 'pattern_definitions' and row['is_nullable'] == 'YES'
                   for row in current_state):
                cursor.execute("""
                    ALTER TABLE pattern_definitions
                    ALTER COLUMN code_reference SET NOT NULL
                """)
                print("  ✓ Applied NOT NULL to pattern_definitions.code_reference")
            else:
                print("  ⊘ pattern_definitions.code_reference already NOT NULL")

            # Apply constraint to indicator_definitions
            if any(row['table_name'] == 'indicator_definitions' and row['is_nullable'] == 'YES'
                   for row in current_state):
                cursor.execute("""
                    ALTER TABLE indicator_definitions
                    ALTER COLUMN code_reference SET NOT NULL
                """)
                print("  ✓ Applied NOT NULL to indicator_definitions.code_reference")
            else:
                print("  ⊘ indicator_definitions.code_reference already NOT NULL")

        conn.commit()
        print("\n✓ Migration committed successfully")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        return False

    # Step 4: Verify
    print("\nStep 4: Verifying constraints...")
    final_state = check_current_constraints(conn)

    all_not_null = True
    for row in final_state:
        if row['is_nullable'] == 'NO':
            print(f"  ✓ {row['table_name']}.{row['column_name']}: NOT NULL constraint active")
        else:
            print(f"  ❌ {row['table_name']}.{row['column_name']}: Still nullable")
            all_not_null = False

    if all_not_null:
        print("\n" + "="*70)
        print("✓ MIGRATION SUCCESSFUL")
        print("="*70)
        print("\ncode_reference columns now require values on INSERT/UPDATE")
        return True
    else:
        print("\n❌ MIGRATION INCOMPLETE - Some constraints were not applied")
        return False


def rollback_migration(conn, dry_run=False):
    """Remove NOT NULL constraints (use with caution)"""
    print("\n" + "="*70)
    print("ROLLBACK: REMOVE NOT NULL CONSTRAINTS FROM code_reference")
    print("="*70)
    print("\n⚠ WARNING: This will allow NULL values in code_reference columns")

    if not dry_run:
        confirm = input("\nType 'ROLLBACK' to confirm: ")
        if confirm != 'ROLLBACK':
            print("Rollback cancelled")
            return False

    print("\nRemoving NOT NULL constraints...")

    if dry_run:
        print("  [DRY RUN] Would execute:")
        print("    ALTER TABLE pattern_definitions ALTER COLUMN code_reference DROP NOT NULL;")
        print("    ALTER TABLE indicator_definitions ALTER COLUMN code_reference DROP NOT NULL;")
        return True

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE pattern_definitions
                ALTER COLUMN code_reference DROP NOT NULL
            """)
            print("  ✓ Removed NOT NULL from pattern_definitions.code_reference")

            cursor.execute("""
                ALTER TABLE indicator_definitions
                ALTER COLUMN code_reference DROP NOT NULL
            """)
            print("  ✓ Removed NOT NULL from indicator_definitions.code_reference")

        conn.commit()
        print("\n✓ Rollback completed")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Rollback failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Add NOT NULL constraint to code_reference columns'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Remove NOT NULL constraints (use with caution)'
    )

    args = parser.parse_args()

    try:
        # Connect to database
        print("Connecting to database...")
        conn = get_db_connection()
        print("✓ Connected")

        # Execute migration or rollback
        if args.rollback:
            success = rollback_migration(conn, dry_run=args.dry_run)
        else:
            success = apply_migration(conn, dry_run=args.dry_run)

        conn.close()

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
