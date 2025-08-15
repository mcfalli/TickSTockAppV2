import os
import ast
import json
import logging
import argparse
from typing import Dict, List, Set, Optional
from pathlib import Path
import re

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
    emphasizing domains, data flows, and system boundaries.
    """
    
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.files = {}
        self.components = {}
        self.routes = []
        self.websocket_events = []
        
        # Domain classification patterns
        self.domain_patterns = {
            'market_data': [
                r'market.*data', r'polygon', r'stock.*tick', r'real.*time.*data',
                r'synthetic.*data', r'data.*provider', r'websocket.*client'
            ],
            'authentication': [
                r'auth', r'login', r'register', r'session', r'user', r'verification'
            ],
            'event_detection': [
                r'detector', r'trend', r'surge', r'buysell', r'tracker', r'event'
            ],
            'real_time_communication': [
                r'websocket', r'socket.*io', r'publisher', r'broadcast'
            ],
            'css_architecture': [
                r'base.*css', r'variables.*css', r'reset.*css', r'layout.*css',
                r'components.*css', r'utilities.*css', r'main.*css'
            ],
            'configuration': [
                r'config', r'settings', r'env', r'docker', r'nginx', r'prometheus'
            ],
            'utilities': [
                r'util', r'helper', r'debug', r'logger', r'cache'
            ],
            'testing': [
                r'test', r'conftest', r'pytest'
            ],
            'user_interface': [
                r'template', r'static', r'css', r'js', r'html'
            ]
        }
        
        # Critical architectural components
        self.critical_components = {
            'orchestrators': [
                'MarketDataService', 'WebSocketManager', 'AuthenticationManager'
            ],
            'data_providers': [
                'PolygonDataProvider', 'SimulatedDataProvider', 'DataProviderFactory'
            ],
            'event_processors': [
                'HighLowDetector', 'TrendDetector', 'SurgeDetector'
            ],
            'communication': [
                'WebSocketPublisher', 'EmailManager', 'SMSManager'
            ]
        }
        
        # Noise imports to filter out
        self.noise_imports = {
            'logging', 'os', 'sys', 'time', 'datetime', 'json', 'typing',
            'pathlib', 're', 'uuid', 'secrets', 'string', 'random', 'math',
            'csv', 'argparse', 'traceback', 'threading', 'queue'
        }

    def analyze_project(self) -> Dict:
        """Main analysis method that returns architectural overview."""
        self._scan_files()
        
        return {
            "application": self._generate_application_overview(),
            "core_domains": self._identify_core_domains(),
            "key_data_flows": self._identify_data_flows(),
            "external_dependencies": self._identify_external_dependencies(),
            "configuration": self._identify_configuration(),
            "testing_strategy": self._analyze_testing_strategy(),
            "css_architecture": self._analyze_css_architecture(), 
            "js_architecture": self._analyze_js_architecture(),  
            "requirements": self._extract_requirements(),  
            "file_inventory": self._generate_file_inventory(),
            "critical_relationships": self._identify_critical_relationships()
        }

    def _scan_files(self):
        """Scan project files and extract components."""
        exclude_dirs = {'.git', '__pycache__', 'venv', '.venv', 'env', '.env', 'logs', 'data', 'node_modules', 'dev_tools'}
        include_patterns = [r"\.py$", r"\.js$", r"\.html$", r"\.css$", r"\.yml$", r"\.yaml$", r"\.json$", r"\.env$", r"\.txt$", r"\.ico$", r"\.ini$", r"\.bat$", r"Dockerfile$", r"nginx\.conf$"]
        
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.root_dir).replace('\\', '/')
                
                if any(re.search(pattern, file, re.IGNORECASE) for pattern in include_patterns):
                    self._analyze_file(file_path, rel_path)

    def _analyze_file(self, file_path: str, rel_path: str):
        """Analyze individual file for architectural significance."""
        try:
            # Initialize file info first
            self.files[rel_path] = {
                'type': self._get_file_type(file_path),
                'domain': self._classify_domain(rel_path),
                'architectural_role': self._determine_architectural_role(rel_path)
            }
            
            # Then run specific analysis (which may add to the file info)
            if file_path.endswith('.py'):
                self._analyze_python_file(file_path, rel_path)
            elif file_path.endswith('.js') and not file_path.endswith('-min.js'):
                self._analyze_javascript_file(file_path, rel_path)
            elif file_path.endswith('.css'):
                self._analyze_css_file(file_path, rel_path)
                
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")

    def _analyze_python_file(self, file_path: str, rel_path: str):
        """Extract architectural components from Python files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Extract routes for main app file
            if rel_path == 'app.py':
                route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"]'
                self.routes.extend(re.findall(route_pattern, content))
            
            # Parse AST for components
            try:
                tree = ast.parse(content, filename=file_path)
                self._extract_components_from_ast(tree, rel_path)
            except SyntaxError:
                # Fallback to regex for syntax errors
                self._extract_components_with_regex(content, rel_path)
                
        except Exception as e:
            logger.warning(f"Failed to analyze Python file {file_path}: {e}")

    def _analyze_javascript_file(self, file_path: str, rel_path: str):
        """Enhanced JavaScript analysis for modular architecture."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Extract WebSocket events
            socket_pattern = r'socket\.(on|emit)\s*\(\s*[\'"]([^\'"]+)[\'"]'
            events = re.findall(socket_pattern, content)
            for direction, event_name in events:
                self.websocket_events.append({
                    "name": event_name,
                    "direction": direction,
                    "file": rel_path
                })
            
            # Extract JavaScript classes
            class_pattern = r'class\s+(\w+)\s*(?:extends\s+\w+)?\s*\{'
            classes = re.findall(class_pattern, content)
            
            # Extract significant functions
            function_patterns = [
                r'function\s+(\w+)\s*\(',  # function declarations
                r'(\w+)\s*:\s*function\s*\(',  # object methods
                r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function',  # function expressions
                r'(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>', # arrow functions
            ]
            
            functions = []
            for pattern in function_patterns:
                functions.extend(re.findall(pattern, content))
            
            # Analyze JavaScript architecture
            js_info = {
                'classes': len(classes),
                'functions': len(functions),
                'socket_events': len(events),
                'global_variables': len(re.findall(r'(?:window\.|global\.)\w+\s*=', content)),
                'module_exports': len(re.findall(r'(?:module\.exports|export)', content)),
                'dom_manipulations': len(re.findall(r'document\.(?:getElementById|querySelector|createElement)', content)),
                'event_listeners': len(re.findall(r'addEventListener\s*\(', content)),
                'size_lines': len(content.split('\n')),
                'enterprise_comments': content.count('==========') + content.count('Sprint'),
                'chart_js_usage': bool(re.search(r'Chart\.js|new Chart|Chart\(', content)),
                'modular_structure': bool(re.search(r'console\.log.*loaded.*initializing', content))
            }
            
            # Store JS-specific analysis
            if rel_path not in self.files:
                self.files[rel_path] = {}
            
            self.files[rel_path]['js_analysis'] = js_info
            
            # Extract significant JavaScript components
            for class_name in classes:
                if self._is_js_component_significant(class_name, rel_path):
                    self.components[f"{rel_path}:{class_name}"] = {
                        'name': class_name,
                        'type': 'js_class',
                        'file': rel_path,
                        'domain': self._classify_js_domain(rel_path, class_name),
                        'architectural_role': self._determine_js_role(class_name),
                        'module_type': self._determine_js_module_type(rel_path)
                    }
            
            for func_name in functions:
                if self._is_js_component_significant(func_name, rel_path):
                    self.components[f"{rel_path}:{func_name}"] = {
                        'name': func_name,
                        'type': 'js_function',
                        'file': rel_path,
                        'domain': self._classify_js_domain(rel_path, func_name),
                        'architectural_role': self._determine_js_role(func_name),
                        'module_type': self._determine_js_module_type(rel_path)
                    }
                    
        except Exception as e:
            logger.warning(f"Failed to analyze JavaScript file {file_path}: {e}")

    def _is_js_component_significant(self, name: str, file_path: str) -> bool:
        """Determine if a JavaScript component is architecturally significant."""
        # Always include classes (they start with uppercase)
        if name and name[0].isupper():
            return True
        
        # Include significant function patterns
        significant_patterns = [
            r'update.*', r'create.*', r'initialize.*', r'process.*', r'handle.*',
            r'manage.*', r'connect.*', r'disconnect.*', r'emit.*', r'broadcast.*',
            r'.*Manager$', r'.*Handler$', r'.*Controller$', r'.*Service$'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in significant_patterns):
            return True
        
        # Include Chart.js related functions
        chart_patterns = [r'.*[Gg]auge.*', r'.*[Cc]hart.*', r'.*[Vv]isualization.*']
        if any(re.search(pattern, name) for pattern in chart_patterns):
            return True
        
        return False

    def _classify_js_domain(self, file_path: str, component_name: str) -> str:
        """Classify JavaScript component into domain."""
        filename = os.path.basename(file_path).lower()
        name_lower = component_name.lower()
        
        if 'app-universe' in filename or 'universe' in name_lower or 'session' in name_lower:
            return 'universe_management'
        elif 'app-gauges' in filename or 'gauge' in name_lower or 'chart' in name_lower:
            return 'data_visualization'
        elif 'app-events' in filename or 'event' in name_lower or 'trending' in name_lower or 'surge' in name_lower:
            return 'event_processing'
        elif 'app-core' in filename or 'socket' in name_lower or 'utility' in name_lower:
            return 'core_infrastructure'
        else:
            return 'frontend'

    def _determine_js_role(self, component_name: str) -> str:
        """Determine the architectural role of a JavaScript component."""
        name_lower = component_name.lower()
        
        if 'manager' in name_lower:
            return 'frontend_manager'
        elif 'gauge' in name_lower or 'chart' in name_lower:
            return 'visualization_component'
        elif 'session' in name_lower:
            return 'session_handler'
        elif 'universe' in name_lower:
            return 'universe_controller'
        elif 'update' in name_lower or 'process' in name_lower:
            return 'data_processor'
        elif 'create' in name_lower or 'format' in name_lower:
            return 'ui_builder'
        else:
            return 'utility_function'

    def _determine_js_module_type(self, file_path: str) -> str:
        """Determine the type of JavaScript module."""
        filename = os.path.basename(file_path)
        
        if 'app-core' in filename:
            return 'core_foundation'
        elif 'app-universe' in filename:
            return 'universe_management'
        elif 'app-gauges' in filename:
            return 'visualization_system'
        elif 'app-events' in filename:
            return 'event_processing'
        else:
            return 'utility_module'
    
    def _analyze_js_architecture(self) -> Dict:
        """Analyze JavaScript modular architecture."""
        js_files = {f: info for f, info in self.files.items() if f.endswith('.js') and not f.endswith('-min.js')}
        
        # Count architectural elements
        total_classes = 0
        total_functions = 0
        total_dom_manipulations = 0
        total_event_listeners = 0
        modular_files = 0
        
        for file_path, file_info in js_files.items():
            if isinstance(file_info, dict) and 'js_analysis' in file_info:
                analysis = file_info['js_analysis']
                total_classes += analysis.get('classes', 0)
                total_functions += analysis.get('functions', 0)
                total_dom_manipulations += analysis.get('dom_manipulations', 0)
                total_event_listeners += analysis.get('event_listeners', 0)
                if analysis.get('modular_structure', False):
                    modular_files += 1
        
        # Detect architecture maturity
        has_modular_structure = modular_files >= 3
        has_class_architecture = total_classes >= 3
        has_proper_separation = len([f for f in js_files if 'app-' in f]) >= 3
        
        if has_modular_structure and has_class_architecture and has_proper_separation:
            architecture_type = "Modular Enterprise"
        elif has_modular_structure:
            architecture_type = "Modular"
        elif len(js_files) > 1:
            architecture_type = "Multi-file"
        else:
            architecture_type = "Monolithic"
        
        return {
            "architecture_type": architecture_type,
            "total_js_files": len(js_files),
            "modular_files": [f for f in js_files if 'app-' in f],
            "total_classes": total_classes,
            "total_functions": total_functions,
            "dom_interactions": total_dom_manipulations,
            "event_handling": total_event_listeners,
            "websocket_events": len(self.websocket_events),
            "module_separation": {
                "core_foundation": bool([f for f in js_files if 'app-core' in f]),
                "universe_management": bool([f for f in js_files if 'app-universe' in f]),
                "visualization_system": bool([f for f in js_files if 'app-gauges' in f]),
                "event_processing": bool([f for f in js_files if 'app-events' in f])
            },
            "enterprise_standards": {
                "modular_architecture": has_modular_structure,
                "class_based_design": has_class_architecture,
                "proper_separation": has_proper_separation,
                "documented_modules": modular_files
            }
        }

    def _analyze_css_file(self, file_path: str, rel_path: str):
        """Analyze CSS files for modular architecture patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Detect CSS architecture patterns
            css_info = {
                'imports': len(re.findall(r'@import\s+url\(', content)),
                'custom_properties': len(re.findall(r'--[\w-]+:', content)),
                'components_documented': '===============' in content,
                'responsive_breakpoints': len(re.findall(r'@media\s*\(', content)),
                'accessibility_features': bool(re.search(r'prefers-|aria-|sr-only|focus-visible', content)),
                'size_lines': len(content.split('\n')),
                'enterprise_comments': content.count('PURPOSE:') + content.count('COMPONENTS INCLUDED:')
            }
            
            # Store CSS-specific analysis
            if rel_path not in self.files:
                self.files[rel_path] = {}
            
            self.files[rel_path]['css_analysis'] = css_info
            
            # Detect significant CSS components/utilities
            if css_info['enterprise_comments'] > 0 or css_info['custom_properties'] > 10:
                component_name = os.path.basename(rel_path).replace('.css', '')
                self.components[f"{rel_path}:{component_name}"] = {
                    'name': component_name,
                    'type': 'css_module',
                    'file': rel_path,
                    'domain': self._classify_domain(rel_path),
                    'architectural_role': self._determine_css_role(rel_path),
                    'css_properties': css_info['custom_properties'],
                    'responsive': css_info['responsive_breakpoints'] > 0,
                    'documented': css_info['components_documented']
                }
                
        except Exception as e:
            logger.warning(f"Failed to analyze CSS file {file_path}: {e}")

    def _extract_components_from_ast(self, tree: ast.AST, rel_path: str):
        """Extract classes and significant functions from AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                if self._is_architecturally_significant(class_name, rel_path):
                    docstring = ast.get_docstring(node) or ""
                    self.components[f"{rel_path}:{class_name}"] = {
                        'name': class_name,
                        'type': 'class',
                        'file': rel_path,
                        'domain': self._classify_domain(rel_path),
                        'architectural_role': self._determine_component_role(class_name),
                        'description': docstring.split('\n')[0][:100] if docstring else ""
                    }
            
            elif isinstance(node, ast.FunctionDef):
                func_name = node.name
                if self._is_architecturally_significant(func_name, rel_path):
                    docstring = ast.get_docstring(node) or ""
                    self.components[f"{rel_path}:{func_name}"] = {
                        'name': func_name,
                        'type': 'function',
                        'file': rel_path,
                        'domain': self._classify_domain(rel_path),
                        'architectural_role': self._determine_component_role(func_name),
                        'description': docstring.split('\n')[0][:100] if docstring else ""
                    }

    def _extract_components_with_regex(self, content: str, rel_path: str):
        """Fallback regex extraction for components."""
        # Extract classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            if self._is_architecturally_significant(class_name, rel_path):
                self.components[f"{rel_path}:{class_name}"] = {
                    'name': class_name,
                    'type': 'class',
                    'file': rel_path,
                    'domain': self._classify_domain(rel_path),
                    'architectural_role': self._determine_component_role(class_name)
                }
        
        # Extract significant functions
        func_pattern = r'def\s+(\w+)'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            if self._is_architecturally_significant(func_name, rel_path):
                self.components[f"{rel_path}:{func_name}"] = {
                    'name': func_name,
                    'type': 'function',
                    'file': rel_path,
                    'domain': self._classify_domain(rel_path),
                    'architectural_role': self._determine_component_role(func_name)
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
        elif 'provider' in filename or 'client' in filename:
            return 'data_provider'
        elif 'detector' in filename or 'tracker' in filename:
            return 'event_processor'
        elif 'publisher' in filename or 'websocket' in filename:
            return 'communication'
        elif 'model' in filename or 'schema' in filename:
            return 'data_model'
        elif filename.startswith('test_'):
            return 'test'
        elif filename in ['app.py', 'main.py']:
            return 'application_entry'
        elif 'config' in filename or filename.startswith('.env'):
            return 'configuration'
        else:
            return 'support'

    def _determine_component_role(self, component_name: str) -> str:
        """Determine the role of a specific component."""
        name_lower = component_name.lower()
        
        # Check critical component categories
        for category, components in self.critical_components.items():
            if any(comp.lower() in name_lower for comp in components):
                return category
        
        # Pattern-based classification
        if 'service' in name_lower or 'manager' in name_lower:
            return 'orchestrator'
        elif 'provider' in name_lower or 'client' in name_lower:
            return 'data_provider'
        elif 'detector' in name_lower or 'tracker' in name_lower:
            return 'event_processor'
        elif 'publisher' in name_lower or 'socket' in name_lower:
            return 'communication'
        else:
            return 'support'

    def _determine_css_role(self, file_path: str) -> str:
        """Determine the architectural role of a CSS file."""
        filename = os.path.basename(file_path).lower()
        
        if 'main.css' in filename:
            return 'css_entry_point'
        elif 'variables.css' in filename:
            return 'design_system_foundation'
        elif 'reset.css' in filename or 'base.css' in filename:
            return 'css_base_layer'
        elif 'components/' in file_path:
            return 'css_component'
        elif 'utilities/' in file_path or 'animations' in filename:
            return 'css_utilities'
        elif 'layout/' in file_path or 'grid' in filename:
            return 'css_layout_system'
        elif 'auth.css' in filename:
            return 'css_page_specific'
        else:
            return 'css_support'

    def _is_architecturally_significant(self, name: str, file_path: str) -> bool:
        """Determine if a component is architecturally significant."""
        # Always include critical components
        for components in self.critical_components.values():
            if any(comp.lower() in name.lower() for comp in components):
                return True
        
        # Include classes
        if name[0].isupper():
            return True
            
        # Include significant functions (not private/utility)
        if not name.startswith('_') and not name.startswith('test_'):
            significant_patterns = [
                r'handle_', r'process_', r'manage_', r'create_', r'generate_',
                r'detect_', r'track_', r'publish_', r'broadcast_', r'connect_',
                r'authenticate_', r'register_', r'login_', r'logout_'
            ]
            if any(re.search(pattern, name, re.IGNORECASE) for pattern in significant_patterns):
                return True
        
        return False

    def _get_file_type(self, file_path: str) -> str:
        """Get file type classification."""
        ext = Path(file_path).suffix.lower()
        if ext == '.py':
            return 'python'
        elif ext == '.js':
            return 'javascript'
        elif ext in ['.html', '.htm']:
            return 'template'
        elif ext == '.css':
            return 'stylesheet'
        elif ext in ['.yml', '.yaml']:
            return 'yaml_config'
        elif ext == '.json':
            return 'json_config'
        elif ext in ['.env', '.ini']:
            return 'environment_config'
        else:
            return 'other'

    def _generate_application_overview(self) -> Dict:
        """Generate high-level application overview."""
        has_flask = any('flask' in str(self.components.get(comp, {})) for comp in self.components)
        has_socketio = bool(self.websocket_events)
        has_real_time = any('websocket' in file for file in self.files)
        
        app_type = "Single Page Application" if has_real_time else "Web Application"
        
        # Detect architecture pattern
        has_event_detection = any('detector' in file for file in self.files)
        has_services = any('service' in file for file in self.files)
        
        if has_event_detection and has_services:
            pattern = "Event-driven microservices"
        elif has_services:
            pattern = "Service-oriented"
        else:
            pattern = "Monolithic"
        
        return {
            "type": app_type,
            "backend": "Flask with Flask-SocketIO" if has_flask and has_socketio else "Flask",
            "frontend": "JavaScript with Socket.IO" if has_socketio else "Server-side rendered",
            "description": "Real-time market data processing and visualization",
            "architecture_pattern": pattern,
            "data_flow": self._infer_primary_data_flow(),
            "routes": self.routes[:20],  # Limit to prevent overflow
            "websocket_events": [event['name'] for event in self.websocket_events[:10]]
        }

    def _infer_primary_data_flow(self) -> str:
        """Infer the primary data flow through the system."""
        components = list(self.components.keys())
        
        # Look for data flow indicators
        has_polygon = any('polygon' in comp.lower() for comp in components)
        has_websocket = any('websocket' in comp.lower() for comp in components)
        has_detector = any('detector' in comp.lower() for comp in components)
        has_frontend = any('app.js' in file for file in self.files)
        
        if has_polygon and has_websocket and has_detector and has_frontend:
            return "Polygon API → WebSocket → Event Detection → Frontend Visualization"
        elif has_websocket and has_frontend:
            return "Data Sources → WebSocket → Frontend"
        else:
            return "Request → Processing → Response"

    def _identify_core_domains(self) -> Dict:
        """Identify and describe core business domains."""
        domains = {}
        
        # Group components by domain
        domain_components = {}
        for comp_key, comp_info in self.components.items():
            domain = comp_info['domain']
            if domain not in domain_components:
                domain_components[domain] = []
            domain_components[domain].append(comp_info['name'])
        
        # Define domain purposes and features
        domain_descriptions = {
            'market_data': {
                'purpose': 'Real-time stock data ingestion and processing',
                'data_sources': ['Polygon.io API', 'Synthetic data generators'],
                'features': ['Live price feeds', 'Volume tracking', 'Market status monitoring']
            },
            'authentication': {
                'purpose': 'User management and session handling',
                'features': ['Email verification', 'SMS 2FA', 'Rate limiting', 'Session management']
            },
            'event_detection': {
                'purpose': 'Identify trading patterns and market events',
                'algorithms': ['Price trend analysis', 'Volume surge detection', 'High/low tracking']
            },
            'real_time_communication': {
                'purpose': 'Live data streaming to frontend',
                'events': list(set([event['name'] for event in self.websocket_events]))
            },
            'user_interface': {
                'purpose': 'Frontend visualization and user interaction',
                'components': ['Trading dashboard', 'Authentication forms', 'Real-time charts']
            }
        }
        
        for domain, components in domain_components.items():
            if domain in domain_descriptions:
                domains[domain] = {
                    **domain_descriptions[domain],
                    'key_components': components[:5]  # Limit to prevent overflow
                }
        
        return domains

    def _identify_data_flows(self) -> List[Dict]:
        """Identify key data flows through the system."""
        flows = []
        
        # Market data pipeline
        if any('polygon' in comp.lower() for comp in self.components):
            flows.append({
                'name': 'Market Data Pipeline',
                'flow': 'Polygon API → PolygonWebSocketClient → MarketDataService → Event Detectors → WebSocketPublisher → Frontend',
                'trigger': 'Real-time market tick data',
                'components': ['PolygonWebSocketClient', 'MarketDataService', 'HighLowDetector', 'WebSocketPublisher']
            })
        
        # Authentication flow
        if any('auth' in comp.lower() for comp in self.components):
            flows.append({
                'name': 'User Authentication',
                'flow': 'Registration → Email Verification → Login → Session Creation → Rate Limiting',
                'trigger': 'User registration/login attempts',
                'components': ['RegistrationManager', 'AuthenticationManager', 'SessionManager']
            })
        
        # Event detection flow
        if any('detector' in comp.lower() for comp in self.components):
            flows.append({
                'name': 'Event Detection',
                'flow': 'Market Tick → Event Detectors → Pattern Analysis → Alert Generation → Frontend Notification',
                'trigger': 'Market data changes meeting detection criteria',
                'components': ['HighLowDetector', 'TrendDetector', 'SurgeDetector']
            })
        
        return flows

    def _identify_external_dependencies(self) -> Dict:
        """Identify external system dependencies."""
        dependencies = {
            'apis': [],
            'databases': [],
            'infrastructure': []
        }
        
        # Scan for API dependencies
        if any('polygon' in file.lower() for file in self.files):
            dependencies['apis'].append('Polygon.io (market data)')
        if any('twilio' in comp.lower() for comp in self.components):
            dependencies['apis'].append('Twilio (SMS)')
        if any('smtp' in comp.lower() for comp in self.components):
            dependencies['apis'].append('SMTP (email)')
        
        # Database dependencies
        if any('postgres' in file.lower() for file in self.files):
            dependencies['databases'].append('PostgreSQL (user data)')
        if any('redis' in file.lower() for file in self.files):
            dependencies['databases'].append('Redis (caching)')
        
        # Infrastructure
        if 'docker-compose.yml' in self.files:
            dependencies['infrastructure'].append('Docker')
        if 'nginx.conf' in self.files:
            dependencies['infrastructure'].append('Nginx')
        if 'prometheus.yml' in self.files:
            dependencies['infrastructure'].append('Prometheus')
        
        return dependencies

    def _identify_configuration(self) -> Dict:
        """Identify configuration files and patterns."""
        config_files = {file for file in self.files if self.files[file]['domain'] == 'configuration'}
        
        return {
            'environment_files': [f for f in config_files if '.env' in f or 'config' in f],
            'deployment': [f for f in config_files if any(x in f for x in ['docker', 'nginx', 'compose'])],
            'monitoring': [f for f in config_files if any(x in f for x in ['prometheus', 'logging'])],
            'package_management': [f for f in config_files if any(x in f for x in ['requirements', 'package'])]
        }

    def _analyze_testing_strategy(self) -> Dict:
        """Analyze testing approach and coverage."""
        test_files = {file for file in self.files if self.files[file]['domain'] == 'testing'}
        
        strategy = {
            'unit_tests': [f for f in test_files if f.startswith('tests/test_')],
            'integration_tests': [f for f in test_files if 'integration' in f or 'end_to_end' in f],
            'load_tests': [f for f in test_files if 'load' in f or 'performance' in f],
            'data_quality': [f for f in test_files if 'quality' in f or 'csv' in f]
        }
        
        return {k: v for k, v in strategy.items() if v}  # Only include non-empty categories

    def _analyze_css_architecture(self) -> Dict:
        """Analyze CSS architecture and modular structure."""
        css_files = {f: info for f, info in self.files.items() if f.endswith('.css')}
        
        # Detect architecture type
        has_main_css = any('main.css' in f for f in css_files)
        has_modular_structure = any('css/base/' in f or 'css/components/' in f for f in css_files)
        has_variables = any('variables.css' in f for f in css_files)
        
        # Count modular components
        modular_components = [f for f in css_files if 'components/' in f]
        base_system = [f for f in css_files if 'base/' in f]
        utilities = [f for f in css_files if 'utilities/' in f]
        
        # Calculate total CSS custom properties across all files
        total_custom_properties = 0
        total_responsive_breakpoints = 0
        documented_files = 0
        
        for file_path, file_info in css_files.items():
            if isinstance(file_info, dict) and 'css_analysis' in file_info:
                analysis = file_info['css_analysis']
                total_custom_properties += analysis.get('custom_properties', 0)
                total_responsive_breakpoints += analysis.get('responsive_breakpoints', 0)
                if analysis.get('components_documented', False):
                    documented_files += 1
        
        # Determine architecture maturity
        if has_main_css and has_modular_structure and has_variables and documented_files > 3:
            architecture_maturity = "Enterprise-grade"
        elif has_modular_structure and has_variables:
            architecture_maturity = "Modular"
        elif len(css_files) > 1:
            architecture_maturity = "Multi-file"
        else:
            architecture_maturity = "Monolithic"
        
        return {
            "architecture_type": architecture_maturity,
            "total_css_files": len(css_files),
            "modular_components": modular_components,
            "base_system": base_system,
            "utilities": utilities,
            "design_tokens": has_variables,
            "enterprise_standards": {
                "has_main_entry": has_main_css,
                "modular_structure": has_modular_structure,
                "design_system": has_variables,
                "documented_components": documented_files,
                "total_custom_properties": total_custom_properties,
                "responsive_breakpoints": total_responsive_breakpoints
            },
            "css_import_strategy": "Modular imports" if has_main_css else "Individual files",
            "maintainability_score": self._calculate_css_maintainability(css_files)
        }

    def _calculate_css_maintainability(self, css_files: Dict) -> str:
        """Calculate CSS maintainability score based on architecture."""
        score = 0
        
        # Points for good architecture
        if any('main.css' in f for f in css_files): score += 2
        if any('variables.css' in f for f in css_files): score += 2
        if any('components/' in f for f in css_files): score += 2
        if len([f for f in css_files if 'components/' in f]) >= 3: score += 1
        
        # Documentation points
        documented = sum(1 for f, info in css_files.items() 
                        if info.get('css_analysis', {}).get('components_documented', False))
        if documented >= len(css_files) * 0.8: score += 2
        elif documented >= len(css_files) * 0.5: score += 1
        
        # Return score interpretation
        if score >= 8: return "Excellent"
        elif score >= 6: return "Good"
        elif score >= 4: return "Fair"
        else: return "Needs improvement"

    def _extract_requirements(self) -> Dict:
        """Extract and categorize Python package requirements."""
        requirements_data = {
            "files_found": [],
            "dependencies": {
                "web_framework": [],
                "real_time": [],
                "data_processing": [],
                "authentication": [],
                "database": [],
                "testing": [],
                "development": [],
                "other": []
            },
            "total_packages": 0,
            "raw_contents": {}
        }
        
        # Look for requirements files
        req_files = [
            'requirements.txt', 
            'requirements-dev.txt', 
            'requirements-prod.txt',
            'dev-requirements.txt',
            'prod-requirements.txt'
        ]
        
        # Categorization patterns
        categories = {
            "web_framework": [
                r'^flask', r'^django', r'^fastapi', r'^pyramid', r'^tornado',
                r'^werkzeug', r'^jinja2', r'^markupsafe'
            ],
            "real_time": [
                r'^flask-socketio', r'^python-socketio', r'^eventlet', r'^gevent',
                r'^websocket', r'^ws4py'
            ],
            "data_processing": [
                r'^pandas', r'^numpy', r'^scipy', r'^requests', r'^httpx',
                r'^aiohttp', r'^urllib3', r'^polygon'
            ],
            "authentication": [
                r'^flask-login', r'^authlib', r'^pyjwt', r'^passlib',
                r'^bcrypt', r'^cryptography', r'^twilio'
            ],
            "database": [
                r'^sqlalchemy', r'^psycopg2', r'^pymongo', r'^redis',
                r'^flask-sqlalchemy', r'^alembic'
            ],
            "testing": [
                r'^pytest', r'^unittest', r'^mock', r'^coverage',
                r'^factory-boy', r'^faker'
            ],
            "development": [
                r'^black', r'^flake8', r'^mypy', r'^pre-commit',
                r'^python-dotenv', r'^watchdog'
            ]
        }
        
        for req_file in req_files:
            req_path = os.path.join(self.root_dir, req_file)
            if os.path.exists(req_path):
                try:
                    with open(req_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    if content:
                        requirements_data["files_found"].append(req_file)
                        requirements_data["raw_contents"][req_file] = content
                        
                        # Parse requirements
                        lines = [line.strip() for line in content.split('\n') 
                                if line.strip() and not line.strip().startswith('#')]
                        
                        for line in lines:
                            # Clean up the package name (remove version specifiers)
                            package_name = re.split(r'[>=<!=]', line)[0].strip()
                            
                            if package_name:
                                requirements_data["total_packages"] += 1
                                
                                # Categorize the package
                                categorized = False
                                for category, patterns in categories.items():
                                    if any(re.search(pattern, package_name, re.IGNORECASE) 
                                          for pattern in patterns):
                                        requirements_data["dependencies"][category].append({
                                            "package": package_name,
                                            "specification": line,
                                            "file": req_file
                                        })
                                        categorized = True
                                        break
                                
                                if not categorized:
                                    requirements_data["dependencies"]["other"].append({
                                        "package": package_name,
                                        "specification": line,
                                        "file": req_file
                                    })
                                    
                except Exception as e:
                    logger.warning(f"Failed to read requirements file {req_file}: {e}")
        
        # Remove empty categories
        requirements_data["dependencies"] = {
            k: v for k, v in requirements_data["dependencies"].items() if v
        }
        
        return requirements_data

    def _generate_file_inventory(self) -> Dict:
        """Generate categorized file inventory with descriptions."""
        inventory = {}
        
        # Group files by architectural role
        for file_path, file_info in self.files.items():
            role = file_info['architectural_role']
            if role not in inventory:
                inventory[role] = {}
            
            # Generate description based on file analysis
            description = self._generate_file_description(file_path, file_info)
            inventory[role][file_path] = description
        
        return inventory

    def _generate_file_description(self, file_path: str, file_info: Dict) -> str:
        """Generate a meaningful description for a file."""
        filename = os.path.basename(file_path)
        
        # Special cases for well-known files
        descriptions = {
            'app.py': 'Main Flask application with routes and WebSocket handlers',
            'model.py': 'Database models and data structures',
            'requirements.txt': 'Python package dependencies',
            'docker-compose.yml': 'Multi-container deployment configuration',
            'nginx.conf': 'Reverse proxy and load balancer configuration',
            'main.css': 'CSS entry point importing modular architecture components',
            'variables.css': 'Design system foundation with CSS custom properties',
            'reset.css': 'Modern CSS reset and base element normalization',
            'grid.css': 'Layout system and responsive grid components',
            'navbar.css': 'Navigation bar and status indicator components',
            'events.css': 'Market events system styling (highs, lows, trends, surges)',
            'modals.css': 'Modal dialogs and overlay components',
            'dashboard.css': 'Dashboard panels and metrics display components',
            'status-bar.css': 'Footer status bar and data source indicators',
            'user-menu.css': 'User dropdown menu and authentication interface',
            'gauges.css': 'Chart.js gauge components and visualizations',
            'animations.css': 'Utility classes, animations, and helper functions',
            'auth.css': 'Authentication page styling (legacy monolithic)'
        }
        
        if filename in descriptions:
            return descriptions[filename]
        
        # Enhanced pattern-based descriptions
        if file_path.endswith('.css'):
            if 'components/' in file_path:
                component_name = filename.replace('.css', '').replace('-', ' ').title()
                return f"CSS component for {component_name} styling and behavior"
            elif 'base/' in file_path:
                return f"CSS base layer - {filename.replace('.css', '').replace('-', ' ')}"
            elif 'utilities/' in file_path:
                return f"CSS utility classes - {filename.replace('.css', '').replace('-', ' ')}"
            elif 'layout/' in file_path:
                return f"CSS layout system - {filename.replace('.css', '').replace('-', ' ')}"
            else:
                return "CSS styling component"
        
        # Existing patterns
        if 'service' in filename:
            return f"Service orchestrator for {file_info['domain']} operations"
        elif 'manager' in filename:
            return f"Management layer for {file_info['domain']} functionality"
        elif 'provider' in filename:
            return f"Data provider for {file_info['domain']}"
        elif 'detector' in filename:
            return f"Event detection for {file_info['domain']}"
        elif 'test_' in filename:
            return f"Test suite for {filename.replace('test_', '').replace('.py', '')}"
        elif file_path.startswith('templates/'):
            return f"HTML template for {filename.replace('.html', '')} page"
        elif file_path.startswith('static/'):
            return f"Static asset for frontend"
        else:
            return f"{file_info['domain']} component"

    def _identify_critical_relationships(self) -> List[str]:
        """Identify the most important architectural relationships."""
        relationships = []
        
        # Service orchestration relationships
        if 'MarketDataService' in str(self.components):
            relationships.append("MarketDataService orchestrates all event detection components")
        
        if 'WebSocketManager' in str(self.components):
            relationships.append("WebSocketManager broadcasts events from MarketDataService to frontend")
        
        if 'AuthenticationManager' in str(self.components):
            relationships.append("AuthenticationManager integrates with SessionManager for security")
        
        # Interface relationships
        if 'DataProvider' in str(self.components):
            relationships.append("All data providers implement the DataProvider interface")
        
        # Data structure relationships
        if 'MarketEvent' in str(self.components):
            relationships.append("Event detectors communicate through MarketEvent data structure")
        
        # Configuration relationships
        if 'ConfigManager' in str(self.components):
            relationships.append("ConfigManager centralizes all application configuration")
        
        return relationships

def save_structure(structure: Dict, output_file: str):
    """Save the architectural structure to Markdown file in docs folder."""
    try:
        # Create full output path (ensure parent directories exist)
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert structure to Markdown
        markdown_content = "# Project Structure Documentation\n\n"
        
        # Application Overview
        markdown_content += "## Application Overview\n"
        app = structure.get('application', {})
        markdown_content += f"- **Type**: {app.get('type', 'N/A')}\n"
        markdown_content += f"- **Backend**: {app.get('backend', 'N/A')}\n"
        markdown_content += f"- **Frontend**: {app.get('frontend', 'N/A')}\n"
        markdown_content += f"- **Description**: {app.get('description', 'N/A')}\n"
        markdown_content += f"- **Architecture Pattern**: {app.get('architecture_pattern', 'N/A')}\n"
        markdown_content += f"- **Primary Data Flow**: {app.get('data_flow', 'N/A')}\n"
        
        # Core Domains
        markdown_content += "\n## Core Domains\n"
        for domain, details in structure.get('core_domains', {}).items():
            markdown_content += f"### {domain.title().replace('_', ' ')}\n"
            markdown_content += f"- **Purpose**: {details.get('purpose', 'N/A')}\n"
            if 'features' in details:
                markdown_content += "- **Features**:\n"
                for feature in details.get('features', []):
                    markdown_content += f"  - {feature}\n"
            if 'key_components' in details:
                markdown_content += "- **Key Components**:\n"
                for comp in details.get('key_components', []):
                    markdown_content += f"  - {comp}\n"
        
        # Data Flows
        markdown_content += "\n## Key Data Flows\n"
        for flow in structure.get('key_data_flows', []):
            markdown_content += f"### {flow.get('name', 'Unnamed Flow')}\n"
            markdown_content += f"- **Flow**: {flow.get('flow', 'N/A')}\n"
            markdown_content += f"- **Trigger**: {flow.get('trigger', 'N/A')}\n"
            markdown_content += "- **Components**:\n"
            for comp in flow.get('components', []):
                markdown_content += f"  - {comp}\n"
        
        # External Dependencies
        markdown_content += "\n## External Dependencies\n"
        deps = structure.get('external_dependencies', {})
        if deps.get('apis'):
            markdown_content += "- **APIs**:\n"
            for api in deps.get('apis', []):
                markdown_content += f"  - {api}\n"
        if deps.get('databases'):
            markdown_content += "- **Databases**:\n"
            for db in deps.get('databases', []):
                markdown_content += f"  - {db}\n"
        if deps.get('infrastructure'):
            markdown_content += "- **Infrastructure**:\n"
            for infra in deps.get('infrastructure', []):
                markdown_content += f"  - {infra}\n"
        
        # Configuration
        markdown_content += "\n## Configuration\n"
        config = structure.get('configuration', {})
        for category, files in config.items():
            if files:
                markdown_content += f"- **{category.title().replace('_', ' ')}**:\n"
                for file in files:
                    markdown_content += f"  - {file}\n"
        
        # Testing Strategy
        markdown_content += "\n## Testing Strategy\n"
        for category, tests in structure.get('testing_strategy', {}).items():
            if tests:
                markdown_content += f"- **{category.title().replace('_', ' ')}**:\n"
                for test in tests:
                    markdown_content += f"  - {test}\n"
        
        # CSS Architecture
        markdown_content += "\n## CSS Architecture\n"
        css = structure.get('css_architecture', {})
        markdown_content += f"- **Architecture Type**: {css.get('architecture_type', 'N/A')}\n"
        markdown_content += f"- **Total CSS Files**: {css.get('total_css_files', 0)}\n"
        markdown_content += f"- **Design Tokens**: {'Yes' if css.get('design_tokens') else 'No'}\n"
        markdown_content += f"- **Maintainability Score**: {css.get('maintainability_score', 'N/A')}\n"
        
        # JavaScript Architecture
        markdown_content += "\n## JavaScript Architecture\n"
        js = structure.get('js_architecture', {})
        markdown_content += f"- **Architecture Type**: {js.get('architecture_type', 'N/A')}\n"
        markdown_content += f"- **Total JS Files**: {js.get('total_js_files', 0)}\n"
        markdown_content += f"- **Total Classes**: {js.get('total_classes', 0)}\n"
        markdown_content += f"- **Total Functions**: {js.get('total_functions', 0)}\n"
        
        # Requirements
        markdown_content += "\n## Requirements\n"
        reqs = structure.get('requirements', {})
        markdown_content += f"- **Total Packages**: {reqs.get('total_packages', 0)}\n"
        for category, deps in reqs.get('dependencies', {}).items():
            markdown_content += f"- **{category.title().replace('_', ' ')}**:\n"
            for dep in deps:
                markdown_content += f"  - {dep.get('package')} ({dep.get('file')})\n"
        
        # File Inventory
        markdown_content += "\n## File Inventory\n"
        for role, files in structure.get('file_inventory', {}).items():
            markdown_content += f"### {role.title().replace('_', ' ')}\n"
            for file, desc in files.items():
                markdown_content += f"- **{file}**: {desc}\n"
        
        # Critical Relationships
        markdown_content += "\n## Critical Relationships\n"
        for rel in structure.get('critical_relationships', []):
            markdown_content += f"- {rel}\n"
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        logger.info(f"Architectural documentation saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to save documentation to {output_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate architectural project documentation")
    
    # Update default paths to work from dev_tools folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_root_dir = os.path.dirname(script_dir)  # Go up one level from dev_tools
    
    parser.add_argument(
        "--root-dir",
        default=default_root_dir,
        help="Root directory of the project (default: parent of dev_tools directory)"
    )
    parser.add_argument(
        "--output-file",
        default=os.path.join(default_root_dir, "docs/architecture/project_structure.md"),
        help="Output Markdown file path (default: project_root/docs/architecture/project_structure.md)"
    )
    args = parser.parse_args()

    analyzer = CreateProjectStructureDocumentation(args.root_dir)
    structure = analyzer.analyze_project()
    save_structure(structure, args.output_file)
    
    # Print summary
    print(f"\n🏗️  Architectural Documentation Complete")
    print(f"📁 Files analyzed: {len(analyzer.files)}")
    print(f"🔧 Components found: {len(analyzer.components)}")
    print(f"🌐 Routes discovered: {len(analyzer.routes)}")
    print(f"⚡ WebSocket events: {len(analyzer.websocket_events)}")
    print(f"📊 Output saved to: {args.output_file}")

if __name__ == "__main__":
    main()