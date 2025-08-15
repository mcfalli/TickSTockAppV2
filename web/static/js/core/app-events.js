// File-level debug flag - set to true to enable optional debug logging
const APP_EVENTS_DEBUG = false;

if (APP_EVENTS_DEBUG) console.log("JS: app-events.js loaded - initializing event processing...");

// ==========================================================================
// SPRINT 3: ENHANCED VOLUME FORMATTING UTILITIES
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

function formatTrendAgeAsTime(ageSeconds) {
    const now = new Date();
    const trendTime = new Date(now.getTime() - (ageSeconds * 1000));
    return trendTime.toLocaleTimeString('en-US', { 
        hour12: true, hour: '2-digit', minute: '2-digit' 
    });
}


// ==========================================================================
// DATA PROCESSING FUNCTIONS
// ==========================================================================

function updateHighLowEvents(data, displayedEventTracking) {
    const highListEl = document.getElementById('highs-list');
    const lowListEl = document.getElementById('lows-list');
    
    if (highListEl && data.highs && Array.isArray(data.highs) && data.highs.length > 0) {
        const fragment = document.createDocumentFragment();
        const processedKeys = new Set();
        
        for (let i = data.highs.length - 1; i >= 0; i--) {
            try {
                const h = data.highs[i];
                const eventKey = `${h.ticker}-${h.price}`;
                
                if (processedKeys.has(eventKey) || highListEl.querySelector(`[data-event-key="${eventKey}"]`)) {
                    continue;
                }
                
                processedKeys.add(eventKey);
                const item = createEventListItem(h, true);
                item.setAttribute('data-event-key', eventKey);
                item.setAttribute('data-timestamp', new Date().getTime());
                
                fragment.appendChild(item);
            } catch (e) {
                console.error(`Error creating high event for ${data.highs[i]?.ticker}:`, e);
            }
        }
        
        if (fragment.children.length > 0) {
            highListEl.insertBefore(fragment, highListEl.firstChild);
            const MAX_EVENTS = 100;
            while (highListEl.children.length > MAX_EVENTS) {
                highListEl.removeChild(highListEl.lastChild);
            }
        }
    }

    if (lowListEl && data.lows && Array.isArray(data.lows) && data.lows.length > 0) {
        const fragment = document.createDocumentFragment();
        const processedKeys = new Set();
        
        for (let i = data.lows.length - 1; i >= 0; i--) {
            try {
                const l = data.lows[i];
                const eventKey = `${l.ticker}-${l.price}`;
                
                if (processedKeys.has(eventKey) || lowListEl.querySelector(`[data-event-key="${eventKey}"]`)) {
                    continue;
                }
                
                processedKeys.add(eventKey);
                const item = createEventListItem(l, false);
                item.setAttribute('data-event-key', eventKey);
                item.setAttribute('data-timestamp', new Date().getTime());
                
                fragment.appendChild(item);
            } catch (e) {
                console.error(`Error creating low event for ${data.lows[i]?.ticker}:`, e);
            }
        }
        
        if (fragment.children.length > 0) {
            lowListEl.insertBefore(fragment, lowListEl.firstChild);
            const MAX_EVENTS = 100;
            while (lowListEl.children.length > MAX_EVENTS) {
                lowListEl.removeChild(lowListEl.lastChild);
            }
        }
    }
}

// ==========================================================================
// EVENT LIST ITEM CREATION
// ==========================================================================
function createEventListItem(entry, isHigh) {
    const div = document.createElement('div');
    div.className = isHigh ? 'high-event' : 'low-event';
    
    if (entry.market_status) {
        div.classList.add(`status-${entry.market_status.toLowerCase()}`);
    }

    const mainInfo = document.createElement('div');
    mainInfo.className = 'event-main-info';
    
    // Calculate values
    const countValue = isHigh ? 
        (entry.count_up || entry.count || '1') : 
        (entry.count_down || entry.count || '1');
    const countLevel = getCountLevel(countValue);
    
    const percentChange = entry.percent_change !== undefined ? 
        `${entry.percent_change > 0 ? '+' : ''}${entry.percent_change.toFixed(2)}%` : 'N/A';
    const percentClass = entry.percent_change > 0 ? 
        'positive-change' : (entry.percent_change < 0 ? 'negative-change' : '');
    
    const vwapDistance = entry.vwap_divergence !== undefined ?
        `${entry.vwap_divergence > 0 ? '+' : ''}${entry.vwap_divergence.toFixed(2)}%` : 'N/A';
    const vwapDistanceClass = entry.vwap_divergence > 0 ?
        'positive-change' : (entry.vwap_divergence < 0 ? 'negative-change' : '');
    
    const priceFormatted = entry.price ? formatCurrency(entry.price) : 'N/A';
    const volumeFormatted = formatVolumeForEvents(entry.volume);
    const eventTime = entry.time || formatTime(entry.timestamp);
    
    // SPRINT S50 FIX: Label construction with guaranteed content
    const labelParts = [];

    // Add trend indicator if present
    if (entry.trend_flag) {
        const trendDirection = entry.trend_flag === 'up' ? '↑' : '↓';
        const trendColor = entry.trend_flag === 'up' ? '#22c55e' : '#ef4444';
        labelParts.push(`<span style="color: ${trendColor}; font-weight: bold;">T${trendDirection}</span>`);
    }
    
    // Add surge indicator if present
    if (entry.surge_flag) {
        const surgeDirection = entry.surge_flag === 'up' ? '↑' : '↓';
        const surgeColor = entry.surge_flag === 'up' ? '#22c55e' : '#ef4444';
        labelParts.push(`<span style="color: ${surgeColor}; font-weight: bold;">S${surgeDirection}</span>`);
    }
    
    // Construct the label display with non-breaking space fallback
    let displayLabel = '';
    if (labelParts.length > 0) {
        displayLabel = `<div style="display: flex; justify-content: center; align-items: center; gap: 4px;">${labelParts.join('')}</div>`;
    } else {
        // SPRINT S50: Always provide content to prevent column collapse
        displayLabel = '<span style="display: inline-block;">&nbsp;</span>';
    }
    
    // Column order: Count | Ticker | Price | Chng% | Dist VWAP% | Volume | Label | Time
    mainInfo.innerHTML = `
        <span class="event-count count-highlight count-level-${countLevel}">${countValue}</span>
        <span class="event-ticker">${entry.ticker || 'N/A'}</span>
        <span class="event-price">${priceFormatted}</span>
        <span class="event-change ${percentClass}">${percentChange}</span>
        <span class="event-vwap-distance ${vwapDistanceClass}">${vwapDistance}</span>
        <span class="event-volume">${volumeFormatted}</span>
        <span class="event-label">${displayLabel}</span>
        <span class="event-time">${eventTime}</span>
    `;
    
    div.appendChild(mainInfo);
    return div;
}
// ==========================================================================
// TRENDING STOCKS FUNCTIONS
// ==========================================================================
// Sprint 17 Phase 2: Frontend Implementation for Trending & Surging Grids
// This code updates app-events.js to handle the new grouped JSON structure

// ==========================================================================
// TRENDING STOCKS - UPDATED FOR SPRINT 17
// ==========================================================================

function updateTrendingStocks(trendingData) {
    const uptrendList = document.getElementById('uptrend-list');
    const downtrendList = document.getElementById('downtrend-list');
    
    if (!uptrendList || !downtrendList || !trendingData) return;
    
    // Process uptrends - EXACTLY like high/low events
    if (trendingData.up && Array.isArray(trendingData.up) && trendingData.up.length > 0) {
        const fragment = document.createDocumentFragment();
        const processedKeys = new Set();
        
        // Process from end to beginning (newest first)
        for (let i = trendingData.up.length - 1; i >= 0; i--) {
            try {
                const item = trendingData.up[i];
                const eventKey = `${item.ticker}-${item.price}`;
                
                // Skip if already processed or already exists in DOM
                if (processedKeys.has(eventKey) || uptrendList.querySelector(`[data-event-key="${eventKey}"]`)) {
                    continue;
                }
                
                processedKeys.add(eventKey);
                const newElement = createTrendingItem(item, true);
                newElement.setAttribute('data-event-key', eventKey);
                newElement.setAttribute('data-timestamp', new Date().getTime());
                
                fragment.appendChild(newElement);
            } catch (e) {
                console.error(`Error creating uptrend event for ${trendingData.up[i]?.ticker}:`, e);
            }
        }
        
        // Only update DOM if we have new items
        if (fragment.children.length > 0) {
            uptrendList.insertBefore(fragment, uptrendList.firstChild);
            const MAX_EVENTS = 100;
            while (uptrendList.children.length > MAX_EVENTS) {
                uptrendList.removeChild(uptrendList.lastChild);
            }
        }
    }
    
    // Process downtrends - EXACTLY like high/low events
    if (trendingData.down && Array.isArray(trendingData.down) && trendingData.down.length > 0) {
        const fragment = document.createDocumentFragment();
        const processedKeys = new Set();
        
        // Process from end to beginning (newest first)
        for (let i = trendingData.down.length - 1; i >= 0; i--) {
            try {
                const item = trendingData.down[i];
                const eventKey = `${item.ticker}-${item.price}`;
                
                // Skip if already processed or already exists in DOM
                if (processedKeys.has(eventKey) || downtrendList.querySelector(`[data-event-key="${eventKey}"]`)) {
                    continue;
                }
                
                processedKeys.add(eventKey);
                const newElement = createTrendingItem(item, false);
                newElement.setAttribute('data-event-key', eventKey);
                newElement.setAttribute('data-timestamp', new Date().getTime());
                
                fragment.appendChild(newElement);
            } catch (e) {
                console.error(`Error creating downtrend event for ${trendingData.down[i]?.ticker}:`, e);
            }
        }
        
        // Only update DOM if we have new items
        if (fragment.children.length > 0) {
            downtrendList.insertBefore(fragment, downtrendList.firstChild);
            const MAX_EVENTS = 100;
            while (downtrendList.children.length > MAX_EVENTS) {
                downtrendList.removeChild(downtrendList.lastChild);
            }
        }
    }
    
    // Update counts
    //const uptrendCountText = document.getElementById('uptrend-count-text');
    //const downtrendCountText = document.getElementById('downtrend-count-text');
    //if (uptrendCountText) uptrendCountText.textContent = `(${uptrendList.children.length})`;
    //if (downtrendCountText) downtrendCountText.textContent = `(${downtrendList.children.length})`;
}

function createTrendingItem(entry, isUptrend) {
    const div = document.createElement('div');
    div.className = isUptrend ? 'uptrend-event' : 'downtrend-event';
    div.classList.add(isUptrend ? 'high-event' : 'low-event');
    
    const mainInfo = document.createElement('div');
    mainInfo.className = 'event-main-info';
    
    // Sprint 17: Direction column with reversal indicator
    const direction = entry.direction || (isUptrend ? 'up' : 'down');
    const directionArrow = direction === 'up' ? '↑' : '↓';
    const directionColor = direction === 'up' ? '#22c55e' : '#ef4444';
    
    let directionDisplay = `<span style="color: ${directionColor}; font-size: 16px;">${directionArrow}</span>`;
    
    // Add reversal indicator if present
    if (entry.reversal) {
        const reversalArrow = entry.reversal === 'down-now-up' ? '↓' : '↑';
        const reversalColor = entry.reversal === 'down-now-up' ? '#ef4444' : '#22c55e';
        directionDisplay += `<span style="color: ${reversalColor}; font-size: 12px; margin-left: 2px;">${reversalArrow}</span>`;
    }
    
    // Sprint 17: Count column
    const count = isUptrend ? (entry.count_up || entry.count || 0) : (entry.count_down || entry.count || 0);
    const countLevel = getCountLevel(count);
    let countDisplay = `<span class="count-highlight count-level-${countLevel}">${count}</span>`;
    
    // Price
    const priceFormatted = typeof formatCurrency === 'function' ? 
        formatCurrency(entry.price) : `$${entry.price}`;
    
    // Percentage change
    const percentChange = entry.percent_change !== undefined ? 
        `${entry.percent_change > 0 ? '+' : ''}${entry.percent_change.toFixed(2)}%` : 'N/A';
    const percentClass = entry.percent_change > 0 ? 
        'positive-change' : (entry.percent_change < 0 ? 'negative-change' : '');
    
    // VWAP divergence
    const vwapDivergence = entry.vwap_divergence !== undefined ?
        `${entry.vwap_divergence > 0 ? '+' : ''}${entry.vwap_divergence.toFixed(2)}%` : 'N/A';
    const vwapDivergenceClass = entry.vwap_divergence > 0 ?
        'positive-change' : (entry.vwap_divergence < 0 ? 'negative-change' : '');
    
    // Volume
    const volumeFormatted = formatVolumeForEvents(entry.volume);
    
    // Label
    const label = entry.trend_strength;// || entry.trend_strength || 'moderate';
    let labelClass = '';
    if (label === 'strong') {
        labelClass = 'positive-change';
    } else if (label === 'weak') {
        labelClass = 'negative-change';
    }
    
    // Time
    const eventTime = entry.time || new Date().toLocaleTimeString('en-US', { 
        hour12: true, hour: '2-digit', minute: '2-digit' 
    });
    
    // NEW COLUMN ORDER: Direction | Count | Ticker | Price | Chng% | Dist VWAP% | Volume | Label | Time
    mainInfo.innerHTML = `
        <span class="event-direction">${directionDisplay}</span>
        <span class="event-count">${countDisplay}</span>
        <span class="event-ticker">${entry.ticker}</span>
        <span class="event-price">${priceFormatted}</span>
        <span class="event-change ${percentClass}">${percentChange}</span>
        <span class="event-vwap-distance ${vwapDivergenceClass}">${vwapDivergence}</span>
        <span class="event-volume">${volumeFormatted}</span>
        <span class="event-label ${labelClass}">${label}</span>
        <span class="event-time">${eventTime}</span>
    `;
    
    div.appendChild(mainInfo);
    div.setAttribute('data-ticker', entry.ticker);
    div.setAttribute('data-timestamp', new Date().getTime());
    
    div.style.opacity = '0';
    setTimeout(() => div.style.opacity = '1', 10);
    
    return div;
}




// ==========================================================================
// SURGING STOCKS FUNCTIONS
// ==========================================================================
function updateSurgingStocks(surgingData) {
    const surgingUpList = document.getElementById('surging-up-list');
    const surgingDownList = document.getElementById('surging-down-list');
    
    if (!surgingUpList || !surgingDownList || !surgingData) return;
    
    // Handle new grouped structure
    const upSurges = surgingData.up || [];
    const downSurges = surgingData.down || [];
    
    // Process up surges - EXACTLY like high/low events
    if (upSurges.length > 0) {
        const fragment = document.createDocumentFragment();
        const processedKeys = new Set();
        
        // Process from end to beginning (newest first)
        for (let i = upSurges.length - 1; i >= 0; i--) {
            try {
                const item = upSurges[i];
                // For surging, we need a more unique key since same ticker can surge multiple times
                const eventKey = item.event_key || `${item.ticker}-${item.price}-${item.timestamp || Date.now()}`;
                
                // Skip if already processed or already exists in DOM
                if (processedKeys.has(eventKey) || surgingUpList.querySelector(`[data-event-key="${eventKey}"]`)) {
                    continue;
                }
                
                processedKeys.add(eventKey);
                const newElement = createSurgingItem(item, true);
                // Note: createSurgingItem already sets data-event-key, but ensure it matches our key
                newElement.setAttribute('data-event-key', eventKey);
                newElement.setAttribute('data-timestamp', new Date().getTime());
                
                fragment.appendChild(newElement);
            } catch (e) {
                console.error(`Error creating up surge event for ${upSurges[i]?.ticker}:`, e);
            }
        }
        
        // Only update DOM if we have new items
        if (fragment.children.length > 0) {
            surgingUpList.insertBefore(fragment, surgingUpList.firstChild);
            const MAX_EVENTS = 100;
            while (surgingUpList.children.length > MAX_EVENTS) {
                surgingUpList.removeChild(surgingUpList.lastChild);
            }
        }
    }
    
    // Process down surges - EXACTLY like high/low events
    if (downSurges.length > 0) {
        const fragment = document.createDocumentFragment();
        const processedKeys = new Set();
        
        // Process from end to beginning (newest first)
        for (let i = downSurges.length - 1; i >= 0; i--) {
            try {
                const item = downSurges[i];
                // For surging, we need a more unique key since same ticker can surge multiple times
                const eventKey = item.event_key || `${item.ticker}-${item.price}-${item.timestamp || Date.now()}`;
                
                // Skip if already processed or already exists in DOM
                if (processedKeys.has(eventKey) || surgingDownList.querySelector(`[data-event-key="${eventKey}"]`)) {
                    continue;
                }
                
                processedKeys.add(eventKey);
                const newElement = createSurgingItem(item, false);
                // Note: createSurgingItem already sets data-event-key, but ensure it matches our key
                newElement.setAttribute('data-event-key', eventKey);
                newElement.setAttribute('data-timestamp', new Date().getTime());
                
                fragment.appendChild(newElement);
            } catch (e) {
                console.error(`Error creating down surge event for ${downSurges[i]?.ticker}:`, e);
            }
        }
        
        // Only update DOM if we have new items
        if (fragment.children.length > 0) {
            surgingDownList.insertBefore(fragment, surgingDownList.firstChild);
            const MAX_EVENTS = 100;
            while (surgingDownList.children.length > MAX_EVENTS) {
                surgingDownList.removeChild(surgingDownList.lastChild);
            }
        }
    }
    
    // Update counts
    //const surgingUpCountText = document.getElementById('surging-up-count-text');
    //const surgingDownCountText = document.getElementById('surging-down-count-text');
    //if (surgingUpCountText) surgingUpCountText.textContent = `(${surgingUpList.children.length})`;
    //if (surgingDownCountText) surgingDownCountText.textContent = `(${surgingDownList.children.length})`;
}


function createSurgingItem(entry, isUp) {
    const div = document.createElement('div');
    div.className = isUp ? 'surging-up-event' : 'surging-down-event';
    div.classList.add(isUp ? 'high-event' : 'low-event');
    
    const mainInfo = document.createElement('div');
    mainInfo.className = 'event-main-info';
    
    // Sprint 17: Direction column with reversal indicator
    const direction = entry.direction || (isUp ? 'up' : 'down');
    const directionArrow = direction === 'up' ? '↑' : '↓';
    const directionColor = direction === 'up' ? '#22c55e' : '#ef4444';
    
    let directionDisplay = `<span style="color: ${directionColor}; font-size: 16px;">${directionArrow}</span>`;
    
    // Add reversal indicator if present
    if (entry.reversal) {
        const reversalArrow = entry.reversal === 'down-now-up' ? '↓' : '↑';
        const reversalColor = entry.reversal === 'down-now-up' ? '#ef4444' : '#22c55e';
        directionDisplay += `<span style="color: ${reversalColor}; font-size: 12px; margin-left: 2px;">${reversalArrow}</span>`;
    }
    
    // Sprint 17: Count column
    const count = isUp ? (entry.count_up || entry.count || 0) : (entry.count_down || entry.count || 0);
    const countLevel = getCountLevel(count);
    let countDisplay = `<span class="count-highlight count-level-${countLevel}">${count}</span>`;
    
    // Price
    const priceFormatted = typeof formatCurrency === 'function' ? 
        formatCurrency(entry.price) : `$${entry.price}`;
    
    // Percentage change
    const percentChange = entry.percent_change !== undefined ? 
        `${entry.percent_change.toFixed(2)}%` : 'N/A';
    const percentClass = entry.percent_change > 0 ? 
        'positive-change' : (entry.percent_change < 0 ? 'negative-change' : '');
    
    // VWAP divergence
    const vwapDivergence = entry.vwap_divergence !== undefined ?
        `${entry.vwap_divergence > 0 ? '+' : ''}${entry.vwap_divergence.toFixed(2)}%` : 'N/A';
    const vwapDivergenceClass = entry.vwap_divergence > 0 ?
        'positive-change' : (entry.vwap_divergence < 0 ? 'negative-change' : '');
    
    // Volume
    const volumeFormatted = formatVolumeForEvents(entry.volume);
    
    // Label
    const label = entry.label || `${Math.abs(entry.magnitude || 0).toFixed(1)}% ${entry.score || 0} ${entry.trigger_type || ''}`.trim();
    
    // Time
    const eventTime = entry.time || new Date().toLocaleTimeString('en-US', { 
        hour12: true, hour: '2-digit', minute: '2-digit' 
    });
    
    // NEW COLUMN ORDER: Direction | Count | Ticker | Price | Chng% | Dist VWAP% | Volume | Label | Time
    mainInfo.innerHTML = `
        <span class="event-direction">${directionDisplay}</span>
        <span class="event-count">${countDisplay}</span>
        <span class="event-ticker">${entry.ticker}</span>
        <span class="event-price">${priceFormatted}</span>
        <span class="event-change ${percentClass}">${percentChange}</span>
        <span class="event-vwap-distance ${vwapDivergenceClass}">${vwapDivergence}</span>
        <span class="event-volume">${volumeFormatted}</span>
        <span class="event-label">${label}</span>
        <span class="event-time">${eventTime}</span>
    `;
    
    div.appendChild(mainInfo);
    div.setAttribute('data-ticker', entry.ticker);
    div.setAttribute('data-event-key', entry.event_key || `${entry.ticker}_${entry.direction}_${entry.timestamp}`);
    div.setAttribute('data-timestamp', new Date().getTime());
    
    // MATCH HIGH/LOW ANIMATION - Simple opacity fade only
    div.style.opacity = '0';
    setTimeout(() => div.style.opacity = '1', 10);
    
    return div;
}


if (APP_EVENTS_DEBUG) console.log("JS: app-events.js cleaned - session accumulation moved to dashboard");