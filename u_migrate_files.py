#!/usr/bin/env python3
"""
TickStock File Migration Mapper
Maps all source files from TickStockApp to their new locations in TickStockAppV2
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import shutil

class FileMigrationMapper:
    def __init__(self, source_dir: str = r"C:\Users\McDude\TickStockApp",
                 dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.mappings = []
        self.unmapped_files = []
        self.stats = {
            'total_files': 0,
            'mapped_files': 0,
            'unmapped_files': 0,
            'directories_created': 0
        }
        
    def create_mapping(self) -> Dict:
        """Create complete file mapping from source to destination"""
        
        # Define mapping rules
        mapping_rules = {
            # Main application files
            'app.py': 'src/app.py',
            'app_startup.py': 'src/core/services/startup_service.py',
            'app_routes_main.py': 'src/api/rest/main.py',
            'app_routes_api.py': 'src/api/rest/api.py',
            'app_routes_auth.py': 'src/api/rest/auth.py',
            'app_forms.py': 'src/presentation/validators/forms.py',
            'app_utils.py': 'src/shared/utils/app_utils.py',
            'market_utils.py': 'src/shared/utils/market_utils.py',
            
            # Configuration files
            '.env': '.env',
            'requirements.txt': 'requirements/base.txt',
            'pytest.ini': 'pytest.ini',
            'docker-compose.yml': 'docker/docker-compose.yml',
            'Dockerfile': 'docker/Dockerfile',
            'nginx.conf': 'docker/nginx.conf',
            'prometheus.yml': 'config/prometheus.yml',
            'LICENSE.txt': 'LICENSE.txt',
            'package.json': 'web/package.json',
            'package-lock.json': 'web/package-lock.json',
            'component_actions.json': 'config/component_actions.json',
            
            # Authentication module
            'auth/authentication.py': 'src/auth/authentication.py',
            'auth/registration.py': 'src/auth/registration.py',
            'auth/session.py': 'src/auth/session.py',
            'auth/__init__.py': 'src/auth/__init__.py',
            
            # Configuration module
            'config/app_config.py': 'config/app_config.py',
            'config/logging_config.py': 'config/logging_config.py',
            'config/cache_control.py': 'src/infrastructure/cache/cache_control.py',
            'config/config_manager.py': 'src/core/services/config_manager.py',
            'config/__init__.py': 'config/__init__.py',
            
            # Classes/Domain models
            'classes/events/base.py': 'src/core/domain/events/base.py',
            'classes/events/control.py': 'src/core/domain/events/control.py',
            'classes/events/highlow.py': 'src/core/domain/events/highlow.py',
            'classes/events/surge.py': 'src/core/domain/events/surge.py',
            'classes/events/trend.py': 'src/core/domain/events/trend.py',
            'classes/events/__init__.py': 'src/core/domain/events/__init__.py',
            
            'classes/market/state.py': 'src/core/domain/market/state.py',
            'classes/market/tick.py': 'src/core/domain/market/tick.py',
            'classes/market/__init__.py': 'src/core/domain/market/__init__.py',
            
            'classes/processing/queue.py': 'src/processing/queues/base_queue.py',
            'classes/processing/__init__.py': 'src/processing/queues/__init__.py',
            
            'classes/analytics/model.py': 'src/infrastructure/database/models/analytics.py',
            'classes/analytics/__init__.py': 'src/infrastructure/database/models/__init__.py',
            
            'classes/transport/models.py': 'src/presentation/converters/transport_models.py',
            'classes/transport/__init__.py': 'src/presentation/converters/__init__.py',
            
            # Database
            'database/model.py': 'src/infrastructure/database/models/base.py',
            'database/model_migrations_run.py': 'src/infrastructure/database/migrations/run_migrations.py',
            'database/__init__.py': 'src/infrastructure/database/__init__.py',
            
            # Data providers
            'data_providers/base/data_provider.py': 'src/core/interfaces/data_provider.py',
            'data_providers/data_provider_factory.py': 'src/infrastructure/data_sources/factory.py',
            'data_providers/polygon/polygon_data_provider.py': 'src/infrastructure/data_sources/polygon/provider.py',
            'data_providers/simulated/simulated_data_provider.py': 'src/infrastructure/data_sources/synthetic/provider.py',
            'data_providers/real_time_data_adapter.py': 'src/infrastructure/data_sources/adapters/realtime_adapter.py',
            'data_providers/synthetic_data_adapter.py': 'src/infrastructure/data_sources/synthetic/adapter.py',
            'data_providers/__init__.py': 'src/infrastructure/data_sources/__init__.py',
            
            # Market data service
            'market_data_service/core_service.py': 'src/core/services/market_data_service.py',
            'market_data_service/data_publisher.py': 'src/presentation/websocket/data_publisher.py',
            'market_data_service/event_processor.py': 'src/processing/pipeline/event_processor.py',
            'market_data_service/tick_processor.py': 'src/processing/pipeline/tick_processor.py',
            'market_data_service/__init__.py': 'src/core/services/__init__.py',
            
            # Event detection
            'event_detection/event_detection_manager.py': 'src/processing/detectors/manager.py',
            'event_detection/event_detector_util.py': 'src/processing/detectors/utils.py',
            'event_detection/buysell_market_tracker.py': 'src/processing/detectors/buysell_tracker.py',
            'event_detection/engines/highlow_detector.py': 'src/processing/detectors/highlow_detector.py',
            'event_detection/engines/surge_detector.py': 'src/processing/detectors/surge_detector.py',
            'event_detection/engines/trend_detector.py': 'src/processing/detectors/trend_detector.py',
            'event_detection/engines/buysell_tracker.py': 'src/processing/detectors/buysell_engine.py',
            'event_detection/__init__.py': 'src/processing/detectors/__init__.py',
            
            # Processing
            'processing/event_detector.py': 'src/processing/pipeline/event_detector.py',
            'processing/priority_manager.py': 'src/processing/queues/priority_manager.py',
            'processing/worker_pool_manager.py': 'src/processing/workers/pool_manager.py',
            'processing/__init__.py': 'src/processing/__init__.py',
            
            # Data flow
            'data_flow/metrics_collector.py': 'src/monitoring/metrics_collector.py',
            'data_flow/performance_monitor.py': 'src/monitoring/performance_monitor.py',
            'data_flow/session_manager.py': 'src/core/services/session_manager.py',
            'data_flow/__init__.py': 'src/monitoring/__init__.py',
            
            # Services
            'services/email_manager.py': 'src/infrastructure/messaging/email_service.py',
            'services/sms_manager.py': 'src/infrastructure/messaging/sms_service.py',
            'services/tickstock_universe_manager.py': 'src/core/services/universe_service.py',
            'services/user_filters_service.py': 'src/core/services/user_filters_service.py',
            'services/user_settings_service.py': 'src/core/services/user_settings_service.py',
            'services/__init__.py': 'src/core/services/__init__.py',
            
            # Universe management
            'universe/core_universe_manager.py': 'src/core/services/universe/core_manager.py',
            'universe/subscription_manager.py': 'src/core/services/universe/subscription_manager.py',
            'universe/user_universe_manager.py': 'src/core/services/universe/user_manager.py',
            'universe/universe_analytics.py': 'src/core/services/universe/analytics.py',
            'universe/__init__.py': 'src/core/services/universe/__init__.py',
            
            # Session accumulation
            'session_accumulation/accumulation_manager.py': 'src/core/services/accumulation_manager.py',
            'session_accumulation/__init__.py': 'src/core/services/__init__.py',
            
            # Market analytics
            'market_analytics/analytics_manager.py': 'src/core/services/analytics_manager.py',
            'market_analytics/__init__.py': 'src/core/services/__init__.py',
            
            # WebSocket
            'websocket/web_socket_manager.py': 'src/presentation/websocket/manager.py',
            'websocket/websocket_publisher.py': 'src/presentation/websocket/publisher.py',
            'websocket/websocket_analytics.py': 'src/presentation/websocket/analytics.py',
            'websocket/websocket_data_filter.py': 'src/presentation/websocket/data_filter.py',
            'websocket/websocket_display.py': 'src/presentation/websocket/display_converter.py',
            'websocket/websocket_filter_cache.py': 'src/presentation/websocket/filter_cache.py',
            'websocket/websocket_universe_cache.py': 'src/presentation/websocket/universe_cache.py',
            'websocket/websocket_statistics.py': 'src/presentation/websocket/statistics.py',
            'websocket/polygon_websocket_client.py': 'src/infrastructure/data_sources/polygon/websocket_client.py',
            'websocket/__init__.py': 'src/presentation/websocket/__init__.py',
            
            # Monitoring
            'monitoring/monitoring.py': 'src/monitoring/system_monitor.py',
            'monitoring/tracer.py': 'src/monitoring/tracer.py',
            'monitoring/__init__.py': 'src/monitoring/__init__.py',
            
            # Utils
            'utils/event_factory.py': 'src/shared/utils/event_factory.py',
            'utils/utils.py': 'src/shared/utils/general.py',
            'utils/validation.py': 'src/shared/utils/validation.py',
            'utils/__init__.py': 'src/shared/utils/__init__.py',
            
            # Dev tools -> Scripts
            'dev_tools/util_create_project_structure_documentation.py': 'scripts/dev_tools/create_structure_docs.py',
            'dev_tools/util_code_scan_unused_code.py': 'scripts/dev_tools/scan_unused_code.py',
            
            # Migrations
            'migrations/versions/eaf466e1159c_initial_migration_baseline_schema.py': 
                'src/infrastructure/database/migrations/versions/001_initial_schema.py',
        }
        
        # Process static files
        static_mappings = {
            'static/css/': 'web/static/css/',
            'static/js/': 'web/static/js/',
            'static/images/': 'web/static/images/',
            'static/favicon.ico': 'web/static/favicon.ico',
        }
        
        # Process template files
        template_mappings = {
            'templates/': 'web/templates/pages/',
        }
        
        # Process test files
        test_mappings = {
            'tests/test_trace_': 'tests/integration/trace/',
            'tests/test_': 'tests/unit/',
            'tests/trace_': 'tests/fixtures/trace/',
            'tests/util_': 'scripts/dev_tools/',
            'tests/commands.txt': 'tests/fixtures/commands.txt',
        }
        
        print("Creating file migration mapping...")
        print("=" * 60)
        
        # Scan all files in source directory
        for root, dirs, files in os.walk(self.source_dir):
            # Skip certain directories
            skip_dirs = {'.git', '__pycache__', 'venv', '.venv', 'logs', 'node_modules'}
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                self.stats['total_files'] += 1
                source_path = Path(root) / file
                relative_path = source_path.relative_to(self.source_dir)
                relative_str = str(relative_path).replace('\\', '/')
                
                mapped = False
                
                # Check direct mappings first
                if relative_str in mapping_rules:
                    dest_path = self.dest_dir / mapping_rules[relative_str]
                    self.mappings.append({
                        'source': str(source_path),
                        'dest': str(dest_path),
                        'relative_source': relative_str,
                        'relative_dest': mapping_rules[relative_str]
                    })
                    mapped = True
                    self.stats['mapped_files'] += 1
                
                # Check static files
                elif relative_str.startswith('static/'):
                    if relative_str.startswith('static/css/'):
                        # Organize CSS files
                        if 'base' in file or 'reset' in file or 'variables' in file:
                            dest = f"web/static/css/base/{file}"
                        elif 'component' in file or 'modal' in file or 'gauge' in file:
                            dest = f"web/static/css/components/{file}"
                        elif 'layout' in file or 'grid' in file:
                            dest = f"web/static/css/layout/{file}"
                        else:
                            dest = f"web/static/css/utilities/{file}"
                    elif relative_str.startswith('static/js/'):
                        # Organize JS files
                        if 'app-core' in file or 'app-' in file:
                            dest = f"web/static/js/core/{file}"
                        elif 'lib' in file or 'vendor' in file:
                            dest = f"web/static/js/vendor/{file}"
                        else:
                            dest = f"web/static/js/utils/{file}"
                    else:
                        dest = f"web/{relative_str}"
                    
                    dest_path = self.dest_dir / dest
                    self.mappings.append({
                        'source': str(source_path),
                        'dest': str(dest_path),
                        'relative_source': relative_str,
                        'relative_dest': dest
                    })
                    mapped = True
                    self.stats['mapped_files'] += 1
                
                # Check template files
                elif relative_str.startswith('templates/'):
                    if 'email' in file:
                        dest = f"web/templates/emails/{file}"
                    elif 'layout' in file or 'base' in file:
                        dest = f"web/templates/layouts/{file}"
                    else:
                        dest = f"web/templates/pages/{file}"
                    
                    dest_path = self.dest_dir / dest
                    self.mappings.append({
                        'source': str(source_path),
                        'dest': str(dest_path),
                        'relative_source': relative_str,
                        'relative_dest': dest
                    })
                    mapped = True
                    self.stats['mapped_files'] += 1
                
                # Check test files
                elif relative_str.startswith('tests/'):
                    if 'trace' in file:
                        if file.startswith('test_'):
                            dest = f"tests/integration/trace/{file}"
                        else:
                            dest = f"tests/fixtures/trace/{file}"
                    elif file.startswith('test_'):
                        dest = f"tests/unit/{file}"
                    elif file.startswith('util_'):
                        dest = f"scripts/dev_tools/{file}"
                    else:
                        dest = f"tests/fixtures/{file}"
                    
                    dest_path = self.dest_dir / dest
                    self.mappings.append({
                        'source': str(source_path),
                        'dest': str(dest_path),
                        'relative_source': relative_str,
                        'relative_dest': dest
                    })
                    mapped = True
                    self.stats['mapped_files'] += 1
                
                # Track unmapped files
                if not mapped and not file.endswith('.pyc'):
                    self.unmapped_files.append(relative_str)
                    self.stats['unmapped_files'] += 1
        
        return self._create_summary()
    
    def _create_summary(self) -> Dict:
        """Create mapping summary"""
        return {
            'source_dir': str(self.source_dir),
            'dest_dir': str(self.dest_dir),
            'stats': self.stats,
            'mappings': self.mappings,
            'unmapped_files': self.unmapped_files,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_mapping(self, filename: str = "migration_mapping.json"):
        """Save mapping to JSON file"""
        mapping_data = self.create_mapping()
        
        # Save to destination directory
        output_path = self.dest_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(mapping_data, f, indent=2)
        
        print(f"\n✓ Mapping saved to: {output_path}")
        
        # Also create a human-readable version
        readable_path = self.dest_dir / "migration_mapping_readable.txt"
        with open(readable_path, 'w') as f:
            f.write("FILE MIGRATION MAPPING\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Source: {self.source_dir}\n")
            f.write(f"Destination: {self.dest_dir}\n")
            f.write(f"Total files: {self.stats['total_files']}\n")
            f.write(f"Mapped files: {self.stats['mapped_files']}\n")
            f.write(f"Unmapped files: {self.stats['unmapped_files']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            
            f.write("MAPPED FILES:\n")
            f.write("-" * 40 + "\n")
            for mapping in self.mappings:
                f.write(f"{mapping['relative_source']}\n")
                f.write(f"  → {mapping['relative_dest']}\n\n")
            
            if self.unmapped_files:
                f.write("\n" + "=" * 80 + "\n")
                f.write("UNMAPPED FILES (need manual review):\n")
                f.write("-" * 40 + "\n")
                for file in self.unmapped_files:
                    f.write(f"  - {file}\n")
        
        print(f"✓ Readable mapping saved to: {readable_path}")
        
        return mapping_data
    
    def execute_migration(self, dry_run: bool = True):
        """Execute the file migration"""
        if not self.mappings:
            self.create_mapping()
        
        print(f"\n{'DRY RUN' if dry_run else 'EXECUTING'} MIGRATION")
        print("=" * 60)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for mapping in self.mappings:
            source = Path(mapping['source'])
            dest = Path(mapping['dest'])
            
            if dry_run:
                if source.exists():
                    print(f"✓ Would copy: {mapping['relative_source']} → {mapping['relative_dest']}")
                    success_count += 1
                else:
                    print(f"✗ Source not found: {mapping['relative_source']}")
                    error_count += 1
            else:
                try:
                    if source.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, dest)
                        print(f"✓ Copied: {mapping['relative_source']} → {mapping['relative_dest']}")
                        success_count += 1
                    else:
                        print(f"✗ Source not found: {mapping['relative_source']}")
                        error_count += 1
                        errors.append(f"Source not found: {mapping['relative_source']}")
                except Exception as e:
                    print(f"✗ Error copying {mapping['relative_source']}: {e}")
                    error_count += 1
                    errors.append(f"Error copying {mapping['relative_source']}: {e}")
        
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Files processed: {success_count + error_count}")
        print(f"Successful: {success_count}")
        print(f"Errors: {error_count}")
        
        if self.unmapped_files:
            print(f"\nUnmapped files requiring manual review: {len(self.unmapped_files)}")
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors,
            'dry_run': dry_run
        }


def main():
    """Main execution"""
    import sys
    
    print("TickStock File Migration Mapper")
    print("=" * 60)
    
    # Parse arguments
    dry_run = '--execute' not in sys.argv
    
    # Create mapper
    mapper = FileMigrationMapper()
    
    # Create and save mapping
    mapping_data = mapper.save_mapping()
    
    print("\n" + "=" * 60)
    print("MAPPING SUMMARY")
    print("=" * 60)
    print(f"Total files found: {mapper.stats['total_files']}")
    print(f"Files mapped: {mapper.stats['mapped_files']}")
    print(f"Files needing manual review: {mapper.stats['unmapped_files']}")
    
    if mapper.unmapped_files:
        print("\nUnmapped files (first 10):")
        for file in mapper.unmapped_files[:10]:
            print(f"  - {file}")
        if len(mapper.unmapped_files) > 10:
            print(f"  ... and {len(mapper.unmapped_files) - 10} more")
    
    # Ask about migration execution
    if dry_run:
        print("\nTo execute migration, run with --execute flag")
        print("Example: python file_migration_mapper.py --execute")
    else:
        response = input("\nProceed with migration? (yes/no): ")
        if response.lower() == 'yes':
            mapper.execute_migration(dry_run=False)
        else:
            print("Migration cancelled")
    
    return 0


if __name__ == "__main__":
    main()