"""
WebSocket Broadcasting Service
Enhanced Flask-SocketIO integration for real-time TickStockPL event broadcasting.

Sprint 10 Phase 2: Flask-SocketIO WebSocket Broadcasting
- Real-time event broadcasting to browser clients
- User subscription management for targeted events
- Connection management and heartbeat monitoring
- Message queuing for offline users (Redis Streams)
"""

import logging
import time
import json
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass
from flask_socketio import SocketIO, emit, disconnect
from flask_login import current_user
from flask import request
import redis

logger = logging.getLogger(__name__)

@dataclass
class ConnectedUser:
    """Represents a connected WebSocket user."""
    user_id: str
    session_id: str
    connected_at: float
    last_seen: float
    subscriptions: Set[str]  # Pattern subscriptions
    
    def update_last_seen(self):
        """Update last seen timestamp."""
        self.last_seen = time.time()

class WebSocketBroadcaster:
    """
    Enhanced WebSocket broadcasting service for TickStockPL integration.
    
    Manages real-time event broadcasting to browser clients with user-specific
    subscriptions and connection resilience. Integrates with existing Flask-SocketIO.
    """
    
    def __init__(self, socketio: SocketIO, redis_client: Optional[redis.Redis] = None):
        """Initialize WebSocket broadcaster."""
        self.socketio = socketio
        self.redis_client = redis_client
        
        # Connection tracking
        self.connected_users: Dict[str, ConnectedUser] = {}  # session_id -> ConnectedUser
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_ids
        
        # Message queuing for offline users
        self.offline_message_queue: Dict[str, List[Dict[str, Any]]] = {}  # user_id -> messages
        self.max_offline_messages = 100
        
        # Statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_queued': 0,
            'disconnections': 0,
            'start_time': time.time()
        }
        
        # Register SocketIO event handlers
        self._register_socketio_handlers()
        
        logger.info("WEBSOCKET-BROADCASTER: Service initialized")
    
    def _register_socketio_handlers(self):
        """Register enhanced SocketIO event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect(auth=None):
            """Handle client connection with user authentication."""
            try:
                # Get user information
                user_id = 'anonymous'
                if current_user and hasattr(current_user, 'id'):
                    user_id = str(current_user.id)
                
                session_id = request.sid
                
                # Create connected user record
                connected_user = ConnectedUser(
                    user_id=user_id,
                    session_id=session_id,
                    connected_at=time.time(),
                    last_seen=time.time(),
                    subscriptions=set()
                )
                
                # Track connection
                self.connected_users[session_id] = connected_user
                
                if user_id not in self.user_sessions:
                    self.user_sessions[user_id] = set()
                self.user_sessions[user_id].add(session_id)
                
                # Update stats
                self.stats['total_connections'] += 1
                self.stats['active_connections'] = len(self.connected_users)
                
                logger.info(f"WEBSOCKET-BROADCASTER: User {user_id} connected (session: {session_id})")
                
                # Send connection confirmation
                emit('connection_confirmed', {
                    'user_id': user_id,
                    'session_id': session_id,
                    'server_time': time.time(),
                    'status': 'connected'
                })
                
                # Deliver queued messages for authenticated users
                if user_id != 'anonymous':
                    self._deliver_queued_messages(user_id, session_id)
                
            except Exception as e:
                logger.error(f"WEBSOCKET-BROADCASTER: Connection error: {e}")
                disconnect()
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            try:
                session_id = request.sid
                
                if session_id in self.connected_users:
                    connected_user = self.connected_users[session_id]
                    user_id = connected_user.user_id
                    
                    # Remove from tracking
                    del self.connected_users[session_id]
                    
                    if user_id in self.user_sessions:
                        self.user_sessions[user_id].discard(session_id)
                        if not self.user_sessions[user_id]:
                            del self.user_sessions[user_id]
                    
                    # Update stats
                    self.stats['disconnections'] += 1
                    self.stats['active_connections'] = len(self.connected_users)
                    
                    logger.info(f"WEBSOCKET-BROADCASTER: User {user_id} disconnected (session: {session_id})")
                
            except Exception as e:
                logger.error(f"WEBSOCKET-BROADCASTER: Disconnection error: {e}")
        
        @self.socketio.on('subscribe_patterns')
        def handle_pattern_subscription(data):
            """Handle pattern subscription requests from clients."""
            try:
                session_id = request.sid
                
                if session_id not in self.connected_users:
                    emit('error', {'message': 'Session not found'})
                    return
                
                connected_user = self.connected_users[session_id]
                patterns = data.get('patterns', [])
                
                if not isinstance(patterns, list):
                    emit('error', {'message': 'Invalid patterns format'})
                    return
                
                # Update subscriptions
                connected_user.subscriptions = set(patterns)
                connected_user.update_last_seen()
                
                logger.info(f"WEBSOCKET-BROADCASTER: User {connected_user.user_id} subscribed to {len(patterns)} patterns")
                
                # Confirm subscription
                emit('subscription_confirmed', {
                    'patterns': patterns,
                    'count': len(patterns),
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"WEBSOCKET-BROADCASTER: Pattern subscription error: {e}")
                emit('error', {'message': 'Subscription failed'})
        
        @self.socketio.on('heartbeat')
        def handle_heartbeat():
            """Handle client heartbeat for connection monitoring."""
            try:
                session_id = request.sid
                
                if session_id in self.connected_users:
                    self.connected_users[session_id].update_last_seen()
                    emit('heartbeat_ack', {'timestamp': time.time()})
                
            except Exception as e:
                logger.error(f"WEBSOCKET-BROADCASTER: Heartbeat error: {e}")
    
    def broadcast_pattern_alert(self, pattern_event: Dict[str, Any]):
        """Broadcast pattern alert to subscribed users."""
        try:
            pattern_name = pattern_event.get('data', {}).get('pattern')
            symbol = pattern_event.get('data', {}).get('symbol')
            
            if not pattern_name:
                logger.warning("WEBSOCKET-BROADCASTER: Pattern event missing pattern name")
                return
            
            # Find users subscribed to this pattern
            target_sessions = []
            
            for session_id, connected_user in self.connected_users.items():
                # Check if user is subscribed to this pattern or all patterns
                if not connected_user.subscriptions or pattern_name in connected_user.subscriptions:
                    target_sessions.append(session_id)
            
            if not target_sessions:
                logger.debug(f"WEBSOCKET-BROADCASTER: No users subscribed to pattern {pattern_name}")
                return
            
            # Prepare WebSocket message
            websocket_message = {
                'type': 'pattern_alert',
                'pattern': pattern_name,
                'symbol': symbol,
                'event_data': pattern_event,
                'timestamp': time.time()
            }
            
            # Broadcast to target sessions
            for session_id in target_sessions:
                try:
                    self.socketio.emit('pattern_alert', websocket_message, room=session_id)
                    self.stats['messages_sent'] += 1
                except Exception as e:
                    logger.error(f"WEBSOCKET-BROADCASTER: Failed to send to session {session_id}: {e}")
            
            logger.info(f"WEBSOCKET-BROADCASTER: Pattern alert sent to {len(target_sessions)} users - {pattern_name} on {symbol}")
            
        except Exception as e:
            logger.error(f"WEBSOCKET-BROADCASTER: Pattern alert broadcast error: {e}")
    
    def broadcast_backtest_progress(self, progress_event: Dict[str, Any]):
        """Broadcast backtest progress to all connected users."""
        try:
            job_id = progress_event.get('data', {}).get('job_id')
            progress = progress_event.get('data', {}).get('progress', 0)
            
            websocket_message = {
                'type': 'backtest_progress',
                'job_id': job_id,
                'progress': progress,
                'event_data': progress_event,
                'timestamp': time.time()
            }
            
            # Broadcast to all connected users
            self.socketio.emit('backtest_progress', websocket_message, broadcast=True)
            self.stats['messages_sent'] += len(self.connected_users)
            
            logger.debug(f"WEBSOCKET-BROADCASTER: Backtest progress broadcasted - Job {job_id}: {progress:.1%}")
            
        except Exception as e:
            logger.error(f"WEBSOCKET-BROADCASTER: Backtest progress broadcast error: {e}")
    
    def broadcast_backtest_result(self, result_event: Dict[str, Any]):
        """Broadcast backtest results to all connected users."""
        try:
            job_id = result_event.get('data', {}).get('job_id')
            status = result_event.get('data', {}).get('status')
            
            websocket_message = {
                'type': 'backtest_result',
                'job_id': job_id,
                'status': status,
                'event_data': result_event,
                'timestamp': time.time()
            }
            
            # Broadcast to all connected users
            self.socketio.emit('backtest_result', websocket_message, broadcast=True)
            self.stats['messages_sent'] += len(self.connected_users)
            
            logger.info(f"WEBSOCKET-BROADCASTER: Backtest result broadcasted - Job {job_id}: {status}")
            
        except Exception as e:
            logger.error(f"WEBSOCKET-BROADCASTER: Backtest result broadcast error: {e}")
    
    def broadcast_system_health(self, health_event: Dict[str, Any]):
        """Broadcast system health updates to all connected users."""
        try:
            websocket_message = {
                'type': 'system_health',
                'health_data': health_event.get('data', {}),
                'timestamp': time.time()
            }
            
            # Broadcast to all connected users
            self.socketio.emit('system_health', websocket_message, broadcast=True)
            self.stats['messages_sent'] += len(self.connected_users)
            
            logger.debug("WEBSOCKET-BROADCASTER: System health update broadcasted")
            
        except Exception as e:
            logger.error(f"WEBSOCKET-BROADCASTER: System health broadcast error: {e}")
    
    def _deliver_queued_messages(self, user_id: str, session_id: str):
        """Deliver queued messages to newly connected user."""
        try:
            if user_id not in self.offline_message_queue:
                return
            
            queued_messages = self.offline_message_queue[user_id]
            if not queued_messages:
                return
            
            logger.info(f"WEBSOCKET-BROADCASTER: Delivering {len(queued_messages)} queued messages to user {user_id}")
            
            # Send queued messages
            for message in queued_messages:
                try:
                    self.socketio.emit('queued_message', message, room=session_id)
                    self.stats['messages_sent'] += 1
                except Exception as e:
                    logger.error(f"WEBSOCKET-BROADCASTER: Failed to deliver queued message: {e}")
            
            # Clear queue
            del self.offline_message_queue[user_id]
            
        except Exception as e:
            logger.error(f"WEBSOCKET-BROADCASTER: Error delivering queued messages: {e}")
    
    def queue_message_for_offline_user(self, user_id: str, message: Dict[str, Any]):
        """Queue message for offline user."""
        try:
            if user_id == 'anonymous':
                return  # Don't queue for anonymous users
            
            if user_id not in self.offline_message_queue:
                self.offline_message_queue[user_id] = []
            
            # Add message with timestamp
            queued_message = {
                **message,
                'queued_at': time.time(),
                'queued': True
            }
            
            self.offline_message_queue[user_id].append(queued_message)
            
            # Limit queue size
            if len(self.offline_message_queue[user_id]) > self.max_offline_messages:
                self.offline_message_queue[user_id] = self.offline_message_queue[user_id][-self.max_offline_messages:]
            
            self.stats['messages_queued'] += 1
            
            logger.debug(f"WEBSOCKET-BROADCASTER: Message queued for offline user {user_id}")
            
        except Exception as e:
            logger.error(f"WEBSOCKET-BROADCASTER: Error queueing message: {e}")
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user is currently online."""
        return user_id in self.user_sessions and len(self.user_sessions[user_id]) > 0
    
    def get_connected_users(self) -> List[Dict[str, Any]]:
        """Get list of currently connected users."""
        users = []
        
        for connected_user in self.connected_users.values():
            users.append({
                'user_id': connected_user.user_id,
                'session_id': connected_user.session_id,
                'connected_at': connected_user.connected_at,
                'last_seen': connected_user.last_seen,
                'subscriptions': list(connected_user.subscriptions),
                'connection_duration': time.time() - connected_user.connected_at
            })
        
        return users
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broadcaster statistics."""
        runtime = time.time() - self.stats['start_time']
        
        return {
            **self.stats,
            'runtime_seconds': round(runtime, 1),
            'messages_per_second': round(self.stats['messages_sent'] / max(runtime, 1), 2),
            'unique_users': len(self.user_sessions),
            'offline_queues': len(self.offline_message_queue),
            'total_queued_messages': sum(len(queue) for queue in self.offline_message_queue.values())
        }
    
    def cleanup_stale_connections(self, max_idle_seconds: int = 300):
        """Clean up stale connections that haven't sent heartbeat."""
        try:
            current_time = time.time()
            stale_sessions = []
            
            for session_id, connected_user in self.connected_users.items():
                if current_time - connected_user.last_seen > max_idle_seconds:
                    stale_sessions.append(session_id)
            
            for session_id in stale_sessions:
                logger.info(f"WEBSOCKET-BROADCASTER: Cleaning up stale connection: {session_id}")
                # Force disconnect will trigger handle_disconnect
                self.socketio.disconnect(session_id)
            
            return len(stale_sessions)
            
        except Exception as e:
            logger.error(f"WEBSOCKET-BROADCASTER: Error cleaning up stale connections: {e}")
            return 0