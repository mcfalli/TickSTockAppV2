# Documentation Archive Map
Generated: 2025-09-26
Updated: 2025-09-27

## Purpose
This file maps the old documentation structure to the new streamlined version.
Original doc count: 262 files → Current: ~10 core files

## Phase 1: Initial Cleanup (Sept 26)

### Archived/Removed Directories
- agents/ → Moved to .claude/agents/
- analysis/ → Archived (outdated sprint artifacts)
- recommendations/ → Archived (historical analysis)
- development/ → Merged into guides/
- implementation/ → Merged into guides/
- operations/ → Moved to wiki/issues
- troubleshooting/ → Moved to wiki/issues
- testing/ → Merged into guides/testing.md

### Consolidation Map

#### Architecture (24 files → 4 files)
- Kept: redis-integration.md, websockets-integration.md, configuration.md
- Merged into README.md: system-architecture, project-overview, database-architecture
- Removed: Pattern-specific docs (moved to TickStockPL)

#### API (Multiple files → 1 file)
- endpoints.md: Merged all API documentation

## Phase 2: Guides Cleanup (Sept 27)

### Guides Folder (25 files → 3 files)

#### Created New Consolidated Guides:
1. **quickstart.md** - Merged content from:
   - startup-guide.md
   - startup-integrated-guide.md
   - integration-guide.md
   - historical-data-loading.md (data loading sections)

2. **configuration.md** - Merged content from:
   - settings-configuration.md
   - data-source-configuration.md
   - administration-system.md (admin configuration)
   - historical_data_production_setup.md

3. **testing.md** - New comprehensive testing guide

#### Deleted Files (22 total):
**Redundant guides:**
- administration-system.md → Merged into configuration.md
- data-source-configuration.md → Merged into configuration.md
- historical_data_production_setup.md → Merged into configuration.md
- historical-data-loading.md → Merged into quickstart.md
- integration-guide.md → Merged into quickstart.md
- polygon-summarized-guide.md → Should be in data-sources/
- settings-configuration.md → Merged into configuration.md
- startup-guide.md → Merged into quickstart.md
- startup-integrated-guide.md → Merged into quickstart.md
- technical-analysis-indicators.md → TickStockPL concern
- README.md (guides folder index) → No longer needed

**Web UI navigation files (11 files):**
- web_index.md
- web_overview_nav.md
- web_pattern_discovery_nav.md
- web_performance_nav.md
- web_distribution_nav.md
- web_historical_nav.md
- web_market_nav.md
- web_correlations_nav.md
- web_temporal_nav.md
- web_compare_nav.md
- web_sprint25_integration.md

**Maintenance folder (4 files):**
- maintenance/README.md
- maintenance/cache-entries-loading.md
- maintenance/historical-data-loading.md
- maintenance/stocks-loading.md

## Phase 3: Root Docs Cleanup (Sept 27)

### Deleted Root Files:
- CURRENT_STATUS.md → Sprint 26 historical status
- INDEX.md → Old navigation with incorrect paths
- TickStock About.md → Duplicate of about_tickstock.md

## Final Documentation Structure

```
docs/
├── README.md                  # Main documentation entry
├── about_tickstock.md         # Platform overview
├── project_structure.md       # Codebase organization
├── ARCHIVE_MAP.md            # This file - migration reference
├── architecture/
│   ├── README.md             # Consolidated architecture
│   ├── redis-integration.md  # Redis pub-sub patterns
│   ├── websockets-integration.md # WebSocket communication
│   └── configuration.md      # Environment setup
├── guides/
│   ├── quickstart.md         # Getting started guide
│   ├── configuration.md      # Configuration reference
│   └── testing.md            # Testing strategies
├── api/
│   └── endpoints.md          # Complete API documentation
├── data/                     # Data definitions (unchanged)
├── data-sources/             # External data sources (unchanged)
└── planning/                 # Sprint planning (user managed)
```

## Phase 4: Development Folder Removal (Sept 27)

### Deleted Entire Folder (12 files)
- Coding practices → Merged key points into CLAUDE.md
- Sprint-specific guides → Removed (outdated)
- Agent configuration → Already in .claude/agents
- Testing documentation → Already in guides/testing.md
- All other development docs → Redundant or outdated

**Files deleted:**
- advanced-features-implementation-guide.md
- agent-configuration-guide.md
- agent-review-2025-09-23.md
- architectural-decision-process.md
- code-documentation-standards.md
- coding-practices.md
- grid-stack.md
- README.md
- sprint14-execution-testing-guide.md
- sprint16-agent-usage-guide.md
- technical-debt-management.md
- unit_testing.md

## Phase 5: Architecture Consolidation (Sept 27)

### Architecture Folder (19 files → 4 files)

#### Kept Core Files:
1. **README.md** - Main consolidated architecture
2. **redis-integration.md** - Critical pub-sub patterns
3. **websockets-integration.md** - Real-time communication
4. **configuration.md** - Environment setup

#### Deleted Files (15 total):
**Merged into README.md:**
- system-architecture.md
- project-overview.md
- simplified-technical-overview.md
- database-architecture.md
- data-integration.md

**TickStockPL specific (not AppV2):**
- tickstockpl-architecture.md
- pattern-library-architecture.md
- pattern-processing-flow.md
- pydantic-implementation.md

**Redundant/outdated:**
- websocket-scalability-architecture.md (overly detailed)
- websocket-pattern-events.md (too specific)
- user-authentication.md (in configuration.md)
- rest-endpoints.md (moved to api/endpoints.md)
- error_handling_architecture.md (sprint-specific)
- architectural_decisions.md (process doc)

## Summary Statistics
- **Original files**: 262
- **Files deleted**: ~280+ (including folders)
- **Current core docs**: ~10
- **Reduction**: 96% fewer files
- **Benefit**: Easier to maintain, find, and update documentation