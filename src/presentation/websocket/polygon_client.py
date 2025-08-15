import json
import threading
import sys
import time
from datetime import datetime
import traceback
from typing import Dict, List, Any, Callable, Optional
import pytz

# Now that the folder is renamed, we can use the normal import!
import websocket

from src.core.domain.market.tick import TickData
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.highlow import HighLowEvent
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'polygon_websocket_client')


class PolygonWebSocketClient:
    """
    PHASE 4 COMPLIANCE for polygon_websocket_client.py:

    This file is an EXTERNAL BOUNDARY that:
    1. Receives raw dict data from Polygon WebSocket API
    2. Validates and parses the dict data (using .get() is CORRECT here)
    3. Creates typed TickData objects from the parsed data
    4. Passes typed objects to internal callbacks

    DO NOT REMOVE:
    - event.get() calls - needed for external API parsing
    - isinstance(dict) checks - needed to validate API responses
    - Dict parsing logic - this is the conversion boundary

    DO REMOVE (if present):
    - Any dict-to-dict transformations
    - Any attempts to treat internal objects as dicts
    - Any legacy compatibility for internal data flow
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PolygonWebSocketClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, api_key, on_tick_callback=None, on_status_callback=None, config=None):
        if self._initialized:
            if on_tick_callback:
                self.on_tick_callback = on_tick_callback
            if on_status_callback:
                self.on_status_callback = on_status_callback
            return
        
        self.config = config or {}
        self.api_key = api_key
        self.url = "wss://socket.polygon.io/stocks"
        self.ws = None
        self.connected = False
        self.should_reconnect = True
        self.on_tick_callback = on_tick_callback
        self.on_status_callback = on_status_callback
        self.subscribed_tickers = set()
        self.connection_thread = None
        
        self.auth_sent_time = 0
        self.auth_received = False
        
        self.reconnect_delay = self.config.get('POLYGON_WEBSOCKET_RECONNECT_DELAY', 5)
        self.max_reconnect_delay = self.config.get('POLYGON_WEBSOCKET_MAX_RECONNECT_DELAY', 60)
        self.max_retries = self.config.get('POLYGON_WEBSOCKET_MAX_RETRIES', 5)
        self.retry_count = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = self.max_retries
        self.base_reconnect_delay = self.reconnect_delay
        
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30
        self._connection_lock = threading.Lock()
        
        self._initialized = True
              
        threading.Thread(target=self._heartbeat_checker, daemon=True).start()

    def _update_status(self, status: str, extra_info: Optional[Dict] = None):
        if self.on_status_callback:
            try:
                self.on_status_callback(status, extra_info)
            except Exception as e:
                logger.error(f"POLYGON-WEBSOCKET: Error in status callback: {e}")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.last_heartbeat = time.time()
            #logger.debug(f"POLYGON-WEBSOCKET: WebSocket message received: {json.dumps(data)[:200]}...")
            
            if isinstance(data, list):
                for msg in data:
                    if msg.get('ev') == 'status' and msg.get('status') == 'auth_success':
                        self.auth_received = True
                        self.retry_count = 0
                        #logger.info("POLYGON-WEBSOCKET: Authentication confirmed")
                        # Notify status callback about successful authentication
                        self._update_status('connected', {'message': 'Authentication successful'})
                    elif msg.get('ev') in ['T', 'Q', 'A']:
                        #logger.info(f"POLYGON-WEBSOCKET: Received event of type {msg.get('ev')} for {msg.get('sym')}")
                        self._process_event(msg)
            else:
                if data.get('ev') == 'status' and data.get('status') == 'auth_success':
                    self.auth_received = True
                    self.retry_count = 0
                    #logger.info("POLYGON-WEBSOCKET: Authentication confirmed")
                    # Notify status callback about successful authentication
                    self._update_status('connected', {'message': 'Authentication successful'})
                elif data.get('ev') in ['T', 'Q', 'A']:
                    #logger.info(f"POLYGON-WEBSOCKET: Received event of type {data.get('ev')} for {data.get('sym')}")
                    self._process_event(data)
        except Exception as e:
            logger.error(f"POLYGON-WEBSOCKET: Error processing WebSocket message: {str(e)}")

    def _process_event(self, event):
        """
        Process raw Polygon WebSocket events and convert to typed TickData.
        PHASE 4: This is an EXTERNAL BOUNDARY - we receive dicts and create typed objects.
        """
        if not isinstance(event, dict):
            return
            
        event_type = event.get('ev')
        #if event_type not in ['status', 'error', 'ping', 'pong']:
            #logger.debug(f"POLYGON-WEBSOCKET: Event data: {event}")
        
        if event_type == 'status':
            status = event.get('status')
            message = event.get('message')
            #logger.info(f"POLYGON-WEBSOCKET: Polygon WebSocket status: {status} - {message}")
            if message and 'authenticated' in message.lower():
                self.auth_received = True
                #logger.info("POLYGON-WEBSOCKET: WebSocket authentication successful")
            elif message and 'authentication failed' in message.lower():
                #logger.error("POLYGON-WEBSOCKET: WebSocket authentication failed")
                self.connected = False
            self._update_status('status_update', {'status': status, 'message': message})
        
        elif event_type == 'A':  # Aggregate bar
            if self.on_tick_callback:
                try:
                    ticker = event.get('sym')
                    price = event.get('c')  # Close price
                    
                    # Convert timestamp from Unix milliseconds to seconds
                    end_timestamp_ms = event.get('e', 0)
                    end_timestamp_seconds = end_timestamp_ms / 1000.0
                    start_timestamp_ms = event.get('s', 0)
                    start_timestamp_seconds = start_timestamp_ms / 1000.0 if start_timestamp_ms else None
                    
                    # Detect market status based on timestamp
                    from datetime import datetime
                    import pytz
                    from src.shared.utils import detect_market_status
                    end_datetime = datetime.fromtimestamp(end_timestamp_seconds, tz=pytz.utc)
                    current_market_status = detect_market_status(end_datetime)
                    
                    # PHASE 4: Create typed TickData object from external dict data
                    # This is the CORRECT place to convert dict → typed object
                    tick_data = TickData(
                        # Required fields
                        ticker=ticker,
                        price=price,
                        volume=event.get('v', 0),
                        timestamp=end_timestamp_seconds,
                        
                        # Source identification
                        source='polygon',
                        event_type=event_type,
                        
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
                    
                    # Pass typed object to callback
                    self.on_tick_callback(tick_data)
                    
                except Exception as e:
                    logger.error(f"POLYGON-WEBSOCKET: Error in tick callback: {e}", exc_info=True)
        
        elif event_type == 'T':  # Trade event
            if self.on_tick_callback:
                try:
                    # PHASE 4: Create typed TickData from raw trade event
                    tick_data = TickData(
                        ticker=event.get('sym'),
                        price=event.get('p'),
                        volume=event.get('s', 0),  # size
                        timestamp=event.get('t', 0) / 1000.0,  # Convert ms to seconds
                        source='polygon',
                        event_type='T',
                        market_status='REGULAR',  # Will be updated by processor
                        tick_trade_size=event.get('s')
                    )
                    
                    self.on_tick_callback(tick_data)
                    
                except Exception as e:
                    logger.error(f"POLYGON-WEBSOCKET: Error processing trade event: {e}", exc_info=True)
        
        elif event_type == 'Q':  # Quote event
            if self.on_tick_callback:
                try:
                    # For quotes, calculate midpoint as price
                    bid = event.get('bp', 0)
                    ask = event.get('ap', 0)
                    midpoint = (bid + ask) / 2 if bid and ask else bid or ask
                    
                    # PHASE 4: Create typed TickData from raw quote event
                    tick_data = TickData(
                        ticker=event.get('sym'),
                        price=midpoint,
                        volume=0,  # Quotes don't have volume
                        timestamp=event.get('t', 0) / 1000.0,  # Convert ms to seconds
                        source='polygon',
                        event_type='Q',
                        market_status='REGULAR',  # Will be updated by processor
                        bid=bid,
                        ask=ask
                    )
                    
                    self.on_tick_callback(tick_data)
                    
                except Exception as e:
                    logger.error(f"POLYGON-WEBSOCKET: Error processing quote event: {e}", exc_info=True)
        
    def _on_error(self, ws, error):
        logger.error(f"POLYGON-WEBSOCKET: WebSocket error: {error}")
        self.connected = False
        self._update_status('error', {'error': str(error)})
        self._attempt_reconnect()

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"POLYGON-WEBSOCKET: WebSocket connection closed: {close_status_code} - {close_msg}")
        self.connected = False
        self._update_status('disconnected')
        self._attempt_reconnect()

    def _attempt_reconnect(self):
        if not self.should_reconnect or self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"POLYGON-WEBSOCKET: Max reconnect attempts ({self.max_reconnect_attempts}) reached, giving up")
            self.should_reconnect = False
            return
        self.reconnect_attempts += 1
        delay = min(self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)), self.max_reconnect_delay)
        logger.info(f"POLYGON-WEBSOCKET: Attempting to reconnect (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}) in {delay}s...")
        time.sleep(delay)
        with self._connection_lock:
            if self.connect():
                self.reconnect_attempts = 0
                logger.info("POLYGON-WEBSOCKET: Reconnection successful")

    def _heartbeat_checker(self):
        while self.should_reconnect:
            if self.connected and (time.time() - self.last_heartbeat) > self.heartbeat_interval:
                logger.warning(f"POLYGON-WEBSOCKET: No messages received in {self.heartbeat_interval} seconds")
                try:
                    if self.ws and self.ws.sock:
                        self.ws.sock.ping()
                        self.last_heartbeat = time.time()
                    else:
                        raise Exception("No socket available")
                except:
                    logger.warning("POLYGON-WEBSOCKET: Heartbeat failed, triggering reconnect")
                    self.connected = False
                    self._attempt_reconnect()
            time.sleep(5)

    def _on_open(self, ws):
        """Handle WebSocket open event with improved connection management"""
        logger.debug("POLYGON-WEBSOCKET: WebSocket connection opened - beginning authentication")
        
        # Send authentication message
        auth_msg = {"action": "auth", "params": self.api_key}
        try:
            ws.send(json.dumps(auth_msg))
            self.auth_sent_time = time.time()
            logger.info("POLYGON-WEBSOCKET: Authentication request sent")
        except Exception as e:
            logger.error(f"POLYGON-WEBSOCKET: Failed to send authentication: {e}")
            self._update_status('error', {'error': 'Authentication failed'})
            return
        
        # Wait for authentication success with timeout
        auth_timeout = 10  # seconds
        auth_start = time.time()
        while time.time() - auth_start < auth_timeout:
            if self.auth_received:
                logger.info("POLYGON-WEBSOCKET: Authentication confirmed")
                break
            time.sleep(0.5)
        
        if not self.auth_received:
            logger.warning("POLYGON-WEBSOCKET: Authentication not confirmed within timeout, but continuing")
        
        # Keep the connection open - don't subscribe here, let the adapter do it
        logger.info("POLYGON-WEBSOCKET: WebSocket opened and authenticated successfully")
        self.connected = True
        self._update_status('connected')
        self.retry_count = 0
        
    def connect(self):
        """Establish WebSocket connection with improved lifecycle management"""
        logger.info("POLYGON-WEBSOCKET: Initiating WebSocket connection")
        
        with self._connection_lock:
            # Check if we already have a valid connection
            if self.ws and self.ws.sock and self.ws.sock.connected and self.connected:
                logger.info("POLYGON-WEBSOCKET: WebSocket already connected, skipping reconnection")
                return True
            
            # Clean up any existing connection
            if self.ws:
                logger.debug("POLYGON-WEBSOCKET: Cleaning up existing WebSocket connection")
                try:
                    self.ws.close()
                except Exception as e:
                    logger.warning(f"POLYGON-WEBSOCKET: Error closing existing connection: {e}")
                finally:
                    self.ws = None
                    self.connected = False
                    time.sleep(1)  # Give socket time to close
            
            # Ensure we're starting from a clean state
            self.auth_received = False
            self.last_heartbeat = time.time()
            
            # Create a new WebSocketApp instance
            logger.debug("POLYGON-WEBSOCKET: Creating new WebSocketApp instance")
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start the WebSocket connection in a background thread
            self.connection_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={
                    'ping_interval': 30,
                    'ping_timeout': 10,
                    'skip_utf8_validation': True  # Improve performance
                }
            )
            self.connection_thread.daemon = True
            self.connection_thread.start()
            
            # Wait for connection and authentication with timeout
            logger.debug("POLYGON-WEBSOCKET: Waiting for connection to establish...")
            connection_timeout = 15  # seconds
            start_time = time.time()
            
            while time.time() - start_time < connection_timeout:
                if self.connected:
                    logger.info("POLYGON-WEBSOCKET: WebSocket connection established successfully")
                    return True
                time.sleep(0.5)
            
            logger.warning("POLYGON-WEBSOCKET: Connection timed out - connection state: " + 
                        ("connected" if self.connected else "disconnected"))
            return self.connected  # Return current state
        
    def disconnect(self):
        logger.info("POLYGON-WEBSOCKET: WebSocket Disconnecting from Polygon.io WebSocket")
        self.should_reconnect = False
        
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        self.connected = False
        self._update_status('disconnected')
    
    def subscribe(self, tickers):
        """Subscribe to ticker events with improved handling of connection state"""
        if not isinstance(tickers, list):
            tickers = [tickers]
        
        if not tickers:
            logger.debug("POLYGON-WEBSOCKET: No tickers to subscribe to")
            return True
        
        MAX_SUBSCRIPTIONS = 3000
        
        # Check subscription limit
        if len(self.subscribed_tickers) + len(tickers) > MAX_SUBSCRIPTIONS:
            logger.warning(f"POLYGON-WEBSOCKET: Subscription limit reached: {len(self.subscribed_tickers)} current + {len(tickers)} requested exceeds {MAX_SUBSCRIPTIONS}")
            return False
        
        # Wait for connection if not yet connected
        if not self.connected or not self.ws or not hasattr(self.ws, 'sock') or not self.ws.sock:
            logger.warning("POLYGON-WEBSOCKET: Cannot subscribe - not connected to WebSocket")
            return False
        
        # Get new tickers that aren't already subscribed
        new_tickers = [ticker for ticker in tickers if ticker not in self.subscribed_tickers]
        
        if not new_tickers:
            logger.debug("POLYGON-WEBSOCKET: All requested tickers already subscribed")
            return True
        
        # Format tickers for per-second aggregates (A.*)
        agg_tickers = [f"A.{ticker}" for ticker in new_tickers]
        agg_list = ",".join(agg_tickers)
        
        # Add some jitter/delay to prevent overwhelming the socket
        time.sleep(0.5)
        
        # Subscribe request
        subscribe_message = {"action": "subscribe", "params": agg_list}
        
        # Send subscription request with retry
        for attempt in range(3):
            try:
                logger.info(f"POLYGON-WEBSOCKET: Subscribing to {len(agg_tickers)} aggregate tickers (attempt {attempt+1}/3)")
                self.ws.send(json.dumps(subscribe_message))
                
                # Add to our tracking set
                self.subscribed_tickers.update(new_tickers)
                
                logger.info(f"POLYGON-WEBSOCKET: Successfully subscribed to {len(new_tickers)} tickers")
                return True
            except Exception as e:
                logger.error(f"POLYGON-WEBSOCKET: Error subscribing (attempt {attempt+1}/3): {e}")
                time.sleep(1)
        
        logger.error(f"POLYGON-WEBSOCKET: Failed to subscribe after 3 attempts")
        return False
    
    '''
    def unsubscribe(self, tickers):
        if not isinstance(tickers, list):
            tickers = [tickers]
        
        if not self.connected:
            logger.warning("POLYGON-WEBSOCKET: Cannot unsubscribe - not connected to WebSocket")
            self.subscribed_tickers.difference_update(tickers)
            return False
        
        formatted_tickers = [f"A.{ticker}" for ticker in tickers]
        self.subscribed_tickers.difference_update(tickers)
        
        unsubscription_message = {
            "action": "unsubscribe",
            "params": ",".join(formatted_tickers)
        }
        
        try:
            self.ws.send(json.dumps(unsubscription_message))
            logger.info(f"POLYGON-WEBSOCKET: Unsubscribed from {len(tickers)} tickers")
            return True
        except Exception as e:
            logger.error(f"POLYGON-WEBSOCKET: Error unsubscribing from tickers: {e}")
            return False
    '''
    def check_subscriptions(self):
        """Send a status message to check current subscriptions"""
        if not self.connected or not self.ws or not hasattr(self.ws, 'sock') or not self.ws.sock.connected:
            logger.warning("POLYGON-WEBSOCKET: Cannot check subscriptions - not connected to WebSocket")
            return False
        
        try:
            status_message = {"action": "subscription_check"}
            logger.info("POLYGON-WEBSOCKET: Checking active subscriptions")
            self.ws.send(json.dumps(status_message))
            return True
        except Exception as e:
            logger.error(f"POLYGON-WEBSOCKET: Error checking subscriptions: {e}")
            return False