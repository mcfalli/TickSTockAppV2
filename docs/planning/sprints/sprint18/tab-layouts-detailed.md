# Three-Tab Layout Specifications  

**Date**: 2025-09-04  
**Sprint**: 18 - Planning Phase  
**Status**: Detailed Tab Design  

## Tab 2: Market Breadth - Complete Layout

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TickStock.ai                                         🔍 Search   👤 Profile    │
├─────────────────────────────────────────────────────────────────────────────────┤
│           [Pattern Scanner] [Market Breadth*] [My Focus]                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 📊 MARKET OVERVIEW                    │ 🌡️ SECTOR HEATMAP                      │
│                                       │                                         │
│ Major Indices (Live Updates)          │ ┌─────────────────────────────────────┐ │
│ SPY  $445.23 +0.8% ●●●○ [📊]        │ │ [XLK] Tech        +2.3% ████████    │ │
│ QQQ  $385.67 +1.2% ●●●● [📊]        │ │ [XLF] Finance     +0.8% ███         │ │
│ IWM  $198.45 -0.3% ●○○○ [📊]        │ │ [XLE] Energy      +3.1% ██████████  │ │
│ DIA  $356.78 +0.6% ●●○○ [📊]        │ │ [XLV] Healthcare  +1.2% ████        │ │
│ VXX  $28.76  -2.1% ○○○● [📊]        │ │ [XLI] Industrial  +0.9% ███         │ │
│                                       │ │ [XLY] Cons.Discr  -0.2% ▓           │ │
│ Market Breadth Indicators             │ │ [XLP] Cons.Stapl  +0.4% █           │ │
│ A/D Line:    ●●●○ Bullish            │ │ [XLB] Materials   +1.8% █████       │ │
│ New Hi/Lo:   ●●○○ Neutral            │ │ [XLRE] REIT       -0.1% ▓           │ │
│ Up Volume:   ●●●● Strong             │ │ [XLU] Utilities   +0.6% ██          │ │
│ McCl Osc:    ●●●○ Positive           │ │                                     │ │
│                                       │ │ 🔥 Strongest: Energy (+3.1%)       │ │
│ Support/Resistance Levels             │ │ 🧊 Weakest: Cons.Discr (-0.2%)     │ │
│ SPY: Support 442 | Resistance 448    │ └─────────────────────────────────────┘ │
│ QQQ: Support 380 | Resistance 390    │                                         │
│ IWM: Support 195 | Resistance 202    │ 📈 ROTATION ANALYSIS                    │
│                                       │ Money Flow: Tech ← Finance (High Vol) │
│                                       │ Defensive Play: Utilities ↑            │
│                                       │ Risk-On: Energy, Materials ↑           │
├───────────────────────────────────────┴─────────────────────────────────────────┤
│ 🎯 INDEX PATTERNS & ALERTS                                                     │
│ Symbol│Pattern      │Frame │Conf│ RS │Vol│Price  │Key Levels    │Alert│Chart │
│ SPY   │AscTriangle  │Daily │.89 │1.0x│1.4│445.23 │R:448 S:442   │🔔  │ 📊  │
│ QQQ   │BullFlag     │Daily │.92 │1.2x│1.8│385.67 │R:390 S:380   │🔔  │ 📊  │
│ IWM   │BrokenSupp   │Daily │.85 │0.8x│2.1│198.45 │R:202 S:195   │🔕  │ 📊  │
│ XLK   │Breakout     │Intra │.91 │1.5x│2.2│178.34 │Target: 182   │🔔  │ 📊  │
│ XLE   │Surge        │Intra │.93 │2.1x│3.8│68.45  │Momentum: +3% │🔔  │ 📊  │
│ VXX   │Reversal     │Daily │.87 │0.7x│2.5│28.76  │Fear Spike    │🔔  │ 📊  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 📈 MARKET CONTEXT CHART: SPY with sector overlay • Real-time market pulse      │
│ [Chart shows market leader (SPY) with sector rotation indicators]               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Key Market Breadth Features

#### Real-Time Index Monitoring
- **Live price updates** for major indices (SPY, QQQ, IWM, DIA)
- **Pattern detection** on index ETFs using same engines as individual stocks
- **Volatility tracking** (VXX) for fear/greed sentiment
- **Strength indicators** (●●●○) for quick visual assessment

#### Sector Rotation Heatmap
- **Visual heat mapping** showing sector performance
- **Money flow indicators** showing capital rotation
- **Relative strength** of sectors vs overall market
- **Sector ETF patterns** (XLK, XLF, XLE, etc.) with confidence scores

#### Market Breadth Metrics
- **Advance/Decline Line** - More stocks advancing vs declining
- **New Highs/Lows** - Distribution of stocks hitting extremes  
- **Up/Down Volume** - Volume distribution by direction
- **McClellan Oscillator** - Market momentum indicator

## Tab 3: My Focus - Personal Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TickStock.ai                                         🔍 Search   👤 Profile    │
├─────────────────────────────────────────────────────────────────────────────────┤
│           [Pattern Scanner] [Market Breadth] [My Focus*]                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 📁 MY WATCHLISTS                      │ ⚡ ACTIVE PATTERNS ON MY SYMBOLS         │
│                                       │                                         │
│ ┌───────────────────────────────────┐ │ Symbol│Pattern   │Conf│RS │Vol│Alert │📊│
│ │ 📂 Tech Leaders (12 symbols)      │ │ AAPL  │WeeklyBO  │.92 │1.4│2.1│🔔   │📊│
│ │ ├ AAPL ●●●○ 3 patterns           │ │ NVDA  │BullFlag  │.95 │1.6│3.2│🔕   │📊│
│ │ ├ NVDA ●●●● 2 patterns           │ │ MSFT  │TrendHold │.88 │1.1│1.8│🔕   │📊│
│ │ ├ MSFT ●●○○ 1 pattern            │ │ GOOGL │GapFill   │.91 │0.9│1.6│🔔   │📊│
│ │ └ [9 more symbols...]            │ │ TSLA  │VolSpike  │.94 │1.2│4.2│🔔   │📊│
│ │                                   │ │                                         │
│ │ 📂 High Momentum (8 symbols)      │ │ ┌─────────────────────────────────────┐ │
│ │ ├ TSLA ●●●● 2 patterns           │ │ │      🚨 LIVE PATTERN ALERTS         │ │
│ │ ├ AMD  ●●●○ 1 pattern            │ │ │ 🟢 AAPL entry signal $184.75       │ │
│ │ └ [6 more symbols...]            │ │ │ 🟡 NVDA approaching R at $490       │ │
│ │                                   │ │ │ 🔴 TSLA stop loss hit $238.50      │ │
│ │ 📂 Value Opportunities (15)       │ │ │ 🟢 New: AMD Ascending Triangle      │ │
│ │ 📂 Crypto Proxies (6)            │ │ │ ⏰ GOOGL pattern expires in 45m     │ │
│ │                                   │ │ └─────────────────────────────────────┘ │
│ │ [+ New Watchlist]                │ │                                         │
│ └───────────────────────────────────┘ │ 📊 TODAY'S PERFORMANCE                  │
│                                       │ Patterns Triggered: 12                 │
│ 🎛️ MY SAVED FILTERS                   │ Win Rate: 68% (8/12)                   │
│                                       │ Avg Confidence: 0.89                   │
│ ┌───────────────────────────────────┐ │ Best: NVDA (+5.2%)                     │
│ │ 📂 Morning Gap Plays              │ │ Worst: TSLA (-1.8%)                    │
│ │   • Gaps >2% with volume         │ │ Total P&L: +$2,450                     │
│ │   • Market cap >$5B               │ │                                         │
│ │                                   │ │ 🎯 FOCUS METRICS                       │
│ │ 📂 High RS + Volume Surge         │ │ Watchlist Coverage: 89%                │
│ │   • RS >1.2, Volume >2x          │ │ Pattern Accuracy: 72%                   │
│ │   • Daily + Intraday combo       │ │ Avg Hold Time: 2.3 days                │
│ │                                   │ │ Risk/Reward: 1:2.1                     │
│ │ 📂 End of Day Swings              │ │                                         │
│ │   • Daily patterns, 3-7 day hold │ │                                         │
│ │                                   │ │                                         │
│ │ [+ New Saved Filter]             │ │                                         │
│ └───────────────────────────────────┘ │                                         │
├───────────────────────────────────────┴─────────────────────────────────────────┤
│ 📈 AUTO-FOCUS CHART: Highest confidence pattern from active watchlist           │
│ Currently showing: NVDA Bull Flag (.95 confidence) • Updates automatically      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### My Focus Key Features

#### Personal Watchlists
- **Organized by strategy** (Tech Leaders, High Momentum, Value, etc.)
- **Pattern count indicators** per symbol (●●●○ = 3 active patterns)
- **Quick pattern summary** for each watchlist
- **Easy symbol management** with drag-and-drop organization

#### Saved Filter Sets  
- **Strategy-based filters** saved for quick access
- **Complex combinations** (RS + Volume + Timeframe)
- **One-click activation** to apply to Pattern Scanner
- **Shareable filter sets** for team/community use

#### Live Pattern Alerts
- **Real-time notifications** when watchlist patterns trigger
- **Entry/exit signals** with specific price levels  
- **Risk management alerts** (stop losses, expiration warnings)
- **Performance tracking** with P&L calculation

#### Performance Analytics
- **Win rate tracking** for pattern-based trades
- **Confidence score analysis** - which confidence levels perform best
- **Hold time optimization** - pattern duration vs performance
- **Risk/reward metrics** for strategy evaluation

## Mobile Responsive Design (All Tabs)

### Pattern Scanner Mobile
```
┌─────────────────────────────┐
│ Pattern Scanner    [☰]     │
├─────────────────────────────┤
│ 🎛️ Filters [▼] Found: 247   │
├─────────────────────────────┤
│ Symbol Pattern  Conf  Chart │
│ AAPL  WeeklyBO .92    📊   │
│ NVDA  BullFlag .95    📊   │
│ MSFT  TrendHld .88    📊   │
│ TSLA  VolSpike .94    📊   │
│ AMD   Reversal .87    📊   │
│ [Load 20 More...]          │
├─────────────────────────────┤
│ 📈 Tap row to view chart    │
└─────────────────────────────┘
```

### Market Breadth Mobile
```
┌─────────────────────────────┐
│ Market Breadth     [☰]     │
├─────────────────────────────┤
│ 📊 INDICES                  │
│ SPY $445.23 +0.8% ●●●○ 📊 │
│ QQQ $385.67 +1.2% ●●●● 📊 │
│ IWM $198.45 -0.3% ●○○○ 📊 │
├─────────────────────────────┤
│ 🌡️ SECTORS                  │
│ Tech     +2.3% ████████    │
│ Energy   +3.1% ██████████  │
│ Finance  +0.8% ███         │
│ [View All Sectors...]      │
├─────────────────────────────┤
│ 📈 Tap index to view chart  │
└─────────────────────────────┘
```

### My Focus Mobile
```
┌─────────────────────────────┐
│ My Focus           [☰]     │
├─────────────────────────────┤
│ 📁 Tech Leaders (12) [▼]   │
│ AAPL 3 patterns ●●●○ 📊   │
│ NVDA 2 patterns ●●●● 📊   │
│ MSFT 1 pattern  ●●○○ 📊   │
├─────────────────────────────┤
│ 🚨 ALERTS (4)              │
│ 🟢 AAPL entry $184.75     │
│ 🟡 NVDA near R $490        │
│ [View All Alerts...]       │
├─────────────────────────────┤
│ 📊 Today: +$2,450 (68%)    │
│ 📈 Auto-chart: NVDA        │
└─────────────────────────────┘
```

## Key Design Principles

### Information Hierarchy
1. **Tab Navigation**: Clear separation of use cases
2. **Data Density**: Maximum information per screen area  
3. **Visual Scanning**: Color coding and symbols for quick pattern recognition
4. **Progressive Disclosure**: Details available on-demand (click for chart)

### Interaction Patterns
1. **Click Row → Load Chart**: Universal interaction across all tabs
2. **Filter Persistence**: Filters remain active across tab switches
3. **Real-time Updates**: Live data refresh without page reload
4. **Export Capabilities**: CSV/JSON export for analysis tools

### Performance Considerations
1. **Lazy Loading**: Charts load only when requested
2. **Virtual Scrolling**: Handle thousands of patterns efficiently
3. **Debounced Filtering**: Smooth user experience during rapid filter changes
4. **Caching Strategy**: Redis cache for pattern queries, WebSocket for updates

This three-tab approach provides comprehensive pattern discovery while maintaining the data density and scanning efficiency you requested. Each tab serves a distinct purpose while sharing common interaction patterns for consistency.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Redesign UI for high-density pattern data display", "status": "completed", "activeForm": "Redesigning UI for high-density pattern data"}, {"content": "Create market breadth tab concept", "status": "completed", "activeForm": "Creating market breadth tab concept"}, {"content": "Design user focus/watchlist tab", "status": "completed", "activeForm": "Designing user focus/watchlist tab"}, {"content": "Update wireframe document with new layout", "status": "completed", "activeForm": "Updating wireframe document"}]