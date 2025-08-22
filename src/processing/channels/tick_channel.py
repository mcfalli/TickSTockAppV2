"""
Tick data processing channel implementation.

Concrete implementation of ProcessingChannel for processing real-time tick data
with integration to existing event detection systems.

Sprint 105: Core Channel Infrastructure Implementation
"""

from typing import Any, Optional, List, Dict
import asyncio
import time

from config.logging_config import get_domain_logger, LogDomain

# Import from base channel infrastructure
from .base_channel import ProcessingChannel, ChannelType, ProcessingResult
from .channel_config import TickChannelConfig

# Import from existing domain models
from src.core.domain.market.tick import TickData
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent

# Import existing presentation models for compatibility
from src.presentation.converters.transport_models import StockData

logger = get_domain_logger(LogDomain.CORE, 'tick_channel')


class TickChannel(ProcessingChannel):
    """
    Concrete implementation of ProcessingChannel for tick data processing.
    
    Integrates with existing event detection systems while providing
    the new channel architecture benefits:
    - Standardized metrics and health monitoring
    - Configurable processing parameters
    - Circuit breaker protection
    - Async processing capabilities
    """
    
    def __init__(self, name: str, config: TickChannelConfig):
        super().__init__(name, config)
        
        # Store typed config for easy access
        self.tick_config = config
        
        # Stock data cache (mirrors existing StockData management)
        self._stock_data_cache: Dict[str, StockData] = {}
        
        # Event detection components (to be injected)
        self._highlow_detector = None
        self._trend_detector = None
        self._surge_detector = None
        
        # Performance tracking
        self._last_cleanup_time = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
        logger.info(f"Initialized TickChannel: {name} with event detection: "
                   f"HL={config.highlow_detection['enabled']}, "
                   f"T={config.trend_detection['enabled']}, "
                   f"S={config.surge_detection['enabled']}")
    
    def get_channel_type(self) -> ChannelType:
        """Return TICK channel type"""
        return ChannelType.TICK
    
    async def initialize(self) -> bool:
        """Initialize the tick channel with detection components"""
        try:
            # Initialize event detectors (these would be injected in full implementation)
            await self._initialize_detectors()
            
            # Validate configuration
            if not self._validate_tick_configuration():
                return False
            
            logger.info(f"TickChannel {self.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TickChannel {self.name}: {e}", exc_info=True)
            return False
    
    async def _initialize_detectors(self):
        """Initialize event detection components with real detectors"""
        
        # Use real detector implementations
        try:
            # Import real detectors
            from src.processing.detectors.highlow_detector import HighLowDetector
            from src.processing.detectors.trend_detector import TrendDetector  
            from src.processing.detectors.surge_detector import SurgeDetector
            
            # Get config for detector initialization (use app config structure)
            detector_config = {
                'HIGHLOW_MIN_PRICE_CHANGE': 0.01,
                'HIGHLOW_MIN_PERCENT_CHANGE': 0.1, 
                'HIGHLOW_COOLDOWN_SECONDS': 1.0,
                'HIGHLOW_MARKET_AWARE': True,
                'TREND_GLOBAL_SENSITIVITY': 1.0,
                'TREND_DIRECTION_THRESHOLD': 0.3,
                'SURGE_GLOBAL_SENSITIVITY': 1.0,
                'SURGE_VOLUME_THRESHOLD': 1.3
            }
            
            if self.tick_config.highlow_detection['enabled']:
                self._highlow_detector = RealHighLowDetectorAdapter(
                    HighLowDetector(detector_config)
                )
                logger.info(f"✅ Initialized REAL HighLow detector for channel {self.name}")
            
            if self.tick_config.trend_detection['enabled']:
                self._trend_detector = RealTrendDetectorAdapter(
                    TrendDetector(detector_config)
                )
                logger.info(f"✅ Initialized REAL Trend detector for channel {self.name}")
            
            if self.tick_config.surge_detection['enabled']:
                self._surge_detector = RealSurgeDetectorAdapter(
                    SurgeDetector(detector_config)
                )
                logger.info(f"✅ Initialized REAL Surge detector for channel {self.name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize real detectors, falling back to placeholders: {e}")
            # Fallback to placeholders if real detectors fail
            await self._initialize_placeholder_detectors()
    
    async def _initialize_placeholder_detectors(self):
        """Fallback to placeholder detectors if real ones fail"""
        logger.warning("Using placeholder detectors - limited event generation")
        
        if self.tick_config.highlow_detection['enabled']:
            self._highlow_detector = HighLowDetectorPlaceholder(
                self.tick_config.highlow_detection
            )
            logger.debug(f"Initialized HighLow placeholder for channel {self.name}")
        
        if self.tick_config.trend_detection['enabled']:
            self._trend_detector = TrendDetectorPlaceholder(
                self.tick_config.trend_detection
            )
            logger.debug(f"Initialized Trend placeholder for channel {self.name}")
        
        if self.tick_config.surge_detection['enabled']:
            self._surge_detector = SurgeDetectorPlaceholder(
                self.tick_config.surge_detection
            )
            logger.debug(f"Initialized Surge placeholder for channel {self.name}")
    
    def _validate_tick_configuration(self) -> bool:
        """Validate tick-specific configuration"""
        try:
            # Check detection parameters
            required_params = ['highlow', 'trend', 'surge']
            for param in required_params:
                if param not in self.tick_config.detection_parameters:
                    logger.error(f"Missing detection parameter: {param}")
                    return False
            
            # Check universe filter if specified
            if self.tick_config.universe_filter:
                if not isinstance(self.tick_config.universe_filter, list):
                    logger.error("Universe filter must be a list of ticker symbols")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    def validate_data(self, data: Any) -> bool:
        """Validate incoming tick data"""
        
        # Check if data is TickData object
        if isinstance(data, TickData):
            return self._validate_tick_data(data)
        
        # Check if data is dictionary with required fields
        if isinstance(data, dict):
            required_fields = ['ticker', 'price', 'timestamp']
            if all(field in data for field in required_fields):
                return self._validate_tick_dict(data)
        
        logger.warning(f"Invalid data format for TickChannel: {type(data)}")
        return False
    
    def _validate_tick_data(self, tick_data: TickData) -> bool:
        """Validate TickData object"""
        try:
            # Basic validation
            if not tick_data.ticker or not tick_data.ticker.strip():
                return False
            
            if tick_data.price <= 0:
                return False
            
            if tick_data.timestamp <= 0:
                return False
            
            # Universe filter check
            if self.tick_config.universe_filter:
                if tick_data.ticker not in self.tick_config.universe_filter:
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"TickData validation error: {e}")
            return False
    
    def _validate_tick_dict(self, data: Dict[str, Any]) -> bool:
        """Validate dictionary tick data"""
        try:
            ticker = data.get('ticker', '').strip()
            price = data.get('price', 0)
            timestamp = data.get('timestamp', 0)
            
            if not ticker or price <= 0 or timestamp <= 0:
                return False
            
            # Universe filter check
            if self.tick_config.universe_filter:
                if ticker not in self.tick_config.universe_filter:
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Tick dict validation error: {e}")
            return False
    
    async def process_data(self, data: Any) -> ProcessingResult:
        """
        Process tick data through event detection pipeline.
        
        Main processing logic that:
        1. Converts data to TickData if needed
        2. Updates stock data cache
        3. Runs event detection
        4. Returns generated events
        """
        
        try:
            # Step 1: Convert to TickData if needed
            tick_data = self._convert_to_tick_data(data)
            if not tick_data:
                return ProcessingResult(
                    success=False,
                    errors=["Failed to convert data to TickData"]
                )
            
            # Step 2: Get or create stock data
            stock_data = self._get_or_create_stock_data(tick_data.ticker)
            
            # Step 3: Update stock data with tick information
            self._update_stock_data(stock_data, tick_data)
            
            # Step 4: Run event detection
            events = await self._detect_events(tick_data, stock_data)
            
            # Step 5: Periodic cleanup
            await self._periodic_cleanup()
            
            # Return results
            return ProcessingResult(
                success=True,
                events=events,
                metadata={
                    'ticker': tick_data.ticker,
                    'price': tick_data.price,
                    'events_generated': len(events),
                    'detection_enabled': {
                        'highlow': self.tick_config.highlow_detection['enabled'],
                        'trend': self.tick_config.trend_detection['enabled'],
                        'surge': self.tick_config.surge_detection['enabled']
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing tick data in channel {self.name}: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                errors=[f"Processing error: {str(e)}"],
                metadata={'ticker': getattr(data, 'ticker', 'unknown')}
            )
    
    def _convert_to_tick_data(self, data: Any) -> Optional[TickData]:
        """Convert various data formats to TickData"""
        
        if isinstance(data, TickData):
            return data
        
        if isinstance(data, dict):
            try:
                return TickData(
                    ticker=data['ticker'],
                    price=float(data['price']),
                    timestamp=float(data['timestamp']),
                    volume=data.get('volume'),
                    vwap=data.get('vwap'),
                    session_high=data.get('session_high'),
                    session_low=data.get('session_low'),
                    market_status=data.get('market_status', 'REGULAR')
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to convert dict to TickData: {e}")
                return None
        
        logger.warning(f"Cannot convert {type(data)} to TickData")
        return None
    
    def _get_or_create_stock_data(self, ticker: str) -> StockData:
        """Get existing stock data or create new entry"""
        
        if ticker not in self._stock_data_cache:
            self._stock_data_cache[ticker] = StockData(ticker=ticker)
            # Reduced logging: only log for initial cache creation
            if len(self._stock_data_cache) <= 10:  # Only log first 10 tickers
                logger.debug(f"Created new StockData for ticker: {ticker}")
        
        return self._stock_data_cache[ticker]
    
    def _update_stock_data(self, stock_data: StockData, tick_data: TickData):
        """Update stock data with new tick information"""
        
        stock_data.last_price = tick_data.price
        stock_data.last_update = tick_data.timestamp
        
        # Update volume if available
        if tick_data.volume is not None:
            stock_data.volume = tick_data.volume
        
        # Update VWAP if available (TickData doesn't have vwap attribute - skip for now)
        # TODO: Add VWAP calculation when TickData includes vwap attribute
        
        # Update session highs/lows (use day_high/day_low from TickData)
        if tick_data.day_high is not None:
            stock_data.session_high = tick_data.day_high
        
        if tick_data.day_low is not None:
            stock_data.session_low = tick_data.day_low
        
        # Update market status
        if tick_data.market_status:
            stock_data.market_status = tick_data.market_status
    
    async def _detect_events(self, tick_data: TickData, stock_data: StockData) -> List[BaseEvent]:
        """Run event detection and return generated events"""
        
        events = []
        
        try:
            # High/Low event detection
            if self._highlow_detector and self.tick_config.highlow_detection['enabled']:
                highlow_events = await self._highlow_detector.detect(tick_data, stock_data)
                events.extend(highlow_events)
            
            # Trend event detection
            if self._trend_detector and self.tick_config.trend_detection['enabled']:
                trend_events = await self._trend_detector.detect(tick_data, stock_data)
                events.extend(trend_events)
            
            # Surge event detection
            if self._surge_detector and self.tick_config.surge_detection['enabled']:
                surge_events = await self._surge_detector.detect(tick_data, stock_data)
                events.extend(surge_events)
            
            # Update stock data with any new events (for compatibility with existing system)
            for event in events:
                stock_data.add_event(event)
            
            if events:
                logger.debug(f"Generated {len(events)} events for {tick_data.ticker}: "
                           f"{[e.type for e in events]}")
            
        except Exception as e:
            logger.error(f"Error in event detection for {tick_data.ticker}: {e}", exc_info=True)
        
        return events
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old stock data"""
        current_time = time.time()
        
        if current_time - self._last_cleanup_time > self._cleanup_interval:
            self._last_cleanup_time = current_time
            
            # Clean up old stock data (older than 1 hour)
            cleanup_age = 3600  # 1 hour
            tickers_to_remove = []
            
            for ticker, stock_data in self._stock_data_cache.items():
                if current_time - stock_data.last_update > cleanup_age:
                    tickers_to_remove.append(ticker)
            
            for ticker in tickers_to_remove:
                del self._stock_data_cache[ticker]
            
            if tickers_to_remove:
                logger.info(f"Cleaned up {len(tickers_to_remove)} old stock data entries")
    
    async def shutdown(self) -> bool:
        """Shutdown the tick channel"""
        try:
            # Clean up resources
            self._stock_data_cache.clear()
            
            # Shutdown detectors
            if self._highlow_detector:
                await self._highlow_detector.shutdown()
            if self._trend_detector:
                await self._trend_detector.shutdown()
            if self._surge_detector:
                await self._surge_detector.shutdown()
            
            logger.info(f"TickChannel {self.name} shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during TickChannel shutdown: {e}", exc_info=True)
            return False
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get statistics about the stock data cache"""
        return {
            'cached_tickers': len(self._stock_data_cache),
            'cache_size_mb': self._estimate_cache_size() / (1024 * 1024),
            'oldest_entry_age': self._get_oldest_entry_age(),
            'newest_entry_age': self._get_newest_entry_age()
        }
    
    def _estimate_cache_size(self) -> int:
        """Estimate cache size in bytes (rough approximation)"""
        return len(self._stock_data_cache) * 1024  # Rough estimate: 1KB per entry
    
    def _get_oldest_entry_age(self) -> float:
        """Get age of oldest cache entry in seconds"""
        if not self._stock_data_cache:
            return 0.0
        
        current_time = time.time()
        oldest_time = min(stock_data.last_update for stock_data in self._stock_data_cache.values())
        return current_time - oldest_time
    
    def _get_newest_entry_age(self) -> float:
        """Get age of newest cache entry in seconds"""
        if not self._stock_data_cache:
            return 0.0
        
        current_time = time.time()
        newest_time = max(stock_data.last_update for stock_data in self._stock_data_cache.values())
        return current_time - newest_time


# Placeholder detector implementations for Sprint 105
# In Sprint 106, these would be replaced with actual integrations to existing detectors

class DetectorPlaceholder:
    """Base placeholder for event detectors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    async def detect(self, tick_data: TickData, stock_data: StockData) -> List[BaseEvent]:
        """Placeholder detection method"""
        return []
    
    async def shutdown(self):
        """Placeholder shutdown"""
        pass


class HighLowDetectorPlaceholder(DetectorPlaceholder):
    """Placeholder for high/low event detection"""
    
    async def detect(self, tick_data: TickData, stock_data: StockData) -> List[BaseEvent]:
        """Placeholder high/low detection with basic event generation for testing"""
        events = []
        
        # SPRINT 110 ENHANCEMENT: Generate some events for testing purposes
        # Simple placeholder logic - in real implementation this would use
        # the existing HighLowDetector from src/processing/detectors/
        
        # Generate session high events more frequently for testing
        if stock_data.session_high is None or tick_data.price > stock_data.session_high:
            # Potential session high
            if self._meets_high_criteria(tick_data, stock_data):
                events.append(self._create_high_event(tick_data, stock_data))
        
        if stock_data.session_low is None or tick_data.price < stock_data.session_low:
            # Potential session low
            if self._meets_low_criteria(tick_data, stock_data):
                events.append(self._create_low_event(tick_data, stock_data))
        
        return events
    
    def _meets_high_criteria(self, tick_data: TickData, stock_data: StockData) -> bool:
        """Check if tick meets high event criteria"""
        # More lenient criteria for testing (generate events more frequently)
        min_change = self.config.get('min_price_change', 0.005)  # Reduced threshold
        if stock_data.last_price > 0:
            change = tick_data.price - stock_data.last_price
            return change >= min_change
        return True  # Always generate first event
    
    def _meets_low_criteria(self, tick_data: TickData, stock_data: StockData) -> bool:
        """Check if tick meets low event criteria"""
        # More lenient criteria for testing (generate events more frequently)
        min_change = self.config.get('min_price_change', 0.005)  # Reduced threshold
        if stock_data.last_price > 0:
            change = stock_data.last_price - tick_data.price
            return change >= min_change
        return True  # Always generate first event
    
    def _create_high_event(self, tick_data: TickData, stock_data: StockData) -> HighLowEvent:
        """Create high event (placeholder)"""
        return HighLowEvent(
            ticker=tick_data.ticker,
            type='session_high',
            price=tick_data.price,
            time=tick_data.timestamp,
            direction='↑',
            volume=tick_data.volume or 0,
            vwap=tick_data.vwap,
            reversal=False
        )
    
    def _create_low_event(self, tick_data: TickData, stock_data: StockData) -> HighLowEvent:
        """Create low event (placeholder)"""
        return HighLowEvent(
            ticker=tick_data.ticker,
            type='session_low',
            price=tick_data.price,
            time=tick_data.timestamp,
            direction='↓',
            volume=tick_data.volume or 0,
            vwap=tick_data.vwap,
            reversal=False
        )


class TrendDetectorPlaceholder(DetectorPlaceholder):
    """Placeholder for trend event detection"""
    
    async def detect(self, tick_data: TickData, stock_data: StockData) -> List[BaseEvent]:
        """Placeholder trend detection"""
        # In real implementation, this would use existing TrendDetector
        return []


class SurgeDetectorPlaceholder(DetectorPlaceholder):
    """Placeholder for surge event detection"""
    
    async def detect(self, tick_data: TickData, stock_data: StockData) -> List[BaseEvent]:
        """Placeholder surge detection"""
        # In real implementation, this would use existing SurgeDetector
        return []


# =============================================================================
# Real Detector Adapters
# =============================================================================
# These adapters connect the real detector implementations to the channel system

class RealHighLowDetectorAdapter:
    """Adapter to connect real HighLowDetector to channel system"""
    
    def __init__(self, real_detector):
        self.real_detector = real_detector
        logger.info("✅ RealHighLowDetectorAdapter initialized")
    
    async def detect(self, tick_data: TickData, stock_data: StockData) -> List[BaseEvent]:
        """Detect high/low events using real detector"""
        try:
            # Call the real detector
            result = self.real_detector.detect_highlow(tick_data, stock_data)
            
            # Extract events from result
            events = result.get('events', []) if result else []
            
            # Events generated successfully
            
            return events
            
        except Exception as e:
            logger.error(f"Error in real highlow detector: {e}", exc_info=True)
            return []
    
    async def shutdown(self):
        """Shutdown real detector"""
        pass


class RealTrendDetectorAdapter:
    """Adapter to connect real TrendDetector to channel system"""
    
    def __init__(self, real_detector):
        self.real_detector = real_detector
        logger.info("✅ RealTrendDetectorAdapter initialized")
    
    async def detect(self, tick_data: TickData, stock_data: StockData) -> List[BaseEvent]:
        """Detect trend events using real detector"""
        try:
            # Call the real detector with required parameters
            result = self.real_detector.detect_trend(
                stock_data=stock_data,
                ticker=tick_data.ticker,
                price=tick_data.price,
                vwap=tick_data.vwap or tick_data.price,
                volume=tick_data.volume or 0,
                tick_vwap=tick_data.vwap or tick_data.price,
                tick_volume=tick_data.volume or 0,
                tick_trade_size=tick_data.volume or 0,
                timestamp=tick_data.timestamp
            )
            
            # Extract events from result
            events = result.get('events', []) if result else []
            
            # Events generated successfully
            
            return events
            
        except Exception as e:
            logger.error(f"Error in real trend detector: {e}", exc_info=True)
            return []
    
    async def shutdown(self):
        """Shutdown real detector"""
        pass


class RealSurgeDetectorAdapter:
    """Adapter to connect real SurgeDetector to channel system"""
    
    def __init__(self, real_detector):
        self.real_detector = real_detector
        logger.info("✅ RealSurgeDetectorAdapter initialized")
    
    async def detect(self, tick_data: TickData, stock_data: StockData) -> List[BaseEvent]:
        """Detect surge events using real detector"""
        try:
            # Call the real detector with required parameters
            result = self.real_detector.detect_surge(
                stock_data=stock_data,
                ticker=tick_data.ticker,
                price=tick_data.price,
                vwap=tick_data.vwap or tick_data.price,
                volume=tick_data.volume or 0,
                tick_vwap=tick_data.vwap or tick_data.price,
                tick_volume=tick_data.volume or 0,
                tick_trade_size=tick_data.volume or 0
            )
            
            # Extract events from result
            events = result.get('events', []) if result else []
            
            # Events generated successfully
            
            return events
            
        except Exception as e:
            logger.error(f"Error in real surge detector: {e}", exc_info=True)
            return []
    
    async def shutdown(self):
        """Shutdown real detector"""
        pass