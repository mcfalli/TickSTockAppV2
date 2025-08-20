#!/usr/bin/env python3
"""
Validate that the router reference error is fixed
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_router_references():
    """Test that all router references work"""
    try:
        # Test imports
        from src.processing.channels.channel_router import (
            DataChannelRouter, RouterConfig, RoutingStrategy
        )
        print("SUCCESS: Router imports working")
        
        # Test router creation
        config = RouterConfig()
        router = DataChannelRouter(config)
        print("SUCCESS: Router instantiation working")
        
        # Test that we can access router properties
        print(f"Channel types available: {list(router.channels.keys())}")
        print(f"Routing strategy: {router.config.routing_strategy}")
        
        # Test strategy setting
        router.config.routing_strategy = RoutingStrategy.LOAD_BASED
        print(f"Strategy changed to: {router.config.routing_strategy}")
        
        # Test router statistics (should not crash)
        stats = router.get_routing_statistics()
        print(f"Router stats available: {len(stats)} entries")
        
        print("SUCCESS: All router references resolved")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Router Reference Validation Test")
    print("=" * 40)
    
    success = asyncio.run(test_router_references())
    
    if success:
        print("VALIDATION: PASSED - No reference errors")
        sys.exit(0)
    else:
        print("VALIDATION: FAILED - Reference errors remain")  
        sys.exit(1)