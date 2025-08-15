# authentication.py (updated check_rate_limit and login)
from flask import flash, url_for
from flask_login import login_user, logout_user
from src.infrastructure.database import User, db
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta, timezone
from config.logging_config import get_domain_logger, LogDomain
import random
import string

logger = get_domain_logger(LogDomain.AUTH_SESSION, 'authentication')

class AuthenticationManager:
    def __init__(self, app_secret_key, mail):
        self.max_attempts = None
        self.lockout_duration = timedelta(minutes=20)
        self.max_lockouts = 3
        self.failed_attempts = {}
        self.serializer = URLSafeTimedSerializer(app_secret_key)
        self.mail = mail
        logger.debug(f"AuthenticationManager initialized with mail: {mail}")

    def load_settings(self, cache_control):
        try:
            # First try to get from cache_control for environment-specific settings
            app_settings = cache_control.get_cache('app_settings') or {}
            
            # Get config from ConfigManager for application defaults if not in cache
            from src.core.services.config_manager import get_config
            config = get_config()
            
            # Load all authentication settings
            self.max_attempts = app_settings.get('MAX_LOGIN_ATTEMPTS', 
                                            config.get('MAX_LOGIN_ATTEMPTS', 5))
            
            lockout_minutes = app_settings.get('LOCKOUT_DURATION_MINUTES', 
                                            config.get('LOCKOUT_DURATION_MINUTES', 20))
            self.lockout_duration = timedelta(minutes=lockout_minutes)
            
            self.max_lockouts = app_settings.get('MAX_LOCKOUTS', 
                                            config.get('MAX_LOCKOUTS', 3))
            
            self.password_reset_salt = config.get('PASSWORD_RESET_SALT', 'password-reset')
            
            # Update serializer if salt changed
            self.serializer = URLSafeTimedSerializer(self.serializer.secret_key, 
                                                salt=self.password_reset_salt)
            
            logger.debug("AuthenticationManager settings loaded: max_attempts=%s, "
                        "lockout_minutes=%s, max_lockouts=%s", 
                        self.max_attempts, lockout_minutes, self.max_lockouts)
        except Exception as e:
            logger.error(f"Error loading authentication settings: {e}")
            # Fall back to defaults
            self.max_attempts = 5
            self.lockout_duration = timedelta(minutes=20)
            self.max_lockouts = 3

    def generate_reset_token(self, email):
        return self.serializer.dumps(email, salt='password-reset')

    def verify_reset_token(self, token, max_age=3600):
        try:
            email = self.serializer.loads(token, salt='password-reset', max_age=max_age)
            return email
        except Exception as e:
            logger.error(f"Invalid or expired reset token: {e}")
            return None

    def validate_captcha(self, captcha_response):
        """Validate CAPTCHA stub (mirrors RegistrationManager)."""
        logger.debug("Validating CAPTCHA stub: Checking checkbox")
        return captcha_response == 'on'

    def initiate_password_reset(self, email):
        """Update to send both email and SMS verification."""
        from src.infrastructure.messaging.email_service import EmailManager
        from src.infrastructure.messaging.sms_service import SMSManager
        from flask import current_app
        
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found with that email")
            logger.warning(f"Password reset attempted for non-existent email: {email}")
            return False
        if not user.is_verified:
            flash("Please verify your email before resetting your password")
            logger.warning(f"Password reset attempted for unverified user: {email}")
            return False
        try:
            # Generate email token
            token = self.generate_reset_token(email)
            reset_url = url_for('reset_password', token=token, _external=True)
            
            # Generate SMS verification code
            code_length = current_app.config.get('SMS_VERIFICATION_CODE_LENGTH', 6)
            verification_code = self.generate_verification_code(code_length)
            
            # Store verification code
            expiry_minutes = current_app.config.get('SMS_VERIFICATION_CODE_EXPIRY', 10)
            if not self.store_verification_code(user.id, verification_code, expiry_minutes):
                logger.error(f"Failed to store verification code for {email}")
                flash("Failed to initiate password reset. Please try again later.")
                return False
            
            # Send SMS if phone is available
            sms_sent = False
            is_test_mode = current_app.config.get('SMS_TEST_MODE', True)
            
            if user.phone:
                sms_manager = SMSManager(current_app)
                sms_sent = sms_manager.send_verification_code(user.id, user.phone, verification_code)
                if not sms_sent:
                    logger.warning(f"Failed to send verification code to {user.phone}")
                    # We'll still continue with email
            
            # Send reset email
            email_manager = EmailManager(self.mail)
            email_sent = email_manager.send_reset_email(user.email, reset_url)
            
            if email_sent:
                logger.info(f"Password reset email sent for {email}: {reset_url}")
                
                # Different message based on test mode and SMS success
                if sms_sent:
                    if is_test_mode:
                        flash("Password reset initiated. Check your email for instructions and for the verification code (SMS test mode).")
                    else:
                        flash("Password reset initiated. Check your email for instructions and enter the verification code sent to your phone.")
                else:
                    flash("Password reset initiated. Check your email for instructions.")
                    
                return True
            else:
                logger.error(f"Failed to send password reset email for {email}")
                flash("Failed to send reset email. Please try again later.")
                return False
        except Exception as e:
            logger.error(f"Error initiating password reset for {email}: {e}", exc_info=True)
            flash("An error occurred while initiating password reset")
            return False

    def change_password(self, user, current_password, new_password, captcha_response=None):
        from src.auth.registration import RegistrationManager
        from src.infrastructure.messaging.email_service import EmailManager
        try:
            if not user.is_authenticated:
                logger.error("Password change attempted by unauthenticated user")
                flash("Please log in to change your password")
                return False

            user_email = user.email  # Store email before any logout
            if captcha_response and not self.validate_captcha(captcha_response):
                flash("Please complete the CAPTCHA")
                logger.debug(f"Password change failed for {user_email}: Invalid CAPTCHA")
                return False

            logger.debug(f"Checking current password for {user_email}")
            if not user.check_password(current_password):
                logger.debug(f"Password change failed for {user_email}: Incorrect current password")
                flash("Current password is incorrect")
                return False

            registration_manager = RegistrationManager(self.serializer.secret_key, None)
            logger.debug(f"Validating inputs for {user_email}: email={user.email}, username={user.username}, password=[REDACTED], phone=None")
            errors = registration_manager.validate_inputs(
                email=user.email, username=user.username, password=new_password, phone=None
            )
            if errors:
                for error in errors:
                    flash(error)
                logger.debug(f"Password change failed for {user_email}: Validation errors: {errors}")
                return False

            user.set_password(new_password)
            db.session.commit()
            logger.info(f"Password changed for user: {user_email}")

            # Send confirmation email
            email_manager = EmailManager(self.mail)
            success = email_manager.send_change_password_email(
                user.email, user.username, datetime.now(timezone.utc).isoformat()
            )
            if not success:
                logger.warning(f"Failed to send change password email to {user_email}")
                flash("Password changed, but failed to send confirmation email")
            else:
                flash("Password changed successfully. Check your email for confirmation.")

            # Terminate all sessions
            from src.auth.session import SessionManager
            session_manager = SessionManager()
            session_manager.invalidate_all_sessions(user.id)
            logout_user()
            logger.info(f"All sessions terminated for user: {user_email}")

            return True
        except Exception as e:
            logger.error(f"Error changing password for {getattr(user, 'email', 'unknown')}: {e}", exc_info=True)
            db.session.rollback()
            flash("An error occurred while changing password")
            return False

    def reset_password(self, user, new_password, captcha_response=None):
        from src.infrastructure.messaging.email_service import EmailManager
        try:
            if captcha_response and not self.validate_captcha(captcha_response):
                flash("Please complete the CAPTCHA")
                return False
                
            # Only validate password requirements, not phone number
            # Using a more targeted approach instead of the full registration validation
            if not new_password or len(new_password) < 8 or len(new_password) > 64:
                flash("Password must be 8-64 characters")
                return False
                
            import re
            if not re.search(r"[A-Za-z]", new_password) or not re.search(r"[0-9]", new_password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
                flash("Password must include letters, numbers, and special characters")
                return False
                
            # Check for common passwords
            if new_password.lower() in {'password', 'password123', '12345678', 'qwerty'}:
                flash("Password is too common")
                return False
                
            user.set_password(new_password)
            db.session.commit()
            logger.info(f"Password reset for user: {user.email}")
            
            # Send confirmation email
            email_manager = EmailManager(self.mail)
            from datetime import datetime, timezone
            change_time = datetime.now(timezone.utc).isoformat()
            success = email_manager.send_change_password_email(
                user.email, 
                user.username, 
                change_time
            )
            
            if not success:
                logger.warning(f"Failed to send password change confirmation email to {user.email}")
                # Don't flash message here as it would appear on login page after redirect
            else:
                logger.info(f"Password change confirmation email sent to {user.email}")
                
            return True
        except Exception as e:
            logger.error(f"Error resetting password for {user.email}: {e}", exc_info=True)
            db.session.rollback()
            flash("Failed to reset password")
            return False

    def check_rate_limit(self, email):
        from src.infrastructure.messaging.email_service import EmailManager
        now = datetime.now(timezone.utc)
        if email not in self.failed_attempts:
            self.failed_attempts[email] = {'count': 0, 'last_attempt': now, 'lockout_count': 0}
        
        record = self.failed_attempts[email]
        user = User.query.filter_by(email=email).first()
        max_attempts = self.max_attempts if self.max_attempts is not None else 5
        email_manager = EmailManager(self.mail)

        if user and user.is_disabled:
            flash("Your account is disabled, contact support")
            return False

        if user and user.account_locked_until and user.account_locked_until > now:
            flash("Your account is temporarily locked out")
            return False
        
        if record['count'] >= max_attempts:
            if now - record['last_attempt'] < self.lockout_duration:
                flash("Your account is temporarily locked out")
                if user:
                    new_lockout_count = (user.lockout_count or 0) + 1
                    user.account_locked_until = now + self.lockout_duration
                    user.lockout_count = new_lockout_count
                    db.session.commit()
                    if new_lockout_count >= self.max_lockouts:
                        user.is_disabled = True
                        db.session.commit()
                        email_manager.send_disable_email(email)
                        flash("Your account is disabled, contact support")
                    else:
                        email_manager.send_lockout_email(email, 20)  # Duration in minutes
                return False
            else:
                record['count'] = 0
                record['last_attempt'] = now
                if user:
                    user.account_locked_until = None
                    db.session.commit()
        
        return True

    def login(self, email, password, session_manager, fingerprint_data=None, captcha_response=None, terms_accepted=None, ip_address=None):
        from src.infrastructure.messaging.email_service import EmailManager
        from src.infrastructure.database import Subscription
        from datetime import datetime, timezone
        
        try:
            if not self.validate_captcha(captcha_response):
                flash("Please complete the CAPTCHA")
                return False, None

            if not terms_accepted:
                flash("You must accept the Terms and Conditions to log in")
                return False, None

            if not self.check_rate_limit(email):
                return False, None

            user = User.query.filter_by(email=email).first()
            if not user:
                self.failed_attempts.setdefault(email, {'count': 0, 'last_attempt': datetime.now(timezone.utc), 'lockout_count': 0})
                self.failed_attempts[email]['count'] += 1
                self.failed_attempts[email]['last_attempt'] = datetime.now(timezone.utc)
                flash("Failure to authenticate")
                return False, None

            if user.is_disabled:
                flash("Your account is disabled, contact support")
                return False, None

            if not user.is_verified:
                flash("Please verify your email before logging in")
                return False, None

            if not user.check_password(password):
                self.failed_attempts.setdefault(email, {'count': 0, 'last_attempt': datetime.now(timezone.utc), 'lockout_count': 0})
                self.failed_attempts[email]['count'] += 1
                self.failed_attempts[email]['last_attempt'] = datetime.now(timezone.utc)
                user.failed_login_attempts = self.failed_attempts[email]['count']
                db.session.commit()
                email_manager = EmailManager(self.mail)
                if self.failed_attempts[email]['count'] >= self.max_attempts:
                    new_lockout_count = (user.lockout_count or 0) + 1
                    user.account_locked_until = datetime.now(timezone.utc) + self.lockout_duration
                    user.lockout_count = new_lockout_count
                    db.session.commit()
                    if new_lockout_count >= self.max_lockouts:
                        user.is_disabled = True
                        db.session.commit()
                        email_manager.send_disable_email(email)
                        flash("Your account is disabled, contact support")
                        return False, None
                    else:
                        email_manager.send_lockout_email(email, 20)
                        flash("Your account is temporarily locked out")
                        return False, None
                flash("Failure to authenticate")
                return False, None

            # NEW: Check subscription status for premium users
            if user.subscription_tier == 'premium':
                now = datetime.now(timezone.utc)
                
                # Get the most recent subscription regardless of status
                latest_subscription = Subscription.query.filter_by(
                    user_id=user.id
                ).order_by(Subscription.created_at.desc()).first()
                
                if not latest_subscription:
                    # No subscription record found at all
                    flash("Your account requires an active subscription. Please contact support.")
                    return False, None
                
                # Check if subscription is still valid (regardless of status)
                if latest_subscription.end_date >= now:
                    # Subscription is still valid - allow access
                    logger.info(f"User {email} accessing with valid subscription (status: {latest_subscription.status}, ends: {latest_subscription.end_date})")
                    # Continue with login process
                else:
                    # Subscription has expired - show renewal confirmation modal
                    if latest_subscription.status == 'active':
                        # Update status to expired if it's still marked as active
                        latest_subscription.status = 'expired'
                        db.session.commit()
                    
                    # Check if user has phone on file
                    if not user.phone:
                        flash("Your subscription has expired and no phone number is on file. Please contact support to renew.")
                        return False, None
                    
                    # Store user info in session for potential renewal
                    from flask import session
                    session['expired_user_id'] = user.id
                    session['expired_user_email'] = user.email
                    session['expired_user_phone'] = user.phone
                    
                    # Return special flag to show renewal modal
                    return False, {'redirect': 'show_renewal_modal'}

            # Update terms acceptance info if not previously accepted or if version changed
            current_terms_version = "1.0"
            if not user.terms_accepted or user.terms_version != current_terms_version:
                user.terms_accepted = True
                user.terms_accepted_at = datetime.now(timezone.utc)
                user.terms_version = current_terms_version

            session_manager.invalidate_prior_sessions(user.id)
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()

            if email in self.failed_attempts:
                self.failed_attempts[email]['count'] = 0

            login_user(user)
            
            session = session_manager.create_session(user.id, fingerprint_data, ip_address)
            if not session:
                flash("Failed to create session")
                return False, None

            logger.info(f"User logged in: {email}")
            return True, user

        except Exception as e:
            logger.error(f"Error during login: {e}")
            user = User.query.filter_by(email=email).first()
            if user and user.account_locked_until and user.account_locked_until > datetime.now(timezone.utc):
                flash("Your account is temporarily locked out")
            elif user and user.is_disabled:
                flash("Your account is disabled, contact support")
            else:
                flash("An error occurred during login")
            return False, None

    def logout(self, session_manager):
        try:
            user_id = session_manager.get_current_user_id()
            session_manager.invalidate_all_sessions(user_id)
            logout_user()
            logger.info(f"User logged out: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
        

    def generate_verification_code(self, length=6):
        """Generate a numeric verification code."""
        return ''.join(random.choices(string.digits, k=length))

    def store_verification_code(self, user_id, code, expiry_minutes=10):
        """Store the verification code in the database with expiry time."""
        from src.infrastructure.database import VerificationCode, db, User
        from datetime import datetime, timedelta
        from sqlalchemy.exc import SQLAlchemyError
        
        try:
            # Try to delete any existing codes first (wrapped in try/except)
            try:
                VerificationCode.query.filter_by(
                    user_id=user_id, 
                    verification_type='password_reset'
                ).delete()
                db.session.commit()
            except SQLAlchemyError:
                # If this fails, just continue - it could be permissions or the table doesn't exist
                db.session.rollback()
                logger.warning(f"Unable to delete existing verification codes for user {user_id}")
            
            # Create new verification code in memory first
            expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
            verification = VerificationCode(
                user_id=user_id,
                code=code,
                expires_at=expires_at,
                verification_type='password_reset'
            )
            
            # Store in memory regardless of whether we successfully save to DB
            if not hasattr(self, '_verification_codes'):
                self._verification_codes = {}
            
            self._verification_codes[user_id] = {
                'code': code,
                'expires_at': expires_at,
                'verification_type': 'password_reset'
            }
            
            # Now try to save to database
            try:
                db.session.add(verification)
                db.session.commit()
                logger.info(f"Verification code stored in database for user {user_id}")
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.warning(f"Failed to store verification code in database for user {user_id}: {e}")
                logger.info(f"Using in-memory fallback for verification code")
            
            return True
        except Exception as e:
            logger.error(f"Failed to store verification code for user {user_id}: {e}", exc_info=True)
            # Still try to store in memory
            if not hasattr(self, '_verification_codes'):
                self._verification_codes = {}
            
            expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
            self._verification_codes[user_id] = {
                'code': code,
                'expires_at': expires_at,
                'verification_type': 'password_reset'
            }
            logger.info(f"Verification code stored in memory for user {user_id} (fallback)")
            return True
        
    def verify_code(self, user_id, code):
        """Verify the provided code against stored code and log the attempt."""
        from src.infrastructure.database import VerificationCode, CommunicationLog, db
        from datetime import datetime
        from sqlalchemy.exc import SQLAlchemyError
        
        try:
            success = False
            error_message = None
            verification = None
            
            # First check if we have the code in memory
            in_memory_verified = False
            if hasattr(self, '_verification_codes') and user_id in self._verification_codes:
                stored_data = self._verification_codes[user_id]
                
                if stored_data['verification_type'] != 'password_reset':
                    error_message = "Invalid verification code type"
                    logger.warning(f"Invalid verification code type for user {user_id}")
                elif stored_data['expires_at'] < datetime.utcnow():
                    error_message = "Verification code expired"
                    logger.warning(f"Verification code expired for user {user_id}")
                elif stored_data['code'] != code:
                    error_message = "Invalid verification code"
                    logger.warning(f"Invalid verification code for user {user_id}")
                else:
                    # Code is valid, delete it to prevent reuse
                    del self._verification_codes[user_id]
                    in_memory_verified = True
                    success = True
                    logger.info(f"In-memory verification code validated for user {user_id}")
            
            # If not verified in memory, try the database
            if not in_memory_verified:
                try:
                    verification = VerificationCode.query.filter_by(
                        user_id=user_id,
                        verification_type='password_reset'
                    ).first()
                    
                    if not verification:
                        error_message = "No verification code found"
                        logger.warning(f"No verification code found for user {user_id}")
                    elif verification.expires_at < datetime.utcnow():
                        error_message = "Verification code expired"
                        logger.warning(f"Verification code expired for user {user_id}")
                    elif verification.code != code:
                        error_message = "Invalid verification code"
                        logger.warning(f"Invalid verification code for user {user_id}")
                    else:
                        # Code is valid, delete it to prevent reuse
                        db.session.delete(verification)
                        db.session.commit()
                        success = True
                        logger.info(f"Database verification code validated for user {user_id}")
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.warning(f"Database error during verification: {e}")
                    # If we already verified in memory, don't override success
                    if not in_memory_verified:
                        error_message = "Verification system error"
            
            # Log the verification attempt 
            try:
                comm_log = CommunicationLog(
                    user_id=user_id,
                    communication_type='sms_code_verification',
                    status='success' if success else 'failure',
                    error_message=error_message
                )
                db.session.add(comm_log)
                db.session.commit()
            except Exception as log_error:
                logger.error(f"Failed to log verification attempt: {log_error}")
                db.session.rollback()
            
            return success
        except Exception as e:
            logger.error(f"Error verifying code for user {user_id}: {e}", exc_info=True)
            try:
                # Log the verification error
                comm_log = CommunicationLog(
                    user_id=user_id,
                    communication_type='sms_code_verification',
                    status='failure',
                    error_message=str(e)
                )
                db.session.add(comm_log)
                db.session.commit()
            except Exception as log_error:
                logger.error(f"Failed to log verification error: {log_error}")
                db.session.rollback()
            return False
        
