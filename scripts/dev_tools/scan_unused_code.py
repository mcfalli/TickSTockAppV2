#!/usr/bin/env python3
"""
Unused Method Detector for TickStock
Analyzes Python codebase to find methods that are never called internally or externally.
Place this file in dev_tools/ folder and run from project root.
"""

import argparse
import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MethodInfo:
    """Information about a method in the codebase."""
    file_path: str
    class_name: str
    method_name: str
    line_number: int
    is_property: bool = False
    is_static: bool = False
    is_class_method: bool = False
    decorators: list[str] = field(default_factory=list)


@dataclass
class MethodUsage:
    """Track where a method is called from."""
    caller_file: str
    caller_class: str | None
    caller_method: str | None
    line_number: int
    usage_type: str  # 'internal', 'external', 'import'


class MethodAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze method definitions and calls."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.current_class = None
        self.current_method = None
        self.methods: dict[str, MethodInfo] = {}
        self.method_calls: list[tuple[str, str, int]] = []
        self.imports: dict[str, str] = {}
        self.from_imports: dict[str, list[str]] = defaultdict(list)

    def visit_Import(self, node):
        """Track regular imports."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from imports."""
        if node.module:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                self.from_imports[node.module].append(name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Process class definitions."""
        old_class = self.current_class
        self.current_class = node.name

        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                self._process_method(item)

        self.generic_visit(node)
        self.current_class = old_class

    def _process_method(self, node):
        """Process method definitions."""
        if self.current_class:
            method_key = f"{self.current_class}.{node.name}"

            # Extract decorator information
            decorators = []
            is_property = False
            is_static = False
            is_class_method = False

            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    decorators.append(decorator.id)
                    if decorator.id == 'property':
                        is_property = True
                    elif decorator.id == 'staticmethod':
                        is_static = True
                    elif decorator.id == 'classmethod':
                        is_class_method = True
                elif isinstance(decorator, ast.Attribute):
                    decorators.append(f"{decorator.attr}")

            self.methods[method_key] = MethodInfo(
                file_path=self.file_path,
                class_name=self.current_class,
                method_name=node.name,
                line_number=node.lineno,
                is_property=is_property,
                is_static=is_static,
                is_class_method=is_class_method,
                decorators=decorators
            )

    def visit_FunctionDef(self, node):
        """Process function definitions."""
        old_method = self.current_method

        if not self.current_class:
            # Module-level function
            self.current_method = node.name
        else:
            # Class method
            self.current_method = node.name
            self._process_method(node)

        self.generic_visit(node)
        self.current_method = old_method

    def visit_AsyncFunctionDef(self, node):
        """Process async function definitions."""
        self.visit_FunctionDef(node)

    def visit_Call(self, node):
        """Track method calls."""
        method_name = None
        class_ref = None

        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr

            # Check if it's a self/cls call
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id in ('self', 'cls'):
                    class_ref = self.current_class
                else:
                    class_ref = node.func.value.id
            elif isinstance(node.func.value, ast.Call):
                # Handle chained calls
                if hasattr(node.func.value.func, 'id'):
                    class_ref = node.func.value.func.id

        elif isinstance(node.func, ast.Name):
            method_name = node.func.id

        if method_name:
            self.method_calls.append((
                class_ref or '',
                method_name,
                node.lineno
            ))

        self.generic_visit(node)


class TickStockUnusedMethodDetector:
    """Unused method detector specifically configured for TickStock project."""

    def __init__(self, root_path: str | None = None):
        # If no root path provided, assume we're running from project root
        self.root_path = Path(root_path) if root_path else Path.cwd()

        # TickStock specific directories to analyze
        self.directories_to_analyze = [
            "auth",
            "classes",
            "classes/analytics",
            "classes/events",
            "classes/market",
            "classes/processing",
            "classes/transport",
            "config",
            "database",
            "data_flow",
            "data_providers",
            "data_providers/base",
            "data_providers/polygon",
            "data_providers/simulated",
            "event_detection",
            "event_detection/engines",
            "market_analytics",
            "market_data_service",
            "processing",
            "services",
            "session_accumulation",
            "universe",
            "utils",
            "ws_handlers"
        ]

        # Specific files in root directory
        self.specific_files = [
            "app.py",
            "app_forms.py",
            "app_routes_api.py",
            "app_routes_auth.py",
            "app_routes_main.py",
            "app_startup.py",
            "app_utils.py",
        ]

        self.all_methods: dict[str, MethodInfo] = {}
        self.method_usages: dict[str, list[MethodUsage]] = defaultdict(list)

        # Common method names to exclude from analysis
        self.excluded_methods = {
            '__init__', '__str__', '__repr__', '__eq__', '__hash__',
            '__enter__', '__exit__', '__getattr__', '__setattr__',
            '__delattr__', '__getitem__', '__setitem__', '__delitem__',
            '__len__', '__bool__', '__call__', '__iter__', '__next__',
            '__contains__', '__add__', '__sub__', '__mul__', '__div__',
            '__mod__', '__pow__', '__and__', '__or__', '__xor__',
            '__lt__', '__le__', '__gt__', '__ge__', '__ne__',
            'setUp', 'tearDown', 'setUpClass', 'tearDownClass',  # Test methods
        }

        # Flask/SocketIO/TickStock specific methods to exclude
        self.framework_methods = {
            # HTTP methods
            'get', 'post', 'put', 'delete', 'patch', 'head', 'options',
            # Flask hooks
            'before_request', 'after_request', 'teardown_request',
            'before_first_request', 'errorhandler',
            # SocketIO handlers
            'on_connect', 'on_disconnect', 'on_message', 'on_error',
            'on_join', 'on_leave', 'emit', 'send',
            # Common handlers
            'handle', 'dispatch', 'run', 'start', 'stop', 'initialize',
            'shutdown', 'cleanup', 'reset', 'clear',
            # TickStock specific
            'process', 'update', 'calculate', 'validate', 'execute',
            'on_market_data', 'on_tick', 'on_bar', 'on_event',
        }

        # Files to always skip
        self.skip_files = {
            '__init__.py',
            'setup.py',
            'conftest.py',
        }

    def get_files_to_analyze(self) -> list[Path]:
        """Get list of Python files to analyze based on TickStock structure."""
        files_to_analyze = []

        # Add specific root files
        for file_name in self.specific_files:
            file_path = self.root_path / file_name
            if file_path.exists() and file_path.is_file():
                files_to_analyze.append(file_path)
            else:
                print(f"Warning: Specified file not found: {file_name}", file=sys.stderr)

        # Add files from specified directories
        for dir_path in self.directories_to_analyze:
            full_dir_path = self.root_path / dir_path
            if full_dir_path.exists() and full_dir_path.is_dir():
                # Get all .py files in this specific directory (not recursive for each)
                for file_path in full_dir_path.glob("*.py"):
                    if file_path.name not in self.skip_files:
                        files_to_analyze.append(file_path)
            else:
                print(f"Warning: Directory not found: {dir_path}", file=sys.stderr)

        return files_to_analyze

    def analyze_file(self, file_path: Path) -> tuple[dict[str, MethodInfo], list[tuple[str, str, int]]]:
        """Analyze a single Python file."""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            analyzer = MethodAnalyzer(str(file_path.relative_to(self.root_path)))
            analyzer.visit(tree)

            return analyzer.methods, analyzer.method_calls

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
            return {}, []

    def scan_codebase(self):
        """Scan TickStock codebase for methods and their usages."""
        python_files = self.get_files_to_analyze()

        print(f"Analyzing {len(python_files)} Python files in TickStock project...")
        print(f"Root path: {self.root_path}")
        print("")

        # First pass: collect all method definitions
        for file_path in python_files:
            methods, _ = self.analyze_file(file_path)
            self.all_methods.update(methods)

        print(f"Found {len(self.all_methods)} total methods")

        # Second pass: collect all method calls
        for file_path in python_files:
            _, method_calls = self.analyze_file(file_path)
            relative_path = str(file_path.relative_to(self.root_path))

            for class_ref, method_name, line_no in method_calls:
                # Try to match with defined methods
                if class_ref:
                    method_key = f"{class_ref}.{method_name}"
                    if method_key in self.all_methods:
                        usage_type = 'internal' if self.all_methods[method_key].file_path == relative_path else 'external'
                        self.method_usages[method_key].append(
                            MethodUsage(
                                caller_file=relative_path,
                                caller_class=None,
                                caller_method=None,
                                line_number=line_no,
                                usage_type=usage_type
                            )
                        )

                # Also check for any method with this name (partial matching)
                for key in self.all_methods:
                    if key.endswith(f".{method_name}"):
                        # Don't double-count if we already matched above
                        if class_ref and key == f"{class_ref}.{method_name}":
                            continue
                        self.method_usages[key].append(
                            MethodUsage(
                                caller_file=relative_path,
                                caller_class=None,
                                caller_method=None,
                                line_number=line_no,
                                usage_type='external'
                            )
                        )

    def find_unused_methods(self) -> dict[str, list[MethodInfo]]:
        """Find all methods that are never called."""
        unused = defaultdict(list)

        for method_key, method_info in self.all_methods.items():
            # Skip special methods and framework methods
            if (method_info.method_name in self.excluded_methods or
                method_info.method_name in self.framework_methods):
                continue

            # Skip private methods starting with _ (but not __)
            if (method_info.method_name.startswith('_') and
                not method_info.method_name.startswith('__')):
                # These are often internal and may be called dynamically
                continue

            # Skip decorated methods (likely routes, handlers, etc.)
            if method_info.decorators:
                route_decorators = {'route', 'get', 'post', 'put', 'delete', 'patch',
                                  'socketio', 'on', 'emit', 'task', 'cached_property'}
                if any(dec in route_decorators for dec in method_info.decorators):
                    continue

            # Check if method is ever called
            if method_key not in self.method_usages:
                unused[method_info.file_path].append(method_info)

        return unused

    def generate_report(self, output_format: str = 'text') -> str:
        """Generate report of unused methods."""
        self.scan_codebase()
        unused_methods = self.find_unused_methods()

        if output_format == 'json':
            return self._generate_json_report(unused_methods)
        return self._generate_text_report(unused_methods)

    def _generate_text_report(self, unused_methods: dict[str, list[MethodInfo]]) -> str:
        """Generate human-readable text report."""
        report = []
        report.append("=" * 80)
        report.append("TICKSTOCK UNUSED METHOD DETECTION REPORT")
        report.append("=" * 80)
        report.append(f"Root Path: {self.root_path}")
        report.append(f"Total Methods Analyzed: {len(self.all_methods)}")

        total_unused = sum(len(methods) for methods in unused_methods.values())
        report.append(f"Total Unused Methods Found: {total_unused}")
        report.append("")

        if not unused_methods:
            report.append("✓ No unused methods found! Code is well utilized.")
        else:
            # Group by directory for better organization
            by_directory = defaultdict(list)
            for file_path, methods in unused_methods.items():
                dir_name = str(Path(file_path).parent) if '/' in file_path else 'root'
                by_directory[dir_name].extend([(file_path, m) for m in methods])

            for directory in sorted(by_directory.keys()):
                report.append("-" * 80)
                report.append(f"Directory: {directory}/")

                # Group by file within directory
                files_in_dir = defaultdict(list)
                for file_path, method in by_directory[directory]:
                    files_in_dir[file_path].append(method)

                for file_path in sorted(files_in_dir.keys()):
                    report.append(f"\n  File: {file_path}")
                    report.append(f"  Unused Methods: {len(files_in_dir[file_path])}")

                    for method in sorted(files_in_dir[file_path], key=lambda m: m.line_number):
                        report.append(f"    Line {method.line_number:4d}: {method.class_name}.{method.method_name}()")
                        if method.decorators:
                            report.append(f"              Decorators: {', '.join(method.decorators)}")

                report.append("")

        report.append("=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)

        if unused_methods:
            report.append(f"Found {total_unused} potentially unused methods across {len(unused_methods)} files.")
            report.append("")
            report.append("IMPORTANT NOTES:")
            report.append("• Some methods might be called dynamically (getattr, reflection)")
            report.append("• WebSocket/Flask handlers may be registered indirectly")
            report.append("• Always verify before removing any code")
            report.append("• Consider adding @deprecated decorator before removal")
        else:
            report.append("All analyzed methods appear to be in use.")
            report.append("Your codebase is clean and well-maintained!")

        return "\n".join(report)

    def _generate_json_report(self, unused_methods: dict[str, list[MethodInfo]]) -> str:
        """Generate JSON report for programmatic processing."""
        result = {
            "project": "TickStock",
            "root_path": str(self.root_path),
            "total_methods": len(self.all_methods),
            "total_unused": sum(len(methods) for methods in unused_methods.values()),
            "analyzed_directories": self.directories_to_analyze,
            "analyzed_files": self.specific_files,
            "unused_methods": {}
        }

        for file_path, methods in unused_methods.items():
            result["unused_methods"][file_path] = [
                {
                    "class": method.class_name,
                    "method": method.method_name,
                    "line": method.line_number,
                    "decorators": method.decorators,
                    "is_property": method.is_property,
                    "is_static": method.is_static,
                    "is_class_method": method.is_class_method
                }
                for method in methods
            ]

        return json.dumps(result, indent=2)


def main():
    """Main entry point for the TickStock unused method detector."""
    parser = argparse.ArgumentParser(
        description="Detect unused methods in TickStock codebase",
        epilog="Run this script from the TickStock project root directory"
    )
    parser.add_argument(
        "--path",
        help="Root path of TickStock project (default: current directory)",
        default=None
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--output",
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed analysis progress"
    )

    args = parser.parse_args()

    # Create detector instance
    detector = TickStockUnusedMethodDetector(args.path)

    # Generate report
    report = detector.generate_report(args.format)

    # Output report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
