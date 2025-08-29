#!/usr/bin/env python3
"""
Test if login route is accessible
"""

import requests

try:
    # Test the login route directly
    response = requests.get('http://localhost:5000/login', timeout=5)
    print(f"Login route status: {response.status_code}")
    if response.status_code == 200:
        print("Login route is working!")
        print(f"Content length: {len(response.text)}")
        print(f"First 200 chars: {response.text[:200]}")
    else:
        print(f"Login route returned: {response.status_code}")
        print(f"Response: {response.text}")
        
    # Test if any routes are working
    print("\n=== Testing other routes ===")
    test_routes = ['/health', '/terms', '/privacy']
    for route in test_routes:
        try:
            resp = requests.get(f'http://localhost:5000{route}', timeout=2)
            print(f"{route}: {resp.status_code}")
        except Exception as e:
            print(f"{route}: Error - {e}")
            
except Exception as e:
    print(f"Error testing login route: {e}")
    print("Is your Flask server running on localhost:5000?")