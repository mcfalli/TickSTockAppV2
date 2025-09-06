# Pattern Discovery Dashboard - Detailed Wireframes

**Date**: 2025-09-04  
**Sprint**: 18 - Planning Phase  
**Status**: Visual Design Specification - REVISED for Data Density  

## REVISED APPROACH: High-Density Data Tables

**Key Changes Based on Feedback:**
- Replaced visual cards with dense tabular data for scanning efficiency
- Consolidated three processing tiers into unified "Pattern Scanner" tab
- Added "Market Breadth" tab for index/ETF analysis  
- Added "My Focus" tab for personal watchlists and saved filters
- Emphasized information density over visual polish

## Desktop Layout Wireframes  

### Tab 1: Pattern Scanner (Unified High-Density View)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TickStock.ai                                         🔍 Search   👤 Profile    │
├─────────────────────────────────────────────────────────────────────────────────┤
│           [Pattern Scanner*] [Market Breadth] [My Focus]                        │
├───────────────┬─────────────────────────────────────────────────────────────────┤
│ 🎛️ FILTERS     │          DENSE PATTERN TABLE - 1,247 found                  │
│ [Collapsible]  │                                                             │
│               │ Symbol│Pattern    │Conf│ RS │Vol│Price │Chg │Time│Exp │Chart │
│ PATTERN TYPE  │ AAPL  │WeeklyBO   │.92 │1.4x│2.1│185.50│+2.3│2h  │3d  │ 📊  │
│ ☑ Breakouts   │ NVDA  │BullFlag   │.95 │1.6x│3.2│485.75│+5.2│1h  │2d  │ 📊  │
│ ☑ Volume      │ MSFT  │TrendHold  │.88 │1.1x│1.8│415.25│+0.8│4h  │1d  │ 📊  │
│ ☑ Trendlines  │ TSLA  │VolSpike   │.94 │1.2x│4.2│242.85│+3.8│2m  │4h  │ 📊  │
│ ☐ Gaps        │ AMD   │Reversal   │.87 │1.3x│2.8│152.30│+1.9│30m │2h  │ 📊  │
│ ☐ Reversals   │ GOOGL │GapFill    │.91 │0.9x│1.6│138.25│-0.3│12m │1h  │ 📊  │
│               │ AMZN  │MomShift   │.89 │1.1x│1.9│145.80│+1.1│8m  │45m │ 📊  │
│ TIMEFRAME     │ NFLX  │Support    │.86 │0.8x│1.3│485.60│-0.5│1d  │7d  │ 📊  │
│ ● All         │ [... 20 more visible rows ...]                             │
│ ○ Daily       │ ┌─────────────────────────────────────────────────────────┐ │
│ ○ Intraday    │ │ Page: [1] 2 3 4 5 ... 42    Show: [30▼] per page      │ │
│ ○ Combo       │ │ Export: [CSV] [JSON]    Auto-refresh: [ON▼] 30s         │ │
│               │ └─────────────────────────────────────────────────────────┘ │
│ INDICATORS    │                                                             │
│ RS > [1.0▼]   │                                                             │
│ Vol> [1.5▼]   │                                                             │
│ RSI  [30-70]  │                                                             │
│               │                                                             │
│ CONFIDENCE    │                                                             │
│ ●●●○ > 0.85   │                                                             │
│ ●●○○ > 0.70   │                                                             │
│ ●○○○ > 0.50   │                                                             │
│               │                                                             │
│ SYMBOLS       │                                                             │
│ 🔍 Search...  │                                                             │
│ ☐ Tech        │                                                             │
│ ☐ Healthcare  │                                                             │
│ ☐ Finance     │                                                             │
│               │                                                             │
│ TIME RANGE    │                                                             │
│ ● Last 4hrs   │                                                             │
│ ○ Today       │                                                             │
│ ○ 3 days      │                                                             │
│               │                                                             │
├───────────────┴─────────────────────────────────────────────────────────────────┤
│ 📈 CHART: Click any table row to load • Currently: AAPL Weekly Breakout       │
│                                                                                 │
│ $190 ┐                                                    🏷️ Weekly Breakout   │
│      │        ▲ Pattern Trigger                            Level: $180.25      │
│ $185 │     ┌──█──┐                                         Confidence: 0.92    │
│      │    ▐     ▌  ██                                     Target: $195.00      │
│ $180 │ ───▐─────▌──██─── ← Breakout Level                Stop: $178.50         │
│      │   ▐       ▌  ▐                                                          │
│ $175 │  ▐         ▌ ▐                                                          │
│      └──────────────────────────────────────────────────                      │
│        Apr 1    Apr 8    Apr 15   Apr 22                                       │
│                                                                                 │
│ Volume 📊  RSI(14) 📈  Rel.Strength 📊                                         │
│ ████ █ ██ ████ █       70 ▲                1.4x ████████▲                     │
│ ████ ████ ████ ████    50 ─────────        1.0x ────────────                  │
│ ██████████████ ████    30 ▼                0.5x                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Intraday Signals Tab View
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TickStock.ai                                         🔍 Search   👤 Profile    │
├─────────────────────────────────────────────────────────────────────────────────┤
│           [Daily Patterns] [Intraday Signals*] [Combo Alerts]                  │
├───────────────┬─────────────────────────────────────────────────┬───────────────┤
│               │                                                 │               │
│ 🎛️ FILTERS     │  ⚡ INTRADAY SIGNALS (156 active)              │ 🔴 LIVE FEED  │
│               │  🔄 Auto-refresh: ON • Last update: 11:42:13    │               │
│ Signal Types  │                                                 │ 🟢 New Signal │
│ ☑️ Vol Spike   │  ┌─────────────────┐ ┌─────────────────┐       │ AAPL Vol     │
│ ☑️ Momentum    │  │ TSLA  ⚡ LIVE   │ │ AAPL  🔥 HOT    │       │ 3.1x @ 11:42  │
│ ☑️ Gap Play    │  │ Volume Explosion│ │ Momentum Shift  │       │               │
│ ☐ Reversal    │  │ $242.85 (+3.8%) │ │ $185.75 (+2.1%) │       │ 🟢 New Signal │
│               │  │ ⭐ 0.94 | 4.2x   │ │ ⭐ 0.89 | 2.3x   │       │ NVDA Gap Fill │
│ RSI Filter    │  │ RSI: 78 (Hot!)  │ │ RSI: 68 (Strong)│       │ 95% complete  │
│ ●●○ >70       │  │ [📈▃▆█▆▅▃▂]    │ │ [📈▂▃▅▇█▅▃]    │       │               │
│ ○○○ 30-70     │  │ 🕐 2m ago       │ │ 🕐 5m ago       │       │ 🟡 Updated    │
│ ○○○ <30       │  └─────────────────┘ └─────────────────┘       │ MSFT Signal   │
│               │                                                 │ Strength +15% │
│ Volume Filter │  ┌─────────────────┐ ┌─────────────────┐       │               │
│ >2.0x ▲       │  │ MSFT  📊        │ │ GOOGL 🎯        │       │ ⏰ Pattern    │
│ >1.5x ●       │  │ Breakout Setup  │ │ Gap Fill        │       │ Expirations   │
│ >1.0x ○       │  │ $415.50 (+1.2%) │ │ $138.25 (-0.3%) │       │ (Next 30min)  │
│               │  │ ⭐ 0.91 | 1.9x   │ │ ⭐ 0.87 | 1.6x   │       │ • NVDA (2m)   │
│ Time Frame    │  │ RSI: 65         │ │ RSI: 45         │       │ • AMD (12m)   │
│ ● 5 minutes   │  │ [📈▅▆▅▆▇▆▅]    │ │ [📈▆▅▄▃▄▅▆]    │       │ • TSLA (28m)  │
│ ○ 15 minutes  │  │ 🕐 8m ago       │ │ 🕐 12m ago      │       │               │
│ ○ 30 minutes  │  └─────────────────┘ └─────────────────┘       │               │
└───────────────┴─────────────────────────────────────────────────┴───────────────┘
```

### Combo Alerts Tab - Multi-Timeframe View
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TickStock.ai                                         🔍 Search   👤 Profile    │
├─────────────────────────────────────────────────────────────────────────────────┤
│           [Daily Patterns] [Intraday Signals] [Combo Alerts*]                  │
├───────────────┬─────────────────────────────────────────────────┬───────────────┤
│               │                                                 │               │
│ 🎛️ FILTERS     │  🔥 COMBO ALERTS (8 high-conviction setups)    │ 🔴 LIVE FEED  │
│               │                                                 │               │
│ Combo Types   │  ┌─────────────────────────────────────┐       │ 🟢 New Combo  │
│ ☑️ Daily+Intra │  │ AAPL  🎯 PERFECT SETUP             │       │ MSFT Daily    │
│ ☑️ Multi-TF    │  │ Daily Breakout + Intraday Volume   │       │ Flag + Volume │
│ ☐ Sector Play │  │ $185.50 (+2.3%) • RS: 1.4x        │       │ Confirmation  │
│               │  │ ⭐⭐⭐ 0.96 Confidence               │       │               │
│ Strength      │  │                                     │       │ 🟡 Alert      │
│ RS: >1.2 ●    │  │ 📅 Daily: Weekly Breakout (2hrs)   │       │ NVDA Combo    │
│ RS: >1.0 ○    │  │ ⚡ Intraday: Volume Confirm (5m)   │       │ Pattern Risk  │
│               │  │ 🎯 Entry: $184.75 • Target: $195   │       │ Level Broken  │
│ Priority      │  │ [View Daily] [View Intraday] [📊]  │       │               │
│ ●●● High      │  └─────────────────────────────────────┘       │               │
│ ●○○ Medium    │                                                 │               │
│ ○○○ Low       │  ┌─────────────────────────────────────┐       │               │
│               │  │ NVDA  ⚡ MOMENTUM COMBO             │       │               │
│ Watchlists    │  │ Daily Bull Flag + RSI Breakout     │       │               │
│ 📁 My Combos  │  │ $485.75 (+5.2%) • RS: 1.6x        │       │               │
│ 📁 High Prob  │  │ ⭐⭐ 0.93 Confidence                │       │               │
│ 📁 Breakouts  │  │                                     │       │               │
│               │  │ 📅 Daily: Bull Flag Setup (4hrs)   │       │               │
│               │  │ ⚡ Intraday: RSI Break >70 (2m)    │       │               │
│               │  │ 🎯 Entry: $482.50 • Target: $510   │       │               │
│               │  │ [View Setup] [Set Alert] [📊]      │       │               │
│               │  └─────────────────────────────────────┘       │               │
└───────────────┴─────────────────────────────────────────────────┴───────────────┘
```

## Mobile/Tablet Responsive Views

### Tablet Layout (768px - 1024px)
```
┌─────────────────────────────────────────────┐
│ TickStock.ai              🔍  👤  ☰       │
├─────────────────────────────────────────────┤
│ [Daily] [Intraday] [Combo]          🎛️     │
├─────────────────────────────────────────────┤
│                                             │
│ 📊 PATTERN RESULTS (Filters Collapsed)     │
│                                             │
│ ┌─────────────────┐ ┌─────────────────┐   │
│ │ AAPL  📈        │ │ MSFT  📊        │   │
│ │ Weekly Breakout │ │ Trendline Hold  │   │
│ │ $185.50 (+2.3%) │ │ $415.25 (+0.8%) │   │
│ │ ⭐ 0.92 | RS:1.4x│ │ ⭐ 0.88 | RS:1.1x│   │
│ └─────────────────┘ └─────────────────┘   │
│                                             │
│ ┌─────────────────┐ ┌─────────────────┐   │
│ │ NVDA  🚀        │ │ AMD   ⚡        │   │
│ │ Bull Flag       │ │ Volume Surge    │   │
│ │ $485.75 (+5.2%) │ │ $152.30 (+1.9%) │   │
│ │ ⭐ 0.95 | RS:1.6x│ │ ⭐ 0.91 | RS:1.2x│   │
│ └─────────────────┘ └─────────────────┘   │
│                                             │
├─────────────────────────────────────────────┤
│ 📈 CHART - AAPL                            │
│ ┌─────────────────────────────────────────┐ │
│ │ $190 ┐                                  │ │
│ │      │     ▲ Breakout                   │ │
│ │ $185 │  ┌──█──┐                         │ │
│ │      │ ▐     ▌  ██                     │ │
│ │ $180 │───▐───▌──██──                   │ │
│ │      └─────────────────                │ │
│ │ Vol: ████ █ ██ ████ █                  │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Mobile Layout (≤767px)
```
┌─────────────────────────────────┐
│ TickStock  🔍  👤  ☰           │
├─────────────────────────────────┤
│ Daily  Intraday  Combo    🎛️    │
├─────────────────────────────────┤
│                                 │
│ 📊 PATTERNS (23)      [Sort ▼] │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ AAPL  📈 Weekly Breakout    │ │
│ │ $185.50 (+2.3%) • ⭐ 0.92   │ │
│ │ RS:1.4x Vol:2.1x • 2hrs ago │ │
│ │ [📈▁▂▃▅▆█▅]                 │ │
│ │ [👁️ View] [⭐ Watch] [📊]    │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ NVDA  🚀 Bull Flag          │ │
│ │ $485.75 (+5.2%) • ⭐ 0.95   │ │
│ │ RS:1.6x Vol:3.2x • 1hr ago  │ │
│ │ [📈▃▅▆█▆▅▃]                 │ │
│ │ [👁️ View] [⭐ Watch] [📊]    │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Load More... (19 remaining) │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

## Interactive Elements & States

### Pattern Card Interactions
```
Normal State:
┌─────────────────┐
│ AAPL  📈        │
│ Weekly Breakout │
│ $185.50 (+2.3%) │
│ ⭐ 0.92 | RS:1.4x│
│ [📈▁▂▃▅▆█▅]    │
│ 2hrs ago        │
└─────────────────┘

Hover State:
┌─────────────────┐ ← Elevated shadow
│ AAPL  📈    [↗️] │ ← External link icon
│ Weekly Breakout │
│ $185.50 (+2.3%) │
│ ⭐ 0.92 | RS:1.4x│ ← Highlighted
│ [📈▁▂▃▅▆█▅]    │
│ 2hrs ago        │
│ ┌─────────────┐ │ ← Action overlay
│ │[👁️][⭐][📊][🔔]│ │   View/Watch/Chart/Alert
│ └─────────────┘ │
└─────────────────┘

Selected State:
┌═════════════════┐ ← Thick blue border
│ AAPL  📈    [✓] │ ← Checkmark
│ Weekly Breakout │
│ $185.50 (+2.3%) │ ← Blue highlighted text
│ ⭐ 0.92 | RS:1.4x│
│ [📈▁▂▃▅▆█▅]    │ ← Blue sparkline
│ 2hrs ago        │
└═════════════════┘
```

### Filter Panel Interactions
```
Collapsed State (Mobile/Tablet):
┌─────────────────────┐
│ 🎛️ Filters (5)  [▼] │
└─────────────────────┘

Expanded State:
┌─────────────────────┐
│ 🎛️ Filters     [▲] │
├─────────────────────┤
│ Pattern Types       │
│ ☑️ Breakouts (12)   │
│ ☑️ Volume (8)       │
│ ☐ Trendlines (3)    │
│                     │
│ Relative Strength   │
│ ●────●──────○  1.4x │
│ 1.0   1.2    2.0    │
│                     │
│ [Apply] [Reset]     │
└─────────────────────┘
```

### Chart Panel States
```
Loading State:
┌─────────────────────────────────┐
│ 📈 Loading chart data...        │
│         ⏳ Please wait          │
│                                 │
│     [Spinner Animation]         │
└─────────────────────────────────┘

Error State:
┌─────────────────────────────────┐
│ 📈 Chart unavailable            │
│     ❌ Data not found           │
│                                 │
│     [Retry] [Report Issue]      │
└─────────────────────────────────┘

Full Chart State:
┌─────────────────────────────────┐
│ 📈 AAPL - Weekly Breakout       │
│ [D][H4][H1][15m][5m] 🔄 Live   │
│ ┌─────────────────────────────┐ │
│ │    Pattern annotations      │ │
│ │    with price levels        │ │
│ │    and volume indicators    │ │
│ └─────────────────────────────┘ │
│ [Zoom] [Indicators] [Export]    │
└─────────────────────────────────┘
```

## Key Design Principles

### Visual Hierarchy
1. **Primary Actions**: Bright colors (blue/green) for view/watch buttons
2. **Secondary Info**: Muted colors for timestamps, metadata
3. **Alert States**: Red for warnings, orange for expiring patterns
4. **Success States**: Green for active patterns, completed setups

### Data Visualization
1. **Sparklines**: Mini charts in pattern cards for quick visual context
2. **Confidence Indicators**: Star ratings (⭐⭐⭐) for pattern strength
3. **Volume Bars**: Height-coded volume with color intensity
4. **Status Icons**: Emoji-based quick recognition (📈📊⚡🚀🎯)

### Performance Considerations
1. **Lazy Loading**: Load chart data only when pattern selected
2. **Virtual Scrolling**: Handle 1000+ patterns without performance hit  
3. **Debounced Filters**: 300ms delay before applying filter changes
4. **Cached Queries**: Redis cache for repeated pattern lookups

This wireframe provides the detailed visual specification needed to implement the pattern discovery dashboard with clear user experience flows and technical implementation guidance.