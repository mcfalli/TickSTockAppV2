"""Simplified synthetic data provider for TickStockPL integration.

PHASE 6 CLEANUP: Simplified to basic tick data generation with:
- Simple price generation algorithm
- Standard TickData objects
- Basic market status detection
- Redis publishing for TickStockPL integration

Removed: Multi-frequency generators, validation systems, complex statistics.
"""
import random
import time
import pytz
from datetime import datetime
from typing import Dict, Any

from src.core.interfaces.data_provider import DataProvider
from src.core.domain.market.tick import TickData
import logging

logger = logging.getLogger(__name__)

class SimulatedDataProvider(DataProvider):
    """Simplified provider that generates synthetic stock market data."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.market_timezone = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))
        
        # Basic price tracking
        self.price_seeds = {}
        self.last_price_time = {}
        self.last_price = {}
        
        # Basic statistics
        self.ticks_generated = 0
        
        logger.info("SIM-DATA-PROVIDER: Simplified synthetic data provider initialized")
    
    def get_market_status(self) -> str:
        """Get current market status based on time."""
        utc_now = datetime.now(pytz.utc)
        eastern_now = utc_now.astimezone(self.market_timezone)
        
        if eastern_now.weekday() < 5:  # Monday to Friday
            if (eastern_now.hour == 9 and eastern_now.minute >= 30) or (9 < eastern_now.hour < 16):
                return "REGULAR"
            elif eastern_now.hour >= 4 and eastern_now.hour < 9 or (eastern_now.hour == 9 and eastern_now.minute < 30):
                return "PRE"
            elif 16 <= eastern_now.hour < 20:
                return "AFTER"
        return "CLOSED"
    
    def get_ticker_price(self, ticker: str) -> float:
        """Generate a realistic price for a ticker."""
        current_time = time.time()
        
        # Rate limiting to prevent excessive generation
        if ticker in self.last_price_time and current_time - self.last_price_time[ticker] < 0.2:
            return self.last_price.get(ticker, 100.0)
        
        self.last_price_time[ticker] = current_time
        
        # Initialize price seed for consistent behavior
        if ticker not in self.price_seeds:
            self.price_seeds[ticker] = random.randint(1, 1000)
        
        # Generate base price
        base_price = 100 + (hash(ticker) % 100)
        time_factor = int(current_time / 5)
        random.seed(self.price_seeds[ticker] + time_factor)
        
        # Apply variance based on activity level
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        variance_map = {'low': 5, 'medium': 10, 'high': 20}
        variance = variance_map.get(activity_level, 10)
        
        price = base_price + random.uniform(-variance, variance) + (current_time % 20) / 10
        price = max(1.0, price)
        self.last_price[ticker] = price
        
        return price
    
    def generate_tick_data(self, ticker: str) -> TickData:
        """Generate synthetic tick data for a ticker."""
        current_time = time.time()
        current_price = self.get_ticker_price(ticker)
        
        # Generate realistic tick variations
        tick_variance = 0.001
        tick_high = round(current_price * (1 + random.uniform(0, tick_variance)), 2)
        tick_low = round(current_price * (1 - random.uniform(0, tick_variance)), 2)
        tick_open = round(current_price * (1 + random.uniform(-tick_variance/2, tick_variance/2)), 2)
        
        # Generate volume
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        volume_map = {'low': (1000, 10000), 'medium': (10000, 100000), 'high': (100000, 500000)}
        volume_range = volume_map.get(activity_level, (10000, 100000))
        tick_volume = random.randint(*volume_range)
        
        # Generate VWAP
        tick_vwap = round(current_price * (1 + random.uniform(-0.002, 0.002)), 2)
        
        tick = TickData(
            ticker=ticker,
            price=current_price,
            volume=tick_volume,
            timestamp=current_time,
            source='simulated',
            event_type='A',
            market_status=self.get_market_status(),
            bid=round(current_price * 0.999, 2),
            ask=round(current_price * 1.001, 2),
            tick_open=tick_open,
            tick_high=tick_high,
            tick_low=tick_low,
            tick_close=current_price,
            tick_volume=tick_volume,
            tick_vwap=tick_vwap,
            vwap=tick_vwap,
            tick_start_timestamp=current_time - 1,
            tick_end_timestamp=current_time
        )
        
        self.ticks_generated += 1
        
        # Tick generation is normal operation - no logging needed for each tick
        
        return tick
    
    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive ticker details."""
        current_price = self.get_ticker_price(ticker)
        
        # Generate day-level data
        open_price = current_price * (1 + random.uniform(-0.05, 0.05))
        day_high = max(current_price, open_price) * (1 + random.uniform(0, 0.03))
        day_low = min(current_price, open_price) * (1 - random.uniform(0, 0.03))
        prev_close = current_price * (1 + random.uniform(-0.1, 0.1))
        volume = random.randint(10000, 10000000)
        
        return {
            "ticker": ticker,
            "name": f"{ticker} Corporation",
            "price": current_price,
            "change": current_price - prev_close,
            "change_percent": ((current_price - prev_close) / prev_close) * 100,
            "open": round(open_price, 2),
            "high": round(day_high, 2),
            "low": round(day_low, 2),
            "prev_close": round(prev_close, 2),
            "volume": volume,
            "market_cap": current_price * random.randint(10, 500) * 1000000,
            "sector": random.choice(["Technology", "Healthcare", "Financial", "Consumer", "Industrial"]),
            "last_updated": datetime.now().isoformat()
        }
    
    def get_multiple_tickers(self, tickers: list) -> Dict[str, Dict[str, Any]]:
        """Get details for multiple tickers."""
        return {ticker: self.get_ticker_details(ticker) for ticker in tickers}
    
    def is_available(self) -> bool:
        """Synthetic data is always available."""
        return True