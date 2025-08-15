import random
import time
import pytz
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.infrastructure.data_sources.synthetic..base.data_provider import DataProvider
from src.core.domain.market.tick import TickData  # Replace MarketEvent import
from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'simulated_data_provider')

class SimulatedDataProvider(DataProvider):
    """Provider that generates simulated stock market data with comprehensive tracing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.market_timezone = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))
        self.price_seeds = {}
        self.sectors = ["Technology", "Healthcare", "Financial", "Consumer", "Industrial", "Energy"]
        self.ticker_sectors = {}
        self.last_price_time = {}  # Track last price generation per ticker
        self.last_price = {}  # Store last price per ticker
        
        # Track tick generation statistics
        self.ticks_generated = 0
        self.last_stats_log = time.time()
        
        logger.info("🚀 SIM-DATA-PROVIDER: SimulatedDataProvider initialized with tracing enabled")
        
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='SimulatedDataProvider',
                action='initialized',
                data={
                    'input_count': ensure_int(0),
                    'output_count': ensure_int(0),
                    'duration_ms': 0,
                    'details': {
                        'market_timezone': str(self.market_timezone),
                        'activity_level': config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
                    }
                }
            )
    
    def validate_tick_data(self, tick: TickData) -> bool:
        """Validate TickData object."""
        try:
            return tick.validate()  # TickData has built-in validation
        except Exception as e:
            logger.warning(f"SIM-DATA-PROVIDER: Invalid TickData: {e}")
            return False
    
    def get_market_status(self) -> str:
        utc_now = datetime.now(pytz.utc)
        eastern_now = utc_now.astimezone(self.market_timezone)
        market_status = "CLOSED"
        if eastern_now.weekday() < 5:
            if eastern_now.hour == 9 and eastern_now.minute >= 30 or eastern_now.hour > 9 and eastern_now.hour < 16:
                market_status = "REGULAR"
            elif (eastern_now.hour >= 4 and eastern_now.hour < 9) or (eastern_now.hour == 9 and eastern_now.minute < 30):
                market_status = "PRE"
            elif eastern_now.hour >= 16 and eastern_now.hour < 20:
                market_status = "AFTER"
        return market_status
    
    def get_ticker_price(self, ticker: str) -> float:
        # Rate-limit to 1 price per 0.2s per ticker
        current_time = time.time()
        if ticker in self.last_price_time and current_time - self.last_price_time[ticker] < 0.2:
            logger.debug(f"SIM-DATA-PROVIDER: Skipping price for {ticker}: too frequent")
            
            return self.last_price.get(ticker, 100.0)
        
        self.last_price_time[ticker] = current_time
        
        if ticker not in self.price_seeds:
            self.price_seeds[ticker] = random.randint(1, 1000)
        base_price = 100 + (hash(ticker) % 100)
        time_factor = int(current_time / 5)
        random.seed(self.price_seeds[ticker] + time_factor)
        
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        variance_map = {'low': 5, 'medium': 10, 'high': 20, 'opening_bell': 50}
        variance = variance_map.get(activity_level, 10)
        
        price = base_price + random.uniform(-variance, variance) + (current_time % 20) / 10
        price = max(1.0, price)
        self.last_price[ticker] = price  # Store last price
        
        logger.debug(f"SIM-DATA-PROVIDER: Generated price for {ticker}: {price}, activity_level={activity_level}")
        return price
    
    def generate_tick_data(self, ticker: str) -> TickData:
        """Generate a TickData object for the ticker with comprehensive tracing."""

        """Generate realistic tick data"""
        # TEMPORARY DEBUG
        import sys
        print(f"DEBUG: generate_tick_data called for {ticker}", file=sys.stderr)


        generation_start = time.time()
        current_price = self.get_ticker_price(ticker)
        current_time = time.time()
        
        # Generate realistic tick variations
        tick_variance = 0.001  # 0.1% variance for tick data
        tick_high = round(current_price * (1 + random.uniform(0, tick_variance)), 2)
        tick_low = round(current_price * (1 - random.uniform(0, tick_variance)), 2)
        tick_open = round(current_price * (1 + random.uniform(-tick_variance/2, tick_variance/2)), 2)
        
        # Generate volume based on activity level
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        volume_map = {'low': (1000, 10000), 'medium': (10000, 100000), 
                      'high': (100000, 500000), 'opening_bell': (500000, 1000000)}
        volume_range = volume_map.get(activity_level, (10000, 100000))
        tick_volume = random.randint(*volume_range)
        
        # Generate VWAP
        vwap_variance = 0.002  # 0.2% variance from price
        tick_vwap = round(current_price * (1 + random.uniform(-vwap_variance, vwap_variance)), 2)
        
        # Create the tick
        tick = TickData(
            ticker=ticker,
            price=current_price,
            volume=tick_volume,
            timestamp=current_time,
            source='simulated',
            event_type='A',  # Aggregate
            market_status=self.get_market_status(),
            bid=round(current_price * 0.999, 2),
            ask=round(current_price * 1.001, 2),
            tick_open=tick_open,
            tick_high=tick_high,
            tick_low=tick_low,
            tick_close=current_price,
            tick_volume=tick_volume,
            tick_vwap=tick_vwap,
            vwap=tick_vwap,  # For simulated data, use same as tick_vwap
            tick_start_timestamp=current_time - 1,  # 1 second window
            tick_end_timestamp=current_time
        )
        
        self.ticks_generated += 1
        
        # TRACE: Tick generated at source
        if tracer.should_trace(ticker):
            tracer.trace(
                ticker=ticker,
                component='SimulatedDataProvider',
                action='tick_generated',
                data={
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(1),
                    'duration_ms': (time.time() - generation_start) * 1000,
                    'details': {
                        'detail_ticker': ticker,
                        'price': current_price,
                        'volume': tick_volume,
                        'market_status': tick.market_status,
                        'tick_number': self.ticks_generated
                    }
                }
            )
        
        # Log stats periodically
        if time.time() - self.last_stats_log % 10 == 0:
            logger.info(f"📊 SIM-DATA-PROVIDER: Every 10 Generated {self.ticks_generated} ticks total")
            self.last_stats_log = time.time()

        # Log first few ticks for debugging
        if self.ticks_generated % 10 == 0:
            logger.info(f"🎯 SIM-DATA-PROVIDER: Every 10 Generated tick #{self.ticks_generated}: {ticker} @ ${current_price} vol={tick_volume}")
        
        return tick
    
    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """Get detailed ticker information with tracing."""
        detail_start = time.time()
        current_price = self.get_ticker_price(ticker)
        
        if ticker not in self.ticker_sectors:
            self.ticker_sectors[ticker] = random.choice(self.sectors)
        
        # Generate day-level data
        open_price = current_price * (1 + random.uniform(-0.05, 0.05))
        day_high = max(current_price, open_price) * (1 + random.uniform(0, 0.03))
        day_low = min(current_price, open_price) * (1 - random.uniform(0, 0.03))
        prev_close = current_price * (1 + random.uniform(-0.1, 0.1))
        volume = random.randint(10000, 10000000)
        base_shares = random.randint(10, 500) * 1000000
        market_cap = current_price * base_shares
        
        # Create a TickData object for validation
        tick = self.generate_tick_data(ticker)
        
        # Update tick with day-level data
        tick.day_high = round(day_high, 2)
        tick.day_low = round(day_low, 2)
        tick.open_price = round(open_price, 2)
        tick.previous_close = round(prev_close, 2)
        tick.accumulated_volume = volume
        
        if not self.validate_tick_data(tick):
            logger.error(f"SIM-DATA-PROVIDER: Generated invalid TickData for {ticker}")
            
            return {}
        
        details = {
            "ticker": ticker,
            "name": f"{ticker} Corporation",
            "price": current_price,
            "change": current_price - prev_close,
            "change_percent": ((current_price - prev_close) / prev_close) * 100,
            "open": open_price,
            "high": day_high,
            "low": day_low,
            "prev_close": prev_close,
            "volume": volume,
            "market_cap": market_cap,
            "sector": self.ticker_sectors[ticker],
            "pe_ratio": random.uniform(5, 50),
            "dividend_yield": random.uniform(0, 5),
            "last_updated": datetime.now().isoformat()
        }
       
        
        return details
    def get_multiple_tickers(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get details for multiple tickers with batch tracing."""
        batch_start = time.time()
        results = {}
        
        
        for ticker in tickers:
            results[ticker] = self.get_ticker_details(ticker)
        
        
        return results
    '''    
    def get_next_tick(self, ticker: str) -> Optional[TickData]:
        """Generate the next tick for a ticker - used by real-time simulation."""
        start_time = time.time()
        try:
            tick = self.generate_tick_data(ticker)
            
            return tick
            
        except Exception as e:
            logger.error(f"SIM-DATA-PROVIDER: Error generating tick for {ticker}: {e}")
            
            return None
    '''

    def is_available(self) -> bool:
        return True