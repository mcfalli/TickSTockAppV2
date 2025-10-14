#!/usr/bin/env python3
"""
Stock Cache Entries Analysis Script
Analyzes current cache_entries table to understand stock data structure

NOTE: Cache entries are now managed via the Admin Historical Load page
using the "Update and Organize Cache" button. This script is for analysis only.
"""

import json
import logging
import os
import sys
from datetime import datetime

import psycopg2

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from config.database_config import get_database_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define stock-related types (based on provided data)
STOCK_RELATED_TYPES = [
    'stock_universe',
    'etf_universe',    # Added ETF universe
    'stock_stats',
    'themes',
    'UNIVERSE',        # Legacy - should be cleaned up
    'priority_stocks'
]

# Non-stock types that should be preserved
PROTECTED_TYPES = [
    'app_settings',
    'cache_config'     # Added cache configuration protection
]

def analyze_cache_structure(conn):
    """Analyze the structure of cache_entries table."""
    print("\n" + "=" * 60)
    print("CACHE ENTRIES STRUCTURE ANALYSIS")
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
            if type_name in STOCK_RELATED_TYPES:
                category = "📦 Stock-Related"
            elif type_name in PROTECTED_TYPES:
                category = "🔒 Protected"
            else:
                category = "⚙️ Other"
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
                if type_name in STOCK_RELATED_TYPES:
                    category = "Stock"
                elif type_name in PROTECTED_TYPES:
                    category = "Protected"
                else:
                    category = "Other"
                print(f"\n  [{category}] {type_name}:")
            print(f"    • {name:30} {count:4,} entries")

        return type_counts, type_name_counts

def analyze_stock_universe_entries(conn):
    """Analyze stock_universe entries in detail."""
    print("\n" + "=" * 60)
    print("🔍 STOCK UNIVERSE ANALYSIS")
    print("=" * 60)

    with conn.cursor() as cur:
        # Get all stock_universe and etf_universe entries with key details
        cur.execute("""
            SELECT type, name, key, 
                   CASE 
                       WHEN type = 'etf_universe' AND jsonb_typeof(value::jsonb) = 'array' 
                       THEN jsonb_array_length(value::jsonb)::text
                       WHEN type = 'etf_universe' 
                       THEN 'N/A'
                       ELSE jsonb_extract_path_text(value::jsonb, 'count')
                   END as entry_count,
                   LENGTH(value::text) as value_size,
                   updated_at
            FROM cache_entries
            WHERE type IN ('stock_universe', 'etf_universe', 'UNIVERSE')
            ORDER BY type, name, key
        """)

        entries = cur.fetchall()

        print("\n📊 Universe Entries:")
        print("-" * 80)
        print(f"{'Type':15} {'Name':20} {'Key':25} {'Count':8} {'Size':10} {'Updated'}")
        print("-" * 80)

        for entry in entries:
            type_val, name, key, entry_count, value_size, updated = entry
            updated_str = updated.strftime('%Y-%m-%d') if updated else 'Unknown'
            size_kb = f"{value_size/1024:.1f}KB" if value_size else "N/A"
            count_str = str(entry_count) if entry_count else "N/A"

            print(f"{type_val:15} {name:20} {key:25} {count_str:8} {size_kb:10} {updated_str}")

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
        # Get symbols statistics (updated table name)
        cur.execute("""
            SELECT 
                COUNT(*) as total_stocks,
                COUNT(DISTINCT sector) as sectors,
                COUNT(DISTINCT industry) as industries,
                MAX(sic_updated_at) as last_update
            FROM symbols
            WHERE type = 'CS' AND active = true
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
        print("  Symbols Table:")
        print(f"    • Total Stocks:    {stock_main_stats[0]:,}")
        print(f"    • Sectors:         {stock_main_stats[1]}")
        print(f"    • Industries:      {stock_main_stats[2]}")
        print(f"    • Last SIC Update: {stock_main_stats[3]}")

        if cache_stats and cache_stats[0]:
            print("\n  Cache Entries:")
            print(f"    • Cached Stocks:   {cache_stats[0]}")

            # Check if cache is out of sync
            if stock_main_stats[0] != int(cache_stats[0] or 0):
                diff = stock_main_stats[0] - int(cache_stats[0] or 0)
                print(f"\n  ⚠️  Cache is out of sync by {abs(diff):,} stocks")
                print("     Recommendation: Reload cache from stock_main")
        else:
            print("\n  ⚠️  No cache statistics found")

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
    print("  2. Use Admin Interface: /admin/historical-data -> 'Update and Organize Cache'")
    print("  3. Or run command line: python scripts/maintenance/run_cache_synchronization.py")
    print("  4. Schedule regular cache updates (weekly/monthly)")
    print("  5. Monitor cache configuration in 'cache_config' entries")

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

def analyze_cache_configuration(conn):
    """Analyze cache configuration entries."""
    print("\n" + "=" * 60)
    print("🔧 CACHE CONFIGURATION ANALYSIS")
    print("=" * 60)

    with conn.cursor() as cur:
        # Get all cache configuration entries
        cur.execute("""
            SELECT name, key, value, updated_at
            FROM cache_entries
            WHERE type = 'cache_config'
            ORDER BY name, key
        """)

        config_entries = cur.fetchall()

        if config_entries:
            print("\n⚙️ Configuration Categories:")
            print("-" * 70)

            current_name = None
            for name, key, value, updated in config_entries:
                if current_name != name:
                    current_name = name
                    print(f"\n📋 {name.replace('_', ' ').title()}:")

                # Parse value for display
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                        if isinstance(parsed_value, list):
                            display_value = f"[{len(parsed_value)} items: {', '.join(parsed_value[:3])}{'...' if len(parsed_value) > 3 else ''}]"
                        else:
                            display_value = str(parsed_value)
                    except:
                        display_value = str(value)
                else:
                    display_value = str(value)

                updated_str = updated.strftime('%Y-%m-%d %H:%M') if updated else 'Unknown'
                print(f"  • {key:25} {display_value[:40]:40} (Updated: {updated_str})")

            # Check for missing configuration
            expected_configs = {
                'market_cap_thresholds': ['mega_cap', 'large_cap', 'mid_cap', 'small_cap', 'micro_cap'],
                'theme_definitions': ['ai', 'biotech', 'cloud', 'crypto', 'cybersecurity', 'ev', 'fintech'],
                'industry_groups': ['banks', 'insurance', 'software', 'retail'],
                'etf_categories': ['etf_broad_market', 'etf_sectors', 'etf_growth', 'etf_value'],
                'complete_limits': ['stocks_full_metadata_limit', 'etfs_full_metadata_limit']
            }

            print("\n🔍 Configuration Validation:")
            missing_configs = []

            config_dict = {}
            for name, key, value, updated in config_entries:
                if name not in config_dict:
                    config_dict[name] = set()
                config_dict[name].add(key)

            for config_name, expected_keys in expected_configs.items():
                actual_keys = config_dict.get(config_name, set())
                missing_keys = set(expected_keys) - actual_keys
                if missing_keys:
                    missing_configs.append(f"{config_name}: {', '.join(missing_keys)}")

            if missing_configs:
                print("  ⚠️ Missing configurations:")
                for missing in missing_configs:
                    print(f"    - {missing}")
            else:
                print("  ✅ All expected configurations present")

        else:
            print("\n⚠️  No cache configuration found!")
            print("   This means the system is using hardcoded defaults.")
            print("   Run the INSERT statements to set up database-driven configuration.")

def analyze_sic_integration(conn):
    """Analyze the SIC code integration and symbol enrichment."""
    print("\n" + "=" * 60)
    print("SIC INTEGRATION ANALYSIS")
    print("=" * 60)

    with conn.cursor() as cur:
        # Check symbol enrichment status
        cur.execute("""
            SELECT 
                COUNT(*) as total_symbols,
                COUNT(CASE WHEN sector IS NOT NULL AND sector != 'Unknown' THEN 1 END) as enriched_symbols,
                COUNT(CASE WHEN sic_code IS NOT NULL THEN 1 END) as symbols_with_sic,
                COUNT(DISTINCT sector) as unique_sectors,
                COUNT(DISTINCT industry) as unique_industries
            FROM symbols 
            WHERE active = true
        """)

        enrichment_stats = cur.fetchone()
        total, enriched, with_sic, sectors, industries = enrichment_stats

        print("\n📊 Symbol Enrichment Status:")
        print("-" * 50)
        print(f"  Total Active Symbols:     {total:,}")
        print(f"  Enriched with Sector:     {enriched:,} ({enriched/total*100:.1f}%)")
        print(f"  Have SIC Codes:           {with_sic:,} ({with_sic/total*100:.1f}%)")
        print(f"  Unique Sectors:           {sectors}")
        print(f"  Unique Industries:        {industries}")

        # Show sector distribution
        cur.execute("""
            SELECT sector, COUNT(*) as count, 
                   AVG(market_cap) as avg_market_cap,
                   MAX(market_cap) as max_market_cap
            FROM symbols 
            WHERE sector IS NOT NULL AND sector != 'Unknown' 
              AND active = true AND market_cap IS NOT NULL
            GROUP BY sector 
            ORDER BY count DESC
        """)

        sector_stats = cur.fetchall()

        print("\n🏢 Sector Distribution:")
        print("-" * 70)
        print(f"{'Sector':25} {'Count':8} {'Avg Market Cap':15} {'Largest'}")
        print("-" * 70)

        for sector, count, avg_cap, max_cap in sector_stats:
            avg_str = f"${float(avg_cap)/1e9:.1f}B" if avg_cap else "N/A"
            max_str = f"${float(max_cap)/1e9:.1f}B" if max_cap else "N/A"
            print(f"{sector:25} {count:8} {avg_str:15} {max_str}")

        # Check SIC configuration status
        cur.execute("""
            SELECT name, COUNT(*) as config_count
            FROM cache_entries 
            WHERE type = 'cache_config' 
              AND name IN ('sic_mapping', 'sic_ranges')
            GROUP BY name
        """)

        sic_configs = cur.fetchall()

        print("\n🔧 SIC Configuration Status:")
        print("-" * 40)
        for name, count in sic_configs:
            print(f"  {name:20} {count:,} entries")

def analyze_sector_cache_performance(conn):
    """Analyze how well the sector-based cache entries are performing."""
    print("\n" + "=" * 60)
    print("🚀 SECTOR CACHE PERFORMANCE")
    print("=" * 60)

    with conn.cursor() as cur:
        # Check sector leaders cache entries
        cur.execute("""
            SELECT 
                key,
                jsonb_extract_path_text(value::jsonb, 'count')::int as stock_count,
                LENGTH(value::text) as json_size,
                updated_at
            FROM cache_entries 
            WHERE type = 'stock_universe' 
              AND name = 'sector_leaders'
            ORDER BY jsonb_extract_path_text(value::jsonb, 'count')::int DESC
        """)

        sector_leaders = cur.fetchall()

        if sector_leaders:
            print("\n🏆 Sector Leaders Cache Entries:")
            print("-" * 70)
            print(f"{'Sector Key':30} {'Stocks':8} {'JSON Size':12} {'Updated'}")
            print("-" * 70)

            total_stocks = 0
            for key, stock_count, json_size, updated in sector_leaders:
                updated_str = updated.strftime('%Y-%m-%d %H:%M') if updated else 'Unknown'
                size_kb = f"{json_size/1024:.1f}KB" if json_size else "N/A"
                total_stocks += stock_count if stock_count else 0
                print(f"{key:30} {stock_count:8} {size_kb:12} {updated_str}")

            print(f"\n📈 Total stocks in sector leaders: {total_stocks}")
        else:
            print("\n⚠️  No sector leaders cache found!")
            print("   This suggests the cache synchronizer hasn't run with the new SIC data.")

        # Check industry groups
        cur.execute("""
            SELECT 
                key,
                jsonb_extract_path_text(value::jsonb, 'count')::int as company_count,
                updated_at
            FROM cache_entries 
            WHERE type = 'stock_universe' 
              AND name = 'industry_groups'
            ORDER BY jsonb_extract_path_text(value::jsonb, 'count')::int DESC
            LIMIT 10
        """)

        industry_groups = cur.fetchall()

        if industry_groups:
            print("\n🏭 Top Industry Groups:")
            print("-" * 60)
            print(f"{'Industry Key':40} {'Companies':10} {'Updated'}")
            print("-" * 60)

            for key, company_count, updated in industry_groups:
                updated_str = updated.strftime('%Y-%m-%d %H:%M') if updated else 'Unknown'
                print(f"{key:40} {company_count:10} {updated_str}")
        else:
            print("\n⚠️  No industry groups cache found!")

def analyze_cache_quality(conn):
    """Analyze the quality and completeness of cache entries."""
    print("\n" + "=" * 60)
    print("✨ CACHE QUALITY ANALYSIS")
    print("=" * 60)

    with conn.cursor() as cur:
        # Check for "Unknown" entries in cache
        cur.execute("""
            SELECT 
                type,
                name,
                COUNT(*) as entries_with_unknown
            FROM cache_entries 
            WHERE value::text ILIKE '%"Unknown"%'
            GROUP BY type, name
            ORDER BY entries_with_unknown DESC
        """)

        unknown_entries = cur.fetchall()

        if unknown_entries:
            print("\n⚠️  Cache Entries with 'Unknown' Values:")
            print("-" * 60)
            print(f"{'Type':20} {'Name':25} {'Count'}")
            print("-" * 60)

            for cache_type, name, count in unknown_entries:
                print(f"{cache_type:20} {name:25} {count}")

            print("\n💡 These entries may benefit from SIC enrichment or updated classification logic.")
        else:
            print("\n✅ No 'Unknown' values found in cache entries!")

        # Sample a sector leader entry to show quality
        cur.execute("""
            SELECT key, value
            FROM cache_entries 
            WHERE type = 'stock_universe' 
              AND name = 'sector_leaders'
              AND key NOT LIKE '%unknown%'
            LIMIT 1
        """)

        sample_entry = cur.fetchone()

        if sample_entry:
            key, value = sample_entry
            print(f"\n📋 Sample Sector Leader Entry ({key}):")
            print("-" * 60)

            try:
                data = json.loads(value) if isinstance(value, str) else value
                stocks = data.get('stocks', [])[:3]  # Show first 3 stocks

                print(f"  Sector: {key.replace('top_10_', '').replace('_', ' ').title()}")
                print(f"  Total Stocks: {data.get('count', 'N/A')}")
                print("  Sample Companies:")

                for stock in stocks:
                    name = stock.get('name', 'N/A')[:30]
                    ticker = stock.get('ticker', 'N/A')
                    sector = stock.get('sector', 'N/A')
                    market_cap = stock.get('market_cap', 0)
                    cap_str = f"${float(market_cap)/1e9:.1f}B" if market_cap else "N/A"
                    print(f"    • {ticker:6} {name:30} {sector:20} {cap_str}")

            except Exception as e:
                print(f"    Error parsing entry: {e}")

def analyze_specific_symbols(conn, symbol_list):
    """Analyze specific symbols for targeted reporting."""
    print("\n" + "=" * 60)
    print("SPECIFIC SYMBOLS ANALYSIS")
    print("=" * 60)

    symbols = [s.strip().upper() for s in symbol_list]
    print(f"Analyzing symbols: {', '.join(symbols)}")

    with conn.cursor() as cur:
        # Check symbol existence and basic info
        cur.execute("""
            SELECT symbol, name, type, market, active, sector, industry, 
                   sic_code, market_cap, sic_updated_at
            FROM symbols 
            WHERE symbol = ANY(%s)
            ORDER BY symbol
        """, (symbols,))

        symbol_data = cur.fetchall()
        found_symbols = {row[0] for row in symbol_data}
        missing_symbols = set(symbols) - found_symbols

        print("\nSYMBOL STATUS:")
        print("-" * 60)
        print(f"{'Symbol':8} {'Name':25} {'Type':6} {'Market':8} {'Sector':20} {'SIC'}")
        print("-" * 60)

        for symbol, name, sym_type, market, active, sector, industry, sic_code, market_cap, sic_updated in symbol_data:
            name_short = name[:24] if name else "N/A"
            sector_short = sector[:19] if sector else "None"
            sic_short = str(sic_code) if sic_code else "None"
            status = "Active" if active else "Inactive"
            print(f"{symbol:8} {name_short:25} {sym_type:6} {market:8} {sector_short:20} {sic_short}")

        if missing_symbols:
            print(f"\nMISSING SYMBOLS: {', '.join(missing_symbols)}")
            print("These symbols are not in the symbols table.")

        # Check cache entries containing these symbols
        print("\nCACHE ENTRIES CONTAINING THESE SYMBOLS:")
        print("-" * 80)

        for symbol in found_symbols:
            cur.execute("""
                SELECT type, name, key, 
                       CASE 
                           WHEN value::jsonb ? 'ticker' THEN 'ticker'
                           WHEN value::jsonb ? 'symbol' THEN 'symbol' 
                           WHEN value::text ILIKE %s THEN 'text_match'
                           ELSE 'no_match'
                       END as match_type,
                       LENGTH(value::text) as size,
                       updated_at
                FROM cache_entries 
                WHERE value::text ILIKE %s
                ORDER BY type, name, key
            """, (f'%{symbol}%', f'%{symbol}%'))

            cache_entries = cur.fetchall()

            if cache_entries:
                print(f"\n  {symbol} found in {len(cache_entries)} cache entries:")
                for cache_type, name, key, match_type, size, updated in cache_entries:
                    updated_str = updated.strftime('%Y-%m-%d %H:%M') if updated else 'Unknown'
                    print(f"    {cache_type:15} {name:20} {key:25} ({size:,} bytes, {updated_str})")
            else:
                print(f"\n  {symbol} NOT found in any cache entries")

        # Check if symbols would be picked up by cache synchronizer
        print("\nCACHE SYNCHRONIZER ELIGIBILITY:")
        print("-" * 60)

        for symbol_info in symbol_data:
            symbol, name, sym_type, market, active, sector, industry, sic_code, market_cap, sic_updated = symbol_info

            # Check sector leader eligibility
            if sector and sector != 'Unknown' and active and sym_type == 'CS' and market_cap:
                cur.execute("""
                    SELECT COUNT(*) as rank
                    FROM symbols 
                    WHERE sector = %s 
                      AND active = true 
                      AND type = 'CS' 
                      AND market_cap > %s 
                      AND market_cap IS NOT NULL
                """, (sector, market_cap))

                rank = cur.fetchone()[0] + 1  # +1 because we're counting those above us

                sector_leader_eligible = "YES (Top 10)" if rank <= 10 else f"NO (Rank {rank})"
            else:
                sector_leader_eligible = "NO (Missing: "
                missing = []
                if not sector or sector == 'Unknown': missing.append("sector")
                if not active: missing.append("active")
                if sym_type != 'CS': missing.append("common stock")
                if not market_cap: missing.append("market cap")
                sector_leader_eligible += ", ".join(missing) + ")"

            # Check industry group eligibility
            industry_eligible = "YES" if industry and industry != 'Unknown' and active else "NO"

            print(f"  {symbol:8}")
            print(f"    Sector Leader:  {sector_leader_eligible}")
            print(f"    Industry Group: {industry_eligible}")
            if market_cap:
                print(f"    Market Cap:     ${float(market_cap)/1e9:.1f}B")

def main():
    """Main analysis function."""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze TickStock cache entries')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols to analyze specifically')
    parser.add_argument('--full', action='store_true', help='Run full analysis (default if no symbols specified)')

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("TICKSTOCK - Cache Entries Analysis Tool")
    print("=" * 80)

    try:
        # Connect to database
        print("\nConnecting to database...")
        db_config = get_database_config()
        conn = psycopg2.connect(**db_config)
        print("Connected successfully")

        # Check if specific symbols were requested
        if args.symbols:
            symbol_list = [s.strip() for s in args.symbols.split(',')]
            analyze_specific_symbols(conn, symbol_list)
        else:
            # Run full analysis
            analyze_cache_structure(conn)
            analyze_cache_configuration(conn)
            analyze_sic_integration(conn)  # NEW: SIC integration analysis
            analyze_sector_cache_performance(conn)  # NEW: Sector cache performance
            analyze_stock_universe_entries(conn)
            analyze_themes_entries(conn)
            analyze_priority_stocks(conn)
            analyze_cache_quality(conn)  # NEW: Cache quality analysis
            analyze_data_freshness(conn)
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
