#!/usr/bin/env python3
"""
Debug route registration
"""

import eventlet
eventlet.monkey_patch(
    os=True, 
    select=True, 
    socket=True, 
    thread=True, 
    time=True
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask
from config.app_config import create_flask_app, initialize_flask_extensions
from config.logging_config import configure_logging
from src.core.services.config_manager import ConfigManager

# Minimal setup
config = ConfigManager()
configure_logging(config)

env_config = {
    'DATABASE_URI': 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock',
    'APP_HOST': 'localhost',
    'APP_PORT': '5000'
}

class MockCacheControl:
    def get_cache(self, key):
        return {}

cache_control = MockCacheControl()

# Create app
app = create_flask_app(env_config, cache_control, config)
extensions = initialize_flask_extensions(app)

print("=== BEFORE AUTH ROUTES ===")
print("Available routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.endpoint} -> {rule.rule} [{','.join(rule.methods)}]")

# Try to register auth routes
try:
    from src.api.rest.auth import register_auth_routes
    register_auth_routes(app, extensions, cache_control, config)
    print("\n=== AFTER AUTH ROUTES ===")
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.endpoint} -> {rule.rule} [{','.join(rule.methods)}]")
        
    # Look specifically for login
    login_rules = [rule for rule in app.url_map.iter_rules() if 'login' in rule.endpoint.lower()]
    print(f"\nLogin routes found: {len(login_rules)}")
    for rule in login_rules:
        print(f"  {rule.endpoint} -> {rule.rule} [{','.join(rule.methods)}]")
        
except Exception as e:
    print(f"Error registering auth routes: {e}")
    import traceback
    traceback.print_exc()