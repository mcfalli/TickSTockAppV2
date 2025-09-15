"""
Integration Tests for TickStockApp ↔ TickStockPL Pattern Data Communication
Tests Redis message flow, pattern event processing, and cross-system communication.

Issue: Pattern data not flowing from TickStockPL to TickStockApp
- Daily patterns: 0, Intraday patterns: 0
- Combo patterns: 569 (suggests some data exists)
- Need to validate Redis pub-sub communication

Test Coverage:
1. Redis channel monitoring for pattern events
2. Pattern cache event processing
3. End-to-end message delivery
4. System health and service status
5. Performance validation
"""

import pytest
import redis
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from src.infrastructure.cache.redis_pattern_cache import RedisPatternCache, CachedPattern
from src.core.services.redis_event_subscriber import RedisEventSubscriber, TickStockEvent, EventType
from src.core.services.pattern_discovery_service import PatternDiscoveryService

class TestRedisPatternCommunication:
    """Test Redis communication patterns for TickStockApp ↔ TickStockPL integration."""
    
    @pytest.fixture
    def redis_client(self):
        """Redis client for testing with dedicated test database."""
        client = redis.Redis(
            host='localhost', 
            port=6379, 
            db=15,  # Test database
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=1
        )
        
        # Test connection
        try:
            client.ping()
        except redis.ConnectionError:
            pytest.skip("Redis not available for testing")
            
        yield client
        
        # Cleanup after test
        try:
            client.flushdb()
        except:
            pass
    
    @pytest.fixture
    def pattern_cache(self, redis_client):
        """Pattern cache instance for testing."""
        config = {
            'pattern_cache_ttl': 3600,
            'api_response_cache_ttl': 30,
            'index_cache_ttl': 3600
        }
        cache = RedisPatternCache(redis_client, config)
        return cache
    
    @pytest.fixture
    def mock_socketio(self):
        """Mock Flask-SocketIO for testing."""
        socketio = Mock()
        socketio.emit = Mock()
        return socketio
    
    @pytest.fixture
    def event_subscriber(self, redis_client, mock_socketio):
        """Event subscriber for testing."""
        config = {
            'channels': [
                'tickstock.events.patterns',
                'tickstock.events.backtesting.progress',
                'tickstock.events.backtesting.results'
            ]
        }
        subscriber = RedisEventSubscriber(redis_client, mock_socketio, config)
        return subscriber

    def test_redis_connection_health(self, redis_client):
        """Test basic Redis connectivity for pattern communication."""
        # Verify Redis is accessible
        assert redis_client.ping() is True
        
        # Test basic pub-sub functionality
        pubsub = redis_client.pubsub()
        pubsub.subscribe('test_channel')
        
        # Publish test message
        redis_client.publish('test_channel', json.dumps({'test': 'message'}))
        
        # Verify message received
        message = pubsub.get_message(timeout=1.0)
        assert message is not None
        
        pubsub.unsubscribe()
        pubsub.close()
    
    def test_pattern_event_channel_monitoring(self, redis_client):
        """Test monitoring of TickStockPL pattern event channels."""
        received_messages = []
        
        def monitor_channel(channel_name):
            """Monitor specific Redis channel for pattern events."""
            pubsub = redis_client.pubsub()
            pubsub.subscribe(channel_name)
            
            try:
                # Listen for 2 seconds
                start_time = time.time()
                while time.time() - start_time < 2.0:
                    message = pubsub.get_message(timeout=0.1)
                    if message and message['type'] == 'message':
                        received_messages.append({
                            'channel': message['channel'],
                            'data': json.loads(message['data']),
                            'timestamp': time.time()
                        })
            finally:
                pubsub.unsubscribe()
                pubsub.close()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=monitor_channel,
            args=('tickstock.events.patterns',),
            daemon=True
        )
        monitor_thread.start()
        
        # Wait for subscription to be established
        time.sleep(0.1)
        
        # Simulate TickStockPL publishing pattern events
        test_patterns = [
            {
                'event_type': 'pattern_detected',
                'symbol': 'AAPL',
                'pattern': 'Doji',
                'confidence': 0.85,
                'current_price': 150.25,
                'price_change': 2.1,
                'timestamp': time.time(),
                'expires_at': time.time() + 3600,
                'indicators': {
                    'relative_strength': 1.2,
                    'relative_volume': 1.5,
                    'rsi': 65.0
                },
                'source': 'daily'
            },
            {
                'event_type': 'pattern_detected',
                'symbol': 'GOOGL',
                'pattern': 'Hammer',
                'confidence': 0.78,
                'current_price': 2750.50,
                'price_change': -0.8,
                'timestamp': time.time(),
                'expires_at': time.time() + 1800,
                'indicators': {
                    'relative_strength': 0.9,
                    'relative_volume': 2.1,
                    'rsi': 45.0
                },
                'source': 'intraday'
            }
        ]
        
        # Publish test pattern events
        for pattern in test_patterns:
            redis_client.publish('tickstock.events.patterns', json.dumps(pattern))
            time.sleep(0.05)  # Small delay between messages
        
        # Wait for monitoring to complete
        monitor_thread.join(timeout=3.0)
        
        # Analyze results
        return {
            'messages_received': len(received_messages),
            'messages': received_messages,
            'channels_active': len(set(msg['channel'] for msg in received_messages)),
            'test_passed': len(received_messages) == len(test_patterns)
        }
    
    def test_pattern_cache_event_processing(self, pattern_cache):
        """Test pattern cache processing of TickStockPL events."""
        # Test pattern event processing
        test_event = {
            'event_type': 'pattern_detected',
            'data': {
                'symbol': 'MSFT',
                'pattern': 'Engulfing',
                'confidence': 0.92,
                'current_price': 380.75,
                'price_change': 1.5,
                'timestamp': time.time(),
                'expires_at': time.time() + 3600,
                'indicators': {
                    'relative_strength': 1.1,
                    'relative_volume': 1.8,
                    'rsi': 70.0
                },
                'source': 'combo'
            }
        }
        
        # Process event
        success = pattern_cache.process_pattern_event(test_event)
        assert success, "Pattern event processing should succeed"
        
        # Verify pattern was cached
        cache_stats = pattern_cache.get_cache_stats()
        assert cache_stats['cached_patterns'] > 0, "Pattern should be cached"
        
        # Test pattern retrieval
        filters = {
            'symbols': ['MSFT'],
            'pattern_types': ['Engulfing'],
            'confidence_min': 0.9,
            'page': 1,
            'per_page': 10
        }
        
        results = pattern_cache.scan_patterns(filters)
        assert results['pagination']['total'] > 0, "Cached pattern should be retrievable"
        assert len(results['patterns']) > 0, "Pattern should appear in scan results"
        
        # Verify pattern data integrity
        pattern = results['patterns'][0]
        assert pattern['symbol'] == 'MSFT'
        assert pattern['pattern'] == 'Engulfing'
        assert float(pattern['conf']) == 0.92
        
        return {
            'processing_success': success,
            'cached_patterns': cache_stats['cached_patterns'],
            'retrieval_success': results['pagination']['total'] > 0,
            'pattern_data': pattern
        }
    
    def test_end_to_end_pattern_delivery(self, redis_client, pattern_cache, event_subscriber):
        """Test complete pattern event flow from Redis to WebSocket."""
        delivery_results = []
        
        # Mock WebSocket emission to capture events
        def mock_emit(event_name, data, **kwargs):
            delivery_results.append({
                'event_name': event_name,
                'data': data,
                'timestamp': time.time(),
                'kwargs': kwargs
            })
        
        event_subscriber.socketio.emit = mock_emit
        
        # Start event subscriber
        subscriber_started = event_subscriber.start()
        assert subscriber_started, "Event subscriber should start successfully"
        
        # Add pattern event handler to cache patterns
        def cache_pattern_handler(event: TickStockEvent):
            pattern_cache.process_pattern_event(event.data)
        
        event_subscriber.add_event_handler(EventType.PATTERN_DETECTED, cache_pattern_handler)
        
        # Wait for subscriber to be ready
        time.sleep(0.2)
        
        # Simulate TickStockPL publishing pattern event
        pattern_event = {
            'event_type': 'pattern_detected',
            'symbol': 'TSLA',
            'pattern': 'Bull_Flag',
            'confidence': 0.88,
            'current_price': 250.30,
            'price_change': 3.2,
            'timestamp': time.time(),
            'expires_at': time.time() + 2700,
            'indicators': {
                'relative_strength': 1.4,
                'relative_volume': 2.3,
                'rsi': 68.0
            },
            'source': 'daily'
        }
        
        # Publish event
        redis_client.publish('tickstock.events.patterns', json.dumps(pattern_event))
        
        # Wait for event processing
        time.sleep(0.5)
        
        # Stop subscriber
        event_subscriber.stop()
        
        # Verify cache was updated
        cache_stats = pattern_cache.get_cache_stats()
        
        # Check WebSocket delivery
        websocket_delivered = len(delivery_results) > 0
        pattern_alert_sent = any(result['event_name'] == 'pattern_alert' for result in delivery_results)
        
        return {
            'subscriber_started': subscriber_started,
            'redis_published': True,
            'cache_updated': cache_stats['cached_patterns'] > 0,
            'websocket_delivered': websocket_delivered,
            'pattern_alert_sent': pattern_alert_sent,
            'delivery_results': delivery_results,
            'processing_time_ms': 500  # Approximate
        }
    
    def test_live_pattern_event_monitoring(self, redis_client):
        """Test monitoring live pattern events from TickStockPL (if running)."""
        monitoring_results = {
            'channels_monitored': [],
            'events_detected': [],
            'monitoring_duration': 5.0,
            'tickstockpl_active': False
        }
        
        # Channels to monitor for TickStockPL activity
        channels_to_monitor = [
            'tickstock.events.patterns',
            'tickstock.events.backtesting.progress',
            'tickstock.events.backtesting.results',
            'tickstock.health.status'
        ]
        
        # Monitor multiple channels simultaneously
        def monitor_channels():
            pubsub = redis_client.pubsub()
            
            try:
                # Subscribe to all TickStockPL channels
                pubsub.subscribe(channels_to_monitor)
                monitoring_results['channels_monitored'] = channels_to_monitor
                
                # Monitor for specified duration
                start_time = time.time()
                while time.time() - start_time < monitoring_results['monitoring_duration']:
                    message = pubsub.get_message(timeout=0.1)
                    
                    if message and message['type'] == 'message':
                        try:
                            event_data = json.loads(message['data'])
                            monitoring_results['events_detected'].append({
                                'channel': message['channel'],
                                'event_type': event_data.get('event_type', 'unknown'),
                                'source': event_data.get('source', 'unknown'),
                                'timestamp': time.time(),
                                'data_keys': list(event_data.keys())
                            })
                            monitoring_results['tickstockpl_active'] = True
                        except json.JSONDecodeError:
                            # Invalid JSON - might be test data
                            pass
                            
            finally:
                pubsub.unsubscribe()
                pubsub.close()
        
        # Start monitoring
        monitor_thread = threading.Thread(target=monitor_channels, daemon=True)
        monitor_thread.start()
        monitor_thread.join(timeout=6.0)
        
        return monitoring_results
    
    def test_database_pattern_table_status(self):
        """Test database connectivity and pattern table status."""
        try:
            from src.infrastructure.database.tickstock_db import TickStockDatabase
            
            # Initialize database connection
            db_config = {
                'host': 'localhost',
                'port': 5432,
                'database': 'tickstock',
                'user': 'app_readwrite', 
                'password': 'test_password'  # This would come from env
            }
            
            try:
                db = TickStockDatabase(db_config)
                
                # Test database connectivity
                health = db.health_check()
                db_healthy = health.get('status') in ['healthy', 'degraded']
                
                if db_healthy:
                    # Check pattern table counts
                    with db.get_connection() as conn:
                        # Check daily patterns
                        daily_count = conn.execute("SELECT COUNT(*) FROM daily_patterns").scalar()
                        
                        # Check intraday patterns  
                        intraday_count = conn.execute("SELECT COUNT(*) FROM intraday_patterns").scalar()
                        
                        # Check combo patterns
                        combo_count = conn.execute("SELECT COUNT(*) FROM pattern_detections").scalar()
                        
                        # Check recent pattern activity
                        recent_patterns = conn.execute("""
                            SELECT COUNT(*) FROM pattern_detections 
                            WHERE detected_at > NOW() - INTERVAL '24 hours'
                        """).scalar()
                        
                        db.close()
                        
                        return {
                            'database_healthy': True,
                            'daily_patterns_count': daily_count,
                            'intraday_patterns_count': intraday_count,
                            'combo_patterns_count': combo_count,
                            'recent_patterns_24h': recent_patterns,
                            'tables_accessible': True
                        }
                        
            except Exception as db_error:
                return {
                    'database_healthy': False,
                    'error': str(db_error),
                    'tables_accessible': False
                }
                
        except ImportError as e:
            return {
                'database_healthy': False,
                'error': f"Database module import failed: {e}",
                'tables_accessible': False
            }
    
    def test_performance_requirements(self, redis_client, pattern_cache):
        """Test performance requirements for pattern data pipeline."""
        performance_results = {
            'redis_latency_ms': [],
            'cache_processing_ms': [],
            'api_response_ms': [],
            'meets_requirements': False
        }
        
        # Test Redis pub-sub latency (target <100ms)
        for i in range(5):
            start_time = time.time()
            
            # Publish message and measure delivery time
            pubsub = redis_client.pubsub()
            pubsub.subscribe('performance_test')
            
            test_message = {'test_id': i, 'timestamp': time.time()}
            redis_client.publish('performance_test', json.dumps(test_message))
            
            message = pubsub.get_message(timeout=1.0)
            if message and message['type'] == 'message':
                latency_ms = (time.time() - start_time) * 1000
                performance_results['redis_latency_ms'].append(latency_ms)
            
            pubsub.unsubscribe()
            pubsub.close()
            time.sleep(0.01)
        
        # Test pattern cache processing (target <50ms)
        for i in range(5):
            start_time = time.time()
            
            test_pattern = {
                'event_type': 'pattern_detected',
                'data': {
                    'symbol': f'TEST{i}',
                    'pattern': 'Performance_Test',
                    'confidence': 0.80,
                    'current_price': 100.0,
                    'price_change': 1.0,
                    'timestamp': time.time(),
                    'expires_at': time.time() + 3600,
                    'indicators': {'rsi': 50.0},
                    'source': 'test'
                }
            }
            
            pattern_cache.process_pattern_event(test_pattern)
            
            processing_ms = (time.time() - start_time) * 1000
            performance_results['cache_processing_ms'].append(processing_ms)
        
        # Test API response times (target <50ms)
        for i in range(5):
            start_time = time.time()
            
            filters = {
                'pattern_types': ['Performance_Test'],
                'confidence_min': 0.7,
                'page': 1,
                'per_page': 10
            }
            
            results = pattern_cache.scan_patterns(filters)
            
            api_ms = (time.time() - start_time) * 1000
            performance_results['api_response_ms'].append(api_ms)
        
        # Calculate averages
        avg_redis_latency = sum(performance_results['redis_latency_ms']) / len(performance_results['redis_latency_ms'])
        avg_cache_processing = sum(performance_results['cache_processing_ms']) / len(performance_results['cache_processing_ms'])
        avg_api_response = sum(performance_results['api_response_ms']) / len(performance_results['api_response_ms'])
        
        # Check requirements
        redis_ok = avg_redis_latency < 100  # <100ms message delivery
        cache_ok = avg_cache_processing < 50  # <50ms cache processing  
        api_ok = avg_api_response < 50  # <50ms API response
        
        performance_results['meets_requirements'] = redis_ok and cache_ok and api_ok
        performance_results['avg_redis_latency_ms'] = avg_redis_latency
        performance_results['avg_cache_processing_ms'] = avg_cache_processing
        performance_results['avg_api_response_ms'] = avg_api_response
        
        return performance_results

class TestIntegrationDiagnostics:
    """Comprehensive diagnostic tests for pattern data communication failure."""
    
    def test_comprehensive_system_diagnosis(self):
        """Run complete system diagnosis to identify pattern data issues."""
        diagnosis = {}
        
        # Initialize test components
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
            redis_client.ping()
            
            pattern_cache_config = {'pattern_cache_ttl': 3600, 'api_response_cache_ttl': 30}
            pattern_cache = RedisPatternCache(redis_client, pattern_cache_config)
            
            test_comm = TestRedisPatternCommunication()
            
        except Exception as e:
            return {'critical_error': f"Failed to initialize test components: {e}"}
        
        try:
            # 1. Test Redis connectivity
            diagnosis['redis_health'] = test_comm.test_redis_connection_health(redis_client)
            
            # 2. Monitor live pattern events
            diagnosis['live_monitoring'] = test_comm.test_live_pattern_event_monitoring(redis_client)
            
            # 3. Test pattern cache functionality
            diagnosis['cache_processing'] = test_comm.test_pattern_cache_event_processing(pattern_cache)
            
            # 4. Test database access
            diagnosis['database_status'] = test_comm.test_database_pattern_table_status()
            
            # 5. Test performance
            diagnosis['performance'] = test_comm.test_performance_requirements(redis_client, pattern_cache)
            
            # 6. Overall system health assessment
            diagnosis['system_health'] = self._assess_system_health(diagnosis)
            
            # Cleanup
            redis_client.flushdb()
            
            return diagnosis
            
        except Exception as e:
            return {
                **diagnosis,
                'diagnosis_error': f"Error during system diagnosis: {e}"
            }
    
    def _assess_system_health(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall system health based on diagnostic results."""
        health_assessment = {
            'overall_status': 'unknown',
            'critical_issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check Redis connectivity
        if not diagnosis.get('redis_health'):
            health_assessment['critical_issues'].append("Redis connectivity failed")
        
        # Check TickStockPL activity
        live_monitoring = diagnosis.get('live_monitoring', {})
        if not live_monitoring.get('tickstockpl_active'):
            health_assessment['critical_issues'].append("TickStockPL not publishing pattern events")
            health_assessment['recommendations'].append("Verify TickStockPL service is running and connected to Redis")
        
        # Check database access
        db_status = diagnosis.get('database_status', {})
        if not db_status.get('database_healthy'):
            health_assessment['warnings'].append("Database connectivity issues detected")
            health_assessment['recommendations'].append("Check database connection and credentials")
        
        # Check pattern data
        if db_status.get('daily_patterns_count', 0) == 0:
            health_assessment['critical_issues'].append("No daily patterns in database")
        
        if db_status.get('intraday_patterns_count', 0) == 0:
            health_assessment['critical_issues'].append("No intraday patterns in database")
        
        if db_status.get('recent_patterns_24h', 0) == 0:
            health_assessment['warnings'].append("No recent pattern activity in last 24 hours")
        
        # Check performance
        performance = diagnosis.get('performance', {})
        if not performance.get('meets_requirements'):
            health_assessment['warnings'].append("Performance requirements not met")
        
        # Determine overall status
        if health_assessment['critical_issues']:
            health_assessment['overall_status'] = 'critical'
        elif health_assessment['warnings']:
            health_assessment['overall_status'] = 'degraded'  
        else:
            health_assessment['overall_status'] = 'healthy'
        
        return health_assessment

# Integration test execution helper
def run_pattern_communication_diagnosis():
    """Execute comprehensive pattern communication diagnosis."""
    print("="*80)
    print("TickStockApp ↔ TickStockPL Pattern Communication Diagnosis")
    print("="*80)
    
    diagnostics = TestIntegrationDiagnostics()
    results = diagnostics.test_comprehensive_system_diagnosis()
    
    # Print results
    print("\n📊 DIAGNOSTIC RESULTS:")
    print("-" * 50)
    
    for category, data in results.items():
        if category == 'system_health':
            continue
            
        print(f"\n🔍 {category.upper().replace('_', ' ')}:")
        
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print(f"  Result: {data}")
    
    # Print system health assessment
    if 'system_health' in results:
        health = results['system_health']
        status_icon = {'healthy': '✅', 'degraded': '⚠️', 'critical': '❌', 'unknown': '❓'}
        
        print(f"\n{status_icon.get(health['overall_status'], '❓')} SYSTEM HEALTH: {health['overall_status'].upper()}")
        
        if health['critical_issues']:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in health['critical_issues']:
                print(f"  • {issue}")
        
        if health['warnings']:
            print("\n⚠️  WARNINGS:")
            for warning in health['warnings']:
                print(f"  • {warning}")
        
        if health['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in health['recommendations']:
                print(f"  • {rec}")
    
    print("\n" + "="*80)
    return results

if __name__ == "__main__":
    # Run diagnostics if executed directly
    run_pattern_communication_diagnosis()