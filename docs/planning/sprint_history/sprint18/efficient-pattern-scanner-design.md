# Efficient Pattern Scanner - High-Density UI Design

**Date**: 2025-09-04  
**Sprint**: 18 - Planning Phase  
**Status**: Revised Design - Data-Dense Approach  

## Design Philosophy: Information Density Over Visual Polish

Your feedback is spot-on - with hundreds/thousands of patterns, cards become a scanning nightmare. This revision prioritizes:
- **Information density** - Maximum data per screen real estate
- **Quick scanning** - Eye can quickly process tabular data
- **Extensive filtering** - Complex filter combinations for pattern discovery
- **Focused interaction** - Click row → see chart, minimal UI chrome

## Three-Tab Architecture (Revised)

### Tab 1: Pattern Scanner
**Purpose**: Universal pattern search across all timeframes and types
**Layout**: Extensive filters + dense table + on-demand chart
**Data Sources**: All pattern tables (daily, intraday, combo) unified view

### Tab 2: Market Breadth  
**Purpose**: Index/ETF analysis for market context and sector rotation
**Layout**: Market overview + sector heatmap + index pattern analysis
**Data Sources**: ETF symbols (SPY, QQQ, IWM, XLE, XLF, etc.) + sector aggregations

### Tab 3: My Focus
**Purpose**: Personal watchlists and saved filter presets
**Layout**: Saved searches + custom watchlists + real-time updates
**Data Sources**: User preferences + subset of pattern data

## Tab 1: Pattern Scanner - Detailed Design

### Layout Structure
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          Pattern Scanner                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Filters [▼]  │                    Results: 1,247 patterns                       │
├──────────────┼─────────────────────────────────────────────────────────────────┤
│              │ Symbol │Pattern     │Conf│ RS │Vol│Price │Chg│Time │Exp │Chart │
│ PATTERN TYPE │ AAPL   │WeeklyBreak │.92 │1.4x│2.1│185.50│+2.3│2h  │3d  │ 📊  │
│ ☑ Breakouts  │ NVDA   │BullFlag    │.95 │1.6x│3.2│485.75│+5.2│1h  │2d  │ 📊  │
│ ☑ Volume     │ MSFT   │TrendHold   │.88 │1.1x│1.8│415.25│+0.8│4h  │1d  │ 📊  │
│ ☑ Trendlines │ TSLA   │VolSpike    │.94 │1.2x│4.2│242.85│+3.8│2m  │4h  │ 📊  │
│ ☐ Gaps       │ AMD    │Reversal    │.87 │1.3x│2.8│152.30│+1.9│30m │2h  │ 📊  │
│ ☐ Reversals  │ GOOGL  │GapFill     │.91 │0.9x│1.6│138.25│-0.3│12m │1h  │ 📊  │
│              │ AMZN   │MomShift    │.89 │1.1x│1.9│145.80│+1.1│8m  │45m │ 📊  │
│ TIMEFRAME    │ NFLX   │Support     │.86 │0.8x│1.3│485.60│-0.5│1d  │7d  │ 📊  │
│ ● All        │ [... 20 more visible rows ...]                                 │
│ ○ Daily      │ ┌─────────────────────────────────────────────────────────────┐ │
│ ○ Intraday   │ │ Page: [1] 2 3 4 5 ... 42    Show: [30▼] per page          │ │
│ ○ Combo      │ │ Export: [CSV] [JSON]    Auto-refresh: [ON▼] 30s             │ │
│              │ └─────────────────────────────────────────────────────────────┘ │
│ INDICATORS   │                                                                 │
│ RS > [1.0▼]  │                                                                 │
│ Vol> [1.5▼]  │                                                                 │
│ RSI  [30-70] │                                                                 │
│              │                                                                 │
│ CONFIDENCE   │                                                                 │
│ ●●●○ > 0.85  │                                                                 │
│ ●●○○ > 0.70  │                                                                 │
│ ●○○○ > 0.50  │                                                                 │
│              │                                                                 │
│ SYMBOLS      │                                                                 │
│ 🔍 Search... │                                                                 │
│ ☐ Tech       │                                                                 │
│ ☐ Healthcare │                                                                 │
│ ☐ Finance    │                                                                 │
│ ☐ Energy     │                                                                 │
│              │                                                                 │
│ TIME RANGE   │                                                                 │
│ ● Last 4hrs  │                                                                 │
│ ○ Today      │                                                                 │
│ ○ 3 days     │                                                                 │
│ ○ Custom     │                                                                 │
│              │                                                                 │
│ [Reset All]  │                                                                 │
│ [Save Filter]│                                                                 │
├──────────────┴─────────────────────────────────────────────────────────────────┤
│ 📈 CHART: Click any row above to load chart • Currently: None selected         │
│ [Chart panel collapses/expands as needed - initially collapsed to save space]  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Advanced Filter Features

#### Multi-Select Pattern Types
```
PATTERN TYPE ☑☑☑☐☐☐ (6 selected)
┌────────────────────────────┐
│ ☑ Breakouts (45)          │ 
│ ☑ Volume Spikes (89)      │
│ ☑ Trendlines (23)         │
│ ☐ Gaps (12)               │
│ ☐ Reversals (8)           │
│ ☐ Momentum Shifts (67)    │
│ ☐ Flag Patterns (34)      │
│ ☐ Support/Resistance (56) │
└────────────────────────────┘
```

#### Combined Indicator Filters  
```
ADVANCED FILTERS
┌────────────────────────────┐
│ Relative Strength          │
│ ○ Any   ● >1.0  ○ >1.2     │
│ ○ >1.5  ○ >2.0             │
│                            │
│ Volume Multiple            │
│ ● >1.5x  ○ >2.0x  ○ >3.0x  │
│                            │
│ RSI Range                  │
│ [25] ████████████ [75]     │
│                            │
│ Price Change               │
│ ○ Any  ○ >1%  ● >2%  ○ >5% │
│                            │
│ Market Cap                 │
│ ☑ Large  ☑ Mid  ☐ Small   │
└────────────────────────────┘
```

#### Saved Filter Sets
```
MY SAVED FILTERS
┌────────────────────────────┐
│ 📁 High Momentum Breakouts │
│ 📁 Volume Surge + RS > 1.2 │
│ 📁 Intraday Scalp Setups  │
│ 📁 Daily Swing Patterns   │
│ 📁 ETF Sector Rotation    │
│                            │
│ [+ Create New Filter Set]  │
└────────────────────────────┘
```

## Tab 2: Market Breadth - Index Analysis

### Layout Structure  
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Market Breadth                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Major Indices              │ Sector Rotation                                    │
├────────────────────────────┼────────────────────────────────────────────────────┤
│ SPY  $445.23 +0.8% ●●●○   │ ┌──────────────────────────────────────────────┐  │
│ QQQ  $385.67 +1.2% ●●●●   │ │              SECTOR HEATMAP                  │  │
│ IWM  $198.45 -0.3% ●○○○   │ │                                              │  │
│ VXX  $28.76  -2.1% ○○○●   │ │ [XLK]    [XLF]    [XLE]    [XLV]           │  │
│                            │ │ Tech     Finance  Energy   Health          │  │
│ Breadth Indicators         │ │ +2.3%    +0.8%    +3.1%    +1.2%           │  │
│ A/D Line:  ●●●○ Bullish   │ │ ████     ██       ██████    ███             │  │
│ New Hi/Lo: ●●○○ Neutral   │ │                                              │  │
│ Up Volume: ●●●● Strong    │ │ [XLI]    [XLY]    [XLP]    [XLB]           │  │
│                            │ │ Indust   ConsDis  ConsStpl Materials      │  │
│ Index Patterns             │ │ +0.9%    -0.2%    +0.4%    +1.8%           │  │
│ SPY: Ascending Triangle    │ │ ██       ▓        █        ████             │  │
│ QQQ: Bull Flag Formation   │ │                                              │  │
│ IWM: Below Support         │ │ [XLRE]   [XLU]    [Other ETFs...]          │  │
│                            │ │ REIT     Utility                           │  │
│                            │ │ -0.1%    +0.6%                             │  │
│                            │ │ ▓        ██                                 │  │
│                            │ └──────────────────────────────────────────────┘  │
├────────────────────────────┴────────────────────────────────────────────────────┤
│ INDEX PATTERN DETAILS                                                           │
│ Symbol│Pattern      │Timeframe│Conf│ RS │Vol │Price  │Key Levels      │Chart  │
│ SPY   │AscTriangle  │Daily    │.89 │1.0x│1.4x│445.23 │R:448 S:442     │  📊  │
│ QQQ   │BullFlag     │Daily    │.92 │1.2x│1.8x│385.67 │R:390 S:380     │  📊  │
│ IWM   │BrokenSupp   │Daily    │.85 │0.8x│2.1x│198.45 │R:202 S:195     │  📊  │
│ XLK   │Breakout     │Intraday │.91 │1.5x│2.2x│178.34 │Target: 182     │  📊  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Market Context Features
- **Real-time index updates** with pattern detection on major ETFs
- **Sector rotation analysis** showing money flow between sectors  
- **Breadth indicators** (advance/decline, new highs/lows, volume)
- **Pattern correlation** - how individual stock patterns align with market

## Tab 3: My Focus - Personal Watchlists  

### Layout Structure
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              My Focus                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│ My Watchlists [▼]     │ Active Patterns on My Symbols                          │
├───────────────────────┼─────────────────────────────────────────────────────────┤
│                       │ Symbol│Pattern    │Conf│RS │Vol│Price │Alert│Chart     │
│ 📁 Tech Leaders (12)  │ AAPL  │WeeklyBO   │.92 │1.4│2.1│185.5 │🔔  │ 📊      │
│ 📁 High Momentum (8)  │ NVDA  │BullFlag   │.95 │1.6│3.2│485.7 │🔕  │ 📊      │
│ 📁 Value Plays (15)   │ MSFT  │TrendHold  │.88 │1.1│1.8│415.2 │🔕  │ 📊      │
│ 📁 Crypto/Tech (6)    │                                                        │
│                       │ ┌──────────────────────────────────────────────────┐  │
│ Saved Filters [▼]     │ │           PATTERN ALERTS                         │  │
│                       │ │ 🟢 AAPL triggered entry signal at $184.75       │  │
│ 📂 Morning Breakouts  │ │ 🟡 NVDA approaching resistance at $490          │  │
│ 📂 Volume + RS > 1.2  │ │ 🔴 TSLA stop loss triggered at $238.50          │  │
│ 📂 Gap Plays          │ │ 🟢 New pattern: AMD - Ascending Triangle        │  │
│ 📂 End of Day Swings  │ └──────────────────────────────────────────────────┘  │
│                       │                                                        │
│ Quick Actions         │ Performance Summary (Today)                           │
│ [+ New Watchlist]     │ Patterns Triggered: 12                               │
│ [+ New Filter]        │ Avg Confidence: 0.89                                 │
│ [Import Symbols]      │ Win Rate: 68%                                         │
│ [Export Data]         │ Best Performer: NVDA (+5.2%)                         │
│                       │ Worst: TSLA (-1.8%)                                  │
├───────────────────────┴─────────────────────────────────────────────────────────┤
│ 📈 FOCUS CHART: Auto-loads highest confidence pattern from watchlist            │
│ [Real-time updates as watchlist patterns change]                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Information Density Optimizations

### Compact Column Design
- **Symbol**: 6 chars max
- **Pattern**: Abbreviated names (WeeklyBO, BullFlag, TrendHold)
- **Confidence**: Decimal (.92) instead of stars
- **RS/Vol**: Multiplier format (1.4x, 2.1x)
- **Time**: Relative (2h, 30m, 1d) instead of timestamps
- **Price**: Current price only, change in separate column

### Visual Efficiency  
- **Color coding**: Green (+), Red (-), Gray (neutral) for quick scanning
- **Sortable columns**: Click any header to sort
- **Row highlighting**: Hover shows full pattern details in tooltip
- **Compact pagination**: Numbers only, no verbose text

### Mobile Responsive (768px and below)
```
┌─────────────────────────────┐
│ Pattern Scanner    [☰]     │
├─────────────────────────────┤
│ 🎛️ Filters [▼] Results: 247 │
├─────────────────────────────┤
│AAPL WeeklyBO .92 1.4x 📊   │
│$185.5 +2.3% 2hr            │
│NVDA BullFlag .95 1.6x 📊   │
│$485.7 +5.2% 1hr            │
│MSFT TrendHold .88 1.1x 📊  │
│$415.2 +0.8% 4hr            │
│[Load More...]              │
└─────────────────────────────┘
```

This design handles thousands of patterns efficiently while maintaining quick scanning and powerful filtering capabilities. The three-tab structure separates concerns clearly: universal search, market context, and personal focus.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Redesign UI for high-density pattern data display", "status": "completed", "activeForm": "Redesigning UI for high-density pattern data"}, {"content": "Create market breadth tab concept", "status": "completed", "activeForm": "Creating market breadth tab concept"}, {"content": "Design user focus/watchlist tab", "status": "completed", "activeForm": "Designing user focus/watchlist tab"}, {"content": "Update wireframe document with new layout", "status": "in_progress", "activeForm": "Updating wireframe document"}]