# classes/market/state.py
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class TickerState:
    """
    Maintains state for a single ticker.
    Replaces various dict-based state tracking.
    """
    ticker: str

    # Price tracking
    current_price: float = 0.0
    previous_price: float = 0.0
    open_price: float | None = None

    # High/Low tracking
    day_high: float = 0.0
    day_low: float = float('inf')
    session_high: float = 0.0
    session_low: float = float('inf')

    # VWAP tracking
    vwap: float = 0.0
    vwap_numerator: float = 0.0
    vwap_denominator: float = 0.0

    # Volume tracking
    total_volume: float = 0
    avg_volume: float = 0
    volume_30s: float = 0

    # Momentum tracking
    momentum_score: float = 0.0
    price_changes: deque[float] = field(default_factory=lambda: deque(maxlen=20))

    # Event counts
    high_count: int = 0
    low_count: int = 0
    trend_count: int = 0
    surge_count: int = 0

    # Timing
    last_update: float = field(default_factory=time.time)
    last_event_time: float | None = None
    session_start: float = field(default_factory=time.time)

    # Market session
    market_session: str = 'REGULAR'  # 'PREMARKET', 'REGULAR', 'AFTERHOURS'

    '''
    def update_price(self, price: float, volume: float = 0):
        """Update price and related calculations"""
        self.previous_price = self.current_price
        self.current_price = price
        self.last_update = time.time()
        
        # Track price change
        if self.previous_price > 0:
            change = price - self.previous_price
            self.price_changes.append(change)
            
        # Update high/low
        if price > self.day_high:
            self.day_high = price
        if price < self.day_low:
            self.day_low = price
            
        if price > self.session_high:
            self.session_high = price
        if price < self.session_low:
            self.session_low = price
            
        # Update volume
        self.total_volume += volume
        
        # Update VWAP
        if volume > 0:
            self.vwap_numerator += price * volume
            self.vwap_denominator += volume
            self.vwap = self.vwap_numerator / self.vwap_denominator if self.vwap_denominator > 0 else price
    def calculate_momentum(self) -> float:
        """Calculate current momentum based on recent price changes"""
        if len(self.price_changes) < 2:
            return 0.0
            
        # Simple momentum: sum of recent changes
        recent_changes = list(self.price_changes)[-10:]
        if not recent_changes:
            return 0.0
            
        momentum = sum(recent_changes)
        
        # Normalize by price
        if self.current_price > 0:
            momentum = (momentum / self.current_price) * 100
            
        self.momentum_score = momentum
        return momentum

    def reset_session(self, session_type: str):
        """Reset session-specific data"""
        self.market_session = session_type
        self.session_high = self.current_price
        self.session_low = self.current_price
        self.session_start = time.time()
        
        # Reset daily data at market open
        if session_type == 'REGULAR':
            self.day_high = self.current_price
            self.day_low = self.current_price
            self.open_price = self.current_price
            self.total_volume = 0
            self.vwap_numerator = 0
            self.vwap_denominator = 0
            
    def get_state_dict(self) -> Dict:
        """Export state as dictionary for storage/transport"""
        return {
            'ticker': self.ticker,
            'current_price': self.current_price,
            'day_high': self.day_high,
            'day_low': self.day_low,
            'session_high': self.session_high,
            'session_low': self.session_low,
            'vwap': self.vwap,
            'total_volume': self.total_volume,
            'momentum_score': self.momentum_score,
            'event_counts': {
                'highs': self.high_count,
                'lows': self.low_count,
                'trends': self.trend_count,
                'surges': self.surge_count
            },
            'market_session': self.market_session,
            'last_update': self.last_update
        }
    '''
