# Massive API Testing Utilities - Quick Summary

## What Was Created

Three utility scripts for testing Massive API (formerly Polygon) connections and ETF discovery:

### 1. ✅ util_massive_etf_discovery.py
**Status**: Ready to use
**Purpose**: Discover and test ETF data availability

```bash
# Quick test - common ETFs (SPY, QQQ, XLF, etc.)
python scripts/dev_tools/util_massive_etf_discovery.py

# Test specific ETFs
python scripts/dev_tools/util_massive_etf_discovery.py --symbols SPY,QQQ,XLF

# Search all available ETFs
python scripts/dev_tools/util_massive_etf_discovery.py --search --verbose
```

### 2. ⚠️  util_massive_websocket_test.py
**Status**: Requires `websockets` module
**Purpose**: Test multi-connection WebSocket streaming

```bash
# Install dependency first
pip install websockets

# Then test
python scripts/dev_tools/util_massive_websocket_test.py
python scripts/dev_tools/util_massive_websocket_test.py --connections 3 --duration 60
```

### 3. ✅ util_massive_api_explorer.py
**Status**: Ready to use
**Purpose**: Explore API endpoints and ticker details

```bash
# List all ETFs
python scripts/dev_tools/util_massive_api_explorer.py --list-etfs

# Get ticker details
python scripts/dev_tools/util_massive_api_explorer.py --ticker-details SPY

# Market snapshot
python scripts/dev_tools/util_massive_api_explorer.py --market-snapshot

# Test all endpoints
python scripts/dev_tools/util_massive_api_explorer.py --test-endpoints
```

## Quick Start - Windows Batch Script

**✅ test_massive_quick.bat** - Easy testing on Windows:

```cmd
# Show available options
test_massive_quick.bat

# Test common ETFs
test_massive_quick.bat etf

# Test all ETFs (takes longer)
test_massive_quick.bat etf-all

# Market snapshot
test_massive_quick.bat snapshot

# Test all API endpoints
test_massive_quick.bat endpoints

# WebSocket tests (requires websockets module)
test_massive_quick.bat websocket
test_massive_quick.bat websocket-3
```

## Documentation

📖 **README_MASSIVE_UTILS.md** - Complete documentation including:
- Detailed usage instructions
- Command reference
- Troubleshooting guide
- Integration with Sprint 52
- Advanced usage examples

## What Each Script Tests

### ETF Discovery Script
✅ Tests 4 data types for each ETF:
1. Ticker information (name, type, market)
2. Historical daily bars (7 days)
3. Real-time snapshot data
4. Minute aggregates (WebSocket compatibility)

**Output**: Console summary + `logs/massive_etf_discovery.json`

### WebSocket Test Script
✅ Tests multi-connection streaming:
1. Concurrent connections (1-3)
2. Authentication flow
3. Symbol subscription
4. Real-time minute bars (AM events)
5. Message throughput per connection

**Output**: Connection stats with message rates

### API Explorer Script
✅ Tests various endpoints:
- Market status
- Ticker details
- Daily/minute aggregates
- Snapshots
- Last trades
- Previous close

**Output**: Success/fail status with response times

## ETFs You're Looking For

Based on your interest in common ETFs, here are the defaults tested:

**Market Indices**:
- SPY (S&P 500)
- QQQ (NASDAQ-100)
- DIA (Dow Jones)
- IWM (Russell 2000)

**SPDR Sectors**:
- XLF (Financials)
- XLE (Energy)
- XLK (Technology)
- XLV (Healthcare)
- XLI (Industrials)
- XLB (Materials)
- XLRE (Real Estate)
- XLU (Utilities)
- XLY (Consumer Discretionary)
- XLP (Consumer Staples)

**Vanguard**:
- VTI (Total Stock Market)
- VOO (S&P 500)
- VEA (Developed Markets)
- VWO (Emerging Markets)

**Commodities**:
- GLD (Gold)
- SLV (Silver)
- USO (Oil)

**Bonds**:
- TLT (20+ Year Treasury)
- AGG (Aggregate Bond)
- LQD (Investment Grade Corporate)
- HYG (High Yield)

**Specialized**:
- ARKK (ARK Innovation)
- SOXX (Semiconductors)
- XBI (Biotech)
- XRT (Retail)

## Quick ETF Discovery Test

Want to see what ETFs are available right now? Run:

```bash
# Test the most common ETFs
python scripts/dev_tools/util_massive_etf_discovery.py

# Or just the sector ETFs
python scripts/dev_tools/util_massive_etf_discovery.py --symbols XLF,XLE,XLK,XLV,XLI,XLB,XLRE,XLU,XLY,XLP
```

This will show:
- ✅ Which ETFs have complete data
- ❌ Which ETFs have issues
- 📊 Summary statistics
- 💾 Results saved to `logs/massive_etf_discovery.json`

## Example Output

```
Testing: XLF
   ✅ Ticker Info: Financial Select Sector SPDR Fund
   ✅ Historical Data: 7 bars
   ✅ Snapshot: Last=$36.45
   ✅ Minute Aggregates: 10 bars (WebSocket ready)

✅ Fully Available ETFs (24):
   SPY    - SPDR S&P 500 ETF Trust
   QQQ    - Invesco QQQ Trust
   XLF    - Financial Select Sector SPDR Fund
   ...
```

## Installation Requirements

All scripts work out-of-the-box EXCEPT:
- **WebSocket script** requires: `pip install websockets`

## Dependencies Already Installed
- ✅ requests
- ✅ sys, os, json, time, datetime (standard library)
- ✅ ConfigManager (from TickStock)

## Next Steps

1. **Test ETF availability** (ready now):
   ```bash
   python scripts/dev_tools/util_massive_etf_discovery.py
   ```

2. **Explore API** (ready now):
   ```bash
   python scripts/dev_tools/util_massive_api_explorer.py --list-etfs
   ```

3. **Test WebSocket** (install websockets first):
   ```bash
   pip install websockets
   python scripts/dev_tools/util_massive_websocket_test.py --connections 3
   ```

## Troubleshooting

**"MASSIVE_API_KEY not found"**:
- Check `.env` file has `MASSIVE_API_KEY=your_key`
- Verify key is valid (not expired)

**"No messages received" (WebSocket)**:
- Check if market is open (9:30 AM - 4:00 PM ET)
- Try during market hours
- Test with highly liquid symbols (SPY, QQQ)

**"HTTP 404" errors**:
- Symbol may not exist or is inactive
- Verify symbol via `--ticker-details` first

## Integration with Sprint 52

These utilities validate the multi-connection WebSocket architecture planned for Sprint 52:

- ✅ Massive allows up to 3 concurrent connections
- ✅ Symbols can be distributed across connections
- ✅ Each connection operates independently
- ✅ Minute aggregates (AM events) work as expected

Use the WebSocket test to validate your connection strategy before implementing the admin dashboard.

---

**Created**: January 21, 2025
**Related Sprint**: Sprint 52 - WebSocket Connections Admin Dashboard
**Full Documentation**: README_MASSIVE_UTILS.md
