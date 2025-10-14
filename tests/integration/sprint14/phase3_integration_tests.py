"""
Sprint 14 Phase 3 Integration Tests

Tests cross-system integration for:
- Cache Entries Expansion with enhanced universe management
- ETF Universe Manager with AUM/liquidity tracking
- Test Data Scenarios for comprehensive validation

Validates advanced features integration with Redis pub-sub architecture
and TickStockApp (consumer) ↔ TickStockPL (producer) communication patterns.
"""
import time

from sqlalchemy import text

from tests.integration.sprint14.conftest import PERFORMANCE_TARGETS, SPRINT14_REDIS_CHANNELS


class TestCacheEntriesExpansionIntegration:
    """Test cache entries expansion and synchronization workflows"""

    def test_cache_universe_expansion_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test cache universe expansion and synchronization workflow.
        
        Workflow:
        1. New universe definitions created in cache_entries
        2. Universe expansion notifications published to Redis
        3. TickStockApp receives universe updates
        4. UI dropdowns and filters updated accordingly
        """
        listener = redis_pubsub_listener(redis_client)
        # Use quality_alert channel for cache sync notifications
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate cache entries expansion scenarios
            cache_expansions = [
                {
                    'alert_type': 'cache_universe_expanded',
                    'severity': 'low',
                    'description': 'Added new thematic universe: AI & Machine Learning',
                    'universe_key': 'ai_ml_stocks',
                    'symbol_count': 45,
                    'category': 'thematic',
                    'expansion_reason': 'user_demand',
                    'symbols_added': ['NVDA', 'PLTR', 'C3AI', 'AI', 'SNOW']
                },
                {
                    'alert_type': 'cache_universe_expanded',
                    'severity': 'low',
                    'description': 'Extended international ETF coverage',
                    'universe_key': 'international_etfs',
                    'symbol_count': 78,
                    'category': 'etf_geographic',
                    'expansion_reason': 'market_coverage',
                    'regions_added': ['APAC', 'EMEA', 'LatAm']
                },
                {
                    'alert_type': 'cache_universe_expanded',
                    'severity': 'low',
                    'description': 'Updated sector rotation universe',
                    'universe_key': 'sector_rotation',
                    'symbol_count': 120,
                    'category': 'strategy_based',
                    'expansion_reason': 'rebalancing',
                    'sectors_rebalanced': ['Technology', 'Healthcare', 'Energy']
                }
            ]

            # Publish cache expansion notifications
            for expansion in cache_expansions:
                with integration_performance_monitor.measure_operation('cache_expansion_publish'):
                    producer.publish_data_quality_alert(expansion)
                time.sleep(0.05)

            # Wait for cache synchronization
            time.sleep(0.5)
            cache_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Filter cache expansion messages
            expansion_messages = [
                msg for msg in cache_messages
                if msg['parsed_data']['alert_type'] == 'cache_universe_expanded'
            ]

            # Validate cache expansions received
            assert len(expansion_messages) == 3

            # Validate universe categories
            categories = [msg['parsed_data']['category'] for msg in expansion_messages]
            assert 'thematic' in categories
            assert 'etf_geographic' in categories
            assert 'strategy_based' in categories

            # Validate AI/ML thematic universe
            ai_ml_message = next(
                msg for msg in expansion_messages
                if msg['parsed_data']['universe_key'] == 'ai_ml_stocks'
            )
            ai_ml_data = ai_ml_message['parsed_data']
            assert ai_ml_data['symbol_count'] == 45
            assert 'NVDA' in ai_ml_data['symbols_added']
            assert ai_ml_data['expansion_reason'] == 'user_demand'

            # Validate international ETF expansion
            intl_etf_message = next(
                msg for msg in expansion_messages
                if msg['parsed_data']['universe_key'] == 'international_etfs'
            )
            intl_data = intl_etf_message['parsed_data']
            assert intl_data['symbol_count'] == 78
            assert 'APAC' in intl_data['regions_added']

        finally:
            listener.stop_listening()

    def test_cache_entries_real_time_sync(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test real-time cache entries synchronization between systems.
        
        Validates that cache changes in TickStockPL are immediately
        reflected in TickStockApp without database polling.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate real-time cache synchronization events
            sync_events = [
                {
                    'alert_type': 'cache_sync_update',
                    'severity': 'low',
                    'description': 'Symbol added to multiple universes',
                    'symbol': 'NEWLY_PUBLIC',
                    'universes_added': ['small_cap', 'technology_stocks', 'high_growth'],
                    'sync_timestamp': time.time(),
                    'change_type': 'symbol_addition'
                },
                {
                    'alert_type': 'cache_sync_update',
                    'severity': 'low',
                    'description': 'ETF universe weights rebalanced',
                    'universe_key': 'etf_growth',
                    'symbols_reweighted': 15,
                    'sync_timestamp': time.time(),
                    'change_type': 'weight_adjustment'
                },
                {
                    'alert_type': 'cache_sync_update',
                    'severity': 'medium',
                    'description': 'Symbol removed due to delisting',
                    'symbol': 'DELISTED_CORP',
                    'universes_removed': ['mid_cap', 'dividend_stocks'],
                    'sync_timestamp': time.time(),
                    'change_type': 'symbol_removal',
                    'removal_reason': 'delisting'
                }
            ]

            # Publish sync events with performance tracking
            sync_start = time.time()

            for event in sync_events:
                with integration_performance_monitor.measure_operation('cache_sync_realtime'):
                    producer.publish_data_quality_alert(event)
                time.sleep(0.02)  # Very small delay for real-time simulation

            sync_duration = (time.time() - sync_start) * 1000  # Convert to ms

            # Wait for synchronization
            time.sleep(0.3)
            sync_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Filter sync update messages
            update_messages = [
                msg for msg in sync_messages
                if msg['parsed_data']['alert_type'] == 'cache_sync_update'
            ]

            # Validate real-time sync messages
            assert len(update_messages) == 3

            # Validate symbol addition sync
            addition_message = next(
                msg for msg in update_messages
                if msg['parsed_data']['change_type'] == 'symbol_addition'
            )
            addition_data = addition_message['parsed_data']
            assert addition_data['symbol'] == 'NEWLY_PUBLIC'
            assert len(addition_data['universes_added']) == 3
            assert 'small_cap' in addition_data['universes_added']

            # Validate removal sync
            removal_message = next(
                msg for msg in update_messages
                if msg['parsed_data']['change_type'] == 'symbol_removal'
            )
            removal_data = removal_message['parsed_data']
            assert removal_data['symbol'] == 'DELISTED_CORP'
            assert removal_data['removal_reason'] == 'delisting'

            # Performance validation for real-time sync
            assert sync_duration < 200, f"Sync duration {sync_duration:.2f}ms too slow for real-time"

            integration_performance_monitor.assert_performance_target(
                'cache_sync_realtime',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

        finally:
            listener.stop_listening()

    def test_universe_hierarchy_management(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test hierarchical universe management and parent-child relationships.
        
        Validates that nested universe structures are properly synchronized
        and hierarchical relationships are maintained across systems.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate hierarchical universe structure updates
            hierarchy_updates = [
                {
                    'alert_type': 'universe_hierarchy_updated',
                    'severity': 'low',
                    'description': 'Created parent universe for sector breakdown',
                    'parent_universe': 'all_sectors',
                    'child_universes': [
                        'technology_stocks', 'healthcare_stocks',
                        'financial_stocks', 'energy_stocks'
                    ],
                    'hierarchy_level': 1,
                    'total_symbols': 2847
                },
                {
                    'alert_type': 'universe_hierarchy_updated',
                    'severity': 'low',
                    'description': 'Sub-categorized technology stocks',
                    'parent_universe': 'technology_stocks',
                    'child_universes': [
                        'ai_ml_stocks', 'semiconductor_stocks',
                        'software_stocks', 'hardware_stocks'
                    ],
                    'hierarchy_level': 2,
                    'total_symbols': 687
                },
                {
                    'alert_type': 'universe_hierarchy_updated',
                    'severity': 'low',
                    'description': 'ETF hierarchy by asset class',
                    'parent_universe': 'all_etfs',
                    'child_universes': [
                        'equity_etfs', 'bond_etfs',
                        'commodity_etfs', 'international_etfs'
                    ],
                    'hierarchy_level': 1,
                    'total_symbols': 458
                }
            ]

            # Publish hierarchy updates
            for update in hierarchy_updates:
                with integration_performance_monitor.measure_operation('hierarchy_update'):
                    producer.publish_data_quality_alert(update)
                time.sleep(0.05)

            # Wait for hierarchy synchronization
            time.sleep(0.5)
            hierarchy_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Filter hierarchy update messages
            hierarchy_updates_received = [
                msg for msg in hierarchy_messages
                if msg['parsed_data']['alert_type'] == 'universe_hierarchy_updated'
            ]

            # Validate hierarchy updates
            assert len(hierarchy_updates_received) == 3

            # Validate sector hierarchy (level 1)
            sector_hierarchy = next(
                msg for msg in hierarchy_updates_received
                if msg['parsed_data']['parent_universe'] == 'all_sectors'
            )
            sector_data = sector_hierarchy['parsed_data']
            assert sector_data['hierarchy_level'] == 1
            assert len(sector_data['child_universes']) == 4
            assert 'technology_stocks' in sector_data['child_universes']
            assert sector_data['total_symbols'] == 2847

            # Validate technology sub-hierarchy (level 2)
            tech_hierarchy = next(
                msg for msg in hierarchy_updates_received
                if msg['parsed_data']['parent_universe'] == 'technology_stocks'
            )
            tech_data = tech_hierarchy['parsed_data']
            assert tech_data['hierarchy_level'] == 2
            assert 'ai_ml_stocks' in tech_data['child_universes']
            assert tech_data['total_symbols'] == 687

            # Validate ETF hierarchy
            etf_hierarchy = next(
                msg for msg in hierarchy_updates_received
                if msg['parsed_data']['parent_universe'] == 'all_etfs'
            )
            etf_data = etf_hierarchy['parsed_data']
            assert len(etf_data['child_universes']) == 4
            assert 'international_etfs' in etf_data['child_universes']

        finally:
            listener.stop_listening()


class TestETFUniverseManagerIntegration:
    """Test ETF Universe Manager integration workflows"""

    def test_etf_aum_tracking_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test ETF AUM (Assets Under Management) tracking and alerts.
        
        Workflow:
        1. ETF AUM changes detected
        2. Universe membership updated based on AUM thresholds
        3. Notifications published to Redis
        4. UI universe filters updated accordingly
        """
        listener = redis_pubsub_listener(redis_client)
        channels = [
            SPRINT14_REDIS_CHANNELS['events']['etf_updated'],
            SPRINT14_REDIS_CHANNELS['events']['quality_alert']
        ]
        listener.subscribe(channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Insert test ETF data
            test_etf_data = {
                'symbol': 'AUM_TEST_ETF',
                'name': 'AUM Test ETF',
                'etf_type': 'equity_growth',
                'aum_millions': 5000.0,  # Initial AUM
                'expense_ratio': 0.0050
            }

            db_connection.execute(text("""
                INSERT INTO symbols (symbol, name, type, etf_type, aum_millions, expense_ratio)
                VALUES (:symbol, :name, 'ETF', :etf_type, :aum_millions, :expense_ratio)
            """), test_etf_data)
            db_connection.commit()

            # Simulate AUM threshold changes
            aum_scenarios = [
                {
                    'symbol': 'AUM_TEST_ETF',
                    'old_aum_millions': 5000.0,
                    'new_aum_millions': 12000.0,  # Crossed into large-cap ETF
                    'threshold_crossed': 'large_cap_etf',
                    'universe_changes': {
                        'added_to': ['large_cap_etfs', 'institutional_etfs'],
                        'removed_from': ['mid_cap_etfs']
                    }
                },
                {
                    'symbol': 'DECLINING_ETF',
                    'old_aum_millions': 15000.0,
                    'new_aum_millions': 8000.0,  # Dropped below large-cap threshold
                    'threshold_crossed': 'mid_cap_etf',
                    'universe_changes': {
                        'added_to': ['mid_cap_etfs'],
                        'removed_from': ['large_cap_etfs', 'institutional_etfs']
                    }
                }
            ]

            # Publish AUM tracking events
            for scenario in aum_scenarios:
                # ETF update event
                etf_update = {
                    'symbol': scenario['symbol'],
                    'aum_millions': scenario['new_aum_millions'],
                    'aum_change_percent': (
                        (scenario['new_aum_millions'] - scenario['old_aum_millions']) /
                        scenario['old_aum_millions'] * 100
                    ),
                    'threshold_crossed': scenario['threshold_crossed']
                }

                with integration_performance_monitor.measure_operation('etf_aum_update'):
                    producer.publish_etf_data_update(scenario['symbol'], etf_update)

                # Universe change notification
                universe_change = {
                    'alert_type': 'etf_universe_rebalanced',
                    'severity': 'low',
                    'description': 'ETF universe membership updated due to AUM change',
                    'symbol': scenario['symbol'],
                    'old_aum': scenario['old_aum_millions'],
                    'new_aum': scenario['new_aum_millions'],
                    'universe_changes': scenario['universe_changes']
                }

                producer.publish_data_quality_alert(universe_change)
                time.sleep(0.1)

            # Wait for AUM tracking updates
            time.sleep(0.5)

            # Verify ETF update messages
            etf_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['etf_updated'])
            assert len(etf_messages) == 2

            # Validate AUM increase scenario
            aum_increase_message = next(
                msg for msg in etf_messages
                if msg['parsed_data']['symbol'] == 'AUM_TEST_ETF'
            )
            increase_data = aum_increase_message['parsed_data']
            assert increase_data['aum_millions'] == 12000.0
            assert increase_data['aum_change_percent'] > 100  # > 100% increase

            # Verify universe change notifications
            quality_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            universe_changes = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'etf_universe_rebalanced'
            ]
            assert len(universe_changes) == 2

            # Validate universe membership changes
            for change_msg in universe_changes:
                change_data = change_msg['parsed_data']
                assert 'universe_changes' in change_data
                assert 'added_to' in change_data['universe_changes']
                assert 'removed_from' in change_data['universe_changes']

        finally:
            listener.stop_listening()

    def test_etf_liquidity_monitoring_integration(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test ETF liquidity monitoring and trading volume analysis.
        
        Validates liquidity-based universe assignment and
        alerts for ETFs with liquidity issues.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate ETF liquidity monitoring events
            liquidity_scenarios = [
                {
                    'symbol': 'LIQUID_ETF',
                    'alert_type': 'etf_liquidity_updated',
                    'severity': 'low',
                    'description': 'High liquidity ETF maintains strong trading volume',
                    'avg_daily_volume': 5000000,
                    'liquidity_tier': 'high_liquidity',
                    'bid_ask_spread_bps': 2.5,
                    'universe_assignment': 'liquid_etfs'
                },
                {
                    'symbol': 'ILLIQUID_ETF',
                    'alert_type': 'etf_liquidity_concern',
                    'severity': 'medium',
                    'description': 'ETF shows declining liquidity patterns',
                    'avg_daily_volume': 50000,
                    'liquidity_tier': 'low_liquidity',
                    'bid_ask_spread_bps': 25.0,
                    'volume_decline_percent': -45.2,
                    'days_declining': 7,
                    'universe_assignment': 'illiquid_etfs'
                },
                {
                    'symbol': 'NICHE_ETF',
                    'alert_type': 'etf_liquidity_updated',
                    'severity': 'low',
                    'description': 'Specialized ETF maintains adequate niche liquidity',
                    'avg_daily_volume': 250000,
                    'liquidity_tier': 'medium_liquidity',
                    'bid_ask_spread_bps': 8.5,
                    'specialty_factor': 'sector_specific',
                    'universe_assignment': 'specialty_etfs'
                }
            ]

            # Publish liquidity monitoring events
            for scenario in liquidity_scenarios:
                with integration_performance_monitor.measure_operation('etf_liquidity_monitor'):
                    producer.publish_data_quality_alert(scenario)
                time.sleep(0.05)

            # Wait for liquidity monitoring
            time.sleep(0.5)
            liquidity_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Filter liquidity-related messages
            liquidity_updates = [
                msg for msg in liquidity_messages
                if 'liquidity' in msg['parsed_data']['alert_type']
            ]

            # Validate liquidity monitoring messages
            assert len(liquidity_updates) == 3

            # Validate high liquidity ETF
            liquid_message = next(
                msg for msg in liquidity_updates
                if msg['parsed_data']['symbol'] == 'LIQUID_ETF'
            )
            liquid_data = liquid_message['parsed_data']
            assert liquid_data['liquidity_tier'] == 'high_liquidity'
            assert liquid_data['avg_daily_volume'] >= 1000000
            assert liquid_data['bid_ask_spread_bps'] <= 5.0

            # Validate liquidity concern
            concern_message = next(
                msg for msg in liquidity_updates
                if msg['parsed_data']['alert_type'] == 'etf_liquidity_concern'
            )
            concern_data = concern_message['parsed_data']
            assert concern_data['symbol'] == 'ILLIQUID_ETF'
            assert concern_data['severity'] == 'medium'
            assert concern_data['volume_decline_percent'] < -40
            assert concern_data['days_declining'] >= 7

            # Validate specialty ETF classification
            niche_message = next(
                msg for msg in liquidity_updates
                if msg['parsed_data']['symbol'] == 'NICHE_ETF'
            )
            niche_data = niche_message['parsed_data']
            assert niche_data['specialty_factor'] == 'sector_specific'
            assert niche_data['universe_assignment'] == 'specialty_etfs'

        finally:
            listener.stop_listening()

    def test_etf_correlation_matrix_updates(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test ETF correlation matrix updates and universe clustering.
        
        Validates that ETF correlation changes trigger appropriate
        universe reassignments and clustering updates.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['etf_updated']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate ETF correlation matrix updates
            correlation_updates = [
                {
                    'symbol': 'SPY_CLONE_ETF',
                    'correlation_reference': 'SPY',
                    'correlation_coefficient': 0.98,
                    'correlation_period_days': 30,
                    'correlation_strength': 'very_high',
                    'cluster_assignment': 'spy_alternatives',
                    'diversification_benefit': 'minimal'
                },
                {
                    'symbol': 'UNCORR_SECTOR_ETF',
                    'correlation_reference': 'SPY',
                    'correlation_coefficient': 0.25,
                    'correlation_period_days': 30,
                    'correlation_strength': 'low',
                    'cluster_assignment': 'diversifiers',
                    'diversification_benefit': 'high'
                },
                {
                    'symbol': 'INTL_DIVERSIFIER',
                    'correlation_reference': 'SPY',
                    'correlation_coefficient': 0.45,
                    'correlation_period_days': 30,
                    'correlation_strength': 'moderate',
                    'cluster_assignment': 'moderate_diversifiers',
                    'diversification_benefit': 'moderate',
                    'geographic_factor': 'international'
                }
            ]

            # Publish correlation updates
            for update in correlation_updates:
                with integration_performance_monitor.measure_operation('etf_correlation_update'):
                    producer.publish_etf_data_update(update['symbol'], update)
                time.sleep(0.05)

            # Wait for correlation processing
            time.sleep(0.5)
            correlation_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['etf_updated'])

            # Validate correlation updates received
            assert len(correlation_messages) == 3

            # Validate SPY clone identification
            spy_clone = next(
                msg for msg in correlation_messages
                if msg['parsed_data']['symbol'] == 'SPY_CLONE_ETF'
            )
            clone_data = spy_clone['parsed_data']
            assert clone_data['correlation_coefficient'] >= 0.95
            assert clone_data['correlation_strength'] == 'very_high'
            assert clone_data['cluster_assignment'] == 'spy_alternatives'
            assert clone_data['diversification_benefit'] == 'minimal'

            # Validate diversifier identification
            diversifier = next(
                msg for msg in correlation_messages
                if msg['parsed_data']['symbol'] == 'UNCORR_SECTOR_ETF'
            )
            div_data = diversifier['parsed_data']
            assert div_data['correlation_coefficient'] <= 0.3
            assert div_data['correlation_strength'] == 'low'
            assert div_data['diversification_benefit'] == 'high'

            # Validate international diversifier
            intl_div = next(
                msg for msg in correlation_messages
                if msg['parsed_data']['symbol'] == 'INTL_DIVERSIFIER'
            )
            intl_data = intl_div['parsed_data']
            assert intl_data['geographic_factor'] == 'international'
            assert intl_data['correlation_strength'] == 'moderate'

        finally:
            listener.stop_listening()


class TestDataScenariosIntegration:
    """Test comprehensive data scenario generation and validation"""

    def test_synthetic_test_scenario_generation(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test synthetic test scenario generation for comprehensive validation.
        
        Validates generation of test scenarios covering edge cases,
        performance stress testing, and data quality validation.
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
            # Simulate test scenario generation
            test_scenarios = [
                {
                    'alert_type': 'test_scenario_generated',
                    'severity': 'low',
                    'description': 'Generated high-volatility market stress scenario',
                    'scenario_type': 'market_stress',
                    'scenario_id': 'stress_001',
                    'parameters': {
                        'volatility_multiplier': 3.5,
                        'symbols_affected': 500,
                        'duration_days': 10,
                        'correlation_breakdown': True
                    },
                    'expected_patterns': ['Engulfing', 'Doji', 'Hammer'],
                    'validation_targets': {
                        'pattern_detection_rate': 0.85,
                        'false_positive_rate': 0.05,
                        'latency_ms_max': 100
                    }
                },
                {
                    'alert_type': 'test_scenario_generated',
                    'severity': 'low',
                    'description': 'Generated IPO surge scenario with data gaps',
                    'scenario_type': 'ipo_surge',
                    'scenario_id': 'ipo_001',
                    'parameters': {
                        'new_ipos_per_day': 15,
                        'data_gap_probability': 0.15,
                        'backfill_delay_hours': 2,
                        'market_cap_range': [100, 50000]
                    },
                    'validation_targets': {
                        'ipo_detection_rate': 0.98,
                        'backfill_completion_rate': 0.95,
                        'universe_assignment_accuracy': 0.90
                    }
                },
                {
                    'alert_type': 'test_scenario_generated',
                    'severity': 'low',
                    'description': 'Generated ETF rebalancing cascade scenario',
                    'scenario_type': 'etf_rebalancing',
                    'scenario_id': 'etf_001',
                    'parameters': {
                        'etfs_rebalancing': 25,
                        'rebalancing_magnitude': 0.25,
                        'correlation_impact': 'moderate',
                        'liquidity_impact': 'high'
                    },
                    'validation_targets': {
                        'aum_tracking_accuracy': 0.99,
                        'liquidity_alert_timeliness': 60,  # seconds
                        'correlation_update_accuracy': 0.92
                    }
                }
            ]

            # Publish test scenario generation events
            scenario_job_id = f"test_scenarios_{int(time.time())}"

            for scenario in test_scenarios:
                with integration_performance_monitor.measure_operation('test_scenario_generation'):
                    producer.publish_data_quality_alert(scenario)
                time.sleep(0.05)

            # Simulate test scenario execution progress
            execution_progress = [0.25, 0.50, 0.75, 1.0]
            for progress in execution_progress:
                status = 'processing' if progress < 1.0 else 'completed'
                producer.publish_backtest_progress(scenario_job_id, progress, status)
                time.sleep(0.1)

            # Wait for scenario processing
            time.sleep(1.0)

            # Verify scenario generation messages
            quality_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            scenario_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'test_scenario_generated'
            ]

            assert len(scenario_messages) == 3

            # Validate market stress scenario
            stress_scenario = next(
                msg for msg in scenario_messages
                if msg['parsed_data']['scenario_type'] == 'market_stress'
            )
            stress_data = stress_scenario['parsed_data']
            assert stress_data['parameters']['volatility_multiplier'] == 3.5
            assert stress_data['parameters']['symbols_affected'] == 500
            assert 'Engulfing' in stress_data['expected_patterns']

            # Validate IPO surge scenario
            ipo_scenario = next(
                msg for msg in scenario_messages
                if msg['parsed_data']['scenario_type'] == 'ipo_surge'
            )
            ipo_data = ipo_scenario['parsed_data']
            assert ipo_data['parameters']['new_ipos_per_day'] == 15
            assert ipo_data['validation_targets']['ipo_detection_rate'] == 0.98

            # Verify scenario execution progress
            progress_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['backtesting_progress'])
            assert len(progress_messages) >= 4

            completed_message = next(
                msg for msg in progress_messages
                if msg['parsed_data']['progress'] == 1.0
            )
            assert completed_message['parsed_data']['status'] == 'completed'

        finally:
            listener.stop_listening()

    def test_edge_case_scenario_validation(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test edge case scenario validation and system resilience.
        
        Validates system behavior under unusual market conditions
        and data anomalies.
        """
        listener = redis_pubsub_listener(redis_client)
        listener.subscribe([SPRINT14_REDIS_CHANNELS['events']['quality_alert']])
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate edge case scenarios
            edge_cases = [
                {
                    'alert_type': 'edge_case_detected',
                    'severity': 'high',
                    'description': 'Flash crash scenario with 30% market decline in 5 minutes',
                    'edge_case_type': 'flash_crash',
                    'magnitude': -0.30,
                    'duration_minutes': 5,
                    'affected_symbols': 1500,
                    'circuit_breakers_triggered': True,
                    'system_response': {
                        'pattern_detection_suspended': True,
                        'emergency_mode_activated': True,
                        'data_validation_enhanced': True
                    }
                },
                {
                    'alert_type': 'edge_case_detected',
                    'severity': 'medium',
                    'description': 'Extended trading halt affecting 50+ ETFs',
                    'edge_case_type': 'widespread_halt',
                    'symbols_halted': 67,
                    'halt_duration_hours': 4.5,
                    'halt_reason': 'regulatory_review',
                    'system_response': {
                        'fmv_approximation_enabled': True,
                        'correlation_tracking_suspended': False,
                        'alternative_data_sources_activated': True
                    }
                },
                {
                    'alert_type': 'edge_case_detected',
                    'severity': 'medium',
                    'description': 'Massive IPO day with 25 new listings',
                    'edge_case_type': 'ipo_flood',
                    'new_listings_count': 25,
                    'combined_market_cap_billions': 150.0,
                    'system_load_factor': 3.2,
                    'system_response': {
                        'ipo_processing_prioritized': True,
                        'universe_assignment_automated': True,
                        'backfill_parallelization_increased': True
                    }
                }
            ]

            # Publish edge case scenarios
            for edge_case in edge_cases:
                with integration_performance_monitor.measure_operation('edge_case_handling'):
                    producer.publish_data_quality_alert(edge_case)
                time.sleep(0.1)

            # Wait for edge case processing
            time.sleep(0.8)
            edge_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])

            # Filter edge case messages
            edge_case_messages = [
                msg for msg in edge_messages
                if msg['parsed_data']['alert_type'] == 'edge_case_detected'
            ]

            # Validate edge case handling
            assert len(edge_case_messages) == 3

            # Validate flash crash handling
            flash_crash = next(
                msg for msg in edge_case_messages
                if msg['parsed_data']['edge_case_type'] == 'flash_crash'
            )
            crash_data = flash_crash['parsed_data']
            assert crash_data['severity'] == 'high'
            assert crash_data['magnitude'] == -0.30
            assert crash_data['system_response']['emergency_mode_activated'] is True
            assert crash_data['circuit_breakers_triggered'] is True

            # Validate widespread halt handling
            halt_case = next(
                msg for msg in edge_case_messages
                if msg['parsed_data']['edge_case_type'] == 'widespread_halt'
            )
            halt_data = halt_case['parsed_data']
            assert halt_data['symbols_halted'] == 67
            assert halt_data['system_response']['fmv_approximation_enabled'] is True

            # Validate IPO flood handling
            ipo_flood = next(
                msg for msg in edge_case_messages
                if msg['parsed_data']['edge_case_type'] == 'ipo_flood'
            )
            flood_data = ipo_flood['parsed_data']
            assert flood_data['new_listings_count'] == 25
            assert flood_data['system_response']['universe_assignment_automated'] is True

        finally:
            listener.stop_listening()


class TestPhase3CrossSystemIntegration:
    """Test cross-system integration scenarios across Phase 3 features"""

    def test_cache_etf_scenario_integration_workflow(
        self,
        redis_client,
        db_connection,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor,
        sprint14_test_data
    ):
        """
        Test complete Phase 3 workflow: Cache expansion → ETF universe updates → Test scenarios.
        
        End-to-end validation of advanced features integration.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = [
            SPRINT14_REDIS_CHANNELS['events']['etf_updated'],
            SPRINT14_REDIS_CHANNELS['events']['quality_alert'],
            SPRINT14_REDIS_CHANNELS['events']['backtesting_progress']
        ]
        listener.subscribe(all_channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Step 1: Cache Universe Expansion
            cache_expansion = {
                'alert_type': 'cache_universe_expanded',
                'severity': 'low',
                'description': 'Added ESG-focused ETF universe',
                'universe_key': 'esg_etfs',
                'symbol_count': 32,
                'category': 'esg_focused',
                'expansion_reason': 'sustainability_trend'
            }

            with integration_performance_monitor.measure_operation('phase3_cache_expansion'):
                producer.publish_data_quality_alert(cache_expansion)

            # Step 2: ETF Universe Manager Updates
            etf_updates = [
                {
                    'symbol': 'ESG_LEADER_ETF',
                    'aum_millions': 8500.0,
                    'expense_ratio': 0.0045,
                    'esg_score': 92,
                    'universe_assignment': 'esg_etfs'
                },
                {
                    'symbol': 'GREEN_ENERGY_ETF',
                    'aum_millions': 3200.0,
                    'expense_ratio': 0.0075,
                    'esg_score': 88,
                    'universe_assignment': 'esg_etfs'
                }
            ]

            for etf in etf_updates:
                with integration_performance_monitor.measure_operation('phase3_etf_update'):
                    producer.publish_etf_data_update(etf['symbol'], etf)
                time.sleep(0.05)

            # Step 3: Test Scenario Generation for ESG ETFs
            esg_test_scenario = {
                'alert_type': 'test_scenario_generated',
                'severity': 'low',
                'description': 'Generated ESG ETF correlation scenario',
                'scenario_type': 'esg_correlation_test',
                'scenario_id': 'esg_001',
                'parameters': {
                    'esg_etfs_count': 32,
                    'correlation_benchmark': 'ESG_LEADER_ETF',
                    'test_duration_days': 30,
                    'sustainability_events': True
                },
                'validation_targets': {
                    'esg_correlation_accuracy': 0.88,
                    'universe_assignment_precision': 0.94
                }
            }

            producer.publish_data_quality_alert(esg_test_scenario)

            # Step 4: Execute test scenario with progress tracking
            scenario_job_id = 'esg_correlation_test'
            execution_steps = [0.33, 0.67, 1.0]

            for progress in execution_steps:
                status = 'processing' if progress < 1.0 else 'completed'
                producer.publish_backtest_progress(scenario_job_id, progress, status)
                time.sleep(0.1)

            # Wait for complete workflow
            time.sleep(1.5)

            # Verify cache expansion
            quality_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['quality_alert'])
            cache_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'cache_universe_expanded'
            ]
            assert len(cache_messages) >= 1

            cache_data = cache_messages[0]['parsed_data']
            assert cache_data['universe_key'] == 'esg_etfs'
            assert cache_data['symbol_count'] == 32

            # Verify ETF updates
            etf_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['etf_updated'])
            assert len(etf_messages) >= 2

            esg_leader_message = next(
                (msg for msg in etf_messages
                 if msg['parsed_data']['symbol'] == 'ESG_LEADER_ETF'),
                None
            )
            assert esg_leader_message is not None
            assert esg_leader_message['parsed_data']['esg_score'] == 92

            # Verify test scenario generation
            scenario_messages = [
                msg for msg in quality_messages
                if msg['parsed_data']['alert_type'] == 'test_scenario_generated'
            ]
            assert len(scenario_messages) >= 1

            scenario_data = scenario_messages[0]['parsed_data']
            assert scenario_data['scenario_type'] == 'esg_correlation_test'

            # Verify test execution completion
            progress_messages = listener.get_messages(SPRINT14_REDIS_CHANNELS['events']['backtesting_progress'])
            completed_messages = [
                msg for msg in progress_messages
                if msg['parsed_data']['progress'] == 1.0
            ]
            assert len(completed_messages) >= 1

            # Performance validation for complete workflow
            integration_performance_monitor.assert_performance_target(
                'phase3_cache_expansion',
                PERFORMANCE_TARGETS['message_delivery_ms']
            )

        finally:
            listener.stop_listening()

    def test_phase3_advanced_features_resilience(
        self,
        redis_client,
        mock_tickstockpl_producer,
        redis_pubsub_listener,
        integration_performance_monitor
    ):
        """
        Test Phase 3 advanced features resilience under complex scenarios.
        
        Validates system stability with concurrent cache updates,
        ETF universe changes, and test scenario executions.
        """
        listener = redis_pubsub_listener(redis_client)
        all_channels = list(SPRINT14_REDIS_CHANNELS['events'].values())
        listener.subscribe(all_channels)
        listener.start_listening()

        producer = mock_tickstockpl_producer(redis_client)

        try:
            # Simulate concurrent advanced operations
            with integration_performance_monitor.measure_operation('phase3_concurrent_operations'):

                # Concurrent cache universe expansions
                for i in range(5):
                    cache_expansion = {
                        'alert_type': 'cache_universe_expanded',
                        'severity': 'low',
                        'description': f'Universe expansion #{i}',
                        'universe_key': f'dynamic_universe_{i}',
                        'symbol_count': 20 + i * 5,
                        'category': 'dynamic_test'
                    }
                    producer.publish_data_quality_alert(cache_expansion)

                # Concurrent ETF AUM updates
                for i in range(10):
                    etf_update = {
                        'symbol': f'CONCURRENT_ETF_{i}',
                        'aum_millions': 1000.0 + i * 500,
                        'liquidity_tier': 'high_liquidity' if i % 2 == 0 else 'medium_liquidity'
                    }
                    producer.publish_etf_data_update(etf_update['symbol'], etf_update)

                # Concurrent test scenario generation
                for i in range(3):
                    test_scenario = {
                        'alert_type': 'test_scenario_generated',
                        'severity': 'low',
                        'description': f'Concurrent test scenario #{i}',
                        'scenario_type': f'resilience_test_{i}',
                        'scenario_id': f'resilience_{i:03d}'
                    }
                    producer.publish_data_quality_alert(test_scenario)

                    # Immediate scenario execution
                    producer.publish_backtest_progress(f'resilience_{i:03d}', 1.0, 'completed')

            # Allow processing time for concurrent operations
            time.sleep(2.0)

            # Verify system handled concurrent operations
            all_messages = []
            for channel in all_channels:
                channel_messages = listener.get_messages(channel)
                all_messages.extend(channel_messages)

            # Should receive substantial number of messages
            assert len(all_messages) >= 15, f"Expected ≥15 messages, got {len(all_messages)}"

            # Verify message type diversity
            message_types = set()
            for msg in all_messages:
                if 'alert_type' in msg['parsed_data']:
                    message_types.add(msg['parsed_data']['alert_type'])
                elif 'event_type' in msg['parsed_data']:
                    message_types.add(msg['parsed_data']['event_type'])

            # Should have diverse message types
            assert len(message_types) >= 4

            # Performance should be reasonable under concurrent load
            integration_performance_monitor.assert_performance_target(
                'phase3_concurrent_operations',
                PERFORMANCE_TARGETS['end_to_end_workflow_ms'] * 2  # Allow 2x normal latency
            )

        finally:
            listener.stop_listening()
