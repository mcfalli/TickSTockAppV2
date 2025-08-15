"""
Market Metrics Tracking Module
Centralizes all market metrics including counts, activity levels, and tick tracking.
Sprint 36: Refactored from metrics_tracker.py to provide tick-based activity tracking.
"""

import time
from datetime import datetime
from collections import deque
from typing import Dict, List, Any, Optional, Tuple
import pytz
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'market_metrics')

class MarketMetrics:
    """
    Centralized market metrics tracking including:
    - Session high/low counts
    - Tick-based activity tracking
    - Activity level calculations
    - Per-ticker momentum tracking
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Session counts (from metrics_tracker)
        self._running_high_low_totals = {
            "total_highs": 0,
            "total_lows": 0,
            "total_events": 0
        }
        
        # Cache for high/low totals
        self._cached_high_low_totals = None
        self._cached_high_low_timestamp = 0
        self._cache_ttl = 1.0  # 1 second cache
        
        # Tick tracking for activity metrics (replacing event-based)
        self._tick_windows = {
            10: deque(),    # 10 second window
            30: deque(),    # 30 second window  
            60: deque(),    # 60 second window
            300: deque()    # 300 second window
        }
        
        # Per-ticker momentum tracking (from metrics_tracker)
        self.per_ticker_momentum = {}
        self.MOMENTUM_WINDOW_SECONDS = config.get('MOMENTUM_WINDOW_SECONDS', 10)
        
        # Activity thresholds (ticks per minute) - NEW tick-based
        self.ACTIVITY_THRESHOLDS = {
            'very_low': 30,
            'low': 60,
            'medium': 120,
            'high': 240,
            'very_high': 480
        }
        
        # Market session tracking
        self._current_session = None
        self._session_start_time = None
        self.eastern_tz = pytz.timezone('US/Eastern')
        
        logger.info("✅ MarketMetrics initialized with tick-based activity tracking")
    
    # ========== TICK TRACKING (NEW) ==========
    
    def record_tick(self, timestamp: Optional[float] = None) -> None:
        """Record a market tick for activity tracking."""
        current_time = timestamp or time.time()
        
        # Add to all windows
        for window_seconds in self._tick_windows:
            self._tick_windows[window_seconds].append(current_time)
        
        # Cleanup old entries
        self._cleanup_tick_windows(current_time)
    
    def get_tick_counts(self) -> Dict[str, int]:
        """Get current tick counts for all windows."""
        current_time = time.time()
        tick_counts = {}
        
        for window_seconds, window_deque in self._tick_windows.items():
            # Count ticks within window
            cutoff = current_time - window_seconds
            valid_ticks = [t for t in window_deque if t > cutoff]
            tick_counts[f'ticks_{window_seconds}sec'] = len(valid_ticks)
        
        return tick_counts
    
    # ========== HIGH/LOW COUNT TRACKING (FROM metrics_tracker) ==========
    
    def update_high_low_tracking(self, ticker: str, high_count_delta: int = 0, low_count_delta: int = 0) -> None:
        """
        Update high/low tracking when counts change.
        
        Args:
            ticker: Ticker symbol that had a count change
            high_count_delta: Change in high count (positive for increase)
            low_count_delta: Change in low count (positive for increase)
        """
        # Update running totals
        self._running_high_low_totals["total_highs"] += high_count_delta
        self._running_high_low_totals["total_lows"] += low_count_delta
        self._running_high_low_totals["total_events"] += (high_count_delta + low_count_delta)
        
        # Invalidate cache to force recalculation on next request
        self._cached_high_low_timestamp = 0
        
        # Debug logging if enabled
        if self.config.get('DEBUG_COUNT_TRACKING', False):
            logger.debug(f"COUNT LOG: Updated {ticker} - High delta: {high_count_delta}, Low delta: {low_count_delta}. "
                        f"Totals - Highs: {self._running_high_low_totals['total_highs']}, "
                        f"Lows: {self._running_high_low_totals['total_lows']}")
    
    def get_high_low_totals(self) -> Dict[str, Any]:
        """Get cached high/low totals with percentages."""
        current_time = time.time()
        
        # Check cache
        if (self._cached_high_low_totals and 
            current_time - self._cached_high_low_timestamp < self._cache_ttl):
            return self._cached_high_low_totals
        
        # Use running totals
        total_highs = self._running_high_low_totals["total_highs"]
        total_lows = self._running_high_low_totals["total_lows"]
        total_events = self._running_high_low_totals["total_events"]
        
        # Calculate percentages for visualization
        high_percentage = 50.0  # Default balanced value
        low_percentage = 50.0
        
        if total_events > 0:
            high_percentage = (total_highs / total_events) * 100
            low_percentage = (total_lows / total_events) * 100
        
        # Ensure minimum 10% for UI visualization
        if high_percentage < 10 and total_events > 0:
            high_percentage = 10
            low_percentage = 90
        elif low_percentage < 10 and total_events > 0:
            low_percentage = 10
            high_percentage = 90
        
        result = {
            "total_highs": total_highs,
            "total_lows": total_lows,
            "total_events": total_events,
            "high_percentage": high_percentage,
            "low_percentage": low_percentage
        }
        
        # Cache the result
        self._cached_high_low_totals = result
        self._cached_high_low_timestamp = current_time
        
        return result
    
    def reset_session_counts(self, reason: str = "session_change") -> None:
        """Reset session counts (called during market transitions)."""
        logger.info(f"COUNT LOG: Resetting session counts. Reason: {reason}. "
                   f"Previous counts - Highs: {self._running_high_low_totals['total_highs']}, "
                   f"Lows: {self._running_high_low_totals['total_lows']}")
        
        # Reset counts
        self._running_high_low_totals = {
            "total_highs": 0,
            "total_lows": 0,
            "total_events": 0
        }
        
        # Invalidate cache
        self._cached_high_low_totals = None
        self._cached_high_low_timestamp = 0
        
        # Clear tick windows for fresh start
        for window in self._tick_windows.values():
            window.clear()
            
        # Clear per-ticker momentum
        self.per_ticker_momentum.clear()
    
    # ========== PER-TICKER MOMENTUM (FROM metrics_tracker) ==========
    
    def update_per_ticker_momentum(self, ticker: str, event_type: str, timestamp: Any) -> Tuple[int, int]:
        """
        Update momentum tracking for a specific ticker.
        
        Args:
            ticker: Stock symbol
            event_type: "high" or "low"
            timestamp: Event timestamp
            
        Returns:
            tuple: (high_count, low_count) for the ticker in the momentum window
        """
        if ticker not in self.per_ticker_momentum:
            self.per_ticker_momentum[ticker] = {"highs": [], "lows": [], "last_update": 0.0}
        
        momentum = self.per_ticker_momentum[ticker]
        current_time = time.time()
        
        # Rate-limit updates to prevent spam
        if current_time - momentum["last_update"] < 0.1:
            return len(momentum["highs"]), len(momentum["lows"])
        
        momentum["last_update"] = current_time
        
        # Convert timestamp to Unix seconds
        timestamp_seconds = timestamp.timestamp() if isinstance(timestamp, datetime) else timestamp
        
        # Record the event
        if event_type == "high":
            momentum["highs"].append(timestamp_seconds)
        elif event_type == "low":
            momentum["lows"].append(timestamp_seconds)
        
        # Clean up old events
        cutoff = current_time - self.MOMENTUM_WINDOW_SECONDS
        momentum["highs"] = [t for t in momentum["highs"] if t > cutoff]
        momentum["lows"] = [t for t in momentum["lows"] if t > cutoff]
        
        # Cap to prevent memory issues
        max_events = 100
        if len(momentum["highs"]) > max_events:
            momentum["highs"] = momentum["highs"][-max_events:]
        if len(momentum["lows"]) > max_events:
            momentum["lows"] = momentum["lows"][-max_events:]
        
        return len(momentum["highs"]), len(momentum["lows"])
    
    # ========== ACTIVITY METRICS (REFACTORED) ==========
    
    def get_activity_metrics(self) -> Dict[str, Any]:
        """Get comprehensive activity metrics for WebSocket emission."""
        current_time = time.time()
        
        # Get tick counts
        tick_counts = self.get_tick_counts()
        
        # Get high/low totals
        high_low_totals = self.get_high_low_totals()
        
        # Calculate ticks per minute from 60-second window
        ticks_per_minute = tick_counts.get('ticks_60sec', 0)
        
        # Determine activity level
        activity_level = self._calculate_activity_level(ticks_per_minute)
        
        # Check for special market periods
        if self._is_market_open_period():
            activity_level = "Opening Bell"
        elif self._is_market_close_period():
            activity_level = "Closing Bell"
        
        # Build complete activity metrics
        return {
            'total_highs': high_low_totals['total_highs'],
            'total_lows': high_low_totals['total_lows'],
            'activity_level': activity_level,
            'activity_ratio': {
                'calculation_method': 'ticks_per_minute',
                'current_rate': ticks_per_minute,
                'threshold_low': self.ACTIVITY_THRESHOLDS['very_low'],
                'threshold_medium': self.ACTIVITY_THRESHOLDS['low'],
                'threshold_high': self.ACTIVITY_THRESHOLDS['medium'],
                'threshold_very_high': self.ACTIVITY_THRESHOLDS['high']
            },
            **tick_counts  # Include all tick window counts
        }
    
    # ========== MARKET SESSION HANDLING ==========
    
    def set_market_session(self, session: str, session_start: Optional[datetime] = None) -> None:
        """Update current market session for activity level calculations."""
        self._current_session = session
        self._session_start_time = session_start or datetime.now(self.eastern_tz)
        logger.info(f"Market session set to: {session}")
    
    def determine_market_status(self, current_time: Optional[datetime] = None) -> str:
        """
        Determine market status based on eastern time.
        
        Returns:
            str: Market status ("PRE", "REGULAR", "AFTER", or "CLOSED")
        """
        if current_time is None:
            current_time = datetime.now(self.eastern_tz)
        
        hour, minute = current_time.hour, current_time.minute
        if 4 <= hour < 9 or (hour == 9 and minute < 30):
            return "PRE"
        elif (hour == 9 and minute >= 30) or (10 <= hour < 16):
            return "REGULAR"
        elif 16 <= hour < 20:
            return "AFTER"
        return "CLOSED"
    
    # ========== Heatbeat Status Update Handler ==========

    def get_status_metrics(self, api_health: Dict[str, Any]) -> Dict[str, Any]:
        """Get simplified status metrics for heartbeat/status updates."""
        # Determine provider based on config
        use_synthetic = self.config.get('USE_SYNTHETIC_DATA', False)
        use_polygon = self.config.get('USE_POLYGON_API', False)
        provider = "Test" if use_synthetic else ("Production" if use_polygon else "Test")
        
        # Calculate average response time
        avg_response = float(sum(api_health.get("response_times", [])) / len(api_health.get("response_times", [1])) 
                        if api_health.get("response_times") else 0)
        
        return {
            "status": api_health.get("status", "unknown"),
            "connected": api_health.get("connected", False),
            "provider": provider,
            "market_status": self.determine_market_status(),  # Already has this method!
            "timestamp": datetime.now().isoformat(),
            "avg_response": avg_response
        }

    # ========== PRIVATE HELPER METHODS ==========
    
    def _cleanup_tick_windows(self, current_time: float) -> None:
        """Remove old ticks from windows."""
        for window_seconds, window_deque in self._tick_windows.items():
            cutoff = current_time - window_seconds
            while window_deque and window_deque[0] < cutoff:
                window_deque.popleft()
    
    def _calculate_activity_level(self, ticks_per_minute: int) -> str:
        """Calculate activity level based on tick rate."""
        if ticks_per_minute >= self.ACTIVITY_THRESHOLDS['very_high']:
            return 'Extreme'
        elif ticks_per_minute >= self.ACTIVITY_THRESHOLDS['high']:
            return 'Very High'
        elif ticks_per_minute >= self.ACTIVITY_THRESHOLDS['medium']:
            return 'High'
        elif ticks_per_minute >= self.ACTIVITY_THRESHOLDS['low']:
            return 'Medium'
        elif ticks_per_minute >= self.ACTIVITY_THRESHOLDS['very_low']:
            return 'Low'
        else:
            return 'Very Low'
    
    def _is_market_open_period(self) -> bool:
        """Check if we're in the opening bell period (first 15 minutes)."""
        if self._current_session != 'REGULAR' or not self._session_start_time:
            return False
            
        elapsed = (datetime.now(self.eastern_tz) - self._session_start_time).total_seconds()
        return elapsed < 900  # 15 minutes
    
    def _is_market_close_period(self) -> bool:
        """Check if we're in the closing bell period (last 15 minutes)."""
        if self._current_session != 'REGULAR':
            return False
            
        now = datetime.now(self.eastern_tz)
        return now.hour == 15 and now.minute >= 45