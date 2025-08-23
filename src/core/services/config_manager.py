import os
import json
import time
import re
import threading
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from typing import Any, Dict, List, Optional, Callable, Tuple
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'config_manager')

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
    
    COLLECTION_INTERVAL = 0.5   # DataPublisher collection rate
    EMISSION_INTERVAL = 1.0     # WebSocketPublisher emission rate
    UPDATE_INTERVAL = 0.5       # Already used by DataPublisher

    # Core Detection Parameters (hardcode as class constants)
    SURGE_INTERVAL_SECONDS = 5              # Baseline comparison window
    SURGE_MIN_DATA_POINTS = 3               # Minimum buffer size before detection
    SURGE_VOLUME_THRESHOLD = 1.3            # Base volume multiplier threshold
    SURGE_GLOBAL_SENSITIVITY = 1.0          # Global threshold multiplier (NEW)
    SURGE_BUFFER_SIZE = 20                  # Maximum buffer points
    SURGE_MAX_HISTORY_POINTS = 15           # Surge history retention
    SURGE_EXPIRATION_SECONDS = 30           # Event expiration time
    SURGE_COOLDOWN_SECONDS = 5              # Time between surge events (matches interval)

    # Scoring System (hardcode as class constants)
    SURGE_SCORE_PRICE_WEIGHT = 50           # Weight for price component
    SURGE_SCORE_VOLUME_WEIGHT = 50          # Weight for volume component

    # Default configuration values
    DEFAULTS = {
        'APP_VERSION': '',
        'SQLALCHEMY_DATABASE_URI': '',
        'DATABASE_URI': 'postgresql://app_readwrite:1DfTGVBsECVtJa@localhost/marketpulse',
        'DATABASE_SYNCH_AGGREGATE_SECONDS': 30,    # Seconds
        'APP_ENVIRONMENT': 'development',
        'APP_DEBUG': False,
        'APP_HOST': '0.0.0.0',
        'APP_PORT': 5000,
        'MARKET_TIMEZONE': 'US/Eastern',
        'UPDATE_INTERVAL': UPDATE_INTERVAL,
        'COLLECTION_INTERVAL': COLLECTION_INTERVAL,
        'EMISSION_INTERVAL': EMISSION_INTERVAL,
        'USE_POLYGON_API': False,
        'POLYGON_API_KEY': '',
        'POLYGON_WEBSOCKET_RECONNECT_DELAY': 5,
        'POLYGON_WEBSOCKET_MAX_RECONNECT_DELAY': 60,
        'POLYGON_WEBSOCKET_MAX_RETRIES': 5,
        'API_CACHE_TTL': 60,
        'API_MIN_REQUEST_INTERVAL': 0.05,
        'API_BATCH_SIZE': 25,
        'SEED_FROM_RECENT_CANDLE': False,
        'USE_SYNTHETIC_DATA': False,
        'SIMULATOR_UNIVERSE': 'MARKET_CAP_LARGE_UNIVERSE',
        'SYNTHETIC_DATA_RATE': 0.1,
        'SYNTHETIC_DATA_VARIANCE': 0.05,
        'MOMENTUM_WINDOW_SECONDS': 5,
        'MOMENTUM_MAX_THRESHOLD': 15,
        'FLOW_WINDOW_SECONDS': 30,
        'FLOW_MAX_THRESHOLD': 40,
        'FLOW_DECAY_FACTOR': 0.95,
        
        # LOGGING CONFIGURATION
        'LOG_CONSOLE_VERBOSE': False,
        'LOG_CONSOLE_DEBUG': False,
        'LOG_CONSOLE_CONNECTION_VERBOSE': True,
        'LOG_FILE_ENABLED': True,
        'LOG_FILE_PRODUCTION_MODE': False,

        # TRACING
        'DATA_DEBUG_TRACE': False,
        'DATA_DEBUG_TRACE_LEVEL': 'NORMAL',
        'TRACE_ENABLED': False,
        'TRACE_TICKERS': ['AAPL', 'TSLA', 'NVDA'],
        'TRACE_LEVEL': 'NORMAL',
        'TRACE_OUTPUT_DIR': './logs/trace',
        'TRACE_AUTO_EXPORT_INTERVAL': 300,
        'TRACE_MAX_SIZE_MB': 50,

        # POOL WORKERS CONFIGURATION - SPRINT 26 BASELINE
        'WORKER_POOL_SIZE': 12,
        'MIN_WORKER_POOL_SIZE': 8,
        'MAX_WORKER_POOL_SIZE': 16,
        'WORKER_EVENT_BATCH_SIZE': 1000,
        'WORKER_COLLECTION_TIMEOUT': 0.5,

        # QUEUE CONFIGURATION - Keep in config for environment tuning
        'MAX_QUEUE_SIZE': 100000,
        'QUEUE_OVERFLOW_DROP_THRESHOLD': 0.98,
        'MAX_EVENT_AGE_MS': 120000,

        # COLLECTION CONFIGURATION - SPRINT 26 OPTIMIZED
        'EVENT_BATCH_SIZE': 500,
        'COLLECTION_MAX_EVENTS': 1000,
        'COLLECTION_TIMEOUT': 0.5,

        'HEARTBEAT_INTERVAL': 2.0,
        'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
        'FLASK_SECRET_KEY': os.urandom(16).hex(),
        'MAX_SESSIONS_PER_USER': 1,
        'SESSION_EXPIRY_DAYS': 1,
        'LOCKOUT_DURATION_MINUTES': 20,
        'MAX_LOCKOUTS': 3,
        'CAPTCHA_ENABLED': True,
        'COMMON_PASSWORDS': 'password,password123,12345678,qwerty',
        'EMAIL_VERIFICATION_SALT': 'email-verification',
        'PASSWORD_RESET_SALT': 'password-reset',
        'SUPPORT_EMAIL': 'support@tickstock.com',

        
        
        # HighLow Event Detection Configuration
        'HIGHLOW_MIN_PRICE_CHANGE': 0.01,
        'HIGHLOW_MIN_PERCENT_CHANGE': 0.1,
        'HIGHLOW_COOLDOWN_SECONDS': 1,
        'HIGHLOW_MARKET_AWARE': True,
        'HIGHLOW_EXTENDED_HOURS_MULTIPLIER': 2.0,
        'HIGHLOW_OPENING_MULTIPLIER': 1.5,
        'HIGHLOW_SIGNIFICANCE_SCORING': True,
        'HIGHLOW_SIGNIFICANCE_VOLUME_WEIGHT': 0.5,
        'HIGHLOW_TRACK_REVERSALS': True,
        'HIGHLOW_REVERSAL_WINDOW': 300,
        
        # SMS Settings
        'SMS_TEST_MODE': True,
        'TWILIO_ACCOUNT_SID': '',
        'TWILIO_AUTH_TOKEN': '',
        'TWILIO_PHONE_NUMBER': '+15551234567',
        'SMS_VERIFICATION_CODE_LENGTH': 6,
        'SMS_VERIFICATION_CODE_EXPIRY': 10,
        'RENEWAL_SMS_MAX_ATTEMPTS': 3,
        'RENEWAL_SMS_LOCKOUT_MINUTES': 15,

        # Migration Validation Settings
        'MIGRATION_VALIDATION': True,
        'MIGRATION_PERFORMANCE_LOGGING': True,
        'MIGRATION_PARALLEL_PROCESSING': False,

        # Event Processor Configuration
        'EVENT_RATE_LIMIT': 0.1,
        'STOCK_DETAILS_MAX_AGE': 3600,

        # Performance Monitoring
        'DATA_PUBLISHER_STATS_INTERVAL': 30,
        'RESET_STATS_ON_SESSION_CHANGE': True,

        # Data Publisher Configuration (Phase 2)
        'MAX_EVENTS_PER_PUBLISH': 100,
        'PUBLISH_BATCH_SIZE': 30,
        'ENABLE_LEGACY_FALLBACK': True,
        'DATA_PUBLISHER_DEBUG_MODE': True,

        # MARKET PERIOD - OPENING (9:30-9:45 AM ET)  # CHANGED from 9:30-10:00 AM
        'TREND_DIRECTION_THRESHOLD_OPENING': 0.25,
        'TREND_STRENGTH_THRESHOLD_OPENING': 0.45,
        'TREND_GLOBAL_SENSITIVITY_OPENING': 1.0,
        'TREND_MIN_EMISSION_INTERVAL_OPENING': 45,
        'TREND_RETRACEMENT_THRESHOLD_OPENING': 0.5,
        'TREND_MIN_DATA_POINTS_PER_WINDOW_OPENING': 4,
        'TREND_WARMUP_PERIOD_SECONDS_OPENING': 45,

        # MARKET PERIOD - MIDDAY (9:45 AM - 3:30 PM ET)  # CHANGED from 10:00 AM - 3:30 PM
        'TREND_DIRECTION_THRESHOLD_MIDDAY': 0.025,
        'TREND_STRENGTH_THRESHOLD_MIDDAY': 0.05,
        'TREND_GLOBAL_SENSITIVITY_MIDDAY': 1.5,
        'TREND_MIN_EMISSION_INTERVAL_MIDDAY': 90,
        'TREND_RETRACEMENT_THRESHOLD_MIDDAY': 0.25,
        'TREND_MIN_DATA_POINTS_PER_WINDOW_MIDDAY': 8,
        'TREND_WARMUP_PERIOD_SECONDS_MIDDAY': 90,

        # MARKET PERIOD - CLOSING (3:30-4:00 PM ET)
        'TREND_DIRECTION_THRESHOLD_CLOSING': 0.25,  # Increased from 0.20
        'TREND_STRENGTH_THRESHOLD_CLOSING': 0.50,   # Increased from 0.40
        'TREND_GLOBAL_SENSITIVITY_CLOSING': 1.0,    # Reduced from 1.2
        'TREND_MIN_EMISSION_INTERVAL_CLOSING': 30,  # Increased from 20
        'TREND_RETRACEMENT_THRESHOLD_CLOSING': 0.6, # Reduced from 0.8
        'TREND_MIN_DATA_POINTS_PER_WINDOW_CLOSING': 4,  # Increased from 3
        'TREND_WARMUP_PERIOD_SECONDS_CLOSING': 30,  # Increased from 20

        # MARKET PERIOD - AFTERHOURS (4:00-8:00 PM ET)
        'TREND_DIRECTION_THRESHOLD_AFTERHOURS': 0.015,  # Increased from 0.005 (3x)
        'TREND_STRENGTH_THRESHOLD_AFTERHOURS': 0.04,    # Increased from 0.015 (2.6x)
        'TREND_GLOBAL_SENSITIVITY_AFTERHOURS': 2.5,     # Reduced from 5.0
        'TREND_MIN_EMISSION_INTERVAL_AFTERHOURS': 150,  # Increased from 120
        'TREND_RETRACEMENT_THRESHOLD_AFTERHOURS': 0.15, # Reduced from 0.2
        'TREND_MIN_DATA_POINTS_PER_WINDOW_AFTERHOURS': 12,  # Increased from 10
        'TREND_WARMUP_PERIOD_SECONDS_AFTERHOURS': 240,  # Increased from 180

        # MARKET PERIOD - PREMARKET (4:00-9:30 AM ET)
        'TREND_DIRECTION_THRESHOLD_PREMARKET': 0.02,   # Increased from 0.01 (2x)
        'TREND_STRENGTH_THRESHOLD_PREMARKET': 0.05,    # Increased from 0.025 (2x)
        'TREND_GLOBAL_SENSITIVITY_PREMARKET': 2.0,     # Reduced from 4.0
        'TREND_MIN_EMISSION_INTERVAL_PREMARKET': 120,  # Increased from 90
        'TREND_RETRACEMENT_THRESHOLD_PREMARKET': 0.2,  # Reduced from 0.25
        'TREND_MIN_DATA_POINTS_PER_WINDOW_PREMARKET': 10,  # Increased from 8
        'TREND_WARMUP_PERIOD_SECONDS_PREMARKET': 180,  # Increased from 120

        # PRICE BUCKET THRESHOLDS - More conservative
        'TREND_DIRECTION_THRESHOLD_PENNY': 0.04,    # Increased from 0.02 (2x)
        'TREND_STRENGTH_THRESHOLD_PENNY': 0.08,     # Increased from 0.05
        'TREND_PRICE_CHANGE_PERCENT_PENNY': 1.5,    # Increased from 1.0

        'TREND_DIRECTION_THRESHOLD_LOW': 0.02,      # Increased from 0.01 (2x)
        'TREND_STRENGTH_THRESHOLD_LOW': 0.05,       # Increased from 0.03
        'TREND_PRICE_CHANGE_PERCENT_LOW': 0.75,     # Increased from 0.5

        'TREND_DIRECTION_THRESHOLD_MID': 0.015,     # Increased from 0.008
        'TREND_STRENGTH_THRESHOLD_MID': 0.035,      # Increased from 0.02
        'TREND_PRICE_CHANGE_PERCENT_MID': 0.5,      # Increased from 0.3

        'TREND_DIRECTION_THRESHOLD_HIGH': 0.01,     # Increased from 0.005 (2x)
        'TREND_STRENGTH_THRESHOLD_HIGH': 0.025,     # Increased from 0.015
        'TREND_PRICE_CHANGE_PERCENT_HIGH': 0.35,    # Increased from 0.2

        'TREND_DIRECTION_THRESHOLD_ULTRA': 0.006,   # Increased from 0.003 (2x)
        'TREND_STRENGTH_THRESHOLD_ULTRA': 0.02,     # Increased from 0.01 (2x)
        'TREND_PRICE_CHANGE_PERCENT_ULTRA': 0.2,    # Increased from 0.1 (2x)

        # VOLATILITY MULTIPLIERS - Less aggressive adjustments
        'TREND_VOLATILITY_MULTIPLIER_HIGH': 0.7,    # Increased from 0.5 (less reduction)
        'TREND_VOLATILITY_MULTIPLIER_NORMAL': 1.0,  # No change
        'TREND_VOLATILITY_MULTIPLIER_LOW': 1.3,     # Reduced from 2.0 (less amplification)

        # ===============================================
        # SURGE DETECTION PARAMETERS - UPDATED VALUES
        # ===============================================
        
        # MARKET PERIOD - OPENING (9:30-9:45 AM ET)  # CHANGED from 9:30-10:00 AM
        'SURGE_THRESHOLD_MULTIPLIER_OPENING': 0.7,     # Reduced from 1.0
        'SURGE_VOLUME_THRESHOLD_OPENING': 3.0,         # Increased from 2.0 
        'SURGE_GLOBAL_SENSITIVITY_OPENING': 0.5,       # Reduced from 0.8
        'SURGE_MIN_DATA_POINTS_OPENING': 4,            # Increased from 3
        'SURGE_INTERVAL_SECONDS_OPENING': 5,           # Increased from 3
        'SURGE_PRICE_THRESHOLD_PERCENT_OPENING': 4.5,  # Increased from 3.0

        # MARKET PERIOD - MIDDAY (9:45 AM - 3:30 PM ET)  # CHANGED from 10:00 AM - 3:30 PM
        # CRITICAL: This is where 60%+ false positives are happening
        'SURGE_THRESHOLD_MULTIPLIER_MIDDAY': 0.4,      # AGGRESSIVE: Reduced from 1.0
        'SURGE_VOLUME_THRESHOLD_MIDDAY': 3.0,          # DOUBLED from 1.5
        'SURGE_GLOBAL_SENSITIVITY_MIDDAY': 0.4,        # AGGRESSIVE: Reduced from 1.0
        'SURGE_MIN_DATA_POINTS_MIDDAY': 8,             # Increased from 5
        'SURGE_INTERVAL_SECONDS_MIDDAY': 20,           # Doubled from 10
        'SURGE_PRICE_THRESHOLD_PERCENT_MIDDAY': 4.0,   # DOUBLED from 2.0

        # MARKET PERIOD - CLOSING (3:30-4:00 PM ET)
        'SURGE_THRESHOLD_MULTIPLIER_CLOSING': 0.9,  # Increased from 0.7
        'SURGE_VOLUME_THRESHOLD_CLOSING': 2.5,      # Increased from 2.0
        'SURGE_GLOBAL_SENSITIVITY_CLOSING': 0.8,    # Reduced from 1.0
        'SURGE_MIN_DATA_POINTS_CLOSING': 3,         # Increased from 2
        'SURGE_INTERVAL_SECONDS_CLOSING': 2,        # Increased from 1
        'SURGE_PRICE_THRESHOLD_PERCENT_CLOSING': 3.5,  # Increased from 2.5

        # MARKET PERIOD - AFTERHOURS (4:00-8:00 PM ET)
        'SURGE_THRESHOLD_MULTIPLIER_AFTERHOURS': 1.5,  # Reduced from 2.0
        'SURGE_VOLUME_THRESHOLD_AFTERHOURS': 1.0,   # Increased from 0.8
        'SURGE_GLOBAL_SENSITIVITY_AFTERHOURS': 2.0, # Reduced from 3.0
        'SURGE_MIN_DATA_POINTS_AFTERHOURS': 5,      # Increased from 4
        'SURGE_INTERVAL_SECONDS_AFTERHOURS': 15,    # Increased from 10
        'SURGE_PRICE_THRESHOLD_PERCENT_AFTERHOURS': 1.0,  # Increased from 0.5 (2x)

        # MARKET PERIOD - PREMARKET (4:00-9:30 AM ET)
        'SURGE_THRESHOLD_MULTIPLIER_PREMARKET': 1.3,  # Reduced from 1.8
        'SURGE_VOLUME_THRESHOLD_PREMARKET': 1.2,    # Increased from 0.9
        'SURGE_GLOBAL_SENSITIVITY_PREMARKET': 1.5,  # Reduced from 2.5
        'SURGE_MIN_DATA_POINTS_PREMARKET': 4,       # Increased from 3
        'SURGE_INTERVAL_SECONDS_PREMARKET': 12,     # Increased from 8
        'SURGE_PRICE_THRESHOLD_PERCENT_PREMARKET': 1.25,  # Increased from 0.75

        # PRICE BANDS - More conservative thresholds
        'SURGE_PRICE_BAND_PENNY_MAX': 10,
        'SURGE_PRICE_BAND_PENNY_PCT': 8.0,             # Increased from 5.0
        'SURGE_PRICE_BAND_PENNY_DOLLAR': 0.15,      # Increased from 0.10

        'SURGE_PRICE_BAND_LOW_MAX': 50,
        'SURGE_PRICE_BAND_LOW_PCT': 5.0,               # Increased from 3.0
        'SURGE_PRICE_BAND_LOW_DOLLAR': 0.75,        # Increased from 0.50

        'SURGE_PRICE_BAND_MID_MAX': 200,
        'SURGE_PRICE_BAND_MID_PCT': 4.0,               # Increased from 2.5
        'SURGE_PRICE_BAND_MID_DOLLAR': 1.50,        # Increased from 1.00

        'SURGE_PRICE_BAND_HIGH_MAX': 500,
        'SURGE_PRICE_BAND_HIGH_PCT': 3.0,              # Increased from 1.5
        'SURGE_PRICE_BAND_HIGH_DOLLAR': 3.00,       # Increased from 2.00

        'SURGE_PRICE_BAND_ULTRA_PCT': 2.0,             # Increased from 1.0
        'SURGE_PRICE_BAND_ULTRA_DOLLAR': 5.00,      # Increased from 3.00

        # VOLATILITY MULTIPLIERS - Less aggressive
        'SURGE_VOLATILITY_MULTIPLIER_HIGH': 0.8,    # Increased from 0.7 (less reduction)
        'SURGE_VOLATILITY_MULTIPLIER_NORMAL': 1.0,  # No change
        'SURGE_VOLATILITY_MULTIPLIER_LOW': 1.2,     # Reduced from 1.5 (less amplification)

        # ADDITIONAL PARAMETERS
        'SURGE_BUFFER_MAX_AGE_SECONDS': 120,           # Increased from 90
        'SURGE_COOLDOWN_MULTIPLIER_MARKET': 2.0,       # Increased from 1.5

        'SURGE_DETECTION_MODE_DEFAULT': 'STRICT',      # Ensure STRICT is enforced
        'SURGE_DETECTION_MODE_MIDDAY': 'STRICT',       # NEW: Force STRICT for midday
        
        # Multi-frequency configuration defaults
        'DATA_SOURCE_MODE': 'production',
        'ACTIVE_DATA_PROVIDERS': ['polygon'],
        'ENABLE_MULTI_FREQUENCY': False,
        'WEBSOCKET_SUBSCRIPTIONS_FILE': 'config/websocket_subscriptions.json',
        'PROCESSING_CONFIG_FILE': 'config/processing_config.json',
        'WEBSOCKET_CONNECTION_POOL_SIZE': 3,
        'WEBSOCKET_CONNECTION_TIMEOUT': 15,
        'WEBSOCKET_SUBSCRIPTION_BATCH_SIZE': 50,
        'WEBSOCKET_HEALTH_CHECK_INTERVAL': 30,
        'WEBSOCKET_PER_SECOND_ENABLED': True,
        'WEBSOCKET_PER_MINUTE_ENABLED': False,
        'WEBSOCKET_FAIR_VALUE_ENABLED': False,
        
        # Synthetic Data Multi-Frequency Configuration
        'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
        'VALIDATION_PRICE_TOLERANCE': 0.001,  # 0.1%
        'VALIDATION_VOLUME_TOLERANCE': 0.05,   # 5%
        'VALIDATION_VWAP_TOLERANCE': 0.002,    # 0.2%
        
        # Per-Second Generator Configuration
        'SYNTHETIC_TICK_VARIANCE': 0.001,      # 0.1% tick variance
        'SYNTHETIC_VOLUME_MULTIPLIER': 1.0,
        'SYNTHETIC_VWAP_VARIANCE': 0.002,      # 0.2% VWAP variance
        
        # Per-Minute Generator Configuration
        'SYNTHETIC_MINUTE_WINDOW': 60,         # seconds
        'SYNTHETIC_MINUTE_VOLUME_MULTIPLIER': 50,
        'SYNTHETIC_MINUTE_DRIFT': 0.005,       # 0.5% price drift variance
        
        # Fair Market Value Generator Configuration
        'SYNTHETIC_FMV_UPDATE_INTERVAL': 30,   # seconds
        'SYNTHETIC_FMV_CORRELATION': 0.85,     # 0-1 correlation strength
        'SYNTHETIC_FMV_VARIANCE': 0.002,       # 0.2% FMV variance
        'SYNTHETIC_FMV_PREMIUM_RANGE': 0.01,   # 1% premium/discount range
        
        # Enhanced FMV Correlation Parameters
        'SYNTHETIC_FMV_MOMENTUM_DECAY': 0.7,   # FMV momentum persistence
        'SYNTHETIC_FMV_LAG_FACTOR': 0.3,       # FMV lag response
        'SYNTHETIC_FMV_VOLATILITY_DAMPENING': 0.6,  # FMV volatility reduction
        'SYNTHETIC_FMV_TRENDING_CORRELATION': 0.90,  # Higher correlation in trends
        'SYNTHETIC_FMV_SIDEWAYS_CORRELATION': 0.75,  # Medium correlation sideways
        'SYNTHETIC_FMV_VOLATILE_CORRELATION': 0.65,  # Lower correlation in volatility

    }

    CONFIG_TYPES = {
        'APP_VERSION': str,
        'SQLALCHEMY_DATABASE_URI': str,
        'DATABASE_URI': str,
        'DATABASE_SYNCH_AGGREGATE_SECONDS': int,
        'APP_ENVIRONMENT': str,
        'APP_DEBUG': bool,
        'APP_HOST': str,
        'APP_PORT': int,
        'MARKET_TIMEZONE': str,
        'UPDATE_INTERVAL': float,
        'COLLECTION_INTERVAL': float,
        'EMISSION_INTERVAL': float,
        'USE_POLYGON_API': bool,
        'POLYGON_API_KEY': str,
        'POLYGON_WEBSOCKET_RECONNECT_DELAY': int,
        'POLYGON_WEBSOCKET_MAX_RECONNECT_DELAY': int,
        'POLYGON_WEBSOCKET_MAX_RETRIES': int,
        'API_CACHE_TTL': int,
        'API_MIN_REQUEST_INTERVAL': float,
        'API_BATCH_SIZE': int,
        'SEED_FROM_RECENT_CANDLE': bool,
        'USE_SYNTHETIC_DATA': bool,
        'SIMULATOR_UNIVERSE': str,
        'SYNTHETIC_DATA_RATE': float,
        'SYNTHETIC_DATA_VARIANCE': float,
        'MOMENTUM_WINDOW_SECONDS': float,
        'MOMENTUM_MAX_THRESHOLD': int,
        'FLOW_WINDOW_SECONDS': float,
        'FLOW_MAX_THRESHOLD': int,
        'FLOW_DECAY_FACTOR': float,
        
        # LOGGING CONFIGURATION TYPES
        'LOG_CONSOLE_VERBOSE': bool,
        'LOG_CONSOLE_DEBUG': bool,
        'LOG_CONSOLE_CONNECTION_VERBOSE': bool,
        'LOG_FILE_ENABLED': bool,
        'LOG_FILE_PRODUCTION_MODE': bool,

        # TRACING
        'DATA_DEBUG_TRACE': bool,
        'DATA_DEBUG_TRACE_LEVEL': str,
        'TRACE_ENABLED': bool,
        'TRACE_TICKERS': list,
        'TRACE_LEVEL': str,
        'TRACE_OUTPUT_DIR': str,
        'TRACE_AUTO_EXPORT_INTERVAL': int,
        'TRACE_MAX_SIZE_MB': int,

        # POOL WORKERS CONFIGURATION
        'WORKER_POOL_SIZE': int,
        'MIN_WORKER_POOL_SIZE': int,
        'MAX_WORKER_POOL_SIZE': int,
        'WORKER_EVENT_BATCH_SIZE': int,
        'WORKER_COLLECTION_TIMEOUT': float,
        'MAX_QUEUE_SIZE': int,
        'QUEUE_OVERFLOW_DROP_THRESHOLD': float,
        'EVENT_BATCH_SIZE': int,
        'MAX_EVENT_AGE_MS': int,
        'COLLECTION_MAX_EVENTS': int,
        'COLLECTION_TIMEOUT': float,

        'HEARTBEAT_INTERVAL': float,
        'SYNTHETIC_ACTIVITY_LEVEL': str,
        'FLASK_SECRET_KEY': str,
        'MAX_SESSIONS_PER_USER': int,
        'SESSION_EXPIRY_DAYS': int,
        'LOCKOUT_DURATION_MINUTES': int,
        'MAX_LOCKOUTS': int,
        'CAPTCHA_ENABLED': bool,
        'COMMON_PASSWORDS': str,
        'EMAIL_VERIFICATION_SALT': str,
        'PASSWORD_RESET_SALT': str,
        'SUPPORT_EMAIL': str,



        # HighLow Event Detection Configuration
        'HIGHLOW_MIN_PRICE_CHANGE': float,
        'HIGHLOW_MIN_PERCENT_CHANGE': float,
        'HIGHLOW_COOLDOWN_SECONDS': int,
        'HIGHLOW_MARKET_AWARE': bool,
        'HIGHLOW_EXTENDED_HOURS_MULTIPLIER': float,
        'HIGHLOW_OPENING_MULTIPLIER': float,
        'HIGHLOW_SIGNIFICANCE_SCORING': bool,
        'HIGHLOW_SIGNIFICANCE_VOLUME_WEIGHT': float,
        'HIGHLOW_TRACK_REVERSALS': bool,
        'HIGHLOW_REVERSAL_WINDOW': int,
        
        # SMS Settings
        'SMS_TEST_MODE': bool,
        'TWILIO_ACCOUNT_SID': '',
        'TWILIO_AUTH_TOKEN': '',
        'TWILIO_PHONE_NUMBER': '+15551234567',
        'SMS_VERIFICATION_CODE_LENGTH': int,
        'SMS_VERIFICATION_CODE_EXPIRY': int,
        'RENEWAL_SMS_MAX_ATTEMPTS': int,
        'RENEWAL_SMS_LOCKOUT_MINUTES': int,

        # Migration Validation Settings
        'MIGRATION_VALIDATION': bool,
        'MIGRATION_PERFORMANCE_LOGGING': bool,
        'MIGRATION_PARALLEL_PROCESSING': bool,

        # Event Processor Configuration
        'EVENT_RATE_LIMIT': float,
        'STOCK_DETAILS_MAX_AGE': int,

        # Performance Monitoring
        'DATA_PUBLISHER_STATS_INTERVAL': int,
        'RESET_STATS_ON_SESSION_CHANGE': bool,

        # Data Publisher Configuration (Phase 2)
        'MAX_EVENTS_PER_PUBLISH': int,
        'PUBLISH_BATCH_SIZE': int,
        'ENABLE_LEGACY_FALLBACK': bool,
        'DATA_PUBLISHER_DEBUG_MODE': bool,

        # TREND DETECTION PARAMETERS
        'TREND_DIRECTION_THRESHOLD_OPENING': float,
        'TREND_STRENGTH_THRESHOLD_OPENING': float,
        'TREND_GLOBAL_SENSITIVITY_OPENING': float,
        'TREND_MIN_EMISSION_INTERVAL_OPENING': int,
        'TREND_RETRACEMENT_THRESHOLD_OPENING': float,
        'TREND_MIN_DATA_POINTS_PER_WINDOW_OPENING': int,
        'TREND_WARMUP_PERIOD_SECONDS_OPENING': int,

        'TREND_DIRECTION_THRESHOLD_MIDDAY': float,
        'TREND_STRENGTH_THRESHOLD_MIDDAY': float,
        'TREND_GLOBAL_SENSITIVITY_MIDDAY': float,
        'TREND_MIN_EMISSION_INTERVAL_MIDDAY': int,
        'TREND_RETRACEMENT_THRESHOLD_MIDDAY': float,
        'TREND_MIN_DATA_POINTS_PER_WINDOW_MIDDAY': int,
        'TREND_WARMUP_PERIOD_SECONDS_MIDDAY': int,

        'TREND_DIRECTION_THRESHOLD_CLOSING': float,
        'TREND_STRENGTH_THRESHOLD_CLOSING': float,
        'TREND_GLOBAL_SENSITIVITY_CLOSING': float,
        'TREND_MIN_EMISSION_INTERVAL_CLOSING': int,
        'TREND_RETRACEMENT_THRESHOLD_CLOSING': float,
        'TREND_MIN_DATA_POINTS_PER_WINDOW_CLOSING': int,
        'TREND_WARMUP_PERIOD_SECONDS_CLOSING': int,

        'TREND_DIRECTION_THRESHOLD_AFTERHOURS': float,
        'TREND_STRENGTH_THRESHOLD_AFTERHOURS': float,
        'TREND_GLOBAL_SENSITIVITY_AFTERHOURS': float,
        'TREND_MIN_EMISSION_INTERVAL_AFTERHOURS': int,
        'TREND_RETRACEMENT_THRESHOLD_AFTERHOURS': float,
        'TREND_MIN_DATA_POINTS_PER_WINDOW_AFTERHOURS': int,
        'TREND_WARMUP_PERIOD_SECONDS_AFTERHOURS': int,

        'TREND_DIRECTION_THRESHOLD_PREMARKET': float,
        'TREND_STRENGTH_THRESHOLD_PREMARKET': float,
        'TREND_GLOBAL_SENSITIVITY_PREMARKET': float,
        'TREND_MIN_EMISSION_INTERVAL_PREMARKET': int,
        'TREND_RETRACEMENT_THRESHOLD_PREMARKET': float,
        'TREND_MIN_DATA_POINTS_PER_WINDOW_PREMARKET': int,
        'TREND_WARMUP_PERIOD_SECONDS_PREMARKET': int,

        'TREND_DIRECTION_THRESHOLD_PENNY': float,
        'TREND_STRENGTH_THRESHOLD_PENNY': float,
        'TREND_PRICE_CHANGE_PERCENT_PENNY': float,

        'TREND_DIRECTION_THRESHOLD_LOW': float,
        'TREND_STRENGTH_THRESHOLD_LOW': float,
        'TREND_PRICE_CHANGE_PERCENT_LOW': float,

        'TREND_DIRECTION_THRESHOLD_MID': float,
        'TREND_STRENGTH_THRESHOLD_MID': float,
        'TREND_PRICE_CHANGE_PERCENT_MID': float,

        'TREND_DIRECTION_THRESHOLD_HIGH': float,
        'TREND_STRENGTH_THRESHOLD_HIGH': float,
        'TREND_PRICE_CHANGE_PERCENT_HIGH': float,

        'TREND_DIRECTION_THRESHOLD_ULTRA': float,
        'TREND_STRENGTH_THRESHOLD_ULTRA': float,
        'TREND_PRICE_CHANGE_PERCENT_ULTRA': float,

        'TREND_VOLATILITY_MULTIPLIER_HIGH': float,
        'TREND_VOLATILITY_MULTIPLIER_NORMAL': float,
        'TREND_VOLATILITY_MULTIPLIER_LOW': float,

        # MARKET PERIOD - OPENING (9:30-10:00 AM ET)
        'SURGE_THRESHOLD_MULTIPLIER_OPENING': float,
        'SURGE_VOLUME_THRESHOLD_OPENING': float,
        'SURGE_GLOBAL_SENSITIVITY_OPENING': float,
        'SURGE_MIN_DATA_POINTS_OPENING': int,
        'SURGE_INTERVAL_SECONDS_OPENING': int,
        'SURGE_PRICE_THRESHOLD_PERCENT_OPENING': float,

        # MARKET PERIOD - MIDDAY (10:00 AM - 3:30 PM ET)
        'SURGE_THRESHOLD_MULTIPLIER_MIDDAY': float,
        'SURGE_VOLUME_THRESHOLD_MIDDAY': float,
        'SURGE_GLOBAL_SENSITIVITY_MIDDAY': float,
        'SURGE_MIN_DATA_POINTS_MIDDAY': int,
        'SURGE_INTERVAL_SECONDS_MIDDAY': int,
        'SURGE_PRICE_THRESHOLD_PERCENT_MIDDAY': float,

        # MARKET PERIOD - CLOSING (3:30-4:00 PM ET)
        'SURGE_THRESHOLD_MULTIPLIER_CLOSING': float,
        'SURGE_VOLUME_THRESHOLD_CLOSING': float,
        'SURGE_GLOBAL_SENSITIVITY_CLOSING': float,
        'SURGE_MIN_DATA_POINTS_CLOSING': int,
        'SURGE_INTERVAL_SECONDS_CLOSING': int,
        'SURGE_PRICE_THRESHOLD_PERCENT_CLOSING': float,

        # MARKET PERIOD - AFTERHOURS (4:00-8:00 PM ET)
        'SURGE_THRESHOLD_MULTIPLIER_AFTERHOURS': float,
        'SURGE_VOLUME_THRESHOLD_AFTERHOURS': float,
        'SURGE_GLOBAL_SENSITIVITY_AFTERHOURS': float,
        'SURGE_MIN_DATA_POINTS_AFTERHOURS': int,
        'SURGE_INTERVAL_SECONDS_AFTERHOURS': int,
        'SURGE_PRICE_THRESHOLD_PERCENT_AFTERHOURS': float,

        # MARKET PERIOD - PREMARKET (4:00-9:30 AM ET)
        'SURGE_THRESHOLD_MULTIPLIER_PREMARKET': float,
        'SURGE_VOLUME_THRESHOLD_PREMARKET': float,
        'SURGE_GLOBAL_SENSITIVITY_PREMARKET': float,
        'SURGE_MIN_DATA_POINTS_PREMARKET': int,
        'SURGE_INTERVAL_SECONDS_PREMARKET': int,
        'SURGE_PRICE_THRESHOLD_PERCENT_PREMARKET': float,

        # PRICE BANDS
        'SURGE_PRICE_BAND_PENNY_MAX': int,
        'SURGE_PRICE_BAND_PENNY_PCT': float,
        'SURGE_PRICE_BAND_PENNY_DOLLAR': float,

        'SURGE_PRICE_BAND_LOW_MAX': int,
        'SURGE_PRICE_BAND_LOW_PCT': float,
        'SURGE_PRICE_BAND_LOW_DOLLAR': float,

        'SURGE_PRICE_BAND_MID_MAX': int,
        'SURGE_PRICE_BAND_MID_PCT': float,
        'SURGE_PRICE_BAND_MID_DOLLAR': float,

        'SURGE_PRICE_BAND_HIGH_MAX': int,
        'SURGE_PRICE_BAND_HIGH_PCT': float,
        'SURGE_PRICE_BAND_HIGH_DOLLAR': float,

        'SURGE_PRICE_BAND_ULTRA_PCT': float,
        'SURGE_PRICE_BAND_ULTRA_DOLLAR': float,

        # VOLATILITY MULTIPLIERS
        'SURGE_VOLATILITY_MULTIPLIER_HIGH': float,
        'SURGE_VOLATILITY_MULTIPLIER_NORMAL': float,
        'SURGE_VOLATILITY_MULTIPLIER_LOW': float,

        # ADDITIONAL PARAMETERS
        'SURGE_BUFFER_MAX_AGE_SECONDS': int,
        'SURGE_COOLDOWN_MULTIPLIER_MARKET': float,
        'SURGE_DETECTION_MODE_DEFAULT': str,
        'SURGE_DETECTION_MODE_MIDDAY': str,
        
        # Multi-frequency configuration types
        'DATA_SOURCE_MODE': str,
        'ACTIVE_DATA_PROVIDERS': list,
        'ENABLE_MULTI_FREQUENCY': bool,
        'WEBSOCKET_SUBSCRIPTIONS_FILE': str,
        'PROCESSING_CONFIG_FILE': str,
        'WEBSOCKET_CONNECTION_POOL_SIZE': int,
        'WEBSOCKET_CONNECTION_TIMEOUT': int,
        'WEBSOCKET_SUBSCRIPTION_BATCH_SIZE': int,
        'WEBSOCKET_HEALTH_CHECK_INTERVAL': int,
        'WEBSOCKET_PER_SECOND_ENABLED': bool,
        'WEBSOCKET_PER_MINUTE_ENABLED': bool,
        'WEBSOCKET_FAIR_VALUE_ENABLED': bool,
        
        # WebSocket Emission Controls (Sprint 111)
        'ENABLE_PER_SECOND_EVENTS': bool,
        'ENABLE_PER_MINUTE_EVENTS': bool,  
        'ENABLE_FMV_EVENTS': bool,
        
        # Synthetic Data Multi-Frequency Configuration Types
        'ENABLE_SYNTHETIC_DATA_VALIDATION': bool,
        'VALIDATION_PRICE_TOLERANCE': float,
        'VALIDATION_VOLUME_TOLERANCE': float,
        'VALIDATION_VWAP_TOLERANCE': float,
        
        # Per-Second Generator Configuration Types
        'SYNTHETIC_TICK_VARIANCE': float,
        'SYNTHETIC_VOLUME_MULTIPLIER': float,
        'SYNTHETIC_VWAP_VARIANCE': float,
        
        # Per-Minute Generator Configuration Types
        'SYNTHETIC_MINUTE_WINDOW': int,
        'SYNTHETIC_MINUTE_VOLUME_MULTIPLIER': int,
        'SYNTHETIC_MINUTE_DRIFT': float,
        
        # Fair Market Value Generator Configuration Types
        'SYNTHETIC_FMV_UPDATE_INTERVAL': int,
        'SYNTHETIC_FMV_CORRELATION': float,
        'SYNTHETIC_FMV_VARIANCE': float,
        'SYNTHETIC_FMV_PREMIUM_RANGE': float,
        
        # Enhanced FMV Correlation Parameter Types
        'SYNTHETIC_FMV_MOMENTUM_DECAY': float,
        'SYNTHETIC_FMV_LAG_FACTOR': float,
        'SYNTHETIC_FMV_VOLATILITY_DAMPENING': float,
        'SYNTHETIC_FMV_TRENDING_CORRELATION': float,
        'SYNTHETIC_FMV_SIDEWAYS_CORRELATION': float,
        'SYNTHETIC_FMV_VOLATILE_CORRELATION': float

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
                self.config[key] = value.strip().lower() in ('true', 'yes', 'y', '1')
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
                self.config[key] = [item.strip() for item in value.split(',') if item.strip()]
            elif isinstance(value, list):
                self.config[key] = value
            else:
                logger.warning(f"Invalid list value for {key}: {value}, using default")
        
        elif expected_type is list:
            if isinstance(value, str):
                # Handle comma-separated provider lists
                self.config[key] = [item.strip() for item in value.split(',') if item.strip()]
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
                    for pair in value.split(','):
                        if ':' in pair:
                            k, v = pair.split(':', 1)
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
        if self.config.get('USE_POLYGON_API') and not self.config.get('POLYGON_API_KEY'):
            errors.append("POLYGON_API_KEY is required when USE_POLYGON_API is enabled")
        
        if self.config.get('USE_SYNTHETIC_DATA') and self.config.get('USE_POLYGON_API'):
            warnings.append("Both USE_SYNTHETIC_DATA and USE_POLYGON_API enabled; prioritizing synthetic data")
            self.config['USE_POLYGON_API'] = False
        
        # Multi-frequency validation
        if self.config.get('ENABLE_MULTI_FREQUENCY'):
            multi_errors, multi_warnings = self._validate_multi_frequency_config()
            errors.extend(multi_errors)
            warnings.extend(multi_warnings)
        
        # Synthetic data configuration validation
        if self.config.get('USE_SYNTHETIC_DATA') or 'synthetic' in self.config.get('ACTIVE_DATA_PROVIDERS', []):
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
                
            with open(file_path, 'r') as f:
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
        valid_modes = ['production', 'test', 'hybrid']
        data_source_mode = self.config.get('DATA_SOURCE_MODE', 'production')
        if data_source_mode not in valid_modes:
            errors.append(f"Invalid DATA_SOURCE_MODE: {data_source_mode}. Must be one of {valid_modes}")
        
        # Validate active providers
        active_providers = self.config.get('ACTIVE_DATA_PROVIDERS', [])
        valid_providers = ['polygon', 'synthetic', 'simulated']
        invalid_providers = [p for p in active_providers if p not in valid_providers]
        if invalid_providers:
            errors.append(f"Invalid providers in ACTIVE_DATA_PROVIDERS: {invalid_providers}")
        
        # Polygon API key validation
        if 'polygon' in active_providers and not self.config.get('POLYGON_API_KEY'):
            errors.append("POLYGON_API_KEY required when 'polygon' is in ACTIVE_DATA_PROVIDERS")
        
        # Connection pool validation
        pool_size = self.config.get('WEBSOCKET_CONNECTION_POOL_SIZE', 3)
        if pool_size < 1 or pool_size > 10:
            warnings.append(f"WEBSOCKET_CONNECTION_POOL_SIZE ({pool_size}) outside recommended range 1-10")
        
        return errors, warnings
    
    def _validate_synthetic_data_config(self):
        """Validate synthetic data configuration for multi-frequency generation."""
        errors = []
        warnings = []
        
        # Validate tolerance values are reasonable
        price_tolerance = self.config.get('VALIDATION_PRICE_TOLERANCE', 0.001)
        if not (0.0001 <= price_tolerance <= 0.01):  # 0.01% to 1%
            warnings.append(f"VALIDATION_PRICE_TOLERANCE ({price_tolerance}) outside recommended range 0.0001-0.01")
        
        volume_tolerance = self.config.get('VALIDATION_VOLUME_TOLERANCE', 0.05)
        if not (0.01 <= volume_tolerance <= 0.2):  # 1% to 20%
            warnings.append(f"VALIDATION_VOLUME_TOLERANCE ({volume_tolerance}) outside recommended range 0.01-0.2")
        
        # Validate FMV correlation parameters
        fmv_correlation = self.config.get('SYNTHETIC_FMV_CORRELATION', 0.85)
        if not (0.1 <= fmv_correlation <= 1.0):
            errors.append(f"SYNTHETIC_FMV_CORRELATION ({fmv_correlation}) must be between 0.1 and 1.0")
        
        # Validate FMV regime correlations are in logical order
        trending_corr = self.config.get('SYNTHETIC_FMV_TRENDING_CORRELATION', 0.90)
        sideways_corr = self.config.get('SYNTHETIC_FMV_SIDEWAYS_CORRELATION', 0.75)
        volatile_corr = self.config.get('SYNTHETIC_FMV_VOLATILE_CORRELATION', 0.65)
        
        if not (volatile_corr <= sideways_corr <= trending_corr):
            warnings.append(
                f"FMV regime correlations should be ordered: volatile ({volatile_corr}) <= "
                f"sideways ({sideways_corr}) <= trending ({trending_corr})"
            )
        
        # Validate update intervals are reasonable
        fmv_interval = self.config.get('SYNTHETIC_FMV_UPDATE_INTERVAL', 30)
        if fmv_interval < 1 or fmv_interval > 300:  # 1 second to 5 minutes
            warnings.append(f"SYNTHETIC_FMV_UPDATE_INTERVAL ({fmv_interval}s) outside recommended range 1-300 seconds")
        
        # Validate variance parameters
        tick_variance = self.config.get('SYNTHETIC_TICK_VARIANCE', 0.001)
        if tick_variance > 0.01:  # More than 1%
            warnings.append(f"SYNTHETIC_TICK_VARIANCE ({tick_variance}) is high, may cause unrealistic price jumps")
        
        minute_drift = self.config.get('SYNTHETIC_MINUTE_DRIFT', 0.005)
        if minute_drift > 0.02:  # More than 2%
            warnings.append(f"SYNTHETIC_MINUTE_DRIFT ({minute_drift}) is high, may cause unrealistic minute bars")
        
        # Validate momentum decay factor
        momentum_decay = self.config.get('SYNTHETIC_FMV_MOMENTUM_DECAY', 0.7)
        if not (0.1 <= momentum_decay <= 0.95):
            warnings.append(f"SYNTHETIC_FMV_MOMENTUM_DECAY ({momentum_decay}) outside recommended range 0.1-0.95")
        
        return errors, warnings
    
    def _migrate_legacy_configuration(self):
        """Automatically migrate legacy configuration to multi-frequency format."""
        migrations_applied = []
        
        # Migrate USE_POLYGON_API to ACTIVE_DATA_PROVIDERS
        if self.config.get('USE_POLYGON_API'):
            providers = list(self.config.get('ACTIVE_DATA_PROVIDERS', []))
            if 'polygon' not in providers:
                providers.append('polygon')
                self.config['ACTIVE_DATA_PROVIDERS'] = providers
                migrations_applied.append('USE_POLYGON_API -> ACTIVE_DATA_PROVIDERS')
        
        # Migrate USE_SYNTHETIC_DATA to ACTIVE_DATA_PROVIDERS
        if self.config.get('USE_SYNTHETIC_DATA'):
            providers = list(self.config.get('ACTIVE_DATA_PROVIDERS', []))
            if 'synthetic' not in providers:
                providers.append('synthetic')
                self.config['ACTIVE_DATA_PROVIDERS'] = providers
                migrations_applied.append('USE_SYNTHETIC_DATA -> ACTIVE_DATA_PROVIDERS')
        
        # Ensure at least one provider is active
        if not self.config.get('ACTIVE_DATA_PROVIDERS'):
            self.config['ACTIVE_DATA_PROVIDERS'] = ['simulated']
            migrations_applied.append('Added default simulated provider')
        
        if migrations_applied:
            logger.info(f"Applied legacy configuration migrations: {migrations_applied}")
        
        return migrations_applied
    
    def load_json_configurations(self):
        """Load JSON configuration files with caching and validation."""
        current_time = time.time()
        
        # Check if reload is needed (cache for 60 seconds)
        if (self._last_config_load and 
            current_time - self._last_config_load < 60):
            return True
        
        try:
            # Load WebSocket subscriptions configuration
            subscriptions_file = self.config.get('WEBSOCKET_SUBSCRIPTIONS_FILE')
            if subscriptions_file and Path(subscriptions_file).exists():
                with open(subscriptions_file, 'r') as f:
                    raw_config = json.load(f)
                    self._websocket_subscriptions = self._interpolate_environment_variables(raw_config)
                
                # Validate subscriptions configuration
                errors = self._validate_websocket_subscriptions_schema(self._websocket_subscriptions)
                if errors:
                    logger.error(f"WebSocket subscriptions configuration errors: {errors}")
                    return False
            
            # Load processing configuration
            processing_file = self.config.get('PROCESSING_CONFIG_FILE')  
            if processing_file and Path(processing_file).exists():
                with open(processing_file, 'r') as f:
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
                pattern = r'\$\{([^:}]+)(?::([^}]*))?\}'
                
                def replace_var(match):
                    var_name = match.group(1)
                    default_value = match.group(2) or ''
                    return os.environ.get(var_name, default_value)
                
                return re.sub(pattern, replace_var, value)
            elif isinstance(value, dict):
                return {k: interpolate_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [interpolate_value(item) for item in value]
            else:
                return value
        
        return interpolate_value(config_dict)
    
    def _validate_websocket_subscriptions_schema(self, subscriptions_config):
        """Validate WebSocket subscriptions JSON configuration."""
        required_fields = ['version', 'subscriptions']
        errors = []
        
        # Check required top-level fields
        for field in required_fields:
            if field not in subscriptions_config:
                errors.append(f"Missing required field: {field}")
        
        # Validate subscription entries
        subscriptions = subscriptions_config.get('subscriptions', {})
        for freq_name, freq_config in subscriptions.items():
            # Required fields per subscription
            sub_required = ['enabled', 'provider', 'tickers']
            for field in sub_required:
                if field not in freq_config:
                    errors.append(f"Subscription '{freq_name}' missing required field: {field}")
            
            # Provider validation
            provider = freq_config.get('provider')
            if provider not in ['polygon', 'synthetic', 'simulated']:
                errors.append(f"Subscription '{freq_name}' has invalid provider: {provider}")
            
            # Ticker validation
            tickers = freq_config.get('tickers', [])
            if not isinstance(tickers, list) or not tickers:
                errors.append(f"Subscription '{freq_name}' must have non-empty tickers list")
            
            # Max ticker validation
            max_tickers = freq_config.get('max_tickers', 1000)
            if len(tickers) > max_tickers:
                errors.append(f"Subscription '{freq_name}' has {len(tickers)} tickers, exceeds max_tickers {max_tickers}")
        
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
            'USE_POLYGON_API': lambda: 'polygon' in self.config.get('ACTIVE_DATA_PROVIDERS', []),
            'USE_SYNTHETIC_DATA': lambda: 'synthetic' in self.config.get('ACTIVE_DATA_PROVIDERS', [])
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
                self.config.get('WEBSOCKET_SUBSCRIPTIONS_FILE'),
                self.config.get('PROCESSING_CONFIG_FILE')
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
                if self.config.get('ENABLE_MULTI_FREQUENCY'):
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
            else:
                logger.error("Configuration hot-reload failed to load files, reverting to backup")
                self._websocket_subscriptions = backup_subscriptions
                self._processing_config = backup_processing
                return False
                
        except Exception as e:
            logger.error(f"Error during configuration hot-reload: {e}")
            return False
    
    # Synthetic Data Configuration Helper Methods
    def get_synthetic_data_config(self) -> Dict[str, Any]:
        """
        Get complete synthetic data configuration for all frequencies.
        
        Returns:
            Dict containing all synthetic data configuration options
        """
        config = {}
        
        # Multi-frequency enablement
        config['multi_frequency_enabled'] = self.config.get('ENABLE_MULTI_FREQUENCY', False)
        config['per_second_enabled'] = self.config.get('WEBSOCKET_PER_SECOND_ENABLED', True)
        config['per_minute_enabled'] = self.config.get('WEBSOCKET_PER_MINUTE_ENABLED', False)
        config['fair_value_enabled'] = self.config.get('WEBSOCKET_FAIR_VALUE_ENABLED', False)
        
        # Data validation
        config['validation_enabled'] = self.config.get('ENABLE_SYNTHETIC_DATA_VALIDATION', True)
        config['validation_price_tolerance'] = self.config.get('VALIDATION_PRICE_TOLERANCE', 0.001)
        config['validation_volume_tolerance'] = self.config.get('VALIDATION_VOLUME_TOLERANCE', 0.05)
        config['validation_vwap_tolerance'] = self.config.get('VALIDATION_VWAP_TOLERANCE', 0.002)
        
        # Per-second generation settings
        config['per_second'] = {
            'activity_level': self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium'),
            'price_variance': self.config.get('SYNTHETIC_PER_SECOND_PRICE_VARIANCE', 0.001),
            'volume_range': self.config.get('SYNTHETIC_PER_SECOND_VOLUME_RANGE', [10000, 100000]),
            'tick_frequency': self.config.get('SYNTHETIC_PER_SECOND_FREQUENCY', 1.0)
        }
        
        # Per-minute generation settings
        config['per_minute'] = {
            'aggregation_window': self.config.get('SYNTHETIC_PER_MINUTE_WINDOW', 60),
            'min_ticks_per_minute': self.config.get('SYNTHETIC_PER_MINUTE_MIN_TICKS', 5),
            'max_ticks_per_minute': self.config.get('SYNTHETIC_PER_MINUTE_MAX_TICKS', 30),
            'ohlc_variance': self.config.get('SYNTHETIC_PER_MINUTE_OHLC_VARIANCE', 0.005),
            'volume_multiplier': self.config.get('SYNTHETIC_PER_MINUTE_VOLUME_MULTIPLIER', 5.0)
        }
        
        # Fair market value settings
        config['fair_value'] = {
            'update_interval': self.config.get('SYNTHETIC_FMV_UPDATE_INTERVAL', 30),
            'correlation_strength': self.config.get('SYNTHETIC_FMV_CORRELATION', 0.85),
            'value_variance': self.config.get('SYNTHETIC_FMV_VARIANCE', 0.002),
            'premium_discount_range': self.config.get('SYNTHETIC_FMV_PREMIUM_RANGE', 0.01),
            'momentum_decay': self.config.get('SYNTHETIC_FMV_MOMENTUM_DECAY', 0.7),
            'lag_factor': self.config.get('SYNTHETIC_FMV_LAG_FACTOR', 0.3),
            'volatility_dampening': self.config.get('SYNTHETIC_FMV_VOLATILITY_DAMPENING', 0.6),
            'trending_correlation': self.config.get('SYNTHETIC_FMV_TRENDING_CORRELATION', 0.90),
            'sideways_correlation': self.config.get('SYNTHETIC_FMV_SIDEWAYS_CORRELATION', 0.75),
            'volatile_correlation': self.config.get('SYNTHETIC_FMV_VOLATILE_CORRELATION', 0.65)
        }
        
        return config
    
    def get_synthetic_data_presets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get predefined synthetic data configuration presets.
        
        Returns:
            Dict of preset configurations for different testing scenarios
        """
        return {
            'development': {
                'description': 'Low-frequency development testing',
                'ENABLE_MULTI_FREQUENCY': True,
                'WEBSOCKET_PER_SECOND_ENABLED': True,
                'WEBSOCKET_PER_MINUTE_ENABLED': False,
                'WEBSOCKET_FAIR_VALUE_ENABLED': False,
                'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
                'SYNTHETIC_PER_SECOND_FREQUENCY': 2.0,  # Every 2 seconds
                'ENABLE_SYNTHETIC_DATA_VALIDATION': True
            },
            'integration_testing': {
                'description': 'Full multi-frequency integration testing',
                'ENABLE_MULTI_FREQUENCY': True,
                'WEBSOCKET_PER_SECOND_ENABLED': True,
                'WEBSOCKET_PER_MINUTE_ENABLED': True,
                'WEBSOCKET_FAIR_VALUE_ENABLED': True,
                'SYNTHETIC_ACTIVITY_LEVEL': 'high',
                'SYNTHETIC_PER_SECOND_FREQUENCY': 0.5,  # Every 0.5 seconds
                'SYNTHETIC_FMV_UPDATE_INTERVAL': 15,  # Every 15 seconds
                'ENABLE_SYNTHETIC_DATA_VALIDATION': True,
                'VALIDATION_PRICE_TOLERANCE': 0.0005  # Stricter validation
            },
            'performance_testing': {
                'description': 'High-frequency performance testing',
                'ENABLE_MULTI_FREQUENCY': True,
                'WEBSOCKET_PER_SECOND_ENABLED': True,
                'WEBSOCKET_PER_MINUTE_ENABLED': True,
                'WEBSOCKET_FAIR_VALUE_ENABLED': True,
                'SYNTHETIC_ACTIVITY_LEVEL': 'opening_bell',
                'SYNTHETIC_PER_SECOND_FREQUENCY': 0.1,  # Every 0.1 seconds
                'SYNTHETIC_FMV_UPDATE_INTERVAL': 5,  # Every 5 seconds
                'ENABLE_SYNTHETIC_DATA_VALIDATION': False,  # Disable for performance
                'SYNTHETIC_PER_MINUTE_MAX_TICKS': 50
            },
            'market_simulation': {
                'description': 'Realistic market behavior simulation',
                'ENABLE_MULTI_FREQUENCY': True,
                'WEBSOCKET_PER_SECOND_ENABLED': True,
                'WEBSOCKET_PER_MINUTE_ENABLED': True,
                'WEBSOCKET_FAIR_VALUE_ENABLED': True,
                'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
                'SYNTHETIC_PER_SECOND_FREQUENCY': 1.0,
                'SYNTHETIC_FMV_UPDATE_INTERVAL': 30,
                'SYNTHETIC_FMV_CORRELATION': 0.82,  # Realistic correlation
                'SYNTHETIC_FMV_TRENDING_CORRELATION': 0.88,
                'SYNTHETIC_FMV_VOLATILE_CORRELATION': 0.65,
                'ENABLE_SYNTHETIC_DATA_VALIDATION': True
            },
            'minimal': {
                'description': 'Minimal synthetic data for basic testing',
                'ENABLE_MULTI_FREQUENCY': False,
                'WEBSOCKET_PER_SECOND_ENABLED': True,
                'WEBSOCKET_PER_MINUTE_ENABLED': False,
                'WEBSOCKET_FAIR_VALUE_ENABLED': False,
                'SYNTHETIC_ACTIVITY_LEVEL': 'low',
                'SYNTHETIC_PER_SECOND_FREQUENCY': 5.0,  # Every 5 seconds
                'ENABLE_SYNTHETIC_DATA_VALIDATION': False
            }
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
        logger.info(f"Applying synthetic data preset '{preset_name}': {preset_config['description']}")
        
        # Apply preset configuration
        changes_made = 0
        for key, value in preset_config.items():
            if key != 'description':  # Skip the description field
                if self.config.get(key) != value:
                    self.config[key] = value
                    changes_made += 1
        
        if changes_made > 0:
            logger.info(f"Applied {changes_made} configuration changes from preset '{preset_name}'")
            self._notify_configuration_change()
        else:
            logger.info(f"Preset '{preset_name}' already active, no changes needed")
        
        return True
    
    def validate_synthetic_data_config(self) -> Tuple[bool, List[str]]:
        """
        Validate synthetic data configuration for consistency.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check if multi-frequency is enabled but no frequencies are active
        if self.config.get('ENABLE_MULTI_FREQUENCY', False):
            active_frequencies = 0
            if self.config.get('WEBSOCKET_PER_SECOND_ENABLED', False):
                active_frequencies += 1
            if self.config.get('WEBSOCKET_PER_MINUTE_ENABLED', False):
                active_frequencies += 1
            if self.config.get('WEBSOCKET_FAIR_VALUE_ENABLED', False):
                active_frequencies += 1
            
            if active_frequencies == 0:
                errors.append("Multi-frequency enabled but no frequency streams are active")
        
        # Validate frequency intervals
        per_second_freq = self.config.get('SYNTHETIC_PER_SECOND_FREQUENCY', 1.0)
        if per_second_freq < 0.1 or per_second_freq > 60.0:
            errors.append(f"Per-second frequency {per_second_freq} outside valid range (0.1-60.0)")
        
        fmv_interval = self.config.get('SYNTHETIC_FMV_UPDATE_INTERVAL', 30)
        if fmv_interval < 5 or fmv_interval > 300:
            errors.append(f"FMV update interval {fmv_interval} outside valid range (5-300 seconds)")
        
        # Validate correlation parameters
        correlations = [
            ('SYNTHETIC_FMV_CORRELATION', 0.85),
            ('SYNTHETIC_FMV_TRENDING_CORRELATION', 0.90),
            ('SYNTHETIC_FMV_SIDEWAYS_CORRELATION', 0.75),
            ('SYNTHETIC_FMV_VOLATILE_CORRELATION', 0.65)
        ]
        
        for param, default in correlations:
            value = self.config.get(param, default)
            if not (0.0 <= value <= 1.0):
                errors.append(f"Correlation parameter {param} ({value}) outside valid range (0.0-1.0)")
        
        # Validate tolerance parameters
        tolerances = [
            ('VALIDATION_PRICE_TOLERANCE', 0.001, 0.0001, 0.01),
            ('VALIDATION_VOLUME_TOLERANCE', 0.05, 0.001, 0.20),
            ('VALIDATION_VWAP_TOLERANCE', 0.002, 0.0001, 0.01)
        ]
        
        for param, default, min_val, max_val in tolerances:
            value = self.config.get(param, default)
            if not (min_val <= value <= max_val):
                errors.append(f"Tolerance parameter {param} ({value}) outside valid range ({min_val}-{max_val})")
        
        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Synthetic data configuration validation failed: {len(errors)} errors")
        
        return is_valid, errors
    
    def set_synthetic_data_intervals(self, per_second_interval: float = 1.0, 
                                   per_minute_interval: int = 60, 
                                   fmv_interval: int = 30) -> bool:
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
            logger.error(f"Per-second interval {per_second_interval} outside valid range (0.1-60.0)")
            return False
            
        if not (30 <= per_minute_interval <= 300):
            logger.error(f"Per-minute interval {per_minute_interval} outside valid range (30-300)")
            return False
            
        if not (5 <= fmv_interval <= 300):
            logger.error(f"FMV interval {fmv_interval} outside valid range (5-300)")
            return False
        
        # Set the intervals
        self.config['SYNTHETIC_PER_SECOND_FREQUENCY'] = per_second_interval
        self.config['SYNTHETIC_MINUTE_WINDOW'] = per_minute_interval
        self.config['SYNTHETIC_FMV_UPDATE_INTERVAL'] = fmv_interval
        
        logger.info(
            f"CONFIG: Set synthetic data intervals - "
            f"Per-second: {per_second_interval}s, "
            f"Per-minute: {per_minute_interval}s, "
            f"FMV: {fmv_interval}s"
        )
        
        return True
    
    def get_common_interval_presets(self) -> Dict[str, Dict[str, float]]:
        """
        Get common interval presets for testing (15s, 30s, 60s as mentioned in PRD).
        
        Returns:
            Dict of preset configurations with different interval combinations
        """
        return {
            'fast_15s': {
                'description': '15-second intervals for rapid testing',
                'per_second_interval': 15.0,
                'per_minute_interval': 60,
                'fmv_interval': 15
            },
            'standard_30s': {
                'description': '30-second intervals for standard testing',
                'per_second_interval': 30.0,
                'per_minute_interval': 60, 
                'fmv_interval': 30
            },
            'slow_60s': {
                'description': '60-second intervals for slow testing',
                'per_second_interval': 60.0,
                'per_minute_interval': 60,
                'fmv_interval': 60
            },
            'mixed_intervals': {
                'description': 'Mixed intervals (15s per-second, 30s FMV, 60s per-minute)',
                'per_second_interval': 15.0,
                'per_minute_interval': 60,
                'fmv_interval': 30
            },
            'high_frequency': {
                'description': 'High frequency testing (5s per-second, 15s FMV)', 
                'per_second_interval': 5.0,
                'per_minute_interval': 60,
                'fmv_interval': 15
            }
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
            per_second_interval=preset['per_second_interval'],
            per_minute_interval=preset['per_minute_interval'], 
            fmv_interval=preset['fmv_interval']
        )