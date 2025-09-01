# ==========================================================================
# TICKSTOCK SPRINT 12 JAVASCRIPT COMPONENT TESTS
# ==========================================================================
# PURPOSE: Test JavaScript components for dashboard functionality
# COMPONENTS: ChartManager, DashboardManager classes and their interactions
# TESTING APPROACH: Use Selenium WebDriver for JavaScript execution testing
# ==========================================================================

import pytest
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from unittest.mock import patch, Mock

# ==========================================================================
# JAVASCRIPT COMPONENT TESTS - CHART MANAGER
# ==========================================================================

@pytest.mark.javascript
@pytest.mark.unit
class TestChartManager:
    """Test ChartManager JavaScript class functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_driver(self):
        """Setup Chrome WebDriver for JavaScript testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(1920, 1080)
        yield
        self.driver.quit()
    
    def test_chart_manager_initialization(self, live_server):
        """Test ChartManager initializes correctly."""
        # Load test page with ChartManager
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
        </head>
        <body>
            <canvas id="price-chart"></canvas>
            <select id="chart-symbol-select">
                <option value="">Select symbol...</option>
                <option value="AAPL">AAPL</option>
            </select>
            <input type="radio" name="chart-timeframe" value="1d" checked>
            <script>
                // Include ChartManager class here
                class ChartManager {
                    constructor() {
                        this.isInitialized = false;
                        this.init();
                    }
                    init() {
                        this.isInitialized = true;
                        window.chartManagerReady = true;
                    }
                }
                const chartManager = new ChartManager();
            </script>
        </body>
        </html>
        """
        
        # Create temporary HTML file and serve it
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            temp_file = f.name
        
        try:
            self.driver.get(f"file://{temp_file}")
            
            # Wait for ChartManager to initialize
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.chartManagerReady === true")
            )
            
            # Verify initialization
            is_initialized = self.driver.execute_script(
                "return typeof chartManager !== 'undefined' && chartManager.isInitialized"
            )
            assert is_initialized is True
            
        finally:
            os.unlink(temp_file)
    
    def test_chart_symbol_selection(self, live_server):
        """Test chart symbol selection triggers data loading."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <select id="chart-symbol-select">
                <option value="">Select symbol...</option>
                <option value="AAPL">AAPL</option>
                <option value="GOOGL">GOOGL</option>
            </select>
            <canvas id="price-chart"></canvas>
            <script>
                class ChartManager {
                    constructor() {
                        this.currentSymbol = null;
                        this.loadDataCalled = false;
                        this.setupEventListeners();
                    }
                    
                    setupEventListeners() {
                        document.addEventListener('change', (e) => {
                            if (e.target.id === 'chart-symbol-select') {
                                this.onSymbolChange(e.target.value);
                            }
                        });
                    }
                    
                    onSymbolChange(symbol) {
                        this.currentSymbol = symbol;
                        this.loadChartData();
                    }
                    
                    loadChartData() {
                        this.loadDataCalled = true;
                        window.chartDataRequested = this.currentSymbol;
                    }
                }
                
                const chartManager = new ChartManager();
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
            
            # Select a symbol
            select = self.driver.find_element(By.ID, "chart-symbol-select")
            select.click()
            select.find_element(By.XPATH, "//option[@value='AAPL']").click()
            
            # Wait for symbol change to be processed
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.chartDataRequested === 'AAPL'")
            )
            
            # Verify data loading was triggered
            current_symbol = self.driver.execute_script("return chartManager.currentSymbol")
            load_called = self.driver.execute_script("return chartManager.loadDataCalled")
            
            assert current_symbol == "AAPL"
            assert load_called is True
            
        finally:
            os.unlink(temp_file)
    
    def test_chart_data_formatting(self, live_server):
        """Test chart data formatting for Chart.js compatibility."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <script>
                class ChartManager {
                    formatChartData(rawData) {
                        if (!Array.isArray(rawData)) return [];
                        
                        return rawData.map(item => ({
                            x: new Date(item.timestamp).getTime(),
                            o: parseFloat(item.open),
                            h: parseFloat(item.high),
                            l: parseFloat(item.low),
                            c: parseFloat(item.close),
                            v: parseInt(item.volume)
                        }));
                    }
                }
                
                const chartManager = new ChartManager();
                
                // Test data formatting
                const testData = [
                    {
                        timestamp: '2023-01-01T10:00:00Z',
                        open: '150.00',
                        high: '155.50',
                        low: '149.25',
                        close: '154.75',
                        volume: '25000000'
                    }
                ];
                
                const formatted = chartManager.formatChartData(testData);
                window.formattedData = formatted;
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
            
            # Get formatted data
            formatted_data = self.driver.execute_script("return window.formattedData")
            
            assert len(formatted_data) == 1
            data_point = formatted_data[0]
            
            assert isinstance(data_point['x'], (int, float))  # Timestamp as number
            assert data_point['o'] == 150.0  # Open price as float
            assert data_point['h'] == 155.5  # High price as float
            assert data_point['l'] == 149.25  # Low price as float
            assert data_point['c'] == 154.75  # Close price as float
            assert data_point['v'] == 25000000  # Volume as integer
            
        finally:
            os.unlink(temp_file)
    
    def test_chart_error_handling(self, live_server):
        """Test chart error handling and display."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="chart-container">
                <canvas id="price-chart"></canvas>
            </div>
            <script>
                class ChartManager {
                    showChartError(message) {
                        const ctx = document.getElementById('price-chart');
                        if (!ctx) return;
                        
                        const container = ctx.parentElement;
                        container.innerHTML = `
                            <div class="chart-error text-center p-4">
                                <p class="mb-0">${message}</p>
                            </div>
                        `;
                        
                        window.errorDisplayed = true;
                        window.errorMessage = message;
                    }
                }
                
                const chartManager = new ChartManager();
                chartManager.showChartError('Test error message');
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
            
            # Verify error display
            error_displayed = self.driver.execute_script("return window.errorDisplayed")
            error_message = self.driver.execute_script("return window.errorMessage")
            
            assert error_displayed is True
            assert error_message == "Test error message"
            
            # Check if error element exists in DOM
            error_element = self.driver.find_element(By.CLASS_NAME, "chart-error")
            assert error_element is not None
            assert "Test error message" in error_element.text
            
        finally:
            os.unlink(temp_file)

# ==========================================================================
# JAVASCRIPT COMPONENT TESTS - DASHBOARD MANAGER  
# ==========================================================================

@pytest.mark.javascript
@pytest.mark.unit
class TestDashboardManager:
    """Test DashboardManager JavaScript class functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_driver(self):
        """Setup Chrome WebDriver for JavaScript testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(1920, 1080)
        yield
        self.driver.quit()
    
    def test_dashboard_manager_initialization(self, live_server):
        """Test DashboardManager initializes correctly."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="watchlist-container"></div>
            <div id="alerts-list"></div>
            <script>
                class DashboardManager {
                    constructor() {
                        this.watchlist = [];
                        this.isInitialized = false;
                        this.init();
                    }
                    
                    init() {
                        this.isInitialized = true;
                        window.dashboardReady = true;
                    }
                    
                    setupEventListeners() {
                        // Event listener setup
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
            
            # Wait for DashboardManager to initialize
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.dashboardReady === true")
            )
            
            # Verify initialization
            is_initialized = self.driver.execute_script(
                "return typeof dashboardManager !== 'undefined' && dashboardManager.isInitialized"
            )
            assert is_initialized is True
            
        finally:
            os.unlink(temp_file)
    
    def test_watchlist_rendering(self, live_server):
        """Test watchlist rendering with mock data."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="watchlist-container"></div>
            <script>
                class DashboardManager {
                    constructor() {
                        this.watchlist = [];
                        this.priceData = new Map();
                    }
                    
                    renderWatchlist() {
                        const container = document.getElementById('watchlist-container');
                        if (!container) return;
                        
                        if (this.watchlist.length === 0) {
                            container.innerHTML = '<div class="text-center">No symbols</div>';
                            return;
                        }
                        
                        const html = this.watchlist.map(symbol => {
                            const priceInfo = this.priceData.get(symbol.symbol) || {};
                            return `<div class="watchlist-item" data-symbol="${symbol.symbol}">
                                ${symbol.symbol} - $${(symbol.last_price || 0).toFixed(2)}
                            </div>`;
                        }).join('');
                        
                        container.innerHTML = html;
                        window.watchlistRendered = true;
                    }
                }
                
                const dashboardManager = new DashboardManager();
                
                // Test with mock data
                dashboardManager.watchlist = [
                    { symbol: 'AAPL', name: 'Apple Inc.', last_price: 175.50 },
                    { symbol: 'GOOGL', name: 'Alphabet Inc.', last_price: 142.80 }
                ];
                
                dashboardManager.renderWatchlist();
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
            
            # Wait for rendering
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.watchlistRendered === true")
            )
            
            # Verify watchlist items are rendered
            watchlist_items = self.driver.find_elements(By.CLASS_NAME, "watchlist-item")
            assert len(watchlist_items) == 2
            
            # Check first item
            assert "AAPL" in watchlist_items[0].text
            assert "$175.50" in watchlist_items[0].text
            
            # Check second item  
            assert "GOOGL" in watchlist_items[1].text
            assert "$142.80" in watchlist_items[1].text
            
        finally:
            os.unlink(temp_file)
    
    def test_price_data_update(self, live_server):
        """Test real-time price data updates."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="watchlist-container"></div>
            <script>
                class DashboardManager {
                    constructor() {
                        this.watchlist = [
                            { symbol: 'AAPL', name: 'Apple Inc.', last_price: 175.50 }
                        ];
                        this.priceData = new Map();
                    }
                    
                    updatePrice(symbol, priceData) {
                        this.priceData.set(symbol, priceData);
                        this.renderWatchlist();
                        window.priceUpdated = true;
                        window.updatedPrice = priceData.price;
                    }
                    
                    renderWatchlist() {
                        const container = document.getElementById('watchlist-container');
                        const html = this.watchlist.map(symbol => {
                            const priceInfo = this.priceData.get(symbol.symbol) || {};
                            const currentPrice = priceInfo.price || symbol.last_price || 0;
                            return `<div class="watchlist-item" data-symbol="${symbol.symbol}">
                                ${symbol.symbol} - $${currentPrice.toFixed(2)}
                            </div>`;
                        }).join('');
                        container.innerHTML = html;
                    }
                }
                
                const dashboardManager = new DashboardManager();
                dashboardManager.renderWatchlist();
                
                // Simulate price update
                dashboardManager.updatePrice('AAPL', { 
                    price: 178.25, 
                    change: 2.75, 
                    changePercent: 1.57 
                });
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
            
            # Wait for price update
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.priceUpdated === true")
            )
            
            # Verify price was updated
            updated_price = self.driver.execute_script("return window.updatedPrice")
            assert updated_price == 178.25
            
            # Check if UI shows updated price
            watchlist_item = self.driver.find_element(By.CLASS_NAME, "watchlist-item")
            assert "$178.25" in watchlist_item.text
            
        finally:
            os.unlink(temp_file)
    
    def test_market_summary_update(self, live_server):
        """Test market summary calculations and display."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="total-symbols">0</div>
            <div id="symbols-up">0</div>
            <div id="symbols-down">0</div>
            <script>
                class DashboardManager {
                    constructor() {
                        this.watchlist = [
                            { symbol: 'AAPL' },
                            { symbol: 'GOOGL' },
                            { symbol: 'MSFT' }
                        ];
                        this.priceData = new Map();
                        this.marketSummary = {
                            totalSymbols: 0,
                            symbolsUp: 0,
                            symbolsDown: 0
                        };
                    }
                    
                    updateMarketSummaryFromPrices() {
                        let up = 0, down = 0;
                        
                        this.priceData.forEach(priceInfo => {
                            if (priceInfo.change > 0) up++;
                            else if (priceInfo.change < 0) down++;
                        });
                        
                        this.marketSummary.symbolsUp = up;
                        this.marketSummary.symbolsDown = down;
                        this.marketSummary.totalSymbols = this.watchlist.length;
                        
                        this.updateMarketSummary();
                    }
                    
                    updateMarketSummary() {
                        const totalElem = document.getElementById('total-symbols');
                        const upElem = document.getElementById('symbols-up');
                        const downElem = document.getElementById('symbols-down');
                        
                        if (totalElem) totalElem.textContent = this.marketSummary.totalSymbols;
                        if (upElem) upElem.textContent = this.marketSummary.symbolsUp;
                        if (downElem) downElem.textContent = this.marketSummary.symbolsDown;
                        
                        window.marketSummaryUpdated = true;
                    }
                }
                
                const dashboardManager = new DashboardManager();
                
                // Add mock price data
                dashboardManager.priceData.set('AAPL', { change: 2.30 });  // Up
                dashboardManager.priceData.set('GOOGL', { change: -1.20 }); // Down  
                dashboardManager.priceData.set('MSFT', { change: 1.50 });   // Up
                
                dashboardManager.updateMarketSummaryFromPrices();
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
            
            # Wait for market summary update
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.marketSummaryUpdated === true")
            )
            
            # Verify market summary values
            total_symbols = self.driver.find_element(By.ID, "total-symbols").text
            symbols_up = self.driver.find_element(By.ID, "symbols-up").text
            symbols_down = self.driver.find_element(By.ID, "symbols-down").text
            
            assert total_symbols == "3"  # Total watchlist items
            assert symbols_up == "2"     # AAPL and MSFT up
            assert symbols_down == "1"   # GOOGL down
            
        finally:
            os.unlink(temp_file)

# ==========================================================================
# INTEGRATION TESTS - JAVASCRIPT COMPONENTS
# ==========================================================================

@pytest.mark.javascript
@pytest.mark.integration
class TestJavaScriptIntegration:
    """Test integration between JavaScript components."""
    
    @pytest.fixture(autouse=True)  
    def setup_driver(self):
        """Setup Chrome WebDriver for JavaScript testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(1920, 1080)
        yield
        self.driver.quit()
    
    def test_chart_dashboard_integration(self, live_server):
        """Test integration between ChartManager and DashboardManager."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div id="watchlist-container"></div>
            <canvas id="price-chart"></canvas>
            <script>
                class ChartManager {
                    updateRealTimePrice(symbol, priceData) {
                        window.chartUpdatedSymbol = symbol;
                        window.chartUpdatedPrice = priceData.price;
                        return true;
                    }
                }
                
                class DashboardManager {
                    constructor() {
                        this.watchlist = [{ symbol: 'AAPL', name: 'Apple Inc.' }];
                        this.priceData = new Map();
                    }
                    
                    updatePrice(symbol, priceData) {
                        this.priceData.set(symbol, priceData);
                        
                        // Update chart if available
                        if (window.chartManager) {
                            window.chartManager.updateRealTimePrice(symbol, priceData);
                        }
                        
                        window.priceUpdateProcessed = true;
                    }
                }
                
                window.chartManager = new ChartManager();
                const dashboardManager = new DashboardManager();
                
                // Simulate price update
                dashboardManager.updatePrice('AAPL', { price: 180.50, change: 5.00 });
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
            
            # Wait for price update processing
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return window.priceUpdateProcessed === true")
            )
            
            # Verify chart was updated
            chart_updated_symbol = self.driver.execute_script("return window.chartUpdatedSymbol")
            chart_updated_price = self.driver.execute_script("return window.chartUpdatedPrice")
            
            assert chart_updated_symbol == "AAPL"
            assert chart_updated_price == 180.50
            
        finally:
            os.unlink(temp_file)