/**
 * Pattern Export Service for TickStock Pattern Discovery
 * Handles CSV export and pattern list sharing capabilities
 * 
 * Sprint 21 - Week 1 Deliverable
 * Architecture: Follows established web/static/js/services/ pattern
 * Integration: Extends Pattern Discovery Dashboard functionality
 */

class PatternExportService {
    constructor() {
        this.isInitialized = false;
        
        // Export format configurations
        this.exportFormats = {
            csv: {
                name: 'CSV (Comma Separated Values)',
                extension: 'csv',
                mimeType: 'text/csv'
            },
            json: {
                name: 'JSON (JavaScript Object Notation)',
                extension: 'json',
                mimeType: 'application/json'
            },
            xlsx: {
                name: 'Excel Spreadsheet (XLSX)',
                extension: 'xlsx',
                mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        };
        
        this.initialize();
    }

    async initialize() {
        try {
            this.setupEventHandlers();
            this.addExportButtons();
            this.isInitialized = true;
            console.log('PatternExportService initialized successfully');
        } catch (error) {
            console.error('Failed to initialize PatternExportService:', error);
            this.showError('Failed to initialize pattern export functionality.');
        }
    }

    /**
     * Add export buttons to the pattern discovery interface
     */
    addExportButtons() {
        // Add export button to pattern discovery header
        const patternHeader = document.querySelector('#pattern-discovery-content .d-flex.justify-content-between.align-items-center');
        if (patternHeader) {
            const existingExportBtn = document.getElementById('export-patterns-btn');
            if (!existingExportBtn) {
                const exportButton = document.createElement('button');
                exportButton.id = 'export-patterns-btn';
                exportButton.className = 'btn btn-sm btn-outline-success ms-2';
                exportButton.innerHTML = '<i class="fas fa-download me-1"></i>Export';
                exportButton.title = 'Export pattern data';
                exportButton.addEventListener('click', () => this.showExportModal());
                
                patternHeader.appendChild(exportButton);
            }
        }
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Listen for keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+E or Cmd+E for export
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                this.showExportModal();
            }
        });
    }

    /**
     * Show export modal with format options
     */
    showExportModal() {
        const patterns = this.getCurrentPatterns();
        if (!patterns || patterns.length === 0) {
            this.showWarning('No patterns available to export. Please load some patterns first.');
            return;
        }

        const formatOptions = Object.entries(this.exportFormats).map(([key, format]) => 
            `<option value="${key}">${format.name}</option>`
        ).join('');

        Swal.fire({
            title: 'Export Pattern Data',
            html: `
                <div class="mb-3">
                    <label for="export-format" class="form-label">Export Format</label>
                    <select class="form-select" id="export-format">
                        ${formatOptions}
                    </select>
                </div>
                
                <div class="mb-3">
                    <label for="export-filename" class="form-label">Filename</label>
                    <input type="text" class="form-control" id="export-filename" 
                           value="tickstock-patterns-${this.getCurrentTimestamp()}" 
                           placeholder="Enter filename (without extension)">
                </div>
                
                <div class="mb-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="include-metadata" checked>
                        <label class="form-check-label" for="include-metadata">
                            Include metadata (timestamp, filters, etc.)
                        </label>
                    </div>
                </div>
                
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Exporting ${patterns.length} patterns
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'Export',
            cancelButtonText: 'Cancel',
            preConfirm: () => {
                const format = document.getElementById('export-format').value;
                const filename = document.getElementById('export-filename').value.trim();
                const includeMetadata = document.getElementById('include-metadata').checked;
                
                if (!filename) {
                    Swal.showValidationMessage('Please enter a filename');
                    return false;
                }
                
                return { format, filename, includeMetadata };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                const { format, filename, includeMetadata } = result.value;
                this.exportPatterns(patterns, format, filename, includeMetadata);
            }
        });
    }

    /**
     * Get current patterns from pattern discovery service
     */
    getCurrentPatterns() {
        if (window.patternDiscovery) {
            return window.patternDiscovery.getPatternsForDisplay();
        }
        return [];
    }

    /**
     * Get current timestamp for filename
     */
    getCurrentTimestamp() {
        const now = new Date();
        return now.toISOString().slice(0, 19).replace(/[T:]/g, '-');
    }

    /**
     * Export patterns in specified format
     */
    async exportPatterns(patterns, format, filename, includeMetadata = true) {
        try {
            let exportData;
            let mimeType;
            let extension;
            
            switch (format) {
                case 'csv':
                    exportData = this.generateCSV(patterns, includeMetadata);
                    mimeType = this.exportFormats.csv.mimeType;
                    extension = this.exportFormats.csv.extension;
                    break;
                    
                case 'json':
                    exportData = this.generateJSON(patterns, includeMetadata);
                    mimeType = this.exportFormats.json.mimeType;
                    extension = this.exportFormats.json.extension;
                    break;
                    
                case 'xlsx':
                    this.showWarning('Excel export will be available in a future update. Please use CSV format for now.');
                    return;
                    
                default:
                    throw new Error(`Unsupported export format: ${format}`);
            }
            
            // Create and download file
            this.downloadFile(exportData, `${filename}.${extension}`, mimeType);
            
            this.showSuccess(`Successfully exported ${patterns.length} patterns as ${format.toUpperCase()}`);
            
        } catch (error) {
            console.error('Export failed:', error);
            this.showError(`Export failed: ${error.message}`);
        }
    }

    /**
     * Generate CSV format data
     */
    generateCSV(patterns, includeMetadata) {
        const headers = [
            'Symbol',
            'Pattern',
            'Confidence',
            'Price',
            'Change Percent',
            'RS Score',
            'Volume',
            'RSI',
            'Market Cap',
            'Detected Time'
        ];
        
        let csvContent = '';
        
        // Add metadata if requested
        if (includeMetadata) {
            csvContent += `# TickStock Pattern Export\n`;
            csvContent += `# Export Date: ${new Date().toISOString()}\n`;
            csvContent += `# Total Patterns: ${patterns.length}\n`;
            
            // Add active filter information
            if (window.patternDiscovery?.filteredPatterns) {
                csvContent += `# Filtered Data: ${patterns.length} of ${window.patternDiscovery.patterns.length} patterns\n`;
            }
            
            if (window.watchlistManager?.activeWatchlist) {
                const activeWatchlist = window.watchlistManager.getActiveWatchlist();
                csvContent += `# Active Watchlist: ${activeWatchlist?.name}\n`;
            }
            
            if (window.filterPresets?.activePreset) {
                const activePreset = window.filterPresets.getPreset(window.filterPresets.activePreset);
                csvContent += `# Active Filter Preset: ${activePreset?.name}\n`;
            }
            
            csvContent += `#\n`;
        }
        
        // Add headers
        csvContent += headers.join(',') + '\n';
        
        // Add pattern data
        patterns.forEach(pattern => {
            const row = [
                this.escapeCsvValue(pattern.symbol),
                this.escapeCsvValue(pattern.pattern),
                pattern.confidence,
                pattern.price,
                pattern.change_percent,
                pattern.rs || '',
                pattern.volume || '',
                pattern.rsi || '',
                pattern.market_cap || '',
                this.escapeCsvValue(pattern.timestamp)
            ];
            
            csvContent += row.join(',') + '\n';
        });
        
        return csvContent;
    }

    /**
     * Generate JSON format data
     */
    generateJSON(patterns, includeMetadata) {
        const exportData = {
            patterns: patterns
        };
        
        if (includeMetadata) {
            exportData.metadata = {
                exportDate: new Date().toISOString(),
                totalPatterns: patterns.length,
                source: 'TickStock Pattern Discovery Dashboard'
            };
            
            // Add filter context
            if (window.patternDiscovery?.filteredPatterns) {
                exportData.metadata.isFiltered = true;
                exportData.metadata.totalAvailablePatterns = window.patternDiscovery.patterns.length;
            }
            
            if (window.watchlistManager?.activeWatchlist) {
                const activeWatchlist = window.watchlistManager.getActiveWatchlist();
                exportData.metadata.activeWatchlist = {
                    id: activeWatchlist.id,
                    name: activeWatchlist.name,
                    symbolCount: activeWatchlist.symbols.length
                };
            }
            
            if (window.filterPresets?.activePreset) {
                const activePreset = window.filterPresets.getPreset(window.filterPresets.activePreset);
                exportData.metadata.activeFilterPreset = {
                    id: activePreset.id,
                    name: activePreset.name,
                    description: activePreset.description
                };
            }
        }
        
        return JSON.stringify(exportData, null, 2);
    }

    /**
     * Escape CSV values to handle commas and quotes
     */
    escapeCsvValue(value) {
        if (value === null || value === undefined) {
            return '';
        }
        
        const stringValue = String(value);
        
        // If the value contains commas, quotes, or newlines, wrap it in quotes
        if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
            // Escape existing quotes by doubling them
            return `"${stringValue.replace(/"/g, '""')}"`;
        }
        
        return stringValue;
    }

    /**
     * Download file with given content
     */
    downloadFile(content, filename, mimeType) {
        // Create blob with content
        const blob = new Blob([content], { type: mimeType });
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        
        // Cleanup
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }

    /**
     * Share patterns via web share API or clipboard
     */
    async sharePatterns(patterns, format = 'json') {
        try {
            const exportData = format === 'csv' 
                ? this.generateCSV(patterns, true)
                : this.generateJSON(patterns, true);
            
            // Try Web Share API first (mobile browsers)
            if (navigator.share) {
                const blob = new Blob([exportData], { 
                    type: format === 'csv' ? 'text/csv' : 'application/json'
                });
                const file = new File([blob], `tickstock-patterns-${this.getCurrentTimestamp()}.${format}`, {
                    type: blob.type
                });
                
                await navigator.share({
                    title: 'TickStock Pattern Data',
                    text: `${patterns.length} patterns from TickStock`,
                    files: [file]
                });
                
                this.showSuccess('Pattern data shared successfully');
                return;
            }
            
            // Fallback to clipboard API
            if (navigator.clipboard) {
                await navigator.clipboard.writeText(exportData);
                this.showSuccess('Pattern data copied to clipboard');
                return;
            }
            
            // Ultimate fallback - show data in modal for manual copy
            this.showShareModal(exportData, format);
            
        } catch (error) {
            console.error('Share failed:', error);
            this.showError(`Share failed: ${error.message}`);
        }
    }

    /**
     * Show share modal for manual copying
     */
    showShareModal(data, format) {
        const formatName = format.toUpperCase();
        
        Swal.fire({
            title: `Share Pattern Data (${formatName})`,
            html: `
                <div class="mb-3">
                    <p>Copy the data below and share it manually:</p>
                    <textarea class="form-control" rows="10" id="share-data" readonly>${data}</textarea>
                </div>
                <div class="d-grid">
                    <button class="btn btn-outline-primary" onclick="this.select(); document.execCommand('copy'); alert('Copied to clipboard!')">
                        <i class="fas fa-copy me-1"></i>Copy to Clipboard
                    </button>
                </div>
            `,
            showConfirmButton: false,
            showCancelButton: true,
            cancelButtonText: 'Close'
        });
        
        // Auto-select text
        setTimeout(() => {
            const textarea = document.getElementById('share-data');
            if (textarea) {
                textarea.select();
            }
        }, 100);
    }

    /**
     * Quick export current patterns as CSV
     */
    quickExportCSV() {
        const patterns = this.getCurrentPatterns();
        if (!patterns || patterns.length === 0) {
            this.showWarning('No patterns available to export');
            return;
        }
        
        this.exportPatterns(patterns, 'csv', `tickstock-patterns-${this.getCurrentTimestamp()}`, true);
    }

    /**
     * Quick share current patterns
     */
    quickShare() {
        const patterns = this.getCurrentPatterns();
        if (!patterns || patterns.length === 0) {
            this.showWarning('No patterns available to share');
            return;
        }
        
        this.sharePatterns(patterns, 'json');
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
                timer: 3000,
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

// Initialize pattern export service when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof window !== 'undefined') {
        window.patternExport = new PatternExportService();
    }
});