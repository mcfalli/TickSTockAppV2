#!/usr/bin/env python3
"""
Comprehensive Reference Integrity Checker for TickStock V2
Validates all imports, cross-references, and dependencies across the solution.
Fixed version with proper encoding handling.
"""

import sys
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime

class ReferenceIntegrityChecker:
    """Comprehensive reference and dependency checker for TickStock V2."""
    
    def __init__(self, base_path: str = None):
        """Initialize the checker with the project base path."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.src_path = self.base_path / "src"
        self.config_path = self.base_path / "config"
        self.web_path = self.base_path / "web"
        
        # Track all findings
        self.imports_map = defaultdict(set)  # file -> imported modules
        self.exports_map = defaultdict(set)  # file -> exported items
        self.circular_deps = []
        self.missing_modules = []
        self.orphaned_files = []
        self.broken_references = []
        self.websocket_events = defaultdict(set)
        self.database_models = set()
        self.api_endpoints = defaultdict(set)
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'python_files': 0,
            'js_files': 0,
            'imports_validated': 0,
            'circular_dependencies': 0,
            'missing_modules': 0,
            'orphaned_files': 0,
            'websocket_mismatches': 0
        }
        
    def run_full_check(self) -> Dict:
        """Run complete reference integrity check."""
        print("=" * 80)
        print("TICKSTOCK V2 REFERENCE INTEGRITY CHECKER")
        print("=" * 80)
        print(f"Base Path: {self.base_path}\n")
        
        # Step 1: Discover all Python files
        print("Step 1: Discovering Python files...")
        python_files = self._discover_python_files()
        
        # Step 2: Parse imports and exports
        print("Step 2: Analyzing imports and exports...")
        self._analyze_python_files(python_files)
        
        # Step 3: Check for circular dependencies
        print("Step 3: Checking for circular dependencies...")
        self._check_circular_dependencies()
        
        # Step 4: Validate all imports
        print("Step 4: Validating import references...")
        self._validate_imports()
        
        # Step 5: Find orphaned files
        print("Step 5: Finding orphaned files...")
        self._find_orphaned_files(python_files)
        
        # Step 6: Check WebSocket events
        print("Step 6: Checking WebSocket event consistency...")
        self._check_websocket_events()
        
        # Step 7: Validate database models
        print("Step 7: Validating database models...")
        self._validate_database_models()
        
        # Step 8: Check API endpoints
        print("Step 8: Checking API endpoints...")
        self._check_api_endpoints()
        
        # Step 9: Cross-reference validation
        print("Step 9: Cross-reference validation...")
        self._cross_reference_validation()
        
        # Generate report
        return self._generate_report()
        
    def _discover_python_files(self) -> List[Path]:
        """Discover all Python files in the project."""
        python_files = []
        
        for path in [self.src_path, self.config_path]:
            if path.exists():
                python_files.extend(path.rglob("*.py"))
                
        self.stats['python_files'] = len(python_files)
        print(f"  Found {len(python_files)} Python files")
        return python_files
        
    def _analyze_python_files(self, python_files: List[Path]):
        """Parse Python files to extract imports and exports."""
        for py_file in python_files:
            try:
                # Use UTF-8 encoding with error handling
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                tree = ast.parse(content)
                
                # Get relative path for tracking
                rel_path = str(py_file.relative_to(self.base_path))
                
                # Extract imports
                imports = self._extract_imports(tree, rel_path)
                self.imports_map[rel_path] = imports
                
                # Extract exports (classes, functions, variables)
                exports = self._extract_exports(tree)
                self.exports_map[rel_path] = exports
                
                # Check for WebSocket events
                self._extract_websocket_events(content, rel_path)
                
                # Check for database models
                if 'models' in str(py_file) or 'database' in str(py_file):
                    self._extract_database_models(tree, rel_path)
                    
                # Check for API endpoints
                if 'routes' in str(py_file) or 'api' in str(py_file):
                    self._extract_api_endpoints(content, rel_path)
                    
            except Exception as e:
                self.broken_references.append({
                    'file': rel_path,
                    'error': f"Parse error: {str(e)}"
                })
                
    def _extract_imports(self, tree: ast.AST, file_path: str) -> Set[str]:
        """Extract all imports from an AST."""
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if module:
                    imports.add(module)
                # Track specific imports for validation
                for alias in node.names:
                    if module:
                        imports.add(f"{module}.{alias.name}")
                        
        self.stats['imports_validated'] += len(imports)
        return imports
        
    def _extract_exports(self, tree: ast.AST) -> Set[str]:
        """Extract all exported items from an AST."""
        exports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                exports.add(node.name)
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):  # Skip private functions
                    exports.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith('_'):
                        exports.add(target.id)
                        
        return exports
        
    def _extract_websocket_events(self, content: str, file_path: str):
        """Extract WebSocket event definitions."""
        # Backend events (emit patterns)
        emit_pattern = r'emit\([\'"](\w+)[\'"]'
        for match in re.finditer(emit_pattern, content):
            self.websocket_events['backend'].add(match.group(1))
            
        # Frontend events (on patterns)
        on_pattern = r'\.on\([\'"](\w+)[\'"]'
        for match in re.finditer(on_pattern, content):
            self.websocket_events['handlers'].add(match.group(1))
            
    def _extract_database_models(self, tree: ast.AST, file_path: str):
        """Extract database model definitions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a SQLAlchemy model
                for base in node.bases:
                    if isinstance(base, ast.Name) and 'Model' in base.id:
                        self.database_models.add(node.name)
                        
    def _extract_api_endpoints(self, content: str, file_path: str):
        """Extract API endpoint definitions."""
        route_pattern = r'@.*\.route\([\'"]([^\'\"]+)[\'"]'
        for match in re.finditer(route_pattern, content):
            self.api_endpoints[file_path].add(match.group(1))
            
    def _check_circular_dependencies(self):
        """Check for circular import dependencies."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(module: str, path: List[str]) -> Optional[List[str]]:
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            if module in self.imports_map:
                for imported in self.imports_map[module]:
                    # Convert import to file path
                    import_path = self._import_to_path(imported)
                    
                    if import_path in rec_stack:
                        # Found circular dependency
                        cycle_start = path.index(import_path)
                        return path[cycle_start:] + [import_path]
                    elif import_path not in visited and import_path in self.imports_map:
                        cycle = has_cycle(import_path, path.copy())
                        if cycle:
                            return cycle
                            
            rec_stack.remove(module)
            return None
            
        for module in self.imports_map:
            if module not in visited:
                cycle = has_cycle(module, [])
                if cycle:
                    self.circular_deps.append(cycle)
                    self.stats['circular_dependencies'] += 1
                    
    def _import_to_path(self, import_name: str) -> str:
        """Convert import name to file path."""
        # Handle different import formats
        if import_name.startswith('src.'):
            return import_name.replace('.', '/') + '.py'
        elif import_name.startswith('config.'):
            return import_name.replace('.', '/') + '.py'
        return import_name
        
    def _validate_imports(self):
        """Validate that all imports point to existing modules."""
        all_modules = set(self.exports_map.keys())
        
        for file_path, imports in self.imports_map.items():
            for imp in imports:
                # Check if it's an internal import
                if imp.startswith('src.') or imp.startswith('config.'):
                    import_path = self._import_to_path(imp.split('.')[0])
                    
                    # Check if the module exists
                    if not any(import_path in m for m in all_modules):
                        # Check if it's a valid sub-import
                        base_module = '.'.join(imp.split('.')[:-1])
                        if base_module:
                            base_path = self._import_to_path(base_module)
                            if not any(base_path in m for m in all_modules):
                                self.missing_modules.append({
                                    'file': file_path,
                                    'import': imp,
                                    'type': 'missing_module'
                                })
                                self.stats['missing_modules'] += 1
                                
    def _find_orphaned_files(self, python_files: List[Path]):
        """Find Python files that are never imported."""
        imported_files = set()
        
        # Collect all files that are imported
        for imports in self.imports_map.values():
            for imp in imports:
                if imp.startswith('src.') or imp.startswith('config.'):
                    import_path = self._import_to_path(imp)
                    imported_files.add(import_path)
                    
        # Check which files are never imported
        for py_file in python_files:
            rel_path = str(py_file.relative_to(self.base_path))
            
            # Skip special files
            if any(skip in rel_path for skip in ['__init__.py', 'app.py', 'test_', 'setup.py', 'u_']):
                continue
                
            # Check if file is imported anywhere
            if rel_path not in imported_files and not any(rel_path in imp for imp in imported_files):
                self.orphaned_files.append(rel_path)
                self.stats['orphaned_files'] += 1
                
    def _check_websocket_events(self):
        """Check WebSocket event consistency between backend and frontend."""
        # Load JavaScript files to check frontend events
        js_files = []
        if self.web_path.exists():
            js_files = list(self.web_path.rglob("*.js"))
            
        for js_file in js_files:
            try:
                content = js_file.read_text(encoding='utf-8', errors='ignore')
                
                # Frontend socket.on handlers
                on_pattern = r'socket\.on\([\'"](\w+)[\'"]'
                for match in re.finditer(on_pattern, content):
                    self.websocket_events['frontend_handlers'].add(match.group(1))
                    
                # Frontend socket.emit events
                emit_pattern = r'socket\.emit\([\'"](\w+)[\'"]'
                for match in re.finditer(emit_pattern, content):
                    self.websocket_events['frontend_emits'].add(match.group(1))
                    
            except Exception:
                pass
                
        # Check for mismatches
        backend_emits = self.websocket_events.get('backend', set())
        frontend_handlers = self.websocket_events.get('frontend_handlers', set())
        
        unhandled_events = backend_emits - frontend_handlers
        if unhandled_events:
            self.stats['websocket_mismatches'] += len(unhandled_events)
            for event in unhandled_events:
                self.broken_references.append({
                    'type': 'websocket_mismatch',
                    'event': event,
                    'issue': 'Backend emits but no frontend handler'
                })
                
    def _validate_database_models(self):
        """Validate database models against migration files."""
        migration_path = self.src_path / "infrastructure" / "database" / "migrations"
        
        if migration_path.exists():
            migration_files = list(migration_path.glob("*.sql"))
            
            for mig_file in migration_files:
                try:
                    content = mig_file.read_text(encoding='utf-8', errors='ignore')
                    # Extract table names from CREATE TABLE statements
                    table_pattern = r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)'
                    for match in re.finditer(table_pattern, content, re.IGNORECASE):
                        table_name = match.group(1)
                        # Check if corresponding model exists
                        model_name = ''.join(word.capitalize() for word in table_name.split('_'))
                        if model_name not in self.database_models and table_name not in ['alembic_version']:
                            self.broken_references.append({
                                'type': 'database_mismatch',
                                'table': table_name,
                                'issue': f'No model found for table {table_name}'
                            })
                except Exception:
                    pass
                    
    def _check_api_endpoints(self):
        """Check API endpoint consistency."""
        # Check for duplicate endpoints
        all_endpoints = []
        for file_path, endpoints in self.api_endpoints.items():
            for endpoint in endpoints:
                all_endpoints.append((endpoint, file_path))
                
        # Find duplicates
        endpoint_dict = defaultdict(list)
        for endpoint, file_path in all_endpoints:
            endpoint_dict[endpoint].append(file_path)
            
        for endpoint, files in endpoint_dict.items():
            if len(files) > 1:
                self.broken_references.append({
                    'type': 'duplicate_endpoint',
                    'endpoint': endpoint,
                    'files': files
                })
                
    def _cross_reference_validation(self):
        """Perform cross-reference validation between components."""
        # Check if key services are properly imported where needed
        critical_services = [
            'MarketDataService',
            'WebSocketManager',
            'SessionManager',
            'DataProviderFactory'
        ]
        
        for service in critical_services:
            importing_files = []
            for file_path, imports in self.imports_map.items():
                if any(service in imp for imp in imports):
                    importing_files.append(file_path)
                    
            if len(importing_files) == 0 and service in str(self.exports_map.values()):
                self.broken_references.append({
                    'type': 'unused_service',
                    'service': service,
                    'issue': 'Critical service is defined but never imported'
                })
                
    def _generate_report(self) -> Dict:
        """Generate comprehensive report."""
        print("\n" + "=" * 80)
        print("INTEGRITY CHECK REPORT")
        print("=" * 80)
        
        # Summary statistics
        print("\n📊 STATISTICS:")
        print(f"  Total Python files: {self.stats['python_files']}")
        print(f"  Total imports validated: {self.stats['imports_validated']}")
        print(f"  Circular dependencies: {self.stats['circular_dependencies']}")
        print(f"  Missing modules: {self.stats['missing_modules']}")
        print(f"  Orphaned files: {self.stats['orphaned_files']}")
        print(f"  WebSocket mismatches: {self.stats['websocket_mismatches']}")
        
        # Critical issues
        critical_issues = []
        
        if self.circular_deps:
            print("\n🔄 CIRCULAR DEPENDENCIES FOUND:")
            for cycle in self.circular_deps[:5]:  # Show first 5
                print(f"  • {' → '.join(cycle)}")
                critical_issues.append({'type': 'circular', 'data': cycle})
                
        if self.missing_modules:
            print("\n❌ MISSING MODULES:")
            for missing in self.missing_modules[:10]:  # Show first 10
                print(f"  • {missing['file']}: Cannot import '{missing['import']}'")
                critical_issues.append({'type': 'missing', 'data': missing})
                
        if self.orphaned_files:
            print("\n📁 ORPHANED FILES (never imported):")
            for orphan in self.orphaned_files[:10]:  # Show first 10
                print(f"  • {orphan}")
                
        if self.broken_references:
            print("\n⚠️ BROKEN REFERENCES:")
            for ref in self.broken_references[:10]:  # Show first 10
                if ref.get('type') == 'websocket_mismatch':
                    print(f"  • WebSocket: Event '{ref['event']}' - {ref['issue']}")
                elif ref.get('type') == 'database_mismatch':
                    print(f"  • Database: {ref['issue']}")
                elif ref.get('type') == 'duplicate_endpoint':
                    print(f"  • API: Duplicate endpoint '{ref['endpoint']}' in {len(ref['files'])} files")
                else:
                    print(f"  • {ref}")
                    
        # Health score
        total_issues = (
            self.stats['circular_dependencies'] +
            self.stats['missing_modules'] +
            self.stats['orphaned_files'] +
            self.stats['websocket_mismatches']
        )
        
        if total_issues == 0:
            health_score = 100
            health_status = "EXCELLENT ✅"
        elif total_issues < 5:
            health_score = 90
            health_status = "GOOD ✅"
        elif total_issues < 10:
            health_score = 75
            health_status = "FAIR ⚠️"
        elif total_issues < 20:
            health_score = 60
            health_status = "NEEDS ATTENTION ⚠️"
        else:
            health_score = 40
            health_status = "CRITICAL ❌"
            
        print(f"\n🏥 REFERENCE INTEGRITY SCORE: {health_score}/100 - {health_status}")
        
        # Save detailed report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'base_path': str(self.base_path),
            'statistics': self.stats,
            'health_score': health_score,
            'health_status': health_status,
            'circular_dependencies': self.circular_deps,
            'missing_modules': self.missing_modules,
            'orphaned_files': self.orphaned_files,
            'broken_references': self.broken_references,
            'websocket_events': {k: list(v) for k, v in self.websocket_events.items()},
            'database_models': list(self.database_models),
            'api_endpoints': {k: list(v) for k, v in self.api_endpoints.items()},
            'critical_issues': critical_issues
        }
        
        # Save to JSON file
        report_file = self.base_path / f"integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return report_data
        

def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='TickStock V2 Reference Integrity Checker')
    parser.add_argument('--path', default=r"C:\Users\McDude\TickStockAppV2",
                        help='Base path of the TickStock V2 project')
    parser.add_argument('--fix', action='store_true',
                        help='Attempt to auto-fix issues (experimental)')
    args = parser.parse_args()
    
    # Run integrity check
    checker = ReferenceIntegrityChecker(args.path)
    report = checker.run_full_check()
    
    # Auto-fix if requested
    if args.fix and report['critical_issues']:
        print("\n" + "=" * 80)
        print("AUTO-FIX MODE")
        print("=" * 80)
        
        fixes_applied = 0
        
        # Fix missing imports (polygon_websocket_client -> polygon_client)
        if any('polygon_websocket_client' in str(issue) for issue in report['missing_modules']):
            print("Fixing polygon_websocket_client references...")
            fix_count = fix_polygon_imports(Path(args.path))
            print(f"  Fixed {fix_count} references")
            fixes_applied += fix_count
            
        print(f"\n✅ Total fixes applied: {fixes_applied}")
        print("Please run the checker again to verify fixes.")
        
    print("\n" + "=" * 80)
    print("INTEGRITY CHECK COMPLETE")
    print("=" * 80)
    

def fix_polygon_imports(base_path: Path) -> int:
    """Fix polygon_websocket_client import issues."""
    fixes = 0
    
    for py_file in base_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            if 'polygon_websocket_client' in content:
                new_content = content.replace('polygon_websocket_client', 'polygon_client')
                py_file.write_text(new_content, encoding='utf-8')
                fixes += 1
        except Exception:
            pass
            
    return fixes


if __name__ == "__main__":
    main()