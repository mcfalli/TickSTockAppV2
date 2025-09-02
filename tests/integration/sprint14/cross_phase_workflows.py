"""
Sprint 14 Cross-Phase Workflow Integration Tests

Tests comprehensive end-to-end workflows that span multiple phases
of Sprint 14 implementation, validating complete system integration
from foundation through production optimization.

Validates:
- Phase 1→2→3→4 cascading workflows
- Cross-phase data consistency
- End-to-end performance targets
- System resilience across all phases
"""
import pytest
import json
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy import text
from typing import Dict, List, Optional, Tuple, Set

from tests.integration.sprint14.conftest import (
    SPRINT14_REDIS_CHANNELS,
    PERFORMANCE_TARGETS
)


class TestCompleteSystemWorkflow:
    """Test complete system workflow across all Sprint 14 phases"""
    
    def test_new_ipo_complete_lifecycle_workflow(
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
        Test complete IPO lifecycle across all phases.
        
        Complete Workflow:
        Phase 1: ETF Integration + EOD Processing + Historical Loading
        Phase 2: IPO Detection + Data Quality Monitoring + Equity Type Assignment
        Phase 3: Cache Universe Assignment + Test Scenario Generation
        Phase 4: Enterprise Scheduling + Market Calendar Integration
        
        End-to-end: New IPO → Complete system integration → Production monitoring
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values()) + list(SPRINT14_REDIS_CHANNELS['jobs'].values())
        listener.subscribe(all_channels)
        listener.start_listening()
        
        consumer = mock_tickstockapp_consumer(redis_client)
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # === PHASE 1: Foundation Enhancement ===
            
            # Step 1a: ETF Integration - New sector ETF detected
            new_etf_data = {
                'symbol': 'NEWTECH_ETF',
                'name': 'New Technology Sector ETF',
                'etf_type': 'sector_technology',
                'aum_millions': 2500.0,
                'expense_ratio': 0.0065,
                'underlying_index': 'Custom Tech Index'
            }
            
            with integration_performance_monitor.measure_operation('complete_workflow_etf_integration'):
                # Database insertion
                db_connection.execute(text("""
                    INSERT INTO symbols (symbol, name, type, etf_type, aum_millions, expense_ratio, underlying_index)
                    VALUES (:symbol, :name, 'ETF', :etf_type, :aum_millions, :expense_ratio, :underlying_index)
                """), new_etf_data)
                db_connection.commit()
                
                # ETF update notification
                producer.publish_etf_data_update(new_etf_data['symbol'], new_etf_data)
            
            # Step 1b: Historical Loading - Trigger backfill for new ETF
            historical_job = {
                'request_type': 'historical_backfill',
                'symbols': [new_etf_data['symbol']],
                'start_date': '2024-01-01',
                'end_date': '2024-03-31',
                'data_types': ['ohlcv_daily', 'ohlcv_1min'],
                'priority': 'medium'
            }
            
            consumer.submit_data_request(historical_job)
            
            # Step 1c: EOD Processing integration
            eod_summary = {
                'symbols_processed': 4250,  # Including new ETF
                'success_rate': 0.976,
                'failed_symbols': [],
                'processing_time_seconds': 3480,
                'new_symbols_processed': [new_etf_data['symbol']]
            }
            producer.publish_eod_completion(eod_summary)
            
            # === PHASE 2: Automation & Monitoring ===
            
            # Step 2a: IPO Detection - New company IPO
            ipo_data = sprint14_test_data.ipo_listing_data()
            ipo_data['symbol'] = 'COMPLETE_IPO'
            ipo_data['sector'] = 'Technology'  # Related to the ETF
            ipo_data['market_cap'] = 8000.0  # Mid-cap
            
            with integration_performance_monitor.measure_operation('complete_workflow_ipo_detection'):
                # IPO database insertion
                db_connection.execute(text("""
                    INSERT INTO symbols (symbol, name, type, market_cap, sector, exchange, listing_date)
                    VALUES (:symbol, :name, 'CS', :market_cap, :sector, :exchange, :listing_date)
                """), ipo_data)
                db_connection.commit()
                
                # IPO detection notification
                producer.publish_ipo_detection(ipo_data['symbol'], ipo_data)
            
            # Step 2b: Data Quality Assessment for new IPO
            ipo_quality_assessment = {
                'symbol': ipo_data['symbol'],
                'alert_type': 'new_symbol_assessment',
                'severity': 'low',
                'description': 'Initial data quality assessment for new IPO',
                'data_availability': 'good',
                'assessment_score': 0.85,
                'recommendations': ['monitor_liquidity', 'standard_processing']
            }
            producer.publish_data_quality_alert(ipo_quality_assessment)
            
            # Step 2c: Equity Type Assignment
            equity_type_assignment = {
                'symbol': ipo_data['symbol'],
                'alert_type': 'equity_type_assigned',
                'severity': 'low',
                'description': 'Equity type assigned to new IPO',
                'equity_type': 'realtime_equity',
                'assignment_reason': 'mid_cap_ipo_default',
                'processing_rules': {
                    'tick_processing': True,
                    'pattern_detection': True,
                    'quality_monitoring_enhanced': True,
                    'probation_period_days': 30
                }
            }
            producer.publish_data_quality_alert(equity_type_assignment)
            
            # === PHASE 3: Advanced Features ===
            
            # Step 3a: Cache Universe Assignment for both ETF and IPO
            cache_assignments = [
                {
                    'alert_type': 'cache_universe_expanded',
                    'severity': 'low',
                    'description': 'New technology ETF added to sector universes',
                    'universe_key': 'technology_etfs',
                    'symbols_added': [new_etf_data['symbol']],
                    'expansion_reason': 'new_sector_etf'
                },
                {
                    'alert_type': 'cache_sync_update',
                    'severity': 'low',
                    'description': 'New IPO added to technology and mid-cap universes',
                    'symbol': ipo_data['symbol'],
                    'universes_added': ['technology_stocks', 'mid_cap_stocks', 'new_listings'],
                    'change_type': 'symbol_addition'
                }
            ]
            
            for assignment in cache_assignments:
                producer.publish_data_quality_alert(assignment)
                time.sleep(0.05)
            
            # Step 3b: Test Scenario Generation
            comprehensive_test_scenario = {
                'alert_type': 'test_scenario_generated',
                'severity': 'low',
                'description': 'Generated comprehensive test for new ETF and IPO integration',
                'scenario_type': 'new_listing_integration_test',
                'scenario_id': 'complete_workflow_001',
                'parameters': {
                    'new_etf_symbol': new_etf_data['symbol'],
                    'new_ipo_symbol': ipo_data['symbol'],
                    'test_duration_days': 14,
                    'validation_scope': 'complete_integration'
                },
                'validation_targets': {
                    'etf_correlation_accuracy': 0.90,
                    'ipo_pattern_detection_rate': 0.82,
                    'universe_assignment_accuracy': 0.95,
                    'data_quality_score': 0.88
                }
            }
            producer.publish_data_quality_alert(comprehensive_test_scenario)
            
            # === PHASE 4: Production Optimization ===
            
            # Step 4a: Enterprise Scheduler handles new symbol processing
            enterprise_jobs = [
                {
                    'job_type': 'new_symbol_processing',
                    'job_id': 'enterprise_new_symbols',
                    'priority': 'high',
                    'symbols_batch': [new_etf_data['symbol'], ipo_data['symbol']],
                    'processing_type': 'comprehensive_onboarding',
                    'scheduler': 'enterprise_scheduler'
                },
                {
                    'job_type': 'universe_rebalancing',
                    'job_id': 'enterprise_rebalance',
                    'priority': 'medium',
                    'affected_universes': ['technology_stocks', 'technology_etfs'],
                    'scheduler': 'enterprise_scheduler'
                }
            ]
            
            for job in enterprise_jobs:
                consumer.submit_data_request(job)
                time.sleep(0.05)
            
            # Step 4b: Market Calendar Integration
            market_schedule_update = {
                'alert_type': 'market_calendar_update',
                'severity': 'low',
                'description': 'New listings integrated into market schedule',
                'calendar_event': 'new_listings_integration',
                'symbols_affected': [new_etf_data['symbol'], ipo_data['symbol']],
                'schedule_adjustments': {
                    'first_trading_day_monitoring': True,
                    'enhanced_pattern_detection': True,
                    'quality_monitoring_increased': True
                }
            }
            producer.publish_data_quality_alert(market_schedule_update)
            
            # === EXECUTION PHASE: Process all jobs with progress tracking ===
            
            job_ids = [
                'enterprise_new_symbols',
                'enterprise_rebalance',
                'complete_workflow_001'  # Test scenario
            ]
            
            # Execute jobs with progress updates
            for job_id in job_ids:
                progress_steps = [0.25, 0.50, 0.75, 1.0]
                for progress in progress_steps:
                    status = 'processing' if progress < 1.0 else 'completed'
                    with integration_performance_monitor.measure_operation('complete_workflow_job_execution'):
                        producer.publish_backtest_progress(job_id, progress, status)
                    time.sleep(0.1)
            
            # Pattern detection for both new symbols
            pattern_detections = [
                {
                    'symbol': new_etf_data['symbol'],
                    'pattern': 'ETF_Formation',
                    'confidence': 0.78,
                    'timeframe': '1D'
                },
                {
                    'symbol': ipo_data['symbol'],
                    'pattern': 'IPO_Breakout',
                    'confidence': 0.82,
                    'timeframe': '1D'
                }
            ]
            
            for detection in pattern_detections:
                producer.publish_pattern_event(detection)
            
            # === VALIDATION PHASE ===
            time.sleep(2.0)  # Allow complete processing
            
            # Collect all messages
            all_messages = []
            message_counts_by_channel = {}
            
            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                all_messages.extend(channel_messages)
                message_counts_by_channel[channel] = len(channel_messages)
                
            # Validate comprehensive workflow completion
            assert len(all_messages) >= 20, f"Expected ≥20 messages in complete workflow, got {len(all_messages)}"
            
            # Phase 1 Validation: ETF and EOD integration
            etf_messages = [
                msg for msg in all_messages 
                if msg.get('parsed_data', {}).get('symbol') == new_etf_data['symbol']
            ]
            assert len(etf_messages) >= 3, "ETF should appear in multiple workflow steps"
            
            eod_messages = [
                msg for msg in all_messages
                if 'eod_processing_complete' in str(msg.get('parsed_data', {}))
            ]
            assert len(eod_messages) >= 1, "EOD completion should be captured"
            
            # Phase 2 Validation: IPO and quality monitoring
            ipo_messages = [
                msg for msg in all_messages
                if msg.get('parsed_data', {}).get('symbol') == ipo_data['symbol']
            ]
            assert len(ipo_messages) >= 4, "IPO should appear in detection, quality, and equity type steps"
            
            # Phase 3 Validation: Cache and test scenarios
            cache_messages = [
                msg for msg in all_messages
                if 'cache_universe' in str(msg.get('parsed_data', {}).get('alert_type', ''))
            ]
            assert len(cache_messages) >= 2, "Cache universe updates should be present"
            
            test_scenario_messages = [
                msg for msg in all_messages
                if 'test_scenario' in str(msg.get('parsed_data', {}).get('alert_type', ''))
            ]
            assert len(test_scenario_messages) >= 1, "Test scenario generation should be captured"
            
            # Phase 4 Validation: Enterprise and market calendar
            enterprise_job_messages = [
                msg for msg in all_messages
                if msg.get('parsed_data', {}).get('scheduler') == 'enterprise_scheduler'
            ]
            assert len(enterprise_job_messages) >= 2, "Enterprise jobs should be present"
            
            # Pattern detection validation
            pattern_messages = [
                msg for msg in all_messages
                if 'pattern' in str(msg.get('parsed_data', {}))
            ]
            assert len(pattern_messages) >= 2, "Pattern detections should be captured"
            
            # Job completion validation
            completed_jobs = [
                msg for msg in all_messages
                if msg.get('parsed_data', {}).get('progress') == 1.0
            ]
            assert len(completed_jobs) >= 3, "All major jobs should complete"
            
            # Performance validation across complete workflow
            integration_performance_monitor.assert_performance_target(
                'complete_workflow_etf_integration',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
            integration_performance_monitor.assert_performance_target(
                'complete_workflow_ipo_detection',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
            # Validate database consistency
            final_symbols_check = db_connection.execute(text("""
                SELECT COUNT(*) FROM symbols 
                WHERE symbol IN (:etf_symbol, :ipo_symbol)
            """), {
                'etf_symbol': new_etf_data['symbol'],
                'ipo_symbol': ipo_data['symbol']
            })
            
            assert final_symbols_check.scalar() == 2, "Both ETF and IPO should be in database"
            
        finally:
            listener.stop_listening()
    
    def test_market_disruption_complete_system_response(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test complete system response to market disruption across all phases.
        
        Scenario: Major market disruption requires coordinated response
        across ETF monitoring, data quality, universe management, and scheduling.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values())
        listener.subscribe(all_channels)
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # === MARKET DISRUPTION EVENT ===
            disruption_trigger = {
                'alert_type': 'market_disruption_detected',
                'severity': 'high',
                'description': 'Major market disruption detected - coordinated system response',
                'disruption_type': 'flash_crash_recovery',
                'market_impact': {
                    'sp500_decline_percent': -15.2,
                    'vix_spike': 68.5,
                    'volume_surge_multiplier': 4.8,
                    'circuit_breakers_triggered': True
                },
                'response_coordination_required': True
            }
            
            with integration_performance_monitor.measure_operation('market_disruption_coordination'):
                producer.publish_data_quality_alert(disruption_trigger)
            
            # === PHASE 1 RESPONSE: ETF and EOD Adjustments ===
            
            # ETF correlation breakdown detection
            etf_responses = [
                {
                    'symbol': 'SPY',
                    'correlation_reference': 'SPY',
                    'correlation_coefficient': 0.45,  # Massive correlation breakdown
                    'correlation_strength': 'severely_disrupted',
                    'emergency_monitoring': True
                },
                {
                    'symbol': 'QQQ',
                    'correlation_reference': 'SPY', 
                    'correlation_coefficient': 0.32,
                    'correlation_strength': 'severely_disrupted',
                    'emergency_monitoring': True
                }
            ]
            
            for etf in etf_responses:
                producer.publish_etf_data_update(etf['symbol'], etf)
            
            # Emergency EOD processing
            emergency_eod = {
                'symbols_processed': 4200,
                'success_rate': 0.891,  # Lower due to market chaos
                'failed_symbols': ['HALTED_1', 'HALTED_2', 'SUSPENDED_1'],
                'processing_time_seconds': 4800,  # Longer due to disruption
                'emergency_processing': True,
                'market_condition': 'severe_disruption'
            }
            producer.publish_eod_completion(emergency_eod)
            
            # === PHASE 2 RESPONSE: Quality Monitoring and IPO Impact ===
            
            # Massive data quality alerts
            quality_alerts = [
                {
                    'symbol': 'VOLATILE_STOCK',
                    'alert_type': 'extreme_price_movement',
                    'severity': 'critical',
                    'description': 'Stock down 45% in 10 minutes',
                    'price_change_percent': -45.2,
                    'volume_surge': 8.5,
                    'circuit_breaker_hit': True
                },
                {
                    'symbol': 'GAPPED_STOCK',
                    'alert_type': 'trading_halt_data_gap',
                    'severity': 'high',
                    'description': 'Trading halt causing data gaps',
                    'halt_duration_minutes': 30,
                    'gap_handling': 'fmv_approximation_active'
                }
            ]
            
            for alert in quality_alerts:
                producer.publish_data_quality_alert(alert)
            
            # IPO postponement notifications
            ipo_disruption = {
                'symbol': 'POSTPONED_IPO',
                'alert_type': 'ipo_postponement',
                'severity': 'medium',
                'description': 'IPO postponed due to market volatility',
                'postponement_reason': 'market_disruption',
                'new_tentative_date': '2024-02-15'
            }
            producer.publish_data_quality_alert(ipo_disruption)
            
            # === PHASE 3 RESPONSE: Universe Rebalancing and Scenarios ===
            
            # Emergency universe rebalancing
            universe_rebalancing = [
                {
                    'alert_type': 'emergency_universe_rebalance',
                    'severity': 'high',
                    'description': 'Emergency rebalancing of volatility-based universes',
                    'universe_key': 'high_volatility_stocks',
                    'symbols_added': 450,
                    'symbols_removed': 120,
                    'rebalancing_trigger': 'market_disruption'
                },
                {
                    'alert_type': 'universe_hierarchy_updated',
                    'severity': 'medium',
                    'description': 'Safe haven universe expanded during disruption',
                    'parent_universe': 'defensive_assets',
                    'child_universes': ['treasury_etfs', 'gold_etfs', 'utility_stocks'],
                    'expansion_reason': 'market_disruption_response'
                }
            ]
            
            for rebalance in universe_rebalancing:
                producer.publish_data_quality_alert(rebalance)
            
            # Emergency test scenario generation
            disruption_test = {
                'alert_type': 'test_scenario_generated',
                'severity': 'high',
                'description': 'Generated market disruption stress test scenario',
                'scenario_type': 'market_disruption_stress_test',
                'scenario_id': 'disruption_stress_001',
                'parameters': {
                    'disruption_magnitude': 'severe',
                    'recovery_time_estimate_hours': 6,
                    'system_resilience_test': True
                }
            }
            producer.publish_data_quality_alert(disruption_test)
            
            # === PHASE 4 RESPONSE: Emergency Scheduling and Calendar ===
            
            # Enterprise scheduler emergency mode
            emergency_scheduling = {
                'alert_type': 'enterprise_emergency_mode',
                'severity': 'critical',
                'description': 'Enterprise scheduler activated emergency response mode',
                'emergency_protocols': {
                    'critical_jobs_only': True,
                    'processing_priority_elevated': True,
                    'background_jobs_suspended': True,
                    'resource_allocation_maximized': True
                },
                'estimated_emergency_duration_hours': 4
            }
            producer.publish_data_quality_alert(emergency_scheduling)
            
            # Market calendar disruption adjustment
            calendar_disruption = {
                'alert_type': 'market_calendar_disruption',
                'severity': 'high',
                'description': 'Market calendar adjusted for disruption response',
                'disruption_adjustments': {
                    'extended_monitoring_hours': True,
                    'weekend_emergency_processing': True,
                    'holiday_processing_override': True,
                    'emergency_notification_channels': 'activated'
                }
            }
            producer.publish_data_quality_alert(calendar_disruption)
            
            # === COORDINATED RESPONSE EXECUTION ===
            
            # System-wide coordination jobs
            coordination_jobs = [
                'emergency_correlation_recalc',
                'volatility_universe_rebuild', 
                'data_quality_emergency_scan',
                'pattern_detection_recalibration'
            ]
            
            for job_id in coordination_jobs:
                # Rapid execution under emergency conditions
                progress_steps = [0.4, 0.8, 1.0]  # Fewer steps, faster execution
                for progress in progress_steps:
                    status = 'emergency_processing' if progress < 1.0 else 'emergency_completed'
                    producer.publish_backtest_progress(job_id, progress, status)
                    time.sleep(0.05)  # Very fast execution
            
            # Pattern detection under extreme conditions
            extreme_patterns = [
                {
                    'symbol': 'CRASH_STOCK',
                    'pattern': 'Extreme_Bearish_Engulfing',
                    'confidence': 0.95,
                    'market_condition': 'severe_disruption'
                },
                {
                    'symbol': 'RECOVERY_STOCK',
                    'pattern': 'Hammer',
                    'confidence': 0.88,
                    'market_condition': 'disruption_recovery'
                }
            ]
            
            for pattern in extreme_patterns:
                producer.publish_pattern_event(pattern)
            
            # === VALIDATION OF COORDINATED RESPONSE ===
            time.sleep(2.5)  # Allow emergency processing
            
            # Collect all disruption response messages
            all_messages = []
            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                all_messages.extend(channel_messages)
            
            # Should handle substantial emergency message volume
            assert len(all_messages) >= 25, f"Expected ≥25 emergency messages, got {len(all_messages)}"
            
            # Validate market disruption detection
            disruption_messages = [
                msg for msg in all_messages
                if 'disruption' in str(msg.get('parsed_data', {}))
            ]
            assert len(disruption_messages) >= 5, "Should capture multiple disruption responses"
            
            # Validate emergency mode activation
            emergency_messages = [
                msg for msg in all_messages
                if 'emergency' in str(msg.get('parsed_data', {}))
            ]
            assert len(emergency_messages) >= 4, "Should activate emergency protocols"
            
            # Validate ETF correlation breakdown detection
            etf_correlation_messages = [
                msg for msg in all_messages
                if msg.get('parsed_data', {}).get('correlation_strength') == 'severely_disrupted'
            ]
            assert len(etf_correlation_messages) >= 2, "Should detect ETF correlation breakdown"
            
            # Validate extreme pattern detection
            extreme_pattern_messages = [
                msg for msg in all_messages
                if 'Extreme' in str(msg.get('parsed_data', {}).get('pattern', ''))
            ]
            assert len(extreme_pattern_messages) >= 1, "Should detect extreme patterns"
            
            # Validate emergency job completion
            emergency_completed_jobs = [
                msg for msg in all_messages
                if msg.get('parsed_data', {}).get('status') == 'emergency_completed'
            ]
            assert len(emergency_completed_jobs) >= 4, "Emergency jobs should complete"
            
            # Performance validation - should maintain responsiveness even under extreme load
            integration_performance_monitor.assert_performance_target(
                'market_disruption_coordination',
                PERFORMANCE_TARGETS['message_delivery_ms'] * 2  # Allow 2x latency under emergency
            )
            
        finally:
            listener.stop_listening()


class TestSystemWideConsistencyValidation:
    """Test system-wide data consistency across all phases"""
    
    def test_cross_phase_data_consistency(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test data consistency across all phases of Sprint 14.
        
        Validates that data remains consistent as it flows through
        all phases and that no data corruption occurs during
        cross-system integration.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values())
        listener.subscribe(all_channels)
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        # Track symbols and their data across phases
        consistency_tracking = {
            'symbols': {},
            'universes': {},
            'jobs': {},
            'patterns': {}
        }
        
        try:
            # === CONSISTENCY TEST SETUP ===
            
            # Create test symbols for consistency tracking
            test_symbols = [
                {
                    'symbol': 'CONSIST_STOCK',
                    'name': 'Consistency Test Stock',
                    'type': 'CS',
                    'market_cap': 5000.0,
                    'sector': 'Technology'
                },
                {
                    'symbol': 'CONSIST_ETF',
                    'name': 'Consistency Test ETF',
                    'type': 'ETF',
                    'etf_type': 'equity_growth',
                    'aum_millions': 3500.0,
                    'expense_ratio': 0.0055
                }
            ]
            
            # Insert test symbols into database
            for symbol in test_symbols:
                if symbol['type'] == 'CS':
                    db_connection.execute(text("""
                        INSERT INTO symbols (symbol, name, type, market_cap, sector)
                        VALUES (:symbol, :name, :type, :market_cap, :sector)
                    """), symbol)
                else:
                    db_connection.execute(text("""
                        INSERT INTO symbols (symbol, name, type, etf_type, aum_millions, expense_ratio)
                        VALUES (:symbol, :name, :type, :etf_type, :aum_millions, :expense_ratio)
                    """), symbol)
                consistency_tracking['symbols'][symbol['symbol']] = symbol
            
            db_connection.commit()
            
            # === PHASE 1: Foundation Data Flow ===
            
            # ETF update with specific data
            etf_update_data = {
                'symbol': 'CONSIST_ETF',
                'aum_millions': 3500.0,
                'expense_ratio': 0.0055,
                'correlation_coefficient': 0.82,
                'tracking_id': 'consist_001'
            }
            
            with integration_performance_monitor.measure_operation('consistency_etf_update'):
                producer.publish_etf_data_update('CONSIST_ETF', etf_update_data)
            
            # Historical loading completion
            historical_completion_data = {
                'symbols_processed': 2,
                'success_rate': 1.0,
                'failed_symbols': [],
                'processing_time_seconds': 180,
                'specific_symbols': ['CONSIST_STOCK', 'CONSIST_ETF'],
                'tracking_id': 'consist_001'
            }
            producer.publish_eod_completion(historical_completion_data)
            
            # === PHASE 2: Quality and Classification ===
            
            # Data quality assessment for stock
            stock_quality_data = {
                'symbol': 'CONSIST_STOCK',
                'alert_type': 'data_quality_assessment',
                'severity': 'low',
                'description': 'Consistency test - data quality validated',
                'assessment_score': 0.91,
                'data_completeness': 0.98,
                'tracking_id': 'consist_001'
            }
            producer.publish_data_quality_alert(stock_quality_data)
            
            # Equity type assignment
            equity_type_data = {
                'symbol': 'CONSIST_STOCK',
                'alert_type': 'equity_type_assigned',
                'severity': 'low',
                'description': 'Consistency test - equity type assigned',
                'equity_type': 'realtime_equity',
                'processing_rules': {
                    'tick_processing': True,
                    'pattern_detection': True
                },
                'tracking_id': 'consist_001'
            }
            producer.publish_data_quality_alert(equity_type_data)
            
            # === PHASE 3: Universe and Scenarios ===
            
            # Cache universe assignments
            universe_assignments = [
                {
                    'alert_type': 'cache_sync_update',
                    'severity': 'low',
                    'description': 'Consistency test - stock universe assignment',
                    'symbol': 'CONSIST_STOCK',
                    'universes_added': ['technology_stocks', 'mid_cap_stocks'],
                    'tracking_id': 'consist_001'
                },
                {
                    'alert_type': 'cache_sync_update',
                    'severity': 'low',
                    'description': 'Consistency test - ETF universe assignment',
                    'symbol': 'CONSIST_ETF',
                    'universes_added': ['equity_etfs', 'growth_etfs'],
                    'tracking_id': 'consist_001'
                }
            ]
            
            for assignment in universe_assignments:
                producer.publish_data_quality_alert(assignment)
            
            # Test scenario with both symbols
            test_scenario_data = {
                'alert_type': 'test_scenario_generated',
                'severity': 'low',
                'description': 'Consistency test scenario generated',
                'scenario_type': 'consistency_validation',
                'scenario_id': 'consist_test_001',
                'parameters': {
                    'test_symbols': ['CONSIST_STOCK', 'CONSIST_ETF'],
                    'validation_scope': 'cross_phase_consistency'
                },
                'tracking_id': 'consist_001'
            }
            producer.publish_data_quality_alert(test_scenario_data)
            
            # === PHASE 4: Enterprise and Schedule ===
            
            # Enterprise job processing both symbols
            enterprise_job_data = {
                'alert_type': 'enterprise_job_summary',
                'severity': 'low',
                'description': 'Consistency test - enterprise processing completed',
                'job_type': 'consistency_validation',
                'symbols_processed': ['CONSIST_STOCK', 'CONSIST_ETF'],
                'processing_results': {
                    'CONSIST_STOCK': {'status': 'success', 'score': 0.91},
                    'CONSIST_ETF': {'status': 'success', 'score': 0.87}
                },
                'tracking_id': 'consist_001'
            }
            producer.publish_data_quality_alert(enterprise_job_data)
            
            # Pattern detection for both symbols
            pattern_detections = [
                {
                    'symbol': 'CONSIST_STOCK',
                    'pattern': 'Doji',
                    'confidence': 0.85,
                    'tracking_id': 'consist_001'
                },
                {
                    'symbol': 'CONSIST_ETF',
                    'pattern': 'Bullish_Engulfing',
                    'confidence': 0.79,
                    'tracking_id': 'consist_001'
                }
            ]
            
            for pattern in pattern_detections:
                producer.publish_pattern_event(pattern)
            
            # === CONSISTENCY VALIDATION ===
            time.sleep(1.5)  # Allow all processing
            
            # Collect all messages for consistency analysis
            all_messages = []
            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                all_messages.extend(channel_messages)
            
            # Filter messages with tracking_id for consistency validation
            tracked_messages = [
                msg for msg in all_messages
                if msg.get('parsed_data', {}).get('tracking_id') == 'consist_001'
            ]
            
            # Should have consistent tracking across all phases
            assert len(tracked_messages) >= 8, f"Expected ≥8 tracked messages, got {len(tracked_messages)}"
            
            # Validate symbol consistency across phases
            symbols_in_messages = set()
            for msg in tracked_messages:
                data = msg.get('parsed_data', {})
                if 'symbol' in data:
                    symbols_in_messages.add(data['symbol'])
                elif 'test_symbols' in data.get('parameters', {}):
                    symbols_in_messages.update(data['parameters']['test_symbols'])
                elif 'symbols_processed' in data:
                    if isinstance(data['symbols_processed'], list):
                        symbols_in_messages.update(data['symbols_processed'])
            
            expected_symbols = {'CONSIST_STOCK', 'CONSIST_ETF'}
            assert expected_symbols.issubset(symbols_in_messages), "Symbols should be consistent across all phases"
            
            # Validate data value consistency
            etf_aum_values = []
            stock_assessment_scores = []
            
            for msg in tracked_messages:
                data = msg.get('parsed_data', {})
                if data.get('symbol') == 'CONSIST_ETF' and 'aum_millions' in data:
                    etf_aum_values.append(data['aum_millions'])
                elif data.get('symbol') == 'CONSIST_STOCK' and 'assessment_score' in data:
                    stock_assessment_scores.append(data['assessment_score'])
            
            # ETF AUM should be consistent
            if etf_aum_values:
                assert all(aum == 3500.0 for aum in etf_aum_values), "ETF AUM values should be consistent"
            
            # Stock assessment scores should be consistent
            if stock_assessment_scores:
                assert all(score == 0.91 for score in stock_assessment_scores), "Assessment scores should be consistent"
            
            # Validate database consistency
            final_db_check = db_connection.execute(text("""
                SELECT symbol, 
                       CASE WHEN type = 'ETF' THEN aum_millions ELSE market_cap END as value,
                       CASE WHEN type = 'ETF' THEN expense_ratio ELSE NULL END as secondary_value
                FROM symbols 
                WHERE symbol IN ('CONSIST_STOCK', 'CONSIST_ETF')
                ORDER BY symbol
            """))
            
            db_results = final_db_check.fetchall()
            assert len(db_results) == 2, "Both test symbols should remain in database"
            
            # Verify database values match message data
            for row in db_results:
                symbol, value, secondary = row
                if symbol == 'CONSIST_ETF':
                    assert float(value) == 3500.0, "Database ETF AUM should match message data"
                    assert float(secondary or 0) == 0.0055, "Database expense ratio should match"
                elif symbol == 'CONSIST_STOCK':
                    assert float(value) == 5000.0, "Database market cap should be preserved"
            
            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'consistency_etf_update',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
        finally:
            listener.stop_listening()


class TestSystemScalabilityValidation:
    """Test system scalability across all Sprint 14 phases"""
    
    def test_high_volume_cross_phase_scalability(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test system scalability under high volume across all phases.
        
        Simulates high-volume market day with:
        - 100+ ETF updates
        - 50+ IPO detections  
        - 500+ data quality alerts
        - 1000+ pattern detections
        - 200+ enterprise jobs
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values())
        listener.subscribe(all_channels)
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # === HIGH VOLUME SIMULATION ===
            
            total_messages_generated = 0
            
            with integration_performance_monitor.measure_operation('high_volume_scalability_test'):
                
                # Phase 1: High volume ETF updates
                for i in range(100):
                    etf_data = {
                        'symbol': f'SCALE_ETF_{i:03d}',
                        'aum_millions': 1000.0 + (i * 50),
                        'expense_ratio': 0.005 + (i * 0.0001),
                        'batch_id': 'scalability_001'
                    }
                    producer.publish_etf_data_update(etf_data['symbol'], etf_data)
                    total_messages_generated += 1
                    
                    if i % 25 == 0:  # Brief pause every 25 messages
                        time.sleep(0.01)
                
                # Phase 1: EOD processing under load
                for i in range(10):
                    eod_data = {
                        'symbols_processed': 4200 + i,
                        'success_rate': 0.97 - (i * 0.001),
                        'processing_time_seconds': 3600 + (i * 100),
                        'batch_processing': True,
                        'batch_id': f'eod_batch_{i}'
                    }
                    producer.publish_eod_completion(eod_data)
                    total_messages_generated += 1
                
                # Phase 2: High volume IPO detections
                for i in range(50):
                    ipo_data = {
                        'symbol': f'SCALE_IPO_{i:03d}',
                        'listing_date': '2024-01-15',
                        'market_cap': 500.0 + (i * 100),
                        'sector': ['Technology', 'Healthcare', 'Financial'][i % 3],
                        'batch_id': 'scalability_001'
                    }
                    producer.publish_ipo_detection(ipo_data['symbol'], ipo_data)
                    total_messages_generated += 1
                
                # Phase 2: Massive data quality alerts
                for i in range(500):
                    quality_alert = {
                        'symbol': f'SCALE_STOCK_{i:04d}',
                        'alert_type': 'routine_quality_check',
                        'severity': 'low',
                        'description': f'Scalability test alert #{i}',
                        'quality_score': 0.8 + (i * 0.0004),
                        'batch_id': 'scalability_001'
                    }
                    producer.publish_data_quality_alert(quality_alert)
                    total_messages_generated += 1
                    
                    if i % 100 == 0:  # Brief pause every 100 messages
                        time.sleep(0.01)
                
                # Phase 3: Universe assignments and test scenarios
                for i in range(25):
                    universe_update = {
                        'alert_type': 'cache_universe_expanded',
                        'severity': 'low',
                        'description': f'Scalability universe update #{i}',
                        'universe_key': f'scale_universe_{i}',
                        'symbol_count': 50 + i,
                        'batch_id': 'scalability_001'
                    }
                    producer.publish_data_quality_alert(universe_update)
                    total_messages_generated += 1
                
                # Test scenarios under load
                for i in range(10):
                    test_scenario = {
                        'alert_type': 'test_scenario_generated',
                        'severity': 'low',
                        'description': f'Scalability test scenario #{i}',
                        'scenario_type': 'scalability_test',
                        'scenario_id': f'scale_test_{i:03d}',
                        'batch_id': 'scalability_001'
                    }
                    producer.publish_data_quality_alert(test_scenario)
                    total_messages_generated += 1
                
                # Phase 4: Enterprise job load and pattern detections
                for i in range(200):
                    # Alternate between job status and enterprise monitoring
                    if i % 2 == 0:
                        job_status = {
                            'alert_type': 'job_queue_status',
                            'severity': 'low',
                            'description': f'Enterprise queue update #{i}',
                            'queue_metrics': {
                                'pending_jobs': 10 + (i % 20),
                                'processing_jobs': min(5, i % 10),
                                'load_factor': 0.5 + (i * 0.002)
                            },
                            'batch_id': 'scalability_001'
                        }
                        producer.publish_data_quality_alert(job_status)
                    else:
                        # Job progress updates
                        producer.publish_backtest_progress(
                            f'scale_job_{i:03d}',
                            min(1.0, 0.1 * (i % 10)),
                            'processing' if i % 10 < 9 else 'completed'
                        )
                    
                    total_messages_generated += 1
                
                # High volume pattern detections
                for i in range(1000):
                    pattern_data = {
                        'symbol': f'PATTERN_STOCK_{i:04d}',
                        'pattern': ['Doji', 'Hammer', 'Engulfing', 'Star'][i % 4],
                        'confidence': 0.7 + (i * 0.0003),
                        'batch_id': 'scalability_001'
                    }
                    producer.publish_pattern_event(pattern_data)
                    total_messages_generated += 1
                    
                    if i % 200 == 0:  # Brief pause every 200 patterns
                        time.sleep(0.01)
            
            # === SCALABILITY VALIDATION ===
            
            # Allow substantial processing time for high volume
            time.sleep(5.0)
            
            # Collect all messages
            all_messages = []
            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                all_messages.extend(channel_messages)
            
            messages_received = len(all_messages)
            
            # Validate high-volume message handling
            message_retention_rate = messages_received / total_messages_generated if total_messages_generated > 0 else 0
            
            # Should retain substantial percentage of messages despite volume
            assert message_retention_rate >= 0.85, (
                f"Message retention rate {message_retention_rate:.2%} too low for scalability. "
                f"Generated: {total_messages_generated}, Received: {messages_received}"
            )
            
            # Validate message diversity under load
            batch_ids = set()
            alert_types = set()
            symbols = set()
            
            for msg in all_messages:
                data = msg.get('parsed_data', {})
                if 'batch_id' in data:
                    batch_ids.add(data['batch_id'])
                if 'alert_type' in data:
                    alert_types.add(data['alert_type'])
                elif 'event_type' in data:
                    alert_types.add(data['event_type'])
                if 'symbol' in data:
                    symbols.add(data['symbol'])
            
            # Should maintain message diversity
            assert len(alert_types) >= 8, f"Expected diverse message types, got {len(alert_types)}"
            assert len(symbols) >= 100, f"Expected diverse symbols, got {len(symbols)}"
            
            # Validate phase representation
            phase1_messages = len([
                msg for msg in all_messages
                if any(phrase in str(msg.get('parsed_data', {})) for phrase in ['etf', 'eod'])
            ])
            phase2_messages = len([
                msg for msg in all_messages  
                if any(phrase in str(msg.get('parsed_data', {})) for phrase in ['ipo', 'quality'])
            ])
            phase3_messages = len([
                msg for msg in all_messages
                if any(phrase in str(msg.get('parsed_data', {})) for phrase in ['universe', 'scenario'])
            ])
            phase4_messages = len([
                msg for msg in all_messages
                if any(phrase in str(msg.get('parsed_data', {})) for phrase in ['job_queue', 'enterprise'])
            ])
            
            # All phases should be represented under load
            assert phase1_messages >= 80, f"Phase 1 under-represented: {phase1_messages}"
            assert phase2_messages >= 400, f"Phase 2 under-represented: {phase2_messages}" 
            assert phase3_messages >= 25, f"Phase 3 under-represented: {phase3_messages}"
            assert phase4_messages >= 80, f"Phase 4 under-represented: {phase4_messages}"
            
            # Performance validation - should maintain reasonable performance under load
            integration_performance_monitor.assert_performance_target(
                'high_volume_scalability_test',
                PERFORMANCE_TARGETS['end_to_end_workflow_ms'] * 10  # Allow 10x latency under extreme load
            )
            
            print(f"Scalability Test Results:")
            print(f"  Total messages generated: {total_messages_generated}")
            print(f"  Total messages received: {messages_received}")
            print(f"  Message retention rate: {message_retention_rate:.1%}")
            print(f"  Message types detected: {len(alert_types)}")
            print(f"  Unique symbols processed: {len(symbols)}")
            print(f"  Phase distribution: P1={phase1_messages}, P2={phase2_messages}, P3={phase3_messages}, P4={phase4_messages}")
            
        finally:
            listener.stop_listening()

    def test_concurrent_phase_operations_scalability(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test concurrent operations across all phases simultaneously.
        
        Simulates realistic concurrent operations where all phases
        are active simultaneously rather than sequentially.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values())
        listener.subscribe(all_channels)
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Define concurrent operation threads
            operation_threads = []
            thread_results = {'messages_sent': 0, 'errors': 0}
            
            def phase1_operations():
                """Concurrent Phase 1 operations"""
                try:
                    for i in range(20):
                        # ETF updates
                        etf_data = {
                            'symbol': f'CONCURRENT_ETF_{i:02d}',
                            'aum_millions': 2000.0 + i * 100,
                            'thread_id': 'phase1_thread'
                        }
                        producer.publish_etf_data_update(etf_data['symbol'], etf_data)
                        
                        # EOD completions
                        if i % 5 == 0:
                            eod_data = {
                                'symbols_processed': 4000 + i,
                                'success_rate': 0.97,
                                'thread_id': 'phase1_thread'
                            }
                            producer.publish_eod_completion(eod_data)
                        
                        thread_results['messages_sent'] += 1
                        time.sleep(0.02)
                except Exception as e:
                    thread_results['errors'] += 1
                    print(f"Phase 1 thread error: {e}")
            
            def phase2_operations():
                """Concurrent Phase 2 operations"""
                try:
                    for i in range(30):
                        # IPO detections
                        if i % 3 == 0:
                            ipo_data = {
                                'symbol': f'CONCURRENT_IPO_{i:02d}',
                                'market_cap': 1000.0 + i * 200,
                                'thread_id': 'phase2_thread'
                            }
                            producer.publish_ipo_detection(ipo_data['symbol'], ipo_data)
                        
                        # Quality alerts
                        quality_alert = {
                            'symbol': f'CONCURRENT_QUAL_{i:02d}',
                            'alert_type': 'concurrent_quality_check',
                            'severity': 'low',
                            'thread_id': 'phase2_thread'
                        }
                        producer.publish_data_quality_alert(quality_alert)
                        
                        thread_results['messages_sent'] += 1
                        time.sleep(0.015)
                except Exception as e:
                    thread_results['errors'] += 1
                    print(f"Phase 2 thread error: {e}")
            
            def phase3_operations():
                """Concurrent Phase 3 operations"""
                try:
                    for i in range(15):
                        # Universe updates
                        universe_update = {
                            'alert_type': 'cache_universe_expanded',
                            'severity': 'low',
                            'universe_key': f'concurrent_universe_{i}',
                            'symbol_count': 25 + i,
                            'thread_id': 'phase3_thread'
                        }
                        producer.publish_data_quality_alert(universe_update)
                        
                        # Test scenarios
                        if i % 3 == 0:
                            test_scenario = {
                                'alert_type': 'test_scenario_generated',
                                'scenario_type': 'concurrent_test',
                                'scenario_id': f'concurrent_{i:02d}',
                                'thread_id': 'phase3_thread'
                            }
                            producer.publish_data_quality_alert(test_scenario)
                        
                        thread_results['messages_sent'] += 1
                        time.sleep(0.03)
                except Exception as e:
                    thread_results['errors'] += 1
                    print(f"Phase 3 thread error: {e}")
            
            def phase4_operations():
                """Concurrent Phase 4 operations"""
                try:
                    for i in range(25):
                        # Enterprise job monitoring
                        job_update = {
                            'alert_type': 'job_queue_status',
                            'severity': 'low',
                            'queue_metrics': {
                                'pending_jobs': 5 + (i % 10),
                                'concurrent_thread': True
                            },
                            'thread_id': 'phase4_thread'
                        }
                        producer.publish_data_quality_alert(job_update)
                        
                        # Job progress
                        producer.publish_backtest_progress(
                            f'concurrent_job_{i:02d}',
                            min(1.0, 0.2 * (i % 5)),
                            'processing' if i % 5 < 4 else 'completed'
                        )
                        
                        thread_results['messages_sent'] += 1
                        time.sleep(0.025)
                except Exception as e:
                    thread_results['errors'] += 1
                    print(f"Phase 4 thread error: {e}")
            
            def pattern_operations():
                """Concurrent pattern detection across all phases"""
                try:
                    for i in range(100):
                        pattern_data = {
                            'symbol': f'CONCURRENT_PATTERN_{i:03d}',
                            'pattern': ['Doji', 'Hammer', 'Engulfing'][i % 3],
                            'confidence': 0.75 + (i * 0.002),
                            'thread_id': 'pattern_thread'
                        }
                        producer.publish_pattern_event(pattern_data)
                        thread_results['messages_sent'] += 1
                        time.sleep(0.01)
                except Exception as e:
                    thread_results['errors'] += 1
                    print(f"Pattern thread error: {e}")
            
            # === EXECUTE CONCURRENT OPERATIONS ===
            
            with integration_performance_monitor.measure_operation('concurrent_phase_operations'):
                
                # Start all operation threads simultaneously
                threads = [
                    threading.Thread(target=phase1_operations, name='Phase1'),
                    threading.Thread(target=phase2_operations, name='Phase2'), 
                    threading.Thread(target=phase3_operations, name='Phase3'),
                    threading.Thread(target=phase4_operations, name='Phase4'),
                    threading.Thread(target=pattern_operations, name='Patterns')
                ]
                
                # Start all threads
                start_time = time.time()
                for thread in threads:
                    thread.start()
                
                # Wait for all threads to complete
                for thread in threads:
                    thread.join(timeout=10.0)  # 10 second timeout per thread
                
                execution_time = time.time() - start_time
            
            # === CONCURRENT OPERATION VALIDATION ===
            
            # Allow processing time
            time.sleep(2.0)
            
            # Collect messages from all channels
            all_messages = []
            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                all_messages.extend(channel_messages)
            
            # Validate concurrent operation results
            total_messages_sent = thread_results['messages_sent']
            total_messages_received = len(all_messages)
            
            assert thread_results['errors'] == 0, f"Encountered {thread_results['errors']} thread errors"
            assert total_messages_sent > 0, "Should have sent messages from concurrent operations"
            
            # Validate message retention under concurrency
            retention_rate = total_messages_received / total_messages_sent if total_messages_sent > 0 else 0
            assert retention_rate >= 0.80, (
                f"Concurrent message retention {retention_rate:.1%} too low. "
                f"Sent: {total_messages_sent}, Received: {total_messages_received}"
            )
            
            # Validate thread representation
            thread_ids = set()
            phase_representation = {'phase1': 0, 'phase2': 0, 'phase3': 0, 'phase4': 0, 'patterns': 0}
            
            for msg in all_messages:
                data = msg.get('parsed_data', {})
                if 'thread_id' in data:
                    thread_ids.add(data['thread_id'])
                    
                    # Count phase representation
                    if 'phase1' in data['thread_id']:
                        phase_representation['phase1'] += 1
                    elif 'phase2' in data['thread_id']:
                        phase_representation['phase2'] += 1
                    elif 'phase3' in data['thread_id']:
                        phase_representation['phase3'] += 1
                    elif 'phase4' in data['thread_id']:
                        phase_representation['phase4'] += 1
                    elif 'pattern' in data['thread_id']:
                        phase_representation['patterns'] += 1
            
            # All threads should be represented
            assert len(thread_ids) >= 4, f"Expected ≥4 thread IDs, got {len(thread_ids)}: {thread_ids}"
            
            # Each phase should have reasonable representation
            for phase, count in phase_representation.items():
                assert count > 0, f"Phase {phase} not represented in concurrent operations"
            
            # Performance validation
            assert execution_time < 15.0, f"Concurrent execution took {execution_time:.1f}s, expected <15s"
            
            integration_performance_monitor.assert_performance_target(
                'concurrent_phase_operations',
                PERFORMANCE_TARGETS['end_to_end_workflow_ms'] * 5  # Allow 5x latency for concurrency
            )
            
            print(f"Concurrent Operations Results:")
            print(f"  Execution time: {execution_time:.1f}s")
            print(f"  Messages sent: {total_messages_sent}")
            print(f"  Messages received: {total_messages_received}")
            print(f"  Retention rate: {retention_rate:.1%}")
            print(f"  Thread representation: {len(thread_ids)} threads")
            print(f"  Phase distribution: {phase_representation}")
            print(f"  Thread errors: {thread_results['errors']}")
            
        finally:
            listener.stop_listening()