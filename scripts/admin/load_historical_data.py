#!/usr/bin/env python3
"""
Clean wrapper for historical data loader - suppresses eventlet warnings
Usage: python load_historical_data.py --summary
"""

import os
import sys
import warnings

# Suppress eventlet and other warnings for cleaner output
warnings.filterwarnings('ignore', message='.*RLock.*not greened.*')
warnings.filterwarnings('ignore', module='eventlet')

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import and run the historical loader
if __name__ == '__main__':
    from src.data.historical_loader import main
    main()