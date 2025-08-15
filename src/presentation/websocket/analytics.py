"""
WebSocket Analytics Processor

Prepares analytics data for WebSocket emission.
"""
import json
from config.logging_config import get_domain_logger, LogDomain
from typing import Dict, Optional, Any
from datetime import datetime

logger = get_domain_logger(LogDomain.CORE, 'websocket_analytics')


class WebSocketAnalytics:
    """Prepares analytics data for WebSocket emission."""
    
    def __init__(self, cache_control=None, config=None):
        """Initialize analytics processor."""
        self.cache_control = cache_control
    
    def prepare_enhanced_dual_universe_data(self, stock_data: Dict, 
                                        analytics_data: Dict, 
                                        user_id: int) -> Dict:
        """Prepare data with new structure."""
        try:
            # Start with original stock data
            enhanced_data = stock_data.copy()
            
            # Create new activity section with all metrics
            enhanced_data['activity'] = self._create_activity_section(analytics_data)
            
            # Clean up deprecated fields
            self._cleanup_deprecated_fields(enhanced_data)
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error preparing enhanced data: {e}")
            return stock_data
    

    def _create_activity_section(self, analytics_data: Dict) -> Dict:
        """Create new activity section with all activity metrics."""
        try:
            # Get activity metrics from analytics data
            activity_metrics = analytics_data.get('activity_metrics', {})
            
            return activity_metrics  # MarketMetrics already provides the right structure
            
        except Exception as e:
            logger.error(f"Error creating activity section: {e}")
            return {
                'total_highs': 0,
                'total_lows': 0,
                'activity_level': 'Medium',
                'activity_ratio': {
                    'calculation_method': 'ticks_per_minute',
                    'current_rate': 0,
                    'threshold_low': 30,
                    'threshold_medium': 60,
                    'threshold_high': 120,
                    'threshold_very_high': 240
                },
                'ticks_10sec': 0,
                'ticks_30sec': 0,
                'ticks_60sec': 0,
                'ticks_300sec': 0
            }
        
    def _cleanup_deprecated_fields(self, data: Dict) -> None:
        """Remove deprecated fields from data structure."""
        deprecated_fields = [
            'counts',  # Moved to activity section
            'activity_level',  # Moved to activity section
            'simple_averages',  # Technical debt - not used
            'current_state',  # Technical debt - redundant
            'aggregation_info',  # Technical debt - internal metrics
            '_frontend_mapping',
            'dual_universe_metadata',
            'analytics_metadata',
            'core_analytics',  # ADDED: Remove core analytics if present
            'core_universe_analytics'  # ADDED: Remove legacy name if present
        ]
        
        for field in deprecated_fields:
            data.pop(field, None)
        
        # Also clean up nested last_updated fields
        if 'core_analytics' in data:
            for section in ['gauge_analytics', 'vertical_analytics']:
                if section in data['core_analytics'] and 'last_updated' in data['core_analytics'][section]:
                    data['core_analytics'][section].pop('last_updated', None)


    def _calculate_activity_level(self, stock_data: Dict) -> str:
        """
        Calculate activity level based on event frequency.
        
        Args:
            stock_data: Current stock data
            
        Returns:
            str: Activity level (Low, Medium, High, Very High)
        """
        try:
            # Count total events in current emission
            total_events = (
                len(stock_data.get('highs', [])) +
                len(stock_data.get('lows', [])) +
                len(stock_data.get('trending', {}).get('up', [])) +
                len(stock_data.get('trending', {}).get('down', [])) +
                len(stock_data.get('surging', {}).get('up', [])) +
                len(stock_data.get('surging', {}).get('down', []))
            )
            
            # Define thresholds (adjust based on your system's typical volumes)
            if total_events >= 50:
                return 'Very High'
            elif total_events >= 25:
                return 'High'
            elif total_events >= 10:
                return 'Medium'
            else:
                return 'Low'
                
        except Exception as e:
            logger.error(f"Error calculating activity level: {e}")
            return 'Medium'

    
    def _get_session_counts(self, analytics_data: Dict, stock_data: Dict) -> Dict[str, int]:
        """
        Get session counts from analytics data or accumulation manager.
        
        Args:
            analytics_data: Analytics data that should contain session totals
            stock_data: Current stock data (used only as last resort)
            
        Returns:
            dict: Session counts with total_highs and total_lows
        """
        try:
            # First priority: Check if counts are in analytics_data.session_totals
            if analytics_data and 'session_totals' in analytics_data:
                session_totals = analytics_data['session_totals']
                counts = {
                    'total_highs': session_totals.get('total_highs', 0),
                    'total_lows': session_totals.get('total_lows', 0)
                }
                logger.debug(f"📊 Using session totals from analytics_data: {counts}")
                return counts
            
            # Second priority: Check if counts are in analytics_data directly
            if analytics_data:
                if 'total_highs' in analytics_data and 'total_lows' in analytics_data:
                    counts = {
                        'total_highs': analytics_data.get('total_highs', 0),
                        'total_lows': analytics_data.get('total_lows', 0)
                    }
                    logger.debug(f"📊 Using counts from analytics_data root: {counts}")
                    return counts
            
            # Last resort: Log warning and return zeros (don't count current events)
            logger.warning("⚠️ Session totals not found in analytics_data - returning zeros")
            logger.debug(f"Analytics data keys: {list(analytics_data.keys()) if analytics_data else 'None'}")
            
            # Return zeros instead of counting current events
            return {
                'total_highs': 0,
                'total_lows': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting session counts: {e}", exc_info=True)
            return {'total_highs': 0, 'total_lows': 0}
    
    def _create_default_gauge_analytics(self, net_score: float) -> Dict:
        """Create default gauge analytics structure."""
        return {
            'ema_net_score': net_score,
            'current_net_score': net_score,
            'alpha_used': 0.3,
            'sample_count': 0,
            'last_updated': datetime.now().isoformat()
        }
    
    def _create_default_vertical_analytics(self, net_score: float, data: Dict) -> Dict:
        """Create default vertical analytics structure."""
        return {
            'ema_net_score': net_score,
            'current_weighted_score': net_score,
            'weighted_alpha': 0.2,
            'volume_weight': 0,
            'max_activity_seen': data.get('activity_count', 45000),
            'last_updated': datetime.now().isoformat()
        }
    
    def _calculate_simple_averages(self, gauge_data: Dict, market_data: Dict) -> Dict:
        """Calculate simple averages for analytics."""
        net_score = gauge_data.get('current_net_score', 0)
        return {
            'avg_net_score_10sec': net_score,
            'avg_net_score_60sec': net_score,
            'avg_net_score_300sec': net_score,
            'avg_activity_60sec': market_data.get('activity_count', 0)
        }
    
    def _get_core_universe_stock_count(self) -> int:
        """Get actual core universe stock count from cache control."""
        try:
            if self.cache_control:
                if hasattr(self.cache_control, 'get_core_universe_tickers'):
                    core_tickers = self.cache_control.get_core_universe_tickers('tickstock_core')
                    return len(core_tickers)
                elif hasattr(self.cache_control, 'get_core_universe_stats'):
                    core_stats = self.cache_control.get_core_universe_stats()
                    return core_stats.get('total_core_stocks', 2800)
            return 2800
        except Exception as e:
            logger.error(f"Error getting core universe stock count: {e}")
            return 2800
    
    def _get_user_universe_stock_count(self, user_id: Optional[int]) -> int:
        """Get user universe stock count."""
        # This would need access to universe cache to get actual count
        # For now, return default
        return 800
    
    def _cleanup_data(self, data: Dict):
        """Remove unnecessary fields from data."""
        cleanup_fields = [
            '_frontend_mapping',
            'dual_universe_metadata', 
            'analytics_metadata',
            'source',
            'is_synthetic'
        ]
        
        for field in cleanup_fields:
            data.pop(field, None)
    
