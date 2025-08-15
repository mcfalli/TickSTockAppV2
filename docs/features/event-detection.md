# Event Detection Systems Architecture

**Version:** 2.0  
**Last Updated:** JUNE 2025
**Status:** Production Architecture

## Overview

TickStock implements sophisticated event detection through specialized components that identify market patterns in real-time. The system processes tick data through multiple detection algorithms operating within the EventDetector component framework.

## Architecture Overview
EventDetector (Orchestrator)
├── High/Low Detection
├── Trend Analysis (Multi-window)
├── Surge Detection (Dynamic thresholds)
└── Pattern Recognition (Future)

## Component Integration

### EventDetector Component

The EventDetector component orchestrates all detection algorithms:

```python
class EventDetector:
    """Central event detection orchestration."""
    
    def __init__(self, config, stock_tick_event_detector):
        self.config = config
        self.detector = stock_tick_event_detector
        self.trend_detector = TrendDetector(config)
        self.surge_detector = SurgeDetector(config)
    
    def detect_events(self, tick_data, stock_state):
        """Coordinate all detection algorithms."""
        results = {
            'high_low': self._detect_high_low(tick_data, stock_state),
            'trends': self.trend_detector.detect_trend(stock_state, tick_data),
            'surges': self.surge_detector.detect_surge(stock_state, tick_data)
        }
        return EventDetectionResult(results)
Trend Detection System
Architecture
Multi-window momentum analysis with VWAP integration and volume confirmation.
Configuration
python# Time Windows
TREND_SHORT_WINDOW = 180       # 3 minutes
TREND_MEDIUM_WINDOW = 360      # 6 minutes  
TREND_LONG_WINDOW = 600        # 10 minutes

# Component Weights
TREND_PRICE_WEIGHT = 0.5       # Price movement weight
TREND_VWAP_WEIGHT = 0.3        # VWAP relationship weight
TREND_VOLUME_WEIGHT = 0.2      # Volume confirmation weight

# Detection Thresholds
TREND_DIRECTION_THRESHOLD = 0.3  # Minimum score for direction
TREND_STRENGTH_THRESHOLD = 0.6   # Strong trend threshold
Detection Algorithm
pythonclass TrendDetector:
    def detect_trend(self, stock_data, tick_data):
        """Multi-window trend analysis."""
        # Store data point
        self._add_data_point(stock_data, tick_data)
        
        # Analyze each window
        short = self._analyze_window(stock_data, self.short_window)
        medium = self._analyze_window(stock_data, self.medium_window)
        long = self._analyze_window(stock_data, self.long_window)
        
        # Weighted combination
        overall_score = (
            short['score'] * 0.3 +
            medium['score'] * 0.4 +
            long['score'] * 0.3
        )
        
        return self._classify_trend(overall_score)
Window Analysis Components
Price Trend (50% weight)

Measures price movement with recency bias
Normalizes to -1 to +1 scale
Recent changes weighted higher

VWAP Trend (30% weight)

Analyzes price position relative to VWAP
Tracks divergence changes
Identifies institutional activity

Volume Trend (20% weight)

Confirms price movement with volume
Identifies accumulation/distribution
Weights unusual volume patterns

Trend Classification
pythondef _classify_trend(self, score):
    """Classify trend direction and strength."""
    if score > self.direction_threshold:
        direction = '↑'
        strength = self._get_strength(score)
    elif score < -self.direction_threshold:
        direction = '↓'
        strength = self._get_strength(abs(score))
    else:
        direction = '→'
        strength = 'neutral'
    
    return TrendResult(direction, strength, score)
Surge Detection System
Architecture
Real-time spike detection with dynamic thresholds based on stock price ranges.
Dynamic Threshold Matrix
python# Price-based thresholds: (max_price, (percent_threshold, min_dollar_change))
SURGE_THRESHOLD_MATRIX = [
    (0.01,    (10.0, 0.005)),   # Penny stocks
    (0.7,     (9.0,  0.05)),    # Very low price
    (1.0,     (7.0,  0.05)),    # Low price
    (5.0,     (5.0,  0.10)),    # Low-mid price
    (25.0,    (4.0,  0.25)),    # Mid price
    (100.0,   (3.0,  0.75)),    # Mid-high price
    (500.0,   (2.5,  1.50)),    # High price
    (1000.0,  (2.0,  10.00)),   # Very high price
    (inf,     (1.5,  15.00))    # Ultra-high price
]
Detection Process
pythonclass SurgeDetector:
    def detect_surge(self, stock_data, tick_data):
        """Detect price and volume surges."""
        # Initialize surge tracking
        surge_data = self._get_surge_data(stock_data)
        
        # Add current data point
        surge_data['buffer'].append({
            'price': tick_data.price,
            'volume': tick_data.volume,
            'timestamp': tick_data.timestamp
        })
        
        # Check surge conditions
        price_surge = self._check_price_surge(surge_data, tick_data.price)
        volume_surge = self._check_volume_surge(surge_data, tick_data.volume)
        
        if price_surge or volume_surge:
            return self._create_surge_event(
                price_surge, volume_surge, tick_data
            )
Surge Scoring
pythondef _calculate_surge_score(self, price_change_pct, volume_multiplier):
    """Calculate composite surge score."""
    price_score = min(
        (price_change_pct / self.threshold_pct) * self.price_weight,
        self.price_weight
    )
    
    volume_score = min(
        (volume_multiplier / self.volume_threshold) * self.volume_weight,
        self.volume_weight
    )
    
    total_score = price_score + volume_score
    
    return {
        'score': total_score,
        'strength': 'strong' if total_score >= 80 else
                   'moderate' if total_score >= 60 else 'weak',
        'components': {
            'price': price_score,
            'volume': volume_score
        }
    }
Integration with Frontend
Event Enhancement
Events are enhanced with detection flags for frontend display:
pythondef enhance_events_with_flags(self, events, detections):
    """Add detection flags to events."""
    for event in events:
        ticker = event['ticker']
        
        # Add trend flags
        if ticker in detections['trending']:
            event['trend_flag'] = detections['trending'][ticker]['direction']
            event['trend_strength'] = detections['trending'][ticker]['strength']
        
        # Add surge flags
        if ticker in detections['surging']:
            event['surge_flag'] = detections['surging'][ticker]['direction']
            event['surge_score'] = detections['surging'][ticker]['score']
WebSocket Data Structure
javascript{
    "highs": [
        {
            "ticker": "AAPL",
            "price": 150.25,
            "trend_flag": "up",
            "trend_strength": "strong",
            "surge_flag": null
        }
    ],
    "trending": {
        "up": [...],
        "down": [...]
    },
    "surging": [...]
}
Performance Optimization
Efficient Data Structures
python# Circular buffer for price history
from collections import deque

class PriceBuffer:
    def __init__(self, max_size=300):
        self.buffer = deque(maxlen=max_size)
    
    def add(self, price_point):
        self.buffer.append(price_point)
Throttling Strategies
python# Analysis interval throttling
def should_analyze(self, last_analysis_time, interval):
    """Throttle analysis to configured intervals."""
    return (time.time() - last_analysis_time) >= interval
Memory Management
python# Automatic cleanup of old data
def cleanup_old_data(self, stock_data, max_age_seconds=600):
    """Remove data older than max age."""
    cutoff_time = time.time() - max_age_seconds
    stock_data['price_history'] = [
        point for point in stock_data['price_history']
        if point['timestamp'] > cutoff_time
    ]
Configuration Reference
Trend Detection Settings
ParameterDefaultDescriptionSHORT_WINDOW180sShort-term trend windowMEDIUM_WINDOW360sMedium-term trend windowLONG_WINDOW600sLong-term trend windowDIRECTION_THRESHOLD0.3Minimum score for trendSTRENGTH_THRESHOLD0.6Strong trend threshold
Surge Detection Settings
ParameterDefaultDescriptionINTERVAL_SECONDS15Analysis frequencyCOOLDOWN_SECONDS30Between surge eventsVOLUME_THRESHOLD1.5Volume multiplierMAX_BUFFER_SIZE20Price history points
Monitoring and Metrics
Performance Metrics
pythondef get_detection_metrics(self):
    return {
        'trends': {
            'detected': self.trends_detected,
            'avg_detection_time_ms': self.avg_trend_time,
            'active_trends': len(self.active_trends)
        },
        'surges': {
            'detected': self.surges_detected,
            'avg_detection_time_ms': self.avg_surge_time,
            'cooldown_active': self.cooldown_active_count
        }
    }
Health Monitoring
pythondef get_detector_health(self):
    return {
        'buffer_sizes': self._get_buffer_sizes(),
        'detection_rates': self._get_detection_rates(),
        'memory_usage_mb': self._calculate_memory_usage(),
        'last_detection': self.last_detection_time
    }
Best Practices
Detection Tuning

Start with default thresholds
Monitor false positive rates
Adjust based on market conditions
Consider different settings per universe

Performance Guidelines

Use throttling for expensive calculations
Implement circular buffers for history
Clean up old data regularly
Profile detection algorithms regularly

Integration Patterns
python# Clean integration with EventProcessor
class EventProcessor:
    def _process_tick_event(self, tick_data):
        # Efficient state lookup
        stock_state = self.get_ticker_state(tick_data.ticker)
        
        # Delegate to EventDetector
        detections = self.event_detector.detect_events(
            tick_data, stock_state
        )
        
        # Update state with results
        self.update_ticker_state(tick_data.ticker, detections)