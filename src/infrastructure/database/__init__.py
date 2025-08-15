"""
Database Package
Contains SQLAlchemy models and database-related utilities for TickStock.
"""

# Import database instance and models
from src.infrastructure.database.model import (
    db,
    AppSettings,
    BillingInfo,
    CacheEntry,
    CommunicationLog,
    EventSession,
    MarketAnalytics,
    PaymentHistory,
    Session,
    StockData,
    Subscription,
    TaggedStock,
    User,
    UserFilters,
    UserHistory,
    UserSettings,
    VerificationCode,
)

# Import migration utilities
from src.infrastructure.database.model_migrations_run import (
    run_migration_command,
)

__all__ = [
    # Database instance
    'db',
    
    # Models
    'AppSettings',
    'BillingInfo',
    'CacheEntry',
    'CommunicationLog',
    'EventSession',
    'MarketAnalytics',
    'PaymentHistory',
    'Session',
    'StockData',
    'Subscription',
    'TaggedStock',
    'User',
    'UserFilters',
    'UserHistory',
    'UserSettings',
    'VerificationCode',
    
    # Migration utilities
    'run_migration_command',
]
