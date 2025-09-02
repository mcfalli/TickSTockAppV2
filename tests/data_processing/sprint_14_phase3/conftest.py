#!/usr/bin/env python3
"""
Sprint 14 Phase 3 Test Fixtures and Utilities

Comprehensive fixtures and utilities for Phase 3 advanced features testing:
- ETF Universe Manager test fixtures with realistic data
- Test Scenario Generator fixtures with pattern validation
- Cache Entries Synchronizer fixtures with change tracking
- Performance testing utilities and benchmarking tools
- Mock Redis and database services for isolated testing

Test Support:
- Realistic ETF metadata and universe data
- Synthetic OHLCV data generators for scenario testing  
- Synchronization change builders and validators
- Performance timing utilities and assertions
- Integration test helpers and mock services
"""

import pytest
import asyncio
import json
import os
import sys
import time
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from decimal import Decimal
import psycopg2.extras

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.data.etf_universe_manager import ETFMetadata
from src.data.test_scenario_generator import ScenarioConfig
from src.data.cache_entries_synchronizer import SynchronizationChange

# ====================================================================
# ETF Universe Manager Fixtures
# ====================================================================

@pytest.fixture
def sample_etf_metadata():
    """Sample ETF metadata for testing"""
    return ETFMetadata(
        symbol='XLF',
        name='Financial Select Sector SPDR Fund',
        aum=40e9,
        expense_ratio=0.12,
        avg_volume=50e6,
        underlying_index='S&P 500 Financial Sector',
        sector_focus='financial',
        inception_date='1998-12-16',
        dividend_yield=1.8
    )

@pytest.fixture
def etf_universe_sample_data():
    """Sample ETF universe data for comprehensive testing"""
    return {
        'etf_sectors': {
            'symbols': ['XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLB', 'XLRE', 'XLU', 'XLY', 'XLP'],
            'universe_category': 'ETF',
            'liquidity_filter': {
                'min_aum': 1000000000,
                'min_volume': 5000000,
                'min_liquidity_score': 85
            },
            'universe_metadata': {
                'theme': 'Sector ETFs',
                'description': 'SPDR Select Sector ETFs covering major market sectors',
                'count': 10,
                'criteria': 'AUM > $1B, Volume > 5M daily',
                'focus': 'sector_rotation',
                'rebalance_frequency': 'quarterly',
                'correlation_tracking': True
            }
        },
        'etf_technology': {
            'symbols': ['QQQ', 'XLK', 'VGT', 'FTEC', 'SOXX', 'ARKK', 'SKYY', 'ROBO'],
            'universe_category': 'ETF',
            'liquidity_filter': {
                'min_aum': 500000000,
                'min_volume': 3000000,
                'technology_focus': True
            },
            'universe_metadata': {
                'theme': 'Technology ETFs',
                'description': 'Technology sector and innovation-focused ETFs',
                'count': 8,
                'criteria': 'Technology focus, Innovation exposure',
                'focus': 'technology_innovation',
                'sub_sectors': ['software', 'semiconductors', 'cloud', 'ai_robotics'],
                'growth_orientation': True
            }
        }
    }

@pytest.fixture
def etf_validation_results():
    """Sample ETF validation results for testing"""
    return [
        {
            'universe_key': 'etf_sectors',
            'symbol': 'XLF',
            'exists_in_symbols': True,
            'symbol_type': 'ETF',
            'active_status': True
        },
        {
            'universe_key': 'etf_sectors',
            'symbol': 'XLE',
            'exists_in_symbols': True,
            'symbol_type': 'ETF',
            'active_status': True
        },
        {
            'universe_key': 'etf_sectors',
            'symbol': 'MISSING_ETF',
            'exists_in_symbols': False,
            'symbol_type': 'UNKNOWN',
            'active_status': False
        },
        {
            'universe_key': 'etf_technology',
            'symbol': 'QQQ',
            'exists_in_symbols': True,
            'symbol_type': 'ETF',
            'active_status': True
        }
    ]

# ====================================================================
# Test Scenario Generator Fixtures
# ====================================================================

@pytest.fixture
def sample_scenario_config():
    """Sample scenario configuration for testing"""
    return ScenarioConfig(
        name='test_crash_scenario',
        description='Test market crash scenario for validation',
        length=126,  # 6 months
        base_price=150.0,
        volatility_profile='extreme',
        trend_direction='mixed',
        volume_profile='spike',
        pattern_features=['high_low_events', 'volatility_surge', 'volume_spike', 'trend_reversal'],
        expected_outcomes={
            'max_drawdown': -25.0,
            'volatility_spike_count': 8,
            'high_low_events': 6,
            'recovery_pattern': 'v_shaped',
            'total_return': -5.0
        }
    )

@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for scenario testing"""
    np.random.seed(42)  # Reproducible data
    
    base_price = 100.0
    ohlcv_data = []
    
    for i in range(50):  # 50 trading days
        # Generate realistic price movement
        daily_return = np.random.normal(0.001, 0.025)  # Slight upward bias with volatility
        close_price = base_price * (1 + daily_return)
        
        # Generate realistic OHLC
        daily_range = close_price * np.random.uniform(0.02, 0.05)
        high_price = close_price + np.random.uniform(0.3, 0.7) * daily_range
        low_price = close_price - np.random.uniform(0.3, 0.7) * daily_range
        
        # Open price based on previous close with gap potential
        if i > 0:
            gap_factor = np.random.normal(0, 0.01)
            open_price = base_price * (1 + gap_factor)
        else:
            open_price = close_price
        
        # Ensure OHLC relationships
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Generate volume
        volume = int(np.random.uniform(1500000, 4000000))
        
        ohlcv_data.append({
            'symbol': 'TEST_SCENARIO',
            'date': date.today() - timedelta(days=50-i),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        
        base_price = close_price
    
    return ohlcv_data

@pytest.fixture
def scenario_validation_data():
    """Validation data for scenario pattern testing"""
    return {
        'crash_2020': {
            'expected_phases': ['normal', 'crash', 'recovery'],
            'expected_drawdown_range': (-40.0, -25.0),
            'expected_volatility_spikes': (10, 20),
            'expected_volume_spikes': (5, 15)
        },
        'growth_2021': {
            'expected_phases': ['recovery', 'momentum', 'consolidation'],
            'expected_return_range': (15.0, 35.0),
            'expected_trend_strength': (0.6, 0.9),
            'expected_breakout_count': (3, 10)
        },
        'volatility_periods': {
            'expected_volatility_clustering': True,
            'expected_mean_reversion': True,
            'expected_trading_range': (20.0, 40.0),
            'expected_volatility_periods': (2, 5)
        }
    }

# ====================================================================
# Cache Entries Synchronizer Fixtures  
# ====================================================================

@pytest.fixture
def sample_sync_change():
    """Sample synchronization change for testing"""
    return SynchronizationChange(
        change_type='market_cap_update',
        universe='top_500',
        symbol='AAPL',
        action='added',
        reason='Market cap ranking qualified for top_500',
        timestamp=datetime.now(),
        metadata={'market_cap_rank': 15, 'previous_rank': None}
    )

@pytest.fixture
def market_cap_ranking_data():
    """Sample market cap ranking data for synchronization testing"""
    return [
        {
            'symbol': 'AAPL',
            'market_cap': 3000e9,
            'sector': 'Technology',
            'name': 'Apple Inc.',
            'rank': 1
        },
        {
            'symbol': 'MSFT',
            'market_cap': 2500e9,
            'sector': 'Technology',
            'name': 'Microsoft Corporation',
            'rank': 2
        },
        {
            'symbol': 'GOOGL',
            'market_cap': 1800e9,
            'sector': 'Communication Services',
            'name': 'Alphabet Inc.',
            'rank': 3
        },
        {
            'symbol': 'AMZN',
            'market_cap': 1500e9,
            'sector': 'Consumer Discretionary',
            'name': 'Amazon.com Inc.',
            'rank': 4
        },
        {
            'symbol': 'TSLA',
            'market_cap': 800e9,
            'sector': 'Consumer Discretionary',
            'name': 'Tesla Inc.',
            'rank': 5
        }
    ]

@pytest.fixture
def ipo_assignment_data():
    """Sample IPO data for universe assignment testing"""
    return [
        {
            'symbol': 'NEWIPO1',
            'sector': 'Technology',
            'market_cap': 15e9,
            'industry': 'Software',
            'name': 'New Tech IPO Corp.',
            'type': 'CS'
        },
        {
            'symbol': 'NEWIPO2',
            'sector': 'Healthcare',
            'market_cap': 8e9,
            'industry': 'Biotechnology',
            'name': 'Bio Innovation Inc.',
            'type': 'CS'
        },
        {
            'symbol': 'NEWETF1',
            'sector': 'Financial',
            'market_cap': 2e9,
            'industry': 'ETF',
            'name': 'New Theme ETF',
            'type': 'ETF'
        }
    ]

@pytest.fixture
def sync_task_results():
    """Sample synchronization task results for testing"""
    return {
        'market_cap_recalculation': {
            'status': 'completed',
            'changes_count': 15,
            'duration_seconds': 2.5,
            'changes': [
                SynchronizationChange(
                    'market_cap_update', 'top_100', 'AAPL', 'added',
                    'Market cap increase', datetime.now(), {'rank': 1}
                )
            ]
        },
        'ipo_universe_assignment': {
            'status': 'completed',
            'changes_count': 3,
            'duration_seconds': 1.2,
            'changes': [
                SynchronizationChange(
                    'ipo_assignment', 'tech_growth', 'NEWIPO1', 'added',
                    'New IPO assignment', datetime.now(), {'sector': 'Technology'}
                )
            ]
        },
        'delisted_cleanup': {
            'status': 'completed',
            'changes_count': 0,
            'duration_seconds': 0.8,
            'changes': []
        },
        'theme_rebalancing': {
            'status': 'completed',
            'changes_count': 0,
            'duration_seconds': 0.3,
            'changes': []
        },
        'etf_universe_maintenance': {
            'status': 'completed',
            'changes_count': 7,
            'duration_seconds': 1.8,
            'changes': [
                SynchronizationChange(
                    'etf_maintenance', 'etf_sectors', None, 'updated',
                    'ETF universe metadata refresh', datetime.now(),
                    {'symbol_count': 10}
                )
            ]
        }
    }

# ====================================================================
# Performance Testing Utilities
# ====================================================================

@pytest.fixture
def performance_timer():
    """Performance timing utility for testing"""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = 0
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            if self.start_time is None:
                raise ValueError("Timer not started")
            self.end_time = time.time()
            self.elapsed = self.end_time - self.start_time
        
        def reset(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = 0
        
        def assert_under(self, max_seconds, message=None):
            if self.elapsed >= max_seconds:
                msg = message or f"Operation took {self.elapsed:.3f}s, expected <{max_seconds}s"
                pytest.fail(msg)
        
        def assert_over(self, min_seconds, message=None):
            if self.elapsed <= min_seconds:
                msg = message or f"Operation took {self.elapsed:.3f}s, expected >{min_seconds}s"
                pytest.fail(msg)
    
    return PerformanceTimer()

@pytest.fixture
def performance_benchmarks():
    """Performance benchmark thresholds for Phase 3 features"""
    return {
        'etf_universe_expansion': {
            'max_duration': 2.0,  # <2 seconds for 200+ ETF processing
            'min_etf_count': 40,   # At least 40 ETFs across themes
            'themes_required': 7   # All 7 themes processed
        },
        'scenario_generation': {
            'max_duration': 120.0,  # <2 minutes for full scenario
            'min_data_points': 50,  # At least 50 trading days
            'max_memory_mb': 100    # <100MB memory usage
        },
        'cache_synchronization': {
            'max_duration': 1800.0,  # <30 minutes for daily sync
            'redis_publish_max': 5.0, # <5 seconds for Redis delivery
            'eod_wait_timeout': 3600  # 1 hour max wait for EOD
        },
        'database_operations': {
            'etf_query_max': 2.0,     # <2 seconds for ETF queries
            'universe_update_max': 1.0, # <1 second for universe updates
            'validation_max': 0.5      # <0.5 seconds for validation
        },
        'integration_workflows': {
            'end_to_end_max': 10.0,   # <10 seconds for complete workflow (mocked)
            'concurrent_max': 5.0,    # <5 seconds for concurrent operations
            'redis_throughput_min': 10 # >10 messages/second throughput
        }
    }

# ====================================================================
# Mock Database Services
# ====================================================================

@pytest.fixture
def mock_database():
    """Mock database connection and cursor for testing"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Default successful responses
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.rowcount = 0
    
    return mock_conn, mock_cursor

@pytest.fixture
def mock_etf_database_responses(mock_database, etf_universe_sample_data):
    """Mock database responses specific to ETF operations"""
    mock_conn, mock_cursor = mock_database
    
    # Setup ETF-specific responses
    etf_responses = {
        'get_etf_universe': lambda theme: [{
            'cache_key': f'etf_{theme}',
            'symbols': etf_universe_sample_data.get(f'etf_{theme}', {}).get('symbols', []),
            'metadata': etf_universe_sample_data.get(f'etf_{theme}', {}).get('universe_metadata', {}),
            'liquidity_filter': etf_universe_sample_data.get(f'etf_{theme}', {}).get('liquidity_filter', {}),
            'last_updated': datetime.now(),
            'filtered': True
        }],
        'update_etf_universe': lambda theme, symbols, metadata: [{
            'action': 'updated' if theme in ['sectors', 'technology'] else 'created',
            'cache_key': f'etf_{theme}',
            'symbols_count': len(json.loads(symbols)) if isinstance(symbols, str) else len(symbols),
            'added_count': 2,
            'removed_count': 0,
            'timestamp': datetime.now()
        }],
        'validate_etf_universe_symbols': lambda: [
            {
                'universe_key': 'etf_sectors',
                'symbol': 'XLF',
                'exists_in_symbols': True,
                'symbol_type': 'ETF',
                'active_status': True
            }
        ]
    }
    
    return mock_conn, mock_cursor, etf_responses

# ====================================================================
# Mock Redis Services
# ====================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    mock_client = AsyncMock()
    
    # Default successful responses
    mock_client.ping.return_value = True
    mock_client.publish.return_value = 1
    mock_client.blpop.return_value = ('eod_complete', 'signal')
    
    return mock_client

@pytest.fixture
def redis_message_capture():
    """Redis message capture utility for testing"""
    captured_messages = []
    
    async def capture_publish(channel, message):
        captured_messages.append({
            'channel': channel,
            'message': json.loads(message) if isinstance(message, str) else message,
            'timestamp': datetime.now().isoformat()
        })
        return 1
    
    def get_messages():
        return captured_messages
    
    def get_messages_by_channel(channel):
        return [msg for msg in captured_messages if msg['channel'] == channel]
    
    def clear_messages():
        captured_messages.clear()
    
    return {
        'capture_publish': capture_publish,
        'get_messages': get_messages,
        'get_messages_by_channel': get_messages_by_channel,
        'clear_messages': clear_messages
    }

# ====================================================================
# Data Generation Utilities
# ====================================================================

@pytest.fixture
def etf_data_generator():
    """ETF data generator utility for testing"""
    def generate_etf_metadata(
        symbol_prefix='TEST_ETF',
        count=10,
        min_aum=1e9,
        max_aum=100e9,
        sector_focus='technology'
    ):
        etfs = []
        for i in range(count):
            aum = np.random.uniform(min_aum, max_aum)
            volume = np.random.uniform(1e6, 50e6)
            expense_ratio = np.random.uniform(0.05, 0.75)
            dividend_yield = np.random.uniform(0.5, 4.0)
            
            etfs.append(ETFMetadata(
                symbol=f'{symbol_prefix}_{i:02d}',
                name=f'Test ETF {i}',
                aum=aum,
                expense_ratio=expense_ratio,
                avg_volume=int(volume),
                underlying_index=f'Test Index {i}',
                sector_focus=sector_focus,
                inception_date=f'20{i:02d}-01-01',
                dividend_yield=dividend_yield
            ))
        
        return etfs
    
    def generate_universe_data(theme, symbols_list, metadata_override=None):
        base_metadata = {
            'theme': theme.title(),
            'description': f'{theme.title()} ETFs for testing',
            'count': len(symbols_list),
            'criteria': 'Test criteria',
            'focus': theme.lower(),
            'updated': datetime.now().isoformat()
        }
        
        if metadata_override:
            base_metadata.update(metadata_override)
        
        return {
            'cache_key': f'etf_{theme}',
            'symbols': symbols_list,
            'universe_category': 'ETF',
            'liquidity_filter': {
                'min_aum': 1000000000,
                'min_volume': 5000000
            },
            'universe_metadata': base_metadata
        }
    
    return {
        'generate_etf_metadata': generate_etf_metadata,
        'generate_universe_data': generate_universe_data
    }

@pytest.fixture  
def scenario_data_generator():
    """Scenario data generator utility for testing"""
    def generate_realistic_ohlcv(
        symbol='TEST_SCENARIO',
        days=100,
        base_price=100.0,
        volatility=0.02,
        trend=0.001,
        volume_base=2000000
    ):
        np.random.seed(42)  # Reproducible
        
        ohlcv_data = []
        current_price = base_price
        
        for i in range(days):
            # Generate return with trend and volatility
            daily_return = np.random.normal(trend, volatility)
            current_price *= (1 + daily_return)
            
            # Generate OHLC
            daily_range = current_price * np.random.uniform(0.01, 0.05)
            high = current_price + np.random.uniform(0.3, 0.7) * daily_range
            low = current_price - np.random.uniform(0.3, 0.7) * daily_range
            
            # Open based on previous close with gaps
            if i > 0:
                gap = np.random.normal(0, volatility * 0.5)
                open_price = prev_close * (1 + gap)
            else:
                open_price = current_price
            
            # Ensure OHLC relationships
            high = max(high, open_price, current_price)
            low = min(low, open_price, current_price)
            
            # Generate volume with some correlation to volatility
            volume_multiplier = 1 + abs(daily_return) / volatility
            volume = int(volume_base * volume_multiplier * np.random.uniform(0.7, 1.5))
            
            ohlcv_data.append({
                'symbol': symbol,
                'date': date.today() - timedelta(days=days-i-1),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(current_price, 2),
                'volume': volume
            })
            
            prev_close = current_price
        
        return ohlcv_data
    
    def inject_high_low_events(ohlcv_data, event_frequency=10):
        """Inject high/low events into OHLCV data"""
        modified_data = ohlcv_data.copy()
        
        for i in range(event_frequency, len(modified_data), event_frequency):
            if np.random.random() > 0.5:  # High event
                factor = np.random.uniform(1.05, 1.15)  # 5-15% increase
            else:  # Low event
                factor = np.random.uniform(0.85, 0.95)  # 5-15% decrease
            
            # Modify the close price and adjust OHLC accordingly
            original_close = modified_data[i]['close']
            new_close = original_close * factor
            
            modified_data[i]['close'] = round(new_close, 2)
            modified_data[i]['high'] = max(modified_data[i]['high'], new_close)
            modified_data[i]['low'] = min(modified_data[i]['low'], new_close)
            
            # Increase volume for event days
            modified_data[i]['volume'] = int(modified_data[i]['volume'] * np.random.uniform(2.0, 4.0))
        
        return modified_data
    
    return {
        'generate_realistic_ohlcv': generate_realistic_ohlcv,
        'inject_high_low_events': inject_high_low_events
    }

@pytest.fixture
def sync_change_builder():
    """Synchronization change builder utility for testing"""
    def build_market_cap_changes(symbols, universe, action='added'):
        changes = []
        for i, symbol in enumerate(symbols):
            changes.append(SynchronizationChange(
                change_type='market_cap_update',
                universe=universe,
                symbol=symbol,
                action=action,
                reason=f'Market cap ranking {action} for {universe}',
                timestamp=datetime.now() - timedelta(minutes=i),
                metadata={'rank': i + 1}
            ))
        return changes
    
    def build_ipo_assignments(ipo_data):
        changes = []
        for ipo in ipo_data:
            universes = ['stock_universe']  # Default assignment
            if ipo.get('sector') == 'Technology':
                universes.append('tech_growth')
            elif ipo.get('type') == 'ETF':
                universes.append('etf_universe')
            
            for universe in universes:
                changes.append(SynchronizationChange(
                    change_type='ipo_assignment',
                    universe=universe,
                    symbol=ipo['symbol'],
                    action='added',
                    reason=f"New IPO - {ipo.get('sector', 'Unknown')} sector",
                    timestamp=datetime.now(),
                    metadata={
                        'sector': ipo.get('sector'),
                        'market_cap': ipo.get('market_cap'),
                        'symbol_type': ipo.get('type')
                    }
                ))
        
        return changes
    
    def build_etf_maintenance_changes(etf_universes):
        changes = []
        for cache_key, universe_data in etf_universes.items():
            changes.append(SynchronizationChange(
                change_type='etf_maintenance',
                universe=cache_key,
                symbol=None,
                action='updated',
                reason='ETF universe metadata refresh',
                timestamp=datetime.now(),
                metadata={
                    'symbol_count': len(universe_data.get('symbols', [])),
                    'theme': universe_data.get('universe_metadata', {}).get('theme', 'Unknown')
                }
            ))
        
        return changes
    
    return {
        'build_market_cap_changes': build_market_cap_changes,
        'build_ipo_assignments': build_ipo_assignments,
        'build_etf_maintenance_changes': build_etf_maintenance_changes
    }

# ====================================================================
# Test Validation Utilities
# ====================================================================

@pytest.fixture
def validation_helpers():
    """Validation helper utilities for testing"""
    def validate_etf_metadata(etf_metadata_list):
        """Validate ETF metadata structure and constraints"""
        assert isinstance(etf_metadata_list, list), "ETF metadata should be a list"
        
        for etf in etf_metadata_list:
            # Required fields
            assert etf.symbol is not None, "ETF symbol is required"
            assert etf.name is not None, "ETF name is required"
            assert etf.aum is not None and etf.aum > 0, "ETF AUM must be positive"
            
            # Constraint validation
            assert etf.expense_ratio is not None and 0 <= etf.expense_ratio <= 2.0, "Invalid expense ratio"
            assert etf.avg_volume is not None and etf.avg_volume > 0, "Volume must be positive"
            
            # Optional fields with validation
            if etf.dividend_yield is not None:
                assert 0 <= etf.dividend_yield <= 10.0, "Invalid dividend yield"
    
    def validate_ohlcv_data(ohlcv_data):
        """Validate OHLCV data structure and relationships"""
        assert isinstance(ohlcv_data, list), "OHLCV data should be a list"
        assert len(ohlcv_data) > 0, "OHLCV data should not be empty"
        
        for record in ohlcv_data:
            # Required fields
            required_fields = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            for field in required_fields:
                assert field in record, f"Missing required field: {field}"
            
            # OHLC relationships
            assert record['high'] >= record['open'], "High must be >= Open"
            assert record['high'] >= record['close'], "High must be >= Close"
            assert record['low'] <= record['open'], "Low must be <= Open"
            assert record['low'] <= record['close'], "Low must be <= Close"
            
            # Value constraints
            assert record['volume'] > 0, "Volume must be positive"
            assert record['high'] > 0, "Prices must be positive"
    
    def validate_sync_changes(sync_changes):
        """Validate synchronization changes structure"""
        assert isinstance(sync_changes, list), "Sync changes should be a list"
        
        for change in sync_changes:
            # Required fields
            assert change.change_type is not None, "Change type is required"
            assert change.universe is not None, "Universe is required"
            assert change.action in ['added', 'removed', 'updated'], "Invalid action"
            assert change.reason is not None, "Reason is required"
            assert change.timestamp is not None, "Timestamp is required"
            assert change.metadata is not None, "Metadata is required"
    
    def validate_redis_message_format(message):
        """Validate Redis message format consistency"""
        assert isinstance(message, dict), "Message should be a dictionary"
        
        # Required fields for all messages
        required_fields = ['timestamp', 'service', 'event_type']
        for field in required_fields:
            assert field in message, f"Missing required field: {field}"
        
        # Validate timestamp format (ISO 8601)
        timestamp = message['timestamp']
        assert 'T' in timestamp, "Timestamp should be in ISO format"
        
        # Validate service naming
        valid_services = ['etf_universe_manager', 'cache_entries_synchronizer', 'test_scenario_generator']
        assert message['service'] in valid_services, f"Invalid service name: {message['service']}"
    
    def validate_performance_metrics(duration, max_duration, operation_name):
        """Validate performance metrics against requirements"""
        assert duration < max_duration, f"{operation_name} took {duration:.3f}s, expected <{max_duration}s"
        
        if duration < 0.001:  # Less than 1ms might indicate mocking
            pytest.skip(f"{operation_name} completed too quickly, likely mocked")
    
    return {
        'validate_etf_metadata': validate_etf_metadata,
        'validate_ohlcv_data': validate_ohlcv_data,
        'validate_sync_changes': validate_sync_changes,
        'validate_redis_message_format': validate_redis_message_format,
        'validate_performance_metrics': validate_performance_metrics
    }