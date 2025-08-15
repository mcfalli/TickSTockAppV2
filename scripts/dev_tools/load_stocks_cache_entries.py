import psycopg2
import json
from datetime import datetime
import logging
from decimal import Decimal

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "tickstock",
    "user": "app_readwrite",
    "password": "1DfTGVBsECVtJa"
}

# Environment setting
ENVIRONMENT = "DEFAULT"  # Change to PROD, TEST, UAT as needed

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def decimal_default(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def clear_existing_cache_entries(conn, cache_type=None):
    """Clear existing cache entries, optionally filtered by type, but preserve app_settings."""
    try:
        with conn.cursor() as cur:
            if cache_type:
                cur.execute("""
                    DELETE FROM cache_entries 
                    WHERE type = %s AND environment = %s
                """, (cache_type, ENVIRONMENT))
                logger.info(f"Cleared existing cache entries for type: {cache_type}")
            else:
                # Clear all except app_settings to preserve critical app configuration
                cur.execute("""
                    DELETE FROM cache_entries 
                    WHERE environment = %s AND type != 'app_settings'
                """, (ENVIRONMENT,))
                logger.info("Cleared all existing cache entries (preserved app_settings)")
        conn.commit()
    except Exception as e:
        logger.error(f"Error clearing cache entries: {e}")
        conn.rollback()
        raise

def ensure_app_settings(conn):
    """Ensure required app settings exist in cache_entries."""
    logger.info("Ensuring app settings exist...")
    
    app_settings = [
        ('SECRET_KEY', '{"value": "<GENERATE_RANDOM_32_CHAR_HEX>"}'),
        ('MAX_LOGIN_ATTEMPTS', '{"value": 5}'),
        ('SESSION_DURATION', '{"value": 10}'),
        ('SESSION_EXPIRY_DAYS', '{"value": 1}'),
        ('LOCKOUT_DURATION_MINUTES', '{"value": 20}'),
        ('MAX_LOCKOUTS', '{"value": 3}'),
        ('MAIL_SERVER', '{"value": "127.0.0.1"}'),
        ('MAIL_PORT', '{"value": 1025}'),
        ('MAIL_USE_TLS', '{"value": false}'),
        ('MAIL_USE_SSL', '{"value": false}'),
        ('MAIL_DEFAULT_SENDER', '{"value": "noreply@tickstock.ai"}'),
        ('MAIL_TIMEOUT', '{"value": 10}'),
        ('SQLALCHEMY_TRACK_MODIFICATIONS', '{"value": false}'),
        ('SERVER_NAME', '{"value": "localhost:5000"}'),
        ('BASE_URL', '{"value": "http://localhost:5000"}'),
        ('REDIS_URL', '{"value": "redis://localhost:6379"}')
    ]
    
    try:
        with conn.cursor() as cur:
            for key, value_json in app_settings:
                cur.execute("""
                    INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) 
                    VALUES ('app_settings', 'app_settings', %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (type, name, key, environment) DO NOTHING
                """, (key, value_json, ENVIRONMENT))
        
        conn.commit()
        logger.info("App settings ensured in cache_entries")
    except Exception as e:
        logger.error(f"Error ensuring app settings: {e}")
        conn.rollback()
        raise

def insert_cache_entry(conn, cache_type, name, key, value_data):
    """Insert a single cache entry."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cache_entries (type, name, key, value, environment, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (type, name, key, environment) 
                DO UPDATE SET 
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
            """, (cache_type, name, key, json.dumps(value_data, default=decimal_default), ENVIRONMENT, datetime.utcnow()))
        conn.commit()
        logger.debug(f"Inserted cache entry: {cache_type}.{name}.{key}")
    except Exception as e:
        logger.error(f"Error inserting cache entry {cache_type}.{name}.{key}: {e}")
        conn.rollback()
        raise

def build_market_cap_universes(conn):
    """Build market cap-based stock universes."""
    logger.info("Building market cap universes...")
    
    market_cap_tiers = [
        ("MEGA_CAP", "mega_cap", "market_cap >= 200000000000"),
        ("LARGE_CAP", "large_cap", "market_cap >= 10000000000 AND market_cap < 200000000000"),
        ("MID_CAP", "mid_cap", "market_cap >= 2000000000 AND market_cap < 10000000000"),
        ("SMALL_CAP", "small_cap", "market_cap >= 300000000 AND market_cap < 2000000000"),
        ("MICRO_CAP", "micro_cap", "market_cap > 0 AND market_cap < 300000000")
    ]
    
    for tier_name, tier_key, where_clause in market_cap_tiers:
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT ticker, name, sector, industry, market_cap, primary_exchange
                    FROM stock_main 
                    WHERE enabled = true 
                      AND active = true 
                      AND {where_clause}
                      AND market_cap IS NOT NULL
                    ORDER BY market_cap DESC
                    LIMIT 500
                """)
                
                stocks = []
                for i, row in enumerate(cur.fetchall(), 1):
                    stocks.append({
                        "rank": i,
                        "ticker": row[0],
                        "name": row[1],
                        "sector": row[2],
                        "industry": row[3],
                        "market_cap": row[4],
                        "exchange": row[5]
                    })
                
                if stocks:
                    cache_data = {
                        "stocks": stocks,
                        "count": len(stocks),
                        "criteria": f"Market cap tier: {tier_name}",
                        "last_updated": datetime.utcnow().isoformat()
                    }
                    
                    insert_cache_entry(conn, "stock_universe", "market_cap", tier_key, cache_data)
                    logger.info(f"Built {tier_name} universe with {len(stocks)} stocks")
                
        except Exception as e:
            logger.error(f"Error building {tier_name} universe: {e}")

def build_sector_leaders(conn):
    """Build sector leader universes (top stocks by market cap per sector)."""
    logger.info("Building sector leader universes...")
    
    try:
        with conn.cursor() as cur:
            # Get all sectors
            cur.execute("""
                SELECT DISTINCT sector 
                FROM stock_main 
                WHERE enabled = true 
                  AND active = true 
                  AND sector != 'Unknown'
                  AND market_cap IS NOT NULL
                ORDER BY sector
            """)
            
            sectors = [row[0] for row in cur.fetchall()]
            
            for sector in sectors:
                # Get top 10 stocks by market cap in this sector
                cur.execute("""
                    SELECT ticker, name, sector, industry, market_cap, primary_exchange
                    FROM stock_main 
                    WHERE enabled = true 
                      AND active = true 
                      AND sector = %s
                      AND market_cap IS NOT NULL
                    ORDER BY market_cap DESC
                    LIMIT 10
                """, (sector,))
                
                stocks = []
                for i, row in enumerate(cur.fetchall(), 1):
                    stocks.append({
                        "rank": i,
                        "ticker": row[0],
                        "name": row[1],
                        "sector": row[2],
                        "industry": row[3],
                        "market_cap": row[4],
                        "exchange": row[5]
                    })
                
                if stocks:
                    cache_data = {
                        "stocks": stocks,
                        "count": len(stocks),
                        "criteria": f"Top 10 by market cap in {sector}",
                        "last_updated": datetime.utcnow().isoformat()
                    }
                    
                    sector_key = sector.lower().replace(" ", "_").replace("&", "and")
                    insert_cache_entry(conn, "stock_universe", "sector_leaders", f"top_10_{sector_key}", cache_data)
                    logger.info(f"Built top 10 {sector} universe with {len(stocks)} stocks")
                    
    except Exception as e:
        logger.error(f"Error building sector leaders: {e}")

def build_overall_leaders(conn):
    """Build overall market leader universes."""
    logger.info("Building overall market leader universes...")
    
    universes = [
        ("TOP_50", "top_50", 50, "Top 50 stocks by market cap"),
        ("TOP_100", "top_100", 100, "Top 100 stocks by market cap"), 
        ("TOP_250", "top_250", 250, "Top 250 stocks by market cap"),
        ("TOP_500", "top_500", 500, "Top 500 stocks by market cap")
    ]
    
    for universe_name, universe_key, limit, description in universes:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, name, sector, industry, market_cap, primary_exchange
                    FROM stock_main 
                    WHERE enabled = true 
                      AND active = true 
                      AND market_cap IS NOT NULL
                    ORDER BY market_cap DESC
                    LIMIT %s
                """, (limit,))
                
                stocks = []
                for i, row in enumerate(cur.fetchall(), 1):
                    stocks.append({
                        "rank": i,
                        "ticker": row[0],
                        "name": row[1],
                        "sector": row[2],
                        "industry": row[3],
                        "market_cap": row[4],
                        "exchange": row[5]
                    })
                
                if stocks:
                    cache_data = {
                        "stocks": stocks,
                        "count": len(stocks),
                        "criteria": description,
                        "last_updated": datetime.utcnow().isoformat()
                    }
                    
                    insert_cache_entry(conn, "stock_universe", "market_leaders", universe_key, cache_data)
                    logger.info(f"Built {universe_name} universe with {len(stocks)} stocks")
                    
        except Exception as e:
            logger.error(f"Error building {universe_name} universe: {e}")

def build_thematic_universes(conn):
    """Build thematic/trend-based stock universes."""
    logger.info("Building thematic universes...")
    
    # Define thematic stock lists
    themes = {
        "AI": {
            "tickers": ["NVDA", "AMD", "MSFT", "GOOGL", "SNOW", "PANW", "PLTR", "CRWD", "ZS", "AVGO", "ASML", "ADBE", "INTC", "C3AI"],
            "description": "Artificial Intelligence and Machine Learning leaders"
        },
        "Crypto": {
            "tickers": ["MSTR", "IBIT", "COIN", "RIOT", "MARA", "CLSK", "HUT", "BTDR", "GLXY", "CORZ", "HOOD", "SQ"],
            "description": "Cryptocurrency and Digital Asset companies"
        },
        "EV": {
            "tickers": ["TSLA", "LCID", "RIVN", "NIO", "LI", "XPEV", "BYD", "F", "GM", "CHPT", "EVGO"],
            "description": "Electric Vehicle manufacturers and infrastructure"
        },
        "Quantum": {
            "tickers": ["IBM", "GOOGL", "MSFT", "IONQ", "NVDA", "INTC", "RGTI", "QBTS", "FORM"],
            "description": "Quantum Computing technologies and research"
        },
        "Marijuana": {
            "tickers": ["TLRY", "CGC", "CRON", "SNDL", "ACB", "VFF", "GRWG", "HYFM", "MJ"],
            "description": "Cannabis and Marijuana industry companies"
        },
        "Semi": {
            "tickers": ["NVDA", "AMD", "QCOM", "TSM", "AVGO", "ASML", "LRCX", "AMAT", "INTC", "TXN", "MCHP", "MRVL"],
            "description": "Semiconductor manufacturers and equipment"
        },
        "Robotics": {
            "tickers": ["ISRG", "TER", "FANUC", "ABB", "NVDA", "TSLA", "SYM", "IRBT", "ZBRA", "ROK", "KSCP"],
            "description": "Robotics and Automation technologies"
        },
        "Cloud": {
            "tickers": ["AMZN", "MSFT", "GOOGL", "SNOW", "CRM", "ORCL", "ADBE", "NOW", "WDAY", "DDOG", "ZS", "AKAM"],
            "description": "Cloud Computing and Software-as-a-Service"
        },
        "Cybersecurity": {
            "tickers": ["CRWD", "PANW", "ZS", "OKTA", "FTNT", "S", "NET", "CYBR", "TENB", "QLYS"],
            "description": "Cybersecurity and Information Security"
        },
        "Fintech": {
            "tickers": ["SQ", "PYPL", "HOOD", "COIN", "AFRM", "SOFI", "UPST", "FI", "MELI", "NU"],
            "description": "Financial Technology and Digital Payments"
        },
        "Space": {
            "tickers": ["RKLB", "ASTS", "SPCE", "LMT", "NOC", "RTX", "BA", "PL"],
            "description": "Space Technology and Aerospace"
        },
        "Biotech": {
            "tickers": ["REGN", "VRTX", "AMGN", "GILD", "BIIB", "MRNA", "BMRN", "INCY", "NBIX", "SRPT"],
            "description": "Biotechnology and Pharmaceutical Research"
        }
    }
    
    for theme_name, theme_data in themes.items():
        try:
            with conn.cursor() as cur:
                # Get stock data for tickers in this theme
                placeholders = ','.join(['%s'] * len(theme_data["tickers"]))
                cur.execute(f"""
                    SELECT ticker, name, sector, industry, market_cap, primary_exchange
                    FROM stock_main 
                    WHERE enabled = true 
                      AND active = true 
                      AND ticker IN ({placeholders})
                    ORDER BY 
                        CASE WHEN market_cap IS NOT NULL THEN 0 ELSE 1 END,
                        market_cap DESC,
                        ticker ASC
                """, theme_data["tickers"])
                
                stocks = []
                found_tickers = set()
                for i, row in enumerate(cur.fetchall(), 1):
                    stocks.append({
                        "rank": i,
                        "ticker": row[0],
                        "name": row[1],
                        "sector": row[2],
                        "industry": row[3],
                        "market_cap": row[4],
                        "exchange": row[5]
                    })
                    found_tickers.add(row[0])
                
                # Track any missing tickers
                missing_tickers = set(theme_data["tickers"]) - found_tickers
                if missing_tickers:
                    logger.warning(f"Theme {theme_name}: Missing tickers {missing_tickers}")
                
                if stocks:
                    # Store as both detailed stock data and simple ticker list for compatibility
                    cache_data = {
                        "stocks": stocks,
                        "tickers": [stock["ticker"] for stock in stocks],
                        "count": len(stocks),
                        "criteria": theme_data["description"],
                        "missing_tickers": list(missing_tickers) if missing_tickers else [],
                        "last_updated": datetime.utcnow().isoformat()
                    }
                    
                    # Insert detailed data
                    insert_cache_entry(conn, "stock_universe", "themes", theme_name.lower(), cache_data)
                    
                    # Also insert simple ticker list for backward compatibility
                    simple_list = [stock["ticker"] for stock in stocks]
                    insert_cache_entry(conn, "themes", theme_name, "list", simple_list)
                    
                    logger.info(f"Built {theme_name} theme with {len(stocks)} stocks (missing: {len(missing_tickers)})")
                else:
                    logger.warning(f"No stocks found for theme {theme_name}")
                    
        except Exception as e:
            logger.error(f"Error building {theme_name} theme: {e}")
    """Build specific industry and thematic universes."""
    logger.info("Building industry-specific universes...")
    
    # FAANG+ (major tech giants)
    faang_tickers = ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'AMZN', 'NVDA', 'TSLA', 'NFLX']
    
    try:
        with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(faang_tickers))
            cur.execute(f"""
                SELECT ticker, name, sector, industry, market_cap, primary_exchange
                FROM stock_main 
                WHERE enabled = true 
                  AND active = true 
                  AND ticker IN ({placeholders})
                ORDER BY market_cap DESC
            """, faang_tickers)
            
            stocks = []
            for i, row in enumerate(cur.fetchall(), 1):
                stocks.append({
                    "rank": i,
                    "ticker": row[0],
                    "name": row[1],
                    "sector": row[2],
                    "industry": row[3],
                    "market_cap": row[4],
                    "exchange": row[5]
                })
            
            if stocks:
                cache_data = {
                    "stocks": stocks,
                    "count": len(stocks),
                    "criteria": "FAANG+ major technology companies",
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                insert_cache_entry(conn, "stock_universe", "thematic", "faang_plus", cache_data)
                logger.info(f"Built FAANG+ universe with {len(stocks)} stocks")
    
    except Exception as e:
        logger.error(f"Error building FAANG+ universe: {e}")
    
def build_industry_specific_universes(conn):
    """Build specific industry universes (non-thematic)."""
    logger.info("Building industry-specific universes...")
    
    # FAANG+ (major tech giants)
    faang_tickers = ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'AMZN', 'NVDA', 'TSLA', 'NFLX']
    
    try:
        with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(faang_tickers))
            cur.execute(f"""
                SELECT ticker, name, sector, industry, market_cap, primary_exchange
                FROM stock_main 
                WHERE enabled = true 
                  AND active = true 
                  AND ticker IN ({placeholders})
                ORDER BY market_cap DESC
            """, faang_tickers)
            
            stocks = []
            for i, row in enumerate(cur.fetchall(), 1):
                stocks.append({
                    "rank": i,
                    "ticker": row[0],
                    "name": row[1],
                    "sector": row[2],
                    "industry": row[3],
                    "market_cap": row[4],
                    "exchange": row[5]
                })
            
            if stocks:
                cache_data = {
                    "stocks": stocks,
                    "count": len(stocks),
                    "criteria": "FAANG+ major technology companies",
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                insert_cache_entry(conn, "UNIVERSE", "THEMATIC", "faang_plus", cache_data)
                logger.info(f"Built FAANG+ universe with {len(stocks)} stocks")
    
    except Exception as e:
        logger.error(f"Error building FAANG+ universe: {e}")
    
    # Industry-specific universes (broader than themes)
    industry_filters = [
        ("PHARMACEUTICALS", "pharmaceuticals", "industry ILIKE '%pharmaceutical%'"),
        ("BANKS", "banks", "industry ILIKE '%bank%'"),
        ("INSURANCE", "insurance", "industry ILIKE '%insurance%'"),
        ("OIL_GAS", "oil_gas", "sector = 'Energy' AND industry ILIKE '%oil%' OR industry ILIKE '%gas%'"),
        ("SOFTWARE", "software", "industry ILIKE '%software%'"),
        ("REITS", "reits", "industry ILIKE '%reit%'"),
        ("AEROSPACE", "aerospace", "industry ILIKE '%aircraft%' OR industry ILIKE '%aerospace%'"),
        ("UTILITIES", "utilities", "sector = 'Utilities'"),
        ("RETAIL", "retail", "industry ILIKE '%retail%' OR industry ILIKE '%store%'")
    ]
    
    for filter_name, filter_key, where_clause in industry_filters:
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT ticker, name, sector, industry, market_cap, primary_exchange
                    FROM stock_main 
                    WHERE enabled = true 
                      AND active = true 
                      AND ({where_clause})
                      AND market_cap IS NOT NULL
                    ORDER BY market_cap DESC
                    LIMIT 50
                """)
                
                stocks = []
                for i, row in enumerate(cur.fetchall(), 1):
                    stocks.append({
                        "rank": i,
                        "ticker": row[0],
                        "name": row[1],
                        "sector": row[2],
                        "industry": row[3],
                        "market_cap": row[4],
                        "exchange": row[5]
                    })
                
                if stocks:
                    cache_data = {
                        "stocks": stocks,
                        "count": len(stocks),
                        "criteria": f"Top {filter_name.replace('_', ' ').title()} stocks by market cap",
                        "last_updated": datetime.utcnow().isoformat()
                    }
                    
                    insert_cache_entry(conn, "stock_universe", "industry", filter_key, cache_data)
                    logger.info(f"Built {filter_name} universe with {len(stocks)} stocks")
                    
        except Exception as e:
            logger.error(f"Error building {filter_name} universe: {e}")

def build_complete_universe(conn):
    """Build the complete TickStock universe."""
    logger.info("Building complete TickStock universe...")
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ticker, name, sector, industry, market_cap, primary_exchange
                FROM stock_main 
                WHERE enabled = true 
                  AND active = true
                ORDER BY 
                    CASE WHEN market_cap IS NOT NULL THEN 0 ELSE 1 END,
                    market_cap DESC,
                    ticker ASC
            """)
            
            stocks = []
            for i, row in enumerate(cur.fetchall(), 1):
                stocks.append({
                    "rank": i,
                    "ticker": row[0],
                    "name": row[1],
                    "sector": row[2],
                    "industry": row[3],
                    "market_cap": row[4],
                    "exchange": row[5]
                })
            
            if stocks:
                cache_data = {
                    "stocks": stocks,
                    "count": len(stocks),
                    "criteria": "Complete TickStock universe of all active stocks",
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                insert_cache_entry(conn, "stock_universe", "complete", "all_stocks", cache_data)
                logger.info(f"Built complete universe with {len(stocks)} stocks")
                
    except Exception as e:
        logger.error(f"Error building complete universe: {e}")

def build_summary_stats(conn):
    """Build summary statistics cache entry."""
    logger.info("Building summary statistics...")
    
    try:
        with conn.cursor() as cur:
            # Overall stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_stocks,
                    COUNT(CASE WHEN market_cap IS NOT NULL THEN 1 END) as stocks_with_market_cap,
                    SUM(market_cap) as total_market_cap,
                    AVG(market_cap) as avg_market_cap,
                    COUNT(DISTINCT sector) as unique_sectors,
                    COUNT(DISTINCT industry) as unique_industries,
                    COUNT(DISTINCT primary_exchange) as unique_exchanges
                FROM stock_main 
                WHERE enabled = true AND active = true
            """)
            
            stats = cur.fetchone()
            
            # Sector breakdown
            cur.execute("""
                SELECT sector, COUNT(*) as count, 
                       COALESCE(SUM(market_cap), 0) as total_market_cap
                FROM stock_main 
                WHERE enabled = true AND active = true
                GROUP BY sector 
                ORDER BY count DESC
            """)
            
            sector_breakdown = []
            for row in cur.fetchall():
                sector_breakdown.append({
                    "sector": row[0],
                    "count": row[1],
                    "total_market_cap": row[2]
                })
            
            # Exchange breakdown
            cur.execute("""
                SELECT primary_exchange, COUNT(*) as count
                FROM stock_main 
                WHERE enabled = true AND active = true
                GROUP BY primary_exchange 
                ORDER BY count DESC
            """)
            
            exchange_breakdown = []
            for row in cur.fetchall():
                exchange_breakdown.append({
                    "exchange": row[0],
                    "count": row[1]
                })
            
            summary_data = {
                "overview": {
                    "total_stocks": stats[0],
                    "stocks_with_market_cap": stats[1],
                    "total_market_cap": stats[2],
                    "average_market_cap": stats[3],
                    "unique_sectors": stats[4],
                    "unique_industries": stats[5],
                    "unique_exchanges": stats[6]
                },
                "sector_breakdown": sector_breakdown,
                "exchange_breakdown": exchange_breakdown,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            insert_cache_entry(conn, "stock_stats", "universe", "summary", summary_data)
            logger.info("Built summary statistics")
            
    except Exception as e:
        logger.error(f"Error building summary statistics: {e}")

def main():
    """Main function to build all stock universe cache entries."""
    conn = None
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Connected to PostgreSQL database.")
        
        # Ensure app settings exist first
        ensure_app_settings(conn)
        
        # Clear existing cache entries (but preserve app_settings)
        clear_existing_cache_entries(conn)
        
        # Build all universes
        build_market_cap_universes(conn)
        build_sector_leaders(conn)
        build_overall_leaders(conn)
        build_thematic_universes(conn)
        build_industry_specific_universes(conn)
        build_complete_universe(conn)
        build_summary_stats(conn)
        
        logger.info("Successfully built all stock universe cache entries!")
        
        # Display summary
        with conn.cursor() as cur:
            cur.execute("""
                SELECT type, name, key, 
                       (value->>'count')::int as stock_count
                FROM cache_entries 
                WHERE environment = %s 
                  AND type IN ('stock_universe', 'stock_stats')
                ORDER BY type, name, key
            """, (ENVIRONMENT,))
            
            logger.info("\n=== Cache Entries Summary ===")
            for row in cur.fetchall():
                logger.info(f"{row[0]}.{row[1]}.{row[2]}: {row[3]} stocks")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")

if __name__ == "__main__":
    main()