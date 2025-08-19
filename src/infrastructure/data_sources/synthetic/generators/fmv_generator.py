"""
Fair Market Value (FMV) Generator

Generates synthetic fair market value updates that correlate with current price 
movements. Simulates Polygon FMV events for comprehensive testing without requiring
Business plan access.
"""

import random
import time
from datetime import datetime
from typing import Dict, Any, Optional
from src.infrastructure.data_sources.synthetic.types import DataFrequency
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'fmv_generator')


class FMVGenerator:
    """Generates Fair Market Value updates with realistic correlation to price movements."""
    
    def __init__(self, config: Dict[str, Any], provider):
        """
        Initialize the FMV generator.
        
        Args:
            config: Configuration dictionary
            provider: Reference to parent SimulatedDataProvider
        """
        self.config = config
        self.provider = provider
        self.generation_count = 0
        
        # FMV specific configuration
        self.update_interval = config.get('SYNTHETIC_FMV_UPDATE_INTERVAL', 30)  # seconds
        self.correlation_strength = config.get('SYNTHETIC_FMV_CORRELATION', 0.85)  # 0-1
        self.value_variance = config.get('SYNTHETIC_FMV_VARIANCE', 0.002)  # 0.2%
        self.premium_discount_range = config.get('SYNTHETIC_FMV_PREMIUM_RANGE', 0.01)  # 1%
        
        # Enhanced correlation parameters
        self.momentum_decay = config.get('SYNTHETIC_FMV_MOMENTUM_DECAY', 0.7)  # FMV momentum persistence
        self.lag_factor = config.get('SYNTHETIC_FMV_LAG_FACTOR', 0.3)  # FMV follows with lag
        self.volatility_dampening = config.get('SYNTHETIC_FMV_VOLATILITY_DAMPENING', 0.6)  # FMV less volatile
        
        # Market regime awareness
        self.trending_correlation = config.get('SYNTHETIC_FMV_TRENDING_CORRELATION', 0.90)  # Higher correlation in trends
        self.sideways_correlation = config.get('SYNTHETIC_FMV_SIDEWAYS_CORRELATION', 0.75)  # Lower correlation sideways
        self.volatile_correlation = config.get('SYNTHETIC_FMV_VOLATILE_CORRELATION', 0.65)  # Even lower in volatility
        
        # Track FMV history and timing
        self._last_fmv_update: Dict[str, float] = {}
        self._fmv_values: Dict[str, float] = {}
        self._fmv_trends: Dict[str, float] = {}  # Track FMV momentum
        
        # Enhanced correlation tracking
        self._price_history: Dict[str, List[float]] = {}  # Recent price movements for correlation
        self._fmv_history: Dict[str, List[float]] = {}   # Recent FMV movements
        self._market_regime: Dict[str, str] = {}         # Current market regime per ticker
        self._correlation_strength_adjusted: Dict[str, float] = {}  # Dynamic correlation per ticker
        
        logger.info("FMV-GEN: FMVGenerator initialized for fair market value generation")
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Fair Market Value update.
        
        Args:
            ticker: Stock ticker symbol
            config: Generation configuration
            
        Returns:
            Dict: FMV update data in Polygon FMV event format
        """
        current_time = time.time()
        
        # Check if enough time has passed for FMV update (typically less frequent than ticks)
        if ticker in self._last_fmv_update:
            time_since_last = current_time - self._last_fmv_update[ticker]
            if time_since_last < self.update_interval:
                logger.debug(f"FMV-GEN: Skipping FMV update for {ticker}, too recent")
                return None
        
        self._last_fmv_update[ticker] = current_time
        
        # Generate FMV based on current market price with realistic correlation
        fmv_data = self._generate_fmv_value(ticker, current_time)
        
        # Create Polygon FMV-style event structure
        fmv_event = self._create_fmv_event_structure(ticker, fmv_data, current_time)
        
        self.generation_count += 1
        
        # Log statistics
        if self.generation_count % 5 == 0:
            logger.debug(
                f"FMV-GEN: Generated {self.generation_count} FMV updates. "
                f"Latest: {ticker} FMV=${fmv_data['fair_value']:.2f} "
                f"vs Market=${fmv_data['market_price']:.2f} "
                f"({fmv_data['premium_discount']:+.2%})"
            )
        
        return fmv_event
    
    def _generate_fmv_value(self, ticker: str, timestamp: float) -> Dict[str, Any]:
        """
        Generate realistic FMV that correlates with but differs from market price.
        
        FMV typically:
        - Follows market price trends but with lag
        - Has lower volatility than market price
        - May trade at premium/discount to market price
        - Updates less frequently than market price
        """
        current_market_price = self.provider.get_ticker_price(ticker)
        
        # Initialize FMV if first time for this ticker
        if ticker not in self._fmv_values:
            # Start FMV close to market price with small random premium/discount
            initial_premium = random.uniform(-self.premium_discount_range/2, self.premium_discount_range/2)
            self._fmv_values[ticker] = current_market_price * (1 + initial_premium)
            self._fmv_trends[ticker] = 0.0
            self._price_history[ticker] = [current_market_price]
            self._fmv_history[ticker] = [self._fmv_values[ticker]]
            self._market_regime[ticker] = 'sideways'
            self._correlation_strength_adjusted[ticker] = self.correlation_strength
        
        previous_fmv = self._fmv_values[ticker]
        
        # Update price history and detect market regime
        self._update_price_history(ticker, current_market_price)
        market_regime = self._detect_market_regime(ticker)
        
        # Calculate FMV movement with enhanced correlation logic
        if ticker in self.provider.last_price:
            previous_market_price = self.provider.last_price[ticker]
            market_change = (current_market_price - previous_market_price) / previous_market_price if previous_market_price > 0 else 0.0
        else:
            market_change = 0.0
        
        # Adjust correlation based on market regime
        adjusted_correlation = self._get_regime_adjusted_correlation(ticker, market_regime)
        
        # FMV follows market movement but with dampening, lag, and regime awareness
        correlated_change = market_change * adjusted_correlation * self.volatility_dampening
        
        # Add FMV-specific trend momentum with enhanced persistence
        trend_change = self._fmv_trends[ticker] * self.momentum_decay
        
        # Add lag component (FMV slower to react)
        lag_component = self._calculate_lag_component(ticker, market_change)
        
        # Add regime-aware variance
        regime_variance = self._get_regime_adjusted_variance(market_regime)
        random_change = random.uniform(-regime_variance, regime_variance)
        
        # Combine all change components with weights
        total_fmv_change = (
            correlated_change * 0.6 +      # Primary correlation component
            trend_change * 0.2 +           # FMV momentum
            lag_component * 0.15 +         # Lag adjustment
            random_change * 0.05           # Random noise
        )
        
        # Apply change to FMV
        new_fmv = previous_fmv * (1 + total_fmv_change)
        new_fmv = max(0.01, new_fmv)  # Ensure positive
        
        # Update trend momentum with enhanced tracking
        self._fmv_trends[ticker] = total_fmv_change * self.momentum_decay
        
        # Store new FMV and update history
        self._fmv_values[ticker] = new_fmv
        self._update_fmv_history(ticker, new_fmv)
        
        # Store current market regime
        self._market_regime[ticker] = market_regime
        
        # Calculate premium/discount relative to market
        premium_discount = (new_fmv - current_market_price) / current_market_price
        
        # Add market session effects
        session_adjustment = self._apply_session_effects(ticker, timestamp, new_fmv, current_market_price)
        adjusted_fmv = new_fmv * (1 + session_adjustment)
        
        return {
            'fair_value': adjusted_fmv,
            'market_price': current_market_price,
            'premium_discount': (adjusted_fmv - current_market_price) / current_market_price,
            'confidence': self._calculate_confidence_score(ticker, premium_discount),
            'timestamp': timestamp,
            'session_adjustment': session_adjustment
        }
    
    def _apply_session_effects(self, ticker: str, timestamp: float, fmv: float, market_price: float) -> float:
        """
        Apply market session effects to FMV calculation.
        
        FMV typically:
        - More stable during regular hours
        - May have wider spreads during extended hours
        - Less reliable when market is closed
        """
        market_status = self.provider.get_market_status()
        
        if market_status == 'REGULAR':
            # Regular hours - FMV is most reliable
            return random.uniform(-0.0005, 0.0005)  # Minimal adjustment
        elif market_status == 'PRE' or market_status == 'AFTER':
            # Extended hours - wider FMV spreads
            return random.uniform(-0.002, 0.002)  # Larger adjustments
        else:
            # Market closed - FMV becomes stale, may drift
            return random.uniform(-0.001, 0.001)
    
    def _calculate_confidence_score(self, ticker: str, premium_discount: float) -> float:
        """
        Calculate confidence score for FMV (0-1 scale).
        
        Higher confidence when:
        - Premium/discount is within normal ranges
        - Market is in regular session
        - Recent price movements are moderate
        """
        base_confidence = 0.85
        
        # Adjust based on premium/discount magnitude
        premium_penalty = min(0.3, abs(premium_discount) * 10)
        confidence = base_confidence - premium_penalty
        
        # Adjust based on market session
        market_status = self.provider.get_market_status()
        if market_status == 'REGULAR':
            session_bonus = 0.1
        elif market_status in ['PRE', 'AFTER']:
            session_bonus = 0.0
        else:
            session_bonus = -0.15  # Lower confidence when market closed
        
        confidence += session_bonus
        
        # Add some randomness for realism
        confidence += random.uniform(-0.05, 0.05)
        
        return max(0.1, min(1.0, confidence))
    
    def _update_price_history(self, ticker: str, price: float):
        """Update price history for correlation analysis."""
        if ticker not in self._price_history:
            self._price_history[ticker] = []
        
        self._price_history[ticker].append(price)
        
        # Keep only last 20 price points (10 minutes of updates at 30s intervals)
        if len(self._price_history[ticker]) > 20:
            self._price_history[ticker] = self._price_history[ticker][-20:]
    
    def _update_fmv_history(self, ticker: str, fmv: float):
        """Update FMV history for correlation analysis."""
        if ticker not in self._fmv_history:
            self._fmv_history[ticker] = []
        
        self._fmv_history[ticker].append(fmv)
        
        # Keep only last 20 FMV points
        if len(self._fmv_history[ticker]) > 20:
            self._fmv_history[ticker] = self._fmv_history[ticker][-20:]
    
    def _detect_market_regime(self, ticker: str) -> str:
        """Detect current market regime based on recent price movements."""
        if ticker not in self._price_history or len(self._price_history[ticker]) < 5:
            return 'sideways'  # Default regime
        
        prices = self._price_history[ticker][-10:]  # Last 10 price points
        if len(prices) < 3:
            return 'sideways'
        
        # Calculate price changes
        changes = []
        for i in range(1, len(prices)):
            change = (prices[i] - prices[i-1]) / prices[i-1] if prices[i-1] > 0 else 0
            changes.append(change)
        
        if not changes:
            return 'sideways'
        
        # Calculate trend strength and volatility
        avg_change = sum(changes) / len(changes)
        volatility = sum(abs(change - avg_change) for change in changes) / len(changes)
        
        # Determine regime
        if volatility > 0.005:  # High volatility (> 0.5%)
            return 'volatile'
        elif abs(avg_change) > 0.002:  # Strong trend (> 0.2%)
            return 'trending'
        else:
            return 'sideways'
    
    def _get_regime_adjusted_correlation(self, ticker: str, regime: str) -> float:
        """Get correlation strength adjusted for market regime."""
        regime_correlations = {
            'trending': self.trending_correlation,
            'sideways': self.sideways_correlation,
            'volatile': self.volatile_correlation
        }
        
        base_correlation = regime_correlations.get(regime, self.correlation_strength)
        
        # Store adjusted correlation for reporting
        self._correlation_strength_adjusted[ticker] = base_correlation
        
        return base_correlation
    
    def _get_regime_adjusted_variance(self, regime: str) -> float:
        """Get variance adjusted for market regime."""
        regime_multipliers = {
            'trending': 0.8,    # Lower variance in trending markets
            'sideways': 1.0,    # Normal variance
            'volatile': 1.4     # Higher variance in volatile markets
        }
        
        multiplier = regime_multipliers.get(regime, 1.0)
        return self.value_variance * multiplier
    
    def _calculate_lag_component(self, ticker: str, market_change: float) -> float:
        """Calculate lag component for FMV response to price changes."""
        if abs(market_change) < 0.001:  # Very small price changes
            return 0.0
        
        # FMV lags behind market moves, especially large ones
        lag_strength = min(0.8, abs(market_change) * 100)  # Stronger lag for bigger moves
        lag_direction = 1.0 if market_change > 0 else -1.0
        
        # Lag component is proportional to price change but dampened
        return market_change * self.lag_factor * (1 - lag_strength) * lag_direction
    
    def _create_fmv_event_structure(self, ticker: str, fmv_data: Dict[str, Any], timestamp: float) -> Dict[str, Any]:
        """
        Create Polygon FMV event structure for consistency with real data.
        
        Note: This simulates the structure that would come from Polygon's Business plan
        FMV data feed.
        """
        timestamp_ms = int(timestamp * 1000)
        
        return {
            'ev': 'FMV',  # Event type: Fair Market Value
            'sym': ticker,  # Symbol
            'fmv': round(fmv_data['fair_value'], 4),  # Fair Market Value
            'mp': round(fmv_data['market_price'], 4),  # Market Price
            'pd': round(fmv_data['premium_discount'], 6),  # Premium/Discount
            'conf': round(fmv_data['confidence'], 4),  # Confidence Score
            't': timestamp_ms,  # Timestamp
            'source': 'simulated_fmv',
            'market_status': self.provider.get_market_status(),
            
            # Additional synthetic fields for testing
            'session_adj': round(fmv_data.get('session_adjustment', 0.0), 6),
            'trend_momentum': round(self._fmv_trends.get(ticker, 0.0), 6),
            'update_interval': self.update_interval
        }
    
    def get_current_fmv(self, ticker: str) -> Optional[float]:
        """
        Get the current FMV for a ticker without generating new data.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Optional[float]: Current FMV value if available
        """
        return self._fmv_values.get(ticker)
    
    def reset_fmv_for_ticker(self, ticker: str):
        """
        Reset FMV state for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol to reset
        """
        self._fmv_values.pop(ticker, None)
        self._fmv_trends.pop(ticker, None)
        self._last_fmv_update.pop(ticker, None)
        
        logger.debug(f"FMV-GEN: Reset FMV state for {ticker}")
    
    def supports_frequency(self, frequency: DataFrequency) -> bool:
        """Check if generator supports the given frequency."""
        return frequency == DataFrequency.FAIR_VALUE
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get generation statistics for this generator."""
        return {
            'type': 'fair_market_value',
            'total_generated': self.generation_count,
            'tickers_tracked': len(self._fmv_values),
            'config': {
                'update_interval': self.update_interval,
                'correlation_strength': self.correlation_strength,
                'value_variance': self.value_variance,
                'premium_discount_range': self.premium_discount_range
            },
            'current_fmv_count': len(self._fmv_values),
            'enhanced_correlation': {
                'momentum_decay': self.momentum_decay,
                'lag_factor': self.lag_factor,
                'volatility_dampening': self.volatility_dampening,
                'regime_correlations': {
                    'trending': self.trending_correlation,
                    'sideways': self.sideways_correlation,
                    'volatile': self.volatile_correlation
                }
            }
        }
    
    def get_correlation_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get detailed correlation analysis for a specific ticker."""
        if ticker not in self._fmv_values:
            return {'error': 'No FMV data available for ticker'}
        
        analysis = {
            'ticker': ticker,
            'current_fmv': self._fmv_values[ticker],
            'current_market_price': self.provider.get_ticker_price(ticker) if hasattr(self.provider, 'get_ticker_price') else None,
            'market_regime': self._market_regime.get(ticker, 'unknown'),
            'adjusted_correlation': self._correlation_strength_adjusted.get(ticker, self.correlation_strength),
            'fmv_momentum': self._fmv_trends.get(ticker, 0.0),
            'price_history_length': len(self._price_history.get(ticker, [])),
            'fmv_history_length': len(self._fmv_history.get(ticker, []))
        }
        
        # Calculate realized correlation if we have enough history
        if (ticker in self._price_history and ticker in self._fmv_history and 
            len(self._price_history[ticker]) >= 5 and len(self._fmv_history[ticker]) >= 5):
            
            price_changes = []
            fmv_changes = []
            
            prices = self._price_history[ticker][-10:]
            fmvs = self._fmv_history[ticker][-10:]
            
            min_len = min(len(prices), len(fmvs))
            
            for i in range(1, min_len):
                if prices[i-1] > 0 and fmvs[i-1] > 0:
                    price_change = (prices[i] - prices[i-1]) / prices[i-1]
                    fmv_change = (fmvs[i] - fmvs[i-1]) / fmvs[i-1]
                    price_changes.append(price_change)
                    fmv_changes.append(fmv_change)
            
            if len(price_changes) >= 3:
                # Simple correlation calculation
                price_mean = sum(price_changes) / len(price_changes)
                fmv_mean = sum(fmv_changes) / len(fmv_changes)
                
                numerator = sum((p - price_mean) * (f - fmv_mean) for p, f in zip(price_changes, fmv_changes))
                price_var = sum((p - price_mean) ** 2 for p in price_changes)
                fmv_var = sum((f - fmv_mean) ** 2 for f in fmv_changes)
                
                if price_var > 0 and fmv_var > 0:
                    correlation = numerator / (price_var * fmv_var) ** 0.5
                    analysis['realized_correlation'] = round(correlation, 4)
                else:
                    analysis['realized_correlation'] = 0.0
            else:
                analysis['realized_correlation'] = None
        else:
            analysis['realized_correlation'] = None
        
        return analysis