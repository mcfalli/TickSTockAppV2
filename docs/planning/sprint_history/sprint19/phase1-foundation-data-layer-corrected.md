# Phase 1: Foundation & Data Layer - Corrected Implementation Guide

**Date**: 2025-09-04  
**Sprint**: 19 - Phase 1 Implementation  
**Duration**: 2-3 Weeks  
**Status**: Implementation Ready (Architecture Approved)  
**Prerequisites**: TickStockPL pattern detection operational, Redis infrastructure configured  

## Phase Overview
Establish the backend infrastructure for the Pattern Discovery Dashboard, focusing on a Redis-driven consumer architecture for TickStockApp. This phase ensures read-only access to pre-computed patterns from TickStockPL via Redis pub-sub, supports user data management, and delivers real-time WebSocket updates, achieving <50ms API responses and <100ms WebSocket latency.

## Success Criteria
✅ **Performance**: API endpoints <50ms for 1,000+ patterns  
✅ **Real-Time**: WebSocket updates <100ms, 100+ concurrent users  
✅ **Architecture**: Strict Consumer/Producer separation (TickStockApp consumes Redis events)  
✅ **Caching**: Redis reduces DB load by 70%+  
✅ **Testing**: 95%+ coverage for APIs and WebSocket handlers  

## Corrected Architecture Approach
- **Redis Consumer**: TickStockApp consumes patterns from Redis channels (`tickstock.events.patterns.daily`, `intraday`, `combo`) published by TickStockPL, avoiding direct DB pattern queries.
- **Database Role**: Read-only access for user data (watchlists, filters) and symbols; schema tasks (indexes, views) moved to TickStockPL.
- **WebSocket**: Event-driven via Redis Streams, preserving pull model for zero-event-loss.

## Implementation Tasks

### Week 1: Redis Consumer APIs & Database Setup
#### Task 1.1: Read-Only Database Connections
- Configure SQLAlchemy for read-only pooling (user data, symbols).
- Create tables: `user_watchlists`, `user_filters`, `symbols`.
```python
# src/db/setup.py
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine('postgresql://user:pass@localhost/tickstock', pool_size=20, max_overflow=10)
session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Session = scoped_session(session_factory)
```
- Query symbols for UI dropdowns (`SELECT symbol, name FROM symbols`).

#### Task 1.2: Redis Consumer API
- Implement `/api/patterns/scan` to query Redis sorted sets.
```python
# src/api/pattern_scanner.py
from flask import Blueprint, jsonify
import redis
import json

scanner_bp = Blueprint('scanner', __name__)
redis_client = redis.Redis.from_url('redis://localhost:6379')

@scanner_bp.route('/api/patterns/scan', methods=['GET'])
def scan_patterns():
    # Fetch patterns from Redis sorted set (sorted by confidence)
    patterns = []
    for pattern_json in redis_client.zrange('tickstock:patterns:unified', 0, 999, desc=True):
        patterns.append(json.loads(pattern_json))
    return jsonify({'patterns': patterns, 'total': len(patterns)})
```
- Cache patterns for 1 hour, APIs for 30s.

#### Task 1.3: User Universe Management
- Endpoint: `/api/users/universe` for watchlist/filter CRUD.
```python
# src/api/users.py
users_bp = Blueprint('users', __name__)

@users_bp.route('/api/users/universe', methods=['GET'])
def get_user_universe():
    user_id = request.headers.get('X-User-ID')
    watchlists = Session.execute(text("SELECT * FROM user_watchlists WHERE user_id = :user_id"), {'user_id': user_id}).fetchall()
    return jsonify([dict(w) for w in watchlists])
```

### Week 2: Event-Driven WebSocket System
#### Task 2.1: Flask-SocketIO Integration
- Subscribe to Redis channels for real-time pattern updates.
```python
# src/api/websockets.py
from flask_socketio import SocketIO
from app import app, redis_client

socketio = SocketIO(app, message_queue='redis://localhost:6379')

@socketio.on('subscribe_patterns')
def handle_subscribe(data):
    pubsub = redis_client.pubsub()
    pubsub.subscribe('tickstock.events.patterns.daily', 'tickstock.events.patterns.intraday', 'tickstock.events.patterns.combo')
    for message in pubsub.listen():
        if message['type'] == 'message':
            socketio.emit('pattern_update', json.loads(message['data']))
```
- Use Redis Streams for offline queuing.

#### Task 2.2: Pull Model Preservation
- Maintain `WebSocketPublisher` for zero-event-loss delivery.
```python
# src/events/websocket_publisher.py
class WebSocketPublisher:
    def publish(self, event: dict):
        socketio.emit('pattern_update', event, broadcast=True)
```

### Week 3: Performance & Caching Optimization
#### Task 3.1: Redis Caching Strategy
- Use sorted sets for pattern indexing (`ZADD tickstock:patterns:unified {score: confidence} {pattern_json}`).
- Set TTL: 30s for API responses, 1h for patterns.
```python
# src/cache/redis_cache.py
def cache_patterns(patterns: list):
    for p in patterns:
        redis_client.zadd('tickstock:patterns:unified', {json.dumps(p): p['confidence']})
        redis_client.expire('tickstock:patterns:unified', 3600)
```

#### Task 3.2: Performance Monitoring
- Track API/WebSocket latency in Redis (`api_performance`).
```python
# src/api/pattern_scanner.py
@scanner_bp.before_request
def before_request():
    request.start_time = time.time()

@scanner_bp.after_request
def after_request(response):
    duration = time.time() - request.start_time
    redis_client.lpush('api_performance', json.dumps({'endpoint': request.endpoint, 'duration': duration}))
    return response
```

## Testing Plan
- **Unit Tests**: Cover Redis consumer APIs, WebSocket handlers (`tests/unit/sprint19/test_redis_consumer.py`).
- **Integration Tests**: Validate Redis-to-WebSocket pipeline (`tests/integration/sprint19/test_event_flow.py`).
- **Performance Tests**: Benchmark <50ms APIs, <100ms WebSocket with pytest-benchmark.
- **Backtesting**: Validate Redis patterns against Massive historical data (<5% error per FMV).

## Deployment Checklist
- [ ] Read-only DB connections configured  
- [ ] Redis consumer APIs operational  
- [ ] WebSocket system broadcasting events  
- [ ] Caching achieving 70%+ DB load reduction  
- [ ] Performance monitoring logging metrics  
- [ ] 95%+ test coverage achieved  

## Next Phase Handoff
**Phase 2 Prerequisites**:
- Redis-driven APIs responding <50ms  
- WebSocket updates <100ms  
- User data tables populated  

This corrected phase ensures TickStockApp consumes patterns efficiently, paving the way for a high-performance UI!