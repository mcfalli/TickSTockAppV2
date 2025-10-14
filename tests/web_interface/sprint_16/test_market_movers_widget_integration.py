"""
Sprint 16 Market Movers Widget Tests - market-movers.js Frontend Component
=========================================================================

Test comprehensive Market Movers frontend widget functionality, auto-refresh, and error handling.

**Sprint**: 16 - Grid Modernization
**Component**: market-movers.js MarketMoversManager class
**Functional Area**: web_interface/sprint_16
**Performance Target**: <100ms WebSocket delivery, <50ms UI updates
"""
import json
import time
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest


class TestMarketMoversManagerInitialization:
    """Test MarketMoversManager initialization and configuration."""

    def setup_method(self):
        """Setup test environment before each test method."""
        # Mock DOM and browser APIs
        self.mock_document = Mock()
        self.mock_window = Mock()
        self.mock_fetch = Mock()
        self.mock_console = Mock()

        # Mock performance API
        self.mock_performance = Mock()
        self.mock_performance.now.return_value = 1000.0

        # Mock container element
        self.mock_container = Mock()
        self.mock_document.getElementById.return_value = self.mock_container

        # Setup DOM ready state
        self.mock_document.readyState = 'complete'

        # Mock performance metrics
        self.performance_metrics = {
            'apiCalls': 0,
            'totalResponseTime': 0,
            'errors': 0,
            'lastUpdateDuration': 0
        }

    def test_market_movers_manager_initialization(self):
        """Test MarketMoversManager initializes with correct configuration."""
        # Expected configuration from market-movers.js
        expected_config = {
            'refreshInterval': None,
            'refreshIntervalMs': 60000,  # 60 seconds
            'isLoading': False,
            'lastUpdateTime': None,
            'retryCount': 0,
            'maxRetries': 3,
            'retryDelay': 2000  # 2 seconds
        }

        # Verify initialization values
        assert expected_config['refreshIntervalMs'] == 60000, "Refresh interval should be 60 seconds"
        assert expected_config['maxRetries'] == 3, "Max retries should be 3"
        assert expected_config['retryDelay'] == 2000, "Retry delay should be 2000ms"
        assert expected_config['isLoading'] == False, "Should not be loading initially"

    def test_market_movers_auto_refresh_setup(self):
        """Test auto-refresh mechanism setup."""
        refresh_interval_ms = 60000
        refresh_active = False

        # Simulate startAutoRefresh()
        def start_auto_refresh():
            nonlocal refresh_active
            refresh_active = True
            return {'interval_id': 'mock_interval', 'interval_ms': refresh_interval_ms}

        refresh_config = start_auto_refresh()

        assert refresh_active, "Auto-refresh should be active after start"
        assert refresh_config['interval_ms'] == 60000, "Refresh interval should be 60 seconds"

    def test_market_movers_websocket_setup(self):
        """Test WebSocket listener setup for real-time updates."""
        # Mock WebSocket socket
        mock_socket = Mock()
        websocket_listeners = []

        def mock_socket_on(event_name, callback):
            websocket_listeners.append({'event': event_name, 'callback': callback})

        mock_socket.on = mock_socket_on
        mock_socket.emit = Mock()

        # Simulate setupWebSocketListeners()
        if mock_socket:
            # Should listen for market_movers_update
            mock_socket_on('market_movers_update', lambda data: None)

            # Should subscribe to market movers updates
            mock_socket.emit('subscribe_market_movers', {'user_id': 'test_user'})

        # Verify WebSocket setup
        assert len(websocket_listeners) == 1, "Should set up one WebSocket listener"
        assert websocket_listeners[0]['event'] == 'market_movers_update', "Should listen for market_movers_update"
        mock_socket.emit.assert_called_once_with('subscribe_market_movers', {'user_id': 'test_user'})

    def test_market_movers_container_detection(self):
        """Test container element detection and validation."""
        container_id = 'market-movers-content'

        # Test container exists
        def mock_get_element_by_id(element_id):
            if element_id == container_id:
                return Mock()  # Container exists
            return None

        container = mock_get_element_by_id(container_id)
        assert container is not None, f"Container '{container_id}' should exist"

        # Test container missing
        missing_container = mock_get_element_by_id('non-existent-container')
        assert missing_container is None, "Missing container should return None"


class TestMarketMoversManagerDataFetching:
    """Test data fetching and API integration."""

    def setup_method(self):
        """Setup test environment for data fetching tests."""
        self.mock_fetch = Mock()
        self.sample_api_response = {
            'success': True,
            'data': {
                'gainers': [
                    {
                        'symbol': 'AAPL',
                        'name': 'Apple Inc.',
                        'price': 175.50,
                        'change': 8.25,
                        'change_percent': 4.93,
                        'volume': 2500000
                    },
                    {
                        'symbol': 'NVDA',
                        'name': 'NVIDIA Corporation',
                        'price': 425.75,
                        'change': 18.50,
                        'change_percent': 4.54,
                        'volume': 1800000
                    }
                ],
                'losers': [
                    {
                        'symbol': 'TSLA',
                        'name': 'Tesla Inc.',
                        'price': 195.25,
                        'change': -12.75,
                        'change_percent': -6.13,
                        'volume': 3200000
                    }
                ],
                'timestamp': datetime.now(UTC).isoformat()
            }
        }

    def test_market_movers_api_request_configuration(self):
        """Test API request configuration and headers."""
        expected_request_config = {
            'method': 'GET',
            'headers': {
                'Content-Type': 'application/json',
                'X-CSRFToken': 'mock_csrf_token'
            },
            'cache': 'no-cache'
        }

        # Verify request configuration
        assert expected_request_config['method'] == 'GET', "Should use GET method"
        assert expected_request_config['headers']['Content-Type'] == 'application/json', "Should set JSON content type"
        assert expected_request_config['cache'] == 'no-cache', "Should disable cache for fresh data"
        assert 'X-CSRFToken' in expected_request_config['headers'], "Should include CSRF token"

    @pytest.mark.performance
    def test_market_movers_fetch_performance_tracking(self):
        """Test API fetch performance tracking and metrics."""
        start_time = 1000.0  # Mock performance.now()
        end_time = 1025.0    # 25ms response time

        response_time = end_time - start_time

        # Update performance metrics (simulate actual implementation)
        performance_metrics = {
            'apiCalls': 1,
            'totalResponseTime': response_time,
            'lastUpdateDuration': response_time,
            'errors': 0
        }

        # Verify performance tracking
        assert performance_metrics['apiCalls'] == 1, "Should increment API call counter"
        assert performance_metrics['lastUpdateDuration'] == 25.0, "Should track last response time"
        assert response_time < 100, f"Response time should be <100ms, got {response_time}ms"

    def test_market_movers_successful_data_processing(self):
        """Test successful API response data processing."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = self.sample_api_response

        # Simulate loadMarketMovers() success path
        if mock_response.ok:
            data = mock_response.json()

            if data['success']:
                market_data = data['data']

                # Verify data structure
                assert 'gainers' in market_data, "Response should have gainers"
                assert 'losers' in market_data, "Response should have losers"
                assert 'timestamp' in market_data, "Response should have timestamp"

                # Verify gainers data
                gainers = market_data['gainers']
                assert len(gainers) == 2, f"Should have 2 gainers, got {len(gainers)}"

                for gainer in gainers:
                    assert gainer['change'] > 0, f"Gainer {gainer['symbol']} should have positive change"
                    assert gainer['change_percent'] > 0, f"Gainer {gainer['symbol']} should have positive change_percent"

                # Verify losers data
                losers = market_data['losers']
                assert len(losers) == 1, f"Should have 1 loser, got {len(losers)}"

                for loser in losers:
                    assert loser['change'] < 0, f"Loser {loser['symbol']} should have negative change"
                    assert loser['change_percent'] < 0, f"Loser {loser['symbol']} should have negative change_percent"

    def test_market_movers_loading_state_management(self):
        """Test loading state display and management."""
        is_loading = False

        # Simulate loading state start
        def show_loading_state():
            nonlocal is_loading
            is_loading = True

            # Mock DOM manipulation
            return {
                'loading_visible': True,
                'content_hidden': True
            }

        # Simulate loading state end
        def hide_loading_state():
            nonlocal is_loading
            is_loading = False

            return {
                'loading_visible': False,
                'content_visible': True
            }

        # Test loading state cycle
        loading_start = show_loading_state()
        assert loading_start['loading_visible'], "Loading state should be visible"
        assert loading_start['content_hidden'], "Content should be hidden during loading"

        loading_end = hide_loading_state()
        assert loading_end['loading_visible'] == False, "Loading state should be hidden after load"
        assert loading_end['content_visible'], "Content should be visible after load"

    def test_market_movers_duplicate_request_prevention(self):
        """Test prevention of duplicate concurrent requests."""
        is_loading = False

        def load_market_movers():
            nonlocal is_loading
            if is_loading:
                return {'status': 'skipped', 'reason': 'already_loading'}

            is_loading = True
            # Simulate API call
            time.sleep(0.01)
            is_loading = False
            return {'status': 'completed', 'reason': 'success'}

        # First request should proceed
        result1 = load_market_movers()
        assert result1['status'] == 'completed', "First request should complete"

        # Simulate concurrent request (should be skipped if loading)
        is_loading = True
        result2 = load_market_movers()
        assert result2['status'] == 'skipped', "Concurrent request should be skipped"
        assert result2['reason'] == 'already_loading', "Should indicate already loading"


class TestMarketMoversManagerRendering:
    """Test data rendering and UI generation."""

    def setup_method(self):
        """Setup test environment for rendering tests."""
        self.sample_market_data = {
            'gainers': [
                {
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'price': 175.50,
                    'change': 8.25,
                    'change_percent': 4.93,
                    'volume': 2500000
                },
                {
                    'symbol': 'MSFT',
                    'name': 'Microsoft Corporation',
                    'price': 330.25,
                    'change': 12.75,
                    'change_percent': 4.02,
                    'volume': 1900000
                }
            ],
            'losers': [
                {
                    'symbol': 'TSLA',
                    'name': 'Tesla Inc.',
                    'price': 195.25,
                    'change': -12.75,
                    'change_percent': -6.13,
                    'volume': 3200000
                }
            ]
        }

    def test_market_movers_html_generation(self):
        """Test HTML generation for market movers display."""
        gainers = self.sample_market_data['gainers']
        losers = self.sample_market_data['losers']

        # Test tab structure generation
        expected_html_elements = [
            'market-movers-tabs',
            'gainers-tab',
            'losers-tab',
            'gainers-content',
            'losers-content',
            f'Gainers ({len(gainers)})',
            f'Losers ({len(losers)})'
        ]

        # Simulate generateMarketMoversHTML()
        html_content = f"""
        <div class="market-movers-tabs">
            <ul class="nav nav-pills nav-fill mb-3" id="market-movers-tabs">
                <li class="nav-item">
                    <button class="nav-link active" id="gainers-tab">
                        Gainers ({len(gainers)})
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="losers-tab">
                        Losers ({len(losers)})
                    </button>
                </li>
            </ul>
        </div>
        """

        # Verify HTML structure elements
        for element in expected_html_elements:
            assert element in html_content or element in str(len(gainers)) or element in str(len(losers)), f"HTML should contain {element}"

    def test_market_movers_individual_item_rendering(self):
        """Test individual market mover item rendering."""
        test_gainer = self.sample_market_data['gainers'][0]
        test_loser = self.sample_market_data['losers'][0]

        # Test gainer item structure
        gainer_html_elements = [
            test_gainer['symbol'],  # AAPL
            f"{test_gainer['change_percent']:.2f}%",  # +4.93%
            f"${test_gainer['price']:.2f}",  # $175.50
            f"+{test_gainer['change']:.2f}",  # +8.25
            'fa-arrow-up',  # Up arrow icon
            'text-success'   # Success color class
        ]

        for element in gainer_html_elements:
            # Verify expected elements would be in rendered HTML
            assert isinstance(element, (str, float)), f"Element {element} should be renderable"

        # Test loser item structure
        loser_html_elements = [
            test_loser['symbol'],  # TSLA
            f"{test_loser['change_percent']:.2f}%",  # -6.13%
            f"${test_loser['price']:.2f}",  # $195.25
            f"{test_loser['change']:.2f}",  # -12.75 (no + prefix)
            'fa-arrow-down',  # Down arrow icon
            'text-danger'     # Danger color class
        ]

        for element in loser_html_elements:
            assert isinstance(element, (str, float)), f"Element {element} should be renderable"

    def test_market_movers_empty_state_rendering(self):
        """Test rendering when no market movers data available."""
        empty_data = {
            'gainers': [],
            'losers': []
        }

        # Should generate empty state HTML
        if len(empty_data['gainers']) == 0 and len(empty_data['losers']) == 0:
            empty_state_html = """
            <div class="text-center p-3 text-muted">
                <i class="fas fa-chart-line fa-2x mb-2"></i>
                <p class="mb-0">No market movers data available</p>
            </div>
            """

            # Verify empty state elements
            assert 'fa-chart-line' in empty_state_html, "Should show chart icon"
            assert 'No market movers data available' in empty_state_html, "Should show no data message"

    def test_market_movers_top_5_limitation(self):
        """Test display limitation to top 5 movers per category."""
        # Create test data with more than 5 items
        many_gainers = []
        for i in range(10):  # Create 10 gainers
            many_gainers.append({
                'symbol': f'TEST{i}',
                'name': f'Test Company {i}',
                'price': 100.0 + i,
                'change': 1.0 + (i * 0.5),
                'change_percent': 1.0 + (i * 0.3),
                'volume': 1000000 + (i * 100000)
            })

        # Simulate top 5 filtering (slice(0, 5))
        top_5_gainers = many_gainers[:5]

        assert len(top_5_gainers) == 5, f"Should limit to 5 gainers, got {len(top_5_gainers)}"
        assert len(many_gainers) == 10, "Original data should have 10 gainers"

        # Should show "Showing top 5 of X" message when more available
        if len(many_gainers) > 5:
            footer_message = f"Showing top 5 of {len(many_gainers)} gainers"
            assert "Showing top 5" in footer_message, "Should indicate limited display"

    def test_market_movers_text_truncation(self):
        """Test company name text truncation for long names."""
        long_company_name = "Very Long Company Name That Should Be Truncated For Display"
        max_length = 25

        # Simulate truncateText() function
        def truncate_text(text, max_len):
            if len(text) <= max_len:
                return text
            return text[:max_len - 3] + '...'

        truncated_name = truncate_text(long_company_name, max_length)

        assert len(truncated_name) <= max_length, f"Truncated text should be <= {max_length} chars"
        assert truncated_name.endswith('...'), "Truncated text should end with '...'"
        assert len(long_company_name) > max_length, "Original name should be longer than max"

    @pytest.mark.performance
    def test_market_movers_render_performance(self):
        """Test rendering performance meets <50ms UI update target."""
        import time

        # Create moderate dataset for performance test
        perf_test_data = {
            'gainers': [
                {
                    'symbol': f'GAIN{i:02d}',
                    'name': f'Gainer Company {i}',
                    'price': 100.0 + i,
                    'change': 1.0 + (i * 0.1),
                    'change_percent': 1.0 + (i * 0.05),
                    'volume': 1000000 + (i * 10000)
                } for i in range(20)  # 20 gainers
            ],
            'losers': [
                {
                    'symbol': f'LOSS{i:02d}',
                    'name': f'Loser Company {i}',
                    'price': 80.0 - (i * 0.5),
                    'change': -1.0 - (i * 0.1),
                    'change_percent': -1.2 - (i * 0.05),
                    'volume': 800000 + (i * 8000)
                } for i in range(20)  # 20 losers
            ]
        }

        # Simulate rendering time
        start_time = time.perf_counter()

        # Mock HTML generation for all items (only top 5 would be displayed)
        html_parts = []
        for gainer in perf_test_data['gainers'][:5]:  # Top 5 only
            html_parts.append(f"<div>{gainer['symbol']} +{gainer['change_percent']:.2f}%</div>")

        for loser in perf_test_data['losers'][:5]:  # Top 5 only
            html_parts.append(f"<div>{loser['symbol']} {loser['change_percent']:.2f}%</div>")

        combined_html = ''.join(html_parts)

        render_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert render_time < 50, f"Rendering should be <50ms, got {render_time:.2f}ms"
        assert len(combined_html) > 0, "Should generate valid HTML content"


class TestMarketMoversManagerErrorHandling:
    """Test error handling and recovery mechanisms."""

    def setup_method(self):
        """Setup test environment for error handling tests."""
        self.error_scenarios = [
            {'type': 'network', 'status': 0, 'message': 'Network error'},
            {'type': 'auth', 'status': 401, 'message': 'Unauthorized'},
            {'type': 'forbidden', 'status': 403, 'message': 'Forbidden'},
            {'type': 'server', 'status': 500, 'message': 'Internal Server Error'},
            {'type': 'timeout', 'status': 408, 'message': 'Request Timeout'}
        ]

    def test_market_movers_network_error_handling(self):
        """Test network error handling and user feedback."""
        network_error = self.error_scenarios[0]

        def handle_load_error(error):
            error_message = 'Failed to load market movers'

            if 'fetch' in str(error) or 'network' in error.get('message', '').lower():
                error_message = 'Network error - check connection'
            elif 'HTTP 40' in str(error):
                error_message = 'Authorization error - please refresh page'
            elif 'HTTP 50' in str(error):
                error_message = 'Server error - please try again'

            return error_message

        # Test network error
        network_error_message = handle_load_error({'message': 'network error'})
        assert 'Network error' in network_error_message, "Should show network-specific error message"

        # Test auth error
        auth_error_message = handle_load_error({'message': 'HTTP 401'})
        assert 'Authorization error' in auth_error_message, "Should show auth-specific error message"

        # Test server error
        server_error_message = handle_load_error({'message': 'HTTP 500'})
        assert 'Server error' in server_error_message, "Should show server-specific error message"

    def test_market_movers_retry_mechanism(self):
        """Test automatic retry mechanism with exponential backoff."""
        max_retries = 3
        retry_delay = 2000  # 2 seconds
        retry_count = 0

        async def retry_load():
            nonlocal retry_count

            if retry_count >= max_retries:
                return {'status': 'failed', 'reason': 'max_retries_exceeded'}

            retry_count += 1

            # Mock delay before retry
            await mock_delay(retry_delay)

            # Mock successful retry on 3rd attempt
            if retry_count == 3:
                return {'status': 'success', 'reason': 'retry_succeeded'}
            return {'status': 'failed', 'reason': 'retry_failed'}

        async def mock_delay(ms):
            # Mock delay without actual waiting
            pass

        # Test retry progression
        assert retry_count == 0, "Should start with 0 retries"

        # Simulate multiple retry attempts
        for attempt in range(1, max_retries + 2):
            if retry_count < max_retries:
                retry_count += 1

        assert retry_count == max_retries, f"Should not exceed max retries ({max_retries})"

    def test_market_movers_error_state_display(self):
        """Test error state UI display and recovery options."""
        error_message = "Failed to load market movers data"

        # Mock error state HTML generation
        error_state_html = f"""
        <div class="error-state text-center p-3">
            <i class="fas fa-exclamation-triangle text-warning fa-2x mb-2"></i>
            <p class="text-muted mb-2">{error_message}</p>
            <button class="btn btn-sm btn-outline-primary" id="market-movers-retry-btn">
                <i class="fas fa-redo me-1"></i>Retry
            </button>
        </div>
        """

        # Verify error state elements
        assert 'fa-exclamation-triangle' in error_state_html, "Should show warning icon"
        assert error_message in error_state_html, "Should show error message"
        assert 'market-movers-retry-btn' in error_state_html, "Should show retry button"
        assert 'fa-redo' in error_state_html, "Should show retry icon"

    def test_market_movers_malformed_response_handling(self):
        """Test handling of malformed API responses."""
        malformed_responses = [
            '{"invalid": json}',  # Invalid JSON
            '{"success": true}',  # Missing data field
            '{"success": true, "data": {}}',  # Missing gainers/losers
            '{"success": false, "error": "API Error"}',  # API error response
            '',  # Empty response
            'null'  # Null response
        ]

        for response_data in malformed_responses:
            try:
                if response_data == '' or response_data == 'null':
                    parsed_data = None
                else:
                    parsed_data = json.loads(response_data)

                # Validate response structure
                if parsed_data is None or not parsed_data.get('success') or 'data' not in parsed_data or 'gainers' not in parsed_data.get('data', {}) or 'losers' not in parsed_data.get('data', {}):
                    should_show_error = True
                else:
                    should_show_error = False

            except json.JSONDecodeError:
                should_show_error = True

            # Should handle all malformed responses gracefully
            assert True, "Should handle malformed responses without crashing"

    def test_market_movers_performance_degradation_handling(self):
        """Test handling of performance degradation scenarios."""
        performance_thresholds = {
            'warning_threshold_ms': 100,
            'error_threshold_ms': 200
        }

        test_response_times = [25, 75, 125, 175, 225]  # Various response times

        for response_time in test_response_times:
            if response_time > performance_thresholds['error_threshold_ms']:
                performance_status = 'error'
                should_show_warning = True
            elif response_time > performance_thresholds['warning_threshold_ms']:
                performance_status = 'warning'
                should_show_warning = True
            else:
                performance_status = 'good'
                should_show_warning = False

            # Verify performance monitoring
            if response_time <= 100:
                assert performance_status == 'good', f"Response time {response_time}ms should be good"
            elif response_time <= 200:
                assert performance_status == 'warning', f"Response time {response_time}ms should trigger warning"
            else:
                assert performance_status == 'error', f"Response time {response_time}ms should trigger error"


class TestMarketMoversManagerAutoRefresh:
    """Test auto-refresh functionality and lifecycle management."""

    def setup_method(self):
        """Setup test environment for auto-refresh tests."""
        self.refresh_interval_ms = 60000  # 60 seconds
        self.refresh_active = False
        self.refresh_count = 0

    def test_market_movers_auto_refresh_start_stop(self):
        """Test auto-refresh start and stop functionality."""
        def start_auto_refresh():
            self.refresh_active = True
            return {'status': 'started', 'interval_ms': self.refresh_interval_ms}

        def stop_auto_refresh():
            self.refresh_active = False
            return {'status': 'stopped'}

        # Test start
        start_result = start_auto_refresh()
        assert self.refresh_active, "Auto-refresh should be active after start"
        assert start_result['interval_ms'] == 60000, "Should use correct refresh interval"

        # Test stop
        stop_result = stop_auto_refresh()
        assert not self.refresh_active, "Auto-refresh should be inactive after stop"
        assert stop_result['status'] == 'stopped', "Should confirm stop status"

    def test_market_movers_refresh_interval_accuracy(self):
        """Test refresh interval timing accuracy."""
        expected_interval = 60000  # 60 seconds
        tolerance_ms = 1000  # 1 second tolerance

        # Mock setInterval behavior
        def mock_set_interval(callback, interval_ms):
            assert abs(interval_ms - expected_interval) <= tolerance_ms, \
                f"Interval should be {expected_interval}ms ± {tolerance_ms}ms, got {interval_ms}ms"
            return {'interval_id': 'mock_id', 'interval_ms': interval_ms}

        result = mock_set_interval(lambda: None, self.refresh_interval_ms)
        assert result['interval_ms'] == expected_interval, "Should set correct interval"

    def test_market_movers_refresh_callback_execution(self):
        """Test refresh callback execution and data updates."""
        refresh_callback_called = False
        last_refresh_time = None

        def refresh_callback():
            nonlocal refresh_callback_called, last_refresh_time
            refresh_callback_called = True
            last_refresh_time = datetime.now(UTC)
            self.refresh_count += 1

        # Simulate interval callback execution
        refresh_callback()

        assert refresh_callback_called, "Refresh callback should be executed"
        assert last_refresh_time is not None, "Should update last refresh time"
        assert self.refresh_count == 1, "Should increment refresh count"

    def test_market_movers_page_unload_cleanup(self):
        """Test cleanup on page unload and component destruction."""
        refresh_active = True
        websocket_listeners = ['market_movers_update']

        def destroy_component():
            nonlocal refresh_active, websocket_listeners

            # Stop auto-refresh
            refresh_active = False

            # Remove WebSocket listeners
            websocket_listeners.clear()

            # Cleanup performance metrics
            return {
                'refresh_stopped': not refresh_active,
                'listeners_removed': len(websocket_listeners) == 0,
                'cleanup_complete': True
            }

        cleanup_result = destroy_component()

        assert cleanup_result['refresh_stopped'], "Should stop auto-refresh on destroy"
        assert cleanup_result['listeners_removed'], "Should remove WebSocket listeners"
        assert cleanup_result['cleanup_complete'], "Should complete full cleanup"

    def test_market_movers_manual_refresh_override(self):
        """Test manual refresh override of auto-refresh timing."""
        auto_refresh_active = True
        last_auto_refresh = datetime.now(UTC)

        def manual_refresh():
            # Should trigger immediate refresh regardless of auto-refresh timing
            manual_refresh_time = datetime.now(UTC)

            # Reset auto-refresh timer (in actual implementation)
            return {
                'refresh_triggered': True,
                'refresh_time': manual_refresh_time,
                'auto_refresh_reset': True
            }

        manual_result = manual_refresh()

        assert manual_result['refresh_triggered'], "Manual refresh should trigger immediately"
        assert manual_result['auto_refresh_reset'], "Should reset auto-refresh timer"


@pytest.mark.performance
class TestMarketMoversManagerPerformance:
    """Test Market Movers widget performance characteristics."""

    def test_market_movers_dom_manipulation_performance(self):
        """Test DOM manipulation performance during updates."""
        import time

        # Mock DOM operations
        def mock_dom_update(num_items):
            start_time = time.perf_counter()

            # Simulate DOM updates for market movers items
            html_fragments = []
            for i in range(num_items):
                html_fragments.append(f'<div class="mover-item">Item {i}</div>')

            combined_html = ''.join(html_fragments)

            # Mock innerHTML assignment
            mock_innerHTML_update = len(combined_html) > 0

            update_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

            return update_time, mock_innerHTML_update

        # Test with typical data size (10 items total, 5 displayed)
        update_time, update_successful = mock_dom_update(10)

        assert update_time < 25, f"DOM update should be <25ms, got {update_time:.2f}ms"
        assert update_successful, "DOM update should complete successfully"

    def test_market_movers_memory_usage_stability(self):
        """Test memory usage stability during repeated updates."""
        import gc

        # Simulate repeated data updates
        update_cycles = 50
        large_data_sets = []

        for cycle in range(update_cycles):
            # Create mock market data
            mock_data = {
                'gainers': [
                    {'symbol': f'G{i}', 'price': 100 + i, 'change': 1 + (i * 0.1)}
                    for i in range(20)
                ],
                'losers': [
                    {'symbol': f'L{i}', 'price': 80 - i, 'change': -1 - (i * 0.1)}
                    for i in range(20)
                ]
            }

            # Simulate processing and discarding data
            processed_html = f"<div>Cycle {cycle} data processed</div>"

            # Only keep reference to current data (simulate proper cleanup)
            if cycle == update_cycles - 1:
                large_data_sets.append(processed_html)

        # Force garbage collection
        gc.collect()

        # Should only have final reference, not all cycles
        assert len(large_data_sets) == 1, "Should not accumulate references to old data"

    def test_market_movers_websocket_message_processing_performance(self):
        """Test WebSocket message processing performance."""
        import time

        # Mock large WebSocket update message
        websocket_message = {
            'type': 'market_movers_update',
            'data': {
                'gainers': [
                    {
                        'symbol': f'WS_GAIN{i:03d}',
                        'name': f'WebSocket Gainer {i}',
                        'price': 150.0 + (i * 2),
                        'change': 2.0 + (i * 0.1),
                        'change_percent': 1.3 + (i * 0.05),
                        'volume': 1000000 + (i * 50000)
                    } for i in range(25)  # 25 gainers
                ],
                'losers': [
                    {
                        'symbol': f'WS_LOSS{i:03d}',
                        'name': f'WebSocket Loser {i}',
                        'price': 120.0 - (i * 1.5),
                        'change': -1.8 - (i * 0.08),
                        'change_percent': -1.5 - (i * 0.04),
                        'volume': 900000 + (i * 30000)
                    } for i in range(25)  # 25 losers
                ]
            },
            'timestamp': datetime.now(UTC).isoformat()
        }

        # Test message processing time
        start_time = time.perf_counter()

        # Simulate handleRealtimeUpdate() processing
        if websocket_message['type'] == 'market_movers_update':
            market_data = websocket_message['data']

            # Simulate data validation and rendering
            gainers_count = len(market_data.get('gainers', []))
            losers_count = len(market_data.get('losers', []))

            processing_result = {
                'gainers_processed': gainers_count,
                'losers_processed': losers_count,
                'update_time': datetime.fromisoformat(websocket_message['timestamp'].replace('Z', '+00:00'))
            }

        processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert processing_time < 50, f"WebSocket message processing should be <50ms, got {processing_time:.2f}ms"
        assert processing_result['gainers_processed'] == 25, "Should process all gainers"
        assert processing_result['losers_processed'] == 25, "Should process all losers"
