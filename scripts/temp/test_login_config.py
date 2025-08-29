#!/usr/bin/env python3
"""
Test Flask-Login configuration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import eventlet
eventlet.monkey_patch(
    os=True, 
    select=True, 
    socket=True, 
    thread=True, 
    time=True
)

from flask import Flask
from flask_login import LoginManager

# Create a minimal Flask app to test the configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'

login_manager = LoginManager(app)

print(f"Initial login_view: {login_manager.login_view}")
print(f"Initial login_message: {login_manager.login_message}")

# Set the configuration
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

print(f"After config login_view: {login_manager.login_view}")
print(f"After config login_message: {login_manager.login_message}")

# Test a simple route
@app.route('/')
@login_manager.unauthorized
def index():
    return "Dashboard"

@app.route('/login')
def login():
    return "Login page"

# Test the unauthorized handler
with app.test_client() as client:
    print("\nTesting unauthorized access to /:")
    response = client.get('/', follow_redirects=False)
    print(f"Status code: {response.status_code}")
    print(f"Location header: {response.headers.get('Location', 'Not set')}")
    print(f"Response data: {response.get_data(as_text=True)}")