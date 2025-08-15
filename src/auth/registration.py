import re
import json
from flask import flash, url_for
from itsdangerous import URLSafeTimedSerializer
from src.infrastructure.database import User, db
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.AUTH_SESSION, 'registration')

class RegistrationManager:
    def __init__(self, app_secret_key, mail):
        self.captcha_enabled = True
        self.serializer = URLSafeTimedSerializer(app_secret_key)
        self.common_passwords = {'password', 'password123', '12345678', 'qwerty'}
        self.mail = mail
        logger.debug(f"RegistrationManager initialized with mail: {mail}")
        self.load_settings()

    def load_settings(self, cache_control=None):
        try:
            # Get config from ConfigManager for application defaults
            from src.core.services.config_manager import get_config
            config = get_config()
            
            self.captcha_enabled = config.get('CAPTCHA_ENABLED', True)
            
            common_passwords_str = config.get('COMMON_PASSWORDS', 
                                            'password,password123,12345678,qwerty')
            self.common_passwords = set(common_passwords_str.split(','))
            
            self.email_verification_salt = config.get('EMAIL_VERIFICATION_SALT', 
                                                    'email-verification')
            
            # Update serializer if salt changed
            self.serializer = URLSafeTimedSerializer(self.serializer.secret_key, 
                                                salt=self.email_verification_salt)
            
            self.support_email = config.get('SUPPORT_EMAIL', 'support@tickstock.com')
            
            logger.debug("RegistrationManager settings loaded: captcha_enabled=%s, "
                        "common_passwords=%s", 
                        self.captcha_enabled, self.common_passwords)
        except Exception as e:
            logger.error(f"Error loading registration settings: {e}")
            # Fall back to defaults
            self.captcha_enabled = True
            self.common_passwords = {'password', 'password123', '12345678', 'qwerty'}

    def validate_captcha(self, captcha_response):
        if not self.captcha_enabled:
            return True
        logger.debug("Register: CAPTCHA validation stub: Checking checkbox")
        return captcha_response == 'on'

    def generate_verification_token(self, email):
        return self.serializer.dumps(email, salt='email-verification')

    def verify_token(self, token, max_age=86400):
        try:
            email = self.serializer.loads(token, salt='email-verification', max_age=max_age)
            return email
        except Exception as e:
            logger.error(f"Register: Invalid or expired token: {e}")
            return None

    def send_verification_email(self, user):
        from src.infrastructure.messaging.email_service import EmailManager
        try:
            if not user.email:
                raise ValueError("User email is empty")
            token = self.generate_verification_token(user.email)
            logger.debug(f"Generated token for {user.email}: {token}")
            verification_url = url_for('verify_email', token=token, _external=True)
            logger.debug(f"Verification URL: {verification_url}")
            email_manager = EmailManager(self.mail)
            success = email_manager.send_verification_email(user.email, user.username, verification_url)
            if success:
                logger.info(f"Register: Verification email sent to {user.email}: {verification_url}")
                return True
            else:
                logger.error(f"Register: Failed to send verification email to {user.email}")
                return False
        except Exception as e:
            logger.error(f"Register: Failed to send verification email to {user.email}: {str(e)}", exc_info=True)
            return False

    def validate_inputs(self, email, username, password, phone, confirm_password=None):
        import phonenumbers
        errors = []
        logger.debug(f"Validating inputs: email={email}, username={username}, phone={phone!r}, confirm_password={'set' if confirm_password else 'None'}")
        
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+(\.[^@]+)*$", email):
            errors.append("Invalid email address. Must include a valid domain (e.g., .com, .org)")
        if not username or len(username) < 5 or len(username) > 50:
            errors.append("Username must be 5-50 characters")        
        if not password:
            errors.append("Password is required")
        elif len(password) < 8 or len(password) > 64:
            errors.append("Password must be 8-64 characters")
        elif not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must include letters, numbers, and special characters")
        elif password.lower() in self.common_passwords:
            errors.append("Password is too common")
        if confirm_password is not None and password != confirm_password:
            errors.append("Passwords do not match")
        
        # Skip phone validation if phone is None or empty
        if phone is not None and phone != '':
            logger.debug(f"Validating phone number: {phone}")
            try:
                # Handle bare 10-digit US numbers or common US formats
                digits_only = re.sub(r'[^\d]', '', phone)
                if len(digits_only) == 10 and not phone.startswith('+'):
                    phone = f'+1{digits_only}'  # Assume US number
                    logger.debug(f"Auto-prefixed US phone number: {phone}")
                elif phone.startswith('+') and len(digits_only) == 10:
                    phone = f'+1{digits_only}'  # Correct invalid + prefix for US numbers
                    logger.debug(f"Corrected US phone number: {phone}")

                parsed = phonenumbers.parse(phone, None)
                if not phonenumbers.is_valid_number(parsed):
                    logger.debug(f"Invalid phone number after parsing: {phone}")
                    errors.append("Invalid phone number")
                else:
                    normalized_phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                    logger.debug(f"Normalized phone number: {normalized_phone}")
                    if User.query.filter_by(phone=normalized_phone).first():
                        logger.debug(f"Phone number already registered: {normalized_phone}")
                        errors.append("Phone number already registered")
            except phonenumbers.NumberParseException as e:
                logger.debug(f"Phone number parse error for {phone}: {e}")
                errors.append("Invalid phone number format")
        else:
            logger.debug("Skipping phone validation (phone is None or empty)")
        
        if errors:
            logger.debug(f"Validation errors: {errors}")
        return errors

    def register_user(self, email, username, password, phone, captcha_response, fingerprint_data, 
         confirm_password, first_name, last_name, subscription_tier='premium',  # Default to premium
         address_line1=None, address_line2=None, city=None, state_province=None, 
         postal_code=None, country=None, card_number=None, expiry=None, cvv=None):
        from src.infrastructure.messaging.email_service import EmailManager
        try:
            errors = self.validate_inputs(email, username, password, phone, confirm_password)
            if errors:
                logger.debug(f"Register: Validation errors for email {email}: {errors}")
                for error in errors:
                    flash(error)
                return False, None

            # Validate billing address - NOW REQUIRED FOR ALL USERS
            if not address_line1 or not city or not postal_code or not country:
                flash("Billing address fields are required")
                return False, None
                
            # Validate payment information - NOW REQUIRED FOR ALL USERS
            if not card_number or not expiry or not cvv:
                flash("Payment information is required")
                return False, None
                
            # Basic card validation
            card_digits = ''.join(filter(str.isdigit, card_number))
            if len(card_digits) < 13 or len(card_digits) > 16:
                flash("Invalid card number")
                return False, None
                
            # Basic expiry validation (MM/YY format)
            if not re.match(r'^\d{2}/\d{2}$', expiry):
                flash("Expiry must be in MM/YY format")
                return False, None
                
            # Basic CVV validation
            cvv_digits = ''.join(filter(str.isdigit, cvv))
            if len(cvv_digits) < 3 or len(cvv_digits) > 4:
                flash("Invalid CVV")
                return False, None

            if not self.validate_captcha(captcha_response):
                logger.debug(f"Register: CAPTCHA validation failed for email {email}")
                flash("Please complete the CAPTCHA")
                return False, None

            # Check for existing user - EXISTING LOGIC REMAINS
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                # Check if this is a returning user with expired subscription
                if existing_user.subscription_tier == 'premium':
                    latest_subscription = Subscription.query.filter_by(
                        user_id=existing_user.id
                    ).order_by(Subscription.created_at.desc()).first()
                    
                    now = datetime.now(timezone.utc)
                    
                    # If user has expired subscription, allow "re-registration" (reactivation)
                    if latest_subscription and latest_subscription.end_date < now and latest_subscription.status in ['expired', 'cancelled']:
                        logger.info(f"Register: Reactivating expired user account: {email}")
                        
                        # Update user information
                        existing_user.username = username
                        existing_user.first_name = first_name
                        existing_user.last_name = last_name
                        existing_user.set_password(password)
                        
                        # Update phone if provided
                        if phone:
                            normalized_phone = re.sub(r'[ -()]', '', phone)
                            existing_user.phone = normalized_phone
                        
                        # Reset verification status to require re-verification
                        existing_user.is_verified = False
                        existing_user.is_active = True
                        existing_user.is_disabled = False
                        existing_user.failed_login_attempts = 0
                        existing_user.account_locked_until = None
                        existing_user.lockout_count = 0
                        
                        db.session.commit()
                        
                        # Handle subscription renewal - UPDATE BILLING INFO
                        from src.infrastructure.database import BillingInfo, Subscription
                        
                        # Update or create billing info
                        billing_info = BillingInfo.query.filter_by(
                            user_id=existing_user.id,
                            is_default=True
                        ).first()
                        
                        if billing_info:
                            # Update existing billing info
                            billing_info.address_line1 = address_line1
                            billing_info.address_line2 = address_line2
                            billing_info.city = city
                            billing_info.state_province = state_province
                            billing_info.postal_code = postal_code
                            billing_info.country = country
                            billing_info.last_four = card_digits[-4:]
                            billing_info.card_type = self._determine_card_type(card_digits)
                            
                            expiry_parts = expiry.split('/')
                            billing_info.expiry_month = int(expiry_parts[0])
                            billing_info.expiry_year = int(expiry_parts[1]) + 2000
                            billing_info.updated_at = now
                        else:
                            # Create new billing info
                            expiry_parts = expiry.split('/')
                            billing_info = BillingInfo(
                                user_id=existing_user.id,
                                address_line1=address_line1,
                                address_line2=address_line2 if address_line2 else None,
                                city=city,
                                state_province=state_province if state_province else None,
                                postal_code=postal_code,
                                country=country,
                                payment_processor='stripe',
                                last_four=card_digits[-4:],
                                card_type=self._determine_card_type(card_digits),
                                expiry_month=int(expiry_parts[0]),
                                expiry_year=int(expiry_parts[1]) + 2000,
                                is_default=True
                            )
                            db.session.add(billing_info)
                        
                        # Reactivate subscription
                        end_date = now + timedelta(days=30)
                        latest_subscription.status = 'active'
                        latest_subscription.start_date = now
                        latest_subscription.end_date = end_date
                        latest_subscription.next_billing_date = end_date
                        latest_subscription.canceled_at = None
                        
                        db.session.commit()
                        logger.info(f"Register: Subscription reactivated for returning user {email}")
                        
                        # Send verification email for reactivated account
                        email_manager = EmailManager(self.mail)
                        if not self.send_verification_email(existing_user):
                            logger.warning(f"Register: Failed to send reactivation verification email to {email}")
                            flash("Account reactivated successfully, but failed to send verification email")
                        else:
                            flash("Welcome back! Your account has been reactivated. Please check your email for verification.")
                        
                        logger.info(f"Register: Returning user account reactivated: {email}")
                        return True, existing_user
                    
                    else:
                        # User has active subscription or recent account
                        logger.debug(f"Register: Email already registered with active account: {email}")
                        flash("Email already registered")
                        return False, None
                else:
                    # Non-premium user trying to register again
                    logger.debug(f"Register: Email already registered: {email}")
                    flash("Email already registered")
                    return False, None

            # Create new user (ALL USERS NOW PREMIUM)
            user = User(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_verified=False,
                subscription_tier='premium'  # Always premium now
            )
            user.set_password(password)
            normalized_phone = re.sub(r'[ -()]', '', phone)
            user.phone = normalized_phone

            db.session.add(user)
            db.session.commit()
            logger.info(f"Register: New user data saved for {email}, username: {username}")

            # Create billing info and subscription records for ALL users
            from src.infrastructure.database import BillingInfo, Subscription
            from datetime import datetime, timedelta, timezone
            
            # Create billing info
            billing_info = BillingInfo(
                user_id=user.id,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                state_province=state_province,
                postal_code=postal_code,
                country=country,
                payment_processor='stripe',
                last_four=card_digits[-4:],
                is_default=True
            )
            
            # Extract expiry month and year
            expiry_parts = expiry.split('/')
            expiry_month = int(expiry_parts[0])
            expiry_year = int(expiry_parts[1]) + 2000
            
            billing_info.expiry_month = expiry_month
            billing_info.expiry_year = expiry_year
            billing_info.card_type = self._determine_card_type(card_digits)
            
            db.session.add(billing_info)
            
            # Create subscription - monthly subscription with 30-day period
            now = datetime.now(timezone.utc)
            end_date = now + timedelta(days=30)
            
            subscription = Subscription(
                user_id=user.id,
                subscription_type='monthly',
                subscription_tier='premium',
                status='active',
                start_date=now,
                end_date=end_date,
                next_billing_date=end_date
            )
            
            db.session.add(subscription)
            db.session.commit()
            logger.info(f"Register: Billing and subscription created for {email}")

            email_manager = EmailManager(self.mail)
            if not self.send_verification_email(user):
                logger.warning(f"Register: Failed to send verification email to {email}")
                flash("Registration successful, but failed to send verification email")

            logger.info(f"Register: User registered (pending verification): {email}")
            return True, user

        except Exception as e:
            logger.error(f"Register: Error registering user {email}: {e}", exc_info=True)
            db.session.rollback()
            flash("An error occurred during registration")
            return False, None
        

    def _determine_card_type(self, card_digits):
        """Helper method to determine card type from card number."""
        if card_digits.startswith('4'):
            return 'Visa'
        elif card_digits.startswith('5'):
            return 'MasterCard'
        elif card_digits.startswith('3'):
            return 'American Express'
        elif card_digits.startswith('6'):
            return 'Discover'
        else:
            return 'Other'