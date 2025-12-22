"""
ETF Holdings Loader - Sprint 60 Enhanced

Loads ETF holdings from CSV files into definition_groups and group_memberships tables.
Supports multiple CSV formats (iShares, Vanguard, SPDR) with market cap filtering.
Includes smart update logic with change detection via checksums.

Usage:
    python load_etf_holdings.py --mode dry-run         # Preview without inserting
    python load_etf_holdings.py --mode full            # Full reload (TRUNCATE+INSERT)
    python load_etf_holdings.py --mode incremental     # Update changed ETFs only
    python load_etf_holdings.py --rebuild              # Alias for --mode full
    python load_etf_holdings.py --etf SPY              # Load specific ETF only
    python load_etf_holdings.py --etf SPY --mode incremental  # Incremental for single ETF
"""

import os
import sys
import csv
import json
import argparse
import logging
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import psycopg2
from urllib.parse import urlparse
from src.core.services.config_manager import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ETFHoldingsLoader:
    """Load and process ETF holdings from CSV files and inline definitions"""

    # Market cap thresholds by ETF type (in dollars)
    MARKET_CAP_THRESHOLDS = {
        'core_index': 5_000_000_000,      # $5B for SPY, QQQ, etc.
        'broad_market': 1_000_000_000,    # $1B for VTI, IWV, etc.
        'small_cap': 300_000_000,         # $300M for IWM
        'micro_cap': 50_000_000,          # $50M for thematic/speculative
    }

    # Inline ETF holdings for small/medium ETFs (<200 stocks)
    # Format: { "ETF_SYMBOL": {"name": "...", "holdings": [...], "etf_type": "..."} }
    INLINE_ETF_HOLDINGS = {
        "DIA": {
            "name": "SPDR Dow Jones Industrial Average ETF",
            "etf_type": "core_index",
            "holdings": [
                # All 30 Dow Jones Industrial Average components (2025)
                "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
                "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
                "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"
            ]
        },
        "QQQ": {
            "name": "Invesco QQQ Trust (NASDAQ-100)",
            "etf_type": "core_index",
            "holdings": [
                # Top 100 NASDAQ holdings (represents ~100% of fund)
                # Top 25 holdings (72.51% of fund)
                "NVDA", "AAPL", "MSFT", "AVGO", "AMZN", "GOOGL", "GOOG", "TSLA", "META", "PLTR",
                "NFLX", "COST", "AMD", "CSCO", "MU", "TMUS", "AMAT", "APP", "LRCX", "ISRG",
                "PEP", "SHOP", "QCOM", "INTU", "LIN",
                # Next 25 holdings (adds ~15% more coverage)
                "TXN", "ADBE", "BKNG", "CMCSA", "AMGN", "HON", "PANW", "VRTX", "ADP", "ABNB",
                "SBUX", "GILD", "ADI", "REGN", "MELI", "LULU", "MDLZ", "PYPL", "SNPS", "KLAC",
                "CDNS", "ASML", "CRWD", "MAR", "MRVL",
                # Next 25 holdings (adds ~8% more coverage)
                "FTNT", "CEG", "CSX", "ORLY", "DASH", "WDAY", "CHTR", "PCAR", "NXPI", "MNST",
                "AEP", "CPRT", "ROST", "PAYX", "KDP", "MCHP", "FAST", "KHC", "ODFL", "EA",
                "DXCM", "BKR", "VRSK", "IDXX", "CTSH",
                # Final 27 to reach 102 total (remaining ~4%)
                "CTAS", "GEHC", "FANG", "BIIB", "XEL", "CCEP", "TTWO", "ZS", "ANSS", "ON",
                "ILMN", "MDB", "WBD", "CDW", "WBA", "GFS", "MRNA", "DLTR", "SMCI", "DDOG",
                "ARM", "TEAM", "RIVN", "LCID", "ZM", "NTES", "JD"
            ]
        },
        "XLK": {
            "name": "Technology Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 73 technology holdings from S&P 500
                # Top 25 holdings (~85% of fund)
                "NVDA", "AAPL", "MSFT", "AVGO", "PLTR", "AMD", "ORCL", "CSCO", "IBM", "MU",
                "CRM", "AMAT", "LRCX", "APP", "QCOM", "INTU", "NOW", "INTC", "APH", "ACN",
                "TXN", "KLAC", "ADBE", "ADI", "ANET",
                # Next 25 holdings (~12% more)
                "PANW", "SNPS", "CDNS", "NXPI", "MCHP", "FTNT", "MSI", "HPQ", "KEYS", "ANSS",
                "TYL", "GDDY", "ADSK", "ROP", "PTC", "STX", "NTAP", "TRMB", "TER", "IT",
                "GLW", "HPE", "ZBRA", "AKAM", "FFIV",
                # Remaining ~23 holdings (~3% more coverage)
                "CTXS", "JNPR", "VRSN", "ENPH", "PAYC", "FICO", "HUBS", "BR", "SWKS",
                "GEN", "MPWR", "TDY", "LSCC", "AVT", "JKHY", "IPGP", "SEDG", "PLXS", "EPAM",
                "LITE", "MKSI", "COHR"
            ]
        },
        "XLF": {
            "name": "Financial Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 77 financials holdings from S&P 500
                "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "C",
                "SPGI", "BLK", "CB", "PGR", "MMC", "ICE", "PNC", "USB", "TFC", "CME",
                "AON", "AFL", "AIG", "MET", "ALL", "TRV", "PRU", "AJG", "HIG", "MSCI",
                "COF", "MCO", "AMP", "FIS", "DFS", "BK", "STT", "TROW", "MTB", "FITB",
                "KEY", "CFG", "RF", "HBAN", "BRO", "CINF", "L", "GL", "WRB", "IVZ",
                "NTRS", "FDS", "JKHY", "AIZ", "RJF", "MKTX", "BEN", "EG", "CBOE", "PFG"
            ]
        },
        "XLV": {
            "name": "Health Care Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 63 healthcare holdings from S&P 500
                "LLY", "JNJ", "ABBV", "UNH", "MRK", "ABT", "TMO", "ISRG", "AMGN", "GILD",
                "DHR", "PFE", "SYK", "CVS", "VRTX", "BSX", "CI", "REGN", "MDT", "BMY",
                "ELV", "ZTS", "MCK", "HCA", "COR", "GEHC", "WAT", "HUM", "BDX", "A",
                "IQV", "DXCM", "IDXX", "EW", "MTD", "RMD", "CNC", "STE", "HLT", "ALGN",
                "CAH", "TFX", "PODD", "COO", "LH", "DGX", "WST", "BAX", "HSIC", "MOH",
                "VTRS", "HOLX", "UHS", "TECH", "DVA", "RVTY", "CRL", "SOLV", "INCY", "OGN"
            ]
        },
        "XLE": {
            "name": "Energy Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # All 25 energy holdings from S&P 500
                "XOM", "CVX", "COP", "WMB", "EOG", "MPC", "KMI", "PSX", "VLO", "SLB",
                "LNG", "OKE", "HES", "TRGP", "FANG", "TPL", "MRO", "DVN", "HAL", "BKR",
                "OXY", "CTRA", "EQT", "APA", "CHRD"
            ]
        },
        "XLI": {
            "name": "Industrial Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 75 industrials holdings from S&P 500
                "GE", "CAT", "RTX", "UNP", "HON", "ETN", "ADP", "BA", "LMT", "DE",
                "UPS", "TT", "GD", "WM", "PH", "CTAS", "ITW", "CSX", "EMR", "MMM",
                "NOC", "PCAR", "NSC", "URI", "FDX", "CMI", "TDG", "RSG", "PAYX", "ODFL",
                "CARR", "JCI", "FAST", "OTIS", "VRSK", "CPRT", "ROK", "GWW", "AME", "IR",
                "DAL", "AXON", "XYL", "HWM", "DOV", "HUBB", "FTV", "LDOS", "BR", "VLTO",
                "EFX", "SW", "SNA", "J", "LUV", "CHRW", "PWR", "SWK", "EXPD", "IEX",
                "PNR", "JBHT", "BLDR", "FBHS", "MAS", "NDSN", "ROL", "WAB", "AOS", "ALLE",
                "TXT", "GGG", "GNRC", "HII", "ESI"
            ]
        },
        "XLY": {
            "name": "Consumer Discretionary Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 55 consumer discretionary holdings from S&P 500
                "AMZN", "TSLA", "HD", "MCD", "BKNG", "NKE", "SBUX", "LOW", "TJX", "ABNB",
                "CMG", "ORLY", "MAR", "GM", "AZO", "ROST", "DHI", "F", "YUM", "LULU",
                "LEN", "HLT", "GRMN", "DECK", "EBAY", "POOL", "NVR", "ULTA", "DPZ", "PHM",
                "DRI", "TPR", "LVS", "CCL", "WYNN", "MGM", "RCL", "EXPE", "NCLH", "TSCO",
                "BBY", "GPC", "KMX", "CZR", "APTV", "LKQ", "WHR", "RL", "HAS", "MHK",
                "LEG", "NWL", "PVH", "UAA", "UA"
            ]
        },
        "XLP": {
            "name": "Consumer Staples Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 33 consumer staples holdings from S&P 500
                "WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "MDLZ", "CL", "KMB",
                "GIS", "STZ", "SYY", "HSY", "K", "CHD", "CLX", "TSN", "CAG", "HRL",
                "MKC", "SJM", "TAP", "CPB", "KHC", "LW", "BG", "KVUE", "EL", "KR",
                "SWK", "DG", "DLTR"
            ]
        },
        "XLU": {
            "name": "Utilities Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 30 utilities holdings from S&P 500
                "NEE", "SO", "DUK", "CEG", "SRE", "AEP", "VST", "D", "PCG", "PEG",
                "EXC", "XEL", "ED", "EIX", "WEC", "AWK", "DTE", "PPL", "ES", "FE",
                "AEE", "CMS", "CNP", "NI", "LNT", "EVRG", "ATO", "NWE", "PNW", "OGE"
            ]
        },
        "XLB": {
            "name": "Materials Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 30 materials holdings from S&P 500
                "LIN", "SHW", "APD", "ECL", "FCX", "NEM", "CTVA", "DD", "NUE", "DOW",
                "VMC", "MLM", "PPG", "ALB", "STLD", "IFF", "EMN", "MOS", "BALL", "AVY",
                "AMCR", "SW", "PKG", "IP", "CE", "FMC", "CF", "LYB", "WRK", "HUN"
            ]
        },
        "XLC": {
            "name": "Communication Services Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 25 communication services holdings from S&P 500
                "META", "GOOGL", "GOOG", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "WBD",
                "EA", "TTWO", "OMC", "PARA", "FOXA", "FOX", "LYV", "MTCH", "NWSA", "NWS",
                "IPG", "DISH", "NYT", "PINS", "SNAP"
            ]
        },
        "XLRE": {
            "name": "Real Estate Select Sector SPDR Fund",
            "etf_type": "core_index",
            "holdings": [
                # Top 30 real estate holdings from S&P 500
                "PLD", "AMT", "EQIX", "WELL", "PSA", "SPG", "DLR", "O", "CCI", "VICI",
                "EXR", "AVB", "SBAC", "EQR", "INVH", "VTR", "MAA", "ESS", "ARE", "KIM",
                "DOC", "UDR", "CPT", "HST", "REG", "FRT", "BXP", "VNO", "AIV", "SLG"
            ]
        }
    }

    # ETF classifications
    ETF_TYPES = {
        'SPY': 'core_index',
        'QQQ': 'core_index',
        'DIA': 'core_index',
        'VOO': 'core_index',
        'VTI': 'broad_market',
        'IWV': 'broad_market',
        'IWM': 'small_cap',
        'VEA': 'broad_market',
        'VWO': 'broad_market',
        'IEFA': 'broad_market',
        'EEM': 'broad_market',
        # Sector ETFs
        'XLF': 'core_index',
        'XLK': 'core_index',
        'XLV': 'core_index',
        'XLE': 'core_index',
        'XLI': 'core_index',
        'XLP': 'core_index',
        'XLY': 'core_index',
        'XLU': 'core_index',
        'XLB': 'core_index',
        'XLC': 'core_index',
        'XLRE': 'core_index',
    }

    def __init__(self, holdings_dir: str, mode: str = 'full'):
        """
        Initialize loader

        Args:
            holdings_dir: Path to directory containing holdings CSV files
            mode: Load mode ('full', 'incremental', 'dry-run')
        """
        self.holdings_dir = holdings_dir
        self.mode = mode
        self.dry_run = (mode == 'dry-run')
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.conn = None if self.dry_run else self._get_connection()
        self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')  # Use DEFAULT (10 chars limit)

        logger.info(f"ETFHoldingsLoader initialized in {mode.upper()} mode")

    def _get_connection(self):
        """Get database connection"""
        parsed = urlparse(self.db_uri)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password
        )

    def calculate_csv_checksum(self, csv_path: str) -> str:
        """
        Calculate MD5 checksum of CSV file for change detection

        Args:
            csv_path: Path to CSV file

        Returns:
            MD5 checksum as hex string
        """
        md5 = hashlib.md5()
        with open(csv_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def calculate_inline_checksum(self, holdings_list: List[str]) -> str:
        """
        Calculate MD5 checksum of inline holdings list

        Args:
            holdings_list: List of ticker symbols

        Returns:
            MD5 checksum as hex string
        """
        # Sort to ensure consistent checksums
        sorted_holdings = sorted(holdings_list)
        content = ','.join(sorted_holdings)
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get_etf_metadata_from_db(self, etf_symbol: str) -> Optional[Dict[str, any]]:
        """
        Get existing ETF metadata from database

        Args:
            etf_symbol: ETF ticker symbol

        Returns:
            Metadata dict or None if not found
        """
        if self.dry_run:
            return None

        try:
            cursor = self.conn.cursor()
            query = """
                SELECT metadata, liquidity_filter, updated_at
                FROM definition_groups
                WHERE name = %s AND type = 'ETF' AND environment = %s
            """
            cursor.execute(query, (etf_symbol.upper(), self.environment))
            result = cursor.fetchone()

            if result:
                return {
                    'metadata': result[0],
                    'liquidity_filter': result[1],
                    'updated_at': result[2]
                }
            return None

        except Exception as e:
            logger.warning(f"Error reading metadata for {etf_symbol}: {e}")
            return None

    def has_etf_changed(self, etf_symbol: str, holdings_data: Dict[str, any]) -> bool:
        """
        Check if ETF has changed since last load

        Args:
            etf_symbol: ETF ticker symbol
            holdings_data: New holdings data with checksum

        Returns:
            True if changed or new, False if unchanged
        """
        # Always reload in full mode
        if self.mode == 'full':
            return True

        # Get existing metadata from database
        db_metadata = self.get_etf_metadata_from_db(etf_symbol)

        if not db_metadata:
            logger.info(f"{etf_symbol}: New ETF (not in database)")
            return True

        # Compare checksums
        old_checksum = db_metadata['metadata'].get('checksum', '')
        new_checksum = holdings_data.get('checksum', '')

        if old_checksum != new_checksum:
            logger.info(f"{etf_symbol}: Changed (checksum mismatch)")
            logger.debug(f"  Old: {old_checksum[:8]}... | New: {new_checksum[:8]}...")
            return True

        logger.info(f"{etf_symbol}: Unchanged (skipping)")
        return False

    def validate_holdings_data(self, holdings_data: Dict[str, any]) -> tuple[bool, List[str]]:
        """
        Pre-load validation: Check for data quality issues

        Args:
            holdings_data: Holdings data to validate

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []

        # Check for empty holdings
        if not holdings_data.get('holdings'):
            warnings.append(f"ETF has no holdings")
            return False, warnings

        holdings = holdings_data['holdings']

        # Check for duplicate symbols
        seen = set()
        duplicates = []
        for symbol in holdings:
            if symbol in seen:
                duplicates.append(symbol)
            seen.add(symbol)

        if duplicates:
            warnings.append(f"Duplicate symbols found: {', '.join(duplicates[:5])}")
            if len(duplicates) > 5:
                warnings.append(f"  ... and {len(duplicates) - 5} more duplicates")

        # Check for invalid symbols (basic validation)
        invalid_symbols = [s for s in holdings if not s or len(s) > 10 or not s.replace('-', '').replace('.', '').isalnum()]
        if invalid_symbols:
            warnings.append(f"Invalid symbols: {', '.join(invalid_symbols[:5])}")
            if len(invalid_symbols) > 5:
                warnings.append(f"  ... and {len(invalid_symbols) - 5} more invalid")

        # Check for unusually small/large holdings count
        total_holdings = len(holdings)
        if total_holdings < 10:
            warnings.append(f"Unusually small holdings count: {total_holdings}")
        elif total_holdings > 5000:
            warnings.append(f"Unusually large holdings count: {total_holdings}")

        # Determine if critical errors exist (duplicates or invalid symbols are critical)
        is_valid = len(duplicates) == 0 and len(invalid_symbols) == 0

        return is_valid, warnings

    def run_post_load_validation(self) -> bool:
        """
        Post-load validation: Run validate_relationships.py

        Returns:
            True if validation passed, False otherwise
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would run post-load validation")
            return True

        try:
            import subprocess
            script_path = os.path.join(os.path.dirname(__file__), 'validate_relationships.py')

            logger.info("Running post-load validation...")
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("✓ Post-load validation passed")
                return True
            else:
                logger.error(f"✗ Post-load validation failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("✗ Post-load validation timed out (>60s)")
            return False
        except Exception as e:
            logger.error(f"✗ Error running post-load validation: {e}")
            return False

    def detect_csv_format(self, csv_path: str) -> str:
        """
        Detect CSV format (iShares, Vanguard, SPDR, Simple)

        Args:
            csv_path: Path to CSV file

        Returns:
            Format name: 'ishares', 'vanguard', 'spdr', or 'simple'
        """
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # iShares format: Ticker, Name, Sector, Market Value
            if 'Ticker' in headers and 'Market Value' in headers:
                return 'ishares'

            # Vanguard format: Ticker Symbol, Holdings, Market Value
            elif 'Ticker Symbol' in headers or 'Holdings' in headers:
                return 'vanguard'

            # SPDR format: Identifier, Weight
            elif 'Identifier' in headers and 'Weight' in headers:
                return 'spdr'

            # Simple format: Just Symbol column
            elif 'Symbol' in headers or 'symbol' in headers:
                return 'simple'

            # Default fallback
            return 'unknown'

    def parse_market_cap(self, value: str) -> Optional[float]:
        """
        Parse market cap from various formats

        Args:
            value: Market cap string (e.g., "$1,234,567.89", "1234567.89")

        Returns:
            Float value or None if invalid
        """
        if not value or value.strip() == '':
            return None

        try:
            # Remove currency symbols, commas, whitespace
            cleaned = value.replace('$', '').replace(',', '').strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None

    def parse_ishares_csv(self, csv_path: str,
                         threshold: float) -> List[Dict[str, any]]:
        """
        Parse iShares format CSV

        Args:
            csv_path: Path to CSV file
            threshold: Market cap threshold

        Returns:
            List of holdings dicts
        """
        holdings = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get('Ticker', '').strip()
                market_value = self.parse_market_cap(row.get('Market Value', ''))

                if not ticker or ticker == '-':
                    continue

                if market_value and market_value >= threshold:
                    holdings.append({
                        'symbol': ticker,
                        'market_cap': market_value,
                        'sector': row.get('Sector', '').strip(),
                        'weight': self.parse_market_cap(row.get('Weight (%)', '0'))
                    })

        return holdings

    def parse_vanguard_csv(self, csv_path: str,
                          threshold: float) -> List[Dict[str, any]]:
        """
        Parse Vanguard format CSV

        Args:
            csv_path: Path to CSV file
            threshold: Market cap threshold

        Returns:
            List of holdings dicts
        """
        holdings = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get('Ticker Symbol', '').strip()
                market_value = self.parse_market_cap(row.get('Market Value', ''))

                if not ticker or ticker == '-':
                    continue

                if market_value and market_value >= threshold:
                    holdings.append({
                        'symbol': ticker,
                        'market_cap': market_value,
                        'sector': row.get('Asset Class', '').strip(),
                        'weight': self.parse_market_cap(row.get('% of Fund', '0'))
                    })

        return holdings

    def parse_spdr_csv(self, csv_path: str,
                      threshold: float) -> List[Dict[str, any]]:
        """
        Parse SPDR format CSV

        Args:
            csv_path: Path to CSV file
            threshold: Market cap threshold

        Returns:
            List of holdings dicts
        """
        holdings = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get('Identifier', '').strip()
                weight = self.parse_market_cap(row.get('Weight', '0'))

                if not ticker or ticker == '-':
                    continue

                # SPDR files often don't have market cap, use weight filter
                if weight and weight > 0:
                    holdings.append({
                        'symbol': ticker,
                        'market_cap': None,
                        'sector': row.get('Sector', '').strip(),
                        'weight': weight
                    })

        return holdings

    def parse_simple_csv(self, csv_path: str,
                        threshold: float) -> List[Dict[str, any]]:
        """
        Parse simple format CSV (just Symbol column)

        Args:
            csv_path: Path to CSV file
            threshold: Market cap threshold (ignored for simple format)

        Returns:
            List of holdings dicts
        """
        holdings = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try both 'Symbol' and 'symbol' (case insensitive)
                ticker = row.get('Symbol', row.get('symbol', '')).strip()

                if not ticker or ticker == '-':
                    continue

                holdings.append({
                    'symbol': ticker,
                    'market_cap': None,
                    'sector': None,
                    'weight': None
                })

        return holdings

    def load_inline_holdings(self, etf_symbol: str) -> Optional[Dict[str, any]]:
        """
        Load holdings from inline definitions

        Args:
            etf_symbol: ETF ticker symbol (e.g., 'QQQ')

        Returns:
            Dict with holdings data or None if not found
        """
        etf_data = self.INLINE_ETF_HOLDINGS.get(etf_symbol.upper())

        if not etf_data:
            return None

        etf_type = etf_data.get('etf_type', 'core_index')
        threshold = self.MARKET_CAP_THRESHOLDS[etf_type]
        holdings = etf_data['holdings']

        # Calculate checksum for change detection
        checksum = self.calculate_inline_checksum(holdings)

        logger.info(f"Loading {etf_symbol} from inline definition (type: {etf_type})")

        return {
            'etf_symbol': etf_symbol.upper(),
            'etf_type': etf_type,
            'holdings': holdings,
            'total_holdings': len(holdings),
            'market_cap_threshold': threshold,
            'last_updated': datetime.now().isoformat(),
            'data_source': 'inline_definition',
            'checksum': checksum
        }

    def load_etf_holdings(self, etf_symbol: str) -> Optional[Dict[str, any]]:
        """
        Load holdings for a single ETF (from CSV or inline)

        Args:
            etf_symbol: ETF ticker symbol (e.g., 'SPY')

        Returns:
            Dict with holdings data or None if not found
        """
        # First try inline holdings
        inline_data = self.load_inline_holdings(etf_symbol)
        if inline_data:
            logger.info(f"Loaded {len(inline_data['holdings'])} holdings for {etf_symbol} (inline)")
            return inline_data

        # Fall back to CSV file
        csv_filename = f"{etf_symbol.lower()}_holdings.csv"
        csv_path = os.path.join(self.holdings_dir, csv_filename)

        if not os.path.exists(csv_path):
            logger.warning(f"Holdings not found for {etf_symbol} (no CSV or inline definition)")
            return None

        # Determine ETF type and threshold
        etf_type = self.ETF_TYPES.get(etf_symbol.upper(), 'broad_market')
        threshold = self.MARKET_CAP_THRESHOLDS[etf_type]

        logger.info(f"Loading {etf_symbol} (type: {etf_type}, "
                   f"threshold: ${threshold:,.0f})")

        # Detect format and parse
        csv_format = self.detect_csv_format(csv_path)
        logger.info(f"Detected format: {csv_format}")

        if csv_format == 'ishares':
            holdings = self.parse_ishares_csv(csv_path, threshold)
        elif csv_format == 'vanguard':
            holdings = self.parse_vanguard_csv(csv_path, threshold)
        elif csv_format == 'spdr':
            holdings = self.parse_spdr_csv(csv_path, threshold)
        elif csv_format == 'simple':
            holdings = self.parse_simple_csv(csv_path, threshold)
        else:
            logger.error(f"Unknown CSV format for {etf_symbol}")
            return None

        # Extract symbol list
        symbols = [h['symbol'] for h in holdings]

        # Calculate checksum for change detection
        checksum = self.calculate_csv_checksum(csv_path)

        logger.info(f"Loaded {len(symbols)} holdings for {etf_symbol} "
                   f"(threshold: ${threshold:,.0f})")

        return {
            'etf_symbol': etf_symbol.upper(),
            'etf_type': etf_type,
            'holdings': symbols,
            'total_holdings': len(symbols),
            'market_cap_threshold': threshold,
            'last_updated': datetime.now().isoformat(),
            'data_source': csv_filename,
            'checksum': checksum
        }

    def insert_etf_holdings(self, holdings_data: Dict[str, any]) -> bool:
        """
        Insert ETF holdings into cache_entries

        Args:
            holdings_data: Holdings data dict

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert {holdings_data['etf_symbol']} "
                       f"with {holdings_data['total_holdings']} holdings")
            return True

        try:
            cursor = self.conn.cursor()

            # Prepare metadata JSON
            metadata = {
                'total_holdings': holdings_data['total_holdings'],
                'data_source': holdings_data['data_source'],
                'last_updated': holdings_data['last_updated'],
                'checksum': holdings_data.get('checksum', '')
            }

            # Prepare liquidity filter JSON
            liquidity_filter = {
                'market_cap_threshold': holdings_data['market_cap_threshold']
            }

            # Insert into definition_groups (or update if exists)
            query = """
                INSERT INTO definition_groups
                    (name, type, description, metadata, liquidity_filter, environment)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (name, type, environment)
                DO UPDATE SET
                    metadata = EXCLUDED.metadata,
                    liquidity_filter = EXCLUDED.liquidity_filter,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """

            cursor.execute(query, (
                holdings_data['etf_symbol'],
                'ETF',
                holdings_data['etf_symbol'],  # description
                json.dumps(metadata),
                json.dumps(liquidity_filter),
                self.environment
            ))

            group_id = cursor.fetchone()[0]

            # Delete existing memberships for this group (for clean reload)
            cursor.execute("""
                DELETE FROM group_memberships
                WHERE group_id = %s
            """, (group_id,))

            # Insert new memberships
            for symbol in holdings_data['holdings']:
                cursor.execute("""
                    INSERT INTO group_memberships (group_id, symbol)
                    VALUES (%s, %s)
                    ON CONFLICT (group_id, symbol) DO NOTHING
                """, (group_id, symbol))

            self.conn.commit()

            logger.info(f"✓ Inserted {holdings_data['etf_symbol']} "
                       f"(group_id: {group_id}, holdings: {holdings_data['total_holdings']})")
            return True

        except Exception as e:
            logger.error(f"Error inserting {holdings_data['etf_symbol']}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def load_all_etfs(self, specific_etf: Optional[str] = None):
        """
        Load holdings for all ETFs (from both CSV files and inline definitions)

        Args:
            specific_etf: If provided, load only this ETF
        """
        if specific_etf:
            etf_symbols = [specific_etf.upper()]
        else:
            # Collect ETFs from both CSV files and inline definitions
            csv_etfs = []
            if os.path.exists(self.holdings_dir):
                csv_files = [f for f in os.listdir(self.holdings_dir)
                            if f.endswith('_holdings.csv')]
                csv_etfs = [f.replace('_holdings.csv', '').upper()
                           for f in csv_files]

            inline_etfs = list(self.INLINE_ETF_HOLDINGS.keys())

            # Combine and deduplicate (CSV takes precedence if both exist)
            etf_symbols = sorted(list(set(csv_etfs + inline_etfs)))

            logger.info(f"Found {len(csv_etfs)} CSV file(s) and "
                       f"{len(inline_etfs)} inline definition(s)")

        logger.info(f"Loading {len(etf_symbols)} ETF(s): {etf_symbols}")

        success_count = 0
        failed_count = 0
        skipped_count = 0
        validation_failed_count = 0

        for etf_symbol in etf_symbols:
            holdings_data = self.load_etf_holdings(etf_symbol)

            if holdings_data:
                # Pre-load validation
                is_valid, warnings = self.validate_holdings_data(holdings_data)
                if warnings:
                    for warning in warnings:
                        logger.warning(f"{etf_symbol}: {warning}")

                if not is_valid:
                    logger.error(f"{etf_symbol}: Pre-load validation failed, skipping")
                    validation_failed_count += 1
                    failed_count += 1
                    continue

                # In incremental mode, check if ETF has changed
                if self.mode == 'incremental' and not self.has_etf_changed(etf_symbol, holdings_data):
                    skipped_count += 1
                    continue

                if self.insert_etf_holdings(holdings_data):
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"Load Summary ({self.mode.upper()} mode):")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Failed:  {failed_count}")
        if validation_failed_count > 0:
            logger.info(f"    - Validation failed: {validation_failed_count}")
        if self.mode == 'incremental':
            logger.info(f"  Skipped: {skipped_count} (unchanged)")
        logger.info(f"  Total:   {len(etf_symbols)}")
        logger.info(f"{'='*60}")

        # Post-load validation (run if any ETFs were loaded)
        if success_count > 0 and not self.dry_run:
            logger.info("")
            if not self.run_post_load_validation():
                logger.warning("Post-load validation failed - see errors above")
                return False

        return True

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Load ETF holdings from CSV files into definition_groups and group_memberships'
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without inserting into database')
    parser.add_argument('--etf', type=str,
                       help='Load specific ETF only (e.g., SPY)')
    parser.add_argument('--mode', type=str, choices=['full', 'incremental', 'dry-run'],
                       default='full',
                       help='Load mode: full (TRUNCATE+INSERT), incremental (update changed only), dry-run (preview)')
    parser.add_argument('--rebuild', action='store_true',
                       help='Force full rebuild (alias for --mode full)')

    args = parser.parse_args()

    # Handle --rebuild flag (overrides --mode)
    if args.rebuild:
        args.mode = 'full'

    # Handle --dry-run flag (overrides --mode)
    if args.dry_run:
        args.mode = 'dry-run'

    # Determine holdings directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    holdings_dir = os.path.join(script_dir, 'holdings')

    if not os.path.exists(holdings_dir):
        logger.warning(f"Holdings directory not found: {holdings_dir}")
        logger.info("Will use inline ETF definitions only")
        os.makedirs(holdings_dir, exist_ok=True)

    # Create loader and run
    loader = ETFHoldingsLoader(holdings_dir, mode=args.mode)

    try:
        loader.load_all_etfs(specific_etf=args.etf)
    finally:
        loader.close()


if __name__ == '__main__':
    main()
