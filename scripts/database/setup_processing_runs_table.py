#!/usr/bin/env python3
"""
Setup processing_runs table for Sprint 33 Phase 4
Run this script to create the required database table.
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from src.core.services.config_manager import get_config
import re

def create_processing_runs_table():
    """Create the processing_runs table if it doesn't exist"""

    config = get_config()
    db_uri = config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')

    # Parse URI to extract components
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)', db_uri)
    if match:
        user, password, host, port, database = match.groups()
        port = port or '5432'
    else:
        print("ERROR: Invalid DATABASE_URI format")
        return False

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password
        )
        conn.autocommit = True
        cursor = conn.cursor()

        print(f"Connected to database: {database}@{host}:{port}")

        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_runs (
                run_id VARCHAR(64) PRIMARY KEY,
                trigger_type VARCHAR(32),
                status VARCHAR(32),
                phase VARCHAR(64),
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds INTEGER,
                symbols_total INTEGER DEFAULT 0,
                symbols_processed INTEGER DEFAULT 0,
                symbols_failed INTEGER DEFAULT 0,
                indicators_total INTEGER DEFAULT 0,
                indicators_processed INTEGER DEFAULT 0,
                indicators_failed INTEGER DEFAULT 0,
                error_message TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        print("[OK] Table 'processing_runs' created/verified")

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_processing_runs_started_at
            ON processing_runs(started_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_processing_runs_status
            ON processing_runs(status)
        """)

        print("[OK] Indexes created/verified")

        # Check if table is accessible
        cursor.execute("SELECT COUNT(*) FROM processing_runs")
        count = cursor.fetchone()[0]

        print(f"[OK] Table is accessible, contains {count} records")

        cursor.close()
        conn.close()

        print("\n[SUCCESS] processing_runs table is ready for use")
        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to create table: {e}")
        return False

if __name__ == "__main__":
    success = create_processing_runs_table()
    sys.exit(0 if success else 1)