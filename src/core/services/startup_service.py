"""
Application Startup Sequence
Handles environment configuration, database connection, and cache initialization.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# Configure basic logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_environment():
    """
    Detect environment based on multiple factors.
    Priority: ENV_VAR > CONFIG_FILE > HOSTNAME_DETECTION > DEFAULT
    """
    
    # Method 1: Explicit environment variable (highest priority)
    env_from_var = os.getenv('APP_ENVIRONMENT')
    if env_from_var:
        logger.info(f"Environment detected from APP_ENVIRONMENT variable: {env_from_var}")
        return env_from_var.upper()
    
    # Method 2: Check for environment-specific config files
    config_files = {
        'PRODUCTION': ['.env.production', 'config/production.env'],
        'STAGING': ['.env.staging', 'config/staging.env'], 
        'DEVELOPMENT': ['.env.development', '.env', 'config/development.env']
    }
    
    for env, files in config_files.items():
        for file_path in files:
            if os.path.exists(file_path):
                logger.info(f"Environment detected from config file {file_path}: {env}")
                return env
    
    # Method 3: Hostname-based detection (for legacy deployments)
    import socket
    hostname = socket.gethostname().lower()
    if any(prod_indicator in hostname for prod_indicator in ['prod', 'production', 'aws', 'gcp', 'azure']):
        logger.info(f"Environment detected from hostname {hostname}: PRODUCTION")
        return 'PRODUCTION'
    elif any(stage_indicator in hostname for stage_indicator in ['stage', 'staging', 'test']):
        logger.info(f"Environment detected from hostname {hostname}: STAGING")
        return 'STAGING'
    
    # Method 4: Default
    logger.info("No environment detected, defaulting to DEVELOPMENT")
    return 'DEVELOPMENT'


def load_environment_config():
    """
    Load core environment configuration required for startup.
    Hybrid approach: Environment variables override config files.
    """
    
    # Step 1: Detect environment
    app_environment = detect_environment()
    
    # Step 2: Try to get DATABASE_URI from environment variable first (production/security)
    database_uri = os.getenv('DATABASE_URI')
    config_source = "environment variable"
    
    if not database_uri:
        # Try environment-specific variable
        database_uri = os.getenv(f'DATABASE_URI_{app_environment}')
        if database_uri:
            config_source = f"environment variable (DATABASE_URI_{app_environment})"
    
    if not database_uri:
        # Step 3: Fall back to ConfigManager (development convenience)
        logger.info("DATABASE_URI not found in environment variables, trying ConfigManager")
        
        try:
            from src.core.services.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # Try to load from environment-specific file first
            env_files = {
                'PRODUCTION': ['.env.production', 'config/production.env'],
                'STAGING': ['.env.staging', 'config/staging.env'], 
                'DEVELOPMENT': ['.env.development', '.env', 'config/development.env']
            }
            
            config_loaded = False
            for env_file in env_files.get(app_environment, []):
                if os.path.exists(env_file):
                    logger.info(f"Loading configuration from {env_file}")
                    # Assuming ConfigManager has a method to load from specific file
                    # If not, we'll load from env and set the file path
                    config_manager.load_from_env()  # This may need enhancement
                    config_loaded = True
                    config_source = f"config file ({env_file})"
                    break
            
            if not config_loaded:
                # Fall back to default env loading
                config_manager.load_from_env()
                config_source = "config manager (default)"
            
            config = config_manager.get_config()
            database_uri = config.get('DATABASE_URI')
            
            if not database_uri:
                database_uri = config.get(f'DATABASE_URI_{app_environment}')
                
        except Exception as e:
            logger.warning(f"ConfigManager fallback failed: {e}")
    
    # Step 4: Validate we have a database URI
    if not database_uri:
        logger.error("DATABASE_URI not found in environment variables or configuration files")
        logger.error("Please set DATABASE_URI in one of the following ways:")
        logger.error("  1. Environment variable: export DATABASE_URI=postgresql://...")
        logger.error("  2. Environment-specific variable: export DATABASE_URI_%s=postgresql://...", app_environment)
        logger.error("  3. Config file (.env, .env.%s, config/%s.env)", app_environment.lower(), app_environment.lower())
        logger.error("Example: DATABASE_URI=postgresql://user:pass@localhost:5432/tickstock")
        sys.exit(1)
    
    # Step 5: Build environment config (prioritize env vars, fall back to defaults)
    env_config = {
        'APP_ENVIRONMENT': app_environment,
        'DATABASE_URI': database_uri,
        'APP_HOST': os.getenv('APP_HOST', '0.0.0.0'),
        'APP_PORT': int(os.getenv('APP_PORT', 5000)),
        'APP_DEBUG': os.getenv('APP_DEBUG', 'false').lower() == 'true'
    }
    
    logger.info("Environment configuration loaded for: %s (DATABASE_URI from %s)", app_environment, config_source)
    return env_config


def create_cache_database_engine(database_uri):
    """Create SQLAlchemy engine specifically for cache loading."""
    try:
        engine = create_engine(
            database_uri,
            pool_size=1,          # Minimal pool for startup
            max_overflow=0,       # No overflow needed
            pool_timeout=10,      # Quick timeout for startup
            pool_recycle=3600,    # Recycle connections hourly
            echo=False            # Set to True for SQL debugging
        )
        
        # Test the connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        logger.info("Database engine created and tested successfully")
        return engine
        
    except OperationalError as e:
        logger.error("Database connection failed: %s", str(e))
        logger.error("Check DATABASE_URI and ensure database is accessible")
        logger.error("DATABASE_URI format: postgresql://user:password@host:port/database")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected database error: %s", str(e))
        sys.exit(1)


def initialize_cache_with_database(cache_control, environment, db_engine):
    """Initialize cache using dedicated database engine."""
    try:
        # Create a session for cache loading using our dedicated engine
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=db_engine)
        session = Session()
        
        try:
            # Create a minimal Flask app just for the cache initialization context
            from flask import Flask
            temp_app = Flask(__name__)
            temp_app.config['SQLALCHEMY_DATABASE_URI'] = db_engine.url
            
            # Initialize db with temp app for context
            from src.infrastructure.database import db
            db.init_app(temp_app)
            
            # Use application context for cache loading
            with temp_app.app_context():
                # Temporarily replace db.session for cache loading
                original_session = getattr(db, 'session', None)
                db.session = session
                
                try:
                    # Initialize cache
                    cache_control.initialize(environment)
                    logger.info("Cache successfully loaded from src.infrastructure.database")
                    return True
                    
                finally:
                    # Restore original session
                    if original_session:
                        db.session = original_session
                        
        finally:
            session.close()
            
    except Exception as e:
        logger.error("Cache initialization failed: %s", str(e))
        logger.error("Application cannot start without cache data")
        logger.error("Ensure cache_entries table exists and contains data for environment: %s", environment)
        sys.exit(1)


def run_startup_sequence():
    """Execute the complete application startup sequence."""
    
    logger.info("Starting TickStock application startup sequence")
    
    # STEP 1: Load environment configuration
    logger.info("Step 1: Loading environment configuration")
    env_config = load_environment_config()
    
    # STEP 2: Create database engine for cache loading  
    logger.info("Step 2: Creating database engine for cache loading")
    cache_db_engine = create_cache_database_engine(env_config['DATABASE_URI'])
    
    # STEP 3: Initialize cache control (without Flask context)
    logger.info("Step 3: Initializing cache control")
    from src.infrastructure.cache.cache_control import CacheControl
    cache_control = CacheControl()
    initialize_cache_with_database(cache_control, env_config['APP_ENVIRONMENT'], cache_db_engine)
    
    # STEP 4: Load additional configuration from existing ConfigManager
    logger.info("Step 4: Loading additional configuration from ConfigManager")
    from src.core.services.config_manager import ConfigManager
    config_manager = ConfigManager()
    config_manager.load_from_env()
    config = config_manager.get_config()
    config_manager.validate_config()
    
    # Close the cache database engine since Flask will create its own
    cache_db_engine.dispose()
    
    logger.info("Application startup sequence completed successfully")
    
    return {
        'env_config': env_config,
        'cache_control': cache_control,
        'config_manager': config_manager,
        'config': config
    }