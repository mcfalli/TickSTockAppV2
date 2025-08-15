# classes/transport/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.core.domain.events.base import BaseEvent
import time
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent

@dataclass
class EventCounts:
    """Track event counts by type"""
    highs: int = 0
    lows: int = 0
    trends: int = 0
    surges: int = 0
    
    '''
    def increment(self, event_type: str):
        """Increment count for event type"""
        if event_type in ['high', 'session_high']:
            self.highs += 1
        elif event_type in ['low', 'session_low']:
            self.lows += 1
        elif event_type == 'trend':
            self.trends += 1
        elif event_type == 'surge':
            self.surges += 1
    '''

    def to_dict(self) -> Dict[str, int]:
        return {
            'highs': self.highs,
            'lows': self.lows,
            'trends': self.trends,
            'surges': self.surges
        }

@dataclass
class HighLowBar:
    """High/Low percentage bar calculations"""
    high_count: int = 0
    low_count: int = 0
    
    '''
    @property
    def total(self) -> int:
        return self.high_count + self.low_count
        
    @property
    def high_percentage(self) -> float:
        return (self.high_count / self.total * 100) if self.total > 0 else 50.0
        
    @property
    def low_percentage(self) -> float:
        return (self.low_count / self.total * 100) if self.total > 0 else 50.0
    '''
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'high_count': self.high_count,
            'low_count': self.low_count,
            'high_percentage': self.high_percentage,
            'low_percentage': self.low_percentage
        }

@dataclass
class StockData:
    """
    Main data structure for stock information.
    PHASE 4: Pure typed implementation without dict compatibility.
    Sprint 21B: Trends/surges no longer stored, they flow through event queue.
    """
    # Stock identification
    ticker: str
    last_price: float = 0.0
    last_update: float = field(default_factory=lambda: time.time())
    
    # Event collections - only store high/low events
    highs: List[HighLowEvent] = field(default_factory=list)
    lows: List[HighLowEvent] = field(default_factory=list)
    
    # DEPRECATED: Keep empty for backward compatibility
    trends: List[TrendEvent] = field(default_factory=list)  # DO NOT USE - events flow through queue
    surges: List[SurgeEvent] = field(default_factory=list)  # DO NOT USE - events flow through queue
    
    # Combined events list - only high/low events stored
    events: List[BaseEvent] = field(default_factory=list)
    
    # Statistics
    event_counts: EventCounts = field(default_factory=EventCounts)
    highlow_bar: HighLowBar = field(default_factory=HighLowBar)
    
    # Additional metrics
    vwap: Optional[float] = None
    volume: float = 0
    rel_volume: float = 0.0
    momentum: float = 0.0
    volatility: float = 0.0
    
    # Market status
    market_status: str = 'REGULAR'
    session_high: Optional[float] = None
    session_low: Optional[float] = None
    
    # Trend tracking fields (for current state, not storage)
    trend_direction: str = '→'  # '↑', '↓', '→'
    trend_strength: str = 'neutral'  # 'weak', 'moderate', 'strong', 'extreme'
    trend_score: float = 0.0
    trend_count: int = 0
    trend_count_up: int = 0
    trend_count_down: int = 0
    
    # Surge tracking fields (for current state, not storage)
    surge_active: bool = False
    surge_last_magnitude: float = 0.0
    surge_last_direction: str = '→'
    surge_count: int = 0
    surge_count_up: int = 0
    surge_count_down: int = 0
    
    # Additional fields for compatibility
    high_count: int = 0
    low_count: int = 0
    percent_change: float = 0.0
    vwap_divergence: float = 0.0
    vwap_position: str = 'unknown'  # 'above', 'below', 'at'
    
    # Price history for trend/surge detection
    price_history: List[Dict[str, Any]] = field(default_factory=list)
    surge_data: Optional[Dict[str, Any]] = None
    
    # Market open price for percent change calculations
    market_open_price: Optional[float] = None
    
    def add_event(self, event: BaseEvent):
        """
        Add typed event to appropriate collection.
        Sprint 21B: Only high/low events are stored. Trends/surges update tracking fields only.
        """
        if isinstance(event, HighLowEvent):
            # Store high/low events
            if event.type in ['high', 'session_high']:
                self.highs.append(event)
                self.events.append(event)
                self.highlow_bar.high_count += 1
                self.high_count += 1
                self.event_counts.highs += 1
            elif event.type in ['low', 'session_low']:
                self.lows.append(event)
                self.events.append(event)
                self.highlow_bar.low_count += 1
                self.low_count += 1
                self.event_counts.lows += 1
                
        elif isinstance(event, TrendEvent):
            # DON'T STORE - just update tracking fields
            self.trend_direction = event.direction
            self.trend_strength = event.trend_strength
            self.trend_score = event.trend_score
            self.trend_count = event.count
            self.trend_count_up = event.count_up
            self.trend_count_down = event.count_down
            self.event_counts.trends += 1
            
        elif isinstance(event, SurgeEvent):
            # DON'T STORE - just update tracking fields
            self.surge_active = True
            self.surge_last_magnitude = event.surge_magnitude
            self.surge_last_direction = event.direction
            self.surge_count = event.count
            self.surge_count_up = event.count_up
            self.surge_count_down = event.count_down
            self.event_counts.surges += 1
            
        # Always update price and time
        self.last_price = event.price
        self.last_update = event.time
        
        # Update percent change if we have market open price
        if self.market_open_price and self.market_open_price > 0:
            self.percent_change = ((event.price - self.market_open_price) / self.market_open_price) * 100
            
        # Update VWAP divergence
        if event.vwap and event.vwap > 0:
            self.vwap = event.vwap
            self.vwap_divergence = event.vwap_divergence
            self.vwap_position = 'above' if event.price > event.vwap else 'below'

    '''            
    def get_filtered_events(self, event_type: Optional[str] = None,
                          min_strength: Optional[str] = None) -> List[BaseEvent]:
        """
        Get filtered events with type safety.
        Sprint 21B: Only returns high/low events from storage.
        """
        events = []
        
        # Only high/low events are stored
        if event_type in [None, 'high', 'low']:
            events.extend(self.highs)
            events.extend(self.lows)
            
        # Trends and surges are no longer stored
        if event_type in ['trend', 'surge']:
            logger.debug(f"Trend/surge events requested but not stored - they flow through queue")
                
        return sorted(events, key=lambda e: e.time, reverse=True)
    '''
    def to_transport_dict(self) -> Dict[str, Any]:
        """Convert to S18/19/20 compliant transport structure"""
        return {
            'ticker': self.ticker,
            'last_price': self.last_price,
            'last_update': self.last_update,
            'highs': [h.to_transport_dict() for h in self.highs[-10:]],  # Last 10
            'lows': [l.to_transport_dict() for l in self.lows[-10:]],
            'event_counts': self.event_counts.to_dict(),
            'highlow_bar': self.highlow_bar.to_dict(),
            'vwap': self.vwap,
            'volume': self.volume,
            'rel_volume': self.rel_volume,
            'momentum': self.momentum,
            'volatility': self.volatility,
            'market_status': self.market_status,
            'session_high': self.session_high,
            'session_low': self.session_low,
            'percent_change': self.percent_change,
            'vwap_divergence': self.vwap_divergence,
            'vwap_position': self.vwap_position,
            # Trend state (not events)
            'trend_direction': self.trend_direction,
            'trend_strength': self.trend_strength,
            'trend_score': self.trend_score,
            'trend_count': self.trend_count,
            'trend_count_up': self.trend_count_up,
            'trend_count_down': self.trend_count_down,
            # Surge state (not events)
            'surge_active': self.surge_active,
            'surge_last_magnitude': self.surge_last_magnitude,
            'surge_last_direction': self.surge_last_direction,
            'surge_count': self.surge_count,
            'surge_count_up': self.surge_count_up,
            'surge_count_down': self.surge_count_down
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for external boundaries (WebSocket, etc)"""
        return self.to_transport_dict()

    '''    
    def clear_old_events(self, max_age_seconds: float = 3600):
        """Remove events older than max_age - only affects high/low events"""
        current_time = time.time()
        cutoff_time = current_time - max_age_seconds
        
        # Only clear high/low events (trends/surges not stored)
        self.highs = [h for h in self.highs if h.time > cutoff_time]
        self.lows = [l for l in self.lows if l.time > cutoff_time]
        self.events = [e for e in self.events if e.time > cutoff_time]
    '''

    '''    
    def get_current_state_summary(self) -> Dict[str, Any]:
        """Get current state summary for diagnostics"""
        return {
            'ticker': self.ticker,
            'last_price': self.last_price,
            'last_update': self.last_update,
            'stored_highs': len(self.highs),
            'stored_lows': len(self.lows),
            'trend_state': {
                'direction': self.trend_direction,
                'strength': self.trend_strength,
                'score': self.trend_score,
                'total_count': self.trend_count
            },
            'surge_state': {
                'active': self.surge_active,
                'last_magnitude': self.surge_last_magnitude,
                'total_count': self.surge_count
            },
            'event_totals': self.event_counts.to_dict()
        }
    '''
    
# PHASE 4: Dict compatibility methods removed - use direct attribute access

@dataclass
class GaugeAnalytics:
    """Current V1 gauge analytics structure"""
    ema_net_score: float = 0.0
    current_net_score: float = 0.0
    alpha_used: float = 0.0
    sample_count: int = 0
    last_updated: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ema_net_score': self.ema_net_score,
            'current_net_score': self.current_net_score,
            'alpha_used': self.alpha_used,
            'sample_count': self.sample_count,
            'last_updated': self.last_updated
        }

@dataclass
class VerticalAnalytics:
    """Current V1 vertical analytics structure"""
    ema_net_score: float = 0.0
    current_weighted_score: float = 0.0
    weighted_alpha: float = 0.0
    volume_weight: float = 0.0
    max_activity_seen: float = 0.0
    last_updated: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ema_net_score': self.ema_net_score,
            'current_weighted_score': self.current_weighted_score,
            'weighted_alpha': self.weighted_alpha,
            'volume_weight': self.volume_weight,
            'max_activity_seen': self.max_activity_seen,
            'last_updated': self.last_updated
        }

@dataclass
class SimpleAverages:
    """Current V1 simple averages structure"""
    avg_net_score_10sec: float = 0.0
    avg_net_score_60sec: float = 0.0
    avg_net_score_300sec: float = 0.0
    avg_activity_60sec: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'avg_net_score_10sec': self.avg_net_score_10sec,
            'avg_net_score_60sec': self.avg_net_score_60sec,
            'avg_net_score_300sec': self.avg_net_score_300sec,
            'avg_activity_60sec': self.avg_activity_60sec
        }

@dataclass
class CurrentState:
    """Current V1 state structure"""
    net_score: float = 0.0
    activity_level: str = "low"
    buying_count: int = 0
    selling_count: int = 0
    activity_count: int = 0
    universe_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'net_score': self.net_score,
            'activity_level': self.activity_level,
            'buying_count': self.buying_count,
            'selling_count': self.selling_count,
            'activity_count': self.activity_count,
            'universe_size': self.universe_size
        }

@dataclass
class AggregationInfo:
    """Current V1 aggregation info structure"""
    aggregation_interval_seconds: int = 0
    records_aggregated: int = 0
    session_calculation_count: int = 0
    database_sync_active: bool = False
    last_database_sync: Optional[str] = None
    last_update: Optional[str] = None  # Used in user_universe
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'aggregation_interval_seconds': self.aggregation_interval_seconds,
            'records_aggregated': self.records_aggregated,
            'session_calculation_count': self.session_calculation_count,
            'database_sync_active': self.database_sync_active
        }
        
        # Include the appropriate last update field
        if self.last_database_sync is not None:
            result['last_database_sync'] = self.last_database_sync
        if self.last_update is not None:
            result['last_update'] = self.last_update
            
        return result

@dataclass
class UniverseAnalytics:
    """
    Current V1 universe analytics structure.
    This is what's actually being emitted now.
    """
    gauge_analytics: GaugeAnalytics = field(default_factory=GaugeAnalytics)
    vertical_analytics: VerticalAnalytics = field(default_factory=VerticalAnalytics)
    simple_averages: SimpleAverages = field(default_factory=SimpleAverages)
    current_state: CurrentState = field(default_factory=CurrentState)
    aggregation_info: AggregationInfo = field(default_factory=AggregationInfo)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'gauge_analytics': self.gauge_analytics.to_dict(),
            'vertical_analytics': self.vertical_analytics.to_dict(),
            'simple_averages': self.simple_averages.to_dict(),
            'current_state': self.current_state.to_dict(),
            'aggregation_info': self.aggregation_info.to_dict()
        }

@dataclass
class MarketAnalyticsV1:
    """
    Complete V1 market analytics emission structure.
    Contains both core and user universe analytics.
    """
    core_universe_analytics: UniverseAnalytics = field(default_factory=UniverseAnalytics)
    user_universe_analytics: UniverseAnalytics = field(default_factory=UniverseAnalytics)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'core_universe_analytics': self.core_universe_analytics.to_dict(),
            'user_universe_analytics': self.user_universe_analytics.to_dict()
        }
    
@dataclass
class MarketCounts:
    """Market-wide event counts"""
    highs: int = 0
    lows: int = 0
    total_highs: int = 0
    total_lows: int = 0
    session_total_highs: int = 0
    session_total_lows: int = 0
    session_total_events: int = 0
    session_active_tickers: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'highs': self.highs,
            'lows': self.lows,
            'total_highs': self.total_highs,
            'total_lows': self.total_lows,
            'session_total_highs': self.session_total_highs,
            'session_total_lows': self.session_total_lows,
            'session_total_events': self.session_total_events,
            'session_active_tickers': self.session_active_tickers
        }

@dataclass
class ActivityWindow:
    """Activity metrics for a time window"""
    count: int = 0
    events_per_second: float = 0.0
    level: Optional[str] = None  # Not used in 1s window
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'count': self.count,
            'events_per_second': self.events_per_second
        }
        if self.level is not None:
            result['level'] = self.level
        return result

@dataclass
class ActivityMetrics:
    """Activity metrics across different time windows"""
    one_s_activity: ActivityWindow = field(default_factory=ActivityWindow)
    ten_s_activity: ActivityWindow = field(default_factory=ActivityWindow)
    thirty_s_activity: ActivityWindow = field(default_factory=ActivityWindow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'one_s_activity': self.one_s_activity.to_dict(),
            'ten_s_activity': self.ten_s_activity.to_dict(),
            'thirty_s_activity': self.thirty_s_activity.to_dict()
        }

@dataclass
class BuySellMetrics:
    """Buy/sell metrics (deprecated but still in use)"""
    net_score: float = 0.0
    buying_count: int = 0
    selling_count: int = 0
    activity_count: int = 0
    activity_level: str = "low"
    calc_time: float = 0.0
    _deprecated: bool = True
    _replacement: str = "Use universe_analytics instead"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'net_score': self.net_score,
            'buying_count': self.buying_count,
            'selling_count': self.selling_count,
            'activity_count': self.activity_count,
            'activity_level': self.activity_level,
            'calc_time': self.calc_time,
            '_deprecated': self._deprecated,
            '_replacement': self._replacement
        }

@dataclass
class MemoryEfficiency:
    """Memory efficiency metrics"""
    dirty_tickers: int = 0
    last_sync_ago: float = 0.0
    sync_needed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'dirty_tickers': self.dirty_tickers,
            'last_sync_ago': self.last_sync_ago,
            'sync_needed': self.sync_needed
        }

@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    system_health: str = "healthy"
    avg_operation_time_ms: float = 0.0
    operations_per_second: float = 0.0
    total_events_tracked: int = 0
    sync_success_rate: float = 1.0
    memory_efficiency: MemoryEfficiency = field(default_factory=MemoryEfficiency)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'system_health': self.system_health,
            'avg_operation_time_ms': self.avg_operation_time_ms,
            'operations_per_second': self.operations_per_second,
            'total_events_tracked': self.total_events_tracked,
            'sync_success_rate': self.sync_success_rate,
            'memory_efficiency': self.memory_efficiency.to_dict()
        }

@dataclass
class SyncStatus:
    """Database sync status"""
    should_sync: bool = False
    last_sync_ago: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'should_sync': self.should_sync,
            'last_sync_ago': self.last_sync_ago
        }

@dataclass
class SessionAccumulation:
    """Session accumulation and performance data"""
    session_date: str = ""
    universe_size: int = 0
    last_updated: float = 0.0
    data_source: str = ""
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    sync_status: SyncStatus = field(default_factory=SyncStatus)
    zero_flask_context_errors: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_date': self.session_date,
            'universe_size': self.universe_size,
            'last_updated': self.last_updated,
            'data_source': self.data_source,
            'performance_metrics': self.performance_metrics.to_dict(),
            'sync_status': self.sync_status.to_dict(),
            'zero_flask_context_errors': self.zero_flask_context_errors
        }