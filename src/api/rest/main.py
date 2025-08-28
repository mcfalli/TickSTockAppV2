"""
Main Application Routes
Handles account management, subscription management, and static pages.
Enhanced with user filter API endpoints for Sprint 1B.
"""
from datetime import datetime, timezone, timedelta

from flask import render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from flask_login import login_required, current_user, logout_user

from src.presentation.validators.forms import UpdateEmailForm, UpdatePhoneForm, VerifyPhoneForm
from src.shared.utils.app_utils import (
    generate_verification_code, store_verification_code, verify_code,
    cancel_subscription, log_subscription_change, determine_card_type
)
from src.infrastructure.database.models.base import User, db, Subscription, BillingInfo
from src.auth.registration import RegistrationManager
from src.infrastructure.messaging.email_service import EmailManager
import logging


logger = logging.getLogger(__name__)


def register_main_routes(app, extensions, cache_control, config):
    """Register all main application routes."""
    
    # Get instances from extensions
    mail = extensions['mail']
    
    # Initialize managers
    registration_manager = RegistrationManager(app.config['SECRET_KEY'], mail)
    email_manager = EmailManager(mail)


    @app.route('/terms')
    def terms_and_conditions():
        """Display terms and conditions page."""
        return render_template('terms_and_conditions.html')

    @app.route('/privacy')
    def privacy_notice():
        """Display privacy notice page."""
        return render_template('privacy_notice.html')

    @app.route('/account', methods=['GET', 'POST'])
    @login_required
    def account():
        """Handle account management page."""
        update_email_form = UpdateEmailForm()
        update_phone_form = UpdatePhoneForm()
        
        if update_email_form.submit_email.data and update_email_form.validate():
            # Process email update
            new_email = update_email_form.email.data
            
            # Check if email already exists
            if User.query.filter(User.email == new_email, User.id != current_user.id).first():
                flash("Email already registered by another user")
                return render_template('account.html', 
                                     update_email_form=update_email_form, 
                                     update_phone_form=update_phone_form, 
                                     user=current_user)
            
            # Generate token and store pending email in session
            token = registration_manager.generate_verification_token(new_email)
            session['pending_email'] = {
                'email': new_email,
                'user_id': current_user.id
            }
            
            # Send verification email
            verification_url = url_for('verify_email_change', token=token, _external=True)
            
            # Pass the current username for the email
            if email_manager.send_verification_email(new_email, current_user.username, verification_url):
                flash("Email update initiated. Please check your new email for verification.")
                # Log out the user and redirect to login
                logout_user()
                return redirect(url_for('login'))
            else:
                flash("Failed to send verification email. Please try again.")
        
        if update_phone_form.submit_phone.data and update_phone_form.validate():
            # Process phone update
            new_phone = update_phone_form.phone.data
            
            # Basic phone validation
            from src.shared.utils.app_utils import validate_phone_number
            is_valid, normalized_phone = validate_phone_number(new_phone)
            
            if not is_valid:
                flash("Invalid phone number format.")
                return render_template('account.html', 
                                     update_email_form=update_email_form, 
                                     update_phone_form=update_phone_form, 
                                     user=current_user)
                
            # Check if phone already exists
            if User.query.filter(User.phone == normalized_phone, User.id != current_user.id).first():
                flash("Phone number already registered by another user")
                return render_template('account.html', 
                                     update_email_form=update_email_form, 
                                     update_phone_form=update_phone_form, 
                                     user=current_user)
                
            # Generate verification code
            verification_code = generate_verification_code()
            if store_verification_code(current_user.id, verification_code, 'phone_update'):
                # Send SMS with verification code
                from src.infrastructure.messaging.sms_service import SMSManager
                sms_manager = SMSManager(app)
                
                if sms_manager.send_verification_code(current_user.id, normalized_phone, verification_code):
                    # Store pending phone in session
                    session['pending_phone'] = normalized_phone
                    flash("Verification code sent to your new phone number.")
                    return redirect(url_for('verify_phone'))
                else:
                    flash("Failed to send verification code. Please try again.")
            else:
                flash("Failed to initiate phone update. Please try again.")
        
        return render_template('account.html', 
                              update_email_form=update_email_form, 
                              update_phone_form=update_phone_form, 
                              user=current_user)

    @app.route('/verify_phone', methods=['GET', 'POST'])
    @login_required
    def verify_phone():
        """Handle phone number verification."""
        form = VerifyPhoneForm()
        
        if form.validate_on_submit():
            code = form.verification_code.data
            pending_phone = session.get('pending_phone')
            
            if not pending_phone:
                flash("No phone update in progress.")
                return redirect(url_for('account'))
            
            if verify_code(current_user.id, code, 'phone_update'):
                # Update the phone number
                try:
                    # Store old phone for reference
                    old_phone = current_user.phone
                    
                    # Update to new phone number
                    current_user.phone = pending_phone
                    db.session.commit()
                    
                    # Send confirmation email
                    email_manager.send_account_update_email(
                        current_user.email, 
                        current_user.username, 
                        'phone number',
                        datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                    )
                    
                    # Clear session data
                    session.pop('pending_phone', None)
                    
                    flash("Phone number updated successfully.")
                    return redirect(url_for('account'))
                except Exception as e:
                    logger.error(f"Error updating phone: {e}")
                    db.session.rollback()
                    flash("Failed to update phone number.")
            else:
                flash("Invalid verification code. Please try again.")
        
        # Pass required context variables
        return render_template('verify_phone.html', 
                              form=form, 
                              context="phone_update",  # Set context
                              locked=False,            # Default to not locked
                              phone_hint=None)         # No phone hint for regular verification

    @app.route('/subscription', methods=['GET', 'POST'])
    @login_required
    def subscription():
        """Handle subscription management page."""
        # Get current subscription data
        subscription = Subscription.query.filter_by(
            user_id=current_user.id
        ).order_by(Subscription.created_at.desc()).first()
        
        # Get billing info
        billing_info = BillingInfo.query.filter_by(
            user_id=current_user.id,
            is_default=True
        ).first()
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'cancel':
                # Cancel subscription
                if subscription and subscription.status == 'active':
                    success = cancel_subscription(subscription)
                    if success:
                        flash("Your subscription has been cancelled. You will have access until the end of your current billing period.")
                    else:
                        flash("Failed to cancel subscription. Please try again.")
                    return redirect(url_for('subscription'))
            
            elif action == 'update_card':
                try:
                    # Get card information
                    card_number = request.form.get('card_number', '').replace(' ', '')
                    expiry = request.form.get('expiry', '')
                    cvv = request.form.get('cvv', '')
                    
                    # Get billing address information
                    address_line1 = request.form.get('address_line1', '').strip()
                    address_line2 = request.form.get('address_line2', '').strip()
                    city = request.form.get('city', '').strip()
                    state_province = request.form.get('state_province', '').strip()
                    postal_code = request.form.get('postal_code', '').strip()
                    country = request.form.get('country', '').strip()
                    
                    # Validate card information
                    if not card_number or len(card_number) < 13:
                        flash("Please enter a valid card number.")
                        return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
                    
                    if not expiry or len(expiry) != 5 or '/' not in expiry:
                        flash("Please enter a valid expiry date (MM/YY).")
                        return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
                    
                    if not cvv or len(cvv) < 3:
                        flash("Please enter a valid CVV.")
                        return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
                    
                    # Validate billing address
                    if not address_line1:
                        flash("Address Line 1 is required.")
                        return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
                    
                    if not city:
                        flash("City is required.")
                        return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
                    
                    if not postal_code:
                        flash("Postal/ZIP code is required.")
                        return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
                    
                    if not country:
                        flash("Country is required.")
                        return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
                    
                    # Update billing info
                    if billing_info:
                        
                        # Update card information
                        billing_info.last_four = card_number[-4:]
                        billing_info.card_type = determine_card_type(card_number)
                        
                        # Parse and update expiry
                        month, year = expiry.split('/')
                        billing_info.expiry_month = int(month)
                        billing_info.expiry_year = 2000 + int(year)
                        
                        # Update billing address
                        billing_info.address_line1 = address_line1
                        billing_info.address_line2 = address_line2 if address_line2 else None
                        billing_info.city = city
                        billing_info.state_province = state_province if state_province else None
                        billing_info.postal_code = postal_code
                        billing_info.country = country
                        
                        billing_info.updated_at = datetime.now(timezone.utc)
                        
                        db.session.commit()
                        logger.info(f"Payment method and billing address updated successfully for user {current_user.id}")
                        
                        flash("Payment method and billing address updated successfully.")
                        
                        # Refresh billing_info from src.infrastructure.database
                        billing_info = BillingInfo.query.filter_by(user_id=current_user.id, is_default=True).first()
                        
                    else:
                        logger.warning(f"No billing information found for user {current_user.id}")
                        flash("No billing information found to update.")
                    
                    return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
                    
                except Exception as e:
                    logger.error(f"Error updating payment method and billing address: {e}")
                    db.session.rollback()
                    flash("Failed to update payment method and billing address. Please try again.")
                    return render_template('subscription.html', subscription=subscription, billing_info=billing_info)
            
            elif action == 'resubscribe':
                # Reactivate subscription (simplified for this sprint)
                if subscription and (subscription.status == 'cancelled' or subscription.status == 'expired'):
                    try:
                        # Set up new subscription period
                        now = datetime.now(timezone.utc)
                        end_date = now + timedelta(days=30)
                        
                        # Reactivate existing subscription
                        subscription.status = 'active'
                        subscription.start_date = now
                        subscription.end_date = end_date
                        subscription.next_billing_date = end_date
                        subscription.canceled_at = None
                        
                        db.session.commit()
                        
                        # Log the reactivation
                        log_subscription_change(
                            subscription.user_id,
                            subscription.id,
                            'reactivated',
                            f"Subscription reactivated, valid until {end_date.strftime('%Y-%m-%d')}"
                        )
                        
                        # Send reactivation email
                        try:
                            email_manager.send_subscription_reactivated_email(
                                current_user.email,
                                current_user.username,
                                end_date.strftime('%Y-%m-%d')
                            )
                        except Exception as email_error:
                            logger.error(f"Failed to send reactivation email: {email_error}")
                        
                        flash("Your subscription has been reactivated.")
                        return redirect(url_for('subscription'))
                        
                    except Exception as e:
                        logger.error(f"Error reactivating subscription: {e}")
                        db.session.rollback()
                        flash("Failed to reactivate subscription. Please try again.")
            
            elif action == 'subscribe':
                # New subscription (simplified for this sprint)
                if not subscription or subscription.status != 'active':
                    try:
                        # Create new subscription
                        now = datetime.now(timezone.utc)
                        end_date = now + timedelta(days=30)
                        
                        new_subscription = Subscription(
                            user_id=current_user.id,
                            subscription_type='monthly',
                            subscription_tier='premium',
                            status='active',
                            start_date=now,
                            end_date=end_date,
                            next_billing_date=end_date
                        )
                        
                        db.session.add(new_subscription)
                        db.session.commit()
                        
                        # Update user subscription tier
                        current_user.subscription_tier = 'premium'
                        db.session.commit()
                        
                        # Log the new subscription
                        log_subscription_change(
                            current_user.id,
                            new_subscription.id,
                            'created',
                            f"New subscription created, valid until {end_date.strftime('%Y-%m-%d')}"
                        )
                        
                        flash("Your subscription has been activated.")
                        return redirect(url_for('subscription'))
                        
                    except Exception as e:
                        logger.error(f"Error creating subscription: {e}")
                        db.session.rollback()
                        flash("Failed to create subscription. Please try again.")
            
            else:
                logger.warning(f"Unknown action received: {action}")
                flash("Invalid action.")
        
        return render_template('subscription.html', 
                              subscription=subscription, 
                              billing_info=billing_info)


    # SPRINT 10 PHASE 1: Health Dashboard
    @app.route('/health-dashboard')
    @login_required
    def health_dashboard():
        """Display TickStockPL integration health dashboard."""
        return render_template('health_dashboard.html')
    
    # SPRINT 10 PHASE 3: Backtesting Dashboard
    @app.route('/backtest-dashboard')
    @login_required
    def backtest_dashboard():
        """Display TickStockPL backtesting dashboard."""
        return render_template('backtest_dashboard.html')
    
    # SPRINT 10 PHASE 4: Pattern Alerts Dashboard
    @app.route('/pattern-alerts')
    @login_required
    def pattern_alerts():
        """Display TickStockPL pattern alerts management dashboard."""
        return render_template('pattern_alerts.html')
    
    #TRACE TRACING
    @app.route('/trace/ScoobyDoo123')
    @login_required
    def trace():
        """Display trace control panel."""
        # Check if user has permission (you might want to restrict this to admins)
        # For now, any logged-in user can access
        
        return render_template('trace.html', config=config)

