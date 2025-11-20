# Future Sprint Roadmap

**Last Updated**: 2025-09-19

This document outlines the future sprint roadmap after Sprint 26 (Pattern Flow Display).

## Sprint 27: Market Insights Dashboard with ETF-Based State
**Original Sprint 26 - Now Sprint 27**

- **Goal**: Market overview using ETFs (SPY, QQQ, IWM, etc.)
- **Features**:
  - Market regime detection (Bull/Bear/Consolidation)
  - Sector rotation analysis
  - Risk-on/Risk-off indicators
  - ETF performance matrix
- **Files**:
  - `sprint26_market_insights_definition_of_done.md` (from original Sprint 26)

## Sprint 28: Pattern Alert Management System

- **Goal**: User-configurable alerts for patterns
- **Features**:
  - Alert rules and thresholds per user
  - Multi-channel delivery (WebSocket, Email, Database)
  - Alert history tracking
  - Confidence threshold management

## Sprint 29: User Pattern Interest Selection

- **Goal**: Personalization of pattern preferences
- **Features**:
  - Pattern type preferences
  - Symbol watchlists
  - Sector preferences
  - Machine learning for preference optimization

## Sprint 30: Personalized Dashboard

- **Goal**: Adaptive dashboard based on user interests
- **Features**:
  - Dynamic widget arrangement
  - Drag-and-drop customization
  - Personal performance tracking
  - User-specific insights

## Sprint 31: Advanced Analytics & Performance

- **Goal**: Deep analytics and performance optimization
- **Features**:
  - Pattern success metrics
  - User behavior analytics
  - System performance optimization
  - Advanced reporting

## Architecture Principles (Maintained Across All Sprints)

- **Consumer Role**: TickStockAppV2 remains a pure consumer
- **Data Source**: All pattern data from TickStockPL via Redis
- **Performance**: <100ms WebSocket delivery, <50ms API responses
- **Loose Coupling**: Complete separation via Redis pub-sub
- **No Pattern Generation**: Display and organize only, never detect

## Notes

- Each sprint builds on the previous one
- Focus on creating a comprehensive, personalized trading dashboard system
- All features maintain the consumer architecture pattern