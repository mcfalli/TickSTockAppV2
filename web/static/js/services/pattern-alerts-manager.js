/**
 * Pattern Alerts Management Service
 * Handles user pattern subscriptions, preferences, and real-time alerts
 */
class PatternAlertsManager {
    constructor() {
        this.socket = null;
        this.subscriptions = new Map();
        this.preferences = {};
        this.alertHistory = [];
        this.performanceData = new Map();
        
        this.initializeSocket();
        this.bindEventHandlers();
        this.requestNotificationPermission();
    }
    
    initializeSocket() {
        // Connect to TickStockPL integration socket
        this.socket = io('/tickstockpl');
        
        this.socket.on('connect', () => {
            console.log('Connected to TickStockPL pattern alerts');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from TickStockPL pattern alerts');
            this.updateConnectionStatus(false);
        });
        
        // Listen for pattern alerts
        this.socket.on('pattern_alert', (data) => {
            this.handlePatternAlert(data);
        });
        
        // Listen for performance updates
        this.socket.on('pattern_performance', (data) => {
            this.updatePerformanceMetrics(data);
        });
    }
    
    bindEventHandlers() {
        // Add subscription modal and form handlers
        document.getElementById('addSubscriptionBtn').addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('addSubscriptionModal'));
            modal.show();
        });
        
        // Add subscription form submission
        document.getElementById('add-subscription-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addSubscription();
        });
        
        // Preferences form handlers
        const confidenceSlider = document.getElementById('confidence-threshold');
        const confidenceValue = document.getElementById('confidence-value');
        
        confidenceSlider.addEventListener('input', (e) => {
            confidenceValue.textContent = e.target.value + '%';
            this.updatePreferencePreview();
        });
        
        // Min confidence slider in modal
        const minConfidenceSlider = document.getElementById('min-confidence');
        const minConfidenceValue = document.getElementById('min-confidence-value');
        
        minConfidenceSlider.addEventListener('input', (e) => {
            minConfidenceValue.textContent = e.target.value + '%';
        });
        
        // Preferences form submission
        document.getElementById('preferences-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.savePreferences();
        });
        
        // Reset preferences
        document.getElementById('reset-preferences').addEventListener('click', () => {
            this.resetPreferences();
        });
        
        // Quiet hours toggle
        document.getElementById('enable-quiet-hours').addEventListener('change', (e) => {
            this.toggleQuietHoursDisplay(e.target.checked);
            this.updatePreferencePreview();
        });
        
        // Quiet hours time changes
        document.getElementById('quiet-start').addEventListener('change', () => {
            this.updateQuietHoursPreview();
        });
        
        document.getElementById('quiet-end').addEventListener('change', () => {
            this.updateQuietHoursPreview();
        });
        
        // Preference form changes for preview
        ['max-alerts-per-hour', 'notify-browser', 'notify-sound', 'priority-filter'].forEach(id => {
            document.getElementById(id).addEventListener('change', () => {
                this.updatePreferencePreview();
            });
        });
        
        // Performance timeframe change
        document.getElementById('performance-timeframe').addEventListener('change', (e) => {
            this.loadPerformance(e.target.value);
        });
        
        // History filter change
        document.getElementById('history-filter').addEventListener('change', (e) => {
            this.filterHistory(e.target.value);
        });
        
        // Load more history
        document.getElementById('load-more-history').addEventListener('click', () => {
            this.loadMoreHistory();
        });
        
        // Export history
        document.getElementById('export-history').addEventListener('click', () => {
            this.exportHistory();
        });
    }
    
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }
    
    async loadSubscriptions() {
        try {
            const response = await fetch('/api/tickstockpl/alerts/subscriptions');
            if (!response.ok) throw new Error('Failed to load subscriptions');
            
            const data = await response.json();
            this.subscriptions.clear();
            
            data.subscriptions.forEach(sub => {
                this.subscriptions.set(sub.pattern_name, sub);
            });
            
            this.renderSubscriptions();
            this.updateQuickStats();
            
        } catch (error) {
            console.error('Error loading subscriptions:', error);
            this.showError('Failed to load pattern subscriptions');
        }
    }
    
    async loadPreferences() {
        try {
            const response = await fetch('/api/tickstockpl/alerts/preferences');
            if (!response.ok) throw new Error('Failed to load preferences');
            
            const data = await response.json();
            this.preferences = data.preferences;
            this.populatePreferencesForm();
            this.updatePreferencePreview();
            
        } catch (error) {
            console.error('Error loading preferences:', error);
            // Use defaults if preferences don't exist
            this.preferences = this.getDefaultPreferences();
            this.populatePreferencesForm();
        }
    }
    
    async loadPerformance(timeframe = '30d') {
        try {
            const response = await fetch(`/api/tickstockpl/alerts/performance?timeframe=${timeframe}`);
            if (!response.ok) throw new Error('Failed to load performance');
            
            const data = await response.json();
            this.performanceData.clear();
            
            data.performance.forEach(perf => {
                this.performanceData.set(perf.pattern_name, perf);
            });
            
            this.renderPerformance();
            
        } catch (error) {
            console.error('Error loading performance:', error);
            this.showError('Failed to load pattern performance data');
        }
    }
    
    async loadHistory(limit = 50, offset = 0) {
        try {
            const response = await fetch(`/api/tickstockpl/alerts/history?limit=${limit}&offset=${offset}`);
            if (!response.ok) throw new Error('Failed to load history');
            
            const data = await response.json();
            
            if (offset === 0) {
                this.alertHistory = data.alerts;
            } else {
                this.alertHistory.push(...data.alerts);
            }
            
            this.renderHistory();
            
        } catch (error) {
            console.error('Error loading history:', error);
            this.showError('Failed to load alert history');
        }
    }
    
    renderSubscriptions() {
        const container = document.getElementById('subscriptions-list');
        container.innerHTML = '';
        
        if (this.subscriptions.size === 0) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="text-center p-4">
                        <i class="fas fa-bell-slash fa-3x text-muted mb-3"></i>
                        <h5 class="text-muted">No Pattern Subscriptions</h5>
                        <p class="text-muted mb-3">Start receiving real-time pattern alerts by adding your first subscription.</p>
                        <button class="btn btn-primary" onclick="document.getElementById('addSubscriptionBtn').click()">
                            <i class="fas fa-plus me-1"></i> Add Your First Pattern
                        </button>
                    </div>
                </div>
            `;
            return;
        }
        
        this.subscriptions.forEach((subscription, patternName) => {
            const card = this.createSubscriptionCard(subscription);
            container.appendChild(card);
        });
    }
    
    createSubscriptionCard(subscription) {
        const div = document.createElement('div');
        div.className = 'col-md-6 mb-3';
        
        const priorityClass = this.getPriorityClass(subscription.confidence || 70);
        const symbolsDisplay = subscription.symbols ? subscription.symbols.join(', ') : 'All symbols';
        
        div.innerHTML = `
            <div class="card pattern-alert-card ${priorityClass}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="card-title mb-0">${this.formatPatternName(subscription.pattern_name)}</h6>
                        <div class="form-check form-switch">
                            <input class="form-check-input subscription-toggle" type="checkbox" 
                                   id="toggle-${subscription.pattern_name}" 
                                   ${subscription.active ? 'checked' : ''}
                                   onchange="patternAlertsManager.toggleSubscription('${subscription.pattern_name}')">
                        </div>
                    </div>
                    <div class="mb-2">
                        <small class="text-muted">
                            <i class="fas fa-chart-line me-1"></i> ${symbolsDisplay}
                        </small>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="confidence-badge badge bg-primary">
                            ${subscription.confidence || 70}% min confidence
                        </span>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-secondary" 
                                    onclick="patternAlertsManager.editSubscription('${subscription.pattern_name}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-outline-danger" 
                                    onclick="patternAlertsManager.removeSubscription('${subscription.pattern_name}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    renderPerformance() {
        const container = document.getElementById('performance-metrics');
        container.innerHTML = '';
        
        if (this.performanceData.size === 0) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="text-center p-4">
                        <i class="fas fa-chart-bar fa-3x text-muted mb-3"></i>
                        <p class="text-muted">No performance data available yet.</p>
                        <small class="text-muted">Pattern performance data will appear here once you start receiving alerts.</small>
                    </div>
                </div>
            `;
            return;
        }
        
        // Sort patterns by total alerts descending for better display
        const sortedPatterns = Array.from(this.performanceData.entries())
            .sort((a, b) => (b[1].total_alerts || 0) - (a[1].total_alerts || 0));
        
        sortedPatterns.forEach(([patternName, perf]) => {
            const card = this.createPerformanceCard(perf);
            container.appendChild(card);
        });
        
        // Add summary statistics at the top if we have data
        this.addPerformanceSummary(container, sortedPatterns);
    }
    
    createPerformanceCard(performance) {
        const div = document.createElement('div');
        div.className = 'col-md-4 mb-3';
        
        const totalAlerts = performance.total_alerts || 0;
        const successfulAlerts = performance.successful_alerts || 0;
        const successRate = totalAlerts > 0 ? (successfulAlerts / totalAlerts * 100).toFixed(1) : '0.0';
        const avgConfidence = (performance.average_confidence || 0).toFixed(1);
        const avgReturnPercent = (performance.average_return_percent || 0).toFixed(2);
        const lastAlertTime = performance.last_alert_time ? 
            new Date(performance.last_alert_time * 1000).toLocaleDateString() : 'Never';
        
        // Determine success rate color
        const successRateColor = parseFloat(successRate) >= 60 ? 'text-success' : 
                                parseFloat(successRate) >= 40 ? 'text-warning' : 'text-danger';
        
        // Determine confidence color
        const confidenceColor = parseFloat(avgConfidence) >= 80 ? 'text-success' : 
                               parseFloat(avgConfidence) >= 60 ? 'text-info' : 'text-warning';
        
        div.innerHTML = `
            <div class="pattern-performance">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">${this.formatPatternName(performance.pattern_name)}</h6>
                    <small class="text-muted">Last: ${lastAlertTime}</small>
                </div>
                <div class="row">
                    <div class="col-4">
                        <div class="performance-metric">
                            <div class="performance-number">${totalAlerts}</div>
                            <div class="performance-label">Total Alerts</div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="performance-metric">
                            <div class="performance-number ${successRateColor}">${successRate}%</div>
                            <div class="performance-label">Success Rate</div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="performance-metric">
                            <div class="performance-number ${confidenceColor}">${avgConfidence}%</div>
                            <div class="performance-label">Avg Confidence</div>
                        </div>
                    </div>
                </div>
                ${avgReturnPercent !== '0.00' ? `
                <div class="row mt-2">
                    <div class="col-12">
                        <div class="performance-metric">
                            <div class="performance-number ${avgReturnPercent > 0 ? 'text-success' : 'text-danger'}">
                                ${avgReturnPercent > 0 ? '+' : ''}${avgReturnPercent}%
                            </div>
                            <div class="performance-label">Avg Return</div>
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>
        `;
        
        return div;
    }
    
    addPerformanceSummary(container, sortedPatterns) {
        // Add overall performance summary at the top
        const totalAlerts = sortedPatterns.reduce((sum, [_, perf]) => sum + (perf.total_alerts || 0), 0);
        const totalSuccessful = sortedPatterns.reduce((sum, [_, perf]) => sum + (perf.successful_alerts || 0), 0);
        const overallSuccessRate = totalAlerts > 0 ? (totalSuccessful / totalAlerts * 100).toFixed(1) : '0.0';
        const activePatterns = sortedPatterns.length;
        
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'col-12 mb-4';
        summaryDiv.innerHTML = `
            <div class="card bg-light">
                <div class="card-body">
                    <h5 class="card-title mb-3">
                        <i class="fas fa-chart-line me-2"></i>Performance Summary
                    </h5>
                    <div class="row text-center">
                        <div class="col-md-3">
                            <div class="performance-metric">
                                <div class="performance-number text-primary">${activePatterns}</div>
                                <div class="performance-label">Active Patterns</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="performance-metric">
                                <div class="performance-number text-info">${totalAlerts}</div>
                                <div class="performance-label">Total Alerts</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="performance-metric">
                                <div class="performance-number text-success">${totalSuccessful}</div>
                                <div class="performance-label">Successful</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="performance-metric">
                                <div class="performance-number ${parseFloat(overallSuccessRate) >= 50 ? 'text-success' : 'text-warning'}">
                                    ${overallSuccessRate}%
                                </div>
                                <div class="performance-label">Overall Success</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Insert at the beginning
        container.insertBefore(summaryDiv, container.firstChild);
    }
    
    renderHistory() {
        const container = document.getElementById('alert-history-list');
        
        if (this.alertHistory.length === 0) {
            container.innerHTML = `
                <div class="text-center p-4">
                    <i class="fas fa-history fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No alert history available.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = '';
        this.alertHistory.forEach(alert => {
            const item = this.createHistoryItem(alert);
            container.appendChild(item);
        });
    }
    
    createHistoryItem(alert) {
        const div = document.createElement('div');
        div.className = 'alert-history-item';
        
        const timestamp = new Date(alert.timestamp).toLocaleString();
        const priorityClass = this.getPriorityClass(alert.confidence);
        
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${this.formatPatternName(alert.pattern)} - ${alert.symbol}</h6>
                    <p class="mb-1 text-muted">${alert.description || 'Pattern detected'}</p>
                    <small class="text-muted">
                        <i class="fas fa-clock me-1"></i> ${timestamp}
                    </small>
                </div>
                <div class="text-end">
                    <span class="confidence-badge badge bg-primary mb-1">
                        ${alert.confidence}%
                    </span>
                    <div>
                        <small class="text-muted">$${alert.price || 'N/A'}</small>
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    populatePreferencesForm() {
        document.getElementById('confidence-threshold').value = this.preferences.confidence_threshold || 70;
        document.getElementById('confidence-value').textContent = (this.preferences.confidence_threshold || 70) + '%';
        
        document.getElementById('max-alerts-per-hour').value = this.preferences.max_alerts_per_hour || 20;
        document.getElementById('notify-browser').checked = this.preferences.browser_notifications !== false;
        document.getElementById('notify-sound').checked = this.preferences.sound_alerts || false;
        document.getElementById('priority-filter').value = this.preferences.priority_filter || 'all';
        
        if (this.preferences.quiet_hours) {
            document.getElementById('enable-quiet-hours').checked = true;
            document.getElementById('quiet-start').value = this.preferences.quiet_hours.start || '22:00';
            document.getElementById('quiet-end').value = this.preferences.quiet_hours.end || '07:00';
            this.toggleQuietHoursDisplay(true);
        }
    }
    
    updatePreferencePreview() {
        const confidence = document.getElementById('confidence-threshold').value;
        const maxAlerts = document.getElementById('max-alerts-per-hour').value;
        const browserNotifs = document.getElementById('notify-browser').checked;
        const soundAlerts = document.getElementById('notify-sound').checked;
        const priority = document.getElementById('priority-filter').value;
        
        document.getElementById('preview-confidence').textContent = confidence + '%';
        document.getElementById('preview-max-alerts').textContent = maxAlerts === '-1' ? 'Unlimited' : maxAlerts;
        
        const methods = [];
        if (browserNotifs) methods.push('Browser');
        if (soundAlerts) methods.push('Sound');
        document.getElementById('preview-methods').textContent = methods.join(', ') || 'None';
        
        const priorityText = {
            'all': 'All',
            'high': 'High Only',
            'medium-high': 'Medium & High'
        };
        document.getElementById('preview-priority').textContent = priorityText[priority] || 'All';
    }
    
    toggleQuietHoursDisplay(enabled) {
        const display = document.getElementById('quiet-hours-preview');
        if (enabled) {
            display.style.display = 'block';
            this.updateQuietHoursPreview();
        } else {
            display.style.display = 'none';
        }
    }
    
    updateQuietHoursPreview() {
        const start = document.getElementById('quiet-start').value;
        const end = document.getElementById('quiet-end').value;
        const text = document.getElementById('quiet-hours-text');
        
        if (start && end) {
            text.textContent = `${start} - ${end} (no alerts during this time)`;
        }
    }
    
    handlePatternAlert(data) {
        const alert = data.event;
        
        // Check if alert matches user preferences
        if (!this.shouldShowAlert(alert)) {
            return;
        }
        
        // Show browser notification if enabled
        if (this.preferences.browser_notifications !== false && 'Notification' in window && Notification.permission === 'granted') {
            this.showBrowserNotification(alert);
        }
        
        // Play sound if enabled
        if (this.preferences.sound_alerts) {
            this.playAlertSound();
        }
        
        // Update recent alerts display
        this.addRecentAlert(alert);
        
        // Update alert statistics
        this.updateQuickStats();
    }
    
    shouldShowAlert(alert) {
        // Check confidence threshold
        if (alert.data.confidence < (this.preferences.confidence_threshold || 70)) {
            return false;
        }
        
        // Check if pattern is subscribed
        const subscription = this.subscriptions.get(alert.data.pattern);
        if (!subscription || !subscription.active) {
            return false;
        }
        
        // Check symbol filter
        if (subscription.symbols && subscription.symbols.length > 0) {
            if (!subscription.symbols.includes(alert.data.symbol)) {
                return false;
            }
        }
        
        // Check quiet hours
        if (this.preferences.quiet_hours && this.isInQuietHours()) {
            return false;
        }
        
        return true;
    }
    
    isInQuietHours() {
        if (!this.preferences.quiet_hours || !document.getElementById('enable-quiet-hours').checked) {
            return false;
        }
        
        const now = new Date();
        const currentTime = now.getHours() * 60 + now.getMinutes();
        
        const start = this.timeToMinutes(this.preferences.quiet_hours.start);
        const end = this.timeToMinutes(this.preferences.quiet_hours.end);
        
        if (start > end) {
            // Quiet hours cross midnight
            return currentTime >= start || currentTime <= end;
        } else {
            return currentTime >= start && currentTime <= end;
        }
    }
    
    timeToMinutes(timeStr) {
        const [hours, minutes] = timeStr.split(':').map(Number);
        return hours * 60 + minutes;
    }
    
    showBrowserNotification(alert) {
        const title = `Pattern Alert: ${this.formatPatternName(alert.data.pattern)}`;
        const body = `${alert.data.symbol} - Confidence: ${alert.data.confidence}%`;
        const icon = '/static/images/tickstock-icon.png';
        
        const notification = new Notification(title, { body, icon });
        
        notification.onclick = () => {
            window.focus();
            notification.close();
        };
        
        setTimeout(() => {
            notification.close();
        }, 5000);
    }
    
    playAlertSound() {
        // Create and play alert sound
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.2);
    }
    
    async addSubscription() {
        const patternName = document.getElementById('pattern-name').value;
        const symbolFilter = document.getElementById('symbol-filter').value;
        const minConfidence = document.getElementById('min-confidence').value;
        
        if (!patternName) {
            this.showError('Please select a pattern');
            return;
        }
        
        const subscriptionData = {
            pattern_name: patternName,
            confidence: parseInt(minConfidence),
            symbols: symbolFilter ? symbolFilter.split(',').map(s => s.trim().toUpperCase()) : null,
            active: true
        };
        
        try {
            const response = await fetch('/api/tickstockpl/alerts/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscriptionData)
            });
            
            if (!response.ok) throw new Error('Failed to add subscription');
            
            const result = await response.json();
            this.showSuccess('Pattern subscription added successfully');
            
            // Close modal and refresh subscriptions
            const modal = bootstrap.Modal.getInstance(document.getElementById('addSubscriptionModal'));
            modal.hide();
            
            // Reset form
            document.getElementById('add-subscription-form').reset();
            document.getElementById('min-confidence-value').textContent = '70%';
            
            // Reload subscriptions
            this.loadSubscriptions();
            
        } catch (error) {
            console.error('Error adding subscription:', error);
            this.showError('Failed to add pattern subscription');
        }
    }
    
    async toggleSubscription(patternName) {
        const subscription = this.subscriptions.get(patternName);
        if (!subscription) return;
        
        const newActive = !subscription.active;
        
        try {
            const response = await fetch(`/api/tickstockpl/alerts/subscribe/${patternName}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active: newActive })
            });
            
            if (!response.ok) throw new Error('Failed to update subscription');
            
            subscription.active = newActive;
            this.showSuccess(`Pattern ${newActive ? 'activated' : 'deactivated'}`);
            this.updateQuickStats();
            
        } catch (error) {
            console.error('Error toggling subscription:', error);
            this.showError('Failed to update subscription');
            // Revert toggle
            document.getElementById(`toggle-${patternName}`).checked = subscription.active;
        }
    }
    
    async removeSubscription(patternName) {
        if (!confirm(`Are you sure you want to remove the ${this.formatPatternName(patternName)} subscription?`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/tickstockpl/alerts/subscribe/${patternName}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) throw new Error('Failed to remove subscription');
            
            this.subscriptions.delete(patternName);
            this.showSuccess('Pattern subscription removed');
            this.renderSubscriptions();
            this.updateQuickStats();
            
        } catch (error) {
            console.error('Error removing subscription:', error);
            this.showError('Failed to remove subscription');
        }
    }
    
    async savePreferences() {
        const preferences = {
            confidence_threshold: parseInt(document.getElementById('confidence-threshold').value),
            max_alerts_per_hour: parseInt(document.getElementById('max-alerts-per-hour').value),
            browser_notifications: document.getElementById('notify-browser').checked,
            sound_alerts: document.getElementById('notify-sound').checked,
            priority_filter: document.getElementById('priority-filter').value,
            quiet_hours: document.getElementById('enable-quiet-hours').checked ? {
                start: document.getElementById('quiet-start').value,
                end: document.getElementById('quiet-end').value
            } : null
        };
        
        try {
            const response = await fetch('/api/tickstockpl/alerts/preferences', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ preferences })
            });
            
            if (!response.ok) throw new Error('Failed to save preferences');
            
            this.preferences = preferences;
            this.showSuccess('Preferences saved successfully');
            
        } catch (error) {
            console.error('Error saving preferences:', error);
            this.showError('Failed to save preferences');
        }
    }
    
    resetPreferences() {
        if (!confirm('Are you sure you want to reset all preferences to defaults?')) {
            return;
        }
        
        this.preferences = this.getDefaultPreferences();
        this.populatePreferencesForm();
        this.updatePreferencePreview();
        this.showSuccess('Preferences reset to defaults');
    }
    
    getDefaultPreferences() {
        return {
            confidence_threshold: 70,
            max_alerts_per_hour: 20,
            browser_notifications: true,
            sound_alerts: false,
            priority_filter: 'all',
            quiet_hours: null
        };
    }
    
    updateQuickStats() {
        const activeCount = Array.from(this.subscriptions.values()).filter(s => s.active).length;
        document.getElementById('active-subscriptions').textContent = activeCount;
        
        // Count today's alerts (this would come from the backend in real implementation)
        const today = new Date().toDateString();
        const todayAlerts = this.alertHistory.filter(alert => 
            new Date(alert.timestamp).toDateString() === today
        ).length;
        document.getElementById('alerts-today').textContent = todayAlerts;
    }
    
    addRecentAlert(alert) {
        const container = document.getElementById('recent-alerts');
        
        if (!container.firstChild || container.children.length === 0) {
            container.innerHTML = '';
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.className = 'mb-2 p-2 border rounded';
        alertDiv.innerHTML = `
            <small>
                <strong>${this.formatPatternName(alert.data.pattern)}</strong><br>
                ${alert.data.symbol} - ${alert.data.confidence}%<br>
                <span class="text-muted">${new Date().toLocaleTimeString()}</span>
            </small>
        `;
        
        container.insertBefore(alertDiv, container.firstChild);
        
        // Keep only last 5 alerts
        while (container.children.length > 5) {
            container.removeChild(container.lastChild);
        }
    }
    
    formatPatternName(patternName) {
        return patternName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    
    getPriorityClass(confidence) {
        if (confidence >= 85) return 'alert-priority-high';
        if (confidence >= 70) return 'alert-priority-medium';
        return 'alert-priority-low';
    }
    
    updateConnectionStatus(connected) {
        const indicator = document.querySelector('.real-time-indicator');
        if (indicator) {
            indicator.style.backgroundColor = connected ? '#28a745' : '#dc3545';
        }
    }
    
    filterHistory(filter) {
        // This would filter the displayed history based on the selected filter
        // Implementation would depend on backend support
        console.log('Filtering history by:', filter);
    }
    
    loadMoreHistory() {
        const currentLength = this.alertHistory.length;
        this.loadHistory(50, currentLength);
    }
    
    exportHistory() {
        // Export alert history as CSV
        const csv = this.convertHistoryToCSV();
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `pattern_alert_history_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        
        window.URL.revokeObjectURL(url);
    }
    
    convertHistoryToCSV() {
        const headers = ['Timestamp', 'Pattern', 'Symbol', 'Confidence', 'Price', 'Description'];
        const rows = this.alertHistory.map(alert => [
            new Date(alert.timestamp).toISOString(),
            alert.pattern,
            alert.symbol,
            alert.confidence,
            alert.price || '',
            alert.description || ''
        ]);
        
        return [headers, ...rows].map(row => row.join(',')).join('\n');
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'danger');
    }
    
    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // Add to page (create toast container if doesn't exist)
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        container.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

// Make PatternAlertsManager globally available
window.PatternAlertsManager = PatternAlertsManager;