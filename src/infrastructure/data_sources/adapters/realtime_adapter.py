from typing import Callable, Any, List
from src.presentation.websocket.polygon_client import PolygonWebSocketClient
from src.infrastructure.data_sources.adapters.synthetic import SyntheticDataGenerator
import time
import threading
from config.logging_config import get_domain_logger, LogDomain
from src.core.domain.market.tick import TickData 


logger = get_domain_logger(LogDomain.CORE, 'real_time_data_adapter')


class RealTimeDataAdapter:
    """Adapter for handling real-time data streams from WebSocket providers."""
    
    def __init__(self, config: dict, tick_callback: Callable, status_callback: Callable):
        self.config = config
        self.tick_callback = tick_callback
        self.status_callback = status_callback
        self.client = None
        self.connection_lock = threading.Lock() 
        if config.get('USE_POLYGON_API') and config.get('POLYGON_API_KEY'):
            self.client = PolygonWebSocketClient(
                api_key=config['POLYGON_API_KEY'],
                on_tick_callback=self.tick_callback,
                on_status_callback=self.status_callback,
                config=config
            )
            
    def connect(self, tickers: List[str]) -> bool:
        if not self.client:
            logger.warning("REAL-TIME-DATA-ADAPTOR: No WebSocket client initialized - check POLYGON_API_KEY")
            return False
        
        logger.info(f"REAL-TIME-DATA-ADAPTOR: Attempting to connect to Polygon WebSocket with {len(tickers)} tickers")
        
        with self.connection_lock:
            # If we already have an existing connection, try to clean it up
            if self.client.ws:
                logger.info("REAL-TIME-DATA-ADAPTOR: Closing existing WebSocket connection")
                try:
                    self.client.ws.close()
                    self.client.connected = False
                    self.client.ws = None
                    time.sleep(3)  # Give socket time to close properly
                    logger.info("REAL-TIME-DATA-ADAPTOR: Existing connection cleared")
                except Exception as e:
                    logger.warning(f"REAL-TIME-DATA-ADAPTOR: Error closing connection: {str(e)}")
                    time.sleep(3)  # Still wait to ensure things settle

            # Try to establish the connection
            success = self.client.connect()
            if success:
                time.sleep(10)  # Wait for connection to stabilize
                if self.client.connected:
                    self.client.subscribe(tickers)
                    logger.info(f"REAL-TIME-DATA-ADAPTOR: Connected to Polygon WebSocket, subscribed to {len(tickers)} tickers: {tickers}")
                    time.sleep(5)  # Wait for subscription to complete
                    if not self.client.connected:
                        logger.error("REAL-TIME-DATA-ADAPTOR: Connection lost after subscription")
                        raise Exception("REAL-TIME-DATA-ADAPTOR: Connection lost post-subscription")
                    return True
                else:
                    logger.warning(f"REAL-TIME-DATA-ADAPTOR: Connection established but not confirmed")
            else:
                logger.warning(f"REAL-TIME-DATA-ADAPTOR: WebSocket connection attempt failed")
            
            return False

    def disconnect(self):
        """Disconnect from the WebSocket."""
        if self.client:
            self.client.disconnect()
            logger.info("REAL-TIME-DATA-ADAPTOR: Disconnected from Polygon WebSocket")

class SyntheticDataAdapter(RealTimeDataAdapter):
    def __init__(self, config, tick_callback, status_callback):
        super().__init__(config, tick_callback, status_callback)
        self.generator = SyntheticDataGenerator(config)
        self.connected = False
   
    def connect(self, tickers):
        logger.info("REAL-TIME-DATA-ADAPTOR: Starting synthetic data simulation")
        self.connected = True
        threading.Thread(target=self._simulate_events, daemon=True).start()
        return True
   
    def _simulate_events(self):
        rate = self.config.get('SYNTHETIC_DATA_RATE', 0.5)
        activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
        update_interval = self.config.get('UPDATE_INTERVAL', 0.5)
        
        while self.connected:
            # generate_events now returns TickData objects
            events = self.generator.generate_events(
                count=max(1, int(rate * len(self.generator.tickers))),
                activity_level=activity_level
            )
            
            # Events are now TickData objects, not MarketEvent
            for event in events["highs"] + events["lows"]:
                self.tick_callback(event)  # event is now a TickData object
            time.sleep(update_interval)
   
    def disconnect(self):
        self.connected = False
        logger.info("REAL-TIME-DATA-ADAPTOR: Stopped synthetic data simulation")