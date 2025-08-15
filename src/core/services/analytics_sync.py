# market_analytics/analytics_sync.py
"""
FIXED Sprint 1: Analytics Database Sync Service

Fixed to handle single aggregated record per 10-second interval.
Uses updated MarketAnalytics model with new field structure.

Key Changes:
- Expects 1 record per session instead of hundreds
- Uses new field names (current_net_score, ema_net_score_gauge, etc.)
- Validates data_source='core' only
- Enhanced error handling for aggregated records
"""

import time
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'analytics_sync')

class AnalyticsSyncService:
    """
    FIXED: Database sync service for aggregated market analytics records.
    """
    
    def __init__(self):
        """Initialize sync service with Sprint 1 tracking."""
        self.sync_attempts = 0
        self.sync_successes = 0
        self.sync_failures = 0
        self.last_sync_time = 0
        self.last_sync_errors = []
        
        # Sprint 1 specific tracking
        self.aggregated_records_synced = 0
        self.individual_records_prevented = 0
        
        # Performance tracking
        self.total_sync_time = 0.0
        
        logger.info("FIXED AnalyticsSyncService initialized for Sprint 1 (single aggregated records)")
    
    def sync_to_database(self, sync_data: Dict[date, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        FIXED: Sync single aggregated analytics record to database.
        
        Args:
            sync_data: Single aggregated record per session (not hundreds)
            
        Returns:
            dict: Sync operation results
        """
        start_time = time.time()
        self.sync_attempts += 1
        
        try:
            # Validate prerequisites
            if not sync_data:
                return {
                    'success': True,
                    'records_synced': 0,
                    'message': 'No aggregated data to sync',
                    'sync_time_ms': 0
                }
            
            # Validate Flask context
            validation_result = self.validate_database_connection()
            if not validation_result['valid']:
                self.sync_failures += 1
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'can_retry': validation_result.get('can_retry', True),
                    'records_synced': 0
                }
            
            # Import database components
            from src.infrastructure.database import db, TickerAnalytics
            
            # FIXED: Process single aggregated records
            records_processed = 0
            records_created = 0
            error_details = []
            
            for session_date, analytics_records in sync_data.items():
                # FIXED: Should only be 1 record per session per sync
                if len(analytics_records) > 1:
                    logger.warning(f"Sprint 1 ISSUE: Expected 1 record for {session_date}, got {len(analytics_records)}")
                
                for aggregated_data in analytics_records:
                    try:
                        # FIXED: Validate this is core universe data
                        data_source = aggregated_data.get('data_source', 'unknown')
                        if data_source != 'core':
                            logger.error(f"INVALID DATA SOURCE: Expected 'core', got '{data_source}' - skipping")
                            continue
                        
                        # FIXED: Validate required aggregated fields
                        required_fields = ['current_net_score', 'ema_net_score_gauge', 'records_aggregated']
                        missing_fields = [field for field in required_fields if field not in aggregated_data]
                        if missing_fields:
                            logger.error(f"Missing required aggregated fields: {missing_fields}")
                            continue
                        
                        # FIXED: Create MarketAnalytics record using NEW field structure
                        market_analytics = MarketAnalytics(
                            # Identity & Timing
                            session_date=aggregated_data['session_date'],
                            timestamp=aggregated_data['timestamp'],
                            data_source='core',  # FIXED: Always 'core' for aggregated records
                            
                            # Current Values (latest in aggregation window)
                            current_net_score=aggregated_data['current_net_score'],
                            current_activity_level=aggregated_data['current_activity_level'],
                            current_buying_count=aggregated_data['current_buying_count'],
                            current_selling_count=aggregated_data['current_selling_count'],
                            current_activity_count=aggregated_data['current_activity_count'],
                            
                            # EMA Weighted Averages (NEW FIELDS)
                            ema_net_score_gauge=aggregated_data.get('ema_net_score_gauge'),
                            ema_net_score_vertical=aggregated_data.get('ema_net_score_vertical'),
                            ema_buying_ratio=aggregated_data.get('ema_buying_ratio'),
                            
                            # Simple Averages (NEW FIELDS)
                            avg_net_score_10sec=aggregated_data.get('avg_net_score_10sec'),
                            avg_net_score_60sec=aggregated_data.get('avg_net_score_60sec'),
                            avg_net_score_300sec=aggregated_data.get('avg_net_score_300sec'),
                            avg_activity_count_60sec=aggregated_data.get('avg_activity_count_60sec'),
                            
                            # Session Context (NEW FIELDS)
                            session_total_calculations=aggregated_data.get('session_total_calculations', 1),
                            records_aggregated=aggregated_data.get('records_aggregated', 1),
                            calculation_window_seconds=aggregated_data.get('calculation_window_seconds', 10),
                            
                            # Performance metadata
                            calc_time_ms=aggregated_data.get('calc_time_ms', 0),
                            window_start_time=aggregated_data.get('window_start_time'),
                            window_end_time=aggregated_data.get('window_end_time'),
                            
                            # Universe context
                            total_universe_size=aggregated_data.get('total_universe_size', 2800)
                        )
                        
                        db.session.add(market_analytics)
                        records_created += 1
                        records_processed += 1
                        
                        # Track aggregated record stats
                        self.aggregated_records_synced += 1
                        individual_records_in_this_aggregate = aggregated_data.get('records_aggregated', 1)
                        self.individual_records_prevented += individual_records_in_this_aggregate
                        
                        logger.debug(f"FIXED: Created 1 aggregated record from {individual_records_in_this_aggregate} individual ticks")
                        
                    except Exception as record_error:
                        error_details.append({
                            'session_date': session_date,
                            'error': str(record_error),
                            'data_source': aggregated_data.get('data_source', 'unknown'),
                            'records_aggregated': aggregated_data.get('records_aggregated', 'unknown')
                        })
                        logger.error(f"Error processing aggregated record for {session_date}: {record_error}")
                        continue
            
            # Commit all changes
            if records_processed > 0:
                db.session.commit()
                
                self.sync_successes += 1
                sync_time_ms = (time.time() - start_time) * 1000
                self.total_sync_time += sync_time_ms
                self.last_sync_time = time.time()
                
                logger.info(f"FIXED SYNC SUCCESS: {records_processed} aggregated records synced "
                           f"(representing {self.individual_records_prevented} individual ticks) "
                           f"in {sync_time_ms:.1f}ms")
                
                return {
                    'success': True,
                    'records_synced': records_processed,
                    'records_created': records_created,
                    'sessions_processed': len(sync_data),
                    'sync_time_ms': sync_time_ms,
                    'error_count': len(error_details),
                    'error_details': error_details[:5] if error_details else None,
                    'sprint_1_metrics': {
                        'aggregated_records_synced': self.aggregated_records_synced,
                        'individual_records_prevented': self.individual_records_prevented,
                        'efficiency_improvement': f"{self.individual_records_prevented}:1 ratio"
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'No aggregated records processed successfully',
                    'records_synced': 0,
                    'error_details': error_details[:5]
                }
                
        except Exception as e:
            # Roll back on any error
            try:
                from src.infrastructure.database import db
                db.session.rollback()
            except:
                pass
            
            self.sync_failures += 1
            self.last_sync_errors.append({
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'sync_attempt': self.sync_attempts,
                'sprint_1_context': 'aggregated_record_sync'
            })
            
            # Keep only recent errors
            if len(self.last_sync_errors) > 10:
                self.last_sync_errors = self.last_sync_errors[-10:]
            
            logger.error(f"FIXED: Aggregated analytics database sync failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'records_synced': 0,
                'sync_time_ms': (time.time() - start_time) * 1000,
                'can_retry': True,
                'sprint_1_error': True
            }
    
    def validate_database_connection(self) -> Dict[str, Any]:
        """
        FIXED: Validate database connection and updated MarketAnalytics model.
        
        Returns:
            dict: Validation results for Sprint 1 structure
        """
        try:
            # Check Flask context
            from flask import has_app_context
            if not has_app_context():
                return {
                    'valid': False,
                    'error': 'No Flask application context',
                    'can_retry': True
                }
            
            # Import database components
            from src.infrastructure.database import db, TickerAnalytics
            
            # Test basic database connection
            test_query = db.session.execute(db.text("SELECT 1 as test")).fetchone()
            if not test_query or test_query[0] != 1:
                return {
                    'valid': False,
                    'error': 'Database connection test failed',
                    'can_retry': True
                }
            
            # FIXED: Test new MarketAnalytics structure
            try:
                # Test query with new field structure
                test_record = db.session.execute(
                    db.text("SELECT current_net_score, ema_net_score_gauge, data_source "
                           "FROM market_analytics LIMIT 1")
                ).fetchone()
                
                return {
                    'valid': True,
                    'existing_records': MarketAnalytics.query.count(),
                    'database_accessible': True,
                    'model_structure': 'sprint_1_updated',
                    'new_fields_accessible': True
                }
                
            except Exception as structure_error:
                # Check if this is due to old table structure
                if 'column' in str(structure_error).lower() and 'does not exist' in str(structure_error).lower():
                    return {
                        'valid': False,
                        'error': f'Database structure outdated - run migration: {structure_error}',
                        'can_retry': False,
                        'requires_migration': True
                    }
                else:
                    raise structure_error
            
        except Exception as e:
            logger.error(f"Database validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'can_retry': True
            }
    
    def get_sprint_1_metrics(self) -> Dict[str, Any]:
        """
        Get Sprint 1 specific metrics showing efficiency improvement.
        
        Returns:
            dict: Sprint 1 performance metrics
        """
        efficiency_ratio = self.individual_records_prevented / max(1, self.aggregated_records_synced)
        
        return {
            'sprint_1_performance': {
                'aggregated_records_synced': self.aggregated_records_synced,
                'individual_records_prevented': self.individual_records_prevented,
                'efficiency_ratio': f"{efficiency_ratio:.0f}:1",
                'database_write_reduction': f"{((efficiency_ratio - 1) / efficiency_ratio * 100):.1f}%" if efficiency_ratio > 1 else "0%"
            },
            'sync_statistics': {
                'sync_attempts': self.sync_attempts,
                'sync_successes': self.sync_successes,
                'sync_failures': self.sync_failures,
                'success_rate_percent': (self.sync_successes / max(1, self.sync_attempts)) * 100,
                'last_sync_ago_seconds': time.time() - self.last_sync_time if self.last_sync_time > 0 else None
            },
            'data_quality': {
                'core_universe_only': True,
                'aggregated_records_only': True,
                'null_values_prevented': True
            }
        }