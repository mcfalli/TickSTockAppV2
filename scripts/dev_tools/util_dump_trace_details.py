#!/usr/bin/env python3
"""
Tracer Entry Dump Tool for TickStock
Extracts tracer.should_trace and tracer.trace statements from methods (outside exception blocks) and generates a report in /logs/
"""
import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set

class TracerAnalyzer:
    """Analyze Python files for tracer statements in methods."""
    
    def __init__(self):
        self.trace_starts = {
            'should_trace': 'tracer.should_trace(',
            'trace': 'tracer.trace(',
        }
        self.method_pattern = re.compile(r'^\s{4}def\s+(\w+)\s*\(', re.MULTILINE)
        self.except_pattern = re.compile(r'^\s*except\s*(?:\w+\s*(?:,\s*\w+)*\s*)?(?:as\s*\w+\s*)?:', re.MULTILINE)
        # Track processed files to avoid duplicates
        self.processed_files = set()
        
    def analyze_file(self, filepath: str) -> Dict:
        """Analyze a single Python file for tracer statements."""
        # Get absolute path to handle duplicates
        abs_filepath = os.path.abspath(filepath)
        
        # Skip if already processed
        if abs_filepath in self.processed_files:
            return None
            
        self.processed_files.add(abs_filepath)
        
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
        """Extract full tracer statements outside exception blocks."""
        traces = []
        lines = method_content.split('\n')
        in_except_block = False
        except_indent = None
        
        for i, line in enumerate(lines):
            # Check if entering except block
            if self.except_pattern.match(line):
                in_except_block = True
                except_indent = len(line) - len(line.lstrip())
                continue
            
            # Check if leaving except block
            if in_except_block:
                current_indent = len(line) - len(line.lstrip())
                if line.strip() and current_indent <= except_indent:
                    in_except_block = False
                    except_indent = None
            
            # Skip if in except block
            if in_except_block:
                continue
            
            # Look for trace starts in this line
            for trace_type, start_str in self.trace_starts.items():
                if start_str in line:
                    # Extract from this line onward
                    start_idx = line.find(start_str)
                    # Get full multi-line trace call
                    full_content = self._extract_multiline_trace(lines, i, start_idx)
                    if full_content:
                        # Format: split lines, strip, join with |
                        content_lines = full_content.split('\n')
                        formatted = '|'.join(line.strip() for line in content_lines if line.strip())
                        traces.append({
                            'type': trace_type,
                            'line': i + 1,
                            'content': formatted
                        })
        
        return traces
    
    def _extract_multiline_trace(self, lines: List[str], start_line_idx: int, start_pos_in_line: int) -> str:
        """Extract a potentially multi-line trace call."""
        result = []
        balance = 0
        started = False
        
        for i in range(start_line_idx, len(lines)):
            line = lines[i]
            
            if i == start_line_idx:
                # First line - start from the trace call
                line = line[start_pos_in_line:]
            
            for char in line:
                if char == '(':
                    balance += 1
                    started = True
                elif char == ')':
                    balance -= 1
                
                if started:
                    result.append(char)
                    
                if started and balance == 0:
                    return ''.join(result)
            
            if started:
                result.append('\n')
        
        return ''  # Unbalanced parentheses
    
    def generate_report(self, results: List[Dict]) -> str:
        """Generate a report of tracer statements."""
        # Filter out None results (duplicates)
        results = [r for r in results if r is not None]
        
        report_lines = [
            "=" * 80,
            "TickStock Tracer Entries Report",
            "Identifies tracer.should_trace() and tracer.trace() calls within Python methods,",
            "excluding those in exception blocks.",
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
                        f"    {trace['type'].upper()} (line {trace['line']}): {trace['content']}"
                    )
        
        if not any(len(r.get('methods', {})) for r in results):
            report_lines.append("\n⚠️ No tracer statements found in analyzed files")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append(f"Processing complete: {len(self.processed_files)} unique files analyzed")
        
        return "\n".join(report_lines)


def analyze_project(directories: List[str], specific_files: List[str], output_dir: str = "logs"):
    """Analyze tracing in project directories and specific files."""
    analyzer = TracerAnalyzer()
    results = []
    
    print("🔍 Analyzing Python files for tracer statements...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "tracer_entries_report.txt")
    
    # Analyze directories (without recursion into subdirectories already listed)
    processed_paths = set()
    
    for directory in directories:
        if os.path.exists(directory):
            dir_path = os.path.abspath(directory)
            if dir_path not in processed_paths:
                processed_paths.add(dir_path)
                print(f"\n📁 Scanning directory: {directory}")
                
                # Only process files in this specific directory
                # Don't recurse if subdirectories are explicitly listed
                for file in os.listdir(directory):
                    filepath = os.path.join(directory, file)
                    if os.path.isfile(filepath) and file.endswith('.py'):
                        print(f"  Analyzing: {filepath}")
                        result = analyzer.analyze_file(filepath)
                        if result and 'error' not in result:
                            results.append(result)
        else:
            print(f"  ⚠️ Directory not found: {directory}")
    
    # Analyze specific files
    if specific_files:
        print(f"\n📄 Analyzing specific files in root directory:")
        for filepath in specific_files:
            # Check if file exists
            file_exists = os.path.exists(filepath)
            is_python = filepath.endswith('.py')
            
            if file_exists and is_python:
                print(f"  ✓ Analyzing: {filepath}")
                result = analyzer.analyze_file(filepath)
                if result and 'error' not in result:
                    results.append(result)
                elif result and 'error' in result:
                    print(f"    Error analyzing file: {result['error']}")
            else:
                if not file_exists:
                    # Try to provide more helpful information
                    print(f"  ⚠️ File not found: {filepath}")
                    # Check if it exists with different casing or in current directory
                    cwd_path = os.path.join(os.getcwd(), filepath)
                    if os.path.exists(cwd_path):
                        print(f"    Found at: {cwd_path}")
                elif not is_python:
                    print(f"  ⚠️ Not a Python file: {filepath}")
    
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
    
    # Filter out None results for summary
    valid_results = [r for r in results if r is not None]
    total_traces = sum(
        sum(len(method_data.get('traces', [])) for method_data in r.get('methods', {}).values())
        for r in valid_results
    )
    
    print(f"\nSummary:")
    print(f"  Files analyzed: {len(valid_results)}")
    print(f"  Duplicate files skipped: {len(analyzer.processed_files) - len(valid_results)}")
    print(f"  Methods with tracers: {sum(len(r.get('methods', {})) for r in valid_results)}")
    print(f"  Total tracer statements: {total_traces}")
    
    return valid_results

if __name__ == "__main__":
    # FIXED: Include both parent directories and subdirectories where needed
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
        "data_providers",  # Added back - may have files in root
        "data_providers/base",
        "data_providers/polygon",
        "data_providers/simulated",
        "event_detection",  # Added back - has files in root
        "event_detection/engines",  # Keep subdirectory too
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
    # Note: app_config.py is in the config/ directory, not root
    specific_files = [
        "app.py",
        "app_forms.py",
        "app_routes_api.py",
        "app_routes_auth.py",
        "app_routes_main.py",
        "app_startup.py",
        "app_utils.py",
    ]
    
    # Debug: Check which root files actually exist
    print("\n🔎 Checking for root Python files:")
    for file in specific_files:
        if os.path.exists(file):
            print(f"  ✓ Found: {file}")
        else:
            print(f"  ✗ Missing: {file}")
    
    analyze_project(directories_to_analyze, specific_files)