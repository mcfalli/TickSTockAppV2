"""
TickStock V2 - Main Application Package

This is the root package for the TickStock V2 application.
"""

# Define what should be exposed at the package level
__all__ = [
    'app',
    'startup',
]

# Version info
__version__ = '2.0.0'
__author__ = 'TickStock Team'

# Import main application entry point for convenience
try:
    from . import app
except ImportError:
    pass  # App module may not be available in all contexts

# Import startup module if it exists
try:
    from . import startup
except ImportError:
    pass  # Startup module is optional
