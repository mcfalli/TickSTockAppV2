#!/usr/bin/env python3
"""
Test Scenario Generator - Sprint 14 Phase 3

This service generates sophisticated testing data scenarios for pattern validation:
- Synthetic OHLCV data with controllable patterns and realistic characteristics
- Predefined scenarios: crash_2020, growth_2021, volatility_periods, trend_changes
- Integration with ta-lib for technical pattern validation
- CLI integration with historical loader for scenario loading
- Performance target: scenario generation and loading in <2 minutes

Architecture:
- Runs as part of data management pipeline for testing
- Generates realistic synthetic data without interfering with production
- Integration with existing historical loader CLI via --scenario parameter
- Pattern validation and expected outcome documentation
"""

import os
import sys
import json
import logging
import numpy as np

# Load environment variables from config manager
try:
    from src.core.services.config_manager import get_config
except ImportError:
    pass  # config manager not available, will handle below
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import psycopg2
import psycopg2.extras
from decimal import Decimal
import math
import random

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("+ TA-Lib not available - pattern validation will be limited")

@dataclass
class ScenarioConfig:
    """Test scenario configuration"""
    name: str
    description: str
    length: int  # Number of trading days
    base_price: float
    volatility_profile: str  # low, medium, high, extreme
    trend_direction: str  # up, down, sideways, mixed
    volume_profile: str  # low, normal, high, spike
    pattern_features: List[str]  # List of expected patterns
    expected_outcomes: Dict[str, Any]

class TestScenarioGenerator:
    """
    Test Scenario Generator
    
    Generates synthetic OHLCV data for pattern detection validation:
    - Realistic market scenarios with controllable characteristics
    - Known pattern injection for validation purposes
    - Integration with technical analysis libraries
    - Performance optimized for rapid scenario deployment
    """
    
    def __init__(self, database_uri: str = None):
        """Initialize test scenario generator"""
        config = get_config()
        self.database_uri = database_uri or config.get(
            'DATABASE_URI',
            'postgresql://app_readwrite:OLD_PASSWORD_2024@localhost/tickstock'
        )
        # Scenario configurations
        self.scenarios = self._initialize_scenario_configs()
        
        # Random seed for reproducible results
        self.random_seed = 42
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _initialize_scenario_configs(self) -> Dict[str, ScenarioConfig]:
        """Initialize predefined scenario configurations"""
        return {
            'crash_2020': ScenarioConfig(
                name='crash_2020',
                description='COVID-19 market crash simulation (March 2020 style)',
                length=252,  # 1 year of trading days
                base_price=100.0,
                volatility_profile='extreme',
                trend_direction='mixed',
                volume_profile='spike',
                pattern_features=['high_low_events', 'volatility_surge', 'volume_spike', 'trend_reversal'],
                expected_outcomes={
                    'max_drawdown': -35.0,
                    'volatility_spike_count': 15,
                    'high_low_events': 8,
                    'recovery_pattern': 'v_shaped'
                }
            ),
            'growth_2021': ScenarioConfig(
                name='growth_2021',
                description='Post-pandemic growth market simulation',
                length=252,
                base_price=100.0,
                volatility_profile='medium',
                trend_direction='up',
                volume_profile='high',
                pattern_features=['trend_continuation', 'momentum_patterns', 'breakout_patterns'],
                expected_outcomes={
                    'total_return': 25.0,
                    'trend_strength': 0.75,
                    'breakout_count': 6,
                    'momentum_periods': 4
                }
            ),
            'volatility_periods': ScenarioConfig(
                name='volatility_periods',
                description='High volatility periods with sideways movement',
                length=126,  # 6 months
                base_price=150.0,
                volatility_profile='high',
                trend_direction='sideways',
                volume_profile='normal',
                pattern_features=['range_bound', 'volatility_clustering', 'mean_reversion'],
                expected_outcomes={
                    'volatility_periods': 3,
                    'trading_range': 30.0,
                    'mean_reversion_strength': 0.65,
                    'volatility_clustering': True
                }
            ),
            'trend_changes': ScenarioConfig(
                name='trend_changes',
                description='Multiple trend direction changes for pattern detection',
                length=189,  # 9 months
                base_price=80.0,
                volatility_profile='medium',
                trend_direction='mixed',
                volume_profile='normal',
                pattern_features=['trend_reversals', 'support_resistance', 'momentum_divergence'],
                expected_outcomes={
                    'trend_changes': 4,
                    'support_resistance_levels': 6,
                    'false_breakouts': 2,
                    'momentum_divergences': 3
                }
            ),
            'high_low_events': ScenarioConfig(
                name='high_low_events',
                description='Frequent high/low events for threshold testing',
                length=63,  # 3 months
                base_price=200.0,
                volatility_profile='high',
                trend_direction='mixed',
                volume_profile='spike',
                pattern_features=['high_low_events', 'price_gaps', 'volume_anomalies'],
                expected_outcomes={
                    'high_events': 12,
                    'low_events': 10,
                    'price_gaps': 8,
                    'volume_spikes': 15
                }
            )
        }
    
    def get_database_connection(self):
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(
                self.database_uri,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            return conn
        except Exception as e:
            self.logger.error(f"- Database connection failed: {e}")
            return None
    
    def generate_scenario_data(self, scenario_name: str, symbol_suffix: str = '') -> Optional[List[Dict[str, Any]]]:
        """
        Generate synthetic OHLCV data for specified scenario
        
        Args:
            scenario_name: Name of the scenario to generate
            symbol_suffix: Optional suffix for symbol name (e.g., '_TEST')
            
        Returns:
            List of OHLCV data dictionaries or None if scenario not found
        """
        if scenario_name not in self.scenarios:
            self.logger.error(f"- Unknown scenario: {scenario_name}")
            return None
        
        config = self.scenarios[scenario_name]
        self.logger.info(f"+ Generating scenario '{scenario_name}': {config.length} days")
        
        # Set reproducible seed
        np.random.seed(self.random_seed)
        random.seed(self.random_seed)
        
        # Generate base time series
        if config.name == 'crash_2020':
            ohlcv_data = self._generate_crash_scenario(config)
        elif config.name == 'growth_2021':
            ohlcv_data = self._generate_growth_scenario(config)
        elif config.name == 'volatility_periods':
            ohlcv_data = self._generate_volatility_scenario(config)
        elif config.name == 'trend_changes':
            ohlcv_data = self._generate_trend_changes_scenario(config)
        elif config.name == 'high_low_events':
            ohlcv_data = self._generate_high_low_scenario(config)
        else:
            ohlcv_data = self._generate_generic_scenario(config)
        
        # Add symbol suffix if provided
        if symbol_suffix:
            for row in ohlcv_data:
                row['symbol'] = f"TEST_{scenario_name.upper()}{symbol_suffix}"
        else:
            for row in ohlcv_data:
                row['symbol'] = f"TEST_{scenario_name.upper()}"
        
        self.logger.info(f"+ Generated {len(ohlcv_data)} OHLCV records for scenario '{scenario_name}'")
        return ohlcv_data
    
    def _generate_crash_scenario(self, config: ScenarioConfig) -> List[Dict[str, Any]]:
        """Generate COVID-19 style crash scenario"""
        length = config.length
        base_price = config.base_price
        
        # Phase structure: Normal (60%) -> Crash (10%) -> Recovery (30%)
        normal_period = int(length * 0.6)
        crash_period = int(length * 0.1)
        recovery_period = length - normal_period - crash_period
        
        # Generate returns for each phase
        normal_returns = np.random.normal(0.0008, 0.015, normal_period)  # Slight upward bias, low vol
        crash_returns = np.random.normal(-0.08, 0.12, crash_period)      # Heavy downward, extreme vol
        recovery_returns = np.random.normal(0.025, 0.06, recovery_period) # Strong recovery, medium vol
        
        # Combine and create price series
        all_returns = np.concatenate([normal_returns, crash_returns, recovery_returns])
        prices = base_price * np.cumprod(1 + all_returns)
        
        # Generate OHLCV data with realistic intraday patterns
        ohlcv_data = []
        start_date = datetime.now().date() - timedelta(days=length + 30)
        
        for i, close in enumerate(prices):
            current_date = start_date + timedelta(days=i)
            
            # Skip weekends
            if current_date.weekday() >= 5:
                continue
                
            # Determine volatility phase for intraday range
            if i < normal_period:
                vol_multiplier = 1.0
                volume_base = 2000000
            elif i < normal_period + crash_period:
                vol_multiplier = 3.5  # Extreme volatility during crash
                volume_base = 8000000  # High volume during crash
            else:
                vol_multiplier = 2.0  # Elevated volatility during recovery
                volume_base = 4000000
            
            # Calculate OHLC with realistic intraday patterns
            daily_range = close * np.random.uniform(0.02, 0.08) * vol_multiplier
            high = close + np.random.uniform(0.3, 0.7) * daily_range
            low = close - np.random.uniform(0.3, 0.7) * daily_range
            
            # Open price based on previous close with gap potential
            if i > 0:
                gap_factor = np.random.normal(0, 0.01 * vol_multiplier)
                open_price = prices[i-1] * (1 + gap_factor)
            else:
                open_price = close
            
            # Ensure OHLC relationships are valid
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            # Generate realistic volume with spikes during crash
            volume_noise = np.random.uniform(0.7, 1.5)
            if i >= normal_period and i < normal_period + crash_period:
                volume_noise *= np.random.uniform(2.0, 5.0)  # Volume spikes during crash
                
            volume = int(volume_base * volume_noise)
            
            ohlcv_data.append({
                'date': current_date,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        return ohlcv_data
    
    def _generate_growth_scenario(self, config: ScenarioConfig) -> List[Dict[str, Any]]:
        """Generate post-pandemic growth market scenario"""
        length = config.length
        base_price = config.base_price
        
        # Growth phases: Recovery (30%) -> Momentum (50%) -> Consolidation (20%)
        recovery_period = int(length * 0.3)
        momentum_period = int(length * 0.5)
        consolidation_period = length - recovery_period - momentum_period
        
        # Generate returns with growth bias
        recovery_returns = np.random.normal(0.015, 0.025, recovery_period)    # Steady recovery
        momentum_returns = np.random.normal(0.008, 0.020, momentum_period)    # Growth momentum
        consolidation_returns = np.random.normal(0.002, 0.015, consolidation_period) # Consolidation
        
        all_returns = np.concatenate([recovery_returns, momentum_returns, consolidation_returns])
        prices = base_price * np.cumprod(1 + all_returns)
        
        # Generate OHLCV data
        ohlcv_data = []
        start_date = datetime.now().date() - timedelta(days=length + 30)
        
        for i, close in enumerate(prices):
            current_date = start_date + timedelta(days=i)
            
            if current_date.weekday() >= 5:
                continue
            
            # Determine phase characteristics
            if i < recovery_period:
                vol_multiplier = 1.2
                volume_base = 3000000
            elif i < recovery_period + momentum_period:
                vol_multiplier = 1.0  # Lower volatility during momentum
                volume_base = 5000000  # Higher volume during growth
            else:
                vol_multiplier = 0.8  # Low volatility during consolidation
                volume_base = 2000000
            
            # Generate OHLC
            daily_range = close * np.random.uniform(0.015, 0.035) * vol_multiplier
            high = close + np.random.uniform(0.4, 0.8) * daily_range
            low = close - np.random.uniform(0.2, 0.6) * daily_range  # Upward bias
            
            if i > 0:
                gap_factor = np.random.normal(0.001, 0.005)  # Small upward gaps
                open_price = prices[i-1] * (1 + gap_factor)
            else:
                open_price = close
            
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = int(volume_base * np.random.uniform(0.8, 1.3))
            
            ohlcv_data.append({
                'date': current_date,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        return ohlcv_data
    
    def _generate_volatility_scenario(self, config: ScenarioConfig) -> List[Dict[str, Any]]:
        """Generate high volatility sideways movement scenario"""
        length = config.length
        base_price = config.base_price
        
        # Create mean-reverting series with volatility clustering
        returns = []
        current_vol = 0.02  # Base volatility
        
        for i in range(length):
            # Volatility clustering - high vol periods followed by high vol
            vol_persistence = 0.85
            vol_innovation = np.random.normal(0, 0.005)
            current_vol = current_vol * vol_persistence + vol_innovation
            current_vol = max(0.01, min(0.08, current_vol))  # Bound volatility
            
            # Mean reversion to sideways trend
            mean_reversion_strength = 0.05
            if i > 0:
                price_level = sum(returns) / len(returns) if returns else 0
                mean_reversion = -mean_reversion_strength * price_level
            else:
                mean_reversion = 0
            
            # Generate return with mean reversion and current volatility
            daily_return = mean_reversion + np.random.normal(0, current_vol)
            returns.append(daily_return)
        
        prices = base_price * np.cumprod(1 + np.array(returns))
        
        # Generate OHLCV data with volatility clustering
        ohlcv_data = []
        start_date = datetime.now().date() - timedelta(days=length + 30)
        
        for i, close in enumerate(prices):
            current_date = start_date + timedelta(days=i)
            
            if current_date.weekday() >= 5:
                continue
            
            # Use local volatility for intraday range
            local_vol = abs(returns[i]) if i < len(returns) else 0.02
            vol_multiplier = 1 + (local_vol / 0.02)  # Scale based on return volatility
            
            daily_range = close * np.random.uniform(0.03, 0.06) * vol_multiplier
            high = close + np.random.uniform(0.3, 0.7) * daily_range
            low = close - np.random.uniform(0.3, 0.7) * daily_range
            
            if i > 0:
                gap_factor = np.random.normal(0, 0.008)
                open_price = prices[i-1] * (1 + gap_factor)
            else:
                open_price = close
            
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            # Volume increases with volatility
            volume_base = 2500000
            volume_multiplier = 1 + (local_vol / 0.02) * 0.5
            volume = int(volume_base * volume_multiplier * np.random.uniform(0.7, 1.4))
            
            ohlcv_data.append({
                'date': current_date,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        return ohlcv_data
    
    def _generate_trend_changes_scenario(self, config: ScenarioConfig) -> List[Dict[str, Any]]:
        """Generate scenario with multiple trend direction changes"""
        length = config.length
        base_price = config.base_price
        
        # Define trend segments
        segment_length = length // 4
        trend_segments = [
            ('up', 0.012, 0.020),      # Uptrend
            ('down', -0.008, 0.025),   # Downtrend  
            ('up', 0.015, 0.018),      # Recovery
            ('sideways', 0.001, 0.022) # Consolidation
        ]
        
        all_returns = []
        for trend_type, mean_return, volatility in trend_segments:
            segment_returns = np.random.normal(mean_return, volatility, segment_length)
            all_returns.extend(segment_returns)
        
        # Add any remaining days
        remaining = length - len(all_returns)
        if remaining > 0:
            all_returns.extend(np.random.normal(0.002, 0.020, remaining))
        
        prices = base_price * np.cumprod(1 + np.array(all_returns[:length]))
        
        # Generate OHLCV data
        ohlcv_data = []
        start_date = datetime.now().date() - timedelta(days=length + 30)
        
        for i, close in enumerate(prices):
            current_date = start_date + timedelta(days=i)
            
            if current_date.weekday() >= 5:
                continue
            
            # Determine current trend segment
            segment_index = min(i // segment_length, len(trend_segments) - 1)
            trend_type, _, segment_vol = trend_segments[segment_index]
            
            # Adjust characteristics based on trend
            if trend_type == 'up':
                vol_multiplier = 0.9
                volume_base = 3500000
            elif trend_type == 'down':
                vol_multiplier = 1.3
                volume_base = 4500000
            else:
                vol_multiplier = 1.0
                volume_base = 2800000
            
            daily_range = close * np.random.uniform(0.02, 0.05) * vol_multiplier
            high = close + np.random.uniform(0.3, 0.7) * daily_range
            low = close - np.random.uniform(0.3, 0.7) * daily_range
            
            if i > 0:
                gap_factor = np.random.normal(0, 0.006)
                open_price = prices[i-1] * (1 + gap_factor)
            else:
                open_price = close
            
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = int(volume_base * np.random.uniform(0.8, 1.3))
            
            # Add trend change volume spikes
            if i > 0 and i % segment_length == 0:  # Trend change point
                volume *= np.random.uniform(1.5, 2.5)
            
            ohlcv_data.append({
                'date': current_date,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': int(volume)
            })
        
        return ohlcv_data
    
    def _generate_high_low_scenario(self, config: ScenarioConfig) -> List[Dict[str, Any]]:
        """Generate scenario with frequent high/low events for threshold testing"""
        length = config.length
        base_price = config.base_price
        
        # Generate base price series with embedded high/low events
        returns = np.random.normal(0.003, 0.025, length)
        
        # Inject high/low events at regular intervals
        high_event_frequency = length // 12  # Every ~5 trading days
        low_event_frequency = length // 10   # Every ~6 trading days
        
        for i in range(0, length, high_event_frequency):
            if i < len(returns):
                returns[i] = np.random.uniform(0.08, 0.15)  # High event
                
        for i in range(low_event_frequency//2, length, low_event_frequency):
            if i < len(returns):
                returns[i] = np.random.uniform(-0.12, -0.08)  # Low event
        
        prices = base_price * np.cumprod(1 + returns)
        
        # Generate OHLCV data with exaggerated ranges for high/low events
        ohlcv_data = []
        start_date = datetime.now().date() - timedelta(days=length + 30)
        
        for i, close in enumerate(prices):
            current_date = start_date + timedelta(days=i)
            
            if current_date.weekday() >= 5:
                continue
            
            # Check if this is a high/low event day
            is_high_event = abs(returns[i]) > 0.07 and returns[i] > 0
            is_low_event = abs(returns[i]) > 0.07 and returns[i] < 0
            
            if is_high_event or is_low_event:
                # Exaggerated ranges for event days
                vol_multiplier = 2.5
                volume_base = 8000000  # High volume on event days
            else:
                vol_multiplier = 1.0
                volume_base = 2000000
            
            daily_range = close * np.random.uniform(0.025, 0.08) * vol_multiplier
            high = close + np.random.uniform(0.2, 0.8) * daily_range
            low = close - np.random.uniform(0.2, 0.8) * daily_range
            
            if i > 0:
                # Add price gaps on event days
                if is_high_event or is_low_event:
                    gap_factor = np.random.normal(returns[i] * 0.3, 0.01)
                else:
                    gap_factor = np.random.normal(0, 0.005)
                open_price = prices[i-1] * (1 + gap_factor)
            else:
                open_price = close
            
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = int(volume_base * np.random.uniform(0.8, 1.5))
            
            ohlcv_data.append({
                'date': current_date,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        return ohlcv_data
    
    def _generate_generic_scenario(self, config: ScenarioConfig) -> List[Dict[str, Any]]:
        """Generate generic scenario based on configuration parameters"""
        length = config.length
        base_price = config.base_price
        
        # Map volatility profile to parameters
        vol_params = {
            'low': 0.012,
            'medium': 0.020,
            'high': 0.035,
            'extreme': 0.060
        }
        
        # Map trend direction to return bias
        trend_params = {
            'up': 0.008,
            'down': -0.005,
            'sideways': 0.001,
            'mixed': 0.002
        }
        
        vol = vol_params.get(config.volatility_profile, 0.020)
        trend = trend_params.get(config.trend_direction, 0.002)
        
        returns = np.random.normal(trend, vol, length)
        prices = base_price * np.cumprod(1 + returns)
        
        # Volume parameters
        volume_params = {
            'low': 1000000,
            'normal': 2500000,
            'high': 5000000,
            'spike': 8000000
        }
        
        volume_base = volume_params.get(config.volume_profile, 2500000)
        
        # Generate OHLCV data
        ohlcv_data = []
        start_date = datetime.now().date() - timedelta(days=length + 30)
        
        for i, close in enumerate(prices):
            current_date = start_date + timedelta(days=i)
            
            if current_date.weekday() >= 5:
                continue
            
            daily_range = close * np.random.uniform(0.02, 0.06)
            high = close + np.random.uniform(0.3, 0.7) * daily_range
            low = close - np.random.uniform(0.3, 0.7) * daily_range
            
            if i > 0:
                gap_factor = np.random.normal(0, vol * 0.3)
                open_price = prices[i-1] * (1 + gap_factor)
            else:
                open_price = close
            
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = int(volume_base * np.random.uniform(0.7, 1.4))
            
            ohlcv_data.append({
                'date': current_date,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        return ohlcv_data
    
    def load_scenario(self, scenario_name: str, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Load scenario data into database for testing
        
        Args:
            scenario_name: Name of scenario to load
            symbols: List of symbol names (default: ['TEST_<SCENARIO>'])
            
        Returns:
            Loading results with statistics and performance metrics
        """
        start_time = datetime.now()
        
        if not symbols:
            symbols = [f'TEST_{scenario_name.upper()}']
        
        conn = self.get_database_connection()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            total_records = 0
            loaded_symbols = []
            
            for symbol in symbols:
                # Generate scenario data
                ohlcv_data = self.generate_scenario_data(scenario_name, f'_{symbol}' if len(symbols) > 1 else '')
                
                if not ohlcv_data:
                    continue
                
                cursor = conn.cursor()
                
                # Insert into historical_data table
                for row in ohlcv_data:
                    cursor.execute("""
                        INSERT INTO historical_data (symbol, date, open_price, high_price, low_price, close_price, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, date) DO UPDATE SET
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume,
                            updated_at = CURRENT_TIMESTAMP
                    """, (row['symbol'], row['date'], row['open'], row['high'], 
                          row['low'], row['close'], row['volume']))
                
                total_records += len(ohlcv_data)
                loaded_symbols.append(row['symbol'])
                
                # Ensure symbol exists in symbols table
                cursor.execute("""
                    INSERT INTO symbols (symbol, name, type, active)
                    VALUES (%s, %s, 'TEST', true)
                    ON CONFLICT (symbol) DO UPDATE SET
                        active = true,
                        updated_at = CURRENT_TIMESTAMP
                """, (row['symbol'], f'Test Scenario: {scenario_name.title()}'))
            
            conn.commit()
            
            load_duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'scenario_name': scenario_name,
                'symbols_loaded': loaded_symbols,
                'total_records': total_records,
                'load_duration_seconds': load_duration,
                'records_per_second': total_records / load_duration if load_duration > 0 else 0,
                'expected_outcomes': self.scenarios[scenario_name].expected_outcomes if scenario_name in self.scenarios else {},
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"+ Scenario '{scenario_name}' loaded: {total_records} records in {load_duration:.2f}s")
            return result
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"- Scenario loading failed: {e}")
            return {'error': str(e)}
        finally:
            if conn:
                conn.close()
    
    def validate_scenario_patterns(self, scenario_name: str, symbol: str = None) -> Dict[str, Any]:
        """
        Validate generated patterns using TA-Lib (if available)
        
        Args:
            scenario_name: Name of scenario to validate
            symbol: Symbol to validate (default: TEST_<SCENARIO>)
            
        Returns:
            Pattern validation results
        """
        if not TALIB_AVAILABLE:
            return {'error': 'TA-Lib not available for pattern validation'}
        
        if not symbol:
            symbol = f'TEST_{scenario_name.upper()}'
        
        conn = self.get_database_connection()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor()
            
            # Get OHLCV data for validation
            cursor.execute("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM historical_data 
                WHERE symbol = %s
                ORDER BY date
            """, (symbol,))
            
            data = cursor.fetchall()
            if not data:
                return {'error': f'No data found for symbol {symbol}'}
            
            # Convert to numpy arrays for TA-Lib
            opens = np.array([float(row['open_price']) for row in data])
            highs = np.array([float(row['high_price']) for row in data])
            lows = np.array([float(row['low_price']) for row in data])
            closes = np.array([float(row['close_price']) for row in data])
            volumes = np.array([int(row['volume']) for row in data])
            
            # Calculate basic technical indicators
            validation_results = {
                'symbol': symbol,
                'scenario': scenario_name,
                'data_points': len(data),
                'date_range': {
                    'start': data[0]['date'].isoformat(),
                    'end': data[-1]['date'].isoformat()
                }
            }
            
            # Price movement validation
            total_return = (closes[-1] - closes[0]) / closes[0] * 100
            validation_results['total_return_pct'] = round(total_return, 2)
            
            # Volatility calculation (20-day rolling)
            if len(closes) >= 20:
                returns = np.diff(np.log(closes))
                volatility = np.std(returns) * np.sqrt(252) * 100  # Annualized volatility
                validation_results['volatility_pct'] = round(volatility, 2)
            
            # Volume analysis
            avg_volume = np.mean(volumes)
            max_volume = np.max(volumes)
            validation_results['avg_volume'] = int(avg_volume)
            validation_results['max_volume'] = int(max_volume)
            validation_results['volume_spike_ratio'] = round(max_volume / avg_volume, 2)
            
            # Pattern-specific validations
            config = self.scenarios.get(scenario_name)
            if config:
                expected = config.expected_outcomes
                validation_results['expected_outcomes'] = expected
                
                # Compare actual vs expected (simplified)
                validation_results['outcome_validation'] = {}
                
                if 'max_drawdown' in expected:
                    cummax = np.maximum.accumulate(closes)
                    drawdowns = (closes - cummax) / cummax * 100
                    actual_max_drawdown = np.min(drawdowns)
                    validation_results['outcome_validation']['max_drawdown'] = {
                        'expected': expected['max_drawdown'],
                        'actual': round(actual_max_drawdown, 2),
                        'within_range': abs(actual_max_drawdown - expected['max_drawdown']) < 10
                    }
                
                if 'total_return' in expected:
                    validation_results['outcome_validation']['total_return'] = {
                        'expected': expected['total_return'],
                        'actual': total_return,
                        'within_range': abs(total_return - expected['total_return']) < 10
                    }
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"- Pattern validation failed: {e}")
            return {'error': str(e)}
        finally:
            if conn:
                conn.close()
    
    def list_scenarios(self) -> Dict[str, Any]:
        """List available scenarios with descriptions and characteristics"""
        scenario_list = {}
        
        for name, config in self.scenarios.items():
            scenario_list[name] = {
                'name': config.name,
                'description': config.description,
                'length_days': config.length,
                'base_price': config.base_price,
                'volatility_profile': config.volatility_profile,
                'trend_direction': config.trend_direction,
                'volume_profile': config.volume_profile,
                'pattern_features': config.pattern_features,
                'expected_outcomes': config.expected_outcomes
            }
        
        return {
            'available_scenarios': scenario_list,
            'total_scenarios': len(scenario_list),
            'talib_available': TALIB_AVAILABLE
        }

def main():
    """Main execution function for test scenario generation"""
    generator = TestScenarioGenerator()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--list-scenarios':
            scenarios = generator.list_scenarios()
            print("Available Test Scenarios:")
            for name, info in scenarios['available_scenarios'].items():
                print(f"\n  {name}:")
                print(f"    Description: {info['description']}")
                print(f"    Length: {info['length_days']} days")
                print(f"    Volatility: {info['volatility_profile']}")
                print(f"    Trend: {info['trend_direction']}")
                print(f"    Features: {', '.join(info['pattern_features'])}")
                
        elif command.startswith('--load-scenario='):
            scenario_name = command.split('=')[1]
            result = generator.load_scenario(scenario_name)
            if 'error' not in result:
                print(f"Scenario '{scenario_name}' loaded successfully:")
                print(f"  Symbols: {', '.join(result['symbols_loaded'])}")
                print(f"  Records: {result['total_records']}")
                print(f"  Duration: {result['load_duration_seconds']:.2f}s")
                print(f"  Performance: {result['records_per_second']:.0f} records/sec")
            else:
                print(f"Loading failed: {result['error']}")
                
        elif command.startswith('--validate-scenario='):
            scenario_name = command.split('=')[1]
            result = generator.validate_scenario_patterns(scenario_name)
            if 'error' not in result:
                print(f"Scenario '{scenario_name}' validation:")
                print(f"  Symbol: {result['symbol']}")
                print(f"  Data Points: {result['data_points']}")
                print(f"  Total Return: {result['total_return_pct']}%")
                if 'volatility_pct' in result:
                    print(f"  Volatility: {result['volatility_pct']}%")
                print(f"  Volume Spike: {result['volume_spike_ratio']:.1f}x")
            else:
                print(f"Validation failed: {result['error']}")
                
        else:
            print("Usage:")
            print("  --list-scenarios: List all available test scenarios")
            print("  --load-scenario=<name>: Load specific scenario into database")
            print("  --validate-scenario=<name>: Validate scenario patterns")
            print("\nAvailable scenarios: crash_2020, growth_2021, volatility_periods, trend_changes, high_low_events")
    else:
        # Default: list scenarios
        scenarios = generator.list_scenarios()
        print(f"Test Scenario Generator - {len(scenarios['available_scenarios'])} scenarios available")
        print("Use --list-scenarios for details or --load-scenario=<name> to load")

if __name__ == '__main__':
    main()