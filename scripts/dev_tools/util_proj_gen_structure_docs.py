"""
TickStock Project Structure Documentation Generator

This utility analyzes the TickStock V2 project codebase to generate comprehensive architectural documentation.

PURPOSE:
--------
- Scans the entire project directory structure
- Analyzes Python, JavaScript, CSS, and configuration files 
- Generates detailed markdown documentation covering:
  * Application overview and system architecture
  * Module structure and component inventory
  * Data flows and processing pipelines
  * WebSocket architecture and event processing
  * External dependencies and configuration
  * Testing strategy and quality metrics

FUNCTIONALITY:
--------------
- AST (Abstract Syntax Tree) parsing for Python files to extract classes/functions
- Pattern matching for architectural significance filtering
- Domain classification using regex patterns for src/ modular structure
- Import relationship mapping between modules
- Critical component identification for core system elements
- Sprint reference tracking from code comments
- WebSocket event extraction from JavaScript files
- Quality metrics calculation including modularity scoring

OUTPUT:
-------
Generates 'docs/new/project_structure_docs.md' containing:
- Structured markdown with table of contents
- Detailed sections for each architectural domain
- Component inventories with descriptions
- Data flow diagrams and processing pipelines
- Configuration and dependency mappings
- Quality metrics and testing coverage analysis

USAGE:
------
python util_proj_gen_structure_docs.py [--root-dir PATH] [--output-file PATH] [--verbose]

The script automatically analyzes the modular src/ architecture of TickStock V2 and produces
documentation suitable for developers, architects, and stakeholders.
"""

import argparse
import ast
import logging
import os
import re
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class CreateProjectStructureDocumentation:
    """
    Analyzes project structure to generate a documentation-focused architectural overview
    emphasizing domains, data flows, and system boundaries for TickStock V2.
    
    Enhanced for the new modular src/ structure with improved domain detection
    and relationship mapping.
    """

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.files = {}
        self.components = {}
        self.routes = []
        self.websocket_events = []
        self.imports = {}  # Track import relationships

        # Updated domain patterns for new structure
        self.domain_patterns = {
            'core_services': [
                r'src[/\\]core[/\\]services', r'market.*data.*service', r'session.*manager',
                r'analytics.*manager', r'config.*manager', r'universe.*service'
            ],
            'domain_models': [
                r'src[/\\]core[/\\]domain', r'events[/\\]', r'market[/\\]',
                r'tick\.py', r'state\.py', r'base\.py'
            ],
            'infrastructure': [
                r'src[/\\]infrastructure', r'data.*sources', r'database', r'cache',
                r'massive', r'synthetic', r'messaging'
            ],
            'presentation': [
                r'src[/\\]presentation', r'websocket', r'converters', r'validators',
                r'publisher', r'display', r'filter'
            ],
            'processing': [
                r'src[/\\]processing', r'detectors', r'pipeline', r'queues',
                r'workers', r'event.*processor', r'tick.*processor'
            ],
            'authentication': [
                r'src[/\\]auth', r'authentication', r'registration', r'session',
                r'login', r'user.*verification'
            ],
            'api': [
                r'src[/\\]api', r'rest', r'graphql', r'websocket[/\\]__init__'
            ],
            'monitoring': [
                r'src[/\\]monitoring', r'health.*monitor', r'metrics', r'performance',
                r'tracer', r'system.*monitor'
            ],
            'frontend': [
                r'web[/\\]', r'static', r'templates', r'\.js$', r'\.css$', r'\.html$'
            ],
            'configuration': [
                r'config[/\\]', r'environments', r'\.env', r'docker', r'nginx',
                r'prometheus', r'requirements'
            ],
            'testing': [
                r'tests[/\\]', r'test_', r'fixtures', r'conftest'
            ],
            'utilities': [
                r'src[/\\]shared', r'utils', r'constants', r'exceptions',
                r'scripts[/\\]', r'dev_tools'
            ]
        }

        # Critical architectural components for V2 structure
        self.critical_components = {
            'core_orchestrators': [
                'MarketDataService', 'SessionManager', 'ConfigManager',
                'UniverseService', 'AnalyticsManager', 'StartupService'
            ],
            'data_providers': [
                'DataProviderFactory', 'MassiveDataProvider', 'SyntheticDataProvider',
                'RealTimeDataAdapter', 'DataProvider'
            ],
            'event_processors': [
                'EventDetectionManager', 'HighLowDetector', 'TrendDetector',
                'SurgeDetector', 'BuySellTracker', 'EventProcessor', 'TickProcessor'
            ],
            'websocket_layer': [
                'WebSocketManager', 'WebSocketPublisher', 'DataPublisher',
                'WebSocketDataFilter', 'WebSocketAnalytics', 'MassiveWebSocketClient'
            ],
            'domain_events': [
                'BaseEvent', 'HighLowEvent', 'TrendEvent', 'SurgeEvent',
                'ControlEvent', 'MarketTick', 'MarketState'
            ],
            'infrastructure_services': [
                'CacheControl', 'DatabaseSync', 'EmailService', 'SMSService',
                'HealthMonitor', 'MetricsCollector', 'PerformanceMonitor'
            ]
        }

        # Module structure patterns
        self.module_patterns = {
            'src/core': 'Core Business Logic',
            'src/infrastructure': 'External Integrations & Data Layer',
            'src/presentation': 'User Interface & WebSocket Layer',
            'src/processing': 'Event Detection & Processing Pipeline',
            'src/api': 'REST & WebSocket API Endpoints',
            'src/auth': 'Authentication & Authorization',
            'src/monitoring': 'System Monitoring & Metrics',
            'src/shared': 'Shared Utilities & Constants'
        }

        # Statistics tracking
        self.stats = {
            'total_files': 0,
            'python_files': 0,
            'js_files': 0,
            'css_files': 0,
            'test_files': 0,
            'config_files': 0
        }

        # Sprint tracking
        self.sprint_references = []

    def analyze_project(self) -> dict:
        """Main analysis method that returns architectural overview."""
        logger.info(f"Starting analysis of {self.root_dir}")
        self._scan_files()
        self._analyze_import_relationships()

        return {
            "metadata": self._generate_metadata(),
            "application": self._generate_application_overview(),
            "architecture": self._analyze_architecture(),
            "core_domains": self._identify_core_domains(),
            "module_structure": self._analyze_module_structure(),
            "key_data_flows": self._identify_data_flows(),
            "component_inventory": self._generate_component_inventory(),
            "external_dependencies": self._identify_external_dependencies(),
            "websocket_architecture": self._analyze_websocket_architecture(),
            "event_processing": self._analyze_event_processing(),
            "configuration": self._identify_configuration(),
            "testing_strategy": self._analyze_testing_strategy(),
            "frontend_architecture": self._analyze_frontend_architecture(),
            "requirements": self._extract_requirements(),
            "statistics": self.stats,
            "quality_metrics": self._calculate_quality_metrics(),
            "sprint_tracking": self._analyze_sprint_references()
        }

    def _scan_files(self):
        """Scan project files and extract components."""
        exclude_dirs = {
            '.git', '__pycache__', 'venv', '.venv', 'env', '.env',
            'logs', 'data', 'node_modules', '.pytest_cache',
            'dist', 'build', '*.egg-info'
        }

        include_patterns = [
            r"\.py$", r"\.js$", r"\.html$", r"\.css$",
            r"\.yml$", r"\.yaml$", r"\.json$", r"\.env$",
            r"\.txt$", r"\.md$", r"\.ini$", r"\.sh$", r"\.bat$",
            r"Dockerfile$", r"nginx\.conf$", r"\.gitignore$"
        ]

        for root, dirs, files in os.walk(self.root_dir):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.root_dir).replace('\\', '/')

                # Skip if not matching include patterns
                if not any(re.search(pattern, file, re.IGNORECASE) for pattern in include_patterns):
                    continue

                self.stats['total_files'] += 1
                self._analyze_file(file_path, rel_path)

    def _analyze_file(self, file_path: str, rel_path: str):
        """Analyze individual file for architectural significance."""
        try:
            # Initialize file info
            self.files[rel_path] = {
                'type': self._get_file_type(file_path),
                'domain': self._classify_domain(rel_path),
                'module': self._identify_module(rel_path),
                'architectural_role': self._determine_architectural_role(rel_path),
                'size': os.path.getsize(file_path)
            }

            # Run type-specific analysis
            if file_path.endswith('.py'):
                self.stats['python_files'] += 1
                if 'test' in rel_path.lower():
                    self.stats['test_files'] += 1
                self._analyze_python_file(file_path, rel_path)
            elif file_path.endswith('.js') and not file_path.endswith('-min.js'):
                self.stats['js_files'] += 1
                self._analyze_javascript_file(file_path, rel_path)
            elif file_path.endswith('.css'):
                self.stats['css_files'] += 1
                self._analyze_css_file(file_path, rel_path)
            elif any(file_path.endswith(ext) for ext in ['.yml', '.yaml', '.json', '.env', '.ini']):
                self.stats['config_files'] += 1

        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")

    def _analyze_python_file(self, file_path: str, rel_path: str):
        """Enhanced Python file analysis for V2 structure."""
        try:
            with open(file_path, encoding='utf-8') as file:
                content = file.read()

            # Track sprint references
            sprint_matches = re.findall(r'Sprint\s+(\d+)', content, re.IGNORECASE)
            for sprint_num in sprint_matches:
                self.sprint_references.append({
                    'file': rel_path,
                    'sprint': int(sprint_num)
                })

            # Extract routes for Flask apps
            if 'app.py' in rel_path or 'routes' in rel_path:
                route_pattern = r'@(?:app|api|blueprint)\.route\([\'"]([^\'"]+)[\'"]'
                self.routes.extend(re.findall(route_pattern, content))

            # Extract imports for relationship mapping
            import_pattern = r'^(?:from|import)\s+([\w\.]+)'
            imports = re.findall(import_pattern, content, re.MULTILINE)
            self.imports[rel_path] = imports

            # Parse AST for components
            try:
                tree = ast.parse(content, filename=file_path)
                self._extract_components_from_ast(tree, rel_path)
            except SyntaxError:
                self._extract_components_with_regex(content, rel_path)

        except Exception as e:
            logger.warning(f"Failed to analyze Python file {file_path}: {e}")

    def _extract_components_from_ast(self, tree: ast.AST, rel_path: str):
        """Extract classes and significant functions from AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                if self._is_architecturally_significant(class_name, rel_path):
                    docstring = ast.get_docstring(node) or ""
                    base_classes = [self._get_name(base) for base in node.bases]

                    # Count methods
                    methods = [n.name for n in ast.walk(node)
                              if isinstance(n, ast.FunctionDef)]

                    self.components[f"{rel_path}:{class_name}"] = {
                        'name': class_name,
                        'type': 'class',
                        'file': rel_path,
                        'domain': self._classify_domain(rel_path),
                        'module': self._identify_module(rel_path),
                        'architectural_role': self._determine_component_role(class_name),
                        'description': docstring.split('\n')[0][:100] if docstring else "",
                        'base_classes': base_classes,
                        'method_count': len(methods),
                        'is_critical': self._is_critical_component(class_name)
                    }

            elif isinstance(node, ast.FunctionDef):
                func_name = node.name
                if self._is_architecturally_significant(func_name, rel_path):
                    docstring = ast.get_docstring(node) or ""
                    params = [arg.arg for arg in node.args.args]

                    self.components[f"{rel_path}:{func_name}"] = {
                        'name': func_name,
                        'type': 'function',
                        'file': rel_path,
                        'domain': self._classify_domain(rel_path),
                        'module': self._identify_module(rel_path),
                        'architectural_role': self._determine_component_role(func_name),
                        'description': docstring.split('\n')[0][:100] if docstring else "",
                        'parameters': params,
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    }

    def _get_name(self, node) -> str:
        """Extract name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)

    def _identify_module(self, file_path: str) -> str:
        """Identify which module a file belongs to."""
        for pattern, module in self.module_patterns.items():
            if pattern in file_path:
                return module
        return 'Root'

    def _is_critical_component(self, name: str) -> bool:
        """Check if component is critical to architecture."""
        for category, components in self.critical_components.items():
            if any(comp.lower() in name.lower() for comp in components):
                return True
        return False

    def _analyze_import_relationships(self):
        """Analyze import relationships between modules."""
        relationships = {}
        for file_path, imports in self.imports.items():
            module = self._identify_module(file_path)
            if module not in relationships:
                relationships[module] = set()

            for imp in imports:
                if imp.startswith('src.'):
                    target_module = self._identify_module_from_import(imp)
                    if target_module and target_module != module:
                        relationships[module].add(target_module)

        self.module_relationships = {k: list(v) for k, v in relationships.items()}

    def _identify_module_from_import(self, import_path: str) -> str | None:
        """Identify module from import statement."""
        parts = import_path.split('.')
        if len(parts) >= 2:
            module_path = '/'.join(parts[:2])
            return self.module_patterns.get(module_path)
        return None

    def _generate_metadata(self) -> dict:
        """Generate metadata about the documentation."""
        return {
            'generated_at': datetime.now().isoformat(),
            'project_root': self.root_dir,
            'version': '2.0',
            'structure_type': 'Modular Architecture (src/)',
            'total_components': len(self.components),
            'total_files': self.stats['total_files']
        }

    def _generate_application_overview(self) -> dict:
        """Generate high-level application overview."""
        has_flask = any('flask' in str(self.imports.get(f, [])).lower()
                       for f in self.files)
        has_socketio = bool(self.websocket_events) or any('socketio' in str(self.imports.get(f, [])).lower()
                                                          for f in self.files)

        return {
            "name": "TickStock V2",
            "type": "Real-time Market Data Processing System",
            "backend": "Flask with Flask-SocketIO",
            "frontend": "JavaScript SPA with WebSocket",
            "description": "High-performance market data processing with sub-millisecond event detection",
            "architecture_pattern": "Component-based with Pull Model Event Distribution",
            "data_flow": "WebSocket → Core Services → Event Processing → User Distribution",
            "key_features": [
                "Real-time market data processing (4,000+ tickers)",
                "Sub-millisecond event detection",
                "Pull-based event distribution (zero event loss)",
                "Per-user data isolation and filtering",
                "Modular component architecture"
            ],
            "routes": self.routes[:20],
            "websocket_events": list(set([event['name'] for event in self.websocket_events[:10]]))
        }

    def _analyze_architecture(self) -> dict:
        """Analyze overall system architecture."""
        return {
            "pattern": "Modular Component Architecture",
            "layers": {
                "presentation": "WebSocket & API Layer (src/presentation, src/api)",
                "business": "Core Services & Domain Logic (src/core)",
                "processing": "Event Detection & Processing (src/processing)",
                "infrastructure": "Data Sources & External Services (src/infrastructure)",
                "shared": "Utilities & Constants (src/shared)"
            },
            "key_patterns": [
                "Dependency Injection",
                "Event-Driven Architecture",
                "Pull Model Distribution",
                "Memory-First Processing",
                "Per-User Isolation"
            ],
            "module_dependencies": self.module_relationships if hasattr(self, 'module_relationships') else {}
        }

    def _analyze_module_structure(self) -> dict:
        """Analyze the modular structure of the application."""
        modules = {}

        # First, create module entries with proper descriptions
        for pattern, description in self.module_patterns.items():
            modules[description] = {
                'files': [],
                'components': [],
                'description': description,
                'path': pattern,
                'size': 0
            }

        # Add "Root" for files not in any module
        modules['Root'] = {
            'files': [],
            'components': [],
            'description': 'Root level files and scripts',
            'path': '',
            'size': 0
        }

        # Now map files to modules
        for file_path, file_info in self.files.items():
            module_name = file_info.get('module', 'Root')
            if module_name in modules:
                modules[module_name]['files'].append(file_path)
                modules[module_name]['size'] += file_info.get('size', 0)

        # Add components to modules
        for comp_key, comp_info in self.components.items():
            module_name = comp_info.get('module', 'Root')
            if module_name in modules:
                # Avoid duplicates and filter out non-critical components
                comp_name = comp_info['name']
                if comp_name not in modules[module_name]['components']:
                    modules[module_name]['components'].append(comp_name)

        # Calculate statistics and clean up
        for module_name, module in modules.items():
            module['file_count'] = len(module['files'])
            module['component_count'] = len(module['components'])

            # Sort and limit lists for readability
            module['files'] = sorted(module['files'])[:10]
            module['components'] = sorted(list(set(module['components'])))[:10]

            # Remove empty modules
            if module['file_count'] == 0:
                continue

        # Remove modules with no files
        modules = {k: v for k, v in modules.items() if v['file_count'] > 0}

        return modules

    def _identify_core_domains(self) -> dict:
        """Identify and describe core business domains."""
        domains = {
            'market_data_processing': {
                'purpose': 'Real-time market data ingestion and processing',
                'key_components': [],
                'data_sources': ['Massive.com WebSocket', 'Synthetic Data Generator'],
                'processing_capacity': '4,000+ tickers with sub-millisecond processing'
            },
            'event_detection': {
                'purpose': 'Identify market patterns and significant events',
                'detection_types': [
                    'High/Low Detection (0.1% threshold)',
                    'Trend Analysis (180/360/600s windows)',
                    'Volume Surge Detection (3x average)'
                ],
                'key_components': []
            },
            'websocket_communication': {
                'purpose': 'Real-time data distribution to clients',
                'architecture': 'Pull-based model with zero event loss',
                'features': [
                    'Per-user filtering',
                    'Event buffering (1000 events/type)',
                    'Independent emission timers'
                ],
                'key_components': []
            },
            'authentication': {
                'purpose': 'User authentication and session management',
                'features': [
                    'Email/SMS verification',
                    'Session tracking',
                    'Rate limiting',
                    'Password reset flows'
                ],
                'key_components': []
            },
            'monitoring': {
                'purpose': 'System health and performance monitoring',
                'metrics': [
                    'Processing latency',
                    'Queue depths',
                    'Event rates',
                    'API health'
                ],
                'key_components': []
            }
        }

        # Map components to domains
        for comp_key, comp_info in self.components.items():
            domain = comp_info.get('domain')
            if domain == 'core_services':
                domains['market_data_processing']['key_components'].append(comp_info['name'])
            elif domain == 'processing':
                domains['event_detection']['key_components'].append(comp_info['name'])
            elif domain == 'presentation':
                domains['websocket_communication']['key_components'].append(comp_info['name'])
            elif domain == 'authentication':
                domains['authentication']['key_components'].append(comp_info['name'])
            elif domain == 'monitoring':
                domains['monitoring']['key_components'].append(comp_info['name'])

        # Limit component lists
        for domain in domains.values():
            if 'key_components' in domain:
                domain['key_components'] = list(set(domain['key_components']))[:8]

        return domains

    def _identify_data_flows(self) -> list[dict]:
        """Identify key data flows through the system."""
        flows = [
            {
                'name': 'Market Data Pipeline',
                'stages': [
                    'Data Source (Massive/Synthetic)',
                    'WebSocket Ingestion',
                    'MarketDataService.handle_tick()',
                    'EventProcessor.process_tick()',
                    'Event Detection (HighLow/Trend/Surge)',
                    'Priority Queue Management',
                    'Worker Pool Processing',
                    'Display Queue (for UI events)',
                    'DataPublisher Collection',
                    'WebSocketPublisher Pull & Emit'
                ],
                'processing_time': 'Sub-millisecond per tick'
            },
            {
                'name': 'Pull Model Event Distribution',
                'description': 'Zero event loss architecture (Sprint 29)',
                'flow': [
                    'Workers → Convert typed events to dicts',
                    'Display Queue → Buffer events',
                    'DataPublisher → Collect & buffer (up to 1000/type)',
                    'WebSocketPublisher → Pull on timer',
                    'Per-user filtering',
                    'WebSocket emission to clients'
                ],
                'benefits': 'Eliminates 37% event loss from push model'
            },
            {
                'name': 'User Authentication Flow',
                'stages': [
                    'Registration/Login Request',
                    'Credential Validation',
                    'Email/SMS Verification',
                    'Session Creation',
                    'JWT Token Generation',
                    'WebSocket Authentication'
                ]
            }
        ]

        return flows

    def _generate_component_inventory(self) -> dict:
        """Generate categorized component inventory."""
        inventory = {
            'core_processing': {
                'description': 'Heart of data processing pipeline',
                'components': []
            },
            'event_processing': {
                'description': 'Event detection and management',
                'components': []
            },
            'websocket_layer': {
                'description': 'Real-time communication',
                'components': []
            },
            'data_providers': {
                'description': 'Data source integrations',
                'components': []
            },
            'infrastructure': {
                'description': 'Supporting services',
                'components': []
            }
        }

        # Track seen components to avoid duplicates
        seen_components = set()

        # Categorize components
        for comp_key, comp_info in self.components.items():
            if not comp_info.get('is_critical'):
                continue

            name = comp_info['name']

            # Skip if already added
            if name in seen_components:
                continue
            seen_components.add(name)

            role = comp_info.get('architectural_role', '')

            comp_summary = {
                'name': name,
                'file': comp_info['file'],
                'type': comp_info['type'],
                'description': comp_info.get('description', '')
            }

            # Clean up descriptions that are just sprint comments
            if 'Sprint' in comp_summary['description'] and ':' in comp_summary['description']:
                # Extract actual description after sprint comment
                parts = comp_summary['description'].split(':', 1)
                if len(parts) > 1:
                    comp_summary['description'] = parts[1].strip()

            if role in ['core_orchestrators', 'orchestrator']:
                inventory['core_processing']['components'].append(comp_summary)
            elif role in ['event_processors', 'event_processor']:
                inventory['event_processing']['components'].append(comp_summary)
            elif role in ['websocket_layer', 'communication']:
                inventory['websocket_layer']['components'].append(comp_summary)
            elif role in ['data_providers', 'data_provider']:
                inventory['data_providers']['components'].append(comp_summary)
            elif role in ['infrastructure_services', 'support']:
                inventory['infrastructure']['components'].append(comp_summary)

        # Sort and limit component lists
        for category in inventory.values():
            # Sort by name for consistency
            category['components'] = sorted(category['components'], key=lambda x: x['name'])[:10]

        return inventory

    def _analyze_websocket_architecture(self) -> dict:
        """Analyze WebSocket architecture and events."""
        ws_components = [comp for comp in self.components.values()
                        if 'websocket' in comp.get('name', '').lower()]

        return {
            'architecture': 'Pull-based distribution model',
            'component_count': len(ws_components),
            'key_components': [comp['name'] for comp in ws_components[:8]],
            'event_types': list(set([e['name'] for e in self.websocket_events[:15]])),
            'features': [
                'Per-user data isolation',
                'Event buffering (1000 events/type)',
                'Independent emission timers',
                'LRU cache with 1-hour TTL',
                'User filter preferences'
            ]
        }

    def _analyze_event_processing(self) -> dict:
        """Analyze event processing architecture."""
        detectors = [comp for comp in self.components.values()
                    if 'detector' in comp.get('name', '').lower()]

        return {
            'detector_count': len(detectors),
            'detectors': [comp['name'] for comp in detectors],
            'event_types': [
                'HighLowEvent (0.1% threshold)',
                'TrendEvent (180/360/600s windows)',
                'SurgeEvent (3x volume average)',
                'ControlEvent (system events)'
            ],
            'processing_model': 'Typed events → Worker conversion → Dict transport',
            'queue_priorities': [
                'P0: Control events',
                'P1: High priority market events',
                'P2: Standard market events',
                'P3: Low priority events',
                'P4: Background tasks'
            ]
        }

    def _analyze_frontend_architecture(self) -> dict:
        """Analyze frontend architecture (JavaScript and CSS)."""
        js_files = [f for f in self.files if f.endswith('.js') and not f.endswith('-min.js')]
        css_files = [f for f in self.files if f.endswith('.css')]

        return {
            'javascript': {
                'file_count': len(js_files),
                'modular_files': [f for f in js_files if 'app-' in f],
                'key_modules': [
                    'app-core.js (Foundation)',
                    'app-universe.js (Universe management)',
                    'app-gauges.js (Visualizations)',
                    'app-events.js (Event handling)',
                    'app-filters.js (Data filtering)'
                ]
            },
            'css': {
                'file_count': len(css_files),
                'architecture': 'Modular component-based',
                'structure': {
                    'base': 'Reset and variables',
                    'layout': 'Grid and layout systems',
                    'components': 'Reusable UI components',
                    'utilities': 'Helper classes and animations'
                }
            },
            'templates': {
                'count': len([f for f in self.files if f.endswith('.html')]),
                'engine': 'Jinja2'
            }
        }

    def _identify_external_dependencies(self) -> dict:
        """Identify external system dependencies."""
        return {
            'data_sources': [
                'Massive.com WebSocket API',
                'Synthetic Data Generator (development)'
            ],
            'databases': [
                'PostgreSQL (user data, analytics)',
                'Redis (caching, session storage)'
            ],
            'messaging': [
                'Twilio (SMS verification)',
                'SMTP (email notifications)'
            ],
            'infrastructure': [
                'Docker (containerization)',
                'Nginx (reverse proxy)',
                'Prometheus (metrics)',
                'Eventlet (async processing)'
            ],
            'frontend': [
                'Socket.IO (real-time communication)',
                'Chart.js (data visualization)',
                'GridStack (layout management)'
            ]
        }

    def _identify_configuration(self) -> dict:
        """Identify configuration structure."""
        config_files = [f for f in self.files
                       if self.files[f].get('domain') == 'configuration']

        return {
            'environment': {
                'files': [f for f in config_files if '.env' in f or 'environments/' in f],
                'description': 'Environment-specific settings'
            },
            'application': {
                'files': [f for f in config_files if 'config/' in f and '.py' in f],
                'description': 'Application configuration modules'
            },
            'deployment': {
                'files': [f for f in config_files if any(x in f for x in ['docker', 'nginx'])],
                'description': 'Container and server configuration'
            },
            'monitoring': {
                'files': [f for f in config_files if 'prometheus' in f or 'logging' in f],
                'description': 'Logging and metrics configuration'
            }
        }

    def _analyze_testing_strategy(self) -> dict:
        """Analyze testing approach."""
        test_files = [f for f in self.files if 'test' in f.lower()]

        return {
            'test_count': len(test_files),
            'coverage': {
                'unit_tests': len([f for f in test_files if 'unit/' in f]),
                'integration_tests': len([f for f in test_files if 'integration/' in f]),
                'performance_tests': len([f for f in test_files if 'performance/' in f])
            },
            'test_categories': {
                'trace_tests': [f for f in test_files if 'trace' in f][:5],
                'component_tests': [f for f in test_files if 'trace' not in f and 'test_' in f][:5]
            },
            'fixtures': len([f for f in test_files if 'fixture' in f])
        }

    def _extract_requirements(self) -> dict:
        """Extract Python dependencies."""
        requirements = {
            'files': [],
            'categories': {
                'web_framework': [],
                'real_time': [],
                'data_processing': [],
                'database': [],
                'monitoring': [],
                'authentication': []
            }
        }

        req_patterns = ['requirements*.txt', 'requirements/*.txt']
        for pattern in req_patterns:
            req_files = Path(self.root_dir).glob(pattern)
            for req_file in req_files:
                if req_file.is_file():
                    requirements['files'].append(str(req_file.relative_to(self.root_dir)))

                    try:
                        content = req_file.read_text()
                        for line in content.split('\n'):
                            line = line.strip()
                            if line and not line.startswith('#'):
                                package = line.split('==')[0].split('>=')[0].split('<')[0]

                                # Categorize
                                if any(x in package.lower() for x in ['flask', 'fastapi', 'django']):
                                    requirements['categories']['web_framework'].append(package)
                                elif any(x in package.lower() for x in ['socketio', 'websocket', 'eventlet']):
                                    requirements['categories']['real_time'].append(package)
                                elif any(x in package.lower() for x in ['pandas', 'numpy', 'requests']):
                                    requirements['categories']['data_processing'].append(package)
                                elif any(x in package.lower() for x in ['sqlalchemy', 'psycopg', 'redis']):
                                    requirements['categories']['database'].append(package)
                                elif any(x in package.lower() for x in ['prometheus', 'logging']):
                                    requirements['categories']['monitoring'].append(package)
                                elif any(x in package.lower() for x in ['jwt', 'auth', 'twilio']):
                                    requirements['categories']['authentication'].append(package)
                    except Exception as e:
                        logger.warning(f"Failed to parse requirements file {req_file}: {e}")

        # Remove duplicates
        for category in requirements['categories']:
            requirements['categories'][category] = list(set(requirements['categories'][category]))[:10]

        return requirements

    def _calculate_quality_metrics(self) -> dict:
        """Calculate code quality metrics."""
        return {
            'modularity_score': self._calculate_modularity_score(),
            'test_coverage': f"{(self.stats['test_files'] / max(self.stats['python_files'], 1) * 100):.1f}%",
            'documentation_files': len([f for f in self.files if f.endswith('.md')]),
            'component_documentation': len([c for c in self.components.values() if c.get('description')]),
            'critical_components': len([c for c in self.components.values() if c.get('is_critical')]),
            'average_file_size': sum(f.get('size', 0) for f in self.files.values()) / max(len(self.files), 1)
        }

    def _calculate_modularity_score(self) -> str:
        """Calculate modularity score based on structure."""
        score = 0

        # Points for good structure
        if any('src/core' in f for f in self.files): score += 2
        if any('src/infrastructure' in f for f in self.files): score += 2
        if any('src/presentation' in f for f in self.files): score += 2
        if any('src/processing' in f for f in self.files): score += 2
        if self.stats['test_files'] > 10: score += 1
        if len(self.components) > 50: score += 1

        if score >= 9: return "Excellent"
        if score >= 7: return "Good"
        if score >= 5: return "Fair"
        return "Needs improvement"

    def _analyze_sprint_references(self) -> dict:
        """Analyze sprint references in code."""
        if not self.sprint_references:
            return {'found': False}

        sprint_numbers = [ref['sprint'] for ref in self.sprint_references]
        unique_sprints = sorted(set(sprint_numbers))

        return {
            'found': True,
            'total_references': len(self.sprint_references),
            'unique_sprints': unique_sprints,
            'latest_sprint': max(sprint_numbers) if sprint_numbers else 0,
            'files_with_references': list(set([ref['file'] for ref in self.sprint_references]))[:10]
        }

    def _classify_domain(self, file_path: str) -> str:
        """Classify file into architectural domain."""
        file_lower = file_path.lower()

        for domain, patterns in self.domain_patterns.items():
            if any(re.search(pattern, file_lower) for pattern in patterns):
                return domain

        return 'core'

    def _determine_architectural_role(self, file_path: str) -> str:
        """Determine the architectural role of a file."""
        filename = os.path.basename(file_path).lower()

        if 'service' in filename or 'manager' in filename:
            return 'service_orchestrator'
        if 'provider' in filename or 'adapter' in filename:
            return 'data_provider'
        if 'detector' in filename or 'processor' in filename:
            return 'event_processor'
        if 'publisher' in filename or 'websocket' in filename:
            return 'communication'
        if 'model' in filename or 'event' in filename:
            return 'domain_model'
        if filename.startswith('test_'):
            return 'test'
        if 'config' in filename:
            return 'configuration'
        return 'support'

    def _determine_component_role(self, component_name: str) -> str:
        """Determine the role of a specific component."""
        name_lower = component_name.lower()

        # Check against critical components
        for category, components in self.critical_components.items():
            if any(comp.lower() in name_lower for comp in components):
                return category

        # Pattern-based classification
        if 'service' in name_lower or 'manager' in name_lower:
            return 'orchestrator'
        if 'provider' in name_lower or 'adapter' in name_lower:
            return 'data_provider'
        if 'detector' in name_lower or 'processor' in name_lower:
            return 'event_processor'
        if 'publisher' in name_lower or 'websocket' in name_lower:
            return 'communication'
        if 'event' in name_lower or 'model' in name_lower:
            return 'domain_model'
        return 'support'



    def _is_architecturally_significant(self, name: str, file_path: str) -> bool:
        """Enhanced filtering for architectural significance."""
        # Skip test helpers and migration scripts
        if any(x in name.lower() for x in ['importfixer', 'migrat', 'test_', 'fixture', 'mock', 'stub']):
            return False

        # Skip logging utilities unless they're managers
        if 'logging' in name.lower() and 'manager' not in name.lower():
            return False

        # Skip trace and debug utilities
        if any(x in name.lower() for x in ['trace', 'debug', 'dump', 'temp_']):
            return False

        # Skip private methods and internal helpers
        if name.startswith('_'):
            return False

        # Always include critical components
        if self._is_critical_component(name):
            return True

        # Include classes (except test classes)
        if name[0].isupper() and not name.startswith('Test'):
            return True

        # Include significant function patterns
        significant_patterns = [
            r'^handle_', r'^process_', r'^detect_', r'^emit_',
            r'^create_', r'^initialize_', r'^register_', r'^connect_',
            r'^manage_', r'^orchestrate_', r'^publish_'
        ]

        if any(re.match(pattern, name) for pattern in significant_patterns):
            return True

        return False



    def _get_file_type(self, file_path: str) -> str:
        """Get file type classification."""
        ext = Path(file_path).suffix.lower()
        type_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.html': 'template',
            '.css': 'stylesheet',
            '.yml': 'yaml_config',
            '.yaml': 'yaml_config',
            '.json': 'json_config',
            '.env': 'environment_config',
            '.ini': 'ini_config',
            '.md': 'documentation',
            '.txt': 'text',
            '.sh': 'shell_script',
            '.bat': 'batch_script'
        }
        return type_map.get(ext, 'other')

    def _analyze_javascript_file(self, file_path: str, rel_path: str):
        """Analyze JavaScript files."""
        try:
            with open(file_path, encoding='utf-8') as file:
                content = file.read()

            # Extract WebSocket events
            socket_patterns = [
                r'socket\.on\s*\(\s*[\'"]([^\'"]+)[\'"]',
                r'socket\.emit\s*\(\s*[\'"]([^\'"]+)[\'"]',
                r'io\.emit\s*\(\s*[\'"]([^\'"]+)[\'"]'
            ]

            for pattern in socket_patterns:
                events = re.findall(pattern, content)
                for event_name in events:
                    self.websocket_events.append({
                        'name': event_name,
                        'file': rel_path,
                        'type': 'emit' if 'emit' in pattern else 'on'
                    })

            # Store analysis results
            self.files[rel_path]['js_analysis'] = {
                'websocket_events': len(events) if 'events' in locals() else 0,
                'size_lines': len(content.split('\n'))
            }

        except Exception as e:
            logger.warning(f"Failed to analyze JavaScript file {file_path}: {e}")

    def _analyze_css_file(self, file_path: str, rel_path: str):
        """Analyze CSS files."""
        try:
            with open(file_path, encoding='utf-8') as file:
                content = file.read()

            self.files[rel_path]['css_analysis'] = {
                'custom_properties': len(re.findall(r'--[\w-]+:', content)),
                'media_queries': len(re.findall(r'@media', content)),
                'size_lines': len(content.split('\n'))
            }

        except Exception as e:
            logger.warning(f"Failed to analyze CSS file {file_path}: {e}")

    def _extract_components_with_regex(self, content: str, rel_path: str):
        """Fallback regex extraction for components when AST parsing fails."""
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\([^)]*\))?:'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            if self._is_architecturally_significant(class_name, rel_path):
                self.components[f"{rel_path}:{class_name}"] = {
                    'name': class_name,
                    'type': 'class',
                    'file': rel_path,
                    'domain': self._classify_domain(rel_path),
                    'module': self._identify_module(rel_path),
                    'architectural_role': self._determine_component_role(class_name),
                    'is_critical': self._is_critical_component(class_name)
                }

        # Extract functions
        func_pattern = r'def\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            if self._is_architecturally_significant(func_name, rel_path):
                self.components[f"{rel_path}:{func_name}"] = {
                    'name': func_name,
                    'type': 'function',
                    'file': rel_path,
                    'domain': self._classify_domain(rel_path),
                    'module': self._identify_module(rel_path),
                    'architectural_role': self._determine_component_role(func_name)
                }


def save_structure(structure: dict, output_file: str):
    """Save the architectural structure to enhanced Markdown file."""
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate enhanced Markdown
        markdown = generate_enhanced_markdown(structure)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        logger.info(f"Documentation saved to {output_file}")

    except Exception as e:
        logger.error(f"Failed to save documentation: {e}")


def generate_enhanced_markdown(structure: dict) -> str:
    """Generate enhanced Markdown documentation."""
    md = []

    # Header
    md.append("# TickStock V2 - Project Structure Documentation\n")
    md.append(f"*Generated: {structure['metadata']['generated_at']}*\n")
    md.append(f"*Version: {structure['metadata']['version']}*\n")
    md.append(f"*Architecture: {structure['metadata']['structure_type']}*\n\n")

    # Table of Contents
    md.append("## Table of Contents\n")
    md.append("1. [Application Overview](#application-overview)\n")
    md.append("2. [System Architecture](#system-architecture)\n")
    md.append("3. [Module Structure](#module-structure)\n")
    md.append("4. [Core Domains](#core-domains)\n")
    md.append("5. [Data Flows](#data-flows)\n")
    md.append("6. [Component Inventory](#component-inventory)\n")
    md.append("7. [WebSocket Architecture](#websocket-architecture)\n")
    md.append("8. [Event Processing](#event-processing)\n")
    md.append("9. [External Dependencies](#external-dependencies)\n")
    md.append("10. [Configuration](#configuration)\n")
    md.append("11. [Testing Strategy](#testing-strategy)\n")
    md.append("12. [Frontend Architecture](#frontend-architecture)\n")
    md.append("13. [Quality Metrics](#quality-metrics)\n")
    md.append("14. [Sprint Tracking](#sprint-tracking)\n\n")

    # Application Overview
    md.append("## Application Overview\n")
    app = structure.get('application', {})
    md.append(f"**{app.get('name', 'TickStock')}** - {app.get('description', '')}\n\n")
    md.append(f"- **Type**: {app.get('type', 'N/A')}\n")
    md.append(f"- **Backend**: {app.get('backend', 'N/A')}\n")
    md.append(f"- **Frontend**: {app.get('frontend', 'N/A')}\n")
    md.append(f"- **Architecture**: {app.get('architecture_pattern', 'N/A')}\n")
    md.append(f"- **Data Flow**: {app.get('data_flow', 'N/A')}\n\n")

    if app.get('key_features'):
        md.append("### Key Features\n")
        for feature in app['key_features']:
            md.append(f"- {feature}\n")
        md.append("\n")

    # System Architecture
    md.append("## System Architecture\n")
    arch = structure.get('architecture', {})
    md.append(f"**Pattern**: {arch.get('pattern', 'N/A')}\n\n")

    if arch.get('layers'):
        md.append("### Architectural Layers\n")
        for layer, desc in arch['layers'].items():
            md.append(f"- **{layer.title()}**: {desc}\n")
        md.append("\n")

    if arch.get('key_patterns'):
        md.append("### Design Patterns\n")
        for pattern in arch['key_patterns']:
            md.append(f"- {pattern}\n")
        md.append("\n")

    # Module Structure
    md.append("## Module Structure\n")
    modules = structure.get('module_structure', {})
    for module_name, module_info in modules.items():
        if module_name != 'Unknown':
            md.append(f"### {module_name}\n")
            md.append(f"*{module_info.get('description', '')}*\n\n")
            md.append(f"- **Files**: {module_info.get('file_count', 0)}\n")
            md.append(f"- **Components**: {module_info.get('component_count', 0)}\n")
            if module_info.get('components'):
                md.append("- **Key Components**: " + ", ".join(module_info['components'][:5]) + "\n")
            md.append("\n")

    # Core Domains
    md.append("## Core Domains\n")
    for domain, details in structure.get('core_domains', {}).items():
        md.append(f"### {domain.replace('_', ' ').title()}\n")
        md.append(f"**Purpose**: {details.get('purpose', 'N/A')}\n\n")

        for key, value in details.items():
            if key != 'purpose' and key != 'key_components':
                if isinstance(value, list):
                    md.append(f"**{key.replace('_', ' ').title()}**:\n")
                    for item in value:
                        md.append(f"- {item}\n")
                elif isinstance(value, str):
                    md.append(f"**{key.replace('_', ' ').title()}**: {value}\n")

        if details.get('key_components'):
            md.append("\n**Key Components**:\n")
            for comp in details['key_components'][:8]:
                md.append(f"- `{comp}`\n")
        md.append("\n")

    # Data Flows
    md.append("## Data Flows\n")
    for flow in structure.get('key_data_flows', []):
        md.append(f"### {flow.get('name', 'Unnamed Flow')}\n")

        if flow.get('description'):
            md.append(f"*{flow['description']}*\n\n")

        if flow.get('stages'):
            md.append("**Stages**:\n")
            for i, stage in enumerate(flow['stages'], 1):
                md.append(f"{i}. {stage}\n")
        elif flow.get('flow'):
            md.append("**Flow**:\n")
            for step in flow['flow']:
                md.append(f"- {step}\n")

        if flow.get('processing_time'):
            md.append(f"\n**Processing Time**: {flow['processing_time']}\n")

        if flow.get('benefits'):
            md.append(f"**Benefits**: {flow['benefits']}\n")

        md.append("\n")

    # Component Inventory
    md.append("## Component Inventory\n")
    inventory = structure.get('component_inventory', {})
    for category, info in inventory.items():
        if info.get('components'):
            md.append(f"### {category.replace('_', ' ').title()}\n")
            md.append(f"*{info.get('description', '')}*\n\n")
            for comp in info['components'][:10]:
                md.append(f"- **{comp['name']}** ({comp['type']})\n")
                if comp.get('description'):
                    md.append(f"  - {comp['description']}\n")
            md.append("\n")

    # WebSocket Architecture
    md.append("## WebSocket Architecture\n")
    ws = structure.get('websocket_architecture', {})
    md.append(f"**Architecture**: {ws.get('architecture', 'N/A')}\n")
    md.append(f"**Components**: {ws.get('component_count', 0)}\n\n")

    if ws.get('features'):
        md.append("### Features\n")
        for feature in ws['features']:
            md.append(f"- {feature}\n")
        md.append("\n")

    if ws.get('event_types'):
        md.append("### Event Types\n")
        for event in ws['event_types'][:10]:
            md.append(f"- `{event}`\n")
        md.append("\n")

    # Event Processing
    md.append("## Event Processing\n")
    events = structure.get('event_processing', {})
    md.append(f"**Detectors**: {events.get('detector_count', 0)}\n")
    md.append(f"**Processing Model**: {events.get('processing_model', 'N/A')}\n\n")

    if events.get('event_types'):
        md.append("### Event Types\n")
        for event_type in events['event_types']:
            md.append(f"- {event_type}\n")
        md.append("\n")

    if events.get('queue_priorities'):
        md.append("### Queue Priorities\n")
        for priority in events['queue_priorities']:
            md.append(f"- {priority}\n")
        md.append("\n")

    # External Dependencies
    md.append("## External Dependencies\n")
    deps = structure.get('external_dependencies', {})
    for category, items in deps.items():
        if items:
            md.append(f"### {category.replace('_', ' ').title()}\n")
            for item in items:
                md.append(f"- {item}\n")
            md.append("\n")

    # Configuration
    md.append("## Configuration\n")
    config = structure.get('configuration', {})
    for category, info in config.items():
        if info.get('files'):
            md.append(f"### {category.title()}\n")
            md.append(f"*{info.get('description', '')}*\n")
            for file in info['files'][:5]:
                md.append(f"- `{file}`\n")
            md.append("\n")

    # Testing Strategy
    md.append("## Testing Strategy\n")
    testing = structure.get('testing_strategy', {})
    md.append(f"**Total Tests**: {testing.get('test_count', 0)}\n\n")

    if testing.get('coverage'):
        md.append("### Coverage\n")
        for test_type, count in testing['coverage'].items():
            md.append(f"- **{test_type.replace('_', ' ').title()}**: {count}\n")
        md.append("\n")

    # Frontend Architecture
    md.append("## Frontend Architecture\n")
    frontend = structure.get('frontend_architecture', {})

    if frontend.get('javascript'):
        js = frontend['javascript']
        md.append("### JavaScript\n")
        md.append(f"- **Files**: {js.get('file_count', 0)}\n")
        md.append(f"- **Modular Files**: {len(js.get('modular_files', []))}\n")
        if js.get('key_modules'):
            md.append("- **Key Modules**:\n")
            for module in js['key_modules']:
                md.append(f"  - {module}\n")
        md.append("\n")

    if frontend.get('css'):
        css = frontend['css']
        md.append("### CSS\n")
        md.append(f"- **Files**: {css.get('file_count', 0)}\n")
        md.append(f"- **Architecture**: {css.get('architecture', 'N/A')}\n")
        md.append("\n")

    # Quality Metrics
    md.append("## Quality Metrics\n")
    metrics = structure.get('quality_metrics', {})
    md.append(f"- **Modularity Score**: {metrics.get('modularity_score', 'N/A')}\n")
    md.append(f"- **Test Coverage**: {metrics.get('test_coverage', 'N/A')}\n")
    md.append(f"- **Documentation Files**: {metrics.get('documentation_files', 0)}\n")
    md.append(f"- **Critical Components**: {metrics.get('critical_components', 0)}\n")
    md.append(f"- **Component Documentation**: {metrics.get('component_documentation', 0)}\n\n")

    # Sprint Tracking
    if structure.get('sprint_tracking', {}).get('found'):
        sprint = structure['sprint_tracking']
        md.append("## Sprint Tracking\n")
        md.append(f"- **Latest Sprint**: Sprint {sprint.get('latest_sprint', 0)}\n")
        md.append(f"- **Total References**: {sprint.get('total_references', 0)}\n")
        md.append(f"- **Unique Sprints**: {', '.join(map(str, sprint.get('unique_sprints', [])))}\n\n")

    # Statistics
    md.append("## Statistics\n")
    stats = structure.get('statistics', {})
    md.append(f"- **Total Files**: {stats.get('total_files', 0)}\n")
    md.append(f"- **Python Files**: {stats.get('python_files', 0)}\n")
    md.append(f"- **JavaScript Files**: {stats.get('js_files', 0)}\n")
    md.append(f"- **CSS Files**: {stats.get('css_files', 0)}\n")
    md.append(f"- **Test Files**: {stats.get('test_files', 0)}\n")
    md.append(f"- **Config Files**: {stats.get('config_files', 0)}\n\n")

    # Footer
    md.append("---\n")
    md.append("*This documentation was automatically generated from the project structure.*\n")

    return ''.join(md)


def main():
    parser = argparse.ArgumentParser(
        description="Generate architectural project documentation for TickStock V2"
    )

    # Update default paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_root_dir = os.path.dirname(os.path.dirname(script_dir))  # Go up two levels from scripts/dev_tools

    parser.add_argument(
        "--root-dir",
        default=default_root_dir,
        help="Root directory of the project"
    )
    parser.add_argument(
        "--output-file",
        default=os.path.join(default_root_dir, "docs/development", "new", "project_structure_docs.md"),
        help="Output Markdown file path"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run analysis
    print(f"🔍 Analyzing project structure in {args.root_dir}...")
    analyzer = CreateProjectStructureDocumentation(args.root_dir)
    structure = analyzer.analyze_project()

    # Save documentation
    save_structure(structure, args.output_file)

    # Print summary
    print(f"\n{'='*60}")
    print("📊 TickStock V2 Documentation Generation Complete")
    print(f"{'='*60}")
    print(f"📁 Files analyzed: {structure['statistics']['total_files']}")
    print(f"🐍 Python files: {structure['statistics']['python_files']}")
    print(f"🌐 JavaScript files: {structure['statistics']['js_files']}")
    print(f"🎨 CSS files: {structure['statistics']['css_files']}")
    print(f"🧪 Test files: {structure['statistics']['test_files']}")
    print(f"⚙️  Config files: {structure['statistics']['config_files']}")
    print(f"🔧 Components found: {structure['metadata']['total_components']}")
    print(f"📊 Quality Score: {structure['quality_metrics']['modularity_score']}")

    if structure.get('sprint_tracking', {}).get('found'):
        print(f"🚀 Latest Sprint: Sprint {structure['sprint_tracking']['latest_sprint']}")

    print(f"\n✅ Documentation saved to: {args.output_file}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
