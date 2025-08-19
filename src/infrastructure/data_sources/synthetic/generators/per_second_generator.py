"""
Per-Second Data Generator

Generates real-time tick-level synthetic data maintaining backward compatibility
with existing SimulatedDataProvider functionality while supporting the new
multi-frequency architecture.
"""

import random
import time
from typing import Dict, Any, Union
from src.core.domain.market.tick import TickData
from src.infrastructure.data_sources.synthetic.types import DataFrequency
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'per_second_generator')


class PerSecondGenerator:
    """Generates per-second tick data with realistic market behavior patterns."""
    
    def __init__(self, config: Dict[str, Any], provider):
        """
        Initialize the per-second generator.
        
        Args:
            config: Configuration dictionary
            provider: Reference to parent SimulatedDataProvider for shared state
        """
        self.config = config
        self.provider = provider
        self.generation_count = 0
        
        # Per-second specific configuration
        self.tick_variance = config.get('SYNTHETIC_TICK_VARIANCE', 0.001)  # 0.1%
        self.volume_base_multiplier = config.get('SYNTHETIC_VOLUME_MULTIPLIER', 1.0)
        self.vwap_variance = config.get('SYNTHETIC_VWAP_VARIANCE', 0.002)  # 0.2%
        
        logger.info("PER-SEC-GEN: PerSecondGenerator initialized for real-time tick generation")
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> TickData:
        """
        Generate a single per-second tick data point.
        
        Args:
            ticker: Stock ticker symbol
            config: Generation configuration
            
        Returns:
            TickData: Real-time tick data object
        """
        generation_start = time.time()
        current_price = self.provider.get_ticker_price(ticker)
        current_time = time.time()
        
        # Generate realistic tick-level price variations
        tick_high = round(current_price * (1 + random.uniform(0, self.tick_variance)), 2)
        tick_low = round(current_price * (1 - random.uniform(0, self.tick_variance)), 2)
        tick_open = round(current_price * (1 + random.uniform(-self.tick_variance/2, self.tick_variance/2)), 2)
        
        # Generate volume based on activity level and market session
        tick_volume = self._generate_realistic_volume(ticker, current_time)
        
        # Generate VWAP with slight variance from current price
        tick_vwap = round(current_price * (1 + random.uniform(-self.vwap_variance, self.vwap_variance)), 2)
        
        # Create tick data object
        tick = TickData(
            ticker=ticker,
            price=current_price,
            volume=tick_volume,
            timestamp=current_time,
            source='simulated_per_second',
            event_type='A',  # Aggregate tick
            market_status=self.provider.get_market_status(),
            bid=round(current_price * 0.9995, 2),  # Tighter spread for per-second
            ask=round(current_price * 1.0005, 2),
            tick_open=tick_open,
            tick_high=tick_high,
            tick_low=tick_low,
            tick_close=current_price,
            tick_volume=tick_volume,
            tick_vwap=tick_vwap,
            vwap=tick_vwap,
            tick_start_timestamp=current_time - 1,  # 1 second window
            tick_end_timestamp=current_time
        )
        
        self.generation_count += 1
        
        # Log statistics periodically
        if self.generation_count % 50 == 0:
            generation_time = (time.time() - generation_start) * 1000
            logger.debug(
                f"PER-SEC-GEN: Generated {self.generation_count} per-second ticks. "
                f"Latest: {ticker} @ ${current_price} vol={tick_volume} ({generation_time:.2f}ms)"
            )
        
        return tick
    
    def _generate_realistic_volume(self, ticker: str, timestamp: float) -> int:
        """
        Generate realistic volume based on market conditions and activity level.
        
        Args:
            ticker: Stock ticker symbol
            timestamp: Current timestamp
            
        Returns:
            int: Realistic volume for the tick
        """
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        market_status = self.provider.get_market_status()
        
        # Base volume ranges by activity level
        volume_ranges = {
            'low': (100, 2000),
            'medium': (500, 5000), 
            'high': (2000, 15000),
            'opening_bell': (10000, 50000)
        }
        
        base_min, base_max = volume_ranges.get(activity_level, (500, 5000))
        
        # Adjust for market session
        if market_status == 'REGULAR':
            # Regular market hours - use base volumes
            volume_multiplier = 1.0
        elif market_status == 'PRE':
            # Pre-market - lower volume
            volume_multiplier = 0.3
        elif market_status == 'AFTER':
            # After-hours - lower volume  
            volume_multiplier = 0.4
        else:
            # Market closed - minimal volume
            volume_multiplier = 0.1
        
        # Apply session multiplier
        min_vol = max(50, int(base_min * volume_multiplier))
        max_vol = max(100, int(base_max * volume_multiplier))
        
        # Add some randomness for realism
        volume = random.randint(min_vol, max_vol)
        
        # Apply per-ticker adjustments (some tickers are naturally more active)
        ticker_multiplier = self._get_ticker_volume_multiplier(ticker)
        
        return max(50, int(volume * ticker_multiplier))
    
    def _get_ticker_volume_multiplier(self, ticker: str) -> float:
        """Get volume multiplier based on ticker characteristics."""
        # High-volume tickers (simulate popular stocks)
        high_volume_tickers = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN', 'GOOGL']
        medium_volume_tickers = ['META', 'NFLX', 'AMD', 'INTC', 'CRM'] 
        
        if ticker in high_volume_tickers:
            return random.uniform(2.0, 4.0)
        elif ticker in medium_volume_tickers:
            return random.uniform(1.5, 2.5)
        else:
            return random.uniform(0.8, 1.5)
    
    def supports_frequency(self, frequency: DataFrequency) -> bool:
        """Check if generator supports the given frequency."""
        return frequency == DataFrequency.PER_SECOND
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get generation statistics for this generator."""
        return {
            'type': 'per_second',
            'total_generated': self.generation_count,
            'config': {
                'tick_variance': self.tick_variance,
                'volume_multiplier': self.volume_base_multiplier,
                'vwap_variance': self.vwap_variance
            }
        }