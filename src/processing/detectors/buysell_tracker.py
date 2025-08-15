import time
from collections import deque
from typing import Dict, List, Set, Any, Optional
from datetime import datetime, date
import pytz
from src.processing.detectors.buysell_engine import BuySellTracker
from config.logging_config import get_domain_logger, LogDomain

# PHASE 4: Import typed event classes
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent

logger = get_domain_logger(LogDomain.CORE, 'buysell_market_tracker')

class BuySellMarketTracker(BuySellTracker):
    """
    Enhanced tracker with universe filtering logging.
    Tracks buying and selling pressure based on price movements of high-volume stocks.
    Uses a rolling window to calculate net pressure scores.
    
    PHASE 4: Now uses typed events internally for all processing.
    """
    
    def __init__(self, config, cache_control=None):
        """Initialize with analytics manager integration."""
        super().__init__(config, tracker_name="MARKET")
        
        # Existing initialization...
        self.tracked_stocks = set(cache_control.get_default_universe()) if cache_control else set()
        self.cache_control = cache_control
        
        # 🆕 PHASE 2.2: Analytics Manager Integration
        self.analytics_integration_enabled = config.get('ANALYTICS_INTEGRATION_ENABLED', True)
        self.analytics_manager = None  # Will be set by market_data_service
        

        # Enhanced rolling average buffers for smooth visualization
        self.rolling_buffers = {
            '5min': deque(maxlen=10),    # 10 calculations × 30 seconds = 5 minutes
            '15min': deque(maxlen=30),   # 30 calculations × 30 seconds = 15 minutes
        }
        
        # Session-wide tracking for session average
        self.session_tracking = {
            'session_date': None,
            'net_score_sum': 0.0,
            'calculation_count': 0,
            'session_start_time': None
        }
        
        # Track universe filtering statistics
        self.universe_stats = {
            'ticks_received': 0,
            'ticks_processed': 0,
            'ticks_filtered': 0,
            'unique_tickers_received': set(),
            'unique_tickers_processed': set(),
            'unique_tickers_filtered': set(),
            'last_stats_log': time.time(),
            'last_hour_stats': {
                'processed': 0,
                'filtered': 0,
                'last_reset': time.time()
            }
        }
        
        self.reset_tracking()
        
    def reset_tracking(self):
        """Reset all tracking data including rolling averages."""
        self.buysell_market = {
            "buying_count": 0,           # Volume-weighted buying activity
            "selling_count": 0,          # Volume-weighted selling activity
            "activity_count": 0,         # Total volume activity
            "last_prices": {},           # Store previous prices for comparison
            "calculations": [],          # Store last 4 calculations
            "window_start": time.time(), # Time window tracking
            "tracked_stocks": self.tracked_stocks.copy()  # Set of stocks we're tracking
        }
        
        # Track events within the rolling window
        self.events = []
        
        # Reset universe filter stats but keep hourly stats
        current_time = time.time()
        self.universe_stats.update({
            'ticks_received': 0,
            'ticks_processed': 0,
            'ticks_filtered': 0,
            'unique_tickers_received': set(),
            'unique_tickers_processed': set(),
            'unique_tickers_filtered': set(),
            'last_stats_log': current_time
        })
        
        # Clear rolling buffers but keep session tracking unless it's a new session
        self.rolling_buffers['5min'].clear()
        self.rolling_buffers['15min'].clear()
        

    def set_analytics_manager(self, analytics_manager):
        """
        Set analytics manager for automatic data recording.
        
        Args:
            analytics_manager: AnalyticsManager instance
        """
        self.analytics_manager = analytics_manager

    def initialize_session(self, session_date: date):
        """
        Initialize or continue session tracking.
        
        Args:
            session_date: Current trading session date
        """
        if self.session_tracking['session_date'] != session_date:
            # New session - reset session tracking
            self.session_tracking = {
                'session_date': session_date,
                'net_score_sum': 0.0,
                'calculation_count': 0,
                'session_start_time': time.time()
            }
            
            # Clear rolling buffers for new session
            self.rolling_buffers['5min'].clear()
            self.rolling_buffers['15min'].clear()
            
 
    
    def process_tick(self, ticker: str, price: float, volume: Optional[int] = None, timestamp: Optional[float] = None) -> bool:
        """
        Enhanced process_tick with comprehensive universe filtering logging.
        
        Args:
            ticker: Stock symbol
            price: Current price
            volume: Trading volume (if available, otherwise estimated)
            timestamp: Event timestamp (defaults to current time)
            
        Returns:
            bool: True if event was processed, False if ignored
        """
        current_time = timestamp or time.time()
        
        # Update received counter and unique ticker tracking
        self.universe_stats['ticks_received'] += 1
        self.universe_stats['unique_tickers_received'].add(ticker)
        
        # Check if ticker is in tracked universe
        if ticker not in self.tracked_stocks:
            self.universe_stats['ticks_filtered'] += 1
            self.universe_stats['unique_tickers_filtered'].add(ticker)
            
            logger.debug(f"DIAG-UNIVERSE: FILTERED_MARKET: {ticker} not in tracked universe - skipping")
            
            # Log filtering statistics periodically
            self._log_filter_statistics()
            return False
        
        # Ticker is in universe - process normally
        self.universe_stats['ticks_processed'] += 1
        self.universe_stats['unique_tickers_processed'].add(ticker)
        self.universe_stats['last_hour_stats']['processed'] += 1
        
        # Use default volume if not provided
        if volume is None or volume <= 0:
            volume = 100
        
        # Check if we have a previous price for comparison
        if ticker in self.buysell_market["last_prices"]:
            prev_price = self.buysell_market["last_prices"][ticker]
            
            # Calculate price change and determine if buying or selling pressure
            if price > prev_price:
                # Buying pressure (price went up)
                self.events.append({
                    "ticker": ticker,
                    "type": "buy",
                    "price": price,
                    "prev_price": prev_price,
                    "volume": volume,
                    "timestamp": current_time,
                    "price_change": price - prev_price,
                    "price_change_pct": round(((price - prev_price) / prev_price) * 100, 4)
                })
                
            elif price < prev_price:
                # Selling pressure (price went down)
                self.events.append({
                    "ticker": ticker,
                    "type": "sell",
                    "price": price,
                    "prev_price": prev_price,
                    "volume": volume,
                    "timestamp": current_time,
                    "price_change": price - prev_price,
                    "price_change_pct": round(((price - prev_price) / prev_price) * 100, 4)
                })
        
        # Update last price regardless of whether we had a previous value
        self.buysell_market["last_prices"][ticker] = price
        
        # Check if it's time to calculate metrics (end of window)
        if current_time - self.buysell_market["window_start"] >= self.window_seconds:
            self.calculate_pressure_metrics()
            
            # Log filtering statistics periodically
            self._log_filter_statistics()
            return True
        
        # Log filtering statistics periodically
        self._log_filter_statistics()
        
        return True
    '''
    def process_typed_event(self, event: BaseEvent) -> bool:
        """
        PHASE 4: Process typed event directly without dict conversion.
        
        Args:
            event: Typed event (HighLowEvent, TrendEvent, or SurgeEvent)
            
        Returns:
            bool: True if event was processed, False if ignored
        """
        # Check if ticker is in tracked universe
        if event.ticker not in self.tracked_stocks:
            self.universe_stats['ticks_filtered'] += 1
            self.universe_stats['unique_tickers_filtered'].add(event.ticker)
            logger.debug(f"DIAG-UNIVERSE: FILTERED_MARKET: {event.ticker} not in tracked universe - skipping typed event")
            return False
        
        # Process based on event type
        if isinstance(event, HighLowEvent):
            # High/Low events contribute to pressure based on direction
            volume = event.volume if event.volume > 0 else 5000
            if event.type in ['session_high', 'high']:
                self.buysell_market["buying_count"] += volume
                self.buysell_market["activity_count"] += volume
            else:
                self.buysell_market["selling_count"] += volume
                self.buysell_market["activity_count"] += volume
        
        elif isinstance(event, TrendEvent):
            # Trend events contribute based on direction
            volume = event.volume if event.volume > 0 else 1000
            if event.direction in ['up', '↑']:
                self.buysell_market["buying_count"] += volume
                self.buysell_market["activity_count"] += volume
            elif event.direction in ['down', '↓']:
                self.buysell_market["selling_count"] += volume
                self.buysell_market["activity_count"] += volume
        
        elif isinstance(event, SurgeEvent):
            # Surge events have significant impact
            volume = event.volume if event.volume > 0 else 10000
            if event.direction in ['up', '↑']:
                self.buysell_market["buying_count"] += volume * event.surge_volume_multiplier
                self.buysell_market["activity_count"] += volume * event.surge_volume_multiplier
            elif event.direction in ['down', '↓']:
                self.buysell_market["selling_count"] += volume * event.surge_volume_multiplier
                self.buysell_market["activity_count"] += volume * event.surge_volume_multiplier
        
        # Check if it's time to calculate metrics
        current_time = event.time
        if current_time - self.buysell_market["window_start"] >= self.window_seconds:
            self.calculate_pressure_metrics()
        
        return True
    '''
    def calculate_pressure_metrics(self):
        """
        UPDATED Sprint 1: Enhanced calculate pressure metrics with FIXED analytics recording.
        PHASE 4: Now processes internal event data without dict access.
        """
        
        # Existing calculation logic...
        current_time = time.time()
        window_start = self.buysell_market["window_start"]
        
        # Filter events in the current window
        window_events = [e for e in self.events 
                        if e["timestamp"] >= window_start]
        
        # Reset counters for this window
        buying_count = 0
        selling_count = 0
        activity_count = 0
        
        # Detailed analysis for logging
        buy_events = []
        sell_events = []
        unique_buy_tickers = set()
        unique_sell_tickers = set()
        
        # Accumulate events by type
        for event in window_events:
            # PHASE 4: Direct access to event dict fields (these are internal pressure tracking dicts, not typed events)
            volume = event["volume"]  # Direct access, no .get()
            ticker = event["ticker"]
            
            if event["type"] == "buy":
                buying_count += volume
                activity_count += volume
                buy_events.append(event)
                unique_buy_tickers.add(ticker)
            elif event["type"] == "sell":
                selling_count += volume
                activity_count += volume
                sell_events.append(event)
                unique_sell_tickers.add(ticker)
        
        # Calculate net score using base class method
        net_score = self.calculate_net_score(buying_count, selling_count, activity_count)
        
        # Get activity level from base class and map to database-valid values
        base_activity_level = self.calculate_activity_level(activity_count)
        
        # Map activity levels to database constraint valid values
        activity_level_mapping = {
            'low': 'Low',
            'moderate': 'Moderate', 
            'high': 'High',
            'very_high': 'Very High',
            'extreme': 'Very High',
            'ultra': 'Very High',
            'mega': 'Very High'
        }
        
        activity_level = activity_level_mapping.get(
            base_activity_level.lower().replace(' ', '_'), 
            'Moderate'
        )
        
        # Rolling Average Calculations (kept for compatibility)
        self.rolling_buffers['5min'].append(net_score)
        self.rolling_buffers['15min'].append(net_score)
        
        # Calculate rolling averages
        avg_net_score_5min = self._calculate_buffer_average(self.rolling_buffers['5min'])
        avg_net_score_15min = self._calculate_buffer_average(self.rolling_buffers['15min'])
        
        # Update session tracking
        self.session_tracking['net_score_sum'] += net_score
        self.session_tracking['calculation_count'] += 1
        avg_net_score_session = (self.session_tracking['net_score_sum'] / 
                                self.session_tracking['calculation_count'])
        
        # Enhanced Result with Averages (kept for compatibility)
        result = {
            # Raw calculations (30-second window)
            "net_score": net_score,
            "buying_count": buying_count,
            "selling_count": selling_count,
            "activity_count": activity_count,
            "activity_level": activity_level,
            "calc_time": current_time,
            "window_start": window_start,
            "window_end": current_time,
            "buy_events_count": len(buy_events),
            "sell_events_count": len(sell_events),
            "unique_buy_tickers": len(unique_buy_tickers),
            "unique_sell_tickers": len(unique_sell_tickers),
            
            # Rolling averages for smooth visualization (legacy)
            "avg_net_score_5min": avg_net_score_5min,
            "avg_net_score_15min": avg_net_score_15min,
            "avg_net_score_session": avg_net_score_session,
            
            # Enhanced metadata
            "session_date": self.session_tracking['session_date'],
            "total_universe_size": len(self.tracked_stocks),
            "rolling_buffer_sizes": {
                '5min': len(self.rolling_buffers['5min']),
                '15min': len(self.rolling_buffers['15min'])
            },
            "session_calculation_count": self.session_tracking['calculation_count'],
            "original_activity_level": base_activity_level
        }
        
        # Update buysell_market state
        self.buysell_market["buying_count"] = buying_count
        self.buysell_market["selling_count"] = selling_count
        self.buysell_market["activity_count"] = activity_count
        
        # Store calculation in history (keep last 4)
        self.buysell_market["calculations"].append(result)
        if len(self.buysell_market["calculations"]) > 4:
            self.buysell_market["calculations"] = self.buysell_market["calculations"][-4:]
        
        if self.analytics_integration_enabled and self.analytics_manager:
            try:
                analytics_data = {
                    # Identity & Timing
                    'session_date': self.session_tracking['session_date'] or date.today(),
                    'timestamp': datetime.fromtimestamp(current_time),
                    'universe_type': 'core',  # FIXED: Mark as core universe
                    'data_source': 'core',    # FIXED: Changed from 'live' to 'core'
                    # Current Market Data (for accumulation)
                    'market_net_score': net_score,
                    'market_activity_level': activity_level,
                    'market_buying_count': buying_count,
                    'market_selling_count': selling_count,
                    'market_activity_count': activity_count,
                    # Event Details
                    'buy_events_count': len(buy_events),
                    'sell_events_count': len(sell_events),
                    'unique_buy_tickers': len(unique_buy_tickers),
                    'unique_sell_tickers': len(unique_sell_tickers),
                    # Universe Context
                    'total_universe_size': len(self.tracked_stocks),
                    # Performance Data
                    'calc_time_ms': (current_time - window_start) * 1000,
                    'window_start_time': datetime.fromtimestamp(window_start),
                    'window_end_time': datetime.fromtimestamp(current_time),
                    # Legacy fields (for compatibility during transition)
                    'avg_net_score_5min': avg_net_score_5min,
                    'avg_net_score_15min': avg_net_score_15min,
                    'avg_net_score_session': avg_net_score_session
                }
                
                success = self.analytics_manager.record_market_calculation(analytics_data)

            except Exception as e:
                logger.error(f"FIXED: Error in analytics accumulation: {e}")

        # Start new window
        self.buysell_market["window_start"] = current_time
        
        # Prune old events
        cutoff_time = current_time - self.window_seconds
        self.events = [e for e in self.events if e["timestamp"] >= cutoff_time]

        return result
    
    def _calculate_buffer_average(self, buffer: deque) -> float:
        """
        Calculate average of values in a rolling buffer.
        
        Args:
            buffer: deque containing net score values
            
        Returns:
            float: Average value, or 0.0 if buffer is empty
        """
        if not buffer:
            return 0.0
        
        return sum(buffer) / len(buffer)

    def get_latest_metrics_with_averages(self) -> Dict[str, Any]:
        """
        Get the latest calculated metrics including rolling averages.
        
        Returns:
            dict: Latest pressure metrics with averages or empty dict if no calculations yet
        """
        if self.buysell_market["calculations"]:
            latest = self.buysell_market["calculations"][-1].copy()
            
            # Add additional context for database storage
            latest["universe_info"] = {
                "tracked_stocks_count": len(self.tracked_stocks),
                "current_universes": getattr(self, '_current_universe_keys', []),
                "filter_stats": {
                    "last_filter_rate": self.universe_stats.get('filter_rate_percentage', 0),
                    "unique_tickers_processed": len(self.universe_stats.get('unique_tickers_processed', set())),
                    "unique_tickers_filtered": len(self.universe_stats.get('unique_tickers_filtered', set()))
                }
            }
            
            # Add smoothing quality indicators
            latest["smoothing_quality"] = {
                "5min_sample_count": len(self.rolling_buffers['5min']),
                "15min_sample_count": len(self.rolling_buffers['15min']),
                "5min_full": len(self.rolling_buffers['5min']) >= self.rolling_buffers['5min'].maxlen,
                "15min_full": len(self.rolling_buffers['15min']) >= self.rolling_buffers['15min'].maxlen,
                "session_stability": min(1.0, self.session_tracking['calculation_count'] / 100.0)  # 0-1 stability score
            }
            
            return latest
        
        return {}
    '''
    def get_analytics_data_for_database(self) -> Optional[Dict[str, Any]]:
        """
        UPDATED Sprint 1: Get formatted data for FIXED analytics system.
        This method is now used for compatibility only.
        
        Returns:
            dict: Analytics data compatible with FIXED system
        """
        latest_metrics = self.get_latest_metrics_with_averages()
        
        if not latest_metrics:
            return None
        
        # FIXED: Format for new analytics system
        analytics_data = {
            # Identity & Timing
            'session_date': latest_metrics.get('session_date') or date.today(),
            'timestamp': datetime.now(),
            'universe_type': 'core',  # FIXED: Always core for market tracker
            'data_source': 'core',    # FIXED: Changed from 'live' to 'core'
            
            # Current Market Data (Sprint 1 new field names)
            'market_net_score': latest_metrics.get('net_score', 0),
            'market_activity_level': latest_metrics.get('activity_level', 'Low'),
            'market_buying_count': latest_metrics.get('buying_count', 0),
            'market_selling_count': latest_metrics.get('selling_count', 0),
            'market_activity_count': latest_metrics.get('activity_count', 0),
            
            # Enhanced event data
            'buy_events_count': latest_metrics.get('buy_events_count', 0),
            'sell_events_count': latest_metrics.get('sell_events_count', 0),
            'unique_buy_tickers': latest_metrics.get('unique_buy_tickers', 0),
            'unique_sell_tickers': latest_metrics.get('unique_sell_tickers', 0),
            'total_universe_size': latest_metrics.get('total_universe_size', 0),
            
            # Performance data
            'calc_time_ms': (latest_metrics.get('calc_time', 0) - latest_metrics.get('window_start', 0)) * 1000,
            'window_start_time': datetime.fromtimestamp(latest_metrics.get('window_start', 0)),
            'window_end_time': datetime.fromtimestamp(latest_metrics.get('calc_time', 0)),
            
            # Legacy compatibility fields
            'avg_net_score_5min': latest_metrics.get('avg_net_score_5min', 0.0),
            'avg_net_score_15min': latest_metrics.get('avg_net_score_15min', 0.0),
            'avg_net_score_session': latest_metrics.get('avg_net_score_session', 0.0)
        }
        
        return analytics_data
    '''
    def _log_filter_statistics(self):
        """Enhanced filter statistics logging with hourly trends."""
        try:
            current_time = time.time()
            
            # Log every 60 seconds
            if current_time - self.universe_stats['last_stats_log'] >= 60:
                stats = self.universe_stats
                
                if stats['ticks_received'] > 0:
                    filter_rate = round((stats['ticks_filtered'] / stats['ticks_received']) * 100, 1)
                    
                    # Calculate unique ticker statistics
                    unique_received = len(stats['unique_tickers_received'])
                    unique_processed = len(stats['unique_tickers_processed'])
                    unique_filtered = len(stats['unique_tickers_filtered'])
                    
                    logger.debug(
                        f"MARKET_FILTER_STATS: {stats['ticks_processed']} ticks processed, "
                        f"{stats['ticks_filtered']} filtered ({filter_rate}% filter rate), "
                        f"unique tickers: {unique_processed} processed, {unique_filtered} filtered, "
                        f"universe size: {len(self.tracked_stocks)}"
                    )
                    
                    # Log hourly trend if significant filtering
                    hourly_stats = stats['last_hour_stats']
                    time_since_reset = current_time - hourly_stats['last_reset']
                    
                    if time_since_reset >= 3600:  # 1 hour
                        hourly_filter_rate = round((hourly_stats['filtered'] / (hourly_stats['processed'] + hourly_stats['filtered'])) * 100, 1) if (hourly_stats['processed'] + hourly_stats['filtered']) > 0 else 0
                        
                        logger.info(
                            f"MARKET_HOURLY_TREND: {hourly_stats['processed']} processed, "
                            f"{hourly_stats['filtered']} filtered ({hourly_filter_rate}% hourly filter rate)"
                        )
                        
                        # Reset hourly stats
                        hourly_stats['processed'] = 0
                        hourly_stats['filtered'] = 0
                        hourly_stats['last_reset'] = current_time
                
                # Reset counters
                stats['ticks_received'] = 0
                stats['ticks_processed'] = 0
                stats['ticks_filtered'] = 0
                stats['unique_tickers_received'] = set()
                stats['unique_tickers_processed'] = set()
                stats['unique_tickers_filtered'] = set()
                stats['last_stats_log'] = current_time
                
        except Exception as e:
            logger.error(f"Error logging market filter statistics: {e}")
    '''
    def update_tracked_stocks(self, universe_keys):
        """
        Enhanced update with comprehensive universe logging.
        
        Args:
            universe_keys: List of universe keys to combine
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not universe_keys:
                logger.warning("No universe keys provided, keeping current tracked stocks")
                return False
            
            old_count = len(self.tracked_stocks)
            old_universes = getattr(self, '_current_universe_keys', [])
            
            # Get combined ticker list from cache_control
            all_tickers = set()
            universe_breakdown = {}
            
            for universe_key in universe_keys:
                try:
                    tickers = self.cache_control.get_universe_tickers(universe_key)
                    all_tickers.update(tickers)
                    universe_breakdown[universe_key] = len(tickers)
                    
                except Exception as e:
                    logger.error(f"Error getting tickers for universe {universe_key}: {e}")
            
            # Analyze the change
            added_tickers = all_tickers - self.tracked_stocks
            removed_tickers = self.tracked_stocks - all_tickers
            
            # Update tracked stocks
            self.tracked_stocks = all_tickers
            new_count = len(self.tracked_stocks)
            
            # Store current universe keys for future reference
            self._current_universe_keys = universe_keys
            
            # Reset tracking data to start fresh with new universe
            self.reset_tracking()
            
            # Comprehensive logging
            logger.info(f"DIAG-UNIVERSE: MARKET_UNIVERSE_UPDATE: {old_count} -> {new_count} stocks (+{len(added_tickers)} added, -{len(removed_tickers)} removed) from src.core.services.universes: {universe_keys}")
            
            # Log universe breakdown
            universe_info = []
            for universe_key, count in universe_breakdown.items():
                universe_info.append(f"{universe_key}({count})")
            
            logger.info(f"DIAG-UNIVERSE: MARKET_UNIVERSE_BREAKDOWN: {', '.join(universe_info)}")
            
            # Log significant changes
            if len(added_tickers) > 0:
                if len(added_tickers) <= 10:
                    logger.debug(f"DIAG-UNIVERSE: MARKET_ADDED_TICKERS: {', '.join(sorted(added_tickers))}")
                else:
                    logger.debug(f"DIAG-UNIVERSE: MARKET_ADDED_TICKERS: {len(added_tickers)} tickers (too many to list)")
            
            if len(removed_tickers) > 0:
                if len(removed_tickers) <= 10:
                    logger.debug(f"DIAG-UNIVERSE: MARKET_REMOVED_TICKERS: {', '.join(sorted(removed_tickers))}")
                else:
                    logger.debug(f"DIAG-UNIVERSE: MARKET_REMOVED_TICKERS: {len(removed_tickers)} tickers (too many to list)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in market tracker universe update: {e}", exc_info=True)
            return False
    def get_latest_metrics(self) -> Dict[str, Any]:
        """
        Get the latest calculated metrics with universe context.
        
        Returns:
            dict: Latest pressure metrics or empty dict if no calculations yet
        """
        if self.buysell_market["calculations"]:
            latest = self.buysell_market["calculations"][-1].copy()
            
            # Add universe context
            latest["universe_info"] = {
                "tracked_stocks_count": len(self.tracked_stocks),
                "current_universes": getattr(self, '_current_universe_keys', []),
                "filter_stats": {
                    "last_filter_rate": self.universe_stats.get('filter_rate_percentage', 0),
                    "unique_tickers_processed": len(self.universe_stats.get('unique_tickers_processed', set())),
                    "unique_tickers_filtered": len(self.universe_stats.get('unique_tickers_filtered', set()))
                }
            }
            
            return latest
        
        return {}
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """
        Get history of calculated metrics.
        
        Returns:
            list: List of metric dictionaries
        """
        return self.buysell_market["calculations"].copy()
    
    '''
    def get_universe_info(self):
        """
        Get comprehensive information about currently tracked universe.
        
        Returns:
            dict: Information about the tracked stocks
        """
        current_time = time.time()
        
        return {
            'tracker_type': 'market',
            'tracked_stock_count': len(self.tracked_stocks),
            'current_universes': getattr(self, '_current_universe_keys', []),
            'tracking_window_seconds': self.window_seconds,
            'last_reset': getattr(self, 'last_reset_time', None),
            'filter_statistics': {
                'total_received': self.universe_stats['ticks_received'],
                'total_processed': self.universe_stats['ticks_processed'],
                'total_filtered': self.universe_stats['ticks_filtered'],
                'current_filter_rate': round((self.universe_stats['ticks_filtered'] / max(1, self.universe_stats['ticks_received'])) * 100, 1),
                'unique_tickers_seen': len(self.universe_stats['unique_tickers_received']),
                'last_stats_update': self.universe_stats['last_stats_log']
            },
            'performance_metrics': {
                'events_in_current_window': len(self.events),
                'last_calculation_time': self.buysell_market["calculations"][-1]["calc_time"] if self.buysell_market["calculations"] else None,
                'window_start': self.buysell_market["window_start"],
                'tracked_prices_count': len(self.buysell_market.get("last_prices", {}))
            }
        }
    '''
    def update_with_core_universe(self, core_universe_tickers: Set[str]) -> bool:
        """
        Update the market tracker to use TickStock Core Universe.
        
        Args:
            core_universe_tickers: Set of ticker symbols from TickStock Core Universe
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            old_count = len(self.tracked_stocks)
            
            # Update tracked stocks with core universe
            self.tracked_stocks = core_universe_tickers.copy()
            new_count = len(self.tracked_stocks)
            
            # Reset tracking data to start fresh with core universe
            self.reset_tracking()
            
            # Mark that we're using core universe
            self._using_core_universe = True
            self._core_universe_update_time = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating market tracker with core universe: {e}", exc_info=True)
            return False
    '''     
    def is_using_core_universe(self) -> bool:
        """
        Check if the market tracker is using TickStock Core Universe.
        
        Returns:
            bool: True if using core universe, False otherwise
        """
        return getattr(self, '_using_core_universe', False)

    '''
    def get_core_universe_integration_info(self) -> Dict[str, Any]:
        """
        Get information about core universe integration.
        
        Returns:
            dict: Integration information
        """
        return {
            'using_core_universe': self.is_using_core_universe(),
            'core_universe_update_time': getattr(self, '_core_universe_update_time', None),
            'tracked_stocks_count': len(self.tracked_stocks),
            'integration_status': 'active' if self.is_using_core_universe() else 'not_active'
        }

    '''