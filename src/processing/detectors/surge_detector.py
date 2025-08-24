import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pytz
from collections import deque
from config.logging_config import get_domain_logger, LogDomain
from src.presentation.converters.transport_models import StockData
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.events.base import BaseEvent
from src.processing.detectors.utils import (
    calculate_vwap_divergence, 
    calculate_relative_volume,
    calculate_percent_change,
    get_base_price,
    map_direction_symbol,
    generate_event_label,
    get_market_context
)
from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int
from src.processing.detectors.engines import SurgeDetectionEngine

logger = get_domain_logger(LogDomain.CORE, 'surge_detector')

class SurgeDetector:
    
    def __init__(self, config, cache_control=None):
        """
        Initialize the surge detector with configuration and cache control.
        
        Args:
            config: Application configuration dictionary
            cache_control: CacheControl instance for accessing cached data
        """
        self.config = config
        self.cache_control = cache_control
        self.eastern_tz = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))
        
        # ===== DETECTION PARAMETERS =====
        self.interval_seconds = float(config.get('SURGE_INTERVAL_SECONDS', 5))
        self.min_data_points = int(config.get('SURGE_MIN_DATA_POINTS', 3))
        
        # ===== SENSITIVITY CONTROLS =====
        self.global_sensitivity = float(config.get('SURGE_GLOBAL_SENSITIVITY', 1.0))
        self.up_threshold_multiplier = float(config.get('SURGE_UP_THRESHOLD_MULTIPLIER', 1.0))
        self.down_threshold_multiplier = float(config.get('SURGE_DOWN_THRESHOLD_MULTIPLIER', 1.0))
        
        # ===== VOLUME THRESHOLDS =====
        self.base_volume_threshold = float(config.get('SURGE_VOLUME_THRESHOLD', 1.3))
        self.volume_threshold = self.base_volume_threshold  # Will be dynamic
        
        # ===== MARKET-AWARE MULTIPLIERS =====
        self.market_open_multiplier = float(config.get('SURGE_MARKET_OPEN_MULTIPLIER', 2.0))
        self.market_close_multiplier = float(config.get('SURGE_MARKET_CLOSE_MULTIPLIER', 1.5))
        self.midday_multiplier = float(config.get('SURGE_MIDDAY_MULTIPLIER', 0.8))
        
        # ===== BUFFER MANAGEMENT (Hardcoded) =====
        self.max_buffer_size = 20
        self.max_history_points = 15
        
        # ===== TIMING CONTROLS (Hardcoded) =====
        self.surge_cooldown = self.interval_seconds  # Matches interval
        self.surge_expiration_seconds = 30
        
        # ===== SCORING SYSTEM (Hardcoded) =====
        self.price_score_weight = 50.0
        self.volume_score_weight = 50.0
        
        # ===== TESTING MODE =====
        self.testing_mode = config.get('SURGE_TESTING_MODE', False)
        if self.testing_mode:
            self.test_threshold_multiplier = float(config.get('SURGE_TEST_THRESHOLD_MULTIPLIER', 0.2))
            self.test_dollar_multiplier = float(config.get('SURGE_TEST_DOLLAR_MULTIPLIER', 0.1))
            self.test_volume_multiplier = float(config.get('SURGE_TEST_VOLUME_MULTIPLIER', 0.5))
            self.volume_threshold *= self.test_volume_multiplier
        else:
            self.test_threshold_multiplier = 1.0
            self.test_dollar_multiplier = 1.0
            self.test_volume_multiplier = 1.0
        
        # ===== STATE TRACKING =====
        self.last_analysis_times = {}
        self.last_sent_surges = {}
        self.surge_counts = {}  # {ticker: {'up': count, 'down': count}}
        self.last_surge_direction = {}  # {ticker: 'up' or 'down'}

    def detect_surge(self, stock_data, ticker, price, vwap, volume, tick_vwap, tick_volume, tick_trade_size, check_only=False):
        """
        TEMPORARY BYPASS: Enhanced detect_surge with adaptive thresholds based on market context.
        
        TEMPORARY: Returns SURGE event for ALL ticks with real data
        """
        try:
            # TEMPORARY BYPASS: Skip all logic and create surge event for every tick
            from src.core.domain.events.surge import SurgeEvent
            
            current_time = time.time()
            
            # Use real calculations for realistic data
            from src.processing.detectors.utils import calculate_percent_change
            
            # Get base price for calculations
            base_price = getattr(stock_data, 'market_open_price', price * 0.99)
            percent_change = calculate_percent_change(price, base_price)
            
            # Calculate volume surge ratio (mock but realistic)
            avg_volume = getattr(stock_data, 'average_volume', 10000)
            volume_ratio = (volume / avg_volume) if volume and avg_volume > 0 else 1.5
            
            # Create realistic surge event with actual data
            event = SurgeEvent(
                ticker=ticker,
                type='surge',
                price=price,
                time=current_time,
                direction='up' if percent_change > 0 else 'down',
                surge_trigger_type='price_and_volume' if volume_ratio > 1.2 else 'price',
                surge_magnitude=abs(percent_change),
                surge_volume_multiplier=volume_ratio,
                surge_strength='strong' if abs(percent_change) > 2.0 else 'moderate',
                surge_score=min(abs(percent_change) * 10, 100.0),  # Scale to 0-100
                percent_change=percent_change,
                vwap=vwap,
                volume=volume or 0,
                label=f"BYPASS-SURGE-{ticker}-{int(current_time)}"
            )
            
            result = {"events": [event], "surge_detected": True, "surge_info": event}
            return result
            
            # Use the shared utility function from event_detector_util
            from src.processing.detectors.utils import get_market_period_detailed, get_surge_price_band, calculate_surge_volatility
            
            market_period = get_market_period_detailed(current_timestamp)
            price_band = get_surge_price_band(price, self.config)
            volatility_class = calculate_surge_volatility(surge_data['buffer'])
            
            # Log market context
            #logger.debug(f"DIAG-SURGE-CONTEXT [{data_source}] {ticker}: "
            #            f"period={market_period}, band={price_band['name']}, "
            #            f"volatility={volatility_class}")
            
            # Build dynamic configuration
            dynamic_config = self._build_dynamic_config(market_period, price_band, 
                                                    volatility_class, surge_data['buffer'])
            
            # Use dynamic interval for timing check
            time_since_last_check = current_time - surge_data['last_check_time']
            interval_seconds = dynamic_config['SURGE_INTERVAL_SECONDS']
            
            if time_since_last_check < interval_seconds:
                #logger.debug(f"DIAG-SURGE-SKIP-TIMING [{data_source}] {ticker}: "
                #            f"Too soon ({time_since_last_check:.1f}s < {interval_seconds}s)")
                return result
            
            surge_data['last_check_time'] = current_time
            
            # Validate inputs
            if price <= 0:
                #logger.warning(f"DIAG-SURGE-INVALID-PRICE [{data_source}] {ticker}: price={price}")
                return result
            
            # Determine actual volume
            actual_volume = tick_volume if tick_volume is not None and tick_volume > 0 else volume
            has_any_volume = actual_volume is not None and actual_volume > 0
            
            #logger.debug(f"DIAG-SURGE-VOLUME-CHECK [{data_source}] {ticker}: "
            #            f"tick_volume={tick_volume}, volume={volume}, "
            #            f"using={'tick_volume' if tick_volume else 'volume' if volume else 'none'}")
            
            if not has_any_volume:
                #logger.warning(f"DIAG-SURGE-NO-VOLUME [{data_source}] {ticker}: No volume data")
                return result
            
            # Update buffer
            actual_vwap = tick_vwap if tick_vwap is not None else vwap
            
            surge_data['buffer'].append({
                'price': price,
                'volume': actual_volume,
                'timestamp': current_time,
                'vwap': actual_vwap,
                'trade_size': tick_trade_size
            })
            
            # Check if we have enough data (using dynamic minimum)
            min_data_points = dynamic_config['SURGE_MIN_DATA_POINTS']
            if len(surge_data['buffer']) < min_data_points:
                points_needed = min_data_points - len(surge_data['buffer'])
                #logger.debug(f"DIAG-SURGE-INSUFFICIENT [{data_source}] {ticker}: "
                #            f"Need {points_needed} more points "
                #            f"(have {len(surge_data['buffer'])}/{min_data_points})")
                return result
            
            # CALCULATION: Use engine with dynamic config
            calc_start = time.time()
            metrics = SurgeDetectionEngine.calculate_surge_metrics(
                buffer=surge_data['buffer'],
                current_price=price,
                current_volume=actual_volume,
                current_time=current_time,
                config=dynamic_config
            )
            calc_duration = (time.time() - calc_start) * 1000
            
            #logger.debug(f"DIAG-SURGE-METRICS [{data_source}] {ticker}: "
            #            f"price_change={metrics['price_change_pct']:.2f}%, "
            #            f"volume_mult={metrics['volume_multiplier']:.2f}x, "
            #            f"baseline_price={metrics['baseline_price']:.2f}, "
            #            f"calc_time={calc_duration:.1f}ms")
            
            # EVALUATION: Use adaptive evaluation with dynamic thresholds
            eval_start = time.time()
            
            # Get the dynamic thresholds that were calculated
            dynamic_thresholds = dynamic_config.get('_dynamic_thresholds', {})
            
            # Use the adaptive evaluation method
            conditions = SurgeDetectionEngine.evaluate_surge_conditions_adaptive(
                metrics=metrics,
                price=price,
                config=dynamic_config,
                dynamic_thresholds=dynamic_thresholds
            )
            eval_duration = (time.time() - eval_start) * 1000
            
            # Log evaluation with context
            thresholds = conditions.get('thresholds_used', {})
            #logger.debug(f"DIAG-SURGE-DECISION [{data_source}] {ticker}: "
            #            f"is_surge={conditions['is_surge']}, "
            #            f"trigger={conditions['trigger_type']}, "
            #            f"score={conditions['surge_score']:.1f}, "
            #            f"mode={thresholds.get('detection_mode', 'unknown')}, "
            #            f"period={thresholds.get('market_period', 'unknown')}, "
            #            f"eval_time={eval_duration:.1f}ms")
            
            # Log threshold details
            #logger.debug(f"DIAG-SURGE-THRESHOLDS [{data_source}] {ticker}: "
            #            f"price_thresh={thresholds.get('price_threshold_pct', 0):.2f}%, "
            #            f"dollar_thresh=${thresholds.get('min_dollar_change', 0):.3f}, "
            #            f"volume_thresh={thresholds.get('volume_threshold', 0):.2f}x, "
            #            f"band={thresholds.get('price_band', 'unknown')}, "
            #            f"volatility={thresholds.get('volatility_class', 'unknown')}")
            
            # Check if surge detected
            if not conditions['is_surge']:
                # Log attempt details for debugging
                price_pct = abs(metrics['price_change_pct'])
                price_thresh = thresholds.get('price_threshold_pct', 0)
                vol_mult = metrics['volume_multiplier']
                vol_thresh = thresholds.get('volume_threshold', 0)
                
                price_ratio = price_pct / price_thresh if price_thresh > 0 else 0
                vol_ratio = vol_mult / vol_thresh if vol_thresh > 0 else 0
                
                #logger.debug(f"DIAG-SURGE-ATTEMPT [{data_source}] {ticker}: "
                #            f"price={price_pct:.2f}%/{price_thresh:.2f}% ({price_ratio:.0%}), "
                #            f"volume={vol_mult:.2f}x/{vol_thresh:.2f}x ({vol_ratio:.0%}), "
                #            f"period={market_period}, band={price_band['name']}")
                
                #if price_ratio > 0.7 or vol_ratio > 0.7:
                    #logger.info(f"DIAG-SURGE-NEAR-MISS [{data_source}] {ticker}: "
                    #        f"Close to threshold in {market_period}/{price_band['name']}")
                
                return result
    
            if conditions['is_surge']:
                # Add quality validation
                if not self._validate_surge_quality(metrics, conditions, ticker, market_period):
                    return result  # Return empty result, surge filtered out
                
            # Check cooldown (can be dynamic based on market period)
            cooldown_multiplier = dynamic_config.get('SURGE_COOLDOWN_MULTIPLIER_MARKET', 1.0)
            effective_cooldown = interval_seconds * cooldown_multiplier
            
            time_since_last = current_time - surge_data.get('last_surge_time', 0)
            if surge_data.get('last_surge_time', 0) > 0 and time_since_last < effective_cooldown:
                time_remaining = effective_cooldown - time_since_last
                #logger.debug(f"DIAG-SURGE-COOLDOWN-BLOCKED [{data_source}] {ticker}: "
                #            f"time_since_last={time_since_last:.1f}s, "
                #            f"cooldown_required={effective_cooldown}s, "
                #            f"time_remaining={time_remaining:.1f}s")
                return result
            
            # Continue with existing event creation logic...
            # Initialize tracking
            self._initialize_ticker_tracking(ticker, check_only=False)
            
            # Detect reversal
            reversal = self._detect_reversal(ticker, metrics['direction'], check_only=False)
            #if reversal:
                #logger.info(f"DIAG-SURGE-REVERSAL [{data_source}] {ticker}: {reversal}")
            
            # Create event using existing method
            surge_event = self._create_surge_event_from_engine_data(
                ticker=ticker,
                price=price,
                current_time=current_time,
                metrics=metrics,
                conditions=conditions,
                reversal=reversal,
                vwap=vwap,
                actual_volume=actual_volume,
                stock_data=stock_data
            )
            
            # Log successful detection with context
            #logger.info(f"DIAG-SURGE-EVENT-CREATED [{data_source}] {ticker}: "
            #        f"{surge_event.direction} magnitude={surge_event.surge_magnitude:.1f}% "
            #        f"score={surge_event.surge_score:.1f} trigger={surge_event.surge_trigger_type} "
            #        f"[{market_period}/{price_band['name']}/{volatility_class}]")
            
            # Update tracking
            self._update_surge_tracking(
                surge_data, surge_event, metrics, conditions,
                current_time, ticker
            )
            
            result['events'].append(surge_event)
            
            # Success summary
            total_duration = (time.time() - detection_start_time) * 1000
            #logger.info(f"DIAG-SURGE-SUCCESS [{data_source}] {ticker}: "
            #        f"Event detected in {total_duration:.1f}ms "
            #        f"with adaptive thresholds")
            
            return result
            
        except Exception as e:
            logger.error(f"SURGE-ERROR {ticker}: Error in detect_surge: {e}", exc_info=True)
            return {"events": [], "surge_detected": False, "surge_info": None}


    def _create_surge_event_from_engine_data(self, ticker, price, current_time, metrics, 
                                            conditions, reversal, vwap, actual_volume, stock_data):
        """
        Create a SurgeEvent from engine calculation results.
        This method handles event-specific logic like counting and labeling.
        """
        # Update counts based on direction
        if metrics['direction'] == 'up':
            self.surge_counts[ticker]['up'] += 1
        elif metrics['direction'] == 'down':
            self.surge_counts[ticker]['down'] += 1

        if metrics['direction'] != 'neutral':
            self.last_surge_direction[ticker] = metrics['direction']
        
        # Get base price for percent change
        from src.processing.detectors.utils import get_base_price, calculate_relative_volume, generate_event_label, map_direction_symbol, calculate_percent_change
        
        base_price, base_price_source = get_base_price(
            stock_data=stock_data,
            market_status=getattr(stock_data, 'market_status', 'REGULAR'),
            market_open_price=getattr(stock_data, 'market_open_price', None),
            current_price=price
        )
        
        # Calculate SESSION percent change (for chng% field)
        session_percent_change = calculate_percent_change(price, base_price)
        
        # Calculate additional metrics
        average_volume = getattr(stock_data, 'average_volume', None)
        rel_volume = calculate_relative_volume(actual_volume, average_volume)
        vwap_divergence = calculate_vwap_divergence(price, vwap)
        
        # Build calculation transparency
        surge_calculation = self._build_surge_calculation_from_engine(
            metrics, conditions, actual_volume, current_time
        )
        
        # Generate label using the standard function (this uses the SURGE percentage)
        label = generate_event_label('surge', ticker, 
                                direction=map_direction_symbol(metrics['direction']), 
                                magnitude=abs(metrics['price_change_pct']),  # This is surge %
                                trigger_type=conditions['trigger_type'])
        
        # Clean up the label
        # Remove "Surge" or "surge" from the label
        label = label.replace("Surge ", "").replace("surge ", "").replace("SURGE ", "")
        
        # Make trigger types more readable
        label = label.replace("price_driven", "price-led")
        label = label.replace("volume_driven", "volume-led")
        label = label.replace("price_and_volume", "price & volume")
        

        # ADD DEBUG LOGGING
        '''
        logger.info(f"🔍 SURGE DEBUG {ticker}: "
                    f"Current price: ${price:.2f}, "
                    f"Baseline price: ${metrics.get('baseline_price', 'N/A'):.2f}, "
                    f"Surge %: {metrics['price_change_pct']:.1f}%, "
                    f"Session base: ${base_price:.2f}, "
                    f"Session %: {session_percent_change:.1f}% "
                    f"label: '{label}', ")
        
        # Also log the buffer to see what's in there
        if hasattr(stock_data, 'surge_data') and stock_data.surge_data:
            buffer = stock_data.surge_data.get('buffer', deque())
            if buffer:
                buffer_list = list(buffer)
                # Show last 5 prices with timestamps
                for i, point in enumerate(buffer_list[-5:]):
                    time_diff = current_time - point['timestamp']
                    logger.info(f"  Buffer[{i-5}]: ${point['price']:.2f} ({time_diff:.1f}s ago)")
        '''

        # Create the event
        expiration_time = current_time + self.surge_expiration_seconds
        
        surge_event = SurgeEvent(
            ticker=ticker,
            type='surge',
            price=price,
            time=time.time(),
            direction=metrics['direction'],  # Keep as 'up' or 'down', not arrow
            reversal=reversal if reversal else False,
            count=self.surge_counts[ticker]['up'] + self.surge_counts[ticker]['down'],
            count_up=self.surge_counts[ticker]['up'],
            count_down=self.surge_counts[ticker]['down'],
            percent_change=session_percent_change,  # FIXED: Now uses session change, not surge change
            vwap=vwap,
            vwap_divergence=vwap_divergence,
            volume=actual_volume,
            rel_volume=rel_volume,
            label=label,  # Uses surge % in label (correct)
            # Surge-specific fields
            surge_magnitude=metrics['price_change_pct'],  # This is the surge % (correct)
            surge_strength=conditions['surge_strength'],
            surge_trigger_type=conditions['trigger_type'],
            surge_score=conditions['surge_score'],
            surge_volume_multiplier=metrics['volume_multiplier'],
            surge_calculation=surge_calculation,
            surge_description=f"Surge {metrics['direction']} "
                            f"{conditions['trigger_type'].replace('_', '/')} "
                            f"({abs(metrics['price_change_pct']):.1f}%)",
            surge_expiration=expiration_time,
            surge_daily_count=stock_data.surge_data['daily_surge_count'] + 1,
            surge_age=0
        )
        
        return surge_event
    
    def _build_dynamic_config(self, market_period: str, price_band: Dict[str, Any], 
                            volatility_class: str, buffer: deque) -> Dict[str, Any]:
        """
        Build dynamic configuration based on market context.
        
        Args:
            market_period: Current market period
            price_band: Price band information
            volatility_class: Volatility classification
            buffer: Current surge buffer
            
        Returns:
            Dynamic configuration dictionary
        """
        try:
            # Get dynamic thresholds from engine
            dynamic_thresholds = SurgeDetectionEngine.get_dynamic_thresholds(
                market_period, price_band, volatility_class, self.config
            )
            
            # Start with base config
            config = self.config.copy()
            
            # Apply dynamic values
            config['SURGE_INTERVAL_SECONDS'] = dynamic_thresholds['interval_seconds']
            config['SURGE_MIN_DATA_POINTS'] = dynamic_thresholds['min_data_points']
            config['SURGE_VOLUME_THRESHOLD'] = dynamic_thresholds['volume_threshold']
            config['SURGE_GLOBAL_SENSITIVITY'] = dynamic_thresholds['global_sensitivity']
            
            # Store context for later use
            config['_dynamic_thresholds'] = dynamic_thresholds
            config['_market_period'] = market_period
            config['_price_band'] = price_band['name']
            config['_volatility_class'] = volatility_class
            
            #logger.debug(f"DIAG-SURGE-CONFIG: Built dynamic config - "
            #            f"period={market_period}, band={price_band['name']}, "
            #            f"volatility={volatility_class}, "
            #            f"price_thresh={dynamic_thresholds['price_threshold_pct']:.2f}%, "
            #            f"vol_thresh={dynamic_thresholds['volume_threshold']:.1f}x, "
            #            f"sensitivity={dynamic_thresholds['global_sensitivity']:.1f}")
            
            return config
            
        except Exception as e:
            logger.error(f"Error building dynamic config: {e}")
            # Return original config on error
            return self.config

    def _validate_surge_quality(self, metrics: Dict, conditions: Dict, 
                            ticker: str, market_period: str) -> bool:
        """
        Additional quality gate to reduce false positives.
        Returns True if surge passes quality checks, False if it should be filtered.
        
        Args:
            metrics: Surge metrics from calculation engine
            conditions: Surge conditions from evaluation
            ticker: Stock ticker symbol
            market_period: Current market period
        
        Returns:
            Boolean - True if surge is valid, False if should be filtered
        """
        try:
            # Extract key values for validation
            price_change_pct = abs(metrics.get('price_change_pct', 0))
            price_change_abs = abs(metrics.get('price_change_abs', 0))
            volume_multiplier = metrics.get('volume_multiplier', 1.0)
            surge_score = conditions.get('surge_score', 0)
            trigger_type = conditions.get('trigger_type', 'none')
            price_band = conditions.get('thresholds_used', {}).get('price_band', 'MID')
            
            # ===== QUALITY GATE 1: Minimum Absolute Dollar Change =====
            # Prevent tiny dollar moves from triggering surges even if % is high
            min_dollar_changes = {
                'PENNY': 0.10,    # $0.10 for stocks under $10 (relaxed for penny stocks)
                'LOW': 0.50,      # $0.50 for $10-50
                'MID': 1.50,      # $1.50 for $50-200
                'HIGH': 3.00,     # $3.00 for $200-500
                'ULTRA': 5.00     # $5.00 for $500+
            }
            
            min_dollar = min_dollar_changes.get(price_band, 1.00)
            
            # During opening period, relax dollar requirements slightly
            if market_period == 'OPENING':
                min_dollar *= 0.7
            
            if price_change_abs < min_dollar:
                logger.info(f"🚫 SURGE-QUALITY-FILTERED [{ticker}]: "
                        f"Dollar change ${price_change_abs:.2f} < ${min_dollar:.2f} minimum "
                        f"(band={price_band}, period={market_period})")
                return False
            
            # ===== QUALITY GATE 2: Minimum Score Requirements =====
            # Higher score requirements for midday to reduce false positives
            min_scores = {
                'OPENING': 50,      # Lower threshold for volatile opening
                'MIDDAY': 75,       # HIGH threshold for midday (main problem period)
                'CLOSING': 60,      # Medium threshold
                'AFTERHOURS': 45,   # Lower for sparse data
                'PREMARKET': 45     # Lower for sparse data
            }
            
            min_score = min_scores.get(market_period, 60)
            
            if surge_score < min_score:
                logger.info(f"🚫 SURGE-QUALITY-FILTERED [{ticker}]: "
                        f"Score {surge_score:.1f} < {min_score} minimum "
                        f"(period={market_period})")
                return False
            
            # ===== QUALITY GATE 3: Trigger Type Validation =====
            # During midday, require both price AND volume (strict mode)
            if market_period == 'MIDDAY':
                if trigger_type not in ['price_and_volume', 'price_driven', 'volume_driven']:
                    logger.info(f"🚫 SURGE-QUALITY-FILTERED [{ticker}]: "
                            f"Midday requires strong trigger, got '{trigger_type}'")
                    return False
                
                # For midday, if it's only price OR volume (not both), require higher thresholds
                if trigger_type == 'price':
                    if price_change_pct < 5.0:  # Require 5% for price-only surges in midday
                        logger.info(f"🚫 SURGE-QUALITY-FILTERED [{ticker}]: "
                                f"Midday price-only surge needs 5%, got {price_change_pct:.2f}%")
                        return False
                elif trigger_type == 'volume':
                    if volume_multiplier < 4.0:  # Require 4x volume for volume-only surges
                        logger.info(f"🚫 SURGE-QUALITY-FILTERED [{ticker}]: "
                                f"Midday volume-only surge needs 4x, got {volume_multiplier:.2f}x")
                        return False
            
            # ===== QUALITY GATE 4: Surge Frequency Check =====
            # Prevent spam - track last surge time per ticker
            current_time = time.time()
            
            # Initialize tracking dict if needed
            if not hasattr(self, '_surge_quality_tracking'):
                self._surge_quality_tracking = {}
            
            if ticker in self._surge_quality_tracking:
                last_surge_time = self._surge_quality_tracking[ticker]['last_time']
                time_since_last = current_time - last_surge_time
                
                # Dynamic cooldown based on market period
                quality_cooldowns = {
                    'OPENING': 45,      # 45 seconds minimum between surges
                    'MIDDAY': 180,      # 3 minutes for midday (strict!)
                    'CLOSING': 60,      # 1 minute
                    'AFTERHOURS': 120,  # 2 minutes
                    'PREMARKET': 120    # 2 minutes
                }
                
                required_cooldown = quality_cooldowns.get(market_period, 90)
                
                if time_since_last < required_cooldown:
                    logger.info(f"🚫 SURGE-QUALITY-FILTERED [{ticker}]: "
                            f"Quality cooldown {time_since_last:.1f}s < {required_cooldown}s required "
                            f"(period={market_period})")
                    return False
                
                # Check surge frequency (max surges per period)
                surge_count = self._surge_quality_tracking[ticker].get('count', 0)
                
                # Reset count if it's been more than 30 minutes
                if time_since_last > 1800:  # 30 minutes
                    surge_count = 0
                
                # Maximum surges allowed per 30-minute window
                max_surges_per_window = {
                    'OPENING': 5,     # More allowed during volatile opening
                    'MIDDAY': 3,      # Very restricted during midday
                    'CLOSING': 4,     # Some flexibility
                    'AFTERHOURS': 3,  # Limited
                    'PREMARKET': 3    # Limited
                }
                
                max_allowed = max_surges_per_window.get(market_period, 3)
                
                if surge_count >= max_allowed:
                    logger.info(f"🚫 SURGE-QUALITY-FILTERED [{ticker}]: "
                            f"Max surges reached ({surge_count}/{max_allowed}) in 30min window "
                            f"(period={market_period})")
                    return False
            else:
                # First surge for this ticker
                self._surge_quality_tracking[ticker] = {'last_time': 0, 'count': 0}
            
            # ===== QUALITY GATE 5: Volatility-Based Filtering =====
            # If volatility is LOW, require higher thresholds
            volatility_class = conditions.get('thresholds_used', {}).get('volatility_class', 'NORMAL')
            
            if volatility_class == 'LOW' and market_period == 'MIDDAY':
                # In low volatility midday, require exceptional moves
                if price_change_pct < 3.5:
                    logger.info(f"🚫 SURGE-QUALITY-FILTERED [{ticker}]: "
                            f"Low volatility midday needs 3.5%, got {price_change_pct:.2f}%")
                    return False
            
            # ===== PASSED ALL QUALITY GATES =====
            # Update tracking
            self._surge_quality_tracking[ticker]['last_time'] = current_time
            self._surge_quality_tracking[ticker]['count'] = \
                self._surge_quality_tracking[ticker].get('count', 0) + 1
            
            logger.info(f"✅ SURGE-QUALITY-PASSED [{ticker}]: "
                    f"Score={surge_score:.1f}, Change={price_change_pct:.2f}%, "
                    f"Volume={volume_multiplier:.2f}x, Trigger={trigger_type} "
                    f"(period={market_period}, band={price_band})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in surge quality validation for {ticker}: {e}", exc_info=True)
            # On error, allow the surge through (fail open)
            return True

    # Also add this helper method to reset quality tracking on session change
    def reset_surge_quality_tracking(self):
        """
        Reset surge quality tracking on market session changes.
        Call this along with reset_daily_counts().
        """
        if hasattr(self, '_surge_quality_tracking'):
            self._surge_quality_tracking.clear()
            logger.info("Surge quality tracking reset for new session")

    def _get_dynamic_volume_threshold(self, timestamp, market_status):
        """Get volume threshold based on market conditions"""
        
        # FIXED: Ensure timestamp is datetime for market_utils
        if isinstance(timestamp, (int, float)):
            timestamp_dt = datetime.fromtimestamp(timestamp, tz=self.eastern_tz)
        else:
            timestamp_dt = timestamp
        
        context = get_market_context(timestamp_dt, market_status)
        base_threshold = self.base_volume_threshold
        
        if context['period'] == 'opening_30':
            return base_threshold * self.market_open_multiplier
        elif context['period'] == 'closing_30':
            return base_threshold * self.market_close_multiplier
        elif context['period'] == 'lunch':
            return base_threshold * self.midday_multiplier
        else:
            return base_threshold

    def _get_market_period(self, timestamp, market_status):
        """Get current market period for tracing"""
        context = get_market_context(timestamp, market_status)
        return context['period']

    def _build_surge_calculation_from_engine(self, metrics, conditions, actual_volume, current_time):
        """Build calculation transparency from engine results."""
        thresholds = conditions['thresholds_used']
        
        return {
            'baseline_price': metrics['baseline_price'],
            'baseline_window': f"Previous price from buffer (t-{self.interval_seconds}s)",
            'price_change_pct': metrics['price_change_pct'],
            'volume_baseline': metrics['avg_volume'],
            'volume_current': actual_volume,
            'volume_multiplier_formula': f"({actual_volume} / {metrics['avg_volume']}) = "
                                    f"{metrics['volume_multiplier']:.2f}" 
                                    if metrics['avg_volume'] > 0 else "N/A",
            'magnitude_calculation': {
                'formula': f"abs(price_change_pct) = abs({metrics['price_change_pct']:.2f})",
                'components': {
                    'baseline_price': metrics['baseline_price'],
                    'absolute_change': metrics['price_change_abs'],
                    'percent_change': metrics['price_change_pct']
                }
            },
            'score_calculation': {
                'formula': f"price_score({conditions['price_score']:.1f}) + "
                        f"volume_score({conditions['volume_score']:.1f})",
                'weights': {
                    'price_weight': self.config.get('SURGE_SCORE_PRICE_WEIGHT', 50),
                    'volume_weight': self.config.get('SURGE_SCORE_VOLUME_WEIGHT', 50)
                },
                'result': conditions['surge_score']
            },
            'trigger_evaluation': {
                'thresholds_checked': thresholds,
                'price_surge': conditions['is_price_surge'],
                'volume_surge': conditions['is_volume_surge'],
                'trigger_type': conditions['trigger_type']
            },
            'strength_derivation': f"Score {conditions['surge_score']:.1f} → "
                                f"'{conditions['surge_strength']}' (strong>=80, moderate>=60)"
        }

        
    def _initialize_surge_data(self, stock_data, ticker, check_only):
        """Initialize surge data structure if needed."""
        if not hasattr(stock_data, 'surge_data') or stock_data.surge_data is None:
            if not check_only:
                logger.debug(f"🔍 SURGE-DETECT: Initializing surge_data for {ticker}")
            stock_data.surge_data = {
                'buffer': deque(maxlen=self.max_buffer_size),
                'last_surge_time': 0,  # Keep as 0, not None
                'surge_history': deque(maxlen=self.max_history_points),
                'surge_count': 0,
                'daily_surge_count': 0,
                'last_surge_timestamp': None,  # Keep as None
                'last_check_time': 0  # Keep as 0
            }

        surge_data = stock_data.surge_data

        # Ensure all required fields exist
        for field, default in [
            ('buffer', deque(maxlen=self.max_buffer_size)),
            ('last_surge_time', 0),
            ('surge_history', deque(maxlen=self.max_history_points)),
            ('surge_count', 0),
            ('daily_surge_count', 0),
            ('last_surge_timestamp', None),
            ('last_check_time', 0)
        ]:
            if field not in surge_data:
                surge_data[field] = default
                
        return surge_data

    def _get_dynamic_volume_threshold(self, timestamp, market_status):
        """Get volume threshold based on market conditions"""
        
        context = get_market_context(timestamp, market_status)
        base_threshold = self.base_volume_threshold
        
        if context['period'] == 'opening_30':
            return base_threshold * self.market_open_multiplier
        elif context['period'] == 'closing_30':
            return base_threshold * self.market_close_multiplier
        elif context['period'] == 'lunch':
            return base_threshold * self.midday_multiplier
        else:
            return base_threshold
        
    def _validate_and_check_timing(self, surge_data, ticker, price, volume, tick_volume, current_time):
        """Validate inputs and check timing constraints (no calculations)."""

        time_since_last_check = current_time - surge_data['last_check_time']
        if time_since_last_check < self.interval_seconds:
            logger.debug(f"🔍 SURGE-DETECT: Skipping {ticker} - Too soon since last check")
            return False  
        
        surge_data['last_check_time'] = current_time
        
        if price <= 0 or (tick_volume is None and volume is None):
            logger.debug(f"🔍 SURGE-DETECT: Skipping {ticker} - Invalid data")
            return False
        
        return True  

    def _update_data_buffer(self, ticker, surge_data, price, volume, tick_volume, 
                            vwap, tick_vwap, tick_trade_size, current_time, check_only):
        """Update the data buffer with new data point."""
        buffer_start_time = time.time()  # Add for duration tracking
        actual_volume = tick_volume if tick_volume is not None and tick_volume > 0 else volume
        actual_vwap = tick_vwap if tick_vwap is not None else vwap
        
        # Check if buffer is at max capacity (will cause oldest to be dropped)
        buffer_at_max = len(surge_data['buffer']) >= self.max_buffer_size

        # CRITICAL FIX: Detect and correct future timestamps
        real_current_time = time.time()
        timestamp_to_use = float(current_time)  # Ensure float storage
        
        # Check if timestamp is in the future (common with synthetic data)
        if timestamp_to_use > real_current_time + 60:  # More than 60 seconds in future
            time_offset = timestamp_to_use - real_current_time
            logger.warning(f"📊 SURGE-TIMESTAMP-FIX: Correcting future timestamp "
                        f"offset={time_offset:.1f}s for {ticker}")
            # Use real current time instead
            timestamp_to_use = real_current_time

        surge_data['buffer'].append({
            'price': price,
            'volume': actual_volume,
            'timestamp': timestamp_to_use,  # Use corrected timestamp
            'vwap': actual_vwap,
            'trade_size': tick_trade_size
        })
        
        # TRACE: Buffer overflow if item was dropped
        if buffer_at_max and tracer.should_trace(ticker, TraceLevel.VERBOSE) and not check_only:
            tracer.trace(
                ticker=ticker,
                component='SurgeDetector',
                action='buffer_overflow',
                data={
                    'timestamp': current_time,
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(0),  # One dropped
                    'duration_ms': 0,
                    'details': {
                        'max_buffer_size': self.max_buffer_size,
                        'oldest_dropped': True
                    }
                }
            )
        
        # TRACE: Buffer updated (verbose only, and only for full detection)
        if tracer.should_trace(ticker, TraceLevel.VERBOSE) and not check_only:
            tracer.trace(
                ticker=ticker,
                component='SurgeDetector',
                action='buffer_updated',
                data={
                    'timestamp': current_time,
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(1),
                    'duration_ms': (time.time() - buffer_start_time) * 1000,  # Now with actual duration
                    'details': {
                        'buffer_size': len(surge_data['buffer']),
                        'time_span_seconds': current_time - surge_data['buffer'][0]['timestamp'] if surge_data['buffer'] else 0
                    }
                }
            )
        
        return actual_volume, actual_vwap

    

    

    def _initialize_ticker_tracking(self, ticker, check_only):
        """Initialize tracking for the ticker if needed."""
        if ticker not in self.surge_counts:
            self.surge_counts[ticker] = {'up': 0, 'down': 0}
            if not check_only:
                logger.debug(f"🔍 SURGE-DETECT: Initialized surge counts for {ticker}")

    def _detect_reversal(self, ticker, direction, check_only):
        """Detect if a reversal has occurred."""
        reversal = None
        if ticker in self.last_surge_direction:
            if self.last_surge_direction[ticker] == 'up' and direction == 'down':
                reversal = 'up-now-down'
            elif self.last_surge_direction[ticker] == 'down' and direction == 'up':
                reversal = 'down-now-up'
            if reversal and not check_only:
                logger.debug(f"🔍 SURGE-DETECT: {ticker} - Reversal detected: {reversal}")
        return reversal

    

    

    def _check_cooldown(self, surge_data, current_time, ticker):
        """Check if cooldown period has passed."""
        if surge_data['last_surge_time'] == 0:
            logger.debug(f"🔍 SURGE-DETECT: {ticker} - SURGE DETECTED! First surge (no cooldown)")
            return True
        else:
            time_since_last_surge = current_time - surge_data['last_surge_time']
            if time_since_last_surge < self.interval_seconds:
                logger.debug(f"🔍 SURGE-DETECT: {ticker} - SURGE BLOCKED by cooldown "
                        f"({time_since_last_surge:.1f}s < {self.interval_seconds}s)")
                
                # TRACE: Cooldown block
                if tracer.should_trace(ticker):
                    tracer.trace(
                        ticker=ticker,
                        component='SurgeDetector',
                        action='surge_cooldown_blocked',
                        data={
                            'timestamp': current_time,
                            'input_count': ensure_int(1),
                            'output_count': ensure_int(0),  # Blocked
                            'duration_ms': 0,
                            'details': {
                                'time_since_last': time_since_last_surge,
                                'cooldown_required': self.interval_seconds,
                                'time_remaining': self.interval_seconds - time_since_last_surge
                            }
                        }
                    )
                
                return False
            else:
                logger.debug(f"🔍 SURGE-DETECT: {ticker} - SURGE DETECTED! Cooldown OK "
                        f"({time_since_last_surge:.1f}s)")
                return True

    def _create_surge_event(self, ticker, price, current_time, price_metrics, 
                           volume_metrics, surge_conditions, reversal, vwap, 
                           actual_volume, stock_data):
        """Create a typed SurgeEvent."""
        # Update counts
        if price_metrics['direction'] == 'up':
            self.surge_counts[ticker]['up'] += 1
        elif price_metrics['direction'] == 'down':
            self.surge_counts[ticker]['down'] += 1

        if price_metrics['direction'] != 'neutral':
            self.last_surge_direction[ticker] = price_metrics['direction']
        
        # Calculate scores
        price_score = self._calculate_price_score(
            price_metrics['price_change_pct_abs'], 
            surge_conditions['threshold_pct']
        )
        volume_score = self._calculate_volume_score(
            volume_metrics['volume_multiplier'], 
            surge_conditions['is_volume_surge']
        )
        surge_score = price_score + volume_score
        
        strength = 'strong' if surge_score >= 80 else 'moderate' if surge_score >= 60 else 'weak'
        expiration_time = current_time + self.surge_expiration_seconds
        
        logger.debug(f"🔍 SURGE-DETECT: {ticker} - Creating surge event: "
                    f"Type:{surge_conditions['trigger_type']}, Score:{surge_score:.1f}, Strength:{strength}")
        
        # Get base price for percent change calculation
        base_price, base_price_source = get_base_price(
            stock_data=stock_data,
            market_status=getattr(stock_data, 'market_status', 'REGULAR'),
            market_open_price=getattr(stock_data, 'market_open_price', None),
            current_price=price
        )

        # Calculate additional metrics
        average_volume = getattr(stock_data, 'average_volume', None)
        rel_volume = calculate_relative_volume(actual_volume, average_volume)
        vwap_divergence = calculate_vwap_divergence(price, vwap)
        
        # Build calculation transparency
        surge_calculation = self._build_surge_calculation(
            price_metrics, volume_metrics, surge_conditions,
            price_score, volume_score, surge_score, strength,
            actual_volume, current_time
        )
        
        # Create the event
        surge_event = SurgeEvent(
            ticker=ticker,
            type='surge',
            price=price,
            time=time.time(),
            direction=price_metrics['direction'],
            reversal=reversal if reversal else False,
            count=self.surge_counts[ticker]['up'] + self.surge_counts[ticker]['down'],
            count_up=self.surge_counts[ticker]['up'],
            count_down=self.surge_counts[ticker]['down'],
            percent_change=price_metrics['price_change_pct'],
            vwap=vwap,
            vwap_divergence=vwap_divergence,
            volume=actual_volume,
            rel_volume=rel_volume,
            label=generate_event_label('surge', ticker, 
                                     direction=map_direction_symbol(price_metrics['direction']), 
                                     magnitude=price_metrics['price_change_pct_abs'], 
                                     trigger_type=surge_conditions['trigger_type']),
            # Surge-specific fields
            surge_magnitude=price_metrics['price_change_pct'],
            surge_strength=strength,
            surge_trigger_type=surge_conditions['trigger_type'],
            surge_score=surge_score,
            surge_volume_multiplier=volume_metrics['volume_multiplier'],
            surge_calculation=surge_calculation,
            surge_description=f"Surge {price_metrics['direction']} "
                            f"{surge_conditions['trigger_type'].replace('_', '/')} "
                            f"({price_metrics['price_change_pct_abs']:.1f}%)",
            surge_expiration=expiration_time,
            surge_daily_count=stock_data.surge_data['daily_surge_count'] + 1,
            surge_age=0
        )
        
        return surge_event

    def _calculate_price_score(self, price_change_pct_abs, threshold_pct):
        """Calculate the price component of the surge score."""
        if threshold_pct > 0:
            return min((price_change_pct_abs / threshold_pct * self.price_score_weight), 
                      self.price_score_weight)
        return 0

    def _calculate_volume_score(self, volume_multiplier, is_volume_surge):
        """Calculate the volume component of the surge score."""
        if is_volume_surge:
            return min((volume_multiplier / self.volume_threshold * self.volume_score_weight), 
                      self.volume_score_weight)
        return 0

    def _build_surge_calculation(self, price_metrics, volume_metrics, surge_conditions,
                                price_score, volume_score, surge_score, strength,
                                actual_volume, current_time):
        """Build the surge calculation transparency object."""
        surge_data = {}  # Get from somewhere if needed
        
        return {
            'baseline_price': price_metrics['baseline_price'],
            'baseline_window': f"Previous price from buffer (t-{self.interval_seconds}s)",
            'price_change_pct': price_metrics['price_change_pct'],
            'volume_baseline': volume_metrics['avg_volume'],
            'volume_current': actual_volume,
            'volume_multiplier_formula': f"({actual_volume} / {volume_metrics['avg_volume']}) = "
                                       f"{volume_metrics['volume_multiplier']:.2f}" 
                                       if volume_metrics['avg_volume'] > 0 else "N/A",
            'magnitude_calculation': {
                'formula': f"abs({price_metrics.get('current_price', 'N/A')} - "
                          f"{price_metrics['baseline_price']}) / {price_metrics['baseline_price']} * 100",
                'components': {
                    'current_price': price_metrics.get('current_price', 'N/A'),
                    'baseline_price': price_metrics['baseline_price'],
                    'absolute_change': price_metrics['price_change_abs'],
                    'percent_change': price_metrics['price_change_pct']
                }
            },
            'score_calculation': {
                'formula': f"price_score({price_score:.1f}) + volume_score({volume_score:.1f})",
                'weights': {
                    'price_weight': self.price_score_weight,
                    'volume_weight': self.volume_score_weight
                },
                'price_score_formula': f"min(({price_metrics['price_change_pct_abs']:.2f} / "
                                     f"{surge_conditions['threshold_pct']:.2f} * "
                                     f"{self.price_score_weight}), {self.price_score_weight})",
                'volume_score_formula': f"min(({volume_metrics['volume_multiplier']:.2f} / "
                                      f"{self.volume_threshold:.2f} * {self.volume_score_weight}), "
                                      f"{self.volume_score_weight})" 
                                      if surge_conditions['is_volume_surge'] else "0 (no volume surge)"
            },
            'trigger_evaluation': {
                'thresholds_checked': {
                    'price_threshold_pct': surge_conditions['threshold_pct'],
                    'price_threshold_dollar': surge_conditions['min_dollar_change'],
                    'volume_threshold': self.volume_threshold
                },
                'trigger_logic': f"Price: {price_metrics['price_change_pct_abs']:.2f}% >= "
                               f"{surge_conditions['threshold_pct']:.2f}% AND "
                               f"${abs(price_metrics['price_change_abs']):.3f} >= "
                               f"${surge_conditions['min_dollar_change']:.3f}: "
                               f"{surge_conditions['is_price_surge']}, "
                               f"Volume: {volume_metrics['volume_multiplier']:.2f}x >= "
                               f"{self.volume_threshold:.2f}x: {surge_conditions['is_volume_surge']}",
                'cooldown_check': f"Time since last surge: "
                                f"{current_time - surge_data.get('last_surge_time', 0):.1f}s "
                                f"(cooldown: {self.interval_seconds}s)"
            },
            'strength_derivation': f"Score {surge_score:.1f} → '{strength}' (strong>=80, moderate>=60)"
        }

    def _update_surge_tracking(self, surge_data, surge_event, price_metrics, 
                            surge_conditions, current_time, ticker):
        """Update internal surge tracking data."""
        # FIXED: Ensure timestamp stored as float
        surge_data['surge_history'].append({
            'type': 'surge',
            'ticker': ticker,
            'direction': price_metrics['direction'],
            'trigger_type': surge_conditions['trigger_type'],
            'price': surge_event.price,
            'price_change_pct': price_metrics['price_change_pct'],
            'price_change_abs': price_metrics['price_change_abs'],
            'volume_multiplier': surge_event.surge_volume_multiplier,
            'surge_score': surge_event.surge_score,
            'score': surge_event.surge_score,
            'timestamp': float(current_time),  # Store as float
            'expiration': surge_event.surge_expiration,
            'label': f"Surge {price_metrics['direction']} ({surge_conditions['trigger_type'].replace('_', '/')})",
            'surge_description': surge_event.surge_description,
            'magnitude': price_metrics['price_change_pct'],
            'strength': surge_event.surge_strength,
            'surge_calculation': surge_event.surge_calculation,
            'reversal': surge_event.reversal,
            'count_up': self.surge_counts[ticker]['up'],
            'count_down': self.surge_counts[ticker]['down'],
            'time': datetime.fromtimestamp(current_time).strftime('%H:%M:%S')  # Keep for display
        })
        
        # Update tracking with float timestamps
        surge_data['last_surge_time'] = float(current_time)
        surge_data['surge_count'] += 1
        surge_data['daily_surge_count'] += 1
        surge_data['last_surge_timestamp'] = float(current_time)
        
        logger.debug(f"✅ SURGE-DETECT: {ticker} - Updated tracking: "
                    f"TotalCount:{surge_data['surge_count']}, "
                    f"DailyCount:{surge_data['daily_surge_count']}")

    def reset_daily_counts(self):
        """
        Sprint 17: Reset daily surge counts for all tracked stocks.
        Called on market session changes.
        """
        for ticker in self.surge_counts:
            self.surge_counts[ticker] = {'up': 0, 'down': 0}
        # Note: We keep last_surge_direction to detect reversals across sessions

    
    def _validate_timestamp(self, timestamp, ticker, context=""):
        """Validate and log timestamp issues"""
        current_time = time.time()
        
        # Normalize to float
        if isinstance(timestamp, datetime):
            ts_float = timestamp.timestamp()
        else:
            ts_float = float(timestamp) if timestamp else current_time
        
        # Check for future timestamps
        if ts_float > current_time + 1:  # Allow 1 second tolerance
            logger.warning(f"⚠️ FUTURE TIMESTAMP [{context}] {ticker}: "
                        f"timestamp={ts_float}, current={current_time}, "
                        f"diff={ts_float - current_time:.2f}s in future")
            return False
        
        # Check for very old timestamps (>1 hour old)
        if ts_float < current_time - 3600:
            age_hours = (current_time - ts_float) / 3600
            logger.warning(f"⚠️ OLD TIMESTAMP [{context}] {ticker}: "
                        f"timestamp={ts_float}, age={age_hours:.1f} hours")
            return False
        
        return True
    
    '''
    def cleanup_last_sent_surges(self, max_age=300):
        """
        Clean up old entries from last_sent_surges.
        
        Args:
            max_age: Maximum age in seconds (defaults to 300)
        """
        current_time = time.time()
        to_remove = [surge_id for surge_id, sent_time in self.last_sent_surges.items()
                     if current_time - sent_time > max_age]
        for surge_id in to_remove:
            del self.last_sent_surges[surge_id]

    def cleanup_expired_surges(self, stock_data, ticker):
        """Clean up expired surge events from history with tracing."""
        try:
            current_time = time.time()  # Already float
            cleanup_start_time = current_time
            
            if not hasattr(stock_data, 'surge_data') or not stock_data.surge_data:
                return
            
            surge_history = stock_data.surge_data.get('surge_history', deque())
            initial_count = len(surge_history)
            
            # Remove expired surges
            non_expired = deque()
            expired_count = 0
            
            for surge in surge_history:
                # FIXED: Ensure comparison uses floats
                expiration = surge.get('expiration', 0)
                if isinstance(expiration, datetime):
                    expiration = expiration.timestamp()
                
                if expiration > current_time:
                    non_expired.append(surge)
                else:
                    expired_count += 1
            
            stock_data.surge_data['surge_history'] = non_expired
            
            # TRACE: Cleanup operation
            if tracer.should_trace(ticker) and expired_count > 0:
                tracer.trace(
                    ticker=ticker,
                    component='SurgeDetector',
                    action='surge_cleanup',
                    data={
                        'timestamp': current_time,
                        'input_count': ensure_int(initial_count),
                        'output_count': ensure_int(len(non_expired)),
                        'duration_ms': (time.time() - cleanup_start_time) * 1000,
                        'details': {
                            'expired_count': expired_count,
                            'remaining_count': len(non_expired)
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"Error cleaning up surges for {ticker}: {e}")
    '''