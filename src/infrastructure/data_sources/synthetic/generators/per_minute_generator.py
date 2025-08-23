"""
Per-Minute Data Generator

Generates realistic OHLCV aggregate bars that mathematically align with 
underlying per-second tick data. Simulates Polygon AM (aggregate minute) events.
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from src.infrastructure.data_sources.synthetic.types import DataFrequency
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'per_minute_generator')


class PerMinuteGenerator:
    """Generates per-minute OHLCV aggregate data from synthetic tick streams."""
    
    def __init__(self, config: Dict[str, Any], provider):
        """
        Initialize the per-minute generator.
        
        Args:
            config: Configuration dictionary 
            provider: Reference to parent SimulatedDataProvider
        """
        self.config = config
        self.provider = provider
        self.generation_count = 0
        
        # Per-minute specific configuration
        self.aggregate_window = config.get('SYNTHETIC_MINUTE_WINDOW', 60)  # seconds
        self.volume_amplification = config.get('SYNTHETIC_MINUTE_VOLUME_MULTIPLIER', 50)
        self.price_drift_variance = config.get('SYNTHETIC_MINUTE_DRIFT', 0.005)  # 0.5%
        
        # Maintain minute-level price history for realistic OHLC generation
        self._price_history: Dict[str, List[Dict[str, Any]]] = {}
        self._last_minute_generated: Dict[str, float] = {}
        
        logger.info("PER-MIN-GEN: PerMinuteGenerator initialized for aggregate OHLCV generation")
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a per-minute OHLCV aggregate bar.
        
        Args:
            ticker: Stock ticker symbol
            config: Generation configuration
            
        Returns:
            Dict: Per-minute aggregate data in Polygon AM event format
        """
        current_time = time.time()
        minute_timestamp = self._round_to_minute(current_time)
        
        logger.info(f"🔍 PER-MIN-GEN: Attempting to generate data for {ticker}, current_time={current_time}, minute_timestamp={minute_timestamp}")
        
        # Check if we already generated this minute (avoid duplicates)
        if ticker in self._last_minute_generated:
            if minute_timestamp <= self._last_minute_generated[ticker]:
                logger.info(f"🔍 PER-MIN-GEN: Skipping duplicate minute for {ticker} - minute_timestamp={minute_timestamp}, last_generated={self._last_minute_generated[ticker]}")
                return None
        
        logger.info(f"🔍 PER-MIN-GEN: Proceeding with generation for {ticker}")
        self._last_minute_generated[ticker] = minute_timestamp
        
        # Generate realistic OHLCV based on underlying tick simulation
        ohlcv_data = self._generate_minute_ohlcv(ticker, minute_timestamp)
        
        # Create Polygon AM-style event structure
        am_event = self._create_am_event_structure(ticker, ohlcv_data, minute_timestamp)
        
        self.generation_count += 1
        
        # Log statistics
        if self.generation_count % 10 == 0:
            logger.debug(
                f"PER-MIN-GEN: Generated {self.generation_count} minute bars. "
                f"Latest: {ticker} O:{ohlcv_data['open']} H:{ohlcv_data['high']} "
                f"L:{ohlcv_data['low']} C:{ohlcv_data['close']} V:{ohlcv_data['volume']}"
            )
        
        return am_event
    
    def _round_to_minute(self, timestamp: float) -> float:
        """Round timestamp to the nearest minute boundary."""
        dt = datetime.fromtimestamp(timestamp)
        # Round down to minute boundary
        rounded_dt = dt.replace(second=0, microsecond=0)
        return rounded_dt.timestamp()
    
    def _generate_minute_ohlcv(self, ticker: str, minute_timestamp: float) -> Dict[str, Any]:
        """
        Generate realistic OHLCV data for a minute window.
        
        This simulates aggregating 60 seconds of tick data into a minute bar,
        ensuring mathematical consistency that would exist in real data.
        """
        # Get current price as starting point
        base_price = self.provider.get_ticker_price(ticker)
        
        # Generate realistic price movement within the minute
        prices = self._simulate_minute_price_path(ticker, base_price)
        
        # Calculate OHLC from the price path
        open_price = prices[0]
        high_price = max(prices)
        low_price = min(prices)
        close_price = prices[-1]
        
        # Update provider's price to maintain consistency
        self.provider.last_price[ticker] = close_price
        
        # Generate volume that represents aggregation of tick volumes
        volume = self._generate_minute_volume(ticker, minute_timestamp)
        
        # Calculate volume-weighted average price (VWAP)
        vwap = self._calculate_realistic_vwap(open_price, high_price, low_price, close_price, volume)
        
        return {
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': int(volume),
            'vwap': round(vwap, 2),
            'timestamp': minute_timestamp,
            'transactions': random.randint(20, 200)  # Simulated transaction count
        }
    
    def _simulate_minute_price_path(self, ticker: str, base_price: float) -> List[float]:
        """Simulate realistic price path over a 60-second window."""
        prices = [base_price]
        current_price = base_price
        
        # Generate 12 price points (every 5 seconds) for realistic path
        for i in range(1, 13):
            # Add some trend and random walk
            trend_component = random.uniform(-0.001, 0.001)  # Small trend
            random_component = random.uniform(-self.price_drift_variance, self.price_drift_variance)
            
            # Apply market session volatility
            session_multiplier = self._get_session_volatility_multiplier()
            total_change = (trend_component + random_component) * session_multiplier
            
            current_price = max(0.01, current_price * (1 + total_change))
            prices.append(current_price)
        
        return prices
    
    def _get_session_volatility_multiplier(self) -> float:
        """Get volatility multiplier based on market session."""
        market_status = self.provider.get_market_status()
        
        if market_status == 'REGULAR':
            return 1.0  # Normal volatility
        elif market_status == 'PRE' or market_status == 'AFTER':
            return 1.5  # Higher volatility in extended hours
        else:
            return 0.5  # Lower volatility when market closed
    
    def _generate_minute_volume(self, ticker: str, timestamp: float) -> float:
        """Generate realistic minute-level volume as aggregation of tick volumes."""
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        market_status = self.provider.get_market_status()
        
        # Base volume ranges for minute aggregates (much higher than per-second)
        volume_ranges = {
            'low': (5000, 25000),
            'medium': (15000, 80000),
            'high': (50000, 200000), 
            'opening_bell': (200000, 800000)
        }
        
        base_min, base_max = volume_ranges.get(activity_level, (15000, 80000))
        
        # Session adjustments
        session_multipliers = {
            'REGULAR': 1.0,
            'PRE': 0.4,
            'AFTER': 0.3,
            'CLOSED': 0.1
        }
        
        multiplier = session_multipliers.get(market_status, 0.5)
        
        # Add time-of-day effects (opening/closing more volume)
        time_multiplier = self._get_time_of_day_volume_multiplier(timestamp)
        
        volume = random.randint(int(base_min * multiplier), int(base_max * multiplier))
        volume = int(volume * time_multiplier)
        
        return max(1000, volume)  # Minimum volume threshold
    
    def _get_time_of_day_volume_multiplier(self, timestamp: float) -> float:
        """Apply time-of-day volume patterns."""
        dt = datetime.fromtimestamp(timestamp)
        hour = dt.hour
        minute = dt.minute
        
        # Higher volume at market open (9:30-10:00) and close (3:30-4:00)
        if (hour == 9 and minute >= 30) or (hour == 10 and minute <= 30):
            return random.uniform(1.5, 2.5)  # Opening volume
        elif (hour == 15 and minute >= 30) or (hour == 16 and minute <= 30):
            return random.uniform(1.3, 2.0)  # Closing volume
        elif 11 <= hour <= 14:
            return random.uniform(0.7, 0.9)  # Midday lull
        else:
            return random.uniform(0.9, 1.1)  # Normal trading
    
    def _calculate_realistic_vwap(self, open_p: float, high: float, low: float, close: float, volume: float) -> float:
        """Calculate a realistic VWAP based on OHLC and volume."""
        # Weighted average of OHLC with bias toward close price
        # This simulates volume-weighted behavior
        typical_price = (high + low + close * 2) / 4  # Weight close more heavily
        
        # Add small variance to make it more realistic
        variance = random.uniform(-0.001, 0.001)
        vwap = typical_price * (1 + variance)
        
        # Ensure VWAP is within OHLC range
        vwap = max(low, min(high, vwap))
        
        return vwap
    
    def _create_am_event_structure(self, ticker: str, ohlcv: Dict[str, Any], timestamp: float) -> Dict[str, Any]:
        """Create Polygon AM event structure for consistency with real data."""
        # Convert timestamp to milliseconds (Polygon format)
        timestamp_ms = int(timestamp * 1000)
        
        return {
            'ev': 'AM',  # Event type: Aggregate Minute
            'sym': ticker,  # Symbol
            'o': ohlcv['open'],  # Open
            'h': ohlcv['high'],  # High
            'l': ohlcv['low'],   # Low
            'c': ohlcv['close'], # Close
            'v': ohlcv['volume'], # Volume
            'vw': ohlcv['vwap'],  # Volume weighted average price
            'n': ohlcv['transactions'],  # Number of transactions
            't': timestamp_ms,    # Timestamp (start of minute)
            'T': timestamp_ms + 60000,  # End timestamp
            'source': 'simulated_per_minute',
            'market_status': self.provider.get_market_status()
        }
    
    def supports_frequency(self, frequency: DataFrequency) -> bool:
        """Check if generator supports the given frequency."""
        return frequency == DataFrequency.PER_MINUTE
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get generation statistics for this generator."""
        return {
            'type': 'per_minute',
            'total_generated': self.generation_count,
            'tickers_tracked': len(self._last_minute_generated),
            'config': {
                'window_seconds': self.aggregate_window,
                'volume_amplification': self.volume_amplification,
                'price_drift_variance': self.price_drift_variance
            }
        }