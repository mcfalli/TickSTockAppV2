#!/usr/bin/env python3
"""
Comprehensive Tests for Rapid Development Refresh - Sprint 14 Phase 4

Tests for incremental development data system including:
- Smart gap detection with <30 seconds full refresh capability  
- Docker container integration for isolated development environments
- Configuration profile management for different development needs
- Database reset/restore to baseline within 30 seconds
- 2-minute refresh target for 50 symbols with selective backfill

Author: TickStock Testing Framework
Sprint: 14 Phase 4
Test Category: Development/Refresh
Performance Targets: <30s reset, <2min refresh, 70% loading efficiency
"""

import pytest
import time
import json
import tempfile
import shutil
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock, call, mock_open
from typing import Dict, List, Any

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.development.rapid_development_refresh import (
    RapidDevelopmentRefresh,
    DevelopmentProfile
)

@pytest.fixture
def refresh_system():
    """Create RapidDevelopmentRefresh instance for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        system = RapidDevelopmentRefresh(
            database_uri="postgresql://test_user:test_password@localhost/test_db"
        )
        # Override paths to use temp directory
        system.dev_base_path = os.path.join(temp_dir, 'dev_environments')
        system.backup_path = os.path.join(temp_dir, 'backups')
        system.docker_volumes_path = os.path.join(temp_dir, 'docker_volumes')
        
        # Create directories
        os.makedirs(system.dev_base_path, exist_ok=True)
        os.makedirs(system.backup_path, exist_ok=True)
        os.makedirs(system.docker_volumes_path, exist_ok=True)
        
        yield system

@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit = Mock()
    mock_conn.rollback = Mock()
    mock_conn.close = Mock()
    
    # Mock query results
    mock_cursor.fetchone.return_value = {
        'first_date': date(2024, 1, 1),
        'last_date': date(2024, 6, 1),
        'record_count': 100
    }
    mock_cursor.fetchall.return_value = [
        {'date': date(2024, 1, 1)},
        {'date': date(2024, 1, 2)},
        {'date': date(2024, 1, 3)}
    ]
    mock_cursor.execute = Mock()
    
    return mock_conn

@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing"""
    mock_client = Mock()
    
    # Mock container operations
    mock_container = Mock()
    mock_container.id = "container_123"
    mock_container.status = 'running'
    mock_container.start = Mock()
    mock_container.ports = {'5432/tcp': [{'HostPort': '5432'}]}
    mock_container.exec_run.return_value.exit_code = 0
    mock_container.exec_run.return_value.output = b"Success"
    mock_container.put_archive = Mock()
    
    mock_client.containers.list.return_value = []
    mock_client.containers.run.return_value = mock_container
    mock_client.containers.get.return_value = mock_container
    
    return mock_client

@pytest.fixture
def sample_development_profiles():
    """Sample development profiles for testing"""
    return {
        'patterns': DevelopmentProfile(
            name='patterns',
            symbols_count=20,
            days_back=90,
            minute_data=True,
            description='Pattern detection development',
            priority_symbols=['AAPL', 'MSFT', 'TSLA'],
            universe_focus='high_volatility',
            refresh_frequency='daily'
        ),
        'ui_testing': DevelopmentProfile(
            name='ui_testing',
            symbols_count=10,
            days_back=30,
            minute_data=True,
            description='UI development testing',
            priority_symbols=['AAPL', 'GOOGL'],
            universe_focus='tech_leaders',
            refresh_frequency='hourly'
        )
    }

@pytest.fixture
def mock_gap_analysis_result():
    """Mock gap analysis result for testing"""
    return {
        'analysis_duration_seconds': 0.5,
        'symbols_analyzed': 5,
        'total_gaps': 3,
        'total_missing_days': 15,
        'gaps_by_symbol': {
            'AAPL': {
                'existing_records': 200,
                'expected_records': 220,
                'completeness_pct': 90.9,
                'first_date': '2024-01-01',
                'last_date': '2024-06-01',
                'gaps': [('2024-06-02', '2024-06-15')],
                'loading_strategy': 'incremental'
            },
            'MSFT': {
                'existing_records': 0,
                'expected_records': 220,
                'completeness_pct': 0,
                'first_date': None,
                'last_date': None,
                'gaps': [('2024-01-01', '2024-06-15')],
                'loading_strategy': 'full_load'
            }
        },
        'loading_efficiency_estimate': 0.75,
        'recommended_loading_order': ['MSFT', 'AAPL']
    }


class TestRapidDevelopmentRefresh:
    """Test suite for RapidDevelopmentRefresh system"""

    def test_initialization(self, refresh_system):
        """Test proper initialization of refresh system"""
        assert refresh_system.refresh_target_minutes == 2
        assert refresh_system.reset_target_seconds == 30
        assert refresh_system.gap_detection_efficiency_target == 0.7
        assert len(refresh_system.dev_profiles) == 4  # patterns, backtesting, ui_testing, etf_analysis

    def test_development_profiles_configuration(self, refresh_system):
        """Test development profiles are properly configured"""
        profiles = refresh_system.dev_profiles
        
        # Verify all required profiles exist
        required_profiles = {'patterns', 'backtesting', 'ui_testing', 'etf_analysis'}
        assert set(profiles.keys()) == required_profiles
        
        # Verify profile structure
        for name, profile in profiles.items():
            assert isinstance(profile, DevelopmentProfile)
            assert profile.name == name
            assert profile.symbols_count > 0
            assert profile.days_back > 0
            assert len(profile.priority_symbols) > 0
            assert profile.universe_focus is not None

    def test_database_connection_success(self, refresh_system, mock_database_connection):
        """Test successful database connection"""
        with patch('psycopg2.connect', return_value=mock_database_connection):
            conn = refresh_system.get_database_connection()
            
            assert conn is not None
            assert conn == mock_database_connection

    def test_database_connection_failure(self, refresh_system):
        """Test database connection failure handling"""
        with patch('psycopg2.connect', side_effect=Exception("Connection failed")):
            conn = refresh_system.get_database_connection()
            assert conn is None

    def test_get_development_symbols(self, refresh_system):
        """Test development symbol selection based on profile"""
        profile = refresh_system.dev_profiles['patterns']
        symbols = refresh_system.get_development_symbols(profile)
        
        assert len(symbols) == profile.symbols_count
        assert all(symbol in symbols for symbol in profile.priority_symbols)
        
        # Verify no duplicates
        assert len(symbols) == len(set(symbols))

    def test_universe_symbols_mapping(self, refresh_system):
        """Test universe symbol mapping for different focus areas"""
        # Test high volatility universe
        high_vol_symbols = refresh_system.get_universe_symbols('high_volatility', 5)
        assert 'TSLA' in high_vol_symbols or 'NVDA' in high_vol_symbols
        
        # Test tech leaders universe  
        tech_symbols = refresh_system.get_universe_symbols('tech_leaders', 5)
        assert 'AAPL' in tech_symbols or 'MSFT' in tech_symbols
        
        # Test ETF sectors
        etf_symbols = refresh_system.get_universe_symbols('etf_sectors', 5)
        assert any(symbol.startswith('XL') for symbol in etf_symbols)

    @pytest.mark.performance
    def test_rapid_refresh_performance_target(self, refresh_system, mock_database_connection):
        """Test rapid refresh meets <2 minute performance target"""
        with patch.object(refresh_system, 'get_database_connection', return_value=mock_database_connection):
            with patch.object(refresh_system, 'analyze_data_gaps') as mock_gaps:
                with patch.object(refresh_system, 'incremental_load_with_gaps') as mock_loading:
                    with patch.object(refresh_system, 'update_development_cache_entries') as mock_cache:
                        
                        # Mock return values for fast execution
                        mock_gaps.return_value = {'gaps_by_symbol': {}}
                        mock_loading.return_value = {'total_records_loaded': 100}
                        mock_cache.return_value = {'success': True}
                        
                        start_time = time.time()
                        result = refresh_system.rapid_refresh('patterns', 'test_dev')
                        refresh_duration = time.time() - start_time
                        
                        # Performance requirement: <2 minutes (120 seconds)
                        assert refresh_duration < 120, f"Refresh took {refresh_duration:.2f}s, expected <120s"
                        assert result['within_target'] == True

    def test_rapid_refresh_with_valid_profile(self, refresh_system, mock_database_connection, mock_gap_analysis_result):
        """Test rapid refresh with valid development profile"""
        with patch.object(refresh_system, 'get_database_connection', return_value=mock_database_connection):
            with patch.object(refresh_system, 'analyze_data_gaps', return_value=mock_gap_analysis_result):
                with patch.object(refresh_system, 'incremental_load_with_gaps') as mock_loading:
                    with patch.object(refresh_system, 'update_development_cache_entries') as mock_cache:
                        
                        mock_loading.return_value = {
                            'symbols_processed': 5,
                            'total_records_loaded': 500,
                            'loading_duration_seconds': 30
                        }
                        mock_cache.return_value = {'success': True}
                        
                        result = refresh_system.rapid_refresh('patterns', 'test_dev')
                        
                        assert 'error' not in result
                        assert result['profile'] == 'patterns'
                        assert result['developer'] == 'test_dev'
                        assert 'refresh_duration_seconds' in result
                        assert result['symbols_analyzed'] > 0

    def test_rapid_refresh_invalid_profile(self, refresh_system):
        """Test rapid refresh with invalid profile name"""
        result = refresh_system.rapid_refresh('invalid_profile', 'test_dev')
        
        assert 'error' in result
        assert 'Unknown profile' in result['error']

    def test_analyze_data_gaps_comprehensive(self, refresh_system, mock_database_connection):
        """Test comprehensive data gap analysis"""
        profile = refresh_system.dev_profiles['patterns']
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        with patch.object(refresh_system, 'get_database_connection', return_value=mock_database_connection):
            with patch.object(refresh_system, 'detect_specific_gaps', return_value=[(date(2024, 6, 1), date(2024, 6, 15))]):
                with patch.object(refresh_system, 'calculate_expected_trading_days', return_value=220):
                    
                    result = refresh_system.analyze_data_gaps(symbols, profile, 'test_dev')
                    
                    assert 'error' not in result
                    assert result['symbols_analyzed'] == len(symbols)
                    assert 'gaps_by_symbol' in result
                    assert 'loading_efficiency_estimate' in result

    def test_gap_detection_efficiency(self, refresh_system, mock_database_connection):
        """Test smart gap detection achieves 70%+ efficiency target"""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        profile = refresh_system.dev_profiles['patterns']
        
        # Mock database responses to simulate partial data
        mock_cursor = mock_database_connection.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            {'first_date': date(2024, 1, 1), 'last_date': date(2024, 5, 31), 'record_count': 150},  # AAPL - mostly complete
            {'first_date': date(2024, 3, 1), 'last_date': date(2024, 5, 31), 'record_count': 65},   # MSFT - partial
            {'first_date': None, 'last_date': None, 'record_count': 0},                              # GOOGL - empty
            {'first_date': date(2024, 1, 1), 'last_date': date(2024, 6, 1), 'record_count': 110},  # AMZN - complete
            {'first_date': date(2024, 2, 1), 'last_date': date(2024, 4, 30), 'record_count': 65}   # TSLA - gaps
        ]
        
        with patch.object(refresh_system, 'get_database_connection', return_value=mock_database_connection):
            with patch.object(refresh_system, 'detect_specific_gaps', return_value=[]):
                with patch.object(refresh_system, 'calculate_expected_trading_days', return_value=110):
                    
                    result = refresh_system.analyze_data_gaps(symbols, profile, 'test_dev')
                    
                    # Should achieve >70% loading efficiency by avoiding unnecessary loads
                    assert result['loading_efficiency_estimate'] >= 0.7

    def test_specific_gap_detection(self, refresh_system, mock_database_connection):
        """Test specific date gap detection in historical data"""
        mock_cursor = mock_database_connection.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {'date': date(2024, 1, 1)},
            {'date': date(2024, 1, 2)},
            # Gap: 2024-01-03 to 2024-01-05 missing
            {'date': date(2024, 1, 6)},
            {'date': date(2024, 1, 7)}
        ]
        
        with patch.object(refresh_system, 'calculate_expected_trading_days', return_value=1):
            gaps = refresh_system.detect_specific_gaps(
                mock_cursor, 'AAPL', date(2024, 1, 1), date(2024, 1, 10)
            )
            
            # Should detect the gap from Jan 3-5
            assert len(gaps) > 0
            gap_start, gap_end = gaps[0]
            assert gap_start >= date(2024, 1, 3)
            assert gap_end <= date(2024, 1, 5)

    def test_incremental_loading_with_gaps(self, refresh_system, mock_gap_analysis_result, mock_database_connection):
        """Test incremental loading based on gap analysis"""
        profile = refresh_system.dev_profiles['patterns']
        
        with patch.object(refresh_system, 'get_database_connection', return_value=mock_database_connection):
            with patch.object(refresh_system, 'load_symbol_gaps') as mock_load_symbol:
                mock_load_symbol.return_value = {
                    'success': True,
                    'gaps_filled': 2,
                    'records_loaded': 100,
                    'loading_strategy': 'incremental'
                }
                
                result = refresh_system.incremental_load_with_gaps(
                    mock_gap_analysis_result, profile, 'test_dev'
                )
                
                assert result['symbols_processed'] > 0
                assert result['total_records_loaded'] > 0
                assert 'loading_rate_records_per_second' in result

    def test_loading_efficiency_calculation(self, refresh_system, mock_gap_analysis_result):
        """Test loading efficiency calculation accuracy"""
        loading_results = {
            'total_records_loaded': 200,
            'symbols_processed': 2
        }
        
        efficiency = refresh_system.calculate_loading_efficiency(
            mock_gap_analysis_result, loading_results
        )
        
        assert 0.0 <= efficiency <= 1.0
        assert isinstance(efficiency, float)

    def test_symbol_loading_simulation(self, refresh_system):
        """Test symbol data loading simulation"""
        profile = refresh_system.dev_profiles['patterns']  # minute_data = True
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        records = refresh_system.simulate_gap_loading('AAPL', start_date, end_date, profile)
        
        # For minute data, should be ~390 records per trading day
        expected_trading_days = refresh_system.calculate_expected_trading_days(start_date, end_date)
        expected_records = expected_trading_days * 390  # Minutes per trading day
        
        assert records == expected_records
        assert records > 0

    def test_trading_days_calculation(self, refresh_system):
        """Test trading days calculation accuracy"""
        # Test weekday range (5 trading days)
        start_date = date(2024, 1, 1)  # Monday
        end_date = date(2024, 1, 5)    # Friday
        
        trading_days = refresh_system.calculate_expected_trading_days(start_date, end_date)
        
        # Should approximate 5 trading days (5/7 * 5 days = ~3.6, rounded up)
        assert trading_days >= 3
        assert trading_days <= 5

    @pytest.mark.performance
    def test_database_reset_performance_target(self, refresh_system):
        """Test database reset meets <30 second performance target"""
        baseline_file = os.path.join(refresh_system.backup_path, 'test_baseline.sql')
        
        # Create mock baseline file
        with open(baseline_file, 'w') as f:
            f.write("-- Test baseline\nSELECT 1;")
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stderr = ""
            
            start_time = time.time()
            result = refresh_system.database_reset_restore('test_dev', 'test_baseline')
            reset_duration = time.time() - start_time
            
            # Performance requirement: <30 seconds
            assert reset_duration < 30, f"Reset took {reset_duration:.2f}s, expected <30s"
            assert result['within_target'] == True

    def test_docker_environment_setup(self, refresh_system, mock_docker_client):
        """Test Docker environment setup for developer isolation"""
        refresh_system.docker_client = mock_docker_client
        
        result = refresh_system.setup_docker_environment('test_developer')
        
        assert 'error' not in result
        assert result['status'] in ['created', 'already_running', 'restarted']
        assert 'container_name' in result
        assert 'test_developer' in result['container_name']

    def test_docker_environment_existing_container(self, refresh_system, mock_docker_client):
        """Test Docker environment with existing running container"""
        # Mock existing running container
        mock_container = Mock()
        mock_container.status = 'running'
        mock_container.id = 'existing_123'
        mock_docker_client.containers.list.return_value = [mock_container]
        
        refresh_system.docker_client = mock_docker_client
        
        result = refresh_system.setup_docker_environment('test_developer')
        
        assert result['status'] == 'already_running'
        assert result['container_id'] == 'existing_123'

    def test_docker_environment_restart_stopped_container(self, refresh_system, mock_docker_client):
        """Test Docker environment restart of stopped container"""
        # Mock existing stopped container
        mock_container = Mock()
        mock_container.status = 'exited'
        mock_container.id = 'stopped_123'
        mock_container.start = Mock()
        mock_docker_client.containers.list.return_value = [mock_container]
        
        refresh_system.docker_client = mock_docker_client
        
        result = refresh_system.setup_docker_environment('test_developer')
        
        assert result['status'] == 'restarted'
        mock_container.start.assert_called_once()

    def test_developer_database_connection_docker(self, refresh_system, mock_docker_client):
        """Test developer-specific database connection via Docker"""
        # Mock Docker container with port mapping
        mock_container = Mock()
        mock_container.ports = {'5432/tcp': [{'HostPort': '5432'}]}
        mock_docker_client.containers.list.return_value = [mock_container]
        
        refresh_system.docker_client = mock_docker_client
        
        with patch.object(refresh_system, 'get_database_connection') as mock_get_conn:
            mock_get_conn.return_value = Mock()
            
            conn = refresh_system.get_developer_database_connection('test_dev')
            
            # Should have attempted connection with developer-specific URI
            mock_get_conn.assert_called_once()
            args = mock_get_conn.call_args[0]
            assert '5432' in args[0]  # Port should be mapped port
            assert 'test_dev' in args[0]  # Database name should include developer

    def test_docker_reset_restore(self, refresh_system, mock_docker_client):
        """Test Docker-based database reset and restore"""
        baseline_file = os.path.join(refresh_system.backup_path, 'test_baseline.sql')
        
        # Create mock baseline file
        with open(baseline_file, 'w') as f:
            f.write("-- Test baseline\nCREATE TABLE test (id INT);")
        
        # Mock container operations
        mock_container = Mock()
        mock_container.exec_run.return_value.exit_code = 0
        mock_container.put_archive = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        
        refresh_system.docker_client = mock_docker_client
        
        with patch('builtins.open', mock_open(read_data=b"baseline content")):
            result = refresh_system.docker_reset_restore('test_dev', baseline_file)
            
            assert result['method'] == 'docker'
            assert result['success'] == True
            assert 'test_dev' in result['database_name']

    def test_local_reset_restore(self, refresh_system):
        """Test local database reset and restore"""
        baseline_file = os.path.join(refresh_system.backup_path, 'test_baseline.sql')
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock all subprocess commands as successful
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stderr = ""
            
            result = refresh_system.local_reset_restore('test_dev', baseline_file)
            
            assert result['method'] == 'local'
            assert result['success'] == True
            assert 'test_dev' in result['database_name']
            
            # Should have called 3 commands (dropdb, createdb, psql)
            assert mock_subprocess.call_count == 3

    def test_baseline_snapshot_creation(self, refresh_system):
        """Test creation of baseline snapshot for rapid restore"""
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stderr = ""
            
            # Mock file size
            with patch('os.path.getsize', return_value=1024000):  # 1MB
                result = refresh_system.create_baseline_snapshot('test_baseline')
                
                assert result['success'] == True
                assert result['baseline_name'] == 'test_baseline'
                assert result['file_size_mb'] == 1.0

    def test_development_cache_entries_update(self, refresh_system, mock_database_connection):
        """Test update of development cache entries"""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        profile = refresh_system.dev_profiles['patterns']
        
        with patch.object(refresh_system, 'get_database_connection', return_value=mock_database_connection):
            result = refresh_system.update_development_cache_entries(symbols, profile, 'test_dev')
            
            assert result['success'] == True
            assert result['symbols_count'] == len(symbols)
            assert 'cache_key' in result
            assert 'test_dev' in result['cache_key']

    def test_loading_order_prioritization(self, refresh_system, mock_gap_analysis_result):
        """Test optimal loading order prioritization"""
        profile = refresh_system.dev_profiles['patterns']
        gaps_by_symbol = mock_gap_analysis_result['gaps_by_symbol']
        
        loading_order = refresh_system.prioritize_loading_order(gaps_by_symbol, profile)
        
        assert len(loading_order) == len(gaps_by_symbol)
        assert isinstance(loading_order, list)
        
        # Priority symbols should come first if they have gaps
        for priority_symbol in profile.priority_symbols:
            if priority_symbol in gaps_by_symbol:
                priority_index = loading_order.index(priority_symbol)
                # Should be in first half of loading order
                assert priority_index < len(loading_order) / 2

    @pytest.mark.integration
    def test_end_to_end_rapid_refresh(self, refresh_system, mock_database_connection):
        """Test complete end-to-end rapid refresh workflow"""
        # Mock all database operations
        with patch.object(refresh_system, 'get_database_connection', return_value=mock_database_connection):
            with patch.object(refresh_system, 'get_developer_database_connection', return_value=None):
                # Mock gap analysis
                with patch.object(refresh_system, 'detect_specific_gaps', return_value=[]):
                    with patch.object(refresh_system, 'calculate_expected_trading_days', return_value=65):
                        
                        # Execute complete workflow
                        result = refresh_system.rapid_refresh('ui_testing', 'integration_test_dev')
                        
                        # Verify end-to-end success
                        assert 'error' not in result
                        assert result['profile'] == 'ui_testing'
                        assert result['developer'] == 'integration_test_dev'
                        assert result['symbols_analyzed'] == 10  # ui_testing profile symbol count
                        assert 'efficiency_achieved' in result

    def test_configuration_profile_management(self, refresh_system):
        """Test configuration profile management for different development needs"""
        # Test patterns profile
        patterns_profile = refresh_system.dev_profiles['patterns']
        assert patterns_profile.minute_data == True
        assert patterns_profile.universe_focus == 'high_volatility'
        assert 'AAPL' in patterns_profile.priority_symbols
        
        # Test backtesting profile
        backtesting_profile = refresh_system.dev_profiles['backtesting']
        assert backtesting_profile.days_back == 365
        assert backtesting_profile.universe_focus == 'broad_market'
        assert backtesting_profile.symbols_count == 50
        
        # Test UI testing profile
        ui_profile = refresh_system.dev_profiles['ui_testing']
        assert ui_profile.days_back == 30
        assert ui_profile.symbols_count == 10
        assert ui_profile.refresh_frequency == 'hourly'

    def test_error_handling_database_failure(self, refresh_system):
        """Test error handling when database operations fail"""
        with patch.object(refresh_system, 'get_database_connection', return_value=None):
            result = refresh_system.rapid_refresh('patterns', 'test_dev')
            
            # Should handle database failure gracefully
            assert 'error' in result or result['gaps_analysis'].get('error') is not None

    def test_error_handling_docker_unavailable(self, refresh_system):
        """Test error handling when Docker is unavailable"""
        refresh_system.docker_client = None
        
        result = refresh_system.setup_docker_environment('test_dev')
        
        assert 'error' in result
        assert 'Docker not available' in result['error']

    @pytest.mark.performance
    def test_50_symbol_refresh_performance(self, refresh_system, mock_database_connection):
        """Test 2-minute refresh target specifically for 50 symbols"""
        # Use backtesting profile which has 50 symbols
        with patch.object(refresh_system, 'get_database_connection', return_value=mock_database_connection):
            with patch.object(refresh_system, 'calculate_expected_trading_days', return_value=65):
                with patch.object(refresh_system, 'detect_specific_gaps', return_value=[]):
                    
                    start_time = time.time()
                    result = refresh_system.rapid_refresh('backtesting', 'perf_test')
                    duration = time.time() - start_time
                    
                    # Should handle 50 symbols in under 2 minutes
                    assert duration < 120  # 2 minutes in seconds
                    assert result['symbols_analyzed'] == 50


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])