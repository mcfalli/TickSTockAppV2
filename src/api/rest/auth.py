"""
Authentication Routes
Handles user registration, login, password management, and subscription renewal.
"""

import json
from datetime import datetime, timedelta, timezone

from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user, logout_user

from src.presentation.validators.forms import (
    RegisterForm, LoginForm, ChangePasswordForm, InitiatePasswordResetForm,
    ResetPasswordForm, SubscriptionRenewalForm, VerifyPhoneForm
)
from src.shared.utils.app_utils import (
    generate_verification_code, store_verification_code, verify_code,
    determine_card_type, validate_phone_number
)
from src.infrastructure.database.models.base import User, db, Subscription, BillingInfo, CommunicationLog
from src.auth.registration import RegistrationManager
from src.auth.authentication import AuthenticationManager
from src.auth.session import SessionManager
from src.infrastructure.messaging.email_service import EmailManager
import logging

logger = logging.getLogger(__name__)


def register_auth_routes(app, extensions, cache_control, config):
    """Register all authentication-related routes."""
    
    # Get instances from extensions
    mail = extensions['mail']
    
    # Initialize authentication managers
    registration_manager = RegistrationManager(app.config['SECRET_KEY'], mail)
    registration_manager.load_settings(cache_control)
    
    authentication_manager = AuthenticationManager(app.config['SECRET_KEY'], mail)
    authentication_manager.load_settings(cache_control)
    
    session_manager = SessionManager()
    session_manager.load_settings(cache_control)
    
    email_manager = EmailManager(mail)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Handle user registration."""
        form = RegisterForm()
        if form.validate_on_submit():
            email = form.email.data
            first_name = form.first_name.data
            last_name = form.last_name.data
            username = form.username.data
            password = form.password.data
            confirm_password = form.confirm_password.data
            phone = form.phone.data
            captcha_response = 'on' if form.captcha_response.data else None
            subscription_tier = 'premium'  # Always premium since checkbox is required
            fingerprint_data = form.fingerprint_data.data
            
            # Get billing address fields - ALL REQUIRED since subscription is mandatory
            address_line1 = form.address_line1.data
            address_line2 = form.address_line2.data
            city = form.city.data
            state_province = form.state_province.data
            postal_code = form.postal_code.data
            country = form.country.data
            
            # Get payment information - ALL REQUIRED - CLEAN CARD NUMBER
            card_number = form.card_number.data.replace(' ', '') if form.card_number.data else ''
            expiry = form.expiry.data
            cvv = form.cvv.data

            # Validate required fields for subscription (all users now premium)
            if not address_line1 or not city or not postal_code or not country or not card_number or not expiry or not cvv:
                flash("All billing and payment fields are required")
                return render_template('auth/register.html', form=form)

            success, user = registration_manager.register_user(
                email=email,
                username=username,
                password=password,
                phone=phone,
                captcha_response=captcha_response,
                fingerprint_data=fingerprint_data,
                confirm_password=confirm_password,
                first_name=first_name,
                last_name=last_name,
                subscription_tier=subscription_tier,
                address_line1=address_line1,
                address_line2=address_line2, 
                city=city,
                state_province=state_province,
                postal_code=postal_code,
                country=country,
                card_number=card_number,
                expiry=expiry,
                cvv=cvv
            )
            if success:
                flash("Registration successful, check your email for verification")
                return redirect(url_for('login'))
            # Errors are flashed in register_user
        return render_template('auth/register.html', form=form)

    @app.route('/verify_email/<token>')
    def verify_email(token):
        """Verify user email from verification link."""
        email = registration_manager.verify_token(token)
        if not email:
            logger.debug(f"Verify Email: Invalid or expired token: {token}")
            flash("Invalid or expired verification link")
            return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        if not user:
            logger.debug(f"Verify Email: User not found for email: {email}")
            flash("User not found")
            return redirect(url_for('login'))
        
        if user.is_verified:
            logger.debug(f"Verify Email: Email already verified for {email}")
            flash("Email already verified")
            return redirect(url_for('login'))
        
        try:
            user.is_verified = True
            db.session.commit()
            logger.info(f"Verify Email: Email verified for {email}")
            
            if not email_manager.send_welcome_email(email, user.username):
                logger.debug(f"Verify Email: Failed to send welcome email to {email}")
                flash("Email verified successfully, but failed to send welcome email")
            else:
                logger.debug(f"Verify Email: Welcome email sent to {email}")
                flash("Email verified successfully, check your email for welcome confirmation")
        except Exception as e:
            logger.error(f"Verify Email: Error verifying email for {email}: {e}", exc_info=True)
            db.session.rollback()
            flash("An error occurred while verifying your email")
        
        return redirect(url_for('login'))

    @app.route('/verify_email_change/<token>')
    def verify_email_change(token):
        """Verify email change from link in email."""
        try:
            # Verify token
            new_email = registration_manager.verify_token(token)
            if not new_email:
                flash("Invalid or expired verification link")
                return redirect(url_for('login'))
                
            # Get the pending email data
            pending_email = session.get('pending_email')
            if not pending_email or pending_email.get('email') != new_email:
                flash("Email verification failed")
                return redirect(url_for('login'))
                
            # Update user email
            user_id = pending_email.get('user_id')
            user = User.query.get(user_id)
            
            if not user:
                flash("User not found")
                return redirect(url_for('login'))
                
            # Store old email for notification
            old_email = user.email
            
            # Record time of update for consistency across both emails
            update_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Send specialized notification to old email address BEFORE making the change
            notification_to_old_email = email_manager.send_email_change_notification(
                old_email,
                new_email,
                user.username,
                update_time
            )
            
            if not notification_to_old_email:
                logger.warning(f"Failed to send notification to old email ({old_email}) about email change")
            
            # Update email and reset verification status
            user.email = new_email
            user.is_verified = True  # Auto-verify since they've clicked the link
            db.session.commit()
            
            # Send confirmation email to new address
            email_manager.send_account_update_email(
                new_email,
                user.username,
                'email address',
                update_time
            )
            
            # Clear session data
            session.pop('pending_email', None)
            
            flash("Email updated successfully. Please log in with your new email.")
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Error verifying email change: {e}")
            flash("Failed to verify email change")
            return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handle user login."""
        form = LoginForm()
        if request.method == 'POST' and not form.validate_on_submit():
            flash("Failure to authenticate")
        
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data
            captcha_response = 'on' if form.captcha_response.data else None
            terms_accepted = form.terms_accepted.data
            fingerprint_data = json.loads(form.fingerprint_data.data) if form.fingerprint_data.data else None
            ip_address = request.remote_addr
            
            success, result = authentication_manager.login(
                email, password, session_manager, fingerprint_data, captcha_response, terms_accepted, ip_address
            )
            
            if success:
                return redirect(url_for('index'))
            elif isinstance(result, dict) and result.get('redirect') == 'subscription_renewal':
                # Redirect to subscription renewal page
                return redirect(url_for('subscription_renewal'))
            elif isinstance(result, dict) and result.get('redirect') == 'renewal_sms_challenge':
                # Redirect to SMS challenge for renewal
                return redirect(url_for('renewal_sms_challenge'))
            elif isinstance(result, dict) and result.get('redirect') == 'show_renewal_modal':
                # Show login page with renewal modal
                return render_template('auth/login.html', form=form, show_renewal_modal=True)
            # If result is None or any other value, fall through to render login page with flash messages
            
        return render_template('auth/login.html', form=form)

    @app.route('/confirm_renewal', methods=['POST'])
    def confirm_renewal():
        """Handle user's renewal confirmation decision."""
        
        # Check if user data is in session
        expired_user_id = session.get('expired_user_id')
        expired_user_email = session.get('expired_user_email')
        expired_user_phone = session.get('expired_user_phone')
        
        if not expired_user_id or not expired_user_email:
            flash("Session expired. Please try logging in again.")
            return redirect(url_for('login'))
        
        # Get user's decision
        user_decision = request.form.get('decision')
        
        if user_decision == 'yes':
            # User wants to renew - start SMS challenge
            
            # Transfer session data for SMS challenge
            session['renewal_challenge_user_id'] = expired_user_id
            session['renewal_challenge_email'] = expired_user_email
            session['renewal_challenge_phone'] = expired_user_phone
            session['renewal_challenge_attempts'] = 0
            session['renewal_challenge_locked_until'] = None
            
            # Clear expired session data
            session.pop('expired_user_id', None)
            session.pop('expired_user_email', None)
            session.pop('expired_user_phone', None)
            
            flash("For security, we'll send a verification code to your phone to proceed with renewal.")
            return redirect(url_for('renewal_sms_challenge'))
            
        elif user_decision == 'no':
            # User doesn't want to renew - clear session and return to login
            session.pop('expired_user_id', None)
            session.pop('expired_user_email', None)
            session.pop('expired_user_phone', None)
            
            flash("You can log in again anytime to renew your subscription.")
            return redirect(url_for('login'))
            
        else:
            # Invalid decision
            flash("Please select an option.")
            return redirect(url_for('login'))

    @app.route('/logout')
    @login_required
    def logout():
        """Handle user logout."""
        authentication_manager.logout(session_manager)
        return redirect(url_for('login'))

    @app.route('/change_password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        """Handle password change for authenticated users."""
        if not current_user.is_authenticated:
            logger.error("Unauthenticated user attempted to access change_password")
            flash("Please log in to change your password")
            return redirect(url_for('login'))

        form = ChangePasswordForm()
        if form.validate_on_submit():
            current_password = form.current_password.data
            new_password = form.new_password.data
            confirm_password = form.confirm_password.data
            captcha_response = 'on' if form.captcha_response.data else None
            
            if new_password != confirm_password:
                flash("New passwords do not match")
                logger.debug(f"Password change failed for {current_user.email}: Passwords do not match")
                return render_template('auth/change_password.html', form=form)

            success = authentication_manager.change_password(
                current_user, current_password, new_password, captcha_response
            )
            if success:
                return redirect(url_for('login'))
            # Errors are flashed in AuthenticationManager
        return render_template('auth/change_password.html', form=form)

    @app.route('/initiate_password_reset', methods=['GET', 'POST'])
    def initiate_password_reset():
        """Handle password reset initiation."""
        form = InitiatePasswordResetForm()
        if form.validate_on_submit():
            email = form.email.data
            captcha_response = 'on' if form.captcha_response.data else None
            
            if not authentication_manager.validate_captcha(captcha_response):
                flash("Please complete the CAPTCHA")
                return render_template('auth/initiate_password_reset.html', form=form)
            
            success = authentication_manager.initiate_password_reset(email)
            if success:
                return redirect(url_for('login'))
            # Error messages are flashed in AuthenticationManager
        return render_template('auth/initiate_password_reset.html', form=form)

    @app.route('/reset_password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        """Handle password reset with SMS verification."""
        email = authentication_manager.verify_reset_token(token)
        if not email:
            flash("Invalid or expired reset link")
            return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("User not found")
            return redirect(url_for('login'))
        
        form = ResetPasswordForm()
        if form.validate_on_submit():
            new_password = form.new_password.data
            confirm_password = form.confirm_password.data
            verification_code = form.verification_code.data
            captcha_response = 'on' if form.captcha_response.data else None
            
            if new_password != confirm_password:
                flash("Passwords do not match")
                return render_template('auth/reset_password.html', form=form, token=token)
                
            if not authentication_manager.validate_captcha(captcha_response):
                flash("Please complete the CAPTCHA")
                return render_template('auth/reset_password.html', form=form, token=token)
                
            # Verify SMS code
            if not verify_code(user.id, verification_code, 'password_reset'):
                flash("Invalid or expired verification code")
                return render_template('auth/reset_password.html', form=form, token=token)
                
            success = authentication_manager.reset_password(user, new_password, captcha_response)
            if success:
                session_manager.invalidate_all_sessions(user.id)  # Terminate existing sessions
                flash("Password reset successfully. Check your email for confirmation.")
                return redirect(url_for('login'))
            else:
                flash("Failed to reset password")
        
        return render_template('auth/reset_password.html', form=form, token=token)

    @app.route('/renewal_sms_challenge', methods=['GET', 'POST'])
    def renewal_sms_challenge():
        """Handle SMS verification challenge for subscription renewal."""
        
        # Check if user data is in session (from failed login)
        challenge_user_id = session.get('renewal_challenge_user_id')
        challenge_email = session.get('renewal_challenge_email')
        challenge_phone = session.get('renewal_challenge_phone')
        
        if not challenge_user_id or not challenge_email:
            flash("Please log in to access your account.")
            return redirect(url_for('login'))
        
        # Get user data
        user = User.query.get(challenge_user_id)
        if not user or user.email != challenge_email:
            flash("Invalid session data. Please try logging in again.")
            session.pop('renewal_challenge_user_id', None)
            session.pop('renewal_challenge_email', None)
            session.pop('renewal_challenge_phone', None)
            return redirect(url_for('login'))
        
        # Check for lockout
        lockout_until = session.get('renewal_challenge_locked_until')
        now = datetime.now(timezone.utc)
        
        if lockout_until:
            lockout_time = datetime.fromisoformat(lockout_until)
            if now < lockout_time:
                minutes_remaining = int((lockout_time - now).total_seconds() / 60)
                flash(f"Too many failed attempts. Please try again in {minutes_remaining} minutes or contact support.")
                return render_template('auth/verify_phone.html', 
                                     form=VerifyPhoneForm(), 
                                     locked=True, 
                                     context="renewal")
        
        form = VerifyPhoneForm()
        
        # Handle GET request - send SMS code
        if request.method == 'GET':
            # Generate and send verification code
            verification_code = generate_verification_code()
            
            if store_verification_code(user.id, verification_code, 'renewal_verification'):
                # Send SMS with verification code
                from src.infrastructure.messaging.sms_service import SMSManager
                sms_manager = SMSManager(app)
                
                if sms_manager.send_verification_code(user.id, user.phone, verification_code):
                    # Log the SMS send attempt
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='renewal_sms_verification',
                        status='sent',
                        error_message=f"SMS verification sent to {user.phone[-4:]} for subscription renewal"
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    
                    flash("A verification code has been sent to your phone. Please enter it below to proceed with renewal.")
                else:
                    flash("Failed to send verification code. Please try again or contact support.")
                    
                    # Log the SMS failure
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='renewal_sms_verification',
                        status='failure',
                        error_message="Failed to send SMS verification code for renewal"
                    )
                    db.session.add(comm_log)
                    db.session.commit()
            else:
                flash("Failed to generate verification code. Please try again or contact support.")
        
        # Handle POST request - verify code
        if form.validate_on_submit():
            code = form.verification_code.data
            attempts = session.get('renewal_challenge_attempts', 0)
            max_attempts = app.config.get('RENEWAL_SMS_MAX_ATTEMPTS', 3)
            
            if verify_code(user.id, code, 'renewal_verification'):
                # Code is valid - clear session data and proceed to renewal
                session.pop('renewal_challenge_user_id', None)
                session.pop('renewal_challenge_email', None)
                session.pop('renewal_challenge_phone', None)
                session.pop('renewal_challenge_attempts', None)
                session.pop('renewal_challenge_locked_until', None)
                
                # Set up renewal session data
                session['renewal_user_id'] = user.id
                session['renewal_email'] = user.email
                
                # Log successful verification
                comm_log = CommunicationLog(
                    user_id=user.id,
                    communication_type='renewal_sms_verification',
                    status='success',
                    error_message="SMS verification successful for renewal access"
                )
                db.session.add(comm_log)
                db.session.commit()
                
                flash("Verification successful! You can now proceed with subscription renewal.")
                return redirect(url_for('subscription_renewal'))
            else:
                # Code is invalid - increment attempts
                attempts += 1
                session['renewal_challenge_attempts'] = attempts
                
                # Log failed attempt
                comm_log = CommunicationLog(
                    user_id=user.id,
                    communication_type='renewal_sms_verification',
                    status='failure',
                    error_message=f"Invalid SMS verification code - attempt {attempts}/{max_attempts}"
                )
                db.session.add(comm_log)
                db.session.commit()
                
                if attempts >= max_attempts:
                    # Lock out user
                    lockout_minutes = app.config.get('RENEWAL_SMS_LOCKOUT_MINUTES', 15)
                    lockout_until = now + timedelta(minutes=lockout_minutes)
                    session['renewal_challenge_locked_until'] = lockout_until.isoformat()
                    
                    # Log lockout
                    comm_log = CommunicationLog(
                        user_id=user.id,
                        communication_type='renewal_sms_verification',
                        status='locked',
                        error_message=f"Account locked due to {max_attempts} failed SMS verification attempts"
                    )
                    db.session.add(comm_log)
                    db.session.commit()
                    
                    flash(f"Too many failed attempts. Access locked for {lockout_minutes} minutes. Please contact support if you need assistance.")
                    return render_template('auth/verify_phone.html', 
                                         form=form, 
                                         locked=True, 
                                         context="renewal")
                else:
                    remaining = max_attempts - attempts
                    flash(f"Invalid verification code. {remaining} attempt(s) remaining.")
        
        return render_template('auth/verify_phone.html', 
                              form=form, 
                              context="renewal",
                              phone_hint=f"***-***-{user.phone[-4:]}" if user.phone else "your phone")

    @app.route('/subscription_renewal', methods=['GET', 'POST'])
    def subscription_renewal():
        """Handle subscription renewal for expired users."""
        
        # Check if user data is in session (from failed login)
        renewal_user_id = session.get('renewal_user_id')
        renewal_email = session.get('renewal_email')
        
        if not renewal_user_id or not renewal_email:
            flash("Please log in to access your account.")
            return redirect(url_for('login'))
        
        # Get user data
        user = User.query.get(renewal_user_id)
        if not user or user.email != renewal_email:
            flash("Invalid session data. Please try logging in again.")
            session.pop('renewal_user_id', None)
            session.pop('renewal_email', None)
            return redirect(url_for('login'))
        
        # Get existing billing info if available
        billing_info = BillingInfo.query.filter_by(
            user_id=user.id,
            is_default=True
        ).first()
        
        # Create form and pre-populate with existing data
        form = SubscriptionRenewalForm()
        
        # Pre-populate form with existing data on GET request
        if request.method == 'GET' and billing_info:
            form.address_line1.data = billing_info.address_line1
            form.address_line2.data = billing_info.address_line2
            form.city.data = billing_info.city
            form.state_province.data = billing_info.state_province
            form.postal_code.data = billing_info.postal_code
            form.country.data = billing_info.country
            form.phone.data = user.phone
        
        if form.validate_on_submit():
            try:
                # Get form data
                phone = form.phone.data.strip() if form.phone.data else ''
                card_number = form.card_number.data.replace(' ', '')
                expiry = form.expiry.data
                cvv = form.cvv.data
                address_line1 = form.address_line1.data.strip()
                address_line2 = form.address_line2.data.strip() if form.address_line2.data else ''
                city = form.city.data.strip()
                state_province = form.state_province.data.strip() if form.state_province.data else ''
                postal_code = form.postal_code.data.strip()
                country = form.country.data.strip()
                
                # Validate phone number if provided and different from current
                if phone and phone != user.phone:
                    is_valid, normalized_phone = validate_phone_number(phone)
                    if not is_valid:
                        flash("Invalid phone number format.")
                        return render_template('account/subscription_renewal.html', form=form, user=user, billing_info=billing_info)
                    user.phone = normalized_phone
                
                # Basic card validation (additional to form validation)
                card_digits = ''.join(filter(str.isdigit, card_number))
                if len(card_digits) < 13 or len(card_digits) > 16:
                    flash("Invalid card number length.")
                    return render_template('account/subscription_renewal.html', form=form, user=user, billing_info=billing_info)
                
                # Process renewal
                now = datetime.now(timezone.utc)
                end_date = now + timedelta(days=30)
                
                # Update or create billing info
                if billing_info:
                    billing_info.address_line1 = address_line1
                    billing_info.address_line2 = address_line2 if address_line2 else None
                    billing_info.city = city
                    billing_info.state_province = state_province if state_province else None
                    billing_info.postal_code = postal_code
                    billing_info.country = country
                    billing_info.last_four = card_digits[-4:]
                    billing_info.card_type = determine_card_type(card_digits)
                    
                    month, year = expiry.split('/')
                    billing_info.expiry_month = int(month)
                    billing_info.expiry_year = 2000 + int(year)
                    billing_info.updated_at = now
                else:
                    month, year = expiry.split('/')
                    billing_info = BillingInfo(
                        user_id=user.id,
                        address_line1=address_line1,
                        address_line2=address_line2 if address_line2 else None,
                        city=city,
                        state_province=state_province if state_province else None,
                        postal_code=postal_code,
                        country=country,
                        payment_processor='stripe',
                        last_four=card_digits[-4:],
                        card_type=determine_card_type(card_digits),
                        expiry_month=int(month),
                        expiry_year=2000 + int(year),
                        is_default=True
                    )
                    db.session.add(billing_info)
                
                # Reactivate or create subscription
                latest_subscription = Subscription.query.filter_by(
                    user_id=user.id
                ).order_by(Subscription.created_at.desc()).first()
                
                if latest_subscription and latest_subscription.status in ['cancelled', 'expired']:
                    # Reactivate existing subscription
                    latest_subscription.status = 'active'
                    latest_subscription.start_date = now
                    latest_subscription.end_date = end_date
                    latest_subscription.next_billing_date = end_date
                    latest_subscription.canceled_at = None
                    subscription = latest_subscription
                else:
                    # Create new subscription
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
                
                # Ensure user is marked as premium tier
                user.subscription_tier = 'premium'
                
                db.session.commit()
                
                # Log the renewal
                from src.shared.utils.app_utils import log_subscription_change
                log_subscription_change(
                    user.id,
                    subscription.id,
                    'renewed',
                    f"Subscription renewed, valid until {end_date.strftime('%Y-%m-%d')}"
                )
                
                # Send renewal confirmation email
                try:
                    email_manager.send_subscription_reactivated_email(
                        user.email,
                        user.username,
                        end_date.strftime('%Y-%m-%d')
                    )
                except Exception as email_error:
                    logger.error(f"Failed to send renewal email: {email_error}")
                
                # Clear renewal session data
                session.pop('renewal_user_id', None)
                session.pop('renewal_email', None)
                
                flash("Your subscription has been renewed successfully. You can now log in.")
                return redirect(url_for('login'))
                
            except Exception as e:
                logger.error(f"Error renewing subscription: {e}")
                db.session.rollback()
                flash("Failed to renew subscription. Please try again.")
        
        return render_template('account/subscription_renewal.html', form=form, user=user, billing_info=billing_info)