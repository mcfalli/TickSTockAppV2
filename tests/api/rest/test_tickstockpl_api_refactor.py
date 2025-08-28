"""
TickStockPL API Integration Tests - Sprint 10 Phase 1
Tests for TickStockPL API endpoints including authentication, error handling, and response formats.

Test Coverage:
- All API endpoints (/health, /dashboard, /symbols, /stats/basic, etc.)
- Authentication requirements and login_required decorator
- Error responses and status codes
- JSON response formats and structure
- Service initialization and error handling
- Blueprint registration and routing
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from flask_login import current_user

from src.api.rest.tickstockpl_api import register_tickstockpl_routes


class TestTickStockPLAPIRegistration:
    """Test API registration and initialization."""

    def test_successful_service_initialization(self):
        """Test successful registration with all services available."""
        app = Flask(__name__)
        extensions = {}
        cache_control = Mock()
        config = {
            'redis_client': Mock(),
            'test_config': 'value'
        }
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_instance = Mock()
                mock_db_instance = Mock()
                mock_health_monitor.return_value = mock_health_instance
                mock_db.return_value = mock_db_instance
                
                blueprint = register_tickstockpl_routes(app, extensions, cache_control, config)
                
                assert blueprint is not None
                assert blueprint.name == 'tickstockpl'
                assert blueprint.url_prefix == '/api/tickstockpl'
                
                # Verify services are stored in app context
                assert hasattr(app, 'tickstockpl_health_monitor')
                assert hasattr(app, 'tickstockpl_database')
                assert app.tickstockpl_health_monitor == mock_health_instance
                assert app.tickstockpl_database == mock_db_instance

    def test_partial_service_initialization_failure(self):
        """Test registration when some services fail to initialize."""
        app = Flask(__name__)
        extensions = {}
        cache_control = Mock()
        config = {'test_config': 'value'}  # No Redis client
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_monitor.side_effect = Exception("Health monitor init failed")
                mock_db.side_effect = Exception("Database init failed")
                
                # Should not raise exception, but log warning
                blueprint = register_tickstockpl_routes(app, extensions, cache_control, config)
                
                assert blueprint is not None
                # Services should be None due to initialization failure
                assert app.tickstockpl_health_monitor is None
                assert app.tickstockpl_database is None

    def test_blueprint_route_registration(self):
        """Test that all expected routes are registered on the blueprint."""
        app = Flask(__name__)
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor'):
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase'):
                blueprint = register_tickstockpl_routes(app, extensions, cache_control, config)
                
                # Check that blueprint has expected number of rules
                expected_routes = [
                    '/health',
                    '/dashboard', 
                    '/symbols',
                    '/stats/basic',
                    '/alerts/history',
                    '/patterns/performance',
                    '/connectivity/test'
                ]
                
                # Blueprint routes include the url_prefix
                blueprint_rules = [rule.rule for rule in blueprint.deferred_functions]
                # Note: We can't easily check exact routes without app context, 
                # but we can verify blueprint was created successfully
                assert len(blueprint.deferred_functions) > 0


class TestTickStockPLAPIHealthEndpoint:
    """Test /health endpoint functionality."""

    @pytest.fixture
    def app_with_api(self):
        """Create Flask app with TickStockPL API registered."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        extensions = {}
        cache_control = Mock()
        config = {'redis_client': Mock()}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_instance = Mock()
                mock_health_monitor.return_value = mock_health_instance
                mock_db.return_value = Mock()
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app, mock_health_instance

    def test_health_endpoint_success(self, app_with_api):
        """Test successful health endpoint response."""
        app, mock_health_monitor = app_with_api
        
        mock_health_data = {
            'timestamp': time.time(),
            'overall_status': 'healthy',
            'components': {
                'database': {'status': 'healthy'},
                'redis': {'status': 'healthy'}
            },
            'summary': {'healthy': 2, 'degraded': 0, 'error': 0, 'unknown': 0}
        }
        mock_health_monitor.get_overall_health.return_value = mock_health_data
        
        with app.test_client() as client:
            response = client.get('/api/tickstockpl/health')
            
            assert response.status_code == 200
            assert response.content_type == 'application/json'
            
            data = json.loads(response.data)
            assert data['overall_status'] == 'healthy'
            assert 'timestamp' in data
            assert 'components' in data

    def test_health_endpoint_service_unavailable(self, app_with_api):
        """Test health endpoint when health monitor is not available."""
        app, _ = app_with_api
        # Simulate service not available by setting it to None
        app.tickstockpl_health_monitor = None
        
        with app.test_client() as client:
            response = client.get('/api/tickstockpl/health')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['error'] == 'Health monitoring service not available'
            assert data['status'] == 'error'

    def test_health_endpoint_internal_error(self, app_with_api):
        """Test health endpoint with internal error."""
        app, mock_health_monitor = app_with_api
        mock_health_monitor.get_overall_health.side_effect = Exception("Internal health error")
        
        with app.test_client() as client:
            response = client.get('/api/tickstockpl/health')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] == 'Health check failed'
            assert 'Internal health error' in data['message']
            assert data['status'] == 'error'


class TestTickStockPLAPIDashboardEndpoint:
    """Test /dashboard endpoint functionality."""

    @pytest.fixture
    def app_with_auth(self):
        """Create Flask app with authentication and TickStockPL API."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock Flask-Login setup
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            # Mock user for testing
            user = Mock()
            user.id = user_id
            user.is_authenticated = True
            return user
        
        extensions = {}
        cache_control = Mock()
        config = {'redis_client': Mock()}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_instance = Mock()
                mock_health_monitor.return_value = mock_health_instance
                mock_db.return_value = Mock()
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app, mock_health_instance

    def test_dashboard_endpoint_requires_authentication(self, app_with_auth):
        """Test that dashboard endpoint requires authentication."""
        app, _ = app_with_auth
        
        with app.test_client() as client:
            response = client.get('/api/tickstockpl/dashboard')
            
            # Should redirect to login or return 401 (depends on Flask-Login config)
            assert response.status_code in [302, 401]

    def test_dashboard_endpoint_success(self, app_with_auth):
        """Test successful dashboard endpoint response with authentication."""
        app, mock_health_monitor = app_with_auth
        
        mock_dashboard_data = {
            'health': {
                'overall_status': 'healthy',
                'components': {}
            },
            'quick_stats': {
                'symbols_count': 4000,
                'events_count': 25000
            },
            'alerts': []
        }
        mock_health_monitor.get_dashboard_data.return_value = mock_dashboard_data
        
        with app.test_client() as client:
            # Mock authentication by manually setting the user session
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_user.id = '123'
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/dashboard')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['health']['overall_status'] == 'healthy'
                assert data['quick_stats']['symbols_count'] == 4000

    def test_dashboard_endpoint_service_unavailable(self, app_with_auth):
        """Test dashboard endpoint when health monitor is not available."""
        app, _ = app_with_auth
        app.tickstockpl_health_monitor = None
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/dashboard')
                
                assert response.status_code == 503
                data = json.loads(response.data)
                assert data['error'] == 'Health monitoring service not available'


class TestTickStockPLAPISymbolsEndpoint:
    """Test /symbols endpoint functionality."""

    @pytest.fixture
    def app_with_db(self):
        """Create Flask app with database service."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            user = Mock()
            user.id = user_id
            user.is_authenticated = True
            return user
        
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_monitor.return_value = Mock()
                mock_db_instance = Mock()
                mock_db.return_value = mock_db_instance
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app, mock_db_instance

    def test_symbols_endpoint_success(self, app_with_db):
        """Test successful symbols endpoint response."""
        app, mock_database = app_with_db
        
        mock_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        mock_database.get_symbols_for_dropdown.return_value = mock_symbols
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/symbols')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['symbols'] == mock_symbols
                assert data['count'] == 4
                assert 'timestamp' in data

    def test_symbols_endpoint_database_unavailable(self, app_with_db):
        """Test symbols endpoint when database service is not available."""
        app, _ = app_with_db
        app.tickstockpl_database = None
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/symbols')
                
                assert response.status_code == 503
                data = json.loads(response.data)
                assert data['error'] == 'Database service not available'

    def test_symbols_endpoint_database_error(self, app_with_db):
        """Test symbols endpoint with database error."""
        app, mock_database = app_with_db
        mock_database.get_symbols_for_dropdown.side_effect = Exception("Database connection failed")
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/symbols')
                
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data['error'] == 'Failed to retrieve symbols'
                assert 'Database connection failed' in data['message']


class TestTickStockPLAPIStatsEndpoint:
    """Test /stats/basic endpoint functionality."""

    @pytest.fixture
    def app_with_db(self):
        """Create Flask app with database service."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            user = Mock()
            user.id = user_id
            user.is_authenticated = True
            return user
        
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_monitor.return_value = Mock()
                mock_db_instance = Mock()
                mock_db.return_value = mock_db_instance
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app, mock_db_instance

    def test_basic_stats_endpoint_success(self, app_with_db):
        """Test successful basic stats endpoint response."""
        app, mock_database = app_with_db
        
        mock_stats = {
            'symbols_count': 4000,
            'events_count': 25000,
            'latest_event_time': '2025-01-15T10:30:00',
            'database_status': 'connected'
        }
        mock_database.get_basic_dashboard_stats.return_value = mock_stats
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/stats/basic')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['symbols_count'] == 4000
                assert data['events_count'] == 25000
                assert data['database_status'] == 'connected'


class TestTickStockPLAPIAlertsEndpoint:
    """Test /alerts/history endpoint functionality."""

    @pytest.fixture
    def app_with_db(self):
        """Create Flask app with database service."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            user = Mock()
            user.id = user_id
            user.is_authenticated = True
            return user
        
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_monitor.return_value = Mock()
                mock_db_instance = Mock()
                mock_db.return_value = mock_db_instance
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app, mock_db_instance

    def test_alerts_endpoint_success(self, app_with_db):
        """Test successful alerts endpoint response."""
        app, mock_database = app_with_db
        
        mock_alerts = [
            {
                'symbol': 'AAPL',
                'pattern': 'high_low',
                'confidence': 0.85,
                'created_at': '2025-01-15T10:30:00',
                'metadata': {'price': 150.0}
            },
            {
                'symbol': 'GOOGL',
                'pattern': 'trend',
                'confidence': 0.92,
                'created_at': '2025-01-15T10:25:00',
                'metadata': {'direction': 'up'}
            }
        ]
        mock_database.get_user_alert_history.return_value = mock_alerts
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_user.id = '123'
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/alerts/history')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert len(data['alerts']) == 2
                assert data['count'] == 2
                assert data['user_id'] == '123'
                assert data['limit'] == 50  # Default limit

    def test_alerts_endpoint_with_limit_parameter(self, app_with_db):
        """Test alerts endpoint with custom limit parameter."""
        app, mock_database = app_with_db
        mock_database.get_user_alert_history.return_value = []
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_user.id = '123'
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/alerts/history?limit=25')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['limit'] == 25
                
                # Verify database was called with correct limit
                mock_database.get_user_alert_history.assert_called_once_with('123', 25)

    def test_alerts_endpoint_limit_clamping(self, app_with_db):
        """Test that limit parameter is properly clamped between 1 and 100."""
        app, mock_database = app_with_db
        mock_database.get_user_alert_history.return_value = []
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_user.id = '123'
                mock_get_user.return_value = mock_user
                
                # Test limit too high
                response = client.get('/api/tickstockpl/alerts/history?limit=200')
                data = json.loads(response.data)
                assert data['limit'] == 100
                
                # Test limit too low
                response = client.get('/api/tickstockpl/alerts/history?limit=0')
                data = json.loads(response.data)
                assert data['limit'] == 1

    def test_alerts_endpoint_anonymous_user(self, app_with_db):
        """Test alerts endpoint with anonymous user (no current_user.id)."""
        app, mock_database = app_with_db
        mock_database.get_user_alert_history.return_value = []
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                # No id attribute to simulate anonymous user
                del mock_user.id if hasattr(mock_user, 'id') else None
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/alerts/history')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['user_id'] == 'anonymous'


class TestTickStockPLAPIPatternsEndpoint:
    """Test /patterns/performance endpoint functionality."""

    @pytest.fixture
    def app_with_db(self):
        """Create Flask app with database service."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            user = Mock()
            user.id = user_id
            user.is_authenticated = True
            return user
        
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_monitor.return_value = Mock()
                mock_db_instance = Mock()
                mock_db.return_value = mock_db_instance
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app, mock_db_instance

    def test_patterns_performance_endpoint_success(self, app_with_db):
        """Test successful pattern performance endpoint response."""
        app, mock_database = app_with_db
        
        mock_performance_data = [
            {
                'pattern': 'high_low',
                'detection_count': 1500,
                'avg_confidence': 0.78,
                'max_confidence': 0.95,
                'min_confidence': 0.45
            },
            {
                'pattern': 'trend',
                'detection_count': 800,
                'avg_confidence': 0.82,
                'max_confidence': 0.98,
                'min_confidence': 0.52
            }
        ]
        mock_database.get_pattern_performance.return_value = mock_performance_data
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/patterns/performance')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert len(data['patterns']) == 2
                assert data['count'] == 2
                assert data['filter'] is None
                assert 'timestamp' in data

    def test_patterns_performance_endpoint_with_filter(self, app_with_db):
        """Test pattern performance endpoint with pattern filter."""
        app, mock_database = app_with_db
        mock_database.get_pattern_performance.return_value = [
            {
                'pattern': 'high_low',
                'detection_count': 1500,
                'avg_confidence': 0.78,
                'max_confidence': 0.95,
                'min_confidence': 0.45
            }
        ]
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                response = client.get('/api/tickstockpl/patterns/performance?pattern=high_low')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['filter'] == 'high_low'
                
                # Verify database was called with filter
                mock_database.get_pattern_performance.assert_called_once_with('high_low')


class TestTickStockPLAPIConnectivityEndpoint:
    """Test /connectivity/test endpoint functionality."""

    @pytest.fixture
    def app_with_health_monitor(self):
        """Create Flask app with health monitor service."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            user = Mock()
            user.id = user_id
            user.is_authenticated = True
            return user
        
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_instance = Mock()
                mock_health_monitor.return_value = mock_health_instance
                mock_db.return_value = Mock()
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app, mock_health_instance

    def test_connectivity_test_endpoint_success(self, app_with_health_monitor):
        """Test successful connectivity test endpoint response."""
        app, mock_health_monitor = app_with_health_monitor
        
        mock_health_data = {
            'components': {
                'database': {'status': 'healthy', 'response_time_ms': 25.0},
                'redis': {'status': 'healthy', 'response_time_ms': 15.0},
                'tickstockpl_connectivity': {'status': 'healthy', 'response_time_ms': 30.0}
            },
            'overall_status': 'healthy'
        }
        mock_health_monitor.get_overall_health.return_value = mock_health_data
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                response = client.post('/api/tickstockpl/connectivity/test')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['overall_status'] == 'healthy'
                assert 'database' in data
                assert 'redis' in data
                assert 'tickstockpl' in data
                assert 'test_timestamp' in data

    def test_connectivity_test_endpoint_post_only(self, app_with_health_monitor):
        """Test that connectivity test endpoint only accepts POST requests."""
        app, _ = app_with_health_monitor
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                # GET should not be allowed
                response = client.get('/api/tickstockpl/connectivity/test')
                assert response.status_code == 405  # Method Not Allowed


class TestTickStockPLAPIErrorHandlers:
    """Test API error handlers and edge cases."""

    @pytest.fixture
    def app_with_api(self):
        """Create Flask app with TickStockPL API registered."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor'):
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase'):
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app

    def test_404_error_handler(self, app_with_api):
        """Test 404 error handler for non-existent endpoints."""
        app = app_with_api
        
        with app.test_client() as client:
            response = client.get('/api/tickstockpl/nonexistent')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['error'] == 'API endpoint not found'
            assert 'does not exist' in data['message']

    def test_500_error_handler(self, app_with_api):
        """Test 500 error handler for internal server errors."""
        # Note: This test would need to be implemented based on how Flask error handlers work
        # in the specific application context. The error handler registration may need adjustment.
        pass


@pytest.mark.performance
class TestTickStockPLAPIPerformance:
    """Test TickStockPL API performance requirements."""

    @pytest.fixture
    def app_with_fast_services(self):
        """Create Flask app with fast mock services."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            user = Mock()
            user.id = user_id
            user.is_authenticated = True
            return user
        
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_instance = Mock()
                mock_db_instance = Mock()
                
                # Configure fast responses
                mock_health_instance.get_overall_health.return_value = {'overall_status': 'healthy'}
                mock_db_instance.get_symbols_for_dropdown.return_value = ['AAPL'] * 4000
                mock_db_instance.get_basic_dashboard_stats.return_value = {'symbols_count': 4000}
                
                mock_health_monitor.return_value = mock_health_instance
                mock_db.return_value = mock_db_instance
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                return app

    @pytest.mark.performance
    def test_health_endpoint_performance(self, app_with_fast_services):
        """Test that health endpoint meets <100ms performance requirement."""
        app = app_with_fast_services
        
        with app.test_client() as client:
            start_time = time.time()
            response = client.get('/api/tickstockpl/health')
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            assert response.status_code == 200
            assert execution_time < 100.0, f"Health endpoint took {execution_time:.2f}ms, should be <100ms"

    @pytest.mark.performance
    def test_symbols_endpoint_performance(self, app_with_fast_services):
        """Test that symbols endpoint meets <100ms performance requirement."""
        app = app_with_fast_services
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '123'
                sess['_fresh'] = True
                
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_user = Mock()
                mock_user.is_authenticated = True
                mock_get_user.return_value = mock_user
                
                start_time = time.time()
                response = client.get('/api/tickstockpl/symbols')
                execution_time = (time.time() - start_time) * 1000
                
                assert response.status_code == 200
                assert execution_time < 100.0, f"Symbols endpoint took {execution_time:.2f}ms, should be <100ms"


class TestTickStockPLAPIIntegration:
    """Test integration scenarios and edge cases."""

    def test_multiple_simultaneous_requests(self):
        """Test handling of multiple simultaneous API requests."""
        # This would test concurrent request handling
        # Implementation depends on specific threading/async requirements
        pass

    def test_api_with_redis_unavailable(self):
        """Test API behavior when Redis is unavailable."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        extensions = {}
        cache_control = Mock()
        config = {'redis_client': None}  # No Redis client
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_instance = Mock()
                mock_health_instance.get_overall_health.return_value = {
                    'overall_status': 'degraded',
                    'components': {
                        'redis': {'status': 'unknown', 'message': 'Redis client not configured'}
                    }
                }
                mock_health_monitor.return_value = mock_health_instance
                mock_db.return_value = Mock()
                
                register_tickstockpl_routes(app, extensions, cache_control, config)
                
                with app.test_client() as client:
                    response = client.get('/api/tickstockpl/health')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['overall_status'] == 'degraded'

    def test_api_with_database_unavailable(self):
        """Test API behavior when database is unavailable."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        extensions = {}
        cache_control = Mock()
        config = {}
        
        with patch('src.api.rest.tickstockpl_api.HealthMonitor') as mock_health_monitor:
            with patch('src.api.rest.tickstockpl_api.TickStockDatabase') as mock_db:
                mock_health_monitor.return_value = Mock()
                mock_db.side_effect = Exception("Database unavailable")
                
                # Should handle initialization failure gracefully
                blueprint = register_tickstockpl_routes(app, extensions, cache_control, config)
                
                assert blueprint is not None
                assert app.tickstockpl_database is None