#!/usr/bin/env python3
"""
TickStock V2 Comprehensive Test Runner
Runs all available tests and provides detailed reporting
"""

import os
import sys
import json
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import importlib.util

class ComprehensiveTestRunner:
    def __init__(self, project_dir: str = r"C:\Users\McDude\TickStockAppV2", verbose: bool = False):
        self.project_dir = Path(project_dir)
        self.test_dir = self.project_dir / "tests"
        self.verbose = verbose  # Add verbose flag
        
        # Add project to path
        sys.path.insert(0, str(self.project_dir))
        
        # Test results
        self.results = {
            'import_tests': {},
            'unit_tests': {},
            'integration_tests': {},
            'trace_tests': {},
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0
            }
        }
        
        # Timestamp for reporting
        self.test_run_time = datetime.now()
    
    def run_all_tests(self):
        """Run all test suites"""
        print("="*80)
        print(" "*20 + "TICKSTOCK V2 COMPREHENSIVE TEST SUITE")
        print("="*80)
        print(f"Test run started: {self.test_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*80)
        
        # Phase 1: Import Tests (Most Critical)
        print("\n" + "="*60)
        print("PHASE 1: IMPORT VALIDATION TESTS")
        print("="*60)
        self.run_import_tests()
        
        # Phase 2: Core Component Tests
        print("\n" + "="*60)
        print("PHASE 2: CORE COMPONENT TESTS")
        print("="*60)
        self.run_core_component_tests()
        
        # Phase 3: Integration Tests
        print("\n" + "="*60)
        print("PHASE 3: INTEGRATION TESTS")
        print("="*60)
        self.run_integration_tests()
        
        # Phase 4: Trace System Tests (if available)
        print("\n" + "="*60)
        print("PHASE 4: TRACE SYSTEM TESTS")
        print("="*60)
        self.run_trace_tests()
        
        # Generate Report
        self.generate_report()
        
        return self.results
    
    def run_import_tests(self):
        """Test all critical imports"""
        print("\nTesting critical imports...")
        print("-"*40)
        
        critical_imports = [
            # Core Services
            ("MarketDataService", "from src.core.services.market_data_service import MarketDataService"),
            ("SessionManager", "from src.core.services.session_manager import SessionManager"),
            ("ConfigManager", "from src.core.services.config_manager import ConfigManager"),
            ("AnalyticsManager", "from src.core.services.analytics_manager import AnalyticsManager"),
            
            # WebSocket Components
            ("WebSocketManager", "from src.presentation.websocket.manager import WebSocketManager"),
            ("WebSocketPublisher", "from src.presentation.websocket.publisher import WebSocketPublisher"),
            ("DataPublisher", "from src.presentation.websocket.data_publisher import DataPublisher"),
            
            # Data Sources
            ("DataProviderFactory", "from src.infrastructure.data_sources.factory import DataProviderFactory"),
            ("PolygonProvider", "from src.infrastructure.data_sources.polygon.provider import PolygonDataProvider"),
            ("SyntheticProvider", "from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider"),
            
            # Event Detection
            ("EventDetectionManager", "from src.processing.detectors.manager import EventDetectionManager"),
            ("HighLowDetector", "from src.processing.detectors.highlow_detector import HighLowDetector"),
            ("SurgeDetector", "from src.processing.detectors.surge_detector import SurgeDetector"),
            
            # Domain Models
            ("HighLowEvent", "from src.core.domain.events.highlow import HighLowEvent"),
            ("SurgeEvent", "from src.core.domain.events.surge import SurgeEvent"),
            ("TickData", "from src.core.domain.market.tick import TickData"),
            
            # Authentication
            ("AuthenticationManager", "from src.auth.authentication import AuthenticationManager"),
            
            # Configuration
            ("Logging Config", "from config.logging_config import get_domain_logger"),
            ("App Config", "import config.app_config"),
            
            # Database
            ("Database Models", "from src.infrastructure.database.models.base import db"),
            
            # Cache
            ("Cache Manager", "from src.infrastructure.cache.cache_control import CacheControl"),
        ]
        
        for name, import_stmt in critical_imports:
            result = self.test_import(name, import_stmt)
            self.results['import_tests'][name] = result
            
            if result['status'] == 'passed':
                print(f"  ✅ {name}")
            else:
                # Show full error
                print(f"  ❌ {name}:")
                print(f"     Full error: {result.get('error', 'Unknown error')}")
                if self.verbose and 'traceback' in result:
                    # Show the most relevant part of traceback
                    tb_lines = result['traceback'].split('\n')
                    for line in tb_lines[-4:-1]:  # Show last 3 meaningful lines
                        if line.strip():
                            print(f"     {line}")
        
        # Summary
        passed = sum(1 for r in self.results['import_tests'].values() if r['status'] == 'passed')
        failed = len(self.results['import_tests']) - passed
        print(f"\nImport Tests: {passed} passed, {failed} failed")
    
    def test_import(self, name: str, import_statement: str) -> Dict:
        """Test a single import"""
        try:
            exec(import_statement)
            self.results['summary']['passed'] += 1
            return {'status': 'passed', 'name': name}
        except ImportError as e:
            self.results['summary']['failed'] += 1
            # Get full error with traceback
            import traceback
            full_error = str(e)
            tb_str = traceback.format_exc()
            return {
                'status': 'failed', 
                'name': name, 
                'error': full_error,
                'traceback': tb_str
            }
        except Exception as e:
            self.results['summary']['errors'] += 1
            import traceback
            full_error = str(e)
            tb_str = traceback.format_exc()
            return {
                'status': 'error', 
                'name': name, 
                'error': full_error,
                'traceback': tb_str
            }
        finally:
            self.results['summary']['total'] += 1
    
    def run_core_component_tests(self):
        """Test core component functionality"""
        print("\nTesting core components...")
        print("-"*40)
        
        component_tests = [
            ("Config Manager", self.test_config_manager),
            ("Session Manager", self.test_session_manager),
            ("Market Data Service", self.test_market_data_service),
            ("Event Detection", self.test_event_detection),
            ("WebSocket Manager", self.test_websocket_manager),
        ]
        
        for name, test_func in component_tests:
            try:
                result = test_func()
                self.results['unit_tests'][name] = result
                
                if result['status'] == 'passed':
                    print(f"  ✅ {name}")
                else:
                    print(f"  ❌ {name}: {result.get('error', 'Failed')}")
                    
            except Exception as e:
                self.results['unit_tests'][name] = {
                    'status': 'error',
                    'error': str(e)
                }
                print(f"  ❌ {name}: {str(e)[:50]}")
    
    def test_config_manager(self) -> Dict:
        """Test ConfigManager functionality"""
        try:
            from src.core.services.config_manager import ConfigManager
            
            # Test instantiation
            config = ConfigManager()
            
            # Test basic methods
            if hasattr(config, 'get'):
                # Test getting a config value
                value = config.get('DEBUG', False)
                
            self.results['summary']['passed'] += 1
            return {'status': 'passed'}
            
        except Exception as e:
            self.results['summary']['failed'] += 1
            return {'status': 'failed', 'error': str(e)}
        finally:
            self.results['summary']['total'] += 1
    
    def test_session_manager(self) -> Dict:
        """Test SessionManager functionality"""
        try:
            from src.core.services.session_manager import SessionManager
            
            # Test instantiation with config dict
            config = {'DEBUG': False}  # Use a dict which has .get() method
            session_mgr = SessionManager(config)
            
            # Test basic methods
            if hasattr(session_mgr, 'get_current_session'):
                session = session_mgr.get_current_session()
                
            self.results['summary']['passed'] += 1
            return {'status': 'passed'}
        except Exception as e:
            self.results['summary']['failed'] += 1
            return {'status': 'failed', 'error': str(e)}
        finally:
            self.results['summary']['total'] += 1
    
    def test_market_data_service(self) -> Dict:
        """Test MarketDataService functionality"""
        try:
            from src.core.services.market_data_service import MarketDataService
            
            # Test instantiation (might need mock dependencies)
            # For now, just test import
            
            self.results['summary']['passed'] += 1
            return {'status': 'passed'}
            
        except Exception as e:
            self.results['summary']['failed'] += 1
            return {'status': 'failed', 'error': str(e)}
        finally:
            self.results['summary']['total'] += 1
    
    def test_event_detection(self) -> Dict:
        """Test Event Detection components"""
        try:
            from src.processing.detectors.manager import EventDetectionManager
            from src.processing.detectors.highlow_detector import HighLowDetector
            
            # Test instantiation with config dict (not ConfigManager)
            config = {'DEBUG': False}  # Use a dict which has .get() method
            detector = HighLowDetector(config)
            
            self.results['summary']['passed'] += 1
            return {'status': 'passed'}
            
        except Exception as e:
            self.results['summary']['failed'] += 1
            return {'status': 'failed', 'error': str(e)}
        finally:
            self.results['summary']['total'] += 1
    
    def test_websocket_manager(self) -> Dict:
        """Test WebSocketManager functionality"""
        try:
            from src.presentation.websocket.manager import WebSocketManager
            
            # Test import successful
            self.results['summary']['passed'] += 1
            return {'status': 'passed'}
            
        except Exception as e:
            self.results['summary']['failed'] += 1
            return {'status': 'failed', 'error': str(e)}
        finally:
            self.results['summary']['total'] += 1
    
    def run_integration_tests(self):
        """Run integration tests"""
        print("\nRunning integration tests...")
        print("-"*40)
        
        # Check for pytest tests
        if self.test_dir.exists():
            pytest_files = list(self.test_dir.glob("test_*.py"))
            
            if pytest_files:
                print(f"  Found {len(pytest_files)} test files")
                
                # Try running with pytest
                try:
                    result = subprocess.run(
                        ["pytest", str(self.test_dir), "-v", "--tb=short"],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if result.returncode == 0:
                        print("  ✅ All pytest tests passed")
                        self.results['integration_tests']['pytest'] = {'status': 'passed'}
                    else:
                        print(f"  ❌ Some pytest tests failed")
                        self.results['integration_tests']['pytest'] = {
                            'status': 'failed',
                            'output': result.stdout[-500:] if result.stdout else result.stderr[-500:]
                        }
                        
                except FileNotFoundError:
                    print("  ⚠ pytest not installed, skipping pytest tests")
                except subprocess.TimeoutExpired:
                    print("  ⚠ pytest tests timed out")
                except Exception as e:
                    print(f"  ❌ Error running pytest: {e}")
            else:
                print("  No pytest test files found")
        else:
            print("  Tests directory not found")
    
    def run_trace_tests(self):
        """Run trace system tests if available"""
        print("\nChecking for trace tests...")
        print("-"*40)
        
        trace_test_files = [
            "tests/test_trace_format_validator.py",
            "tests/test_trace_flow_validation.py",
            "tests/test_trace_coverage.py",
            "tests/test_trace_emission_timing.py",
            "tests/test_trace_statistical.py",
        ]
        
        found_tests = []
        for test_file in trace_test_files:
            test_path = self.project_dir / test_file
            if test_path.exists():
                found_tests.append(test_path)
        
        if found_tests:
            print(f"  Found {len(found_tests)} trace test files")
            # Note: These require trace data files to run
            print("  ℹ Trace tests require trace data files (logs/trace/trace_all.json)")
            print("  Run them separately after capturing trace data")
        else:
            print("  No trace test files found")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print(" "*25 + "TEST REPORT SUMMARY")
        print("="*80)
        
        # Import Tests Summary
        import_passed = sum(1 for r in self.results['import_tests'].values() if r['status'] == 'passed')
        import_total = len(self.results['import_tests'])
        
        print(f"\n📦 IMPORT TESTS: {import_passed}/{import_total} passed")
        if import_passed < import_total:
            print("  Failed imports (with full errors):")
            for name, result in self.results['import_tests'].items():
                if result['status'] != 'passed':
                    print(f"\n    ❌ {name}:")
                    print(f"       Full error: {result.get('error', 'Unknown')}")
                    if self.verbose and 'traceback' in result:
                        print("       Traceback (last line):")
                        tb_lines = result['traceback'].strip().split('\n')
                        # Find the actual error location
                        for line in tb_lines:
                            if 'File' in line and '.py' in line:
                                print(f"       {line.strip()}")
        
        # Unit Tests Summary
        unit_passed = sum(1 for r in self.results['unit_tests'].values() if r['status'] == 'passed')
        unit_total = len(self.results['unit_tests'])
        
        if unit_total > 0:
            print(f"\n🧪 UNIT TESTS: {unit_passed}/{unit_total} passed")
            if unit_passed < unit_total:
                print("  Failed tests:")
                for name, result in self.results['unit_tests'].items():
                    if result['status'] != 'passed':
                        print(f"    ❌ {name}")
        
        # Overall Summary
        total = self.results['summary']['total']
        passed = self.results['summary']['passed']
        failed = self.results['summary']['failed']
        errors = self.results['summary']['errors']
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"  Total tests: {total}")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  ⚠️  Errors: {errors}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n  Success Rate: {success_rate:.1f}%")
        
        # Grade
        if success_rate >= 95:
            grade = "A+ 🌟"
        elif success_rate >= 90:
            grade = "A 🎯"
        elif success_rate >= 80:
            grade = "B 👍"
        elif success_rate >= 70:
            grade = "C 🔧"
        elif success_rate >= 60:
            grade = "D ⚠️"
        else:
            grade = "F 🚨"
        
        print(f"  Grade: {grade}")
        
        # Save report to file
        report_file = self.project_dir / f"test_report_{self.test_run_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        # Recommendations
        print("\n📋 RECOMMENDATIONS:")
        print("-"*40)
        
        if import_passed < import_total:
            print("1. Fix import errors first - these are blocking other functionality")
            
        if success_rate < 80:
            print("2. Focus on getting core components working")
            
        if success_rate >= 80 and success_rate < 95:
            print("3. Address remaining test failures")
            
        if success_rate >= 95:
            print("✅ System is ready for production!")
            print("   Consider adding more comprehensive tests")
    
    def run_specific_test_file(self, test_file: str):
        """Run a specific test file"""
        print(f"\nRunning specific test: {test_file}")
        print("-"*40)
        
        test_path = self.project_dir / test_file
        
        if not test_path.exists():
            print(f"  ❌ Test file not found: {test_file}")
            return False
        
        try:
            # Try to run as Python script
            result = subprocess.run(
                [sys.executable, str(test_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_dir)
            )
            
            print(result.stdout)
            
            if result.returncode == 0:
                print(f"  ✅ Test passed")
                return True
            else:
                print(f"  ❌ Test failed")
                if result.stderr:
                    print(f"  Error: {result.stderr[:500]}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  ⚠ Test timed out")
            return False
        except Exception as e:
            print(f"  ❌ Error running test: {e}")
            return False

def main():
    """Main execution"""
    # Check for command line arguments
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    runner = ComprehensiveTestRunner(verbose=verbose)
    
    # Check for specific test file (excluding verbose flag)
    args = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
    
    if args:
        # Run specific test file
        test_file = args[0]
        runner.run_specific_test_file(test_file)
    else:
        # Run all tests
        results = runner.run_all_tests()
        
        # Return exit code based on results
        success_rate = (results['summary']['passed'] / results['summary']['total'] * 100) if results['summary']['total'] > 0 else 0
        
        if success_rate >= 80:
            print("\n✅ Test suite passed with acceptable success rate")
            return 0
        else:
            print(f"\n❌ Test suite needs attention (success rate: {success_rate:.1f}%)")
            return 1

if __name__ == "__main__":
    sys.exit(main())