"""
Flask Application Configuration
Handles Flask app creation, configuration layering, and extension initialization.
"""

import os
import logging
from flask import Flask
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate 

logger = logging.getLogger(__name__)


def create_flask_app(env_config, cache_control, config):
    """Create and configure Flask application."""
    
    logger.info("Creating Flask application")
    
    # Get the project root directory (parent of config folder)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create Flask app with absolute paths
    app = Flask(__name__, 
                static_folder=os.path.join(project_root, 'web/static'),
                template_folder=os.path.join(project_root, 'web/templates/pages'))
    
    # Get cached settings
    app_settings = cache_control.get_cache('app_settings') or {}
    
    # Apply configuration - environment variables take precedence over cache
    configure_app_settings(app, env_config, app_settings, config)
    
    logger.info("Flask application configured with %d cached settings", len(app_settings))
    logger.info(f"Template folder: {app.template_folder}")
    logger.info(f"Static folder: {app.static_folder}")
    
    return app


def configure_app_settings(app, env_config, app_settings, config):
    """Configure Flask application settings from multiple sources."""
    
    # Core Flask settings
    app.config['SECRET_KEY'] = config.get('FLASK_SECRET_KEY', 
                                        app_settings.get('SECRET_KEY', 
                                                       os.urandom(16).hex()))
    
    # Database configuration - ALWAYS from environment
    app.config['SQLALCHEMY_DATABASE_URI'] = env_config['DATABASE_URI']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = app_settings.get('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    
    # Mail settings - cache with config fallbacks
    app.config['MAIL_SERVER'] = app_settings.get('MAIL_SERVER', 
                                                config.get('MAIL_SERVER', '127.0.0.1'))
    app.config['MAIL_PORT'] = app_settings.get('MAIL_PORT', 
                                              config.get('MAIL_PORT', 1025))
    app.config['MAIL_USE_TLS'] = app_settings.get('MAIL_USE_TLS', 
                                                 config.get('MAIL_USE_TLS', False))
    app.config['MAIL_USE_SSL'] = app_settings.get('MAIL_USE_SSL', 
                                                 config.get('MAIL_USE_SSL', False))
    app.config['MAIL_DEFAULT_SENDER'] = app_settings.get('MAIL_DEFAULT_SENDER', 
                                                        config.get('MAIL_DEFAULT_SENDER', 'noreply@tickstock.com'))
    app.config['MAIL_TIMEOUT'] = app_settings.get('MAIL_TIMEOUT', 
                                                 config.get('MAIL_TIMEOUT', 10))
    
    # Server settings - cache with environment fallbacks
    app.config['SERVER_NAME'] = app_settings.get('SERVER_NAME', 
                                                f"{env_config['APP_HOST']}:{env_config['APP_PORT']}")
    app.config['BASE_URL'] = app_settings.get('BASE_URL', 
                                             f"http://{env_config['APP_HOST']}:{env_config['APP_PORT']}")
    
    # SMS configuration from config manager
    app.config['SMS_TEST_MODE'] = config.get('SMS_TEST_MODE', True)
    app.config['TWILIO_ACCOUNT_SID'] = config.get('TWILIO_ACCOUNT_SID', '')
    app.config['TWILIO_AUTH_TOKEN'] = config.get('TWILIO_AUTH_TOKEN', '')
    app.config['TWILIO_PHONE_NUMBER'] = config.get('TWILIO_PHONE_NUMBER', '+15551234567')
    app.config['SMS_VERIFICATION_CODE_LENGTH'] = config.get('SMS_VERIFICATION_CODE_LENGTH', 6)
    app.config['SMS_VERIFICATION_CODE_EXPIRY'] = config.get('SMS_VERIFICATION_CODE_EXPIRY', 10)
    app.config['RENEWAL_SMS_MAX_ATTEMPTS'] = config.get('RENEWAL_SMS_MAX_ATTEMPTS', 3)
    app.config['RENEWAL_SMS_LOCKOUT_MINUTES'] = config.get('RENEWAL_SMS_LOCKOUT_MINUTES', 15)

    # 🆕 PHASE 2.2: Dual Universe Analytics Aggregation Configuration
    app.config['ANALYTICS_GAUGE_AGGREGATION_SECONDS'] = config.get('ANALYTICS_GAUGE_AGGREGATION_SECONDS', 10)
    app.config['ANALYTICS_VERTICAL_AGGREGATION_SECONDS'] = config.get('ANALYTICS_VERTICAL_AGGREGATION_SECONDS', 10)
    app.config['ANALYTICS_DATABASE_SYNC_SECONDS'] = config.get('ANALYTICS_DATABASE_SYNC_SECONDS', 10)
    app.config['ANALYTICS_PRODUCTION_GAUGE_SECONDS'] = config.get('ANALYTICS_PRODUCTION_GAUGE_SECONDS', 60)
    app.config['ANALYTICS_PRODUCTION_VERTICAL_SECONDS'] = config.get('ANALYTICS_PRODUCTION_VERTICAL_SECONDS', 60)
    app.config['ANALYTICS_PRODUCTION_DATABASE_SECONDS'] = config.get('ANALYTICS_PRODUCTION_DATABASE_SECONDS', 60)
    app.config['ANALYTICS_EMIT_MODE'] = config.get('ANALYTICS_EMIT_MODE', 'continuous_with_hold')
    app.config['ANALYTICS_AGGREGATION_BATCH_SIZE'] = config.get('ANALYTICS_AGGREGATION_BATCH_SIZE', 4)
    app.config['ANALYTICS_GAUGE_ALPHA'] = config.get('ANALYTICS_GAUGE_ALPHA', 0.3)
    app.config['ANALYTICS_VERTICAL_BASE_ALPHA'] = config.get('ANALYTICS_VERTICAL_BASE_ALPHA', 0.2)

def initialize_flask_extensions(app):
    """Initialize Flask extensions."""
    
    logger.info("Initializing Flask extensions")
    
    # Initialize extensions
    from src.infrastructure.database import db
    
    mail = Mail(app)
    csrf = CSRFProtect(app)
    db.init_app(app)
    
    # ADD FLASK-MIGRATE INITIALIZATION
    migrate = Migrate(app, db)
    
    # Configure login manager (existing code stays the same)
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message = None
    
    @login_manager.user_loader
    def load_user(user_id):
        from src.infrastructure.database import User
        return User.query.get(int(user_id))
    
    # Log configuration (existing code stays the same)
    logger.debug("Flask-Mail settings: server=%s, port=%d, use_tls=%s, use_ssl=%s, sender=%s, timeout=%d",
                app.config['MAIL_SERVER'], app.config['MAIL_PORT'],
                app.config['MAIL_USE_TLS'], app.config['MAIL_USE_SSL'],
                app.config['MAIL_DEFAULT_SENDER'], app.config['MAIL_TIMEOUT'])
    
    return {
        'mail': mail,
        'csrf': csrf,
        'db': db,
        'login_manager': login_manager,
        'migrate': migrate  # ADD THIS LINE
    }

def initialize_socketio(app, cache_control, config):
    """Initialize SocketIO with Redis configuration."""
    
    logger.info("Initializing SocketIO")
    
    # Get Redis configuration from environment config (not cache)
    redis_url = config.get('REDIS_URL')
    
    # Check if Redis should be used
    use_redis = False
    if redis_url and redis_url.strip():
        logger.info(f"SocketIO: Attempting to connect to Redis at {redis_url}")
        try:
            import redis
            test_client = redis.Redis.from_url(redis_url, socket_timeout=2, socket_connect_timeout=2)
            test_client.ping()
            use_redis = True
            logger.info(f"Redis is available at {redis_url}, using for SocketIO message queue")
        except Exception as e:
            logger.warning(f"Redis connection failed, falling back to in-memory queue: {e}")
            redis_url = None
    else:
        logger.info("SocketIO: No Redis URL configured, using in-memory message queue")
    
    # Create SocketIO instance
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        ping_timeout=60,
        ping_interval=10,
        max_http_buffer_size=5*1024*1024,
        message_queue=redis_url if use_redis else None
    )
    
    logger.info("SocketIO initialized with %s message queue", "Redis" if use_redis else "in-memory")
    
    return socketio