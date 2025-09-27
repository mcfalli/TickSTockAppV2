# TickStock V2

**TickStock.ai** is a high-performance platform for real-time and batch processing of market data, analyzing over 4,000 stock symbols with sub-millisecond efficiency. It leverages a three-tiered architecture—Daily Batch Processing, Intraday Streaming, and Combo Hybrid Intelligence—to detect technical patterns (e.g., Doji, breakouts) and calculate indicators (e.g., RSI, MACD) across intraday, hourly, daily, weekly, and monthly timeframes. Built with Python (pandas, NumPy, SciPy), it integrates Polygon API data and supports modular expansion via a dynamic loading system (NO FALLBACK policy).

**Components:**
- **TickStockAppV2**: Manages UI, authentication, and real-time WebSocket updates; consumes events and triggers jobs via Redis.
- **TickStockPL**: Handles pattern detection, data processing, backtesting, and TimescaleDB management; publishes events to Redis.

**Key Features:**
- Processes thousands of symbols/minute for intraday patterns/indicators
- Performs daily batch analysis for long-term trends, stored in TimescaleDB
- Correlates multi-timeframe signals with fundamentals (e.g., EPS surprises) for <5% false positives
- Achieves >300 symbols/second, >92% cache hit rates, with Flask, SQLAlchemy, and Matplotlib integration

## Quick Start

```bash
# Start both services
python start_both_services.py

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