import threading
from typing import Dict, Any, Set, List
from flask import config
from flask_socketio import SocketIO
import time
import json
from datetime import datetime
from config.logging_config import get_domain_logger, LogDomain

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = get_domain_logger(LogDomain.CORE, 'websocket_manager')

class WebSocketManager:
    def __init__(self, socketio, config):
        init_start_time = time.time()
        
        self.socketio = socketio
        self.config = config
        self.clients = set()
        
        # user connection tracking
        self.user_connections = {}  # user_id -> [connection_ids]
        self.connection_users = {}  # connection_id -> user_id

        logger.info("WebSocket manager initialized with user connection tracking")
        
        # TRACE: Initialization complete
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='WebSocketManager',
                action='initialization_complete',
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(0),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - init_start_time) * 1000,
                    'details': {
                        'has_socketio': socketio is not None,
                        'user_tracking_enabled': True
                    }
                }
            )

    def register_client(self, client_id):
        """Register a generic client connection"""
        start_time = time.time()
        
        self.clients.add(client_id)
        logger.debug(f"Client registered: {client_id}")
        
        # TRACE: Generic client registration (VERBOSE to avoid spam)
        if tracer.should_trace('SYSTEM', TraceLevel.VERBOSE):
            tracer.trace(
                ticker='SYSTEM',
                component="WebSocketManager",
                action="generic_client_registered",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(1),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        "client_id": client_id,
                        "total_generic_clients": len(self.clients)
                    }
                }
            )

    def unregister_client(self, client_id):
        """Unregister a generic client connection"""
        start_time = time.time()
        
        self.clients.discard(client_id)
        logger.debug(f"Client unregistered: {client_id}")
        
        # TRACE: Generic client unregistration (VERBOSE to avoid spam)
        if tracer.should_trace('SYSTEM', TraceLevel.VERBOSE):
            tracer.trace(
                ticker='SYSTEM',
                component="WebSocketManager",
                action="generic_client_unregistered",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(1),
                    'output_count': ensure_int(1),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        "client_id": client_id,
                        "total_generic_clients": len(self.clients)
                    }
                }
            )

    def register_user_connection(self, user_id: int, connection_id: str):
        """
        Register a user's WebSocket connection.
        
        Args:
            user_id: Authenticated user ID
            connection_id: WebSocket connection ID
        """
        start_time = time.time()
        
        try:
            # Initialize user connection list if needed
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            
            # Add connection to user's list
            self.user_connections[user_id].append(connection_id)
            
            # Map connection back to user
            self.connection_users[connection_id] = user_id
            
            # Get total connected users for trace
            total_users = len(self.user_connections)
            is_first_connection = len(self.user_connections[user_id]) == 1
            
            logger.debug(f"WEB-SOCKET: USER_CONNECTION_REGISTERED: User {user_id} -> Connection {connection_id}")
            logger.debug(f"WEB-SOCKET: User {user_id} now has {len(self.user_connections[user_id])} active connections")

            # TRACE for user connection
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="user_connected",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),  # One user connection
                        'output_count': ensure_int(1),  # Successfully registered
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            "user_id": user_id,
                            "connection_id": connection_id,
                            "user_connections": len(self.user_connections[user_id]),
                            "total_users": total_users,
                            "is_first_connection": is_first_connection
                        }
                    }
                )

        except Exception as e:
            logger.error(f"Error registering user connection: {e}")
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="user_connection_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "user_id": user_id,
                            "connection_id": connection_id,
                            "error_type": type(e).__name__
                        }
                    }
                )

    def unregister_user_connection(self, connection_id: str):
        """Remove user connection mapping."""
        start_time = time.time()
        
        try:
            if connection_id in self.connection_users:
                user_id = self.connection_users[connection_id]
                
                # Remove connection from user's list
                if user_id in self.user_connections:
                    if connection_id in self.user_connections[user_id]:
                        self.user_connections[user_id].remove(connection_id)
                    
                    # Track if user is disconnecting completely
                    user_disconnected = False
                    
                    # Clean up empty user entries
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
                        user_disconnected = True
                        logger.debug(f"Removed user {user_id} from user_connections (no active connections)")
                    
                    # Remove connection->user mapping
                    del self.connection_users[connection_id]
                    
                    logger.debug(f"WEB-SOCKET: USER_CONNECTION_UNREGISTERED: Connection {connection_id} for User {user_id}")
                    
                    # TRACE for user disconnection
                    if tracer.should_trace('SYSTEM'):
                        tracer.trace(
                            ticker='SYSTEM',
                            component="WebSocketManager",
                            action="user_disconnected",
                            data={
                                'timestamp': time.time(),
                                'input_count': ensure_int(1),  # One disconnection
                                'output_count': ensure_int(1),  # Successfully unregistered
                                'duration_ms': (time.time() - start_time) * 1000,
                                'details': {
                                    "user_id": user_id,
                                    "connection_id": connection_id,
                                    "remaining_connections": len(self.user_connections.get(user_id, [])),
                                    "user_fully_disconnected": user_disconnected,
                                    "total_users": len(self.user_connections)
                                }
                            }
                        )
            else:
                logger.debug(f"WEB-SOCKET: Connection {connection_id} was not registered to any user")
                
        except Exception as e:
            logger.error(f"Error unregistering user connection: {e}")
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="user_disconnection_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "connection_id": connection_id,
                            "error_type": type(e).__name__
                        }
                    }
                )

    def emit_to_user(self, data: dict, user_id: int, event_name: str = 'stock_data'):
        """
        Emit data to all connections for a specific user.
        
        Args:
            data: Data to emit
            user_id: Target user ID
            event_name: WebSocket event name
        """
        try:
            emit_start_time = time.time()
            if user_id in self.user_connections:
                connections = self.user_connections[user_id]
                
                # Serialize data once for efficiency
                payload = json.dumps(data, default=str)
                payload_size = len(payload.encode('utf-8'))
                
                # Extract event summary for metrics
                event_summary = self._extract_event_summary(data)
                emitted_tickers = event_summary.pop('emitted_tickers', set())
                
                # Emit to all user's connections
                successful_emissions = 0
                failed_emissions = []
                
                for connection_id in connections:
                    try:
                        connection_emit_start = time.time()
                        
                        # DEBUG: Log WebSocket emissions to trace data flow
                        # 777777777777777777777777777777777777777777777777777777777777777777777
                        logger.info("7" * 80)
                        logger.info(f"🔍 EMIT-DEBUG: Emitting {payload_size} bytes to user {user_id} connection {connection_id}")
                        logger.info("7" * 80)
                        if successful_emissions == 0:  # Log first emission content
                            logger.info(f"🔍 EMIT-DEBUG: Event: {event_name}, Content: {payload[:1000]}...")  # First 1000 chars
                            logger.info(f"🔍 EMIT-DEBUG: Full payload size: {payload_size} bytes")
                        self.socketio.emit(event_name, payload, room=connection_id)
                        successful_emissions += 1
                        
                    except Exception as emit_error:
                        logger.warning(f"Failed to emit to connection {connection_id}: {emit_error}")
                        failed_emissions.append({
                            'connection_id': connection_id,
                            'error': str(emit_error)
                        })
                
                # SINGLE QUALITY TRACE: User emission summary
                if tracer.should_trace('SYSTEM') and (successful_emissions > 0 or failed_emissions):
                    emission_status = 'complete' if successful_emissions == len(connections) else 'partial'
                    
                    tracer.trace(
                        ticker='SYSTEM',
                        component="WebSocketManager",
                        action="user_emission",
                        data={
                            'timestamp': time.time(),
                            'input_count': ensure_int(event_summary.get('total_events', 0)),
                            'output_count': ensure_int(successful_emissions),
                            'duration_ms': (time.time() - emit_start_time) * 1000,
                            'details': {
                                "user_id": user_id,
                                "event_name": event_name,
                                "status": emission_status,
                                "connections_total": len(connections),
                                "connections_success": successful_emissions,
                                "connections_failed": len(failed_emissions),
                                "payload_size_kb": round(payload_size / 1024, 2),
                                "event_breakdown": {
                                    'highs': event_summary.get('highs', 0),
                                    'lows': event_summary.get('lows', 0),
                                    'trends': event_summary.get('trends_total', 0),
                                    'surges': event_summary.get('surges_total', 0)
                                },
                                "ticker_count": len(emitted_tickers),
                                "failed_connections": failed_emissions if failed_emissions else None
                            }
                        }
                    )
                
                # Log summary (only if issues or significant size)
                if failed_emissions or payload_size > 50000:  # >50KB
                    logger.info(f"📤 WEB-SOCKET: User {user_id} emission: "
                            f"{successful_emissions}/{len(connections)} connections, "
                            f"{round(payload_size/1024, 1)}KB, "
                            f"{event_summary.get('total_events', 0)} events")
                
                return successful_emissions > 0
                
            else:
                logger.warning(f"WEB-SOCKET: User {user_id} has no active connections")
                return False
                
        except Exception as e:
            logger.error(f"WEB-SOCKET: Error emitting to user {user_id}: {e}")
            
            # TRACE: Error (always trace errors)
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="user_emit_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - emit_start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "user_id": user_id,
                            "event_name": event_name,
                            "error_type": type(e).__name__,
                            "has_connections": user_id in self.user_connections
                        }
                    }
                )
            
            return False

    def _extract_event_summary(self, data: dict) -> dict:
        """Extract event summary from payload data."""
        summary = {
            'highs': 0,
            'lows': 0,
            'trends_total': 0,
            'surges_total': 0,
            'total_events': 0,
            'emitted_tickers': set()
        }
        
        try:
            if isinstance(data, dict):
                # Count highs/lows
                highs = data.get('highs', [])
                lows = data.get('lows', [])
                summary['highs'] = len(highs)
                summary['lows'] = len(lows)
                
                # Count trending/surging
                trending = data.get('trending', {})
                surging = data.get('surging', {})
                summary['trends_total'] = len(trending.get('up', [])) + len(trending.get('down', []))
                summary['surges_total'] = len(surging.get('up', [])) + len(surging.get('down', []))
                
                # Total events
                summary['total_events'] = (summary['highs'] + summary['lows'] + 
                                        summary['trends_total'] + summary['surges_total'])
                
                # Extract unique tickers
                for event_list in [highs, lows]:
                    for event in event_list:
                        if isinstance(event, dict) and 'ticker' in event:
                            summary['emitted_tickers'].add(event['ticker'])
                
                for direction_events in [trending, surging]:
                    for direction in ['up', 'down']:
                        for event in direction_events.get(direction, []):
                            if isinstance(event, dict) and 'ticker' in event:
                                summary['emitted_tickers'].add(event['ticker'])
        
        except Exception as e:
            logger.debug(f"Error extracting event summary: {e}")
        
        return summary

    def get_connected_user_ids(self) -> List[int]:
        """
        Get list of all connected user IDs.
        
        Returns:
            list: List of user IDs with active connections
        """
        return list(self.user_connections.keys())

    def get_user_connection_count(self, user_id: int) -> int:
        """
        Get number of connections for a specific user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            int: Number of active connections for user
        """
        return len(self.user_connections.get(user_id, []))

    def get_total_user_connections(self) -> int:
        """Get total number of authenticated user connections"""
        total = sum(len(connections) for connections in self.user_connections.values())
        return total

    def get_connection_user_id(self, connection_id: str) -> int:
        """
        Get user ID for a connection.
        
        Args:
            connection_id: Connection ID to look up
            
        Returns:
            int or None: User ID if found, None otherwise
        """
        return self.connection_users.get(connection_id)

    '''
    def is_user_connected(self, user_id: int) -> bool:
        """
        Check if a user has any active connections.
        
        Args:
            user_id: User ID to check
            
        Returns:
            bool: True if user has active connections
        """
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0
    '''
    def emit_update(self, data, event_name='stock_update', room=None):
        """
        Legacy method for backward compatibility.
        Emits to all clients (authenticated and unauthenticated).
        """
        start_time = time.time()
        
        try:
            # Ensure data is JSON-serializable
            payload = json.dumps(data, default=str)
            payload_size = len(payload.encode('utf-8'))
            
            logger.debug(f"WEB-SOCKET: JSON: socketio.emit Payload: Emitting {event_name} to {room if room else 'all clients'}: {payload[:500]}...")
            
            if room:
                self.socketio.emit(event_name, payload, room=room)
            else:
                self.socketio.emit(event_name, payload)
            
            # TRACE: Broadcast complete (VERBOSE to avoid spam)
            if tracer.should_trace('SYSTEM', TraceLevel.VERBOSE):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="broadcast_complete",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(1),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            "event_name": event_name,
                            "room": room,
                            "payload_size": payload_size
                        }
                    }
                )
                
        except json.JSONEncodeError as e:
            logger.error(f"WEB-SOCKET: JSON serialization failed for {event_name}: {e}")
            self.emit_error(f"Server error: Invalid data format in {event_name}")
        except Exception as e:
            logger.error(f"WEB-SOCKET: Error emitting {event_name}: {e}", exc_info=True)
            self.emit_error(f"Server error in {event_name}: {str(e)}")
                
    '''
    def broadcast_market_status(self, status: str):
        """Broadcast market status to all authenticated users"""
        start_time = time.time()
        
        if not self.user_connections:
            logger.debug("WEB-SOCKET: No authenticated users to broadcast market status to")
            return
            
        try:
            status_data = {'status': status}
            authenticated_users = self.get_connected_user_ids()
            successful_broadcasts = 0
            
            for user_id in authenticated_users:
                if self.emit_to_user(status_data, user_id, 'market_status'):
                    successful_broadcasts += 1
            
            # TRACE: Market status broadcast
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="market_status_broadcast",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(len(authenticated_users)),
                        'output_count': ensure_int(successful_broadcasts),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            "status": status,
                            "users_targeted": len(authenticated_users),
                            "users_reached": successful_broadcasts,
                            "success_rate": (successful_broadcasts / len(authenticated_users) * 100) if authenticated_users else 0
                        }
                    }
                )
                
            logger.debug(f"WEB-SOCKET: Broadcasted market status: {status} to {successful_broadcasts}/{len(authenticated_users)} authenticated users")
        except Exception as e:
            logger.error(f"WEB-SOCKET: Error broadcasting market status: {e}")
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="market_status_broadcast_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(len(self.user_connections)),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "status": status,
                            "error_type": type(e).__name__
                        }
                    }
                )
    '''
    def emit_error(self, error_message: str, room: str = None):
        """Emit error message to specific room or all clients"""
        start_time = time.time()
        
        try:
            data = {"error": error_message, "timestamp": int(datetime.now().timestamp() * 1000)}
            if room:
                self.socketio.emit('error', data, room=room)
                logger.debug(f"WEB-SOCKET: Emitted error to room {room}: {error_message}")
            else:
                self.socketio.emit('error', data)
                logger.debug(f"WEB-SOCKET: Emitted error to all clients: {error_message}")
            
            # TRACE: Error emission (VERBOSE to avoid spam)
            if tracer.should_trace('SYSTEM', TraceLevel.VERBOSE):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="error_emitted",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(1),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            "error_message": error_message[:100],  # Truncate for tracing
                            "room": room
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"WEB-SOCKET: Error emitting error message: {e}")
    
    def get_client_count(self) -> int:
        """Get total number of connected clients (legacy + authenticated)"""
        return len(self.clients)
    
    def get_user_connection_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive connection statistics.
        
        Returns:
            dict: Connection statistics
        """
        start_time = time.time()
        
        try:
            total_users = len(self.user_connections)
            total_user_connections = self.get_total_user_connections()
            total_generic_clients = len(self.clients)
            
            # Calculate connections per user
            connections_per_user = {}
            if self.user_connections:
                for user_id, connections in self.user_connections.items():
                    connections_per_user[user_id] = len(connections)
            
            stats = {
                'total_authenticated_users': total_users,
                'total_user_connections': total_user_connections,
                'total_generic_clients': total_generic_clients,
                'connections_per_user': connections_per_user,
                'avg_connections_per_user': total_user_connections / total_users if total_users > 0 else 0
            }
            
            # TRACE: Stats retrieved
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="connection_stats_retrieved",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(total_users + total_generic_clients),
                        'output_count': ensure_int(1),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': stats
                    }
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"WEB-SOCKET: Error getting user connection stats: {e}")
            return {'error': str(e)}
    
    def emit_heartbeat(self, data):
        """Emit heartbeat to all clients (legacy compatibility)"""
        start_time = time.time()
        
        try:
            payload = json.dumps(data, default=str)
            payload_size = len(payload.encode('utf-8'))
            
            logger.debug(f"WEB-SOCKET: Emitting socketio status_update: {payload}")
            self.socketio.emit('status_update', payload)
            
            # TRACE: Heartbeat sent (VERBOSE to avoid spam)
            if tracer.should_trace('SYSTEM', TraceLevel.VERBOSE):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketManager",
                    action="heartbeat_sent",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(1),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            "payload_size": payload_size
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"WEB-SOCKET: Error emitting status_update: {e}", exc_info=True)
            self.emit_error(f"Server error in status_update: {str(e)}")

