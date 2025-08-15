'''
Use Polygon's API to fetch all stocks, map to sectors and industry and load staging/processing table to then load in cache from secondary job

Polygon --> public.stock_main

2nd Job

public.stock_main --> cache_entries
'''
import requests
import psycopg2
from psycopg2 import sql
from datetime import datetime
import logging
import time
import json
import sys
from collections import defaultdict

# Configuration
POLYGON_API_KEY = "RtZnxR_RWjhOfLoMZSllqCDqsu186_75"  # Replace with your Polygon.io API key
BASE_URL = "https://api.polygon.io"
TICKERS_URL = f"{BASE_URL}/v3/reference/tickers"
COMPANY_URL = f"{BASE_URL}/v3/reference/tickers"
RELATED_TICKERS_URL = f"{BASE_URL}/v1/related-companies"

DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "tickstock",
    "user": "app_readwrite",
    "password": "1DfTGVBsECVtJa"
}

# Comprehensive SIC Code to Sector/Industry mapping
SIC_MAPPING = {
    # Technology
    "3571": {"sector": "Technology", "industry": "Computer Hardware"},
    "3572": {"sector": "Technology", "industry": "Computer Storage & Peripherals"},
    "3575": {"sector": "Technology", "industry": "Computer Terminals"},
    "3576": {"sector": "Technology", "industry": "Computer Communications Equipment"},
    "3577": {"sector": "Technology", "industry": "Computer Peripheral Equipment"},
    "3578": {"sector": "Technology", "industry": "Calculating & Accounting Machines"},
    "3661": {"sector": "Technology", "industry": "Telephone & Telegraph Equipment"},
    "3663": {"sector": "Technology", "industry": "Radio & TV Broadcasting Equipment"},
    "3669": {"sector": "Technology", "industry": "Communications Equipment"},
    "3672": {"sector": "Technology", "industry": "Printed Circuit Boards"},
    "3674": {"sector": "Technology", "industry": "Semiconductors"},
    "3679": {"sector": "Technology", "industry": "Electronic Components"},
    "7370": {"sector": "Technology", "industry": "Computer Programming & Data Processing"},
    "7371": {"sector": "Technology", "industry": "Computer Programming Services"},
    "7372": {"sector": "Technology", "industry": "Prepackaged Software"},
    "7373": {"sector": "Technology", "industry": "Computer Integrated Systems Design"},
    "7374": {"sector": "Technology", "industry": "Computer Processing & Data Preparation"},
    "7375": {"sector": "Technology", "industry": "Information Retrieval Services"},
    "7376": {"sector": "Technology", "industry": "Computer Facilities Management"},
    "7377": {"sector": "Technology", "industry": "Computer Rental & Leasing"},
    "7378": {"sector": "Technology", "industry": "Computer Maintenance & Repair"},
    "7379": {"sector": "Technology", "industry": "Computer Related Services"},
    
    # Healthcare & Biotechnology
    "2833": {"sector": "Healthcare", "industry": "Medicinal Chemicals"},
    "2834": {"sector": "Healthcare", "industry": "Pharmaceutical Preparations"},
    "2835": {"sector": "Healthcare", "industry": "In Vitro Diagnostics"},
    "2836": {"sector": "Healthcare", "industry": "Biological Products"},
    "3841": {"sector": "Healthcare", "industry": "Surgical & Medical Instruments"},
    "3842": {"sector": "Healthcare", "industry": "Orthopedic & Prosthetic Appliances"},
    "3845": {"sector": "Healthcare", "industry": "Electromedical Equipment"},
    "5047": {"sector": "Healthcare", "industry": "Medical Equipment Wholesale"},
    "8000": {"sector": "Healthcare", "industry": "Health Services"},
    "8011": {"sector": "Healthcare", "industry": "Offices of Doctors"},
    "8071": {"sector": "Healthcare", "industry": "Medical Laboratories"},
    "8082": {"sector": "Healthcare", "industry": "Home Health Care Services"},
    
    # Financial Services
    "6021": {"sector": "Financial Services", "industry": "National Commercial Banks"},
    "6022": {"sector": "Financial Services", "industry": "State Commercial Banks"},
    "6029": {"sector": "Financial Services", "industry": "Commercial Banks"},
    "6035": {"sector": "Financial Services", "industry": "Savings Institutions"},
    "6036": {"sector": "Financial Services", "industry": "Savings Institutions"},
    "6141": {"sector": "Financial Services", "industry": "Personal Credit Institutions"},
    "6153": {"sector": "Financial Services", "industry": "Short-Term Business Credit"},
    "6159": {"sector": "Financial Services", "industry": "Miscellaneous Business Credit"},
    "6162": {"sector": "Financial Services", "industry": "Mortgage Bankers & Brokers"},
    "6199": {"sector": "Financial Services", "industry": "Finance Services"},
    "6211": {"sector": "Financial Services", "industry": "Security Brokers & Dealers"},
    "6221": {"sector": "Financial Services", "industry": "Commodity Contracts Brokers"},
    "6282": {"sector": "Financial Services", "industry": "Investment Advice"},
    "6311": {"sector": "Financial Services", "industry": "Life Insurance"},
    "6321": {"sector": "Financial Services", "industry": "Accident & Health Insurance"},
    "6324": {"sector": "Financial Services", "industry": "Hospital & Medical Service Plans"},
    "6331": {"sector": "Financial Services", "industry": "Fire, Marine & Casualty Insurance"},
    "6351": {"sector": "Financial Services", "industry": "Surety Insurance"},
    "6361": {"sector": "Financial Services", "industry": "Title Insurance"},
    "6371": {"sector": "Financial Services", "industry": "Pension, Health & Welfare Funds"},
    
    # Consumer Discretionary
    "2300": {"sector": "Consumer Discretionary", "industry": "Apparel & Textiles"},
    "3711": {"sector": "Consumer Discretionary", "industry": "Motor Vehicles"},
    "3714": {"sector": "Consumer Discretionary", "industry": "Motor Vehicle Parts"},
    "3715": {"sector": "Consumer Discretionary", "industry": "Truck Trailers"},
    "3716": {"sector": "Consumer Discretionary", "industry": "Motor Homes"},
    "3751": {"sector": "Consumer Discretionary", "industry": "Motorcycles & Bicycles"},
    "5311": {"sector": "Consumer Discretionary", "industry": "Department Stores"},
    "5331": {"sector": "Consumer Discretionary", "industry": "Variety Stores"},
    "5411": {"sector": "Consumer Discretionary", "industry": "Grocery Stores"},
    "5531": {"sector": "Consumer Discretionary", "industry": "Auto & Home Supply Stores"},
    "5621": {"sector": "Consumer Discretionary", "industry": "Women's Clothing Stores"},
    "5651": {"sector": "Consumer Discretionary", "industry": "Family Clothing Stores"},
    "5812": {"sector": "Consumer Discretionary", "industry": "Eating Places"},
    "5912": {"sector": "Consumer Discretionary", "industry": "Drug Stores"},
    "5944": {"sector": "Consumer Discretionary", "industry": "Jewelry Stores"},
    "5961": {"sector": "Consumer Discretionary", "industry": "Catalog & Mail-Order Houses"},
    "7011": {"sector": "Consumer Discretionary", "industry": "Hotels & Motels"},
    
    # Energy
    "1311": {"sector": "Energy", "industry": "Crude Petroleum & Natural Gas"},
    "1321": {"sector": "Energy", "industry": "Natural Gas Liquids"},
    "1381": {"sector": "Energy", "industry": "Drilling Oil & Gas Wells"},
    "1382": {"sector": "Energy", "industry": "Oil & Gas Field Exploration Services"},
    "1389": {"sector": "Energy", "industry": "Oil & Gas Field Services"},
    "2911": {"sector": "Energy", "industry": "Petroleum Refining"},
    "4612": {"sector": "Energy", "industry": "Crude Petroleum Pipelines"},
    "4613": {"sector": "Energy", "industry": "Refined Petroleum Pipelines"},
    
    # Industrials
    "1540": {"sector": "Industrials", "industry": "General Building Contractors"},
    "3531": {"sector": "Industrials", "industry": "Construction Machinery"},
    "3537": {"sector": "Industrials", "industry": "Industrial Trucks & Tractors"},
    "3559": {"sector": "Industrials", "industry": "Special Industry Machinery"},
    "3560": {"sector": "Industrials", "industry": "General Industrial Machinery"},
    "3721": {"sector": "Industrials", "industry": "Aircraft"},
    "3724": {"sector": "Industrials", "industry": "Aircraft Engines & Parts"},
    "3728": {"sector": "Industrials", "industry": "Aircraft Parts & Equipment"},
    "4011": {"sector": "Industrials", "industry": "Railroads"},
    "4213": {"sector": "Industrials", "industry": "Trucking"},
    "4512": {"sector": "Industrials", "industry": "Air Transportation"},
    "4513": {"sector": "Industrials", "industry": "Air Courier Services"},
    "7359": {"sector": "Industrials", "industry": "Equipment Rental & Leasing"},
    
    # Materials
    "1000": {"sector": "Materials", "industry": "Metal Mining"},
    "2621": {"sector": "Materials", "industry": "Paper Mills"},
    "2800": {"sector": "Materials", "industry": "Chemicals & Allied Products"},
    "2821": {"sector": "Materials", "industry": "Plastics Materials & Resins"},
    "2822": {"sector": "Materials", "industry": "Synthetic Rubber"},
    "2851": {"sector": "Materials", "industry": "Paints & Allied Products"},
    "2870": {"sector": "Materials", "industry": "Agricultural Chemicals"},
    "2890": {"sector": "Materials", "industry": "Miscellaneous Chemical Products"},
    "3312": {"sector": "Materials", "industry": "Steel Works & Blast Furnaces"},
    "3317": {"sector": "Materials", "industry": "Steel Pipe & Tubes"},
    "3334": {"sector": "Materials", "industry": "Primary Production of Aluminum"},
    "3357": {"sector": "Materials", "industry": "Drawing & Insulating of Nonferrous Wire"},
    
    # Consumer Staples
    "2000": {"sector": "Consumer Staples", "industry": "Food & Kindred Products"},
    "2020": {"sector": "Consumer Staples", "industry": "Dairy Products"},
    "2030": {"sector": "Consumer Staples", "industry": "Canned & Preserved Fruits & Vegetables"},
    "2040": {"sector": "Consumer Staples", "industry": "Grain Mill Products"},
    "2050": {"sector": "Consumer Staples", "industry": "Bakery Products"},
    "2060": {"sector": "Consumer Staples", "industry": "Sugar & Confectionery Products"},
    "2070": {"sector": "Consumer Staples", "industry": "Fats & Oils"},
    "2080": {"sector": "Consumer Staples", "industry": "Beverages"},
    "2090": {"sector": "Consumer Staples", "industry": "Miscellaneous Food Preparations"},
    "2100": {"sector": "Consumer Staples", "industry": "Tobacco Products"},
    
    # Utilities
    "4911": {"sector": "Utilities", "industry": "Electric Services"},
    "4922": {"sector": "Utilities", "industry": "Natural Gas Transmission"},
    "4923": {"sector": "Utilities", "industry": "Natural Gas Transmission & Distribution"},
    "4924": {"sector": "Utilities", "industry": "Natural Gas Distribution"},
    "4931": {"sector": "Utilities", "industry": "Electric & Other Services Combined"},
    "4932": {"sector": "Utilities", "industry": "Gas & Other Services Combined"},
    "4941": {"sector": "Utilities", "industry": "Water Supply"},
    
    # Real Estate
    "6500": {"sector": "Real Estate", "industry": "Real Estate"},
    "6510": {"sector": "Real Estate", "industry": "Real Estate Operators"},
    "6512": {"sector": "Real Estate", "industry": "Operators of Nonresidential Buildings"},
    "6513": {"sector": "Real Estate", "industry": "Operators of Apartment Buildings"},
    "6519": {"sector": "Real Estate", "industry": "Lessors of Real Property"},
    "6531": {"sector": "Real Estate", "industry": "Real Estate Agents & Managers"},
    "6798": {"sector": "Real Estate", "industry": "Real Estate Investment Trusts"},
    
    # Communication Services
    "2711": {"sector": "Communication Services", "industry": "Newspapers"},
    "2721": {"sector": "Communication Services", "industry": "Periodicals"},
    "2731": {"sector": "Communication Services", "industry": "Books"},
    "4813": {"sector": "Communication Services", "industry": "Telephone Communications"},
    "4822": {"sector": "Communication Services", "industry": "Telegraph Communications"},
    "4832": {"sector": "Communication Services", "industry": "Radio Broadcasting"},
    "4833": {"sector": "Communication Services", "industry": "Television Broadcasting"},
    "4841": {"sector": "Communication Services", "industry": "Cable & Other Pay Television Services"},
    "7812": {"sector": "Communication Services", "industry": "Motion Picture & Video Tape Production"},
    # Additional specific codes found in data
    "3826": {"sector": "Technology", "industry": "Laboratory Analytical Instruments"},
    "6770": {"sector": "Financial Services", "industry": "Blank Check Companies"},
    "3585": {"sector": "Industrials", "industry": "Air-Conditioning & Heating Equipment"},
    "1400": {"sector": "Materials", "industry": "Mining & Quarrying of Nonmetallic Minerals"},
    "5500": {"sector": "Consumer Discretionary", "industry": "Automotive Dealers & Service Stations"},
    "7340": {"sector": "Industrials", "industry": "Services to Dwellings & Buildings"},
    "8731": {"sector": "Healthcare", "industry": "Commercial Physical & Biological Research"},
    "3440": {"sector": "Industrials", "industry": "Fabricated Structural Metal Products"},
    "2780": {"sector": "Industrials", "industry": "Blankbooks & Looseleaf Binders"},
    "8742": {"sector": "Industrials", "industry": "Management Consulting Services"},
    "7900": {"sector": "Consumer Discretionary", "industry": "Amusement & Recreation Services"},
    "8093": {"sector": "Healthcare", "industry": "Specialty Outpatient Facilities"},
    "8711": {"sector": "Industrials", "industry": "Engineering Services"},
    "7389": {"sector": "Industrials", "industry": "Business Services"},
    "6411": {"sector": "Financial Services", "industry": "Insurance Agents & Brokers"},
    "6794": {"sector": "Financial Services", "industry": "Patent Owners & Lessors"},
    "3420": {"sector": "Industrials", "industry": "Cutlery, Handtools & General Hardware"},
    "3690": {"sector": "Technology", "industry": "Miscellaneous Electrical Machinery"},
    "7381": {"sector": "Industrials", "industry": "Detective, Guard & Armored Car Services"},
    "3825": {"sector": "Technology", "industry": "Instruments for Measuring & Testing"},
    "5099": {"sector": "Consumer Discretionary", "industry": "Durable Goods Wholesale"},
}

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_polygon_connection():
    """Test connection to Polygon API."""
    print("\n🔍 Testing Polygon API connection...")
    
    # Try multiple endpoints to ensure connection works
    test_endpoints = [
        {
            "url": f"{BASE_URL}/v3/reference/tickers",
            "params": {
                "apiKey": POLYGON_API_KEY,
                "limit": 1,
                "market": "stocks",
                "type": "CS"
            },
            "name": "Tickers endpoint"
        },
        {
            "url": f"{BASE_URL}/v1/marketstatus/now",
            "params": {"apiKey": POLYGON_API_KEY},
            "name": "Market status endpoint"
        }
    ]
    
    for endpoint in test_endpoints:
        try:
            print(f"   Testing {endpoint['name']}...")
            response = requests.get(endpoint["url"], params=endpoint["params"], timeout=10)
            
            # Check HTTP status
            if response.status_code == 401:
                print("❌ Authentication failed - Invalid API key")
                print(f"   Please check your API key: {POLYGON_API_KEY[:10]}...")
                return False
            elif response.status_code == 403:
                print("❌ Access forbidden - API key may not have required permissions")
                return False
            elif response.status_code == 429:
                print("❌ Rate limit exceeded - Too many requests")
                return False
            
            response.raise_for_status()
            data = response.json()
            
            # Debug: Show the actual response structure
            if "status" not in data:
                print(f"   Response keys: {list(data.keys())}")
            
            # Check for successful response (Polygon uses different status indicators)
            if data.get("status") in ["OK", "SUCCESS"] or "results" in data:
                print(f"✅ Polygon API connection successful via {endpoint['name']}!")
                
                # Try to show some relevant info
                if "market" in data:
                    print(f"   Market Status: {data.get('market', 'unknown')}")
                elif "results" in data and len(data["results"]) > 0:
                    print(f"   Test fetch successful - API is responding")
                    if endpoint["name"] == "Tickers endpoint":
                        sample = data["results"][0]
                        print(f"   Sample stock: {sample.get('ticker')} - {sample.get('name')}")
                
                return True
            else:
                print(f"   API returned status: {data.get('status', 'No status field')}")
                print(f"   Full response: {json.dumps(data, indent=2)[:500]}...")
                continue
                
        except requests.exceptions.Timeout:
            print(f"   Timeout on {endpoint['name']}")
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"   Connection error on {endpoint['name']}: {e}")
            continue
        except requests.exceptions.RequestException as e:
            print(f"   Request error on {endpoint['name']}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response status code: {e.response.status_code}")
                try:
                    error_data = e.response.json()
                    print(f"   Error message: {error_data}")
                except:
                    print(f"   Response text: {e.response.text[:200]}")
            continue
        except json.JSONDecodeError as e:
            print(f"   Failed to parse JSON response: {e}")
            print(f"   Raw response: {response.text[:200]}...")
            continue
        except Exception as e:
            print(f"   Unexpected error on {endpoint['name']}: {e}")
            continue
    
    print("❌ Could not establish connection to Polygon API")
    print("\n📋 Troubleshooting tips:")
    print("   1. Check your API key is correct")
    print("   2. Ensure you have an active Polygon.io subscription")
    print("   3. Verify your API key has the required permissions")
    print("   4. Check if you've exceeded rate limits")
    print("   5. Try visiting https://api.polygon.io in your browser")
    
    return False

def test_database_connection():
    """Test connection to PostgreSQL database."""
    print("\n🔍 Testing database connection...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version();")
            db_info = cur.fetchone()
            print("✅ Database connection successful!")
            print(f"   Database: {db_info[0]}")
            print(f"   User: {db_info[1]}")
            
            # Check if tables exist
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('stock_main', 'stock_related_tickers')
                ORDER BY table_name;
            """)
            tables = cur.fetchall()
            if tables:
                print(f"   Found tables: {', '.join([t[0] for t in tables])}")
                
                # Get current stock count
                cur.execute("SELECT COUNT(*) FROM stock_main WHERE type = 'CS';")
                count = cur.fetchone()[0]
                print(f"   Current common stocks in database: {count:,}")
            else:
                print("   ⚠️  Required tables not found!")
                return False
                
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

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

def get_sector_industry_from_sic(sic_code):
    """Map SIC code to sector and industry with fallback logic."""
    if not sic_code:
        return "Unknown", "Unknown"
    
    # Direct mapping first
    if sic_code in SIC_MAPPING:
        mapping = SIC_MAPPING[sic_code]
        return mapping["sector"], mapping["industry"]
    
    # Fallback to broader SIC code ranges
    try:
        sic_int = int(sic_code)
        
        # Technology ranges
        if 3570 <= sic_int <= 3579:
            return "Technology", "Computer & Office Equipment"
        elif 3660 <= sic_int <= 3699:
            return "Technology", "Electronic & Electrical Equipment"
        elif 7370 <= sic_int <= 7379:
            return "Technology", "Computer Programming & Data Processing"
        elif 3820 <= sic_int <= 3829:
            return "Technology", "Measuring & Controlling Devices"
        
        # Healthcare ranges
        elif 2830 <= sic_int <= 2839:
            return "Healthcare", "Drugs"
        elif 3840 <= sic_int <= 3849:
            return "Healthcare", "Medical Instruments & Supplies"
        elif 8000 <= sic_int <= 8099:
            return "Healthcare", "Health Services"
        elif 8730 <= sic_int <= 8739:
            return "Healthcare", "Research & Testing Services"
        
        # Financial Services ranges
        elif 6000 <= sic_int <= 6099:
            return "Financial Services", "Depository Institutions"
        elif 6100 <= sic_int <= 6199:
            return "Financial Services", "Non-Depository Credit Institutions"
        elif 6200 <= sic_int <= 6299:
            return "Financial Services", "Security & Commodity Brokers"
        elif 6300 <= sic_int <= 6399:
            return "Financial Services", "Insurance Carriers"
        elif 6400 <= sic_int <= 6499:
            return "Financial Services", "Insurance Agents & Brokers"
        elif 6700 <= sic_int <= 6799:
            return "Financial Services", "Holding & Investment Offices"
        
        # Industrials ranges
        elif 1500 <= sic_int <= 1599:
            return "Industrials", "Building Construction"
        elif 3500 <= sic_int <= 3569:
            return "Industrials", "Industrial & Commercial Machinery"
        elif 3700 <= sic_int <= 3799:
            return "Industrials", "Transportation Equipment"
        elif 4000 <= sic_int <= 4099:
            return "Industrials", "Railroad Transportation"
        elif 4200 <= sic_int <= 4299:
            return "Industrials", "Motor Freight Transportation"
        elif 4500 <= sic_int <= 4599:
            return "Industrials", "Transportation by Air"
        elif 8700 <= sic_int <= 8799:
            return "Industrials", "Engineering & Management Services"
        
        # Consumer Discretionary ranges
        elif 2300 <= sic_int <= 2399:
            return "Consumer Discretionary", "Apparel & Other Finished Products"
        elif 3700 <= sic_int <= 3719:
            return "Consumer Discretionary", "Motor Vehicles & Equipment"
        elif 5000 <= sic_int <= 5199:
            return "Consumer Discretionary", "Wholesale Trade"
        elif 5200 <= sic_int <= 5999:
            return "Consumer Discretionary", "Retail Trade"
        elif 7000 <= sic_int <= 7099:
            return "Consumer Discretionary", "Hotels & Lodging"
        elif 7300 <= sic_int <= 7399:
            return "Consumer Discretionary", "Business Services"
        elif 7800 <= sic_int <= 7999:
            return "Consumer Discretionary", "Motion Pictures & Amusement Services"
        
        # Energy ranges
        elif 1300 <= sic_int <= 1399:
            return "Energy", "Oil & Gas Extraction"
        elif 2900 <= sic_int <= 2999:
            return "Energy", "Petroleum Refining"
        elif 4600 <= sic_int <= 4699:
            return "Energy", "Pipelines"
        
        # Materials ranges
        elif 1000 <= sic_int <= 1499:
            return "Materials", "Mining"
        elif 2600 <= sic_int <= 2699:
            return "Materials", "Paper & Allied Products"
        elif 2800 <= sic_int <= 2899:
            return "Materials", "Chemicals & Allied Products"
        elif 3300 <= sic_int <= 3399:
            return "Materials", "Primary Metal Industries"
        
        # Consumer Staples ranges
        elif 2000 <= sic_int <= 2199:
            return "Consumer Staples", "Food & Kindred Products"
        
        # Utilities ranges
        elif 4900 <= sic_int <= 4999:
            return "Utilities", "Electric, Gas & Sanitary Services"
        
        # Real Estate ranges
        elif 6500 <= sic_int <= 6599:
            return "Real Estate", "Real Estate"
        
        # Communication Services ranges
        elif 2700 <= sic_int <= 2799:
            return "Communication Services", "Printing, Publishing & Allied Industries"
        elif 4800 <= sic_int <= 4899:
            return "Communication Services", "Communications"
            
    except (ValueError, TypeError):
        pass
    
    return "Unknown", "Unknown"

def extract_country_from_address(address_data):
    """Extract country from address data, defaulting to US for US-based companies."""
    if not address_data:
        return "US"  # Default assumption for US market
    
    # Most US companies don't include country in address
    state = address_data.get("state")
    if state and len(state) == 2:  # US state codes are 2 characters
        return "US"
    
    return address_data.get("country", "US")

def truncate_tables(conn):
    """Truncate stock_main and stock_related_tickers tables."""
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE stock_related_tickers CASCADE;")
            cur.execute("TRUNCATE TABLE stock_main CASCADE;")
        conn.commit()
        logger.info("Tables truncated successfully.")
    except Exception as e:
        logger.error(f"Error truncating tables: {e}")
        conn.rollback()
        raise

def fetch_tickers_batch(next_url=None):
    """Fetch a batch of common stocks (CS) from Polygon.io."""
    url = next_url or TICKERS_URL
    params = {
        "apiKey": POLYGON_API_KEY,
        "limit": 500,
        "market": "stocks",
        "locale": "us",
        "active": "true",
        "type": "CS"  # Filter for common stocks only
    } if not next_url else {"apiKey": POLYGON_API_KEY}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "OK":
            raise ValueError(f"API response status not OK: {data.get('status')}")
        
        results = data.get("results", [])
        # Additional filter to ensure we only get CS type
        filtered_results = [stock for stock in results if stock.get("type") == "CS"]
        
        logger.info(f"Fetched {len(filtered_results)} common stocks from batch")
        return filtered_results, data.get("next_url")
    except Exception as e:
        logger.error(f"Error fetching tickers: {e}")
        return [], None

def fetch_company_data(ticker):
    """Fetch company overview data for a ticker."""
    try:
        response = requests.get(f"{COMPANY_URL}/{ticker}", params={"apiKey": POLYGON_API_KEY})
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            logger.warning(f"Company data API status not OK for {ticker}: {data.get('status')}")
            return {}
            
        results = data.get("results", {})
        logger.debug(f"Fetched company data for {ticker}: market_cap={results.get('market_cap')}, sic_code={results.get('sic_code')}")
        return results
    except Exception as e:
        logger.warning(f"Error fetching company data for {ticker}: {e}")
        return {}

def fetch_related_tickers(ticker):
    """Fetch related tickers for a stock."""
    try:
        response = requests.get(f"{RELATED_TICKERS_URL}/{ticker}", params={"apiKey": POLYGON_API_KEY})
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            logger.warning(f"Related tickers API status not OK for {ticker}: {data.get('status')}")
            return []
            
        related_list = [rt["ticker"] for rt in data.get("results", [])]
        logger.debug(f"Fetched {len(related_list)} related tickers for {ticker}")
        return related_list
    except Exception as e:
        logger.warning(f"Error fetching related tickers for {ticker}: {e}")
        return []

def validate_stock(stock):
    """Validate stock data - ensure it's a common stock."""
    if stock.get("type") != "CS":
        logger.debug(f"Skipping non-CS stock: {stock.get('ticker')} (type: {stock.get('type')})")
        return False
    
    if not stock.get("ticker"):
        logger.warning("Stock missing ticker symbol")
        return False
        
    return True

def insert_stock(conn, stock, company_data, related_tickers):
    """Insert a stock and its related tickers into the database."""
    if not validate_stock(stock):
        return
    
    ticker = stock.get("ticker")
    
    try:
        # Extract sector/industry from SIC code
        sic_code = company_data.get("sic_code")
        sector, industry = get_sector_industry_from_sic(sic_code)
        
        # Extract country from address
        address_data = company_data.get("address", {})
        country = extract_country_from_address(address_data)
        
        with conn.cursor() as cur:
            # Insert into stock_main
            insert_stock_query = sql.SQL("""
                INSERT INTO stock_main (
                    ticker, name, market, locale, primary_exchange, type, active,
                    currency_name, cik, market_cap, sector, industry, country,
                    sic_code, sic_description, total_employees,
                    share_class_shares_outstanding, weighted_shares_outstanding,
                    list_date, insert_date, last_updated_date, enabled
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (ticker) DO UPDATE SET
                    name = EXCLUDED.name,
                    market_cap = EXCLUDED.market_cap,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    country = EXCLUDED.country,
                    sic_code = EXCLUDED.sic_code,
                    sic_description = EXCLUDED.sic_description,
                    total_employees = EXCLUDED.total_employees,
                    share_class_shares_outstanding = EXCLUDED.share_class_shares_outstanding,
                    weighted_shares_outstanding = EXCLUDED.weighted_shares_outstanding,
                    last_updated_date = EXCLUDED.last_updated_date
            """)
            
            now = datetime.utcnow()
            list_date = None
            if company_data.get("list_date"):
                try:
                    list_date = datetime.strptime(company_data.get("list_date"), "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Invalid list_date format for {ticker}: {company_data.get('list_date')}")
            
            cur.execute(insert_stock_query, (
                ticker,
                stock.get("name"),
                stock.get("market"),
                stock.get("locale"),
                stock.get("primary_exchange"),
                stock.get("type"),
                stock.get("active"),
                stock.get("currency_name"),
                stock.get("cik"),
                company_data.get("market_cap"),
                sector,
                industry,
                country,
                sic_code,
                company_data.get("sic_description"),
                company_data.get("total_employees"),
                company_data.get("share_class_shares_outstanding"),
                company_data.get("weighted_shares_outstanding"),
                list_date,
                now,
                stock.get("last_updated_utc"),
                True
            ))
            
            # Insert into stock_related_tickers
            if related_tickers:
                # First, delete existing related tickers for this stock
                cur.execute("DELETE FROM stock_related_tickers WHERE stock_ticker = %s", (ticker,))
                
                insert_related_query = sql.SQL("""
                    INSERT INTO stock_related_tickers (
                        stock_ticker, related_ticker, insert_date
                    ) VALUES (%s, %s, %s)
                    ON CONFLICT (stock_ticker, related_ticker) DO UPDATE SET
                        insert_date = EXCLUDED.insert_date
                """)
                for rt in related_tickers:
                    cur.execute(insert_related_query, (ticker, rt, now))
        
        conn.commit()
        logger.info(f"Inserted stock {ticker} (sector: {sector}, industry: {industry}, country: {country}) with {len(related_tickers)} related tickers.")
    except Exception as e:
        logger.error(f"Error inserting stock {ticker}: {e}")
        conn.rollback()
        raise

def run_test_mode():
    """Run in test mode - gather and display information without database operations."""
    print("\n📊 Running in TEST MODE - No database changes will be made")
    print("=" * 60)
    
    try:
        # Fetch first batch to analyze
        print("\n🔄 Fetching first batch of stocks...")
        tickers, next_url = fetch_tickers_batch()
        
        if not tickers:
            print("❌ No stocks fetched from Polygon API")
            return
        
        print(f"✅ Fetched {len(tickers)} stocks in first batch")
        
        # Analyze sector distribution
        sector_counts = defaultdict(int)
        industry_counts = defaultdict(int)
        exchange_counts = defaultdict(int)
        sample_stocks = []
        
        print("\n🔍 Analyzing first 10 stocks in detail...")
        for i, stock in enumerate(tickers[:10]):
            ticker = stock.get("ticker")
            print(f"\n  Stock {i+1}: {ticker}")
            print(f"    Name: {stock.get('name')}")
            print(f"    Exchange: {stock.get('primary_exchange')}")
            
            # Fetch additional data
            company_data = fetch_company_data(ticker)
            if company_data:
                sic_code = company_data.get("sic_code")
                sector, industry = get_sector_industry_from_sic(sic_code)
                print(f"    SIC Code: {sic_code}")
                print(f"    Sector: {sector}")
                print(f"    Industry: {industry}")
                print(f"    Market Cap: ${company_data.get('market_cap', 'N/A'):,}" if company_data.get('market_cap') else "    Market Cap: N/A")
                
                sector_counts[sector] += 1
                industry_counts[industry] += 1
            
            exchange_counts[stock.get("primary_exchange", "Unknown")] += 1
            
            related = fetch_related_tickers(ticker)
            print(f"    Related Tickers: {len(related)}")
            
            sample_stocks.append({
                "ticker": ticker,
                "name": stock.get("name"),
                "sector": sector if company_data else "Unknown",
                "industry": industry if company_data else "Unknown"
            })
            
            time.sleep(0.1)  # Rate limiting
        
        # Summary statistics
        print("\n" + "=" * 60)
        print("📈 TEST MODE SUMMARY")
        print("=" * 60)
        
        print(f"\n🔢 Statistics from sample:")
        print(f"  Total stocks available: ~{len(tickers)} in first batch")
        print(f"  Has more pages: {'Yes' if next_url else 'No'}")
        
        print(f"\n📊 Sector Distribution (from sample):")
        for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {sector}: {count}")
        
        print(f"\n🏢 Exchange Distribution (from batch):")
        for exchange, count in sorted(exchange_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {exchange}: {count}")
        
        print("\n✅ Test completed successfully - API connections working")
        print("ℹ️  In production mode, this would:")
        print("  1. Truncate existing tables (if selected)")
        print("  2. Fetch ALL stocks from Polygon (thousands of records)")
        print("  3. Enrich each with company data and related tickers")
        print("  4. Insert into stock_main and stock_related_tickers tables")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        raise

def run_diagnostics():
    """Run diagnostic tests on API and database connections."""
    print("\n" + "=" * 60)
    print("🔧 DIAGNOSTIC MODE")
    print("=" * 60)
    
    # Test API key format
    print("\n📝 API Key Check:")
    if not POLYGON_API_KEY:
        print("   ❌ API key is empty!")
    elif len(POLYGON_API_KEY) < 20:
        print(f"   ⚠️  API key seems short: {len(POLYGON_API_KEY)} characters")
    else:
        print(f"   ✅ API key present: {POLYGON_API_KEY[:10]}...{POLYGON_API_KEY[-4:]}")
    
    # Test basic connectivity
    print("\n🌐 Basic Connectivity Test:")
    try:
        response = requests.get("https://api.polygon.io", timeout=5)
        print(f"   ✅ Can reach api.polygon.io (Status: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Cannot reach api.polygon.io: {e}")
    
    # Test API authentication
    print("\n🔑 API Authentication Test:")
    test_url = f"{BASE_URL}/v3/reference/tickers"
    try:
        response = requests.get(
            test_url,
            params={
                "apiKey": POLYGON_API_KEY,
                "limit": 1
            },
            timeout=10
        )
        print(f"   HTTP Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response has 'status': {'status' in data}")
            print(f"   Response has 'results': {'results' in data}")
            if 'results' in data:
                print(f"   Number of results: {len(data.get('results', []))}")
            print("   ✅ API authentication successful")
        elif response.status_code == 401:
            print("   ❌ Authentication failed (401) - Invalid API key")
        elif response.status_code == 403:
            print("   ❌ Forbidden (403) - Check API permissions")
        elif response.status_code == 429:
            print("   ⚠️  Rate limit exceeded (429)")
        else:
            print(f"   ⚠️  Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Error during authentication test: {e}")
    
    print("\n" + "=" * 60)

def main():
    """Main function to fetch and insert stocks."""
    print("\n" + "=" * 60)
    print("🚀 TICKSTOCK - Stock Maintenance Utility")
    print("=" * 60)
    
    # Check for diagnostic mode
    if len(sys.argv) > 1 and sys.argv[1] in ['--diagnose', '-d']:
        run_diagnostics()
        sys.exit(0)
    
    # Test connections first
    if not test_polygon_connection():
        print("\n❌ Cannot proceed without Polygon API connection")
        sys.exit(1)
    
    if not test_database_connection():
        print("\n❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Ask user if they want to run test mode
    if prompt_user("Do you want to TEST the process first? (Gather info, no DB changes)", default="y"):
        run_test_mode()
        
        # After test, ask if they want to continue with actual process
        if not prompt_user("\n🔄 Test complete. Continue with ACTUAL data load?", default="n"):
            print("👋 Exiting without making changes.")
            sys.exit(0)
    
    # Ask about truncation
    truncate_mode = prompt_user(
        "⚠️  Do you want to TRUNCATE existing tables before loading?\n"
        "   (This will DELETE all existing stock data)", 
        default="n"
    )
    
    if truncate_mode:
        if not prompt_user("⚠️  ARE YOU SURE? This will DELETE all existing stock data!", default="n"):
            truncate_mode = False
            print("ℹ️  Truncation cancelled - will use UPSERT mode instead")
    
    # Final confirmation
    print("\n" + "=" * 60)
    print("📋 READY TO EXECUTE:")
    print(f"  • Mode: {'TRUNCATE & RELOAD' if truncate_mode else 'UPSERT (preserve existing)'}")
    print(f"  • Source: Polygon.io API")
    print(f"  • Target: stock_main and stock_related_tickers tables")
    print("=" * 60)
    
    if not prompt_user("Ready to continue? This will modify the database!", default="n"):
        print("👋 Operation cancelled by user.")
        sys.exit(0)
    
    # Execute main process
    conn = None
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Connected to PostgreSQL database.")
        
        # Truncate tables if specified
        if truncate_mode:
            truncate_tables(conn)
        
        # Fetch and process tickers in batches
        next_url = None
        batch_count = 0
        total_processed = 0
        sector_summary = defaultdict(int)
        
        print("\n🔄 Starting stock data load...")
        
        while True:
            tickers, next_url = fetch_tickers_batch(next_url)
            if not tickers:
                logger.info("No more tickers to process.")
                break
            
            for stock in tickers:
                ticker = stock.get("ticker")
                logger.debug(f"Processing ticker: {ticker}")
                
                # Fetch additional data
                company_data = fetch_company_data(ticker)
                related_tickers = fetch_related_tickers(ticker)
                
                # Track sectors
                if company_data:
                    sic_code = company_data.get("sic_code")
                    sector, _ = get_sector_industry_from_sic(sic_code)
                    sector_summary[sector] += 1
                
                # Insert stock and related tickers
                insert_stock(conn, stock, company_data, related_tickers)
                total_processed += 1
                
                # Progress indicator
                if total_processed % 100 == 0:
                    print(f"  Processed {total_processed:,} stocks...")
                
                time.sleep(0.1)  # Rate limiting for per-ticker API calls
            
            batch_count += 1
            logger.info(f"Processed batch {batch_count} with {len(tickers)} tickers, total processed: {total_processed}")
            
            time.sleep(0.5)  # Rate limiting for batch API calls
            if not next_url:
                logger.info("No more batches to process.")
                break
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ LOAD COMPLETE - Summary")
        print("=" * 60)
        print(f"  Total stocks processed: {total_processed:,}")
        print(f"  Total batches: {batch_count}")
        
        print("\n📊 Sector Distribution:")
        for sector, count in sorted(sector_summary.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_processed * 100) if total_processed > 0 else 0
            print(f"  {sector:30} {count:6,} ({percentage:5.1f}%)")
        
        logger.info(f"Completed fetching and inserting {total_processed} common stocks.")
    
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"\n❌ Fatal error: {e}")
        raise
    
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")
            print("\n👋 Database connection closed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Process failed: {e}")
        sys.exit(1)