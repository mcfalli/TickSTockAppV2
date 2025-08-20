"""
Test runner for channel infrastructure tests.

Executes comprehensive test suite for Sprint 105 channel infrastructure
with coverage reporting and performance metrics.

Sprint 105: Core Channel Infrastructure Testing
"""

import sys
import os
import subprocess
import time
from pathlib import Path


def run_tests():
    """Run comprehensive channel infrastructure tests"""
    
    # Add src to path
    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    
    print("🚀 Running Sprint 105 Channel Infrastructure Tests")
    print("=" * 60)
    
    # Test configurations
    test_configs = [
        {
            "name": "Unit Tests - Base Channel",
            "path": "tests/unit/processing/channels/test_base_channel.py",
            "markers": "-m unit"
        },
        {
            "name": "Unit Tests - Channel Metrics", 
            "path": "tests/unit/processing/channels/test_channel_metrics.py",
            "markers": "-m unit"
        },
        {
            "name": "Unit Tests - Channel Config",
            "path": "tests/unit/processing/channels/test_channel_config.py", 
            "markers": "-m unit"
        },
        {
            "name": "Unit Tests - Channel Router",
            "path": "tests/unit/processing/channels/test_channel_router.py",
            "markers": "-m unit"
        },
        {
            "name": "Unit Tests - Tick Channel",
            "path": "tests/unit/processing/channels/test_tick_channel.py",
            "markers": "-m unit"
        },
        {
            "name": "Integration Tests - Multi-Channel",
            "path": "tests/integration/channels/test_multi_channel_integration.py",
            "markers": "-m integration"
        }
    ]
    
    # Performance test configuration
    performance_config = {
        "name": "Performance Tests - All Channels",
        "path": "tests/unit/processing/channels/",
        "markers": "-m performance"
    }
    
    results = {}
    total_start_time = time.time()
    
    # Run each test configuration
    for config in test_configs:
        print(f"\n🧪 {config['name']}")
        print("-" * 40)
        
        start_time = time.time()
        
        # Build pytest command
        cmd = [
            "python", "-m", "pytest",
            config["path"],
            config["markers"],
            "-v",
            "--tb=short",
            "--disable-warnings"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            elapsed_time = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ PASSED ({elapsed_time:.2f}s)")
                results[config["name"]] = "PASSED"
            else:
                print(f"❌ FAILED ({elapsed_time:.2f}s)")
                print(f"Error: {result.stderr}")
                results[config["name"]] = "FAILED"
                
        except subprocess.TimeoutExpired:
            print("⏰ TIMEOUT (>5 minutes)")
            results[config["name"]] = "TIMEOUT"
        except Exception as e:
            print(f"💥 ERROR: {e}")
            results[config["name"]] = "ERROR"
    
    # Run performance tests separately
    print(f"\n🏃‍♂️ {performance_config['name']}")
    print("-" * 40)
    
    perf_start_time = time.time()
    
    cmd = [
        "python", "-m", "pytest",
        performance_config["path"],
        performance_config["markers"], 
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for performance tests
        )
        
        elapsed_time = time.time() - perf_start_time
        
        if result.returncode == 0:
            print(f"✅ PASSED ({elapsed_time:.2f}s)")
            results[performance_config["name"]] = "PASSED"
        else:
            print(f"❌ FAILED ({elapsed_time:.2f}s)")
            results[performance_config["name"]] = "FAILED"
            
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT (>10 minutes)")
        results[performance_config["name"]] = "TIMEOUT"
    except Exception as e:
        print(f"💥 ERROR: {e}")
        results[performance_config["name"]] = "ERROR"
    
    # Summary
    total_elapsed = time.time() - total_start_time
    
    print(f"\n📊 Test Summary")
    print("=" * 60)
    
    passed_count = sum(1 for status in results.values() if status == "PASSED")
    total_count = len(results)
    
    for test_name, status in results.items():
        status_emoji = {
            "PASSED": "✅",
            "FAILED": "❌", 
            "TIMEOUT": "⏰",
            "ERROR": "💥"
        }.get(status, "❓")
        
        print(f"{status_emoji} {test_name}: {status}")
    
    print(f"\n📈 Overall Results:")
    print(f"   Passed: {passed_count}/{total_count}")
    print(f"   Success Rate: {(passed_count/total_count)*100:.1f}%")
    print(f"   Total Time: {total_elapsed:.2f}s")
    
    # Coverage report (if available)
    print(f"\n📋 Running Coverage Report...")
    print("-" * 40)
    
    coverage_cmd = [
        "python", "-m", "pytest",
        "tests/unit/processing/channels/",
        "--cov=src.processing.channels",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/channels",
        "-q"
    ]
    
    try:
        result = subprocess.run(
            coverage_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            print("✅ Coverage report generated")
            print(f"📁 HTML report: htmlcov/channels/index.html")
            
            # Extract coverage percentage from output
            if "TOTAL" in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "TOTAL" in line:
                        print(f"📊 {line}")
                        break
        else:
            print("❌ Coverage report failed")
            
    except Exception as e:
        print(f"💥 Coverage error: {e}")
    
    print(f"\n🎯 Sprint 105 Channel Infrastructure Testing Complete!")
    
    # Return exit code based on results
    if passed_count == total_count:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - see results above")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)