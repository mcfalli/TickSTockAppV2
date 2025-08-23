import json
import threading
import sys
import time
from datetime import datetime
import traceback
from typing import Dict, List, Any, Callable, Optional, Literal
from enum import Enum
import pytz

# Now that the folder is renamed, we can use the normal import!
import websocket

from src.core.domain.market.tick import TickData
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from src.shared.types import FrequencyType
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'polygon_websocket_client')


class StreamConnection:
    """
    Represents a single WebSocket connection for a specific frequency type.
    Each frequency has its own isolated connection for better error handling.
    """
    def __init__(self, frequency_type: FrequencyType, url: str, api_key: str, 
                 on_message_callback: Callable, on_status_callback: Callable, config: dict):
        self.frequency_type = frequency_type
        self.url = url
        self.api_key = api_key
        self.on_message_callback = on_message_callback
        self.on_status_callback = on_status_callback
        self.config = config
        
        # Connection state
        self.ws = None
        self.connected = False
        self.should_reconnect = True
        self.auth_received = False
        self.subscribed_tickers = set()
        self.connection_thread = None
        
        # Timing and reconnection
        self.auth_sent_time = 0
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.get('POLYGON_WEBSOCKET_MAX_RETRIES', 5)
        self.base_reconnect_delay = config.get('POLYGON_WEBSOCKET_RECONNECT_DELAY', 5)
        self.max_reconnect_delay = config.get('POLYGON_WEBSOCKET_MAX_RECONNECT_DELAY', 60)
        
        # Thread safety
        self._connection_lock = threading.Lock()
        
        # Start heartbeat checker
        threading.Thread(target=self._heartbeat_checker, daemon=True).start()
    
    def get_event_types(self) -> List[str]:
        """Get the event types this connection should handle"""
        if self.frequency_type == FrequencyType.PER_SECOND:
            return ['A', 'T', 'Q']  # Aggregates, Trades, Quotes
        elif self.frequency_type == FrequencyType.PER_MINUTE:
            return ['AM']  # Per-minute aggregates
        elif self.frequency_type == FrequencyType.FAIR_MARKET_VALUE:
            return ['FMV']  # Fair market value
        return []
    
    def get_subscription_prefix(self) -> str:
        """Get the subscription prefix for this frequency type"""
        if self.frequency_type == FrequencyType.PER_SECOND:
            return 'A'  # Per-second aggregates
        elif self.frequency_type == FrequencyType.PER_MINUTE:
            return 'AM'  # Per-minute aggregates
        elif self.frequency_type == FrequencyType.FAIR_MARKET_VALUE:
            return 'FMV'  # Fair market value
        return 'A'  # Default fallback

    def _heartbeat_checker(self):
        """Monitor connection health and trigger reconnection if needed"""
        while self.should_reconnect:
            if self.connected and (time.time() - self.last_heartbeat) > self.heartbeat_interval:
                logger.warning(f"POLYGON-{self.frequency_type.value.upper()}: No messages received in {self.heartbeat_interval} seconds")
                try:
                    if self.ws and self.ws.sock:
                        self.ws.sock.ping()
                        self.last_heartbeat = time.time()
                    else:
                        raise Exception("No socket available")
                except:
                    logger.warning(f"POLYGON-{self.frequency_type.value.upper()}: Heartbeat failed, triggering reconnect")
                    self.connected = False
                    self._attempt_reconnect()
            time.sleep(5)
    
    def _attempt_reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        if not self.should_reconnect or self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"POLYGON-{self.frequency_type.value.upper()}: Max reconnect attempts ({self.max_reconnect_attempts}) reached, giving up")
            self.should_reconnect = False
            return
        
        self.reconnect_attempts += 1
        delay = min(self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)), self.max_reconnect_delay)
        logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Attempting to reconnect (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}) in {delay}s...")
        time.sleep(delay)
        
        with self._connection_lock:
            if self.connect():
                self.reconnect_attempts = 0
                logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Reconnection successful")
    
    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.debug(f"POLYGON-{self.frequency_type.value.upper()}: WebSocket connection opened - beginning authentication")
        
        # Send authentication message
        auth_msg = {"action": "auth", "params": self.api_key}
        try:
            ws.send(json.dumps(auth_msg))
            self.auth_sent_time = time.time()
            logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Authentication request sent")
        except Exception as e:
            logger.error(f"POLYGON-{self.frequency_type.value.upper()}: Failed to send authentication: {e}")
            self.on_status_callback(f'error_{self.frequency_type.value}', {'error': 'Authentication failed'})
            return
        
        # Wait for authentication success
        auth_timeout = 10
        auth_start = time.time()
        while time.time() - auth_start < auth_timeout:
            if self.auth_received:
                break
            time.sleep(0.5)
        
        if not self.auth_received:
            logger.warning(f"POLYGON-{self.frequency_type.value.upper()}: Authentication not confirmed within timeout, but continuing")
        
        logger.info(f"POLYGON-{self.frequency_type.value.upper()}: WebSocket opened and authenticated successfully")
        self.connected = True
        self.on_status_callback(f'connected_{self.frequency_type.value}', {'message': 'Authentication successful'})
        self.reconnect_attempts = 0
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            self.last_heartbeat = time.time()
            
            if isinstance(data, list):
                for msg in data:
                    self._process_message(msg)
            else:
                self._process_message(data)
        except Exception as e:
            logger.error(f"POLYGON-{self.frequency_type.value.upper()}: Error processing WebSocket message: {str(e)}")
    
    def _process_message(self, msg):
        """Process individual message from WebSocket"""
        if msg.get('ev') == 'status':
            if msg.get('status') == 'auth_success':
                self.auth_received = True
                logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Authentication confirmed")
                self.on_status_callback(f'connected_{self.frequency_type.value}', {'message': 'Authentication successful'})
            else:
                status = msg.get('status')
                message = msg.get('message')
                self.on_status_callback(f'status_update_{self.frequency_type.value}', {'status': status, 'message': message})
        elif msg.get('ev') in self.get_event_types():
            # Pass the message to the callback with frequency information
            self.on_message_callback(msg, self.frequency_type)
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"POLYGON-{self.frequency_type.value.upper()}: WebSocket error: {error}")
        self.connected = False
        self.on_status_callback(f'error_{self.frequency_type.value}', {'error': str(error)})
        self._attempt_reconnect()
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info(f"POLYGON-{self.frequency_type.value.upper()}: WebSocket connection closed: {close_status_code} - {close_msg}")
        self.connected = False
        self.on_status_callback(f'disconnected_{self.frequency_type.value}')
        self._attempt_reconnect()
    
    def connect(self) -> bool:
        """Establish WebSocket connection"""
        logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Initiating WebSocket connection to {self.url}")
        
        with self._connection_lock:
            if self.ws and self.ws.sock and self.ws.sock.connected and self.connected:
                logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Already connected, skipping reconnection")
                return True
            
            # Clean up existing connection
            if self.ws:
                try:
                    self.ws.close()
                except Exception as e:
                    logger.warning(f"POLYGON-{self.frequency_type.value.upper()}: Error closing existing connection: {e}")
                finally:
                    self.ws = None
                    self.connected = False
                    time.sleep(1)
            
            # Reset state
            self.auth_received = False
            self.last_heartbeat = time.time()
            
            # Create new WebSocketApp
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start connection thread
            self.connection_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={
                    'ping_interval': 30,
                    'ping_timeout': 10,
                    'skip_utf8_validation': True
                }
            )
            self.connection_thread.daemon = True
            self.connection_thread.start()
            
            # Wait for connection
            connection_timeout = 15
            start_time = time.time()
            
            while time.time() - start_time < connection_timeout:
                if self.connected:
                    logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Connection established successfully")
                    return True
                time.sleep(0.5)
            
            logger.warning(f"POLYGON-{self.frequency_type.value.upper()}: Connection timed out")
            return self.connected
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Disconnecting from WebSocket")
        self.should_reconnect = False
        
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        self.connected = False
        self.on_status_callback(f'disconnected_{self.frequency_type.value}')
    
    def subscribe(self, tickers: List[str]) -> bool:
        """Subscribe to tickers for this frequency type"""
        if not tickers:
            return True
        
        if not self.connected:
            logger.warning(f"POLYGON-{self.frequency_type.value.upper()}: Cannot subscribe - not connected")
            return False
        
        # Filter new tickers
        new_tickers = [ticker for ticker in tickers if ticker not in self.subscribed_tickers]
        if not new_tickers:
            return True
        
        # Format subscription message
        prefix = self.get_subscription_prefix()
        formatted_tickers = [f"{prefix}.{ticker}" for ticker in new_tickers]
        subscribe_message = {"action": "subscribe", "params": ",".join(formatted_tickers)}
        
        # Send subscription
        try:
            logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Subscribing to {len(new_tickers)} tickers")
            self.ws.send(json.dumps(subscribe_message))
            self.subscribed_tickers.update(new_tickers)
            return True
        except Exception as e:
            logger.error(f"POLYGON-{self.frequency_type.value.upper()}: Error subscribing: {e}")
            return False

    def unsubscribe(self, tickers: List[str]) -> bool:
        """Unsubscribe from tickers for this frequency type"""
        if not tickers:
            return True
        
        if not self.connected:
            logger.warning(f"POLYGON-{self.frequency_type.value.upper()}: Cannot unsubscribe - not connected")
            return False
        
        # Filter existing tickers
        existing_tickers = [ticker for ticker in tickers if ticker in self.subscribed_tickers]
        if not existing_tickers:
            return True
        
        # Format unsubscription message
        prefix = self.get_subscription_prefix()
        formatted_tickers = [f"{prefix}.{ticker}" for ticker in existing_tickers]
        unsubscribe_message = {"action": "unsubscribe", "params": ",".join(formatted_tickers)}
        
        # Send unsubscription
        try:
            logger.info(f"POLYGON-{self.frequency_type.value.upper()}: Unsubscribing from {len(existing_tickers)} tickers")
            self.ws.send(json.dumps(unsubscribe_message))
            self.subscribed_tickers.difference_update(existing_tickers)
            return True
        except Exception as e:
            logger.error(f"POLYGON-{self.frequency_type.value.upper()}: Error unsubscribing: {e}")
            return False


class PolygonWebSocketClient:
    """
    Multi-frequency Polygon WebSocket client supporting concurrent connections.
    
    PHASE 4 COMPLIANCE: This is an EXTERNAL BOUNDARY that:
    1. Receives raw dict data from Polygon WebSocket API
    2. Validates and parses the dict data (using .get() is CORRECT here)
    3. Creates typed TickData objects from the parsed data
    4. Passes typed objects to internal callbacks
    
    Sprint 101: Enhanced to support multiple concurrent WebSocket connections
    for different frequency types (per-second, per-minute, fair market value).
    """
    
    def __init__(self, api_key: str, on_tick_callback: Optional[Callable] = None, 
                 on_status_callback: Optional[Callable] = None, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_key = api_key
        self.on_tick_callback = on_tick_callback
        self.on_status_callback = on_status_callback
        
        # Multi-frequency connection management
        self.connections: Dict[FrequencyType, StreamConnection] = {}
        self.enabled_frequencies: List[FrequencyType] = []
        
        # URL configuration for different frequency types
        self.url_config = {
            FrequencyType.PER_SECOND: "wss://socket.polygon.io/stocks",
            FrequencyType.PER_MINUTE: "wss://socket.polygon.io/stocks", 
            FrequencyType.FAIR_MARKET_VALUE: "wss://business.polygon.io/stocks"
        }
        
        # Initialize based on config
        self._initialize_frequency_config()
    
    def _initialize_frequency_config(self):
        """Initialize enabled frequencies based on configuration - NO FALLBACKS"""
        # PRODUCTION HARDENING: Validate configuration first
        self._validate_configuration()
        
        # Check standard config keys ONLY (no fallbacks)
        if self.config.get('WEBSOCKET_PER_SECOND_ENABLED', False):
            self.enabled_frequencies.append(FrequencyType.PER_SECOND)
            logger.info("POLYGON-CLIENT: ✅ Per-second WebSocket connections ENABLED")
        else:
            logger.info("POLYGON-CLIENT: ❌ Per-second WebSocket connections DISABLED")
        
        if self.config.get('WEBSOCKET_PER_MINUTE_ENABLED', False):
            self.enabled_frequencies.append(FrequencyType.PER_MINUTE)
            logger.info("POLYGON-CLIENT: ✅ Per-minute WebSocket connections ENABLED")
        else:
            logger.info("POLYGON-CLIENT: ❌ Per-minute WebSocket connections DISABLED")
            
        if self.config.get('WEBSOCKET_FAIR_VALUE_ENABLED', False):
            self.enabled_frequencies.append(FrequencyType.FAIR_MARKET_VALUE)
            logger.info("POLYGON-CLIENT: ✅ Fair Market Value WebSocket connections ENABLED")
        else:
            logger.info("POLYGON-CLIENT: ❌ Fair Market Value WebSocket connections DISABLED")
        
        # REMOVED ALL FALLBACK CODE - Configuration must be explicit
        if not self.enabled_frequencies:
            error_msg = (
                "🚨 POLYGON-CLIENT: CONFIGURATION ERROR - No WebSocket frequencies enabled!\n"
                "   Required: Set at least one WEBSOCKET_*_ENABLED=true in configuration:\n"
                "   - WEBSOCKET_PER_SECOND_ENABLED=true\n"
                "   - WEBSOCKET_PER_MINUTE_ENABLED=true\n" 
                "   - WEBSOCKET_FAIR_VALUE_ENABLED=true"
            )
            logger.error(error_msg)
            raise ValueError("No WebSocket frequencies enabled. Configuration must be explicit.")
        
        logger.info(f"POLYGON-CLIENT: 🚀 Initialized with frequencies: {[f.value for f in self.enabled_frequencies]}")
    
    def _validate_configuration(self):
        """Validate that configuration is explicit and complete"""
        enabled_flags = {
            'WEBSOCKET_PER_SECOND_ENABLED': self.config.get('WEBSOCKET_PER_SECOND_ENABLED', False),
            'WEBSOCKET_PER_MINUTE_ENABLED': self.config.get('WEBSOCKET_PER_MINUTE_ENABLED', False),
            'WEBSOCKET_FAIR_VALUE_ENABLED': self.config.get('WEBSOCKET_FAIR_VALUE_ENABLED', False)
        }
        
        enabled_count = sum(enabled_flags.values())
        
        logger.info("POLYGON-CLIENT: 🔧 Configuration validation:")
        for flag_name, enabled in enabled_flags.items():
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            logger.info(f"POLYGON-CLIENT:    {flag_name}: {status}")
        
        if enabled_count == 0:
            error_msg = (
                "🚨 POLYGON-CLIENT: CONFIGURATION ERROR - No frequencies enabled!\n"
                "   At least one WebSocket frequency must be enabled.\n"
                "   Check your .env file configuration."
            )
            logger.error(error_msg)
            raise ValueError("At least one WebSocket frequency must be enabled")
        
        # Validate API key for FMV
        if self.config.get('WEBSOCKET_FAIR_VALUE_ENABLED') and not self.api_key:
            error_msg = (
                "🚨 POLYGON-CLIENT: CONFIGURATION ERROR - FMV requires API key!\n"
                "   WEBSOCKET_FAIR_VALUE_ENABLED=true but POLYGON_API_KEY is missing.\n"
                "   Either disable FMV or provide valid API key."
            )
            logger.error(error_msg)
            raise ValueError("Fair Market Value requires valid Polygon API key")
        
        logger.info(f"POLYGON-CLIENT: ✅ Configuration validated - {enabled_count} frequencies enabled")
    
    @property
    def connected(self) -> bool:
        """
        Check if client is connected - no primary connection assumptions.
        Returns True if ALL enabled connections are active.
        """
        if not self.connections:
            return False
        
        # Get connections for enabled frequencies only
        enabled_connections = [conn for freq, conn in self.connections.items() 
                              if freq in self.enabled_frequencies]
        
        if not enabled_connections:
            return False
            
        # ALL enabled connections must be connected for system to be "connected"
        all_connected = all(conn.connected for conn in enabled_connections)
        
        if all_connected:
            logger.debug(f"POLYGON-CLIENT: All {len(enabled_connections)} enabled connections active")
        else:
            disconnected = [conn.frequency_type.value for conn in enabled_connections if not conn.connected]
            logger.warning(f"POLYGON-CLIENT: Disconnected frequencies: {disconnected}")
            
        return all_connected
    
    @property
    def ws(self):
        """
        Get the primary WebSocket connection - backward compatibility property.
        Returns the per-second connection's WebSocket object.
        """
        primary_connection = self.connections.get(FrequencyType.PER_SECOND)
        if primary_connection:
            return primary_connection.ws
        
        # If no per-second connection, return the first available connection
        for connection in self.connections.values():
            if connection.ws:
                return connection.ws
        
        return None
    
    def _on_stream_message(self, event: Dict, frequency_type: FrequencyType):
        """Handle messages from individual stream connections"""
        try:
            self._process_event(event, frequency_type)
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error processing event from {frequency_type.value} stream: {e}")
    
    def _on_stream_status(self, status: str, extra_info: Optional[Dict] = None):
        """Handle status updates from individual stream connections"""
        if self.on_status_callback:
            try:
                self.on_status_callback(status, extra_info)
            except Exception as e:
                logger.error(f"POLYGON-CLIENT: Error in status callback: {e}")
    
    def _process_event(self, event: Dict, frequency_type: FrequencyType):
        """
        Process events from different frequency streams and convert to TickData.
        PHASE 4: This is the EXTERNAL BOUNDARY - we receive dicts and create typed objects.
        """
        if not isinstance(event, dict):
            return
            
        event_type = event.get('ev')
        
        if event_type == 'A':  # Per-second aggregate
            self._process_aggregate_event(event, is_per_second=True)
        elif event_type == 'AM':  # Per-minute aggregate  
            self._process_aggregate_event(event, is_per_second=False)
        elif event_type == 'FMV':  # Fair market value
            self._process_fmv_event(event)
        elif event_type == 'T':  # Trade event
            self._process_trade_event(event)
        elif event_type == 'Q':  # Quote event
            self._process_quote_event(event)
    
    def _process_aggregate_event(self, event: Dict, is_per_second: bool = True):
        """Process aggregate bar events (per-second 'A' or per-minute 'AM')"""
        if not self.on_tick_callback:
            return
            
        try:
            ticker = event.get('sym')
            price = event.get('c')  # Close price
            
            # Convert timestamps
            end_timestamp_ms = event.get('e', 0)
            end_timestamp_seconds = end_timestamp_ms / 1000.0
            start_timestamp_ms = event.get('s', 0)
            start_timestamp_seconds = start_timestamp_ms / 1000.0 if start_timestamp_ms else None
            
            # Detect market status
            from datetime import datetime
            import pytz
            from src.shared.utils import detect_market_status
            end_datetime = datetime.fromtimestamp(end_timestamp_seconds, tz=pytz.utc)
            current_market_status = detect_market_status(end_datetime)
            
            # Create TickData with frequency-specific event type
            frequency_suffix = "_second" if is_per_second else "_minute"
            
            tick_data = TickData(
                # Required fields
                ticker=ticker,
                price=price,
                volume=event.get('v', 0),
                timestamp=end_timestamp_seconds,
                
                # Source identification with frequency
                source='polygon',
                event_type=f"A{frequency_suffix}",
                
                # Market status
                market_status=current_market_status,
                
                # Price fields (aggregate bar data)
                tick_open=event.get('o'),
                tick_high=event.get('h'),
                tick_low=event.get('l'),
                tick_close=price,
                
                # Market open price
                market_open_price=event.get('op', price),
                
                # Volume fields
                tick_volume=event.get('v'),
                accumulated_volume=event.get('av'),
                
                # VWAP fields
                tick_vwap=event.get('vw'),
                vwap=event.get('a'),
                
                # Timing fields
                tick_start_timestamp=start_timestamp_seconds,
                tick_end_timestamp=end_timestamp_seconds,
            )
            
            self.on_tick_callback(tick_data)
            
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error processing aggregate event: {e}", exc_info=True)
    
    def _process_fmv_event(self, event: Dict):
        """Process Fair Market Value events"""
        if not self.on_tick_callback:
            return
            
        try:
            ticker = event.get('sym')
            fmv_price = event.get('fmv')
            timestamp_ns = event.get('t', 0)
            timestamp_seconds = timestamp_ns / 1_000_000_000.0  # Convert nanoseconds to seconds
            
            # Create TickData for FMV event
            tick_data = TickData(
                ticker=ticker,
                price=fmv_price,
                volume=0,  # FMV doesn't have volume
                timestamp=timestamp_seconds,
                source='polygon',
                event_type='FMV',
                market_status='REGULAR',  # Will be updated by processor
                fmv_price=fmv_price
            )
            
            self.on_tick_callback(tick_data)
            
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error processing FMV event: {e}", exc_info=True)
    
    def _process_trade_event(self, event: Dict):
        """Process Trade events"""
        if not self.on_tick_callback:
            return
            
        try:
            tick_data = TickData(
                ticker=event.get('sym'),
                price=event.get('p'),
                volume=event.get('s', 0),  # size
                timestamp=event.get('t', 0) / 1000.0,  # Convert ms to seconds
                source='polygon',
                event_type='T',
                market_status='REGULAR',
                tick_trade_size=event.get('s')
            )
            
            self.on_tick_callback(tick_data)
            
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error processing trade event: {e}", exc_info=True)
    
    def _process_quote_event(self, event: Dict):
        """Process Quote events"""
        if not self.on_tick_callback:
            return
            
        try:
            # Calculate midpoint as price
            bid = event.get('bp', 0)
            ask = event.get('ap', 0)
            midpoint = (bid + ask) / 2 if bid and ask else bid or ask
            
            tick_data = TickData(
                ticker=event.get('sym'),
                price=midpoint,
                volume=0,  # Quotes don't have volume
                timestamp=event.get('t', 0) / 1000.0,  # Convert ms to seconds
                source='polygon',
                event_type='Q',
                market_status='REGULAR',
                bid=bid,
                ask=ask
            )
            
            self.on_tick_callback(tick_data)
            
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error processing quote event: {e}", exc_info=True)
    
    def connect(self) -> bool:
        """Connect all enabled frequency streams"""
        logger.info(f"POLYGON-CLIENT: Connecting to {len(self.enabled_frequencies)} frequency streams")
        
        success_count = 0
        for frequency_type in self.enabled_frequencies:
            try:
                # Create stream connection if not exists
                if frequency_type not in self.connections:
                    url = self.url_config[frequency_type]
                    connection = StreamConnection(
                        frequency_type=frequency_type,
                        url=url,
                        api_key=self.api_key,
                        on_message_callback=self._on_stream_message,
                        on_status_callback=self._on_stream_status,
                        config=self.config
                    )
                    self.connections[frequency_type] = connection
                
                # Connect stream
                if self.connections[frequency_type].connect():
                    success_count += 1
                    logger.info(f"POLYGON-CLIENT: Successfully connected {frequency_type.value} stream")
                else:
                    logger.error(f"POLYGON-CLIENT: Failed to connect {frequency_type.value} stream")
                    
            except Exception as e:
                logger.error(f"POLYGON-CLIENT: Error connecting {frequency_type.value} stream: {e}")
        
        is_connected = success_count > 0
        if is_connected:
            logger.info(f"POLYGON-CLIENT: Connected {success_count}/{len(self.enabled_frequencies)} frequency streams")
        else:
            logger.error("POLYGON-CLIENT: Failed to connect any frequency streams")
        
        return is_connected
    
    def disconnect(self):
        """Disconnect all frequency streams"""
        logger.info("POLYGON-CLIENT: Disconnecting all frequency streams")
        
        for frequency_type, connection in self.connections.items():
            try:
                connection.disconnect()
                logger.info(f"POLYGON-CLIENT: Disconnected {frequency_type.value} stream")
            except Exception as e:
                logger.error(f"POLYGON-CLIENT: Error disconnecting {frequency_type.value} stream: {e}")
        
        self.connections.clear()
    
    def subscribe(self, tickers: List[str], frequencies: Optional[List[FrequencyType]] = None) -> bool:
        """
        Subscribe to tickers across specified frequencies.
        If frequencies not specified, subscribes to all enabled frequencies.
        """
        if not isinstance(tickers, list):
            tickers = [tickers]
        
        if not tickers:
            logger.debug("POLYGON-CLIENT: No tickers to subscribe to")
            return True
        
        # Use all enabled frequencies if not specified
        target_frequencies = frequencies or self.enabled_frequencies
        
        success_count = 0
        for frequency_type in target_frequencies:
            if frequency_type in self.connections:
                try:
                    if self.connections[frequency_type].subscribe(tickers):
                        success_count += 1
                        logger.info(f"POLYGON-CLIENT: Successfully subscribed to {len(tickers)} tickers on {frequency_type.value} stream")
                    else:
                        logger.error(f"POLYGON-CLIENT: Failed to subscribe to tickers on {frequency_type.value} stream")
                except Exception as e:
                    logger.error(f"POLYGON-CLIENT: Error subscribing to {frequency_type.value} stream: {e}")
            else:
                logger.warning(f"POLYGON-CLIENT: No connection available for {frequency_type.value} stream")
        
        return success_count > 0
    
    def unsubscribe(self, tickers: List[str], frequencies: Optional[List[FrequencyType]] = None) -> bool:
        """
        Unsubscribe from tickers across specified frequencies.
        If frequencies not specified, unsubscribes from all enabled frequencies.
        """
        if not isinstance(tickers, list):
            tickers = [tickers]
        
        if not tickers:
            logger.debug("POLYGON-CLIENT: No tickers to unsubscribe from")
            return True
        
        # Use all enabled frequencies if not specified
        target_frequencies = frequencies or self.enabled_frequencies
        
        success_count = 0
        for frequency_type in target_frequencies:
            if frequency_type in self.connections:
                try:
                    if self.connections[frequency_type].unsubscribe(tickers):
                        success_count += 1
                        logger.info(f"POLYGON-CLIENT: Successfully unsubscribed from {len(tickers)} tickers on {frequency_type.value} stream")
                    else:
                        logger.error(f"POLYGON-CLIENT: Failed to unsubscribe from tickers on {frequency_type.value} stream")
                except Exception as e:
                    logger.error(f"POLYGON-CLIENT: Error unsubscribing from {frequency_type.value} stream: {e}")
            else:
                logger.warning(f"POLYGON-CLIENT: No connection available for {frequency_type.value} stream")
        
        return success_count > 0
    
    def check_subscriptions(self):
        """
        Check subscription status - backward compatibility method.
        In the new multi-frequency implementation, this logs the status of all connections.
        """
        logger.info("POLYGON-CLIENT: Checking subscription status across all frequencies")
        
        for frequency_type, connection in self.connections.items():
            if connection.connected:
                ticker_count = len(connection.subscribed_tickers)
                logger.info(f"POLYGON-CLIENT: {frequency_type.value} stream - {ticker_count} subscribed tickers")
            else:
                logger.warning(f"POLYGON-CLIENT: {frequency_type.value} stream - disconnected")
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all frequency streams"""
        status = {}
        for frequency_type, connection in self.connections.items():
            status[frequency_type.value] = connection.connected
        return status
    
    def get_subscribed_tickers(self, frequency_type: Optional[FrequencyType] = None) -> Dict[str, set]:
        """Get subscribed tickers by frequency type"""
        if frequency_type and frequency_type in self.connections:
            return {frequency_type.value: self.connections[frequency_type].subscribed_tickers}
        
        result = {}
        for freq_type, connection in self.connections.items():
            result[freq_type.value] = connection.subscribed_tickers
        return result
    
    def is_connected(self) -> bool:
        """Check if any frequency stream is connected"""
        return any(conn.connected for conn in self.connections.values())
    
    def get_enabled_frequencies(self) -> List[str]:
        """Get list of enabled frequency types"""
        return [freq.value for freq in self.enabled_frequencies]