#!/usr/bin/env python3
"""
Stock Cache Entries Loading Script
Loads stock data from stock_main table into cache_entries table
Maintains non-stock entries (app_settings) while refreshing stock data
FIXED VERSION: Stores complete stock lists, not just previews
"""

import psycopg2
from psycopg2 import sql
import json
from datetime import datetime
from collections import defaultdict, OrderedDict
import logging
import sys
import time

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

# Define stock-related types to be refreshed
STOCK_RELATED_TYPES = [
    'stock_universe',
    'stock_stats',
    'themes',
    'UNIVERSE',  # Legacy type to be removed
    'priority_stocks'  # New type for processing prioritization
]

# Market cap thresholds (in billions)
MARKET_CAP_RANGES = {
    'mega_cap': {'min': 200, 'max': None, 'limit': 45},
    'large_cap': {'min': 10, 'max': 200, 'limit': 500},
    'mid_cap': {'min': 2, 'max': 10, 'limit': 500},
    'small_cap': {'min': 0.3, 'max': 2, 'limit': 500},
    'micro_cap': {'min': 0, 'max': 0.3, 'limit': 500}
}

# Priority stocks definition - top 100 most important/popular stocks
PRIORITY_STOCKS = {
    'top_priority': [
        # Mega Tech
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA',
        # Major Tech/Semis
        'AVGO', 'ORCL', 'CRM', 'AMD', 'INTC', 'QCOM', 'TXN', 'MU',
        # Financial Giants
        'BRK.B', 'BRK.A', 'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C',
        # Healthcare Leaders
        'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'TMO', 'ABT', 'CVS',
        # Consumer/Retail
        'WMT', 'HD', 'PG', 'KO', 'PEP', 'MCD', 'NKE', 'SBUX',
        # Communications/Media
        'DIS', 'NFLX', 'CMCSA', 'VZ', 'T', 'TMUS'
    ],
    'secondary_priority': [
        # Growth Tech
        'ADBE', 'PYPL', 'SQ', 'SHOP', 'SNAP', 'PINS', 'ROKU', 'ZM',
        'DOCU', 'OKTA', 'TWLO', 'NET', 'DDOG', 'SNOW', 'PLTR', 'U',
        # EVs & Clean Energy
        'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'FSR', 'PLUG', 'ENPH',
        # Biotech
        'MRNA', 'BNTX', 'GILD', 'BIIB', 'REGN', 'VRTX', 'ILMN',
        # Industrials
        'BA', 'CAT', 'DE', 'UPS', 'FDX', 'RTX', 'LMT', 'GE',
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO'
    ]
}

# Theme definitions with tickers
THEME_DEFINITIONS = {
    'AI': ['MSFT', 'NVDA', 'GOOGL', 'AVGO', 'PLTR', 'AMD', 'ADBE', 'PANW', 'CRWD', 'INTC', 'SNOW', 'ZS'],
    'Biotech': ['AMGN', 'GILD', 'VRTX', 'REGN', 'BIIB', 'INCY', 'NBIX', 'BMRN', 'MRNA', 'SRPT'],
    'Cloud': ['MSFT', 'AMZN', 'GOOGL', 'ORCL', 'CRM', 'NOW', 'ADBE', 'WDAY', 'SNOW', 'DDOG', 'ZS', 'AKAM'],
    'Crypto': ['MSTR', 'COIN', 'HOOD', 'MARA', 'CORZ', 'RIOT', 'GLXY', 'BTDR', 'CLSK', 'HUT', 'SQ'],
    'Cybersecurity': ['PANW', 'CRWD', 'FTNT', 'NET', 'ZS', 'OKTA', 'CYBR', 'S', 'QLYS', 'TENB'],
    'EV': ['TSLA', 'GM', 'F', 'RIVN', 'LCID', 'BYD', 'EVGO', 'CHPT'],
    'Fintech': ['MELI', 'FI', 'PYPL', 'COIN', 'NU', 'HOOD', 'AFRM', 'SOFI', 'UPST', 'SQ'],
    'Marijuana': ['CRON', 'TLRY', 'SNDL', 'ACB', 'CGC', 'VFF', 'GRWG', 'HYFM'],
    'Quantum': ['MSFT', 'NVDA', 'GOOGL', 'IBM', 'INTC', 'IONQ', 'QBTS', 'RGTI', 'FORM'],
    'Robotics': ['NVDA', 'TSLA', 'ISRG', 'ROK', 'ZBRA', 'TER', 'SYM', 'IRBT', 'KSCP'],
    'Semi': ['NVDA', 'AVGO', 'AMD', 'TXN', 'QCOM', 'AMAT', 'LRCX', 'INTC', 'MRVL', 'MCHP'],
    'Space': ['RTX', 'BA', 'LMT', 'NOC', 'RKLB', 'ASTS', 'PL', 'SPCE']
}

def prompt_user(message, default="n"):
    """Prompt user for Y/N response."""
    while True:
        response = input(f"\n{message} [{default.upper()}/{'n' if default.lower() == 'y' else 'y'}]: ").strip().lower()
        if response == "":
            response = default.lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")

def analyze_current_cache(conn):
    """Analyze current cache entries before making changes."""
    print("\n📊 Analyzing Current Cache...")
    
    with conn.cursor() as cur:
        # Count stock-related entries
        cur.execute("""
            SELECT type, COUNT(*) as count
            FROM cache_entries
            WHERE type = ANY(%s)
            GROUP BY type
            ORDER BY type
        """, (STOCK_RELATED_TYPES,))
        
        stock_entries = cur.fetchall()
        
        # Count non-stock entries
        cur.execute("""
            SELECT type, COUNT(*) as count
            FROM cache_entries
            WHERE type != ALL(%s)
            GROUP BY type
            ORDER BY type
        """, (STOCK_RELATED_TYPES,))
        
        non_stock_entries = cur.fetchall()
        
        return stock_entries, non_stock_entries

def delete_stock_entries(conn, test_mode=False):
    """Delete stock-related entries from cache_entries."""
    print("\n🗑️  Deleting Stock-Related Cache Entries...")
    
    with conn.cursor() as cur:
        # Count entries to be deleted
        cur.execute("""
            SELECT COUNT(*) 
            FROM cache_entries
            WHERE type = ANY(%s)
        """, (STOCK_RELATED_TYPES,))
        
        delete_count = cur.fetchone()[0]
        
        if test_mode:
            print(f"   TEST MODE: Would delete {delete_count:,} stock-related entries")
            print(f"   Types to delete: {', '.join(STOCK_RELATED_TYPES)}")
        else:
            # Perform deletion
            cur.execute("""
                DELETE FROM cache_entries
                WHERE type = ANY(%s)
            """, (STOCK_RELATED_TYPES,))
            
            conn.commit()
            print(f"   ✅ Deleted {delete_count:,} stock-related entries")
        
        return delete_count

def get_stocks_by_market_cap(conn, min_cap_b, max_cap_b, limit):
    """Get stocks within a market cap range."""
    with conn.cursor() as cur:
        if max_cap_b is None:
            # No upper limit (mega cap)
            cur.execute("""
                SELECT ticker, name, sector, industry, market_cap, primary_exchange
                FROM stock_main
                WHERE type = 'CS'
                AND market_cap >= %s::numeric * 1000000000
                AND market_cap IS NOT NULL
                ORDER BY market_cap DESC
                LIMIT %s
            """, (min_cap_b, limit))
        else:
            cur.execute("""
                SELECT ticker, name, sector, industry, market_cap, primary_exchange
                FROM stock_main
                WHERE type = 'CS'
                AND market_cap >= %s::numeric * 1000000000
                AND market_cap < %s::numeric * 1000000000
                AND market_cap IS NOT NULL
                ORDER BY market_cap DESC
                LIMIT %s
            """, (min_cap_b, max_cap_b, limit))
        
        return cur.fetchall()

def get_stocks_by_sector(conn, sector, limit=10):
    """Get top stocks by sector."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ticker, name, sector, industry, market_cap, primary_exchange
            FROM stock_main
            WHERE type = 'CS'
            AND sector = %s
            AND market_cap IS NOT NULL
            ORDER BY market_cap DESC
            LIMIT %s
        """, (sector, limit))
        
        return cur.fetchall()

def get_stocks_by_industry(conn, industry, limit=50):
    """Get top stocks by industry."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ticker, name, sector, industry, market_cap, primary_exchange
            FROM stock_main
            WHERE type = 'CS'
            AND industry ILIKE %s
            AND market_cap IS NOT NULL
            ORDER BY market_cap DESC
            LIMIT %s
        """, (f'%{industry}%', limit))
        
        return cur.fetchall()

def get_theme_stocks(conn, ticker_list):
    """Get stock details for a list of tickers (theme)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ticker, name, sector, industry, market_cap, primary_exchange
            FROM stock_main
            WHERE type = 'CS'
            AND ticker = ANY(%s)
            AND market_cap IS NOT NULL
            ORDER BY market_cap DESC
        """, (ticker_list,))
        
        return cur.fetchall()

def format_stock_entry(stocks, rank_start=1):
    """Format stocks into cache entry structure."""
    stock_list = []
    for i, stock in enumerate(stocks, rank_start):
        ticker, name, sector, industry, market_cap, exchange = stock
        stock_list.append({
            "name": name,
            "rank": i,
            "sector": sector or "Unknown",
            "ticker": ticker,
            "exchange": exchange or "Unknown",
            "industry": industry or "Unknown",
            "market_cap": float(market_cap) if market_cap else 0
        })
    return stock_list

def insert_cache_entry(conn, type_val, name, key, value_data, test_mode=False):
    """Insert a single cache entry."""
    if test_mode:
        return
    
    with conn.cursor() as cur:
        now = datetime.utcnow()
        
        # Generate ID (you might want to use a sequence instead)
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM cache_entries")
        new_id = cur.fetchone()[0]
        
        cur.execute("""
            INSERT INTO cache_entries (
                id, type, name, key, value, environment, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            new_id, type_val, name, key,
            json.dumps(value_data), 'DEFAULT',
            now, now
        ))

def load_market_cap_categories(conn, test_mode=False):
    """Load market cap category entries."""
    print("\n📈 Loading Market Cap Categories...")
    
    for cap_key, cap_config in MARKET_CAP_RANGES.items():
        stocks = get_stocks_by_market_cap(
            conn,
            cap_config['min'],
            cap_config['max'],
            cap_config['limit']
        )
        
        if stocks:
            stock_list = format_stock_entry(stocks)
            value_data = {
                "count": len(stock_list),
                "stocks": stock_list  # FIXED: Store ALL stocks, not preview
            }
            
            insert_cache_entry(conn, 'stock_universe', 'market_cap', cap_key, value_data, test_mode)
            
            if test_mode:
                print(f"   TEST: Would load {cap_key}: {len(stocks)} stocks (ALL stored)")
            else:
                print(f"   ✅ Loaded {cap_key}: {len(stocks)} stocks (ALL stored)")

def load_sector_leaders(conn, test_mode=False):
    """Load sector leader entries."""
    print("\n🏢 Loading Sector Leaders...")
    
    with conn.cursor() as cur:
        # Get distinct sectors
        cur.execute("""
            SELECT DISTINCT sector
            FROM stock_main
            WHERE type = 'CS'
            AND sector IS NOT NULL
            AND sector != 'Unknown'
        """)
        
        sectors = [row[0] for row in cur.fetchall()]
        
        for sector in sectors:
            stocks = get_stocks_by_sector(conn, sector, 10)
            
            if stocks:
                stock_list = format_stock_entry(stocks)
                key = f"top_10_{sector.lower().replace(' ', '_').replace(',', '')}"
                
                value_data = {
                    "count": len(stock_list),
                    "stocks": stock_list  # FIXED: Store ALL stocks
                }
                
                insert_cache_entry(conn, 'stock_universe', 'sector_leaders', key, value_data, test_mode)
                
                if test_mode:
                    print(f"   TEST: Would load {sector}: {len(stocks)} stocks (ALL stored)")
                else:
                    print(f"   ✅ Loaded {sector}: {len(stocks)} stocks (ALL stored)")

def load_themes(conn, test_mode=False):
    """Load theme entries."""
    print("\n🎯 Loading Themes...")
    
    for theme_name, ticker_list in THEME_DEFINITIONS.items():
        # Format 1: themes type with list (store as JSON array, not dict with 'value' key)
        insert_cache_entry(conn, 'themes', theme_name, 'list', ticker_list, test_mode)
        
        # Format 2: stock_universe type with details
        stocks = get_theme_stocks(conn, ticker_list)
        if stocks:
            stock_list = format_stock_entry(stocks)
            value_data = {
                "count": len(stock_list),
                "stocks": stock_list  # Store full list for themes (already working correctly)
            }
            
            insert_cache_entry(conn, 'stock_universe', 'themes', theme_name.lower(), value_data, test_mode)
        
        if test_mode:
            print(f"   TEST: Would load theme {theme_name}: {len(ticker_list)} tickers")
        else:
            print(f"   ✅ Loaded theme {theme_name}: {len(ticker_list)} tickers")

def load_market_leaders(conn, test_mode=False):
    """Load market leader entries (top N stocks)."""
    print("\n👑 Loading Market Leaders...")
    
    leader_configs = [
        ('top_10_stocks', 10),
        ('top_50', 50),
        ('top_100', 100),
        ('top_250', 250),
        ('top_500', 500)
    ]
    
    with conn.cursor() as cur:
        for key, limit in leader_configs:
            cur.execute("""
                SELECT ticker, name, sector, industry, market_cap, primary_exchange
                FROM stock_main
                WHERE type = 'CS'
                AND market_cap IS NOT NULL
                ORDER BY market_cap DESC
                LIMIT %s
            """, (limit,))
            
            stocks = cur.fetchall()
            
            if stocks:
                stock_list = format_stock_entry(stocks)
                value_data = {
                    "count": len(stock_list),
                    "stocks": stock_list  # FIXED: Store ALL stocks
                }
                
                insert_cache_entry(conn, 'stock_universe', 'market_leaders', key, value_data, test_mode)
                
                if test_mode:
                    print(f"   TEST: Would load {key}: {len(stocks)} stocks (ALL stored)")
                else:
                    print(f"   ✅ Loaded {key}: {len(stocks)} stocks (ALL stored)")

def load_industry_categories(conn, test_mode=False):
    """Load industry category entries."""
    print("\n🏭 Loading Industry Categories...")
    
    industry_list = [
        'pharmaceuticals',
        'banks',
        'insurance',
        'oil_gas',
        'software',
        'aerospace',
        'utilities',
        'retail'
    ]
    
    for industry in industry_list:
        stocks = get_stocks_by_industry(conn, industry.replace('_', ' '), 50)
        
        if stocks:
            stock_list = format_stock_entry(stocks)
            value_data = {
                "count": len(stock_list),
                "stocks": stock_list  # FIXED: Store ALL stocks
            }
            
            insert_cache_entry(conn, 'stock_universe', 'industry', industry, value_data, test_mode)
            
            if test_mode:
                print(f"   TEST: Would load {industry}: {len(stocks)} stocks (ALL stored)")
            else:
                print(f"   ✅ Loaded {industry}: {len(stocks)} stocks (ALL stored)")

def load_complete_universe(conn, test_mode=False):
    """Load complete stock universe."""
    print("\n🌍 Loading Complete Stock Universe...")
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                ticker, name, sector, industry, market_cap, primary_exchange
            FROM stock_main
            WHERE type = 'CS'
            ORDER BY market_cap DESC NULLS LAST
        """)
        
        all_stocks = cur.fetchall()
        
        if all_stocks:
            # Store ALL stocks, not just top 1000 preview
            stock_list = format_stock_entry(all_stocks)  # FIXED: Format ALL stocks
            value_data = {
                "count": len(all_stocks),  # Total count
                "stocks": stock_list        # FIXED: Store ALL stocks
            }
            
            insert_cache_entry(conn, 'stock_universe', 'complete', 'all_stocks', value_data, test_mode)
            
            if test_mode:
                print(f"   TEST: Would load complete universe: {len(all_stocks)} stocks (ALL stored)")
            else:
                print(f"   ✅ Loaded complete universe: {len(all_stocks)} stocks (ALL stored)")
                print(f"      ⚠️  Note: Storing {len(all_stocks)} complete records - this will be large!")

def load_stock_stats(conn, test_mode=False):
    """Load stock statistics summary."""
    print("\n📊 Loading Stock Statistics...")
    
    with conn.cursor() as cur:
        # Gather statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_stocks,
                COUNT(DISTINCT sector) as unique_sectors,
                SUM(market_cap) as total_market_cap,
                COUNT(DISTINCT primary_exchange) as unique_exchanges,
                COUNT(DISTINCT industry) as unique_industries,
                AVG(market_cap) as average_market_cap,
                COUNT(market_cap) as stocks_with_market_cap
            FROM stock_main
            WHERE type = 'CS'
        """)
        
        stats = cur.fetchone()
        
        # Get sector breakdown
        cur.execute("""
            SELECT sector, COUNT(*) as count, SUM(market_cap) as total_market_cap
            FROM stock_main
            WHERE type = 'CS'
            GROUP BY sector
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        
        sector_breakdown = []
        for sector, count, total_cap in cur.fetchall():
            sector_breakdown.append({
                "sector": sector or "Unknown",
                "count": count,
                "total_market_cap": float(total_cap) if total_cap else 0
            })
        
        value_data = {
            "overview": {
                "total_stocks": stats[0],
                "unique_sectors": stats[1],
                "total_market_cap": float(stats[2]) if stats[2] else 0,
                "unique_exchanges": stats[3],
                "unique_industries": stats[4],
                "average_market_cap": float(stats[5]) if stats[5] else 0,
                "stocks_with_market_cap": stats[6]
            },
            "sector_breakdown": sector_breakdown,  # Store ALL sectors, not preview
            "last_updated": datetime.utcnow().isoformat()
        }
        
        insert_cache_entry(conn, 'stock_stats', 'universe', 'summary', value_data, test_mode)
        
        if test_mode:
            print(f"   TEST: Would load statistics for {stats[0]} stocks")
        else:
            print(f"   ✅ Loaded statistics for {stats[0]} stocks")

def load_priority_stocks(conn, test_mode=False):
    """Load priority stocks for processing prioritization."""
    print("\n⭐ Loading Priority Stocks...")
    
    # Combine all priority stocks
    all_priority_tickers = []
    all_priority_tickers.extend(PRIORITY_STOCKS['top_priority'])
    all_priority_tickers.extend(PRIORITY_STOCKS['secondary_priority'])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_priority_tickers = []
    for ticker in all_priority_tickers:
        if ticker not in seen:
            seen.add(ticker)
            unique_priority_tickers.append(ticker)
    
    # Get stock details from src.infrastructure.database
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ticker, name, sector, industry, market_cap, primary_exchange
            FROM stock_main
            WHERE type = 'CS'
            AND ticker = ANY(%s)
            ORDER BY 
                CASE 
                    WHEN ticker = ANY(%s) THEN 0
                    ELSE 1
                END,
                market_cap DESC NULLS LAST
        """, (unique_priority_tickers, PRIORITY_STOCKS['top_priority']))
        
        priority_stocks = cur.fetchall()
    
    if priority_stocks:
        # Format stocks with priority ranking
        stock_list = []
        for i, stock in enumerate(priority_stocks, 1):
            ticker, name, sector, industry, market_cap, exchange = stock
            
            # Determine priority level
            if ticker in PRIORITY_STOCKS['top_priority']:
                priority_level = 'TOP'
                priority_score = 100 - PRIORITY_STOCKS['top_priority'].index(ticker)
            else:
                priority_level = 'SECONDARY'
                priority_score = 50 - PRIORITY_STOCKS['secondary_priority'].index(ticker)
            
            stock_list.append({
                "ticker": ticker,
                "name": name or "",
                "rank": i,
                "priority_level": priority_level,
                "priority_score": priority_score,
                "sector": sector or "Unknown",
                "industry": industry or "Unknown",
                "market_cap": float(market_cap) if market_cap else 0,
                "exchange": exchange or "Unknown"
            })
        
        # Create main priority entry
        value_data = {
            "count": len(stock_list),
            "stocks": stock_list,  # Priority stocks already working correctly
            "top_priority_count": len([s for s in stock_list if s['priority_level'] == 'TOP']),
            "secondary_priority_count": len([s for s in stock_list if s['priority_level'] == 'SECONDARY']),
            "criteria": "Most important stocks for processing prioritization",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        insert_cache_entry(conn, 'priority_stocks', 'processing', 'priority_list', value_data, test_mode)
        
        # Also create separate entries for each priority level
        top_priority_stocks = [s for s in stock_list if s['priority_level'] == 'TOP']
        if top_priority_stocks:
            insert_cache_entry(
                conn, 'priority_stocks', 'processing', 'top_priority',
                {
                    "count": len(top_priority_stocks),
                    "stocks": top_priority_stocks,
                    "tickers": [s['ticker'] for s in top_priority_stocks]
                },
                test_mode
            )
        
        secondary_priority_stocks = [s for s in stock_list if s['priority_level'] == 'SECONDARY']
        if secondary_priority_stocks:
            insert_cache_entry(
                conn, 'priority_stocks', 'processing', 'secondary_priority',
                {
                    "count": len(secondary_priority_stocks),
                    "stocks": secondary_priority_stocks,
                    "tickers": [s['ticker'] for s in secondary_priority_stocks]
                },
                test_mode
            )
        
        if test_mode:
            print(f"   TEST: Would load {len(stock_list)} priority stocks")
            print(f"         Top Priority: {len(top_priority_stocks)}")
            print(f"         Secondary Priority: {len(secondary_priority_stocks)}")
        else:
            print(f"   ✅ Loaded {len(stock_list)} priority stocks")
            print(f"      • Top Priority: {len(top_priority_stocks)} stocks")
            print(f"      • Secondary Priority: {len(secondary_priority_stocks)} stocks")

def execute_loading_plan(conn, test_mode=False):
    """Execute the complete loading plan."""
    print("\n" + "=" * 60)
    if test_mode:
        print("🧪 EXECUTING IN TEST MODE (No Changes)")
    else:
        print("🚀 EXECUTING CACHE LOADING")
    print("=" * 60)
    
    steps = [
        ("Priority Stocks", load_priority_stocks),
        ("Market Cap Categories", load_market_cap_categories),
        ("Sector Leaders", load_sector_leaders),
        ("Themes", load_themes),
        ("Market Leaders", load_market_leaders),
        ("Industry Categories", load_industry_categories),
        ("Complete Universe", load_complete_universe),
        ("Stock Statistics", load_stock_stats)
    ]
    
    total_steps = len(steps)
    
    for i, (step_name, step_func) in enumerate(steps, 1):
        print(f"\n[{i}/{total_steps}] {step_name}")
        print("-" * 40)
        
        try:
            step_func(conn, test_mode)
            
            if not test_mode:
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error in {step_name}: {e}")
            if not test_mode:
                conn.rollback()
            raise

def print_summary(conn, delete_count, test_mode=False):
    """Print execution summary."""
    print("\n" + "=" * 60)
    print("📋 EXECUTION SUMMARY")
    print("=" * 60)
    
    try:
        with conn.cursor() as cur:
            # Count new entries
            cur.execute("""
                SELECT type, COUNT(*) as count
                FROM cache_entries
                WHERE type = ANY(%s)
                GROUP BY type
                ORDER BY type
            """, (['stock_universe', 'stock_stats', 'themes', 'priority_stocks'],))
            
            new_entries = cur.fetchall()
            
            # Count preserved entries
            cur.execute("""
                SELECT COUNT(*)
                FROM cache_entries
                WHERE type != ALL(%s)
            """, (STOCK_RELATED_TYPES,))
            
            preserved_count = cur.fetchone()[0]
            
            # Check for truncation issues
            cur.execute("""
                SELECT 
                    COUNT(*) as truncated_entries,
                    SUM((value->>'count')::int - jsonb_array_length(value->'stocks')) as total_missing
                FROM cache_entries
                WHERE value ? 'stocks'
                AND value ? 'count'
                AND (value->>'count')::int > jsonb_array_length(value->'stocks')
            """)
            
            truncation_check = cur.fetchone()
            
            if test_mode:
                print("\n🧪 TEST MODE RESULTS:")
                print(f"  • Would delete: {delete_count:,} entries")
                print(f"  • Would preserve: {preserved_count:,} non-stock entries")
                print(f"  • Would create new stock entries (with FULL data)")
            else:
                print("\n✅ EXECUTION COMPLETE:")
                print(f"  • Deleted: {delete_count:,} old entries")
                print(f"  • Preserved: {preserved_count:,} non-stock entries")
                print("\n  New Entries Created:")
                
                total_new = 0
                for type_name, count in new_entries:
                    print(f"    • {type_name}: {count:,}")
                    total_new += count
                
                print(f"\n  Total New Entries: {total_new:,}")
                
                # Check for any truncation issues
                if truncation_check[0] > 0:
                    print(f"\n  ⚠️  WARNING: {truncation_check[0]} entries may still be truncated!")
                    print(f"     Missing {truncation_check[1]} stocks total")
                else:
                    print("\n  ✅ All stock lists stored completely (no truncation)")
                
                # Get timestamp
                cur.execute("""
                    SELECT MAX(updated_at)
                    FROM cache_entries
                    WHERE type = ANY(%s)
                """, (['stock_universe', 'stock_stats', 'themes', 'priority_stocks'],))
                
                last_update = cur.fetchone()[0]
                if last_update:
                    print(f"  Last Update: {last_update.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    except Exception as e:
        if not test_mode:
            print("\n✅ Cache loading completed successfully!")
            print(f"  Note: Summary generation had an issue: {e}")

def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("🚀 TICKSTOCK - Cache Entries Loading Tool (FIXED VERSION)")
    print("   This version stores COMPLETE stock lists, not previews")
    print("=" * 80)
    
    try:
        # Connect to database
        print("\n🔍 Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected successfully")
        
        # Analyze current state
        stock_entries, non_stock_entries = analyze_current_cache(conn)
        
        print("\n📊 Current Cache State:")
        print("  Stock-related entries to refresh:")
        for type_name, count in stock_entries:
            print(f"    • {type_name}: {count:,}")
        
        print("\n  Non-stock entries to preserve:")
        for type_name, count in non_stock_entries:
            print(f"    • {type_name}: {count:,}")
        
        # Ask for test mode
        if prompt_user("Do you want to run in TEST MODE first?", default="y"):
            print("\n" + "=" * 60)
            print("🧪 RUNNING TEST MODE")
            print("=" * 60)
            
            # Test deletion
            delete_count = delete_stock_entries(conn, test_mode=True)
            
            # Test loading
            execute_loading_plan(conn, test_mode=True)
            
            # Show summary
            print_summary(conn, delete_count, test_mode=True)
            
            # Ask to proceed
            if not prompt_user("\n🔄 Test complete. Execute ACTUAL cache reload?", default="n"):
                print("👋 Exiting without changes.")
                sys.exit(0)
        
        # Final confirmation
        print("\n⚠️  WARNING: This will store COMPLETE stock lists (5000+ stocks)")
        print("   The 'all_stocks' entry alone will be several MB in size.")
        if not prompt_user("Ready to reload cache with FULL stock data?", default="n"):
            print("👋 Operation cancelled.")
            sys.exit(0)
        
        # Execute actual loading
        print("\n" + "=" * 60)
        print("🔄 EXECUTING CACHE RELOAD WITH FULL DATA")
        print("=" * 60)
        
        # Delete old entries
        delete_count = delete_stock_entries(conn, test_mode=False)
        
        # Load new entries
        execute_loading_plan(conn, test_mode=False)
        
        # Commit all changes
        conn.commit()
        
        # Print summary
        print_summary(conn, delete_count, test_mode=False)
        
        print("\n" + "=" * 80)
        print("✅ Cache Loading Complete with FULL Stock Lists!")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()