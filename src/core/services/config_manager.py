import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from dotenv import find_dotenv, load_dotenv

logger = logging.getLogger(__name__)

# Global instance for get_config() compatibility function
_global_config_manager = None


def get_config():
    """
    Get the configuration using a global ConfigManager instance.
    Provides backward compatibility with the old config.py get_config() function.

    Returns:
        dict: The configuration dictionary
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
        _global_config_manager.load_from_env()
    return _global_config_manager.get_config()


class ConfigManager:
    """Centralized configuration management with validation."""

    COLLECTION_INTERVAL = 0.5  # DataPublisher collection rate
    EMISSION_INTERVAL = 1.0  # WebSocketPublisher emission rate
    UPDATE_INTERVAL = 0.5  # Already used by DataPublisher

    # Core Processing Parameters
    # (Removed legacy surge detection constants)

    # Default configuration values
    DEFAULTS = {
        "APP_VERSION": "",
        "DATABASE_URI": "postgresql://app_readwrite:OLD_PASSWORD_LEGACY@localhost/marketpulse",
        "DATABASE_SYNCH_AGGREGATE_SECONDS": 30,  # Seconds
        "APP_ENVIRONMENT": "development",
        "APP_DEBUG": False,
        "APP_HOST": "0.0.0.0",
        "APP_PORT": 5000,
        "MARKET_TIMEZONE": "US/Eastern",
        "UPDATE_INTERVAL": UPDATE_INTERVAL,
        # Symbol Universe Configuration
        "SYMBOL_UNIVERSE_KEY": "stock_etf_test:combo_test",  # Default universe key for WebSocket subscriptions
        # Sprint 10: Redis Configuration for TickStockPL Integration
        "REDIS_URL": "",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": 6379,
        "REDIS_DB": 0,
        # Sprint 36: TickStockPL API Integration Configuration
        "TICKSTOCKPL_HOST": "localhost",
        "TICKSTOCKPL_PORT": 8080,
        "TICKSTOCKPL_API_KEY": "tickstock-cache-sync-2025",
        # Sprint 10: TimescaleDB Configuration
        "TICKSTOCK_DB_HOST": "localhost",
        "TICKSTOCK_DB_PORT": 5432,
        "TICKSTOCK_DB_NAME": "tickstock",
        "TICKSTOCK_DB_USER": "app_readwrite",
        "TICKSTOCK_DB_PASSWORD": "password",  # Default placeholder - must be set in .env
        "COLLECTION_INTERVAL": COLLECTION_INTERVAL,
        "EMISSION_INTERVAL": EMISSION_INTERVAL,
        "USE_MASSIVE_API": False,
        "MASSIVE_API_KEY": "",
        "MASSIVE_WEBSOCKET_RECONNECT_DELAY": 5,
        "MASSIVE_WEBSOCKET_MAX_RECONNECT_DELAY": 60,
        "MASSIVE_WEBSOCKET_MAX_RETRIES": 5,
        "API_CACHE_TTL": 60,
        "API_MIN_REQUEST_INTERVAL": 0.05,
        "API_BATCH_SIZE": 25,
        "SEED_FROM_RECENT_CANDLE": False,
        "USE_SYNTHETIC_DATA": False,
        "SIMULATOR_UNIVERSE": "MARKET_CAP_LARGE_UNIVERSE",
        "SYNTHETIC_DATA_RATE": 0.1,
        "SYNTHETIC_DATA_VARIANCE": 0.05,
        # Sprint 51: Multi-Connection WebSocket Configuration
        "USE_MULTI_CONNECTION": False,
        "WEBSOCKET_CONNECTIONS_MAX": 3,
        "WEBSOCKET_ROUTING_STRATEGY": "manual",
        # Connection 1: Primary Watchlist
        "WEBSOCKET_CONNECTION_1_ENABLED": False,
        "WEBSOCKET_CONNECTION_1_NAME": "primary",
        "WEBSOCKET_CONNECTION_1_UNIVERSE_KEY": "",
        "WEBSOCKET_CONNECTION_1_SYMBOLS": "",
        # Connection 2: Secondary Watchlist
        "WEBSOCKET_CONNECTION_2_ENABLED": False,
        "WEBSOCKET_CONNECTION_2_NAME": "secondary",
        "WEBSOCKET_CONNECTION_2_UNIVERSE_KEY": "",
        "WEBSOCKET_CONNECTION_2_SYMBOLS": "",
        # Connection 3: Tertiary Watchlist
        "WEBSOCKET_CONNECTION_3_ENABLED": False,
        "WEBSOCKET_CONNECTION_3_NAME": "tertiary",
        "WEBSOCKET_CONNECTION_3_UNIVERSE_KEY": "",
        "WEBSOCKET_CONNECTION_3_SYMBOLS": "",
        # Sprint 41: Enhanced Synthetic Data Configuration
        "SYNTHETIC_UNIVERSE": "market_leaders:top_500",
        "SYNTHETIC_PATTERN_INJECTION": True,
        "SYNTHETIC_PATTERN_FREQUENCY": 0.1,
        "SYNTHETIC_PATTERN_TYPES": "Doji,Hammer,ShootingStar,BullishEngulfing,BearishEngulfing,Harami",
        "SYNTHETIC_SCENARIO": "normal",
        "SYNTHETIC_ACTIVITY_LEVEL": "medium",
        "MOMENTUM_WINDOW_SECONDS": 5,
        "MOMENTUM_MAX_THRESHOLD": 15,
        "FLOW_WINDOW_SECONDS": 30,
        "FLOW_MAX_THRESHOLD": 40,
        "FLOW_DECAY_FACTOR": 0.95,
        # LOGGING CONFIGURATION
        "LOG_CONSOLE_VERBOSE": False,
        "LOG_CONSOLE_DEBUG": False,
        "LOG_CONSOLE_CONNECTION_VERBOSE": True,
        "LOG_FILE_ENABLED": False,  # Temporarily disabled to fix startup hanging
        "LOG_FILE_PRODUCTION_MODE": False,
        # Integration Logging Configuration
        "INTEGRATION_LOGGING_ENABLED": True,
        "INTEGRATION_LOG_FILE": False,
        "INTEGRATION_LOG_LEVEL": "INFO",
        # Sprint 32: Enhanced Error Management Configuration
        "LOG_FILE_PATH": "logs/tickstock.log",
        "LOG_FILE_MAX_SIZE": 10485760,  # 10MB
        "LOG_FILE_BACKUP_COUNT": 5,
        "LOG_DB_ENABLED": False,
        "LOG_DB_SEVERITY_THRESHOLD": "error",
        "REDIS_ERROR_CHANNEL": "tickstock:errors",
        # (Removed legacy tracing configuration - no longer needed after event detection cleanup)
        # POOL WORKERS CONFIGURATION - SPRINT 26 BASELINE
        "WORKER_POOL_SIZE": 12,
        "MIN_WORKER_POOL_SIZE": 8,
        "MAX_WORKER_POOL_SIZE": 16,
        "WORKER_EVENT_BATCH_SIZE": 1000,
        "WORKER_COLLECTION_TIMEOUT": 0.5,
        # QUEUE CONFIGURATION - Keep in config for environment tuning
        "MAX_QUEUE_SIZE": 100000,
        "QUEUE_OVERFLOW_DROP_THRESHOLD": 0.98,
        "MAX_EVENT_AGE_MS": 120000,
        # COLLECTION CONFIGURATION - SPRINT 26 OPTIMIZED
        "EVENT_BATCH_SIZE": 500,
        "COLLECTION_MAX_EVENTS": 1000,
        "COLLECTION_TIMEOUT": 0.5,
        "HEARTBEAT_INTERVAL": 2.0,
        "FLASK_SECRET_KEY": os.urandom(16).hex(),
        "MAX_SESSIONS_PER_USER": 1,
        "SESSION_EXPIRY_DAYS": 1,
        "LOCKOUT_DURATION_MINUTES": 20,
        "MAX_LOCKOUTS": 3,
        "CAPTCHA_ENABLED": True,
        "COMMON_PASSWORDS": "password,password123,12345678,qwerty",
        "EMAIL_VERIFICATION_SALT": "email-verification",
        "PASSWORD_RESET_SALT": "password-reset",
        "SUPPORT_EMAIL": "support@tickstock.com",
        # (Removed legacy HighLow detection configuration)
        # SMS Settings
        "SMS_TEST_MODE": True,
        "TWILIO_ACCOUNT_SID": "",
        "TWILIO_AUTH_TOKEN": "",
        "TWILIO_PHONE_NUMBER": "+15551234567",
        "SMS_VERIFICATION_CODE_LENGTH": 6,
        "SMS_VERIFICATION_CODE_EXPIRY": 10,
        "RENEWAL_SMS_MAX_ATTEMPTS": 3,
        "RENEWAL_SMS_LOCKOUT_MINUTES": 15,
        # Migration Validation Settings
        "MIGRATION_VALIDATION": True,
        "MIGRATION_PARALLEL_PROCESSING": False,
        # Event Processor Configuration
        "EVENT_RATE_LIMIT": 0.1,
        "STOCK_DETAILS_MAX_AGE": 3600,
        # Performance Monitoring
        "DATA_PUBLISHER_STATS_INTERVAL": 30,
        "RESET_STATS_ON_SESSION_CHANGE": True,
        # Data Publisher Configuration (Phase 2)
        "MAX_EVENTS_PER_PUBLISH": 100,
        "PUBLISH_BATCH_SIZE": 30,
        "ENABLE_LEGACY_FALLBACK": True,
        "DATA_PUBLISHER_DEBUG_MODE": True,
        # (Removed legacy trend detection parameters)
        # (Removed legacy surge detection parameters)
        # Multi-frequency configuration defaults
        "DATA_SOURCE_MODE": "production",
        "ACTIVE_DATA_PROVIDERS": ["massive"],
        "ENABLE_MULTI_FREQUENCY": False,
        "WEBSOCKET_SUBSCRIPTIONS_FILE": "config/websocket_subscriptions.json",
        "PROCESSING_CONFIG_FILE": "config/processing_config.json",
        "WEBSOCKET_CONNECTION_POOL_SIZE": 3,
        "WEBSOCKET_CONNECTION_TIMEOUT": 15,
        "WEBSOCKET_SUBSCRIPTION_BATCH_SIZE": 50,
        "WEBSOCKET_HEALTH_CHECK_INTERVAL": 30,
        "WEBSOCKET_PER_SECOND_ENABLED": True,
        "WEBSOCKET_PER_MINUTE_ENABLED": False,
        "WEBSOCKET_FAIR_VALUE_ENABLED": False,
        # Synthetic Data Multi-Frequency Configuration
        "ENABLE_SYNTHETIC_DATA_VALIDATION": True,
        "VALIDATION_PRICE_TOLERANCE": 0.001,  # 0.1%
        "VALIDATION_VOLUME_TOLERANCE": 0.05,  # 5%
        "VALIDATION_VWAP_TOLERANCE": 0.002,  # 0.2%
        # Per-Second Generator Configuration
        "SYNTHETIC_TICK_VARIANCE": 0.001,  # 0.1% tick variance
        "SYNTHETIC_VOLUME_MULTIPLIER": 1.0,
        "SYNTHETIC_VWAP_VARIANCE": 0.002,  # 0.2% VWAP variance
        # Per-Minute Generator Configuration
        "SYNTHETIC_MINUTE_WINDOW": 60,  # seconds
        "SYNTHETIC_MINUTE_VOLUME_MULTIPLIER": 50,
        "SYNTHETIC_MINUTE_DRIFT": 0.005,  # 0.5% price drift variance
        # Fair Market Value Generator Configuration
        "SYNTHETIC_FMV_UPDATE_INTERVAL": 30,  # seconds
        "SYNTHETIC_FMV_CORRELATION": 0.85,  # 0-1 correlation strength
        "SYNTHETIC_FMV_VARIANCE": 0.002,  # 0.2% FMV variance
        "SYNTHETIC_FMV_PREMIUM_RANGE": 0.01,  # 1% premium/discount range
        # Enhanced FMV Correlation Parameters
        "SYNTHETIC_FMV_MOMENTUM_DECAY": 0.7,  # FMV momentum persistence
        "SYNTHETIC_FMV_LAG_FACTOR": 0.3,  # FMV lag response
        "SYNTHETIC_FMV_VOLATILITY_DAMPENING": 0.6,  # FMV volatility reduction
        "SYNTHETIC_FMV_TRENDING_CORRELATION": 0.90,  # Higher correlation in trends
        "SYNTHETIC_FMV_SIDEWAYS_CORRELATION": 0.75,  # Medium correlation sideways
        "SYNTHETIC_FMV_VOLATILE_CORRELATION": 0.65,  # Lower correlation in volatility
    }

    CONFIG_TYPES = {
        "APP_VERSION": str,
        "DATABASE_URI": str,
        "DATABASE_SYNCH_AGGREGATE_SECONDS": int,
        "APP_ENVIRONMENT": str,
        "APP_DEBUG": bool,
        "APP_HOST": str,
        "APP_PORT": int,
        "MARKET_TIMEZONE": str,
        "UPDATE_INTERVAL": float,
        "COLLECTION_INTERVAL": float,
        "EMISSION_INTERVAL": float,
        "USE_MASSIVE_API": bool,
        "MASSIVE_API_KEY": str,
        "MASSIVE_WEBSOCKET_RECONNECT_DELAY": int,
        "MASSIVE_WEBSOCKET_MAX_RECONNECT_DELAY": int,
        "MASSIVE_WEBSOCKET_MAX_RETRIES": int,
        "API_CACHE_TTL": int,
        "API_MIN_REQUEST_INTERVAL": float,
        "API_BATCH_SIZE": int,
        "SEED_FROM_RECENT_CANDLE": bool,
        "USE_SYNTHETIC_DATA": bool,
        "SIMULATOR_UNIVERSE": str,
        "SYMBOL_UNIVERSE_KEY": str,
        "SYNTHETIC_DATA_RATE": float,
        "SYNTHETIC_DATA_VARIANCE": float,
        # Sprint 51: Multi-Connection WebSocket Configuration Types
        "USE_MULTI_CONNECTION": bool,
        "WEBSOCKET_CONNECTIONS_MAX": int,
        "WEBSOCKET_ROUTING_STRATEGY": str,
        "WEBSOCKET_CONNECTION_1_ENABLED": bool,
        "WEBSOCKET_CONNECTION_1_NAME": str,
        "WEBSOCKET_CONNECTION_1_UNIVERSE_KEY": str,
        "WEBSOCKET_CONNECTION_1_SYMBOLS": str,
        "WEBSOCKET_CONNECTION_2_ENABLED": bool,
        "WEBSOCKET_CONNECTION_2_NAME": str,
        "WEBSOCKET_CONNECTION_2_UNIVERSE_KEY": str,
        "WEBSOCKET_CONNECTION_2_SYMBOLS": str,
        "WEBSOCKET_CONNECTION_3_ENABLED": bool,
        "WEBSOCKET_CONNECTION_3_NAME": str,
        "WEBSOCKET_CONNECTION_3_UNIVERSE_KEY": str,
        "WEBSOCKET_CONNECTION_3_SYMBOLS": str,
        "MOMENTUM_WINDOW_SECONDS": float,
        "MOMENTUM_MAX_THRESHOLD": int,
        "FLOW_WINDOW_SECONDS": float,
        "FLOW_MAX_THRESHOLD": int,
        "FLOW_DECAY_FACTOR": float,
        # REDIS CONFIGURATION TYPES
        "REDIS_URL": str,
        "REDIS_HOST": str,
        "REDIS_PORT": int,
        "REDIS_DB": int,
        # Sprint 36: TickStockPL API Integration Configuration Types
        "TICKSTOCKPL_HOST": str,
        "TICKSTOCKPL_PORT": int,
        "TICKSTOCKPL_API_KEY": str,
        # LOGGING CONFIGURATION TYPES
        "LOG_CONSOLE_VERBOSE": bool,
        "LOG_CONSOLE_DEBUG": bool,
        "LOG_CONSOLE_CONNECTION_VERBOSE": bool,
        "LOG_FILE_ENABLED": bool,
        "LOG_FILE_PRODUCTION_MODE": bool,
        # Sprint 32: Enhanced Error Management Configuration Types
        "LOG_FILE_PATH": str,
        "LOG_FILE_MAX_SIZE": int,
        "LOG_FILE_BACKUP_COUNT": int,
        "LOG_DB_ENABLED": bool,
        "LOG_DB_SEVERITY_THRESHOLD": str,
        "REDIS_ERROR_CHANNEL": str,
        # (Removed legacy tracing type definitions)
        # POOL WORKERS CONFIGURATION
        "WORKER_POOL_SIZE": int,
        "MIN_WORKER_POOL_SIZE": int,
        "MAX_WORKER_POOL_SIZE": int,
        "WORKER_EVENT_BATCH_SIZE": int,
        "WORKER_COLLECTION_TIMEOUT": float,
        "MAX_QUEUE_SIZE": int,
        "QUEUE_OVERFLOW_DROP_THRESHOLD": float,
        "EVENT_BATCH_SIZE": int,
        "MAX_EVENT_AGE_MS": int,
        "COLLECTION_MAX_EVENTS": int,
        "COLLECTION_TIMEOUT": float,
        "HEARTBEAT_INTERVAL": float,
        "SYNTHETIC_ACTIVITY_LEVEL": str,
        "FLASK_SECRET_KEY": str,
        "MAX_SESSIONS_PER_USER": int,
        "SESSION_EXPIRY_DAYS": int,
        "LOCKOUT_DURATION_MINUTES": int,
        "MAX_LOCKOUTS": int,
        "CAPTCHA_ENABLED": bool,
        "COMMON_PASSWORDS": str,
        "EMAIL_VERIFICATION_SALT": str,
        "PASSWORD_RESET_SALT": str,
        "SUPPORT_EMAIL": str,
        # (Removed legacy HighLow detection type definitions)
        # SMS Settings
        "SMS_TEST_MODE": bool,
        "TWILIO_ACCOUNT_SID": str,
        "TWILIO_AUTH_TOKEN": str,
        "TWILIO_PHONE_NUMBER": str,
        "SMS_VERIFICATION_CODE_LENGTH": int,
        "SMS_VERIFICATION_CODE_EXPIRY": int,
        "RENEWAL_SMS_MAX_ATTEMPTS": int,
        "RENEWAL_SMS_LOCKOUT_MINUTES": int,
        # Migration Validation Settings
        "MIGRATION_VALIDATION": bool,
        "MIGRATION_PARALLEL_PROCESSING": bool,
        # Event Processor Configuration
        "EVENT_RATE_LIMIT": float,
        "STOCK_DETAILS_MAX_AGE": int,
        # Performance Monitoring
        "DATA_PUBLISHER_STATS_INTERVAL": int,
        "RESET_STATS_ON_SESSION_CHANGE": bool,
        # Data Publisher Configuration (Phase 2)
        "MAX_EVENTS_PER_PUBLISH": int,
        "PUBLISH_BATCH_SIZE": int,
        "ENABLE_LEGACY_FALLBACK": bool,
        "DATA_PUBLISHER_DEBUG_MODE": bool,
        # (Removed legacy trend detection type definitions)
        # (Removed legacy surge detection type definitions)
        # Multi-frequency configuration types
        "DATA_SOURCE_MODE": str,
        "ACTIVE_DATA_PROVIDERS": list,
        "ENABLE_MULTI_FREQUENCY": bool,
        "WEBSOCKET_SUBSCRIPTIONS_FILE": str,
        "PROCESSING_CONFIG_FILE": str,
        "WEBSOCKET_CONNECTION_POOL_SIZE": int,
        "WEBSOCKET_CONNECTION_TIMEOUT": int,
        "WEBSOCKET_SUBSCRIPTION_BATCH_SIZE": int,
        "WEBSOCKET_HEALTH_CHECK_INTERVAL": int,
        "WEBSOCKET_PER_SECOND_ENABLED": bool,
        "WEBSOCKET_PER_MINUTE_ENABLED": bool,
        "WEBSOCKET_FAIR_VALUE_ENABLED": bool,
        # WebSocket Emission Controls (Sprint 111)
        "ENABLE_PER_SECOND_EVENTS": bool,
        "ENABLE_PER_MINUTE_EVENTS": bool,
        "ENABLE_FMV_EVENTS": bool,
        # Synthetic Data Multi-Frequency Configuration Types
        "ENABLE_SYNTHETIC_DATA_VALIDATION": bool,
        "VALIDATION_PRICE_TOLERANCE": float,
        "VALIDATION_VOLUME_TOLERANCE": float,
        "VALIDATION_VWAP_TOLERANCE": float,
        # Per-Second Generator Configuration Types
        "SYNTHETIC_TICK_VARIANCE": float,
        "SYNTHETIC_VOLUME_MULTIPLIER": float,
        "SYNTHETIC_VWAP_VARIANCE": float,
        # Per-Minute Generator Configuration Types
        "SYNTHETIC_MINUTE_WINDOW": int,
        "SYNTHETIC_MINUTE_VOLUME_MULTIPLIER": int,
        "SYNTHETIC_MINUTE_DRIFT": float,
        # Fair Market Value Generator Configuration Types
        "SYNTHETIC_FMV_UPDATE_INTERVAL": int,
        "SYNTHETIC_FMV_CORRELATION": float,
        "SYNTHETIC_FMV_VARIANCE": float,
        "SYNTHETIC_FMV_PREMIUM_RANGE": float,
        # Enhanced FMV Correlation Parameter Types
        "SYNTHETIC_FMV_MOMENTUM_DECAY": float,
        "SYNTHETIC_FMV_LAG_FACTOR": float,
        "SYNTHETIC_FMV_VOLATILITY_DAMPENING": float,
        "SYNTHETIC_FMV_TRENDING_CORRELATION": float,
        "SYNTHETIC_FMV_SIDEWAYS_CORRELATION": float,
        "SYNTHETIC_FMV_VOLATILE_CORRELATION": float,
    }

    def __init__(self):
        self.config = {}
        self._load_defaults()

        # Multi-frequency configuration caches
        self._websocket_subscriptions = None
        self._processing_config = None
        self._last_config_load = None
        self._config_change_callbacks = []
        self._file_watcher_thread = None

        logger.info("Configuration manager initialized with defaults")

    def _load_defaults(self):
        """Load default configuration values."""
        self.config = self.DEFAULTS.copy()

    def load_from_env(self, env_path=None):
        """Load configuration from environment variables."""
        if env_path is None:
            env_path = find_dotenv()

        if env_path:
            logger.info(f"Loading environment from: {env_path}")
            load_dotenv(env_path, override=True)
        else:
            logger.warning("No .env file found, using environment variables as-is")

        # Load all configuration values
        for key in self.CONFIG_TYPES:
            if key in os.environ:
                self._set_config_value(key, os.environ[key])

        logger.info("Configuration loaded from environment")
        return self.config

    def _set_config_value(self, key, value):
        """Parse and validate configuration value based on its expected type."""
        expected_type = self.CONFIG_TYPES.get(key)

        if expected_type is bool:
            if isinstance(value, str):
                self.config[key] = value.strip().lower() in ("true", "yes", "y", "1")
            else:
                self.config[key] = bool(value)

        elif expected_type is int:
            try:
                self.config[key] = int(value)
            except (ValueError, TypeError):
                logger.warning(f"Invalid integer value for {key}: {value}, using default")

        elif expected_type is float:
            try:
                self.config[key] = float(value)
            except (ValueError, TypeError):
                logger.warning(f"Invalid float value for {key}: {value}, using default")

        elif expected_type is list:
            if isinstance(value, str):
                self.config[key] = [item.strip() for item in value.split(",") if item.strip()]
            elif isinstance(value, list):
                self.config[key] = value
            else:
                logger.warning(f"Invalid list value for {key}: {value}, using default")

        elif expected_type is list:
            if isinstance(value, str):
                # Handle comma-separated provider lists
                self.config[key] = [item.strip() for item in value.split(",") if item.strip()]
            elif isinstance(value, list):
                self.config[key] = value
            else:
                logger.warning(f"Invalid list value for {key}: {value}, using default")

        elif expected_type is dict:
            if isinstance(value, str):
                try:
                    # Try to parse as JSON
                    import json

                    self.config[key] = json.loads(value)
                except (ValueError, json.JSONDecodeError):
                    # If not valid JSON, try simple key:value parsing
                    result = {}
                    for pair in value.split(","):
                        if ":" in pair:
                            k, v = pair.split(":", 1)
                            try:
                                result[k.strip()] = int(v.strip())
                            except ValueError:
                                result[k.strip()] = v.strip()
                    self.config[key] = result
            elif isinstance(value, dict):
                self.config[key] = value
            else:
                logger.warning(f"Invalid dict value for {key}: {value}, using default")
        else:
            self.config[key] = value

    def get_config(self):
        """Get the complete configuration dictionary."""
        return self.config

    def validate_config(self):
        """Validate the loaded configuration for consistency."""
        errors = []
        warnings = []

        # Legacy validation
        if self.config.get("USE_MASSIVE_API") and not self.config.get("MASSIVE_API_KEY"):
            errors.append("MASSIVE_API_KEY is required when USE_MASSIVE_API is enabled")

        if self.config.get("USE_SYNTHETIC_DATA") and self.config.get("USE_MASSIVE_API"):
            warnings.append(
                "Both USE_SYNTHETIC_DATA and USE_MASSIVE_API enabled; prioritizing synthetic data"
            )
            self.config["USE_MASSIVE_API"] = False

        # Multi-frequency validation
        if self.config.get("ENABLE_MULTI_FREQUENCY"):
            multi_errors, multi_warnings = self._validate_multi_frequency_config()
            errors.extend(multi_errors)
            warnings.extend(multi_warnings)

        # Synthetic data configuration validation
        if self.config.get("USE_SYNTHETIC_DATA") or "synthetic" in self.config.get(
            "ACTIVE_DATA_PROVIDERS", []
        ):
            synthetic_errors, synthetic_warnings = self._validate_synthetic_data_config()
            errors.extend(synthetic_errors)
            warnings.extend(synthetic_warnings)

        # Apply backward compatibility migrations
        self._migrate_legacy_configuration()

        # Log warnings
        for warning in warnings:
            logger.warning(f"CONFIG: {warning}")

        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info("Configuration validation successful")
        return True

    '''
    def save_config(self, file_path):
        """Save current configuration to a file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    '''

    def load_config(self, file_path):
        """Load configuration from a file."""
        try:
            if not Path(file_path).exists():
                logger.warning(f"Configuration file not found: {file_path}")
                return False

            with open(file_path) as f:
                file_config = json.load(f)

            for key, value in file_config.items():
                if key in self.CONFIG_TYPES:
                    self.config[key] = value
                else:
                    logger.warning(f"Unknown configuration key in file: {key}")

            logger.info(f"Configuration loaded from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False

    def _validate_multi_frequency_config(self):
        """Validate multi-frequency configuration for consistency."""
        errors = []
        warnings = []

        # Validate data source mode
        valid_modes = ["production", "test", "hybrid"]
        data_source_mode = self.config.get("DATA_SOURCE_MODE", "production")
        if data_source_mode not in valid_modes:
            errors.append(
                f"Invalid DATA_SOURCE_MODE: {data_source_mode}. Must be one of {valid_modes}"
            )

        # Validate active providers
        active_providers = self.config.get("ACTIVE_DATA_PROVIDERS", [])
        valid_providers = ["massive", "synthetic", "simulated"]
        invalid_providers = [p for p in active_providers if p not in valid_providers]
        if invalid_providers:
            errors.append(f"Invalid providers in ACTIVE_DATA_PROVIDERS: {invalid_providers}")

        # Massive API key validation
        if "massive" in active_providers and not self.config.get("MASSIVE_API_KEY"):
            errors.append("MASSIVE_API_KEY required when 'massive' is in ACTIVE_DATA_PROVIDERS")

        # Connection pool validation
        pool_size = self.config.get("WEBSOCKET_CONNECTION_POOL_SIZE", 3)
        if pool_size < 1 or pool_size > 10:
            warnings.append(
                f"WEBSOCKET_CONNECTION_POOL_SIZE ({pool_size}) outside recommended range 1-10"
            )

        return errors, warnings

    def _validate_synthetic_data_config(self):
        """Validate synthetic data configuration for multi-frequency generation."""
        errors = []
        warnings = []

        # Validate tolerance values are reasonable
        price_tolerance = self.config.get("VALIDATION_PRICE_TOLERANCE", 0.001)
        if not (0.0001 <= price_tolerance <= 0.01):  # 0.01% to 1%
            warnings.append(
                f"VALIDATION_PRICE_TOLERANCE ({price_tolerance}) outside recommended range 0.0001-0.01"
            )

        volume_tolerance = self.config.get("VALIDATION_VOLUME_TOLERANCE", 0.05)
        if not (0.01 <= volume_tolerance <= 0.2):  # 1% to 20%
            warnings.append(
                f"VALIDATION_VOLUME_TOLERANCE ({volume_tolerance}) outside recommended range 0.01-0.2"
            )

        # Validate FMV correlation parameters
        fmv_correlation = self.config.get("SYNTHETIC_FMV_CORRELATION", 0.85)
        if not (0.1 <= fmv_correlation <= 1.0):
            errors.append(
                f"SYNTHETIC_FMV_CORRELATION ({fmv_correlation}) must be between 0.1 and 1.0"
            )

        # Validate FMV regime correlations are in logical order
        trending_corr = self.config.get("SYNTHETIC_FMV_TRENDING_CORRELATION", 0.90)
        sideways_corr = self.config.get("SYNTHETIC_FMV_SIDEWAYS_CORRELATION", 0.75)
        volatile_corr = self.config.get("SYNTHETIC_FMV_VOLATILE_CORRELATION", 0.65)

        if not (volatile_corr <= sideways_corr <= trending_corr):
            warnings.append(
                f"FMV regime correlations should be ordered: volatile ({volatile_corr}) <= "
                f"sideways ({sideways_corr}) <= trending ({trending_corr})"
            )

        # Validate update intervals are reasonable
        fmv_interval = self.config.get("SYNTHETIC_FMV_UPDATE_INTERVAL", 30)
        if fmv_interval < 1 or fmv_interval > 300:  # 1 second to 5 minutes
            warnings.append(
                f"SYNTHETIC_FMV_UPDATE_INTERVAL ({fmv_interval}s) outside recommended range 1-300 seconds"
            )

        # Validate variance parameters
        tick_variance = self.config.get("SYNTHETIC_TICK_VARIANCE", 0.001)
        if tick_variance > 0.01:  # More than 1%
            warnings.append(
                f"SYNTHETIC_TICK_VARIANCE ({tick_variance}) is high, may cause unrealistic price jumps"
            )

        minute_drift = self.config.get("SYNTHETIC_MINUTE_DRIFT", 0.005)
        if minute_drift > 0.02:  # More than 2%
            warnings.append(
                f"SYNTHETIC_MINUTE_DRIFT ({minute_drift}) is high, may cause unrealistic minute bars"
            )

        # Validate momentum decay factor
        momentum_decay = self.config.get("SYNTHETIC_FMV_MOMENTUM_DECAY", 0.7)
        if not (0.1 <= momentum_decay <= 0.95):
            warnings.append(
                f"SYNTHETIC_FMV_MOMENTUM_DECAY ({momentum_decay}) outside recommended range 0.1-0.95"
            )

        return errors, warnings

    def _migrate_legacy_configuration(self):
        """Automatically migrate legacy configuration to multi-frequency format."""
        migrations_applied = []

        # Migrate USE_MASSIVE_API to ACTIVE_DATA_PROVIDERS
        if self.config.get("USE_MASSIVE_API"):
            providers = list(self.config.get("ACTIVE_DATA_PROVIDERS", []))
            if "massive" not in providers:
                providers.append("massive")
                self.config["ACTIVE_DATA_PROVIDERS"] = providers
                migrations_applied.append("USE_MASSIVE_API -> ACTIVE_DATA_PROVIDERS")

        # Migrate USE_SYNTHETIC_DATA to ACTIVE_DATA_PROVIDERS
        if self.config.get("USE_SYNTHETIC_DATA"):
            providers = list(self.config.get("ACTIVE_DATA_PROVIDERS", []))
            if "synthetic" not in providers:
                providers.append("synthetic")
                self.config["ACTIVE_DATA_PROVIDERS"] = providers
                migrations_applied.append("USE_SYNTHETIC_DATA -> ACTIVE_DATA_PROVIDERS")

        # Ensure at least one provider is active
        if not self.config.get("ACTIVE_DATA_PROVIDERS"):
            self.config["ACTIVE_DATA_PROVIDERS"] = ["simulated"]
            migrations_applied.append("Added default simulated provider")

        if migrations_applied:
            logger.info(f"Applied legacy configuration migrations: {migrations_applied}")

        return migrations_applied

    def load_json_configurations(self):
        """Load JSON configuration files with caching and validation."""
        current_time = time.time()

        # Check if reload is needed (cache for 60 seconds)
        if self._last_config_load and current_time - self._last_config_load < 60:
            return True

        try:
            # Load WebSocket subscriptions configuration
            subscriptions_file = self.config.get("WEBSOCKET_SUBSCRIPTIONS_FILE")
            if subscriptions_file and Path(subscriptions_file).exists():
                with open(subscriptions_file) as f:
                    raw_config = json.load(f)
                    self._websocket_subscriptions = self._interpolate_environment_variables(
                        raw_config
                    )

                # Validate subscriptions configuration
                errors = self._validate_websocket_subscriptions_schema(
                    self._websocket_subscriptions
                )
                if errors:
                    logger.error(f"WebSocket subscriptions configuration errors: {errors}")
                    return False

            # Load processing configuration
            processing_file = self.config.get("PROCESSING_CONFIG_FILE")
            if processing_file and Path(processing_file).exists():
                with open(processing_file) as f:
                    raw_config = json.load(f)
                    self._processing_config = self._interpolate_environment_variables(raw_config)

            self._last_config_load = current_time
            logger.info("JSON configurations loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading JSON configurations: {e}")
            return False

    def _interpolate_environment_variables(self, config_dict):
        """Recursively interpolate environment variables in configuration values."""

        def interpolate_value(value):
            if isinstance(value, str):
                # Replace ${VAR} and ${VAR:default} patterns
                pattern = r"\$\{([^:}]+)(?::([^}]*))?\}"

                def replace_var(match):
                    var_name = match.group(1)
                    default_value = match.group(2) or ""
                    return os.environ.get(var_name, default_value)

                return re.sub(pattern, replace_var, value)
            if isinstance(value, dict):
                return {k: interpolate_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [interpolate_value(item) for item in value]
            return value

        return interpolate_value(config_dict)

    def _validate_websocket_subscriptions_schema(self, subscriptions_config):
        """Validate WebSocket subscriptions JSON configuration."""
        required_fields = ["version", "subscriptions"]
        errors = []

        # Check required top-level fields
        for field in required_fields:
            if field not in subscriptions_config:
                errors.append(f"Missing required field: {field}")

        # Validate subscription entries
        subscriptions = subscriptions_config.get("subscriptions", {})
        for freq_name, freq_config in subscriptions.items():
            # Required fields per subscription
            sub_required = ["enabled", "provider", "tickers"]
            for field in sub_required:
                if field not in freq_config:
                    errors.append(f"Subscription '{freq_name}' missing required field: {field}")

            # Provider validation
            provider = freq_config.get("provider")
            if provider not in ["massive", "synthetic", "simulated"]:
                errors.append(f"Subscription '{freq_name}' has invalid provider: {provider}")

            # Ticker validation
            tickers = freq_config.get("tickers", [])
            if not isinstance(tickers, list) or not tickers:
                errors.append(f"Subscription '{freq_name}' must have non-empty tickers list")

            # Max ticker validation
            max_tickers = freq_config.get("max_tickers", 1000)
            if len(tickers) > max_tickers:
                errors.append(
                    f"Subscription '{freq_name}' has {len(tickers)} tickers, exceeds max_tickers {max_tickers}"
                )

        return errors

    def get_websocket_subscriptions(self):
        """Get WebSocket subscriptions configuration with lazy loading."""
        if self._websocket_subscriptions is None:
            self.load_json_configurations()
        return self._websocket_subscriptions or {}

    def get_processing_config(self):
        """Get processing configuration with lazy loading."""
        if self._processing_config is None:
            self.load_json_configurations()
        return self._processing_config or {}

    def get_legacy_config_value(self, key):
        """Get configuration value using legacy key names for backward compatibility."""
        legacy_mappings = {
            "USE_MASSIVE_API": lambda: "massive" in self.config.get("ACTIVE_DATA_PROVIDERS", []),
            "USE_SYNTHETIC_DATA": lambda: "synthetic"
            in self.config.get("ACTIVE_DATA_PROVIDERS", []),
        }

        if key in legacy_mappings:
            try:
                return legacy_mappings[key]()
            except Exception as e:
                logger.warning(f"Error resolving legacy config key {key}: {e}")
                return self.config.get(key)

        return self.config.get(key)

    def register_config_change_callback(self, callback: Callable[[], None]):
        """Register a callback to be called when configuration changes."""
        self._config_change_callbacks.append(callback)

    def _notify_configuration_change(self):
        """Notify all registered callbacks of configuration changes."""
        for callback in self._config_change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in configuration change callback: {e}")

    def setup_file_watching(self):
        """Set up file system watching for configuration changes."""
        if self._file_watcher_thread is not None:
            return  # Already watching

        def watch_config_files():
            """Background thread to monitor configuration file changes."""
            config_files = [
                self.config.get("WEBSOCKET_SUBSCRIPTIONS_FILE"),
                self.config.get("PROCESSING_CONFIG_FILE"),
            ]

            file_timestamps = {}

            while True:
                try:
                    for file_path in config_files:
                        if file_path and Path(file_path).exists():
                            current_mtime = Path(file_path).stat().st_mtime

                            if file_path not in file_timestamps:
                                file_timestamps[file_path] = current_mtime
                            elif current_mtime > file_timestamps[file_path]:
                                logger.info(f"Configuration file changed: {file_path}")
                                self._reload_json_configurations_safe()
                                file_timestamps[file_path] = current_mtime

                    time.sleep(5)  # Check every 5 seconds

                except Exception as e:
                    logger.error(f"Error in configuration file watching: {e}")
                    time.sleep(30)  # Wait longer on error

        # Start file watcher thread
        self._file_watcher_thread = threading.Thread(target=watch_config_files, daemon=True)
        self._file_watcher_thread.start()
        logger.info("Configuration file watching enabled")

    def _reload_json_configurations_safe(self):
        """Safely reload JSON configurations with validation."""
        try:
            # Store current configuration as backup
            backup_subscriptions = self._websocket_subscriptions
            backup_processing = self._processing_config

            # Clear cache to force reload
            self._websocket_subscriptions = None
            self._processing_config = None
            self._last_config_load = None

            # Attempt to load new configurations
            if self.load_json_configurations():
                # Validate new configuration
                if self.config.get("ENABLE_MULTI_FREQUENCY"):
                    subscriptions = self.get_websocket_subscriptions()
                    if subscriptions:
                        errors = self._validate_websocket_subscriptions_schema(subscriptions)
                        if errors:
                            logger.error(f"Configuration hot-reload validation failed: {errors}")
                            self._websocket_subscriptions = backup_subscriptions
                            self._processing_config = backup_processing
                            return False

                logger.info("Configuration hot-reload successful")
                self._notify_configuration_change()
                return True
            logger.error("Configuration hot-reload failed to load files, reverting to backup")
            self._websocket_subscriptions = backup_subscriptions
            self._processing_config = backup_processing
            return False

        except Exception as e:
            logger.error(f"Error during configuration hot-reload: {e}")
            return False

    # Synthetic Data Configuration Helper Methods
    def get_synthetic_data_config(self) -> dict[str, Any]:
        """
        Get complete synthetic data configuration for all frequencies.

        Returns:
            Dict containing all synthetic data configuration options
        """
        config = {}

        # Multi-frequency enablement
        config["multi_frequency_enabled"] = self.config.get("ENABLE_MULTI_FREQUENCY", False)
        config["per_second_enabled"] = self.config.get("WEBSOCKET_PER_SECOND_ENABLED", True)
        config["per_minute_enabled"] = self.config.get("WEBSOCKET_PER_MINUTE_ENABLED", False)
        config["fair_value_enabled"] = self.config.get("WEBSOCKET_FAIR_VALUE_ENABLED", False)

        # Data validation
        config["validation_enabled"] = self.config.get("ENABLE_SYNTHETIC_DATA_VALIDATION", True)
        config["validation_price_tolerance"] = self.config.get("VALIDATION_PRICE_TOLERANCE", 0.001)
        config["validation_volume_tolerance"] = self.config.get("VALIDATION_VOLUME_TOLERANCE", 0.05)
        config["validation_vwap_tolerance"] = self.config.get("VALIDATION_VWAP_TOLERANCE", 0.002)

        # Per-second generation settings
        config["per_second"] = {
            "activity_level": self.config.get("SYNTHETIC_ACTIVITY_LEVEL", "medium"),
            "price_variance": self.config.get("SYNTHETIC_PER_SECOND_PRICE_VARIANCE", 0.001),
            "volume_range": self.config.get("SYNTHETIC_PER_SECOND_VOLUME_RANGE", [10000, 100000]),
            "tick_frequency": self.config.get("SYNTHETIC_PER_SECOND_FREQUENCY", 1.0),
        }

        # Per-minute generation settings
        config["per_minute"] = {
            "aggregation_window": self.config.get("SYNTHETIC_PER_MINUTE_WINDOW", 60),
            "min_ticks_per_minute": self.config.get("SYNTHETIC_PER_MINUTE_MIN_TICKS", 5),
            "max_ticks_per_minute": self.config.get("SYNTHETIC_PER_MINUTE_MAX_TICKS", 30),
            "ohlc_variance": self.config.get("SYNTHETIC_PER_MINUTE_OHLC_VARIANCE", 0.005),
            "volume_multiplier": self.config.get("SYNTHETIC_PER_MINUTE_VOLUME_MULTIPLIER", 5.0),
        }

        # Fair market value settings
        config["fair_value"] = {
            "update_interval": self.config.get("SYNTHETIC_FMV_UPDATE_INTERVAL", 30),
            "correlation_strength": self.config.get("SYNTHETIC_FMV_CORRELATION", 0.85),
            "value_variance": self.config.get("SYNTHETIC_FMV_VARIANCE", 0.002),
            "premium_discount_range": self.config.get("SYNTHETIC_FMV_PREMIUM_RANGE", 0.01),
            "momentum_decay": self.config.get("SYNTHETIC_FMV_MOMENTUM_DECAY", 0.7),
            "lag_factor": self.config.get("SYNTHETIC_FMV_LAG_FACTOR", 0.3),
            "volatility_dampening": self.config.get("SYNTHETIC_FMV_VOLATILITY_DAMPENING", 0.6),
            "trending_correlation": self.config.get("SYNTHETIC_FMV_TRENDING_CORRELATION", 0.90),
            "sideways_correlation": self.config.get("SYNTHETIC_FMV_SIDEWAYS_CORRELATION", 0.75),
            "volatile_correlation": self.config.get("SYNTHETIC_FMV_VOLATILE_CORRELATION", 0.65),
        }

        return config

    def get_synthetic_data_presets(self) -> dict[str, dict[str, Any]]:
        """
        Get predefined synthetic data configuration presets.

        Returns:
            Dict of preset configurations for different testing scenarios
        """
        return {
            "development": {
                "description": "Low-frequency development testing",
                "ENABLE_MULTI_FREQUENCY": True,
                "WEBSOCKET_PER_SECOND_ENABLED": True,
                "WEBSOCKET_PER_MINUTE_ENABLED": False,
                "WEBSOCKET_FAIR_VALUE_ENABLED": False,
                "SYNTHETIC_ACTIVITY_LEVEL": "medium",
                "SYNTHETIC_PER_SECOND_FREQUENCY": 2.0,  # Every 2 seconds
                "ENABLE_SYNTHETIC_DATA_VALIDATION": True,
            },
            "integration_testing": {
                "description": "Full multi-frequency integration testing",
                "ENABLE_MULTI_FREQUENCY": True,
                "WEBSOCKET_PER_SECOND_ENABLED": True,
                "WEBSOCKET_PER_MINUTE_ENABLED": True,
                "WEBSOCKET_FAIR_VALUE_ENABLED": True,
                "SYNTHETIC_ACTIVITY_LEVEL": "high",
                "SYNTHETIC_PER_SECOND_FREQUENCY": 0.5,  # Every 0.5 seconds
                "SYNTHETIC_FMV_UPDATE_INTERVAL": 15,  # Every 15 seconds
                "ENABLE_SYNTHETIC_DATA_VALIDATION": True,
                "VALIDATION_PRICE_TOLERANCE": 0.0005,  # Stricter validation
            },
            "performance_testing": {
                "description": "High-frequency performance testing",
                "ENABLE_MULTI_FREQUENCY": True,
                "WEBSOCKET_PER_SECOND_ENABLED": True,
                "WEBSOCKET_PER_MINUTE_ENABLED": True,
                "WEBSOCKET_FAIR_VALUE_ENABLED": True,
                "SYNTHETIC_ACTIVITY_LEVEL": "opening_bell",
                "SYNTHETIC_PER_SECOND_FREQUENCY": 0.1,  # Every 0.1 seconds
                "SYNTHETIC_FMV_UPDATE_INTERVAL": 5,  # Every 5 seconds
                "ENABLE_SYNTHETIC_DATA_VALIDATION": False,  # Disable for performance
                "SYNTHETIC_PER_MINUTE_MAX_TICKS": 50,
            },
            "market_simulation": {
                "description": "Realistic market behavior simulation",
                "ENABLE_MULTI_FREQUENCY": True,
                "WEBSOCKET_PER_SECOND_ENABLED": True,
                "WEBSOCKET_PER_MINUTE_ENABLED": True,
                "WEBSOCKET_FAIR_VALUE_ENABLED": True,
                "SYNTHETIC_ACTIVITY_LEVEL": "medium",
                "SYNTHETIC_PER_SECOND_FREQUENCY": 1.0,
                "SYNTHETIC_FMV_UPDATE_INTERVAL": 30,
                "SYNTHETIC_FMV_CORRELATION": 0.82,  # Realistic correlation
                "SYNTHETIC_FMV_TRENDING_CORRELATION": 0.88,
                "SYNTHETIC_FMV_VOLATILE_CORRELATION": 0.65,
                "ENABLE_SYNTHETIC_DATA_VALIDATION": True,
            },
            "minimal": {
                "description": "Minimal synthetic data for basic testing",
                "ENABLE_MULTI_FREQUENCY": False,
                "WEBSOCKET_PER_SECOND_ENABLED": True,
                "WEBSOCKET_PER_MINUTE_ENABLED": False,
                "WEBSOCKET_FAIR_VALUE_ENABLED": False,
                "SYNTHETIC_ACTIVITY_LEVEL": "low",
                "SYNTHETIC_PER_SECOND_FREQUENCY": 5.0,  # Every 5 seconds
                "ENABLE_SYNTHETIC_DATA_VALIDATION": False,
            },
        }

    def apply_synthetic_data_preset(self, preset_name: str) -> bool:
        """
        Apply a synthetic data configuration preset.

        Args:
            preset_name: Name of the preset to apply

        Returns:
            bool: True if preset was applied successfully
        """
        presets = self.get_synthetic_data_presets()

        if preset_name not in presets:
            logger.error(f"Unknown synthetic data preset: {preset_name}")
            return False

        preset_config = presets[preset_name]
        logger.info(
            f"Applying synthetic data preset '{preset_name}': {preset_config['description']}"
        )

        # Apply preset configuration
        changes_made = 0
        for key, value in preset_config.items():
            if key != "description":  # Skip the description field
                if self.config.get(key) != value:
                    self.config[key] = value
                    changes_made += 1

        if changes_made > 0:
            logger.info(f"Applied {changes_made} configuration changes from preset '{preset_name}'")
            self._notify_configuration_change()
        else:
            logger.info(f"Preset '{preset_name}' already active, no changes needed")

        return True

    def validate_synthetic_data_config(self) -> tuple[bool, list[str]]:
        """
        Validate synthetic data configuration for consistency.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check if multi-frequency is enabled but no frequencies are active
        if self.config.get("ENABLE_MULTI_FREQUENCY", False):
            active_frequencies = 0
            if self.config.get("WEBSOCKET_PER_SECOND_ENABLED", False):
                active_frequencies += 1
            if self.config.get("WEBSOCKET_PER_MINUTE_ENABLED", False):
                active_frequencies += 1
            if self.config.get("WEBSOCKET_FAIR_VALUE_ENABLED", False):
                active_frequencies += 1

            if active_frequencies == 0:
                errors.append("Multi-frequency enabled but no frequency streams are active")

        # Validate frequency intervals
        per_second_freq = self.config.get("SYNTHETIC_PER_SECOND_FREQUENCY", 1.0)
        if per_second_freq < 0.1 or per_second_freq > 60.0:
            errors.append(f"Per-second frequency {per_second_freq} outside valid range (0.1-60.0)")

        fmv_interval = self.config.get("SYNTHETIC_FMV_UPDATE_INTERVAL", 30)
        if fmv_interval < 5 or fmv_interval > 300:
            errors.append(f"FMV update interval {fmv_interval} outside valid range (5-300 seconds)")

        # Validate correlation parameters
        correlations = [
            ("SYNTHETIC_FMV_CORRELATION", 0.85),
            ("SYNTHETIC_FMV_TRENDING_CORRELATION", 0.90),
            ("SYNTHETIC_FMV_SIDEWAYS_CORRELATION", 0.75),
            ("SYNTHETIC_FMV_VOLATILE_CORRELATION", 0.65),
        ]

        for param, default in correlations:
            value = self.config.get(param, default)
            if not (0.0 <= value <= 1.0):
                errors.append(
                    f"Correlation parameter {param} ({value}) outside valid range (0.0-1.0)"
                )

        # Validate tolerance parameters
        tolerances = [
            ("VALIDATION_PRICE_TOLERANCE", 0.001, 0.0001, 0.01),
            ("VALIDATION_VOLUME_TOLERANCE", 0.05, 0.001, 0.20),
            ("VALIDATION_VWAP_TOLERANCE", 0.002, 0.0001, 0.01),
        ]

        for param, default, min_val, max_val in tolerances:
            value = self.config.get(param, default)
            if not (min_val <= value <= max_val):
                errors.append(
                    f"Tolerance parameter {param} ({value}) outside valid range ({min_val}-{max_val})"
                )

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Synthetic data configuration validation failed: {len(errors)} errors")

        return is_valid, errors

    def set_synthetic_data_intervals(
        self,
        per_second_interval: float = 1.0,
        per_minute_interval: int = 60,
        fmv_interval: int = 30,
    ) -> bool:
        """
        Set synthetic data generation intervals for testing flexibility.

        Args:
            per_second_interval: Seconds between per-second data generation (0.1-60.0)
            per_minute_interval: Seconds for minute aggregation window (30-300)
            fmv_interval: Seconds between FMV updates (5-300)

        Returns:
            bool: True if intervals were set successfully
        """
        # Validate intervals
        if not (0.1 <= per_second_interval <= 60.0):
            logger.error(
                f"Per-second interval {per_second_interval} outside valid range (0.1-60.0)"
            )
            return False

        if not (30 <= per_minute_interval <= 300):
            logger.error(f"Per-minute interval {per_minute_interval} outside valid range (30-300)")
            return False

        if not (5 <= fmv_interval <= 300):
            logger.error(f"FMV interval {fmv_interval} outside valid range (5-300)")
            return False

        # Set the intervals
        self.config["SYNTHETIC_PER_SECOND_FREQUENCY"] = per_second_interval
        self.config["SYNTHETIC_MINUTE_WINDOW"] = per_minute_interval
        self.config["SYNTHETIC_FMV_UPDATE_INTERVAL"] = fmv_interval

        logger.info(
            f"CONFIG: Set synthetic data intervals - "
            f"Per-second: {per_second_interval}s, "
            f"Per-minute: {per_minute_interval}s, "
            f"FMV: {fmv_interval}s"
        )

        return True

    def get_common_interval_presets(self) -> dict[str, dict[str, float]]:
        """
        Get common interval presets for testing (15s, 30s, 60s as mentioned in PRD).

        Returns:
            Dict of preset configurations with different interval combinations
        """
        return {
            "fast_15s": {
                "description": "15-second intervals for rapid testing",
                "per_second_interval": 15.0,
                "per_minute_interval": 60,
                "fmv_interval": 15,
            },
            "standard_30s": {
                "description": "30-second intervals for standard testing",
                "per_second_interval": 30.0,
                "per_minute_interval": 60,
                "fmv_interval": 30,
            },
            "slow_60s": {
                "description": "60-second intervals for slow testing",
                "per_second_interval": 60.0,
                "per_minute_interval": 60,
                "fmv_interval": 60,
            },
            "mixed_intervals": {
                "description": "Mixed intervals (15s per-second, 30s FMV, 60s per-minute)",
                "per_second_interval": 15.0,
                "per_minute_interval": 60,
                "fmv_interval": 30,
            },
            "high_frequency": {
                "description": "High frequency testing (5s per-second, 15s FMV)",
                "per_second_interval": 5.0,
                "per_minute_interval": 60,
                "fmv_interval": 15,
            },
        }

    def apply_interval_preset(self, preset_name: str) -> bool:
        """
        Apply a common interval preset for easy testing.

        Args:
            preset_name: Name of the preset to apply

        Returns:
            bool: True if preset was applied successfully
        """
        presets = self.get_common_interval_presets()

        if preset_name not in presets:
            logger.error(f"Unknown interval preset: {preset_name}")
            return False

        preset = presets[preset_name]
        logger.info(f"Applying interval preset '{preset_name}': {preset['description']}")

        return self.set_synthetic_data_intervals(
            per_second_interval=preset["per_second_interval"],
            per_minute_interval=preset["per_minute_interval"],
            fmv_interval=preset["fmv_interval"],
        )


# Sprint 32: Enhanced Error Management Configuration
try:
    from typing import Optional

    from pydantic import BaseModel, Field
    from pydantic_settings import BaseSettings

    class LoggingConfig(BaseSettings):
        """Logging configuration from environment"""

        # File logging
        log_file_enabled: bool = Field(default=False, env="LOG_FILE_ENABLED")
        log_file_path: str = Field(default="logs/tickstock.log", env="LOG_FILE_PATH")
        log_file_max_size: int = Field(default=10485760, env="LOG_FILE_MAX_SIZE")
        log_file_backup_count: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")

        # Database logging
        log_db_enabled: bool = Field(default=False, env="LOG_DB_ENABLED")
        log_db_severity_threshold: str = Field(default="error", env="LOG_DB_SEVERITY_THRESHOLD")

        # Redis integration
        redis_error_channel: str = Field(default="tickstock:errors", env="REDIS_ERROR_CHANNEL")

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"  # Ignore extra environment variables

except ImportError:
    logger.warning("Pydantic not available, LoggingConfig class not created")
    LoggingConfig = None
