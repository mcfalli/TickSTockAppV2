"""
Database Configuration for TickStockAppV2 Development Tools
==========================================================

Configuration settings for database integrity checker and other dev tools.
"""

from typing import Any

from src.core.services.config_manager import get_config

# Get configuration
try:
    config = get_config()
except:
    config = None

def get_database_config() -> dict[str, Any]:
    """Get database configuration from TickStockAppV2 .env file values"""

    return {
        # Connection parameters from .env DATABASE_URI
        # config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')
        'host': 'localhost',
        'port': '5432',
        'database': 'tickstock',
        'user': 'app_readwrite',
        'password': 'PASSWORD_PLACEHOLDER',

        # Connection pool settings
        'minconn': 1,
        'maxconn': 10,
        'connect_timeout': 30,

        # SSL settings
        'sslmode': 'prefer',
    }

def get_test_patterns() -> dict[str, Any]:
    """Get test patterns and expected data for validation"""

    return {
        # Expected Sprint 23 objects
        'sprint23_tables': [
            'market_conditions',
            'pattern_correlations_cache',
            'temporal_performance_cache',
            'advanced_metrics_cache'
        ],

        'sprint23_functions': [
            'calculate_pattern_correlations',
            'analyze_temporal_performance',
            'analyze_pattern_market_context',
            'calculate_advanced_pattern_metrics',
            'compare_pattern_performance',
            'generate_pattern_prediction_signals',
            'refresh_correlations_cache',
            'refresh_temporal_cache',
            'refresh_advanced_metrics_cache',
            'refresh_all_analytics_cache',
            'refresh_analytics_views'
        ],

        'sprint23_views': [
            'v_current_market_conditions'
        ],

        'sprint23_materialized_views': [
            'mv_active_patterns_summary',
            'mv_pattern_correlation_summary'
        ],

        'sprint23_indexes': [
            'idx_market_conditions_timestamp',
            'idx_market_conditions_analysis',
            'idx_market_conditions_temporal',
            'idx_correlations_cache_lookup',
            'idx_temporal_cache_lookup',
            'idx_advanced_cache_lookup'
        ],

        # Minimum expected data counts
        'min_market_conditions_records': 5,
        'min_pattern_definitions': 2,

        # Performance thresholds
        'max_query_time_ms': 100,
        'max_analytics_query_time_ms': 200,
    }

# Environment-specific configurations
ENVIRONMENTS = {
    'development': {
        'debug': True,
        'check_timescaledb': True,
        'require_sample_data': True,
    },

    'testing': {
        'debug': True,
        'check_timescaledb': False,
        'require_sample_data': True,
    },

    'production': {
        'debug': False,
        'check_timescaledb': True,
        'require_sample_data': False,
    }
}

def get_environment_config(env: str = 'development') -> dict[str, Any]:
    """Get environment-specific configuration"""
    return ENVIRONMENTS.get(env, ENVIRONMENTS['development'])
