// File-level debug flags - set to true to enable optional debug logging
const SESSION_MANAGER_DEBUG = false;
const UNIVERSE_MANAGER_DEBUG = false;
const UNIVERSE_API_DEBUG = false;

// ==========================================================================
// SESSION MANAGER CLASS
// ==========================================================================
class SessionManager {
    constructor(timeoutMinutes, loginPageUrl, socket) {
        this.timeoutMs = timeoutMinutes * 60 * 1000;
        this.warningMs = 30 * 1000;
        this.modalTimeoutMs = 30 * 1000;
        this.loginPageUrl = loginPageUrl;
        this.socket = socket;
        this.timer = null;
        this.modalTimer = null;
        this.lastActivity = Date.now();
        this.events = ['mousemove', 'mousedown', 'keypress', 'touchstart', 'click'];
        this.isWarningShown = false;
    }

    start() {
        this.resetTimer();
        this.bindEvents();
    }

    bindEvents() {
        this.events.forEach(event => {
            document.addEventListener(event, () => this.handleActivity());
        });
    }

    handleActivity() {
        this.lastActivity = Date.now();
        this.isWarningShown = false;
        this.removeModal();
        this.resetTimer();
    }

    resetTimer() {
        if (this.timer) {
            clearTimeout(this.timer);
        }
        const timeSinceLastActivity = Date.now() - this.lastActivity;
        const remainingTime = this.timeoutMs - timeSinceLastActivity;

        if (remainingTime <= this.warningMs && !this.isWarningShown) {
            this.timer = setTimeout(() => this.showWarning(), 0);
        } else {
            this.timer = setTimeout(() => this.showWarning(), remainingTime - this.warningMs);
        }
    }

    showWarning() {
        if (this.isWarningShown) return;
        this.isWarningShown = true;

        const modal = document.createElement('div');
        modal.id = 'session-warning-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <p>Your session will expire in 30 seconds. Stay logged in?</p>
                <button id="stay-logged-in">Stay Logged In</button>
                <button id="log-out">Log Out</button>
            </div>
        `;
        document.body.appendChild(modal);

        document.getElementById('stay-logged-in').addEventListener('click', () => {
            this.handleActivity();
        });
        document.getElementById('log-out').addEventListener('click', () => {
            this.removeModal();
            setTimeout(() => this.finalizeExpiration(), 1000);
        });

        this.modalTimer = setTimeout(() => {
            this.removeModal();
            this.finalizeExpiration();
        }, this.modalTimeoutMs);
    }

    removeModal() {
        const modal = document.getElementById('session-warning-modal');
        if (modal) {
            modal.remove();
            this.isWarningShown = false;
        }
        if (this.modalTimer) {
            clearTimeout(this.modalTimer);
            this.modalTimer = null;
        }
    }

    finalizeExpiration() {
        // Keep critical session expiration logging
        console.warn('Session expired, redirecting to login page');
        if (this.socket) {
            this.socket.disconnect();
            if (SESSION_MANAGER_DEBUG) console.log('Socket.IO disconnected due to session expiration');
        }
        window.location.href = this.loginPageUrl;
    }

    stop() {
        if (this.timer) {
            clearTimeout(this.timer);
        }
        this.removeModal();
        this.events.forEach(event => {
            document.removeEventListener(event, () => this.handleActivity());
        });
        if (SESSION_MANAGER_DEBUG) console.log('SessionManager stopped');
    }
}

// ==========================================================================
// ENHANCED UNIVERSE SELECTION MANAGER CLASS
// ==========================================================================
class UniverseSelectionManager {
    constructor() {
        this.modal = null;
        this.currentTracker = null;
        this.universeData = {};
        // Only highlow universe selection remains active
        this.selectedUniverses = {
            highlow: ['DEFAULT_UNIVERSE']
        };
        this.isLoading = false;
        this.useDatabase = true;
        
        // User context integration
        this.userContext = {
            userId: null,
            username: window.userContext?.username || 'User',
            isAuthenticated: window.userContext?.isAuthenticated || false
        };
        
        this.init();
    }
    
    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
        } else {
            this.setupEventListeners();
        }
        
        this.fetchUniverseData();
        this.loadCurrentSelections();
        
        // Get user context from API
        this.getUserContext();
    }
    
    // Get user context from API response
    async getUserContext() {
        try {
            // Use the same pattern as filters - get user_id from API response
            const response = await fetch('/api/user/universe-selections');
            if (response.ok) {
                const data = await response.json();
                if (data.user_id) {
                    this.userContext.userId = data.user_id;
                    if (UNIVERSE_API_DEBUG) console.log(`User context loaded - User ID: ${this.userContext.userId}`);
                    this.updateUserContextDisplay();
                }
            }
        } catch (error) {
            console.error('Error getting user context:', error);
        }
    }
    
    // Update UI elements to show user context
    updateUserContextDisplay() {
        const userInfoElement = document.getElementById('universe-user-info');
        if (userInfoElement && this.userContext.userId) {
            userInfoElement.textContent = `Personal selection for ${this.userContext.username} (ID: ${this.userContext.userId})`;
        }
        
        // Update modal title if open
        const modalTitle = document.querySelector('.modal-title');
        if (modalTitle && this.modal && this.modal.style.display === 'block') {
            modalTitle.textContent = `${this.userContext.username}'s Universe Selection`;
        }
    }
    
    setupEventListeners() {
        this.modal = document.getElementById('universeSelectionModal');
        
        document.querySelectorAll('.universe-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tracker = e.currentTarget.dataset.tracker;
                this.openModal(tracker);
            });
        });
        
        const closeBtn = document.querySelector('.universe-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }
        
        const applyBtn = document.getElementById('applyUniverseSelection');
        const cancelBtn = document.getElementById('cancelUniverseSelection');
        
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applySelection());
        }
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeModal());
        }
        
        document.querySelectorAll('.universe-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateSummary());
        });
        
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
    }
    
    async fetchUniverseData() {
        try {
            const response = await fetch('/api/universes');
            if (response.ok) {
                this.universeData = await response.json();
                this.updateUniverseDisplay();
                if (UNIVERSE_API_DEBUG) console.log('Universe data fetched successfully');
            } else {
                console.error('Failed to fetch universe data:', response.statusText);
                this.fallbackUniverseData();
            }
        } catch (error) {
            console.error('Error fetching universe data:', error);
            this.fallbackUniverseData();
        }
    }
    
    fallbackUniverseData() {
        if (UNIVERSE_API_DEBUG) console.log('Using fallback universe data');
        this.universeData = {
            'DEFAULT_UNIVERSE': { count: 762, description: 'Balanced selection of stocks' },
            'MARKET_CAP_LARGE_UNIVERSE': { count: 545, description: 'Large cap stocks' },
            'MARKET_CAP_MID_UNIVERSE': { count: 1000, description: 'Mid cap stocks' },
            'LEADER_UNIVERSE': { count: 500, description: 'Market leaders' }
        };
        this.updateUniverseDisplay();
    }
    
    // Enhanced universe selection loading with user context
    async loadCurrentSelections() {
        try {
            const response = await fetch('/api/user/universe-selections');
            if (response.ok) {
                const data = await response.json();
                
                // Get user context from response
                if (data.user_id && !this.userContext.userId) {
                    this.userContext.userId = data.user_id;
                    this.updateUserContextDisplay();
                }
                
                if (data.selections) {
                    // Only load highlow selections - per-user from database
                    this.selectedUniverses = {
                        highlow: data.selections.highlow?.universes || ['DEFAULT_UNIVERSE']
                    };
                    this.useDatabase = true;
                    if (UNIVERSE_API_DEBUG) console.log('Loaded per-user universe selections from database:', this.selectedUniverses);
                    this.updateTrackerDisplays();
                    return;
                }
                
                if (data.universe_selections) {
                    // Legacy format - only load highlow selections
                    this.selectedUniverses = {
                        highlow: data.universe_selections.highlow || ['DEFAULT_UNIVERSE']
                    };
                    this.useDatabase = true;
                    if (UNIVERSE_API_DEBUG) console.log('Loaded universe selections from database (legacy format):', this.selectedUniverses);
                    this.updateTrackerDisplays();
                    return;
                }
            }
            
            await this.loadFromSession();
            
        } catch (error) {
            console.error('Error loading universe selections:', error);
            await this.loadFromSession();
        }
    }
    
    async loadFromSession() {
        try {
            const response = await fetch('/api/universes/current');
            if (response.ok) {
                const data = await response.json();
                // Only load highlow from session
                this.selectedUniverses = {
                    highlow: data.highlow || ['DEFAULT_UNIVERSE']
                };
                this.useDatabase = false;
                this.updateTrackerDisplays();
                if (UNIVERSE_API_DEBUG) console.log('Loaded universe selections from session (fallback)');
            }
        } catch (error) {
            console.error('Session fallback also failed:', error);
        }
    }
    
    updateUniverseDisplay() {
        document.querySelectorAll('.universe-count').forEach(countSpan => {
            const label = countSpan.closest('.universe-checkbox-label');
            const checkbox = label.querySelector('.universe-checkbox');
            const universeKey = checkbox.value;
            
            if (this.universeData[universeKey]) {
                countSpan.textContent = `(${this.universeData[universeKey].count} stocks)`;
            }
        });
        
        this.updateTrackerDisplays();
    }
    
    openModal(tracker) {
        if (this.isLoading) return;
        
        this.currentTracker = tracker;
        
        // Update modal with user context
        const modalTitle = document.querySelector('.modal-title');
        if (modalTitle) {
            modalTitle.textContent = `${this.userContext.username}'s Universe Selection`;
        }
        
        document.querySelectorAll('.universe-checkbox').forEach(checkbox => {
            const isSelected = this.selectedUniverses[tracker].includes(checkbox.value);
            checkbox.checked = isSelected;
            
            const label = checkbox.closest('.universe-checkbox-label');
            if (isSelected) {
                label.classList.add('selected');
            } else {
                label.classList.remove('selected');
            }
        });
        
        this.updateSummary();
        this.modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        
        if (UNIVERSE_MANAGER_DEBUG) console.log(`Opened universe modal for ${this.userContext.username}, tracker: ${tracker}`);
    }
    
    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
        this.currentTracker = null;
    }
    
    updateSummary() {
        const checkedBoxes = document.querySelectorAll('.universe-checkbox:checked');
        const selectedKeys = Array.from(checkedBoxes).map(cb => cb.value);
        
        document.querySelectorAll('.universe-checkbox-label').forEach(label => {
            const checkbox = label.querySelector('.universe-checkbox');
            if (checkbox.checked) {
                label.classList.add('selected');
            } else {
                label.classList.remove('selected');
            }
        });
        
        let totalStocks = 0;
        let uniqueStocks = 0;
        
        selectedKeys.forEach(key => {
            if (this.universeData[key]) {
                totalStocks += this.universeData[key].count;
            }
        });
        
        if (selectedKeys.length === 1) {
            uniqueStocks = totalStocks;
        } else if (selectedKeys.length === 2) {
            uniqueStocks = Math.floor(totalStocks * 0.85);
        } else if (selectedKeys.length === 3) {
            uniqueStocks = Math.floor(totalStocks * 0.75);
        } else {
            uniqueStocks = Math.floor(totalStocks * 0.65);
        }
        
        const totalCountSpan = document.getElementById('total-stocks-count');
        const uniqueCountSpan = document.getElementById('unique-stocks-count');
        const performanceSpan = document.getElementById('performance-warning');
        
        if (totalCountSpan) totalCountSpan.textContent = totalStocks.toLocaleString();
        if (uniqueCountSpan) uniqueCountSpan.textContent = uniqueStocks.toLocaleString();
        
        if (performanceSpan) {
            if (uniqueStocks <= 800) {
                performanceSpan.textContent = 'Optimal';
                performanceSpan.className = 'stat-value good';
            } else if (uniqueStocks <= 1200) {
                performanceSpan.textContent = 'Good';
                performanceSpan.className = 'stat-value warning';
            } else {
                performanceSpan.textContent = 'May Impact Performance';
                performanceSpan.className = 'stat-value danger';
            }
        }
    }
    
    // Enhanced apply selection with per-user cache invalidation
    async applySelection() {
        if (!this.currentTracker || this.isLoading) return;
        
        const checkedBoxes = document.querySelectorAll('.universe-checkbox:checked');
        const selectedKeys = Array.from(checkedBoxes).map(cb => cb.value);
        
        if (selectedKeys.length === 0) {
            this.showNotification('Please select at least one universe.', 'error');
            return;
        }
        
        this.setLoadingState(true);
        
        try {
            // Enhanced API call with per-user context
            const success = await this.saveToDatabase(selectedKeys);
            
            if (success) {
                this.useDatabase = true;
                if (UNIVERSE_API_DEBUG) console.log(`Universe selection saved to database for user ${this.userContext.userId}`);
            } else {
                await this.saveToSession(selectedKeys);
                this.useDatabase = false;
                if (UNIVERSE_API_DEBUG) console.log('Universe selection saved to session (fallback)');
            }
            
            this.selectedUniverses[this.currentTracker] = selectedKeys;
            this.updateTrackerDisplays();
            
            // Enhanced success message with user context
            this.showNotification(
                `${this.userContext.username}'s universe selection updated for ${this.currentTracker} tracker! Your data stream will update immediately.`, 
                'success'
            );
            this.closeModal();
            this.triggerDataRefresh();
            
        } catch (error) {
            console.error('Error applying universe selection:', error);
            this.showNotification('Failed to update universe selection. Please try again.', 'error');
        } finally {
            this.setLoadingState(false);
        }
    }
    
    // Enhanced database save with user context
    async saveToDatabase(selectedKeys) {
        try {
            const csrfToken = window.csrfToken || document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            
            const requestBody = {
                tracker: this.currentTracker,
                universes: selectedKeys
            };
            
            // Add user context if available
            if (this.userContext.userId) {
                requestBody.user_id = this.userContext.userId;
            }
            
            if (UNIVERSE_API_DEBUG) console.log('Saving universe selection:', requestBody);
            
            const response = await fetch('/api/universes/select', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify(requestBody)
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Validate cache invalidation occurred
                if (result.cache_invalidated) {
                    if (UNIVERSE_API_DEBUG) console.log('✅ Per-user cache invalidation confirmed');
                } else {
                    console.warn('⚠️ Cache invalidation may not have occurred');
                }
                
                // Update user context if provided
                if (result.user_id && !this.userContext.userId) {
                    this.userContext.userId = result.user_id;
                    this.updateUserContextDisplay();
                }
                
                return true;
            } else {
                console.warn('Database storage failed, will try session fallback');
                return false;
            }
        } catch (error) {
            console.warn('Database error, will try session fallback:', error);
            return false;
        }
    }
    
    async saveToSession(selectedKeys) {
        try {
            const csrfToken = window.csrfToken || document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            
            const response = await fetch('/api/universes/select-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify({
                    tracker: this.currentTracker,
                    universes: selectedKeys
                })
            });
            
            if (response.ok) {
                if (UNIVERSE_API_DEBUG) console.log(`Session: Universe selection applied for ${this.currentTracker}:`, selectedKeys);
            } else {
                throw new Error(`Session storage failed: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Session storage also failed:', error);
            throw error;
        }
    }
    
    setLoadingState(loading) {
        this.isLoading = loading;
        const applyBtn = document.getElementById('applyUniverseSelection');
        const cancelBtn = document.getElementById('cancelUniverseSelection');
        
        if (applyBtn) {
            applyBtn.disabled = loading;
            applyBtn.textContent = loading ? 'Applying...' : 'Apply My Selection';
        }
        
        if (cancelBtn) {
            cancelBtn.disabled = loading;
        }
        
        document.body.style.cursor = loading ? 'wait' : '';
    }
    
    // Enhanced tracker display with user context
    updateTrackerDisplays() {
        const highlowDisplay = document.getElementById('highlow-universe-display');
        if (highlowDisplay) {
            const highlowSelection = this.selectedUniverses.highlow;
            const totalStocks = this.calculateTotalStocks(highlowSelection);
            
            if (highlowSelection.length === 1) {
                const universeKey = highlowSelection[0];
                const name = this.getUniverseName(universeKey);
                highlowDisplay.textContent = `(${name} - ${totalStocks} stocks)`;
            } else {
                highlowDisplay.textContent = `(${highlowSelection.length} universes - ~${totalStocks} stocks)`;
            }
            
            if (UNIVERSE_MANAGER_DEBUG) console.log(`Updated universe display for ${this.userContext.username}: ${highlowDisplay.textContent}`);
        } else {
                // Handle case where display element doesn't exist
                // Could update button text or tooltip instead
                const universeBtn = document.querySelector('.universe-btn');
                if (universeBtn) {
                    const highlowSelection = this.selectedUniverses.highlow;
                    const totalStocks = this.calculateTotalStocks(highlowSelection);
                    universeBtn.title = `Current selection: ${highlowSelection.length} universe(s) - ~${totalStocks} stocks`;
                }
            }
    }
    
    calculateTotalStocks(universeKeys) {
        let total = 0;
        universeKeys.forEach(key => {
            if (this.universeData[key]) {
                total += this.universeData[key].count;
            }
        });
        
        if (universeKeys.length > 1) {
            total = Math.floor(total * (1 - (universeKeys.length - 1) * 0.15));
        }
        
        return total;
    }
    
    getUniverseName(universeKey) {
        const names = {
            'DEFAULT_UNIVERSE': 'Default',
            'MARKET_CAP_LARGE_UNIVERSE': 'Large Cap',
            'MARKET_CAP_MID_UNIVERSE': 'Mid Cap',
            'LEADER_UNIVERSE': 'Leaders'
        };
        return names[universeKey] || universeKey;
    }
    
    // Enhanced notifications with user context
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            z-index: 3000;
            transition: opacity 0.3s ease;
            max-width: 400px;
        `;
        
        if (type === 'success') {
            notification.style.backgroundColor = '#4caf50';
        } else if (type === 'error') {
            notification.style.backgroundColor = '#f44336';
        } else {
            notification.style.backgroundColor = '#2196f3';
        }
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
    
    // Enhanced data refresh trigger with user context
    triggerDataRefresh() {
        if (window.socket) {
            window.socket.emit('refresh_universe_data', {
                tracker: this.currentTracker,
                universes: this.selectedUniverses[this.currentTracker],
                user_id: this.userContext.userId,
                username: this.userContext.username
            });
        }
        
        if (UNIVERSE_MANAGER_DEBUG) console.log(`Triggering data refresh for ${this.userContext.username}'s universe selection change`);
    }
}

// ==========================================================================
// ENHANCED UNIVERSE MANAGER INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Enhanced authentication check
    if (!window.userContext?.isAuthenticated) {
        console.warn('User not authenticated, redirecting to login');
        window.location.href = '/login';
        return;
    }
    
    // Initialize SessionManager
    const sessionManager = new SessionManager(540, '/login', window.socket);
    sessionManager.start();

    // Clean up SessionManager before page unload
    window.addEventListener('beforeunload', () => {
        sessionManager.stop();
    });
    
    // Initialize the Enhanced Universe Selection Manager
    window.universeManager = new UniverseSelectionManager();
    
    // Enhanced socket integration with user context
    if (window.socket) {
        window.socket.on('universe_updated', function(data) {
            if (UNIVERSE_MANAGER_DEBUG) console.log('Universe selection updated:', data);
            
            if (window.universeManager) {
                const username = window.universeManager.userContext.username;
                window.universeManager.showNotification(
                    `${username}'s ${data.tracker} tracker updated with ${data.ticker_count} stocks`, 
                    'success'
                );
            }
        });
        
        // Add per-user cache invalidation listener
        window.socket.on('user_cache_invalidated', function(data) {
            if (UNIVERSE_MANAGER_DEBUG) console.log('User cache invalidated:', data);
            
            if (window.universeManager && data.user_id === window.universeManager.userContext.userId) {
                window.universeManager.showNotification(
                    'Your data stream has been updated with new universe selection!', 
                    'info'
                );
            }
        });
    }
});