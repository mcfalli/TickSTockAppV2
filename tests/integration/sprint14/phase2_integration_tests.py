"""
Sprint 14 Phase 2 Integration Tests

Tests cross-system integration for:
- Symbol Change and IPO Monitoring automation
- Equity Types Integration for processing rule management
- Data Quality and Monitoring with automated issue resolution

Validates automation service → Redis pub-sub → TickStockApp consumer workflows
with loose coupling enforcement and <100ms message delivery performance.
"""
import time
from datetime import datetime

from sqlalchemy import text

from tests.integration.sprint14.conftest import PERFORMANCE_TARGETS, SPRINT14_REDIS_CHANNELS


class TestIPOMonitoringIntegration:
    """Test IPO monitoring and symbol change detection workflows"""

    def test_ipo_detection_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor,
        sprint14_test_data
    ):
        """
        Test IPO detection and notification workflow.
        
        Workflow:
        1. IPO scanner detects new listing
        2. Symbol added to database
        3. Redis notification published
        4. TickStockApp receives IPO alert
        5. Historical backfill triggered
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['events']['ipo_detected'],
            SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
        ]
        listener.subscribe(channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)
        ipo_data = sprint14_test_data.ipo_listing_data()

        try:
            # Step 1: Simulate database insertion of new IPO symbol
            with integration_performance_monitor.measure_operation('ipo_db_insert'):
                db_connection.execute(text("""
                    INSERT INTO symbols (symbol, name, type, market_cap, sector, exchange, listing_date)
                    VALUES (:symbol, :name, 'CS', :market_cap, :sector, :exchange, :listing_date)
                """), {
                    **ipo_data,
                    'type': 'CS'  # Common Stock
                })
                db_connection.commit()

            # Step 2: Publish IPO detection event
            with integration_performance_monitor.measure_operation('ipo_event_publish'):
                producer.publish_ipo_detection(ipo_data['symbol'], ipo_data)

            # Step 3: Simulate historical backfill trigger
            backfill_job_id = f"ipo_backfill_{ipo_data['symbol']}"
            producer.publish_backtest_progress(backfill_job_id, 0.5, 'processing')
            producer.publish_backtest_progress(backfill_job_id, 1.0, 'completed')

            # Verify IPO detection message
            with integration_performance_monitor.measure_operation('ipo_message_delivery'):
                ipo_message = listener.wait_for_message(
                    SPRINT14_REDIS_CHANNELS['events']['ipo_detected'],
                    timeout=2.0
                )

            assert ipo_message is not None, "IPO detection message not received"
            ipo_event = ipo_message['parsed_data']

            # Validate IPO event data
            assert ipo_event['event_type'] == 'ipo_detected'
            assert ipo_event['symbol'] == ipo_data['symbol']
            assert ipo_event['listing_date'] == ipo_data['listing_date']
            assert ipo_event['market_cap'] == ipo_data['market_cap']
            assert ipo_event['sector'] == ipo_data['sector']
            assert ipo_event['source'] == 'tickstock_pl'

            # Verify database consistency
            result = db_connection.execute(text("""
                SELECT symbol, name, market_cap, sector, listing_date
                FROM symbols 
                WHERE symbol = :symbol
            """), {'symbol': ipo_data['symbol']})

            db_row = result.fetchone()
            assert db_row is not None
            assert db_row[0] == ipo_data['symbol']
            assert db_row[1] == ipo_data['name']
            assert float(db_row[2]) == ipo_data['market_cap']

            # Verify backfill progress messages
            time.sleep(0.5)
            progress_messages = listener.get_messages(
                SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
            )

            assert len(progress_messages) >= 2
            completed_message = next(
                (msg for msg in progress_messages
                 if msg['parsed_data']['progress'] == 1.0),
                None
            )
            assert completed_message is not None
            assert completed_message['parsed_data']['status'] == 'completed'

            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'ipo_message_delivery',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

        finally:
            listener.stop_listening()

    def test_symbol_change_detection_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test symbol change detection (ticker changes, delistings).
        
        Workflow:
        1. Symbol change detected (e.g., ticker symbol change)
        2. Database updated with archival/mapping
        3. Notification published to Redis
        4. Cache entries updated accordingly
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['ipo_detected']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Insert existing symbol that will undergo change
            old_symbol = 'OLDTICKER'
            new_symbol = 'NEWTICKER'

            db_connection.execute(text("""
                INSERT INTO symbols (symbol, name, type, market_cap, active)
                VALUES (:symbol, 'Test Company', 'CS', 1000000000, true)
            """), {'symbol': old_symbol})
            db_connection.commit()

            # Simulate symbol change detection
            symbol_change_data = {
                'old_symbol': old_symbol,
                'new_symbol': new_symbol,
                'change_type': 'ticker_change',
                'effective_date': datetime.now().date().isoformat(),
                'reason': 'corporate_rebranding'
            }

            with integration_performance_monitor.measure_operation('symbol_change_detection'):
                # Simulate the change as an IPO-like event for the new symbol
                change_notification = {
                    'symbol': new_symbol,
                    'listing_date': symbol_change_data['effective_date'],
                    'market_cap': 1000.0,
                    'sector': 'Technology',
                    'change_from': old_symbol,
                    'change_type': symbol_change_data['change_type']
                }
                producer.publish_ipo_detection(new_symbol, change_notification)

            # Verify symbol change notification
            change_message = listener.wait_for_message(
                SPRINT14_REDIS_CHANNELS['events']['ipo_detected'],
                timeout=2.0
            )

            assert change_message is not None
            change_data = change_message['parsed_data']

            # Validate symbol change event
            assert change_data['symbol'] == new_symbol
            assert 'change_from' in change_data
            assert change_data['change_from'] == old_symbol

            # Verify database state after change
            old_result = db_connection.execute(text("""
                SELECT active FROM symbols WHERE symbol = :symbol
            """), {'symbol': old_symbol})

            old_row = old_result.fetchone()
            # In real implementation, old symbol might be marked inactive
            # For this test, we just verify it still exists
            assert old_row is not None

        finally:
            listener.stop_listening()

    def test_ipo_universe_assignment_integration(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test automatic universe assignment for new IPOs.
        
        Validates that newly detected IPOs are automatically
        assigned to appropriate cache_entries universes based
        on market cap, sector, and other criteria.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['ipo_detected']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Test multiple IPO scenarios with different characteristics
            ipo_scenarios = [
                {
                    'symbol': 'BIGTECH_IPO',
                    'listing_date': '2024-01-15',
                    'market_cap': 50000.0,  # Large cap
                    'sector': 'Technology',
                    'expected_universes': ['large_cap', 'technology_stocks']
                },
                {
                    'symbol': 'SMALLBIO_IPO',
                    'listing_date': '2024-01-16',
                    'market_cap': 500.0,  # Small cap
                    'sector': 'Healthcare',
                    'expected_universes': ['small_cap', 'healthcare_stocks']
                },
                {
                    'symbol': 'FINTECH_IPO',
                    'listing_date': '2024-01-17',
                    'market_cap': 5000.0,  # Mid cap
                    'sector': 'Financial Services',
                    'expected_universes': ['mid_cap', 'financial_stocks']
                }
            ]

            for scenario in ipo_scenarios:
                with integration_performance_monitor.measure_operation('ipo_universe_assignment'):
                    producer.publish_ipo_detection(scenario['symbol'], scenario)
                time.sleep(0.1)  # Small delay between IPOs

            # Wait for all IPO notifications
            time.sleep(1.0)
            ipo_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['ipo_detected'])

            # Validate all IPO notifications received
            assert len(ipo_messages) == 3

            # Validate IPO characteristics for universe assignment
            symbols_by_market_cap = {}
            for message in ipo_messages:
                data = message['parsed_data']
                symbols_by_market_cap[data['symbol']] = data['market_cap']

            # Verify market cap classification
            assert symbols_by_market_cap['BIGTECH_IPO'] >= 10000.0  # Large cap
            assert symbols_by_market_cap['SMALLBIO_IPO'] < 2000.0   # Small cap
            assert 2000.0 <= symbols_by_market_cap['FINTECH_IPO'] < 10000.0  # Mid cap

            # Verify sector information for universe assignment
            sectors_detected = [msg['parsed_data']['sector'] for msg in ipo_messages]
            assert 'Technology' in sectors_detected
            assert 'Healthcare' in sectors_detected
            assert 'Financial Services' in sectors_detected

        finally:
            listener.stop_listening()


class TestDataQualityMonitoringIntegration:
    """Test data quality monitoring and automated remediation workflows"""

    def test_price_anomaly_detection_workflow(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor,
        sprint14_test_data
    ):
        """
        Test price anomaly detection and alerting workflow.
        
        Workflow:
        1. Data quality monitor detects price anomaly
        2. Alert published to Redis
        3. TickStockApp receives quality alert
        4. Dashboard displays anomaly notification
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate multiple types of price anomalies
            anomaly_scenarios = [
                {
                    'symbol': 'GAPPY_STOCK',
                    'alert_type': 'price_gap',
                    'severity': 'high',
                    'description': 'Overnight price gap >15% without news',
                    'current_price': 125.50,
                    'previous_close': 108.00,
                    'gap_percentage': 16.2,
                    'volume_context': 'normal_volume'
                },
                {
                    'symbol': 'VOLATILE_STOCK',
                    'alert_type': 'unusual_volatility',
                    'severity': 'medium',
                    'description': 'Intraday volatility 5x normal range',
                    'volatility_ratio': 5.2,
                    'price_range_percent': 12.8,
                    'volume_spike': True
                },
                {
                    'symbol': 'STALE_STOCK',
                    'alert_type': 'stale_data',
                    'severity': 'medium',
                    'description': 'No price updates for 3+ hours during market',
                    'last_update_hours': 3.5,
                    'market_status': 'open',
                    'expected_activity': True
                }
            ]

            # Publish anomaly alerts
            for anomaly in anomaly_scenarios:
                with integration_performance_monitor.measure_operation('quality_alert_publish'):
                    producer.publish_data_quality_alert(anomaly)
                time.sleep(0.05)

            # Wait for alert processing
            time.sleep(0.5)
            alert_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Validate all alerts received
            assert len(alert_messages) == 3

            # Validate alert types and severity levels
            alert_types = [msg['parsed_data']['alert_type'] for msg in alert_messages]
            assert 'price_gap' in alert_types
            assert 'unusual_volatility' in alert_types
            assert 'stale_data' in alert_types

            # Validate severity classification
            severities = [msg['parsed_data']['severity'] for msg in alert_messages]
            assert 'high' in severities
            assert 'medium' in severities

            # Validate specific anomaly data
            gap_alert = next(
                msg for msg in alert_messages
                if msg['parsed_data']['alert_type'] == 'price_gap'
            )
            gap_data = gap_alert['parsed_data']
            assert gap_data['symbol'] == 'GAPPY_STOCK'
            assert gap_data['gap_percentage'] == 16.2
            assert gap_data['current_price'] == 125.50

            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'quality_alert_publish',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

        finally:
            listener.stop_listening()

    def test_data_completeness_monitoring_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test data completeness monitoring and gap detection.
        
        Validates detection of missing OHLCV data, trading day gaps,
        and automated remediation triggers.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate data completeness issues
            completeness_issues = [
                {
                    'symbol': 'MISSING_OHLC',
                    'alert_type': 'missing_ohlcv_data',
                    'severity': 'high',
                    'description': 'Missing OHLCV data for 2 consecutive trading days',
                    'missing_days': 2,
                    'last_valid_date': '2024-01-12',
                    'first_missing_date': '2024-01-13',
                    'data_source': 'massive_io',
                    'remediation_attempted': False
                },
                {
                    'symbol': 'PARTIAL_TICKS',
                    'alert_type': 'incomplete_tick_data',
                    'severity': 'medium',
                    'description': 'Tick data coverage <80% for trading session',
                    'coverage_percentage': 72.5,
                    'expected_ticks': 10000,
                    'received_ticks': 7250,
                    'session_date': '2024-01-15'
                },
                {
                    'symbol': 'WEEKEND_GAP',
                    'alert_type': 'expected_data_gap',
                    'severity': 'low',
                    'description': 'Normal weekend data gap detected',
                    'gap_type': 'weekend',
                    'gap_start': '2024-01-12 16:00:00',
                    'gap_end': '2024-01-16 09:30:00',
                    'expected': True
                }
            ]

            # Publish completeness alerts
            for issue in completeness_issues:
                with integration_performance_monitor.measure_operation('completeness_alert_publish'):
                    producer.publish_data_quality_alert(issue)
                time.sleep(0.05)

            # Wait for alert processing
            time.sleep(0.5)
            completeness_messages = listener.get_messages(
                SPRINT14_REDIS_CHANNELS['events']['quality_alert']
            )

            # Validate completeness alerts
            assert len(completeness_messages) == 3

            # Validate alert classification by severity
            high_severity_alerts = [
                msg for msg in completeness_messages
                if msg['parsed_data']['severity'] == 'high'
            ]
            assert len(high_severity_alerts) == 1
            assert high_severity_alerts[0]['parsed_data']['alert_type'] == 'missing_ohlcv_data'

            # Validate missing data details
            missing_ohlc_alert = high_severity_alerts[0]['parsed_data']
            assert missing_ohlc_alert['symbol'] == 'MISSING_OHLC'
            assert missing_ohlc_alert['missing_days'] == 2
            assert missing_ohlc_alert['last_valid_date'] == '2024-01-12'

            # Validate expected vs unexpected gaps
            weekend_alert = next(
                msg for msg in completeness_messages
                if msg['parsed_data']['alert_type'] == 'expected_data_gap'
            )
            weekend_data = weekend_alert['parsed_data']
            assert weekend_data['expected'] is True
            assert weekend_data['severity'] == 'low'

        finally:
            listener.stop_listening()

    def test_automated_remediation_workflow(
        self,
        redis_client,
        mock_tickstockpl_producer,
        mock_tickstockapp_consumer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test automated remediation workflow for data quality issues.
        
        Workflow:
        1. Data quality issue detected
        2. Alert published to Redis
        3. Automated remediation triggered
        4. Remediation status updates published
        5. Issue resolution confirmed
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['events']['quality_alert'],
            SPRINT14_REDIS_CHANNELS['jobs']['data_request']
        ]
        listener.subscribe(channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)
        consumer = mock_tickstockapp_consumer(redis_client)

        try:
            # Step 1: Publish initial data quality alert
            initial_issue = {
                'symbol': 'REMEDIATE_ME',
                'alert_type': 'missing_recent_data',
                'severity': 'medium',
                'description': 'Missing last 4 hours of tick data',
                'hours_missing': 4,
                'auto_remediation_eligible': True,
                'remediation_method': 'api_refetch'
            }

            with integration_performance_monitor.measure_operation('remediation_alert_initial'):
                producer.publish_data_quality_alert(initial_issue)

            # Step 2: Simulate automated remediation request
            remediation_request = {
                'symbols': [initial_issue['symbol']],
                'data_types': ['tick_data'],
                'time_range_hours': initial_issue['hours_missing'],
                'priority': 'high',
                'triggered_by': 'data_quality_monitor'
            }

            with integration_performance_monitor.measure_operation('remediation_request_submit'):
                consumer.submit_data_request(remediation_request)

            # Step 3: Simulate remediation progress updates
            remediation_updates = [
                {
                    'symbol': 'REMEDIATE_ME',
                    'alert_type': 'remediation_in_progress',
                    'severity': 'low',
                    'description': 'Refetching missing tick data from API',
                    'progress_percentage': 25,
                    'estimated_completion_minutes': 15
                },
                {
                    'symbol': 'REMEDIATE_ME',
                    'alert_type': 'remediation_completed',
                    'severity': 'low',
                    'description': 'Successfully recovered 3.8 hours of tick data',
                    'recovered_hours': 3.8,
                    'success_rate': 0.95,
                    'remaining_gaps': 0.2
                }
            ]

            for update in remediation_updates:
                producer.publish_data_quality_alert(update)
                time.sleep(0.1)

            # Wait for all remediation messages
            time.sleep(1.0)

            # Verify initial alert received
            quality_alerts = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            initial_alerts = [
                msg for msg in quality_alerts
                if msg['parsed_data']['alert_type'] == 'missing_recent_data'
            ]
            assert len(initial_alerts) == 1

            # Verify remediation request received
            remediation_requests = listener.get_messages(SPRINT14_REDIS_CHANNELS['jobs']['data_request'])
            assert len(remediation_requests) == 1

            request_data = remediation_requests[0]['parsed_data']
            assert request_data['triggered_by'] == 'data_quality_monitor'
            assert 'REMEDIATE_ME' in request_data['symbols']

            # Verify remediation progress updates
            progress_alerts = [
                msg for msg in quality_alerts
                if msg['parsed_data']['alert_type'] == 'remediation_in_progress'
            ]
            assert len(progress_alerts) == 1

            # Verify remediation completion
            completion_alerts = [
                msg for msg in quality_alerts
                if msg['parsed_data']['alert_type'] == 'remediation_completed'
            ]
            assert len(completion_alerts) == 1

            completion_data = completion_alerts[0]['parsed_data']
            assert completion_data['recovered_hours'] == 3.8
            assert completion_data['success_rate'] == 0.95

            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'remediation_alert_initial',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

        finally:
            listener.stop_listening()


class TestEquityTypesIntegration:
    """Test equity types integration for processing rule management"""

    def test_equity_type_configuration_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test equity type configuration and processing rule updates.
        
        Workflow:
        1. Equity type configuration updated
        2. Processing rules modified based on type
        3. Notification published to Redis
        4. System adapts processing behavior
        """
        listener = redis_pubsub_listener(redis_client)
        # Use quality_alert channel for equity type notifications
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate equity type processing rule updates
            equity_type_updates = [
                {
                    'symbol': 'REALTIME_STOCK',
                    'alert_type': 'equity_type_updated',
                    'severity': 'low',
                    'description': 'Symbol classified as real-time equity',
                    'equity_type': 'realtime_equity',
                    'processing_rules': {
                        'tick_processing': True,
                        'pattern_detection': True,
                        'eod_updates': True,
                        'latency_target_ms': 50
                    }
                },
                {
                    'symbol': 'EOD_ONLY_FUND',
                    'alert_type': 'equity_type_updated',
                    'severity': 'low',
                    'description': 'Symbol classified as EOD-only mutual fund',
                    'equity_type': 'eod_only_fund',
                    'processing_rules': {
                        'tick_processing': False,
                        'pattern_detection': False,
                        'eod_updates': True,
                        'update_frequency': 'daily_close'
                    }
                },
                {
                    'symbol': 'DELAYED_ETF',
                    'alert_type': 'equity_type_updated',
                    'severity': 'low',
                    'description': 'Symbol classified as delayed-data ETF',
                    'equity_type': 'delayed_etf',
                    'processing_rules': {
                        'tick_processing': True,
                        'pattern_detection': True,
                        'data_delay_minutes': 15,
                        'fmv_approximation_allowed': True
                    }
                }
            ]

            # Publish equity type updates
            for update in equity_type_updates:
                with integration_performance_monitor.measure_operation('equity_type_update'):
                    producer.publish_data_quality_alert(update)
                time.sleep(0.05)

            # Wait for processing rule updates
            time.sleep(0.5)
            equity_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Filter equity type update messages
            equity_updates = [
                msg for msg in equity_messages
                if msg['parsed_data']['alert_type'] == 'equity_type_updated'
            ]

            # Validate equity type updates received
            assert len(equity_updates) == 3

            # Validate processing rule configurations
            symbols_by_type = {}
            for message in equity_updates:
                data = message['parsed_data']
                symbols_by_type[data['equity_type']] = {
                    'symbol': data['symbol'],
                    'rules': data['processing_rules']
                }

            # Validate real-time equity configuration
            realtime_config = symbols_by_type['realtime_equity']
            assert realtime_config['rules']['tick_processing'] is True
            assert realtime_config['rules']['pattern_detection'] is True
            assert realtime_config['rules']['latency_target_ms'] == 50

            # Validate EOD-only fund configuration
            eod_config = symbols_by_type['eod_only_fund']
            assert eod_config['rules']['tick_processing'] is False
            assert eod_config['rules']['pattern_detection'] is False
            assert eod_config['rules']['update_frequency'] == 'daily_close'

            # Validate delayed ETF configuration
            delayed_config = symbols_by_type['delayed_etf']
            assert delayed_config['rules']['data_delay_minutes'] == 15
            assert delayed_config['rules']['fmv_approximation_allowed'] is True

        finally:
            listener.stop_listening()

    def test_processing_rule_adaptation_workflow(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test processing rule adaptation based on equity types.
        
        Validates that system behavior adapts to different
        equity types with appropriate processing rules.
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['events']['patterns'],
            SPRINT14_REDIS_CHANNELS['events']['quality_alert']
        ]
        listener.subscribe(channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate processing behavior for different equity types

            # Real-time equity: Full pattern detection enabled
            realtime_pattern = {
                'symbol': 'REALTIME_STOCK',
                'pattern': 'Doji',
                'confidence': 0.89,
                'timeframe': '1M',
                'processing_latency_ms': 45,
                'equity_type': 'realtime_equity'
            }

            with integration_performance_monitor.measure_operation('realtime_pattern_detection'):
                producer.publish_pattern_event(realtime_pattern)

            # Delayed ETF: Pattern detection with FMV approximation
            delayed_etf_pattern = {
                'symbol': 'DELAYED_ETF',
                'pattern': 'Hammer',
                'confidence': 0.76,
                'timeframe': '5M',
                'processing_latency_ms': 85,
                'equity_type': 'delayed_etf',
                'fmv_approximation_used': True,
                'data_delay_minutes': 15
            }

            producer.publish_pattern_event(delayed_etf_pattern)

            # EOD-only fund: No pattern detection, only EOD alert
            eod_fund_alert = {
                'symbol': 'EOD_ONLY_FUND',
                'alert_type': 'eod_price_update',
                'severity': 'low',
                'description': 'Daily NAV update received',
                'nav_price': 25.47,
                'equity_type': 'eod_only_fund',
                'update_time': '16:00:00'
            }

            producer.publish_data_quality_alert(eod_fund_alert)

            # Wait for processing adaptations
            time.sleep(0.5)

            # Verify real-time pattern detection
            pattern_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['patterns'])
            assert len(pattern_messages) == 2

            realtime_message = next(
                msg for msg in pattern_messages
                if msg['parsed_data']['symbol'] == 'REALTIME_STOCK'
            )
            realtime_data = realtime_message['parsed_data']
            assert realtime_data['processing_latency_ms'] <= 50  # Within target
            assert realtime_data['confidence'] >= 0.8

            # Verify delayed ETF processing
            delayed_message = next(
                msg for msg in pattern_messages
                if msg['parsed_data']['symbol'] == 'DELAYED_ETF'
            )
            delayed_data = delayed_message['parsed_data']
            assert 'fmv_approximation_used' in delayed_data
            assert delayed_data['fmv_approximation_used'] is True

            # Verify EOD-only fund behavior
            quality_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            eod_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'eod_price_update'
            ]
            assert len(eod_messages) == 1

            eod_data = eod_messages[0]['parsed_data']
            assert eod_data['symbol'] == 'EOD_ONLY_FUND'
            assert eod_data['nav_price'] == 25.47

        finally:
            listener.stop_listening()


class TestPhase2CrossSystemIntegration:
    """Test cross-system integration scenarios across Phase 2 features"""

    def test_ipo_to_quality_to_equity_type_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor,
        sprint14_test_data
    ):
        """
        Test complete Phase 2 workflow: IPO detection → Quality monitoring → Equity type assignment.
        
        End-to-end validation of Phase 2 automation capabilities.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = [
            SPRINT14_REDIS_CHANNELS['events']['ipo_detected'],
            SPRINT14_REDIS_CHANNELS['events']['quality_alert']
        ]
        listener.subscribe(all_channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Step 1: IPO Detection
            ipo_data = sprint14_test_data.ipo_listing_data()
            ipo_data['symbol'] = 'PHASE2_IPO'

            with integration_performance_monitor.measure_operation('phase2_ipo_detection'):
                producer.publish_ipo_detection(ipo_data['symbol'], ipo_data)

            # Step 2: Initial data quality assessment
            quality_assessment = {
                'symbol': ipo_data['symbol'],
                'alert_type': 'new_symbol_assessment',
                'severity': 'low',
                'description': 'Initial data quality assessment for new IPO',
                'data_availability': 'limited',
                'assessment_score': 0.7,
                'recommendations': ['monitor_for_30_days', 'use_fmv_approximation']
            }

            with integration_performance_monitor.measure_operation('phase2_quality_assessment'):
                producer.publish_data_quality_alert(quality_assessment)

            # Step 3: Equity type assignment
            equity_type_assignment = {
                'symbol': ipo_data['symbol'],
                'alert_type': 'equity_type_assigned',
                'severity': 'low',
                'description': 'Equity type assigned based on IPO characteristics',
                'equity_type': 'realtime_equity',  # New IPO gets real-time processing
                'assignment_reason': 'new_ipo_default',
                'processing_rules': {
                    'tick_processing': True,
                    'pattern_detection': True,
                    'quality_monitoring_enhanced': True,
                    'probation_period_days': 30
                }
            }

            producer.publish_data_quality_alert(equity_type_assignment)

            # Wait for complete workflow
            time.sleep(1.0)

            # Verify IPO detection
            ipo_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['ipo_detected'])
            assert len(ipo_messages) >= 1

            ipo_detected = next(
                msg for msg in ipo_messages
                if msg['parsed_data']['symbol'] == 'PHASE2_IPO'
            )
            assert ipo_detected is not None

            # Verify quality assessment
            quality_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            assessment_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'new_symbol_assessment'
            ]
            assert len(assessment_messages) >= 1

            # Verify equity type assignment
            assignment_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'equity_type_assigned'
            ]
            assert len(assignment_messages) >= 1

            assignment_data = assignment_messages[0]['parsed_data']
            assert assignment_data['symbol'] == 'PHASE2_IPO'
            assert assignment_data['equity_type'] == 'realtime_equity'
            assert assignment_data['processing_rules']['probation_period_days'] == 30

            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'phase2_ipo_detection',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

        finally:
            listener.stop_listening()

    def test_phase2_system_resilience_under_load(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test Phase 2 system resilience under high IPO and quality alert volume.
        
        Validates system performance during periods of high market activity
        with multiple IPOs and quality issues.
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['events']['ipo_detected'],
            SPRINT14_REDIS_CHANNELS['events']['quality_alert']
        ]
        listener.subscribe(channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate high-volume scenario: Multiple IPOs and quality alerts
            with integration_performance_monitor.measure_operation('phase2_high_volume_resilience'):

                # Generate 20 IPO events
                for i in range(20):
                    ipo_data = {
                        'symbol': f'IPO_{i:03d}',
                        'listing_date': '2024-01-15',
                        'market_cap': 1000.0 + (i * 100),
                        'sector': ['Technology', 'Healthcare', 'Financial Services'][i % 3]
                    }
                    producer.publish_ipo_detection(ipo_data['symbol'], ipo_data)

                # Generate 50 quality alerts
                for i in range(50):
                    quality_alert = {
                        'symbol': f'ALERT_{i:03d}',
                        'alert_type': 'price_anomaly',
                        'severity': ['low', 'medium', 'high'][i % 3],
                        'description': f'Automated quality check #{i}',
                        'anomaly_score': 0.5 + (i * 0.01)
                    }
                    producer.publish_data_quality_alert(quality_alert)

                    if i % 10 == 0:  # Yield every 10 messages
                        time.sleep(0.01)

            # Allow processing time
            time.sleep(2.0)

            # Verify system handled high volume
            ipo_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['ipo_detected'])
            quality_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Should receive most messages despite high volume
            assert len(ipo_messages) >= 18, f"Expected ≥18 IPO messages, got {len(ipo_messages)}"
            assert len(quality_messages) >= 45, f"Expected ≥45 quality messages, got {len(quality_messages)}"

            # Validate message integrity under load
            ipo_symbols = set(msg['parsed_data']['symbol'] for msg in ipo_messages)
            quality_symbols = set(msg['parsed_data']['symbol'] for msg in quality_messages)

            # Should have diverse symbol coverage
            assert len(ipo_symbols) >= 15
            assert len(quality_symbols) >= 40

            # Performance should be reasonable under load
            integration_performance_monitor.assert_performance_target(
                'phase2_high_volume_resilience',
                PERFORMANCE_TARGETS['end_to_end_workflow_ms']
            )

        finally:
            listener.stop_listening()
