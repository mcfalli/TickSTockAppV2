# TickStock.ai Documentation Evolution Index

**Last Updated**: 2025-08-27  
**Status**: Post-Consolidation Architecture Documentation

This index lists the core Markdown files defining TickStock.ai's current system architecture after major documentation consolidation. Each file captures a critical aspect of the system, guiding development and ensuring alignment.

## Core System Documentation

- **project-overview.md**: Complete project vision, requirements, system architecture, and technical principles. Consolidates original overview and requirements into single source of truth. Purpose: Sets the project's north star and technical foundation.

- **architecture_overview.md**: Detailed application role clarity (TickStockApp vs TickStockPL), communication patterns via Redis pub-sub, database architecture, and key architectural principles. Purpose: Defines clear system boundaries and interaction patterns.

- **tickstockpl-integration-guide.md**: Complete technical guide for TickStockPL integration including Redis channels, message formats, connection setup, and deployment considerations. Purpose: Enables seamless integration between systems.

## Technical Specifications

- **database_architecture.md**: PostgreSQL/TimescaleDB schema (symbols, ticks, ohlcv_1min/daily, events), optimization strategies, and data access patterns. Purpose: Guides shared database setup for historical/real-time pattern analysis.

- **pattern_library_architecture.md**: Pattern library technical blueprint including folder structure, key classes (BasePattern, PatternScanner), and processing workflows. Purpose: Technical framework for pattern implementation in TickStockPL.

- **pattern_library_overview.md**: Pattern library goals, categories (candlestick, chart, trend, breakout), and integration overview. Purpose: Frames the pattern detection scope and capabilities.

- **websockets_integration.md**: WebSocket implementation details for real-time data flow from external sources through TickStockApp to TickStockPL via Redis. Purpose: Defines real-time data pipeline architecture.

## Implementation Guidance

- **sprint10/**: Current Sprint 10 implementation plans including:
  - `sprint10-appv2-implementation-plan.md`: Detailed TickStockAppV2 UI integration roadmap
  - `sprint10-completed-summary.md`: TickStockPL completed work summary
  - Supporting documentation for current development phase

- **user_stories.md**: Requirements captured in user story format for development guidance. Purpose: Provides user-focused requirements for feature development.

- **get_historical_data.md**: Technical details for seeding database with historical OHLCV data via API integration. Purpose: Guides initial data loading for backtesting capabilities.

## Archived Documentation

- **archive/**: Contains consolidated/superseded documents including original overview, requirements, and architecture documents that have been merged into the current structure.

## Evolution Notes

**Major Consolidation (2025-08-27)**:
- Merged `overview.md` + `requirements.md` → `project-overview.md`
- Archived redundant architecture documents
- Updated cross-references throughout documentation
- Established clear information architecture with single sources of truth

These files represent the current state of TickStock.ai documentation, stored in `docs/planning` for version control and reference. The consolidated structure eliminates redundancy while maintaining comprehensive coverage of all system aspects.