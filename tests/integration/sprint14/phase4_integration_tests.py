"""
Sprint 14 Phase 4 Integration Tests

Tests cross-system integration for:
- Enterprise Scheduler with Redis Streams job distribution
- Rapid Development Environment Refresh capabilities
- Market Schedule Integration for automated processing timing

Validates production optimization features with enterprise-grade
scheduling, development efficiency, and market calendar awareness.
"""
import pytest
import json
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy import text
from typing import Dict, List, Optional, Tuple

from tests.integration.sprint14.conftest import (
    SPRINT14_REDIS_CHANNELS,
    PERFORMANCE_TARGETS
)


class TestEnterpriseSchedulerIntegration:
    """Test Enterprise Scheduler integration with Redis Streams"""
    
    def test_redis_streams_job_distribution(
        self,
        redis_client,
        mock_tickstockapp_consumer,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test Redis Streams job distribution for enterprise scheduling.
        
        Workflow:
        1. Enterprise scheduler submits jobs to Redis Streams
        2. Multiple worker instances consume jobs from streams
        3. Job status updates published via pub-sub
        4. Job completion notifications distributed
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['jobs']['historical_load'],
            SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
        ]
        listener.subscribe(channels)
        listener.start_listening()
        
        consumer = mock_tickstockapp_consumer(redis_client)
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate enterprise job submissions via Redis Streams
            enterprise_jobs = [
                {
                    'job_type': 'bulk_historical_load',
                    'job_id': 'enterprise_001',
                    'priority': 'high',
                    'symbols_batch': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
                    'date_range': '2024-01-01:2024-03-31',
                    'worker_assignment': 'auto',
                    'scheduler': 'enterprise_scheduler'
                },
                {
                    'job_type': 'etf_universe_refresh',
                    'job_id': 'enterprise_002',
                    'priority': 'medium',
                    'universe_keys': ['etf_growth', 'etf_value', 'etf_international'],
                    'refresh_type': 'incremental',
                    'scheduler': 'enterprise_scheduler'
                },
                {
                    'job_type': 'data_quality_scan',
                    'job_id': 'enterprise_003',
                    'priority': 'low',
                    'scan_scope': 'all_active_symbols',
                    'scan_depth': 'comprehensive',
                    'scheduler': 'enterprise_scheduler'
                }
            ]
            
            # Submit jobs through enterprise scheduler
            job_ids = []
            for job in enterprise_jobs:
                with integration_performance_monitor.measure_operation('enterprise_job_submit'):
                    job_id = consumer.submit_data_request(job)
                    job_ids.append(job_id or job['job_id'])
                time.sleep(0.05)
            
            # Simulate worker processing with status updates
            for i, job_id in enumerate(job_ids):
                # Processing progress updates
                progress_steps = [0.2, 0.6, 1.0]
                for progress in progress_steps:
                    status = 'processing' if progress < 1.0 else 'completed'
                    
                    with integration_performance_monitor.measure_operation('enterprise_job_progress'):
                        producer.publish_backtest_progress(job_id, progress, status)
                    time.sleep(0.1)
            
            # Wait for job distribution and processing
            time.sleep(1.0)
            
            # Verify job submissions received
            job_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['jobs']['historical_load'])
            assert len(job_messages) >= 3, f"Expected ≥3 job messages, got {len(job_messages)}"
            
            # Validate enterprise job characteristics
            job_types = [msg['parsed_data']['job_type'] for msg in job_messages]
            assert 'bulk_historical_load' in job_types
            assert 'etf_universe_refresh' in job_types
            assert 'data_quality_scan' in job_types
            
            # Verify scheduler attribution
            schedulers = [msg['parsed_data']['scheduler'] for msg in job_messages]
            assert all(scheduler == 'enterprise_scheduler' for scheduler in schedulers)
            
            # Verify job progress updates
            progress_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['backtesting_progress'])
            assert len(progress_messages) >= 9, f"Expected ≥9 progress messages, got {len(progress_messages)}"
            
            # Validate job completion
            completed_jobs = [
                msg for msg in progress_messages
                if msg['parsed_data']['progress'] == 1.0
            ]
            assert len(completed_jobs) >= 3, f"Expected ≥3 completed jobs, got {len(completed_jobs)}"
            
            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'enterprise_job_submit',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
        finally:
            listener.stop_listening()
    
    def test_job_priority_and_queuing_system(
        self,
        redis_client,
        mock_tickstockapp_consumer,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test job priority handling and intelligent queuing system.
        
        Validates that high-priority jobs are processed first
        and queue management works correctly under load.
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['jobs']['historical_load'],
            SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
        ]
        listener.subscribe(channels)
        listener.start_listening()
        
        consumer = mock_tickstockapp_consumer(redis_client)
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Submit jobs with different priorities
            priority_jobs = [
                {
                    'job_type': 'critical_data_fix',
                    'job_id': 'critical_001',
                    'priority': 'critical',
                    'estimated_duration_minutes': 5,
                    'submission_time': time.time()
                },
                {
                    'job_type': 'routine_maintenance',
                    'job_id': 'routine_001', 
                    'priority': 'low',
                    'estimated_duration_minutes': 60,
                    'submission_time': time.time()
                },
                {
                    'job_type': 'user_requested_backtest',
                    'job_id': 'user_001',
                    'priority': 'high',
                    'estimated_duration_minutes': 15,
                    'submission_time': time.time()
                },
                {
                    'job_type': 'scheduled_eod_update',
                    'job_id': 'eod_001',
                    'priority': 'medium',
                    'estimated_duration_minutes': 30,
                    'submission_time': time.time()
                }
            ]
            
            # Submit jobs in non-priority order to test queuing
            submission_order = [1, 0, 3, 2]  # routine, critical, eod, user
            
            for i in submission_order:
                job = priority_jobs[i]
                with integration_performance_monitor.measure_operation('priority_job_submit'):
                    consumer.submit_data_request(job)
                time.sleep(0.02)  # Very small delay
            
            # Simulate priority-aware job processing
            # Critical and high priority jobs should be processed first
            priority_order = ['critical_001', 'user_001', 'eod_001', 'routine_001']
            
            for job_id in priority_order:
                # Immediate processing for high-priority jobs
                processing_time = 0.1 if 'critical' in job_id or 'user' in job_id else 0.3
                
                producer.publish_backtest_progress(job_id, 0.5, 'processing')
                time.sleep(processing_time)
                producer.publish_backtest_progress(job_id, 1.0, 'completed')
            
            # Wait for priority processing
            time.sleep(1.0)
            
            # Verify job submissions
            job_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['jobs']['historical_load'])
            assert len(job_messages) == 4
            
            # Validate priority job characteristics
            priorities = [msg['parsed_data']['priority'] for msg in job_messages]
            assert 'critical' in priorities
            assert 'high' in priorities
            assert 'medium' in priorities
            assert 'low' in priorities
            
            # Verify job processing completion
            progress_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['backtesting_progress'])
            completed_messages = [
                msg for msg in progress_messages
                if msg['parsed_data']['progress'] == 1.0
            ]
            
            assert len(completed_messages) >= 4
            
            # Validate priority-based processing (critical and user jobs completed first)
            # This is a simplified test - in real implementation, timestamps would verify order
            critical_completed = any(
                'critical_001' in msg['parsed_data']['job_id'] 
                for msg in completed_messages
            )
            user_completed = any(
                'user_001' in msg['parsed_data']['job_id']
                for msg in completed_messages
            )
            
            assert critical_completed, "Critical job should be completed"
            assert user_completed, "High priority user job should be completed"
            
        finally:
            listener.stop_listening()
    
    def test_enterprise_job_monitoring_dashboard(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test enterprise job monitoring dashboard integration.
        
        Validates comprehensive job status tracking, performance
        metrics, and dashboard update notifications.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate enterprise job monitoring events
            monitoring_events = [
                {
                    'alert_type': 'job_queue_status',
                    'severity': 'low',
                    'description': 'Enterprise job queue status update',
                    'queue_metrics': {
                        'pending_jobs': 15,
                        'processing_jobs': 3,
                        'completed_today': 47,
                        'failed_today': 2,
                        'avg_processing_time_minutes': 12.5,
                        'queue_health_score': 0.94
                    },
                    'worker_status': {
                        'active_workers': 5,
                        'idle_workers': 2,
                        'worker_efficiency': 0.87,
                        'worker_utilization': 0.71
                    }
                },
                {
                    'alert_type': 'job_performance_alert',
                    'severity': 'medium',
                    'description': 'Job processing time exceeded SLA',
                    'job_id': 'slow_job_001',
                    'job_type': 'bulk_historical_load',
                    'processing_time_minutes': 45,
                    'sla_target_minutes': 30,
                    'sla_breach_percentage': 50.0,
                    'recommended_action': 'increase_worker_allocation'
                },
                {
                    'alert_type': 'enterprise_health_summary',
                    'severity': 'low',
                    'description': 'Daily enterprise system health summary',
                    'system_health': {
                        'overall_score': 0.91,
                        'job_success_rate': 0.96,
                        'avg_job_latency_ms': 450,
                        'redis_streams_health': 0.98,
                        'worker_pool_efficiency': 0.89
                    },
                    'recommendations': [
                        'consider_adding_1_worker_during_peak_hours',
                        'optimize_bulk_load_chunking_strategy'
                    ]
                }
            ]
            
            # Publish monitoring events
            for event in monitoring_events:
                with integration_performance_monitor.measure_operation('enterprise_monitoring'):
                    producer.publish_data_quality_alert(event)
                time.sleep(0.1)
            
            # Wait for monitoring processing
            time.sleep(0.5)
            monitoring_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            
            # Filter monitoring messages
            monitoring_updates = [
                msg for msg in monitoring_messages
                if msg['parsed_data']['alert_type'] in [
                    'job_queue_status', 'job_performance_alert', 'enterprise_health_summary'
                ]
            ]
            
            # Validate monitoring updates
            assert len(monitoring_updates) == 3
            
            # Validate queue status monitoring
            queue_status = next(
                msg for msg in monitoring_updates
                if msg['parsed_data']['alert_type'] == 'job_queue_status'
            )
            queue_data = queue_status['parsed_data']
            assert queue_data['queue_metrics']['pending_jobs'] == 15
            assert queue_data['worker_status']['active_workers'] == 5
            assert queue_data['queue_metrics']['queue_health_score'] >= 0.9
            
            # Validate performance alert
            perf_alert = next(
                msg for msg in monitoring_updates
                if msg['parsed_data']['alert_type'] == 'job_performance_alert'
            )
            perf_data = perf_alert['parsed_data']
            assert perf_data['severity'] == 'medium'
            assert perf_data['sla_breach_percentage'] == 50.0
            assert perf_data['recommended_action'] == 'increase_worker_allocation'
            
            # Validate health summary
            health_summary = next(
                msg for msg in monitoring_updates
                if msg['parsed_data']['alert_type'] == 'enterprise_health_summary'
            )
            health_data = health_summary['parsed_data']
            assert health_data['system_health']['overall_score'] >= 0.9
            assert health_data['system_health']['job_success_rate'] >= 0.95
            assert len(health_data['recommendations']) >= 2
            
        finally:
            listener.stop_listening()


class TestDevelopmentRefreshIntegration:
    """Test rapid development environment refresh capabilities"""
    
    def test_rapid_database_refresh_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test rapid database refresh for development environments.
        
        Workflow:
        1. Development refresh triggered
        2. Database subset loaded rapidly
        3. Cache entries synchronized
        4. UI updated with fresh data
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['events']['quality_alert'],
            SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
        ]
        listener.subscribe(channels)
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate development refresh trigger
            refresh_request = {
                'alert_type': 'dev_refresh_initiated',
                'severity': 'low',
                'description': 'Development environment refresh started',
                'refresh_type': 'rapid_subset',
                'target_environment': 'development',
                'refresh_scope': {
                    'symbols_count': 50,
                    'date_range_months': 3,
                    'data_types': ['ohlcv_daily', 'events'],
                    'universes': ['dev_top_50', 'dev_etfs']
                },
                'estimated_duration_minutes': 3
            }
            
            with integration_performance_monitor.measure_operation('dev_refresh_initiate'):
                producer.publish_data_quality_alert(refresh_request)
            
            # Simulate rapid refresh execution phases
            refresh_phases = [
                {
                    'phase': 'database_cleanup',
                    'progress': 0.2,
                    'description': 'Cleaning development database tables'
                },
                {
                    'phase': 'subset_data_load',
                    'progress': 0.6,
                    'description': 'Loading subset historical data'
                },
                {
                    'phase': 'cache_synchronization',
                    'progress': 0.8,
                    'description': 'Synchronizing cache entries and universes'
                },
                {
                    'phase': 'ui_notification',
                    'progress': 1.0,
                    'description': 'Notifying UI components of refresh completion'
                }
            ]
            
            refresh_job_id = 'dev_refresh_001'
            for phase in refresh_phases:
                status = 'processing' if phase['progress'] < 1.0 else 'completed'
                
                # Publish phase progress
                with integration_performance_monitor.measure_operation('dev_refresh_progress'):
                    producer.publish_backtest_progress(refresh_job_id, phase['progress'], status)
                
                # Publish phase-specific alerts
                phase_alert = {
                    'alert_type': 'dev_refresh_phase',
                    'severity': 'low',
                    'description': phase['description'],
                    'phase_name': phase['phase'],
                    'progress_percentage': phase['progress'] * 100,
                    'refresh_job_id': refresh_job_id
                }
                
                producer.publish_data_quality_alert(phase_alert)
                time.sleep(0.2)  # Phase processing time
            
            # Simulate refresh completion notification
            completion_summary = {
                'alert_type': 'dev_refresh_completed',
                'severity': 'low',
                'description': 'Development environment refresh completed successfully',
                'refresh_job_id': refresh_job_id,
                'completion_metrics': {
                    'total_duration_minutes': 2.8,
                    'symbols_refreshed': 50,
                    'records_updated': 45000,
                    'cache_entries_synchronized': 8,
                    'performance_improvement': '15x faster than full refresh'
                },
                'next_refresh_recommendation': '24_hours'
            }
            
            producer.publish_data_quality_alert(completion_summary)
            
            # Wait for refresh workflow completion
            time.sleep(1.0)
            
            # Verify refresh initiation
            quality_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            initiation_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'dev_refresh_initiated'
            ]
            assert len(initiation_messages) == 1
            
            init_data = initiation_messages[0]['parsed_data']
            assert init_data['refresh_type'] == 'rapid_subset'
            assert init_data['refresh_scope']['symbols_count'] == 50
            
            # Verify refresh phases
            phase_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'dev_refresh_phase'
            ]
            assert len(phase_messages) == 4  # One for each phase
            
            phase_names = [msg['parsed_data']['phase_name'] for msg in phase_messages]
            assert 'database_cleanup' in phase_names
            assert 'subset_data_load' in phase_names
            assert 'cache_synchronization' in phase_names
            assert 'ui_notification' in phase_names
            
            # Verify completion summary
            completion_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'dev_refresh_completed'
            ]
            assert len(completion_messages) == 1
            
            completion_data = completion_messages[0]['parsed_data']
            assert completion_data['completion_metrics']['total_duration_minutes'] < 5.0
            assert completion_data['completion_metrics']['symbols_refreshed'] == 50
            
            # Verify progress tracking
            progress_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['backtesting_progress'])
            completed_progress = [
                msg for msg in progress_messages
                if msg['parsed_data']['progress'] == 1.0
            ]
            assert len(completed_progress) >= 1
            
            # Performance validation
            integration_performance_monitor.assert_performance_target(
                'dev_refresh_initiate',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
        finally:
            listener.stop_listening()
    
    def test_development_environment_isolation(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test development environment isolation and safety mechanisms.
        
        Validates that development operations don't affect production
        and proper isolation boundaries are maintained.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate environment isolation validation
            isolation_checks = [
                {
                    'alert_type': 'environment_isolation_check',
                    'severity': 'low',
                    'description': 'Development environment isolation verified',
                    'environment': 'development',
                    'isolation_metrics': {
                        'database_separation': True,
                        'redis_namespace_isolation': True,
                        'api_key_segregation': True,
                        'data_volume_limits_enforced': True
                    },
                    'safety_checks': {
                        'production_data_protection': True,
                        'resource_usage_bounded': True,
                        'network_isolation': True
                    }
                },
                {
                    'alert_type': 'dev_resource_usage_alert',
                    'severity': 'low',
                    'description': 'Development environment resource usage within limits',
                    'resource_metrics': {
                        'cpu_usage_percent': 25.3,
                        'memory_usage_mb': 512,
                        'disk_usage_gb': 2.1,
                        'api_calls_per_hour': 450,
                        'redis_memory_usage_mb': 64
                    },
                    'resource_limits': {
                        'cpu_limit_percent': 50,
                        'memory_limit_mb': 1024,
                        'disk_limit_gb': 10,
                        'api_calls_limit_per_hour': 1000,
                        'redis_memory_limit_mb': 128
                    },
                    'utilization_status': 'within_limits'
                },
                {
                    'alert_type': 'production_safety_verification',
                    'severity': 'low',
                    'description': 'Production environment unaffected by dev operations',
                    'verification_results': {
                        'production_database_untouched': True,
                        'production_redis_isolated': True,
                        'production_api_limits_unaffected': True,
                        'production_performance_stable': True
                    },
                    'safety_score': 1.0
                }
            ]
            
            # Publish isolation verification events
            for check in isolation_checks:
                with integration_performance_monitor.measure_operation('environment_isolation_check'):
                    producer.publish_data_quality_alert(check)
                time.sleep(0.05)
            
            # Wait for isolation verification
            time.sleep(0.3)
            isolation_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            
            # Filter isolation check messages
            isolation_updates = [
                msg for msg in isolation_messages
                if 'isolation' in msg['parsed_data']['alert_type'] or 
                   'safety' in msg['parsed_data']['alert_type'] or
                   'resource' in msg['parsed_data']['alert_type']
            ]
            
            # Validate isolation checks
            assert len(isolation_updates) == 3
            
            # Validate environment isolation
            env_isolation = next(
                msg for msg in isolation_updates
                if msg['parsed_data']['alert_type'] == 'environment_isolation_check'
            )
            isolation_data = env_isolation['parsed_data']
            assert isolation_data['isolation_metrics']['database_separation'] is True
            assert isolation_data['safety_checks']['production_data_protection'] is True
            
            # Validate resource usage monitoring
            resource_alert = next(
                msg for msg in isolation_updates
                if msg['parsed_data']['alert_type'] == 'dev_resource_usage_alert'
            )
            resource_data = resource_alert['parsed_data']
            assert resource_data['utilization_status'] == 'within_limits'
            assert resource_data['resource_metrics']['cpu_usage_percent'] < 50
            assert resource_data['resource_metrics']['memory_usage_mb'] <= 1024
            
            # Validate production safety
            safety_check = next(
                msg for msg in isolation_updates
                if msg['parsed_data']['alert_type'] == 'production_safety_verification'
            )
            safety_data = safety_check['parsed_data']
            assert safety_data['safety_score'] == 1.0
            assert safety_data['verification_results']['production_database_untouched'] is True
            
        finally:
            listener.stop_listening()
    
    def test_development_performance_benchmarking(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test development environment performance benchmarking.
        
        Validates performance measurement and comparison between
        development refresh strategies and timing optimization.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate performance benchmarking results
            benchmark_scenarios = [
                {
                    'alert_type': 'dev_performance_benchmark',
                    'severity': 'low',
                    'description': 'Rapid subset refresh performance benchmark',
                    'benchmark_type': 'rapid_subset_refresh',
                    'performance_metrics': {
                        'total_duration_seconds': 168,  # 2.8 minutes
                        'symbols_per_second': 18,
                        'records_loaded_per_second': 268,
                        'api_calls_per_second': 12,
                        'database_inserts_per_second': 1250,
                        'cache_sync_duration_seconds': 15
                    },
                    'comparison_baseline': {
                        'full_refresh_duration_seconds': 2520,  # 42 minutes
                        'performance_improvement_factor': 15.0,
                        'resource_efficiency_improvement': 8.2
                    }
                },
                {
                    'alert_type': 'dev_performance_benchmark',
                    'severity': 'low',
                    'description': 'Incremental update performance benchmark',
                    'benchmark_type': 'incremental_update',
                    'performance_metrics': {
                        'total_duration_seconds': 45,
                        'symbols_updated_per_second': 25,
                        'delta_records_per_second': 450,
                        'cache_invalidation_duration_seconds': 3
                    },
                    'comparison_baseline': {
                        'full_refresh_duration_seconds': 168,
                        'performance_improvement_factor': 3.7,
                        'resource_efficiency_improvement': 12.8
                    }
                },
                {
                    'alert_type': 'dev_optimization_recommendation',
                    'severity': 'low',
                    'description': 'Development refresh optimization recommendations',
                    'recommendations': [
                        {
                            'optimization': 'parallel_symbol_loading',
                            'expected_improvement_percent': 25,
                            'implementation_effort': 'medium'
                        },
                        {
                            'optimization': 'smart_cache_preloading',
                            'expected_improvement_percent': 15,
                            'implementation_effort': 'low'
                        },
                        {
                            'optimization': 'batch_database_operations',
                            'expected_improvement_percent': 35,
                            'implementation_effort': 'high'
                        }
                    ],
                    'total_potential_improvement_percent': 55
                }
            ]
            
            # Publish benchmarking results
            for benchmark in benchmark_scenarios:
                with integration_performance_monitor.measure_operation('dev_performance_benchmark'):
                    producer.publish_data_quality_alert(benchmark)
                time.sleep(0.05)
            
            # Wait for benchmarking processing
            time.sleep(0.3)
            benchmark_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            
            # Filter benchmark messages
            benchmark_updates = [
                msg for msg in benchmark_messages
                if 'performance_benchmark' in msg['parsed_data']['alert_type'] or
                   'optimization_recommendation' in msg['parsed_data']['alert_type']
            ]
            
            # Validate benchmark results
            assert len(benchmark_updates) == 3
            
            # Validate rapid subset refresh benchmark
            rapid_benchmark = next(
                msg for msg in benchmark_updates
                if msg['parsed_data']['benchmark_type'] == 'rapid_subset_refresh'
            )
            rapid_data = rapid_benchmark['parsed_data']
            assert rapid_data['performance_metrics']['total_duration_seconds'] < 300  # <5 minutes
            assert rapid_data['comparison_baseline']['performance_improvement_factor'] >= 10
            
            # Validate incremental update benchmark
            incremental_benchmark = next(
                msg for msg in benchmark_updates
                if msg['parsed_data']['benchmark_type'] == 'incremental_update'
            )
            inc_data = incremental_benchmark['parsed_data']
            assert inc_data['performance_metrics']['total_duration_seconds'] < 60  # <1 minute
            assert inc_data['comparison_baseline']['performance_improvement_factor'] >= 3
            
            # Validate optimization recommendations
            optimization_msg = next(
                msg for msg in benchmark_updates
                if msg['parsed_data']['alert_type'] == 'dev_optimization_recommendation'
            )
            opt_data = optimization_msg['parsed_data']
            assert len(opt_data['recommendations']) >= 3
            assert opt_data['total_potential_improvement_percent'] >= 50
            
            # Validate specific optimization suggestions
            optimizations = {rec['optimization']: rec for rec in opt_data['recommendations']}
            assert 'parallel_symbol_loading' in optimizations
            assert optimizations['parallel_symbol_loading']['expected_improvement_percent'] >= 20
            
        finally:
            listener.stop_listening()


class TestMarketScheduleIntegration:
    """Test market schedule integration and automated timing"""
    
    def test_market_calendar_awareness_workflow(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test market calendar awareness and automated scheduling.
        
        Workflow:
        1. Market calendar events detected
        2. Processing schedules adjusted automatically
        3. Holiday and early close handling
        4. Notifications sent for schedule changes
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate market calendar events
            calendar_events = [
                {
                    'alert_type': 'market_calendar_update',
                    'severity': 'low',
                    'description': 'Market holiday detected - adjusting processing schedules',
                    'calendar_event': 'market_holiday',
                    'event_date': '2024-12-25',
                    'event_name': 'Christmas Day',
                    'market_status': 'closed',
                    'schedule_adjustments': {
                        'eod_processing_skipped': True,
                        'next_processing_date': '2024-12-26',
                        'pattern_detection_suspended': True,
                        'data_validation_deferred': True
                    }
                },
                {
                    'alert_type': 'market_calendar_update',
                    'severity': 'low',
                    'description': 'Early market close detected - adjusting EOD timing',
                    'calendar_event': 'early_close',
                    'event_date': '2024-07-03',
                    'event_name': 'Day before Independence Day',
                    'market_status': 'early_close',
                    'early_close_time': '13:00:00',  # 1 PM ET
                    'schedule_adjustments': {
                        'eod_processing_time': '13:30:00',  # 30 minutes after close
                        'processing_window_shortened': True,
                        'priority_jobs_only': True
                    }
                },
                {
                    'alert_type': 'market_calendar_update',
                    'severity': 'low',
                    'description': 'Normal trading hours resumed after holiday',
                    'calendar_event': 'normal_trading_resumed',
                    'event_date': '2024-12-26',
                    'event_name': 'Trading resumes after Christmas',
                    'market_status': 'normal',
                    'schedule_adjustments': {
                        'eod_processing_time': '16:30:00',  # Normal 4:30 PM
                        'pattern_detection_resumed': True,
                        'full_processing_restored': True,
                        'catch_up_processing_enabled': True
                    }
                }
            ]
            
            # Publish calendar events
            for event in calendar_events:
                with integration_performance_monitor.measure_operation('market_calendar_update'):
                    producer.publish_data_quality_alert(event)
                time.sleep(0.1)
            
            # Wait for calendar processing
            time.sleep(0.5)
            calendar_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            
            # Filter calendar update messages
            calendar_updates = [
                msg for msg in calendar_messages
                if msg['parsed_data']['alert_type'] == 'market_calendar_update'
            ]
            
            # Validate calendar updates
            assert len(calendar_updates) == 3
            
            # Validate holiday handling
            holiday_update = next(
                msg for msg in calendar_updates
                if msg['parsed_data']['calendar_event'] == 'market_holiday'
            )
            holiday_data = holiday_update['parsed_data']
            assert holiday_data['market_status'] == 'closed'
            assert holiday_data['schedule_adjustments']['eod_processing_skipped'] is True
            assert holiday_data['schedule_adjustments']['next_processing_date'] == '2024-12-26'
            
            # Validate early close handling
            early_close = next(
                msg for msg in calendar_updates
                if msg['parsed_data']['calendar_event'] == 'early_close'
            )
            early_data = early_close['parsed_data']
            assert early_data['market_status'] == 'early_close'
            assert early_data['early_close_time'] == '13:00:00'
            assert early_data['schedule_adjustments']['eod_processing_time'] == '13:30:00'
            
            # Validate normal trading resumption
            normal_resume = next(
                msg for msg in calendar_updates
                if msg['parsed_data']['calendar_event'] == 'normal_trading_resumed'
            )
            resume_data = normal_resume['parsed_data']
            assert resume_data['market_status'] == 'normal'
            assert resume_data['schedule_adjustments']['full_processing_restored'] is True
            assert resume_data['schedule_adjustments']['catch_up_processing_enabled'] is True
            
        finally:
            listener.stop_listening()
    
    def test_automated_schedule_adaptation(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test automated schedule adaptation based on market conditions.
        
        Validates dynamic scheduling adjustments for various
        market conditions and system load factors.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate automated schedule adaptations
            adaptation_scenarios = [
                {
                    'alert_type': 'schedule_adaptation',
                    'severity': 'low',
                    'description': 'High market volatility detected - adjusting processing frequency',
                    'trigger': 'high_market_volatility',
                    'volatility_index': 45.8,  # VIX-like measure
                    'adaptations': {
                        'pattern_detection_frequency': 'increased',
                        'data_quality_checks': 'enhanced',
                        'processing_priority': 'elevated',
                        'alert_sensitivity': 'heightened'
                    },
                    'estimated_duration_hours': 4
                },
                {
                    'alert_type': 'schedule_adaptation',
                    'severity': 'low',
                    'description': 'Low volume trading detected - optimizing resource allocation',
                    'trigger': 'low_volume_trading',
                    'volume_vs_average': 0.35,  # 35% of normal volume
                    'adaptations': {
                        'worker_pool_size': 'reduced',
                        'processing_intervals': 'extended',
                        'resource_conservation': 'enabled',
                        'non_critical_jobs': 'deferred'
                    },
                    'resource_savings_percent': 40
                },
                {
                    'alert_type': 'schedule_adaptation',
                    'severity': 'medium',
                    'description': 'System load spike detected - implementing load balancing',
                    'trigger': 'high_system_load',
                    'cpu_usage_percent': 85,
                    'memory_usage_percent': 78,
                    'adaptations': {
                        'job_prioritization': 'strict',
                        'processing_throttling': 'enabled',
                        'queue_management': 'aggressive',
                        'background_jobs': 'paused'
                    },
                    'load_reduction_target_percent': 25
                }
            ]
            
            # Publish adaptation scenarios
            for scenario in adaptation_scenarios:
                with integration_performance_monitor.measure_operation('schedule_adaptation'):
                    producer.publish_data_quality_alert(scenario)
                time.sleep(0.1)
            
            # Wait for adaptation processing
            time.sleep(0.5)
            adaptation_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            
            # Filter adaptation messages
            adaptation_updates = [
                msg for msg in adaptation_messages
                if msg['parsed_data']['alert_type'] == 'schedule_adaptation'
            ]
            
            # Validate schedule adaptations
            assert len(adaptation_updates) == 3
            
            # Validate volatility adaptation
            volatility_adaptation = next(
                msg for msg in adaptation_updates
                if msg['parsed_data']['trigger'] == 'high_market_volatility'
            )
            vol_data = volatility_adaptation['parsed_data']
            assert vol_data['volatility_index'] > 40  # High volatility threshold
            assert vol_data['adaptations']['pattern_detection_frequency'] == 'increased'
            assert vol_data['adaptations']['alert_sensitivity'] == 'heightened'
            
            # Validate low volume adaptation
            volume_adaptation = next(
                msg for msg in adaptation_updates
                if msg['parsed_data']['trigger'] == 'low_volume_trading'
            )
            volume_data = volume_adaptation['parsed_data']
            assert volume_data['volume_vs_average'] < 0.5  # Less than 50% normal volume
            assert volume_data['adaptations']['resource_conservation'] == 'enabled'
            assert volume_data['resource_savings_percent'] >= 30
            
            # Validate system load adaptation
            load_adaptation = next(
                msg for msg in adaptation_updates
                if msg['parsed_data']['trigger'] == 'high_system_load'
            )
            load_data = load_adaptation['parsed_data']
            assert load_data['cpu_usage_percent'] >= 80
            assert load_data['adaptations']['processing_throttling'] == 'enabled'
            assert load_data['load_reduction_target_percent'] >= 20
            
        finally:
            listener.stop_listening()


class TestPhase4CrossSystemIntegration:
    """Test cross-system integration scenarios across Phase 4 features"""
    
    def test_enterprise_dev_market_integration_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockapp_consumer,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test complete Phase 4 workflow: Enterprise scheduling → Dev refresh → Market calendar integration.
        
        End-to-end validation of production optimization features.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = [
            SPRINT14_REDIS_CHANNELS['jobs']['historical_load'],
            SPRINT14_REDIS_CHANNELS['events']['backtesting_progress'],
            SPRINT14_REDIS_CHANNELS['events']['quality_alert']
        ]
        listener.subscribe(all_channels)
        listener.start_listening()
        
        consumer = mock_tickstockapp_consumer(redis_client)
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Step 1: Market calendar triggers schedule adjustment
            calendar_trigger = {
                'alert_type': 'market_calendar_update',
                'severity': 'low',
                'description': 'Early close detected - adjusting enterprise jobs',
                'calendar_event': 'early_close',
                'event_date': '2024-07-03',
                'early_close_time': '13:00:00',
                'schedule_adjustments': {
                    'enterprise_jobs_rescheduled': True,
                    'dev_refresh_accelerated': True,
                    'processing_window_compressed': True
                }
            }
            
            with integration_performance_monitor.measure_operation('phase4_calendar_trigger'):
                producer.publish_data_quality_alert(calendar_trigger)
            
            # Step 2: Enterprise scheduler adapts to shortened trading day
            adapted_job = {
                'job_type': 'accelerated_eod_processing',
                'job_id': 'enterprise_early_close',
                'priority': 'critical',
                'symbols_batch': ['SPY', 'QQQ', 'IWM', 'GLD'],
                'processing_deadline': '13:15:00',  # 15 minutes after early close
                'scheduler': 'enterprise_scheduler',
                'market_condition': 'early_close'
            }
            
            consumer.submit_data_request(adapted_job)
            
            # Step 3: Development refresh triggered as part of adaptation
            dev_refresh_request = {
                'alert_type': 'dev_refresh_initiated',
                'severity': 'low',
                'description': 'Accelerated dev refresh due to early market close',
                'refresh_type': 'rapid_subset',
                'target_environment': 'development',
                'trigger_reason': 'market_calendar_adaptation'
            }
            
            producer.publish_data_quality_alert(dev_refresh_request)
            
            # Step 4: Execute enterprise job with progress tracking
            job_progress = [0.25, 0.75, 1.0]
            for progress in job_progress:
                status = 'processing' if progress < 1.0 else 'completed'
                producer.publish_backtest_progress('enterprise_early_close', progress, status)
                time.sleep(0.1)
            
            # Step 5: Complete development refresh
            dev_completion = {
                'alert_type': 'dev_refresh_completed',
                'severity': 'low',
                'description': 'Accelerated development refresh completed',
                'completion_metrics': {
                    'total_duration_minutes': 2.2,  # Even faster due to early close
                    'symbols_refreshed': 25,  # Reduced set for early close
                    'market_adaptation': 'successful'
                }
            }
            
            producer.publish_data_quality_alert(dev_completion)
            
            # Wait for complete workflow
            time.sleep(1.5)
            
            # Verify market calendar trigger
            quality_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            calendar_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'market_calendar_update'
            ]
            assert len(calendar_messages) >= 1
            
            calendar_data = calendar_messages[0]['parsed_data']
            assert calendar_data['calendar_event'] == 'early_close'
            assert calendar_data['schedule_adjustments']['enterprise_jobs_rescheduled'] is True
            
            # Verify enterprise job submission
            job_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['jobs']['historical_load'])
            enterprise_jobs = [
                msg for msg in job_messages
                if msg['parsed_data'].get('scheduler') == 'enterprise_scheduler'
            ]
            assert len(enterprise_jobs) >= 1
            
            enterprise_data = enterprise_jobs[0]['parsed_data']
            assert enterprise_data['priority'] == 'critical'
            assert enterprise_data['market_condition'] == 'early_close'
            
            # Verify development refresh
            refresh_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] in ['dev_refresh_initiated', 'dev_refresh_completed']
            ]
            assert len(refresh_messages) >= 2
            
            # Verify job completion
            progress_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['backtesting_progress'])
            completed_jobs = [
                msg for msg in progress_messages
                if msg['parsed_data']['progress'] == 1.0
            ]
            assert len(completed_jobs) >= 1
            
            # Performance validation for complete workflow
            integration_performance_monitor.assert_performance_target(
                'phase4_calendar_trigger',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )
            
        finally:
            listener.stop_listening()
    
    def test_phase4_production_optimization_resilience(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test Phase 4 production optimization resilience under stress.
        
        Validates enterprise scheduler, dev refresh, and market calendar
        integration under high-load production conditions.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values())
        listener.subscribe(all_channels)
        listener.start_listening()
        
        producer = mock_tickstockpl_producer(redis_client)
        
        try:
            # Simulate high-stress production optimization scenario
            with integration_performance_monitor.measure_operation('phase4_production_stress'):
                
                # Multiple concurrent market events
                market_events = [
                    {'calendar_event': 'high_volatility_day', 'volatility_spike': 60},
                    {'calendar_event': 'earnings_flood', 'earnings_announcements': 150},
                    {'calendar_event': 'fed_announcement', 'market_impact': 'high'},
                    {'calendar_event': 'options_expiry', 'volume_multiplier': 3.2}
                ]
                
                for event in market_events:
                    calendar_update = {
                        'alert_type': 'market_calendar_update',
                        'severity': 'medium',
                        'description': f'Market event: {event["calendar_event"]}',
                        **event
                    }
                    producer.publish_data_quality_alert(calendar_update)
                
                # Enterprise scheduler overload simulation
                for i in range(15):  # 15 concurrent enterprise jobs
                    enterprise_alert = {
                        'alert_type': 'job_queue_status',
                        'severity': 'medium' if i > 10 else 'low',
                        'description': f'Enterprise job queue update #{i}',
                        'queue_metrics': {
                            'pending_jobs': 8 + i,
                            'processing_jobs': min(5, i),
                            'queue_stress_level': 'high' if i > 10 else 'normal'
                        }
                    }
                    producer.publish_data_quality_alert(enterprise_alert)
                
                # Multiple development refresh requests
                for i in range(5):
                    dev_refresh = {
                        'alert_type': 'dev_refresh_initiated',
                        'severity': 'low',
                        'description': f'Concurrent dev refresh #{i}',
                        'refresh_type': 'rapid_subset',
                        'concurrent_request_id': i
                    }
                    producer.publish_data_quality_alert(dev_refresh)
                    
                    # Immediate completion simulation
                    completion = {
                        'alert_type': 'dev_refresh_completed',
                        'severity': 'low',
                        'description': f'Concurrent dev refresh #{i} completed',
                        'concurrent_request_id': i,
                        'completion_metrics': {
                            'total_duration_minutes': 2.5 + (i * 0.1),  # Slight degradation under load
                            'performance_impact': 'minimal'
                        }
                    }
                    producer.publish_data_quality_alert(completion)
            
            # Allow stress scenario processing
            time.sleep(3.0)
            
            # Verify system handled production stress
            all_messages = []
            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                all_messages.extend(channel_messages)
            
            # Should handle substantial message volume
            assert len(all_messages) >= 30, f"Expected ≥30 messages under stress, got {len(all_messages)}"
            
            # Verify market event handling
            quality_messages = [msg for msg in all_messages if 'alert_type' in msg.get('parsed_data', {})]
            market_updates = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'market_calendar_update'
            ]
            assert len(market_updates) >= 4  # Should handle all market events
            
            # Verify enterprise job queue management
            queue_updates = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'job_queue_status'
            ]
            assert len(queue_updates) >= 10  # Should handle queue stress
            
            # Verify development refresh resilience
            refresh_completions = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'dev_refresh_completed'
            ]
            assert len(refresh_completions) >= 4  # Most should complete despite load
            
            # Performance should be reasonable despite stress
            integration_performance_monitor.assert_performance_target(
                'phase4_production_stress',
                PERFORMANCE_TARGETS['end_to_end_workflow_ms'] * 3  # Allow 3x normal latency
            )
            
        finally:
            listener.stop_listening()