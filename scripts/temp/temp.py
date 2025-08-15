#!/usr/bin/env python3
"""
Unused Method Detector
Analyzes Python codebase to find methods that are never called internally or externally.
Useful for identifying dead code in enterprise applications.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import argparse
import json


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
    decorators: List[str] = field(default_factory=list)


@dataclass
class MethodUsage:
    """Track where a method is called from."""
    caller_file: str
    caller_class: Optional[str]
    caller_method: Optional[str]
    line_number: int
    usage_type: str  # 'internal', 'external', 'import'


class MethodAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze method definitions and calls."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.current_class = None
        self.current_method = None
        self.methods: Dict[str, MethodInfo] = {}
        self.method_calls: List[Tuple[str, str, int]] = []
        self.imports: Dict[str, str] = {}
        self.from_imports: Dict[str, List[str]] = defaultdict(list)
        
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


class UnusedMethodDetector:
    """Main class for detecting unused methods in a Python codebase."""
    
    def __init__(self, root_path: str, exclude_patterns: Optional[List[str]] = None):
        self.root_path = Path(root_path)
        self.exclude_patterns = exclude_patterns or []
        self.all_methods: Dict[str, MethodInfo] = {}
        self.method_usages: Dict[str, List[MethodUsage]] = defaultdict(list)
        
        # Common method names to exclude from analysis
        self.excluded_methods = {
            '__init__', '__str__', '__repr__', '__eq__', '__hash__',
            '__enter__', '__exit__', '__getattr__', '__setattr__',
            '__delattr__', '__getitem__', '__setitem__', '__delitem__',
            '__len__', '__bool__', '__call__', '__iter__', '__next__',
            'setUp', 'tearDown', 'setUpClass', 'tearDownClass',  # Test methods
        }
        
        # Flask/web framework specific methods to exclude
        self.framework_methods = {
            'get', 'post', 'put', 'delete', 'patch', 'head', 'options',  # HTTP methods
            'before_request', 'after_request', 'teardown_request',  # Flask hooks
            'on_connect', 'on_disconnect', 'on_message',  # WebSocket handlers
            'handle', 'dispatch', 'run', 'start', 'stop',  # Common handlers
        }
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from analysis."""
        str_path = str(file_path)
        
        # Default exclusions
        if '__pycache__' in str_path or '.pyc' in str_path:
            return True
        
        # Check custom exclude patterns
        for pattern in self.exclude_patterns:
            if pattern in str_path:
                return True
        
        return False
    
    def analyze_file(self, file_path: Path) -> Tuple[Dict[str, MethodInfo], List[Tuple[str, str, int]]]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            analyzer = MethodAnalyzer(str(file_path))
            analyzer.visit(tree)
            
            return analyzer.methods, analyzer.method_calls
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
            return {}, []
    
    def scan_codebase(self):
        """Scan entire codebase for methods and their usages."""
        python_files = list(self.root_path.rglob("*.py"))
        
        # First pass: collect all method definitions
        print(f"Scanning {len(python_files)} Python files...")
        for file_path in python_files:
            if self.should_exclude_file(file_path):
                continue
            
            methods, _ = self.analyze_file(file_path)
            self.all_methods.update(methods)
        
        # Second pass: collect all method calls
        for file_path in python_files:
            if self.should_exclude_file(file_path):
                continue
            
            _, method_calls = self.analyze_file(file_path)
            
            for class_ref, method_name, line_no in method_calls:
                # Try to match with defined methods
                if class_ref:
                    method_key = f"{class_ref}.{method_name}"
                    if method_key in self.all_methods:
                        usage_type = 'internal' if self.all_methods[method_key].file_path == str(file_path) else 'external'
                        self.method_usages[method_key].append(
                            MethodUsage(
                                caller_file=str(file_path),
                                caller_class=None,
                                caller_method=None,
                                line_number=line_no,
                                usage_type=usage_type
                            )
                        )
                
                # Also check for any method with this name (partial matching)
                for key in self.all_methods:
                    if key.endswith(f".{method_name}"):
                        self.method_usages[key].append(
                            MethodUsage(
                                caller_file=str(file_path),
                                caller_class=None,
                                caller_method=None,
                                line_number=line_no,
                                usage_type='external'
                            )
                        )
    
    def find_unused_methods(self) -> Dict[str, List[MethodInfo]]:
        """Find all methods that are never called."""
        unused = defaultdict(list)
        
        for method_key, method_info in self.all_methods.items():
            # Skip special methods and framework methods
            if (method_info.method_name in self.excluded_methods or 
                method_info.method_name in self.framework_methods or
                method_info.method_name.startswith('_') and method_info.method_name != '__init__'):
                continue
            
            # Skip decorated methods (likely routes, handlers, etc.)
            if method_info.decorators:
                route_decorators = {'route', 'get', 'post', 'put', 'delete', 'patch'}
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
        else:
            return self._generate_text_report(unused_methods)
    
    def _generate_text_report(self, unused_methods: Dict[str, List[MethodInfo]]) -> str:
        """Generate human-readable text report."""
        report = []
        report.append("=" * 80)
        report.append("UNUSED METHOD DETECTION REPORT")
        report.append("=" * 80)
        report.append(f"Root Path: {self.root_path}")
        report.append(f"Total Methods Analyzed: {len(self.all_methods)}")
        
        total_unused = sum(len(methods) for methods in unused_methods.values())
        report.append(f"Total Unused Methods Found: {total_unused}")
        report.append("")
        
        if not unused_methods:
            report.append("No unused methods found!")
        else:
            for file_path, methods in sorted(unused_methods.items()):
                report.append("-" * 80)
                report.append(f"File: {file_path}")
                report.append(f"Unused Methods: {len(methods)}")
                report.append("")
                
                for method in sorted(methods, key=lambda m: m.line_number):
                    report.append(f"  Line {method.line_number:4d}: {method.class_name}.{method.method_name}()")
                    if method.decorators:
                        report.append(f"            Decorators: {', '.join(method.decorators)}")
                report.append("")
        
        report.append("=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)
        
        if unused_methods:
            report.append("Consider reviewing these methods for potential removal.")
            report.append("Note: Some methods might be called dynamically or via reflection.")
            report.append("Always verify before removing any code!")
        
        return "\n".join(report)
    
    def _generate_json_report(self, unused_methods: Dict[str, List[MethodInfo]]) -> str:
        """Generate JSON report for programmatic processing."""
        result = {
            "root_path": str(self.root_path),
            "total_methods": len(self.all_methods),
            "total_unused": sum(len(methods) for methods in unused_methods.values()),
            "unused_methods": {}
        }
        
        for file_path, methods in unused_methods.items():
            result["unused_methods"][file_path] = [
                {
                    "class": method.class_name,
                    "method": method.method_name,
                    "line": method.line_number,
                    "decorators": method.decorators
                }
                for method in methods
            ]
        
        return json.dumps(result, indent=2)


def main():
    """Main entry point for the utility."""
    parser = argparse.ArgumentParser(
        description="Detect unused methods in Python codebase"
    )
    parser.add_argument(
        "path",
        help="Root path of the codebase to analyze"
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help="Patterns to exclude from analysis (e.g., 'test', 'migrations')",
        default=[]
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
    
    args = parser.parse_args()
    
    # Create detector instance
    detector = UnusedMethodDetector(args.path, args.exclude)
    
    # Generate report
    report = detector.generate_report(args.format)
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()