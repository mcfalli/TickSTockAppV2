import pytz
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from config.logging_config import get_domain_logger, LogDomain
from src.presentation.converters.transport_models import StockData
from src.core.domain.events.trend import TrendEvent
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
from src.processing.detectors.trend_detector import TrendDetector

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = get_domain_logger(LogDomain.CORE, 'trend_detector')

class TrendDetector:
    """
    Enhanced trend detection for stock price movements.
    
    Features:
    - Multiple time windows analysis
    - VWAP relationship tracking
    - Volume-based trend confirmation
    - Weighted recency calculations
    - Configurable trend thresholds
    """
    
    def __init__(self, config, cache_control=None):
        """
        Initialize the trend detector with configuration and cache control.
        
        Args:
            config: Application configuration dictionary
            cache_control: CacheControl instance for accessing cached data
        """
        init_start_time = time.time()
        
        self.last_sent_trends = {}
        self.config = config
        self.cache_control = cache_control
        
        self.eastern_tz = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))
        
        
        # ===== TIME WINDOWS =====
        self.short_window = config.get('TREND_SHORT_WINDOW_SECONDS', 180)      # 3 minutes
        self.medium_window = config.get('TREND_MEDIUM_WINDOW_SECONDS', 360)    # 6 minutes
        self.long_window = config.get('TREND_LONG_WINDOW_SECONDS', 600)        # 10 minutes
        
        # ===== COMPONENT WEIGHTS (Hardcoded) =====
        self.price_weight = 0.5      # Price movement importance
        self.vwap_weight = 0.3       # VWAP relationship importance
        self.volume_weight = 0.2     # Volume confirmation importance
        
        # ===== SENSITIVITY CONTROLS =====
        self.global_sensitivity = float(config.get('TREND_GLOBAL_SENSITIVITY', 1.0))
        self.direction_threshold = float(config.get('TREND_DIRECTION_THRESHOLD', 0.3))
        self.strength_threshold = float(config.get('TREND_STRENGTH_THRESHOLD', 0.6))
        self.retracement_threshold = float(config.get('TREND_RETRACEMENT_THRESHOLD', 0.4))
        
        # ===== MARKET-AWARE MULTIPLIERS =====
        self.market_open_multiplier = float(config.get('TREND_MARKET_OPEN_MULTIPLIER', 1.3))
        self.market_close_multiplier = float(config.get('TREND_MARKET_CLOSE_MULTIPLIER', 1.2))
        self.midday_multiplier = float(config.get('TREND_MIDDAY_MULTIPLIER', 0.9))
        
        # ===== ANALYSIS INTERVALS =====
        self.short_term_analysis_interval = config.get('TREND_SHORT_ANALYSIS_INTERVAL', 30)
        self.medium_term_analysis_interval = config.get('TREND_MEDIUM_ANALYSIS_INTERVAL', 60)
        self.long_term_analysis_interval = config.get('TREND_LONG_ANALYSIS_INTERVAL', 60)
        
        # ===== EMISSION CONTROL =====
        self.min_emission_interval = config.get('TREND_MIN_EMISSION_INTERVAL', 60)
        
        # ===== DATA MANAGEMENT (Hardcoded) =====
        self.max_history_points = 300      # Price history retention
        self.max_events = 20               # Event buffer size
        self.trend_max_age = 300          # Event cleanup age (5 minutes)
        
        # ===== ALGORITHM PARAMETERS (Hardcoded) =====
        self.recency_decay = 0.9          # Weight decay for older data
        self.min_data_points = 3          # Minimum points per window
        
        # ===== WARM-UP REQUIREMENTS (NEW) =====
        self.min_history_points_required = config.get('TREND_MIN_HISTORY_POINTS_REQUIRED', 30)  # Total points before analysis
        self.warmup_period_seconds = config.get('TREND_WARMUP_PERIOD_SECONDS', 180)  # 3 minutes default
        self.min_data_points_per_window = config.get('TREND_MIN_DATA_POINTS_PER_WINDOW', 10)  # Points per window

        # ===== FEATURE FLAGS =====
        self.volatility_window_adjustment = config.get('TREND_VOLATILITY_WINDOW_ADJUSTMENT', False)
        self.dynamic_retracement = config.get('TREND_DYNAMIC_RETRACEMENT', True)
        
        # ===== STATE TRACKING =====
        self.last_analysis_times = {}
        self.trend_counts = {}  # {ticker: {'up': count, 'down': count}}
        self.last_trend_direction = {}  # {ticker: 'up' or 'down'}
        self.last_trend_emission = {}  # Track when we last emitted a trend event
        
        # Update logging
        logger.info(f"TrendDetector initialized with:")
        logger.info(f"  - Windows: {self.short_window}s/{self.medium_window}s/{self.long_window}s")
        logger.info(f"  - Global Sensitivity: {self.global_sensitivity}")
        logger.info(f"  - Direction Threshold: {self.direction_threshold}")
        logger.info(f"  - Market Multipliers: Open={self.market_open_multiplier}, "
                    f"Close={self.market_close_multiplier}, Midday={self.midday_multiplier}")
        logger.info(f"  - Warm-up: {self.warmup_period_seconds}s with min {self.min_history_points_required} points")        

        # DIAGNOSTICS Add diagnostic tracking
        self._warmup_logged = set()  # Track which tickers have logged warmup complete
        self._diagnostic_interval = 30  # Log diagnostics every 30 seconds
        self._last_diagnostic_log = {}  # Track last diagnostic log time per ticker
        
        # DIAGNOSTICS Log configuration on startup
        logger.info("=" * 60)
        logger.info("TREND DETECTOR CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Warmup Period: {self.warmup_period_seconds}s")
        logger.info(f"Min History Points: {self.min_history_points_required}")
        logger.info(f"Min Points Per Window: {self.min_data_points_per_window}")
        logger.info(f"Windows: short={self.short_window}s, medium={self.medium_window}s, long={self.long_window}s")
        logger.info(f"Emission Interval: {self.min_emission_interval}s")
        logger.info(f"Component Weights: price={self.price_weight}, vwap={self.vwap_weight}, volume={self.volume_weight}")
        logger.info("=" * 60)


        # TRACE: Initialization complete
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='TrendDetector',
                action='initialization_complete',
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(0),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - init_start_time) * 1000,
                    'details': {
                        'short_window': self.short_window,
                        'medium_window': self.medium_window,
                        'long_window': self.long_window,
                        'direction_threshold': self.direction_threshold,
                        'strength_threshold': self.strength_threshold,
                        'global_sensitivity': self.global_sensitivity,
                        'market_aware': True,
                        'dynamic_retracement': self.dynamic_retracement
                    }
                }
            )

    
    def detect_trend(self, stock_data, ticker, price, vwap, volume, tick_vwap, tick_volume, 
                    tick_trade_size, timestamp=None, check_only=False):
        """
        Detect price trends using TrendDetectionEngine.
        Now uses centralized engine for all calculations with market awareness.
        Enhanced with comprehensive diagnostic logging and Sprint 48 adaptive thresholds.
        """
        start_time = time.time()
        import json
        
        try:
            # DIAGNOSTIC: Track data source
            data_source = "PRODUCTION" if self.config.get('USE_POLYGON_API') else "SYNTHETIC"
            
            # Initialize timestamp and result
            current_time = self._normalize_timestamp(timestamp)
            result = {"events": [], "trend_detected": False, "trend_info": None}
            
            # DIAGNOSTIC LOG 1: Entry point with source
            #logger.info(f"📊 DIAG TREND-ENTRY [{data_source}] {ticker}: price={price}, "
            #        f"vwap={vwap}, volume={volume}, tick_volume={tick_volume}, "
            #        f"timestamp={timestamp}")
            
            # DIAGNOSTIC: Timestamp validation
            if timestamp:
                self._validate_timestamp(timestamp, ticker, f"TREND-{data_source}")
            
            # DEPRECATED: check_only parameter
            if check_only:
                logger.warning(f"check_only parameter is deprecated. Use check_trend_conditions utility instead.")
                from src.processing.detectors.utils import check_trend_conditions
                return check_trend_conditions(stock_data, price, vwap, volume, self.config)
            
            # Initialize price history (state management)
            self._initialize_price_history(stock_data)
            history_before = len(stock_data.price_history)
            
            # Add current data point (state management)
            self._add_data_point(stock_data, price, vwap, volume, current_time)
            history_after = len(stock_data.price_history)
            
            # DIAGNOSTIC LOG 2: Data accumulation with timing
            if history_after % 5 == 0:  # Every 5 points
                if stock_data.price_history and len(stock_data.price_history) >= 2:
                    # Calculate time between points
                    recent_points = stock_data.price_history[-5:]
                    intervals = []
                    for i in range(1, len(recent_points)):
                        t1 = recent_points[i-1]['timestamp']
                        t2 = recent_points[i]['timestamp']
                        intervals.append(t2 - t1)
                    
                    avg_interval = sum(intervals) / len(intervals) if intervals else 0
                    min_interval = min(intervals) if intervals else 0
                    max_interval = max(intervals) if intervals else 0
                    
                    #logger.info(f"📈 DIAG TREND-ACCUMULATE [{data_source}] {ticker}: "
                    #        f"{history_after} points collected, "
                    #        f"avg_interval={avg_interval:.2f}s, "
                    #        f"min={min_interval:.2f}s, max={max_interval:.2f}s")
            
            # DIAGNOSTIC: Data quality check
            if history_after >= 5:
                recent_data = stock_data.price_history[-5:]
                recent_volumes = [p['volume'] for p in recent_data if p.get('volume') is not None]
                recent_vwaps = [p['vwap'] for p in recent_data if p.get('vwap') is not None]
                
                volume_availability = len(recent_volumes) / 5.0 * 100
                vwap_availability = len(recent_vwaps) / 5.0 * 100
                
                #logger.debug(f"📊 DIAG TREND-QUALITY [{data_source}] {ticker}: "
                #            f"volume_data={volume_availability:.0f}%, "
                #            f"vwap_data={vwap_availability:.0f}%")

            # SPRINT 48: Build dynamic configuration based on market context
            dynamic_config = self._build_dynamic_config(
                ticker=ticker,
                price=price,
                timestamp=current_time,
                price_history=stock_data.price_history
            )

            # Apply dynamic thresholds to config
            config_with_dynamic = self.config.copy()
            config_with_dynamic.update({
                'TREND_DIRECTION_THRESHOLD': dynamic_config['direction_threshold'],
                'TREND_STRENGTH_THRESHOLD': dynamic_config['strength_threshold'],
                'TREND_GLOBAL_SENSITIVITY': dynamic_config['global_sensitivity'],
                'TREND_MIN_EMISSION_INTERVAL': dynamic_config['min_emission_interval'],
                'TREND_RETRACEMENT_THRESHOLD': dynamic_config['retracement_threshold'],
                'TREND_MIN_DATA_POINTS_PER_WINDOW': dynamic_config['min_data_points_per_window'],
                'TREND_WARMUP_PERIOD_SECONDS': dynamic_config['warmup_period_seconds']
            })

            # Use dynamic values for checks
            min_history_required = dynamic_config['min_data_points_per_window'] * 3  # Need data for all windows
            warmup_period = dynamic_config['warmup_period_seconds']

            # Check Minimum History Requirement with detailed logging
            if history_after < min_history_required:
                # Estimate time to ready
                time_to_ready = "unknown"
                if history_after > 1:
                    recent_intervals = []
                    for i in range(max(1, history_after - 5), history_after):
                        if i > 0:
                            t1 = stock_data.price_history[i-1]['timestamp']
                            t2 = stock_data.price_history[i]['timestamp']
                            recent_intervals.append(t2 - t1)
                    
                    if recent_intervals:
                        avg_interval = sum(recent_intervals) / len(recent_intervals)
                        points_needed = min_history_required - history_after
                        time_to_ready = f"{(points_needed * avg_interval):.1f}s"
                
                #logger.info(f"🔍 DIAG TREND-WAITING [{data_source}] {ticker}: {history_after}/{min_history_required} points (need {min_history_required - history_after} more), ETA: {time_to_ready}")
                
                # Get diagnostics even when not ready
                if hasattr(self, 'get_trend_diagnostics'):
                    diag = self.get_trend_diagnostics(ticker, stock_data)
                    diag['data_source'] = data_source
                    # Format as single line
                    diag_str = json.dumps(diag, separators=(',', ':'))
                    #logger.debug(f"📊 DIAG TREND-DIAGNOSTICS [{data_source}] {ticker}: {diag_str}")
                
                # Still update stock data but don't detect trends
                self._update_stock_data_trends_from_engine(
                    stock_data, 
                    {'trend_direction': '→', 'trend_strength': 'neutral', 'score': 0},
                    {'short_trend': {'score': 0}, 'medium_trend': {'score': 0}, 'long_trend': {'score': 0}},
                    price, vwap
                )
                return result

            # DIAGNOSTIC LOG 3: Warmup check with progress
            if stock_data.price_history:
                first_point_time = stock_data.price_history[0]['timestamp']
                if isinstance(first_point_time, datetime):
                    ticker_age_seconds = (current_time - first_point_time).total_seconds()
                else:
                    ticker_age_seconds = current_time.timestamp() - first_point_time
                
                warmup_progress = min(100, (ticker_age_seconds / warmup_period) * 100)
                
                if ticker_age_seconds < warmup_period:
                    remaining = warmup_period - ticker_age_seconds
                    #logger.info(f"⏳ DIAG TREND-WARMUP [{data_source}] {ticker}: "
                    #        f"{ticker_age_seconds:.1f}s elapsed ({warmup_progress:.0f}%), "
                    #        f"{remaining:.1f}s remaining")
                    # Still update stock data but don't detect trends
                    self._update_stock_data_trends_from_engine(
                        stock_data, 
                        {'trend_direction': '→', 'trend_strength': 'neutral', 'score': 0},
                        {'short_trend': {'score': 0}, 'medium_trend': {'score': 0}, 'long_trend': {'score': 0}},
                        price, vwap
                    )
                    return result
                elif not hasattr(self, '_warmup_logged'):
                    self._warmup_logged = set()
                if ticker not in self._warmup_logged:
                    #logger.info(f"✅ DIAG TREND-READY [{data_source}] {ticker}: "
                    #        f"Warmup complete after {ticker_age_seconds:.1f}s")
                    self._warmup_logged.add(ticker)

            # DIAGNOSTIC LOG 4: Window analysis before calculation
            if hasattr(self, 'get_trend_diagnostics'):
                diag = self.get_trend_diagnostics(ticker, stock_data)
                diag['data_source'] = data_source
                windows_ready = diag.get('windows', {})
                
                # Check data distribution across windows
                short_coverage = windows_ready.get('short', {}).get('coverage_pct', 0)
                medium_coverage = windows_ready.get('medium', {}).get('coverage_pct', 0)
                long_coverage = windows_ready.get('long', {}).get('coverage_pct', 0)
                
                #logger.debug(f"📊 DIAG TREND-WINDOWS [{data_source}] {ticker}: "
                #            f"short={windows_ready.get('short', {}).get('points', 0)}/{dynamic_config['min_data_points_per_window']} ({short_coverage:.0f}%), "
                #            f"medium={windows_ready.get('medium', {}).get('points', 0)}/{dynamic_config['min_data_points_per_window']} ({medium_coverage:.0f}%), "
                #            f"long={windows_ready.get('long', {}).get('points', 0)}/{dynamic_config['min_data_points_per_window']} ({long_coverage:.0f}%)")

                # Check why no points in windows despite having history
                history_count = len(stock_data.price_history)
                if windows_ready.get('short', {}).get('points', 0) == 0 and history_count >= 5:
                    # Debug: Check why no points in windows
                    current_ts = current_time.timestamp() if isinstance(current_time, datetime) else current_time
                    recent_points = stock_data.price_history[-5:]
                    
                    point_ages = []
                    for p in recent_points:
                        p_ts = p['timestamp']
                        if isinstance(p_ts, datetime):
                            p_ts = p_ts.timestamp()
                        age = current_ts - p_ts
                        point_ages.append(age)
                    
                    #logger.warning(f"⚠️ DIAG TREND-WINDOW-ISSUE [{data_source}] {ticker}: "
                    #            f"Have {history_count} points but 0 in windows! "
                    #            f"Point ages: {[f'{age:.1f}s' for age in point_ages]}")

            # Initialize analysis times (state management)
            self._initialize_analysis_times(ticker)
            
            # Log dynamic configuration
            #logger.debug(f"DIAG-TREND-START [{ticker}]: price={price:.2f}, "
            #            f"period={dynamic_config['market_period']}, "
            #            f"bucket={dynamic_config['price_bucket']}")

            # CALCULATION: Use engine for trend calculations with dynamic config
            calc_start = time.time()
            trend_data = TrendDetectionEngine.calculate_multi_window_trends(
                price_history=stock_data.price_history,
                current_time=current_time,
                config=config_with_dynamic  # Use dynamic config here
            )
            calc_duration = (time.time() - calc_start) * 1000

            # DIAGNOSTIC LOG: Calculation results with dynamic context
            #logger.info(f"DIAG-TREND-CALC [{ticker}]: "
            #            f"score={trend_data.get('combined_score', 0):.4f} "
            #            f"(thresh={dynamic_config['direction_threshold']:.4f}) "
            #            f"direction={trend_data.get('combined_direction', 'neutral')} "
            #            f"market={dynamic_config['market_period']} "
            #            f"bucket={dynamic_config['price_bucket']} "
            #            f"calc_time={calc_duration:.1f}ms")
            
            # Log individual window scores with data points
            #logger.debug(f"📊 DIAG TREND-WINDOW-SCORES [{data_source}] {ticker}: "
            #            f"short={trend_data['short_trend']['score']:.3f} (n={trend_data['short_trend'].get('data_points', 0)}), "
            #            f"medium={trend_data['medium_trend']['score']:.3f} (n={trend_data['medium_trend'].get('data_points', 0)}), "
            #            f"long={trend_data['long_trend']['score']:.3f} (n={trend_data['long_trend'].get('data_points', 0)})")
            
            # Check for retracement with current price
            previous_score = getattr(stock_data, 'trend_score', 0)
            retracement_detected = TrendDetectionEngine.check_retracement(
                previous_score=previous_score,
                current_score=trend_data['combined_score'],
                current_price=price,  # Pass current price for dynamic threshold
                config=config_with_dynamic
            )
            
            if retracement_detected:
                logger.info(f"🔄 TREND-RETRACEMENT [{data_source}] {ticker}: "
                        f"Detected retracement, neutralizing trend "
                        f"(prev_score={previous_score:.3f}, curr_score={trend_data['combined_score']:.3f})")
                trend_data['combined_score'] = 0
                trend_data['combined_direction'] = 'neutral'
                trend_data['combined_strength'] = 'neutral'
            
            # EVALUATION: Use adaptive evaluation with dynamic thresholds
            conditions = TrendDetectionEngine.evaluate_trend_conditions_adaptive(
                trend_data=trend_data,
                config=self.config,
                dynamic_thresholds=dynamic_config
            )
            
            # Initialize tracking (state management)
            self._initialize_ticker_tracking(ticker)
            
            # Detect reversal (state check)
            reversal = self._detect_trend_reversal(ticker, conditions['raw_direction'])
            if reversal:
                logger.info(f"🔄 TREND-REVERSAL [{data_source}] {ticker}: {reversal}")
            
            # DIAGNOSTIC LOG: Emission decision with detailed reasoning
            if conditions['trend_direction'] != '→':
                should_emit = self._should_emit_trend_event_enhanced_adaptive(
                    ticker=ticker,
                    current_direction=conditions['raw_direction'],
                    current_time=current_time,
                    stock_data=stock_data,
                    min_emission_interval=dynamic_config['min_emission_interval']
                )
                
                # Check last emission time
                last_emission_info = "never"
                time_since_last = float('inf')
                if ticker in self.last_trend_emission:
                    last_time = self.last_trend_emission[ticker]
                    if isinstance(last_time, datetime):
                        time_since = (current_time - last_time).total_seconds()
                    else:
                        time_since = current_time.timestamp() - last_time
                    time_since_last = time_since
                    last_emission_info = f"{time_since:.1f}s ago"
                
                # Emission reasoning
                emission_reasons = []
                if should_emit:
                    if ticker not in self.last_trend_direction or self.last_trend_direction[ticker] != conditions['raw_direction']:
                        emission_reasons.append("direction_change")
                    if time_since_last >= dynamic_config['min_emission_interval']:
                        emission_reasons.append("time_elapsed")
                    if ticker not in self.last_trend_emission:
                        emission_reasons.append("first_trend")
                
                #logger.info(f"DIAG-TREND-DECISION [{ticker}]: "
                #            f"detected={conditions['is_trend']}, "
                #            f"emit={should_emit}, "
                #            f"strength={conditions['trend_strength']}, "
                #            f"interval={dynamic_config['min_emission_interval']}s, "
                #           f"reasons={emission_reasons}")
                
                if should_emit:
                    # CREATE EVENT: This stays in TrendDetector
                    trend_event = self._create_trend_event_from_engine_data(
                        ticker=ticker,
                        price=price,
                        current_time=current_time,
                        conditions=conditions,
                        trend_data=trend_data,
                        reversal=reversal,
                        vwap=vwap,
                        volume=volume,
                        stock_data=stock_data,
                        retracement_detected=retracement_detected
                    )
                    
                    result['events'].append(trend_event)
                    
                    # Log successful event creation with Sprint 48 context
                    #logger.info(f"DIAG-TREND-EVENT [{ticker}]: "
                    #            f"Created {conditions['raw_direction']} trend event "
                    #            f"(score={conditions['score']:.4f}, "
                    #            f"period={dynamic_config['market_period']}, "
                    #            f"bucket={dynamic_config['price_bucket']})")
                    
                    # Enhanced trace with market context and Sprint 48 info
                    if tracer.should_trace(ticker):
                        time_since_last = 0
                        if ticker in self.last_trend_emission:
                            time_since_last = (current_time - self.last_trend_emission[ticker]).total_seconds()
                        
                        tracer.trace(
                            ticker=ticker,
                            component='TrendDetector',
                            action='event_detected',
                            data={
                                'timestamp': time.time(),
                                'input_count': ensure_int(1),
                                'output_count': ensure_int(1),
                                'duration_ms': (time.time() - start_time) * 1000,
                                'details': {
                                    'event_type': 'trend',
                                    'direction': conditions['trend_direction'],
                                    'strength': conditions['trend_strength'],
                                    'score': conditions['score'],
                                    'reversal': reversal,
                                    'retracement_detected': retracement_detected,
                                    'time_since_last_emission': time_since_last,
                                    'market_period': dynamic_config['market_period'],
                                    'price_bucket': dynamic_config['price_bucket'],
                                    'volatility_category': dynamic_config.get('volatility_category', 'NORMAL'),
                                    'sensitivity_used': dynamic_config['global_sensitivity'],
                                    'direction_threshold': dynamic_config['direction_threshold'],
                                    'event_id': trend_event.event_id if hasattr(trend_event, 'event_id') else None,
                                    'data_source': data_source
                                }
                            }
                        )
                    
                    # Update emission time
                    self.last_trend_emission[ticker] = current_time
                    stock_data.last_trend_update = current_time
                #else:
                #    logger.debug(f"⏸️ DIAG TREND-SKIP-EMIT [{data_source}] {ticker}: "
                #                f"Event not emitted (conditions not met)")
            #else:
            #    logger.debug(f"➡️ DIAG TREND-NEUTRAL [{data_source}] {ticker}: "
            #                f"No trend detected (neutral direction)")
            
            # Periodic diagnostic logging
            current_timestamp = time.time()
            if not hasattr(self, '_last_diagnostic_log'):
                self._last_diagnostic_log = {}
            if not hasattr(self, '_diagnostic_interval'):
                self._diagnostic_interval = 30  # Log every 30 seconds
                
            if ticker not in self._last_diagnostic_log or \
            current_timestamp - self._last_diagnostic_log.get(ticker, 0) > self._diagnostic_interval:
                
                if hasattr(self, 'get_trend_diagnostics'):
                    diag = self.get_trend_diagnostics(ticker, stock_data)
                    diag['data_source'] = data_source
                    diag['market_period'] = dynamic_config['market_period']
                    diag['price_bucket'] = dynamic_config['price_bucket']
                    diag['thresholds'] = {
                        'direction': dynamic_config['direction_threshold'],
                        'strength': dynamic_config['strength_threshold']
                    }
                    # Format as single line
                    diag_str = json.dumps(diag, separators=(',', ':'))
                    #logger.info(f"📊 DIAG TREND-PERIODIC-DIAGNOSTIC [{data_source}] {ticker}: {diag_str}")
                    
                    # Also log human-readable summary
                    #logger.info(f"📊 DIAG TREND-SUMMARY [{data_source}] {ticker}: "
                    #        f"points={diag.get('history_points', 0)} "
                    #        f"age={diag.get('data_age_seconds', 0):.1f}s "
                    #        f"warmup={diag.get('warmup_complete', False)} "
                    #        f"ready={diag.get('ready_to_detect', False)} "
                    #        f"period={dynamic_config['market_period']} "
                    #        f"bucket={dynamic_config['price_bucket']}")
                    
                    self._last_diagnostic_log[ticker] = current_timestamp
            
            # Update stock data trends (state management)
            self._update_stock_data_trends_from_engine(
                stock_data, conditions, trend_data, price, vwap
            )
            
            # Update last analysis times (state management)
            ticker_key = f"trend_{ticker}"
            self.last_analysis_times[ticker_key] = {
                'short': current_time,
                'medium': current_time,
                'long': current_time
            }
            
            # Final diagnostic summary
            total_duration = (time.time() - start_time) * 1000
            #logger.debug(f"📊 DIAG TREND-COMPLETE [{data_source}] {ticker}: "
            #            f"total_time={total_duration:.1f}ms, "
            #            f"events_created={len(result['events'])}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ TREND-ERROR [{data_source if 'data_source' in locals() else 'UNKNOWN'}] {ticker}: "
                        f"Error in detect_trend: {e}", exc_info=True)
            return {"events": [], "trend_detected": False, "trend_info": None}


    def _should_emit_trend_event_enhanced_adaptive(self, ticker, current_direction, 
                                                current_time, stock_data, 
                                                min_emission_interval):
        """
        Enhanced emission logic with adaptive interval.
        """
        # Check warm-up period (unchanged)
        if stock_data.price_history:
            first_point_time = stock_data.price_history[0]['timestamp']
            if isinstance(current_time, datetime):
                current_timestamp = current_time.timestamp()
            else:
                current_timestamp = float(current_time) if current_time else time.time()
            
            ticker_age_seconds = current_timestamp - first_point_time
            
            # Use dynamic warmup period
            warmup_required = min_emission_interval // 3  # Adaptive warmup
            if ticker_age_seconds < warmup_required:
                #logger.debug(f"DIAG-TREND [{ticker}]: Still in warm-up period: "
                #            f"{ticker_age_seconds:.1f}s < {warmup_required}s")
                return False
        
        # Emit if direction changed
        if ticker not in self.last_trend_direction or self.last_trend_direction[ticker] != current_direction:
            return True
        
        # Emit if enough time has passed (using dynamic interval)
        if ticker in self.last_trend_emission:
            last_emission_time = self.last_trend_emission[ticker]
            
            if isinstance(current_time, datetime) and isinstance(last_emission_time, datetime):
                time_since_last = (current_time - last_emission_time).total_seconds()
            else:
                if isinstance(current_time, datetime):
                    current_timestamp = current_time.timestamp()
                else:
                    current_timestamp = float(current_time) if current_time else time.time()
                    
                if isinstance(last_emission_time, datetime):
                    last_timestamp = last_emission_time.timestamp()
                else:
                    last_timestamp = float(last_emission_time)
                    
                time_since_last = current_timestamp - last_timestamp
            
            if time_since_last >= min_emission_interval:
                return True
        else:
            return True
        
        return False


    def _create_trend_event_from_engine_data(self, ticker, price, current_time, conditions,
                                            trend_data, reversal, vwap, volume, stock_data,
                                            retracement_detected):
        """
        Create a TrendEvent from engine calculation results.
        This method handles event-specific logic like counting and labeling.
        """
        from src.processing.detectors.utils import (get_base_price, calculate_percent_change, 
                                    calculate_relative_volume, 
                                    generate_event_label)
        
        # Update counts based on direction
        if conditions['raw_direction'] == 'up':
            self.trend_counts[ticker]['up'] += 1
        elif conditions['raw_direction'] == 'down':
            self.trend_counts[ticker]['down'] += 1
            
        if conditions['raw_direction'] in ['up', 'down']:
            self.last_trend_direction[ticker] = conditions['raw_direction']
        
        # Get base price
        base_price, base_price_source = get_base_price(
            stock_data=stock_data,
            market_status=getattr(stock_data, 'market_status', 'REGULAR'),
            market_open_price=getattr(stock_data, 'market_open_price', None),
            current_price=price
        )
        
        # Calculate metrics
        percent_change = calculate_percent_change(price, base_price)
        average_volume = getattr(stock_data, 'average_volume', None)
        rel_volume = calculate_relative_volume(volume, average_volume)
        vwap_divergence = calculate_vwap_divergence(price, vwap)
        
        # Build calculation transparency
        calc_transparency = {
            'trend_windows': {
                'short': self._format_window_data(trend_data['short_trend']),
                'medium': self._format_window_data(trend_data['medium_trend']),
                'long': self._format_window_data(trend_data['long_trend'])
            },
            'overall_calculation': {
                'formula': 'overall_score = (short * 0.3 + medium * 0.4 + long * 0.3)',
                'result': trend_data['combined_score']
            },
            'retracement_detected': retracement_detected
        }
        
        # Create typed TrendEvent
        trend_event = TrendEvent(
            ticker=ticker,
            type='trend',
            price=price,
            time=time.time(),
            direction=conditions['raw_direction'],  # Use raw 'up' or 'down', not arrow
            reversal=reversal if reversal else False,
            count=self.trend_counts[ticker]['up'] + self.trend_counts[ticker]['down'],
            count_up=self.trend_counts[ticker]['up'],
            count_down=self.trend_counts[ticker]['down'],
            percent_change=percent_change,
            vwap=vwap,
            vwap_divergence=vwap_divergence,
            volume=volume,
            rel_volume=rel_volume,
            label=generate_event_label(
                'trend', ticker, 
                direction=conditions['trend_direction'], 
                strength=conditions['trend_strength']
            ),
            # Trend-specific fields
            trend_strength=conditions['trend_strength'],
            trend_score=conditions['score'],
            trend_short_score=trend_data['short_trend']['score'],
            trend_medium_score=trend_data['medium_trend']['score'],
            trend_long_score=trend_data['long_trend']['score'],
            trend_vwap_position='above' if price > vwap else 'below' if vwap else 'unknown',
            trend_age=0,
            trend_calc_transparency=calc_transparency
        )
        
        return trend_event


    def _build_dynamic_config(self, ticker: str, price: float, timestamp: datetime,
                            price_history: list = None) -> Dict[str, Any]:
        """
        Build dynamic configuration based on market context.
        
        Args:
            ticker: Stock ticker
            price: Current stock price
            timestamp: Current timestamp
            price_history: Price history for volatility calculation
            
        Returns:
            Dictionary with dynamic configuration values
        """
        try:
            from src.processing.detectors.utils import (
                get_market_period_detailed, 
                get_price_bucket,
                calculate_volatility_category
            )
            
            # Determine market period
            market_period = get_market_period_detailed(timestamp, self.config.get('MARKET_TIMEZONE', 'US/Eastern'))
            
            # Determine price bucket
            price_bucket = get_price_bucket(price)
            
            # Calculate volatility category
            volatility_category = 'NORMAL'
            if price_history and len(price_history) >= 10:
                volatility_category = calculate_volatility_category(price_history)
            
            # Get dynamic thresholds from engine
            dynamic_thresholds = TrendDetectionEngine.get_dynamic_thresholds(
                market_period=market_period,
                price_bucket=price_bucket,
                volatility_category=volatility_category,
                config=self.config
            )
            
            # Add context info for logging
            dynamic_thresholds['market_period'] = market_period
            dynamic_thresholds['price_bucket'] = price_bucket
            dynamic_thresholds['volatility_category'] = volatility_category
            
            # Log the context for debugging
            #logger.debug(f"DIAG-TREND-CONTEXT [{ticker}]: price=${price:.2f}, period={market_period}, bucket={price_bucket}, volatility={volatility_category}")
            #logger.debug(f"DIAG-TREND-THRESH [{ticker}]: dir={dynamic_thresholds['direction_threshold']:.4f}, str={dynamic_thresholds['strength_threshold']:.4f}, sens={dynamic_thresholds['global_sensitivity']:.2f}")
            
            return dynamic_thresholds
            
        except Exception as e:
            logger.error(f"Error building dynamic config for {ticker}: {e}")
            # Return base config on error
            return {
                'direction_threshold': self.config.get('TREND_DIRECTION_THRESHOLD', 0.3),
                'strength_threshold': self.config.get('TREND_STRENGTH_THRESHOLD', 0.6),
                'global_sensitivity': self.config.get('TREND_GLOBAL_SENSITIVITY', 1.0),
                'min_emission_interval': self.config.get('TREND_MIN_EMISSION_INTERVAL', 60),
                'retracement_threshold': self.config.get('TREND_RETRACEMENT_THRESHOLD', 0.4),
                'min_data_points_per_window': self.config.get('TREND_MIN_DATA_POINTS_PER_WINDOW', 10),
                'warmup_period_seconds': self.config.get('TREND_WARMUP_PERIOD_SECONDS', 180),
                'market_period': 'MIDDAY',
                'price_bucket': 'MID',
                'volatility_category': 'NORMAL'
            }

    def _format_window_data(self, window_trend):
        """Format window trend data for transparency."""
        return {
            'score': window_trend['score'],
            'direction': window_trend['direction'],
            'strength': window_trend['strength'],
            'data_points': window_trend['data_points'],
            'components': {
                'price': window_trend['price_component'],
                'vwap': window_trend['vwap_component'],
                'volume': window_trend['volume_component']
            }
        }

    def _should_emit_trend_event_enhanced(self, ticker, current_direction, current_time, stock_data):
        """
        Enhanced emission logic with configurable interval and warm-up period.
        Fixed to handle float timestamps consistently.
        """
        # ===== NEW: Check Warm-up Period =====
        if stock_data.price_history:
            first_point_time = stock_data.price_history[0]['timestamp']
            
            # CRITICAL FIX: Handle timestamp comparison consistently
            # Both timestamps should be compared as floats
            if isinstance(current_time, datetime):
                current_timestamp = current_time.timestamp()
            else:
                current_timestamp = float(current_time) if current_time else time.time()
            
            # first_point_time is now always a float (seconds) due to _add_data_point fix
            ticker_age_seconds = current_timestamp - first_point_time
                
            if ticker_age_seconds < self.warmup_period_seconds:
                logger.debug(f"🔍 TREND-DETECT: {ticker} - Still in warm-up period: "
                            f"{ticker_age_seconds:.1f}s < {self.warmup_period_seconds}s")
                return False
        
        # Emit if direction changed
        if ticker not in self.last_trend_direction or self.last_trend_direction[ticker] != current_direction:
            return True
        
        # Emit if enough time has passed (now configurable)
        if ticker in self.last_trend_emission:
            # Handle last emission time which might be datetime or float
            last_emission_time = self.last_trend_emission[ticker]
            
            if isinstance(current_time, datetime) and isinstance(last_emission_time, datetime):
                time_since_last = (current_time - last_emission_time).total_seconds()
            else:
                # Convert both to float for comparison
                if isinstance(current_time, datetime):
                    current_timestamp = current_time.timestamp()
                else:
                    current_timestamp = float(current_time) if current_time else time.time()
                    
                if isinstance(last_emission_time, datetime):
                    last_timestamp = last_emission_time.timestamp()
                else:
                    last_timestamp = float(last_emission_time)
                    
                time_since_last = current_timestamp - last_timestamp
            
            if time_since_last >= self.min_emission_interval:
                return True
        else:
            return True
        
        return False

    def _update_stock_data_trends_from_engine(self, stock_data, conditions, trend_data, price, vwap):
        """Update stock data with trend information from engine results."""
        stock_data.trend_direction = conditions['trend_direction']
        stock_data.trend_strength = conditions['trend_strength']
        stock_data.trend_score = conditions['score']
        
        # Store window trends
        stock_data.short_trend = trend_data['short_trend']
        stock_data.medium_trend = trend_data['medium_trend']
        stock_data.long_trend = trend_data['long_trend']
        
        # VWAP position
        if vwap is not None and price is not None:
            stock_data.vwap_position = 'above' if price > vwap else 'below'
            stock_data.vwap_divergence = ((price - vwap) / vwap * 100) if vwap > 0 else 0
        else:
            stock_data.vwap_position = 'unknown'
            stock_data.vwap_divergence = 0
            
    def _normalize_timestamp(self, timestamp):
        """Normalize timestamp to datetime with timezone."""
        if timestamp is None:
            timestamp = time.time()
            
        if isinstance(timestamp, (int, float)):
            current_time = datetime.fromtimestamp(timestamp)
        else:
            current_time = timestamp
            
        # Ensure timezone
        if current_time.tzinfo is None:
            current_time = self.eastern_tz.localize(current_time)
            
        return current_time

    def _initialize_price_history(self, stock_data):
        """Initialize price history if needed."""
        if not hasattr(stock_data, 'price_history') or stock_data.price_history is None:
            stock_data.price_history = []

    def _add_data_point(self, stock_data, price, vwap, volume, timestamp):
        """Add current data point to price history with timestamp correction."""
        # CRITICAL FIX: Detect and correct future timestamps
        current_time = time.time()
        
        # Convert datetime to float timestamp for consistent storage
        if isinstance(timestamp, datetime):
            timestamp_float = timestamp.timestamp()
        else:
            timestamp_float = float(timestamp) if timestamp is not None else current_time
        
        # Check if timestamp is in the future (common with synthetic data)
        if timestamp_float > current_time + 60:  # More than 60 seconds in future
            time_offset = timestamp_float - current_time
            logger.warning(f"📊 TREND-TIMESTAMP-FIX: Correcting future timestamp "
                        f"offset={time_offset:.1f}s for {stock_data.ticker if hasattr(stock_data, 'ticker') else 'unknown'}")
            # Use current time instead
            timestamp_float = current_time
        
        data_point = {
            'price': price,
            'vwap': vwap,
            'volume': volume,
            'timestamp': timestamp_float  # Always store as float seconds
        }
        stock_data.price_history.append(data_point)
        
        # Limit history
        if len(stock_data.price_history) > self.max_history_points:
            stock_data.price_history = stock_data.price_history[-self.max_history_points:]

    def _initialize_analysis_times(self, ticker):
        """Initialize last analysis times for the ticker."""
        ticker_key = f"trend_{ticker}"
        if ticker_key not in self.last_analysis_times:
            self.last_analysis_times[ticker_key] = {
                'short': datetime.min.replace(tzinfo=self.eastern_tz),
                'medium': datetime.min.replace(tzinfo=self.eastern_tz),
                'long': datetime.min.replace(tzinfo=self.eastern_tz)
            }

    
    
    def _initialize_ticker_tracking(self, ticker):
        """Initialize tracking for the ticker if needed."""
        if ticker not in self.trend_counts:
            self.trend_counts[ticker] = {'up': 0, 'down': 0}
            
            # TRACE: Ticker initialized
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='TrendDetector',
                    action='ticker_initialized',
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(0),
                        'output_count': ensure_int(0),
                        'duration_ms': 0,
                        'details': {
                            'counts': {'up': 0, 'down': 0}
                        }
                    }
                )

    def _detect_trend_reversal(self, ticker, current_direction):
        """Detect if a trend reversal has occurred."""
        reversal = None
        if current_direction and ticker in self.last_trend_direction:
            if self.last_trend_direction[ticker] == 'up' and current_direction == 'down':
                reversal = 'up-now-down'
            elif self.last_trend_direction[ticker] == 'down' and current_direction == 'up':
                reversal = 'down-now-up'
        return reversal



    def _should_emit_trend_event(self, ticker, current_direction, current_time):
        """Determine if we should emit a trend event."""
        # Emit if direction changed
        if ticker not in self.last_trend_direction or self.last_trend_direction[ticker] != current_direction:
            return True
        
        # Emit if enough time has passed
        if ticker in self.last_trend_emission:
            time_since_last = (current_time - self.last_trend_emission[ticker]).total_seconds()
            if time_since_last >= self.medium_term_analysis_interval:
                return True
        else:
            return True
        
        return False

    def _create_trend_event(self, ticker, price, current_time, trend_characteristics,
                           window_trends, overall_score, reversal, vwap, volume, 
                           stock_data, calc_transparency):
        """Create a typed TrendEvent."""
        # Update counts
        if trend_characteristics['current_direction']:
            self.trend_counts[ticker][trend_characteristics['current_direction']] += 1
            self.last_trend_direction[ticker] = trend_characteristics['current_direction']
        
        # Get base price
        base_price, base_price_source = get_base_price(
            stock_data=stock_data,
            market_status=getattr(stock_data, 'market_status', 'REGULAR'),
            market_open_price=getattr(stock_data, 'market_open_price', None),
            current_price=price
        )
        
        # Calculate metrics
        percent_change = calculate_percent_change(price, base_price)
        average_volume = getattr(stock_data, 'average_volume', None)
        rel_volume = calculate_relative_volume(volume, average_volume)
        vwap_divergence = calculate_vwap_divergence(price, vwap)
        
        # Create typed TrendEvent directly
        trend_event = TrendEvent(
            ticker=ticker,
            type='trend',
            price=price,
            time=time.time(),
            direction=trend_characteristics['current_direction'],
            reversal=reversal if reversal else False,
            count=self.trend_counts[ticker]['up'] + self.trend_counts[ticker]['down'],
            count_up=self.trend_counts[ticker]['up'],
            count_down=self.trend_counts[ticker]['down'],
            percent_change=percent_change,
            vwap=vwap,
            vwap_divergence=vwap_divergence,
            volume=volume,
            rel_volume=rel_volume,
            label=generate_event_label(
                'trend', ticker, 
                direction=trend_characteristics['trend_direction'], 
                strength=trend_characteristics['trend_strength']
            ),
            # Trend-specific fields
            trend_strength=trend_characteristics['trend_strength'],
            trend_score=overall_score,
            trend_short_score=window_trends['short']['score'],
            trend_medium_score=window_trends['medium']['score'],
            trend_long_score=window_trends['long']['score'],
            trend_vwap_position='above' if price > vwap else 'below' if vwap else 'unknown',
            trend_age=0,
            trend_calc_transparency=calc_transparency
        )
        
        return trend_event

    def _update_stock_data_trends(self, stock_data, trend_characteristics, 
                                 overall_score, price, vwap):
        """Update stock data with trend information."""
        stock_data.trend_direction = trend_characteristics['trend_direction']
        stock_data.trend_strength = trend_characteristics['trend_strength']
        stock_data.trend_score = overall_score
        
        if vwap is not None and price is not None:
            stock_data.vwap_position = 'above' if price > vwap else 'below'
            stock_data.vwap_divergence = ((price - vwap) / vwap * 100) if vwap > 0 else 0
        else:
            stock_data.vwap_position = 'unknown'
            stock_data.vwap_divergence = 0
    
    def reset_daily_counts(self):
        """
        Sprint 17: Reset daily trend counts for all tracked stocks.
        Called on market session changes.
        """
        start_time = time.time()
        ticker_count = len(self.trend_counts)
        
        for ticker in self.trend_counts:
            self.trend_counts[ticker] = {'up': 0, 'down': 0}
        # Optionally clear last directions to start fresh
        # self.last_trend_direction.clear()
        
        # TRACE: Daily reset
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='TrendDetector',
                action='daily_counts_reset',
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(ticker_count),
                    'output_count': ensure_int(ticker_count),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        'tickers_reset': ticker_count
                    }
                }
            )
    
    def _get_strength_formula(self, score):
        """Get the formula used to determine trend strength."""
        abs_score = abs(score)
        if abs_score > self.strength_threshold:
            return f"|score| > {self.strength_threshold} → 'strong'"
        elif abs_score > self.direction_threshold * 2:
            return f"|score| > {self.direction_threshold * 2} → 'moderate'"
        elif abs_score > self.direction_threshold:
            return f"|score| > {self.direction_threshold} → 'weak'"
        else:
            return f"|score| <= {self.direction_threshold} → 'neutral'"


    
    
    def get_trend_diagnostics(self, ticker: str, stock_data=None) -> Dict[str, Any]:
        """Get comprehensive diagnostics for trend detection debugging."""
        
        current_time = time.time()
        diagnostics = {
            'ticker': ticker,
            'timestamp': current_time,
            'config': {
                'warmup_period': self.warmup_period_seconds,
                'min_history_points': self.min_history_points_required,
                'min_points_per_window': self.min_data_points_per_window,
                'windows': {
                    'short': self.short_window,
                    'medium': self.medium_window,
                    'long': self.long_window
                }
            }
        }
        
        # Check if we have stock data
        if not stock_data or not hasattr(stock_data, 'price_history'):
            diagnostics['error'] = 'No stock data or price history'
            return diagnostics
        
        # Price history analysis
        history_points = len(stock_data.price_history) if stock_data.price_history else 0
        diagnostics['history_points'] = history_points
        
        if stock_data.price_history and history_points > 0:
            # Time analysis
            first_point = stock_data.price_history[0]
            last_point = stock_data.price_history[-1]
            
            first_time = first_point['timestamp']
            if isinstance(first_time, datetime):
                first_timestamp = first_time.timestamp()
            else:
                first_timestamp = float(first_time)
            
            # FIX: Use the last point's timestamp as reference, not current_time
            last_time = last_point['timestamp']
            if isinstance(last_time, datetime):
                last_timestamp = last_time.timestamp()
            else:
                last_timestamp = float(last_time)
                
            # Calculate age from the perspective of the last data point
            age_seconds = last_timestamp - first_timestamp
            diagnostics['data_age_seconds'] = age_seconds
            diagnostics['warmup_complete'] = age_seconds >= self.warmup_period_seconds
            diagnostics['warmup_remaining'] = max(0, self.warmup_period_seconds - age_seconds)
            
            # Data frequency analysis
            if history_points > 1:
                intervals = []
                for i in range(1, min(10, history_points)):  # Last 10 intervals
                    t1 = stock_data.price_history[-i-1]['timestamp']
                    t2 = stock_data.price_history[-i]['timestamp']
                    
                    # Convert to timestamps
                    if isinstance(t1, datetime):
                        t1 = t1.timestamp()
                    if isinstance(t2, datetime):
                        t2 = t2.timestamp()
                        
                    intervals.append(t2 - t1)
                
                diagnostics['recent_intervals'] = intervals
                diagnostics['avg_interval'] = sum(intervals) / len(intervals) if intervals else 0
                diagnostics['max_interval'] = max(intervals) if intervals else 0
            
            # Window analysis - FIX: Use last_timestamp as reference
            windows_analysis = {}
            for window_name, window_seconds in [
                ('short', self.short_window),
                ('medium', self.medium_window),
                ('long', self.long_window)
            ]:
                window_start = last_timestamp - window_seconds  # FIX: Use last data point time
                window_points = []
                
                for point in stock_data.price_history:
                    point_time = point['timestamp']
                    if isinstance(point_time, datetime):
                        point_timestamp = point_time.timestamp()
                    else:
                        point_timestamp = float(point_time)
                        
                    if point_timestamp >= window_start:
                        window_points.append(point)
                
                windows_analysis[window_name] = {
                    'points': len(window_points),
                    'required': self.min_data_points_per_window,
                    'sufficient': len(window_points) >= self.min_data_points_per_window,
                    'coverage_pct': (len(window_points) / self.min_data_points_per_window * 100) 
                                if self.min_data_points_per_window > 0 else 0
                }
            
            diagnostics['windows'] = windows_analysis
            
            # Overall readiness
            all_windows_ready = all(w['sufficient'] for w in windows_analysis.values())
            diagnostics['ready_to_detect'] = (
                history_points >= self.min_history_points_required and
                age_seconds >= self.warmup_period_seconds and
                all_windows_ready
            )
            
            # Last emission info
            if ticker in self.last_trend_emission:
                last_emission = self.last_trend_emission[ticker]
                if isinstance(last_emission, datetime):
                    last_emission_time = last_emission.timestamp()
                else:
                    last_emission_time = float(last_emission)
                
                diagnostics['last_emission'] = {
                    'time_ago': current_time - last_emission_time,
                    'can_emit_again': (current_time - last_emission_time) >= self.min_emission_interval
                }
        
        return diagnostics
    
    
    def _validate_timestamp(self, timestamp, ticker, context=""):
        """Validate and log timestamp issues"""
        current_time = time.time()
        
        # Normalize to float
        if isinstance(timestamp, datetime):
            ts_float = timestamp.timestamp()
        else:
            ts_float = float(timestamp)
        
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
    

    def cleanup_trend_tracking(self, max_age=None):
        """Clean up old trend tracking data."""
        start_time = time.time()
        max_age = max_age or self.trend_max_age
        current_time = time.time()
        to_remove = []
        
        for trend_id, sent_time in self.last_sent_trends.items():
            if current_time - sent_time > max_age:
                to_remove.append(trend_id)
        
        for trend_id in to_remove:
            del self.last_sent_trends[trend_id]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old trend entries from last_sent_trends")
            
            # TRACE: Cleanup complete
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component='TrendDetector',
                    action='cleanup_complete',
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(len(self.last_sent_trends) + len(to_remove)),
                        'output_count': ensure_int(len(self.last_sent_trends)),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            'entries_removed': len(to_remove),
                            'entries_remaining': len(self.last_sent_trends),
                            'max_age_seconds': max_age
                        }
                    }
                )