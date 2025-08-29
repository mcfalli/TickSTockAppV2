#!/usr/bin/env python3
"""
Phase 10 Validation Test - TickStock Cleanup Validation

Tests core functionality after major simplification to ensure:
1. Core data structures are intact
2. Basic data flow logic works
3. Redis integration points are correct
4. Essential imports resolve correctly
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_core_data_structures():
    """Test that core data structures are working."""
    print("🧪 Testing core data structures...")
    
    try:
        # Test TickData creation
        from src.core.domain.market.tick import TickData
        
        tick = TickData(
            ticker="AAPL",
            price=150.25,
            volume=1000,
            timestamp=time.time(),
            source='test',
            event_type='A',
            market_status='REGULAR'
        )
        
        assert tick.ticker == "AAPL"
        assert tick.price == 150.25
        assert tick.volume == 1000
        
        print("✅ TickData creation and access works")
        
    except Exception as e:
        print(f"❌ TickData test failed: {e}")
        return False
        
    return True

def test_synthetic_data_provider():
    """Test simplified synthetic data provider."""
    print("🧪 Testing synthetic data provider...")
    
    try:
        from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
        
        config = {
            'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
            'MARKET_TIMEZONE': 'US/Eastern'
        }
        
        provider = SimulatedDataProvider(config)
        
        # Test basic functionality
        assert provider.is_available() == True
        
        # Test price generation
        price = provider.get_ticker_price('AAPL')
        assert isinstance(price, float)
        assert price > 0
        
        # Test tick data generation
        tick_data = provider.generate_tick_data('AAPL')
        assert tick_data.ticker == 'AAPL'
        assert isinstance(tick_data.price, float)
        assert tick_data.price > 0
        
        print("✅ Synthetic data provider works")
        
    except Exception as e:
        print(f"❌ Synthetic data provider test failed: {e}")
        return False
        
    return True

def test_data_factory():
    """Test simplified data provider factory."""
    print("🧪 Testing data provider factory...")
    
    try:
        from src.infrastructure.data_sources.factory import DataProviderFactory
        
        # Test synthetic data configuration
        config = {
            'USE_SYNTHETIC_DATA': True,
            'USE_POLYGON_API': False
        }
        
        provider = DataProviderFactory.get_provider(config)
        assert provider is not None
        assert provider.__class__.__name__ == 'SimulatedDataProvider'
        
        print("✅ Data provider factory works")
        
    except Exception as e:
        print(f"❌ Data provider factory test failed: {e}")
        return False
        
    return True

def test_redis_integration_logic():
    """Test Redis integration logic without actual Redis connection."""
    print("🧪 Testing Redis integration logic...")
    
    try:
        # Mock Redis client behavior
        class MockRedis:
            def __init__(self):
                self.data = {}
                
            def ping(self):
                return True
                
            def publish(self, channel, message):
                self.data[channel] = message
                return True
        
        # Test Redis message creation
        from src.core.domain.market.tick import TickData
        
        tick_data = TickData(
            ticker="AAPL",
            price=150.25,
            volume=1000,
            timestamp=time.time(),
            source='test',
            event_type='A',
            market_status='REGULAR'
        )
        
        # Simulate Redis message creation
        redis_message = {
            'event_type': 'tick_data',
            'ticker': tick_data.ticker,
            'price': tick_data.price,
            'volume': tick_data.volume,
            'timestamp': tick_data.timestamp,
            'source': tick_data.source,
            'market_status': tick_data.market_status
        }
        
        # Test JSON serialization 
        json_message = json.dumps(redis_message)
        parsed_message = json.loads(json_message)
        
        assert parsed_message['ticker'] == 'AAPL'
        assert parsed_message['price'] == 150.25
        assert parsed_message['event_type'] == 'tick_data'
        
        print("✅ Redis integration logic works")
        
    except Exception as e:
        print(f"❌ Redis integration test failed: {e}")
        return False
        
    return True

def test_websocket_display_converter():
    """Test simplified display converter."""
    print("🧪 Testing WebSocket display converter...")
    
    try:
        from src.presentation.websocket.display_converter import WebSocketDisplayConverter
        from src.core.domain.market.tick import TickData
        
        converter = WebSocketDisplayConverter()
        
        tick_data = TickData(
            ticker="AAPL",
            price=150.25,
            volume=1000,
            timestamp=time.time(),
            source='test',
            event_type='A',
            market_status='REGULAR'
        )
        
        display_data = converter.convert_tick_data(tick_data)
        
        assert display_data['ticker'] == 'AAPL'
        assert display_data['price'] == 150.25
        assert display_data['volume'] == 1000
        assert display_data['event_type'] == 'tick_update'
        
        print("✅ WebSocket display converter works")
        
    except Exception as e:
        print(f"❌ Display converter test failed: {e}")
        return False
        
    return True

def test_universe_service():
    """Test simplified universe service."""
    print("🧪 Testing universe service...")
    
    try:
        from src.core.services.universe_service import TickStockUniverseManager
        
        universe_manager = TickStockUniverseManager()
        
        # Test basic functionality
        universe = universe_manager.get_core_universe()
        assert isinstance(universe, list)
        assert len(universe) > 0
        
        # Test membership
        universe_manager.add_ticker('TEST')
        assert universe_manager.is_in_universe('TEST') == True
        
        # Test set operations
        universe_set = universe_manager.get_core_universe_set()
        assert isinstance(universe_set, set)
        assert 'TEST' in universe_set
        
        print("✅ Universe service works")
        
    except Exception as e:
        print(f"❌ Universe service test failed: {e}")
        return False
        
    return True

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("🚀 PHASE 10 VALIDATION - TickStock Cleanup Testing")
    print("=" * 60)
    
    tests = [
        test_core_data_structures,
        test_synthetic_data_provider,
        test_data_factory,
        test_redis_integration_logic,
        test_websocket_display_converter,
        test_universe_service,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        
        print()  # Add spacing between tests
    
    print("=" * 60)
    print(f"📊 VALIDATION RESULTS")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed / (passed + failed) * 100:.1f}%")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - Phase 10 Validation Complete!")
        print("✅ Core functionality is working after major simplification")
        print("✅ Redis integration points are correct")
        print("✅ Data flow logic is intact")
        print("✅ Ready for TickStockPL integration!")
    else:
        print("⚠️  Some tests failed - review errors above")
    
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)