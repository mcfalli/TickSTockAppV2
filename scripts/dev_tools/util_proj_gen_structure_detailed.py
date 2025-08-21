import os
import ast
from pathlib import Path
import re
from typing import List, Dict, Set, Tuple, Optional

def generate_project_structure(root_dir: str, ignore_dirs: List[str], output_dir: str) -> str:
    """
    Generate a single comprehensive markdown file documenting the TickStock project structure
    with focus on technical architecture and data flow.
    """
    project_structure = {}
    class_dependencies = {}
    architectural_components = {
        'real_time_pipeline': [],
        'websocket_layer': [],
        'data_providers': [],
        'event_detectors': [],
        'universe_managers': [],
        'analytics_services': [],
        'database_models': []
    }
    
    # Updated ignore list including web
    ignore_dirs = ignore_dirs + ['web'] if 'web' not in ignore_dirs else ignore_dirs
    exclude_patterns = [r'^test_.*\.py$', r'^util_.*\.py$', r'.*/temp/.*\.py$']
    
    output_file = os.path.join(output_dir, 'project_structure_detailed.md')
    
    # First pass: collect and categorize
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith('.py') and not any(re.match(pattern, os.path.join(root, file)) for pattern in exclude_patterns):
                file_path = os.path.join(root, file)
                relative_path = str(Path(file_path).relative_to(root_dir)).replace('\\', '/')
                
                # Only process src/ and config/ files
                if not (relative_path.startswith('src/') or relative_path.startswith('config/')):
                    continue
                
                try:
                    file_data = parse_python_file_optimized(file_path, class_dependencies, file == '__init__.py')
                    project_structure[relative_path] = file_data
                    
                    # Categorize components for architectural overview
                    categorize_component(relative_path, file_data, architectural_components)
                    
                except (SyntaxError, UnicodeDecodeError) as e:
                    project_structure[relative_path] = {'error': f'Parse error: {str(e)}'}
    
    # Generate optimized markdown
    os.makedirs(output_dir, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write('# TickStock Technical Architecture\n\n')
        f.write('*Real-time market data processing system with WebSocket distribution*\n\n')
        
        # Executive Summary
        write_executive_summary(f, project_structure, architectural_components)
        
        # Data Flow Architecture
        write_data_flow_architecture(f, architectural_components)
        
        # Component Interactions
        write_component_interactions(f)
        
        # Core Components by Layer
        write_layered_architecture(f, project_structure, class_dependencies)
        
        # Critical Classes and Interfaces
        write_critical_classes(f, project_structure, architectural_components)
        
        # Configuration & Deployment
        write_configuration_notes(f)
        
        # Configuration Components
        write_config_section(f, project_structure)
        
        # Inter-Component Dependencies
        write_dependency_matrix(f, class_dependencies, project_structure)
        
        # Quick Reference Index
        write_quick_reference(f, project_structure)
    
    return output_file


def parse_python_file_optimized(file_path: str, class_dependencies: Dict, is_init: bool) -> Dict:
    """
    Parse Python file focusing on essential technical information.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {'error': 'Syntax error'}
    
    result = {
        'classes': {},
        'functions': [],
        'imports': set(),
        'constants': [],
        'decorators': set(),
        'init_content': None
    }
    
    # Handle __init__.py special content
    if is_init:
        result['init_content'] = {'all': [], 'imports': []}
    
    class OptimizedVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_class = None
            
        def visit_ClassDef(self, node):
            class_name = node.name
            self.current_class = class_name
            
            bases = []
            for base in node.bases:
                try:
                    base_str = ast.unparse(base).split('.')[-1]
                    bases.append(base_str)
                except:
                    pass
            
            # Only capture key methods (init, public API, handlers)
            key_methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if (item.name == '__init__' or 
                        not item.name.startswith('_') or 
                        'handle' in item.name or 
                        'process' in item.name or
                        'emit' in item.name):
                        # Simplified signature
                        params = [arg.arg for arg in item.args.args if arg.arg != 'self']
                        key_methods.append(f"{item.name}({', '.join(params[:3])}{'...' if len(params) > 3 else ''})")
            
            result['classes'][class_name] = {
                'extends': bases[0] if bases else None,
                'methods': key_methods[:10],  # Limit to 10 most important
                'is_abstract': any(isinstance(d, ast.Name) and d.id == 'ABC' for d in node.decorator_list)
            }
            
            self.generic_visit(node)
            self.current_class = None
        
        def visit_FunctionDef(self, node):
            # Only module-level functions (not class methods)
            if not self.current_class:
                params = [arg.arg for arg in node.args.args]
                result['functions'].append(f"{node.name}({', '.join(params[:2])}{'...' if len(params) > 2 else ''})")
            self.generic_visit(node)
        
        def visit_ImportFrom(self, node):
            if node.module:
                for name in node.names:
                    if isinstance(name.name, str) and name.name[0].isupper():
                        result['imports'].add(name.name)
                        
                # Special handling for __init__.py
                if is_init and node.module:
                    for name in node.names:
                        result['init_content']['imports'].append(f"{node.module}.{name.name}")
            self.generic_visit(node)
        
        def visit_Import(self, node):
            if is_init:
                for name in node.names:
                    result['init_content']['imports'].append(name.name)
            self.generic_visit(node)
        
        def visit_Assign(self, node):
            # Check for __all__ in __init__.py
            if is_init:
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            result['init_content']['all'] = [
                                elt.value for elt in node.value.elts 
                                if isinstance(elt, ast.Constant)
                            ]
            
            # Check for constants
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    result['constants'].append(target.id)
            
            self.generic_visit(node)
    
    visitor = OptimizedVisitor()
    visitor.visit(tree)
    
    # Track dependencies with relative path as key
    relative_path = str(Path(file_path).relative_to(ROOT_DIR)).replace('\\', '/')
    if relative_path not in class_dependencies:
        class_dependencies[relative_path] = result['imports']
    
    return result

def categorize_component(path: str, data: Dict, categories: Dict):
    """
    Categorize components by their architectural role.
    """
    if 'error' in data:
        return
    
    # Map paths to categories
    if 'websocket' in path:
        categories['websocket_layer'].append(path)
    elif 'data_sources' in path or 'provider' in path.lower():
        categories['data_providers'].append(path)
    elif 'detector' in path:
        categories['event_detectors'].append(path)
    elif 'universe' in path:
        categories['universe_managers'].append(path)
    elif 'analytics' in path or 'metrics' in path:
        categories['analytics_services'].append(path)
    elif 'models/base.py' in path or 'models/analytics.py' in path:
        categories['database_models'].append(path)
    elif any(cls in data.get('classes', {}) for cls in ['TickProcessor', 'EventProcessor', 'MarketDataService']):
        categories['real_time_pipeline'].append(path)


def write_executive_summary(f, structure: Dict, components: Dict):
    """Write a concise executive summary with key insights."""
    f.write('## Executive Summary\n\n')
    
    # Calculate statistics
    total_files = len([p for p in structure if not structure[p].get('error')])
    total_classes = sum(len(s.get('classes', {})) for s in structure.values())
    
    f.write('### System Overview\n')
    f.write('Real-time financial data processing system with:\n')
    f.write(f'- **{total_files}** Python modules across `src/` and `config/`\n')
    f.write(f'- **{total_classes}** classes implementing the architecture\n')
    f.write(f'- **{len(components["websocket_layer"])}** WebSocket components for real-time distribution\n')
    f.write(f'- **{len(components["event_detectors"])}** event detection engines\n\n')
    
    f.write('### Core Capabilities\n')
    f.write('- **Event Detection**: HighLow, Surge, and Trend detection in real-time\n')
    f.write('- **Universe Filtering**: Core universe and user-specific stock filtering\n')
    f.write('- **Session Management**: Market session state tracking (pre-market, market, after-hours)\n')
    f.write('- **Priority Processing**: Queue-based priority management for event handling\n')
    f.write('- **Analytics**: Real-time accumulation and aggregation of market metrics\n\n')
    
    f.write('### Key Technologies\n')
    f.write('- **Backend**: Python 3.x, Flask, Flask-SocketIO\n')
    f.write('- **Real-time Data**: Polygon.io WebSocket API, Socket.IO\n')
    f.write('- **Processing**: Multi-threaded event detection pipeline with priority queues\n')
    f.write('- **Database**: PostgreSQL with SQLAlchemy ORM\n')
    f.write('- **Caching**: In-memory caching with CacheControl\n\n')


def write_data_flow_architecture(f, components: Dict):
    """Write the data flow architecture section with more detail."""
    f.write('## Data Flow Architecture\n\n')
    
    f.write('### Primary Data Pipeline\n')
    f.write('```\n')
    f.write('[Polygon WebSocket API]\n')
    f.write('         ↓\n')
    f.write('  RealTimeDataAdapter\n')
    f.write('         ↓\n')
    f.write('   MarketDataService ←→ [CacheControl]\n')
    f.write('         ↓\n')
    f.write('    EventProcessor\n')
    f.write('         ↓\n')
    f.write('  ┌──────┴──────┐\n')
    f.write('  │  Detectors  │\n')
    f.write('  ├─ HighLow ───┤\n')
    f.write('  ├─ Surge ─────┤\n')
    f.write('  └─ Trend ─────┘\n')
    f.write('         ↓\n')
    f.write('   PriorityManager\n')
    f.write('         ↓\n')
    f.write('   DataPublisher\n')
    f.write('         ↓\n')
    f.write(' WebSocketPublisher\n')
    f.write('         ↓\n')
    f.write('  [User Clients]\n')
    f.write('```\n\n')
    
    f.write('### Key Processing Stages\n')
    f.write('1. **Data Ingestion**: WebSocket connection to Polygon for real-time ticks\n')
    f.write('2. **Event Detection**: Pattern recognition for market events\n')
    f.write('3. **Priority Queuing**: Event prioritization based on universe membership\n')
    f.write('4. **Accumulation**: Session-based event counting and analytics\n')
    f.write('5. **Distribution**: WebSocket emission to connected clients\n\n')


def write_component_interactions(f):
    """Add a section describing key component interactions."""
    f.write('## Component Interactions\n\n')
    
    f.write('### Session Management Flow\n')
    f.write('```\n')
    f.write('SessionManager determines market session\n')
    f.write('    ↓\n')
    f.write('MarketDataService.handle_market_session_change()\n')
    f.write('    ↓\n')
    f.write('Resets: Detectors, Accumulation, Analytics\n')
    f.write('```\n\n')
    
    f.write('### Universe Filtering Flow\n')
    f.write('```\n')
    f.write('User selects universes → UserUniverseManager\n')
    f.write('                              ↓\n')
    f.write('                    UniverseCoordinator\n')
    f.write('                              ↓\n')
    f.write('           Updates: BuySellTracker, WebSocketPublisher\n')
    f.write('```\n\n')
    
    f.write('### Event Lifecycle\n')
    f.write('```\n')
    f.write('Tick → Detection → Priority Queue → Collection → Filter → Emit\n')
    f.write('```\n\n')


def write_layered_architecture(f, structure: Dict, dependencies: Dict):
    """Write components organized by architectural layer."""
    f.write('## Component Layers\n\n')
    
    layers = {
        'API Layer': ['src/api/rest/', 'src/api/websocket/'],
        'Core Services': ['src/core/services/'],
        'Processing Pipeline': ['src/processing/'],
        'Data Infrastructure': ['src/infrastructure/data_sources/', 'src/infrastructure/database/'],
        'Presentation': ['src/presentation/websocket/'],
        'Monitoring': ['src/monitoring/']
    }
    
    for layer_name, prefixes in layers.items():
        f.write(f'### {layer_name}\n\n')
        
        layer_files = [p for p in structure.keys() if any(p.startswith(prefix) for prefix in prefixes)]
        
        if not layer_files:
            f.write('*No components*\n\n')
            continue
        
        # Group by subdirectory
        subdirs = {}
        for file_path in sorted(layer_files):
            parts = file_path.split('/')
            subdir = '/'.join(parts[:-1])
            if subdir not in subdirs:
                subdirs[subdir] = []
            
            file_info = structure[file_path]
            if file_info.get('classes'):
                for class_name, class_data in file_info['classes'].items():
                    extends = f" ← {class_data['extends']}" if class_data.get('extends') else ""
                    methods = len(class_data.get('methods', []))
                    subdirs[subdir].append(f"**{class_name}**{extends} ({methods} methods)")
            elif file_info.get('functions'):
                subdirs[subdir].append(f"*{parts[-1]}* - {len(file_info['functions'])} functions")
        
        # Track already written classes to avoid duplicates
        written_classes = set()
        
        for subdir in sorted(subdirs.keys()):
            if subdirs[subdir]:
                f.write(f'**{subdir}/**\n')
                for item in subdirs[subdir]:
                    # Extract class name from item string
                    class_name = item.split('**')[1] if '**' in item else None
                    if class_name and class_name not in written_classes:
                        f.write(f'- {item}\n')
                        written_classes.add(class_name)
                    elif not class_name:  # It's a function file
                        f.write(f'- {item}\n')
                f.write('\n')


def write_critical_classes(f, structure: Dict, components: Dict):
    """Write the most important classes with context."""
    f.write('## Critical Components\n\n')
    
    critical_components = {
        'Core Processing': {
            'MarketDataService': 'Central orchestrator for market data flow',
            'EventProcessor': 'Processes ticks and triggers event detection',
            'PriorityManager': 'Manages event queue with priority logic'
        },
        'Event Detection': {
            'HighLowDetector': 'Detects session highs/lows with configurable thresholds',
            'SurgeDetector': 'Identifies volume/price surges with adaptive thresholds',
            'TrendDetector': 'Multi-window trend analysis with retracement detection'
        },
        'Data Distribution': {
            'DataPublisher': 'Collects and buffers events for emission',
            'WebSocketPublisher': 'Manages WebSocket emissions to users',
            'WebSocketManager': 'Handles client connections and rooms'
        },
        'Universe Management': {
            'UniverseCoordinator': 'Coordinates universe filtering across components',
            'CoreUniverseManager': 'Manages core stock universe',
            'UserUniverseManager': 'Handles user-specific universe selections'
        }
    }
    
    for category, classes in critical_components.items():
        f.write(f'### {category}\n\n')
        
        for class_name, description in classes.items():
            # Find the class in structure
            for file_path, file_data in structure.items():
                if 'classes' in file_data and class_name in file_data['classes']:
                    f.write(f'#### {class_name}\n')
                    f.write(f'*{description}*\n\n')
                    f.write(f'Location: `{file_path}`\n\n')
                    
                    class_info = file_data['classes'][class_name]
                    if class_info.get('extends'):
                        f.write(f'Extends: `{class_info["extends"]}`\n\n')
                    
                    # Only show the most important methods
                    important_methods = [m for m in class_info.get('methods', []) 
                                       if not m.startswith('_') or m == '__init__'][:5]
                    if important_methods:
                        f.write('Key Methods:\n')
                        for method in important_methods:
                            f.write(f'- `{method}`\n')
                    f.write('\n')
                    break


def write_configuration_notes(f):
    """Add configuration and deployment notes."""
    f.write('## Configuration & Deployment\n\n')
    
    f.write('### Environment Variables\n')
    f.write('- `POLYGON_API_KEY`: Required for real-time data\n')
    f.write('- `USE_REAL_DATA`: Toggle between real/simulated data\n')
    f.write('- `DATABASE_URL`: PostgreSQL connection string\n')
    f.write('- `REDIS_URL`: Optional Redis cache\n\n')
    
    f.write('### Key Configuration Files\n')
    f.write('- `config/app_config.py`: Main configuration loader\n')
    f.write('- `config/environments/`: Environment-specific settings\n')
    f.write('- `config/logging_config.py`: Logging configuration\n\n')
    
    f.write('### Performance Tuning\n')
    f.write('- Worker pool size: Configurable based on load\n')
    f.write('- Queue sizes: Adjustable for memory/latency tradeoff\n')
    f.write('- Emission intervals: Balance between latency and efficiency\n')
    f.write('- Cache TTLs: Optimize for data freshness vs API calls\n\n')


def write_config_section(f, structure: Dict):
    """Write configuration components section."""
    f.write('## Configuration Components\n\n')
    
    config_files = [p for p in structure.keys() if p.startswith('config/')]
    
    if not config_files:
        f.write('*No configuration files found*\n\n')
        return
    
    for file_path in sorted(config_files):
        file_data = structure[file_path]
        f.write(f'**{file_path}**\n')
        
        if file_data.get('classes'):
            f.write(f"- Classes: {', '.join(file_data['classes'].keys())}\n")
        if file_data.get('functions'):
            f.write(f"- Functions: {len(file_data['functions'])}\n")
        if file_data.get('constants'):
            f.write(f"- Constants: {', '.join(file_data['constants'][:5])}\n")
        f.write('\n')


def write_dependency_matrix(f, dependencies: Dict, structure: Dict):
    """Write a simplified dependency matrix focusing on cross-module dependencies."""
    f.write('## Key Dependencies\n\n')
    
    # Focus on service-to-service dependencies
    key_services = ['MarketDataService', 'EventProcessor', 'UniverseCoordinator', 
                    'WebSocketPublisher', 'DataPublisher', 'PriorityManager']
    
    has_dependencies = False
    dependency_rows = []
    
    for file_path, deps in dependencies.items():
        file_classes = structure.get(file_path, {}).get('classes', {})
        for class_name in file_classes:
            if class_name in key_services:
                key_deps = [d for d in deps if d in key_services or 'Manager' in d or 'Service' in d]
                if key_deps:
                    dependency_rows.append(f'| {class_name} | {", ".join(key_deps[:5])} |')
                    has_dependencies = True
    
    if has_dependencies:
        f.write('| Service | Dependencies |\n')
        f.write('|---------|-------------|\n')
        for row in dependency_rows:
            f.write(row + '\n')
    else:
        f.write('*No cross-service dependencies detected*\n')
    
    f.write('\n')


def write_quick_reference(f, structure: Dict):
    """Write a quick reference index."""
    f.write('## Quick Reference Index\n\n')
    
    # Group by component type
    groups = {
        'Services': [],
        'Detectors': [],
        'Managers': [],
        'Models': [],
        'Utils': []
    }
    
    for path, data in structure.items():
        if 'classes' in data:
            for class_name in data['classes']:
                if 'Service' in class_name:
                    groups['Services'].append((class_name, path))
                elif 'Detector' in class_name:
                    groups['Detectors'].append((class_name, path))
                elif 'Manager' in class_name:
                    groups['Managers'].append((class_name, path))
                elif '/models/' in path:
                    groups['Models'].append((class_name, path))
                elif '/utils/' in path:
                    groups['Utils'].append((class_name, path))
    
    for group_name, items in groups.items():
        if items:
            f.write(f'### {group_name}\n')
            for class_name, path in sorted(items)[:15]:  # Limit each group
                f.write(f'- `{class_name}` → {path}\n')
            f.write('\n')


if __name__ == '__main__':
    # Configuration
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    IGNORE_DIRS = ['venv', '__pycache__', 'tests', '.git', 'migrations', 'scripts', 
                   'requirements', 'logs', 'docs', 'build', 'dist', 'static', 
                   'templates', 'web']  # Added 'web' to ignore list
    OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../docs'))

    output_file = generate_project_structure(ROOT_DIR, IGNORE_DIRS, OUTPUT_DIR)
    print('Complete!')
    print(f'Generated: {output_file}')