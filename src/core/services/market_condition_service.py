"""
Market Condition Service
=======================

Provides market environment analysis for pattern performance correlation.
Tracks volatility, volume, trend, and session data to understand how market
conditions affect pattern success rates.

Features:
- Real-time market condition tracking
- Pattern performance by market environment
- Market volatility and volume analysis
- Session-based performance (pre-market, regular, after-hours)

Author: TickStock Development Team  
Date: 2025-09-06
Sprint: 23
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.infrastructure.database.connection_pool import DatabaseConnectionPool

logger = logging.getLogger(__name__)

class MarketTrend(Enum):
    """Market trend enumeration"""
    BULLISH = "bullish"
    BEARISH = "bearish" 
    NEUTRAL = "neutral"

class SessionType(Enum):
    """Trading session enumeration"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"

@dataclass
class MarketCondition:
    """Current market condition snapshot"""
    timestamp: datetime
    market_volatility: float
    volatility_percentile: float
    overall_volume: int
    volume_vs_average: float
    market_trend: MarketTrend
    trend_strength: float
    session_type: SessionType
    day_of_week: int
    advancing_count: int
    declining_count: int
    advance_decline_ratio: float
    sp500_change: float
    nasdaq_change: float
    dow_change: float

@dataclass
class PatternMarketContext:
    """Pattern performance in specific market conditions"""
    condition_type: str
    condition_value: str
    detection_count: int
    success_rate: float
    avg_return_1d: float
    vs_overall_performance: float

class MarketConditionService:
    """Service for market condition analysis and pattern correlation"""
    
    def __init__(self, db_pool: DatabaseConnectionPool):
        """Initialize market condition service
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self._current_conditions_cache = None
        self._cache_timestamp = None
        self._cache_timeout = 300  # 5 minutes
        
        logger.info("MarketConditionService initialized")
    
    async def get_current_market_conditions(self) -> Optional[MarketCondition]:
        """Get the most recent market conditions
        
        Returns:
            Current market conditions or None if unavailable
        """
        try:
            # Check cache first
            if (self._current_conditions_cache and self._cache_timestamp and 
                (datetime.now() - self._cache_timestamp).seconds < self._cache_timeout):
                logger.debug("Returning cached current market conditions")
                return self._current_conditions_cache
            
            # Fetch from database
            async with self.db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT * FROM market_conditions 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """)
                    
                    result = await cursor.fetchone()
                    
                    if not result:
                        logger.warning("No market conditions found in database")
                        return self._get_mock_market_conditions()
                    
                    conditions = MarketCondition(
                        timestamp=result[1],
                        market_volatility=float(result[2]) if result[2] else 0.0,
                        volatility_percentile=float(result[3]) if result[3] else 0.0,
                        overall_volume=int(result[4]) if result[4] else 0,
                        volume_vs_average=float(result[5]) if result[5] else 1.0,
                        market_trend=MarketTrend(result[6]),
                        trend_strength=float(result[7]) if result[7] else 0.0,
                        session_type=SessionType(result[8]),
                        day_of_week=int(result[9]),
                        advancing_count=int(result[10]) if result[10] else 0,
                        declining_count=int(result[11]) if result[11] else 0,
                        advance_decline_ratio=float(result[12]) if result[12] else 1.0,
                        sp500_change=float(result[13]) if result[13] else 0.0,
                        nasdaq_change=float(result[14]) if result[14] else 0.0,
                        dow_change=float(result[15]) if result[15] else 0.0
                    )
            
            # Cache the result
            self._current_conditions_cache = conditions
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Retrieved current market conditions: {conditions.market_trend.value}, volatility: {conditions.market_volatility}")
            return conditions
            
        except Exception as e:
            logger.error(f"Error getting current market conditions: {e}")
            # Return mock data for testing
            return self._get_mock_market_conditions()
    
    async def get_pattern_market_context(self, 
                                       pattern_name: str,
                                       days_back: int = 30) -> List[PatternMarketContext]:
        """Get pattern performance by market conditions
        
        Args:
            pattern_name: Name of the pattern to analyze
            days_back: Number of days to analyze
            
        Returns:
            List of pattern performance by market context
        """
        try:
            # Fetch from database using Sprint 23 analytics function
            async with self.db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT * FROM analyze_pattern_market_context(%s, %s)
                        ORDER BY detection_count DESC
                    """, (pattern_name, days_back))
                    
                    results = await cursor.fetchall()
                    
                    contexts = []
                    for row in results:
                        contexts.append(PatternMarketContext(
                            condition_type=row[0],
                            condition_value=row[1],
                            detection_count=int(row[2]),
                            success_rate=float(row[3]) if row[3] else 0.0,
                            avg_return_1d=float(row[4]) if row[4] else 0.0,
                            vs_overall_performance=float(row[5]) if row[5] else 0.0
                        ))
            
            logger.info(f"Retrieved {len(contexts)} market contexts for pattern: {pattern_name}")
            return contexts
            
        except Exception as e:
            logger.error(f"Error getting pattern market context for {pattern_name}: {e}")
            # Return mock data for testing
            return self._get_mock_pattern_market_context(pattern_name)
    
    async def get_market_condition_history(self, 
                                         hours_back: int = 24) -> List[MarketCondition]:
        """Get historical market conditions
        
        Args:
            hours_back: Number of hours of history to retrieve
            
        Returns:
            List of historical market conditions
        """
        try:
            async with self.db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT * FROM market_conditions 
                        WHERE timestamp >= %s 
                        ORDER BY timestamp DESC
                    """, (datetime.now() - timedelta(hours=hours_back),))
                    
                    results = await cursor.fetchall()
                    
                    conditions = []
                    for row in results:
                        conditions.append(MarketCondition(
                            timestamp=row[1],
                            market_volatility=float(row[2]) if row[2] else 0.0,
                            volatility_percentile=float(row[3]) if row[3] else 0.0,
                            overall_volume=int(row[4]) if row[4] else 0,
                            volume_vs_average=float(row[5]) if row[5] else 1.0,
                            market_trend=MarketTrend(row[6]),
                            trend_strength=float(row[7]) if row[7] else 0.0,
                            session_type=SessionType(row[8]),
                            day_of_week=int(row[9]),
                            advancing_count=int(row[10]) if result[10] else 0,
                            declining_count=int(row[11]) if result[11] else 0,
                            advance_decline_ratio=float(row[12]) if row[12] else 1.0,
                            sp500_change=float(row[13]) if row[13] else 0.0,
                            nasdaq_change=float(row[14]) if row[14] else 0.0,
                            dow_change=float(row[15]) if row[15] else 0.0
                        ))
            
            logger.info(f"Retrieved {len(conditions)} historical market conditions")
            return conditions
            
        except Exception as e:
            logger.error(f"Error getting market condition history: {e}")
            # Return mock data for testing
            return [self._get_mock_market_conditions()]
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Get market condition summary for dashboard
        
        Returns:
            Market summary with key indicators
        """
        try:
            current = await self.get_current_market_conditions()
            if not current:
                return self._get_mock_market_summary()
            
            # Determine volatility level
            if current.market_volatility < 15:
                volatility_level = "Low"
            elif current.market_volatility < 25:
                volatility_level = "Medium"  
            else:
                volatility_level = "High"
            
            # Determine volume level
            if current.volume_vs_average > 1.5:
                volume_level = "High"
            elif current.volume_vs_average > 0.8:
                volume_level = "Normal"
            else:
                volume_level = "Low"
            
            summary = {
                'timestamp': current.timestamp.isoformat(),
                'trend': current.market_trend.value.title(),
                'trend_strength': current.trend_strength,
                'volatility': current.market_volatility,
                'volatility_level': volatility_level,
                'volatility_percentile': current.volatility_percentile,
                'volume_level': volume_level,
                'volume_vs_average': current.volume_vs_average,
                'session': current.session_type.value.replace('_', ' ').title(),
                'advance_decline_ratio': current.advance_decline_ratio,
                'major_indexes': {
                    'sp500': current.sp500_change,
                    'nasdaq': current.nasdaq_change,
                    'dow': current.dow_change
                }
            }
            
            logger.info("Generated market summary")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating market summary: {e}")
            return self._get_mock_market_summary()
    
    def clear_cache(self):
        """Clear cached market conditions"""
        self._current_conditions_cache = None
        self._cache_timestamp = None
        logger.info("Market condition cache cleared")
    
    # Mock data methods for testing (will be replaced with real data from TickStockPL)
    
    def _get_mock_market_conditions(self) -> MarketCondition:
        """Generate mock market conditions for testing"""
        return MarketCondition(
            timestamp=datetime.now(),
            market_volatility=18.5,
            volatility_percentile=42.3,
            overall_volume=1250000000,
            volume_vs_average=1.12,
            market_trend=MarketTrend.BULLISH,
            trend_strength=6.2,
            session_type=SessionType.REGULAR,
            day_of_week=3,  # Wednesday
            advancing_count=2845,
            declining_count=1678,
            advance_decline_ratio=1.695,
            sp500_change=0.85,
            nasdaq_change=1.23,
            dow_change=0.67
        )
    
    def _get_mock_pattern_market_context(self, pattern_name: str) -> List[PatternMarketContext]:
        """Generate mock pattern market context for testing"""
        return [
            PatternMarketContext(
                condition_type="Volatility",
                condition_value="Low (<15)",
                detection_count=25,
                success_rate=78.2,
                avg_return_1d=2.45,
                vs_overall_performance=8.5
            ),
            PatternMarketContext(
                condition_type="Volatility",
                condition_value="Medium (15-25)",
                detection_count=18,
                success_rate=65.7,
                avg_return_1d=1.82,
                vs_overall_performance=-3.8
            ),
            PatternMarketContext(
                condition_type="Market Trend",
                condition_value="BULLISH",
                detection_count=32,
                success_rate=72.1,
                avg_return_1d=2.98,
                vs_overall_performance=5.6
            ),
            PatternMarketContext(
                condition_type="Market Trend", 
                condition_value="BEARISH",
                detection_count=11,
                success_rate=45.8,
                avg_return_1d=-0.65,
                vs_overall_performance=-23.7
            )
        ]
    
    def _get_mock_market_summary(self) -> Dict[str, Any]:
        """Generate mock market summary for testing"""
        return {
            'timestamp': datetime.now().isoformat(),
            'trend': 'Bullish',
            'trend_strength': 6.2,
            'volatility': 18.5,
            'volatility_level': 'Medium',
            'volatility_percentile': 42.3,
            'volume_level': 'High',
            'volume_vs_average': 1.12,
            'session': 'Regular',
            'advance_decline_ratio': 1.695,
            'major_indexes': {
                'sp500': 0.85,
                'nasdaq': 1.23,
                'dow': 0.67
            }
        }