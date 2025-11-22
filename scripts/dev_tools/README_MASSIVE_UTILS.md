# Massive API Testing Utilities

Comprehensive testing utilities for exploring and validating Massive API (formerly Polygon) connections, ETF discovery, and multi-connection WebSocket testing.

## Overview

Three specialized utilities for testing different aspects of Massive API:

1. **util_massive_etf_discovery.py** - Discover and validate ETF data availability
2. **util_massive_websocket_test.py** - Test multi-connection WebSocket streaming
3. **util_massive_api_explorer.py** - Interactive API endpoint explorer

## Prerequisites

- Python 3.10+
- `MASSIVE_API_KEY` configured in `.env` file
- Dependencies: `requests`, `websockets`, `asyncio`

## Quick Start

### 1. ETF Discovery

Find all available ETFs and test their data availability:

```bash
# Discover all available ETFs via API
python scripts/dev_tools/util_massive_etf_discovery.py --search

# Test common ETFs (SPY, QQQ, XLF, etc.)
python scripts/dev_tools/util_massive_etf_discovery.py

# Test specific ETFs
python scripts/dev_tools/util_massive_etf_discovery.py --symbols SPY,QQQ,XLF,XLE,GLD

# Verbose output with detailed data
python scripts/dev_tools/util_massive_etf_discovery.py --verbose
```

**What it tests:**
- Ticker information availability
- Historical daily data (7 days)
- Real-time snapshot data
- Minute aggregates (WebSocket compatibility)

**Output:**
- Console summary with pass/fail per ETF
- JSON results saved to `logs/massive_etf_discovery.json`

### 2. WebSocket Multi-Connection Testing

Test multiple concurrent WebSocket connections (Sprint 52 requirement):

```bash
# Test single connection (default)
python scripts/dev_tools/util_massive_websocket_test.py

# Test 3 concurrent connections
python scripts/dev_tools/util_massive_websocket_test.py --connections 3

# Custom symbols and duration
python scripts/dev_tools/util_massive_websocket_test.py \
    --connections 3 \
    --symbols SPY,QQQ,XLF,XLE,XLK,XLV,XLI,DIA,IWM,GLD \
    --duration 60

# Verbose mode (show all messages)
python scripts/dev_tools/util_massive_websocket_test.py --connections 3 --verbose
```

**What it tests:**
- Concurrent WebSocket connections (up to 3)
- Authentication and subscription flow
- Real-time minute aggregate (AM) messages
- Message throughput per connection
- Symbol distribution across connections

**Output:**
- Connection stats per WebSocket
- Total messages and bars received
- Message rate (msgs/sec)
- Symbols seen per connection

**Key Metrics:**
- Messages received per connection
- Bars received (minute aggregates)
- Unique symbols seen
- Message rate (msgs/sec)
- Error counts

### 3. API Endpoint Explorer

Interactive tool for exploring Massive API capabilities:

```bash
# List all available ETFs
python scripts/dev_tools/util_massive_api_explorer.py --list-etfs

# Get detailed ticker info
python scripts/dev_tools/util_massive_api_explorer.py --ticker-details SPY

# Market snapshot for common ETFs
python scripts/dev_tools/util_massive_api_explorer.py --market-snapshot

# Market snapshot for specific symbols
python scripts/dev_tools/util_massive_api_explorer.py --market-snapshot --symbols SPY,QQQ,GLD

# Test all API endpoints
python scripts/dev_tools/util_massive_api_explorer.py --test-endpoints

# Test endpoints with specific symbol
python scripts/dev_tools/util_massive_api_explorer.py --test-endpoints --symbols AAPL

# Save results to JSON
python scripts/dev_tools/util_massive_api_explorer.py --list-etfs --save results.json
```

**What it tests:**
- Market status endpoint
- Ticker details (v3 reference API)
- Daily aggregates
- Minute aggregates
- Snapshot data
- Last trade
- Previous close
- Ticker types listing

**Output:**
- Structured data per endpoint
- Success/failure status
- Response times
- Sample data (with --verbose)

## Common Use Cases

### Sprint 52: WebSocket Dashboard Preparation

Test 3-connection WebSocket setup with different symbol groups:

```bash
# Test primary ETFs on connection 1
python scripts/dev_tools/util_massive_websocket_test.py \
    --connections 1 \
    --symbols SPY,QQQ,DIA,IWM \
    --duration 30

# Test sector ETFs distributed across 3 connections
python scripts/dev_tools/util_massive_websocket_test.py \
    --connections 3 \
    --symbols XLF,XLE,XLK,XLV,XLI,XLB,XLRE,XLU,XLY,XLP \
    --duration 60 \
    --verbose
```

### ETF Universe Validation

Validate which ETFs are available and have complete data:

```bash
# Search and test all ETFs
python scripts/dev_tools/util_massive_etf_discovery.py --search --verbose

# Test specific sector ETFs
python scripts/dev_tools/util_massive_etf_discovery.py \
    --symbols XLF,XLE,XLK,XLV,XLI,XLB,XLRE,XLU,XLY,XLP
```

### API Capability Assessment

Understand what data is available:

```bash
# Test all endpoints with SPY
python scripts/dev_tools/util_massive_api_explorer.py --test-endpoints

# Get detailed info for multiple symbols
for symbol in SPY QQQ XLF XLE; do
    python scripts/dev_tools/util_massive_api_explorer.py --ticker-details $symbol
done
```

## Output Files

All utilities can save results:

- `logs/massive_etf_discovery.json` - ETF discovery results
- Custom JSON output with `--save` flag

Example:
```bash
python scripts/dev_tools/util_massive_api_explorer.py \
    --list-etfs \
    --save logs/all_etfs.json
```

## Interpreting Results

### ETF Discovery

**Fully Available ETF:**
```
SPY:
   ✅ Ticker Info: SPDR S&P 500 ETF Trust
   ✅ Historical Data: 7 bars
   ✅ Snapshot: Last=$450.23
   ✅ Minute Aggregates: 10 bars (WebSocket ready)
```

**Problematic ETF:**
```
XYZ:
   ✅ Ticker Info: XYZ ETF
   ❌ Historical Data: No bars
   ❌ Snapshot: HTTP 404
   ❌ Minute Aggregates: HTTP 404
```

### WebSocket Test

**Successful Connection:**
```
Connection 1:
  Connected at:      14:23:45
  Last message at:   14:24:45
  Messages received: 156
  Bars received:     156
  Symbols seen:      5 - DIA, IWM, QQQ, SPY, XLF
  Message rate:      2.60 msgs/sec
```

**Connection Issues:**
```
Connection 2:
  Messages received: 0
  Errors:            1
```

### API Explorer

**Successful Endpoint:**
```
Testing: Daily Aggregates
Endpoint: /v2/aggs/ticker/SPY/range/1/day/2025-01-14/2025-01-21
✅ SUCCESS (0.345s)
Results count: 7
```

## Troubleshooting

### No Messages Received (WebSocket)

**Possible causes:**
- Market is closed (WebSocket only streams during market hours)
- Symbols don't have active trading
- API key lacks WebSocket permissions

**Solutions:**
- Run during market hours (9:30 AM - 4:00 PM ET)
- Test with highly liquid symbols (SPY, QQQ)
- Verify API subscription includes WebSocket access

### HTTP 404 Errors

**Causes:**
- Symbol doesn't exist or is inactive
- Wrong market (ensure `market=stocks`)
- ETF not in Massive database

**Solutions:**
- Verify symbol exists via `--ticker-details`
- Check if symbol is active
- Try alternate symbol format

### Rate Limiting

**Symptoms:**
- HTTP 429 errors
- Slow responses
- Connection timeouts

**Solutions:**
- All utilities include rate limiting delays
- Reduce concurrent requests
- Upgrade API subscription tier

### API Key Issues

**Error:**
```
❌ ERROR: MASSIVE_API_KEY not found in configuration
```

**Solution:**
```bash
# Add to .env file
echo "MASSIVE_API_KEY=your_api_key_here" >> .env

# Verify it loads
python -c "from src.core.services.config_manager import ConfigManager; cm = ConfigManager(); cm.load_from_env(); print(cm.get_config().get('MASSIVE_API_KEY')[-4:])"
```

## Advanced Usage

### Batch Testing Multiple Symbol Sets

```bash
# Test different ETF categories
python scripts/dev_tools/util_massive_etf_discovery.py --symbols SPY,QQQ,DIA,IWM > logs/broad_market.txt
python scripts/dev_tools/util_massive_etf_discovery.py --symbols XLF,XLE,XLK,XLV > logs/sectors.txt
python scripts/dev_tools/util_massive_etf_discovery.py --symbols GLD,SLV,USO > logs/commodities.txt
```

### Continuous WebSocket Monitoring

```bash
# Long-duration test (5 minutes)
python scripts/dev_tools/util_massive_websocket_test.py \
    --connections 3 \
    --duration 300 \
    --verbose \
    2>&1 | tee logs/websocket_test_$(date +%Y%m%d_%H%M%S).log
```

### Compare Single vs Multi-Connection

```bash
# Single connection baseline
python scripts/dev_tools/util_massive_websocket_test.py \
    --connections 1 \
    --symbols SPY,QQQ,XLF,XLE,XLK \
    --duration 60

# Three connections (same symbols)
python scripts/dev_tools/util_massive_websocket_test.py \
    --connections 3 \
    --symbols SPY,QQQ,XLF,XLE,XLK \
    --duration 60
```

## Integration with TickStock

These utilities validate the multi-connection architecture planned for Sprint 52.

**Key validations:**
1. **Connection Limits**: Massive allows up to 3 concurrent WebSocket connections
2. **Symbol Distribution**: Symbols can be split across connections
3. **Independent Streams**: Each connection operates independently
4. **Data Format**: Minute aggregates (AM events) are consistent

**Next Steps:**
1. Use discovery results to populate universe keys
2. Use WebSocket tests to validate throughput capacity
3. Use API explorer to understand data structure for dashboard display

## Related Documentation

- **Sprint 52 Plan**: `docs/planning/sprints/sprint52/README.md`
- **WebSocket Architecture**: `docs/architecture/websocket-integration.md`
- **Configuration Guide**: `docs/guides/configuration.md`
- **Massive API Docs**: https://massive.com/docs/

## Command Reference

### util_massive_etf_discovery.py

```
Options:
  --symbols SYMBOLS   Comma-separated ETF symbols (default: common ETFs)
  --search            Search for all available ETFs via API
  --verbose, -v       Show detailed output
```

### util_massive_websocket_test.py

```
Options:
  --connections N, -c N  Number of concurrent connections (default: 1, max: 3)
  --symbols SYMBOLS      Comma-separated symbols (default: top 10 ETFs)
  --duration N, -d N     Test duration in seconds (default: 30)
  --verbose, -v          Show detailed message output
```

### util_massive_api_explorer.py

```
Operations (mutually exclusive):
  --list-etfs                  List all available ETFs
  --ticker-details SYMBOL      Get detailed info for ticker
  --market-snapshot            Get snapshot for common ETFs
  --test-endpoints             Test various API endpoints

Options:
  --symbols SYMBOLS     Comma-separated symbols (for snapshot mode)
  --limit N             Limit number of results
  --verbose, -v         Show detailed output
  --save FILE           Save results to JSON file
```

---

**Created**: January 2025
**Last Updated**: January 21, 2025
**Related Sprint**: Sprint 52 - WebSocket Connections Admin Dashboard
