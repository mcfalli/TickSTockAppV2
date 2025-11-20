import csv
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Unique session ID for log files
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]

class QueryDebugFilter(logging.Filter):
    """Simple filter for console output based on config flags."""

    def __init__(self, verbose=False, debug=False, connection_verbose=False):
        super().__init__()
        self.verbose = verbose
        self.debug = debug
        self.connection_verbose = connection_verbose

        # Patterns for connection-related loggers
        self.connection_patterns = [
            'massive_websocket_client', 'massive_data_provider',
            'synthetic_data_generator', 'simulated_data_provider',
            'websocket.massive_websocket_client', 'data_providers.massive.massive_data_provider',
            'data_providers.simulated.synthetic_data_generator', 'data_providers.simulated.simulated_data_provider',
            'core.massive_data_provider', 'core.simulated_data_provider'
        ]

    def filter(self, record):
        # Always show errors and warnings
        if record.levelno >= logging.WARNING:
            return True

        # INFO level: show if verbose or if connection-related and connection_verbose
        if record.levelno == logging.INFO:
            if self.verbose:
                return True
            if self.connection_verbose and self._is_connection_logger(record.name):
                return True
            return False

        # DEBUG level: show if debug or if connection-related and connection_verbose
        if record.levelno == logging.DEBUG:
            if self.debug:
                return True
            if self.connection_verbose and self._is_connection_logger(record.name):
                return True
            return False

        return False

    def _is_connection_logger(self, logger_name: str) -> bool:
        logger_name_lower = logger_name.lower()
        return any(pattern in logger_name_lower for pattern in self.connection_patterns)

def configure_logging(config):
    """Configure simple logging with one file and filtered console."""
    # Extract config flags
    console_verbose = config.get('LOG_CONSOLE_VERBOSE', False)
    console_debug = config.get('LOG_CONSOLE_DEBUG', False)
    console_connection_verbose = config.get('LOG_CONSOLE_CONNECTION_VERBOSE', True)
    file_enabled = config.get('LOG_FILE_ENABLED', True)

    # Set root logger to DEBUG (capture everything)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler (filtered)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    console_filter = QueryDebugFilter(
        verbose=console_verbose,
        debug=console_debug,
        connection_verbose=console_connection_verbose
    )
    console_handler.addFilter(console_filter)
    root_logger.addHandler(console_handler)

    # Single file handler (all records if enabled)
    if file_enabled:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"tickstock_{SESSION_ID}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        root_logger.info(f"Log file enabled: {log_file}")

    # Suppress third-party loggers unless debug
    for name in ['urllib3', 'socketio', 'engineio', 'eventlet', 'werkzeug', 'websocket']:
        logging.getLogger(name).setLevel(logging.WARNING if not console_debug else logging.DEBUG)

    root_logger.info(f"Logging configured - Session: {SESSION_ID}")
    root_logger.info(f"Console: Verbose={console_verbose}, Debug={console_debug}, Connection={console_connection_verbose}")
    root_logger.info(f"File: Enabled={file_enabled}")

    return console_filter

def get_session_id():
    """Return the unique session ID."""
    return SESSION_ID

def write_debug_csv(file_path: str | Path, headers: list[str], data: list[Any]):
    """Write to CSV with session ID in filename."""
    try:
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        base_dir = file_path.parent
        filename_parts = file_path.name.split('.')
        base_name = filename_parts[0]
        ext = filename_parts[1] if len(filename_parts) > 1 else 'csv'
        new_filename = f"{base_name}_{SESSION_ID}.{ext}"
        file_path = base_dir / new_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = file_path.exists()
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(data)
    except Exception as e:
        logger.error(f"Failed to write CSV to {file_path}: {e}")
