"""
Cache Universe Organization Script

Organizes and rebuilds universe entries in cache_entries table.
Replaces the UI-based "Update and Organize Cache" button.

Usage:
    python scripts/cache_maintenance/organize_universes.py [options]

Options:
    --preserve    Preserve existing entries (append mode)
    --dry-run     Show what would be changed without making changes
    --verbose     Show detailed logging

Example:
    python scripts/cache_maintenance/organize_universes.py --preserve --verbose
"""

import argparse
import json
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch

# Add parent directory to path for imports
sys.path.insert(0, 'C:\\Users\\McDude\\TickStockAppV2')

from src.core.services.config_manager import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UniverseOrganizer:
    """Organize and maintain universe entries in cache_entries"""

    def __init__(self, dry_run: bool = False):
        """Initialize organizer with database connection"""
        self.dry_run = dry_run
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.stats = {
            'added': 0,
            'updated': 0,
            'deleted': 0,
            'errors': 0
        }

    def get_connection(self):
        """Get database connection"""
        from urllib.parse import urlparse
        parsed = urlparse(self.db_uri)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password
        )

    def load_symbols_from_csv(self, filename: str) -> List[str]:
        """Load symbols from a CSV file in the same directory as this script"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, filename)

        symbols = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    symbol = line.strip()
                    if symbol:  # Skip empty lines
                        symbols.append(symbol)
            logger.info(f"Loaded {len(symbols)} symbols from {filename}")
            return symbols
        except FileNotFoundError:
            logger.warning(f"CSV file not found: {filename} - using empty list")
            return []
        except Exception as e:
            logger.error(f"Error loading CSV file {filename}: {e}")
            return []

    def remove_legacy_types(self):
        """Remove legacy universe types (stock_etf_combo)"""
        logger.info("Removing legacy universe types...")

        conn = self.get_connection()
        try:
            if not self.dry_run:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM cache_entries
                        WHERE type = 'stock_etf_combo'
                    """)
                    deleted_count = cursor.rowcount
                    self.stats['deleted'] += deleted_count
                    logger.info(f"Deleted {deleted_count} legacy stock_etf_combo entries")
                conn.commit()
            else:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) FROM cache_entries
                        WHERE type = 'stock_etf_combo'
                    """)
                    count = cursor.fetchone()[0]
                    logger.info(f"[DRY RUN] Would delete {count} stock_etf_combo entries")
        except Exception as e:
            logger.error(f"Error removing legacy types: {e}")
            conn.rollback()
            self.stats['errors'] += 1
        finally:
            conn.close()

    def organize_etf_universes(self, preserve_existing: bool = False):
        """
        Organize ETF universe entries using standardized structure.

        Organization:
        - master_* : Master lists (all ETFs)
        - index_*  : Broad market indexes
        - sector_* : Sector-based groupings
        - theme_*  : Thematic groupings
        - equal_*  : Equal weighted groupings
        - industry_* : Industry-specific groupings
        """
        logger.info("Organizing ETF universes...")

        # Define universe structures with naming convention
        etf_universes = {
            # Master Lists
            'master_all_etfs': {
                'name': 'All ETFs',
                'description': 'Master list of all tracked ETFs',
                'symbols': ['SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'VEA', 'VWO', 'AGG', 'BND',
                           'XLF', 'XLK', 'XLV', 'XLE', 'XLI', 'XLP', 'XLY', 'XLU', 'XLB', 'XLC', 'XLRE',
                           'VUG', 'VTV', 'SCHG', 'SCHV', 'TLT', 'IEF', 'IEFA', 'EEM', 'IBIT', 'FBTC',
                           'RSP', 'QQQE', 'GSEW', 'EQAL', 'EQL', 'EUSA', 'SMH', 'SOXX', 'XBI', 'IBB',
                           'VNQ', 'ICLN', 'TAN', 'BOTZ', 'ROBO', 'IRBO', 'ARKQ', 'DRIV', 'UFO', 'AIQ',
                           'IGPT', 'CHAT', 'XAR', 'ITA', 'PPA']
            },

            # Index-based (Broad Market)
            'index_broad_market': {
                'name': 'Broad Market Index ETFs',
                'description': 'Major market index ETFs',
                'symbols': ['SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'MDY']
            },

            # Sector-based
            'sector_sector_etfs': {
                'name': 'Sector ETFs',
                'description': 'S&P Sector SPDR ETFs',
                'symbols': ['XLF', 'XLK', 'XLV', 'XLE', 'XLI', 'XLP', 'XLY', 'XLU', 'XLB', 'XLC', 'XLRE']
            },
            'sector_bonds': {
                'name': 'Fixed Income ETFs',
                'description': 'Bond and fixed income ETFs',
                'symbols': ['AGG', 'BND', 'TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'MUB']
            },
            'sector_international': {
                'name': 'International ETFs',
                'description': 'International and emerging market ETFs',
                'symbols': ['VEA', 'VWO', 'IEFA', 'EEM', 'EFA', 'IEMG']
            },

            # Equal Weighted
            'equal_weighted_market': {
                'name': 'Equal Weighted Market ETFs',
                'description': 'Popular equal weighted broad market ETFs',
                'symbols': ['RSP', 'QQQE', 'GSEW', 'EQAL', 'EQL', 'EUSA', 'EWMC', 'EWSC']
            },

            # Industry-based
            'industry_semiconductors': {
                'name': 'Semiconductor ETFs',
                'description': 'Semiconductor industry ETFs',
                'symbols': ['SMH', 'SOXX', 'PSI']
            },
            'industry_biotech': {
                'name': 'Biotech ETFs',
                'description': 'Biotechnology industry ETFs',
                'symbols': ['XBI', 'IBB', 'LABU']
            },
            'industry_reits': {
                'name': 'REIT ETFs',
                'description': 'Real estate investment trust ETFs',
                'symbols': ['VNQ', 'IYR', 'SCHH']
            },
            'industry_defense': {
                'name': 'Defense ETFs',
                'description': 'Aerospace and defense industry ETFs',
                'symbols': ['XAR', 'ITA', 'PPA']
            },

            # Theme-based
            'theme_growth_value': {
                'name': 'Growth & Value ETFs',
                'description': 'Growth and value style ETFs',
                'symbols': ['VUG', 'VTV', 'SCHG', 'SCHV', 'IWF', 'IWD', 'MTUM', 'QUAL', 'USMV']
            },
            'theme_crypto': {
                'name': 'Cryptocurrency ETFs',
                'description': 'Bitcoin and cryptocurrency ETFs',
                'symbols': ['IBIT', 'FBTC', 'GBTC', 'BITO']
            },
            'theme_robotics': {
                'name': 'Robotics ETFs',
                'description': 'Robotics and automation ETFs',
                'symbols': ['BOTZ', 'ROBO', 'IRBO']
            },
            'theme_drones': {
                'name': 'Drones & Autonomous ETFs',
                'description': 'Drones and autonomous vehicle ETFs',
                'symbols': ['ARKQ', 'DRIV', 'UFO', 'IFLY']
            },
            'theme_ai': {
                'name': 'Artificial Intelligence ETFs',
                'description': 'AI and machine learning ETFs',
                'symbols': ['AIQ', 'IGPT', 'CHAT', 'BOTZ', 'ROBO']
            },
            'theme_clean_energy': {
                'name': 'Clean Energy ETFs',
                'description': 'Renewable and clean energy ETFs',
                'symbols': ['ICLN', 'TAN', 'PBW', 'QCLN']
            }
        }

        conn = self.get_connection()

        try:
            if not preserve_existing:
                # Delete existing ETF universes
                if not self.dry_run:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            DELETE FROM cache_entries
                            WHERE type = 'etf_universe'
                        """)
                        deleted_count = cursor.rowcount
                        self.stats['deleted'] += deleted_count
                        logger.info(f"Deleted {deleted_count} existing ETF universe entries")

            # Insert/update universe entries
            for key, data in etf_universes.items():
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would upsert: etf_universe:{key} ({len(data['symbols'])} symbols)")
                    continue

                with conn.cursor() as cursor:
                    # Upsert entry
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (type, name, key, environment)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            updated_at = NOW()
                    """, (
                        'etf_universe',
                        data['name'],
                        key,
                        json.dumps(data['symbols']),
                        'DEFAULT'
                    ))

                    if cursor.rowcount > 0:
                        self.stats['added' if preserve_existing else 'updated'] += 1
                        logger.info(
                            f"[OK] Upserted etf_universe:{key} - {len(data['symbols'])} symbols"
                        )

            if not self.dry_run:
                conn.commit()
                logger.info("ETF universe organization complete")

        except Exception as e:
            logger.error(f"Error organizing ETF universes: {e}")
            conn.rollback()
            self.stats['errors'] += 1
        finally:
            conn.close()

    def organize_stock_universes(self, preserve_existing: bool = False):
        """
        Organize stock universe entries using standardized structure.

        Organization:
        - master_* : Master lists (all stocks)
        - index_*  : Major indexes (SP500, NASDAQ100, DOW30, Russell3000)
        - sector_* : Sector-based groupings
        - theme_*  : Thematic groupings
        """
        logger.info("Organizing stock universes...")

        # Define universe structures with naming convention
        stock_universes = {
            # Master Lists
            'master_all_stocks': {
                'name': 'All Stocks',
                'description': 'Master list of all tracked stocks with market cap over $1B',
                'symbols': []  # Populate with unique symbols from all below for thoroughness; left as placeholder for large list
            },

            # Index-based (loaded from CSV files)
            'index_sp500': {
                'name': 'S&P 500',
                'description': 'S&P 500 index components (market cap > $1B)',
                'symbols': self.load_symbols_from_csv('sp500.csv')
            },
            'index_nasdaq100': {
                'name': 'NASDAQ 100',
                'description': 'NASDAQ 100 index components (market cap > $1B)',
                'symbols': self.load_symbols_from_csv('nasdaq100.csv')
            },
            'index_dow30': {
                'name': 'Dow Jones 30',
                'description': 'Dow Jones Industrial Average components (market cap > $1B)',
                'symbols': self.load_symbols_from_csv('dow30.csv')
            },
            'index_russell3000': {
                'name': 'Russell 3000',
                'description': 'Russell 3000 index components (market cap > $1B, representative)',
                'symbols': self.load_symbols_from_csv('russell3000.csv')
            },

            # Sector-based (expanded with more stocks, all >$1B cap)
            'sector_technology': {
                'name': 'Technology Sector',
                'description': 'Major technology stocks (market cap > $1B)',
                'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'ORCL', 'CRM', 'ADBE', 'AMD', 'QCOM', 'ACN', 'IBM', 'CSCO', 'NOW', 'TXN', 'INTU', 'AMAT', 'MU', 'ADI', 'KLAC', 'LRCX', 'PANW', 'INTC', 'SNPS', 'CDNS', 'APH', 'ROP', 'ANET', 'MSI', 'ADS', 'TEL', 'MCHP', 'FSLR', 'ENPH', 'HPQ', 'GLW']
            },
            'sector_healthcare': {
                'name': 'Healthcare Sector',
                'description': 'Major healthcare stocks (market cap > $1B)',
                'symbols': ['UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY', 'ELV', 'SYK', 'MDT', 'BSX', 'REGN', 'VRTX', 'CI', 'HCA', 'GILD', 'ZTS', 'CVS', 'MCK', 'BDX', 'EW', 'DXCM', 'IDXX', 'IQV', 'HUM', 'CNC', 'RMD', 'MTD']
            },
            'sector_financials': {
                'name': 'Financial Sector',
                'description': 'Major financial stocks (market cap > $1B)',
                'symbols': ['JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'BLK', 'C', 'SPGI', 'AXP', 'BX', 'SCHW', 'MMC', 'CB', 'PGR', 'FI', 'TFC', 'USB', 'PNC', 'AON', 'CME', 'ICE', 'AIG', 'AJG', 'COF', 'TRV', 'MET', 'AFL', 'PRU', 'ALL']
            },
            'sector_energy': {
                'name': 'Energy Sector',
                'description': 'Major energy stocks (market cap > $1B)',
                'symbols': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'PSX', 'VLO', 'OXY', 'WMB', 'OKE', 'KMI', 'HAL', 'BKR', 'FANG', 'DVN', 'HES', 'TRGP', 'CTRA', 'APA']
            },
            'sector_consumer_staples': {
                'name': 'Consumer Staples Sector',
                'description': 'Major consumer staples stocks (market cap > $1B)',
                'symbols': ['PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MDLZ', 'CL', 'MO', 'TGT', 'KHC', 'STZ', 'GIS', 'SYY', 'KMB', 'KVUE', 'KDP', 'MNST', 'HSY', 'K']
            },
            'sector_consumer_discretionary': {
                'name': 'Consumer Discretionary Sector',
                'description': 'Major consumer discretionary stocks (market cap > $1B)',
                'symbols': ['AMZN', 'TSLA', 'HD', 'MCD', 'LOW', 'BKNG', 'TJX', 'SBUX', 'NKE', 'CMG', 'ORLY', 'MAR', 'AZO', 'GM', 'HLT', 'DHI', 'YUM', 'LULU', 'ROST', 'LEN']
            },
            'sector_utilities': {
                'name': 'Utilities Sector',
                'description': 'Major utilities stocks (market cap > $1B)',
                'symbols': ['NEE', 'SO', 'DUK', 'CEG', 'SRE', 'AEP', 'D', 'PCG', 'PEG', 'EXC', 'ED', 'XEL', 'EIX', 'WEC', 'AWK', 'DTE', 'ETR', 'ES', 'PPL', 'FE']
            },
            'sector_materials': {
                'name': 'Materials Sector',
                'description': 'Major materials stocks (market cap > $1B)',
                'symbols': ['LIN', 'SHW', 'APD', 'ECL', 'FCX', 'NEM', 'CTVA', 'DOW', 'NUE', 'MLM', 'VMC', 'PPG', 'LYB', 'STLD', 'IFF', 'BALL', 'AVY', 'PKG', 'IP', 'AMCR']
            },
            'sector_communication_services': {
                'name': 'Communication Services Sector',
                'description': 'Major communication services stocks (market cap > $1B)',
                'symbols': ['GOOGL', 'GOOG', 'META', 'NFLX', 'TMUS', 'VZ', 'DIS', 'CMCSA', 'T', 'TTWO', 'EA', 'OMC', 'IPG', 'LYV', 'WBD', 'MTCH', 'FOXA', 'FOX', 'PARA', 'NWSA']
            },
            'sector_real_estate': {
                'name': 'Real Estate Sector',
                'description': 'Major real estate stocks (market cap > $1B)',
                'symbols': ['PLD', 'AMT', 'EQIX', 'WELL', 'SPG', 'O', 'PSA', 'DLR', 'CCI', 'CSGP', 'EXR', 'VICI', 'AVB', 'CBRE', 'IRM', 'EQR', 'WY', 'VTR', 'INVH', 'ESS']
            },
            'sector_industrials': {
                'name': 'Industrials Sector',
                'description': 'Major industrials stocks (market cap > $1B)',
                'symbols': ['GE', 'CAT', 'RTX', 'UNP', 'UBER', 'HON', 'ETN', 'LMT', 'UPS', 'DE', 'BA', 'ADP', 'WM', 'TRI', 'TDG', 'CPRT', 'CSX', 'ITW', 'PH', 'TT']
            },

            # Theme-based
            'theme_dividend': {
                'name': 'Dividend Stocks',
                'description': 'High-quality dividend-paying stocks (market cap > $1B)',
                'symbols': ['AOS', 'ABT', 'ABBV', 'AFL', 'APD', 'ALB', 'AMCR', 'ADM', 'ATO', 'ADP', 'BDX', 'BRO', 'BF.B', 'CAH', 'CAT', 'CHRW', 'CVX', 'CB', 'CHD', 'CINF', 'CTAS', 'CLX', 'KO', 'CL', 'ED', 'DOV', 'ECL', 'EMR', 'ERIE', 'ES', 'ESS', 'EXPD', 'XOM', 'FDS', 'FAST', 'FRT', 'BEN', 'GD', 'GPC', 'HRL', 'ITW', 'IBM', 'SJM', 'JNJ', 'KVUE', 'KMB', 'LIN', 'LOW', 'MKC', 'MCD', 'MDT', 'NEE', 'NDSN', 'NUE', 'PNR', 'PEP', 'PPG', 'PG', 'O', 'ROP', 'SPGI', 'SHW', 'SWK', 'SYY', 'TROW', 'TGT', 'GWW', 'WMT', 'WST']
            },
            'theme_growth': {
                'name': 'Growth Stocks',
                'description': 'High-growth stocks (market cap > $1B)',
                'symbols': ['NVDA', 'AVGO', 'LLY', 'JPM', 'PLTR', 'CPRT', 'TYL', 'CMG', 'SAP', 'TSM', 'GOOGL', 'SCHW', 'SMCI', 'STUB', 'SHOP', 'UBER', 'NIU', 'FTCI']
            },
            'theme_value': {
                'name': 'Value Stocks',
                'description': 'Value-oriented stocks (market cap > $1B)',
                'symbols': ['CPB', 'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'BRK.B', 'TSLA', 'WMT', 'JPM', 'XOM', 'UNH', 'V', 'MA', 'PG', 'COST', 'JNJ', 'HD', 'MRK', 'ABBV']
            },
            'theme_crypto': {
                'name': 'Crypto Related Stocks',
                'description': 'Stocks related to cryptocurrency (market cap > $1B)',
                'symbols': ['COIN', 'MSTR', 'RIOT', 'MARA', 'NVDA', 'SQ', 'PYPL', 'CLSK', 'HUT', 'CIFR']
            },
            'theme_bitcoin_miners': {
                'name': 'Bitcoin Miners',
                'description': 'Bitcoin mining stocks (market cap > $1B)',
                'symbols': ['MARA', 'RIOT', 'CLSK', 'HUT', 'CIFR', 'IREN', 'CORZ', 'BITF', 'TERW']
            },
            'theme_robotics': {
                'name': 'Robotics Stocks',
                'description': 'Robotics and automation stocks (market cap > $1B)',
                'symbols': ['ABB', 'FANUC', 'KUKA', 'YASK', 'KEYENCE', 'TER', 'ISRG', 'NVDA', 'TSLA', 'PATH', 'EMR', 'TRMB', 'OMCL', 'LECO', 'KRKN', 'RR', 'ARBE', 'TMO', 'QCOM']
            },
            'theme_drones': {
                'name': 'Drone Stocks',
                'description': 'Drone and UAV stocks (market cap > $1B)',
                'symbols': ['RTX', 'AVAV', 'KTOS', 'ONDS', 'BA', 'NOC', 'LMT', 'DPRO', 'UMAC', 'RCAT', 'DRO', 'DRSHF', 'AIRO']
            }
        }

        conn = self.get_connection()

        try:
            if not preserve_existing:
                # Delete existing stock universes
                if not self.dry_run:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            DELETE FROM cache_entries
                            WHERE type = 'stock_universe'
                        """)
                        deleted_count = cursor.rowcount
                        self.stats['deleted'] += deleted_count
                        logger.info(f"Deleted {deleted_count} existing stock universe entries")

            # Insert/update universe entries (only non-empty ones)
            for key, data in stock_universes.items():
                if not data['symbols']:
                    logger.info(f"Skipping {key}: No symbols defined (placeholder)")
                    continue

                if self.dry_run:
                    logger.info(f"[DRY RUN] Would upsert: stock_universe:{key} ({len(data['symbols'])} symbols)")
                    continue

                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (type, name, key, environment)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            updated_at = NOW()
                    """, (
                        'stock_universe',
                        data['name'],
                        key,
                        json.dumps(data['symbols']),
                        'DEFAULT'
                    ))

                    if cursor.rowcount > 0:
                        self.stats['added' if preserve_existing else 'updated'] += 1
                        logger.info(
                            f"[OK] Upserted stock_universe:{key} - {len(data['symbols'])} symbols"
                        )

            if not self.dry_run:
                conn.commit()
                logger.info("Stock universe organization complete")

        except Exception as e:
            logger.error(f"Error organizing stock universes: {e}")
            conn.rollback()
            self.stats['errors'] += 1
        finally:
            conn.close()

    # NOTE: stock_etf_combo type REMOVED in Sprint 57
    # Use stock_universe and etf_universe types only
    # Combo universes can be created by combining queries from both types

    def organize_theme_definitions(self, preserve_existing: bool = False):
        """
        Organize custom theme definitions for Sprint 58 Phase 4.

        Creates theme_definition cache entries with rich metadata:
        - description
        - selection_criteria
        - related_themes
        - last_updated
        """
        logger.info("Organizing custom theme definitions...")

        # Define theme definitions with metadata
        theme_definitions = {
            'crypto_miners': {
                'name': 'Bitcoin & Cryptocurrency Miners',
                'description': 'Companies primarily engaged in cryptocurrency mining operations',
                'symbols': ['MARA', 'RIOT', 'CLSK', 'HUT', 'CIFR', 'IREN', 'CORZ', 'BITF', 'TERW'],
                'selection_criteria': 'Primary business: Bitcoin/crypto mining, Market cap > $500M',
                'related_themes': ['theme_crypto', 'theme_energy_intensive']
            },
            'robotics_automation': {
                'name': 'Robotics & Industrial Automation',
                'description': 'Companies focused on robotics, automation, and AI-driven manufacturing',
                'symbols': ['ABB', 'FANUC', 'KUKA', 'YASK', 'KEYENCE', 'TER', 'ISRG', 'PATH', 'EMR', 'TRMB', 'OMCL', 'LECO', 'KRKN', 'RR', 'ARBE', 'TMO', 'QCOM'],
                'selection_criteria': 'Core business: Robotics, automation, or AI manufacturing',
                'related_themes': ['theme_ai', 'theme_technology']
            },
            'drones_uav': {
                'name': 'Drones & Unmanned Aerial Vehicles',
                'description': 'Drone manufacturers and UAV technology companies',
                'symbols': ['RTX', 'AVAV', 'KTOS', 'ONDS', 'BA', 'NOC', 'LMT', 'DPRO', 'UMAC', 'RCAT', 'DRO', 'DRSHF', 'AIRO'],
                'selection_criteria': 'Significant drone/UAV revenue or R&D focus',
                'related_themes': ['theme_defense', 'theme_robotics']
            },
            'gold_miners': {
                'name': 'Gold Mining Companies',
                'description': 'Major gold mining and exploration companies',
                'symbols': ['NEM', 'GOLD', 'AEM', 'KGC', 'FNV', 'AU', 'WPM', 'RGLD', 'AGI', 'EGO', 'HL', 'PAAS'],
                'selection_criteria': 'Primary business: Gold mining or streaming, Market cap > $500M',
                'related_themes': ['sector_materials', 'theme_commodities']
            },
            'silver_miners': {
                'name': 'Silver Mining Companies',
                'description': 'Major silver mining and exploration companies',
                'symbols': ['PAAS', 'AG', 'HL', 'FSM', 'EXK', 'MAG', 'CDE', 'ASM', 'SILV'],
                'selection_criteria': 'Primary business: Silver mining, Market cap > $300M',
                'related_themes': ['sector_materials', 'theme_commodities']
            },
            'space_technology': {
                'name': 'Space Technology & Satellites',
                'description': 'Space exploration, satellite, and aerospace technology companies',
                'symbols': ['BA', 'LMT', 'NOC', 'RTX', 'RKLB', 'SPCE', 'ASTS', 'LUNR', 'IRDM', 'GSAT', 'VSAT'],
                'selection_criteria': 'Significant space/satellite technology revenue',
                'related_themes': ['theme_defense', 'sector_industrials']
            },
            'clean_energy': {
                'name': 'Clean & Renewable Energy',
                'description': 'Solar, wind, and renewable energy companies',
                'symbols': ['ENPH', 'SEDG', 'FSLR', 'RUN', 'NEE', 'AES', 'PLUG', 'BE', 'NOVA', 'SHLS', 'ARRY', 'CSIQ'],
                'selection_criteria': 'Primary business: Renewable energy generation or equipment',
                'related_themes': ['sector_utilities', 'theme_esg']
            },
            'battery_storage': {
                'name': 'Battery & Energy Storage',
                'description': 'Battery manufacturing and energy storage technology',
                'symbols': ['TSLA', 'ALB', 'SQM', 'LAC', 'LITM', 'MP', 'PCRFY', 'NOVT', 'QS', 'STEM', 'CHPT'],
                'selection_criteria': 'Core business: Battery tech or energy storage systems',
                'related_themes': ['theme_clean_energy', 'theme_electric_vehicles']
            },
            'ai_machine_learning': {
                'name': 'Artificial Intelligence & Machine Learning',
                'description': 'Pure-play AI and machine learning companies',
                'symbols': ['NVDA', 'AMD', 'PLTR', 'AI', 'SNOW', 'PATH', 'DDOG', 'NET', 'CRWD', 'FTNT', 'PANW', 'S', 'SOUN', 'BBAI'],
                'selection_criteria': 'AI/ML as core product or infrastructure',
                'related_themes': ['sector_technology', 'theme_semiconductors']
            },
            'quantum_computing': {
                'name': 'Quantum Computing',
                'description': 'Quantum computing research and development companies',
                'symbols': ['IBM', 'GOOGL', 'MSFT', 'IONQ', 'RGTI', 'QUBT', 'ARQQ'],
                'selection_criteria': 'Active quantum computing R&D or commercialization',
                'related_themes': ['theme_ai', 'sector_technology']
            },
            'genomics_biotech': {
                'name': 'Genomics & Biotechnology',
                'description': 'Gene editing, sequencing, and advanced biotechnology',
                'symbols': ['ILMN', 'TMO', 'CRSP', 'NTLA', 'BEAM', 'EDIT', 'TWST', 'PACB', 'SGMO', 'RXRX'],
                'selection_criteria': 'Focus on genomics, gene editing, or DNA sequencing',
                'related_themes': ['sector_healthcare', 'theme_biotech']
            },
            'cloud_computing': {
                'name': 'Cloud Computing & Infrastructure',
                'description': 'Cloud infrastructure and platform providers',
                'symbols': ['AMZN', 'MSFT', 'GOOGL', 'ORCL', 'CRM', 'SNOW', 'NET', 'DDOG', 'MDB', 'ESTC', 'DT', 'FSLY'],
                'selection_criteria': 'Cloud infrastructure or platform as core business',
                'related_themes': ['sector_technology', 'theme_saas']
            },
            'cybersecurity': {
                'name': 'Cybersecurity',
                'description': 'Cybersecurity software and services',
                'symbols': ['CRWD', 'PANW', 'FTNT', 'ZS', 'OKTA', 'S', 'CYBR', 'TENB', 'QLYS', 'VRNS', 'RBRK'],
                'selection_criteria': 'Primary business: Cybersecurity products or services',
                'related_themes': ['sector_technology', 'theme_enterprise_software']
            },
            'five_g_infrastructure': {
                'name': '5G Infrastructure',
                'description': '5G network equipment and infrastructure',
                'symbols': ['AMT', 'CCI', 'SBAC', 'QCOM', 'ANET', 'CSCO', 'NOK', 'ERIC', 'TMUS', 'MRVL'],
                'selection_criteria': '5G infrastructure revenue or telecom tower operations',
                'related_themes': ['sector_communication_services', 'theme_semiconductors']
            },
            'electric_vehicles': {
                'name': 'Electric Vehicles',
                'description': 'Electric vehicle manufacturers and suppliers',
                'symbols': ['TSLA', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'F', 'GM', 'STLA', 'APTV', 'ALV', 'LEA'],
                'selection_criteria': 'EV manufacturing or significant EV component supply',
                'related_themes': ['theme_battery_storage', 'sector_consumer_discretionary']
            },
            'autonomous_vehicles': {
                'name': 'Autonomous Vehicles',
                'description': 'Self-driving technology and autonomous systems',
                'symbols': ['TSLA', 'GOOGL', 'UBER', 'MBLY', 'LAZR', 'LIDR', 'OUST', 'VLDR', 'INVZ', 'AMBA'],
                'selection_criteria': 'Autonomous driving technology or sensor systems',
                'related_themes': ['theme_electric_vehicles', 'theme_ai']
            },
            'water_technology': {
                'name': 'Water Technology & Infrastructure',
                'description': 'Water treatment, purification, and infrastructure',
                'symbols': ['AWK', 'WMS', 'XYL', 'WTR', 'ERII', 'BMI', 'VMI', 'FELE', 'IEX'],
                'selection_criteria': 'Water infrastructure, treatment, or conservation',
                'related_themes': ['sector_utilities', 'sector_industrials']
            },
            'agriculture_technology': {
                'name': 'Agriculture Technology',
                'description': 'Precision agriculture and agtech companies',
                'symbols': ['DE', 'AGCO', 'CNHI', 'ANDE', 'SMG', 'FMC', 'NTR', 'MOS', 'CF', 'IPI'],
                'selection_criteria': 'Agricultural equipment or technology focus',
                'related_themes': ['sector_materials', 'sector_industrials']
            },
            'nuclear_energy': {
                'name': 'Nuclear Energy',
                'description': 'Nuclear power generation and uranium mining',
                'symbols': ['CEG', 'VST', 'NEE', 'DUK', 'D', 'CCJ', 'UEC', 'UUUU', 'NXE', 'DNN'],
                'selection_criteria': 'Nuclear power operations or uranium production',
                'related_themes': ['sector_utilities', 'sector_energy']
            },
            'rare_earth_minerals': {
                'name': 'Rare Earth & Critical Minerals',
                'description': 'Rare earth mining and critical mineral producers',
                'symbols': ['MP', 'LAC', 'ALB', 'SQM', 'VALE', 'FCX', 'SCCO', 'TECK', 'HBM', 'IVN'],
                'selection_criteria': 'Rare earth or critical mineral mining operations',
                'related_themes': ['sector_materials', 'theme_battery_storage']
            }
        }

        conn = self.get_connection()

        try:
            if not preserve_existing:
                # Delete existing theme definitions from definition_groups
                if not self.dry_run:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            DELETE FROM definition_groups
                            WHERE type = 'THEME'
                            AND environment = 'DEFAULT'
                        """)
                        deleted_count = cursor.rowcount
                        self.stats['deleted'] += deleted_count
                        logger.info(f"Deleted {deleted_count} existing theme definition entries")

            # Insert/update theme definition entries into definition_groups
            for key, data in theme_definitions.items():
                # Build metadata JSON (without symbols - those go in group_memberships)
                metadata = {
                    'selection_criteria': data['selection_criteria'],
                    'related_themes': data['related_themes'],
                    'last_updated': datetime.now().isoformat()
                }

                if self.dry_run:
                    logger.info(f"[DRY RUN] Would upsert: theme_definition:{key} ({len(data['symbols'])} symbols)")
                    continue

                with conn.cursor() as cursor:
                    # Insert/update definition_groups entry
                    cursor.execute("""
                        INSERT INTO definition_groups
                            (name, type, description, metadata, environment)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (name, type, environment)
                        DO UPDATE SET
                            description = EXCLUDED.description,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        key,                     # name (e.g., 'crypto_miners')
                        'THEME',                 # type
                        data['name'],            # description (e.g., 'Bitcoin & Cryptocurrency Miners')
                        json.dumps(metadata),    # metadata JSONB
                        'DEFAULT'                # environment
                    ))

                    group_id = cursor.fetchone()[0]

                    # Delete existing memberships for clean reload
                    cursor.execute("""
                        DELETE FROM group_memberships
                        WHERE group_id = %s
                    """, (group_id,))

                    # Insert symbols into group_memberships
                    for symbol in data['symbols']:
                        cursor.execute("""
                            INSERT INTO group_memberships (group_id, symbol)
                            VALUES (%s, %s)
                            ON CONFLICT (group_id, symbol) DO NOTHING
                        """, (group_id, symbol))

                    self.stats['added' if preserve_existing else 'updated'] += 1
                    logger.info(
                        f"[OK] Upserted theme_definition:{key} - {len(data['symbols'])} symbols"
                    )

            if not self.dry_run:
                conn.commit()
                logger.info("Theme definitions organization complete")

        except Exception as e:
            logger.error(f"Error organizing theme definitions: {e}")
            conn.rollback()
            self.stats['errors'] += 1
        finally:
            conn.close()

    def print_summary(self):
        """Print organization summary"""
        print("\n" + "="*60)
        print("CACHE ORGANIZATION SUMMARY")
        print("="*60)
        print(f"Added:   {self.stats['added']}")
        print(f"Updated: {self.stats['updated']}")
        print(f"Deleted: {self.stats['deleted']}")
        print(f"Errors:  {self.stats['errors']}")
        print("="*60)

        if self.dry_run:
            print("\n[DRY RUN MODE] No changes were made to the database")
        else:
            print("\n[SUCCESS] Cache organization complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Organize universe entries in cache_entries table'
    )
    parser.add_argument(
        '--preserve',
        action='store_true',
        help='Preserve existing entries (append mode)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("Cache Universe Organization Script")
    print("="*60)
    print(f"Mode: {'Preserve existing' if args.preserve else 'Replace all'}")
    print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    print("="*60)

    if not args.dry_run and not args.preserve:
        confirm = input("\nWARNING: This will DELETE and replace all ETF/stock universes. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return

    organizer = UniverseOrganizer(dry_run=args.dry_run)

    try:
        # Remove legacy types first (stock_etf_combo)
        organizer.remove_legacy_types()

        # Organize universes with new structure
        organizer.organize_etf_universes(preserve_existing=args.preserve)
        organizer.organize_stock_universes(preserve_existing=args.preserve)

        # Organize theme definitions (Sprint 58 Phase 4)
        organizer.organize_theme_definitions(preserve_existing=args.preserve)

        organizer.print_summary()

    except Exception as e:
        logger.error(f"Organization failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()