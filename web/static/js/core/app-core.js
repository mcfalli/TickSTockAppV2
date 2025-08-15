// ==========================================================================
// TICKSTOCK CORE APPLICATION MODULE - CLEANED & OPTIMIZED
// ==========================================================================
// VERSION: 3.0.0 - Sprint S54
// PURPOSE: Core application logic, socket handling, and UI management
// ==========================================================================

// File-level debug flags
const APP_CORE_DEBUG = false;
const ANALYTICS_DEBUG = false;
const PERFORMANCE_DEBUG = false;
//console.log("JS: app-core.js loaded - initializing...");

// ==========================================================================
// GLOBAL VARIABLES
// ==========================================================================

// Connection & Status
let lastUpdateTime = null;
let isConnected = false;
let apiHealth = 'initializing';
let dataSource = 'unknown';
let lastMarketStatus = null;
let disconnectionCount = 0;
let lastConnectionLossTime = null;
let isOverlayHidden = false;

// Activity Dashboard
window.velocityDashboard = null;

// Data Tracking
let totalHighs = 0;
let totalLows = 0;

// Event tracking
const displayedEventTracking = {
    highEventKeys: new Set(),
    lowEventKeys: new Set(),
    surgeEventKeys: new Set()
};

// ==========================================================================
// PRODUCTION LOGGING UTILITY
// ==========================================================================
const ProductionLogger = {
    info: (component, message, data = null) => {
        if (APP_CORE_DEBUG) {
            const logData = data ? (typeof data === 'object' ? { 
                summary: Object.keys(data).length > 5 ? `${Object.keys(data).length} properties` : data 
            } : data) : '';
            console.log(`[${component}] ${message}`, logData);
        }
    },
    
    error: (component, message, error) => {
        console.error(`[${component}] ERROR: ${message}`, error);
    },
    
    warn: (component, message, data = null) => {
        console.warn(`[${component}] WARNING: ${message}`, data);
    },
    
    performance: (component, operation, duration) => {
        if (PERFORMANCE_DEBUG && duration > 10) {
            console.log(`[PERF] ${component}.${operation}: ${duration}ms`);
        }
    },
    
    critical: (component, message, data = null) => {
        console.log(`[CRITICAL] ${component}: ${message}`, data);
    }
};

// ==========================================================================
// UTILITY FUNCTIONS
// ==========================================================================

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function getMarketStatusText(status) {
    switch (status) {
        case 'PRE': return 'Pre-Market';
        case 'REGULAR': return 'Market Open';
        case 'AFTER': return 'After-Hours';
        case 'CLOSED': return 'Market Closed';
        default: return 'Unknown';
    }
}

function formatCurrency(price) {
    if (typeof price !== 'number' || isNaN(price)) return 'N/A';
    return '$' + price.toFixed(2);
}

function abbreviateNumber(num) {
    if (!num || isNaN(num)) return 'N/A';
    
    const absNum = Math.abs(num);
    
    if (absNum >= 1000000000) {
        return (num / 1000000000).toFixed(1) + 'B';
    } else if (absNum >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (absNum >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    } else {
        return num.toString();
    }
}

function showStatusNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'status-notification';
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 500);
    }, 5000);
}

function updateConnectionStatus(connected) {
    const connectionIndicator = document.getElementById('connection-status');
    if (!connectionIndicator) return;
    
    const connectionText = connectionIndicator.querySelector('.connection-text');
    
    if (connected) {
        connectionIndicator.classList.add('connected');
        connectionIndicator.classList.remove('disconnected');
        if (connectionText) connectionText.textContent = 'Connected';
    } else {
        connectionIndicator.classList.remove('connected');
        connectionIndicator.classList.add('disconnected');
        if (connectionText) connectionText.textContent = 'Disconnected';
    }
}

// ==========================================================================
// SCROLLBAR DETECTION - SIMPLIFIED
// ==========================================================================

// SPRINT S54: Simple, performant scrollbar detection
function checkScrollbars() {
    // Only add class for browsers without scrollbar-gutter support
    if (!CSS.supports('scrollbar-gutter', 'stable')) {
        document.querySelectorAll('.events-list').forEach(list => {
            const hasScrollbar = list.scrollHeight > list.clientHeight;
            const section = list.closest('section');
            if (section) {
                const headerRow = section.querySelector('.events-header-row');
                if (headerRow) {
                    if (hasScrollbar) {
                        headerRow.style.paddingRight = '29px'; // 12px + 17px scrollbar
                    } else {
                        headerRow.style.paddingRight = '12px';
                    }
                }
            }
        });
    }
}

// Debounced version for performance
const debouncedScrollbarCheck = debounce(checkScrollbars, 100);

// ==========================================================================
// SOCKET.IO CONNECTION & HANDLERS
// ==========================================================================
const socket = io('http://localhost:5000', {
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000,
    timeout: 20000
});

// Store socket globally for other modules
window.socket = socket;

socket.on('connect', () => {
    ProductionLogger.critical("SOCKET", "Connected successfully", { id: socket.id });
    isConnected = true;
    updateConnectionStatus(true);
    updateLoadingOverlay();
});

socket.on('connect_error', (error) => {
    ProductionLogger.error("SOCKET", "Connection failed", error.message);
    isConnected = false;
    updateConnectionStatus(false);
    updateLoadingOverlay();
});

socket.on('disconnect', (reason) => {
    ProductionLogger.warn("SOCKET", "Disconnected", { reason });
    isConnected = false;
    disconnectionCount++;
    lastConnectionLossTime = Date.now();
    updateConnectionStatus(false);
    updateLoadingOverlay();
});

socket.on('status_update', (data) => {
    try {
        const parsedData = typeof data === 'string' ? JSON.parse(data) : data;
        isConnected = parsedData.connected;
        apiHealth = parsedData.status;
        dataSource = parsedData.provider || 'Synthetic';
        
        updateConnectionStatus(isConnected);
        
        const marketStatus = document.getElementById('market-status');
        if (marketStatus) {
            marketStatus.textContent = getMarketStatusText(parsedData.market_status || 'UNKNOWN');
            marketStatus.className = `status-badge status-${(parsedData.market_status || 'unknown').toLowerCase()}`;
        }
        
        updateLoadingOverlay();
        
    } catch (error) {
        ProductionLogger.error("STATUS", "Error processing status_update", error);
    }
});

socket.on('session_reset', (data) => {
    // Clear tracking
    displayedEventTracking.highEventKeys.clear();
    displayedEventTracking.lowEventKeys.clear();
    displayedEventTracking.surgeEventKeys.clear();
    
    // Clear lists
    ['highs-list', 'lows-list', 'surging-up-list', 'surging-down-list'].forEach(id => {
        const list = document.getElementById(id);
        if (list) list.innerHTML = '';
    });
    
    // Update market status
    const marketStatus = document.getElementById('market-status');
    if (marketStatus && data.new_session) {
        marketStatus.textContent = getMarketStatusText(data.new_session);
        marketStatus.className = `status-badge status-${data.new_session.toLowerCase()}`;
    }
    
    ProductionLogger.critical("SESSION", "Reset to " + getMarketStatusText(data.new_session));
    showStatusNotification(`Market session changed to ${getMarketStatusText(data.new_session)}`);
});

// MAIN STOCK DATA HANDLER
socket.on('stock_data', (data) => {
    try {
        // Parse if string
        if (typeof data === 'string') data = JSON.parse(data);
        if (!data || typeof data !== 'object') throw new Error('Invalid stock_data payload');
        
        // Update timestamp
        lastUpdateTime = Date.now();
        
        // Process velocity dashboard data
        if (data.activity) {
            processVelocityData(data);
        }
        
        // Calculate percentages
        const currentHighs = (data.activity?.total_highs) || 0;
        const currentLows = (data.activity?.total_lows) || 0;
        const totalEvents = currentHighs + currentLows;
        const highPercentage = totalEvents > 0 ? (currentHighs / totalEvents * 100) : 50;
        const lowPercentage = totalEvents > 0 ? (currentLows / totalEvents * 100) : 50;

        // Update UI components
        updateUnifiedPercentBarWithData(data);
        updateHeaderInfo(highPercentage, lowPercentage, currentHighs, currentLows);

        // Process events (functions from app-events.js)
        if (typeof updateHighLowEvents === 'function') {
            updateHighLowEvents(data, displayedEventTracking);
        }

        if (data.trending && typeof updateTrendingStocks === 'function') {
            updateTrendingStocks(data.trending);
        }
        
        if (data.surging && typeof updateSurgingStocks === 'function') {
            updateSurgingStocks(data.surging);
        }

        updateStatusDisplay(data);
        
        // Check scrollbars occasionally
        debouncedScrollbarCheck();
        
    } catch (error) {
        ProductionLogger.error("STOCK_DATA", "Error processing data", error);
    }
});

// ==========================================================================
// UI UPDATE FUNCTIONS
// ==========================================================================

function updateLoadingOverlay() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (!loadingOverlay || isOverlayHidden) return;
    
    if (isConnected && (apiHealth === 'healthy' || apiHealth === 'connected')) {
        loadingOverlay.classList.add('hidden');
        loadingOverlay.style.display = 'none';
        isOverlayHidden = true;
        ProductionLogger.critical("UI", "Loading overlay hidden - connection ready");
    } else {
        loadingOverlay.classList.remove('hidden');
        loadingOverlay.style.display = 'flex';
    }
}

function updateHeaderInfo(highPercentage, lowPercentage, totalHighs, totalLows) {
    const highCountEl = document.getElementById('high-percent-text');
    const lowCountEl = document.getElementById('low-percent-text');
    
    if (highCountEl) {
        highCountEl.textContent = `(${highPercentage.toFixed(1)}%)`;
    }
    
    if (lowCountEl) {
        lowCountEl.textContent = `(${lowPercentage.toFixed(1)}%)`;
    }
}

function updateStatusDisplay(data) {
    try {
        const headerStatus = document.querySelector('.header-right .filter-placeholder');
        if (headerStatus) {
            const coreCount = data.core_analytics?.current_state?.universe_size || 2800;
            headerStatus.textContent = `Core: ${coreCount.toLocaleString()} stocks`;
        }
    } catch (error) {
        ProductionLogger.error("UI", "Error updating status display", error);
    }
}

function updateUnifiedPercentBarWithData(data) {
    try {
        let totalHighs = 0;
        let totalLows = 0;
        
        // Extract from data sources
        if (data.activity) {
            totalHighs = data.activity.total_highs || 0;
            totalLows = data.activity.total_lows || 0;
        } else if (data.session_accumulation) {
            totalHighs = data.session_accumulation.session_total_highs || 0;
            totalLows = data.session_accumulation.session_total_lows || 0;
        }
        
        // Calculate percentages
        const totalEvents = totalHighs + totalLows;
        const highPercentage = totalEvents > 0 ? (totalHighs / totalEvents * 100) : 50;
        const lowPercentage = totalEvents > 0 ? (totalLows / totalEvents * 100) : 50;
        
        // Update percentage bar
        if (typeof updateUnifiedPercentBar === 'function') {
            updateUnifiedPercentBar(highPercentage, lowPercentage, totalHighs, totalLows);
        }
        
    } catch (error) {
        ProductionLogger.error("UI", "Error updating unified percent bar", error);
    }
}

// ==========================================================================
// ACTIVITY VELOCITY DASHBOARD
// ==========================================================================

function initializeVelocityDashboard() {
    const container = document.getElementById('core-gauge-container');
    if (container) {
        window.velocityDashboard = new ActivityVelocityDashboard('core-gauge-container');
    } else {
        console.error("Core gauge container not found");
    }
}

function processVelocityData(data) {
    try {
        if (!data.activity) {
            console.warn("No activity data in payload");
            return;
        }
        
        if (window.velocityDashboard) {
            window.velocityDashboard.updateData(data);
        }
        
        if (APP_CORE_DEBUG) {
            console.log("Activity Update:", {
                tickRate: data.activity.activity_ratio?.current_rate || 0,
                level: data.activity.activity_level,
                highs: data.activity.total_highs,
                lows: data.activity.total_lows
            });
        }
        
    } catch (error) {
        console.error("Error processing velocity data:", error);
    }
}

// ==========================================================================
// SESSION MODAL STYLES
// ==========================================================================

function injectSessionModalStyles() {
    const style = document.createElement('style');
    style.textContent = `
        #session-warning-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        #session-warning-modal .modal-content {
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            max-width: 400px;
        }
        #session-warning-modal p {
            margin: 0 0 20px;
            font-size: 16px;
        }
        #session-warning-modal button {
            padding: 10px 20px;
            margin: 0 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        #stay-logged-in {
            background: #4caf50;
            color: #fff;
        }
        #log-out {
            background: #f44336;
            color: #fff;
        }
    `;
    document.head.appendChild(style);
}

// ==========================================================================
// DOM READY & INITIALIZATION
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    updateLoadingOverlay();
    ProductionLogger.critical("APP", "DOM ready - initializing core module");
    
    // User menu dropdown
    const userMenu = document.querySelector('.user-menu');
    const userButton = document.querySelector('.user-settings-btn');
    
    if (userMenu && userButton) {
        userButton.addEventListener('click', function(e) {
            e.stopPropagation();
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            this.setAttribute('aria-expanded', !isExpanded);
            userMenu.classList.toggle('active');
        });
        
        document.addEventListener('click', function(e) {
            if (!userMenu.contains(e.target)) {
                userButton.setAttribute('aria-expanded', 'false');
                userMenu.classList.remove('active');
            }
        });
        
        userButton.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    }
   
    // SPRINT S54: Simple scrollbar check
    setTimeout(() => {
        checkScrollbars();
        
        // Monitor for changes with simple observer
        const observer = new MutationObserver(debouncedScrollbarCheck);
        
        ['highs-list', 'lows-list', 'uptrend-list', 'downtrend-list', 'surging-up-list', 'surging-down-list'].forEach(id => {
            const list = document.getElementById(id);
            if (list) {
                observer.observe(list, { 
                    childList: true, 
                    subtree: false,
                    attributes: false
                });
            }
        });
    }, 500);

    // Data freshness indicator
    setInterval(() => {
        const freshnessIndicator = document.getElementById('data-freshness');
        if (!freshnessIndicator) return;
        
        if (lastUpdateTime) {
            const diffSeconds = Math.floor((Date.now() - lastUpdateTime) / 1000);
            if (diffSeconds < 5) {
                freshnessIndicator.textContent = "Live";
                freshnessIndicator.className = "freshness-badge fresh";
            } else if (diffSeconds < 30) {
                freshnessIndicator.textContent = `${diffSeconds}s ago`;
                freshnessIndicator.className = "freshness-badge recent";
            } else {
                const minutes = Math.floor(diffSeconds / 60);
                const seconds = diffSeconds % 60;
                freshnessIndicator.textContent = `${minutes}m ${seconds}s ago`;
                freshnessIndicator.className = "freshness-badge stale";
            }
        } else {
            freshnessIndicator.textContent = "Awaiting data";
            freshnessIndicator.className = "freshness-badge stale";
        }
    }, 1000);

    // Initialize velocity dashboard
    setTimeout(initializeVelocityDashboard, 1000);

    // Window resize handler
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(checkScrollbars, 250);
    });

    // Inject modal styles
    injectSessionModalStyles();

    if (APP_CORE_DEBUG) {
        console.log("app-core.js initialization complete");
    }
});

// ==========================================================================
// DEBUG UTILITIES (Available in console)
// ==========================================================================

window.debugAlignment = function() {
    const grids = {
        'highs-list': 'High',
        'lows-list': 'Low',
        'uptrend-list': 'Trend Up',
        'downtrend-list': 'Trend Down',
        'surging-up-list': 'Surge Up',
        'surging-down-list': 'Surge Down'
    };
    
    console.log('=== ALIGNMENT CHECK ===');
    Object.entries(grids).forEach(([id, name]) => {
        const list = document.getElementById(id);
        if (!list) return;
        
        const firstRow = list.querySelector('.event-main-info');
        if (!firstRow) {
            console.log(`${name}: No data`);
            return;
        }
        
        const section = list.closest('section');
        const header = section?.querySelector('.events-header-row');
        if (!header) return;
        
        const headerLeft = header.children[0]?.getBoundingClientRect().left;
        const dataLeft = firstRow.children[0]?.getBoundingClientRect().left;
        const offset = Math.abs(headerLeft - dataLeft);
        
        console.log(`${name}: ${offset < 2 ? '✅ ALIGNED' : `❌ ${offset.toFixed(1)}px off`}`);
    });
};