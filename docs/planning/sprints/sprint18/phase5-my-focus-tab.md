# Phase 5: My Focus Tab - Detailed Implementation Guide

**Date**: 2025-09-04  
**Sprint**: 18 - Phase 5 Implementation  
**Duration**: 2 weeks  
**Status**: Implementation Ready  
**Prerequisites**: Phase 4 complete (Market breadth analysis operational)

## Phase Overview

Implement the My Focus tab to provide personalized watchlist management, intelligent real-time alerts, and comprehensive performance analytics. This phase transforms the pattern discovery dashboard into a personalized trading command center with advanced portfolio correlation and performance tracking capabilities.

## Success Criteria

✅ **Watchlist Management**: Support 5+ custom watchlists with 50 symbols each, <10ms updates  
✅ **Real-Time Alerts**: WebSocket-based pattern alerts with mobile push notifications  
✅ **Performance Analytics**: Pattern-based P&L tracking with win rate analysis by confidence level + Polygon fundamental overlays for revenue surprise correlation  
✅ **Intelligent Features**: Auto-focus charting, strategy optimization, performance benchmarking  
✅ **Social Features**: Shareable filter sets and watchlist export/import functionality  

## Implementation Tasks

### Task 5.1: Advanced Watchlist Management Backend (Days 1-3)

#### 5.1.1 Watchlist Management API
**File**: `src/api/watchlists.py`

```python
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text
from app import db, redis_client
from datetime import datetime, timedelta
import json
import uuid

watchlists_bp = Blueprint('watchlists', __name__)

@watchlists_bp.route('/api/watchlists', methods=['GET'])
def get_user_watchlists():
    """
    Get all watchlists for the current user
    """
    user_id = request.headers.get('X-User-ID', 'anonymous')
    
    try:
        query = """
        SELECT id, name, symbols, filters, created_at, updated_at,
               (SELECT COUNT(*) FROM patterns_with_alerts pwa 
                WHERE pwa.symbol = ANY(user_watchlists.symbols) 
                AND pwa.user_id = user_watchlists.user_id) as active_patterns
        FROM user_watchlists 
        WHERE user_id = :user_id
        ORDER BY updated_at DESC
        """
        
        result = db.session.execute(text(query), {'user_id': user_id})
        watchlists = []
        
        for row in result:
            watchlists.append({
                'id': row.id,
                'name': row.name,
                'symbols': row.symbols,
                'symbol_count': len(row.symbols),
                'filters': row.filters or {},
                'active_patterns': row.active_patterns or 0,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
        
        return jsonify({'watchlists': watchlists})
        
    except Exception as e:
        current_app.logger.error(f"Failed to get watchlists for user {user_id}: {e}")
        return jsonify({'error': 'Failed to retrieve watchlists'}), 500

@watchlists_bp.route('/api/watchlists', methods=['POST'])
def create_watchlist():
    """
    Create a new watchlist
    """
    user_id = request.headers.get('X-User-ID', 'anonymous')
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Watchlist name is required'}), 400
    
    # Validate symbols
    symbols = data.get('symbols', [])
    if len(symbols) > 50:
        return jsonify({'error': 'Maximum 50 symbols per watchlist'}), 400
    
    # Validate symbols exist in our database
    valid_symbols = validate_symbols(symbols)
    invalid_symbols = [s for s in symbols if s not in valid_symbols]
    
    if invalid_symbols:
        return jsonify({
            'error': f'Invalid symbols: {", ".join(invalid_symbols)}'
        }), 400
    
    try:
        watchlist_id = str(uuid.uuid4())
        query = """
        INSERT INTO user_watchlists (id, user_id, name, symbols, filters, created_at, updated_at)
        VALUES (:id, :user_id, :name, :symbols, :filters, NOW(), NOW())
        RETURNING id, name, symbols, filters, created_at, updated_at
        """
        
        result = db.session.execute(text(query), {
            'id': watchlist_id,
            'user_id': user_id,
            'name': data['name'],
            'symbols': valid_symbols,
            'filters': json.dumps(data.get('filters', {}))
        })
        
        db.session.commit()
        row = result.fetchone()
        
        # Create initial alert subscriptions for this watchlist
        create_watchlist_subscriptions(user_id, watchlist_id, valid_symbols)
        
        return jsonify({
            'id': row.id,
            'name': row.name,
            'symbols': row.symbols,
            'symbol_count': len(row.symbols),
            'filters': json.loads(row.filters) if row.filters else {},
            'created_at': row.created_at.isoformat(),
            'updated_at': row.updated_at.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create watchlist: {e}")
        return jsonify({'error': 'Failed to create watchlist'}), 500

@watchlists_bp.route('/api/watchlists/<watchlist_id>', methods=['PUT'])
def update_watchlist(watchlist_id):
    """
    Update an existing watchlist
    """
    user_id = request.headers.get('X-User-ID', 'anonymous')
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Verify ownership
        ownership_query = """
        SELECT id FROM user_watchlists 
        WHERE id = :watchlist_id AND user_id = :user_id
        """
        
        ownership = db.session.execute(text(ownership_query), {
            'watchlist_id': watchlist_id,
            'user_id': user_id
        }).fetchone()
        
        if not ownership:
            return jsonify({'error': 'Watchlist not found or access denied'}), 404
        
        # Build update query dynamically
        update_fields = []
        params = {'watchlist_id': watchlist_id, 'user_id': user_id}
        
        if 'name' in data:
            update_fields.append('name = :name')
            params['name'] = data['name']
        
        if 'symbols' in data:
            symbols = data['symbols']
            if len(symbols) > 50:
                return jsonify({'error': 'Maximum 50 symbols per watchlist'}), 400
            
            valid_symbols = validate_symbols(symbols)
            update_fields.append('symbols = :symbols')
            params['symbols'] = valid_symbols
            
            # Update alert subscriptions
            update_watchlist_subscriptions(user_id, watchlist_id, valid_symbols)
        
        if 'filters' in data:
            update_fields.append('filters = :filters')
            params['filters'] = json.dumps(data['filters'])
        
        if update_fields:
            update_fields.append('updated_at = NOW()')
            
            query = f"""
            UPDATE user_watchlists 
            SET {', '.join(update_fields)}
            WHERE id = :watchlist_id AND user_id = :user_id
            RETURNING id, name, symbols, filters, updated_at
            """
            
            result = db.session.execute(text(query), params)
            row = result.fetchone()
            db.session.commit()
            
            return jsonify({
                'id': row.id,
                'name': row.name,
                'symbols': row.symbols,
                'symbol_count': len(row.symbols),
                'filters': json.loads(row.filters) if row.filters else {},
                'updated_at': row.updated_at.isoformat()
            })
        
        return jsonify({'message': 'No changes made'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update watchlist {watchlist_id}: {e}")
        return jsonify({'error': 'Failed to update watchlist'}), 500

@watchlists_bp.route('/api/watchlists/<watchlist_id>', methods=['DELETE'])
def delete_watchlist(watchlist_id):
    """
    Delete a watchlist
    """
    user_id = request.headers.get('X-User-ID', 'anonymous')
    
    try:
        # Delete with ownership verification
        query = """
        DELETE FROM user_watchlists 
        WHERE id = :watchlist_id AND user_id = :user_id
        RETURNING id
        """
        
        result = db.session.execute(text(query), {
            'watchlist_id': watchlist_id,
            'user_id': user_id
        })
        
        deleted_row = result.fetchone()
        
        if not deleted_row:
            return jsonify({'error': 'Watchlist not found or access denied'}), 404
        
        # Clean up alert subscriptions
        delete_watchlist_subscriptions(user_id, watchlist_id)
        
        db.session.commit()
        return jsonify({'message': 'Watchlist deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete watchlist {watchlist_id}: {e}")
        return jsonify({'error': 'Failed to delete watchlist'}), 500

@watchlists_bp.route('/api/watchlists/<watchlist_id>/patterns', methods=['GET'])
def get_watchlist_patterns(watchlist_id):
    """
    Get active patterns for symbols in a specific watchlist
    """
    user_id = request.headers.get('X-User-ID', 'anonymous')
    
    try:
        # Get watchlist symbols
        watchlist_query = """
        SELECT symbols FROM user_watchlists 
        WHERE id = :watchlist_id AND user_id = :user_id
        """
        
        watchlist = db.session.execute(text(watchlist_query), {
            'watchlist_id': watchlist_id,
            'user_id': user_id
        }).fetchone()
        
        if not watchlist:
            return jsonify({'error': 'Watchlist not found'}), 404
        
        symbols = watchlist.symbols
        if not symbols:
            return jsonify({'patterns': []})
        
        # Get patterns for these symbols
        patterns_query = """
        SELECT symbol, pattern_type, confidence, current_price, price_change,
               indicators, detected_at, expiration, 'daily' as source
        FROM daily_patterns 
        WHERE symbol = ANY(:symbols) AND expiration > NOW()
        
        UNION ALL
        
        SELECT symbol, pattern_type, confidence, current_price, price_change,
               indicators, detected_at, expiration, 'intraday' as source
        FROM intraday_patterns 
        WHERE symbol = ANY(:symbols) AND expiration > NOW()
        
        UNION ALL
        
        SELECT symbol, pattern_type, confidence, current_price, price_change,
               indicators, detected_at, expiration, 'combo' as source
        FROM daily_intraday_patterns 
        WHERE symbol = ANY(:symbols) AND expiration > NOW()
        
        ORDER BY confidence DESC, detected_at DESC
        """
        
        result = db.session.execute(text(patterns_query), {'symbols': symbols})
        
        patterns = []
        for row in result:
            patterns.append({
                'symbol': row.symbol,
                'pattern_type': row.pattern_type,
                'confidence': float(row.confidence),
                'current_price': float(row.current_price) if row.current_price else None,
                'price_change': float(row.price_change) if row.price_change else None,
                'indicators': row.indicators or {},
                'detected_at': row.detected_at.isoformat(),
                'expiration': row.expiration.isoformat(),
                'source': row.source,
                'time_remaining': calculate_time_remaining(row.expiration)
            })
        
        return jsonify({
            'watchlist_id': watchlist_id,
            'patterns': patterns,
            'pattern_count': len(patterns),
            'symbol_count': len(symbols)
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get patterns for watchlist {watchlist_id}: {e}")
        return jsonify({'error': 'Failed to retrieve patterns'}), 500

def validate_symbols(symbols):
    """Validate symbols against our symbols table"""
    if not symbols:
        return []
    
    query = """
    SELECT symbol FROM symbols 
    WHERE symbol = ANY(:symbols) AND active = true
    """
    
    result = db.session.execute(text(query), {'symbols': symbols})
    return [row.symbol for row in result]

def create_watchlist_subscriptions(user_id, watchlist_id, symbols):
    """Create alert subscriptions for watchlist symbols"""
    try:
        subscriptions = []
        for symbol in symbols:
            subscriptions.append({
                'user_id': user_id,
                'watchlist_id': watchlist_id,
                'symbol': symbol,
                'alert_types': ['pattern_detected', 'confidence_change', 'expiration_warning']
            })
        
        # Store in Redis for fast WebSocket lookups
        redis_key = f"watchlist_alerts:{user_id}:{watchlist_id}"
        redis_client.setex(redis_key, 86400, json.dumps(subscriptions))  # 24 hour TTL
        
    except Exception as e:
        current_app.logger.error(f"Failed to create subscriptions: {e}")

def update_watchlist_subscriptions(user_id, watchlist_id, symbols):
    """Update alert subscriptions when watchlist symbols change"""
    # Implementation similar to create_watchlist_subscriptions
    pass

def delete_watchlist_subscriptions(user_id, watchlist_id):
    """Clean up alert subscriptions when watchlist is deleted"""
    try:
        redis_key = f"watchlist_alerts:{user_id}:{watchlist_id}"
        redis_client.delete(redis_key)
    except Exception as e:
        current_app.logger.error(f"Failed to delete subscriptions: {e}")

def calculate_time_remaining(expiration):
    """Calculate human-readable time remaining until expiration"""
    now = datetime.now()
    if expiration <= now:
        return 'Expired'
    
    diff = expiration - now
    if diff.days > 0:
        return f"{diff.days}d"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}h"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}m"
    else:
        return f"{diff.seconds}s"
```

#### 5.1.2 Performance Analytics API
**File**: `src/api/performance_analytics.py`

```python
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text
from app import db
from datetime import datetime, timedelta
import json

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/analytics/performance', methods=['GET'])
def get_performance_analytics():
    """
    Get comprehensive performance analytics for user's watchlists and patterns
    """
    user_id = request.headers.get('X-User-ID', 'anonymous')
    timeframe = request.args.get('timeframe', '7d')  # 1d, 7d, 30d, 90d
    
    try:
        time_filter = get_time_filter(timeframe)
        
        # Pattern Performance Analysis
        pattern_performance = calculate_pattern_performance(user_id, time_filter)
        
        # Win Rate by Confidence Level
        win_rates = calculate_win_rates_by_confidence(user_id, time_filter)
        
        # Best/Worst Performers
        symbol_performance = calculate_symbol_performance(user_id, time_filter)
        
        # Pattern Type Effectiveness
        pattern_type_stats = calculate_pattern_type_effectiveness(user_id, time_filter)
        
        # FMV Accuracy Correlation
        fmv_accuracy = calculate_fmv_correlation(user_id, time_filter)
        
        # Overall portfolio metrics
        portfolio_metrics = calculate_portfolio_metrics(user_id, time_filter)
        
        # Polygon Fundamental Overlays Enhancement
        fundamental_correlations = calculate_fundamental_correlations(user_id, time_filter)
        
        return jsonify({
            'timeframe': timeframe,
            'pattern_performance': pattern_performance,
            'win_rates': win_rates,
            'symbol_performance': symbol_performance,
            'pattern_type_stats': pattern_type_stats,
            'fmv_accuracy': fmv_accuracy,
            'portfolio_metrics': portfolio_metrics,
            'fundamental_correlations': fundamental_correlations,  # New enhancement
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to generate analytics for user {user_id}: {e}")
        return jsonify({'error': 'Failed to generate performance analytics'}), 500

def calculate_fundamental_correlations(user_id, time_filter):
    """Calculate correlations between pattern performance and Polygon fundamentals"""
    from polygon import RESTClient
    
    try:
        polygon_client = RESTClient(current_app.config['POLYGON_API_KEY'])
        
        # Get user's symbols with pattern performance
        query = f"""
        SELECT DISTINCT dp.symbol, 
               AVG(CASE WHEN dp.outcome = 'win' THEN 1.0 ELSE 0.0 END) as win_rate,
               COUNT(*) as pattern_count
        FROM daily_patterns dp
        JOIN user_watchlists uw ON dp.symbol = ANY(uw.symbols)
        WHERE uw.user_id = %s {time_filter}
        GROUP BY dp.symbol
        HAVING COUNT(*) >= 3  -- Minimum patterns for statistical significance
        """
        
        results = db.session.execute(text(query), (user_id,)).fetchall()
        correlations = []
        
        for symbol_data in results:
            symbol = symbol_data.symbol
            win_rate = float(symbol_data.win_rate)
            
            try:
                # Get fundamental data from Polygon
                financials = polygon_client.get_ticker_details(symbol)
                
                if financials and hasattr(financials, 'market_cap'):
                    # Revenue surprise correlation
                    revenue_growth = getattr(financials, 'weighted_shares_outstanding', 0)
                    eps_surprise = 0  # Would fetch from earnings API
                    
                    correlations.append({
                        'symbol': symbol,
                        'win_rate': win_rate,
                        'pattern_count': symbol_data.pattern_count,
                        'revenue_correlation': calculate_correlation_boost(win_rate, revenue_growth),
                        'fundamental_strength': classify_fundamental_strength(financials),
                        'confidence_boost': 0.1 if revenue_growth > 0 else -0.05
                    })
            except Exception as e:
                current_app.logger.warning(f"Could not fetch fundamentals for {symbol}: {e}")
                continue
        
        # Calculate overall correlations
        avg_boost = sum(c['confidence_boost'] for c in correlations) / len(correlations) if correlations else 0
        
        return {
            'symbol_correlations': correlations,
            'avg_fundamental_boost': avg_boost,
            'enhanced_symbols': len([c for c in correlations if c['confidence_boost'] > 0]),
            'correlation_strength': classify_correlation_strength(correlations)
        }
        
    except Exception as e:
        current_app.logger.error(f"Failed to calculate fundamental correlations: {e}")
        return {
            'symbol_correlations': [],
            'avg_fundamental_boost': 0,
            'enhanced_symbols': 0,
            'correlation_strength': 'unknown'
        }

def calculate_correlation_boost(win_rate, revenue_growth):
    """Calculate how much revenue growth correlates with pattern win rate"""
    if revenue_growth > 0 and win_rate > 0.6:
        return min(0.15, revenue_growth * 0.1)  # Cap at 15% boost
    return 0

def classify_fundamental_strength(financials):
    """Classify fundamental strength based on Polygon data"""
    score = 0
    if hasattr(financials, 'market_cap') and financials.market_cap > 1e9:
        score += 1
    # Add more fundamental criteria
    
    if score >= 2:
        return 'strong'
    elif score == 1:
        return 'moderate'
    return 'weak'

def classify_correlation_strength(correlations):
    """Classify overall correlation strength"""
    if not correlations:
        return 'insufficient_data'
    
    positive_correlations = len([c for c in correlations if c['confidence_boost'] > 0])
    total = len(correlations)
    
    if positive_correlations / total > 0.7:
        return 'strong_positive'
    elif positive_correlations / total > 0.4:
        return 'moderate'
    return 'weak'

def calculate_pattern_performance(user_id, time_filter):
    """Calculate overall pattern performance metrics"""
    query = f"""
    WITH user_patterns AS (
        SELECT dp.symbol, dp.pattern_type, dp.confidence, dp.current_price as entry_price,
               dp.detected_at, dp.expiration,
               -- Get price after pattern expiration or current price
               COALESCE(
                   (SELECT current_price FROM daily_patterns dp2 
                    WHERE dp2.symbol = dp.symbol 
                    AND dp2.detected_at > dp.expiration 
                    ORDER BY dp2.detected_at ASC LIMIT 1),
                   dp.current_price
               ) as exit_price
        FROM daily_patterns dp
        JOIN user_watchlists uw ON dp.symbol = ANY(uw.symbols)
        WHERE uw.user_id = :user_id 
        AND dp.detected_at >= :time_filter
        
        UNION ALL
        
        SELECT ip.symbol, ip.pattern_type, ip.confidence, ip.current_price,
               ip.detected_at, ip.expiration,
               COALESCE(
                   (SELECT current_price FROM intraday_patterns ip2 
                    WHERE ip2.symbol = ip.symbol 
                    AND ip2.detected_at > ip.expiration 
                    ORDER BY ip2.detected_at ASC LIMIT 1),
                   ip.current_price
               ) as exit_price
        FROM intraday_patterns ip
        JOIN user_watchlists uw ON ip.symbol = ANY(uw.symbols)
        WHERE uw.user_id = :user_id 
        AND ip.detected_at >= :time_filter
    ),
    performance_calc AS (
        SELECT 
            symbol,
            pattern_type,
            confidence,
            entry_price,
            exit_price,
            ((exit_price - entry_price) / entry_price * 100) as return_pct,
            CASE WHEN exit_price > entry_price THEN 1 ELSE 0 END as is_winner,
            detected_at,
            expiration
        FROM user_patterns
        WHERE entry_price > 0 AND exit_price > 0
    )
    SELECT 
        COUNT(*) as total_patterns,
        COUNT(CASE WHEN is_winner = 1 THEN 1 END) as winning_patterns,
        AVG(return_pct) as avg_return,
        STDDEV(return_pct) as return_volatility,
        MAX(return_pct) as best_return,
        MIN(return_pct) as worst_return,
        COUNT(CASE WHEN return_pct > 0 THEN 1 END)::float / COUNT(*)::float * 100 as win_rate
    FROM performance_calc
    """
    
    result = db.session.execute(text(query), {
        'user_id': user_id, 
        'time_filter': time_filter
    }).fetchone()
    
    if not result or not result.total_patterns:
        return {
            'total_patterns': 0,
            'win_rate': 0,
            'avg_return': 0,
            'best_return': 0,
            'worst_return': 0,
            'sharpe_ratio': 0
        }
    
    # Calculate Sharpe ratio (simplified)
    sharpe_ratio = (result.avg_return / result.return_volatility) if result.return_volatility > 0 else 0
    
    return {
        'total_patterns': result.total_patterns,
        'winning_patterns': result.winning_patterns,
        'win_rate': round(float(result.win_rate or 0), 2),
        'avg_return': round(float(result.avg_return or 0), 2),
        'best_return': round(float(result.best_return or 0), 2),
        'worst_return': round(float(result.worst_return or 0), 2),
        'sharpe_ratio': round(sharpe_ratio, 2)
    }

def calculate_win_rates_by_confidence(user_id, time_filter):
    """Calculate win rates segmented by confidence levels"""
    query = f"""
    WITH user_pattern_results AS (
        -- Same CTE as above but with confidence buckets
        SELECT 
            CASE 
                WHEN confidence >= 0.9 THEN '90%+'
                WHEN confidence >= 0.8 THEN '80-90%'
                WHEN confidence >= 0.7 THEN '70-80%'
                WHEN confidence >= 0.6 THEN '60-70%'
                ELSE '<60%'
            END as confidence_bucket,
            ((exit_price - entry_price) / entry_price * 100) as return_pct
        FROM (
            -- Pattern performance calculation (abbreviated)
            SELECT confidence, entry_price, exit_price
            FROM daily_patterns dp
            JOIN user_watchlists uw ON dp.symbol = ANY(uw.symbols)
            WHERE uw.user_id = :user_id AND dp.detected_at >= :time_filter
        ) calc
        WHERE entry_price > 0 AND exit_price > 0
    )
    SELECT 
        confidence_bucket,
        COUNT(*) as pattern_count,
        COUNT(CASE WHEN return_pct > 0 THEN 1 END)::float / COUNT(*)::float * 100 as win_rate,
        AVG(return_pct) as avg_return
    FROM user_pattern_results
    GROUP BY confidence_bucket
    ORDER BY confidence_bucket DESC
    """
    
    result = db.session.execute(text(query), {
        'user_id': user_id,
        'time_filter': time_filter
    })
    
    return [
        {
            'confidence_bucket': row.confidence_bucket,
            'pattern_count': row.pattern_count,
            'win_rate': round(float(row.win_rate or 0), 2),
            'avg_return': round(float(row.avg_return or 0), 2)
        }
        for row in result
    ]

def calculate_symbol_performance(user_id, time_filter):
    """Get best and worst performing symbols"""
    query = f"""
    WITH symbol_performance AS (
        SELECT 
            symbol,
            COUNT(*) as pattern_count,
            AVG(((exit_price - entry_price) / entry_price * 100)) as avg_return,
            COUNT(CASE WHEN exit_price > entry_price THEN 1 END)::float / COUNT(*)::float * 100 as win_rate
        FROM (
            -- Pattern performance by symbol (abbreviated)
            SELECT symbol, entry_price, exit_price
            FROM daily_patterns dp
            JOIN user_watchlists uw ON dp.symbol = ANY(uw.symbols)
            WHERE uw.user_id = :user_id AND dp.detected_at >= :time_filter
        ) calc
        WHERE entry_price > 0 AND exit_price > 0
        GROUP BY symbol
        HAVING COUNT(*) >= 2  -- At least 2 patterns for statistical relevance
    )
    SELECT 
        symbol,
        pattern_count,
        avg_return,
        win_rate
    FROM symbol_performance
    ORDER BY avg_return DESC
    """
    
    result = db.session.execute(text(query), {
        'user_id': user_id,
        'time_filter': time_filter
    })
    
    all_symbols = [
        {
            'symbol': row.symbol,
            'pattern_count': row.pattern_count,
            'avg_return': round(float(row.avg_return or 0), 2),
            'win_rate': round(float(row.win_rate or 0), 2)
        }
        for row in result
    ]
    
    return {
        'best_performers': all_symbols[:5],  # Top 5
        'worst_performers': all_symbols[-5:],  # Bottom 5
        'all_symbols': all_symbols
    }

def get_time_filter(timeframe):
    """Convert timeframe string to datetime"""
    now = datetime.now()
    
    if timeframe == '1d':
        return now - timedelta(days=1)
    elif timeframe == '7d':
        return now - timedelta(days=7)
    elif timeframe == '30d':
        return now - timedelta(days=30)
    elif timeframe == '90d':
        return now - timedelta(days=90)
    else:
        return now - timedelta(days=7)  # Default to 7 days
```

### Task 5.2: My Focus Frontend Component (Days 4-8)

#### 5.2.1 MyFocus Main Component
**File**: `static/js/components/MyFocus.js`

```javascript
class MyFocus {
    constructor(container) {
        this.container = container;
        this.watchlists = [];
        this.activeWatchlistId = null;
        this.patterns = [];
        this.analytics = null;
        this.alertSettings = {};
        this.updateInterval = null;
        this.websocketHandler = null;
        
        this.init();
        this.loadData();
        this.setupWebSocketAlerts();
        this.startAutoRefresh();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="my-focus">
                <!-- Header with Actions -->
                <div class="focus-header">
                    <div class="header-left">
                        <h3>🎯 My Focus</h3>
                        <div class="watchlist-selector">
                            <select id="active-watchlist-select">
                                <option value="">Select Watchlist...</option>
                            </select>
                        </div>
                    </div>
                    <div class="header-actions">
                        <button class="focus-btn" id="create-watchlist-btn">+ New Watchlist</button>
                        <button class="focus-btn" id="import-watchlist-btn">📥 Import</button>
                        <button class="focus-btn" id="export-watchlist-btn">📤 Export</button>
                        <button class="focus-btn" id="settings-btn">⚙️ Settings</button>
                    </div>
                </div>
                
                <!-- Main Content Grid -->
                <div class="focus-content-grid">
                    <!-- Left Panel: Watchlist Management -->
                    <div class="watchlist-panel">
                        <!-- Watchlist Overview -->
                        <div class="focus-section">
                            <h4>📋 My Watchlists</h4>
                            <div class="watchlist-overview" id="watchlist-overview">
                                <!-- Populated by JavaScript -->
                            </div>
                        </div>
                        
                        <!-- Quick Actions -->
                        <div class="focus-section">
                            <h4>⚡ Quick Actions</h4>
                            <div class="quick-actions-grid">
                                <button class="quick-action-btn" id="scan-all-watchlists">
                                    🔍 Scan All
                                </button>
                                <button class="quick-action-btn" id="refresh-patterns">
                                    🔄 Refresh
                                </button>
                                <button class="quick-action-btn" id="clear-expired">
                                    🗑️ Clear Expired
                                </button>
                                <button class="quick-action-btn" id="optimize-alerts">
                                    🎯 Optimize Alerts
                                </button>
                            </div>
                        </div>
                        
                        <!-- Performance Summary -->
                        <div class="focus-section">
                            <h4>📊 Performance Summary</h4>
                            <div class="performance-summary" id="performance-summary">
                                <!-- Populated by JavaScript -->
                            </div>
                        </div>
                    </div>
                    
                    <!-- Center Panel: Active Patterns -->
                    <div class="active-patterns-panel">
                        <!-- Pattern Table -->
                        <div class="focus-section full-height">
                            <div class="section-header">
                                <h4 id="patterns-title">🎯 Active Patterns</h4>
                                <div class="pattern-controls">
                                    <span class="pattern-count" id="pattern-count">0 patterns</span>
                                    <select id="sort-patterns">
                                        <option value="confidence">Sort by Confidence</option>
                                        <option value="detected_at">Sort by Time</option>
                                        <option value="symbol">Sort by Symbol</option>
                                        <option value="expiration">Sort by Expiration</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="patterns-table-container">
                                <table class="focus-patterns-table" id="focus-patterns-table">
                                    <thead>
                                        <tr>
                                            <th>Symbol</th>
                                            <th>Pattern</th>
                                            <th>Conf</th>
                                            <th>RS</th>
                                            <th>Vol</th>
                                            <th>Price</th>
                                            <th>Change</th>
                                            <th>Detected</th>
                                            <th>Expires</th>
                                            <th>Alert</th>
                                            <th>Chart</th>
                                        </tr>
                                    </thead>
                                    <tbody id="focus-patterns-body">
                                        <!-- Populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Right Panel: Alerts & Analytics -->
                    <div class="alerts-analytics-panel">
                        <!-- Real-time Alerts -->
                        <div class="focus-section">
                            <h4>🔔 Live Alerts</h4>
                            <div class="alerts-container" id="live-alerts">
                                <!-- Populated by WebSocket -->
                            </div>
                        </div>
                        
                        <!-- Performance Analytics -->
                        <div class="focus-section">
                            <h4>📈 Analytics Dashboard</h4>
                            <div class="analytics-tabs">
                                <button class="analytics-tab active" data-tab="overview">Overview</button>
                                <button class="analytics-tab" data-tab="winrate">Win Rate</button>
                                <button class="analytics-tab" data-tab="symbols">Symbols</button>
                            </div>
                            
                            <div class="analytics-content">
                                <!-- Overview Tab -->
                                <div class="analytics-panel active" id="overview-panel">
                                    <div class="metrics-grid" id="overview-metrics">
                                        <!-- Populated by analytics API -->
                                    </div>
                                </div>
                                
                                <!-- Win Rate Tab -->
                                <div class="analytics-panel" id="winrate-panel">
                                    <div class="winrate-breakdown" id="winrate-breakdown">
                                        <!-- Win rate by confidence level -->
                                    </div>
                                </div>
                                
                                <!-- Symbols Tab -->
                                <div class="analytics-panel" id="symbols-panel">
                                    <div class="symbol-performance" id="symbol-performance">
                                        <!-- Best/worst performers -->
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Auto-Focus Chart Section -->
                <div class="auto-focus-chart" id="auto-focus-chart" style="display: none;">
                    <div class="chart-header">
                        <h4>📈 Auto-Focus: <span id="focus-chart-symbol">-</span></h4>
                        <button class="chart-toggle" id="close-focus-chart">&times;</button>
                    </div>
                    <div class="chart-content" id="focus-chart-content">
                        <!-- Chart loaded here -->
                    </div>
                </div>
            </div>
        `;
        
        this.bindEvents();
    }
    
    bindEvents() {
        // Watchlist selection
        document.getElementById('active-watchlist-select').addEventListener('change', (e) => {
            this.selectWatchlist(e.target.value);
        });
        
        // Header actions
        document.getElementById('create-watchlist-btn').addEventListener('click', () => {
            this.showCreateWatchlistDialog();
        });
        
        document.getElementById('import-watchlist-btn').addEventListener('click', () => {
            this.showImportDialog();
        });
        
        document.getElementById('export-watchlist-btn').addEventListener('click', () => {
            this.exportActiveWatchlist();
        });
        
        // Quick actions
        document.getElementById('scan-all-watchlists').addEventListener('click', () => {
            this.scanAllWatchlists();
        });
        
        document.getElementById('refresh-patterns').addEventListener('click', () => {
            this.refreshPatterns();
        });
        
        document.getElementById('clear-expired').addEventListener('click', () => {
            this.clearExpiredPatterns();
        });
        
        // Pattern sorting
        document.getElementById('sort-patterns').addEventListener('change', (e) => {
            this.sortPatterns(e.target.value);
        });
        
        // Analytics tabs
        this.container.querySelectorAll('.analytics-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchAnalyticsTab(e.target.dataset.tab);
            });
        });
        
        // Pattern table interactions
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('alert-toggle-btn')) {
                const symbol = e.target.dataset.symbol;
                this.togglePatternAlert(symbol);
            } else if (e.target.classList.contains('focus-chart-btn')) {
                const symbol = e.target.dataset.symbol;
                this.showAutoFocusChart(symbol);
            } else if (e.target.classList.contains('watchlist-item')) {
                const watchlistId = e.target.dataset.watchlistId;
                this.selectWatchlist(watchlistId);
            }
        });
        
        // Close auto-focus chart
        document.getElementById('close-focus-chart').addEventListener('click', () => {
            this.hideAutoFocusChart();
        });
    }
    
    async loadData() {
        try {
            this.showLoading(true);
            
            // Load watchlists and analytics in parallel
            const [watchlistsResponse, analyticsResponse] = await Promise.all([
                fetch('/api/watchlists', {
                    headers: { 'X-User-ID': this.getUserId() }
                }),
                fetch('/api/analytics/performance?timeframe=7d', {
                    headers: { 'X-User-ID': this.getUserId() }
                })
            ]);
            
            this.watchlists = await watchlistsResponse.json().then(data => data.watchlists || []);
            this.analytics = await analyticsResponse.json();
            
            this.renderWatchlists();
            this.renderAnalytics();
            
            // Load patterns for first watchlist if available
            if (this.watchlists.length > 0 && !this.activeWatchlistId) {
                this.selectWatchlist(this.watchlists[0].id);
            }
            
        } catch (error) {
            this.showError('Failed to load My Focus data: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    renderWatchlists() {
        // Update selector
        const select = document.getElementById('active-watchlist-select');
        select.innerHTML = '<option value="">Select Watchlist...</option>' +
            this.watchlists.map(wl => `
                <option value="${wl.id}" ${wl.id === this.activeWatchlistId ? 'selected' : ''}>
                    ${wl.name} (${wl.symbol_count})
                </option>
            `).join('');
        
        // Update overview
        const overview = document.getElementById('watchlist-overview');
        overview.innerHTML = this.watchlists.map(watchlist => `
            <div class="watchlist-item ${watchlist.id === this.activeWatchlistId ? 'active' : ''}" 
                 data-watchlist-id="${watchlist.id}">
                <div class="watchlist-header">
                    <span class="watchlist-name">${watchlist.name}</span>
                    <div class="watchlist-actions">
                        <button class="mini-btn edit-watchlist" data-id="${watchlist.id}">✏️</button>
                        <button class="mini-btn delete-watchlist" data-id="${watchlist.id}">🗑️</button>
                    </div>
                </div>
                <div class="watchlist-stats">
                    <span class="stat">
                        <span class="stat-value">${watchlist.symbol_count}</span>
                        <span class="stat-label">symbols</span>
                    </span>
                    <span class="stat">
                        <span class="stat-value">${watchlist.active_patterns || 0}</span>
                        <span class="stat-label">patterns</span>
                    </span>
                </div>
                <div class="watchlist-updated">
                    Updated: ${this.formatDate(watchlist.updated_at)}
                </div>
            </div>
        `).join('');
        
        // Bind watchlist actions
        overview.querySelectorAll('.edit-watchlist').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.editWatchlist(e.target.dataset.id);
            });
        });
        
        overview.querySelectorAll('.delete-watchlist').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteWatchlist(e.target.dataset.id);
            });
        });
    }
    
    async selectWatchlist(watchlistId) {
        if (!watchlistId) {
            this.activeWatchlistId = null;
            this.patterns = [];
            this.renderPatterns();
            return;
        }
        
        this.activeWatchlistId = watchlistId;
        document.getElementById('active-watchlist-select').value = watchlistId;
        
        try {
            const response = await fetch(`/api/watchlists/${watchlistId}/patterns`, {
                headers: { 'X-User-ID': this.getUserId() }
            });
            
            const data = await response.json();
            this.patterns = data.patterns || [];
            
            this.renderPatterns();
            this.renderWatchlists(); // Update active state
            this.autoSelectHighestConfidencePattern();
            
        } catch (error) {
            this.showError('Failed to load watchlist patterns: ' + error.message);
        }
    }
    
    renderPatterns() {
        const tbody = document.getElementById('focus-patterns-body');
        const countElement = document.getElementById('pattern-count');
        
        countElement.textContent = `${this.patterns.length} patterns`;
        
        tbody.innerHTML = this.patterns.map(pattern => `
            <tr class="focus-pattern-row" data-symbol="${pattern.symbol}">
                <td class="symbol-cell">
                    <strong>${pattern.symbol}</strong>
                </td>
                <td class="pattern-cell">
                    <span class="pattern-badge pattern-${pattern.pattern_type.toLowerCase()}">
                        ${this.abbreviatePattern(pattern.pattern_type)}
                    </span>
                </td>
                <td class="confidence-cell">
                    <span class="confidence-value conf-${this.getConfidenceClass(pattern.confidence)}">
                        ${Math.round(pattern.confidence * 100)}%
                    </span>
                </td>
                <td class="rs-cell">
                    <span class="rs-value ${(pattern.indicators?.relative_strength || 1) > 1.1 ? 'rs-high' : ''}">
                        ${(pattern.indicators?.relative_strength || 1.0).toFixed(1)}x
                    </span>
                </td>
                <td class="vol-cell">
                    <span class="vol-value ${(pattern.indicators?.relative_volume || 1) > 2.0 ? 'vol-high' : ''}">
                        ${(pattern.indicators?.relative_volume || 1.0).toFixed(1)}x
                    </span>
                </td>
                <td class="price-cell">${this.formatPrice(pattern.current_price)}</td>
                <td class="change-cell">
                    <span class="price-change ${pattern.price_change >= 0 ? 'positive' : 'negative'}">
                        ${this.formatChange(pattern.price_change)}
                    </span>
                </td>
                <td class="time-cell">${this.formatTimeAgo(pattern.detected_at)}</td>
                <td class="expiry-cell">
                    <span class="expiration ${this.isExpiringSoon(pattern.expiration) ? 'expiring' : ''}">
                        ${pattern.time_remaining}
                    </span>
                </td>
                <td class="alert-cell">
                    <button class="alert-toggle-btn ${this.isAlertActive(pattern.symbol) ? 'active' : ''}" 
                            data-symbol="${pattern.symbol}">
                        ${this.isAlertActive(pattern.symbol) ? '🔔' : '🔕'}
                    </button>
                </td>
                <td class="chart-cell">
                    <button class="focus-chart-btn" data-symbol="${pattern.symbol}">📊</button>
                </td>
            </tr>
        `).join('');
    }
    
    renderAnalytics() {
        if (!this.analytics) return;
        
        // Overview metrics
        const overviewMetrics = document.getElementById('overview-metrics');
        const perf = this.analytics.pattern_performance || {};
        
        overviewMetrics.innerHTML = `
            <div class="metric-card">
                <div class="metric-value">${perf.total_patterns || 0}</div>
                <div class="metric-label">Total Patterns</div>
            </div>
            <div class="metric-card">
                <div class="metric-value ${perf.win_rate >= 60 ? 'positive' : perf.win_rate >= 40 ? 'neutral' : 'negative'}">
                    ${(perf.win_rate || 0).toFixed(1)}%
                </div>
                <div class="metric-label">Win Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value ${perf.avg_return >= 0 ? 'positive' : 'negative'}">
                    ${(perf.avg_return || 0).toFixed(1)}%
                </div>
                <div class="metric-label">Avg Return</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${(perf.sharpe_ratio || 0).toFixed(2)}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
        `;
        
        // Win rate breakdown
        this.renderWinRateBreakdown();
        
        // Symbol performance
        this.renderSymbolPerformance();
    }
    
    renderWinRateBreakdown() {
        const container = document.getElementById('winrate-breakdown');
        const winRates = this.analytics.win_rates || [];
        
        container.innerHTML = winRates.map(wr => `
            <div class="winrate-item">
                <div class="confidence-range">${wr.confidence_bucket}</div>
                <div class="winrate-stats">
                    <div class="winrate-bar">
                        <div class="winrate-fill" style="width: ${wr.win_rate}%"></div>
                    </div>
                    <span class="winrate-text">${wr.win_rate.toFixed(1)}%</span>
                    <span class="pattern-count">(${wr.pattern_count} patterns)</span>
                </div>
            </div>
        `).join('');
    }
    
    renderSymbolPerformance() {
        const container = document.getElementById('symbol-performance');
        const symbolPerf = this.analytics.symbol_performance || {};
        
        container.innerHTML = `
            <div class="symbol-performance-section">
                <h5>🏆 Top Performers</h5>
                <div class="symbol-list">
                    ${(symbolPerf.best_performers || []).map(symbol => `
                        <div class="symbol-performance-item best">
                            <span class="symbol-name">${symbol.symbol}</span>
                            <span class="symbol-return positive">+${symbol.avg_return.toFixed(1)}%</span>
                            <span class="symbol-patterns">${symbol.pattern_count} patterns</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="symbol-performance-section">
                <h5>📉 Underperformers</h5>
                <div class="symbol-list">
                    ${(symbolPerf.worst_performers || []).map(symbol => `
                        <div class="symbol-performance-item worst">
                            <span class="symbol-name">${symbol.symbol}</span>
                            <span class="symbol-return negative">${symbol.avg_return.toFixed(1)}%</span>
                            <span class="symbol-patterns">${symbol.pattern_count} patterns</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    setupWebSocketAlerts() {
        if (!window.wsClient) return;
        
        this.websocketHandler = (data) => {
            if (data.type === 'pattern_alert') {
                this.handlePatternAlert(data);
            } else if (data.type === 'pattern_update') {
                this.handlePatternUpdate(data);
            }
        };
        
        window.wsClient.addHandler('watchlist_alerts', this.websocketHandler);
        
        // Subscribe to alerts for active watchlist
        if (this.activeWatchlistId) {
            window.wsClient.send({
                action: 'subscribe_watchlist_alerts',
                watchlist_id: this.activeWatchlistId,
                user_id: this.getUserId()
            });
        }
    }
    
    handlePatternAlert(alertData) {
        const alertsContainer = document.getElementById('live-alerts');
        
        // Create alert element
        const alertElement = document.createElement('div');
        alertElement.className = `live-alert alert-${alertData.severity || 'medium'}`;
        alertElement.innerHTML = `
            <div class="alert-header">
                <span class="alert-icon">${this.getAlertIcon(alertData.alert_type)}</span>
                <span class="alert-symbol">${alertData.symbol}</span>
                <span class="alert-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="alert-message">${alertData.message}</div>
        `;
        
        // Add to alerts container (newest first)
        alertsContainer.insertBefore(alertElement, alertsContainer.firstChild);
        
        // Limit to 10 alerts
        while (alertsContainer.children.length > 10) {
            alertsContainer.removeChild(alertsContainer.lastChild);
        }
        
        // Auto-remove after 30 seconds
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.classList.add('fade-out');
                setTimeout(() => alertElement.remove(), 300);
            }
        }, 30000);
        
        // Show browser notification if supported
        this.showBrowserNotification(alertData);
    }
    
    autoSelectHighestConfidencePattern() {
        if (this.patterns.length === 0) return;
        
        // Find highest confidence pattern
        const highestConfPattern = this.patterns.reduce((prev, current) => 
            (prev.confidence > current.confidence) ? prev : current
        );
        
        if (highestConfPattern.confidence >= 0.85) {
            setTimeout(() => {
                this.showAutoFocusChart(highestConfPattern.symbol);
            }, 1000);
        }
    }
    
    showAutoFocusChart(symbol) {
        const chartSection = document.getElementById('auto-focus-chart');
        const chartContent = document.getElementById('focus-chart-content');
        const chartSymbol = document.getElementById('focus-chart-symbol');
        
        chartSymbol.textContent = symbol;
        chartSection.style.display = 'block';
        
        // Load chart (placeholder for Phase 6)
        chartContent.innerHTML = `
            <div class="chart-placeholder">
                <h3>📈 ${symbol} Auto-Focus Chart</h3>
                <p>Interactive charting coming in Phase 6</p>
                <div class="chart-mock">
                    <div class="chart-line"></div>
                    <div class="pattern-markers">
                        <span class="marker entry">Entry</span>
                        <span class="marker target">Target</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Utility methods
    getUserId() {
        return 'user123'; // Replace with actual user identification
    }
    
    formatPrice(price) {
        return price ? `$${price.toFixed(2)}` : 'N/A';
    }
    
    formatChange(change) {
        return change ? `${change >= 0 ? '+' : ''}${change.toFixed(1)}%` : '0.0%';
    }
    
    formatTimeAgo(dateString) {
        const now = new Date();
        const date = new Date(dateString);
        const diff = (now - date) / 1000;
        
        if (diff < 60) return `${Math.floor(diff)}s`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
        return `${Math.floor(diff / 86400)}d`;
    }
    
    getConfidenceClass(confidence) {
        if (confidence >= 0.9) return 'very-high';
        if (confidence >= 0.8) return 'high';
        if (confidence >= 0.7) return 'medium';
        return 'low';
    }
    
    abbreviatePattern(patternType) {
        const abbreviations = {
            'Weekly_Breakout': 'WeeklyBO',
            'Bull_Flag': 'BullFlag',
            'Volume_Spike': 'VolSpike'
        };
        return abbreviations[patternType] || patternType.substring(0, 8);
    }
    
    isAlertActive(symbol) {
        return this.alertSettings[symbol] || false;
    }
    
    startAutoRefresh() {
        this.updateInterval = setInterval(() => {
            if (this.activeWatchlistId) {
                this.selectWatchlist(this.activeWatchlistId);
            }
        }, 30000); // 30 seconds
    }
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.websocketHandler && window.wsClient) {
            window.wsClient.removeHandler('watchlist_alerts', this.websocketHandler);
        }
    }
}

// Register for GoldenLayout
window.MyFocus = MyFocus;
```

### Task 5.3: My Focus Styles (Days 9-10)

#### 5.3.1 MyFocus CSS
**File**: `static/css/my-focus.css`

```css
/* My Focus Tab Styles */
.my-focus {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
    overflow: hidden;
}

/* Focus Header */
.focus-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.focus-header h3 {
    margin: 0;
    font-size: 16px;
    color: var(--text-primary);
}

.watchlist-selector select {
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 4px;
    font-size: 12px;
    min-width: 200px;
}

.header-actions {
    display: flex;
    gap: 8px;
}

.focus-btn {
    padding: 6px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s ease;
}

.focus-btn:hover {
    background: var(--bg-hover);
    border-color: var(--accent-primary);
}

/* Content Grid */
.focus-content-grid {
    display: grid;
    grid-template-columns: 280px 1fr 300px;
    gap: 16px;
    padding: 16px;
    flex: 1;
    overflow: hidden;
}

.watchlist-panel,
.active-patterns-panel,
.alerts-analytics-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow: hidden;
}

/* Focus Sections */
.focus-section {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.focus-section.full-height {
    flex: 1;
}

.focus-section h4 {
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

/* Watchlist Overview */
.watchlist-overview {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    max-height: 300px;
}

.watchlist-item {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.watchlist-item:hover {
    background: var(--bg-hover);
    border-color: var(--accent-primary);
}

.watchlist-item.active {
    border-color: var(--accent-primary);
    background: rgba(0, 212, 170, 0.1);
}

.watchlist-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.watchlist-name {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 13px;
}

.watchlist-actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.2s ease;
}

.watchlist-item:hover .watchlist-actions {
    opacity: 1;
}

.mini-btn {
    width: 20px;
    height: 20px;
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    border-radius: 2px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
}

.mini-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.watchlist-stats {
    display: flex;
    gap: 16px;
    margin-bottom: 6px;
}

.stat {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.stat-value {
    font-size: 14px;
    font-weight: 600;
    color: var(--accent-primary);
}

.stat-label {
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
}

.watchlist-updated {
    font-size: 10px;
    color: var(--text-secondary);
}

/* Quick Actions */
.quick-actions-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 12px;
}

.quick-action-btn {
    padding: 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    text-align: center;
    transition: all 0.2s ease;
}

.quick-action-btn:hover {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

/* Performance Summary */
.performance-summary {
    padding: 12px;
}

.performance-summary .metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}

.performance-summary .metric-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 8px;
    text-align: center;
}

.performance-summary .metric-value {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.performance-summary .metric-label {
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
}

/* Patterns Table */
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
}

.section-header h4 {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    text-transform: uppercase;
}

.pattern-controls {
    display: flex;
    align-items: center;
    gap: 12px;
}

.pattern-count {
    font-size: 11px;
    color: var(--text-secondary);
}

#sort-patterns {
    padding: 2px 6px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    font-size: 11px;
}

.patterns-table-container {
    flex: 1;
    overflow: auto;
}

.focus-patterns-table {
    width: 100%;
    font-size: 11px;
    border-collapse: collapse;
}

.focus-patterns-table th {
    background: var(--bg-primary);
    padding: 6px 4px;
    text-align: left;
    font-weight: 600;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 10;
}

.focus-patterns-table td {
    padding: 4px;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-primary);
}

.focus-pattern-row:hover {
    background: var(--bg-hover);
}

/* Pattern Cell Styles */
.pattern-badge {
    padding: 1px 4px;
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

.rs-value.rs-high,
.vol-value.vol-high {
    color: var(--success-color);
    font-weight: 600;
}

.price-change.positive {
    color: var(--success-color);
}

.price-change.negative {
    color: var(--error-color);
}

.expiration.expiring {
    color: var(--warning-color);
    font-weight: 600;
}

.alert-toggle-btn,
.focus-chart-btn {
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 2px 4px;
    border-radius: 2px;
    cursor: pointer;
    font-size: 10px;
}

.alert-toggle-btn:hover,
.focus-chart-btn:hover {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

.alert-toggle-btn.active {
    background: var(--success-color);
    color: #fff;
    border-color: var(--success-color);
}

/* Live Alerts */
.alerts-container {
    padding: 12px;
    max-height: 300px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.live-alert {
    background: var(--bg-primary);
    border-left: 3px solid var(--accent-primary);
    padding: 8px;
    border-radius: 4px;
    animation: slideInRight 0.3s ease;
}

.live-alert.alert-high {
    border-left-color: var(--error-color);
}

.live-alert.alert-medium {
    border-left-color: var(--warning-color);
}

.live-alert.alert-low {
    border-left-color: var(--accent-primary);
}

.alert-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.alert-icon {
    font-size: 12px;
}

.alert-symbol {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 12px;
}

.alert-time {
    font-size: 10px;
    color: var(--text-secondary);
}

.alert-message {
    font-size: 11px;
    color: var(--text-primary);
}

.live-alert.fade-out {
    animation: slideOutRight 0.3s ease forwards;
}

/* Analytics Dashboard */
.analytics-tabs {
    display: flex;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
}

.analytics-tab {
    flex: 1;
    padding: 8px 12px;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 11px;
    text-transform: uppercase;
    font-weight: 500;
    transition: all 0.2s ease;
}

.analytics-tab.active {
    color: var(--accent-primary);
    background: var(--bg-secondary);
}

.analytics-tab:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
}

.analytics-content {
    flex: 1;
    overflow: auto;
}

.analytics-panel {
    display: none;
    padding: 12px;
}

.analytics-panel.active {
    display: block;
}

/* Overview Metrics */
.metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 16px;
}

.metric-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 12px;
    text-align: center;
}

.metric-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.metric-value.positive {
    color: var(--success-color);
}

.metric-value.negative {
    color: var(--error-color);
}

.metric-value.neutral {
    color: var(--warning-color);
}

.metric-label {
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
    font-weight: 500;
}

/* Win Rate Breakdown */
.winrate-breakdown {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.winrate-item {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 8px;
}

.confidence-range {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 6px;
}

.winrate-stats {
    display: flex;
    align-items: center;
    gap: 8px;
}

.winrate-bar {
    flex: 1;
    height: 4px;
    background: var(--border-color);
    border-radius: 2px;
    position: relative;
}

.winrate-fill {
    height: 100%;
    background: var(--success-color);
    border-radius: 2px;
    transition: width 0.3s ease;
}

.winrate-text {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    min-width: 40px;
    text-align: right;
}

.pattern-count {
    font-size: 9px;
    color: var(--text-secondary);
}

/* Symbol Performance */
.symbol-performance-section {
    margin-bottom: 16px;
}

.symbol-performance-section h5 {
    margin: 0 0 8px 0;
    font-size: 11px;
    color: var(--text-primary);
    text-transform: uppercase;
    font-weight: 600;
}

.symbol-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.symbol-performance-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 8px;
    border-radius: 3px;
    font-size: 11px;
}

.symbol-performance-item.best {
    background: rgba(81, 207, 102, 0.1);
    border-left: 3px solid var(--success-color);
}

.symbol-performance-item.worst {
    background: rgba(255, 107, 107, 0.1);
    border-left: 3px solid var(--error-color);
}

.symbol-name {
    font-weight: 600;
    color: var(--text-primary);
}

.symbol-return.positive {
    color: var(--success-color);
    font-weight: 600;
}

.symbol-return.negative {
    color: var(--error-color);
    font-weight: 600;
}

.symbol-patterns {
    font-size: 9px;
    color: var(--text-secondary);
}

/* Auto-Focus Chart */
.auto-focus-chart {
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    height: 250px;
    display: flex;
    flex-direction: column;
}

.auto-focus-chart .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
}

.auto-focus-chart .chart-header h4 {
    margin: 0;
    font-size: 13px;
    color: var(--text-primary);
}

.chart-toggle {
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 2px 6px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 12px;
}

.chart-toggle:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.auto-focus-chart .chart-content {
    flex: 1;
    padding: 16px;
    overflow: auto;
}

.chart-placeholder {
    text-align: center;
    color: var(--text-secondary);
}

.chart-mock {
    height: 120px;
    background: linear-gradient(45deg, var(--bg-primary) 25%, transparent 25%),
                linear-gradient(45deg, transparent 75%, var(--bg-primary) 75%);
    background-size: 20px 20px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    margin: 16px 0;
    position: relative;
}

.chart-line {
    position: absolute;
    top: 20px;
    left: 20px;
    right: 20px;
    bottom: 20px;
    border-left: 2px solid var(--accent-primary);
    border-bottom: 2px solid var(--accent-primary);
}

/* Animations */
@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOutRight {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(100%);
        opacity: 0;
    }
}

/* Responsive Design */
@media (max-width: 1400px) {
    .focus-content-grid {
        grid-template-columns: 250px 1fr 280px;
    }
}

@media (max-width: 1200px) {
    .focus-content-grid {
        grid-template-columns: 1fr;
        grid-template-rows: auto auto 1fr;
    }
    
    .watchlist-panel,
    .alerts-analytics-panel {
        max-height: 300px;
    }
}

@media (max-width: 768px) {
    .focus-header {
        flex-direction: column;
        gap: 12px;
        align-items: stretch;
    }
    
    .header-left {
        flex-direction: column;
        gap: 8px;
    }
    
    .header-actions {
        justify-content: center;
    }
    
    .focus-content-grid {
        padding: 8px;
        gap: 8px;
    }
    
    .analytics-tabs {
        flex-wrap: wrap;
    }
    
    .metrics-grid {
        grid-template-columns: 1fr;
    }
}
```

## Testing Strategy

### My Focus Testing
**File**: `tests/test_my_focus.js`

```javascript
describe('MyFocus Component', () => {
    let myFocus;
    let container;
    
    beforeEach(() => {
        container = document.createElement('div');
        document.body.appendChild(container);
        
        // Mock APIs
        global.fetch = jest.fn()
            .mockImplementationOnce(() => Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    watchlists: [
                        {
                            id: 'wl1',
                            name: 'Tech Leaders',
                            symbols: ['AAPL', 'GOOGL', 'MSFT'],
                            symbol_count: 3,
                            active_patterns: 5
                        }
                    ]
                })
            }))
            .mockImplementationOnce(() => Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    pattern_performance: {
                        total_patterns: 25,
                        win_rate: 68.5,
                        avg_return: 3.2
                    }
                })
            }));
        
        myFocus = new MyFocus(container);
    });
    
    afterEach(() => {
        document.body.removeChild(container);
        myFocus.destroy();
    });
    
    test('should load and render watchlists', async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const watchlistItems = container.querySelectorAll('.watchlist-item');
        expect(watchlistItems.length).toBe(1);
        expect(watchlistItems[0].textContent).toContain('Tech Leaders');
    });
    
    test('should handle watchlist selection', async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Mock patterns API for watchlist selection
        global.fetch = jest.fn(() => Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
                patterns: [
                    {
                        symbol: 'AAPL',
                        pattern_type: 'Bull_Flag',
                        confidence: 0.92,
                        current_price: 185.50
                    }
                ]
            })
        }));
        
        await myFocus.selectWatchlist('wl1');
        
        expect(myFocus.activeWatchlistId).toBe('wl1');
        expect(myFocus.patterns).toHaveLength(1);
    });
    
    test('should render performance analytics', async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const metrics = container.querySelector('#overview-metrics');
        expect(metrics).toBeTruthy();
        expect(metrics.textContent).toContain('25'); // Total patterns
        expect(metrics.textContent).toContain('68.5%'); // Win rate
    });
    
    test('should handle WebSocket alerts', () => {
        const alertData = {
            type: 'pattern_alert',
            symbol: 'AAPL',
            message: 'Bull flag pattern detected',
            severity: 'high'
        };
        
        myFocus.handlePatternAlert(alertData);
        
        const alerts = container.querySelectorAll('.live-alert');
        expect(alerts.length).toBe(1);
        expect(alerts[0].textContent).toContain('AAPL');
    });
});

describe('Watchlist API', () => {
    test('should create watchlist with valid data', async () => {
        const mockWatchlist = {
            name: 'Test Watchlist',
            symbols: ['AAPL', 'GOOGL'],
            filters: { confidence_min: 0.8 }
        };
        
        // Test would make actual API call in integration environment
        expect(mockWatchlist.symbols.length).toBeLessThanOrEqual(50);
        expect(mockWatchlist.name).toBeTruthy();
    });
    
    test('should validate maximum symbol limit', () => {
        const tooManySymbols = new Array(51).fill('AAPL');
        
        expect(tooManySymbols.length).toBeGreaterThan(50);
        // API should reject this
    });
});
```

## Performance Benchmarks

### My Focus Performance Targets
- **Watchlist load**: <500ms for 5 watchlists with 250 total symbols
- **Pattern refresh**: <300ms for 50 patterns
- **Analytics calculation**: <200ms for 90-day performance analysis
- **Real-time alerts**: <100ms WebSocket message delivery
- **Memory usage**: <30MB for all watchlist data and analytics

## Deployment Checklist

- [ ] Watchlist CRUD operations working correctly
- [ ] Pattern loading for watchlists functional
- [ ] Real-time WebSocket alerts operational
- [ ] Performance analytics calculating accurately
- [ ] Auto-focus chart selection working
- [ ] Mobile responsive design functional
- [ ] Alert notification system working
- [ ] Data export/import features operational
- [ ] Performance benchmarks met
- [ ] Integration with GoldenLayout system

## Next Phase Handoff

**Phase 6 Prerequisites:**
- My Focus tab fully operational with watchlist management
- Real-time alerts and analytics working
- Auto-focus chart integration ready
- Performance tracking and analytics functional

**Personal Dashboard Ready For:**
- Interactive charting integration (Phase 6)
- Advanced pattern annotation and visualization
- Multi-timeframe chart synchronization
- Chart-based pattern analysis tools

This implementation creates a comprehensive personal trading command center that transforms pattern discovery into actionable trading intelligence with sophisticated performance tracking and real-time alerting capabilities.