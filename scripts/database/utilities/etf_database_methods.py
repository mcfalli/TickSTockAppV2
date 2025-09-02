"""
Enhanced ETF Database Access Methods for TickStockAppV2
Sprint 14 Phase 1 - ETF Integration Database Layer

Extends TickStockDatabase class with ETF-specific query methods
maintaining <50ms performance targets and read-only access patterns.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)

class ETFDatabaseMixin:
    """
    Mixin class providing ETF-specific database operations.
    
    Designed to extend the existing TickStockDatabase class with
    ETF filtering, analysis, and FMV lookup capabilities.
    """
    
    @contextmanager
    def etf_query_timer(self, query_name: str):
        """Monitor ETF query performance for optimization."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            logger.debug(f"ETF_QUERY {query_name}: {duration:.2f}ms")
            if duration > 50:
                logger.warning(f"ETF_QUERY_SLOW {query_name}: {duration:.2f}ms")
    
    def get_etf_symbols_for_dropdown(self, 
                                   etf_type: str = None,
                                   min_aum: float = None,
                                   max_expense_ratio: float = None,
                                   issuer: str = None) -> List[Dict[str, Any]]:
        """
        Get ETF symbols with filtering options for UI dropdowns.
        
        Optimized for <20ms response time with up to 3,000 ETFs.
        Uses idx_etf_classification and idx_etf_aum_size indexes.
        
        Args:
            etf_type: Filter by ETF type ('ETF', 'CEF', etc.)
            min_aum: Minimum AUM in millions USD
            max_expense_ratio: Maximum expense ratio (e.g., 0.01 for 1%)
            issuer: Filter by ETF issuer/sponsor
            
        Returns:
            List of ETF symbols with metadata for dropdown display
        """
        try:
            with self.etf_query_timer("get_etf_symbols_filtered"):
                # Build dynamic query with optimal index usage
                base_query = """
                    SELECT 
                        symbol, 
                        name, 
                        etf_type,
                        aum_millions,
                        expense_ratio,
                        issuer,
                        underlying_index,
                        correlation_reference,
                        active
                    FROM symbols 
                    WHERE etf_type IS NOT NULL 
                      AND active = true
                """
                
                conditions = []
                params = {}
                
                if etf_type:
                    conditions.append("etf_type = :etf_type")
                    params['etf_type'] = etf_type
                    
                if min_aum is not None:
                    conditions.append("aum_millions >= :min_aum")
                    params['min_aum'] = min_aum
                    
                if max_expense_ratio is not None:
                    conditions.append("expense_ratio <= :max_expense_ratio")
                    params['max_expense_ratio'] = max_expense_ratio
                    
                if issuer:
                    conditions.append("issuer ILIKE :issuer")
                    params['issuer'] = f'%{issuer}%'
                
                if conditions:
                    base_query += " AND " + " AND ".join(conditions)
                
                base_query += " ORDER BY aum_millions DESC NULLS LAST, symbol ASC"
                
                with self.get_connection() as conn:
                    result = conn.execute(text(base_query), params)
                    
                    etfs = []
                    for row in result:
                        etfs.append({
                            'symbol': row[0],
                            'name': row[1] or '',
                            'etf_type': row[2] or 'ETF',
                            'aum_millions': float(row[3]) if row[3] else None,
                            'expense_ratio': float(row[4]) if row[4] else None,
                            'issuer': row[5] or '',
                            'underlying_index': row[6] or '',
                            'correlation_reference': row[7] or '',
                            'active': row[8]
                        })
                    
                    logger.debug(f"ETF_DROPDOWN: Retrieved {len(etfs)} ETFs with filters")
                    return etfs
                    
        except Exception as e:
            logger.error(f"Failed to get filtered ETF symbols: {e}")
            return []
    
    def get_etf_correlation_groups(self, 
                                 reference_symbol: str = None,
                                 limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get ETFs grouped by correlation reference for sector analysis.
        
        Uses idx_etf_correlation_ref for optimal performance.
        Target: <30ms for correlation grouping operations.
        
        Args:
            reference_symbol: Filter by correlation reference (e.g., 'SPY')
            limit: Maximum number of correlation groups to return
            
        Returns:
            List of correlation groups with ETF counts and statistics
        """
        try:
            with self.etf_query_timer("get_etf_correlation_groups"):
                if reference_symbol:
                    # Get specific correlation group
                    query = """
                        SELECT 
                            symbol,
                            name,
                            etf_type,
                            aum_millions,
                            expense_ratio,
                            correlation_reference
                        FROM symbols 
                        WHERE correlation_reference = :reference_symbol
                          AND etf_type IS NOT NULL
                          AND active = true
                        ORDER BY aum_millions DESC NULLS LAST
                    """
                    params = {'reference_symbol': reference_symbol}
                else:
                    # Get all correlation groups summary
                    query = """
                        SELECT 
                            correlation_reference,
                            COUNT(*) as etf_count,
                            AVG(expense_ratio) as avg_expense_ratio,
                            AVG(aum_millions) as avg_aum_millions,
                            STRING_AGG(symbol, ', ' ORDER BY aum_millions DESC) as top_etfs
                        FROM symbols 
                        WHERE correlation_reference IS NOT NULL
                          AND etf_type IS NOT NULL
                          AND active = true
                        GROUP BY correlation_reference
                        ORDER BY COUNT(*) DESC, AVG(aum_millions) DESC
                        LIMIT :limit
                    """
                    params = {'limit': limit}
                
                with self.get_connection() as conn:
                    result = conn.execute(text(query), params)
                    
                    if reference_symbol:
                        # Return individual ETFs in correlation group
                        etfs = []
                        for row in result:
                            etfs.append({
                                'symbol': row[0],
                                'name': row[1],
                                'etf_type': row[2],
                                'aum_millions': float(row[3]) if row[3] else None,
                                'expense_ratio': float(row[4]) if row[4] else None,
                                'correlation_reference': row[5]
                            })
                        return etfs
                    else:
                        # Return correlation group summaries
                        groups = []
                        for row in result:
                            groups.append({
                                'correlation_reference': row[0],
                                'etf_count': int(row[1]),
                                'avg_expense_ratio': float(row[2]) if row[2] else None,
                                'avg_aum_millions': float(row[3]) if row[3] else None,
                                'top_etfs': row[4] or ''
                            })
                        return groups
                        
        except Exception as e:
            logger.error(f"Failed to get ETF correlation groups: {e}")
            return []
    
    def get_etf_performance_ranking(self, 
                                  limit: int = 50,
                                  min_aum: float = None) -> List[Dict[str, Any]]:
        """
        Get ETF performance ranking based on liquidity, costs, and size.
        
        Uses v_etf_performance_ranking view for optimal performance.
        Target: <25ms for top 50 ETF ranking.
        
        Args:
            limit: Maximum number of ETFs to return
            min_aum: Minimum AUM filter in millions USD
            
        Returns:
            List of ETFs ranked by performance score
        """
        try:
            with self.etf_query_timer("get_etf_performance_ranking"):
                base_query = """
                    SELECT 
                        symbol,
                        name,
                        etf_type,
                        aum_millions,
                        expense_ratio,
                        average_spread,
                        daily_volume_avg,
                        performance_score
                    FROM v_etf_performance_ranking
                    WHERE active = true
                """
                
                params = {'limit': limit}
                
                if min_aum is not None:
                    base_query += " AND aum_millions >= :min_aum"
                    params['min_aum'] = min_aum
                
                base_query += " ORDER BY performance_score DESC LIMIT :limit"
                
                with self.get_connection() as conn:
                    result = conn.execute(text(base_query), params)
                    
                    rankings = []
                    for row in result:
                        rankings.append({
                            'symbol': row[0],
                            'name': row[1],
                            'etf_type': row[2],
                            'aum_millions': float(row[3]) if row[3] else None,
                            'expense_ratio': float(row[4]) if row[4] else None,
                            'average_spread': float(row[5]) if row[5] else None,
                            'daily_volume_avg': int(row[6]) if row[6] else None,
                            'performance_score': float(row[7]) if row[7] else 0.0
                        })
                    
                    logger.debug(f"ETF_RANKING: Retrieved top {len(rankings)} ETFs")
                    return rankings
                    
        except Exception as e:
            logger.error(f"Failed to get ETF performance ranking: {e}")
            return []
    
    def get_etf_fmv_current(self, symbol: str, 
                           max_age_minutes: int = 15) -> Optional[Dict[str, Any]]:
        """
        Get current Fair Market Value estimate for ETF.
        
        Critical for real-time ETF analysis. Uses TimescaleDB partitioning
        and idx_etf_fmv_symbol_time for <15ms response time.
        
        Args:
            symbol: ETF symbol to lookup
            max_age_minutes: Maximum age of FMV data to consider current
            
        Returns:
            Latest FMV data or None if not available/stale
        """
        try:
            with self.etf_query_timer("get_etf_fmv_current"):
                query = """
                    SELECT 
                        nav_estimate,
                        premium_discount,
                        confidence_score,
                        component_symbols,
                        calculation_method,
                        timestamp,
                        created_at
                    FROM etf_fmv_cache 
                    WHERE symbol = :symbol
                      AND timestamp >= NOW() - INTERVAL '%s minutes'
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """ % max_age_minutes
                
                with self.get_connection() as conn:
                    result = conn.execute(text(query), {'symbol': symbol})
                    row = result.fetchone()
                    
                    if row:
                        return {
                            'symbol': symbol,
                            'nav_estimate': float(row[0]) if row[0] else None,
                            'premium_discount': float(row[1]) if row[1] else None,
                            'confidence_score': float(row[2]) if row[2] else None,
                            'component_symbols': row[3] or [],
                            'calculation_method': row[4] or '',
                            'timestamp': row[5].isoformat() if row[5] else None,
                            'created_at': row[6].isoformat() if row[6] else None,
                            'age_minutes': max_age_minutes
                        }
                    else:
                        logger.debug(f"No current FMV data for ETF {symbol}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to get current FMV for ETF {symbol}: {e}")
            return None
    
    def get_etf_fmv_history(self, symbol: str, 
                           hours_back: int = 24,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get historical Fair Market Value data for ETF trend analysis.
        
        Uses TimescaleDB compression and time-based partitioning.
        Target: <30ms for 24-hour history.
        
        Args:
            symbol: ETF symbol to lookup
            hours_back: Hours of history to retrieve
            limit: Maximum number of FMV records
            
        Returns:
            List of historical FMV estimates ordered by timestamp DESC
        """
        try:
            with self.etf_query_timer("get_etf_fmv_history"):
                query = """
                    SELECT 
                        nav_estimate,
                        premium_discount,
                        confidence_score,
                        calculation_method,
                        timestamp
                    FROM etf_fmv_cache 
                    WHERE symbol = :symbol
                      AND timestamp >= NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC 
                    LIMIT :limit
                """ % hours_back
                
                with self.get_connection() as conn:
                    result = conn.execute(text(query), {
                        'symbol': symbol,
                        'limit': limit
                    })
                    
                    history = []
                    for row in result:
                        history.append({
                            'nav_estimate': float(row[0]) if row[0] else None,
                            'premium_discount': float(row[1]) if row[1] else None,
                            'confidence_score': float(row[2]) if row[2] else None,
                            'calculation_method': row[3] or '',
                            'timestamp': row[4].isoformat() if row[4] else None
                        })
                    
                    logger.debug(f"ETF_FMV_HISTORY: Retrieved {len(history)} records for {symbol}")
                    return history
                    
        except Exception as e:
            logger.error(f"Failed to get FMV history for ETF {symbol}: {e}")
            return []
    
    def get_etf_classifications(self, symbol: str = None,
                               classification_type: str = None) -> List[Dict[str, Any]]:
        """
        Get ETF sector/theme classifications for analysis.
        
        Uses idx_etf_sector_class and idx_etf_symbol_class indexes.
        Target: <20ms for classification queries.
        
        Args:
            symbol: Specific ETF symbol (optional)
            classification_type: Filter by type ('sector', 'theme', 'strategy', 'geography')
            
        Returns:
            List of ETF classifications with weights
        """
        try:
            with self.etf_query_timer("get_etf_classifications"):
                base_query = """
                    SELECT 
                        ec.symbol,
                        s.name as etf_name,
                        ec.classification_type,
                        ec.classification_value,
                        ec.weight_percentage,
                        ec.source,
                        ec.last_updated
                    FROM etf_classifications ec
                    JOIN symbols s ON ec.symbol = s.symbol
                    WHERE s.active = true
                """
                
                conditions = []
                params = {}
                
                if symbol:
                    conditions.append("ec.symbol = :symbol")
                    params['symbol'] = symbol
                    
                if classification_type:
                    conditions.append("ec.classification_type = :classification_type")
                    params['classification_type'] = classification_type
                
                if conditions:
                    base_query += " AND " + " AND ".join(conditions)
                
                base_query += " ORDER BY ec.symbol, ec.classification_type, ec.weight_percentage DESC"
                
                with self.get_connection() as conn:
                    result = conn.execute(text(base_query), params)
                    
                    classifications = []
                    for row in result:
                        classifications.append({
                            'symbol': row[0],
                            'etf_name': row[1],
                            'classification_type': row[2],
                            'classification_value': row[3],
                            'weight_percentage': float(row[4]) if row[4] else None,
                            'source': row[5],
                            'last_updated': row[6].isoformat() if row[6] else None
                        })
                    
                    logger.debug(f"ETF_CLASSIFICATIONS: Retrieved {len(classifications)} records")
                    return classifications
                    
        except Exception as e:
            logger.error(f"Failed to get ETF classifications: {e}")
            return []
    
    def get_etf_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive ETF statistics for dashboard display.
        
        Combines multiple optimized queries for ETF overview.
        Target: <40ms for complete dashboard statistics.
        
        Returns:
            Dictionary with ETF counts, averages, and top performers
        """
        stats = {
            'total_etfs': 0,
            'active_etfs': 0,
            'etf_types': {},
            'top_issuers': [],
            'avg_expense_ratio': None,
            'avg_aum_millions': None,
            'largest_etf': {},
            'lowest_cost_etf': {},
            'newest_etfs': []
        }
        
        try:
            with self.etf_query_timer("get_etf_dashboard_stats"):
                with self.get_connection() as conn:
                    # Total and active ETF counts
                    result = conn.execute(text("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE active = true) as active
                        FROM symbols 
                        WHERE etf_type IS NOT NULL
                    """))
                    row = result.fetchone()
                    if row:
                        stats['total_etfs'] = int(row[0])
                        stats['active_etfs'] = int(row[1])
                    
                    # ETF type distribution
                    result = conn.execute(text("""
                        SELECT etf_type, COUNT(*) 
                        FROM symbols 
                        WHERE etf_type IS NOT NULL AND active = true
                        GROUP BY etf_type 
                        ORDER BY COUNT(*) DESC
                    """))
                    stats['etf_types'] = {row[0]: int(row[1]) for row in result}
                    
                    # Top issuers
                    result = conn.execute(text("""
                        SELECT issuer, COUNT(*) 
                        FROM symbols 
                        WHERE etf_type IS NOT NULL 
                          AND active = true 
                          AND issuer IS NOT NULL
                        GROUP BY issuer 
                        ORDER BY COUNT(*) DESC 
                        LIMIT 5
                    """))
                    stats['top_issuers'] = [{'issuer': row[0], 'count': int(row[1])} for row in result]
                    
                    # Average metrics
                    result = conn.execute(text("""
                        SELECT 
                            AVG(expense_ratio) as avg_expense,
                            AVG(aum_millions) as avg_aum
                        FROM symbols 
                        WHERE etf_type IS NOT NULL 
                          AND active = true
                          AND expense_ratio IS NOT NULL
                          AND aum_millions IS NOT NULL
                    """))
                    row = result.fetchone()
                    if row:
                        stats['avg_expense_ratio'] = float(row[0]) if row[0] else None
                        stats['avg_aum_millions'] = float(row[1]) if row[1] else None
                    
                    # Largest ETF by AUM
                    result = conn.execute(text("""
                        SELECT symbol, name, aum_millions 
                        FROM symbols 
                        WHERE etf_type IS NOT NULL 
                          AND active = true 
                          AND aum_millions IS NOT NULL
                        ORDER BY aum_millions DESC 
                        LIMIT 1
                    """))
                    row = result.fetchone()
                    if row:
                        stats['largest_etf'] = {
                            'symbol': row[0],
                            'name': row[1],
                            'aum_millions': float(row[2])
                        }
                    
                    # Lowest cost ETF
                    result = conn.execute(text("""
                        SELECT symbol, name, expense_ratio 
                        FROM symbols 
                        WHERE etf_type IS NOT NULL 
                          AND active = true 
                          AND expense_ratio IS NOT NULL
                        ORDER BY expense_ratio ASC 
                        LIMIT 1
                    """))
                    row = result.fetchone()
                    if row:
                        stats['lowest_cost_etf'] = {
                            'symbol': row[0],
                            'name': row[1],
                            'expense_ratio': float(row[2])
                        }
                    
                    # Newest ETFs
                    result = conn.execute(text("""
                        SELECT symbol, name, inception_date 
                        FROM symbols 
                        WHERE etf_type IS NOT NULL 
                          AND active = true 
                          AND inception_date IS NOT NULL
                        ORDER BY inception_date DESC 
                        LIMIT 5
                    """))
                    stats['newest_etfs'] = [
                        {
                            'symbol': row[0],
                            'name': row[1],
                            'inception_date': row[2].isoformat() if row[2] else None
                        } for row in result
                    ]
                    
                    logger.debug("ETF_DASHBOARD: Retrieved comprehensive statistics")
                    return stats
                    
        except Exception as e:
            logger.error(f"Failed to get ETF dashboard statistics: {e}")
            stats['error'] = str(e)
            return stats
    
    def calculate_etf_liquidity_score(self, symbol: str) -> Optional[float]:
        """
        Calculate liquidity score for ETF using database function.
        
        Wraps the PostgreSQL calculate_etf_liquidity_score function.
        Target: <10ms for single ETF liquidity calculation.
        
        Args:
            symbol: ETF symbol to analyze
            
        Returns:
            Liquidity score (0.0-1.0) or None if calculation fails
        """
        try:
            with self.etf_query_timer("calculate_etf_liquidity_score"):
                with self.get_connection() as conn:
                    result = conn.execute(text("""
                        SELECT calculate_etf_liquidity_score(:symbol)
                    """), {'symbol': symbol})
                    
                    score = result.scalar()
                    if score is not None:
                        logger.debug(f"ETF_LIQUIDITY: {symbol} score = {score:.3f}")
                        return float(score)
                    else:
                        logger.warning(f"No liquidity score available for ETF {symbol}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to calculate liquidity score for ETF {symbol}: {e}")
            return None

# Integration example for TickStockDatabase class
"""
To integrate these ETF methods into the existing TickStockDatabase class:

class TickStockDatabase(ETFDatabaseMixin):
    # ... existing methods ...
    
    def get_symbols_for_dropdown(self, include_etfs=True, etf_filter=None):
        '''Enhanced symbol dropdown with ETF filtering options.'''
        if include_etfs and etf_filter:
            return self.get_etf_symbols_for_dropdown(**etf_filter)
        else:
            # Call existing implementation
            return self._get_symbols_for_dropdown_original()
    
    def get_enhanced_dashboard_stats(self):
        '''Extended dashboard stats including ETF metrics.'''
        basic_stats = self.get_basic_dashboard_stats()
        etf_stats = self.get_etf_dashboard_stats()
        
        return {
            **basic_stats,
            'etf_data': etf_stats
        }
"""