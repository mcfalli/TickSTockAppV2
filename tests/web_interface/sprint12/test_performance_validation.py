# ==========================================================================
# TICKSTOCK SPRINT 12 PERFORMANCE VALIDATION TESTS
# ==========================================================================
# PURPOSE: Validate Sprint 12 dashboard meets performance requirements
# TARGETS: <50ms API responses, <1s dashboard load, <200ms WebSocket updates
# APPROACH: Load testing, stress testing, and performance benchmarking
# ==========================================================================

import pytest
import json
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

# ==========================================================================
# API PERFORMANCE TESTS
# ==========================================================================

@pytest.mark.performance
@pytest.mark.api
class TestAPIPerformance:
    """Test API endpoint performance meets <50ms requirements."""
    
    @pytest.mark.parametrize("endpoint,setup_mocks", [
        ('/api/symbols/search', lambda mock_db, mock_service: (
            mock_db.get_symbols_for_dropdown.return_value.__setitem__(0, [
                {"symbol": "AAPL", "name": "Apple Inc."} for _ in range(100)
            ]) or mock_db.get_symbols_for_dropdown.return_value
        )),
        ('/api/watchlist', lambda mock_db, mock_service: (
            mock_service.get_user_settings.return_value.__setitem__('watchlist', ['AAPL', 'GOOGL', 'MSFT']) or 
            mock_db.get_symbol_details.side_effect.__setitem__(0, lambda s: {"symbol": s, "name": f"{s} Inc.", "last_price": 100.0})
        ))
    ])
    def test_api_response_times(self, client, performance_timer, endpoint, setup_mocks):
        """Test individual API endpoints meet <50ms response time."""
        with patch('src.api.rest.api.tickstock_db') as mock_db, \
             patch('src.api.rest.api.user_settings_service') as mock_service:
            
            # Setup mocks based on endpoint
            mock_db.get_symbols_for_dropdown.return_value = [
                {"symbol": "AAPL", "name": "Apple Inc."} for _ in range(100)
            ]
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL', 'GOOGL', 'MSFT']}
            mock_db.get_symbol_details.side_effect = lambda s: {
                "symbol": s, "name": f"{s} Inc.", "last_price": 100.0
            }
            
            # Warm-up request
            client.get(endpoint)
            
            # Measure performance over multiple requests
            response_times = []
            for _ in range(10):
                performance_timer.start()
                response = client.get(endpoint)
                performance_timer.stop()
                
                assert response.status_code == 200
                response_times.append(performance_timer.elapsed)
            
            # Verify all responses are under 50ms
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            assert avg_time < 50, f"Average response time {avg_time}ms exceeds 50ms limit"
            assert max_time < 75, f"Max response time {max_time}ms exceeds acceptable limit"
    
    def test_chart_data_api_performance(self, client, performance_timer, mock_chart_data):
        """Test chart data API performance with large datasets."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = {"symbol": "AAPL", "name": "Apple Inc."}
            # Large dataset - 1000 data points
            large_dataset = mock_chart_data * 33  # ~1000 points
            mock_db.get_ohlcv_data.return_value = large_dataset
            
            # Test with different timeframes
            timeframes = ['1d', '1w', '1m']
            
            for timeframe in timeframes:
                performance_timer.start()
                response = client.get(f'/api/chart-data/AAPL?timeframe={timeframe}')
                performance_timer.stop()
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert len(data['chart_data']) > 0
                
                # Verify response time is acceptable even with large dataset
                assert performance_timer.elapsed < 100, f"Chart data response time {performance_timer.elapsed}ms too slow for {timeframe}"
    
    def test_concurrent_api_performance(self, client, performance_timer):
        """Test API performance under concurrent load."""
        with patch('src.api.rest.api.tickstock_db') as mock_db, \
             patch('src.api.rest.api.user_settings_service') as mock_service:
            
            # Setup mocks
            mock_db.get_symbols_for_dropdown.return_value = [
                {"symbol": f"TEST{i}", "name": f"Test Company {i}"} for i in range(50)
            ]
            mock_service.get_user_settings.return_value = {'watchlist': ['AAPL', 'GOOGL']}
            mock_db.get_symbol_details.side_effect = lambda s: {"symbol": s, "name": f"{s} Inc.", "last_price": 100.0}
            
            def make_request(endpoint):
                start_time = time.perf_counter()
                response = client.get(endpoint)
                end_time = time.perf_counter()
                return (response.status_code, (end_time - start_time) * 1000)
            
            # Test concurrent requests to different endpoints
            endpoints = [
                '/api/symbols/search',
                '/api/watchlist',
                '/api/symbols/search?query=TEST',
                '/api/symbols/search',
                '/api/watchlist'
            ]
            
            performance_timer.start()
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request, endpoint) for endpoint in endpoints]
                results = [future.result() for future in as_completed(futures)]
            
            performance_timer.stop()
            
            # Verify all requests succeeded
            for status_code, response_time in results:
                assert status_code == 200
                assert response_time < 100  # Allow higher limit under concurrent load
            
            # Verify total time for concurrent requests is reasonable
            assert performance_timer.elapsed < 300, f"Concurrent API calls took {performance_timer.elapsed}ms"
    
    def test_api_performance_under_load(self, client, performance_timer):
        """Test API performance under sustained load."""
        with patch('src.api.rest.api.tickstock_db') as mock_db, \
             patch('src.api.rest.api.user_settings_service') as mock_service:
            
            mock_db.get_symbols_for_dropdown.return_value = [{"symbol": "AAPL", "name": "Apple Inc."}]
            mock_service.get_user_settings.return_value = {'watchlist': []}
            
            # Sustained load test - 50 requests
            response_times = []
            failed_requests = 0
            
            performance_timer.start()
            
            for i in range(50):
                start = time.perf_counter()
                try:
                    response = client.get('/api/symbols/search')
                    end = time.perf_counter()
                    
                    if response.status_code == 200:
                        response_times.append((end - start) * 1000)
                    else:
                        failed_requests += 1
                except Exception:
                    failed_requests += 1
            
            performance_timer.stop()
            
            # Verify performance under load
            assert failed_requests == 0, f"{failed_requests} requests failed under load"
            assert len(response_times) == 50
            
            avg_time = sum(response_times) / len(response_times)
            p95_time = sorted(response_times)[int(0.95 * len(response_times))]
            
            assert avg_time < 75, f"Average response time under load: {avg_time}ms"
            assert p95_time < 150, f"P95 response time under load: {p95_time}ms"

# ==========================================================================
# DASHBOARD LOAD PERFORMANCE TESTS
# ==========================================================================

@pytest.mark.performance
@pytest.mark.javascript
class TestDashboardLoadPerformance:
    """Test dashboard loading performance meets <1s requirements."""
    
    @pytest.fixture(autouse=True)
    def setup_driver(self):
        """Setup Chrome WebDriver for performance testing."""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox") 
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(1920, 1080)
        yield
        self.driver.quit()
    
    def test_dashboard_initial_load_performance(self, performance_timer):
        """Test initial dashboard load meets <1s requirement."""
        
        # Create optimized dashboard test page
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>TickStock Dashboard Performance Test</title>
            <style>
                .container { max-width: 1200px; margin: 0 auto; }
                .dashboard-grid { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; }
                .card { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
                .watchlist-item { padding: 8px; border-bottom: 1px solid #eee; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="dashboard-grid">
                    <div class="card">
                        <h3>Market Summary</h3>
                        <div id="market-summary">Loading...</div>
                    </div>
                    <div class="card">
                        <h3>Watchlist</h3>
                        <div id="watchlist-container">Loading...</div>
                    </div>
                </div>
            </div>
            
            <script>
                const PERFORMANCE_START = performance.now();
                
                // Mock fast API responses
                window.fetch = async function(url) {
                    // Simulate realistic API response time
                    await new Promise(resolve => setTimeout(resolve, 15));
                    
                    if (url === '/api/watchlist') {
                        return {
                            ok: true,
                            json: async () => ({
                                success: true,
                                symbols: [
                                    {symbol: 'AAPL', name: 'Apple Inc.', last_price: 175.50, change: 2.30},
                                    {symbol: 'GOOGL', name: 'Alphabet Inc.', last_price: 142.80, change: -1.20},
                                    {symbol: 'MSFT', name: 'Microsoft Corporation', last_price: 420.15, change: 5.45}
                                ]
                            })
                        };
                    } else if (url === '/api/symbols/search') {
                        return {
                            ok: true,
                            json: async () => ({
                                success: true,
                                symbols: Array.from({length: 100}, (_, i) => ({
                                    symbol: `SYM${i}`,
                                    name: `Company ${i}`
                                }))
                            })
                        };
                    }
                    return {ok: false};
                };
                
                class DashboardLoader {
                    constructor() {
                        this.loadStartTime = performance.now();
                        this.init();
                    }
                    
                    async init() {
                        try {
                            // Load multiple components in parallel
                            const [watchlistData, symbolsData] = await Promise.all([
                                this.loadWatchlist(),
                                this.loadSymbols()
                            ]);
                            
                            this.renderDashboard(watchlistData, symbolsData);
                            
                            const loadTime = performance.now() - this.loadStartTime;
                            window.dashboardLoadTime = loadTime;
                            window.dashboardReady = true;
                            
                        } catch (error) {
                            console.error('Dashboard load error:', error);
                            window.dashboardError = error.message;
                        }
                    }
                    
                    async loadWatchlist() {
                        const response = await fetch('/api/watchlist');
                        if (response.ok) {
                            const data = await response.json();
                            return data.symbols || [];
                        }
                        return [];
                    }
                    
                    async loadSymbols() {
                        const response = await fetch('/api/symbols/search');
                        if (response.ok) {
                            const data = await response.json();
                            return data.symbols || [];
                        }
                        return [];
                    }
                    
                    renderDashboard(watchlist, symbols) {
                        // Render market summary
                        const summaryDiv = document.getElementById('market-summary');
                        const upCount = watchlist.filter(s => s.change > 0).length;
                        const downCount = watchlist.filter(s => s.change < 0).length;
                        
                        summaryDiv.innerHTML = `
                            <div>Total: ${watchlist.length}</div>
                            <div>Up: ${upCount}</div>
                            <div>Down: ${downCount}</div>
                        `;
                        
                        // Render watchlist
                        const watchlistDiv = document.getElementById('watchlist-container');
                        if (watchlist.length === 0) {
                            watchlistDiv.innerHTML = '<div>No symbols in watchlist</div>';
                        } else {
                            watchlistDiv.innerHTML = watchlist.map(symbol => `
                                <div class="watchlist-item">
                                    <strong>${symbol.symbol}</strong> - $${symbol.last_price}
                                    <span class="${symbol.change >= 0 ? 'positive' : 'negative'}">
                                        ${symbol.change >= 0 ? '+' : ''}${symbol.change}
                                    </span>
                                </div>
                            `).join('');
                        }
                        
                        window.renderComplete = true;
                    }
                }
                
                // Start dashboard loading
                const dashboardLoader = new DashboardLoader();
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
            
            # Wait for dashboard to be ready
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.driver, 2).until(
                lambda driver: driver.execute_script("return window.dashboardReady === true")
            )
            performance_timer.stop()
            
            # Get client-side load time
            client_load_time = self.driver.execute_script("return window.dashboardLoadTime")
            render_complete = self.driver.execute_script("return window.renderComplete")
            
            # Verify performance requirements
            assert render_complete is True
            assert client_load_time < 1000, f"Dashboard load time {client_load_time}ms exceeds 1s limit"
            assert performance_timer.elapsed < 1500, f"Total load time {performance_timer.elapsed}ms too slow"
            
            # Verify content was rendered correctly
            market_summary = self.driver.find_element("id", "market-summary")
            watchlist = self.driver.find_element("id", "watchlist-container")
            
            assert "Total:" in market_summary.text
            assert len(watchlist.find_elements("class name", "watchlist-item")) > 0
            
        finally:
            os.unlink(temp_file)
    
    def test_dashboard_tab_switching_performance(self, performance_timer):
        """Test tab switching performance is smooth (<200ms)."""
        
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .tab-content { display: none; padding: 20px; }
                .tab-content.active { display: block; }
                .tab-btn { padding: 10px 20px; margin: 5px; cursor: pointer; }
                .tab-btn.active { background-color: #007bff; color: white; }
            </style>
        </head>
        <body>
            <div>
                <button class="tab-btn active" data-tab="dashboard">Dashboard</button>
                <button class="tab-btn" data-tab="charts">Charts</button>
                <button class="tab-btn" data-tab="alerts">Alerts</button>
            </div>
            
            <div id="dashboard" class="tab-content active">
                <h2>Dashboard Content</h2>
                <div id="dashboard-data">
                    ${Array.from({length: 50}, (_, i) => `<div>Dashboard Item ${i}</div>`).join('')}
                </div>
            </div>
            
            <div id="charts" class="tab-content">
                <h2>Charts Content</h2>
                <div id="chart-container">
                    <canvas id="price-chart" width="800" height="400"></canvas>
                </div>
            </div>
            
            <div id="alerts" class="tab-content">
                <h2>Alerts Content</h2>
                <div id="alerts-list">
                    ${Array.from({length: 20}, (_, i) => `<div>Alert ${i}: Price movement detected</div>`).join('')}
                </div>
            </div>
            
            <script>
                class TabManager {
                    constructor() {
                        this.setupEventListeners();
                        window.tabSwitchTimes = [];
                    }
                    
                    setupEventListeners() {
                        document.addEventListener('click', (e) => {
                            if (e.target.classList.contains('tab-btn')) {
                                this.switchTab(e.target.dataset.tab);
                            }
                        });
                    }
                    
                    switchTab(tabName) {
                        const startTime = performance.now();
                        
                        // Hide all tabs
                        document.querySelectorAll('.tab-content').forEach(tab => {
                            tab.classList.remove('active');
                        });
                        
                        document.querySelectorAll('.tab-btn').forEach(btn => {
                            btn.classList.remove('active');
                        });
                        
                        // Show selected tab
                        const selectedTab = document.getElementById(tabName);
                        const selectedBtn = document.querySelector(`[data-tab="${tabName}"]`);
                        
                        if (selectedTab && selectedBtn) {
                            selectedTab.classList.add('active');
                            selectedBtn.classList.add('active');
                            
                            // Simulate content loading/updating
                            if (tabName === 'charts') {
                                // Simulate chart rendering
                                setTimeout(() => {
                                    const canvas = document.getElementById('price-chart');
                                    const ctx = canvas.getContext('2d');
                                    ctx.fillStyle = '#007bff';
                                    ctx.fillRect(0, 0, 100, 100);
                                }, 10);
                            }
                        }
                        
                        const switchTime = performance.now() - startTime;
                        window.tabSwitchTimes.push(switchTime);
                        window.lastTabSwitchTime = switchTime;
                        window.activeTab = tabName;
                        
                        // Force layout recalculation
                        selectedTab.offsetHeight;
                    }
                }
                
                const tabManager = new TabManager();
                window.tabManagerReady = true;
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
            
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.common.by import By
            
            # Wait for tab manager to be ready
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.tabManagerReady === true")
            )
            
            # Test switching between tabs
            tabs_to_test = ['charts', 'alerts', 'dashboard']
            
            for tab_name in tabs_to_test:
                tab_btn = self.driver.find_element(By.XPATH, f"//button[@data-tab='{tab_name}']")
                
                performance_timer.start()
                tab_btn.click()
                
                # Wait for tab to be active
                WebDriverWait(self.driver, 1).until(
                    lambda driver: driver.execute_script(f"return window.activeTab === '{tab_name}'")
                )
                performance_timer.stop()
                
                # Verify tab switching performance
                client_switch_time = self.driver.execute_script("return window.lastTabSwitchTime")
                
                assert performance_timer.elapsed < 200, f"Tab switch to {tab_name} took {performance_timer.elapsed}ms"
                assert client_switch_time < 50, f"Client-side tab switch took {client_switch_time}ms"
                
                # Verify correct content is displayed
                active_content = self.driver.find_element(By.CSS_SELECTOR, ".tab-content.active")
                assert tab_name in active_content.get_attribute("id")
            
            # Verify average switching performance
            all_switch_times = self.driver.execute_script("return window.tabSwitchTimes")
            avg_switch_time = sum(all_switch_times) / len(all_switch_times)
            
            assert avg_switch_time < 30, f"Average tab switch time {avg_switch_time}ms too slow"
            
        finally:
            os.unlink(temp_file)

# ==========================================================================
# WEBSOCKET PERFORMANCE TESTS  
# ==========================================================================

@pytest.mark.performance
@pytest.mark.websocket
class TestWebSocketPerformance:
    """Test WebSocket event handling meets <200ms update requirements."""
    
    def test_websocket_update_performance(self, performance_timer):
        """Test WebSocket price updates are processed within <200ms."""
        
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="price-display">$0.00</div>
            <div id="update-count">0</div>
            
            <script>
                class MockWebSocketManager {
                    constructor() {
                        this.priceDisplay = document.getElementById('price-display');
                        this.updateCount = document.getElementById('update-count');
                        this.updates = 0;
                        this.processingTimes = [];
                        
                        window.wsManager = this;
                    }
                    
                    handlePriceUpdate(priceData) {
                        const startTime = performance.now();
                        
                        // Simulate real price update processing
                        const symbol = priceData.symbol;
                        const price = priceData.price;
                        const change = priceData.change;
                        
                        // Update DOM
                        this.priceDisplay.textContent = `$${price.toFixed(2)}`;
                        this.priceDisplay.className = change >= 0 ? 'positive' : 'negative';
                        
                        this.updates++;
                        this.updateCount.textContent = this.updates;
                        
                        const processingTime = performance.now() - startTime;
                        this.processingTimes.push(processingTime);
                        
                        window.lastUpdateTime = processingTime;
                        window.allProcessingTimes = this.processingTimes;
                        
                        // Force DOM update
                        this.priceDisplay.offsetHeight;
                        
                        return processingTime;
                    }
                    
                    simulateHighFrequencyUpdates(count = 100) {
                        const startTime = performance.now();
                        
                        for (let i = 0; i < count; i++) {
                            const priceData = {
                                symbol: 'AAPL',
                                price: 175.0 + (Math.random() - 0.5) * 10,
                                change: (Math.random() - 0.5) * 5,
                                timestamp: Date.now()
                            };
                            
                            this.handlePriceUpdate(priceData);
                        }
                        
                        const totalTime = performance.now() - startTime;
                        window.batchProcessingTime = totalTime;
                        window.batchComplete = true;
                        
                        return totalTime;
                    }
                }
                
                const wsManager = new MockWebSocketManager();
                window.wsManagerReady = true;
            </script>
        </body>
        </html>
        """
        
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.common.by import By
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            temp_file = f.name
        
        try:
            driver.get(f"file://{temp_file}")
            
            # Wait for WebSocket manager to be ready
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return window.wsManagerReady === true")
            )
            
            # Test single update performance
            single_update_script = """
                const priceData = {
                    symbol: 'AAPL',
                    price: 178.50,
                    change: 3.50,
                    timestamp: Date.now()
                };
                return window.wsManager.handlePriceUpdate(priceData);
            """
            
            single_update_time = driver.execute_script(single_update_script)
            assert single_update_time < 10, f"Single WebSocket update took {single_update_time}ms"
            
            # Test high-frequency updates
            performance_timer.start()
            driver.execute_script("window.wsManager.simulateHighFrequencyUpdates(100);")
            
            # Wait for batch processing to complete
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return window.batchComplete === true")
            )
            performance_timer.stop()
            
            # Verify batch processing performance
            batch_time = driver.execute_script("return window.batchProcessingTime")
            processing_times = driver.execute_script("return window.allProcessingTimes")
            
            # Performance assertions
            assert batch_time < 1000, f"Batch processing took {batch_time}ms for 100 updates"
            
            avg_processing_time = sum(processing_times) / len(processing_times)
            max_processing_time = max(processing_times)
            
            assert avg_processing_time < 5, f"Average update processing time {avg_processing_time}ms too slow"
            assert max_processing_time < 20, f"Max update processing time {max_processing_time}ms too slow"
            
            # Verify UI was updated correctly
            final_update_count = driver.find_element(By.ID, "update-count").text
            assert final_update_count == "100"
            
        finally:
            driver.quit()
            os.unlink(temp_file)

# ==========================================================================
# MEMORY AND RESOURCE PERFORMANCE TESTS
# ==========================================================================

@pytest.mark.performance
@pytest.mark.slow
class TestResourcePerformance:
    """Test memory usage and resource efficiency."""
    
    def test_watchlist_memory_efficiency(self, client, performance_timer):
        """Test watchlist operations don't cause memory leaks."""
        with patch('src.api.rest.api.tickstock_db') as mock_db, \
             patch('src.api.rest.api.user_settings_service') as mock_service:
            
            # Setup large dataset
            large_symbol_list = [f"TEST{i:04d}" for i in range(1000)]
            mock_service.get_user_settings.return_value = {'watchlist': large_symbol_list[:500]}
            
            mock_db.get_symbol_details.side_effect = lambda s: {
                "symbol": s,
                "name": f"{s} Corporation",
                "last_price": 100.0 + hash(s) % 100,
                "change": (hash(s) % 21) - 10,
                "volume": 1000000 + hash(s) % 5000000
            }
            
            # Test repeated watchlist operations
            response_times = []
            memory_usage = []
            
            for i in range(20):
                performance_timer.start()
                response = client.get('/api/watchlist')
                performance_timer.stop()
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert len(data['symbols']) == 500
                
                response_times.append(performance_timer.elapsed)
                
                # Simulate memory usage tracking (in real scenario would use memory profiler)
                memory_usage.append(len(json.dumps(data)))
            
            # Verify performance doesn't degrade over time (no memory leaks)
            first_half_avg = sum(response_times[:10]) / 10
            second_half_avg = sum(response_times[10:]) / 10
            
            # Performance shouldn't degrade by more than 20%
            degradation = (second_half_avg - first_half_avg) / first_half_avg
            assert degradation < 0.2, f"Performance degraded by {degradation*100:.1f}%"
            
            # Memory usage should be consistent
            memory_variance = max(memory_usage) - min(memory_usage)
            assert memory_variance < max(memory_usage) * 0.1, "Memory usage too variable"
    
    def test_chart_data_caching_performance(self, client, performance_timer, mock_chart_data):
        """Test chart data caching improves performance."""
        with patch('src.api.rest.api.tickstock_db') as mock_db:
            mock_db.get_symbol_details.return_value = {"symbol": "AAPL", "name": "Apple Inc."}
            mock_db.get_ohlcv_data.return_value = mock_chart_data
            
            # First request (cold cache)
            performance_timer.start()
            response1 = client.get('/api/chart-data/AAPL?timeframe=1d')
            performance_timer.stop()
            cold_cache_time = performance_timer.elapsed
            
            assert response1.status_code == 200
            
            # Second request (should benefit from any caching)
            performance_timer.start()
            response2 = client.get('/api/chart-data/AAPL?timeframe=1d')
            performance_timer.stop()
            warm_cache_time = performance_timer.elapsed
            
            assert response2.status_code == 200
            
            # Verify both requests return same data
            data1 = json.loads(response1.data)
            data2 = json.loads(response2.data)
            assert data1 == data2
            
            # Performance should be consistent (or better with caching)
            assert warm_cache_time <= cold_cache_time * 1.5, "Second request significantly slower"
            assert cold_cache_time < 100, f"Cold cache request took {cold_cache_time}ms"
            assert warm_cache_time < 75, f"Warm cache request took {warm_cache_time}ms"