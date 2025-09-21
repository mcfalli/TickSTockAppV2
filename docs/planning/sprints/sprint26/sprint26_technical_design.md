# Sprint 26: Technical Design
# Pattern Flow Display Architecture

**Last Updated**: 2025-09-19
**Sprint 26**: Comprehensive Technical Architecture

## Technical Architecture Overview

The Pattern Flow Display transforms pattern monitoring from a discovery-based tool into a real-time streaming interface. This design maintains TickStockAppV2's consumer architecture while providing immediate pattern visibility through a 4-column, auto-refreshing display optimized for trading decision support.

## Component Structure

### Frontend Architecture

#### Core Service: PatternFlowService
**File**: `web/static/js/services/pattern-flow.js`

```javascript
class PatternFlowService {
    constructor(options = {}) {
        // Configuration
        this.config = {
            refreshInterval: 15000,        // 15-second auto-refresh
            maxPatternsPerColumn: 50,      // Memory management
            wsReconnectDelay: 5000,        // WebSocket reconnection
            apiTimeout: 10000,             // API request timeout
            animationDuration: 300,        // UI transition timing
            ...options
        };

        // State management
        this.state = {
            isActive: false,
            isConnected: false,
            lastRefresh: null,
            errorCount: 0,
            patternCache: new Map(),
            subscriptions: new Set()
        };

        // Component references
        this.elements = {
            container: null,
            columns: new Map(),
            refreshIndicator: null,
            errorDisplay: null
        };

        // Event handlers
        this.eventHandlers = new Map();
        this.refreshTimer = null;
        this.countdownTimer = null;
    }

    // Service lifecycle
    async initialize() { /* Implementation */ }
    async activate() { /* Implementation */ }
    async deactivate() { /* Implementation */ }
    cleanup() { /* Implementation */ }
}
```

#### Column Management System
```javascript
class PatternColumn {
    constructor(tier, container) {
        this.tier = tier;                    // 'daily', 'intraday', 'combo', 'indicators'
        this.container = container;
        this.patterns = [];
        this.maxPatterns = 50;
        this.isUpdating = false;
    }

    // Pattern management
    addPattern(pattern) {
        // Insert at top, maintain sort order
        this.patterns.unshift(pattern);
        this.patterns = this.patterns.slice(0, this.maxPatterns);
        this.renderPatterns();
    }

    updatePattern(pattern) {
        // Update existing pattern in place
        const index = this.patterns.findIndex(p => p.id === pattern.id);
        if (index !== -1) {
            this.patterns[index] = pattern;
            this.renderPatterns();
        }
    }

    renderPatterns() {
        // Efficient DOM update with document fragment
        const fragment = document.createDocumentFragment();
        this.patterns.forEach(pattern => {
            // Create 60px height minimal pattern rows
            fragment.appendChild(this.createPatternRow(pattern));
        });

        // Smooth update with fade transition
        this.updateContainerWithAnimation(fragment);
    }
}
```

### Data Flow Architecture

#### WebSocket Integration Pattern
```javascript
class PatternFlowWebSocketManager {
    constructor(patternFlowService) {
        this.service = patternFlowService;
        this.socket = io();
        this.subscriptions = {
            'pattern_detected': this.handlePatternDetected.bind(this),
            'indicator_update': this.handleIndicatorUpdate.bind(this),
            'pattern_update': this.handlePatternUpdate.bind(this),
            'connection_status': this.handleConnectionStatus.bind(this)
        };
    }

    subscribeToChannels() {
        // Subscribe to TickStockPL pattern events
        Object.entries(this.subscriptions).forEach(([event, handler]) => {
            this.socket.on(event, handler);
        });

        // Request subscription to pattern channels
        this.socket.emit('subscribe', {
            channels: ['patterns.daily', 'patterns.intraday', 'patterns.combo', 'indicators']
        });
    }

    handlePatternDetected(data) {
        // Real-time pattern insertion
        if (this.service.isActive) {
            this.service.addPatternToColumn(data.tier, data.pattern);
        }
    }
}
```

#### API Integration Layer (Hybrid Refresh Strategy)
```javascript
class PatternFlowAPIClient {
    constructor() {
        this.baseURL = '/api/patterns';
        this.defaultParams = {
            limit: 50,
            sort: 'timestamp_desc'
        };
        // Hybrid approach: WebSocket (primary) + 15-second polling (fallback)
        this.refreshInterval = 15000;
    }

    async fetchPatternsByTier(tier) {
        const url = `${this.baseURL}/scan?tier=${tier}&${new URLSearchParams(this.defaultParams)}`;

        try {
            const response = await fetch(url, {
                timeout: 10000,
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            return this.validatePatternData(data);

        } catch (error) {
            console.error(`Pattern fetch failed for tier ${tier}:`, error);
            throw error;
        }
    }

    validatePatternData(data) {
        // Validate pattern structure
        if (!data.patterns || !Array.isArray(data.patterns)) {
            throw new Error('Invalid pattern data structure');
        }

        return data.patterns.map(pattern => ({
            id: pattern.id || `pattern_${Date.now()}`,
            symbol: pattern.symbol || 'UNKNOWN',
            timestamp: pattern.timestamp || new Date().toISOString(),
            tier: pattern.tier || 'unknown',
            type: pattern.type || 'Unknown Pattern',
            details: pattern.details || {},
            confidence: pattern.confidence || 0
        }));
    }
}
```

## State Management Approach

### Pattern Cache Management
```javascript
class PatternCacheManager {
    constructor(maxSize = 1000) {
        this.cache = new Map();
        this.maxSize = maxSize;
        this.accessTimes = new Map();
    }

    set(key, pattern) {
        // LRU cache implementation
        if (this.cache.size >= this.maxSize) {
            this.evictOldest();
        }

        this.cache.set(key, pattern);
        this.accessTimes.set(key, Date.now());
    }

    get(key) {
        if (this.cache.has(key)) {
            this.accessTimes.set(key, Date.now());
            return this.cache.get(key);
        }
        return null;
    }

    evictOldest() {
        let oldestKey = null;
        let oldestTime = Infinity;

        for (const [key, time] of this.accessTimes) {
            if (time < oldestTime) {
                oldestTime = time;
                oldestKey = key;
            }
        }

        if (oldestKey) {
            this.cache.delete(oldestKey);
            this.accessTimes.delete(oldestKey);
        }
    }
}
```

### Application State Schema
```javascript
const PatternFlowState = {
    // Service status
    status: {
        isActive: false,
        isConnected: false,
        lastRefresh: null,
        refreshCount: 0,
        errorCount: 0
    },

    // Pattern data
    patterns: {
        daily: [],
        intraday: [],
        combo: [],
        indicators: []
    },

    // UI state
    ui: {
        selectedPattern: null,
        modalOpen: false,
        columnHeights: {},
        scrollPositions: {},
        filterStates: {}
    },

    // Performance metrics
    metrics: {
        averageRefreshTime: 0,
        wsLatency: 0,
        apiLatency: 0,
        memoryUsage: 0
    }
};
```

## Performance Considerations

### Memory Optimization Strategy
```javascript
class MemoryManager {
    constructor(patternFlowService) {
        this.service = patternFlowService;
        this.maxMemoryUsage = 50 * 1024 * 1024; // 50MB limit
        this.monitoringInterval = 30000; // 30 seconds
    }

    startMonitoring() {
        setInterval(() => {
            this.checkMemoryUsage();
            this.cleanupIfNeeded();
        }, this.monitoringInterval);
    }

    checkMemoryUsage() {
        if (performance.memory) {
            const used = performance.memory.usedJSHeapSize;
            if (used > this.maxMemoryUsage) {
                this.triggerCleanup();
            }
        }
    }

    triggerCleanup() {
        // Remove old patterns beyond limit
        Object.values(this.service.columns).forEach(column => {
            if (column.patterns.length > 30) {
                column.patterns = column.patterns.slice(0, 30);
                column.renderPatterns();
            }
        });

        // Clear pattern cache
        this.service.patternCache.clear();

        // Force garbage collection if available
        if (window.gc) {
            window.gc();
        }
    }
}
```

### DOM Update Optimization
```javascript
class DOMUpdateOptimizer {
    constructor() {
        this.updateQueue = [];
        this.isProcessing = false;
        this.frameId = null;
    }

    scheduleUpdate(updateFunction) {
        this.updateQueue.push(updateFunction);

        if (!this.isProcessing) {
            this.processQueue();
        }
    }

    processQueue() {
        this.isProcessing = true;

        this.frameId = requestAnimationFrame(() => {
            // Process all updates in a single frame
            while (this.updateQueue.length > 0) {
                const update = this.updateQueue.shift();
                try {
                    update();
                } catch (error) {
                    console.error('DOM update error:', error);
                }
            }

            this.isProcessing = false;

            // Continue processing if new updates were added
            if (this.updateQueue.length > 0) {
                this.processQueue();
            }
        });
    }

    cancelPendingUpdates() {
        if (this.frameId) {
            cancelAnimationFrame(this.frameId);
            this.frameId = null;
        }
        this.updateQueue = [];
        this.isProcessing = false;
    }
}
```

## Mock Data Structure for Development

### Pattern Event Schema
```javascript
const MockPatternEvent = {
    id: 'pattern_20250919_143000_001',
    symbol: 'AAPL',
    timestamp: '2025-09-19T14:30:00.000Z',
    tier: 'daily',
    type: 'Bull Flag',
    confidence: 0.85,
    details: {
        entry_price: 173.25,
        target_price: 178.50,
        stop_loss: 170.00,
        support_levels: [171.50, 169.75],
        resistance_levels: [175.25, 178.50],
        volume_confirmation: true,
        rsi: 58.3,
        macd_signal: 'bullish'
    },
    metadata: {
        source: 'tickstockpl',
        detection_latency: '45ms',
        market_hours: true,
        sector: 'Technology',
        market_cap: 'Large'
    }
};

const MockIndicatorEvent = {
    id: 'indicator_20250919_143015_001',
    symbol: 'TSLA',
    timestamp: '2025-09-19T14:30:15.000Z',
    tier: 'indicators',
    type: 'RSI Oversold',
    confidence: 0.92,
    details: {
        indicator: 'RSI',
        current_value: 28.5,
        threshold: 30,
        signal: 'oversold',
        trend_direction: 'potential_reversal',
        confirmation_needed: true,
        timeframe: '1H'
    },
    metadata: {
        source: 'tickstockpl',
        detection_latency: '12ms',
        market_hours: true,
        sector: 'Automotive',
        volatility: 'high'
    }
};
```

### Mock Data Generator
```javascript
class MockDataGenerator {
    constructor() {
        this.symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'AMD'];
        this.patternTypes = {
            daily: ['Bull Flag', 'Bear Flag', 'Cup and Handle', 'Head and Shoulders', 'Triangle'],
            intraday: ['Momentum Shift', 'Volume Spike', 'Support Break', 'Resistance Test'],
            combo: ['Multi-Timeframe Bull', 'Cross-Tier Confirmation', 'Divergence Signal'],
            indicators: ['RSI Oversold', 'MACD Cross', 'MA Golden Cross', 'Volume Surge']
        };
    }

    generateRandomPattern(tier) {
        const symbol = this.getRandomSymbol();
        const type = this.getRandomPatternType(tier);
        const timestamp = new Date().toISOString();

        return {
            id: `${tier}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            symbol,
            timestamp,
            tier,
            type,
            confidence: 0.6 + Math.random() * 0.4,
            details: this.generatePatternDetails(tier, type),
            metadata: this.generateMetadata()
        };
    }

    startMockStream(patternFlowService, frequency = 5000) {
        return setInterval(() => {
            const tiers = ['daily', 'intraday', 'combo', 'indicators'];
            const randomTier = tiers[Math.floor(Math.random() * tiers.length)];
            const pattern = this.generateRandomPattern(randomTier);

            patternFlowService.addPatternToColumn(randomTier, pattern);
        }, frequency);
    }
}
```

## Integration Architecture

### Redis Event Consumption
```javascript
class RedisPatternConsumer {
    constructor(patternFlowService) {
        this.service = patternFlowService;
        this.channels = {
            'tickstock.events.patterns.daily': this.handleDailyPattern.bind(this),
            'tickstock.events.patterns.intraday': this.handleIntradayPattern.bind(this),
            'tickstock.events.patterns.combo': this.handleComboPattern.bind(this),
            'tickstock.events.indicators': this.handleIndicator.bind(this)
        };
    }

    subscribeToRedisChannels() {
        // WebSocket subscription to Redis pub-sub channels
        this.service.socket.emit('redis_subscribe', {
            channels: Object.keys(this.channels)
        });

        // Handle Redis events
        this.service.socket.on('redis_message', this.handleRedisMessage.bind(this));
    }

    handleRedisMessage(data) {
        const { channel, message } = data;
        const handler = this.channels[channel];

        if (handler) {
            try {
                const pattern = JSON.parse(message);
                handler(pattern);
            } catch (error) {
                console.error(`Failed to parse Redis message from ${channel}:`, error);
            }
        }
    }
}
```

### API Endpoint Integration
```javascript
// Expected API endpoints from Sprint 19 Pattern Discovery
const PatternFlowAPIEndpoints = {
    // Primary pattern scanning endpoint with tier filtering
    scanPatterns: '/api/patterns/scan?tier={tier}&limit=50&sort=timestamp_desc',

    // Pattern details for modal/popup
    patternDetails: '/api/patterns/{id}',

    // Cache performance metrics
    cacheStats: '/api/patterns/stats',

    // Health check
    healthCheck: '/api/pattern-discovery/health'
};

// API client configuration
const APIConfig = {
    baseURL: '/api',
    timeout: 10000,
    retryAttempts: 3,
    retryDelay: 1000,
    headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
};
```

## Error Handling & Resilience

### Error Recovery Strategy
```javascript
class ErrorRecoveryManager {
    constructor(patternFlowService) {
        this.service = patternFlowService;
        this.maxRetries = 3;
        this.baseDelay = 1000;
        this.errorCounts = new Map();
        this.recoveryStrategies = new Map();
    }

    async handleError(error, context) {
        const errorKey = `${context.operation}_${context.tier || 'global'}`;
        const errorCount = this.errorCounts.get(errorKey) || 0;

        this.errorCounts.set(errorKey, errorCount + 1);

        if (errorCount < this.maxRetries) {
            // Exponential backoff retry
            const delay = this.baseDelay * Math.pow(2, errorCount);
            setTimeout(() => {
                this.retryOperation(context);
            }, delay);
        } else {
            // Fall back to cached data or error state
            this.activateFallbackStrategy(context);
        }
    }

    activateFallbackStrategy(context) {
        switch (context.operation) {
            case 'api_fetch':
                this.service.showCachedData(context.tier);
                break;
            case 'websocket_connect':
                this.service.fallbackToPolling();
                break;
            case 'pattern_render':
                this.service.showErrorPlaceholder(context.tier);
                break;
        }
    }
}
```

This technical design provides a comprehensive architecture for the Pattern Flow Display that maintains TickStockAppV2's consumer role while delivering real-time pattern monitoring capabilities with optimal performance and reliability.