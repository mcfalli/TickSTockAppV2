# ==========================================================================
# TICKSTOCK SPRINT 12 API ENDPOINT TESTS
# ==========================================================================
# PURPOSE: Test backend API endpoints for dashboard functionality
# ENDPOINTS: /api/watchlist, /api/watchlist/add, /api/watchlist/remove, 
#           /api/chart-data/<symbol>, /api/symbols/search
# PERFORMANCE TARGETS: <50ms API response times
# ==========================================================================

import pytest
import json
import time
from unittest.mock import patch, Mock, MagicMock
from flask import Flask
from datetime import datetime, timedelta

# ==========================================================================
# API ENDPOINT TESTS - SYMBOLS SEARCH
# ==========================================================================

@pytest.mark.api
@pytest.mark.unit
class TestSymbolsSearchAPI:
    """Test /api/symbols/search endpoint functionality."""
    
    def test_symbols_search_success(self, client, mock_symbols_data):
        """Test successful symbol search returns all symbols."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
            
            response = client.get('/api/symbols/search')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'symbols' in data
            assert len(data['symbols']) == len(mock_symbols_data)
            assert data['symbols'][0]['symbol'] == 'AAPL'
    
    def test_symbols_search_with_query(self, client, mock_symbols_data):
        """Test symbol search with query parameter filters correctly."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
            
            response = client.get('/api/symbols/search?query=AAPL')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            # Should filter symbols containing 'AAPL'
            mock_db.get_symbols_for_dropdown.assert_called_once()
    
    @pytest.mark.performance
    def test_symbols_search_performance(self, client, mock_symbols_data, performance_timer):
        """Test symbol search API meets <50ms response time requirement."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
            
            performance_timer.start()
            response = client.get('/api/symbols/search')
            performance_timer.stop()
            
            assert response.status_code == 200
            assert performance_timer.elapsed < 50  # Less than 50ms
    
    def test_symbols_search_database_error(self, client):
        """Test symbol search handles database errors gracefully."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbols_for_dropdown.side_effect = Exception("Database connection failed")
            
            response = client.get('/api/symbols/search')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data
    
    def test_symbols_search_authentication_required(self, client_no_auth):
        """Test symbol search requires user authentication."""
        response = client_no_auth.get('/api/symbols/search')
        
        # Should redirect to login or return 401
        assert response.status_code in [302, 401]

# ==========================================================================
# API ENDPOINT TESTS - WATCHLIST OPERATIONS
# ==========================================================================

@pytest.mark.api
@pytest.mark.unit 
class TestWatchlistAPI:
    """Test watchlist CRUD operations."""
    
    def test_get_watchlist_success(self, client, mock_watchlist_data):
        """Test successful watchlist retrieval."""
        with patch('src.api.rest.api.user_settings_service') as mock_service:
            mock_service.get_user_settings.return_value = {
                'watchlist': ['AAPL', 'GOOGL', 'MSFT']
            }
            with patch('src.api.rest.api.tickstock_db') as mock_db:
                mock_db.get_symbol_details.side_effect = lambda symbol: next(
                    (s for s in mock_watchlist_data if s['symbol'] == symbol), None
                )
                
                response = client.get('/api/watchlist')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'symbols' in data
                assert len(data['symbols']) == 3
    
    def test_get_empty_watchlist(self, client):
        """Test empty watchlist returns appropriate response."""
        with patch('src.api.rest.api.user_settings_service') as mock_service:
            mock_service.get_user_settings.return_value = {'watchlist': []}
            
            response = client.get('/api/watchlist')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['symbols'] == []
    
    @pytest.mark.performance
    def test_get_watchlist_performance(self, client, mock_watchlist_data, performance_timer):
        """Test watchlist retrieval meets <50ms performance target."""
        with patch('src.api.rest.api.user_settings_service') as mock_service:
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL']}
            with patch('src.api.rest.api.tickstock_db') as mock_db:
                mock_db.get_symbol_details.return_value = mock_watchlist_data[0]
                
                performance_timer.start()
                response = client.get('/api/watchlist')
                performance_timer.stop()
                
                assert response.status_code == 200
                assert performance_timer.elapsed < 50  # Less than 50ms
    
    def test_add_to_watchlist_success(self, client):
        """Test successful addition to watchlist."""
        with patch('src.api.rest.api.user_settings_service') as mock_service, \
             patch('src.api.rest.api.tickstock_db') as mock_db:
            
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL']}
            mock_db.get_symbol_details.return_value = {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'}
            
            response = client.post('/api/watchlist/add', 
                                 json={'symbol': 'GOOGL'},
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'GOOGL added to watchlist' in data.get('message', '')
            
            # Verify settings were updated
            mock_service.update_user_settings.assert_called_once()
    
    def test_add_duplicate_symbol(self, client):
        """Test adding duplicate symbol to watchlist is handled properly."""
        with patch('src.api.rest.api.user_settings_service') as mock_service, \
             patch('src.api.rest.api.tickstock_db') as mock_db:
            
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL']}
            mock_db.get_symbol_details.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.'}
            
            response = client.post('/api/watchlist/add',
                                 json={'symbol': 'AAPL'}, 
                                 content_type='application/json')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'already in watchlist' in data.get('error', '').lower()
    
    def test_add_invalid_symbol(self, client):
        """Test adding invalid symbol returns appropriate error."""
        with patch('src.api.rest.api.user_settings_service') as mock_service, \
             patch('src.api.rest.api.tickstock_db') as mock_db:
            
            mock_service.get_user_settings.return_value = {'watchlist': []}
            mock_db.get_symbol_details.return_value = None  # Symbol not found
            
            response = client.post('/api/watchlist/add',
                                 json={'symbol': 'INVALID'},
                                 content_type='application/json')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'symbol not found' in data.get('error', '').lower()
    
    def test_add_missing_symbol_parameter(self, client):
        """Test add to watchlist without symbol parameter."""
        response = client.post('/api/watchlist/add',
                             json={},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'symbol is required' in data.get('error', '').lower()
    
    def test_remove_from_watchlist_success(self, client):
        """Test successful removal from watchlist."""
        with patch('src.api.rest.api.user_settings_service') as mock_service:
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL', 'GOOGL']}
            
            response = client.post('/api/watchlist/remove',
                                 json={'symbol': 'GOOGL'},
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'GOOGL removed from watchlist' in data.get('message', '')
            
            # Verify settings were updated
            mock_service.update_user_settings.assert_called_once()
    
    def test_remove_symbol_not_in_watchlist(self, client):
        """Test removing symbol not in watchlist."""
        with patch('src.api.rest.api.user_settings_service') as mock_service:
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL']}
            
            response = client.post('/api/watchlist/remove',
                                 json={'symbol': 'GOOGL'},
                                 content_type='application/json')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'not found in watchlist' in data.get('error', '').lower()

# ==========================================================================
# API ENDPOINT TESTS - CHART DATA
# ==========================================================================

@pytest.mark.api
@pytest.mark.unit
class TestChartDataAPI:
    """Test /api/chart-data/<symbol> endpoint functionality."""
    
    def test_get_chart_data_success(self, client, mock_chart_data):
        """Test successful chart data retrieval."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.'}
            mock_db.get_ohlcv_data.return_value = mock_chart_data
            
            response = client.get('/api/chart-data/AAPL')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'chart_data' in data
            assert len(data['chart_data']) == len(mock_chart_data)
    
    def test_get_chart_data_with_timeframe(self, client, mock_chart_data):
        """Test chart data retrieval with timeframe parameter."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.'}
            mock_db.get_ohlcv_data.return_value = mock_chart_data
            
            response = client.get('/api/chart-data/AAPL?timeframe=1w')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify timeframe was passed to database call
            mock_db.get_ohlcv_data.assert_called_with('AAPL', timeframe='1w')
    
    def test_get_chart_data_invalid_symbol(self, client):
        """Test chart data for invalid symbol."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = None
            
            response = client.get('/api/chart-data/INVALID')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'symbol not found' in data.get('error', '').lower()
    
    def test_get_chart_data_no_data(self, client):
        """Test chart data when no historical data available."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.'}
            mock_db.get_ohlcv_data.return_value = []
            
            response = client.get('/api/chart-data/AAPL')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['chart_data'] == []
    
    @pytest.mark.performance
    def test_get_chart_data_performance(self, client, mock_chart_data, performance_timer):
        """Test chart data API meets <50ms performance target."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.'}
            mock_db.get_ohlcv_data.return_value = mock_chart_data
            
            performance_timer.start()
            response = client.get('/api/chart-data/AAPL')
            performance_timer.stop()
            
            assert response.status_code == 200
            assert performance_timer.elapsed < 50  # Less than 50ms
    
    def test_get_chart_data_database_error(self, client):
        """Test chart data handles database errors gracefully."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.'}
            mock_db.get_ohlcv_data.side_effect = Exception("Database query failed")
            
            response = client.get('/api/chart-data/AAPL')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

# ==========================================================================
# INTEGRATION TESTS - API WORKFLOW
# ==========================================================================

@pytest.mark.integration
@pytest.mark.api
class TestAPIWorkflow:
    """Test complete API workflows for dashboard functionality."""
    
    def test_complete_watchlist_workflow(self, client, mock_symbols_data, mock_watchlist_data):
        """Test complete workflow: search symbols → add to watchlist → get watchlist → remove."""
        with patch('src.api.rest.api.tickstock_db') as mock_db, \
             patch('src.api.rest.api.user_settings_service') as mock_service:
            
            # Setup mocks
            mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
            mock_service.get_user_settings.return_value = {'watchlist': []}
            mock_db.get_symbol_details.return_value = mock_symbols_data[0]  # AAPL
            
            # Step 1: Search for symbols
            response = client.get('/api/symbols/search')
            assert response.status_code == 200
            
            # Step 2: Add symbol to watchlist
            response = client.post('/api/watchlist/add',
                                 json={'symbol': 'AAPL'},
                                 content_type='application/json')
            assert response.status_code == 200
            
            # Update mock to reflect addition
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL']}
            mock_db.get_symbol_details.return_value = mock_watchlist_data[0]
            
            # Step 3: Get updated watchlist
            response = client.get('/api/watchlist')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data['symbols']) == 1
            assert data['symbols'][0]['symbol'] == 'AAPL'
            
            # Step 4: Remove symbol from watchlist
            response = client.post('/api/watchlist/remove',
                                 json={'symbol': 'AAPL'},
                                 content_type='application/json')
            assert response.status_code == 200
    
    def test_chart_data_workflow(self, client, mock_symbols_data, mock_chart_data):
        """Test workflow: search symbols → get chart data."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
            mock_db.get_symbol_details.return_value = mock_symbols_data[0]  # AAPL
            mock_db.get_ohlcv_data.return_value = mock_chart_data
            
            # Step 1: Search for symbols  
            response = client.get('/api/symbols/search')
            assert response.status_code == 200
            
            # Step 2: Get chart data for selected symbol
            response = client.get('/api/chart-data/AAPL')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['chart_data']) > 0
    
    @pytest.mark.performance
    def test_api_workflow_performance(self, client, mock_symbols_data, mock_chart_data, performance_timer):
        """Test complete API workflow meets performance targets."""
        with patch('src.api.rest.api.tickstock_db') as mock_db, \
             patch('src.api.rest.api.user_settings_service') as mock_service:
            
            # Setup mocks
            mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
            mock_service.get_user_settings.return_value = {'watchlist': []}
            mock_db.get_symbol_details.return_value = mock_symbols_data[0]
            mock_db.get_ohlcv_data.return_value = mock_chart_data
            
            # Test multiple API calls in sequence - should all be <50ms each
            api_calls = [
                lambda: client.get('/api/symbols/search'),
                lambda: client.get('/api/watchlist'),
                lambda: client.get('/api/chart-data/AAPL')
            ]
            
            for api_call in api_calls:
                performance_timer.start()
                response = api_call()
                performance_timer.stop()
                
                assert response.status_code == 200
                assert performance_timer.elapsed < 50  # Each call <50ms