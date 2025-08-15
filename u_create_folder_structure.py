#!/usr/bin/env python3
"""
TickStock V2 Folder Structure Creation Script
Creates the new organizational structure for TickStockAppV2
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime

class FolderStructureCreator:
    def __init__(self, base_path: str = r"C:\Users\McDude\TickStockAppV2"):
        self.base_path = Path(base_path)
        self.created_folders = []
        self.errors = []
        
    def create_structure(self) -> Dict:
        """Create the complete folder structure for TickStock V2"""
        
        # Define the folder structure
        folders = [
            # Source code structure
            "src/api/rest",
            "src/api/websocket",
            "src/api/graphql",
            
            # Core business logic
            "src/core/domain",
            "src/core/services",
            "src/core/interfaces",
            
            # Infrastructure layer
            "src/infrastructure/data_sources/polygon",
            "src/infrastructure/data_sources/synthetic",
            "src/infrastructure/data_sources/alpaca",  # Future
            "src/infrastructure/data_sources/iex",      # Future
            "src/infrastructure/database/models",
            "src/infrastructure/database/repositories",
            "src/infrastructure/database/migrations",
            "src/infrastructure/messaging/publishers",
            "src/infrastructure/messaging/subscribers",
            "src/infrastructure/cache",
            
            # Processing pipeline
            "src/processing/detectors",
            "src/processing/workers",
            "src/processing/queues",
            "src/processing/pipeline",
            
            # Presentation layer
            "src/presentation/websocket",
            "src/presentation/converters",
            "src/presentation/validators",
            
            # Authentication
            "src/auth",
            
            # Monitoring
            "src/monitoring",
            
            # Shared utilities
            "src/shared/utils",
            "src/shared/constants",
            "src/shared/exceptions",
            
            # Web assets
            "web/static/css/base",
            "web/static/css/components",
            "web/static/css/layout",
            "web/static/css/utilities",
            "web/static/js/core",
            "web/static/js/components",
            "web/static/js/utils",
            "web/static/js/vendor",
            "web/static/images",
            "web/templates/layouts",
            "web/templates/components",
            "web/templates/pages",
            "web/templates/emails",
            
            # Configuration
            "config/environments",
            
            # Libraries (for third-party code)
            "libs",
            
            # Tests
            "tests/unit/core",
            "tests/unit/infrastructure",
            "tests/unit/processing",
            "tests/unit/presentation",
            "tests/integration",
            "tests/performance",
            "tests/fixtures",
            
            # Scripts
            "scripts/migration",
            "scripts/dev_tools",
            "scripts/deployment",
            "scripts/maintenance",
            
            # Documentation
            "docs/api",
            "docs/architecture",
            "docs/guides",
            
            # Docker
            "docker",
            
            # Requirements
            "requirements",
        ]
        
        print(f"Creating folder structure at: {self.base_path}")
        print("=" * 60)
        
        # Create base directory
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created base directory: {self.base_path}")
        except Exception as e:
            self.errors.append(f"Failed to create base directory: {e}")
            return self._get_summary()
        
        # Create all folders
        for folder in folders:
            folder_path = self.base_path / folder
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                self.created_folders.append(str(folder))
                print(f"✓ Created: {folder}")
            except Exception as e:
                self.errors.append(f"Failed to create {folder}: {e}")
                print(f"✗ Error creating {folder}: {e}")
        
        # Create __init__.py files for Python packages
        self._create_init_files()
        
        # Create README files for documentation
        self._create_readme_files()
        
        # Create configuration templates
        self._create_config_templates()
        
        return self._get_summary()
    
    def _create_init_files(self):
        """Create __init__.py files for all Python packages"""
        python_dirs = [
            "src",
            "src/api", "src/api/rest", "src/api/websocket", "src/api/graphql",
            "src/core", "src/core/domain", "src/core/services", "src/core/interfaces",
            "src/infrastructure", "src/infrastructure/data_sources",
            "src/infrastructure/data_sources/polygon",
            "src/infrastructure/data_sources/synthetic",
            "src/infrastructure/database", "src/infrastructure/database/models",
            "src/infrastructure/database/repositories",
            "src/infrastructure/messaging", "src/infrastructure/cache",
            "src/processing", "src/processing/detectors", "src/processing/workers",
            "src/processing/queues", "src/processing/pipeline",
            "src/presentation", "src/presentation/websocket",
            "src/presentation/converters", "src/presentation/validators",
            "src/auth", "src/monitoring", "src/shared",
            "src/shared/utils", "src/shared/constants", "src/shared/exceptions",
            "config", "config/environments",
            "tests", "tests/unit", "tests/integration", "tests/performance",
            "scripts", "scripts/migration", "scripts/dev_tools",
        ]
        
        for dir_path in python_dirs:
            init_file = self.base_path / dir_path / "__init__.py"
            try:
                init_file.touch()
                print(f"✓ Created __init__.py in {dir_path}")
            except Exception as e:
                self.errors.append(f"Failed to create __init__.py in {dir_path}: {e}")
    
    def _create_readme_files(self):
        """Create README files for documentation"""
        readme_locations = {
            "": "# TickStock V2\n\nModern real-time market data processing system.",
            "src": "# Source Code\n\nCore application source code.",
            "src/core": "# Core Business Logic\n\nDomain models and business services.",
            "src/infrastructure": "# Infrastructure Layer\n\nExternal integrations and data sources.",
            "src/processing": "# Processing Pipeline\n\nEvent detection and processing components.",
            "docs": "# Documentation\n\nComprehensive system documentation.",
            "tests": "# Test Suites\n\nUnit, integration, and performance tests.",
            "scripts": "# Utility Scripts\n\nDevelopment and deployment utilities.",
        }
        
        for location, content in readme_locations.items():
            readme_path = self.base_path / location / "README.md"
            try:
                readme_path.write_text(content)
                print(f"✓ Created README.md in {location if location else 'root'}")
            except Exception as e:
                self.errors.append(f"Failed to create README in {location}: {e}")
    
    def _create_config_templates(self):
        """Create configuration template files"""
        
        # Environment config templates
        dev_config = '''"""Development Environment Configuration"""

DEBUG = True
TESTING = False
LOG_LEVEL = "DEBUG"

# Database
DATABASE_URI = "postgresql://localhost/tickstock_dev"

# Redis
REDIS_URL = "redis://localhost:6379/0"

# API Keys (use .env for actual values)
POLYGON_API_KEY = None  # Set in .env

# WebSocket
WS_HEARTBEAT_INTERVAL = 30
WS_RECONNECT_DELAY = 5

# Processing
WORKER_POOL_MIN = 2
WORKER_POOL_MAX = 8
'''

        prod_config = '''"""Production Environment Configuration"""

DEBUG = False
TESTING = False
LOG_LEVEL = "INFO"

# Database
DATABASE_URI = None  # Set via environment variable

# Redis
REDIS_URL = None  # Set via environment variable

# API Keys
POLYGON_API_KEY = None  # Set via environment variable

# WebSocket
WS_HEARTBEAT_INTERVAL = 60
WS_RECONNECT_DELAY = 10

# Processing
WORKER_POOL_MIN = 4
WORKER_POOL_MAX = 16
'''

        # Write config files
        configs = {
            "config/environments/dev.py": dev_config,
            "config/environments/prod.py": prod_config,
        }
        
        for path, content in configs.items():
            config_path = self.base_path / path
            try:
                config_path.write_text(content)
                print(f"✓ Created config: {path}")
            except Exception as e:
                self.errors.append(f"Failed to create {path}: {e}")
        
        # Create .env.example
        env_example = '''# TickStock Environment Variables Template

# Environment
ENV=dev

# Database
DATABASE_URI=postgresql://user:pass@localhost/tickstock

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
POLYGON_API_KEY=your_polygon_api_key_here

# Flask
FLASK_SECRET_KEY=your_secret_key_here

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_password

# Twilio (SMS)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
'''
        
        env_path = self.base_path / ".env.example"
        try:
            env_path.write_text(env_example)
            print("✓ Created .env.example")
        except Exception as e:
            self.errors.append(f"Failed to create .env.example: {e}")
    
    def _get_summary(self) -> Dict:
        """Get summary of the operation"""
        return {
            "base_path": str(self.base_path),
            "folders_created": len(self.created_folders),
            "folders_list": self.created_folders,
            "errors": self.errors,
            "success": len(self.errors) == 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_summary(self, summary: Dict, filename: str = "folder_creation_summary.json"):
        """Save summary to JSON file"""
        summary_path = self.base_path / filename
        try:
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"\n✓ Summary saved to: {summary_path}")
        except Exception as e:
            print(f"✗ Failed to save summary: {e}")


def main():
    """Main execution"""
    print("TickStock V2 Folder Structure Creator")
    print("=" * 60)
    
    # Allow custom path via command line
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = r"C:\Users\McDude\TickStockAppV2"
    
    creator = FolderStructureCreator(base_path)
    summary = creator.create_structure()
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total folders created: {summary['folders_created']}")
    
    if summary['errors']:
        print(f"\nErrors encountered: {len(summary['errors'])}")
        for error in summary['errors']:
            print(f"  - {error}")
    else:
        print("\n✓ All folders created successfully!")
    
    # Save summary
    creator.save_summary(summary)
    
    return 0 if summary['success'] else 1


if __name__ == "__main__":
    sys.exit(main())