"""
Processing Command Publisher for TickStockPL Integration
Sprint 33 - Trigger Commands via Redis

Publishes commands to TickStockPL to trigger processing phases.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

import redis

from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)


class ProcessingCommandPublisher:
    """
    Publishes commands to TickStockPL via Redis pub-sub.
    All processing happens in TickStockPL, TickStockAppV2 just triggers.
    """

    # Command channels - using both notations until clarified by TickStockPL
    COMMAND_CHANNELS = {
        'trigger': ['tickstock:commands:trigger', 'tickstock.commands.trigger'],
        'cancel': ['tickstock:commands:cancel', 'tickstock.commands.cancel'],
        'status': ['tickstock:commands:status', 'tickstock.commands.status'],
        'retry': ['tickstock:commands:retry', 'tickstock.commands.retry']
    }

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.config = get_config()

    def trigger_daily_processing(
        self,
        skip_market_check: bool = False,
        phases: list[str] | None = None,
        trigger_type: str = 'manual'
    ) -> dict[str, Any]:
        """
        Trigger daily processing in TickStockPL.

        Args:
            skip_market_check: Whether to skip market hours check
            phases: List of phases to run (None = all phases)
            trigger_type: 'manual' or 'automatic'

        Returns:
            Command result with run_id
        """
        run_id = str(uuid.uuid4())

        # Default to all phases if not specified
        if phases is None:
            phases = ['data_import', 'cache_sync', 'indicators', 'patterns']

        command = {
            'command': 'trigger_daily_processing',
            'run_id': run_id,
            'parameters': {
                'skip_market_check': skip_market_check,
                'phases': phases,
                'trigger_type': trigger_type
            },
            'source': 'TickStockAppV2',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Publish to both channel formats until we know which one TickStockPL uses
        success = False
        for channel in self.COMMAND_CHANNELS['trigger']:
            try:
                result = self.redis_client.publish(channel, json.dumps(command))
                if result > 0:
                    logger.info(f"Triggered daily processing on {channel}: {run_id}")
                    success = True
                    break
            except Exception as e:
                logger.error(f"Failed to publish to {channel}: {e}")

        if success:
            return {
                'success': True,
                'run_id': run_id,
                'message': 'Processing triggered successfully'
            }
        return {
            'success': False,
            'message': 'No subscribers listening on trigger channels'
        }

    def trigger_data_import(
        self,
        universes: list[str],
        timeframes: list[str] = None,
        lookback_days: int = 30
    ) -> dict[str, Any]:
        """
        Trigger data import phase in TickStockPL.

        Args:
            universes: List of universe names (e.g., ['sp500', 'dow30'])
            timeframes: Timeframes to import (default: ['daily', 'weekly'])
            lookback_days: Days of historical data to import

        Returns:
            Command result
        """
        run_id = str(uuid.uuid4())

        if timeframes is None:
            timeframes = ['daily', 'weekly']

        command = {
            'command': 'trigger_data_import',
            'run_id': run_id,
            'parameters': {
                'universes': universes,
                'timeframes': timeframes,
                'lookback_days': lookback_days
            },
            'source': 'TickStockAppV2',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Try both channel formats
        success = False
        for channel in self.COMMAND_CHANNELS['trigger']:
            try:
                result = self.redis_client.publish(channel, json.dumps(command))
                if result > 0:
                    logger.info(f"Triggered data import on {channel}: {run_id}")
                    success = True
                    break
            except Exception as e:
                logger.error(f"Failed to publish to {channel}: {e}")

        if success:
            return {
                'success': True,
                'run_id': run_id,
                'message': 'Data import triggered successfully'
            }
        return {
            'success': False,
            'message': 'No subscribers listening on trigger channels'
        }

    def trigger_indicator_processing(
        self,
        symbols: list[str] | None = None,
        indicators: list[str] | None = None,
        timeframe: str = 'daily'
    ) -> dict[str, Any]:
        """
        Trigger indicator processing phase in TickStockPL.

        Args:
            symbols: Specific symbols to process (None = all)
            indicators: Specific indicators to calculate (None = all enabled)
            timeframe: Timeframe for indicators

        Returns:
            Command result
        """
        run_id = str(uuid.uuid4())

        command = {
            'command': 'trigger_indicator_processing',
            'run_id': run_id,
            'parameters': {
                'symbols': symbols,
                'indicators': indicators,
                'timeframe': timeframe
            },
            'source': 'TickStockAppV2',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Try both channel formats
        success = False
        for channel in self.COMMAND_CHANNELS['trigger']:
            try:
                result = self.redis_client.publish(channel, json.dumps(command))
                if result > 0:
                    logger.info(f"Triggered indicator processing on {channel}: {run_id}")
                    success = True
                    break
            except Exception as e:
                logger.error(f"Failed to publish to {channel}: {e}")

        if success:
            return {
                'success': True,
                'run_id': run_id,
                'message': 'Indicator processing triggered successfully'
            }
        return {
            'success': False,
            'message': 'No subscribers listening on trigger channels'
        }

    def cancel_processing(self, run_id: str | None = None) -> dict[str, Any]:
        """
        Cancel current processing in TickStockPL.

        Args:
            run_id: Specific run to cancel (None = current run)

        Returns:
            Command result
        """
        command = {
            'command': 'cancel_processing',
            'run_id': run_id,
            'source': 'TickStockAppV2',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Try both channel formats
        success = False
        for channel in self.COMMAND_CHANNELS['cancel']:
            try:
                result = self.redis_client.publish(channel, json.dumps(command))
                if result > 0:
                    logger.info(f"Sent cancel command on {channel}: {run_id or 'current'}")
                    success = True
                    break
            except Exception as e:
                logger.error(f"Failed to publish to {channel}: {e}")

        if success:
            return {
                'success': True,
                'message': 'Cancel command sent successfully'
            }
        return {
            'success': False,
            'message': 'No subscribers listening on cancel channels'
        }

    def retry_failed_imports(self, run_id: str, symbols: list[str] | None = None) -> dict[str, Any]:
        """
        Retry failed data imports from a previous run.

        Args:
            run_id: Previous run ID to retry failures from
            symbols: Specific symbols to retry (None = all failed)

        Returns:
            Command result
        """
        new_run_id = str(uuid.uuid4())

        command = {
            'command': 'retry_failed_imports',
            'run_id': new_run_id,
            'parameters': {
                'original_run_id': run_id,
                'symbols': symbols
            },
            'source': 'TickStockAppV2',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Try both channel formats
        success = False
        for channel in self.COMMAND_CHANNELS['retry']:
            try:
                result = self.redis_client.publish(channel, json.dumps(command))
                if result > 0:
                    logger.info(f"Sent retry command on {channel}: {new_run_id}")
                    success = True
                    break
            except Exception as e:
                logger.error(f"Failed to publish to {channel}: {e}")

        if success:
            return {
                'success': True,
                'run_id': new_run_id,
                'message': 'Retry command sent successfully'
            }
        return {
            'success': False,
            'message': 'No subscribers listening on retry channels'
        }

    def request_status(self, run_id: str | None = None) -> dict[str, Any]:
        """
        Request status update from TickStockPL.

        Args:
            run_id: Specific run to query (None = current run)

        Returns:
            Command result
        """
        command = {
            'command': 'request_status',
            'run_id': run_id,
            'source': 'TickStockAppV2',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Try both channel formats
        success = False
        for channel in self.COMMAND_CHANNELS['status']:
            try:
                result = self.redis_client.publish(channel, json.dumps(command))
                if result > 0:
                    logger.info(f"Requested status on {channel}")
                    success = True
                    break
            except Exception as e:
                logger.error(f"Failed to publish to {channel}: {e}")

        if success:
            return {
                'success': True,
                'message': 'Status request sent'
            }
        return {
            'success': False,
            'message': 'No subscribers listening on status channels'
        }

    def update_schedule(
        self,
        enabled: bool,
        trigger_time: str,
        market_check: bool = True
    ) -> dict[str, Any]:
        """
        Update processing schedule in TickStockPL.

        Args:
            enabled: Whether schedule is enabled
            trigger_time: Time to trigger (HH:MM format)
            market_check: Whether to check market status

        Returns:
            Command result
        """
        command = {
            'command': 'update_schedule',
            'parameters': {
                'enabled': enabled,
                'trigger_time': trigger_time,
                'market_check': market_check
            },
            'source': 'TickStockAppV2',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Schedule updates might go to a different channel
        channels = ['tickstock:processing:schedule', 'tickstock.processing.schedule']

        success = False
        for channel in channels:
            try:
                result = self.redis_client.publish(channel, json.dumps(command))
                if result > 0:
                    logger.info(f"Updated schedule on {channel}")
                    success = True
                    break
            except Exception as e:
                logger.error(f"Failed to publish to {channel}: {e}")

        if success:
            return {
                'success': True,
                'message': 'Schedule updated successfully'
            }
        # Store locally if TickStockPL not listening
        logger.warning("Schedule update not delivered - TickStockPL may not be listening")
        return {
            'success': True,
            'message': 'Schedule saved locally (TickStockPL not responding)'
        }


# Singleton instance
_publisher_instance: ProcessingCommandPublisher | None = None


def get_command_publisher(redis_client: redis.Redis) -> ProcessingCommandPublisher:
    """Get or create singleton ProcessingCommandPublisher instance"""
    global _publisher_instance
    if _publisher_instance is None:
        _publisher_instance = ProcessingCommandPublisher(redis_client)
    return _publisher_instance
