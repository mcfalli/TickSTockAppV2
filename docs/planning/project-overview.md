# TickStock.ai Project Overview

**Document**: Complete Project Overview & Requirements  
**Last Updated**: 2025-08-27  
**Status**: Consolidated from overview.md + requirements.md

---

## 🎯 Vision & Mission

TickStock.ai is a comprehensive platform for algorithmic stock analysis, empowering users to detect patterns in OHLCV data for informed trading decisions. The goal is to build scalable, modular libraries for pattern detection, blending historical and real-time data, while keeping it bootstrap-friendly (lightweight deps like pandas, numpy, scipy, and Redis—no heavy funding needs). 

We focus on extensibility—starting with core patterns (candlesticks, charts, trends, breakouts) and evolving to custom/ML signals via composable conditions and multi-timeframe support. Ultimately, provide actionable signals via events to drive trades, alerts, visualizations, and backtests, all while ensuring loose coupling for independent scaling.

---

## 🏗️ System Architecture

### Major Components
- **TickStock.ai**: Static front end (HTML/JS site) for user-facing info, demos, and access points
- **TickStockApp**: Core application servicing users—handles subscriptions, UI, portfolio, and consumes events (via Redis pub-sub) for real-time alerts/trades
- **TickStockPL** (Pattern Library Services): Microservices for pattern detection—includes scanner, data loaders, and event publishing. Runs separately for modularity/scalability, feeding signals to TickStockApp via Redis pub-sub

### High-Level Processing Flow
1. **Data Ingestion**: Pull OHLCV from APIs (Polygon or yfinance free tier), databases, or real-time feeds (WebSockets via TickStockApp)
2. **Preprocessing**: Clean, resample (to 1min/daily), and blend historical + live data using DataBlender for unified DataFrames
3. **Pattern Scanning**: Analyze blended data in TickStockPL using modular classes (BasePattern, PatternScanner); detect patterns and publish events on finds via Redis pub-sub for loose coupling
4. **Event Handling**: TickStockApp subscribes to Redis channels, consuming signals for user actions (UI alerts, automated trades, or DB logging)
5. **Output**: Generate visuals, backtest results, or responses in TickStockApp, with events persisted for auditing

### System Decoupling
This setup ensures decoupling: TickStockPL processes data independently, publishing events to Redis for TickStockApp to subscribe and act on, enabling resilient, scalable operations.

---

## 📋 Functional Requirements

### Core Pattern Detection
- Real-time Doji detection and reversal signals
- Extensible pattern framework supporting candlestick, chart, trend, and breakout patterns
- Multi-timeframe support (1min, daily, with extensibility for hourly)
- Composable conditions for custom/ML signal development

### Data Management
- Historical and real-time data blending via DataBlender
- Support for multiple data sources (Polygon API, yfinance, WebSocket feeds)
- Database persistence for OHLCV data, symbols, and event logs
- Data preprocessing and resampling capabilities

### User Experience
- Real-time pattern alerts and notifications
- Interactive dashboards and visualizations
- Backtesting interface with historical performance metrics
- Portfolio management and trade execution integration

### System Integration
- Redis pub-sub for loose coupling between components
- Event-driven architecture for scalability
- WebSocket support for real-time UI updates
- API integration for external data sources

*Detailed user stories available in `user_stories.md`*

---

## 🎯 Non-Functional Requirements

### Performance Targets
- **Pattern Detection**: <50ms latency for real-time pattern detections in TickStockPL
- **End-to-End Processing**: <1s from data ingestion to pattern event publication
- **WebSocket Updates**: <100ms for real-time UI updates
- **Database Queries**: <10ms for TimescaleDB queries with proper indexing

### Scalability Requirements
- **Symbol Coverage**: Support scanning 1000+ symbols simultaneously
- **Memory Usage**: <2GB when processing 1k symbols concurrently
- **Parallel Processing**: Multi-threaded PatternScanner for concurrent analysis
- **Horizontal Scaling**: Redis pub-sub enables multiple instances of each component

### Quality Standards
- **Test Coverage**: 80% minimum across src/ (patterns, data, analysis) using pytest
- **Code Quality**: Comprehensive type hints, PEP 8 compliance, modular architecture
- **Documentation**: Complete docstrings, API documentation, architectural decision records

### Reliability & Compatibility
- **Bootstrap-Friendly**: Lightweight dependencies (pandas, numpy, scipy, Redis)
- **Error Handling**: Graceful API fallbacks, retry mechanisms, comprehensive logging
- **Timeframe Support**: Native 1min and daily support, extensible via DataBlender resampling
- **Data Integrity**: OHLCV validation, gap handling, timezone consistency (UTC)

### Security & Usability
- **Event Security**: Secure Redis pub-sub channels with authentication
- **Data Privacy**: No sensitive data logging, secure API key management
- **UI Usability**: Intuitive parameter customization and visualization interfaces
- **System Monitoring**: Health checks, performance metrics, error alerting

---

## 🔧 Technical Architecture Principles

### Separation of Concerns
- **TickStockApp**: UI-focused event consumer and user management
- **TickStockPL**: Heavy-lifting analytical engine and event producer
- **Redis**: Communication layer ensuring loose coupling
- **Database**: Shared persistence with role-based access

### Event-Driven Design
- Asynchronous processing via Redis pub-sub channels
- No direct API calls between applications
- Event sourcing for audit trails and debugging
- Scalable message distribution

### Performance-First Approach
- Memory-first processing for sub-millisecond operations
- TimescaleDB optimization for time-series queries
- Vectorized operations using pandas/numpy
- Efficient data serialization and caching

### Bootstrap Philosophy
- Minimal external dependencies
- Self-contained deployment capabilities
- Cost-effective scaling without heavy infrastructure
- Focus on core functionality over feature bloat

---

## 📈 Success Metrics

### Business Objectives
- **Pattern Accuracy**: High-confidence pattern detection with institutional-grade metrics
- **User Engagement**: Real-time alerts driving trading decisions
- **Platform Adoption**: Growing user base leveraging backtesting capabilities
- **System Reliability**: 99.9% uptime for real-time pattern detection

### Technical Achievements
- **Sprint 7 Performance**: 1.12ms pattern detection (96x faster than target)
- **Sprint 10 Database**: Complete TimescaleDB backend with multi-year historical data
- **Pattern Library**: 11+ patterns with comprehensive backtesting framework
- **Architecture Cleanup**: 60% code reduction maintaining essential functionality

### Development Velocity
- **Rapid Prototyping**: Bootstrap-friendly approach enabling quick iterations
- **Modular Architecture**: Independent scaling and development of components
- **Comprehensive Testing**: Quality assurance through automated test suites
- **Clear Documentation**: Streamlined onboarding and maintenance processes

---

This project overview serves as the single source of truth for TickStock.ai's vision, requirements, and architectural principles, guiding all development efforts toward building fantastic algorithmic pattern libraries in Python.

**Related Documentation:**
- Architecture details: `../architecture/system-architecture.md`
- User stories: `user_stories.md`
- Sprint 10 implementation: Completed - see `evolution_index.md` for project history