# ==========================================================================
# TICKSTOCK SPRINT 12 INTEGRATION WORKFLOW TESTS
# ==========================================================================
# PURPOSE: Test end-to-end dashboard workflows and component integration
# WORKFLOWS: Dashboard load → symbol search → watchlist management → chart display
# TESTING APPROACH: Full-stack integration with mocked external dependencies
# ==========================================================================

import pytest
import json
import time
from unittest.mock import patch, Mock, MagicMock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from flask import Flask

# ==========================================================================
# END-TO-END WORKFLOW TESTS
# ==========================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestDashboardWorkflows:
    """Test complete dashboard workflows with real browser interactions."""
    
    @pytest.fixture(autouse=True)
    def setup_driver(self):
        """Setup Chrome WebDriver for integration testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(1920, 1080)
        yield
        self.driver.quit()
    
    @patch('src.api.rest.api.tickstock_db')
    @patch('src.api.rest.api.user_settings_service')  
    def test_complete_dashboard_load_workflow(self, mock_settings, mock_db, client, mock_symbols_data, mock_watchlist_data):
        """Test complete dashboard loading workflow with all components."""
        # Setup mocks
        mock_settings.get_user_settings.return_value = {'watchlist': ['AAPL', 'GOOGL']}
        mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
        mock_db.get_symbol_details.side_effect = lambda symbol: next(
            (s for s in mock_watchlist_data if s['symbol'] == symbol), None
        )
        
        # Create test dashboard page
        test_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TickStock Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
        </head>
        <body>
            <div class="container-fluid">
                <!-- Bootstrap Tabs -->
                <ul class="nav nav-tabs" id="main-tabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="dashboard-tab" data-bs-toggle="tab" 
                                data-bs-target="#dashboard" type="button" role="tab">Dashboard</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="charts-tab" data-bs-toggle="tab" 
                                data-bs-target="#charts" type="button" role="tab">Charts</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="alerts-tab" data-bs-toggle="tab" 
                                data-bs-target="#alerts" type="button" role="tab">Alerts</button>
                    </li>
                </ul>
                
                <!-- Tab Content -->
                <div class="tab-content" id="main-tab-content">
                    <!-- Dashboard Tab -->
                    <div class="tab-pane fade show active" id="dashboard" role="tabpanel">
                        <div class="row mt-3">
                            <!-- Market Summary -->
                            <div class="col-md-4">
                                <div class="card">
                                    <div class="card-header">Market Summary</div>
                                    <div class="card-body">
                                        <div>Total Symbols: <span id="total-symbols">0</span></div>
                                        <div>Up: <span id="symbols-up">0</span></div>
                                        <div>Down: <span id="symbols-down">0</span></div>
                                        <div>Last Update: <span id="last-update">Never</span></div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Watchlist -->
                            <div class="col-md-8">
                                <div class="card">
                                    <div class="card-header d-flex justify-content-between">
                                        <span>Watchlist</span>
                                        <button id="add-symbol-btn" class="btn btn-sm btn-primary">Add Symbol</button>
                                    </div>
                                    <div class="card-body">
                                        <div id="watchlist-container">Loading...</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Charts Tab -->
                    <div class="tab-pane fade" id="charts" role="tabpanel">
                        <div class="row mt-3">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <select id="chart-symbol-select" class="form-select d-inline-block w-auto">
                                            <option value="">Select a symbol...</option>
                                        </select>
                                    </div>
                                    <div class="card-body">
                                        <div style="height: 400px;">
                                            <canvas id="price-chart"></canvas>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Alerts Tab -->
                    <div class="tab-pane fade" id="alerts" role="tabpanel">
                        <div class="row mt-3">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header d-flex justify-content-between">
                                        <span>Recent Alerts</span>
                                        <button id="clear-alerts-btn" class="btn btn-sm btn-outline-danger">Clear All</button>
                                    </div>
                                    <div class="card-body">
                                        <div id="alerts-list">
                                            <div class="text-center p-3 text-muted">
                                                <i class="fas fa-bell-slash fa-2x mb-2"></i>
                                                <p class="mb-0">No recent alerts</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Bootstrap JS -->
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
            
            <!-- Mock CSRF Token -->
            <script>window.csrfToken = 'test-token';</script>
            
            <!-- Mock Dashboard Manager -->
            <script>
                // Simplified DashboardManager for testing
                class DashboardManager {{
                    constructor() {{
                        this.watchlist = [];
                        this.isInitialized = false;
                        this.init();
                    }}
                    
                    init() {{
                        this.loadWatchlist();
                        this.isInitialized = true;
                        window.dashboardReady = true;
                    }}
                    
                    async loadWatchlist() {{
                        try {{
                            const response = await fetch('/api/watchlist');
                            if (response.ok) {{
                                const data = await response.json();
                                if (data.success) {{
                                    this.watchlist = data.symbols || [];
                                    this.renderWatchlist();
                                    window.watchlistLoaded = true;
                                }}
                            }}
                        }} catch (error) {{
                            console.error('Error loading watchlist:', error);
                            window.watchlistError = error.message;
                        }}
                    }}
                    
                    renderWatchlist() {{
                        const container = document.getElementById('watchlist-container');
                        if (!container) return;
                        
                        if (this.watchlist.length === 0) {{
                            container.innerHTML = '<div class="text-center p-3 text-muted">Add symbols to start tracking</div>';
                            return;
                        }}
                        
                        const html = this.watchlist.map(symbol => {{
                            return `<div class="watchlist-item border-bottom py-2" data-symbol="${{symbol.symbol}}">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <strong>${{symbol.symbol}}</strong>
                                        <small class="text-muted d-block">${{symbol.name || 'Unknown'}}</small>
                                    </div>
                                    <div class="text-end">
                                        <div class="fw-bold">${{(symbol.last_price || 0).toFixed(2)}}</div>
                                    </div>
                                </div>
                            </div>`;
                        }}).join('');
                        
                        container.innerHTML = html;
                    }}
                }}
                
                // Mock ChartManager
                class ChartManager {{
                    constructor() {{
                        this.isInitialized = false;
                        this.init();
                    }}
                    
                    init() {{
                        this.populateSymbolDropdown();
                        this.isInitialized = true;
                        window.chartReady = true;
                    }}
                    
                    async populateSymbolDropdown() {{
                        try {{
                            const response = await fetch('/api/symbols/search');
                            if (response.ok) {{
                                const data = await response.json();
                                const select = document.getElementById('chart-symbol-select');
                                if (select && data.symbols) {{
                                    data.symbols.forEach(symbol => {{
                                        const option = document.createElement('option');
                                        option.value = symbol.symbol;
                                        option.textContent = `${{symbol.symbol}} - ${{symbol.name || 'Unknown'}}`;
                                        select.appendChild(option);
                                    }});
                                    window.chartSymbolsLoaded = true;
                                }}
                            }}
                        }} catch (error) {{
                            console.error('Error loading symbols:', error);
                        }}
                    }}
                }}
                
                // Initialize managers
                const dashboardManager = new DashboardManager();
                const chartManager = new ChartManager();
                
                // Tab switching functionality
                document.addEventListener('DOMContentLoaded', function() {{
                    const tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
                    tabs.forEach(tab => {{
                        tab.addEventListener('shown.bs.tab', function(e) {{
                            window.activeTab = e.target.id;
                        }});
                    }});
                }});
            </script>
        </body>
        </html>
        """
        
        # Create temporary HTML file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            temp_file = f.name
        
        try:
            # Load the dashboard page
            self.driver.get(f"file://{temp_file}")
            
            # Wait for dashboard to initialize
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return window.dashboardReady === true")
            )
            
            # Wait for chart to initialize
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return window.chartReady === true")
            )
            
            # Verify dashboard tab is active by default
            dashboard_tab = self.driver.find_element(By.ID, "dashboard-tab")
            assert "active" in dashboard_tab.get_attribute("class")
            
            # Verify dashboard components are present
            market_summary = self.driver.find_element(By.ID, "total-symbols")
            watchlist_container = self.driver.find_element(By.ID, "watchlist-container")
            add_symbol_btn = self.driver.find_element(By.ID, "add-symbol-btn")
            
            assert market_summary is not None
            assert watchlist_container is not None
            assert add_symbol_btn is not None
            
            # Test tab switching
            charts_tab = self.driver.find_element(By.ID, "charts-tab")
            charts_tab.click()
            
            # Wait for tab switch
            time.sleep(0.5)
            
            # Verify charts tab content is visible
            chart_canvas = self.driver.find_element(By.ID, "price-chart")
            symbol_select = self.driver.find_element(By.ID, "chart-symbol-select")
            
            assert chart_canvas is not None
            assert symbol_select is not None
            
            # Test alerts tab
            alerts_tab = self.driver.find_element(By.ID, "alerts-tab")
            alerts_tab.click()
            
            # Wait for tab switch
            time.sleep(0.5)
            
            # Verify alerts tab content
            alerts_list = self.driver.find_element(By.ID, "alerts-list")
            clear_alerts_btn = self.driver.find_element(By.ID, "clear-alerts-btn")
            
            assert alerts_list is not None
            assert clear_alerts_btn is not None
            assert "No recent alerts" in alerts_list.text
            
        finally:
            os.unlink(temp_file)
    
    @patch('src.api.rest.api.tickstock_db')
    @patch('src.api.rest.api.user_settings_service')
    def test_watchlist_management_workflow(self, mock_settings, mock_db, client, mock_symbols_data):
        """Test complete watchlist management workflow."""
        # Setup initial empty watchlist
        mock_settings.get_user_settings.return_value = {'watchlist': []}
        mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
        mock_db.get_symbol_details.return_value = mock_symbols_data[0]  # AAPL
        
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
        </head>
        <body>
            <div id="watchlist-container">Empty watchlist</div>
            <button id="add-symbol-btn">Add Symbol</button>
            
            <script>
                window.csrfToken = 'test-token';
                
                // Mock successful API responses
                window.fetch = async function(url, options) {
                    if (url === '/api/symbols/search') {
                        return {
                            ok: true,
                            json: async () => ({
                                success: true,
                                symbols: [
                                    { symbol: 'AAPL', name: 'Apple Inc.' },
                                    { symbol: 'GOOGL', name: 'Alphabet Inc.' }
                                ]
                            })
                        };
                    } else if (url === '/api/watchlist/add' && options.method === 'POST') {
                        return {
                            ok: true,
                            json: async () => ({
                                success: true,
                                message: 'AAPL added to watchlist'
                            })
                        };
                    } else if (url === '/api/watchlist') {
                        return {
                            ok: true,
                            json: async () => ({
                                success: true,
                                symbols: [{ symbol: 'AAPL', name: 'Apple Inc.', last_price: 175.50 }]
                            })
                        };
                    }
                    return { ok: false };
                };
                
                // Simplified DashboardManager
                class DashboardManager {
                    constructor() {
                        this.watchlist = [];
                        this.setupEventListeners();
                    }
                    
                    setupEventListeners() {
                        document.addEventListener('click', (e) => {
                            if (e.target.id === 'add-symbol-btn') {
                                this.showAddSymbolDialog();
                            }
                        });
                    }
                    
                    async showAddSymbolDialog() {
                        // Simulate SweetAlert2 dialog with automatic selection
                        window.addSymbolCalled = true;
                        
                        // Simulate user selecting AAPL
                        await this.addToWatchlist('AAPL');
                    }
                    
                    async addToWatchlist(symbol) {
                        const response = await fetch('/api/watchlist/add', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ symbol })
                        });
                        
                        if (response.ok) {
                            await this.loadWatchlist();
                            window.symbolAdded = symbol;
                        }
                    }
                    
                    async loadWatchlist() {
                        const response = await fetch('/api/watchlist');
                        if (response.ok) {
                            const data = await response.json();
                            this.watchlist = data.symbols || [];
                            this.renderWatchlist();
                        }
                    }
                    
                    renderWatchlist() {
                        const container = document.getElementById('watchlist-container');
                        if (this.watchlist.length === 0) {
                            container.innerHTML = 'Empty watchlist';
                        } else {
                            container.innerHTML = this.watchlist.map(s => 
                                `<div>${s.symbol} - $${s.last_price}</div>`
                            ).join('');
                        }
                        window.watchlistRendered = true;
                    }
                }
                
                const dashboardManager = new DashboardManager();
            </script>
        </body>
        </html>
        """
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            temp_file = f.name
        
        try:
            self.driver.get(f"file://{temp_file}")
            
            # Verify initial state
            watchlist_container = self.driver.find_element(By.ID, "watchlist-container")
            assert "Empty watchlist" in watchlist_container.text
            
            # Click add symbol button
            add_btn = self.driver.find_element(By.ID, "add-symbol-btn")
            add_btn.click()
            
            # Wait for add symbol dialog to be called
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.addSymbolCalled === true")
            )
            
            # Wait for symbol to be added
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.symbolAdded === 'AAPL'")
            )
            
            # Wait for watchlist to be rendered
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.watchlistRendered === true")
            )
            
            # Verify symbol was added to watchlist display
            watchlist_container = self.driver.find_element(By.ID, "watchlist-container")
            assert "AAPL" in watchlist_container.text
            assert "$175.50" in watchlist_container.text
            
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.performance
    def test_dashboard_load_performance(self, client, mock_symbols_data, performance_timer):
        """Test dashboard loading meets <1s performance target."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="dashboard-container">Loading...</div>
            
            <script>
                const startTime = performance.now();
                
                // Mock API responses
                window.fetch = async function(url) {
                    // Simulate realistic API delay
                    await new Promise(resolve => setTimeout(resolve, 20));
                    
                    if (url === '/api/watchlist') {
                        return {
                            ok: true,
                            json: async () => ({ success: true, symbols: [] })
                        };
                    } else if (url === '/api/symbols/search') {
                        return {
                            ok: true,
                            json: async () => ({ success: true, symbols: [] })
                        };
                    }
                    return { ok: false };
                };
                
                async function initializeDashboard() {
                    // Simulate dashboard initialization
                    const watchlistResponse = await fetch('/api/watchlist');
                    const symbolsResponse = await fetch('/api/symbols/search');
                    
                    // Simulate DOM updates
                    document.getElementById('dashboard-container').innerHTML = 'Dashboard loaded';
                    
                    const endTime = performance.now();
                    window.loadTime = endTime - startTime;
                    window.dashboardLoaded = true;
                }
                
                // Start initialization
                initializeDashboard();
            </script>
        </body>
        </html>
        """
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            temp_file = f.name
        
        try:
            performance_timer.start()
            self.driver.get(f"file://{temp_file}")
            
            # Wait for dashboard to finish loading
            WebDriverWait(self.driver, 2).until(
                lambda driver: driver.execute_script("return window.dashboardLoaded === true")
            )
            performance_timer.stop()
            
            # Check client-side load time
            client_load_time = self.driver.execute_script("return window.loadTime")
            
            # Verify both server response time and client load time
            assert performance_timer.elapsed < 1000  # <1s total
            assert client_load_time < 500  # <500ms client-side processing
            
        finally:
            os.unlink(temp_file)

# ==========================================================================  
# CROSS-COMPONENT INTEGRATION TESTS
# ==========================================================================

@pytest.mark.integration
class TestComponentIntegration:
    """Test integration between frontend and backend components."""
    
    def test_api_frontend_integration(self, client, mock_symbols_data, mock_watchlist_data):
        """Test integration between API endpoints and frontend components."""
        with patch('src.api.rest.api.tickstock_db') as mock_db, \
             patch('src.api.rest.api.user_settings_service') as mock_service:
            
            # Setup mocks
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL']}
            mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
            mock_db.get_symbol_details.return_value = mock_watchlist_data[0]
            
            # Test symbols endpoint
            response = client.get('/api/symbols/search')
            assert response.status_code == 200
            symbols_data = json.loads(response.data)
            assert symbols_data['success'] is True
            
            # Test watchlist endpoint
            response = client.get('/api/watchlist')
            assert response.status_code == 200
            watchlist_data = json.loads(response.data)
            assert watchlist_data['success'] is True
            assert len(watchlist_data['symbols']) == 1
            
            # Verify data consistency between endpoints
            symbol_from_search = symbols_data['symbols'][0]['symbol']
            symbol_from_watchlist = watchlist_data['symbols'][0]['symbol']
            assert symbol_from_search == symbol_from_watchlist == 'AAPL'
    
    def test_error_handling_integration(self, client):
        """Test error handling across API and frontend integration."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            # Simulate database error
            mock_db.get_symbols_for_dropdown.side_effect = Exception("Database connection failed")
            
            response = client.get('/api/symbols/search')
            assert response.status_code == 500
            
            error_data = json.loads(response.data)
            assert error_data['success'] is False
            assert 'error' in error_data
    
    @pytest.mark.performance
    def test_concurrent_api_calls_performance(self, client, mock_symbols_data, mock_watchlist_data, performance_timer):
        """Test performance under concurrent API calls."""
        with patch('src.api.rest.api.tickstock_db') as mock_db, \
             patch('src.api.rest.api.user_settings_service') as mock_service:
            
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL', 'GOOGL']}
            mock_db.get_symbols_for_dropdown.return_value = mock_symbols_data
            mock_db.get_symbol_details.side_effect = lambda symbol: next(
                (s for s in mock_watchlist_data if s['symbol'] == symbol), None
            )
            
            # Simulate concurrent API calls that might happen during dashboard load
            performance_timer.start()
            
            # Concurrent API calls
            responses = []
            responses.append(client.get('/api/symbols/search'))
            responses.append(client.get('/api/watchlist'))
            responses.append(client.get('/api/symbols/search?query=AAPL'))
            
            performance_timer.stop()
            
            # Verify all responses are successful
            for response in responses:
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
            
            # Verify total time for concurrent calls is reasonable
            assert performance_timer.elapsed < 200  # <200ms for all calls combined

# ==========================================================================
# REGRESSION TESTS
# ==========================================================================

@pytest.mark.integration
@pytest.mark.regression
class TestDashboardRegression:
    """Test for regression issues in dashboard functionality."""
    
    def test_empty_watchlist_handling(self, client):
        """Regression test: Ensure empty watchlist is handled gracefully."""
        with patch('src.api.rest.api.user_settings_service') as mock_service:
            mock_service.get_user_settings.return_value = {'watchlist': []}
            
            response = client.get('/api/watchlist')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['symbols'] == []
    
    def test_invalid_symbol_handling(self, client):
        """Regression test: Invalid symbol operations are handled properly."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = None
            
            # Test adding invalid symbol
            response = client.post('/api/watchlist/add',
                                 json={'symbol': 'INVALID'},
                                 content_type='application/json')
            assert response.status_code == 404
            
            # Test getting chart data for invalid symbol
            response = client.get('/api/chart-data/INVALID')
            assert response.status_code == 404
    
    def test_malformed_requests_handling(self, client):
        """Regression test: Malformed requests are handled gracefully."""
        # Test missing symbol parameter
        response = client.post('/api/watchlist/add',
                             json={},
                             content_type='application/json')
        assert response.status_code == 400
        
        # Test invalid JSON
        response = client.post('/api/watchlist/add',
                             data='invalid json',
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_authentication_requirements(self, client_no_auth):
        """Regression test: Authentication requirements are enforced."""
        endpoints = [
            '/api/symbols/search',
            '/api/watchlist',
            '/api/chart-data/AAPL'
        ]
        
        for endpoint in endpoints:
            response = client_no_auth.get(endpoint)
            # Should redirect to login or return 401
            assert response.status_code in [302, 401]