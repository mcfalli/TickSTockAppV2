# Sprint 58: ETF Data Collection Strategy
## CSV vs Inline Definition Decision Matrix

**Decision Rule**: Use CSV files ONLY for ETFs with >200 holdings

---

## ETFs Requiring CSV Files (>200 stocks)

### Broad Market Index ETFs
| ETF | Name | Approx Holdings | Priority |
|-----|------|----------------|----------|
| **SPY** | SPDR S&P 500 | ~503 | HIGH |
| **VOO** | Vanguard S&P 500 | ~503 | HIGH |
| **VTI** | Vanguard Total Market | ~3,500+ | HIGH |
| **IWM** | iShares Russell 2000 | ~2,000 | MEDIUM |
| **IWB** | iShares Russell 1000 | ~1,000 | MEDIUM |
| **IWV** | iShares Russell 3000 | ~2,591 | MEDIUM |

### International ETFs
| ETF | Name | Approx Holdings | Priority |
|-----|------|----------------|----------|
| **VEA** | Vanguard Developed Markets | ~3,900+ | MEDIUM |
| **VWO** | Vanguard Emerging Markets | ~5,200+ | MEDIUM |
| **IEFA** | iShares Developed Markets | ~2,700+ | LOW |
| **EEM** | iShares Emerging Markets | ~1,100+ | LOW |

### Growth/Value ETFs
| ETF | Name | Approx Holdings | Priority |
|-----|------|----------------|----------|
| **VTV** | Vanguard Value | ~330 | MEDIUM |
| **VUG** | Vanguard Growth | ~280 | MEDIUM |

**Total CSV Files Needed**: 12 (6 HIGH priority, 5 MEDIUM, 1 LOW)

**Recommendation**: Start with 6 HIGH priority files (SPY, VOO, VTI covers 99% of use cases)

---

## ETFs Using Inline Definitions (<200 stocks)

### Core Index ETFs
- **QQQ** (NASDAQ 100) - ~100 stocks - Top 100 NASDAQ companies
- **DIA** (Dow 30) - 30 stocks - Dow Jones Industrial Average

### Sector SPDR ETFs (XL Series)
- **XLK** (Technology) - ~65 stocks
- **XLF** (Financials) - ~65 stocks
- **XLV** (Healthcare) - ~65 stocks
- **XLY** (Consumer Discretionary) - ~60 stocks
- **XLI** (Industrials) - ~70 stocks
- **XLP** (Consumer Staples) - ~30 stocks
- **XLE** (Energy) - ~20 stocks
- **XLU** (Utilities) - ~30 stocks
- **XLB** (Materials) - ~30 stocks
- **XLC** (Communication Services) - ~25 stocks
- **XLRE** (Real Estate) - ~30 stocks

### Thematic ETFs
- **ARKK** (ARK Innovation) - ~30 stocks
- **BOTZ** (Robotics & AI) - ~30 stocks
- **ICLN** (Clean Energy) - ~40 stocks
- **SOXX** (Semiconductors) - ~30 stocks
- **HACK** (Cybersecurity) - ~50 stocks
- **FINX** (Fintech) - ~40 stocks
- **CLOU** (Cloud Computing) - ~45 stocks

### Bond/Fixed Income ETFs
- **AGG** (Aggregate Bond) - ~50 stocks (major holdings)
- **BND** (Total Bond Market) - ~50 stocks (major holdings)
- **TLT** (20+ Year Treasury) - ~30 stocks

**Total Inline Definitions**: ~23 ETFs

---

## Implementation Strategy

### Phase 1: CSV Collection (HIGH Priority Only)
**Collect these 6 CSV files first**:
1. SPY holdings (from SPDR/State Street)
2. VOO holdings (from Vanguard)
3. VTI holdings (from Vanguard)
4. IWM holdings (from iShares)
5. IWB holdings (from iShares)
6. IWV holdings (from iShares)

**Where to Get**:
- **iShares**: https://www.ishares.com/us/products/etf-investments (search ticker → Holdings tab → Download)
- **Vanguard**: https://investor.vanguard.com/investment-products/etfs (search ticker → Portfolio & Management → Holdings)
- **SPDR**: https://www.ssga.com/us/en/individual/etfs (search ticker → Holdings → Download)

### Phase 2: Inline Definitions in Code
Update `load_etf_holdings.py` to include hardcoded holdings for smaller ETFs.

**Example Code Structure**:
```python
INLINE_ETF_HOLDINGS = {
    "QQQ": {
        "name": "Invesco QQQ Trust",
        "holdings": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST", ...],
        "market_cap_threshold": 5000000000,
        "data_source": "inline_definition",
        "last_updated": "2025-12-10"
    },
    "DIA": {
        "name": "SPDR Dow Jones Industrial Average ETF",
        "holdings": ["UNH", "GS", "MSFT", "HD", "CAT", "MCD", "AMGN", "V", ...],
        "market_cap_threshold": 5000000000,
        "data_source": "inline_definition",
        "last_updated": "2025-12-10"
    },
    # ... more inline definitions
}
```

### Phase 3: Sector ETFs (Medium Priority)
Define XL series sector ETFs inline using top holdings (20-70 stocks each).

---

## Prioritized Action Plan

### Step 1: Update load_etf_holdings.py
Add inline holdings support:
```python
def _load_inline_holdings(self):
    """Load ETF holdings defined inline in code"""
    for etf_symbol, etf_data in INLINE_ETF_HOLDINGS.items():
        # Insert into cache_entries as etf_holdings type
        ...
```

### Step 2: Define Top 3 Inline ETFs First
Start with the most important small ETFs:
1. **QQQ** (NASDAQ 100) - ~100 stocks
2. **DIA** (Dow 30) - 30 stocks
3. **XLK** (Technology) - ~65 stocks

**I can generate the exact symbol lists for these if you want me to research the current holdings.**

### Step 3: Collect 3 Critical CSV Files
Focus on the big ones:
1. **SPY** - S&P 500 (503 stocks)
2. **VTI** - Total Market (3,500+ stocks)
3. **IWM** - Russell 2000 (2,000 stocks)

This covers:
- ✅ Large cap (SPY)
- ✅ Total market (VTI)
- ✅ Small cap (IWM)
- ✅ Tech focused (QQQ inline)
- ✅ Blue chip (DIA inline)

---

## Storage Estimate

### CSV Files (6 files)
- SPY: ~503 rows × 100 bytes = ~50 KB
- VOO: ~503 rows × 100 bytes = ~50 KB
- VTI: ~3,500 rows × 100 bytes = ~350 KB
- IWM: ~2,000 rows × 100 bytes = ~200 KB
- IWB: ~1,000 rows × 100 bytes = ~100 KB
- IWV: ~2,591 rows × 100 bytes = ~260 KB
**Total**: ~1 MB

### Inline Code (23 ETFs)
- Average 40 stocks × 23 ETFs = ~920 stock symbols
- Estimate: ~30 KB of Python code
**Total**: ~30 KB

### Database Storage
- `etf_holdings` entries: 29 rows (6 CSV + 23 inline)
- Average JSONB size: ~10 KB per entry
**Total**: ~290 KB in cache_entries table

---

## Next Steps

**Option A: Start Small (Recommended)**
1. I update `load_etf_holdings.py` to support inline definitions
2. I define QQQ, DIA, XLK inline (3 ETFs, ~195 stocks total)
3. You collect SPY.csv only (503 stocks)
4. We test with 4 ETFs, validate relationships
5. Expand incrementally

**Option B: Go Big**
1. You collect all 6 HIGH priority CSV files
2. I define all 23 inline ETFs at once
3. Load everything in one shot
4. Validate 29 ETFs total

**Which approach do you prefer?**

I can also research and provide the exact current holdings for QQQ, DIA, and XLK if you want to start with Option A right now.
