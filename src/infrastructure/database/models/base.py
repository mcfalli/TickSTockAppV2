# model.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask import current_app
from functools import wraps
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from datetime import date
import json
from werkzeug.security import generate_password_hash, check_password_hash
import phonenumbers
import uuid
from sqlalchemy.dialects.postgresql import JSONB
import logging


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

class StockData(db.Model):
    __tablename__ = 'stock_data'
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    high_count = db.Column(db.Integer, default=0)
    low_count = db.Column(db.Integer, default=0)
    trend = db.Column(db.String(50))
    surge = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    user = db.relationship('User', backref=db.backref('subscriptions', lazy='dynamic'))
    
    def is_active(self):
        """Check if subscription is active."""
        return (self.status == 'active' and 
                self.end_date > datetime.now(timezone.utc))
                
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
            self.canceled_at = datetime.now(timezone.utc)
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
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
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
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    
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
        else:
            # We need to push an application context
            from app import app  # Import your Flask app instance
            with app.app_context():
                return f(*args, **kwargs)
    return decorated_function

class EventSession(db.Model):
    """
    Track high/low event accumulation counts for each trading session.
    Resets at market open, accumulates during trading hours.
    """
    __tablename__ = 'event_session'
    
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)  # CHANGED: 10 -> 20
    session_date = db.Column(db.Date, nullable=False, index=True)
    high_count = db.Column(db.Integer, default=0, nullable=False)
    low_count = db.Column(db.Integer, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint for ticker + session_date
    __table_args__ = (
        db.UniqueConstraint('ticker', 'session_date', name='unique_ticker_session'),
        db.Index('idx_session_ticker_date', 'ticker', 'session_date'),
        db.Index('idx_session_date', 'session_date')
    )
    
    def __repr__(self):
        return f'<EventSession {self.ticker} {self.session_date}: H{self.high_count}/L{self.low_count}>'
    
    @classmethod
    @with_app_context
    def get_or_create_for_session(cls, ticker: str, session_date: datetime.date):
        """
        Get existing accumulation record or create new one for the session.
        
        Args:
            ticker: Stock symbol
            session_date: Trading session date
            
        Returns:
            EventSession: Existing or new record
        """
        try:
            # Try to get existing record
            record = cls.query.filter_by(
                ticker=ticker,
                session_date=session_date
            ).first()
            
            if not record:
                # Create new record for this session
                record = cls(
                    ticker=ticker,
                    session_date=session_date,
                    high_count=0,
                    low_count=0
                )
                db.session.add(record)
                db.session.commit()
            
            return record
            
        except Exception as e:
            logger.error(f"Error getting/creating session accumulation for {ticker}: {e}")
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return None
    
    @with_app_context  
    def increment_high_count(self):
        """Increment high count and update timestamp."""
        try:
            self.high_count += 1
            self.last_updated = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error incrementing high count for {self.ticker}: {e}")
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return False
    
    @with_app_context
    def increment_low_count(self):
        """Increment low count and update timestamp."""
        try:
            self.low_count += 1
            self.last_updated = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error incrementing low count for {self.ticker}: {e}")
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return False
    
    def get_total_events(self):
        """Get total events (highs + lows) for this session."""
        return self.high_count + self.low_count
    
    @classmethod
    @with_app_context
    def get_session_totals(cls, session_date: datetime.date):
        """
        Get aggregated totals for entire market session.
        
        Args:
            session_date: Trading session date
            
        Returns:
            dict: Total highs, lows, and active tickers for the session
        """
        try:
            session_records = cls.query.filter_by(session_date=session_date).all()
            
            total_highs = sum(record.high_count for record in session_records)
            total_lows = sum(record.low_count for record in session_records)
            active_tickers = len([r for r in session_records if r.get_total_events() > 0])
            
            return {
                'total_highs': total_highs,
                'total_lows': total_lows,
                'total_events': total_highs + total_lows,
                'active_tickers': active_tickers,
                'session_date': session_date
            }
            
        except Exception as e:
            logger.error(f"Error getting session totals for {session_date}: {e}")
            return {
                'total_highs': 0,
                'total_lows': 0,
                'total_events': 0,
                'active_tickers': 0,
                'session_date': session_date
            }
    
    @classmethod
    @with_app_context
    def get_ticker_session_data(cls, ticker: str, session_date: datetime.date):
        """
        Get accumulation data for a specific ticker and session.
        
        Args:
            ticker: Stock symbol
            session_date: Trading session date
            
        Returns:
            dict: Accumulation data or default values
        """
        try:
            record = cls.query.filter_by(
                ticker=ticker,
                session_date=session_date
            ).first()
            
            if record:
                return {
                    'ticker': ticker,
                    'session_date': session_date,
                    'high_count': record.high_count,
                    'low_count': record.low_count,
                    'total_events': record.get_total_events(),
                    'last_updated': record.last_updated
                }
            else:
                return {
                    'ticker': ticker,
                    'session_date': session_date,
                    'high_count': 0,
                    'low_count': 0,
                    'total_events': 0,
                    'last_updated': None
                }
                
        except Exception as e:
            logger.error(f"Error getting ticker session data for {ticker}: {e}")
            return {
                'ticker': ticker,
                'session_date': session_date,
                'high_count': 0,
                'low_count': 0,
                'total_events': 0,
                'last_updated': None
            }
        
class MarketAnalytics(db.Model):
    """
    Track TickStock Core Universe market pressure analytics with EMA weighted and non-weighted averages.
    Sprint 1 FIXED: Single aggregated record every 10 seconds with BIGINT activity counts for billion-scale data.
    """
    __tablename__ = 'market_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    session_date = db.Column(db.Date, nullable=False, index=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Identity & Data Source - UPDATED: 'live' → 'core'
    data_source = db.Column(db.String(50), default='core', nullable=False)  # Changed from 'live' to 'core'
    
    # Current Values (latest calculated in 10-second window)
    current_net_score = db.Column(db.Numeric(8,2), nullable=False)           # Latest net score (-10 to +10)
    current_activity_level = db.Column(db.String(20), nullable=False)        # 'Low', 'Moderate', 'High', 'Very High'
    
    # ✅ FIXED: Upgraded to BIGINT for billion-scale activity counts
    current_buying_count = db.Column(db.BigInteger, nullable=False, default=0)   # Was Integer, now BigInteger (billions)
    current_selling_count = db.Column(db.BigInteger, nullable=False, default=0)  # Was Integer, now BigInteger (billions) 
    current_activity_count = db.Column(db.BigInteger, nullable=False, default=0) # Was Integer, now BigInteger (billions)
    
    # Weighted Averages (EMA calculations) - NEW FIELDS
    ema_net_score_gauge = db.Column(db.Numeric(8,4), nullable=True)         # Gauge EMA (α=0.3)
    ema_net_score_vertical = db.Column(db.Numeric(8,4), nullable=True)      # Vertical EMA (volume-weighted α)
    ema_buying_ratio = db.Column(db.Numeric(8,4), nullable=True)            # EMA of buying percentage
    
    # Non-Weighted Averages (simple averages) - NEW FIELDS
    avg_net_score_10sec = db.Column(db.Numeric(8,4), nullable=True)         # Simple average last 10 seconds
    avg_net_score_60sec = db.Column(db.Numeric(8,4), nullable=True)         # Simple average last 60 seconds
    avg_net_score_300sec = db.Column(db.Numeric(8,4), nullable=True)        # Simple average last 5 minutes
    
    # ✅ FIXED: Upgraded to handle larger activity averages
    avg_activity_count_60sec = db.Column(db.Numeric(15,2), nullable=True)   # Was Numeric(10,2), now Numeric(15,2)
    
    # Session Context
    session_total_calculations = db.Column(db.Integer, default=0)           # Total calculations this session
    records_aggregated = db.Column(db.Integer, default=1)                  # Number of tick records aggregated
    calculation_window_seconds = db.Column(db.Integer, default=10)          # Aggregation window (10 seconds)
    
    # Performance & Metadata
    calc_time_ms = db.Column(db.Numeric(8,2), default=0)                   # Time to calculate aggregation
    window_start_time = db.Column(db.DateTime(timezone=True), nullable=True) # Start of calculation window
    window_end_time = db.Column(db.DateTime(timezone=True), nullable=True)   # End of calculation window
    
    # Universe Context - NEW FIELD
    total_universe_size = db.Column(db.Integer, nullable=False, default=0)  # Core universe size (~2800)
    
    # ✅ FIXED: Updated constraints for BIGINT support
    __table_args__ = (
        db.CheckConstraint('current_net_score BETWEEN -10 AND 10', name='valid_current_net_score'),
        db.CheckConstraint("current_activity_level IN ('Low', 'Moderate', 'High', 'Very High')", name='valid_current_activity_level'),
        db.CheckConstraint("data_source IN ('core', 'synthetic', 'replay')", name='valid_data_source'),
        db.CheckConstraint('current_buying_count >= 0', name='valid_buying_count'),      # BIGINT constraint
        db.CheckConstraint('current_selling_count >= 0', name='valid_selling_count'),   # BIGINT constraint
        db.CheckConstraint('current_activity_count >= 0', name='valid_activity_count'), # BIGINT constraint
        db.Index('idx_market_analytics_session_date', 'session_date'),
        db.Index('idx_market_analytics_timestamp', 'timestamp'),
        db.Index('idx_market_analytics_core_data', 'session_date', 'data_source', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<MarketAnalytics {self.session_date} {self.timestamp}: score={self.current_net_score}, activity={self.current_activity_count}, source={self.data_source}>'
    
    @classmethod
    @with_app_context
    def create_aggregated_record(cls, aggregated_data: Dict[str, Any]) -> 'MarketAnalytics':
        """
        Create a new aggregated market analytics record.
        Sprint 1: Single record per 10-second aggregation interval.
        
        Args:
            aggregated_data: Aggregated analytics data with EMA and simple averages
            
        Returns:
            MarketAnalytics: New aggregated record instance
        """
        try:
            record = cls(
                # Identity & Timing
                session_date=aggregated_data.get('session_date'),
                timestamp=aggregated_data.get('timestamp', datetime.now(timezone.utc)),
                data_source='core',  # Always 'core' for aggregated records
                
                # Current Values (latest in aggregation window)
                current_net_score=aggregated_data.get('current_net_score', 0),
                current_activity_level=aggregated_data.get('current_activity_level', 'Low'),
                current_buying_count=aggregated_data.get('current_buying_count', 0),
                current_selling_count=aggregated_data.get('current_selling_count', 0),
                current_activity_count=aggregated_data.get('current_activity_count', 0),
                
                # Weighted Averages (EMA calculations)
                ema_net_score_gauge=aggregated_data.get('ema_net_score_gauge'),
                ema_net_score_vertical=aggregated_data.get('ema_net_score_vertical'),
                ema_buying_ratio=aggregated_data.get('ema_buying_ratio'),
                
                # Non-Weighted Averages (simple averages)
                avg_net_score_10sec=aggregated_data.get('avg_net_score_10sec'),
                avg_net_score_60sec=aggregated_data.get('avg_net_score_60sec'),
                avg_net_score_300sec=aggregated_data.get('avg_net_score_300sec'),
                avg_activity_count_60sec=aggregated_data.get('avg_activity_count_60sec'),
                
                # Session Context
                session_total_calculations=aggregated_data.get('session_total_calculations', 1),
                records_aggregated=aggregated_data.get('records_aggregated', 1),
                calculation_window_seconds=aggregated_data.get('calculation_window_seconds', 10),
                
                # Performance metadata
                calc_time_ms=aggregated_data.get('calc_time_ms', 0),
                window_start_time=aggregated_data.get('window_start_time'),
                window_end_time=aggregated_data.get('window_end_time'),
                
                # Universe context
                total_universe_size=aggregated_data.get('total_universe_size', 0)
            )
            
            db.session.add(record)
            db.session.commit()
            
            return record
            
        except Exception as e:
            logger.error(f"Error creating aggregated market analytics record: {e}")
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return None

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