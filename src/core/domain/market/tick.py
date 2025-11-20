# classes/market/tick.py - Enhanced version
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TickData:
    """
    Standardized tick data from any source.
    Replaces MarketEvent throughout the system.

    Record Type "A" Aggregate Per Second:
    
    column, fieldname, datatype, description, required, usage
    ev, "Event_Type", string, "The event type", yes, "Used to identify the incoming record type. 'A' Aggregate Per Second WebSocket Subscription"
    sym, "Ticker", string, "The ticker symbol for the given stock.", yes, "Required to identify the stock"
    v, "Tick_Volume", integer, "The tick volume.", yes, "No logic currently implemented. Store and pass through to consumers. Future state to track volume per second to not surging or highlight steady increase or decrease"
    av, "Volume", integer, "Today's accumulated volume.", yes, "No logic currently implemented. Store and pass through to consumers. Future state will assist in calculations such as relative strength"
    op, "Opening_Price", number, "Today's official opening price.", yes, "When the market opens for the day, the next event would have this value and be the baseline so the next seconds record can be compared as a new session high or low"
    vw, "Tick_VWAP", number, "The tick's volume weighted average price.", yes, "No logic currently implemented. Store and pass through to consumers. Future state would use this to assist with trending, are we above or below and moving away from this price level"
    o, "Tick_Open", number, "The opening tick price for this aggregate window.", yes, "No logic currently implemented. Store and pass through to consumers. Might be storage only" 
    c, "Tick_Close", number, "The closing tick price for this aggregate window.", yes, "The closing price for this tick or second would be the value to calculate against prior stored high or low to determine if we have a new high or low"
    h, "Tick_High", number, "The highest tick price for this aggregate window.", yes, "No logic currently implemented. Store and pass through to consumers. This could assist with a huge spike up or down to notify front end"
    l, "Tick_Low", number, "The lowest tick price for this aggregate window.", yes, "No logic currently implemented. Store and pass through to consumers. This could assist with a huge spike up or down to notify front end"
    a, "VWAP", number, "Today's volume weighted average price.", yes, "No logic currently implemented. Store and pass through to consumers. VWAP. Future state would use this to assist with trending, are we above or below and moving away from this price level"
    z, "Trade_Size", integer, "The average trade size for this aggregate window.", yes, "No logic currently implemented. Store and pass through to consumers. Future state would be able to leverage for larger than normal or average trade size along with other indicators suggesting buying or selling"
    s, "Start_Timestamp", integer, "The start timestamp of this aggregate window in Unix Milliseconds.", yes, "No logic currently implemented. Store and pass through to consumers. Might be storage only" 
    e, "Timestamp", integer, "The end timestamp of this aggregate window in Unix Milliseconds.", yes, "Capture and pass through as the time stamp for this stock events record"
    """

    # Required fields
    ticker: str
    price: float
    volume: int
    timestamp: float

    # Source identification
    source: str = "unknown"  # 'polygon', 'synthetic', 'simulated', 'alpaca', etc.
    event_type: str = "A"  # A=Aggregate, T=Trade, Q=Quote

    # Market data
    bid: float | None = None
    ask: float | None = None
    market_status: str = "REGULAR"  # 'PREMARKET', 'REGULAR', 'AFTERHOURS'

    # Price fields (tick-level)
    tick_open: float | None = None
    tick_high: float | None = None
    tick_low: float | None = None
    tick_close: float | None = None

    # Price fields (day-level)
    day_high: float | None = None
    day_low: float | None = None
    open_price: float | None = None  # Day open
    market_open_price: float | None = None  # Market session open
    previous_close: float | None = None

    # Volume fields
    tick_volume: int | None = None  # Volume for this tick
    tick_trade_size: int | None = None  # Size of individual trade
    accumulated_volume: int | None = None  # Total day volume

    # VWAP fields
    tick_vwap: float | None = None
    vwap: float | None = None  # Day VWAP

    # Timing fields
    tick_start_timestamp: float | None = None
    tick_end_timestamp: float | None = None

    # Processing fields (added during processing)
    processed_at: float | None = None
    effective_volume: int | None = None
    effective_vwap: float | None = None

    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure tick_close defaults to price if not set
        if self.tick_close is None:
            self.tick_close = self.price

        # Ensure volume is properly set
        if self.tick_volume is None and self.volume:
            self.tick_volume = self.volume

        # Validate on instantiation
        self.validate()

    def validate(self) -> bool:
        """Validate tick data"""
        if self.price <= 0:
            raise ValueError(f"Invalid price: {self.price}")
        if self.volume < 0:
            raise ValueError(f"Invalid volume: {self.volume}")
        if not self.ticker:
            raise ValueError("Empty ticker")
        if self.timestamp <= 0:
            raise ValueError(f"Invalid timestamp: {self.timestamp}")

         # ADD: Ensure timestamp is numeric (not datetime object)
        if not isinstance(self.timestamp, (int, float)):
            raise ValueError(f"Timestamp must be numeric (int/float), got {type(self.timestamp).__name__}")

        return True
    '''       
    @property
    def datetime(self) -> datetime:
        """Get timestamp as datetime object."""
        return datetime.fromtimestamp(self.timestamp)
    
    @property
    def hour(self) -> int:
        """Get hour from timestamp."""
        return self.datetime.hour
    
    @property
    def minute(self) -> int:
        """Get minute from timestamp."""
        return self.datetime.minute
    
    @property
    def second(self) -> int:
        """Get second from timestamp."""
        return self.datetime.second
    '''

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'ticker': self.ticker,
            'price': self.price,
            'volume': self.volume,
            'timestamp': self.timestamp,
            'source': self.source,
            'event_type': self.event_type,
            'market_status': self.market_status,
            'bid': self.bid,
            'ask': self.ask,
            'tick_open': self.tick_open,
            'tick_high': self.tick_high,
            'tick_low': self.tick_low,
            'tick_close': self.tick_close,
            'day_high': self.day_high,
            'day_low': self.day_low,
            'open_price': self.open_price,
            'market_open_price': self.market_open_price,
            'previous_close': self.previous_close,
            'tick_volume': self.tick_volume,
            'tick_trade_size': self.tick_trade_size,
            'accumulated_volume': self.accumulated_volume,
            'tick_vwap': self.tick_vwap,
            'vwap': self.vwap,
            'tick_start_timestamp': self.tick_start_timestamp,
            'tick_end_timestamp': self.tick_end_timestamp
        }

    @classmethod
    def from_massive_ws(cls, data: dict) -> 'TickData':
        """Create from Massive WebSocket data."""
        # Massive WebSocket format
        return cls(
            ticker=data['sym'],
            price=data['p'],
            volume=data.get('v', 0),
            timestamp=data['t'] / 1000.0,  # Convert ms to seconds
            source='polygon',
            event_type=data.get('ev', 'A'),
            market_status='REGULAR',  # Will be updated by processor
            bid=data.get('b'),
            ask=data.get('a'),
            tick_vwap=data.get('vw'),
            tick_trade_size=data.get('s')
        )

    @classmethod
    def from_synthetic(cls, ticker: str, price: float, baseline: dict,
                      market_status: str, current_time: datetime, is_up: bool) -> 'TickData':
        """Create synthetic tick data."""
        import random

        # Generate realistic values
        tick_high = round(price * (1 + random.uniform(0, 0.002)), 2) if is_up else price
        tick_low = price if is_up else round(price * (1 - random.uniform(0, 0.002)), 2)

        # Volume calculations
        avg_volume = baseline.get('avg_volume', 1000000)
        sector = baseline.get('sector', 'Unknown')

        # Sector volume multipliers
        sector_volume_multipliers = {
            'Technology': 1.2,
            'Healthcare': 0.8,
            'Financial Services': 1.0,
            'Consumer Discretionary': 1.1,
            'Energy': 0.9,
            'Communication Services': 1.0,
            'Industrials': 0.8,
            'Consumer Staples': 0.7,
            'Materials': 0.8,
            'Real Estate': 0.6,
            'Utilities': 0.5
        }

        volume_multiplier = sector_volume_multipliers.get(sector, 1.0)
        adjusted_avg_volume = int(avg_volume * volume_multiplier)

        # Make tick_volume between 0.5% and 2% of adjusted avg daily volume
        tick_volume = int(adjusted_avg_volume * random.uniform(0.005, 0.02))
        accumulated_volume = int(adjusted_avg_volume * random.uniform(0.1, 0.9))

        # Generate VWAPs
        sector_volatility = baseline.get('volatility', 0.015)
        tick_vwap = round(price * (1 + random.uniform(-sector_volatility/3, sector_volatility/3)), 2)
        vwap = round(baseline.get('volume_weighted_price', price * (1 + random.uniform(-sector_volatility/2, sector_volatility/2))), 2)

        # Timestamps
        end_timestamp = int(current_time.timestamp() * 1000)
        start_timestamp = end_timestamp - 1000

        return cls(
            ticker=ticker,
            price=round(price, 2),
            volume=tick_volume,
            timestamp=current_time.timestamp(),
            source='synthetic',
            event_type='A',
            market_status=market_status,
            bid=round(price * 0.999, 2),
            ask=round(price * 1.001, 2),
            tick_open=round(price * (1 - random.uniform(0, 0.001)), 2),
            tick_high=tick_high,
            tick_low=tick_low,
            tick_close=round(price, 2),
            day_high=baseline.get('day_high', tick_high),
            day_low=baseline.get('day_low', tick_low),
            open_price=round(baseline.get('opening_price', price * 0.99), 2),
            market_open_price=round(baseline.get('opening_price', price * 0.99), 2),
            previous_close=round(baseline.get('prev_close', price * 0.98), 2),
            tick_volume=tick_volume,
            tick_trade_size=baseline.get('avg_trade_size', 500),
            accumulated_volume=accumulated_volume,
            tick_vwap=tick_vwap,
            vwap=vwap,
            tick_start_timestamp=start_timestamp / 1000.0,
            tick_end_timestamp=end_timestamp / 1000.0
        )
