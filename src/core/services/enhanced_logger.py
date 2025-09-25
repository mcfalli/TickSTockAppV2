"""Sprint 32: Enhanced Logger with File and Database Capabilities

This module implements the enhanced logging system that extends the existing
Python logging with file rotation and database storage based on severity thresholds.

Created: 2025-09-25
Purpose: Unified error handling with configurable file and database logging
Architecture: Config-driven via .env, <100ms processing time, zero performance impact
"""

import logging
import os
import json
import traceback as tb
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path

from src.core.models.error_models import ErrorMessage, SEVERITY_LEVELS
from src.core.services.config_manager import LoggingConfig


class EnhancedLogger:
    """Enhanced logger with file and database capabilities

    This class enhances the standard Python logging system with:
    - Configurable file logging with rotation
    - Database storage based on severity thresholds
    - Consistent error formatting across systems
    - High-performance <100ms processing
    """

    def __init__(self, config: LoggingConfig = None, db_connection=None):
        """Initialize enhanced logger

        Args:
            config: LoggingConfig instance with settings
            db_connection: Database connection for error storage
        """
        self.config = config or LoggingConfig()
        self.db = db_connection
        self.logger = logging.getLogger(f'{__name__}.enhanced')

        # Ensure logger level allows all severity levels
        self.logger.setLevel(logging.DEBUG)

        # Setup file handler if enabled
        if self.config.log_file_enabled:
            self._setup_file_handler()

        # Performance tracking
        self._error_count = 0
        self._db_writes = 0

    def _setup_file_handler(self):
        """Configure rotating file handler for error logging"""
        try:
            # Create logs directory if it doesn't exist
            log_dir = Path(self.config.log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            # Create rotating file handler
            handler = RotatingFileHandler(
                filename=self.config.log_file_path,
                maxBytes=self.config.log_file_max_size,
                backupCount=self.config.log_file_backup_count,
                encoding='utf-8'  # Handle Unicode characters properly
            )

            # Set formatter for consistent log format
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)

            # Add handler to logger
            self.logger.addHandler(handler)

            self.logger.info("Enhanced logger file handler initialized")

        except Exception as e:
            # Log setup error but don't fail initialization
            logging.getLogger(__name__).error(f"Failed to setup file handler: {e}")

    def log_error(
        self,
        severity: str,
        message: str,
        category: Optional[str] = None,
        component: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        traceback: Optional[str] = None,
        source: str = 'TickStockAppV2'
    ):
        """Log error with optional database storage

        Args:
            severity: Error severity level (critical|error|warning|info|debug)
            message: Human-readable error message
            category: Error category for grouping
            component: Component that generated the error
            context: Additional context data
            traceback: Stack trace string
            source: Source system name
        """
        try:
            self._error_count += 1

            # Create ErrorMessage object
            error_msg = ErrorMessage.create(
                source=source,
                severity=severity,
                message=message,
                category=category,
                component=component,
                traceback=traceback,
                context=context
            )

            # Always log to standard logger
            self._log_to_standard_logger(error_msg)

            # Check if should store in database
            if self._should_store_in_db(severity):
                self._store_in_database(error_msg)

        except Exception as e:
            # Fallback logging to prevent error handling from failing
            fallback_logger = logging.getLogger(__name__)
            fallback_logger.error(f"Enhanced logger error: {e}")

    def _log_to_standard_logger(self, error_msg: ErrorMessage):
        """Log error message to standard Python logger

        Args:
            error_msg: ErrorMessage instance to log
        """
        # Map severity to logging level
        level = SEVERITY_LEVELS.get(error_msg.severity, 20)  # Default to INFO

        # Format message with context
        log_message = error_msg.get_display_message()
        if error_msg.context:
            log_message += f" | Context: {json.dumps(error_msg.context, default=str)}"

        # Log with appropriate level
        self.logger.log(level, log_message, extra={
            'error_id': error_msg.error_id,
            'source': error_msg.source,
            'category': error_msg.category,
            'component': error_msg.component
        })

    def _should_store_in_db(self, severity: str) -> bool:
        """Check if severity meets threshold for database storage

        Args:
            severity: Error severity level

        Returns:
            bool: True if should store in database
        """
        if not self.config.log_db_enabled or not self.db:
            return False

        threshold_level = SEVERITY_LEVELS.get(
            self.config.log_db_severity_threshold, 40  # Default to 'error'
        )
        current_level = SEVERITY_LEVELS.get(severity, 0)

        return current_level >= threshold_level

    def _store_in_database(self, error_msg: ErrorMessage):
        """Store error in database

        Args:
            error_msg: ErrorMessage instance to store
        """
        try:
            query = """
                INSERT INTO error_logs
                (error_id, source, severity, category, message,
                 component, traceback, context, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Prepare values using the model's database dictionary
            db_dict = error_msg.to_database_dict()
            values = (
                db_dict['error_id'],
                db_dict['source'],
                db_dict['severity'],
                db_dict['category'],
                db_dict['message'],
                db_dict['component'],
                db_dict['traceback'],
                json.dumps(db_dict['context'], default=str) if db_dict['context'] else None,
                db_dict['timestamp']
            )

            # Execute database insert
            if hasattr(self.db, 'get_connection'):
                # Connection pool pattern
                with self.db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query, values)
                        conn.commit()
            else:
                # Direct connection pattern
                with self.db.cursor() as cursor:
                    cursor.execute(query, values)
                    self.db.commit()

            self._db_writes += 1

        except Exception as e:
            # Log database error but don't fail the application
            self.logger.error(f"Failed to store error in database: {e}")

    def log_from_exception(
        self,
        exception: Exception,
        severity: str = 'error',
        category: Optional[str] = None,
        component: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: bool = True
    ):
        """Log error from an exception object

        Args:
            exception: Exception instance
            severity: Error severity level
            category: Error category
            component: Component name
            context: Additional context
            include_traceback: Whether to include stack trace
        """
        traceback_str = None
        if include_traceback:
            traceback_str = tb.format_exc()

        self.log_error(
            severity=severity,
            message=str(exception),
            category=category,
            component=component,
            context=context,
            traceback=traceback_str
        )

    def log_from_redis_message(self, redis_message: Union[str, bytes]):
        """Log error message received from Redis

        Args:
            redis_message: JSON string or bytes from Redis channel
        """
        try:
            # Handle bytes from Redis
            if isinstance(redis_message, bytes):
                redis_message = redis_message.decode('utf-8')

            # Parse ErrorMessage from JSON
            error_msg = ErrorMessage.from_json(redis_message)

            # Log using standard method (will handle file and DB)
            self.log_error(
                severity=error_msg.severity,
                message=f"[{error_msg.source}] {error_msg.message}",
                category=error_msg.category,
                component=error_msg.component,
                context=error_msg.context,
                traceback=error_msg.traceback,
                source=error_msg.source  # Preserve original source
            )

        except Exception as e:
            self.logger.error(f"Failed to process Redis error message: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics

        Returns:
            Dict: Statistics about error logging
        """
        return {
            'total_errors': self._error_count,
            'database_writes': self._db_writes,
            'file_logging_enabled': self.config.log_file_enabled,
            'database_logging_enabled': self.config.log_db_enabled,
            'database_threshold': self.config.log_db_severity_threshold
        }

    def test_logging(self):
        """Test all logging components with sample errors"""
        test_severities = ['debug', 'info', 'warning', 'error', 'critical']

        self.logger.info("Starting enhanced logger test...")

        for severity in test_severities:
            self.log_error(
                severity=severity,
                message=f"Test {severity} message for enhanced logger",
                category='test',
                component='EnhancedLoggerTest',
                context={'test': True, 'severity': severity}
            )

        stats = self.get_stats()
        self.logger.info(f"Enhanced logger test completed. Stats: {stats}")
        return stats


def create_enhanced_logger(
    config: Optional[LoggingConfig] = None,
    db_connection=None
) -> EnhancedLogger:
    """Factory function to create enhanced logger

    Args:
        config: Optional LoggingConfig instance
        db_connection: Optional database connection

    Returns:
        EnhancedLogger: Configured enhanced logger instance
    """
    if config is None:
        config = LoggingConfig()

    return EnhancedLogger(config=config, db_connection=db_connection)


# Global enhanced logger instance (will be initialized by app.py)
enhanced_logger: Optional[EnhancedLogger] = None


def get_enhanced_logger() -> Optional[EnhancedLogger]:
    """Get the global enhanced logger instance

    Returns:
        EnhancedLogger: Global enhanced logger or None if not initialized
    """
    return enhanced_logger


def set_enhanced_logger(logger: EnhancedLogger):
    """Set the global enhanced logger instance

    Args:
        logger: EnhancedLogger instance to set as global
    """
    global enhanced_logger
    enhanced_logger = logger