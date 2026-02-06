/**
 * Stock Group Selector - Sprint 65
 *
 * Interactive selector for stock groups (ETFs, sectors, themes, universes).
 * Features:
 * - Real-time search filtering
 * - Type-based filtering (checkboxes)
 * - Multi-select with checkboxes
 * - Detail grid display for selected groups
 * - Responsive design
 */

class StockGroupSelector {
    constructor(config) {
        this.containerId = config.containerId;
        this.apiEndpoint = config.apiEndpoint || '/api/stock-groups';
        this.csrfToken = config.csrfToken || '';

        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error(`StockGroupSelector: Container '${this.containerId}' not found`);
            return;
        }

        // State management
        this.allGroups = [];
        this.filteredGroups = [];
        this.selectedGroups = [];
        this.searchTerm = '';
        this.selectedTypes = ['ETF', 'SECTOR', 'THEME', 'UNIVERSE'];

        // Initialize
        this.init();
    }

    async init() {
        console.log('StockGroupSelector: Initializing...');

        // Load data from API
        await this.loadGroups();

        // Render table
        this.renderTable();

        // Setup event handlers
        this.setupEventHandlers();

        console.log('StockGroupSelector: Initialized successfully');
    }

    async loadGroups() {
        try {
            const url = `${this.apiEndpoint}?types=${this.selectedTypes.join(',')}`;
            console.log(`Fetching groups from: ${url}`);

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.allGroups = data.groups || [];
            this.filteredGroups = [...this.allGroups];

            console.log(`Loaded ${this.allGroups.length} stock groups`);

        } catch (error) {
            console.error('Error loading stock groups:', error);
            this.displayError('Failed to load stock groups. Please try again.');
        }
    }

    renderTable() {
        const tbody = this.container.querySelector('.stock-group-table tbody');
        if (!tbody) {
            console.error('Table body not found');
            return;
        }

        // Clear existing rows
        tbody.innerHTML = '';

        // Render filtered groups
        if (this.filteredGroups.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No groups found matching your criteria</td></tr>';
            this.updateFilterBadge();
            return;
        }

        this.filteredGroups.forEach((group, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <input type="checkbox"
                           class="form-check-input group-checkbox"
                           data-index="${index}"
                           data-name="${group.name}"
                           data-type="${group.type}">
                </td>
                <td>${this.escapeHtml(group.name)}</td>
                <td><span class="badge bg-primary">${this.escapeHtml(group.type)}</span></td>
                <td>${this.escapeHtml(group.description || '-')}</td>
                <td style="text-align: right;">${group.member_count}</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>${new Date(group.updated_at).toLocaleDateString()}</td>
            `;
            tbody.appendChild(row);
        });

        // Update count badge
        this.updateFilterBadge();

        // Hide status message
        this.hideStatus();
    }

    setupEventHandlers() {
        // Search bar
        const searchInput = this.container.querySelector('.stock-group-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.handleSearch(e));
        }

        // Type filter checkboxes
        const typeFilters = this.container.querySelectorAll('.type-filter-checkbox');
        typeFilters.forEach(cb => {
            cb.addEventListener('change', (e) => this.handleTypeFilter(e));
        });

        // Select All checkbox
        const selectAllCheckbox = this.container.querySelector('#select-all-checkbox');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => this.handleSelectAll(e));
        }

        // Table checkboxes (event delegation for dynamically rendered content)
        const table = this.container.querySelector('.stock-group-table');
        if (table) {
            table.addEventListener('change', (e) => {
                if (e.target.classList.contains('group-checkbox')) {
                    this.handleCheckboxChange(e);
                }
            });
        }

        // Action buttons
        const confirmBtn = this.container.querySelector('.confirm-selection-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.handleConfirmSelection());
        }

        const clearBtn = this.container.querySelector('.clear-selection-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.handleClearSelection());
        }
    }

    handleSearch(event) {
        this.searchTerm = event.target.value.toLowerCase();
        this.applyFilters();
    }

    handleTypeFilter(event) {
        const type = event.target.value;
        if (event.target.checked) {
            if (!this.selectedTypes.includes(type)) {
                this.selectedTypes.push(type);
            }
        } else {
            this.selectedTypes = this.selectedTypes.filter(t => t !== type);
        }
        this.applyFilters();
    }

    applyFilters() {
        // Filter by type
        let filtered = this.allGroups.filter(group =>
            this.selectedTypes.includes(group.type)
        );

        // Filter by search term (case-insensitive, searches name, type, description)
        if (this.searchTerm) {
            filtered = filtered.filter(group =>
                group.name.toLowerCase().includes(this.searchTerm) ||
                (group.description && group.description.toLowerCase().includes(this.searchTerm)) ||
                group.type.toLowerCase().includes(this.searchTerm)
            );
        }

        this.filteredGroups = filtered;
        this.renderTable();
    }

    handleSelectAll(event) {
        const checkboxes = this.container.querySelectorAll('.group-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = event.target.checked;
        });
        this.updateSelectedGroups();
    }

    handleCheckboxChange(event) {
        this.updateSelectedGroups();

        // Update select-all checkbox state
        const selectAllCheckbox = this.container.querySelector('#select-all-checkbox');
        const allCheckboxes = this.container.querySelectorAll('.group-checkbox');
        const checkedCheckboxes = this.container.querySelectorAll('.group-checkbox:checked');

        if (selectAllCheckbox && allCheckboxes.length > 0) {
            selectAllCheckbox.checked = checkedCheckboxes.length === allCheckboxes.length;
            selectAllCheckbox.indeterminate = checkedCheckboxes.length > 0 && checkedCheckboxes.length < allCheckboxes.length;
        }
    }

    updateSelectedGroups() {
        const checkboxes = this.container.querySelectorAll('.group-checkbox:checked');
        this.selectedGroups = Array.from(checkboxes).map(cb => {
            const name = cb.dataset.name;
            const type = cb.dataset.type;
            return this.filteredGroups.find(g => g.name === name && g.type === type);
        }).filter(g => g !== undefined);

        console.log(`Selected ${this.selectedGroups.length} groups`);
    }

    handleConfirmSelection() {
        if (this.selectedGroups.length === 0) {
            alert('Please select at least one group');
            return;
        }

        console.log('Confirming selection:', this.selectedGroups);
        this.renderDetailGrid(this.selectedGroups);
    }

    handleClearSelection() {
        const checkboxes = this.container.querySelectorAll('.group-checkbox');
        checkboxes.forEach(cb => { cb.checked = false; });
        this.selectedGroups = [];

        // Update select-all checkbox
        const selectAllCheckbox = this.container.querySelector('#select-all-checkbox');
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        }

        // Hide detail grid
        const detailGrid = this.container.querySelector('.stock-group-detail-grid');
        if (detailGrid) {
            detailGrid.style.display = 'none';
        }
    }

    renderDetailGrid(groups) {
        // Find or create detail grid container
        let detailGrid = this.container.querySelector('.stock-group-detail-grid');
        if (!detailGrid) {
            detailGrid = document.createElement('div');
            detailGrid.className = 'stock-group-detail-grid row mt-4';
            this.container.appendChild(detailGrid);
        }

        // Clear existing cards
        detailGrid.innerHTML = '';

        // Create header
        const header = document.createElement('div');
        header.className = 'col-12 mb-3';
        header.innerHTML = `
            <h4><i class="fas fa-info-circle"></i> Selected Groups (${groups.length})</h4>
        `;
        detailGrid.appendChild(header);

        // Create cards for selected groups
        groups.forEach(group => {
            const card = document.createElement('div');
            card.className = 'col-lg-4 col-md-6 mb-3';
            card.innerHTML = `
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0">
                            ${this.escapeHtml(group.name)}
                            <span class="badge bg-primary">${this.escapeHtml(group.type)}</span>
                        </h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Description:</strong> ${this.escapeHtml(group.description || 'N/A')}</p>
                        <p><strong>Member Count:</strong> ${group.member_count} stocks</p>
                        <p><strong>Environment:</strong> ${this.escapeHtml(group.environment)}</p>
                        <p><strong>Last Updated:</strong> ${new Date(group.updated_at).toLocaleDateString()}</p>
                    </div>
                </div>
            `;
            detailGrid.appendChild(card);
        });

        // Show detail grid
        detailGrid.style.display = 'flex';

        // Scroll to detail grid
        detailGrid.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    updateFilterBadge() {
        const badge = this.container.querySelector('.filter-count-badge');
        if (badge) {
            badge.textContent = `${this.filteredGroups.length} groups`;
        }
    }

    displayError(message) {
        const statusEl = this.container.querySelector('.status-message');
        if (statusEl) {
            statusEl.innerHTML = `<i class="fas fa-exclamation-triangle text-danger"></i> ${message}`;
        }
    }

    hideStatus() {
        const statusEl = this.container.querySelector('.status-message');
        if (statusEl) {
            statusEl.style.display = 'none';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export to window for global access
window.StockGroupSelector = StockGroupSelector;
