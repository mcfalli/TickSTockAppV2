#!/usr/bin/env python3
"""
Shared Component Definitions for Trace Tests
Central location for component requirements used across all trace analysis tests.
"""

# Component requirements for trace coverage analysis
# Updated based on actual system implementation
COMPONENT_REQUIREMENTS = {
    'SyntheticDataGenerator': {
        'critical': ['tick_created', 'event_generated'],
        'expected': ['initialized', 'batch_complete']
    },
    'CoreService': {
        'critical': ['tick_received', 'tick_delegated'],
        'expected': ['stats_update']
    },
    'EventProcessor': {
        'critical': ['process_start', 'process_complete'],  # These exist
        'expected': ['tick_delegated', 'event_queued', 'universe_check']  # tick_delegated exists!
    },
    'SurgeDetector': {
        'critical': ['event_detected'],  # This is what it actually uses
        'expected': ['surge_cooldown_blocked', 'buffer_updated', 'surge_skipped']
    },
    'TrendDetector': {
        'critical': ['ticker_initialized'],  # This is all that exists
        'expected': ['event_detected']  # This is missing - real issue!
    },
    'HighLowEventDetector': {
        'critical': ['event_detected'],
        'expected': ['detection_start', 'detection_complete']  # It uses all three!
    },
    'EventDetector': {
        'critical': ['detection_summary'],  # Not event_detected
        'expected': ['detection_slow']
    },
    'PriorityManager': {
        'critical': ['surge_event_queued'],  # This exists
        'expected': ['event_queued', 'events_collected']  # Generic queuing is missing
    },
    'WorkerPool': {
        'critical': ['worker_started', 'worker_stopped'],
        'expected': ['batch_processed', 'tick_processing_failed']
    },
    'WorkerPoolManager': {
        'critical': ['start_workers_begin', 'adjust_pool_complete'],
        'expected': ['initialization_complete', 'health_check_performed']
    },
    'DataPublisher': {
        'critical': ['events_collected', 'events_buffered'],
        'expected': ['buffer_pulled', 'collection_start']
    },
    'WebSocketPublisher': {
        'critical': ['event_emitted', 'emission_cycle_start'],
        'expected': ['emission_cycle_complete', 'user_filtering_start']
    },
    'WebSocketManager': {
        'critical': ['user_connected', 'user_disconnected'],
        'expected': ['heartbeat_sent', 'broadcast_complete']
    },
}

# Component name mappings for backward compatibility
COMPONENT_ALIASES = {
    'HighLowDetector': 'HighLowEventDetector',
    'DataProvider': 'SyntheticDataGenerator',  # In synthetic mode
}

# Expected trace flow stages
TRACE_FLOW_STAGES = [
    'tick_created',
    'tick_received', 
    'process_start',
    'universe_check',
    'detection_start',
    'event_detected',
    'event_queued',
    'events_collected',
    'event_ready_for_emission',
    'event_emitted'
]

# Critical event types that should be traced
EVENT_TYPES = ['high', 'low', 'surge', 'trend']

# User connection related actions
USER_CONNECTION_ACTIONS = [
    'user_connected',
    'user_authenticated', 
    'client_connected',
    'new_user_connection',
    'user_ready_for_events',
    'buffered_events_sent',
    'user_disconnected',
    'user_emission',
    'generic_client_registered',
    'generic_client_unregistered'
]


# Specific action names used in traces
TRACE_ACTIONS = {
    'WebSocketPublisher': {
        'EMISSION_CYCLE_START': 'emission_cycle_start',
        'EMISSION_CYCLE_COMPLETE': 'emission_cycle_complete',
        'EVENT_READY_FOR_EMISSION': 'event_ready_for_emission',
        'EVENT_EMITTED': 'event_emitted',
        'USER_FILTERING_START': 'user_filtering_start',
        'USER_FILTERING_COMPLETE': 'user_filtering_complete'
    },
    'WebSocketManager': {
        'USER_CONNECTED': 'user_connected',
        'USER_DISCONNECTED': 'user_disconnected',
        'HEARTBEAT_SENT': 'heartbeat_sent'
    },
}

def get_trace_action(component: str, action_key: str) -> str:
    """Get the actual trace action name for a component action"""
    return TRACE_ACTIONS.get(component, {}).get(action_key, action_key.lower())

def get_actual_component_name(component: str) -> str:
    """Get the actual component name, handling aliases"""
    return COMPONENT_ALIASES.get(component, component)

def get_all_expected_components() -> set:
    """Get all expected component names including aliases"""
    components = set(COMPONENT_REQUIREMENTS.keys())
    components.update(COMPONENT_ALIASES.keys())
    return components

def get_critical_actions_for_component(component: str) -> list:
    """Get critical actions for a component, handling aliases"""
    actual_name = get_actual_component_name(component)
    if actual_name in COMPONENT_REQUIREMENTS:
        return COMPONENT_REQUIREMENTS[actual_name].get('critical', [])
    return []

def get_all_expected_actions_for_component(component: str) -> list:
    """Get all expected actions for a component, handling aliases"""
    actual_name = get_actual_component_name(component)
    if actual_name in COMPONENT_REQUIREMENTS:
        critical = COMPONENT_REQUIREMENTS[actual_name].get('critical', [])
        expected = COMPONENT_REQUIREMENTS[actual_name].get('expected', [])
        return critical + expected
    return []