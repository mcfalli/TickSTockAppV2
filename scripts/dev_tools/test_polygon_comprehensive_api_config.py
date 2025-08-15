"""
Comprehensive test script that checks:
1. Environment variable loading
2. Config parsing
3. Polygon API connection
4. Data provider factory behavior
"""
import os
import sys
import logging
import requests
import json
import traceback

# Import the ConfigManager
from src.core.services.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api-test")

print("\n===== COMPREHENSIVE POLYGON API TEST =====\n")

# Step 1: Configuration Loading
print("STEP 1: CONFIGURATION LOADING\n")

# Initialize ConfigManager
config_manager = ConfigManager()
config_manager.load_from_env()
config = config_manager.get_config()
config_manager.validate_config()

# Extract key configuration values
api_key = config.get('POLYGON_API_KEY')
use_polygon = config.get('USE_POLYGON_API')

print(f"USE_POLYGON_API config value: {use_polygon}")
print(f"POLYGON_API_KEY config value: {'[SET]' if api_key else '[NOT SET]'}")

if not api_key:
    print("ERROR: No API key found in configuration")
    print("Make sure POLYGON_API_KEY is set in your .env file")
    sys.exit(1)

# Step 2: Config Validation
print("\nSTEP 2: CONFIG VALIDATION\n")

# Check config types and values
print(f"USE_POLYGON_API type: {type(use_polygon).__name__}, value: {use_polygon}")
print(f"Other relevant config values:")
print(f"  - MARKET_TIMEZONE: {config.get('MARKET_TIMEZONE')}")
print(f"  - UPDATE_INTERVAL: {config.get('UPDATE_INTERVAL')}")
print(f"  - USE_SYNTHETIC_DATA: {config.get('USE_SYNTHETIC_DATA')}")

# Step 3: Direct API Test
print("\nSTEP 3: DIRECT API TEST\n")

# Base URL
base_url = "https://api.polygon.io"

# Test endpoint
endpoint = "/v1/marketstatus/now"
url = f"{base_url}{endpoint}"
params = {'apiKey': api_key}

print(f"Testing API endpoint: {url}")
print(f"Using API key starting with: {api_key[:4]}..." if api_key else "No API key available")

try:
    response = requests.get(url, params=params, timeout=10)
    
    print(f"Status code: {response.status_code}")
    print(f"Rate limit remaining: {response.headers.get('X-Ratelimit-Remaining', 'N/A')}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response data: {json.dumps(data, indent=2)}")
        print("\nSUCCESS: API connection successful!")
    elif response.status_code == 401 or response.status_code == 403:
        print("\nERROR: Authentication failed - check your API key")
        print(f"Response: {response.text}")
    else:
        print(f"\nWARNING: Unexpected status code {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"\nERROR: Exception occurred while testing API: {str(e)}")

# Step 4: Test DataProviderFactory
print("\nSTEP 4: TESTING RELEVANT MODULES\n")

try:
    print("Trying to import data_provider_factory...")
    from src.infrastructure.data_sources.factory import DataProviderFactory
    print("SUCCESS: DataProviderFactory imported")
    
    print("\nTrying to import polygon_data_provider...")
    from src.infrastructure.data_sources.polygon.provider import PolygonDataProvider
    print("SUCCESS: PolygonDataProvider imported")
    
    print("\nUsing DataProviderFactory with loaded config...")
    try:
        # Use the config from ConfigManager
        provider = DataProviderFactory.get_provider(config)
        provider_type = provider.__class__.__name__
        print(f"Provider created: {provider_type}")
        
        # Test availability regardless of provider type
        print("Testing is_available() method...")
        is_available = provider.is_available()
        print(f"is_available() returned: {is_available}")
        
        # If we got SimulatedDataProvider despite asking for Polygon
        if not use_polygon and provider_type == 'SimulatedDataProvider':
            print("NOTE: Using SimulatedDataProvider as configured")
        elif use_polygon and provider_type != 'PolygonDataProvider':
            print(f"WARNING: Received {provider_type} despite USE_POLYGON_API=True")
            
            # Try PolygonDataProvider directly
            print("\nTesting PolygonDataProvider directly:")
            polygon_provider = PolygonDataProvider(config)
            polygon_available = polygon_provider.is_available()
            print(f"Direct PolygonDataProvider.is_available() returned: {polygon_available}")
            
    except Exception as e:
        print(f"Error creating provider: {e}")
        print(traceback.format_exc())
    
except ImportError as e:
    print(f"ImportError: {str(e)}")
    print("Some modules are not available in this context. Skip DataProviderFactory test.")
except Exception as e:
    print(f"Unexpected error during module testing: {str(e)}")
    print(traceback.format_exc())

print("\n===== TEST COMPLETE =====")