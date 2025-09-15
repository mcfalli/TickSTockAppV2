"""Production Environment Configuration"""

DEBUG = False
TESTING = False
LOG_LEVEL = "INFO"

# Database
DATABASE_URI = None  # Set via environment variable

# Redis
REDIS_URL = None  # Set via environment variable

# API Keys
POLYGON_API_KEY = None  # Set via environment variable

# WebSocket
WS_HEARTBEAT_INTERVAL = 60
WS_RECONNECT_DELAY = 10

# Processing
WORKER_POOL_MIN = 4
WORKER_POOL_MAX = 16

# OHLCV Database Persistence Settings
DB_BATCH_SIZE = 100  # Larger batches for production efficiency
DB_FLUSH_INTERVAL = 5.0  # Flush every 5 seconds in production
