# TickStockAppV2 Documentation

**Version**: 3.0.0
**Last Updated**: September 26, 2025

## Overview

TickStockAppV2 is the consumer-facing application in the TickStock.ai ecosystem, providing user interface, authentication, and real-time data delivery while consuming processed events from TickStockPL.

## Documentation Structure

### Core Documentation
- **[About TickStock](./about_tickstock.md)** - Complete platform overview and capabilities
- **[Project Structure](./project_structure.md)** - Codebase organization and file structure

### Architecture
- **[Architecture Overview](./architecture/README.md)** - System design and components
- **[Redis Integration](./architecture/redis-integration.md)** - Pub-sub messaging patterns
- **[WebSocket Integration](./architecture/websockets-integration.md)** - Real-time communication
- **[Configuration](./architecture/configuration.md)** - Environment and settings

### Guides
- **[Quick Start](./guides/quickstart.md)** - Get up and running quickly
- **[Configuration Guide](./guides/configuration.md)** - Detailed configuration options
- **[Testing Guide](./guides/testing.md)** - Testing strategies and execution

### API Reference
- **[API Endpoints](./api/endpoints.md)** - Complete REST API documentation

### Data Sources
- **[Polygon Configuration](./data-sources/polygon/)** - Market data provider setup

### Planning & Sprints
- **[Sprint Documentation](./planning/sprints/)** - Current and past sprint plans
- **[Backlog](./planning/sprints/BACKLOG.md)** - Future development items

## Quick Links

### Essential Commands
```bash
# Start application
python start_all_services.py

# Run tests
python run_tests.py

# Check health
curl http://localhost:8501/health
```

### Key Endpoints
- Web UI: http://localhost:8501
- Health Check: http://localhost:8501/health
- API Base: http://localhost:8501/api
- WebSocket: ws://localhost:8501/socket.io/

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/tickstock
REDIS_HOST=localhost
REDIS_PORT=6379
FLASK_SECRET_KEY=your-secret-key
```

## Architecture Summary

```
TickStockAppV2 (This Repository)
├── Web Interface (Flask/Jinja2)
├── WebSocket Server (Socket.IO)
├── REST API (Pattern Discovery, Admin)
├── Redis Subscriber (Event Consumption)
└── Read-Only Database Access

    ↕ Redis Pub-Sub ↕

TickStockPL (Processing Engine)
├── Pattern Detection
├── Indicator Calculations
├── Data Processing
├── Database Management
└── Event Publishing
```

## Performance Targets

| Component | Target | Status |
|-----------|--------|--------|
| API Response | <50ms | ✅ |
| WebSocket Delivery | <100ms | ✅ |
| Redis Operation | <10ms | ✅ |
| Cache Hit Rate | >90% | ✅ |

## Getting Help

### Documentation
1. Start with [Quick Start Guide](./guides/quickstart.md)
2. Review [Architecture Overview](./architecture/README.md)
3. Check [API Documentation](./api/endpoints.md)

### Troubleshooting
- Check logs: `logs/tickstock.log`
- Run tests: `python run_tests.py`
- Verify config: `.env` settings
- Monitor health: `/health` endpoint

### Development
- See [CLAUDE.md](../CLAUDE.md) for AI assistant instructions
- Review [Testing Guide](./guides/testing.md) for quality assurance
- Check [Sprint Plans](./planning/sprints/) for current work

## Migration Notes

**Documentation Cleanup (Sept 2025)**
- Consolidated from 262 files to ~15 focused documents
- Removed outdated sprint artifacts
- Merged redundant guides
- See [ARCHIVE_MAP.md](./ARCHIVE_MAP.md) for migration details

## License & Support

This is the UI/consumer component of TickStock.ai. For processing engine documentation, see the TickStockPL repository.