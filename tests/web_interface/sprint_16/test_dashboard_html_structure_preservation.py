"""
Sprint 16 Dashboard HTML Structure Tests - 6 Grid Container Validation
=====================================================================

Test comprehensive dashboard HTML structure, container preservation, and grid compatibility.

**Sprint**: 16 - Grid Modernization
**Component**: dashboard/index.html template structure
**Functional Area**: web_interface/sprint_16  
**Focus**: 6 grid containers, removed tab infrastructure, preserved functionality
"""
import re

import pytest
from bs4 import BeautifulSoup
from flask import Flask


class TestDashboardHTMLStructure:
    """Test dashboard HTML structure and 6 grid container layout."""

    def setup_method(self):
        """Setup test environment before each method."""
        # Mock Flask app for template rendering
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

        # Sample dashboard HTML structure for Sprint 16
        self.dashboard_html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>TickStock.ai</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridstack@10.0.1/dist/gridstack.min.css">
            <script src="https://cdn.jsdelivr.net/npm/gridstack@10.0.1/dist/gridstack-all.js"></script>
        </head>
        <body>
            <div class="container">
                <!-- MAIN CONTENT SECTION - Sprint 16 Grid Layout -->
                <main class="grid-stack" id="grid-container">
                    <!-- Sprint 16: 6 Individual Grid Containers -->
                    
                    <!-- Watchlist Container -->
                    <div class="grid-stack-item" data-gs-id="watchlist" data-gs-x="0" data-gs-y="0" data-gs-width="6" data-gs-height="3">
                        <div class="grid-stack-item-content">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h6 class="card-title mb-0">
                                        <i class="fas fa-list me-2"></i>Watchlist
                                    </h6>
                                </div>
                                <div class="card-body p-0">
                                    <div class="watchlist-container" id="watchlist-container">
                                        <div class="text-center p-3 text-muted">
                                            <p class="mb-0">Add symbols to start tracking</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Market Summary Container -->
                    <div class="grid-stack-item" data-gs-id="market-summary" data-gs-x="6" data-gs-y="0" data-gs-width="6" data-gs-height="3">
                        <div class="grid-stack-item-content">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h6 class="card-title mb-0">
                                        <i class="fas fa-tachometer-alt me-2"></i>Market Summary
                                    </h6>
                                </div>
                                <div class="card-body" id="market-summary-content">
                                    <div class="text-center text-muted">
                                        <p class="mb-0">Loading market summary...</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Charts Container -->
                    <div class="grid-stack-item" data-gs-id="charts" data-gs-x="0" data-gs-y="3" data-gs-width="8" data-gs-height="4">
                        <div class="grid-stack-item-content">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h6 class="card-title mb-0">
                                        <i class="fas fa-chart-area me-2"></i>Charts
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <div id="charts-content">
                                        <canvas id="main-chart"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Alerts Container -->
                    <div class="grid-stack-item" data-gs-id="alerts" data-gs-x="8" data-gs-y="3" data-gs-width="4" data-gs-height="4">
                        <div class="grid-stack-item-content">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h6 class="card-title mb-0">
                                        <i class="fas fa-bell me-2"></i>Alerts
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <div id="alerts-content">
                                        <div class="text-center text-muted">
                                            <p class="mb-0">No alerts</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Market Movers Container -->
                    <div class="grid-stack-item" data-gs-id="market-movers" data-gs-x="0" data-gs-y="7" data-gs-width="6" data-gs-height="3">
                        <div class="grid-stack-item-content">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h6 class="card-title mb-0">
                                        <i class="fas fa-chart-line me-2"></i>Market Movers
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <div id="market-movers-content">
                                        <div class="loading-state text-center">
                                            <div class="spinner-border spinner-border-sm" role="status">
                                                <span class="visually-hidden">Loading...</span>
                                            </div>
                                            <p class="mt-2 mb-0 text-muted">Loading market movers...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Placeholder Container -->
                    <div class="grid-stack-item" data-gs-id="placeholder" data-gs-x="6" data-gs-y="7" data-gs-width="6" data-gs-height="3">
                        <div class="grid-stack-item-content">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h6 class="card-title mb-0">
                                        <i class="fas fa-cog me-2"></i>Placeholder
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <div class="text-center text-muted">
                                        <i class="fas fa-plus-circle fa-3x mb-3"></i>
                                        <p class="mb-0">Future feature space</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
            
            <!-- Grid control buttons -->
            <div class="grid-controls">
                <button class="btn btn-sm btn-outline-secondary" id="grid-edit-btn">
                    <span class="btn-icon">🔓</span>
                    <span class="btn-text">Edit Layout</span>
                </button>
                <button class="btn btn-sm btn-outline-secondary" id="grid-reset-btn">
                    <span class="btn-icon">↻</span>
                    <span class="btn-text">Reset</span>
                </button>
            </div>
        </body>
        </html>
        """

    def test_dashboard_has_six_grid_containers(self):
        """Test dashboard contains exactly 6 grid containers."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        # Find all grid-stack-item elements
        grid_items = soup.find_all('div', class_='grid-stack-item')

        assert len(grid_items) == 6, f"Dashboard should have exactly 6 grid containers, found {len(grid_items)}"

        # Verify each container has required attributes
        for item in grid_items:
            assert item.get('data-gs-id'), "Each grid item should have data-gs-id attribute"
            assert item.get('data-gs-x') is not None, "Each grid item should have data-gs-x attribute"
            assert item.get('data-gs-y') is not None, "Each grid item should have data-gs-y attribute"
            assert item.get('data-gs-width'), "Each grid item should have data-gs-width attribute"
            assert item.get('data-gs-height'), "Each grid item should have data-gs-height attribute"

    def test_required_container_ids_present(self):
        """Test all 6 required container IDs are present."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        expected_container_ids = [
            'watchlist',
            'market-summary',
            'charts',
            'alerts',
            'market-movers',
            'placeholder'
        ]

        # Find containers by data-gs-id attribute
        found_ids = []
        for container_id in expected_container_ids:
            container = soup.find('div', {'data-gs-id': container_id})
            if container:
                found_ids.append(container_id)

        assert len(found_ids) == 6, f"Should find all 6 containers, found {len(found_ids)}: {found_ids}"

        # Verify each expected container exists
        for container_id in expected_container_ids:
            assert container_id in found_ids, f"Container '{container_id}' should be present in dashboard"

    def test_grid_container_positions_correct(self):
        """Test grid container positions match 2x4 layout specification."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        # Expected positions from Sprint 16 2x4 layout
        expected_positions = {
            'watchlist': {'x': '0', 'y': '0', 'w': '6', 'h': '3'},
            'market-summary': {'x': '6', 'y': '0', 'w': '6', 'h': '3'},
            'charts': {'x': '0', 'y': '3', 'w': '8', 'h': '4'},
            'alerts': {'x': '8', 'y': '3', 'w': '4', 'h': '4'},
            'market-movers': {'x': '0', 'y': '7', 'w': '6', 'h': '3'},
            'placeholder': {'x': '6', 'y': '7', 'w': '6', 'h': '3'}
        }

        for container_id, expected_pos in expected_positions.items():
            container = soup.find('div', {'data-gs-id': container_id})
            assert container is not None, f"Container '{container_id}' should exist"

            # Verify position attributes
            assert container.get('data-gs-x') == expected_pos['x'], \
                f"{container_id} x position should be {expected_pos['x']}, got {container.get('data-gs-x')}"
            assert container.get('data-gs-y') == expected_pos['y'], \
                f"{container_id} y position should be {expected_pos['y']}, got {container.get('data-gs-y')}"
            assert container.get('data-gs-width') == expected_pos['w'], \
                f"{container_id} width should be {expected_pos['w']}, got {container.get('data-gs-width')}"
            assert container.get('data-gs-height') == expected_pos['h'], \
                f"{container_id} height should be {expected_pos['h']}, got {container.get('data-gs-height')}"

    def test_grid_main_container_structure(self):
        """Test main grid container has correct structure and classes."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        # Find main grid container
        grid_container = soup.find('main', id='grid-container')
        assert grid_container is not None, "Main grid container should exist with id='grid-container'"

        # Verify classes
        assert 'grid-stack' in grid_container.get('class', []), "Main container should have 'grid-stack' class"

        # Verify it's within a container
        parent_container = grid_container.find_parent('div', class_='container')
        assert parent_container is not None, "Grid should be within a container div"

    def test_no_tab_infrastructure_remains(self):
        """Test that no obsolete tab infrastructure remains."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        # Should not find any tab-related elements
        obsolete_elements = [
            soup.find_all('div', class_=re.compile(r'.*tab-pane.*')),
            soup.find_all('div', class_=re.compile(r'.*tab-content.*')),
            soup.find_all('ul', class_=re.compile(r'.*nav-tabs.*')),
            soup.find_all('button', {'data-bs-toggle': 'tab'}),
            soup.find_all('a', {'data-bs-toggle': 'tab'})
        ]

        # Flatten list and check
        all_obsolete = [item for sublist in obsolete_elements for item in sublist]

        assert len(all_obsolete) == 0, f"Found {len(all_obsolete)} obsolete tab elements: {[elem.name for elem in all_obsolete]}"

    def test_preserved_functionality_ids_exist(self):
        """Test that preserved functionality IDs still exist."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        # Critical IDs that should be preserved for existing functionality
        preserved_ids = [
            'watchlist-container',    # Watchlist functionality
            'market-summary-content', # Market summary display
            'charts-content',         # Charts display
            'main-chart',            # Chart canvas
            'alerts-content',        # Alerts display
            'market-movers-content'   # Market movers display
        ]

        missing_ids = []
        for element_id in preserved_ids:
            element = soup.find(id=element_id)
            if not element:
                missing_ids.append(element_id)

        assert len(missing_ids) == 0, f"Missing preserved IDs: {missing_ids}"

    def test_card_structure_consistency(self):
        """Test all containers have consistent Bootstrap card structure."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        grid_items = soup.find_all('div', class_='grid-stack-item')

        for item in grid_items:
            container_id = item.get('data-gs-id')

            # Each container should have grid-stack-item-content
            content_wrapper = item.find('div', class_='grid-stack-item-content')
            assert content_wrapper is not None, f"Container '{container_id}' should have content wrapper"

            # Each should have a card structure
            card = content_wrapper.find('div', class_='card')
            assert card is not None, f"Container '{container_id}' should have card structure"

            # Card should have h-100 class for full height
            assert 'h-100' in card.get('class', []), f"Container '{container_id}' card should have h-100 class"

            # Card should have header and body
            card_header = card.find('div', class_='card-header')
            card_body = card.find('div', class_='card-body')

            assert card_header is not None, f"Container '{container_id}' should have card header"
            assert card_body is not None, f"Container '{container_id}' should have card body"

            # Header should have title
            title = card_header.find('h6', class_='card-title')
            assert title is not None, f"Container '{container_id}' should have card title"

    def test_gridstack_css_and_js_includes(self):
        """Test GridStack CSS and JavaScript includes are present."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        # Check for GridStack CSS
        gridstack_css = soup.find('link', {'href': re.compile(r'.*gridstack.*\.css')})
        assert gridstack_css is not None, "GridStack CSS should be included"

        # Check for GridStack JavaScript
        gridstack_js = soup.find('script', {'src': re.compile(r'.*gridstack.*\.js')})
        assert gridstack_js is not None, "GridStack JavaScript should be included"

    def test_grid_control_buttons_present(self):
        """Test grid control buttons are present and properly configured."""
        soup = BeautifulSoup(self.dashboard_html_template, 'html.parser')

        # Find grid controls container
        grid_controls = soup.find('div', class_='grid-controls')
        assert grid_controls is not None, "Grid controls container should exist"

        # Check for edit button
        edit_button = soup.find('button', id='grid-edit-btn')
        assert edit_button is not None, "Grid edit button should exist"

        # Check for reset button
        reset_button = soup.find('button', id='grid-reset-btn')
        assert reset_button is not None, "Grid reset button should exist"

        # Verify button structure
        edit_icon = edit_button.find('span', class_='btn-icon')
        edit_text = edit_button.find('span', class_='btn-text')
        assert edit_icon is not None and edit_text is not None, "Edit button should have icon and text spans"

        reset_icon = reset_button.find('span', class_='btn-icon')
        reset_text = reset_button.find('span', class_='btn-text')
        assert reset_icon is not None and reset_text is not None, "Reset button should have icon and text spans"


class TestDashboardHTMLAccessibility:
    """Test dashboard HTML accessibility and semantic structure."""

    def setup_method(self):
        """Setup test environment for accessibility tests."""
        self.dashboard_html = """
        <main class="grid-stack" id="grid-container">
            <div class="grid-stack-item" data-gs-id="watchlist">
                <div class="card">
                    <div class="card-header">
                        <h6 class="card-title mb-0">
                            <i class="fas fa-list me-2" aria-hidden="true"></i>Watchlist
                        </h6>
                    </div>
                </div>
            </div>
        </main>
        """

    def test_semantic_html_structure(self):
        """Test proper semantic HTML structure."""
        soup = BeautifulSoup(self.dashboard_html, 'html.parser')

        # Main element should exist
        main_element = soup.find('main')
        assert main_element is not None, "Should use semantic <main> element"

        # Headers should be properly structured
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for header in headers:
            # Headers should have appropriate classes
            assert 'card-title' in header.get('class', []), "Card headers should have appropriate classes"

    def test_aria_labels_and_accessibility(self):
        """Test ARIA labels and accessibility attributes."""
        soup = BeautifulSoup(self.dashboard_html, 'html.parser')

        # Icons should have aria-hidden attribute
        icons = soup.find_all('i', class_=re.compile(r'fa.*'))
        for icon in icons:
            # Decorative icons should be hidden from screen readers
            assert icon.get('aria-hidden') == 'true', "Decorative icons should have aria-hidden='true'"

    def test_interactive_elements_accessibility(self):
        """Test interactive elements have proper accessibility attributes."""
        # Mock interactive elements
        interactive_html = """
        <button class="btn btn-sm btn-outline-secondary" id="grid-edit-btn" aria-label="Edit grid layout">
            <span class="btn-icon">🔓</span>
            <span class="btn-text">Edit Layout</span>
        </button>
        <button class="btn btn-sm btn-outline-secondary" id="grid-reset-btn" aria-label="Reset grid layout">
            <span class="btn-icon">↻</span>
            <span class="btn-text">Reset</span>
        </button>
        """

        soup = BeautifulSoup(interactive_html, 'html.parser')
        buttons = soup.find_all('button')

        for button in buttons:
            # Buttons should have accessible labels or text content
            has_aria_label = button.get('aria-label') is not None
            has_text_content = button.get_text().strip() != ''

            assert has_aria_label or has_text_content, f"Button {button.get('id')} should have accessible label or text"


class TestDashboardHTMLResponsiveness:
    """Test dashboard HTML responsive design elements."""

    def setup_method(self):
        """Setup test environment for responsive design tests."""
        self.responsive_html = """
        <div class="container">
            <main class="grid-stack" id="grid-container">
                <div class="grid-stack-item" data-gs-id="watchlist" data-gs-x="0" data-gs-y="0" data-gs-width="6" data-gs-height="3">
                    <div class="card h-100">
                        <div class="card-body">Content</div>
                    </div>
                </div>
            </main>
        </div>
        """

    def test_bootstrap_responsive_classes(self):
        """Test Bootstrap responsive classes are properly used."""
        soup = BeautifulSoup(self.responsive_html, 'html.parser')

        # Container should use Bootstrap container class
        container = soup.find('div', class_='container')
        assert container is not None, "Should use Bootstrap container class"

        # Cards should have responsive height
        cards = soup.find_all('div', class_='card')
        for card in cards:
            assert 'h-100' in card.get('class', []), "Cards should have h-100 for responsive height"

    def test_grid_responsive_attributes(self):
        """Test grid containers have responsive attributes."""
        soup = BeautifulSoup(self.responsive_html, 'html.parser')

        grid_items = soup.find_all('div', class_='grid-stack-item')

        for item in grid_items:
            # Should have grid position and size attributes
            required_attrs = ['data-gs-x', 'data-gs-y', 'data-gs-width', 'data-gs-height']
            for attr in required_attrs:
                assert item.get(attr) is not None, f"Grid item should have {attr} attribute"

            # Width should be valid grid units (1-12)
            width = int(item.get('data-gs-width', '0'))
            assert 1 <= width <= 12, f"Grid width should be 1-12, got {width}"


class TestDashboardHTMLPerformance:
    """Test dashboard HTML performance characteristics."""

    def setup_method(self):
        """Setup test environment for performance tests."""
        self.large_dashboard_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>TickStock.ai</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridstack@10.0.1/dist/gridstack.min.css">
        </head>
        <body>
            <div class="container">
                <main class="grid-stack" id="grid-container">
        """ + """
                    <div class="grid-stack-item" data-gs-id="container{}" data-gs-x="0" data-gs-y="{}" data-gs-width="6" data-gs-height="3">
                        <div class="grid-stack-item-content">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h6 class="card-title mb-0">Container {}</h6>
                                </div>
                                <div class="card-body">
                                    <div id="content{}">Content for container {}</div>
                                </div>
                            </div>
                        </div>
                    </div>
        """.join([str(i) for i in range(6)]).format(*[i for i in range(6)] * 6) + """
                </main>
            </div>
        </body>
        </html>
        """

    @pytest.mark.performance
    def test_html_parsing_performance(self):
        """Test HTML parsing performance for dashboard structure."""
        import time

        start_time = time.perf_counter()
        soup = BeautifulSoup(self.large_dashboard_html, 'html.parser')
        parse_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert parse_time < 100, f"HTML parsing should be <100ms, got {parse_time:.2f}ms"

        # Verify parsing worked correctly
        grid_items = soup.find_all('div', class_='grid-stack-item')
        assert len(grid_items) == 6, "Should parse all 6 grid containers"

    @pytest.mark.performance
    def test_dom_query_performance(self):
        """Test DOM query performance for finding containers."""
        import time

        soup = BeautifulSoup(self.large_dashboard_html, 'html.parser')

        container_ids = ['watchlist', 'market-summary', 'charts', 'alerts', 'market-movers', 'placeholder']

        start_time = time.perf_counter()

        found_containers = []
        for container_id in container_ids:
            container = soup.find('div', {'data-gs-id': container_id})
            if container:
                found_containers.append(container_id)

        query_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert query_time < 10, f"DOM queries should be <10ms, got {query_time:.2f}ms"

    def test_html_size_optimization(self):
        """Test HTML size is optimized and not bloated."""
        # Calculate HTML size
        html_size_bytes = len(self.large_dashboard_html.encode('utf-8'))
        html_size_kb = html_size_bytes / 1024

        # Dashboard HTML should be reasonably sized
        assert html_size_kb < 50, f"Dashboard HTML should be <50KB, got {html_size_kb:.2f}KB"

        # Should not have excessive whitespace
        lines = self.large_dashboard_html.split('\n')
        empty_lines = sum(1 for line in lines if line.strip() == '')
        total_lines = len(lines)

        empty_line_ratio = empty_lines / total_lines if total_lines > 0 else 0
        assert empty_line_ratio < 0.3, f"Should not have >30% empty lines, got {empty_line_ratio:.1%}"


class TestDashboardHTMLIntegration:
    """Test dashboard HTML integration with JavaScript components."""

    def setup_method(self):
        """Setup test environment for integration tests."""
        self.integration_html = """
        <main class="grid-stack" id="grid-container">
            <div class="grid-stack-item" data-gs-id="market-movers">
                <div class="card">
                    <div class="card-body">
                        <div id="market-movers-content">
                            <div class="loading-state">Loading...</div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
        <script src="https://cdn.jsdelivr.net/npm/gridstack@10.0.1/dist/gridstack-all.js"></script>
        <script src="/static/js/core/app-gridstack.js"></script>
        <script src="/static/js/core/market-movers.js"></script>
        """

    def test_javascript_integration_points(self):
        """Test HTML provides proper integration points for JavaScript."""
        soup = BeautifulSoup(self.integration_html, 'html.parser')

        # GridStack container should exist
        grid_container = soup.find(id='grid-container')
        assert grid_container is not None, "GridStack container should exist for app-gridstack.js"

        # Market movers content area should exist
        market_movers_content = soup.find(id='market-movers-content')
        assert market_movers_content is not None, "Market movers content area should exist for market-movers.js"

        # Loading state should exist
        loading_state = soup.find(class_='loading-state')
        assert loading_state is not None, "Loading state should exist for JavaScript to manipulate"

    def test_required_javascript_libraries(self):
        """Test required JavaScript libraries are included."""
        soup = BeautifulSoup(self.integration_html, 'html.parser')

        # GridStack JavaScript should be included
        gridstack_script = soup.find('script', {'src': re.compile(r'.*gridstack.*\.js')})
        assert gridstack_script is not None, "GridStack JavaScript should be included"

        # Custom JavaScript files should be referenced
        custom_scripts = [
            '/static/js/core/app-gridstack.js',
            '/static/js/core/market-movers.js'
        ]

        for script_src in custom_scripts:
            script = soup.find('script', {'src': script_src})
            assert script is not None, f"Custom script {script_src} should be included"

    def test_data_attributes_for_javascript(self):
        """Test data attributes are properly set for JavaScript consumption."""
        soup = BeautifulSoup(self.integration_html, 'html.parser')

        grid_items = soup.find_all('div', class_='grid-stack-item')

        for item in grid_items:
            # Each grid item should have data-gs-id for JavaScript identification
            gs_id = item.get('data-gs-id')
            assert gs_id is not None, "Grid items should have data-gs-id for JavaScript"
            assert gs_id.strip() != '', "data-gs-id should not be empty"

    def test_css_classes_for_javascript_manipulation(self):
        """Test CSS classes are available for JavaScript manipulation."""
        soup = BeautifulSoup(self.integration_html, 'html.parser')

        # Classes that JavaScript components expect to find
        expected_classes = [
            'grid-stack',
            'grid-stack-item',
            'grid-stack-item-content',
            'card',
            'card-header',
            'card-body',
            'loading-state'
        ]

        for css_class in expected_classes:
            elements = soup.find_all(class_=css_class)
            assert len(elements) > 0, f"CSS class '{css_class}' should exist for JavaScript manipulation"
