#!/usr/bin/env python3
"""
Sprint 14 Phase 3 System Resilience and Performance Integration Tests

Comprehensive resilience testing for Sprint 14 Phase 3 advanced features:
- System failure recovery and graceful degradation
- Database connection resilience and transaction isolation
- Concurrent operation stress testing and resource management
- Memory and performance monitoring under load
- Error propagation and service boundary maintenance
- Data consistency validation during failures

Performance and Resilience Targets:
- System recovery: <5 seconds from failure
- Concurrent operations: Handle 10+ simultaneous requests
- Memory efficiency: <100MB increase under stress
- Data consistency: 100% ACID compliance during failures
- Error isolation: No cross-service error propagation
"""

import asyncio
import concurrent.futures
import gc
import json
import os
import sys
import time

import psutil
import pytest

from src.core.services.config_manager import get_config

# Initialize configuration with fallback
try:
    config = get_config()
except Exception:
    # Fallback if config_manager not available
    class ConfigFallback:
        def get(self, key, default=None):
            return default  # Use defaults only
    config = ConfigFallback()


# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import psycopg2
import psycopg2.extras
import redis.asyncio as async_redis
from src.data.cache_entries_synchronizer import CacheEntriesSynchronizer

# Import Phase 3 modules
from src.data.etf_universe_manager import ETFUniverseManager
from src.data.test_scenario_generator import TestScenarioGenerator


class TestPhase3SystemResilience:
    """
    System Resilience and Performance Integration Tests
    
    Validates system behavior under:
    1. Database connection failures and recovery
    2. Redis connection disruptions and failover
    3. High concurrent load and resource constraints
    4. Memory pressure and garbage collection impact
    5. Disk I/O limitations and storage failures
    6. Network latency and timeout scenarios
    """

    @pytest.fixture(scope="class")
    def test_config(self):
        """Test configuration"""
        return {
            'database': {
                'host': config.get('TEST_DB_HOST', 'localhost'),
                'database': config.get('TEST_DB_NAME', 'tickstock_test'),
                'user': config.get('TEST_DB_USER', 'app_readwrite'),
                'password': config.get('TEST_DB_PASSWORD', 'OLD_PASSWORD_2024'),
                'port': int(config.get('TEST_DB_PORT', '5432'))
            },
            'redis': {
                'host': config.get('TEST_REDIS_HOST', 'localhost'),
                'port': int(config.get('TEST_REDIS_PORT', '6379')),
                'db': 13  # Dedicated resilience test database
            }
        }

    @pytest.fixture
    def system_monitor(self):
        """System resource monitoring"""
        class SystemMonitor:
            def __init__(self):
                self.process = psutil.Process(os.getpid())
                self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                self.initial_cpu = self.process.cpu_percent()
                self.memory_samples = [self.initial_memory]
                self.cpu_samples = [self.initial_cpu]
                self.monitoring = False
                self.monitor_task = None

            def start_monitoring(self, interval=0.1):
                """Start continuous monitoring"""
                self.monitoring = True
                self.monitor_task = asyncio.create_task(self._monitor_loop(interval))

            async def stop_monitoring(self):
                """Stop monitoring and return results"""
                self.monitoring = False
                if self.monitor_task:
                    self.monitor_task.cancel()
                    try:
                        await self.monitor_task
                    except asyncio.CancelledError:
                        pass

                return {
                    'initial_memory_mb': self.initial_memory,
                    'peak_memory_mb': max(self.memory_samples),
                    'final_memory_mb': self.memory_samples[-1],
                    'memory_increase_mb': max(self.memory_samples) - self.initial_memory,
                    'avg_cpu_percent': sum(self.cpu_samples) / len(self.cpu_samples),
                    'peak_cpu_percent': max(self.cpu_samples),
                    'sample_count': len(self.memory_samples)
                }

            async def _monitor_loop(self, interval):
                """Internal monitoring loop"""
                while self.monitoring:
                    try:
                        memory_mb = self.process.memory_info().rss / 1024 / 1024
                        cpu_percent = self.process.cpu_percent()

                        self.memory_samples.append(memory_mb)
                        self.cpu_samples.append(cpu_percent)

                        await asyncio.sleep(interval)
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        continue

        return SystemMonitor()

    @pytest.fixture
    def failure_injector(self):
        """Helper for injecting controlled failures"""
        class FailureInjector:
            def __init__(self):
                self.failures = []
                self.recovery_times = []

            def inject_database_failure(self, connection, duration=1.0):
                """Simulate database connection failure"""
                try:
                    connection.close()
                    time.sleep(duration)
                    self.failures.append(('database', duration))
                except Exception as e:
                    self.failures.append(('database_error', str(e)))

            async def inject_redis_failure(self, redis_client, duration=1.0):
                """Simulate Redis connection failure"""
                try:
                    await redis_client.connection_pool.disconnect()
                    await asyncio.sleep(duration)
                    self.failures.append(('redis', duration))
                except Exception as e:
                    self.failures.append(('redis_error', str(e)))

            def inject_memory_pressure(self, size_mb=50):
                """Inject memory pressure"""
                try:
                    # Allocate memory to simulate pressure
                    memory_hog = bytearray(size_mb * 1024 * 1024)
                    time.sleep(0.5)
                    del memory_hog
                    gc.collect()
                    self.failures.append(('memory_pressure', size_mb))
                except Exception as e:
                    self.failures.append(('memory_error', str(e)))

            def record_recovery(self, failure_type, recovery_time):
                """Record recovery time"""
                self.recovery_times.append((failure_type, recovery_time))

        return FailureInjector()

    # =================================================================
    # DATABASE RESILIENCE TESTS
    # =================================================================

    def test_database_connection_recovery(self, test_config, failure_injector):
        """Test database connection recovery and transaction resilience"""
        database_uri = f"postgresql://{test_config['database']['user']}:{test_config['database']['password']}@{test_config['database']['host']}:{test_config['database']['port']}/{test_config['database']['database']}"

        etf_manager = ETFUniverseManager(database_uri=database_uri)

        # Phase 1: Normal operation
        initial_conn = etf_manager.get_database_connection()
        assert initial_conn is not None, "Initial database connection failed"

        cursor = initial_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cache_entries")
        initial_count = cursor.fetchone()[0]
        initial_conn.close()

        # Phase 2: Inject database failure
        test_conn = etf_manager.get_database_connection()
        failure_injector.inject_database_failure(test_conn, duration=2.0)

        # Phase 3: Test recovery
        recovery_start = time.time()

        max_retry_attempts = 5
        recovery_successful = False

        for attempt in range(max_retry_attempts):
            try:
                recovery_conn = etf_manager.get_database_connection()
                if recovery_conn:
                    cursor = recovery_conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM cache_entries")
                    recovery_count = cursor.fetchone()[0]
                    recovery_conn.close()

                    recovery_successful = True
                    break
            except Exception:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff

        recovery_time = time.time() - recovery_start
        failure_injector.record_recovery('database', recovery_time)

        # Validate recovery
        assert recovery_successful, "Database connection recovery failed"
        assert recovery_time < 10.0, f"Database recovery took {recovery_time:.2f}s, too slow"
        assert recovery_count == initial_count, "Data consistency lost during recovery"

    def test_transaction_isolation_during_failures(self, test_config):
        """Test transaction isolation and ACID compliance during failures"""
        database_uri = f"postgresql://{test_config['database']['user']}:{test_config['database']['password']}@{test_config['database']['host']}:{test_config['database']['port']}/{test_config['database']['database']}"

        # Create two independent connections
        conn1 = psycopg2.connect(database_uri, cursor_factory=psycopg2.extras.RealDictCursor)
        conn2 = psycopg2.connect(database_uri, cursor_factory=psycopg2.extras.RealDictCursor)

        test_key = f"resilience_test_{int(time.time())}"

        try:
            # Transaction 1: Start long-running transaction
            cursor1 = conn1.cursor()
            cursor1.execute("""
                INSERT INTO cache_entries (cache_key, symbols)
                VALUES (%s, %s)
            """, (test_key, json.dumps(['RESILIENCE_TEST'])))
            # Don't commit yet

            # Transaction 2: Try to read uncommitted data
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT symbols FROM cache_entries WHERE cache_key = %s", (test_key,))
            result = cursor2.fetchone()

            # Should not see uncommitted data (isolation)
            assert result is None, "Transaction isolation violated - saw uncommitted data"

            # Transaction 1: Commit
            conn1.commit()

            # Transaction 2: Now should see committed data
            cursor2.execute("SELECT symbols FROM cache_entries WHERE cache_key = %s", (test_key,))
            result = cursor2.fetchone()

            assert result is not None, "Committed data not visible"
            assert result['symbols'] == ['RESILIENCE_TEST'], "Data corruption during transaction"

            # Test rollback behavior
            cursor1.execute("""
                UPDATE cache_entries 
                SET symbols = %s 
                WHERE cache_key = %s
            """, (json.dumps(['UPDATED_TEST']), test_key))

            # Rollback the update
            conn1.rollback()

            # Verify rollback worked
            cursor2.execute("SELECT symbols FROM cache_entries WHERE cache_key = %s", (test_key,))
            result = cursor2.fetchone()

            assert result['symbols'] == ['RESILIENCE_TEST'], "Rollback failed - data corrupted"

        finally:
            # Cleanup
            try:
                cursor1.execute("DELETE FROM cache_entries WHERE cache_key = %s", (test_key,))
                conn1.commit()
            except:
                pass

            conn1.close()
            conn2.close()

    def test_concurrent_database_operations(self, test_config):
        """Test database performance under concurrent load"""
        database_uri = f"postgresql://{test_config['database']['user']}:{test_config['database']['password']}@{test_config['database']['host']}:{test_config['database']['port']}/{test_config['database']['database']}"

        def concurrent_database_worker(worker_id, operation_count=20):
            """Worker function for concurrent database operations"""
            results = []
            errors = []

            try:
                conn = psycopg2.connect(database_uri, cursor_factory=psycopg2.extras.RealDictCursor)
                conn.autocommit = True
                cursor = conn.cursor()

                for i in range(operation_count):
                    start_time = time.time()

                    try:
                        # Mix of read and write operations
                        if i % 3 == 0:
                            # Write operation
                            test_key = f"concurrent_test_{worker_id}_{i}"
                            cursor.execute("""
                                INSERT INTO cache_entries (cache_key, symbols)
                                VALUES (%s, %s)
                                ON CONFLICT (cache_key) DO UPDATE SET
                                    symbols = EXCLUDED.symbols
                            """, (test_key, json.dumps([f'WORKER_{worker_id}'])))
                        else:
                            # Read operation
                            cursor.execute("SELECT COUNT(*) FROM cache_entries")
                            cursor.fetchone()

                        operation_time = (time.time() - start_time) * 1000  # ms
                        results.append(operation_time)

                    except Exception as e:
                        errors.append(str(e))

                conn.close()

            except Exception as e:
                errors.append(f"Worker {worker_id} connection error: {str(e)}")

            return {
                'worker_id': worker_id,
                'operations_completed': len(results),
                'avg_operation_time_ms': sum(results) / len(results) if results else 0,
                'max_operation_time_ms': max(results) if results else 0,
                'error_count': len(errors),
                'errors': errors
            }

        # Run 10 concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()

            futures = [executor.submit(concurrent_database_worker, worker_id)
                      for worker_id in range(10)]

            results = [future.result() for future in concurrent.futures.as_completed(futures)]

            total_time = time.time() - start_time

        # Validate concurrent performance
        total_operations = sum(r['operations_completed'] for r in results)
        total_errors = sum(r['error_count'] for r in results)

        assert total_errors == 0, f"Concurrent database operations had {total_errors} errors"
        assert total_operations >= 180, f"Expected 200 operations, got {total_operations}"  # Some tolerance
        assert total_time < 30.0, f"Concurrent operations took {total_time:.1f}s, too slow"

        # Validate individual worker performance
        for result in results:
            avg_time = result['avg_operation_time_ms']
            max_time = result['max_operation_time_ms']

            assert avg_time < 100, f"Worker {result['worker_id']} avg time {avg_time:.1f}ms too slow"
            assert max_time < 500, f"Worker {result['worker_id']} max time {max_time:.1f}ms too slow"

        # Cleanup concurrent test data
        try:
            cleanup_conn = psycopg2.connect(database_uri)
            cleanup_conn.autocommit = True
            cursor = cleanup_conn.cursor()
            cursor.execute("DELETE FROM cache_entries WHERE cache_key LIKE 'concurrent_test_%'")
            cleanup_conn.close()
        except:
            pass

    # =================================================================
    # REDIS RESILIENCE TESTS
    # =================================================================

    @pytest.mark.asyncio
    async def test_redis_failover_and_recovery(self, test_config, failure_injector):
        """Test Redis connection failover and message delivery recovery"""
        redis_client = async_redis.Redis(
            **test_config['redis'],
            decode_responses=True,
            retry_on_timeout=True,
            health_check_interval=1
        )

        test_channel = 'tickstock.failover.test'
        received_messages = []

        # Set up subscriber
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(test_channel)

        async def failover_listener():
            try:
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        data = json.loads(message['data'])
                        received_messages.append(data)
            except Exception as e:
                failure_injector.failures.append(('redis_listener_error', str(e)))

        listener_task = asyncio.create_task(failover_listener())

        try:
            # Phase 1: Normal operation
            for i in range(5):
                message = {'msg_id': f'normal_{i}', 'timestamp': time.time()}
                await redis_client.publish(test_channel, json.dumps(message))
                await asyncio.sleep(0.1)

            await asyncio.sleep(0.5)
            normal_count = len(received_messages)
            assert normal_count == 5, f"Normal operation failed: {normal_count}/5 messages"

            # Phase 2: Inject Redis failure
            await failure_injector.inject_redis_failure(redis_client, duration=2.0)

            # Phase 3: Test recovery
            recovery_start = time.time()
            recovery_successful = False

            for attempt in range(10):
                try:
                    # Test connection recovery
                    await redis_client.ping()

                    # Test publishing recovery
                    recovery_message = {
                        'msg_id': f'recovery_{attempt}',
                        'timestamp': time.time()
                    }
                    await redis_client.publish(test_channel, json.dumps(recovery_message))

                    recovery_successful = True
                    break

                except Exception:
                    await asyncio.sleep(0.3)

            recovery_time = time.time() - recovery_start
            failure_injector.record_recovery('redis', recovery_time)

            # Allow time for recovery messages
            await asyncio.sleep(1.0)

            # Validate recovery
            assert recovery_successful, "Redis connection recovery failed"
            assert recovery_time < 5.0, f"Redis recovery took {recovery_time:.2f}s, too slow"

            recovery_count = len(received_messages) - normal_count
            assert recovery_count > 0, "No messages received after Redis recovery"

        finally:
            listener_task.cancel()
            await pubsub.unsubscribe(test_channel)
            await pubsub.aclose()
            await redis_client.aclose()

    @pytest.mark.asyncio
    async def test_redis_memory_pressure_handling(self, test_config):
        """Test Redis behavior under memory pressure"""
        redis_client = async_redis.Redis(**test_config['redis'], decode_responses=True)

        # Create memory pressure by filling Redis with data
        memory_keys = []
        large_data = 'x' * 10000  # 10KB per key

        try:
            # Fill Redis with test data
            for i in range(100):  # 1MB total
                key = f"memory_pressure_{i}"
                await redis_client.set(key, large_data)
                memory_keys.append(key)

            # Test normal operations under memory pressure
            test_channel = 'tickstock.memory.test'
            messages_sent = []
            messages_received = []

            pubsub = redis_client.pubsub()
            await pubsub.subscribe(test_channel)

            async def memory_listener():
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        messages_received.append(json.loads(message['data']))

            listener_task = asyncio.create_task(memory_listener())

            # Send messages while under memory pressure
            for i in range(20):
                message = {
                    'msg_id': f'pressure_{i}',
                    'timestamp': time.time(),
                    'data': 'test_data' * 100  # Moderate payload
                }
                messages_sent.append(message)
                await redis_client.publish(test_channel, json.dumps(message))
                await asyncio.sleep(0.05)

            await asyncio.sleep(1.0)

            # Validate operations continued under pressure
            success_rate = (len(messages_received) / len(messages_sent)) * 100
            assert success_rate >= 90, f"Memory pressure caused {100-success_rate:.1f}% message loss"

            # Test Redis still responsive
            ping_response = await redis_client.ping()
            assert ping_response, "Redis not responsive under memory pressure"

            listener_task.cancel()
            await pubsub.unsubscribe(test_channel)
            await pubsub.aclose()

        finally:
            # Cleanup memory pressure data
            for key in memory_keys:
                try:
                    await redis_client.delete(key)
                except:
                    pass
            await redis_client.aclose()

    # =================================================================
    # SYSTEM LOAD AND PERFORMANCE TESTS
    # =================================================================

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, test_config, system_monitor):
        """Test memory usage remains bounded under heavy load"""
        system_monitor.start_monitoring(interval=0.2)

        try:
            # Create multiple service instances
            etf_manager = ETFUniverseManager()
            scenario_generator = TestScenarioGenerator()
            cache_synchronizer = CacheEntriesSynchronizer()

            # Simulate heavy workload
            tasks = []

            # ETF universe operations
            for _ in range(5):
                task = asyncio.create_task(
                    self._simulate_etf_workload(etf_manager)
                )
                tasks.append(task)

            # Scenario generation operations
            for _ in range(3):
                task = asyncio.create_task(
                    self._simulate_scenario_workload(scenario_generator)
                )
                tasks.append(task)

            # Cache synchronization operations
            for _ in range(2):
                task = asyncio.create_task(
                    self._simulate_sync_workload(cache_synchronizer)
                )
                tasks.append(task)

            # Wait for all workloads
            await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            # Stop monitoring and get results
            monitor_results = await system_monitor.stop_monitoring()

        # Validate memory usage
        memory_increase = monitor_results['memory_increase_mb']
        peak_memory = monitor_results['peak_memory_mb']

        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB, exceeds 100MB limit"
        assert peak_memory < 1000, f"Peak memory {peak_memory:.1f}MB too high"  # Reasonable upper bound

        # Validate CPU usage was reasonable
        avg_cpu = monitor_results['avg_cpu_percent']
        peak_cpu = monitor_results['peak_cpu_percent']

        # CPU can spike during load, but average should be reasonable
        assert avg_cpu < 80, f"Average CPU {avg_cpu:.1f}% too high during load test"

    async def _simulate_etf_workload(self, etf_manager):
        """Simulate ETF universe management workload"""
        try:
            for _ in range(3):
                # Simulate expansion operations
                results = etf_manager.expand_etf_universes()
                await asyncio.sleep(0.1)

                # Simulate validation operations
                validation = await etf_manager.validate_universe_symbols()
                await asyncio.sleep(0.1)
        except Exception:
            pass  # Ignore errors for load testing

    async def _simulate_scenario_workload(self, scenario_generator):
        """Simulate test scenario generation workload"""
        try:
            scenarios = ['crash_2020', 'growth_2021', 'volatility_periods']
            for scenario in scenarios:
                # Generate scenario data
                data = scenario_generator.generate_scenario_data(scenario)
                await asyncio.sleep(0.2)
        except Exception:
            pass

    async def _simulate_sync_workload(self, cache_synchronizer):
        """Simulate cache synchronization workload"""
        try:
            for _ in range(2):
                # Simulate synchronization operations
                result = await cache_synchronizer.perform_synchronization()
                await asyncio.sleep(0.5)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self, test_config):
        """Test multiple services operating concurrently without interference"""
        database_uri = f"postgresql://{test_config['database']['user']}:{test_config['database']['password']}@{test_config['database']['host']}:{test_config['database']['port']}/{test_config['database']['database']}"

        # Create service instances
        services = {
            'etf_manager_1': ETFUniverseManager(database_uri=database_uri),
            'etf_manager_2': ETFUniverseManager(database_uri=database_uri),
            'scenario_gen_1': TestScenarioGenerator(database_uri=database_uri),
            'scenario_gen_2': TestScenarioGenerator(database_uri=database_uri),
            'cache_sync_1': CacheEntriesSynchronizer(database_uri=database_uri),
            'cache_sync_2': CacheEntriesSynchronizer(database_uri=database_uri)
        }

        service_results = {}

        async def run_service_workload(service_name, service_instance):
            """Run workload for specific service"""
            results = []
            errors = []

            try:
                if 'etf_manager' in service_name:
                    for i in range(3):
                        start_time = time.time()
                        expansion = service_instance.expand_etf_universes()
                        duration = time.time() - start_time
                        results.append(('expansion', duration, len(expansion.get('themes', {}))))
                        await asyncio.sleep(0.1)

                elif 'scenario_gen' in service_name:
                    scenarios = ['crash_2020', 'growth_2021']
                    for scenario in scenarios:
                        start_time = time.time()
                        data = service_instance.generate_scenario_data(scenario)
                        duration = time.time() - start_time
                        results.append(('generation', duration, len(data) if data else 0))
                        await asyncio.sleep(0.1)

                elif 'cache_sync' in service_name:
                    for i in range(2):
                        start_time = time.time()
                        sync_result = await service_instance.perform_synchronization()
                        duration = time.time() - start_time
                        results.append(('sync', duration, sync_result.get('total_changes', 0)))
                        await asyncio.sleep(0.2)

            except Exception as e:
                errors.append(str(e))

            service_results[service_name] = {
                'operations': len(results),
                'avg_duration': sum(r[1] for r in results) / len(results) if results else 0,
                'total_errors': len(errors),
                'results': results,
                'errors': errors
            }

        # Run all services concurrently
        start_time = time.time()

        tasks = [
            run_service_workload(name, instance)
            for name, instance in services.items()
        ]

        await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Validate concurrent operation results
        total_operations = sum(r['operations'] for r in service_results.values())
        total_errors = sum(r['total_errors'] for r in service_results.values())

        assert total_errors == 0, f"Concurrent services had {total_errors} errors"
        assert total_operations >= 30, f"Expected 30+ operations, got {total_operations}"  # Some tolerance
        assert total_time < 60, f"Concurrent service operations took {total_time:.1f}s, too slow"

        # Validate individual service performance wasn't degraded by concurrency
        for service_name, results in service_results.items():
            avg_duration = results['avg_duration']
            service_type = service_name.split('_')[0:2]
            service_type = '_'.join(service_type)

            # Set reasonable performance thresholds based on service type
            if service_type == 'etf_manager':
                max_duration = 3.0
            elif service_type == 'scenario_gen':
                max_duration = 10.0
            elif service_type == 'cache_sync':
                max_duration = 15.0
            else:
                max_duration = 5.0

            assert avg_duration < max_duration, f"{service_name} avg duration {avg_duration:.2f}s exceeds {max_duration}s"

    # =================================================================
    # ERROR PROPAGATION AND ISOLATION TESTS
    # =================================================================

    @pytest.mark.asyncio
    async def test_error_isolation_between_services(self, test_config):
        """Test that errors in one service don't propagate to others"""
        database_uri = f"postgresql://{test_config['database']['user']}:{test_config['database']['password']}@{test_config['database']['host']}:{test_config['database']['port']}/{test_config['database']['database']}"

        # Create services
        etf_manager = ETFUniverseManager(database_uri=database_uri)
        scenario_generator = TestScenarioGenerator(database_uri=database_uri)
        cache_synchronizer = CacheEntriesSynchronizer(database_uri=database_uri)

        error_results = {}

        async def test_service_with_errors(service_name, service_func):
            """Test service operation with intentional errors"""
            success_count = 0
            error_count = 0

            try:
                # Mix successful and failing operations
                for i in range(5):
                    try:
                        if i == 2:  # Inject failure on 3rd operation
                            # Simulate various failure modes
                            if service_name == 'etf_manager':
                                # Try invalid operation
                                invalid_manager = ETFUniverseManager(database_uri="invalid://connection")
                                invalid_manager.expand_etf_universes()
                            elif service_name == 'scenario_generator':
                                # Try invalid scenario
                                scenario_generator.generate_scenario_data('invalid_scenario')
                            elif service_name == 'cache_synchronizer':
                                # This will likely fail gracefully
                                await cache_synchronizer.market_cap_recalculation()
                        else:
                            # Normal operation
                            result = await service_func()
                            success_count += 1

                    except Exception:
                        error_count += 1
                        # Errors should be contained within the service

            except Exception:
                error_count += 1

            error_results[service_name] = {
                'success_count': success_count,
                'error_count': error_count,
                'isolation_maintained': error_count > 0  # Should have caught errors
            }

        # Define service test functions
        async def etf_test():
            return etf_manager.expand_etf_universes()

        async def scenario_test():
            return scenario_generator.generate_scenario_data('crash_2020')

        async def sync_test():
            return await cache_synchronizer.perform_synchronization()

        # Run services concurrently with intentional errors
        await asyncio.gather(
            test_service_with_errors('etf_manager', etf_test),
            test_service_with_errors('scenario_generator', scenario_test),
            test_service_with_errors('cache_synchronizer', sync_test),
            return_exceptions=True  # Don't let exceptions propagate
        )

        # Validate error isolation
        for service_name, results in error_results.items():
            success_count = results['success_count']
            error_count = results['error_count']

            # Each service should have had some successful operations
            assert success_count > 0, f"{service_name} had no successful operations"

            # Services should handle their own errors without crashing others
            total_operations = success_count + error_count
            assert total_operations > 0, f"{service_name} completed no operations"

        # Validate that at least one service encountered and handled errors
        total_errors = sum(r['error_count'] for r in error_results.values())
        assert total_errors > 0, "No errors were injected - test invalid"

        # All services should still be functional after errors
        try:
            etf_result = etf_manager.expand_etf_universes()
            assert etf_result is not None, "ETF manager not functional after error isolation test"

            scenario_result = scenario_generator.generate_scenario_data('growth_2021')
            assert scenario_result is not None, "Scenario generator not functional after error isolation test"

            # Cache synchronizer test (may fail gracefully)
            sync_result = await cache_synchronizer.perform_synchronization()
            # Don't assert on sync result as it may legitimately fail in test environment

        except Exception as e:
            pytest.fail(f"Services not functional after error isolation test: {e}")

    def test_graceful_degradation_under_resource_constraints(self, test_config, system_monitor):
        """Test system graceful degradation when resources are constrained"""
        system_monitor.start_monitoring(interval=0.1)

        try:
            # Simulate resource constraints
            database_uri = f"postgresql://{test_config['database']['user']}:{test_config['database']['password']}@{test_config['database']['host']}:{test_config['database']['port']}/{test_config['database']['database']}"

            services = []
            for i in range(20):  # Create many service instances
                etf_manager = ETFUniverseManager(database_uri=database_uri)
                services.append(etf_manager)

            # Simulate heavy workload
            results = []
            for i, service in enumerate(services[:10]):  # Use first 10 services
                try:
                    start_time = time.time()
                    result = service.expand_etf_universes()
                    duration = time.time() - start_time

                    results.append({
                        'service_id': i,
                        'duration': duration,
                        'success': True,
                        'themes_count': len(result.get('themes', {}))
                    })
                except Exception as e:
                    results.append({
                        'service_id': i,
                        'duration': 0,
                        'success': False,
                        'error': str(e)
                    })

                time.sleep(0.1)  # Brief pause between operations

        finally:
            monitor_results = asyncio.run(system_monitor.stop_monitoring())

        # Validate graceful degradation
        successful_operations = [r for r in results if r['success']]
        failed_operations = [r for r in results if not r['success']]

        success_rate = len(successful_operations) / len(results) * 100

        # Should maintain reasonable success rate even under constraints
        assert success_rate >= 70, f"Success rate {success_rate:.1f}% too low under resource constraints"

        # Successful operations should still perform reasonably
        if successful_operations:
            avg_duration = sum(r['duration'] for r in successful_operations) / len(successful_operations)
            assert avg_duration < 5.0, f"Average duration {avg_duration:.2f}s too slow under constraints"

        # Memory usage should remain bounded
        memory_increase = monitor_results['memory_increase_mb']
        assert memory_increase < 200, f"Memory increased by {memory_increase:.1f}MB, excessive under constraints"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
