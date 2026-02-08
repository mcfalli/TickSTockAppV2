/**
 * Sprint 66: Breadth Metrics Renderer Module
 *
 * Provides BreadthMetricsRenderer class for rendering market breadth metrics
 * as horizontal bar charts from TickStockAppV2 /api/breadth-metrics endpoint.
 *
 * Features:
 * - API data fetching with error handling
 * - DOM-based rendering (no external libraries)
 * - Percentage-based bar widths
 * - Flexbox horizontal layout
 * - Loading and error states
 * - Auto-refresh every 60 seconds
 * - CSRF token support
 * - Configurable universe, title, controls
 *
 * Usage:
 *   const renderer = new BreadthMetricsRenderer();
 *   await renderer.render('container-id', {
 *       universe: 'SPY',
 *       title: 'S&P 500 Breadth',
 *       showControls: true
 *   });
 */

class BreadthMetricsRenderer {
    /**
     * Initialize the breadth metrics renderer.
     *
     * @param {Object} options - Configuration options
     * @param {string} options.apiEndpoint - API endpoint URL (default: '/api/breadth-metrics')
     * @param {string} options.csrfToken - CSRF token for API requests
     */
    constructor(options = {}) {
        this.apiEndpoint = options.apiEndpoint || '/api/breadth-metrics';
        this.csrfToken = options.csrfToken || this._getCSRFToken();
        this.refreshInterval = 60000; // 60 seconds
        this.refreshTimer = null;
    }

    /**
     * Render breadth metrics in the specified container.
     *
     * @param {string} containerId - DOM element ID for the container
     * @param {Object} config - Rendering configuration
     * @param {string} config.universe - Universe key (e.g., 'SPY', 'QQQ', 'dow30')
     * @param {string} config.title - Display title (optional)
     * @param {boolean} config.showControls - Show/hide controls (default: true)
     *
     * @returns {Promise<void>}
     */
    async render(containerId, config = {}) {
        const container = document.getElementById(containerId);

        if (!container) {
            console.error(`Container element not found: ${containerId}`);
            return;
        }

        const universe = config.universe || 'SPY';
        const title = config.title || 'Market Breadth';
        const showControls = config.showControls !== false;

        // Clear container and show loading state
        container.innerHTML = '';
        container.className = 'breadth-metrics-container loading';

        try {
            // Fetch data from API
            const data = await this.fetchData(universe);

            // Remove loading state
            container.classList.remove('loading');

            // Render 12 metric rows
            const html = this.createMetricsHTML(data);
            container.innerHTML = html;

            // Setup auto-refresh (60s for intraday data)
            this.setupAutoRefresh(containerId, config);

        } catch (error) {
            // Remove loading state
            container.classList.remove('loading');

            // Show error state
            container.classList.add('error');
            container.innerHTML = `
                <div class="breadth-metrics-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Error loading breadth metrics: ${error.message}</p>
                </div>
            `;

            console.error('Breadth metrics rendering error:', error);
        }
    }

    /**
     * Fetch breadth metrics data from API.
     *
     * @param {string} universe - Universe key
     * @returns {Promise<Object>} API response data
     * @throws {Error} If API request fails
     */
    async fetchData(universe) {
        const params = new URLSearchParams({ universe });
        const url = `${this.apiEndpoint}?${params}`;

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
            },
            credentials: 'same-origin',
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `API error: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Create HTML for all 12 metric rows.
     *
     * @param {Object} data - API response data
     * @returns {string} HTML string
     */
    createMetricsHTML(data) {
        const metrics = data.metrics;
        const metricLabels = {
            'day_change': 'Day Chg',
            'open_change': 'Open Chg',
            'week': 'Week',
            'month': 'Month',
            'quarter': 'Quarter',
            'half_year': 'Half Year',
            'year': 'Year',
            'price_to_ema10': 'Price/EMA10',
            'price_to_ema20': 'Price/EMA20',
            'price_to_sma50': 'Price/SMA50',
            'price_to_sma200': 'Price/SMA200',
        };

        let html = '';

        for (const [key, label] of Object.entries(metricLabels)) {
            const metric = metrics[key];
            if (!metric) continue;

            const barHTML = this.createHorizontalBar(metric, label);
            html += barHTML;
        }

        return html;
    }

    /**
     * Create horizontal bar chart for a single metric.
     *
     * @param {Object} metric - Metric data (up, down, unchanged, pct_up)
     * @param {string} label - Metric label
     * @returns {string} HTML string for metric row
     */
    createHorizontalBar(metric, label) {
        const { up, down, pct_up } = metric;
        const pct_down = 100 - pct_up;

        // Round percentages to 2 decimal places to avoid floating point display errors
        const upWidth = parseFloat(pct_up.toFixed(2));
        const downWidth = parseFloat(pct_down.toFixed(2));

        // Check if no data available (both up and down are 0)
        const hasData = up > 0 || down > 0;
        const countsDisplay = hasData
            ? `<span class="count-up">${up}</span> / <span class="count-down">${down}</span>`
            : `<span class="text-muted">Insufficient Data</span>`;

        // Use grey striped bar for insufficient data, otherwise show red/green bars
        const barContent = hasData
            ? `<div class="metric-bar-up" style="width: ${upWidth}%"></div>
               <div class="metric-bar-down" style="width: ${downWidth}%"></div>`
            : `<div class="metric-bar-insufficient"></div>`;

        return `
            <div class="metric-row">
                <div class="metric-label">${label}</div>
                <div class="metric-bar-container">
                    ${barContent}
                </div>
                <div class="metric-counts">
                    ${countsDisplay}
                </div>
            </div>
        `;
    }

    /**
     * Setup auto-refresh timer for intraday data updates.
     *
     * @param {string} containerId - Container element ID
     * @param {Object} config - Rendering configuration
     */
    setupAutoRefresh(containerId, config) {
        // Clear existing timer
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        // Setup new timer (60s interval)
        this.refreshTimer = setInterval(() => {
            this.render(containerId, config);
        }, this.refreshInterval);
    }

    /**
     * Cleanup refresh timer (call when component unmounts).
     */
    cleanup() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * Get CSRF token from meta tag or cookie.
     *
     * @private
     * @returns {string} CSRF token
     */
    _getCSRFToken() {
        // Try meta tag first
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }

        // Fall back to cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return value;
            }
        }

        return '';
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BreadthMetricsRenderer;
}

// Make available globally for direct <script> tag usage
if (typeof window !== 'undefined') {
    window.BreadthMetricsRenderer = BreadthMetricsRenderer;
}
