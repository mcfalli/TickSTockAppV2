/**
 * Retractable Filter Controller - TickStock.ai
 * 
 * Clean, robust architecture for managing retractable filter panels.
 * Designed for seamless integration with existing Bootstrap layouts.
 * 
 * Features:
 * - CSS Grid based layout (no fixed positioning conflicts)
 * - Responsive design with mobile overlay support
 * - Theme-aware (light/dark mode)
 * - Progressive enhancement
 * - Clean event handling with delegation
 * - Memory-efficient (no event listener leaks)
 */

class RetractableFilterController {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        
        if (!this.container) {
            console.error(`RetractableFilterController: Container '${containerId}' not found`);
            return;
        }
        
        // Configuration options
        this.options = {
            initiallyCollapsed: false,
            animationDuration: 300,
            mobileBreakpoint: 992,
            enableKeyboardNavigation: true,
            enableTouchGestures: false,
            rememberState: true,
            storageKey: `retractable-filter-${containerId}`,
            onToggle: null,
            onBeforeToggle: null,
            ...options
        };
        
        // State management
        this.isCollapsed = this.options.initiallyCollapsed;
        this.isInitialized = false;
        this.isMobile = window.innerWidth < this.options.mobileBreakpoint;
        this.eventHandlers = new Map();
        
        // Initialize
        this.init();
    }
    
    /**
     * Initialize the controller
     */
    init() {
        console.log('RetractableFilterController: Initializing...');
        
        // Load saved state
        this.loadState();
        
        // Setup the HTML structure
        this.setupStructure();
        
        // Setup event handlers
        this.setupEventHandlers();
        
        // Setup responsive behavior
        this.setupResponsiveHandlers();
        
        // Apply initial state
        this.applyState(false); // No animation on initial load
        
        // Setup keyboard navigation if enabled
        if (this.options.enableKeyboardNavigation) {
            this.setupKeyboardNavigation();
        }
        
        this.isInitialized = true;
        console.log('RetractableFilterController: Initialized successfully');
    }
    
    /**
     * Setup the HTML structure within the existing container
     */
    setupStructure() {
        // Store original content
        const originalContent = this.container.innerHTML;
        
        // Create new structure
        this.container.innerHTML = `
            <div class="pattern-discovery-layout" id="${this.containerId}-layout">
                <!-- Toggle Bar -->
                <div class="filter-toggle-bar">
                    <button class="filter-toggle-btn" id="${this.containerId}-toggle" type="button">
                        <i class="fas fa-chevron-left toggle-icon"></i>
                        <span class="toggle-text">Hide Filters</span>
                    </button>
                    <div class="filter-status">
                        <span class="badge bg-secondary" id="${this.containerId}-filter-count">0 filters active</span>
                    </div>
                </div>
                
                <!-- Filter Panel -->
                <div class="filter-panel" id="${this.containerId}-panel">
                    <div class="filter-panel-content" id="${this.containerId}-panel-content">
                        <!-- Filter content will be inserted here -->
                    </div>
                </div>
                
                <!-- Main Content Area -->
                <div class="main-content-area" id="${this.containerId}-content">
                    <!-- Main content will be inserted here -->
                </div>
                
                <!-- Mobile Overlay -->
                <div class="filter-overlay" id="${this.containerId}-overlay"></div>
            </div>
        `;
        
        // Cache DOM references
        this.layout = document.getElementById(`${this.containerId}-layout`);
        this.toggleBtn = document.getElementById(`${this.containerId}-toggle`);
        this.toggleText = this.toggleBtn.querySelector('.toggle-text');
        this.toggleIcon = this.toggleBtn.querySelector('.toggle-icon');
        this.filterPanel = document.getElementById(`${this.containerId}-panel`);
        this.filterContent = document.getElementById(`${this.containerId}-panel-content`);
        this.mainContent = document.getElementById(`${this.containerId}-content`);
        this.overlay = document.getElementById(`${this.containerId}-overlay`);
        this.filterCount = document.getElementById(`${this.containerId}-filter-count`);
        
        // Store reference to original content for later insertion
        this.originalContent = originalContent;
    }
    
    /**
     * Setup event handlers using delegation
     */
    setupEventHandlers() {
        // Toggle button click
        this.addEventHandler(this.toggleBtn, 'click', (e) => {
            e.preventDefault();
            this.toggle();
        });
        
        // Overlay click (mobile)
        this.addEventHandler(this.overlay, 'click', (e) => {
            if (this.isMobile) {
                this.collapse();
            }
        });
        
        // Escape key to close (mobile)
        this.addEventHandler(document, 'keydown', (e) => {
            if (e.key === 'Escape' && this.isMobile && !this.isCollapsed) {
                this.collapse();
            }
        });
    }
    
    /**
     * Setup responsive behavior handlers
     */
    setupResponsiveHandlers() {
        const resizeHandler = () => {
            const wasMobile = this.isMobile;
            this.isMobile = window.innerWidth < this.options.mobileBreakpoint;
            
            // If transitioning between mobile/desktop, update layout
            if (wasMobile !== this.isMobile) {
                this.applyState(false); // No animation during resize
            }
        };
        
        this.addEventHandler(window, 'resize', this.debounce(resizeHandler, 150));
    }
    
    /**
     * Setup keyboard navigation
     */
    setupKeyboardNavigation() {
        // Focus management for accessibility
        this.addEventHandler(this.toggleBtn, 'keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.toggle();
            }
        });
    }
    
    /**
     * Add event handler with cleanup tracking
     */
    addEventHandler(element, event, handler) {
        if (!element) return;
        
        const wrappedHandler = (e) => {
            try {
                handler(e);
            } catch (error) {
                console.error('RetractableFilterController: Event handler error:', error);
            }
        };
        
        element.addEventListener(event, wrappedHandler);
        
        // Track for cleanup
        if (!this.eventHandlers.has(element)) {
            this.eventHandlers.set(element, []);
        }
        this.eventHandlers.get(element).push({ event, handler: wrappedHandler });
    }
    
    /**
     * Toggle the filter panel
     */
    toggle() {
        if (this.options.onBeforeToggle) {
            const shouldContinue = this.options.onBeforeToggle(!this.isCollapsed);
            if (shouldContinue === false) return;
        }
        
        this.isCollapsed = !this.isCollapsed;
        this.applyState(true);
        this.saveState();
        
        if (this.options.onToggle) {
            this.options.onToggle(this.isCollapsed);
        }
    }
    
    /**
     * Expand the filter panel
     */
    expand() {
        if (!this.isCollapsed) return;
        this.toggle();
    }
    
    /**
     * Collapse the filter panel
     */
    collapse() {
        if (this.isCollapsed) return;
        this.toggle();
    }
    
    /**
     * Apply the current state to the DOM
     */
    applyState(animate = true) {
        if (!this.layout) return;
        
        // Temporarily disable transitions if no animation wanted
        if (!animate) {
            this.layout.style.transition = 'none';
            this.filterPanel.style.transition = 'none';
            this.mainContent.style.transition = 'none';
        }
        
        // Apply CSS classes
        this.layout.classList.toggle('filters-collapsed', this.isCollapsed);
        this.layout.classList.toggle('filters-expanded', !this.isCollapsed);
        
        // Update toggle button
        this.updateToggleButton();
        
        // Handle mobile overlay
        if (this.isMobile) {
            document.body.classList.toggle('filter-panel-open', !this.isCollapsed);
        }
        
        // Re-enable transitions
        if (!animate) {
            requestAnimationFrame(() => {
                this.layout.style.transition = '';
                this.filterPanel.style.transition = '';
                this.mainContent.style.transition = '';
            });
        }
    }
    
    /**
     * Update toggle button appearance
     */
    updateToggleButton() {
        if (!this.toggleText || !this.toggleIcon) return;
        
        if (this.isCollapsed) {
            this.toggleText.textContent = 'Show Filters';
            this.toggleIcon.className = 'fas fa-chevron-right toggle-icon';
        } else {
            this.toggleText.textContent = 'Hide Filters';
            this.toggleIcon.className = 'fas fa-chevron-left toggle-icon';
        }
    }
    
    /**
     * Set filter panel content
     */
    setFilterContent(content) {
        if (!this.filterContent) return;
        
        if (typeof content === 'string') {
            this.filterContent.innerHTML = content;
        } else if (content instanceof Element) {
            this.filterContent.innerHTML = '';
            this.filterContent.appendChild(content);
        }
    }
    
    /**
     * Set main content
     */
    setMainContent(content) {
        if (!this.mainContent) return;
        
        if (typeof content === 'string') {
            this.mainContent.innerHTML = content;
        } else if (content instanceof Element) {
            this.mainContent.innerHTML = '';
            this.mainContent.appendChild(content);
        }
    }
    
    /**
     * Update filter count badge
     */
    updateFilterCount(count) {
        if (!this.filterCount) return;
        
        const text = count === 0 ? 'No filters active' : 
                    count === 1 ? '1 filter active' : 
                    `${count} filters active`;
        
        this.filterCount.textContent = text;
        this.filterCount.className = count > 0 ? 'badge bg-primary' : 'badge bg-secondary';
    }
    
    /**
     * Load state from storage
     */
    loadState() {
        if (!this.options.rememberState) return;
        
        try {
            const saved = localStorage.getItem(this.options.storageKey);
            if (saved !== null) {
                this.isCollapsed = JSON.parse(saved);
            }
        } catch (error) {
            console.warn('RetractableFilterController: Could not load state:', error);
        }
    }
    
    /**
     * Save state to storage
     */
    saveState() {
        if (!this.options.rememberState) return;
        
        try {
            localStorage.setItem(this.options.storageKey, JSON.stringify(this.isCollapsed));
        } catch (error) {
            console.warn('RetractableFilterController: Could not save state:', error);
        }
    }
    
    /**
     * Utility: Debounce function
     */
    debounce(func, wait) {
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
    
    /**
     * Get current state
     */
    getState() {
        return {
            isCollapsed: this.isCollapsed,
            isMobile: this.isMobile,
            isInitialized: this.isInitialized
        };
    }
    
    /**
     * Cleanup event handlers and DOM
     */
    destroy() {
        // Remove all event handlers
        for (const [element, handlers] of this.eventHandlers) {
            handlers.forEach(({ event, handler }) => {
                element.removeEventListener(event, handler);
            });
        }
        this.eventHandlers.clear();
        
        // Restore original content if needed
        if (this.originalContent && this.container) {
            this.container.innerHTML = this.originalContent;
        }
        
        // Clear references
        this.layout = null;
        this.toggleBtn = null;
        this.filterPanel = null;
        this.mainContent = null;
        
        console.log('RetractableFilterController: Destroyed');
    }
}

// Export for use
window.RetractableFilterController = RetractableFilterController;