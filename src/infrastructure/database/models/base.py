# model.py
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from functools import wraps

import phonenumbers
from flask import current_app
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from werkzeug.security import check_password_hash, generate_password_hash

# Initialize logger
logger = logging.getLogger(__name__)

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    subscription_tier = db.Column(db.String(50), default='tier1')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    lockout_count = db.Column(db.Integer, default=0, nullable=False)
    is_disabled = db.Column(db.Boolean, default=False, nullable=False)
    terms_accepted = db.Column(db.Boolean, default=False, nullable=False)
    terms_accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    terms_version = db.Column(db.String(20), default='1.0')
    role = db.Column(db.String(20), default='user', nullable=False)

    def set_password(self, password):
        """Set and commit a new password hash for the user."""
        try:
            self.password_hash = generate_password_hash(password)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to set password for user {self.email}: {e}")
            db.session.rollback()
            raise

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        result = check_password_hash(self.password_hash, password)
        if result:
            logger.info(f"Password check successful for user: {self.email}")
        else:
            logger.debug(f"Password check failed for user: {self.email}")
        return result

    def set_phone(self, phone_number):
        """Set and commit a validated phone number for the user."""
        try:
            parsed = phonenumbers.parse(phone_number)
            if phonenumbers.is_valid_number(parsed):
                self.phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                db.session.commit()
            else:
                logger.error(f"Invalid phone number for user {self.email}: {phone_number}")
                raise ValueError("Invalid phone number")
        except phonenumbers.NumberParseException as e:
            logger.error(f"Invalid phone number format for user {self.email}: {phone_number}, error: {e}")
            raise ValueError("Invalid phone number format")
        except Exception as e:
            logger.error(f"Failed to set phone number for user {self.email}: {e}")
            db.session.rollback()
            raise

    def verify_2fa(self, code):
        """Stub for 2FA verification."""
        logger.debug(f"2FA verification stub called for user: {self.email}, code: {code}")
        pass

    def is_admin(self):
        """Check if user has admin role (admin or super)."""
        return self.role in ['admin', 'super']

    def is_super(self):
        """Check if user has super role (full access)."""
        return self.role == 'super'

    def has_role(self, role_name):
        """Check if user has specific role."""
        return self.role == role_name

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('settings', lazy='dynamic'))

class UserHistory(db.Model):
    __tablename__ = 'user_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    field = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.String(255))
    new_value = db.Column(db.String(255))
    change_type = db.Column(db.String(50), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('history', lazy='dynamic'))

# StockData table removed - Phase 2 cleanup

class AppSettings(db.Model):
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TaggedStock(db.Model):
    __tablename__ = 'tagged_stocks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    ticker = db.Column(db.String(10), nullable=False)
    tag_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('tagged_stocks', lazy='dynamic'))

class Session(db.Model):
    __tablename__ = 'sessions'
    session_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(255), nullable=False)
    fingerprint = db.Column(JSONB, nullable=True)
    refresh_token_hash = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def set_refresh_token(self, token):
        self.refresh_token_hash = generate_password_hash(token)
        db.session.commit()

    def check_refresh_token(self, token):
        return check_password_hash(self.refresh_token_hash, token) if self.refresh_token_hash else False

    def update_fingerprint(self, fingerprint_data):
        self.fingerprint = json.dumps(fingerprint_data)
        db.session.commit()

    def is_active(self):
        return self.status == 'active' and self.expires_at > datetime.utcnow()

class CommunicationLog(db.Model):
    __tablename__ = 'communication_log'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    communication_type = db.Column(db.String(50), nullable=False)  # e.g., 'password_reset'
    status = db.Column(db.String(20), nullable=False)  # 'success' or 'failure'
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('communication_logs', lazy='dynamic'))


class VerificationCode(db.Model):
    __tablename__ = 'verification_codes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    code = db.Column(db.String(10), nullable=False)
    verification_type = db.Column(db.String(50), nullable=False)  # e.g., 'password_reset', '2fa'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship('User', backref=db.backref('verification_codes', lazy='dynamic'))

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    subscription_type = db.Column(db.String(50), nullable=False)  # 'monthly', 'annual'
    subscription_tier = db.Column(db.String(50), nullable=False)  # 'tier1', 'premium'
    status = db.Column(db.String(50), nullable=False)  # 'active', 'canceled', 'expired', 'failed'
    start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    end_date = db.Column(db.DateTime(timezone=True), nullable=False)
    next_billing_date = db.Column(db.DateTime(timezone=True), nullable=False)
    canceled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))

    user = db.relationship('User', backref=db.backref('subscriptions', lazy='dynamic'))

    def is_active(self):
        """Check if subscription is active."""
        return (self.status == 'active' and
                self.end_date > datetime.now(UTC))

    def calculate_end_date(self, days=30):
        """Calculate end date based on subscription type."""
        if self.subscription_type == 'monthly':
            return self.start_date + timedelta(days=days)
        # Add more calculations for other subscription types as needed
        return self.start_date + timedelta(days=days)

    def cancel(self):
        """Cancel subscription but maintain access until end date."""
        if self.status == 'active':
            self.status = 'canceled'
            self.canceled_at = datetime.now(UTC)
            # No change to end_date - access remains until this date
            db.session.commit()
            return True
        return False


class BillingInfo(db.Model):
    __tablename__ = 'billing_info'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    state_province = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    payment_processor = db.Column(db.String(50), nullable=False)
    payment_method_id = db.Column(db.String(255), nullable=True)
    last_four = db.Column(db.String(4), nullable=True)
    card_type = db.Column(db.String(50), nullable=True)
    expiry_month = db.Column(db.Integer, nullable=True)
    expiry_year = db.Column(db.Integer, nullable=True)
    is_default = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))

    user = db.relationship('User', backref=db.backref('billing_info', lazy='dynamic'))

    def get_formatted_expiry(self):
        """Get formatted expiry date as MM/YY."""
        if self.expiry_month and self.expiry_year:
            year_str = str(self.expiry_year)
            # Handle both 2-digit and 4-digit years
            if len(year_str) == 4:
                year_display = year_str[2:4]  # Get last 2 digits
            else:
                year_display = f"{self.expiry_year:02d}"  # Pad with zero if needed

            return f"{self.expiry_month:02d}/{year_display}"
        return ""

class PaymentHistory(db.Model):
    __tablename__ = 'payment_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    status = db.Column(db.String(50), nullable=False)  # 'successful', 'failed', 'refunded'
    payment_processor = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(255), nullable=True)
    payment_date = db.Column(db.DateTime(timezone=True), nullable=False)
    billing_period_start = db.Column(db.DateTime(timezone=True), nullable=False)
    billing_period_end = db.Column(db.DateTime(timezone=True), nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(UTC))

    user = db.relationship('User', backref=db.backref('payment_history', lazy='dynamic'))
    subscription = db.relationship('Subscription', backref=db.backref('payments', lazy='dynamic'))

class CacheEntry(db.Model):
    __tablename__ = 'cache_entries'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(JSONB, nullable=False)
    environment = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('type', 'name', 'key', 'environment', name='unique_cache_entry'),
    )

def with_app_context(f):
    """Decorator to ensure Flask application context is available"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app:
            # We're already in an application context
            return f(*args, **kwargs)
        # We need to push an application context
        from app import app  # Import your Flask app instance
        with app.app_context():
            return f(*args, **kwargs)
    return decorated_function

# EventSession table removed - Phase 2 cleanup

# MarketAnalytics table removed - Phase 2 cleanup

class UserFilters(db.Model):
    __tablename__ = 'user_filters'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filter_name = db.Column(db.String(100), nullable=False, default='default')  # Enhanced with default
    filter_data = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add table constraints for Sprint 1B
    __table_args__ = (
        db.UniqueConstraint('user_id', 'filter_name', name='unique_user_filter'),
        db.Index('ix_user_filters_user_filter_name', 'user_id', 'filter_name'),
    )

    user = db.relationship('User', backref=db.backref('filters', lazy='dynamic'))

    def __repr__(self):
        return f'<UserFilters {self.user_id}:{self.filter_name}>'

    @classmethod
    def get_user_filter(cls, user_id: int, filter_name: str = 'default'):
        """Get a specific filter for a user."""
        return cls.query.filter_by(user_id=user_id, filter_name=filter_name).first()

    @classmethod
    def get_all_user_filters(cls, user_id: int):
        """Get all filters for a user."""
        return cls.query.filter_by(user_id=user_id).all()

    def to_dict(self):
        """Convert filter to dictionary."""
        return {
            'id': self.id,
            'filter_name': self.filter_name,
            'filter_data': self.filter_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
