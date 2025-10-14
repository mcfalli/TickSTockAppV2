"""Universe loader for synthetic data provider - Sprint 41 Phase 3.

Loads symbol data from cache_entries table via CacheControl,
providing realistic baseline prices and sector information.
"""
import logging
import random
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Information about a symbol for synthetic data generation."""
    ticker: str
    sector: str
    baseline_price: float
    volatility_factor: float  # Multiplier for sector-based volatility


# Sector-based characteristics
SECTOR_CHARACTERISTICS = {
    'Technology': {
        'volatility_factor': 1.5,
        'typical_price_range': (50, 300)
    },
    'Healthcare': {
        'volatility_factor': 1.2,
        'typical_price_range': (30, 200)
    },
    'Financial': {
        'volatility_factor': 1.0,
        'typical_price_range': (20, 150)
    },
    'Consumer': {
        'volatility_factor': 0.9,
        'typical_price_range': (25, 180)
    },
    'Industrial': {
        'volatility_factor': 0.8,
        'typical_price_range': (40, 160)
    },
    'Energy': {
        'volatility_factor': 1.3,
        'typical_price_range': (30, 120)
    },
    'Utilities': {
        'volatility_factor': 0.6,
        'typical_price_range': (50, 100)
    },
    'Materials': {
        'volatility_factor': 1.1,
        'typical_price_range': (35, 140)
    },
    'Communication': {
        'volatility_factor': 1.2,
        'typical_price_range': (40, 200)
    },
    'RealEstate': {
        'volatility_factor': 0.7,
        'typical_price_range': (30, 120)
    },
    'Unknown': {
        'volatility_factor': 1.0,
        'typical_price_range': (50, 150)
    }
}


class UniverseLoader:
    """Loads symbol universe for synthetic data generation."""

    def __init__(self, universe_key: str = 'market_leaders:top_500'):
        self.universe_key = universe_key
        self.symbols: dict[str, SymbolInfo] = {}
        self.tickers: list[str] = []
        self._load_universe()

    def _load_universe(self):
        """Load universe from cache or use fallback."""
        try:
            from src.infrastructure.cache.cache_control import CacheControl

            # Initialize cache
            cache = CacheControl()
            if not hasattr(cache, '_initialized') or not cache._initialized:
                cache.initialize()

            # Try to load from cache
            tickers = cache.get_universe_tickers(self.universe_key)

            if tickers and len(tickers) > 0:
                logger.info(f"UNIVERSE-LOADER: Loaded {len(tickers)} symbols from '{self.universe_key}'")
                self._populate_symbols_from_tickers(tickers)
            else:
                logger.warning(f"UNIVERSE-LOADER: No symbols found for '{self.universe_key}', using fallback")
                self._use_fallback_universe()

        except Exception as e:
            logger.error(f"UNIVERSE-LOADER: Error loading universe: {e}")
            self._use_fallback_universe()

    def _populate_symbols_from_tickers(self, tickers: list[str]):
        """Populate symbol info from ticker list."""
        # Sector assignments (realistic distribution)
        sectors = [
            ('Technology', 0.25),
            ('Healthcare', 0.15),
            ('Financial', 0.15),
            ('Consumer', 0.15),
            ('Industrial', 0.10),
            ('Energy', 0.05),
            ('Utilities', 0.05),
            ('Materials', 0.05),
            ('Communication', 0.03),
            ('RealEstate', 0.02)
        ]

        for ticker in tickers:
            # Assign sector based on distribution
            sector = self._assign_sector(ticker, sectors)

            # Generate baseline price based on ticker hash and sector
            sector_chars = SECTOR_CHARACTERISTICS.get(sector, SECTOR_CHARACTERISTICS['Unknown'])
            price_min, price_max = sector_chars['typical_price_range']

            # Use ticker hash for consistent pricing
            ticker_hash = abs(hash(ticker))
            price = price_min + (ticker_hash % (price_max - price_min))

            symbol_info = SymbolInfo(
                ticker=ticker,
                sector=sector,
                baseline_price=float(price),
                volatility_factor=sector_chars['volatility_factor']
            )

            self.symbols[ticker] = symbol_info

        self.tickers = list(self.symbols.keys())
        logger.info(f"UNIVERSE-LOADER: Initialized {len(self.symbols)} symbols with sector data")

    def _assign_sector(self, ticker: str, sectors: list[tuple]) -> str:
        """Assign sector to ticker based on distribution."""
        # Use ticker hash for consistent sector assignment
        ticker_hash = abs(hash(ticker)) / (2**32)  # Normalize to 0-1

        cumulative = 0.0
        for sector, weight in sectors:
            cumulative += weight
            if ticker_hash < cumulative:
                return sector

        return 'Unknown'

    def _use_fallback_universe(self):
        """Use fallback universe when cache loading fails."""
        fallback_symbols = {
            # Technology
            'AAPL': ('Technology', 175.0),
            'MSFT': ('Technology', 380.0),
            'GOOGL': ('Technology', 140.0),
            'NVDA': ('Technology', 500.0),
            'META': ('Technology', 320.0),
            'TSLA': ('Technology', 250.0),
            'AMD': ('Technology', 140.0),
            'INTC': ('Technology', 45.0),

            # Healthcare
            'UNH': ('Healthcare', 520.0),
            'JNJ': ('Healthcare', 160.0),
            'PFE': ('Healthcare', 30.0),
            'ABBV': ('Healthcare', 150.0),

            # Financial
            'JPM': ('Financial', 150.0),
            'BAC': ('Financial', 35.0),
            'WFC': ('Financial', 45.0),
            'GS': ('Financial', 380.0),

            # Consumer
            'AMZN': ('Consumer', 140.0),
            'WMT': ('Consumer', 155.0),
            'HD': ('Consumer', 340.0),
            'NKE': ('Consumer', 105.0),

            # Communication
            'DIS': ('Communication', 95.0),
            'NFLX': ('Communication', 450.0),
            'CMCSA': ('Communication', 44.0),

            # Energy
            'XOM': ('Energy', 110.0),
            'CVX': ('Energy', 155.0),

            # ETFs
            'SPY': ('Financial', 450.0),
            'QQQ': ('Technology', 380.0),
            'IWM': ('Financial', 200.0),
            'GLD': ('Materials', 190.0),
        }

        for ticker, (sector, price) in fallback_symbols.items():
            sector_chars = SECTOR_CHARACTERISTICS.get(sector, SECTOR_CHARACTERISTICS['Unknown'])
            symbol_info = SymbolInfo(
                ticker=ticker,
                sector=sector,
                baseline_price=price,
                volatility_factor=sector_chars['volatility_factor']
            )
            self.symbols[ticker] = symbol_info

        self.tickers = list(self.symbols.keys())
        logger.info(f"UNIVERSE-LOADER: Using fallback universe with {len(self.symbols)} symbols")

    def get_symbol_info(self, ticker: str) -> SymbolInfo | None:
        """Get symbol information."""
        return self.symbols.get(ticker.upper())

    def get_random_symbols(self, count: int) -> list[str]:
        """Get random symbols from universe."""
        if count >= len(self.tickers):
            return self.tickers.copy()
        return random.sample(self.tickers, count)

    def get_all_tickers(self) -> list[str]:
        """Get all tickers in universe."""
        return self.tickers.copy()

    def get_sectors(self) -> set[str]:
        """Get all unique sectors in universe."""
        return {info.sector for info in self.symbols.values()}

    def get_symbols_by_sector(self, sector: str) -> list[str]:
        """Get all symbols in a specific sector."""
        return [ticker for ticker, info in self.symbols.items() if info.sector == sector]
