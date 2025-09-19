"""
Database Integration Logger
Database persistence for integration event tracking between TickStockPL and TickStockAppV2.

Purpose: Provides database audit trail alongside the file-based integration logging,
enabling integration flow analysis through the integration_events table.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from enum import Enum

from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

class IntegrationEventType(Enum):
    """Event types for database integration logging."""
    PATTERN_DETECTED = "pattern_detected"
    BACKTEST_PROGRESS = "backtest_progress"
    BACKTEST_RESULT = "backtest_result"
    SYSTEM_HEALTH = "system_health"
    HEARTBEAT = "heartbeat"
    SUBSCRIPTION_ACTIVE = "subscription_active"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"

class IntegrationCheckpoint(Enum):
    """Integration checkpoints for database logging."""
    # Redis → TickStockAppV2
    EVENT_RECEIVED = "EVENT_RECEIVED"
    EVENT_PARSED = "EVENT_PARSED"

    # Processing
    USER_FILTER_START = "USER_FILTER_START"
    USER_FILTER_RESULT = "USER_FILTER_RESULT"

    # WebSocket Delivery
    WEBSOCKET_BROADCAST = "WEBSOCKET_BROADCAST"
    WEBSOCKET_DELIVERED = "WEBSOCKET_DELIVERED"

    # Errors/Warnings
    STRUCTURE_MISMATCH = "STRUCTURE_MISMATCH"
    FIELD_MISSING = "FIELD_MISSING"
    NO_SUBSCRIBERS = "NO_SUBSCRIBERS"

class DatabaseIntegrationLogger:
    """
    Database integration logger for tracking pattern event flow through TickStockAppV2.

    Logs integration checkpoints to the integration_events table for audit trail
    and performance analysis of the TickStockPL → TickStockAppV2 integration.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize database integration logger."""
        self.config = config
        self.enabled = True
        self.db = None

        try:
            self.db = TickStockDatabase(config)
            self._test_database_table()
            logger.info("DATABASE-INTEGRATION: Logger initialized successfully")
        except Exception as e:
            logger.error(f"DATABASE-INTEGRATION: Failed to initialize: {e}")
            self.enabled = False

    def _test_database_table(self):
        """Test that the integration_events table exists and is accessible."""
        try:
            with self.db.get_connection() as conn:
                from sqlalchemy import text
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'integration_events'
                    )
                """))
                table_exists = result.scalar()

                if not table_exists:
                    logger.warning("DATABASE-INTEGRATION: integration_events table not found")
                    self.enabled = False
                    return

                # Test the stored procedure exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.routines
                        WHERE routine_schema = 'public'
                        AND routine_name = 'log_integration_event'
                    )
                """))
                function_exists = result.scalar()

                if not function_exists:
                    logger.warning("DATABASE-INTEGRATION: log_integration_event function not found")
                    self.enabled = False
                    return

                logger.info("DATABASE-INTEGRATION: Table and function verified")

        except Exception as e:
            logger.error(f"DATABASE-INTEGRATION: Table test failed: {e}")
            self.enabled = False

    def is_enabled(self) -> bool:
        """Check if database integration logging is enabled."""
        return self.enabled and self.db is not None

    def log_checkpoint(self, flow_id: Optional[str], event_type: IntegrationEventType,
                      checkpoint: IntegrationCheckpoint, channel: Optional[str] = None,
                      symbol: Optional[str] = None, pattern_name: Optional[str] = None,
                      confidence: Optional[float] = None, user_count: Optional[int] = None,
                      details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log integration checkpoint to database.

        Args:
            flow_id: Flow identifier from TickStockPL (if available)
            event_type: Type of integration event
            checkpoint: Integration checkpoint being logged
            channel: Redis channel name
            symbol: Stock symbol
            pattern_name: Pattern name
            confidence: Pattern confidence
            user_count: Number of users notified
            details: Additional details as JSONB

        Returns:
            bool: Success status
        """
        if not self.is_enabled():
            return False

        try:
            # Generate flow_id if not provided
            if not flow_id:
                flow_id = str(uuid.uuid4())

            # Ensure checkpoint is an enum - handle string fallback
            if isinstance(checkpoint, str):
                # Try to find matching enum value
                checkpoint_enum = None
                for cp in IntegrationCheckpoint:
                    if cp.value == checkpoint:
                        checkpoint_enum = cp
                        break
                if checkpoint_enum is None:
                    # Fallback to default
                    checkpoint_enum = IntegrationCheckpoint.EVENT_RECEIVED
                    logger.warning(f"DATABASE-INTEGRATION: Unknown checkpoint string '{checkpoint}', using EVENT_RECEIVED")
                checkpoint = checkpoint_enum

            # Ensure event_type is an enum - handle string fallback
            if isinstance(event_type, str):
                # Try to find matching enum value
                event_type_enum = None
                for et in IntegrationEventType:
                    if et.value == event_type:
                        event_type_enum = et
                        break
                if event_type_enum is None:
                    # Fallback to default
                    event_type_enum = IntegrationEventType.HEARTBEAT
                    logger.warning(f"DATABASE-INTEGRATION: Unknown event_type string '{event_type}', using HEARTBEAT")
                event_type = event_type_enum

            # Prepare details as JSON
            details_json = details if details else {}

            with self.db.get_connection() as conn:
                from sqlalchemy import text
                import json

                # Convert details to JSON string if needed
                details_json_str = json.dumps(details_json) if details_json else None

                # Call the stored procedure
                conn.execute(text("""
                    SELECT log_integration_event(
                        :flow_id, :event_type, :source_system, :checkpoint,
                        :channel, :symbol, :pattern_name, :confidence,
                        :user_count, :details
                    )
                """), {
                    'flow_id': flow_id,
                    'event_type': event_type.value,
                    'source_system': 'TickStockAppV2',
                    'checkpoint': checkpoint.value,
                    'channel': channel,
                    'symbol': symbol,
                    'pattern_name': pattern_name,
                    'confidence': confidence,
                    'user_count': user_count,
                    'details': details_json_str
                })

                conn.commit()

            return True

        except Exception as e:
            # Handle both enum and string checkpoint values in error message
            checkpoint_str = checkpoint.value if hasattr(checkpoint, 'value') else str(checkpoint)
            logger.error(f"DATABASE-INTEGRATION: Failed to log checkpoint {checkpoint_str}: {e}")
            return False

    def extract_flow_id(self, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract flow_id from TickStockPL event data.

        Args:
            event_data: Event data from Redis message

        Returns:
            Optional[str]: Flow ID if found
        """
        try:
            # Check multiple possible locations for flow_id
            flow_id = None

            # Direct in event data
            if 'flow_id' in event_data:
                flow_id = event_data['flow_id']

            # In nested data section
            elif 'data' in event_data and isinstance(event_data['data'], dict):
                if 'flow_id' in event_data['data']:
                    flow_id = event_data['data']['flow_id']

            # In metadata section
            elif 'metadata' in event_data and isinstance(event_data['metadata'], dict):
                if 'flow_id' in event_data['metadata']:
                    flow_id = event_data['metadata']['flow_id']

            return flow_id

        except Exception as e:
            logger.debug(f"DATABASE-INTEGRATION: Error extracting flow_id: {e}")
            return None

    def log_pattern_received(self, event_data: Dict[str, Any], channel: str) -> Optional[str]:
        """
        Log pattern event reception with extracted flow_id.

        Args:
            event_data: Complete event data from Redis
            channel: Redis channel name

        Returns:
            Optional[str]: Flow ID for tracking
        """
        if not self.is_enabled():
            return None

        try:
            # Extract flow_id from TickStockPL event
            flow_id = self.extract_flow_id(event_data)

            # Extract pattern data (handle nested structure)
            pattern_data = event_data.get('data', {}) if 'data' in event_data else event_data
            if isinstance(pattern_data, dict) and 'data' in pattern_data:
                pattern_data = pattern_data['data']

            symbol = pattern_data.get('symbol')
            pattern_name = pattern_data.get('pattern')
            confidence = pattern_data.get('confidence')

            # Log EVENT_RECEIVED checkpoint
            success = self.log_checkpoint(
                flow_id=flow_id,
                event_type=IntegrationEventType.PATTERN_DETECTED,
                checkpoint=IntegrationCheckpoint.EVENT_RECEIVED,
                channel=channel,
                symbol=symbol,
                pattern_name=pattern_name,
                confidence=confidence,
                details={'source': event_data.get('source', 'TickStockPL')}
            )

            if success:
                logger.debug(f"DATABASE-INTEGRATION: Logged EVENT_RECEIVED for {pattern_name}@{symbol}")
                return flow_id

        except Exception as e:
            logger.error(f"DATABASE-INTEGRATION: Error logging pattern received: {e}")

        return None

    def log_pattern_parsed(self, flow_id: Optional[str], symbol: str, pattern_name: str,
                          confidence: float) -> bool:
        """
        Log successful pattern parsing.

        Args:
            flow_id: Flow identifier
            symbol: Stock symbol
            pattern_name: Pattern name
            confidence: Pattern confidence

        Returns:
            bool: Success status
        """
        return self.log_checkpoint(
            flow_id=flow_id,
            event_type=IntegrationEventType.PATTERN_DETECTED,
            checkpoint=IntegrationCheckpoint.EVENT_PARSED,
            symbol=symbol,
            pattern_name=pattern_name,
            confidence=confidence
        )

    def log_websocket_delivery(self, flow_id: Optional[str], symbol: str,
                              pattern_name: str, user_count: int) -> bool:
        """
        Log WebSocket delivery to users.

        Args:
            flow_id: Flow identifier
            symbol: Stock symbol
            pattern_name: Pattern name
            user_count: Number of users notified

        Returns:
            bool: Success status
        """
        return self.log_checkpoint(
            flow_id=flow_id,
            event_type=IntegrationEventType.PATTERN_DETECTED,
            checkpoint=IntegrationCheckpoint.WEBSOCKET_DELIVERED,
            symbol=symbol,
            pattern_name=pattern_name,
            user_count=user_count
        )

    def log_system_event(self, event_type: str, source_system: str, checkpoint: str,
                        channel: str = None, details: Dict[str, Any] = None) -> bool:
        """
        Log system-level events like heartbeats, subscriptions, etc.

        Args:
            event_type: Type of system event (heartbeat, subscription_active, etc.)
            source_system: Source system (TickStockAppV2)
            checkpoint: Event checkpoint (SUBSCRIBER_ALIVE, CHANNEL_SUBSCRIBED, etc.)
            channel: Optional Redis channel name
            details: Optional event details

        Returns:
            bool: Success status
        """
        if not self.is_enabled():
            return False

        try:
            # Use a proper UUID for system events
            flow_id = str(uuid.uuid4())

            # Map string event_type to enum
            event_type_enum = IntegrationEventType.HEARTBEAT
            if event_type == 'subscription_active':
                event_type_enum = IntegrationEventType.SUBSCRIPTION_ACTIVE
            elif event_type == 'subscription_confirmed':
                event_type_enum = IntegrationEventType.SUBSCRIPTION_CONFIRMED
            elif event_type == 'system_health':
                event_type_enum = IntegrationEventType.SYSTEM_HEALTH

            # Map string checkpoint to enum - handle common checkpoint values
            checkpoint_enum = None
            try:
                # First try to find exact match in enum values
                for cp in IntegrationCheckpoint:
                    if cp.value == checkpoint:
                        checkpoint_enum = cp
                        break

                # If no exact match, try to map common string values
                if checkpoint_enum is None:
                    checkpoint_mapping = {
                        'SUBSCRIBER_ALIVE': IntegrationCheckpoint.EVENT_RECEIVED,
                        'CHANNEL_SUBSCRIBED': IntegrationCheckpoint.SUBSCRIPTION_CONFIRMED,
                        'HEARTBEAT': IntegrationCheckpoint.EVENT_RECEIVED,
                    }
                    checkpoint_enum = checkpoint_mapping.get(checkpoint, IntegrationCheckpoint.EVENT_RECEIVED)

            except Exception:
                # Fallback to default checkpoint
                checkpoint_enum = IntegrationCheckpoint.EVENT_RECEIVED

            return self.log_checkpoint(
                flow_id=flow_id,
                event_type=event_type_enum,
                checkpoint=checkpoint_enum,
                channel=channel,
                details=details
            )

        except Exception as e:
            logger.error(f"DATABASE-INTEGRATION: Error logging system event: {e}")
            return False

    def get_recent_flows(self, limit: int = 50) -> list:
        """
        Get recent integration flows for monitoring.

        Args:
            limit: Maximum number of flows to return

        Returns:
            list: Recent integration flows
        """
        if not self.is_enabled():
            return []

        try:
            with self.db.get_connection() as conn:
                from sqlalchemy import text
                result = conn.execute(text("""
                    SELECT
                        flow_id,
                        symbol,
                        pattern_name,
                        MIN(timestamp) as start_time,
                        MAX(timestamp) as end_time,
                        COUNT(*) as checkpoint_count,
                        ARRAY_AGG(checkpoint ORDER BY timestamp) as flow_path
                    FROM integration_events
                    WHERE source_system = 'TickStockAppV2'
                    AND timestamp >= NOW() - INTERVAL '1 hour'
                    GROUP BY flow_id, symbol, pattern_name
                    ORDER BY start_time DESC
                    LIMIT :limit
                """), {'limit': limit})

                flows = []
                for row in result:
                    flows.append({
                        'flow_id': row[0],
                        'symbol': row[1],
                        'pattern_name': row[2],
                        'start_time': row[3].isoformat() if row[3] else None,
                        'end_time': row[4].isoformat() if row[4] else None,
                        'checkpoint_count': row[5],
                        'flow_path': row[6]
                    })

                return flows

        except Exception as e:
            logger.error(f"DATABASE-INTEGRATION: Error getting recent flows: {e}")
            return []

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for database integration logging."""
        if not self.is_enabled():
            return {
                'status': 'disabled',
                'database_connected': False,
                'table_exists': False,
                'last_check': time.time()
            }

        try:
            with self.db.get_connection() as conn:
                from sqlalchemy import text
                # Test basic connectivity
                conn.execute(text("SELECT 1"))

                # Check recent activity
                result = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM integration_events
                    WHERE timestamp >= NOW() - INTERVAL '5 minutes'
                    AND source_system = 'TickStockAppV2'
                """))
                recent_events = result.scalar()

                return {
                    'status': 'healthy',
                    'database_connected': True,
                    'table_exists': True,
                    'recent_events': recent_events,
                    'last_check': time.time()
                }

        except Exception as e:
            logger.error(f"DATABASE-INTEGRATION: Health check failed: {e}")
            return {
                'status': 'error',
                'database_connected': False,
                'error': str(e),
                'last_check': time.time()
            }

# Global instance
database_integration_logger = None

def initialize_database_integration_logger(config: Dict[str, Any]) -> DatabaseIntegrationLogger:
    """Initialize the global database integration logger."""
    global database_integration_logger
    database_integration_logger = DatabaseIntegrationLogger(config)
    return database_integration_logger

def get_database_integration_logger() -> Optional[DatabaseIntegrationLogger]:
    """Get the global database integration logger instance."""
    return database_integration_logger