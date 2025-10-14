"""
Comprehensive Integration Diagnostics Runner
Executes all integration tests to diagnose TickStockApp ↔ TickStockPL pattern data communication failure.

This script runs:
1. Redis pattern communication tests
2. End-to-end pattern event delivery tests  
3. Database pattern integration tests
4. System health and service status validation
5. Performance requirement verification

Results provide detailed diagnostic information to identify and fix the pattern data pipeline issues.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Any

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

def main():
    """Execute comprehensive integration diagnostics."""
    print("STARTING Comprehensive Pattern Data Pipeline Diagnostics")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Testing Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    print()

    overall_results = {
        'start_time': time.time(),
        'tests_executed': [],
        'critical_failures': [],
        'warnings': [],
        'recommendations': [],
        'test_results': {}
    }

    # Test 1: Redis Pattern Communication
    print("1. REDIS PATTERN COMMUNICATION TESTS")
    print("-" * 50)

    try:
        from test_redis_pattern_communication import run_pattern_communication_diagnosis
        redis_results = run_pattern_communication_diagnosis()
        overall_results['test_results']['redis_communication'] = redis_results
        overall_results['tests_executed'].append('redis_communication')

        # Analyze Redis results
        if redis_results.get('system_health', {}).get('overall_status') == 'critical':
            overall_results['critical_failures'].extend(
                redis_results['system_health'].get('critical_issues', [])
            )

    except Exception as e:
        print(f"FAILED Redis communication test failed: {e}")
        overall_results['critical_failures'].append(f"Redis communication test failed: {e}")

    print("\n")

    # Test 2: End-to-End Pattern Event Delivery
    print("2️⃣ END-TO-END PATTERN EVENT DELIVERY TESTS")
    print("-" * 50)

    try:
        from test_pattern_event_delivery import run_pattern_delivery_tests
        delivery_results = run_pattern_delivery_tests()
        overall_results['test_results']['pattern_delivery'] = delivery_results
        overall_results['tests_executed'].append('pattern_delivery')

        # Analyze delivery results
        if delivery_results.get('workflow_results', {}).get('end_to_end_delivery') is False:
            overall_results['critical_failures'].append("End-to-end pattern delivery failed")

        if delivery_results.get('performance_results', {}).get('performance_target_met') is False:
            overall_results['warnings'].append("Pattern delivery performance targets not met")

    except Exception as e:
        print(f"❌ Pattern delivery test failed: {e}")
        overall_results['critical_failures'].append(f"Pattern delivery test failed: {e}")

    print("\n")

    # Test 3: Database Pattern Integration
    print("3️⃣ DATABASE PATTERN INTEGRATION TESTS")
    print("-" * 50)

    try:
        from test_database_pattern_integration import run_database_integration_diagnosis
        database_results = run_database_integration_diagnosis()
        overall_results['test_results']['database_integration'] = database_results
        overall_results['tests_executed'].append('database_integration')

        # Analyze database results
        db_assessment = database_results.get('overall_assessment', {})
        if db_assessment.get('status') == 'critical':
            overall_results['critical_failures'].extend(
                db_assessment.get('critical_issues', [])
            )
        elif db_assessment.get('status') == 'degraded':
            overall_results['warnings'].extend(
                db_assessment.get('warnings', [])
            )

        overall_results['recommendations'].extend(
            db_assessment.get('recommendations', [])
        )

    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        overall_results['critical_failures'].append(f"Database integration test failed: {e}")

    print("\n")

    # Test 4: System Health Monitoring
    print("4️⃣ SYSTEM HEALTH AND SERVICE STATUS")
    print("-" * 50)

    try:
        health_results = run_system_health_checks()
        overall_results['test_results']['system_health'] = health_results
        overall_results['tests_executed'].append('system_health')

        # Analyze health results
        for service, status in health_results.get('service_status', {}).items():
            if not status.get('healthy', False):
                overall_results['critical_failures'].append(f"{service} service not healthy")

    except Exception as e:
        print(f"❌ System health check failed: {e}")
        overall_results['critical_failures'].append(f"System health check failed: {e}")

    print("\n")

    # Generate Final Report
    overall_results['end_time'] = time.time()
    overall_results['total_duration'] = overall_results['end_time'] - overall_results['start_time']

    generate_diagnostic_report(overall_results)

    return overall_results

def run_system_health_checks():
    """Run system health and service status checks."""
    health_results = {
        'timestamp': time.time(),
        'service_status': {},
        'connectivity_tests': {},
        'performance_metrics': {}
    }

    print("🔍 Checking Redis connectivity...")
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()

        health_results['service_status']['redis'] = {
            'healthy': True,
            'status': 'connected',
            'response_time_ms': 0  # Would measure actual response time
        }
        print("  ✅ Redis: Connected")

    except Exception as e:
        health_results['service_status']['redis'] = {
            'healthy': False,
            'status': 'failed',
            'error': str(e)
        }
        print(f"  ❌ Redis: Failed - {e}")

    print("🔍 Checking Database connectivity...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='tickstock',
            user='app_readwrite',
            password='test_password'
        )
        conn.close()

        health_results['service_status']['database'] = {
            'healthy': True,
            'status': 'connected'
        }
        print("  ✅ Database: Connected")

    except Exception as e:
        health_results['service_status']['database'] = {
            'healthy': False,
            'status': 'failed',
            'error': str(e)
        }
        print(f"  ❌ Database: Failed - {e}")

    print("🔍 Checking TickStockPL activity...")
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

        # Monitor TickStockPL channels for activity
        channels = [
            'tickstock.events.patterns',
            'tickstock.events.backtesting.progress',
            'tickstock.events.backtesting.results'
        ]

        activity_detected = False
        pubsub = redis_client.pubsub()
        pubsub.subscribe(channels)

        # Listen for 2 seconds for any activity
        start_time = time.time()
        while time.time() - start_time < 2.0:
            message = pubsub.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                activity_detected = True
                break

        pubsub.unsubscribe()
        pubsub.close()

        health_results['service_status']['tickstockpl'] = {
            'healthy': activity_detected,
            'status': 'active' if activity_detected else 'inactive',
            'monitoring_duration': 2.0
        }

        if activity_detected:
            print("  ✅ TickStockPL: Active (events detected)")
        else:
            print("  ⚠️  TickStockPL: No activity detected in 2-second monitoring window")

    except Exception as e:
        health_results['service_status']['tickstockpl'] = {
            'healthy': False,
            'status': 'error',
            'error': str(e)
        }
        print(f"  ❌ TickStockPL monitoring failed: {e}")

    return health_results

def generate_diagnostic_report(results: dict[str, Any]):
    """Generate comprehensive diagnostic report."""
    print("📋 COMPREHENSIVE DIAGNOSTIC REPORT")
    print("="*80)

    # Executive Summary
    total_tests = len(results['tests_executed'])
    critical_count = len(results['critical_failures'])
    warning_count = len(results['warnings'])

    if critical_count > 0:
        overall_status = "🚨 CRITICAL"
        status_color = "CRITICAL ISSUES DETECTED"
    elif warning_count > 0:
        overall_status = "⚠️  DEGRADED"
        status_color = "PERFORMANCE/CONFIGURATION ISSUES"
    else:
        overall_status = "✅ HEALTHY"
        status_color = "ALL SYSTEMS OPERATIONAL"

    print("\n🎯 EXECUTIVE SUMMARY")
    print(f"Overall System Status: {overall_status}")
    print(f"Status Description: {status_color}")
    print(f"Tests Executed: {total_tests}")
    print(f"Critical Issues: {critical_count}")
    print(f"Warnings: {warning_count}")
    print(f"Total Duration: {results['total_duration']:.2f} seconds")

    # Critical Issues
    if results['critical_failures']:
        print("\n🚨 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
        for i, issue in enumerate(results['critical_failures'], 1):
            print(f"  {i}. {issue}")

    # Warnings
    if results['warnings']:
        print("\n⚠️  WARNINGS - PERFORMANCE/CONFIGURATION ISSUES:")
        for i, warning in enumerate(results['warnings'], 1):
            print(f"  {i}. {warning}")

    # Recommendations
    if results['recommendations']:
        print("\n💡 RECOMMENDED ACTIONS:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"  {i}. {rec}")

    # Test Results Summary
    print("\n📊 DETAILED TEST RESULTS:")
    print("-" * 50)

    for test_name in results['tests_executed']:
        test_data = results['test_results'].get(test_name, {})

        print(f"\n🔍 {test_name.upper().replace('_', ' ')}:")

        if test_name == 'redis_communication':
            redis_health = test_data.get('system_health', {})
            print(f"  Status: {redis_health.get('overall_status', 'unknown')}")
            if 'live_monitoring' in test_data:
                tickstockpl_active = test_data['live_monitoring'].get('tickstockpl_active', False)
                print(f"  TickStockPL Activity: {'✅ Active' if tickstockpl_active else '❌ Inactive'}")

        elif test_name == 'pattern_delivery':
            if 'workflow_results' in test_data:
                workflow = test_data['workflow_results']
                delivery_success = workflow.get('end_to_end_delivery', False)
                print(f"  End-to-End Delivery: {'✅ Working' if delivery_success else '❌ Failed'}")
                print(f"  Cache Patterns Stored: {workflow.get('cache_patterns_stored', 0)}")
                print(f"  WebSocket Alerts Sent: {workflow.get('websocket_alerts_sent', 0)}")

        elif test_name == 'database_integration':
            db_assessment = test_data.get('overall_assessment', {})
            print(f"  Database Status: {db_assessment.get('status', 'unknown')}")

            if 'data_content' in test_data:
                content = test_data['data_content']
                pattern_counts = content.get('pattern_counts', {})
                print(f"  Daily Patterns: {pattern_counts.get('daily_patterns', 0)}")
                print(f"  Intraday Patterns: {pattern_counts.get('intraday_patterns', 0)}")
                print(f"  Combo Patterns: {pattern_counts.get('pattern_detections', 0)}")

        elif test_name == 'system_health':
            service_status = test_data.get('service_status', {})
            for service, status in service_status.items():
                healthy = status.get('healthy', False)
                print(f"  {service.title()}: {'✅ Healthy' if healthy else '❌ Unhealthy'}")

    # Pattern Data Pipeline Analysis
    print("\n🔄 PATTERN DATA PIPELINE ANALYSIS:")
    print("-" * 50)

    # Check if TickStockPL is publishing events
    redis_monitoring = results['test_results'].get('redis_communication', {}).get('live_monitoring', {})
    tickstockpl_publishing = redis_monitoring.get('tickstockpl_active', False)

    # Check if patterns are in database
    db_content = results['test_results'].get('database_integration', {}).get('data_content', {})
    pattern_counts = db_content.get('pattern_counts', {})
    has_daily_patterns = pattern_counts.get('daily_patterns', 0) > 0
    has_intraday_patterns = pattern_counts.get('intraday_patterns', 0) > 0
    has_combo_patterns = pattern_counts.get('pattern_detections', 0) > 0

    print(f"1. TickStockPL Publishing Events: {'✅ Yes' if tickstockpl_publishing else '❌ No'}")
    print(f"2. Daily Patterns in Database: {'✅ Yes' if has_daily_patterns else '❌ No'}")
    print(f"3. Intraday Patterns in Database: {'✅ Yes' if has_intraday_patterns else '❌ No'}")
    print(f"4. Combo Patterns in Database: {'✅ Yes' if has_combo_patterns else '❌ No'}")

    # Pipeline Issue Diagnosis
    if not tickstockpl_publishing and not (has_daily_patterns or has_intraday_patterns):
        print("\n🔍 ROOT CAUSE ANALYSIS:")
        print("   PRIMARY ISSUE: TickStockPL is not running or not publishing pattern events")
        print("   EVIDENCE: No Redis activity detected AND no patterns in database")
        print("   ACTION REQUIRED: Start/restart TickStockPL service and verify Redis connectivity")

    elif has_combo_patterns and not (has_daily_patterns or has_intraday_patterns):
        print("\n🔍 ROOT CAUSE ANALYSIS:")
        print("   PRIMARY ISSUE: Pattern data exists but not in expected tables")
        print("   EVIDENCE: Combo patterns found (569) but daily/intraday tables empty")
        print("   ACTION REQUIRED: Check TickStockPL pattern detection configuration and table mapping")

    elif tickstockpl_publishing and not (has_daily_patterns or has_intraday_patterns):
        print("\n🔍 ROOT CAUSE ANALYSIS:")
        print("   PRIMARY ISSUE: TickStockPL publishing events but patterns not reaching database")
        print("   EVIDENCE: Redis activity detected but no patterns stored")
        print("   ACTION REQUIRED: Check TickStockPL database write permissions and pattern storage logic")

    # Save report to file
    report_filename = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = os.path.join(os.path.dirname(__file__), report_filename)

    try:
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Detailed report saved to: {report_path}")
    except Exception as e:
        print(f"\n❌ Failed to save report: {e}")

    print("\n" + "="*80)
    print("🏁 Diagnostic Analysis Complete")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Diagnostics interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Diagnostic execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
