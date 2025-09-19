"""Simplified Polygon WebSocket client for TickStockPL integration.

PHASE 6 CLEANUP: Simplified to single connection WebSocket client with:
- Single WebSocket connection (no multi-frequency)
- Basic connection management and reconnection
- Standard TickData conversion
- Essential event handling (A, T, Q)

Removed: Multi-frequency complexity, StreamConnection class, advanced management.
"""
import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Callable, Optional
import pytz
import websocket

from src.core.domain.market.tick import TickData
from src.shared.utils import detect_market_status
import logging

logger = logging.getLogger(__name__)

class PolygonWebSocketClient:
    """Simplified Polygon WebSocket client for basic tick data streaming."""
    
    def __init__(self, api_key: str, on_tick_callback: Optional[Callable] = None, 
                 on_status_callback: Optional[Callable] = None, config: Optional[Dict] = None):
        self.api_key = api_key
        self.on_tick_callback = on_tick_callback
        self.on_status_callback = on_status_callback
        self.config = config or {}
        
        # Connection settings
        self.url = "wss://socket.polygon.io/stocks"
        self.ws = None
        self.connected = False
        self.should_reconnect = True
        self.auth_received = False
        self.subscribed_tickers = set()
        self.subscription_confirmations = set()
        
        # Reconnection settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = self.config.get('POLYGON_WEBSOCKET_MAX_RETRIES', 5)
        self.reconnect_delay = self.config.get('POLYGON_WEBSOCKET_RECONNECT_DELAY', 5)
        
        # Thread safety
        self._connection_lock = threading.Lock()
        
        logger.info("POLYGON-CLIENT: Simplified WebSocket client initialized")
    
    def connect(self) -> bool:
        """Establish WebSocket connection."""
        logger.info(f"POLYGON-CLIENT: Connecting to {self.url}")
        
        with self._connection_lock:
            if self.ws and self.connected:
                logger.info("POLYGON-CLIENT: Already connected")
                return True
            
            # Clean up existing connection
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
                self.ws = None
                self.connected = False
                time.sleep(1)
            
            # Reset state
            self.auth_received = False
            self.subscription_confirmations = set()
            
            # Create new WebSocket
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start connection thread
            connection_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={'ping_interval': 30, 'ping_timeout': 10}
            )
            connection_thread.daemon = True
            connection_thread.start()
            
            # Wait for connection
            timeout = 15
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.connected:
                    logger.info("POLYGON-CLIENT: Connection established successfully")
                    self.reconnect_attempts = 0
                    return True
                time.sleep(0.5)
            
            logger.warning("POLYGON-CLIENT: Connection timed out")
            return False
    
    def disconnect(self):
        """Disconnect from WebSocket."""
        logger.info("POLYGON-CLIENT: Disconnecting")
        self.should_reconnect = False
        
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        self.connected = False
        if self.on_status_callback:
            self.on_status_callback('disconnected', None)
    
    def subscribe(self, tickers: List[str]) -> bool:
        """Subscribe to tickers."""
        if not isinstance(tickers, list):
            tickers = [tickers]
        
        if not self.connected:
            logger.warning("POLYGON-CLIENT: Cannot subscribe - not connected")
            return False
        
        # Filter new tickers
        new_tickers = [ticker for ticker in tickers if ticker not in self.subscribed_tickers]
        if not new_tickers:
            return True
        
        # Format subscription message (per-second aggregates)
        formatted_tickers = [f"A.{ticker}" for ticker in new_tickers]
        subscribe_message = {"action": "subscribe", "params": ",".join(formatted_tickers)}
        
        try:
            logger.info(f"POLYGON-CLIENT: Subscribing to {len(new_tickers)} tickers: {', '.join(new_tickers)}")
            self.ws.send(json.dumps(subscribe_message))
            self.subscribed_tickers.update(new_tickers)
            logger.info(f"POLYGON-CLIENT: Total subscribed tickers: {len(self.subscribed_tickers)}")
            return True
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error subscribing: {e}")
            return False
    
    def unsubscribe(self, tickers: List[str]) -> bool:
        """Unsubscribe from tickers."""
        if not isinstance(tickers, list):
            tickers = [tickers]
        
        if not self.connected:
            logger.warning("POLYGON-CLIENT: Cannot unsubscribe - not connected")
            return False
        
        # Filter existing tickers
        existing_tickers = [ticker for ticker in tickers if ticker in self.subscribed_tickers]
        if not existing_tickers:
            return True
        
        # Format unsubscription message
        formatted_tickers = [f"A.{ticker}" for ticker in existing_tickers]
        unsubscribe_message = {"action": "unsubscribe", "params": ",".join(formatted_tickers)}
        
        try:
            logger.info(f"POLYGON-CLIENT: Unsubscribing from {len(existing_tickers)} tickers")
            self.ws.send(json.dumps(unsubscribe_message))
            self.subscribed_tickers.difference_update(existing_tickers)
            return True
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error unsubscribing: {e}")
            return False
    
    def _on_open(self, ws):
        """Handle WebSocket connection open."""
        logger.info("POLYGON-CLIENT: WebSocket opened, sending authentication")
        
        # Send authentication
        auth_msg = {"action": "auth", "params": self.api_key}
        try:
            ws.send(json.dumps(auth_msg))
            logger.info("POLYGON-CLIENT: Authentication sent")
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Failed to send authentication: {e}")
            return
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            if isinstance(data, list):
                for msg in data:
                    self._process_message(msg)
            else:
                self._process_message(data)
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error processing message: {e}")
    
    def _process_message(self, msg):
        """Process individual message."""
        if msg.get('ev') == 'status':
            if msg.get('status') == 'auth_success':
                self.auth_received = True
                self.connected = True
                logger.info("POLYGON-CLIENT: Authentication confirmed - connection established")
                if self.on_status_callback:
                    self.on_status_callback('connected', {'message': 'Authentication successful'})
            else:
                status = msg.get('status')
                message = msg.get('message')
                
                # Handle subscription confirmations specially
                if status == 'success' and message and message.startswith('subscribed to:'):
                    ticker = message.replace('subscribed to: A.', '')
                    self.subscription_confirmations.add(ticker)
                    
                    # Only log summary when all subscriptions are confirmed
                    if len(self.subscription_confirmations) == len(self.subscribed_tickers):
                        logger.info(f"POLYGON-CLIENT: [SUCCESS] All {len(self.subscribed_tickers)} ticker subscriptions confirmed: {', '.join(sorted(self.subscribed_tickers))}")
                    # Log progress for large subscription sets
                    elif len(self.subscribed_tickers) > 5:
                        logger.info(f"POLYGON-CLIENT: Subscription progress: {len(self.subscription_confirmations)}/{len(self.subscribed_tickers)} confirmed")
                    else:
                        logger.info(f"POLYGON-CLIENT: Confirmed subscription: {ticker}")
                else:
                    logger.info(f"POLYGON-CLIENT: Status update - {status}: {message}")
                
                if self.on_status_callback:
                    self.on_status_callback('status_update', {'status': status, 'message': message})
        elif msg.get('ev') in ['A', 'T', 'Q']:
            self._process_tick_event(msg)
    
    def _process_tick_event(self, event: Dict):
        """Process tick events and convert to TickData."""
        if not self.on_tick_callback:
            return
        
        try:
            event_type = event.get('ev')
            ticker = event.get('sym')
            
            if event_type == 'A':  # Aggregate
                self._process_aggregate_event(event)
            elif event_type == 'T':  # Trade
                self._process_trade_event(event)
            elif event_type == 'Q':  # Quote
                self._process_quote_event(event)
        except Exception as e:
            logger.error(f"POLYGON-CLIENT: Error processing tick event: {e}")
    
    def _process_aggregate_event(self, event: Dict):
        """Process aggregate bar events."""
        ticker = event.get('sym')
        price = event.get('c')  # Close price
        end_timestamp_ms = event.get('e', 0)
        end_timestamp_seconds = end_timestamp_ms / 1000.0
        
        # Detect market status
        end_datetime = datetime.fromtimestamp(end_timestamp_seconds, tz=pytz.utc)
        market_status = detect_market_status(end_datetime)
        
        tick_data = TickData(
            ticker=ticker,
            price=price,
            volume=event.get('v', 0),
            timestamp=end_timestamp_seconds,
            source='polygon',
            event_type='A',
            market_status=market_status,
            tick_open=event.get('o'),
            tick_high=event.get('h'),
            tick_low=event.get('l'),
            tick_close=price,
            tick_volume=event.get('v'),
            tick_vwap=event.get('vw'),
            vwap=event.get('a'),
            tick_start_timestamp=event.get('s', 0) / 1000.0 if event.get('s') else None,
            tick_end_timestamp=end_timestamp_seconds
        )
        
        self.on_tick_callback(tick_data)
    
    def _process_trade_event(self, event: Dict):
        """Process trade events."""
        tick_data = TickData(
            ticker=event.get('sym'),
            price=event.get('p'),
            volume=event.get('s', 0),
            timestamp=event.get('t', 0) / 1000.0,
            source='polygon',
            event_type='T',
            market_status='REGULAR'
        )
        self.on_tick_callback(tick_data)
    
    def _process_quote_event(self, event: Dict):
        """Process quote events."""
        bid = event.get('bp', 0)
        ask = event.get('ap', 0)
        midpoint = (bid + ask) / 2 if bid and ask else bid or ask
        
        tick_data = TickData(
            ticker=event.get('sym'),
            price=midpoint,
            volume=0,
            timestamp=event.get('t', 0) / 1000.0,
            source='polygon',
            event_type='Q',
            market_status='REGULAR',
            bid=bid,
            ask=ask
        )
        self.on_tick_callback(tick_data)
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        logger.error(f"POLYGON-CLIENT: WebSocket error: {error}")
        self.connected = False
        if self.on_status_callback:
            self.on_status_callback('error', {'error': str(error)})
        self._attempt_reconnect()
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close."""
        logger.info(f"POLYGON-CLIENT: Connection closed: {close_status_code} - {close_msg}")
        self.connected = False
        if self.on_status_callback:
            self.on_status_callback('disconnected', None)
        self._attempt_reconnect()
    
    def _attempt_reconnect(self):
        """Attempt to reconnect with backoff."""
        if not self.should_reconnect or self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"POLYGON-CLIENT: Max reconnect attempts reached")
            return
        
        self.reconnect_attempts += 1
        delay = self.reconnect_delay * self.reconnect_attempts
        logger.info(f"POLYGON-CLIENT: Attempting reconnect in {delay}s (attempt {self.reconnect_attempts})")
        time.sleep(delay)
        
        if self.connect():
            logger.info("POLYGON-CLIENT: Reconnection successful")
            # Re-subscribe to existing tickers
            if self.subscribed_tickers:
                self.subscribe(list(self.subscribed_tickers))
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self.connected
    
    def get_subscribed_tickers(self) -> set:
        """Get currently subscribed tickers."""
        return self.subscribed_tickers.copy()
    
    def check_subscriptions(self):
        """Log subscription status."""
        logger.info(f"POLYGON-CLIENT: Connected: {self.connected}, Subscribed tickers: {len(self.subscribed_tickers)}")