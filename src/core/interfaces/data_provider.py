import abc
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from src.core.interfaces.data_result import DataResult
import logging

logger = logging.getLogger(__name__)

class DataProvider(abc.ABC):
    """Abstract base class for stock market data providers."""
    
    @abc.abstractmethod
    def get_market_status(self) -> Union[str, DataResult]:
        """
        Get the current market status.
        
        Returns:
            DataResult or str: Market status ("PRE", "REGULAR", "AFTER", or "CLOSED")
                               or DataResult with status in data field
        """
        pass
    
    @abc.abstractmethod
    def get_ticker_price(self, ticker: str) -> Union[float, DataResult]:
        """
        Get the current price for a ticker.
        
        Args:
            ticker: Stock symbol to get price for
            
        Returns:
            DataResult or float: Current price or DataResult with price in data field
        """
        pass
    
    @abc.abstractmethod
    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """
        Get detailed information for a ticker.
        
        Args:
            ticker: Stock symbol to get details for
            
        Returns:
            dict: Ticker details including price, high, low, etc.
        """
        pass
    
    @abc.abstractmethod
    def get_multiple_tickers(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get data for multiple tickers in a single call.
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            dict: Dictionary mapping tickers to their data
        """
        pass
    
    @abc.abstractmethod
    def is_available(self) -> bool:
        """
        Check if the data provider is available.
        
        Returns:
            bool: True if the provider is available, False otherwise
        """
        pass