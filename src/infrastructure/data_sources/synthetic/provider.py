"""Production-grade synthetic data provider - Sprint 41.

SPRINT 41 ENHANCEMENTS:
- Realistic tick generation with OHLCV aggregation
- Market condition simulation (opening bell, midday, closing)
- Pattern injection (Doji, Hammer, ShootingStar, Engulfing, Harami)
- Bid/ask spread simulation
- Time-of-day volume profiles
- Configurable scenarios (normal, volatile, crash, rally)
"""
import random
import time
import pytz
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.core.interfaces.data_provider import DataProvider
from src.core.domain.market.tick import TickData
from src.infrastructure.data_sources.synthetic.universe_loader import UniverseLoader, SymbolInfo
import logging

logger = logging.getLogger(__name__)


@dataclass
class PatternDefinition:
    """Definition for candlestick pattern injection."""
    name: str
    open_pct: float  # % of close
    high_pct: float  # % of close
    low_pct: float   # % of close
    close_pct: float # Base is 1.0


# Pattern definitions based on classic candlestick patterns
PATTERNS = {
    'Doji': PatternDefinition(
        name='Doji',
        open_pct=1.0,      # Open = Close
        high_pct=1.005,    # Small upper shadow
        low_pct=0.995,     # Small lower shadow
        close_pct=1.0
    ),
    'Hammer': PatternDefinition(
        name='Hammer',
        open_pct=0.998,    # Small body
        high_pct=1.001,    # Tiny upper shadow
        low_pct=0.98,      # Long lower shadow (2%)
        close_pct=1.0
    ),
    'ShootingStar': PatternDefinition(
        name='ShootingStar',
        open_pct=1.002,    # Small body
        high_pct=1.02,     # Long upper shadow (2%)
        low_pct=0.999,     # Tiny lower shadow
        close_pct=1.0
    ),
    'BullishEngulfing': PatternDefinition(
        name='BullishEngulfing',
        open_pct=0.99,     # Opens lower
        high_pct=1.015,    # Large upper move
        low_pct=0.985,     # Lower low
        close_pct=1.01     # Closes higher
    ),
    'BearishEngulfing': PatternDefinition(
        name='BearishEngulfing',
        open_pct=1.01,     # Opens higher
        high_pct=1.015,    # Higher high
        low_pct=0.985,     # Large lower move
        close_pct=0.99     # Closes lower
    ),
    'Harami': PatternDefinition(
        name='Harami',
        open_pct=0.998,    # Small body inside previous
        high_pct=1.002,    # Contained range
        low_pct=0.997,     # Contained range
        close_pct=1.001    # Small move
    )
}


class SimulatedDataProvider(DataProvider):
    """Production-grade synthetic data provider with pattern injection."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.market_timezone = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))

        # Universe loading (Phase 3)
        universe_key = config.get('SYNTHETIC_UNIVERSE', 'market_leaders:top_500')
        logger.info(f"SIM-DATA-PROVIDER: Loading universe '{universe_key}'...")
        self.universe_loader = UniverseLoader(universe_key)
        logger.info(f"SIM-DATA-PROVIDER: Loaded {len(self.universe_loader.tickers)} symbols from universe")

        # Price tracking
        self.price_seeds = {}
        self.last_price_time = {}
        self.last_price = {}
        self.price_trend = {}  # Track price trend for pattern injection

        # Initialize prices from universe baseline
        for ticker in self.universe_loader.get_all_tickers():
            symbol_info = self.universe_loader.get_symbol_info(ticker)
            if symbol_info:
                self.last_price[ticker] = symbol_info.baseline_price

        # Pattern injection configuration
        self.pattern_injection = config.get('SYNTHETIC_PATTERN_INJECTION', True)
        self.pattern_frequency = float(config.get('SYNTHETIC_PATTERN_FREQUENCY', 0.1))
        pattern_types_str = config.get('SYNTHETIC_PATTERN_TYPES', 'Doji,Hammer,ShootingStar,BullishEngulfing,BearishEngulfing,Harami')
        self.pattern_types = [p.strip() for p in pattern_types_str.split(',')]

        # Scenario configuration
        self.scenario = config.get('SYNTHETIC_SCENARIO', 'normal')
        self._load_scenario()

        # Statistics
        self.ticks_generated = 0
        self.patterns_injected = 0
        self.pattern_counts = {pattern: 0 for pattern in PATTERNS.keys()}

        logger.info(f"SIM-DATA-PROVIDER: Initialized - Scenario: {self.scenario}, "
                   f"Pattern Injection: {self.pattern_injection} ({self.pattern_frequency*100}%)")
        if self.pattern_injection:
            logger.info(f"SIM-DATA-PROVIDER: Pattern types: {', '.join(self.pattern_types)}")

    def _load_scenario(self):
        """Load scenario-specific parameters."""
        scenarios = {
            'normal': {
                'volatility_multiplier': 1.0,
                'volume_multiplier': 1.0,
                'trend_bias': 0.0,  # No trend bias
                'spread_pct': 0.001  # 0.1% bid/ask spread
            },
            'volatile': {
                'volatility_multiplier': 3.0,
                'volume_multiplier': 2.0,
                'trend_bias': 0.0,
                'spread_pct': 0.003  # 0.3% wider spreads
            },
            'crash': {
                'volatility_multiplier': 5.0,
                'volume_multiplier': 4.0,
                'trend_bias': -0.8,  # Strong downward bias
                'spread_pct': 0.005  # 0.5% panic spreads
            },
            'rally': {
                'volatility_multiplier': 2.0,
                'volume_multiplier': 3.0,
                'trend_bias': 0.8,  # Strong upward bias
                'spread_pct': 0.002  # 0.2% excited spreads
            },
            'opening_bell': {
                'volatility_multiplier': 4.0,
                'volume_multiplier': 5.0,
                'trend_bias': 0.0,
                'spread_pct': 0.004  # 0.4% opening spreads
            }
        }

        scenario_params = scenarios.get(self.scenario, scenarios['normal'])
        self.volatility_multiplier = scenario_params['volatility_multiplier']
        self.volume_multiplier = scenario_params['volume_multiplier']
        self.trend_bias = scenario_params['trend_bias']
        self.spread_pct = scenario_params['spread_pct']

        logger.info(f"SIM-DATA-PROVIDER: Scenario '{self.scenario}' - "
                   f"Volatility: {self.volatility_multiplier}x, Volume: {self.volume_multiplier}x, "
                   f"Trend: {self.trend_bias:+.1f}")

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

    def _get_time_of_day_multiplier(self) -> Dict[str, float]:
        """Get volume/volatility multipliers based on time of day."""
        eastern_now = datetime.now(pytz.utc).astimezone(self.market_timezone)
        hour = eastern_now.hour
        minute = eastern_now.minute

        # Opening bell (9:30-10:00): High activity
        if hour == 9 and minute >= 30:
            return {'volume': 3.0, 'volatility': 2.0}
        elif hour == 10 and minute < 30:
            return {'volume': 2.0, 'volatility': 1.5}

        # Lunch lull (12:00-14:00): Low activity
        elif 12 <= hour < 14:
            return {'volume': 0.5, 'volatility': 0.7}

        # Closing hour (15:00-16:00): High activity
        elif hour == 15:
            return {'volume': 2.5, 'volatility': 1.8}

        # Normal trading
        else:
            return {'volume': 1.0, 'volatility': 1.0}

    def get_ticker_price(self, ticker: str) -> float:
        """Generate a realistic price for a ticker with trend bias and sector volatility."""
        current_time = time.time()

        # Rate limiting to prevent excessive generation
        if ticker in self.last_price_time and current_time - self.last_price_time[ticker] < 0.2:
            return self.last_price.get(ticker, 100.0)

        self.last_price_time[ticker] = current_time

        # Initialize price seed for consistent behavior
        if ticker not in self.price_seeds:
            self.price_seeds[ticker] = random.randint(1, 1000)

        # Get symbol info for sector-based volatility
        symbol_info = self.universe_loader.get_symbol_info(ticker)

        # Get or initialize price
        if ticker in self.last_price:
            base_price = self.last_price[ticker]
        else:
            # Initialize with baseline price from universe
            if symbol_info:
                base_price = symbol_info.baseline_price
            else:
                # Fallback to hash-based price
                base_price = 100 + (hash(ticker) % 100)
            self.last_price[ticker] = base_price

        # Apply scenario-based movement
        time_factor = int(current_time / 5)
        random.seed(self.price_seeds[ticker] + time_factor)

        # Calculate variance based on activity level and scenario
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        variance_map = {'low': 5, 'medium': 10, 'high': 20}
        base_variance = variance_map.get(activity_level, 10)

        # Apply scenario volatility multiplier
        variance = base_variance * self.volatility_multiplier

        # Apply sector-based volatility factor (Phase 3)
        if symbol_info:
            variance *= symbol_info.volatility_factor

        # Generate price movement with trend bias
        movement_pct = random.uniform(-variance/100, variance/100)

        # Apply trend bias
        if self.trend_bias != 0:
            movement_pct += (self.trend_bias * variance / 200)  # Add bias

        price = base_price * (1 + movement_pct)
        price = max(1.0, price)

        self.last_price[ticker] = price

        return round(price, 2)

    def _should_inject_pattern(self) -> bool:
        """Determine if a pattern should be injected in this tick."""
        if not self.pattern_injection:
            return False
        return random.random() < self.pattern_frequency

    def _inject_pattern(self, ticker: str, base_price: float) -> Optional[Dict[str, Any]]:
        """Inject a candlestick pattern into the tick data."""
        # Select random pattern from enabled types
        available_patterns = [p for p in self.pattern_types if p in PATTERNS]
        if not available_patterns:
            return None

        pattern_name = random.choice(available_patterns)
        pattern = PATTERNS[pattern_name]

        # Calculate OHLC based on pattern definition
        tick_close = base_price
        tick_open = base_price * pattern.open_pct
        tick_high = base_price * pattern.high_pct
        tick_low = base_price * pattern.low_pct

        # Ensure high/low are valid
        tick_high = max(tick_high, tick_open, tick_close)
        tick_low = min(tick_low, tick_open, tick_close)

        self.patterns_injected += 1
        self.pattern_counts[pattern_name] += 1

        if self.patterns_injected % 10 == 0:
            logger.debug(f"SIM-DATA-PROVIDER: Pattern injected #{self.patterns_injected}: {pattern_name} on {ticker}")

        return {
            'pattern_name': pattern_name,
            'tick_open': round(tick_open, 2),
            'tick_high': round(tick_high, 2),
            'tick_low': round(tick_low, 2),
            'tick_close': round(tick_close, 2)
        }

    def generate_tick_data(self, ticker: str) -> TickData:
        """Generate realistic synthetic tick data with optional pattern injection."""
        current_time = time.time()
        base_price = self.get_ticker_price(ticker)

        # Get time-of-day multipliers
        tod_multipliers = self._get_time_of_day_multiplier()

        # Check for pattern injection
        pattern_data = None
        if self._should_inject_pattern():
            pattern_data = self._inject_pattern(ticker, base_price)

        # Generate OHLC data
        if pattern_data:
            # Use pattern-injected OHLC
            tick_open = pattern_data['tick_open']
            tick_high = pattern_data['tick_high']
            tick_low = pattern_data['tick_low']
            tick_close = pattern_data['tick_close']
            current_price = tick_close
        else:
            # Generate realistic tick variations
            tick_variance = 0.002 * tod_multipliers['volatility'] * self.volatility_multiplier
            tick_high = round(base_price * (1 + random.uniform(0, tick_variance)), 2)
            tick_low = round(base_price * (1 - random.uniform(0, tick_variance)), 2)
            tick_open = round(base_price * (1 + random.uniform(-tick_variance/2, tick_variance/2)), 2)
            tick_close = base_price
            current_price = base_price

        # Generate volume with time-of-day and scenario multipliers
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        volume_map = {'low': (1000, 10000), 'medium': (10000, 100000), 'high': (100000, 500000)}
        volume_range = volume_map.get(activity_level, (10000, 100000))

        base_volume = random.randint(*volume_range)
        tick_volume = int(base_volume * tod_multipliers['volume'] * self.volume_multiplier)

        # Generate bid/ask spread
        spread = current_price * self.spread_pct
        bid = round(current_price - spread/2, 2)
        ask = round(current_price + spread/2, 2)

        # Generate VWAP (weighted toward close)
        tick_vwap = round((tick_high + tick_low + tick_close * 2) / 4, 2)

        # Create TickData
        tick = TickData(
            ticker=ticker,
            price=current_price,
            volume=tick_volume,
            timestamp=current_time,
            source='simulated',
            event_type='A',
            market_status=self.get_market_status(),
            bid=bid,
            ask=ask,
            tick_open=tick_open,
            tick_high=tick_high,
            tick_low=tick_low,
            tick_close=tick_close,
            tick_volume=tick_volume,
            tick_vwap=tick_vwap,
            vwap=tick_vwap,
            tick_start_timestamp=current_time - 1,
            tick_end_timestamp=current_time
        )

        self.ticks_generated += 1

        # Periodic statistics logging
        if self.ticks_generated % 100 == 0:
            pattern_pct = (self.patterns_injected / self.ticks_generated * 100) if self.ticks_generated > 0 else 0
            logger.info(f"SIM-DATA-PROVIDER: Generated {self.ticks_generated} ticks, "
                       f"{self.patterns_injected} patterns ({pattern_pct:.1f}%)")

        return tick

    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive ticker details with sector info from universe."""
        current_price = self.get_ticker_price(ticker)

        # Get symbol info for sector
        symbol_info = self.universe_loader.get_symbol_info(ticker)
        sector = symbol_info.sector if symbol_info else "Unknown"

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
            "sector": sector,
            "last_updated": datetime.now().isoformat()
        }

    def get_multiple_tickers(self, tickers: list) -> Dict[str, Dict[str, Any]]:
        """Get details for multiple tickers."""
        return {ticker: self.get_ticker_details(ticker) for ticker in tickers}

    def is_available(self) -> bool:
        """Synthetic data is always available."""
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get provider statistics (debugging/monitoring)."""
        return {
            'ticks_generated': self.ticks_generated,
            'patterns_injected': self.patterns_injected,
            'pattern_injection_rate': (self.patterns_injected / self.ticks_generated * 100) if self.ticks_generated > 0 else 0,
            'pattern_counts': dict(self.pattern_counts),
            'scenario': self.scenario,
            'volatility_multiplier': self.volatility_multiplier,
            'volume_multiplier': self.volume_multiplier,
            'trend_bias': self.trend_bias
        }
