"""
Application Form Definitions
All WTForms form classes used throughout the application.
"""

import logging

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length

logger = logging.getLogger(__name__)

class RegisterForm(FlaskForm):
    """User registration form with subscription and billing information."""

    # User information
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message="Invalid email address. Must include a valid domain (e.g., .com, .org)")
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(),
        Length(min=1, max=100)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(),
        Length(min=1, max=100)
    ])
    username = StringField('Display Name', validators=[
        DataRequired(),
        Length(min=5, max=50, message="Display Name must be 5-50 characters")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8)
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        Length(min=8)
    ])
    phone = StringField('Phone', validators=[DataRequired()])

    # Billing address fields
    address_line1 = StringField('Address Line 1', validators=[Length(max=255)])
    address_line2 = StringField('Address Line 2', validators=[Length(max=255)])
    city = StringField('City', validators=[Length(max=100)])
    state_province = StringField('State/Province', validators=[Length(max=100)])
    postal_code = StringField('Postal/ZIP Code', validators=[Length(max=20)])
    country = StringField('Country', validators=[Length(max=100)])

    # Subscription - SINGLE TIER CHECKBOX WITH REQUIRED VALIDATION
    subscription = BooleanField('Subscribe to TickStock Premium', validators=[
        DataRequired(message="You must subscribe to TickStock Premium to register")
    ])
    # UPDATED: Remove length validation to allow formatted card numbers with spaces
    card_number = StringField('Card Number')
    expiry = StringField('Expiry (MM/YY)', validators=[Length(max=5)])
    cvv = StringField('CVV', validators=[Length(max=4)])

    # Terms acceptance
    terms_accepted = BooleanField('Terms Accepted', validators=[DataRequired()])

    # Hidden fields
    fingerprint_data = HiddenField('Fingerprint Data')
    captcha_response = BooleanField('CAPTCHA (stub)', validators=[DataRequired()])

    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    """User login form."""

    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    terms_accepted = BooleanField(
        'I accept the <a href="/terms" target="_blank">Terms and Conditions</a>',
        validators=[DataRequired()]
    )
    captcha_response = BooleanField('CAPTCHA (stub)', validators=[DataRequired()])
    fingerprint_data = HiddenField()
    submit = SubmitField('Login')


class ChangePasswordForm(FlaskForm):
    """Change password form for authenticated users."""

    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, max=64)
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired()])
    captcha_response = BooleanField('CAPTCHA (stub)', validators=[DataRequired()])
    submit = SubmitField('Change Password')


class InitiatePasswordResetForm(FlaskForm):
    """Form to initiate password reset process."""

    email = StringField('Email', validators=[DataRequired(), Email()])
    captcha_response = BooleanField('CAPTCHA (stub)', validators=[DataRequired()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    """Password reset form with SMS verification."""

    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, max=64)
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired()])
    verification_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6)
    ])
    captcha_response = BooleanField('CAPTCHA (stub)', validators=[DataRequired()])
    submit = SubmitField('Reset Password')


class SubscriptionRenewalForm(FlaskForm):
    """Subscription renewal form for expired users."""

    # Contact information
    phone = StringField('Phone')

    # Billing address
    address_line1 = StringField('Address Line 1', validators=[DataRequired()])
    address_line2 = StringField('Address Line 2')
    city = StringField('City', validators=[DataRequired()])
    state_province = StringField('State/Province')
    postal_code = StringField('Postal/ZIP Code', validators=[DataRequired()])
    country = StringField('Country', validators=[DataRequired()])

    # Payment information
    card_number = StringField('Card Number', validators=[
        DataRequired(),
        Length(min=13, max=19)
    ])
    expiry = StringField('Expiry', validators=[
        DataRequired(),
        Length(min=5, max=5)
    ])
    cvv = StringField('CVV', validators=[
        DataRequired(),
        Length(min=3, max=4)
    ])

    # CAPTCHA
    captcha_response = BooleanField('CAPTCHA (stub)', validators=[DataRequired()])

    submit = SubmitField('Renew Subscription - $29.99')


class UpdateCardForm(FlaskForm):
    """Form to update payment method."""

    card_number = StringField('Card Number', validators=[
        DataRequired(),
        Length(min=13, max=19)
    ])
    expiry = StringField('Expiry', validators=[
        DataRequired(),
        Length(min=5, max=5)
    ])
    cvv = StringField('CVV', validators=[
        DataRequired(),
        Length(min=3, max=4)
    ])
    action = HiddenField(default='update_card')
    submit = SubmitField('Save Payment Method')


class UpdateEmailForm(FlaskForm):
    """Form to update user email address."""

    email = StringField('New Email', validators=[DataRequired(), Email()])
    submit_email = SubmitField('Update Email')


class UpdatePhoneForm(FlaskForm):
    """Form to update user phone number."""

    phone = StringField('New Phone', validators=[DataRequired()])
    submit_phone = SubmitField('Update Phone')


class VerifyPhoneForm(FlaskForm):
    """Form to verify phone number with SMS code."""

    verification_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6)
    ])
    submit = SubmitField('Verify')
