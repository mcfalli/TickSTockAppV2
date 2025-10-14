"""
Admin user management routes for TickStock application.
"""

import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from src.infrastructure.database.models.base import User, db
from src.utils.auth_decorators import admin_required

logger = logging.getLogger(__name__)

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin')

@admin_users_bp.route('/users')
@login_required
@admin_required
def users_dashboard():
    """Admin dashboard for user management."""
    try:
        # Get all users with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20

        users = User.query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Get role statistics
        role_stats = db.session.query(
            User.role,
            db.func.count(User.id).label('count')
        ).group_by(User.role).all()

        # Get recent users (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users_count = User.query.filter(User.created_at >= week_ago).count()

        stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter(User.is_active == True).count(),
            'verified_users': User.query.filter(User.is_verified == True).count(),
            'recent_users': recent_users_count,
            'role_breakdown': dict(role_stats)
        }

        return render_template('admin/users_dashboard.html',
                             users=users,
                             stats=stats)

    except Exception as e:
        logger.error(f"Error loading users dashboard: {e}")
        flash(f"Error loading users: {str(e)}", 'error')
        return redirect(url_for('admin_historical_dashboard'))

@admin_users_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    """Update user role via AJAX."""
    try:
        user = User.query.get_or_404(user_id)
        new_role = request.json.get('role')

        if new_role not in ['user', 'admin', 'moderator', 'super']:
            return jsonify({'success': False, 'error': 'Invalid role'}), 400

        # Don't let user remove their own admin/super privileges
        if user.id == current_user.id and new_role not in ['admin', 'super']:
            return jsonify({'success': False, 'error': 'Cannot remove your own admin privileges'}), 400

        old_role = user.role
        user.role = new_role
        db.session.commit()

        logger.info(f"Admin {current_user.email} changed user {user.email} role from {old_role} to {new_role}")

        return jsonify({
            'success': True,
            'message': f'User role updated to {new_role}',
            'user_id': user_id,
            'new_role': new_role
        })

    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_users_bp.route('/users/<int:user_id>/status', methods=['POST'])
@login_required
@admin_required
def update_user_status(user_id):
    """Update user active/disabled status via AJAX."""
    try:
        user = User.query.get_or_404(user_id)
        action = request.json.get('action')

        # Don't let user disable themselves
        if user.id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot modify your own account status'}), 400

        if action == 'activate':
            user.is_active = True
            user.is_disabled = False
            message = f'User {user.email} activated'
        elif action == 'deactivate':
            user.is_active = False
            message = f'User {user.email} deactivated'
        elif action == 'disable':
            user.is_disabled = True
            user.is_active = False
            message = f'User {user.email} disabled'
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400

        db.session.commit()

        logger.info(f"Admin {current_user.email} {action}d user {user.email}")

        return jsonify({
            'success': True,
            'message': message,
            'user_id': user_id,
            'is_active': user.is_active,
            'is_disabled': user.is_disabled
        })

    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_users_bp.route('/health')
@login_required
@admin_required
def health_dashboard():
    """Display TickStockPL integration health dashboard for admins."""
    return render_template('admin/health_dashboard.html')
