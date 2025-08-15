# market_analytics/memory_analytics.py
"""
FIXED Sprint 1: In-Memory Market Analytics Handler

Fixed to accumulate data and create single aggregated record every 10 seconds.
Implements EMA weighted and non-weighted calculations.

Key Changes:
- Accumulate tick data in buffers instead of storing every tick
- Create single aggregated record every 10 seconds
- Implement EMA weighted (α=0.3) and non-weighted (simple) averages
- Only 'core' universe data saves to database
"""
import threading
import time
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'memory_analytics')

class InMemoryAnalytics:
    """
    FIXED: Thread-safe in-memory analytics with accumulation → aggregation → single DB record.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with FIXED accumulation logic for Sprint 1."""
        self.lock = threading.Lock()
        self.config = config or {}
        
        # FIXED: Configuration for 10-second aggregation (Sprint 1)
        self.aggregation_interval_seconds = self.config.get('ANALYTICS_DATABASE_SYNC_SECONDS', 10)
        self.gauge_alpha = self.config.get('ANALYTICS_GAUGE_ALPHA', 0.3)
        self.vertical_base_alpha = self.config.get('ANALYTICS_VERTICAL_BASE_ALPHA', 0.2)
        
        # FIXED: Accumulation buffers instead of storing every tick
        self.core_accumulator = {
            'net_scores': deque(),
            'activity_counts': deque(), 
            'buying_counts': deque(),
            'selling_counts': deque(),
            'activity_levels': deque(),
            'timestamps': deque(),
            'tick_count': 0,
            'last_aggregation': time.time(),
            'session_calculation_count': 0
        }
        
        # EMA state tracking
        self.ema_state = {
            'gauge_ema': None,
            'vertical_ema': None,
            'buying_ratio_ema': None,
            'max_activity_seen': 1
        }
        
        # Historical data for simple averages
        self.historical_data = {
            '10sec': deque(maxlen=1),   # Last 10 seconds (1 data point)
            '60sec': deque(maxlen=6),   # Last 60 seconds (6 × 10-second intervals)
            '300sec': deque(maxlen=30)  # Last 300 seconds (30 × 10-second intervals)
        }
        
        # FIXED: Database sync tracking - only 1 record per interval
        self.pending_database_record = None
        self.session_date = None
        self.dirty_flag = False
        
        # Performance tracking
        self.stats = {
            'ticks_accumulated': 0,
            'aggregations_performed': 0,
            'database_records_created': 0,
            'last_aggregation_time': 0,
            'average_operation_time_ms': 0.0
        }
        
    
    def set_session_date(self, session_date: date):
        """Set session date and reset accumulation."""
        with self.lock:
            if self.session_date != session_date:
                self.session_date = session_date
                self._reset_session_data()
    
    def _reset_session_data(self):
        """Reset session data for new trading day."""
        self.core_accumulator['session_calculation_count'] = 0
        self.core_accumulator['last_aggregation'] = time.time()
        self.ema_state = {
            'gauge_ema': None,
            'vertical_ema': None, 
            'buying_ratio_ema': None,
            'max_activity_seen': 1
        }
        self.historical_data['10sec'].clear()
        self.historical_data['60sec'].clear()
        self.historical_data['300sec'].clear()
        
    
    def record_market_calculation(self, analytics_data: Dict[str, Any]) -> bool:
        """
        FIXED: Accumulate market data instead of storing every tick.
        
        Args:
            analytics_data: Market analytics data from BuySellMarketTracker
            
        Returns:
            bool: True if accumulated successfully
        """
        start_time = time.time()
        
        try:
            with self.lock:
                if not self.session_date:
                    logger.warning("No session date set - cannot accumulate analytics")
                    return False
                
                # FIXED: Accumulate in buffers instead of storing every record
                self._accumulate_tick_data(analytics_data)
                
                # Check if it's time to aggregate (every 10 seconds)
                current_time = time.time()
                if self._should_create_aggregated_record(current_time):
                    self._create_aggregated_database_record(current_time)
                
                # Update stats
                self.stats['ticks_accumulated'] += 1
                operation_time = (time.time() - start_time) * 1000
                self.stats['average_operation_time_ms'] = (
                    (self.stats['average_operation_time_ms'] * (self.stats['ticks_accumulated'] - 1) + operation_time) /
                    self.stats['ticks_accumulated']
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error accumulating market data: {e}")
            return False
    
    def _accumulate_tick_data(self, analytics_data: Dict[str, Any]):
        """
        FIXED: Accumulate tick data in buffers for later aggregation.
        
        Args:
            analytics_data: Individual tick analytics data
        """
        
        # Extract key metrics
        net_score = analytics_data.get('market_net_score', 0)
        activity_count = analytics_data.get('market_activity_count', 0)
        buying_count = analytics_data.get('market_buying_count', 0)
        selling_count = analytics_data.get('market_selling_count', 0)
        activity_level = analytics_data.get('market_activity_level', 'Low')
        

        # Add to accumulation buffers
        self.core_accumulator['net_scores'].append(net_score)
        self.core_accumulator['activity_counts'].append(activity_count)
        self.core_accumulator['buying_counts'].append(buying_count)
        self.core_accumulator['selling_counts'].append(selling_count)
        self.core_accumulator['activity_levels'].append(activity_level)
        self.core_accumulator['timestamps'].append(time.time())

        self.core_accumulator['tick_count'] += 1
        
        # Update max activity seen for volume weighting
        if activity_count > self.ema_state['max_activity_seen']:
            self.ema_state['max_activity_seen'] = activity_count
            
    
    def _should_create_aggregated_record(self, current_time: float) -> bool:
        """
        FIXED: Check if it's time to create single aggregated database record.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            bool: True if aggregation should be performed
        """
        time_since_last = current_time - self.core_accumulator['last_aggregation']
        has_data = self.core_accumulator['tick_count'] > 0
        
        return time_since_last >= self.aggregation_interval_seconds and has_data
    
    def _create_aggregated_database_record(self, current_time: float):
        """
        FIXED: Create single aggregated record from accumulated tick data.
        
        Args:
            current_time: Current timestamp
        """
        
        try:
            
            if not self.core_accumulator['net_scores']:
                
                return
            
            # Calculate current values (latest in window)
            current_net_score = self.core_accumulator['net_scores'][-1]
            current_activity_count = self.core_accumulator['activity_counts'][-1]
            current_buying_count = self.core_accumulator['buying_counts'][-1]
            current_selling_count = self.core_accumulator['selling_counts'][-1]
            current_activity_level = self.core_accumulator['activity_levels'][-1]
            
            # Calculate EMA weighted averages
            ema_calculations = self._calculate_ema_averages(current_net_score, current_activity_count)
            
            # Calculate simple averages
            simple_averages = self._calculate_simple_averages()
            
            # Create aggregated database record
            window_start = self.core_accumulator['timestamps'][0] if self.core_accumulator['timestamps'] else current_time
            window_end = current_time
            
            aggregated_record = {
                # Identity & Timing
                'session_date': self.session_date,
                'timestamp': datetime.fromtimestamp(current_time),
                'data_source': 'core', 

                # Current Values
                'current_net_score': current_net_score,
                'current_activity_level': current_activity_level,
                'current_buying_count': current_buying_count,
                'current_selling_count': current_selling_count,
                'current_activity_count': current_activity_count,
                
                # EMA Weighted Averages
                'ema_net_score_gauge': ema_calculations['gauge_ema'],
                'ema_net_score_vertical': ema_calculations['vertical_ema'],
                'ema_buying_ratio': ema_calculations['buying_ratio_ema'],
                
                # Simple Averages
                'avg_net_score_10sec': simple_averages['avg_10sec'],
                'avg_net_score_60sec': simple_averages['avg_60sec'],
                'avg_net_score_300sec': simple_averages['avg_300sec'],
                'avg_activity_count_60sec': simple_averages['avg_activity_60sec'],
                
                # Session Context
                'session_total_calculations': self.core_accumulator['session_calculation_count'] + 1,
                'records_aggregated': self.core_accumulator['tick_count'],
                'calculation_window_seconds': self.aggregation_interval_seconds,
                
                # Performance
                'calc_time_ms': (current_time - window_start) * 1000,
                'window_start_time': datetime.fromtimestamp(window_start),
                'window_end_time': datetime.fromtimestamp(window_end),
                
                # Universe Context
                'total_universe_size': 2800  # Core universe size
            }
            
            # FIXED: Store single record for database sync
            self.pending_database_record = aggregated_record
            self.dirty_flag = True
            
            # Update historical data for simple averages
            self._update_historical_data(current_net_score, current_activity_count)
            
            # Reset accumulation buffers
            self._reset_accumulation_buffers(current_time)
            
            # Update stats
            self.stats['aggregations_performed'] += 1
            self.stats['database_records_created'] += 1
            self.stats['last_aggregation_time'] = current_time
            

            
        except Exception as e:
            logger.error(f"Error creating aggregated record: {e}")
            
    
    def _calculate_ema_averages(self, current_net_score: float, current_activity_count: int) -> Dict[str, float]:
        """
        Calculate EMA weighted averages using Sprint 1 formulas.
        
        Args:
            current_net_score: Current net score
            current_activity_count: Current activity count
            
        Returns:
            dict: EMA calculations
        """
        # Gauge EMA (α = 0.3)
        if self.ema_state['gauge_ema'] is None:
            gauge_ema = current_net_score  # Bootstrap
        else:
            gauge_ema = (self.gauge_alpha * current_net_score + 
                        (1 - self.gauge_alpha) * self.ema_state['gauge_ema'])
        
        # Vertical EMA (volume-weighted α)
        volume_weight = current_activity_count / self.ema_state['max_activity_seen']
        weighted_alpha = self.vertical_base_alpha * (1 + volume_weight)
        weighted_alpha = min(weighted_alpha, 0.8)  # Clamp to 0.8
        
        if self.ema_state['vertical_ema'] is None:
            vertical_ema = current_net_score  # Bootstrap
        else:
            vertical_ema = (weighted_alpha * current_net_score + 
                           (1 - weighted_alpha) * self.ema_state['vertical_ema'])
        
        # Buying ratio EMA
        buying_ratio = 0.0
        if self.core_accumulator['buying_counts'] and self.core_accumulator['selling_counts']:
            total_activity = self.core_accumulator['buying_counts'][-1] + self.core_accumulator['selling_counts'][-1]
            if total_activity > 0:
                buying_ratio = self.core_accumulator['buying_counts'][-1] / total_activity
        
        if self.ema_state['buying_ratio_ema'] is None:
            buying_ratio_ema = buying_ratio
        else:
            buying_ratio_ema = (self.gauge_alpha * buying_ratio + 
                              (1 - self.gauge_alpha) * self.ema_state['buying_ratio_ema'])
        
        # Update EMA state
        self.ema_state.update({
            'gauge_ema': gauge_ema,
            'vertical_ema': vertical_ema,
            'buying_ratio_ema': buying_ratio_ema
        })
        
        return {
            'gauge_ema': gauge_ema,
            'vertical_ema': vertical_ema,
            'buying_ratio_ema': buying_ratio_ema,
            'volume_weight': volume_weight,
            'weighted_alpha': weighted_alpha
        }
    
    def _calculate_simple_averages(self) -> Dict[str, float]:
        """
        Calculate simple (non-weighted) averages for historical analysis.
        
        Returns:
            dict: Simple average calculations
        """
        # 10-second average (current window)
        avg_10sec = sum(self.core_accumulator['net_scores']) / len(self.core_accumulator['net_scores'])
        
        # 60-second average (from historical data)
        if self.historical_data['60sec']:
            avg_60sec = sum(self.historical_data['60sec']) / len(self.historical_data['60sec'])
        else:
            avg_60sec = avg_10sec
        
        # 300-second average (from historical data)
        if self.historical_data['300sec']:
            avg_300sec = sum(self.historical_data['300sec']) / len(self.historical_data['300sec'])
        else:
            avg_300sec = avg_10sec
        
        # Activity average (60 seconds)
        if self.historical_data['60sec']:
            # Use same length as net scores for activity data
            recent_activities = list(self.historical_data['60sec'])
            avg_activity_60sec = sum(recent_activities) / len(recent_activities)
        else:
            avg_activity_60sec = self.core_accumulator['activity_counts'][-1] if self.core_accumulator['activity_counts'] else 0
        
        return {
            'avg_10sec': avg_10sec,
            'avg_60sec': avg_60sec,
            'avg_300sec': avg_300sec,
            'avg_activity_60sec': avg_activity_60sec
        }
    
    def _update_historical_data(self, net_score: float, activity_count: int):
        """
        Update historical data deques for simple average calculations.
        
        Args:
            net_score: Current aggregated net score
            activity_count: Current activity count
        """
        # Add current aggregated values to historical data
        self.historical_data['10sec'].append(net_score)
        self.historical_data['60sec'].append(net_score)
        self.historical_data['300sec'].append(net_score)
    
    def _reset_accumulation_buffers(self, current_time: float):
        """
        Reset accumulation buffers after creating aggregated record.
        
        Args:
            current_time: Current timestamp
        """
        self.core_accumulator.update({
            'net_scores': deque(),
            'activity_counts': deque(),
            'buying_counts': deque(),
            'selling_counts': deque(),
            'activity_levels': deque(),
            'timestamps': deque(),
            'tick_count': 0,
            'last_aggregation': current_time,
            'session_calculation_count': self.core_accumulator['session_calculation_count'] + 1
        })
    
    def should_sync_to_database(self) -> bool:
        """
        FIXED: Check if single aggregated record is ready for database sync.
        
        Returns:
            bool: True if sync is needed
        """
        return self.dirty_flag and self.pending_database_record is not None
    
    def get_dirty_data_for_sync(self) -> Dict[date, List[Dict[str, Any]]]:
        """
        FIXED: Get single aggregated record for database sync.
        
        Returns:
            dict: Single aggregated record ready for database
        """
        with self.lock:
            if not self.should_sync_to_database():
                return {}
            
            # FIXED: Return single record instead of hundreds
            sync_data = {
                self.session_date: [self.pending_database_record]
            }
            
            # Clear dirty state
            self.pending_database_record = None
            self.dirty_flag = False
            
            return sync_data
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for Sprint 1 fixed implementation."""
        current_time = time.time()
        
        return {
            'sprint_1_fixed': True,
            'accumulation_performance': {
                'ticks_accumulated': self.stats['ticks_accumulated'],
                'aggregations_performed': self.stats['aggregations_performed'],
                'database_records_created': self.stats['database_records_created'],
                'average_operation_time_ms': self.stats['average_operation_time_ms'],
                'records_reduction_ratio': self.stats['ticks_accumulated'] / max(1, self.stats['database_records_created'])
            },
            'current_state': {
                'accumulated_ticks': self.core_accumulator['tick_count'],
                'time_until_next_aggregation': self.aggregation_interval_seconds - (current_time - self.core_accumulator['last_aggregation']),
                'has_pending_database_record': self.dirty_flag,
                'session_calculation_count': self.core_accumulator['session_calculation_count']
            },
            'ema_state': {
                'gauge_ema': self.ema_state['gauge_ema'],
                'vertical_ema': self.ema_state['vertical_ema'],
                'buying_ratio_ema': self.ema_state['buying_ratio_ema'],
                'max_activity_seen': self.ema_state['max_activity_seen']
            },
            'configuration': {
                'aggregation_interval_seconds': self.aggregation_interval_seconds,
                'gauge_alpha': self.gauge_alpha,
                'vertical_base_alpha': self.vertical_base_alpha
            }
        }
    
    def get_latest_gauge_analytics(self) -> Optional[Dict[str, Any]]:
        """
        🆕 SPRINT 2: Get latest gauge analytics data for WebSocket emission.
        
        Returns:
            dict: Latest gauge analytics or None if no data available
        """
        try:
            with self.lock:
                if self.ema_state['gauge_ema'] is None:
                    return None
                
                current_time = time.time()
                
                return {
                    'ema_net_score': float(self.ema_state['gauge_ema']),
                    'current_net_score': float(self.core_accumulator['net_scores'][-1]) if self.core_accumulator['net_scores'] else 0.0,
                    'alpha_used': self.gauge_alpha,
                    'sample_count': len(self.core_accumulator['net_scores']),
                    'timestamp': datetime.fromtimestamp(current_time).isoformat(),
                    'last_updated': datetime.fromtimestamp(current_time).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting latest gauge analytics: {e}")
            return None
    
    def get_latest_vertical_analytics(self) -> Optional[Dict[str, Any]]:
        """
        🆕 SPRINT 2: Get latest vertical analytics data for WebSocket emission.
        
        Returns:
            dict: Latest vertical analytics or None if no data available
        """
        try:
            with self.lock:
                if self.ema_state['vertical_ema'] is None:
                    return None
                
                current_time = time.time()
                current_activity = self.core_accumulator['activity_counts'][-1] if self.core_accumulator['activity_counts'] else 0
                volume_weight = current_activity / self.ema_state['max_activity_seen']
                weighted_alpha = self.vertical_base_alpha * (1 + volume_weight)
                weighted_alpha = min(weighted_alpha, 0.8)  # Clamp to 0.8
                
                return {
                    'ema_net_score': float(self.ema_state['vertical_ema']),
                    'current_weighted_score': float(self.core_accumulator['net_scores'][-1]) if self.core_accumulator['net_scores'] else 0.0,
                    'weighted_alpha': weighted_alpha,
                    'volume_weight': volume_weight,
                    'max_activity_seen': self.ema_state['max_activity_seen'],
                    'timestamp': datetime.fromtimestamp(current_time).isoformat(),
                    'last_updated': datetime.fromtimestamp(current_time).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting latest vertical analytics: {e}")
            return None