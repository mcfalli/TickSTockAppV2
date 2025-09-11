"""
Historical Data Loader for TickStock.ai
Loads historical OHLCV data from Polygon.io API into TimescaleDB.

This module provides selective data loading with:
- Batch processing by date ranges
- Rate limiting and API quota management  
- Symbol-by-symbol loading with progress tracking
- Data validation and duplicate handling
- Flexible timeframe support (daily, 1min, etc.)

Usage:
    python -m src.data.historical_loader --symbols AAPL,MSFT,NVDA --years 1 --timespan day
"""

import os
import sys

# Load environment variables from .env file first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not available, continue without it

# Import other standard libraries
import time
import argparse
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

# Import third-party libraries
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PolygonHistoricalLoader:
    """Loads historical market data from Polygon.io API"""
    
    def __init__(self, api_key: str = None, database_uri: str = None):
        """
        Initialize historical data loader.
        
        Args:
            api_key: Polygon.io API key (defaults to env POLYGON_API_KEY)
            database_uri: Database connection string (defaults to env DATABASE_URI)
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        self.database_uri = database_uri or os.getenv('DATABASE_URI')
        
        # API key only required for data fetching, not for summary/database operations
        if not self.database_uri:
            raise ValueError("DATABASE_URI environment variable or database_uri parameter required")
            
        self.base_url = "https://api.polygon.io"
        self.rate_limit_delay = 12  # 5 calls per minute = 12 sec between calls
        self.session = requests.Session()
        self.batch_size = 1000  # Records per database insert
        
        # Connection will be established per operation
        self.conn = None
        
        if self.api_key:
            logger.info(f"HISTORICAL-LOADER: Initialized with API key: {'***' + self.api_key[-4:]}")
        else:
            logger.info("HISTORICAL-LOADER: Initialized without API key (database operations only)")
        
    def _connect_db(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(self.database_uri)
            logger.info("HISTORICAL-LOADER: Database connected")
            
    def _close_db(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("HISTORICAL-LOADER: Database connection closed")
            
    def _make_api_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make rate-limited API request to Polygon.io.
        
        Args:
            endpoint: API endpoint (e.g., '/v2/aggs/ticker/AAPL/range/1/day/2023-01-01/2024-01-01')
            params: Additional query parameters
            
        Returns:
            JSON response as dictionary
        """
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY required for API requests")
            
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apikey'] = self.api_key
        
        try:
            logger.debug(f"HISTORICAL-LOADER: API request: {endpoint}")
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("HISTORICAL-LOADER: Rate limited, waiting 60 seconds...")
                time.sleep(60)
                response = self.session.get(url, params=params, timeout=30)
            
            response.raise_for_status()
            data = response.json()
            
            # Respect rate limits proactively
            time.sleep(self.rate_limit_delay)
            
            return data
            
        except requests.exceptions.RequestException as e:
            # Check if this is an expected 404 for ETF financials
            if "404" in str(e) and "/financials" in url:
                logger.debug(f"HISTORICAL-LOADER: ETF financials endpoint returned 404 (expected)")
            else:
                logger.error(f"HISTORICAL-LOADER: API request failed: {e}")
            raise
            
    def fetch_symbol_metadata(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch symbol metadata from Polygon.io tickers endpoint.
        
        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            
        Returns:
            Dictionary with symbol metadata or None if not found
        """
        endpoint = f"/v3/reference/tickers/{symbol}"
        
        try:
            response = self._make_api_request(endpoint)
            
            if response.get('status') == 'OK' and response.get('results'):
                ticker_data = response['results']
                
                # Map API response to our schema
                metadata = {
                    'symbol': ticker_data.get('ticker', symbol),
                    'name': ticker_data.get('name', ''),
                    'market': ticker_data.get('market', 'stocks'),
                    'locale': ticker_data.get('locale', 'us'),
                    'currency_name': ticker_data.get('currency_name', 'USD'),
                    'currency_symbol': ticker_data.get('currency_symbol', '$'),
                    'type': ticker_data.get('type', 'CS'),
                    'active': ticker_data.get('active', True),
                    'cik': ticker_data.get('cik'),
                    'composite_figi': ticker_data.get('composite_figi'),
                    'share_class_figi': ticker_data.get('share_class_figi'),
                    'market_cap': ticker_data.get('market_cap'),
                    'weighted_shares_outstanding': ticker_data.get('weighted_shares_outstanding'),
                    'exchange': ticker_data.get('primary_exchange', ''),
                    'last_updated_utc': ticker_data.get('last_updated_utc'),
                    'sic_code': ticker_data.get('sic_code'),
                    'sic_description': ticker_data.get('sic_description'),
                    'total_employees': ticker_data.get('total_employees'),
                    'list_date': ticker_data.get('list_date')
                }
                
                # If this is an ETF, extract ETF-specific metadata
                if ticker_data.get('type') == 'ETF' or self._is_etf_symbol(symbol):
                    logger.info(f"HISTORICAL-LOADER: Detected ETF {symbol}, extracting ETF metadata...")
                    etf_metadata = self._extract_etf_metadata(ticker_data)
                    metadata.update(etf_metadata)
                    
                    # Try to fetch additional ETF details
                    try:
                        etf_details = self.fetch_etf_details(symbol)
                        if etf_details:
                            # Only update with non-None values from ETF details
                            for key, value in etf_details.items():
                                if value is not None:
                                    metadata[key] = value
                    except Exception as e:
                        # ETF financials are often unavailable - this is expected
                        if "404" in str(e) or "Not Found" in str(e):
                            logger.debug(f"HISTORICAL-LOADER: ETF financials not available for {symbol} (expected)")
                        else:
                            logger.warning(f"HISTORICAL-LOADER: Could not fetch additional ETF details for {symbol}: {e}")
                
                logger.debug(f"HISTORICAL-LOADER: Fetched metadata for {symbol}: {metadata['name']}")
                return metadata
            else:
                logger.warning(f"HISTORICAL-LOADER: No metadata found for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to fetch metadata for {symbol}: {e}")
            return None
    
    def _extract_etf_metadata(self, ticker_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract ETF-specific metadata from Polygon.io response.
        
        Args:
            ticker_data: Raw ticker data from Polygon.io API
            
        Returns:
            Dictionary with ETF-specific fields
        """
        etf_fields = {
            'etf_type': ticker_data.get('type', 'ETF'),
            'fmv_supported': True,  # Enable FMV for all ETFs
            'primary_exchange': ticker_data.get('primary_exchange', ''),
            'inception_date': ticker_data.get('list_date'),  # ETF inception date
            'dividend_frequency': 'quarterly',  # Default assumption
            'creation_unit_size': 50000,  # Default ETF creation unit
            'expense_ratio': None,  # Will be populated if available
            'aum_millions': None  # Will be calculated from market_cap if available
        }
        
        # Map common ETF issuers from name patterns
        name = ticker_data.get('name', '').upper()
        if 'SPDR' in name or 'STATE STREET' in name:
            etf_fields['issuer'] = 'State Street'
        elif 'ISHARES' in name or 'BLACKROCK' in name:
            etf_fields['issuer'] = 'BlackRock'
        elif 'VANGUARD' in name:
            etf_fields['issuer'] = 'Vanguard'
        elif 'INVESCO' in name:
            etf_fields['issuer'] = 'Invesco'
        elif 'FIDELITY' in name:
            etf_fields['issuer'] = 'Fidelity'
        else:
            etf_fields['issuer'] = 'Other'
        
        # Determine correlation reference based on common patterns
        symbol = ticker_data.get('ticker', '')
        name_upper = name.upper()
        
        # Broad Market ETFs
        if symbol in ['SPY', 'VOO', 'IVV'] or 'S&P 500' in name_upper:
            etf_fields['correlation_reference'] = 'SPY'
            etf_fields['underlying_index'] = 'S&P 500'
        elif symbol in ['QQQ', 'TQQQ'] or 'NASDAQ' in name_upper:
            etf_fields['correlation_reference'] = 'QQQ'
            etf_fields['underlying_index'] = 'NASDAQ-100'
        elif symbol in ['IWM', 'IWN', 'IWO'] or 'RUSSELL 2000' in name_upper:
            etf_fields['correlation_reference'] = 'IWM'
            etf_fields['underlying_index'] = 'Russell 2000'
        elif symbol in ['VTI', 'ITOT'] or 'TOTAL STOCK' in name_upper:
            etf_fields['correlation_reference'] = 'VTI'
            etf_fields['underlying_index'] = 'CRSP US Total Market'
        # Style ETFs
        elif symbol in ['VUG', 'IVW', 'SCHG'] or 'GROWTH' in name_upper:
            etf_fields['correlation_reference'] = 'VUG'
            etf_fields['underlying_index'] = 'Growth Index'
        elif symbol in ['VTV', 'IVE', 'SCHV'] or 'VALUE' in name_upper:
            etf_fields['correlation_reference'] = 'VTV'
            etf_fields['underlying_index'] = 'Value Index'
        # Technology ETFs
        elif symbol in ['VGT', 'XLK', 'FTEC'] or 'TECHNOLOGY' in name_upper:
            etf_fields['correlation_reference'] = 'VGT'
            etf_fields['underlying_index'] = 'Technology Sector'
        # Sector ETFs
        elif symbol == 'XLF' or 'FINANCIAL' in name_upper:
            etf_fields['correlation_reference'] = 'XLF'
            etf_fields['underlying_index'] = 'Financial Sector'
        elif symbol == 'XLV' or 'HEALTH' in name_upper:
            etf_fields['correlation_reference'] = 'XLV'
            etf_fields['underlying_index'] = 'Healthcare Sector'
        elif symbol == 'XLE' or 'ENERGY' in name_upper:
            etf_fields['correlation_reference'] = 'XLE'
            etf_fields['underlying_index'] = 'Energy Sector'
        elif symbol in ['XLI'] or 'INDUSTRIAL' in name_upper:
            etf_fields['correlation_reference'] = 'XLI'
            etf_fields['underlying_index'] = 'Industrial Sector'
        elif symbol in ['XLP'] or 'CONSUMER STAPLES' in name_upper:
            etf_fields['correlation_reference'] = 'XLP'
            etf_fields['underlying_index'] = 'Consumer Staples Sector'
        elif symbol in ['XLY'] or 'CONSUMER DISCRETIONARY' in name_upper:
            etf_fields['correlation_reference'] = 'XLY'
            etf_fields['underlying_index'] = 'Consumer Discretionary Sector'
        # Bond ETFs
        elif symbol in ['AGG', 'BND'] or 'BOND' in name_upper or 'AGGREGATE' in name_upper:
            etf_fields['correlation_reference'] = 'AGG'
            etf_fields['underlying_index'] = 'Bond Aggregate'
        # International ETFs
        elif symbol in ['VEA', 'IEFA'] or 'EAFE' in name_upper or 'DEVELOPED' in name_upper:
            etf_fields['correlation_reference'] = 'VEA'
            etf_fields['underlying_index'] = 'EAFE Index'
        elif symbol in ['EEM', 'VWO'] or 'EMERGING' in name_upper:
            etf_fields['correlation_reference'] = 'EEM'
            etf_fields['underlying_index'] = 'Emerging Markets'
        # Factor ETFs
        elif symbol == 'MTUM' or 'MOMENTUM' in name_upper:
            etf_fields['correlation_reference'] = 'MTUM'
            etf_fields['underlying_index'] = 'Momentum Factor'
        elif symbol == 'QUAL' or 'QUALITY' in name_upper:
            etf_fields['correlation_reference'] = 'QUAL'
            etf_fields['underlying_index'] = 'Quality Factor'
        elif symbol == 'USMV' or 'MIN VOL' in name_upper or 'LOW VOL' in name_upper:
            etf_fields['correlation_reference'] = 'USMV'
            etf_fields['underlying_index'] = 'Minimum Volatility'
        else:
            etf_fields['correlation_reference'] = 'SPY'  # Default to S&P 500
            etf_fields['underlying_index'] = 'S&P 500'  # Default underlying index
        
        # Calculate AUM from market cap if available
        market_cap = ticker_data.get('market_cap')
        if market_cap:
            # For ETFs, market cap is often close to AUM
            etf_fields['aum_millions'] = market_cap / 1000000  # Convert to millions
        
        logger.debug(f"HISTORICAL-LOADER: ETF metadata extracted for {symbol}: issuer={etf_fields['issuer']}, ref={etf_fields['correlation_reference']}")
        return etf_fields
    
    def _is_etf_symbol(self, symbol: str) -> bool:
        """
        Determine if a symbol is likely an ETF based on common patterns.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            True if symbol appears to be an ETF
        """
        # Common ETF symbol patterns and known ETF tickers
        etf_patterns = [
            'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'IVV', 'EEM', 'VEA', 'VWO',
            'XLK', 'XLF', 'XLV', 'XLE', 'XLI', 'XLY', 'XLP', 'XLB', 'XLU', 'XLRE',
            'VUG', 'VTV', 'VYM', 'IVW', 'IVE', 'SCHG', 'SCHV', 'BND', 'AGG',
            'GLD', 'SLV', 'TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'VGT', 'FTEC'
        ]
        
        return symbol in etf_patterns
    
    def fetch_etf_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed ETF information from Polygon.io.
        This supplements the basic ticker metadata with ETF-specific details.
        
        Args:
            symbol: ETF ticker (e.g., 'SPY')
            
        Returns:
            Dictionary with detailed ETF information or None
        """
        # Try to get ETF details from financials endpoint
        endpoint = f"/vX/reference/tickers/{symbol}/financials"
        
        try:
            response = self._make_api_request(endpoint)
            
            if response.get('status') == 'OK' and response.get('results'):
                # Extract relevant financial data for ETFs
                results = response['results']
                if results:
                    latest = results[0]  # Most recent financial data
                    financials = latest.get('financials', {})
                    balance_sheet = financials.get('balance_sheet', {})
                    
                    etf_details = {
                        'net_assets': balance_sheet.get('net_assets', {}).get('value'),
                        'total_assets': balance_sheet.get('assets', {}).get('value')
                    }
                    
                    logger.debug(f"HISTORICAL-LOADER: Fetched ETF details for {symbol}")
                    return etf_details
            
            logger.debug(f"HISTORICAL-LOADER: No detailed ETF data available for {symbol}")
            return {}
            
        except Exception as e:
            # ETF financials endpoint typically returns 404 - this is expected
            if "404" in str(e) or "Not Found" in str(e):
                logger.debug(f"HISTORICAL-LOADER: ETF financials not available for {symbol} (expected for ETFs)")
            else:
                logger.warning(f"HISTORICAL-LOADER: Failed to fetch ETF details for {symbol}: {e}")
            return {}
    
    def get_sector_industry_from_sic(self, sic_code: Optional[str]) -> Tuple[str, str]:
        """
        Map SIC code to sector and industry using database configuration.
        This replaces the hardcoded mapping from maint_get_stocks.py with database-driven approach.
        
        Args:
            sic_code: SIC code from Polygon API
            
        Returns:
            tuple: (sector, industry) strings
        """
        if not sic_code:
            return "Unknown", "Unknown"
        
        try:
            # First try exact SIC code mapping from cache_entries
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT value
                    FROM cache_entries 
                    WHERE type = 'cache_config' 
                      AND name = 'sic_mapping' 
                      AND key = %s
                """, (str(sic_code),))
                
                result = cursor.fetchone()
                if result:
                    # Handle both string and dict values from database
                    if isinstance(result[0], str):
                        mapping_data = json.loads(result[0])
                    else:
                        mapping_data = result[0]
                    return mapping_data["sector"], mapping_data["industry"]
                
                # If no exact match, try range-based fallback
                sic_int = int(sic_code)
                
                # Get all range configurations
                cursor.execute("""
                    SELECT key, value
                    FROM cache_entries 
                    WHERE type = 'cache_config' 
                      AND name = 'sic_ranges'
                """)
                
                range_results = cursor.fetchall()
                
                for range_key, range_value in range_results:
                    # Handle both string and dict values from database
                    if isinstance(range_value, str):
                        range_data = json.loads(range_value)
                    else:
                        range_data = range_value
                    for range_rule in range_data.get("ranges", []):
                        if range_rule["start"] <= sic_int <= range_rule["end"]:
                            return range_rule["sector"], range_rule["industry"]
                            
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            logger.warning(f"HISTORICAL-LOADER: Error resolving SIC {sic_code}: {e}")
        
        return "Unknown", "Unknown"

    def extract_country_from_address(self, address_data: Optional[Dict[str, Any]]) -> str:
        """Extract country from address data, defaulting to US for US-based companies."""
        if not address_data:
            return "US"  # Default assumption for US market
        
        # Most US companies don't include country in address
        state = address_data.get("state")
        if state and len(state) == 2:  # US state codes are 2 characters
            return "US"
        
        return address_data.get("country", "US")
    
    def ensure_symbol_exists(self, symbol: str) -> bool:
        """
        Ensure symbol exists in symbols table, create or update with latest metadata.
        Always fetches fresh metadata from Polygon.io to capture any updates.
        
        Args:
            symbol: Stock ticker to check/create/update
            
        Returns:
            True if symbol was processed successfully
        """
        self._connect_db()
        
        try:
            # Always fetch fresh metadata from API
            logger.info(f"HISTORICAL-LOADER: Fetching/updating symbol metadata for {symbol}")
            metadata = self.fetch_symbol_metadata(symbol)
            
            # Enhanced metadata processing with SIC resolution
            if metadata:
                # Extract sector/industry from SIC code
                sic_code = metadata.get("sic_code")
                sector, industry = self.get_sector_industry_from_sic(sic_code)
                
                # Extract country from address
                address_data = metadata.get("address", {})
                country = self.extract_country_from_address(address_data)
                
                # Parse list_date if available
                list_date = None
                if metadata.get("list_date"):
                    try:
                        list_date = datetime.strptime(metadata.get("list_date"), "%Y-%m-%d").date()
                    except ValueError:
                        logger.warning(f"HISTORICAL-LOADER: Invalid list_date format for {symbol}: {metadata.get('list_date')}")
                
                # Add new fields to metadata
                metadata.update({
                    'sic_code': sic_code,
                    'sic_description': metadata.get('sic_description'),
                    'sector': sector,
                    'industry': industry,
                    'country': country,
                    'total_employees': metadata.get('total_employees'),
                    'list_date': list_date
                })
                
                # Ensure all ETF fields are present with None defaults for non-ETF symbols
                if not (metadata.get('type') == 'ETF' or self._is_etf_symbol(symbol)):
                    etf_defaults = {
                        'etf_type': None,
                        'aum_millions': None,
                        'expense_ratio': None,
                        'fmv_supported': None,
                        'inception_date': None,
                        'issuer': '',
                        'correlation_reference': '',
                        'underlying_index': '',
                        'creation_unit_size': None,
                        'dividend_frequency': '',
                        'primary_exchange': metadata.get('primary_exchange', '')
                    }
                    # Only add fields that aren't already present
                    for key, value in etf_defaults.items():
                        if key not in metadata:
                            metadata[key] = value
                
                logger.info(f"HISTORICAL-LOADER: Enhanced {symbol} with sector: {sector}, industry: {industry}")
            else:
                # Default metadata includes new fields
                metadata = {
                    'symbol': symbol,
                    'name': f'Unknown Company ({symbol})',
                    'market': 'stocks',
                    'locale': 'us',
                    'currency_name': 'USD',
                    'currency_symbol': '$',
                    'type': 'CS',
                    'active': True,
                    'cik': None,
                    'composite_figi': None,
                    'share_class_figi': None,
                    'market_cap': None,
                    'weighted_shares_outstanding': None,
                    'etf_type': None,
                    'aum_millions': None,
                    'expense_ratio': None,
                    'fmv_supported': None,
                    'inception_date': None,
                    'issuer': '',
                    'correlation_reference': '',
                    'underlying_index': '',
                    'creation_unit_size': None,
                    'dividend_frequency': '',
                    'exchange': '',
                    'primary_exchange': '',
                    'last_updated_utc': datetime.utcnow(),
                    'sic_code': None,
                    'sic_description': None,
                    'sector': 'Unknown',
                    'industry': 'Unknown',
                    'country': 'US',
                    'total_employees': None,
                    'list_date': None
                }
                logger.warning(f"HISTORICAL-LOADER: Using enhanced default metadata for {symbol}")
            
            # Upsert symbol record (insert or update)
            with self.conn.cursor() as cursor:
                insert_sql = """
                INSERT INTO symbols (
                    symbol, name, exchange, market, locale, currency_name, 
                    currency_symbol, type, active, cik, composite_figi, 
                    share_class_figi, market_cap, weighted_shares_outstanding, 
                    last_updated_utc, last_updated,
                    etf_type, aum_millions, expense_ratio, fmv_supported, 
                    inception_date, primary_exchange, issuer, correlation_reference, 
                    underlying_index, creation_unit_size, dividend_frequency,
                    sic_code, sic_description, sector, industry, country, 
                    total_employees, list_date, sic_updated_at
                ) VALUES (
                    %(symbol)s, %(name)s, %(exchange)s, %(market)s, %(locale)s, 
                    %(currency_name)s, %(currency_symbol)s, %(type)s, %(active)s, 
                    %(cik)s, %(composite_figi)s, %(share_class_figi)s, 
                    %(market_cap)s, %(weighted_shares_outstanding)s, 
                    %(last_updated_utc)s, CURRENT_TIMESTAMP,
                    %(etf_type)s, %(aum_millions)s, %(expense_ratio)s, %(fmv_supported)s,
                    %(inception_date)s, %(primary_exchange)s, %(issuer)s, %(correlation_reference)s,
                    %(underlying_index)s, %(creation_unit_size)s, %(dividend_frequency)s,
                    %(sic_code)s, %(sic_description)s, %(sector)s, %(industry)s, %(country)s,
                    %(total_employees)s, %(list_date)s, CURRENT_TIMESTAMP
                ) ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    exchange = EXCLUDED.exchange,
                    market = EXCLUDED.market,
                    locale = EXCLUDED.locale,
                    currency_name = EXCLUDED.currency_name,
                    currency_symbol = EXCLUDED.currency_symbol,
                    type = EXCLUDED.type,
                    active = EXCLUDED.active,
                    cik = EXCLUDED.cik,
                    composite_figi = EXCLUDED.composite_figi,
                    share_class_figi = EXCLUDED.share_class_figi,
                    market_cap = EXCLUDED.market_cap,
                    weighted_shares_outstanding = EXCLUDED.weighted_shares_outstanding,
                    last_updated_utc = EXCLUDED.last_updated_utc,
                    last_updated = CURRENT_TIMESTAMP,
                    etf_type = EXCLUDED.etf_type,
                    aum_millions = EXCLUDED.aum_millions,
                    expense_ratio = EXCLUDED.expense_ratio,
                    fmv_supported = EXCLUDED.fmv_supported,
                    inception_date = EXCLUDED.inception_date,
                    primary_exchange = EXCLUDED.primary_exchange,
                    issuer = EXCLUDED.issuer,
                    correlation_reference = EXCLUDED.correlation_reference,
                    underlying_index = EXCLUDED.underlying_index,
                    creation_unit_size = EXCLUDED.creation_unit_size,
                    dividend_frequency = EXCLUDED.dividend_frequency,
                    sic_code = EXCLUDED.sic_code,
                    sic_description = EXCLUDED.sic_description,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    country = EXCLUDED.country,
                    total_employees = EXCLUDED.total_employees,
                    list_date = EXCLUDED.list_date,
                    sic_updated_at = CURRENT_TIMESTAMP
                """
                
                cursor.execute(insert_sql, metadata)
                self.conn.commit()
                
                # Log successful upsert (ON CONFLICT handles insert vs update)
                logger.info(f"HISTORICAL-LOADER: ✓ Upserted symbol metadata for {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to ensure symbol {symbol} exists: {e}")
            logger.error(f"HISTORICAL-LOADER: Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"HISTORICAL-LOADER: Traceback: {traceback.format_exc()}")
            if self.conn:
                self.conn.rollback()
            return False
            
    def _create_tables_if_needed(self):
        """Create historical data tables if they don't exist."""
        self._connect_db()
        
        # Table creation SQL
        daily_table_sql = """
        CREATE TABLE IF NOT EXISTS ohlcv_daily (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            open DECIMAL(12,4),
            high DECIMAL(12,4),
            low DECIMAL(12,4),
            close DECIMAL(12,4),
            volume BIGINT,
            transactions INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        );
        
        -- Create hypertable for TimescaleDB if available
        SELECT create_hypertable('ohlcv_daily', 'date', if_not_exists => TRUE);
        """
        
        minute_table_sql = """
        CREATE TABLE IF NOT EXISTS ohlcv_1min (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(12,4),
            high DECIMAL(12,4),
            low DECIMAL(12,4),
            close DECIMAL(12,4),
            volume BIGINT,
            transactions INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp)
        );
        
        -- Create hypertable for TimescaleDB if available
        SELECT create_hypertable('ohlcv_1min', 'timestamp', if_not_exists => TRUE);
        """
        
        try:
            with self.conn.cursor() as cursor:
                # Try to create daily table
                try:
                    cursor.execute(daily_table_sql)
                    logger.info("HISTORICAL-LOADER: ohlcv_daily table ready")
                except Exception as e:
                    # Fallback without hypertable creation
                    cursor.execute("ROLLBACK")
                    cursor.execute(daily_table_sql.split('SELECT create_hypertable')[0])
                    logger.warning(f"HISTORICAL-LOADER: Created ohlcv_daily without hypertable: {e}")
                
                # Try to create minute table
                try:
                    cursor.execute(minute_table_sql)
                    logger.info("HISTORICAL-LOADER: ohlcv_1min table ready")
                except Exception as e:
                    # Fallback without hypertable creation
                    cursor.execute("ROLLBACK")
                    cursor.execute(minute_table_sql.split('SELECT create_hypertable')[0])
                    logger.warning(f"HISTORICAL-LOADER: Created ohlcv_1min without hypertable: {e}")
                    
                self.conn.commit()
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to create tables: {e}")
            self.conn.rollback()
            raise
    
    def fetch_symbol_data(self, symbol: str, start_date: str, end_date: str, 
                         timespan: str = 'day', multiplier: int = 1) -> pd.DataFrame:
        """
        Fetch historical data for a single symbol.
        
        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            timespan: 'day', 'minute', 'hour' etc.
            multiplier: Time multiplier (e.g., 1 for 1-day, 5 for 5-minute)
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"HISTORICAL-LOADER: Fetching {symbol} data from {start_date} to {end_date}")
        
        all_data = []
        current_start = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Process in chunks to respect API limits
        while current_start < end_dt:
            # For daily data, process yearly chunks; for minute data, monthly chunks
            if timespan == 'day':
                current_end = min(current_start + timedelta(days=365), end_dt)
            else:
                current_end = min(current_start + timedelta(days=30), end_dt)
            
            chunk_start = current_start.strftime('%Y-%m-%d')
            chunk_end = current_end.strftime('%Y-%m-%d')
            
            endpoint = f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{chunk_start}/{chunk_end}"
            
            try:
                response = self._make_api_request(endpoint, {
                    'adjusted': 'true',
                    'sort': 'asc',
                    'limit': 50000
                })
                
                if response.get('status') == 'OK' and response.get('results'):
                    for result in response['results']:
                        record = {
                            'symbol': symbol,
                            'timestamp': pd.to_datetime(result['t'], unit='ms'),
                            'open': result['o'],
                            'high': result['h'], 
                            'low': result['l'],
                            'close': result['c'],
                            'volume': result['v'],
                            'transactions': result.get('n', None)
                        }
                        all_data.append(record)
                        
                    logger.info(f"HISTORICAL-LOADER: {symbol} chunk {chunk_start} to {chunk_end}: {len(response['results'])} records")
                else:
                    logger.warning(f"HISTORICAL-LOADER: No data for {symbol} {chunk_start}-{chunk_end}")
                    
            except Exception as e:
                logger.error(f"HISTORICAL-LOADER: Failed to fetch {symbol} {chunk_start}-{chunk_end}: {e}")
                
            current_start = current_end + timedelta(days=1)
            
        df = pd.DataFrame(all_data)
        logger.info(f"HISTORICAL-LOADER: Fetched {len(df)} total records for {symbol}")
        return df
    
    def save_data_to_db(self, df: pd.DataFrame, timespan: str = 'day'):
        """
        Save DataFrame to appropriate database table.
        
        Args:
            df: DataFrame with OHLCV data
            timespan: 'day' or 'minute' to determine target table
        """
        if df.empty:
            logger.warning("HISTORICAL-LOADER: No data to save")
            return
            
        self._connect_db()
        
        table_name = 'ohlcv_daily' if timespan == 'day' else 'ohlcv_1min'
        date_col = 'date' if timespan == 'day' else 'timestamp'
        
        # Prepare data
        if timespan == 'day':
            df['date'] = df['timestamp'].dt.date
            df = df.drop('timestamp', axis=1)
        
        # Remove transactions column if present (not in existing schema)
        if 'transactions' in df.columns:
            df = df.drop('transactions', axis=1)
        
        # Insert with ON CONFLICT handling for duplicates
        insert_sql = f"""
        INSERT INTO {table_name} (symbol, {date_col}, open, high, low, close, volume)
        VALUES (%(symbol)s, %({date_col})s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
        ON CONFLICT (symbol, {date_col}) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            created_at = CURRENT_TIMESTAMP
        """
        
        try:
            with self.conn.cursor() as cursor:
                # Insert in batches
                records = df.to_dict('records')
                for i in range(0, len(records), self.batch_size):
                    batch = records[i:i + self.batch_size]
                    cursor.executemany(insert_sql, batch)
                    logger.info(f"HISTORICAL-LOADER: Inserted batch {i//self.batch_size + 1} ({len(batch)} records)")
                
                self.conn.commit()
                logger.info(f"HISTORICAL-LOADER: Successfully saved {len(df)} records to {table_name}")
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to save data: {e}")
            self.conn.rollback()
            raise
    
    def load_symbols_from_cache(self, universe_key: str = 'top_50') -> List[str]:
        """
        Load symbols from cache_entries table.
        
        Args:
            universe_key: Cache key (e.g., 'top_50', 'mega_cap', 'all_stocks')
            
        Returns:
            List of ticker symbols
        """
        self._connect_db()
        
        # Build query based on universe type
        if universe_key.startswith('etf_'):
            # ETF universe categories
            query = """
            SELECT value FROM cache_entries 
            WHERE type = 'etf_universe' 
              AND key = %s
            """
        elif universe_key.startswith('top_10_') and universe_key != 'top_10_stocks':
            # Sector leaders format (top_10_technology, top_10_healthcare, etc.)
            query = """
            SELECT value FROM cache_entries 
            WHERE type = 'stock_universe' 
              AND name = 'sector_leaders'
              AND key = %s
            """
        elif universe_key in ['mega_cap', 'large_cap', 'mid_cap', 'small_cap', 'micro_cap']:
            # Market cap categories
            query = """
            SELECT value FROM cache_entries 
            WHERE type = 'stock_universe' 
              AND name = 'market_cap'
              AND key = %s
            """
        elif universe_key in ['ai', 'cloud', 'ev', 'fintech', 'semi', 'quantum', 'space']:
            # Theme categories
            query = """
            SELECT value FROM cache_entries 
            WHERE type = 'stock_universe' 
              AND name = 'themes'
              AND key = %s
            """
        elif universe_key == 'combo_test':
            # Stock + ETF combo test universe
            query = """
            SELECT value FROM cache_entries 
            WHERE type = 'stock_etf_combo' 
              AND name = 'stock_etf_test'
              AND key = 'combo_test'
            """
        elif universe_key == 'all_stocks':
            # Complete universe (simple ticker array)
            query = """
            SELECT value FROM cache_entries 
            WHERE type = 'stock_universe' 
              AND name = 'complete'
              AND key = 'all_stocks'
            """
        else:
            # Default: market leaders format
            query = """
            SELECT value FROM cache_entries 
            WHERE type = 'stock_universe' 
              AND (
                (name = 'market_leaders' AND key = %s) OR
                (name = 'complete' AND key = %s)
              )
            LIMIT 1
            """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Execute query based on parameter count
                if universe_key in ['all_stocks', 'combo_test']:
                    cursor.execute(query)  # No parameters for all_stocks and combo_test
                elif universe_key.startswith('etf_'):
                    # ETF universe queries - single parameter
                    cursor.execute(query, (universe_key,))
                elif 'LIMIT 1' in query:
                    # Query needs two parameters (for market_leaders fallback)
                    cursor.execute(query, (universe_key, universe_key))
                else:
                    # Single parameter queries
                    cursor.execute(query, (universe_key,))
                    
                result = cursor.fetchone()
                
                if result and result['value']:
                    # Handle different value formats
                    value = result['value']
                    
                    # Check if it's already a list (themes, all_stocks)
                    if isinstance(value, list):
                        symbols = value
                    # Check if it has 'stocks' key (market leaders, sectors, market cap)
                    elif isinstance(value, dict) and 'stocks' in value:
                        stocks = value.get('stocks', [])
                        symbols = [stock['ticker'] for stock in stocks]
                    # Check if it has 'etfs' key (ETF universes)
                    elif isinstance(value, dict) and 'etfs' in value:
                        etfs = value.get('etfs', [])
                        # Handle both 'ticker' and 'symbol' field names
                        symbols = [etf.get('ticker') or etf.get('symbol') for etf in etfs if etf.get('ticker') or etf.get('symbol')]
                    else:
                        logger.warning(f"HISTORICAL-LOADER: Unknown value format for {universe_key}")
                        return []
                    
                    logger.info(f"HISTORICAL-LOADER: Loaded {len(symbols)} symbols from {universe_key}")
                    return symbols
                else:
                    logger.warning(f"HISTORICAL-LOADER: No symbols found for {universe_key}")
                    return []
                    
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to load symbols: {e}")
            return []
    
    def create_etf_universes(self):
        """
        Create initial ETF universe entries in cache_entries table.
        This sets up the ETF themes mentioned in Sprint 14.
        """
        self._connect_db()
        
        # Popular ETFs for different themes
        etf_universes = {
            'etf_growth': {
                'name': 'Growth ETFs',
                'description': 'Popular growth-focused ETFs',
                'etfs': [
                    {'ticker': 'VUG', 'name': 'Vanguard Growth ETF'},
                    {'ticker': 'IVW', 'name': 'iShares Core S&P U.S. Growth ETF'},
                    {'ticker': 'SCHG', 'name': 'Schwab U.S. Large-Cap Growth ETF'},
                    {'ticker': 'QQQ', 'name': 'Invesco QQQ Trust ETF'},
                    {'ticker': 'VGT', 'name': 'Vanguard Information Technology ETF'},
                    {'ticker': 'XLK', 'name': 'Technology Select Sector SPDR Fund'},
                    {'ticker': 'ARKK', 'name': 'ARK Innovation ETF'},
                    {'ticker': 'TQQQ', 'name': 'ProShares UltraPro QQQ'},
                    {'ticker': 'IGV', 'name': 'iShares Expanded Tech-Software Sector ETF'},
                    {'ticker': 'FTEC', 'name': 'Fidelity MSCI Information Technology Index ETF'}
                ]
            },
            'etf_sectors': {
                'name': 'Sector ETFs', 
                'description': 'Major sector-focused ETFs',
                'etfs': [
                    {'ticker': 'XLF', 'name': 'Financial Select Sector SPDR Fund'},
                    {'ticker': 'XLE', 'name': 'Energy Select Sector SPDR Fund'},
                    {'ticker': 'XLV', 'name': 'Health Care Select Sector SPDR Fund'},
                    {'ticker': 'XLI', 'name': 'Industrial Select Sector SPDR Fund'},
                    {'ticker': 'XLU', 'name': 'Utilities Select Sector SPDR Fund'},
                    {'ticker': 'XLB', 'name': 'Materials Select Sector SPDR Fund'},
                    {'ticker': 'XLRE', 'name': 'Real Estate Select Sector SPDR Fund'},
                    {'ticker': 'XLP', 'name': 'Consumer Staples Select Sector SPDR Fund'},
                    {'ticker': 'XLY', 'name': 'Consumer Discretionary Select Sector SPDR Fund'},
                    {'ticker': 'XLC', 'name': 'Communication Services Select Sector SPDR Fund'}
                ]
            },
            'etf_value': {
                'name': 'Value ETFs',
                'description': 'Value-focused ETFs',
                'etfs': [
                    {'ticker': 'VTV', 'name': 'Vanguard Value ETF'},
                    {'ticker': 'IVE', 'name': 'iShares Core S&P U.S. Value ETF'},
                    {'ticker': 'SCHV', 'name': 'Schwab U.S. Large-Cap Value ETF'},
                    {'ticker': 'VYM', 'name': 'Vanguard High Dividend Yield ETF'},
                    {'ticker': 'DVY', 'name': 'iShares Select Dividend ETF'},
                    {'ticker': 'SPHD', 'name': 'Invesco S&P 500 High Dividend Low Volatility ETF'},
                    {'ticker': 'IWD', 'name': 'iShares Russell 1000 Value ETF'},
                    {'ticker': 'VOOV', 'name': 'Vanguard S&P 500 Value ETF'},
                    {'ticker': 'DGRW', 'name': 'WisdomTree US Quality Dividend Growth Fund'},
                    {'ticker': 'USMV', 'name': 'iShares MSCI USA Min Vol Factor ETF'}
                ]
            },
            'etf_broad_market': {
                'name': 'Broad Market ETFs',
                'description': 'Major broad market ETFs',
                'etfs': [
                    {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF Trust'},
                    {'ticker': 'VOO', 'name': 'Vanguard S&P 500 ETF'},
                    {'ticker': 'IVV', 'name': 'iShares Core S&P 500 ETF'},
                    {'ticker': 'VTI', 'name': 'Vanguard Total Stock Market ETF'},
                    {'ticker': 'ITOT', 'name': 'iShares Core S&P Total U.S. Stock Market ETF'},
                    {'ticker': 'IWM', 'name': 'iShares Russell 2000 ETF'},
                    {'ticker': 'IWN', 'name': 'iShares Russell 2000 Value ETF'},
                    {'ticker': 'IWO', 'name': 'iShares Russell 2000 Growth ETF'},
                    {'ticker': 'DIA', 'name': 'SPDR Dow Jones Industrial Average ETF Trust'},
                    {'ticker': 'MDY', 'name': 'SPDR S&P MidCap 400 ETF Trust'}
                ]
            }
        }
        
        try:
            with self.conn.cursor() as cursor:
                for universe_key, universe_data in etf_universes.items():
                    insert_sql = """
                    INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                    VALUES ('etf_universe', %s, %s, %s, 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (type, name, key, environment) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = CURRENT_TIMESTAMP
                    """
                    
                    cursor.execute(insert_sql, (universe_data['name'], universe_key, json.dumps(universe_data)))
                    logger.info(f"HISTORICAL-LOADER: Created/updated ETF universe {universe_key} with {len(universe_data['etfs'])} ETFs")
                
                self.conn.commit()
                logger.info("HISTORICAL-LOADER: ETF universe creation completed")
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to create ETF universes: {e}")
            if self.conn:
                self.conn.rollback()
            raise
    
    def load_historical_data(self, symbols: List[str], years: int = 1, months: int = None,
                           timespan: str = 'day', multiplier: int = 1, dev_mode: bool = False):
        """
        Load historical data for multiple symbols.
        Enhanced with ETF support and development mode optimizations.
        
        Args:
            symbols: List of ticker symbols (stocks and ETFs)
            years: Number of years of historical data to load
            months: Number of months to load (overrides years, for dev subsets)
            timespan: 'day' or 'minute'
            multiplier: Time multiplier
            dev_mode: Enable development optimizations
        """
        # Calculate date range - support months for development subsets
        end_date = datetime.now()
        if months:
            start_date = end_date - timedelta(days=int(months * 30))
            logger.info(f"HISTORICAL-LOADER: Loading {months} months of data (development mode)")
        else:
            start_date = end_date - timedelta(days=int(years * 365))
            logger.info(f"HISTORICAL-LOADER: Loading {years} years of data")
        
        # Development mode optimizations
        if dev_mode:
            self.rate_limit_delay = 6  # Faster for dev (10 calls/minute)
            logger.info("HISTORICAL-LOADER: Development mode enabled - reduced rate limiting")
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"HISTORICAL-LOADER: Starting bulk load for {len(symbols)} symbols")
        logger.info(f"HISTORICAL-LOADER: Date range: {start_str} to {end_str}")
        logger.info(f"HISTORICAL-LOADER: Timespan: {multiplier} {timespan}")
        
        # Create tables if needed
        self._create_tables_if_needed()
        
        successful_loads = 0
        failed_symbols = []
        
        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"HISTORICAL-LOADER: Processing {symbol} ({i+1}/{len(symbols)})")
                
                # Ensure symbol exists in symbols table first
                logger.debug(f"HISTORICAL-LOADER: About to ensure symbol {symbol} exists")
                if not self.ensure_symbol_exists(symbol):
                    logger.error(f"HISTORICAL-LOADER: ✗ {symbol} - failed to create symbol record")
                    failed_symbols.append(symbol)
                    continue
                logger.debug(f"HISTORICAL-LOADER: Symbol {symbol} existence confirmed")
                
                # Fetch data
                df = self.fetch_symbol_data(symbol, start_str, end_str, timespan, multiplier)
                
                if not df.empty:
                    # Save to database
                    self.save_data_to_db(df, timespan)
                    successful_loads += 1
                    logger.info(f"HISTORICAL-LOADER: ✓ {symbol} completed ({len(df)} records)")
                else:
                    logger.warning(f"HISTORICAL-LOADER: ✗ {symbol} - no data received")
                    failed_symbols.append(symbol)
                    
            except Exception as e:
                logger.error(f"HISTORICAL-LOADER: ✗ {symbol} failed: {e}")
                failed_symbols.append(symbol)
                
        logger.info(f"HISTORICAL-LOADER: Bulk load completed")
        logger.info(f"HISTORICAL-LOADER: Successful: {successful_loads}/{len(symbols)}")
        if failed_symbols:
            logger.warning(f"HISTORICAL-LOADER: Failed symbols: {', '.join(failed_symbols)}")
            
    def get_data_summary(self, timespan: str = 'day') -> Dict[str, Any]:
        """Get summary of loaded historical data."""
        self._connect_db()
        
        table_name = 'ohlcv_daily' if timespan == 'day' else 'ohlcv_1min'
        date_col = 'date' if timespan == 'day' else 'timestamp'
        
        query = f"""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            MIN({date_col}) as earliest_date,
            MAX({date_col}) as latest_date
        FROM {table_name}
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return dict(result) if result else {}
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to get summary: {e}")
            return {}
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, 'conn'):
            self._close_db()

def main():
    """CLI entry point for historical data loading."""
    parser = argparse.ArgumentParser(description='Load historical data from Polygon.io')
    parser.add_argument('--symbols', help='Comma-separated list of symbols (e.g., AAPL,MSFT)')
    parser.add_argument('--universe', default='top_50', help='Stock universe key from cache_entries')
    parser.add_argument('--years', type=float, default=1, help='Years of historical data to load')
    parser.add_argument('--timespan', default='day', choices=['day', 'minute'], help='Data timespan')
    parser.add_argument('--multiplier', type=int, default=1, help='Time multiplier')
    parser.add_argument('--api-key', help='Polygon.io API key (overrides env var)')
    parser.add_argument('--database-uri', help='Database URI (overrides env var)')
    parser.add_argument('--summary', action='store_true', help='Show data summary only')
    
    args = parser.parse_args()
    
    try:
        # Initialize loader
        loader = PolygonHistoricalLoader(
            api_key=args.api_key,
            database_uri=args.database_uri
        )
        
        if args.summary:
            # Show summary
            summary = loader.get_data_summary(args.timespan)
            print("\nHistorical Data Summary:")
            print(f"Table: ohlcv_{args.timespan}")
            for key, value in summary.items():
                print(f"  {key}: {value}")
            return
        
        # Determine symbols to load
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(',')]
        else:
            symbols = loader.load_symbols_from_cache(args.universe)
            
        if not symbols:
            logger.error("No symbols to load. Specify --symbols or ensure cache_entries has data.")
            return
            
        # Load historical data
        loader.load_historical_data(
            symbols=symbols,
            years=args.years,
            months=args.months,
            timespan=args.timespan,
            multiplier=args.multiplier,
            dev_mode=args.dev_mode
        )
        
        # Show final summary
        summary = loader.get_data_summary(args.timespan)
        print("\nLoad Complete - Data Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        logger.error(f"HISTORICAL-LOADER: Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()