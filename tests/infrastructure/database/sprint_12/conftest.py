"""
Pytest configuration and fixtures for CacheEntriesSynchronizer tests.

Provides comprehensive test fixtures, mock data generators, and shared utilities
for testing the cache synchronization service.
"""

import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, MagicMock
import psycopg2
from psycopg2.extras import RealDictCursor
import redis


@pytest.fixture(scope="function")
def sample_stocks():
    """Sample stock data covering all market cap categories."""
    return [
        # Mega cap stocks (>= $200B)
        {'symbol': 'AAPL', 'name': 'Apple Inc.', 'market_cap': 3000000000000, 'sector': 'Technology', 'industry': 'Consumer Electronics', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'market_cap': 2800000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'market_cap': 2000000000000, 'sector': 'Technology', 'industry': 'Internet Content & Information', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'market_cap': 1800000000000, 'sector': 'Consumer Discretionary', 'industry': 'Internet Retail', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'market_cap': 1600000000000, 'sector': 'Technology', 'industry': 'Semiconductors', 'primary_exchange': 'NASDAQ'},
        
        # Large cap stocks ($10B - $200B)
        {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'market_cap': 500000000000, 'sector': 'Financial Services', 'industry': 'Banks', 'primary_exchange': 'NYSE'},
        {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'market_cap': 450000000000, 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'primary_exchange': 'NYSE'},
        {'symbol': 'V', 'name': 'Visa Inc.', 'market_cap': 420000000000, 'sector': 'Financial Services', 'industry': 'Financial Data & Stock Exchanges', 'primary_exchange': 'NYSE'},
        {'symbol': 'PG', 'name': 'Procter & Gamble Company', 'market_cap': 380000000000, 'sector': 'Consumer Defensive', 'industry': 'Household & Personal Products', 'primary_exchange': 'NYSE'},
        {'symbol': 'MA', 'name': 'Mastercard Incorporated', 'market_cap': 360000000000, 'sector': 'Financial Services', 'industry': 'Financial Data & Stock Exchanges', 'primary_exchange': 'NYSE'},
        
        # Mid cap stocks ($2B - $10B)
        {'symbol': 'PLTR', 'name': 'Palantir Technologies Inc.', 'market_cap': 40000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
        {'symbol': 'COIN', 'name': 'Coinbase Global Inc.', 'market_cap': 35000000000, 'sector': 'Financial Services', 'industry': 'Financial Data & Stock Exchanges', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'SNOW', 'name': 'Snowflake Inc.', 'market_cap': 30000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NYSE'},
        {'symbol': 'ZM', 'name': 'Zoom Video Communications Inc.', 'market_cap': 25000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'DDOG', 'name': 'Datadog Inc.', 'market_cap': 20000000000, 'sector': 'Technology', 'industry': 'Software', 'primary_exchange': 'NASDAQ'},
        
        # Small cap stocks ($300M - $2B)
        {'symbol': 'RIOT', 'name': 'Riot Blockchain Inc.', 'market_cap': 1800000000, 'sector': 'Financial Services', 'industry': 'Capital Markets', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'MARA', 'name': 'Marathon Digital Holdings Inc.', 'market_cap': 1600000000, 'sector': 'Financial Services', 'industry': 'Capital Markets', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'HUT', 'name': 'Hut 8 Mining Corp.', 'market_cap': 800000000, 'sector': 'Financial Services', 'industry': 'Capital Markets', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'IONQ', 'name': 'IonQ Inc.', 'market_cap': 600000000, 'sector': 'Technology', 'industry': 'Computer Hardware', 'primary_exchange': 'NYSE'},
        {'symbol': 'RGTI', 'name': 'Rigetti Computing Inc.', 'market_cap': 400000000, 'sector': 'Technology', 'industry': 'Computer Hardware', 'primary_exchange': 'NASDAQ'},
        
        # Micro cap stocks (< $300M)
        {'symbol': 'SNDL', 'name': 'Sundial Growers Inc.', 'market_cap': 250000000, 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'CGC', 'name': 'Canopy Growth Corporation', 'market_cap': 200000000, 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'ACB', 'name': 'Aurora Cannabis Inc.', 'market_cap': 150000000, 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'primary_exchange': 'NYSE'},
        {'symbol': 'TLRY', 'name': 'Tilray Brands Inc.', 'market_cap': 100000000, 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'primary_exchange': 'NASDAQ'},
        {'symbol': 'CRON', 'name': 'Cronos Group Inc.', 'market_cap': 50000000, 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'primary_exchange': 'NASDAQ'},
    ]


@pytest.fixture(scope="function")
def sample_etfs():
    """Sample ETF data covering different categories."""
    return [
        # Broad Market ETFs
        {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'market_cap': 450000000000, 'etf_type': 'Index', 'issuer': 'State Street', 'primary_exchange': 'NYSE', 'aum_millions': 450000},
        {'symbol': 'VTI', 'name': 'Vanguard Total Stock Market ETF', 'market_cap': 350000000000, 'etf_type': 'Index', 'issuer': 'Vanguard', 'primary_exchange': 'NYSE', 'aum_millions': 350000},
        {'symbol': 'IVV', 'name': 'iShares Core S&P 500 ETF', 'market_cap': 300000000000, 'etf_type': 'Index', 'issuer': 'iShares', 'primary_exchange': 'NYSE', 'aum_millions': 300000},
        
        # Technology ETFs
        {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust', 'market_cap': 250000000000, 'etf_type': 'Index', 'issuer': 'Invesco', 'primary_exchange': 'NASDAQ', 'aum_millions': 250000},
        {'symbol': 'XLK', 'name': 'Technology Select Sector SPDR Fund', 'market_cap': 60000000000, 'etf_type': 'Sector', 'issuer': 'State Street', 'primary_exchange': 'NYSE', 'aum_millions': 60000},
        {'symbol': 'VGT', 'name': 'Vanguard Information Technology ETF', 'market_cap': 55000000000, 'etf_type': 'Sector', 'issuer': 'Vanguard', 'primary_exchange': 'NYSE', 'aum_millions': 55000},
        
        # Growth ETFs
        {'symbol': 'VUG', 'name': 'Vanguard Growth ETF', 'market_cap': 80000000000, 'etf_type': 'Growth', 'issuer': 'Vanguard', 'primary_exchange': 'NYSE', 'aum_millions': 80000},
        {'symbol': 'IWF', 'name': 'iShares Russell 1000 Growth ETF', 'market_cap': 70000000000, 'etf_type': 'Growth', 'issuer': 'iShares', 'primary_exchange': 'NYSE', 'aum_millions': 70000},
        
        # Value ETFs
        {'symbol': 'VTV', 'name': 'Vanguard Value ETF', 'market_cap': 85000000000, 'etf_type': 'Value', 'issuer': 'Vanguard', 'primary_exchange': 'NYSE', 'aum_millions': 85000},
        {'symbol': 'IWD', 'name': 'iShares Russell 1000 Value ETF', 'market_cap': 75000000000, 'etf_type': 'Value', 'issuer': 'iShares', 'primary_exchange': 'NYSE', 'aum_millions': 75000},
        
        # International ETFs
        {'symbol': 'VEA', 'name': 'Vanguard FTSE Developed Markets ETF', 'market_cap': 90000000000, 'etf_type': 'International', 'issuer': 'Vanguard', 'primary_exchange': 'NYSE', 'aum_millions': 90000},
        {'symbol': 'VWO', 'name': 'Vanguard FTSE Emerging Markets ETF', 'market_cap': 70000000000, 'etf_type': 'International', 'issuer': 'Vanguard', 'primary_exchange': 'NYSE', 'aum_millions': 70000},
        
        # Bond ETFs
        {'symbol': 'BND', 'name': 'Vanguard Total Bond Market ETF', 'market_cap': 95000000000, 'etf_type': 'Bond', 'issuer': 'Vanguard', 'primary_exchange': 'NYSE', 'aum_millions': 95000},
        {'symbol': 'AGG', 'name': 'iShares Core U.S. Aggregate Bond ETF', 'market_cap': 88000000000, 'etf_type': 'Bond', 'issuer': 'iShares', 'primary_exchange': 'NYSE', 'aum_millions': 88000},
        
        # Commodity ETFs
        {'symbol': 'GLD', 'name': 'SPDR Gold Trust', 'market_cap': 65000000000, 'etf_type': 'Commodity', 'issuer': 'State Street', 'primary_exchange': 'NYSE', 'aum_millions': 65000},
        {'symbol': 'USO', 'name': 'United States Oil Fund', 'market_cap': 2000000000, 'etf_type': 'Commodity', 'issuer': 'United States Commodity Funds', 'primary_exchange': 'NYSE', 'aum_millions': 2000},
    ]


@pytest.fixture(scope="function")
def sample_sectors():
    """Sample sectors represented in the stock data."""
    return [
        'Technology',
        'Financial Services',
        'Healthcare', 
        'Consumer Discretionary',
        'Consumer Defensive',
        'Industrials',
        'Energy',
        'Materials',
        'Utilities',
        'Real Estate',
        'Communication Services'
    ]


@pytest.fixture(scope="function")
def comprehensive_test_dataset(sample_stocks, sample_etfs, sample_sectors):
    """Comprehensive test dataset combining all sample data."""
    return {
        'stocks': sample_stocks,
        'etfs': sample_etfs,
        'sectors': sample_sectors,
        'app_settings': [
            {'type': 'app_settings', 'name': 'ui_config', 'key': 'theme', 'value': 'dark'},
            {'type': 'app_settings', 'name': 'system', 'key': 'version', 'value': '2.1.0'},
            {'type': 'app_settings', 'name': 'features', 'key': 'notifications', 'value': 'enabled'},
        ]
    }


@pytest.fixture(scope="function")
def mock_database_connection():
    """Mock database connection with cursor context manager."""
    mock_conn = Mock()
    mock_cursor = Mock(spec=RealDictCursor)
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)
    mock_cursor.rowcount = 0
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture(scope="function")
def mock_redis_client():
    """Mock Redis client for testing notifications."""
    mock_redis = Mock()
    mock_redis.ping.return_value = True
    mock_redis.publish.return_value = 1  # Number of subscribers
    return mock_redis


@pytest.fixture(scope="function")
def performance_large_dataset():
    """Generate large dataset for performance testing."""
    def generate_dataset(num_stocks=5000, num_etfs=500, num_sectors=20):
        stocks = []
        for i in range(num_stocks):
            # Distribute market caps realistically
            if i < num_stocks * 0.01:  # Top 1% mega cap
                market_cap = 200_000_000_000 + (i * 10_000_000_000)
            elif i < num_stocks * 0.05:  # Next 4% large cap
                market_cap = 10_000_000_000 + (i * 200_000_000)
            elif i < num_stocks * 0.20:  # Next 15% mid cap
                market_cap = 2_000_000_000 + (i * 50_000_000)
            elif i < num_stocks * 0.60:  # Next 40% small cap
                market_cap = 300_000_000 + (i * 10_000_000)
            else:  # Remaining micro cap
                market_cap = 50_000_000 + (i * 5_000_000)
            
            stocks.append({
                'symbol': f'STK{i:05d}',
                'name': f'Stock Company {i} Inc.',
                'market_cap': market_cap,
                'sector': f'Sector{i % num_sectors}',
                'industry': f'Industry{i % (num_sectors * 3)}',
                'primary_exchange': 'NYSE' if i % 2 == 0 else 'NASDAQ'
            })
        
        etfs = []
        for i in range(num_etfs):
            etfs.append({
                'symbol': f'ETF{i:03d}',
                'name': f'ETF Fund {i}',
                'market_cap': 500_000_000 + (i * 10_000_000),
                'etf_type': ['Index', 'Sector', 'Growth', 'Value', 'International', 'Bond', 'Commodity'][i % 7],
                'issuer': f'Issuer{i % 10}',
                'primary_exchange': 'NYSE',
                'aum_millions': 500 + (i * 10)
            })
        
        return {
            'stocks': stocks,
            'etfs': etfs,
            'sectors': [f'Sector{i}' for i in range(num_sectors)]
        }
    
    return generate_dataset


@pytest.fixture(scope="function")
def database_stats_mock():
    """Mock database statistics for testing."""
    return {
        'total_stocks': 25000,
        'unique_sectors': 11,
        'unique_industries': 200,
        'unique_exchanges': 15,
        'total_market_cap': 75000000000000,  # $75T total market cap
        'average_market_cap': 3000000000     # $3B average market cap
    }


@pytest.fixture(scope="function") 
def theme_test_data():
    """Test data specifically for theme validation."""
    return {
        'ai_stocks': ['NVDA', 'GOOGL', 'MSFT', 'AMD', 'PLTR'],
        'crypto_stocks': ['COIN', 'RIOT', 'MARA', 'SQ', 'PYPL'],
        'biotech_stocks': ['MRNA', 'GILD', 'BIIB', 'AMGN', 'REGN'],
        'cloud_stocks': ['CRM', 'SNOW', 'AMZN', 'MSFT', 'GOOGL'],
        'available_symbols': ['NVDA', 'GOOGL', 'MSFT', 'AMD', 'COIN', 'RIOT', 'SNOW', 'CRM']
    }


def create_dynamic_cursor_mock(test_data: Dict[str, Any]):
    """
    Create a cursor mock that responds dynamically to different queries.
    
    Args:
        test_data: Dictionary containing stocks, etfs, sectors data
        
    Returns:
        Mock cursor that responds appropriately to different SQL queries
    """
    mock_cursor = Mock(spec=RealDictCursor)
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)
    
    def dynamic_fetchall(*args, **kwargs):
        if len(args) > 0 and isinstance(args[0], str):
            query = args[0].lower()
            
            # Sector queries
            if 'distinct sector' in query:
                return [{'sector': sector} for sector in test_data.get('sectors', [])]
            
            # ETF queries
            if 'type = \'etf\'' in query:
                return [{'symbol': etf['symbol']} for etf in test_data.get('etfs', [])]
            
            # Theme queries (symbol = ANY(%s))
            if 'symbol = any' in query:
                # Return first 5 symbols as available for any theme
                return [{'symbol': stock['symbol']} for stock in test_data.get('stocks', [])[:5]]
            
            # Market cap queries
            if 'market_cap >=' in query:
                # Parse threshold and filter stocks
                if '200000000000' in query:  # Mega cap
                    return [s for s in test_data.get('stocks', []) if s.get('market_cap', 0) >= 200000000000]
                elif '10000000000' in query:  # Large cap
                    return [s for s in test_data.get('stocks', []) if 10000000000 <= s.get('market_cap', 0) < 200000000000]
            
            # Sector-specific queries
            if 'sector =' in query:
                sector_name = None
                for sector in test_data.get('sectors', []):
                    if sector.lower() in query.lower():
                        sector_name = sector
                        break
                if sector_name:
                    return [s for s in test_data.get('stocks', []) if s.get('sector') == sector_name][:10]
            
            # Industry queries
            if 'industry = any' in query:
                # Return stocks matching any of the provided industries
                return [s for s in test_data.get('stocks', []) if s.get('industry') in ['Banks', 'Software', 'Insurance', 'Retail']]
            
            # LIMIT queries (market leaders)
            if 'limit' in query:
                limit_match = None
                for word in query.split():
                    if word.isdigit():
                        limit_match = int(word)
                        break
                if limit_match:
                    return test_data.get('stocks', [])[:limit_match]
        
        # Default: return all stocks
        return test_data.get('stocks', [])
    
    def dynamic_fetchone(*args, **kwargs):
        # Statistics query response
        return {
            'total_stocks': len(test_data.get('stocks', [])),
            'unique_sectors': len(test_data.get('sectors', [])),
            'unique_industries': len(set(s.get('industry', 'Unknown') for s in test_data.get('stocks', []))),
            'unique_exchanges': len(set(s.get('primary_exchange', 'Unknown') for s in test_data.get('stocks', []))),
            'total_market_cap': sum(s.get('market_cap', 0) for s in test_data.get('stocks', [])),
            'average_market_cap': sum(s.get('market_cap', 0) for s in test_data.get('stocks', [])) / max(len(test_data.get('stocks', [])), 1)
        }
    
    mock_cursor.fetchall.side_effect = dynamic_fetchall
    mock_cursor.fetchone.side_effect = dynamic_fetchone
    mock_cursor.rowcount = len(test_data.get('stocks', [])) // 4  # Simulate some deletions
    
    return mock_cursor


@pytest.fixture(scope="function")
def error_test_scenarios():
    """Common error scenarios for testing."""
    return {
        'connection_errors': [
            psycopg2.OperationalError("Connection refused"),
            psycopg2.OperationalError("FATAL: password authentication failed"),
            psycopg2.InterfaceError("Connection lost"),
            psycopg2.OperationalError("could not connect to server")
        ],
        'transaction_errors': [
            psycopg2.IntegrityError("duplicate key violates unique constraint"),
            psycopg2.OperationalError("deadlock detected"),
            psycopg2.OperationalError("could not obtain lock on relation"),
            psycopg2.InternalError("current transaction is aborted")
        ],
        'redis_errors': [
            redis.ConnectionError("Redis connection failed"),
            redis.RedisError("Redis publish failed"),
            redis.TimeoutError("Redis operation timed out")
        ]
    }


@pytest.fixture(scope="session")
def test_config():
    """Test configuration constants."""
    return {
        'performance_limits': {
            'full_rebuild_seconds': 60,
            'individual_method_seconds': 5,
            'memory_limit_mb': 100,
            'redis_overhead_seconds': 2
        },
        'data_limits': {
            'max_stocks': 10000,
            'max_etfs': 1000,
            'max_sectors': 30,
            'max_themes': 15
        },
        'database_config': {
            'test_uri': 'postgresql://testuser:testpass@localhost:5432/testdb',
            'connection_timeout': 30,
            'query_timeout': 60
        }
    }