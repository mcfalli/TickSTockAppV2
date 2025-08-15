# market_analytics/analytics_manager.py
"""
FIXED Sprint 1: Market Analytics Manager

Fixed to use accumulation → aggregation → single database record pattern.
Only processes 'core' universe data for database storage.

Key Changes:
- record_market_calculation() now accumulates instead of storing every tick
- Only 'core' universe data goes to database
- Maintains compatibility with existing calling patterns
- Enhanced reporting shows efficiency improvements
"""

import time
from datetime import date, datetime
from typing import Dict, List, Any, Optional

from src.core.services.memory_analytics import InMemoryAnalytics
from src.core.services.analytics_sync import AnalyticsSyncService
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'analytics_manager')

class AnalyticsManager:
    """
    FIXED Sprint 1: Market Analytics Manager with accumulation-based processing.
    """

    
    def __init__(self, config=None):
        """Initialize with FIXED Sprint 1 configuration."""
        self.config = config or {}

        # FIXED: Initialize with Sprint 1 configuration
        self.memory_analytics = InMemoryAnalytics(self.config)
        self.sync_service = AnalyticsSyncService()
        
        # Configuration from config or defaults
        self.aggregation_interval = self.config.get('ANALYTICS_DATABASE_SYNC_SECONDS', 10)
        self.gauge_aggregation_seconds = self.config.get('ANALYTICS_GAUGE_AGGREGATION_SECONDS', 10)
        self.vertical_aggregation_seconds = self.config.get('ANALYTICS_VERTICAL_AGGREGATION_SECONDS', 10)
            
        # Manager-level statistics
        self.manager_start_time = time.time()
        self.total_ticks_received = 0
        self.total_records_created = 0
        self.core_universe_ticks = 0
        self.user_universe_ticks = 0
        self.sync_operations = 0
        self.sync_failures = 0
        

    def initialize_session(self, session_date: date):
        """
        Initialize analytics collection for a trading session.
        
        Args:
            session_date: Trading session date
        """
        self.memory_analytics.set_session_date(session_date)
    
    def record_market_calculation(self, analytics_data: Dict[str, Any]) -> bool:
        """
        FIXED: Record market calculation with core universe filtering.
        
        Args:
            analytics_data: Market analytics data from BuySellMarketTracker
            
        Returns:
            bool: True if processed successfully
        """
        
        try:
            self.total_ticks_received += 1
            
            # FIXED: Only process 'core' universe data for database
            universe_type = analytics_data.get('universe_type', 'core')
            data_source = analytics_data.get('data_source', 'live')
            
            # Convert 'live' to 'core' for database consistency
            if data_source == 'live':
                analytics_data['data_source'] = 'core'
                data_source = 'core'
                
            
            if universe_type == 'core' and data_source == 'core':

                # FIXED: Accumulate core universe data (will create aggregated DB record)
                success = self.memory_analytics.record_market_calculation(analytics_data)
                
                if success:
                    self.core_universe_ticks += 1
                else:
                    logger.warning("⚠️ Core universe tick accumulation failed")
                return success
                
            else:
                # Log non-core data but don't process for database
                self.user_universe_ticks += 1
                
                return True  # Return True to indicate we handled it (just didn't process)
                
        except Exception as e:
            logger.error(f"Error in record_market_calculation: {e}")
            
            return False

    def should_sync_to_database(self) -> bool:
        """
        FIXED: Check if aggregated record is ready for database sync.
        
        Returns:
            bool: True if sync is needed
        """
        return self.memory_analytics.should_sync_to_database()
    
    def sync_to_database(self) -> Dict[str, Any]:
        """
        FIXED: Sync single aggregated record to database.
        
        Returns:
            dict: Sync operation results
        """
        sync_start_time = time.time()
        self.sync_operations += 1
        
        try:
            # FIXED: Get single aggregated record for sync
            dirty_data = self.memory_analytics.get_dirty_data_for_sync()
            
            if not dirty_data:
                return {
                    'success': True,
                    'records_synced': 0,
                    'message': 'No aggregated analytics data to sync',
                    'sync_time_ms': 0
                }
            
            # Perform database sync
            sync_result = self.sync_service.sync_to_database(dirty_data)
            
            # Update manager statistics
            if sync_result['success']:
                records_synced = sync_result.get('records_synced', 0)
                self.total_records_created += records_synced
                
            else:
                self.sync_failures += 1
                error_msg = sync_result.get('error', 'Unknown sync error')
                logger.error(f"FIXED SYNC FAILED: {error_msg}")
            
            # Add manager-level metadata
            sync_result['manager_metadata'] = {
                'total_sessions_synced': len(dirty_data),
                'manager_sync_operations': self.sync_operations,
                'manager_sync_failures': self.sync_failures,
                'sync_operation_time_ms': (time.time() - sync_start_time) * 1000,
                'sprint_1_fixed': True
            }
            
            return sync_result
            
        except Exception as e:
            self.sync_failures += 1
            logger.error(f"FIXED: Analytics manager sync error: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'records_synced': 0,
                'manager_error': True,
                'sprint_1_fixed': True
            }
    
    def get_sprint_1_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive Sprint 1 performance report showing improvements.
        
        Returns:
            dict: Sprint 1 performance metrics
        """
        try:
            current_time = time.time()
            uptime_hours = (current_time - self.manager_start_time) / 3600
            
            # Get memory performance
            memory_metrics = self.memory_analytics.get_performance_metrics()
            
            # Get sync metrics
            sync_metrics = self.sync_service.get_sprint_1_metrics()
            
            # Calculate efficiency improvements
            if self.total_records_created > 0:
                records_prevented = self.total_ticks_received - self.total_records_created
                efficiency_ratio = self.total_ticks_received / self.total_records_created
                database_write_reduction = ((efficiency_ratio - 1) / efficiency_ratio * 100) if efficiency_ratio > 1 else 0
            else:
                records_prevented = 0
                efficiency_ratio = 0
                database_write_reduction = 0
            
            return {
                'sprint_1_status': 'FIXED',
                'timestamp': current_time,
                
                'problem_solved': {
                    'before_sprint_1': 'Saved 100-1000+ individual tick records every 10 seconds',
                    'after_sprint_1': 'Saves 1 aggregated record every 10 seconds',
                    'records_prevented': records_prevented,
                    'efficiency_improvement': f"{efficiency_ratio:.0f}:1 ratio",
                    'database_write_reduction': f"{database_write_reduction:.1f}%"
                },
                
                'data_quality_improvements': {
                    'data_source_fixed': 'Changed from "live" to "core"',
                    'null_values_eliminated': 'All required fields populated',
                    'aggregation_logic': 'EMA weighted + non-weighted averages implemented',
                    'single_record_per_interval': True
                },
                
                'performance_metrics': {
                    'uptime_hours': uptime_hours,
                    'total_ticks_received': self.total_ticks_received,
                    'core_universe_ticks': self.core_universe_ticks,
                    'user_universe_ticks': self.user_universe_ticks,
                    'database_records_created': self.total_records_created,
                    'ticks_per_hour': self.total_ticks_received / uptime_hours if uptime_hours > 0 else 0,
                    'aggregation_interval_seconds': self.aggregation_interval
                },
                
                'memory_performance': memory_metrics.get('accumulation_performance', {}),
                'sync_performance': sync_metrics.get('sprint_1_performance', {}),
                'database_health': sync_metrics.get('data_quality', {}),
                
                'manager_statistics': {
                    'sync_operations': self.sync_operations,
                    'sync_failures': self.sync_failures,
                    'sync_success_rate': ((self.sync_operations - self.sync_failures) / 
                                        max(1, self.sync_operations)) * 100,
                    'manager_start_time': self.manager_start_time
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating Sprint 1 performance report: {e}")
            return {
                'sprint_1_status': 'ERROR',
                'timestamp': time.time(),
                'error': str(e)
            }
    
    def get_memory_handler(self) -> InMemoryAnalytics:
        """
        Get direct access to memory analytics handler for compatibility.
        
        Returns:
            InMemoryAnalytics: Fixed memory analytics handler
        """
        return self.memory_analytics
    
    def get_aggregation_status(self) -> Dict[str, Any]:
        """
        Get current aggregation status for monitoring.
        
        Returns:
            dict: Current aggregation state
        """
        try:
            memory_metrics = self.memory_analytics.get_performance_metrics()
            current_state = memory_metrics.get('current_state', {})
            
            return {
                'aggregation_active': True,
                'accumulated_ticks': current_state.get('accumulated_ticks', 0),
                'time_until_next_aggregation': current_state.get('time_until_next_aggregation', 0),
                'has_pending_database_record': current_state.get('has_pending_database_record', False),
                'session_calculation_count': current_state.get('session_calculation_count', 0),
                'aggregation_interval_seconds': self.aggregation_interval,
                'should_sync': self.should_sync_to_database()
            }
            
        except Exception as e:
            logger.error(f"Error getting aggregation status: {e}")
            return {
                'aggregation_active': False,
                'error': str(e)
            }
    '''
    def force_aggregation_and_sync(self) -> Dict[str, Any]:
        """
        Force immediate aggregation and database sync for testing.
        
        Returns:
            dict: Force operation results
        """
        try:
            
            # Force aggregation by setting last_aggregation to 0
            with self.memory_analytics.lock:
                current_time = time.time()
                if self.memory_analytics.core_accumulator['tick_count'] > 0:
                    self.memory_analytics.core_accumulator['last_aggregation'] = 0
                    self.memory_analytics._create_aggregated_database_record(current_time)
                    
                    # Attempt sync
                    sync_result = self.sync_to_database()
                    
                    return {
                        'success': True,
                        'forced_aggregation': True,
                        'ticks_aggregated': self.memory_analytics.core_accumulator['tick_count'],
                        'sync_result': sync_result,
                        'timestamp': current_time
                    }
                else:
                    return {
                        'success': False,
                        'message': 'No accumulated ticks to aggregate',
                        'ticks_accumulated': 0
                    }
                    
        except Exception as e:
            logger.error(f"Error in force aggregation and sync: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    '''
    def get_analytics_for_websocket_emission(self):
        """
        🆕 SPRINT 2: Get analytics data formatted for WebSocket emission.
        
        Returns:
            dict: Analytics data for dual universe WebSocket emission
        """
        
        try:
            current_time = time.time()
            
            # Get latest analytics data from memory
            gauge_data = self.memory_analytics.get_latest_gauge_analytics()
            vertical_data = self.memory_analytics.get_latest_vertical_analytics()
            
            # Check if we have valid analytics data
            if not gauge_data and not vertical_data:
                return None
            
            analytics_payload = {
                'core_gauge': gauge_data,
                'core_vertical': vertical_data,
                'user_gauge': None,  
                'user_vertical': None,  
                'emission_mode': 'enhanced_analytics',
                'analytics_timestamp': current_time,
                'aggregation_intervals': {
                    'gauge_seconds': self.gauge_aggregation_seconds,
                    'vertical_seconds': self.vertical_aggregation_seconds
                },
                'database_writes': {
                    'core_active': True,
                    'user_active': False
                }
            }
            
            return analytics_payload
            
        except Exception as e:
            logger.error(f"Error preparing analytics for WebSocket emission: {e}")
            
            return None
    '''
    def get_current_intervals(self) -> Dict[str, Any]:
        """
        🆕 SPRINT 2: Get current aggregation intervals for WebSocket emission metadata.
        
        Returns:
            dict: Current interval configuration for dual universe analytics
        """
        try:
            return {
                'aggregation_interval_seconds': self.aggregation_interval,
                'gauge_aggregation_seconds': getattr(self, 'gauge_aggregation_seconds', 10),
                'vertical_aggregation_seconds': getattr(self, 'vertical_aggregation_seconds', 10),
                'database_sync_seconds': self.aggregation_interval,
                'core_universe_sync_active': True,
                'user_universe_sync_active': False,  # User universe is display-only
                'memory_operation_interval': 0.5,  # Real-time memory operations
                'configuration_source': 'analytics_manager'
            }
            
        except Exception as e:
            logger.error(f"Error getting current intervals: {e}")
            # Return safe defaults
            return {
                'aggregation_interval_seconds': 10,
                'gauge_aggregation_seconds': 10,
                'vertical_aggregation_seconds': 10,
                'database_sync_seconds': 10,
                'core_universe_sync_active': True,
                'user_universe_sync_active': False,
                'memory_operation_interval': 0.5,
                'configuration_source': 'fallback_defaults'
            }
    '''

    '''
    def record_user_universe_calculation(self, analytics_data: Dict[str, Any]) -> bool:
        """
        SPRINT S11 FIX: Record user universe calculation .
        
        Args:
            analytics_data: User universe analytics data
            
        Returns:
            bool: True if processed successfully
        """
        
        try:
            # Extract universe type to confirm this is user universe data
            universe_type = analytics_data.get('universe_type', 'user')
            save_to_database = analytics_data.get('save_to_database', False)
            
            # User universe data should not save to database
            if universe_type == 'user' and not save_to_database:
                # Process for display aggregation only (no database storage)
                self.user_universe_ticks += 1
                
                return True
            else:
                logger.warning(f"Unexpected user universe data - universe_type: {universe_type}, save_to_database: {save_to_database}")
                
                return False
                
        except Exception as e:
            logger.error(f"Error recording user universe calculation: {e}")
            
            return False
    '''
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive session summary for database sync operations.
        
        Returns:
            dict: Session summary with aggregation status and performance metrics
        """
        try:
            # Get current aggregation status
            aggregation_status = self.get_aggregation_status()
            
            # Get performance report
            performance_report = self.get_sprint_1_performance_report()
            
            # Get memory handler metrics
            memory_metrics = self.memory_analytics.get_performance_metrics()
            
            # Calculate session efficiency metrics
            current_time = time.time()
            uptime_hours = (current_time - self.manager_start_time) / 3600
            
            session_summary = {
                'session_status': 'active',
                'aggregation_active': aggregation_status.get('aggregation_active', False),
                'pending_database_record': aggregation_status.get('has_pending_database_record', False),
                'should_sync': self.should_sync_to_database(),
                
                # Performance metrics
                'performance': {
                    'uptime_hours': uptime_hours,
                    'total_ticks_received': self.total_ticks_received,
                    'core_universe_ticks': self.core_universe_ticks,
                    'user_universe_ticks': self.user_universe_ticks,
                    'database_records_created': self.total_records_created,
                    'sync_operations': self.sync_operations,
                    'sync_success_rate': ((self.sync_operations - self.sync_failures) / 
                                        max(1, self.sync_operations)) * 100
                },
                
                # Memory system health
                'memory_system': {
                    'accumulation_performance': memory_metrics.get('accumulation_performance', {}),
                    'current_state': memory_metrics.get('current_state', {}),
                    'aggregation_interval_seconds': self.aggregation_interval
                },
                
                # Sprint 1 improvements
                'sprint_1_status': {
                    'database_efficiency_active': True,
                    'ema_calculations_active': True,
                    'single_record_aggregation': True,
                    'data_source_fixed': 'core'
                },
                
                # System health indicators
                'health_indicators': {
                    'memory_operations_healthy': memory_metrics.get('accumulation_performance', {}).get('average_operation_time_ms', 0) < 1.0,
                    'database_sync_healthy': self.sync_failures < 3,
                    'aggregation_current': aggregation_status.get('time_until_next_aggregation', 0) < self.aggregation_interval,
                    'overall_status': 'healthy' if self.sync_failures < 3 else 'warning'
                },
                
                'timestamp': current_time,
                'manager_version': 'sprint_1_fixed'
            }
            
            return session_summary
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return {
                'session_status': 'error',
                'error': str(e),
                'timestamp': time.time(),
                'manager_version': 'sprint_1_fixed'
            }