"""
Pattern Alert Manager
Manages user pattern subscriptions, alert preferences, and notification delivery.

Sprint 10 Phase 4: Pattern Alert System
- User pattern subscription management
- Alert preference configuration (notification types, thresholds)
- Real-time pattern notification delivery
- Alert history and performance tracking
"""

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import redis

from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of notifications users can receive."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    BROWSER = "browser"

class AlertThreshold(Enum):
    """Alert confidence threshold levels."""
    LOW = 0.3      # 30%+ confidence
    MEDIUM = 0.5   # 50%+ confidence
    HIGH = 0.7     # 70%+ confidence
    VERY_HIGH = 0.9  # 90%+ confidence

@dataclass
class PatternSubscription:
    """User's subscription to a specific pattern."""
    pattern: str
    enabled: bool
    confidence_threshold: float
    notification_types: set[NotificationType]
    symbols: set[str] | None = None  # If None, subscribe to all symbols
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'pattern': self.pattern,
            'enabled': self.enabled,
            'confidence_threshold': self.confidence_threshold,
            'notification_types': [nt.value for nt in self.notification_types],
            'symbols': list(self.symbols) if self.symbols else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PatternSubscription':
        """Create PatternSubscription from dictionary."""
        notification_types = set()
        for nt_value in data.get('notification_types', []):
            try:
                notification_types.add(NotificationType(nt_value))
            except ValueError:
                logger.warning(f"Unknown notification type: {nt_value}")

        symbols = set(data['symbols']) if data.get('symbols') else None

        return cls(
            pattern=data['pattern'],
            enabled=data['enabled'],
            confidence_threshold=data['confidence_threshold'],
            notification_types=notification_types,
            symbols=symbols,
            created_at=data.get('created_at', 0.0),
            updated_at=data.get('updated_at', 0.0)
        )

@dataclass
class UserAlertPreferences:
    """User's overall alert preferences."""
    user_id: str
    global_enabled: bool
    default_confidence_threshold: float
    default_notification_types: set[NotificationType]
    quiet_hours_start: str | None = None  # "22:00" format
    quiet_hours_end: str | None = None    # "08:00" format
    max_alerts_per_hour: int = 50
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'global_enabled': self.global_enabled,
            'default_confidence_threshold': self.default_confidence_threshold,
            'default_notification_types': [nt.value for nt in self.default_notification_types],
            'quiet_hours_start': self.quiet_hours_start,
            'quiet_hours_end': self.quiet_hours_end,
            'max_alerts_per_hour': self.max_alerts_per_hour,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'UserAlertPreferences':
        """Create UserAlertPreferences from dictionary."""
        notification_types = set()
        for nt_value in data.get('default_notification_types', []):
            try:
                notification_types.add(NotificationType(nt_value))
            except ValueError:
                logger.warning(f"Unknown notification type: {nt_value}")

        return cls(
            user_id=data['user_id'],
            global_enabled=data['global_enabled'],
            default_confidence_threshold=data['default_confidence_threshold'],
            default_notification_types=notification_types,
            quiet_hours_start=data.get('quiet_hours_start'),
            quiet_hours_end=data.get('quiet_hours_end'),
            max_alerts_per_hour=data.get('max_alerts_per_hour', 50),
            created_at=data.get('created_at', 0.0),
            updated_at=data.get('updated_at', 0.0)
        )

class PatternAlertManager:
    """
    Manages pattern alert subscriptions and notifications for TickStockAppV2.
    
    Handles user preferences, pattern filtering, alert delivery,
    and performance tracking for the pattern alert system.
    """

    def __init__(self, redis_client: redis.Redis, tickstock_db: TickStockDatabase | None = None):
        """Initialize pattern alert manager."""
        self.redis_client = redis_client
        self.tickstock_db = tickstock_db

        # Redis key prefix for all alert-related keys
        self.key_prefix = "tickstock:alerts:"

        # Redis key patterns
        self.user_prefs_key = "tickstock:alerts:prefs:{user_id}"
        self.user_subscriptions_key = "tickstock:alerts:subscriptions:{user_id}"
        self.alert_history_key = "tickstock:alerts:history:{user_id}"
        self.rate_limit_key = "tickstock:alerts:ratelimit:{user_id}:{hour}"

        # Available patterns (from Sprint 5-9)
        self.available_patterns = [
            'Doji', 'Hammer', 'ShootingStar', 'Engulfing', 'Harami',
            'MorningStar', 'EveningStar', 'ThreeWhiteSoldiers', 'ThreeBlackCrows',
            'PiercingLine', 'DarkCloudCover'
        ]

        # Statistics
        self.stats = {
            'alerts_sent': 0,
            'alerts_filtered': 0,
            'rate_limited': 0,
            'users_subscribed': 0,
            'start_time': time.time()
        }

        logger.info("PATTERN-ALERT-MANAGER: Initialized successfully")

    def get_user_preferences(self, user_id: str) -> UserAlertPreferences:
        """Get user's alert preferences."""
        try:
            prefs_key = self.user_prefs_key.format(user_id=user_id)
            prefs_data = self.redis_client.get(prefs_key)

            if prefs_data:
                prefs_dict = json.loads(prefs_data)
                return UserAlertPreferences.from_dict(prefs_dict)
            # Return default preferences
            return self._create_default_preferences(user_id)

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error getting preferences for {user_id}: {e}")
            return self._create_default_preferences(user_id)

    def _create_default_preferences(self, user_id: str) -> UserAlertPreferences:
        """Create default alert preferences for a user."""
        return UserAlertPreferences(
            user_id=user_id,
            global_enabled=True,
            default_confidence_threshold=AlertThreshold.MEDIUM.value,
            default_notification_types={NotificationType.IN_APP, NotificationType.BROWSER},
            max_alerts_per_hour=50,
            created_at=time.time(),
            updated_at=time.time()
        )

    def update_user_preferences(self, user_id: str, preferences: UserAlertPreferences) -> bool:
        """Update user's alert preferences."""
        try:
            preferences.updated_at = time.time()

            prefs_key = self.user_prefs_key.format(user_id=user_id)
            prefs_data = json.dumps(preferences.to_dict())

            # Store with 30-day TTL
            self.redis_client.setex(prefs_key, 86400 * 30, prefs_data)

            logger.info(f"PATTERN-ALERT-MANAGER: Updated preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error updating preferences: {e}")
            return False

    def get_user_subscriptions(self, user_id: str) -> dict[str, PatternSubscription]:
        """Get user's pattern subscriptions."""
        try:
            subs_key = self.user_subscriptions_key.format(user_id=user_id)
            subs_data = self.redis_client.get(subs_key)

            if subs_data:
                subs_dict = json.loads(subs_data)
                subscriptions = {}
                for pattern, sub_data in subs_dict.items():
                    subscriptions[pattern] = PatternSubscription.from_dict(sub_data)
                return subscriptions
            # Return default subscriptions
            return self._create_default_subscriptions(user_id)

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error getting subscriptions for {user_id}: {e}")
            return {}

    def _create_default_subscriptions(self, user_id: str) -> dict[str, PatternSubscription]:
        """Create default pattern subscriptions for a user."""
        default_prefs = self.get_user_preferences(user_id)
        subscriptions = {}

        # Create subscriptions for all available patterns
        for pattern in self.available_patterns:
            subscriptions[pattern] = PatternSubscription(
                pattern=pattern,
                enabled=True,
                confidence_threshold=default_prefs.default_confidence_threshold,
                notification_types=default_prefs.default_notification_types,
                symbols=None,  # Subscribe to all symbols by default
                created_at=time.time(),
                updated_at=time.time()
            )

        # Save default subscriptions
        self._save_user_subscriptions(user_id, subscriptions)
        return subscriptions

    def update_user_subscriptions(self, user_id: str,
                                 subscriptions: dict[str, PatternSubscription]) -> bool:
        """Update user's pattern subscriptions."""
        try:
            # Update timestamps
            for subscription in subscriptions.values():
                subscription.updated_at = time.time()

            return self._save_user_subscriptions(user_id, subscriptions)

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error updating subscriptions: {e}")
            return False

    def _save_user_subscriptions(self, user_id: str,
                               subscriptions: dict[str, PatternSubscription]) -> bool:
        """Save user subscriptions to Redis."""
        try:
            subs_key = self.user_subscriptions_key.format(user_id=user_id)
            subs_dict = {pattern: sub.to_dict() for pattern, sub in subscriptions.items()}
            subs_data = json.dumps(subs_dict)

            # Store with 30-day TTL
            self.redis_client.setex(subs_key, 86400 * 30, subs_data)

            logger.debug(f"PATTERN-ALERT-MANAGER: Saved subscriptions for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error saving subscriptions: {e}")
            return False

    def subscribe_to_pattern(self, user_id: str, pattern: str,
                           confidence_threshold: float = AlertThreshold.MEDIUM.value,
                           notification_types: set[NotificationType] = None,
                           symbols: set[str] = None) -> bool:
        """Subscribe user to a specific pattern."""
        try:
            if pattern not in self.available_patterns:
                logger.warning(f"PATTERN-ALERT-MANAGER: Unknown pattern: {pattern}")
                return False

            subscriptions = self.get_user_subscriptions(user_id)

            # Create or update subscription
            if not notification_types:
                prefs = self.get_user_preferences(user_id)
                notification_types = prefs.default_notification_types

            subscriptions[pattern] = PatternSubscription(
                pattern=pattern,
                enabled=True,
                confidence_threshold=confidence_threshold,
                notification_types=notification_types,
                symbols=symbols,
                created_at=subscriptions.get(pattern, PatternSubscription(pattern, False, 0.5, set())).created_at or time.time(),
                updated_at=time.time()
            )

            return self._save_user_subscriptions(user_id, subscriptions)

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error subscribing to pattern: {e}")
            return False

    def unsubscribe_from_pattern(self, user_id: str, pattern: str) -> bool:
        """Unsubscribe user from a specific pattern."""
        try:
            subscriptions = self.get_user_subscriptions(user_id)

            if pattern in subscriptions:
                subscriptions[pattern].enabled = False
                subscriptions[pattern].updated_at = time.time()
                return self._save_user_subscriptions(user_id, subscriptions)

            return True

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error unsubscribing from pattern: {e}")
            return False

    def should_alert_user(self, user_id: str, pattern: str, symbol: str,
                         confidence: float) -> tuple[bool, str]:
        """
        Check if user should receive alert for this pattern detection.
        
        Returns: (should_alert, reason)
        """
        try:
            # Check global preferences
            prefs = self.get_user_preferences(user_id)
            if not prefs.global_enabled:
                return False, "Global alerts disabled"

            # Check rate limiting
            if not self._check_rate_limit(user_id, prefs.max_alerts_per_hour):
                self.stats['rate_limited'] += 1
                return False, "Rate limit exceeded"

            # Check quiet hours
            if self._is_quiet_hours(prefs):
                return False, "Quiet hours active"

            # Check pattern subscription
            subscriptions = self.get_user_subscriptions(user_id)
            if pattern not in subscriptions:
                return False, "Pattern not subscribed"

            subscription = subscriptions[pattern]
            if not subscription.enabled:
                return False, "Pattern subscription disabled"

            # Check confidence threshold
            if confidence < subscription.confidence_threshold:
                self.stats['alerts_filtered'] += 1
                return False, f"Confidence {confidence:.2f} below threshold {subscription.confidence_threshold:.2f}"

            # Check symbol filtering
            if subscription.symbols and symbol not in subscription.symbols:
                return False, f"Symbol {symbol} not in subscription filter"

            return True, "Alert approved"

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error checking alert criteria: {e}")
            return False, "Error checking criteria"

    def _check_rate_limit(self, user_id: str, max_alerts_per_hour: int) -> bool:
        """Check if user is within rate limit for current hour."""
        try:
            current_hour = int(time.time() // 3600)
            rate_key = self.rate_limit_key.format(user_id=user_id, hour=current_hour)

            current_count = self.redis_client.get(rate_key)
            current_count = int(current_count) if current_count else 0

            if current_count >= max_alerts_per_hour:
                return False

            # Increment counter with 1-hour TTL
            pipe = self.redis_client.pipeline()
            pipe.incr(rate_key)
            pipe.expire(rate_key, 3600)
            pipe.execute()

            return True

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Rate limit check error: {e}")
            return True  # Allow on error to avoid blocking alerts

    def _is_quiet_hours(self, prefs: UserAlertPreferences) -> bool:
        """Check if current time is within user's quiet hours."""
        if not prefs.quiet_hours_start or not prefs.quiet_hours_end:
            return False

        try:
            from datetime import datetime
            from datetime import time as dt_time

            current_time = datetime.now().time()
            start_time = dt_time(*map(int, prefs.quiet_hours_start.split(':')))
            end_time = dt_time(*map(int, prefs.quiet_hours_end.split(':')))

            if start_time <= end_time:
                # Same day quiet hours (e.g., 14:00 to 18:00)
                return start_time <= current_time <= end_time
            # Overnight quiet hours (e.g., 22:00 to 08:00)
            return current_time >= start_time or current_time <= end_time

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Quiet hours check error: {e}")
            return False

    def get_pattern_performance(self, pattern: str | None = None) -> list[dict[str, Any]]:
        """Get pattern performance statistics from database."""
        try:
            if self.tickstock_db:
                return self.tickstock_db.get_pattern_performance(pattern)
            logger.warning("PATTERN-ALERT-MANAGER: No database connection for performance data")
            return []

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error getting pattern performance: {e}")
            return []

    def record_alert_delivery(self, user_id: str, pattern: str, symbol: str,
                            confidence: float, notification_types: list[str]):
        """Record successful alert delivery for tracking."""
        try:
            alert_record = {
                'pattern': pattern,
                'symbol': symbol,
                'confidence': confidence,
                'notification_types': notification_types,
                'timestamp': time.time()
            }

            history_key = self.alert_history_key.format(user_id=user_id)

            # Store in Redis list with 7-day TTL
            pipe = self.redis_client.pipeline()
            pipe.lpush(history_key, json.dumps(alert_record))
            pipe.ltrim(history_key, 0, 999)  # Keep last 1000 alerts
            pipe.expire(history_key, 86400 * 7)  # 7-day TTL
            pipe.execute()

            self.stats['alerts_sent'] += 1

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error recording alert delivery: {e}")

    def get_user_alert_history(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get user's recent alert history."""
        try:
            history_key = self.alert_history_key.format(user_id=user_id)
            alert_records = self.redis_client.lrange(history_key, 0, limit - 1)

            history = []
            for record_data in alert_records:
                try:
                    if isinstance(record_data, bytes):
                        record_data = record_data.decode('utf-8')
                    record = json.loads(record_data)
                    history.append(record)
                except Exception as parse_error:
                    logger.warning(f"PATTERN-ALERT-MANAGER: Error parsing alert record: {parse_error}")

            return history

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error getting alert history: {e}")
            return []

    def get_available_patterns(self) -> list[str]:
        """Get list of available patterns for subscription."""
        return self.available_patterns.copy()

    def get_subscribed_users_count(self) -> int:
        """Get count of users with active subscriptions."""
        try:
            # This is an approximation - in production you'd want a more efficient method
            pattern = self.user_subscriptions_key.format(user_id="*")
            keys = self.redis_client.keys(pattern)
            return len(keys)

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error getting subscribed users count: {e}")
            return 0

    def get_stats(self) -> dict[str, Any]:
        """Get alert manager statistics."""
        runtime = time.time() - self.stats['start_time']

        return {
            **self.stats,
            'runtime_seconds': round(runtime, 1),
            'alerts_per_hour': round(self.stats['alerts_sent'] / max(runtime / 3600, 1), 2),
            'filter_rate': round(
                self.stats['alerts_filtered'] / max(self.stats['alerts_filtered'] + self.stats['alerts_sent'], 1) * 100, 1
            ),
            'available_patterns': len(self.available_patterns),
            'subscribed_users': self.get_subscribed_users_count()
        }

    def cleanup_expired_data(self):
        """Clean up expired alert data and rate limiting keys."""
        try:
            # Redis TTL handles most cleanup, but we can do additional maintenance here
            logger.debug("PATTERN-ALERT-MANAGER: Cleanup completed")

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Cleanup error: {e}")

    def get_users_for_alert(self, pattern_name: str, symbol: str, confidence: float) -> list[str]:
        """
        Get list of user IDs who should receive this pattern alert.
        
        Args:
            pattern_name: Name of the detected pattern
            symbol: Stock symbol
            confidence: Pattern detection confidence (0-100)
            
        Returns:
            List of user IDs who should receive the alert
        """
        try:
            interested_users = []

            # Get all users who have subscriptions
            subscription_keys = self.redis_client.keys(f"{self.key_prefix}subscriptions:*")

            for key in subscription_keys:
                try:
                    user_id = key.split(':')[-1]  # Extract user_id from key

                    # Get user preferences
                    preferences = self.get_preferences(user_id)

                    # Check if user meets minimum confidence threshold
                    if confidence < preferences.get('confidence_threshold', 70):
                        continue

                    # Check quiet hours
                    if self._is_in_quiet_hours(preferences):
                        continue

                    # Check rate limiting
                    if not self._check_rate_limit(user_id, preferences):
                        continue

                    # Get user's subscriptions
                    subscriptions = self.get_subscriptions(user_id)

                    # Check if user is subscribed to this pattern
                    pattern_subscription = None
                    for sub in subscriptions:
                        if sub['pattern_name'] == pattern_name and sub.get('active', True):
                            pattern_subscription = sub
                            break

                    if not pattern_subscription:
                        continue

                    # Check pattern-specific confidence threshold
                    if confidence < pattern_subscription.get('confidence', 70):
                        continue

                    # Check symbol filtering
                    if pattern_subscription.get('symbols'):
                        if symbol not in pattern_subscription['symbols']:
                            continue

                    # User passes all filters
                    interested_users.append(user_id)

                except Exception as e:
                    logger.debug(f"PATTERN-ALERT-MANAGER: Skipping user {key}: {e}")
                    continue

            return interested_users

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error getting users for alert: {e}")
            return []

    def _is_in_quiet_hours(self, preferences: dict[str, Any]) -> bool:
        """Check if current time is within user's quiet hours."""
        quiet_hours = preferences.get('quiet_hours')
        if not quiet_hours:
            return False

        try:
            now = datetime.now()
            current_time = now.hour * 60 + now.minute

            start_time = self._time_to_minutes(quiet_hours.get('start', '22:00'))
            end_time = self._time_to_minutes(quiet_hours.get('end', '07:00'))

            if start_time > end_time:
                # Quiet hours cross midnight
                return current_time >= start_time or current_time <= end_time
            return start_time <= current_time <= end_time

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error checking quiet hours: {e}")
            return False

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM time string to minutes since midnight."""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        except Exception:
            return 0

    def _check_rate_limit(self, user_id: str, preferences: dict[str, Any]) -> bool:
        """Check if user is within their alert rate limit."""
        max_per_hour = preferences.get('max_alerts_per_hour', 20)
        if max_per_hour == -1:  # Unlimited
            return True

        try:
            # Get current hour's alert count
            current_hour = int(time.time() // 3600)  # Hour since epoch
            rate_limit_key = f"{self.key_prefix}rate_limit:{user_id}:{current_hour}"

            current_count = int(self.redis_client.get(rate_limit_key) or 0)

            if current_count >= max_per_hour:
                return False

            # Increment counter (with 2-hour TTL)
            pipe = self.redis_client.pipeline()
            pipe.incr(rate_limit_key)
            pipe.expire(rate_limit_key, 7200)  # 2 hours TTL
            pipe.execute()

            return True

        except Exception as e:
            logger.error(f"PATTERN-ALERT-MANAGER: Error checking rate limit: {e}")
            return True  # Allow on error
