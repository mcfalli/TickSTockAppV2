// ==========================================================================
// APP-GAUGES.JS - ENHANCED VERSION WITH DYNAMIC AUTO-SCALING
// Removed: TickStockGauge, PressureBarManager, DualUniverseGaugeManager
// Kept: SmoothPercentageBar for standalone percentage bar
// Enhanced: ActivityVelocityDashboard with dynamic scaling for test/production
// ==========================================================================

// File-level debug flag - set to true to enable optional debug logging
const GAUGE_DEBUG = false;

// ==========================================================================
// ACTIVITY VELOCITY DASHBOARD - With Dynamic Auto-Scaling
// ==========================================================================

// Debug flag for tooltips - set to false to hide tick counts
const SHOW_TICK_TOOLTIPS = true;

class ActivityVelocityDashboard {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.isInitialized = false;
        
        // Data tracking
        this.currentData = {
            tickRate: 0,
            ticksHistory: [],
            activityLevel: 'medium',
            trend: 'stable',
            timeWindows: {
                '10s': { ticks: 0, trend: 'stable', history: [] },
                '30s': { ticks: 0, trend: 'stable', history: [] },
                '60s': { ticks: 0, trend: 'stable', history: [] },
                '5m': { ticks: 0, trend: 'stable', history: [] }
            }
        };
        
        // Dynamic scaling parameters
        this.scaling = {
            mode: 'production',  // 'auto', 'test', 'production'
            maxObserved: 0,
            minObserved: Infinity,
            history: [],
            calibrationPeriod: 30000, // 30 seconds to calibrate
            lastCalibration: Date.now(),
            environmentDetected: null
        };
        
        // Base thresholds (percentage of max scale)
        this.baseThresholds = {
            extreme: 0.75,   // 75% of max
            veryHigh: 0.50,  // 50% of max
            high: 0.30,      // 30% of max
            medium: 0.15,    // 15% of max
            low: 0.075       // 7.5% of max
        };
        
        // Environment presets
        this.presets = {
            test: {
                maxScale: 2100,
                thresholds: {
                    extreme: 1500,
                    veryHigh: 1000,
                    high: 600,
                    medium: 300,
                    low: 150
                },
                markers: [300, 900, 1500, 2100]
            },
            production: {
                maxScale: 60000,  // Scaled for real production volumes
                thresholds: {
                    extreme: 50000,   // Major news/events
                    veryHigh: 35000,  // Very high activity
                    high: 25000,      // High activity  
                    medium: 15000,    // Normal active trading (17k fits here)
                    low: 7500         // Light activity
                },
                markers: [10000, 20000, 40000, 60000]
            }
        };
        
        // Start with test defaults
        this.currentScale = this.presets.test.maxScale;
        this.thresholds = { ...this.presets.test.thresholds };
        this.currentMarkers = [...this.presets.test.markers];
        
        // Animation
        this.animationFrame = null;
        this.lastUpdate = Date.now();
        this.tooltips = new Map();
        
        this.initialize();
    }
    
    initialize() {
        if (!this.container) {
            console.error(`ActivityVelocityDashboard: Container ${this.containerId} not found`);
            return;
        }
        
        // Clear existing content
        this.container.innerHTML = '';
        
        // Build new L-shaped dashboard
        this.buildDashboard();
        this.attachEventListeners();
        this.isInitialized = true;
        
        // Start animation loop
        this.startAnimation();
        
        if (GAUGE_DEBUG) {
            console.log('ActivityVelocityDashboard: Initialized with auto-scaling enabled');
        }
    }
    
    buildDashboard() {
        // Build markers HTML dynamically
        const markersHTML = this.currentMarkers.map((value, index) => {
            const positions = [10, 40, 70, 90];
            const displayValue = this.formatMarkerValue(value);
            return `<span class="marker-vertical" style="bottom: ${positions[index]}%" data-marker-index="${index}">${displayValue}</span>`;
        }).join('');
        
        this.container.innerHTML = `
            <div class="velocity-dashboard">
                <h5>Activity Monitor <span class="scaling-indicator" id="scaling-indicator"></span></h5>
                
                <!-- Left Section: Vertical Velocity Bar -->
                <div class="velocity-left-section">
                    <div class="velocity-bar-label">Ticks/Min</div>
                    <div class="velocity-bar-vertical-container" ${SHOW_TICK_TOOLTIPS ? 'data-tooltip="velocity-main"' : ''}>
                        <div class="velocity-fill-vertical" id="velocity-fill-vertical"></div>
                        <div class="velocity-speed-lines" id="velocity-speed-lines">
                            <div class="speed-line"></div>
                            <div class="speed-line"></div>
                            <div class="speed-line"></div>
                            <div class="speed-line"></div>
                            <div class="speed-line"></div>
                            <div class="speed-line"></div>
                        </div>
                        <div class="velocity-markers-vertical" id="velocity-markers">
                            ${markersHTML}
                        </div>
                    </div>
                </div>
                
                <!-- Right Section: Horizontal Time Window Bars (Moved Up) -->
                <div class="velocity-right-section">
                    <div class="time-window-item">
                        <span class="time-window-label">10 sec</span>
                        <div class="time-bar-container" ${SHOW_TICK_TOOLTIPS ? 'data-tooltip="ticks-10s"' : ''}>
                            <div class="time-bar-fill" id="bar-10s"></div>
                        </div>
                        <div class="time-window-trend stable" id="trend-10s">→</div>
                    </div>
                    
                    <div class="time-window-item">
                        <span class="time-window-label">30 sec</span>
                        <div class="time-bar-container" ${SHOW_TICK_TOOLTIPS ? 'data-tooltip="ticks-30s"' : ''}>
                            <div class="time-bar-fill" id="bar-30s"></div>
                        </div>
                        <div class="time-window-trend stable" id="trend-30s">→</div>
                    </div>
                    
                    <div class="time-window-item">
                        <span class="time-window-label">1 min</span>
                        <div class="time-bar-container" ${SHOW_TICK_TOOLTIPS ? 'data-tooltip="ticks-60s"' : ''}>
                            <div class="time-bar-fill" id="bar-60s"></div>
                        </div>
                        <div class="time-window-trend stable" id="trend-60s">→</div>
                    </div>
                    
                    <div class="time-window-item">
                        <span class="time-window-label">5 min</span>
                        <div class="time-bar-container" ${SHOW_TICK_TOOLTIPS ? 'data-tooltip="ticks-5m"' : ''}>
                            <div class="time-bar-fill" id="bar-5m"></div>
                        </div>
                        <div class="time-window-trend stable" id="trend-5m">→</div>
                    </div>
                    
                    <!-- Center Section: Main Trend Indicator (Moved Down) -->
                    <div class="velocity-center-section">
                        <div class="trend-indicator-main" id="trend-indicator-main">
                            <div class="trend-arrow-main stable" id="trend-arrow-main">→</div>
                        </div>
                        <div class="trend-label-main" id="trend-label-main">STABLE</div>
                    </div>
                </div>
                
                <!-- Activity Level Indicator -->
                <div class="activity-level-indicator medium" id="activity-level">
                    <span class="level-text">MEDIUM ACTIVITY</span>
                </div>
                
                ${SHOW_TICK_TOOLTIPS ? '<div class="velocity-tooltip" id="velocity-tooltip"></div>' : ''}
            </div>
        `;
    }
    
    formatMarkerValue(value) {
        if (value >= 10000) {
            return `${(value / 1000).toFixed(0)}k`;
        } else if (value >= 1000) {
            return `${(value / 1000).toFixed(1)}k`.replace('.0k', 'k');
        }
        return value.toString();
    }
    
    attachEventListeners() {
        // Add hover listeners for tooltips only if debug flag is enabled
        if (SHOW_TICK_TOOLTIPS) {
            const tooltipElements = this.container.querySelectorAll('[data-tooltip]');
            
            tooltipElements.forEach(element => {
                element.addEventListener('mouseenter', (e) => this.showTooltip(e));
                element.addEventListener('mousemove', (e) => this.updateTooltipPosition(e));
                element.addEventListener('mouseleave', () => this.hideTooltip());
            });
        }
    }
    
    updateData(data) {
        if (!this.isInitialized) return;
        
        try {
            const activityData = data.activity || {};
            const coreAnalytics = data.core_analytics || {};
            
            // Extract tick rates
            const tickRate = activityData.activity_ratio?.current_rate || 0;
            const ticks10s = activityData.ticks_10sec || 0;
            const ticks30s = activityData.ticks_30sec || 0;
            const ticks60s = activityData.ticks_60sec || 0;
            const ticks300s = activityData.ticks_300sec || 0;
            
            // Update scaling based on observed data
            this.updateScaling(tickRate);
            
            // Store historical data for trend calculation
            this.updateHistoricalData('10s', ticks10s);
            this.updateHistoricalData('30s', ticks30s);
            this.updateHistoricalData('60s', ticks60s);
            this.updateHistoricalData('5m', ticks300s);
            
            // Calculate trends
            const mainTrend = this.calculateMainTrend(tickRate);
            
            // Update current data
            this.currentData = {
                tickRate,
                activityLevel: this.calculateActivityLevel(tickRate),
                trend: mainTrend,
                timeWindows: {
                    '10s': { 
                        ticks: ticks10s, 
                        trend: this.calculateWindowTrend('10s'),
                        history: this.currentData.timeWindows['10s'].history 
                    },
                    '30s': { 
                        ticks: ticks30s, 
                        trend: this.calculateWindowTrend('30s'),
                        history: this.currentData.timeWindows['30s'].history 
                    },
                    '60s': { 
                        ticks: ticks60s, 
                        trend: this.calculateWindowTrend('60s'),
                        history: this.currentData.timeWindows['60s'].history 
                    },
                    '5m': { 
                        ticks: ticks300s, 
                        trend: this.calculateWindowTrend('5m'),
                        history: this.currentData.timeWindows['5m'].history 
                    }
                }
            };
            
            // Update UI
            this.updateDisplay();
            
        } catch (error) {
            console.error('ActivityVelocityDashboard: Error updating data', error);
        }
    }
    
    updateScaling(tickRate) {
        // Track historical data
        this.scaling.history.push({
            value: tickRate,
            timestamp: Date.now()
        });
        
        // Keep only last 5 minutes
        const fiveMinutesAgo = Date.now() - 300000;
        this.scaling.history = this.scaling.history.filter(
            item => item.timestamp > fiveMinutesAgo
        );
        
        // Update observed range
        if (tickRate > 0) {
            this.scaling.maxObserved = Math.max(this.scaling.maxObserved, tickRate);
            this.scaling.minObserved = Math.min(this.scaling.minObserved, tickRate);
        }
        
        // Auto-detect environment and scale after calibration period
        if (this.scaling.mode === 'auto') {
            const now = Date.now();
            if (now - this.scaling.lastCalibration > this.scaling.calibrationPeriod) {
                this.calibrateScale();
                this.scaling.lastCalibration = now;
            }
        }
    }
    
    calibrateScale() {
        if (this.scaling.history.length < 10) return; // Need minimum data
        
        // Calculate percentiles for better scaling
        const values = this.scaling.history.map(h => h.value).filter(v => v > 0).sort((a, b) => a - b);
        if (values.length === 0) return;
        
        const p95 = values[Math.floor(values.length * 0.95)] || this.scaling.maxObserved;
        const p50 = values[Math.floor(values.length * 0.50)] || 0;
        const p75 = values[Math.floor(values.length * 0.75)] || 0;
        
        // Detect environment based on data characteristics
        let detectedEnvironment = null;
        
        // Adjusted thresholds for environment detection
        if (p95 > 10000 || this.scaling.maxObserved > 12000) {
            // Production environment detected (raised from 5000/8000)
            detectedEnvironment = 'production';
            if (this.scaling.environmentDetected !== 'production') {
                //console.log('ActivityVelocityDashboard: Production environment detected (95th percentile:', p95, ')');
                this.applyPreset('production');
                this.scaling.environmentDetected = 'production';
            }
        } else if (p95 < 3000 && this.scaling.maxObserved < 4000) {
            // Test environment
            detectedEnvironment = 'test';
            if (this.scaling.environmentDetected !== 'test') {
                //console.log('ActivityVelocityDashboard: Test environment detected (95th percentile:', p95, ')');
                this.applyPreset('test');
                this.scaling.environmentDetected = 'test';
            }
        } else {
            // Hybrid or transitioning - use custom scaling
            detectedEnvironment = 'custom';
            
            // Calculate a custom scale that accommodates observed data
            const suggestedMax = Math.max(p95 * 1.5, this.scaling.maxObserved * 1.2);
            this.currentScale = Math.ceil(suggestedMax / 1000) * 1000; // Round up to nearest 1000
            
            // Ensure minimum scale
            this.currentScale = Math.max(this.currentScale, 3000);
            
            // Calculate dynamic thresholds
            this.thresholds = {
                extreme: this.currentScale * this.baseThresholds.extreme,
                veryHigh: this.currentScale * this.baseThresholds.veryHigh,
                high: this.currentScale * this.baseThresholds.high,
                medium: this.currentScale * this.baseThresholds.medium,
                low: this.currentScale * this.baseThresholds.low
            };
            
            // Calculate custom markers
            this.currentMarkers = [
                Math.round(this.currentScale * 0.17),
                Math.round(this.currentScale * 0.33),
                Math.round(this.currentScale * 0.67),
                this.currentScale
            ];
            
            if (this.scaling.environmentDetected !== 'custom') {
                console.log('ActivityVelocityDashboard: Custom scaling applied (scale:', this.currentScale, ')');
                this.scaling.environmentDetected = 'custom';
            }
            
            // Update UI markers
            this.updateScaleMarkers();
        }
        
        // Update scaling indicator
        this.updateScalingIndicator(detectedEnvironment);
    }
    
    applyPreset(presetName) {
        if (this.presets[presetName]) {
            this.currentScale = this.presets[presetName].maxScale;
            this.thresholds = { ...this.presets[presetName].thresholds };
            this.currentMarkers = [...this.presets[presetName].markers];
            this.updateScaleMarkers();
            
            if (GAUGE_DEBUG) {
                console.log(`ActivityVelocityDashboard: Applied ${presetName} preset (scale: ${this.currentScale})`);
            }
        }
    }
    
    updateScaleMarkers() {
        // Dynamically update the vertical bar markers
        const markersContainer = document.getElementById('velocity-markers');
        if (markersContainer) {
            const positions = [10, 40, 70, 90];
            const markersHTML = this.currentMarkers.map((value, index) => {
                const displayValue = this.formatMarkerValue(value);
                return `<span class="marker-vertical" style="bottom: ${positions[index]}%" data-marker-index="${index}">${displayValue}</span>`;
            }).join('');
            
            markersContainer.innerHTML = markersHTML;
        }
    }
    
    updateScalingIndicator(environment) {
        const indicator = document.getElementById('scaling-indicator');
        if (indicator) {
            let text = '';
            let className = '';
            
            switch(environment) {
                case 'production':
                    text = '(Production)';
                    className = 'production-mode';
                    break;
                case 'test':
                    text = '(Test)';
                    className = 'test-mode';
                    break;
                case 'custom':
                    text = `(Auto: ${this.formatMarkerValue(this.currentScale)})`;
                    className = 'custom-mode';
                    break;
            }
            
            indicator.textContent = text;
            indicator.className = `scaling-indicator ${className}`;
        }
    }
    
    updateHistoricalData(window, value) {
        const history = this.currentData.timeWindows[window].history;
        history.push({ value, timestamp: Date.now() });
        
        // Keep only last 5 minutes of data
        const fiveMinutesAgo = Date.now() - 300000;
        this.currentData.timeWindows[window].history = history.filter(
            item => item.timestamp > fiveMinutesAgo
        );
    }
    
    calculateMainTrend(currentRate) {
        const previousRate = this.currentData.tickRate;
        if (currentRate > previousRate * 1.2) return 'up';
        if (currentRate < previousRate * 0.8) return 'down';
        return 'stable';
    }
    
    calculateWindowTrend(window) {
        const history = this.currentData.timeWindows[window].history;
        if (history.length < 2) return 'stable';
        
        // Get values from 30 seconds ago vs now
        const thirtySecondsAgo = Date.now() - 30000;
        const oldValues = history.filter(item => 
            item.timestamp < thirtySecondsAgo + 5000 && item.timestamp >= thirtySecondsAgo - 5000
        );
        const recentValues = history.slice(-5);
        
        if (oldValues.length === 0 || recentValues.length === 0) return 'stable';
        
        const oldAvg = oldValues.reduce((sum, item) => sum + item.value, 0) / oldValues.length;
        const recentAvg = recentValues.reduce((sum, item) => sum + item.value, 0) / recentValues.length;
        
        if (recentAvg > oldAvg * 1.2) return 'up';
        if (recentAvg < oldAvg * 0.8) return 'down';
        return 'stable';
    }
    
    calculateActivityLevel(tickRate) {
        if (tickRate >= this.thresholds.extreme) return 'extreme';
        if (tickRate >= this.thresholds.veryHigh) return 'very-high';
        if (tickRate >= this.thresholds.high) return 'high';
        if (tickRate >= this.thresholds.medium) return 'medium';
        if (tickRate >= this.thresholds.low) return 'low';
        return 'minimal';
    }
    
    updateDisplay() {
        // Update vertical velocity bar with dynamic scaling
        const velocityFill = document.getElementById('velocity-fill-vertical');
        if (velocityFill) {
            // Use current scale for percentage calculation
            const percentage = Math.min((this.currentData.tickRate / this.currentScale) * 100, 100);
            velocityFill.style.height = `${percentage}%`;
            
            // Add visual indicator if we're near max scale
            velocityFill.classList.toggle('near-max', percentage > 90);
            
            // Store actual percentage for debugging
            velocityFill.dataset.percentage = percentage.toFixed(1);
            velocityFill.dataset.tickRate = this.currentData.tickRate;
            velocityFill.dataset.scale = this.currentScale;
        }
        
        // Update speed lines effect
        const speedLines = document.getElementById('velocity-speed-lines');
        if (speedLines) {
            const shouldActivate = this.currentData.activityLevel === 'extreme' || 
                                 this.currentData.activityLevel === 'very-high';
            speedLines.classList.toggle('active', shouldActivate);
        }
        
        // Update main trend indicator
        this.updateMainTrend();
        
        // Update time window bars
        this.updateTimeWindowBars();
        
        // Update activity level
        this.updateActivityLevel();
    }
    
    updateMainTrend() {
        const trendArrow = document.getElementById('trend-arrow-main');
        const trendIndicator = document.getElementById('trend-indicator-main');
        const trendLabel = document.getElementById('trend-label-main');
        
        if (trendArrow) {
            trendArrow.className = `trend-arrow-main ${this.currentData.trend}`;
            trendArrow.textContent = this.currentData.trend === 'up' ? '↗' : 
                                    this.currentData.trend === 'down' ? '↘' : '→';
        }
        
        if (trendIndicator) {
            // Add pulse effect for high activity
            const shouldPulse = this.currentData.activityLevel === 'extreme' || 
                              this.currentData.activityLevel === 'very-high';
            trendIndicator.classList.toggle('pulse', shouldPulse);
        }
        
        if (trendLabel) {
            trendLabel.textContent = this.currentData.trend.toUpperCase();
        }
    }
    
    updateTimeWindowBars() {
        // Calculate expected ratios between time windows
        const data = this.currentData.timeWindows;
        
        // Find the maximum tick rate per second across all windows
        const tickRates = {
            '10s': data['10s'].ticks / 10,
            '30s': data['30s'].ticks / 30,
            '60s': data['60s'].ticks / 60,
            '5m': data['5m'].ticks / 300
        };
        
        const maxTickRate = Math.max(...Object.values(tickRates));
        
        // Scale bars based on their tick rate relative to max
        Object.entries(this.currentData.timeWindows).forEach(([window, windowData]) => {
            const barId = window === '5m' ? 'bar-5m' : `bar-${window}`;
            const bar = document.getElementById(barId);
            
            if (bar) {
                // Calculate percentage based on tick rate, not absolute counts
                const windowSeconds = {
                    '10s': 10,
                    '30s': 30,
                    '60s': 60,
                    '5m': 300
                };
                
                const tickRate = windowData.ticks / windowSeconds[window];
                const basePercentage = maxTickRate > 0 ? (tickRate / maxTickRate) * 70 : 0;
                
                // Enhanced volatility and sensitivity for shorter windows
                let adjustedPercentage = basePercentage;
                
                if (window === '10s') {
                    // Dynamic volatility based on environment
                    const volatilityThreshold = this.scaling.environmentDetected === 'production' ? 50 : 50;
                    
                    if (tickRate > volatilityThreshold) {
                        // Active market volatility
                        const volatility = (Math.sin(Date.now() / 2000) * 0.15);
                        const amplification = 1.3;
                        adjustedPercentage = basePercentage * amplification + (volatility * 50);
                        
                        // Add micro-fluctuations
                        const microFluctuation = (Math.random() - 0.5) * 8;
                        adjustedPercentage += microFluctuation;
                    } else {
                        // Minimal amplification for quiet markets
                        adjustedPercentage = basePercentage * 1.05;
                        const microFluctuation = (Math.random() - 0.5) * 2;
                        adjustedPercentage += microFluctuation;
                    }
                    
                } else if (window === '30s') {
                    // Dynamic volatility for 30s window
                    const volatilityThreshold = this.scaling.environmentDetected === 'production' ? 40 : 40;
                    
                    if (tickRate > volatilityThreshold) {
                        const volatility = (Math.sin(Date.now() / 4000) * 0.08);
                        const amplification = 1.15;
                        adjustedPercentage = basePercentage * amplification + (volatility * 30);
                        
                        const microFluctuation = (Math.random() - 0.5) * 4;
                        adjustedPercentage += microFluctuation;
                    } else {
                        adjustedPercentage = basePercentage * 1.03;
                        const microFluctuation = (Math.random() - 0.5) * 1;
                        adjustedPercentage += microFluctuation;
                    }
                    
                } else if (window === '60s') {
                    // 60s: Slight volatility only in active markets
                    const volatilityThreshold = this.scaling.environmentDetected === 'production' ? 30 : 30;
                    
                    if (tickRate > volatilityThreshold) {
                        const amplification = 1.05;
                        adjustedPercentage = basePercentage * amplification;
                    } else {
                        adjustedPercentage = basePercentage;
                    }
                    
                } else {
                    // 5m: Stable baseline - no amplification
                    adjustedPercentage = basePercentage;
                }
                
                // Ensure percentage stays within bounds
                adjustedPercentage = Math.max(5, Math.min(100, adjustedPercentage));
                bar.style.width = `${adjustedPercentage}%`;
                
                // Add visual feedback classes based on activity
                bar.classList.remove('surging', 'dropping', 'active');
                
                if (window === '10s' || window === '30s') {
                    // Add classes for visual effects on short windows
                    if (adjustedPercentage > 85) {
                        bar.classList.add('surging');
                    } else if (adjustedPercentage < 25) {
                        bar.classList.add('dropping');
                    } else if (adjustedPercentage > 30) {
                        bar.classList.add('active');
                    }
                } else {
                    // Longer windows just show active state
                    if (adjustedPercentage > 30) {
                        bar.classList.add('active');
                    }
                }
                
                // Store debug data
                bar.dataset.percentage = adjustedPercentage.toFixed(1);
                bar.dataset.ticks = windowData.ticks;
                bar.dataset.tickRate = tickRate.toFixed(2);
            }
            
            // Update trend arrow
            const trendId = window === '5m' ? 'trend-5m' : `trend-${window}`;
            const trend = document.getElementById(trendId);
            if (trend) {
                trend.className = `time-window-trend ${windowData.trend}`;
                trend.textContent = windowData.trend === 'up' ? '↗' : 
                                  windowData.trend === 'down' ? '↘' : '→';
            }
        });
    }
    
    updateActivityLevel() {
        const levelElement = document.getElementById('activity-level');
        if (levelElement) {
            const level = this.currentData.activityLevel;
            levelElement.className = `activity-level-indicator ${level}`;
            
            const levelText = levelElement.querySelector('.level-text');
            if (levelText) {
                let displayText = `${level.replace('-', ' ').toUpperCase()} ACTIVITY`;
                
                // Add tick rate to display only if debug is enabled and in production mode
                if (GAUGE_DEBUG && this.scaling.environmentDetected === 'production' && this.currentData.tickRate > 1000) {
                    const formattedRate = this.formatMarkerValue(Math.round(this.currentData.tickRate));
                    displayText += ` (${formattedRate}/min)`;
                }
                
                levelText.textContent = displayText;
            }
        }
    }
    
    showTooltip(event) {
        const tooltip = document.getElementById('velocity-tooltip');
        if (!tooltip) return;
        
        const target = event.currentTarget;
        const tooltipType = target.dataset.tooltip;
        let content = '';
        
        switch (tooltipType) {
            case 'velocity-main':
                const rate = Math.round(this.currentData.tickRate);
                const formattedRate = rate > 1000 ? this.formatMarkerValue(rate) : rate;
                content = `${formattedRate} ticks/min (Scale: ${this.formatMarkerValue(this.currentScale)})`;
                break;
            case 'ticks-10s':
                content = `${this.currentData.timeWindows['10s'].ticks} ticks in 10s`;
                break;
            case 'ticks-30s':
                content = `${this.currentData.timeWindows['30s'].ticks} ticks in 30s`;
                break;
            case 'ticks-60s':
                content = `${this.currentData.timeWindows['60s'].ticks} ticks in 60s`;
                break;
            case 'ticks-5m':
                content = `${this.currentData.timeWindows['5m'].ticks} ticks in 5m`;
                break;
        }
        
        tooltip.textContent = content;
        tooltip.classList.add('show');
        this.updateTooltipPosition(event);
    }
    
    updateTooltipPosition(event) {
        const tooltip = document.getElementById('velocity-tooltip');
        if (!tooltip) return;
        
        const rect = this.container.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        tooltip.style.left = `${x + 10}px`;
        tooltip.style.top = `${y - 30}px`;
    }
    
    hideTooltip() {
        const tooltip = document.getElementById('velocity-tooltip');
        if (tooltip) {
            tooltip.classList.remove('show');
        }
    }
    
    // Manual control methods for testing
    setScalingMode(mode) {
        if (mode === 'auto') {
            this.scaling.mode = 'auto';
            this.scaling.lastCalibration = Date.now();
            console.log('ActivityVelocityDashboard: Scaling mode set to auto');
        } else if (this.presets[mode]) {
            this.scaling.mode = mode;
            this.applyPreset(mode);
            console.log(`ActivityVelocityDashboard: Scaling mode set to ${mode}`);
        } else {
            console.warn(`ActivityVelocityDashboard: Invalid scaling mode '${mode}'`);
        }
    }
    
    getScalingInfo() {
        return {
            mode: this.scaling.mode,
            environment: this.scaling.environmentDetected,
            currentScale: this.currentScale,
            maxObserved: this.scaling.maxObserved,
            thresholds: this.thresholds,
            markers: this.currentMarkers
        };
    }
    
    startAnimation() {
        const animate = () => {
            // Could add continuous animations here if needed
            this.animationFrame = requestAnimationFrame(animate);
        };
        animate();
    }
    
    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.scaling.history = [];
        console.log('ActivityVelocityDashboard: Destroyed');
    }
}

// ==========================================================================
// SMOOTH PERCENTAGE BAR SYSTEM - KEPT FOR STANDALONE PERCENTAGE BAR
// ==========================================================================

class SmoothPercentageBar {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.highFill = document.getElementById('high-percent-fill');
        this.lowFill = document.getElementById('low-percent-fill');
        this.highLabel = document.getElementById('high-percent-label');
        this.lowLabel = document.getElementById('low-percent-label');
        
        // Smoothing parameters
        this.currentHighPercent = 50;
        this.currentLowPercent = 50;
        this.targetHighPercent = 50;
        this.targetLowPercent = 50;
        this.smoothingFactor = 0.15; // Higher = faster transitions (0.1-0.3 range)
        this.animationId = null;
        this.lastUpdate = Date.now();
        this.isAnimating = false;
        
        // Data validation
        this.minPercentage = 0;
        this.maxPercentage = 100;
        this.updateThreshold = 0.1; // Only update if change > 0.1%
        
        this.initializeBar();
    }
    
    initializeBar() {
        if (!this.container || !this.highFill || !this.lowFill) {
            console.warn('SmoothPercentageBar: Required elements not found');
            return false;
        }
        
        // Set initial state
        this.updateVisualElements(50, 50);
        if (GAUGE_DEBUG) console.log('SmoothPercentageBar: Initialized successfully');
        return true;
    }
    
    updatePercentages(highPercentage, lowPercentage, totalHighs = 0, totalLows = 0) {
        // Validate and clamp input values
        const validHigh = Math.max(this.minPercentage, Math.min(this.maxPercentage, highPercentage || 0));
        const validLow = Math.max(this.minPercentage, Math.min(this.maxPercentage, lowPercentage || 0));
        
        // Check if update is significant enough
        const highDelta = Math.abs(validHigh - this.targetHighPercent);
        const lowDelta = Math.abs(validLow - this.targetLowPercent);
        
        if (highDelta < this.updateThreshold && lowDelta < this.updateThreshold) {
            return; // Skip insignificant updates
        }
        
        // Set new targets
        this.targetHighPercent = validHigh;
        this.targetLowPercent = validLow;
        this.lastUpdate = Date.now();
        
        // Start smooth animation if not already running
        if (!this.isAnimating) {
            this.startSmoothAnimation();
        }
        
        // Update labels immediately (they don't need smoothing)
        this.updateLabels(validHigh, validLow);
    }
    
    startSmoothAnimation() {
        if (this.isAnimating) return;
        
        this.isAnimating = true;
        this.animateToTarget();
    }
    
    animateToTarget() {
        const now = Date.now();
        const deltaTime = Math.min(now - this.lastUpdate, 100); // Cap at 100ms
        
        // Calculate smooth interpolation
        const highDelta = this.targetHighPercent - this.currentHighPercent;
        const lowDelta = this.targetLowPercent - this.currentLowPercent;
        
        // Apply smoothing factor (exponential moving average style)
        const smoothStep = this.smoothingFactor * (deltaTime / 16.67); // Normalize to 60fps
        
        this.currentHighPercent += highDelta * smoothStep;
        this.currentLowPercent += lowDelta * smoothStep;
        
        // Update visual elements
        this.updateVisualElements(this.currentHighPercent, this.currentLowPercent);
        
        // Check if we're close enough to target (within 0.1%)
        const highRemaining = Math.abs(this.targetHighPercent - this.currentHighPercent);
        const lowRemaining = Math.abs(this.targetLowPercent - this.currentLowPercent);
        
        if (highRemaining > 0.1 || lowRemaining > 0.1) {
            // Continue animation
            this.animationId = requestAnimationFrame(() => this.animateToTarget());
        } else {
            // Animation complete - snap to final values
            this.currentHighPercent = this.targetHighPercent;
            this.currentLowPercent = this.targetLowPercent;
            this.updateVisualElements(this.currentHighPercent, this.currentLowPercent);
            this.isAnimating = false;
            
            if (this.animationId) {
                cancelAnimationFrame(this.animationId);
                this.animationId = null;
            }
        }
    }
    
    updateVisualElements(highPercent, lowPercent) {
        if (!this.highFill || !this.lowFill) return;
        
        // Update fill widths with smooth values
        this.highFill.style.width = `${highPercent.toFixed(1)}%`;
        this.lowFill.style.width = `${lowPercent.toFixed(1)}%`;
        
        // Add subtle visual feedback classes
        this.highFill.classList.add('smooth-updating');
        this.lowFill.classList.add('smooth-updating');
        
        // Remove classes after a short delay
        setTimeout(() => {
            if (this.highFill) this.highFill.classList.remove('smooth-updating');
            if (this.lowFill) this.lowFill.classList.remove('smooth-updating');
        }, 100);
    }
    
    updateLabels(highPercent, lowPercent) {
        if (this.highLabel) {
            this.highLabel.textContent = `${highPercent.toFixed(1)}%`;
        }
        if (this.lowLabel) {
            this.lowLabel.textContent = `${lowPercent.toFixed(1)}%`;
        }
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        this.isAnimating = false;
        if (GAUGE_DEBUG) console.log('SmoothPercentageBar: Destroyed');
    }
}

// ==========================================================================
// GLOBAL EXPORTS AND INITIALIZATION
// ==========================================================================

// Export for use
window.ActivityVelocityDashboard = ActivityVelocityDashboard;
window.SmoothPercentageBar = SmoothPercentageBar;

// Global instance for percentage bar
window.percentageBar = null;

// Initialize percentage bar function
function initializeSmoothPercentageBar() {
    if (!window.percentageBar) {
        window.percentageBar = new SmoothPercentageBar('unified-percent-bar');
        if (!window.percentageBar.container) {
            console.warn('Could not initialize smooth percentage bar');            return false;
        }
    }
    return true;
}

// Enhanced updateUnifiedPercentBar function for standalone percentage bar
function updateUnifiedPercentBar(highPercentage, lowPercentage, totalHighs, totalLows) {
    // Initialize if needed
    if (!window.percentageBar) {
        if (!initializeSmoothPercentageBar()) {
            return;
        }
    }
    
    // Use the smooth update method
    window.percentageBar.updatePercentages(highPercentage, lowPercentage, totalHighs, totalLows);
}

// Initialize on DOM ready
window.addEventListener('DOMContentLoaded', () => {
    // Initialize percentage bar
    setTimeout(initializeSmoothPercentageBar, 500);
    
    // Check if we should auto-initialize velocity dashboard
    const container = document.getElementById('core-gauge-container');
    if (container && !window.velocityDashboard) {
        window.velocityDashboard = new ActivityVelocityDashboard('core-gauge-container');
    }
});

// Make updateUnifiedPercentBar globally available
window.updateUnifiedPercentBar = updateUnifiedPercentBar;

// Console helper for manual scaling control
window.setDashboardScaling = function(mode) {
    if (window.velocityDashboard) {
        window.velocityDashboard.setScalingMode(mode);
    } else {
        console.warn('Velocity dashboard not initialized');
    }
};

// Console helper to get current scaling info
window.getDashboardScaling = function() {
    if (window.velocityDashboard) {
        return window.velocityDashboard.getScalingInfo();
    } else {
        console.warn('Velocity dashboard not initialized');
        return null;
    }
};