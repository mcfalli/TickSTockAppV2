/**
 * Filter Presets Service for TickStock Pattern Discovery
 * Handles saved filter configurations and advanced filtering logic
 * 
 * Sprint 21 - Week 1 Deliverable
 * Architecture: Follows established web/static/js/services/ pattern
 * Integration: Extends Pattern Discovery Dashboard functionality
 */

class FilterPresetsService {
    constructor() {
        this.presets = new Map();
        this.activePreset = null;
        this.isInitialized = false;
        
        // API endpoints
        this.endpoints = {
            list: '/api/filters/presets',
            create: '/api/filters/presets',
            update: '/api/filters/presets',
            delete: '/api/filters/presets'
        };
        
        // Filter operators
        this.operators = {
            'eq': { label: 'equals', apply: (value, target) => value === target },
            'ne': { label: 'not equals', apply: (value, target) => value !== target },
            'gt': { label: 'greater than', apply: (value, target) => value > target },
            'gte': { label: 'greater than or equal', apply: (value, target) => value >= target },
            'lt': { label: 'less than', apply: (value, target) => value < target },
            'lte': { label: 'less than or equal', apply: (value, target) => value <= target },
            'in': { label: 'in list', apply: (value, target) => Array.isArray(target) && target.includes(value) },
            'contains': { label: 'contains', apply: (value, target) => String(value).toLowerCase().includes(String(target).toLowerCase()) },
            'between': { label: 'between', apply: (value, target) => Array.isArray(target) && target.length === 2 && value >= target[0] && value <= target[1] }
        };
        
        this.initialize();
    }

    async initialize() {
        try {
            await this.loadPresets();
            this.renderPresetsPanel();
            this.setupEventHandlers();
            this.isInitialized = true;
            console.log('FilterPresetsService initialized successfully');
        } catch (error) {
            console.error('Failed to initialize FilterPresetsService:', error);
            this.loadFromLocalStorage();
        }
    }

    /**
     * Load all saved filter presets from API
     */
    async loadPresets() {
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
                
                const presets = JSON.parse(responseText);
                
                // Handle both direct array and wrapped response formats
                const presetsArray = Array.isArray(presets) ? presets : presets;
                
                this.presets.clear();
                presetsArray.forEach(preset => {
                    this.presets.set(preset.id, preset);
                });
                
            } else {
                throw new Error(`API returned ${response.status}`);
            }
        } catch (error) {
            console.warn('API unavailable, using mock data:', error.message);
            this.loadMockData();
        }
    }

    /**
     * Create mock filter preset data for development
     */
    loadMockData() {
        const mockPresets = [
            {
                id: 'high-confidence',
                name: 'High Confidence Patterns',
                description: 'Patterns with 80%+ confidence',
                filters: {
                    logic: 'AND',
                    conditions: [
                        {
                            field: 'confidence',
                            operator: 'gte',
                            value: 0.8
                        }
                    ]
                },
                created_at: '2025-01-16T10:00:00Z',
                updated_at: '2025-01-16T15:30:00Z'
            },
            {
                id: 'breakout-patterns',
                name: 'Breakout Patterns',
                description: 'Weekly and Daily breakout patterns with strong RS',
                filters: {
                    logic: 'AND',
                    conditions: [
                        {
                            field: 'pattern',
                            operator: 'in',
                            value: ['WeeklyBO', 'DailyBO']
                        },
                        {
                            field: 'rs',
                            operator: 'gte',
                            value: 70
                        },
                        {
                            field: 'confidence',
                            operator: 'gte',
                            value: 0.7
                        }
                    ]
                },
                created_at: '2025-01-15T14:20:00Z',
                updated_at: '2025-01-16T09:15:00Z'
            },
            {
                id: 'reversal-signals',
                name: 'Reversal Signals',
                description: 'Doji and Hammer patterns with high volume',
                filters: {
                    logic: 'AND',
                    conditions: [
                        {
                            field: 'pattern',
                            operator: 'in',
                            value: ['Doji', 'Hammer', 'ShootingStar']
                        },
                        {
                            field: 'volume',
                            operator: 'gte',
                            value: 1000000
                        }
                    ]
                },
                created_at: '2025-01-14T11:45:00Z',
                updated_at: '2025-01-16T12:00:00Z'
            }
        ];

        this.presets.clear();
        mockPresets.forEach(preset => {
            this.presets.set(preset.id, preset);
        });
        
        this.saveToLocalStorage();
    }

    /**
     * Create new filter preset
     */
    async createPreset(name, description, filters) {
        try {
            const preset = {
                name: name.trim(),
                description: description.trim(),
                filters: filters,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            };

            const response = await fetch(this.endpoints.create, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(preset)
            });

            if (response.ok) {
                const createdPreset = await response.json();
                this.presets.set(createdPreset.id, createdPreset);
                this.renderPresetsPanel();
                this.saveToLocalStorage();
                return createdPreset;
            } else {
                throw new Error(`Failed to create preset: ${response.status}`);
            }
        } catch (error) {
            console.warn('API unavailable, creating locally:', error.message);
            return this.createPresetLocally(name, description, filters);
        }
    }

    /**
     * Create preset locally when API unavailable
     */
    createPresetLocally(name, description, filters) {
        const id = `preset-${Date.now()}`;
        const preset = {
            id,
            name: name.trim(),
            description: description.trim(),
            filters: filters,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        this.presets.set(id, preset);
        this.renderPresetsPanel();
        this.saveToLocalStorage();
        return preset;
    }

    /**
     * Update existing preset
     */
    async updatePreset(id, updates) {
        try {
            const existingPreset = this.presets.get(id);
            if (!existingPreset) {
                throw new Error(`Preset ${id} not found`);
            }

            const updatedPreset = {
                ...existingPreset,
                ...updates,
                updated_at: new Date().toISOString()
            };

            const response = await fetch(`${this.endpoints.update}/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updatedPreset)
            });

            if (response.ok) {
                const result = await response.json();
                this.presets.set(id, result);
                this.renderPresetsPanel();
                this.saveToLocalStorage();
                return result;
            } else {
                throw new Error(`Failed to update preset: ${response.status}`);
            }
        } catch (error) {
            console.warn('API unavailable, updating locally:', error.message);
            return this.updatePresetLocally(id, updates);
        }
    }

    /**
     * Update preset locally when API unavailable
     */
    updatePresetLocally(id, updates) {
        const existingPreset = this.presets.get(id);
        if (!existingPreset) {
            throw new Error(`Preset ${id} not found`);
        }

        const updatedPreset = {
            ...existingPreset,
            ...updates,
            updated_at: new Date().toISOString()
        };

        this.presets.set(id, updatedPreset);
        this.renderPresetsPanel();
        this.saveToLocalStorage();
        return updatedPreset;
    }

    /**
     * Delete preset
     */
    async deletePreset(id) {
        try {
            const response = await fetch(`${this.endpoints.delete}/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.presets.delete(id);
                
                // Reset active preset if deleted
                if (this.activePreset === id) {
                    this.activePreset = null;
                    this.clearActiveFilter();
                }
                
                this.renderPresetsPanel();
                this.saveToLocalStorage();
                return true;
            } else {
                throw new Error(`Failed to delete preset: ${response.status}`);
            }
        } catch (error) {
            console.warn('API unavailable, deleting locally:', error.message);
            return this.deletePresetLocally(id);
        }
    }

    /**
     * Delete preset locally when API unavailable
     */
    deletePresetLocally(id) {
        const deleted = this.presets.delete(id);
        
        if (deleted && this.activePreset === id) {
            this.activePreset = null;
            this.clearActiveFilter();
        }
        
        this.renderPresetsPanel();
        this.saveToLocalStorage();
        return deleted;
    }

    /**
     * Apply filter preset
     */
    applyPreset(id) {
        const preset = this.presets.get(id);
        if (!preset) {
            this.showError(`Preset ${id} not found`);
            return;
        }

        this.activePreset = id;
        
        // Apply filters to pattern discovery, considering active watchlist
        if (window.patternDiscovery) {
            let patterns = window.patternDiscovery.patterns;
            
            // First apply watchlist filter if active
            if (window.watchlistManager?.activeWatchlist) {
                const activeWatchlist = window.watchlistManager.getActiveWatchlist();
                if (activeWatchlist) {
                    patterns = patterns.filter(pattern => 
                        activeWatchlist.symbols.includes(pattern.symbol)
                    );
                }
            }
            
            // Then apply filter preset on top of watchlist filter
            const filteredPatterns = this.applyFilters(patterns, preset.filters);
            window.patternDiscovery.filteredPatterns = filteredPatterns;
            window.patternDiscovery.renderPatterns();
            window.patternDiscovery.updatePatternCount();
            
            // Show combined filter status
            let statusMessage = `Applied ${preset.name}`;
            if (window.watchlistManager?.activeWatchlist) {
                const activeWatchlist = window.watchlistManager.getActiveWatchlist();
                statusMessage = `Filtered by ${activeWatchlist.name} + ${preset.name}`;
            }
            statusMessage += `: ${filteredPatterns.length} patterns`;
            
            window.patternDiscovery.showNotification(statusMessage, 'info');
        }
        
        this.renderPresetsPanel();
        this.saveToLocalStorage();
    }

    /**
     * Apply complex filter logic to patterns
     */
    applyFilters(patterns, filters) {
        if (!filters.conditions || filters.conditions.length === 0) {
            return patterns;
        }

        return patterns.filter(pattern => {
            const results = filters.conditions.map(condition => 
                this.evaluateCondition(pattern, condition)
            );
            
            if (filters.logic === 'OR') {
                return results.some(result => result);
            } else {
                return results.every(result => result);
            }
        });
    }

    /**
     * Evaluate single filter condition
     */
    evaluateCondition(pattern, condition) {
        const { field, operator, value } = condition;
        const patternValue = this.getPatternValue(pattern, field);
        
        if (patternValue === null || patternValue === undefined) {
            return false;
        }
        
        const operatorFunc = this.operators[operator];
        if (!operatorFunc) {
            console.warn(`Unknown operator: ${operator}`);
            return false;
        }
        
        return operatorFunc.apply(patternValue, value);
    }

    /**
     * Get value from pattern object by field name
     */
    getPatternValue(pattern, field) {
        switch (field) {
            case 'confidence':
                return pattern.confidence;
            case 'pattern':
                return pattern.pattern;
            case 'symbol':
                return pattern.symbol;
            case 'price':
                return pattern.price;
            case 'change_percent':
                return pattern.change_percent;
            case 'rs':
                return pattern.rs;
            case 'volume':
                return pattern.volume;
            case 'rsi':
                return pattern.rsi;
            case 'market_cap':
                return pattern.market_cap;
            default:
                return pattern[field];
        }
    }

    /**
     * Clear active filter
     */
    clearActiveFilter() {
        this.activePreset = null;
        
        if (window.patternDiscovery) {
            window.patternDiscovery.filteredPatterns = null;
            window.patternDiscovery.renderPatterns();
            window.patternDiscovery.updatePatternCount();
        }
        
        this.renderPresetsPanel();
        this.saveToLocalStorage();
        
        this.showSuccess('Cleared active filter preset');
    }

    /**
     * Get preset by ID
     */
    getPreset(id) {
        return this.presets.get(id);
    }

    /**
     * Get all presets as array
     */
    getAllPresets() {
        return Array.from(this.presets.values());
    }

    /**
     * Render presets panel in the UI
     */
    renderPresetsPanel() {
        // First try the new collapsible structure
        let container = document.querySelector('#presets-content .p-3');
        if (!container) {
            // Fallback to old structure
            container = document.getElementById('filter-presets-panel');
            if (!container) {
                this.createPresetsPanel();
                return;
            }
        }

        const presetsArray = this.getAllPresets();
        const activePreset = this.activePreset ? this.presets.get(this.activePreset) : null;

        // Check if we're in the new collapsible structure
        const isCollapsibleStructure = !!document.querySelector('#presets-content .p-3');

        if (isCollapsibleStructure) {
            // New collapsible structure - render compact content
            container.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div class="d-flex align-items-center">
                        ${activePreset ? `<span class="badge bg-success me-2">${activePreset.name}</span>` : 
                                         `<span class="text-muted small">No preset selected</span>`}
                    </div>
                    <div>
                        ${this.activePreset ? `<button class="btn btn-sm btn-outline-secondary me-1" id="clear-preset-btn" title="Clear preset">
                            <i class="fas fa-times"></i>
                        </button>` : ''}
                        <button class="btn btn-sm btn-success" id="create-preset-btn" title="Create preset">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                </div>
                ${presetsArray.length === 0 ? this.renderEmptyState() : this.renderCompactPresetsList(presetsArray, activePreset)}
            `;
        } else {
            // Old structure - render full card
            container.innerHTML = `
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-filter me-2"></i>Filter Presets
                            ${activePreset ? `<span class="badge bg-primary ms-2">${activePreset.name}</span>` : ''}
                        </h6>
                        <div>
                            ${this.activePreset ? `<button class="btn btn-sm btn-outline-secondary me-2" id="clear-preset-btn">
                                <i class="fas fa-times"></i> Clear
                            </button>` : ''}
                            <button class="btn btn-sm btn-outline-primary" id="create-preset-btn">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                    </div>
                    <div class="card-body p-0">
                        ${presetsArray.length === 0 ? this.renderEmptyState() : this.renderPresetsList(presetsArray, activePreset)}
                    </div>
                </div>
            `;
        }

        this.setupPanelEventHandlers();
    }

    /**
     * Create presets panel container
     */
    createPresetsPanel() {
        const watchlistPanel = document.getElementById('watchlist-panel');
        console.log('Creating presets panel - watchlistPanel found:', watchlistPanel);
        
        if (watchlistPanel) {
            // Insert presets panel after watchlist panel
            const presetsPanel = document.createElement('div');
            presetsPanel.id = 'filter-presets-panel';
            presetsPanel.className = 'mb-3';
            
            watchlistPanel.parentNode.insertBefore(presetsPanel, watchlistPanel.nextSibling);
            console.log('Filter presets panel created and inserted');
            this.renderPresetsPanel();
        } else {
            // Fallback: insert into pattern discovery content
            const patternDiscoveryContent = document.getElementById('pattern-discovery-content');
            if (patternDiscoveryContent) {
                const presetsPanel = document.createElement('div');
                presetsPanel.id = 'filter-presets-panel';
                presetsPanel.className = 'mb-3';
                
                if (patternDiscoveryContent.firstChild) {
                    patternDiscoveryContent.insertBefore(presetsPanel, patternDiscoveryContent.firstChild);
                } else {
                    patternDiscoveryContent.appendChild(presetsPanel);
                }
                console.log('Filter presets panel created as fallback');
                this.renderPresetsPanel();
            }
        }
    }

    /**
     * Render empty state when no presets exist
     */
    renderEmptyState() {
        return `
            <div class="text-center p-4 text-muted">
                <i class="fas fa-filter fa-2x mb-2"></i>
                <p class="mb-0">No filter presets created yet</p>
                <small>Click + to create your first preset</small>
            </div>
        `;
    }

    /**
     * Render compact presets list for collapsible structure
     */
    renderCompactPresetsList(presets, activePreset) {
        if (presets.length === 0) {
            return this.renderEmptyState();
        }

        return `
            <div class="presets-compact-list">
                ${presets.map(preset => `
                    <div class="preset-compact-item ${preset.id === activePreset?.id ? 'active' : ''}" 
                         data-preset-id="${preset.id}">
                        <div class="d-flex justify-content-between align-items-center py-2 px-2 rounded ${preset.id === activePreset?.id ? 'bg-success text-white' : 'hover-bg-light'}"
                             style="cursor: pointer;" 
                             title="${preset.name}${preset.description ? ': ' + preset.description : ''}">
                            <div class="flex-grow-1" onclick="window.filterPresets.applyPreset('${preset.id}')">
                                <div class="fw-semibold">${preset.name}</div>
                            </div>
                            <div class="d-flex align-items-center">
                                ${preset.id === activePreset?.id ? 
                                    '<i class="fas fa-check-circle me-1"></i>' : ''}
                                <div class="dropdown">
                                    <button class="btn btn-sm ${preset.id === activePreset?.id ? 'btn-light' : 'btn-outline-secondary'}" 
                                            data-bs-toggle="dropdown" onclick="event.stopPropagation();">
                                        <i class="fas fa-ellipsis-v"></i>
                                    </button>
                                    <ul class="dropdown-menu dropdown-menu-end">
                                        <li><button class="dropdown-item edit-preset-btn" data-preset-id="${preset.id}">
                                            <i class="fas fa-edit me-2"></i>Edit
                                        </button></li>
                                        <li><button class="dropdown-item text-danger delete-preset-btn" data-preset-id="${preset.id}">
                                            <i class="fas fa-trash me-2"></i>Delete
                                        </button></li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Render list of presets
     */
    renderPresetsList(presets, activePreset) {
        return `
            <div class="list-group list-group-flush">
                ${presets.map(preset => `
                    <div class="list-group-item ${preset.id === (activePreset?.id) ? 'active' : ''}" 
                         data-preset-id="${preset.id}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1" style="cursor: pointer;" onclick="window.filterPresets.applyPreset('${preset.id}')">
                                <h6 class="mb-1">${preset.name}</h6>
                                <p class="mb-1 small text-muted">${preset.description}</p>
                                <small class="text-muted">${preset.filters.conditions.length} conditions</small>
                            </div>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-outline-secondary dropdown-toggle" 
                                        data-bs-toggle="dropdown" aria-expanded="false">
                                    <i class="fas fa-ellipsis-v"></i>
                                </button>
                                <ul class="dropdown-menu">
                                    <li><a class="dropdown-item" href="#" onclick="window.filterPresets.showEditModal('${preset.id}')">
                                        <i class="fas fa-edit me-2"></i>Edit
                                    </a></li>
                                    <li><a class="dropdown-item" href="#" onclick="window.filterPresets.showDetailsModal('${preset.id}')">
                                        <i class="fas fa-eye me-2"></i>View Details
                                    </a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item text-danger" href="#" onclick="window.filterPresets.confirmDelete('${preset.id}')">
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
     * Setup event handlers for presets panel
     */
    setupPanelEventHandlers() {
        // Create preset button
        const createBtn = document.getElementById('create-preset-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.showCreateModal());
        }

        // Clear preset button
        const clearBtn = document.getElementById('clear-preset-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearActiveFilter());
        }
    }

    /**
     * Setup global event handlers
     */
    setupEventHandlers() {
        // Any global event handlers can be set up here
    }

    /**
     * Show create preset modal
     */
    showCreateModal() {
        Swal.fire({
            title: 'Create Filter Preset',
            html: `
                <div class="mb-3">
                    <label for="preset-name" class="form-label">Preset Name</label>
                    <input type="text" class="form-control" id="preset-name" placeholder="e.g. High Confidence Breakouts">
                </div>
                <div class="mb-3">
                    <label for="preset-description" class="form-label">Description</label>
                    <textarea class="form-control" id="preset-description" rows="2" 
                              placeholder="Brief description of this filter preset"></textarea>
                </div>
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Advanced filter builder will be available in the next update. For now, creating basic presets.
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'Create',
            preConfirm: () => {
                const name = document.getElementById('preset-name').value.trim();
                const description = document.getElementById('preset-description').value.trim();
                
                if (!name) {
                    Swal.showValidationMessage('Please enter a preset name');
                    return false;
                }
                
                // For now, create a simple high confidence filter
                const filters = {
                    logic: 'AND',
                    conditions: [
                        {
                            field: 'confidence',
                            operator: 'gte',
                            value: 0.75
                        }
                    ]
                };
                
                return { name, description, filters };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.createPreset(result.value.name, result.value.description, result.value.filters)
                    .then(() => {
                        this.showSuccess(`Created filter preset "${result.value.name}"`);
                    })
                    .catch(error => {
                        this.showError(`Failed to create preset: ${error.message}`);
                    });
            }
        });
    }

    /**
     * Show edit preset modal
     */
    showEditModal(presetId) {
        const preset = this.getPreset(presetId);
        if (!preset) return;

        Swal.fire({
            title: 'Edit Filter Preset',
            html: `
                <div class="mb-3">
                    <label for="edit-preset-name" class="form-label">Preset Name</label>
                    <input type="text" class="form-control" id="edit-preset-name" value="${preset.name}">
                </div>
                <div class="mb-3">
                    <label for="edit-preset-description" class="form-label">Description</label>
                    <textarea class="form-control" id="edit-preset-description" rows="2">${preset.description}</textarea>
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'Save Changes',
            preConfirm: () => {
                const name = document.getElementById('edit-preset-name').value.trim();
                const description = document.getElementById('edit-preset-description').value.trim();
                
                if (!name) {
                    Swal.showValidationMessage('Please enter a preset name');
                    return false;
                }
                
                return { name, description };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.updatePreset(presetId, result.value)
                    .then(() => {
                        this.showSuccess(`Updated filter preset "${result.value.name}"`);
                    })
                    .catch(error => {
                        this.showError(`Failed to update preset: ${error.message}`);
                    });
            }
        });
    }

    /**
     * Show preset details modal
     */
    showDetailsModal(presetId) {
        const preset = this.getPreset(presetId);
        if (!preset) return;

        const conditionsHtml = preset.filters.conditions.map(condition => {
            const operator = this.operators[condition.operator];
            const valueStr = Array.isArray(condition.value) ? condition.value.join(', ') : condition.value;
            return `
                <li class="list-group-item d-flex justify-content-between">
                    <span><strong>${condition.field}</strong> ${operator?.label || condition.operator} <em>${valueStr}</em></span>
                </li>
            `;
        }).join('');

        Swal.fire({
            title: `${preset.name}`,
            html: `
                <div class="text-start">
                    <p class="text-muted mb-3">${preset.description}</p>
                    
                    <h6>Filter Logic: <span class="badge bg-primary">${preset.filters.logic}</span></h6>
                    
                    <h6 class="mt-3">Conditions:</h6>
                    <ul class="list-group list-group-flush">
                        ${conditionsHtml}
                    </ul>
                    
                    <div class="row mt-3">
                        <div class="col">
                            <small class="text-muted">
                                <strong>Created:</strong> ${new Date(preset.created_at).toLocaleString()}
                            </small>
                        </div>
                        <div class="col">
                            <small class="text-muted">
                                <strong>Updated:</strong> ${new Date(preset.updated_at).toLocaleString()}
                            </small>
                        </div>
                    </div>
                </div>
            `,
            confirmButtonText: 'Close',
            showCancelButton: false
        });
    }

    /**
     * Confirm preset deletion
     */
    confirmDelete(presetId) {
        const preset = this.getPreset(presetId);
        if (!preset) return;

        Swal.fire({
            title: 'Delete Filter Preset?',
            text: `Are you sure you want to delete "${preset.name}"? This action cannot be undone.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                this.deletePreset(presetId)
                    .then(() => {
                        this.showSuccess(`Deleted filter preset "${preset.name}"`);
                    })
                    .catch(error => {
                        this.showError(`Failed to delete preset: ${error.message}`);
                    });
            }
        });
    }

    /**
     * Save presets to localStorage for offline functionality
     */
    saveToLocalStorage() {
        const data = {
            presets: Object.fromEntries(this.presets),
            activePreset: this.activePreset,
            timestamp: Date.now()
        };
        localStorage.setItem('tickstock-filter-presets', JSON.stringify(data));
    }

    /**
     * Load presets from localStorage
     */
    loadFromLocalStorage() {
        const stored = localStorage.getItem('tickstock-filter-presets');
        if (stored) {
            try {
                const data = JSON.parse(stored);
                this.presets = new Map(Object.entries(data.presets || {}));
                this.activePreset = data.activePreset;
                this.renderPresetsPanel();
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

// Initialize filter presets service when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof window !== 'undefined') {
        window.filterPresets = new FilterPresetsService();
    }
});