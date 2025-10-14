"""
Session Accumulation - Database Sync Module
Handles all database operations with proper Flask context management.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabaseSyncService:
    """
    Handles database synchronization for session accumulation.
    Only operates within Flask application context.
    """

    def __init__(self):
        """Initialize database sync service."""
        self.sync_stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'records_synced': 0,
            'last_sync_time': 0,
            'avg_sync_time_ms': 0,
            'sync_times': []
        }

        # Track detailed error information
        self.last_sync_errors = []


    def is_flask_context_available(self) -> bool:
        """
        Check if Flask application context is available.
        
        Returns:
            bool: True if Flask context is available
        """
        try:
            from flask import has_app_context
            return has_app_context()
        except ImportError:
            logger.error("Flask not available - cannot check application context")
            return False
        except Exception as e:
            logger.warning(f"Error checking Flask context: {e}")
            return False

    def validate_database_connection(self) -> dict[str, Any]:
        """
        Validate database connection with proper SQLAlchemy 2.x syntax.
        Uses EventSession model with event_session table.
        """
        validation_result = {
            'flask_context_available': False,
            'database_accessible': False,
            'model_imports_successful': False,
            'query_test_successful': False,
            'validation_time': time.time()
        }

        try:
            # Check Flask context
            validation_result['flask_context_available'] = self.is_flask_context_available()

            if not validation_result['flask_context_available']:
                validation_result['error'] = 'No Flask application context available'
                return validation_result

            # FIXED: Import EventSession model
            from src.infrastructure.database import EventSession, db
            validation_result['model_imports_successful'] = True

            # Test database access with proper SQLAlchemy 2.x syntax
            try:
                # FIXED: Use text() wrapper for raw SQL
                result = db.session.execute(text("SELECT 1 as test")).fetchone()

                if result and result[0] == 1:
                    validation_result['database_accessible'] = True

                    # Test EventSession table access
                    count = EventSession.query.count()
                    validation_result['query_test_successful'] = True
                    validation_result['record_count'] = count

                else:
                    validation_result['query_error'] = 'Database test query returned unexpected result'

            except Exception as query_error:
                validation_result['database_accessible'] = False
                validation_result['query_error'] = str(query_error)
                logger.warning(f"Database query test failed: {query_error}")

        except ImportError as import_error:
            validation_result['import_error'] = str(import_error)
            logger.error(f"Model import failed: {import_error}")
        except Exception as e:
            validation_result['error'] = str(e)
            logger.error(f"Database validation error: {e}")

        return validation_result

    def sync_to_database(self, sync_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """
        ENHANCED: Sync accumulation data to database with detailed error tracking.
        
        Args:
            sync_data: Dictionary of ticker data to sync
            
        Returns:
            dict: Sync results and statistics
        """
        sync_start_time = time.time()

        # Validate Flask context first
        if not self.is_flask_context_available():
            logger.warning("DIAG-DATABASE: Flask context not available - cannot sync to database")
            return {
                'success': False,
                'error': 'No Flask application context',
                'records_synced': 0,
                'records_failed': 0
            }

        if not sync_data:
            # No data to sync - early return
            return {
                'success': True,
                'records_synced': 0,
                'records_failed': 0,
                'message': 'No data to sync'
            }

        # Validate database connection before proceeding
        db_validation = self.validate_database_connection()
        if not db_validation.get('database_accessible', False):
            error_msg = f"Database validation failed: {db_validation.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'records_synced': 0,
                'records_failed': len(sync_data)
            }

        try:
            # Import database models (only when we know we're in Flask context)
            from src.infrastructure.database import EventSession, db

            success_count = 0
            error_count = 0
            error_details = []

            # Clear previous errors
            self.last_sync_errors = []

            # Database sync is normal operation - minimal logging
            sample_tickers = list(sync_data.keys())[:3]

            # Process each ticker's data
            for ticker, data in sync_data.items():
                try:
                    record_result = self._sync_ticker_record(ticker, data, EventSession, db)
                    if record_result['success']:
                        success_count += 1
                    else:
                        error_count += 1
                        error_msg = f"{ticker}: {record_result['error']}"
                        error_details.append(error_msg)
                        self.last_sync_errors.append(error_msg)
                        logger.warning(f"DIAG-DATABASE: Failed to process {ticker}: {record_result['error']}")

                except Exception as e:
                    error_count += 1
                    error_message = f"Error syncing {ticker}: {str(e)}"
                    error_details.append(error_message)
                    self.last_sync_errors.append(error_message)
                    logger.error(error_message)

            # ENHANCED: Check if we actually have objects to commit
            pending_objects = len(db.session.new) + len(db.session.dirty)
            # Track pending objects for diagnostics

            # Commit all changes in one transaction
            if success_count > 0:
                try:
                    # Committing records - normal operation
                    db.session.commit()
                    sync_time_ms = (time.time() - sync_start_time) * 1000

                    # ENHANCED: Verify records actually made it to database
                    verification_count = 0
                    for ticker in sample_tickers:
                        if ticker in sync_data:
                            verification = EventSession.query.filter_by(
                                ticker=ticker,
                                session_date=sync_data[ticker]['session_date']
                            ).first()
                            if verification:
                                verification_count += 1

                    # Database sync completed successfully

                    # Update performance statistics
                    self._update_sync_stats(success_count, error_count, sync_time_ms)

                    return {
                        'success': True,
                        'records_synced': success_count,
                        'records_failed': error_count,
                        'sync_time_ms': sync_time_ms,
                        'verification_count': verification_count,
                        'error_details': error_details if error_details else None
                    }

                except Exception as commit_error:
                    logger.error(f"Database commit failed: {commit_error}")
                    logger.error(f"Pending objects when commit failed: new={len(db.session.new)}, dirty={len(db.session.dirty)}")

                    try:
                        db.session.rollback()
                        logger.debug("DIAG-DATABASE: Database session rolled back successfully")
                    except Exception as rollback_error:
                        logger.error(f"DIAG-DATABASE: Rollback also failed: {rollback_error}")

                    self._update_sync_stats(0, len(sync_data), 0)

                    return {
                        'success': False,
                        'error': f'Database commit failed: {str(commit_error)}',
                        'records_synced': 0,
                        'records_failed': len(sync_data),
                        'commit_error': True
                    }
            else:
                logger.warning(f"DIAG-DATABASE: Database sync completed with no successful records: {error_count} errors")
                self._update_sync_stats(0, error_count, 0)

                # Log first few errors for debugging
                if self.last_sync_errors:
                    logger.error(f"DIAG-DATABASE: Sample sync errors: {self.last_sync_errors[:3]}")

                return {
                    'success': False,
                    'error': 'No records successfully processed',
                    'records_synced': 0,
                    'records_failed': error_count,
                    'error_details': error_details,
                    'sample_errors': self.last_sync_errors[:5]  # First 5 errors for debugging
                }

        except Exception as e:
            logger.error(f"Critical error during database sync: {e}")
            logger.error(f"Sync data sample: {dict(list(sync_data.items())[:2])}")

            # Attempt rollback if possible
            try:
                if self.is_flask_context_available():
                    from src.infrastructure.database import db
                    db.session.rollback()
                    logger.debug("DIAG-DATABASE: Emergency rollback completed")
            except Exception as rollback_error:
                logger.error(f"Emergency rollback failed: {rollback_error}")

            self._update_sync_stats(0, len(sync_data), 0)

            return {
                'success': False,
                'error': f'Critical sync error: {str(e)}',
                'records_synced': 0,
                'records_failed': len(sync_data),
                'critical_error': True
            }

    def _sync_ticker_record(self, ticker: str, data: dict[str, Any], EventSession, db) -> dict[str, Any]:
        """
        ENHANCED: Sync a single ticker's accumulation record with validation.
        """
        try:
            # ADDED: Validate ticker length before processing
            if len(ticker) > 20:  # Even with increased limit, validate
                return {
                    'success': False,
                    'error': f'Ticker too long ({len(ticker)} chars): {ticker[:20]}...'
                }

            # Validate required data fields
            required_fields = ['session_date', 'high_count', 'low_count']
            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }

            # Get or create database record
            record = EventSession.query.filter_by(
                ticker=ticker,
                session_date=data['session_date']
            ).first()

            if not record:
                # Create new record with validation
                record = EventSession(
                    ticker=ticker[:20],  # ADDED: Truncate to ensure it fits
                    session_date=data['session_date'],
                    high_count=data['high_count'],
                    low_count=data['low_count']
                )
                db.session.add(record)
                action = 'created'
                # New accumulation record created
            else:
                # Update existing record
                record.high_count = data['high_count']
                record.low_count = data['low_count']
                action = 'updated'
                # Existing accumulation record updated

            # Update timestamp (use timezone-aware datetime)
            record.last_updated = datetime.now(UTC)

            return {
                'success': True,
                'action': action
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _update_sync_stats(self, success_count: int, error_count: int, sync_time_ms: float):
        """
        Update internal sync statistics.
        
        Args:
            success_count: Number of successful records
            error_count: Number of failed records  
            sync_time_ms: Sync time in milliseconds
        """
        self.sync_stats['total_syncs'] += 1

        if success_count > 0:
            self.sync_stats['successful_syncs'] += 1
            self.sync_stats['records_synced'] += success_count

        if error_count > 0:
            self.sync_stats['failed_syncs'] += 1

        self.sync_stats['last_sync_time'] = time.time()

        # Track sync timing
        if sync_time_ms > 0:
            self.sync_stats['sync_times'].append(sync_time_ms)

            # Keep only last 50 sync times
            if len(self.sync_stats['sync_times']) > 50:
                self.sync_stats['sync_times'] = self.sync_stats['sync_times'][-50:]

            # Calculate average sync time
            self.sync_stats['avg_sync_time_ms'] = (
                sum(self.sync_stats['sync_times']) / len(self.sync_stats['sync_times'])
            )

    def get_sync_statistics(self) -> dict[str, Any]:
        """
        Get database sync statistics.
        
        Returns:
            dict: Comprehensive sync statistics
        """
        current_time = time.time()

        # Calculate success rate
        total_syncs = self.sync_stats['total_syncs']
        success_rate = (self.sync_stats['successful_syncs'] / total_syncs * 100) if total_syncs > 0 else 100

        return {
            'total_syncs': total_syncs,
            'successful_syncs': self.sync_stats['successful_syncs'],
            'failed_syncs': self.sync_stats['failed_syncs'],
            'success_rate': success_rate,
            'records_synced': self.sync_stats['records_synced'],
            'last_sync_ago': current_time - self.sync_stats['last_sync_time'],
            'avg_sync_time_ms': self.sync_stats['avg_sync_time_ms'],
            'flask_context_available': self.is_flask_context_available(),
            'recent_errors': self.last_sync_errors[-5:] if self.last_sync_errors else [],
            'error_count': len(self.last_sync_errors),
            'performance_health': {
                'sync_speed_good': self.sync_stats['avg_sync_time_ms'] < 100,  # <100ms target
                'success_rate_good': success_rate >= 95,  # >=95% target
                'recent_activity': (current_time - self.sync_stats['last_sync_time']) < 60  # <1min ago
            }
        }

    def get_health_status(self) -> str:
        """
        Get overall health status for database sync service.
        
        Returns:
            str: Health status ('healthy', 'degraded', 'error')
        """
        stats = self.get_sync_statistics()
        validation = self.validate_database_connection()

        # Check critical requirements
        if not validation['flask_context_available']:
            return 'error'

        if not validation['database_accessible']:
            return 'error'

        # Check performance metrics
        perf = stats['performance_health']
        if perf['sync_speed_good'] and perf['success_rate_good']:
            return 'healthy'
        if perf['success_rate_good']:
            return 'degraded'  # Slow but working
        return 'error'  # High failure rate

    def test_database_operations(self) -> dict[str, Any]:
        """
        Test database operations for debugging purposes.
        
        Returns:
            dict: Test results and diagnostics
        """
        if not self.is_flask_context_available():
            return {
                'success': False,
                'error': 'No Flask application context available'
            }

        try:
            from datetime import date

            from src.infrastructure.database import EventSession, db

            test_results = {
                'flask_context': True,
                'model_import': True,
                'connection_test': False,
                'table_exists': False,
                'insert_test': False,
                'query_test': False
            }

            # Test database connection
            try:
                result = db.session.execute(text("SELECT 1 as test")).fetchone()
                if result and result[0] == 1:
                    test_results['connection_test'] = True
            except Exception as e:
                test_results['connection_error'] = str(e)

            # Test table existence
            try:
                # Try to query the table
                count = EventSession.query.count()
                test_results['table_exists'] = True
                test_results['existing_records'] = count
            except Exception as e:
                test_results['table_error'] = str(e)

            # Test insert operation
            try:
                test_record = EventSession(
                    ticker='TEST_TICKER',
                    session_date=date.today(),
                    high_count=1,
                    low_count=1
                )

                db.session.add(test_record)
                db.session.flush()  # Don't commit yet

                test_results['insert_test'] = True
                test_results['test_record_id'] = test_record.id

                # Clean up test record
                db.session.delete(test_record)
                db.session.commit()

            except Exception as e:
                test_results['insert_error'] = str(e)
                try:
                    db.session.rollback()
                except:
                    pass

            # Test query operations
            try:
                recent_records = EventSession.query.filter(
                    EventSession.session_date == date.today()
                ).limit(5).all()

                test_results['query_test'] = True
                test_results['recent_records_count'] = len(recent_records)

            except Exception as e:
                test_results['query_error'] = str(e)

            return {
                'success': True,
                'test_results': test_results,
                'overall_health': all([
                    test_results['flask_context'],
                    test_results['model_import'],
                    test_results['connection_test'],
                    test_results['table_exists']
                ])
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Test operations failed: {str(e)}'
            }
