import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from src.infrastructure.database import User, CommunicationLog, db, VerificationCode
from datetime import datetime, timedelta
from config.logging_config import get_domain_logger, LogDomain
from src.infrastructure.messaging import EmailManager 

logger = get_domain_logger(LogDomain.AUTH_SESSION, 'sms_manager')

class SMSManager:
    """Manages sending SMS with retry logic and test mode support."""

    def __init__(self, app=None):
        self.client = None
        self.from_number = None
        self.test_mode = True  # Default to test mode for development
        if app:
            self.init_app(app)
        logger.debug("SMSManager initialized with test_mode=%s", self.test_mode)

    def init_app(self, app):
        """Initialize Twilio client with app config."""
        try:
            # Get config from ConfigManager for application defaults
            from src.core.services.config_manager import get_config
            config = get_config()
            
            # First try app.config (might be overridden by environment)
            self.test_mode = app.config.get('SMS_TEST_MODE', config.get('SMS_TEST_MODE', True))
            account_sid = app.config.get('TWILIO_ACCOUNT_SID', config.get('TWILIO_ACCOUNT_SID', ''))
            auth_token = app.config.get('TWILIO_AUTH_TOKEN', config.get('TWILIO_AUTH_TOKEN', ''))
            self.from_number = app.config.get('TWILIO_PHONE_NUMBER', config.get('TWILIO_PHONE_NUMBER', ''))
            
            if not self.test_mode and account_sid and auth_token:
                self.client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized")
            elif self.test_mode:
                logger.info("SMS Manager running in test mode - SMS will be logged but not sent")
            else:
                logger.warning("Twilio credentials not found, SMS features disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}", exc_info=True)
            self.test_mode = True

    def send_sms(self, to_number, message, max_retries=2):
        """Send SMS with retry logic or simulate in test mode."""
        if self.test_mode:
            # Simulate successful SMS in test mode
            logger.info(f"TEST MODE: Would send SMS to {to_number}: {message}")
            return True
        
        if not self.client or not self.from_number:
            logger.error("Twilio client not initialized or phone number not configured")
            return False

        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Sending SMS to {to_number} (attempt {attempt + 1}/{max_retries + 1})")
                message = self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=to_number
                )
                logger.info(f"SMS sent successfully to {to_number}, SID: {message.sid}")
                return True
            except TwilioRestException as e:
                logger.error(f"Twilio error sending SMS to {to_number}: {e}")
                if attempt >= max_retries:
                    return False
            except Exception as e:
                logger.error(f"Unexpected error sending SMS to {to_number}: {e}", exc_info=True)
                return False
        
        return False

    def send_verification_code(self, user_id, phone_number, code):
        """
        Send verification code via SMS in production or via email in test mode.
        Logs the communication regardless of mode.
        """
        from src.infrastructure.database import User, CommunicationLog, db
        from flask import current_app
        
        try:
            # Get user information for logging or email fallback
            user = User.query.get(user_id)
            if not user:
                logger.error(f"Failed to send verification code: User {user_id} not found")
                return False
                
            if self.test_mode:
                # In test mode, send the code via email instead

                expiry_minutes = current_app.config.get('SMS_VERIFICATION_CODE_EXPIRY', 10)
                email_manager = EmailManager(current_app.extensions['mail'])
                
                logger.info(f"TEST MODE: Sending verification code {code} via email to {user.email}")
                
                template = email_manager._get_template_env().get_template('temp_code_email.html')
                html_content = template.render(
                    username=user.username,
                    verification_code=code,
                    expiry_time=expiry_minutes,
                    support_email='support@tickstock.com'
                )
                
                from flask_mail import Message
                msg = Message(
                    subject="TickStock Verification Code (Test Mode)",
                    recipients=[user.email],
                    html=html_content,
                    sender=current_app.config['MAIL_DEFAULT_SENDER']
                )
                
                success = email_manager._send_email_with_backoff(msg)
                communication_type = 'sms_verification_code_email_fallback'
                error_message = None if success else 'Failed to send verification code email (test mode)'
                
            else:
                # In production mode, send real SMS
                message = f"Your TickStock verification code is: {code}. Valid for 10 minutes."
                success = self.send_sms(phone_number, message)
                communication_type = 'sms_verification_code'
                error_message = None if success else 'Failed to send SMS verification code'
            
            # Log the communication attempt
            comm_log = CommunicationLog(
                user_id=user_id,
                communication_type=communication_type,
                status='success' if success else 'failure',
                error_message=error_message
            )
            db.session.add(comm_log)
            db.session.commit()
            
            if success:
                logger.info(f"Verification code sent successfully to user {user_id}")
            else:
                logger.error(f"Failed to send verification code to user {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending verification code to user {user_id}: {e}", exc_info=True)
            try:
                # Log the error
                comm_log = CommunicationLog(
                    user_id=user_id,
                    communication_type='sms_verification_code_error',
                    status='failure',
                    error_message=str(e)
                )
                db.session.add(comm_log)
                db.session.commit()
            except Exception as log_error:
                logger.error(f"Failed to log verification code error: {log_error}")
                db.session.rollback()
            return False