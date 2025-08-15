"""
Session Accumulation - Memory Management Module
Handles all in-memory session accumulation tracking with zero Flask context dependencies.
"""

import time
import threading
from datetime import datetime, date
from typing import Dict, Any, Optional
from collections import defaultdict
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'memory_accumulation')

class InMemorySessionAccumulation:
    """
    Thread-safe in-memory session accumulation tracking.
    Zero Flask context dependencies - safe for use in background threads.
    """
    
    def __init__(self):
        """Initialize memory-based session accumulation."""
        self.lock = threading.Lock()
        self.session_data = defaultdict(lambda: defaultdict(lambda: {
            'high_count': 0, 
            'low_count': 0, 
            'last_updated': None
        }))
        self.current_session_date = None
        self.dirty_tickers = set()  # Track which tickers need database sync
        self.last_db_sync = 0
        self.sync_interval = 30  # Sync to database every 30 seconds
        
        # Performance tracking
        self.performance_stats = {
            'operations_completed': 0,
            'operations_per_second': 0,
            'last_performance_check': time.time(),
            'avg_operation_time_ms': 0,
            'operation_times': []
        }
        
        # Statistics
        self.stats = {
            'high_events_tracked': 0,
            'low_events_tracked': 0,
            'total_events_tracked': 0,
            'last_reset': None,
            'db_sync_count': 0,
            'db_sync_errors': 0,
            'session_resets': 0
        }
        
        logger.info("InMemorySessionAccumulation initialized - zero Flask context dependencies")
    
    def set_session_date(self, session_date: date):
        """
        Set the current session date and reset if it changed.
        
        Args:
            session_date: Current trading session date
        """
        with self.lock:
            if self.current_session_date != session_date:
                old_date = self.current_session_date
                self.current_session_date = session_date
                
                # Clear old session data but preserve statistics
                self.session_data.clear()
                self.dirty_tickers.clear()
                
                # Update statistics
                self.stats['last_reset'] = time.time()
                self.stats['session_resets'] += 1
                
                # Reset event counters for new session
                self.stats['high_events_tracked'] = 0
                self.stats['low_events_tracked'] = 0
                self.stats['total_events_tracked'] = 0
                
                logger.info(f"Session reset: {old_date} -> {session_date}")
    
    def increment_high_count(self, ticker: str) -> bool:
        """
        Increment high count for a ticker in current session.
        Thread-safe, sub-millisecond performance target.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            bool: True if successful, False otherwise
        """
        operation_start = time.time()
        
        try:
            with self.lock:
                if not self.current_session_date:
                    logger.warning(f"No session date set for high count increment: {ticker}")
                    return False
                
                # Update memory data
                self.session_data[self.current_session_date][ticker]['high_count'] += 1
                self.session_data[self.current_session_date][ticker]['last_updated'] = time.time()
                
                # Mark for database sync
                self.dirty_tickers.add(ticker)
                
                # Update statistics
                self.stats['high_events_tracked'] += 1
                self.stats['total_events_tracked'] += 1
                
                # Track performance
                self._record_operation_performance(operation_start)
                
                return True
                
        except Exception as e:
            logger.error(f"Error incrementing high count for {ticker}: {e}")
            return False
    
    def increment_low_count(self, ticker: str) -> bool:
        """
        Increment low count for a ticker in current session.
        Thread-safe, sub-millisecond performance target.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            bool: True if successful, False otherwise
        """
        operation_start = time.time()
        
        try:
            with self.lock:
                if not self.current_session_date:
                    logger.warning(f"No session date set for low count increment: {ticker}")
                    return False
                
                # Update memory data
                self.session_data[self.current_session_date][ticker]['low_count'] += 1
                self.session_data[self.current_session_date][ticker]['last_updated'] = time.time()
                
                # Mark for database sync
                self.dirty_tickers.add(ticker)
                
                # Update statistics
                self.stats['low_events_tracked'] += 1
                self.stats['total_events_tracked'] += 1
                
                # Track performance
                self._record_operation_performance(operation_start)
                
                return True
                
        except Exception as e:
            logger.error(f"Error incrementing low count for {ticker}: {e}")
            return False
    
    def _record_operation_performance(self, operation_start: float):
        """Record performance metrics for operation timing."""
        operation_time = (time.time() - operation_start) * 1000  # Convert to ms
        
        self.performance_stats['operations_completed'] += 1
        self.performance_stats['operation_times'].append(operation_time)
        
        # Keep only last 100 operation times
        if len(self.performance_stats['operation_times']) > 100:
            self.performance_stats['operation_times'] = self.performance_stats['operation_times'][-100:]
        
        # Calculate running average
        self.performance_stats['avg_operation_time_ms'] = (
            sum(self.performance_stats['operation_times']) / 
            len(self.performance_stats['operation_times'])
        )
        
        # Calculate operations per second periodically
        current_time = time.time()
        if current_time - self.performance_stats['last_performance_check'] >= 10:
            time_window = current_time - self.performance_stats['last_performance_check']
            ops_in_window = len(self.performance_stats['operation_times'])
            self.performance_stats['operations_per_second'] = ops_in_window / time_window
            self.performance_stats['last_performance_check'] = current_time
        
        # Log warning if operation is slow (target: <1ms)
        if operation_time > 2.0:
            logger.warning(f"Slow memory operation: {operation_time:.2f}ms (target: <1ms)")
    
    def get_ticker_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get accumulation data for a specific ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            dict: Ticker accumulation data
        """
        with self.lock:
            if not self.current_session_date:
                return {
                    'high_count': 0, 
                    'low_count': 0, 
                    'total_events': 0, 
                    'last_updated': None
                }
            
            data = self.session_data[self.current_session_date][ticker]
            return {
                'high_count': data['high_count'],
                'low_count': data['low_count'],
                'total_events': data['high_count'] + data['low_count'],
                'last_updated': data['last_updated']
            }
    
    def get_session_totals(self) -> Dict[str, Any]:
        """
        Get totals for the current session.
        
        Returns:
            dict: Session totals and metadata
        """
        with self.lock:
            if not self.current_session_date:
                return {
                    'total_highs': 0,
                    'total_lows': 0,
                    'total_events': 0,
                    'active_tickers': 0,
                    'session_date': None
                }
            
            session_tickers = self.session_data[self.current_session_date]
            total_highs = sum(ticker_data['high_count'] for ticker_data in session_tickers.values())
            total_lows = sum(ticker_data['low_count'] for ticker_data in session_tickers.values())
            active_tickers = len([t for t in session_tickers.values() if (t['high_count'] + t['low_count']) > 0])
            
            return {
                'total_highs': total_highs,
                'total_lows': total_lows,
                'total_events': total_highs + total_lows,
                'active_tickers': active_tickers,
                'session_date': self.current_session_date
            }
    
    def get_multiple_ticker_data(self, tickers: list) -> Dict[str, Dict[str, Any]]:
        """
        Get accumulation data for multiple tickers efficiently.
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            dict: Ticker data for all requested tickers
        """
        result = {}
        for ticker in tickers:
            result[ticker] = self.get_ticker_data(ticker)
        return result
    
    def should_sync_to_database(self) -> bool:
        """
        Check if it's time to sync to database.
        
        Returns:
            bool: True if sync is needed
        """
        current_time = time.time()
        time_since_sync = current_time - self.last_db_sync
        has_dirty_data = len(self.dirty_tickers) > 0
        
        return time_since_sync >= self.sync_interval and has_dirty_data
    
    def get_dirty_data_for_sync(self) -> Dict[str, Dict[str, Any]]:
        """
        Get data that needs to be synced to database.
        Clears dirty ticker list after retrieval.
        
        Returns:
            dict: Data ready for database sync
        """
        with self.lock:
            if not self.current_session_date or not self.dirty_tickers:
                return {}
            
            sync_data = {}
            for ticker in self.dirty_tickers:
                ticker_data = self.session_data[self.current_session_date][ticker]
                sync_data[ticker] = {
                    'session_date': self.current_session_date,
                    'high_count': ticker_data['high_count'],
                    'low_count': ticker_data['low_count'],
                    'last_updated': ticker_data['last_updated']
                }
            
            # Clear dirty tickers after getting data
            dirty_count = len(self.dirty_tickers)
            self.dirty_tickers.clear()
            self.last_db_sync = time.time()
            
            
            return sync_data
    
    def mark_sync_complete(self, success_count: int, error_count: int):
        """
        Mark database sync as complete and update statistics.
        
        Args:
            success_count: Number of successfully synced records
            error_count: Number of failed sync operations
        """
        self.stats['db_sync_count'] += 1
        if error_count > 0:
            self.stats['db_sync_errors'] += error_count
        
        if success_count > 0:
            logger.debug(f"DIAG-DB: Database sync completed: {success_count} success, {error_count} errors")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics and performance metrics.
        
        Returns:
            dict: Comprehensive statistics
        """
        with self.lock:
            current_time = time.time()
            
            # Calculate sync success rate
            total_syncs = self.stats['db_sync_count']
            sync_success_rate = ((total_syncs - self.stats['db_sync_errors']) / total_syncs * 100) if total_syncs > 0 else 100
            
            return {
                **self.stats,
                'current_session_date': self.current_session_date.isoformat() if self.current_session_date else None,
                'dirty_tickers_count': len(self.dirty_tickers),
                'last_db_sync_ago': current_time - self.last_db_sync,
                'sync_success_rate': sync_success_rate,
                'performance_metrics': {
                    'avg_operation_time_ms': self.performance_stats['avg_operation_time_ms'],
                    'operations_per_second': self.performance_stats['operations_per_second'],
                    'operations_completed': self.performance_stats['operations_completed'],
                    'target_met_sub_1ms': self.performance_stats['avg_operation_time_ms'] < 1.0
                }
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary for monitoring.
        
        Returns:
            dict: Performance summary
        """
        stats = self.get_stats()
        
        return {
            'system_health': 'optimal' if stats['performance_metrics']['target_met_sub_1ms'] else 'degraded',
            'avg_operation_time_ms': stats['performance_metrics']['avg_operation_time_ms'],
            'operations_per_second': stats['performance_metrics']['operations_per_second'],
            'total_events_tracked': stats['total_events_tracked'],
            'sync_success_rate': stats['sync_success_rate'],
            'memory_efficiency': {
                'dirty_tickers': stats['dirty_tickers_count'],
                'last_sync_ago': stats['last_db_sync_ago'],
                'sync_needed': self.should_sync_to_database()
            }
        }