"""Business Services

Import service classes individually as needed:
    from src.core.services.market_data_service import MarketDataService
    from src.core.services.session_manager import SessionManager
    etc.
"""

# Only import the most commonly used services
try:
    from .market_data_service import MarketDataService
except ImportError:
    MarketDataService = None
    
try:
    from .session_manager import SessionManager  
except ImportError:
    SessionManager = None

try:
    from .config_manager import ConfigManager
except ImportError:
    ConfigManager = None

# Export what was successfully imported
__all__ = [
    name for name in ['MarketDataService', 'SessionManager', 'ConfigManager']
    if globals().get(name) is not None
]
