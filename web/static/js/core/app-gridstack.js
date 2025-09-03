// frontend/js/app-gridstack.js - Post Webclean Version
// Sprint 16: Enhanced with 2x4 layout support for 6 containers
class GridStackManager {
    constructor() {
        this.grid = null;
        this.layoutLoaded = false;
        this.isInitializing = false;
        
        // Calculate optimal cell height based on viewport
        const viewportHeight = window.innerHeight;
        const navbarHeight = 60; // Approximate navbar height
        const statusBarHeight = 40; // Status bar height
        const containerPadding = 20; // Container padding
        const availableHeight = viewportHeight - navbarHeight - statusBarHeight - containerPadding;
        const optimalCellHeight = Math.floor(availableHeight / 10); // 10 rows total for flexibility
        
        this.defaultOptions = {
            column: 12,
            cellHeight: optimalCellHeight || 60, // Dynamic cell height based on viewport
            margin: 5, // Reduced margin for better space utilization
            float: true,
            animate: true,
            disableResize: false,
            disableDrag: true, // Start locked by default
            resizable: { handles: 'se' },
            minRow: 10 // Ensure minimum 10 rows for proper layout
        };
        
        // Debug mode can be enabled via console: window.gridManager.debug = true
        this.debug = false;
        
        this.init();
    }

    log(...args) {
        if (this.debug) {
            console.log('[GridStack]', ...args);
        }
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupGrid());
        } else {
            this.setupGrid();
        }
    }

    setupGrid() {
        this.isInitializing = true;
        
        // Initialize GridStack
        this.grid = GridStack.init(this.defaultOptions, '#grid-container');
        
        // Setup event handlers and controls
        this.setupControls();
        this.setupResponsive();
        
        // Wait for containers to be ready
        this.waitForReady().then(() => {
            this.log('Grid containers ready');
            // Load saved layout or apply default layout
            this.loadLayout();
            this.isInitializing = false;
        });
    }

    waitForReady() {
        return new Promise((resolve) => {
            const checkReady = () => {
                const gridReady = this.grid && this.grid.engine;
                
                // Check for key containers that should be present
                const requiredContainers = ['watchlist', 'market-summary', 'charts', 'alerts', 'market-movers', 'placeholder'];
                const presentContainers = requiredContainers.filter(id => 
                    document.querySelector(`#grid-container .grid-stack-item[data-gs-id="${id}"]`)
                );
                
                // Allow initialization if grid is ready and at least placeholder exists
                const placeholderReady = document.querySelector('#grid-container .grid-stack-item[data-gs-id="placeholder"]');
                
                if (gridReady && placeholderReady) {
                    this.log('Grid components ready', { 
                        present: presentContainers.length, 
                        total: requiredContainers.length 
                    });
                    resolve();
                } else {
                    this.log('Waiting for grid containers...', { 
                        gridReady, 
                        placeholderReady: !!placeholderReady,
                        presentContainers: presentContainers.length
                    });
                    setTimeout(checkReady, 100);
                }
            };
            checkReady();
        });
    }

    getDefaultLayout() {
        // Sprint 16: 2 columns x 4 rows layout to fill available space
        // Total height of 10 units to properly fill viewport
        return [
            // Row 1: watchlist (left) | market-summary (right)
            {
                id: 'watchlist', 
                x: 0, y: 0, 
                w: 6, h: 2.5, 
                minW: 4, minH: 2, 
                maxW: 8, maxH: 4
            },
            {
                id: 'market-summary', 
                x: 6, y: 0, 
                w: 6, h: 2.5, 
                minW: 4, minH: 2, 
                maxW: 8, maxH: 4
            },
            
            // Row 2: charts (left, wider) | alerts (right)
            {
                id: 'charts', 
                x: 0, y: 2.5, 
                w: 8, h: 2.5, 
                minW: 6, minH: 2, 
                maxW: 10, maxH: 4
            },
            {
                id: 'alerts', 
                x: 8, y: 2.5, 
                w: 4, h: 2.5, 
                minW: 3, minH: 2, 
                maxW: 6, maxH: 4
            },
            
            // Row 3-4: market-movers (left) | placeholder (right)
            {
                id: 'market-movers', 
                x: 0, y: 5, 
                w: 6, h: 5, 
                minW: 4, minH: 3, 
                maxW: 8, maxH: 6
            },
            {
                id: 'placeholder', 
                x: 6, y: 5, 
                w: 6, h: 5, 
                minW: 4, minH: 3, 
                maxW: 8, maxH: 6
            }
        ];
    }

    applyLayout(layout) {
        this.grid.batchUpdate();
        
        // Clear existing positions
        this.grid.removeAll(false); // false = don't remove DOM elements
        
        // Apply new layout
        layout.forEach(item => {
            const element = document.querySelector(`[data-gs-id="${item.id}"]`);
            
            if (element) {
                const widgetOptions = {
                    x: item.x,
                    y: item.y,
                    w: item.w,
                    h: item.h,
                    minW: item.minW,
                    minH: item.minH,
                    maxW: item.maxW,
                    maxH: item.maxH,
                    id: item.id
                };
                this.grid.addWidget(element, widgetOptions);
            } 
        });
        
        this.grid.commit();
        
        // Trigger layout updated event
        window.requestAnimationFrame(() => {
            document.dispatchEvent(new Event('layoutUpdated'));
        });
    }

    saveLayout() {
        if (this.isInitializing) {
            return;
        }
        
        const layout = this.grid.save(false);
        
        // Simple localStorage save for placeholder layout
        try {
            localStorage.setItem('gridstack-layout', JSON.stringify(layout));
            this.showSaveConfirmation();
            this.log('Layout saved to localStorage');
        } catch (error) {
            this.showError('Failed to save layout');
            this.log('Save failed:', error);
        }
    }

    loadLayout() {
        try {
            const saved = localStorage.getItem('gridstack-layout');
            if (saved) {
                const layout = JSON.parse(saved);
                this.applyLayout(layout);
                this.log('Layout loaded from localStorage');
            } else {
                // Apply default layout
                this.applyLayout(this.getDefaultLayout());
                this.log('Applied default layout');
            }
        } catch (error) {
            this.log('Load failed, using default:', error);
            this.applyLayout(this.getDefaultLayout());
        }
    }

    showError(message) {
        const toast = document.createElement('div');
        toast.className = 'layout-save-toast error';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 60px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 10000;
            animation: fadeInOut 3s ease-in-out;
        `;
        
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    showSaveConfirmation() {
        const toast = document.createElement('div');
        toast.className = 'layout-save-toast';
        toast.textContent = 'Layout saved';
        toast.style.cssText = `
            position: fixed;
            bottom: 60px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 10000;
            animation: fadeInOut 2s ease-in-out;
        `;
        
        // Add animation if not already present
        if (!document.querySelector('#gridstack-animations')) {
            const style = document.createElement('style');
            style.id = 'gridstack-animations';
            style.textContent = `
                @keyframes fadeInOut {
                    0% { opacity: 0; transform: translateY(20px); }
                    20% { opacity: 1; transform: translateY(0); }
                    80% { opacity: 1; transform: translateY(0); }
                    100% { opacity: 0; transform: translateY(-20px); }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2000);
    }

    setupControls() {
        // Track changes
        this.grid.on('change', (event, items) => {
            if (!this.isInitializing && !this.grid.opts.disableDrag) {
                this.log('Layout changed');
                this.updateEditButtonState();
            }
        });
        
        // Edit/Lock button
        const editBtn = document.getElementById('grid-edit-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => this.toggleEditMode());
        }
        
        // Reset button
        const resetBtn = document.getElementById('grid-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetLayout());
        }
        
        // Set initial button state
        this.updateEditButtonState();
    }

    toggleEditMode() {
        const isLocked = this.grid.opts.disableDrag;
        
        if (isLocked) {
            // Enable edit mode
            this.grid.enable();
            document.querySelector('.grid-stack').classList.add('grid-edit-mode');
            this.log('Edit mode enabled');
        } else {
            // Disable edit mode and save
            this.grid.disable();
            document.querySelector('.grid-stack').classList.remove('grid-edit-mode');
            this.saveLayout();
            this.log('Edit mode disabled, layout saved');
        }
        
        this.updateEditButtonState();
    }

    updateEditButtonState() {
        const editBtn = document.getElementById('grid-edit-btn');
        if (!editBtn) {
            return;
        }
        
        const isLocked = this.grid.opts.disableDrag;
        const btnText = editBtn.querySelector('.btn-text');
        const btnIcon = editBtn.querySelector('.btn-icon');
        
        if (isLocked) {
            editBtn.classList.remove('active');
            if (btnText) btnText.textContent = 'Edit Layout';
            if (btnIcon) btnIcon.textContent = '🔓';
        } else {
            editBtn.classList.add('active');
            if (btnText) btnText.textContent = 'Save Layout';
            if (btnIcon) btnIcon.textContent = '💾';
        }
    }

    resetLayout() {
        if (window.Swal) {
            Swal.fire({
                title: 'Reset Layout',
                text: 'Are you sure you want to reset to the default layout?',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Yes, reset',
                cancelButtonText: 'Cancel'
            }).then((result) => {
                if (result.isConfirmed) {
                    this.performReset();
                }
            });
        } else {
            // Fallback if SweetAlert is not available
            if (confirm('Are you sure you want to reset to the default layout?')) {
                this.performReset();
            }
        }
    }

    performReset() {
        // Apply default layout
        this.applyLayout(this.getDefaultLayout());
        this.saveLayout();
        this.updateEditButtonState();
        this.log('Layout reset to default');
    }

    setupResponsive() {
        const checkMobile = () => {
            const editBtn = document.getElementById('grid-edit-btn');
            
            if (window.innerWidth <= 768) {
                // Mobile: Stack containers vertically by adjusting layout
                this.grid.disable();
                this.grid.opts.disableResize = true;
                if (editBtn) {
                    editBtn.style.display = 'none';
                }
                
                // Apply mobile-optimized layout if in mobile view
                this.applyMobileLayout();
            } else {
                // Desktop: Enable full grid functionality
                if (editBtn) {
                    editBtn.style.display = '';
                }
                if (!document.querySelector('.grid-stack').classList.contains('grid-edit-mode')) {
                    this.grid.disable();
                }
                
                // Restore desktop layout if switching from mobile
                this.restoreDesktopLayout();
            }
        };
        
        window.addEventListener('resize', checkMobile);
        checkMobile();
    }
    
    applyMobileLayout() {
        // Mobile layout: Stack all containers vertically with full width
        const mobileLayout = [
            {id: 'watchlist', x: 0, y: 0, w: 12, h: 3, minW: 12, minH: 2},
            {id: 'market-summary', x: 0, y: 3, w: 12, h: 3, minW: 12, minH: 2},
            {id: 'charts', x: 0, y: 6, w: 12, h: 4, minW: 12, minH: 3},
            {id: 'alerts', x: 0, y: 10, w: 12, h: 3, minW: 12, minH: 2},
            {id: 'market-movers', x: 0, y: 13, w: 12, h: 3, minW: 12, minH: 2},
            {id: 'placeholder', x: 0, y: 16, w: 12, h: 3, minW: 12, minH: 2}
        ];
        
        if (this.grid && !this.isInitializing) {
            this.applyLayout(mobileLayout);
        }
    }
    
    restoreDesktopLayout() {
        // Only restore if currently in a mobile layout (all containers at width 12)
        const currentLayout = this.getCurrentLayout();
        const isMobileLayout = currentLayout.every(item => item.w === 12);
        
        if (this.grid && !this.isInitializing && isMobileLayout) {
            // Try to load saved layout, fallback to default
            this.loadLayout();
        }
    }

    // Public method to get current layout
    getCurrentLayout() {
        return this.grid.save(false);
    }

    // Add a widget programmatically (for future development)
    addWidget(element, options) {
        return this.grid.addWidget(element, options);
    }

    // Remove a widget programmatically
    removeWidget(element) {
        this.grid.removeWidget(element);
    }
}

// Initialize GridStackManager
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.gridManager = new GridStackManager();
    });
} else {
    window.gridManager = new GridStackManager();
}