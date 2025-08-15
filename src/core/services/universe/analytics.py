"""
Universe Analytics - Sprint 6B
Handles universe statistics, analysis, and reporting.
Extracted from src.core.services.universe_coordinator.py
"""

import logging
import time
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.UNIVERSE_TRACKING, 'universe_analytics')

class DataFlowStats:
    """Track universe analytics data flow."""
    def __init__(self):
        self.ticks_analyzed = 0
        self.ticks_in_universe = 0
        self.ticks_filtered = 0
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
    
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self, logger):
        filter_rate = 0
        if self.ticks_analyzed > 0:
            filter_rate = (self.ticks_filtered / self.ticks_analyzed) * 100
        
        logger.info(
            f"📊 UNIVERSE ANALYTICS: Analyzed:{self.ticks_analyzed} → "
            f"InUniverse:{self.ticks_in_universe} → Filtered:{self.ticks_filtered} "
            f"(Filter rate: {filter_rate:.1f}%)"
        )
        self.last_log_time = time.time()

@dataclass
class UniverseMetrics:
    """Data class for universe metrics."""
    total_tickers: int = 0
    unique_tickers: int = 0
    overlap_count: int = 0
    coverage_percentage: float = 0.0
    efficiency_percentage: float = 0.0
    timestamp: float = field(default_factory=time.time)

class UniverseAnalytics:
    """
    Handles all universe-related analytics and statistics.
    
    Responsibilities:
    - Track universe coverage and overlap
    - Calculate efficiency metrics
    - Generate universe reports
    - Monitor universe performance
    """
    
    def __init__(self, config, cache_control):
        """Initialize universe analytics."""
        self.config = config
        self.cache_control = cache_control
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        # Analytics storage
        self.universe_metrics = defaultdict(lambda: UniverseMetrics())
        self.processing_stats = {
            'total_ticks_received': 0,
            'ticks_in_universe': 0,
            'ticks_filtered_out': 0,
            'filter_rate_percentage': 0.0,
            'last_calculation': 0
        }
        
        # Historical tracking
        self.historical_metrics = defaultdict(list)  # user_id -> list of metrics
        self.max_history_size = config.get('UNIVERSE_ANALYTICS_HISTORY_SIZE', 100)
        
        logger.info("✅ UniverseAnalytics initialized")
    
    def analyze_subscription_coverage(self, subscribed_tickers: List[str], 
                                    universe_selections: List[str], 
                                    user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze coverage between subscriptions and universe selections.
        
        Args:
            subscribed_tickers: List of subscribed tickers
            universe_selections: List of selected universe keys
            user_id: Optional user ID for user-specific analysis
            
        Returns:
            dict: Coverage analysis results
        """
        try:
            # Get universe tickers
            universe_tickers = set()
            for universe_key in universe_selections:
                try:
                    tickers = self.cache_control.get_universe_tickers(universe_key)
                    universe_tickers.update(tickers)
                except Exception as e:
                    logger.error(f"❌ Failed to get tickers for universe {universe_key}: {e}")
            
            # Convert to sets for analysis
            subscribed_set = set(subscribed_tickers)
            
            # Calculate metrics
            overlap = subscribed_set & universe_tickers
            coverage_percentage = 0
            if universe_tickers:
                coverage_percentage = (len(overlap) / len(universe_tickers)) * 100
            
            efficiency_percentage = 0
            if subscribed_set:
                efficiency_percentage = (len(overlap) / len(subscribed_set)) * 100
            
            # Create metrics object
            metrics = UniverseMetrics(
                total_tickers=len(subscribed_set),
                unique_tickers=len(universe_tickers),
                overlap_count=len(overlap),
                coverage_percentage=round(coverage_percentage, 2),
                efficiency_percentage=round(efficiency_percentage, 2)
            )
            
            # Store metrics
            if user_id:
                self.universe_metrics[user_id] = metrics
                self._add_to_history(user_id, metrics)
                # Log first analysis for user
                if len(self.historical_metrics[user_id]) == 1:
                    logger.info(
                        f"📥 USER {user_id} UNIVERSE: {len(universe_tickers)} tickers, "
                        f"Coverage: {coverage_percentage:.1f}%"
                    )
            else:
                self.universe_metrics['global'] = metrics
            
            # Log poor coverage
            if coverage_percentage < 80:
                logger.warning(
                    f"⚠️ Low universe coverage: {coverage_percentage:.1f}% "
                    f"for {'user ' + str(user_id) if user_id else 'global'}"
                )
            
            result = {
                'subscribed_count': len(subscribed_set),
                'universe_count': len(universe_tickers),
                'overlap_count': len(overlap),
                'coverage_percentage': metrics.coverage_percentage,
                'subscription_efficiency': metrics.efficiency_percentage,
                'missing_from_subscription': len(universe_tickers - subscribed_set),
                'extra_in_subscription': len(subscribed_set - universe_tickers),
                'universe_selections': universe_selections,
                'analysis_timestamp': metrics.timestamp
            }
            
            # Add user context if provided
            if user_id:
                result['user_id'] = user_id
                result['analysis_type'] = 'per_user'
            else:
                result['analysis_type'] = 'global'
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Coverage analysis failed: {e}")
            return {'error': str(e)}
    
    def update_processing_stats(self, ticker: str, in_universe: bool):
        """
        Update processing statistics for universe filtering.
        
        Args:
            ticker: Ticker being processed
            in_universe: Whether ticker is in selected universe
        """
        try:
            self.stats.ticks_analyzed += 1
            self.processing_stats['total_ticks_received'] += 1
            
            if in_universe:
                self.stats.ticks_in_universe += 1
                self.processing_stats['ticks_in_universe'] += 1
            else:
                self.stats.ticks_filtered += 1
                self.processing_stats['ticks_filtered_out'] += 1
            
            # Log first few filtered tickers
            if self.stats.ticks_filtered <= 5 and not in_universe:
                logger.debug(f"🔍 DIAG-UNIVERSE-FILTER: first few logged here for sample FILTERED OUT: {ticker} (not in user universe)")
            
            # Update filter rate every 100 ticks
            if self.processing_stats['total_ticks_received'] % 100 == 0:
                self._calculate_filter_rate()
            
            # Periodic stats logging
            if self.stats.should_log():
                self.stats.log_stats(logger)
                
        except Exception as e:
            logger.error(f"❌ Failed to update processing stats: {e}")
    
    def _calculate_filter_rate(self):
        """Calculate current filter rate percentage."""
        total = self.processing_stats['total_ticks_received']
        if total > 0:
            filtered = self.processing_stats['ticks_filtered_out']
            self.processing_stats['filter_rate_percentage'] = round((filtered / total) * 100, 2)
            self.processing_stats['last_calculation'] = time.time()
    
    def get_universe_comparison(self, user_ids: List[int]) -> Dict[str, Any]:
        """
        Compare universe selections across multiple users.
        
        Args:
            user_ids: List of user IDs to compare
            
        Returns:
            dict: Comparison results
        """
        try:
            # Calculate overlap between users
            comparison = {
                'users_compared': len(user_ids),
                'user_metrics': {},
                'timestamp': time.time()
            }
            
            for user_id in user_ids:
                if user_id in self.universe_metrics:
                    metrics = self.universe_metrics[user_id]
                    comparison['user_metrics'][user_id] = {
                        'total_tickers': metrics.total_tickers,
                        'coverage_percentage': metrics.coverage_percentage,
                        'efficiency_percentage': metrics.efficiency_percentage
                    }
            
            return comparison
            
        except Exception as e:
            logger.error(f"❌ Universe comparison failed: {e}")
            return {'error': str(e)}
    
    def generate_universe_report(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate comprehensive universe analytics report.
        
        Args:
            user_id: Optional user ID for user-specific report
            
        Returns:
            dict: Universe analytics report
        """
        try:
            # Base report structure
            report = {
                'report_type': 'user_specific' if user_id else 'global',
                'timestamp': time.time(),
                'processing_stats': self.processing_stats.copy(),
                'flow_stats': {
                    'ticks_analyzed': self.stats.ticks_analyzed,
                    'ticks_in_universe': self.stats.ticks_in_universe,
                    'ticks_filtered': self.stats.ticks_filtered,
                    'filter_rate': round((self.stats.ticks_filtered / self.stats.ticks_analyzed * 100) 
                                       if self.stats.ticks_analyzed > 0 else 0, 2)
                }
            }
            
            # Add specific metrics
            if user_id and user_id in self.universe_metrics:
                metrics = self.universe_metrics[user_id]
                report['current_metrics'] = {
                    'total_tickers': metrics.total_tickers,
                    'unique_tickers': metrics.unique_tickers,
                    'overlap_count': metrics.overlap_count,
                    'coverage_percentage': metrics.coverage_percentage,
                    'efficiency_percentage': metrics.efficiency_percentage,
                    'last_updated': metrics.timestamp
                }
                
                # Add historical trend if available
                if user_id in self.historical_metrics:
                    history = self.historical_metrics[user_id]
                    if len(history) > 1:
                        report['trend'] = self._calculate_trend(history)
                        
            elif 'global' in self.universe_metrics:
                metrics = self.universe_metrics['global']
                report['current_metrics'] = {
                    'total_tickers': metrics.total_tickers,
                    'unique_tickers': metrics.unique_tickers,
                    'overlap_count': metrics.overlap_count,
                    'coverage_percentage': metrics.coverage_percentage,
                    'efficiency_percentage': metrics.efficiency_percentage,
                    'last_updated': metrics.timestamp
                }
            
            # Add summary statistics
            report['summary'] = self._generate_summary_stats()
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            return {'error': str(e)}
    
    def _add_to_history(self, user_id: int, metrics: UniverseMetrics):
        """Add metrics to historical tracking."""
        history = self.historical_metrics[user_id]
        history.append(metrics)
        
        # Limit history size
        if len(history) > self.max_history_size:
            history.pop(0)
    
    def _calculate_trend(self, history: List[UniverseMetrics]) -> Dict[str, Any]:
        """Calculate trend from historical metrics."""
        if len(history) < 2:
            return {}
        
        recent = history[-1]
        previous = history[-min(10, len(history))]  # Compare to 10 periods ago
        
        return {
            'coverage_change': recent.coverage_percentage - previous.coverage_percentage,
            'efficiency_change': recent.efficiency_percentage - previous.efficiency_percentage,
            'period_count': min(10, len(history)),
            'trend_direction': 'improving' if recent.coverage_percentage > previous.coverage_percentage else 'declining'
        }
    
    def _generate_summary_stats(self) -> Dict[str, Any]:
        """Generate summary statistics across all tracked universes."""
        try:
            if not self.universe_metrics:
                return {'message': 'No universe metrics available'}
            
            # Calculate aggregates
            total_users = len([k for k in self.universe_metrics.keys() if isinstance(k, int)])
            avg_coverage = 0
            avg_efficiency = 0
            
            if total_users > 0:
                coverages = [m.coverage_percentage for k, m in self.universe_metrics.items() if isinstance(k, int)]
                efficiencies = [m.efficiency_percentage for k, m in self.universe_metrics.items() if isinstance(k, int)]
                
                avg_coverage = sum(coverages) / len(coverages) if coverages else 0
                avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
            
            return {
                'total_users_tracked': total_users,
                'average_coverage_percentage': round(avg_coverage, 2),
                'average_efficiency_percentage': round(avg_efficiency, 2),
                'processing_summary': {
                    'total_ticks': self.processing_stats['total_ticks_received'],
                    'filter_rate': self.processing_stats['filter_rate_percentage']
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Summary stats generation failed: {e}")
            return {'error': str(e)}
    
    def reset_processing_stats(self):
        """Reset processing statistics."""
        self.processing_stats = {
            'total_ticks_received': 0,
            'ticks_in_universe': 0,
            'ticks_filtered_out': 0,
            'filter_rate_percentage': 0.0,
            'last_calculation': time.time()
        }
        self.stats = DataFlowStats()  # Reset flow stats too
        logger.info("📊 Processing statistics reset")
    
    def clear_user_metrics(self, user_id: int):
        """Clear metrics for a specific user."""
        if user_id in self.universe_metrics:
            del self.universe_metrics[user_id]
        if user_id in self.historical_metrics:
            del self.historical_metrics[user_id]
        logger.info(f"🗑️ Cleared metrics for user {user_id}")
    
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if self.stats.ticks_analyzed == 0:
            logger.error("🚨 NO TICKS ANALYZED - Check if data is reaching analytics")
        elif self.stats.ticks_in_universe == 0:
            logger.error("🚨 All ticks filtered out - Check universe configuration")
        elif self.stats.ticks_filtered > self.stats.ticks_in_universe * 10:
            logger.warning("⚠️ Excessive filtering detected - Review universe selections")
        else:
            in_rate = (self.stats.ticks_in_universe / self.stats.ticks_analyzed * 100) if self.stats.ticks_analyzed > 0 else 0
            logger.info(f"✅ Universe analytics healthy: {in_rate:.1f}% pass rate")