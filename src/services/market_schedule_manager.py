#!/usr/bin/env python3
"""
Market Schedule Manager - Sprint 14 Phase 4

This service provides comprehensive market calendar and schedule awareness:
- Market calendar system with multiple exchange support (NYSE, NASDAQ, TSE, LSE, XETR)
- International market integration with primary exchange processing
- Weekend and after-hours processing optimization
- Schedule adjustment notifications via Redis pub-sub
- Early close day detection and automated maintenance scheduling

Architecture:
- Integrates with existing EOD processor and automation services
- Uses Redis pub-sub for schedule notifications and maintenance coordination
- Provides timezone-aware international market support
- Optimizes resource utilization during non-trading periods
- Maintains database of market schedules and holiday calendars
"""

import os
import sys
import asyncio
import json
import logging
import redis.asyncio as redis
from datetime import datetime, timedelta, time as dt_time, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import pytz
import psycopg2
import psycopg2.extras

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

try:
    import pandas_market_calendars as mcal
    import pandas as pd
    MARKET_CALENDARS_AVAILABLE = True
except ImportError:
    MARKET_CALENDARS_AVAILABLE = False
    print("+ Market calendars not available - using built-in holiday logic")

@dataclass
class MarketSession:
    """Market session information"""
    exchange: str
    session_date: datetime.date
    open_time: dt_time
    close_time: dt_time
    is_trading_day: bool
    is_early_close: bool
    timezone_name: str
    holiday_name: Optional[str] = None

@dataclass
class ScheduleAdjustment:
    """Schedule adjustment notification"""
    adjustment_type: str  # early_close, holiday, schedule_change
    exchange: str
    affected_date: datetime.date
    original_schedule: Dict[str, Any]
    adjusted_schedule: Dict[str, Any]
    reason: str
    timestamp: datetime

class MarketScheduleManager:
    """
    Market Schedule Manager
    
    Provides comprehensive market schedule awareness with:
    - Multi-exchange support (NYSE, NASDAQ, TSE, LSE, XETR)
    - Holiday calendar integration and early close detection
    - International market timezone coordination
    - Weekend and after-hours processing optimization
    - Automated schedule adjustment notifications
    - Integration with existing EOD and maintenance systems
    """
    
    def __init__(self, database_uri: str = None, redis_host: str = None):
        """Initialize market schedule manager"""
        self.database_uri = database_uri or os.getenv(
            'DATABASE_URL',
            'postgresql://app_readwrite:4pp_U$3r_2024!@localhost/tickstock'
        )
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        
        # Exchange configuration with timezones
        self.exchanges = {
            'NYSE': {
                'name': 'New York Stock Exchange',
                'timezone': 'America/New_York',
                'standard_open': dt_time(9, 30),
                'standard_close': dt_time(16, 0),
                'country': 'US',
                'currency': 'USD'
            },
            'NASDAQ': {
                'name': 'NASDAQ Stock Market',
                'timezone': 'America/New_York',
                'standard_open': dt_time(9, 30),
                'standard_close': dt_time(16, 0),
                'country': 'US',
                'currency': 'USD'
            },
            'TSE': {
                'name': 'Tokyo Stock Exchange',
                'timezone': 'Asia/Tokyo',
                'standard_open': dt_time(9, 0),
                'standard_close': dt_time(15, 0),
                'country': 'JP',
                'currency': 'JPY'
            },
            'LSE': {
                'name': 'London Stock Exchange',
                'timezone': 'Europe/London',
                'standard_open': dt_time(8, 0),
                'standard_close': dt_time(16, 30),
                'country': 'GB',
                'currency': 'GBP'
            },
            'XETR': {
                'name': 'Frankfurt Stock Exchange',
                'timezone': 'Europe/Berlin',
                'standard_open': dt_time(9, 0),
                'standard_close': dt_time(17, 30),
                'country': 'DE',
                'currency': 'EUR'
            }
        }
        
        # Initialize market calendars if available
        self.market_calendars = {}
        if MARKET_CALENDARS_AVAILABLE:
            try:
                for exchange in self.exchanges.keys():
                    if exchange in ['NYSE', 'NASDAQ', 'TSE', 'LSE']:
                        self.market_calendars[exchange] = mcal.get_calendar(exchange)
            except Exception as e:
                self.logger.warning(f"- Some market calendars unavailable: {e}")
        
        # Built-in US holidays for fallback
        self.us_holidays_2024_2025 = {
            '2024-01-01': 'New Year\'s Day',
            '2024-01-15': 'Martin Luther King Jr. Day',
            '2024-02-19': 'Presidents\' Day',
            '2024-03-29': 'Good Friday',
            '2024-05-27': 'Memorial Day',
            '2024-06-19': 'Juneteenth',
            '2024-07-04': 'Independence Day',
            '2024-09-02': 'Labor Day',
            '2024-11-28': 'Thanksgiving',
            '2024-11-29': 'Day after Thanksgiving',
            '2024-12-25': 'Christmas Day',
            '2025-01-01': 'New Year\'s Day',
            '2025-01-20': 'Martin Luther King Jr. Day',
            '2025-02-17': 'Presidents\' Day',
            '2025-04-18': 'Good Friday',
            '2025-05-26': 'Memorial Day',
            '2025-06-19': 'Juneteenth',
            '2025-07-04': 'Independence Day',
            '2025-09-01': 'Labor Day',
            '2025-11-27': 'Thanksgiving',
            '2025-11-28': 'Day after Thanksgiving',
            '2025-12-25': 'Christmas Day'
        }
        
        # Early close days (1:00 PM ET)
        self.us_early_close_days_2024_2025 = {
            '2024-07-03': 'Day before Independence Day',
            '2024-11-29': 'Day after Thanksgiving',
            '2024-12-24': 'Christmas Eve',
            '2025-07-03': 'Day before Independence Day',
            '2025-11-28': 'Day after Thanksgiving',
            '2025-12-24': 'Christmas Eve'
        }
        
        # Redis channels for schedule notifications
        self.channels = {
            'schedule_notification': 'tickstock.market.schedule_notification',
            'maintenance_schedule': 'tickstock.market.maintenance_schedule',
            'holiday_alert': 'tickstock.market.holiday_alert',
            'market_status': 'tickstock.market.status_update'
        }
        
        # Processing optimization schedules
        self.optimization_schedules = {
            'weekend_maintenance': {
                'description': 'Intensive maintenance during weekends',
                'tasks': ['database_maintenance', 'correlation_updates', 'cache_rebalancing'],
                'max_duration_hours': 8
            },
            'after_hours_processing': {
                'description': 'Light processing after market close',
                'tasks': ['data_quality_validation', 'universe_updates'],
                'max_duration_hours': 2
            },
            'pre_market_preparation': {
                'description': 'Market preparation before opening',
                'tasks': ['system_health_check', 'cache_warming'],
                'max_duration_hours': 1
            }
        }
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
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
    
    async def connect_redis(self) -> Optional[redis.Redis]:
        """Establish Redis connection for schedule notifications"""
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
    
    def is_trading_day(self, date: datetime.date, exchange: str = 'NYSE') -> bool:
        """
        Check if given date is a trading day for specified exchange
        
        Args:
            date: Date to check
            exchange: Exchange to check (default: NYSE)
            
        Returns:
            True if trading day, False if holiday/weekend
        """
        # Check weekend
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check with market calendar if available
        if exchange in self.market_calendars:
            try:
                calendar = self.market_calendars[exchange]
                return calendar.is_session(pd.Timestamp(date))
            except Exception as e:
                self.logger.warning(f"- Market calendar check failed: {e}")
        
        # Fallback to built-in US holidays for US exchanges
        if exchange in ['NYSE', 'NASDAQ']:
            date_str = date.isoformat()
            if date_str in self.us_holidays_2024_2025:
                return False
        
        # International markets - basic weekend check
        # In production, this would integrate with proper international holiday calendars
        return True
    
    def get_market_session(self, date: datetime.date, exchange: str = 'NYSE') -> MarketSession:
        """
        Get detailed market session information for a date and exchange
        
        Args:
            date: Date to get session info for
            exchange: Exchange to check
            
        Returns:
            MarketSession with detailed schedule information
        """
        if exchange not in self.exchanges:
            raise ValueError(f"Unknown exchange: {exchange}")
        
        exchange_info = self.exchanges[exchange]
        date_str = date.isoformat()
        
        # Check if trading day
        is_trading = self.is_trading_day(date, exchange)
        
        # Check for early close
        is_early_close = False
        close_time = exchange_info['standard_close']
        holiday_name = None
        
        if exchange in ['NYSE', 'NASDAQ']:
            if date_str in self.us_early_close_days_2024_2025:
                is_early_close = True
                close_time = dt_time(13, 0)  # 1:00 PM ET
                holiday_name = self.us_early_close_days_2024_2025[date_str]
            elif date_str in self.us_holidays_2024_2025:
                holiday_name = self.us_holidays_2024_2025[date_str]
        
        # Use market calendar for more precise information if available
        if exchange in self.market_calendars:
            try:
                calendar = self.market_calendars[exchange]
                pd_date = pd.Timestamp(date)
                
                if calendar.is_session(pd_date):
                    # Check for early closes
                    early_closes = calendar.early_closes(pd_date, pd_date)
                    if len(early_closes) > 0:
                        is_early_close = True
                        close_time = early_closes[0].time()
            except Exception as e:
                self.logger.warning(f"- Detailed session check failed: {e}")
        
        return MarketSession(
            exchange=exchange,
            session_date=date,
            open_time=exchange_info['standard_open'],
            close_time=close_time,
            is_trading_day=is_trading,
            is_early_close=is_early_close,
            timezone_name=exchange_info['timezone'],
            holiday_name=holiday_name
        )
    
    def get_market_close_time(self, date: datetime.date, exchange: str = 'NYSE') -> dt_time:
        """Get market close time, handling early close days"""
        session = self.get_market_session(date, exchange)
        return session.close_time
    
    def is_market_hours(self, exchange: str = 'NYSE', current_time: datetime = None) -> bool:
        """Check if currently in trading hours for specified exchange"""
        if current_time is None:
            current_time = datetime.now()
        
        if exchange not in self.exchanges:
            return False
        
        exchange_info = self.exchanges[exchange]
        
        # Convert to exchange timezone
        exchange_tz = pytz.timezone(exchange_info['timezone'])
        local_time = current_time.astimezone(exchange_tz)
        
        # Check if trading day
        if not self.is_trading_day(local_time.date(), exchange):
            return False
        
        # Get session information
        session = self.get_market_session(local_time.date(), exchange)
        
        # Check if within trading hours
        current_time_only = local_time.time()
        return session.open_time <= current_time_only <= session.close_time
    
    async def schedule_maintenance_jobs(self) -> Dict[str, Any]:
        """Schedule maintenance jobs with market calendar awareness"""
        today = datetime.now().date()
        
        self.logger.info("+ Scheduling maintenance jobs with market awareness")
        
        # Check primary market (NYSE) trading status
        nyse_session = self.get_market_session(today, 'NYSE')
        
        if not nyse_session.is_trading_day:
            self.logger.info(f"+ NYSE holiday ({nyse_session.holiday_name}) - running intensive maintenance")
            return await self.schedule_holiday_maintenance(nyse_session)
        
        # Regular trading day - schedule standard EOD maintenance
        maintenance_time = self.calculate_eod_maintenance_time(nyse_session)
        
        return await self.schedule_eod_maintenance(maintenance_time, nyse_session)
    
    async def schedule_eod_maintenance(self, maintenance_time: dt_time, session: MarketSession) -> Dict[str, Any]:
        """Schedule end-of-day maintenance after market close"""
        redis_client = await self.connect_redis()
        
        maintenance_schedule = {
            'type': 'eod_maintenance',
            'exchange': session.exchange,
            'trading_date': session.session_date.isoformat(),
            'market_close': session.close_time.isoformat(),
            'maintenance_start': maintenance_time.isoformat(),
            'is_early_close': session.is_early_close,
            'tasks': [
                'data_validation',
                'cache_synchronization',
                'universe_updates',
                'performance_metrics'
            ]
        }
        
        if redis_client:
            await redis_client.publish(
                self.channels['maintenance_schedule'],
                json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'schedule': maintenance_schedule
                })
            )
            await redis_client.aclose()
        
        self.logger.info(f"+ EOD maintenance scheduled for {maintenance_time} after {session.close_time} market close")
        
        return maintenance_schedule
    
    async def schedule_holiday_maintenance(self, session: MarketSession) -> Dict[str, Any]:
        """Schedule intensive maintenance during market holidays"""
        redis_client = await self.connect_redis()
        
        holiday_maintenance = {
            'type': 'holiday_maintenance',
            'exchange': session.exchange,
            'holiday_date': session.session_date.isoformat(),
            'holiday_name': session.holiday_name,
            'maintenance_start': dt_time(10, 0).isoformat(),  # Start at 10 AM
            'estimated_duration_hours': 6,
            'tasks': [
                'database_optimization',
                'historical_correlation_updates',
                'universe_rebalancing',
                'system_health_checks',
                'backup_operations',
                'cache_rebuilding'
            ]
        }
        
        if redis_client:
            await redis_client.publish(
                self.channels['maintenance_schedule'],
                json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'schedule': holiday_maintenance
                })
            )
            await redis_client.aclose()
        
        self.logger.info(f"+ Holiday maintenance scheduled for {session.holiday_name}")
        
        return holiday_maintenance
    
    def calculate_eod_maintenance_time(self, session: MarketSession) -> dt_time:
        """Calculate optimal EOD maintenance start time"""
        if session.is_early_close:
            # Start maintenance 30 minutes after early close
            maintenance_start = (
                datetime.combine(datetime.min, session.close_time) + 
                timedelta(minutes=30)
            ).time()
        else:
            # Standard maintenance 1 hour after regular close
            maintenance_start = (
                datetime.combine(datetime.min, session.close_time) + 
                timedelta(hours=1)
            ).time()
        
        return maintenance_start
    
    async def process_international_etfs(self) -> Dict[str, Any]:
        """Process international ETFs according to their primary exchange schedules"""
        processing_results = {
            'etfs_processed': 0,
            'exchanges_active': [],
            'exchanges_holiday': [],
            'processing_details': {}
        }
        
        # Get international ETFs from database
        international_etfs = self.get_international_etfs()
        
        current_time = datetime.now()
        
        for etf in international_etfs:
            primary_exchange = etf.get('primary_exchange', 'NYSE')
            symbol = etf['symbol']
            
            # Get session information for primary exchange
            try:
                session = self.get_market_session(current_time.date(), primary_exchange)
                
                if session.is_trading_day:
                    # Process during their market session
                    local_time = self.convert_to_exchange_time(current_time, primary_exchange)
                    
                    processing_result = await self.schedule_etf_processing(etf, local_time, session)
                    processing_results['processing_details'][symbol] = processing_result
                    processing_results['etfs_processed'] += 1
                    
                    if primary_exchange not in processing_results['exchanges_active']:
                        processing_results['exchanges_active'].append(primary_exchange)
                else:
                    self.logger.info(f"+ Skipping {symbol} - {primary_exchange} holiday: {session.holiday_name}")
                    processing_results['processing_details'][symbol] = {
                        'status': 'skipped',
                        'reason': f'{primary_exchange} holiday: {session.holiday_name}'
                    }
                    
                    if primary_exchange not in processing_results['exchanges_holiday']:
                        processing_results['exchanges_holiday'].append(primary_exchange)
                        
            except Exception as e:
                self.logger.error(f"- Error processing ETF {symbol}: {e}")
                processing_results['processing_details'][symbol] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return processing_results
    
    def get_international_etfs(self) -> List[Dict[str, Any]]:
        """Get international ETFs with primary exchange information"""
        # This would query the database for international ETFs
        # For demonstration, returning mock data
        return [
            {'symbol': 'EWJ', 'name': 'Japan ETF', 'primary_exchange': 'TSE'},
            {'symbol': 'EWU', 'name': 'UK ETF', 'primary_exchange': 'LSE'},
            {'symbol': 'EWG', 'name': 'Germany ETF', 'primary_exchange': 'XETR'},
            {'symbol': 'VEA', 'name': 'Developed Markets ETF', 'primary_exchange': 'NYSE'},
            {'symbol': 'VWO', 'name': 'Emerging Markets ETF', 'primary_exchange': 'NYSE'}
        ]
    
    def convert_to_exchange_time(self, utc_time: datetime, exchange: str) -> datetime:
        """Convert UTC time to exchange local time"""
        if exchange not in self.exchanges:
            return utc_time
        
        exchange_tz = pytz.timezone(self.exchanges[exchange]['timezone'])
        
        # Ensure UTC timezone if not specified
        if utc_time.tzinfo is None:
            utc_time = pytz.utc.localize(utc_time)
        
        return utc_time.astimezone(exchange_tz)
    
    async def schedule_etf_processing(self, etf: Dict[str, Any], local_time: datetime, 
                                   session: MarketSession) -> Dict[str, Any]:
        """Schedule ETF processing based on local market conditions"""
        symbol = etf['symbol']
        exchange = session.exchange
        
        # Determine processing priority based on market hours
        if self.is_market_hours(exchange, local_time):
            priority = 'high'
            processing_delay = timedelta(minutes=15)  # Delay during market hours
        else:
            priority = 'normal'
            processing_delay = timedelta(minutes=5)   # Process quickly after hours
        
        processing_time = local_time + processing_delay
        
        # Publish processing schedule
        redis_client = await self.connect_redis()
        if redis_client:
            await redis_client.publish(
                self.channels['schedule_notification'],
                json.dumps({
                    'type': 'etf_processing',
                    'symbol': symbol,
                    'exchange': exchange,
                    'local_time': local_time.isoformat(),
                    'processing_time': processing_time.isoformat(),
                    'priority': priority,
                    'session_info': {
                        'is_trading_day': session.is_trading_day,
                        'is_early_close': session.is_early_close
                    }
                })
            )
            await redis_client.aclose()
        
        return {
            'status': 'scheduled',
            'processing_time': processing_time.isoformat(),
            'priority': priority,
            'exchange': exchange
        }
    
    async def optimize_weekend_processing(self) -> Dict[str, Any]:
        """Optimize processing for weekends and after-hours"""
        current_time = datetime.now()
        
        optimization_results = {
            'optimization_type': None,
            'tasks_scheduled': [],
            'estimated_duration_hours': 0,
            'resource_utilization_target': 'high'
        }
        
        if current_time.weekday() >= 5:  # Weekend
            optimization_results = await self.schedule_weekend_maintenance()
        elif not self.is_market_hours('NYSE') and not self.is_market_hours('NASDAQ'):
            optimization_results = await self.schedule_after_hours_processing()
        else:
            optimization_results['optimization_type'] = 'market_hours_active'
            optimization_results['resource_utilization_target'] = 'low'
        
        return optimization_results
    
    async def schedule_weekend_maintenance(self) -> Dict[str, Any]:
        """Schedule intensive maintenance tasks for weekends"""
        weekend_tasks = self.optimization_schedules['weekend_maintenance']
        
        maintenance_schedule = {
            'optimization_type': 'weekend_maintenance',
            'tasks_scheduled': weekend_tasks['tasks'],
            'estimated_duration_hours': weekend_tasks['max_duration_hours'],
            'resource_utilization_target': 'high',
            'start_time': datetime.now().replace(hour=2, minute=0).isoformat(),  # Start at 2 AM
            'tasks_detail': {
                'database_maintenance': 'VACUUM, REINDEX, statistics update',
                'correlation_updates': 'Update historical correlations for all symbols',
                'cache_rebalancing': 'Rebalance cache_entries and universe memberships'
            }
        }
        
        # Notify systems of weekend maintenance
        redis_client = await self.connect_redis()
        if redis_client:
            await redis_client.publish(
                self.channels['maintenance_schedule'],
                json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'schedule': maintenance_schedule
                })
            )
            await redis_client.aclose()
        
        self.logger.info("+ Weekend maintenance scheduled - intensive tasks")
        
        return maintenance_schedule
    
    async def schedule_after_hours_processing(self) -> Dict[str, Any]:
        """Schedule after-hours processing optimization"""
        after_hours_tasks = self.optimization_schedules['after_hours_processing']
        
        processing_schedule = {
            'optimization_type': 'after_hours_processing',
            'tasks_scheduled': after_hours_tasks['tasks'],
            'estimated_duration_hours': after_hours_tasks['max_duration_hours'],
            'resource_utilization_target': 'medium',
            'start_time': datetime.now().isoformat(),
            'tasks_detail': {
                'data_quality_validation': 'Validate today\'s data quality metrics',
                'universe_updates': 'Update universe memberships based on market cap changes'
            }
        }
        
        # Notify systems of after-hours processing
        redis_client = await self.connect_redis()
        if redis_client:
            await redis_client.publish(
                self.channels['schedule_notification'],
                json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'schedule': processing_schedule
                })
            )
            await redis_client.aclose()
        
        self.logger.info("+ After-hours processing scheduled - light tasks")
        
        return processing_schedule
    
    async def notify_schedule_adjustments(self, adjustment: ScheduleAdjustment):
        """Notify administrators of schedule adjustments"""
        redis_client = await self.connect_redis()
        
        notification = {
            'type': 'schedule_adjustment',
            'adjustment_type': adjustment.adjustment_type,
            'exchange': adjustment.exchange,
            'affected_date': adjustment.affected_date.isoformat(),
            'original_schedule': adjustment.original_schedule,
            'adjusted_schedule': adjustment.adjusted_schedule,
            'reason': adjustment.reason,
            'timestamp': adjustment.timestamp.isoformat(),
            'priority': 'high' if adjustment.adjustment_type in ['early_close', 'unexpected_holiday'] else 'medium'
        }
        
        if redis_client:
            # Publish to schedule notification channel
            await redis_client.publish(
                self.channels['schedule_notification'],
                json.dumps(notification)
            )
            
            # Also publish to holiday alert channel if it's a holiday
            if adjustment.adjustment_type in ['holiday', 'unexpected_holiday']:
                await redis_client.publish(
                    self.channels['holiday_alert'],
                    json.dumps(notification)
                )
            
            await redis_client.aclose()
        
        # Log critical adjustments
        if adjustment.adjustment_type in ['early_close', 'unexpected_holiday']:
            self.logger.warning(f"! Critical schedule adjustment: {adjustment.reason}")
        else:
            self.logger.info(f"+ Schedule adjustment: {adjustment.reason}")
        
        # Email notification would go here for critical adjustments
        if adjustment.adjustment_type == 'unexpected_holiday':
            self.send_admin_email_notification(notification)
    
    def send_admin_email_notification(self, notification: Dict[str, Any]):
        """Send email notification to administrators (placeholder)"""
        # This would integrate with email service
        self.logger.info(f"+ Email notification sent for critical adjustment: {notification['reason']}")
    
    async def get_market_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive market status summary for all exchanges"""
        current_time = datetime.now()
        today = current_time.date()
        
        status_summary = {
            'timestamp': current_time.isoformat(),
            'date': today.isoformat(),
            'exchanges': {},
            'overall_status': 'unknown'
        }
        
        trading_exchanges = 0
        total_exchanges = len(self.exchanges)
        
        for exchange in self.exchanges.keys():
            session = self.get_market_session(today, exchange)
            is_currently_trading = self.is_market_hours(exchange, current_time)
            
            exchange_status = {
                'is_trading_day': session.is_trading_day,
                'is_currently_trading': is_currently_trading,
                'open_time': session.open_time.isoformat(),
                'close_time': session.close_time.isoformat(),
                'is_early_close': session.is_early_close,
                'holiday_name': session.holiday_name,
                'timezone': self.exchanges[exchange]['timezone'],
                'local_time': self.convert_to_exchange_time(current_time, exchange).isoformat()
            }
            
            status_summary['exchanges'][exchange] = exchange_status
            
            if session.is_trading_day:
                trading_exchanges += 1
        
        # Determine overall market status
        if trading_exchanges == 0:
            status_summary['overall_status'] = 'global_holiday'
        elif trading_exchanges == total_exchanges:
            status_summary['overall_status'] = 'full_trading'
        else:
            status_summary['overall_status'] = 'partial_trading'
        
        return status_summary
    
    async def create_market_schedule_database_tables(self):
        """Create database tables for market schedule management"""
        conn = self.get_database_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Market calendars table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_calendars (
                    id SERIAL PRIMARY KEY,
                    exchange VARCHAR(10) NOT NULL,
                    calendar_date DATE NOT NULL,
                    is_trading_day BOOLEAN NOT NULL,
                    open_time TIME,
                    close_time TIME,
                    is_early_close BOOLEAN DEFAULT false,
                    holiday_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(exchange, calendar_date)
                )
            """)
            
            # Schedule adjustments log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedule_adjustments (
                    id SERIAL PRIMARY KEY,
                    adjustment_type VARCHAR(50) NOT NULL,
                    exchange VARCHAR(10) NOT NULL,
                    affected_date DATE NOT NULL,
                    original_schedule JSONB,
                    adjusted_schedule JSONB,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Market status log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_status_log (
                    id SERIAL PRIMARY KEY,
                    log_date DATE NOT NULL,
                    exchange VARCHAR(10) NOT NULL,
                    status JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_calendars_exchange_date ON market_calendars (exchange, calendar_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_adjustments_date ON schedule_adjustments (affected_date DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_status_date ON market_status_log (log_date DESC)")
            
            conn.commit()
            self.logger.info("+ Market schedule database tables created/verified")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"- Database table creation failed: {e}")
        finally:
            if conn:
                conn.close()

async def main():
    """Main execution function for market schedule management"""
    schedule_manager = MarketScheduleManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--schedule-maintenance':
            result = await schedule_manager.schedule_maintenance_jobs()
            print(f"Maintenance scheduling complete:")
            print(f"  Type: {result['type']}")
            if 'holiday_name' in result:
                print(f"  Holiday: {result['holiday_name']}")
            print(f"  Tasks: {len(result['tasks'])} scheduled")
            
        elif command == '--market-status':
            status = await schedule_manager.get_market_status_summary()
            print(f"Market Status Summary ({status['date']}):")
            print(f"  Overall Status: {status['overall_status']}")
            
            for exchange, info in status['exchanges'].items():
                trading_status = "TRADING" if info['is_currently_trading'] else "CLOSED"
                holiday_info = f" ({info['holiday_name']})" if info['holiday_name'] else ""
                print(f"  {exchange}: {trading_status}{holiday_info}")
                print(f"    Hours: {info['open_time']} - {info['close_time']}")
                
        elif command == '--process-international':
            result = await schedule_manager.process_international_etfs()
            print(f"International ETF processing:")
            print(f"  ETFs processed: {result['etfs_processed']}")
            print(f"  Active exchanges: {result['exchanges_active']}")
            print(f"  Holiday exchanges: {result['exchanges_holiday']}")
            
        elif command == '--weekend-optimization':
            result = await schedule_manager.optimize_weekend_processing()
            print(f"Weekend optimization:")
            print(f"  Type: {result['optimization_type']}")
            print(f"  Tasks: {len(result['tasks_scheduled'])}")
            print(f"  Duration: {result['estimated_duration_hours']} hours")
            
        elif command.startswith('--is-trading='):
            parts = command.split('=')[1].split(',')
            exchange = parts[0] if parts else 'NYSE'
            date_str = parts[1] if len(parts) > 1 else datetime.now().date().isoformat()
            
            date_obj = datetime.fromisoformat(date_str).date()
            is_trading = schedule_manager.is_trading_day(date_obj, exchange)
            
            print(f"Trading Day Check:")
            print(f"  Exchange: {exchange}")
            print(f"  Date: {date_obj}")
            print(f"  Is Trading Day: {is_trading}")
            
            session = schedule_manager.get_market_session(date_obj, exchange)
            if session.holiday_name:
                print(f"  Holiday: {session.holiday_name}")
            if session.is_early_close:
                print(f"  Early Close: {session.close_time}")
                
        elif command == '--create-tables':
            await schedule_manager.create_market_schedule_database_tables()
            print("Database tables created/verified for market schedule management")
            
        else:
            print("Usage:")
            print("  --schedule-maintenance: Schedule maintenance jobs based on market calendar")
            print("  --market-status: Show current market status for all exchanges")
            print("  --process-international: Process international ETFs based on exchange schedules")
            print("  --weekend-optimization: Optimize weekend processing")
            print("  --is-trading=<exchange>,<date>: Check if date is trading day")
            print("  --create-tables: Create market schedule database tables")
    else:
        # Default: show current market status
        status = await schedule_manager.get_market_status_summary()
        
        print("Market Schedule Manager")
        print(f"Date: {status['date']}")
        print(f"Overall Status: {status['overall_status']}")
        print(f"Market Calendars Available: {'Yes' if MARKET_CALENDARS_AVAILABLE else 'No (using built-in)'}")
        print()
        
        print("Exchange Status:")
        for exchange, info in status['exchanges'].items():
            status_text = "🟢 TRADING" if info['is_currently_trading'] else "🔴 CLOSED"
            holiday_text = f" 🎄 {info['holiday_name']}" if info['holiday_name'] else ""
            early_close_text = " ⏰ Early Close" if info['is_early_close'] else ""
            
            print(f"  {exchange}: {status_text}{holiday_text}{early_close_text}")

if __name__ == '__main__':
    asyncio.run(main())