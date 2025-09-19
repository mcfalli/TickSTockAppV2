#!/usr/bin/env python3
"""
Add integration logging to key components and clean up noisy logs.
"""

import re
import os

def update_redis_event_subscriber():
    """Update redis_event_subscriber.py with integration logging."""
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/redis_event_subscriber.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Add import at the top
    import_lines = """from src.core.services.integration_logger import (
    flow_logger, IntegrationPoint, log_redis_publish, log_websocket_delivery
)
"""

    # Add import after other imports
    if "from src.core.services.integration_logger import" not in content:
        content = content.replace("import redis\nfrom flask_socketio import SocketIO",
                                  f"import redis\nfrom flask_socketio import SocketIO\n{import_lines}")

    # Update _process_message to add integration logging
    old_process = """    def _process_message(self, message: Dict[str, Any]):
        \"\"\"Process a Redis message and forward to WebSocket.\"\"\"
        try:
            self.stats['events_received'] += 1"""

    new_process = """    def _process_message(self, message: Dict[str, Any]):
        \"\"\"Process a Redis message and forward to WebSocket.\"\"\"
        try:
            self.stats['events_received'] += 1

            # Start integration flow tracking
            flow_id = None"""

    content = content.replace(old_process, new_process)

    # Add flow tracking after event creation
    old_event_creation = """            event = TickStockEvent(
                event_type=event_type,
                source=event_data.get('source', 'unknown'),
                timestamp=event_data.get('timestamp', time.time()),
                data=event_data,
                channel=channel
            )

            # Process event
            self._handle_event(event)"""

    new_event_creation = """            event = TickStockEvent(
                event_type=event_type,
                source=event_data.get('source', 'unknown'),
                timestamp=event_data.get('timestamp', time.time()),
                data=event_data,
                channel=channel
            )

            # Integration logging
            if event_type == EventType.PATTERN_DETECTED:
                flow_id = flow_logger.start_flow(event_data)
                flow_logger.log_checkpoint(flow_id, IntegrationPoint.EVENT_RECEIVED, channel)
                flow_logger.log_checkpoint(flow_id, IntegrationPoint.EVENT_PARSED)

            # Process event
            self._handle_event(event)

            # Complete flow tracking
            if flow_id:
                flow_logger.complete_flow(flow_id)"""

    content = content.replace(old_event_creation, new_event_creation)

    # Update pattern event handler
    old_pattern_log = '            logger.info(f"REDIS-SUBSCRIBER: Pattern alert sent to {len(interested_users)} users - {pattern_name} on {symbol}")'
    new_pattern_log = '''            # Integration logging instead of verbose logging
            log_websocket_delivery(pattern_name, symbol, len(interested_users))'''

    content = content.replace(old_pattern_log, new_pattern_log)

    # Reduce other noisy logs to debug level
    content = content.replace('logger.info(f"REDIS-SUBSCRIBER: Pattern alert broadcasted (no filter) - {pattern_name} on {symbol}")',
                             'logger.debug(f"REDIS-SUBSCRIBER: Pattern alert broadcasted - {pattern_name} on {symbol}")')

    content = content.replace('logger.debug(f"REDIS-SUBSCRIBER: Handling {event.event_type.value} event from {event.source}")',
                             '# Handled by integration logger')

    with open(file_path, 'w') as f:
        f.write(content)

    print("[OK] Updated redis_event_subscriber.py with integration logging")

def update_websocket_broadcaster():
    """Update websocket_broadcaster.py with integration logging."""
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/websocket_broadcaster.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Add import
    if "from src.core.services.integration_logger import" not in content:
        import_line = "from src.core.services.integration_logger import IntegrationPoint, flow_logger\n"
        content = content.replace("import redis\n\n", f"import redis\n{import_line}\n")

    # Update broadcast_pattern_alert
    old_warning = "                logger.warning(f'WEBSOCKET-BROADCASTER: Pattern event missing pattern name, event keys: {pattern_data.keys()}')"
    new_warning = """                flow_logger.log_checkpoint('', IntegrationPoint.FIELD_MISSING,
                                         f'pattern name missing, keys: {pattern_data.keys()}')"""

    content = content.replace(old_warning, new_warning)

    # Update successful broadcast logging
    old_log = '            logger.info(f"WEBSOCKET-BROADCASTER: Pattern alert sent to {len(target_sessions)} users - {pattern_name} on {symbol}")'
    new_log = '''            # Integration logging
            if len(target_sessions) > 0:
                flow_logger.log_checkpoint('', IntegrationPoint.WEBSOCKET_DELIVERED,
                                         f"{pattern_name}@{symbol} to {len(target_sessions)} users")
            else:
                flow_logger.log_checkpoint('', IntegrationPoint.NO_SUBSCRIBERS,
                                         f"{pattern_name}@{symbol}")'''

    content = content.replace(old_log, new_log)

    # Reduce connection logs
    content = content.replace('logger.info(f"WEBSOCKET-BROADCASTER: User {user_id} connected (session: {session_id})")',
                             'logger.debug(f"WEBSOCKET-BROADCASTER: User {user_id} connected")')

    content = content.replace('logger.info(f"WEBSOCKET-BROADCASTER: User {user_id} disconnected (session: {session_id})")',
                             'logger.debug(f"WEBSOCKET-BROADCASTER: User {user_id} disconnected")')

    with open(file_path, 'w') as f:
        f.write(content)

    print("[OK] Updated websocket_broadcaster.py with integration logging")

def update_pattern_alert_manager():
    """Update pattern_alert_manager.py to reduce noise."""
    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/pattern_alert_manager.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Add integration logger import
    if "from src.core.services.integration_logger import" not in content:
        import_line = "from src.core.services.integration_logger import flow_logger, IntegrationPoint\n"
        content = content.replace("import redis\n", f"import redis\n{import_line}")

    # Update get_users_for_alert to use integration logging
    old_error = 'logger.error(f"PATTERN-ALERT-MANAGER: Error checking user {key}: {e}")'
    new_error = 'logger.debug(f"PATTERN-ALERT-MANAGER: Skipping user {key}: {e}")'

    content = content.replace(old_error, new_error)

    with open(file_path, 'w') as f:
        f.write(content)

    print("[OK] Updated pattern_alert_manager.py to reduce noise")

def create_integration_config():
    """Create configuration to enable/disable integration logging."""
    config_content = """# Integration Logging Configuration

# Enable/disable integration flow logging
INTEGRATION_LOGGING_ENABLED = True

# Log to separate file
INTEGRATION_LOG_FILE = True

# Integration log level (INFO, DEBUG, WARNING)
INTEGRATION_LOG_LEVEL = 'INFO'

# Show timing information for slow operations (ms)
INTEGRATION_SLOW_THRESHOLD = 100

# Pattern event tracking
TRACK_PATTERN_EVENTS = True

# Cache operation tracking
TRACK_CACHE_OPS = False

# Database query tracking
TRACK_DB_QUERIES = False
"""

    config_path = "C:/Users/McDude/TickStockAppV2/src/config/integration_logging.py"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, 'w') as f:
        f.write(config_content)

    print("[OK] Created integration logging configuration")

def update_app_startup():
    """Update app.py to initialize integration logging."""
    file_path = "C:/Users/McDude/TickStockAppV2/src/app.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Add integration logger setup
    setup_code = """    # Initialize integration logging
    try:
        from src.core.services.integration_logger import configure_integration_logging
        from src.config.integration_logging import (
            INTEGRATION_LOGGING_ENABLED,
            INTEGRATION_LOG_FILE,
            INTEGRATION_LOG_LEVEL
        )

        flow_logger = configure_integration_logging(
            enabled=INTEGRATION_LOGGING_ENABLED,
            log_file=INTEGRATION_LOG_FILE,
            log_level=INTEGRATION_LOG_LEVEL
        )

        logger.info(f"STARTUP: Integration logging configured (enabled={INTEGRATION_LOGGING_ENABLED})")
    except ImportError:
        logger.warning("STARTUP: Integration logging not available")
"""

    # Add after Flask app creation
    if "Integration logging configured" not in content:
        content = content.replace('    logger.info("STARTUP: LOGIN-MANAGER configured immediately after extensions")',
                                  f'{setup_code}\n    logger.info("STARTUP: LOGIN-MANAGER configured immediately after extensions")')

    with open(file_path, 'w') as f:
        f.write(content)

    print("[OK] Updated app.py with integration logging initialization")

def main():
    """Run all updates."""
    print("=" * 60)
    print("Adding Integration Logging to TickStockAppV2")
    print("=" * 60)

    try:
        # Create config first
        create_integration_config()

        # Update components
        update_redis_event_subscriber()
        update_websocket_broadcaster()
        update_pattern_alert_manager()
        update_app_startup()

        print("\n" + "=" * 60)
        print("[SUCCESS] Integration logging added!")
        print("=" * 60)
        print("\nIntegration logs will show flow like:")
        print("  [10:30:45] ← Event Received: tickstock.events.patterns")
        print("  [10:30:45] ✓ Event Parsed: Hammer@AAPL")
        print("  [10:30:45] → WebSocket Broadcast: 12 sessions")
        print("  [10:30:45] ✓ Delivered to User: Hammer@AAPL to 12 users")
        print("\nTo toggle: Edit src/config/integration_logging.py")

    except Exception as e:
        print(f"\n[ERROR] Failed to add integration logging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()