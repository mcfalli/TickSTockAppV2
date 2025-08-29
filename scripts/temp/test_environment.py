#!/usr/bin/env python3
"""
Simple script to test the Python environment and required packages
"""

import sys
import os

def main():
    print("=== Python Environment Test ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Test required imports
    imports_to_test = [
        'pandas',
        'psycopg2', 
        'requests',
        'dotenv'
    ]
    
    print("\n=== Package Import Test ===")
    for package in imports_to_test:
        try:
            if package == 'dotenv':
                from dotenv import load_dotenv
                print(f"✓ {package}: OK")
            elif package == 'psycopg2':
                import psycopg2
                print(f"✓ {package}: OK") 
            else:
                exec(f"import {package}")
                print(f"✓ {package}: OK")
        except ImportError as e:
            print(f"✗ {package}: MISSING - {e}")
    
    print("\n=== Environment Variables ===")
    database_uri = os.getenv('DATABASE_URI')
    polygon_key = os.getenv('POLYGON_API_KEY')
    
    print(f"DATABASE_URI: {'Set' if database_uri else 'Not set'}")
    print(f"POLYGON_API_KEY: {'Set' if polygon_key else 'Not set'}")
    
    if database_uri:
        print("✓ Ready for database operations")
    else:
        print("✗ DATABASE_URI not found")
        
    print("\n=== Recommendation ===")
    if sys.executable.find('venv') != -1:
        print("✓ Using virtual environment")
    else:
        print("✗ NOT using virtual environment!")
        print("  Please run: C:\\Users\\McDude\\TickStockAppV2\\venv\\Scripts\\Activate.ps1")

if __name__ == '__main__':
    main()