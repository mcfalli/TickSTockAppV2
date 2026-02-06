/**
 * Sprint 64: Threshold Bar Renderer Module
 *
 * Provides ThresholdBarRenderer class for rendering diverging threshold bars
 * from TickStockAppV2 /api/threshold-bars endpoint.
 *
 * Features:
 * - API data fetching with error handling
 * - DOM-based rendering (no external libraries)
 * - Percentage-based segment widths
 * - Flexbox layout for divergence
 * - Horizontal and vertical orientations
 * - Loading and error states
 * - CSRF token support
 *
 * Usage:
 *   const renderer = new ThresholdBarRenderer();
 *   await renderer.render('bar-container-id', {
 *       dataSource: 'sp500',
 *       barType: 'DivergingThresholdBar',
 *       timeframe: 'daily',
 *       threshold: 0.10
 *   });
 */

class ThresholdBarRenderer {
    /**
     * Initialize the threshold bar renderer.
     *
     * @param {Object} options - Configuration options
     * @param {string} options.apiEndpoint - API endpoint URL (default: '/api/threshold-bars')
     * @param {string} options.csrfToken - CSRF token for API requests
     */
    constructor(options = {}) {
        this.apiEndpoint = options.apiEndpoint || '/api/threshold-bars';
        this.csrfToken = options.csrfToken || this._getCSRFToken();
    }

    /**
     * Render a threshold bar in the specified container.
     *
     * @param {string} containerId - DOM element ID for the bar container
     * @param {Object} config - Bar configuration
     * @param {string} config.dataSource - Data source (e.g., 'sp500', 'SPY', 'sp500:nasdaq100')
     * @param {string} config.barType - 'DivergingThresholdBar' or 'SimpleDivergingBar'
     * @param {string} config.timeframe - '1min', 'hourly', 'daily', 'weekly', 'monthly'
     * @param {number} config.threshold - Threshold value (0.0-1.0, default: 0.10)
     * @param {number} config.periodDays - Period in days (default: 1)
     * @param {string} config.orientation - 'horizontal' or 'vertical' (default: 'horizontal')
     * @param {string} config.label - Optional label text
     * @param {boolean} config.showMetadata - Show metadata row (default: false)
     *
     * @returns {Promise<void>}
     * @throws {Error} If container not found or API request fails
     */
    async render(containerId, config) {
        const container = document.getElementById(containerId);

        if (!container) {
            throw new Error(`Container element not found: ${containerId}`);
        }

        // Clear container
        container.innerHTML = '';
        container.className = 'threshold-bar-container';

        // Add label if provided
        if (config.label) {
            const labelEl = document.createElement('div');
            labelEl.className = 'threshold-bar-label';
            labelEl.textContent = config.label;
            container.appendChild(labelEl);
        }

        // Create bar wrapper
        const wrapper = document.createElement('div');
        wrapper.className = `threshold-bar-wrapper ${config.orientation || 'horizontal'} loading`;
        container.appendChild(wrapper);

        try {
            // Fetch threshold data from API
            const data = await this.fetchThresholdData(
                config.dataSource,
                config.barType || 'DivergingThresholdBar',
                config.timeframe || 'daily',
                config.threshold || 0.10,
                config.periodDays || 1
            );

            // Remove loading state
            wrapper.classList.remove('loading');

            // Render segments
            this._renderSegments(wrapper, data, config.orientation || 'horizontal');

            // Add metadata if requested
            if (config.showMetadata) {
                this._renderMetadata(container, data.metadata);
            }
        } catch (error) {
            // Remove loading state
            wrapper.classList.remove('loading');

            // Show error state
            wrapper.classList.add('error');
            const errorMsg = document.createElement('div');
            errorMsg.className = 'threshold-bar-error-message';
            errorMsg.textContent = `Error: ${error.message}`;
            wrapper.appendChild(errorMsg);

            console.error('Threshold bar rendering error:', error);
        }
    }

    /**
     * Fetch threshold bar data from API.
     *
     * @param {string} dataSource - Data source identifier
     * @param {string} barType - Bar type
     * @param {string} timeframe - Timeframe
     * @param {number} threshold - Threshold value
     * @param {number} periodDays - Period in days
     *
     * @returns {Promise<Object>} API response data
     * @throws {Error} If API request fails
     */
    async fetchThresholdData(dataSource, barType, timeframe, threshold, periodDays) {
        const params = new URLSearchParams({
            data_source: dataSource,
            bar_type: barType,
            timeframe: timeframe,
            threshold: threshold.toString(),
            period_days: periodDays.toString(),
        });

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
     * Render bar segments using flexbox layout.
     *
     * @private
     * @param {HTMLElement} wrapper - Bar wrapper element
     * @param {Object} data - API response data
     * @param {string} orientation - 'horizontal' or 'vertical'
     */
    _renderSegments(wrapper, data, orientation) {
        const { segments } = data;

        // Create segments container
        const segmentsContainer = document.createElement('div');
        segmentsContainer.className = 'threshold-bar-segments';
        wrapper.appendChild(segmentsContainer);

        // Create baseline
        const baseline = document.createElement('div');
        baseline.className = 'threshold-bar-baseline';
        wrapper.appendChild(baseline);

        // Determine segment order based on bar type
        let segmentOrder;
        if (Object.keys(segments).length === 4) {
            // DivergingThresholdBar: significant_decline, minor_decline, minor_advance, significant_advance
            segmentOrder = [
                'significant_decline',
                'minor_decline',
                'minor_advance',
                'significant_advance',
            ];
        } else {
            // SimpleDivergingBar: decline, advance
            segmentOrder = ['decline', 'advance'];
        }

        // Render each segment
        segmentOrder.forEach((segmentName) => {
            const percentage = segments[segmentName] || 0;

            if (percentage > 0) {
                const segmentEl = document.createElement('div');
                segmentEl.className = `threshold-bar-segment ${segmentName}`;
                segmentEl.setAttribute('data-width', Math.round(percentage));
                segmentEl.setAttribute(
                    'data-tooltip',
                    `${this._formatSegmentLabel(segmentName)}: ${percentage.toFixed(1)}%`
                );

                // Set flexbox width (percentage of 50% for each half)
                // Scale percentage to half-bar width (0-50% becomes 0-100% of half)
                const scaledWidth = (percentage / 50) * 100;
                if (orientation === 'horizontal') {
                    segmentEl.style.width = `${scaledWidth}%`;
                    segmentEl.style.height = '100%';
                } else {
                    segmentEl.style.height = `${scaledWidth}%`;
                    segmentEl.style.width = '100%';
                }

                // Add label text if segment is wide enough
                if (percentage >= 3) {
                    const label = document.createElement('span');
                    label.className = 'threshold-bar-segment-label';
                    label.textContent = `${percentage.toFixed(1)}%`;
                    segmentEl.appendChild(label);
                }

                segmentsContainer.appendChild(segmentEl);
            }
        });
    }

    /**
     * Render metadata row below the bar.
     *
     * @private
     * @param {HTMLElement} container - Container element
     * @param {Object} metadata - Metadata from API response
     */
    _renderMetadata(container, metadata) {
        const metadataEl = document.createElement('div');
        metadataEl.className = 'threshold-bar-metadata';

        // Data source
        const dataSourceItem = document.createElement('div');
        dataSourceItem.className = 'threshold-bar-metadata-item';
        dataSourceItem.innerHTML = `
            <span class="threshold-bar-metadata-label">Source:</span>
            <span class="threshold-bar-metadata-value">${metadata.data_source}</span>
        `;
        metadataEl.appendChild(dataSourceItem);

        // Symbol count
        const symbolCountItem = document.createElement('div');
        symbolCountItem.className = 'threshold-bar-metadata-item';
        symbolCountItem.innerHTML = `
            <span class="threshold-bar-metadata-label">Symbols:</span>
            <span class="threshold-bar-metadata-value">${metadata.symbol_count}</span>
        `;
        metadataEl.appendChild(symbolCountItem);

        // Timeframe
        const timeframeItem = document.createElement('div');
        timeframeItem.className = 'threshold-bar-metadata-item';
        timeframeItem.innerHTML = `
            <span class="threshold-bar-metadata-label">Timeframe:</span>
            <span class="threshold-bar-metadata-value">${metadata.timeframe}</span>
        `;
        metadataEl.appendChild(timeframeItem);

        container.appendChild(metadataEl);
    }

    /**
     * Format segment name for display.
     *
     * @private
     * @param {string} segmentName - Raw segment name (e.g., 'significant_decline')
     * @returns {string} Formatted name (e.g., 'Significant Decline')
     */
    _formatSegmentLabel(segmentName) {
        return segmentName
            .split('_')
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
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
    module.exports = ThresholdBarRenderer;
}

// Make available globally for direct <script> tag usage
if (typeof window !== 'undefined') {
    window.ThresholdBarRenderer = ThresholdBarRenderer;
}
