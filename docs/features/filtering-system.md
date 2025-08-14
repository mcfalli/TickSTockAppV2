# User Filtering System Architecture

**Version:** 2.0  
**Last Updated:** JUNE 2025
**Status:** Production Architecture

## Overview

TickStock provides comprehensive per-user filtering capabilities that allow authenticated users to customize their data streams. The system integrates with the DataPublisher component to apply filters in real-time.

## Architecture
Filter System Components
├── UserFiltersService (Database operations)
├── Filter Cache (Per-user memory cache)
├── Filter Validation (Data integrity)
└── Filter Application (Real-time processing)

## Filter Categories

### High/Low Events
Filter events based on occurrence count and volume thresholds.

```python
highlow_filters = {
    'min_count': 25,        # Minimum event count
    'min_volume': 100000    # Minimum volume threshold
}
Trending Stocks
Filter trends by strength, VWAP position, and age.
pythontrend_filters = {
    'strength': 'moderate',           # weak|moderate|strong
    'vwap_position': 'any_vwap_position',  # above_vwap|below_vwap|any
    'min_age': 30,                   # Minimum age in seconds
    'max_age': 300,                  # Maximum age in seconds
    'volume_confirmation': False      # Require volume backing
}
Surge Events
Filter surges by magnitude, trigger type, and recency.
pythonsurge_filters = {
    'magnitude_threshold': 2.0,      # Minimum percentage change
    'min_age': 15,                   # Minimum age in seconds
    'max_age': 120,                  # Maximum age in seconds
    'trigger_types': ['price', 'volume', 'price_and_volume'],
    'price_ranges': ['penny', 'low', 'mid', 'high']
}
Core Components
UserFiltersService
pythonclass UserFiltersService:
    """Database operations for user filters."""
    
    def __init__(self):
        self.validation = FilterValidator()
    
    def load_user_filters(self, user_id: int, 
                         filter_name: str = 'default') -> Dict:
        """Load filters from database."""
        filter_record = UserFilters.query.filter_by(
            user_id=user_id,
            filter_name=filter_name
        ).first()
        
        if not filter_record:
            return self.get_default_filters()
            
        return json.loads(filter_record.filter_data)
    
    def save_user_filters(self, user_id: int, 
                         filter_data: Dict) -> bool:
        """Validate and save filters."""
        # Validate filter structure
        is_valid, errors = self.validation.validate(filter_data)
        if not is_valid:
            raise ValueError(f"Invalid filters: {errors}")
        
        # Save to database
        filter_record = UserFilters.query.filter_by(
            user_id=user_id
        ).first()
        
        if not filter_record:
            filter_record = UserFilters(user_id=user_id)
            
        filter_record.filter_data = json.dumps(filter_data)
        db.session.commit()
        
        return True
Filter Cache Management
pythonclass FilterCache:
    """Per-user filter caching."""
    
    def __init__(self):
        self.cache = {}  # user_id -> filter_data
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
    
    def get_or_load(self, user_id: int) -> Dict:
        """Get from cache or load from database."""
        if user_id in self.cache:
            self.stats['hits'] += 1
            return self.cache[user_id]
        
        self.stats['misses'] += 1
        filters = self.load_from_database(user_id)
        self.cache[user_id] = filters
        return filters
    
    def invalidate(self, user_id: int):
        """Remove user from cache."""
        if user_id in self.cache:
            del self.cache[user_id]
            self.stats['invalidations'] += 1
Filter Application Pipeline
Integration with DataPublisher
pythonclass DataPublisher:
    def _apply_user_filters(self, stock_data: Dict, 
                           user_id: int) -> Dict:
        """Apply filters in publishing pipeline."""
        # Get user's filters
        filters = self.filter_cache.get_or_load(user_id)
        
        # Apply each category
        filtered_data = {
            'highs': self._filter_highlow_events(
                stock_data['highs'], filters['highlow']
            ),
            'lows': self._filter_highlow_events(
                stock_data['lows'], filters['highlow']
            ),
            'trending': self._filter_trending(
                stock_data['trending'], filters['trends']
            ),
            'surging': self._filter_surges(
                stock_data['surging'], filters['surges']
            )
        }
        
        # Add filter statistics
        filtered_data['filter_stats'] = self._calculate_filter_stats(
            stock_data, filtered_data
        )
        
        return filtered_data
Filter Implementation
pythondef _filter_highlow_events(self, events: List[Dict], 
                          filters: Dict) -> List[Dict]:
    """Apply high/low filters."""
    min_count = filters.get('min_count', 0)
    min_volume = filters.get('min_volume', 0)
    
    return [
        event for event in events
        if event.get('count', 0) >= min_count and
           event.get('volume', 0) >= min_volume
    ]

def _filter_trending(self, trending_data: Dict, 
                    filters: Dict) -> Dict:
    """Apply trend filters."""
    strength_filter = filters.get('strength', 'weak')
    vwap_filter = filters.get('vwap_position', 'any')
    
    filtered = {'up': [], 'down': []}
    
    for direction in ['up', 'down']:
        for stock in trending_data.get(direction, []):
            if self._matches_trend_criteria(stock, filters):
                filtered[direction].append(stock)
    
    return filtered
Frontend Integration
Filter Modal UI
javascript// Filter configuration interface
class FilterManager {
    constructor() {
        this.filters = this.loadCurrentFilters();
        this.modal = document.getElementById('userFiltersModal');
    }
    
    async saveFilters() {
        const filterData = this.collectFilterData();
        
        const response = await fetch('/api/user-filters', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrfToken
            },
            body: JSON.stringify({filter_data: filterData})
        });
        
        if (response.ok) {
            this.showSuccess('Filters saved successfully');
            // Data automatically updates via WebSocket
        }
    }
}
Real-time Updates
javascript// Filters applied automatically on WebSocket data
socket.on('dual_universe_stock_data', (data) => {
    // Data arrives pre-filtered per user settings
    updateHighLowGrid(data.highs, data.lows);
    updateTrendingPanel(data.trending);
    updateSurgeList(data.surging);
    
    // Display filter statistics
    if (data.filter_stats) {
        updateFilterStats(data.filter_stats);
    }
});
API Endpoints
Get Filters
GET /api/user-filters
Authorization: Required
Save Filters
POST /api/user-filters
Authorization: Required
Content-Type: application/json

{
    "filter_data": {
        "filters": {
            "highlow": {...},
            "trends": {...},
            "surges": {...}
        }
    }
}
Clear Cache
POST /api/user-filters/cache/invalidate
Authorization: Required
Performance Considerations
Caching Strategy
python# Cache configuration
FILTER_CACHE_TTL = 3600  # 1 hour
FILTER_CACHE_MAX_SIZE = 10000  # Maximum users in cache

# Cache warming for active users
def warm_filter_cache(self):
    """Pre-load filters for recently active users."""
    recent_users = self.get_recently_active_users(minutes=30)
    for user_id in recent_users:
        self.filter_cache.get_or_load(user_id)
Filter Optimization
python# Pre-compile filter functions for performance
class OptimizedFilters:
    def __init__(self, filters):
        self.compiled = self._compile_filters(filters)
    
    def _compile_filters(self, filters):
        """Create optimized filter functions."""
        return {
            'highlow': lambda e: (
                e.get('count', 0) >= filters['highlow']['min_count'] and
                e.get('volume', 0) >= filters['highlow']['min_volume']
            )
        }
Monitoring
Filter Metrics
pythondef get_filter_metrics():
    return {
        'cache_performance': {
            'hit_rate': calculate_cache_hit_rate(),
            'size': len(filter_cache.cache),
            'avg_load_time_ms': get_avg_load_time()
        },
        'filter_usage': {
            'users_with_filters': count_users_with_filters(),
            'most_common_filters': analyze_filter_patterns(),
            'avg_filter_complexity': calculate_complexity()
        },
        'performance': {
            'avg_filter_time_ms': get_avg_filter_time(),
            'filtered_events_ratio': calculate_filter_ratio()
        }
    }
Best Practices
Filter Design

Start with sensible defaults
Validate all filter inputs
Provide clear UI feedback
Cache aggressively but invalidate properly

Performance

Apply filters after universe filtering
Use compiled filter functions
Monitor cache effectiveness
Profile filter performance regularly

User Experience

Save filters immediately
Show filter effects in real-time
Provide filter statistics
Allow filter presets

Development Checklist

 Validate filter structure on save
 Implement proper cache invalidation
 Add filter statistics to WebSocket data
 Monitor filter performance impact
 Test with extreme filter values
 Document filter effects clearly
 Provide filter import/export
 Add filter preset management