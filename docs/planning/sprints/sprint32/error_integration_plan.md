# Sprint 32: TickStockPL Error Monitoring System

## Sprint Overview
**Sprint Number**: 32
**Sprint Name**: Error Monitoring & Logging Infrastructure
**Duration**: Standard Sprint
**Priority**: CRITICAL
**Status**: PLANNING
**Created**: 2024-10-30

## Business Context

### Problem Statement
TickStockPL processing is **critical to application success**, yet we currently have:
- **Zero visibility** into TickStockPL processing failures
- **Silent failures** in historical data imports (0 Redis subscribers detected)
- **No error alerting** for pattern detection failures
- **Sprint 31 blocked** due to integration issues we can't diagnose

### Impact of Current State
- Historical data imports failing without notification
- Pattern detection errors invisible to operations team
- Unable to diagnose integration issues between systems
- Production readiness at risk without error monitoring

### Success Criteria
- Real-time error visibility from TickStockPL via Redis channel
- Critical errors trigger immediate admin notifications
- Error logging to file when LOG_FILE_ENABLED=true
- Error statistics and health indicators in UI
- Historical error analysis capability via database storage

## Technical Specification

### 1. Redis Error Channel Integration

#### Channel Details
- **Channel Name**: `tickstock:errors` (from TickStockPL)
- **Message Format**: JSON with error details
- **Subscription**: Persistent connection with auto-reconnect

#### Error Message Structure (from TickStockPL)
```json
{
    "error_id": "PatternDetector_detect_doji_1234567890.123",
    "error_type": "PatternDetectionError",
    "error_message": "Pattern detection failed for Doji: Insufficient data",
    "error_traceback": "Full Python traceback...",
    "severity": "error",
    "category": "pattern",
    "context": {
        "component": "PatternDetector",
        "operation": "detect_doji",
        "symbol": "AAPL",
        "timeframe": "daily",
        "metadata": {},
        "timestamp": "2024-01-01T12:00:00"
    },
    "timestamp": "2024-01-01T12:00:00"
}
```

### 2. Error Severity Levels
- **debug**: Development information (not displayed in production)
- **info**: Informational messages (logged only)
- **warning**: Non-critical issues (displayed in UI)
- **error**: Failures requiring attention (alert + log)
- **critical**: System-critical failures (immediate notification)

### 3. Error Categories
- **pattern**: Pattern detection errors
- **indicator**: Indicator calculation errors
- **database**: Database connection/query errors
- **network**: Network/API errors (including Polygon.io)
- **validation**: Data validation errors
- **performance**: Performance threshold violations
- **configuration**: Configuration errors
- **unknown**: Uncategorized errors

### 4. File Logging Configuration

#### Environment Variable
```bash
# .env configuration
LOG_FILE_ENABLED=true  # Enable file logging
LOG_FILE_PATH=logs/tickstock_errors.log  # Log file location
LOG_FILE_MAX_SIZE=10485760  # 10MB max file size
LOG_FILE_BACKUP_COUNT=5  # Keep 5 backup files
```

#### Integration with Existing Logger
Use the standard application logger with file handler when enabled:

```python
import os
import logging
from logging.handlers import RotatingFileHandler

class ErrorMonitorLogger:
    def __init__(self):
        self.logger = logging.getLogger('tickstock.error_monitor')
        self.logger.setLevel(logging.INFO)

        # Add file handler if LOG_FILE_ENABLED
        if os.getenv('LOG_FILE_ENABLED', 'false').lower() == 'true':
            self._setup_file_handler()

    def _setup_file_handler(self):
        """Setup rotating file handler for error logging"""
        log_file = os.getenv('LOG_FILE_PATH', 'logs/tickstock_errors.log')
        max_size = int(os.getenv('LOG_FILE_MAX_SIZE', 10485760))  # 10MB
        backup_count = int(os.getenv('LOG_FILE_BACKUP_COUNT', 5))

        # Create logs directory if doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )

        # Set formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(file_handler)

    def log_error(self, error_data):
        """Log error based on severity"""
        severity = error_data.get('severity', 'error')
        message = self._format_error_message(error_data)

        if severity == 'critical':
            self.logger.critical(message)
        elif severity == 'error':
            self.logger.error(message)
        elif severity == 'warning':
            self.logger.warning(message)
        elif severity == 'info':
            self.logger.info(message)
        else:  # debug
            self.logger.debug(message)

    def _format_error_message(self, error_data):
        """Format error for logging"""
        return (
            f"[{error_data.get('category', 'unknown')}] "
            f"{error_data.get('error_type', 'Unknown')}: "
            f"{error_data.get('error_message', 'No message')} "
            f"(Symbol: {error_data.get('context', {}).get('symbol', 'N/A')})"
        )
```

## Implementation Plan

### Phase 1: Core Error Monitoring (Priority 1)

#### 1.1 Redis Subscriber Service
**File**: `src/core/services/error_monitor_service.py`

```python
import redis
import json
import threading
import logging
from typing import Callable, List, Dict, Any
from datetime import datetime

class ErrorMonitorService:
    """Service to monitor TickStockPL errors via Redis channel"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.pubsub = None
        self.monitoring = False
        self.error_callbacks: List[Callable] = []
        self.error_logger = ErrorMonitorLogger()
        self.logger = logging.getLogger(__name__)
        self.listener_thread = None

    def start(self):
        """Start monitoring the error channel"""
        try:
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe('tickstock:errors')
            self.monitoring = True

            # Start listener thread
            self.listener_thread = threading.Thread(
                target=self._listen_for_errors,
                daemon=True
            )
            self.listener_thread.start()

            self.logger.info("Error monitoring service started")

        except Exception as e:
            self.logger.error(f"Failed to start error monitoring: {e}")
            raise

    def _listen_for_errors(self):
        """Listen for error messages from TickStockPL"""
        for message in self.pubsub.listen():
            if not self.monitoring:
                break

            if message['type'] == 'message':
                try:
                    error_data = json.loads(message['data'])
                    self._process_error(error_data)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid error message format: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")

    def _process_error(self, error_data: Dict[str, Any]):
        """Process incoming error from TickStockPL"""
        # Log to file if enabled
        self.error_logger.log_error(error_data)

        # Store in database for critical/error severity
        if error_data.get('severity') in ['critical', 'error']:
            self._store_error_in_db(error_data)

        # Call registered callbacks (for WebSocket broadcasting)
        for callback in self.error_callbacks:
            try:
                callback(error_data)
            except Exception as e:
                self.logger.error(f"Error callback failed: {e}")

    def _store_error_in_db(self, error_data: Dict[str, Any]):
        """Store error in database for analysis"""
        # Implementation for database storage
        pass

    def register_callback(self, callback: Callable):
        """Register callback for error notifications"""
        self.error_callbacks.append(callback)

    def stop(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.pubsub:
            self.pubsub.unsubscribe('tickstock:errors')
        self.logger.info("Error monitoring service stopped")
```

#### 1.2 WebSocket Broadcasting
**File**: `src/api/websocket/error_broadcaster.py`

```python
from flask_socketio import SocketIO, emit
from typing import Dict, Any
import logging

class ErrorBroadcaster:
    """Broadcast TickStockPL errors to WebSocket clients"""

    def __init__(self, socketio: SocketIO, error_monitor: ErrorMonitorService):
        self.socketio = socketio
        self.error_monitor = error_monitor
        self.logger = logging.getLogger(__name__)

        # Register as callback for error notifications
        self.error_monitor.register_callback(self.broadcast_error)

    def broadcast_error(self, error_data: Dict[str, Any]):
        """Broadcast error to connected WebSocket clients"""
        try:
            # Filter what to broadcast based on severity
            if error_data.get('severity') in ['warning', 'error', 'critical']:

                # Prepare client-friendly error format
                client_error = {
                    'id': error_data.get('error_id'),
                    'type': error_data.get('error_type'),
                    'message': error_data.get('error_message'),
                    'severity': error_data.get('severity'),
                    'category': error_data.get('category'),
                    'symbol': error_data.get('context', {}).get('symbol'),
                    'component': error_data.get('context', {}).get('component'),
                    'timestamp': error_data.get('timestamp')
                }

                # Broadcast to error monitoring namespace
                self.socketio.emit(
                    'tickstock_error',
                    client_error,
                    namespace='/monitoring'
                )

                # For critical errors, also broadcast to main namespace
                if error_data.get('severity') == 'critical':
                    self.socketio.emit(
                        'critical_error',
                        client_error,
                        namespace='/'
                    )

                self.logger.debug(f"Broadcasted error: {error_data.get('error_id')}")

        except Exception as e:
            self.logger.error(f"Failed to broadcast error: {e}")
```

### Phase 2: Database Storage (Priority 2)

#### 2.1 Error Storage Model
**File**: `src/models/error_log.py`

```python
from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.models.base import Base
import uuid
from datetime import datetime

class ErrorLog(Base):
    """Store TickStockPL errors for analysis"""

    __tablename__ = 'error_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    error_id = Column(String(255), unique=True, index=True)
    error_type = Column(String(100), index=True)
    error_message = Column(Text)
    error_traceback = Column(Text)
    severity = Column(String(20), index=True)
    category = Column(String(50), index=True)
    component = Column(String(100))
    operation = Column(String(100))
    symbol = Column(String(10), index=True)
    context = Column(JSONB)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### 2.2 Database Migration
**File**: `scripts/database/create_error_logs_table.sql`

```sql
-- Create error_logs table for TickStockPL error storage
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_id VARCHAR(255) UNIQUE NOT NULL,
    error_type VARCHAR(100),
    error_message TEXT,
    error_traceback TEXT,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    component VARCHAR(100),
    operation VARCHAR(100),
    symbol VARCHAR(10),
    context JSONB,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX idx_error_logs_timestamp ON error_logs(timestamp DESC);
CREATE INDEX idx_error_logs_severity ON error_logs(severity);
CREATE INDEX idx_error_logs_category ON error_logs(category);
CREATE INDEX idx_error_logs_symbol ON error_logs(symbol);
CREATE INDEX idx_error_logs_error_type ON error_logs(error_type);

-- Index for recent errors by severity
CREATE INDEX idx_error_logs_recent_critical
ON error_logs(timestamp DESC)
WHERE severity IN ('critical', 'error');
```

### Phase 3: UI Components (Priority 3)

#### 3.1 Error Display Components
**File**: `web/static/js/error_monitor.js`

```javascript
class ErrorMonitor {
    constructor() {
        this.errors = [];
        this.maxErrors = 100;
        this.filter = 'all';
        this.socket = null;
        this.errorContainer = null;
        this.statsContainer = null;
        this.errorCounts = {
            total: 0,
            critical: 0,
            error: 0,
            warning: 0
        };
    }

    init() {
        // Initialize WebSocket connection
        this.socket = io('/monitoring');

        // Set up event listeners
        this.socket.on('tickstock_error', (error) => {
            this.handleError(error);
        });

        this.socket.on('critical_error', (error) => {
            this.showCriticalNotification(error);
        });

        // Initialize UI containers
        this.errorContainer = document.getElementById('error-list');
        this.statsContainer = document.getElementById('error-stats');

        // Set up filter buttons
        this.setupFilters();

        // Load recent errors
        this.loadRecentErrors();
    }

    handleError(error) {
        // Add to errors array
        this.errors.unshift(error);
        if (this.errors.length > this.maxErrors) {
            this.errors.pop();
        }

        // Update counts
        this.updateErrorCounts(error);

        // Update display
        this.updateErrorDisplay();

        // Show notification for critical/error severity
        if (error.severity === 'critical' || error.severity === 'error') {
            this.showNotification(error);
        }
    }

    updateErrorCounts(error) {
        this.errorCounts.total++;
        this.errorCounts[error.severity]++;
        this.updateStatsDisplay();
    }

    updateStatsDisplay() {
        if (!this.statsContainer) return;

        this.statsContainer.innerHTML = `
            <div class="error-stats-grid">
                <div class="stat-card">
                    <span class="stat-label">Total</span>
                    <span class="stat-value">${this.errorCounts.total}</span>
                </div>
                <div class="stat-card critical">
                    <span class="stat-label">Critical</span>
                    <span class="stat-value">${this.errorCounts.critical}</span>
                </div>
                <div class="stat-card error">
                    <span class="stat-label">Errors</span>
                    <span class="stat-value">${this.errorCounts.error}</span>
                </div>
                <div class="stat-card warning">
                    <span class="stat-label">Warnings</span>
                    <span class="stat-value">${this.errorCounts.warning}</span>
                </div>
            </div>
        `;
    }

    updateErrorDisplay() {
        if (!this.errorContainer) return;

        const filteredErrors = this.filter === 'all'
            ? this.errors
            : this.errors.filter(e => e.category === this.filter);

        const errorHtml = filteredErrors.map(error => `
            <div class="error-item ${error.severity}">
                <div class="error-header">
                    <span class="error-time">${this.formatTime(error.timestamp)}</span>
                    <span class="error-severity badge-${error.severity}">${error.severity}</span>
                    <span class="error-category">[${error.category}]</span>
                    ${error.symbol ? `<span class="error-symbol">${error.symbol}</span>` : ''}
                </div>
                <div class="error-message">${error.message}</div>
                ${error.component ? `<div class="error-component">Component: ${error.component}</div>` : ''}
            </div>
        `).join('');

        this.errorContainer.innerHTML = errorHtml;
    }

    showNotification(error) {
        // Use existing notification system or create toast
        const notification = document.createElement('div');
        notification.className = `notification notification-${error.severity}`;
        notification.innerHTML = `
            <strong>${error.category}:</strong> ${error.message}
            ${error.symbol ? `(${error.symbol})` : ''}
        `;

        document.getElementById('notifications').appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => notification.remove(), 5000);
    }

    showCriticalNotification(error) {
        // More prominent notification for critical errors
        alert(`CRITICAL ERROR: ${error.message}`);
        // In production, use a better notification system
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    }

    setupFilters() {
        document.querySelectorAll('.error-filter').forEach(button => {
            button.addEventListener('click', (e) => {
                this.filter = e.target.dataset.filter;
                this.updateErrorDisplay();
            });
        });
    }

    async loadRecentErrors() {
        try {
            const response = await fetch('/api/errors/recent');
            const errors = await response.json();
            errors.forEach(error => this.handleError(error));
        } catch (e) {
            console.error('Failed to load recent errors:', e);
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const errorMonitor = new ErrorMonitor();
    errorMonitor.init();
});
```

#### 3.2 Admin Dashboard Component
**File**: `web/templates/admin/error_monitoring.html`

```html
{% extends "base.html" %}

{% block title %}Error Monitoring - TickStock Admin{% endblock %}

{% block content %}
<div class="error-monitoring-dashboard">
    <h1>TickStockPL Error Monitoring</h1>

    <!-- Error Statistics -->
    <div id="error-stats" class="stats-section">
        <!-- Populated by JavaScript -->
    </div>

    <!-- System Health Indicator -->
    <div class="health-indicator">
        <span class="health-label">System Health:</span>
        <span id="health-status" class="health-status health-green">Operational</span>
    </div>

    <!-- Error Filters -->
    <div class="error-filters">
        <button class="error-filter active" data-filter="all">All</button>
        <button class="error-filter" data-filter="pattern">Pattern</button>
        <button class="error-filter" data-filter="indicator">Indicator</button>
        <button class="error-filter" data-filter="database">Database</button>
        <button class="error-filter" data-filter="network">Network</button>
        <button class="error-filter" data-filter="validation">Validation</button>
        <button class="error-filter" data-filter="performance">Performance</button>
    </div>

    <!-- Error List -->
    <div class="error-list-container">
        <h2>Recent Errors</h2>
        <div id="error-list" class="error-list">
            <!-- Populated by JavaScript -->
        </div>
    </div>

    <!-- Notifications Container -->
    <div id="notifications" class="notifications-container"></div>
</div>

<style>
.error-monitoring-dashboard {
    padding: 20px;
}

.stats-section {
    margin-bottom: 20px;
}

.error-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.stat-card {
    background: white;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 15px;
    text-align: center;
}

.stat-card.critical {
    border-color: #dc3545;
}

.stat-card.error {
    border-color: #fd7e14;
}

.stat-card.warning {
    border-color: #ffc107;
}

.stat-label {
    display: block;
    font-size: 14px;
    color: #666;
}

.stat-value {
    display: block;
    font-size: 24px;
    font-weight: bold;
    margin-top: 5px;
}

.health-indicator {
    margin-bottom: 20px;
    padding: 10px;
    background: white;
    border-radius: 5px;
}

.health-status {
    font-weight: bold;
    padding: 5px 10px;
    border-radius: 3px;
}

.health-green {
    background: #28a745;
    color: white;
}

.health-yellow {
    background: #ffc107;
    color: black;
}

.health-red {
    background: #dc3545;
    color: white;
}

.error-filters {
    margin-bottom: 20px;
}

.error-filter {
    padding: 8px 16px;
    margin-right: 10px;
    border: 1px solid #ddd;
    background: white;
    border-radius: 3px;
    cursor: pointer;
}

.error-filter.active {
    background: #007bff;
    color: white;
}

.error-list {
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
    background: white;
}

.error-item {
    padding: 10px;
    margin-bottom: 10px;
    border-left: 4px solid #ddd;
    background: #f9f9f9;
}

.error-item.critical {
    border-left-color: #dc3545;
    background: #fff5f5;
}

.error-item.error {
    border-left-color: #fd7e14;
    background: #fff9f5;
}

.error-item.warning {
    border-left-color: #ffc107;
    background: #fffef5;
}

.error-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 5px;
}

.error-time {
    font-size: 12px;
    color: #666;
}

.badge-critical {
    background: #dc3545;
    color: white;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
}

.badge-error {
    background: #fd7e14;
    color: white;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
}

.badge-warning {
    background: #ffc107;
    color: black;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
}

.error-category {
    font-weight: bold;
    color: #333;
}

.error-symbol {
    background: #e9ecef;
    padding: 2px 6px;
    border-radius: 3px;
}

.error-message {
    margin-bottom: 5px;
}

.error-component {
    font-size: 12px;
    color: #666;
}

.notifications-container {
    position: fixed;
    top: 70px;
    right: 20px;
    z-index: 1000;
}

.notification {
    padding: 15px;
    margin-bottom: 10px;
    border-radius: 5px;
    background: white;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    animation: slideIn 0.3s ease;
}

.notification-critical {
    border-left: 4px solid #dc3545;
}

.notification-error {
    border-left: 4px solid #fd7e14;
}

.notification-warning {
    border-left: 4px solid #ffc107;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}
</style>

<script src="{{ url_for('static', filename='js/error_monitor.js') }}"></script>
{% endblock %}
```

### Phase 4: API Endpoints (Priority 4)

#### 4.1 Error REST API
**File**: `src/api/rest/error_monitoring.py`

```python
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from src.models.error_log import ErrorLog
from src.database import db
import logging

error_monitoring_bp = Blueprint('error_monitoring', __name__)
logger = logging.getLogger(__name__)

@error_monitoring_bp.route('/api/errors/recent', methods=['GET'])
def get_recent_errors():
    """Get recent errors for display"""
    try:
        limit = request.args.get('limit', 100, type=int)

        # Query recent errors from database
        recent_errors = db.session.query(ErrorLog)\
            .order_by(ErrorLog.timestamp.desc())\
            .limit(limit)\
            .all()

        # Format for client
        errors = [{
            'id': str(error.error_id),
            'type': error.error_type,
            'message': error.error_message,
            'severity': error.severity,
            'category': error.category,
            'symbol': error.symbol,
            'component': error.component,
            'timestamp': error.timestamp.isoformat()
        } for error in recent_errors]

        return jsonify(errors)

    except Exception as e:
        logger.error(f"Failed to get recent errors: {e}")
        return jsonify({'error': 'Failed to retrieve errors'}), 500

@error_monitoring_bp.route('/api/errors/statistics', methods=['GET'])
def get_error_statistics():
    """Get error statistics for dashboard"""
    try:
        # Time range (last 24 hours by default)
        hours = request.args.get('hours', 24, type=int)
        since = datetime.utcnow() - timedelta(hours=hours)

        # Query statistics
        stats = db.session.query(
            ErrorLog.severity,
            db.func.count(ErrorLog.id).label('count')
        ).filter(
            ErrorLog.timestamp >= since
        ).group_by(
            ErrorLog.severity
        ).all()

        # Query by category
        category_stats = db.session.query(
            ErrorLog.category,
            db.func.count(ErrorLog.id).label('count')
        ).filter(
            ErrorLog.timestamp >= since
        ).group_by(
            ErrorLog.category
        ).all()

        # Format response
        response = {
            'timeRange': f'last_{hours}_hours',
            'bySeverity': {s.severity: s.count for s in stats},
            'byCategory': {c.category: c.count for c in category_stats},
            'total': sum(s.count for s in stats)
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Failed to get error statistics: {e}")
        return jsonify({'error': 'Failed to retrieve statistics'}), 500

@error_monitoring_bp.route('/api/errors/health', methods=['GET'])
def get_system_health():
    """Get system health based on error rates"""
    try:
        # Check errors in last 5 minutes
        since = datetime.utcnow() - timedelta(minutes=5)

        critical_count = db.session.query(ErrorLog).filter(
            ErrorLog.timestamp >= since,
            ErrorLog.severity == 'critical'
        ).count()

        error_count = db.session.query(ErrorLog).filter(
            ErrorLog.timestamp >= since,
            ErrorLog.severity == 'error'
        ).count()

        # Determine health status
        if critical_count > 0:
            status = 'critical'
            health = 'red'
        elif error_count > 10:
            status = 'degraded'
            health = 'yellow'
        else:
            status = 'operational'
            health = 'green'

        return jsonify({
            'status': status,
            'health': health,
            'criticalErrors': critical_count,
            'errors': error_count,
            'checkTime': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return jsonify({'status': 'unknown', 'health': 'gray'}), 500
```

## Testing Plan

### 1. Test Error Generation Script
**File**: `scripts/test_error_monitoring.py`

```python
#!/usr/bin/env python3
"""Test error monitoring system"""

import redis
import json
import time
import random
from datetime import datetime

def send_test_error(severity='error', category='pattern'):
    """Send a test error to the channel"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    # Generate test error
    test_error = {
        'error_id': f'Test_{category}_{datetime.utcnow().timestamp()}',
        'error_type': f'Test{category.title()}Error',
        'error_message': f'This is a test {severity} message for {category}',
        'error_traceback': 'Test traceback...\nLine 2\nLine 3',
        'severity': severity,
        'category': category,
        'context': {
            'component': 'TestComponent',
            'operation': 'test_operation',
            'symbol': random.choice(['AAPL', 'GOOGL', 'MSFT', 'TSLA']),
            'timeframe': 'daily',
            'metadata': {'test': True},
            'timestamp': datetime.utcnow().isoformat()
        },
        'timestamp': datetime.utcnow().isoformat()
    }

    # Publish to error channel
    subscribers = r.publish('tickstock:errors', json.dumps(test_error))

    print(f"Test {severity} error sent to {subscribers} subscribers")
    print(f"Category: {category}, Symbol: {test_error['context']['symbol']}")

    return test_error

def run_test_sequence():
    """Run a sequence of test errors"""
    print("Starting error monitoring test sequence...")
    print("=" * 50)

    # Test different severities
    for severity in ['debug', 'info', 'warning', 'error', 'critical']:
        send_test_error(severity=severity, category='test')
        time.sleep(1)

    print("\n" + "=" * 50)

    # Test different categories
    categories = ['pattern', 'indicator', 'database', 'network', 'validation']
    for category in categories:
        send_test_error(severity='error', category=category)
        time.sleep(1)

    print("\n" + "=" * 50)
    print("Test sequence complete!")
    print("\nCheck the following:")
    print("1. Error monitoring dashboard for displayed errors")
    print("2. Log file (if LOG_FILE_ENABLED=true)")
    print("3. Database error_logs table for stored errors")
    print("4. WebSocket clients for real-time updates")

if __name__ == "__main__":
    run_test_sequence()
```

### 2. Integration Test
**File**: `tests/sprint32/test_error_monitoring_integration.py`

```python
import pytest
import redis
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch

def test_error_subscription():
    """Test that service subscribes to correct channel"""
    # Test implementation
    pass

def test_error_logging_to_file():
    """Test file logging when LOG_FILE_ENABLED=true"""
    # Test implementation
    pass

def test_error_database_storage():
    """Test that critical errors are stored in database"""
    # Test implementation
    pass

def test_websocket_broadcasting():
    """Test that errors are broadcast via WebSocket"""
    # Test implementation
    pass

def test_error_statistics():
    """Test error statistics calculation"""
    # Test implementation
    pass

def test_system_health_indicator():
    """Test system health based on error rates"""
    # Test implementation
    pass
```

## Deployment Checklist

### Pre-Deployment
- [ ] Create `error_logs` table in database
- [ ] Set `LOG_FILE_ENABLED` in `.env` file
- [ ] Create `logs` directory with proper permissions
- [ ] Update Flask app to initialize ErrorMonitorService
- [ ] Add error monitoring route to admin navigation

### Deployment Steps
1. Run database migration script
2. Deploy error monitoring service code
3. Start ErrorMonitorService on app startup
4. Verify Redis subscription active
5. Run test error sequence
6. Verify file logging working
7. Check WebSocket broadcasting
8. Confirm UI displays errors

### Post-Deployment Verification
- [ ] Redis channel has 1+ subscribers
- [ ] Test errors appear in UI
- [ ] Critical errors trigger notifications
- [ ] Errors logged to file (if enabled)
- [ ] Database contains error records
- [ ] Health indicator reflects system state

## Success Metrics

1. **Real-time Detection**: Errors appear in UI within 1 second
2. **Zero Error Loss**: All critical/error severity logged
3. **File Logging**: Errors written to file when enabled
4. **UI Responsiveness**: Dashboard loads in <500ms
5. **Alert Latency**: Critical errors alert within 2 seconds
6. **Storage Efficiency**: Database queries complete in <50ms

## Alert Thresholds

- **Critical Alert**: Any critical severity error
- **Error Rate Alert**: >10 errors per minute
- **Category Alert**: >5 errors in same category within 5 minutes
- **Pattern Failure Alert**: >3 pattern detection failures for same symbol
- **Database Alert**: Any database connection error

## Monitoring & Maintenance

### Daily Checks
- Review critical errors from last 24 hours
- Check error trends by category
- Verify log file rotation working

### Weekly Tasks
- Analyze error patterns for root causes
- Clean up old errors (>30 days)
- Review and adjust alert thresholds

### Monthly Review
- Error trend analysis
- System health report
- Performance optimization if needed

## Risk Mitigation

### Potential Issues & Solutions

1. **High Error Volume**
   - Solution: Implement rate limiting and aggregation
   - Buffer errors and batch database writes

2. **Redis Connection Loss**
   - Solution: Auto-reconnect with exponential backoff
   - Cache errors locally until connection restored

3. **Database Storage Full**
   - Solution: Automated cleanup of old errors
   - Archive errors older than 30 days

4. **WebSocket Overload**
   - Solution: Throttle broadcasts to max 10/second
   - Aggregate similar errors before broadcasting

## Documentation References

- TickStockPL Error Guide: `C:\Users\McDude\TickStockPL\docs\guides\ERROR_MONITORING_GUIDE.md`
- Redis Pub/Sub: https://redis.io/topics/pubsub
- Flask-SocketIO: https://flask-socketio.readthedocs.io/
- Python Logging: https://docs.python.org/3/library/logging.html

---

**Sprint Status**: PLANNING
**Last Updated**: 2024-10-30
**Owner**: TickStockAppV2 Team
**Priority**: CRITICAL - Required for production readiness