# classes/analytics/models.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

@dataclass
class TickerAnalytics:
    """Analytics for a single ticker"""
    ticker: str
    
    # Price metrics
    price_change_percent: float = 0.0
    price_volatility: float = 0.0
    
    # Volume metrics
    volume_ratio: float = 0.0
    volume_surge_detected: bool = False
    
    # Trend metrics
    trend_strength: str = 'neutral'  # 'strong_up', 'up', 'neutral', 'down', 'strong_down'
    trend_consistency: float = 0.0
    
    # Event metrics
    event_rate: float = 0.0  # Events per minute
    high_low_ratio: float = 0.5
    
    # Technical indicators
    rsi: Optional[float] = None
    macd_signal: Optional[str] = None
    
    # Momentum
    momentum_score: float = 0.0
    momentum_rank: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'price_change_percent': round(self.price_change_percent, 2),
            'volume_ratio': round(self.volume_ratio, 2),
            'trend_strength': self.trend_strength,
            'momentum_score': round(self.momentum_score, 2),
            'momentum_rank': self.momentum_rank,
            'event_rate': round(self.event_rate, 2),
            'high_low_ratio': round(self.high_low_ratio, 2)
        }

@dataclass
class UniverseAnalytics:
    """Analytics for the entire ticker universe"""
    
    # Universe size
    total_tickers: int = 0
    active_tickers: int = 0
    
    # Top movers
    top_gainers: List[Dict] = field(default_factory=list)
    top_losers: List[Dict] = field(default_factory=list)
    most_active: List[Dict] = field(default_factory=list)
    
    # Momentum leaders
    momentum_leaders: List[Dict] = field(default_factory=list)
    momentum_laggards: List[Dict] = field(default_factory=list)
    
    # Trend summary
    trending_up_count: int = 0
    trending_down_count: int = 0
    neutral_count: int = 0
    
    # Event statistics
    total_events_per_minute: float = 0.0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    
    # Market breadth
    advance_decline_ratio: float = 0.0
    high_low_ratio: float = 0.0
    
    # Volatility metrics
    avg_volatility: float = 0.0
    volatility_spike_count: int = 0
    
    # Update timestamp
    last_update: float = field(default_factory=time.time)
    
    '''
    def add_ticker_analytics(self, analytics: TickerAnalytics):
        """Incorporate single ticker analytics into universe"""
        self.active_tickers += 1
        
        # Update trend counts
        if 'up' in analytics.trend_strength:
            self.trending_up_count += 1
        elif 'down' in analytics.trend_strength:
            self.trending_down_count += 1
        else:
            self.neutral_count += 1
        
    def calculate_market_breadth(self):
        """Calculate market breadth indicators"""
        if self.trending_down_count > 0:
            self.advance_decline_ratio = self.trending_up_count / self.trending_down_count
        else:
            self.advance_decline_ratio = float('inf') if self.trending_up_count > 0 else 1.0
    '''        
    def to_dict(self) -> Dict:
        """Export analytics as dictionary"""
        return {
            'total_tickers': self.total_tickers,
            'active_tickers': self.active_tickers,
            'top_gainers': self.top_gainers[:5],
            'top_losers': self.top_losers[:5],
            'most_active': self.most_active[:5],
            'momentum_leaders': self.momentum_leaders[:5],
            'trend_summary': {
                'up': self.trending_up_count,
                'down': self.trending_down_count,
                'neutral': self.neutral_count
            },
            'market_breadth': {
                'advance_decline_ratio': round(self.advance_decline_ratio, 2),
                'high_low_ratio': round(self.high_low_ratio, 2)
            },
            'events_per_minute': round(self.total_events_per_minute, 1),
            'last_update': self.last_update
        }

@dataclass
class GaugeAnalytics:
    """Analytics for gauge visualization"""
    
    # Momentum gauge
    momentum_value: float = 0.0  # -100 to 100
    momentum_label: str = "Neutral"
    momentum_color: str = "#gray"
    
    # Volatility gauge  
    volatility_value: float = 0.0  # 0 to 100
    volatility_label: str = "Low"
    volatility_color: str = "#green"
    
    # Volume gauge
    volume_value: float = 0.0  # 0 to 100
    volume_label: str = "Normal"
    volume_color: str = "#blue"
    
    # Trend gauge
    trend_value: float = 0.0  # -100 to 100
    trend_label: str = "Neutral"
    trend_color: str = "#gray"
    
    def to_dict(self) -> Dict:
        return {
            'momentum': {
                'value': round(self.momentum_value, 1),
                'label': self.momentum_label,
                'color': self.momentum_color
            },
            'volatility': {
                'value': round(self.volatility_value, 1),
                'label': self.volatility_label,
                'color': self.volatility_color
            },
            'volume': {
                'value': round(self.volume_value, 1),
                'label': self.volume_label,
                'color': self.volume_color
            },
            'trend': {
                'value': round(self.trend_value, 1),
                'label': self.trend_label,
                'color': self.trend_color
            }
        }