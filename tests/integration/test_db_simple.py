#!/usr/bin/env python3
"""Simple database connection test."""

import eventlet
eventlet.monkey_patch()

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.services.config_manager import ConfigManager
from src.infrastructure.database.tickstock_db import TickStockDatabase

def test_db():
    """Test database connection."""
    try:
        print("Testing database connection...")
        
        config_manager = ConfigManager()
        config = config_manager.config
        
        db = TickStockDatabase(config)
        print("SUCCESS: Database connection established")
        
        # Test pattern tables
        tables = ['daily_patterns', 'intraday_patterns', 'pattern_detections', 'pattern_definitions']
        
        for table in tables:
            try:
                result = db.execute_query(f'SELECT COUNT(*) FROM {table}', [])
                count = result[0][0] if result else 0
                print(f"SUCCESS: {table}: {count} records")
            except Exception as e:
                print(f"ERROR: {table} table error: {e}")
                
        print("Database connectivity test completed!")
        
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")

if __name__ == "__main__":
    test_db()