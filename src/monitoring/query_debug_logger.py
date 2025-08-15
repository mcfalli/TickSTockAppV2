"""
Enhanced logging module with query parameter-based debug control.
This allows enabling debug logs only when the '?debug' query parameter is present.
"""

import logging
import threading
from flask import request, has_request_context
from functools import wraps

# Thread local storage to track debug state
_debug_local = threading.local()
_debug_local.enabled = False

class QueryDebugFilter(logging.Filter):
    """
    Logging filter that only allows debug messages when debug mode is enabled via query param.
    """
    def filter(self, record):
        # Always allow INFO and above
        if record.levelno >= logging.INFO:
            return True
            
        # For DEBUG level, only allow if debug is enabled
        return getattr(_debug_local, 'enabled', False)

def configure_query_debug_logging():
    """
    Configure the application's loggers to use the query debug filter.
    Call this after the Flask app and basic logging are initialized.
    """
    # Create our special filter
    debug_filter = QueryDebugFilter()
    
    # Add the filter to the root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(debug_filter)
    
    # Add it to our application loggers as well
    app_logger = logging.getLogger('app')
    app_logger.addFilter(debug_filter)
    
    # May need to add to other specific loggers if they have direct handlers
    for name in ['data_processor', 'highlow_detector', 'polygon_data_provider', 'utils']:
        logger = logging.getLogger(name)
        logger.addFilter(debug_filter)
    
    logging.info("Query parameter debug logging configured")

def check_debug_query_param():
    """
    Check if the debug query parameter is present in the current request.
    Sets the thread-local debug state accordingly.
    """
    if has_request_context():
        _debug_local.enabled = 'debug' in request.args
        if _debug_local.enabled:
            logging.info("Debug logging enabled via query parameter")

def query_debug_middleware(app):
    """
    Flask middleware to check for debug query parameter on each request.
    """
    @app.before_request
    def before_request():
        check_debug_query_param()
    
    @app.after_request
    def after_request(response):
        # Reset debug state after request completes
        _debug_local.enabled = False
        return response
    
    return app

# Decorator for functions that need query debug checking (like WebSocket handlers)
def with_query_debug(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Extract and check for debug parameter in arguments
        # For SocketIO events, check data parameter which contains connection info
        if args and isinstance(args[0], dict) and 'query' in args[0]:
            _debug_local.enabled = 'debug' in args[0]['query']
        
        return f(*args, **kwargs)
    return decorated