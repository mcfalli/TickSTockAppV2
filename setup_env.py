#!/usr/bin/env python3
"""
Setup environment for TickStock V2
Run this before starting the application
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

print(f"✓ Added {project_root} to PYTHONPATH")
print("You can now import modules with:")
print("  from src.core.services import MarketDataService")
print("  from config.logging_config import get_domain_logger")
