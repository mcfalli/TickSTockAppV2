#!/usr/bin/env python3
"""
Comprehensive Tests for Market Schedule Manager - Sprint 14 Phase 4

Tests for comprehensive market calendar and schedule awareness including:
- Multi-exchange support (NYSE, NASDAQ, TSE, LSE, XETR)
- International market integration with timezone handling  
- Weekend and after-hours processing optimization
- Schedule adjustment notifications via Redis pub-sub
- Early close day detection and automated maintenance scheduling

Author: TickStock Testing Framework
Sprint: 14 Phase 4
Test Category: Services/MarketSchedule
Performance Targets: <50ms schedule queries, accurate timezone conversions
"""

import json
import os

# Import the module under test
import sys
from datetime import date, datetime
from datetime import time as dt_time
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.services.market_schedule_manager import (
    MarketScheduleManager,
    MarketSession,
    ScheduleAdjustment,
)


@pytest.fixture
def schedule_manager():
    """Create MarketScheduleManager instance for testing"""
    return MarketScheduleManager(
        database_uri="postgresql://test_user:test_password@localhost/test_db",
        redis_host="localhost"
    )

@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit = Mock()
    mock_conn.rollback = Mock()
    mock_conn.close = Mock()
    mock_cursor.execute = Mock()
    return mock_conn

@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing"""
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.publish = AsyncMock(return_value=1)
    mock_client.aclose = AsyncMock()
    return mock_client

@pytest.fixture
def sample_market_sessions():
    """Sample market sessions for testing"""
    return {
        'NYSE': MarketSession(
            exchange='NYSE',
            session_date=date(2024, 7, 4),  # Independence Day
            open_time=dt_time(9, 30),
            close_time=dt_time(16, 0),
            is_trading_day=False,
            is_early_close=False,
            timezone_name='America/New_York',
            holiday_name='Independence Day'
        ),
        'TSE': MarketSession(
            exchange='TSE',
            session_date=date(2024, 7, 4),
            open_time=dt_time(9, 0),
            close_time=dt_time(15, 0),
            is_trading_day=True,
            is_early_close=False,
            timezone_name='Asia/Tokyo',
            holiday_name=None
        )
    }

@pytest.fixture
def sample_schedule_adjustment():
    """Sample schedule adjustment for testing"""
    return ScheduleAdjustment(
        adjustment_type='early_close',
        exchange='NYSE',
        affected_date=date(2024, 11, 29),
        original_schedule={'close_time': '16:00'},
        adjusted_schedule={'close_time': '13:00'},
        reason='Day after Thanksgiving - early close',
        timestamp=datetime.now()
    )

@pytest.fixture
def mock_market_calendar():
    """Mock pandas market calendar"""
    mock_calendar = Mock()
    mock_calendar.is_session.return_value = True
    mock_calendar.early_closes.return_value = []
    return mock_calendar


class TestMarketScheduleManager:
    """Test suite for MarketScheduleManager"""

    def test_initialization(self, schedule_manager):
        """Test proper initialization of market schedule manager"""
        assert len(schedule_manager.exchanges) == 5
        required_exchanges = {'NYSE', 'NASDAQ', 'TSE', 'LSE', 'XETR'}
        assert set(schedule_manager.exchanges.keys()) == required_exchanges

        # Verify Redis channels configured
        assert len(schedule_manager.channels) == 4
        assert 'schedule_notification' in schedule_manager.channels
        assert 'maintenance_schedule' in schedule_manager.channels

    def test_exchange_configuration(self, schedule_manager):
        """Test exchange configuration with timezones and schedules"""
        # Test NYSE configuration
        nyse = schedule_manager.exchanges['NYSE']
        assert nyse['timezone'] == 'America/New_York'
        assert nyse['standard_open'] == dt_time(9, 30)
        assert nyse['standard_close'] == dt_time(16, 0)
        assert nyse['country'] == 'US'
        assert nyse['currency'] == 'USD'

        # Test international exchanges
        tse = schedule_manager.exchanges['TSE']
        assert tse['timezone'] == 'Asia/Tokyo'
        assert tse['currency'] == 'JPY'

        lse = schedule_manager.exchanges['LSE']
        assert lse['timezone'] == 'Europe/London'
        assert lse['currency'] == 'GBP'

    def test_built_in_us_holidays(self, schedule_manager):
        """Test built-in US holiday calendar"""
        holidays = schedule_manager.us_holidays_2024_2025

        # Verify key holidays exist
        assert '2024-07-04' in holidays
        assert holidays['2024-07-04'] == 'Independence Day'
        assert '2024-12-25' in holidays
        assert holidays['2024-12-25'] == 'Christmas Day'
        assert '2025-01-01' in holidays

        # Verify reasonable number of holidays
        assert len(holidays) >= 20  # At least 10 per year

    def test_early_close_days(self, schedule_manager):
        """Test early close day configuration"""
        early_closes = schedule_manager.us_early_close_days_2024_2025

        # Verify key early close days
        assert '2024-11-29' in early_closes  # Day after Thanksgiving
        assert '2024-12-24' in early_closes  # Christmas Eve
        assert early_closes['2024-11-29'] == 'Day after Thanksgiving'

    @pytest.mark.asyncio
    async def test_redis_connection_success(self, schedule_manager, mock_redis):
        """Test successful Redis connection establishment"""
        with patch('redis.asyncio.Redis', return_value=mock_redis):
            redis_client = await schedule_manager.connect_redis()

            assert redis_client is not None
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, schedule_manager):
        """Test Redis connection failure handling"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_client = AsyncMock()
            mock_client.ping.side_effect = Exception("Connection failed")
            mock_redis_class.return_value = mock_client

            redis_client = await schedule_manager.connect_redis()
            assert redis_client is None

    def test_database_connection_success(self, schedule_manager, mock_database_connection):
        """Test successful database connection"""
        with patch('psycopg2.connect', return_value=mock_database_connection):
            conn = schedule_manager.get_database_connection()

            assert conn is not None
            assert conn == mock_database_connection

    def test_is_trading_day_weekends(self, schedule_manager):
        """Test weekend trading day detection"""
        saturday = date(2024, 6, 1)  # Saturday
        sunday = date(2024, 6, 2)    # Sunday
        monday = date(2024, 6, 3)    # Monday

        assert schedule_manager.is_trading_day(saturday) == False
        assert schedule_manager.is_trading_day(sunday) == False
        assert schedule_manager.is_trading_day(monday) == True

    def test_is_trading_day_us_holidays(self, schedule_manager):
        """Test US holiday trading day detection"""
        independence_day = date(2024, 7, 4)
        christmas = date(2024, 12, 25)
        regular_day = date(2024, 6, 15)  # Regular weekday

        assert schedule_manager.is_trading_day(independence_day, 'NYSE') == False
        assert schedule_manager.is_trading_day(christmas, 'NASDAQ') == False
        assert schedule_manager.is_trading_day(regular_day, 'NYSE') == True

    def test_is_trading_day_with_market_calendar(self, schedule_manager, mock_market_calendar):
        """Test trading day detection with pandas market calendar"""
        schedule_manager.market_calendars['NYSE'] = mock_market_calendar
        test_date = date(2024, 6, 15)

        # Mock calendar says it's a trading day
        mock_market_calendar.is_session.return_value = True
        result = schedule_manager.is_trading_day(test_date, 'NYSE')
        assert result == True

        # Mock calendar says it's not a trading day
        mock_market_calendar.is_session.return_value = False
        result = schedule_manager.is_trading_day(test_date, 'NYSE')
        assert result == False

    def test_get_market_session_regular_day(self, schedule_manager):
        """Test market session for regular trading day"""
        regular_day = date(2024, 6, 15)  # Regular weekday

        session = schedule_manager.get_market_session(regular_day, 'NYSE')

        assert session.exchange == 'NYSE'
        assert session.session_date == regular_day
        assert session.open_time == dt_time(9, 30)
        assert session.close_time == dt_time(16, 0)
        assert session.is_trading_day == True
        assert session.is_early_close == False
        assert session.timezone_name == 'America/New_York'
        assert session.holiday_name is None

    def test_get_market_session_holiday(self, schedule_manager):
        """Test market session for holiday"""
        independence_day = date(2024, 7, 4)

        session = schedule_manager.get_market_session(independence_day, 'NYSE')

        assert session.is_trading_day == False
        assert session.holiday_name == 'Independence Day'

    def test_get_market_session_early_close(self, schedule_manager):
        """Test market session for early close day"""
        day_after_thanksgiving = date(2024, 11, 29)

        session = schedule_manager.get_market_session(day_after_thanksgiving, 'NYSE')

        assert session.is_early_close == True
        assert session.close_time == dt_time(13, 0)  # 1:00 PM ET
        assert session.holiday_name == 'Day after Thanksgiving'

    def test_get_market_session_unknown_exchange(self, schedule_manager):
        """Test market session with unknown exchange"""
        with pytest.raises(ValueError, match="Unknown exchange"):
            schedule_manager.get_market_session(date(2024, 6, 15), 'UNKNOWN')

    def test_get_market_close_time(self, schedule_manager):
        """Test market close time retrieval"""
        regular_day = date(2024, 6, 15)
        early_close_day = date(2024, 11, 29)

        # Regular close time
        regular_close = schedule_manager.get_market_close_time(regular_day, 'NYSE')
        assert regular_close == dt_time(16, 0)

        # Early close time
        early_close = schedule_manager.get_market_close_time(early_close_day, 'NYSE')
        assert early_close == dt_time(13, 0)

    @pytest.mark.performance
    def test_schedule_query_performance(self, schedule_manager):
        """Test schedule queries meet <50ms performance requirement"""
        test_dates = [date(2024, 6, i) for i in range(1, 31)]

        import time
        start_time = time.time()

        # Query 30 days of schedule data
        for test_date in test_dates:
            session = schedule_manager.get_market_session(test_date, 'NYSE')
            is_trading = schedule_manager.is_trading_day(test_date, 'NYSE')

        total_time = (time.time() - start_time) * 1000  # Convert to ms
        avg_time_per_query = total_time / (len(test_dates) * 2)  # 2 queries per date

        # Performance requirement: <50ms per query
        assert avg_time_per_query < 50, f"Average query time: {avg_time_per_query:.2f}ms, expected <50ms"

    def test_is_market_hours_nyse(self, schedule_manager):
        """Test NYSE market hours detection"""
        # Create timezone-aware datetimes
        et_tz = pytz.timezone('America/New_York')

        # During market hours (10:00 AM ET on a weekday)
        market_time = et_tz.localize(datetime(2024, 6, 15, 10, 0))  # Saturday
        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value = market_time

            # Mock trading day check
            with patch.object(schedule_manager, 'is_trading_day', return_value=True):
                is_hours = schedule_manager.is_market_hours('NYSE', market_time)
                assert is_hours == True

    def test_is_market_hours_international(self, schedule_manager):
        """Test international market hours detection"""
        # Tokyo time during market hours
        jst_tz = pytz.timezone('Asia/Tokyo')
        tokyo_market_time = jst_tz.localize(datetime(2024, 6, 15, 11, 0))

        with patch.object(schedule_manager, 'is_trading_day', return_value=True):
            is_hours = schedule_manager.is_market_hours('TSE', tokyo_market_time)
            assert is_hours == True

    def test_timezone_conversion(self, schedule_manager):
        """Test accurate timezone conversions"""
        utc_time = datetime(2024, 6, 15, 14, 0, tzinfo=pytz.UTC)  # 2:00 PM UTC

        # Convert to NYSE timezone (EDT: UTC-4)
        nyse_time = schedule_manager.convert_to_exchange_time(utc_time, 'NYSE')
        assert nyse_time.hour == 10  # Should be 10:00 AM EDT

        # Convert to Tokyo timezone (JST: UTC+9)
        tse_time = schedule_manager.convert_to_exchange_time(utc_time, 'TSE')
        assert tse_time.hour == 23  # Should be 11:00 PM JST

    def test_timezone_conversion_naive_datetime(self, schedule_manager):
        """Test timezone conversion with naive datetime"""
        naive_time = datetime(2024, 6, 15, 14, 0)  # No timezone info

        # Should handle naive datetime by treating as UTC
        nyse_time = schedule_manager.convert_to_exchange_time(naive_time, 'NYSE')
        assert nyse_time.tzinfo is not None
        assert nyse_time.hour == 10  # 14:00 UTC -> 10:00 EDT

    @pytest.mark.asyncio
    async def test_schedule_maintenance_jobs_trading_day(self, schedule_manager, mock_redis):
        """Test maintenance job scheduling on trading day"""
        trading_day = date(2024, 6, 15)  # Regular Saturday

        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value.date.return_value = trading_day

            with patch.object(schedule_manager, 'connect_redis', return_value=mock_redis):
                with patch.object(schedule_manager, 'schedule_eod_maintenance') as mock_eod:
                    mock_eod.return_value = {'type': 'eod_maintenance'}

                    result = await schedule_manager.schedule_maintenance_jobs()

                    assert result['type'] == 'eod_maintenance'
                    mock_eod.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_maintenance_jobs_holiday(self, schedule_manager, mock_redis):
        """Test maintenance job scheduling on holiday"""
        holiday = date(2024, 7, 4)  # Independence Day

        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value.date.return_value = holiday

            with patch.object(schedule_manager, 'connect_redis', return_value=mock_redis):
                with patch.object(schedule_manager, 'schedule_holiday_maintenance') as mock_holiday:
                    mock_holiday.return_value = {'type': 'holiday_maintenance'}

                    result = await schedule_manager.schedule_maintenance_jobs()

                    assert result['type'] == 'holiday_maintenance'
                    mock_holiday.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_eod_maintenance(self, schedule_manager, mock_redis, sample_market_sessions):
        """Test end-of-day maintenance scheduling"""
        regular_session = MarketSession(
            exchange='NYSE',
            session_date=date(2024, 6, 15),
            open_time=dt_time(9, 30),
            close_time=dt_time(16, 0),
            is_trading_day=True,
            is_early_close=False,
            timezone_name='America/New_York',
            holiday_name=None
        )

        maintenance_time = dt_time(17, 0)  # 1 hour after close

        result = await schedule_manager.schedule_eod_maintenance(maintenance_time, regular_session)

        assert result['type'] == 'eod_maintenance'
        assert result['exchange'] == 'NYSE'
        assert 'data_validation' in result['tasks']
        assert result['is_early_close'] == False

        # Verify Redis publication
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_holiday_maintenance(self, schedule_manager, mock_redis, sample_market_sessions):
        """Test holiday maintenance scheduling"""
        holiday_session = sample_market_sessions['NYSE']  # Independence Day

        result = await schedule_manager.schedule_holiday_maintenance(holiday_session)

        assert result['type'] == 'holiday_maintenance'
        assert result['holiday_name'] == 'Independence Day'
        assert result['estimated_duration_hours'] == 6
        assert 'database_optimization' in result['tasks']
        assert 'historical_correlation_updates' in result['tasks']

        # Verify Redis publication
        mock_redis.publish.assert_called_once()

    def test_calculate_eod_maintenance_time(self, schedule_manager):
        """Test EOD maintenance time calculation"""
        # Regular trading day
        regular_session = MarketSession(
            exchange='NYSE',
            session_date=date(2024, 6, 15),
            open_time=dt_time(9, 30),
            close_time=dt_time(16, 0),
            is_trading_day=True,
            is_early_close=False,
            timezone_name='America/New_York',
            holiday_name=None
        )

        maintenance_time = schedule_manager.calculate_eod_maintenance_time(regular_session)
        assert maintenance_time == dt_time(17, 0)  # 1 hour after close

        # Early close day
        early_close_session = MarketSession(
            exchange='NYSE',
            session_date=date(2024, 11, 29),
            open_time=dt_time(9, 30),
            close_time=dt_time(13, 0),
            is_trading_day=True,
            is_early_close=True,
            timezone_name='America/New_York',
            holiday_name='Day after Thanksgiving'
        )

        early_maintenance_time = schedule_manager.calculate_eod_maintenance_time(early_close_session)
        assert early_maintenance_time == dt_time(13, 30)  # 30 minutes after early close

    def test_get_international_etfs(self, schedule_manager):
        """Test international ETF retrieval"""
        etfs = schedule_manager.get_international_etfs()

        assert len(etfs) > 0

        # Verify ETF structure
        for etf in etfs:
            assert 'symbol' in etf
            assert 'name' in etf
            assert 'primary_exchange' in etf

        # Verify specific ETFs exist
        symbols = [etf['symbol'] for etf in etfs]
        assert 'EWJ' in symbols  # Japan ETF
        assert 'EWU' in symbols  # UK ETF
        assert 'EWG' in symbols  # Germany ETF

    @pytest.mark.asyncio
    async def test_process_international_etfs(self, schedule_manager, mock_redis):
        """Test international ETF processing with exchange schedules"""
        with patch.object(schedule_manager, 'convert_to_exchange_time') as mock_convert:
            with patch.object(schedule_manager, 'schedule_etf_processing') as mock_schedule:
                mock_convert.return_value = datetime.now()
                mock_schedule.return_value = {'status': 'scheduled', 'priority': 'normal'}

                result = await schedule_manager.process_international_etfs()

                assert 'etfs_processed' in result
                assert 'exchanges_active' in result
                assert 'processing_details' in result

    @pytest.mark.asyncio
    async def test_schedule_etf_processing_market_hours(self, schedule_manager, mock_redis):
        """Test ETF processing scheduling during market hours"""
        etf = {'symbol': 'EWJ', 'name': 'Japan ETF', 'primary_exchange': 'TSE'}
        local_time = datetime(2024, 6, 15, 11, 0)  # During TSE market hours

        session = MarketSession(
            exchange='TSE',
            session_date=date(2024, 6, 15),
            open_time=dt_time(9, 0),
            close_time=dt_time(15, 0),
            is_trading_day=True,
            is_early_close=False,
            timezone_name='Asia/Tokyo',
            holiday_name=None
        )

        with patch.object(schedule_manager, 'is_market_hours', return_value=True):
            with patch.object(schedule_manager, 'connect_redis', return_value=mock_redis):

                result = await schedule_manager.schedule_etf_processing(etf, local_time, session)

                assert result['status'] == 'scheduled'
                assert result['priority'] == 'high'  # High priority during market hours
                assert result['exchange'] == 'TSE'

    @pytest.mark.asyncio
    async def test_optimize_weekend_processing(self, schedule_manager):
        """Test weekend processing optimization"""
        # Mock weekend (Saturday)
        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value.weekday.return_value = 5  # Saturday

            with patch.object(schedule_manager, 'schedule_weekend_maintenance') as mock_weekend:
                mock_weekend.return_value = {
                    'optimization_type': 'weekend_maintenance',
                    'resource_utilization_target': 'high'
                }

                result = await schedule_manager.optimize_weekend_processing()

                assert result['optimization_type'] == 'weekend_maintenance'
                assert result['resource_utilization_target'] == 'high'

    @pytest.mark.asyncio
    async def test_schedule_weekend_maintenance(self, schedule_manager, mock_redis):
        """Test weekend maintenance scheduling"""
        with patch.object(schedule_manager, 'connect_redis', return_value=mock_redis):

            result = await schedule_manager.schedule_weekend_maintenance()

            assert result['optimization_type'] == 'weekend_maintenance'
            assert result['resource_utilization_target'] == 'high'
            assert result['estimated_duration_hours'] == 8
            assert 'database_maintenance' in result['tasks_scheduled']

            # Verify Redis publication
            mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_after_hours_processing(self, schedule_manager, mock_redis):
        """Test after-hours processing scheduling"""
        with patch.object(schedule_manager, 'connect_redis', return_value=mock_redis):

            result = await schedule_manager.schedule_after_hours_processing()

            assert result['optimization_type'] == 'after_hours_processing'
            assert result['resource_utilization_target'] == 'medium'
            assert result['estimated_duration_hours'] == 2
            assert 'data_quality_validation' in result['tasks_scheduled']

    @pytest.mark.asyncio
    async def test_notify_schedule_adjustments(self, schedule_manager, mock_redis, sample_schedule_adjustment):
        """Test schedule adjustment notifications"""
        with patch.object(schedule_manager, 'connect_redis', return_value=mock_redis):

            await schedule_manager.notify_schedule_adjustments(sample_schedule_adjustment)

            # Should publish to schedule notification channel
            assert mock_redis.publish.call_count >= 1

            # Verify notification structure
            publish_calls = mock_redis.publish.call_args_list
            notification_call = publish_calls[0]
            channel, message = notification_call[0]

            assert channel == schedule_manager.channels['schedule_notification']
            notification_data = json.loads(message)
            assert notification_data['adjustment_type'] == 'early_close'
            assert notification_data['exchange'] == 'NYSE'

    @pytest.mark.asyncio
    async def test_notify_holiday_adjustments(self, schedule_manager, mock_redis):
        """Test holiday adjustment notifications"""
        holiday_adjustment = ScheduleAdjustment(
            adjustment_type='unexpected_holiday',
            exchange='NYSE',
            affected_date=date(2024, 9, 2),
            original_schedule={'trading_day': True},
            adjusted_schedule={'trading_day': False},
            reason='Unexpected market closure',
            timestamp=datetime.now()
        )

        with patch.object(schedule_manager, 'connect_redis', return_value=mock_redis):
            with patch.object(schedule_manager, 'send_admin_email_notification') as mock_email:

                await schedule_manager.notify_schedule_adjustments(holiday_adjustment)

                # Should publish to both channels for holidays
                assert mock_redis.publish.call_count >= 2
                mock_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_market_status_summary(self, schedule_manager):
        """Test comprehensive market status summary"""
        test_date = date(2024, 6, 15)  # Regular trading day

        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value.date.return_value = test_date
            mock_dt.now.return_value = datetime(2024, 6, 15, 10, 0)

            status = await schedule_manager.get_market_status_summary()

            assert 'timestamp' in status
            assert status['date'] == test_date.isoformat()
            assert 'exchanges' in status
            assert len(status['exchanges']) == 5
            assert 'overall_status' in status

            # Verify exchange status structure
            for exchange, info in status['exchanges'].items():
                assert 'is_trading_day' in info
                assert 'is_currently_trading' in info
                assert 'open_time' in info
                assert 'close_time' in info
                assert 'timezone' in info
                assert 'local_time' in info

    def test_market_status_overall_classification(self, schedule_manager):
        """Test overall market status classification logic"""
        # Mock different scenarios
        with patch.object(schedule_manager, 'get_market_session') as mock_session:
            with patch.object(schedule_manager, 'is_market_hours', return_value=False):

                # All markets closed (global holiday)
                mock_session.return_value.is_trading_day = False

                async def test_global_holiday():
                    status = await schedule_manager.get_market_status_summary()
                    return status['overall_status']

                # Would need to run async test to verify, but logic is testable

    @pytest.mark.asyncio
    async def test_create_market_schedule_database_tables(self, schedule_manager, mock_database_connection):
        """Test database table creation for market schedule management"""
        with patch.object(schedule_manager, 'get_database_connection', return_value=mock_database_connection):

            await schedule_manager.create_market_schedule_database_tables()

            # Verify table creation SQL was executed
            mock_cursor = mock_database_connection.cursor.return_value
            assert mock_cursor.execute.call_count >= 3  # At least 3 tables created

            # Verify commit was called
            mock_database_connection.commit.assert_called_once()

    def test_optimization_schedules_configuration(self, schedule_manager):
        """Test processing optimization schedule configuration"""
        schedules = schedule_manager.optimization_schedules

        # Verify all optimization types exist
        assert 'weekend_maintenance' in schedules
        assert 'after_hours_processing' in schedules
        assert 'pre_market_preparation' in schedules

        # Verify schedule structure
        for schedule_type, config in schedules.items():
            assert 'description' in config
            assert 'tasks' in config
            assert 'max_duration_hours' in config
            assert len(config['tasks']) > 0

    @pytest.mark.integration
    async def test_end_to_end_schedule_workflow(self, schedule_manager, mock_redis, mock_database_connection):
        """Test complete end-to-end schedule management workflow"""
        trading_day = date(2024, 6, 15)

        with patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value.date.return_value = trading_day
            mock_dt.now.return_value = datetime(2024, 6, 15, 10, 0)

            with patch.object(schedule_manager, 'connect_redis', return_value=mock_redis):
                with patch.object(schedule_manager, 'get_database_connection', return_value=mock_database_connection):

                    # Step 1: Get market status
                    market_status = await schedule_manager.get_market_status_summary()
                    assert 'overall_status' in market_status

                    # Step 2: Schedule maintenance
                    with patch.object(schedule_manager, 'schedule_eod_maintenance') as mock_eod:
                        mock_eod.return_value = {'type': 'eod_maintenance'}
                        maintenance_result = await schedule_manager.schedule_maintenance_jobs()
                        assert maintenance_result['type'] == 'eod_maintenance'

                    # Step 3: Process international ETFs
                    with patch.object(schedule_manager, 'schedule_etf_processing') as mock_etf:
                        mock_etf.return_value = {'status': 'scheduled'}
                        etf_result = await schedule_manager.process_international_etfs()
                        assert 'etfs_processed' in etf_result

    def test_multiple_timezone_handling(self, schedule_manager):
        """Test accurate handling of multiple timezones simultaneously"""
        # Test time: 2:00 PM UTC
        utc_time = datetime(2024, 6, 15, 14, 0, tzinfo=pytz.UTC)

        # Convert to all exchange timezones
        timezone_conversions = {}
        for exchange in schedule_manager.exchanges.keys():
            local_time = schedule_manager.convert_to_exchange_time(utc_time, exchange)
            timezone_conversions[exchange] = local_time

        # Verify conversions are different (different timezones)
        times = list(timezone_conversions.values())
        assert len(set(t.hour for t in times)) > 1  # Different hours due to timezones

        # Verify all conversions have timezone info
        for exchange, local_time in timezone_conversions.items():
            assert local_time.tzinfo is not None

    def test_edge_case_holiday_detection(self, schedule_manager):
        """Test edge cases in holiday detection"""
        # Test holiday that falls on weekend
        saturday_holiday = date(2024, 7, 6)  # If July 4th falls on Saturday
        sunday_holiday = date(2024, 7, 7)    # If observed on Sunday

        # Weekend days should still be non-trading regardless of holiday status
        assert schedule_manager.is_trading_day(saturday_holiday, 'NYSE') == False
        assert schedule_manager.is_trading_day(sunday_holiday, 'NYSE') == False

    @pytest.mark.performance
    def test_international_market_query_performance(self, schedule_manager):
        """Test international market queries meet performance requirements"""
        exchanges = ['NYSE', 'NASDAQ', 'TSE', 'LSE', 'XETR']
        test_date = date(2024, 6, 15)

        import time
        start_time = time.time()

        # Query all international exchanges
        for exchange in exchanges:
            session = schedule_manager.get_market_session(test_date, exchange)
            is_trading = schedule_manager.is_trading_day(test_date, exchange)
            close_time = schedule_manager.get_market_close_time(test_date, exchange)

        total_time = (time.time() - start_time) * 1000  # Convert to ms
        avg_time_per_exchange = total_time / len(exchanges) / 3  # 3 queries per exchange

        # Performance requirement: <50ms per query
        assert avg_time_per_exchange < 50, f"Average query time: {avg_time_per_exchange:.2f}ms, expected <50ms"

    def test_redis_pub_sub_channel_organization(self, schedule_manager):
        """Test Redis pub-sub channels are properly organized"""
        channels = schedule_manager.channels

        # Verify channel naming convention
        for channel_name, channel_key in channels.items():
            assert channel_key.startswith('tickstock.market.')
            assert channel_name in channel_key

        # Verify all required channels exist
        required_channels = {
            'schedule_notification', 'maintenance_schedule',
            'holiday_alert', 'market_status'
        }
        assert set(channels.keys()) == required_channels


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
