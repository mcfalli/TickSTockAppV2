"""Simplified display converter for TickStockPL integration.

PHASE 7 CLEANUP: Simplified to basic data conversion with:
- Simple TickData to display format conversion
- Basic field mapping
- No complex transformations or filtering

Removed: Complex analytics, transformations, aggregations.
"""

import logging
import time
from typing import Any

from src.core.domain.market.tick import TickData

logger = logging.getLogger(__name__)

class WebSocketDisplayConverter:
    """Simplified converter for WebSocket display data."""

    def __init__(self, config=None):
        self.config = config or {}
        logger.info("DISPLAY-CONVERTER: Simplified converter initialized")

    def convert_tick_data(self, tick_data: TickData) -> dict[str, Any]:
        """Convert TickData to simple display format."""
        try:
            display_data = {
                'ticker': tick_data.ticker,
                'price': tick_data.price,
                'volume': tick_data.volume,
                'timestamp': tick_data.timestamp,
                'source': tick_data.source,
                'event_type': 'tick_update',
                'market_status': tick_data.market_status
            }

            # Add optional fields if available
            if hasattr(tick_data, 'bid') and tick_data.bid:
                display_data['bid'] = tick_data.bid

            if hasattr(tick_data, 'ask') and tick_data.ask:
                display_data['ask'] = tick_data.ask

            if hasattr(tick_data, 'tick_high') and tick_data.tick_high:
                display_data['high'] = tick_data.tick_high

            if hasattr(tick_data, 'tick_low') and tick_data.tick_low:
                display_data['low'] = tick_data.tick_low

            return display_data

        except Exception as e:
            logger.error(f"DISPLAY-CONVERTER: Error converting tick data: {e}")
            return self._create_error_response(str(e))

    def convert_multiple_ticks(self, tick_data_list: list) -> list:
        """Convert multiple TickData objects."""
        return [self.convert_tick_data(tick) for tick in tick_data_list]

    def _create_error_response(self, error_message: str) -> dict[str, Any]:
        """Create error response for failed conversions."""
        return {
            'error': True,
            'message': error_message,
            'timestamp': time.time()
        }
