"""
Unit Tests for Data Type Models - Sprint 106

Tests the OHLCVData and FMVData models with validation scenarios,
serialization/deserialization, and compatibility with existing systems.
"""

import pytest
import time
from datetime import datetime

from src.shared.models.data_types import (
    OHLCVData, 
    FMVData, 
    identify_data_type, 
    convert_to_typed_data
)


class TestOHLCVData:
    """Test suite for OHLCVData model"""
    
    def test_ohlcv_data_creation_valid(self):
        """Test creating valid OHLCVData instance"""
        ohlcv = OHLCVData(
            ticker="AAPL",
            timestamp=time.time(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
            avg_volume=800000.0
        )
        
        assert ohlcv.ticker == "AAPL"
        assert ohlcv.open == 150.0
        assert ohlcv.high == 152.0
        assert ohlcv.low == 149.0
        assert ohlcv.close == 151.0
        assert ohlcv.volume == 1000000
        assert ohlcv.avg_volume == 800000.0
        assert ohlcv.timeframe == "1m"  # Default
        assert ohlcv.source == "unknown"  # Default
    
    def test_ohlcv_data_percent_change_calculation(self):
        """Test automatic percent change calculation"""
        ohlcv = OHLCVData(
            ticker="AAPL",
            timestamp=time.time(),
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
            avg_volume=800000.0
        )
        
        # Should calculate (102 - 100) / 100 * 100 = 2.0%
        assert abs(ohlcv.percent_change - 2.0) < 0.01
    
    def test_ohlcv_data_validation_valid_prices(self):
        """Test OHLCV data with valid price relationships"""
        ohlcv = OHLCVData(
            ticker="AAPL",
            timestamp=time.time(),
            open=150.0,
            high=152.0,  # High >= max(open, close)
            low=149.0,   # Low <= min(open, close)
            close=151.0,
            volume=1000000,
            avg_volume=800000.0
        )
        
        assert ohlcv.validate()
    
    def test_ohlcv_data_validation_invalid_high(self):
        """Test validation fails when high < max(open, close)"""
        with pytest.raises(ValueError, match="High .* must be >= max\\(open .*, close .*\\)"):
            OHLCVData(
                ticker="AAPL",
                timestamp=time.time(),
                open=150.0,
                high=149.0,  # Invalid: high < open
                low=148.0,
                close=151.0,
                volume=1000000,
                avg_volume=800000.0
            )
    
    def test_ohlcv_data_validation_invalid_low(self):
        """Test validation fails when low > min(open, close)"""
        with pytest.raises(ValueError, match="Low .* must be <= min\\(open .*, close .*\\)"):
            OHLCVData(
                ticker="AAPL",
                timestamp=time.time(),
                open=150.0,
                high=152.0,
                low=151.0,  # Invalid: low > open
                close=149.0,
                volume=1000000,
                avg_volume=800000.0
            )
    
    def test_ohlcv_data_validation_negative_values(self):
        """Test validation fails with negative prices or volume"""
        # Negative price - will fail on price relationship first, so use better test data
        with pytest.raises(ValueError, match="Invalid open"):
            OHLCVData(
                ticker="AAPL",
                timestamp=time.time(),
                open=-150.0,
                high=-149.0,  # Set high negative too to avoid relationship error
                low=-152.0,   # Set low negative too to avoid relationship error
                close=-151.0, # Set close negative too to avoid relationship error
                volume=1000000,
                avg_volume=800000.0
            )
        
        # Negative volume
        with pytest.raises(ValueError, match="Invalid volume"):
            OHLCVData(
                ticker="AAPL",
                timestamp=time.time(),
                open=150.0,
                high=152.0,
                low=149.0,
                close=151.0,
                volume=-1000000,
                avg_volume=800000.0
            )
    
    def test_ohlcv_data_serialization(self):
        """Test to_dict and from_dict serialization"""
        original = OHLCVData(
            ticker="AAPL",
            timestamp=1642781234.567,
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
            avg_volume=800000.0,
            timeframe="5m",
            source="polygon"
        )
        
        # Serialize to dict
        data_dict = original.to_dict()
        
        # Deserialize from dict
        restored = OHLCVData.from_dict(data_dict)
        
        # Verify all fields match
        assert restored.ticker == original.ticker
        assert restored.timestamp == original.timestamp
        assert restored.open == original.open
        assert restored.high == original.high
        assert restored.low == original.low
        assert restored.close == original.close
        assert restored.volume == original.volume
        assert restored.avg_volume == original.avg_volume
        assert restored.timeframe == original.timeframe
        assert restored.source == original.source
    
    def test_ohlcv_data_utility_methods(self):
        """Test utility methods for analysis"""
        ohlcv = OHLCVData(
            ticker="AAPL",
            timestamp=time.time(),
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=3000000,  # 3x avg volume
            avg_volume=1000000.0
        )
        
        # Test price range
        assert ohlcv.get_price_range() == 10.0  # 105 - 95
        
        # Test price change
        assert ohlcv.get_price_change() == 2.0  # 102 - 100
        
        # Test volume surge detection
        assert ohlcv.is_volume_surge(2.5)  # 3x > 2.5x threshold
        assert not ohlcv.is_volume_surge(3.5)  # 3x < 3.5x threshold
        
        # Test significant move detection
        assert ohlcv.is_significant_move(1.5)  # 2.0% > 1.5% threshold
        assert not ohlcv.is_significant_move(2.5)  # 2.0% < 2.5% threshold


class TestFMVData:
    """Test suite for FMVData model"""
    
    def test_fmv_data_creation_valid(self):
        """Test creating valid FMVData instance"""
        fmv = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=155.0,
            market_price=150.0,
            confidence=0.85
        )
        
        assert fmv.ticker == "AAPL"
        assert fmv.fmv == 155.0
        assert fmv.market_price == 150.0
        assert fmv.confidence == 0.85
        assert fmv.valuation_model == "unknown"  # Default
        assert fmv.source == "unknown"  # Default
    
    def test_fmv_data_deviation_calculation(self):
        """Test automatic deviation calculation"""
        fmv = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=155.0,  # 3.33% above market
            market_price=150.0,
            confidence=0.85
        )
        
        # Should calculate (155 - 150) / 150 * 100 = 3.33%
        assert abs(fmv.deviation_percent - 3.333333333333333) < 0.01
    
    def test_fmv_data_validation_valid(self):
        """Test FMV data validation with valid values"""
        fmv = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=155.0,
            market_price=150.0,
            confidence=0.85
        )
        
        assert fmv.validate()
    
    def test_fmv_data_validation_invalid_prices(self):
        """Test validation fails with invalid prices"""
        # Invalid FMV price
        with pytest.raises(ValueError, match="Invalid FMV price"):
            FMVData(
                ticker="AAPL",
                timestamp=time.time(),
                fmv=-155.0,
                market_price=150.0,
                confidence=0.85
            )
        
        # Invalid market price
        with pytest.raises(ValueError, match="Invalid market price"):
            FMVData(
                ticker="AAPL",
                timestamp=time.time(),
                fmv=155.0,
                market_price=-150.0,
                confidence=0.85
            )
    
    def test_fmv_data_validation_invalid_confidence(self):
        """Test validation fails with invalid confidence values"""
        # Confidence > 1.0
        with pytest.raises(ValueError, match="Invalid confidence"):
            FMVData(
                ticker="AAPL",
                timestamp=time.time(),
                fmv=155.0,
                market_price=150.0,
                confidence=1.5
            )
        
        # Confidence < 0.0
        with pytest.raises(ValueError, match="Invalid confidence"):
            FMVData(
                ticker="AAPL",
                timestamp=time.time(),
                fmv=155.0,
                market_price=150.0,
                confidence=-0.1
            )
    
    def test_fmv_data_serialization(self):
        """Test to_dict and from_dict serialization"""
        original = FMVData(
            ticker="AAPL",
            timestamp=1642781234.567,
            fmv=155.0,
            market_price=150.0,
            confidence=0.85,
            valuation_model="dcf",
            source="polygon"
        )
        
        # Serialize to dict
        data_dict = original.to_dict()
        
        # Deserialize from dict
        restored = FMVData.from_dict(data_dict)
        
        # Verify all fields match
        assert restored.ticker == original.ticker
        assert restored.timestamp == original.timestamp
        assert restored.fmv == original.fmv
        assert restored.market_price == original.market_price
        assert restored.confidence == original.confidence
        assert restored.valuation_model == original.valuation_model
        assert restored.source == original.source
    
    def test_fmv_data_valuation_analysis(self):
        """Test valuation analysis methods"""
        # Undervalued scenario (FMV > market price)
        undervalued_fmv = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=160.0,
            market_price=150.0,  # 6.67% undervalued
            confidence=0.9
        )
        
        assert undervalued_fmv.get_valuation_signal() == "undervalued"
        assert undervalued_fmv.is_high_confidence(0.8)
        assert undervalued_fmv.is_significant_deviation(5.0)  # 6.67% > 5.0%
        assert not undervalued_fmv.is_significant_deviation(10.0)  # 6.67% < 10.0%
        
        # Overvalued scenario (FMV < market price)
        overvalued_fmv = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=140.0,
            market_price=150.0,  # 6.67% overvalued
            confidence=0.9
        )
        
        assert overvalued_fmv.get_valuation_signal() == "overvalued"
        assert overvalued_fmv.deviation_percent < 0  # Negative deviation
        
        # Fair value scenario
        fair_fmv = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=150.5,
            market_price=150.0,  # 0.33% difference
            confidence=0.8
        )
        
        assert fair_fmv.get_valuation_signal() == "fair_value"
    
    def test_fmv_data_signal_strength(self):
        """Test signal strength calculation"""
        # High deviation, high confidence = strong signal
        strong_signal = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=180.0,  # 20% deviation (capped at 20%)
            market_price=150.0,
            confidence=1.0
        )
        
        signal_strength = strong_signal.get_signal_strength()
        assert signal_strength == 1.0  # Max signal strength
        
        # Low deviation, high confidence = weak signal
        weak_signal = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=151.0,  # 0.67% deviation
            market_price=150.0,
            confidence=1.0
        )
        
        signal_strength = weak_signal.get_signal_strength()
        assert signal_strength < 0.1  # Very weak signal


class TestDataTypeIdentification:
    """Test suite for data type identification utilities"""
    
    def test_identify_data_type_ohlcv_object(self):
        """Test identifying OHLCVData object"""
        ohlcv = OHLCVData(
            ticker="AAPL",
            timestamp=time.time(),
            open=150.0, high=152.0, low=149.0, close=151.0,
            volume=1000000, avg_volume=800000.0
        )
        
        assert identify_data_type(ohlcv) == 'ohlcv'
    
    def test_identify_data_type_fmv_object(self):
        """Test identifying FMVData object"""
        fmv = FMVData(
            ticker="AAPL",
            timestamp=time.time(),
            fmv=155.0, market_price=150.0, confidence=0.85
        )
        
        assert identify_data_type(fmv) == 'fmv'
    
    def test_identify_data_type_ohlcv_dict(self):
        """Test identifying OHLCV dictionary"""
        ohlcv_dict = {
            'ticker': 'AAPL',
            'open': 150.0,
            'high': 152.0,
            'low': 149.0,
            'close': 151.0,
            'volume': 1000000
        }
        
        assert identify_data_type(ohlcv_dict) == 'ohlcv'
    
    def test_identify_data_type_fmv_dict(self):
        """Test identifying FMV dictionary"""
        fmv_dict = {
            'ticker': 'AAPL',
            'fmv': 155.0,
            'market_price': 150.0,
            'confidence': 0.85
        }
        
        assert identify_data_type(fmv_dict) == 'fmv'
    
    def test_identify_data_type_tick_dict(self):
        """Test identifying tick dictionary"""
        tick_dict = {
            'ticker': 'AAPL',
            'price': 150.0,
            'timestamp': time.time()
        }
        
        assert identify_data_type(tick_dict) == 'tick'
    
    def test_identify_data_type_unknown(self):
        """Test identifying unknown data type"""
        unknown_data = {'random': 'data'}
        
        assert identify_data_type(unknown_data) == 'unknown'
        assert identify_data_type("string") == 'unknown'
        assert identify_data_type(12345) == 'unknown'


class TestDataTypeConversion:
    """Test suite for data type conversion utilities"""
    
    def test_convert_to_ohlcv_data(self):
        """Test converting dictionary to OHLCVData"""
        ohlcv_dict = {
            'ticker': 'AAPL',
            'timestamp': time.time(),
            'open': 150.0,
            'high': 152.0,
            'low': 149.0,
            'close': 151.0,
            'volume': 1000000,
            'avg_volume': 800000.0
        }
        
        ohlcv_data = convert_to_typed_data(ohlcv_dict, 'ohlcv')
        
        assert isinstance(ohlcv_data, OHLCVData)
        assert ohlcv_data.ticker == 'AAPL'
        assert ohlcv_data.open == 150.0
        assert ohlcv_data.close == 151.0
        assert ohlcv_data.volume == 1000000
    
    def test_convert_to_fmv_data(self):
        """Test converting dictionary to FMVData"""
        fmv_dict = {
            'ticker': 'AAPL',
            'timestamp': time.time(),
            'fmv': 155.0,
            'market_price': 150.0,
            'confidence': 0.85
        }
        
        fmv_data = convert_to_typed_data(fmv_dict, 'fmv')
        
        assert isinstance(fmv_data, FMVData)
        assert fmv_data.ticker == 'AAPL'
        assert fmv_data.fmv == 155.0
        assert fmv_data.market_price == 150.0
        assert fmv_data.confidence == 0.85
    
    def test_convert_auto_detection(self):
        """Test automatic data type detection during conversion"""
        # OHLCV dict with auto-detection
        ohlcv_dict = {
            'ticker': 'AAPL',
            'timestamp': time.time(),
            'open': 150.0, 'high': 152.0, 'low': 149.0, 'close': 151.0,
            'volume': 1000000, 'avg_volume': 800000.0
        }
        
        data = convert_to_typed_data(ohlcv_dict)
        assert isinstance(data, OHLCVData)
        
        # FMV dict with auto-detection
        fmv_dict = {
            'ticker': 'AAPL',
            'timestamp': time.time(),
            'fmv': 155.0,
            'market_price': 150.0,
            'confidence': 0.85
        }
        
        data = convert_to_typed_data(fmv_dict)
        assert isinstance(data, FMVData)
    
    def test_convert_invalid_data_type(self):
        """Test conversion with invalid data type"""
        with pytest.raises(ValueError, match="Unknown data type"):
            convert_to_typed_data({'data': 'invalid'}, 'invalid_type')
    
    def test_convert_conversion_failure(self):
        """Test handling conversion failures"""
        # Missing required fields
        invalid_dict = {'ticker': 'AAPL'}
        
        with pytest.raises(ValueError, match="Failed to convert data"):
            convert_to_typed_data(invalid_dict, 'ohlcv')


class TestModelCompatibility:
    """Test compatibility with existing systems"""
    
    def test_ohlcv_from_aggregate_event(self):
        """Test creating OHLCVData from aggregate event structure"""
        aggregate_event = {
            'ticker': 'AAPL',
            'time': time.time(),
            'minute_open': 150.0,
            'minute_high': 152.0,
            'minute_low': 149.0,
            'minute_close': 151.0,
            'minute_volume': 1000000,
            'accumulated_volume': 50000000,
            'minute_vwap': 150.8,
            'timeframe': '1m'
        }
        
        ohlcv = OHLCVData.from_aggregate_event(aggregate_event)
        
        assert ohlcv.ticker == 'AAPL'
        assert ohlcv.open == 150.0
        assert ohlcv.high == 152.0
        assert ohlcv.low == 149.0
        assert ohlcv.close == 151.0
        assert ohlcv.volume == 1000000
        assert ohlcv.vwap == 150.8
        assert ohlcv.timeframe == '1m'
    
    def test_fmv_from_fmv_event(self):
        """Test creating FMVData from FMV event structure"""
        fmv_event = {
            'ticker': 'AAPL',
            'time': time.time(),
            'fmv_price': 155.0,
            'market_price': 150.0,
            'confidence': 0.85,
            'fmv_vs_market_pct': 3.33,
            'valuation_model': 'dcf'
        }
        
        fmv = FMVData.from_fmv_event(fmv_event)
        
        assert fmv.ticker == 'AAPL'
        assert fmv.fmv == 155.0
        assert fmv.market_price == 150.0
        assert fmv.confidence == 0.85
        assert fmv.valuation_model == 'dcf'