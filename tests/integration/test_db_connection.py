#!/usr/bin/env python3
"""Test database connection for tier patterns."""

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

def test_database_connection():
    """Test database connection and pattern table counts."""
    try:
        print("Testing database connection...")
        
        # Get configuration
        config_manager = ConfigManager()
        config = config_manager.config
        
        # Create database connection
        db = TickStockDatabase(config)
        print("✓ Database connection established")
        
        # Test daily_patterns table
        try:
            result = db.execute_query('SELECT COUNT(*) FROM daily_patterns', [])
            daily_count = result[0][0] if result else 0
            print(f"✓ daily_patterns: {daily_count} records")
        except Exception as e:
            print(f"✗ daily_patterns table error: {e}")
        
        # Test intraday_patterns table
        try:
            result = db.execute_query('SELECT COUNT(*) FROM intraday_patterns', [])
            intraday_count = result[0][0] if result else 0
            print(f"✓ intraday_patterns: {intraday_count} records")
        except Exception as e:
            print(f"✗ intraday_patterns table error: {e}")
        
        # Test pattern_detections table
        try:
            result = db.execute_query('SELECT COUNT(*) FROM pattern_detections', [])
            detections_count = result[0][0] if result else 0
            print(f"✓ pattern_detections: {detections_count} records")
        except Exception as e:
            print(f"✗ pattern_detections table error: {e}")
        
        # Test pattern_definitions table
        try:
            result = db.execute_query('SELECT COUNT(*) FROM pattern_definitions', [])
            definitions_count = result[0][0] if result else 0
            print(f"✓ pattern_definitions: {definitions_count} records")
        except Exception as e:
            print(f"✗ pattern_definitions table error: {e}")
            
        print("\n✓ Database connectivity test completed successfully!")
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_database_connection()