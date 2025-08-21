# CLAUDE.md

This file provides comprehensive guidance to Claude Code when working with Python code in this repository.

**Important** - CLAUDE documentation is stored local at ./claude-code-docs to reference not having to go out to anthropic to find documentation. This is kept current daily.

_This document is a living guide. Update it as the project evolves and new patterns emerge._

## About TickStock

### What is TickStock?
TickStock is a high-performance, real-time market data processing system that handles 4,000+ stock tickers with sub-millisecond event detection. It processes WebSocket data streams from Polygon.io (production) or synthetic data (development) and delivers personalized, filtered market events to users via WebSocket connections.

### Core Value Proposition
- Real-time processing of market data with <100ms end-to-end latency
- Zero event loss through Pull Model architecture
- Per-user filtering and personalization

### Technology Stack
- **Backend**: Python 3.x, Flask, Flask-SocketIO, Eventlet
- **Frontend**: JavaScript ES6+ SPA with Socket.IO client
- **Database**: PostgreSQL with SQLAlchemy
- **Cache**: Redis for user preferences and universe caching
- **Data Provider**: Polygon.io (live) / Synthetic (dev/test)
- **Architecture**: Component-based with Pull Model Event Distribution

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
- See `docs/new/project_structure.md` for complete folder organization
- See `docs/new/project_structure_docs.md` for documentation structure

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

#### Quick Reference
- **New Event Type**: Create class → Add detection → Implement transport → Update routing
- **Database Changes**: Always provide ALTER and CREATE statements with proper grants

## Testing & Reliability

### Testing Framework
***TickStock uses a comprehensive testing strategy with pytest for quality assurance and performance verification.***

**Comprehensive Testing Guidelines**: See `docs/instructions/unit_testing.md` for complete testing standards, organization structure, sprint requirements, and best practices.

#### Key Testing Principles
- **Quality First**: No feature is complete without tests
- **Performance Critical**: Sub-millisecond processing requires performance validation
- **Functional Organization**: Tests organized by business domain (event_processing, data_processing, etc.)
- **Sprint-Specific**: Each sprint creates tests in appropriate functional area with sprint subfolders

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

## Important Operating Guidelines

### Critical Rules
- **NEVER ASSUME OR GUESS** - When in doubt, ask for clarification
- **Always verify file paths and module names** before use
- **Keep CLAUDE.md updated** when adding new patterns or dependencies
- **Follow all development standards** - See Development Standards & Processes section above
- **Document your decisions** - Future developers (including yourself) will thank you

### Search Command Requirements
**CRITICAL**: Use `rg` (ripgrep) instead of traditional `grep` and `find` commands. See `docs/instructions/coding-practices.md` for complete search command patterns and examples.