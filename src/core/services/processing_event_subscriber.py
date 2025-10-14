"""
Processing Event Subscriber for TickStockPL Integration
Sprint 33 - Real Redis Integration (No Mocks)

Subscribes to TickStockPL processing events and updates dashboard state.
"""

import json
import logging
import threading
from datetime import datetime
from enum import Enum
from typing import Any

import psycopg2
import redis
from psycopg2.extras import RealDictCursor

from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)


class ProcessingPhase(Enum):
    """Processing phases from Sprint 33"""
    IDLE = "idle"
    SCHEDULED = "scheduled"
    DATA_IMPORT = "data_import"
    CACHE_SYNC = "cache_sync"
    INDICATOR_PROCESSING = "indicator_processing"
    PATTERN_DETECTION = "pattern_detection"
    COMPLETED = "completed"
    ERROR = "error"


class ProcessingEventSubscriber:
    """
    Subscribes to TickStockPL processing events via Redis pub-sub.
    Maintains current processing state and history in database.
    """

    def __init__(self, redis_client: redis.Redis, socketio=None):
        self.redis_client = redis_client
        self.socketio = socketio
        self.pubsub = None
        self.subscriber_thread = None
        self.running = False
        self.config = get_config()

        # Current processing state (will be persisted to DB)
        self.current_state = {
            'run_id': None,
            'phase': ProcessingPhase.IDLE,
            'is_running': False,
            'progress': 0,
            'current_symbol': None,
            'symbols_total': 0,
            'symbols_completed': 0,
            'symbols_failed': 0,
            'estimated_completion': None,
            'started_at': None,
            'last_updated': None,
            'error_message': None,
            'phase_details': {}
        }

        # Channels to subscribe to (confirmed by TickStockPL team - all use colon notation)
        self.channels = [
            # Processing Control & Status
            'tickstock:processing:status',
            'tickstock:processing:schedule',

            # Phase 2: Import events
            'tickstock:import:started',
            'tickstock:import:progress',
            'tickstock:import:completed',

            # Phase 2.5: Cache sync events
            'tickstock:cache:started',
            'tickstock:cache:progress',
            'tickstock:cache:completed',

            # Phase 3: Indicator events
            'tickstock:indicators:started',
            'tickstock:indicators:progress',
            'tickstock:indicators:completed',
            'tickstock:indicators:calculated',

            # Phase 4: Pattern events
            'tickstock:patterns:started',
            'tickstock:patterns:progress',
            'tickstock:patterns:completed',
            'tickstock:patterns:detected',

            # System channels
            'tickstock:monitoring',
            'tickstock:errors'
        ]

        # Event handlers mapped by event type
        self.event_handlers = {
            'daily_processing_started': self._handle_processing_started,
            'daily_processing_progress': self._handle_processing_progress,
            'daily_processing_completed': self._handle_processing_completed,
            'data_import_started': self._handle_import_started,
            'data_import_completed': self._handle_import_completed,
            'indicator_processing_started': self._handle_indicator_started,
            'indicator_progress': self._handle_indicator_progress,
            'indicator_processing_completed': self._handle_indicator_completed,
            'processing_error': self._handle_processing_error,
            'job_progress_update': self._handle_job_progress
        }

        self._init_database_tables()

    def _init_database_tables(self):
        """Initialize database tables for processing history"""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                # Create processing runs table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processing_runs (
                            run_id VARCHAR(64) PRIMARY KEY,
                            trigger_type VARCHAR(32),
                            status VARCHAR(32),
                            phase VARCHAR(64),
                            started_at TIMESTAMP,
                            completed_at TIMESTAMP,
                            duration_seconds INTEGER,
                            symbols_total INTEGER DEFAULT 0,
                            symbols_processed INTEGER DEFAULT 0,
                            symbols_failed INTEGER DEFAULT 0,
                            indicators_total INTEGER DEFAULT 0,
                            indicators_processed INTEGER DEFAULT 0,
                            indicators_failed INTEGER DEFAULT 0,
                            error_message TEXT,
                            metadata JSONB,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)

                # Create indexes if they don't exist
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_processing_runs_started_at
                    ON processing_runs(started_at DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_processing_runs_status
                    ON processing_runs(status)
                """)

                conn.commit()
                logger.info("Ensured processing_runs table exists")

        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def _get_db_connection(self):
        """Get database connection using config_manager"""
        db_uri = self.config.get('DATABASE_URI',
                                'postgresql://app_readwrite:password@localhost:5432/tickstock')

        # Parse URI to extract components
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)', db_uri)
        if match:
            user, password, host, port, database = match.groups()
            port = port or '5432'
        else:
            raise ValueError("Invalid DATABASE_URI format")

        return psycopg2.connect(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password,
            cursor_factory=RealDictCursor
        )

    def start(self):
        """Start the Redis subscriber thread"""
        if not self.running:
            self.running = True
            self.subscriber_thread = threading.Thread(target=self._subscribe_loop, daemon=True)
            self.subscriber_thread.start()
            logger.info(f"Processing event subscriber started, listening to {len(self.channels)} channels")

    def stop(self):
        """Stop the Redis subscriber thread"""
        self.running = False
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()
        if self.subscriber_thread:
            self.subscriber_thread.join(timeout=5)
        logger.info("Processing event subscriber stopped")

    def _subscribe_loop(self):
        """Main subscription loop running in separate thread"""
        try:
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(*self.channels)

            while self.running:
                try:
                    message = self.pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        self._process_message(message)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except Exception as e:
            logger.error(f"Subscriber loop error: {e}")
        finally:
            if self.pubsub:
                self.pubsub.close()

    def _process_message(self, message):
        """Process incoming Redis message"""
        try:
            channel = message['channel']
            if isinstance(channel, bytes):
                channel = channel.decode('utf-8')

            data = message['data']
            if isinstance(data, bytes):
                data = data.decode('utf-8')

            # Parse JSON event
            event = json.loads(data)

            # Route to appropriate handler based on event type
            event_type = event.get('event') or event.get('event_type')
            if event_type in self.event_handlers:
                self.event_handlers[event_type](event, channel)
            else:
                logger.debug(f"Unhandled event type: {event_type} on channel: {channel}")

            # Emit to WebSocket if connected
            if self.socketio and self.current_state['is_running']:
                self._emit_status_update()

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message as JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _handle_processing_started(self, event: dict[str, Any], channel: str):
        """Handle processing started event"""
        payload = event.get('payload', {})
        run_id = payload.get('run_id')

        if not run_id:
            logger.warning("Processing started event missing run_id")
            return

        self.current_state.update({
            'run_id': run_id,
            'phase': ProcessingPhase.SCHEDULED,
            'is_running': True,
            'progress': 0,
            'symbols_total': payload.get('total_symbols', 0),
            'symbols_completed': 0,
            'symbols_failed': 0,
            'started_at': event.get('timestamp'),
            'last_updated': datetime.now().isoformat(),
            'error_message': None
        })

        # Store in database
        self._save_processing_run(trigger_type=payload.get('trigger_type', 'automatic'))

        logger.info(f"Processing started: {run_id}")

    def _handle_processing_progress(self, event: dict[str, Any], channel: str):
        """Handle processing progress event"""
        payload = event.get('payload', {})

        self.current_state.update({
            'progress': payload.get('progress', self.current_state['progress']),
            'current_symbol': payload.get('current_symbol'),
            'symbols_completed': payload.get('symbols_completed', self.current_state['symbols_completed']),
            'estimated_completion': payload.get('estimated_completion'),
            'last_updated': datetime.now().isoformat()
        })

        # Update database
        if self.current_state['run_id']:
            self._update_processing_run()

    def _handle_processing_completed(self, event: dict[str, Any], channel: str):
        """Handle processing completed event"""
        payload = event.get('payload', {})

        self.current_state.update({
            'phase': ProcessingPhase.COMPLETED,
            'is_running': False,
            'progress': 100,
            'symbols_completed': payload.get('symbols_processed', self.current_state['symbols_completed']),
            'symbols_failed': payload.get('symbols_failed', 0),
            'last_updated': datetime.now().isoformat()
        })

        # Update database with completion
        if self.current_state['run_id']:
            self._complete_processing_run(
                success=payload.get('success', True),
                duration=payload.get('duration_seconds')
            )

        logger.info(f"Processing completed: {self.current_state['run_id']}")

    def _handle_import_started(self, event: dict[str, Any], channel: str):
        """Handle data import phase started"""
        payload = event.get('payload', {})

        self.current_state.update({
            'phase': ProcessingPhase.DATA_IMPORT,
            'phase_details': {
                'import': {
                    'universes': payload.get('universe_names', []),
                    'timeframes': payload.get('timeframes', []),
                    'lookback_days': payload.get('lookback_days', {})
                }
            }
        })

        logger.info("Data import phase started")

    def _handle_import_completed(self, event: dict[str, Any], channel: str):
        """Handle data import phase completed"""
        payload = event.get('payload', {})

        phase_details = self.current_state.get('phase_details', {})
        phase_details['import'] = {
            **phase_details.get('import', {}),
            'completed': True,
            'success_count': payload.get('success_count', 0),
            'failure_count': payload.get('failure_count', 0),
            'duration': payload.get('duration_seconds', 0)
        }

        self.current_state['phase_details'] = phase_details

        logger.info(f"Data import completed: {payload.get('success_count')} successful")

    def _handle_indicator_started(self, event: dict[str, Any], channel: str):
        """Handle indicator processing started"""
        payload = event.get('payload', {})

        self.current_state.update({
            'phase': ProcessingPhase.INDICATOR_PROCESSING,
            'phase_details': {
                **self.current_state.get('phase_details', {}),
                'indicators': {
                    'total_symbols': payload.get('total_symbols', 0),
                    'total_indicators': payload.get('total_indicators', 0),
                    'timeframes': payload.get('timeframes', [])
                }
            }
        })

        logger.info("Indicator processing phase started")

    def _handle_indicator_progress(self, event: dict[str, Any], channel: str):
        """Handle indicator processing progress"""
        payload = event.get('payload', {})

        phase_details = self.current_state.get('phase_details', {})
        indicators = phase_details.get('indicators', {})
        indicators.update({
            'completed_symbols': payload.get('completed_symbols', 0),
            'percent_complete': payload.get('percent_complete', 0),
            'current_symbol': payload.get('current_symbol'),
            'eta_seconds': payload.get('eta_seconds', 0)
        })

        phase_details['indicators'] = indicators
        self.current_state['phase_details'] = phase_details

    def _handle_indicator_completed(self, event: dict[str, Any], channel: str):
        """Handle indicator processing completed"""
        payload = event.get('payload', {})

        phase_details = self.current_state.get('phase_details', {})
        indicators = phase_details.get('indicators', {})
        indicators.update({
            'completed': True,
            'successful_symbols': payload.get('successful_symbols', 0),
            'failed_symbols': payload.get('failed_symbols', 0),
            'successful_indicators': payload.get('successful_indicators', 0),
            'failed_indicators': payload.get('failed_indicators', 0),
            'success_rate': payload.get('success_rate', 0),
            'duration_seconds': payload.get('duration_seconds', 0)
        })

        phase_details['indicators'] = indicators
        self.current_state['phase_details'] = phase_details

        logger.info(f"Indicator processing completed: {indicators['success_rate']}% success rate")

    def _handle_processing_error(self, event: dict[str, Any], channel: str):
        """Handle processing error event"""
        payload = event.get('payload', {})

        self.current_state.update({
            'phase': ProcessingPhase.ERROR,
            'is_running': False,
            'error_message': payload.get('error_message', 'Unknown error')
        })

        # Update database with error
        if self.current_state['run_id']:
            self._complete_processing_run(success=False, error=self.current_state['error_message'])

        logger.error(f"Processing error: {self.current_state['error_message']}")

    def _handle_job_progress(self, event: dict[str, Any], channel: str):
        """Handle generic job progress update from monitoring channel"""
        payload = event.get('payload', {})
        source = event.get('source', '')

        # Only process if it's from a processing-related source
        if 'processing' in source or 'import' in source or 'indicator' in source:
            self.current_state.update({
                'progress': payload.get('percentage', self.current_state['progress']),
                'current_symbol': payload.get('current_symbol', self.current_state['current_symbol']),
                'symbols_completed': payload.get('completed', self.current_state['symbols_completed']),
                'symbols_failed': payload.get('failed', self.current_state['symbols_failed']),
                'estimated_completion': payload.get('estimated_completion'),
                'last_updated': datetime.now().isoformat()
            })

    def _save_processing_run(self, trigger_type: str = 'automatic'):
        """Save new processing run to database"""
        if not self.current_state['run_id']:
            return

        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO processing_runs (
                        run_id, trigger_type, status, phase, started_at,
                        symbols_total, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        phase = EXCLUDED.phase,
                        updated_at = NOW()
                """, (
                    self.current_state['run_id'],
                    trigger_type,
                    'running',
                    self.current_state['phase'].value,
                    self.current_state['started_at'] or datetime.now(),
                    self.current_state['symbols_total'],
                    json.dumps(self.current_state['phase_details'])
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save processing run: {e}")
        finally:
            conn.close()

    def _update_processing_run(self):
        """Update existing processing run in database"""
        if not self.current_state['run_id']:
            return

        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE processing_runs SET
                        phase = %s,
                        symbols_processed = %s,
                        symbols_failed = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE run_id = %s
                """, (
                    self.current_state['phase'].value,
                    self.current_state['symbols_completed'],
                    self.current_state['symbols_failed'],
                    json.dumps(self.current_state['phase_details']),
                    self.current_state['run_id']
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update processing run: {e}")
        finally:
            conn.close()

    def _complete_processing_run(self, success: bool = True, duration: int | None = None, error: str | None = None):
        """Mark processing run as completed in database"""
        if not self.current_state['run_id']:
            return

        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                # Calculate duration if not provided
                if duration is None and self.current_state['started_at']:
                    start_time = datetime.fromisoformat(self.current_state['started_at'].replace('Z', '+00:00'))
                    duration = int((datetime.now() - start_time).total_seconds())

                cursor.execute("""
                    UPDATE processing_runs SET
                        status = %s,
                        phase = %s,
                        completed_at = NOW(),
                        duration_seconds = %s,
                        symbols_processed = %s,
                        symbols_failed = %s,
                        error_message = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE run_id = %s
                """, (
                    'success' if success else 'failed',
                    ProcessingPhase.COMPLETED.value if success else ProcessingPhase.ERROR.value,
                    duration,
                    self.current_state['symbols_completed'],
                    self.current_state['symbols_failed'],
                    error,
                    json.dumps(self.current_state['phase_details']),
                    self.current_state['run_id']
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to complete processing run: {e}")
        finally:
            conn.close()

    def _emit_status_update(self):
        """Emit current status to WebSocket clients"""
        if self.socketio:
            try:
                self.socketio.emit('processing_status_update', {
                    'status': self._get_current_status_dict()
                })
            except Exception as e:
                logger.error(f"Failed to emit WebSocket update: {e}")

    def _get_current_status_dict(self) -> dict[str, Any]:
        """Get current status as dictionary for API/WebSocket"""
        return {
            'is_running': self.current_state['is_running'],
            'run_id': self.current_state['run_id'],
            'phase': self.current_state['phase'].value,
            'progress': self.current_state['progress'],
            'current_symbol': self.current_state['current_symbol'],
            'symbols_total': self.current_state['symbols_total'],
            'symbols_completed': self.current_state['symbols_completed'],
            'symbols_failed': self.current_state['symbols_failed'],
            'estimated_completion': self.current_state['estimated_completion'],
            'last_updated': self.current_state['last_updated'],
            'error_message': self.current_state['error_message'],
            'import_status': self.current_state['phase_details'].get('import', {}),
            'indicator_status': self.current_state['phase_details'].get('indicators', {})
        }

    def get_current_status(self) -> dict[str, Any]:
        """Public method to get current processing status"""
        return self._get_current_status_dict()

    def get_processing_history(self, days: int = 7, limit: int = 20) -> list:
        """Get processing history from database"""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        run_id,
                        trigger_type,
                        status,
                        phase,
                        started_at as start_time,
                        completed_at as end_time,
                        duration_seconds,
                        symbols_total,
                        symbols_processed,
                        symbols_failed,
                        error_message
                    FROM processing_runs
                    WHERE started_at >= NOW() - INTERVAL '%s days'
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (days, limit))

                results = cursor.fetchall()
                return [dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Failed to get processing history: {e}")
            return []
        finally:
            conn.close()


# Singleton instance
_subscriber_instance: ProcessingEventSubscriber | None = None


def get_processing_subscriber(redis_client: redis.Redis, socketio=None) -> ProcessingEventSubscriber:
    """Get or create singleton ProcessingEventSubscriber instance"""
    global _subscriber_instance
    if _subscriber_instance is None:
        _subscriber_instance = ProcessingEventSubscriber(redis_client, socketio)
        _subscriber_instance.start()
    return _subscriber_instance


def stop_processing_subscriber():
    """Stop the singleton ProcessingEventSubscriber instance"""
    global _subscriber_instance
    if _subscriber_instance:
        _subscriber_instance.stop()
        _subscriber_instance = None
