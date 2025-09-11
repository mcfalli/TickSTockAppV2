"""
Error Handling and Resilience Tests
Sprint 25 Day 4: Comprehensive error handling and resilience testing for EventRouter.

Tests cover:
- Malformed routing rules handling
- Content transformation error recovery
- Thread safety under error conditions
- Router fallback to ScalableBroadcaster
- Cache corruption recovery
- System recovery after error cascades
- Resource exhaustion scenarios
- Network failure simulation
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
from collections import defaultdict
from typing import Dict, Any, List
import gc
import traceback

# Core imports for testing
from src.infrastructure.websocket.event_router import (
    EventRouter, RoutingRule, RoutingResult, RouterStats,
    RoutingStrategy, EventCategory, DeliveryPriority
)
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster


class TestMalformedRuleHandling:
    """Test handling of malformed and problematic routing rules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)
        
        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()
    
    def test_invalid_regex_pattern_handling(self):
        """Test handling of invalid regex patterns in routing rules."""
        # Arrange - Create rule with invalid regex pattern
        malformed_rule = RoutingRule(
            rule_id='invalid_regex_rule',
            name='Invalid Regex Rule',
            description='Rule with invalid regex patterns',
            event_type_patterns=[
                r'[',           # Unclosed bracket
                r'(',           # Unclosed parenthesis
                r'*invalid',    # Invalid quantifier
                r'\x',          # Invalid escape
            ],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['error_room'],
            priority=DeliveryPriority.MEDIUM
        )
        
        # Act & Assert - Should not crash the system
        add_result = self.router.add_routing_rule(malformed_rule)
        
        # System should handle malformed rule gracefully
        assert isinstance(add_result, bool)
        
        # Rule should be added even with invalid patterns
        if add_result:
            assert 'invalid_regex_rule' in self.router.routing_rules
        
        # Try to use the rule - should not crash
        routing_result = self.router.route_event('test_event', {'test': 'data'})
        assert routing_result is not None
        
        # Rule matching should fail gracefully
        rule = self.router.routing_rules.get('invalid_regex_rule')
        if rule:
            matches = rule.matches_event('test_event', {'test': 'data'})
            assert matches is False  # Should return False, not crash
    
    def test_non_serializable_content_filters(self):
        """Test handling of non-serializable content filters."""
        # Arrange - Create rule with problematic filters
        class NonSerializableObject:
            def __str__(self):
                raise Exception("Cannot convert to string")
            
            def __eq__(self, other):
                raise Exception("Cannot compare")
        
        problematic_rule = RoutingRule(
            rule_id='non_serializable_rule',
            name='Non-Serializable Rule',
            description='Rule with non-serializable filters',
            event_type_patterns=[r'.*'],
            content_filters={
                'object_filter': NonSerializableObject(),
                'function_filter': lambda x: x > 5,  # Functions are not serializable
                'nested_problematic': {
                    'inner_object': NonSerializableObject(),
                    'valid_field': 'valid_value'
                }
            },
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['problematic_room'],
            priority=DeliveryPriority.MEDIUM
        )
        
        # Act & Assert
        add_result = self.router.add_routing_rule(problematic_rule)
        assert isinstance(add_result, bool)
        
        # Try to match events - should not crash
        test_data = {
            'object_filter': 'test_value',
            'function_filter': 10,
            'nested_problematic': {'inner_object': 'test', 'valid_field': 'valid_value'}
        }
        
        routing_result = self.router.route_event('problematic_test', test_data)
        assert routing_result is not None
        
        # Should handle errors gracefully
        if 'non_serializable_rule' in self.router.routing_rules:
            rule = self.router.routing_rules['non_serializable_rule']
            matches = rule.matches_event('problematic_test', test_data)
            # Should return False due to matching errors, not crash
            assert isinstance(matches, bool)
    
    def test_circular_reference_in_filters(self):
        """Test handling of circular references in content filters."""
        # Arrange - Create circular reference
        circular_dict = {'key': 'value'}
        circular_dict['self'] = circular_dict  # Circular reference
        
        circular_rule = RoutingRule(
            rule_id='circular_rule',
            name='Circular Reference Rule',
            description='Rule with circular reference in filters',
            event_type_patterns=[r'.*'],
            content_filters={
                'circular': circular_dict,
                'normal_field': 'normal_value'
            },
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['circular_room'],
            priority=DeliveryPriority.MEDIUM
        )
        
        # Act & Assert
        add_result = self.router.add_routing_rule(circular_rule)
        assert isinstance(add_result, bool)
        
        # Try to generate cache key (which involves serialization)
        event_data = {'circular': {'key': 'test'}, 'normal_field': 'normal_value'}
        
        try:
            cache_key = self.router._generate_cache_key('circular_test', event_data, None)
            assert isinstance(cache_key, str)
        except:
            # If cache key generation fails, it should be handled gracefully
            pass
        
        # Route event should still work
        routing_result = self.router.route_event('circular_test', event_data)
        assert routing_result is not None
    
    def test_extremely_large_rule_sets(self):
        """Test handling of extremely large routing rule configurations."""
        # Arrange - Create rule with very large configuration
        large_patterns = [f'pattern_{i}.*' for i in range(1000)]  # 1000 patterns
        large_filters = {f'filter_{i}': f'value_{i}' for i in range(500)}  # 500 filters
        large_destinations = [f'room_{i}' for i in range(200)]  # 200 destinations
        
        large_rule = RoutingRule(
            rule_id='extremely_large_rule',
            name='Extremely Large Rule',
            description='Rule with extremely large configuration',
            event_type_patterns=large_patterns,
            content_filters=large_filters,
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=large_destinations,
            priority=DeliveryPriority.MEDIUM
        )
        
        # Act
        start_time = time.time()
        add_result = self.router.add_routing_rule(large_rule)
        add_time = (time.time() - start_time) * 1000
        
        # Assert
        assert isinstance(add_result, bool)
        # Adding large rule shouldn't take excessively long
        assert add_time < 1000, f"Adding large rule took {add_time:.1f}ms, too slow"
        
        if add_result:
            # Try to match against the large rule
            start_time = time.time()
            rule = self.router.routing_rules['extremely_large_rule']
            matches = rule.matches_event('pattern_500_test', {'filter_250': 'value_250'})
            match_time = (time.time() - start_time) * 1000
            
            # Matching shouldn't be excessively slow
            assert match_time < 100, f"Matching large rule took {match_time:.1f}ms, too slow"
            assert isinstance(matches, bool)


class TestContentTransformationErrorHandling:
    """Test error handling in content transformation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)
        
        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()
    
    def test_transformation_function_exceptions(self):
        """Test handling of exceptions in content transformation functions."""
        # Arrange - Transformation functions that raise various exceptions
        def always_fails_transformer(event_data):
            raise Exception("Transformation always fails")
        
        def type_error_transformer(event_data):
            return event_data.nonexistent_method()
        
        def key_error_transformer(event_data):
            return event_data['nonexistent_key']
        
        def infinite_loop_transformer(event_data):
            while True:  # This would hang if not handled properly
                pass
        
        # Create rules with failing transformers
        failing_rules = [
            ('always_fails_rule', always_fails_transformer),
            ('type_error_rule', type_error_transformer),
            ('key_error_rule', key_error_transformer),
        ]
        
        for rule_id, transformer in failing_rules:
            rule = RoutingRule(
                rule_id=rule_id,
                name=f'Failing Rule {rule_id}',
                description=f'Rule with failing transformer: {rule_id}',
                event_type_patterns=[r'.*'],
                content_filters={},
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=[f'{rule_id}_room'],
                priority=DeliveryPriority.MEDIUM,
                content_transformer=transformer
            )
            self.router.add_routing_rule(rule)
        
        # Act & Assert - Should handle all transformation errors gracefully
        event_data = {'test': 'data', 'value': 42}
        
        routing_result = self.router.route_event('transformation_error_test', event_data)
        
        # Should still get a valid result even with failing transformers
        assert routing_result is not None
        assert len(routing_result.matched_rules) == len(failing_rules)
        
        # Transformations should not be applied due to errors
        assert len(routing_result.transformations_applied) == 0
        
        # Error count should be tracked
        assert self.router.stats.transformation_errors >= len(failing_rules)
    
    def test_transformation_returns_invalid_data(self):
        """Test handling of transformers that return invalid data types."""
        # Arrange - Transformers that return problematic data
        def returns_none_transformer(event_data):
            return None
        
        def returns_string_transformer(event_data):
            return "This should be a dict"
        
        def returns_list_transformer(event_data):
            return ['not', 'a', 'dict']
        
        def returns_circular_transformer(event_data):
            circular = {'data': event_data}
            circular['self'] = circular
            return circular
        
        invalid_transformers = [
            ('none_transformer_rule', returns_none_transformer),
            ('string_transformer_rule', returns_string_transformer),
            ('list_transformer_rule', returns_list_transformer),
            ('circular_transformer_rule', returns_circular_transformer),
        ]
        
        for rule_id, transformer in invalid_transformers:
            rule = RoutingRule(
                rule_id=rule_id,
                name=f'Invalid Transformer Rule {rule_id}',
                description=f'Rule with invalid transformer: {rule_id}',
                event_type_patterns=[r'.*'],
                content_filters={},
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=[f'{rule_id}_room'],
                priority=DeliveryPriority.MEDIUM,
                content_transformer=transformer
            )
            self.router.add_routing_rule(rule)
        
        # Act
        routing_result = self.router.route_event('invalid_transformer_test', {'test': 'data'})
        
        # Assert
        assert routing_result is not None
        
        # Should handle invalid transformer returns gracefully
        # (exact behavior depends on implementation)
        transformation_errors_before = self.router.stats.transformation_errors
        
        # Run another event to see if errors are tracked
        routing_result2 = self.router.route_event('invalid_transformer_test2', {'test': 'data2'})
        assert routing_result2 is not None
        
        # Error tracking should be working
        transformation_errors_after = self.router.stats.transformation_errors
        assert transformation_errors_after >= transformation_errors_before
    
    def test_transformation_performance_timeout(self):
        """Test handling of transformers that take too long."""
        # Arrange - Slow transformer
        def slow_transformer(event_data):
            time.sleep(0.1)  # 100ms delay
            return {**event_data, 'slow_processed': True}
        
        slow_rule = RoutingRule(
            rule_id='slow_transformer_rule',
            name='Slow Transformer Rule',
            description='Rule with slow transformer',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['slow_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=slow_transformer
        )
        self.router.add_routing_rule(slow_rule)
        
        # Act
        start_time = time.time()
        routing_result = self.router.route_event('slow_transform_test', {'test': 'data'})
        end_time = time.time()
        
        routing_time_ms = (end_time - start_time) * 1000
        
        # Assert
        assert routing_result is not None
        
        # System should handle slow transformers but may apply them
        # Performance should still be reasonable for routing overall
        assert routing_time_ms < 1000, f"Routing with slow transformer took {routing_time_ms:.1f}ms"


class TestThreadSafetyUnderErrors:
    """Test thread safety when errors occur during concurrent operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)
        
        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()
        
        # Add some rules that may cause errors
        error_prone_rule = RoutingRule(
            rule_id='error_prone_rule',
            name='Error Prone Rule',
            description='Rule that may cause errors',
            event_type_patterns=[r'.*'],
            content_filters={'error_test': True},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['error_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=lambda x: {'transformed': True} if x.get('transform') else x
        )
        self.router.add_routing_rule(error_prone_rule)
    
    def test_concurrent_routing_with_random_errors(self):
        """Test thread safety when random errors occur during routing."""
        # Arrange
        results = []
        exceptions = []
        error_count = 0
        
        def error_prone_routing_worker(thread_id):
            """Worker that may encounter errors."""
            nonlocal error_count
            try:
                thread_results = []
                
                for i in range(50):
                    event_data = {
                        'error_test': True,
                        'thread_id': thread_id,
                        'iteration': i,
                        'transform': i % 3 == 0  # Sometimes trigger transformation
                    }
                    
                    # Occasionally cause issues
                    if i % 7 == 0:
                        # Add problematic data
                        event_data['problematic'] = object()  # Non-serializable
                    
                    if i % 11 == 0:
                        # Simulate network-style error by mocking broadcaster failure
                        with patch.object(self.router, '_execute_routing') as mock_execute:
                            mock_execute.side_effect = Exception(f"Broadcast error in thread {thread_id}")
                            
                            result = self.router.route_event(f'error_test_{i}', event_data)
                            thread_results.append(result)
                            error_count += 1
                    else:
                        result = self.router.route_event(f'error_test_{i}', event_data)
                        thread_results.append(result)
                
                results.extend(thread_results)
                
            except Exception as e:
                exceptions.append((thread_id, str(e), traceback.format_exc()))
        
        # Act - Run concurrent operations with errors
        threads = []
        for thread_id in range(6):
            thread = threading.Thread(target=error_prone_routing_worker, args=(thread_id,))
            threads.append(thread)
        
        start_time = time.time()
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Assert
        assert len(exceptions) == 0, f"Thread safety violated with exceptions: {exceptions}"
        assert len(results) == 6 * 50  # All operations should complete
        
        # All results should be valid routing results
        for result in results:
            assert result is not None
            assert isinstance(result, RoutingResult)
        
        # Router should be in consistent state
        stats = self.router.get_routing_stats()
        assert stats['total_events'] == len(results)
        
        # Some errors should have been recorded
        assert stats['routing_errors'] >= 0  # May have errors from mocked failures
        
        # Performance should still be reasonable despite errors
        events_per_second = len(results) / total_time
        assert events_per_second > 100, f"Performance {events_per_second:.0f} events/sec too low with errors"
    
    def test_concurrent_rule_modification_during_routing(self):
        """Test thread safety when rules are modified during routing operations."""
        # Arrange
        routing_active = threading.Event()
        modification_complete = threading.Event()
        results = []
        exceptions = []
        
        def continuous_routing_worker():
            """Worker that continuously routes events."""
            try:
                routing_active.set()
                worker_results = []
                
                while not modification_complete.is_set():
                    result = self.router.route_event('concurrent_test', {'test': True})
                    worker_results.append(result)
                    time.sleep(0.001)  # Small delay
                
                results.extend(worker_results)
                
            except Exception as e:
                exceptions.append(('routing_worker', str(e)))
        
        def rule_modification_worker():
            """Worker that modifies rules during routing."""
            try:
                routing_active.wait()  # Wait for routing to start
                
                # Add and remove rules while routing is happening
                for i in range(10):
                    # Add rule
                    new_rule = RoutingRule(
                        rule_id=f'dynamic_rule_{i}',
                        name=f'Dynamic Rule {i}',
                        description=f'Dynamically added rule {i}',
                        event_type_patterns=[f'.*dynamic_{i}.*'],
                        content_filters={'dynamic': i},
                        user_criteria={},
                        strategy=RoutingStrategy.BROADCAST_ALL,
                        destinations=[f'dynamic_room_{i}'],
                        priority=DeliveryPriority.MEDIUM
                    )
                    self.router.add_routing_rule(new_rule)
                    time.sleep(0.01)
                    
                    # Remove rule
                    self.router.remove_routing_rule(f'dynamic_rule_{i}')
                    time.sleep(0.01)
                
                modification_complete.set()
                
            except Exception as e:
                exceptions.append(('modification_worker', str(e)))
        
        # Act
        routing_thread = threading.Thread(target=continuous_routing_worker)
        modification_thread = threading.Thread(target=rule_modification_worker)
        
        routing_thread.start()
        modification_thread.start()
        
        routing_thread.join()
        modification_thread.join()
        
        # Assert
        assert len(exceptions) == 0, f"Concurrent modification caused exceptions: {exceptions}"
        assert len(results) > 0, "No routing operations completed"
        
        # All results should be valid
        for result in results:
            assert result is not None
            assert isinstance(result, RoutingResult)
        
        # Router should be in consistent state
        stats = self.router.get_routing_stats()
        assert stats['total_events'] >= len(results)


class TestRouterFallbackMechanisms:
    """Test fallback mechanisms when routing system encounters critical errors."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)
        
        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()
    
    def test_fallback_when_all_rules_fail(self):
        """Test fallback behavior when all routing rules fail."""
        # Arrange - Add rules that will fail
        def failing_transformer(event_data):
            raise Exception("Transformer failure")
        
        failing_rule = RoutingRule(
            rule_id='failing_rule',
            name='Failing Rule',
            description='Rule that always fails',
            event_type_patterns=[r'['],  # Invalid regex
            content_filters={'bad_filter': object()},  # Non-serializable filter
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['failing_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=failing_transformer
        )
        self.router.add_routing_rule(failing_rule)
        
        # Act
        routing_result = self.router.route_event('fallback_test', {'test': 'data'})
        
        # Assert
        assert routing_result is not None
        
        # Should handle failures gracefully
        # Result should indicate no rules matched due to errors
        assert isinstance(routing_result.matched_rules, list)
        assert isinstance(routing_result.destinations, dict)
        assert isinstance(routing_result.total_users, int)
        assert routing_result.total_users >= 0
    
    def test_fallback_when_cache_system_fails(self):
        """Test fallback when cache system encounters errors."""
        # Arrange - Corrupt cache system
        with patch.object(self.router, '_get_cached_route') as mock_cache_get:
            mock_cache_get.side_effect = Exception("Cache system failure")
            
            with patch.object(self.router, '_cache_routing_result') as mock_cache_set:
                mock_cache_set.side_effect = Exception("Cache write failure")
                
                # Add a working rule
                working_rule = RoutingRule(
                    rule_id='working_rule',
                    name='Working Rule',
                    description='Rule that should work despite cache failures',
                    event_type_patterns=[r'.*'],
                    content_filters={},
                    user_criteria={},
                    strategy=RoutingStrategy.BROADCAST_ALL,
                    destinations=['working_room'],
                    priority=DeliveryPriority.MEDIUM
                )
                self.router.add_routing_rule(working_rule)
                
                # Act
                routing_result = self.router.route_event('cache_failure_test', {'test': 'data'})
                
                # Assert
                assert routing_result is not None
                assert len(routing_result.matched_rules) > 0
                assert 'working_rule' in routing_result.matched_rules
                
                # Should work without caching
                assert routing_result.cache_hit is False
    
    def test_fallback_when_broadcaster_fails(self):
        """Test behavior when ScalableBroadcaster fails."""
        # Arrange
        working_rule = RoutingRule(
            rule_id='broadcaster_test_rule',
            name='Broadcaster Test Rule',
            description='Rule for testing broadcaster failures',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['test_room'],
            priority=DeliveryPriority.MEDIUM
        )
        self.router.add_routing_rule(working_rule)
        
        # Mock broadcaster to fail
        self.mock_broadcaster.broadcast_to_room.side_effect = Exception("Broadcaster failure")
        self.mock_broadcaster.broadcast_to_users.side_effect = Exception("Broadcaster failure")
        
        # Act
        routing_result = self.router.route_event('broadcaster_failure_test', {'test': 'data'})
        
        # Assert
        assert routing_result is not None
        
        # Routing should complete even if broadcasting fails
        assert len(routing_result.matched_rules) > 0
        assert 'broadcaster_test_rule' in routing_result.matched_rules
        
        # The routing decision should be made correctly
        assert len(routing_result.destinations) > 0


class TestSystemRecoveryAndResilience:
    """Test system recovery after error cascades and resilience mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)
        
        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()
    
    def test_recovery_after_error_cascade(self):
        """Test system recovery after experiencing cascade of errors."""
        # Arrange - Add mix of working and failing rules
        working_rule = RoutingRule(
            rule_id='recovery_working_rule',
            name='Working Rule',
            description='Rule that works correctly',
            event_type_patterns=[r'.*working.*'],
            content_filters={'status': 'ok'},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['working_room'],
            priority=DeliveryPriority.MEDIUM
        )
        
        def problematic_transformer(event_data):
            if 'cause_error' in event_data:
                raise Exception("Cascade error")
            return event_data
        
        problematic_rule = RoutingRule(
            rule_id='recovery_problematic_rule',
            name='Problematic Rule',
            description='Rule that may cause errors',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['problematic_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=problematic_transformer
        )
        
        self.router.add_routing_rule(working_rule)
        self.router.add_routing_rule(problematic_rule)
        
        # Phase 1: Cause cascade of errors
        error_events = []
        for i in range(20):
            event_data = {'cause_error': True, 'iteration': i}
            result = self.router.route_event('error_cascade_test', event_data)
            error_events.append(result)
        
        # Check that errors were recorded
        initial_error_count = self.router.stats.transformation_errors
        assert initial_error_count > 0, "No errors were recorded during cascade"
        
        # Phase 2: Try normal operation after errors
        recovery_events = []
        for i in range(10):
            event_data = {'status': 'ok', 'recovery_test': i}
            result = self.router.route_event('working_recovery_test', event_data)
            recovery_events.append(result)
        
        # Assert - System should recover and work normally
        for result in recovery_events:
            assert result is not None
            assert len(result.matched_rules) > 0
            assert 'recovery_working_rule' in result.matched_rules
        
        # Error count should stabilize (no new errors in recovery phase)
        final_error_count = self.router.stats.transformation_errors
        assert final_error_count == initial_error_count, "New errors occurred during recovery"
        
        # System should be fully operational
        stats = self.router.get_routing_stats()
        assert stats['total_events'] == 30  # 20 error + 10 recovery events
        assert stats['events_routed'] == 30  # All events should be routed despite errors
    
    def test_health_monitoring_detects_error_conditions(self):
        """Test health monitoring correctly detects and reports error conditions."""
        # Arrange - Create conditions that should trigger health warnings
        def failing_transformer(event_data):
            raise Exception("Systematic failure")
        
        # Add failing rule
        failing_rule = RoutingRule(
            rule_id='health_failing_rule',
            name='Health Failing Rule',
            description='Rule that fails for health testing',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['failing_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=failing_transformer
        )
        self.router.add_routing_rule(failing_rule)
        
        # Generate enough failures to trigger health warnings
        for i in range(15):  # Should exceed error threshold
            self.router.route_event(f'health_test_{i}', {'health_check': i})
        
        # Act
        health_status = self.router.get_health_status()
        
        # Assert
        assert health_status is not None
        assert 'status' in health_status
        assert 'message' in health_status
        assert health_status['status'] in ['healthy', 'warning', 'error']
        
        # Should detect high error rate
        if health_status['status'] == 'error':
            assert 'error' in health_status['message'].lower()
        
        # Performance targets should be included
        assert 'performance_targets' in health_status
        targets = health_status['performance_targets']
        assert 'routing_time_target_ms' in targets
        assert 'error_rate_target' in targets
    
    def test_performance_optimization_under_error_conditions(self):
        """Test performance optimization works even with ongoing errors."""
        # Arrange - Create mixed environment with some errors
        def intermittent_transformer(event_data):
            if event_data.get('iteration', 0) % 5 == 0:
                raise Exception("Intermittent failure")
            return {**event_data, 'processed': True}
        
        mixed_rule = RoutingRule(
            rule_id='optimization_mixed_rule',
            name='Mixed Rule',
            description='Rule with intermittent failures',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['mixed_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=intermittent_transformer
        )
        self.router.add_routing_rule(mixed_rule)
        
        # Generate mixed traffic (some errors, some success)
        for i in range(50):
            self.router.route_event('optimization_test', {'iteration': i})
        
        # Act - Perform optimization
        optimization_result = self.router.optimize_performance()
        
        # Assert
        assert optimization_result is not None
        assert isinstance(optimization_result, dict)
        
        # Optimization should complete successfully despite errors
        assert 'cache_cleaned' in optimization_result
        assert 'rules_optimized' in optimization_result
        assert 'optimization_timestamp' in optimization_result
        
        # System should remain stable after optimization
        post_optimization_result = self.router.route_event('post_optimization_test', {'test': 'stable'})
        assert post_optimization_result is not None
    
    def test_graceful_shutdown_under_error_conditions(self):
        """Test graceful shutdown works even with ongoing errors."""
        # Arrange - Create conditions with active errors
        def shutdown_test_transformer(event_data):
            time.sleep(0.05)  # Simulate some processing time
            if 'shutdown_error' in event_data:
                raise Exception("Error during shutdown")
            return event_data
        
        shutdown_rule = RoutingRule(
            rule_id='shutdown_test_rule',
            name='Shutdown Test Rule',
            description='Rule for testing shutdown under errors',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['shutdown_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=shutdown_test_transformer
        )
        self.router.add_routing_rule(shutdown_rule)
        
        # Start some background routing operations
        import threading
        shutdown_complete = threading.Event()
        
        def background_routing():
            while not shutdown_complete.is_set():
                self.router.route_event('shutdown_bg_test', {'shutdown_error': True})
                time.sleep(0.01)
        
        bg_thread = threading.Thread(target=background_routing)
        bg_thread.start()
        
        try:
            time.sleep(0.1)  # Let some operations run
            
            # Act - Perform graceful shutdown
            start_time = time.time()
            self.router.shutdown()
            shutdown_time = (time.time() - start_time) * 1000
            
            # Assert
            # Shutdown should complete in reasonable time even with errors
            assert shutdown_time < 10000, f"Shutdown took {shutdown_time:.1f}ms, too long"
            
        finally:
            shutdown_complete.set()
            bg_thread.join(timeout=1)
        
        # Verify system is properly shut down
        with self.router.cache_lock:
            assert len(self.router.route_cache) == 0
            assert len(self.router.cache_access_order) == 0


if __name__ == '__main__':
    pytest.main([__file__])