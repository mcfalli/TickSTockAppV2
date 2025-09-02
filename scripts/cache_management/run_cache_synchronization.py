#!/usr/bin/env python3
"""
Cache Entries Synchronization Script
Rebuilds stock and ETF cache entries based on cache_entries_directions.md

This script rebuilds cache entries from the symbols table to organize stocks and ETFs into:
- Market cap categories (mega_cap, large_cap, mid_cap, small_cap, micro_cap)
- Sector leaders (top 10 per sector)
- Market leaders (top_10_stocks, top_50, top_100, top_250, top_500)
- Themes (AI, Biotech, Cloud, Crypto, etc.)
- Industry groups (banks, insurance, software, retail)
- ETF universes
- Complete universes (all_stocks)

PRESERVES app_settings and other non-stock content.

Usage:
    python scripts/maintenance/run_cache_synchronization.py [--no-delete] [--verbose]
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add src to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', 'src')
sys.path.insert(0, src_path)

from core.services.cache_entries_synchronizer import CacheEntriesSynchronizer

def setup_logging(verbose: bool = False):
    """Configure logging for the script."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/cache_sync_{datetime.now().strftime("%Y%m%d")}.log')
        ]
    )

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Cache Entries Rebuild Synchronization')
    parser.add_argument('--no-delete', action='store_true', 
                       help='Skip deleting existing entries (append mode)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    print("=" * 70)
    print("🚀 TickStock Cache Entries Rebuild")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'APPEND' if args.no_delete else 'REPLACE'}")
    print()
    
    try:        
        # Execute cache rebuild
        synchronizer = CacheEntriesSynchronizer()
        
        start_time = datetime.now()
        stats = synchronizer.rebuild_stock_cache_entries(delete_existing=not args.no_delete)
        end_time = datetime.now()
        
        duration = end_time - start_time
        
        print()
        print("=" * 70)
        print("✅ CACHE REBUILD COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"Duration: {duration.total_seconds():.2f} seconds")
        print()
        print("📊 Rebuild Statistics:")
        print(f"  • Deleted entries: {stats['deleted_entries']}")
        print(f"  • Market cap categories: {stats['market_cap_entries']}")
        print(f"  • Sector leader groups: {stats['sector_leader_entries']}")
        print(f"  • Market leader groups: {stats['market_leader_entries']}")
        print(f"  • Theme entries: {stats['theme_entries']}")
        print(f"  • Industry groups: {stats['industry_entries']}")
        print(f"  • ETF categories: {stats['etf_entries']}")
        print(f"  • Complete universe: {stats['complete_entries']}")
        print(f"  • Stats summaries: {stats['stats_entries']}")
        print(f"  • Redis notifications: {stats['redis_notifications']}")
        print()
        
        # Log completion
        logger.info(f"Cache rebuild completed successfully in {duration.total_seconds():.2f}s")
        logger.info(f"Stats: {stats}")
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ CACHE REBUILD FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        
        logger.error(f"Cache rebuild failed: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())