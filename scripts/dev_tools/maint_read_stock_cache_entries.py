#!/usr/bin/env python3
"""
Stock Cache Entries Analysis Script
Analyzes current cache_entries table to understand stock data structure
Part of Step 2 in the cache loading process
"""

import psycopg2
from psycopg2 import sql
import json
from datetime import datetime
from collections import defaultdict
import logging

# Configuration
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "tickstock",
    "user": "app_readwrite",
    "password": "1DfTGVBsECVtJa"
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define stock-related types (based on provided data)
STOCK_RELATED_TYPES = [
    'stock_universe',
    'stock_stats',
    'themes',
    'UNIVERSE',  # Note: appears to be duplicate/legacy
    'priority_stocks'
]

# Non-stock types that should be preserved
NON_STOCK_TYPES = [
    'app_settings'
]

def analyze_cache_structure(conn):
    """Analyze the structure of cache_entries table."""
    print("\n" + "=" * 60)
    print("📊 CACHE ENTRIES STRUCTURE ANALYSIS")
    print("=" * 60)
    
    with conn.cursor() as cur:
        # Get distinct types and their counts
        cur.execute("""
            SELECT type, COUNT(*) as count
            FROM cache_entries
            GROUP BY type
            ORDER BY type
        """)
        type_counts = cur.fetchall()
        
        print("\n📈 Entry Types and Counts:")
        print("-" * 40)
        total = 0
        for type_name, count in type_counts:
            total += count
            category = "📦 Stock-Related" if type_name in STOCK_RELATED_TYPES else "⚙️ System"
            print(f"  {category:20} {type_name:20} {count:6,} entries")
        print("-" * 40)
        print(f"  {'Total:':41} {total:6,} entries")
        
        # Get detailed breakdown for each type
        print("\n📋 Detailed Type/Name Breakdown:")
        print("-" * 60)
        
        cur.execute("""
            SELECT type, name, COUNT(*) as count
            FROM cache_entries
            GROUP BY type, name
            ORDER BY type, name
        """)
        type_name_counts = cur.fetchall()
        
        current_type = None
        for type_name, name, count in type_name_counts:
            if current_type != type_name:
                current_type = type_name
                category = "Stock" if type_name in STOCK_RELATED_TYPES else "System"
                print(f"\n  [{category}] {type_name}:")
            print(f"    • {name:30} {count:4,} entries")
        
        return type_counts, type_name_counts

def analyze_stock_universe_entries(conn):
    """Analyze stock_universe entries in detail."""
    print("\n" + "=" * 60)
    print("🔍 STOCK UNIVERSE ANALYSIS")
    print("=" * 60)
    
    with conn.cursor() as cur:
        # Get all stock_universe entries with key details
        cur.execute("""
            SELECT type, name, key, 
                   jsonb_extract_path_text(value::jsonb, 'count') as stock_count,
                   LENGTH(value::text) as value_size,
                   updated_at
            FROM cache_entries
            WHERE type IN ('stock_universe', 'UNIVERSE')
            ORDER BY type, name, key
        """)
        
        entries = cur.fetchall()
        
        print("\n📊 Stock Universe Entries:")
        print("-" * 80)
        print(f"{'Type':15} {'Name':20} {'Key':25} {'Stocks':8} {'Size':10} {'Updated'}")
        print("-" * 80)
        
        for entry in entries:
            type_val, name, key, stock_count, value_size, updated = entry
            updated_str = updated.strftime('%Y-%m-%d') if updated else 'Unknown'
            size_kb = f"{value_size/1024:.1f}KB" if value_size else "N/A"
            stock_count_str = stock_count if stock_count else "N/A"
            
            print(f"{type_val:15} {name:20} {key:25} {stock_count_str:8} {size_kb:10} {updated_str}")

def analyze_themes_entries(conn):
    """Analyze theme entries."""
    print("\n" + "=" * 60)
    print("🎯 THEMES ANALYSIS")
    print("=" * 60)
    
    with conn.cursor() as cur:
        # Get all theme entries
        cur.execute("""
            SELECT name, key, value
            FROM cache_entries
            WHERE type = 'themes'
            ORDER BY name
        """)
        
        themes = cur.fetchall()
        
        print("\n🏷️ Available Themes:")
        print("-" * 60)
        
        for theme_name, key, value in themes:
            try:
                # Handle both formats: direct list or wrapped in dict
                if isinstance(value, list):
                    tickers = value
                elif isinstance(value, dict) and 'value' in value:
                    # Legacy format with nested 'value' key
                    tickers = value['value']
                    if isinstance(tickers, str):
                        import json
                        tickers = json.loads(tickers)
                elif isinstance(value, str):
                    # Direct JSON string
                    import json
                    tickers = json.loads(value)
                else:
                    tickers = []
                    
                if isinstance(tickers, list):
                    ticker_count = len(tickers)
                    ticker_preview = ', '.join(tickers[:5])
                    if len(tickers) > 5:
                        ticker_preview += f"... (+{len(tickers)-5} more)"
                else:
                    ticker_count = "N/A"
                    ticker_preview = f"Invalid format: {type(tickers)}"
            except Exception as e:
                ticker_count = "Error"
                ticker_preview = f"Parse error: {str(e)}"
            
            print(f"  • {theme_name:15} ({ticker_count:3} stocks): {ticker_preview}")

def analyze_data_freshness(conn):
    """Analyze how fresh the cached data is."""
    print("\n" + "=" * 60)
    print("⏰ DATA FRESHNESS ANALYSIS")
    print("=" * 60)
    
    with conn.cursor() as cur:
        # Get update timestamps
        cur.execute("""
            SELECT 
                type,
                MIN(updated_at) as oldest_update,
                MAX(updated_at) as newest_update,
                COUNT(DISTINCT DATE(updated_at)) as update_days
            FROM cache_entries
            WHERE type IN %s
            GROUP BY type
            ORDER BY type
        """, (tuple(STOCK_RELATED_TYPES),))
        
        freshness = cur.fetchall()
        
        print("\n📅 Update Timeline by Type:")
        print("-" * 70)
        print(f"{'Type':20} {'Oldest Update':20} {'Newest Update':20} {'Days'}")
        print("-" * 70)
        
        for type_name, oldest, newest, days in freshness:
            oldest_str = oldest.strftime('%Y-%m-%d %H:%M') if oldest else 'Unknown'
            newest_str = newest.strftime('%Y-%m-%d %H:%M') if newest else 'Unknown'
            print(f"{type_name:20} {oldest_str:20} {newest_str:20} {days:4}")
        
        # Check if data needs refresh
        cur.execute("""
            SELECT MAX(updated_at) as last_update
            FROM cache_entries
            WHERE type IN %s
        """, (tuple(STOCK_RELATED_TYPES),))
        
        last_update = cur.fetchone()[0]
        if last_update:
            days_old = (datetime.now() - last_update).days
            print(f"\n⚠️  Cache data is {days_old} days old")
            if days_old > 7:
                print("   📌 Recommendation: Cache data should be refreshed")

def analyze_stock_main_comparison(conn):
    """Compare stock_main table with cache_entries."""
    print("\n" + "=" * 60)
    print("🔄 STOCK_MAIN vs CACHE_ENTRIES COMPARISON")
    print("=" * 60)
    
    with conn.cursor() as cur:
        # Get stock_main statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_stocks,
                COUNT(DISTINCT sector) as sectors,
                COUNT(DISTINCT industry) as industries,
                MAX(last_updated_date) as last_update
            FROM stock_main
            WHERE type = 'CS'
        """)
        
        stock_main_stats = cur.fetchone()
        
        # Get cache statistics for comparison
        cur.execute("""
            SELECT 
                jsonb_extract_path_text(value::jsonb, 'overview', 'total_stocks') as cached_stocks
            FROM cache_entries
            WHERE type = 'stock_stats' 
            AND name = 'universe'
            AND key = 'summary'
            LIMIT 1
        """)
        
        cache_stats = cur.fetchone()
        
        print("\n📊 Comparison:")
        print("-" * 60)
        print(f"  Stock Main Table:")
        print(f"    • Total Stocks:    {stock_main_stats[0]:,}")
        print(f"    • Sectors:         {stock_main_stats[1]}")
        print(f"    • Industries:      {stock_main_stats[2]}")
        print(f"    • Last Update:     {stock_main_stats[3]}")
        
        if cache_stats and cache_stats[0]:
            print(f"\n  Cache Entries:")
            print(f"    • Cached Stocks:   {cache_stats[0]}")
            
            # Check if cache is out of sync
            if stock_main_stats[0] != int(cache_stats[0] or 0):
                diff = stock_main_stats[0] - int(cache_stats[0] or 0)
                print(f"\n  ⚠️  Cache is out of sync by {abs(diff):,} stocks")
                print(f"     Recommendation: Reload cache from stock_main")
        else:
            print(f"\n  ⚠️  No cache statistics found")

def generate_recommendations(conn):
    """Generate recommendations for cache loading."""
    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS")
    print("=" * 60)
    
    recommendations = []
    
    with conn.cursor() as cur:
        # Check for duplicate/legacy entries
        cur.execute("""
            SELECT COUNT(*)
            FROM cache_entries
            WHERE type = 'UNIVERSE'
        """)
        universe_count = cur.fetchone()[0]
        
        if universe_count > 0:
            recommendations.append(
                "Remove legacy 'UNIVERSE' type entries (use 'stock_universe' instead)"
            )
        
        # Check for missing standard categories
        cur.execute("""
            SELECT DISTINCT name
            FROM cache_entries
            WHERE type = 'stock_universe'
        """)
        existing_names = [row[0] for row in cur.fetchall()]
        
        expected_names = [
            'market_cap', 'sector_leaders', 'market_leaders',
            'themes', 'industry', 'complete', 'thematic'
        ]
        
        missing_names = [n for n in expected_names if n not in existing_names]
        if missing_names:
            recommendations.append(
                f"Add missing categories: {', '.join(missing_names)}"
            )
        
        # Check data age
        cur.execute("""
            SELECT MAX(updated_at)
            FROM cache_entries
            WHERE type IN %s
        """, (tuple(STOCK_RELATED_TYPES),))
        
        last_update = cur.fetchone()[0]
        if last_update:
            days_old = (datetime.now() - last_update).days
            if days_old > 7:
                recommendations.append(
                    f"Refresh cache data (currently {days_old} days old)"
                )
    
    print("\n📝 Action Items:")
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("  ✅ Cache appears to be in good condition")
    
    print("\n🔧 Next Steps:")
    print("  1. Review the analysis above")
    print("  2. Run maint_load_stock_cache_entries.py to reload cache")
    print("  3. Schedule regular cache updates (daily/weekly)")

def analyze_priority_stocks(conn):
    """Analyze priority stocks entries."""
    print("\n" + "=" * 60)
    print("⭐ PRIORITY STOCKS ANALYSIS")
    print("=" * 60)
    
    with conn.cursor() as cur:
        # Check if priority stocks exist
        cur.execute("""
            SELECT name, key, 
                   jsonb_extract_path_text(value::jsonb, 'count') as stock_count,
                   jsonb_extract_path_text(value::jsonb, 'top_priority_count') as top_count,
                   jsonb_extract_path_text(value::jsonb, 'secondary_priority_count') as secondary_count,
                   updated_at
            FROM cache_entries
            WHERE type = 'priority_stocks'
            ORDER BY name, key
        """)
        
        priority_entries = cur.fetchall()
        
        if priority_entries:
            print("\n📊 Priority Stock Entries:")
            print("-" * 70)
            
            for name, key, stock_count, top_count, secondary_count, updated in priority_entries:
                updated_str = updated.strftime('%Y-%m-%d %H:%M') if updated else 'Unknown'
                print(f"  • {name}/{key}:")
                print(f"    Total: {stock_count or 'N/A'} stocks")
                if top_count:
                    print(f"    Top Priority: {top_count} stocks")
                if secondary_count:
                    print(f"    Secondary Priority: {secondary_count} stocks")
                print(f"    Last Updated: {updated_str}")
        else:
            print("\n⚠️  No priority stocks found in cache")
            print("   Recommendation: Add priority_stocks for processing prioritization")

def main():
    """Main analysis function."""
    print("\n" + "=" * 80)
    print("🚀 TICKSTOCK - Cache Entries Analysis Tool")
    print("=" * 80)
    
    try:
        # Connect to database
        print("\n🔍 Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected successfully")
        
        # Run analyses
        analyze_cache_structure(conn)
        analyze_stock_universe_entries(conn)
        analyze_themes_entries(conn)
        analyze_priority_stocks(conn)  # New analysis
        analyze_data_freshness(conn)
        analyze_stock_main_comparison(conn)
        generate_recommendations(conn)
        
        print("\n" + "=" * 80)
        print("✅ Analysis Complete")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        print(f"\n❌ Error: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()