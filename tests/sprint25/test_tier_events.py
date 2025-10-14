"""
Comprehensive unit tests for tier-specific event models.

Sprint 25 Day 1 Implementation Testing:
- TierPatternEvent, MarketStateEvent, PatternAlertEvent models
- WebSocket-ready event serialization
- Consumer-focused event processing (no pattern detection logic)
- Event filtering and user preference matching
"""

import json
from datetime import datetime
from unittest.mock import patch

# Import the components under test
from src.core.domain.events.tier_events import (
    EVENT_TYPE_REGISTRY,
    EventPriority,
    MarketRegime,
    MarketStateEvent,
    PatternAlertEvent,
    PatternTier,
    SystemHealthEvent,
    TierPatternEvent,
    create_event_from_type,
)


class TestPatternTier:
    """Test PatternTier enum functionality."""

    def test_pattern_tier_values(self):
        """Test PatternTier enum values."""
        assert PatternTier.DAILY.value == "daily"
        assert PatternTier.INTRADAY.value == "intraday"
        assert PatternTier.COMBO.value == "combo"

        # Test all enum members
        assert len(PatternTier) == 3
        values = [tier.value for tier in PatternTier]
        assert "daily" in values
        assert "intraday" in values
        assert "combo" in values


class TestMarketRegime:
    """Test MarketRegime enum functionality."""

    def test_market_regime_values(self):
        """Test MarketRegime enum values."""
        assert MarketRegime.BULL.value == "bull"
        assert MarketRegime.BEAR.value == "bear"
        assert MarketRegime.NEUTRAL.value == "neutral"
        assert MarketRegime.CONSOLIDATION.value == "consolidation"

        # Test all enum members
        assert len(MarketRegime) == 4


class TestEventPriority:
    """Test EventPriority enum functionality."""

    def test_event_priority_values(self):
        """Test EventPriority enum values."""
        assert EventPriority.LOW.value == "low"
        assert EventPriority.MEDIUM.value == "medium"
        assert EventPriority.HIGH.value == "high"
        assert EventPriority.CRITICAL.value == "critical"

        # Test all enum members
        assert len(EventPriority) == 4


class TestTierPatternEvent:
    """Comprehensive tests for TierPatternEvent."""

    def test_tier_pattern_event_creation_minimal(self):
        """Test TierPatternEvent creation with minimal parameters."""
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.85,
            event_id="test_event_123",
            timestamp=datetime(2025, 1, 1, 10, 0, 0)
        )

        assert event.pattern_type == "BreakoutBO"
        assert event.symbol == "AAPL"
        assert event.tier == PatternTier.DAILY
        assert event.confidence == 0.85
        assert event.event_id == "test_event_123"
        assert event.timestamp == datetime(2025, 1, 1, 10, 0, 0)
        assert event.source == "TickStockPL"
        assert event.pattern_data == {}
        assert event.market_context == {}
        assert event.priority == EventPriority.MEDIUM
        assert event.tags == []

    def test_tier_pattern_event_creation_full(self):
        """Test TierPatternEvent creation with all parameters."""
        pattern_data = {"breakout_level": 150.0, "volume_surge": 2.5}
        market_context = {"market_regime": "bull", "volatility": "low"}
        tags = ["high_confidence", "volume_breakout"]

        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.INTRADAY,
            confidence=0.92,
            event_id="full_event_456",
            timestamp=datetime(2025, 1, 1, 14, 30, 0),
            source="CustomSource",
            pattern_data=pattern_data,
            market_context=market_context,
            priority=EventPriority.HIGH,
            tags=tags
        )

        assert event.pattern_type == "BreakoutBO"
        assert event.symbol == "AAPL"
        assert event.tier == PatternTier.INTRADAY
        assert event.confidence == 0.92
        assert event.source == "CustomSource"
        assert event.pattern_data == pattern_data
        assert event.market_context == market_context
        assert event.priority == EventPriority.HIGH
        assert event.tags == tags

    def test_to_websocket_dict(self):
        """Test conversion to WebSocket-friendly format."""
        pattern_data = {"breakout_level": 150.0}
        market_context = {"regime": "bull"}

        event = TierPatternEvent(
            pattern_type="TrendReversal",
            symbol="TSLA",
            tier=PatternTier.COMBO,
            confidence=0.78,
            event_id="ws_test_789",
            timestamp=datetime(2025, 1, 1, 16, 45, 30),
            pattern_data=pattern_data,
            market_context=market_context,
            priority=EventPriority.HIGH,
            tags=["reversal", "combo"]
        )

        ws_dict = event.to_websocket_dict()

        # Check all required fields
        assert ws_dict["event_id"] == "ws_test_789"
        assert ws_dict["pattern_type"] == "TrendReversal"
        assert ws_dict["symbol"] == "TSLA"
        assert ws_dict["tier"] == "combo"
        assert ws_dict["confidence"] == 0.780  # Rounded to 3 decimals
        assert ws_dict["timestamp"] == "2025-01-01T16:45:30"
        assert ws_dict["source"] == "TickStockPL"
        assert ws_dict["pattern_data"] == pattern_data
        assert ws_dict["market_context"] == market_context
        assert ws_dict["priority"] == "high"
        assert ws_dict["tags"] == ["reversal", "combo"]

        # Should be JSON serializable
        json_str = json.dumps(ws_dict)
        assert len(json_str) > 0

    def test_matches_user_filters_pattern_types(self):
        """Test pattern type filtering."""
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.8,
            event_id="filter_test",
            timestamp=datetime.now()
        )

        # Should match when pattern type in filter
        assert event.matches_user_filters({
            "pattern_types": ["BreakoutBO", "TrendReversal"]
        }) is True

        # Should not match when pattern type not in filter
        assert event.matches_user_filters({
            "pattern_types": ["TrendReversal", "SurgePattern"]
        }) is False

        # Should match when no pattern type filter (accepts all)
        assert event.matches_user_filters({}) is True

    def test_matches_user_filters_symbols(self):
        """Test symbol filtering."""
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="TSLA",
            tier=PatternTier.DAILY,
            confidence=0.8,
            event_id="symbol_test",
            timestamp=datetime.now()
        )

        # Should match when symbol in filter
        assert event.matches_user_filters({
            "symbols": ["AAPL", "TSLA", "MSFT"]
        }) is True

        # Should not match when symbol not in filter
        assert event.matches_user_filters({
            "symbols": ["AAPL", "GOOGL"]
        }) is False

        # Should match when no symbol filter
        assert event.matches_user_filters({}) is True

    def test_matches_user_filters_tiers(self):
        """Test tier filtering."""
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.INTRADAY,
            confidence=0.8,
            event_id="tier_test",
            timestamp=datetime.now()
        )

        # Should match with string tier values
        assert event.matches_user_filters({
            "tiers": ["daily", "intraday"]
        }) is True

        # Should match with enum tier values
        assert event.matches_user_filters({
            "tiers": [PatternTier.INTRADAY, PatternTier.COMBO]
        }) is True

        # Should not match when tier not in filter
        assert event.matches_user_filters({
            "tiers": ["daily", "combo"]
        }) is False

        # Should match when no tier filter
        assert event.matches_user_filters({}) is True

    def test_matches_user_filters_confidence_threshold(self):
        """Test confidence threshold filtering."""
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.75,
            event_id="confidence_test",
            timestamp=datetime.now()
        )

        # Should match when confidence above threshold
        assert event.matches_user_filters({
            "confidence_min": 0.7
        }) is True

        # Should not match when confidence below threshold
        assert event.matches_user_filters({
            "confidence_min": 0.8
        }) is False

        # Should match when confidence exactly at threshold
        assert event.matches_user_filters({
            "confidence_min": 0.75
        }) is True

    def test_matches_user_filters_priority_minimum(self):
        """Test priority minimum filtering."""
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.8,
            event_id="priority_test",
            timestamp=datetime.now(),
            priority=EventPriority.HIGH
        )

        # Should match when priority meets minimum
        assert event.matches_user_filters({
            "priority_min": "medium"  # HIGH >= MEDIUM
        }) is True

        # Should not match when priority below minimum
        assert event.matches_user_filters({
            "priority_min": "critical"  # HIGH < CRITICAL
        }) is False

        # Should match when priority exactly at minimum
        assert event.matches_user_filters({
            "priority_min": "high"
        }) is True

    def test_matches_user_filters_combined_criteria(self):
        """Test filtering with multiple criteria."""
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.85,
            event_id="combined_test",
            timestamp=datetime.now(),
            priority=EventPriority.HIGH
        )

        # Should match all criteria
        assert event.matches_user_filters({
            "pattern_types": ["BreakoutBO"],
            "symbols": ["AAPL", "TSLA"],
            "tiers": ["daily", "intraday"],
            "confidence_min": 0.8,
            "priority_min": "medium"
        }) is True

        # Should fail if any criteria not met
        assert event.matches_user_filters({
            "pattern_types": ["BreakoutBO"],
            "symbols": ["TSLA"],  # AAPL not in list
            "confidence_min": 0.8,
        }) is False

    def test_matches_user_filters_error_handling(self):
        """Test error handling in filter matching."""
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.8,
            event_id="error_test",
            timestamp=datetime.now()
        )

        # Should return False on any error in filtering
        assert event.matches_user_filters({
            "invalid_filter": object()  # Non-comparable object
        }) is False

    def test_from_redis_event_minimal(self):
        """Test creating event from minimal Redis data."""
        redis_data = {
            "pattern": "BreakoutBO",
            "symbol": "AAPL",
            "confidence": 0.75
        }

        event = TierPatternEvent.from_redis_event(redis_data)

        assert event.pattern_type == "BreakoutBO"
        assert event.symbol == "AAPL"
        assert event.confidence == 0.75
        assert event.tier == PatternTier.DAILY  # Default
        assert event.priority == EventPriority.MEDIUM  # Based on confidence 0.75
        assert event.source == "TickStockPL"
        assert "AAPL_BreakoutBO_" in event.event_id  # Generated ID

    def test_from_redis_event_full(self):
        """Test creating event from complete Redis data."""
        timestamp_val = 1704110400  # 2024-01-01 12:00:00 UTC

        redis_data = {
            "pattern_type": "TrendReversal",
            "symbol": "TSLA",
            "tier": "intraday",
            "confidence": 0.92,
            "event_id": "redis_event_123",
            "timestamp": timestamp_val,
            "breakout_level": 250.0,
            "volume_surge": 1.8,
            "market_regime": "bull"
        }

        event = TierPatternEvent.from_redis_event(redis_data)

        assert event.pattern_type == "TrendReversal"
        assert event.symbol == "TSLA"
        assert event.tier == PatternTier.INTRADAY
        assert event.confidence == 0.92
        assert event.event_id == "redis_event_123"
        assert event.timestamp == datetime.fromtimestamp(timestamp_val)
        assert event.priority == EventPriority.CRITICAL  # Based on confidence 0.92
        assert event.pattern_data["breakout_level"] == 250.0
        assert event.pattern_data["volume_surge"] == 1.8
        assert event.pattern_data["market_regime"] == "bull"
        assert "high_confidence" in event.tags  # Auto-generated tag

    def test_from_redis_event_priority_assignment(self):
        """Test automatic priority assignment based on confidence."""
        # Test CRITICAL priority (>= 0.9)
        event = TierPatternEvent.from_redis_event({
            "pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.95
        })
        assert event.priority == EventPriority.CRITICAL

        # Test HIGH priority (>= 0.8)
        event = TierPatternEvent.from_redis_event({
            "pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.85
        })
        assert event.priority == EventPriority.HIGH

        # Test MEDIUM priority (>= 0.6)
        event = TierPatternEvent.from_redis_event({
            "pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.7
        })
        assert event.priority == EventPriority.MEDIUM

        # Test LOW priority (< 0.6)
        event = TierPatternEvent.from_redis_event({
            "pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.5
        })
        assert event.priority == EventPriority.LOW

    def test_from_redis_event_tag_generation(self):
        """Test automatic tag generation."""
        # High confidence tag
        event = TierPatternEvent.from_redis_event({
            "pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.85, "tier": "daily"
        })
        assert "high_confidence" in event.tags

        # Multi-timeframe tag for combo tier
        event = TierPatternEvent.from_redis_event({
            "pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.7, "tier": "combo"
        })
        assert "multi_timeframe" in event.tags

    def test_from_redis_event_invalid_tier(self):
        """Test handling of invalid tier values."""
        event = TierPatternEvent.from_redis_event({
            "pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.8, "tier": "invalid_tier"
        })

        assert event.tier == PatternTier.DAILY  # Should default to DAILY

    def test_from_redis_event_error_handling(self):
        """Test error handling during Redis event parsing."""
        # Test with invalid/missing data
        invalid_data = {
            "invalid": "data",
            "confidence": "not_a_number"  # Invalid confidence
        }

        event = TierPatternEvent.from_redis_event(invalid_data)

        # Should create minimal error event
        assert event.pattern_type == "ParseError"
        assert event.symbol == "ERROR"
        assert event.tier == PatternTier.DAILY
        assert event.confidence == 0.0
        assert "error_" in event.event_id


class TestMarketStateEvent:
    """Comprehensive tests for MarketStateEvent."""

    def test_market_state_event_creation(self):
        """Test MarketStateEvent creation."""
        etf_performance = {"SPY": 0.02, "QQQ": -0.01, "IWM": 0.005}
        sector_strength = {"Technology": 0.03, "Healthcare": -0.005}
        market_breadth = {"advancing": 1500, "declining": 1000}

        event = MarketStateEvent(
            regime=MarketRegime.BULL,
            regime_confidence=0.85,
            etf_performance=etf_performance,
            sector_strength=sector_strength,
            event_id="market_test_123",
            timestamp=datetime(2025, 1, 1, 9, 30, 0),
            risk_on_score=0.6,
            volatility_regime="low",
            market_breadth=market_breadth
        )

        assert event.regime == MarketRegime.BULL
        assert event.regime_confidence == 0.85
        assert event.etf_performance == etf_performance
        assert event.sector_strength == sector_strength
        assert event.event_id == "market_test_123"
        assert event.source == "TickStockPL"
        assert event.risk_on_score == 0.6
        assert event.volatility_regime == "low"
        assert event.market_breadth == market_breadth

    def test_to_websocket_dict(self):
        """Test MarketStateEvent WebSocket conversion."""
        event = MarketStateEvent(
            regime=MarketRegime.BEAR,
            regime_confidence=0.78,
            etf_performance={"SPY": -0.015, "QQQ": -0.025},
            sector_strength={"Technology": -0.02},
            event_id="ws_market_456",
            timestamp=datetime(2025, 1, 1, 15, 45, 0),
            risk_on_score=-0.4,
            volatility_regime="high"
        )

        ws_dict = event.to_websocket_dict()

        assert ws_dict["event_id"] == "ws_market_456"
        assert ws_dict["regime"] == "bear"
        assert ws_dict["regime_confidence"] == 0.780  # Rounded
        assert ws_dict["etf_performance"]["SPY"] == -0.01  # Rounded to 2 decimals
        assert ws_dict["etf_performance"]["QQQ"] == -0.03  # Rounded to 2 decimals
        assert ws_dict["sector_strength"]["Technology"] == -0.02
        assert ws_dict["timestamp"] == "2025-01-01T15:45:00"
        assert ws_dict["source"] == "TickStockPL"
        assert ws_dict["risk_on_score"] == -0.40
        assert ws_dict["volatility_regime"] == "high"

        # Should be JSON serializable
        json_str = json.dumps(ws_dict)
        assert len(json_str) > 0

    def test_get_market_summary_bull(self):
        """Test market summary for bull market."""
        event = MarketStateEvent(
            regime=MarketRegime.BULL,
            regime_confidence=0.85,
            etf_performance={"SPY": 0.025, "QQQ": 0.03, "IWM": 0.01},
            sector_strength={},
            event_id="bull_test",
            timestamp=datetime.now(),
            risk_on_score=0.5,
            volatility_regime="normal"
        )

        summary = event.get_market_summary()

        assert summary["sentiment"] == "Bullish"
        assert summary["confidence"] == "85.0%"
        assert summary["risk_sentiment"] == "Risk-On"
        assert summary["volatility"] == "Normal"
        assert summary["best_performer"] == "QQQ (+3.0%)"
        assert "Bullish market with Risk-On sentiment" in summary["summary"]

    def test_get_market_summary_bear(self):
        """Test market summary for bear market."""
        event = MarketStateEvent(
            regime=MarketRegime.BEAR,
            regime_confidence=0.72,
            etf_performance={"SPY": -0.02, "QQQ": -0.015},
            sector_strength={},
            event_id="bear_test",
            timestamp=datetime.now(),
            risk_on_score=-0.5,
            volatility_regime="high"
        )

        summary = event.get_market_summary()

        assert summary["sentiment"] == "Bearish"
        assert summary["confidence"] == "72.0%"
        assert summary["risk_sentiment"] == "Risk-Off"
        assert summary["volatility"] == "High"
        assert summary["best_performer"] == "QQQ (-1.5%)"  # Least negative
        assert "Bearish market with Risk-Off sentiment" in summary["summary"]

    def test_get_market_summary_neutral(self):
        """Test market summary for neutral market."""
        event = MarketStateEvent(
            regime=MarketRegime.NEUTRAL,
            regime_confidence=0.65,
            etf_performance={"SPY": 0.005},
            sector_strength={},
            event_id="neutral_test",
            timestamp=datetime.now(),
            risk_on_score=0.1,
            volatility_regime="normal"
        )

        summary = event.get_market_summary()

        assert summary["sentiment"] == "Neutral"
        assert summary["risk_sentiment"] == "Balanced"
        assert "Neutral market with Balanced sentiment" in summary["summary"]

    def test_get_market_summary_consolidation(self):
        """Test market summary for consolidation."""
        event = MarketStateEvent(
            regime=MarketRegime.CONSOLIDATION,
            regime_confidence=0.68,
            etf_performance={},
            sector_strength={},
            event_id="consolidation_test",
            timestamp=datetime.now()
        )

        summary = event.get_market_summary()

        assert summary["sentiment"] == "Consolidating"
        assert summary["best_performer"] == "N/A (0)"  # No ETF data

    def test_get_market_summary_empty_etf_performance(self):
        """Test market summary with no ETF performance data."""
        event = MarketStateEvent(
            regime=MarketRegime.BULL,
            regime_confidence=0.8,
            etf_performance={},  # Empty
            sector_strength={},
            event_id="empty_etf_test",
            timestamp=datetime.now()
        )

        summary = event.get_market_summary()

        assert summary["best_performer"] == "N/A (0)"


class TestPatternAlertEvent:
    """Tests for PatternAlertEvent."""

    def test_pattern_alert_event_creation(self):
        """Test PatternAlertEvent creation."""
        # Create source pattern event
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.85,
            event_id="pattern_123",
            timestamp=datetime(2025, 1, 1, 10, 0, 0)
        )

        user_filters = {"symbols": ["AAPL"], "confidence_min": 0.8}

        alert = PatternAlertEvent(
            alert_id="alert_456",
            user_id="user789",
            timestamp=datetime(2025, 1, 1, 10, 0, 5),
            pattern_event=pattern_event,
            alert_type="pattern_match",
            delivery_channels=["websocket", "email"],
            user_filters=user_filters,
            alert_priority=EventPriority.HIGH
        )

        assert alert.alert_id == "alert_456"
        assert alert.user_id == "user789"
        assert alert.pattern_event == pattern_event
        assert alert.alert_type == "pattern_match"
        assert alert.delivery_channels == ["websocket", "email"]
        assert alert.user_filters == user_filters
        assert alert.alert_priority == EventPriority.HIGH

    def test_pattern_alert_to_websocket_dict(self):
        """Test PatternAlertEvent WebSocket conversion."""
        pattern_event = TierPatternEvent(
            pattern_type="TrendReversal",
            symbol="TSLA",
            tier=PatternTier.INTRADAY,
            confidence=0.9,
            event_id="pattern_789",
            timestamp=datetime(2025, 1, 1, 14, 30, 0)
        )

        alert = PatternAlertEvent(
            alert_id="alert_ws_test",
            user_id="user123",
            timestamp=datetime(2025, 1, 1, 14, 30, 5),
            pattern_event=pattern_event,
            user_filters={"symbols": ["TSLA"], "pattern_types": ["TrendReversal"]},
            alert_priority=EventPriority.CRITICAL
        )

        ws_dict = alert.to_websocket_dict()

        assert ws_dict["alert_id"] == "alert_ws_test"
        assert ws_dict["user_id"] == "user123"
        assert ws_dict["timestamp"] == "2025-01-01T14:30:05"
        assert ws_dict["alert_type"] == "pattern_match"
        assert ws_dict["priority"] == "critical"
        assert "pattern_event" in ws_dict
        assert ws_dict["pattern_event"]["pattern_type"] == "TrendReversal"
        assert ws_dict["delivery_channels"] == ["websocket"]
        assert ws_dict["matched_filters"] == ["symbols", "pattern_types"]

        # Should be JSON serializable
        json_str = json.dumps(ws_dict)
        assert len(json_str) > 0


class TestSystemHealthEvent:
    """Tests for SystemHealthEvent."""

    def test_system_health_event_creation(self):
        """Test SystemHealthEvent creation."""
        performance_metrics = {"latency_ms": 25.5, "throughput_ops": 1000}
        error_counts = {"connection_errors": 2, "timeout_errors": 0}

        event = SystemHealthEvent(
            service_name="websocket_manager",
            status="healthy",
            status_message="All systems operational",
            performance_metrics=performance_metrics,
            error_counts=error_counts,
            event_id="health_123",
            timestamp=datetime(2025, 1, 1, 12, 0, 0)
        )

        assert event.service_name == "websocket_manager"
        assert event.status == "healthy"
        assert event.status_message == "All systems operational"
        assert event.performance_metrics == performance_metrics
        assert event.error_counts == error_counts
        assert event.event_id == "health_123"
        assert event.source == "TickStockAppV2"

    def test_system_health_to_websocket_dict(self):
        """Test SystemHealthEvent WebSocket conversion."""
        event = SystemHealthEvent(
            service_name="pattern_processor",
            status="warning",
            status_message="High latency detected",
            performance_metrics={"avg_latency_ms": 150.0},
            error_counts={"processing_errors": 5},
            event_id="health_warning_456",
            timestamp=datetime(2025, 1, 1, 16, 15, 30)
        )

        ws_dict = event.to_websocket_dict()

        assert ws_dict["event_id"] == "health_warning_456"
        assert ws_dict["service_name"] == "pattern_processor"
        assert ws_dict["status"] == "warning"
        assert ws_dict["status_message"] == "High latency detected"
        assert ws_dict["performance_metrics"]["avg_latency_ms"] == 150.0
        assert ws_dict["error_counts"]["processing_errors"] == 5
        assert ws_dict["timestamp"] == "2025-01-01T16:15:30"
        assert ws_dict["source"] == "TickStockAppV2"


class TestEventTypeRegistry:
    """Tests for event type registry and factory functions."""

    def test_event_type_registry_completeness(self):
        """Test event type registry contains all event types."""
        assert "tier_pattern" in EVENT_TYPE_REGISTRY
        assert "market_state" in EVENT_TYPE_REGISTRY
        assert "pattern_alert" in EVENT_TYPE_REGISTRY
        assert "system_health" in EVENT_TYPE_REGISTRY

        assert EVENT_TYPE_REGISTRY["tier_pattern"] == TierPatternEvent
        assert EVENT_TYPE_REGISTRY["market_state"] == MarketStateEvent
        assert EVENT_TYPE_REGISTRY["pattern_alert"] == PatternAlertEvent
        assert EVENT_TYPE_REGISTRY["system_health"] == SystemHealthEvent

    def test_create_event_from_type_tier_pattern(self):
        """Test creating TierPatternEvent from event type."""
        data = {
            "pattern": "BreakoutBO",
            "symbol": "AAPL",
            "confidence": 0.8,
            "tier": "daily"
        }

        event = create_event_from_type("tier_pattern", data)

        assert isinstance(event, TierPatternEvent)
        assert event.pattern_type == "BreakoutBO"
        assert event.symbol == "AAPL"
        assert event.confidence == 0.8
        assert event.tier == PatternTier.DAILY

    def test_create_event_from_type_unknown(self):
        """Test creating event from unknown type."""
        event = create_event_from_type("unknown_type", {})

        assert event is None

    def test_create_event_from_type_no_from_redis_method(self):
        """Test creating event from type without from_redis_event method."""
        # Mock an event class without from_redis_event method
        class MockEvent:
            pass

        with patch.dict(EVENT_TYPE_REGISTRY, {"mock_event": MockEvent}):
            event = create_event_from_type("mock_event", {})

        assert event is None

    def test_create_event_from_type_error_handling(self):
        """Test error handling in event creation."""
        # This should trigger an error in from_redis_event
        data = {"invalid": "data", "confidence": "not_a_number"}

        event = create_event_from_type("tier_pattern", data)

        # Should still return an event (error event for TierPatternEvent)
        assert isinstance(event, TierPatternEvent)
        assert event.pattern_type == "ParseError"


class TestEventSerialization:
    """Test event serialization for WebSocket delivery."""

    def test_all_events_json_serializable(self):
        """Test that all events can be JSON serialized."""
        # TierPatternEvent
        tier_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.8,
            event_id="serialize_test_1",
            timestamp=datetime.now()
        )

        # MarketStateEvent
        market_event = MarketStateEvent(
            regime=MarketRegime.BULL,
            regime_confidence=0.85,
            etf_performance={"SPY": 0.02},
            sector_strength={"Tech": 0.03},
            event_id="serialize_test_2",
            timestamp=datetime.now()
        )

        # PatternAlertEvent
        alert_event = PatternAlertEvent(
            alert_id="serialize_test_3",
            user_id="user123",
            timestamp=datetime.now(),
            pattern_event=tier_event
        )

        # SystemHealthEvent
        health_event = SystemHealthEvent(
            service_name="test_service",
            status="healthy",
            status_message="All good",
            performance_metrics={"latency": 25.0},
            event_id="serialize_test_4",
            timestamp=datetime.now()
        )

        events = [tier_event, market_event, alert_event, health_event]

        for event in events:
            ws_dict = event.to_websocket_dict()

            # Should be JSON serializable
            json_str = json.dumps(ws_dict)
            assert len(json_str) > 0

            # Should be deserializable
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)
            assert "timestamp" in parsed

    def test_websocket_dict_completeness(self):
        """Test that WebSocket dicts contain all necessary fields."""
        tier_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.8,
            event_id="completeness_test",
            timestamp=datetime.now()
        )

        ws_dict = tier_event.to_websocket_dict()

        required_fields = [
            "event_id", "pattern_type", "symbol", "tier", "confidence",
            "timestamp", "source", "pattern_data", "market_context",
            "priority", "tags"
        ]

        for field in required_fields:
            assert field in ws_dict, f"Missing required field: {field}"

    def test_numeric_precision_in_websocket_dict(self):
        """Test numeric precision in WebSocket serialization."""
        # Test confidence rounding
        event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.123456789,  # Many decimal places
            event_id="precision_test",
            timestamp=datetime.now()
        )

        ws_dict = event.to_websocket_dict()

        # Should round confidence to 3 decimal places
        assert ws_dict["confidence"] == 0.123

        # Test market state rounding
        market_event = MarketStateEvent(
            regime=MarketRegime.BULL,
            regime_confidence=0.876543210,
            etf_performance={"SPY": 0.123456},
            sector_strength={"Tech": -0.987654},
            event_id="market_precision_test",
            timestamp=datetime.now(),
            risk_on_score=0.555555
        )

        ws_dict = market_event.to_websocket_dict()

        # Should round appropriately
        assert ws_dict["regime_confidence"] == 0.877  # 3 decimals
        assert ws_dict["etf_performance"]["SPY"] == 0.12  # 2 decimals
        assert ws_dict["sector_strength"]["Tech"] == -0.99  # 2 decimals
        assert ws_dict["risk_on_score"] == 0.56  # 2 decimals
