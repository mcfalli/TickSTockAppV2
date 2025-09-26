"""
Simple Pattern Data Diagnostics
Quick diagnostic test to identify the pattern data communication failure.
"""

import sys
import os
import time
import json
import re
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.services.config_manager import get_config

def test_redis_connectivity():
    """Test basic Redis connectivity."""
    print("Testing Redis connectivity...")
    
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        print("  PASS: Redis connection successful")
        return True, redis_client
    except Exception as e:
        print(f"  FAIL: Redis connection failed - {e}")
        return False, None

def test_database_connectivity():
    """Test database connectivity."""
    print("Testing Database connectivity...")

    try:
        import psycopg2
        # Database connection using config_manager
        config = get_config()
        db_uri = config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')
        # Parse URI to extract components
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)', db_uri)
        if match:
            user, password, host, port, database = match.groups()
            port = port or '5432'
        else:
            # Fallback values
            host, port, database, user, password = 'localhost', 5432, 'tickstock', 'app_readwrite', 'password'

        conn = psycopg2.connect(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        print("  PASS: Database connection successful")
        return True
    except Exception as e:
        print(f"  FAIL: Database connection failed - {e}")
        return False

def test_pattern_tables():
    """Test pattern table data."""
    print("Testing pattern table data...")

    try:
        import psycopg2
        # Database connection using config_manager
        config = get_config()
        db_uri = config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')
        # Parse URI to extract components
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)', db_uri)
        if match:
            user, password, host, port, database = match.groups()
            port = port or '5432'
        else:
            # Fallback values
            host, port, database, user, password = 'localhost', 5432, 'tickstock', 'app_readwrite', 'password'

        conn = psycopg2.connect(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password
        )
        
        cursor = conn.cursor()
        
        # Check daily patterns
        cursor.execute("SELECT COUNT(*) FROM daily_patterns")
        daily_count = cursor.fetchone()[0]
        print(f"  Daily patterns: {daily_count}")
        
        # Check intraday patterns
        cursor.execute("SELECT COUNT(*) FROM intraday_patterns")
        intraday_count = cursor.fetchone()[0]
        print(f"  Intraday patterns: {intraday_count}")
        
        # Check combo patterns
        cursor.execute("SELECT COUNT(*) FROM pattern_detections")
        combo_count = cursor.fetchone()[0]
        print(f"  Combo patterns: {combo_count}")
        
        # Check recent activity
        cursor.execute("""
            SELECT COUNT(*) FROM pattern_detections 
            WHERE detected_at > NOW() - INTERVAL '24 hours'
        """)
        recent_count = cursor.fetchone()[0]
        print(f"  Recent patterns (24h): {recent_count}")
        
        cursor.close()
        conn.close()
        
        return {
            'daily': daily_count,
            'intraday': intraday_count,
            'combo': combo_count,
            'recent_24h': recent_count
        }
        
    except Exception as e:
        print(f"  FAIL: Pattern table query failed - {e}")
        return None

def test_tickstockpl_activity(redis_client):
    """Test TickStockPL activity by monitoring Redis channels."""
    print("Testing TickStockPL activity...")
    
    if not redis_client:
        print("  SKIP: No Redis connection available")
        return False
    
    try:
        # Monitor TickStockPL channels
        pubsub = redis_client.pubsub()
        channels = [
            'tickstock.events.patterns',
            'tickstock.events.backtesting.progress',
            'tickstock.events.backtesting.results'
        ]
        
        pubsub.subscribe(channels)
        
        print("  Monitoring TickStockPL channels for 3 seconds...")
        activity_detected = False
        messages_received = 0
        
        start_time = time.time()
        while time.time() - start_time < 3.0:
            message = pubsub.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                activity_detected = True
                messages_received += 1
                print(f"    Message received on {message['channel']}")
        
        pubsub.unsubscribe()
        pubsub.close()
        
        if activity_detected:
            print(f"  PASS: TickStockPL activity detected - {messages_received} messages")
        else:
            print("  FAIL: No TickStockPL activity detected")
        
        return activity_detected
        
    except Exception as e:
        print(f"  FAIL: TickStockPL monitoring failed - {e}")
        return False

def test_redis_pattern_cache():
    """Test Redis pattern cache functionality."""
    print("Testing Redis pattern cache...")
    
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Check for pattern cache keys
        pattern_keys = redis_client.keys("tickstock:patterns:*")
        api_cache_keys = redis_client.keys("tickstock:api_cache:*")
        index_keys = redis_client.keys("tickstock:indexes:*")
        
        print(f"  Pattern cache keys: {len(pattern_keys)}")
        print(f"  API cache keys: {len(api_cache_keys)}")
        print(f"  Index keys: {len(index_keys)}")
        
        # Test basic cache operations
        test_key = "tickstock:patterns:TEST_PATTERN"
        test_data = {"symbol": "TEST", "pattern": "Test", "confidence": 0.8}
        
        redis_client.set(test_key, json.dumps(test_data))
        retrieved = redis_client.get(test_key)
        
        if retrieved:
            parsed_data = json.loads(retrieved)
            if parsed_data['symbol'] == 'TEST':
                print("  PASS: Cache read/write operations working")
                redis_client.delete(test_key)  # Cleanup
                return True
        
        print("  FAIL: Cache operations not working")
        return False
        
    except Exception as e:
        print(f"  FAIL: Redis cache test failed - {e}")
        return False

def main():
    """Run simple pattern data diagnostics."""
    print("PATTERN DATA DIAGNOSTICS")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test 1: Redis connectivity
    redis_ok, redis_client = test_redis_connectivity()
    results['tests']['redis_connectivity'] = redis_ok
    print()
    
    # Test 2: Database connectivity
    db_ok = test_database_connectivity()
    results['tests']['database_connectivity'] = db_ok
    print()
    
    # Test 3: Pattern table data
    pattern_data = test_pattern_tables()
    results['tests']['pattern_data'] = pattern_data
    print()
    
    # Test 4: TickStockPL activity
    tickstockpl_ok = test_tickstockpl_activity(redis_client)
    results['tests']['tickstockpl_activity'] = tickstockpl_ok
    print()
    
    # Test 5: Redis pattern cache
    cache_ok = test_redis_pattern_cache()
    results['tests']['redis_cache'] = cache_ok
    print()
    
    # Analysis
    print("DIAGNOSTIC ANALYSIS")
    print("-" * 30)
    
    if not redis_ok:
        print("CRITICAL: Redis not available - check Redis service")
    
    if not db_ok:
        print("CRITICAL: Database not available - check PostgreSQL service and credentials")
    
    if pattern_data:
        daily = pattern_data.get('daily', 0)
        intraday = pattern_data.get('intraday', 0)
        combo = pattern_data.get('combo', 0)
        recent = pattern_data.get('recent_24h', 0)
        
        if daily == 0 and intraday == 0:
            print("ISSUE: No daily or intraday patterns found in database")
            if combo > 0:
                print(f"  BUT: {combo} combo patterns exist - data structure issue?")
            else:
                print("  AND: No combo patterns either - TickStockPL not writing to DB")
        
        if recent == 0:
            print("WARNING: No recent pattern activity in last 24 hours")
    
    if not tickstockpl_ok:
        print("CRITICAL: TickStockPL not publishing events to Redis")
        print("  ACTION: Check if TickStockPL service is running")
        print("  ACTION: Verify TickStockPL Redis configuration")
    
    # Root cause assessment
    print()
    print("ROOT CAUSE ASSESSMENT")
    print("-" * 30)
    
    if not tickstockpl_ok and pattern_data and pattern_data.get('combo', 0) == 0:
        print("ROOT CAUSE: TickStockPL service is not running")
        print("  EVIDENCE: No Redis activity AND no database patterns")
        print("  SOLUTION: Start TickStockPL service")
    
    elif not tickstockpl_ok and pattern_data and pattern_data.get('combo', 0) > 0:
        print("ROOT CAUSE: TickStockPL database writes working but Redis publishing broken")
        print("  EVIDENCE: Database has patterns but no Redis activity")
        print("  SOLUTION: Check TickStockPL Redis publishing configuration")
    
    elif tickstockpl_ok and pattern_data and pattern_data.get('combo', 0) == 0:
        print("ROOT CAUSE: TickStockPL Redis working but database writes broken")
        print("  EVIDENCE: Redis activity detected but no database patterns")
        print("  SOLUTION: Check TickStockPL database write permissions")
    
    elif pattern_data and pattern_data.get('daily', 0) == 0 and pattern_data.get('intraday', 0) == 0 and pattern_data.get('combo', 0) > 0:
        print("ROOT CAUSE: Pattern data exists but in wrong tables")
        print("  EVIDENCE: Combo patterns exist but daily/intraday tables empty")
        print("  SOLUTION: Check TickStockPL table routing configuration")
    
    else:
        print("ROOT CAUSE: Multiple issues detected - requires detailed investigation")
    
    print()
    print("=" * 50)
    print("DIAGNOSTICS COMPLETE")
    
    return results

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"DIAGNOSTIC FAILED: {e}")
        import traceback
        traceback.print_exc()