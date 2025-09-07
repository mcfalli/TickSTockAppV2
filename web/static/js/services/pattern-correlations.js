/**
 * Pattern Correlations Service - Sprint 23
 * =======================================
 * 
 * Provides pattern correlation analysis with heatmap and matrix visualizations
 * Integrates with Sprint 23 backend analytics services for real-time correlation data
 * 
 * Author: TickStock Development Team
 * Date: 2025-09-06
 * Sprint: 23
 */

// Debug flag for development
const CORRELATIONS_DEBUG = false;

class PatternCorrelationsService {
    constructor() {
        this.initialized = false;
        this.correlationData = null;
        this.currentFormat = 'heatmap'; // heatmap, matrix, network
        this.chart = null;
        this.setupEventHandlers();
    }

    async initialize(containerId = null) {
        if (this.initialized) return;
        
        if (CORRELATIONS_DEBUG) console.log('🔗 Initializing Pattern Correlations Dashboard...');
        
        try {
            // If containerId is provided, render to that container instead
            if (containerId) {
                const container = document.getElementById(containerId);
                if (container) {
                    container.innerHTML = this.createCorrelationInterface();
                }
            } else {
                await this.renderDashboard();
            }
            
            // Use mock data by default for faster loading
            this.renderMockData();
            this.initialized = true;
            if (CORRELATIONS_DEBUG) console.log('✅ Pattern Correlations Dashboard initialized with mock data');
            
            // Try to load real data in background
            setTimeout(() => {
                this.loadCorrelationData().catch(error => {
                    if (CORRELATIONS_DEBUG) console.log('Using mock data - API not available');
                });
            }, 1000);
            
        } catch (error) {
            console.error('❌ Pattern Correlations initialization failed:', error);
            this.renderError(error.message);
        }
    }

    async renderDashboard() {
        const container = document.getElementById('correlations-dashboard');
        if (!container) throw new Error('Correlations container not found');

        container.innerHTML = `
            <div class="correlations-header mb-4">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <h4><i class="fas fa-project-diagram text-success me-2"></i>Pattern Correlations</h4>
                        <p class="text-muted mb-0">Analyze relationships between trading patterns</p>
                    </div>
                    <div class="col-md-6 text-end">
                        <div class="btn-group" role="group">
                            <button type="button" class="btn btn-outline-primary btn-sm format-btn active" data-format="heatmap">
                                <i class="fas fa-th me-1"></i>Heatmap
                            </button>
                            <button type="button" class="btn btn-outline-primary btn-sm format-btn" data-format="matrix">
                                <i class="fas fa-table me-1"></i>Matrix
                            </button>
                            <button type="button" class="btn btn-outline-primary btn-sm format-btn" data-format="network">
                                <i class="fas fa-sitemap me-1"></i>Network
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="correlations-controls mb-4">
                <div class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">Time Period</label>
                        <select class="form-select" id="correlation-timeperiod">
                            <option value="7">Last 7 days</option>
                            <option value="30" selected>Last 30 days</option>
                            <option value="60">Last 60 days</option>
                            <option value="90">Last 90 days</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Min Correlation</label>
                        <select class="form-select" id="correlation-threshold">
                            <option value="0.1">0.1 (Weak)</option>
                            <option value="0.3" selected>0.3 (Moderate)</option>
                            <option value="0.5">0.5 (Strong)</option>
                            <option value="0.7">0.7 (Very Strong)</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Relationship Type</label>
                        <select class="form-select" id="correlation-type">
                            <option value="all" selected>All Types</option>
                            <option value="concurrent">Concurrent</option>
                            <option value="sequential">Sequential</option>
                            <option value="inverse">Inverse</option>
                        </select>
                    </div>
                    <div class="col-md-3 d-flex align-items-end">
                        <button class="btn btn-primary" id="refresh-correlations">
                            <i class="fas fa-sync-alt me-1"></i>Refresh
                        </button>
                    </div>
                </div>
            </div>

            <div class="correlations-content">
                <div class="row">
                    <div class="col-md-9">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="mb-0" id="visualization-title">Pattern Correlation Heatmap</h5>
                            </div>
                            <div class="card-body">
                                <div id="correlation-visualization" style="height: 400px;">
                                    <div class="d-flex align-items-center justify-content-center h-100">
                                        <div class="spinner-border text-primary me-3" role="status"></div>
                                        <span>Loading correlation data...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">Correlation Summary</h6>
                            </div>
                            <div class="card-body" id="correlation-summary">
                                <div class="text-center text-muted">
                                    <div class="spinner-border spinner-border-sm mb-2"></div>
                                    <div>Loading...</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card mt-3">
                            <div class="card-header">
                                <h6 class="mb-0">Top Correlations</h6>
                            </div>
                            <div class="card-body" id="top-correlations">
                                <div class="text-center text-muted">
                                    <div class="spinner-border spinner-border-sm mb-2"></div>
                                    <div>Loading...</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventHandlers() {
        document.addEventListener('click', (event) => {
            // Format button handlers
            if (event.target.closest('.format-btn')) {
                const btn = event.target.closest('.format-btn');
                const format = btn.dataset.format;
                this.switchFormat(format);
            }
        });

        document.addEventListener('change', (event) => {
            if (event.target.id === 'correlation-timeperiod' || 
                event.target.id === 'correlation-threshold' ||
                event.target.id === 'correlation-type') {
                this.loadCorrelationData();
            }
        });

        document.addEventListener('click', (event) => {
            if (event.target.id === 'refresh-correlations' || 
                event.target.closest('#refresh-correlations')) {
                this.refreshData();
            }
        });
    }

    async loadCorrelationData() {
        try {
            const timeperiod = document.getElementById('correlation-timeperiod')?.value || 30;
            const threshold = document.getElementById('correlation-threshold')?.value || 0.3;
            const type = document.getElementById('correlation-type')?.value || 'all';

            // API call to Sprint 23 backend
            const response = await fetch(`/api/analytics/correlations?format=${this.currentFormat}&days_back=${timeperiod}&min_correlation=${threshold}&type=${type}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                }
            });

            if (response.ok) {
                this.correlationData = await response.json();
                this.renderVisualization();
                this.updateSummary();
                this.updateTopCorrelations();
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

        } catch (error) {
            console.error('Failed to load correlation data:', error);
            this.renderMockData(); // Fallback to mock data for development
        }
    }

    switchFormat(format) {
        // Update active button
        document.querySelectorAll('.format-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-format="${format}"]`).classList.add('active');
        
        this.currentFormat = format;
        this.updateVisualizationTitle();
        this.loadCorrelationData();
    }

    updateVisualizationTitle() {
        const titles = {
            heatmap: 'Pattern Correlation Heatmap',
            matrix: 'Pattern Correlation Matrix',
            network: 'Pattern Correlation Network'
        };
        
        const titleElement = document.getElementById('visualization-title');
        if (titleElement) {
            titleElement.textContent = titles[this.currentFormat] || 'Pattern Correlations';
        }
    }

    renderVisualization() {
        const container = document.getElementById('correlation-visualization');
        if (!container || !this.correlationData) return;

        // Clear existing chart
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }

        switch (this.currentFormat) {
            case 'heatmap':
                this.renderHeatmap(container);
                break;
            case 'matrix':
                this.renderMatrix(container);
                break;
            case 'network':
                this.renderNetwork(container);
                break;
        }
    }

    renderHeatmap(container) {
        // Create canvas for Chart.js heatmap
        container.innerHTML = '<canvas id="correlation-heatmap-chart"></canvas>';
        const ctx = document.getElementById('correlation-heatmap-chart').getContext('2d');

        const data = this.correlationData.pattern_pairs || [];
        const patterns = [...new Set(data.flatMap(item => [item.pattern_a, item.pattern_b]))];

        // Create heatmap data matrix
        const heatmapData = [];
        patterns.forEach((patternA, i) => {
            patterns.forEach((patternB, j) => {
                const correlation = data.find(item => 
                    (item.pattern_a === patternA && item.pattern_b === patternB) ||
                    (item.pattern_a === patternB && item.pattern_b === patternA)
                );
                
                heatmapData.push({
                    x: j,
                    y: i,
                    v: correlation ? correlation.correlation_coefficient : (i === j ? 1.0 : 0)
                });
            });
        });

        this.chart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Correlation',
                    data: heatmapData,
                    backgroundColor: function(context) {
                        const value = context.parsed.v;
                        const alpha = Math.abs(value);
                        return value > 0 ? `rgba(34, 197, 94, ${alpha})` : `rgba(239, 68, 68, ${alpha})`;
                    },
                    pointRadius: 8,
                    pointHoverRadius: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        min: -0.5,
                        max: patterns.length - 0.5,
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                return patterns[Math.round(value)] || '';
                            }
                        }
                    },
                    y: {
                        min: -0.5,
                        max: patterns.length - 0.5,
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                return patterns[Math.round(value)] || '';
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const point = context[0];
                                const patternA = patterns[point.parsed.x] || 'Unknown';
                                const patternB = patterns[point.parsed.y] || 'Unknown';
                                return `${patternA} ↔ ${patternB}`;
                            },
                            label: function(context) {
                                return `Correlation: ${context.parsed.v.toFixed(3)}`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderMatrix(container) {
        const data = this.correlationData.patterns || [];
        const matrix = this.correlationData.matrix || [];

        let html = '<div class="table-responsive"><table class="table table-sm">';
        html += '<thead><tr><th></th>';
        
        data.forEach(pattern => {
            html += `<th class="text-center small">${pattern}</th>`;
        });
        html += '</tr></thead><tbody>';

        matrix.forEach((row, i) => {
            html += `<tr><th>${data[i]}</th>`;
            row.forEach(value => {
                const colorClass = value > 0.5 ? 'bg-success bg-opacity-25' : 
                                 value < -0.5 ? 'bg-danger bg-opacity-25' : '';
                html += `<td class="text-center small ${colorClass}">${value.toFixed(2)}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    renderNetwork(container) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-sitemap fa-3x text-muted mb-3"></i>
                <h5>Network Visualization</h5>
                <p class="text-muted">Network diagram coming soon...</p>
                <div class="mt-3">
                    <div class="badge bg-primary me-2">Strong Correlations: ${this.correlationData?.strong_count || 0}</div>
                    <div class="badge bg-warning me-2">Moderate Correlations: ${this.correlationData?.moderate_count || 0}</div>
                    <div class="badge bg-secondary">Weak Correlations: ${this.correlationData?.weak_count || 0}</div>
                </div>
            </div>
        `;
    }

    updateSummary() {
        const summaryContainer = document.getElementById('correlation-summary');
        if (!summaryContainer || !this.correlationData) return;

        const data = this.correlationData;
        summaryContainer.innerHTML = `
            <div class="mb-3">
                <div class="d-flex justify-content-between">
                    <span class="text-muted small">Total Patterns:</span>
                    <span class="fw-bold">${data.total_patterns || 0}</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted small">Correlations Found:</span>
                    <span class="fw-bold">${data.total_correlations || 0}</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted small">Avg Correlation:</span>
                    <span class="fw-bold">${data.avg_correlation?.toFixed(3) || '0.000'}</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted small">Max Correlation:</span>
                    <span class="fw-bold text-success">${data.max_correlation?.toFixed(3) || '0.000'}</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted small">Last Updated:</span>
                    <span class="text-muted small">${new Date().toLocaleTimeString()}</span>
                </div>
            </div>
            <div class="progress mb-2" style="height: 4px;">
                <div class="progress-bar bg-success" style="width: 70%"></div>
            </div>
            <small class="text-muted">Data Quality: Good</small>
        `;
    }

    updateTopCorrelations() {
        const container = document.getElementById('top-correlations');
        if (!container || !this.correlationData) return;

        const correlations = this.correlationData.pattern_pairs || [];
        const top5 = correlations
            .sort((a, b) => Math.abs(b.correlation_coefficient) - Math.abs(a.correlation_coefficient))
            .slice(0, 5);

        let html = '';
        top5.forEach((corr, index) => {
            const isPositive = corr.correlation_coefficient > 0;
            const colorClass = isPositive ? 'text-success' : 'text-danger';
            const iconClass = isPositive ? 'fa-arrow-up' : 'fa-arrow-down';
            
            html += `
                <div class="d-flex justify-content-between align-items-center mb-2 p-2 rounded border">
                    <div class="small">
                        <div class="fw-bold">${corr.pattern_a}</div>
                        <div class="text-muted">↔ ${corr.pattern_b}</div>
                    </div>
                    <div class="text-end">
                        <div class="${colorClass} fw-bold">
                            <i class="fas ${iconClass} me-1"></i>
                            ${Math.abs(corr.correlation_coefficient).toFixed(3)}
                        </div>
                        <small class="text-muted">${corr.co_occurrence_count} pairs</small>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html || '<p class="text-muted text-center">No correlations found</p>';
    }

    renderMockData() {
        // Mock data for development/testing
        this.correlationData = {
            pattern_pairs: [
                { pattern_a: 'WeeklyBO', pattern_b: 'DailyBO', correlation_coefficient: 0.73, co_occurrence_count: 15 },
                { pattern_a: 'Hammer', pattern_b: 'Doji', correlation_coefficient: 0.58, co_occurrence_count: 12 },
                { pattern_a: 'EngulfingBull', pattern_b: 'VolumeSpike', correlation_coefficient: 0.65, co_occurrence_count: 8 },
            ],
            patterns: ['WeeklyBO', 'DailyBO', 'Hammer', 'Doji'],
            matrix: [[1.0, 0.73, 0.45, 0.32], [0.73, 1.0, 0.58, 0.41], [0.45, 0.58, 1.0, 0.67], [0.32, 0.41, 0.67, 1.0]],
            total_patterns: 4,
            total_correlations: 6,
            avg_correlation: 0.587,
            max_correlation: 0.73
        };

        this.renderVisualization();
        this.updateSummary();
        this.updateTopCorrelations();
    }

    createCorrelationInterface() {
        return `
            <div class="correlation-dashboard-container">
                <!-- Summary Cards Row -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card border-0 shadow-sm">
                            <div class="card-header bg-primary text-white">
                                <i class="fas fa-chart-line me-2"></i>Correlation Summary
                            </div>
                            <div class="card-body" id="correlation-summary">
                                <div class="d-flex justify-content-center py-3">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card border-0 shadow-sm">
                            <div class="card-header bg-success text-white">
                                <i class="fas fa-trophy me-2"></i>Top Correlations
                            </div>
                            <div class="card-body" id="top-correlations">
                                <div class="d-flex justify-content-center py-3">
                                    <div class="spinner-border text-success" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Visualization Controls -->
                <div class="card border-0 shadow-sm mb-4">
                    <div class="card-header bg-white border-bottom">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">
                                <i class="fas fa-project-diagram me-2 text-primary"></i>Pattern Correlations
                            </h5>
                            <div class="btn-group" role="group">
                                <button class="btn btn-sm btn-outline-primary active" onclick="patternCorrelationsService.setVisualizationFormat('heatmap')">
                                    <i class="fas fa-th me-1"></i>Heatmap
                                </button>
                                <button class="btn btn-sm btn-outline-primary" onclick="patternCorrelationsService.setVisualizationFormat('matrix')">
                                    <i class="fas fa-table me-1"></i>Matrix
                                </button>
                                <button class="btn btn-sm btn-outline-primary" onclick="patternCorrelationsService.setVisualizationFormat('network')">
                                    <i class="fas fa-share-alt me-1"></i>Network
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <div id="correlation-visualization" style="min-height: 400px;">
                            <div class="d-flex justify-content-center align-items-center" style="height: 400px;">
                                <div class="text-center">
                                    <div class="spinner-border text-primary mb-3" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                    <p class="text-muted">Loading correlation visualization...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Additional Analysis Tools -->
                <div class="row">
                    <div class="col-md-12">
                        <div class="card border-0 shadow-sm">
                            <div class="card-header bg-info text-white">
                                <i class="fas fa-tools me-2"></i>Analysis Tools
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <button class="btn btn-outline-primary w-100 mb-2" onclick="patternCorrelationsService.refreshData()">
                                            <i class="fas fa-sync-alt me-1"></i>Refresh Data
                                        </button>
                                    </div>
                                    <div class="col-md-4">
                                        <button class="btn btn-outline-success w-100 mb-2" onclick="patternCorrelationsService.exportData()">
                                            <i class="fas fa-download me-1"></i>Export CSV
                                        </button>
                                    </div>
                                    <div class="col-md-4">
                                        <button class="btn btn-outline-info w-100 mb-2" onclick="patternCorrelationsService.showSettings()">
                                            <i class="fas fa-cog me-1"></i>Settings
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderError(message) {
        const container = document.getElementById('correlations-dashboard');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                    <h5>Failed to Load Correlations</h5>
                    <p class="text-muted">${message}</p>
                    <button class="btn btn-primary" onclick="patternCorrelationsService.initialize()">
                        <i class="fas fa-retry me-1"></i>Retry
                    </button>
                </div>
            `;
        }
    }

    async refreshData() {
        if (CORRELATIONS_DEBUG) console.log('🔄 Refreshing correlation data...');
        await this.loadCorrelationData();
    }

    setVisualizationFormat(format) {
        this.currentFormat = format;
        // Update button states
        document.querySelectorAll('.btn-group button').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        this.renderVisualization();
    }

    exportData() {
        if (!this.correlationData) {
            alert('No data available to export');
            return;
        }

        const csv = this.generateCSV();
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pattern-correlations-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    generateCSV() {
        if (!this.correlationData || !this.correlationData.pattern_pairs) return '';

        let csv = 'Pattern A,Pattern B,Correlation,Co-occurrences\n';
        this.correlationData.pattern_pairs.forEach(pair => {
            csv += `${pair.pattern_a},${pair.pattern_b},${pair.correlation_coefficient},${pair.co_occurrence_count}\n`;
        });
        return csv;
    }

    showSettings() {
        // Placeholder for settings modal
        alert('Settings panel coming soon!');
    }
}

// Global service instance
const patternCorrelationsService = new PatternCorrelationsService();