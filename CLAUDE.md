# CLAUDE.md

This file provides comprehensive guidance to Claude Code when working with Python code in this repository.

**Important** - CLAUDE documentation is stored local at ./.claude-code-docs to reference not having to go out to anthropic to find documentation. This is kept current daily.

_This document is a living guide. Update it as the project evolves and new patterns emerge._

## About TickStock

### What is TickStock?
TickStock is a high-performance, real-time market data processing system that handles 4,000+ stock tickers with sub-millisecond event detection. It processes WebSocket data streams from Polygon.io (production) or synthetic data (development) and delivers personalized, filtered market events to users via WebSocket connections.

### Core Value Proposition
- Real-time processing of market data with <100ms end-to-end latency
- Zero event loss through Pull Model architecture
- Per-user filtering and personalization
- **Sprint 10 Complete**: Full TickStockPL integration with backtesting platform and pattern alerts

### Technology Stack
- **Backend**: Python 3.x, Flask, Flask-SocketIO, Eventlet
- **Frontend**: JavaScript ES6+ SPA with Socket.IO client
- **Database**: PostgreSQL + TimescaleDB for time-series data
- **Cache**: Redis for user preferences, TickStockPL integration, and pub-sub messaging
- **Data Provider**: Polygon.io (live) / Synthetic (dev/test)
- **Architecture**: Component-based with Pull Model + TickStockPL Integration via Redis

## Project Organization

### Development Standards & Processes
Follow these comprehensive instruction guides for all development work:

- **Sprint Documentation**: See `docs/instructions/sprint-documentation-tasks.md` - Process for handling documentation during sprints
- **Testing Standards**: See `docs/instructions/unit_testing.md` - Complete testing organization, standards, and sprint requirements
- **Coding Practices**: See `docs/instructions/coding-practices.md` - Development philosophy, style, error handling, anti-patterns, and best practices
- **Documentation Standards**: See `docs/instructions/code-documentation-standards.md` - Docstrings, comments, API documentation, and inline comment standards
- **Technical Debt Management**: See `docs/instructions/technical-debt-management.md` - Systematic debt identification, prioritization, and resolution process
- **Architectural Decisions**: See `docs/instructions/architectural-decision-process.md` - ADR creation, review, and governance process

These guides provide complete coverage of TickStock's development workflow and must be followed for all development assistance and code generation.

### Project Structure
- See `docs/project_structure.md` for complete folder organization

### Key Components Reference
#### Core Processing Pipeline
1. **app.py** → Flask application entry point
2. **core_service.py** → WebSocket tick handler & orchestrator
3. **event_processor.py** → Main event processing logic
4. **event_detector.py** → High/Low, Trend, Surge detection
5. **data_publisher.py** → Event collection & buffering
6. **websocket_publisher.py** → Pull-based emission to users

#### Database Models
- **cache_entries** → Core universe definitions
- **user_universe** → Per-user stock selections
- **analytics_data** → Stored analytics results
- **app_readwrite** → Database user for application

## Architecture & Design

### Critical Architecture Patterns

#### Pull Model (Sprint 29) - MUST MAINTAIN
- DataPublisher collects and buffers events (no emission)
- WebSocketPublisher pulls when ready (controls flow)
- Zero event loss guaranteed
- Buffer overflow protection (1000 events/type max)

#### Event Type Boundary
- Detection → Worker: Typed Events (HighLowEvent, TrendEvent, SurgeEvent)
- Worker → Display Queue: Dict conversion via `to_transport_dict()`
- Display Queue → Frontend: Dict only
- **Never mix typed events and dicts after Worker conversion**

#### Memory-First Processing
- All operations in memory for sub-millisecond performance
- Database sync every 10 seconds (500:1 write reduction)
- Redis for user preferences and universe caching

### Core Development Philosophy
**Comprehensive Guidelines**: See `docs/instructions/coding-practices.md` for complete development philosophy, design principles, and coding best practices.

#### Key Principles
- **KISS**: Keep solutions simple and maintainable
- **YAGNI**: Build features only when needed
- **DRY**: Avoid code duplication through abstraction
- **Single Responsibility**: Each component has one clear purpose

## Code Standards & Quality

### Code Structure & Style
**Comprehensive Style Guide**: See `docs/instructions/coding-practices.md` for complete code structure, modularity guidelines, Python style standards, and naming conventions.

#### Key Standards
- **File Limits**: Max 500 lines per file, 50 lines per function
- **Style**: PEP 8 with real-time financial system adaptations
- **Naming**: snake_case functions, PascalCase classes, UPPER_SNAKE_CASE constants
- **Type Safety**: Comprehensive type hints for all functions

### Documentation Standards
**Comprehensive Documentation Guide**: See `docs/instructions/code-documentation-standards.md` for complete documentation standards, Google-style docstrings, and inline comment guidelines.

#### Key Requirements
- **Module Documentation**: Every module needs purpose docstring
- **Function Documentation**: Complete Google-style docstrings for public functions
- **Inline Comments**: Use `# Reason:` prefix for complex logic
- **Documentation Files**: Update date/time and sprint info when modified

### Error Handling & Logging
**Complete Implementation Guides**: See `docs/instructions/coding-practices.md` for comprehensive error handling patterns, logging strategies, and configuration management standards.

#### Key Patterns
- **Custom Exceptions**: Domain-specific exception hierarchy for market data errors
- **Context Managers**: Proper resource management for connections and external services
- **Domain Logging**: Structured logging with performance and error tracking
- **Pydantic Config**: Type-safe environment variable management with validation

### Common Development Tasks
**Detailed Task Guides**: See `docs/instructions/coding-practices.md` for complete development task workflows, database schema patterns, and implementation guidelines.


## Testing & Reliability

### Testing Framework
***TickStock uses a comprehensive testing strategy with pytest for quality assurance and performance verification.***

**Comprehensive Testing Guidelines**: See `docs/instructions/unit_testing.md` for complete testing standards, organization structure, sprint requirements, and best practices.

**Testing Agents**: Comprehensive testing is provided by multiple specialized agents:
- **`tickstock-test-specialist`**: Automated test generation and quality assurance for TickStock processing components
- **`integration-testing-specialist`**: Cross-system testing for TickStockApp ↔ TickStockPL communication via Redis

These agents are automatically invoked when creating features, fixing bugs, or modifying core processing components to ensure comprehensive test coverage following TickStock standards.

#### Key Testing Principles
- **Quality First**: No feature is complete without tests
- **Performance Critical**: Sub-millisecond processing requires performance validation
- **Functional Organization**: Tests organized by business domain (event_processing, data_processing, etc.)
- **Sprint-Specific**: Each sprint creates tests in appropriate functional area with sprint subfolders
- **Agent-Assisted**: Automated test generation through specialized testing agent

### Quality Assurance
**Comprehensive Guidelines**: See `docs/instructions/coding-practices.md` for complete quality standards, code review guidelines, and common pitfalls.

#### Key DON'Ts and DOs
- **DON'T**: Mix event types after Worker boundary, exceed size limits, skip tests
- **DO**: Maintain Pull Model, use memory/cache for hot paths, write comprehensive tests
- **Architecture**: Always maintain event type consistency and zero event loss

## Development Workflow

### Sprint Management
- **Sprint Capacity Monitoring**: Alert at 80% chat capacity
- **Context Preservation**: Capture all relevant context before chat transitions
- **Task Tracking**: Maintain sprint tasks with ongoing task list for items that arise
- **Specialized Agent Integration**: Multiple specialized agents provide domain expertise:
  - `appv2-integration-specialist` for Sprint 10 UI integration phases
  - `tickstock-test-specialist` for comprehensive test coverage
  - `architecture-validation-specialist` for continuous compliance checking
  - See complete agent list in Specialized Agents section below

### Git Workflow
#### Branch Strategy
- **main** - primary repository

#### Commit Message Format
```
<type>(<scope>): <subject>
<body>
<footer>
```

**Types**: feat, fix, docs, style, refactor, test, chore

**Example**:
```
feat(auth): add two-factor authentication
Implement TOTP generation and validation
Add QR code generation for authenticator apps
Update user model with 2FA fields
Closes #123
```

**NEVER include claude code, written by claude code, or any Generated with Claude Code attribution in commit messages**

Do NOT add these lines to any commits:
- 🤖 Generated with [Claude Code](https://claude.ai/code)
- Co-Authored-By: Claude <noreply@anthropic.com>

### AI Development Tasks
Use these files when structured feature development is requested using PRD or Sprint:
- `tasks/templates/create-prd.md`
- `tasks/templates/generate-tasks.md`
- `tasks/templates/process-task-list.md`

### Communication Protocol
When working on sprints/problems:
- Repeat understanding of goals in response
- Analyze and summarize the approach
- Ask clarifying questions before generating code
- Provide clear directions with code examples
- Track additional items that arise during sprint work
- Leverage specialized agents for domain-specific tasks (see Specialized Agents section below)

## Specialized Agents

TickStock.ai uses specialized agents for domain-specific tasks. These agents have deep expertise in specific areas and should be used proactively when their domain is encountered.

### Implementation Agents

#### `appv2-integration-specialist`
**Domain**: TickStockAppV2 UI integration and Redis consumption  
**Use When**: Sprint 10 implementation phases, Flask/SocketIO integration, WebSocket broadcasting, maintaining lean ~11,000 line architecture  
**Expertise**: Database read-only connections, Redis event consumption, backtesting UI, pattern alert management  
**Key Focus**: Consumer role (triggers jobs, displays results), no heavy data processing

#### `redis-integration-specialist` 
**Domain**: Redis pub-sub architecture and message handling  
**Use When**: Redis Streams, channel management, WebSocket broadcasting patterns, message queuing  
**Expertise**: Persistent message queuing, offline user handling, Redis scaling and performance optimization  
**Key Focus**: Loose coupling between TickStockApp and TickStockPL via async pub-sub

#### `database-query-specialist`
**Domain**: TimescaleDB read-only queries and health monitoring  
**Use When**: UI data queries, health monitoring dashboards, connection pooling, database performance  
**Expertise**: Simple performant queries (<50ms), connection management, read-only boundaries  
**Key Focus**: TickStockAppV2 database access (read-only), UI dropdowns, basic stats

### Quality Assurance Agents

#### `tickstock-test-specialist`
**Domain**: TickStock real-time financial data processing testing  
**Use When**: Creating features, fixing bugs, modifying core processing components  
**Expertise**: Performance benchmarks, financial data mocking, functional test organization, Sprint-specific testing  
**Key Focus**: Sub-millisecond requirements, Pull Model architecture, zero event loss guarantee  
**Usage**: MUST BE USED proactively for comprehensive test coverage

#### `integration-testing-specialist`
**Domain**: Cross-system integration testing (TickStockApp ↔ TickStockPL)  
**Use When**: Redis message flow validation, database integration testing, end-to-end workflow verification  
**Expertise**: Message delivery performance, system resilience, loose coupling validation  
**Key Focus**: <100ms message delivery, role boundary enforcement, system health validation

### Architecture & Documentation Agents

#### `documentation-sync-specialist`
**Domain**: Documentation alignment and consistency across planning documents  
**Use When**: Cross-reference validation, architecture consistency checking, sprint documentation updates  
**Expertise**: Terminology standardization, navigation updates, consolidated information architecture maintenance  
**Key Focus**: Single source of truth, consistent cross-references, evolution tracking

#### `architecture-validation-specialist`
**Domain**: Architecture compliance and role separation enforcement  
**Use When**: Detecting tight coupling, role boundary violations, anti-patterns  
**Expertise**: Redis pub-sub pattern validation, database access control, performance pattern compliance  
**Key Focus**: TickStockApp (consumer) vs TickStockPL (producer) separation, loose coupling via Redis

### Agent Usage Guidelines

#### Proactive Agent Usage
- **`tickstock-test-specialist`**: Automatically invoke when creating features, fixing bugs, or modifying core components
- **`architecture-validation-specialist`**: Use for continuous compliance checking throughout development
- **`documentation-sync-specialist`**: Invoke when updating documentation or cross-references

#### Phase-Based Agent Usage (Sprint 10)
- **Phase 1-3**: `appv2-integration-specialist` + `database-query-specialist`
- **Phase 2-4**: `redis-integration-specialist` + `integration-testing-specialist`  
- **Throughout**: `architecture-validation-specialist` + `documentation-sync-specialist`

#### Agent Coordination
- All agents understand the role boundaries (AppV2 = Consumer, TickStockPL = Producer)
- All agents reference consolidated documentation (`project-overview.md`, `architecture_overview.md`)
- All agents enforce performance targets (<100ms WebSocket, <50ms DB queries)
- All agents maintain Redis pub-sub loose coupling patterns

## Recent Major Updates

### Enhanced Symbols Table & Historical Loader (Sprint 11)
**Date**: 2025-08-29  
**Changes**: 
- **Symbols table enhanced** with 12 new columns from Polygon.io API (market cap, FIGI identifiers, SEC CIK, etc.)
- **Historical loader auto-creates symbols** - no more foreign key constraint errors
- **Symbol metadata refresh** - existing symbols updated with latest data from API
- **Web interface fixed** - admin historical data dashboard now uses updated loader
- **Database scripts** available in `scripts/database/` for table updates

**Migration Required**: Run `scripts/database/symbols_table_enhancement.sql` to add new columns

**Breaking Change**: `get_symbols_for_dropdown()` now returns rich objects instead of strings

## Important Operating Guidelines

### Critical Rules
- **NEVER ASSUME OR GUESS** - When in doubt, ask for clarification
- **Always verify file paths and module names** before use
- **Keep CLAUDE.md updated** when adding new patterns or dependencies
- **Follow all development standards** - See Development Standards & Processes section above
- **Document your decisions** - Future developers (including yourself) will thank you

### Search Command Requirements
**CRITICAL**: Use `rg` (ripgrep) instead of traditional `grep` and `find` commands. See `docs/instructions/coding-practices.md` for complete search command patterns and examples.