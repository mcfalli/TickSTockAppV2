from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import time
import pytz
from src.shared.utils import calculate_percentage_change
from collections import deque  
#from src.processing.detectors.trend_detector import TrendDetector
#from src.processing.detectors.surge_detector import SurgeDetector
from config.logging_config import get_domain_logger, LogDomain
from src.core.domain.market.tick import TickData 
from src.core.domain.events.highlow import HighLowEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.presentation.converters.transport_models import StockData

from src.core.domain.events.highlow import HighLowEvent
from src.processing.detectors.engines import HighLowDetectionEngine

from src.processing.detectors.utils import (
    calculate_vwap_divergence, 
    calculate_relative_volume,
    calculate_percent_change,
    get_base_price,
    map_direction_symbol,
    generate_event_label,
    detect_reversal,
    normalize_timestamp,
    initialize_ticker_state,
    update_ticker_state,
    handle_market_status_change,
    create_calculation_details
)

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = get_domain_logger(LogDomain.CORE, 'highlow_detector')

class HighLowDetector:
    def __init__(self, config, cache_control=None):
        """Initialize with enhanced configuration."""
        self.config = config
        self.cache_control = cache_control
        
        # ===== DETECTION PARAMETERS =====
        self.base_min_price_change = float(config.get('HIGHLOW_MIN_PRICE_CHANGE', 0.01))
        self.base_min_percent_change = float(config.get('HIGHLOW_MIN_PERCENT_CHANGE', 0.1))
        self.cooldown_seconds = float(config.get('HIGHLOW_COOLDOWN_SECONDS', 1))  # Very low default
        
        # ===== MARKET AWARENESS =====
        self.market_aware = config.get('HIGHLOW_MARKET_AWARE', True)
        self.extended_multiplier = float(config.get('HIGHLOW_EXTENDED_HOURS_MULTIPLIER', 2.0))
        self.opening_multiplier = float(config.get('HIGHLOW_OPENING_MULTIPLIER', 1.5))
        
        # ===== SIGNIFICANCE SCORING =====
        self.enable_significance = config.get('HIGHLOW_SIGNIFICANCE_SCORING', True)
        self.significance_volume_weight = float(config.get('HIGHLOW_SIGNIFICANCE_VOLUME_WEIGHT', 0.5))
        
        # ===== REVERSAL DETECTION =====
        self.track_reversals = config.get('HIGHLOW_TRACK_REVERSALS', True)
        self.reversal_window_seconds = float(config.get('HIGHLOW_REVERSAL_WINDOW', 300))  # 5 minutes
        
        # ===== STATE TRACKING =====
        self.ticker_data = {}
        self.last_emission_times = {}

    def reset_for_new_market_session(self, market_status):
        """Reset all tickers for new market session."""
        for ticker in self.ticker_data:
            # Save the current market_open_price before resetting
            market_open_price = self.ticker_data[ticker].get("market_open_price", 0)
            
            # Reset session values
            self.ticker_data[ticker]["session_high"] = float('-inf')
            self.ticker_data[ticker]["session_low"] = float('inf')
            self.ticker_data[ticker]["last_price"] = float('inf')
            self.ticker_data[ticker]["high_event_emitted"] = False
            self.ticker_data[ticker]["low_event_emitted"] = False
            self.ticker_data[ticker]["market_status"] = market_status
            self.ticker_data[ticker]["last_market_status"] = market_status
            
            # Restore the market_open_price
            self.ticker_data[ticker]["market_open_price"] = market_open_price
            # CORRECTED: Keep as None to indicate no update yet in new session
            self.ticker_data[ticker]["last_update"] = None

    def initialize_highlow_event_data(self, ticker, session_high=None, session_low=None, 
                                    market_status=None, last_price=None, market_open_price=None):
        """Initialize ticker data with provided values."""
        if ticker not in self.ticker_data:
            # Create default entry - CORRECTED: Keep datetime for backward compatibility here
            # since this is initialization and the original used datetime.now()
            self.ticker_data[ticker] = {
                "session_high": float('-inf'),
                "session_low": float('inf'),
                "last_price": None,
                "high_event_emitted": False,
                "low_event_emitted": False,
                "last_update": datetime.now(),  # Keep original behavior
                "last_market_status": market_status,
                "market_status": market_status,
                "market_open_price": 0
            }

        ticker_info = self.ticker_data[ticker]
        
        # Market open price is used for initial values during REGULAR session
        if market_open_price is not None:
            ticker_info["market_open_price"] = market_open_price
            
            # If we're in regular market hours and don't have high/low values yet,
            # use the market_open_price as initial high/low values
            if (market_status == "REGULAR" and 
                (ticker_info["session_high"] == float('-inf') or 
                ticker_info["session_low"] == float('inf'))):
                if session_high is None:
                    ticker_info["session_high"] = market_open_price
                if session_low is None:
                    ticker_info["session_low"] = market_open_price
        
        # SPRINT 41 FIX: Only update session values if they improve on existing values
        # This ensures monotonic behavior (highs only increase, lows only decrease)
        if session_high is not None:
            # Only update if new high is greater than existing, or if uninitialized
            if ticker_info["session_high"] == float('-inf') or session_high > ticker_info["session_high"]:
                ticker_info["session_high"] = session_high
            
        if session_low is not None:
            # Only update if new low is less than existing, or if uninitialized
            if ticker_info["session_low"] == float('inf') or session_low < ticker_info["session_low"]:
                ticker_info["session_low"] = session_low
            
        if last_price is not None:
            ticker_info["last_price"] = last_price
        
        if market_status is not None:
            ticker_info["last_market_status"] = market_status
            ticker_info["market_status"] = market_status

    def detect_highlow(self, tick_data: TickData, stock_data: StockData):
        """
        TEMPORARY BYPASS: Process a stock tick event for event detection.
        PHASE 4: Now works exclusively with typed objects.
        
        TEMPORARY: Returns HIGH event for ALL ticks with real data
        
        Args:
            tick_data: TickData object containing the current tick
            stock_data: StockData object containing the stock state
        
        Returns:
            dict: Contains detected events and updated state
        """
        start_time = time.time()
        
        try:
            current_time = time.time()
            ticker = tick_data.ticker
            price = tick_data.price
            market_status = tick_data.market_status
            timestamp = tick_data.timestamp
            
            # TEMPORARY BYPASS: Initialize state normally but force event creation
            # Initialize or get ticker state
            if ticker not in self.ticker_data:
                from src.processing.detectors.utils import initialize_ticker_state
                self.ticker_data[ticker] = initialize_ticker_state(
                    ticker=ticker,
                    price=price,
                    market_status=market_status,
                    market_open_price=tick_data.market_open_price,
                    timestamp=timestamp,
                    tick_data=tick_data
                )
                internal_state = self.ticker_data[ticker]
            else:
                internal_state = self.ticker_data[ticker]
            
            # Get real base price calculation
            from src.processing.detectors.utils import get_base_price, calculate_percent_change
            base_price, base_price_source = get_base_price(
                stock_data=stock_data,
                market_status=market_status,
                market_open_price=tick_data.market_open_price,
                current_price=price
            )
            
            percent_change = calculate_percent_change(price, base_price)
            
            # Update session highs/lows normally
            internal_state['session_high'] = max(internal_state.get('session_high', price), price)
            internal_state['session_low'] = min(internal_state.get('session_low', price), price)
            internal_state['last_price'] = price
            
            # TEMPORARY BYPASS: Force creation of HIGH event for every tick
            from src.core.domain.events.highlow import HighLowEvent
            
            event = HighLowEvent(
                ticker=ticker,
                price=price,
                type='high',
                time=timestamp,
                direction='up',
                percent_change=percent_change,
                vwap=getattr(tick_data, 'vwap', None),
                volume=getattr(tick_data, 'volume', 0),
                session_high=internal_state['session_high'],
                session_low=internal_state['session_low'],
                trend_flag=getattr(stock_data, 'trend_flag', 'unknown'),
                surge_flag=getattr(stock_data, 'surge_flag', 'unknown'),
                is_initial=False,
                label=f"BYPASS-HIGH-{ticker}-{int(current_time)}"
            )
            
            result = {"events": [event]}
            return result
            
            # TRACE: Start of processing
            tracer.create_trace_event(
                ticker=ticker,
                component='HighLowEventDetector',
                action='detection_start',
                start_time=start_time,
                details={
                    'price': price,
                    'market_status': market_status
                }
            )

            # Initialize result structure
            result = {"events": []}
            
            #logger.info(f"🔍 DIAG-STOCK-TICK: Processing {ticker} @ ${price}, market_status={market_status}")
            
            # Initialize or get ticker state
            if ticker not in self.ticker_data:
                #logger.info(f"🔍 DIAG-STOCK-TICK: Initializing new ticker {ticker}")
                
                # Use utility to create initial state
                self.ticker_data[ticker] = initialize_ticker_state(
                    ticker=ticker,
                    price=price,
                    market_status=market_status,
                    market_open_price=tick_data.market_open_price,
                    timestamp=timestamp,
                    tick_data=tick_data
                )
                internal_state = self.ticker_data[ticker]
                
                # TRACE: Ticker initialized
                tracer.create_trace_event(
                    ticker=ticker,
                    component='HighLowEventDetector',
                    action='ticker_initialized',
                    start_time=start_time,
                    output_count=1,
                    details={
                        'initial_high': internal_state['session_high'],
                        'initial_low': internal_state['session_low'],
                        'market_status': market_status,
                        'market_open_price': tick_data.market_open_price,
                        'last_price': price,
                        'high_count': 0,
                        'low_count': 0
                    }
                )
                
                #logger.info(f"🔍 DIAG-STOCK-TICK: {ticker} initialized with high={internal_state['session_high']}, "
                #        f"low={internal_state['session_low']}")
                
            else:
                internal_state = self.ticker_data[ticker]
                
                #logger.debug(f"🔍 DIAG-STOCK-TICK: {ticker} state before - session_high={internal_state.get('session_high')}, "
                #            f"session_low={internal_state.get('session_low')}, last_price={internal_state.get('last_price')}")
                
            # Use the utility to get base price
            base_price, base_price_source = get_base_price(
                stock_data=stock_data,
                market_status=market_status,
                market_open_price=tick_data.market_open_price,
                current_price=price
            )
            
            # Calculate percent change
            percent_change = calculate_percent_change(price, base_price)
            
            #logger.debug(f"🔍 DIAG-STOCK-TICK: {ticker} base_price={base_price} ({base_price_source}), "
            #            f"percent_change={percent_change:.2f}%")
            
            # Store calculation details using utility
            internal_state['calc_details'] = create_calculation_details(
                price=price,
                base_price=base_price,
                base_price_source=base_price_source,
                percent_change=percent_change,
                market_status=market_status,
                session_start=internal_state.get('session_start_time', timestamp)
            )

            # Store percent_change in internal state and result
            internal_state['percent_change'] = percent_change
            result['percent_change'] = percent_change
            
            # Update volume history (handled by utility)
            update_ticker_state(internal_state, tick_data, price, current_time)

            # Check for market status change using utility
            market_changed = handle_market_status_change(internal_state, market_status, price)
            if market_changed:
                result["market_status_changed"] = True
                logger.info(f"🔍 DIAG-STOCK-TICK: {ticker} session reset due to market status change")
            
            # Check for trend conditions (just get the flag, no events)
            trend_result = self._trend_detection(
                stock_data,  # Changed from stock_data
                ticker, price, 
                tick_data.vwap, tick_data.volume,
                tick_data.tick_vwap, tick_data.tick_volume, 
                tick_data.tick_trade_size
            )
            
            # Extract trend flag if detected
            trend_flag = None
            if trend_result and trend_result.get('trend_direction') not in ['→', None]:
                # Convert direction symbol to flag value
                direction = trend_result.get('trend_direction')
                if direction in ['↑', 'up']:
                    trend_flag = 'up'
                elif direction in ['↓', 'down']:
                    trend_flag = 'down'
            
            # Check for surge conditions (just get the flag, no events)
            surge_result = self._surge_detection(
                stock_data,  # Changed from stock_data
                ticker, price,
                tick_data.vwap, tick_data.volume,
                tick_data.tick_vwap, tick_data.tick_volume,
                tick_data.tick_trade_size
            )
            
            # Extract surge flag if detected
            surge_flag = None
            if surge_result and surge_result.get('surge_detected'):
                surge_info = surge_result.get('surge_info', {})
                direction = surge_info.get('direction')
                if direction == 'up':
                    surge_flag = 'up'
                elif direction == 'down':
                    surge_flag = 'down'
            
            # **Detect new highs/lows and apply trend/surge flags**
            high_low_result = self._highlow_event_detection(
                internal_state, ticker, price, market_status, timestamp, percent_change,
                trend_flag=trend_flag, surge_flag=surge_flag
            )
            
            if high_low_result and high_low_result.get('events'):
                result['events'].extend(high_low_result['events'])

            # Include current highs, lows, and percent change in result
            result['session_high'] = internal_state['session_high']
            result['session_low'] = internal_state['session_low']
            
            # LOG FINAL RESULT
            total_events = len(result.get('events', []))
            if total_events > 0:
                event_types = [event.type for event in result.get('events', [])]
                #logger.info(f"🔍 DIAG-STOCK-TICK: {ticker} FINAL RETURN: {total_events} events - {event_types}")
            
            # TRACE: Processing complete
            tracer.create_trace_event(
                ticker=ticker,
                component='HighLowEventDetector',
                action='detection_complete',
                start_time=start_time,
                output_count=len(result['events']),
                details={
                    'events_detected': len(result['events']),
                    'event_types': [e.type for e in result['events']],
                    'trend_flag': trend_flag,
                    'surge_flag': surge_flag
                }
            )

            return result
            
        except Exception as e:
            logger.error(f"Error in detect_highlow for {tick_data.ticker}: {e}", exc_info=True)
            
            # TRACE: Error
            tracer.create_trace_event(
                ticker=tick_data.ticker,
                component='HighLowEventDetector',
                action='detection_error',
                start_time=start_time,
                error=str(e),
                details={'error_type': type(e).__name__}
            )
            
            return {"events": [], "error": str(e)}
        
    
    def _highlow_event_detection(self, internal_state, ticker, price, market_status, 
                        timestamp, percent_change, trend_flag=None, surge_flag=None):
        """
        Enhanced high/low detection with all new features.
        
        Args:
            internal_state: Internal tracking dict from self.ticker_data[ticker]
            ticker: Stock symbol
            price: Current price
            market_status: Market status
            timestamp: Event timestamp
            percent_change: Calculated percent change
            trend_flag: 'up', 'down', or None
            surge_flag: 'up', 'down', or None
        """
        start_time = time.time()
        
        try:
            
            # FIXED: Ensure timestamp is float
            timestamp_float = normalize_timestamp(timestamp)
            
            #logger.info(f"🔍 DIAG-HL-DETECT: Called for {ticker} @ ${price} session_high={internal_state.get('session_high')}, session_low={internal_state.get('session_low')}")

            # SPRINT 41 SAFEGUARD: Validate session values are monotonic
            current_session_high = internal_state.get('session_high', float('-inf'))
            current_session_low = internal_state.get('session_low', float('inf'))
            
            # Log warning if we detect non-monotonic values
            if 'previous_session_high' in internal_state:
                if current_session_high < internal_state['previous_session_high']:
                    logger.error(f"SPRINT41 VIOLATION: Session high decreased from "
                            f"{internal_state['previous_session_high']} to {current_session_high}")
            
            if 'previous_session_low' in internal_state:
                if current_session_low > internal_state['previous_session_low']:
                    logger.error(f"SPRINT41 VIOLATION: Session low increased from {internal_state['previous_session_low']} to {current_session_low}")
            
            # Store for next check
            internal_state['previous_session_high'] = current_session_high
            internal_state['previous_session_low'] = current_session_low

            events = []
            calc_details = internal_state.get('calc_details', {})
            
            # Get price-based thresholds
            thresholds = HighLowDetectionEngine.get_price_thresholds(price, self.config)
            
            # Check cooldown
            if not self._check_emission_cooldown(ticker, internal_state):
                #logger.debug(f"🔍 DIAG-HL-DETECT: {ticker} - Skipping due to cooldown")
                return {'events': []}
            
            # Get current session counts
            session_high_count = internal_state.get('high_count', 0)
            session_low_count = internal_state.get('low_count', 0)
            
            # Determine if we should check for highs/lows
            last_price = internal_state.get('last_price')
            if last_price is not None:
                price_change_abs = abs(price - last_price)
                should_check = (
                    abs(percent_change) >= thresholds['min_percent_change'] or
                    price_change_abs >= thresholds['min_price_change']
                )
                
                if not should_check:
                    #logger.debug(f"🔍 DIAG-HL-DETECT: {ticker} - Change too small: {percent_change:.2f}% < {thresholds['min_percent_change']}%, ${price_change_abs:.3f} < ${thresholds['min_price_change']}")
                    return {'events': []}
            
            # Check for new session high
            if price > internal_state['session_high']:
                
                previous_high = internal_state['session_high']
                is_initial = previous_high == float('-inf')
                
                #logger.info(f"🔍 DIAG-HL-DETECT: {ticker} NEW HIGH detected: ${price} > ${previous_high}")
                
                # Increment count
                internal_state['high_count'] = internal_state.get('high_count', 0) + 1
                current_count = internal_state['high_count']
                
                # Update session counts
                session_high_count = internal_state['high_count']
                session_total_events = session_high_count + session_low_count
                
                # Detect reversal
                reversal_info = None
                if self.track_reversals:
                    reversal_info = self._detect_reversal_pattern(ticker, 'high', internal_state)
                    if reversal_info:
                        logger.info(f"🔄 REVERSAL: {ticker} - {reversal_info['type']} pattern detected")
                
                # Calculate significance
                avg_volume = internal_state.get('average_volume')
                volume = internal_state.get('volume', 0)
                significance_score = self._calculate_significance_score(
                    price, previous_high, volume, avg_volume, percent_change
                )
                
                # Update state with float timestamps
                internal_state['previous_high'] = previous_high if not is_initial else None
                internal_state['session_high'] = price
                internal_state['current_high'] = price
                internal_state['last_event_type'] = 'high'
                internal_state['last_event_time'] = time.time()  # FIXED: Store as float
                internal_state['last_event_price'] = price
                internal_state['last_significance_score'] = significance_score
                
                # Add to event history with float timestamp
                if 'event_history' not in internal_state:
                    internal_state['event_history'] = deque(maxlen=10)
                internal_state['event_history'].append({
                    'type': 'high',
                    'price': price,
                    'time': time.time(),  # FIXED: Store as float
                    'significance': significance_score
                })
                
                # Get VWAP and volume metrics
                vwap = internal_state.get('vwap')
                vwap_divergence = calculate_vwap_divergence(price, vwap)
                rel_volume = calculate_relative_volume(volume, avg_volume)
                
                # Calculate period_seconds for session events
                session_start = internal_state.get('session_start_time', timestamp_float)
                # FIXED: Ensure both are floats for subtraction
                session_start_float = normalize_timestamp(session_start)
                period_seconds = int(timestamp_float - session_start_float) if session_start else 0
                
                # Create typed HighLowEvent
                high_event = HighLowEvent(
                    ticker=ticker,
                    type='high',
                    price=price,
                    time=time.time(),
                    count=session_total_events,
                    percent_change=percent_change,
                    vwap=vwap,
                    volume=volume or 0,
                    # Standard fields
                    direction='up',
                    reversal=bool(reversal_info),
                    count_up=session_high_count,
                    count_down=session_low_count,
                    vwap_divergence=vwap_divergence,
                    rel_volume=rel_volume,
                    label=generate_event_label('high', ticker, count=current_count),
                    # HighLow specific fields
                    current_high=price,
                    current_low=internal_state.get('current_low', internal_state.get('session_low')),
                    previous_high=previous_high if not is_initial else None,
                    previous_low=internal_state.get('previous_low'),
                    period='session',
                    session_high=price,
                    session_low=internal_state.get('session_low') if internal_state.get('session_low') != float('inf') else None,
                    is_initial=is_initial,
                    last_update=timestamp_float,  # FIXED: Use float timestamp
                    # Add trend and surge flags
                    trend_flag=trend_flag,
                    surge_flag=surge_flag,
                    # NEW: Enhanced fields
                    significance_score=significance_score,
                    reversal_info=reversal_info,
                    thresholds_used=thresholds
                )

                # Add calculation transparency
                high_event.highlow_calc_transparency = self._create_calc_transparency(
                    price, previous_high, is_initial, calc_details, vwap, 
                    session_total_events, internal_state, thresholds
                )
                
                # Update reversal tracking
                if reversal_info:
                    internal_state['last_reversal'] = reversal_info
                    internal_state['reversal_count'] = internal_state.get('reversal_count', 0) + 1
                
                # TRACE: Event detected
                tracer.create_trace_event(
                    ticker=ticker,
                    component='HighLowEventDetector',
                    action='event_detected',
                    start_time=start_time,
                    output_count=1,
                    details={
                        'event_type': 'high',
                        'price': price,
                        'previous_high': previous_high if not is_initial else None,
                        'count': current_count,
                        'is_initial': is_initial,
                        'trend_flag': trend_flag,
                        'surge_flag': surge_flag,
                        'significance_score': significance_score,
                        'reversal': reversal_info['type'] if reversal_info else None,
                        'event_id': high_event.event_id if hasattr(high_event, 'event_id') else None
                    }
                )
                
                events.append(high_event)
                
                # Update emission time
                self._update_emission_time(ticker, 'high')
            
            # Check for new session low
            elif price < internal_state['session_low']:
                
                previous_low = internal_state['session_low']
                is_initial = previous_low == float('inf')
                
                #logger.info(f"🔍 DIAG-HL-DETECT: {ticker} NEW LOW detected: ${price} < ${previous_low}")
                
                # Increment count
                internal_state['low_count'] = internal_state.get('low_count', 0) + 1
                current_count = internal_state['low_count']
                
                # Update session counts
                session_low_count = internal_state['low_count']
                session_total_events = session_high_count + session_low_count
                
                # Detect reversal
                reversal_info = None
                if self.track_reversals:
                    reversal_info = self._detect_reversal_pattern(ticker, 'low', internal_state)
                    if reversal_info:
                        logger.info(f"🔄 REVERSAL: {ticker} - {reversal_info['type']} pattern detected")
                
                # Calculate significance
                avg_volume = internal_state.get('average_volume')
                volume = internal_state.get('volume', 0)
                significance_score = self._calculate_significance_score(
                    price, previous_low, volume, avg_volume, percent_change
                )
                
                # Update state with float timestamps
                internal_state['previous_low'] = previous_low if not is_initial else None
                internal_state['session_low'] = price
                internal_state['current_low'] = price
                internal_state['last_event_type'] = 'low'
                internal_state['last_event_time'] = time.time()  # FIXED: Store as float
                internal_state['last_event_price'] = price
                internal_state['last_significance_score'] = significance_score
                
                # Add to event history with float timestamp
                if 'event_history' not in internal_state:
                    internal_state['event_history'] = deque(maxlen=10)
                internal_state['event_history'].append({
                    'type': 'low',
                    'price': price,
                    'time': time.time(),  # FIXED: Store as float
                    'significance': significance_score
                })
                
                # Get VWAP and volume metrics
                vwap = internal_state.get('vwap')
                vwap_divergence = calculate_vwap_divergence(price, vwap)
                rel_volume = calculate_relative_volume(volume, avg_volume)
                
                # Calculate period_seconds for session events
                session_start = internal_state.get('session_start_time', timestamp_float)
                # FIXED: Ensure both are floats for subtraction
                session_start_float = normalize_timestamp(session_start)
                period_seconds = int(timestamp_float - session_start_float) if session_start else 0
                
                # Create typed HighLowEvent (same pattern as high event, with low-specific values)
                low_event = HighLowEvent(
                    ticker=ticker,
                    type='low',
                    price=price,
                    time=time.time(),
                    count=session_total_events,
                    percent_change=percent_change,
                    vwap=vwap,
                    volume=volume or 0,
                    # Standard fields
                    direction='down',
                    reversal=bool(reversal_info),
                    count_up=session_high_count,
                    count_down=session_low_count,
                    vwap_divergence=vwap_divergence,
                    rel_volume=rel_volume,
                    label=generate_event_label('low', ticker, count=current_count),
                    # HighLow specific fields
                    current_high=internal_state.get('current_high', internal_state.get('session_high')),
                    current_low=price,
                    previous_high=internal_state.get('previous_high'),
                    previous_low=previous_low if not is_initial else None,
                    period='session',
                    session_high=internal_state.get('session_high') if internal_state.get('session_high') != float('-inf') else None,
                    session_low=price,
                    is_initial=is_initial,
                    last_update=timestamp_float,  # FIXED: Use float timestamp
                    # Add trend and surge flags
                    trend_flag=trend_flag,
                    surge_flag=surge_flag,
                    # NEW: Enhanced fields
                    significance_score=significance_score,
                    reversal_info=reversal_info,
                    thresholds_used=thresholds
                )
                
                # Add calculation transparency
                low_event.highlow_calc_transparency = self._create_calc_transparency(
                    price, previous_low, is_initial, calc_details, vwap, 
                    session_total_events, internal_state, thresholds, is_low=True
                )
                
                # Update reversal tracking
                if reversal_info:
                    internal_state['last_reversal'] = reversal_info
                    internal_state['reversal_count'] = internal_state.get('reversal_count', 0) + 1
                
                # TRACE: Event detected
                tracer.create_trace_event(
                    ticker=ticker,
                    component='HighLowEventDetector',
                    action='event_detected',
                    start_time=start_time,
                    output_count=1,
                    details={
                        'event_type': 'low',
                        'price': price,
                        'previous_low': previous_low if not is_initial else None,
                        'count': current_count,
                        'is_initial': is_initial,
                        'trend_flag': trend_flag,
                        'surge_flag': surge_flag,
                        'significance_score': significance_score,
                        'reversal': reversal_info['type'] if reversal_info else None,
                        'event_id': low_event.event_id if hasattr(low_event, 'event_id') else None
                    }
                )
                
                events.append(low_event)
                
                # Update emission time
                self._update_emission_time(ticker, 'low')
            
            return {'events': events}
            
        except Exception as e:
            logger.error(f"Error in high low event detection for {ticker}: {e}", exc_info=True)
            
            # TRACE: Error
            tracer.create_trace_event(
                ticker=ticker,
                component='HighLowEventDetector',
                action='highlow_detection_error',
                start_time=start_time,
                error=str(e),
                details={'error_type': type(e).__name__}
            )
            
            return {'events': []}
            

    def _detect_reversal_pattern(self, ticker: str, current_event_type: str, internal_state: Dict) -> Optional[Dict]:
        """
        Detect reversal patterns with enhanced logic.
        
        Returns:
            Dict with reversal info or None
        """
        if not self.track_reversals:
            return None
            
        # Get last event info
        last_event_type = internal_state.get('last_event_type')
        last_event_time = internal_state.get('last_event_time')
        last_event_price = internal_state.get('last_event_price')
        
        if not last_event_type:
            return None
        
        current_time = time.time()
        
        # FIXED: Ensure we're comparing floats
        last_event_time_float = normalize_timestamp(last_event_time) if last_event_time else 0
        time_since_last = current_time - last_event_time_float
        
        # Check if within reversal window
        if time_since_last > self.reversal_window_seconds:
            return None
        
        # Detect basic reversal
        reversal_type = None
        if last_event_type == 'low' and current_event_type == 'high':
            reversal_type = 'V-bottom'  # Low followed by high
        elif last_event_type == 'high' and current_event_type == 'low':
            reversal_type = 'V-top'     # High followed by low
        
        if reversal_type:
            # Calculate reversal characteristics
            reversal_info = {
                'type': reversal_type,
                'time_span': time_since_last,
                'is_rapid': time_since_last < 60,  # Less than 1 minute
                'previous_type': last_event_type,
                'previous_price': last_event_price
            }
            
            # Check for double patterns
            event_history = internal_state.get('event_history', [])
            if len(event_history) >= 3:
                # Check for W-bottom (low-high-low-high)
                if (current_event_type == 'high' and 
                    event_history[-1]['type'] == 'low' and
                    event_history[-2]['type'] == 'high' and
                    event_history[-3]['type'] == 'low'):
                    reversal_info['pattern'] = 'W-bottom'
                    
                # Check for M-top (high-low-high-low)
                elif (current_event_type == 'low' and
                    event_history[-1]['type'] == 'high' and
                    event_history[-2]['type'] == 'low' and
                    event_history[-3]['type'] == 'high'):
                    reversal_info['pattern'] = 'M-top'
            
            return reversal_info
        
        return None

    def _calculate_significance_score(self, price: float, previous_value: float, 
                                    volume: float, avg_volume: Optional[float], 
                                    percent_change: float) -> float:
        """Calculate how significant this high/low event is (0-100)."""
        
        if not self.enable_significance:
            return 0
        
        # Price change component (0-50 points)
        price_change_pct = abs(percent_change)
        price_score = min(price_change_pct * 10, 50)  # 5% change = 50 points
        
        # Volume component (0-50 points)
        volume_score = 0
        if avg_volume and avg_volume > 0 and volume > 0:
            volume_ratio = volume / avg_volume
            volume_score = min(volume_ratio * 25, 50)  # 2x volume = 50 points
        
        # Apply volume weight
        weighted_volume_score = volume_score * self.significance_volume_weight
        weighted_price_score = price_score * (1 - self.significance_volume_weight)
        
        total_score = weighted_price_score + weighted_volume_score
        
        return total_score

    def _create_calc_transparency(self, price, threshold_value, is_initial, calc_details, 
                                vwap, events_in_session, stock_data, thresholds, is_low=False):
        """Helper to create calculation transparency dict with threshold info."""
        operator = '<' if is_low else '>'
        event_type = 'low' if is_low else 'high'
        
        return {
            'session_open_price': calc_details.get('base_price'),
            'base_price_source': calc_details.get('base_price_source'),
            'price_change_amount': calc_details.get('price_change_amount'),
            'percent_change_formula': calc_details.get('percent_change_formula'),
            'threshold_type': 'price_comparison',
            'threshold_value': threshold_value if not is_initial else None,
            'detection_logic': f"{price} {operator} {threshold_value if not is_initial else 'initial'}",
            'session_start': stock_data.get('session_start_time'),
            'session_end': None,
            'events_in_session': events_in_session,
            'vwap_at_detection': vwap,
            'vwap_distance_formula': f"(({price} - {vwap}) / {vwap}) * 100" if vwap else None,
            # NEW: Add threshold details
            'thresholds_applied': thresholds,
            'significance_score': stock_data.get('last_significance_score', 0)
        }

    def _check_emission_cooldown(self, ticker: str, stock_data: Dict) -> bool:
        """Check if enough time has passed since last emission."""
        if self.cooldown_seconds <= 0:
            return True
            
        current_time = time.time()
        last_event_time = stock_data.get('last_event_time', None)
        
        # CORRECTED: If no last event, cooldown passes (first event allowed)
        if last_event_time is None:
            return True
        
        # Now normalize for comparison
        last_event_time_float = normalize_timestamp(last_event_time)
        
        time_since_last = current_time - last_event_time_float
        if time_since_last < self.cooldown_seconds:
            logger.debug(f"🔍 HIGHLOW-COOLDOWN: {ticker} blocked - {time_since_last:.1f}s < {self.cooldown_seconds}s")
            return False
        
        return True

    def _update_emission_time(self, ticker: str, event_type: str):
        """Update last emission time for cooldown tracking."""
        key = f"{ticker}_{event_type}"
        self.last_emission_times[key] = time.time()

    def _trend_detection(self, stock_data, ticker, price, vwap, volume, tick_vwap, tick_volume, tick_trade_size):
        """
        Detect price trend using lightweight utility function.
        """
        start_time = time.time()
        
        try:
            from src.processing.detectors.utils import check_trend_conditions
            
            # Just use the stock_data passed in - no cache_control lookup!
            trend_result = check_trend_conditions(
                stock_data=stock_data,
                price=price,
                vwap=vwap,
                volume=volume,
                config=self.config
            )
            
            # Convert to expected format for compatibility
            formatted_result = {
                'trend_direction': '→',
                'trend_strength': 'neutral',
                'trend_score': 0,
                'events': []
            }
            
            if trend_result.get('trend_detected'):
                trend_info = trend_result['trend_info']
                formatted_result['trend_direction'] = map_direction_symbol(trend_info['direction'])
                formatted_result['trend_strength'] = trend_info['strength']
                formatted_result['trend_score'] = trend_info.get('score', 0)
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Error in _trend_detection for {ticker}: {e}", exc_info=True)
            return {
                'trend_direction': '→',
                'trend_strength': 'neutral',
                'trend_score': 0,
                'events': []
            }


    def _surge_detection(self, stock_data, ticker, price, vwap, volume, tick_vwap, tick_volume, tick_trade_size):
        """
        Detect price surge using lightweight utility function.
        """
        start_time = time.time()
        
        try:
            from src.processing.detectors.utils import check_surge_conditions
            
            # Just use the stock_data passed in - no cache_control lookup!
            surge_result = check_surge_conditions(
                stock_data=stock_data,
                price=price,
                volume=volume,
                tick_volume=tick_volume,
                config=self.config
            )
            
            # Convert to expected format
            formatted_result = None
            if surge_result.get('surge_detected'):
                formatted_result = {
                    'events': [],
                    'surge_detected': True,
                    'surge_info': surge_result['surge_info']
                }
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Error in _surge_detection for {ticker}: {e}", exc_info=True)
            return None
        
    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """Get details for a specific ticker."""
        if ticker not in self.ticker_data:
            return {}
        
        ticker_info = self.ticker_data[ticker]
        
        # Safely access keys that might not exist
        result = {
            "last_price": ticker_info.get("last_price"),
            "session_high": ticker_info.get("session_high") if ticker_info.get("session_high", float('-inf')) != float('-inf') else None,
            "session_low": ticker_info.get("session_low") if ticker_info.get("session_low", float('inf')) != float('inf') else None,
            "last_update": ticker_info.get("last_update"),
            "market_status": ticker_info.get("last_market_status"),
        }
        
        # Add optional fields only if they exist
        if "day_high" in ticker_info:
            result["day_high"] = ticker_info["day_high"] if ticker_info["day_high"] != float('-inf') else None
        
        if "day_low" in ticker_info:
            result["day_low"] = ticker_info["day_low"] if ticker_info["day_low"] != float('inf') else None
        
        # Add other potentially missing fields with defaults
        result["initial_seed_price"] = ticker_info.get("initial_seed_price", ticker_info.get("last_price"))
        result["needs_seeding"] = ticker_info.get("needs_seeding", False)
        result["prior_candle_close"] = ticker_info.get("prior_candle_close")
        
        return result
    '''
    def get_all_tickers_details(self) -> Dict[str, Dict[str, Any]]:
        """
        Get details for all tracked tickers.
        
        Returns:
            Dictionary mapping ticker symbols to their details
        """
        results = {}
        for ticker in self.ticker_data:
            results[ticker] = self.get_ticker_details(ticker)
        return results
    '''