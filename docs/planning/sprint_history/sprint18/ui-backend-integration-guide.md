# UI-Backend Integration Guide for TickStock.ai Pattern Discovery Dashboard

**Date**: 2025-09-04  
**Sprint**: 18 - Planning Phase  
**Status**: Technical Integration Specification  
**Source**: Incorporated feedback from Super Algorithmic Pattern Library Curator  

## Overview

This guide bridges the front-end design (per `efficient-pattern-scanner-design.md` and related docs) with our Python-based pattern library, ensuring seamless data flow from TimescaleDB-stored patterns/indicators to the UI's high-density tables, filters, and charts. We leverage Flask for REST/WebSocket APIs, SQLAlchemy for queries, and polygon-api-client for fundamental correlations, aligning with our three-tiered architecture and <50ms query goals.

## Key Integration Points

### 1. Pattern Scanner Tab: Unified Data Feed

#### Backend Support
- **Query all tiers** via a unified endpoint, pulling from `daily_patterns`, `intraday_patterns`, and `daily_intraday_patterns`
- **Filter mapping**: UI filters (e.g., RS >1.0, Pattern Type: Breakouts) translate to SQL WHERE clauses
- **Dense table population**: Return abbreviated data (e.g., "WeeklyBO" for pattern) with JSON serialization for efficiency

#### Flask API Implementation

**File: `src/api/pattern_scanner.py`**
```python
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app import db  # SQLAlchemy session

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route('/api/patterns/scan', methods=['GET'])
def scan_patterns():
    """
    Unified pattern scanning endpoint supporting all UI filters.
    
    Query Parameters:
    - pattern_types: List of pattern types to include
    - rs_min: Minimum relative strength filter
    - vol_min: Minimum volume multiple filter  
    - timeframe: All, Daily, Intraday, Combo
    - page, per_page: Pagination controls
    """
    # Parse filters from query params
    pattern_types = request.args.getlist('pattern_types')  # e.g., ['Breakouts', 'Volume']
    rs_min = float(request.args.get('rs_min', 0))
    vol_min = float(request.args.get('vol_min', 0))
    confidence_min = float(request.args.get('confidence_min', 0.5))
    timeframe = request.args.get('timeframe', 'All')  # All, Daily, Intraday, Combo
    
    # Build dynamic SQL for unified view
    base_query = """
    SELECT symbol, pattern_type AS pattern, confidence AS conf,
           jsonb_extract_path_text(indicators, 'relative_strength') AS rs,
           jsonb_extract_path_text(indicators, 'relative_volume') AS vol,
           current_price AS price, price_change AS chg,
           detected_at AS time, expiration AS exp,
           'daily' as source
    FROM daily_patterns
    WHERE confidence > :confidence_min
    
    UNION ALL
    
    SELECT symbol, pattern_type AS pattern, confidence AS conf,
           jsonb_extract_path_text(indicators, 'relative_strength') AS rs,
           jsonb_extract_path_text(indicators, 'relative_volume') AS vol,
           current_price AS price, price_change AS chg,
           detected_at AS time, expiration AS exp,
           'intraday' as source
    FROM intraday_patterns  
    WHERE confidence > :confidence_min
    
    UNION ALL
    
    SELECT symbol, pattern_type AS pattern, confidence AS conf,
           jsonb_extract_path_text(combo_indicators, 'relative_strength_surge') AS rs,
           jsonb_extract_path_text(combo_indicators, 'relative_volume') AS vol,
           current_price AS price, price_change AS chg,
           detected_at AS time, expiration AS exp,
           'combo' as source
    FROM daily_intraday_patterns
    WHERE confidence > :confidence_min
    """
    
    params = {'confidence_min': confidence_min}
    
    # Add dynamic filters
    conditions = []
    if pattern_types:
        conditions.append("pattern_type = ANY(:pattern_types)")
        params['pattern_types'] = pattern_types
    if rs_min > 0:
        conditions.append("CAST(jsonb_extract_path_text(indicators, 'relative_strength') AS FLOAT) > :rs_min")
        params['rs_min'] = rs_min
    if vol_min > 0:
        conditions.append("CAST(jsonb_extract_path_text(indicators, 'relative_volume') AS FLOAT) > :vol_min")
        params['vol_min'] = vol_min
    if timeframe != 'All':
        conditions.append("source = :timeframe")
        params['timeframe'] = timeframe.lower()
    
    # Wrap unified query with additional filters
    if conditions:
        final_query = f"""
        SELECT * FROM ({base_query}) AS unified 
        WHERE {' AND '.join(conditions)}
        """
    else:
        final_query = f"SELECT * FROM ({base_query}) AS unified"
        
    # Add pagination and ordering
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 30))
    final_query += " ORDER BY conf DESC, time DESC LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = (page - 1) * per_page

    # Execute query
    result = db.session.execute(text(final_query), params).fetchall()
    patterns = [dict(row) for row in result]

    # Enhanced: Correlate with fundamentals (boost confidence with EPS surprises)
    from polygon_api_client import PolygonClient
    client = PolygonClient()  # Assume initialized
    for p in patterns:
        try:
            financials = client.list_stock_financials(p['symbol'], limit=1)
            if financials and len(financials) > 0:
                eps_surprise = financials[0].get('eps_surprise', 0)
                if eps_surprise > 0:
                    p['conf'] = min(0.99, float(p['conf']) + 0.05)  # Boost confidence
                    p['fundamental_boost'] = True
        except Exception:
            pass  # Graceful degradation if fundamentals unavailable
            
    # Get total count for pagination
    count_query = f"SELECT COUNT(*) FROM ({final_query.split('LIMIT')[0]}) AS count_unified"
    total_count = db.session.execute(text(count_query), {k:v for k,v in params.items() if k not in ['limit', 'offset']}).scalar()

    return jsonify({
        'patterns': patterns, 
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'pages': (total_count + per_page - 1) // per_page
    })
```

#### Performance Optimization
- **TimescaleDB indexes**: Create on `symbol`, `pattern_type`, `confidence`, `detected_at`
- **Redis caching**: Cache hot queries for 30-60 seconds
- **Query optimization**: Use materialized views for complex joins

**Database Indexes (TimescaleDB)**:
```sql
-- Core pattern table indexes
CREATE INDEX CONCURRENTLY idx_daily_patterns_symbol_type_conf 
ON daily_patterns (symbol, pattern_type, confidence DESC);

CREATE INDEX CONCURRENTLY idx_daily_patterns_detected_at 
ON daily_patterns (detected_at DESC);

CREATE INDEX CONCURRENTLY idx_daily_patterns_indicators_gin 
ON daily_patterns USING GIN (indicators);

-- Similar indexes for intraday_patterns and daily_intraday_patterns
-- Replicate above pattern for other tables
```

### 2. Market Breadth Tab: Index/ETF Analysis

#### Backend Support  
- **Dedicated endpoint** for ETF patterns (SPY, QQQ) and sector aggregations
- **Heatmap data**: Aggregate RS/Vol from indicators for sector visualization
- **Real-time index monitoring**: WebSocket updates for major indices

#### Market Breadth Detector Implementation

**File: `src/analysis/market_breadth_detector.py`**
```python
import pandas as pd
import numpy as np
from polygon_api_client import PolygonClient
from typing import List, Dict
from datetime import datetime, timedelta

class MarketBreadthDetector:
    """
    Detects patterns on market indices and ETFs for breadth analysis.
    Integrates with TickStockPL pattern detection engines.
    """
    
    def __init__(self, client: PolygonClient):
        self.client = client
        self.major_indices = ['SPY', 'QQQ', 'IWM', 'DIA']
        self.sector_etfs = {
            'XLK': 'Technology',
            'XLF': 'Finance', 
            'XLE': 'Energy',
            'XLV': 'Healthcare',
            'XLI': 'Industrial',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLU': 'Utilities'
        }

    def detect_index_patterns(self, timeframe='Daily') -> List[Dict]:
        """Detect patterns on major market indices."""
        patterns = []
        
        # Date range for analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)  # 60-day lookback
        
        for index in self.major_indices:
            try:
                # Get historical data
                aggs = self.client.list_aggs(
                    index, 1, 'day', 
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
                
                if len(aggs) < 20:  # Need minimum data points
                    continue
                    
                df = pd.DataFrame(aggs)
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df.sort_values('date')
                
                # Detect Ascending Triangle pattern
                pattern = self._detect_ascending_triangle(df, index)
                if pattern:
                    patterns.append(pattern)
                    
                # Detect Bull Flag pattern  
                pattern = self._detect_bull_flag(df, index)
                if pattern:
                    patterns.append(pattern)
                    
                # Detect Support/Resistance breaks
                pattern = self._detect_support_resistance(df, index)
                if pattern:
                    patterns.append(pattern)
                    
            except Exception as e:
                print(f"Error detecting patterns for {index}: {e}")
                continue
                
        return patterns

    def _detect_ascending_triangle(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Detect ascending triangle: converging highs and rising lows."""
        if len(df) < 20:
            return None
            
        # Get recent highs and lows
        recent_data = df.tail(20)
        highs = recent_data['high'].values
        lows = recent_data['low'].values
        
        # Fit trend lines
        x = np.arange(len(highs))
        high_slope = np.polyfit(x, highs, 1)[0]
        low_slope = np.polyfit(x, lows, 1)[0]
        
        # Ascending triangle: flat/declining highs, rising lows
        if high_slope <= 0.01 and low_slope > 0.02:
            resistance_level = np.max(highs[-10:])  # Recent resistance
            current_price = df.iloc[-1]['close']
            
            # Calculate relative strength vs SPY (if not SPY itself)
            rs = self._calculate_relative_strength(symbol, df) if symbol != 'SPY' else 1.0
            
            # Volume analysis
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            recent_volume = df['volume'].iloc[-1]
            vol_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            confidence = 0.85 + (0.1 if rs > 1.0 else 0) + (0.05 if vol_ratio > 1.5 else 0)
            confidence = min(0.99, confidence)
            
            return {
                'symbol': symbol,
                'pattern': 'AscTriangle',
                'timeframe': 'Daily',
                'conf': round(confidence, 2),
                'rs': round(rs, 2),
                'vol': round(vol_ratio, 1),
                'price': round(current_price, 2),
                'key_levels': {
                    'resistance': round(resistance_level, 2),
                    'target': round(resistance_level * 1.05, 2)  # 5% above resistance
                }
            }
        return None

    def _detect_bull_flag(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Detect bull flag: strong uptrend followed by consolidation."""
        if len(df) < 15:
            return None
            
        # Look for strong recent uptrend (flagpole)
        flagpole_data = df.tail(15).head(10)  # Days -15 to -5
        consolidation_data = df.tail(5)       # Last 5 days
        
        flagpole_return = (flagpole_data['close'].iloc[-1] / flagpole_data['close'].iloc[0] - 1)
        
        # Bull flag criteria: strong uptrend (>5%) + consolidation
        if flagpole_return > 0.05:  # 5% uptrend in flagpole
            consolidation_range = (consolidation_data['high'].max() / consolidation_data['low'].min() - 1)
            
            if consolidation_range < 0.08:  # Tight consolidation (<8% range)
                current_price = df.iloc[-1]['close']
                rs = self._calculate_relative_strength(symbol, df) if symbol != 'SPY' else 1.0
                
                # Volume should decline in consolidation
                avg_flagpole_vol = flagpole_data['volume'].mean()
                avg_consolidation_vol = consolidation_data['volume'].mean()
                vol_decline = avg_consolidation_vol / avg_flagpole_vol if avg_flagpole_vol > 0 else 1.0
                
                confidence = 0.88 + (0.07 if vol_decline < 0.8 else 0) + (0.05 if rs > 1.1 else 0)
                confidence = min(0.99, confidence)
                
                breakout_level = consolidation_data['high'].max()
                
                return {
                    'symbol': symbol,
                    'pattern': 'BullFlag',
                    'timeframe': 'Daily', 
                    'conf': round(confidence, 2),
                    'rs': round(rs, 2),
                    'vol': round(1 / vol_decline, 1),  # Invert for display
                    'price': round(current_price, 2),
                    'key_levels': {
                        'breakout': round(breakout_level, 2),
                        'target': round(breakout_level * (1 + flagpole_return), 2)
                    }
                }
        return None

    def _calculate_relative_strength(self, symbol: str, df: pd.DataFrame) -> float:
        """Calculate relative strength vs SPY benchmark."""
        if symbol == 'SPY':
            return 1.0
            
        try:
            # Get SPY data for same period
            spy_aggs = self.client.list_aggs(
                'SPY', 1, 'day',
                df['date'].min().strftime('%Y-%m-%d'),
                df['date'].max().strftime('%Y-%m-%d')
            )
            spy_df = pd.DataFrame(spy_aggs)
            
            # Calculate 20-day returns
            symbol_return = df['close'].pct_change(20).iloc[-1]
            spy_return = spy_df['close'].pct_change(20).iloc[-1] if len(spy_df) > 20 else 0
            
            if spy_return != 0:
                return (1 + symbol_return) / (1 + spy_return)
            return 1.0
            
        except Exception:
            return 1.0

    def get_sector_heatmap_data(self) -> Dict:
        """Generate sector performance heatmap data."""
        sector_data = {}
        
        for etf, sector_name in self.sector_etfs.items():
            try:
                # Get recent performance data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=5)  # 5-day performance
                
                aggs = self.client.list_aggs(
                    etf, 1, 'day',
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if len(aggs) >= 2:
                    df = pd.DataFrame(aggs)
                    performance = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
                    
                    sector_data[etf] = {
                        'name': sector_name,
                        'performance': round(performance, 1),
                        'current_price': round(df['close'].iloc[-1], 2),
                        'volume_ratio': round(df['volume'].iloc[-1] / df['volume'].mean(), 1)
                    }
                    
            except Exception as e:
                print(f"Error getting sector data for {etf}: {e}")
                
        return sector_data
```

#### Market Breadth API Endpoint

**File: `src/api/market_breadth.py`**
```python
from flask import Blueprint, jsonify
from src.analysis.market_breadth_detector import MarketBreadthDetector
from polygon_api_client import PolygonClient

breadth_bp = Blueprint('breadth', __name__)

@breadth_bp.route('/api/market/breadth', methods=['GET'])
def get_market_breadth():
    """Get comprehensive market breadth data."""
    try:
        client = PolygonClient()  # Initialize with API key
        detector = MarketBreadthDetector(client)
        
        # Get index patterns
        index_patterns = detector.detect_index_patterns()
        
        # Get sector heatmap data
        sector_data = detector.get_sector_heatmap_data()
        
        # Calculate market breadth indicators (simplified)
        breadth_indicators = {
            'advance_decline': 'Bullish',  # Would calculate from actual market data
            'new_highs_lows': 'Neutral',
            'up_volume': 'Strong'
        }
        
        return jsonify({
            'index_patterns': index_patterns,
            'sector_heatmap': sector_data,
            'breadth_indicators': breadth_indicators,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 3. My Focus Tab: Watchlists and Real-Time Alerts

#### WebSocket Implementation for Live Updates

**File: `src/api/websockets.py`**
```python
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from app import socketio, db
from sqlalchemy import text
import json

@socketio.on('subscribe_watchlist')
def handle_watchlist_subscription(data):
    """Subscribe to real-time updates for user's watchlist symbols."""
    try:
        user_id = data.get('user_id')
        watchlist_id = data.get('watchlist_id')
        symbols = data.get('symbols', [])
        
        # Join room for this watchlist
        room_name = f"watchlist_{user_id}_{watchlist_id}"
        join_room(room_name)
        
        # Send initial pattern data
        initial_patterns = get_watchlist_patterns(symbols)
        emit('watchlist_patterns', {
            'patterns': initial_patterns,
            'watchlist_id': watchlist_id
        })
        
        emit('subscription_confirmed', {
            'watchlist_id': watchlist_id,
            'symbols': symbols,
            'room': room_name
        })
        
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('unsubscribe_watchlist') 
def handle_watchlist_unsubscription(data):
    """Unsubscribe from watchlist updates."""
    user_id = data.get('user_id')
    watchlist_id = data.get('watchlist_id')
    room_name = f"watchlist_{user_id}_{watchlist_id}"
    leave_room(room_name)
    emit('unsubscription_confirmed', {'watchlist_id': watchlist_id})

def get_watchlist_patterns(symbols):
    """Get current patterns for watchlist symbols."""
    if not symbols:
        return []
        
    query = """
    SELECT symbol, pattern_type AS pattern, confidence AS conf,
           jsonb_extract_path_text(indicators, 'relative_strength') AS rs,
           jsonb_extract_path_text(indicators, 'relative_volume') AS vol,
           current_price AS price, price_change AS chg,
           detected_at AS time, expiration AS exp
    FROM (
        SELECT * FROM daily_patterns WHERE symbol = ANY(:symbols)
        UNION
        SELECT * FROM intraday_patterns WHERE symbol = ANY(:symbols) 
        UNION  
        SELECT * FROM daily_intraday_patterns WHERE symbol = ANY(:symbols)
    ) AS watchlist_patterns
    ORDER BY confidence DESC, detected_at DESC
    """
    
    result = db.session.execute(text(query), {'symbols': symbols}).fetchall()
    return [dict(row) for row in result]

# Background task to push real-time pattern updates
def push_pattern_updates():
    """Background task to push pattern updates to subscribed clients."""
    # This would be called by the pattern detection engines
    # when new patterns are detected or updated
    
    # Example: Get all active watchlists and check for new patterns
    active_rooms = socketio.server.manager.get_rooms()
    
    for room in active_rooms:
        if room.startswith('watchlist_'):
            try:
                # Parse room name to get user_id and watchlist_id
                parts = room.split('_')
                user_id, watchlist_id = parts[1], parts[2]
                
                # Get symbols for this watchlist (would query user_watchlists table)
                symbols = get_watchlist_symbols(user_id, watchlist_id)
                
                # Get latest patterns
                new_patterns = get_watchlist_patterns(symbols)
                
                # Emit updates to room
                socketio.emit('pattern_update', {
                    'patterns': new_patterns,
                    'watchlist_id': watchlist_id,
                    'timestamp': datetime.now().isoformat()
                }, room=room)
                
            except Exception as e:
                print(f"Error pushing updates to room {room}: {e}")

def get_watchlist_symbols(user_id, watchlist_id):
    """Get symbols for a user's watchlist."""
    # This would query the user_watchlists table
    # Placeholder implementation
    return ['AAPL', 'NVDA', 'MSFT']  # Example symbols
```

## Performance Benchmarking & Validation

### Query Performance Targets
- **Pattern scan queries**: <50ms for 1,000+ patterns
- **Market breadth updates**: <25ms for all indices
- **Watchlist updates**: <10ms for 50 symbols max

### Testing Framework

**File: `tests/api/test_performance.py`**
```python
import pytest
import time
from flask import Flask
from src.api.pattern_scanner import scanner_bp

def test_pattern_scan_performance(client):
    """Test pattern scanning API performance."""
    start_time = time.time()
    
    response = client.get('/api/patterns/scan', query_string={
        'pattern_types': ['Breakouts', 'Volume'],
        'rs_min': 1.0,
        'per_page': 100
    })
    
    elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
    
    assert response.status_code == 200
    assert elapsed_time < 50  # Must be under 50ms
    
    data = response.get_json()
    assert 'patterns' in data
    assert len(data['patterns']) <= 100

@pytest.mark.benchmark
def test_unified_query_benchmark(benchmark, client):
    """Benchmark the unified pattern query."""
    def query_patterns():
        return client.get('/api/patterns/scan', query_string={
            'pattern_types': ['Breakouts'],
            'rs_min': 1.2,
            'vol_min': 1.5,
            'per_page': 50
        })
    
    result = benchmark(query_patterns)
    assert result.status_code == 200
```

### FMV Integration for Pattern Accuracy
Following the FMV Whitepaper methodology for low-error predictions:

```python
def validate_pattern_accuracy(symbol, pattern_data):
    """Validate pattern accuracy against FMV next-trade predictions."""
    try:
        # Get FMV next-trade price prediction
        fmv_prediction = get_fmv_prediction(symbol)  # From FMV calculation
        actual_next_price = get_next_trade_price(symbol)  # From Polygon
        
        # Calculate prediction error
        error = abs(fmv_prediction - actual_next_price) / actual_next_price * 100
        
        # Target <5% error rate per whitepaper
        if error < 5.0:
            pattern_data['accuracy_validated'] = True
            pattern_data['prediction_error'] = error
        else:
            pattern_data['accuracy_validated'] = False
            
        return pattern_data
        
    except Exception:
        pattern_data['accuracy_validated'] = None
        return pattern_data
```

## Next Steps for Implementation

1. **Database Setup**: Create indexes and materialized views for optimal query performance
2. **API Development**: Implement Flask endpoints with the provided code examples  
3. **WebSocket Integration**: Set up real-time pattern update broadcasting
4. **Performance Testing**: Establish benchmarking with <50ms targets
5. **Chart Integration**: Develop matplotlib-based pattern overlays for GoldenLayout
6. **Fundamental Data**: Integrate Polygon fundamentals API for pattern confidence boosting

This integration ensures our pattern library drives a responsive, data-rich UI that transforms pre-computed patterns into actionable trading insights with sub-50ms performance and real-time updates.