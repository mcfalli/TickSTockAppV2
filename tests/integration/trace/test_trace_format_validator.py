#!/usr/bin/env python3
"""
Enhanced Trace Format Validator
Validates JSON structure, schema compliance, and data integrity.
Provides automated pre-flight checks before deployments.
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import re
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
class FormatValidator:
    """Enhanced format validation with pre-flight checks"""
    
    # Expected trace schema
    REQUIRED_FIELDS = {
        'timestamp': (float, int),
        'ticker': str,
        'component': str,
        'action': str
    }
    
    OPTIONAL_FIELDS = {
        'data': dict,
        'category': str,
        'trace_id': str
    }
    
    # In test_trace_format_validator.py, update VALID_ACTIONS:
    VALID_ACTIONS = {
        'DataProvider': ['tick_created', 'tick_received'],
        'CoreService': ['tick_received', 'tick_delegated', 'stats_update'],
        'EventProcessor': ['tick_delegated', 'event_queued', 'process_start', 'universe_check', 
                        'event_processing', 'process_complete'],
        'EventDetector': ['event_detected', 'detection_slow', 'detection_summary'],
        'DataPublisher': ['events_collected', 'display_queue_collected', 'collection_start',
                        'events_buffered', 'buffer_pulled', 'buffer_overflow', 'buffer_near_capacity',
                        'display_collection_complete', 'nvda_in_prepared_data'],
        'WebSocketPublisher': ['event_emitted', 'event_ready_for_emission', 'emission_start', 
                            'emission_complete', 'user_filtering_start', 'user_filtering_complete',
                            'status_update_start', 'status_update_complete', 'heartbeat_loop_start',
                            'emission_cycle_start', 'emission_cycle_complete', 'slow_buffer_pull',
                            'emission_drought', 'new_user_connection', 'user_ready_for_events',
                            'universe_resolved', 'universe_resolution_start', 'universe_resolution_complete',
                            'found_in_universe', 'filtering_nvda_events', 'nvda_filter_result',
                            'high_events_lost', 'emission_failed_no_manager', 'emission_skipped_no_users',
                            'initialization_complete', 'emission_cycle_attempt'],
        'PriorityManager': ['event_dropped', 'initialization_complete', 'circuit_breaker_trip',
                            'error', 'queue_sample', 'surge_event_queued', 'events_collected'],
        'UniverseManager': ['universe_resolved', 'found_in_universe'],
        # Add new components found in trace report:
        'WorkerPool': ['tick_processing_failed', 'tick_processing_success', 'event_stored',
                    'event_bypass_storage', 'event_requeued_for_display', 'display_queue_full',
                    'worker_started', 'worker_stopped', 'batch_processed'],
        'WorkerPoolManager': ['initialization_complete', 'adjust_pool_begin', 'adjust_pool_complete',
                            'health_check_performed', 'start_workers_begin', 'start_workers_complete',
                            'stop_workers_begin', 'stop_workers_complete'],
        'TickProcessor': ['rate_limit_blocked', 'rate_limit_passed'],
        'SurgeDetector': ['event_detected', 'surge_cooldown_blocked', 'buffer_overflow', 
                        'buffer_updated', 'surge_cleanup', 'surge_skipped'],
        'TrendDetector': ['event_detected', 'initialization_complete', 'window_analysis_start',
                        'window_analysis_complete', 'ticker_initialized', 'cleanup_complete',
                        'detection_slow', 'daily_counts_reset'],
        'SimulatedDataProvider': ['tick_generated', 'initialized'],
        'SyntheticDataGenerator': ['tick_created', 'event_generated', 'batch_complete', 'initialized'],
        'WebSocketManager': ['user_connected', 'user_disconnected', 'user_emission', 'broadcast_complete',
                            'market_status_broadcast', 'error_emitted', 'heartbeat_sent', 
                            'connection_stats_retrieved', 'generic_client_registered',
                            'generic_client_unregistered', 'initialization_complete']
    }
    
    # Expected event types
    VALID_EVENT_TYPES = {
        'high', 'low', 'surge', 'trend', 
        'session_high', 'session_low', 
        'multiple', 'unknown'
    }
        
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.stats = defaultdict(int)
        self.trace_path = './logs/trace/'  # Default path
        
    def validate_file(self, filename: str) -> bool:
        """Comprehensive file validation"""
        print(f"[SEARCH] TRACE FORMAT VALIDATOR")
        print(f"{'='*80}")
        
        # Use stored trace_path or default
        #trace_path = getattr(self, 'trace_path', './logs/trace/')
        trace_path = self.trace_path
        full_path = os.path.join(trace_path, filename)
        
        print(f"[FILE] File: {full_path}")
        
        # Check file existence
        if not os.path.exists(full_path):
            self.errors.append(f"File not found: {full_path}")
            self._print_results()
            return False
        
        # Check file size - FIXED: use full_path instead of filename
        file_size = os.path.getsize(full_path)
        print(f"[CHART] File size: {self._format_size(file_size)}")
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            self.warnings.append(f"Large file size: {self._format_size(file_size)}")
        
        # Load and parse JSON
        try:
            with open(full_path, 'r') as f:  # FIXED: use full_path
                content = f.read()
            
            # Check for common JSON issues
            self._check_json_integrity(content)
            
            # Parse JSON
            data = json.loads(content)
            
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON parsing error: {e}")
            self._attempt_json_recovery(content)
            self._print_results()
            return False
        except Exception as e:
            self.errors.append(f"File read error: {e}")
            self._print_results()
            return False
        
        # Validate structure
        self._validate_structure(data)
        
        # Extract traces
        traces = self._extract_traces(data)
        if not traces:
            self.errors.append("No traces found in file")
            self._print_results()
            return False
        
        print(f"[CHART] Traces found: {len(traces)}")
        
        # Validate each trace
        self._validate_traces(traces)
        
        # Check data integrity
        self._check_data_integrity(traces)
        
        # Check for known issues
        self._check_known_issues(traces)
        
        # Run pre-flight checks
        self._run_preflight_checks(traces)
        
        # Print results
        self._print_results()
        
        return len(self.errors) == 0
    
    def _format_size(self, size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def _check_json_integrity(self, content: str):
        """Check for common JSON formatting issues"""
        # Check for trailing commas
        if re.search(r',\s*}', content) or re.search(r',\s*]', content):
            self.warnings.append("Found trailing commas in JSON")
        
        # Check for truncation
        if content.strip().endswith(','):
            self.errors.append("JSON appears to be truncated (ends with comma)")
        
        # Check for proper closure
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            self.errors.append(f"Mismatched braces: {open_braces} open, {close_braces} close")
        
        open_brackets = content.count('[')
        close_brackets = content.count(']')
        if open_brackets != close_brackets:
            self.errors.append(f"Mismatched brackets: {open_brackets} open, {close_brackets} close")
    
    def _attempt_json_recovery(self, content: str):
        """Attempt to recover from common JSON errors"""
        print("\n[TOOL] Attempting JSON recovery...")
        
        fixed = content.strip()
        
        # Remove trailing comma
        if fixed.endswith(','):
            fixed = fixed[:-1]
            self.info.append("Removed trailing comma")
        
        # Wrap in array if needed
        if not fixed.startswith('[') and '"ticker"' in fixed:
            fixed = '[' + fixed + ']'
            self.info.append("Wrapped content in array")
        
        # Try to parse fixed JSON
        try:
            data = json.loads(fixed)
            self.info.append(f"[OK] Recovery successful! Found {len(data)} items")
            
            # Save fixed file
            recovery_file = 'recovered_trace.json'
            with open(recovery_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.info.append(f"Saved recovered data to {recovery_file}")
            
        except json.JSONDecodeError:
            self.errors.append("Recovery failed - manual intervention required")
    
    def _validate_structure(self, data: Any):
        """Validate overall JSON structure"""
        if isinstance(data, dict):
            # Check for wrapper format
            if 'steps' in data:
                self.info.append("Found trace wrapper format")
                self.stats['wrapper_format'] = 1
                
                # Validate wrapper fields
                if 'trace_id' in data:
                    self.stats['has_trace_id'] = 1
                if 'duration_seconds' in data:
                    self.stats['has_duration'] = 1
                    
            elif 'traces' in data:
                self.info.append("Found traces array format")
            else:
                self.warnings.append("Unknown dictionary structure")
                
        elif isinstance(data, list):
            self.info.append("Found direct array format")
            self.stats['array_format'] = 1
        else:
            self.errors.append(f"Unexpected root type: {type(data)}")
    
    def _extract_traces(self, data: Any) -> List[dict]:
        """Extract trace entries from various formats"""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            if 'steps' in data:
                return data['steps']
            elif 'traces' in data:
                return data['traces']
        return []
    
    def _validate_traces(self, traces: List[dict]):
        """Validate individual trace entries"""
        print(f"\n[LIST] Validating {len(traces)} traces...")
        
        invalid_count = 0
        sample_errors = defaultdict(list)
        
        for i, trace in enumerate(traces):
            if not isinstance(trace, dict):
                invalid_count += 1
                sample_errors['not_dict'].append(i)
                continue
            
            # Check required fields
            for field, expected_types in self.REQUIRED_FIELDS.items():
                if field not in trace:
                    invalid_count += 1
                    sample_errors[f'missing_{field}'].append(i)
                else:
                    # Check type
                    value = trace[field]
                    if not isinstance(value, expected_types):
                        sample_errors[f'invalid_{field}_type'].append(i)
            
            # Validate specific fields
            self._validate_trace_fields(trace, i)
        
        # Report validation results
        if invalid_count > 0:
            self.errors.append(f"{invalid_count} traces failed validation")
            
        for error_type, indices in sample_errors.items():
            if indices:
                sample = indices[:3]
                msg = f"{error_type}: {len(indices)} occurrences (samples: {sample})"
                if len(indices) > 10:
                    self.errors.append(msg)
                else:
                    self.warnings.append(msg)
    
    def _validate_trace_fields(self, trace: dict, index: int):
        """Validate specific trace fields"""
        # Validate timestamp
        if 'timestamp' in trace:
            try:
                ts = float(trace['timestamp'])
                if ts <= 0:
                    self.warnings.append(f"Trace {index}: Invalid timestamp {ts}")
                # Check if timestamp is reasonable (not too old or future)
                now = datetime.now().timestamp()
                if abs(now - ts) > 365 * 24 * 3600:  # More than a year off
                    self.warnings.append(f"Trace {index}: Suspicious timestamp (off by >1 year)")
            except:
                self.errors.append(f"Trace {index}: Timestamp not numeric")
        
        # Validate component/action pair
        component = trace.get('component', '')
        action = trace.get('action', '')
        
        if component in self.VALID_ACTIONS:
            if action not in self.VALID_ACTIONS[component]:
                self.warnings.append(f"Trace {index}: Unexpected action '{action}' for component '{component}'")
        
        # Validate data field
        if 'data' in trace:
            self._validate_data_field(trace['data'], index)
    
    def _validate_data_field(self, data: Any, trace_index: int):
        """Validate the data field of a trace"""
        if isinstance(data, str):
            self.warnings.append(f"Trace {trace_index}: Data field is string (should be dict)")
            # Try to parse
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    self.info.append(f"Trace {trace_index}: String data is valid JSON")
            except:
                self.errors.append(f"Trace {trace_index}: String data is not valid JSON")
        
        elif isinstance(data, dict):
            # Check for string/integer issues
            for key, value in data.items():
                if key.endswith('_count') and isinstance(value, str):
                    self.warnings.append(f"Trace {trace_index}: {key} is string (should be int)")
                    try:
                        int(value)
                    except:
                        self.errors.append(f"Trace {trace_index}: {key} value '{value}' not convertible to int")
            
            # Validate event types
            details = data.get('details', {})
            if isinstance(details, dict) and 'event_type' in details:
                event_type = details['event_type']
                normalized = self._normalize_event_type(event_type)
                if normalized not in self.VALID_EVENT_TYPES:
                    self.warnings.append(f"Trace {trace_index}: Unknown event type '{event_type}'")
    
    def _normalize_event_type(self, event_type: str) -> str:
        """Normalize event type"""
        if not event_type:
            return 'unknown'
        
        normalized = str(event_type).lower()
        
        # Map variations
        mappings = {
            'session_high': 'high',
            'session_low': 'low',
            '_low': 'low'
        }
        
        return mappings.get(normalized, normalized)
    
    def _check_data_integrity(self, traces: List[dict]):
        """Check overall data integrity"""
        print("\n[SEARCH] Checking data integrity...")
        
        # Check chronological order
        timestamps = []
        for trace in traces:
            if 'timestamp' in trace:
                try:
                    timestamps.append(float(trace['timestamp']))
                except:
                    pass
        
        if timestamps:
            if timestamps != sorted(timestamps):
                self.warnings.append("Traces not in chronological order")
                
                # Find biggest jumps
                out_of_order = 0
                for i in range(1, len(timestamps)):
                    if timestamps[i] < timestamps[i-1]:
                        out_of_order += 1
                
                self.info.append(f"Found {out_of_order} out-of-order timestamps")
        
        # Check for duplicates
        seen = set()
        duplicates = 0
        
        for trace in traces:
            # Create a signature
            sig = (
                trace.get('timestamp', 0),
                trace.get('ticker', ''),
                trace.get('action', ''),
                str(trace.get('data', {}))
            )
            
            if sig in seen:
                duplicates += 1
            seen.add(sig)
        
        if duplicates > 0:
            self.warnings.append(f"Found {duplicates} duplicate traces")
        
        # Check ticker consistency
        tickers = defaultdict(int)
        for trace in traces:
            ticker = trace.get('ticker', 'UNKNOWN')
            tickers[ticker] += 1
        
        self.info.append(f"Found {len(tickers)} unique tickers: {dict(tickers)}")
    
    def _check_known_issues(self, traces: List[dict]):
        """Check for known issues from Sprint 27"""
        print("\n[BUG] Checking for known issues...")
        
        # Check for missing event_ready_for_emission
        has_ready_for_emission = any(
            t.get('action') == 'event_ready_for_emission' 
            for t in traces
        )
        
        if not has_ready_for_emission:
            self.errors.append("Missing 'event_ready_for_emission' traces (Sprint 27 issue)")
        
        # Check for string event counts
        string_counts = 0
        for trace in traces:
            data = trace.get('data', {})
            if isinstance(data, dict):
                details = data.get('details', {})
                if isinstance(details, dict):
                    breakdown = details.get('event_breakdown', {})
                    if isinstance(breakdown, dict):
                        for key, value in breakdown.items():
                            if isinstance(value, str):
                                string_counts += 1
        
        if string_counts > 0:
            self.warnings.append(f"Found {string_counts} string event counts (should be integers)")
        
        # Check event type variations
        event_types = set()
        for trace in traces:
            data = trace.get('data', {})
            if isinstance(data, dict):
                details = data.get('details', {})
                if isinstance(details, dict) and 'event_type' in details:
                    event_types.add(details['event_type'])
        
        problematic_types = [et for et in event_types if et in ['session_high', 'session_low', '_low']]
        if problematic_types:
            self.warnings.append(f"Found non-normalized event types: {problematic_types}")
    
    def _run_preflight_checks(self, traces: List[dict]):
        """Run pre-flight deployment checks"""
        print("\n[PLANE]  Running pre-flight checks...")
        
        checks_passed = []
        checks_failed = []
        
        # Check 1: Minimum trace count
        if len(traces) >= 100:
            checks_passed.append("Sufficient trace volume")
        else:
            checks_failed.append(f"Low trace count ({len(traces)} < 100)")
        
        # Check 2: All critical actions present
        critical_actions = [
            'event_detected', 'event_queued', 'event_emitted',
            'event_ready_for_emission'
        ]
        
        present_actions = set(t.get('action', '') for t in traces)
        missing_actions = set(critical_actions) - present_actions
        
        if not missing_actions:
            checks_passed.append("All critical actions present")
        else:
            checks_failed.append(f"Missing critical actions: {missing_actions}")
        
        # Check 3: Error rate
        error_actions = ['error', 'exception', 'failed']
        error_count = sum(
            1 for t in traces 
            if any(err in t.get('action', '').lower() for err in error_actions)
        )
        
        error_rate = (error_count / len(traces) * 100) if traces else 0
        if error_rate < 1:
            checks_passed.append(f"Low error rate ({error_rate:.2f}%)")
        else:
            checks_failed.append(f"High error rate ({error_rate:.2f}%)")
        
        # Check 4: Event flow completeness
        event_ids = defaultdict(set)
        for trace in traces:
            data = trace.get('data', {})
            if isinstance(data, dict):
                details = data.get('details', {})
                event_id = details.get('event_id') or data.get('event_id')
                if event_id and event_id != 'None':
                    event_ids[trace.get('action', '')].add(event_id)
        
        detected = len(event_ids.get('event_detected', set()))
        emitted = len(event_ids.get('event_emitted', set()))
        
        if detected > 0:
            efficiency = (emitted / detected * 100)
            if efficiency >= 85:
                checks_passed.append(f"Good event flow efficiency ({efficiency:.1f}%)")
            else:
                checks_failed.append(f"Poor event flow efficiency ({efficiency:.1f}%)")
        
        # Print pre-flight results
        print(f"\n[OK] Passed: {len(checks_passed)}")
        for check in checks_passed:
            print(f"  [v] {check}")
        
        if checks_failed:
            print(f"\n[X] Failed: {len(checks_failed)}")
            for check in checks_failed:
                print(f"  [x] {check}")
        
        # Overall pre-flight status
        if not checks_failed:
            print(f"\n[PLANE]  PRE-FLIGHT STATUS: READY FOR DEPLOYMENT")
        else:
            print(f"\n[STOP] PRE-FLIGHT STATUS: NOT READY FOR DEPLOYMENT")
    
    def _print_results(self):
        """Print validation results"""
        print(f"\n{'='*80}")
        print("[CHART] VALIDATION SUMMARY")
        print(f"{'='*80}")
        
        # Print errors
        if self.errors:
            print(f"\n[X] Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        # Print warnings
        if self.warnings:
            print(f"\n[!]  Warnings ({len(self.warnings)}):")
            for warning in self.warnings[:10]:  # Limit to 10
                print(f"  • {warning}")
            if len(self.warnings) > 10:
                print(f"  • ... and {len(self.warnings) - 10} more")
        
        # Print info
        if self.info:
            print(f"\n[i]  Information:")
            for info in self.info[:5]:  # Limit to 5
                print(f"  • {info}")
        
        # Overall status
        if not self.errors:
            print(f"\n[OK] VALIDATION PASSED")
        else:
            print(f"\n[X] VALIDATION FAILED")
        
        print(f"{'='*80}")

def main():
    """Main entry point with standardized argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate trace file JSON format and structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                           # Use default trace_all.json
  %(prog)s NVDA.json                 # Validate specific file
  %(prog)s NVDA.json /custom/path/   # Custom path and file
        '''
    )
    
    parser.add_argument('filename', nargs='?', default='trace_all.json',
                       help='Trace filename with .json extension (default: trace_all.json)')
    parser.add_argument('trace_path', nargs='?', default='./logs/trace/',
                       help='Path to trace directory (default: ./logs/trace/)')
    
    args = parser.parse_args()
    
    validator = FormatValidator()
    validator.trace_path = args.trace_path
    success = validator.validate_file(args.filename)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()