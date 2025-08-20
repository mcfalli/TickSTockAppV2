"""
OHLCV Channel Implementation for Sprint 106: Data Type Handlers

Processes OHLCV (Open, High, Low, Close, Volume) aggregate data with batch optimization,
symbol-based buffering, and aggregate-specific event detection.

Designed for minute-level and longer timeframe data processing with specialized
aggregation logic and volume analysis capabilities.
"""

from typing import Any, Optional, List, Dict, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
import asyncio
import time
import statistics

from config.logging_config import get_domain_logger, LogDomain

# Import base channel infrastructure
from .base_channel import ProcessingChannel, ChannelType, ProcessingResult
from .channel_config import OHLCVChannelConfig

# Import data models
from src.shared.models.data_types import OHLCVData, identify_data_type
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.aggregate import PerMinuteAggregateEvent

logger = get_domain_logger(LogDomain.CORE, 'ohlcv_channel')


@dataclass
class SymbolBuffer:
    """Buffer for symbol-specific OHLCV data to enable multi-period analysis"""
    ticker: str
    history: deque = field(default_factory=lambda: deque(maxlen=100))  # Keep last 100 periods
    last_update: float = field(default_factory=time.time)
    volume_baseline: Optional[float] = None  # Rolling average volume
    price_baseline: Optional[float] = None   # Rolling average price
    
    def add_data(self, ohlcv_data: OHLCVData):
        """Add new OHLCV data to buffer"""
        self.history.append(ohlcv_data)
        self.last_update = time.time()
        self._update_baselines()
    
    def _update_baselines(self):
        """Update rolling baselines for comparison"""
        if len(self.history) >= 10:  # Need at least 10 periods
            recent_volumes = [data.volume for data in list(self.history)[-10:] if data.volume > 0]
            recent_closes = [data.close for data in list(self.history)[-10:]]
            
            if recent_volumes:
                self.volume_baseline = statistics.mean(recent_volumes)
            if recent_closes:
                self.price_baseline = statistics.mean(recent_closes)
    
    def get_volume_ratio(self, current_volume: int) -> float:
        """Get volume ratio compared to baseline"""
        if self.volume_baseline and self.volume_baseline > 0:
            return current_volume / self.volume_baseline
        return 1.0
    
    def get_price_change_pattern(self, periods: int = 5) -> str:
        """Analyze recent price change pattern"""
        if len(self.history) < periods:
            return 'insufficient_data'
        
        recent = list(self.history)[-periods:]
        changes = [data.percent_change for data in recent]
        
        positive_count = sum(1 for change in changes if change > 0)
        negative_count = sum(1 for change in changes if change < 0)
        
        if positive_count >= periods * 0.8:
            return 'strong_uptrend'
        elif negative_count >= periods * 0.8:
            return 'strong_downtrend'
        elif positive_count > negative_count:
            return 'weak_uptrend'
        elif negative_count > positive_count:
            return 'weak_downtrend'
        else:
            return 'sideways'


class OHLCVChannel(ProcessingChannel):
    """
    OHLCV Channel for processing minute-level aggregate data.
    
    Features:
    - Batch processing with configurable size (default: 100, timeout: 100ms)
    - Symbol-based buffering for multi-period analysis
    - Aggregate-specific event detection (high/low closes, volume surges)
    - Volume spike detection with 3x average threshold
    - Support for multiple timeframes (1m, 5m, 15m, 1h)
    """
    
    def __init__(self, name: str, config: OHLCVChannelConfig):
        super().__init__(name, config)
        
        # Store typed config for easy access
        self.ohlcv_config = config
        
        # Symbol-based buffering system
        self._symbol_buffers: Dict[str, SymbolBuffer] = {}
        
        # Processing statistics
        self._stats = {
            'batches_processed': 0,
            'events_generated': 0,
            'volume_spikes_detected': 0,
            'significant_moves_detected': 0,
            'symbols_tracked': 0
        }
        
        # Performance tracking
        self._last_cleanup_time = time.time()
        self._cleanup_interval = 600  # 10 minutes
        
        logger.info(f"Initialized OHLCVChannel: {name} with batch_size={config.batching.max_batch_size}, "
                   f"volume_threshold={config.volume_surge_multiplier}x, "
                   f"move_threshold={config.significant_move_threshold}%")
    
    def get_channel_type(self) -> ChannelType:
        """Return OHLCV channel type"""
        return ChannelType.OHLCV
    
    async def initialize(self) -> bool:
        """Initialize the OHLCV channel"""
        try:
            # Validate configuration
            if not self._validate_ohlcv_configuration():
                return False
            
            logger.info(f"OHLCVChannel {self.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OHLCVChannel {self.name}: {e}", exc_info=True)
            return False
    
    def _validate_ohlcv_configuration(self) -> bool:
        """Validate OHLCV-specific configuration"""
        try:
            # Check required parameters
            if not hasattr(self.ohlcv_config, 'volume_surge_multiplier'):
                logger.error("Missing volume_surge_multiplier in OHLCV config")
                return False
            
            if not hasattr(self.ohlcv_config, 'significant_move_threshold'):
                logger.error("Missing significant_move_threshold in OHLCV config")
                return False
            
            # Validate parameter values
            if self.ohlcv_config.volume_surge_multiplier < 1.0:
                logger.error(f"Invalid volume_surge_multiplier: {self.ohlcv_config.volume_surge_multiplier}")
                return False
            
            if self.ohlcv_config.significant_move_threshold <= 0:
                logger.error(f"Invalid significant_move_threshold: {self.ohlcv_config.significant_move_threshold}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    def validate_data(self, data: Any) -> bool:
        """Validate incoming OHLCV data"""
        
        # Check if data is OHLCVData object
        if isinstance(data, OHLCVData):
            return self._validate_ohlcv_data(data)
        
        # Check if data is dictionary with OHLCV structure
        if isinstance(data, dict):
            required_fields = ['ticker', 'open', 'high', 'low', 'close', 'volume']
            if all(field in data for field in required_fields):
                return self._validate_ohlcv_dict(data)
        
        # Check if data is aggregate event
        if isinstance(data, dict) and 'minute_open' in data:
            return self._validate_aggregate_event(data)
        
        logger.warning(f"Invalid data format for OHLCVChannel: {type(data)}")
        return False
    
    def _validate_ohlcv_data(self, ohlcv_data: OHLCVData) -> bool:
        """Validate OHLCVData object"""
        try:
            # Basic validation is handled by OHLCVData.validate()
            return ohlcv_data.validate()
            
        except Exception as e:
            logger.warning(f"OHLCVData validation error: {e}")
            return False
    
    def _validate_ohlcv_dict(self, data: Dict[str, Any]) -> bool:
        """Validate dictionary OHLCV data"""
        try:
            ticker = data.get('ticker', '').strip()
            if not ticker:
                return False
            
            # Validate OHLC relationships
            open_price = float(data['open'])
            high_price = float(data['high'])
            low_price = float(data['low'])
            close_price = float(data['close'])
            volume = int(data['volume'])
            
            if not (low_price <= min(open_price, close_price) and 
                   high_price >= max(open_price, close_price)):
                return False
            
            if volume < 0:
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"OHLCV dict validation error: {e}")
            return False
    
    def _validate_aggregate_event(self, data: Dict[str, Any]) -> bool:
        """Validate aggregate event data"""
        try:
            required_fields = ['ticker', 'minute_open', 'minute_high', 'minute_low', 'minute_close']
            return all(field in data for field in required_fields)
            
        except Exception as e:
            logger.warning(f"Aggregate event validation error: {e}")
            return False
    
    async def process_data(self, data: Any) -> ProcessingResult:
        """
        Process OHLCV data through aggregate analysis pipeline.
        
        Sprint 106 OHLCV Processing Flow:
        1. Validate data type compatibility
        2. Convert to OHLCVData format
        3. Update symbol-based buffer for multi-period analysis
        4. Detect significant moves and volume spikes
        5. Generate aggregate-specific events
        6. Return events with metadata
        
        Performance: Batch processing with 100ms timeout for efficiency
        """
        
        try:
            # Step 1: Validate data type for channel routing
            data_type = identify_data_type(data)
            if data_type != 'ohlcv' and data_type != 'unknown':
                return ProcessingResult(
                    success=False,
                    errors=[f"Invalid data type '{data_type}' for OHLCVChannel"]
                )
            
            # Step 2: Convert to OHLCVData format
            ohlcv_data = self._convert_to_ohlcv_data(data)
            if not ohlcv_data:
                return ProcessingResult(
                    success=False,
                    errors=["Failed to convert data to OHLCVData"]
                )
            
            # Step 3: Update symbol buffer for multi-period analysis
            symbol_buffer = self._get_or_create_symbol_buffer(ohlcv_data.ticker)
            symbol_buffer.add_data(ohlcv_data)
            
            # Step 4: Analyze and detect events
            events = await self._analyze_ohlcv_data(ohlcv_data, symbol_buffer)
            
            # Step 5: Add channel metadata to events
            for event in events:
                self._add_channel_metadata(event)
            
            # Step 6: Update statistics
            self._update_statistics(ohlcv_data, events)
            
            # Step 7: Periodic cleanup
            await self._periodic_cleanup()
            
            # Return results
            return ProcessingResult(
                success=True,
                events=events,
                metadata={
                    'ticker': ohlcv_data.ticker,
                    'close_price': ohlcv_data.close,
                    'volume': ohlcv_data.volume,
                    'percent_change': ohlcv_data.percent_change,
                    'timeframe': ohlcv_data.timeframe,
                    'events_generated': len(events),
                    'channel_name': self.name,
                    'channel_type': 'ohlcv',
                    'data_source': ohlcv_data.source,
                    'processing_mode': 'batch',
                    'analysis': {
                        'volume_ratio': symbol_buffer.get_volume_ratio(ohlcv_data.volume),
                        'price_pattern': symbol_buffer.get_price_change_pattern(),
                        'buffer_size': len(symbol_buffer.history)
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing OHLCV data in channel {self.name}: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                errors=[f"Processing error: {str(e)}"],
                metadata={'ticker': getattr(data, 'ticker', 'unknown')}
            )
    
    def _convert_to_ohlcv_data(self, data: Any) -> Optional[OHLCVData]:
        """Convert various data formats to OHLCVData"""
        
        if isinstance(data, OHLCVData):
            return data
        
        if isinstance(data, dict):
            try:
                # Handle standard OHLCV dict
                if 'open' in data:
                    return OHLCVData(
                        ticker=data['ticker'],
                        timestamp=data.get('timestamp', time.time()),
                        open=float(data['open']),
                        high=float(data['high']),
                        low=float(data['low']),
                        close=float(data['close']),
                        volume=int(data['volume']),
                        avg_volume=data.get('avg_volume', data.get('accumulated_volume', 1000000)),
                        percent_change=data.get('percent_change', 0.0),
                        vwap=data.get('vwap'),
                        daily_open=data.get('daily_open'),
                        accumulated_volume=data.get('accumulated_volume'),
                        trade_count=data.get('trade_count'),
                        timeframe=data.get('timeframe', '1m'),
                        market_session=data.get('market_session', 'REGULAR'),
                        source=data.get('source', 'aggregate')
                    )
                
                # Handle aggregate event format
                elif 'minute_open' in data:
                    return OHLCVData.from_aggregate_event(data)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to convert dict to OHLCVData: {e}")
                return None
        
        logger.warning(f"Cannot convert {type(data)} to OHLCVData")
        return None
    
    def _get_or_create_symbol_buffer(self, ticker: str) -> SymbolBuffer:
        """Get existing symbol buffer or create new one"""
        
        if ticker not in self._symbol_buffers:
            self._symbol_buffers[ticker] = SymbolBuffer(ticker=ticker)
            logger.debug(f"Created new SymbolBuffer for ticker: {ticker}")
        
        return self._symbol_buffers[ticker]
    
    async def _analyze_ohlcv_data(self, ohlcv_data: OHLCVData, symbol_buffer: SymbolBuffer) -> List[BaseEvent]:
        """Analyze OHLCV data and generate events"""
        
        events = []
        
        try:
            # Volume surge detection
            if self._is_volume_surge(ohlcv_data, symbol_buffer):
                volume_event = self._create_volume_surge_event(ohlcv_data, symbol_buffer)
                events.append(volume_event)
                self._stats['volume_spikes_detected'] += 1
            
            # Significant price move detection
            if self._is_significant_move(ohlcv_data):
                move_event = self._create_significant_move_event(ohlcv_data, symbol_buffer)
                events.append(move_event)
                self._stats['significant_moves_detected'] += 1
            
            # High/Low close detection (relative to recent period)
            close_events = self._detect_high_low_closes(ohlcv_data, symbol_buffer)
            events.extend(close_events)
            
            if events:
                logger.debug(f"Generated {len(events)} OHLCV events for {ohlcv_data.ticker}: "
                           f"{[e.type for e in events]}")
            
        except Exception as e:
            logger.error(f"Error in OHLCV analysis for {ohlcv_data.ticker}: {e}", exc_info=True)
        
        return events
    
    def _is_volume_surge(self, ohlcv_data: OHLCVData, symbol_buffer: SymbolBuffer) -> bool:
        """Check if volume represents a surge compared to baseline"""
        volume_ratio = symbol_buffer.get_volume_ratio(ohlcv_data.volume)
        surge_threshold = self.ohlcv_config.volume_surge_multiplier
        
        return volume_ratio >= surge_threshold
    
    def _is_significant_move(self, ohlcv_data: OHLCVData) -> bool:
        """Check if price movement is significant"""
        return abs(ohlcv_data.percent_change) >= self.ohlcv_config.significant_move_threshold
    
    def _detect_high_low_closes(self, ohlcv_data: OHLCVData, symbol_buffer: SymbolBuffer) -> List[BaseEvent]:
        """Detect high/low closes relative to recent periods"""
        events = []
        
        if len(symbol_buffer.history) < 5:  # Need history for comparison
            return events
        
        recent_closes = [data.close for data in list(symbol_buffer.history)[-10:]]
        current_close = ohlcv_data.close
        
        # Check for highest close in recent period
        if current_close == max(recent_closes):
            high_close_event = self._create_high_close_event(ohlcv_data, symbol_buffer)
            events.append(high_close_event)
        
        # Check for lowest close in recent period
        elif current_close == min(recent_closes):
            low_close_event = self._create_low_close_event(ohlcv_data, symbol_buffer)
            events.append(low_close_event)
        
        return events
    
    def _create_volume_surge_event(self, ohlcv_data: OHLCVData, symbol_buffer: SymbolBuffer) -> BaseEvent:
        """Create volume surge event"""
        volume_ratio = symbol_buffer.get_volume_ratio(ohlcv_data.volume)
        
        # Create aggregate event for volume surge
        event = PerMinuteAggregateEvent(
            ticker=ohlcv_data.ticker,
            type='volume_surge_aggregate',
            price=ohlcv_data.close,
            time=ohlcv_data.timestamp,
            minute_open=ohlcv_data.open,
            minute_high=ohlcv_data.high,
            minute_low=ohlcv_data.low,
            minute_close=ohlcv_data.close,
            minute_volume=ohlcv_data.volume,
            minute_vwap=ohlcv_data.vwap,
            volume=ohlcv_data.volume,
            vwap=ohlcv_data.vwap,
            accumulated_volume=ohlcv_data.accumulated_volume,
            start_timestamp=ohlcv_data.timestamp - 60,  # 1 minute ago
            end_timestamp=ohlcv_data.timestamp,
            timeframe=ohlcv_data.timeframe,
            market_session=ohlcv_data.market_session
        )
        
        # Add volume surge specific metadata
        event.label = f"Volume Surge {volume_ratio:.1f}x avg via {ohlcv_data.source}"
        
        return event
    
    def _create_significant_move_event(self, ohlcv_data: OHLCVData, symbol_buffer: SymbolBuffer) -> BaseEvent:
        """Create significant price move event"""
        move_direction = '↑' if ohlcv_data.percent_change > 0 else '↓'
        move_type = 'breakout' if ohlcv_data.percent_change > 0 else 'breakdown'
        
        event = PerMinuteAggregateEvent(
            ticker=ohlcv_data.ticker,
            type=f'significant_move_{move_type}',
            price=ohlcv_data.close,
            time=ohlcv_data.timestamp,
            direction=move_direction,
            minute_open=ohlcv_data.open,
            minute_high=ohlcv_data.high,
            minute_low=ohlcv_data.low,
            minute_close=ohlcv_data.close,
            minute_volume=ohlcv_data.volume,
            minute_vwap=ohlcv_data.vwap,
            percent_change=ohlcv_data.percent_change,
            volume=ohlcv_data.volume,
            vwap=ohlcv_data.vwap,
            timeframe=ohlcv_data.timeframe,
            market_session=ohlcv_data.market_session
        )
        
        event.label = f"Move {ohlcv_data.percent_change:+.1f}% via {ohlcv_data.source}"
        
        return event
    
    def _create_high_close_event(self, ohlcv_data: OHLCVData, symbol_buffer: SymbolBuffer) -> BaseEvent:
        """Create high close event"""
        event = PerMinuteAggregateEvent(
            ticker=ohlcv_data.ticker,
            type='high_close_aggregate',
            price=ohlcv_data.close,
            time=ohlcv_data.timestamp,
            direction='↑',
            minute_open=ohlcv_data.open,
            minute_high=ohlcv_data.high,
            minute_low=ohlcv_data.low,
            minute_close=ohlcv_data.close,
            minute_volume=ohlcv_data.volume,
            minute_vwap=ohlcv_data.vwap,
            volume=ohlcv_data.volume,
            vwap=ohlcv_data.vwap,
            timeframe=ohlcv_data.timeframe
        )
        
        event.label = f"High Close {ohlcv_data.timeframe} via {ohlcv_data.source}"
        
        return event
    
    def _create_low_close_event(self, ohlcv_data: OHLCVData, symbol_buffer: SymbolBuffer) -> BaseEvent:
        """Create low close event"""
        event = PerMinuteAggregateEvent(
            ticker=ohlcv_data.ticker,
            type='low_close_aggregate',
            price=ohlcv_data.close,
            time=ohlcv_data.timestamp,
            direction='↓',
            minute_open=ohlcv_data.open,
            minute_high=ohlcv_data.high,
            minute_low=ohlcv_data.low,
            minute_close=ohlcv_data.close,
            minute_volume=ohlcv_data.volume,
            minute_vwap=ohlcv_data.vwap,
            volume=ohlcv_data.volume,
            vwap=ohlcv_data.vwap,
            timeframe=ohlcv_data.timeframe
        )
        
        event.label = f"Low Close {ohlcv_data.timeframe} via {ohlcv_data.source}"
        
        return event
    
    def _add_channel_metadata(self, event: BaseEvent):
        """Add channel-specific metadata to events"""
        channel_info = f"[{self.name}:{self.channel_id[:6]}]"
        if event.label:
            event.label = f"{event.label} {channel_info}"
        else:
            event.label = channel_info
    
    def _update_statistics(self, ohlcv_data: OHLCVData, events: List[BaseEvent]):
        """Update channel processing statistics"""
        self._stats['symbols_tracked'] = len(self._symbol_buffers)
        self._stats['events_generated'] += len(events)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old symbol buffers"""
        current_time = time.time()
        
        if current_time - self._last_cleanup_time > self._cleanup_interval:
            self._last_cleanup_time = current_time
            
            # Clean up old symbol buffers (older than 2 hours)
            cleanup_age = 7200  # 2 hours
            tickers_to_remove = []
            
            for ticker, buffer in self._symbol_buffers.items():
                if current_time - buffer.last_update > cleanup_age:
                    tickers_to_remove.append(ticker)
            
            for ticker in tickers_to_remove:
                del self._symbol_buffers[ticker]
            
            if tickers_to_remove:
                logger.info(f"Cleaned up {len(tickers_to_remove)} old symbol buffers")
    
    async def shutdown(self) -> bool:
        """Shutdown the OHLCV channel"""
        try:
            # Clean up resources
            self._symbol_buffers.clear()
            
            logger.info(f"OHLCVChannel {self.name} shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during OHLCVChannel shutdown: {e}", exc_info=True)
            return False
    
    def get_channel_info(self) -> Dict[str, Any]:
        """Get comprehensive channel information"""
        return {
            'name': self.name,
            'channel_id': self.channel_id,
            'channel_type': 'ohlcv',
            'status': self.status.value,
            'processing_mode': 'batch',
            'batch_size': self.config.batching.max_batch_size,
            'batch_timeout_ms': self.config.batching.max_wait_time_ms,
            'priority': self.config.priority,
            'configuration': {
                'volume_surge_multiplier': self.ohlcv_config.volume_surge_multiplier,
                'significant_move_threshold': self.ohlcv_config.significant_move_threshold,
                'supported_timeframes': getattr(self.ohlcv_config, 'supported_timeframes', ['1m', '5m', '15m'])
            },
            'statistics': self._stats,
            'buffer_info': {
                'symbols_tracked': len(self._symbol_buffers),
                'total_history_points': sum(len(buffer.history) for buffer in self._symbol_buffers.values()),
                'oldest_buffer_age': self._get_oldest_buffer_age(),
                'newest_buffer_age': self._get_newest_buffer_age()
            }
        }
    
    def get_symbol_analysis(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get analysis for specific symbol"""
        if ticker not in self._symbol_buffers:
            return None
        
        buffer = self._symbol_buffers[ticker]
        
        if not buffer.history:
            return {'ticker': ticker, 'status': 'no_data'}
        
        latest_data = buffer.history[-1]
        
        return {
            'ticker': ticker,
            'latest_close': latest_data.close,
            'latest_volume': latest_data.volume,
            'percent_change': latest_data.percent_change,
            'volume_ratio': buffer.get_volume_ratio(latest_data.volume),
            'price_pattern': buffer.get_price_change_pattern(),
            'volume_baseline': buffer.volume_baseline,
            'price_baseline': buffer.price_baseline,
            'history_length': len(buffer.history),
            'last_update': buffer.last_update,
            'timeframe': latest_data.timeframe
        }
    
    def _get_oldest_buffer_age(self) -> float:
        """Get age of oldest buffer in seconds"""
        if not self._symbol_buffers:
            return 0.0
        
        current_time = time.time()
        oldest_time = min(buffer.last_update for buffer in self._symbol_buffers.values())
        return current_time - oldest_time
    
    def _get_newest_buffer_age(self) -> float:
        """Get age of newest buffer in seconds"""
        if not self._symbol_buffers:
            return 0.0
        
        current_time = time.time()
        newest_time = max(buffer.last_update for buffer in self._symbol_buffers.values())
        return current_time - newest_time