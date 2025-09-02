#!/usr/bin/env python3
"""
Sprint 14 Phase 3 Integration Test Configuration Helper

Provides centralized configuration management and environment validation for Phase 3 integration tests:
- Test environment setup and validation
- Database schema verification and initialization
- Redis connectivity and channel validation
- Performance target management
- Test data management utilities
- Environment-specific configuration handling
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import subprocess

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import psycopg2
import psycopg2.extras
import redis
import redis.asyncio as async_redis

@dataclass
class TestConfiguration:
    """Test configuration data structure"""
    database_config: Dict[str, Any]
    redis_config: Dict[str, Any]
    performance_targets: Dict[str, float]
    test_channels: Dict[str, str]
    test_data_config: Dict[str, Any]
    environment: str

@dataclass
class ValidationResult:
    """Environment validation result"""
    component: str
    status: str  # 'pass', 'fail', 'warning'
    message: str
    details: Optional[Dict[str, Any]] = None

class Phase3IntegrationTestHelper:
    """
    Integration Test Configuration Helper for Sprint 14 Phase 3
    
    Provides:
    1. Environment validation and setup
    2. Test configuration management
    3. Database schema verification
    4. Redis connectivity validation
    5. Performance target management
    6. Test data utilities
    """
    
    def __init__(self, environment: str = 'test'):
        """Initialize test helper with environment-specific configuration"""
        self.environment = environment
        self.config = self._load_configuration()
        self.validation_results: List[ValidationResult] = []
    
    def _load_configuration(self) -> TestConfiguration:
        """Load environment-specific test configuration"""
        # Base configuration
        base_config = {
            'database': {
                'host': os.getenv('TEST_DB_HOST', 'localhost'),
                'database': os.getenv('TEST_DB_NAME', 'tickstock_test'),
                'user': os.getenv('TEST_DB_USER', 'app_readwrite'),
                'password': os.getenv('TEST_DB_PASSWORD', '4pp_U$3r_2024!'),
                'port': int(os.getenv('TEST_DB_PORT', '5432'))
            },
            'redis': {
                'host': os.getenv('TEST_REDIS_HOST', 'localhost'),
                'port': int(os.getenv('TEST_REDIS_PORT', '6379')),
                'db_integration': 15,
                'db_flows': 14,
                'db_resilience': 13
            },
            'performance_targets': {
                # ETF Universe Operations (seconds)
                'etf_expansion_time': 2.0,
                'etf_universe_query': 2.0,
                'etf_validation_time': 2.0,
                
                # Test Scenario Operations (seconds)
                'scenario_generation_time': 120.0,
                'scenario_loading_time': 120.0,
                
                # Cache Synchronization (seconds)
                'cache_sync_window': 1800.0,
                'redis_notification_delay': 5.0,
                
                # Database Performance (seconds)
                'ui_query_time': 0.05,
                'general_query_time': 0.5,
                'etf_query_time': 2.0,
                
                # Redis Performance (milliseconds)
                'message_delivery_time': 100.0,
                'message_success_rate': 95.0,
                
                # System Performance
                'memory_increase_limit': 100.0,  # MB
                'cpu_usage_limit': 80.0,  # percentage
                'recovery_time_database': 10.0,  # seconds
                'recovery_time_redis': 5.0  # seconds
            },
            'test_channels': {
                'universe_updated': 'tickstock.universe.updated',
                'cache_sync_complete': 'tickstock.cache.sync_complete',
                'etf_correlation_update': 'tickstock.etf.correlation_update',
                'universe_validation': 'tickstock.universe.validation_complete',
                'ipo_assignment': 'tickstock.cache.ipo_assignment',
                'delisting_cleanup': 'tickstock.cache.delisting_cleanup'
            },
            'test_data': {
                'test_symbol_prefix': 'TEST_',
                'test_cache_prefix': 'test_',
                'cleanup_on_teardown': True,
                'preserve_baseline_data': False,
                'max_test_symbols': 1000,
                'max_test_cache_entries': 100
            }
        }
        
        # Environment-specific overrides
        if self.environment == 'ci':
            base_config['performance_targets']['etf_expansion_time'] = 3.0  # More lenient for CI
            base_config['performance_targets']['message_delivery_time'] = 150.0  # CI tolerance
            base_config['database']['host'] = 'postgres'  # Docker service name
            base_config['redis']['host'] = 'redis'  # Docker service name
        
        elif self.environment == 'local':
            base_config['performance_targets']['memory_increase_limit'] = 150.0  # Local dev tolerance
        
        elif self.environment == 'staging':
            base_config['database']['database'] = 'tickstock_staging_test'
            base_config['performance_targets']['etf_expansion_time'] = 1.5  # Tighter for staging
        
        return TestConfiguration(
            database_config=base_config['database'],
            redis_config=base_config['redis'],
            performance_targets=base_config['performance_targets'],
            test_channels=base_config['test_channels'],
            test_data_config=base_config['test_data'],
            environment=self.environment
        )
    
    def validate_test_environment(self) -> List[ValidationResult]:
        """Comprehensive test environment validation"""
        self.validation_results = []
        
        # Validate database connectivity and schema
        db_result = self._validate_database()
        self.validation_results.append(db_result)
        
        # Validate Redis connectivity and configuration
        redis_result = asyncio.run(self._validate_redis())
        self.validation_results.append(redis_result)
        
        # Validate required Python dependencies
        deps_result = self._validate_dependencies()
        self.validation_results.append(deps_result)
        
        # Validate performance testing prerequisites
        perf_result = self._validate_performance_prerequisites()
        self.validation_results.append(perf_result)
        
        # Validate test data configuration
        data_result = self._validate_test_data_setup()
        self.validation_results.append(data_result)
        
        return self.validation_results
    
    def _validate_database(self) -> ValidationResult:
        """Validate database connectivity and Phase 3 schema requirements"""
        try:
            conn = psycopg2.connect(
                **self.config.database_config,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check Phase 3 schema enhancements
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'cache_entries' 
                AND column_name IN ('universe_category', 'liquidity_filter', 'universe_metadata', 'last_universe_update')
            """)
            columns = [row['column_name'] for row in cursor.fetchall()]
            
            required_columns = ['universe_category', 'liquidity_filter', 'universe_metadata', 'last_universe_update']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                return ValidationResult(
                    component='database_schema',
                    status='fail',
                    message=f'Missing Phase 3 schema columns: {missing_columns}',
                    details={'missing_columns': missing_columns}
                )
            
            # Check required database functions
            cursor.execute("""
                SELECT proname 
                FROM pg_proc 
                WHERE proname IN ('get_etf_universe', 'update_etf_universe', 'get_etf_universes_summary', 'validate_etf_universe_symbols')
            """)
            functions = [row['proname'] for row in cursor.fetchall()]
            
            required_functions = ['get_etf_universe', 'update_etf_universe', 'get_etf_universes_summary', 'validate_etf_universe_symbols']
            missing_functions = [func for func in required_functions if func not in functions]
            
            # Test basic query performance
            start_time = time.time()
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            query_time = (time.time() - start_time) * 1000  # ms
            
            conn.close()
            
            details = {
                'columns_found': columns,
                'functions_found': functions,
                'missing_functions': missing_functions,
                'query_performance_ms': query_time
            }
            
            if missing_functions:
                return ValidationResult(
                    component='database_functions',
                    status='warning',
                    message=f'Missing database functions: {missing_functions}',
                    details=details
                )
            
            if query_time > 100:  # Basic query should be fast
                return ValidationResult(
                    component='database_performance',
                    status='warning',
                    message=f'Basic query took {query_time:.1f}ms, may impact performance tests',
                    details=details
                )
            
            return ValidationResult(
                component='database',
                status='pass',
                message='Database connectivity and schema validated successfully',
                details=details
            )
            
        except Exception as e:
            return ValidationResult(
                component='database',
                status='fail',
                message=f'Database validation failed: {str(e)}',
                details={'error': str(e)}
            )
    
    async def _validate_redis(self) -> ValidationResult:
        """Validate Redis connectivity and configuration"""
        try:
            # Test all Redis databases used in testing
            redis_details = {}
            
            for db_name, db_num in [('integration', 15), ('flows', 14), ('resilience', 13)]:
                client = async_redis.Redis(
                    host=self.config.redis_config['host'],
                    port=self.config.redis_config['port'],
                    db=db_num,
                    decode_responses=True
                )
                
                # Test basic connectivity
                ping_start = time.time()
                ping_result = await client.ping()
                ping_time = (time.time() - ping_start) * 1000  # ms
                
                # Test pub-sub capability
                pubsub = client.pubsub()
                await pubsub.subscribe('test_channel')
                await client.publish('test_channel', 'test_message')
                await pubsub.unsubscribe('test_channel')
                await pubsub.aclose()
                
                # Get Redis info
                info = await client.info()
                redis_details[db_name] = {
                    'ping_time_ms': ping_time,
                    'version': info.get('redis_version'),
                    'memory_used': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients')
                }
                
                await client.aclose()
            
            return ValidationResult(
                component='redis',
                status='pass',
                message='Redis connectivity validated successfully',
                details=redis_details
            )
            
        except Exception as e:
            return ValidationResult(
                component='redis',
                status='fail',
                message=f'Redis validation failed: {str(e)}',
                details={'error': str(e)}
            )
    
    def _validate_dependencies(self) -> ValidationResult:
        """Validate required Python dependencies"""
        required_packages = [
            'pytest', 'pytest-asyncio', 'psycopg2', 'redis', 'psutil', 'numpy'
        ]
        
        optional_packages = [
            'talib'  # For pattern validation in test scenarios
        ]
        
        missing_required = []
        missing_optional = []
        found_versions = {}
        
        for package in required_packages:
            try:
                if package == 'psycopg2':
                    import psycopg2
                    found_versions[package] = psycopg2.__version__
                elif package == 'pytest':
                    import pytest
                    found_versions[package] = pytest.__version__
                elif package == 'pytest-asyncio':
                    import pytest_asyncio
                    found_versions[package] = getattr(pytest_asyncio, '__version__', 'unknown')
                elif package == 'redis':
                    import redis
                    found_versions[package] = redis.__version__
                elif package == 'psutil':
                    import psutil
                    found_versions[package] = psutil.__version__
                elif package == 'numpy':
                    import numpy
                    found_versions[package] = numpy.__version__
            except ImportError:
                missing_required.append(package)
        
        for package in optional_packages:
            try:
                if package == 'talib':
                    import talib
                    found_versions[package] = 'available'
            except ImportError:
                missing_optional.append(package)
        
        if missing_required:
            return ValidationResult(
                component='dependencies',
                status='fail',
                message=f'Missing required packages: {missing_required}',
                details={
                    'missing_required': missing_required,
                    'missing_optional': missing_optional,
                    'found_versions': found_versions
                }
            )
        
        status = 'pass' if not missing_optional else 'warning'
        message = 'All dependencies available' if not missing_optional else f'Optional packages missing: {missing_optional}'
        
        return ValidationResult(
            component='dependencies',
            status=status,
            message=message,
            details={
                'missing_optional': missing_optional,
                'found_versions': found_versions
            }
        )
    
    def _validate_performance_prerequisites(self) -> ValidationResult:
        """Validate system meets performance testing prerequisites"""
        try:
            import psutil
            
            # Check available memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            # Check CPU information
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Check disk space
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            
            details = {
                'available_memory_gb': round(available_gb, 2),
                'cpu_count': cpu_count,
                'cpu_freq_mhz': cpu_freq.current if cpu_freq else None,
                'free_disk_gb': round(free_gb, 2)
            }
            
            warnings = []
            
            if available_gb < 2.0:
                warnings.append(f'Low available memory: {available_gb:.1f}GB')
            
            if cpu_count < 2:
                warnings.append(f'Limited CPU cores: {cpu_count}')
            
            if free_gb < 5.0:
                warnings.append(f'Low disk space: {free_gb:.1f}GB')
            
            if warnings:
                return ValidationResult(
                    component='performance_prerequisites',
                    status='warning',
                    message=f'Performance testing constraints: {"; ".join(warnings)}',
                    details=details
                )
            
            return ValidationResult(
                component='performance_prerequisites',
                status='pass',
                message='System meets performance testing requirements',
                details=details
            )
            
        except Exception as e:
            return ValidationResult(
                component='performance_prerequisites',
                status='fail',
                message=f'Performance prerequisites validation failed: {str(e)}',
                details={'error': str(e)}
            )
    
    def _validate_test_data_setup(self) -> ValidationResult:
        """Validate test data configuration and cleanup capabilities"""
        try:
            # Check for existing test data that might interfere
            conn = psycopg2.connect(
                **self.config.database_config,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check for existing test symbols
            test_prefix = self.config.test_data_config['test_symbol_prefix']
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM symbols 
                WHERE symbol LIKE %s
            """, (f'{test_prefix}%',))
            existing_test_symbols = cursor.fetchone()['count']
            
            # Check for existing test cache entries
            cache_prefix = self.config.test_data_config['test_cache_prefix']
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM cache_entries 
                WHERE cache_key LIKE %s
            """, (f'{cache_prefix}%',))
            existing_test_cache = cursor.fetchone()['count']
            
            conn.close()
            
            details = {
                'existing_test_symbols': existing_test_symbols,
                'existing_test_cache_entries': existing_test_cache,
                'test_symbol_prefix': test_prefix,
                'test_cache_prefix': cache_prefix,
                'cleanup_enabled': self.config.test_data_config['cleanup_on_teardown']
            }
            
            warnings = []
            
            if existing_test_symbols > 100:
                warnings.append(f'Many existing test symbols: {existing_test_symbols}')
            
            if existing_test_cache > 50:
                warnings.append(f'Many existing test cache entries: {existing_test_cache}')
            
            if warnings:
                return ValidationResult(
                    component='test_data_setup',
                    status='warning',
                    message=f'Test data concerns: {"; ".join(warnings)}',
                    details=details
                )
            
            return ValidationResult(
                component='test_data_setup',
                status='pass',
                message='Test data setup validated successfully',
                details=details
            )
            
        except Exception as e:
            return ValidationResult(
                component='test_data_setup',
                status='fail',
                message=f'Test data setup validation failed: {str(e)}',
                details={'error': str(e)}
            )
    
    def setup_test_environment(self) -> bool:
        """Set up test environment based on validation results"""
        validation_results = self.validate_test_environment()
        
        # Check for any failed validations
        failures = [r for r in validation_results if r.status == 'fail']
        if failures:
            print("❌ Cannot set up test environment due to failures:")
            for failure in failures:
                print(f"   - {failure.component}: {failure.message}")
            return False
        
        # Show warnings
        warnings = [r for r in validation_results if r.status == 'warning']
        if warnings:
            print("⚠️  Test environment warnings:")
            for warning in warnings:
                print(f"   - {warning.component}: {warning.message}")
        
        # All validations passed (with possible warnings)
        print("✅ Test environment validation completed successfully")
        return True
    
    def cleanup_test_data(self):
        """Clean up test data after test execution"""
        if not self.config.test_data_config['cleanup_on_teardown']:
            return
        
        try:
            # Clean up database test data
            conn = psycopg2.connect(
                **self.config.database_config,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Remove test symbols
            test_prefix = self.config.test_data_config['test_symbol_prefix']
            cursor.execute("DELETE FROM symbols WHERE symbol LIKE %s", (f'{test_prefix}%',))
            
            # Remove test cache entries
            cache_prefix = self.config.test_data_config['test_cache_prefix']
            cursor.execute("DELETE FROM cache_entries WHERE cache_key LIKE %s", (f'{cache_prefix}%',))
            
            # Remove test historical data
            cursor.execute("DELETE FROM historical_data WHERE symbol LIKE %s", (f'{test_prefix}%',))
            
            conn.close()
            
            # Clean up Redis test data
            asyncio.run(self._cleanup_redis_data())
            
            print("🧹 Test data cleanup completed")
            
        except Exception as e:
            print(f"⚠️  Test data cleanup failed: {e}")
    
    async def _cleanup_redis_data(self):
        """Clean up Redis test data"""
        for db_num in [13, 14, 15]:  # Test databases
            client = async_redis.Redis(
                host=self.config.redis_config['host'],
                port=self.config.redis_config['port'],
                db=db_num,
                decode_responses=True
            )
            
            await client.flushdb()
            await client.aclose()
    
    def get_performance_target(self, target_name: str) -> float:
        """Get performance target by name"""
        return self.config.performance_targets.get(target_name, 0.0)
    
    def get_database_uri(self) -> str:
        """Get formatted database URI"""
        config = self.config.database_config
        return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    
    def print_configuration_summary(self):
        """Print test configuration summary"""
        print("📋 Phase 3 Integration Test Configuration")
        print(f"   Environment: {self.environment}")
        print(f"   Database: {self.config.database_config['host']}:{self.config.database_config['port']}/{self.config.database_config['database']}")
        print(f"   Redis: {self.config.redis_config['host']}:{self.config.redis_config['port']}")
        print(f"   Performance Targets:")
        for target, value in self.config.performance_targets.items():
            print(f"     - {target}: {value}")
        print(f"   Test Channels: {len(self.config.test_channels)} configured")

def main():
    """CLI interface for test configuration helper"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--validate':
            helper = Phase3IntegrationTestHelper()
            results = helper.validate_test_environment()
            
            print("🔍 Phase 3 Integration Test Environment Validation")
            for result in results:
                status_icon = "✅" if result.status == 'pass' else "⚠️" if result.status == 'warning' else "❌"
                print(f"{status_icon} {result.component}: {result.message}")
                
                if result.details and '--verbose' in sys.argv:
                    print(f"   Details: {json.dumps(result.details, indent=4)}")
            
            # Summary
            passed = len([r for r in results if r.status == 'pass'])
            warnings = len([r for r in results if r.status == 'warning'])
            failed = len([r for r in results if r.status == 'fail'])
            
            print(f"\n📊 Validation Summary: {passed} passed, {warnings} warnings, {failed} failed")
            
        elif command == '--setup':
            environment = sys.argv[2] if len(sys.argv) > 2 else 'test'
            helper = Phase3IntegrationTestHelper(environment=environment)
            
            success = helper.setup_test_environment()
            if success:
                helper.print_configuration_summary()
            else:
                sys.exit(1)
                
        elif command == '--cleanup':
            helper = Phase3IntegrationTestHelper()
            helper.cleanup_test_data()
            
        elif command == '--config':
            environment = sys.argv[2] if len(sys.argv) > 2 else 'test'
            helper = Phase3IntegrationTestHelper(environment=environment)
            helper.print_configuration_summary()
            
        else:
            print("Usage:")
            print("  --validate [--verbose]: Validate test environment")
            print("  --setup [environment]: Set up test environment (test/ci/local/staging)")
            print("  --cleanup: Clean up test data")
            print("  --config [environment]: Show configuration summary")
    else:
        print("Phase 3 Integration Test Configuration Helper")
        print("Use --help or see available commands above")

if __name__ == '__main__':
    main()