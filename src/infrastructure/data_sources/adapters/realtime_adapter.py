"""Simplified real-time data adapter for TickStockPL integration.

PHASE 6 CLEANUP: Simplified to basic data forwarding with:
- Simple Polygon WebSocket client integration
- Basic synthetic data simulation
- Standard callback patterns
- Redis publishing ready

Removed: Multi-frequency complexity, elaborate connection management.
"""
import time
import threading
from typing import Callable, List
from src.presentation.websocket.polygon_client import PolygonWebSocketClient
from src.infrastructure.data_sources.factory import DataProviderFactory
import logging

logger = logging.getLogger(__name__)

class RealTimeDataAdapter:
    """Simplified adapter for real-time data streams."""
    
    def __init__(self, config: dict, tick_callback: Callable, status_callback: Callable):
        self.config = config
        self.tick_callback = tick_callback
        self.status_callback = status_callback
        self.client = None
        
        # Initialize Polygon WebSocket client if configured
        if config.get('USE_POLYGON_API') and config.get('POLYGON_API_KEY'):
            self.client = PolygonWebSocketClient(
                api_key=config['POLYGON_API_KEY'],
                on_tick_callback=self.tick_callback,
                on_status_callback=self.status_callback,
                config=config
            )
            logger.info("REAL-TIME-ADAPTER: Initialized with Polygon WebSocket client")
        else:
            logger.info("REAL-TIME-ADAPTER: No WebSocket client - using synthetic data only")
    
    def connect(self, tickers: List[str]) -> bool:
        """Connect to data source and subscribe to tickers."""
        if self.client:
            logger.info(f"REAL-TIME-ADAPTER: Connecting to Polygon WebSocket with {len(tickers)} tickers")
            success = self.client.connect()
            if success:
                self.client.subscribe(tickers)
                logger.info(f"REAL-TIME-ADAPTER: Connected and subscribed to {len(tickers)} tickers")
                return True
            else:
                logger.error("REAL-TIME-ADAPTER: WebSocket connection failed")
                return False
        else:
            logger.info("REAL-TIME-ADAPTER: No WebSocket client configured")
            return False
    
    def disconnect(self):
        """Disconnect from data source."""
        if self.client:
            self.client.disconnect()
            logger.info("REAL-TIME-ADAPTER: Disconnected from WebSocket")

class SyntheticDataAdapter(RealTimeDataAdapter):
    """Adapter for synthetic data generation."""
    
    def __init__(self, config, tick_callback, status_callback):
        super().__init__(config, tick_callback, status_callback)
        self.connected = False
        self.generation_thread = None
    
    def connect(self, tickers: List[str]) -> bool:
        """Start synthetic data generation."""
        logger.info(f"REAL-TIME-ADAPTER: Starting synthetic data generation for {len(tickers)} tickers")
        self.connected = True
        self.tickers = tickers
        
        # Start generation thread
        self.generation_thread = threading.Thread(target=self._generate_data, daemon=True)
        self.generation_thread.start()
        return True
    
    def _generate_data(self):
        """Generate synthetic tick data continuously."""
        try:
            data_provider = DataProviderFactory.get_provider(self.config)
            update_interval = self.config.get('SYNTHETIC_UPDATE_INTERVAL', 1.0)
            
            logger.info(f"REAL-TIME-ADAPTER: Synthetic generation started with {update_interval}s interval")
            
            while self.connected:
                for ticker in getattr(self, 'tickers', []):
                    try:
                        tick_data = data_provider.generate_tick_data(ticker)
                        self.tick_callback(tick_data)
                    except Exception as e:
                        logger.error(f"REAL-TIME-ADAPTER: Error generating data for {ticker}: {e}")
                
                time.sleep(update_interval)
                
        except Exception as e:
            logger.error(f"REAL-TIME-ADAPTER: Data generation error: {e}")
            self.connected = False
    
    def disconnect(self):
        """Stop synthetic data generation."""
        self.connected = False
        if self.generation_thread and self.generation_thread.is_alive():
            self.generation_thread.join(timeout=2.0)
        logger.info("REAL-TIME-ADAPTER: Stopped synthetic data generation")