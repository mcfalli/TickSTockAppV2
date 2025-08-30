# TickStock.ai Planning Documentation

**Last Updated**: 2025-08-30  
**Status**: Post-Reorganization - Focused Planning Content

---

## 📚 Planning Documentation Overview

This folder contains the core planning documentation for TickStock.ai, focusing on **what to build** and **why**. For technical implementation details and operational guides, see the reorganized documentation structure below.

---

## 📋 Core Planning Documents

### Project Vision & Requirements
- **[`project-overview.md`](project-overview.md)** - **START HERE**: Complete system vision, requirements, architecture principles, and technical foundation
- **[`user_stories.md`](user_stories.md)** - Development requirements captured in user story format
- **[`user_stories_2.md`](user_stories_2.md)** - Next phase user stories for upcoming development

### Pattern Library Planning
- **[`pattern_library_overview.md`](pattern_library_overview.md)** - Pattern library goals, categories, and integration overview
- **[`patterns_library_patterns.md`](patterns_library_patterns.md)** - Detailed pattern specifications for TickStockPL implementation

### Documentation Evolution
- **[`evolution_index.md`](evolution_index.md)** - Complete documentation catalog with purpose explanations

---

## 🗂️ Reorganized Documentation Structure

The documentation has been reorganized for better navigation and maintenance:

### Technical Architecture
**Moved to**: [`../architecture/`](../architecture/)
- `system-architecture.md` - Complete system architecture and role separation
- `database-architecture.md` - Database schema and optimization
- `pattern-library-architecture.md` - Pattern detection technical framework
- `websockets-integration.md` - Real-time communication architecture
- `pydantic-implementation.md` - Data validation and serialization

### Operational Guides
**Moved to**: [`../guides/`](../guides/)
- `startup-guide.md` - TickStockAppV2 startup instructions
- `startup-integrated-guide.md` - Integrated system startup
- `integration-guide.md` - TickStockPL integration procedures
- `historical-data-loading.md` - Historical data loading procedures
- `administration-system.md` - System administration guide
- `technical-analysis-indicators.md` - Advanced pattern implementation guide

---

## 🎯 Quick Navigation

### For New Developers
1. **[`project-overview.md`](project-overview.md)** - Understand the complete system vision
2. **[`../architecture/system-architecture.md`](../architecture/system-architecture.md)** - Learn system boundaries and communication
3. **[`user_stories.md`](user_stories.md)** - Review development requirements

### For TickStockPL Integration
1. **[`project-overview.md`](project-overview.md)** - System vision and integration context
2. **[`../architecture/system-architecture.md`](../architecture/system-architecture.md)** - Role separation and communication patterns
3. **[`../guides/integration-guide.md`](../guides/integration-guide.md)** - Complete integration procedures

### For System Architecture
1. **[`../architecture/`](../architecture/)** - Technical architecture specifications
2. **[`../guides/`](../guides/)** - Operational and setup guides
3. **[`pattern_library_overview.md`](pattern_library_overview.md)** - Pattern library planning

### For Current Development
1. **[`user_stories_2.md`](user_stories_2.md)** - Next phase requirements
2. **[`patterns_library_patterns.md`](patterns_library_patterns.md)** - Pattern specifications
3. **[`evolution_index.md`](evolution_index.md)** - Documentation tracking

---

## 📁 Related Documentation Folders

- **[`../architecture/`](../architecture/)** - Technical system architecture specifications
- **[`../guides/`](../guides/)** - Operational setup and integration procedures  
- **[`../development/`](../development/)** - Development guidelines and standards

---

## 🔄 Documentation Evolution

### What Changed (2025-08-30)
- **Reorganized Structure**: Moved technical architecture to `../architecture/`
- **Operational Focus**: Moved guides to `../guides/` for better discoverability
- **Planning Focus**: Kept true planning content (vision, requirements, user stories)
- **Cross-References**: Updated all links to reflect new organization
- **Single Sources**: Maintained single sources of truth with clear navigation

### What Remained in Planning
- **Project Vision**: Complete system overview and requirements
- **User Stories**: Development requirements and next phase planning  
- **Pattern Planning**: Pattern library scope and specifications
- **Evolution Tracking**: Documentation catalog and change management

---

This planning documentation provides the strategic foundation for TickStock.ai development, focusing on the clear separation between TickStockApp (UI consumer) and TickStockPL (analytical producer) with Redis-based loose coupling.