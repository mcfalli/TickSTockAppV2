import random
import time
import logging
from datetime import datetime
import pytz
from typing import Dict, List, Any
import os
from src.infrastructure.data_sources.synthetic.synthetic_data_loader import SyntheticDataLoader
from src.infrastructure.cache.cache_control import CacheControl

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = logging.getLogger(__name__)

class SyntheticDataGenerator:
    def __init__(self, config):
        logger.debug("Synthetic Data Generator initialization started, loading universe to process.")
        
        # Pull universe from config (fallback to 'market_leaders:top_50')
        universe = config.get('SIMULATOR_UNIVERSE', 'market_leaders:top_50')
        logger.debug(f"SIM-DATA-GEN: Using synthetic universe: {universe}")
        
        self._event_log_counter = 0  # Counter for logging frequency
        self._total_ticks_generated = 0
        
        # Initialize CacheControl
        self.cache_control = CacheControl()
        self.cache_control.initialize()
        
        # Initialize the data loader with universe support
        self.data_loader = SyntheticDataLoader(
            universe=universe,
            cache_control=self.cache_control
        )
        
        # Get tickers from the selected universe
        self.tickers = self.data_loader.get_all_tickers()
        
        if self.tickers:
            universe_info = self.data_loader.get_universe_info()
            logger.debug(f"SIM-DATA-GEN: SyntheticDataGenerator: Using {len(self.tickers)} tickers from {universe_info['universe']} universe")
            logger.debug(f"SIM-DATA-GEN: Universe sectors: {', '.join(universe_info['sectors'][:5])}{'...' if len(universe_info['sectors']) > 5 else ''}")
        else:
            # Emergency fallback if load fails
            self.tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
            logger.warning("SIM-DATA-GEN: Universe loading failed, using emergency fallback list")
        
        # TRACE: Generator initialization (moved after tickers load)
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='SyntheticDataGenerator',
                action='initialized',
                data={
                    'input_count': 0,
                    'output_count': 0,
                    'duration_ms': 0,
                    'details': {
                        'universe': universe,
                        'ticker_count': len(self.tickers),
                        'load_method': 'cache'
                    }
                }
            )
        
        # Initialize with data from loader
        self.stock_prices = {}
        self.trend_directions = {}
        self.trend_counters = {}
        
        for ticker in self.tickers:
            baseline = self.data_loader.get_ticker_baseline(ticker)
            self.stock_prices[ticker] = baseline['baseline_price']
            # Initialize trend direction randomly
            self.trend_directions[ticker] = random.choice([1, -1])
            self.trend_counters[ticker] = 0
        
        logger.debug(f"SIM-DATA-GEN: SyntheticDataGenerator initialized with {len(self.tickers)} tickers, price range: ${min(self.stock_prices.values()):.2f} - ${max(self.stock_prices.values()):.2f}")
        logger.debug(f"SIM-DATA-GEN: Current universe: {universe} | Sample tickers: {', '.join(self.tickers[:10])}")


    def generate_events(self, count=1, market_status="REGULAR", activity_level="medium"):
        events = {'highs': [], 'lows': []}
        eastern_tz = pytz.timezone('US/Eastern')
        current_time = datetime.now(eastern_tz)
        
        # Determine realistic activity based on market conditions
        if activity_level == "low":
            active_pct = 0.05  # 5% of tickers active per second
            variance = 0.05
        elif activity_level == "medium":
            active_pct = 0.10  # 10% of tickers active per second
            variance = 0.1
        elif activity_level == "high":
            active_pct = 0.20  # 20% of tickers active per second
            variance = 0.15
        else:  # opening bell
            active_pct = 0.40  # 40% of tickers active in opening minute
            variance = 0.2
        
        # Calculate how many tickers should have activity
        active_tickers_count = max(1, int(len(self.tickers) * active_pct))
        
        # Select random tickers for activity
        active_tickers = random.sample(self.tickers, min(active_tickers_count, len(self.tickers)))
        
        # Always include TSLA and NVDA for debugging consistency (if they exist in our universe)
        special_tickers = ["TSLA", "NVDA"]
        for special_ticker in special_tickers:
            if special_ticker in self.tickers and special_ticker not in active_tickers:
                active_tickers.append(special_ticker)
        
        # Generate one event for each active ticker
        for ticker in active_tickers:

            current_price = self.stock_prices.get(ticker)
            is_high = random.choice([True, False])

            # TRACE
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='SyntheticDataGenerator',
                    action='event_generated',
                    data={
                        'input_count': 1,
                        'output_count': 1,
                        'duration_ms': 0,
                        'details': {
                            'event_type': 'high' if is_high else 'low',
                            'current_price': current_price,
                            'activity_level': activity_level
                        }
                    }
                )

            
            if is_high:
                step = random.uniform(0, variance) * current_price
                new_price = max(1.0, current_price + step)
                event = self._create_tick_data(ticker, new_price, market_status, current_time, True)
                events['highs'].append(event)
            else:
                step = -random.uniform(0, variance) * current_price
                new_price = max(1.0, current_price + step)
                event = self._create_tick_data(ticker, new_price, market_status, current_time, False)
                events['lows'].append(event)
            
            # Update stored price
            self.stock_prices[ticker] = new_price
        
        self._event_log_counter += 1
        
        # TRACE 
        total_events = len(events['highs']) + len(events['lows'])
        if tracer.should_trace('SYSTEM') and total_events > 0:
            tracer.trace(
                ticker='SYSTEM',
                component='SyntheticDataGenerator',
                action='batch_complete',
                data={
                    'input_count': len(active_tickers),
                    'output_count': total_events,
                    'duration_ms': 0,  # Could track actual time if needed
                    'details': {
                        'highs': len(events['highs']),
                        'lows': len(events['lows']),
                        'activity_level': activity_level
                    }
                }
            )
        
        
        if self._event_log_counter % 20 == 0:
            logger.debug(f"SIM-DATA-GEN: Sythetic Data Gen every 20 gens:Total {self._event_log_counter} Generated {len(events['highs'])} highs, {len(events['lows'])} lows for activity_level={activity_level}")
        return events

    def _generate_event_for_ticker(self, ticker, is_up, events, market_status, current_time, volatility):
        """Helper to generate a single event for a specific ticker"""
        baseline = self.data_loader.get_ticker_baseline(ticker)
        current_price = self.stock_prices.get(ticker, baseline['baseline_price'])
        
        # Apply trend and volatility
        if is_up:
            step = random.uniform(0, volatility) * current_price
            new_price = max(1.0, current_price + step)
            events['highs'].append(self._create_tick_data(ticker, new_price, market_status, current_time, step > 0))
        else:
            step = -random.uniform(0, volatility) * current_price
            new_price = max(1.0, current_price + step)
            events['lows'].append(self._create_tick_data(ticker, new_price, market_status, current_time, step > 0))
        
        # Update stored price
        self.stock_prices[ticker] = new_price
        
        return events

    def _create_tick_data(self, ticker, price, market_status, current_time, is_up):
            """Create a TickData object for the given parameters with tracing"""
            from src.core.domain.market.tick import TickData
            
            baseline = self.data_loader.get_ticker_baseline(ticker)
            
            # Use the new from_synthetic factory method
            tick = TickData.from_synthetic(
                ticker=ticker,
                price=price,
                baseline=baseline,
                market_status=market_status,
                current_time=current_time,
                is_up=is_up
            )
            
            self._total_ticks_generated += 1
            
            # TRACE: Tick created
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='SyntheticDataGenerator',
                    action='tick_created',
                    data={
                        'input_count': 1,
                        'output_count': 1,
                        'duration_ms': 0,
                        'details': {
                            'tick_number': self._total_ticks_generated,
                            'price': price,
                            'market_status': market_status,
                            'is_up': is_up,
                            'sector': baseline.get('sector')
                        }
                    }
                )                
            
            # Log first few ticks
            #if self._total_ticks_generated % 50 == 0:
            #    logger.info(f"🎯 SYNTHETIC-GEN: Every 50 Created tick #{self._total_ticks_generated}: {ticker} @ ${price} is_up={is_up}")
            
            return tick
 
    def get_universe_info(self) -> Dict[str, Any]:
        """Get information about the current synthetic data universe."""
        if hasattr(self.data_loader, 'get_universe_info'):
            return self.data_loader.get_universe_info()
        else:
            return {
                'method': 'legacy',
                'ticker_count': len(self.tickers),
                'universe': 'CSV or Config'
            }
    '''
    def switch_universe(self, universe: str) -> bool:
        """Switch to a different universe for synthetic data generation."""
        if not self.cache_control:
            logging.warning("Cannot switch universe - no CacheControl available")
            return False
            
        try:
            # Create new data loader with different universe
            new_data_loader = SyntheticDataLoader(
                universe=universe,
                cache_control=self.cache_control
            )
            
            new_tickers = new_data_loader.get_all_tickers()
            
            if not new_tickers:
                logging.warning(f"No tickers found in universe {universe}")
                return False
            
            # Switch to new universe
            self.data_loader = new_data_loader
            self.tickers = new_tickers
            
            # Reinitialize price tracking
            self.stock_prices = {}
            self.trend_directions = {}
            self.trend_counters = {}
            
            for ticker in self.tickers:
                baseline = self.data_loader.get_ticker_baseline(ticker)
                self.stock_prices[ticker] = baseline['baseline_price']
                self.trend_directions[ticker] = random.choice([1, -1])
                self.trend_counters[ticker] = 0
            
            universe_info = self.data_loader.get_universe_info()
            logger.debug(f"SIM-DATA-GEN: Switched to {universe} universe with {len(self.tickers)} tickers")
            
            return True
            
        except Exception as e:
            logger.error(f"SIM-DATA-GEN: Failed to switch to universe {universe}: {e}")
            return False

    '''