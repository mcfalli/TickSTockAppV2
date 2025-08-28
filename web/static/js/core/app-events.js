// ==========================================================================
// TICKSTOCK EVENTS MODULE - POST WEBCLEAN
// ==========================================================================
// VERSION: 4.0.0 - Post Webclean
// PURPOSE: Basic event utilities and placeholder functions
// ==========================================================================

// File-level debug flag - set to true to enable optional debug logging
const APP_EVENTS_DEBUG = false;

if (APP_EVENTS_DEBUG) console.log("JS: app-events.js loaded - placeholder event processing...");

// ==========================================================================
// UTILITY FUNCTIONS - PRESERVED FOR FUTURE USE
// ==========================================================================

/**
 * Format volume numbers for display in event cards
 * @param {number} volume - Raw volume number
 * @returns {string} - Formatted volume string
 */
function formatVolumeForEvents(volume) {
    if (!volume || volume === 0) return '';
    
    if (volume >= 1000000000) {
        return (volume / 1000000000).toFixed(1) + 'B';
    } else if (volume >= 1000000) {
        return (volume / 1000000).toFixed(1) + 'M';
    } else if (volume >= 1000) {
        return (volume / 1000).toFixed(1) + 'K';
    } else {
        return volume.toString();
    }
}

/**
 * Get volume class for styling based on volume level
 * @param {number} volume - Raw volume number
 * @returns {string} - CSS class name
 */
function getVolumeClass(volume) {
    if (!volume || volume === 0) return 'volume-none';
    
    if (volume >= 10000000) return 'volume-very-high'; // 10M+
    if (volume >= 1000000) return 'volume-high';       // 1M+
    if (volume >= 100000) return 'volume-medium';      // 100K+
    if (volume >= 10000) return 'volume-low';          // 10K+
    return 'volume-very-low';
}

/**
 * Get count level for styling
 * @param {number|string} count - Event count
 * @returns {string} - Level indicator
 */
function getCountLevel(count) {
    const countNum = parseInt(count, 10) || 0;
    if (countNum >= 150) return '5';
    if (countNum >= 90) return '4';
    if (countNum >= 50) return '3';
    if (countNum >= 35) return '2';
    if (countNum >= 25) return '1';
    if (countNum > 15) return '0';
    return '';
}

/**
 * Format age in seconds as time
 * @param {number} ageSeconds - Age in seconds
 * @returns {string} - Formatted time
 */
function formatTrendAgeAsTime(ageSeconds) {
    const now = new Date();
    const trendTime = new Date(now.getTime() - (ageSeconds * 1000));
    return trendTime.toLocaleTimeString('en-US', { 
        hour12: true, hour: '2-digit', minute: '2-digit' 
    });
}

/**
 * Format currency for display
 * @param {number} price - Price value
 * @returns {string} - Formatted currency
 */
function formatCurrencyForEvents(price) {
    if (typeof price !== 'number' || isNaN(price)) return '$0.00';
    return '$' + price.toFixed(2);
}

/**
 * Format percentage for display
 * @param {number} percentage - Percentage value
 * @returns {string} - Formatted percentage
 */
function formatPercentageForEvents(percentage) {
    if (typeof percentage !== 'number' || isNaN(percentage)) return '0.00%';
    const sign = percentage >= 0 ? '+' : '';
    return sign + percentage.toFixed(2) + '%';
}

// ==========================================================================
// PLACEHOLDER FUNCTIONS - FOR BACKWARD COMPATIBILITY
// ==========================================================================

/**
 * Placeholder function for high/low events - removed in webclean
 * @param {Object} data - Event data
 * @param {Object} displayedEventTracking - Event tracking object
 */
function updateHighLowEvents(data, displayedEventTracking) {
    if (APP_EVENTS_DEBUG) {
        console.log('[PLACEHOLDER] updateHighLowEvents called - components removed in webclean');
    }
    // No-op - all high/low components were removed in webclean
}

/**
 * Placeholder function for trending stocks - removed in webclean
 * @param {Object} trendingData - Trending data
 */
function updateTrendingStocks(trendingData) {
    if (APP_EVENTS_DEBUG) {
        console.log('[PLACEHOLDER] updateTrendingStocks called - components removed in webclean');
    }
    // No-op - all trending components were removed in webclean
}

/**
 * Placeholder function for surging stocks - removed in webclean
 * @param {Object} surgingData - Surging data
 */
function updateSurgingStocks(surgingData) {
    if (APP_EVENTS_DEBUG) {
        console.log('[PLACEHOLDER] updateSurgingStocks called - components removed in webclean');
    }
    // No-op - all surging components were removed in webclean
}

/**
 * Placeholder function for percentage bar updates - removed in webclean
 * @param {number} highPercentage - High percentage
 * @param {number} lowPercentage - Low percentage
 * @param {number} totalHighs - Total highs
 * @param {number} totalLows - Total lows
 */
function updateUnifiedPercentBar(highPercentage, lowPercentage, totalHighs, totalLows) {
    if (APP_EVENTS_DEBUG) {
        console.log('[PLACEHOLDER] updateUnifiedPercentBar called - component removed in webclean');
    }
    // No-op - percentage bar component was removed in webclean
}

// ==========================================================================
// FUTURE EVENT SYSTEM PLACEHOLDER
// ==========================================================================

/**
 * Create a generic event item for future implementation
 * @param {Object} eventData - Event data object
 * @param {string} eventType - Type of event (high, low, trend, surge, etc.)
 * @returns {HTMLElement} - Event element
 */
function createGenericEventItem(eventData, eventType) {
    const item = document.createElement('div');
    item.className = `event-item event-${eventType}`;
    
    // Basic event structure for future use
    item.innerHTML = `
        <div class="event-header">
            <span class="event-ticker">${eventData.ticker || 'N/A'}</span>
            <span class="event-type">${eventType.toUpperCase()}</span>
        </div>
        <div class="event-details">
            <span class="event-price">${formatCurrencyForEvents(eventData.price)}</span>
            <span class="event-change">${formatPercentageForEvents(eventData.change_percent)}</span>
        </div>
        <div class="event-meta">
            <span class="event-volume">${formatVolumeForEvents(eventData.volume)}</span>
            <span class="event-time">${new Date().toLocaleTimeString('en-US', { hour12: false })}</span>
        </div>
    `;
    
    return item;
}

/**
 * Add event to placeholder container (for future implementation)
 * @param {Object} eventData - Event data
 * @param {string} eventType - Event type
 */
function addEventToPlaceholder(eventData, eventType) {
    const placeholder = document.querySelector('.placeholder-content');
    if (placeholder && APP_EVENTS_DEBUG) {
        console.log(`[PLACEHOLDER] Would add ${eventType} event for ${eventData.ticker}`);
        
        // Could add visual indication of events in placeholder
        const eventIndicator = document.createElement('div');
        eventIndicator.className = 'event-indicator';
        eventIndicator.textContent = `${eventType.toUpperCase()}: ${eventData.ticker}`;
        eventIndicator.style.cssText = `
            font-size: 0.8rem;
            color: var(--color-text-muted);
            margin: 2px 0;
            opacity: 0.7;
        `;
        
        placeholder.appendChild(eventIndicator);
        
        // Remove old indicators (keep only last 5)
        const indicators = placeholder.querySelectorAll('.event-indicator');
        while (indicators.length > 5) {
            indicators[0].remove();
        }
    }
}

// ==========================================================================
// DEBUG UTILITIES
// ==========================================================================

/**
 * Debug function for testing event utilities
 */
window.debugEventUtilities = function() {
    console.log('=== EVENT UTILITIES DEBUG ===');
    console.log('formatVolumeForEvents(1500000):', formatVolumeForEvents(1500000));
    console.log('getVolumeClass(5000000):', getVolumeClass(5000000));
    console.log('getCountLevel(75):', getCountLevel(75));
    console.log('formatCurrencyForEvents(123.45):', formatCurrencyForEvents(123.45));
    console.log('formatPercentageForEvents(2.34):', formatPercentageForEvents(2.34));
    
    // Test placeholder functions
    console.log('Testing placeholder functions (should show no-op messages):');
    updateHighLowEvents({}, {});
    updateTrendingStocks({});
    updateSurgingStocks({});
};

if (APP_EVENTS_DEBUG) {
    console.log("app-events.js initialization complete (Post-Webclean)");
}