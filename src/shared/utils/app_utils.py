"""
Application Utility Functions
Helper functions used across the application.
"""

import random
import string
import logging
from datetime import datetime, timedelta, timezone
from src.infrastructure.database import db, VerificationCode, CommunicationLog

logger = logging.getLogger(__name__)


def generate_verification_code(length=6):
    """Generate a numeric verification code."""
    return ''.join(random.choices(string.digits, k=length))


def store_verification_code(user_id, code, verification_type='phone_update', expiry_minutes=10):
    """Store a verification code in the database."""
    try:
        # Delete existing codes first
        VerificationCode.query.filter_by(
            user_id=user_id,
            verification_type=verification_type
        ).delete()
        
        # Create new code
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        verification = VerificationCode(
            user_id=user_id,
            code=code,
            verification_type=verification_type,
            expires_at=expires_at
        )
        
        db.session.add(verification)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to store verification code: {e}")
        db.session.rollback()
        return False


def verify_code(user_id, code, verification_type='phone_update'):
    """Verify a code for a user and code type."""
    try:
        verification = VerificationCode.query.filter_by(
            user_id=user_id,
            verification_type=verification_type
        ).first()
        
        if not verification:
            logger.warning(f"No verification code found for user {user_id}, type: {verification_type}")
            return False
            
        if verification.expires_at < datetime.utcnow():
            logger.warning(f"Verification code expired for user {user_id}, type: {verification_type}")
            db.session.delete(verification)
            db.session.commit()
            return False
            
        if verification.code != code:
            logger.warning(f"Invalid verification code for user {user_id}, type: {verification_type}")
            return False
            
        # Code is valid, delete it to prevent reuse
        db.session.delete(verification)
        db.session.commit()
        logger.info(f"Verification code validated for user {user_id}, type: {verification_type}")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying code: {e}")
        return False


def cancel_subscription(subscription):
    """Cancel a user's subscription but maintain access until end date."""
    try:
        if subscription.status != 'active':
            logger.warning(f"Attempted to cancel inactive subscription {subscription.id}")
            return False
            
        subscription.status = 'cancelled'
        subscription.canceled_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Log the cancellation
        log_subscription_change(
            subscription.user_id,
            subscription.id,
            'cancelled',
            f"Subscription cancelled, access until {subscription.end_date.strftime('%Y-%m-%d')}"
        )
        
        # Send cancellation email
        try:
            from src.infrastructure.database import User
            from src.infrastructure.messaging.email_service import EmailManager
            from flask import current_app
            
            user = User.query.get(subscription.user_id)
            if user:
                # Get mail instance from app context
                mail = current_app.extensions.get('mail')
                if mail:
                    email_manager = EmailManager(mail)
                    email_manager.send_subscription_cancelled_email(
                        user.email,
                        user.username,
                        subscription.end_date.strftime('%Y-%m-%d')
                    )
        except Exception as email_error:
            logger.error(f"Failed to send cancellation email: {email_error}")
        
        return True
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        db.session.rollback()
        return False


def log_subscription_change(user_id, subscription_id, status, message):
    """Log subscription status changes."""
    try:
        # Create a communication log entry
        comm_log = CommunicationLog(
            user_id=user_id,
            communication_type='subscription_update',
            status=status,
            error_message=message
        )
        db.session.add(comm_log)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to log subscription change: {e}")
        db.session.rollback()
        return False


def determine_card_type(card_number):
    """Determine card type from card number."""
    if card_number.startswith('4'):
        return 'Visa'
    elif card_number.startswith(('5', '2')):
        return 'Mastercard'
    elif card_number.startswith(('34', '37')):
        return 'American Express'
    elif card_number.startswith('6'):
        return 'Discover'
    else:
        return 'Unknown'


def validate_phone_number(phone):
    """Validate and normalize phone number."""
    import re
    import phonenumbers
    
    try:
        normalized_phone = phone
        # Format numbers if they appear valid
        digits_only = re.sub(r'[^\d]', '', phone)
        if len(digits_only) >= 10:
            try:
                parsed = phonenumbers.parse(phone)
                if not phonenumbers.is_valid_number(parsed):
                    parsed = phonenumbers.parse(f"+1{digits_only}")
                
                if phonenumbers.is_valid_number(parsed):
                    normalized_phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                    return True, normalized_phone
            except Exception:
                # If parsing fails, use the raw input
                pass
        
        return False, phone
        
    except Exception as e:
        logger.error(f"Error validating phone number: {e}")
        return False, phone


def generate_test_events(market_service):
    """Generate test events for debugging."""
    return {
        "highs": [{"ticker": "AAPL", "price": 175.5, "time": datetime.now().strftime("%H:%M:%S"), 
                  "market_status": market_service.get_market_status(), "count": 1, "label": "Test high"}],
        "lows": [{"ticker": "MSFT", "price": 350.25, "time": datetime.now().strftime("%H:%M:%S"), 
                 "market_status": market_service.get_market_status(), "count": 1, "label": "Test low"}],
        "counts": {"highs": 1, "lows": 1, "total_highs": 1, "total_lows": 1},
        "market_status": market_service.get_market_status(),
        "source": "Test Events",
        "is_synthetic": True
    }