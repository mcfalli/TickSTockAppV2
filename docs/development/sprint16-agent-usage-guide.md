# Sprint 16 Agent Usage Guide: Grid Modernization Implementation

**Generated**: 2025-09-02  
**Sprint**: 16 - Dashboard Grid Modernization  
**Purpose**: Comprehensive guide for when and how to use each specialized agent during Sprint 16 implementation

## Overview

Sprint 16 focuses on transforming the tabbed interface into a modern grid-based dashboard layout using grid-stack.js. This guide provides specific agent usage patterns for each phase of implementation, ensuring architecture compliance and comprehensive testing throughout the sprint.

## Mandatory Agent Usage Workflow

### Phase 1: Pre-Implementation Analysis (REQUIRED)
Before ANY Sprint 16 work begins:

1. **`architecture-validation-specialist`** - MANDATORY first step
   - Validates grid-stack integration approach
   - Reviews UI architecture compliance
   - Ensures TickStockApp consumer role boundaries
   - Identifies potential violations before coding

2. **`appv2-integration-specialist`** - Domain analysis
   - Reviews grid-stack integration patterns
   - Validates WebSocket connection preservation
   - Ensures UI responsiveness requirements
   - Plans database read-only access patterns

### Phase 2: Implementation (CONTINUOUS)
During active development, agents provide ongoing guidance:

3. **Domain specialists** - Based on work area (see Auto-Triggers below)
4. **`documentation-sync-specialist`** - For any documentation updates

### Phase 3: Quality Assurance (MANDATORY)
After implementation, before completion:

5. **`tickstock-test-specialist`** - REQUIRED for all code changes
6. **`integration-testing-specialist`** - REQUIRED for system integration
7. **Final architecture validation** - Compliance confirmation

## Sprint 16 Agent Auto-Triggers

### **AUTOMATIC Triggers by Task Type**

#### Grid Layout Tasks (TASK-001, TASK-002, TASK-003)
**Required Agents**:
- `architecture-validation-specialist` (pre-implementation)
- `appv2-integration-specialist` (implementation)
- `tickstock-test-specialist` (testing)

**Trigger Conditions**:
- Modifying `app-gridstack.js`
- Changes to `index.html` layout structure
- Removing navigation elements
- Adding new grid containers

**Example Usage**:
```bash
# TASK-001: Before modifying app-gridstack.js
"I need to extend the grid configuration to support 6 containers in a 2x4 layout. 
Let me start with architecture validation."

# This AUTOMATICALLY triggers:
# 1. architecture-validation-specialist - validate approach
# 2. appv2-integration-specialist - implement grid changes
# 3. tickstock-test-specialist - test grid functionality
```

#### Content Migration Tasks (TASK-004 through TASK-007)
**Required Agents**:
- `architecture-validation-specialist` (pre-implementation)
- `appv2-integration-specialist` (implementation)
- `redis-integration-specialist` (WebSocket preservation)
- `tickstock-test-specialist` (testing)
- `integration-testing-specialist` (system integration)

**Trigger Conditions**:
- Migrating Watchlist, Market Summary, Charts, or Alerts
- Preserving WebSocket connections
- Maintaining real-time functionality
- UI component restructuring

**Example Usage**:
```bash
# TASK-004: Before migrating Watchlist
"I need to migrate the Watchlist tab content to a grid container while preserving 
WebSocket real-time updates and all existing functionality."

# This AUTOMATICALLY triggers:
# 1. architecture-validation-specialist - validate migration approach
# 2. appv2-integration-specialist - handle UI migration
# 3. redis-integration-specialist - ensure WebSocket preservation
# 4. tickstock-test-specialist - test migrated functionality
# 5. integration-testing-specialist - validate real-time features
```

#### API Integration Tasks (TASK-008: Market Movers Widget)
**Required Agents**:
- `architecture-validation-specialist` (pre-implementation)
- `appv2-integration-specialist` (implementation)
- `database-query-specialist` (if database access needed)
- `tickstock-test-specialist` (testing)
- `integration-testing-specialist` (API integration testing)

**Trigger Conditions**:
- Integrating Polygon.io API
- Adding new data fetching services
- Creating display components
- Implementing auto-refresh functionality

**Example Usage**:
```bash
# TASK-008: Before implementing Market Movers
"I need to create a Market Movers widget using the Polygon.io API with 60-second 
auto-refresh and error handling for API failures."

# This AUTOMATICALLY triggers:
# 1. architecture-validation-specialist - validate API integration approach
# 2. appv2-integration-specialist - implement widget
# 3. database-query-specialist - if caching data locally
# 4. tickstock-test-specialist - test widget functionality
# 5. integration-testing-specialist - test API integration
```

#### Testing & Documentation Tasks (TASK-012 through TASK-015)
**Required Agents**:
- `tickstock-test-specialist` (performance and cross-browser testing)
- `integration-testing-specialist` (system integration testing)
- `documentation-sync-specialist` (documentation updates)

## Agent-Specific Usage Scenarios

### `architecture-validation-specialist`

**When to Use**:
- **MANDATORY**: Before every Sprint 16 task
- Before modifying UI architecture
- When integrating external APIs (Polygon.io)
- Before removing existing functionality

**Sprint 16 Focus Areas**:
- Ensure grid-stack integration doesn't violate TickStockApp consumer role
- Validate no heavy processing in UI components
- Confirm proper separation between UI display and data processing
- Check for performance anti-patterns in grid operations

**Example Scenarios**:
```bash
# Before TASK-001 (Grid Configuration)
"Validate that extending app-gridstack.js for 6 containers maintains 
architecture compliance and doesn't introduce performance issues."

# Before TASK-008 (Market Movers API)
"Validate that integrating Polygon.io Market Movers API maintains 
TickStockApp consumer role and uses proper async patterns."
```

### `appv2-integration-specialist`

**When to Use**:
- All grid layout modifications (TASK-001, TASK-002, TASK-003)
- Content migration tasks (TASK-004 through TASK-007)
- New widget implementation (TASK-008)
- UI optimization tasks (TASK-010, TASK-011)

**Sprint 16 Expertise**:
- Grid-stack.js integration patterns
- WebSocket connection preservation during migration
- UI component restructuring
- Flask/SocketIO integration maintenance

**Example Scenarios**:
```bash
# TASK-003: Container Expansion
"Modify index.html to add 5 more grid-stack containers while maintaining 
proper initialization and interactive functionality."

# TASK-005: Market Summary Migration
"Extract Market Summary tab content and integrate into grid container 
while preserving data refresh logic and formatting."
```

### `database-query-specialist`

**When to Use**:
- If Market Movers widget needs local data caching
- When migrating components that query dashboard statistics
- If adding new database-backed features

**Sprint 16 Context**:
- Market Movers widget may cache data locally
- Preserve existing read-only query patterns
- Maintain <50ms query performance targets

**Example Scenarios**:
```bash
# TASK-008: If caching Market Movers data
"Design read-only queries to cache Market Movers data locally for 
improved performance while maintaining data freshness."
```

### `redis-integration-specialist`

**When to Use**:
- Content migration tasks involving WebSocket connections
- When preserving real-time functionality during migration
- If implementing new pub-sub patterns

**Sprint 16 Focus**:
- Ensure WebSocket connections survive grid migration
- Validate real-time updates work in new containers
- Preserve message delivery performance (<100ms)

**Example Scenarios**:
```bash
# TASK-004: Watchlist Migration
"Ensure WebSocket connections for real-time price updates are preserved 
when migrating Watchlist from tab to grid container."

# TASK-007: Alerts Migration
"Preserve real-time alert notifications and WebSocket connections 
during migration to grid container format."
```

### `tickstock-test-specialist`

**When to Use**:
- **MANDATORY**: After every code change in Sprint 16
- All grid functionality testing
- Performance validation
- Cross-browser compatibility testing

**Sprint 16 Testing Focus**:
- Grid-stack functionality (drag, resize, layout)
- Real-time features preservation
- Performance benchmarks (<3s load, <100ms WebSocket)
- Mobile responsiveness

**Example Scenarios**:
```bash
# After TASK-003: Container implementation
"Generate comprehensive tests for 6-container grid layout including 
drag/resize functionality, responsive behavior, and initialization."

# After TASK-008: Market Movers widget
"Create tests for Market Movers widget including API integration, 
auto-refresh, error handling, and performance validation."
```

### `integration-testing-specialist`

**When to Use**:
- **MANDATORY**: For any system integration changes
- WebSocket functionality preservation
- End-to-end workflow validation
- Performance integration testing

**Sprint 16 Integration Focus**:
- Real-time data flow through new grid containers
- WebSocket message delivery performance
- Cross-system communication validation

**Example Scenarios**:
```bash
# After content migration tasks
"Validate end-to-end real-time data flow from backend to grid containers, 
ensuring <100ms message delivery and zero data loss."

# After Market Movers implementation
"Test integration between Polygon.io API, local caching, and grid display 
with proper error handling and performance validation."
```

### `documentation-sync-specialist`

**When to Use**:
- **MANDATORY**: For TASK-015 (documentation updates)
- When modifying architecture or adding new features
- Sprint completion documentation

**Sprint 16 Documentation**:
- Update grid-stack configuration documentation
- Document new Market Movers widget integration
- Update user guides for new dashboard layout

**Example Scenarios**:
```bash
# TASK-015: Documentation updates
"Update all documentation to reflect new grid-based dashboard layout, 
including configuration guides and troubleshooting information."
```

## Phase-by-Phase Agent Workflow

### **Phase 1: Grid Configuration (Day 1)**

**Tasks**: TASK-001, TASK-002  
**Agent Sequence**:
1. `architecture-validation-specialist` - Pre-implementation validation
2. `appv2-integration-specialist` - Grid configuration implementation
3. `tickstock-test-specialist` - Grid functionality testing

```bash
# Example workflow:
"Starting Phase 1: Grid Configuration. Need to extend app-gridstack.js for 6 containers 
and remove deprecated navigation links."

# Automatic agent cascade:
# 1. Architecture validation of grid approach
# 2. Implementation of grid changes
# 3. Testing of grid functionality
```

### **Phase 2: Layout Restructuring (Days 2-3)**

**Tasks**: TASK-003  
**Agent Sequence**:
1. `architecture-validation-specialist` - Layout change validation
2. `appv2-integration-specialist` - Container expansion implementation
3. `tickstock-test-specialist` - Interactive functionality testing

### **Phase 3: Content Migration (Days 4-7)**

**Tasks**: TASK-004, TASK-005, TASK-006, TASK-007  
**Agent Sequence** (for each migration):
1. `architecture-validation-specialist` - Migration approach validation
2. `appv2-integration-specialist` - Content migration implementation
3. `redis-integration-specialist` - WebSocket preservation validation
4. `tickstock-test-specialist` - Functionality testing
5. `integration-testing-specialist` - End-to-end validation

```bash
# Example workflow per migration:
"Migrating [Watchlist/Market Summary/Charts/Alerts] from tab to grid container 
while preserving all functionality and real-time features."

# Full agent cascade for each migration ensures comprehensive coverage
```

### **Phase 4: New Features (Days 8-9)**

**Tasks**: TASK-008, TASK-009  
**Agent Sequence**:
1. `architecture-validation-specialist` - API integration validation
2. `appv2-integration-specialist` - Widget implementation
3. `database-query-specialist` - If local caching needed
4. `tickstock-test-specialist` - Widget functionality testing  
5. `integration-testing-specialist` - API integration testing

### **Phase 5: Cleanup & Optimization (Days 10-11)**

**Tasks**: TASK-010, TASK-011  
**Agent Sequence**:
1. `architecture-validation-specialist` - Cleanup validation
2. `appv2-integration-specialist` - Code and CSS optimization
3. `tickstock-test-specialist` - Performance validation

### **Phase 6: Testing & Documentation (Days 12-14)**

**Tasks**: TASK-012, TASK-013, TASK-014, TASK-015  
**Agent Sequence**:
1. `tickstock-test-specialist` - Cross-browser and mobile testing
2. `integration-testing-specialist` - Performance integration testing
3. `documentation-sync-specialist` - Documentation updates

## Common Anti-Patterns to Avoid

### **DON'T Use Agents For**:
- Simple CSS styling changes without logic modifications
- Minor text content updates
- Basic HTML structure changes without functionality impact

### **DO Use Agents For**:
- Any JavaScript functionality changes
- WebSocket or real-time feature modifications
- API integrations or new data sources
- Performance-critical modifications
- Architecture or structural changes

## Agent Coordination Examples

### **Multi-Agent Workflow Example**:
```bash
# TASK-004: Watchlist Migration
User: "I need to migrate the Watchlist tab to a grid container while preserving 
real-time price updates and all existing functionality."

# Automatic agent sequence:
# 1. architecture-validation-specialist: 
#    "Validating Watchlist migration approach for architecture compliance..."
#    
# 2. appv2-integration-specialist:
#    "Implementing Watchlist migration with preserved functionality..."
#    
# 3. redis-integration-specialist:
#    "Ensuring WebSocket connections are preserved during migration..."
#    
# 4. tickstock-test-specialist:
#    "Creating comprehensive tests for migrated Watchlist functionality..."
#    
# 5. integration-testing-specialist:
#    "Validating end-to-end real-time data flow in new container..."
```

### **Single-Agent Workflow Example**:
```bash
# TASK-011: CSS Optimization
User: "I need to consolidate and optimize CSS for the new grid layout."

# Single agent usage:
# 1. appv2-integration-specialist only (if no functionality changes)
#    "Optimizing CSS for grid layout with responsive behavior..."
#
# But if performance implications:
# 2. tickstock-test-specialist: "Testing performance impact of CSS changes..."
```

## Sprint 16 Success Criteria

### **Agent Coverage Requirements**:
- ✅ Every task must start with `architecture-validation-specialist`
- ✅ Every code change must include `tickstock-test-specialist`
- ✅ WebSocket-related tasks must include `redis-integration-specialist`
- ✅ API integration must include `integration-testing-specialist`
- ✅ Documentation updates must include `documentation-sync-specialist`

### **Performance Validation**:
- Page load time < 3 seconds (tested by `tickstock-test-specialist`)
- WebSocket latency < 100ms (validated by `integration-testing-specialist`)
- Smooth drag/resize operations (tested by `tickstock-test-specialist`)

### **Architecture Compliance**:
- No heavy processing in UI components (validated by `architecture-validation-specialist`)
- Proper TickStockApp consumer role maintenance (enforced throughout)
- Redis pub-sub patterns preserved (validated by `redis-integration-specialist`)

## Quick Reference Decision Tree

```
Task involves JavaScript changes?
├── YES → Use tickstock-test-specialist (MANDATORY)
│   ├── Changes WebSocket functionality? → Add redis-integration-specialist
│   ├── Changes API integration? → Add integration-testing-specialist  
│   ├── Changes architecture? → Add architecture-validation-specialist (MANDATORY first)
│   └── UI changes only? → Use appv2-integration-specialist
└── NO → Consider if agents needed based on impact
```

## Documentation References

- **Sprint 16 Tasks**: [`sprint16-tasks.md`](../../planning/sprints/sprint16/sprint16-tasks.md)
- **Agent Instructions**: [`.claude/agents/`](../../.claude/agents/) - Individual agent capabilities
- **Architecture Guidelines**: [`system-architecture.md`](../../architecture/system-architecture.md)
- **Development Standards**: [`unit_testing.md`](unit_testing.md), [`coding-practices.md`](coding-practices.md)

## Summary

This guide ensures Sprint 16 grid modernization maintains TickStock's architecture principles while leveraging specialized agents for comprehensive validation, implementation, and testing. Every task follows the mandatory agent workflow to guarantee quality and compliance throughout the sprint.

**Remember**: When in doubt, start with `architecture-validation-specialist` and let the auto-triggers guide the agent selection process. The agents are designed to work together systematically to ensure Sprint 16's success.