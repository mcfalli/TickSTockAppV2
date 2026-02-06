# TickStock V2

**TickStock.ai** is a high-performance, real-time stock analytics platform that curates actionable insights across more than 4,000 tickers.

It delivers dynamic, subscription-based dashboards featuring:
- **Ranked top-performing stocks** by live and EOD percentage changes
- **Multi-timeframe performance trends** (1-week through 1-year)
- **Key fundamental metrics** (EPS rank, P/E ratio, revenue rank)
- **Advanced risk and volatility indicators** (ATR, ADR%, ATR relative to SMA(50))

Subscribers can dive deep into:
- **Sector-specific and industry-group breakdowns** (semiconductors, energy, metals, finance) with proprietary stage analysis for bullish and bearish setups
- **Moving average matrices** for precise entry, hold, and exit signals
- **Aggregated market health metrics** across major indices (NASDAQ, S&P 500, QQQE) and sector ETFs

The platform is enhanced with intuitive **color-coded visualizations**, **multi-timeframe trend analysis** (intraday + daily correlations), customizable filtering, and **sub-millisecond update performance**—powered by a memory-first architecture. Designed to highlight high-probability opportunities such as volume surges, momentum shifts, and trend confirmations through comprehensive market state analysis, TickStock.ai is built for serious day traders, swing analysts, and portfolio managers who demand a real edge in fast-moving, volatile markets.

**Technical Architecture:**
- **TickStockAppV2**: UI, authentication, real-time WebSocket updates; market state dashboards and trend visualization
- **TickStockPL**: Data import and management, historical data processing, TimescaleDB management
- **Performance**: Processes thousands of symbols/minute, >300 symbols/second throughput, >92% cache hit rates
- **Integration**: Python (pandas, NumPy, SciPy), Flask, SQLAlchemy, Matplotlib, multi-connection WebSocket support

## Quick Start

```bash
# Start all services
python start_all_services.py

# Run Integration Test Suite (<10 seconds)
python run_tests.py
```

## Documentation

### Core Documentation
- **[About TickStock](docs/about_tickstock.md)** - Platform overview and capabilities
- **[Quick Start Guide](docs/guides/quickstart.md)** - Get up and running quickly
- **[Architecture](docs/architecture/README.md)** - System design and components
- **[API Reference](docs/api/endpoints.md)** - REST API documentation

### Developer Resources
- **[CLAUDE.md](CLAUDE.md)** - AI assistant development guide
- **[Configuration](docs/guides/configuration.md)** - Environment and settings
- **[Testing](docs/guides/testing.md)** - Testing strategies and execution
- **[Project Structure](docs/project_structure.md)** - Codebase organization

### Key Integration Points
- **[Redis Integration](docs/architecture/redis-integration.md)** - Pub-sub messaging
- **[WebSocket Integration](docs/architecture/websockets-integration.md)** - Real-time updates

For detailed documentation, see the [docs folder](docs/README.md).