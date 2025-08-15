#!/usr/bin/env python3
"""
TickStock Dependency Creation Script
Creates additional dependencies like __init__.py files and configuration files
"""

import os
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

class DependencyCreator:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        self.created_files = []
        self.updated_files = []
        self.skipped_files = []
        
    def create_init_files(self):
        """Create __init__.py files with proper exports"""
        
        init_contents = {
            'src/__init__.py': '"""TickStock V2 - Main Application Package"""',
            
            'src/api/__init__.py': '"""API Layer"""',
            
            'src/api/rest/__init__.py': '''"""REST API Endpoints"""

from .main import *
from .api import *
from .auth import *
''',
            
            'src/core/__init__.py': '"""Core Business Logic"""',
            
            'src/core/domain/__init__.py': '''"""Domain Models and Entities"""

from .events import *
from .market import *
''',
            
            'src/core/services/__init__.py': '''"""Business Services"""

from .market_data_service import MarketDataService
from .session_manager import SessionManager
from .analytics_manager import AnalyticsManager
from .config_manager import ConfigManager
from .startup_service import StartupService
from .universe_service import TickStockUniverseManager
from .user_filters_service import UserFiltersService
from .user_settings_service import UserSettingsService
from .accumulation_manager import AccumulationManager
from .analytics_coordinator import AnalyticsCoordinator
from .universe_coordinator import UniverseCoordinator

__all__ = [
    'MarketDataService',
    'SessionManager', 
    'AnalyticsManager',
    'ConfigManager',
    'StartupService',
    'TickStockUniverseManager',
    'UserFiltersService',
    'UserSettingsService',
    'AccumulationManager',
    'AnalyticsCoordinator',
    'UniverseCoordinator'
]
''',

            'src/core/interfaces/__init__.py': '''"""Abstract Interfaces and Contracts"""

from .data_provider import DataProvider
from .data_result import DataResult

__all__ = ['DataProvider', 'DataResult']
''',

            'src/infrastructure/__init__.py': '"""Infrastructure Layer"""',

            'src/infrastructure/data_sources/__init__.py': '''"""Data Source Implementations"""

from .factory import DataProviderFactory

__all__ = ['DataProviderFactory']
''',

            'src/infrastructure/data_sources/polygon/__init__.py': '''"""Polygon Data Provider"""

from .provider import PolygonDataProvider
from .api import PolygonAPI

__all__ = ['PolygonDataProvider', 'PolygonAPI']
''',

            'src/infrastructure/data_sources/synthetic/__init__.py': '''"""Synthetic Data Provider"""

from .provider import SimulatedDataProvider
from .generator import SyntheticDataGenerator
from .loader import SyntheticDataLoader

__all__ = ['SimulatedDataProvider', 'SyntheticDataGenerator', 'SyntheticDataLoader']
''',

            'src/infrastructure/data_sources/adapters/__init__.py': '''"""Data Adapters"""

from .realtime_adapter import RealTimeDataAdapter

__all__ = ['RealTimeDataAdapter']
''',

            'src/infrastructure/database/__init__.py': '''"""Database Layer"""

from .models.base import Base, db

__all__ = ['Base', 'db']
''',

            'src/infrastructure/database/models/__init__.py': '''"""Database Models"""

from .base import Base, db
from .analytics import TickerAnalytics

__all__ = ['Base', 'db', 'MarketAnalytics']
''',

            'src/infrastructure/database/migrations/__init__.py': '"""Database Migrations"""',

            'src/infrastructure/cache/__init__.py': '''"""Cache Infrastructure"""

from .cache_control import CacheControl

__all__ = ['CacheControl']
''',

            'src/infrastructure/messaging/__init__.py': '''"""Messaging Services"""

from .email_service import EmailService
from .sms_service import SMSService

__all__ = ['EmailService', 'SMSService']
''',

            'src/processing/__init__.py': '"""Processing Pipeline"""',

            'src/processing/pipeline/__init__.py': '''"""Processing Pipeline Components"""

from .event_processor import EventProcessor
from .event_detector import EventDetector
from .tick_processor import TickProcessor

__all__ = ['EventProcessor', 'EventDetector', 'TickProcessor']
''',

            'src/processing/detectors/__init__.py': '''"""Event Detection Engines"""

from .manager import EventDetectionManager
from .highlow_detector import HighLowDetector
from .trend_detector import TrendDetector
from .surge_detector import SurgeDetector
from .buysell_tracker import BuySellMarketTracker
from .buysell_engine import BuySellTracker

__all__ = [
    'EventDetectionManager',
    'HighLowDetector',
    'TrendDetector', 
    'SurgeDetector',
    'BuySellMarketTracker',
    'BuySellTracker'
]
''',

            'src/processing/detectors/engines/__init__.py': '''"""Detection Engine Implementations"""

from .buysell_tracker import BuySellTracker
from .highlow_detector import HighLowDetector
from .surge_detector import SurgeDetector
from .trend_detector import TrendDetector

__all__ = [
    'BuySellTracker',
    'HighLowDetector',
    'SurgeDetector',
    'TrendDetector'
]
''',

            'src/processing/workers/__init__.py': '''"""Worker Pool Management"""

from .worker_pool import WorkerPoolManager

__all__ = ['WorkerPoolManager']
''',

            'src/processing/queues/__init__.py': '''"""Queue Management"""

from .priority_manager import PriorityManager
from .base_queue import BaseQueue

__all__ = ['PriorityManager', 'BaseQueue']
''',

            'src/presentation/__init__.py': '"""Presentation Layer"""',

            'src/presentation/validators/__init__.py': '''"""Input Validators"""

from .forms import *

__all__ = []
''',

            'src/presentation/converters/__init__.py': '''"""Data Converters"""

from .transport_models import *

__all__ = []
''',

            'src/presentation/websocket/__init__.py': '''"""WebSocket Communication Layer"""

from .manager import WebSocketManager
from .publisher import WebSocketPublisher
from .data_publisher import DataPublisher
from .analytics import WebSocketAnalytics
from .data_filter import WebSocketDataFilter
from .display_converter import WebSocketDisplayConverter
from .filter_cache import WebSocketFilterCache
from .statistics import WebSocketStatistics
from .universe_cache import WebSocketUniverseCache
from .polygon_client import PolygonWebSocketClient

__all__ = [
    'WebSocketManager',
    'WebSocketPublisher',
    'DataPublisher',
    'WebSocketAnalytics',
    'WebSocketDataFilter',
    'WebSocketDisplayConverter',
    'WebSocketFilterCache',
    'WebSocketStatistics',
    'WebSocketUniverseCache',
    'PolygonWebSocketClient'
]
''',

            'src/auth/__init__.py': '''"""Authentication and Authorization"""

from .authentication import AuthenticationManager
from .registration import RegistrationManager
from .session import SessionManager

__all__ = [
    'AuthenticationManager',
    'RegistrationManager',
    'SessionManager'
]
''',

            'src/monitoring/__init__.py': '''"""System Monitoring and Observability"""

from .system_monitor import SystemMonitor
from .metrics_collector import MetricsCollector
from .performance_monitor import PerformanceMonitor
from .tracer import Tracer
from .health_monitor import HealthMonitor
from .query_debug_logger import QueryDebugLogger

__all__ = [
    'SystemMonitor',
    'MetricsCollector',
    'PerformanceMonitor',
    'Tracer',
    'HealthMonitor',
    'QueryDebugLogger'
]
''',

            'src/shared/__init__.py': '"""Shared Resources"""',

            'src/shared/utils/__init__.py': '''"""Shared Utility Functions"""

from .general import *
from .validation import *
from .event_factory import EventFactory
from .app_utils import *
from .market_utils import *

__all__ = ['EventFactory']
''',
        }
        
        print("Creating __init__.py files with exports...")
        print("=" * 60)
        
        for filepath, content in init_contents.items():
            full_path = self.dest_dir / filepath
            
            # Check if file already exists
            if full_path.exists():
                existing_content = full_path.read_text()
                if existing_content.strip() and existing_content != content:
                    self.skipped_files.append(filepath)
                    print(f"⚠ Skipped (exists): {filepath}")
                    continue
            
            # Create parent directory if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                full_path.write_text(content, encoding='utf-8')
                self.created_files.append(filepath)
                print(f"✓ Created: {filepath}")
            except Exception as e:
                print(f"✗ Error creating {filepath}: {e}")
    
    def create_requirements_files(self):
        """Create split requirements files"""
        
        base_requirements = """# Base requirements for TickStock V2
Flask==2.3.3
Flask-SocketIO==5.3.4
Flask-WTF==1.1.1
Flask-Login==0.6.2
Flask-Mail==0.9.1
Flask-Migrate==4.0.4
SQLAlchemy==2.0.20
psycopg2-binary==2.9.7
python-dotenv==1.0.0
python-socketio==5.9.0
eventlet==0.33.3
redis==4.6.0
celery==5.3.1
requests==2.31.0
pandas==2.0.3
numpy==1.24.3
websocket-client==1.6.1
polygon-api-client==1.12.0
twilio==8.5.0
email-validator==2.0.0
phonenumbers==8.13.18
pytz==2023.3
python-dateutil==2.8.2
prometheus-client==0.17.1
alembic==1.11.3
"""

        dev_requirements = """# Development requirements
-r base.txt

pytest==7.4.0
pytest-cov==4.1.0
pytest-asyncio==0.21.1
black==23.7.0
flake8==6.1.0
mypy==1.5.0
ipython==8.14.0
jupyter==1.0.0
pre-commit==3.3.3
"""

        prod_requirements = """# Production requirements
-r base.txt

gunicorn==21.2.0
supervisor==4.2.5
sentry-sdk==1.29.2
datadog==0.47.0
"""

        requirements = {
            'requirements/base.txt': base_requirements,
            'requirements/dev.txt': dev_requirements,
            'requirements/prod.txt': prod_requirements,
        }
        
        print("\nCreating requirements files...")
        print("=" * 60)
        
        for filepath, content in requirements.items():
            full_path = self.dest_dir / filepath
            
            if full_path.exists():
                self.skipped_files.append(filepath)
                print(f"⚠ Skipped (exists): {filepath}")
                continue
                
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                full_path.write_text(content, encoding='utf-8')
                self.created_files.append(filepath)
                print(f"✓ Created: {filepath}")
            except Exception as e:
                print(f"✗ Error creating {filepath}: {e}")
    
    def create_env_example(self):
        """Create .env.example file"""
        
        env_example = """# TickStock V2 Environment Configuration Example
# Copy this file to .env and fill in your values

# Environment
ENV=development
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URI=postgresql://username:password@localhost:5432/tickstock
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0

# Polygon API
POLYGON_API_KEY=your-polygon-api-key
USE_POLYGON_API=True
USE_SYNTHETIC_DATA=False

# Email Settings
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Twilio Settings
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

# Session Settings
SESSION_TYPE=redis
SESSION_PERMANENT=False
SESSION_USE_SIGNER=True
SESSION_KEY_PREFIX=tickstock:

# CORS Settings
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# Monitoring
PROMETHEUS_ENABLED=True
TRACER_ENABLED=True
LOG_LEVEL=INFO
"""
        
        print("\nCreating .env.example...")
        print("=" * 60)
        
        env_path = self.dest_dir / '.env.example'
        
        if env_path.exists():
            self.skipped_files.append('.env.example')
            print(f"⚠ Skipped (exists): .env.example")
        else:
            try:
                env_path.write_text(env_example, encoding='utf-8')
                self.created_files.append('.env.example')
                print(f"✓ Created: .env.example")
            except Exception as e:
                print(f"✗ Error creating .env.example: {e}")
    
    def create_all_dependencies(self):
        """Create all dependency files"""
        self.create_init_files()
        self.create_requirements_files()
        self.create_env_example()
        
        return {
            'created_files': self.created_files,
            'updated_files': self.updated_files,
            'skipped_files': self.skipped_files,
            'total_created': len(self.created_files),
            'total_updated': len(self.updated_files),
            'total_skipped': len(self.skipped_files)
        }
    
    def save_report(self, results: Dict):
        """Save dependency creation report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'created_files': self.created_files,
            'skipped_files': self.skipped_files
        }
        
        report_path = self.dest_dir / 'dependency_creation_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Report saved to: {report_path}")
        
        # Create readable report
        readable_path = self.dest_dir / 'dependency_creation_report.txt'
        with open(readable_path, 'w', encoding='utf-8') as f:
            f.write("DEPENDENCY CREATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp: {report['timestamp']}\n")
            f.write(f"Files created: {results['total_created']}\n")
            f.write(f"Files skipped: {results['total_skipped']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            
            if self.created_files:
                f.write("CREATED FILES:\n")
                f.write("-" * 40 + "\n")
                for file in sorted(self.created_files):
                    f.write(f"  - {file}\n")
            
            if self.skipped_files:
                f.write("\n" + "=" * 80 + "\n")
                f.write("SKIPPED FILES (already exist):\n")
                f.write("-" * 40 + "\n")
                for file in sorted(self.skipped_files):
                    f.write(f"  - {file}\n")
        
        print(f"✓ Readable report saved to: {readable_path}")


def main():
    """Main execution"""
    print("TickStock Dependency Creation")
    print("=" * 60)
    
    creator = DependencyCreator()
    results = creator.create_all_dependencies()
    
    print("\n" + "=" * 60)
    print("CREATION SUMMARY")
    print("=" * 60)
    print(f"Files created: {results['total_created']}")
    print(f"Files updated: {results['total_updated']}")
    print(f"Files skipped: {results['total_skipped']}")
    
    creator.save_report(results)
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. Test imports: python -c \"from src.core.services import MarketDataService\"")
    print("2. Run the application: python src/app.py")
    print("3. Run tests: pytest tests/")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())