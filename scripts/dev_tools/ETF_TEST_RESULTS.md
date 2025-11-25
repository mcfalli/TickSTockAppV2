# Massive API ETF Availability Test Results

**Test Date**: January 21, 2025
**API Endpoint**: `https://api.massive.com/v1/open-close/{SYMBOL}/{DATE}`
**Test Data Date**: 2023-01-09 (confirmed working)

## ✅ All 15 ETFs Tested Successfully

### Market Indices (4/4 available)
| Symbol | Name | Close Price | Volume | Status |
|--------|------|-------------|--------|--------|
| **SPY** | SPDR S&P 500 ETF Trust | $387.86 | 73.9M | ✅ Available |
| **QQQ** | Invesco QQQ Trust (NASDAQ-100) | $270.54 | 45.6M | ✅ Available |
| **DIA** | SPDR Dow Jones Industrial Average ETF | $335.29 | 3.9M | ✅ Available |
| **IWM** | iShares Russell 2000 ETF | $177.88 | 18.4M | ✅ Available |

### SPDR Sector ETFs (5/5 available)
| Symbol | Name | Close Price | Volume | Status |
|--------|------|-------------|--------|--------|
| **XLF** | Financial Select Sector SPDR Fund | $35.25 | 48.7M | ✅ Available |
| **XLE** | Energy Select Sector SPDR Fund | $87.25 | 23.0M | ✅ Available |
| **XLK** | Technology Select Sector SPDR Fund | $126.18 | 10.7M | ✅ Available |
| **XLV** | Health Care Select Sector SPDR Fund | $133.40 | 7.7M | ✅ Available |
| **XLI** | Industrial Select Sector SPDR Fund | $100.46 | 12.8M | ✅ Available |

### Commodities (2/2 available)
| Symbol | Name | Close Price | Volume | Status |
|--------|------|-------------|--------|--------|
| **GLD** | SPDR Gold Trust | $174.10 | 5.1M | ✅ Available |
| **SLV** | iShares Silver Trust | $21.74 | 15.6M | ✅ Available |

### Fixed Income (1/1 available)
| Symbol | Name | Close Price | Volume | Status |
|--------|------|-------------|--------|--------|
| **TLT** | iShares 20+ Year Treasury Bond ETF | $105.74 | 21.5M | ✅ Available |

### Equal Weight ETFs (3/3 available)
| Symbol | Name | Close Price | Volume | Status |
|--------|------|-------------|--------|--------|
| **RSP** | Invesco S&P 500 Equal Weight | $145.29 (2023) | 2.7M | ✅ Available |
| **RSPD** | Invesco S&P 500 Equal Weight Dividend | $46.60 (2024) | 159K | ✅ Available (2024+ launch) |
| **RSPS** | Invesco S&P 500 Equal Weight Consumer Staples | $31.655 (2024) | 1.26M | ✅ Available (2024+ launch) |

**Note**: RSPD and RSPS are newer ETFs launched in 2024. When testing:
- RSP: Use `2023-01-09` or any date
- RSPD, RSPS: Use `2024-01-09` or later (returns `NOT_FOUND` for 2023 dates)

## Additional SPDR Sectors (Not Yet Tested)

These are highly likely to be available based on the pattern:

- **XLB** - Materials Select Sector SPDR Fund
- **XLRE** - Real Estate Select Sector SPDR Fund
- **XLU** - Utilities Select Sector SPDR Fund
- **XLY** - Consumer Discretionary Select Sector SPDR Fund
- **XLP** - Consumer Staples Select Sector SPDR Fund

## Test Command Pattern

```bash
# Test any ETF symbol
curl -s "https://api.massive.com/v1/open-close/{SYMBOL}/2023-01-09?adjusted=true&apiKey=YOUR_KEY"
```

### Example Response (Success)
```json
{
  "status": "OK",
  "from": "2023-01-09",
  "symbol": "SPY",
  "open": 390.37,
  "high": 393.7,
  "low": 387.67,
  "close": 387.86,
  "volume": 73978071,
  "afterHours": 387.15,
  "preMarket": 388.37
}
```

## Python Test Script Issues

⚠️ **Note**: The Python test scripts (`util_massive_etf_discovery.py`, `util_massive_websocket_test.py`) currently fail due to:
1. Python 3.13 SSL recursion bug
2. Unicode character encoding issues on Windows console

**Workaround**: Use `curl` commands directly (shown above) or the batch script.

## Working Test Methods

### ✅ Method 1: Direct curl (RECOMMENDED)
```bash
curl -s "https://api.massive.com/v1/open-close/SPY/2023-01-09?adjusted=true&apiKey=YOUR_KEY"
```

### ✅ Method 2: Batch script
```cmd
test_etfs_curl.bat
```

### ❌ Method 3: Python scripts (Currently broken on Python 3.13)
```bash
python scripts/dev_tools/util_massive_etf_quick_test.py   # SSL recursion error
```

## Summary

✅ **Success Rate**: 15/15 (100%)
✅ **Market Indices**: All major indices available (SPY, QQQ, DIA, IWM)
✅ **Sector ETFs**: All tested SPDR sectors available
✅ **Commodities**: Gold and Silver ETFs available
✅ **Bonds**: Treasury bond ETF available
✅ **Equal Weight**: RSP family available (including 2024 launches)

## Recommendations for Sprint 52

1. **Use these 15 confirmed ETFs** for initial WebSocket dashboard testing
2. **Primary connection** could focus on: SPY, QQQ, DIA, IWM (market indices)
3. **Secondary connection** could handle: XLF, XLE, XLK, XLV, XLI (sectors)
4. **Tertiary connection** could monitor: GLD, SLV, TLT, RSP (commodities/bonds/equal-weight)

## Next Steps

1. ✅ **Confirmed ETF availability** via Massive API
2. ⏳ **WebSocket testing** - Need to resolve Python 3.13 SSL issue OR use Node.js/JavaScript for WebSocket tests
3. ⏳ **Sprint 52 implementation** - Build admin dashboard with these confirmed ETFs

## Alternative: WebSocket Testing with JavaScript

Since Python 3.13 has SSL issues, consider testing WebSocket with Node.js:

```javascript
// Quick WebSocket test (Node.js)
const WebSocket = require('ws');
const ws = new WebSocket('wss://socket.massive.com/stocks');

ws.on('open', function open() {
    ws.send(JSON.stringify({action: 'auth', params: 'YOUR_API_KEY'}));
    ws.send(JSON.stringify({action: 'subscribe', params: 'AM.SPY,AM.QQQ,AM.XLF'}));
});

ws.on('message', function incoming(data) {
    console.log(data.toString());
});
```

---

**Test Completed**: January 21, 2025
**Python Version**: 3.13 (has SSL recursion bug)
**curl Version**: Working perfectly
**ETF Success Rate**: 100% (15/15)
**Latest Additions**: RSP, RSPD, RSPS (equal weight ETFs)
