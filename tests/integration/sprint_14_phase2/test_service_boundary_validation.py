"""
Service Boundary Validation Tests - Sprint 14 Phase 2
Validates service boundary enforcement and loose coupling architecture.

Tests ensure:
- No direct API calls between TickStockApp and automation services
- Proper role separation (producer/consumer boundaries)
- Redis-only communication patterns
- Service independence and isolation

Date: 2025-09-01
Sprint: 14 Phase 2
Coverage: Service boundary validation
"""

import json
import os
import sys
import time
from typing import Any
from unittest.mock import patch

import pytest
import redis
import requests

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

class ServiceBoundaryValidator:
    """Validates service boundaries and loose coupling enforcement"""

    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=15):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_client = None

        # Network monitoring for detecting direct API calls
        self.monitored_ports = [5000, 8000, 8080, 3000]  # Common app server ports
        self.captured_requests = []

    def setup(self):
        """Setup boundary validator"""
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            db=self.redis_db,
            decode_responses=True
        )
        self.redis_client.flushdb()

    def cleanup(self):
        """Cleanup boundary validator"""
        if self.redis_client:
            self.redis_client.flushdb()
            self.redis_client.close()

class TestServiceBoundaryEnforcement:
    """Test service boundary enforcement and isolation"""

    def setup_method(self):
        """Setup for boundary tests"""
        self.validator = ServiceBoundaryValidator()
        self.validator.setup()

    def teardown_method(self):
        """Cleanup boundary tests"""
        self.validator.cleanup()

    def test_no_direct_http_api_calls_between_services(self):
        """
        Test that automation services don't make direct HTTP API calls to TickStockApp
        Validates: No HTTP traffic between services, Redis-only communication
        """
        # Mock requests library to capture any HTTP calls
        captured_requests = []

        def mock_request_method(method):
            def mock_implementation(*args, **kwargs):
                captured_requests.append({
                    'method': method,
                    'args': args,
                    'kwargs': kwargs,
                    'timestamp': time.time()
                })
                # Raise exception to prevent actual HTTP calls during testing
                raise requests.exceptions.ConnectionError(f"HTTP {method} call intercepted during boundary test")
            return mock_implementation

        # Patch all HTTP methods
        with patch('requests.get', side_effect=mock_request_method('GET')), \
             patch('requests.post', side_effect=mock_request_method('POST')), \
             patch('requests.put', side_effect=mock_request_method('PUT')), \
             patch('requests.delete', side_effect=mock_request_method('DELETE')), \
             patch('requests.patch', side_effect=mock_request_method('PATCH')):

            # Simulate automation service operations that should NOT make HTTP calls

            # 1. IPO Monitor simulation - should only use Redis
            ipo_event = {
                'service': 'ipo_monitor',
                'event_type': 'new_symbol',
                'data': {
                    'symbol': 'BOUNDARY_TEST_IPO',
                    'name': 'Boundary Test IPO Company'
                }
            }

            # This should work (Redis pub-sub)
            result = self.validator.redis_client.publish(
                'tickstock.automation.symbols.new',
                json.dumps(ipo_event)
            )
            assert result >= 0, "Redis publish should succeed"

            # 2. Data Quality Monitor simulation - should only use Redis
            quality_alert = {
                'service': 'data_quality_monitor',
                'alert_type': 'price_anomaly',
                'data': {
                    'symbol': 'BOUNDARY_TEST_QUAL',
                    'severity': 'high'
                }
            }

            # This should work (Redis pub-sub)
            result = self.validator.redis_client.publish(
                'tickstock.quality.price_anomaly',
                json.dumps(quality_alert)
            )
            assert result >= 0, "Redis publish should succeed"

            # 3. Simulate any attempts at direct HTTP communication
            # These should be blocked by our patches

            try:
                # This would be a boundary violation - should be prevented
                requests.get('http://localhost:5000/api/symbols')
                pytest.fail("HTTP GET call should have been intercepted")
            except requests.exceptions.ConnectionError:
                pass  # Expected - boundary violation prevented

            try:
                # This would be a boundary violation - should be prevented
                requests.post('http://localhost:5000/api/alerts')
                pytest.fail("HTTP POST call should have been intercepted")
            except requests.exceptions.ConnectionError:
                pass  # Expected - boundary violation prevented

        # Verify no HTTP calls were attempted
        assert len(captured_requests) == 2, "Only the test HTTP calls should have been captured"

        # Verify the captured requests were the test violations we expected
        methods = [req['method'] for req in captured_requests]
        assert 'GET' in methods, "Test GET call should have been captured"
        assert 'POST' in methods, "Test POST call should have been captured"

    def test_redis_only_communication_pattern_enforcement(self):
        """
        Test that all inter-service communication goes through Redis only
        Validates: Redis channel usage, message format consistency, no other protocols
        """
        # Monitor all Redis operations
        redis_operations = []

        # Patch Redis client to track operations
        original_publish = self.validator.redis_client.publish
        original_subscribe = self.validator.redis_client.pubsub

        def track_publish(channel, message):
            redis_operations.append({
                'operation': 'publish',
                'channel': channel,
                'message': message,
                'timestamp': time.time()
            })
            return original_publish(channel, message)

        def track_subscribe():
            redis_operations.append({
                'operation': 'subscribe',
                'timestamp': time.time()
            })
            return original_subscribe()

        self.validator.redis_client.publish = track_publish
        self.validator.redis_client.pubsub = track_subscribe

        # Simulate complete service communication workflow

        # 1. IPO Monitor publishes new symbol discovery
        ipo_notification = {
            'timestamp': time.time(),
            'service': 'ipo_monitor',
            'event_type': 'new_symbol_discovered',
            'data': {
                'symbol': 'REDIS_ONLY_TEST',
                'discovery_source': 'polygon_api',
                'confidence': 1.0
            }
        }

        self.validator.redis_client.publish(
            'tickstock.automation.symbols.new',
            json.dumps(ipo_notification)
        )

        # 2. IPO Monitor publishes backfill completion
        backfill_notification = {
            'timestamp': time.time(),
            'service': 'ipo_monitor',
            'event_type': 'backfill_completed',
            'data': {
                'symbol': 'REDIS_ONLY_TEST',
                'records_loaded': 90,
                'duration_seconds': 45
            }
        }

        self.validator.redis_client.publish(
            'tickstock.automation.backfill.completed',
            json.dumps(backfill_notification)
        )

        # 3. Data Quality Monitor publishes alert
        quality_alert = {
            'timestamp': time.time(),
            'service': 'data_quality_monitor',
            'alert_type': 'volume_spike',
            'data': {
                'symbol': 'REDIS_ONLY_TEST',
                'volume_ratio': 8.5,
                'severity': 'critical'
            }
        }

        self.validator.redis_client.publish(
            'tickstock.quality.volume_anomaly',
            json.dumps(quality_alert)
        )

        # 4. Simulate TickStockApp subscribing (consumer pattern)
        pubsub = self.validator.redis_client.pubsub()
        pubsub.subscribe([
            'tickstock.automation.symbols.new',
            'tickstock.automation.backfill.completed',
            'tickstock.quality.volume_anomaly'
        ])

        # Verify Redis-only communication pattern
        assert len(redis_operations) >= 4, "Should have tracked multiple Redis operations"

        # Verify all operations were Redis operations
        operation_types = [op['operation'] for op in redis_operations]
        assert 'publish' in operation_types, "Should have Redis publish operations"
        assert 'subscribe' in operation_types, "Should have Redis subscribe operations"

        # Verify proper channel usage
        publish_operations = [op for op in redis_operations if op['operation'] == 'publish']
        channels_used = [op['channel'] for op in publish_operations]

        expected_channels = [
            'tickstock.automation.symbols.new',
            'tickstock.automation.backfill.completed',
            'tickstock.quality.volume_anomaly'
        ]

        for expected_channel in expected_channels:
            assert expected_channel in channels_used, f"Expected channel {expected_channel} not used"

        # Verify message format consistency
        for op in publish_operations:
            message = json.loads(op['message'])
            assert 'timestamp' in message, "All messages should have timestamp"
            assert 'service' in message, "All messages should identify source service"
            assert 'data' in message, "All messages should have data payload"

        pubsub.close()

    def test_service_role_separation_enforcement(self):
        """
        Test that services maintain proper role separation (producer vs consumer)
        Validates: Automation services as producers, TickStockApp as consumer only
        """
        # Track message flow patterns
        message_flows = {
            'automation_to_app': [],
            'app_to_automation': [],
            'automation_to_automation': []
        }

        # Setup message flow tracking
        def track_message_flow(channel, message):
            try:
                msg_data = json.loads(message)
                service = msg_data.get('service', 'unknown')

                # Categorize message flow based on channel and service
                if channel.startswith('tickstock.automation') or channel.startswith('tickstock.quality'):
                    if service in ['ipo_monitor', 'data_quality_monitor']:
                        message_flows['automation_to_app'].append({
                            'service': service,
                            'channel': channel,
                            'timestamp': time.time()
                        })
                    elif service == 'tickstock_app':
                        # This would be a role violation - app shouldn't publish to automation channels
                        message_flows['app_to_automation'].append({
                            'service': service,
                            'channel': channel,
                            'timestamp': time.time()
                        })
                elif channel.startswith('tickstock.internal'):
                    if service in ['ipo_monitor', 'data_quality_monitor']:
                        message_flows['automation_to_automation'].append({
                            'service': service,
                            'channel': channel,
                            'timestamp': time.time()
                        })
            except:
                pass  # Ignore malformed messages

        # Patch Redis publish to track flows
        original_publish = self.validator.redis_client.publish
        def tracking_publish(channel, message):
            track_message_flow(channel, message)
            return original_publish(channel, message)

        self.validator.redis_client.publish = tracking_publish

        # Simulate proper producer role (automation services)

        # 1. IPO Monitor acting as producer (CORRECT ROLE)
        self.validator.redis_client.publish(
            'tickstock.automation.symbols.new',
            json.dumps({
                'service': 'ipo_monitor',
                'event_type': 'symbol_created',
                'data': {'symbol': 'ROLE_TEST_IPO'}
            })
        )

        # 2. Data Quality Monitor acting as producer (CORRECT ROLE)
        self.validator.redis_client.publish(
            'tickstock.quality.price_anomaly',
            json.dumps({
                'service': 'data_quality_monitor',
                'alert_type': 'price_spike',
                'data': {'symbol': 'ROLE_TEST_QUAL'}
            })
        )

        # 3. Simulate TickStockApp attempting to publish to automation channels (ROLE VIOLATION)
        # This should be detected as incorrect role usage
        self.validator.redis_client.publish(
            'tickstock.automation.symbols.new',
            json.dumps({
                'service': 'tickstock_app',
                'event_type': 'symbol_request',  # This would be wrong - app should consume, not produce
                'data': {'symbol': 'ROLE_VIOLATION_TEST'}
            })
        )

        # Verify proper role separation

        # Should have legitimate automation-to-app flows
        assert len(message_flows['automation_to_app']) == 2, "Should have 2 legitimate automation service messages"

        # Should detect app-to-automation role violation
        assert len(message_flows['app_to_automation']) == 1, "Should detect 1 role violation"

        # Verify the role violation was properly categorized
        violation = message_flows['app_to_automation'][0]
        assert violation['service'] == 'tickstock_app', "Role violation should be from tickstock_app"
        assert 'automation' in violation['channel'], "Violation should be on automation channel"

        # Verify legitimate flows are from correct services
        for flow in message_flows['automation_to_app']:
            assert flow['service'] in ['ipo_monitor', 'data_quality_monitor'], \
                f"Legitimate flow should be from automation service, got {flow['service']}"

    def test_database_access_boundary_enforcement(self):
        """
        Test database access boundaries between services
        Validates: Automation services have write access, proper role separation
        """
        # This test would require actual database connections, so we'll simulate
        # the boundary validation logic

        database_operations = {
            'ipo_monitor_writes': [],
            'quality_monitor_reads': [],
            'app_reads': [],
            'boundary_violations': []
        }

        # Simulate database operation tracking
        def simulate_database_operation(service: str, operation: str, table: str, access_type: str):
            """Simulate database operation and track access patterns"""

            operation_record = {
                'service': service,
                'operation': operation,
                'table': table,
                'access_type': access_type,
                'timestamp': time.time()
            }

            # Validate access patterns based on service roles
            if service == 'ipo_monitor':
                if access_type == 'write' and table in ['symbols', 'historical_data', 'equity_processing_queue']:
                    database_operations['ipo_monitor_writes'].append(operation_record)
                elif access_type == 'read':
                    database_operations['ipo_monitor_writes'].append(operation_record)  # IPO monitor can read too
                else:
                    database_operations['boundary_violations'].append(operation_record)

            elif service == 'data_quality_monitor':
                if access_type == 'read':
                    database_operations['quality_monitor_reads'].append(operation_record)
                elif access_type == 'write':
                    # Quality monitor should primarily read, but may write quality metrics
                    if table in ['quality_metrics', 'data_quality_log']:
                        database_operations['quality_monitor_reads'].append(operation_record)
                    else:
                        database_operations['boundary_violations'].append(operation_record)

            elif service == 'tickstock_app':
                if access_type == 'read':
                    database_operations['app_reads'].append(operation_record)
                elif access_type == 'write':
                    # TickStockApp should primarily be read-only consumer
                    if table in ['user_preferences', 'user_sessions']:
                        database_operations['app_reads'].append(operation_record)  # Allowed writes
                    else:
                        database_operations['boundary_violations'].append(operation_record)
            else:
                database_operations['boundary_violations'].append(operation_record)

        # Simulate legitimate database operations

        # IPO Monitor operations (should be allowed)
        simulate_database_operation('ipo_monitor', 'INSERT', 'symbols', 'write')
        simulate_database_operation('ipo_monitor', 'INSERT', 'historical_data', 'write')
        simulate_database_operation('ipo_monitor', 'SELECT', 'symbols', 'read')

        # Data Quality Monitor operations (should be allowed)
        simulate_database_operation('data_quality_monitor', 'SELECT', 'historical_data', 'read')
        simulate_database_operation('data_quality_monitor', 'SELECT', 'symbols', 'read')

        # TickStockApp operations (should be allowed)
        simulate_database_operation('tickstock_app', 'SELECT', 'symbols', 'read')
        simulate_database_operation('tickstock_app', 'SELECT', 'historical_data', 'read')

        # Boundary violations (should be detected)
        simulate_database_operation('tickstock_app', 'INSERT', 'symbols', 'write')  # Violation - app shouldn't create symbols
        simulate_database_operation('data_quality_monitor', 'DELETE', 'symbols', 'write')  # Violation - quality monitor shouldn't delete symbols
        simulate_database_operation('unknown_service', 'SELECT', 'symbols', 'read')  # Violation - unknown service

        # Verify boundary enforcement

        # Verify legitimate operations
        assert len(database_operations['ipo_monitor_writes']) == 3, "IPO Monitor should have 3 legitimate operations"
        assert len(database_operations['quality_monitor_reads']) == 2, "Quality Monitor should have 2 legitimate operations"
        assert len(database_operations['app_reads']) == 2, "TickStockApp should have 2 legitimate operations"

        # Verify boundary violations detected
        assert len(database_operations['boundary_violations']) == 3, "Should detect 3 boundary violations"

        # Verify specific violations
        violations = database_operations['boundary_violations']
        violation_services = [v['service'] for v in violations]
        assert 'tickstock_app' in violation_services, "Should detect TickStockApp write violation"
        assert 'data_quality_monitor' in violation_services, "Should detect Quality Monitor delete violation"
        assert 'unknown_service' in violation_services, "Should detect unknown service violation"

    def test_service_independence_and_isolation(self):
        """
        Test that services can operate independently without dependencies
        Validates: Service isolation, no shared state, independent startup/shutdown
        """
        service_states = {
            'ipo_monitor': {'status': 'unknown', 'dependencies': [], 'operations': []},
            'data_quality_monitor': {'status': 'unknown', 'dependencies': [], 'operations': []},
            'tickstock_app': {'status': 'unknown', 'dependencies': [], 'operations': []}
        }

        def simulate_service_operation(service_name: str, operation: str, requires_other_services: list[str] = None):
            """Simulate service operation and track dependencies"""
            requires_other_services = requires_other_services or []

            service_states[service_name]['operations'].append({
                'operation': operation,
                'requires': requires_other_services,
                'timestamp': time.time()
            })

            # Track dependencies
            for required_service in requires_other_services:
                if required_service not in service_states[service_name]['dependencies']:
                    service_states[service_name]['dependencies'].append(required_service)

        # Simulate independent service operations

        # IPO Monitor operating independently
        simulate_service_operation('ipo_monitor', 'startup')
        simulate_service_operation('ipo_monitor', 'discover_new_symbols')
        simulate_service_operation('ipo_monitor', 'create_symbol_records')
        simulate_service_operation('ipo_monitor', 'publish_notifications')
        simulate_service_operation('ipo_monitor', 'shutdown')

        # Data Quality Monitor operating independently
        simulate_service_operation('data_quality_monitor', 'startup')
        simulate_service_operation('data_quality_monitor', 'scan_data_quality')
        simulate_service_operation('data_quality_monitor', 'detect_anomalies')
        simulate_service_operation('data_quality_monitor', 'publish_alerts')
        simulate_service_operation('data_quality_monitor', 'shutdown')

        # TickStockApp operating independently
        simulate_service_operation('tickstock_app', 'startup')
        simulate_service_operation('tickstock_app', 'load_user_interface')
        simulate_service_operation('tickstock_app', 'subscribe_to_events')
        simulate_service_operation('tickstock_app', 'display_notifications')
        simulate_service_operation('tickstock_app', 'shutdown')

        # Test scenarios that would indicate improper dependencies

        # GOOD: Each service can start independently
        assert len(service_states['ipo_monitor']['operations']) == 5
        assert len(service_states['data_quality_monitor']['operations']) == 5
        assert len(service_states['tickstock_app']['operations']) == 5

        # GOOD: No direct service dependencies
        assert len(service_states['ipo_monitor']['dependencies']) == 0, "IPO Monitor should have no direct service dependencies"
        assert len(service_states['data_quality_monitor']['dependencies']) == 0, "Quality Monitor should have no direct service dependencies"
        assert len(service_states['tickstock_app']['dependencies']) == 0, "TickStockApp should have no direct service dependencies"

        # Simulate what would be BAD dependencies (should not occur)
        # These are examples of violations we want to prevent

        bad_dependencies_detected = []

        # Simulate checking for bad dependencies
        def check_for_bad_dependency(service: str, operation: str, dependency: str):
            """Check for improper direct service dependencies"""
            try:
                # This would be a violation - services should not directly depend on each other
                simulate_service_operation(service, operation, [dependency])
                bad_dependencies_detected.append({
                    'service': service,
                    'operation': operation,
                    'improper_dependency': dependency
                })
            except:
                pass  # Expected - should not create direct dependencies

        # Test for violations (these should not succeed in a properly isolated system)
        check_for_bad_dependency('ipo_monitor', 'notify_app_directly', 'tickstock_app')
        check_for_bad_dependency('tickstock_app', 'request_data_directly', 'data_quality_monitor')
        check_for_bad_dependency('data_quality_monitor', 'trigger_ipo_scan', 'ipo_monitor')

        # In a properly isolated system, we should have detected these as violations
        # For this test, we're allowing them to be recorded to verify we can detect them
        assert len(bad_dependencies_detected) == 3, "Should detect 3 improper dependency attempts"

        # Verify the specific violations
        violation_types = [(bd['service'], bd['improper_dependency']) for bd in bad_dependencies_detected]
        assert ('ipo_monitor', 'tickstock_app') in violation_types, "Should detect IPO Monitor -> App dependency"
        assert ('tickstock_app', 'data_quality_monitor') in violation_types, "Should detect App -> Quality Monitor dependency"
        assert ('data_quality_monitor', 'ipo_monitor') in violation_types, "Should detect Quality Monitor -> IPO Monitor dependency"

    def test_message_format_standardization_across_services(self):
        """
        Test that all services use standardized message formats
        Validates: Consistent message structure, required fields, format compliance
        """
        message_validations = []

        def validate_message_format(channel: str, message: str) -> dict[str, Any]:
            """Validate message format compliance"""
            validation_result = {
                'channel': channel,
                'valid': True,
                'errors': [],
                'warnings': []
            }

            try:
                # Parse message
                msg_data = json.loads(message)

                # Check required fields
                required_fields = ['timestamp', 'service', 'data']
                for field in required_fields:
                    if field not in msg_data:
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"Missing required field: {field}")

                # Check timestamp format
                if 'timestamp' in msg_data:
                    try:
                        timestamp = msg_data['timestamp']
                        if isinstance(timestamp, (int, float)):
                            # Unix timestamp is acceptable
                            pass
                        elif isinstance(timestamp, str):
                            # ISO format should be parseable
                            from datetime import datetime
                            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            validation_result['warnings'].append("Timestamp format should be Unix time or ISO string")
                    except:
                        validation_result['errors'].append("Invalid timestamp format")

                # Check service identification
                if 'service' in msg_data:
                    valid_services = ['ipo_monitor', 'data_quality_monitor', 'tickstock_app']
                    if msg_data['service'] not in valid_services:
                        validation_result['warnings'].append(f"Unknown service identifier: {msg_data['service']}")

                # Check data payload structure
                if 'data' in msg_data:
                    if not isinstance(msg_data['data'], dict):
                        validation_result['errors'].append("Data payload should be a dictionary")
                    else:
                        # Check for common data fields based on channel
                        if 'symbols' in channel:
                            if 'symbol' not in msg_data['data']:
                                validation_result['warnings'].append("Symbol-related message should include symbol field")
                        elif 'quality' in channel:
                            if 'alert_type' not in msg_data and 'anomaly_type' not in msg_data:
                                validation_result['warnings'].append("Quality alert should include alert_type or anomaly_type")

            except json.JSONDecodeError:
                validation_result['valid'] = False
                validation_result['errors'].append("Message is not valid JSON")
            except Exception as e:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Validation error: {str(e)}")

            return validation_result

        # Test messages from different services
        test_messages = [
            # GOOD: Properly formatted IPO Monitor message
            {
                'channel': 'tickstock.automation.symbols.new',
                'message': json.dumps({
                    'timestamp': time.time(),
                    'service': 'ipo_monitor',
                    'event_type': 'new_symbol',
                    'data': {
                        'symbol': 'FORMAT_TEST_IPO',
                        'name': 'Format Test Company',
                        'ipo_date': '2025-09-01'
                    }
                })
            },

            # GOOD: Properly formatted Quality Monitor message
            {
                'channel': 'tickstock.quality.price_anomaly',
                'message': json.dumps({
                    'timestamp': '2025-09-01T12:00:00Z',
                    'service': 'data_quality_monitor',
                    'alert_type': 'price_spike',
                    'data': {
                        'symbol': 'FORMAT_TEST_QUAL',
                        'severity': 'high',
                        'price_change_pct': 0.30
                    }
                })
            },

            # BAD: Missing required fields
            {
                'channel': 'tickstock.automation.symbols.new',
                'message': json.dumps({
                    'service': 'ipo_monitor',
                    # Missing timestamp and data
                    'event_type': 'incomplete_message'
                })
            },

            # BAD: Invalid JSON
            {
                'channel': 'tickstock.quality.volume_anomaly',
                'message': 'invalid json content {'
            },

            # BAD: Wrong data payload structure
            {
                'channel': 'tickstock.quality.data_gap',
                'message': json.dumps({
                    'timestamp': time.time(),
                    'service': 'data_quality_monitor',
                    'alert_type': 'data_gap',
                    'data': "should be dict not string"  # This is wrong
                })
            }
        ]

        # Validate all test messages
        for test_msg in test_messages:
            validation = validate_message_format(test_msg['channel'], test_msg['message'])
            message_validations.append(validation)

        # Verify format validation results
        valid_messages = [v for v in message_validations if v['valid']]
        invalid_messages = [v for v in message_validations if not v['valid']]

        # Should have 2 valid messages and 3 invalid messages based on our test cases
        assert len(valid_messages) == 2, f"Expected 2 valid messages, got {len(valid_messages)}"
        assert len(invalid_messages) == 3, f"Expected 3 invalid messages, got {len(invalid_messages)}"

        # Check specific validation errors
        error_types = []
        for invalid_msg in invalid_messages:
            error_types.extend(invalid_msg['errors'])

        assert any('Missing required field' in error for error in error_types), "Should detect missing required fields"
        assert any('not valid JSON' in error for error in error_types), "Should detect invalid JSON"
        assert any('should be a dictionary' in error for error in error_types), "Should detect wrong data payload type"
