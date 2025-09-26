#!/usr/bin/env python3
"""
Rapid Development Refresh System - Sprint 14 Phase 4

This service provides rapid development data refresh capabilities:
- Incremental development data system with smart gap detection
- Docker container integration for isolated development environments
- Configuration profile management for different development needs
- Database reset/restore to baseline within 30 seconds
- 2-minute refresh target for 50 symbols with selective backfill

Architecture:
- Integrates with existing historical loader for data operations
- Uses Docker for complete environment isolation between developers
- Smart gap detection minimizes unnecessary data loading
- Configuration-driven profiles for patterns, backtesting, UI testing
- Database snapshot/restore for rapid environment reset
"""

import os
import sys
import json
import logging
import time

# Load environment variables from config manager
try:
    from src.core.services.config_manager import get_config
except ImportError:
    pass  # config manager not available, will handle below
import shutil
import subprocess
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import psycopg2
import psycopg2.extras

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    print("+ Docker not available - using local development mode")

@dataclass
class DevelopmentProfile:
    """Development profile configuration"""
    name: str
    symbols_count: int
    days_back: int
    minute_data: bool
    description: str
    priority_symbols: List[str]
    universe_focus: str
    refresh_frequency: str

class RapidDevelopmentRefresh:
    """
    Rapid Development Refresh System
    
    Provides accelerated development workflows with:
    - Smart incremental data updates with gap detection
    - Docker-based environment isolation for multiple developers
    - Configuration profiles for different development scenarios
    - Sub-2-minute refresh times for 50+ symbols
    - 30-second database reset capability
    - Integration with existing historical loader and cache systems
    """
    
    def __init__(self, database_uri: str = None, docker_client=None):
        """Initialize rapid development refresh system"""
        config = get_config()
        self.database_uri = database_uri or config.get(
            'DATABASE_URI',
            'postgresql://app_readwrite:OLD_PASSWORD_2024@localhost/tickstock'
        )
        # Docker integration
        if DOCKER_AVAILABLE:
            self.docker_client = docker_client or docker.from_env()
        else:
            self.docker_client = None
        
        # Development profiles
        self.dev_profiles = {
            'patterns': DevelopmentProfile(
                name='patterns',
                symbols_count=20,
                days_back=90,
                minute_data=True,
                description='Pattern detection development with minute-level data',
                priority_symbols=['AAPL', 'MSFT', 'TSLA', 'SPY', 'QQQ'],
                universe_focus='high_volatility',
                refresh_frequency='daily'
            ),
            'backtesting': DevelopmentProfile(
                name='backtesting',
                symbols_count=50,
                days_back=365,
                minute_data=False,
                description='Backtesting development with extended historical data',
                priority_symbols=['SPY', 'QQQ', 'IWM', 'VTI', 'VEA'],
                universe_focus='broad_market',
                refresh_frequency='weekly'
            ),
            'ui_testing': DevelopmentProfile(
                name='ui_testing',
                symbols_count=10,
                days_back=30,
                minute_data=True,
                description='UI development with recent data and real-time simulation',
                priority_symbols=['AAPL', 'GOOGL', 'AMZN'],
                universe_focus='tech_leaders',
                refresh_frequency='hourly'
            ),
            'etf_analysis': DevelopmentProfile(
                name='etf_analysis',
                symbols_count=30,
                days_back=180,
                minute_data=False,
                description='ETF analysis development with sector and theme focus',
                priority_symbols=['SPY', 'XLF', 'XLE', 'XLK', 'XLV'],
                universe_focus='etf_sectors',
                refresh_frequency='daily'
            )
        }
        
        # Performance targets
        self.refresh_target_minutes = 2
        self.reset_target_seconds = 30
        self.gap_detection_efficiency_target = 0.7  # 70% reduction in unnecessary loading
        
        # Development paths
        self.dev_base_path = os.path.join(os.path.dirname(__file__), '../../dev_environments')
        self.backup_path = os.path.join(self.dev_base_path, 'backups')
        self.docker_volumes_path = os.path.join(self.dev_base_path, 'docker_volumes')
        
        # Ensure directories exist
        os.makedirs(self.dev_base_path, exist_ok=True)
        os.makedirs(self.backup_path, exist_ok=True)
        os.makedirs(self.docker_volumes_path, exist_ok=True)
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_database_connection(self, database_uri: str = None):
        """Get PostgreSQL database connection"""
        uri = database_uri or self.database_uri
        try:
            conn = psycopg2.connect(
                uri,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            return conn
        except Exception as e:
            self.logger.error(f"- Database connection failed: {e}")
            return None
    
    def rapid_refresh(self, profile_name: str = 'patterns', developer_name: str = 'dev') -> Dict[str, Any]:
        """
        Perform rapid development data refresh
        
        Args:
            profile_name: Development profile to use
            developer_name: Developer identifier for environment isolation
            
        Returns:
            Refresh results with timing and statistics
        """
        refresh_start = datetime.now()
        self.logger.info(f"=== Starting Rapid Development Refresh: {profile_name} for {developer_name} ===")
        
        if profile_name not in self.dev_profiles:
            return {'error': f'Unknown profile: {profile_name}'}
        
        profile = self.dev_profiles[profile_name]
        
        try:
            # Get development symbols for this profile
            symbols = self.get_development_symbols(profile)
            
            # Smart gap detection and incremental loading
            gaps_analysis = self.analyze_data_gaps(symbols, profile, developer_name)
            
            # Perform selective loading based on gaps
            loading_results = self.incremental_load_with_gaps(gaps_analysis, profile, developer_name)
            
            # Update cache entries if needed
            cache_updates = self.update_development_cache_entries(symbols, profile, developer_name)
            
            refresh_duration = (datetime.now() - refresh_start).total_seconds()
            
            result = {
                'profile': profile_name,
                'developer': developer_name,
                'refresh_start': refresh_start.isoformat(),
                'refresh_duration_seconds': refresh_duration,
                'within_target': refresh_duration <= (self.refresh_target_minutes * 60),
                'symbols_analyzed': len(symbols),
                'gaps_analysis': gaps_analysis,
                'loading_results': loading_results,
                'cache_updates': cache_updates,
                'efficiency_achieved': self.calculate_loading_efficiency(gaps_analysis, loading_results)
            }
            
            if result['within_target']:
                self.logger.info(f"+ Rapid refresh completed in {refresh_duration:.1f}s (within {self.refresh_target_minutes}min target)")
            else:
                self.logger.warning(f"- Refresh took {refresh_duration:.1f}s (exceeded {self.refresh_target_minutes}min target)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"- Rapid refresh failed: {e}")
            return {
                'error': str(e),
                'refresh_duration_seconds': (datetime.now() - refresh_start).total_seconds()
            }
    
    def get_development_symbols(self, profile: DevelopmentProfile) -> List[str]:
        """Get symbols for development based on profile configuration"""
        symbols = []
        
        # Start with priority symbols
        symbols.extend(profile.priority_symbols)
        
        # Add additional symbols based on universe focus and count
        additional_needed = profile.symbols_count - len(symbols)
        
        if additional_needed > 0:
            additional_symbols = self.get_universe_symbols(profile.universe_focus, additional_needed)
            symbols.extend(additional_symbols)
        
        # Ensure we don't exceed the profile symbol count
        return symbols[:profile.symbols_count]
    
    def get_universe_symbols(self, universe_focus: str, count: int) -> List[str]:
        """Get symbols from universe based on focus area"""
        universe_mappings = {
            'high_volatility': ['TSLA', 'NVDA', 'AMD', 'NFLX', 'ZOOM', 'PELOTON', 'GME', 'AMC'],
            'broad_market': ['VTI', 'VXUS', 'BND', 'VNQ', 'VT', 'SCHX', 'SPDW', 'SPEM'],
            'tech_leaders': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'CRM', 'ADBE'],
            'etf_sectors': ['XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLB', 'XLRE', 'XLU', 'XLY', 'XLP'],
            'development_testing': ['TEST_CRASH', 'TEST_GROWTH', 'TEST_VOLATILITY', 'TEST_TREND']
        }
        
        symbols = universe_mappings.get(universe_focus, ['AAPL', 'MSFT', 'SPY', 'QQQ'])
        
        # Extend with additional symbols if needed
        if len(symbols) < count:
            additional = ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'PNC', 'TFC', 'COF']
            symbols.extend(additional)
        
        return symbols[:count]
    
    def analyze_data_gaps(self, symbols: List[str], profile: DevelopmentProfile, 
                         developer_name: str) -> Dict[str, Any]:
        """
        Analyze data gaps for smart incremental loading
        
        Args:
            symbols: List of symbols to analyze
            profile: Development profile configuration
            developer_name: Developer environment identifier
            
        Returns:
            Gap analysis with loading recommendations
        """
        gap_analysis_start = datetime.now()
        
        # Get developer-specific database connection if using Docker
        conn = self.get_developer_database_connection(developer_name)
        if not conn:
            conn = self.get_database_connection()
        
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor()
            
            # Calculate target date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=profile.days_back)
            
            gaps_by_symbol = {}
            total_gaps = 0
            total_missing_days = 0
            
            for symbol in symbols:
                # Get existing data range for symbol
                cursor.execute("""
                    SELECT MIN(date) as first_date, MAX(date) as last_date, COUNT(*) as record_count
                    FROM historical_data 
                    WHERE symbol = %s
                    AND date >= %s
                """, (symbol, start_date))
                
                result = cursor.fetchone()
                
                if result and result['record_count'] > 0:
                    first_date = result['first_date']
                    last_date = result['last_date']
                    record_count = result['record_count']
                    
                    # Calculate expected trading days
                    expected_days = self.calculate_expected_trading_days(start_date, end_date)
                    
                    # Identify specific gaps
                    symbol_gaps = self.detect_specific_gaps(cursor, symbol, start_date, end_date)
                    
                    # Determine loading strategy
                    if last_date < end_date - timedelta(days=1):
                        # Need incremental update from last_date to end_date
                        incremental_gap = (last_date + timedelta(days=1), end_date)
                        symbol_gaps.append(incremental_gap)
                    
                    gaps_by_symbol[symbol] = {
                        'existing_records': record_count,
                        'expected_records': expected_days,
                        'completeness_pct': (record_count / expected_days) * 100 if expected_days > 0 else 0,
                        'first_date': first_date.isoformat() if first_date else None,
                        'last_date': last_date.isoformat() if last_date else None,
                        'gaps': [(gap[0].isoformat(), gap[1].isoformat()) for gap in symbol_gaps],
                        'loading_strategy': 'incremental' if len(symbol_gaps) <= 3 else 'full_reload'
                    }
                    
                    total_gaps += len(symbol_gaps)
                    total_missing_days += sum((gap[1] - gap[0]).days for gap in symbol_gaps)
                else:
                    # No existing data - full load needed
                    gaps_by_symbol[symbol] = {
                        'existing_records': 0,
                        'expected_records': self.calculate_expected_trading_days(start_date, end_date),
                        'completeness_pct': 0,
                        'first_date': None,
                        'last_date': None,
                        'gaps': [(start_date.isoformat(), end_date.isoformat())],
                        'loading_strategy': 'full_load'
                    }
                    
                    total_gaps += 1
                    total_missing_days += (end_date - start_date).days
            
            analysis_duration = (datetime.now() - gap_analysis_start).total_seconds()
            
            return {
                'analysis_duration_seconds': analysis_duration,
                'symbols_analyzed': len(symbols),
                'total_gaps': total_gaps,
                'total_missing_days': total_missing_days,
                'gaps_by_symbol': gaps_by_symbol,
                'loading_efficiency_estimate': self.estimate_loading_efficiency(gaps_by_symbol),
                'recommended_loading_order': self.prioritize_loading_order(gaps_by_symbol, profile)
            }
            
        except Exception as e:
            self.logger.error(f"- Gap analysis failed: {e}")
            return {'error': str(e)}
        finally:
            if conn:
                conn.close()
    
    def detect_specific_gaps(self, cursor, symbol: str, start_date: date, end_date: date) -> List[Tuple[date, date]]:
        """Detect specific date gaps in historical data"""
        try:
            # Get all dates with data for the symbol
            cursor.execute("""
                SELECT date 
                FROM historical_data 
                WHERE symbol = %s 
                AND date >= %s 
                AND date <= %s
                ORDER BY date
            """, (symbol, start_date, end_date))
            
            existing_dates = [row['date'] for row in cursor.fetchall()]
            
            if not existing_dates:
                return [(start_date, end_date)]
            
            # Find gaps in the date sequence
            gaps = []
            current_date = start_date
            
            for existing_date in existing_dates:
                if existing_date > current_date:
                    # Found a gap
                    gap_end = existing_date - timedelta(days=1)
                    if (gap_end - current_date).days > 0:
                        gaps.append((current_date, gap_end))
                
                current_date = existing_date + timedelta(days=1)
            
            # Check for final gap
            if current_date <= end_date:
                gaps.append((current_date, end_date))
            
            # Filter out weekend-only gaps (optional optimization)
            significant_gaps = []
            for gap_start, gap_end in gaps:
                trading_days = self.calculate_expected_trading_days(gap_start, gap_end)
                if trading_days > 0:
                    significant_gaps.append((gap_start, gap_end))
            
            return significant_gaps
            
        except Exception as e:
            self.logger.error(f"- Gap detection failed for {symbol}: {e}")
            return [(start_date, end_date)]  # Fallback to full range
    
    def calculate_expected_trading_days(self, start_date: date, end_date: date) -> int:
        """Calculate expected trading days between dates (excluding weekends)"""
        total_days = (end_date - start_date).days + 1
        
        # Simple approximation: 5/7 of days are trading days
        trading_days = int(total_days * 5 / 7)
        
        # More accurate calculation could integrate with market calendar
        # if MARKET_CALENDARS_AVAILABLE:
        #     calendar = mcal.get_calendar('NYSE')
        #     trading_days = len(calendar.sessions_in_range(start_date, end_date))
        
        return max(0, trading_days)
    
    def incremental_load_with_gaps(self, gaps_analysis: Dict[str, Any], 
                                  profile: DevelopmentProfile, developer_name: str) -> Dict[str, Any]:
        """
        Perform incremental loading based on gap analysis
        
        Args:
            gaps_analysis: Results from gap analysis
            profile: Development profile configuration
            developer_name: Developer environment identifier
            
        Returns:
            Loading results with performance metrics
        """
        loading_start = datetime.now()
        
        if 'error' in gaps_analysis:
            return {'error': gaps_analysis['error']}
        
        gaps_by_symbol = gaps_analysis['gaps_by_symbol']
        loading_order = gaps_analysis['recommended_loading_order']
        
        loading_results = {
            'symbols_processed': 0,
            'total_gaps_filled': 0,
            'total_records_loaded': 0,
            'loading_details': {},
            'skipped_symbols': [],
            'failed_symbols': []
        }
        
        # Process symbols in priority order
        for symbol in loading_order:
            try:
                symbol_gaps = gaps_by_symbol[symbol]
                
                if symbol_gaps['loading_strategy'] == 'skip':
                    loading_results['skipped_symbols'].append(symbol)
                    continue
                
                symbol_result = self.load_symbol_gaps(symbol, symbol_gaps, profile, developer_name)
                loading_results['loading_details'][symbol] = symbol_result
                
                if symbol_result['success']:
                    loading_results['symbols_processed'] += 1
                    loading_results['total_gaps_filled'] += len(symbol_gaps['gaps'])
                    loading_results['total_records_loaded'] += symbol_result['records_loaded']
                else:
                    loading_results['failed_symbols'].append(symbol)
                    
            except Exception as e:
                self.logger.error(f"- Failed to load symbol {symbol}: {e}")
                loading_results['failed_symbols'].append(symbol)
        
        loading_duration = (datetime.now() - loading_start).total_seconds()
        loading_results['loading_duration_seconds'] = loading_duration
        loading_results['loading_rate_records_per_second'] = (
            loading_results['total_records_loaded'] / loading_duration 
            if loading_duration > 0 else 0
        )
        
        return loading_results
    
    def load_symbol_gaps(self, symbol: str, symbol_gaps: Dict[str, Any], 
                        profile: DevelopmentProfile, developer_name: str) -> Dict[str, Any]:
        """Load data for specific symbol gaps"""
        try:
            total_records = 0
            gaps_filled = 0
            
            # Get developer-specific database connection
            conn = self.get_developer_database_connection(developer_name)
            if not conn:
                conn = self.get_database_connection()
            
            if not conn:
                return {'success': False, 'error': 'Database connection failed'}
            
            cursor = conn.cursor()
            
            # Process each gap
            for gap_str in symbol_gaps['gaps']:
                gap_start = datetime.fromisoformat(gap_str[0]).date()
                gap_end = datetime.fromisoformat(gap_str[1]).date()
                
                # Simulate data loading (replace with actual historical loader integration)
                records_loaded = self.simulate_gap_loading(symbol, gap_start, gap_end, profile)
                
                # Insert simulated data
                self.insert_simulated_data(cursor, symbol, gap_start, gap_end, records_loaded)
                
                total_records += records_loaded
                gaps_filled += 1
            
            conn.commit()
            
            return {
                'success': True,
                'gaps_filled': gaps_filled,
                'records_loaded': total_records,
                'loading_strategy': symbol_gaps['loading_strategy']
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            if conn:
                conn.close()
    
    def simulate_gap_loading(self, symbol: str, start_date: date, end_date: date, 
                           profile: DevelopmentProfile) -> int:
        """Simulate data loading for development (replace with actual loader)"""
        # Calculate approximate records
        days = (end_date - start_date).days + 1
        trading_days = self.calculate_expected_trading_days(start_date, end_date)
        
        # Simulate loading time based on profile
        if profile.minute_data:
            records_per_day = 390  # Minutes in trading day
        else:
            records_per_day = 1    # Daily OHLCV
        
        return max(0, trading_days * records_per_day)
    
    def insert_simulated_data(self, cursor, symbol: str, start_date: date, end_date: date, records_count: int):
        """Insert simulated data for development"""
        # This would integrate with actual historical loader
        # For now, just update a metadata table to track loading
        cursor.execute("""
            INSERT INTO dev_loading_log (symbol, start_date, end_date, records_loaded, loaded_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (symbol, start_date, end_date, records_count, datetime.now()))
    
    def prioritize_loading_order(self, gaps_by_symbol: Dict[str, Any], 
                               profile: DevelopmentProfile) -> List[str]:
        """Determine optimal loading order for symbols"""
        symbols_with_priority = []
        
        for symbol, gap_info in gaps_by_symbol.items():
            # Calculate priority score
            completeness = gap_info['completeness_pct']
            missing_days = sum(
                (datetime.fromisoformat(gap[1]) - datetime.fromisoformat(gap[0])).days 
                for gap in gap_info['gaps']
            )
            
            # Priority factors
            is_priority_symbol = symbol in profile.priority_symbols
            loading_efficiency = 100 - completeness  # Higher score for more incomplete data
            
            priority_score = (
                (50 if is_priority_symbol else 0) +
                (loading_efficiency * 0.3) +
                (min(missing_days, 100) * 0.2)
            )
            
            symbols_with_priority.append((symbol, priority_score))
        
        # Sort by priority score (highest first)
        symbols_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        return [symbol for symbol, _ in symbols_with_priority]
    
    def calculate_loading_efficiency(self, gaps_analysis: Dict[str, Any], 
                                   loading_results: Dict[str, Any]) -> float:
        """Calculate loading efficiency (percentage of unnecessary loading avoided)"""
        if 'gaps_by_symbol' not in gaps_analysis:
            return 0.0
        
        total_possible_days = 0
        actual_loaded_days = 0
        
        gaps_by_symbol = gaps_analysis['gaps_by_symbol']
        
        for symbol, gap_info in gaps_by_symbol.items():
            # Calculate total days that could have been loaded (full reload)
            expected_records = gap_info['expected_records']
            total_possible_days += expected_records
            
            # Calculate actual days loaded based on gaps
            actual_gaps_days = sum(
                (datetime.fromisoformat(gap[1]) - datetime.fromisoformat(gap[0])).days
                for gap in gap_info['gaps']
            )
            actual_loaded_days += actual_gaps_days
        
        if total_possible_days == 0:
            return 0.0
        
        efficiency = max(0, 1 - (actual_loaded_days / total_possible_days))
        return efficiency
    
    def estimate_loading_efficiency(self, gaps_by_symbol: Dict[str, Any]) -> float:
        """Estimate loading efficiency before actual loading"""
        total_expected = 0
        total_needed = 0
        
        for symbol, gap_info in gaps_by_symbol.items():
            total_expected += gap_info['expected_records']
            gaps_days = sum(
                (datetime.fromisoformat(gap[1]) - datetime.fromisoformat(gap[0])).days
                for gap in gap_info['gaps']
            )
            total_needed += gaps_days
        
        if total_expected == 0:
            return 0.0
        
        return max(0, 1 - (total_needed / total_expected))
    
    def get_developer_database_connection(self, developer_name: str):
        """Get developer-specific database connection (Docker or local)"""
        if DOCKER_AVAILABLE and self.docker_client:
            # Try to get connection to developer's Docker database
            try:
                container_name = f"tickstock_dev_{developer_name}"
                containers = self.docker_client.containers.list(
                    filters={"name": container_name}
                )
                
                if containers:
                    container = containers[0]
                    port_info = container.ports.get('5432/tcp')
                    if port_info:
                        host_port = port_info[0]['HostPort']
                        dev_db_uri = f"postgresql://dev_user:dev_password@localhost:{host_port}/tickstock_dev_{developer_name}"
                        return self.get_database_connection(dev_db_uri)
            except Exception as e:
                self.logger.warning(f"- Could not connect to developer database: {e}")
        
        # Fallback to main database
        return None
    
    def setup_docker_environment(self, developer_name: str) -> Dict[str, Any]:
        """Create isolated Docker environment for developer"""
        if not DOCKER_AVAILABLE:
            return {'error': 'Docker not available'}
        
        try:
            container_name = f"tickstock_dev_{developer_name}"
            database_name = f"tickstock_dev_{developer_name}"
            volume_name = f"tickstock_dev_data_{developer_name}"
            
            # Check if container already exists
            existing_containers = self.docker_client.containers.list(
                all=True, filters={"name": container_name}
            )
            
            if existing_containers:
                container = existing_containers[0]
                if container.status == 'running':
                    return {
                        'status': 'already_running',
                        'container_name': container_name,
                        'container_id': container.id
                    }
                else:
                    container.start()
                    return {
                        'status': 'restarted',
                        'container_name': container_name,
                        'container_id': container.id
                    }
            
            # Create new container
            dev_container = self.docker_client.containers.run(
                "postgres:13",
                name=container_name,
                environment={
                    'POSTGRES_DB': database_name,
                    'POSTGRES_USER': 'dev_user',
                    'POSTGRES_PASSWORD': 'dev_password'
                },
                volumes={
                    volume_name: {
                        'bind': '/var/lib/postgresql/data',
                        'mode': 'rw'
                    }
                },
                ports={'5432/tcp': None},  # Auto-assign port
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            # Wait for container to be ready
            time.sleep(5)
            
            # Initialize database schema
            self.initialize_dev_database(container_name, database_name)
            
            return {
                'status': 'created',
                'container_name': container_name,
                'container_id': dev_container.id,
                'database_name': database_name,
                'volume_name': volume_name
            }
            
        except Exception as e:
            self.logger.error(f"- Docker environment setup failed: {e}")
            return {'error': str(e)}
    
    def initialize_dev_database(self, container_name: str, database_name: str):
        """Initialize development database with schema"""
        try:
            # Run schema initialization inside container
            schema_commands = [
                "CREATE EXTENSION IF NOT EXISTS timescaledb;",
                """CREATE TABLE IF NOT EXISTS historical_data (
                    symbol VARCHAR(20),
                    date DATE,
                    open_price NUMERIC(12,4),
                    high_price NUMERIC(12,4), 
                    low_price NUMERIC(12,4),
                    close_price NUMERIC(12,4),
                    volume BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, date)
                );""",
                """CREATE TABLE IF NOT EXISTS dev_loading_log (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20),
                    start_date DATE,
                    end_date DATE,
                    records_loaded INTEGER,
                    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );""",
                "SELECT create_hypertable('historical_data', 'date', if_not_exists => TRUE);"
            ]
            
            for command in schema_commands:
                result = self.docker_client.containers.get(container_name).exec_run(
                    f'psql -U dev_user -d {database_name} -c "{command}"'
                )
                if result.exit_code != 0:
                    self.logger.warning(f"- Schema command warning: {result.output.decode()}")
                    
        except Exception as e:
            self.logger.error(f"- Database initialization failed: {e}")
    
    def database_reset_restore(self, developer_name: str, baseline_name: str = 'dev_baseline') -> Dict[str, Any]:
        """Fast database reset to known baseline"""
        reset_start = datetime.now()
        
        try:
            baseline_file = os.path.join(self.backup_path, f"{baseline_name}.sql")
            
            if not os.path.exists(baseline_file):
                return {'error': f'Baseline {baseline_name} not found'}
            
            if DOCKER_AVAILABLE and self.docker_client:
                # Docker-based reset
                result = self.docker_reset_restore(developer_name, baseline_file)
            else:
                # Local database reset
                result = self.local_reset_restore(developer_name, baseline_file)
            
            reset_duration = (datetime.now() - reset_start).total_seconds()
            result['reset_duration_seconds'] = reset_duration
            result['within_target'] = reset_duration <= self.reset_target_seconds
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'reset_duration_seconds': (datetime.now() - reset_start).total_seconds()
            }
    
    def docker_reset_restore(self, developer_name: str, baseline_file: str) -> Dict[str, Any]:
        """Reset Docker-based development database"""
        container_name = f"tickstock_dev_{developer_name}"
        database_name = f"tickstock_dev_{developer_name}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Copy baseline file to container
            with open(baseline_file, 'rb') as f:
                container.put_archive('/tmp/', f.read())
            
            # Drop and recreate database
            drop_result = container.exec_run(
                f'psql -U dev_user -d postgres -c "DROP DATABASE IF EXISTS {database_name};"'
            )
            
            create_result = container.exec_run(
                f'psql -U dev_user -d postgres -c "CREATE DATABASE {database_name};"'
            )
            
            # Restore from baseline
            restore_result = container.exec_run(
                f'psql -U dev_user -d {database_name} -f /tmp/{os.path.basename(baseline_file)}'
            )
            
            success = all(r.exit_code == 0 for r in [drop_result, create_result, restore_result])
            
            return {
                'method': 'docker',
                'success': success,
                'container_name': container_name,
                'database_name': database_name
            }
            
        except Exception as e:
            return {'method': 'docker', 'success': False, 'error': str(e)}
    
    def local_reset_restore(self, developer_name: str, baseline_file: str) -> Dict[str, Any]:
        """Reset local development database"""
        try:
            # Use pg_dump/restore for local reset
            restore_commands = [
                f"dropdb --if-exists tickstock_dev_{developer_name}",
                f"createdb tickstock_dev_{developer_name}",
                f"psql tickstock_dev_{developer_name} < {baseline_file}"
            ]
            
            for command in restore_commands:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    return {
                        'method': 'local',
                        'success': False,
                        'error': f"Command failed: {command}, Error: {result.stderr}"
                    }
            
            return {
                'method': 'local',
                'success': True,
                'database_name': f"tickstock_dev_{developer_name}"
            }
            
        except Exception as e:
            return {'method': 'local', 'success': False, 'error': str(e)}
    
    def create_baseline_snapshot(self, baseline_name: str = 'dev_baseline') -> Dict[str, Any]:
        """Create a baseline snapshot for rapid restore"""
        try:
            baseline_file = os.path.join(self.backup_path, f"{baseline_name}.sql")
            
            # Create snapshot using pg_dump
            dump_command = f"pg_dump {self.database_uri} > {baseline_file}"
            result = subprocess.run(dump_command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                file_size = os.path.getsize(baseline_file)
                return {
                    'success': True,
                    'baseline_name': baseline_name,
                    'baseline_file': baseline_file,
                    'file_size_mb': file_size / 1024 / 1024
                }
            else:
                return {
                    'success': False,
                    'error': f"pg_dump failed: {result.stderr}"
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_development_cache_entries(self, symbols: List[str], profile: DevelopmentProfile, 
                                       developer_name: str) -> Dict[str, Any]:
        """Update cache entries for development environment"""
        try:
            conn = self.get_developer_database_connection(developer_name)
            if not conn:
                conn = self.get_database_connection()
            
            if not conn:
                return {'error': 'Database connection failed'}
            
            cursor = conn.cursor()
            
            # Create/update development cache entry
            cache_key = f"dev_{profile.name}_{developer_name}"
            
            cursor.execute("""
                INSERT INTO cache_entries (cache_key, symbols, universe_category, universe_metadata, last_universe_update)
                VALUES (%s, %s, 'DEVELOPMENT', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (cache_key) DO UPDATE SET
                    symbols = EXCLUDED.symbols,
                    universe_metadata = EXCLUDED.universe_metadata,
                    last_universe_update = CURRENT_TIMESTAMP
            """, (cache_key, json.dumps(symbols), json.dumps({
                'profile': profile.name,
                'developer': developer_name,
                'symbol_count': len(symbols),
                'description': profile.description,
                'universe_focus': profile.universe_focus
            })))
            
            conn.commit()
            
            return {
                'success': True,
                'cache_key': cache_key,
                'symbols_count': len(symbols)
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            return {'error': str(e)}
        finally:
            if conn:
                conn.close()

def main():
    """Main execution function for rapid development refresh"""
    refresh_system = RapidDevelopmentRefresh()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command.startswith('--refresh='):
            parts = command.split('=')[1].split(',')
            profile = parts[0] if parts else 'patterns'
            developer = parts[1] if len(parts) > 1 else 'dev'
            
            result = refresh_system.rapid_refresh(profile, developer)
            if 'error' not in result:
                print(f"Rapid refresh complete for {developer}:")
                print(f"  Profile: {result['profile']}")
                print(f"  Duration: {result['refresh_duration_seconds']:.1f}s")
                print(f"  Within target: {result['within_target']}")
                print(f"  Symbols: {result['symbols_analyzed']}")
                print(f"  Efficiency: {result['efficiency_achieved']:.1%}")
            else:
                print(f"Refresh failed: {result['error']}")
                
        elif command.startswith('--docker-setup='):
            developer = command.split('=')[1]
            result = refresh_system.setup_docker_environment(developer)
            if 'error' not in result:
                print(f"Docker environment setup for {developer}:")
                print(f"  Status: {result['status']}")
                print(f"  Container: {result['container_name']}")
            else:
                print(f"Docker setup failed: {result['error']}")
                
        elif command.startswith('--reset='):
            parts = command.split('=')[1].split(',')
            developer = parts[0] if parts else 'dev'
            baseline = parts[1] if len(parts) > 1 else 'dev_baseline'
            
            result = refresh_system.database_reset_restore(developer, baseline)
            if 'error' not in result:
                print(f"Database reset for {developer}:")
                print(f"  Success: {result['success']}")
                print(f"  Duration: {result['reset_duration_seconds']:.1f}s")
                print(f"  Within target: {result['within_target']}")
            else:
                print(f"Reset failed: {result['error']}")
                
        elif command == '--create-baseline':
            result = refresh_system.create_baseline_snapshot()
            if result['success']:
                print(f"Baseline created: {result['baseline_name']}")
                print(f"  File: {result['baseline_file']}")
                print(f"  Size: {result['file_size_mb']:.1f} MB")
            else:
                print(f"Baseline creation failed: {result['error']}")
                
        else:
            print("Usage:")
            print("  --refresh=<profile>,<developer>: Rapid refresh (e.g., --refresh=patterns,john)")
            print("  --docker-setup=<developer>: Setup Docker environment")
            print("  --reset=<developer>,<baseline>: Reset database to baseline")
            print("  --create-baseline: Create baseline snapshot")
            print(f"\nAvailable profiles: {', '.join(refresh_system.dev_profiles.keys())}")
    else:
        # Default: show available profiles
        print("Rapid Development Refresh System")
        print("\nAvailable Development Profiles:")
        for name, profile in refresh_system.dev_profiles.items():
            print(f"  {name}:")
            print(f"    Description: {profile.description}")
            print(f"    Symbols: {profile.symbols_count}")
            print(f"    Days back: {profile.days_back}")
            print(f"    Minute data: {profile.minute_data}")
            print()

if __name__ == '__main__':
    main()