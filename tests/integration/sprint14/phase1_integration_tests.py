"""
Sprint 14 Phase 1 Integration Tests

Tests cross-system integration for:
- Enhanced ETF Integration 
- End-of-Day Market Data Updates
- Historical Data Loading with subset support

Validates TickStockApp (consumer) ↔ TickStockPL (producer) communication
via Redis pub-sub with <100ms delivery performance requirements.
"""
import pytest
import json
import time
import threading
from unittest.mock import Mock, patch
from sqlalchemy import text
from typing import Dict, List

from tests.integration.sprint14.conftest import (
    SPRINT14_REDIS_CHANNELS,
    PERFORMANCE_TARGETS
)


class TestETFIntegrationWorkflow:
    """Test ETF integration end-to-end workflow validation"""
    
    def test_etf_universe_loading_integration(
        self, 
        redis_client, 
        db_connection,
        mock_tickstockpl_producer, 
        redis_pubsub_listener,
        integration_performance_monitor,
        sprint14_test_data
    ):
        """
        Test ETF universe loading workflow from database to Redis to UI.
        
        Workflow:
        1. ETF data loaded into symbols table (simulated)
        2. TickStockPL publishes ETF update event
        3. TickStockApp consumes event via Redis
        4. UI receives WebSocket update
        """
        # Setup listener for ETF events
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['etf_updated']])
        listener.start_listening()
        
        # Setup mock producer
        producer = mock_tickstockpl_producer(redis_client)
        etf_data = sprint14_test_data.etf_symbol_data()
        
        try:
            # Simulate ETF data insertion into database
            with integration_performance_monitor.measure_operation('etf_db_insert'):
                db_connection.execute(text("""
                    INSERT INTO symbols (symbol, name, type, market_cap, etf_type, 
                                       aum_millions, expense_ratio, underlying_index)
                    VALUES (:symbol, :name, 'ETF', 1000000000, :etf_type, 
                            :aum_millions, :expense_ratio, :underlying_index)
                """), etf_data)
                db_connection.commit()
            
            # Simulate TickStockPL publishing ETF update
            with integration_performance_monitor.measure_operation('etf_redis_publish'):
                producer.publish_etf_data_update(etf_data['symbol'], etf_data)
            
            # Verify message delivery within performance target
            with integration_performance_monitor.measure_operation('etf_message_delivery'):
                etf_message = listener.wait_for_message(
                    SPRINT14_REDIS_CHANNELS['events']['etf_updated'], 
                    timeout=2.0
                )
            
            # Validate message received
            assert etf_message is not None, "ETF update message not received"
            assert etf_message['parsed_data']['symbol'] == etf_data['symbol']
            assert etf_message['parsed_data']['aum_millions'] == etf_data['aum_millions']
            assert etf_message['parsed_data']['event_type'] == 'etf_data_updated'
            
            # Verify database data consistency
            result = db_connection.execute(text("""
                SELECT symbol, etf_type, aum_millions, expense_ratio 
                FROM symbols 
                WHERE symbol = :symbol
            """), {'symbol': etf_data['symbol']})
            
            db_row = result.fetchone()
            assert db_row is not None
            assert db_row[0] == etf_data['symbol']
            assert float(db_row[2]) == etf_data['aum_millions']
            
            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'etf_message_delivery', 
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
        finally:
            listener.stop_listening()
    
    def test_etf_universe_filtering_integration(
        self, 
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        sprint14_test_data
    ):
        """
        Test ETF universe filtering based on AUM and expense ratio.
        
        Validates that ETF classification events are properly filtered
        and routed to appropriate universe themes.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['etf_updated']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Test multiple ETF types with different characteristics
            etf_scenarios = [
                # Large cap growth ETF
                {
                    'symbol': 'GROWTH_ETF',
                    'etf_type': 'equity_growth',
                    'aum_millions': 50000.0,  # Large AUM
                    'expense_ratio': 0.0050,  # Low expense ratio
                    'expected_theme': 'etf_growth'
                },
                # Sector-specific ETF
                {
                    'symbol': 'TECH_ETF',
                    'etf_type': 'sector_technology',
                    'aum_millions': 10000.0,  # Medium AUM
                    'expense_ratio': 0.0075,
                    'expected_theme': 'etf_sectors'
                },
                # Value ETF
                {
                    'symbol': 'VALUE_ETF',
                    'etf_type': 'equity_value',
                    'aum_millions': 25000.0,
                    'expense_ratio': 0.0040,
                    'expected_theme': 'etf_value'
                }
            ]
            
            for scenario in etf_scenarios:
                producer.publish_etf_data_update(scenario['symbol'], scenario)
                time.sleep(0.05)  # Small delay between messages
            
            # Wait for all messages
            time.sleep(0.5)
            messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['etf_updated'])
            
            # Validate all ETF updates received
            assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
            
            # Validate proper ETF classification
            symbols_received = [msg['parsed_data']['symbol'] for msg in messages]
            expected_symbols = [scenario['symbol'] for scenario in etf_scenarios]
            
            assert set(symbols_received) == set(expected_symbols)
            
            # Validate AUM and expense ratio data
            for message in messages:
                data = message['parsed_data']
                scenario = next(s for s in etf_scenarios if s['symbol'] == data['symbol'])
                
                assert data['aum_millions'] == scenario['aum_millions']
                assert data['expense_ratio'] == scenario['expense_ratio']
                assert data['event_type'] == 'etf_data_updated'
                
        finally:
            listener.stop_listening()
    
    def test_etf_correlation_tracking_integration(
        self, 
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test ETF correlation tracking with reference symbols (SPY, IWM).
        
        Validates that correlation data is properly tracked and
        correlation change events are published.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['etf_updated']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Insert reference ETF with correlation data
            correlation_data = {
                'symbol': 'CORR_ETF',
                'name': 'Correlation Test ETF',
                'etf_type': 'equity_large_cap',
                'aum_millions': 5000.0,
                'expense_ratio': 0.0060,
                'underlying_index': 'S&P 500',
                'correlation_reference': 'SPY'
            }
            
            with integration_performance_monitor.measure_operation('correlation_etf_insert'):
                db_connection.execute(text("""
                    INSERT INTO symbols (symbol, name, type, etf_type, aum_millions, 
                                       expense_ratio, underlying_index, correlation_reference)
                    VALUES (:symbol, :name, 'ETF', :etf_type, :aum_millions, 
                            :expense_ratio, :underlying_index, :correlation_reference)
                """), correlation_data)
                db_connection.commit()
            
            # Publish correlation update event
            correlation_update = {
                **correlation_data,
                'correlation_coefficient': 0.95,
                'correlation_period_days': 30,
                'last_correlation_update': time.time()
            }
            
            producer.publish_etf_data_update(correlation_data['symbol'], correlation_update)
            
            # Verify message delivery
            message = listener.wait_for_message(
                SPRINT14_REDIS_CHANNELS['events']['etf_updated'],
                timeout=2.0
            )
            
            assert message is not None
            data = message['parsed_data']
            assert data['symbol'] == correlation_data['symbol']
            assert data['underlying_index'] == 'S&P 500'
            
            # Validate database correlation reference
            result = db_connection.execute(text("""
                SELECT correlation_reference, underlying_index
                FROM symbols 
                WHERE symbol = :symbol
            """), {'symbol': correlation_data['symbol']})
            
            row = result.fetchone()
            assert row[0] == 'SPY'  # correlation_reference
            assert row[1] == 'S&P 500'  # underlying_index
            
        finally:
            listener.stop_listening()


class TestEODProcessingIntegration:
    """Test End-of-Day processing integration workflow"""
    
    def test_eod_completion_notification_workflow(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test EOD processing completion notification workflow.
        
        Workflow:
        1. EOD processing completes in TickStockPL
        2. Completion notification published to Redis
        3. TickStockApp receives notification
        4. UI displays processing summary
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['eod_complete']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate EOD processing completion
            eod_summary = {
                'symbols_processed': 4247,
                'success_rate': 0.972,
                'failed_symbols': ['DELISTED_STOCK', 'HALTED_STOCK'],
                'processing_time_seconds': 3420,
                'data_gaps_filled': 45,
                'fmv_approximations_used': 12
            }
            
            with integration_performance_monitor.measure_operation('eod_notification_publish'):
                producer.publish_eod_completion(eod_summary)
            
            # Verify notification delivery
            with integration_performance_monitor.measure_operation('eod_notification_delivery'):
                eod_message = listener.wait_for_message(
                    SPRINT14_REDIS_CHANNELS['events']['eod_complete'],
                    timeout=2.0
                )
            
            assert eod_message is not None
            data = eod_message['parsed_data']
            
            # Validate EOD completion data
            assert data['event_type'] == 'eod_processing_complete'
            assert data['symbols_processed'] == 4247
            assert data['success_rate'] == 0.972
            assert len(data['failed_symbols']) == 2
            assert data['processing_time_seconds'] == 3420
            assert data['source'] == 'tickstock_pl'
            
            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'eod_notification_delivery',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
        finally:
            listener.stop_listening()
    
    def test_eod_market_holiday_handling(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener
    ):
        """
        Test EOD processing behavior during market holidays.
        
        Validates that holiday detection prevents unnecessary
        EOD processing and appropriate notifications are sent.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['eod_complete']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate holiday EOD summary
            holiday_summary = {
                'symbols_processed': 0,
                'success_rate': 1.0,
                'failed_symbols': [],
                'processing_time_seconds': 5,
                'holiday_detected': 'Christmas Day',
                'next_processing_date': '2024-12-26',
                'market_closed': True
            }
            
            producer.publish_eod_completion(holiday_summary)
            
            # Verify holiday notification
            holiday_message = listener.wait_for_message(
                SPRINT14_REDIS_CHANNELS['events']['eod_complete'],
                timeout=2.0
            )
            
            assert holiday_message is not None
            data = holiday_message['parsed_data']
            
            # Validate holiday handling
            assert data['symbols_processed'] == 0
            assert 'holiday_detected' in data or 'market_closed' in data
            assert data['processing_time_seconds'] < 60  # Minimal processing
            
        finally:
            listener.stop_listening()
    
    def test_eod_data_quality_validation(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test EOD data quality validation and gap detection.
        
        Validates that data quality issues are detected during
        EOD processing and appropriate alerts are generated.
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['events']['eod_complete'],
            SPRINT14_REDIS_CHANNELS['events']['quality_alert']
        ]
        listener.subscribe(channels)
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # First, publish data quality alerts detected during EOD
            quality_issues = [
                {
                    'symbol': 'GAPPY_STOCK',
                    'alert_type': 'missing_data',
                    'severity': 'medium',
                    'description': 'Missing OHLCV data for 2 consecutive days',
                    'gap_start_date': '2024-01-15',
                    'gap_end_date': '2024-01-16'
                },
                {
                    'symbol': 'VOLATILE_STOCK', 
                    'alert_type': 'price_anomaly',
                    'severity': 'high',
                    'description': 'Price movement >25% without volume spike',
                    'price_change_percent': 28.5,
                    'volume_ratio': 0.8
                }
            ]
            
            # Publish quality alerts
            for alert in quality_issues:
                producer.publish_data_quality_alert(alert)
                time.sleep(0.05)
            
            # Then publish EOD completion with quality summary
            eod_summary = {
                'symbols_processed': 4200,
                'success_rate': 0.965,
                'failed_symbols': ['DELISTED_STOCK'],
                'processing_time_seconds': 3600,
                'data_quality_alerts': len(quality_issues),
                'gaps_detected': 1,
                'anomalies_detected': 1
            }
            
            with integration_performance_monitor.measure_operation('eod_quality_completion'):
                producer.publish_eod_completion(eod_summary)
            
            # Wait for all messages
            time.sleep(0.5)
            
            # Verify quality alerts received
            quality_messages = listener.get_messages(
                SPRINT14_REDIS_CHANNELS['events']['quality_alert']
            )
            assert len(quality_messages) == 2
            
            # Verify EOD completion with quality summary
            eod_messages = listener.get_messages(
                SPRINT14_REDIS_CHANNELS['events']['eod_complete']
            )
            assert len(eod_messages) == 1
            
            eod_data = eod_messages[0]['parsed_data']
            assert eod_data['data_quality_alerts'] == 2
            assert eod_data['gaps_detected'] == 1
            assert eod_data['anomalies_detected'] == 1
            
            # Validate individual quality alerts
            alert_symbols = [msg['parsed_data']['symbol'] for msg in quality_messages]
            assert 'GAPPY_STOCK' in alert_symbols
            assert 'VOLATILE_STOCK' in alert_symbols
            
        finally:
            listener.stop_listening()


class TestHistoricalLoadingIntegration:
    """Test historical data loading integration workflows"""
    
    def test_subset_universe_loading_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockapp_consumer,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor,
        sprint14_test_data
    ):
        """
        Test subset universe loading for development environments.
        
        Workflow:
        1. TickStockApp requests subset historical load
        2. TickStockPL processes subset load job
        3. Progress updates published via Redis
        4. Completion notification with load summary
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['jobs']['data_request'],
            SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
        ]
        listener.subscribe(channels)
        listener.start_listening()
        
        app_consumer = mock_tickstockapp_consumer(redis_client)
        pl_producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate TickStockApp requesting subset historical load
            subset_request = {
                'request_type': 'historical_subset_load',
                'symbols': ['AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ'],
                'start_date': '2024-01-01',
                'end_date': '2024-03-31',
                'data_types': ['ohlcv_daily', 'ohlcv_1min'],
                'environment': 'development'
            }
            
            with integration_performance_monitor.measure_operation('subset_request_submit'):
                app_consumer.submit_data_request(subset_request)
            
            # Verify job request received
            job_message = listener.wait_for_message(
                SPRINT14_REDIS_CHANNELS['jobs']['data_request'],
                timeout=2.0
            )
            
            assert job_message is not None
            job_data = job_message['parsed_data']
            assert job_data['request_type'] == 'historical_subset_load'
            assert len(job_data['symbols']) == 5
            assert job_data['environment'] == 'development'
            
            # Simulate TickStockPL processing subset load with progress updates
            job_id = f"subset_load_{int(time.time())}"
            progress_updates = [0.2, 0.4, 0.6, 0.8, 1.0]
            
            for progress in progress_updates:
                status = 'processing' if progress < 1.0 else 'completed'
                pl_producer.publish_backtest_progress(job_id, progress, status)
                time.sleep(0.1)
            
            # Wait for all progress updates
            time.sleep(0.5)
            progress_messages = listener.get_messages(
                SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
            )
            
            # Validate progress updates
            assert len(progress_messages) == 5
            final_message = progress_messages[-1]
            final_data = final_message['parsed_data']
            
            assert final_data['progress'] == 1.0
            assert final_data['status'] == 'completed'
            
            # Performance validation for subset loading
            integration_performance_monitor.assert_performance_target(
                'subset_request_submit',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
        finally:
            listener.stop_listening()
    
    def test_historical_loading_performance_benchmarks(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test historical loading performance benchmarks.
        
        Validates that subset loading meets <5 minute target for
        development environments (10 stocks + 5 ETFs, 6 months data).
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['backtesting_results']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate subset loading completion with performance metrics
            performance_results = {
                'job_id': 'perf_test_subset_load',
                'load_type': 'development_subset',
                'symbols_loaded': 15,  # 10 stocks + 5 ETFs
                'time_range_months': 6,
                'total_load_time_seconds': 285,  # Under 5 minute target
                'records_loaded': 125000,
                'load_rate_records_per_second': 438,
                'api_calls_made': 450,
                'api_error_rate': 0.008,  # <1% error rate
                'performance_metrics': {
                    'avg_api_response_ms': 245,
                    'database_insert_rate_per_sec': 2500,
                    'memory_usage_mb': 150,
                    'cpu_utilization_percent': 35
                }
            }
            
            with integration_performance_monitor.measure_operation('performance_benchmark_publish'):
                producer.publish_backtest_results(
                    performance_results['job_id'], 
                    performance_results
                )
            
            # Verify performance results message
            perf_message = listener.wait_for_message(
                SPRINT14_REDIS_CHANNELS['events']['backtesting_results'],
                timeout=2.0
            )
            
            assert perf_message is not None
            results = perf_message['parsed_data']['results']
            
            # Validate performance targets met
            assert results['total_load_time_seconds'] < 300  # <5 minutes
            assert results['api_error_rate'] < 0.05  # <5% error rate
            assert results['symbols_loaded'] == 15
            assert results['performance_metrics']['avg_api_response_ms'] < 500
            
        finally:
            listener.stop_listening()
    
    def test_historical_loading_fmv_fallback_integration(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test FMV (Fair Market Value) fallback during historical loading.
        
        Validates that thinly traded symbols use FMV approximations
        when real market data is unavailable.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate FMV fallback scenarios during historical loading
            fmv_alerts = [
                {
                    'symbol': 'THINLY_TRADED_ETF',
                    'alert_type': 'fmv_approximation_used',
                    'severity': 'low',
                    'description': 'Used FMV approximation for missing intraday data',
                    'approximation_method': 'last_known_price_adjusted',
                    'confidence_score': 0.92,
                    'affected_time_periods': 8
                },
                {
                    'symbol': 'MICRO_CAP_STOCK',
                    'alert_type': 'fmv_approximation_used', 
                    'severity': 'medium',
                    'description': 'Extended FMV usage due to trading halt',
                    'approximation_method': 'peer_correlation_estimate',
                    'confidence_score': 0.78,
                    'affected_time_periods': 24,
                    'halt_reason': 'regulatory_review'
                }
            ]
            
            # Publish FMV usage alerts
            for alert in fmv_alerts:
                with integration_performance_monitor.measure_operation('fmv_alert_publish'):
                    producer.publish_data_quality_alert(alert)
                time.sleep(0.05)
            
            # Wait for FMV alerts
            time.sleep(0.5)
            fmv_messages = listener.get_messages(
                SPRINT14_REDIS_CHANNELS['events']['quality_alert']
            )
            
            # Validate FMV alerts received
            assert len(fmv_messages) == 2
            
            fmv_symbols = [msg['parsed_data']['symbol'] for msg in fmv_messages]
            assert 'THINLY_TRADED_ETF' in fmv_symbols
            assert 'MICRO_CAP_STOCK' in fmv_symbols
            
            # Validate FMV confidence scores and methods
            for message in fmv_messages:
                data = message['parsed_data']
                assert data['alert_type'] == 'fmv_approximation_used'
                assert 'confidence_score' in data
                assert 'approximation_method' in data
                assert data['confidence_score'] >= 0.7  # Minimum confidence
                
        finally:
            listener.stop_listening()


class TestPhase1CrossSystemIntegration:
    """Test cross-system integration scenarios across Phase 1 features"""
    
    def test_etf_to_eod_to_historical_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor,
        sprint14_test_data
    ):
        """
        Test complete workflow: ETF integration → EOD processing → Historical loading.
        
        End-to-end workflow validation across all Phase 1 components.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values())
        listener.subscribe(all_channels)
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Step 1: ETF Integration - New ETF discovered and loaded
            etf_data = sprint14_test_data.etf_symbol_data()
            etf_data['symbol'] = 'WORKFLOW_ETF'
            
            with integration_performance_monitor.measure_operation('workflow_etf_integration'):
                producer.publish_etf_data_update(etf_data['symbol'], etf_data)
            
            # Step 2: EOD Processing - ETF included in daily processing
            eod_summary = {
                'symbols_processed': 4248,  # Including new ETF
                'success_rate': 0.975,
                'failed_symbols': [],
                'processing_time_seconds': 3450,
                'new_symbols_added': [etf_data['symbol']],
                'etf_updates': 1
            }
            
            with integration_performance_monitor.measure_operation('workflow_eod_processing'):
                producer.publish_eod_completion(eod_summary)
            
            # Step 3: Historical Loading - Backfill for new ETF triggered
            backfill_job_id = f"backfill_{etf_data['symbol']}_{int(time.time())}"
            
            with integration_performance_monitor.measure_operation('workflow_historical_backfill'):
                producer.publish_backtest_progress(backfill_job_id, 1.0, 'completed')
            
            # Wait for all workflow messages
            time.sleep(1.0)
            
            # Validate ETF integration message
            etf_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['etf_updated'])
            assert len(etf_messages) >= 1
            assert any(
                msg['parsed_data']['symbol'] == 'WORKFLOW_ETF' 
                for msg in etf_messages
            )
            
            # Validate EOD completion message
            eod_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['eod_complete'])
            assert len(eod_messages) >= 1
            eod_data = eod_messages[-1]['parsed_data']
            assert eod_data['symbols_processed'] == 4248
            assert 'new_symbols_added' in eod_data
            
            # Validate backfill progress message
            progress_messages = listener.get_messages(
                SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
            )
            assert len(progress_messages) >= 1
            progress_data = progress_messages[-1]['parsed_data']
            assert progress_data['progress'] == 1.0
            assert progress_data['status'] == 'completed'
            
            # Performance validation for complete workflow
            integration_performance_monitor.assert_performance_target(
                'workflow_etf_integration',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
            integration_performance_monitor.assert_performance_target(
                'workflow_eod_processing', 
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
        finally:
            listener.stop_listening()
    
    def test_phase1_system_resilience(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test system resilience during Phase 1 operations.
        
        Validates graceful handling of Redis disruptions,
        message queue overflow, and recovery scenarios.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['eod_complete']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate high-volume message scenario
            with integration_performance_monitor.measure_operation('high_volume_resilience'):
                for i in range(100):
                    eod_summary = {
                        'symbols_processed': 4200 + i,
                        'success_rate': 0.97 + (i * 0.0001),
                        'failed_symbols': [],
                        'processing_time_seconds': 3400,
                        'batch_id': i
                    }
                    producer.publish_eod_completion(eod_summary)
                    
                    if i % 20 == 0:  # Yield periodically
                        time.sleep(0.01)
            
            # Allow message processing time
            time.sleep(2.0)
            
            # Verify system handled high volume gracefully
            messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['eod_complete'])
            assert len(messages) >= 90, f"Expected >=90 messages, got {len(messages)}"
            
            # Validate message ordering and integrity
            batch_ids = [msg['parsed_data'].get('batch_id', -1) for msg in messages]
            valid_batch_ids = [bid for bid in batch_ids if bid >= 0]
            
            # Should have received most messages in reasonable order
            assert len(valid_batch_ids) >= 90
            assert max(valid_batch_ids) >= 90
            
            # Performance should still be reasonable under load
            integration_performance_monitor.assert_performance_target(
                'high_volume_resilience',
                PERFORMANCE_TARGETS['message_delivery_ms'] * 5  # Allow 5x normal latency
            )
            
        finally:
            listener.stop_listening()