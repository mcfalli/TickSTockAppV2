#!/usr/bin/env python3
"""
TickStock Import Reference Updater - Corrected Version
Updates import statements to match the new folder structure
Includes all WebSocket handler mappings and other corrections
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set
import ast

class ImportUpdater:
    def __init__(self, dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.dest_dir = Path(dest_dir)
        self.import_mappings = self._create_import_mappings()
        self.updated_files = []
        self.errors = []
        
    def _create_import_mappings(self) -> Dict[str, str]:
        """Create mapping of old imports to new imports"""
        return {
            # Auth imports
            'from src.auth.': 'from src.auth.',
            'import src.auth.': 'import src.auth.',
            'import src.auth': 'import src.auth',
            
            # Classes imports -> Domain models
            'from src.core.domain.events': 'from src.core.domain.events',
            'from src.core.domain.market': 'from src.core.domain.market',
            'from src.processing.queues': 'from src.processing.queues',
            'from src.infrastructure.database.models': 'from src.infrastructure.database.models',
            'from src.presentation.converters': 'from src.presentation.converters',
            'import src.core.domain.': 'import src.core.domain.',
            
            # Config imports
            'from config.app_config': 'from config.app_config',
            'from config.logging_config': 'from config.logging_config',
            'from src.infrastructure.cache.cache_control': 'from src.infrastructure.cache.cache_control',
            'from src.core.services.config_manager': 'from src.core.services.config_manager',
            
            # Database imports
            'from src.infrastructure.database.models.base': 'from src.infrastructure.database.models.base',
            'import src.infrastructure.database.': 'import src.infrastructure.database.',
            'from src.infrastructure.database': 'from src.infrastructure.database',
            
            # Data providers
            'from src.core.interfaces.data_provider': 'from src.core.interfaces.data_provider',
            'from src.core.interfaces.data_result': 'from src.core.interfaces.data_result',
            'from src.core.interfaces': 'from src.core.interfaces',
            'from src.infrastructure.data_sources.polygon.provider': 'from src.infrastructure.data_sources.polygon.provider',
            'from src.infrastructure.data_sources.polygon.api': 'from src.infrastructure.data_sources.polygon.api',
            'from src.infrastructure.data_sources.polygon': 'from src.infrastructure.data_sources.polygon',
            'from src.infrastructure.data_sources.synthetic.provider': 'from src.infrastructure.data_sources.synthetic.provider',
            'from src.infrastructure.data_sources.synthetic.generator': 'from src.infrastructure.data_sources.synthetic.generator',
            'from src.infrastructure.data_sources.synthetic.loader': 'from src.infrastructure.data_sources.synthetic.loader',
            'from src.infrastructure.data_sources.synthetic': 'from src.infrastructure.data_sources.synthetic',
            'from src.infrastructure.data_sources.factory': 'from src.infrastructure.data_sources.factory',
            'from src.infrastructure.data_sources.adapters.realtime_adapter': 'from src.infrastructure.data_sources.adapters.realtime_adapter',
            'from src.infrastructure.data_sources': 'from src.infrastructure.data_sources',
            
            # Market data service
            'from src.core.services.market_data_service': 'from src.core.services.market_data_service',
            'from src.presentation.websocket.data_publisher': 'from src.presentation.websocket.data_publisher',
            'from src.processing.pipeline.event_processor': 'from src.processing.pipeline.event_processor',
            'from src.core.services.analytics_coordinator': 'from src.core.services.analytics_coordinator',
            'from src.monitoring.health_monitor': 'from src.monitoring.health_monitor',
            'from src.core.services.universe_coordinator': 'from src.core.services.universe_coordinator',
            'from src.core.services': 'from src.core.services',
            
            # Market analytics
            'from src.core.services.analytics_manager': 'from src.core.services.analytics_manager',
            'from src.core.services.analytics_sync': 'from src.core.services.analytics_sync',
            'from src.core.services.market_metrics': 'from src.core.services.market_metrics',
            'from src.core.services.memory_analytics': 'from src.core.services.memory_analytics',
            'from src.core.services': 'from src.core.services',
            
            # Event detection
            'from src.processing.detectors.manager': 'from src.processing.detectors.manager',
            'from src.processing.detectors.engines': 'from src.processing.detectors.engines',
            'from src.processing.detectors.utils': 'from src.processing.detectors.utils',
            'from src.processing.detectors.buysell_tracker': 'from src.processing.detectors.buysell_tracker',
            'from src.processing.detectors.highlow_detector': 'from src.processing.detectors.highlow_detector',
            'from src.processing.detectors.surge_detector': 'from src.processing.detectors.surge_detector',
            'from src.processing.detectors.trend_detector': 'from src.processing.detectors.trend_detector',
            'from src.processing.detectors.buysell_engine': 'from src.processing.detectors.buysell_engine',
            'from src.processing.detectors': 'from src.processing.detectors',
            'from src.processing.detectors': 'from src.processing.detectors',
            
            # Processing
            'from src.processing.pipeline.event_detector': 'from src.processing.pipeline.event_detector',
            'from src.processing.queues.priority_manager': 'from src.processing.queues.priority_manager',
            'from src.processing.pipeline.tick_processor': 'from src.processing.pipeline.tick_processor',
            'from src.processing.workers.worker_pool': 'from src.processing.workers.worker_pool',
            'from src.processing': 'from src.processing',
            
            # Session accumulation
            'from src.core.services.accumulation_manager': 'from src.core.services.accumulation_manager',
            'from src.core.services.database_sync': 'from src.core.services.database_sync',
            'from src.core.services.memory_accumulation': 'from src.core.services.memory_accumulation',
            'from src.core.services': 'from src.core.services',
            
            # Data flow -> Monitoring
            'from src.monitoring.metrics_collector': 'from src.monitoring.metrics_collector',
            'from src.monitoring.performance_monitor': 'from src.monitoring.performance_monitor',
            'from src.core.services.session_manager': 'from src.core.services.session_manager',
            'from src.monitoring': 'from src.monitoring',
            
            # Services
            'from src.infrastructure.messaging.email_service': 'from src.infrastructure.messaging.email_service',
            'from src.infrastructure.messaging.sms_service': 'from src.infrastructure.messaging.sms_service',
            'from src.core.services.universe_service': 'from src.core.services.universe_service',
            'from src.core.services.user_filters_service': 'from src.core.services.user_filters_service',
            'from src.core.services.user_settings_service': 'from src.core.services.user_settings_service',
            'from src.core.services': 'from src.core.services',
            
            # Universe
            'from src.core.services.universe.core_manager': 'from src.core.services.universe.core_manager',
            'from src.core.services.universe.subscription_manager': 'from src.core.services.universe.subscription_manager',
            'from src.core.services.universe.user_manager': 'from src.core.services.universe.user_manager',
            'from src.core.services.universe.analytics': 'from src.core.services.universe.analytics',
            'from src.core.services.universe': 'from src.core.services.universe',
            
            # WebSocket handlers (ws_handlers was the original folder name)
            'from src.presentation.websocket.manager': 'from src.presentation.websocket.manager',
            'from src.presentation.websocket.publisher': 'from src.presentation.websocket.publisher',
            'from src.presentation.websocket.analytics': 'from src.presentation.websocket.analytics',
            'from src.presentation.websocket.data_filter': 'from src.presentation.websocket.data_filter',
            'from src.presentation.websocket.display_converter': 'from src.presentation.websocket.display_converter',
            'from src.presentation.websocket.filter_cache': 'from src.presentation.websocket.filter_cache',
            'from src.presentation.websocket.statistics': 'from src.presentation.websocket.statistics',
            'from src.presentation.websocket.universe_cache': 'from src.presentation.websocket.universe_cache',
            'from src.presentation.websocket.polygon_client': 'from src.presentation.websocket.polygon_client',
            'from src.presentation.websocket': 'from src.presentation.websocket',
            'import src.presentation.websocket': 'import src.presentation.websocket',
            
            # Monitoring
            'from src.monitoring.system_monitor': 'from src.monitoring.system_monitor',
            'from src.monitoring.tracer': 'from src.monitoring.tracer',
            'from src.monitoring.query_debug_logger': 'from src.monitoring.query_debug_logger',
            'from src.monitoring': 'from src.monitoring',
            'import src.monitoring': 'import src.monitoring',
            
            # Utils
            'from src.shared.utils.event_factory': 'from src.shared.utils.event_factory',
            'from src.shared.utils.general': 'from src.shared.utils.general',
            'from src.shared.utils.validation': 'from src.shared.utils.validation',
            'from src.shared.utils': 'from src.shared.utils',
            'import src.shared.utils': 'import src.shared.utils',
            
            # App modules
            'from src.api.rest.main': 'from src.api.rest.main',
            'from src.api.rest.api': 'from src.api.rest.api',
            'from src.api.rest.auth': 'from src.api.rest.auth',
            'from src.presentation.validators.forms': 'from src.presentation.validators.forms',
            'from src.shared.utils.app_utils': 'from src.shared.utils.app_utils',
            'from src.shared.utils.market_utils': 'from src.shared.utils.market_utils',
            'from src.core.services.startup_service': 'from src.core.services.startup_service',
            
            # Import statements (without from)
            'import src.api.rest.main': 'import src.api.rest.main',
            'import src.api.rest.api': 'import src.api.rest.api',
            'import src.api.rest.auth': 'import src.api.rest.auth',
            'import src.presentation.validators.forms': 'import src.presentation.validators.forms',
            'import src.shared.utils.app_utils': 'import src.shared.utils.app_utils',
            'import src.shared.utils.market_utils': 'import src.shared.utils.market_utils',
            'import src.core.services.startup_service': 'import src.core.services.startup_service',
        }
    
    def update_python_file(self, filepath: Path) -> bool:
        """Update imports in a single Python file"""
        try:
            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply import mappings in order (longer patterns first to avoid partial matches)
            sorted_mappings = sorted(self.import_mappings.items(), key=lambda x: -len(x[0]))
            
            for old_import, new_import in sorted_mappings:
                if old_import in content:
                    content = content.replace(old_import, new_import)
            
            # Update relative imports based on file location
            if str(filepath).startswith(str(self.dest_dir / 'src')):
                content = self._update_relative_imports(filepath, content)
            
            # Only write if content changed
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            self.errors.append(f"Error updating {filepath}: {e}")
            return False
    
    def _update_relative_imports(self, filepath: Path, content: str) -> str:
        """Update relative imports based on new file location"""
        
        try:
            # Determine module depth for relative imports
            relative_to_src = filepath.relative_to(self.dest_dir / 'src')
            depth = len(relative_to_src.parts) - 1  # -1 for the file itself
            
            # Update single-dot relative imports
            if depth > 0:
                # Replace relative imports with absolute imports from src
                content = re.sub(
                    r'from \.([\w.]+) import',
                    lambda m: f'from src.{self._get_module_path(filepath.parent)}.{m.group(1)} import',
                    content
                )
                
                # Handle parent relative imports (.. and more)
                for i in range(2, min(depth + 1, 5)):  # Limit to 5 levels
                    dots = '.' * i
                    content = re.sub(
                        f'from {re.escape(dots)}([\w.]*) import',
                        lambda m: self._create_absolute_import(filepath, i-1, m.group(1)),
                        content
                    )
        except:
            # If there's an issue with relative imports, just return unchanged
            pass
        
        return content
    
    def _create_absolute_import(self, filepath: Path, levels_up: int, module_suffix: str) -> str:
        """Create absolute import from relative import"""
        current = filepath.parent
        for _ in range(levels_up):
            current = current.parent
        base_path = self._get_module_path(current)
        if module_suffix:
            return f'from src.{base_path}.{module_suffix} import'
        else:
            return f'from src.{base_path} import'
    
    def _get_module_path(self, dir_path: Path) -> str:
        """Get module path from directory"""
        try:
            relative = dir_path.relative_to(self.dest_dir / 'src')
            return str(relative).replace('\\', '.').replace('/', '.')
        except:
            return ''
    
    def _get_parent_module_path(self, dir_path: Path, levels: int) -> str:
        """Get parent module path going up N levels"""
        current = dir_path
        for _ in range(levels):
            current = current.parent
        return self._get_module_path(current)
    
    def update_all_imports(self):
        """Update imports in all Python files"""
        print("Updating import references...")
        print("=" * 60)
        
        # Get all Python files
        python_files = []
        for root, dirs, files in os.walk(self.dest_dir):
            # Skip directories we don't want to process
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'venv', '.venv', '.git', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        total_files = len(python_files)
        updated_count = 0
        
        print(f"Found {total_files} Python files to process")
        
        for i, filepath in enumerate(python_files, 1):
            if self.update_python_file(filepath):
                updated_count += 1
                relative_path = filepath.relative_to(self.dest_dir)
                self.updated_files.append(str(relative_path))
                print(f"✓ Updated: {relative_path}")
            
            if i % 20 == 0:
                print(f"Progress: {i}/{total_files} files processed...")
        
        return {
            'total_files': total_files,
            'updated_files': updated_count,
            'errors': len(self.errors),
            'updated_list': self.updated_files,
            'error_list': self.errors
        }
    
    def save_report(self, results: Dict):
        """Save update report"""
        report_path = self.dest_dir / "import_update_report.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Report saved to: {report_path}")
        
        # Create readable report
        readable_path = self.dest_dir / "import_update_report.txt"
        with open(readable_path, 'w', encoding='utf-8') as f:
            f.write("IMPORT UPDATE REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total Python files: {results['total_files']}\n")
            f.write(f"Files updated: {results['updated_files']}\n")
            f.write(f"Errors: {results['errors']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            
            if results['updated_list']:
                f.write("UPDATED FILES:\n")
                f.write("-" * 40 + "\n")
                for file in sorted(results['updated_list']):
                    f.write(f"  - {file}\n")
            
            if results['error_list']:
                f.write("\n" + "=" * 80 + "\n")
                f.write("ERRORS:\n")
                f.write("-" * 40 + "\n")
                for error in results['error_list']:
                    f.write(f"  - {error}\n")
        
        print(f"✓ Readable report saved to: {readable_path}")


def main():
    """Main execution"""
    print("TickStock Import Reference Updater - Corrected Version")
    print("=" * 60)
    
    updater = ImportUpdater()
    results = updater.update_all_imports()
    
    print("\n" + "=" * 60)
    print("UPDATE SUMMARY")
    print("=" * 60)
    print(f"Total Python files: {results['total_files']}")
    print(f"Files updated: {results['updated_files']}")
    print(f"Errors: {results['errors']}")
    
    if results['updated_files'] > 0:
        print(f"\n✅ Successfully updated {results['updated_files']} files")
    
    if results['errors'] > 0:
        print(f"\n⚠️ Errors encountered: {results['errors']}")
        for error in results['error_list'][:5]:
            print(f"  - {error}")
        if len(results['error_list']) > 5:
            print(f"  ... and {len(results['error_list']) - 5} more")
    
    updater.save_report(results)
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. Review the import_update_report.txt for details")
    print("2. Run u_create_dependencies.py to create __init__ files")
    print("3. Test imports with: python -c \"from src.core.services import MarketDataService\"")
    
    return 0 if results['errors'] == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())