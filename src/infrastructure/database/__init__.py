"""
Database Package
Contains SQLAlchemy models and database-related utilities for TickStock.
"""

# Import database instance and models
# Import migration utilities
from src.infrastructure.database.migrations.run_migrations import (
    run_migration_command,
)
from src.infrastructure.database.models.base import (
    AppSettings,
    BillingInfo,
    CacheEntry,
    CommunicationLog,
    PaymentHistory,
    Session,
    Subscription,
    TaggedStock,
    User,
    UserFilters,
    UserHistory,
    UserSettings,
    VerificationCode,
    db,
)

# Analytics models removed during Phase 2 cleanup
# OHLCV persistence removed during Sprint 42 Phase 2 (moved to TickStockPL)

__all__ = [
    # Database instance
    'db',

    # Models
    'AppSettings',
    'BillingInfo',
    'CacheEntry',
    'CommunicationLog',
    'PaymentHistory',
    'Session',
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
