/**
 * Historical Data Management - Job Queue Interface
 * Handles job submission to TickStockPL via Redis and monitors job progress
 */

class HistoricalDataManager {
    constructor() {
        this.activeJobs = new Map();
        this.pollIntervals = new Map();
        this.maxPollDuration = 300000; // 5 minutes max polling
        this.pollFrequency = 1000; // Poll every second

        this.initializeElements();
        this.attachEventListeners();
        this.initializeRedisStatus();
        this.initializeUniverseHandlers();
    }

    initializeElements() {
        // Form elements
        this.symbolsInput = document.getElementById('symbols');
        this.yearsSelect = document.getElementById('years');
        this.timespanSelect = document.getElementById('timespan');
        this.loadTypeRadios = document.querySelectorAll('input[name="load_type"]');

        // Progress display elements
        this.jobStatusContainer = document.getElementById('job-status-container');
        this.jobStatusText = document.getElementById('job-status');
        this.progressBar = document.getElementById('progress-bar');
        this.activeJobsList = document.getElementById('active-jobs');

        // Buttons
        this.submitButton = document.getElementById('submit-load');
        this.testRedisButton = document.getElementById('test-redis');

        // Form sections
        this.symbolsSection = document.getElementById('symbols-section');
        this.universeSection = document.getElementById('universe-section');
        this.multiTimeframeSection = document.getElementById('multi-timeframe-section');
    }

    attachEventListeners() {
        // Load type radio buttons
        this.loadTypeRadios.forEach(radio => {
            radio.addEventListener('change', () => this.handleLoadTypeChange());
        });

        // Submit button
        if (this.submitButton) {
            this.submitButton.addEventListener('click', () => this.submitDataLoad());
        }

        // Test Redis button
        if (this.testRedisButton) {
            this.testRedisButton.addEventListener('click', () => this.testRedisConnection());
        }

        // Bulk operation buttons
        document.querySelectorAll('.bulk-operation').forEach(button => {
            button.addEventListener('click', (e) => this.handleBulkOperation(e));
        });
    }

    handleLoadTypeChange() {
        const selectedType = document.querySelector('input[name="load_type"]:checked')?.value;

        // Hide all sections
        if (this.symbolsSection) this.symbolsSection.style.display = 'none';
        if (this.universeSection) this.universeSection.style.display = 'none';
        if (this.multiTimeframeSection) this.multiTimeframeSection.style.display = 'none';

        // Show relevant section
        switch (selectedType) {
            case 'symbols':
                if (this.symbolsSection) this.symbolsSection.style.display = 'block';
                break;
            case 'universe':
                if (this.universeSection) this.universeSection.style.display = 'block';
                break;
            case 'multi_timeframe':
                if (this.multiTimeframeSection) this.multiTimeframeSection.style.display = 'block';
                break;
        }
    }

    async submitDataLoad() {
        const loadType = document.querySelector('input[name="load_type"]:checked')?.value;

        let requestData = {};

        switch (loadType) {
            case 'symbols':
                const symbolsText = document.getElementById('symbols')?.value || '';
                const symbols = symbolsText.split(',').map(s => s.trim().toUpperCase()).filter(s => s);

                if (symbols.length === 0) {
                    this.showError('Please enter at least one symbol');
                    return;
                }

                requestData = {
                    job_type: 'historical_load',
                    symbols: symbols,
                    years: parseInt(document.getElementById('years')?.value || '1'),
                    timespan: document.getElementById('timespan')?.value || 'day'
                };
                break;

            case 'universe':
                requestData = {
                    job_type: 'universe_seed',
                    universe_type: document.getElementById('universe_type')?.value || 'SP500',
                    years: parseInt(document.getElementById('universe_years')?.value || '1')
                };
                break;

            case 'multi_timeframe':
                const multiSymbolsText = document.getElementById('multi_symbols')?.value || '';
                const multiSymbols = multiSymbolsText.split(',').map(s => s.trim().toUpperCase()).filter(s => s);

                if (multiSymbols.length === 0) {
                    this.showError('Please enter at least one symbol');
                    return;
                }

                const selectedTimeframes = [];
                document.querySelectorAll('input[name="timeframes"]:checked').forEach(cb => {
                    selectedTimeframes.push(cb.value);
                });

                if (selectedTimeframes.length === 0) {
                    selectedTimeframes.push('hour', 'day'); // Default timeframes
                }

                requestData = {
                    job_type: 'multi_timeframe_load',
                    symbols: multiSymbols,
                    timeframes: selectedTimeframes,
                    years: parseInt(document.getElementById('multi_years')?.value || '1')
                };
                break;

            default:
                this.showError('Please select a load type');
                return;
        }

        // Submit job to backend
        try {
            this.submitButton.disabled = true;
            this.submitButton.textContent = 'Submitting...';

            const response = await fetch('/api/admin/historical-data/load', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(`Job submitted successfully! Job ID: ${result.job_id.substring(0, 8)}...`);
                this.startPollingJobStatus(result.job_id);
                this.addToActiveJobs(result.job_id, requestData);
            } else {
                this.showError(result.message || 'Failed to submit job');
            }
        } catch (error) {
            console.error('Error submitting job:', error);
            this.showError('Failed to submit job: ' + error.message);
        } finally {
            this.submitButton.disabled = false;
            this.submitButton.textContent = 'Submit Load Job';
        }
    }

    startPollingJobStatus(jobId) {
        // Show status container
        if (this.jobStatusContainer) {
            this.jobStatusContainer.style.display = 'block';
        }

        // Clear any existing interval for this job
        if (this.pollIntervals.has(jobId)) {
            clearInterval(this.pollIntervals.get(jobId));
        }

        let pollCount = 0;
        const maxPolls = this.maxPollDuration / this.pollFrequency;

        const interval = setInterval(async () => {
            pollCount++;

            try {
                const response = await fetch(`/api/admin/job-status/${jobId}`);
                const status = await response.json();

                if (status.success) {
                    this.updateJobStatus(jobId, status);

                    // Stop polling if job is complete
                    if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                        clearInterval(interval);
                        this.pollIntervals.delete(jobId);

                        if (status.status === 'completed') {
                            this.showSuccess(`Job ${jobId.substring(0, 8)} completed successfully!`);
                        } else if (status.status === 'failed') {
                            this.showError(`Job ${jobId.substring(0, 8)} failed: ${status.message}`);
                        }

                        // Remove from active jobs after a delay
                        setTimeout(() => {
                            this.removeFromActiveJobs(jobId);
                        }, 5000);
                    }
                } else if (response.status === 404) {
                    // Job not found or expired
                    clearInterval(interval);
                    this.pollIntervals.delete(jobId);
                    this.updateJobStatus(jobId, {
                        status: 'expired',
                        message: 'Job status expired or not found',
                        progress: 100
                    });
                }
            } catch (error) {
                console.error(`Error polling job ${jobId}:`, error);
            }

            // Stop polling after max duration
            if (pollCount >= maxPolls) {
                clearInterval(interval);
                this.pollIntervals.delete(jobId);
                this.updateJobStatus(jobId, {
                    status: 'timeout',
                    message: 'Polling timeout - job may still be running',
                    progress: -1
                });
            }
        }, this.pollFrequency);

        this.pollIntervals.set(jobId, interval);
    }

    updateJobStatus(jobId, status) {
        // Update main status display if this is the most recent job
        if (this.jobStatusText && this.activeJobs.size > 0) {
            const mostRecentJob = Array.from(this.activeJobs.keys()).pop();
            if (jobId === mostRecentJob) {
                this.jobStatusText.textContent = `${status.status}: ${status.message || ''}`;

                if (this.progressBar && status.progress !== undefined && status.progress >= 0) {
                    this.progressBar.style.width = `${status.progress}%`;
                    this.progressBar.textContent = `${status.progress}%`;
                    this.progressBar.setAttribute('aria-valuenow', status.progress);
                }
            }
        }

        // Update in active jobs list
        const jobElement = document.getElementById(`job-${jobId}`);
        if (jobElement) {
            const statusBadge = jobElement.querySelector('.job-status-badge');
            const progressText = jobElement.querySelector('.job-progress');

            if (statusBadge) {
                statusBadge.textContent = status.status;
                statusBadge.className = `job-status-badge status-${status.status}`;
            }

            if (progressText && status.progress >= 0) {
                progressText.textContent = `${status.progress}%`;
            }

            if (status.message) {
                const messageElement = jobElement.querySelector('.job-message');
                if (messageElement) {
                    messageElement.textContent = status.message;
                }
            }
        }
    }

    addToActiveJobs(jobId, jobData) {
        this.activeJobs.set(jobId, jobData);

        if (!this.activeJobsList) return;

        const jobElement = document.createElement('div');
        jobElement.id = `job-${jobId}`;
        jobElement.className = 'job-card';
        jobElement.innerHTML = `
            <div class="job-header">
                <span class="job-id">${jobId.substring(0, 8)}...</span>
                <span class="job-status-badge status-submitted">submitted</span>
            </div>
            <div class="job-details">
                <div class="job-type">${jobData.job_type}</div>
                <div class="job-progress">0%</div>
                <div class="job-message">Job submitted to processing queue</div>
            </div>
            <div class="job-actions">
                <button class="btn btn-sm btn-danger cancel-job" data-job-id="${jobId}">
                    Cancel
                </button>
            </div>
        `;

        // Add cancel button handler
        const cancelButton = jobElement.querySelector('.cancel-job');
        if (cancelButton) {
            cancelButton.addEventListener('click', () => this.cancelJob(jobId));
        }

        this.activeJobsList.appendChild(jobElement);
    }

    removeFromActiveJobs(jobId) {
        this.activeJobs.delete(jobId);

        const jobElement = document.getElementById(`job-${jobId}`);
        if (jobElement) {
            jobElement.style.opacity = '0.5';
            setTimeout(() => {
                jobElement.remove();

                // Hide status container if no active jobs
                if (this.activeJobs.size === 0 && this.jobStatusContainer) {
                    this.jobStatusContainer.style.display = 'none';
                }
            }, 1000);
        }
    }

    async cancelJob(jobId) {
        try {
            const response = await fetch(`/admin/historical-data/job/${jobId}/cancel`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(`Cancellation requested for job ${jobId.substring(0, 8)}...`);
            } else {
                this.showError('Failed to cancel job');
            }
        } catch (error) {
            console.error('Error cancelling job:', error);
            this.showError('Failed to cancel job');
        }
    }

    async handleBulkOperation(event) {
        const operation = event.target.dataset.operation;

        if (!operation) return;

        const confirmMessage = `Are you sure you want to ${operation.replace(/_/g, ' ')}?`;
        if (!confirm(confirmMessage)) return;

        try {
            const response = await fetch('/admin/historical-data/bulk-operations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: `operation=${operation}`
            });

            if (response.ok) {
                this.showSuccess(`Bulk operation '${operation}' submitted successfully`);
                // Reload page to show updated job list
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                this.showError('Bulk operation failed');
            }
        } catch (error) {
            console.error('Error executing bulk operation:', error);
            this.showError('Failed to execute bulk operation');
        }
    }

    async testRedisConnection() {
        try {
            const response = await fetch('/admin/historical-data/test-redis');
            const result = await response.json();

            if (result.success) {
                let message = `Redis: ${result.redis}\n`;
                message += `TickStockPL: ${result.tickstockpl}\n`;
                message += `Queue Depth: ${result.queue_depth}`;

                this.showSuccess(message);

                // Update Redis status indicator if exists
                const redisIndicator = document.getElementById('redis-status');
                if (redisIndicator) {
                    redisIndicator.className = 'status-indicator status-connected';
                    redisIndicator.textContent = 'Redis Connected';
                }

                const tickstockIndicator = document.getElementById('tickstockpl-status');
                if (tickstockIndicator) {
                    const isConnected = result.tickstockpl === 'Connected';
                    tickstockIndicator.className = `status-indicator status-${isConnected ? 'connected' : 'disconnected'}`;
                    tickstockIndicator.textContent = `TickStockPL ${result.tickstockpl}`;
                }
            } else {
                this.showError(`Redis connection test failed: ${result.error}`);
            }
        } catch (error) {
            console.error('Error testing Redis:', error);
            this.showError('Failed to test Redis connection');
        }
    }

    async initializeRedisStatus() {
        // Test Redis connection on page load
        await this.testRedisConnection();

        // Periodically check Redis status
        setInterval(() => {
            this.testRedisConnection();
        }, 30000); // Check every 30 seconds
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        // Create notification element if it doesn't exist
        let notification = document.getElementById('notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'notification';
            document.body.appendChild(notification);
        }

        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);
    }

    getCSRFToken() {
        // Try to get CSRF token from meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) return metaTag.content;

        // Try to get from cookie
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrf_token='));

        if (cookieValue) {
            return cookieValue.split('=')[1];
        }

        return '';
    }

    /**
     * Load available universes from backend and populate dropdown
     */
    async loadUniverses() {
        const select = document.getElementById('universe-select');

        try {
            if (!select) {
                console.error('Universe select element not found in DOM');
                return;
            }

            console.log('Fetching universes from /admin/historical-data/universes...');
            const response = await fetch('/admin/historical-data/universes');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Universes response:', data);

            select.innerHTML = '<option value="">Select a universe...</option>';

            if (data.error) {
                throw new Error(data.error);
            }

            if (data.universes && data.universes.length > 0) {
                console.log(`Loading ${data.universes.length} universes into dropdown`);

                data.universes.forEach(universe => {
                    const option = document.createElement('option');
                    option.value = universe.key;
                    option.textContent = `${universe.name} (${universe.symbol_count} symbols)`;
                    option.dataset.symbolCount = universe.symbol_count;
                    option.dataset.universeName = universe.name;
                    select.appendChild(option);
                });

                const triggerButton = document.getElementById('trigger-universe-load');
                if (triggerButton) {
                    triggerButton.disabled = false;
                }

                console.log('Universes loaded successfully');
            } else {
                console.warn('No universes found in response');
                select.innerHTML = '<option value="">No universes available</option>';
            }
        } catch (error) {
            console.error('Failed to load universes:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack
            });

            if (select) {
                select.innerHTML = `<option value="">Error: ${error.message}</option>`;
            }

            // Show user-friendly notification if available
            if (typeof this.showNotification === 'function') {
                this.showNotification(`Failed to load universes: ${error.message}`, 'error');
            }
        }
    }

    /**
     * Handle universe selection change - show preview
     */
    handleUniverseChange(event) {
        const select = event.target;
        const selectedOption = select.options[select.selectedIndex];

        if (select.value && selectedOption) {
            const symbolCount = selectedOption.dataset.symbolCount;
            const universeName = selectedOption.dataset.universeName;

            const preview = document.getElementById('universe-preview');
            const previewText = document.getElementById('preview-text');

            if (preview && previewText) {
                previewText.innerHTML = `
                    <strong>Universe:</strong> ${universeName}<br>
                    <strong>Symbol Count:</strong> ${symbolCount}<br>
                    <strong>Action:</strong> This will load ${symbolCount} symbols with the selected duration
                `;
                preview.style.display = 'block';
            }
        } else {
            const preview = document.getElementById('universe-preview');
            if (preview) {
                preview.style.display = 'none';
            }
        }
    }

    /**
     * Submit universe bulk load
     */
    async submitUniverseLoad(event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);

        // Check which data source is selected
        const dataSource = document.querySelector('input[name="data_source"]:checked')?.value;
        const csvFile = formData.get('csv_file');
        const universeKey = formData.get('universe_key');
        const years = formData.get('years');

        console.log('Data source:', dataSource);
        console.log('CSV file:', csvFile);
        console.log('Universe key:', universeKey);
        console.log('Years:', years);

        // Validate based on selected data source
        if (dataSource === 'csv') {
            if (!csvFile) {
                this.showNotification('Please select a CSV file', 'error');
                return;
            }
            // Clear universe_key to avoid confusion
            formData.delete('universe_key');
            console.log('CSV mode validated');
        } else if (dataSource === 'cached') {
            if (!universeKey) {
                this.showNotification('Please select a cached universe', 'error');
                return;
            }
            // Clear csv_file to avoid confusion
            formData.delete('csv_file');
            console.log('Cached universe mode validated');
        } else {
            this.showNotification('Please select a data source', 'error');
            return;
        }

        try {
            console.log('Sending POST request to /admin/historical-data/trigger-universe-load');

            const response = await fetch('/admin/historical-data/trigger-universe-load', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData)
            });

            console.log('Response status:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Response error:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            console.log('Response data:', data);

            if (data.success) {
                this.showNotification(
                    `Universe load submitted! Job ID: ${data.job_id.substring(0, 8)}... (${data.symbol_count} symbols)`,
                    'success'
                );

                // Show progress container
                const progressContainer = document.getElementById('universe-progress');
                const statusText = document.getElementById('universe-status');

                if (progressContainer) {
                    progressContainer.style.display = 'block';
                }

                if (statusText) {
                    statusText.textContent = `Loading ${data.symbol_count} symbols from ${data.universe_key}...`;
                }

                // Start polling job status
                this.startPollingJobStatus(data.job_id);
            } else {
                this.showNotification(`Failed: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Universe load submission failed:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack
            });
            this.showNotification(
                `Failed to submit universe load: ${error.message}`,
                'error'
            );
        }
    }

    /**
     * Handle data source toggle (CSV vs Cached Universe)
     */
    handleDataSourceToggle() {
        const dataSource = document.querySelector('input[name="data_source"]:checked')?.value;
        const csvGroup = document.getElementById('csv-file-group');
        const cachedGroup = document.getElementById('cached-universe-group');

        if (dataSource === 'csv') {
            csvGroup.style.display = 'flex';
            cachedGroup.style.display = 'none';
        } else if (dataSource === 'cached') {
            csvGroup.style.display = 'none';
            cachedGroup.style.display = 'flex';
        }

        console.log(`Data source toggled to: ${dataSource}`);
    }

    /**
     * Initialize universe-related event listeners
     */
    initializeUniverseHandlers() {
        // Data source radio buttons toggle
        const dataSourceRadios = document.querySelectorAll('input[name="data_source"]');
        dataSourceRadios.forEach(radio => {
            radio.addEventListener('change', () => this.handleDataSourceToggle());
        });

        // Universe selection change event
        const universeSelect = document.getElementById('universe-select');
        if (universeSelect) {
            universeSelect.addEventListener('change', (e) => this.handleUniverseChange(e));
        }

        // Universe load form submission
        const universeLoadForm = document.getElementById('universeLoadForm');
        if (universeLoadForm) {
            universeLoadForm.addEventListener('submit', (e) => this.submitUniverseLoad(e));
        }

        // Load universes on initialization
        this.loadUniverses();

        // Initialize data source toggle state
        this.handleDataSourceToggle();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Prevent duplicate instantiation
    if (window.historicalDataManager) {
        console.log('HistoricalDataManager already initialized, skipping...');
        return;
    }
    console.log('Initializing HistoricalDataManager...');
    window.historicalDataManager = new HistoricalDataManager();
    console.log('HistoricalDataManager initialized');
});