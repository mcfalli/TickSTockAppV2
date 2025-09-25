/**
 * Real-time job monitoring for Admin Historical Data Dashboard
 */

class JobMonitor {
    constructor() {
        this.activeJobs = new Map();
        this.pollInterval = 2000; // Poll every 2 seconds
        this.pollTimer = null;
    }

    start() {
        console.log('Starting job monitor...');
        this.pollJobStatus();
        // Start polling
        this.pollTimer = setInterval(() => this.pollJobStatus(), this.pollInterval);
    }

    stop() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    async pollJobStatus() {
        try {
            // Get all job statuses
            const response = await fetch('/admin/historical-data/jobs/status');

            if (!response.ok) {
                console.error('Failed to fetch job status');
                return;
            }

            const data = await response.json();

            // Update active jobs display
            if (data.active_jobs && Object.keys(data.active_jobs).length > 0) {
                this.updateActiveJobsDisplay(data.active_jobs);
            } else {
                this.clearActiveJobsDisplay();
            }

            // Update recent jobs if changed
            if (data.recent_jobs) {
                this.updateRecentJobsDisplay(data.recent_jobs);
            }

            // Update statistics
            if (data.stats) {
                this.updateStatistics(data.stats);
            }

        } catch (error) {
            console.error('Error polling job status:', error);
        }
    }

    updateActiveJobsDisplay(jobs) {
        const container = document.getElementById('active-jobs-container');
        if (!container) {
            // Create container if doesn't exist
            const jobsSection = document.querySelector('.jobs-section');
            if (jobsSection) {
                const div = document.createElement('div');
                div.id = 'active-jobs-container';
                div.innerHTML = '<h3>🔄 Active Jobs</h3><div id="active-jobs-list"></div>';
                jobsSection.insertBefore(div, jobsSection.firstChild);
            }
        }

        const listContainer = document.getElementById('active-jobs-list') || document.getElementById('active-jobs-container');
        if (!listContainer) return;

        let html = '';

        for (const [jobId, job] of Object.entries(jobs)) {
            const progress = job.progress || 0;
            const status = job.status || 'unknown';
            const currentSymbol = job.current_symbol || '';
            const processedSymbols = job.processed_symbols || 0;
            const totalSymbols = job.total_symbols || 0;
            const message = job.message || '';

            html += `
                <div class="job-card active-job" id="job-${jobId}">
                    <div class="job-header">
                        <h4>Job: ${jobId.substring(0, 20)}...</h4>
                        <span class="job-status status-${status}">${status.toUpperCase()}</span>
                    </div>

                    <div class="job-details">
                        <p><strong>Progress:</strong> ${processedSymbols}/${totalSymbols} symbols (${progress}%)</p>
                        ${currentSymbol ? `<p><strong>Current Symbol:</strong> ${currentSymbol}</p>` : ''}
                        ${message ? `<p><strong>Status:</strong> ${message}</p>` : ''}
                    </div>

                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%; transition: width 0.5s ease;">
                            <span class="progress-text">${progress}%</span>
                        </div>
                    </div>

                    ${status === 'running' ?
                        `<button onclick="cancelJob('${jobId}')" class="btn btn-danger btn-sm">Cancel</button>` :
                        ''
                    }
                </div>
            `;
        }

        if (listContainer.id === 'active-jobs-list') {
            listContainer.innerHTML = html || '<p>No active jobs</p>';
        } else {
            listContainer.innerHTML = '<h3>🔄 Active Jobs</h3>' + (html || '<p>No active jobs</p>');
        }
    }

    clearActiveJobsDisplay() {
        const container = document.getElementById('active-jobs-list');
        if (container) {
            container.innerHTML = '<p>No active jobs</p>';
        }
    }

    updateRecentJobsDisplay(jobs) {
        // Update recent jobs section if needed
        const container = document.querySelector('.recent-jobs-container');
        if (!container) return;

        // Only update if there are changes
        // (implement change detection if needed)
    }

    updateStatistics(stats) {
        // Update statistics cards
        if (stats.active_jobs !== undefined) {
            const activeCard = document.querySelector('.stat-card:nth-child(3) .stat-value');
            if (activeCard) {
                activeCard.textContent = stats.active_jobs;
            }
        }

        if (stats.completed_today !== undefined) {
            const todayCard = document.querySelector('.stat-card:nth-child(4) .stat-value');
            if (todayCard) {
                todayCard.textContent = stats.completed_today;
            }
        }
    }
}

// Add styles for job monitoring
const style = document.createElement('style');
style.textContent = `
    .active-job {
        border-left: 4px solid #007bff;
        background: #f0f8ff;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.9; }
        100% { opacity: 1; }
    }

    .job-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .job-details {
        margin-bottom: 10px;
    }

    .job-details p {
        margin: 5px 0;
    }

    .progress-bar {
        height: 30px;
        background: #e9ecef;
        border-radius: 4px;
        overflow: hidden;
        position: relative;
        margin: 10px 0;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #007bff, #0056b3);
        display: flex;
        align-items: center;
        justify-content: center;
        transition: width 0.5s ease;
    }

    .progress-text {
        color: white;
        font-weight: bold;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }

    .status-running {
        background: #28a745;
        color: white;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 12px;
    }

    .status-completed {
        background: #6c757d;
        color: white;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 12px;
    }

    .status-failed {
        background: #dc3545;
        color: white;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 12px;
    }

    .status-submitted {
        background: #ffc107;
        color: black;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 12px;
    }
`;
document.head.appendChild(style);

// Initialize job monitor when page loads
let jobMonitor = null;

document.addEventListener('DOMContentLoaded', function() {
    // Only run on admin historical data page
    if (window.location.pathname.includes('/admin/historical-data')) {
        jobMonitor = new JobMonitor();
        jobMonitor.start();

        console.log('Job monitor initialized');
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (jobMonitor) {
        jobMonitor.stop();
    }
});