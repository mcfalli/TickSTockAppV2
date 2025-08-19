"""
Data Consistency Validator

Validates mathematical consistency between different frequency data streams,
ensuring per-minute aggregates align with underlying per-second tick data.
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from src.core.domain.market.tick import TickData
from src.infrastructure.data_sources.synthetic.types import DataFrequency
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'data_consistency_validator')


@dataclass
class ValidationResult:
    """Result of data consistency validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, float]
    validation_time: float


@dataclass
class TickWindow:
    """Aggregated tick data for a time window."""
    ticks: List[TickData]
    start_time: float
    end_time: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    total_volume: int
    vwap: float


class DataConsistencyValidator:
    """Validates consistency across multi-frequency synthetic data streams."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data consistency validator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.validation_count = 0
        
        # Validation tolerances
        self.price_tolerance = config.get('VALIDATION_PRICE_TOLERANCE', 0.001)  # 0.1%
        self.volume_tolerance = config.get('VALIDATION_VOLUME_TOLERANCE', 0.05)  # 5%
        self.vwap_tolerance = config.get('VALIDATION_VWAP_TOLERANCE', 0.002)  # 0.2%
        
        # Data collection windows
        self._tick_buffers: Dict[str, List[TickData]] = {}
        self._minute_bars: Dict[str, List[Dict[str, Any]]] = {}
        self._fmv_updates: Dict[str, List[Dict[str, Any]]] = {}
        
        # Validation history
        self._validation_results: List[ValidationResult] = []
        
        logger.info("DATA-CONSISTENCY: DataConsistencyValidator initialized")
    
    def add_tick_data(self, ticker: str, tick: TickData):
        """
        Add tick data to validation buffer.
        
        Args:
            ticker: Stock ticker symbol
            tick: Per-second tick data
        """
        if ticker not in self._tick_buffers:
            self._tick_buffers[ticker] = []
        
        self._tick_buffers[ticker].append(tick)
        
        # Keep only recent ticks (last 5 minutes)
        cutoff_time = time.time() - 300
        self._tick_buffers[ticker] = [
            t for t in self._tick_buffers[ticker] 
            if t.timestamp >= cutoff_time
        ]
    
    def add_minute_bar(self, ticker: str, minute_bar: Dict[str, Any]):
        """
        Add per-minute bar data to validation buffer.
        
        Args:
            ticker: Stock ticker symbol
            minute_bar: Per-minute aggregate bar
        """
        if ticker not in self._minute_bars:
            self._minute_bars[ticker] = []
        
        self._minute_bars[ticker].append(minute_bar)
        
        # Keep only recent bars (last 10 minutes)
        cutoff_time = time.time() - 600
        self._minute_bars[ticker] = [
            bar for bar in self._minute_bars[ticker]
            if bar.get('timestamp', 0) >= cutoff_time
        ]
    
    def add_fmv_update(self, ticker: str, fmv_update: Dict[str, Any]):
        """
        Add FMV update to validation buffer.
        
        Args:
            ticker: Stock ticker symbol
            fmv_update: Fair market value update
        """
        if ticker not in self._fmv_updates:
            self._fmv_updates[ticker] = []
        
        self._fmv_updates[ticker].append(fmv_update)
        
        # Keep only recent FMV updates (last 10 minutes)
        cutoff_time = time.time() - 600
        self._fmv_updates[ticker] = [
            fmv for fmv in self._fmv_updates[ticker]
            if fmv.get('t', 0) / 1000 >= cutoff_time  # FMV timestamps in ms
        ]
    
    def validate_minute_bar_consistency(self, ticker: str, minute_bar: Dict[str, Any]) -> ValidationResult:
        """
        Validate that a minute bar is mathematically consistent with underlying tick data.
        
        Args:
            ticker: Stock ticker symbol
            minute_bar: Per-minute aggregate bar to validate
            
        Returns:
            ValidationResult: Validation results and metrics
        """
        validation_start = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        # Get the time window for this minute bar
        bar_timestamp = minute_bar.get('timestamp', time.time())
        window_start = bar_timestamp
        window_end = bar_timestamp + 60  # 60-second window
        
        # Find corresponding tick data
        if ticker not in self._tick_buffers:
            errors.append(f"No tick data available for {ticker}")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                metrics=metrics,
                validation_time=time.time() - validation_start
            )
        
        # Get ticks within the minute window
        window_ticks = [
            tick for tick in self._tick_buffers[ticker]
            if window_start <= tick.timestamp < window_end
        ]
        
        if not window_ticks:
            warnings.append(f"No tick data found for minute window {datetime.fromtimestamp(bar_timestamp)}")
            return ValidationResult(
                is_valid=True,  # Not invalid, just no data to validate
                errors=errors,
                warnings=warnings,
                metrics=metrics,
                validation_time=time.time() - validation_start
            )
        
        # Create aggregated tick window for comparison
        tick_window = self._aggregate_tick_window(window_ticks, window_start, window_end)
        
        # Validate OHLC consistency
        ohlc_valid, ohlc_errors, ohlc_metrics = self._validate_ohlc_consistency(
            minute_bar, tick_window
        )
        errors.extend(ohlc_errors)
        metrics.update(ohlc_metrics)
        
        # Validate volume consistency
        volume_valid, volume_errors, volume_metrics = self._validate_volume_consistency(
            minute_bar, tick_window
        )
        errors.extend(volume_errors)
        metrics.update(volume_metrics)
        
        # Validate VWAP consistency
        vwap_valid, vwap_errors, vwap_metrics = self._validate_vwap_consistency(
            minute_bar, tick_window
        )
        errors.extend(vwap_errors)
        metrics.update(vwap_metrics)
        
        # Overall validation
        is_valid = ohlc_valid and volume_valid and vwap_valid
        
        # Store validation result
        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
            validation_time=time.time() - validation_start
        )
        
        self._validation_results.append(result)
        self.validation_count += 1
        
        if not is_valid:
            logger.warning(
                f"DATA-CONSISTENCY: Validation failed for {ticker} minute bar at "
                f"{datetime.fromtimestamp(bar_timestamp)}: {len(errors)} errors"
            )
        elif self.validation_count % 10 == 0:
            logger.debug(
                f"DATA-CONSISTENCY: Validated {self.validation_count} minute bars, "
                f"latest: {ticker} ({len(window_ticks)} underlying ticks)"
            )
        
        return result
    
    def _aggregate_tick_window(self, ticks: List[TickData], start_time: float, end_time: float) -> TickWindow:
        """Aggregate tick data into a window for comparison with minute bars."""
        if not ticks:
            raise ValueError("Cannot aggregate empty tick list")
        
        # Sort ticks by timestamp
        sorted_ticks = sorted(ticks, key=lambda t: t.timestamp)
        
        # Calculate OHLC from ticks
        open_price = sorted_ticks[0].price
        close_price = sorted_ticks[-1].price
        high_price = max(tick.price for tick in sorted_ticks)
        low_price = min(tick.price for tick in sorted_ticks)
        
        # Calculate total volume
        total_volume = sum(tick.volume for tick in sorted_ticks)
        
        # Calculate VWAP (Volume Weighted Average Price)
        if total_volume > 0:
            weighted_sum = sum(tick.price * tick.volume for tick in sorted_ticks)
            vwap = weighted_sum / total_volume
        else:
            vwap = (open_price + close_price) / 2  # Simple average if no volume
        
        return TickWindow(
            ticks=sorted_ticks,
            start_time=start_time,
            end_time=end_time,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            total_volume=total_volume,
            vwap=vwap
        )
    
    def _validate_ohlc_consistency(self, minute_bar: Dict[str, Any], tick_window: TickWindow) -> Tuple[bool, List[str], Dict[str, float]]:
        """Validate OHLC prices match between minute bar and aggregated ticks."""
        errors = []
        metrics = {}
        
        # Extract minute bar OHLC
        bar_open = minute_bar.get('o', 0)
        bar_high = minute_bar.get('h', 0)
        bar_low = minute_bar.get('l', 0)
        bar_close = minute_bar.get('c', 0)
        
        # Calculate percentage differences
        open_diff = abs(bar_open - tick_window.open_price) / tick_window.open_price if tick_window.open_price > 0 else 0
        high_diff = abs(bar_high - tick_window.high_price) / tick_window.high_price if tick_window.high_price > 0 else 0
        low_diff = abs(bar_low - tick_window.low_price) / tick_window.low_price if tick_window.low_price > 0 else 0
        close_diff = abs(bar_close - tick_window.close_price) / tick_window.close_price if tick_window.close_price > 0 else 0
        
        metrics.update({
            'ohlc_open_diff_pct': open_diff,
            'ohlc_high_diff_pct': high_diff,
            'ohlc_low_diff_pct': low_diff,
            'ohlc_close_diff_pct': close_diff
        })
        
        # Check tolerances
        if open_diff > self.price_tolerance:
            errors.append(f"Open price mismatch: bar={bar_open:.2f} vs ticks={tick_window.open_price:.2f} ({open_diff:.2%})")
        
        if high_diff > self.price_tolerance:
            errors.append(f"High price mismatch: bar={bar_high:.2f} vs ticks={tick_window.high_price:.2f} ({high_diff:.2%})")
        
        if low_diff > self.price_tolerance:
            errors.append(f"Low price mismatch: bar={bar_low:.2f} vs ticks={tick_window.low_price:.2f} ({low_diff:.2%})")
        
        if close_diff > self.price_tolerance:
            errors.append(f"Close price mismatch: bar={bar_close:.2f} vs ticks={tick_window.close_price:.2f} ({close_diff:.2%})")
        
        return len(errors) == 0, errors, metrics
    
    def _validate_volume_consistency(self, minute_bar: Dict[str, Any], tick_window: TickWindow) -> Tuple[bool, List[str], Dict[str, float]]:
        """Validate volume consistency between minute bar and aggregated ticks."""
        errors = []
        metrics = {}
        
        bar_volume = minute_bar.get('v', 0)
        tick_volume = tick_window.total_volume
        
        if tick_volume > 0:
            volume_diff = abs(bar_volume - tick_volume) / tick_volume
            metrics['volume_diff_pct'] = volume_diff
            
            if volume_diff > self.volume_tolerance:
                errors.append(
                    f"Volume mismatch: bar={bar_volume:,} vs ticks={tick_volume:,} ({volume_diff:.2%})"
                )
        else:
            metrics['volume_diff_pct'] = 0.0
        
        return len(errors) == 0, errors, metrics
    
    def _validate_vwap_consistency(self, minute_bar: Dict[str, Any], tick_window: TickWindow) -> Tuple[bool, List[str], Dict[str, float]]:
        """Validate VWAP consistency between minute bar and aggregated ticks."""
        errors = []
        metrics = {}
        
        bar_vwap = minute_bar.get('vw', 0)
        tick_vwap = tick_window.vwap
        
        if tick_vwap > 0:
            vwap_diff = abs(bar_vwap - tick_vwap) / tick_vwap
            metrics['vwap_diff_pct'] = vwap_diff
            
            if vwap_diff > self.vwap_tolerance:
                errors.append(
                    f"VWAP mismatch: bar={bar_vwap:.2f} vs ticks={tick_vwap:.2f} ({vwap_diff:.2%})"
                )
        else:
            metrics['vwap_diff_pct'] = 0.0
        
        return len(errors) == 0, errors, metrics
    
    def validate_fmv_correlation(self, ticker: str, fmv_update: Dict[str, Any]) -> ValidationResult:
        """
        Validate FMV correlation with market price movements.
        
        Args:
            ticker: Stock ticker symbol
            fmv_update: Fair market value update to validate
            
        Returns:
            ValidationResult: Validation results focusing on price correlation
        """
        validation_start = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        fmv_price = fmv_update.get('fmv', 0)
        market_price = fmv_update.get('mp', 0)
        premium_discount = fmv_update.get('pd', 0)
        confidence = fmv_update.get('conf', 0)
        
        # Validate premium/discount is reasonable (within ±10%)
        if abs(premium_discount) > 0.10:
            warnings.append(f"Large FMV premium/discount: {premium_discount:.2%}")
        
        # Validate confidence score is reasonable (0.1 to 1.0)
        if not (0.1 <= confidence <= 1.0):
            errors.append(f"Invalid confidence score: {confidence}")
        
        # Validate FMV and market price are positive
        if fmv_price <= 0:
            errors.append(f"Invalid FMV price: {fmv_price}")
        
        if market_price <= 0:
            errors.append(f"Invalid market price: {market_price}")
        
        metrics.update({
            'fmv_premium_discount': premium_discount,
            'fmv_confidence': confidence,
            'fmv_price': fmv_price,
            'market_price': market_price
        })
        
        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
            validation_time=time.time() - validation_start
        )
        
        return result
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation results."""
        if not self._validation_results:
            return {
                'total_validations': 0,
                'success_rate': 0.0,
                'average_validation_time': 0.0,
                'common_errors': []
            }
        
        successful = sum(1 for r in self._validation_results if r.is_valid)
        total = len(self._validation_results)
        
        # Collect all errors
        all_errors = []
        for result in self._validation_results:
            all_errors.extend(result.errors)
        
        # Count error frequency
        error_counts = {}
        for error in all_errors:
            # Extract error type (first part before colon)
            error_type = error.split(':')[0] if ':' in error else error[:50]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Sort by frequency
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        avg_time = sum(r.validation_time for r in self._validation_results) / total
        
        return {
            'total_validations': total,
            'successful_validations': successful,
            'success_rate': successful / total,
            'average_validation_time': avg_time,
            'common_errors': common_errors,
            'last_10_results': [r.is_valid for r in self._validation_results[-10:]]
        }