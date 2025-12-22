"""
Authentication and authorization decorators for TickStock admin system.
"""

import logging
from functools import wraps

from flask import abort, request
from flask_login import current_user

logger = logging.getLogger(__name__)

def admin_required(f):
    """
    Decorator to require admin role for route access.
    Allows both 'admin' and 'super' roles.
    
    Usage:
        @admin_required
        @login_required
        def admin_route():
            # Admin-only logic here
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            logger.warning(f"Unauthenticated user attempted to access admin route: {request.endpoint}")
            abort(401)

        if not current_user.is_admin():
            logger.warning(f"Non-admin user {current_user.email} (role: {current_user.role}) attempted to access admin route: {request.endpoint}")
            abort(403)

        #logger.info(f"Admin user {current_user.email} (role: {current_user.role}) accessed admin route: {request.endpoint}")
        return f(*args, **kwargs)

    return decorated_function

def role_required(required_role):
    """
    Decorator to require specific role for route access.
    
    Usage:
        @role_required('admin')
        @login_required
        def admin_route():
            # Admin-only logic here
            
        @role_required('moderator')
        @login_required
        def moderator_route():
            # Moderator-only logic here
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                logger.warning(f"Unauthenticated user attempted to access {required_role} route: {request.endpoint}")
                abort(401)

            if not current_user.has_role(required_role):
                logger.warning(f"User {current_user.email} with role {current_user.role} attempted to access {required_role} route: {request.endpoint}")
                abort(403)

            logger.info(f"User {current_user.email} with role {current_user.role} accessed {required_role} route: {request.endpoint}")
            return f(*args, **kwargs)

        return decorated_function
    return decorator

def super_required(f):
    """
    Decorator to require super role for route access.
    Only allows 'super' role (highest privilege level).
    
    Usage:
        @super_required
        @login_required
        def super_route():
            # Super-only logic here
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            logger.warning(f"Unauthenticated user attempted to access super route: {request.endpoint}")
            abort(401)

        if not current_user.is_super():
            logger.warning(f"Non-super user {current_user.email} (role: {current_user.role}) attempted to access super route: {request.endpoint}")
            abort(403)

        logger.info(f"Super user {current_user.email} accessed super route: {request.endpoint}")
        return f(*args, **kwargs)

    return decorated_function
