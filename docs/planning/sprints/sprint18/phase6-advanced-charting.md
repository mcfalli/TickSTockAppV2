# Phase 6: Advanced Charting Integration - Detailed Implementation Guide

**Date**: 2025-09-04  
**Sprint**: 18 - Phase 6 Implementation  
**Duration**: 2-3 weeks  
**Status**: Implementation Ready  
**Prerequisites**: Phase 5 complete (My Focus tab operational)

## Phase Overview

Implement sophisticated interactive charting with pattern annotation, multi-timeframe synchronization, and GoldenLayout integration. This phase transforms static pattern data into dynamic visual analysis tools with TradingView-grade functionality while maintaining the high-performance standards required for real-time trading applications.

## Success Criteria

✅ **Interactive Charts**: TradingView-like functionality with pattern overlays and annotations  
✅ **Multi-Timeframe**: Synchronized daily/intraday charts with pattern context across timeframes  
✅ **GoldenLayout Integration**: Popout chart windows, multi-chart layouts, persistent state  
✅ **Performance**: <200ms chart load times, smooth real-time updates at 60fps  
✅ **Pattern Visualization**: Automated pattern annotations with support/resistance levels + FMV metrics validation (<5% error on bullish engulfing patterns)  

## Implementation Tasks

### Task 6.1: Chart Library Selection & Integration (Days 1-3)

#### 6.1.1 Chart Library Evaluation & Setup
**File**: `static/js/services/ChartingEngine.js`

```javascript
/**
 * Advanced charting engine for TickStock pattern visualization
 * 
 * Selected: LightWeight Charts (TradingView) for performance + customization
 * Fallback: Chart.js for simpler implementations
 * 
 * Key Requirements:
 * - Real-time data updates
 * - Custom pattern annotations
 * - Multi-timeframe support
 * - Mobile responsive
 * - Memory efficient for long-running sessions
 */

class ChartingEngine {
    constructor() {
        this.charts = new Map(); // Active chart instances
        this.patternOverlays = new Map(); // Pattern annotation overlays
        this.realtimeSubscriptions = new Map(); // WebSocket subscriptions
        this.defaultConfig = {
            layout: {
                background: { type: 'solid', color: '#1a1a1a' },
                textColor: '#ffffff',
            },
            grid: {
                vertLines: { color: '#2d2d2d' },
                horzLines: { color: '#2d2d2d' },
            },
            crosshair: {
                mode: 0, // Normal crosshair
            },
            rightPriceScale: {
                borderColor: '#444444',
            },
            timeScale: {
                borderColor: '#444444',
                timeVisible: true,
                secondsVisible: false,
            },
            watermark: {
                visible: true,
                fontSize: 14,
                horzAlign: 'left',
                vertAlign: 'top',
                color: 'rgba(255, 255, 255, 0.3)',
                text: 'TickStock.ai',
            }
        };
    }
    
    /**
     * Initialize chart library and load dependencies
     */
    async initialize() {
        try {
            // Load LightWeight Charts library if not already loaded
            if (typeof LightweightCharts === 'undefined') {
                await this.loadChartLibrary();
            }
            
            // Initialize pattern annotation system
            this.initializePatternAnnotations();
            
            // Set up WebSocket handlers for real-time updates
            this.setupRealtimeHandlers();
            
            console.log('ChartingEngine initialized successfully');
            return true;
            
        } catch (error) {
            console.error('Failed to initialize ChartingEngine:', error);
            return false;
        }
    }
    
    async loadChartLibrary() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/static/libs/lightweight-charts/lightweight-charts.standalone.production.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    /**
     * Create a new chart instance
     */
    createChart(containerId, symbol, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`Chart container ${containerId} not found`);
        }
        
        const chartConfig = {
            ...this.defaultConfig,
            width: container.clientWidth,
            height: container.clientHeight || 400,
            ...options
        };
        
        const chart = LightweightCharts.createChart(container, chartConfig);
        
        // Create price series (candlestick for daily, line for intraday)
        const mainSeries = chart.addCandlestickSeries({
            upColor: '#51cf66',
            downColor: '#ff6b6b',
            borderUpColor: '#51cf66',
            borderDownColor: '#ff6b6b',
            wickUpColor: '#51cf66',
            wickDownColor: '#ff6b6b',
        });
        
        // Create volume series
        const volumeSeries = chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: { type: 'volume' },
            priceScaleId: '',
            scaleMargins: { top: 0.8, bottom: 0 },
        });
        
        const chartInstance = {
            chart: chart,
            mainSeries: mainSeries,
            volumeSeries: volumeSeries,
            symbol: symbol,
            containerId: containerId,
            patterns: [],
            indicators: new Map(),
            lastUpdate: null
        };
        
        this.charts.set(containerId, chartInstance);
        
        // Set up resize handling
        this.setupChartResize(chartInstance);
        
        return chartInstance;
    }
    
    /**
     * Load OHLCV data and patterns for a symbol
     */
    async loadChartData(chartId, symbol, timeframe = 'daily', days = 30) {
        const chartInstance = this.charts.get(chartId);
        if (!chartInstance) {
            throw new Error(`Chart ${chartId} not found`);
        }
        
        try {
            // Load price data and patterns in parallel
            const [priceResponse, patternsResponse] = await Promise.all([
                fetch(`/api/charts/ohlcv/${symbol}?timeframe=${timeframe}&days=${days}`),
                fetch(`/api/patterns/chart/${symbol}?timeframe=${timeframe}&days=${days}`)
            ]);
            
            const priceData = await priceResponse.json();
            const patternsData = await patternsResponse.json();
            
            // Update chart with price data
            this.updatePriceData(chartInstance, priceData);
            
            // Add pattern annotations
            this.addPatternAnnotations(chartInstance, patternsData.patterns || []);
            
            // Add technical indicators
            await this.addTechnicalIndicators(chartInstance, symbol, timeframe);
            
            chartInstance.lastUpdate = new Date();
            
            return {
                priceDataPoints: priceData.ohlcv?.length || 0,
                patternsCount: patternsData.patterns?.length || 0,
                timeframe: timeframe
            };
            
        } catch (error) {
            console.error(`Failed to load chart data for ${symbol}:`, error);
            throw error;
        }
    }
    
    updatePriceData(chartInstance, priceData) {
        if (!priceData.ohlcv || priceData.ohlcv.length === 0) {
            return;
        }
        
        // Convert to LightweightCharts format
        const candleData = priceData.ohlcv.map(bar => ({
            time: Math.floor(new Date(bar.timestamp).getTime() / 1000),
            open: parseFloat(bar.open),
            high: parseFloat(bar.high),
            low: parseFloat(bar.low),
            close: parseFloat(bar.close)
        }));
        
        const volumeData = priceData.ohlcv.map(bar => ({
            time: Math.floor(new Date(bar.timestamp).getTime() / 1000),
            value: parseFloat(bar.volume),
            color: bar.close >= bar.open ? '#51cf6680' : '#ff6b6b80'
        }));
        
        chartInstance.mainSeries.setData(candleData);
        chartInstance.volumeSeries.setData(volumeData);
        
        // Fit content to show all data
        chartInstance.chart.timeScale().fitContent();
    }
    
    /**
     * Add pattern annotations to chart
     */
    addPatternAnnotations(chartInstance, patterns) {
        // Clear existing pattern overlays
        this.clearPatternAnnotations(chartInstance);
        
        patterns.forEach(pattern => {
            this.addPatternAnnotation(chartInstance, pattern);
        });
        
        chartInstance.patterns = patterns;
    }
    
    // FMV Validation Enhancement
    async validatePatternWithFMV(chartInstance, pattern) {
        try {
            const response = await fetch('/api/patterns/validate-fmv', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    pattern_type: pattern.pattern_type,
                    symbol: chartInstance.symbol,
                    current_price: pattern.current_price,
                    fmv_baseline: pattern.fmv_baseline,
                    confidence: pattern.confidence
                })
            });
            
            if (!response.ok) {
                throw new Error('FMV validation request failed');
            }
            
            const fmvResult = await response.json();
            
            // Enhance pattern with FMV validation results
            const enhancedPattern = {
                ...pattern,
                fmv_validated: fmvResult.error_percentage < 0.05,
                fmv_error_rate: fmvResult.error_percentage,
                fmv_calculated: fmvResult.fmv_calculated,
                validation_status: fmvResult.error_percentage < 0.05 ? 'PASSED' : 'HIGH_ERROR',
                fmv_warning: fmvResult.error_percentage > 0.05,
                requires_review: fmvResult.error_percentage > 0.05
            };
            
            // Update pattern in chart
            if (!chartInstance.patterns) {
                chartInstance.patterns = [];
            }
            chartInstance.patterns.push(enhancedPattern);
            
            // Visual indication for high error patterns
            if (fmvResult.error_percentage > 0.05) {
                this.addFMVWarningIndicator(chartInstance, enhancedPattern);
            }
            
            return {
                error_percentage: fmvResult.error_percentage,
                fmv_calculated: fmvResult.fmv_calculated,
                confidence_score: fmvResult.confidence_score,
                validation_status: enhancedPattern.validation_status,
                requires_review: enhancedPattern.requires_review
            };
            
        } catch (error) {
            console.error('FMV validation failed:', error);
            return {
                error_percentage: 1.0,  // Max error on failure
                validation_status: 'FAILED',
                requires_review: true
            };
        }
    }
    
    addFMVWarningIndicator(chartInstance, pattern) {
        // Add visual warning for patterns with high FMV error
        const warningLine = chartInstance.mainSeries.createPriceLine({
            price: parseFloat(pattern.current_price),
            color: '#FF6B35',  // Warning orange
            lineWidth: 3,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: `⚠ ${pattern.pattern_type} - High FMV Error (${(pattern.fmv_error_rate * 100).toFixed(1)}%)`
        });
        
        return warningLine;
    }
    
    addPatternAnnotation(chartInstance, pattern) {
        const detectedTime = Math.floor(new Date(pattern.detected_at).getTime() / 1000);
        const expirationTime = Math.floor(new Date(pattern.expiration).getTime() / 1000);
        
        // Pattern detection marker
        chartInstance.mainSeries.createPriceLine({
            price: parseFloat(pattern.current_price),
            color: this.getPatternColor(pattern.pattern_type),
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Solid,
            axisLabelVisible: true,
            title: `${pattern.pattern_type} (${Math.round(pattern.confidence * 100)}%)`
        });
        
        // Support/Resistance levels if available
        if (pattern.support_level) {
            chartInstance.mainSeries.createPriceLine({
                price: parseFloat(pattern.support_level),
                color: '#51cf66',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                axisLabelVisible: true,
                title: `Support: ${pattern.support_level}`
            });
        }
        
        if (pattern.resistance_level) {
            chartInstance.mainSeries.createPriceLine({
                price: parseFloat(pattern.resistance_level),
                color: '#ff6b6b',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                axisLabelVisible: true,
                title: `Resistance: ${pattern.resistance_level}`
            });
        }
        
        // Target price level
        if (pattern.target_price) {
            chartInstance.mainSeries.createPriceLine({
                price: parseFloat(pattern.target_price),
                color: '#ffd43b',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dotted,
                axisLabelVisible: true,
                title: `Target: ${pattern.target_price}`
            });
        }
        
        // Add pattern-specific annotations
        this.addPatternSpecificAnnotation(chartInstance, pattern);
    }
    
    addPatternSpecificAnnotation(chartInstance, pattern) {
        const patternType = pattern.pattern_type.toLowerCase();
        
        switch (patternType) {
            case 'ascending_triangle':
                this.drawAscendingTriangle(chartInstance, pattern);
                break;
            case 'bull_flag':
                this.drawBullFlag(chartInstance, pattern);
                break;
            case 'support_resistance_break':
                this.drawSupportResistanceBreak(chartInstance, pattern);
                break;
            case 'volume_spike':
                this.highlightVolumeSpike(chartInstance, pattern);
                break;
        }
    }
    
    drawAscendingTriangle(chartInstance, pattern) {
        // Implementation for drawing ascending triangle pattern
        // This would use custom drawing primitives or annotations
        console.log(`Drawing ascending triangle for ${pattern.symbol}`);
    }
    
    drawBullFlag(chartInstance, pattern) {
        // Implementation for drawing bull flag pattern
        console.log(`Drawing bull flag for ${pattern.symbol}`);
    }
    
    drawSupportResistanceBreak(chartInstance, pattern) {
        // Implementation for highlighting support/resistance breaks
        console.log(`Drawing S/R break for ${pattern.symbol}`);
    }
    
    highlightVolumeSpike(chartInstance, pattern) {
        // Highlight volume spike on volume chart
        console.log(`Highlighting volume spike for ${pattern.symbol}`);
    }
    
    /**
     * Add technical indicators to chart
     */
    async addTechnicalIndicators(chartInstance, symbol, timeframe) {
        try {
            const response = await fetch(`/api/indicators/${symbol}?timeframe=${timeframe}`);
            const indicatorData = await response.json();
            
            // Add moving averages
            if (indicatorData.sma_20) {
                const sma20Series = chartInstance.chart.addLineSeries({
                    color: '#2196f3',
                    lineWidth: 1,
                    title: 'SMA 20'
                });
                
                const sma20Data = indicatorData.sma_20.map(point => ({
                    time: Math.floor(new Date(point.timestamp).getTime() / 1000),
                    value: parseFloat(point.value)
                }));
                
                sma20Series.setData(sma20Data);
                chartInstance.indicators.set('sma_20', sma20Series);
            }
            
            if (indicatorData.sma_50) {
                const sma50Series = chartInstance.chart.addLineSeries({
                    color: '#ff9800',
                    lineWidth: 1,
                    title: 'SMA 50'
                });
                
                const sma50Data = indicatorData.sma_50.map(point => ({
                    time: Math.floor(new Date(point.timestamp).getTime() / 1000),
                    value: parseFloat(point.value)
                }));
                
                sma50Series.setData(sma50Data);
                chartInstance.indicators.set('sma_50', sma50Series);
            }
            
        } catch (error) {
            console.warn('Failed to load technical indicators:', error);
        }
    }
    
    /**
     * Set up real-time data updates
     */
    subscribeToRealtimeUpdates(chartId, symbol) {
        if (!window.wsClient) {
            console.warn('WebSocket client not available for real-time updates');
            return;
        }
        
        const subscriptionId = `chart_${chartId}_${symbol}`;
        
        const handler = (data) => {
            if (data.symbol === symbol) {
                this.handleRealtimeUpdate(chartId, data);
            }
        };
        
        window.wsClient.addHandler(`price_updates_${symbol}`, handler);
        this.realtimeSubscriptions.set(subscriptionId, handler);
        
        // Subscribe to price updates for this symbol
        window.wsClient.send({
            action: 'subscribe_price_updates',
            symbol: symbol,
            chart_id: chartId
        });
    }
    
    handleRealtimeUpdate(chartId, data) {
        const chartInstance = this.charts.get(chartId);
        if (!chartInstance) return;
        
        const timestamp = Math.floor(new Date(data.timestamp).getTime() / 1000);
        
        // Update main price series
        if (data.ohlcv) {
            const candlePoint = {
                time: timestamp,
                open: parseFloat(data.ohlcv.open),
                high: parseFloat(data.ohlcv.high),
                low: parseFloat(data.ohlcv.low),
                close: parseFloat(data.ohlcv.close)
            };
            
            chartInstance.mainSeries.update(candlePoint);
        }
        
        // Update volume series
        if (data.volume) {
            const volumePoint = {
                time: timestamp,
                value: parseFloat(data.volume),
                color: data.ohlcv && data.ohlcv.close >= data.ohlcv.open ? '#51cf6680' : '#ff6b6b80'
            };
            
            chartInstance.volumeSeries.update(volumePoint);
        }
        
        // Update pattern annotations if new patterns detected
        if (data.new_patterns && data.new_patterns.length > 0) {
            data.new_patterns.forEach(pattern => {
                this.addPatternAnnotation(chartInstance, pattern);
            });
        }
    }
    
    /**
     * Multi-timeframe synchronization
     */
    createSynchronizedCharts(containerId, symbol, timeframes = ['daily', 'intraday']) {
        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`Container ${containerId} not found`);
        }
        
        // Create layout for multiple charts
        container.innerHTML = `
            <div class="multi-timeframe-charts">
                ${timeframes.map(tf => `
                    <div class="chart-panel" data-timeframe="${tf}">
                        <div class="chart-header">
                            <h4>${symbol} - ${tf.charAt(0).toUpperCase() + tf.slice(1)}</h4>
                            <div class="chart-controls">
                                <button class="chart-control-btn" data-action="fullscreen">⛶</button>
                                <button class="chart-control-btn" data-action="settings">⚙️</button>
                            </div>
                        </div>
                        <div class="chart-container" id="chart-${tf}-${Date.now()}"></div>
                    </div>
                `).join('')}
            </div>
        `;
        
        const syncedCharts = [];
        
        // Create individual charts
        timeframes.forEach(timeframe => {
            const chartContainer = container.querySelector(`[data-timeframe="${timeframe}"] .chart-container`);
            const chartId = chartContainer.id;
            
            const chartInstance = this.createChart(chartId, symbol, {
                height: container.clientHeight / timeframes.length - 40 // Account for headers
            });
            
            this.loadChartData(chartId, symbol, timeframe);
            this.subscribeToRealtimeUpdates(chartId, symbol);
            
            syncedCharts.push(chartInstance);
        });
        
        // Set up crosshair synchronization
        this.synchronizeChartCrosshairs(syncedCharts);
        
        return syncedCharts;
    }
    
    synchronizeChartCrosshairs(charts) {
        charts.forEach(chartInstance => {
            chartInstance.chart.subscribeCrosshairMove(param => {
                if (param.point === undefined || !param.time || param.point.x < 0 || param.point.y < 0) {
                    // Hide crosshair on other charts
                    charts.forEach(otherChart => {
                        if (otherChart !== chartInstance) {
                            otherChart.chart.clearCrosshairPosition();
                        }
                    });
                    return;
                }
                
                // Sync crosshair position across charts
                charts.forEach(otherChart => {
                    if (otherChart !== chartInstance) {
                        otherChart.chart.setCrosshairPosition(param.point.y, param.time);
                    }
                });
            });
        });
    }
    
    /**
     * Utility methods
     */
    getPatternColor(patternType) {
        const colors = {
            'Bull_Flag': '#51cf66',
            'Ascending_Triangle': '#2196f3',
            'Volume_Spike': '#ff9800',
            'Support_Resistance_Break': '#e91e63',
            'Breakout': '#4caf50',
            'Reversal': '#f44336'
        };
        
        return colors[patternType] || '#ffffff';
    }
    
    clearPatternAnnotations(chartInstance) {
        // Remove existing price lines and annotations
        // Note: LightweightCharts doesn't have a direct method to remove price lines
        // This would need to be tracked and managed separately
        console.log('Clearing pattern annotations');
    }
    
    setupChartResize(chartInstance) {
        const resizeObserver = new ResizeObserver(entries => {
            const container = entries[0].target;
            chartInstance.chart.applyOptions({
                width: container.clientWidth,
                height: container.clientHeight
            });
        });
        
        const container = document.getElementById(chartInstance.containerId);
        if (container) {
            resizeObserver.observe(container);
        }
    }
    
    setupRealtimeHandlers() {
        // Set up WebSocket event handlers for chart updates
        if (window.wsClient) {
            window.wsClient.addHandler('pattern_detected', (data) => {
                // Handle new pattern detection across all charts
                this.charts.forEach((chartInstance, chartId) => {
                    if (chartInstance.symbol === data.symbol) {
                        this.addPatternAnnotation(chartInstance, data.pattern);
                    }
                });
            });
        }
    }
    
    /**
     * Cleanup method
     */
    destroyChart(chartId) {
        const chartInstance = this.charts.get(chartId);
        if (chartInstance) {
            // Unsubscribe from real-time updates
            const subscriptionId = `chart_${chartId}_${chartInstance.symbol}`;
            const handler = this.realtimeSubscriptions.get(subscriptionId);
            
            if (handler && window.wsClient) {
                window.wsClient.removeHandler(`price_updates_${chartInstance.symbol}`, handler);
            }
            
            this.realtimeSubscriptions.delete(subscriptionId);
            
            // Remove chart instance
            chartInstance.chart.remove();
            this.charts.delete(chartId);
        }
    }
    
    destroyAll() {
        this.charts.forEach((_, chartId) => {
            this.destroyChart(chartId);
        });
        
        this.charts.clear();
        this.patternOverlays.clear();
        this.realtimeSubscriptions.clear();
    }
}

// Global instance
window.chartingEngine = new ChartingEngine();
```

### Task 6.2: Chart Data API Endpoints (Days 4-6)

#### 6.2.1 OHLCV Data API
**File**: `src/api/chart_data.py`

```python
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text
from app import db
from datetime import datetime, timedelta
import json

charts_bp = Blueprint('charts', __name__)

@charts_bp.route('/api/charts/ohlcv/<symbol>', methods=['GET'])
def get_ohlcv_data(symbol):
    """
    Get OHLCV data for charting
    
    Query Parameters:
    - timeframe: daily, hourly, minute (default: daily)
    - days: Number of days of data (default: 30, max: 365)
    - interval: For minute data, interval in minutes (1, 5, 15, 30, 60)
    """
    
    timeframe = request.args.get('timeframe', 'daily')
    days = min(int(request.args.get('days', 30)), 365)
    interval = int(request.args.get('interval', 5))  # For minute data
    
    try:
        if timeframe == 'daily':
            ohlcv_data = get_daily_ohlcv(symbol, days)
        elif timeframe == 'hourly':
            ohlcv_data = get_hourly_ohlcv(symbol, days)
        elif timeframe == 'minute':
            ohlcv_data = get_minute_ohlcv(symbol, days, interval)
        else:
            return jsonify({'error': 'Invalid timeframe'}), 400
        
        return jsonify({
            'symbol': symbol,
            'timeframe': timeframe,
            'interval': interval if timeframe == 'minute' else None,
            'days': days,
            'data_points': len(ohlcv_data),
            'ohlcv': ohlcv_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get OHLCV data for {symbol}: {e}")
        return jsonify({'error': 'Failed to retrieve chart data'}), 500

def get_daily_ohlcv(symbol, days):
    """Get daily OHLCV data"""
    query = """
    SELECT 
        time_bucket('1 day', timestamp) as timestamp,
        first(open, timestamp) as open,
        max(high) as high,
        min(low) as low,
        last(close, timestamp) as close,
        sum(volume) as volume
    FROM ohlcv_daily 
    WHERE symbol = :symbol 
    AND timestamp >= NOW() - INTERVAL :days DAY
    GROUP BY time_bucket('1 day', timestamp)
    ORDER BY timestamp ASC
    """
    
    result = db.session.execute(text(query), {
        'symbol': symbol,
        'days': f'{days} days'
    })
    
    return [
        {
            'timestamp': row.timestamp.isoformat(),
            'open': float(row.open),
            'high': float(row.high),
            'low': float(row.low),
            'close': float(row.close),
            'volume': int(row.volume)
        }
        for row in result
    ]

def get_hourly_ohlcv(symbol, days):
    """Get hourly OHLCV data from minute data"""
    query = """
    SELECT 
        time_bucket('1 hour', timestamp) as timestamp,
        first(open, timestamp) as open,
        max(high) as high,
        min(low) as low,
        last(close, timestamp) as close,
        sum(volume) as volume
    FROM ohlcv_minute 
    WHERE symbol = :symbol 
    AND timestamp >= NOW() - INTERVAL :days DAY
    GROUP BY time_bucket('1 hour', timestamp)
    ORDER BY timestamp ASC
    """
    
    result = db.session.execute(text(query), {
        'symbol': symbol,
        'days': f'{days} days'
    })
    
    return [
        {
            'timestamp': row.timestamp.isoformat(),
            'open': float(row.open),
            'high': float(row.high),
            'low': float(row.low),
            'close': float(row.close),
            'volume': int(row.volume)
        }
        for row in result
    ]

def get_minute_ohlcv(symbol, days, interval):
    """Get minute OHLCV data with specified interval"""
    query = f"""
    SELECT 
        time_bucket('{interval} minutes', timestamp) as timestamp,
        first(open, timestamp) as open,
        max(high) as high,
        min(low) as low,
        last(close, timestamp) as close,
        sum(volume) as volume
    FROM ohlcv_minute 
    WHERE symbol = :symbol 
    AND timestamp >= NOW() - INTERVAL :days DAY
    GROUP BY time_bucket('{interval} minutes', timestamp)
    ORDER BY timestamp ASC
    """
    
    result = db.session.execute(text(query), {
        'symbol': symbol,
        'days': f'{days} days'
    })
    
    return [
        {
            'timestamp': row.timestamp.isoformat(),
            'open': float(row.open),
            'high': float(row.high),
            'low': float(row.low),
            'close': float(row.close),
            'volume': int(row.volume)
        }
        for row in result
    ]

@charts_bp.route('/api/patterns/chart/<symbol>', methods=['GET'])
def get_chart_patterns(symbol):
    """
    Get patterns for chart annotation
    """
    timeframe = request.args.get('timeframe', 'daily')
    days = min(int(request.args.get('days', 30)), 90)
    
    try:
        if timeframe == 'daily':
            patterns = get_daily_patterns_for_chart(symbol, days)
        elif timeframe == 'intraday' or timeframe == 'minute':
            patterns = get_intraday_patterns_for_chart(symbol, days)
        elif timeframe == 'combo':
            patterns = get_combo_patterns_for_chart(symbol, days)
        else:
            # Get all patterns
            patterns = (get_daily_patterns_for_chart(symbol, days) + 
                       get_intraday_patterns_for_chart(symbol, days) + 
                       get_combo_patterns_for_chart(symbol, days))
        
        # Sort by detection time
        patterns.sort(key=lambda p: p['detected_at'], reverse=True)
        
        return jsonify({
            'symbol': symbol,
            'timeframe': timeframe,
            'days': days,
            'pattern_count': len(patterns),
            'patterns': patterns
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get patterns for {symbol}: {e}")
        return jsonify({'error': 'Failed to retrieve pattern data'}), 500

def get_daily_patterns_for_chart(symbol, days):
    """Get daily patterns for chart annotation"""
    query = """
    SELECT symbol, pattern_type, confidence, current_price, price_change,
           indicators, detected_at, expiration,
           CAST(indicators->>'support_level' AS FLOAT) as support_level,
           CAST(indicators->>'resistance_level' AS FLOAT) as resistance_level,
           CAST(indicators->>'target_price' AS FLOAT) as target_price,
           'daily' as source
    FROM daily_patterns 
    WHERE symbol = :symbol 
    AND detected_at >= NOW() - INTERVAL :days DAY
    ORDER BY detected_at DESC
    """
    
    result = db.session.execute(text(query), {
        'symbol': symbol,
        'days': f'{days} days'
    })
    
    return format_patterns_for_chart(result)

def get_intraday_patterns_for_chart(symbol, days):
    """Get intraday patterns for chart annotation"""
    query = """
    SELECT symbol, pattern_type, confidence, current_price, price_change,
           indicators, detected_at, expiration,
           CAST(indicators->>'support_level' AS FLOAT) as support_level,
           CAST(indicators->>'resistance_level' AS FLOAT) as resistance_level,
           CAST(indicators->>'target_price' AS FLOAT) as target_price,
           'intraday' as source
    FROM intraday_patterns 
    WHERE symbol = :symbol 
    AND detected_at >= NOW() - INTERVAL :days DAY
    ORDER BY detected_at DESC
    """
    
    result = db.session.execute(text(query), {
        'symbol': symbol,
        'days': f'{days} days'
    })
    
    return format_patterns_for_chart(result)

def get_combo_patterns_for_chart(symbol, days):
    """Get combo patterns for chart annotation"""
    query = """
    SELECT symbol, pattern_type, confidence, current_price, price_change,
           indicators, detected_at, expiration,
           CAST(indicators->>'support_level' AS FLOAT) as support_level,
           CAST(indicators->>'resistance_level' AS FLOAT) as resistance_level,
           CAST(indicators->>'target_price' AS FLOAT) as target_price,
           'combo' as source
    FROM daily_intraday_patterns 
    WHERE symbol = :symbol 
    AND detected_at >= NOW() - INTERVAL :days DAY
    ORDER BY detected_at DESC
    """
    
    result = db.session.execute(text(query), {
        'symbol': symbol,
        'days': f'{days} days'
    })
    
    return format_patterns_for_chart(result)

def format_patterns_for_chart(result):
    """Format patterns for chart consumption"""
    patterns = []
    
    for row in result:
        pattern = {
            'symbol': row.symbol,
            'pattern_type': row.pattern_type,
            'confidence': float(row.confidence),
            'current_price': float(row.current_price) if row.current_price else None,
            'price_change': float(row.price_change) if row.price_change else None,
            'detected_at': row.detected_at.isoformat(),
            'expiration': row.expiration.isoformat() if row.expiration else None,
            'source': row.source,
            'indicators': row.indicators or {}
        }
        
        # Add support/resistance levels if available
        if row.support_level:
            pattern['support_level'] = float(row.support_level)
        if row.resistance_level:
            pattern['resistance_level'] = float(row.resistance_level)
        if row.target_price:
            pattern['target_price'] = float(row.target_price)
        
        patterns.append(pattern)
    
    return patterns

@charts_bp.route('/api/indicators/<symbol>', methods=['GET'])
def get_technical_indicators(symbol):
    """
    Get technical indicators for chart overlays
    """
    timeframe = request.args.get('timeframe', 'daily')
    days = min(int(request.args.get('days', 30)), 90)
    
    try:
        indicators = {}
        
        if timeframe == 'daily':
            indicators = get_daily_indicators(symbol, days)
        elif timeframe == 'intraday':
            indicators = get_intraday_indicators(symbol, days)
        
        return jsonify({
            'symbol': symbol,
            'timeframe': timeframe,
            'indicators': indicators
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get indicators for {symbol}: {e}")
        return jsonify({'error': 'Failed to retrieve indicator data'}), 500

def get_daily_indicators(symbol, days):
    """Get daily technical indicators"""
    query = """
    SELECT 
        timestamp,
        indicators->>'sma_20' as sma_20,
        indicators->>'sma_50' as sma_50,
        indicators->>'rsi' as rsi,
        indicators->>'bollinger_upper' as bb_upper,
        indicators->>'bollinger_lower' as bb_lower,
        indicators->>'relative_strength' as rs,
        indicators->>'relative_volume' as rv
    FROM daily_patterns 
    WHERE symbol = :symbol 
    AND detected_at >= NOW() - INTERVAL :days DAY
    ORDER BY timestamp ASC
    """
    
    result = db.session.execute(text(query), {
        'symbol': symbol,
        'days': f'{days} days'
    })
    
    indicators = {
        'sma_20': [],
        'sma_50': [],
        'rsi': [],
        'bollinger_bands': {'upper': [], 'lower': []},
        'relative_strength': [],
        'relative_volume': []
    }
    
    for row in result:
        timestamp = row.timestamp.isoformat()
        
        if row.sma_20:
            indicators['sma_20'].append({
                'timestamp': timestamp,
                'value': float(row.sma_20)
            })
        
        if row.sma_50:
            indicators['sma_50'].append({
                'timestamp': timestamp,
                'value': float(row.sma_50)
            })
        
        if row.rsi:
            indicators['rsi'].append({
                'timestamp': timestamp,
                'value': float(row.rsi)
            })
        
        if row.bb_upper and row.bb_lower:
            indicators['bollinger_bands']['upper'].append({
                'timestamp': timestamp,
                'value': float(row.bb_upper)
            })
            indicators['bollinger_bands']['lower'].append({
                'timestamp': timestamp,
                'value': float(row.bb_lower)
            })
    
    return indicators
```

### Task 6.3: Advanced Chart Component Integration (Days 7-10)

#### 6.3.1 Enhanced Chart Panel Component
**File**: `static/js/components/ChartPanel.js`

```javascript
class ChartPanel {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            symbol: null,
            timeframe: 'daily',
            height: 400,
            showControls: true,
            allowPopout: true,
            enableRealtime: true,
            ...options
        };
        
        this.chartInstance = null;
        this.isFullscreen = false;
        this.realtimeEnabled = false;
        this.patternOverlays = [];
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="chart-panel">
                <!-- Chart Controls -->
                <div class="chart-controls" ${!this.options.showControls ? 'style="display:none"' : ''}>
                    <div class="chart-controls-left">
                        <div class="symbol-display">
                            <strong id="chart-symbol">${this.options.symbol || 'Select Symbol'}</strong>
                        </div>
                        <div class="timeframe-selector">
                            <select id="timeframe-select">
                                <option value="minute">1 Minute</option>
                                <option value="hourly">1 Hour</option>
                                <option value="daily" ${this.options.timeframe === 'daily' ? 'selected' : ''}>Daily</option>
                            </select>
                        </div>
                        <div class="interval-selector" style="display: none;">
                            <select id="interval-select">
                                <option value="1">1m</option>
                                <option value="5" selected>5m</option>
                                <option value="15">15m</option>
                                <option value="30">30m</option>
                                <option value="60">1h</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="chart-controls-right">
                        <div class="chart-actions">
                            <button class="chart-action-btn" id="toggle-patterns" title="Toggle Patterns">
                                📊 Patterns
                            </button>
                            <button class="chart-action-btn" id="toggle-indicators" title="Toggle Indicators">
                                📈 Indicators
                            </button>
                            <button class="chart-action-btn" id="toggle-realtime" title="Toggle Real-time">
                                🔴 Live
                            </button>
                            <button class="chart-action-btn" id="chart-settings" title="Settings">
                                ⚙️
                            </button>
                            <button class="chart-action-btn" id="fullscreen-btn" title="Fullscreen">
                                ⛶
                            </button>
                            ${this.options.allowPopout ? `
                                <button class="chart-action-btn" id="popout-btn" title="Pop Out">
                                    🗗
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
                
                <!-- Chart Container -->
                <div class="chart-container" id="chart-container">
                    <div class="chart-loading" id="chart-loading">
                        <div class="loading-spinner"></div>
                        <p>Loading chart data...</p>
                    </div>
                </div>
                
                <!-- Pattern Info Panel -->
                <div class="pattern-info-panel" id="pattern-info-panel" style="display: none;">
                    <div class="pattern-info-header">
                        <h4>Pattern Details</h4>
                        <button class="close-info-btn" id="close-pattern-info">&times;</button>
                    </div>
                    <div class="pattern-info-content" id="pattern-info-content">
                        <!-- Pattern details populated here -->
                    </div>
                </div>
            </div>
        `;
        
        this.bindEvents();
        this.initializeChart();
    }
    
    bindEvents() {
        // Timeframe selection
        document.getElementById('timeframe-select').addEventListener('change', (e) => {
            this.changeTimeframe(e.target.value);
        });
        
        // Interval selection (for minute charts)
        document.getElementById('interval-select').addEventListener('change', (e) => {
            this.changeInterval(parseInt(e.target.value));
        });
        
        // Chart action buttons
        document.getElementById('toggle-patterns').addEventListener('click', () => {
            this.togglePatterns();
        });
        
        document.getElementById('toggle-indicators').addEventListener('click', () => {
            this.toggleIndicators();
        });
        
        document.getElementById('toggle-realtime').addEventListener('click', () => {
            this.toggleRealtime();
        });
        
        document.getElementById('fullscreen-btn').addEventListener('click', () => {
            this.toggleFullscreen();
        });
        
        if (this.options.allowPopout) {
            document.getElementById('popout-btn').addEventListener('click', () => {
                this.popoutChart();
            });
        }
        
        document.getElementById('chart-settings').addEventListener('click', () => {
            this.showSettingsModal();
        });
        
        // Pattern info panel
        document.getElementById('close-pattern-info').addEventListener('click', () => {
            this.hidePatternInfo();
        });
    }
    
    async initializeChart() {
        if (!window.chartingEngine) {
            console.error('ChartingEngine not available');
            return;
        }
        
        // Wait for charting engine to initialize
        const initialized = await window.chartingEngine.initialize();
        if (!initialized) {
            this.showError('Failed to initialize charting engine');
            return;
        }
        
        // Create chart instance
        const chartContainer = this.container.querySelector('#chart-container');
        const chartId = `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        chartContainer.id = chartId;
        
        try {
            this.chartInstance = window.chartingEngine.createChart(chartId, this.options.symbol, {
                height: this.options.height
            });
            
            if (this.options.symbol) {
                await this.loadSymbol(this.options.symbol);
            }
            
        } catch (error) {
            console.error('Failed to create chart:', error);
            this.showError('Failed to create chart: ' + error.message);
        }
    }
    
    async loadSymbol(symbol) {
        if (!this.chartInstance) {
            console.warn('Chart not initialized');
            return;
        }
        
        this.options.symbol = symbol;
        document.getElementById('chart-symbol').textContent = symbol;
        this.showLoading(true);
        
        try {
            const result = await window.chartingEngine.loadChartData(
                this.chartInstance.containerId,
                symbol,
                this.options.timeframe,
                30 // days
            );
            
            // Enable real-time updates if requested
            if (this.options.enableRealtime) {
                window.chartingEngine.subscribeToRealtimeUpdates(
                    this.chartInstance.containerId,
                    symbol
                );
                this.realtimeEnabled = true;
                this.updateRealtimeButton();
            }
            
            // Set up pattern click handlers
            this.setupPatternInteractions();
            
            console.log(`Loaded ${result.priceDataPoints} price points and ${result.patternsCount} patterns for ${symbol}`);
            
        } catch (error) {
            console.error('Failed to load symbol:', error);
            this.showError('Failed to load chart data: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    changeTimeframe(timeframe) {
        this.options.timeframe = timeframe;
        
        // Show/hide interval selector for minute charts
        const intervalSelector = document.querySelector('.interval-selector');
        intervalSelector.style.display = timeframe === 'minute' ? 'block' : 'none';
        
        if (this.options.symbol) {
            this.loadSymbol(this.options.symbol);
        }
    }
    
    changeInterval(interval) {
        this.options.interval = interval;
        
        if (this.options.symbol && this.options.timeframe === 'minute') {
            this.loadSymbol(this.options.symbol);
        }
    }
    
    togglePatterns() {
        const btn = document.getElementById('toggle-patterns');
        const showPatterns = !btn.classList.contains('active');
        
        if (showPatterns) {
            btn.classList.add('active');
            this.showPatterns();
        } else {
            btn.classList.remove('active');
            this.hidePatterns();
        }
    }
    
    showPatterns() {
        // Show pattern annotations (already loaded by default)
        console.log('Showing patterns');
    }
    
    hidePatterns() {
        // Hide pattern annotations
        if (this.chartInstance) {
            window.chartingEngine.clearPatternAnnotations(this.chartInstance);
        }
    }
    
    toggleIndicators() {
        const btn = document.getElementById('toggle-indicators');
        const showIndicators = !btn.classList.contains('active');
        
        if (showIndicators) {
            btn.classList.add('active');
            this.showIndicators();
        } else {
            btn.classList.remove('active');
            this.hideIndicators();
        }
    }
    
    showIndicators() {
        // Show technical indicators
        if (this.chartInstance && this.options.symbol) {
            window.chartingEngine.addTechnicalIndicators(
                this.chartInstance,
                this.options.symbol,
                this.options.timeframe
            );
        }
    }
    
    hideIndicators() {
        // Hide technical indicators
        if (this.chartInstance && this.chartInstance.indicators) {
            this.chartInstance.indicators.forEach((series, key) => {
                this.chartInstance.chart.removeSeries(series);
            });
            this.chartInstance.indicators.clear();
        }
    }
    
    toggleRealtime() {
        const btn = document.getElementById('toggle-realtime');
        
        if (this.realtimeEnabled) {
            this.realtimeEnabled = false;
            // Unsubscribe from real-time updates
            console.log('Disabling real-time updates');
        } else {
            this.realtimeEnabled = true;
            if (this.options.symbol && this.chartInstance) {
                window.chartingEngine.subscribeToRealtimeUpdates(
                    this.chartInstance.containerId,
                    this.options.symbol
                );
            }
            console.log('Enabling real-time updates');
        }
        
        this.updateRealtimeButton();
    }
    
    updateRealtimeButton() {
        const btn = document.getElementById('toggle-realtime');
        if (this.realtimeEnabled) {
            btn.classList.add('active');
            btn.innerHTML = '🔴 Live';
        } else {
            btn.classList.remove('active');
            btn.innerHTML = '⚫ Off';
        }
    }
    
    toggleFullscreen() {
        if (!this.isFullscreen) {
            this.enterFullscreen();
        } else {
            this.exitFullscreen();
        }
    }
    
    enterFullscreen() {
        this.container.classList.add('chart-fullscreen');
        this.isFullscreen = true;
        
        // Resize chart
        if (this.chartInstance) {
            this.chartInstance.chart.applyOptions({
                width: window.innerWidth,
                height: window.innerHeight - 60 // Account for controls
            });
        }
        
        document.getElementById('fullscreen-btn').innerHTML = '⛶ Exit';
    }
    
    exitFullscreen() {
        this.container.classList.remove('chart-fullscreen');
        this.isFullscreen = false;
        
        // Resize chart back to normal
        if (this.chartInstance) {
            const container = document.getElementById(this.chartInstance.containerId);
            this.chartInstance.chart.applyOptions({
                width: container.clientWidth,
                height: this.options.height
            });
        }
        
        document.getElementById('fullscreen-btn').innerHTML = '⛶';
    }
    
    popoutChart() {
        // Create popout window with chart
        const popoutWindow = window.open(
            '', 
            `chart_${this.options.symbol}`,
            `width=1200,height=800,scrollbars=yes,resizable=yes`
        );
        
        popoutWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${this.options.symbol} Chart - TickStock.ai</title>
                <link rel="stylesheet" href="/static/css/chart-popout.css">
            </head>
            <body>
                <div id="popout-chart-container"></div>
                <script src="/static/libs/lightweight-charts/lightweight-charts.standalone.production.js"></script>
                <script src="/static/js/services/ChartingEngine.js"></script>
                <script>
                    // Initialize chart in popout window
                    const chartEngine = new ChartingEngine();
                    chartEngine.initialize().then(() => {
                        const chart = chartEngine.createChart('popout-chart-container', '${this.options.symbol}');
                        chartEngine.loadChartData('popout-chart-container', '${this.options.symbol}', '${this.options.timeframe}');
                    });
                </script>
            </body>
            </html>
        `);
        
        popoutWindow.document.close();
    }
    
    setupPatternInteractions() {
        // Set up click handlers for pattern annotations
        if (this.chartInstance && this.chartInstance.patterns) {
            this.chartInstance.patterns.forEach(pattern => {
                // Add click detection for patterns (implementation depends on charting library)
                console.log(`Setting up interaction for pattern: ${pattern.pattern_type}`);
            });
        }
    }
    
    showPatternInfo(pattern) {
        const panel = document.getElementById('pattern-info-panel');
        const content = document.getElementById('pattern-info-content');
        
        content.innerHTML = `
            <div class="pattern-details">
                <div class="pattern-header">
                    <span class="pattern-type">${pattern.pattern_type}</span>
                    <span class="pattern-confidence">${Math.round(pattern.confidence * 100)}%</span>
                </div>
                
                <div class="pattern-metrics">
                    <div class="metric">
                        <label>Current Price:</label>
                        <span class="value">$${pattern.current_price?.toFixed(2) || 'N/A'}</span>
                    </div>
                    
                    <div class="metric">
                        <label>Support Level:</label>
                        <span class="value">$${pattern.support_level?.toFixed(2) || 'N/A'}</span>
                    </div>
                    
                    <div class="metric">
                        <label>Resistance Level:</label>
                        <span class="value">$${pattern.resistance_level?.toFixed(2) || 'N/A'}</span>
                    </div>
                    
                    <div class="metric">
                        <label>Target Price:</label>
                        <span class="value">$${pattern.target_price?.toFixed(2) || 'N/A'}</span>
                    </div>
                    
                    <div class="metric">
                        <label>Detected:</label>
                        <span class="value">${new Date(pattern.detected_at).toLocaleString()}</span>
                    </div>
                    
                    <div class="metric">
                        <label>Expires:</label>
                        <span class="value">${pattern.expiration ? new Date(pattern.expiration).toLocaleString() : 'N/A'}</span>
                    </div>
                </div>
                
                <div class="pattern-indicators">
                    <h5>Technical Indicators</h5>
                    <div class="indicators-grid">
                        <div class="indicator">
                            <label>Relative Strength:</label>
                            <span>${(pattern.indicators?.relative_strength || 1.0).toFixed(1)}x</span>
                        </div>
                        <div class="indicator">
                            <label>Relative Volume:</label>
                            <span>${(pattern.indicators?.relative_volume || 1.0).toFixed(1)}x</span>
                        </div>
                        <div class="indicator">
                            <label>RSI:</label>
                            <span>${pattern.indicators?.rsi?.toFixed(1) || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        panel.style.display = 'block';
    }
    
    hidePatternInfo() {
        document.getElementById('pattern-info-panel').style.display = 'none';
    }
    
    showSettingsModal() {
        // Implementation for chart settings modal
        console.log('Show chart settings modal');
    }
    
    showLoading(show) {
        const loading = document.getElementById('chart-loading');
        loading.style.display = show ? 'flex' : 'none';
    }
    
    showError(message) {
        const container = document.getElementById('chart-container');
        container.innerHTML = `
            <div class="chart-error">
                <div class="error-icon">⚠️</div>
                <div class="error-message">${message}</div>
                <button class="retry-btn" onclick="this.parentElement.style.display='none'; this.initializeChart()">
                    Retry
                </button>
            </div>
        `;
    }
    
    destroy() {
        if (this.chartInstance) {
            window.chartingEngine.destroyChart(this.chartInstance.containerId);
            this.chartInstance = null;
        }
    }
}

// Register for GoldenLayout
window.ChartPanel = ChartPanel;
```

### Task 6.4: Advanced Chart Styles (Days 11-14)

#### 6.4.1 Chart Panel CSS
**File**: `static/css/chart-panel.css`

```css
/* Advanced Chart Panel Styles */
.chart-panel {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
    position: relative;
}

/* Chart Controls */
.chart-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
    min-height: 40px;
}

.chart-controls-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.chart-controls-right {
    display: flex;
    align-items: center;
    gap: 8px;
}

.symbol-display {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}

.timeframe-selector select,
.interval-selector select {
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: 3px;
    font-size: 11px;
    cursor: pointer;
}

.timeframe-selector select:focus,
.interval-selector select:focus {
    outline: none;
    border-color: var(--accent-primary);
}

.chart-actions {
    display: flex;
    gap: 4px;
}

.chart-action-btn {
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    border-radius: 3px;
    cursor: pointer;
    font-size: 10px;
    transition: all 0.2s ease;
    white-space: nowrap;
}

.chart-action-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-color: var(--accent-primary);
}

.chart-action-btn.active {
    background: var(--accent-primary);
    color: #000;
    border-color: var(--accent-primary);
}

/* Chart Container */
.chart-container {
    flex: 1;
    position: relative;
    background: var(--bg-primary);
    overflow: hidden;
}

/* Chart Loading */
.chart-loading {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--bg-primary);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 100;
}

.chart-loading .loading-spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border-color);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 12px;
}

.chart-loading p {
    color: var(--text-secondary);
    font-size: 12px;
}

/* Chart Error */
.chart-error {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: var(--text-secondary);
}

.error-icon {
    font-size: 32px;
    margin-bottom: 12px;
}

.error-message {
    font-size: 14px;
    margin-bottom: 16px;
    color: var(--text-primary);
}

.retry-btn {
    padding: 6px 12px;
    background: var(--accent-primary);
    color: #000;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}

.retry-btn:hover {
    background: var(--success-color);
}

/* Fullscreen Chart */
.chart-fullscreen {
    position: fixed !important;
    top: 0;
    left: 0;
    width: 100vw !important;
    height: 100vh !important;
    z-index: 10000;
    background: var(--bg-primary);
}

.chart-fullscreen .chart-container {
    height: calc(100vh - 60px);
}

/* Pattern Info Panel */
.pattern-info-panel {
    position: absolute;
    top: 50px;
    right: 10px;
    width: 280px;
    max-height: 400px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    z-index: 200;
    overflow: hidden;
}

.pattern-info-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-color);
}

.pattern-info-header h4 {
    margin: 0;
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 600;
}

.close-info-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 16px;
    padding: 2px;
    border-radius: 2px;
    transition: all 0.2s ease;
}

.close-info-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.pattern-info-content {
    padding: 12px;
    overflow-y: auto;
    max-height: 340px;
}

/* Pattern Details */
.pattern-details {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.pattern-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}

.pattern-type {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}

.pattern-confidence {
    font-size: 12px;
    font-weight: 600;
    color: var(--accent-primary);
    background: rgba(0, 212, 170, 0.2);
    padding: 2px 6px;
    border-radius: 3px;
}

.pattern-metrics {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.metric {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
}

.metric label {
    color: var(--text-secondary);
    font-weight: 500;
}

.metric .value {
    color: var(--text-primary);
    font-weight: 600;
}

.pattern-indicators h5 {
    margin: 0 0 8px 0;
    font-size: 11px;
    color: var(--text-primary);
    text-transform: uppercase;
    font-weight: 600;
}

.indicators-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
}

.indicator {
    background: var(--bg-primary);
    padding: 6px 8px;
    border-radius: 3px;
    font-size: 11px;
}

.indicator label {
    display: block;
    color: var(--text-secondary);
    margin-bottom: 2px;
    font-weight: 500;
}

.indicator span {
    color: var(--text-primary);
    font-weight: 600;
}

/* Multi-Timeframe Charts */
.multi-timeframe-charts {
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 1px;
    background: var(--border-color);
}

.multi-timeframe-charts .chart-panel {
    flex: 1;
    background: var(--bg-primary);
}

.multi-timeframe-charts .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
}

.multi-timeframe-charts .chart-header h4 {
    margin: 0;
    font-size: 12px;
    color: var(--text-primary);
    font-weight: 600;
}

.chart-control-btn {
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 2px 6px;
    border-radius: 2px;
    cursor: pointer;
    font-size: 10px;
    margin-left: 4px;
}

.chart-control-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-color: var(--accent-primary);
}

/* Chart Popout Styles */
.chart-popout-container {
    width: 100%;
    height: 100vh;
    background: var(--bg-primary);
    display: flex;
    flex-direction: column;
}

.chart-popout-container .chart-container {
    flex: 1;
}

/* Responsive Design */
@media (max-width: 1200px) {
    .chart-controls {
        flex-direction: column;
        gap: 8px;
        align-items: stretch;
        min-height: auto;
        padding: 12px;
    }
    
    .chart-controls-left,
    .chart-controls-right {
        justify-content: center;
    }
    
    .pattern-info-panel {
        position: fixed;
        top: 10px;
        right: 10px;
        left: 10px;
        width: auto;
        max-height: 60vh;
    }
}

@media (max-width: 768px) {
    .chart-actions {
        flex-wrap: wrap;
    }
    
    .chart-action-btn {
        font-size: 9px;
        padding: 3px 6px;
    }
    
    .symbol-display {
        font-size: 13px;
    }
    
    .multi-timeframe-charts {
        flex-direction: column;
    }
    
    .pattern-info-panel {
        max-height: 50vh;
    }
}

/* Chart Library Customizations */
.tv-lightweight-charts {
    background: var(--bg-primary) !important;
}

/* Loading Animation */
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Scrollbar Styling for Pattern Info */
.pattern-info-content::-webkit-scrollbar {
    width: 4px;
}

.pattern-info-content::-webkit-scrollbar-track {
    background: var(--bg-primary);
}

.pattern-info-content::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 2px;
}

.pattern-info-content::-webkit-scrollbar-thumb:hover {
    background: var(--text-secondary);
}

/* Chart Annotation Styles (for custom overlays) */
.chart-annotation {
    position: absolute;
    padding: 4px 8px;
    background: rgba(0, 0, 0, 0.8);
    color: #fff;
    border-radius: 3px;
    font-size: 10px;
    pointer-events: none;
    z-index: 10;
}

.chart-annotation.pattern-annotation {
    background: var(--accent-primary);
    color: #000;
}

.chart-annotation.support-annotation {
    background: var(--success-color);
}

.chart-annotation.resistance-annotation {
    background: var(--error-color);
}

/* Chart Crosshair Customization */
.tv-lightweight-charts .crosshair-line {
    color: var(--accent-primary) !important;
}

/* Pattern Overlay Lines */
.pattern-line {
    stroke: var(--accent-primary);
    stroke-width: 2;
    fill: none;
}

.support-line {
    stroke: var(--success-color);
    stroke-width: 1;
    stroke-dasharray: 5,5;
}

.resistance-line {
    stroke: var(--error-color);
    stroke-width: 1;
    stroke-dasharray: 5,5;
}

.target-line {
    stroke: var(--warning-color);
    stroke-width: 1;
    stroke-dasharray: 3,3;
}
```

## Testing Strategy

### Chart Integration Testing
**File**: `tests/test_charting_integration.js`

```javascript
describe('ChartingEngine', () => {
    let chartingEngine;
    
    beforeEach(async () => {
        chartingEngine = new ChartingEngine();
        await chartingEngine.initialize();
    });
    
    afterEach(() => {
        chartingEngine.destroyAll();
    });
    
    test('should initialize successfully', () => {
        expect(chartingEngine).toBeDefined();
        expect(chartingEngine.charts).toBeDefined();
    });
    
    test('should create chart instance', () => {
        const container = document.createElement('div');
        container.id = 'test-chart';
        document.body.appendChild(container);
        
        const chart = chartingEngine.createChart('test-chart', 'AAPL');
        
        expect(chart).toBeDefined();
        expect(chart.symbol).toBe('AAPL');
        expect(chartingEngine.charts.has('test-chart')).toBe(true);
        
        document.body.removeChild(container);
    });
    
    test('should load chart data', async () => {
        const container = document.createElement('div');
        container.id = 'test-chart-data';
        document.body.appendChild(container);
        
        // Mock fetch for chart data
        global.fetch = jest.fn()
            .mockImplementationOnce(() => Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    ohlcv: [
                        {
                            timestamp: '2025-01-01T00:00:00Z',
                            open: 100,
                            high: 105,
                            low: 99,
                            close: 103,
                            volume: 1000000
                        }
                    ]
                })
            }))
            .mockImplementationOnce(() => Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    patterns: []
                })
            }));
        
        const chart = chartingEngine.createChart('test-chart-data', 'AAPL');
        const result = await chartingEngine.loadChartData('test-chart-data', 'AAPL', 'daily');
        
        expect(result.priceDataPoints).toBe(1);
        expect(fetch).toHaveBeenCalledTimes(2);
        
        document.body.removeChild(container);
    });
    
    test('should handle pattern annotations', () => {
        const container = document.createElement('div');
        container.id = 'test-patterns';
        document.body.appendChild(container);
        
        const chart = chartingEngine.createChart('test-patterns', 'AAPL');
        const testPattern = {
            pattern_type: 'Bull_Flag',
            confidence: 0.92,
            current_price: 185.50,
            support_level: 180.00,
            resistance_level: 190.00,
            detected_at: '2025-01-01T12:00:00Z',
            expiration: '2025-01-03T12:00:00Z'
        };
        
        chartingEngine.addPatternAnnotation(chart, testPattern);
        
        expect(chart.patterns).toContain(testPattern);
        
        document.body.removeChild(container);
    });
    
    // FMV Metrics Validation Enhancement
    test('should validate pattern annotations with FMV metrics (<5% error)', async () => {
        const container = document.createElement('div');
        container.id = 'test-fmv-validation';
        document.body.appendChild(container);
        
        const chart = chartingEngine.createChart('test-fmv-validation', 'AAPL');
        
        // Test bullish engulfing pattern with known FMV baseline
        const bullishEngulfingPattern = {
            pattern_type: 'Bullish_Engulfing',
            confidence: 0.87,
            current_price: 185.50,
            support_level: 180.00,
            resistance_level: 190.00,
            fmv_baseline: 186.25,  // Fair Market Value baseline
            detection_accuracy: 0.96
        };
        
        // Mock FMV calculation service
        global.fetch = jest.fn()
            .mockImplementationOnce(() => Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    fmv_calculated: 185.82,
                    confidence_score: 0.94,
                    error_percentage: 0.035  // 3.5% error - within <5% threshold
                })
            }));
        
        const result = await chartingEngine.validatePatternWithFMV(chart, bullishEngulfingPattern);
        
        // Validation assertions
        expect(result.error_percentage).toBeLessThan(0.05);  // <5% error requirement
        expect(result.fmv_calculated).toBeCloseTo(185.82, 2);
        expect(result.confidence_score).toBeGreaterThan(0.90);
        expect(result.validation_status).toBe('PASSED');
        
        // Pattern should be enhanced with FMV data
        expect(chart.patterns[0].fmv_validated).toBe(true);
        expect(chart.patterns[0].fmv_error_rate).toBeLessThan(0.05);
        
        document.body.removeChild(container);
    });
    
    test('should flag patterns with high FMV error (>5%)', async () => {
        const container = document.createElement('div');
        container.id = 'test-fmv-error';
        document.body.appendChild(container);
        
        const chart = chartingEngine.createChart('test-fmv-error', 'XYZ');
        
        const patternWithHighError = {
            pattern_type: 'Double_Top',
            confidence: 0.75,
            current_price: 45.20,
            fmv_baseline: 42.80
        };
        
        // Mock high error FMV response
        global.fetch = jest.fn()
            .mockImplementationOnce(() => Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    fmv_calculated: 48.65,
                    confidence_score: 0.68,
                    error_percentage: 0.076  // 7.6% error - exceeds 5% threshold
                })
            }));
        
        const result = await chartingEngine.validatePatternWithFMV(chart, patternWithHighError);
        
        // Should flag as high error
        expect(result.error_percentage).toBeGreaterThan(0.05);
        expect(result.validation_status).toBe('HIGH_ERROR');
        expect(result.requires_review).toBe(true);
        
        // Pattern should be flagged
        expect(chart.patterns[0].fmv_warning).toBe(true);
        expect(chart.patterns[0].validation_status).toBe('HIGH_ERROR');
        
        document.body.removeChild(container);
    });
});

describe('ChartPanel Component', () => {
    let chartPanel;
    let container;
    
    beforeEach(() => {
        container = document.createElement('div');
        document.body.appendChild(container);
        
        chartPanel = new ChartPanel(container, {
            symbol: 'AAPL',
            timeframe: 'daily',
            height: 400
        });
    });
    
    afterEach(() => {
        chartPanel.destroy();
        document.body.removeChild(container);
    });
    
    test('should initialize with correct options', () => {
        expect(chartPanel.options.symbol).toBe('AAPL');
        expect(chartPanel.options.timeframe).toBe('daily');
        expect(chartPanel.options.height).toBe(400);
    });
    
    test('should handle timeframe changes', () => {
        chartPanel.changeTimeframe('minute');
        
        expect(chartPanel.options.timeframe).toBe('minute');
        
        const intervalSelector = container.querySelector('.interval-selector');
        expect(intervalSelector.style.display).toBe('block');
    });
    
    test('should toggle pattern visibility', () => {
        const toggleBtn = container.querySelector('#toggle-patterns');
        
        toggleBtn.click();
        expect(toggleBtn.classList.contains('active')).toBe(true);
        
        toggleBtn.click();
        expect(toggleBtn.classList.contains('active')).toBe(false);
    });
});
```

## Performance Benchmarks

### Chart Performance Targets
- **Chart initialization**: <500ms
- **Data loading**: <200ms for 30 days of OHLCV data
- **Real-time updates**: <16ms (60fps) for smooth animations
- **Pattern annotation**: <50ms for 10+ patterns
- **Memory usage**: <100MB for long-running chart sessions

## Deployment Checklist

- [ ] Chart library loaded and operational
- [ ] OHLCV data API endpoints working
- [ ] Pattern annotation system functional
- [ ] Multi-timeframe synchronization working
- [ ] Real-time updates via WebSocket operational
- [ ] GoldenLayout integration with popout functionality
- [ ] Mobile responsive design functional
- [ ] Performance benchmarks met
- [ ] Pattern interaction and info panels working
- [ ] Technical indicators display correctly

## Next Phase Handoff

**Phase 7 Prerequisites:**
- Advanced charting fully integrated and operational
- Pattern visualization working with real-time updates
- Multi-timeframe charts synchronized
- GoldenLayout popout functionality working

**Charting Platform Ready For:**
- Real-time features and performance optimization (Phase 7)
- Enhanced user experience and polish
- Advanced power user features (Phase 8)
- Production deployment and scaling

This implementation provides professional-grade interactive charting that rivals TradingView functionality while maintaining tight integration with TickStock's pattern detection system and real-time data pipeline.