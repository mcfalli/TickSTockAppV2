Pydantic v2 Integration Plan for TickStock.ai

Based on my analysis of the current codebase, here's a comprehensive plan to incorporate Pydantic v2 strategically:

📊 Current State Analysis

Existing Validation Patterns Found:

- Dataclasses: OHLCVData, FMVData in data_types.py with manual validation
- Manual Validation: Custom validate() methods, manual type checking
- Dict-Based Transport: Extensive to_dict() / from_dict() patterns
- Event Models: TickData with manual validation and field checking

Key Pain Points to Address:

1. Manual Validation: Repetitive validation logic across data models
2. Serialization Complexity: Manual dict conversion methods
3. Type Safety: Limited runtime type checking
4. Performance: Manual validation overhead
5. Redis Message Validation: JSON payloads lacking validation

🎯 Pydantic v2 Integration Strategy

Phase 1: Foundation Models (Week 1)

1.1 Core Market Data Models

Replace existing dataclasses with Pydantic v2 models:

# src/shared/models/market_data.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Literal
from datetime import datetime

class TickStockBaseModel(BaseModel):
    """Base model for all TickStock data with performance optimizations"""
    model_config = ConfigDict(
        # Pydantic v2 performance optimizations
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=False,
        extra='forbid',  # Strict field validation
        str_strip_whitespace=True,
        frozen=False  # Allow updates for processing fields
    )

class TickDataV2(TickStockBaseModel):
    """Pydantic v2 version of TickData with enhanced validation"""
    # Required fields
    ticker: str = Field(..., min_length=1, max_length=5, pattern=r'^[A-Z]+$')
    price: float = Field(..., gt=0, description="Current price")
    volume: int = Field(..., ge=0, description="Volume")
    timestamp: float = Field(..., gt=1577836800, description="Unix timestamp")

    # Source identification with Literal types for performance
    source: Literal["polygon", "synthetic", "simulated", "alpaca"] = "unknown"
    event_type: Literal["A", "T", "Q"] = "A"
    market_status: Literal["PREMARKET", "REGULAR", "AFTERHOURS"] = "REGULAR"

    # Optional fields with smart defaults
    bid: Optional[float] = Field(None, gt=0)
    ask: Optional[float] = Field(None, gt=0)

    # Price fields (tick-level)
    tick_open: Optional[float] = Field(None, gt=0)
    tick_high: Optional[float] = Field(None, gt=0)
    tick_low: Optional[float] = Field(None, gt=0)
    tick_close: Optional[float] = Field(None, gt=0)

    # Processing fields
    processed_at: Optional[float] = None

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        """Ensure timestamp is within reasonable range (2020-2030)"""
        if not (1577836800 < v < 1893456000):
            raise ValueError(f'Timestamp {v} outside valid range')
        return v

    @field_validator('tick_close', mode='before')
    @classmethod
    def set_tick_close_default(cls, v: Optional[float], info) -> Optional[float]:
        """Default tick_close to price if not provided"""
        if v is None and 'price' in info.data:
            return info.data['price']
        return v

class OHLCVDataV2(TickStockBaseModel):
    """Pydantic v2 version of OHLCVData"""
    ticker: str = Field(..., pattern=r'^[A-Z]+$')
    timestamp: float = Field(..., gt=0)

    # OHLC price data with cross-field validation
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)

    # Volume data
    volume: int = Field(..., ge=0)
    avg_volume: float = Field(..., gt=0)

    # Calculated fields
    percent_change: float = 0.0

    # Optional fields
    vwap: Optional[float] = Field(None, gt=0)
    timeframe: str = Field(default="1m", pattern=r'^(1m|5m|15m|1h|1d)$')

    @field_validator('high')
    @classmethod
    def validate_high_price(cls, v: float, info) -> float:
        """Validate high >= max(open, close)"""
        if 'open' in info.data and 'close' in info.data:
            max_price = max(info.data['open'], info.data['close'])
            if v < max_price:
                raise ValueError(f'High {v} must be >= max(open, close) = {max_price}')
        return v

    @field_validator('low')
    @classmethod
    def validate_low_price(cls, v: float, info) -> float:
        """Validate low <= min(open, close)"""
        if 'open' in info.data and 'close' in info.data:
            min_price = min(info.data['open'], info.data['close'])
            if v > min_price:
                raise ValueError(f'Low {v} must be <= min(open, close) = {min_price}')
        return v

1.2 Redis Message Models

Define Pydantic models for Redis pub-sub messages:

# src/shared/models/redis_messages.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union
from datetime import datetime

class RedisMessageBase(TickStockBaseModel):
    """Base Redis message model"""
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    source: str = Field(..., description="Message source")

class PatternEventMessage(RedisMessageBase):
    """Pattern detection event from TickStockPL to TickStockApp"""
    event_type: Literal["pattern_detected"] = "pattern_detected"
    pattern: str = Field(..., min_length=1, description="Pattern name")
    symbol: str = Field(..., pattern=r'^[A-Z]+$')
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    timeframe: str = Field(default="1min", pattern=r'^(1min|5min|15min|1h|1d)$')
    direction: Optional[Literal["bullish", "bearish", "reversal"]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BacktestJobMessage(RedisMessageBase):
    """Backtest job request from TickStockApp to TickStockPL"""
    job_type: Literal["backtest"] = "backtest"
    job_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    symbols: list[str] = Field(..., min_items=1, max_items=50)
    start_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    end_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    patterns: list[str] = Field(..., min_items=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)

class BacktestProgressMessage(RedisMessageBase):
    """Backtest progress update from TickStockPL to TickStockApp"""
    job_id: str = Field(..., min_length=1)
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress 0.0-1.0")
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = ...
    current_symbol: Optional[str] = None
    estimated_completion: Optional[datetime] = None

Phase 2: API Integration (Week 2)

2.1 Flask API Models

Create Pydantic models for Flask API endpoints:

# src/api/models/requests.py
from pydantic import BaseModel, Field
from typing import Optional, List

class UserRegistrationRequest(TickStockBaseModel):
    """User registration request validation"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    email: str = Field(..., pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)

class BacktestConfigRequest(TickStockBaseModel):
    """Backtest configuration request from UI"""
    symbols: List[str] = Field(..., min_items=1, max_items=20)
    start_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    end_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    patterns: List[str] = Field(..., min_items=1)
    initial_capital: float = Field(default=100000, gt=0, le=10000000)
    position_size: float = Field(default=0.1, gt=0, le=1.0)

# src/api/models/responses.py
class APIResponse(TickStockBaseModel):
    """Standard API response format"""
    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())

class BacktestResultResponse(APIResponse):
    """Backtest results response"""
    data: Optional[Dict[str, Union[float, int, str]]] = Field(
        None,
        description="Backtest metrics: win_rate, roi, sharpe_ratio, max_drawdown"
    )

🔄 Migration Strategy

Phase 1: Parallel Implementation (Week 1)

1. Create Pydantic models alongside existing dataclasses
2. Implement adapters for gradual migration
3. Add feature flags to switch between implementations

# Migration adapter pattern
class DataModelAdapter:
    @staticmethod
    def from_legacy_tick(legacy_tick: TickData) -> TickDataV2:
        """Convert legacy TickData to Pydantic TickDataV2"""
        return TickDataV2(**legacy_tick.to_dict())

    @staticmethod
    def to_legacy_tick(pydantic_tick: TickDataV2) -> TickData:
        """Convert Pydantic TickDataV2 to legacy TickData"""
        return TickData(**pydantic_tick.model_dump())

📈 Expected Performance Benefits

Validation Performance

- ~3x faster validation with Pydantic v2's Rust core
- Reduced memory usage with optimized model storage
- Better error messages with detailed validation feedback

Serialization Performance

- ~2x faster JSON serialization with orjson integration
- Type-safe serialization eliminating manual dict conversion
- Automatic field aliasing for external API compatibility

Development Velocity

- Automatic API documentation with OpenAPI schema generation
- IDE autocomplete with proper type hints
- Reduced boilerplate with automatic validation and serialization

🎯 Implementation Priority

High Priority (Sprint 10)

1. Redis message models - Direct impact on TickStockPL integration
2. API request/response models - Improved user interface validation
3. Core market data models - Foundation for all data processing

Medium Priority (Post-Sprint 10)

1. Database models - Enhanced data persistence validation
2. Configuration models - Better environment/settings validation
3. Legacy code migration - Complete transition from dataclasses

This plan leverages Pydantic v2's performance improvements while maintaining the clean architecture boundaries established in our Sprint 10 work. The models will enforce the consumer/producer role separation and provide type-safe Redis communication between TickStockApp and TickStockPL.

## Related Documentation

- **[`system-architecture.md`](system-architecture.md)** - Complete system architecture overview
- **[`../planning/project-overview.md`](../planning/project-overview.md)** - Project vision and requirements