"""Development Environment Configuration"""

DEBUG = True
TESTING = False
LOG_LEVEL = "DEBUG"

# Database
DATABASE_URI = "postgresql://localhost/tickstock_dev"

# Redis
REDIS_URL = "redis://localhost:6379/0"

# API Keys (use .env for actual values)
POLYGON_API_KEY = None  # Set in .env

# WebSocket
WS_HEARTBEAT_INTERVAL = 30
WS_RECONNECT_DELAY = 5

# Processing
WORKER_POOL_MIN = 2
WORKER_POOL_MAX = 8
