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

- **Sprint Documentation**: See `docs/planning/evolution_index.md` - Documentation evolution and sprint history tracking
- **Testing Standards**: See `docs/development/unit_testing.md` - Complete testing organization, standards, and sprint requirements
- **Coding Practices**: See `docs/development/coding-practices.md` - Development philosophy, style, error handling, anti-patterns, and best practices
- **Documentation Standards**: See `docs/development/code-documentation-standards.md` - Docstrings, comments, API documentation, and inline comment standards
- **Technical Debt Management**: See `docs/development/technical-debt-management.md` - Systematic debt identification, prioritization, and resolution process
- **Architectural Decisions**: See `docs/development/architectural-decision-process.md` - ADR creation, review, and governance process

These guides provide complete coverage of TickStock's development workflow and must be followed for all development assistance and code generation.

### Project Structure
- See `docs/development/project_structure.md` for complete folder organization

### Key Components Reference
#### Core Processing Pipeline
1. **app.py** → Flask application entry point
2. **core_service.py** → WebSocket tick handler & orchestrator
3. **event_processor.py** → Main event processing logic
4. **event_detector.py** → High/Low, Trend, Surge detection
5. **data_publisher.py** → Event collection & buffering
6. **websocket_publisher.py** → Pull-based emission to users

#### Pattern Discovery APIs (Sprint 19)
1. **pattern_discovery.py** → Flask integration and service orchestration
2. **pattern_consumer.py** → Pattern scanning API endpoints (`/api/patterns/*`)
3. **user_universe.py** → Symbol and universe management APIs (`/api/symbols`, `/api/users/*`)
4. **redis_pattern_cache.py** → Multi-layer Redis caching consuming TickStockPL events
5. **pattern_discovery_service.py** → Service coordination and health monitoring

#### Database Models
- **cache_entries** → Core universe definitions
- **user_universe** → Per-user stock selections
- **analytics_data** → Stored analytics results
- **symbols** → Stock symbol metadata (read-only access for UI)
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

#### Pattern Discovery Architecture (Sprint 19)
- **Consumer Pattern**: TickStockApp consumes pattern events via Redis pub-sub only
- **Multi-layer Redis Caching**: Pattern entries (1h TTL), API responses (30s TTL), sorted indexes
- **Zero Database Pattern Queries**: All pattern data served from Redis cache consuming TickStockPL events
- **Read-only Database Access**: Only symbols, user data, universe selections (no pattern tables)
- **Service Orchestration**: PatternDiscoveryService coordinates all components with health monitoring
- **Performance Targets**: <50ms API responses, >70% cache hit ratio, <100ms WebSocket delivery

### Core Development Philosophy
**Comprehensive Guidelines**: See `docs/development/coding-practices.md` for complete development philosophy, design principles, and coding best practices.

#### Key Principles
- **KISS**: Keep solutions simple and maintainable
- **YAGNI**: Build features only when needed
- **DRY**: Avoid code duplication through abstraction
- **Single Responsibility**: Each component has one clear purpose

## Code Standards & Quality

### Code Structure & Style
**Comprehensive Style Guide**: See `docs/development/coding-practices.md` for complete code structure, modularity guidelines, Python style standards, and naming conventions.

#### Key Standards
- **File Limits**: Max 500 lines per file, 50 lines per function
- **Style**: PEP 8 with real-time financial system adaptations
- **Naming**: snake_case functions, PascalCase classes, UPPER_SNAKE_CASE constants
- **Type Safety**: Comprehensive type hints for all functions

### Documentation Standards
**Comprehensive Documentation Guide**: See `docs/development/code-documentation-standards.md` for complete documentation standards, Google-style docstrings, and inline comment guidelines.

#### Key Requirements
- **Module Documentation**: Every module needs purpose docstring
- **Function Documentation**: Complete Google-style docstrings for public functions
- **Inline Comments**: Use `# Reason:` prefix for complex logic
- **Documentation Files**: Update date/time and sprint info when modified

### Error Handling & Logging
**Complete Implementation Guides**: See `docs/development/coding-practices.md` for comprehensive error handling patterns, logging strategies, and configuration management standards.

#### Key Patterns
- **Custom Exceptions**: Domain-specific exception hierarchy for market data errors
- **Context Managers**: Proper resource management for connections and external services
- **Domain Logging**: Structured logging with performance and error tracking
- **Pydantic Config**: Type-safe environment variable management with validation

### Common Development Tasks
**Detailed Task Guides**: See `docs/development/coding-practices.md` for complete development task workflows, database schema patterns, and implementation guidelines.


## Testing & Reliability

### Testing Framework
***TickStock uses a comprehensive testing strategy with pytest for quality assurance and performance verification.***

**Comprehensive Testing Guidelines**: See `docs/development/unit_testing.md` for complete testing standards, organization structure, sprint requirements, and best practices.

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
**Comprehensive Guidelines**: See `docs/development/coding-practices.md` for complete quality standards, code review guidelines, and common pitfalls.

#### Key DON'Ts and DOs
- **DON'T**: Mix event types after Worker boundary, exceed size limits, skip tests
- **DO**: Maintain Pull Model, use memory/cache for hot paths, write comprehensive tests
- **Architecture**: Always maintain event type consistency and zero event loss

## Development Workflow

### Sprint Management
- **Sprint Capacity Monitoring**: Alert at 80% chat capacity
- **Context Preservation**: Capture all relevant context before chat transitions
- **Task Tracking**: Maintain sprint tasks with ongoing task list for items that arise
- **Mandatory Agent Integration**: All development work MUST follow the Agent Usage Workflow (see Specialized Agents section)
  - Pre-implementation: `architecture-validation-specialist` reviews approach
  - During implementation: Domain-specific agents (see Agent Auto-Triggers below)
  - Post-implementation: `tickstock-test-specialist` + `integration-testing-specialist`
  - Documentation updates: `documentation-sync-specialist`

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
When working on sprints/problems, MANDATORY workflow:
1. **Immediate Agent Assessment**: Identify required agents based on Auto-Triggers (see Specialized Agents section)
2. **Phase 1 - Analysis**: Launch `architecture-validation-specialist` + domain specialists for approach validation
3. **Understanding Confirmation**: Repeat understanding of goals in response
4. **Approach Summary**: Analyze and summarize the approach with agent recommendations
5. **Clarification**: Ask clarifying questions before generating code
6. **Implementation**: Use mandatory agent workflow throughout development
7. **Quality Gates**: Complete mandatory testing and integration validation
8. **Documentation**: Update all relevant documentation via `documentation-sync-specialist`

**CRITICAL**: No development work may proceed without completing Phase 1 agent analysis and getting explicit approval for the approach.

## Specialized Agents

**CRITICAL**: TickStock.ai REQUIRES specialized agent usage for all development tasks. These agents provide mandatory quality gates and domain expertise. All development work must follow the Agent Usage Workflow defined below.

### Agent Usage Workflow (MANDATORY)

Every development task MUST follow this workflow:

1. **Pre-Implementation Analysis**
   - `architecture-validation-specialist`: Review approach for compliance and anti-patterns
   - Domain specialist (see Auto-Triggers): Validate domain-specific requirements

2. **Implementation Phase**
   - Use domain-specific agents based on Auto-Triggers (see below)
   - Continuous validation through specialized agents

3. **Quality Gate (MANDATORY)**
   - `tickstock-test-specialist`: Generate comprehensive tests (REQUIRED)
   - `integration-testing-specialist`: Validate cross-system integration (REQUIRED)

4. **Documentation & Finalization**
   - `documentation-sync-specialist`: Update documentation and cross-references

### Agent Auto-Triggers (MANDATORY USAGE)

**CRITICAL**: These triggers AUTOMATICALLY require agent usage - no exceptions:

#### Core Processing Files (tickstock-test-specialist + architecture-validation-specialist)
- **ANY modification to**: `src/` directory files containing event processing, data handling, or WebSocket logic
- **Pattern-based triggers**: Files with `*processor*.py`, `*detector*.py`, `*publisher*.py`, `*service*.py` in filename
- **Performance-critical paths**: Any code with <100ms latency requirements or real-time processing
- **Event processing logic**: New event types, detection algorithms, buffer management, Pull Model components
- **WebSocket handling**: Any WebSocket server/client implementation or message broadcasting
- **Market data processing**: Polygon.io integration, tick processing, synthetic data generation

#### Database & Query Operations (database-query-specialist + architecture-validation-specialist)
- **Directory-based**: Any modifications to `src/database/`, `src/models/`, `src/queries/`, `scripts/database/`
- **Pattern-based**: Files with `*model*.py`, `*query*.py`, `*db*.py`, `*database*.py` in filename
- **Schema operations**: TimescaleDB schema changes, migrations, table modifications
- **Connection management**: Connection pooling, database configuration, connection handling
- **Query performance**: Any query with <50ms requirement or complex database operations
- **Read-only enforcement**: Database access boundary validation, user permission management

#### Redis & Integration (redis-integration-specialist + integration-testing-specialist)
- **Directory-based**: Any modifications to `src/redis/`, `src/integration/`, `src/messaging/`
- **Pattern-based**: Files with `*redis*.py`, `*pubsub*.py`, `*message*.py`, `*queue*.py` in filename
- **Integration patterns**: Cross-system communication (TickStockApp ↔ TickStockPL)
- **Message handling**: Redis Streams, pub-sub patterns, message queuing, offline user handling
- **WebSocket integration**: Broadcasting patterns, real-time message delivery
- **Loose coupling**: Architecture ensuring proper system separation via Redis

#### UI & Frontend Integration (appv2-integration-specialist + database-query-specialist)
- **Directory-based**: Any modifications to `src/web/`, `static/`, `templates/`, `src/api/`
- **Pattern-based**: Files with `*app*.py`, `*route*.py`, `*api*.py`, `*web*.py` in filename
- **Flask/SocketIO**: Web framework modifications, WebSocket server implementation
- **Frontend integration**: JavaScript client connections, UI component updates
- **Data presentation**: UI queries, dropdowns, dashboards, user interface data
- **Feature interfaces**: Backtesting UI, pattern alerts, admin panels, user management

#### Documentation & Architecture (documentation-sync-specialist + architecture-validation-specialist)
- **ANY documentation updates**
- **Cross-reference changes**
- **Architecture documentation modifications**
- **Sprint documentation updates**

#### Security-Sensitive Operations (code-security-specialist + architecture-validation-specialist)
- **Authentication & Authorization**: User session management, WebSocket authentication, API token validation
- **Input Handling**: Frontend forms, WebSocket message processing, API endpoint parameters, URL parameters
- **Data Protection**: Database credential management, API key handling, sensitive data exposure prevention
- **WebSocket Security**: Real-time connection security, message validation, origin checking, user authorization
- **API Security**: Polygon.io integration, REST endpoint security, rate limiting, secure HTTP practices
- **Frontend Security**: XSS prevention, CSRF protection, DOM manipulation, client-side validation
- **Redis Security**: TickStockPL integration security, pub-sub authentication, message encryption
- **Configuration Security**: Environment variables, Flask security settings, database connection security
- **Dependency Security**: Python package updates, JavaScript library changes, security patch integration

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
**MANDATORY Usage**: AUTOMATICALLY triggered for ALL code changes (no exceptions)  
**Auto-Triggers**: Any modification to core processing files, new features, bug fixes, performance-critical code  
**Expertise**: Performance benchmarks, financial data mocking, functional test organization, Sprint-specific testing  
**Key Focus**: Sub-millisecond requirements, Pull Model architecture, zero event loss guarantee  
**Quality Gate**: No feature/fix is complete without comprehensive tests from this agent

#### `integration-testing-specialist`
**Domain**: Cross-system integration testing (TickStockApp ↔ TickStockPL)  
**Use When**: Redis message flow validation, database integration testing, end-to-end workflow verification  
**Expertise**: Message delivery performance, system resilience, loose coupling validation  
**Key Focus**: <100ms message delivery, role boundary enforcement, system health validation

#### `code-security-specialist`
**Domain**: Security analysis for TickStockAppV2 real-time market data system  
**MANDATORY Usage**: AUTOMATICALLY triggered for ALL security-sensitive code changes  
**Auto-Triggers**: WebSocket implementations, API endpoints, authentication logic, database queries, Redis integration, frontend user input handling, credential management  
**Expertise**: Financial system security, WebSocket security, API protection, frontend XSS/CSRF prevention, secret detection, dependency vulnerability scanning  
**Key Focus**: Performance-aware security (<100ms maintained), financial data protection, zero secret exposure, secure real-time communication  
**Quality Gate**: No security-sensitive feature/fix is complete without comprehensive security analysis

### Architecture & Documentation Agents

#### `documentation-sync-specialist`
**Domain**: Documentation alignment and consistency across planning documents  
**Use When**: Cross-reference validation, architecture consistency checking, sprint documentation updates  
**Expertise**: Terminology standardization, navigation updates, consolidated information architecture maintenance  
**Key Focus**: Single source of truth, consistent cross-references, evolution tracking

#### `architecture-validation-specialist`
**Domain**: Architecture compliance and role separation enforcement  
**MANDATORY Usage**: AUTOMATICALLY triggered as first step of ANY development task  
**Auto-Triggers**: Before any implementation, during design review, after major changes  
**Expertise**: Redis pub-sub pattern validation, database access control, performance pattern compliance  
**Key Focus**: TickStockApp (consumer) vs TickStockPL (producer) separation, loose coupling via Redis  
**Pre-Implementation Gate**: MUST validate approach before coding begins

### Agent Cascading & Dependencies (AUTOMATIC)

**CRITICAL**: Some agents automatically trigger others - this is MANDATORY:

#### Primary → Secondary Cascades
- **`tickstock-test-specialist`** → `integration-testing-specialist` (for Redis/cross-system testing)
- **`appv2-integration-specialist`** → `database-query-specialist` (for UI data requirements)
- **`redis-integration-specialist`** → `integration-testing-specialist` (for message flow validation)
- **`code-security-specialist`** → `tickstock-test-specialist` (for security test integration)
- **ANY agent** → `documentation-sync-specialist` (if documentation changes)

#### Multi-Agent Requirements
**Core Processing Changes**: `architecture-validation-specialist` + `tickstock-test-specialist` + `integration-testing-specialist` + `code-security-specialist`  
**UI/Database Work**: `appv2-integration-specialist` + `database-query-specialist` + `architecture-validation-specialist` + `code-security-specialist`  
**Redis/Integration**: `redis-integration-specialist` + `integration-testing-specialist` + `architecture-validation-specialist` + `code-security-specialist`  
**Security-Sensitive Changes**: `code-security-specialist` + `architecture-validation-specialist` + `tickstock-test-specialist`

### Development Phase Gates (MANDATORY CHECKPOINTS)

#### Phase 1: Analysis & Design (REQUIRED)
1. `architecture-validation-specialist` - Validate approach, identify anti-patterns
2. Domain specialist based on Auto-Triggers - Domain-specific requirements
3. Get explicit approval before proceeding to implementation

#### Phase 2: Implementation (REQUIRED)
1. Continuous agent consultation during development
2. Domain specialists provide real-time guidance
3. Architecture validation at major decision points

#### Phase 3: Quality Assurance (REQUIRED)
1. `tickstock-test-specialist` - Comprehensive test generation (MANDATORY)
2. `integration-testing-specialist` - Cross-system validation (MANDATORY)
3. `code-security-specialist` - Security analysis for security-sensitive changes (MANDATORY)
4. Performance validation against targets (<100ms, <50ms)

#### Phase 4: Documentation & Finalization (REQUIRED)
1. `documentation-sync-specialist` - Update all documentation
2. `architecture-validation-specialist` - Final compliance check
3. Cross-reference validation and consistency checks

### Agent Performance Requirements

#### All Agents MUST Enforce
- **Performance Targets**: <100ms WebSocket delivery, <50ms database queries
- **Role Boundaries**: TickStockApp (Consumer) vs TickStockPL (Producer) separation
- **Architecture Patterns**: Pull Model, Redis pub-sub loose coupling, zero event loss
- **Security Standards**: Zero secret exposure, WebSocket authentication, secure real-time communication
- **Quality Standards**: Comprehensive testing, security analysis, documentation consistency

#### Agent Coordination Protocol
- All agents reference consolidated documentation (`project-overview.md`, `system-architecture.md`)
- Agents communicate findings and recommendations across the workflow
- Blocking issues require resolution before proceeding to next phase
- Performance violations are automatic failures requiring remediation

## Recent Major Updates

### Pattern Discovery API Integration (Sprint 19)
**Date**: 2025-09-04  
**Status**: ✅ COMPLETE  
**Architecture**: 100% Redis Consumer Pattern Compliance  
**Changes**:
- **Pattern Discovery APIs**: Complete REST endpoints for pattern data consumption (`/api/patterns/*`)
- **Redis Pattern Cache**: Multi-layer caching system consuming TickStockPL events via Redis pub-sub
- **User Universe APIs**: Symbol management and watchlist APIs (`/api/users/*`, `/api/symbols`)
- **Consumer Architecture**: Zero direct pattern database queries - all via Redis cache consumption
- **Performance Optimization**: <50ms API responses, >70% cache hit ratio achieved
- **Service Integration**: `PatternDiscoveryService` orchestrates all components with health monitoring

**New Components**:
```python
# Core Pattern Discovery Integration
from src.api.rest.pattern_discovery import init_app

# Individual Components
from src.infrastructure.cache.redis_pattern_cache import RedisPatternCache
from src.api.rest.pattern_consumer import pattern_consumer_bp
from src.api.rest.user_universe import user_universe_bp
from src.core.services.pattern_discovery_service import PatternDiscoveryService
```

**Integration Pattern**:
```python
# Flask app initialization
def create_app():
    app = Flask(__name__)
    success = init_app(app)  # Initializes Pattern Discovery APIs
    return app
```

**API Endpoints Available**:
- `GET /api/patterns/scan` - Pattern scanning with Redis cache consumption
- `GET /api/patterns/stats` - Cache performance metrics
- `GET /api/symbols` - Symbol dropdown data (read-only database)
- `GET /api/users/universe` - Available universe selections
- `GET /api/pattern-discovery/health` - Comprehensive service health

**Architecture Compliance**:
- ✅ **Consumer Role**: TickStockApp consumes Redis events only, zero pattern DB queries
- ✅ **Producer Role**: TickStockPL publishes pattern events to Redis channels
- ✅ **Loose Coupling**: All communication via Redis pub-sub (`tickstock.events.patterns`)
- ✅ **Performance**: <50ms API responses via multi-layer Redis caching
- ✅ **Pull Model**: Existing zero-event-loss architecture preserved

**Testing**: Comprehensive test suite with 188 tests in `tests/sprint19/`

**Breaking Changes**: None - fully additive implementation

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
**CRITICAL**: Use `rg` (ripgrep) instead of traditional `grep` and `find` commands. See `docs/development/coding-practices.md` for complete search command patterns and examples.