"""
Integration tests for Process Stock Analysis admin workflow.

Sprint 73: Independent Analysis Page - End-to-end workflow tests
Tests job submission, status polling, background execution, and cancellation.
"""

import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
from datetime import datetime


class TestProcessAnalysisWorkflow(unittest.TestCase):
    """Test complete process stock analysis workflow."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal Flask app for testing
        from flask import Flask
        from flask_login import login_user, LoginManager
        from src.api.rest.admin_process_analysis import admin_process_analysis_bp

        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False

        # Setup login manager
        login_manager = LoginManager()
        login_manager.init_app(self.app)

        @login_manager.user_loader
        def load_user(user_id):
            # Return mock user
            user = Mock()
            user.id = 'test-user'
            user.username = 'test-admin'
            user.is_admin = True
            user.is_authenticated = True
            user.is_active = True
            user.is_anonymous = False
            return user

        # Register blueprint
        self.app.register_blueprint(admin_process_analysis_bp)
        self.client = self.app.test_client()

        # Setup mock user for authenticated requests
        with self.app.test_request_context():
            user = Mock()
            user.id = 'test-user'
            user.username = 'test-admin'
            user.is_admin = True
            user.is_authenticated = True
            user.is_active = True
            user.is_anonymous = False
            user.get_id = lambda: 'test-user'
            login_user(user)

    def test_dashboard_loads(self):
        """Test that dashboard page loads successfully."""
        # Mock admin check (decorator would normally handle this)
        def admin_required_mock(f):
            return f

        with patch('src.utils.auth_decorators.admin_required', admin_required_mock):
            with patch('flask_login.utils._get_user') as mock_get_user:
                user = Mock()
                user.is_authenticated = True
                user.is_admin = True
                mock_get_user.return_value = user

                response = self.client.get('/admin/process-analysis')
                self.assertEqual(response.status_code, 200)

    def test_job_submission_with_universe(self):
        """Test job submission with universe selection."""
        request_data = {
            'universe_key': 'nasdaq100',
            'symbols': '',
            'analysis_type': 'both',
            'timeframe': 'daily'
        }

        # Mock admin check and login
        def admin_required_mock(f):
            return f

        with patch('src.utils.auth_decorators.admin_required', admin_required_mock):
            with patch('flask_login.utils._get_user') as mock_get_user:
                with patch('src.core.services.relationship_cache.get_relationship_cache') as mock_cache:
                    # Mock relationship cache
                    mock_cache_instance = MagicMock()
                    mock_cache.return_value = mock_cache_instance
                    mock_cache_instance.get_universe_symbols.return_value = ['AAPL', 'NVDA', 'TSLA']

                    user = Mock()
                    user.username = 'test-admin'
                    user.is_authenticated = True
                    user.is_admin = True
                    mock_get_user.return_value = user

                    response = self.client.post(
                        '/admin/process-analysis/trigger',
                        data=json.dumps(request_data),
                        content_type='application/json'
                    )

                    self.assertEqual(response.status_code, 202)  # 202 Accepted

                    data = json.loads(response.data)
                    self.assertTrue(data['success'])
                    self.assertIn('job_id', data)
                    self.assertEqual(data['symbols_count'], 3)
                    self.assertEqual(data['analysis_type'], 'both')

    def test_job_submission_with_symbols(self):
        """Test job submission with manual symbol entry."""
        request_data = {
            'universe_key': '',
            'symbols': 'AAPL, NVDA, TSLA',
            'analysis_type': 'patterns',
            'timeframe': 'daily'
        }

        # Mock admin check and login
        def admin_required_mock(f):
            return f

        with patch('src.utils.auth_decorators.admin_required', admin_required_mock):
            with patch('flask_login.utils._get_user') as mock_get_user:
                user = Mock()
                user.username = 'test-admin'
                user.is_authenticated = True
                user.is_admin = True
                mock_get_user.return_value = user

                response = self.client.post(
                    '/admin/process-analysis/trigger',
                    data=json.dumps(request_data),
                    content_type='application/json'
                )

                self.assertEqual(response.status_code, 202)

                data = json.loads(response.data)
                self.assertTrue(data['success'])
                self.assertEqual(data['symbols_count'], 3)

    def test_job_submission_validation(self):
        """Test job submission validation (no universe or symbols)."""
        request_data = {
            'universe_key': '',
            'symbols': '',
            'analysis_type': 'both',
            'timeframe': 'daily'
        }

        # Mock admin check and login
        def admin_required_mock(f):
            return f

        with patch('src.utils.auth_decorators.admin_required', admin_required_mock):
            with patch('flask_login.utils._get_user') as mock_get_user:
                user = Mock()
                user.username = 'test-admin'
                user.is_authenticated = True
                user.is_admin = True
                mock_get_user.return_value = user

                response = self.client.post(
                    '/admin/process-analysis/trigger',
                    data=json.dumps(request_data),
                    content_type='application/json'
                )

                self.assertEqual(response.status_code, 400)  # Bad Request

                data = json.loads(response.data)
                self.assertFalse(data['success'])
                self.assertIn('error', data)

    def test_job_status_polling(self):
        """Test job status polling endpoint."""
        from src.api.rest.admin_process_analysis import active_jobs

        # Create a mock job
        job_id = 'analysis_test_123'
        active_jobs[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': 50,
            'current_symbol': 'AAPL',
            'symbols_completed': 5,
            'symbols_total': 10,
            'patterns_detected': 3,
            'indicators_calculated': 40,
            'failed_symbols': [],
            'log_messages': ['Test log message'],
            'completed_at': None
        }

        # Mock login
        with patch('flask_login.utils._get_user') as mock_get_user:
            user = Mock()
            user.is_authenticated = True
            mock_get_user.return_value = user

            response = self.client.get(f'/admin/process-analysis/job-status/{job_id}')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertEqual(data['id'], job_id)
            self.assertEqual(data['status'], 'running')
            self.assertEqual(data['progress'], 50)
            self.assertEqual(data['current_symbol'], 'AAPL')

        # Cleanup
        del active_jobs[job_id]

    def test_job_status_not_found(self):
        """Test job status polling for non-existent job."""
        # Mock login
        with patch('flask_login.utils._get_user') as mock_get_user:
            user = Mock()
            user.is_authenticated = True
            mock_get_user.return_value = user

            response = self.client.get('/admin/process-analysis/job-status/nonexistent_job_id')
            self.assertEqual(response.status_code, 404)

            data = json.loads(response.data)
            self.assertIn('error', data)

    def test_job_cancellation(self):
        """Test job cancellation."""
        from src.api.rest.admin_process_analysis import active_jobs, job_history

        # Create a mock running job
        job_id = 'analysis_test_cancel_123'
        active_jobs[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': 30,
            'current_symbol': 'AAPL',
            'symbols_completed': 3,
            'symbols_total': 10,
            'patterns_detected': 1,
            'indicators_calculated': 24,
            'failed_symbols': [],
            'log_messages': ['Starting analysis'],
            'completed_at': None
        }

        # Mock admin check and login
        def admin_required_mock(f):
            return f

        with patch('src.utils.auth_decorators.admin_required', admin_required_mock):
            with patch('flask_login.utils._get_user') as mock_get_user:
                user = Mock()
                user.username = 'test-admin'
                user.is_authenticated = True
                user.is_admin = True
                mock_get_user.return_value = user

                response = self.client.post(f'/admin/process-analysis/job/{job_id}/cancel')
                self.assertEqual(response.status_code, 200)

                data = json.loads(response.data)
                self.assertTrue(data['success'])

                # Verify job was moved to history
                self.assertNotIn(job_id, active_jobs)
                self.assertTrue(any(j['id'] == job_id for j in job_history))

        # Cleanup
        job_history.clear()

    def test_invalid_timeframe(self):
        """Test job submission with invalid timeframe."""
        request_data = {
            'universe_key': '',
            'symbols': 'AAPL',
            'analysis_type': 'both',
            'timeframe': 'invalid_timeframe'
        }

        # Mock admin check and login
        def admin_required_mock(f):
            return f

        with patch('src.utils.auth_decorators.admin_required', admin_required_mock):
            with patch('flask_login.utils._get_user') as mock_get_user:
                user = Mock()
                user.username = 'test-admin'
                user.is_authenticated = True
                user.is_admin = True
                mock_get_user.return_value = user

                response = self.client.post(
                    '/admin/process-analysis/trigger',
                    data=json.dumps(request_data),
                    content_type='application/json'
                )

                self.assertEqual(response.status_code, 400)

                data = json.loads(response.data)
                self.assertFalse(data['success'])
                self.assertIn('Invalid timeframe', data['error'])

    def test_invalid_analysis_type(self):
        """Test job submission with invalid analysis type."""
        request_data = {
            'universe_key': '',
            'symbols': 'AAPL',
            'analysis_type': 'invalid_type',
            'timeframe': 'daily'
        }

        # Mock admin check and login
        def admin_required_mock(f):
            return f

        with patch('src.utils.auth_decorators.admin_required', admin_required_mock):
            with patch('flask_login.utils._get_user') as mock_get_user:
                user = Mock()
                user.username = 'test-admin'
                user.is_authenticated = True
                user.is_admin = True
                mock_get_user.return_value = user

                response = self.client.post(
                    '/admin/process-analysis/trigger',
                    data=json.dumps(request_data),
                    content_type='application/json'
                )

                self.assertEqual(response.status_code, 400)

                data = json.loads(response.data)
                self.assertFalse(data['success'])
                self.assertIn('Invalid analysis_type', data['error'])


if __name__ == '__main__':
    unittest.main()
