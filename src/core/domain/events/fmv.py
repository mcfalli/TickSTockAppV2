"""
Fair Market Value Event Model - Sprint 101
Handles Polygon FMV (Fair Market Value) events with proprietary pricing data.
"""

import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from src.core.domain.events.base import BaseEvent


@dataclass
class FairMarketValueEvent(BaseEvent):
    """
    Fair Market Value event containing Polygon's proprietary FMV pricing.
    Maps to Polygon's FMV event structure (Business plan required).
    
    Based on Polygon FMV event schema:
    - ev: "FMV"
    - fmv: Fair market value price
    - sym: ticker symbol
    - t: nanosecond timestamp
    
    FMV provides algorithmically derived real-time estimates of security
    fair market prices for pricing strategies, algorithmic modeling,
    risk assessment, and investor decision-making.
    """
    
    # Fair Market Value specific fields
    fmv_price: Optional[float] = None           # 'fmv' - Fair market value price
    fmv_timestamp_ns: Optional[int] = None      # 't' - Original nanosecond timestamp
    
    # Pricing analysis fields
    fmv_vs_market_price: Optional[float] = None    # Difference between FMV and current market price
    fmv_vs_market_pct: Optional[float] = None      # Percentage difference
    fmv_confidence: Optional[str] = None           # Confidence level (if available)
    
    # Market context
    market_price: Optional[float] = None           # Current market price for comparison
    market_price_source: str = 'unknown'          # Source of market price
    
    # Valuation indicators
    is_undervalued: Optional[bool] = None          # FMV > market price
    is_overvalued: Optional[bool] = None           # FMV < market price
    valuation_magnitude: Optional[str] = None     # 'slight', 'moderate', 'significant'
    
    # Timestamp precision
    precision_level: str = 'nanosecond'           # Timestamp precision level
    
    def __post_init__(self):
        """Set type and calculate derived fields"""
        if not self.type:
            self.type = 'fair_market_value'
        
        # Use FMV price as the main price if not set
        if self.fmv_price is not None and self.price == 0:
            self.price = self.fmv_price
        
        # Calculate derived fields
        self._calculate_valuation_metrics()
        
        super().__post_init__()
    
    def _calculate_valuation_metrics(self):
        """Calculate valuation comparison metrics"""
        try:
            if self.fmv_price is not None and self.market_price is not None:
                # Calculate absolute difference
                self.fmv_vs_market_price = self.fmv_price - self.market_price
                
                # Calculate percentage difference
                if self.market_price > 0:
                    self.fmv_vs_market_pct = (self.fmv_vs_market_price / self.market_price) * 100
                
                # Determine valuation status
                if abs(self.fmv_vs_market_pct) < 1.0:  # Less than 1% difference
                    self.is_undervalued = False
                    self.is_overvalued = False
                    self.valuation_magnitude = 'fair'
                elif self.fmv_price > self.market_price:
                    self.is_undervalued = True
                    self.is_overvalued = False
                    # Determine magnitude
                    if abs(self.fmv_vs_market_pct) < 3.0:
                        self.valuation_magnitude = 'slight_undervalued'
                    elif abs(self.fmv_vs_market_pct) < 10.0:
                        self.valuation_magnitude = 'moderate_undervalued'
                    else:
                        self.valuation_magnitude = 'significant_undervalued'
                else:
                    self.is_undervalued = False
                    self.is_overvalued = True
                    # Determine magnitude
                    if abs(self.fmv_vs_market_pct) < 3.0:
                        self.valuation_magnitude = 'slight_overvalued'
                    elif abs(self.fmv_vs_market_pct) < 10.0:
                        self.valuation_magnitude = 'moderate_overvalued'
                    else:
                        self.valuation_magnitude = 'significant_overvalued'
                        
        except Exception as e:
            # Don't fail initialization on calculation errors
            pass
    
    def validate(self) -> bool:
        """Validate Fair Market Value event data"""
        # Call parent validation first
        super().validate()
        
        # Validate FMV-specific fields
        if self.fmv_price is not None and self.fmv_price <= 0:
            raise ValueError(f"Invalid FMV price: {self.fmv_price}")
        
        if self.market_price is not None and self.market_price <= 0:
            raise ValueError(f"Invalid market price: {self.market_price}")
        
        if self.fmv_timestamp_ns is not None and self.fmv_timestamp_ns <= 0:
            raise ValueError(f"Invalid FMV timestamp: {self.fmv_timestamp_ns}")
        
        # Validate logical consistency
        if self.is_undervalued and self.is_overvalued:
            raise ValueError("Cannot be both undervalued and overvalued")
        
        return True
    
    def get_event_specific_data(self) -> Dict[str, Any]:
        """Get Fair Market Value specific data for transport"""
        return {
            'fmv_price': self.fmv_price,
            'fmv_timestamp_ns': self.fmv_timestamp_ns,
            'fmv_vs_market_price': self.fmv_vs_market_price,
            'fmv_vs_market_pct': self.fmv_vs_market_pct,
            'fmv_confidence': self.fmv_confidence,
            'market_price': self.market_price,
            'market_price_source': self.market_price_source,
            'is_undervalued': self.is_undervalued,
            'is_overvalued': self.is_overvalued,
            'valuation_magnitude': self.valuation_magnitude,
            'precision_level': self.precision_level
        }
    
    @classmethod
    def from_polygon_fmv_event(cls, polygon_data: Dict[str, Any], 
                              market_price: Optional[float] = None) -> 'FairMarketValueEvent':
        """
        Create FairMarketValueEvent from Polygon FMV event data.
        
        Args:
            polygon_data: Raw Polygon FMV event dict
            market_price: Optional current market price for comparison
            
        Returns:
            FairMarketValueEvent instance
            
        Raises:
            ValueError: If required fields are missing
            KeyError: If essential polygon fields are missing
        """
        try:
            # Required fields
            ticker = polygon_data['sym']
            fmv_price = polygon_data['fmv']
            
            # Convert timestamp from nanoseconds to seconds
            timestamp_ns = polygon_data.get('t')
            timestamp_sec = timestamp_ns / 1_000_000_000.0 if timestamp_ns else time.time()
            
            return cls(
                ticker=ticker,
                type='fair_market_value',
                price=fmv_price,
                time=timestamp_sec,
                
                # FMV specific fields
                fmv_price=fmv_price,
                fmv_timestamp_ns=timestamp_ns,
                
                # Market comparison
                market_price=market_price,
                market_price_source='external' if market_price else 'unknown',
                
                # Set base volume to 0 (FMV events don't have volume)
                volume=0
            )
            
        except KeyError as e:
            raise ValueError(f"Missing required field in Polygon FMV event: {e}")
        except Exception as e:
            raise ValueError(f"Error creating FairMarketValueEvent from Polygon data: {e}")
    
    def update_market_price(self, market_price: float, source: str = 'realtime'):
        """
        Update market price and recalculate valuation metrics.
        
        Args:
            market_price: Current market price
            source: Source of the market price data
        """
        self.market_price = market_price
        self.market_price_source = source
        self._calculate_valuation_metrics()
    
    def get_valuation_summary(self) -> Dict[str, Any]:
        """Get valuation analysis summary"""
        return {
            'fmv_price': self.fmv_price,
            'market_price': self.market_price,
            'price_difference': self.fmv_vs_market_price,
            'price_difference_pct': self.fmv_vs_market_pct,
            'is_undervalued': self.is_undervalued,
            'is_overvalued': self.is_overvalued,
            'valuation_magnitude': self.valuation_magnitude,
            'valuation_signal': self._get_valuation_signal()
        }
    
    def _get_valuation_signal(self) -> str:
        """Get simplified valuation signal"""
        if self.valuation_magnitude:
            if 'undervalued' in self.valuation_magnitude:
                return 'BUY_SIGNAL'
            elif 'overvalued' in self.valuation_magnitude:
                return 'SELL_SIGNAL'
            elif self.valuation_magnitude == 'fair':
                return 'HOLD_SIGNAL'
        return 'UNKNOWN'
    
    def is_significant_deviation(self, threshold_pct: float = 5.0) -> bool:
        """
        Check if FMV deviates significantly from market price.
        
        Args:
            threshold_pct: Percentage threshold for significant deviation
            
        Returns:
            True if deviation exceeds threshold
        """
        if self.fmv_vs_market_pct is not None:
            return abs(self.fmv_vs_market_pct) >= threshold_pct
        return False
    
    def get_trading_signal_strength(self) -> float:
        """
        Get trading signal strength based on FMV deviation.
        
        Returns:
            Signal strength from 0.0 (no signal) to 1.0 (maximum signal)
        """
        if self.fmv_vs_market_pct is None:
            return 0.0
        
        # Normalize percentage difference to 0-1 scale
        # Clamp at 20% for maximum signal strength
        abs_pct = min(abs(self.fmv_vs_market_pct), 20.0)
        return abs_pct / 20.0
    
    def __str__(self) -> str:
        """Enhanced string representation for logging"""
        fmv_str = f"FMV:${self.fmv_price:.2f}" if self.fmv_price else f"@${self.price:.2f}"
        
        market_str = ""
        if self.market_price:
            market_str = f" vs Market:${self.market_price:.2f}"
            if self.fmv_vs_market_pct:
                sign = "+" if self.fmv_vs_market_pct > 0 else ""
                market_str += f" ({sign}{self.fmv_vs_market_pct:.1f}%)"
        
        signal = ""
        if self.valuation_magnitude and self.valuation_magnitude != 'fair':
            signal = f" [{self._get_valuation_signal()}]"
        
        return f"FMV {self.ticker} {fmv_str}{market_str}{signal}"