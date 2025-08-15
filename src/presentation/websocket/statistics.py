"""
WebSocket Statistics Tracking

Handles emission statistics and performance metrics for WebSocket operations.
"""

from config.logging_config import get_domain_logger, LogDomain
import time
from typing import Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = get_domain_logger(LogDomain.CORE, 'websocket_statistics')


@dataclass
class EmissionStats:
    """Track emission statistics."""
    emissions_attempted: int = 0
    emissions_successful: int = 0
    users_reached: int = 0
    events_sent: int = 0
    events_filtered: int = 0
    last_log_time: float = field(default_factory=time.time)
    log_interval: int = 30
    
    def log_emission(self, users_count, events_count, success=True):
        self.emissions_attempted += 1
        if success:
            self.emissions_successful += 1
            self.users_reached += users_count
            self.events_sent += events_count
    
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self):
        success_rate = (self.emissions_successful / self.emissions_attempted * 100) if self.emissions_attempted > 0 else 0
        logger.info(f"📊 EMISSION STATS: {self.emissions_successful}/{self.emissions_attempted} emissions "
                   f"({success_rate:.0f}% success) → {self.users_reached} users → {self.events_sent} events")
        self.last_log_time = time.time()


class WebSocketStatistics:
    """Tracks WebSocket emission statistics and performance metrics."""
    
    def __init__(self):
        """Initialize statistics tracking."""
        self.emission_stats = EmissionStats()
        
        # Initialize filter statistics (moved from results_filter_stats)
        self.filter_stats = {
            'total_highs_before_filter': 0,
            'total_lows_before_filter': 0,
            'highs_sent_to_frontend': 0,
            'lows_sent_to_frontend': 0,
            'highs_filtered_out': 0,
            'lows_filtered_out': 0,
            'trending_up_before_filter': 0,
            'trending_down_before_filter': 0,
            'trending_up_sent': 0,
            'trending_down_sent': 0,
            'trending_up_filtered': 0,
            'trending_down_filtered': 0,
            'surging_up_before_filter': 0,
            'surging_down_before_filter': 0,
            'surging_up_sent': 0,
            'surging_down_sent': 0,
            'surging_up_filtered': 0,
            'surging_down_filtered': 0,
            'last_stats_log': time.time(),
            'emissions_count': 0,
            'total_payload_size_bytes': 0,
            'avg_filter_processing_time': 0,
            'user_filters_applied': 0,
            'user_filters_cache_hits': 0,
            'user_filters_cache_misses': 0,
            'user_universe_cache_hits': 0,
            'user_universe_cache_misses': 0,
            'user_universe_loads': 0,
            'filtered_events_details': {
                'high_events': [],
                'low_events': [],
                'trending_events': [],
                'surging_events': []
            },
            'universe_coverage_analysis': {
                'last_analysis_time': 0,
                'coverage_by_universe': {},
                'most_filtered_universes': {},
                'filter_efficiency_score': 0
            }
        }
        
    '''
    def track_emission(self, users_count: int, events_count: int, success: bool = True):
        """Track emission statistics."""
        self.emission_stats.log_emission(users_count, events_count, success)
    '''
    '''
    def should_log_stats(self) -> bool:
        """Check if it's time to log statistics."""
        return self.emission_stats.should_log()
    '''
    '''
    def log_performance(self):
        """Log performance metrics."""
        self.emission_stats.log_stats()
    '''
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics summary."""
        return {
            'emission_stats': {
                'attempted': self.emission_stats.emissions_attempted,
                'successful': self.emission_stats.emissions_successful,
                'success_rate': (self.emission_stats.emissions_successful / 
                                self.emission_stats.emissions_attempted * 100) 
                                if self.emission_stats.emissions_attempted > 0 else 0,
                'users_reached': self.emission_stats.users_reached,
                'events_sent': self.emission_stats.events_sent
            },
            'filter_stats': self.get_filter_summary(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_filter_summary(self) -> Dict[str, Any]:
        """Get current filter statistics summary."""
        stats = self.filter_stats
        
        # Calculate totals
        total_events_before = (
            stats['total_highs_before_filter'] + stats['total_lows_before_filter'] + 
            stats['trending_up_before_filter'] + stats['trending_down_before_filter'] +
            stats['surging_up_before_filter'] + stats['surging_down_before_filter']
        )
        
        total_events_sent = (
            stats['highs_sent_to_frontend'] + stats['lows_sent_to_frontend'] + 
            stats['trending_up_sent'] + stats['trending_down_sent'] +
            stats['surging_up_sent'] + stats['surging_down_sent']
        )
        
        total_events_filtered = total_events_before - total_events_sent
        filter_rate = round((total_events_filtered / total_events_before) * 100, 1) if total_events_before > 0 else 0
        
        return {
            'total_events_processed': total_events_before,
            'total_events_sent': total_events_sent,
            'total_events_filtered': total_events_filtered,
            'overall_filter_rate': filter_rate,
            'by_category': {
                'highs': {
                    'sent': stats['highs_sent_to_frontend'], 
                    'filtered': stats['highs_filtered_out']
                },
                'lows': {
                    'sent': stats['lows_sent_to_frontend'], 
                    'filtered': stats['lows_filtered_out']
                },
                'trending': {
                    'sent': stats['trending_up_sent'] + stats['trending_down_sent'], 
                    'filtered': stats['trending_up_filtered'] + stats['trending_down_filtered']
                },
                'surging': {
                    'sent': stats['surging_up_sent'] + stats['surging_down_sent'],
                    'filtered': stats['surging_up_filtered'] + stats['surging_down_filtered']
                }
            }
        }
    '''
    def update_before_filter_stats(self, data: Dict):
        counts = self._count_events(data, detailed=True)
        self.increment_filter_stat('total_highs_before_filter', counts['highs'])
        self.increment_filter_stat('total_lows_before_filter', counts['lows'])
        self.increment_filter_stat('trending_up_before_filter', counts['trending_up'])
        self.increment_filter_stat('trending_down_before_filter', counts['trending_down'])
        self.increment_filter_stat('surging_up_before_filter', counts['surging_up'])
        self.increment_filter_stat('surging_down_before_filter', counts['surging_down'])
    
    def update_after_filter_stats(self, data: Dict):
        counts = self._count_events(data, detailed=True)
        self.increment_filter_stat('highs_sent_to_frontend', counts['highs'])
        self.increment_filter_stat('lows_sent_to_frontend', counts['lows'])
        self.increment_filter_stat('trending_up_sent', counts['trending_up'])
        self.increment_filter_stat('trending_down_sent', counts['trending_down'])
        self.increment_filter_stat('surging_up_sent', counts['surging_up'])
        self.increment_filter_stat('surging_down_sent', counts['surging_down'])

    '''
    def _count_events(self, data: Dict, detailed: bool = False) -> Dict[str, int]:
        """Count events in data structure."""
        trending = data.get('trending', {})
        surging = data.get('surging', {})  # Sprint 17: Now a dict with 'up' and 'down'
        
        counts = {
            'highs': len(data.get('highs', [])),
            'lows': len(data.get('lows', [])),
            'trending': len(trending.get('up', [])) + len(trending.get('down', [])),
            'surging': len(surging.get('up', [])) + len(surging.get('down', []))  # Sprint 17: Updated
        }
        
        if detailed:
            counts.update({
                'trending_up': len(trending.get('up', [])),
                'trending_down': len(trending.get('down', [])),
                'surging_up': len(surging.get('up', [])),  # Sprint 17: Direct access
                'surging_down': len(surging.get('down', []))  # Sprint 17: Direct access
            })
        
        return counts

    '''
    def update_filter_stats(self, stat_key: str, value: Any):
        """Update a specific filter statistic."""
        if stat_key in self.filter_stats:
            if isinstance(value, (int, float)):
                self.filter_stats[stat_key] = value
            else:
                logger.warning(f"WEBSOCKET-STAT: Invalid value type for stat {stat_key}: {type(value)}")
    '''    
    def increment_filter_stat(self, stat_key: str, increment: int = 1):
        """Increment a specific filter statistic."""
        if stat_key in self.filter_stats:
            self.filter_stats[stat_key] += increment
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get the raw filter statistics dictionary for backward compatibility."""
        return self.filter_stats
    def update_average_filter_time(self, new_time: float):
        """Update the rolling average filter processing time."""
        current_avg = self.filter_stats['avg_filter_processing_time']
        count = self.filter_stats['emissions_count']
        if count > 0:
            new_avg = (current_avg * (count - 1) + new_time) / count
            self.filter_stats['avg_filter_processing_time'] = new_avg