# Documentation Warning
**DISCLAIMER**: This documentation is not current and should not be relied upon. As of August 21, 2025, it requires review to determine its relevance. Content must be evaluated for accuracy and applicability to the project. If found relevant, update and retain; if obsolete or duplicative of content elsewhere, delete.

# Multi-User Authentication & Personalization Architecture

**Version:** 2.0  
**Last Updated:** JUNE 2025
**Status:** Production Architecture

## Overview

TickStock implements enterprise-grade multi-user authentication with complete data isolation and personalization. The system provides authenticated WebSocket connections, per-user data streams, and individual preference management.

## Architecture Overview
Authentication Layer
├── Flask-Login Integration
├── Session Management (Redis)
├── WebSocket Authentication
└── CSRF Protection
Personalization Layer
├── Per-User Universe Selection
├── Individual Filter Settings
├── Personal Data Streams
└── Isolated Cache Management

## Core Components

### Authentication Flow

```python
# User login → Session creation → WebSocket auth → Data access
@app.route('/auth/login', methods=['POST'])
def login():
    user = authenticate_user(email, password)
    if user:
        login_user(user)
        return {'success': True, 'user': user.to_dict()}
WebSocket Authentication
python@socketio.on('connect')
def handle_connect():
    """Enforce authentication for WebSocket connections."""
    if not current_user.is_authenticated:
        disconnect()
        return False
    
    # Track user connection
    user_id = current_user.id
    websocket_manager.add_user_connection(user_id, request.sid)
DataPublisher Integration
The DataPublisher component handles per-user routing:
pythonclass DataPublisher:
    def publish_to_users(self):
        """Route data to authenticated users."""
        # Get connected users
        connected_users = self.websocket_mgr.get_connected_user_ids()
        
        # Process for each user
        for user_id in connected_users:
            # Apply user-specific filtering
            user_data = self._prepare_user_data(stock_data, user_id)
            
            # Emit to user's connections
            self.websocket_mgr.emit_to_user(
                user_data, user_id, 'dual_universe_stock_data'
            )
User Universe Management
UserUniverseManager Component
pythonclass UserUniverseManager:
    """Manages per-user universe preferences."""
    
    def __init__(self):
        self.cache = {}  # user_id -> selections
        self.user_settings_service = UserSettingsService()
    
    def get_user_selections(self, user_id: int) -> Dict[str, List[str]]:
        """Get user's universe selections with caching."""
        if user_id not in self.cache:
            self.cache[user_id] = self._load_from_database(user_id)
        return self.cache[user_id]
    
    def save_selections(self, user_id: int, tracker: str, 
                       universes: List[str]) -> bool:
        """Save selections and invalidate cache."""
        success = self.user_settings_service.save_universe_selection(
            user_id, tracker, universes
        )
        if success:
            self.invalidate_cache(user_id)
        return success
Cache Architecture
python# Per-user cache structure
user_cache = {
    123: {  # user_id
        'universes': {
            'market': ['DEFAULT_UNIVERSE'],
            'highlow': ['DEFAULT_UNIVERSE', 'TECH_UNIVERSE']
        },
        'filters': {
            'highlow': {'min_count': 25, 'min_volume': 100000}
        },
        'last_updated': datetime.now()
    }
}
Filter Personalization
UserFiltersService Integration
pythonclass UserFiltersService:
    """Manages per-user filter settings."""
    
    def apply_filters_to_stock_data(self, stock_data: Dict, 
                                   user_id: int) -> Dict:
        """Apply user-specific filters to data."""
        filters = self.load_user_filters(user_id)
        
        # Apply each filter category
        filtered_data = {
            'highs': self._apply_highlow_filters(
                stock_data['highs'], filters['highlow']
            ),
            'lows': self._apply_highlow_filters(
                stock_data['lows'], filters['highlow']
            ),
            'trending': self._apply_trend_filters(
                stock_data['trending'], filters['trends']
            ),
            'surging': self._apply_surge_filters(
                stock_data['surging'], filters['surges']
            )
        }
        
        return filtered_data
Data Isolation
Connection Management
pythonclass WebSocketManager:
    def __init__(self):
        self.user_connections = defaultdict(list)  # user_id -> [sid1, sid2]
    
    def emit_to_user(self, data: Dict, user_id: int, event: str):
        """Emit only to specific user's connections."""
        for sid in self.user_connections[user_id]:
            try:
                socketio.emit(event, data, room=sid)
            except Exception as e:
                logger.error(f"Failed to emit to user {user_id}: {e}")
Security Boundaries
python# API endpoint protection
@app.route('/api/user/universe-selections')
@login_required
def get_universe_selections():
    # Only access current user's data
    user_id = current_user.id
    selections = universe_manager.get_user_selections(user_id)
    return {'success': True, 'selections': selections}

# Prevent cross-user access
def validate_user_access(user_id: int, requested_user_id: int) -> bool:
    """Ensure users can only access their own data."""
    return user_id == requested_user_id
Frontend Integration
User Context
javascript// Global user context (set in template)
window.userContext = {
    username: "{{ username }}",
    isAuthenticated: true,
    userId: {{ current_user.id }}
};

// Personalized UI elements
document.querySelector('.universe-modal-title').textContent = 
    `${userContext.username}'s Universe Selection`;
Authenticated API Calls
javascript// All API calls include session authentication
fetch('/api/user-filters', {
    method: 'POST',
    credentials: 'include',  // Include session cookie
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.csrfToken  // CSRF protection
    },
    body: JSON.stringify({filter_data: filters})
});
Performance Optimization
Cache Strategy
pythonclass UserDataCache:
    """Efficient per-user caching with TTL."""
    
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, user_id: int, key: str):
        """Get cached data with TTL check."""
        if user_id in self.cache and key in self.cache[user_id]:
            entry = self.cache[user_id][key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['data']
        return None
Batch Operations
pythondef load_user_preferences_batch(self, user_ids: List[int]):
    """Load preferences for multiple users efficiently."""
    query = UserSettings.query.filter(
        UserSettings.user_id.in_(user_ids)
    ).all()
    
    # Build cache in one operation
    for setting in query:
        self.cache[setting.user_id] = setting.to_dict()
Monitoring
User Metrics
pythondef get_user_system_metrics():
    return {
        'active_users': len(get_connected_user_ids()),
        'total_connections': get_total_connections(),
        'cache_stats': {
            'universe_cache_size': len(universe_cache),
            'filter_cache_size': len(filter_cache),
            'hit_rate': calculate_cache_hit_rate()
        },
        'personalization': {
            'unique_universe_configs': count_unique_configs(),
            'avg_filters_per_user': calculate_avg_filters()
        }
    }
Security Monitoring
python# Track authentication events
logger.info(f"User {username} authenticated from {ip_address}")
logger.warning(f"Failed login attempt for {email}")
logger.error(f"Unauthorized WebSocket connection attempt")
Configuration
Session Management
python# Flask-Login configuration
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

# Redis session storage
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.from_url(REDIS_URL)
Rate Limiting
python# Per-user rate limits
RATELIMIT_STORAGE_URL = REDIS_URL
RATELIMIT_DEFAULT = "100 per minute"
RATELIMIT_HEADERS_ENABLED = True
Best Practices
Authentication

Always validate session on WebSocket connect
Use CSRF tokens for state-changing operations
Implement proper session timeout
Log all authentication events

Data Isolation

Never expose user IDs in frontend
Validate ownership on all operations
Use database constraints for safety
Implement row-level security

Performance

Cache user preferences aggressively
Batch database operations
Use connection pooling
Monitor cache effectiveness

Security Checklist

 WebSocket connections require authentication
 API endpoints use @login_required
 CSRF protection on all POST requests
 User data properly isolated
 Session cookies configured securely
 Rate limiting implemented
 Authentication events logged
 Regular security audits scheduled