"""
Tier-Specific Event Models
Data structures for Sprint 25 tier-specific pattern events and market insights.

Sprint 25 Phase 1: Tier-Specific Event Handling
- Daily, Intraday, and Combo pattern event models
- Market regime and ETF state event structures
- WebSocket-ready event serialization
- Consumer-focused event processing (no pattern detection logic)
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PatternTier(Enum):
    """Pattern detection tiers from TickStockPL."""
    DAILY = "daily"
    INTRADAY = "intraday"
    COMBO = "combo"

class MarketRegime(Enum):
    """Market regime states for ETF-based market analysis."""
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    CONSOLIDATION = "consolidation"

class EventPriority(Enum):
    """Event priority levels for user notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TierPatternEvent:
    """
    Tier-specific pattern event from TickStockPL.
    
    Consumer event model for pattern alerts with tier categorization.
    Consumed from Redis pub-sub, never generated locally.
    """

    # Core pattern data
    pattern_type: str                    # 'BreakoutBO', 'TrendReversal', etc.
    symbol: str                         # Stock symbol
    tier: PatternTier                   # Daily/Intraday/Combo classification
    confidence: float                   # Pattern confidence (0.0 to 1.0)

    # Event metadata
    event_id: str                       # Unique event identifier
    timestamp: datetime                 # When pattern was detected
    source: str = "TickStockPL"        # Always from TickStockPL

    # Pattern details
    pattern_data: dict[str, Any] = field(default_factory=dict)  # Pattern-specific data
    market_context: dict[str, Any] = field(default_factory=dict) # Market conditions

    # Event classification
    priority: EventPriority = EventPriority.MEDIUM
    tags: list[str] = field(default_factory=list)  # Additional categorization

    def to_websocket_dict(self) -> dict[str, Any]:
        """Convert event to WebSocket-friendly format."""
        return {
            'event_id': self.event_id,
            'pattern_type': self.pattern_type,
            'symbol': self.symbol,
            'tier': self.tier.value,
            'confidence': round(self.confidence, 3),
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'pattern_data': self.pattern_data,
            'market_context': self.market_context,
            'priority': self.priority.value,
            'tags': self.tags
        }

    def matches_user_filters(self, user_filters: dict[str, Any]) -> bool:
        """Check if event matches user subscription filters."""
        try:
            # Pattern type filter
            if 'pattern_types' in user_filters:
                if self.pattern_type not in user_filters['pattern_types']:
                    return False

            # Symbol filter
            if 'symbols' in user_filters:
                if self.symbol not in user_filters['symbols']:
                    return False

            # Tier filter
            if 'tiers' in user_filters:
                tier_values = [t.value if hasattr(t, 'value') else str(t) for t in user_filters['tiers']]
                if self.tier.value not in tier_values:
                    return False

            # Confidence threshold
            if 'confidence_min' in user_filters:
                if self.confidence < user_filters['confidence_min']:
                    return False

            # Priority filter
            if 'priority_min' in user_filters:
                priority_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
                min_priority = priority_order.get(user_filters['priority_min'], 1)
                event_priority = priority_order.get(self.priority.value, 1)
                if event_priority < min_priority:
                    return False

            return True

        except Exception:
            return False

    @classmethod
    def from_redis_event(cls, redis_data: dict[str, Any]) -> 'TierPatternEvent':
        """Create TierPatternEvent from Redis pub-sub message."""
        try:
            # Extract core pattern data
            pattern_type = redis_data.get('pattern', redis_data.get('pattern_type', 'Unknown'))
            symbol = redis_data.get('symbol', 'UNKNOWN')

            # Parse tier information
            tier_str = redis_data.get('tier', 'daily').lower()
            tier = PatternTier(tier_str) if tier_str in [t.value for t in PatternTier] else PatternTier.DAILY

            confidence = float(redis_data.get('confidence', 0.0))

            # Generate event ID if not provided
            event_id = redis_data.get('event_id', f"{symbol}_{pattern_type}_{int(time.time())}")

            # Parse timestamp
            timestamp_val = redis_data.get('timestamp', time.time())
            if isinstance(timestamp_val, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp_val)
            else:
                timestamp = datetime.now()

            # Determine priority based on confidence and tier
            if confidence >= 0.9:
                priority = EventPriority.CRITICAL
            elif confidence >= 0.8:
                priority = EventPriority.HIGH
            elif confidence >= 0.6:
                priority = EventPriority.MEDIUM
            else:
                priority = EventPriority.LOW

            # Extract pattern-specific data
            pattern_data = {k: v for k, v in redis_data.items()
                          if k not in ['pattern', 'pattern_type', 'symbol', 'tier', 'confidence', 'timestamp', 'event_id']}

            # Generate tags based on pattern characteristics
            tags = []
            if confidence >= 0.8:
                tags.append('high_confidence')
            if tier == PatternTier.COMBO:
                tags.append('multi_timeframe')

            return cls(
                pattern_type=pattern_type,
                symbol=symbol,
                tier=tier,
                confidence=confidence,
                event_id=event_id,
                timestamp=timestamp,
                pattern_data=pattern_data,
                priority=priority,
                tags=tags
            )

        except Exception:
            # Return minimal event on parsing error
            return cls(
                pattern_type=redis_data.get('pattern', 'ParseError'),
                symbol=redis_data.get('symbol', 'ERROR'),
                tier=PatternTier.DAILY,
                confidence=0.0,
                event_id=f"error_{int(time.time())}",
                timestamp=datetime.now()
            )

@dataclass
class MarketStateEvent:
    """
    Market state change event for ETF-based market insights.
    
    Consumer event model for market regime changes and ETF performance updates.
    """

    # Market state data
    regime: MarketRegime               # Current market regime
    regime_confidence: float           # Confidence in regime classification

    # ETF performance data
    etf_performance: dict[str, float]  # ETF -> performance percentage
    sector_strength: dict[str, float]  # Sector -> relative strength

    # Event metadata
    event_id: str
    timestamp: datetime
    source: str = "TickStockPL"

    # Market indicators
    risk_on_score: float = 0.0        # Risk-on/Risk-off indicator (-1 to 1)
    volatility_regime: str = "normal"  # 'low', 'normal', 'high'
    market_breadth: dict[str, Any] = field(default_factory=dict)

    def to_websocket_dict(self) -> dict[str, Any]:
        """Convert market state to WebSocket format."""
        return {
            'event_id': self.event_id,
            'regime': self.regime.value,
            'regime_confidence': round(self.regime_confidence, 3),
            'etf_performance': {k: round(v, 2) for k, v in self.etf_performance.items()},
            'sector_strength': {k: round(v, 2) for k, v in self.sector_strength.items()},
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'risk_on_score': round(self.risk_on_score, 2),
            'volatility_regime': self.volatility_regime,
            'market_breadth': self.market_breadth
        }

    def get_market_summary(self) -> dict[str, Any]:
        """Get human-readable market summary."""
        # Determine market sentiment
        if self.regime == MarketRegime.BULL:
            sentiment = "Bullish"
        elif self.regime == MarketRegime.BEAR:
            sentiment = "Bearish"
        elif self.regime == MarketRegime.NEUTRAL:
            sentiment = "Neutral"
        else:
            sentiment = "Consolidating"

        # Risk assessment
        if self.risk_on_score > 0.3:
            risk_sentiment = "Risk-On"
        elif self.risk_on_score < -0.3:
            risk_sentiment = "Risk-Off"
        else:
            risk_sentiment = "Balanced"

        # Top performing ETF
        best_etf = max(self.etf_performance.items(), key=lambda x: x[1]) if self.etf_performance else ("N/A", 0)

        return {
            'sentiment': sentiment,
            'confidence': f"{self.regime_confidence:.1%}",
            'risk_sentiment': risk_sentiment,
            'volatility': self.volatility_regime.title(),
            'best_performer': f"{best_etf[0]} ({best_etf[1]:+.1%})",
            'summary': f"{sentiment} market with {risk_sentiment} sentiment"
        }

@dataclass
class PatternAlertEvent:
    """
    User-specific pattern alert event for notification delivery.
    
    Generated when a TierPatternEvent matches user subscription criteria.
    """

    # Alert metadata
    alert_id: str
    user_id: str
    timestamp: datetime

    # Source pattern event
    pattern_event: TierPatternEvent

    # Alert configuration
    alert_type: str = "pattern_match"      # Type of alert
    delivery_channels: list[str] = field(default_factory=lambda: ["websocket"])  # websocket, email, etc.

    # User context
    user_filters: dict[str, Any] = field(default_factory=dict)  # Filters that matched
    alert_priority: EventPriority = EventPriority.MEDIUM

    def to_websocket_dict(self) -> dict[str, Any]:
        """Convert alert to WebSocket format."""
        return {
            'alert_id': self.alert_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'alert_type': self.alert_type,
            'priority': self.alert_priority.value,
            'pattern_event': self.pattern_event.to_websocket_dict(),
            'delivery_channels': self.delivery_channels,
            'matched_filters': list(self.user_filters.keys())
        }

@dataclass
class SystemHealthEvent:
    """
    System health and performance event for monitoring dashboards.
    """

    # Event metadata (required fields first)
    event_id: str
    timestamp: datetime
    service_name: str
    status: str                        # 'healthy', 'warning', 'error'
    status_message: str
    performance_metrics: dict[str, float]

    # Optional fields with defaults
    error_counts: dict[str, int] = field(default_factory=dict)
    source: str = "TickStockAppV2"

    def to_websocket_dict(self) -> dict[str, Any]:
        """Convert health event to WebSocket format."""
        return {
            'event_id': self.event_id,
            'service_name': self.service_name,
            'status': self.status,
            'status_message': self.status_message,
            'performance_metrics': self.performance_metrics,
            'error_counts': self.error_counts,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source
        }

# Event type registry for WebSocket routing
EVENT_TYPE_REGISTRY = {
    'tier_pattern': TierPatternEvent,
    'market_state': MarketStateEvent,
    'pattern_alert': PatternAlertEvent,
    'system_health': SystemHealthEvent
}

def create_event_from_type(event_type: str, data: dict[str, Any]) -> Any | None:
    """Factory function to create events from WebSocket event types."""
    event_class = EVENT_TYPE_REGISTRY.get(event_type)
    if event_class and hasattr(event_class, 'from_redis_event'):
        try:
            return event_class.from_redis_event(data)
        except Exception:
            return None
    return None
