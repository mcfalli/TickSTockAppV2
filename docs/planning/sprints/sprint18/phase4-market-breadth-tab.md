# Phase 4: Market Breadth Tab - Detailed Implementation Guide

**Date**: 2025-09-04  
**Sprint**: 18 - Phase 4 Implementation  
**Duration**: 2 weeks  
**Status**: Implementation Ready  
**Prerequisites**: Phase 3 complete (Advanced filtering operational)

## Phase Overview

Implement the Market Breadth tab to provide comprehensive market context analysis through index/ETF pattern detection, sector rotation visualization, and breadth indicators. This phase transforms individual pattern analysis into market-wide intelligence for strategic trading decisions.

## Success Criteria

✅ **Real-time Data**: Index patterns update every 30 seconds with <25ms query performance  
✅ **Sector Analysis**: Dynamic heatmap shows sector rotation with money flow indicators  
✅ **Breadth Indicators**: A/D Line, New Hi/Lo ratios, Volume metrics update in real-time  
✅ **Pattern Detection**: Index-specific patterns (SPY, QQQ, IWM) with technical analysis  
✅ **Visual Impact**: Clear heatmap and indicator visualization for quick market assessment  

## Implementation Tasks

### Task 4.1: Market Breadth Backend Services (Days 1-4)

#### 4.1.1 Enhanced MarketBreadthDetector
**File**: `src/services/market_breadth_detector.py`

```python
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from polygon_api_client import PolygonClient
from sqlalchemy import text
from app import db, redis_client
import json
import logging

class MarketBreadthDetector:
    """
    Advanced market breadth analysis for index/ETF patterns and sector rotation
    """
    
    def __init__(self, polygon_client: PolygonClient):
        self.client = polygon_client
        self.major_indices = ['SPY', 'QQQ', 'IWM', 'VXX', 'DIA']
        self.sector_etfs = {
            'XLK': 'Technology',
            'XLF': 'Financials', 
            'XLE': 'Energy',
            'XLV': 'Healthcare',
            'XLI': 'Industrials',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLU': 'Utilities',
            'XLC': 'Communication'
        }
        self.logger = logging.getLogger(__name__)
    
    async def analyze_market_breadth(self) -> Dict:
        """
        Comprehensive market breadth analysis
        """
        try:
            # Parallel analysis of different market aspects
            index_patterns = await self.detect_index_patterns()
            sector_analysis = await self.analyze_sector_rotation()
            breadth_indicators = await self.calculate_breadth_indicators()
            market_sentiment = await self.assess_market_sentiment()
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'index_patterns': index_patterns,
                'sector_analysis': sector_analysis,
                'breadth_indicators': breadth_indicators,
                'market_sentiment': market_sentiment,
                'summary': self.generate_market_summary(
                    index_patterns, sector_analysis, breadth_indicators
                )
            }
            
            # Cache results for 30 seconds
            redis_client.setex('market_breadth_analysis', 30, json.dumps(analysis))
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Market breadth analysis failed: {e}")
            return self.get_fallback_analysis()
    
    async def detect_index_patterns(self) -> List[Dict]:
        """
        Detect patterns on major market indices
        """
        patterns = []
        
        for symbol in self.major_indices:
            try:
                # Get recent OHLCV data
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                aggs = self.client.list_aggs(
                    symbol, 
                    multiplier=1, 
                    timespan='day', 
                    from_date=start_date, 
                    to_date=end_date,
                    limit=30
                )
                
                if not aggs:
                    continue
                
                df = pd.DataFrame([{
                    'timestamp': agg.timestamp,
                    'open': agg.open,
                    'high': agg.high,
                    'low': agg.low,
                    'close': agg.close,
                    'volume': agg.volume
                } for agg in aggs])
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df.sort_values('timestamp')
                
                # Pattern detection
                detected_patterns = self.detect_technical_patterns(symbol, df)
                patterns.extend(detected_patterns)
                
            except Exception as e:
                self.logger.error(f"Failed to analyze {symbol}: {e}")
                continue
        
        return patterns
    
    def detect_technical_patterns(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """
        Detect technical patterns on index data
        """
        patterns = []
        current_price = df['close'].iloc[-1]
        
        # Calculate technical indicators
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()  
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['high_20'] = df['high'].rolling(20).max()
        df['low_20'] = df['low'].rolling(20).min()
        
        # Pattern 1: Ascending Triangle
        ascending_triangle = self.detect_ascending_triangle(df)
        if ascending_triangle:
            patterns.append({
                'symbol': symbol,
                'pattern_type': 'Ascending_Triangle',
                'timeframe': 'Daily',
                'confidence': ascending_triangle['confidence'],
                'current_price': current_price,
                'price_change': self.calculate_price_change(df),
                'support_level': ascending_triangle['support'],
                'resistance_level': ascending_triangle['resistance'],
                'target_price': ascending_triangle['target'],
                'volume_confirmation': ascending_triangle['volume_confirm'],
                'detected_at': datetime.now(),
                'expiration': datetime.now() + timedelta(days=7),
                'indicators': {
                    'relative_strength': self.calculate_relative_strength(symbol, df),
                    'relative_volume': df['volume'].iloc[-1] / df['volume_sma'].iloc[-1],
                    'distance_to_resistance': (ascending_triangle['resistance'] - current_price) / current_price
                }
            })
        
        # Pattern 2: Bull Flag  
        bull_flag = self.detect_bull_flag(df)
        if bull_flag:
            patterns.append({
                'symbol': symbol,
                'pattern_type': 'Bull_Flag',
                'timeframe': 'Daily',
                'confidence': bull_flag['confidence'],
                'current_price': current_price,
                'price_change': self.calculate_price_change(df),
                'flag_high': bull_flag['flag_high'],
                'flag_low': bull_flag['flag_low'],
                'breakout_level': bull_flag['breakout_level'],
                'target_price': bull_flag['target'],
                'detected_at': datetime.now(),
                'expiration': datetime.now() + timedelta(days=5),
                'indicators': {
                    'relative_strength': self.calculate_relative_strength(symbol, df),
                    'relative_volume': df['volume'].iloc[-1] / df['volume_sma'].iloc[-1],
                    'flag_consolidation': bull_flag['consolidation_quality']
                }
            })
        
        # Pattern 3: Support/Resistance Break
        support_resistance = self.detect_support_resistance_break(df)
        if support_resistance:
            patterns.append({
                'symbol': symbol,
                'pattern_type': 'Support_Resistance_Break',
                'timeframe': 'Daily', 
                'confidence': support_resistance['confidence'],
                'current_price': current_price,
                'price_change': self.calculate_price_change(df),
                'break_level': support_resistance['break_level'],
                'break_direction': support_resistance['direction'],
                'volume_confirmation': support_resistance['volume_confirm'],
                'target_price': support_resistance['target'],
                'detected_at': datetime.now(),
                'expiration': datetime.now() + timedelta(days=3),
                'indicators': {
                    'relative_strength': self.calculate_relative_strength(symbol, df),
                    'relative_volume': df['volume'].iloc[-1] / df['volume_sma'].iloc[-1],
                    'break_strength': support_resistance['break_strength']
                }
            })
        
        return patterns
    
    def detect_ascending_triangle(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect ascending triangle pattern on index data
        """
        if len(df) < 20:
            return None
        
        recent_highs = df['high'].tail(10)
        recent_lows = df['low'].tail(10)
        
        # Check for horizontal resistance (similar highs)
        resistance_level = recent_highs.max()
        resistance_touches = (recent_highs >= resistance_level * 0.995).sum()
        
        if resistance_touches < 2:
            return None
        
        # Check for ascending support (rising lows)
        low_points = []
        for i in range(len(recent_lows) - 2):
            if (recent_lows.iloc[i] < recent_lows.iloc[i+1] and 
                recent_lows.iloc[i+1] > recent_lows.iloc[i+2]):
                low_points.append(recent_lows.iloc[i+1])
        
        if len(low_points) < 2:
            return None
        
        # Calculate trend of lows
        support_trend = np.polyfit(range(len(low_points)), low_points, 1)[0]
        
        if support_trend <= 0:  # Not ascending
            return None
        
        support_level = low_points[-1]
        
        # Volume confirmation
        recent_volume = df['volume'].tail(5).mean()
        avg_volume = df['volume'].mean()
        volume_confirm = recent_volume > avg_volume * 1.1
        
        # Calculate confidence
        confidence = min(0.95, 0.7 + 
                        (resistance_touches * 0.05) + 
                        (support_trend * 0.1) + 
                        (0.1 if volume_confirm else 0))
        
        # Target price (triangle height added to breakout)
        triangle_height = resistance_level - support_level
        target = resistance_level + triangle_height
        
        return {
            'confidence': confidence,
            'support': support_level,
            'resistance': resistance_level,
            'target': target,
            'volume_confirm': volume_confirm
        }
    
    def detect_bull_flag(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect bull flag pattern on index data
        """
        if len(df) < 15:
            return None
        
        # Look for strong upward move followed by consolidation
        recent_data = df.tail(15)
        
        # Check for initial strong move (flagpole)
        flagpole_start = len(recent_data) - 10
        flagpole_end = len(recent_data) - 5
        
        if flagpole_start < 0 or flagpole_end < 0:
            return None
        
        flagpole_gain = (recent_data['close'].iloc[flagpole_end] - 
                        recent_data['close'].iloc[flagpole_start]) / recent_data['close'].iloc[flagpole_start]
        
        if flagpole_gain < 0.02:  # Less than 2% gain
            return None
        
        # Check for consolidation (flag)
        flag_data = recent_data.tail(5)
        flag_high = flag_data['high'].max()
        flag_low = flag_data['low'].min()
        flag_range = (flag_high - flag_low) / flag_low
        
        if flag_range > 0.05:  # Too much volatility for a flag
            return None
        
        # Volume should diminish during flag formation
        flag_volume = flag_data['volume'].mean()
        flagpole_volume = recent_data.iloc[flagpole_start:flagpole_end]['volume'].mean()
        volume_diminish = flag_volume < flagpole_volume * 0.8
        
        # Calculate confidence
        confidence = min(0.95, 0.75 + 
                        (flagpole_gain * 2) +  # Stronger flagpole = higher confidence
                        (0.1 if volume_diminish else 0) +
                        (0.05 if flag_range < 0.03 else 0))  # Tighter flag = higher confidence
        
        # Target price (flagpole height added to breakout)
        flagpole_height = recent_data['close'].iloc[flagpole_end] - recent_data['close'].iloc[flagpole_start]
        breakout_level = flag_high
        target = breakout_level + flagpole_height
        
        return {
            'confidence': confidence,
            'flag_high': flag_high,
            'flag_low': flag_low,
            'breakout_level': breakout_level,
            'target': target,
            'consolidation_quality': 1.0 - flag_range / 0.05  # 0-1 scale
        }
    
    def detect_support_resistance_break(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect support or resistance level breaks
        """
        if len(df) < 20:
            return None
        
        current_price = df['close'].iloc[-1]
        previous_price = df['close'].iloc[-2]
        
        # Find significant support/resistance levels
        highs = df['high'].rolling(5, center=True).max()
        lows = df['low'].rolling(5, center=True).min()
        
        # Identify pivot points
        resistance_levels = []
        support_levels = []
        
        for i in range(2, len(df)-2):
            if (df['high'].iloc[i] == highs.iloc[i] and 
                df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i] > df['high'].iloc[i+1]):
                resistance_levels.append(df['high'].iloc[i])
            
            if (df['low'].iloc[i] == lows.iloc[i] and 
                df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i] < df['low'].iloc[i+1]):
                support_levels.append(df['low'].iloc[i])
        
        # Check for recent breaks
        break_detected = None
        
        # Resistance break (bullish)
        for resistance in resistance_levels[-5:]:  # Check last 5 resistance levels
            if (previous_price <= resistance and current_price > resistance and
                current_price > resistance * 1.001):  # 0.1% break threshold
                
                volume_confirm = df['volume'].iloc[-1] > df['volume'].rolling(10).mean().iloc[-1] * 1.2
                break_strength = (current_price - resistance) / resistance
                
                confidence = min(0.95, 0.8 + 
                               (break_strength * 10) +  # Stronger break = higher confidence
                               (0.1 if volume_confirm else 0))
                
                target = resistance + (resistance - min(support_levels[-3:]) if support_levels else resistance * 0.05)
                
                break_detected = {
                    'confidence': confidence,
                    'break_level': resistance,
                    'direction': 'bullish',
                    'target': target,
                    'volume_confirm': volume_confirm,
                    'break_strength': break_strength
                }
                break
        
        # Support break (bearish)
        if not break_detected:
            for support in support_levels[-5:]:
                if (previous_price >= support and current_price < support and
                    current_price < support * 0.999):  # 0.1% break threshold
                    
                    volume_confirm = df['volume'].iloc[-1] > df['volume'].rolling(10).mean().iloc[-1] * 1.2
                    break_strength = (support - current_price) / support
                    
                    confidence = min(0.95, 0.8 + 
                                   (break_strength * 10) +
                                   (0.1 if volume_confirm else 0))
                    
                    target = support - (max(resistance_levels[-3:]) - support if resistance_levels else support * 0.05)
                    
                    break_detected = {
                        'confidence': confidence,
                        'break_level': support,
                        'direction': 'bearish',
                        'target': target,
                        'volume_confirm': volume_confirm,
                        'break_strength': break_strength
                    }
                    break
        
        return break_detected
    
    def calculate_relative_strength(self, symbol: str, df: pd.DataFrame) -> float:
        """
        Calculate relative strength vs SPY benchmark
        """
        try:
            if symbol == 'SPY':
                return 1.0
            
            # Get SPY data for comparison
            spy_data = self.get_benchmark_data('SPY', len(df))
            if not spy_data:
                return 1.0
            
            # Calculate relative performance over last 20 days
            symbol_return = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]
            spy_return = (spy_data[-1] - spy_data[-20]) / spy_data[-20]
            
            relative_strength = (1 + symbol_return) / (1 + spy_return)
            return round(relative_strength, 2)
            
        except:
            return 1.0
    
    async def analyze_sector_rotation(self) -> Dict:
        """
        Analyze sector rotation and money flow patterns
        """
        sector_data = {}
        
        for etf_symbol, sector_name in self.sector_etfs.items():
            try:
                # Get recent performance data
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
                
                aggs = self.client.list_aggs(
                    etf_symbol,
                    multiplier=1,
                    timespan='day',
                    from_date=start_date,
                    to_date=end_date,
                    limit=5
                )
                
                if not aggs or len(aggs) < 2:
                    continue
                
                latest = aggs[-1]
                previous = aggs[-2]
                
                # Calculate metrics
                price_change = (latest.close - previous.close) / previous.close * 100
                volume_change = (latest.volume - previous.volume) / previous.volume * 100
                
                # Get relative strength vs market
                spy_data = await self.get_spy_benchmark(5)
                relative_strength = self.calculate_sector_rs(aggs, spy_data)
                
                # Money flow analysis
                money_flow = self.calculate_money_flow(aggs[-5:])
                
                sector_data[etf_symbol] = {
                    'name': sector_name,
                    'symbol': etf_symbol,
                    'current_price': latest.close,
                    'price_change': round(price_change, 2),
                    'volume_change': round(volume_change, 2),
                    'relative_strength': relative_strength,
                    'money_flow': money_flow,
                    'volume': latest.volume,
                    'market_cap_weight': self.get_sector_weight(etf_symbol),
                    'momentum_score': self.calculate_momentum_score(aggs[-10:] if len(aggs) >= 10 else aggs)
                }
                
            except Exception as e:
                self.logger.error(f"Failed to analyze sector {etf_symbol}: {e}")
                continue
        
        # Calculate sector rotation metrics
        rotation_analysis = self.analyze_rotation_patterns(sector_data)
        
        return {
            'sectors': sector_data,
            'rotation_analysis': rotation_analysis,
            'hot_sectors': self.identify_hot_sectors(sector_data),
            'cold_sectors': self.identify_cold_sectors(sector_data)
        }
    
    async def calculate_breadth_indicators(self) -> Dict:
        """
        Calculate market breadth indicators
        """
        try:
            # Query database for recent stock performance
            query = """
            WITH recent_stocks AS (
                SELECT DISTINCT symbol 
                FROM daily_patterns 
                WHERE detected_at >= NOW() - INTERVAL '1 day'
                LIMIT 1000
            ),
            stock_changes AS (
                SELECT 
                    symbol,
                    price_change,
                    CASE WHEN price_change > 0 THEN 1 ELSE 0 END as advancing,
                    CASE WHEN price_change < 0 THEN 1 ELSE 0 END as declining,
                    current_price
                FROM daily_patterns dp
                WHERE dp.symbol IN (SELECT symbol FROM recent_stocks)
                AND dp.detected_at >= NOW() - INTERVAL '1 day'
                ORDER BY dp.detected_at DESC
            )
            SELECT 
                COUNT(*) as total_stocks,
                SUM(advancing) as advancing_stocks,
                SUM(declining) as declining_stocks,
                AVG(price_change) as avg_change,
                COUNT(CASE WHEN current_price = (SELECT MAX(current_price) FROM stock_changes sc2 WHERE sc2.symbol = stock_changes.symbol) THEN 1 END) as new_highs,
                COUNT(CASE WHEN current_price = (SELECT MIN(current_price) FROM stock_changes sc2 WHERE sc2.symbol = stock_changes.symbol) THEN 1 END) as new_lows
            FROM stock_changes
            """
            
            result = db.session.execute(text(query)).fetchone()
            
            if not result:
                return self.get_fallback_breadth_indicators()
            
            total = result.total_stocks or 0
            advancing = result.advancing_stocks or 0
            declining = result.declining_stocks or 0
            
            # Calculate A/D Line
            ad_ratio = advancing / declining if declining > 0 else 1.0
            ad_line_status = self.classify_ad_line(ad_ratio)
            
            # Calculate New High/Low Ratio
            new_highs = result.new_highs or 0
            new_lows = result.new_lows or 0
            hl_ratio = new_highs / new_lows if new_lows > 0 else 1.0
            hl_status = self.classify_hl_ratio(hl_ratio)
            
            # Up/Down Volume (simplified calculation)
            up_volume_ratio = advancing / total if total > 0 else 0.5
            volume_status = self.classify_volume_ratio(up_volume_ratio)
            
            return {
                'advance_decline': {
                    'advancing': advancing,
                    'declining': declining,
                    'ratio': round(ad_ratio, 2),
                    'status': ad_line_status,
                    'strength': min(4, max(1, round(ad_ratio)))
                },
                'new_highs_lows': {
                    'new_highs': new_highs,
                    'new_lows': new_lows,
                    'ratio': round(hl_ratio, 2),
                    'status': hl_status,
                    'strength': min(4, max(1, round(hl_ratio)))
                },
                'up_down_volume': {
                    'up_volume_ratio': round(up_volume_ratio, 2),
                    'status': volume_status,
                    'strength': min(4, max(1, round(up_volume_ratio * 4)))
                },
                'market_participation': {
                    'total_stocks': total,
                    'participation_rate': round((advancing + declining) / total * 100, 1) if total > 0 else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Breadth indicators calculation failed: {e}")
            return self.get_fallback_breadth_indicators()
    
    def classify_ad_line(self, ratio: float) -> str:
        """Classify Advance/Decline ratio"""
        if ratio >= 2.0:
            return 'Very Bullish'
        elif ratio >= 1.5:
            return 'Bullish'
        elif ratio >= 0.8:
            return 'Neutral'
        elif ratio >= 0.5:
            return 'Bearish'
        else:
            return 'Very Bearish'
    
    def classify_hl_ratio(self, ratio: float) -> str:
        """Classify New High/Low ratio"""
        if ratio >= 3.0:
            return 'Very Bullish'
        elif ratio >= 1.5:
            return 'Bullish'
        elif ratio >= 0.7:
            return 'Neutral'
        elif ratio >= 0.3:
            return 'Bearish'
        else:
            return 'Very Bearish'
    
    def classify_volume_ratio(self, ratio: float) -> str:
        """Classify up/down volume ratio"""
        if ratio >= 0.7:
            return 'Strong'
        elif ratio >= 0.6:
            return 'Moderate'
        elif ratio >= 0.45:
            return 'Neutral'
        else:
            return 'Weak'
    
    def get_fallback_breadth_indicators(self) -> Dict:
        """Fallback breadth indicators when data unavailable"""
        return {
            'advance_decline': {
                'advancing': 0,
                'declining': 0,
                'ratio': 1.0,
                'status': 'Unknown',
                'strength': 2
            },
            'new_highs_lows': {
                'new_highs': 0,
                'new_lows': 0,
                'ratio': 1.0,
                'status': 'Unknown', 
                'strength': 2
            },
            'up_down_volume': {
                'up_volume_ratio': 0.5,
                'status': 'Unknown',
                'strength': 2
            },
            'market_participation': {
                'total_stocks': 0,
                'participation_rate': 0
            }
        }
    
    def calculate_price_change(self, df: pd.DataFrame) -> float:
        """Calculate daily price change percentage"""
        if len(df) < 2:
            return 0.0
        current = df['close'].iloc[-1]
        previous = df['close'].iloc[-2]
        return round((current - previous) / previous * 100, 2)
    
    def generate_market_summary(self, index_patterns: List, sector_analysis: Dict, breadth_indicators: Dict) -> Dict:
        """
        Generate overall market summary
        """
        # Count bullish vs bearish patterns
        bullish_patterns = sum(1 for p in index_patterns if p.get('indicators', {}).get('relative_strength', 1) > 1.0)
        total_patterns = len(index_patterns)
        
        # Sector strength
        sectors = sector_analysis.get('sectors', {})
        positive_sectors = sum(1 for s in sectors.values() if s.get('price_change', 0) > 0)
        total_sectors = len(sectors)
        
        # Breadth strength
        ad_strength = breadth_indicators.get('advance_decline', {}).get('strength', 2)
        hl_strength = breadth_indicators.get('new_highs_lows', {}).get('strength', 2)
        
        # Overall market bias
        pattern_bias = bullish_patterns / total_patterns if total_patterns > 0 else 0.5
        sector_bias = positive_sectors / total_sectors if total_sectors > 0 else 0.5
        breadth_bias = (ad_strength + hl_strength) / 8  # Normalize to 0-1
        
        overall_bias = (pattern_bias * 0.4 + sector_bias * 0.3 + breadth_bias * 0.3)
        
        if overall_bias >= 0.7:
            market_bias = 'Bullish'
        elif overall_bias >= 0.6:
            market_bias = 'Mildly Bullish'
        elif overall_bias >= 0.4:
            market_bias = 'Neutral'
        elif overall_bias >= 0.3:
            market_bias = 'Mildly Bearish'
        else:
            market_bias = 'Bearish'
        
        return {
            'overall_bias': market_bias,
            'bias_score': round(overall_bias, 2),
            'index_patterns_count': total_patterns,
            'bullish_patterns': bullish_patterns,
            'positive_sectors': positive_sectors,
            'total_sectors': total_sectors,
            'key_levels': self.identify_key_market_levels(index_patterns),
            'risk_factors': self.identify_risk_factors(index_patterns, breadth_indicators)
        }
```

### Task 4.2: Market Breadth Frontend Component (Days 5-8)

#### 4.2.1 MarketBreadth React Component
**File**: `static/js/components/MarketBreadth.js`

```javascript
class MarketBreadth {
    constructor(container) {
        this.container = container;
        this.data = null;
        this.updateInterval = null;
        this.heatmapChart = null;
        
        this.init();
        this.loadData();
        this.startAutoRefresh();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="market-breadth">
                <!-- Market Overview Header -->
                <div class="market-overview-header">
                    <div class="market-summary">
                        <h3>📊 Market Overview</h3>
                        <div class="overall-bias" id="overall-bias">
                            <span class="bias-label">Market Bias:</span>
                            <span class="bias-value" id="bias-value">Loading...</span>
                            <span class="bias-score" id="bias-score"></span>
                        </div>
                    </div>
                    <div class="last-updated">
                        <span id="breadth-last-updated">Loading...</span>
                    </div>
                </div>
                
                <!-- Main Content Grid -->
                <div class="breadth-content-grid">
                    <!-- Left Panel: Indices & Breadth -->
                    <div class="indices-breadth-panel">
                        <!-- Major Indices -->
                        <div class="breadth-section">
                            <h4>📈 Major Indices</h4>
                            <div class="indices-grid" id="indices-grid">
                                <!-- Populated by JavaScript -->
                            </div>
                        </div>
                        
                        <!-- Breadth Indicators -->
                        <div class="breadth-section">
                            <h4>📊 Breadth Indicators</h4>
                            <div class="breadth-indicators" id="breadth-indicators">
                                <!-- Populated by JavaScript -->
                            </div>
                        </div>
                        
                        <!-- Index Patterns Table -->
                        <div class="breadth-section">
                            <h4>🎯 Index Pattern Signals</h4>
                            <div class="index-patterns-container">
                                <div class="patterns-table-wrapper">
                                    <table class="index-patterns-table" id="index-patterns-table">
                                        <thead>
                                            <tr>
                                                <th>Symbol</th>
                                                <th>Pattern</th>
                                                <th>Timeframe</th>
                                                <th>Conf</th>
                                                <th>RS</th>
                                                <th>Price</th>
                                                <th>Key Levels</th>
                                                <th>Chart</th>
                                            </tr>
                                        </thead>
                                        <tbody id="index-patterns-body">
                                            <!-- Populated by JavaScript -->
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Right Panel: Sector Analysis -->
                    <div class="sector-analysis-panel">
                        <!-- Sector Rotation Heatmap -->
                        <div class="breadth-section">
                            <h4>🔥 Sector Rotation Heatmap</h4>
                            <div class="sector-heatmap" id="sector-heatmap">
                                <!-- Populated by JavaScript -->
                            </div>
                        </div>
                        
                        <!-- Hot & Cold Sectors -->
                        <div class="breadth-section">
                            <h4>🚀 Sector Performance</h4>
                            <div class="sector-performance">
                                <div class="hot-sectors">
                                    <h5>🔥 Hot Sectors</h5>
                                    <div class="sector-list" id="hot-sectors-list">
                                        <!-- Populated by JavaScript -->
                                    </div>
                                </div>
                                <div class="cold-sectors">
                                    <h5>❄️ Cold Sectors</h5>
                                    <div class="sector-list" id="cold-sectors-list">
                                        <!-- Populated by JavaScript -->
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Money Flow Analysis -->
                        <div class="breadth-section">
                            <h4>💰 Money Flow Analysis</h4>
                            <div class="money-flow-container" id="money-flow-container">
                                <!-- Populated by JavaScript -->
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Risk Factors Alert -->
                <div class="risk-factors" id="risk-factors" style="display: none;">
                    <div class="risk-header">
                        <span class="risk-icon">⚠️</span>
                        <h4>Risk Factors Detected</h4>
                    </div>
                    <div class="risk-list" id="risk-list">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>
            </div>
        `;
        
        this.bindEvents();
    }
    
    bindEvents() {
        // Chart click events for index patterns
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('index-chart-btn')) {
                const symbol = e.target.dataset.symbol;
                this.showIndexChart(symbol);
            }
        });
        
        // Sector click events
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('sector-tile')) {
                const sector = e.target.dataset.sector;
                this.showSectorDetails(sector);
            }
        });
    }
    
    async loadData() {
        try {
            this.showLoading(true);
            const response = await fetch('/api/market/breadth');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.data = await response.json();
            this.renderData();
            
        } catch (error) {
            this.showError('Failed to load market breadth data: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    renderData() {
        if (!this.data) return;
        
        this.renderMarketSummary();
        this.renderIndices();
        this.renderBreadthIndicators();
        this.renderIndexPatterns();
        this.renderSectorHeatmap();
        this.renderSectorPerformance();
        this.renderMoneyFlow();
        this.renderRiskFactors();
        this.updateTimestamp();
    }
    
    renderMarketSummary() {
        const summary = this.data.market_summary || {};
        
        const biasElement = document.getElementById('bias-value');
        const scoreElement = document.getElementById('bias-score');
        
        biasElement.textContent = summary.overall_bias || 'Unknown';
        biasElement.className = `bias-value bias-${(summary.overall_bias || 'neutral').toLowerCase()}`;
        
        scoreElement.textContent = `(${summary.bias_score || 0.5})`;
        
        // Update overall bias container styling
        const overallBias = document.getElementById('overall-bias');
        overallBias.className = `overall-bias ${(summary.overall_bias || 'neutral').toLowerCase()}`;
    }
    
    renderIndices() {
        const indicesGrid = document.getElementById('indices-grid');
        const indices = this.data.index_patterns || [];
        
        // Get unique indices for display
        const indexData = this.getUniqueIndices(indices);
        
        indicesGrid.innerHTML = indexData.map(index => `
            <div class="index-card" data-symbol="${index.symbol}">
                <div class="index-header">
                    <span class="index-symbol">${index.symbol}</span>
                    <span class="index-price">${this.formatPrice(index.current_price)}</span>
                </div>
                <div class="index-change ${index.price_change >= 0 ? 'positive' : 'negative'}">
                    ${this.formatChange(index.price_change)}
                </div>
                <div class="index-strength">
                    ${this.renderStrengthBars(index.strength)}
                </div>
                <div class="index-patterns-count">
                    ${index.pattern_count} pattern${index.pattern_count !== 1 ? 's' : ''}
                </div>
            </div>
        `).join('');
    }
    
    renderBreadthIndicators() {
        const container = document.getElementById('breadth-indicators');
        const breadth = this.data.breadth_indicators || {};
        
        container.innerHTML = `
            <div class="breadth-grid">
                <!-- Advance/Decline Line -->
                <div class="breadth-indicator">
                    <div class="indicator-header">
                        <span class="indicator-label">A/D Line</span>
                        <span class="indicator-status ${breadth.advance_decline?.status?.toLowerCase() || 'unknown'}">
                            ${breadth.advance_decline?.status || 'Unknown'}
                        </span>
                    </div>
                    <div class="indicator-values">
                        <span class="advancing">↑${breadth.advance_decline?.advancing || 0}</span>
                        <span class="declining">↓${breadth.advance_decline?.declining || 0}</span>
                    </div>
                    <div class="indicator-strength">
                        ${this.renderStrengthBars(breadth.advance_decline?.strength || 2)}
                    </div>
                </div>
                
                <!-- New Highs/Lows -->
                <div class="breadth-indicator">
                    <div class="indicator-header">
                        <span class="indicator-label">New Hi/Lo</span>
                        <span class="indicator-status ${breadth.new_highs_lows?.status?.toLowerCase() || 'unknown'}">
                            ${breadth.new_highs_lows?.status || 'Unknown'}
                        </span>
                    </div>
                    <div class="indicator-values">
                        <span class="new-highs">⬆${breadth.new_highs_lows?.new_highs || 0}</span>
                        <span class="new-lows">⬇${breadth.new_highs_lows?.new_lows || 0}</span>
                    </div>
                    <div class="indicator-strength">
                        ${this.renderStrengthBars(breadth.new_highs_lows?.strength || 2)}
                    </div>
                </div>
                
                <!-- Up/Down Volume -->
                <div class="breadth-indicator">
                    <div class="indicator-header">
                        <span class="indicator-label">Up Volume</span>
                        <span class="indicator-status ${breadth.up_down_volume?.status?.toLowerCase() || 'unknown'}">
                            ${breadth.up_down_volume?.status || 'Unknown'}
                        </span>
                    </div>
                    <div class="indicator-values">
                        <span class="volume-ratio">${Math.round((breadth.up_down_volume?.up_volume_ratio || 0.5) * 100)}%</span>
                    </div>
                    <div class="indicator-strength">
                        ${this.renderStrengthBars(breadth.up_down_volume?.strength || 2)}
                    </div>
                </div>
            </div>
        `;
    }
    
    renderIndexPatterns() {
        const tbody = document.getElementById('index-patterns-body');
        const patterns = this.data.index_patterns || [];
        
        tbody.innerHTML = patterns.map(pattern => `
            <tr class="pattern-row">
                <td class="symbol-cell">
                    <strong>${pattern.symbol}</strong>
                </td>
                <td class="pattern-cell">
                    <span class="pattern-badge pattern-${pattern.pattern_type.toLowerCase()}">
                        ${this.abbreviatePattern(pattern.pattern_type)}
                    </span>
                </td>
                <td class="timeframe-cell">${pattern.timeframe}</td>
                <td class="confidence-cell">
                    <span class="confidence-value conf-${this.getConfidenceClass(pattern.confidence)}">
                        ${Math.round(pattern.confidence * 100)}%
                    </span>
                </td>
                <td class="rs-cell">
                    <span class="rs-value ${pattern.indicators?.relative_strength > 1.1 ? 'rs-high' : ''}">
                        ${(pattern.indicators?.relative_strength || 1.0).toFixed(1)}x
                    </span>
                </td>
                <td class="price-cell">${this.formatPrice(pattern.current_price)}</td>
                <td class="levels-cell">
                    ${this.formatKeyLevels(pattern)}
                </td>
                <td class="chart-cell">
                    <button class="index-chart-btn" data-symbol="${pattern.symbol}">📊</button>
                </td>
            </tr>
        `).join('');
    }
    
    renderSectorHeatmap() {
        const container = document.getElementById('sector-heatmap');
        const sectors = this.data.sector_analysis?.sectors || {};
        
        // Convert sectors object to array and sort by performance
        const sectorArray = Object.values(sectors).sort((a, b) => b.price_change - a.price_change);
        
        container.innerHTML = `
            <div class="heatmap-grid">
                ${sectorArray.map(sector => `
                    <div class="sector-tile ${this.getSectorClass(sector.price_change)}" 
                         data-sector="${sector.symbol}">
                        <div class="sector-name">${sector.name}</div>
                        <div class="sector-symbol">${sector.symbol}</div>
                        <div class="sector-change">${this.formatChange(sector.price_change)}</div>
                        <div class="sector-rs">RS: ${(sector.relative_strength || 1.0).toFixed(1)}x</div>
                        <div class="sector-volume">Vol: ${this.formatVolumeChange(sector.volume_change)}</div>
                        <div class="sector-momentum">
                            ${this.renderMomentumBars(sector.momentum_score)}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    renderSectorPerformance() {
        const sectors = this.data.sector_analysis?.sectors || {};
        const sectorArray = Object.values(sectors);
        
        // Hot sectors (top 3 performers)
        const hotSectors = sectorArray
            .sort((a, b) => b.price_change - a.price_change)
            .slice(0, 3);
        
        // Cold sectors (bottom 3 performers)
        const coldSectors = sectorArray
            .sort((a, b) => a.price_change - b.price_change)
            .slice(0, 3);
        
        document.getElementById('hot-sectors-list').innerHTML = hotSectors.map(sector => `
            <div class="sector-item hot">
                <span class="sector-name">${sector.name}</span>
                <span class="sector-change positive">${this.formatChange(sector.price_change)}</span>
            </div>
        `).join('');
        
        document.getElementById('cold-sectors-list').innerHTML = coldSectors.map(sector => `
            <div class="sector-item cold">
                <span class="sector-name">${sector.name}</span>
                <span class="sector-change negative">${this.formatChange(sector.price_change)}</span>
            </div>
        `).join('');
    }
    
    renderMoneyFlow() {
        const container = document.getElementById('money-flow-container');
        const rotationAnalysis = this.data.sector_analysis?.rotation_analysis || {};
        
        container.innerHTML = `
            <div class="money-flow-grid">
                <div class="flow-metric">
                    <div class="metric-label">Primary Flow</div>
                    <div class="metric-value">${rotationAnalysis.primary_flow || 'Balanced'}</div>
                </div>
                <div class="flow-metric">
                    <div class="metric-label">Rotation Strength</div>
                    <div class="metric-value">
                        ${this.renderStrengthBars(rotationAnalysis.rotation_strength || 2)}
                    </div>
                </div>
                <div class="flow-metric">
                    <div class="metric-label">Trend Duration</div>
                    <div class="metric-value">${rotationAnalysis.trend_duration || 'Unknown'}</div>
                </div>
            </div>
        `;
    }
    
    renderRiskFactors() {
        const riskFactors = this.data.market_summary?.risk_factors || [];
        const riskContainer = document.getElementById('risk-factors');
        
        if (riskFactors.length === 0) {
            riskContainer.style.display = 'none';
            return;
        }
        
        riskContainer.style.display = 'block';
        document.getElementById('risk-list').innerHTML = riskFactors.map(risk => `
            <div class="risk-item">
                <span class="risk-severity ${risk.severity?.toLowerCase() || 'medium'}">${risk.severity || 'Medium'}</span>
                <span class="risk-description">${risk.description}</span>
            </div>
        `).join('');
    }
    
    // Utility methods
    getUniqueIndices(patterns) {
        const indexMap = new Map();
        
        patterns.forEach(pattern => {
            if (!indexMap.has(pattern.symbol)) {
                indexMap.set(pattern.symbol, {
                    symbol: pattern.symbol,
                    current_price: pattern.current_price,
                    price_change: pattern.price_change,
                    strength: pattern.indicators?.relative_strength || 1.0,
                    pattern_count: 0
                });
            }
            indexMap.get(pattern.symbol).pattern_count++;
        });
        
        return Array.from(indexMap.values());
    }
    
    renderStrengthBars(strength) {
        const bars = 4;
        const filled = Math.min(bars, Math.max(1, Math.round(strength)));
        
        return Array.from({length: bars}, (_, i) => 
            `<span class="strength-bar ${i < filled ? 'filled' : ''}"></span>`
        ).join('');
    }
    
    renderMomentumBars(momentum) {
        const bars = 3;
        const filled = Math.min(bars, Math.max(0, Math.round(momentum * bars)));
        
        return Array.from({length: bars}, (_, i) => 
            `<span class="momentum-bar ${i < filled ? 'filled' : ''}"></span>`
        ).join('');
    }
    
    getSectorClass(priceChange) {
        if (priceChange >= 2) return 'very-hot';
        if (priceChange >= 1) return 'hot';
        if (priceChange >= 0) return 'warm';
        if (priceChange >= -1) return 'cool';
        if (priceChange >= -2) return 'cold';
        return 'very-cold';
    }
    
    getConfidenceClass(confidence) {
        if (confidence >= 0.9) return 'very-high';
        if (confidence >= 0.8) return 'high';
        if (confidence >= 0.7) return 'medium';
        return 'low';
    }
    
    abbreviatePattern(patternType) {
        const abbreviations = {
            'Ascending_Triangle': 'AscTri',
            'Bull_Flag': 'BullFlag',
            'Support_Resistance_Break': 'SR Break'
        };
        return abbreviations[patternType] || patternType.substring(0, 8);
    }
    
    formatPrice(price) {
        return price ? `$${price.toFixed(2)}` : 'N/A';
    }
    
    formatChange(change) {
        return change ? `${change >= 0 ? '+' : ''}${change.toFixed(1)}%` : '0.0%';
    }
    
    formatVolumeChange(volumeChange) {
        if (!volumeChange) return '0%';
        return `${volumeChange >= 0 ? '+' : ''}${volumeChange.toFixed(0)}%`;
    }
    
    formatKeyLevels(pattern) {
        const levels = [];
        
        if (pattern.support_level) {
            levels.push(`S:${pattern.support_level.toFixed(2)}`);
        }
        if (pattern.resistance_level) {
            levels.push(`R:${pattern.resistance_level.toFixed(2)}`);
        }
        if (pattern.target_price) {
            levels.push(`T:${pattern.target_price.toFixed(2)}`);
        }
        
        return levels.join(' ') || 'N/A';
    }
    
    updateTimestamp() {
        document.getElementById('breadth-last-updated').textContent = 
            `Updated: ${new Date().toLocaleTimeString()}`;
    }
    
    startAutoRefresh() {
        this.updateInterval = setInterval(() => {
            this.loadData();
        }, 30000); // 30 seconds
    }
    
    showLoading(show) {
        // Implementation similar to PatternScanner
    }
    
    showError(message) {
        // Implementation similar to PatternScanner
    }
    
    showIndexChart(symbol) {
        console.log(`Show chart for ${symbol}`);
        // Implementation in Phase 6
    }
    
    showSectorDetails(sector) {
        console.log(`Show details for ${sector}`);
        // Implementation for sector drill-down
    }
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
    }
}

// Register for GoldenLayout
window.MarketBreadth = MarketBreadth;
```

### Task 4.3: Market Breadth Styles (Days 9-10)

#### 4.3.1 Market Breadth CSS
**File**: `static/css/market-breadth.css`

```css
/* Market Breadth Styles */
.market-breadth {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
    overflow: hidden;
}

/* Market Overview Header */
.market-overview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
}

.market-summary h3 {
    margin: 0 0 8px 0;
    font-size: 16px;
    color: var(--text-primary);
}

.overall-bias {
    display: flex;
    align-items: center;
    gap: 8px;
}

.bias-label {
    font-size: 12px;
    color: var(--text-secondary);
    text-transform: uppercase;
    font-weight: 500;
}

.bias-value {
    font-size: 14px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 3px;
}

.bias-value.bullish,
.bias-value.mildly_bullish {
    background: rgba(81, 207, 102, 0.2);
    color: var(--success-color);
}

.bias-value.bearish,
.bias-value.mildly_bearish {
    background: rgba(255, 107, 107, 0.2);
    color: var(--error-color);
}

.bias-value.neutral {
    background: rgba(255, 212, 59, 0.2);
    color: var(--warning-color);
}

.bias-score {
    font-size: 11px;
    color: var(--text-secondary);
}

.last-updated {
    font-size: 11px;
    color: var(--text-secondary);
}

/* Content Grid */
.breadth-content-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 16px;
    flex: 1;
    overflow: hidden;
}

.indices-breadth-panel,
.sector-analysis-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow: hidden;
}

/* Breadth Sections */
.breadth-section {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    overflow: hidden;
}

.breadth-section h4 {
    margin: 0;
    padding: 12px 16px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Indices Grid */
.indices-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 8px;
    padding: 12px;
}

.index-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 8px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
}

.index-card:hover {
    background: var(--bg-hover);
    border-color: var(--accent-primary);
}

.index-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.index-symbol {
    font-weight: 600;
    font-size: 12px;
    color: var(--text-primary);
}

.index-price {
    font-size: 11px;
    color: var(--text-secondary);
}

.index-change {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 6px;
}

.index-change.positive {
    color: var(--success-color);
}

.index-change.negative {
    color: var(--error-color);
}

.index-strength {
    display: flex;
    justify-content: center;
    gap: 2px;
    margin-bottom: 6px;
}

.strength-bar {
    width: 12px;
    height: 4px;
    background: var(--border-color);
    border-radius: 1px;
}

.strength-bar.filled {
    background: var(--accent-primary);
}

.index-patterns-count {
    font-size: 10px;
    color: var(--text-secondary);
}

/* Breadth Indicators */
.breadth-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 12px;
}

.breadth-indicator {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 12px;
}

.indicator-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.indicator-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-primary);
    text-transform: uppercase;
}

.indicator-status {
    font-size: 10px;
    font-weight: 500;
    padding: 2px 6px;
    border-radius: 2px;
    text-transform: uppercase;
}

.indicator-status.bullish,
.indicator-status.very_bullish {
    background: rgba(81, 207, 102, 0.2);
    color: var(--success-color);
}

.indicator-status.bearish,
.indicator-status.very_bearish {
    background: rgba(255, 107, 107, 0.2);
    color: var(--error-color);
}

.indicator-status.neutral {
    background: rgba(255, 212, 59, 0.2);
    color: var(--warning-color);
}

.indicator-status.strong {
    background: rgba(81, 207, 102, 0.2);
    color: var(--success-color);
}

.indicator-status.weak {
    background: rgba(255, 107, 107, 0.2);
    color: var(--error-color);
}

.indicator-values {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.advancing,
.new-highs {
    color: var(--success-color);
    font-weight: 500;
}

.declining,
.new-lows {
    color: var(--error-color);
    font-weight: 500;
}

.volume-ratio {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
}

.indicator-strength {
    display: flex;
    justify-content: center;
    gap: 2px;
}

/* Index Patterns Table */
.patterns-table-wrapper {
    overflow: auto;
    max-height: 300px;
}

.index-patterns-table {
    width: 100%;
    font-size: 11px;
    border-collapse: collapse;
}

.index-patterns-table th {
    background: var(--bg-primary);
    padding: 8px 6px;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 10;
}

.index-patterns-table td {
    padding: 6px;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-primary);
}

.pattern-row:hover {
    background: var(--bg-hover);
}

.pattern-badge {
    padding: 2px 4px;
    border-radius: 2px;
    font-size: 9px;
    font-weight: 500;
    background: var(--bg-hover);
    color: var(--text-primary);
}

.confidence-value.conf-very-high {
    color: #51cf66;
}

.confidence-value.conf-high {
    color: #74c0fc;
}

.confidence-value.conf-medium {
    color: #ffd43b;
}

.confidence-value.conf-low {
    color: #ff8787;
}

.rs-value.rs-high {
    color: var(--success-color);
    font-weight: 600;
}

.index-chart-btn {
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 2px 4px;
    border-radius: 2px;
    cursor: pointer;
    font-size: 10px;
}

.index-chart-btn:hover {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

/* Sector Heatmap */
.heatmap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 6px;
    padding: 12px;
    max-height: 300px;
    overflow: auto;
}

.sector-tile {
    padding: 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    border: 1px solid transparent;
}

.sector-tile:hover {
    border-color: var(--accent-primary);
    transform: translateY(-1px);
}

.sector-tile.very-hot {
    background: linear-gradient(135deg, #ff6b6b, #ff5252);
    color: #fff;
}

.sector-tile.hot {
    background: linear-gradient(135deg, #ff9f43, #ff6348);
    color: #fff;
}

.sector-tile.warm {
    background: linear-gradient(135deg, #ffa726, #ff8a65);
    color: #fff;
}

.sector-tile.cool {
    background: linear-gradient(135deg, #81c784, #66bb6a);
    color: #fff;
}

.sector-tile.cold {
    background: linear-gradient(135deg, #4fc3f7, #29b6f6);
    color: #fff;
}

.sector-tile.very-cold {
    background: linear-gradient(135deg, #5c6bc0, #3f51b5);
    color: #fff;
}

.sector-name {
    font-size: 11px;
    font-weight: 500;
    margin-bottom: 2px;
    opacity: 0.9;
}

.sector-symbol {
    font-size: 10px;
    font-weight: 600;
    margin-bottom: 4px;
}

.sector-change {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 4px;
}

.sector-rs,
.sector-volume {
    font-size: 9px;
    opacity: 0.8;
    margin-bottom: 2px;
}

.sector-momentum {
    display: flex;
    gap: 2px;
    margin-top: 4px;
}

.momentum-bar {
    width: 8px;
    height: 3px;
    background: rgba(255, 255, 255, 0.3);
    border-radius: 1px;
}

.momentum-bar.filled {
    background: rgba(255, 255, 255, 0.8);
}

/* Sector Performance Lists */
.sector-performance {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 12px;
}

.hot-sectors,
.cold-sectors {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 8px;
}

.hot-sectors h5,
.cold-sectors h5 {
    margin: 0 0 8px 0;
    font-size: 11px;
    color: var(--text-primary);
    text-transform: uppercase;
    font-weight: 600;
}

.sector-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.sector-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 11px;
}

.sector-item.hot {
    background: rgba(81, 207, 102, 0.1);
    border-left: 3px solid var(--success-color);
}

.sector-item.cold {
    background: rgba(255, 107, 107, 0.1);
    border-left: 3px solid var(--error-color);
}

.sector-name {
    color: var(--text-primary);
    font-weight: 500;
}

.sector-change.positive {
    color: var(--success-color);
    font-weight: 600;
}

.sector-change.negative {
    color: var(--error-color);
    font-weight: 600;
}

/* Money Flow Analysis */
.money-flow-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 12px;
}

.flow-metric {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 8px;
    text-align: center;
}

.metric-label {
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
    margin-bottom: 4px;
}

.metric-value {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
}

/* Risk Factors */
.risk-factors {
    margin: 16px;
    background: rgba(255, 107, 107, 0.1);
    border: 1px solid var(--error-color);
    border-radius: 6px;
    padding: 12px;
}

.risk-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
}

.risk-header h4 {
    margin: 0;
    color: var(--error-color);
    font-size: 14px;
}

.risk-icon {
    font-size: 18px;
}

.risk-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.risk-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.risk-severity {
    padding: 2px 6px;
    border-radius: 2px;
    font-size: 9px;
    font-weight: 500;
    text-transform: uppercase;
}

.risk-severity.high {
    background: var(--error-color);
    color: #fff;
}

.risk-severity.medium {
    background: var(--warning-color);
    color: #000;
}

.risk-severity.low {
    background: var(--text-secondary);
    color: #fff;
}

.risk-description {
    font-size: 12px;
    color: var(--text-primary);
}

/* Responsive Design */
@media (max-width: 1200px) {
    .breadth-content-grid {
        grid-template-columns: 1fr;
    }
    
    .heatmap-grid {
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    }
}

@media (max-width: 768px) {
    .market-overview-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
    }
    
    .overall-bias {
        flex-direction: column;
        align-items: flex-start;
        gap: 4px;
    }
    
    .indices-grid {
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 6px;
    }
    
    .breadth-grid {
        gap: 8px;
    }
    
    .sector-performance {
        grid-template-columns: 1fr;
        gap: 12px;
    }
    
    .heatmap-grid {
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 4px;
    }
}
```

## Testing Strategy

### Market Breadth Testing
**File**: `tests/test_market_breadth.js`

```javascript
describe('MarketBreadth Component', () => {
    let marketBreadth;
    let container;
    
    beforeEach(() => {
        container = document.createElement('div');
        document.body.appendChild(container);
        
        // Mock fetch for API calls
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    index_patterns: [
                        {
                            symbol: 'SPY',
                            pattern_type: 'Ascending_Triangle',
                            confidence: 0.89,
                            current_price: 445.23,
                            price_change: 0.8
                        }
                    ],
                    breadth_indicators: {
                        advance_decline: {
                            advancing: 1250,
                            declining: 850,
                            status: 'Bullish',
                            strength: 3
                        }
                    },
                    sector_analysis: {
                        sectors: {
                            'XLK': {
                                name: 'Technology',
                                symbol: 'XLK',
                                price_change: 2.3,
                                relative_strength: 1.4
                            }
                        }
                    }
                })
            })
        );
        
        marketBreadth = new MarketBreadth(container);
    });
    
    afterEach(() => {
        document.body.removeChild(container);
        marketBreadth.destroy();
    });
    
    test('should render market summary correctly', async () => {
        await new Promise(resolve => setTimeout(resolve, 100)); // Wait for async load
        
        const biasValue = container.querySelector('#bias-value');
        expect(biasValue).toBeTruthy();
    });
    
    test('should display index patterns table', async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const patternsTable = container.querySelector('#index-patterns-table');
        expect(patternsTable).toBeTruthy();
        
        const rows = container.querySelectorAll('.pattern-row');
        expect(rows.length).toBeGreaterThan(0);
    });
    
    test('should render sector heatmap', async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const heatmap = container.querySelector('#sector-heatmap');
        expect(heatmap).toBeTruthy();
        
        const sectorTiles = container.querySelectorAll('.sector-tile');
        expect(sectorTiles.length).toBeGreaterThan(0);
    });
    
    test('should handle API errors gracefully', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('API Error')));
        
        const newMarketBreadth = new MarketBreadth(container);
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Should not crash and should show error handling
        expect(container.querySelector('.market-breadth')).toBeTruthy();
    });
});

describe('Market Breadth Backend', () => {
    test('should detect ascending triangle pattern', () => {
        // Mock DataFrame data
        const mockData = {
            high: [100, 101, 102, 101.5, 102, 101.8, 102, 102.1],
            low: [95, 96.5, 98, 99, 99.5, 100, 100.2, 100.5],
            close: [98, 99, 100, 100.5, 101, 101.2, 101.5, 101.8],
            volume: [1000000, 1200000, 800000, 900000, 700000, 650000, 600000, 550000]
        };
        
        // Test pattern detection logic
        const detector = new MarketBreadthDetector();
        // Implementation would test the actual pattern detection methods
    });
});
```

## Performance Benchmarks

### Market Breadth Performance Targets
- **Initial load**: <2 seconds
- **Index pattern updates**: <25ms per query
- **Sector heatmap render**: <100ms
- **Real-time updates**: 30 second intervals
- **Memory usage**: <50MB for all market data

## Deployment Checklist

- [ ] Market breadth API endpoints operational
- [ ] Index pattern detection working with live data
- [ ] Sector rotation analysis functional
- [ ] Breadth indicators calculating correctly
- [ ] Real-time updates working every 30 seconds
- [ ] Responsive design working on all devices
- [ ] Error handling for API failures
- [ ] Performance targets met for all operations
- [ ] Integration with GoldenLayout tab system
- [ ] Visual indicators and heatmap rendering correctly

## Next Phase Handoff

**Phase 5 Prerequisites:**
- Market breadth analysis fully operational
- Index and sector pattern detection working
- Real-time breadth indicators functional
- Visual heatmap and performance metrics displaying

**Market Context Ready For:**
- Personal watchlist integration with market context
- Advanced alert system based on market conditions
- Portfolio correlation with market breadth
- Enhanced pattern filtering based on market regime

This implementation provides comprehensive market context that enhances individual pattern analysis with broader market intelligence, enabling more strategic trading decisions.