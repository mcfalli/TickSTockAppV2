"""Simplified WebSocket publisher for TickStockPL integration.

PHASE 7 CLEANUP: Simplified to basic WebSocket emission with:
- Redis subscription for TickStockPL events
- Simple user filtering
- Direct SocketIO emission
- Basic user management

Removed: Complex filtering, analytics, caching, multi-frequency management.
"""

import json
import time
import threading
import redis
from typing import Dict, List, Any, Optional
from flask_socketio import emit
from src.core.domain.market.tick import TickData
import logging

logger = logging.getLogger(__name__)

class WebSocketPublisher:
    """Simplified WebSocket publisher with Redis subscription."""
    
    def __init__(self, config, socketio, market_service=None):
        self.config = config
        self.socketio = socketio
        self.market_service = market_service
        
        # Redis subscription for TickStockPL integration
        self.redis_client = None
        self.redis_subscriber = None
        self.subscription_thread = None
        self._init_redis()
        
        # User management
        self.connected_users = {}
        self.user_subscriptions = {}
        
        # Basic statistics
        self.events_emitted = 0
        self.users_reached = 0
        self.last_stats_log = time.time()
        
        logger.info("WEBSOCKET-PUBLISHER: Simplified publisher initialized")
    
    def _init_redis(self):
        """Initialize Redis connection and subscription."""
        # Check if Redis is configured
        redis_url = self.config.get('REDIS_URL')
        if not redis_url or redis_url.strip() == '':
            logger.info("WEBSOCKET-PUBLISHER: No Redis URL configured, skipping Redis initialization")
            self.redis_client = None
            return
            
        redis_host = self.config.get('REDIS_HOST', 'localhost')
        redis_port = self.config.get('REDIS_PORT', 6379)
        redis_db = self.config.get('REDIS_DB', 0)
        
        logger.info(f"WEBSOCKET-PUBLISHER: Attempting to connect to Redis at {redis_host}:{redis_port}")
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2
            )
            
            # Test connection
            self.redis_client.ping()
            
            # Create subscriber for TickStockPL events
            self.redis_subscriber = self.redis_client.pubsub()
            
            # Subscribe to TickStockPL channels
            self.redis_subscriber.subscribe('tickstock.all_ticks')
            
            # Start subscription thread
            self.subscription_thread = threading.Thread(
                target=self._redis_subscription_loop,
                daemon=True
            )
            self.subscription_thread.start()
            
            logger.info(f"WEBSOCKET-PUBLISHER: Redis subscriber initialized successfully")
            
        except Exception as e:
            logger.warning(f"WEBSOCKET-PUBLISHER: Redis connection failed: {e}")
            self.redis_client = None
    
    def _redis_subscription_loop(self):
        """Listen for TickStockPL events via Redis."""
        try:
            for message in self.redis_subscriber.listen():
                if message['type'] == 'message':
                    try:
                        tick_data = json.loads(message['data'])
                        self._handle_tickstock_event(tick_data)
                    except Exception as e:
                        logger.error(f"WEBSOCKET-PUBLISHER: Error processing Redis message: {e}")
        except Exception as e:
            logger.error(f"WEBSOCKET-PUBLISHER: Redis subscription error: {e}")
    
    def _handle_tickstock_event(self, tick_data: Dict[str, Any]):
        """Handle events from TickStockPL via Redis."""
        try:
            # Convert to TickData object
            ticker = tick_data.get('ticker')
            if not ticker:
                return
            
            # Simple filtering - emit to users interested in this ticker
            users_to_notify = self._get_users_for_ticker(ticker)
            
            if users_to_notify:
                # Create display data
                display_data = {
                    'ticker': ticker,
                    'price': tick_data.get('price'),
                    'volume': tick_data.get('volume'),
                    'timestamp': tick_data.get('timestamp'),
                    'source': 'tickstock_pl',
                    'event_type': 'tick_update'
                }
                
                # Emit to interested users
                for user_id in users_to_notify:
                    self._emit_to_user(user_id, 'tick_data', display_data)
                
                self.events_emitted += 1
                self.users_reached += len(users_to_notify)
                
                # Log stats periodically
                self._log_stats_if_needed()
                
        except Exception as e:
            logger.error(f"WEBSOCKET-PUBLISHER: Error handling TickStock event: {e}")
    
    def emit_tick_data(self, tick_data: TickData):
        """Direct emission of tick data to WebSocket clients."""
        try:
            # Simple filtering - get users interested in this ticker
            users_to_notify = self._get_users_for_ticker(tick_data.ticker)
            
            if users_to_notify:
                # Create simple display data
                display_data = {
                    'ticker': tick_data.ticker,
                    'price': tick_data.price,
                    'volume': tick_data.volume,
                    'timestamp': tick_data.timestamp,
                    'source': tick_data.source,
                    'event_type': 'tick_update',
                    'market_status': tick_data.market_status
                }
                
                # Emit to all interested users
                for user_id in users_to_notify:
                    self._emit_to_user(user_id, 'tick_data', display_data)
                
                self.events_emitted += 1
                self.users_reached += len(users_to_notify)
                
        except Exception as e:
            logger.error(f"WEBSOCKET-PUBLISHER: Error emitting tick data: {e}")
    
    def _get_users_for_ticker(self, ticker: str) -> List[str]:
        """Get users interested in a specific ticker."""
        interested_users = []
        
        for user_id, subscriptions in self.user_subscriptions.items():
            if ticker in subscriptions.get('tickers', []):
                interested_users.append(user_id)
        
        return interested_users
    
    def _emit_to_user(self, user_id: str, event: str, data: Dict[str, Any]):
        """Emit data to a specific user."""
        try:
            self.socketio.emit(event, data, room=user_id)
            logger.debug(f"WEBSOCKET-PUBLISHER: Emitted {event} to user {user_id}")
        except Exception as e:
            logger.error(f"WEBSOCKET-PUBLISHER: Error emitting to user {user_id}: {e}")
    
    def add_user(self, user_id: str, session_id: str):
        """Add a connected user."""
        self.connected_users[user_id] = {
            'session_id': session_id,
            'connected_at': time.time()
        }
        
        # Initialize empty subscriptions
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = {
                'tickers': [],
                'updated_at': time.time()
            }
        
        logger.info(f"WEBSOCKET-PUBLISHER: User {user_id} connected")
    
    def remove_user(self, user_id: str):
        """Remove a disconnected user."""
        if user_id in self.connected_users:
            del self.connected_users[user_id]
        
        if user_id in self.user_subscriptions:
            del self.user_subscriptions[user_id]
        
        logger.info(f"WEBSOCKET-PUBLISHER: User {user_id} disconnected")
    
    def update_user_subscriptions(self, user_id: str, tickers: List[str]):
        """Update user's ticker subscriptions."""
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = {}
        
        self.user_subscriptions[user_id].update({
            'tickers': tickers,
            'updated_at': time.time()
        })
        
        logger.info(f"WEBSOCKET-PUBLISHER: Updated subscriptions for user {user_id}: {len(tickers)} tickers")
    
    def _log_stats_if_needed(self):
        """Log statistics periodically."""
        if time.time() - self.last_stats_log > 30:  # Every 30 seconds
            logger.info(
                f"WEBSOCKET-PUBLISHER: Emitted {self.events_emitted} events to "
                f"{self.users_reached} user notifications, "
                f"Connected users: {len(self.connected_users)}"
            )
            self.last_stats_log = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics."""
        return {
            'connected_users': len(self.connected_users),
            'events_emitted': self.events_emitted,
            'users_reached': self.users_reached,
            'redis_connected': self.redis_client is not None,
            'total_subscriptions': sum(
                len(sub.get('tickers', [])) 
                for sub in self.user_subscriptions.values()
            )
        }
    
    def broadcast_message(self, event: str, data: Dict[str, Any]):
        """Broadcast a message to all connected users."""
        try:
            self.socketio.emit(event, data, broadcast=True)
            logger.info(f"WEBSOCKET-PUBLISHER: Broadcasted {event} to all users")
        except Exception as e:
            logger.error(f"WEBSOCKET-PUBLISHER: Error broadcasting: {e}")