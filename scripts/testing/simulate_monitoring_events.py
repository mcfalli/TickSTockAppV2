#!/usr/bin/env python3
"""
Simulate TickStockPL monitoring events for testing the dashboard.
This script publishes events to Redis in the same format as TickStockPL.
"""

import json
import redis
import time
import random
from datetime import datetime

def publish_monitoring_events():
    """Publish simulated monitoring events to Redis channel."""

    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    print("Publishing simulated TickStockPL monitoring events...")
    print("Watch the dashboard at http://localhost:5000/admin/monitoring")
    print("Press Ctrl+C to stop\n")

    event_count = 0

    try:
        while True:
            # Create a METRIC_UPDATE event
            metric_event = {
                "event_type": "METRIC_UPDATE",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "TickStockPL-Simulator",
                "metrics": {
                    "system": {
                        "cpu_percent": round(random.uniform(20, 80), 1),
                        "memory_percent": round(random.uniform(40, 70), 1),
                        "disk_percent": round(random.uniform(30, 60), 1),
                        "network_io": {
                            "bytes_sent": random.randint(1000000, 5000000),
                            "bytes_recv": random.randint(1000000, 5000000)
                        }
                    },
                    "processing": {
                        "ticks_per_second": random.randint(1000, 5000),
                        "patterns_detected": random.randint(0, 10),
                        "active_backtests": random.randint(0, 3),
                        "queue_depth": random.randint(0, 100)
                    },
                    "redis": {
                        "connected": True,
                        "channels": 4,
                        "messages_published": random.randint(100, 1000),
                        "memory_usage_mb": round(random.uniform(50, 150), 1)
                    },
                    "database": {
                        "connected": True,
                        "active_connections": random.randint(1, 10),
                        "query_latency_ms": round(random.uniform(1, 50), 2),
                        "last_write": datetime.utcnow().isoformat()
                    }
                },
                "health_score": {
                    "overall": random.randint(85, 100),
                    "status": "healthy" if random.random() > 0.2 else "warning",
                    "components": {
                        "market_data": "healthy",
                        "pattern_detection": "healthy",
                        "backtesting": "healthy" if random.random() > 0.1 else "warning",
                        "database": "healthy",
                        "redis": "healthy"
                    }
                }
            }

            # Publish metric event
            r.publish('tickstock:monitoring', json.dumps(metric_event))
            event_count += 1
            print(f"[{event_count}] Published METRIC_UPDATE - CPU: {metric_event['metrics']['system']['cpu_percent']}%, Health: {metric_event['health_score']['overall']}")

            # Occasionally send an alert
            if random.random() < 0.1:  # 10% chance
                alert_event = {
                    "event_type": "ALERT_TRIGGERED",
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "TickStockPL-Simulator",
                    "alert": {
                        "id": f"alert_{event_count}",
                        "level": random.choice(["warning", "error", "critical"]),
                        "component": random.choice(["market_data", "pattern_detection", "backtesting", "database"]),
                        "message": random.choice([
                            "High memory usage detected",
                            "Pattern detection latency increased",
                            "Database connection pool exhausted",
                            "Backtesting queue backlog growing",
                            "Market data feed delay detected"
                        ]),
                        "details": {
                            "threshold": random.randint(70, 90),
                            "current_value": random.randint(80, 100),
                            "duration_seconds": random.randint(30, 300)
                        }
                    }
                }

                r.publish('tickstock:monitoring', json.dumps(alert_event))
                event_count += 1
                print(f"[{event_count}] Published ALERT_TRIGGERED - {alert_event['alert']['level'].upper()}: {alert_event['alert']['message']}")

            # Send health check every 10 events
            if event_count % 10 == 0:
                health_event = {
                    "event_type": "HEALTH_CHECK",
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "TickStockPL-Simulator",
                    "status": "healthy",
                    "components": {
                        "market_data": {"status": "healthy", "latency_ms": random.randint(1, 10)},
                        "pattern_detection": {"status": "healthy", "patterns_per_sec": random.randint(100, 500)},
                        "backtesting": {"status": "healthy", "active_jobs": random.randint(0, 5)},
                        "database": {"status": "healthy", "connections": random.randint(1, 10)},
                        "redis": {"status": "healthy", "memory_mb": random.randint(50, 150)}
                    }
                }

                r.publish('tickstock:monitoring', json.dumps(health_event))
                event_count += 1
                print(f"[{event_count}] Published HEALTH_CHECK - All systems healthy")

            # Wait before next event
            time.sleep(2)  # Send events every 2 seconds

    except KeyboardInterrupt:
        print(f"\n\nStopped. Published {event_count} events total.")

        # Send a system status event before stopping
        status_event = {
            "event_type": "SYSTEM_STATUS",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "TickStockPL-Simulator",
            "status": "stopping",
            "message": "Simulator stopped by user",
            "uptime_seconds": event_count * 2,
            "events_published": event_count
        }

        r.publish('tickstock:monitoring', json.dumps(status_event))
        print("Published SYSTEM_STATUS: Simulator stopping")

if __name__ == "__main__":
    publish_monitoring_events()