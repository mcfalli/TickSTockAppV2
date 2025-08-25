"""Simplified WebSocket manager for TickStockPL integration.

PHASE 7 CLEANUP: Simplified to basic connection management with:
- Simple client registration and tracking
- Basic user connection mapping
- Essential SocketIO integration
- No complex event handling or analytics

Removed: Complex tracing, detailed analytics, elaborate connection management.
"""

import time
from typing import Dict, Set
from flask_socketio import SocketIO
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Simplified WebSocket connection manager."""
    
    def __init__(self, socketio: SocketIO, config: Dict):
        self.socketio = socketio
        self.config = config
        
        # Connection tracking
        self.clients = set()
        self.user_connections = {}  # user_id -> [connection_ids]
        self.connection_users = {}  # connection_id -> user_id
        
        logger.info("WEBSOCKET-MANAGER: Simplified manager initialized")
    
    def register_client(self, client_id: str):
        """Register a generic client connection."""
        self.clients.add(client_id)
        logger.info(f"WEBSOCKET-MANAGER: Client {client_id} registered")
    
    def unregister_client(self, client_id: str):
        """Unregister a client connection."""
        self.clients.discard(client_id)
        
        # Clean up user mappings
        if client_id in self.connection_users:
            user_id = self.connection_users[client_id]
            del self.connection_users[client_id]
            
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(client_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
        
        logger.info(f"WEBSOCKET-MANAGER: Client {client_id} unregistered")
    
    def register_user(self, user_id: str, client_id: str):
        """Register a user with specific client connection."""
        # Add to client set
        self.clients.add(client_id)
        
        # Map user to connection
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(client_id)
        
        # Map connection to user
        self.connection_users[client_id] = user_id
        
        logger.info(f"WEBSOCKET-MANAGER: User {user_id} registered with client {client_id}")
    
    def unregister_user(self, user_id: str, client_id: str = None):
        """Unregister a user and optionally specific client."""
        if client_id:
            # Remove specific connection
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(client_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            if client_id in self.connection_users:
                del self.connection_users[client_id]
            
            self.clients.discard(client_id)
            
            logger.info(f"WEBSOCKET-MANAGER: User {user_id} unregistered from client {client_id}")
        else:
            # Remove all connections for user
            if user_id in self.user_connections:
                for conn_id in self.user_connections[user_id]:
                    self.clients.discard(conn_id)
                    if conn_id in self.connection_users:
                        del self.connection_users[conn_id]
                del self.user_connections[user_id]
            
            logger.info(f"WEBSOCKET-MANAGER: User {user_id} completely unregistered")
    
    def get_user_connections(self, user_id: str) -> Set[str]:
        """Get all connection IDs for a user."""
        return self.user_connections.get(user_id, set()).copy()
    
    def get_connection_user(self, client_id: str) -> str:
        """Get user ID for a connection."""
        return self.connection_users.get(client_id)
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user has any active connections."""
        return user_id in self.user_connections and bool(self.user_connections[user_id])
    
    def get_connected_users(self) -> Set[str]:
        """Get all connected user IDs."""
        return set(self.user_connections.keys())
    
    def get_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            'total_clients': len(self.clients),
            'connected_users': len(self.user_connections),
            'total_user_connections': sum(len(conns) for conns in self.user_connections.values())
        }