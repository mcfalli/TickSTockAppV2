import logging
import smtplib
import time
from datetime import UTC, datetime
from pathlib import Path

from flask import current_app, url_for
from flask_mail import Message
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

from src.infrastructure.cache.cache_control import CacheControl


class EmailManager:
    """Manages sending emails with Jinja2 templates and exponential backoff."""

    def __init__(self, mail):
        self.mail = mail
        self._template_env = None  # Lazy initialization
        self.cache_control = CacheControl()
        self.app_settings = self.cache_control.get_cache('app_settings') or {}
        logger.debug("EmailManager initialized with mail: %s", mail)

    def _get_template_env(self):
        """Lazily initialize and return the Jinja2 Environment."""
        if self._template_env is None:
            # Use templates directory adjacent to this email service file
            template_path = Path(__file__).parent / 'templates'
            logger.debug("Loading templates from: %s", template_path)
            self._template_env = Environment(
                loader=FileSystemLoader(template_path)
            )
        return self._template_env

    def _get_support_email(self):
        """Get support email from configuration."""
        try:
            # Get config from ConfigManager for application defaults
            from src.core.services.config_manager import get_config
            config = get_config()
            return config.get('SUPPORT_EMAIL', 'support@tickstock.com')
        except Exception as e:
            logger.error(f"Error getting support email: {e}")
            return 'support@tickstock.com'

    def _send_email_with_backoff(
        self,
        msg: Message,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 16.0
    ) -> bool:
        attempt = 0
        backoff = initial_backoff

        while attempt < max_retries:
            try:
                logger.debug(f"Attempting to send email to {msg.recipients} (attempt {attempt + 1}/{max_retries})")
                self.mail.send(msg)
                logger.info(f"Email sent successfully to {msg.recipients}")
                return True
            except smtplib.SMTPException as e:
                logger.error(f"SMTP error sending email to {msg.recipients}: {e}")
                attempt += 1
                if attempt >= max_retries:
                    logger.error(f"Max retries reached for email to {msg.recipients}")
                    return False
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
            except Exception as e:
                logger.error(f"Unexpected error sending email to {msg.recipients}: {e}", exc_info=True)
                return False
        return False

    def send_verification_email(self, email, username, verification_url):
        """Send email verification link. Modified to handle new emails during update."""
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            # Check if this is for an existing user or a new email address
            user = User.query.filter_by(email=email).first()
            is_new_email = True if not user else False

            if is_new_email:
                # This is a new email address for an existing user
                # We need to find the user in the session data
                from flask import session
                pending_email = session.get('pending_email', {})
                user_id = pending_email.get('user_id')

                if user_id:
                    user = User.query.get(user_id)

                if not user:
                    logger.error(f"Cannot find user for email verification: {email}")
                    return False

            # Get email settings from cache
            support_email = self._get_support_email()

            template = self._get_template_env().get_template('verification_email.html')
            html_content = template.render(
                email=email,
                username=username,
                verification_url=verification_url,
                support_email=support_email,
                is_new_email=is_new_email
            )
            msg = Message(
                subject="Verify Your TickStock Account Email",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            max_commit_retries = 3
            for attempt in range(max_commit_retries):
                try:
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='verification_notification',
                        status='success' if success else 'failure',
                        error_message=None if success else 'Failed to send verification email'
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    logger.info(f"Communication log saved for verification email to {email}")
                    break
                except Exception as commit_error:
                    logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                    db.session.rollback()
                    if attempt == max_commit_retries - 1:
                        logger.error(f"Max retries reached for communication log commit for {email}")
            if success:
                logger.info(f"Verification email sent successfully to {email}")
            else:
                logger.error(f"Failed to send verification email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}", exc_info=True)
            db.session.rollback()
            if user:
                max_commit_retries = 3
                for attempt in range(max_commit_retries):
                    try:
                        comm_log = CommunicationLog(
                            user_id=user.id,
                            communication_type='verification_notification',
                            status='failure',
                            error_message=str(e)
                        )
                        db.session.add(comm_log)
                        db.session.commit()
                        logger.info(f"Communication log saved for failed verification email to {email}")
                        break
                    except Exception as commit_error:
                        logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                        db.session.rollback()
                        if attempt == max_commit_retries - 1:
                            logger.error(f"Max retries reached for communication log commit for {email}")
            return False

    def send_welcome_email(self, email: str, username: str) -> bool:
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.error(f"Attempted to send welcome email to non-existent user: {email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()
            base_url = self.app_settings.get('BASE_URL', 'http://localhost:5000')

            template = self._get_template_env().get_template('welcome_email.html')
            try:
                with current_app.app_context():
                    login_url = url_for('login', _external=True)
            except Exception as e:
                logger.error(f"Failed to generate login_url for welcome email: {e}")
                login_url = base_url + '/login'

            html_content = template.render(
                email=email,
                username=username,
                login_url=login_url,
                support_email=support_email
            )
            msg = Message(
                subject="Welcome to TickStock!",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            max_commit_retries = 3
            for attempt in range(max_commit_retries):
                try:
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='welcome_notification',
                        status='success' if success else 'failure',
                        error_message=None if success else 'Failed to send welcome email'
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    logger.info(f"Communication log saved for welcome email to {email}")
                    break
                except Exception as commit_error:
                    logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                    db.session.rollback()
                    if attempt == max_commit_retries - 1:
                        logger.error(f"Max retries reached for communication log commit for {email}")
            if success:
                logger.info(f"Welcome email sent successfully to {email}")
            else:
                logger.error(f"Failed to send welcome email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {e}", exc_info=True)
            db.session.rollback()
            if user:
                max_commit_retries = 3
                for attempt in range(max_commit_retries):
                    try:
                        comm_log = CommunicationLog(
                            user_id=user.id,
                            communication_type='welcome_notification',
                            status='failure',
                            error_message=str(e)
                        )
                        db.session.add(comm_log)
                        db.session.commit()
                        logger.info(f"Communication log saved for failed welcome email to {email}")
                        break
                    except Exception as commit_error:
                        logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                        db.session.rollback()
                        if attempt == max_commit_retries - 1:
                            logger.error(f"Max retries reached for communication log commit for {email}")
            return False

    def send_lockout_email(self, email: str, lockout_duration: int) -> bool:
        """Send account lockout notification email."""
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.error(f"Attempted to send lockout email to non-existent user: {email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()

            template = self._get_template_env().get_template('lockout_email.html')
            html_content = template.render(
                email=email,
                lockout_duration=lockout_duration,
                support_email=support_email
            )
            msg = Message(
                subject="TickStock Account Temporarily Locked",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            # Log communication attempt
            comm_log = CommunicationLog(
                user_id=user.id,
                communication_type='lockout_notification',
                status='success' if success else 'failure',
                error_message=None if success else 'Failed to send lockout email'
            )
            db.session.add(comm_log)
            db.session.commit()
            if success:
                logger.info(f"Lockout email sent successfully to {email}")
            else:
                logger.error(f"Failed to send lockout email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send lockout email to {email}: {e}")
            db.session.rollback()
            if user:
                comm_log = CommunicationLog(
                    user_id=user.id,
                    communication_type='lockout_notification',
                    status='failure',
                    error_message=str(e)
                )
                db.session.add(comm_log)
                try:
                    db.session.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to log lockout communication attempt for {email}: {commit_error}")
                    db.session.rollback()
            return False

    def send_disable_email(self, email: str) -> bool:
        """Send account disable notification email."""
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.error(f"Attempted to send disable email to non-existent user: {email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()

            template = self._get_template_env().get_template('disable_email.html')
            html_content = template.render(
                email=email,
                support_email=support_email
            )
            msg = Message(
                subject="TickStock Account Disabled",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            # Log communication attempt
            comm_log = CommunicationLog(
                user_id=user.id,
                communication_type='disable_notification',
                status='success' if success else 'failure',
                error_message=None if success else 'Failed to send disable email'
            )
            db.session.add(comm_log)
            db.session.commit()
            if success:
                logger.info(f"Disable email sent successfully to {email}")
            else:
                logger.error(f"Failed to send disable email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send disable email to {email}: {e}")
            db.session.rollback()
            if user:
                comm_log = CommunicationLog(
                    user_id=user.id,
                    communication_type='disable_notification',
                    status='failure',
                    error_message=str(e)
                )
                db.session.add(comm_log)
                try:
                    db.session.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to log disable communication attempt for {email}: {commit_error}")
                    db.session.rollback()
            return False

    def send_reset_email(self, email: str, reset_url: str) -> bool:
        """Send password reset email."""
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.error(f"Attempted to send reset email to non-existent user: {email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()

            template = self._get_template_env().get_template('reset_email.html')
            html_content = template.render(
                email=email,
                reset_url=reset_url,
                support_email=support_email
            )
            msg = Message(
                subject="Reset Your TickStock Password",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            # Log communication attempt
            comm_log = CommunicationLog(
                user_id=user.id,
                communication_type='password_reset',
                status='success' if success else 'failure',
                error_message=None if success else 'Failed to send email'
            )
            db.session.add(comm_log)
            db.session.commit()
            if success:
                logger.info(f"Reset email sent successfully to {email}")
            else:
                logger.error(f"Failed to send reset email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send reset email to {email}: {e}")
            db.session.rollback()
            if user:
                comm_log = CommunicationLog(
                    user_id=user.id,
                    communication_type='password_reset',
                    status='failure',
                    error_message=str(e)
                )
                db.session.add(comm_log)
                try:
                    db.session.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to log reset communication attempt for {email}: {commit_error}")
                    db.session.rollback()
            return False

    def send_change_password_email(self, email: str, username: str, change_time: str) -> bool:
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.error(f"Attempted to send change password email to non-existent user: {email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()
            base_url = self.app_settings.get('BASE_URL', 'http://localhost:5000')

            template = self._get_template_env().get_template('change_password_email.html')
            try:
                with current_app.app_context():
                    login_url = url_for('login', _external=True)
            except Exception as e:
                logger.error(f"Failed to generate login_url for change password email: {e}")
                login_url = base_url + '/login'

            html_content = template.render(
                email=email,
                username=username,
                change_time=change_time,
                login_url=login_url,
                support_email=support_email
            )
            msg = Message(
                subject="TickStock Password Changed",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )

            success = self._send_email_with_backoff(msg)
            max_commit_retries = 3
            for attempt in range(max_commit_retries):
                try:
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='password_change_notification',
                        status='success' if success else 'failure',
                        error_message=None if success else 'Failed to send change password email'
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    logger.info(f"Communication log saved for change password email to {email}")
                    break
                except Exception as commit_error:
                    logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                    db.session.rollback()
                    if attempt == max_commit_retries - 1:
                        logger.error(f"Max retries reached for communication log commit for {email}")

            if success:
                logger.info(f"Change password email sent successfully to {email}")
            else:
                logger.error(f"Failed to send change password email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send change password email to {email}: {e}", exc_info=True)
            db.session.rollback()
            if user:
                max_commit_retries = 3
                for attempt in range(max_commit_retries):
                    try:
                        comm_log = CommunicationLog(
                            user_id=user.id,
                            communication_type='password_change_notification',
                            status='failure',
                            error_message=str(e)
                        )
                        db.session.add(comm_log)
                        db.session.commit()
                        logger.info(f"Communication log saved for failed change password email to {email}")
                        break
                    except Exception as commit_error:
                        logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                        db.session.rollback()
                        if attempt == max_commit_retries - 1:
                            logger.error(f"Max retries reached for communication log commit for {email}")
            return False

    def send_email_change_notification(self, old_email, new_email, username, update_time=None):
        """Send notification when email address is changed to the old email address."""
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=old_email).first()
            if not user:
                logger.error(f"Attempted to send email change notification to non-existent user: {old_email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()
            base_url = self.app_settings.get('BASE_URL', 'http://localhost:5000')

            # Set update time if not provided
            if update_time is None:
                update_time = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')

            template = self._get_template_env().get_template('email_change_notification.html')
            try:
                with current_app.app_context():
                    login_url = url_for('login', _external=True)
            except Exception as e:
                logger.error(f"Failed to generate login_url for email change notification: {e}")
                login_url = base_url + '/login'

            html_content = template.render(
                old_email=old_email,
                new_email=new_email,
                username=username,
                update_time=update_time,
                support_email=support_email,
                login_url=login_url
            )
            msg = Message(
                subject="TickStock Email Address Changed",
                recipients=[old_email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            max_commit_retries = 3
            for attempt in range(max_commit_retries):
                try:
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='email_change_notification',
                        status='success' if success else 'failure',
                        error_message=None if success else 'Failed to send email change notification'
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    logger.info(f"Communication log saved for email change notification to {old_email}")
                    break
                except Exception as commit_error:
                    logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {old_email}: {commit_error}")
                    db.session.rollback()
                    if attempt == max_commit_retries - 1:
                        logger.error(f"Max retries reached for communication log commit for {old_email}")
            if success:
                logger.info(f"Email change notification sent successfully to {old_email}")
            else:
                logger.error(f"Failed to send email change notification to {old_email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send email change notification to {old_email}: {e}", exc_info=True)
            db.session.rollback()
            if user:
                max_commit_retries = 3
                for attempt in range(max_commit_retries):
                    try:
                        comm_log = CommunicationLog(
                            user_id=user.id,
                            communication_type='email_change_notification',
                            status='failure',
                            error_message=str(e)
                        )
                        db.session.add(comm_log)
                        db.session.commit()
                        logger.info(f"Communication log saved for failed email change notification to {old_email}")
                        break
                    except Exception as commit_error:
                        logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {old_email}: {commit_error}")
                        db.session.rollback()
                        if attempt == max_commit_retries - 1:
                            logger.error(f"Max retries reached for communication log commit for {old_email}")
            return False

    def send_subscription_reactivated_email(self, email, username, end_date):
        """Send email notification when subscription is reactivated."""
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.error(f"Attempted to send subscription reactivated email to non-existent user: {email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()
            base_url = self.app_settings.get('BASE_URL', 'http://localhost:5000')

            template = self._get_template_env().get_template('subscription_reactivated_email.html')
            try:
                with current_app.app_context():
                    login_url = url_for('login', _external=True)
            except Exception as e:
                logger.error(f"Failed to generate login_url for subscription reactivated email: {e}")
                login_url = base_url + '/login'

            html_content = template.render(
                email=email,
                username=username,
                end_date=end_date,
                support_email=support_email,
                login_url=login_url
            )
            msg = Message(
                subject="Your TickStock Premium Subscription is Active!",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            max_commit_retries = 3
            for attempt in range(max_commit_retries):
                try:
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='subscription_reactivated_notification',
                        status='success' if success else 'failure',
                        error_message=None if success else 'Failed to send subscription reactivated email'
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    logger.info(f"Communication log saved for subscription reactivated email to {email}")
                    break
                except Exception as commit_error:
                    logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                    db.session.rollback()
                    if attempt == max_commit_retries - 1:
                        logger.error(f"Max retries reached for communication log commit for {email}")
            if success:
                logger.info(f"Subscription reactivated email sent successfully to {email}")
            else:
                logger.error(f"Failed to send subscription reactivated email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send subscription reactivated email to {email}: {e}", exc_info=True)
            db.session.rollback()
            if user:
                max_commit_retries = 3
                for attempt in range(max_commit_retries):
                    try:
                        comm_log = CommunicationLog(
                            user_id=user.id,
                            communication_type='subscription_reactivated_notification',
                            status='failure',
                            error_message=str(e)
                        )
                        db.session.add(comm_log)
                        db.session.commit()
                        logger.info(f"Communication log saved for failed subscription reactivated email to {email}")
                        break
                    except Exception as commit_error:
                        logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                        db.session.rollback()
                        if attempt == max_commit_retries - 1:
                            logger.error(f"Max retries reached for communication log commit for {email}")
            return False

    def send_account_update_email(self, email, username, updated_field, update_time=None):
        """Send email notification when account details are updated."""
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.error(f"Attempted to send account update email to non-existent user: {email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()
            base_url = self.app_settings.get('BASE_URL', 'http://localhost:5000')

            # Set update time if not provided
            if update_time is None:
                update_time = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')

            template = self._get_template_env().get_template('account_update_email.html')
            try:
                with current_app.app_context():
                    login_url = url_for('login', _external=True)
            except Exception as e:
                logger.error(f"Failed to generate login_url for account update email: {e}")
                login_url = base_url + '/login'

            html_content = template.render(
                email=email,
                username=username,
                updated_field=updated_field,
                update_time=update_time,
                support_email=support_email,
                login_url=login_url
            )
            msg = Message(
                subject="TickStock Account Updated",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            max_commit_retries = 3
            for attempt in range(max_commit_retries):
                try:
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='account_update_notification',
                        status='success' if success else 'failure',
                        error_message=None if success else f'Failed to send account update email for {updated_field}'
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    logger.info(f"Communication log saved for account update email to {email}")
                    break
                except Exception as commit_error:
                    logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                    db.session.rollback()
                    if attempt == max_commit_retries - 1:
                        logger.error(f"Max retries reached for communication log commit for {email}")
            if success:
                logger.info(f"Account update email sent successfully to {email}")
            else:
                logger.error(f"Failed to send account update email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send account update email to {email}: {e}", exc_info=True)
            db.session.rollback()
            if user:
                max_commit_retries = 3
                for attempt in range(max_commit_retries):
                    try:
                        comm_log = CommunicationLog(
                            user_id=user.id,
                            communication_type='account_update_notification',
                            status='failure',
                            error_message=str(e)
                        )
                        db.session.add(comm_log)
                        db.session.commit()
                        logger.info(f"Communication log saved for failed account update email to {email}")
                        break
                    except Exception as commit_error:
                        logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                        db.session.rollback()
                        if attempt == max_commit_retries - 1:
                            logger.error(f"Max retries reached for communication log commit for {email}")
            return False

    def send_subscription_cancelled_email(self, email, username, end_date):
        """Send email notification when subscription is cancelled."""
        from src.infrastructure.database import CommunicationLog, User, db
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.error(f"Attempted to send subscription cancelled email to non-existent user: {email}")
                return False

            # Get email settings from cache
            support_email = self._get_support_email()
            base_url = self.app_settings.get('BASE_URL', 'http://localhost:5000')

            template = self._get_template_env().get_template('subscription_cancelled_email.html')
            try:
                with current_app.app_context():
                    login_url = url_for('login', _external=True)
            except Exception as e:
                logger.error(f"Failed to generate login_url for subscription cancelled email: {e}")
                login_url = base_url + '/login'

            html_content = template.render(
                email=email,
                username=username,
                end_date=end_date,
                support_email=support_email,
                login_url=login_url
            )
            msg = Message(
                subject="TickStock Subscription Cancelled",
                recipients=[email],
                html=html_content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            success = self._send_email_with_backoff(msg)
            max_commit_retries = 3
            for attempt in range(max_commit_retries):
                try:
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='subscription_cancelled_notification',
                        status='success' if success else 'failure',
                        error_message=None if success else 'Failed to send subscription cancelled email'
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    logger.info(f"Communication log saved for subscription cancelled email to {email}")
                    break
                except Exception as commit_error:
                    logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                    db.session.rollback()
                    if attempt == max_commit_retries - 1:
                        logger.error(f"Max retries reached for communication log commit for {email}")
            if success:
                logger.info(f"Subscription cancelled email sent successfully to {email}")
            else:
                logger.error(f"Failed to send subscription cancelled email to {email}")
            return success
        except Exception as e:
            logger.error(f"Failed to send subscription cancelled email to {email}: {e}", exc_info=True)
            db.session.rollback()
            if user:
                max_commit_retries = 3
                for attempt in range(max_commit_retries):
                    try:
                        comm_log = CommunicationLog(
                            user_id=user.id,
                            communication_type='subscription_cancelled_notification',
                            status='failure',
                            error_message=str(e)
                        )
                        db.session.add(comm_log)
                        db.session.commit()
                        logger.info(f"Communication log saved for failed subscription cancelled email to {email}")
                        break
                    except Exception as commit_error:
                        logger.error(f"Failed to commit communication log (attempt {attempt + 1}/{max_commit_retries}) for {email}: {commit_error}")
                        db.session.rollback()
                        if attempt == max_commit_retries - 1:
                            logger.error(f"Max retries reached for communication log commit for {email}")
            return False
