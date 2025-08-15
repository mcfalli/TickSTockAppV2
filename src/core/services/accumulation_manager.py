"""
Session Accumulation - Manager Module
Orchestrates memory accumulation and database sync operations.
"""

import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from config.logging_config import get_domain_logger, LogDomain

from src.core.services.memory_accumulation import InMemorySessionAccumulation
from src.core.services.database_sync import DatabaseSyncService

logger = get_domain_logger(LogDomain.CORE, 'accumulation_manager')

class SessionAccumulationManager:
    """
    Orchestrates session accumulation between memory and database.
    Main interface for all session accumulation operations.
    """
    
    def __init__(self):
        """Initialize session accumulation manager."""
        self.memory_handler = InMemorySessionAccumulation()
        self.database_sync = DatabaseSyncService()
        
        # Manager-level statistics
        self.manager_stats = {
            'total_high_events': 0,
            'total_low_events': 0,
            'sync_operations': 0,
            'sync_failures': 0,
            'last_sync_attempt': 0,
            'manager_start_time': time.time()
        }
        
    
    def initialize_session(self, session_date: date):
        """
        Initialize accumulation for a new session.
        
        Args:
            session_date: Trading session date
        """
        try:
            self.memory_handler.set_session_date(session_date)
            
        except Exception as e:
            logger.error(f"Error initializing session {session_date}: {e}")
            raise
    
    def record_high_event(self, ticker: str) -> bool:
        """
        Record a high event for a ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            bool: True if recorded successfully
        """
        try:
            success = self.memory_handler.increment_high_count(ticker)
            if success:
                self.manager_stats['total_high_events'] += 1

            
            return success
            
        except Exception as e:
            logger.error(f"Error recording high event for {ticker}: {e}")
            return False
    
    def record_low_event(self, ticker: str) -> bool:
        """
        Record a low event for a ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            bool: True if recorded successfully
        """
        try:
            success = self.memory_handler.increment_low_count(ticker)
            if success:
                self.manager_stats['total_low_events'] += 1

            
            return success
            
        except Exception as e:
            logger.error(f"Error recording low event for {ticker}: {e}")
            return False
    
    '''
    def get_ticker_accumulation(self, ticker: str) -> Dict[str, Any]:
        """
        Get accumulation data for a specific ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            dict: Ticker accumulation data
        """
        try:
            return self.memory_handler.get_ticker_data(ticker)
        except Exception as e:
            logger.error(f"Error getting ticker accumulation for {ticker}: {e}")
            return {'high_count': 0, 'low_count': 0, 'total_events': 0, 'last_updated': None}
    '''

    def get_multiple_ticker_accumulation(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get accumulation data for multiple tickers.
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            dict: Accumulation data for all tickers
        """
        try:
            return self.memory_handler.get_multiple_ticker_data(tickers)
        except Exception as e:
            logger.error(f"Error getting multiple ticker accumulation: {e}")
            return {}
    
    def get_session_totals(self) -> Dict[str, Any]:
        """
        Get total accumulation for current session.
        
        Returns:
            dict: Session totals and metadata
        """
        try:
            totals = self.memory_handler.get_session_totals()
            
            # Add manager-level metadata
            totals['manager_metadata'] = {
                'total_events_processed': self.manager_stats['total_high_events'] + self.manager_stats['total_low_events'],
                'sync_operations_completed': self.manager_stats['sync_operations'],
                'sync_failure_count': self.manager_stats['sync_failures'],
                'manager_uptime_hours': (time.time() - self.manager_stats['manager_start_time']) / 3600
            }
            
            return totals
            
        except Exception as e:
            logger.error(f"Error getting session totals: {e}")
            return {
                'total_highs': 0, 'total_lows': 0, 'total_events': 0, 
                'active_tickers': 0, 'session_date': None
            }
    
    def should_sync_to_database(self) -> bool:
        """
        Check if database sync is needed.
        
        Returns:
            bool: True if sync should be performed
        """
        try:
            return self.memory_handler.should_sync_to_database()
        except Exception as e:
            logger.error(f"Error checking sync requirement: {e}")
            return False
    
    def sync_to_database(self) -> Dict[str, Any]:
        """
        Sync memory data to database.
        
        Returns:
            dict: Sync operation results
        """
        self.manager_stats['last_sync_attempt'] = time.time()
        
        try:
            # Get data to sync from memory
            sync_data = self.memory_handler.get_dirty_data_for_sync()
            
            if not sync_data:
                return {
                    'success': True,
                    'message': 'No data to sync',
                    'records_synced': 0
                }
            
            # Perform database sync
            sync_result = self.database_sync.sync_to_database(sync_data)
            
            # Update memory handler with results
            if sync_result['success']:
                success_count = sync_result.get('records_synced', 0)
                error_count = sync_result.get('records_failed', 0)
                
                self.memory_handler.mark_sync_complete(success_count, error_count)
                self.manager_stats['sync_operations'] += 1
                

            else:
                self.manager_stats['sync_failures'] += 1
                logger.error(f"Sync failed: {sync_result.get('error', 'Unknown error')}")
            
            return sync_result
            
        except Exception as e:
            self.manager_stats['sync_failures'] += 1
            logger.error(f"Error during database sync: {e}")
            
            return {
                'success': False,
                'error': f'Sync operation failed: {str(e)}',
                'records_synced': 0
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.
        
        Returns:
            dict: Performance metrics and health status
        """
        try:
            # Get memory performance
            memory_performance = self.memory_handler.get_performance_summary()
            
            # Get database sync statistics
            database_stats = self.database_sync.get_sync_statistics()
            
            # Calculate overall health
            memory_healthy = memory_performance['system_health'] == 'optimal'
            database_healthy = database_stats['performance_health']['success_rate_good']
            
            overall_health = 'optimal' if (memory_healthy and database_healthy) else \
                           'healthy' if memory_healthy else \
                           'degraded' if database_healthy else 'error'
            
            return {
                'overall_health': overall_health,
                'timestamp': time.time(),
                'memory_performance': memory_performance,
                'database_performance': database_stats,
                'manager_statistics': {
                    'total_events_processed': self.manager_stats['total_high_events'] + self.manager_stats['total_low_events'],
                    'high_events': self.manager_stats['total_high_events'],
                    'low_events': self.manager_stats['total_low_events'],
                    'sync_operations': self.manager_stats['sync_operations'],
                    'sync_failures': self.manager_stats['sync_failures'],
                    'sync_success_rate': self._calculate_sync_success_rate(),
                    'last_sync_ago': time.time() - self.manager_stats['last_sync_attempt'],
                    'uptime_hours': (time.time() - self.manager_stats['manager_start_time']) / 3600
                },
                'integration_status': {
                    'memory_system_operational': memory_performance['system_health'] in ['optimal', 'healthy'],
                    'database_system_operational': database_stats['flask_context_available'] and database_stats['performance_health']['success_rate_good'],
                    'sync_system_operational': self._calculate_sync_success_rate() >= 90,
                    'zero_flask_context_errors': True  # Always true with this architecture
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {
                'overall_health': 'error',
                'timestamp': time.time(),
                'error': str(e),
                'integration_status': {
                    'zero_flask_context_errors': True
                }
            }
    
    def _calculate_sync_success_rate(self) -> float:
        """Calculate sync success rate."""
        total_operations = self.manager_stats['sync_operations'] + self.manager_stats['sync_failures']
        if total_operations == 0:
            return 100.0
        return (self.manager_stats['sync_operations'] / total_operations) * 100
    
    '''
    def validate_system_health(self) -> Dict[str, Any]:
        """
        Validate overall system health.
        
        Returns:
            dict: System health validation results
        """
        try:
            validation_result = {
                'validation_time': time.time(),
                'memory_system': {},
                'database_system': {},
                'integration_system': {},
                'overall_status': 'unknown'
            }
            
            # Validate memory system
            memory_stats = self.memory_handler.get_stats()
            validation_result['memory_system'] = {
                'operational': memory_stats['performance_metrics']['target_met_sub_1ms'],
                'avg_operation_time_ms': memory_stats['performance_metrics']['avg_operation_time_ms'],
                'operations_per_second': memory_stats['performance_metrics']['operations_per_second'],
                'total_events_tracked': memory_stats['total_events_tracked']
            }
            
            # Validate database system
            db_validation = self.database_sync.validate_database_connection()
            validation_result['database_system'] = {
                'operational': db_validation['database_accessible'] and db_validation['query_test_successful'],
                'flask_context_available': db_validation['flask_context_available'],
                'connection_healthy': db_validation['database_accessible'],
                'query_test_passed': db_validation.get('query_test_successful', False)
            }
            
            # Validate integration
            sync_rate = self._calculate_sync_success_rate()
            validation_result['integration_system'] = {
                'operational': sync_rate >= 90,
                'sync_success_rate': sync_rate,
                'should_sync_now': self.should_sync_to_database(),
                'last_sync_ago': time.time() - self.manager_stats['last_sync_attempt']
            }
            
            # Determine overall status
            memory_ok = validation_result['memory_system']['operational']
            database_ok = validation_result['database_system']['operational']
            integration_ok = validation_result['integration_system']['operational']
            
            if memory_ok and database_ok and integration_ok:
                validation_result['overall_status'] = 'optimal'
            elif memory_ok and integration_ok:
                validation_result['overall_status'] = 'healthy'  # Database issues but system working
            elif memory_ok:
                validation_result['overall_status'] = 'degraded'  # Memory working, sync issues
            else:
                validation_result['overall_status'] = 'error'  # Memory system problems
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating system health: {e}")
            return {
                'validation_time': time.time(),
                'overall_status': 'error',
                'error': str(e)
            }
    '''
    def get_memory_handler(self) -> InMemorySessionAccumulation:
        """
        Get direct access to memory handler (for advanced use cases).
        
        Returns:
            InMemorySessionAccumulation: Memory handler instance
        """
        return self.memory_handler
    '''
    def get_database_sync_service(self) -> DatabaseSyncService:
        """
        Get direct access to database sync service (for advanced use cases).
        
        Returns:
            DatabaseSyncService: Database sync service instance
        """
        return self.database_sync
    '''