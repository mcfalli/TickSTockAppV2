"""
Enhanced Event Detection Utilities
Expanded utilities to reduce redundancy in event detectors.
Includes lightweight trend and surge detection functions.
"""

from typing import Dict, Any, Optional, Union, Tuple, List
from datetime import datetime, timedelta, time as datetime_time
import time
import pytz
from collections import deque
from config.logging_config import get_domain_logger, LogDomain
from src.presentation.converters.transport_models import StockData
from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

#from src.processing.detectors.trend_detector import TrendDetector
from src.processing.detectors.engines import TrendDetectionEngine
from src.processing.detectors.engines import extract_surge_buffer_from_state, extract_price_history_from_state, SurgeDetectionEngine


logger = get_domain_logger(LogDomain.CORE, 'event_detector_util')


#---------------------------------------------------
# Price and volume calculation utilities
#---------------------------------------------------
def calculate_vwap_divergence(price: float, vwap: Optional[float]) -> float:
    """Calculate percentage divergence from VWAP."""
    try:
        if vwap and vwap > 0:
            return ((price - vwap) / vwap) * 100
        return 0.0
    except Exception as e:
        logger.error(f"Error calculating VWAP divergence: {e}")
        return 0.0


def calculate_relative_volume(current_volume: Optional[float], 
                            average_volume: Optional[float]) -> float:
    """Calculate volume relative to average."""
    try:
        if average_volume and average_volume > 0 and current_volume:
            return current_volume / average_volume
        return 0.0
    except Exception as e:
        logger.error(f"Error calculating relative volume: {e}")
        return 0.0


def calculate_percent_change(current_price: float, 
                           base_price: Optional[float]) -> float:
    """Calculate percentage change from base price."""
    try:
        if base_price and base_price > 0:
            return ((current_price - base_price) / base_price) * 100
        return 0.0
    except Exception as e:
        logger.error(f"Error calculating percent change: {e}")
        return 0.0


def get_base_price(stock_data: Any,
                  market_status: str,
                  market_open_price: Optional[float] = None,
                  current_price: float = 0) -> tuple[float, str]:
    """Determine the base price for percentage calculations."""
    try:
        # Priority 1: Market open price for REGULAR session
        if market_status == "REGULAR" and market_open_price and market_open_price > 0:
            return market_open_price, "market_open_price"
        
        # Check if it's a dict (internal state from ticker_data)
        if isinstance(stock_data, dict):
            initial_seed = stock_data.get('initial_seed_price')
            last_price_val = stock_data.get('last_price', current_price)
        else:
            # It's a StockData object
            initial_seed = None
            last_price_val = stock_data.last_price if stock_data.last_price > 0 else current_price
        
        # Priority 2: Initial seed price (only exists in internal state dict)
        if initial_seed and initial_seed > 0:
            return initial_seed, "initial_seed_price"
        
        # Priority 3: Last known price
        if last_price_val and last_price_val > 0:
            return last_price_val, "last_price"
        
        # Fallback
        return current_price, "current_price"
        
    except Exception as e:
        logger.error(f"Error determining base price: {e}")
        return current_price, "fallback"


def map_direction_symbol(direction: str) -> str:
    """Map direction strings to display symbols."""
    direction_lower = direction.lower() if direction else ''
    if direction_lower in ['up', 'bullish', 'upward']:
        return '↑'
    elif direction_lower in ['down', 'bearish', 'downward']:
        return '↓'
    else:
        return '→'


def generate_event_label(event_type: str, ticker: str, **kwargs) -> str:
    """Generate human-readable event labels."""
    try:
        event_type_lower = event_type.lower()
        
        if event_type_lower in ['high', 'session_high']:
            count = kwargs.get('count', 0)
            #return f"{ticker} HIGH #{count}"
            return f"HIGH #{count}"
            
        elif event_type_lower in ['low', 'session_low']:
            count = kwargs.get('count', 0)
            #return f"{ticker} LOW #{count}"
            return f" LOW #{count}"
            
        elif event_type_lower == 'trend':
            direction = kwargs.get('direction', '→')
            strength = kwargs.get('strength', 'weak')
            #return f"{ticker} TREND {direction} {strength}"
            return f"TREND {direction} {strength}"
            
        elif event_type_lower == 'surge':
            direction = kwargs.get('direction', '→')
            magnitude = kwargs.get('magnitude', 0)
            trigger_type = kwargs.get('trigger_type', 'unknown')
            #return f"{ticker} SURGE {direction} {magnitude:.1f}% {trigger_type}"
            #return f"SURGE {direction} {magnitude:.1f}% {trigger_type}"
            return f"SURGE {direction} {trigger_type}"
            
        else:
            # Default fallback
            price = kwargs.get('price', 0)
            #return f"{ticker} {event_type.upper()} at ${price:.2f}"
            return f"{event_type.upper()} at ${price:.2f}"
            
    except Exception as e:
        logger.error(f"Error generating event label: {e}")
        #return f"{ticker} {event_type}"
        return f"{event_type}"


def calculate_price_momentum(prices: list, window: int = 5) -> float:
    """Calculate simple price momentum."""
    try:
        if not prices or len(prices) < 2:
            return 0.0
            
        # Use up to 'window' most recent prices
        recent_prices = prices[:window]
        
        # Calculate average change
        changes = []
        for i in range(len(recent_prices) - 1):
            if recent_prices[i+1] > 0:
                change = (recent_prices[i] - recent_prices[i+1]) / recent_prices[i+1]
                changes.append(change)
        
        if changes:
            avg_change = sum(changes) / len(changes)
            # Normalize to -1 to 1 range
            return max(-1, min(1, avg_change * 10))
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Error calculating momentum: {e}")
        return 0.0
    

def detect_reversal(current_event_type: str, previous_event_type: str) -> bool:
    """Detect if current event represents a reversal from previous event."""
    if not previous_event_type:
        return False
        
    current_lower = current_event_type.lower()
    previous_lower = previous_event_type.lower()
    
    # High after low or low after high is a reversal
    if ('high' in current_lower and 'low' in previous_lower) or \
       ('low' in current_lower and 'high' in previous_lower):
        return True
    
    return False

#---------------------------------------------------
# Market context utilities
#---------------------------------------------------
def get_market_context(timestamp, market_status):
    """Get detailed market context for any timestamp"""
    
    if market_status != "REGULAR":
        return {
            'status': market_status,
            'period': market_status.lower(),
            'minutes_into_session': 0,
            'volatility_multiplier': 3.0 if market_status in ["PRE", "POST"] else 1.0
        }
    
    # Calculate minutes since 9:30 AM ET
    market_open = timestamp.replace(hour=9, minute=30, second=0)
    minutes_since_open = (timestamp - market_open).total_seconds() / 60
    
    # Determine period
    if minutes_since_open < 30:
        period = "opening_30"
        volatility_multiplier = 2.0
    elif minutes_since_open < 60:
        period = "opening_hour"
        volatility_multiplier = 1.5
    elif 120 < minutes_since_open < 240:
        period = "midday"
        volatility_multiplier = 0.8
    elif minutes_since_open > 360:
        period = "closing_30"
        volatility_multiplier = 1.5
    else:
        period = "regular"
        volatility_multiplier = 1.0
    
    return {
        'status': market_status,
        'period': period,
        'minutes_into_session': minutes_since_open,
        'volatility_multiplier': volatility_multiplier
    }

def get_market_period_detailed(timestamp: datetime, timezone: str = 'US/Eastern') -> str:
    """
    Determine detailed market period from timestamp.
    
    Returns one of:
    - 'PREMARKET': 4:00 AM - 9:30 AM ET
    - 'OPENING': 9:30 AM - 9:45 AM ET  # CHANGED from 10:00 AM
    - 'MIDDAY': 9:45 AM - 3:30 PM ET   # CHANGED from 10:00 AM
    - 'CLOSING': 3:30 PM - 4:00 PM ET
    - 'AFTERHOURS': 4:00 PM - 8:00 PM ET
    - 'CLOSED': All other times
    """
    try:
        # Ensure we have a timezone-aware datetime
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        
        # Convert to Eastern timezone
        tz = pytz.timezone(timezone)
        if timestamp.tzinfo is None:
            timestamp = tz.localize(timestamp)
        else:
            timestamp = timestamp.astimezone(tz)
        
        # Get time only
        current_time = timestamp.time()
        
        # Define market periods (in Eastern Time)
        premarket_start = datetime_time(4, 0)     # 4:00 AM
        market_open = datetime_time(9, 30)        # 9:30 AM
        opening_end = datetime_time(9, 45)        # 9:45 AM - CHANGED from 10:00 AM
        closing_start = datetime_time(15, 30)     # 3:30 PM
        market_close = datetime_time(16, 0)       # 4:00 PM
        afterhours_end = datetime_time(20, 0)     # 8:00 PM
        
        # Determine period
        if premarket_start <= current_time < market_open:
            return 'PREMARKET'
        elif market_open <= current_time < opening_end:
            return 'OPENING'
        elif opening_end <= current_time < closing_start:
            return 'MIDDAY'
        elif closing_start <= current_time < market_close:
            return 'CLOSING'
        elif market_close <= current_time < afterhours_end:
            return 'AFTERHOURS'
        else:
            return 'CLOSED'
            
    except Exception as e:
        logger.error(f"Error determining market period: {e}")
        # Default to MIDDAY on error (most conservative)
        return 'MIDDAY'
    
def handle_market_status_change(state: Dict[str, Any],
                              new_status: str,
                              price: float) -> bool:
    """
    Handle market status transition.
    
    Args:
        state: Current state dictionary to update
        new_status: New market status
        price: Current price for reset
        
    Returns:
        True if status changed, False otherwise
    """
    if state.get('market_status') == new_status:
        return False
        
    # Save previous values
    state['last_market_status'] = state.get('market_status')
    state['market_status'] = new_status
    
    # Save previous highs/lows before reset
    previous_high = state.get('session_high')
    previous_low = state.get('session_low')
    state['previous_high'] = previous_high if previous_high != float('-inf') else None
    state['previous_low'] = previous_low if previous_low != float('inf') else None
    
    # Reset session values
    state['session_high'] = price
    state['session_low'] = price
    state['current_high'] = price
    state['current_low'] = price
    state['high_event_emitted'] = False
    state['low_event_emitted'] = False
    
    logger.info(f"Market status changed: {state['last_market_status']} -> {new_status}")
    
    return True
#---------------------------------------------------
#---------------------------------------------------


#---------------------------------------------------
# Timestamp normalization utility
#---------------------------------------------------
def normalize_timestamp(last_update: Any) -> float:
    """
    Normalize various timestamp formats to Unix timestamp (float).
    
    Args:
        last_update: Timestamp in various formats (datetime, string, float, None)
        
    Returns:
        Unix timestamp as float
    """
    if last_update is None:
        return 0.0  # Return 0 for None, not current time
        
    if isinstance(last_update, (int, float)):
        return float(last_update)
        
    if isinstance(last_update, datetime):
        return last_update.timestamp()
        
    if isinstance(last_update, str):
        try:
            # Parse ISO format string to datetime, then to float
            dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            return dt.timestamp()
        except ValueError:
            logger.warning(f"Failed to parse timestamp string: {last_update}")
            return 0.0  # Return 0, not current time
    
    # Fallback for unknown types
    logger.warning(f"Unknown timestamp type: {type(last_update)}, returning 0")
    return 0.0  # Return 0, not current time


#---------------------------------------------------



def initialize_ticker_state(ticker: str,
                          price: float,
                          market_status: str,
                          market_open_price: Optional[float],
                          timestamp: float,
                          tick_data: Any) -> Dict[str, Any]:
    """
    Create initial state dict for a new ticker.
    
    Args:
        ticker: Stock ticker symbol
        price: Current price
        market_status: Market status (REGULAR, PRE, POST)
        market_open_price: Market open price if available
        timestamp: Current timestamp
        tick_data: TickData object with additional fields
        
    Returns:
        Initialized state dictionary
    """
    # Ensure timestamp is float
    timestamp_float = normalize_timestamp(timestamp)
    current_time = time.time()
    
    # Determine initial high/low values
    if market_status == "REGULAR" and market_open_price and market_open_price > 0:
        initial_high = market_open_price
        initial_low = market_open_price
        initial_seed = market_open_price
    else:
        initial_high = price
        initial_low = price
        initial_seed = price
    
    state = {
        # Core price tracking
        "session_high": initial_high,
        "session_low": initial_low,
        "last_price": price,
        "market_open_price": market_open_price or price,
        "initial_seed_price": initial_seed,
        
        # Event tracking
        "high_event_emitted": False,
        "low_event_emitted": False,
        "high_count": 0,
        "low_count": 0,

        # Event tracking enhancement
        "last_event_type": None,      # 'high' or 'low'
        "last_event_time": None,      # Will be float when set
        "last_event_price": None,
        "event_history": deque(maxlen=10),  # Recent events for pattern detection
        
        # Reversal tracking
        "last_reversal": None,
        "reversal_count": 0,
        
        # Significance tracking
        "last_significance_score": 0,        
        
        # State tracking - ALL TIMESTAMPS AS FLOATS
        "last_update": current_time,  # Use current time as float
        "market_status": market_status,
        "last_market_status": market_status,
        "session_start_time": timestamp_float,  # Store as float
        
        # Historical tracking
        "previous_high": None,
        "previous_low": None,
        "current_high": initial_high,
        "current_low": initial_low,
        
        # Tick data fields
        "tick_high": getattr(tick_data, 'tick_high', None),
        "tick_low": getattr(tick_data, 'tick_low', None),
        "tick_close": getattr(tick_data, 'tick_close', None),
        "tick_open": getattr(tick_data, 'tick_open', None),
        "tick_volume": getattr(tick_data, 'tick_volume', None),
        "volume": getattr(tick_data, 'volume', None),
        "tick_vwap": getattr(tick_data, 'tick_vwap', None),
        "vwap": getattr(tick_data, 'vwap', None),
        "tick_trade_size": getattr(tick_data, 'tick_trade_size', None),
        
        # Analytics fields
        "volume_history": [],
        "average_volume": None,
        "percent_change": 0.0,
        "calc_details": {}
    }

    return state

def update_ticker_state(state: Dict[str, Any],
                       tick_data: Any,
                       price: float,
                       current_time: Optional[float] = None) -> None:
    """
    Update ticker state with new tick data (in-place update).
    
    Args:
        state: Current state dictionary to update
        tick_data: TickData object with new values
        price: Current price
        current_time: Current timestamp (defaults to time.time())
    """
    # Ensure we're using float timestamp
    if current_time is None:
        current_time = time.time()
    else:
        current_time = normalize_timestamp(current_time)
        
    # Update core fields with float timestamp
    state['last_price'] = price
    state['last_update'] = current_time  # Store as float
    
    # Update tick data fields
    tick_fields = [
        'tick_high', 'tick_low', 'tick_close', 'tick_open',
        'tick_volume', 'volume', 'tick_vwap', 'vwap', 'tick_trade_size'
    ]
    
    for field in tick_fields:
        if hasattr(tick_data, field):
            state[field] = getattr(tick_data, field)
            
    # Update volume history
    volume = getattr(tick_data, 'volume', None)
    if volume and volume > 0:
        if 'volume_history' not in state:
            state['volume_history'] = []
            
        state['volume_history'].append(volume)
        
        # Keep last 20 volume points
        if len(state['volume_history']) > 20:
            state['volume_history'] = state['volume_history'][-20:]
        
        # Calculate average volume
        if len(state['volume_history']) >= 5:
            state['average_volume'] = sum(state['volume_history']) / len(state['volume_history'])




def create_calculation_details(price: float,
                             base_price: float,
                             base_price_source: str,
                             percent_change: float,
                             market_status: str,
                             session_start: float) -> Dict[str, Any]:
    """
    Create standardized calculation details dictionary.
    
    Args:
        price: Current price
        base_price: Base price used for calculations
        base_price_source: Source of base price
        percent_change: Calculated percent change
        market_status: Current market status
        session_start: Session start timestamp (as float)
        
    Returns:
        Calculation details dictionary
    """
    # Ensure session_start is float
    session_start_float = normalize_timestamp(session_start)
    
    return {
        'base_price': base_price,
        'base_price_source': base_price_source,
        'price_change_amount': price - base_price,
        'percent_change': percent_change,
        'percent_change_formula': f"(({price} - {base_price}) / {base_price}) * 100" if base_price > 0 else "N/A (base_price=0)",
        'market_status': market_status,
        'session_start': session_start_float  # Store as float
    }

#---------------------------------------------------
# Trend detection utilities
#----------------------------------------------------
def check_trend_conditions(stock_data: Any,
                          price: float,
                          vwap: Optional[float] = None,
                          volume: Optional[float] = None,
                          config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Lightweight trend detection check using TrendDetectionEngine.
    Now includes warm-up period and minimum history checks with fixed timestamp handling.
    All timestamps are handled as floats (Unix seconds) for consistency.
    """
    # Try to get ticker from stock_data for logging
    ticker = "UNKNOWN"
    if isinstance(stock_data, dict):
        ticker = stock_data.get('ticker', 'UNKNOWN')
    elif hasattr(stock_data, 'ticker'):
        ticker = stock_data.ticker
    
    try:
        # Config should be passed from the detector
        if config is None:
            config = {}
        
        # Extract timing requirements from config
        min_history_required = config.get('TREND_MIN_HISTORY_POINTS_REQUIRED', 30)
        min_points_per_window = config.get('TREND_MIN_DATA_POINTS_PER_WINDOW', 10)
        warmup_period_seconds = config.get('TREND_WARMUP_PERIOD_SECONDS', 180)  # 3 minutes default
        
        # Extract price history
        price_history = extract_price_history_from_state(stock_data)
        
        # Check minimum history requirement
        if len(price_history) < min_history_required:
            return {
                'trend_detected': False,
                'trend_info': None,
                'reason': 'insufficient_history',
                'data_points': len(price_history),
                'required': min_history_required
            }
        
        # Check warm-up period
        if price_history and len(price_history) > 0:
            first_point_time = price_history[0]['timestamp']
            current_time = time.time()
            
            # FIXED: Ensure we're comparing floats to floats
            # normalize_timestamp handles all conversion cases
            first_point_float = normalize_timestamp(first_point_time)
            
            ticker_age_seconds = current_time - first_point_float
            
            if ticker_age_seconds < warmup_period_seconds:
                return {
                    'trend_detected': False,
                    'trend_info': None,
                    'reason': 'warmup_period',
                    'ticker_age': ticker_age_seconds,
                    'warmup_required': warmup_period_seconds
                }
        
        # Use float timestamp for consistency with stored data
        current_time = time.time()
        
        # Add current data point to history for calculation
        temp_history = price_history.copy()
        temp_history.append({
            'price': price,
            'vwap': vwap,
            'volume': volume,
            'timestamp': current_time  # Always use float timestamp
        })
        
        # Calculate trends using engine - pass full config
        trend_data = TrendDetectionEngine.calculate_multi_window_trends(
            price_history=temp_history,
            current_time=current_time,
            config=config
        )
        
        # Evaluate conditions - engine uses config internally
        conditions = TrendDetectionEngine.evaluate_trend_conditions(
            trend_data=trend_data,
            config=config
        )
        
        if conditions['is_trend']:
            result = {
                'trend_detected': True,
                'trend_info': {
                    'direction': conditions['raw_direction'],
                    'strength': conditions['trend_strength'],
                    'score': conditions['score']
                }
            }
            return result
        
        return {
            'trend_detected': False,
            'trend_info': None,
            'score': conditions.get('score', 0)
        }
        
    except Exception as e:
        logger.error(f"Error in check_trend_conditions: {e}", exc_info=True)
        return {
            'trend_detected': False,
            'trend_info': None,
            'error': str(e)
        }
    
def get_price_bucket(price: float) -> str:
    """
    Categorize stock by price range.
    
    Returns one of:
    - 'PENNY': $0 - $10
    - 'LOW': $10 - $50
    - 'MID': $50 - $200
    - 'HIGH': $200 - $500
    - 'ULTRA': $500+
    """
    try:
        if price < 10:
            return 'PENNY'
        elif price < 50:
            return 'LOW'
        elif price < 200:
            return 'MID'
        elif price < 500:
            return 'HIGH'
        else:
            return 'ULTRA'
    except Exception as e:
        logger.error(f"Error determining price bucket: {e}")
        # Default to MID on error (conservative)
        return 'MID'


def calculate_volatility_category(price_history: list, window_seconds: int = 300) -> str:
    """
    Categorize stock volatility based on recent price movement.
    
    Args:
        price_history: List of price data points with timestamps
        window_seconds: Time window to analyze (default 5 minutes)
    
    Returns:
        'HIGH', 'NORMAL', or 'LOW' volatility
    """
    try:
        if not price_history or len(price_history) < 3:
            return 'NORMAL'
        
        # Get recent data points within window
        current_time = time.time()
        window_start = current_time - window_seconds
        
        recent_prices = []
        for point in price_history:
            point_time = point.get('timestamp', 0)
            if isinstance(point_time, datetime):
                point_time = point_time.timestamp()
            
            if point_time >= window_start:
                recent_prices.append(point['price'])
        
        if len(recent_prices) < 3:
            return 'NORMAL'
        
        # Calculate standard deviation as percentage of mean
        import statistics
        mean_price = statistics.mean(recent_prices)
        std_dev = statistics.stdev(recent_prices)
        
        if mean_price > 0:
            volatility_pct = (std_dev / mean_price) * 100
            
            # Categorize based on percentage volatility
            if volatility_pct > 2.0:
                return 'HIGH'
            elif volatility_pct < 0.5:
                return 'LOW'
            else:
                return 'NORMAL'
        
        return 'NORMAL'
        
    except Exception as e:
        logger.error(f"Error calculating volatility category: {e}")
        return 'NORMAL'
#---------------------------------------------------
#---------------------------------------------------



#---------------------------------------------------
# Surge detection utilities
#----------------------------------------------------

def check_surge_conditions(stock_data: Any,
                          price: float,
                          volume: Optional[float] = None,
                          tick_volume: Optional[float] = None,
                          config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Lightweight surge detection check using SurgeDetectionEngine.
    
    Args:
        stock_data: StockData object or state dictionary
        price: Current price
        volume: Current volume
        tick_volume: Tick volume (preferred over volume)
        config: Configuration dict (should be passed from detector)
        
    Returns:
        Dict with surge detection results for flagging
    """
    # Try to get ticker from stock_data for logging
    ticker = "UNKNOWN"
    if isinstance(stock_data, dict):
        ticker = stock_data.get('ticker', 'UNKNOWN')
    elif hasattr(stock_data, 'ticker'):
        ticker = stock_data.ticker
    
    try:
        # Config should be passed from the detector
        if config is None:
            config = {}
        
        # Extract the minimum data points requirement from config
        min_data_points = config.get('SURGE_MIN_DATA_POINTS', 3)
        
        # Extract surge buffer
        buffer = extract_surge_buffer_from_state(stock_data)
        
        if len(buffer) < min_data_points:
            return {
                'surge_detected': False,
                'surge_info': None,
                'reason': 'insufficient_data',
                'buffer_size': len(buffer),
                'required': min_data_points
            }
        
        # Determine actual volume
        actual_volume = tick_volume if tick_volume is not None and tick_volume > 0 else volume
        current_time = time.time()
        
        # Calculate metrics using engine - pass full config
        metrics = SurgeDetectionEngine.calculate_surge_metrics(
            buffer=buffer,
            current_price=price,
            current_volume=actual_volume,
            current_time=current_time,
            config=config
        )
        
        # Evaluate conditions using engine - uses config internally
        conditions = SurgeDetectionEngine.evaluate_surge_conditions(
            metrics=metrics,
            price=price,
            config=config
        )
        
        if conditions['is_surge']:
            result = {
                'surge_detected': True,
                'surge_info': {
                    'direction': metrics['direction'],
                    'trigger_type': conditions['trigger_type'],
                    'magnitude': abs(metrics['price_change_pct']),
                    'score': conditions['surge_score'],
                    'strength': conditions['surge_strength']
                }
            }
            return result
        
        return {
            'surge_detected': False,
            'surge_info': None,
            'price_change_pct': metrics['price_change_pct'],
            'volume_multiplier': metrics['volume_multiplier']
        }
        
    except Exception as e:
        logger.error(f"Error in check_surge_conditions: {e}", exc_info=True)
        return {
            'surge_detected': False,
            'surge_info': None,
            'error': str(e)
        }
    

def get_surge_price_band(price: float, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get price band configuration for surge detection.
    Returns: Dict with 'name', 'price_pct', 'dollar_threshold'
    """
    try:
        # Get price band thresholds from config
        penny_max = config.get('SURGE_PRICE_BAND_PENNY_MAX', 10)
        low_max = config.get('SURGE_PRICE_BAND_LOW_MAX', 50)
        mid_max = config.get('SURGE_PRICE_BAND_MID_MAX', 200)
        high_max = config.get('SURGE_PRICE_BAND_HIGH_MAX', 500)
        
        if price < penny_max:
            return {
                'name': 'PENNY',
                'price_pct': config.get('SURGE_PRICE_BAND_PENNY_PCT', 3.0),
                'dollar': config.get('SURGE_PRICE_BAND_PENNY_DOLLAR', 0.10)
            }
        elif price < low_max:
            return {
                'name': 'LOW',
                'price_pct': config.get('SURGE_PRICE_BAND_LOW_PCT', 2.0),
                'dollar': config.get('SURGE_PRICE_BAND_LOW_DOLLAR', 0.50)
            }
        elif price < mid_max:
            return {
                'name': 'MID',
                'price_pct': config.get('SURGE_PRICE_BAND_MID_PCT', 1.5),
                'dollar': config.get('SURGE_PRICE_BAND_MID_DOLLAR', 1.00)
            }
        elif price < high_max:
            return {
                'name': 'HIGH',
                'price_pct': config.get('SURGE_PRICE_BAND_HIGH_PCT', 1.0),
                'dollar': config.get('SURGE_PRICE_BAND_HIGH_DOLLAR', 2.00)
            }
        else:
            return {
                'name': 'ULTRA',
                'price_pct': config.get('SURGE_PRICE_BAND_ULTRA_PCT', 0.5),
                'dollar': config.get('SURGE_PRICE_BAND_ULTRA_DOLLAR', 3.00)
            }
    except Exception as e:
        logger.error(f"Error determining surge price band: {e}")
        # Default to MID on error
        return {'name': 'MID', 'price_pct': 1.5, 'dollar': 1.00}


def calculate_surge_volatility(buffer: deque, lookback_seconds: int = 30) -> str:
    """
    Calculate recent volatility from surge buffer.
    Returns: 'HIGH', 'NORMAL', 'LOW'
    """
    try:
        if not buffer or len(buffer) < 3:
            return 'NORMAL'
        
        # Get current time for comparison
        current_time = time.time()
        lookback_start = current_time - lookback_seconds
        
        # Get recent prices within lookback window
        recent_prices = []
        for point in buffer:
            point_time = point.get('timestamp', 0)
            
            # Handle both datetime and timestamp formats
            if isinstance(point_time, datetime):
                point_time = point_time.timestamp()
            else:
                point_time = float(point_time)
            
            if point_time >= lookback_start:
                recent_prices.append(point['price'])
        
        # Need at least 3 prices for meaningful calculation
        if len(recent_prices) < 3:
            return 'NORMAL'
        
        # Calculate standard deviation as percentage of mean
        import statistics
        try:
            mean_price = statistics.mean(recent_prices)
            std_dev = statistics.stdev(recent_prices)
            
            if mean_price > 0:
                volatility_pct = (std_dev / mean_price) * 100
                
                # Classify volatility
                if volatility_pct > 2.0:
                    return 'HIGH'
                elif volatility_pct < 0.5:
                    return 'LOW'
                else:
                    return 'NORMAL'
            else:
                return 'NORMAL'
                
        except statistics.StatisticsError:
            # Not enough variation for stdev calculation
            return 'LOW'
            
    except Exception as e:
        logger.error(f"Error calculating surge volatility: {e}")
        return 'NORMAL'



#---------------------------------------------------
#---------------------------------------------------


def _get_simple_price_threshold(price: float, config: Dict[str, Any]) -> float:
    """
    Get simple price threshold based on price level.
    
    Args:
        price: Current price
        config: Configuration dictionary
        
    Returns:
        Threshold percentage
    """
    # Simple threshold matrix
    if price < 1.0:
        return 7.0  # 7% for penny stocks
    elif price < 5.0:
        return 5.0  # 5% for low-priced stocks
    elif price < 25.0:
        return 4.0  # 4% for mid-priced stocks
    elif price < 100.0:
        return 3.0  # 3% for higher-priced stocks
    else:
        return 2.0  # 2% for expensive stocks