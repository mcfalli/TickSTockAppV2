"""
Database Package
Contains SQLAlchemy models and database-related utilities for TickStock.
"""

# Import database instance and models
from src.infrastructure.database.models.base import (
    db,
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
)

# Import migration utilities
from src.infrastructure.database.migrations.run_migrations import (
    run_migration_command,
)
# Analytics models removed during Phase 2 cleanup

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
