"""
TickStockPL HTTP API Client
Sprint 33 Phase 4 - Based on TickStockPL Integration Response

Communicates with TickStockPL via HTTP API for commands and status.
"""

import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)


class TickStockPLAPIClient:
    """
    HTTP API client for TickStockPL commands and queries.
    Based on actual TickStockPL API specifications.
    """

    def __init__(self, base_url: Optional[str] = None):
        config = get_config()
        self.base_url = base_url or config.get('TICKSTOCKPL_API_URL', 'http://localhost:8080')
        self.session = requests.Session()
        self.timeout = 2  # seconds - reduced for faster failure when TickStockPL is not running

    def trigger_processing(
        self,
        skip_market_check: bool = False,
        phases: Optional[List[str]] = None,
        universe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger manual processing in TickStockPL.

        Args:
            skip_market_check: Whether to skip market hours check
            phases: Specific phases to run (default: all)
            universe: Universe to process (default: from config)

        Returns:
            API response with run_id and status
        """
        try:
            payload = {
                'skip_market_check': skip_market_check
            }

            if phases:
                payload['phases'] = phases
            else:
                payload['phases'] = ['all']  # Default to all phases

            if universe:
                payload['universe'] = universe

            response = self.session.post(
                f'{self.base_url}/api/processing/trigger-manual',
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"Triggered processing: {data.get('run_id')}")
            return {
                'success': True,
                'run_id': data.get('run_id'),
                'status': data.get('status'),
                'message': data.get('message', 'Processing triggered successfully')
            }

        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to TickStockPL at {self.base_url}")
            return {
                'success': False,
                'message': f'TickStockPL API unavailable at {self.base_url}'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error triggering processing: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current processing status from TickStockPL.

        Returns:
            Current status information
        """
        try:
            response = self.session.get(
                f'{self.base_url}/api/processing/status',
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'is_running': data.get('is_running', False),
                'run_id': data.get('run_id'),
                'phase': data.get('current_phase'),
                'progress': data.get('progress', 0),
                'symbols_processed': data.get('symbols_processed', 0),
                'symbols_total': data.get('symbols_total', 0),
                'start_time': data.get('start_time'),
                'estimated_completion': data.get('estimated_completion')
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting status: {e}")
            return {
                'success': False,
                'is_running': False,
                'message': str(e)
            }

    def get_history(self, days: int = 7) -> Dict[str, Any]:
        """
        Get processing history from TickStockPL.

        Args:
            days: Number of days of history to retrieve

        Returns:
            Processing run history
        """
        try:
            response = self.session.get(
                f'{self.base_url}/api/processing/history',
                params={'days': days},
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            # Convert to format expected by dashboard
            runs = data.get('runs', [])
            formatted_runs = []

            for run in runs:
                formatted_runs.append({
                    'run_id': run.get('run_id'),
                    'trigger_type': run.get('trigger_type', 'automatic'),
                    'status': run.get('status'),
                    'start_time': run.get('start_time'),
                    'end_time': run.get('end_time'),
                    'duration_seconds': run.get('duration_seconds'),
                    'symbols_processed': run.get('symbols_processed', 0),
                    'symbols_failed': run.get('symbols_failed', 0),
                    'patterns_detected': run.get('patterns_detected', 0),
                    'indicators_calculated': run.get('indicators_calculated', 0)
                })

            return {
                'success': True,
                'history': formatted_runs
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting history: {e}")
            return {
                'success': False,
                'history': [],
                'message': str(e)
            }

    def cancel_processing(self) -> Dict[str, Any]:
        """
        Cancel current processing run in TickStockPL.

        Returns:
            Cancellation result
        """
        try:
            response = self.session.delete(
                f'{self.base_url}/api/processing/cancel',
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            logger.info("Processing cancellation requested")
            return {
                'success': True,
                'message': data.get('message', 'Processing cancelled successfully')
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error cancelling processing: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def get_schedule(self) -> Dict[str, Any]:
        """
        Get current processing schedule from TickStockPL.

        Returns:
            Schedule configuration
        """
        try:
            response = self.session.get(
                f'{self.base_url}/api/processing/schedule',
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'enabled': data.get('enabled', False),
                'trigger_time': data.get('trigger_time', '16:10'),
                'timezone': data.get('timezone', 'America/New_York'),
                'next_run': data.get('next_run'),
                'universes': data.get('universes', ['sp500']),
                'market_check': data.get('market_check', True)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting schedule: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def update_schedule(
        self,
        enabled: Optional[bool] = None,
        trigger_time: Optional[str] = None,
        market_check: Optional[bool] = None,
        universes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update processing schedule in TickStockPL.

        Args:
            enabled: Whether schedule is enabled
            trigger_time: Time to trigger (HH:MM format)
            market_check: Whether to check market status
            universes: Universes to process

        Returns:
            Update result
        """
        try:
            payload = {}
            if enabled is not None:
                payload['enabled'] = enabled
            if trigger_time is not None:
                payload['trigger_time'] = trigger_time
            if market_check is not None:
                payload['market_check'] = market_check
            if universes is not None:
                payload['universes'] = universes

            response = self.session.post(
                f'{self.base_url}/api/processing/schedule',
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            logger.info("Schedule updated successfully")
            return {
                'success': True,
                'message': 'Schedule updated successfully',
                'schedule': data
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating schedule: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def trigger_data_import(
        self,
        universes: List[str],
        timeframes: Optional[List[str]] = None,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Trigger data import in TickStockPL.

        Args:
            universes: List of universe names (e.g., ['sp500', 'dow30'])
            timeframes: Timeframes to import (default: ['daily', 'weekly'])
            lookback_days: Days of historical data to import

        Returns:
            Import trigger result
        """
        try:
            payload = {
                'universes': universes,
                'timeframes': timeframes or ['daily', 'weekly'],
                'lookback_days': lookback_days
            }

            response = self.session.post(
                f'{self.base_url}/api/processing/trigger-import',
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"Triggered data import: {data.get('run_id')}")
            return {
                'success': True,
                'run_id': data.get('run_id'),
                'message': data.get('message', 'Data import triggered successfully')
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error triggering data import: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def trigger_indicator_processing(
        self,
        symbols: Optional[List[str]] = None,
        indicators: Optional[List[str]] = None,
        timeframe: str = 'daily'
    ) -> Dict[str, Any]:
        """
        Trigger indicator processing in TickStockPL.

        Args:
            symbols: Specific symbols to process (None = all)
            indicators: Specific indicators to calculate (None = all enabled)
            timeframe: Timeframe for calculations

        Returns:
            Indicator processing trigger result
        """
        try:
            payload = {
                'timeframe': timeframe
            }
            if symbols:
                payload['symbols'] = symbols
            if indicators:
                payload['indicators'] = indicators

            response = self.session.post(
                f'{self.base_url}/api/processing/trigger-indicators',
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"Triggered indicator processing: {data.get('run_id')}")
            return {
                'success': True,
                'run_id': data.get('run_id'),
                'message': data.get('message', 'Indicator processing triggered successfully')
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error triggering indicator processing: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def retry_failed_imports(
        self,
        run_id: str,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Retry failed data imports from a previous run.

        Args:
            run_id: Previous run ID to retry failures from
            symbols: Specific symbols to retry (None = all failed)

        Returns:
            Retry operation result
        """
        try:
            payload = {
                'original_run_id': run_id
            }
            if symbols:
                payload['symbols'] = symbols

            response = self.session.post(
                f'{self.base_url}/api/processing/retry-imports',
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"Triggered import retry: {data.get('run_id')}")
            return {
                'success': True,
                'run_id': data.get('run_id'),
                'message': data.get('message', 'Import retry triggered successfully')
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrying imports: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def health_check(self) -> bool:
        """
        Check if TickStockPL API is available.

        Returns:
            True if API is responding, False otherwise
        """
        try:
            response = self.session.get(
                f'{self.base_url}/health',
                timeout=5
            )
            return response.status_code == 200
        except:
            return False


# Singleton instance
_api_client_instance: Optional[TickStockPLAPIClient] = None


def get_tickstockpl_client(base_url: Optional[str] = None) -> TickStockPLAPIClient:
    """Get or create singleton TickStockPLAPIClient instance"""
    global _api_client_instance
    if _api_client_instance is None:
        _api_client_instance = TickStockPLAPIClient(base_url)
    return _api_client_instance