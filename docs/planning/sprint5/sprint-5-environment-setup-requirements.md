# Sprint 5: Environment & Setup Requirements

**Sprint:** Sprint 5 - Core Pattern Library & Event Publisher  
**Phase:** Pre-Sprint Setup (Complete Before Day 1)  
**Purpose:** Ensure development environment is ready for pattern library implementation  
**Last Updated:** 2025-08-25

## Overview

This document specifies the complete environment setup required before beginning Sprint 5 implementation. All requirements must be validated and working before Day 1 to avoid development delays.

## Core Environment Requirements

### Python Environment
- **Python Version:** 3.11+ (recommended: 3.11.5+)
- **Virtual Environment:** Required (venv, conda, or poetry)
- **Package Manager:** pip (with requirements.txt) or poetry

### Required Python Packages
```bash
# Core dependencies
pip install pandas>=2.0.0
pip install numpy>=1.24.0
pip install redis>=4.5.0
pip install pydantic>=2.0.0
pip install scipy>=1.10.0

# Development dependencies  
pip install pytest>=7.0.0
pip install pytest-cov>=4.0.0
pip install pytest-mock>=3.10.0
pip install pytest-asyncio>=0.21.0
pip install black>=23.0.0
pip install ruff>=0.0.270
pip install mypy>=1.3.0
```

### Redis Server Setup

#### Option 1: Local Redis Installation
```bash
# Windows (via Chocolatey)
choco install redis-64

# macOS (via Homebrew) 
brew install redis

# Linux (Ubuntu/Debian)
sudo apt-get install redis-server
```

#### Option 2: Docker Redis (Recommended for Development)
```bash
# Pull and run Redis container
docker pull redis:7-alpine
docker run --name tickstock-redis -p 6379:6379 -d redis:7-alpine

# Verify Redis is running
docker exec -it tickstock-redis redis-cli ping
# Expected output: PONG
```

### Redis Configuration Validation
Create `tests/setup_validation/test_redis_connection.py`:
```python
import redis
import pytest

def test_redis_connection():
    """Validate Redis server is accessible."""
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        assert True
    except redis.ConnectionError:
        pytest.fail("Redis server not accessible on localhost:6379")

def test_redis_pubsub():
    """Validate Redis pub-sub functionality."""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe('test_channel')
    
    # Test publish/subscribe
    r.publish('test_channel', 'test_message')
    message = pubsub.get_message(timeout=1.0)
    pubsub.unsubscribe('test_channel')
    
    assert message is not None
```

## Project Structure Validation

### Required Directory Structure
Ensure the following directories exist before Sprint 5:
```
TickStockPL/
├── src/
│   ├── patterns/          # Will be created in Sprint 5
│   ├── analysis/          # Will be created in Sprint 5  
│   ├── data/              # May exist from previous sprints
│   └── utils/             # May exist from previous sprints
├── tests/
│   ├── unit/
│   │   └── patterns/      # CREATE: Pattern-specific unit tests
│   ├── integration/
│   │   └── events/        # CREATE: Event integration tests
│   ├── fixtures/          # CREATE: Test data and utilities
│   └── setup_validation/  # CREATE: Environment validation tests
├── examples/              # CREATE: Demo scripts directory
└── docs/
    └── planning/          # Exists
```

### Create Missing Directories
```bash
# Run from TickStockPL root
mkdir -p src/patterns src/analysis 
mkdir -p tests/unit/patterns tests/integration/events tests/fixtures tests/setup_validation
mkdir -p examples
```

## Development Tools Setup

### IDE Configuration (VS Code Recommended)
Required VS Code extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance) 
- Black Formatter (ms-python.black-formatter)
- Ruff (charliermarsh.ruff)

### VS Code Settings (.vscode/settings.json)
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        "htmlcov": true
    }
}
```

### Linting Configuration (pyproject.toml)
```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "W", "C90", "I", "N", "B", "A", "C4", "EM", "ICN", "G", "PIE", "T20", "PYI", "PT", "Q", "RSE", "RET", "SLF", "SIM", "TID", "TCH", "ARG", "PTH", "ERA", "PD", "PGH", "PL", "TRY", "NPY", "RUF"]

[tool.ruff.per-file-ignores]
"tests/**/*.py" = ["PLR2004", "S101", "TID252"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Fast unit tests",
    "integration: Integration tests", 
    "slow: Tests that take > 1 second",
    "redis: Tests requiring Redis server"
]
addopts = [
    "-v",
    "--tb=short", 
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov"
]
```

## Performance Benchmarking Setup

### Benchmarking Tools
```bash
pip install pytest-benchmark>=4.0.0
pip install memory-profiler>=0.60.0
```

### Sample Benchmark Test Template
Create `tests/setup_validation/test_performance_baseline.py`:
```python
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for performance testing."""
    dates = pd.date_range(start='2025-01-01', end='2025-01-02', freq='1min')
    np.random.seed(42)
    
    data = []
    price = 150.0
    for date in dates:
        # Simple random walk for realistic price action
        change = np.random.normal(0, 0.1)
        price += change
        
        high = price + abs(np.random.normal(0, 0.05))
        low = price - abs(np.random.normal(0, 0.05))
        close = price + np.random.normal(0, 0.02)
        volume = np.random.randint(1000, 50000)
        
        data.append({
            'timestamp': date,
            'open': price,
            'high': high,
            'low': low, 
            'close': close,
            'volume': volume
        })
        price = close
        
    return pd.DataFrame(data)

def test_pandas_performance_baseline(benchmark, sample_ohlcv_data):
    """Benchmark baseline pandas operations for performance comparison."""
    def pandas_operations():
        df = sample_ohlcv_data.copy()
        # Simulate pattern detection operations
        df['body'] = abs(df['close'] - df['open'])
        df['range'] = df['high'] - df['low']
        df['ratio'] = df['body'] / df['range'].replace(0, 1)
        return df['ratio'].sum()
    
    result = benchmark(pandas_operations)
    assert result > 0
    # Benchmark should complete in < 50ms for ~1400 1min bars
    assert benchmark.stats['mean'] < 0.05
```

## Sample Data Setup

### Test Data Generation
Create `tests/fixtures/market_data.py`:
```python
"""Fixture data generators for Sprint 5 testing."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

def generate_doji_pattern_data(
    symbol: str = "AAPL", 
    timestamp: datetime = None,
    tolerance: float = 0.01
) -> Dict[str, Any]:
    """Generate OHLCV data with a clear Doji pattern."""
    if timestamp is None:
        timestamp = datetime.now()
    
    # Create Doji: open ≈ close, with high/low spread
    base_price = 150.0
    spread = 2.0
    
    return {
        'symbol': symbol,
        'timestamp': timestamp,
        'open': base_price,
        'high': base_price + spread,
        'low': base_price - spread,
        'close': base_price + (tolerance * spread * 0.5),  # Within tolerance
        'volume': 10000
    }

def generate_hammer_pattern_data(
    symbol: str = "AAPL",
    timestamp: datetime = None,
    shadow_ratio: float = 2.0
) -> Dict[str, Any]:
    """Generate OHLCV data with a clear Hammer pattern."""
    if timestamp is None:
        timestamp = datetime.now()
    
    base_price = 150.0
    body_size = 0.5
    lower_shadow = body_size * shadow_ratio
    
    return {
        'symbol': symbol,
        'timestamp': timestamp, 
        'open': base_price,
        'high': base_price + 0.1,  # Small upper shadow
        'low': base_price - lower_shadow,  # Long lower shadow
        'close': base_price + body_size,  # Bullish body
        'volume': 15000
    }

def generate_sample_ohlcv_series(
    symbol: str = "AAPL",
    start_date: datetime = None,
    periods: int = 100,
    freq: str = '1min'
) -> pd.DataFrame:
    """Generate realistic OHLCV time series data."""
    if start_date is None:
        start_date = datetime(2025, 8, 25, 9, 30)  # Market open
    
    timestamps = pd.date_range(start=start_date, periods=periods, freq=freq)
    np.random.seed(42)  # Reproducible data
    
    data = []
    price = 150.0
    
    for timestamp in timestamps:
        # Random walk with realistic constraints
        change_pct = np.random.normal(0, 0.001)  # 0.1% std deviation
        new_price = price * (1 + change_pct)
        
        # OHLC with realistic spread
        spread = abs(np.random.normal(0, 0.002)) * price
        open_price = price
        high_price = new_price + spread * np.random.uniform(0, 1)
        low_price = new_price - spread * np.random.uniform(0, 1) 
        close_price = new_price
        
        volume = np.random.randint(5000, 50000)
        
        data.append({
            'symbol': symbol,
            'timestamp': timestamp,
            'open': round(open_price, 2),
            'high': round(high_price, 2), 
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        
        price = close_price
    
    return pd.DataFrame(data)
```

## Environment Validation Checklist

### Pre-Sprint 5 Validation Script
Create `scripts/validate_sprint5_setup.py`:
```python
#!/usr/bin/env python3
"""Sprint 5 environment validation script."""
import sys
import importlib
import subprocess
from pathlib import Path

def check_python_version():
    """Verify Python 3.11+ is installed."""
    version = sys.version_info
    if version.major != 3 or version.minor < 11:
        print(f"❌ Python 3.11+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_required_packages():
    """Verify required packages are installed."""
    required = ['pandas', 'numpy', 'redis', 'pydantic', 'scipy', 'pytest']
    missing = []
    
    for package in required:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} - missing")
    
    return len(missing) == 0

def check_redis_connection():
    """Verify Redis server is accessible."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis server connection")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def check_directory_structure():
    """Verify required directories exist."""
    base_path = Path.cwd()
    required_dirs = [
        'src', 'tests/unit/patterns', 'tests/integration/events',
        'tests/fixtures', 'examples'
    ]
    
    missing = []
    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if not full_path.exists():
            missing.append(dir_path)
            print(f"❌ Missing directory: {dir_path}")
        else:
            print(f"✅ Directory exists: {dir_path}")
    
    return len(missing) == 0

def main():
    """Run complete environment validation."""
    print("Sprint 5 Environment Validation")
    print("=" * 40)
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", check_required_packages), 
        ("Redis Connection", check_redis_connection),
        ("Directory Structure", check_directory_structure)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        results.append(check_func())
    
    print("\n" + "=" * 40)
    if all(results):
        print("✅ Sprint 5 environment setup complete!")
        print("Ready to begin Sprint 5 implementation.")
        sys.exit(0)
    else:
        print("❌ Environment setup incomplete.")
        print("Please resolve issues before starting Sprint 5.")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Setup Completion Steps

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Create missing directories
mkdir -p src/patterns src/analysis tests/unit/patterns tests/integration/events tests/fixtures examples
```

### 2. Redis Setup Validation
```bash
# Test Redis connection
python -c "import redis; r=redis.Redis(); print('Redis OK' if r.ping() else 'Redis Failed')"
```

### 3. Run Environment Validation
```bash
python scripts/validate_sprint5_setup.py
```

### 4. Initial Test Run
```bash
# Run setup validation tests
pytest tests/setup_validation/ -v

# Run performance baseline
pytest tests/setup_validation/test_performance_baseline.py --benchmark-only
```

## Success Criteria

**Sprint 5 environment is ready when:**
- ✅ All validation checks pass (`validate_sprint5_setup.py`)
- ✅ Redis pub-sub functionality tested and working
- ✅ Performance baseline established (<50ms for pattern detection)
- ✅ Directory structure created and validated
- ✅ Development tools configured and tested
- ✅ Sample data generation working

**Estimated Setup Time:** 2-4 hours

## Troubleshooting

### Common Issues

**Redis Connection Failed:**
```bash
# Check if Redis is running
redis-cli ping

# Start Redis service (Linux)
sudo systemctl start redis

# Start Redis Docker container
docker start tickstock-redis
```

**Package Installation Issues:**
```bash
# Upgrade pip first
pip install --upgrade pip

# Install with specific versions if conflicts
pip install pandas==2.0.3 numpy==1.24.3
```

**Permission Issues:**
```bash
# Ensure proper directory permissions
chmod -R 755 src/ tests/ examples/
```

This environment setup ensures Sprint 5 can begin immediately with all required tools, dependencies, and validation frameworks in place.