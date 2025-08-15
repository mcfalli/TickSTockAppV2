"""
Core detection engines for trend and surge detection.
Pure calculation logic without side effects, events, or state management.
"""

from typing import Dict, Any, Optional, List, Tuple
from collections import deque
from datetime import datetime
import time
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'detection_engines')


#-------------------------------------------------------------
# HIGHLOW Detection Engine
#-------------------------------------------------------------
class HighLowDetectionEngine:
    """Pure high/low detection calculation engine."""
    
    @staticmethod
    def get_price_thresholds(price: float, config: Dict[str, Any]) -> Dict[str, float]:
        """
        Get price-based thresholds for high/low detection.
        
        Returns:
            Dict with min_price_change and min_percent_change
        """
        # Base thresholds from config
        base_min_price = config.get('HIGHLOW_MIN_PRICE_CHANGE', 0.01)
        base_min_percent = config.get('HIGHLOW_MIN_PERCENT_CHANGE', 0.1)
        
        # Price-based matrix (similar to surge)
        if price < 1.0:
            # Penny stocks - need larger % moves
            return {
                'min_price_change': base_min_price * 0.5,  # $0.005
                'min_percent_change': base_min_percent * 2  # 0.2%
            }
        elif price < 5.0:
            # Low-priced stocks
            return {
                'min_price_change': base_min_price,        # $0.01
                'min_percent_change': base_min_percent * 1.5  # 0.15%
            }
        elif price < 25.0:
            # Mid-priced stocks
            return {
                'min_price_change': base_min_price * 2,    # $0.02
                'min_percent_change': base_min_percent      # 0.1%
            }
        elif price < 100.0:
            # Higher-priced stocks
            return {
                'min_price_change': base_min_price * 5,    # $0.05
                'min_percent_change': base_min_percent * 0.8  # 0.08%
            }
        else:
            # Expensive stocks
            return {
                'min_price_change': base_min_price * 10,   # $0.10
                'min_percent_change': base_min_percent * 0.5  # 0.05%
            }
#-------------------------------------------------------------
# Surge Detection Engine
#-------------------------------------------------------------
class SurgeDetectionEngine:
    """
    Pure surge detection calculation engine.
    No state management, no event creation, just mathematics.
    """
    
    @staticmethod
    def calculate_surge_metrics(
        buffer: deque,
        current_price: float,
        current_volume: Optional[float],
        current_time: float,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate all surge metrics from buffer data.
        
        Args:
            buffer: Deque of price/volume/timestamp data points
            current_price: Current price
            current_volume: Current volume (may be None)
            current_time: Current timestamp
            config: Configuration dictionary
            
        Returns:
            Dictionary containing:
            - baseline_price: Price to compare against
            - price_change_pct: Percentage change from baseline
            - price_change_abs: Absolute price change
            - direction: 'up', 'down', or 'neutral'
            - volume_multiplier: Current volume vs average
            - avg_volume: Average volume from buffer
            - time_from_baseline: Seconds since baseline
        """
        try:
            # Get interval from config
            interval_seconds = config.get('SURGE_INTERVAL_SECONDS', 5)
            
            # Find baseline price from interval seconds ago
            baseline_time = current_time - interval_seconds
            baseline_price = None
            baseline_point = None
            
            # Look for the most recent price that's at least interval_seconds old
            for point in reversed(list(buffer)[:-1]):  # Exclude current point if in buffer
                if point['timestamp'] <= baseline_time:
                    baseline_price = point['price']
                    baseline_point = point
                    break
            
            # If no old enough price, use the oldest available (but not current)
            if baseline_price is None and len(buffer) > 0:
                baseline_price = buffer[0]['price']
                baseline_point = buffer[0]
            else:
                baseline_price = baseline_price or current_price  # Fallback
            
            # Calculate price change
            price_change_pct = ((current_price - baseline_price) / baseline_price * 100) if baseline_price > 0 else 0
            price_change_abs = current_price - baseline_price
            
            # Determine direction
            if price_change_pct > 0:
                direction = "up"
            elif price_change_pct < 0:
                direction = "down"
            else:
                direction = "neutral"
            
            # Calculate volume metrics
            buffer_volumes = [point['volume'] for point in buffer if point.get('volume') is not None]
            
            if len(buffer_volumes) > 1:
                # Exclude current volume from average if it's in the buffer
                avg_volume = sum(buffer_volumes[:-1]) / len(buffer_volumes[:-1])
            elif len(buffer_volumes) == 1:
                avg_volume = buffer_volumes[0]
            else:
                avg_volume = current_volume or 0
            
            volume_multiplier = (current_volume / avg_volume) if (avg_volume > 0 and current_volume) else 1.0
            
            # Calculate time from baseline
            time_from_baseline = current_time - (baseline_point['timestamp'] if baseline_point else current_time)
            
            return {
                'baseline_price': baseline_price,
                'price_change_pct': price_change_pct,
                'price_change_abs': price_change_abs,
                'direction': direction,
                'volume_multiplier': volume_multiplier,
                'avg_volume': avg_volume,
                'time_from_baseline': time_from_baseline,
                'actual_volume': current_volume
            }
            
        except Exception as e:
            logger.error(f"Error calculating surge metrics: {e}")
            return {
                'baseline_price': current_price,
                'price_change_pct': 0,
                'price_change_abs': 0,
                'direction': 'neutral',
                'volume_multiplier': 1.0,
                'avg_volume': 0,
                'time_from_baseline': 0,
                'actual_volume': current_volume
            }
    

    @staticmethod
    def evaluate_surge_conditions(
        metrics: Dict[str, Any],
        price: float,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate if surge conditions are met based on metrics.
        Supports multiple detection modes: STRICT, OR, ADAPTIVE
        
        Args:
            metrics: Output from calculate_surge_metrics
            price: Current price (for threshold calculation)
            config: Configuration dictionary
            
        Returns:
            Dictionary containing:
            - is_surge: Boolean indicating if surge detected
            - is_price_surge: Boolean for price component
            - is_volume_surge: Boolean for volume component
            - trigger_type: 'price', 'volume', 'price_and_volume', 'price_driven', 'volume_driven'
            - surge_score: Calculated surge score
            - surge_strength: 'weak', 'moderate', or 'strong'
            - thresholds_used: Dict of thresholds applied
        """
        try:
            # Get direction-specific multipliers
            direction = metrics['direction']
            dir_multiplier = 1.0
            if direction == "up":
                dir_multiplier = config.get('SURGE_UP_THRESHOLD_MULTIPLIER', 1.0)
            elif direction == "down":
                dir_multiplier = config.get('SURGE_DOWN_THRESHOLD_MULTIPLIER', 1.0)
            
            # Get price thresholds
            threshold_pct, min_dollar_change = SurgeDetectionEngine.get_price_thresholds(price, config)
            threshold_pct *= dir_multiplier
            
            # Get volume threshold
            volume_threshold = config.get('SURGE_VOLUME_THRESHOLD', 1.3)
            if config.get('SURGE_TESTING_MODE', False):
                volume_multiplier = config.get('SURGE_TEST_VOLUME_MULTIPLIER', 0.5)
                volume_threshold *= volume_multiplier
            
            # Get detection mode
            detection_mode = config.get('SURGE_DETECTION_MODE', 'OR')
            
            # Calculate basic surge conditions
            price_change_pct_abs = abs(metrics['price_change_pct'])
            price_change_abs = abs(metrics['price_change_abs'])
            volume_multiplier = metrics['volume_multiplier']
            actual_volume = metrics.get('actual_volume', 0)
            
            # Basic threshold checks
            meets_price_threshold = (price_change_pct_abs >= threshold_pct and 
                                    price_change_abs >= min_dollar_change)
            meets_volume_threshold = (volume_multiplier >= volume_threshold and 
                                    actual_volume > 0)
            
            # Initialize trigger type
            trigger_type = "none"
            
            # Determine if surge based on mode
            if detection_mode == "STRICT":
                # Both required
                is_price_surge = meets_price_threshold
                is_volume_surge = meets_volume_threshold
                is_surge = is_price_surge and is_volume_surge
                
                if is_surge:
                    trigger_type = "price_and_volume"
                    
            elif detection_mode == "OR":
                # Either one (current behavior)
                is_price_surge = meets_price_threshold
                is_volume_surge = meets_volume_threshold
                is_surge = is_price_surge or is_volume_surge
                
                # Determine trigger type
                if is_price_surge and is_volume_surge:
                    trigger_type = "price_and_volume"
                elif is_price_surge:
                    trigger_type = "price"
                elif is_volume_surge:
                    trigger_type = "volume"
                    
            elif detection_mode == "ADAPTIVE":
                # Compensatory logic
                price_comp_mult = config.get('SURGE_PRICE_COMPENSATION_MULTIPLIER', 1.5)
                volume_comp_mult = config.get('SURGE_VOLUME_COMPENSATION_MULTIPLIER', 2.0)
                min_price_pct = config.get('SURGE_MIN_PRICE_THRESHOLD_PCT', 0.5)
                min_volume_pct = config.get('SURGE_MIN_VOLUME_THRESHOLD_PCT', 0.7)
                
                # Calculate compensation factors
                price_factor = price_change_pct_abs / threshold_pct if threshold_pct > 0 else 0
                volume_factor = volume_multiplier / volume_threshold if volume_threshold > 0 else 0
                
                # Case 1: Both meet thresholds
                case1_both = meets_price_threshold and meets_volume_threshold
                
                # Case 2: Strong price compensates for weaker volume
                strong_price = (price_change_pct_abs >= threshold_pct * price_comp_mult and
                            price_change_abs >= min_dollar_change * price_comp_mult)
                adequate_volume = (volume_multiplier >= volume_threshold * min_volume_pct and
                                actual_volume > 0)
                case2_price_driven = strong_price and adequate_volume
                
                # Case 3: Strong volume compensates for weaker price
                strong_volume = (volume_multiplier >= volume_threshold * volume_comp_mult and
                                actual_volume > 0)
                adequate_price = (price_change_pct_abs >= threshold_pct * min_price_pct and
                                price_change_abs >= min_dollar_change * min_price_pct)
                case3_volume_driven = strong_volume and adequate_price
                
                # Determine surge type
                is_surge = case1_both or case2_price_driven or case3_volume_driven
                is_price_surge = meets_price_threshold or strong_price
                is_volume_surge = meets_volume_threshold or strong_volume
                
                # Enhanced trigger type for adaptive mode
                if case1_both:
                    trigger_type = "price_and_volume"
                elif case2_price_driven:
                    trigger_type = "price_driven"
                elif case3_volume_driven:
                    trigger_type = "volume_driven"
                    
            else:
                # Default to OR logic if unknown mode
                is_price_surge = meets_price_threshold
                is_volume_surge = meets_volume_threshold
                is_surge = is_price_surge or is_volume_surge
                
                # Determine trigger type
                if is_price_surge and is_volume_surge:
                    trigger_type = "price_and_volume"
                elif is_price_surge:
                    trigger_type = "price"
                elif is_volume_surge:
                    trigger_type = "volume"
            
            # Calculate surge score
            price_score_weight = config.get('SURGE_SCORE_PRICE_WEIGHT', 50)
            volume_score_weight = config.get('SURGE_SCORE_VOLUME_WEIGHT', 50)
            
            # Price score
            price_score = 0
            if threshold_pct > 0:
                price_score = min((price_change_pct_abs / threshold_pct * price_score_weight), 
                                price_score_weight)
            
            # Volume score
            volume_score = 0
            if is_volume_surge:
                volume_score = min((volume_multiplier / volume_threshold * volume_score_weight), 
                                volume_score_weight)
            
            surge_score = price_score + volume_score
            
            # Determine strength
            if surge_score >= 80:
                surge_strength = 'strong'
            elif surge_score >= 60:
                surge_strength = 'moderate'
            else:
                surge_strength = 'weak'
            
            # Build thresholds_used dictionary
            thresholds_used = {
                'price_threshold_pct': threshold_pct,
                'min_dollar_change': min_dollar_change,
                'volume_threshold': volume_threshold,
                'direction_multiplier': dir_multiplier
            }
            
            # Add adaptive mode details if applicable
            if detection_mode == "ADAPTIVE":
                compensation_case = (
                    "balanced" if case1_both else
                    "price_compensated" if case2_price_driven else
                    "volume_compensated" if case3_volume_driven else
                    "none"
                )
                thresholds_used.update({
                    'detection_mode': 'adaptive',
                    'compensation_case': compensation_case,
                    'price_factor': round(price_factor, 2),
                    'volume_factor': round(volume_factor, 2),
                    'price_comp_multiplier': price_comp_mult,
                    'volume_comp_multiplier': volume_comp_mult,
                    'min_price_threshold_pct': min_price_pct,
                    'min_volume_threshold_pct': min_volume_pct
                })
            else:
                thresholds_used['detection_mode'] = detection_mode.lower()
            
            return {
                'is_surge': is_surge,
                'is_price_surge': is_price_surge,
                'is_volume_surge': is_volume_surge,
                'trigger_type': trigger_type,
                'surge_score': surge_score,
                'surge_strength': surge_strength,
                'price_score': price_score,
                'volume_score': volume_score,
                'thresholds_used': thresholds_used
            }
            
        except Exception as e:
            logger.error(f"Error evaluating surge conditions: {e}")
            return {
                'is_surge': False,
                'is_price_surge': False,
                'is_volume_surge': False,
                'trigger_type': 'none',
                'surge_score': 0,
                'surge_strength': 'weak',
                'price_score': 0,
                'volume_score': 0,
                'thresholds_used': {}
            }
    
    @staticmethod
    def get_price_thresholds(price: float, config: Dict[str, Any]) -> Tuple[float, float]:
        """
        Get price-based thresholds for surge detection.
        
        Args:
            price: Current price level
            config: Configuration dictionary
            
        Returns:
            Tuple of (percent_threshold, min_dollar_change)
        """
        try:
            # Global sensitivity multiplier
            global_sensitivity = config.get('SURGE_GLOBAL_SENSITIVITY', 1.0)
            
            # Testing mode adjustments
            testing_mode = config.get('SURGE_TESTING_MODE', False)
            threshold_multiplier = config.get('SURGE_TEST_THRESHOLD_MULTIPLIER', 0.2) if testing_mode else 1.0
            dollar_multiplier = config.get('SURGE_TEST_DOLLAR_MULTIPLIER', 0.1) if testing_mode else 1.0
            
            # Parse threshold config helper
            def parse_threshold(config_key: str, default: str) -> Tuple[float, float]:
                config_value = config.get(config_key, default)
                try:
                    parts = config_value.split(',')
                    if len(parts) == 2:
                        return float(parts[0]), float(parts[1])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid threshold config {config_key}: {config_value}")
                parts = default.split(',')
                return float(parts[0]), float(parts[1])
            
            # Price threshold matrix
            thresholds = [
                (0.01, parse_threshold('SURGE_THRESHOLD_ULTRA_LOW', '10.0,0.005')),
                (0.7, parse_threshold('SURGE_THRESHOLD_VERY_LOW', '9.0,0.05')),
                (1.0, parse_threshold('SURGE_THRESHOLD_LOW', '7.0,0.05')),
                (5.0, parse_threshold('SURGE_THRESHOLD_LOW_MID', '5.0,0.10')),
                (25.0, parse_threshold('SURGE_THRESHOLD_MID', '4.0,0.25')),
                (100.0, parse_threshold('SURGE_THRESHOLD_MID_HIGH', '3.0,0.75')),
                (500.0, parse_threshold('SURGE_THRESHOLD_HIGH', '2.5,1.50')),
                (1000.0, parse_threshold('SURGE_THRESHOLD_VERY_HIGH', '2.0,10.00')),
                (float('inf'), parse_threshold('SURGE_THRESHOLD_ULTRA_HIGH', '1.5,15.00'))
            ]
            
            # Find appropriate threshold based on price
            for max_price, (percent_threshold, min_dollar_change) in thresholds:
                if price < max_price:
                    return (percent_threshold * threshold_multiplier * global_sensitivity, 
                        min_dollar_change * dollar_multiplier * global_sensitivity)
            
            # Fallback to ultra-high threshold
            percent, dollar = thresholds[-1][1]
            return (percent * threshold_multiplier * global_sensitivity, 
                dollar * dollar_multiplier * global_sensitivity)
            
        except Exception as e:
            logger.error(f"Error getting price thresholds: {e}")
            # Safe defaults
            return (5.0, 0.10)


    @staticmethod
    def get_dynamic_thresholds(market_period: str, price_band: Dict[str, Any], 
                            volatility_class: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get dynamic thresholds based on market context for surge detection.
        
        Args:
            market_period: 'OPENING', 'MIDDAY', 'CLOSING', 'AFTERHOURS', 'PREMARKET', 'CLOSED'
            price_band: Dict with 'name', 'price_pct', 'dollar' from get_surge_price_band
            volatility_class: 'HIGH', 'NORMAL', 'LOW'
            config: Configuration dictionary
            
        Returns:
            Dictionary with adjusted thresholds
        """
        try:
            # Get market period thresholds
            market_key_suffix = market_period.upper()
            
            # Get market-specific configurations
            threshold_mult = config.get(f'SURGE_THRESHOLD_MULTIPLIER_{market_key_suffix}', 1.0)
            volume_thresh = config.get(f'SURGE_VOLUME_THRESHOLD_{market_key_suffix}', 1.3)
            sensitivity = config.get(f'SURGE_GLOBAL_SENSITIVITY_{market_key_suffix}', 1.0)
            min_points = config.get(f'SURGE_MIN_DATA_POINTS_{market_key_suffix}', 3)
            interval = config.get(f'SURGE_INTERVAL_SECONDS_{market_key_suffix}', 5)
            price_pct = config.get(f'SURGE_PRICE_THRESHOLD_PERCENT_{market_key_suffix}', 2.0)
            
            # Get price band thresholds
            band_price_pct = price_band.get('price_pct', 2.0)
            band_dollar_threshold = price_band.get('dollar', 0.10)
            
            # Use the minimum (most sensitive) of market period and price band thresholds
            final_price_pct = min(price_pct, band_price_pct)
            
            # Apply volatility multiplier
            volatility_mult_key = f'SURGE_VOLATILITY_MULTIPLIER_{volatility_class}'
            volatility_multiplier = config.get(volatility_mult_key, 1.0)
            
            # Apply all adjustments
            adjusted_price_pct = final_price_pct * volatility_multiplier * threshold_mult
            adjusted_dollar = band_dollar_threshold * threshold_mult
            adjusted_volume = volume_thresh
            
            # Build return dictionary
            thresholds = {
                'price_threshold_pct': adjusted_price_pct,
                'min_dollar_change': adjusted_dollar,
                'volume_threshold': adjusted_volume,
                'global_sensitivity': sensitivity,
                'min_data_points': min_points,
                'interval_seconds': interval,
                'threshold_multiplier': threshold_mult,
                'market_period': market_period,
                'price_band': price_band['name'],
                'volatility_class': volatility_class,
                'volatility_multiplier': volatility_multiplier
            }
            
            # Log the dynamic thresholds for debugging
            #logger.debug(f"DIAG-SURGE-ENGINE-DYNAMIC: period={market_period}, "
            #            f"band={price_band['name']}, volatility={volatility_class} -> "
            #            f"price_thresh={adjusted_price_pct:.2f}%, "
            #            f"dollar_thresh=${adjusted_dollar:.3f}, "
            #            f"vol_thresh={adjusted_volume:.1f}x, "
            #            f"sensitivity={sensitivity:.2f}")
            
            return thresholds
            
        except Exception as e:
            logger.error(f"Error getting dynamic surge thresholds: {e}")
            # Return safe defaults on error
            return {
                'price_threshold_pct': 2.0,
                'min_dollar_change': 0.10,
                'volume_threshold': 1.3,
                'global_sensitivity': 1.0,
                'min_data_points': 3,
                'interval_seconds': 5,
                'threshold_multiplier': 1.0,
                'market_period': 'UNKNOWN',
                'price_band': 'UNKNOWN',
                'volatility_class': 'NORMAL',
                'volatility_multiplier': 1.0
            }


    @staticmethod
    def evaluate_surge_conditions_adaptive(
        metrics: Dict[str, Any],
        price: float,
        config: Dict[str, Any],
        dynamic_thresholds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced evaluate_surge_conditions with adaptive thresholds.
        
        Args:
            metrics: Output from calculate_surge_metrics
            price: Current price (for threshold calculation)
            config: Configuration dictionary
            dynamic_thresholds: Output from get_dynamic_thresholds
            
        Returns:
            Dictionary with surge evaluation results
        """
        try:
            # Use dynamic thresholds instead of calculating from config
            threshold_pct = dynamic_thresholds['price_threshold_pct']
            min_dollar_change = dynamic_thresholds['min_dollar_change']
            volume_threshold = dynamic_thresholds['volume_threshold']
            
            # Get direction-specific multipliers
            direction = metrics['direction']
            dir_multiplier = 1.0
            if direction == "up":
                dir_multiplier = config.get('SURGE_UP_THRESHOLD_MULTIPLIER', 1.0)
            elif direction == "down":
                dir_multiplier = config.get('SURGE_DOWN_THRESHOLD_MULTIPLIER', 1.0)
            
            # Apply direction multiplier to thresholds
            threshold_pct *= dir_multiplier
            
            # Get detection mode - ENHANCED LOGIC
            market_period = dynamic_thresholds.get('market_period', 'MIDDAY')
            
            # CHANGE: Check for period-specific override first
            period_mode_key = f'SURGE_DETECTION_MODE_{market_period}'
            detection_mode = config.get(period_mode_key, None)
            
            # If no period-specific mode, use adaptive defaults
            if detection_mode is None:
                # Original adaptive logic - but now can be overridden
                if market_period == 'MIDDAY':
                    detection_mode = config.get('SURGE_DETECTION_MODE_DEFAULT', 'STRICT')  # CHANGED: Respect default
                elif market_period in ['AFTERHOURS', 'PREMARKET']:
                    detection_mode = 'ADAPTIVE'  # Compensatory for sparse data
                elif market_period in ['OPENING', 'CLOSING']:
                    detection_mode = 'STRICT'  # Need both price AND volume
                else:
                    detection_mode = config.get('SURGE_DETECTION_MODE_DEFAULT', 'STRICT')
            
            # Calculate basic surge conditions
            price_change_pct_abs = abs(metrics['price_change_pct'])
            price_change_abs = abs(metrics['price_change_abs'])
            volume_multiplier = metrics['volume_multiplier']
            actual_volume = metrics.get('actual_volume', 0)
            
            # Basic threshold checks
            meets_price_threshold = (price_change_pct_abs >= threshold_pct and 
                                    price_change_abs >= min_dollar_change)
            meets_volume_threshold = (volume_multiplier >= volume_threshold and 
                                    actual_volume > 0)
            
            # Initialize trigger type
            trigger_type = "none"
            
            # Determine if surge based on mode
            if detection_mode == "STRICT":
                # Both required
                is_price_surge = meets_price_threshold
                is_volume_surge = meets_volume_threshold
                is_surge = is_price_surge and is_volume_surge
                
                if is_surge:
                    trigger_type = "price_and_volume"
                    
            elif detection_mode == "OR":
                # Either one (most sensitive for midday)
                is_price_surge = meets_price_threshold
                is_volume_surge = meets_volume_threshold
                is_surge = is_price_surge or is_volume_surge
                
                # Determine trigger type
                if is_price_surge and is_volume_surge:
                    trigger_type = "price_and_volume"
                elif is_price_surge:
                    trigger_type = "price"
                elif is_volume_surge:
                    trigger_type = "volume"
                    
            elif detection_mode == "ADAPTIVE":
                # Compensatory logic for sparse data periods
                price_comp_mult = config.get('SURGE_PRICE_COMPENSATION_MULTIPLIER', 1.5)
                volume_comp_mult = config.get('SURGE_VOLUME_COMPENSATION_MULTIPLIER', 2.0)
                min_price_pct = config.get('SURGE_MIN_PRICE_THRESHOLD_PCT', 0.5)
                min_volume_pct = config.get('SURGE_MIN_VOLUME_THRESHOLD_PCT', 0.7)
                
                # Calculate compensation factors
                price_factor = price_change_pct_abs / threshold_pct if threshold_pct > 0 else 0
                volume_factor = volume_multiplier / volume_threshold if volume_threshold > 0 else 0
                
                # Case 1: Both meet thresholds
                case1_both = meets_price_threshold and meets_volume_threshold
                
                # Case 2: Strong price compensates for weaker volume
                strong_price = (price_change_pct_abs >= threshold_pct * price_comp_mult and
                            price_change_abs >= min_dollar_change * price_comp_mult)
                adequate_volume = (volume_multiplier >= volume_threshold * min_volume_pct and
                                actual_volume > 0)
                case2_price_driven = strong_price and adequate_volume
                
                # Case 3: Strong volume compensates for weaker price
                strong_volume = (volume_multiplier >= volume_threshold * volume_comp_mult and
                            actual_volume > 0)
                adequate_price = (price_change_pct_abs >= threshold_pct * min_price_pct and
                                price_change_abs >= min_dollar_change * min_price_pct)
                case3_volume_driven = strong_volume and adequate_price
                
                # Determine surge type
                is_surge = case1_both or case2_price_driven or case3_volume_driven
                is_price_surge = meets_price_threshold or strong_price
                is_volume_surge = meets_volume_threshold or strong_volume
                
                # Enhanced trigger type for adaptive mode
                if case1_both:
                    trigger_type = "price_and_volume"
                elif case2_price_driven:
                    trigger_type = "price_driven"
                elif case3_volume_driven:
                    trigger_type = "volume_driven"
            else:
                # Default to OR logic if unknown mode
                is_price_surge = meets_price_threshold
                is_volume_surge = meets_volume_threshold
                is_surge = is_price_surge or is_volume_surge
                
                if is_price_surge and is_volume_surge:
                    trigger_type = "price_and_volume"
                elif is_price_surge:
                    trigger_type = "price"
                elif is_volume_surge:
                    trigger_type = "volume"
            
            # Calculate surge score
            price_score_weight = config.get('SURGE_SCORE_PRICE_WEIGHT', 50)
            volume_score_weight = config.get('SURGE_SCORE_VOLUME_WEIGHT', 50)
            
            # Price score
            price_score = 0
            if threshold_pct > 0:
                price_score = min((price_change_pct_abs / threshold_pct * price_score_weight), 
                                price_score_weight)
            
            # Volume score
            volume_score = 0
            if is_volume_surge:
                volume_score = min((volume_multiplier / volume_threshold * volume_score_weight), 
                                volume_score_weight)
            
            surge_score = price_score + volume_score
            
            # Determine strength
            if surge_score >= 80:
                surge_strength = 'strong'
            elif surge_score >= 60:
                surge_strength = 'moderate'
            else:
                surge_strength = 'weak'
            
            # Build thresholds_used dictionary with all context
            thresholds_used = {
                'price_threshold_pct': threshold_pct,
                'min_dollar_change': min_dollar_change,
                'volume_threshold': volume_threshold,
                'direction_multiplier': dir_multiplier,
                'detection_mode': detection_mode,
                'market_period': market_period,
                'price_band': dynamic_thresholds.get('price_band', 'UNKNOWN'),
                'volatility_class': dynamic_thresholds.get('volatility_class', 'NORMAL'),
                'global_sensitivity': dynamic_thresholds.get('global_sensitivity', 1.0)
            }
            
            # Log decision for debugging
            #logger.debug(f"DIAG-SURGE-ENGINE-DECISION: "
            #            f"price_change={price_change_pct_abs:.2f}% vs {threshold_pct:.2f}%, "
            #            f"vol_mult={volume_multiplier:.1f}x vs {volume_threshold:.1f}x, "
            #            f"mode={detection_mode}, surge={is_surge}, trigger={trigger_type}")
            
            return {
                'is_surge': is_surge,
                'is_price_surge': is_price_surge,
                'is_volume_surge': is_volume_surge,
                'trigger_type': trigger_type,
                'surge_score': surge_score,
                'surge_strength': surge_strength,
                'price_score': price_score,
                'volume_score': volume_score,
                'thresholds_used': thresholds_used
            }
            
        except Exception as e:
            logger.error(f"Error in adaptive surge evaluation: {e}")
            # Fallback to standard evaluation
            return SurgeDetectionEngine.evaluate_surge_conditions(metrics, price, config)



#-------------------------------------------------------------
# Trend Detection Engine
#-------------------------------------------------------------
class TrendDetectionEngine:
    """
    Pure trend detection calculation engine.
    No state management, no event creation, just mathematics.
    """
    @staticmethod
    def _calculate_price_component(data_points: List[Dict], config: Dict[str, Any]) -> float:
        """Calculate price trend component (-1 to 1)."""
        if len(data_points) < 2:
            return 0
        
        prices = [point['price'] for point in data_points]
        price_changes = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        
        # Apply recency weighting - GET FROM CONFIG, NOT self
        recency_decay = config.get('TREND_RECENCY_DECAY', 0.9)
        weights = [recency_decay ** (len(price_changes) - i - 1) for i in range(len(price_changes))]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Calculate weighted price change
        weighted_changes = [price_changes[i] * weights[i] for i in range(len(price_changes))]
        weighted_sum = sum(weighted_changes)
        
        # Normalize to -1 to +1 range
        avg_price = sum(prices) / len(prices)
        if avg_price > 0:
            normalized_change = weighted_sum / (avg_price * 0.01)  # 1% change = score of 1
            return max(-1, min(1, normalized_change))
        return 0
    
    @staticmethod
    def _calculate_vwap_component(data_points: List[Dict], config: Dict[str, Any]) -> float:
        """Calculate VWAP relationship component (-1 to 1)."""
        vwap_points = [p for p in data_points if p.get('vwap') is not None and p['vwap'] > 0]
        
        if len(vwap_points) < 2:
            return 0
        
        # Calculate price relative to VWAP
        vwap_relations = [(p['price'] - p['vwap']) / p['vwap'] for p in vwap_points]
        
        # Apply recency weighting - GET FROM CONFIG, NOT self
        recency_decay = config.get('TREND_RECENCY_DECAY', 0.9)
        weights = [recency_decay ** (len(vwap_relations) - i - 1) for i in range(len(vwap_relations))]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Calculate weighted VWAP relation
        weighted_relations = [vwap_relations[i] * weights[i] for i in range(len(vwap_relations))]
        weighted_sum = sum(weighted_relations)
        
        # Calculate change in VWAP relation
        vwap_changes = [vwap_relations[i+1] - vwap_relations[i] for i in range(len(vwap_relations)-1)]
        if vwap_changes:
            weighted_changes = [vwap_changes[i] * weights[i] for i in range(len(vwap_changes))]
            change_factor = sum(weighted_changes) * 10
        else:
            change_factor = 0
        
        # Combine position and change
        return max(-1, min(1, weighted_sum * 5 + change_factor))
    
    @staticmethod
    def _calculate_volume_component(data_points: List[Dict], config: Dict[str, Any]) -> float:
        """Calculate volume trend component (-1 to 1)."""
        volume_points = [p for p in data_points if p.get('volume') is not None and p['volume'] > 0]
        
        if len(volume_points) < 3:
            return 0
        
        volumes = [p['volume'] for p in volume_points]
        prices = [p['price'] for p in volume_points]
        
        # Calculate price changes
        price_changes = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        
        # Calculate volume-weighted price change
        volume_weighted_changes = []
        avg_volume = sum(volumes) / len(volumes)
        
        for i in range(len(price_changes)):
            if avg_volume > 0:
                vol_factor = volumes[i] / avg_volume
            else:
                vol_factor = 1
            
            # Price direction determines sign
            direction = 1 if price_changes[i] > 0 else -1 if price_changes[i] < 0 else 0
            volume_weighted_changes.append(direction * vol_factor)
        
        # Apply recency weighting - GET FROM CONFIG, NOT self
        recency_decay = config.get('TREND_RECENCY_DECAY', 0.9)
        weights = [recency_decay ** (len(volume_weighted_changes) - i - 1) 
                  for i in range(len(volume_weighted_changes))]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Calculate weighted volume factor
        weighted_volume_factors = [volume_weighted_changes[i] * weights[i] 
                                  for i in range(len(volume_weighted_changes))]
        weighted_sum = sum(weighted_volume_factors)
        
        # Normalize to -1 to +1 range
        return max(-1, min(1, weighted_sum / 3))
    """
    Pure trend detection calculation engine.
    No state management, no event creation, just mathematics.
    """
    
    @staticmethod
    def calculate_window_trend(
        price_history: List[Dict[str, Any]],
        window_seconds: int,
        current_time: datetime,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate trend for a specific time window.
        
        Args:
            price_history: List of price/volume/timestamp dictionaries
            window_seconds: Window size in seconds
            current_time: Current timestamp
            config: Configuration dictionary
            
        Returns:
            Dictionary containing:
            - direction: 'up', 'down', or 'neutral'
            - score: Trend score (-1 to 1)
            - strength: 'weak', 'moderate', 'strong', or 'neutral'
            - price_component: Price trend component
            - vwap_component: VWAP trend component
            - volume_component: Volume trend component
            - data_points: Number of points analyzed
        """
        try:
            # Handle datetime/timestamp conversion
            if isinstance(current_time, datetime):
                current_timestamp = current_time.timestamp()
            else:
                current_timestamp = float(current_time)
            
            window_start = current_timestamp - window_seconds
            
            # Extract data points within window
            window_data = []
            for point in price_history:
                point_time = point['timestamp']
                # Handle both datetime and timestamp formats
                if isinstance(point_time, datetime):
                    point_timestamp = point_time.timestamp()
                else:
                    point_timestamp = float(point_time)
                
                if point_timestamp >= window_start:
                    window_data.append(point)
            
            # Use configurable minimum
            min_required = config.get('TREND_MIN_DATA_POINTS_PER_WINDOW', 10)
        
            # Need minimum data points
            if len(window_data) < min_required:
                return {
                    'direction': 'neutral',
                    'score': 0,
                    'strength': 'neutral',
                    'price_component': 0,
                    'vwap_component': 0,
                    'volume_component': 0,
                    'data_points': len(window_data),
                    'insufficient_data': True  # Flag for debugging
                }
            
            # Sort by timestamp
            window_data.sort(key=lambda x: x['timestamp'])
            
            # Get component weights from config
            price_weight = config.get('TREND_PRICE_WEIGHT', 0.5)
            vwap_weight = config.get('TREND_VWAP_WEIGHT', 0.3)
            volume_weight = config.get('TREND_VOLUME_WEIGHT', 0.2)
            
            # Calculate components
            price_component = TrendDetectionEngine._calculate_price_component(
                window_data, config
            )
            vwap_component = TrendDetectionEngine._calculate_vwap_component(
                window_data, config
            )
            volume_component = TrendDetectionEngine._calculate_volume_component(
                window_data, config
            )
            
            # Calculate weighted score
            trend_score = (
                price_component * price_weight +
                vwap_component * vwap_weight +
                volume_component * volume_weight
            )
            
            # Determine direction and strength
            direction_threshold = config.get('TREND_DIRECTION_THRESHOLD', 0.3)
            strength_threshold = config.get('TREND_STRENGTH_THRESHOLD', 0.6)
            
            if trend_score > direction_threshold:
                direction = 'up'
                if trend_score > strength_threshold:
                    strength = 'strong'
                elif trend_score > direction_threshold * 2:
                    strength = 'moderate'
                else:
                    strength = 'weak'
            elif trend_score < -direction_threshold:
                direction = 'down'
                if trend_score < -strength_threshold:
                    strength = 'strong'
                elif trend_score < -direction_threshold * 2:
                    strength = 'moderate'
                else:
                    strength = 'weak'
            else:
                direction = 'neutral'
                strength = 'neutral'
            
            return {
                'direction': direction,
                'score': trend_score,
                'strength': strength,
                'price_component': price_component,
                'vwap_component': vwap_component,
                'volume_component': volume_component,
                'data_points': len(window_data)
            }
            
        except Exception as e:
            logger.error(f"Error calculating window trend: {e}")
            return {
                'direction': 'neutral',
                'score': 0,
                'strength': 'neutral',
                'price_component': 0,
                'vwap_component': 0,
                'volume_component': 0,
                'data_points': 0
            }
    
    @staticmethod
    def calculate_multi_window_trends(
        price_history: List[Dict[str, Any]],
        current_time: datetime,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate trends across multiple time windows.
        
        Args:
            price_history: List of price/volume/timestamp dictionaries
            current_time: Current timestamp
            config: Configuration dictionary
            
        Returns:
            Dictionary containing:
            - short_trend: Short window trend data
            - medium_trend: Medium window trend data
            - long_trend: Long window trend data
            - combined_score: Overall trend score
            - combined_direction: Overall direction
            - combined_strength: Overall strength
        """
        try:
            # Get window sizes from config
            short_window = config.get('TREND_SHORT_WINDOW_SECONDS', 180)
            medium_window = config.get('TREND_MEDIUM_WINDOW_SECONDS', 360)
            long_window = config.get('TREND_LONG_WINDOW_SECONDS', 600)
            
            # Calculate trends for each window
            short_trend = TrendDetectionEngine.calculate_window_trend(
                price_history, short_window, current_time, config
            )
            medium_trend = TrendDetectionEngine.calculate_window_trend(
                price_history, medium_window, current_time, config
            )
            long_trend = TrendDetectionEngine.calculate_window_trend(
                price_history, long_window, current_time, config
            )
            
            # Combine scores with weights (medium window has highest weight)
            combined_score = (
                short_trend['score'] * 0.3 +
                medium_trend['score'] * 0.4 +
                long_trend['score'] * 0.3
            )
            
            # Determine combined direction and strength
            direction_threshold = config.get('TREND_DIRECTION_THRESHOLD', 0.3)
            strength_threshold = config.get('TREND_STRENGTH_THRESHOLD', 0.6)
            
            if combined_score > direction_threshold:
                combined_direction = 'up'
                if combined_score > strength_threshold:
                    combined_strength = 'strong'
                elif combined_score > direction_threshold * 2:
                    combined_strength = 'moderate'
                else:
                    combined_strength = 'weak'
            elif combined_score < -direction_threshold:
                combined_direction = 'down'
                if combined_score < -strength_threshold:
                    combined_strength = 'strong'
                elif combined_score < -direction_threshold * 2:
                    combined_strength = 'moderate'
                else:
                    combined_strength = 'weak'
            else:
                combined_direction = 'neutral'
                combined_strength = 'neutral'
            
            return {
                'short_trend': short_trend,
                'medium_trend': medium_trend,
                'long_trend': long_trend,
                'combined_score': combined_score,
                'combined_direction': combined_direction,
                'combined_strength': combined_strength
            }
            
        except Exception as e:
            logger.error(f"Error calculating multi-window trends: {e}")
            # Return neutral trends
            neutral_trend = {
                'direction': 'neutral',
                'score': 0,
                'strength': 'neutral',
                'price_component': 0,
                'vwap_component': 0,
                'volume_component': 0,
                'data_points': 0
            }
            return {
                'short_trend': neutral_trend,
                'medium_trend': neutral_trend,
                'long_trend': neutral_trend,
                'combined_score': 0,
                'combined_direction': 'neutral',
                'combined_strength': 'neutral'
            }
    
    @staticmethod
    def evaluate_trend_conditions(
        trend_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate if trend conditions are met.
        
        Args:
            trend_data: Output from calculate_multi_window_trends
            config: Configuration dictionary
            
        Returns:
            Dictionary containing:
            - is_trend: Boolean indicating if trend detected
            - trend_direction: Direction symbol ('↑', '↓', '→')
            - trend_strength: Strength classification
            - should_emit_event: Boolean for event emission logic
        """
        try:
            combined_direction = trend_data['combined_direction']
            combined_strength = trend_data['combined_strength']
            combined_score = trend_data['combined_score']
            
            # Get global sensitivity
            global_sensitivity = config.get('TREND_GLOBAL_SENSITIVITY', 1.0)
            
            # Apply sensitivity to thresholds
            direction_threshold = config.get('TREND_DIRECTION_THRESHOLD', 0.3) * global_sensitivity
            strength_threshold = config.get('TREND_STRENGTH_THRESHOLD', 0.6) * global_sensitivity
            
            # Re-evaluate with adjusted thresholds
            if abs(combined_score) > strength_threshold:
                combined_strength = 'strong'
            elif abs(combined_score) > direction_threshold * 2:
                combined_strength = 'moderate'
            elif abs(combined_score) > direction_threshold:
                combined_strength = 'weak'
            else:
                combined_strength = 'neutral'
                
            # Re-determine direction with adjusted threshold
            if combined_score > direction_threshold:
                combined_direction = 'up'
            elif combined_score < -direction_threshold:
                combined_direction = 'down'
            else:
                combined_direction = 'neutral'
            
            # Map direction to symbol
            direction_map = {
                'up': '↑',
                'down': '↓',
                'neutral': '→'
            }
            trend_direction = direction_map.get(combined_direction, '→')
            
            # Determine if this is a significant trend
            is_trend = combined_direction != 'neutral'
            
            # For event emission, we might want stronger criteria
            should_emit_event = is_trend and combined_strength != 'weak'
            
            return {
                'is_trend': is_trend,
                'trend_direction': trend_direction,
                'trend_strength': combined_strength,
                'should_emit_event': should_emit_event,
                'raw_direction': combined_direction,
                'score': combined_score
            }
            
        except Exception as e:
            logger.error(f"Error evaluating trend conditions: {e}")
            return {
                'is_trend': False,
                'trend_direction': '→',
                'trend_strength': 'neutral',
                'should_emit_event': False,
                'raw_direction': 'neutral',
                'score': 0
            }
    
    @staticmethod
    def get_dynamic_thresholds(market_period: str, price_bucket: str, 
                              volatility_category: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get dynamic thresholds based on market context.
        
        Args:
            market_period: 'OPENING', 'MIDDAY', 'CLOSING', 'AFTERHOURS', 'PREMARKET', 'CLOSED'
            price_bucket: 'PENNY', 'LOW', 'MID', 'HIGH', 'ULTRA'
            volatility_category: 'HIGH', 'NORMAL', 'LOW'
            config: Configuration dictionary
            
        Returns:
            Dictionary with adjusted thresholds
        """
        try:
            # Start with base thresholds
            thresholds = {
                'direction_threshold': config.get('TREND_DIRECTION_THRESHOLD', 0.3),
                'strength_threshold': config.get('TREND_STRENGTH_THRESHOLD', 0.6),
                'global_sensitivity': config.get('TREND_GLOBAL_SENSITIVITY', 1.0),
                'min_emission_interval': config.get('TREND_MIN_EMISSION_INTERVAL', 60),
                'retracement_threshold': config.get('TREND_RETRACEMENT_THRESHOLD', 0.4),
                'min_data_points_per_window': config.get('TREND_MIN_DATA_POINTS_PER_WINDOW', 10),
                'warmup_period_seconds': config.get('TREND_WARMUP_PERIOD_SECONDS', 180)
            }
            
            # Apply market period adjustments
            period_suffix = f"_{market_period}"
            thresholds['direction_threshold'] = config.get(f'TREND_DIRECTION_THRESHOLD{period_suffix}', 
                                                          thresholds['direction_threshold'])
            thresholds['strength_threshold'] = config.get(f'TREND_STRENGTH_THRESHOLD{period_suffix}', 
                                                         thresholds['strength_threshold'])
            thresholds['global_sensitivity'] = config.get(f'TREND_GLOBAL_SENSITIVITY{period_suffix}', 
                                                         thresholds['global_sensitivity'])
            thresholds['min_emission_interval'] = config.get(f'TREND_MIN_EMISSION_INTERVAL{period_suffix}', 
                                                            thresholds['min_emission_interval'])
            thresholds['retracement_threshold'] = config.get(f'TREND_RETRACEMENT_THRESHOLD{period_suffix}', 
                                                            thresholds['retracement_threshold'])
            thresholds['min_data_points_per_window'] = config.get(f'TREND_MIN_DATA_POINTS_PER_WINDOW{period_suffix}', 
                                                                 thresholds['min_data_points_per_window'])
            thresholds['warmup_period_seconds'] = config.get(f'TREND_WARMUP_PERIOD_SECONDS{period_suffix}', 
                                                            thresholds['warmup_period_seconds'])
            
            # Apply price bucket adjustments (multiplicative)
            price_suffix = f"_{price_bucket}"
            price_dir_threshold = config.get(f'TREND_DIRECTION_THRESHOLD{price_suffix}', None)
            price_str_threshold = config.get(f'TREND_STRENGTH_THRESHOLD{price_suffix}', None)
            
            if price_dir_threshold is not None:
                # Use the minimum (most sensitive) of market period and price bucket thresholds
                thresholds['direction_threshold'] = min(thresholds['direction_threshold'], price_dir_threshold)
            
            if price_str_threshold is not None:
                # Use the minimum (most sensitive) of market period and price bucket thresholds
                thresholds['strength_threshold'] = min(thresholds['strength_threshold'], price_str_threshold)
            
            # Apply volatility adjustments
            volatility_multiplier = config.get(f'TREND_VOLATILITY_MULTIPLIER_{volatility_category}', 1.0)
            thresholds['direction_threshold'] *= volatility_multiplier
            thresholds['strength_threshold'] *= volatility_multiplier
            
            # Log the dynamic thresholds for debugging
            #logger.debug(f"DIAG-TREND-DYNAMIC: period={market_period}, bucket={price_bucket}, "
            #            f"volatility={volatility_category} -> "
            #            f"dir_thresh={thresholds['direction_threshold']:.4f}, "
            #            f"str_thresh={thresholds['strength_threshold']:.4f}, "
            #            f"sensitivity={thresholds['global_sensitivity']:.2f}")
            
            return thresholds
            
        except Exception as e:
            logger.error(f"Error getting dynamic thresholds: {e}")
            # Return base thresholds on error
            return {
                'direction_threshold': config.get('TREND_DIRECTION_THRESHOLD', 0.3),
                'strength_threshold': config.get('TREND_STRENGTH_THRESHOLD', 0.6),
                'global_sensitivity': config.get('TREND_GLOBAL_SENSITIVITY', 1.0),
                'min_emission_interval': config.get('TREND_MIN_EMISSION_INTERVAL', 60),
                'retracement_threshold': config.get('TREND_RETRACEMENT_THRESHOLD', 0.4),
                'min_data_points_per_window': config.get('TREND_MIN_DATA_POINTS_PER_WINDOW', 10),
                'warmup_period_seconds': config.get('TREND_WARMUP_PERIOD_SECONDS', 180)
            }

    @staticmethod
    def evaluate_trend_conditions_adaptive(
        trend_data: Dict[str, Any],
        config: Dict[str, Any],
        dynamic_thresholds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced evaluate_trend_conditions with adaptive thresholds.
        
        Args:
            trend_data: Output from calculate_multi_window_trends
            config: Configuration dictionary
            dynamic_thresholds: Output from get_dynamic_thresholds
            
        Returns:
            Dictionary with trend evaluation results
        """
        try:
            combined_direction = trend_data['combined_direction']
            combined_strength = trend_data['combined_strength']
            combined_score = trend_data['combined_score']
            
            # Use dynamic thresholds instead of config values
            direction_threshold = dynamic_thresholds['direction_threshold']
            strength_threshold = dynamic_thresholds['strength_threshold']
            global_sensitivity = dynamic_thresholds['global_sensitivity']
            
            # Apply global sensitivity
            adjusted_direction_threshold = direction_threshold * global_sensitivity
            adjusted_strength_threshold = strength_threshold * global_sensitivity
            
            # Re-evaluate with adjusted thresholds
            abs_score = abs(combined_score)
            
            # Determine strength with dynamic thresholds
            if abs_score > adjusted_strength_threshold:
                combined_strength = 'strong'
            elif abs_score > adjusted_direction_threshold * 2:
                combined_strength = 'moderate'
            elif abs_score > adjusted_direction_threshold:
                combined_strength = 'weak'
            else:
                combined_strength = 'neutral'
            
            # Re-determine direction with adjusted threshold
            if combined_score > adjusted_direction_threshold:
                combined_direction = 'up'
            elif combined_score < -adjusted_direction_threshold:
                combined_direction = 'down'
            else:
                combined_direction = 'neutral'
            
            # Map direction to symbol
            direction_map = {
                'up': '↑',
                'down': '↓',
                'neutral': '→'
            }
            trend_direction = direction_map.get(combined_direction, '→')
            
            # Determine if this is a significant trend
            is_trend = combined_direction != 'neutral'
            
            # For event emission, use adaptive criteria
            # In midday/afterhours, even weak trends are significant
            # In opening/closing, only moderate+ trends matter
            market_period = dynamic_thresholds.get('market_period', 'MIDDAY')
            if market_period in ['MIDDAY', 'AFTERHOURS', 'PREMARKET']:
                # More sensitive periods - emit even weak trends
                should_emit_event = is_trend
            else:
                # Less sensitive periods - require stronger trends
                should_emit_event = is_trend and combined_strength != 'weak'
            
            #logger.debug(f"DIAG-TREND-EVAL-ADAPTIVE: score={combined_score:.4f}, "
            #            f"adj_dir_thresh={adjusted_direction_threshold:.4f}, "
            #            f"adj_str_thresh={adjusted_strength_threshold:.4f}, "
            #            f"direction={combined_direction}, strength={combined_strength}, "
            #            f"emit={should_emit_event}")
            
            return {
                'is_trend': is_trend,
                'trend_direction': trend_direction,
                'trend_strength': combined_strength,
                'should_emit_event': should_emit_event,
                'raw_direction': combined_direction,
                'score': combined_score,
                'thresholds_used': {
                    'direction': adjusted_direction_threshold,
                    'strength': adjusted_strength_threshold,
                    'sensitivity': global_sensitivity
                }
            }
            
        except Exception as e:
            logger.error(f"Error in adaptive trend evaluation: {e}")
            # Fallback to standard evaluation
            return TrendDetectionEngine.evaluate_trend_conditions(trend_data, config)
        
    @staticmethod
    def get_retracement_threshold(price: float, config: Dict[str, Any]) -> float:
        """
        Get price-based retracement threshold.
        
        Args:
            price: Current price level
            config: Configuration dictionary
            
        Returns:
            Retracement threshold (0.0 to 1.0)
        """
        base_threshold = config.get('TREND_RETRACEMENT_THRESHOLD', 0.4)
        
        # Skip if dynamic retracement is disabled
        if not config.get('TREND_DYNAMIC_RETRACEMENT', True):
            return base_threshold
        
        # Price-based adjustments
        if price < 1.0:
            return base_threshold * 1.25  # 50%
        elif price < 5.0:
            return base_threshold * 1.125  # 45%
        elif price < 25.0:
            return base_threshold  # 40%
        elif price < 100.0:
            return base_threshold * 0.875  # 35%
        else:
            return base_threshold * 0.75  # 30%


    @staticmethod
    def check_retracement(
        previous_score: float,
        current_score: float,
        current_price: float,  # Add this parameter
        config: Dict[str, Any]
    ) -> bool:
        """
        Check if trend has been invalidated by retracement.
        
        Args:
            previous_score: Previous trend score
            current_score: Current trend score
            current_price: Current stock price for dynamic threshold
            config: Configuration dictionary
            
        Returns:
            Boolean indicating if retracement detected
        """
        try:
            direction_threshold = config.get('TREND_DIRECTION_THRESHOLD', 0.3)
            global_sensitivity = config.get('TREND_GLOBAL_SENSITIVITY', 1.0)
            adjusted_threshold = direction_threshold * global_sensitivity
            
            # Get dynamic retracement threshold
            retracement_threshold = TrendDetectionEngine.get_retracement_threshold(current_price, config)
            
            # No retracement if previous trend was weak
            if abs(previous_score) < adjusted_threshold:
                return False
            
            # No retracement if signs changed (that's a reversal)
            if previous_score * current_score < 0:
                return False
            
            # Check for significant retracement
            if previous_score != 0:
                retracement_pct = abs((current_score - previous_score) / previous_score)
                return retracement_pct >= retracement_threshold
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking retracement: {e}")
            return False
    
    @staticmethod
    def _calculate_price_component(data_points: List[Dict], config: Dict[str, Any]) -> float:
        """Calculate price trend component (-1 to 1)."""
        if len(data_points) < 2:
            return 0
        
        prices = [point['price'] for point in data_points]
        price_changes = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        
        # Apply recency weighting
        recency_decay = config.get('TREND_RECENCY_DECAY', 0.9)
        weights = [recency_decay ** (len(price_changes) - i - 1) for i in range(len(price_changes))]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Calculate weighted price change
        weighted_changes = [price_changes[i] * weights[i] for i in range(len(price_changes))]
        weighted_sum = sum(weighted_changes)
        
        # Normalize to -1 to +1 range
        avg_price = sum(prices) / len(prices)
        if avg_price > 0:
            normalized_change = weighted_sum / (avg_price * 0.01)  # 1% change = score of 1
            return max(-1, min(1, normalized_change))
        return 0
    
    @staticmethod
    def _calculate_vwap_component(data_points: List[Dict], config: Dict[str, Any]) -> float:
        """Calculate VWAP relationship component (-1 to 1)."""
        vwap_points = [p for p in data_points if p.get('vwap') is not None and p['vwap'] > 0]
        
        if len(vwap_points) < 2:
            return 0
        
        # Calculate price relative to VWAP
        vwap_relations = [(p['price'] - p['vwap']) / p['vwap'] for p in vwap_points]
        
        # Apply recency weighting
        recency_decay = config.get('TREND_RECENCY_DECAY', 0.9)
        weights = [recency_decay ** (len(vwap_relations) - i - 1) for i in range(len(vwap_relations))]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Calculate weighted VWAP relation
        weighted_relations = [vwap_relations[i] * weights[i] for i in range(len(vwap_relations))]
        weighted_sum = sum(weighted_relations)
        
        # Calculate change in VWAP relation
        vwap_changes = [vwap_relations[i+1] - vwap_relations[i] for i in range(len(vwap_relations)-1)]
        if vwap_changes:
            weighted_changes = [vwap_changes[i] * weights[i] for i in range(len(vwap_changes))]
            change_factor = sum(weighted_changes) * 10
        else:
            change_factor = 0
        
        # Combine position and change
        return max(-1, min(1, weighted_sum * 5 + change_factor))
    
    @staticmethod
    def _calculate_volume_component(data_points: List[Dict], config: Dict[str, Any]) -> float:
        """Calculate volume trend component (-1 to 1)."""
        volume_points = [p for p in data_points if p.get('volume') is not None and p['volume'] > 0]
        
        if len(volume_points) < 3:
            return 0
        
        volumes = [p['volume'] for p in volume_points]
        prices = [p['price'] for p in volume_points]
        
        # Calculate price changes
        price_changes = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        
        # Calculate volume-weighted price change
        volume_weighted_changes = []
        avg_volume = sum(volumes) / len(volumes)
        
        for i in range(len(price_changes)):
            if avg_volume > 0:
                vol_factor = volumes[i] / avg_volume
            else:
                vol_factor = 1
            
            # Price direction determines sign
            direction = 1 if price_changes[i] > 0 else -1 if price_changes[i] < 0 else 0
            volume_weighted_changes.append(direction * vol_factor)
        
        # Apply recency weighting
        recency_decay = config.get('TREND_RECENCY_DECAY', 0.9)
        weights = [recency_decay ** (len(volume_weighted_changes) - i - 1) 
                  for i in range(len(volume_weighted_changes))]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Calculate weighted volume factor
        weighted_volume_factors = [volume_weighted_changes[i] * weights[i] 
                                  for i in range(len(volume_weighted_changes))]
        weighted_sum = sum(weighted_volume_factors)
        
        # Normalize to -1 to +1 range
        return max(-1, min(1, weighted_sum / 3))

# Utility functions for data extraction and normalization
def extract_price_history_from_state(stock_data: Any) -> List[Dict[str, Any]]:
    """Extract price history from various data structures."""
    if hasattr(stock_data, 'price_history'):
        return stock_data.price_history
    elif isinstance(stock_data, dict) and 'price_history' in stock_data:
        return stock_data['price_history']
    else:
        return []


def extract_surge_buffer_from_state(stock_data: Any) -> deque:
    """Extract surge buffer from various data structures."""
    if hasattr(stock_data, 'surge_data') and stock_data.surge_data:
        return stock_data.surge_data.get('buffer', deque())
    elif isinstance(stock_data, dict) and 'surge_data' in stock_data:
        return stock_data['surge_data'].get('buffer', deque())
    else:
        return deque()