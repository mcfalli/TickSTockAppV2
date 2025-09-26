#!/usr/bin/env python3
"""
Sprint 32: Comprehensive tests for Enhanced Error Handling System
Tests file logging, database storage, severity thresholds, and Redis integration
"""

import os
import sys
import json
import time
import tempfile
import psycopg2
import redis
from datetime import datetime
from pathlib import Path
from src.core.services.config_manager import get_config


# Get configuration
try:
    config = get_config()
except:
    config = None

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.services.config_manager import LoggingConfig
from src.core.services.enhanced_logger import EnhancedLogger, create_enhanced_logger
from src.core.services.error_subscriber import ErrorSubscriber, create_error_subscriber
from src.core.models.error_models import ErrorMessage, SEVERITY_LEVELS

# Test configuration
TEST_RESULTS = []
PASSED = 0
FAILED = 0

def test_result(name, passed, message=""):
    """Record test result"""
    global PASSED, FAILED
    status = "PASS" if passed else "FAIL"
    if passed:
        PASSED += 1
    else:
        FAILED += 1
    TEST_RESULTS.append(f"[{status}] {name}: {message}")
    print(f"[{status}] {name}: {message}")

def test_1_logging_config():
    """Test 1: LoggingConfig loads from environment"""
    try:
        config = LoggingConfig()

        # Check that config loaded properly
        assert hasattr(config, 'log_file_path')
        assert hasattr(config, 'log_db_enabled')
        assert hasattr(config, 'log_db_severity_threshold')
        assert hasattr(config, 'redis_error_channel')

        test_result("LoggingConfig Creation", True,
                   f"Config loaded: file={config.log_file_path}, db={config.log_db_enabled}")
        return config
    except Exception as e:
        test_result("LoggingConfig Creation", False, str(e))
        return None

def test_2_file_logging():
    """Test 2: File logging works for all severity levels"""
    try:
        # Create temp log file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as tmp:
            temp_log = tmp.name

        # Create custom config
        config = LoggingConfig()
        config.log_file_path = temp_log
        config.log_file_enabled = True

        # Create logger without database
        logger = create_enhanced_logger(config, None)

        # Test each severity level
        severities = ['debug', 'info', 'warning', 'error', 'critical']
        for severity in severities:
            logger.log_error(
                severity=severity,
                message=f"Test {severity} message",
                category='test',
                component='TestSuite',
                context={'test_id': f'test_{severity}'}
            )

        # Read log file
        with open(temp_log, 'r') as f:
            content = f.read()

        # Verify all messages were logged
        all_logged = all(f"Test {s} message" in content for s in severities)

        # Clean up
        os.unlink(temp_log)

        test_result("File Logging All Severities", all_logged,
                   f"Logged {len(severities)} severity levels to file")
        return True
    except Exception as e:
        test_result("File Logging All Severities", False, str(e))
        return False

def test_3_database_threshold():
    """Test 3: Database only stores errors at or above threshold"""
    try:
        # Get database connection
        db_conn = psycopg2.connect(config.get('DATABASE_URI'))
        cursor = db_conn.cursor()

        # Clear test data
        cursor.execute("DELETE FROM error_logs WHERE component = 'ThresholdTest'")
        db_conn.commit()

        # Create config with 'error' threshold
        config = LoggingConfig()
        config.log_db_enabled = True
        config.log_db_severity_threshold = 'error'

        # Create logger with database
        logger = create_enhanced_logger(config, db_conn)

        # Log messages at different severities
        test_cases = [
            ('debug', False),    # Should NOT be in database
            ('info', False),     # Should NOT be in database
            ('warning', False),  # Should NOT be in database
            ('error', True),     # SHOULD be in database
            ('critical', True),  # SHOULD be in database
        ]

        for severity, should_store in test_cases:
            logger.log_error(
                severity=severity,
                message=f"Threshold test {severity}",
                category='test',
                component='ThresholdTest',
                context={'severity': severity}
            )

        # Check database
        time.sleep(0.5)  # Allow time for database writes
        cursor.execute("""
            SELECT severity, message
            FROM error_logs
            WHERE component = 'ThresholdTest'
            ORDER BY created_at
        """)
        results = cursor.fetchall()

        # Verify only error and critical were stored
        stored_severities = [r[0] for r in results]
        expected = ['error', 'critical']
        threshold_correct = stored_severities == expected

        # Clean up
        cursor.execute("DELETE FROM error_logs WHERE component = 'ThresholdTest'")
        db_conn.commit()
        cursor.close()
        db_conn.close()

        test_result("Database Severity Threshold", threshold_correct,
                   f"Stored {len(results)} errors (threshold=error): {stored_severities}")
        return threshold_correct
    except Exception as e:
        test_result("Database Severity Threshold", False, str(e))
        return False

def test_4_redis_error_subscriber():
    """Test 4: Redis error subscriber receives and processes errors"""
    try:
        # Create Redis client
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Test Redis connection
        redis_client.ping()

        # Create config and logger
        config = LoggingConfig()
        db_conn = psycopg2.connect(config.get('DATABASE_URI'))
        logger = create_enhanced_logger(config, db_conn)

        # Clear test data
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM error_logs WHERE component = 'TickStockPL'")
        db_conn.commit()

        # Create and start error subscriber
        subscriber = create_error_subscriber(redis_client, logger, config)
        if not subscriber.start():
            raise Exception("Failed to start subscriber")

        # Give subscriber time to connect
        time.sleep(1)

        # Publish test error from "TickStockPL"
        test_error = {
            'severity': 'error',
            'message': 'Test error from TickStockPL',
            'category': 'pattern',
            'component': 'TickStockPL',
            'context': {
                'source': 'redis_test',
                'timestamp': time.time()
            }
        }

        # Publish to Redis channel
        redis_client.publish(config.redis_error_channel, json.dumps(test_error))

        # Wait for processing
        time.sleep(2)

        # Check if error was stored in database
        cursor.execute("""
            SELECT message, component
            FROM error_logs
            WHERE component = 'TickStockPL'
            AND message = 'Test error from TickStockPL'
        """)
        result = cursor.fetchone()

        # Stop subscriber
        subscriber.stop()

        # Clean up
        if result:
            cursor.execute("DELETE FROM error_logs WHERE component = 'TickStockPL'")
            db_conn.commit()
        cursor.close()
        db_conn.close()

        test_result("Redis Error Subscriber", result is not None,
                   f"Received and stored TickStockPL error via Redis")
        return result is not None
    except Exception as e:
        test_result("Redis Error Subscriber", False, str(e))
        return False

def test_5_error_models():
    """Test 5: Error models validate and serialize correctly"""
    try:
        # Test valid error message
        error = ErrorMessage(
            severity='error',
            message='Test error message',
            category='test',
            component='TestComponent',
            context={'key': 'value'}
        )

        # Test serialization
        error_dict = error.dict()
        assert error_dict['severity'] == 'error'
        assert error_dict['message'] == 'Test error message'
        assert 'timestamp' in error_dict
        assert 'error_id' in error_dict

        # Test JSON serialization
        error_json = error.json()
        parsed = json.loads(error_json)
        assert parsed['component'] == 'TestComponent'

        # Test invalid severity
        try:
            invalid_error = ErrorMessage(
                severity='invalid',
                message='Test',
                category='test',
                component='Test'
            )
            test_result("Error Model Validation", False, "Should reject invalid severity")
            return False
        except:
            # Expected to fail
            pass

        test_result("Error Model Validation", True,
                   f"Models validate and serialize correctly")
        return True
    except Exception as e:
        test_result("Error Model Validation", False, str(e))
        return False

def test_6_performance():
    """Test 6: Error logging performance <100ms"""
    try:
        # Create logger
        config = LoggingConfig()
        db_conn = psycopg2.connect(config.get('DATABASE_URI'))
        logger = create_enhanced_logger(config, db_conn)

        # Time error logging
        times = []
        for i in range(10):
            start = time.time()
            logger.log_error(
                severity='error',
                message=f'Performance test {i}',
                category='performance',
                component='PerfTest',
                context={'iteration': i}
            )
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        # Calculate average
        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Clean up
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM error_logs WHERE component = 'PerfTest'")
        db_conn.commit()
        cursor.close()
        db_conn.close()

        # Check if under 100ms
        performance_ok = max_time < 100

        test_result("Performance <100ms", performance_ok,
                   f"Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms")
        return performance_ok
    except Exception as e:
        test_result("Performance <100ms", False, str(e))
        return False

def test_7_graceful_degradation():
    """Test 7: System works even if database is unavailable"""
    try:
        # Create logger with invalid database connection
        config = LoggingConfig()
        config.log_db_enabled = True

        # Use None for database connection
        logger = create_enhanced_logger(config, None)

        # Try to log error (should not crash)
        logger.log_error(
            severity='error',
            message='Test with no database',
            category='test',
            component='GracefulTest',
            context={'db_available': False}
        )

        # If we get here without crashing, it worked
        test_result("Graceful Degradation", True,
                   "Logger works without database connection")
        return True
    except Exception as e:
        test_result("Graceful Degradation", False, str(e))
        return False

def test_8_log_rotation():
    """Test 8: File rotation works when size limit reached"""
    try:
        # Create temp directory for logs
        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, 'test_rotation.log')

        # Create config with small max size
        config = LoggingConfig()
        config.log_file_path = log_file
        config.log_file_max_size = 1024  # 1KB - very small for testing
        config.log_file_backup_count = 3
        config.log_file_enabled = True

        # Create logger
        logger = create_enhanced_logger(config, None)

        # Write enough data to trigger rotation
        for i in range(100):
            logger.log_error(
                severity='info',
                message=f'Log rotation test message {i} with some padding to increase size',
                category='test',
                component='RotationTest',
                context={'iteration': i, 'padding': 'x' * 50}
            )

        # Check if rotation files were created
        log_dir = Path(temp_dir)
        log_files = list(log_dir.glob('test_rotation.log*'))

        # Should have main file plus at least one backup
        rotation_worked = len(log_files) > 1

        # Clean up
        for f in log_files:
            f.unlink()
        os.rmdir(temp_dir)

        test_result("Log File Rotation", rotation_worked,
                   f"Created {len(log_files)} log files with rotation")
        return rotation_worked
    except Exception as e:
        test_result("Log File Rotation", False, str(e))
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SPRINT 32: ENHANCED ERROR HANDLING TEST SUITE")
    print("="*60 + "\n")

    # Run tests
    test_1_logging_config()
    test_2_file_logging()
    test_3_database_threshold()
    test_4_redis_error_subscriber()
    test_5_error_models()
    test_6_performance()
    test_7_graceful_degradation()
    test_8_log_rotation()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {PASSED + FAILED}")
    print(f"Passed: {PASSED}")
    print(f"Failed: {FAILED}")
    print(f"Success Rate: {(PASSED/(PASSED+FAILED)*100):.1f}%")

    if FAILED == 0:
        print("\n[SUCCESS] ALL TESTS PASSED! Enhanced Error Handling System is working correctly!")
    else:
        print(f"\n[WARNING] {FAILED} test(s) failed. Review the results above.")

    return FAILED == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)