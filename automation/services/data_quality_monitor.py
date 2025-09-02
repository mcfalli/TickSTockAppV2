#!/usr/bin/env python3
"""
Data Quality Monitoring Service - Sprint 14 Phase 2 Story 3.4

This service monitors data quality across the TickStock system:
- Detects price anomalies (>20% single-day moves)
- Identifies data gaps in historical records
- Monitors volume patterns and unusual activity
- Provides automated remediation recommendations
- Publishes quality alerts via Redis to TickStockApp

Architecture:
- Runs as separate service from TickStockApp
- Full database read/write access for quality monitoring
- Redis pub-sub notifications to TickStockApp consumers
- Maintains loose coupling through message passing
"""

import os
import sys
import asyncio
import json
import logging
import redis.asyncio as redis
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import psycopg2
import psycopg2.extras
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

try:
    import schedule
except ImportError:
    schedule = None
    print("+ Schedule module not available - manual execution mode")

@dataclass
class DataQualityAlert:
    """Data quality alert structure"""
    alert_type: str
    symbol: str
    severity: str  # low, medium, high, critical
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    remediation_suggestion: str

class DataQualityMonitor:
    """
    Data Quality Monitoring Service
    
    Monitors data integrity across the TickStock system with focus on:
    - Price anomaly detection (>20% moves, gaps, spikes)
    - Volume pattern analysis (unusual activity, zero volume)
    - Data completeness (missing records, stale data)
    - Market timing validation (trading hours, holiday schedules)
    """
    
    def __init__(self, database_uri: str = None, redis_host: str = None):
        """Initialize data quality monitor with database and Redis connections"""
        self.database_uri = database_uri or os.getenv(
            'DATABASE_URL',
            'postgresql://app_readwrite:4pp_U$3r_2024!@localhost/tickstock'
        )
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        
        # Quality monitoring configuration
        self.price_anomaly_threshold = 0.20  # 20% single-day move
        self.volume_spike_threshold = 5.0    # 5x average volume
        self.data_staleness_hours = 48       # Alert if data older than 48 hours
        self.min_trading_volume = 1000       # Minimum expected daily volume
        
        # Redis channels for quality alerts
        self.channels = {
            'price_anomaly': 'tickstock.quality.price_anomaly',
            'volume_anomaly': 'tickstock.quality.volume_anomaly',
            'data_gap': 'tickstock.quality.data_gap',
            'stale_data': 'tickstock.quality.stale_data',
            'quality_summary': 'tickstock.quality.daily_summary'
        }
        
        # Market timing configuration
        self.market_open = dt_time(9, 30)    # 9:30 AM ET
        self.market_close = dt_time(16, 0)   # 4:00 PM ET
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    async def connect_redis(self) -> Optional[redis.Redis]:
        """Establish Redis connection for publishing quality alerts"""
        try:
            redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                health_check_interval=30
            )
            
            await redis_client.ping()
            self.logger.info(f"+ Redis connected: {self.redis_host}:{self.redis_port}")
            return redis_client
            
        except Exception as e:
            self.logger.error(f"- Redis connection failed: {e}")
            return None
    
    def get_database_connection(self):
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(
                self.database_uri,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            return conn
        except Exception as e:
            self.logger.error(f"- Database connection failed: {e}")
            return None
    
    async def detect_price_anomalies(self, lookback_days: int = 3) -> List[DataQualityAlert]:
        """
        Detect price anomalies including large single-day moves and gaps
        
        Args:
            lookback_days: Number of days to analyze for anomalies
            
        Returns:
            List of price anomaly alerts
        """
        alerts = []
        
        conn = self.get_database_connection()
        if not conn:
            return alerts
            
        try:
            cursor = conn.cursor()
            
            # Query for significant price movements
            anomaly_query = """
            WITH daily_changes AS (
                SELECT 
                    symbol,
                    date,
                    close_price,
                    LAG(close_price) OVER (PARTITION BY symbol ORDER BY date) as prev_close,
                    volume,
                    high_price,
                    low_price
                FROM historical_data 
                WHERE date >= %s
                AND close_price > 0
                AND volume > 0
            ),
            price_changes AS (
                SELECT 
                    symbol,
                    date,
                    close_price,
                    prev_close,
                    volume,
                    high_price,
                    low_price,
                    CASE 
                        WHEN prev_close > 0 THEN 
                            ABS(close_price - prev_close) / prev_close 
                        ELSE 0 
                    END as price_change_pct,
                    CASE 
                        WHEN prev_close > 0 THEN 
                            (high_price - low_price) / prev_close 
                        ELSE 0 
                    END as intraday_range_pct
                FROM daily_changes
                WHERE prev_close IS NOT NULL
            )
            SELECT 
                symbol,
                date,
                close_price,
                prev_close,
                volume,
                price_change_pct,
                intraday_range_pct
            FROM price_changes
            WHERE price_change_pct > %s  -- Anomaly threshold
            OR intraday_range_pct > %s   -- Large intraday range
            ORDER BY price_change_pct DESC, date DESC
            LIMIT 50;
            """
            
            cutoff_date = datetime.now().date() - timedelta(days=lookback_days)
            cursor.execute(anomaly_query, (
                cutoff_date, 
                self.price_anomaly_threshold,
                self.price_anomaly_threshold * 1.5  # 30% intraday range threshold
            ))
            
            anomalies = cursor.fetchall()
            
            for anomaly in anomalies:
                severity = self._classify_price_anomaly_severity(
                    float(anomaly['price_change_pct'])
                )
                
                alert = DataQualityAlert(
                    alert_type='price_anomaly',
                    symbol=anomaly['symbol'],
                    severity=severity,
                    description=f"Large price movement detected: {anomaly['price_change_pct']:.1%}",
                    details={
                        'date': anomaly['date'].isoformat(),
                        'close_price': float(anomaly['close_price']),
                        'previous_close': float(anomaly['prev_close']),
                        'price_change_pct': float(anomaly['price_change_pct']),
                        'volume': int(anomaly['volume']),
                        'intraday_range_pct': float(anomaly['intraday_range_pct'])
                    },
                    timestamp=datetime.now(),
                    remediation_suggestion=self._get_price_anomaly_remediation(
                        float(anomaly['price_change_pct'])
                    )
                )
                
                alerts.append(alert)
                
        except Exception as e:
            self.logger.error(f"- Price anomaly detection failed: {e}")
        finally:
            if conn:
                conn.close()
        
        self.logger.info(f"+ Detected {len(alerts)} price anomalies")
        return alerts
    
    async def detect_volume_anomalies(self, lookback_days: int = 7) -> List[DataQualityAlert]:
        """
        Detect volume anomalies including spikes and zero volume periods
        
        Args:
            lookback_days: Number of days to analyze volume patterns
            
        Returns:
            List of volume anomaly alerts
        """
        alerts = []
        
        conn = self.get_database_connection()
        if not conn:
            return alerts
            
        try:
            cursor = conn.cursor()
            
            # Query for volume anomalies
            volume_query = """
            WITH volume_stats AS (
                SELECT 
                    symbol,
                    date,
                    volume,
                    AVG(volume) OVER (
                        PARTITION BY symbol 
                        ORDER BY date 
                        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                    ) as avg_volume_20d,
                    STDDEV(volume) OVER (
                        PARTITION BY symbol 
                        ORDER BY date 
                        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                    ) as stddev_volume_20d
                FROM historical_data 
                WHERE date >= %s
                AND volume >= 0
            )
            SELECT 
                symbol,
                date,
                volume,
                avg_volume_20d,
                CASE 
                    WHEN avg_volume_20d > 0 THEN volume / avg_volume_20d 
                    ELSE 0 
                END as volume_ratio
            FROM volume_stats
            WHERE avg_volume_20d IS NOT NULL
            AND (
                volume = 0  -- Zero volume detection
                OR (avg_volume_20d > %s AND volume > avg_volume_20d * %s)  -- Volume spike
                OR (avg_volume_20d > %s AND volume < avg_volume_20d * 0.1)  -- Volume drought
            )
            ORDER BY volume_ratio DESC, date DESC
            LIMIT 50;
            """
            
            cutoff_date = datetime.now().date() - timedelta(days=lookback_days)
            cursor.execute(volume_query, (
                cutoff_date,
                self.min_trading_volume,
                self.volume_spike_threshold,
                self.min_trading_volume
            ))
            
            volume_anomalies = cursor.fetchall()
            
            for anomaly in volume_anomalies:
                volume = int(anomaly['volume'])
                avg_volume = float(anomaly['avg_volume_20d'] or 0)
                volume_ratio = float(anomaly['volume_ratio'] or 0)
                
                if volume == 0:
                    alert_type = 'zero_volume'
                    description = "Zero volume detected"
                    severity = 'medium'
                elif volume_ratio >= self.volume_spike_threshold:
                    alert_type = 'volume_spike'
                    description = f"Volume spike: {volume_ratio:.1f}x normal"
                    severity = 'high'
                else:
                    alert_type = 'volume_drought'
                    description = f"Unusually low volume: {volume_ratio:.1%} of normal"
                    severity = 'medium'
                
                alert = DataQualityAlert(
                    alert_type=alert_type,
                    symbol=anomaly['symbol'],
                    severity=severity,
                    description=description,
                    details={
                        'date': anomaly['date'].isoformat(),
                        'volume': volume,
                        'average_volume_20d': avg_volume,
                        'volume_ratio': volume_ratio
                    },
                    timestamp=datetime.now(),
                    remediation_suggestion=self._get_volume_anomaly_remediation(alert_type)
                )
                
                alerts.append(alert)
                
        except Exception as e:
            self.logger.error(f"- Volume anomaly detection failed: {e}")
        finally:
            if conn:
                conn.close()
        
        self.logger.info(f"+ Detected {len(alerts)} volume anomalies")
        return alerts
    
    async def detect_data_gaps(self, lookback_days: int = 30) -> List[DataQualityAlert]:
        """
        Detect missing data records and gaps in historical data
        
        Args:
            lookback_days: Number of days to check for data completeness
            
        Returns:
            List of data gap alerts
        """
        alerts = []
        
        conn = self.get_database_connection()
        if not conn:
            return alerts
            
        try:
            cursor = conn.cursor()
            
            # Find symbols with missing recent data
            gap_query = """
            WITH active_symbols AS (
                SELECT DISTINCT symbol
                FROM symbols 
                WHERE active = true
                AND type IN ('CS', 'ETF')  -- Common stock and ETF
            ),
            recent_data AS (
                SELECT 
                    symbol,
                    MAX(date) as last_data_date,
                    COUNT(*) as record_count
                FROM historical_data 
                WHERE date >= %s
                GROUP BY symbol
            ),
            expected_days AS (
                SELECT COUNT(*) as trading_days
                FROM generate_series(%s::date, CURRENT_DATE, '1 day'::interval) as d
                WHERE EXTRACT(dow FROM d) BETWEEN 1 AND 5  -- Monday to Friday
            )
            SELECT 
                a.symbol,
                COALESCE(r.last_data_date, '1900-01-01'::date) as last_data_date,
                COALESCE(r.record_count, 0) as record_count,
                e.trading_days as expected_records,
                CURRENT_DATE - COALESCE(r.last_data_date, '1900-01-01'::date) as days_stale
            FROM active_symbols a
            LEFT JOIN recent_data r ON a.symbol = r.symbol
            CROSS JOIN expected_days e
            WHERE COALESCE(r.last_data_date, '1900-01-01'::date) < CURRENT_DATE - INTERVAL '2 days'
            OR COALESCE(r.record_count, 0) < e.trading_days * 0.8  -- Less than 80% expected records
            ORDER BY days_stale DESC, record_count ASC
            LIMIT 50;
            """
            
            cutoff_date = datetime.now().date() - timedelta(days=lookback_days)
            cursor.execute(gap_query, (cutoff_date, cutoff_date))
            
            data_gaps = cursor.fetchall()
            
            for gap in data_gaps:
                days_stale = int(gap['days_stale'])
                record_count = int(gap['record_count'])
                expected_records = int(gap['expected_records'])
                
                if days_stale >= 7:
                    severity = 'high'
                    description = f"Data stale for {days_stale} days"
                elif record_count < expected_records * 0.5:
                    severity = 'high'
                    description = f"Significant data gap: {record_count}/{expected_records} records"
                else:
                    severity = 'medium'
                    description = f"Missing recent data: {record_count}/{expected_records} records"
                
                alert = DataQualityAlert(
                    alert_type='data_gap',
                    symbol=gap['symbol'],
                    severity=severity,
                    description=description,
                    details={
                        'last_data_date': gap['last_data_date'].isoformat(),
                        'days_stale': days_stale,
                        'record_count': record_count,
                        'expected_records': expected_records,
                        'completeness_pct': (record_count / expected_records) * 100 if expected_records > 0 else 0
                    },
                    timestamp=datetime.now(),
                    remediation_suggestion=self._get_data_gap_remediation(days_stale)
                )
                
                alerts.append(alert)
                
        except Exception as e:
            self.logger.error(f"- Data gap detection failed: {e}")
        finally:
            if conn:
                conn.close()
        
        self.logger.info(f"+ Detected {len(alerts)} data gaps")
        return alerts
    
    async def publish_quality_alerts(self, alerts: List[DataQualityAlert]) -> bool:
        """
        Publish quality alerts to Redis for TickStockApp consumption
        
        Args:
            alerts: List of quality alerts to publish
            
        Returns:
            True if publishing succeeded, False otherwise
        """
        if not alerts:
            return True
            
        redis_client = await self.connect_redis()
        if not redis_client:
            self.logger.error("- Cannot publish alerts: Redis connection failed")
            return False
            
        try:
            for alert in alerts:
                # Determine appropriate channel
                if alert.alert_type in ['price_anomaly']:
                    channel = self.channels['price_anomaly']
                elif alert.alert_type in ['volume_spike', 'zero_volume', 'volume_drought']:
                    channel = self.channels['volume_anomaly']
                elif alert.alert_type in ['data_gap']:
                    channel = self.channels['data_gap']
                else:
                    channel = self.channels['quality_summary']
                
                # Create message payload
                message = {
                    'timestamp': alert.timestamp.isoformat(),
                    'service': 'data_quality_monitor',
                    'alert_type': alert.alert_type,
                    'symbol': alert.symbol,
                    'severity': alert.severity,
                    'description': alert.description,
                    'details': alert.details,
                    'remediation': alert.remediation_suggestion
                }
                
                # Publish to Redis
                await redis_client.publish(channel, json.dumps(message))
                
            self.logger.info(f"+ Published {len(alerts)} quality alerts to Redis")
            return True
            
        except Exception as e:
            self.logger.error(f"- Quality alert publishing failed: {e}")
            return False
        finally:
            if redis_client:
                await redis_client.aclose()
    
    def _classify_price_anomaly_severity(self, price_change_pct: float) -> str:
        """Classify price anomaly severity based on magnitude"""
        if price_change_pct >= 0.50:  # 50%+
            return 'critical'
        elif price_change_pct >= 0.35:  # 35-50%
            return 'high'
        elif price_change_pct >= 0.20:  # 20-35%
            return 'medium'
        else:
            return 'low'
    
    def _get_price_anomaly_remediation(self, price_change_pct: float) -> str:
        """Get remediation suggestion for price anomalies"""
        if price_change_pct >= 0.50:
            return "Verify data source accuracy, check for stock splits or corporate actions"
        elif price_change_pct >= 0.35:
            return "Review market news and validate against alternative data sources"
        else:
            return "Monitor for continued unusual activity, validate data quality"
    
    def _get_volume_anomaly_remediation(self, alert_type: str) -> str:
        """Get remediation suggestion for volume anomalies"""
        if alert_type == 'zero_volume':
            return "Check if symbol is actively trading, verify data source connectivity"
        elif alert_type == 'volume_spike':
            return "Investigate market news, earnings announcements, or unusual market activity"
        else:  # volume_drought
            return "Verify symbol trading status and data source reliability"
    
    def _get_data_gap_remediation(self, days_stale: int) -> str:
        """Get remediation suggestion for data gaps"""
        if days_stale >= 7:
            return "Immediate data source investigation required, trigger historical backfill"
        elif days_stale >= 3:
            return "Schedule data refresh, verify symbol trading status"
        else:
            return "Monitor for data source delays, schedule routine backfill"
    
    async def run_quality_scan(self, full_scan: bool = False) -> Dict[str, Any]:
        """
        Run comprehensive data quality scan
        
        Args:
            full_scan: If True, run extended analysis with longer lookback periods
            
        Returns:
            Quality scan summary with alert counts and metrics
        """
        self.logger.info("=== Starting Data Quality Scan ===")
        
        # Configure scan parameters based on scan type
        if full_scan:
            price_lookback = 7
            volume_lookback = 14
            gap_lookback = 60
        else:
            price_lookback = 3
            volume_lookback = 7
            gap_lookback = 30
        
        # Run all quality checks
        price_alerts = await self.detect_price_anomalies(price_lookback)
        volume_alerts = await self.detect_volume_anomalies(volume_lookback)
        gap_alerts = await self.detect_data_gaps(gap_lookback)
        
        all_alerts = price_alerts + volume_alerts + gap_alerts
        
        # Publish alerts to Redis
        publish_success = await self.publish_quality_alerts(all_alerts)
        
        # Create summary
        summary = {
            'scan_timestamp': datetime.now().isoformat(),
            'scan_type': 'full' if full_scan else 'standard',
            'alerts_detected': len(all_alerts),
            'alerts_by_type': {
                'price_anomalies': len(price_alerts),
                'volume_anomalies': len(volume_alerts),
                'data_gaps': len(gap_alerts)
            },
            'alerts_by_severity': {
                severity: len([a for a in all_alerts if a.severity == severity])
                for severity in ['low', 'medium', 'high', 'critical']
            },
            'redis_publishing': 'success' if publish_success else 'failed'
        }
        
        # Log summary
        self.logger.info(f"+ Quality Scan Complete:")
        self.logger.info(f"  - Total Alerts: {summary['alerts_detected']}")
        self.logger.info(f"  - Price Anomalies: {summary['alerts_by_type']['price_anomalies']}")
        self.logger.info(f"  - Volume Anomalies: {summary['alerts_by_type']['volume_anomalies']}")
        self.logger.info(f"  - Data Gaps: {summary['alerts_by_type']['data_gaps']}")
        self.logger.info(f"  - Redis Publishing: {summary['redis_publishing']}")
        
        return summary

async def main():
    """Main execution function for data quality monitoring"""
    monitor = DataQualityMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--full-scan':
            await monitor.run_quality_scan(full_scan=True)
        elif command == '--standard-scan':
            await monitor.run_quality_scan(full_scan=False)
        elif command == '--price-anomalies':
            alerts = await monitor.detect_price_anomalies()
            await monitor.publish_quality_alerts(alerts)
        elif command == '--volume-anomalies':
            alerts = await monitor.detect_volume_anomalies()
            await monitor.publish_quality_alerts(alerts)
        elif command == '--data-gaps':
            alerts = await monitor.detect_data_gaps()
            await monitor.publish_quality_alerts(alerts)
        else:
            print("Usage:")
            print("  --full-scan: Complete quality scan with extended lookback")
            print("  --standard-scan: Standard daily quality scan")
            print("  --price-anomalies: Check for price anomalies only")
            print("  --volume-anomalies: Check for volume anomalies only") 
            print("  --data-gaps: Check for data completeness only")
    else:
        # Default: run standard scan
        await monitor.run_quality_scan(full_scan=False)

if __name__ == '__main__':
    asyncio.run(main())