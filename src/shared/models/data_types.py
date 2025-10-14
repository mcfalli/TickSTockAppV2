"""
Data Type Models for Sprint 106: Data Type Handlers

Defines standardized data structures for different market data types used across 
the multi-channel processing infrastructure. These models provide compatibility
with existing event systems while enabling specialized channel processing.

Created: Sprint 106 - Data Type Handlers Implementation
"""

from dataclasses import dataclass
from typing import Any

# Import existing TickData model
from src.core.domain.market.tick import TickData


@dataclass
class OHLCVData:
    """
    OHLCV (Open, High, Low, Close, Volume) aggregate data for minute-level processing.
    
    Designed for OHLCVChannel batch processing with symbol-based buffering and
    aggregate-specific event detection. Compatible with existing PerMinuteAggregateEvent.
    """
    # Required identification fields
    ticker: str
    timestamp: float  # Unix timestamp for the period end

    # OHLC price data
    open: float
    high: float
    low: float
    close: float

    # Volume data
    volume: int
    avg_volume: float  # Average volume for comparison (historical baseline)

    # Calculated fields
    percent_change: float = 0.0  # (close - open) / open * 100

    # Optional market context fields
    vwap: float | None = None  # Volume weighted average price
    daily_open: float | None = None  # Official opening price for the day
    accumulated_volume: int | None = None  # Total daily volume
    trade_count: int | None = None  # Number of trades in period

    # Period identification
    timeframe: str = "1m"  # Period timeframe: 1m, 5m, 15m, 1h, etc.
    market_session: str = "REGULAR"  # REGULAR, PRE, POST

    # Processing metadata
    source: str = "unknown"
    processed_at: float | None = None

    def __post_init__(self):
        """Calculate derived fields and validate data"""
        # Calculate percent change if not provided
        if self.percent_change == 0.0 and self.open > 0:
            self.percent_change = ((self.close - self.open) / self.open) * 100.0

        # Validate on instantiation
        self.validate()

    def validate(self) -> bool:
        """Validate OHLCV data integrity"""
        if not self.ticker:
            raise ValueError("Empty ticker")

        if self.timestamp <= 0:
            raise ValueError(f"Invalid timestamp: {self.timestamp}")

        # Validate price relationships
        if self.high < max(self.open, self.close):
            raise ValueError(f"High {self.high} must be >= max(open {self.open}, close {self.close})")

        if self.low > min(self.open, self.close):
            raise ValueError(f"Low {self.low} must be <= min(open {self.open}, close {self.close})")

        # Validate non-negative values
        for field, value in [("open", self.open), ("high", self.high), ("low", self.low), ("close", self.close)]:
            if value <= 0:
                raise ValueError(f"Invalid {field}: {value}")

        if self.volume < 0:
            raise ValueError(f"Invalid volume: {self.volume}")

        if self.avg_volume <= 0:
            raise ValueError(f"Invalid avg_volume: {self.avg_volume}")

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization/transport"""
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'avg_volume': self.avg_volume,
            'percent_change': self.percent_change,
            'vwap': self.vwap,
            'daily_open': self.daily_open,
            'accumulated_volume': self.accumulated_volume,
            'trade_count': self.trade_count,
            'timeframe': self.timeframe,
            'market_session': self.market_session,
            'source': self.source,
            'processed_at': self.processed_at
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'OHLCVData':
        """Create instance from dictionary"""
        return cls(**data)

    @classmethod
    def from_aggregate_event(cls, event_data: dict[str, Any]) -> 'OHLCVData':
        """Create from PerMinuteAggregateEvent or similar aggregate data"""
        return cls(
            ticker=event_data['ticker'],
            timestamp=event_data['time'],
            open=event_data.get('minute_open', event_data.get('open', 0)),
            high=event_data.get('minute_high', event_data.get('high', 0)),
            low=event_data.get('minute_low', event_data.get('low', 0)),
            close=event_data.get('minute_close', event_data.get('close', event_data.get('price', 0))),
            volume=event_data.get('minute_volume', event_data.get('volume', 0)),
            avg_volume=event_data.get('avg_volume', event_data.get('accumulated_volume', 1000000)),
            percent_change=event_data.get('minute_price_change_pct', 0.0),
            vwap=event_data.get('minute_vwap', event_data.get('vwap')),
            daily_open=event_data.get('daily_open'),
            accumulated_volume=event_data.get('accumulated_volume'),
            trade_count=event_data.get('trade_count'),
            timeframe=event_data.get('timeframe', '1m'),
            market_session=event_data.get('market_session', 'REGULAR'),
            source=event_data.get('source', 'aggregate'),
            processed_at=event_data.get('processed_at')
        )

    def get_price_range(self) -> float:
        """Get price range (high - low)"""
        return self.high - self.low

    def get_price_change(self) -> float:
        """Get absolute price change (close - open)"""
        return self.close - self.open

    def is_volume_surge(self, threshold_multiplier: float = 3.0) -> bool:
        """Check if volume is significantly above average"""
        return self.volume >= (self.avg_volume * threshold_multiplier)

    def is_significant_move(self, threshold_percent: float = 2.0) -> bool:
        """Check if price movement is significant"""
        return abs(self.percent_change) >= threshold_percent

    def __str__(self) -> str:
        """String representation for logging"""
        return f"OHLCV {self.ticker} O:{self.open:.2f} H:{self.high:.2f} L:{self.low:.2f} C:{self.close:.2f} V:{self.volume:,} ({self.percent_change:+.1f}%)"


@dataclass
class FMVData:
    """
    Fair Market Value data for valuation processing.
    
    Designed for FMVChannel processing with confidence-based filtering and 
    deviation detection. Compatible with existing FairMarketValueEvent.
    """
    # Required identification fields
    ticker: str
    timestamp: float  # Unix timestamp

    # Fair Market Value data
    fmv: float  # Fair market value price
    market_price: float  # Current market price for comparison

    # Confidence and deviation metrics
    confidence: float  # Confidence score (0.0 to 1.0)
    deviation_percent: float = 0.0  # Calculated: (fmv - market_price) / market_price * 100

    # Optional valuation context
    valuation_model: str = "unknown"  # dcf, comparable, option_based, etc.
    model_inputs: dict[str, Any] | None = None

    # Risk adjustments
    volatility_adjustment: float | None = None
    liquidity_adjustment: float | None = None
    sector_correlation: float | None = None

    # Processing metadata
    source: str = "unknown"
    processed_at: float | None = None

    def __post_init__(self):
        """Calculate derived fields and validate data"""
        # Calculate deviation if not provided
        if self.deviation_percent == 0.0 and self.market_price > 0:
            self.deviation_percent = ((self.fmv - self.market_price) / self.market_price) * 100.0

        # Initialize empty model_inputs if None
        if self.model_inputs is None:
            self.model_inputs = {}

        # Validate on instantiation
        self.validate()

    def validate(self) -> bool:
        """Validate FMV data integrity"""
        if not self.ticker:
            raise ValueError("Empty ticker")

        if self.timestamp <= 0:
            raise ValueError(f"Invalid timestamp: {self.timestamp}")

        if self.fmv <= 0:
            raise ValueError(f"Invalid FMV price: {self.fmv}")

        if self.market_price <= 0:
            raise ValueError(f"Invalid market price: {self.market_price}")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Invalid confidence: {self.confidence} (must be 0.0-1.0)")

        return True

    def calculate_deviation(self) -> float:
        """Calculate percentage deviation of FMV from market price"""
        if self.market_price <= 0:
            return 0.0
        return ((self.fmv - self.market_price) / self.market_price) * 100.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization/transport"""
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp,
            'fmv': self.fmv,
            'market_price': self.market_price,
            'confidence': self.confidence,
            'deviation_percent': self.deviation_percent,
            'valuation_model': self.valuation_model,
            'model_inputs': self.model_inputs,
            'volatility_adjustment': self.volatility_adjustment,
            'liquidity_adjustment': self.liquidity_adjustment,
            'sector_correlation': self.sector_correlation,
            'source': self.source,
            'processed_at': self.processed_at
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FMVData':
        """Create instance from dictionary"""
        return cls(**data)

    @classmethod
    def from_fmv_event(cls, event_data: dict[str, Any]) -> 'FMVData':
        """Create from FairMarketValueEvent or similar FMV data"""
        return cls(
            ticker=event_data['ticker'],
            timestamp=event_data['time'],
            fmv=event_data.get('fmv_price', event_data.get('fmv', event_data.get('price', 0))),
            market_price=event_data.get('market_price', event_data.get('price', 0)),
            confidence=event_data.get('confidence', event_data.get('fmv_confidence', 0.5)),
            deviation_percent=event_data.get('fmv_vs_market_pct', 0.0),
            valuation_model=event_data.get('valuation_model', 'unknown'),
            model_inputs=event_data.get('model_inputs', {}),
            volatility_adjustment=event_data.get('volatility_adjustment'),
            liquidity_adjustment=event_data.get('liquidity_adjustment'),
            sector_correlation=event_data.get('sector_correlation'),
            source=event_data.get('source', 'fmv'),
            processed_at=event_data.get('processed_at')
        )

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if FMV data meets confidence threshold"""
        return self.confidence >= threshold

    def is_significant_deviation(self, threshold_percent: float = 1.0) -> bool:
        """Check if FMV deviates significantly from market price"""
        return abs(self.deviation_percent) >= threshold_percent

    def get_valuation_signal(self) -> str:
        """Get simplified valuation signal based on deviation"""
        if self.deviation_percent > 1.0:  # FMV > market price
            return "undervalued"
        if self.deviation_percent < -1.0:  # FMV < market price
            return "overvalued"
        return "fair_value"

    def get_signal_strength(self) -> float:
        """Get signal strength based on confidence and deviation magnitude"""
        deviation_strength = min(abs(self.deviation_percent) / 10.0, 1.0)  # Cap at 10%
        return self.confidence * deviation_strength

    def __str__(self) -> str:
        """String representation for logging"""
        signal = self.get_valuation_signal().upper()
        return f"FMV {self.ticker} FMV:${self.fmv:.2f} Market:${self.market_price:.2f} ({self.deviation_percent:+.1f}%) [{signal}] Conf:{self.confidence:.2f}"


# Utility functions for data type identification
def identify_data_type(data: Any) -> str:
    """
    Identify the data type for routing to appropriate channel.
    
    Args:
        data: Data object to identify
        
    Returns:
        Data type string: 'tick', 'ohlcv', 'fmv', or 'unknown'
    """
    if isinstance(data, TickData):
        return 'tick'
    if isinstance(data, OHLCVData):
        return 'ohlcv'
    if isinstance(data, FMVData):
        return 'fmv'
    if isinstance(data, dict):
        # Try to identify from dictionary structure
        if 'fmv' in data or 'fmv_price' in data:
            return 'fmv'
        if all(field in data for field in ['open', 'high', 'low', 'close']):
            return 'ohlcv'
        if 'ticker' in data and 'price' in data:
            return 'tick'

    return 'unknown'


def convert_to_typed_data(data: dict[str, Any], data_type: str = None) -> Any:
    """
    Convert dictionary data to appropriate typed data model.
    
    Args:
        data: Dictionary data to convert
        data_type: Optional explicit data type, will auto-detect if None
        
    Returns:
        Typed data object (TickData, OHLCVData, or FMVData)
        
    Raises:
        ValueError: If data type cannot be determined or conversion fails
    """
    if data_type is None:
        data_type = identify_data_type(data)

    try:
        if data_type == 'tick':
            return TickData.from_dict(data) if hasattr(TickData, 'from_dict') else TickData(**data)
        if data_type == 'ohlcv':
            return OHLCVData.from_dict(data)
        if data_type == 'fmv':
            return FMVData.from_dict(data)
        raise ValueError(f"Unknown data type: {data_type}")

    except Exception as e:
        raise ValueError(f"Failed to convert data to {data_type}: {e}")
