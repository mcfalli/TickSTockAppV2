/**
 * Process Stock Analysis - Admin Interface
 * Sprint 73: Independent analysis page for manually triggering pattern/indicator analysis
 *
 * Handles job submission, real-time progress polling, and result display for
 * on-demand stock analysis via universe selection or manual symbol entry.
 */

class ProcessAnalysisManager {
    constructor() {
        this.pollIntervals = new Map();
        this.pollFrequency = 1000;      // Poll every 1 second
        this.maxPollDuration = 300000;  // 5 minutes max
        this.initializeElements();
        this.attachEventListeners();
    }

    initializeElements() {
        // Form elements
        this.progressContainer = document.getElementById('progressContainer');
        this.progressBar = document.getElementById('progressBar');
        this.statusText = document.getElementById('statusText');
        this.logMessages = document.getElementById('logMessages');
        this.submitButton = document.getElementById('submitAnalysisBtn');
        this.universeSelect = document.getElementById('universe-select');
        this.symbolsInput = document.getElementById('symbols-input');
    }

    attachEventListeners() {
        if (this.submitButton) {
            this.submitButton.addEventListener('click', () => this.submitAnalysisJob());
        }

        // Load universes on page load
        this.loadUniverses();
    }

    /**
     * Load available universes from backend and populate dropdown
     * Reuses existing /admin/historical-data/universes endpoint
     */
    async loadUniverses() {
        try {
            const response = await fetch('/admin/historical-data/universes?types=UNIVERSE,ETF');

            // Check if response is HTML (redirect to login)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                console.error('Session expired, redirecting to login...');
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.universes && data.universes.length > 0) {
                this.populateUniverseDropdown(data.universes);
            }
        } catch (error) {
            console.error('Failed to load universes:', error);
        }
    }

    /**
     * Populate universe dropdown with grouped optgroups
     */
    populateUniverseDropdown(universes) {
        this.universeSelect.innerHTML = '<option value="">-- Select Universe --</option>';

        // Group by type (UNIVERSE, ETF, etc.)
        const grouped = universes.reduce((acc, u) => {
            if (!acc[u.type]) acc[u.type] = [];
            acc[u.type].push(u);
            return acc;
        }, {});

        // Add optgroups
        Object.keys(grouped).sort().forEach(type => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = `${type} (${grouped[type].length})`;

            grouped[type].forEach(universe => {
                const option = document.createElement('option');
                option.value = universe.name;
                option.textContent = `${universe.name} (${universe.member_count} stocks)`;
                optgroup.appendChild(option);
            });

            this.universeSelect.appendChild(optgroup);
        });
    }

    /**
     * Submit analysis job to backend
     */
    async submitAnalysisJob() {
        // Get form values
        const universeKey = this.universeSelect.value;
        const symbolsInput = this.symbolsInput.value.trim();
        const analysisType = document.querySelector('input[name="analysis_type"]:checked')?.value || 'both';
        const timeframe = document.querySelector('input[name="timeframe"]:checked')?.value || 'daily';

        // Validate: require universe OR symbols (not both empty)
        if (!universeKey && !symbolsInput) {
            this.showNotification('Please select a universe or enter symbols', 'error');
            return;
        }

        try {
            this.submitButton.disabled = true;
            this.submitButton.textContent = 'Submitting...';

            const response = await fetch('/admin/process-analysis/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    universe_key: universeKey,
                    symbols: symbolsInput,
                    analysis_type: analysisType,
                    timeframe: timeframe
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(
                    `Analysis job submitted! (${data.symbols_count} symbols)`,
                    'success'
                );
                this.startPollingJobStatus(data.job_id);
            } else {
                this.showNotification(data.error || 'Failed to submit job', 'error');
            }

        } catch (error) {
            console.error('Error submitting job:', error);
            this.showNotification('Failed to submit job: ' + error.message, 'error');
        } finally {
            this.submitButton.disabled = false;
            this.submitButton.textContent = '🔬 Run Analysis';
        }
    }

    /**
     * Start polling job status with recursive setTimeout
     * CRITICAL: Uses setTimeout (recursive) instead of setInterval
     * Ensures request completion before next poll starts
     */
    startPollingJobStatus(jobId) {
        // Show progress container
        if (this.progressContainer) {
            this.progressContainer.classList.add('show');
        }

        // Clear any existing interval
        if (this.pollIntervals.has(jobId)) {
            clearTimeout(this.pollIntervals.get(jobId));
        }

        let pollCount = 0;
        const maxPolls = this.maxPollDuration / this.pollFrequency;

        const poll = async () => {
            pollCount++;

            try {
                const response = await fetch(`/admin/process-analysis/job-status/${jobId}`);
                const status = await response.json();

                if (status.id) {
                    this.updateJobStatus(jobId, status);

                    // Stop polling if job complete
                    if (['completed', 'failed', 'cancelled'].includes(status.status)) {
                        if (this.pollIntervals.has(jobId)) {
                            clearTimeout(this.pollIntervals.get(jobId));
                            this.pollIntervals.delete(jobId);
                        }

                        if (status.status === 'completed') {
                            this.showNotification(
                                `Analysis complete! ${status.symbols_completed} symbols, ` +
                                `${status.patterns_detected} patterns, ` +
                                `${status.indicators_calculated} indicators`,
                                'success'
                            );
                        } else if (status.status === 'failed') {
                            const errorMsg = status.log_messages.length > 0
                                ? status.log_messages[status.log_messages.length - 1]
                                : 'Unknown error';
                            this.showNotification(`Analysis failed: ${errorMsg}`, 'error');
                        } else if (status.status === 'cancelled') {
                            this.showNotification('Analysis cancelled by user', 'error');
                        }

                        return; // Stop polling
                    }

                    // Continue polling if job still running
                    if (pollCount < maxPolls) {
                        const timeoutId = setTimeout(poll, this.pollFrequency);
                        this.pollIntervals.set(jobId, timeoutId);
                    }

                } else if (response.status === 404) {
                    clearTimeout(this.pollIntervals.get(jobId));
                    this.pollIntervals.delete(jobId);
                    this.showNotification('Job not found or expired', 'error');
                }
            } catch (error) {
                console.error(`Poll error for ${jobId}:`, error);

                // Retry with longer delay on error
                if (pollCount < maxPolls) {
                    const timeoutId = setTimeout(poll, 2000);
                    this.pollIntervals.set(jobId, timeoutId);
                }
            }

            // Stop polling after max duration
            if (pollCount >= maxPolls) {
                clearTimeout(this.pollIntervals.get(jobId));
                this.pollIntervals.delete(jobId);
                this.showNotification('Polling timeout (job may still be running)', 'error');
            }
        };

        // Start polling
        poll();
    }

    /**
     * Update progress bar and status text with job status
     */
    updateJobStatus(jobId, status) {
        // Update progress bar
        if (this.progressBar && status.progress >= 0) {
            this.progressBar.style.width = status.progress + '%';
            this.progressBar.textContent = Math.round(status.progress) + '%';
            this.progressBar.setAttribute('aria-valuenow', status.progress);
        }

        // Update status text
        if (this.statusText) {
            const text = status.current_symbol
                ? `Analyzing ${status.current_symbol} (${status.symbols_completed}/${status.symbols_total})`
                : `Progress: ${status.symbols_completed}/${status.symbols_total}`;
            this.statusText.textContent = text;
        }

        // Update log messages
        if (this.logMessages && status.log_messages && status.log_messages.length > 0) {
            this.logMessages.style.display = 'block';
            this.logMessages.innerHTML = status.log_messages
                .map(msg => `<div>${msg}</div>`)
                .join('');

            // Auto-scroll to bottom
            this.logMessages.scrollTop = this.logMessages.scrollHeight;
        }

        // Update job card in active jobs list if exists
        const jobCard = document.getElementById(`job-${jobId}`);
        if (jobCard) {
            const statusBadge = jobCard.querySelector('.job-status');
            if (statusBadge) {
                statusBadge.textContent = status.status.toUpperCase();
                statusBadge.className = `job-status status-${status.status}`;
            }

            const progressText = jobCard.querySelector('p strong');
            if (progressText && progressText.textContent.includes('Progress')) {
                progressText.parentElement.textContent = `Progress: ${status.symbols_completed}/${status.symbols_total} (${status.progress}%)`;
            }
        }
    }

    /**
     * Cancel a running job
     */
    async cancelJob(jobId) {
        try {
            const response = await fetch(`/admin/process-analysis/job/${jobId}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Job cancelled successfully', 'success');
            } else {
                this.showNotification(data.error || 'Failed to cancel job', 'error');
            }
        } catch (error) {
            console.error('Error cancelling job:', error);
            this.showNotification('Failed to cancel job: ' + error.message, 'error');
        }
    }

    /**
     * Get CSRF token from hidden input, meta tag, or cookie
     * Sprint 62 pattern: Primary → Fallback → Fallback
     */
    getCSRFToken() {
        // Primary: Hidden input field
        const input = document.querySelector('input[name="csrf_token"]');
        if (input && input.value) {
            return input.value;
        }

        // Fallback 1: Meta tag
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) {
            return meta.content;
        }

        // Fallback 2: Cookie
        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrf_token='));
        if (cookie) {
            return cookie.split('=')[1];
        }

        console.error('CSRF token not found!');
        return '';
    }

    /**
     * Show notification message
     */
    showNotification(message, type) {
        let notification = document.getElementById('notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'notification';
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.right = '20px';
            notification.style.padding = '15px 20px';
            notification.style.borderRadius = '8px';
            notification.style.zIndex = '1000';
            notification.style.maxWidth = '400px';
            notification.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            document.body.appendChild(notification);
        }

        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.display = 'block';

        if (type === 'success') {
            notification.style.background = '#d4edda';
            notification.style.color = '#155724';
            notification.style.border = '1px solid #c3e6cb';
        } else {
            notification.style.background = '#f8d7da';
            notification.style.color = '#721c24';
            notification.style.border = '1px solid #f5c6cb';
        }

        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);
    }
}

// Global function for cancel button in HTML (called from onclick)
function cancelJob(jobId) {
    if (window.processAnalysisManager) {
        window.processAnalysisManager.cancelJob(jobId);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('/admin/process-analysis')) {
        window.processAnalysisManager = new ProcessAnalysisManager();
    }
});
