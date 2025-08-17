#!/usr/bin/env python3
"""
Tracer Entry Dump Tool for TickStock
Extracts tracer.should_trace and tracer.trace statements from methods (outside exception blocks) and generates a report in /logs/
"""
import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

class TracerAnalyzer:
    """Analyze Python files for tracer statements in methods."""
    
    def __init__(self):
        self.trace_patterns = {
            'should_trace': re.compile(r'tracer\.should_trace\((.*?)\)', re.DOTALL),
            'trace': re.compile(r'tracer\.trace\((.*?)\)', re.DOTALL),
        }
        self.method_pattern = re.compile(r'^\s{4}def\s+(\w+)\s*\(', re.MULTILINE)
        self.except_pattern = re.compile(r'^\s*except\s*(?:\w+\s*(?:,\s*\w+)*\s*)?(?:as\s*\w+\s*)?:', re.MULTILINE)
        
    def analyze_file(self, filepath: str) -> Dict:
        """Analyze a single Python file for tracer statements."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {'error': str(e), 'filename': os.path.basename(filepath)}
        
        methods = self._extract_methods_with_context(content)
        
        file_analysis = {
            'filename': os.path.basename(filepath),
            'relative_path': self._get_relative_path(filepath),
            'methods': {}
        }
        
        for method_name, method_content, line_start in methods:
            method_traces = self._analyze_method_tracing(method_content)
            if method_traces:
                file_analysis['methods'][method_name] = {
                    'line': line_start,
                    'traces': method_traces
                }
        
        return file_analysis
    
    def _get_relative_path(self, filepath: str) -> str:
        """Get a cleaner relative path for display."""
        try:
            return os.path.relpath(filepath)
        except:
            return filepath
    
    def _extract_methods_with_context(self, content: str) -> List[Tuple[str, str, int]]:
        """Extract method names with their content and line numbers."""
        methods = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            method_match = self.method_pattern.match(line)
            if method_match:
                method_name = method_match.group(1)
                method_lines = [line]
                indent = len(line) - len(line.lstrip())
                
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    if next_line.strip() == '':
                        method_lines.append(next_line)
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= indent and next_line.strip():
                        break
                    method_lines.append(next_line)
                
                method_content = '\n'.join(method_lines)
                methods.append((method_name, method_content, i + 1))
        
        return methods
    
    def _analyze_method_tracing(self, method_content: str) -> List[Dict]:
        """Extract tracer statements outside exception blocks."""
        traces = []
        lines = method_content.split('\n')
        in_except_block = False
        except_indent = None
        
        for i, line in enumerate(lines):
            if self.except_pattern.match(line):
                in_except_block = True
                except_indent = len(line) - len(line.lstrip())
                continue
            
            if in_except_block:
                current_indent = len(line) - len(line.lstrip())
                if line.strip() and current_indent <= except_indent:
                    in_except_block = False
                    except_indent = None
                continue
            
            for trace_type, pattern in self.trace_patterns.items():
                matches = pattern.findall(line)
                for _ in matches:  # We don't need the arg content, just flag
                    traces.append({
                        'type': trace_type,
                        'line': i + 1
                    })
        
        return traces
    
    def generate_report(self, results: List[Dict]) -> str:
        """Generate a report of tracer statements."""
        report_lines = [
            "=" * 80,
            "TickStock Tracer Entries Report",
            "=" * 80,
            ""
        ]
        
        total_files = len(results)
        total_methods = sum(len(r.get('methods', {})) for r in results)
        total_traces = sum(
            sum(len(method_data['traces']) for method_data in r.get('methods', {}).values())
            for r in results
        )
        
        report_lines.extend([
            f"Files Analyzed: {total_files}",
            f"Methods with Tracers: {total_methods}",
            f"Total Tracer Statements: {total_traces}",
            "",
            "Tracer Entries by File and Method:",
            "=" * 80,
        ])
        
        for result in sorted(results, key=lambda x: x['relative_path']):
            if 'error' in result:
                report_lines.append(f"\n⚠️ {result['filename']}: Error - {result['error']}")
                continue
                
            methods = result.get('methods', {})
            if not methods:
                continue
                
            report_lines.append(f"\n📁 {result['relative_path']}")
            report_lines.append("-" * 60)
            
            for method_name, method_data in sorted(methods.items()):
                report_lines.append(f"  Method: {method_name} (line {method_data['line']})")
                if not method_data['traces']:
                    report_lines.append("    No tracer statements found")
                    continue
                
                for trace in method_data['traces']:
                    report_lines.append(
                        f"    {trace['type'].upper()} (line {trace['line']})"
                    )
        
        if not any(len(r.get('methods', {})) for r in results):
            report_lines.append("\n⚠️ No tracer statements found in analyzed files")
        
        return "\n".join(report_lines)


def analyze_project(directories: List[str], specific_files: List[str], output_dir: str = "logs"):
    """Analyze tracing in project directories and specific files."""
    analyzer = TracerAnalyzer()
    results = []
    
    print("🔍 Analyzing Python files for tracer statements...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "tracer_entries_report.txt")
    
    # Analyze directories
    for directory in directories:
        if os.path.exists(directory):
            print(f"\n📁 Scanning directory: {directory}")
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if not d.startswith('__') and d != 'venv']
                
                for file in files:
                    if file.endswith('.py'):
                        filepath = os.path.join(root, file)
                        print(f"  Analyzing: {filepath}")
                        result = analyzer.analyze_file(filepath)
                        if 'error' not in result:
                            results.append(result)
        else:
            print(f"  ⚠️ Directory not found: {directory}")
    
    # Analyze specific files
    if specific_files:
        print(f"\n📄 Analyzing specific files:")
        for filepath in specific_files:
            if os.path.exists(filepath) and filepath.endswith('.py'):
                print(f"  Analyzing: {filepath}")
                result = analyzer.analyze_file(filepath)
                if 'error' not in result:
                    results.append(result)
            else:
                print(f"  ⚠️ File not found or not Python: {filepath}")
    
    # Generate and save report
    report = analyzer.generate_report(results)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ Analysis complete! Report saved to: {output_file}")
    except Exception as e:
        print(f"\n❌ Error saving report: {str(e)}")
        print("\nReport Preview:")
        print(report[:1000] + "..." if len(report) > 1000 else report)
    
    total_traces = sum(
        sum(len(method_data.get('traces', [])) for method_data in r.get('methods', {}).values())
        for r in results
    )
    print(f"\nSummary:")
    print(f"  Files analyzed: {len(results)}")
    print(f"  Methods with tracers: {sum(len(r.get('methods', {})) for r in results)}")
    print(f"  Total tracer statements: {total_traces}")
    
    return results
if __name__ == "__main__":
    # Directories to analyze (unchanged)
    directories_to_analyze = [
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
    # Specific files (unchanged)
    specific_files = [
        "app.py",
        "app_config.py",
        "app_forms.py",
        "app_routes_api.py",
        "app_routes_auth.py",
        "app_routes_main.py",
        "app_startup.py",
        "app_utils.py",
    ]
    
    analyze_project(directories_to_analyze, specific_files)