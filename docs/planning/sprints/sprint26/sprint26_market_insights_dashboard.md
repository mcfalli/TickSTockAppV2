# Sprint 26: Market Insights Dashboard with ETF-Based State

**Priority**: HIGH  
**Duration**: 2-3 weeks  
**Status**: Planning

## Sprint Objectives

Create comprehensive market state dashboard using ETFs to represent market segments with 3-tiered interaction model, providing clear state of the market with combined view using ETFs to represent market conditions.

## Market Intelligence Architecture

### ETF Market Representation Strategy

**Primary Market ETFs for State Detection**:
- **SPY** (S&P 500) - Large Cap Market Health & Overall Direction
- **QQQ** (NASDAQ-100) - Technology/Growth Sector Leadership  
- **IWM** (Russell 2000) - Small Cap Health & Risk Appetite
- **XLF** (Financials) - Economic Health & Credit Conditions
- **XLE** (Energy) - Commodity/Energy Sector & Inflation Signals
- **GLD** (Gold) - Risk-off Sentiment & Inflation Hedge Demand

### Three-Tiered Market Interaction Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Market Insights Dashboard                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Tier 1: Market Overview                         ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       ││
│  │  │Market Health│ │Risk Level   │ │Trend State  │ │Volatility   │       ││
│  │  │    85%      │ │   Medium    │ │  Bullish    │ │    12.3     │       ││  
│  │  │   Healthy   │ │   Risk-On   │ │  Confirmed  │ │   Normal    │       ││
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                   │                                         │
│  ┌─────────────────────────────────▼─────────────────────────────────────────┐│
│  │                      Tier 2: Sector Analysis                           ││
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                      ││
│  │  │ SPY │ │ QQQ │ │ IWM │ │ XLF │ │ XLE │ │ GLD │                      ││
│  │  │+1.2%│ │+2.1%│ │+0.8%│ │+1.5%│ │-0.3%│ │-0.8%│                      ││
│  │  │ 🟢  │ │ 🟢  │ │ 🟡  │ │ 🟢  │ │ 🔴  │ │ 🔴  │                      ││
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                      ││
│  │  Sector Rotation: Tech Leading, Energy Lagging                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                   │                                         │
│  ┌─────────────────────────────────▼─────────────────────────────────────────┐│
│  │              Tier 3: Pattern Integration & Trading Signals             ││
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             ││
│  │  │ETF Patterns     │ │Market Regime    │ │State-Filtered   │             ││
│  │  │SPY: Bull Flag   │ │Classification   │ │Stock Patterns   │             ││
│  │  │QQQ: Breakout    │ │   BULL MARKET   │ │Bullish: 47      │             ││
│  │  │IWM: Support     │ │   Confirmed     │ │Neutral: 23      │             ││
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Components

### 2.1 Market State Engine

**Core Services**:
```python
src/core/services/market_state_service.py          # Main market state orchestrator
src/core/domain/market/etf_analyzer.py             # ETF performance analysis
src/core/domain/market/market_regime_classifier.py # Bull/Bear/Neutral classification
src/core/domain/market/sector_rotation_analyzer.py # Sector strength analysis
src/core/domain/market/risk_assessment_engine.py   # Risk-on/Risk-off signals
```

**Market State Calculation Features**:
- **Real-time ETF Performance**: Price, volume, relative strength analysis
- **Market Regime Detection**: Bull/Bear/Consolidation classification using ETF correlations
- **Risk Assessment**: Risk-on/Risk-off signal generation from ETF relationships
- **Sector Rotation Analysis**: Leadership rotation between major sectors
- **Volatility Context**: Market stress indicators from ETF spreads

### 2.2 Market Insights UI Dashboard

**Frontend Components**:
```javascript
web/static/js/components/market_insights_dashboard.js    # Main dashboard orchestrator
web/static/js/components/market_overview_tier.js         # Tier 1: Market overview
web/static/js/components/etf_matrix_display.js           # Tier 2: ETF performance matrix
web/static/js/components/sector_heatmap.js               # Sector strength visualization
web/static/js/components/market_regime_indicator.js      # Market regime display
web/static/js/components/pattern_market_integration.js   # Tier 3: Pattern filtering
web/static/js/services/market_data_service.js            # Market data management
```

**Dashboard Interaction Features**:
- **Drill-Down Navigation**: Market → Sector → Individual Stock Patterns
- **Real-Time Updates**: WebSocket-driven market state changes
- **Interactive ETF Matrix**: Click ETFs for detailed analysis
- **Context-Aware Patterns**: Pattern filtering based on market regime
- **Historical Context**: Market state trends and regime changes

### 2.3 ETF-Pattern Integration APIs

**New API Endpoints**:
```python
src/api/rest/market_insights.py                    # Market insights API
src/api/rest/etf_analysis.py                       # ETF-specific analysis
```

**API Endpoints**:
- `GET /api/market/state` - Current market regime, health score, risk level
- `GET /api/market/etfs` - Real-time ETF performance and signals
- `GET /api/market/sectors` - Sector analysis and rotation signals
- `GET /api/market/patterns` - Market state-filtered stock patterns
- `GET /api/market/regime/history` - Historical market regime changes
- `GET /api/market/risk/signals` - Risk-on/Risk-off signal analysis

## Market State Logic

### Market Regime Classification
```python
def classify_market_regime(etf_data: Dict) -> MarketRegime:
    """
    Market regime classification using ETF relationships:
    
    BULL MARKET:
    - SPY trending up with volume
    - QQQ outperforming SPY (growth leadership)
    - IWM participating (small cap strength)
    - XLF showing strength (economic confidence)
    - GLD declining (risk-on sentiment)
    
    BEAR MARKET:
    - SPY declining with volume
    - Defensive sectors outperforming
    - GLD rising (flight to safety)
    - XLF underperforming (credit concerns)
    
    CONSOLIDATION:
    - Mixed ETF signals
    - Low volatility across sectors
    - Sector rotation without clear leadership
    """
```

### Risk Assessment Framework
```python
@dataclass
class MarketRiskAssessment:
    risk_level: RiskLevel          # LOW, MEDIUM, HIGH, EXTREME
    risk_direction: RiskDirection  # RISK_ON, RISK_OFF, NEUTRAL
    confidence: float              # 0.0 - 1.0
    
    # Risk signals from ETF relationships
    equity_strength: float         # SPY/QQQ performance
    small_cap_health: float        # IWM relative performance  
    financial_stress: float        # XLF performance indicator
    safe_haven_demand: float       # GLD/Treasury demand
    commodity_pressure: float      # XLE/commodity signals
```

## Technical Implementation Details

### Data Flow Architecture
1. **Market Data Ingestion**: Real-time ETF price/volume from existing market data service
2. **ETF Analysis Engine**: Calculate performance metrics, correlations, signals
3. **Market State Classification**: Determine regime and risk assessment
4. **Pattern Context Integration**: Filter TickStockPL patterns by market state
5. **Dashboard Updates**: Real-time WebSocket updates to UI components

### Performance Requirements
- **Market State Updates**: Every 30 seconds during market hours
- **ETF Data Processing**: <100ms for complete analysis cycle
- **Dashboard Refresh**: <200ms from data update to UI render
- **API Response Times**: <50ms for market state queries
- **Pattern Filtering**: <100ms to apply market context to patterns

### Integration with Existing Systems
- **Market Data Service**: Extend to include ETF data streams
- **Redis Event System**: Add market state change events
- **Pattern Display**: Enhance with market context indicators
- **WebSocket Publisher**: Add market insights broadcast channel

## User Experience Features

### Market State Awareness
- **Visual Market Health**: Color-coded market health indicators
- **Regime Transitions**: Clear notifications when market regime changes
- **Risk Level Alerts**: Notifications when risk assessment changes significantly
- **Context Tooltips**: Explanations of market state calculations

### Pattern Context Enhancement
- **Market-Filtered Patterns**: Show only patterns appropriate for current market regime
- **Regime-Specific Success Rates**: Historical pattern performance by market state
- **Risk-Adjusted Alerts**: Pattern alerts adjusted for current risk environment
- **Market Timing Guidance**: Suggestions based on current market context

## Implementation Timeline

### Week 1: Market State Engine
1. Implement ETF data ingestion and analysis
2. Create market regime classification logic
3. Build risk assessment framework
4. Add market state API endpoints
5. Unit tests for market state calculations

### Week 2: Dashboard UI Components
1. Build market overview (Tier 1) component
2. Create ETF matrix display (Tier 2)
3. Implement pattern integration (Tier 3)
4. Add real-time WebSocket updates
5. Responsive design and mobile optimization

### Week 3: Integration & Advanced Features
1. Integrate with existing pattern display systems
2. Add historical market state tracking
3. Implement market state-based pattern filtering
4. Performance optimization and caching
5. User testing and refinement

## Success Criteria

- [ ] **Market State Accuracy**: Reliable bull/bear/neutral classification
- [ ] **Real-Time Updates**: Market state updates within 30 seconds
- [ ] **ETF Integration**: All 6 primary ETFs tracked and analyzed
- [ ] **Three-Tier Dashboard**: Functional drill-down interaction model
- [ ] **Pattern Context**: Stock patterns filtered by market regime
- [ ] **Performance Targets**: <50ms API responses, <200ms dashboard updates
- [ ] **User Experience**: Intuitive market state visualization and navigation

## Risk Mitigation

### Data Quality Risks
- **ETF Data Reliability**: Multiple data source validation
- **Market State Accuracy**: Backtesting against historical regimes
- **Real-Time Performance**: Load testing with market volatility scenarios

### User Experience Risks
- **Information Overload**: Progressive disclosure design
- **Complexity Management**: Clear visual hierarchy and tooltips
- **Mobile Performance**: Responsive design testing across devices

This sprint establishes comprehensive market context that enhances all subsequent pattern analysis and user decision-making capabilities.