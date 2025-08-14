// File-level debug flag - set to true to enable optional debug logging
const APP_FILTERS_DEBUG = false;

// ==========================================================================
// USER FILTERS MANAGER CLASS
// ==========================================================================
class UserFiltersManager {
    constructor() {
        this.modal = null;
        this.currentFilters = null;
        this.defaultFilters = this.getDefaultFilters();
        this.isLoading = false;
        this.filterButton = null;
        
        this.init();
    }
    
    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.setupEventListeners();
                this.setupWebSocketFilterListeners();
            });
        } else {
            this.setupEventListeners();
            this.setupWebSocketFilterListeners();
        }
        
        // Load current filters
        this.loadCurrentFilters();
    }
    
    getDefaultFilters() {
        return {
            "version": "1.0",
            "timestamp": new Date().toISOString(),
            "filters": {
                "highlow": {
                    "min_count": 0,
                    "min_volume": 0
                },
                "trends": {
                    "strength": "moderate",
                    "vwap_position": "any_vwap_position",
                    "time_window": "medium",
                    "trend_age": "all",
                    "volume_confirmation": "all_trends"
                },
                "surge": {
                    "magnitude": "moderate",
                    "trigger_type": "price_and_volume",
                    "surge_age": "all",
                    "price_range": ["penny", "low", "mid", "high"]
                }
            },
            "display_preferences": {
                "show_filter_indicators": true,
                "compact_filter_display": false
            }
        };
    }
    
    setupEventListeners() {
        // Get modal and button references
        this.modal = document.getElementById('userFiltersModal');
        this.filterButton = document.querySelector('.filters-btn');
        
        if (!this.modal) {
            console.error('Filter modal not found in DOM');
            return;
        }
        
        if (!this.filterButton) {
            console.error('Filter button not found in DOM');
            return;
        }
        
        // Filter button click handler
        this.filterButton.addEventListener('click', (e) => {
            e.preventDefault();
            this.openModal();
        });
        
        // Modal close handlers
        const closeBtn = this.modal.querySelector('.filter-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }
        
        // Button handlers
        const applyBtn = document.getElementById('applyFiltersBtn');
        const cancelBtn = document.getElementById('cancelFiltersBtn');
        const resetBtn = document.getElementById('resetFiltersBtn');
        
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applyFilters());
        }
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeModal());
        }
        
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetAllFilters());
        }
        
        // Checkbox change handlers for visual feedback
        this.modal.querySelectorAll('.filter-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateCheckboxVisuals(checkbox));
        });
        
        // Click outside to close
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
        
        // Keyboard handlers
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal && this.modal.style.display === 'block') {
                this.closeModal();
            }
        });
        
        if (APP_FILTERS_DEBUG) console.log('Filter event listeners setup complete');
    }
    
    openModal() {
        if (this.isLoading || !this.modal) return;
        
        // Populate modal with current filter values
        this.populateModalFromFilters(this.currentFilters || this.defaultFilters);
        
        // Show modal
        this.modal.style.display = 'block';
        this.modal.classList.add('show');
        this.modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        
        // Focus management
        const firstInput = this.modal.querySelector('select, input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
        
        if (APP_FILTERS_DEBUG) console.log('Filter modal opened');
    }
    
    closeModal() {
        if (!this.modal) return;
        
        this.modal.style.display = 'none';
        this.modal.classList.remove('show');
        this.modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        
        if (APP_FILTERS_DEBUG) console.log('Filter modal closed');
    }
    
    populateModalFromFilters(filterData) {
        if (!filterData || !filterData.filters) {
            console.warn('Invalid filter data, using defaults');
            filterData = this.defaultFilters;
        }
        
        const filters = filterData.filters;
        
        try {
            // High/Low filters
            if (filters.highlow) {
                const minCountSelect = document.getElementById('highlow-min-count');
                const minVolumeSelect = document.getElementById('highlow-min-volume');
                
                if (minCountSelect) minCountSelect.value = filters.highlow.min_count || 0;
                if (minVolumeSelect) minVolumeSelect.value = filters.highlow.min_volume || 0;
            }
            
            // Trend filters - Updated for single selections
            if (filters.trends) {
                // Trend strength dropdown
                const trendStrengthSelect = document.getElementById('trend-strength');
                if (trendStrengthSelect) trendStrengthSelect.value = filters.trends.strength || 'moderate';
                
                // VWAP position dropdown
                const trendVwapSelect = document.getElementById('trend-vwap-position');
                if (trendVwapSelect) trendVwapSelect.value = filters.trends.vwap_position || 'any_vwap_position';
                
                // Time window dropdown
                const trendTimeWindowSelect = document.getElementById('trend-time-window');
                if (trendTimeWindowSelect) trendTimeWindowSelect.value = filters.trends.time_window || 'medium';
                
                // Trend age dropdown
                const trendAgeSelect = document.getElementById('trend-age');
                if (trendAgeSelect) trendAgeSelect.value = filters.trends.trend_age || 'all';
                
                // Volume confirmation dropdown
                const trendVolumeConfirmationSelect = document.getElementById('trend-volume-confirmation');
                if (trendVolumeConfirmationSelect) trendVolumeConfirmationSelect.value = filters.trends.volume_confirmation || 'all_trends';
            }
            
            // Surge filters - Updated for single selections
            if (filters.surge) {
                // Surge magnitude dropdown
                const surgeMagnitudeSelect = document.getElementById('surge-magnitude');
                if (surgeMagnitudeSelect) surgeMagnitudeSelect.value = filters.surge.magnitude || 'moderate';
                
                // Trigger type dropdown
                const surgeTriggerTypeSelect = document.getElementById('surge-trigger-type');
                if (surgeTriggerTypeSelect) surgeTriggerTypeSelect.value = filters.surge.trigger_type || 'price_and_volume';
                
                // Surge age dropdown
                const surgeAgeSelect = document.getElementById('surge-age');
                if (surgeAgeSelect) surgeAgeSelect.value = filters.surge.surge_age || 'all';
                
                // Price range checkboxes (keeping as multi-select)
                this.setCheckboxGroupValues('[value="penny"]', filters.surge.price_range, 'penny');
                this.setCheckboxGroupValues('[value="low"]', filters.surge.price_range, 'low');
                this.setCheckboxGroupValues('[value="mid"]', filters.surge.price_range, 'mid');
                this.setCheckboxGroupValues('[value="high"]', filters.surge.price_range, 'high');
            }
            
            // Update visual states for remaining checkboxes
            this.updateAllCheckboxVisuals();
            
        } catch (error) {
            console.error('Error populating filter modal:', error);
        }
    }
    
    setCheckboxGroupValues(selector, valueArray, targetValue) {
        const checkbox = this.modal.querySelector(selector);
        if (checkbox && Array.isArray(valueArray)) {
            checkbox.checked = valueArray.includes(targetValue);
        }
    }
    
    updateCheckboxVisuals(checkbox) {
        const label = checkbox.closest('.filter-checkbox-label');
        if (label) {
            if (checkbox.checked) {
                label.classList.add('selected');
            } else {
                label.classList.remove('selected');
            }
        }
    }
    
    updateAllCheckboxVisuals() {
        this.modal.querySelectorAll('.filter-checkbox').forEach(checkbox => {
            this.updateCheckboxVisuals(checkbox);
        });
    }
    
    collectFilterData() {
        const filterData = {
            "version": "1.0",
            "timestamp": new Date().toISOString(),
            "filters": {
                "highlow": {
                    "min_count": 0,
                    "min_volume": 0
                },
                "trends": {
                    "strength": "moderate",
                    "vwap_position": "any_vwap_position",
                    "time_window": "medium",
                    "trend_age": "all",
                    "volume_confirmation": "all_trends"
                },
                "surge": {
                    "magnitude": "moderate",
                    "trigger_type": "price_and_volume",
                    "surge_age": "all",
                    "price_range": []
                }
            },
            "display_preferences": {
                "show_filter_indicators": true,
                "compact_filter_display": false
            }
        };
        
        try {
            // Collect High/Low filters
            const minCountSelect = document.getElementById('highlow-min-count');
            const minVolumeSelect = document.getElementById('highlow-min-volume');
            
            if (minCountSelect) filterData.filters.highlow.min_count = parseInt(minCountSelect.value) || 0;
            if (minVolumeSelect) filterData.filters.highlow.min_volume = parseInt(minVolumeSelect.value) || 0;
            
            // Collect Trend filters - Updated for single selections
            const trendStrengthSelect = document.getElementById('trend-strength');
            if (trendStrengthSelect) filterData.filters.trends.strength = trendStrengthSelect.value || 'moderate';
            
            const trendVwapSelect = document.getElementById('trend-vwap-position');
            if (trendVwapSelect) filterData.filters.trends.vwap_position = trendVwapSelect.value || 'any_vwap_position';
            
            const trendTimeWindowSelect = document.getElementById('trend-time-window');
            if (trendTimeWindowSelect) filterData.filters.trends.time_window = trendTimeWindowSelect.value || 'medium';
            
            const trendAgeSelect = document.getElementById('trend-age');
            if (trendAgeSelect) filterData.filters.trends.trend_age = trendAgeSelect.value || 'all';
            
            const trendVolumeConfirmationSelect = document.getElementById('trend-volume-confirmation');
            if (trendVolumeConfirmationSelect) filterData.filters.trends.volume_confirmation = trendVolumeConfirmationSelect.value || 'all_trends';
            
            // Collect Surge filters - Updated for single selections
            const surgeMagnitudeSelect = document.getElementById('surge-magnitude');
            if (surgeMagnitudeSelect) filterData.filters.surge.magnitude = surgeMagnitudeSelect.value || 'moderate';
            
            const surgeTriggerTypeSelect = document.getElementById('surge-trigger-type');
            if (surgeTriggerTypeSelect) filterData.filters.surge.trigger_type = surgeTriggerTypeSelect.value || 'price_and_volume';
            
            const surgeAgeSelect = document.getElementById('surge-age');
            if (surgeAgeSelect) filterData.filters.surge.surge_age = surgeAgeSelect.value || 'all';
            
            // Price range checkboxes (keeping as multi-select)
            filterData.filters.surge.price_range = this.getCheckedValues('[value="penny"], [value="low"], [value="mid"], [value="high"]');
            
        } catch (error) {
            console.error('Error collecting filter data:', error);
            return this.defaultFilters;
        }
        
        return filterData;
    }
    
    getCheckedValues(selector) {
        const checkboxes = this.modal.querySelectorAll(selector);
        const values = [];
        
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                values.push(checkbox.value);
            }
        });
        
        return values;
    }
    
    validateFilterData(filterData) {
        if (!filterData || typeof filterData !== 'object') {
            return false;
        }
        
        if (!filterData.filters || typeof filterData.filters !== 'object') {
            return false;
        }
        
        // Basic structure validation
        const requiredSections = ['highlow', 'trends', 'surge'];
        for (const section of requiredSections) {
            if (!filterData.filters[section]) {
                return false;
            }
        }
        
        return true;
    }

    /**
     * Update the applyFilters method to provide immediate feedback
     */
    async applyFilters() {
        if (this.isLoading) return;
        
        this.setLoadingState(true);
        
        try {
            // Collect filter data from form
            const filterData = this.collectFilterData();
            
            // Validate filter data
            if (!this.validateFilterData(filterData)) {
                this.showNotification('Invalid filter configuration. Please check your selections.', 'error');
                return;
            }
            
            // Immediate UI update before server save
            this.currentFilters = filterData;
            this.updateFilterButtonDisplay(filterData);
            this.updateFilterIndicators(filterData);
            
            // Clear existing data to show immediate filter effect
            this.clearEventDisplays();
            
            // Show immediate feedback
            this.showNotification('Applying filters...', 'info');
            
            // Save to server
            const success = await this.saveFiltersToServer(filterData);
            
            if (success) {
                // Show success message
                this.showNotification('Filters applied successfully! Data will update momentarily.', 'success');
                
                // Close modal
                this.closeModal();
                
                // Request fresh data with new filters
                this.requestFilteredDataUpdate();
                
                if (APP_FILTERS_DEBUG) console.log('Filters applied with immediate effect:', filterData);
            } else {
                // Revert UI changes if save failed
                this.loadCurrentFilters(); // This will reset the UI
                this.showNotification('Failed to save filters. Changes reverted.', 'error');
            }
            
        } catch (error) {
            console.error('Error applying filters:', error);
            this.loadCurrentFilters(); // Reset UI on error
            this.showNotification('Error applying filters. Changes reverted.', 'error');
        } finally {
            this.setLoadingState(false);
        }
    }

    /**
     * Clear event displays to show immediate filter effect
     */
    clearEventDisplays() {
        const eventLists = [
            'highs-list',
            'lows-list', 
            'uptrend-list',
            'downtrend-list',
            'surging-up-list',
            'surging-down-list'
        ];
        
        eventLists.forEach(listId => {
            const listElement = document.getElementById(listId);
            if (listElement) {
                // Fade out existing content
                listElement.style.opacity = '0.3';
                
                // Add loading indicator
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'filter-loading-indicator';
                loadingDiv.innerHTML = '<span>Applying filters...</span>';
                loadingDiv.style.cssText = `
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-style: italic;
                `;
                
                // Clear content and add loading indicator
                listElement.innerHTML = '';
                listElement.appendChild(loadingDiv);
            }
        });
    }

    /**
     * Request fresh data update after filter changes
     */
    requestFilteredDataUpdate() {
        // If WebSocket connection is available, we don't need to manually refresh
        // The backend will automatically apply new filters to incoming data
        
        // However, we can request an immediate refresh if needed
        if (typeof socket !== 'undefined' && socket.connected) {
            // Request immediate data refresh (this would need to be implemented on backend)
            socket.emit('request_filtered_data_refresh');
            
            if (APP_FILTERS_DEBUG) console.log('Requested filtered data refresh via WebSocket');
        }
        
        // Set a timeout to restore normal opacity even if no new data comes
        setTimeout(() => {
            const eventLists = document.querySelectorAll('.events-list');
            eventLists.forEach(list => {
                list.style.opacity = '1';
                
                // Remove loading indicators
                const loadingIndicators = list.querySelectorAll('.filter-loading-indicator');
                loadingIndicators.forEach(indicator => indicator.remove());
            });
        }, 3000); // 3 second timeout
    }

    async saveFiltersToServer(filterData) {
        try {
            if (APP_FILTERS_DEBUG) {
                console.log('Attempting to save filters to server:', filterData);
                console.log('CSRF Token:', this.getCSRFToken());
            }
            
            // Ensure proper data structure
            if (!filterData || !filterData.filters) {
                console.error('Invalid filter data structure before sending:', filterData);
                throw new Error('Invalid filter data structure - missing filters');
            }
            
            const requestBody = {
                filter_data: filterData,
                filter_name: 'default'
            };
            
            if (APP_FILTERS_DEBUG) {
                console.log('Request body structure:', {
                    filter_data_keys: Object.keys(requestBody.filter_data),
                    filter_data_filters_keys: Object.keys(requestBody.filter_data.filters || {}),
                    filter_name: requestBody.filter_name
                });
            }
            
            const response = await fetch('/api/user-filters', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(requestBody)
            });
            
            if (APP_FILTERS_DEBUG) {
                console.log('Response status:', response.status);
                console.log('Response headers:', response.headers);
            }
            
            // Check if response is actually JSON
            const contentType = response.headers.get('content-type');
            if (APP_FILTERS_DEBUG) console.log('Content-Type:', contentType);
            
            if (!contentType || !contentType.includes('application/json')) {
                // Server returned HTML instead of JSON
                const htmlResponse = await response.text();
                if (APP_FILTERS_DEBUG) console.error('Server returned HTML instead of JSON:', htmlResponse.substring(0, 500));
                
                // Check if it's a login redirect
                if (htmlResponse.includes('login') || htmlResponse.includes('Login')) {
                    throw new Error('Authentication required - please refresh the page and log in');
                }
                
                // Check if it's a 404 or error page
                if (htmlResponse.includes('404') || htmlResponse.includes('Not Found')) {
                    throw new Error('API endpoint not found - the /api/user-filters route may not be registered');
                }
                
                throw new Error(`Server returned HTML instead of JSON. Status: ${response.status}. Content: ${htmlResponse.substring(0, 200)}`);
            }
            
            const result = await response.json();
            if (APP_FILTERS_DEBUG) console.log('JSON response:', result);
            
            if (response.ok && result.success) {
                if (APP_FILTERS_DEBUG) console.log('Filters saved to database successfully');
                
                // Additional success logging
                if (result.cache_updated && APP_FILTERS_DEBUG) {
                    console.log('Filter cache updated successfully');
                }
                
                if (result.user_id && APP_FILTERS_DEBUG) {
                    console.log(`Filters applied for user ID: ${result.user_id}`);
                }
                
                return true;
            } else {
                console.error('Server error saving filters:', result.error || 'Unknown error');
                
                // More specific error handling
                if (result.error && result.error.includes('validation') && APP_FILTERS_DEBUG) {
                    console.error('Filter validation failed on server');
                    console.error('Sent filter data:', filterData);
                }
                
                throw new Error(result.error || `Server error: ${response.status}`);
            }
            
        } catch (error) {
            console.error('Error saving filters to server:', error);
            
            // More specific error messages
            if (error.message.includes('Authentication required')) {
                console.error('Authentication issue detected');
                this.showNotification('Please refresh the page and log in again.', 'error');
                return false;
            }
            
            if (error.message.includes('API endpoint not found')) {
                console.error('API route registration issue detected');
                this.showNotification('Server configuration error. Please contact support.', 'error');
            }
            
            if (error.message.includes('validation')) {
                console.error('Filter validation failed');
                this.showNotification('Filter configuration is invalid. Please try again.', 'error');
            }
            
            // Fallback to localStorage if API fails
            try {
                localStorage.setItem('tickstock_user_filters', JSON.stringify(filterData));
                console.warn('Saved filters to localStorage as fallback');
                this.showNotification('Filters saved locally (server unavailable)', 'warning');
                return true;
            } catch (fallbackError) {
                console.error('Error saving to localStorage fallback:', fallbackError);
                this.showNotification('Failed to save filters. Please try again.', 'error');
                return false;
            }
        }
    }
    
    async loadCurrentFilters() {
        try {
            // Load from database via API
            const response = await fetch('/api/user-filters?filter_name=default', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                
                if (result.success && result.filter_data) {
                    this.currentFilters = result.filter_data;
                    
                    // Validate loaded filters
                    if (!this.validateFilterData(this.currentFilters)) {
                        console.warn('Invalid filters loaded from database, using defaults');
                        this.currentFilters = this.defaultFilters;
                    }
                    
                    if (APP_FILTERS_DEBUG) console.log('Filters loaded from database:', this.currentFilters);
                } else {
                    this.currentFilters = this.defaultFilters;
                    if (APP_FILTERS_DEBUG) console.log('No filters found in database, using defaults');
                }
            } else {
                // Fallback to localStorage if API fails
                console.warn('API failed, trying localStorage fallback');
                const savedFilters = localStorage.getItem('tickstock_user_filters');
                
                if (savedFilters) {
                    this.currentFilters = JSON.parse(savedFilters);
                    
                    if (!this.validateFilterData(this.currentFilters)) {
                        console.warn('Invalid saved filters, using defaults');
                        this.currentFilters = this.defaultFilters;
                    }
                } else {
                    this.currentFilters = this.defaultFilters;
                }
            }
            
            // Update UI
            this.updateFilterButtonDisplay(this.currentFilters);
            this.updateFilterIndicators(this.currentFilters);
            
            if (APP_FILTERS_DEBUG) console.log('Final loaded filters:', this.currentFilters);
            
        } catch (error) {
            console.error('Error loading filters:', error);
            
            // Fallback to localStorage and then defaults
            try {
                const savedFilters = localStorage.getItem('tickstock_user_filters');
                if (savedFilters) {
                    this.currentFilters = JSON.parse(savedFilters);
                    if (!this.validateFilterData(this.currentFilters)) {
                        this.currentFilters = this.defaultFilters;
                    }
                } else {
                    this.currentFilters = this.defaultFilters;
                }
            } catch (fallbackError) {
                console.error('Error loading from localStorage:', fallbackError);
                this.currentFilters = this.defaultFilters;
            }
            
            this.updateFilterButtonDisplay(this.currentFilters);
            this.updateFilterIndicators(this.currentFilters);
        }
    }
    
    getCSRFToken() {
        // Get CSRF token from meta tag
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        return csrfMeta ? csrfMeta.getAttribute('content') : '';
    }
    
    // Test API connectivity
    async testAPIConnectivity() {
        try {
            if (APP_FILTERS_DEBUG) console.log('Testing API connectivity...');
            
            // Test the debug route first
            const testResponse = await fetch('/api/test-filters', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (APP_FILTERS_DEBUG) console.log('Test API response status:', testResponse.status);
            
            if (testResponse.ok) {
                const testResult = await testResponse.json();
                if (APP_FILTERS_DEBUG) console.log('Test API successful:', testResult);
                return true;
            } else {
                const errorText = await testResponse.text();
                if (APP_FILTERS_DEBUG) console.error('Test API failed:', errorText);
                return false;
            }
            
        } catch (error) {
            if (APP_FILTERS_DEBUG) console.error('API connectivity test failed:', error);
            return false;
        }
    }

    resetAllFilters() {
        if (this.isLoading) return;
        
        // Reset to default filters
        this.populateModalFromFilters(this.defaultFilters);
        
        if (APP_FILTERS_DEBUG) console.log('Filters reset to defaults');
    }
    
    /**
     * Update filter button with real-time status
     */
    updateFilterButtonDisplay(filterData) {
        if (!this.filterButton) return;
        
        const filterStatus = this.getFilterSummaryText(filterData);
        const statusSpan = this.filterButton.querySelector('.current-filters');
        
        if (statusSpan) {
            statusSpan.textContent = filterStatus;
            
            // Add visual indication if filters are active
            if (filterStatus !== 'All Events') {
                statusSpan.style.color = 'var(--color-primary, #007bff)';
                statusSpan.style.fontWeight = '600';
                
                // Add a small indicator icon
                if (!this.filterButton.querySelector('.filter-active-icon')) {
                    const icon = document.createElement('span');
                    icon.className = 'filter-active-icon';
                    icon.innerHTML = '●';
                    icon.style.cssText = `
                        color: var(--color-primary, #007bff);
                        margin-left: 4px;
                        font-size: 8px;
                        vertical-align: middle;
                    `;
                    statusSpan.appendChild(icon);
                }
            } else {
                statusSpan.style.color = '';
                statusSpan.style.fontWeight = '';
                
                // Remove active icon
                const activeIcon = this.filterButton.querySelector('.filter-active-icon');
                if (activeIcon) {
                    activeIcon.remove();
                }
            }
        }
    }
    
    getFilterSummaryText(filterData) {
        if (!filterData || !filterData.filters) {
            return 'All Events';
        }
        
        const filters = filterData.filters;
        const activeFilters = [];
        
        // Check high/low filters
        if (filters.highlow) {
            if (filters.highlow.min_count > 0) {
                activeFilters.push(`Count:${filters.highlow.min_count}+`);
            }
            if (filters.highlow.min_volume > 0) {
                const volumeText = filters.highlow.min_volume >= 1000000 ? 
                    `${filters.highlow.min_volume / 1000000}M+` : 
                    `${filters.highlow.min_volume / 1000}K+`;
                activeFilters.push(`Vol:${volumeText}`);
            }
        }
        
        // Check trend filters
        if (filters.trends) {
            if (filters.trends.strength && filters.trends.strength.length < 3) {
                activeFilters.push('Trend Filter');
            }
            if (filters.trends.trend_age !== 'all') {
                activeFilters.push('Age Filter');
            }
        }
        
        // Check surge filters
        if (filters.surge) {
            if (filters.surge.magnitude && filters.surge.magnitude.length < 3) {
                activeFilters.push('Surge Filter');
            }
            if (filters.surge.price_range && filters.surge.price_range.length < 4) {
                activeFilters.push('Price Range');
            }
        }
        
        if (activeFilters.length === 0) {
            return 'All Events';
        } else if (activeFilters.length === 1) {
            return activeFilters[0];
        } else if (activeFilters.length <= 3) {
            return activeFilters.join(', ');
        } else {
            return `${activeFilters.length} Filters Active`;
        }
    }
    
    /**
     * Enhanced filter indicator updates with detailed status
     */
    updateFilterIndicators(filterData) {
        // Update grid headers with detailed filter indicators
        const headers = [
            { 
                selector: '#highs-header-container h3, .highs-section h3', 
                category: 'highlow',
                label: 'New Highs'
            },
            { 
                selector: '#lows-header-container h3, .lows-section h3', 
                category: 'highlow',
                label: 'New Lows'
            },
            { 
                selector: '#uptrend-header-container h3, .uptrend-section h3', 
                category: 'trends',
                label: 'Uptrend Stocks'
            },
            { 
                selector: '#downtrend-header-container h3, .downtrend-section h3', 
                category: 'trends',
                label: 'Downtrend Stocks'
            },
            { 
                selector: '#surging-up-header-container h3, .surging-up-section h3', 
                category: 'surge',
                label: 'Surging Up Stocks'
            },
            { 
                selector: '#surging-down-header-container h3, .surging-down-section h3', 
                category: 'surge',
                label: 'Surging Down Stocks'
            }
        ];
        
        headers.forEach(({ selector, category, label }) => {
            const headerElement = document.querySelector(selector);
            if (headerElement) {
                // Remove existing filter indicators
                const existingIndicator = headerElement.querySelector('.filter-indicator');
                if (existingIndicator) {
                    existingIndicator.remove();
                }
                
                // Add new filter indicator if filters are active
                if (this.hasActiveFilters(filterData, category)) {
                    const indicator = document.createElement('span');
                    indicator.className = 'filter-indicator active';
                    indicator.textContent = '(Filtered)';
                    
                    // Create detailed tooltip with active filters
                    const tooltip = this.createFilterTooltip(filterData, category);
                    indicator.title = tooltip;
                    
                    // Add styling
                    indicator.style.cssText = `
                        font-size: 0.8em;
                        color: var(--color-primary, #007bff);
                        font-weight: 600;
                        margin-left: 8px;
                        padding: 2px 6px;
                        background: rgba(0, 123, 255, 0.1);
                        border-radius: 3px;
                        cursor: help;
                    `;
                    
                    headerElement.appendChild(indicator);
                }
            }
        });
    }

    /**
     * Create detailed filter tooltip
     */
    createFilterTooltip(filterData, category) {
        if (!filterData || !filterData.filters || !filterData.filters[category]) {
            return 'Filters applied';
        }
        
        const categoryFilters = filterData.filters[category];
        const activeFilters = [];
        
        switch (category) {
            case 'highlow':
                if (categoryFilters.min_count > 0) {
                    activeFilters.push(`Minimum Count: ${categoryFilters.min_count}`);
                }
                if (categoryFilters.min_volume > 0) {
                    const volumeText = categoryFilters.min_volume >= 1000000 ? 
                        `${(categoryFilters.min_volume / 1000000).toFixed(1)}M` : 
                        `${(categoryFilters.min_volume / 1000).toFixed(0)}K`;
                    activeFilters.push(`Minimum Volume: ${volumeText}`);
                }
                break;
                
            case 'trends':
                if (categoryFilters.strength !== 'moderate') {
                    activeFilters.push(`Strength: ${categoryFilters.strength}`);
                }
                if (categoryFilters.vwap_position !== 'any_vwap_position') {
                    activeFilters.push(`VWAP Position: ${categoryFilters.vwap_position.replace('_', ' ')}`);
                }
                if (categoryFilters.time_window !== 'medium') {
                    activeFilters.push(`Time Window: ${categoryFilters.time_window}`);
                }
                if (categoryFilters.trend_age !== 'all') {
                    activeFilters.push(`Age: ${categoryFilters.trend_age}`);
                }
                if (categoryFilters.volume_confirmation !== 'all_trends') {
                    activeFilters.push(`Volume: ${categoryFilters.volume_confirmation.replace('_', ' ')}`);
                }
                break;
                
            case 'surge':
                if (categoryFilters.magnitude !== 'moderate') {
                    activeFilters.push(`Magnitude: ${categoryFilters.magnitude}`);
                }
                if (categoryFilters.trigger_type !== 'price_and_volume') {
                    activeFilters.push(`Trigger: ${categoryFilters.trigger_type.replace('_', ' ')}`);
                }
                if (categoryFilters.surge_age !== 'all') {
                    activeFilters.push(`Age: ${categoryFilters.surge_age}`);
                }
                if (categoryFilters.price_range && categoryFilters.price_range.length < 4) {
                    activeFilters.push(`Price Range: ${categoryFilters.price_range.join(', ')}`);
                }
                break;
        }
        
        if (activeFilters.length === 0) {
            return 'Filters applied';
        }
        
        return `Active Filters:\n${activeFilters.join('\n')}`;
    }

    hasActiveFilters(filterData, category) {
        if (!filterData || !filterData.filters || !filterData.filters[category]) {
            return false;
        }
        
        const categoryFilters = filterData.filters[category];
        
        switch (category) {
            case 'highlow':
                return categoryFilters.min_count > 0 || categoryFilters.min_volume > 0;
                
            case 'trends':
                return categoryFilters.strength !== 'moderate' ||  // Default is moderate
                       categoryFilters.vwap_position !== 'any_vwap_position' ||  // Default is any
                       categoryFilters.time_window !== 'medium' ||  // Default is medium
                       categoryFilters.trend_age !== 'all' ||
                       categoryFilters.volume_confirmation !== 'all_trends';  // Default is all_trends
                       
            case 'surge':
                return categoryFilters.magnitude !== 'moderate' ||  // Default is moderate
                       categoryFilters.trigger_type !== 'price_and_volume' ||  // Default is price_and_volume
                       categoryFilters.surge_age !== 'all' ||
                       (categoryFilters.price_range && categoryFilters.price_range.length < 4);  // Default is all 4 selected
                       
            default:
                return false;
        }
    }
    
    setLoadingState(loading) {
        this.isLoading = loading;
        
        if (!this.modal) return;
        
        const applyBtn = document.getElementById('applyFiltersBtn');
        const cancelBtn = document.getElementById('cancelFiltersBtn');
        const resetBtn = document.getElementById('resetFiltersBtn');
        
        if (loading) {
            this.modal.classList.add('loading');
            if (applyBtn) {
                applyBtn.disabled = true;
                applyBtn.textContent = 'Applying...';
            }
            if (cancelBtn) cancelBtn.disabled = true;
            if (resetBtn) resetBtn.disabled = true;
        } else {
            this.modal.classList.remove('loading');
            if (applyBtn) {
                applyBtn.disabled = false;
                applyBtn.textContent = 'Apply Filters';
            }
            if (cancelBtn) cancelBtn.disabled = false;
            if (resetBtn) resetBtn.disabled = false;
        }
        
        document.body.style.cursor = loading ? 'wait' : '';
    }
    
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
            max-width: 300px;
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
    
    // Getter for current filters (for integration with other modules)
    getCurrentFilters() {
        return this.currentFilters || this.defaultFilters;
    }
    
    // Method to programmatically update filters (for integration)
    updateFilters(newFilterData) {
        if (this.validateFilterData(newFilterData)) {
            this.currentFilters = newFilterData;
            this.updateFilterButtonDisplay(newFilterData);
            this.updateFilterIndicators(newFilterData);
            return true;
        }
        return false;
    }

    /**
     * Listen for WebSocket events related to filtering
     */
    setupWebSocketFilterListeners() {
        if (typeof socket !== 'undefined') {
            // Listen for filter update confirmations
            socket.on('filters_updated', (data) => {
                if (data.success) {
                    this.showNotification('Filters updated successfully!', 'success');
                    
                    // Restore normal display opacity
                    const eventLists = document.querySelectorAll('.events-list');
                    eventLists.forEach(list => {
                        list.style.opacity = '1';
                        
                        // Remove loading indicators
                        const loadingIndicators = list.querySelectorAll('.filter-loading-indicator');
                        loadingIndicators.forEach(indicator => indicator.remove());
                    });
                }
            });
            
            // Listen for filtered data
            socket.on('dual_universe_stock_data', (data) => {
                // Data is already filtered by backend, just restore normal display
                const eventLists = document.querySelectorAll('.events-list');
                eventLists.forEach(list => {
                    if (list.style.opacity === '0.3') {
                        list.style.opacity = '1';
                        
                        // Remove loading indicators
                        const loadingIndicators = list.querySelectorAll('.filter-loading-indicator');
                        loadingIndicators.forEach(indicator => indicator.remove());
                    }
                });
            });
            
            if (APP_FILTERS_DEBUG) console.log('WebSocket filter listeners setup complete');
        }
    }
}

// ==========================================================================
// GLOBAL INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the User Filters Manager
    window.filtersManager = new UserFiltersManager();
    
    if (APP_FILTERS_DEBUG) console.log('User Filters Manager initialized and available globally');
});