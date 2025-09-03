# Sprint 16 Agent Usage Quick Reference

## MANDATORY WORKFLOW
Every Sprint 16 task MUST follow this sequence:
1. **Pre-Implementation**: `architecture-validation-specialist` reviews approach
2. **Implementation**: Domain-specific agents guide development
3. **Quality Gate**: `tickstock-test-specialist` + `integration-testing-specialist` validate

## AUTO-TRIGGERS FOR SPRINT 16

### Grid Configuration Tasks (TASK-001, TASK-003)
**Trigger**: Modifying app-gridstack.js or adding grid containers
**Required Agents**:
1. `architecture-validation-specialist` - Review grid patterns
2. `appv2-integration-specialist` - Implement grid changes
3. `tickstock-test-specialist` - Test grid functionality

### Content Migration Tasks (TASK-004 to TASK-007)
**Trigger**: Moving tab content to grid containers
**Required Agents**:
1. `architecture-validation-specialist` - Ensure proper separation
2. `appv2-integration-specialist` - Migrate UI components
3. `redis-integration-specialist` - Preserve WebSocket connections
4. `integration-testing-specialist` - Validate real-time updates
5. `tickstock-test-specialist` - Comprehensive testing

### Market Movers Widget (TASK-008)
**Trigger**: Implementing Polygon.io API integration
**Required Agents**:
1. `architecture-validation-specialist` - API pattern review
2. `appv2-integration-specialist` - Widget implementation
3. `redis-integration-specialist` - If caching needed
4. `integration-testing-specialist` - API integration testing
5. `tickstock-test-specialist` - Widget testing

### Cleanup Tasks (TASK-010, TASK-011)
**Trigger**: Removing tab infrastructure, optimizing CSS
**Required Agents**:
1. `architecture-validation-specialist` - Ensure nothing breaks
2. `appv2-integration-specialist` - Cleanup implementation
3. `tickstock-test-specialist` - Regression testing

### Testing Tasks (TASK-012 to TASK-014)
**Trigger**: Cross-browser, mobile, performance testing
**Required Agents**:
1. `tickstock-test-specialist` - Primary testing
2. `integration-testing-specialist` - System integration
3. `architecture-validation-specialist` - Performance compliance

### Documentation (TASK-015)
**Trigger**: Updating documentation
**Required Agents**:
1. `documentation-sync-specialist` - Update all docs
2. `architecture-validation-specialist` - Review accuracy

## QUICK DECISION TREE

```
Is it a UI/Frontend change?
├─ YES → appv2-integration-specialist (PRIMARY)
│   └─ Does it affect WebSocket/real-time?
│       ├─ YES → redis-integration-specialist
│       └─ NO → Continue
└─ NO → Continue

Is it an API integration?
├─ YES → integration-testing-specialist (PRIMARY)
│   └─ Need caching?
│       ├─ YES → redis-integration-specialist
│       └─ NO → Continue
└─ NO → Continue

Does it touch the database?
├─ YES → database-query-specialist
└─ NO → Continue

ALWAYS:
- START with architecture-validation-specialist
- END with tickstock-test-specialist
- UPDATE docs with documentation-sync-specialist
```

## SPRINT 16 SPECIFIC PATTERNS

### Grid-Stack Patterns
- File: `app-gridstack.js`
- Agents: `appv2-integration-specialist` → `tickstock-test-specialist`

### Tab Content Migration
- Files: `index.html`, `*.js` (tab-specific)
- Agents: `appv2-integration-specialist` → `redis-integration-specialist` → `integration-testing-specialist`

### Polygon.io Integration
- New file: `market-movers.js` (or similar)
- Agents: `appv2-integration-specialist` → `integration-testing-specialist` → `tickstock-test-specialist`

## INVOCATION EXAMPLES

### Example 1: Extending Grid Configuration (TASK-001)
```
1. Task: "Modify app-gridstack.js for 2x4 layout"
2. Launch: architecture-validation-specialist
   - "Review my approach for extending grid to 6 containers"
3. Launch: appv2-integration-specialist
   - "Implement 2x4 grid configuration in app-gridstack.js"
4. Launch: tickstock-test-specialist
   - "Create tests for grid configuration and layout"
```

### Example 2: Migrating Watchlist (TASK-004)
```
1. Task: "Move Watchlist from tab to grid container"
2. Launch: architecture-validation-specialist
   - "Validate approach for migrating watchlist to grid"
3. Launch: appv2-integration-specialist + redis-integration-specialist
   - "Migrate watchlist preserving WebSocket connections"
4. Launch: integration-testing-specialist
   - "Test watchlist real-time updates in new container"
5. Launch: tickstock-test-specialist
   - "Comprehensive watchlist migration tests"
```

### Example 3: Market Movers Widget (TASK-008)
```
1. Task: "Implement Market Movers with Polygon API"
2. Launch: architecture-validation-specialist
   - "Review Market Movers widget architecture"
3. Launch: appv2-integration-specialist
   - "Create Market Movers widget with Polygon.io API"
4. Launch: integration-testing-specialist
   - "Test Polygon API integration and error handling"
5. Launch: tickstock-test-specialist
   - "Full widget test suite including API mocking"
```

## REMEMBER
- **NEVER** skip architecture-validation-specialist at the start
- **NEVER** skip tickstock-test-specialist at the end
- **ALWAYS** use multiple agents in parallel when appropriate
- **ALWAYS** document changes with documentation-sync-specialist