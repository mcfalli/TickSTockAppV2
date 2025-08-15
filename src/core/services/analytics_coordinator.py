"""
Analytics Coordination - Phase 4 Implementation
Handles analytics operations and database synchronization.
"""

import logging
import json
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'analytics_coordinator')

class DataFlowStats:
    def __init__(self):
        self.analytics_requests = 0
        self.analytics_delivered = 0
        self.sync_requests = 0
        self.sync_completed = 0
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
        
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
        
    def log_stats(self):
        logger.info(f"📊ANALYTICS-CORD: ANALYTICS FLOW: Requests:{self.analytics_requests} → "
                   f"Delivered:{self.analytics_delivered} | "
                   f"Syncs:{self.sync_requests} → Completed:{self.sync_completed}")
        self.last_log_time = time.time()

@dataclass
class AnalyticsOperationResult:
    """Result object for analytics operations."""
    success: bool = True
    analytics_data: Optional[Dict] = None
    records_processed: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    processing_time_ms: float = 0.0
    operation_type: str = "unknown"
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

class AnalyticsCoordinator:
    """
    Coordinates analytics operations and database synchronization.
    """
    @staticmethod
    def get_empty_accumulation_data(error: str = None) -> Dict[str, Any]:
        """Return empty accumulation data structure."""
        return {
            'session_date': None,
            'session_totals': {'total_highs': 0, 'total_lows': 0, 'total_events': 0, 'active_tickers': 0},
            'ticker_data': {},
            'performance_metrics': {},
            'universe_size': 0,
            'last_updated': time.time(),
            'data_source': 'memory_manager',
            'error': error
        }

    def __init__(self, config, market_service, session_accumulation_manager=None, market_analytics_manager=None):
        """Initialize analytics coordinator."""
        self.config = config
        self.market_service = market_service
        
        # Dependencies
        self.session_accumulation_manager = session_accumulation_manager or market_service.session_accumulation_manager
        self.market_analytics_manager = market_analytics_manager or market_service.market_analytics_manager

        # Data flow tracking
        self.stats = DataFlowStats()


    def get_analytics_for_websocket(self) -> AnalyticsOperationResult:
        """Get analytics data for WebSocket emission."""
        
        operation_result = AnalyticsOperationResult(operation_type="websocket_analytics")
        
        try:
            start_time = time.time()
            self.stats.analytics_requests += 1
            
            if not self.market_analytics_manager:
                logger.error("❌ANALYTICS-CORD:  ANALYTICS FAILED: No manager available")
                operation_result.analytics_data = None
                return operation_result
                
            # Get analytics from manager
            analytics_data = self.market_analytics_manager.get_analytics_for_websocket_emission()
            
            if analytics_data:
                operation_result.analytics_data = analytics_data
                operation_result.records_processed = 1
                self.stats.analytics_delivered += 1
                
            # Periodic stats
            if self.stats.should_log():
                self.stats.log_stats()
            
            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Analytics retrieval failed: {str(e)}")
            logger.error(f"❌ ANALYTICS EXCEPTION: {e}")
            
            return operation_result
    
    '''
    def get_session_accumulation_data_memory(self, tickers: List[str] = None) -> AnalyticsOperationResult:
        """Get session accumulation data from memory."""
        operation_result = AnalyticsOperationResult(operation_type="session_accumulation_memory")
        
        try:
            if not self.session_accumulation_manager:
                logger.error("🚨ANALYTICS-CORD:  NO SESSION MANAGER - Cannot retrieve accumulation data")
                operation_result.success = False
                operation_result.errors.append("Session accumulation manager not available")
                return operation_result
            
            # Get session totals
            session_totals = self.session_accumulation_manager.get_session_totals()
            
            # Get individual ticker data if requested
            ticker_data = {}
            if tickers:
                ticker_data = self.session_accumulation_manager.get_multiple_ticker_accumulation(tickers)
                operation_result.records_processed = len(ticker_data)
                
                # Log data retrieval
                if ticker_data and len(ticker_data) > 0:
                    logger.info(f"📤ANALYTICS-CORD:  SESSION DATA: {len(ticker_data)} tickers retrieved")
            
            # Get performance metrics
            performance_report = self.session_accumulation_manager.get_performance_report()
            
            # Prepare analytics data
            operation_result.analytics_data = {
                'session_date': session_totals['session_date'].isoformat() if session_totals['session_date'] else None,
                'session_totals': session_totals,
                'ticker_data': ticker_data,
                'performance_metrics': performance_report['memory_performance'],
                'sync_status': {
                    'should_sync': self.session_accumulation_manager.should_sync_to_database(),
                    'last_sync_ago': performance_report['manager_statistics']['last_sync_ago']
                },
                'universe_size': 0,
                'last_updated': time.time(),
                'data_source': 'memory_manager'
            }
            
            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Session accumulation retrieval failed: {str(e)}")
            operation_result.analytics_data = self.get_empty_accumulation_data(error=str(e))
            logger.error(f"❌ SESSION DATA EXCEPTION: {e}")
            return operation_result
    '''

    '''
    def sync_accumulation_to_database_safe(self) -> AnalyticsOperationResult:
        """Safely sync accumulation data to database."""
        operation_result = AnalyticsOperationResult(operation_type="database_sync")
        
        try:
            start_time = time.time()
            self.stats.sync_requests += 1
            
            # Check if database sync is enabled
            if not self.config.get('DATABASE_SYNC_ENABLED', True):
                return operation_result
            
            if not self.session_accumulation_manager:
                logger.error("🚨ANALYTICS-CORD:  SYNC FAILED: No session accumulation manager")
                operation_result.success = False
                operation_result.errors.append("Session accumulation manager not available")
                return operation_result
            
            # Log first sync attempt
            if self.stats.sync_requests <= 10:
                logger.info("📥ANALYTICS-CORD: logging 10 times  DATABASE SYNC attempt")
            
            # Use manager's integrated sync method
            sync_result = self.session_accumulation_manager.sync_to_database()
            
            if sync_result['success']:
                records_synced = sync_result.get('records_synced', 0)
                sync_time = sync_result.get('sync_time_ms', 0)
                
                operation_result.records_processed = records_synced
                operation_result.analytics_data = sync_result
                self.stats.sync_completed += 1
                
                # Only log when we actually sync records
                #if records_synced > 0:
                    #logger.info(f"✅ANALYTICS-CORD: DATABASE SYNC: {records_synced} records in {sync_time:.1f}ms")
                    # Log first successful sync
                    #if self.stats.sync_completed == 1:
                    #    logger.info("🎯 FIRST SUCCESSFUL DATABASE SYNC")
        


            else:
                error_msg = sync_result.get('error', 'Unknown sync error')
                operation_result.success = False
                operation_result.errors.append(error_msg)
                logger.error(f"❌ANALYTICS-CORD: SYNC FAILED: {error_msg}")
            
            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Database sync failed: {str(e)}")
            logger.error(f"❌ SYNC EXCEPTION: {e}")
            return operation_result
    '''

    '''
    def initialize_session_accumulation(self) -> AnalyticsOperationResult:
        """Initialize session accumulation systems."""
        operation_result = AnalyticsOperationResult(operation_type="session_accumulation_init")
        
        try:
            if not self.session_accumulation_manager:
                logger.error("🚨ANALYTICS-CORD: INIT FAILED: No session accumulation manager")
                operation_result.success = False
                operation_result.errors.append("Session accumulation manager not available")
                return operation_result
 
                
            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Session accumulation initialization failed: {str(e)}")
            logger.error(f"❌ SESSION INIT EXCEPTION: {e}")
            return operation_result
    '''

    '''
    def initialize_market_analytics(self) -> AnalyticsOperationResult:
        """Initialize market analytics systems."""
        operation_result = AnalyticsOperationResult(operation_type="market_analytics_init")
        
        try:
            if not self.market_analytics_manager:
                logger.error("🚨ANALYTICS-CORD: INIT FAILED: No market analytics manager")
                operation_result.success = False
                operation_result.errors.append("Market analytics manager not available")
                return operation_result
            
            # Update config if available
            if hasattr(self.market_analytics_manager.memory_analytics, 'config'):
                self.market_analytics_manager.memory_analytics.config.update(self.config)
            

            return operation_result
            
        except Exception as e:
            operation_result.success = False
            operation_result.errors.append(f"Market analytics initialization failed: {str(e)}")
            logger.error(f"❌ ANALYTICS INIT EXCEPTION: {e}")
            return operation_result
    '''
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if self.stats.analytics_requests == 0:
            logger.error("🚨ANALYTICS-CORD:  NO ANALYTICS REQUESTS - Check if WebSocket publisher is calling")
        elif self.stats.analytics_delivered == 0:
            logger.warning("⚠️ANALYTICS-CORD:  Analytics requested but NOT DELIVERED - Check analytics manager")
        
        if self.stats.sync_requests > 0 and self.stats.sync_completed == 0:
            logger.error("🚨ANALYTICS-CORD:  Database syncs attempted but NONE COMPLETED - Check database connection")
            
        # Log current stats
        logger.info(f"🔍ANALYTICS-CORD: HEALTH CHECK: Analytics {self.stats.analytics_delivered}/{self.stats.analytics_requests}, "
                   f"Syncs {self.stats.sync_completed}/{self.stats.sync_requests}")
    

    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report - simplified for debugging."""
        try:
            return {
                'analytics_flow': {
                    'requests': self.stats.analytics_requests,
                    'delivered': self.stats.analytics_delivered,
                    'success_rate': (self.stats.analytics_delivered / max(self.stats.analytics_requests, 1)) * 100
                },
                'sync_flow': {
                    'requests': self.stats.sync_requests,
                    'completed': self.stats.sync_completed,
                    'success_rate': (self.stats.sync_completed / max(self.stats.sync_requests, 1)) * 100
                },
                'dependencies': {
                    'session_accumulation_manager': self.session_accumulation_manager is not None,
                    'market_analytics_manager': self.market_analytics_manager is not None
                }
            }
        except Exception as e:
            logger.error(f"❌ PERFORMANCE REPORT ERROR: {e}")
            return {'error': str(e)}
        



    def _get_activity_level_logic(self, activity_count):
        """Get activity level determination logic for transparency."""
        # Based on market_metrics.py thresholds
        events_per_second = activity_count / 10.0  # 10-second window
        
        if events_per_second < 1.0:
            return f"{activity_count} events/10s ({events_per_second:.2f}/s) < 1.0/s → 'Very Low'"
        elif events_per_second < 10.0:
            return f"{activity_count} events/10s ({events_per_second:.2f}/s) < 10.0/s → 'Low'"
        elif events_per_second < 15.0:
            return f"{activity_count} events/10s ({events_per_second:.2f}/s) < 15.0/s → 'Medium'"
        elif events_per_second < 20.0:
            return f"{activity_count} events/10s ({events_per_second:.2f}/s) < 20.0/s → 'Medium-High'"
        elif events_per_second < 30.0:
            return f"{activity_count} events/10s ({events_per_second:.2f}/s) < 30.0/s → 'High'"
        elif events_per_second < 50.0:
            return f"{activity_count} events/10s ({events_per_second:.2f}/s) < 50.0/s → 'Very High'"
        else:
            return f"{activity_count} events/10s ({events_per_second:.2f}/s) >= 50.0/s → 'Extreme'"


