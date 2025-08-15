# auth/session.py
from flask import request
from flask_login import current_user
from src.infrastructure.database.models.base.base import Session, db
from datetime import datetime, timedelta, timezone
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.AUTH_SESSION, 'session')

class SessionManager:
    def __init__(self):
        self.max_sessions_per_user = 1  # Default value
        self.session_expiry_days = 1  # Default value 
        logger.debug("SessionManager initialized with default settings")
        self.session_duration = None  # Loaded from CacheControl

    def load_settings(self, cache_control):
        try:
            # First try to get from cache_control for environment-specific settings
            app_settings = cache_control.get_cache('app_settings') or {}
            
            # Get config from ConfigManager for application defaults if not in cache
            from src.core.services.config_manager import get_config
            config = get_config()
            
            self.max_sessions_per_user = app_settings.get('MAX_SESSIONS_PER_USER', 
                                                        config.get('MAX_SESSIONS_PER_USER', 1))
            self.session_expiry_days = app_settings.get('SESSION_EXPIRY_DAYS', 
                                                    config.get('SESSION_EXPIRY_DAYS', 1))
            
            logger.debug("SessionManager settings loaded: max_sessions=%s, expiry_days=%s", 
                        self.max_sessions_per_user, self.session_expiry_days)
        except Exception as e:
            logger.error(f"Error loading session settings: {e}")
            # Fall back to defaults
            self.max_sessions_per_user = 1
            self.session_expiry_days = 1
        
    def create_session(self, user_id, fingerprint_data=None, ip_address=None):
        try:
            # First invalidate all previous sessions to enforce single session policy
            self.invalidate_prior_sessions(user_id)
            
            # Create new session
            from flask import request
            now = datetime.now(timezone.utc)
            user_agent_string = 'Unknown'
            if ip_address is None:
                ip_address = '0.0.0.0'  # Default if not provided
                
            # Try to get user agent if in a request context
            try:
                user_agent_string = request.user_agent.string
            except Exception:
                # Not in a request context or no user agent
                pass
                
            session = Session(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent_string,
                fingerprint=fingerprint_data,
                status='active',
                created_at=now,
                last_active_at=now,
                expires_at=now + timedelta(days=self.session_expiry_days)
            )
            
            # Generate refresh token
            import secrets
            refresh_token = secrets.token_urlsafe(64)
            
            try:
                db.session.add(session)
                db.session.commit()
                session.set_refresh_token(refresh_token)
                return session
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                db.session.rollback()
                return None
                
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    def invalidate_prior_sessions(self, user_id):
        """Invalidate all other sessions for this user."""
        try:
            now = datetime.now(timezone.utc)
            sessions = Session.query.filter_by(
                user_id=user_id,
                status='active'
            ).all()
            
            invalidated_count = 0
            for session in sessions:
                session.status = 'expired'
                session.expires_at = now
                invalidated_count += 1
                
            db.session.commit()
            logger.info(f"Invalidated {invalidated_count} previous sessions for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate prior sessions: {e}")
            db.session.rollback()
            return False

    def invalidate_all_sessions(self, user_id):
        """Invalidate all sessions for the user."""
        try:
            sessions = Session.query.filter_by(user_id=user_id).all()
            for session in sessions:
                session.status = 'inactive'
                session.expires_at = datetime.utcnow()
            db.session.commit()
            logger.debug(f"Invalidated all sessions for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating all sessions for {user_id}: {e}")
            return False

    def get_current_user_id(self):
        """Get the current user's ID."""
        return current_user.id if current_user.is_authenticated else None
    

    def detect_concurrent_login(self, user_id, session_id):
        """Detect if someone tries to login while user already has an active session."""
        try:
            active_sessions = Session.query.filter(
                Session.user_id == user_id,
                Session.status == 'active',
                Session.session_id != session_id,
                Session.expires_at > datetime.now(timezone.utc)
            ).all()
            
            if active_sessions:
                # Log and alert about concurrent login attempt
                logger.warning(f"Concurrent login detected for user {user_id}. Existing sessions: {len(active_sessions)}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error detecting concurrent login: {e}")
            return False
    def monitor_suspicious_logins(self, user_id, current_session_id, new_ip_address, new_fingerprint_data):
        """Monitor for suspicious login patterns even when enforcing single session."""
        try:
            # Get most recent session before this one 
            previous_session = Session.query.filter(
                Session.user_id == user_id,
                Session.session_id != current_session_id,
                Session.status == 'expired'  # Looking at recently expired sessions
            ).order_by(Session.last_active_at.desc()).first()
            
            if previous_session and previous_session.last_active_at > datetime.now(timezone.utc) - timedelta(minutes=5):
                # Session less than 5 minutes old was terminated
                # Check if IP address or fingerprint is different
                if (previous_session.ip_address != new_ip_address or 
                        previous_session.fingerprint != new_fingerprint_data):
                    
                    # Log suspicious rapid session change from different location/device
                    logger.warning(
                        f"Suspicious login detected for user {user_id}. "
                        f"Previous session from {previous_session.ip_address} ended "
                        f"{datetime.now(timezone.utc) - previous_session.last_active_at} ago. "
                        f"New login from {new_ip_address}."
                    )
                    
                    # You could also trigger security alerts here
                    from src.infrastructure.messaging.email_service import EmailManager
                    from flask import current_app
                    from src.infrastructure.database import User
                    
                    user = User.query.get(user_id)
                    if user:
                        email_manager = EmailManager(current_app.extensions['mail'])
                        email_manager.send_security_alert_email(
                            user.email, 
                            'New login detected', 
                            f"Your account was accessed from a new location: {new_ip_address}",
                            previous_ip=previous_session.ip_address,
                            current_ip=new_ip_address,
                            timestamp=datetime.now(timezone.utc).isoformat()
                        )
                    
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error monitoring suspicious logins: {e}")
            return False
    
    def check_login_security(self, user_id, ip_address, fingerprint_data):
        """Check for suspicious login activity after successful authentication."""
        try:
            from src.infrastructure.database import Session
            
            # Get the most recent active session
            current_session = Session.query.filter_by(
                user_id=user_id, 
                status='active'
            ).order_by(Session.created_at.desc()).first()
            
            if current_session:
                return self.monitor_suspicious_logins(
                    user_id, 
                    current_session.session_id, 
                    ip_address, 
                    fingerprint_data
                )
            return False
        except Exception as e:
            logger.error(f"Error checking login security: {e}")
            return False
    