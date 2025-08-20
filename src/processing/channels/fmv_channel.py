"""
FMV Channel Implementation for Sprint 106: Data Type Handlers

Processes Fair Market Value (FMV) data with confidence-based filtering,
deviation detection, and valuation discrepancy event creation.

Designed for high-quality valuation analysis with configurable confidence
thresholds and sophisticated deviation detection algorithms.
"""

from typing import Any, Optional, List, Dict, Tuple
from collections import deque
from dataclasses import dataclass, field
import asyncio
import time
import statistics

from config.logging_config import get_domain_logger, LogDomain

# Import base channel infrastructure
from .base_channel import ProcessingChannel, ChannelType, ProcessingResult
from .channel_config import FMVChannelConfig

# Import data models
from src.shared.models.data_types import FMVData, identify_data_type
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.fmv import FairMarketValueEvent

logger = get_domain_logger(LogDomain.CORE, 'fmv_channel')


@dataclass
class ValuationHistory:
    """Track valuation history for confidence analysis and trend detection"""
    ticker: str
    fmv_history: deque = field(default_factory=lambda: deque(maxlen=50))
    confidence_history: deque = field(default_factory=lambda: deque(maxlen=50))
    deviation_history: deque = field(default_factory=lambda: deque(maxlen=50))
    last_update: float = field(default_factory=time.time)
    
    def add_valuation(self, fmv_data: FMVData):
        """Add new FMV data to history"""
        self.fmv_history.append(fmv_data.fmv)
        self.confidence_history.append(fmv_data.confidence)
        self.deviation_history.append(fmv_data.deviation_percent)
        self.last_update = time.time()
    
    def get_confidence_trend(self, periods: int = 10) -> str:
        """Analyze confidence trend over recent periods"""
        if len(self.confidence_history) < periods:
            return 'insufficient_data'
        
        recent_confidence = list(self.confidence_history)[-periods:]
        avg_recent = statistics.mean(recent_confidence)
        
        if len(self.confidence_history) >= periods * 2:
            older_confidence = list(self.confidence_history)[-(periods*2):-periods]
            avg_older = statistics.mean(older_confidence)
            
            if avg_recent > avg_older + 0.05:
                return 'improving'
            elif avg_recent < avg_older - 0.05:
                return 'declining'
        
        if avg_recent >= 0.8:
            return 'high_confidence'
        elif avg_recent >= 0.6:
            return 'moderate_confidence'
        else:
            return 'low_confidence'
    
    def get_deviation_consistency(self, periods: int = 5) -> Tuple[float, str]:
        """Analyze deviation consistency"""
        if len(self.deviation_history) < periods:
            return 0.0, 'insufficient_data'
        
        recent_deviations = list(self.deviation_history)[-periods:]
        
        positive_count = sum(1 for d in recent_deviations if d > 0)
        negative_count = sum(1 for d in recent_deviations if d < 0)
        
        consistency_ratio = max(positive_count, negative_count) / periods
        
        if consistency_ratio >= 0.8:
            signal_direction = 'undervalued' if positive_count > negative_count else 'overvalued'
            return consistency_ratio, f'consistent_{signal_direction}'
        elif consistency_ratio >= 0.6:
            return consistency_ratio, 'moderately_consistent'
        else:
            return consistency_ratio, 'inconsistent'
    
    def get_average_confidence(self, periods: int = 10) -> float:
        """Get average confidence over recent periods"""
        if len(self.confidence_history) < periods:
            periods = len(self.confidence_history)
        
        if periods == 0:
            return 0.0
        
        recent_confidence = list(self.confidence_history)[-periods:]
        return statistics.mean(recent_confidence)


class FMVChannel(ProcessingChannel):
    """
    FMV Channel for processing Fair Market Value data.
    
    Features:
    - Batch processing with efficiency optimization (default: batch_size=50, timeout=500ms)
    - Confidence-based filtering with minimum threshold (default: 0.8)
    - Deviation detection with configurable threshold (default: 1.0%)
    - Valuation trend analysis and signal strength calculation
    """
    
    def __init__(self, name: str, config: FMVChannelConfig):
        super().__init__(name, config)
        
        # Store typed config for easy access
        self.fmv_config = config
        
        # Valuation history tracking
        self._valuation_histories: Dict[str, ValuationHistory] = {}
        
        # Processing statistics
        self._stats = {
            'fmv_data_processed': 0,
            'high_confidence_filtered': 0,
            'low_confidence_rejected': 0,
            'significant_deviations_detected': 0,
            'valuation_events_generated': 0,
            'symbols_tracked': 0
        }
        
        # Performance tracking
        self._last_cleanup_time = time.time()
        self._cleanup_interval = 900  # 15 minutes
        
        logger.info(f"Initialized FMVChannel: {name} with confidence_threshold={config.confidence_threshold}, "
                   f"deviation_threshold={config.deviation_threshold}%, "
                   f"batch_size={config.batching.max_batch_size}")
    
    def get_channel_type(self) -> ChannelType:
        """Return FMV channel type"""
        return ChannelType.FMV
    
    async def initialize(self) -> bool:
        """Initialize the FMV channel"""
        try:
            if not self._validate_fmv_configuration():
                return False
            
            logger.info(f"FMVChannel {self.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize FMVChannel {self.name}: {e}", exc_info=True)
            return False
    
    def _validate_fmv_configuration(self) -> bool:
        """Validate FMV-specific configuration"""
        try:
            if not hasattr(self.fmv_config, 'confidence_threshold'):
                logger.error("Missing confidence_threshold in FMV config")
                return False
            
            if not hasattr(self.fmv_config, 'deviation_threshold'):
                logger.error("Missing deviation_threshold in FMV config")
                return False
            
            if not (0.0 <= self.fmv_config.confidence_threshold <= 1.0):
                logger.error(f"Invalid confidence_threshold: {self.fmv_config.confidence_threshold}")
                return False
            
            if self.fmv_config.deviation_threshold <= 0:
                logger.error(f"Invalid deviation_threshold: {self.fmv_config.deviation_threshold}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    def validate_data(self, data: Any) -> bool:
        """Validate incoming FMV data"""
        
        if isinstance(data, FMVData):
            return self._validate_fmv_data(data)
        
        if isinstance(data, dict):
            required_fields = ['ticker', 'fmv', 'market_price', 'confidence']
            if all(field in data for field in required_fields):
                return self._validate_fmv_dict(data)
        
        if isinstance(data, dict) and ('fmv_price' in data or 'fmv' in data):
            return self._validate_fmv_event(data)
        
        logger.warning(f"Invalid data format for FMVChannel: {type(data)}")
        return False
    
    def _validate_fmv_data(self, fmv_data: FMVData) -> bool:
        """Validate FMVData object"""
        try:
            return fmv_data.validate()
        except Exception as e:
            logger.warning(f"FMVData validation error: {e}")
            return False
    
    def _validate_fmv_dict(self, data: Dict[str, Any]) -> bool:
        """Validate dictionary FMV data"""
        try:
            ticker = data.get('ticker', '').strip()
            if not ticker:
                return False
            
            fmv = float(data['fmv'])
            market_price = float(data['market_price'])
            confidence = float(data['confidence'])
            
            if fmv <= 0 or market_price <= 0:
                return False
            
            if not (0.0 <= confidence <= 1.0):
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"FMV dict validation error: {e}")
            return False
    
    def _validate_fmv_event(self, data: Dict[str, Any]) -> bool:
        """Validate FMV event data"""
        try:
            required_fields = ['ticker', 'fmv_price', 'market_price']
            return all(field in data for field in required_fields)
        except Exception as e:
            logger.warning(f"FMV event validation error: {e}")
            return False
    
    async def process_data(self, data: Any) -> ProcessingResult:
        """Process FMV data through valuation analysis pipeline"""
        
        try:
            # Step 1: Validate data type
            data_type = identify_data_type(data)
            if data_type != 'fmv' and data_type != 'unknown':
                return ProcessingResult(
                    success=False,
                    errors=[f"Invalid data type '{data_type}' for FMVChannel"]
                )
            
            # Step 2: Convert to FMVData
            fmv_data = self._convert_to_fmv_data(data)
            if not fmv_data:
                return ProcessingResult(
                    success=False,
                    errors=["Failed to convert data to FMVData"]
                )
            
            # Step 3: Apply confidence filtering
            if not self._meets_confidence_threshold(fmv_data):
                self._stats['low_confidence_rejected'] += 1
                return ProcessingResult(
                    success=True,
                    events=[],
                    metadata={
                        'ticker': fmv_data.ticker,
                        'confidence': fmv_data.confidence,
                        'status': 'filtered_low_confidence',
                        'threshold': self.fmv_config.confidence_threshold
                    }
                )
            
            # Step 4: Update valuation history
            valuation_history = self._get_or_create_valuation_history(fmv_data.ticker)
            valuation_history.add_valuation(fmv_data)
            
            # Step 5: Analyze and detect events
            events = await self._analyze_fmv_data(fmv_data, valuation_history)
            
            # Step 6: Add metadata and update stats
            for event in events:
                self._add_channel_metadata(event)
            
            self._update_statistics(fmv_data, events)
            await self._periodic_cleanup()
            
            # Return results
            return ProcessingResult(
                success=True,
                events=events,
                metadata={
                    'ticker': fmv_data.ticker,
                    'fmv_price': fmv_data.fmv,
                    'market_price': fmv_data.market_price,
                    'confidence': fmv_data.confidence,
                    'deviation_percent': fmv_data.deviation_percent,
                    'valuation_signal': fmv_data.get_valuation_signal(),
                    'events_generated': len(events),
                    'channel_name': self.name,
                    'channel_type': 'fmv'
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing FMV data in channel {self.name}: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                errors=[f"Processing error: {str(e)}"],
                metadata={'ticker': getattr(data, 'ticker', 'unknown')}
            )
    
    def _convert_to_fmv_data(self, data: Any) -> Optional[FMVData]:
        """Convert various data formats to FMVData"""
        
        if isinstance(data, FMVData):
            return data
        
        if isinstance(data, dict):
            try:
                if 'fmv' in data and 'market_price' in data:
                    return FMVData(
                        ticker=data['ticker'],
                        timestamp=data.get('timestamp', time.time()),
                        fmv=float(data['fmv']),
                        market_price=float(data['market_price']),
                        confidence=float(data['confidence']),
                        deviation_percent=data.get('deviation_percent', 0.0),
                        valuation_model=data.get('valuation_model', 'unknown'),
                        source=data.get('source', 'fmv')
                    )
                elif 'fmv_price' in data:
                    return FMVData.from_fmv_event(data)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to convert dict to FMVData: {e}")
                return None
        
        logger.warning(f"Cannot convert {type(data)} to FMVData")
        return None
    
    def _meets_confidence_threshold(self, fmv_data: FMVData) -> bool:
        """Check if FMV data meets confidence threshold"""
        return fmv_data.confidence >= self.fmv_config.confidence_threshold
    
    def _get_or_create_valuation_history(self, ticker: str) -> ValuationHistory:
        """Get existing valuation history or create new one"""
        
        if ticker not in self._valuation_histories:
            self._valuation_histories[ticker] = ValuationHistory(ticker=ticker)
            logger.debug(f"Created new ValuationHistory for ticker: {ticker}")
        
        return self._valuation_histories[ticker]
    
    async def _analyze_fmv_data(self, fmv_data: FMVData, valuation_history: ValuationHistory) -> List[BaseEvent]:
        """Analyze FMV data and generate valuation events"""
        
        events = []
        
        try:
            # Check for significant deviation
            if fmv_data.is_significant_deviation(self.fmv_config.deviation_threshold):
                deviation_event = self._create_valuation_deviation_event(fmv_data)
                events.append(deviation_event)
                self._stats['significant_deviations_detected'] += 1
            
            # Check for high-confidence, high-strength signals
            signal_strength = fmv_data.get_signal_strength()
            if signal_strength >= 0.7:
                confidence_event = self._create_high_confidence_event(fmv_data)
                events.append(confidence_event)
            
            # Check for consistent valuation trends
            consistency_ratio, consistency_type = valuation_history.get_deviation_consistency()
            if consistency_ratio >= 0.8 and 'consistent' in consistency_type:
                trend_event = self._create_valuation_trend_event(fmv_data, consistency_type)
                events.append(trend_event)
            
            if events:
                logger.debug(f"Generated {len(events)} FMV events for {fmv_data.ticker}")
            
        except Exception as e:
            logger.error(f"Error in FMV analysis for {fmv_data.ticker}: {e}", exc_info=True)
        
        return events
    
    def _create_valuation_deviation_event(self, fmv_data: FMVData) -> BaseEvent:
        """Create valuation deviation event"""
        signal = fmv_data.get_valuation_signal()
        
        event = FairMarketValueEvent(
            ticker=fmv_data.ticker,
            type='valuation_deviation',
            price=fmv_data.market_price,
            time=fmv_data.timestamp,
            fmv_price=fmv_data.fmv,
            market_price=fmv_data.market_price,
            fmv_vs_market_pct=fmv_data.deviation_percent,
            is_undervalued=signal == 'undervalued',
            is_overvalued=signal == 'overvalued'
        )
        
        event.label = f"FMV Deviation {fmv_data.deviation_percent:+.1f}% via {fmv_data.source}"
        return event
    
    def _create_high_confidence_event(self, fmv_data: FMVData) -> BaseEvent:
        """Create high-confidence valuation event"""
        signal = fmv_data.get_valuation_signal()
        
        event = FairMarketValueEvent(
            ticker=fmv_data.ticker,
            type='high_confidence_valuation',
            price=fmv_data.market_price,
            time=fmv_data.timestamp,
            fmv_price=fmv_data.fmv,
            market_price=fmv_data.market_price,
            fmv_vs_market_pct=fmv_data.deviation_percent,
            is_undervalued=signal == 'undervalued',
            is_overvalued=signal == 'overvalued'
        )
        
        event.label = f"High Confidence {signal.title()} via {fmv_data.source}"
        return event
    
    def _create_valuation_trend_event(self, fmv_data: FMVData, consistency_type: str) -> BaseEvent:
        """Create consistent valuation trend event"""
        
        event = FairMarketValueEvent(
            ticker=fmv_data.ticker,
            type='consistent_valuation_trend',
            price=fmv_data.market_price,
            time=fmv_data.timestamp,
            fmv_price=fmv_data.fmv,
            market_price=fmv_data.market_price,
            fmv_vs_market_pct=fmv_data.deviation_percent
        )
        
        event.label = f"Trend: {consistency_type.replace('_', ' ').title()} via {fmv_data.source}"
        return event
    
    def _add_channel_metadata(self, event: BaseEvent):
        """Add channel-specific metadata to events"""
        channel_info = f"[{self.name}:{self.channel_id[:6]}]"
        if event.label:
            event.label = f"{event.label} {channel_info}"
        else:
            event.label = channel_info
    
    def _update_statistics(self, fmv_data: FMVData, events: List[BaseEvent]):
        """Update channel processing statistics"""
        self._stats['fmv_data_processed'] += 1
        self._stats['high_confidence_filtered'] += 1
        self._stats['valuation_events_generated'] += len(events)
        self._stats['symbols_tracked'] = len(self._valuation_histories)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old valuation histories"""
        current_time = time.time()
        
        if current_time - self._last_cleanup_time > self._cleanup_interval:
            self._last_cleanup_time = current_time
            
            cleanup_age = 14400  # 4 hours
            tickers_to_remove = []
            
            for ticker, history in self._valuation_histories.items():
                if current_time - history.last_update > cleanup_age:
                    tickers_to_remove.append(ticker)
            
            for ticker in tickers_to_remove:
                del self._valuation_histories[ticker]
            
            if tickers_to_remove:
                logger.info(f"Cleaned up {len(tickers_to_remove)} old valuation histories")
    
    async def shutdown(self) -> bool:
        """Shutdown the FMV channel"""
        try:
            self._valuation_histories.clear()
            logger.info(f"FMVChannel {self.name} shutdown completed")
            return True
        except Exception as e:
            logger.error(f"Error during FMVChannel shutdown: {e}", exc_info=True)
            return False