// ==========================================================================
// TICKSTOCK CORE APPLICATION MODULE - POST WEBCLEAN
// ==========================================================================
// VERSION: 4.0.0 - Post Webclean
// PURPOSE: Core application logic, socket handling, and UI management
// ==========================================================================

// File-level debug flags
const APP_CORE_DEBUG = false;
const ANALYTICS_DEBUG = false;
const PERFORMANCE_DEBUG = false;

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
    if (typeof price !== 'number' || isNaN(price)) return '$0.00';
    return '$' + price.toFixed(2);
}

function formatPercentage(percentage) {
    if (typeof percentage !== 'number' || isNaN(percentage)) return '0.00%';
    return percentage.toFixed(2) + '%';
}

function formatNumber(number) {
    if (typeof number !== 'number' || isNaN(number)) return '0';
    return number.toLocaleString();
}

function showStatusNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `status-notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: ${type === 'error' ? '#dc3545' : '#28a745'};
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
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
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .status-notification {
            animation: slideInRight 0.3s ease-out;
        }
        
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// ==========================================================================
// SOCKET.IO CONNECTION & HANDLERS
// ==========================================================================
const socket = io('http://localhost:5000', {
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 2000
});

// Connection handlers
socket.on('connect', () => {
    isConnected = true;
    disconnectionCount = 0;
    ProductionLogger.critical("SOCKET", "Connected to server");
    updateLoadingOverlay();
});

socket.on('connect_error', (error) => {
    isConnected = false;
    ProductionLogger.error("SOCKET", "Connection error", error);
    updateLoadingOverlay();
});

socket.on('disconnect', (reason) => {
    isConnected = false;
    disconnectionCount++;
    lastConnectionLossTime = Date.now();
    ProductionLogger.critical("SOCKET", `Disconnected (${reason}) - Count: ${disconnectionCount}`);
    updateLoadingOverlay();
});

// Status updates
socket.on('status_update', (data) => {
    if (!data) return;
    
    if (data.api_health !== undefined) {
        apiHealth = data.api_health;
        updateLoadingOverlay();
    }
    
    if (data.data_source !== undefined) {
        dataSource = data.data_source;
    }
    
    if (data.market_status !== undefined) {
        lastMarketStatus = data.market_status;
        const statusEl = document.getElementById('market-status');
        if (statusEl) {
            statusEl.textContent = getMarketStatusText(data.market_status);
        }
    }
    
    ProductionLogger.info("STATUS", "Update received", data);
});

// Session reset handler
socket.on('session_reset', (data) => {
    if (!data) return;
    
    ProductionLogger.critical("SESSION", "Reset to " + getMarketStatusText(data.new_session));
    showStatusNotification(`Market session changed to ${getMarketStatusText(data.new_session)}`);
});

// MAIN STOCK DATA HANDLER - Simplified for placeholder
socket.on('stock_data', (data) => {
    try {
        // Parse if string
        if (typeof data === 'string') data = JSON.parse(data);
        if (!data || typeof data !== 'object') throw new Error('Invalid stock_data payload');
        
        // Update timestamp
        lastUpdateTime = Date.now();
        
        // Basic status update for placeholder
        updateStatusDisplay(data);
        
        ProductionLogger.info("STOCK_DATA", "Data received for placeholder");
        
    } catch (error) {
        ProductionLogger.error("STOCK_DATA", "Error processing data", error);
    }
});

// Other socket handlers
socket.on('user_status_response', function(data) {
    ProductionLogger.info("SOCKET", "User status response", data);
    if (data.status && typeof updateUserStatus === 'function') {
        updateUserStatus(data.status);
    }
});

socket.on('pong', function(data) {
    ProductionLogger.info("SOCKET", "Pong received");
});

socket.on('test_event', function(data) {
    ProductionLogger.info("SOCKET", "Test event received", data);
    if (window.DEBUG_MODE && typeof displayDebugMessage === 'function') {
        displayDebugMessage('Test Event', data);
    }
});

socket.on('error', function(error) {
    ProductionLogger.error("SOCKET", "WebSocket error", error);
    if (error.message) {
        showStatusNotification('Connection Error: ' + error.message, 'error');
    }
    if (error.code === 'CONNECTION_LOST') {
        setTimeout(() => {
            ProductionLogger.info("SOCKET", "Attempting to reconnect...");
            socket.connect();
        }, 5000);
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

function updateStatusDisplay(data) {
    try {
        const headerStatus = document.querySelector('.header-right .filter-placeholder');
        if (headerStatus) {
            const coreCount = data.core_analytics?.current_state?.universe_size || 2800;
            headerStatus.textContent = `Core: ${coreCount.toLocaleString()} stocks`;
        }
        
        // Update connection indicator
        const connectionStatus = document.getElementById('connection-status');
        if (connectionStatus) {
            const dot = connectionStatus.querySelector('.connection-dot');
            const text = connectionStatus.querySelector('.connection-text');
            
            if (isConnected) {
                if (dot) dot.style.backgroundColor = '#28a745';
                if (text) text.textContent = 'Connected';
            } else {
                if (dot) dot.style.backgroundColor = '#dc3545';
                if (text) text.textContent = 'Disconnected';
            }
        }
        
    } catch (error) {
        ProductionLogger.error("UI", "Error updating status display", error);
    }
}

// ==========================================================================
// INITIALIZATION
// ==========================================================================

// Helper functions
if (typeof updateUserStatus === 'undefined') {
    window.updateUserStatus = function(status) {
        ProductionLogger.info("USER", "Status updated", status);
    };
}

if (typeof displayDebugMessage === 'undefined') {
    window.displayDebugMessage = function(title, data) {
        console.log(`[DEBUG] ${title}:`, data);
    };
}

if (typeof showNotification === 'undefined') {
    window.showNotification = showStatusNotification;
}

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    ProductionLogger.critical("INIT", "Initializing TickStock App (Post-Webclean)");

    // User menu dropdown functionality
    const userButton = document.querySelector('.user-settings-btn');
    if (userButton) {
        userButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const dropdown = this.nextElementSibling;
            const isOpen = dropdown.style.display === 'block';
            
            // Close all dropdowns first
            document.querySelectorAll('.dropdown-content').forEach(d => {
                d.style.display = 'none';
            });
            
            if (!isOpen) {
                dropdown.style.display = 'block';
                this.setAttribute('aria-expanded', 'true');
            } else {
                this.setAttribute('aria-expanded', 'false');
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!userButton.contains(e.target)) {
                const dropdown = userButton.nextElementSibling;
                if (dropdown) {
                    dropdown.style.display = 'none';
                    userButton.setAttribute('aria-expanded', 'false');
                }
            }
        });
        
        userButton.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    }

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

    // Inject modal styles
    injectSessionModalStyles();

    if (APP_CORE_DEBUG) {
        console.log("app-core.js initialization complete (Post-Webclean)");
    }
});

// ==========================================================================
// DEBUG UTILITIES (Available in console)
// ==========================================================================

window.debugPlaceholder = function() {
    console.log('=== PLACEHOLDER DEBUG ===');
    const placeholder = document.querySelector('[data-gs-id="placeholder"]');
    if (placeholder) {
        console.log('✅ Placeholder found');
        console.log('Content:', placeholder.querySelector('.placeholder-content')?.textContent);
        console.log('GridStack Item:', !!placeholder.classList.contains('grid-stack-item'));
    } else {
        console.log('❌ Placeholder not found');
    }
    
    console.log('Socket connected:', isConnected);
    console.log('API Health:', apiHealth);
    console.log('Last update:', lastUpdateTime ? new Date(lastUpdateTime) : 'None');
};