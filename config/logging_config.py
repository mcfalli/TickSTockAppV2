import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import threading
import csv
import uuid
from typing import List, Any, Union, Dict
from enum import Enum

logger = logging.getLogger(__name__)

# Add session ID
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]

class LogDomain(Enum):
    """Define logging domains for targeted file output"""
    CORE = "core"  # Default - includes all data processing, transport, events, monitoring, etc.
    AUTH_SESSION = "auth_session"  # Authentication and session management only
    USER_SETTINGS = "user_settings"  # User preferences and settings only
    UNIVERSE_TRACKING = "universe_tracking"  # Universe selection and filtering only

# Enhanced logging patterns for migration
MIGRATION_LOG_PATTERNS = {
    'migration_validation': r'🔄 MIGRATION_VALIDATION.*',
    'migration_performance': r'🔄 MIGRATION_PERF.*',
    'migration_status': r'🔄 MIGRATION_STATUS.*',
    'migration_error': r'🚨 MIGRATION_ERROR.*',
    'migration_warning': r'⚠️ MIGRATION_WARNING.*'
}

class DomainLogFilter(logging.Filter):
    """Filter logs to specific domains based on logger name and message patterns"""
    
    def __init__(self, domain: LogDomain, production_mode: bool = False):
        super().__init__()
        self.domain = domain
        self.production_mode = production_mode
        self._thread_local = threading.local()
        
        # Define logger name patterns for each domain
        self.domain_patterns = {
            LogDomain.CORE: [
                # This is now the default - we don't need to list everything
                # Only exclude patterns will be checked
            ],
            LogDomain.AUTH_SESSION: [
                'auth', 'authentication', 'registration', 'session', 
                'email_manager', 'sms_manager', 'app_routes_auth'
            ],
            LogDomain.USER_SETTINGS: [
                'user_settings', 'app_routes_main', 'app_forms'
            ],
            LogDomain.UNIVERSE_TRACKING: [
                'user_settings_service', 'cache_control', 'universe_tracker', 
                'subscription_manager', 'filtering_manager'
            ]
        }
        
        # Define message patterns for domain classification
        self.message_patterns = {
            LogDomain.CORE: [
                # Everything is CORE by default, no need to list patterns
            ],
            LogDomain.AUTH_SESSION: [
                'login', 'logout', 'register', 'authentication', 'session', 
                'password', 'email', 'phone', 'billing', 'subscription', 
                '2fa', 'verification'
            ],
            LogDomain.USER_SETTINGS: [
                'settings', 'preference', 'selection'
            ],
            LogDomain.UNIVERSE_TRACKING: [
                'universe selections', 'filtering', 'subscription vs processing', 
                'universe membership', 'filter rate', 'filtering stats',
                'processed vs dropped', 'subscription overlap', 'universe coverage', 
                'processing stats', 'user universe', 'stock filtering',
                'frontend_filtering', 'filter_efficiency'
            ]
        }
    
    def filter(self, record):
        # Always allow errors and warnings in production
        if self.production_mode and record.levelno >= logging.WARNING:
            return self._matches_domain(record)
        
        # Allow migration status logs in production for visibility
        if self.production_mode and self.domain == LogDomain.CORE:
            message = record.getMessage().lower()
            if any(pattern.lower() in message for pattern in MIGRATION_LOG_PATTERNS.values()):
                return self._matches_domain(record)
        
        # In debug mode, check domain match and level
        if not self.production_mode:
            return self._matches_domain(record)
        
        # Production mode: only errors/warnings for this domain
        return record.levelno >= logging.WARNING and self._matches_domain(record)
    
    def _matches_domain(self, record) -> bool:
        """Check if log record matches this domain"""
        logger_name = record.name.lower()
        message = record.getMessage().lower()
        
        # Check for explicit domain prefixes (highest priority)
        if logger_name.startswith(f"{self.domain.value}."):
            return True
        
        # For CORE domain, it's the default - accept everything except what belongs to other domains
        if self.domain == LogDomain.CORE:
            # Check if this belongs to any other domain
            for other_domain in [LogDomain.AUTH_SESSION, LogDomain.USER_SETTINGS, LogDomain.UNIVERSE_TRACKING]:
                if other_domain == LogDomain.CORE:
                    continue
                    
                # Check logger patterns
                for pattern in self.domain_patterns.get(other_domain, []):
                    if pattern in logger_name:
                        return False
                
                # Check message patterns
                for pattern in self.message_patterns.get(other_domain, []):
                    if pattern in message:
                        # Special case: 'session' in event detection should stay in CORE
                        if other_domain == LogDomain.AUTH_SESSION:
                            if 'event detected' in message or 'session_high' in message or 'session_low' in message:
                                continue
                        # Special case: 'settings' without 'universe' should go to USER_SETTINGS
                        if other_domain == LogDomain.USER_SETTINGS:
                            if 'universe' in message:
                                continue
                        return False
            
            # If not claimed by other domains, it belongs to CORE
            return True
        
        # For AUTH_SESSION
        if self.domain == LogDomain.AUTH_SESSION:
            # Check logger patterns
            for pattern in self.domain_patterns[LogDomain.AUTH_SESSION]:
                if pattern in logger_name:
                    return True
            
            # Check message patterns but exclude event detection
            if 'event detected' not in message and 'session_high' not in message and 'session_low' not in message:
                for pattern in self.message_patterns[LogDomain.AUTH_SESSION]:
                    if pattern in message:
                        return True
        
        # For USER_SETTINGS
        if self.domain == LogDomain.USER_SETTINGS:
            # Check logger patterns
            for pattern in self.domain_patterns[LogDomain.USER_SETTINGS]:
                if pattern in logger_name:
                    return True
            
            # Check message patterns but only for non-universe settings
            if 'universe' not in message:
                for pattern in self.message_patterns[LogDomain.USER_SETTINGS]:
                    if pattern in message:
                        return True
        
        # For UNIVERSE_TRACKING
        if self.domain == LogDomain.UNIVERSE_TRACKING:
            # Check logger patterns
            for pattern in self.domain_patterns[LogDomain.UNIVERSE_TRACKING]:
                if pattern in logger_name:
                    return True
            
            # Check message patterns
            for pattern in self.message_patterns[LogDomain.UNIVERSE_TRACKING]:
                if pattern in message:
                    return True
        
        return False

class QueryDebugFilter(logging.Filter):
    """Enhanced filter for console output with query param debug override"""
    
    def __init__(self, verbose=False, debug=False, connection_verbose=False):
        super().__init__()
        self._thread_local = threading.local()
        self._verbose = verbose
        self._debug = debug
        self._connection_verbose = connection_verbose
        
        # Define connection-related logger patterns (not just exact names)
        self.connection_logger_patterns = [
            'polygon_websocket_client',
            'websocket.polygon_websocket_client',  # New structure
            'polygon_data_provider',
            'data_providers.polygon.polygon_data_provider',  # New structure
            'synthetic_data_generator',
            'data_providers.simulated.synthetic_data_generator',  # New structure
            'simulated_data_provider',
            'data_providers.simulated.simulated_data_provider',  # New structure
            'core.polygon_data_provider',
            'core.simulated_data_provider'
        ]
    
    def filter(self, record):
        # Query param debug override
        enabled = getattr(self._thread_local, 'enabled', False)
        if enabled and self._debug:
            return True
            
        # Always log errors and warnings
        if record.levelno >= logging.ERROR:
            return True
        if record.levelno == logging.WARNING:
            return True
            
        # INFO logs
        if record.levelno == logging.INFO:
            if self._verbose:
                return True
                
            # Check if this is a connection-related logger
            if self._connection_verbose and self._is_connection_logger(record.name):
                return True
            return False
            
        # DEBUG logs
        if record.levelno == logging.DEBUG:
            if self._debug:
                return True

            # Check if this is a connection-related logger
            if self._connection_verbose and self._is_connection_logger(record.name):
                return True
            return False
            
        return False
    
    def _is_connection_logger(self, logger_name):
        """Check if logger name matches any connection logger pattern"""
        logger_name_lower = logger_name.lower()
        
        # Check exact matches first
        if logger_name in self.connection_logger_patterns:
            return True
        
        # Check if logger name contains key patterns (for hierarchical loggers)
        connection_keywords = [
            'polygon_websocket_client',
            'polygon_data_provider', 
            'simulated_data_provider',
            'synthetic_data_generator'
        ]
        
        for keyword in connection_keywords:
            if keyword in logger_name_lower:
                return True
                
        return False
    
    def set_enabled(self, enabled):
        self._thread_local.enabled = enabled
    
    '''
    def update_settings(self, verbose, debug, connection_verbose):
        self._verbose = verbose
        self._debug = debug
        self._connection_verbose = connection_verbose
    '''
    
class LoggingManager:
    """Central logging management for domain-specific file outputs"""
    
    def __init__(self):
        self.domain_filters = {}
        self.file_handlers = {}
        self.console_filter = None
    
    def configure_logging(self, config):
        """Configure enhanced logging with domain-specific files"""
        # Use clear parameter names
        console_verbose = config.get('LOG_CONSOLE_VERBOSE', False)
        console_debug = config.get('LOG_CONSOLE_DEBUG', False)
        console_connection_verbose = config.get('LOG_CONSOLE_CONNECTION_VERBOSE', True)
        file_enabled = config.get('LOG_FILE_ENABLED', True)
        file_production_mode = config.get('LOG_FILE_PRODUCTION_MODE', False)
        
        # Clear existing configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Standard formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        
        self.console_filter = QueryDebugFilter(
            verbose=console_verbose, 
            debug=console_debug, 
            connection_verbose=console_connection_verbose
        )
        console_handler.addFilter(self.console_filter)
        root_logger.addHandler(console_handler)
        
        # Domain-specific file handlers
        if file_enabled:
            self._setup_domain_handlers(formatter, file_production_mode)
        
        # Configure third-party loggers
        self._configure_third_party_loggers(console_debug, console_handler)
        
        # Configure module loggers
        self._configure_module_loggers()
        
        root_logger.info(f"Enhanced logging configured - Session: {SESSION_ID}")
        root_logger.info(f"Console: Verbose={console_verbose}, Debug={console_debug}, Connection={console_connection_verbose}")
        root_logger.info(f"Files: Enabled={file_enabled}, Production={file_production_mode}")
        
        return self.console_filter
    
    def _setup_domain_handlers(self, formatter, production_mode):
        """Create file handlers for each logging domain"""
        log_dir = Path("logs")
        
        try:
            log_dir.mkdir(exist_ok=True)
            
            for domain in LogDomain:
                # Create domain-specific log file
                log_file = log_dir / f"{domain.value}_{SESSION_ID}.log"
                
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                
                # Add domain filter
                domain_filter = DomainLogFilter(domain, production_mode)
                file_handler.addFilter(domain_filter)
                
                # Add to root logger
                root_logger = logging.getLogger()
                root_logger.addHandler(file_handler)
                
                # Store references
                self.domain_filters[domain] = domain_filter
                self.file_handlers[domain] = file_handler
                
                logging.getLogger().info(f"Domain log enabled: {domain.value} -> {log_file}")
                
        except Exception as e:
            logging.getLogger().warning(f"Failed to set up domain file logging: {e}")
    
    def _configure_third_party_loggers(self, debug, console_handler):
        """Configure third-party library loggers"""
        # Suppress urllib3 unless debug
        logging.getLogger('urllib3').setLevel(logging.WARNING if not debug else logging.DEBUG)
        
        # Manage socketio, engineio, etc.
        for name in ['socketio', 'engineio', 'eventlet', 'werkzeug', 'websocket']:
            ext_logger = logging.getLogger(name)
            ext_logger.setLevel(logging.DEBUG)
            ext_logger.handlers.clear()
            ext_logger.addHandler(console_handler)
    
    def _configure_module_loggers(self):
        """Set appropriate levels for application modules"""
        modules = [
            # Core modules (everything else goes here by default)
            'market_data_service', 'data_provider', 'highlow_detector',
            'websocket_manager', 'synthetic_data_generator', 
            'buysell_market_tracker', 'websocket_publisher', 
            'event_processor', 'event_manager', 'surge_detector', 
            'trend_detector', 'metrics_tracker', 'marekt_metrics',
            # Monitoring modules also go to CORE
            'monitoring', 'health_check', 'performance_monitor',
            'resource_monitor', 'system_monitor', 'metrics_collector',
            # Auth modules
            'auth.authentication', 'auth.registration',
            # User settings modules
            'user_settings', 'app_routes_main', 'app_forms',
            # Universe tracking modules
            'user_settings_service', 'cache_control', 'universe_tracker'
        ]
        
        for module in modules:
            logger = logging.getLogger(module)
            logger.setLevel(logging.DEBUG)
    
    def get_domain_logger(self, domain: LogDomain, name: str = None):
        """Get a logger configured for a specific domain"""
        logger_name = f"{domain.value}.{name}" if name else domain.value
        return logging.getLogger(logger_name)

# Global logging manager instance
logging_manager = LoggingManager()

def configure_logging(config):
    """Main entry point for logging configuration"""
    return logging_manager.configure_logging(config)

def get_session_id():
    """Return the unique session ID for this run."""
    return SESSION_ID

def get_domain_logger(domain: LogDomain, name: str = None):
    """Helper to get domain-specific loggers"""
    return logging_manager.get_domain_logger(domain, name)

def get_migration_logger(component_name: str) -> logging.Logger:
    """Get logger specifically for migration validation.
    
    Args:
        component_name: Name of the migration component (e.g., 'schema', 'data_validation').
    
    Returns:
        A logger instance configured for the CORE domain with migration prefix.
    
    Raises:
        ValueError: If component_name is empty or contains invalid characters.
    """
    if not component_name or not component_name.strip():
        raise ValueError("component_name cannot be empty")
    if any(char in component_name for char in '<>:"/\\|?*'):
        raise ValueError("component_name contains invalid characters")
    
    return get_domain_logger(LogDomain.CORE, f'migration_{component_name.strip().lower()}')

def write_debug_csv(file_path: Union[str, Path], headers: List[str], data: List[Any]):
    """Enhanced CSV debug writer with session ID"""
    try:
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        
        base_dir = file_path.parent
        filename = file_path.name
        
        filename_parts = filename.split('.')
        if len(filename_parts) > 1:
            new_filename = f"{filename_parts[0]}_{SESSION_ID}.{filename_parts[1]}"
        else:
            new_filename = f"{filename}_{SESSION_ID}"
        
        file_path = base_dir / new_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_exists = file_path.exists()
        
        # ADD encoding='utf-8' HERE to handle Unicode characters
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(data)
            
    except Exception as e:
        logger.error(f"Failed to write to {file_path}: {e}")