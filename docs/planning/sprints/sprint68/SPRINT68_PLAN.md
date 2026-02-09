# Sprint 68 - Core Analysis Migration: Indicators & Patterns

**Status**: Planning
**Priority**: P1 (Critical)
**Type**: Architecture Migration
**Dependencies**: None
**Duration**: 3 weeks (15 working days)
**Effort**: HIGH

---

## Sprint Goal

Migrate pattern detection and indicator calculation capabilities from TickStockPL to TickStockAppV2, enabling pattern detection to run locally within the unified application without Redis pub-sub dependencies.

**Success Definition**: AppV2 can independently detect patterns and calculate indicators with results matching TickStockPL's output (regression validation).

---

## Why This Sprint

### Current Pain Points
1. **Pattern Detection Disabled**: Core platform feature inactive, blocking user value
2. **Two-Codebase Overhead**: 30-40% slower development due to context switching
3. **Redis Debugging Complexity**: Pattern flow issues require tracing across two systems
4. **Development Stagnation**: Pattern library not actively developed

### Value Delivered
- ✅ Pattern detection re-enabled in AppV2
- ✅ Single codebase for pattern/indicator development
- ✅ Direct function calls (no Redis overhead)
- ✅ Simplified debugging (no cross-system tracing)
- ✅ Foundation for Sprint 69 (background jobs)

---

## Architecture Vision

### Before Sprint 68
```
TickStockPL (Producer)
├── Pattern Detection (20+ patterns)
├── Indicator Calculation (15+ indicators)
├── Analysis Engines (dynamic loading)
└── Redis Publishing → AppV2 consumes

TickStockAppV2 (Consumer)
├── UI Dashboards
├── Redis Pattern Consumer
└── Fallback Patterns (3 basic only)
```

### After Sprint 68
```
TickStockAppV2 (Unified)
├── UI Dashboards
├── Pattern Detection (20+ patterns) ✨ NEW
├── Indicator Calculation (15+ indicators) ✨ NEW
├── Analysis Engines (dynamic loading) ✨ NEW
└── Pattern/Indicator Services ✨ NEW

TickStockPL (Data Loading Only)
├── Historical Data Loading
├── Job Queue Handler
└── Redis Job Status
```

---

## Deliverables

### Phase 1: Indicator Migration (Week 1)

**Files to Migrate** (3,771 lines):
```
TickStockPL/src/indicators/
├── rsi.py (147 lines)
├── macd.py (189 lines)
├── sma.py (92 lines)
├── ema.py (103 lines)
├── stochastic.py (176 lines)
├── bollinger_bands.py (154 lines)
├── atr.py (128 lines)
├── adx.py (198 lines)
├── obv.py (87 lines)
├── volume_sma.py (94 lines)
├── relative_volume.py (112 lines)
├── vwap.py (134 lines)
├── momentum.py (89 lines)
├── roc.py (95 lines)
└── williams_r.py (142 lines)

→ Migrate to:
TickStockAppV2/src/analysis/indicators/
```

**New Files to Create**:
1. `src/analysis/indicators/__init__.py` - Package initialization
2. `src/core/services/indicator_service.py` - Indicator orchestration service
3. `src/core/models/indicator_models.py` - Pydantic models for indicators
4. `tests/analysis/indicators/test_*.py` - Unit tests for each indicator

**Database Access**:
- Read: `indicator_definitions` table (configuration)
- Write: `indicator_results` table (calculation results)
- Write: `indicator_calculation_runs` table (job metadata)

**Dependencies**:
- pandas (already in AppV2)
- NumPy (already in AppV2)
- TA-Lib (add to requirements.txt)

---

### Phase 2: Pattern Migration (Week 2)

**Files to Migrate** (7,287 lines):
```
TickStockPL/src/patterns/
├── candlestick/
│   ├── doji.py (156 lines)
│   ├── hammer.py (178 lines)
│   ├── shooting_star.py (165 lines)
│   ├── engulfing.py (198 lines)
│   ├── harami.py (187 lines)
│   ├── morning_star.py (234 lines)
│   └── evening_star.py (228 lines)
├── daily/
│   ├── head_shoulders.py (412 lines)
│   ├── double_top.py (298 lines)
│   ├── double_bottom.py (287 lines)
│   ├── triangle.py (356 lines)
│   ├── channel.py (398 lines)
│   ├── cup_handle.py (289 lines)
│   └── flag.py (267 lines)
└── combo/
    ├── breakout_volume.py (345 lines)
    ├── macd_divergence.py (378 lines)
    ├── rsi_reversal.py (312 lines)
    └── volume_surge_pattern.py (298 lines)

→ Migrate to:
TickStockAppV2/src/analysis/patterns/
```

**New Files to Create**:
1. `src/analysis/patterns/__init__.py` - Package initialization
2. `src/core/services/pattern_service.py` - Pattern orchestration service
3. `src/core/models/pattern_models.py` - Pydantic models for patterns
4. `tests/analysis/patterns/test_*.py` - Unit tests for each pattern

**Database Access**:
- Read: `pattern_definitions` table (configuration)
- Read: `indicator_results` table (patterns depend on indicators)
- Write: `daily_patterns` table (detection results)
- Write: `pattern_detection_runs` table (job metadata)

**Dependencies**:
- Indicators (from Phase 1)
- SciPy (already in AppV2)
- scikit-learn (add if needed for advanced patterns)

---

### Phase 3: Analysis Engine Migration (Week 3)

**Files to Migrate** (6,427 lines):
```
TickStockPL/src/analysis/
├── dynamic_loader.py (487 lines)
├── pattern_detection_engine.py (892 lines)
├── indicator_calculation_engine.py (756 lines)
├── daily_pattern_engine.py (678 lines)
├── intraday_pattern_engine.py (589 lines)
├── combo_pattern_engine.py (734 lines)
├── events.py (298 lines)
├── realtime_events.py (312 lines)
└── scanner.py (681 lines)

→ Migrate to:
TickStockAppV2/src/analysis/engines/
```

**New Files to Create**:
1. `src/analysis/engines/__init__.py` - Package initialization
2. `src/analysis/engines/base_engine.py` - Abstract base engine class
3. `src/core/services/analysis_service.py` - Unified analysis orchestration
4. `tests/analysis/engines/test_*.py` - Engine unit tests

**Key Adaptations**:
- Remove TickStockPL-specific Redis publishing
- Add internal AppV2 event system (Flask signals or internal pub-sub)
- Integrate with AppV2's database layer
- Update configuration loading (use AppV2's config system)

---

## Detailed Task Breakdown

### Week 1: Indicator Migration (Days 1-5)

#### Day 1: Foundation Setup

**Task 1.1: Create Directory Structure**
```bash
mkdir -p src/analysis/indicators
mkdir -p src/analysis/patterns
mkdir -p src/analysis/engines
mkdir -p tests/analysis/indicators
mkdir -p tests/analysis/patterns
mkdir -p tests/analysis/engines
```

**Task 1.2: Add Dependencies**
```python
# Update requirements.txt
TA-Lib==0.4.28
scikit-learn==1.3.2  # For advanced pattern recognition
```

**Task 1.3: Create Base Indicator Class**
```python
# src/analysis/indicators/base_indicator.py
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd

class BaseIndicator(ABC):
    """Base class for all indicators following TickStockPL convention."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate indicator. MUST return {'value': primary, 'value_data': {...}}"""
        pass

    @abstractmethod
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate input data has required columns and sufficient rows."""
        pass
```

**Deliverable**: ✅ Directory structure, dependencies, base classes

---

#### Day 2-3: Copy Indicator Files

**Task 2.1: Copy 15 Indicator Files**
```bash
# Copy from TickStockPL to AppV2
cp C:/Users/McDude/TickStockPL/src/indicators/*.py \
   C:/Users/McDude/TickStockAppV2/src/analysis/indicators/
```

**Task 2.2: Update Imports in Each File**

Example for `rsi.py`:
```python
# OLD (TickStockPL)
from src.indicators.base import BaseIndicator
from src.database.connection import get_db_connection

# NEW (TickStockAppV2)
from src.analysis.indicators.base_indicator import BaseIndicator
from src.infrastructure.database.tickstock_db import TickStockDatabase
```

**Task 2.3: Verify Indicator Convention**

Each indicator MUST return:
```python
{
    'value': <primary_value>,  # e.g., current RSI value
    'value_data': {            # e.g., {'rsi': 65.4, 'overbought': True}
        'key1': value1,
        'key2': value2
    }
}
```

**Files to Update** (15 indicators):
1. `rsi.py` - RSI indicator
2. `macd.py` - MACD indicator
3. `sma.py` - Simple Moving Average
4. `ema.py` - Exponential Moving Average
5. `stochastic.py` - Stochastic Oscillator
6. `bollinger_bands.py` - Bollinger Bands
7. `atr.py` - Average True Range
8. `adx.py` - Average Directional Index
9. `obv.py` - On-Balance Volume
10. `volume_sma.py` - Volume SMA
11. `relative_volume.py` - Relative Volume
12. `vwap.py` - VWAP
13. `momentum.py` - Momentum
14. `roc.py` - Rate of Change
15. `williams_r.py` - Williams %R

**Deliverable**: ✅ 15 indicator files migrated and imports updated

---

#### Day 4: Create Indicator Service

**Task 3.1: Create IndicatorService**
```python
# src/core/services/indicator_service.py
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from src.analysis.indicators.dynamic_loader import load_indicator
from src.infrastructure.database.tickstock_db import TickStockDatabase

class IndicatorService:
    """Service for calculating technical indicators."""

    def __init__(self):
        self.db = TickStockDatabase()

    def calculate_indicator(
        self,
        symbol: str,
        indicator_name: str,
        df: pd.DataFrame,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Calculate single indicator for symbol."""
        # 1. Load indicator class dynamically
        indicator_class = load_indicator(indicator_name)
        indicator = indicator_class(config)

        # 2. Validate data
        if not indicator.validate_data(df):
            raise ValueError(f"Insufficient data for {indicator_name}")

        # 3. Calculate
        result = indicator.calculate(df)

        # 4. Store result
        self._store_result(symbol, indicator_name, result)

        return result

    def calculate_all_indicators(
        self,
        symbol: str,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate all enabled indicators for symbol."""
        # Load enabled indicators from database
        enabled_indicators = self._get_enabled_indicators()

        results = {}
        for indicator_def in enabled_indicators:
            try:
                result = self.calculate_indicator(
                    symbol,
                    indicator_def['name'],
                    df,
                    indicator_def.get('config')
                )
                results[indicator_def['name']] = result
            except Exception as e:
                logger.error(f"Error calculating {indicator_def['name']}: {e}")
                results[indicator_def['name']] = {'error': str(e)}

        return results

    def _get_enabled_indicators(self) -> List[Dict[str, Any]]:
        """Load enabled indicators from database."""
        with self.db.get_connection() as conn:
            query = """
                SELECT name, config, parameters
                FROM indicator_definitions
                WHERE enabled = true
                ORDER BY execution_order
            """
            return conn.execute(query).fetchall()

    def _store_result(
        self,
        symbol: str,
        indicator_name: str,
        result: Dict[str, Any]
    ):
        """Store indicator result to database."""
        with self.db.get_connection() as conn:
            query = """
                INSERT INTO indicator_results (
                    symbol, indicator_name, value, value_data, calculated_at
                )
                VALUES (:symbol, :indicator_name, :value, :value_data, :calculated_at)
            """
            conn.execute(query, {
                'symbol': symbol,
                'indicator_name': indicator_name,
                'value': result.get('value'),
                'value_data': result.get('value_data'),
                'calculated_at': datetime.utcnow()
            })
```

**Task 3.2: Create Dynamic Loader**
```python
# src/analysis/indicators/dynamic_loader.py
import importlib
from typing import Type
from src.analysis.indicators.base_indicator import BaseIndicator

def load_indicator(indicator_name: str) -> Type[BaseIndicator]:
    """Dynamically load indicator class by name (NO FALLBACK)."""
    try:
        module = importlib.import_module(
            f'src.analysis.indicators.{indicator_name.lower()}'
        )
        # Class name convention: RSI, MACD, SMA, etc.
        class_name = indicator_name.upper()
        indicator_class = getattr(module, class_name)

        if not issubclass(indicator_class, BaseIndicator):
            raise TypeError(f"{class_name} must inherit from BaseIndicator")

        return indicator_class

    except (ImportError, AttributeError) as e:
        # NO FALLBACK - Fail fast if indicator not found
        raise ImportError(
            f"Indicator '{indicator_name}' not found. "
            f"Ensure it's registered in indicator_definitions table. "
            f"Error: {e}"
        )
```

**Deliverable**: ✅ IndicatorService and dynamic loader created

---

#### Day 5: Indicator Testing

**Task 4.1: Create Indicator Unit Tests**
```python
# tests/analysis/indicators/test_rsi.py
import pytest
import pandas as pd
from src.analysis.indicators.rsi import RSI

class TestRSI:
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'date': dates,
            'close': [100 + i * 0.5 for i in range(100)]
        })

    def test_rsi_calculation(self, sample_data):
        """Test RSI calculates correctly."""
        rsi = RSI(config={'period': 14})
        result = rsi.calculate(sample_data)

        assert 'value' in result
        assert 'value_data' in result
        assert 0 <= result['value'] <= 100
        assert 'rsi' in result['value_data']

    def test_rsi_overbought(self, sample_data):
        """Test RSI detects overbought conditions."""
        # Create strongly uptrending data
        sample_data['close'] = [100 + i * 2 for i in range(100)]

        rsi = RSI(config={'period': 14})
        result = rsi.calculate(sample_data)

        assert result['value'] > 70  # Overbought threshold
        assert result['value_data']['overbought'] == True

    def test_insufficient_data(self):
        """Test RSI rejects insufficient data."""
        df = pd.DataFrame({'close': [100, 101, 102]})  # Only 3 rows

        rsi = RSI(config={'period': 14})
        assert not rsi.validate_data(df)
```

**Task 4.2: Run Unit Tests**
```bash
pytest tests/analysis/indicators/ -v --cov=src/analysis/indicators
```

**Task 4.3: Integration Test with Database**
```python
# tests/analysis/indicators/test_indicator_service_integration.py
import pytest
from src.core.services.indicator_service import IndicatorService
from src.infrastructure.database.tickstock_db import TickStockDatabase

@pytest.mark.integration
class TestIndicatorServiceIntegration:
    def test_calculate_rsi_stores_result(self):
        """Test RSI calculation stores result in database."""
        service = IndicatorService()

        # Load OHLCV data for AAPL
        df = self._load_test_data('AAPL')

        # Calculate RSI
        result = service.calculate_indicator('AAPL', 'RSI', df)

        # Verify result stored
        with TickStockDatabase().get_connection() as conn:
            query = """
                SELECT value, value_data
                FROM indicator_results
                WHERE symbol = 'AAPL' AND indicator_name = 'RSI'
                ORDER BY calculated_at DESC
                LIMIT 1
            """
            row = conn.execute(query).fetchone()
            assert row is not None
            assert row['value'] == result['value']
```

**Task 4.4: Regression Testing vs TickStockPL**
```python
# tests/analysis/indicators/test_regression.py
import pytest
from src.core.services.indicator_service import IndicatorService
# Import TickStockPL's indicator for comparison
import sys
sys.path.append('C:/Users/McDude/TickStockPL')
from src.indicators.rsi import RSI as PL_RSI

@pytest.mark.regression
class TestIndicatorRegression:
    def test_rsi_matches_tickstockpl(self):
        """Verify AppV2's RSI matches TickStockPL's output."""
        df = self._load_test_data('AAPL')

        # Calculate with AppV2
        appv2_service = IndicatorService()
        appv2_result = appv2_service.calculate_indicator('AAPL', 'RSI', df)

        # Calculate with TickStockPL
        pl_indicator = PL_RSI(config={'period': 14})
        pl_result = pl_indicator.calculate(df)

        # Results must match within floating-point precision
        assert abs(appv2_result['value'] - pl_result['value']) < 0.01
```

**Deliverable**: ✅ Indicators tested and regression validated

---

### Week 2: Pattern Migration (Days 6-10)

#### Day 6: Copy Pattern Files

**Task 5.1: Copy Pattern Files**
```bash
# Copy from TickStockPL to AppV2
cp -r C:/Users/McDude/TickStockPL/src/patterns/* \
      C:/Users/McDude/TickStockAppV2/src/analysis/patterns/
```

**Task 5.2: Create Base Pattern Class**
```python
# src/analysis/patterns/base_pattern.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

class BasePattern(ABC):
    """Base class for all patterns following TickStockPL convention."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self.min_bars = self.config.get('min_bars', 5)

    @abstractmethod
    def detect(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect pattern in data.

        Returns:
            {
                'detected': True/False,
                'confidence': 0.0-1.0,
                'details': {...},
                'entry_price': float,
                'stop_loss': float,
                'target_price': float
            }
        """
        pass

    @abstractmethod
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate input data has required columns and sufficient rows."""
        pass

    def requires_indicators(self) -> List[str]:
        """List of indicator names this pattern depends on."""
        return []
```

**Task 5.3: Update Pattern Imports**

Update all 20+ pattern files to use AppV2 imports:
```python
# OLD
from src.patterns.base import BasePattern
from src.indicators import get_indicator_result

# NEW
from src.analysis.patterns.base_pattern import BasePattern
from src.core.services.indicator_service import IndicatorService
```

**Deliverable**: ✅ Pattern files copied and base class created

---

#### Day 7-8: Create Pattern Service

**Task 6.1: Create PatternService**
```python
# src/core/services/pattern_service.py
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from src.analysis.patterns.dynamic_loader import load_pattern
from src.core.services.indicator_service import IndicatorService
from src.infrastructure.database.tickstock_db import TickStockDatabase

class PatternService:
    """Service for detecting technical patterns."""

    def __init__(self):
        self.db = TickStockDatabase()
        self.indicator_service = IndicatorService()

    def detect_pattern(
        self,
        symbol: str,
        pattern_name: str,
        df: pd.DataFrame,
        config: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Detect single pattern for symbol."""
        # 1. Load pattern class dynamically
        pattern_class = load_pattern(pattern_name)
        pattern = pattern_class(config)

        # 2. Validate data
        if not pattern.validate_data(df):
            return None

        # 3. Load required indicators
        indicators = {}
        for indicator_name in pattern.requires_indicators():
            indicators[indicator_name] = self._get_latest_indicator(
                symbol, indicator_name
            )

        # 4. Detect pattern
        result = pattern.detect(df, indicators)

        # 5. Store if detected
        if result and result.get('detected'):
            self._store_result(symbol, pattern_name, result)

        return result

    def detect_all_patterns(
        self,
        symbol: str,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Detect all enabled patterns for symbol."""
        enabled_patterns = self._get_enabled_patterns()

        results = {}
        for pattern_def in enabled_patterns:
            try:
                result = self.detect_pattern(
                    symbol,
                    pattern_def['name'],
                    df,
                    pattern_def.get('config')
                )
                if result:
                    results[pattern_def['name']] = result
            except Exception as e:
                logger.error(f"Error detecting {pattern_def['name']}: {e}")

        return results

    def _get_enabled_patterns(self) -> List[Dict[str, Any]]:
        """Load enabled patterns from database."""
        with self.db.get_connection() as conn:
            query = """
                SELECT name, config, parameters, min_bars
                FROM pattern_definitions
                WHERE enabled = true
                ORDER BY execution_order
            """
            return conn.execute(query).fetchall()

    def _get_latest_indicator(
        self,
        symbol: str,
        indicator_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get latest indicator result for symbol."""
        with self.db.get_connection() as conn:
            query = """
                SELECT value, value_data
                FROM indicator_results
                WHERE symbol = :symbol AND indicator_name = :indicator_name
                ORDER BY calculated_at DESC
                LIMIT 1
            """
            row = conn.execute(query, {
                'symbol': symbol,
                'indicator_name': indicator_name
            }).fetchone()

            if row:
                return {
                    'value': row['value'],
                    'value_data': row['value_data']
                }
            return None

    def _store_result(
        self,
        symbol: str,
        pattern_name: str,
        result: Dict[str, Any]
    ):
        """Store pattern detection result to database."""
        with self.db.get_connection() as conn:
            query = """
                INSERT INTO daily_patterns (
                    symbol, pattern_name, confidence, details,
                    entry_price, stop_loss, target_price, detected_at
                )
                VALUES (
                    :symbol, :pattern_name, :confidence, :details,
                    :entry_price, :stop_loss, :target_price, :detected_at
                )
            """
            conn.execute(query, {
                'symbol': symbol,
                'pattern_name': pattern_name,
                'confidence': result.get('confidence'),
                'details': result.get('details'),
                'entry_price': result.get('entry_price'),
                'stop_loss': result.get('stop_loss'),
                'target_price': result.get('target_price'),
                'detected_at': datetime.utcnow()
            })
```

**Task 6.2: Create Pattern Dynamic Loader**
```python
# src/analysis/patterns/dynamic_loader.py
import importlib
from typing import Type
from src.analysis.patterns.base_pattern import BasePattern

def load_pattern(pattern_name: str) -> Type[BasePattern]:
    """Dynamically load pattern class by name (NO FALLBACK)."""
    try:
        # Determine subdirectory (candlestick, daily, combo)
        pattern_type = _determine_pattern_type(pattern_name)

        module_path = f'src.analysis.patterns.{pattern_type}.{pattern_name.lower()}'
        module = importlib.import_module(module_path)

        # Class name convention: Doji, Hammer, HeadShoulders, etc.
        class_name = _to_class_name(pattern_name)
        pattern_class = getattr(module, class_name)

        if not issubclass(pattern_class, BasePattern):
            raise TypeError(f"{class_name} must inherit from BasePattern")

        return pattern_class

    except (ImportError, AttributeError) as e:
        # NO FALLBACK - Fail fast if pattern not found
        raise ImportError(
            f"Pattern '{pattern_name}' not found. "
            f"Ensure it's registered in pattern_definitions table. "
            f"Error: {e}"
        )

def _determine_pattern_type(pattern_name: str) -> str:
    """Determine pattern subdirectory based on name."""
    candlestick_patterns = [
        'doji', 'hammer', 'shooting_star', 'engulfing',
        'harami', 'morning_star', 'evening_star'
    ]
    combo_patterns = [
        'breakout_volume', 'macd_divergence',
        'rsi_reversal', 'volume_surge_pattern'
    ]

    if pattern_name.lower() in candlestick_patterns:
        return 'candlestick'
    elif pattern_name.lower() in combo_patterns:
        return 'combo'
    else:
        return 'daily'

def _to_class_name(pattern_name: str) -> str:
    """Convert pattern_name to ClassName convention."""
    # doji -> Doji
    # head_shoulders -> HeadShoulders
    return ''.join(word.capitalize() for word in pattern_name.split('_'))
```

**Deliverable**: ✅ PatternService and dynamic loader created

---

#### Day 9-10: Pattern Testing

**Task 7.1: Create Pattern Unit Tests**
```python
# tests/analysis/patterns/test_doji.py
import pytest
import pandas as pd
from src.analysis.patterns.candlestick.doji import Doji

class TestDoji:
    @pytest.fixture
    def doji_data(self):
        """Create sample data with doji pattern."""
        return pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'open': [100, 101, 102, 103, 104, 105, 104, 103, 102, 101],
            'high': [101, 102, 103, 104, 105, 106, 105, 104, 103, 102],
            'low': [99, 100, 101, 102, 103, 104, 103, 102, 101, 100],
            'close': [100.1, 101, 102, 103, 104, 105, 104.1, 103, 102, 101],  # Last bar is doji
            'volume': [1000000] * 10
        })

    def test_doji_detection(self, doji_data):
        """Test doji pattern detection."""
        doji = Doji()
        result = doji.detect(doji_data)

        assert result is not None
        assert result['detected'] == True
        assert 0.6 <= result['confidence'] <= 1.0
        assert 'doji_type' in result['details']

    def test_no_doji(self):
        """Test doji not detected in strong trending data."""
        df = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [99, 100, 101, 102, 103],
            'close': [104, 105, 106, 107, 108],  # Strong uptrend, no doji
            'volume': [1000000] * 5
        })

        doji = Doji()
        result = doji.detect(df)

        assert result is None or result['detected'] == False
```

**Task 7.2: Integration Test with Indicators**
```python
# tests/analysis/patterns/test_pattern_service_integration.py
import pytest
from src.core.services.pattern_service import PatternService
from src.core.services.indicator_service import IndicatorService

@pytest.mark.integration
class TestPatternServiceIntegration:
    def test_rsi_reversal_pattern_with_indicator(self):
        """Test RSI Reversal pattern uses indicator results."""
        # 1. Calculate RSI first
        indicator_service = IndicatorService()
        df = self._load_test_data('AAPL')
        indicator_service.calculate_indicator('AAPL', 'RSI', df)

        # 2. Detect RSI Reversal pattern
        pattern_service = PatternService()
        result = pattern_service.detect_pattern('AAPL', 'RSI_Reversal', df)

        # 3. Verify pattern used indicator
        assert result is not None
        assert 'rsi_value' in result['details']
```

**Task 7.3: Regression Testing**
```bash
pytest tests/analysis/patterns/ -v --cov=src/analysis/patterns -m regression
```

**Deliverable**: ✅ Patterns tested and regression validated

---

### Week 3: Analysis Engine Migration (Days 11-15)

#### Day 11-12: Copy Analysis Engines

**Task 8.1: Copy Engine Files**
```bash
cp C:/Users/McDude/TickStockPL/src/analysis/dynamic_loader.py \
   C:/Users/McDude/TickStockAppV2/src/analysis/engines/

cp C:/Users/McDude/TickStockPL/src/analysis/*_engine.py \
   C:/Users/McDude/TickStockAppV2/src/analysis/engines/
```

**Files to Migrate**:
1. `dynamic_loader.py` (487 lines) - Already ported in indicators/patterns
2. `pattern_detection_engine.py` (892 lines) - Orchestrates pattern detection
3. `indicator_calculation_engine.py` (756 lines) - Orchestrates indicator calculation
4. `daily_pattern_engine.py` (678 lines) - Daily timeframe patterns
5. `combo_pattern_engine.py` (734 lines) - Combo pattern detection

**Task 8.2: Remove TickStockPL Redis Dependencies**

Update all engines to use internal AppV2 events:
```python
# OLD (TickStockPL)
from src.infrastructure.messaging.redis_client import RedisClient
redis_client.publish('tickstock.events.patterns', pattern_data)

# NEW (AppV2)
from flask import current_app
from src.core.events.internal_events import publish_pattern_event
publish_pattern_event(pattern_data)  # Internal to AppV2
```

**Task 8.3: Integrate with AppV2 Services**
```python
# Update pattern_detection_engine.py to use AppV2 services
from src.core.services.indicator_service import IndicatorService
from src.core.services.pattern_service import PatternService

class PatternDetectionEngine:
    def __init__(self):
        self.indicator_service = IndicatorService()
        self.pattern_service = PatternService()

    def detect_patterns_for_symbol(self, symbol: str, df: pd.DataFrame):
        # Use AppV2 services instead of TickStockPL's database layer
        indicators = self.indicator_service.calculate_all_indicators(symbol, df)
        patterns = self.pattern_service.detect_all_patterns(symbol, df)
        return patterns
```

**Deliverable**: ✅ Analysis engines migrated and adapted

---

#### Day 13: Create Unified Analysis Service

**Task 9.1: Create AnalysisService**
```python
# src/core/services/analysis_service.py
from typing import List, Dict, Any
import pandas as pd
from src.core.services.indicator_service import IndicatorService
from src.core.services.pattern_service import PatternService
from src.analysis.engines.pattern_detection_engine import PatternDetectionEngine
from src.infrastructure.database.tickstock_db import TickStockDatabase

class AnalysisService:
    """Unified service for all pattern/indicator analysis."""

    def __init__(self):
        self.indicator_service = IndicatorService()
        self.pattern_service = PatternService()
        self.detection_engine = PatternDetectionEngine()
        self.db = TickStockDatabase()

    def analyze_symbol(
        self,
        symbol: str,
        calculate_indicators: bool = True,
        detect_patterns: bool = True
    ) -> Dict[str, Any]:
        """
        Run full analysis for symbol (indicators + patterns).

        This is the main entry point for analysis operations.
        """
        # 1. Load OHLCV data
        df = self._load_ohlcv_data(symbol)

        results = {
            'symbol': symbol,
            'indicators': {},
            'patterns': {}
        }

        # 2. Calculate indicators (if requested)
        if calculate_indicators:
            results['indicators'] = self.indicator_service.calculate_all_indicators(
                symbol, df
            )

        # 3. Detect patterns (if requested)
        if detect_patterns:
            results['patterns'] = self.pattern_service.detect_all_patterns(
                symbol, df
            )

        return results

    def analyze_universe(
        self,
        universe: str,
        parallel: bool = True,
        max_workers: int = 10
    ) -> Dict[str, Any]:
        """
        Run full analysis for all symbols in universe.

        Args:
            universe: Universe key (SPY, QQQ, nasdaq100, etc.)
            parallel: Use parallel processing
            max_workers: Number of parallel workers
        """
        from src.core.services.relationship_cache import get_relationship_cache

        # Get symbols from universe
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols(universe)

        if parallel:
            return self._analyze_universe_parallel(symbols, max_workers)
        else:
            return self._analyze_universe_sequential(symbols)

    def _analyze_universe_parallel(
        self,
        symbols: List[str],
        max_workers: int
    ) -> Dict[str, Any]:
        """Parallel analysis using ThreadPoolExecutor."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {
            'symbols_processed': 0,
            'symbols_failed': 0,
            'indicators_calculated': 0,
            'patterns_detected': 0,
            'errors': []
        }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.analyze_symbol, symbol): symbol
                for symbol in symbols
            }

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    results['symbols_processed'] += 1
                    results['indicators_calculated'] += len(result['indicators'])
                    results['patterns_detected'] += len(result['patterns'])
                except Exception as e:
                    results['symbols_failed'] += 1
                    results['errors'].append({
                        'symbol': symbol,
                        'error': str(e)
                    })

        return results

    def _load_ohlcv_data(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """Load OHLCV data for symbol."""
        with self.db.get_connection() as conn:
            query = """
                SELECT date, open, high, low, close, volume
                FROM ohlcv_daily
                WHERE symbol = :symbol
                ORDER BY date DESC
                LIMIT :days
            """
            df = pd.read_sql_query(query, conn, params={
                'symbol': symbol,
                'days': days
            })
            return df.sort_values('date')  # Chronological order
```

**Deliverable**: ✅ Unified analysis service created

---

#### Day 14: End-to-End Integration Testing

**Task 10.1: Create E2E Test**
```python
# tests/integration/test_analysis_e2e.py
import pytest
from src.core.services.analysis_service import AnalysisService

@pytest.mark.e2e
class TestAnalysisE2E:
    def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline: data → indicators → patterns."""
        service = AnalysisService()

        # Run full analysis for AAPL
        result = service.analyze_symbol(
            'AAPL',
            calculate_indicators=True,
            detect_patterns=True
        )

        # Verify structure
        assert 'indicators' in result
        assert 'patterns' in result

        # Verify indicators calculated
        assert len(result['indicators']) > 0
        assert 'RSI' in result['indicators']

        # Verify patterns detected (may be 0 if no patterns present)
        assert 'patterns' in result

    def test_universe_analysis(self):
        """Test universe-level analysis."""
        service = AnalysisService()

        # Analyze SPY universe (504 symbols)
        result = service.analyze_universe('SPY', max_workers=10)

        # Verify processing
        assert result['symbols_processed'] > 0
        assert result['indicators_calculated'] > 0
```

**Task 10.2: Performance Testing**
```python
@pytest.mark.performance
def test_analysis_performance():
    """Verify analysis meets performance targets."""
    import time

    service = AnalysisService()

    start = time.time()
    result = service.analyze_symbol('AAPL')
    elapsed = time.time() - start

    # Target: <1s for single symbol (15 indicators + 20 patterns)
    assert elapsed < 1.0, f"Analysis took {elapsed}s, target <1s"
```

**Task 10.3: Regression Testing**
```bash
# Compare AppV2 output vs TickStockPL output for same symbol
pytest tests/integration/test_regression.py -v
```

**Deliverable**: ✅ E2E tests passing, performance validated

---

#### Day 15: Final Validation & Documentation

**Task 11.1: Run Full Test Suite**
```bash
# Unit tests
pytest tests/analysis/ -v --cov=src/analysis

# Integration tests
pytest tests/integration/ -v --cov=src/core/services

# Regression tests
pytest tests/ -m regression -v

# Performance tests
pytest tests/ -m performance -v
```

**Task 11.2: Update Documentation**

Create files:
1. `docs/guides/analysis/indicators.md` - Indicator usage guide
2. `docs/guides/analysis/patterns.md` - Pattern detection guide
3. `docs/guides/analysis/analysis-service.md` - AnalysisService API docs
4. `docs/architecture/analysis-architecture.md` - Analysis system architecture

**Task 11.3: Update CLAUDE.md**
```markdown
### Sprint 68 - COMPLETE ✅ (Date)
**Core Analysis Migration: Indicators & Patterns**
- ✅ 15 indicators migrated from TickStockPL
- ✅ 20+ patterns migrated from TickStockPL
- ✅ Analysis engines integrated
- ✅ IndicatorService, PatternService, AnalysisService created
- ✅ Dynamic loader system (NO FALLBACK)
- ✅ Regression testing: output matches TickStockPL
- ✅ Performance: <1s per symbol (15 indicators + 20 patterns)
- See: `docs/planning/sprints/sprint68/SPRINT68_COMPLETE.md`
```

**Deliverable**: ✅ Sprint 68 validated and documented

---

## Success Criteria

### Technical Requirements
- ✅ All 15 indicators functional in AppV2
- ✅ All 20+ patterns functional in AppV2
- ✅ Analysis engines operational
- ✅ IndicatorService calculates indicators correctly
- ✅ PatternService detects patterns correctly
- ✅ AnalysisService orchestrates full pipeline
- ✅ Database writes working (indicator_results, daily_patterns tables)

### Testing Requirements
- ✅ Unit tests: >80% coverage for indicators/patterns
- ✅ Integration tests: E2E pipeline working
- ✅ Regression tests: Output matches TickStockPL ±0.01%
- ✅ Performance tests: <1s per symbol analysis

### Quality Requirements
- ✅ NO FALLBACK policy enforced (dynamic loader)
- ✅ Convention-based indicator/pattern return values
- ✅ Clean ruff validation (0 errors)
- ✅ No "Generated by Claude" comments

### Documentation Requirements
- ✅ Indicator usage guide created
- ✅ Pattern detection guide created
- ✅ AnalysisService API documented
- ✅ CLAUDE.md updated with Sprint 68 status

---

## Risk Mitigation

### High Risks

**1. Regression Bugs (Output Doesn't Match TickStockPL)**
- **Mitigation**: Extensive regression testing suite
- **Detection**: Automated tests compare AppV2 vs PL output
- **Recovery**: Fix bugs before declaring sprint complete

**2. Performance Degradation**
- **Mitigation**: Performance testing at each phase
- **Target**: <1s per symbol (15 indicators + 20 patterns)
- **Recovery**: Profile and optimize slow components

**3. Database Schema Incompatibility**
- **Mitigation**: Use existing tables (indicator_results, daily_patterns)
- **Validation**: Integration tests write and read from database
- **Recovery**: Schema migration if needed

### Medium Risks

**4. Import/Dependency Issues**
- **Mitigation**: Update imports systematically, test after each file
- **Detection**: Unit tests fail if imports broken
- **Recovery**: Fix imports before moving to next file

**5. Dynamic Loader Edge Cases**
- **Mitigation**: Test all 15 indicators + 20 patterns load correctly
- **Detection**: Unit test for dynamic loader
- **Recovery**: Fix loader logic

---

## Dependencies

### External Dependencies
- pandas (already in AppV2)
- NumPy (already in AppV2)
- TA-Lib (add to requirements.txt)
- scikit-learn (optional, for advanced patterns)

### Internal Dependencies
- TickStockDatabase (already exists)
- RelationshipCache (Sprint 60, already exists)
- Configuration system (already exists)

### Database Dependencies
- Tables: indicator_definitions, indicator_results, pattern_definitions, daily_patterns
- Permissions: Read/write access for app_readwrite user

---

## Post-Sprint Cleanup

### Files to Remove (After Sprint 68)
- None (TickStockPL kept for historical data loading)

### Files to Archive
- Document migration in `docs/planning/sprints/sprint68/migration-log.md`

### Configuration Updates
- Update .env: Add any new configuration needed
- Update requirements.txt: Add TA-Lib, scikit-learn

---

## Next Sprint Preview

**Sprint 69**: Background Jobs & Integration
- Create background job framework (APScheduler)
- Daily pattern/indicator jobs
- Historical import integration (trigger analysis after data load)
- TickStockPL deprecation (remove Redis pub-sub dependencies)

---

## References

- **TickStockPL Source**: `C:/Users/McDude/TickStockPL/src/`
- **Migration Assessment**: `docs/planning/sprints/TICKSTOCKPL_MIGRATION_ASSESSMENT.md`
- **TickStockPL CLAUDE.md**: `C:/Users/McDude/TickStockPL/CLAUDE.md`
- **Indicator Conventions**: `C:/Users/McDude/TickStockPL/docs/guides/INDICATOR_PATTERN_CONVENTIONS.md`
- **Dynamic Loading**: `C:/Users/McDude/TickStockPL/docs/architecture/dynamic-loading.md`

---

**Sprint 68 Status**: ✅ Planning Complete - Ready for PRP Creation
