/**
 * Watchlist Management Service for TickStock Pattern Discovery
 * Handles CRUD operations for personal symbol lists and watchlist organization
 * 
 * Sprint 21 - Week 1 Deliverable
 * Architecture: Follows established web/static/js/services/ pattern
 * Integration: Extends Pattern Discovery Dashboard functionality
 */

class WatchlistManager {
    constructor() {
        this.watchlists = new Map();
        this.activeWatchlist = null;
        this.isInitialized = false;
        
        // API endpoints
        this.endpoints = {
            list: '/api/watchlists',
            create: '/api/watchlists',
            update: '/api/watchlists',
            delete: '/api/watchlists',
            addSymbol: '/api/watchlists/symbols',
            removeSymbol: '/api/watchlists/symbols'
        };
        
        this.initialize();
    }

    async initialize() {
        try {
            await this.loadWatchlists();
            this.renderWatchlistPanel();
            this.setupEventHandlers();
            this.isInitialized = true;
            console.log('WatchlistManager initialized successfully');
        } catch (error) {
            console.error('Failed to initialize WatchlistManager:', error);
            this.loadFromLocalStorage();
            // Show a less intrusive message only if there's a real problem
            if (this.watchlists.size === 0) {
                this.showWarning('Using demo watchlists - sign in for full functionality.');
            }
        }
    }

    /**
     * Load all user watchlists from API
     */
    async loadWatchlists() {
        try {
            const response = await fetch(this.endpoints.list, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const responseText = await response.text();
                
                // Check if response is HTML (login redirect) instead of JSON
                if (responseText.trim().startsWith('<!DOCTYPE') || responseText.trim().startsWith('<html')) {
                    throw new Error('Authentication required - received login page instead of JSON data');
                }
                
                const watchlists = JSON.parse(responseText);
                
                // Validate response structure
                if (!Array.isArray(watchlists) && !watchlists.watchlists) {
                    throw new Error('Invalid API response format');
                }
                
                // Handle both direct array and wrapped response formats
                const watchlistsArray = Array.isArray(watchlists) ? watchlists : watchlists.watchlists;
                
                this.watchlists.clear();
                watchlistsArray.forEach(watchlist => {
                    this.watchlists.set(watchlist.id, watchlist);
                });
                
                // Set default watchlist if none active
                if (!this.activeWatchlist && this.watchlists.size > 0) {
                    this.activeWatchlist = this.watchlists.values().next().value.id;
                }
            } else {
                throw new Error(`API returned ${response.status}`);
            }
        } catch (error) {
            console.warn('API unavailable, using mock data:', error.message);
            this.loadMockData();
        }
    }

    /**
     * Create mock watchlist data for development
     */
    loadMockData() {
        const mockWatchlists = [
            {
                id: 'tech-stocks',
                name: 'Tech Stocks',
                symbols: ['AAPL', 'GOOGL', 'MSFT', 'NVDA', 'TSLA'],
                created_at: '2025-01-16T10:00:00Z',
                updated_at: '2025-01-16T15:30:00Z'
            },
            {
                id: 'healthcare',
                name: 'Healthcare',
                symbols: ['JNJ', 'PFE', 'UNH', 'ABBV', 'BMY'],
                created_at: '2025-01-15T14:20:00Z',
                updated_at: '2025-01-16T09:15:00Z'
            },
            {
                id: 'finance',
                name: 'Financial Services',
                symbols: ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
                created_at: '2025-01-14T11:45:00Z',
                updated_at: '2025-01-16T12:00:00Z'
            }
        ];

        this.watchlists.clear();
        mockWatchlists.forEach(watchlist => {
            this.watchlists.set(watchlist.id, watchlist);
        });
        
        this.activeWatchlist = 'tech-stocks';
        this.saveToLocalStorage();
    }

    /**
     * Create new watchlist
     */
    async createWatchlist(name, symbols = []) {
        try {
            const watchlist = {
                name: name.trim(),
                symbols: Array.isArray(symbols) ? symbols : [],
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            };

            const response = await fetch(this.endpoints.create, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(watchlist)
            });

            if (response.ok) {
                const createdWatchlist = await response.json();
                this.watchlists.set(createdWatchlist.id, createdWatchlist);
                this.renderWatchlistPanel();
                this.saveToLocalStorage();
                return createdWatchlist;
            } else {
                throw new Error(`Failed to create watchlist: ${response.status}`);
            }
        } catch (error) {
            console.warn('API unavailable, creating locally:', error.message);
            return this.createWatchlistLocally(name, symbols);
        }
    }

    /**
     * Create watchlist locally when API unavailable
     */
    createWatchlistLocally(name, symbols = []) {
        const id = `watchlist-${Date.now()}`;
        const watchlist = {
            id,
            name: name.trim(),
            symbols: Array.isArray(symbols) ? symbols : [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        this.watchlists.set(id, watchlist);
        this.renderWatchlistPanel();
        this.saveToLocalStorage();
        return watchlist;
    }

    /**
     * Update existing watchlist
     */
    async updateWatchlist(id, updates) {
        try {
            const existingWatchlist = this.watchlists.get(id);
            if (!existingWatchlist) {
                throw new Error(`Watchlist ${id} not found`);
            }

            const updatedWatchlist = {
                ...existingWatchlist,
                ...updates,
                updated_at: new Date().toISOString()
            };

            const response = await fetch(`${this.endpoints.update}/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updatedWatchlist)
            });

            if (response.ok) {
                const result = await response.json();
                this.watchlists.set(id, result);
                this.renderWatchlistPanel();
                this.saveToLocalStorage();
                return result;
            } else {
                throw new Error(`Failed to update watchlist: ${response.status}`);
            }
        } catch (error) {
            console.warn('API unavailable, updating locally:', error.message);
            return this.updateWatchlistLocally(id, updates);
        }
    }

    /**
     * Update watchlist locally when API unavailable
     */
    updateWatchlistLocally(id, updates) {
        const existingWatchlist = this.watchlists.get(id);
        if (!existingWatchlist) {
            throw new Error(`Watchlist ${id} not found`);
        }

        const updatedWatchlist = {
            ...existingWatchlist,
            ...updates,
            updated_at: new Date().toISOString()
        };

        this.watchlists.set(id, updatedWatchlist);
        this.renderWatchlistPanel();
        this.saveToLocalStorage();
        return updatedWatchlist;
    }

    /**
     * Delete watchlist
     */
    async deleteWatchlist(id) {
        try {
            const response = await fetch(`${this.endpoints.delete}/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.watchlists.delete(id);
                
                // Reset active watchlist if deleted
                if (this.activeWatchlist === id) {
                    this.activeWatchlist = this.watchlists.size > 0 
                        ? this.watchlists.keys().next().value 
                        : null;
                }
                
                this.renderWatchlistPanel();
                this.saveToLocalStorage();
                return true;
            } else {
                throw new Error(`Failed to delete watchlist: ${response.status}`);
            }
        } catch (error) {
            console.warn('API unavailable, deleting locally:', error.message);
            return this.deleteWatchlistLocally(id);
        }
    }

    /**
     * Delete watchlist locally when API unavailable
     */
    deleteWatchlistLocally(id) {
        const deleted = this.watchlists.delete(id);
        
        if (deleted && this.activeWatchlist === id) {
            this.activeWatchlist = this.watchlists.size > 0 
                ? this.watchlists.keys().next().value 
                : null;
        }
        
        this.renderWatchlistPanel();
        this.saveToLocalStorage();
        return deleted;
    }

    /**
     * Add symbol to watchlist
     */
    async addSymbolToWatchlist(watchlistId, symbol) {
        const watchlist = this.watchlists.get(watchlistId);
        if (!watchlist) {
            throw new Error(`Watchlist ${watchlistId} not found`);
        }

        if (!watchlist.symbols.includes(symbol.toUpperCase())) {
            watchlist.symbols.push(symbol.toUpperCase());
            await this.updateWatchlist(watchlistId, { symbols: watchlist.symbols });
            this.showSuccess(`Added ${symbol} to ${watchlist.name}`);
        } else {
            this.showWarning(`${symbol} already in ${watchlist.name}`);
        }
    }

    /**
     * Remove symbol from watchlist
     */
    async removeSymbolFromWatchlist(watchlistId, symbol) {
        const watchlist = this.watchlists.get(watchlistId);
        if (!watchlist) {
            throw new Error(`Watchlist ${watchlistId} not found`);
        }

        const symbolIndex = watchlist.symbols.indexOf(symbol.toUpperCase());
        if (symbolIndex > -1) {
            watchlist.symbols.splice(symbolIndex, 1);
            await this.updateWatchlist(watchlistId, { symbols: watchlist.symbols });
            this.showSuccess(`Removed ${symbol} from ${watchlist.name}`);
        }
    }

    /**
     * Get watchlist by ID
     */
    getWatchlist(id) {
        return this.watchlists.get(id);
    }

    /**
     * Get all watchlists as array
     */
    getAllWatchlists() {
        return Array.from(this.watchlists.values());
    }

    /**
     * Get active watchlist
     */
    getActiveWatchlist() {
        return this.activeWatchlist ? this.watchlists.get(this.activeWatchlist) : null;
    }

    /**
     * Set active watchlist
     */
    setActiveWatchlist(id) {
        if (this.watchlists.has(id)) {
            this.activeWatchlist = id;
            this.renderWatchlistPanel();
            this.saveToLocalStorage();
            
            // Apply watchlist filter while preserving any active preset filters
            this.applyWatchlistFilter(id);
        }
    }
    
    /**
     * Clear active watchlist selection
     */
    clearActiveWatchlist() {
        this.activeWatchlist = null;
        this.renderWatchlistPanel();
        this.saveToLocalStorage();
        
        // Reapply any active filter preset without watchlist constraint
        if (window.filterPresets?.activePreset) {
            window.filterPresets.applyPreset(window.filterPresets.activePreset);
        } else if (window.patternDiscovery) {
            window.patternDiscovery.clearWatchlistFilter();
        }
        
        this.showSuccess('Cleared watchlist selection');
    }
    
    /**
     * Apply watchlist filter while preserving preset filters
     */
    applyWatchlistFilter(watchlistId) {
        const watchlist = this.getWatchlist(watchlistId);
        if (!watchlist || !window.patternDiscovery) return;
        
        let patterns = window.patternDiscovery.patterns;
        
        // Apply watchlist filter first
        patterns = patterns.filter(pattern => 
            watchlist.symbols.includes(pattern.symbol)
        );
        
        // Then apply any active filter preset on top of watchlist filter
        if (window.filterPresets?.activePreset) {
            const activePreset = window.filterPresets.getPreset(window.filterPresets.activePreset);
            if (activePreset) {
                patterns = window.filterPresets.applyFilters(patterns, activePreset.filters);
            }
        }
        
        // Update pattern discovery with combined filters
        window.patternDiscovery.filteredPatterns = patterns;
        window.patternDiscovery.renderPatterns();
        window.patternDiscovery.updatePatternCount();
        
        // Show filter status
        let statusMessage = `Filtered by ${watchlist.name}`;
        if (window.filterPresets?.activePreset) {
            const activePreset = window.filterPresets.getPreset(window.filterPresets.activePreset);
            statusMessage += ` + ${activePreset.name}`;
        }
        statusMessage += `: ${patterns.length} patterns`;
        
        window.patternDiscovery.showNotification(statusMessage, 'info');
    }

    /**
     * Render watchlist panel in the UI
     */
    renderWatchlistPanel() {
        const container = document.getElementById('watchlist-panel');
        if (!container) {
            this.createWatchlistPanel();
            return;
        }

        const watchlistArray = this.getAllWatchlists();
        const activeWatchlist = this.getActiveWatchlist();

        container.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <i class="fas fa-star me-2"></i>Watchlists
                        ${activeWatchlist ? `<span class="badge bg-primary ms-2">${activeWatchlist.name}</span>` : ''}
                    </h6>
                    <div>
                        ${this.activeWatchlist ? `<button class="btn btn-sm btn-outline-secondary me-2" id="clear-watchlist-btn">
                            <i class="fas fa-times"></i> Clear
                        </button>` : ''}
                        <button class="btn btn-sm btn-outline-primary" id="create-watchlist-btn">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                </div>
                <div class="card-body p-0">
                    ${watchlistArray.length === 0 ? this.renderEmptyState() : this.renderWatchlistList(watchlistArray, activeWatchlist)}
                </div>
            </div>
        `;

        this.setupPanelEventHandlers();
    }

    /**
     * Create watchlist panel container
     */
    createWatchlistPanel() {
        const patternDiscoveryContent = document.getElementById('pattern-discovery-content');
        console.log('Creating watchlist panel - patternDiscoveryContent:', patternDiscoveryContent);
        
        if (!patternDiscoveryContent) {
            console.warn('pattern-discovery-content element not found');
            return;
        }

        // Simple approach: just insert at the beginning of pattern-discovery-content
        const watchlistPanel = document.createElement('div');
        watchlistPanel.id = 'watchlist-panel';
        watchlistPanel.className = 'mb-3';
        
        // Insert as the first child
        if (patternDiscoveryContent.firstChild) {
            patternDiscoveryContent.insertBefore(watchlistPanel, patternDiscoveryContent.firstChild);
        } else {
            patternDiscoveryContent.appendChild(watchlistPanel);
        }
        
        console.log('Watchlist panel created and inserted as first child');
        this.renderWatchlistPanel();
    }

    /**
     * Render empty state when no watchlists exist
     */
    renderEmptyState() {
        return `
            <div class="text-center p-4 text-muted">
                <i class="fas fa-star fa-2x mb-2"></i>
                <p class="mb-0">No watchlists created yet</p>
                <small>Click + to create your first watchlist</small>
            </div>
        `;
    }

    /**
     * Render list of watchlists
     */
    renderWatchlistList(watchlists, activeWatchlist) {
        return `
            <div class="list-group list-group-flush">
                ${watchlists.map(watchlist => `
                    <div class="list-group-item ${watchlist.id === (activeWatchlist?.id) ? 'active' : ''}" 
                         data-watchlist-id="${watchlist.id}">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="flex-grow-1" style="cursor: pointer;" onclick="window.watchlistManager.setActiveWatchlist('${watchlist.id}')">
                                <h6 class="mb-1">${watchlist.name}</h6>
                                <small class="text-muted">${watchlist.symbols.length} symbols</small>
                            </div>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-outline-secondary dropdown-toggle" 
                                        data-bs-toggle="dropdown" aria-expanded="false">
                                    <i class="fas fa-ellipsis-v"></i>
                                </button>
                                <ul class="dropdown-menu">
                                    <li><a class="dropdown-item" href="#" onclick="window.watchlistManager.showEditModal('${watchlist.id}')">
                                        <i class="fas fa-edit me-2"></i>Edit
                                    </a></li>
                                    <li><a class="dropdown-item" href="#" onclick="window.watchlistManager.showSymbolsModal('${watchlist.id}')">
                                        <i class="fas fa-list me-2"></i>View Symbols
                                    </a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item text-danger" href="#" onclick="window.watchlistManager.confirmDelete('${watchlist.id}')">
                                        <i class="fas fa-trash me-2"></i>Delete
                                    </a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Setup event handlers for watchlist panel
     */
    setupPanelEventHandlers() {
        // Create watchlist button
        const createBtn = document.getElementById('create-watchlist-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.showCreateModal());
        }
        
        // Clear watchlist button
        const clearBtn = document.getElementById('clear-watchlist-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearActiveWatchlist());
        }
    }

    /**
     * Setup global event handlers
     */
    setupEventHandlers() {
        // Listen for pattern table context menu events
        document.addEventListener('contextmenu', (e) => {
            const symbolElement = e.target.closest('[data-symbol]');
            if (symbolElement) {
                e.preventDefault();
                this.showAddToWatchlistContextMenu(e, symbolElement.dataset.symbol);
            }
        });

        // Add to watchlist quick action
        document.addEventListener('click', (e) => {
            if (e.target.matches('.add-to-watchlist-btn')) {
                const symbol = e.target.dataset.symbol;
                this.showQuickAddModal(symbol);
            }
        });
    }

    /**
     * Show create watchlist modal
     */
    showCreateModal() {
        Swal.fire({
            title: 'Create New Watchlist',
            html: `
                <div class="mb-3">
                    <label for="watchlist-name" class="form-label">Watchlist Name</label>
                    <input type="text" class="form-control" id="watchlist-name" placeholder="Enter watchlist name">
                </div>
                <div class="mb-3">
                    <label for="watchlist-symbols" class="form-label">Initial Symbols (Optional)</label>
                    <input type="text" class="form-control" id="watchlist-symbols" 
                           placeholder="AAPL, GOOGL, MSFT (comma separated)">
                    <div class="form-text">You can add symbols later</div>
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'Create',
            preConfirm: () => {
                const name = document.getElementById('watchlist-name').value.trim();
                const symbolsInput = document.getElementById('watchlist-symbols').value.trim();
                
                if (!name) {
                    Swal.showValidationMessage('Please enter a watchlist name');
                    return false;
                }
                
                const symbols = symbolsInput ? 
                    symbolsInput.split(',').map(s => s.trim().toUpperCase()).filter(s => s.length > 0) : 
                    [];
                
                return { name, symbols };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.createWatchlist(result.value.name, result.value.symbols)
                    .then(() => {
                        this.showSuccess(`Created watchlist "${result.value.name}"`);
                    })
                    .catch(error => {
                        this.showError(`Failed to create watchlist: ${error.message}`);
                    });
            }
        });
    }

    /**
     * Show edit watchlist modal
     */
    showEditModal(watchlistId) {
        const watchlist = this.getWatchlist(watchlistId);
        if (!watchlist) return;

        Swal.fire({
            title: 'Edit Watchlist',
            html: `
                <div class="mb-3">
                    <label for="edit-watchlist-name" class="form-label">Watchlist Name</label>
                    <input type="text" class="form-control" id="edit-watchlist-name" value="${watchlist.name}">
                </div>
                <div class="mb-3">
                    <label for="edit-watchlist-symbols" class="form-label">Symbols</label>
                    <textarea class="form-control" id="edit-watchlist-symbols" rows="3">${watchlist.symbols.join(', ')}</textarea>
                    <div class="form-text">Comma separated symbols</div>
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'Save Changes',
            preConfirm: () => {
                const name = document.getElementById('edit-watchlist-name').value.trim();
                const symbolsInput = document.getElementById('edit-watchlist-symbols').value.trim();
                
                if (!name) {
                    Swal.showValidationMessage('Please enter a watchlist name');
                    return false;
                }
                
                const symbols = symbolsInput ? 
                    symbolsInput.split(',').map(s => s.trim().toUpperCase()).filter(s => s.length > 0) : 
                    [];
                
                return { name, symbols };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.updateWatchlist(watchlistId, result.value)
                    .then(() => {
                        this.showSuccess(`Updated watchlist "${result.value.name}"`);
                    })
                    .catch(error => {
                        this.showError(`Failed to update watchlist: ${error.message}`);
                    });
            }
        });
    }

    /**
     * Show watchlist symbols modal
     */
    showSymbolsModal(watchlistId) {
        const watchlist = this.getWatchlist(watchlistId);
        if (!watchlist) return;

        const symbolsHtml = watchlist.symbols.map(symbol => `
            <span class="badge bg-primary me-2 mb-2">
                ${symbol}
                <button type="button" class="btn-close btn-close-white ms-2" 
                        onclick="window.watchlistManager.removeSymbolFromWatchlist('${watchlistId}', '${symbol}')"
                        aria-label="Remove ${symbol}"></button>
            </span>
        `).join('');

        Swal.fire({
            title: `${watchlist.name} Symbols`,
            html: `
                <div class="mb-3">
                    <div class="border rounded p-3" style="max-height: 200px; overflow-y: auto;">
                        ${symbolsHtml || '<span class="text-muted">No symbols in this watchlist</span>'}
                    </div>
                </div>
                <div class="input-group">
                    <input type="text" class="form-control" id="add-symbol-input" 
                           placeholder="Enter symbol (e.g., AAPL)" style="text-transform: uppercase;">
                    <button class="btn btn-primary" type="button" id="add-symbol-btn">Add</button>
                </div>
            `,
            showCloseButton: true,
            showConfirmButton: false,
            didOpen: () => {
                const input = document.getElementById('add-symbol-input');
                const addBtn = document.getElementById('add-symbol-btn');
                
                const addSymbol = () => {
                    const symbol = input.value.trim().toUpperCase();
                    if (symbol) {
                        this.addSymbolToWatchlist(watchlistId, symbol);
                        input.value = '';
                        // Refresh modal
                        setTimeout(() => this.showSymbolsModal(watchlistId), 500);
                    }
                };
                
                addBtn.addEventListener('click', addSymbol);
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') addSymbol();
                });
                input.addEventListener('input', (e) => {
                    e.target.value = e.target.value.toUpperCase();
                });
            }
        });
    }

    /**
     * Confirm watchlist deletion
     */
    confirmDelete(watchlistId) {
        const watchlist = this.getWatchlist(watchlistId);
        if (!watchlist) return;

        Swal.fire({
            title: 'Delete Watchlist?',
            text: `Are you sure you want to delete "${watchlist.name}"? This action cannot be undone.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                this.deleteWatchlist(watchlistId)
                    .then(() => {
                        this.showSuccess(`Deleted watchlist "${watchlist.name}"`);
                    })
                    .catch(error => {
                        this.showError(`Failed to delete watchlist: ${error.message}`);
                    });
            }
        });
    }

    /**
     * Show quick add to watchlist modal
     */
    showQuickAddModal(symbol) {
        const watchlists = this.getAllWatchlists();
        if (watchlists.length === 0) {
            this.showCreateModal();
            return;
        }

        const watchlistOptions = watchlists.map(w => 
            `<option value="${w.id}">${w.name} (${w.symbols.length} symbols)</option>`
        ).join('');

        Swal.fire({
            title: `Add ${symbol} to Watchlist`,
            html: `
                <div class="mb-3">
                    <label for="select-watchlist" class="form-label">Select Watchlist</label>
                    <select class="form-select" id="select-watchlist">
                        ${watchlistOptions}
                    </select>
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'Add Symbol',
            preConfirm: () => {
                return document.getElementById('select-watchlist').value;
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.addSymbolToWatchlist(result.value, symbol);
            }
        });
    }

    /**
     * Save watchlists to localStorage for offline functionality
     */
    saveToLocalStorage() {
        const data = {
            watchlists: Object.fromEntries(this.watchlists),
            activeWatchlist: this.activeWatchlist,
            timestamp: Date.now()
        };
        localStorage.setItem('tickstock-watchlists', JSON.stringify(data));
    }

    /**
     * Load watchlists from localStorage
     */
    loadFromLocalStorage() {
        const stored = localStorage.getItem('tickstock-watchlists');
        if (stored) {
            try {
                const data = JSON.parse(stored);
                this.watchlists = new Map(Object.entries(data.watchlists || {}));
                this.activeWatchlist = data.activeWatchlist;
                this.renderWatchlistPanel();
            } catch (error) {
                console.error('Failed to load from localStorage:', error);
                this.loadMockData();
            }
        } else {
            this.loadMockData();
        }
    }

    /**
     * Show success notification
     */
    showSuccess(message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'success',
                title: 'Success',
                text: message,
                timer: 2000,
                showConfirmButton: false
            });
        } else {
            console.log('SUCCESS:', message);
        }
    }

    /**
     * Show warning notification
     */
    showWarning(message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                title: 'Warning',
                text: message,
                timer: 3000,
                showConfirmButton: false
            });
        } else {
            console.warn('WARNING:', message);
        }
    }

    /**
     * Show error notification
     */
    showError(message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: message,
                confirmButtonText: 'OK'
            });
        } else {
            console.error('ERROR:', message);
        }
    }
}

// Initialize watchlist manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof window !== 'undefined') {
        window.watchlistManager = new WatchlistManager();
    }
});