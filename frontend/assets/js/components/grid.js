// frontend/js/app-gridstack.js
class GridStackManager {
    constructor() {
        this.grid = null;
        this.layoutLoaded = false;
        this.isInitializing = false;
        this.syncManager = null; // Add sync manager
        this.hasUnsavedChanges = false; // Track unsaved changes
        
        this.defaultOptions = {
            column: 12,
            cellHeight: 70,
            margin: 10,
            float: true,
            animate: true,
            disableResize: false,
            disableDrag: true, // Start locked by default
            resizable: { handles: 'se' }
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
        
        // Initialize sync manager
        this.syncManager = new LayoutSyncManager(this);
        
        // Setup event handlers and controls
        this.setupControls();
        this.setupResponsive();
        
        // Wait for all components to be ready
        this.waitForReady().then(() => {
            // Load from database instead of localStorage
            this.syncManager.loadLayoutFromDB();
            this.isInitializing = false;
        });
    }

    waitForReady() {
        return new Promise((resolve) => {
            const checkReady = () => {
                const gridReady = this.grid && this.grid.engine;
                const domReady = document.querySelectorAll('#grid-container .grid-stack-item').length >= 8;
                const socketReady = window.socket?.connected || !window.socket; // Socket optional
                
                if (gridReady && domReady) {
                    this.log('All components ready');
                    resolve();
                } else {
                    this.log('Waiting for components...', { gridReady, domReady, socketReady });
                    setTimeout(checkReady, 100);
                }
            };
            checkReady();
        });
    }

    getDefaultLayout() {
        // if altering this alter this too const domReady = document.querySelectorAll('#grid-container .grid-stack-item').length >= 9;
        return [
            {id: 'core-gauge', x: 0, y: 0, w: 6, h: 3, minW: 4, minH: 3},
            {id: 'percentage-bar', x: 0, y: 3, w: 12, h: 1, minH: 1, maxH: 1},
            {id: 'lows', x: 0, y: 4, w: 6, h: 4, minW: 4, minH: 3},
            {id: 'highs', x: 6, y: 4, w: 6, h: 4, minW: 4, minH: 3},
            {id: 'uptrend', x: 0, y: 8, w: 6, h: 3, minW: 4, minH: 3},
            {id: 'downtrend', x: 6, y: 8, w: 6, h: 3, minW: 4, minH: 3},
            {id: 'surging-up', x: 0, y: 11, w: 6, h: 3, minW: 4, minH: 3},
            {id: 'surging-down', x: 6, y: 11, w: 6, h: 3, minW: 4, minH: 3}
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

    async saveLayout() {
        
        if (this.isInitializing) {
            return;
        }
        
        const layout = this.grid.save(false);
        
        // Ensure all properties are included, including missing 'h' values
        const normalizedLayout = layout.map(item => ({
            id: item.id,
            x: item.x || 0,
            y: item.y || 0,
            w: item.w || 1,
            h: item.h || 1,  // Default to 1 if undefined
            minW: item.minW,
            minH: item.minH,
            maxW: item.maxW,
            maxH: item.maxH
        }));
        
        // Check if syncManager exists and has the method
        if (!this.syncManager) {
            return;
        }
        
        // Save to database - use the correct method name: saveLayout
        try {
            const success = await this.syncManager.saveLayout(normalizedLayout);
            
            if (success) {
                this.hasUnsavedChanges = false;  // Reset the flag
                this.showSaveConfirmation();
                // Force update button state
                setTimeout(() => {
                    this.updateEditButtonState();
                }, 100);
            } else {
                this.showError('Failed to save layout');
            }
        } catch (error) {
            // Show error to user
            this.showError('Failed to save layout');
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
        // Track changes but DON'T auto-save
        this.grid.on('change', (event, items) => {
            if (!this.isInitializing && !this.grid.opts.disableDrag) {
                this.hasUnsavedChanges = true;
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
        } else {
            // Disable edit mode and save to database
            this.grid.disable();
            document.querySelector('.grid-stack').classList.remove('grid-edit-mode');
            
            // Only save if there are changes
            if (this.hasUnsavedChanges) {
                this.saveLayout();
            } 
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
            editBtn.classList.remove('has-changes');  // Make sure to remove this class
            if (btnText) btnText.textContent = 'Edit Layout';
            if (btnIcon) btnIcon.textContent = '🔓';
        } else {
            editBtn.classList.add('active');
            if (btnText) btnText.textContent = this.hasUnsavedChanges ? 'Save Layout*' : 'Save Layout';
            if (btnIcon) btnIcon.textContent = '💾';
            
            // Add visual indicator for unsaved changes
            if (this.hasUnsavedChanges) {
                editBtn.classList.add('has-changes');
            } else {
                editBtn.classList.remove('has-changes');
            }
        }
        
    }
    resetLayout() {
        Swal.fire({
            title: 'Reset Layout',
            text: 'Are you sure you want to reset to the default layout?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, reset',
            cancelButtonText: 'Cancel',
            customClass: {
                popup: 'tickstock-swal-popup',
                confirmButton: 'tickstock-btn-primary',
                cancelButton: 'tickstock-btn-secondary'
            }
        }).then(async (result) => {
            if (result.isConfirmed) {
                // Apply default layout
                this.applyLayout(this.getDefaultLayout());
                
                // Save default layout to database
                await this.syncManager.saveLayout(this.getDefaultLayout());
                
                this.hasUnsavedChanges = false;
                this.updateEditButtonState();
                
                // Notify server if connected
                if (window.socket?.connected) {
                    window.socket.emit('user_action', {
                        action: 'reset_layout',
                        timestamp: Date.now()
                    });
                }
            }
        });
    }

    setupResponsive() {
        const checkMobile = () => {
            const editBtn = document.getElementById('grid-edit-btn');
            
            if (window.innerWidth <= 768) {
                this.grid.disable();
                this.grid.opts.disableResize = true;
                if (editBtn) {
                    editBtn.style.display = 'none';
                }
            } else {
                if (editBtn) {
                    editBtn.style.display = '';
                }
                if (!document.querySelector('.grid-stack').classList.contains('grid-edit-mode')) {
                    this.grid.disable();
                }
            }
        };
        
        window.addEventListener('resize', checkMobile);
        checkMobile();
    }

    // Public method to get current layout
    getCurrentLayout() {
        return this.grid.save(false);
    }

    // Public method to check if layout has unsaved changes
    hasUnsavedLayout() {
        return this.hasUnsavedChanges;
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