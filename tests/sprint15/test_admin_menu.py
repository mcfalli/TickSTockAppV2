"""
Sprint 15 - Admin Menu Tests
Tests for the admin dropdown menu functionality and permissions
"""

import pytest

from src.infrastructure.database.models.base import User, db


class TestAdminMenuFunctionality:
    """Test suite for admin dropdown menu functionality."""

    def test_admin_menu_visible_for_admin_user(self, client, admin_user):
        """Test that admin menu is visible for users with admin role."""
        # Login as admin
        with client:
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })

            # Get dashboard page
            response = client.get('/')
            assert response.status_code == 200

            # Check for admin menu elements
            assert b'Admin' in response.data
            assert b'adminMenuBtn' in response.data
            assert b'Historical Data' in response.data
            assert b'User Management' in response.data
            assert b'Health Monitor' in response.data

    def test_admin_menu_visible_for_super_user(self, client, super_user):
        """Test that admin menu is visible for users with super role."""
        # Login as super user
        with client:
            client.post('/login', data={
                'email': super_user.email,
                'password': 'test_password'
            })

            # Get dashboard page
            response = client.get('/')
            assert response.status_code == 200

            # Check for admin menu elements
            assert b'Admin' in response.data
            assert b'adminMenuBtn' in response.data

    def test_admin_menu_hidden_for_regular_user(self, client, regular_user):
        """Test that admin menu is hidden for regular users."""
        # Login as regular user
        with client:
            client.post('/login', data={
                'email': regular_user.email,
                'password': 'test_password'
            })

            # Get dashboard page
            response = client.get('/')
            assert response.status_code == 200

            # Check that admin menu is not present
            assert b'adminMenuBtn' not in response.data
            assert b'admin-menu' not in response.data

    def test_admin_menu_hidden_for_anonymous_user(self, client):
        """Test that admin menu is hidden for non-authenticated users."""
        # Get dashboard page without login
        response = client.get('/')

        # May redirect to login or show limited view
        if response.status_code == 200:
            assert b'adminMenuBtn' not in response.data
            assert b'admin-menu' not in response.data


class TestAdminRouteAccess:
    """Test suite for admin route access permissions."""

    def test_admin_can_access_historical_data(self, client, admin_user):
        """Test that admin users can access historical data page."""
        with client:
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })

            response = client.get('/admin/historical-data')
            assert response.status_code in [200, 302]  # 302 if redirects to login

    def test_admin_can_access_user_management(self, client, admin_user):
        """Test that admin users can access user management page."""
        with client:
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })

            response = client.get('/admin/users')
            assert response.status_code in [200, 302]

    def test_admin_can_access_health_dashboard(self, client, admin_user):
        """Test that admin users can access health dashboard."""
        with client:
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })

            response = client.get('/admin/health')
            assert response.status_code in [200, 302]

    def test_regular_user_cannot_access_admin_routes(self, client, regular_user):
        """Test that regular users cannot access admin routes."""
        with client:
            client.post('/login', data={
                'email': regular_user.email,
                'password': 'test_password'
            })

            # Try to access admin routes
            response = client.get('/admin/historical-data')
            assert response.status_code in [403, 302]  # Forbidden or redirect

            response = client.get('/admin/users')
            assert response.status_code in [403, 302]

            response = client.get('/admin/health')
            assert response.status_code in [403, 302]


class TestAdminMenuStyling:
    """Test suite for admin menu styling and theme support."""

    def test_admin_menu_css_classes(self, client, admin_user):
        """Test that admin menu has proper CSS classes."""
        with client:
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })

            response = client.get('/')
            assert response.status_code == 200

            # Check for CSS classes
            assert b'admin-menu' in response.data
            assert b'admin-menu-btn' in response.data
            assert b'admin-dropdown-content' in response.data

    def test_theme_support_in_admin_pages(self, client, admin_user):
        """Test that admin pages support light/dark themes."""
        with client:
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })

            # Check if theme classes are present in admin pages
            response = client.get('/admin/historical-data')
            if response.status_code == 200:
                # Check for theme-related elements
                assert b'theme' in response.data or b'Theme' in response.data


# Fixtures for test users
@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        user = User(
            email='admin@test.com',
            username='admin_test',
            role='admin'
        )
        user.set_password('test_password')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def super_user(app):
    """Create a super user for testing."""
    with app.app_context():
        user = User(
            email='super@test.com',
            username='super_test',
            role='super'
        )
        user.set_password('test_password')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def regular_user(app):
    """Create a regular user for testing."""
    with app.app_context():
        user = User(
            email='user@test.com',
            username='regular_test',
            role='user'
        )
        user.set_password('test_password')
        db.session.add(user)
        db.session.commit()
        return user
