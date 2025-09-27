# Documentation Archive Map
Generated: 2025-09-26

## Purpose
This file maps the old documentation structure to the new streamlined version.
Original doc count: 262 files → Target: ~15 files

## Archived/Removed Directories
- agents/ → Moved to .claude/agents/
- analysis/ → Archived (outdated sprint artifacts)
- recommendations/ → Archived (historical analysis)
- development/ → Merged into guides/
- implementation/ → Merged into guides/
- operations/ → Moved to wiki/issues
- troubleshooting/ → Moved to wiki/issues
- testing/ → Merged into guides/testing.md

## Consolidation Map

### Architecture (24 files → 4 files)
- Kept: redis-integration.md, websockets-integration.md, configuration.md
- Merged into README.md: system-architecture, project-overview, database-architecture
- Removed: Pattern-specific docs (moved to TickStockPL)

### Guides (21 files → 3 files)
- quickstart.md: Merged startup-guide, startup-integrated-guide, integration-guide
- configuration.md: Merged settings-configuration, administration-system
- testing.md: Consolidated from testing/ folder
- Removed: 15 web_*.md files (consolidated into API docs)

### API (Multiple files → 1 file)
- endpoints.md: Merged all API documentation

### Data Sources
- Kept minimal Polygon configuration docs
- Removed internal CSV lists and data definitions

## Notes
- Planning folder retained for sprint management (user cleanup)
- Core files retained: README.md, about_tickstock.md, project_structure.md