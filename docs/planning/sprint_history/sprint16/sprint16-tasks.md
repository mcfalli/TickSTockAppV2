## Index.html 
Update index.html as follows
- remove the system health, backtesting, pattern alerts links 
- create 5 additional (6 total) of equal sized grid-stack containers in a 2 per column with 4 rows grid.  Set a default size to fill page as a 2 by 4 grid. 
- Move the tab contents "Watchlist" to a grid-stack container
- Move the tab contents "Market Summary" to a grid-stack container
- Move the tab "Charts" to a grid-stack container 
- Move the tab "Alerts" to a grid-stack container 
- Create a top "Market Movers" item and place in a grid-stack container populated with https://polygon.io/docs/rest/stocks/snapshots/top-market-movers
- The remaining grid-stack containers contain static text "Container 1"
- Remove tab and css that is no longer used as part of these adjustments

# Sprint 16 - Dashboard Grid Modernization Tasks

## Sprint Overview
**Goal**: Transform the tabbed interface into a modern grid-based dashboard layout using the existing grid-stack.js implementation
**Priority**: High
**Estimated Duration**: 1 Sprint (2 weeks)
**Current State**: Grid-stack installed with one container and app-gridstack.js controller

## Prerequisites
- [x] Grid-stack.js already installed and functional
- [x] app-gridstack.js controller in place
- [x] Development branch active
- [ ] Review current app-gridstack.js implementation
- [ ] Backup current index.html and related files

## Task Breakdown

### Phase 1: Grid Configuration (Day 1)
#### TASK-001: Extend Grid Configuration in app-gridstack.js
- **Priority**: Critical
- **Estimate**: 2 hours
- **Description**: Modify app-gridstack.js to support 6 containers in 2x4 layout
- **Technical Details**:
  - Update grid initialization for 2 columns, 4 rows
  - Configure default container sizes
  - Set responsive breakpoints
  - Define container IDs for each widget
- **Acceptance Criteria**:
  - 6 containers configured in app-gridstack.js
  - 2x4 grid layout defined
  - Each container has unique ID

### Phase 2: Layout Restructuring (Days 2-3)
#### TASK-002: Remove Deprecated Navigation Links
- **Priority**: High
- **Estimate**: 1 hour
- **Description**: Remove system health, backtesting, and pattern alerts links from index.html
- **Acceptance Criteria**:
  - Links removed from navigation
  - No broken references in JavaScript
  - Navigation still functional

#### TASK-003: Expand Single Container to Six Containers
- **Priority**: Critical
- **Estimate**: 3 hours
- **Description**: Modify index.html to add 5 more grid-stack containers (6 total)
- **Technical Details**:
  - Use existing container as template
  - Add 5 additional grid-stack-item divs
  - Assign unique IDs to each container
  - Update app-gridstack.js to handle all 6 containers
- **Acceptance Criteria**:
  - 6 containers visible on page
  - Each container properly initialized
  - Grid maintains 2x4 layout
  - All containers interactive (drag/resize)

### Phase 3: Content Migration (Days 4-7)
#### TASK-004: Migrate Watchlist to Grid Container
- **Priority**: Critical
- **Estimate**: 3 hours
- **Description**: Extract Watchlist tab content and integrate into grid-stack container
- **Technical Details**:
  - Preserve existing functionality
  - Update WebSocket connections if needed
  - Maintain real-time updates
- **Acceptance Criteria**:
  - Watchlist fully functional in grid container
  - Real-time updates working
  - No loss of features

#### TASK-005: Migrate Market Summary to Grid Container
- **Priority**: Critical
- **Estimate**: 3 hours
- **Description**: Extract Market Summary tab content and integrate into grid-stack container
- **Technical Details**:
  - Preserve data refresh logic
  - Maintain formatting and styling
  - Update any tab-specific JavaScript
- **Acceptance Criteria**:
  - Market Summary fully functional
  - Data updates working
  - Visual consistency maintained

#### TASK-006: Migrate Charts to Grid Container
- **Priority**: Critical
- **Estimate**: 4 hours
- **Description**: Extract Charts tab content and integrate into grid-stack container
- **Technical Details**:
  - Ensure chart libraries work in new container
  - Handle resize events properly
  - Maintain chart interactivity
- **Acceptance Criteria**:
  - Charts render correctly
  - Resize functionality working
  - All chart features preserved

#### TASK-007: Migrate Alerts to Grid Container
- **Priority**: Critical
- **Estimate**: 3 hours
- **Description**: Extract Alerts tab content and integrate into grid-stack container
- **Technical Details**:
  - Preserve alert notification system
  - Maintain WebSocket connections
  - Update alert display logic
- **Acceptance Criteria**:
  - Alerts display correctly
  - Real-time notifications working
  - Alert management functional

### Phase 4: New Features (Days 8-9)
#### TASK-008: Implement Market Movers Widget
- **Priority**: High
- **Estimate**: 6 hours
- **Description**: Create new Market Movers widget using Polygon.io API
- **Technical Details**:
  - API Endpoint: https://polygon.io/docs/rest/stocks/snapshots/top-market-movers
  - Implement data fetching service
  - Create display component
  - Add auto-refresh capability
- **Acceptance Criteria**:
  - Market movers data displayed
  - Auto-refresh every 60 seconds
  - Error handling for API failures
  - Loading states implemented

#### TASK-009: Add Placeholder Container
- **Priority**: Low
- **Estimate**: 30 minutes
- **Description**: Add static "Container 6" placeholder for future expansion
- **Acceptance Criteria**:
  - Container displays "Container 6" text
  - Styled consistently with other containers
  - Ready for future content

### Phase 5: Cleanup & Optimization (Days 10-11)
#### TASK-010: Remove Obsolete Tab Infrastructure
- **Priority**: Medium
- **Estimate**: 2 hours
- **Description**: Remove all unused tab-related HTML, CSS, and JavaScript
- **Technical Details**:
  - Remove tab navigation HTML
  - Remove tab-specific CSS classes
  - Remove tab switching JavaScript
  - Clean up event listeners
- **Acceptance Criteria**:
  - No dead code remaining
  - No console errors
  - File size reduced

#### TASK-011: CSS Optimization and Cleanup
- **Priority**: Medium
- **Estimate**: 3 hours
- **Description**: Consolidate and optimize CSS for grid layout
- **Technical Details**:
  - Remove unused CSS rules
  - Consolidate grid-specific styles
  - Ensure responsive behavior
  - Add dark mode support if needed
- **Acceptance Criteria**:
  - CSS file size reduced by >20%
  - No style conflicts
  - Consistent theming

### Phase 6: Testing & Documentation (Days 12-14)
#### TASK-012: Cross-Browser Testing
- **Priority**: High
- **Estimate**: 4 hours
- **Description**: Test grid layout across major browsers
- **Test Matrix**:
  - Chrome (latest)
  - Firefox (latest)
  - Safari (latest)
  - Edge (latest)
- **Acceptance Criteria**:
  - Layout works in all browsers
  - No JavaScript errors
  - Performance acceptable

#### TASK-013: Mobile Responsiveness Testing
- **Priority**: High
- **Estimate**: 3 hours
- **Description**: Ensure grid layout works on mobile devices
- **Technical Details**:
  - Test on various screen sizes
  - Implement responsive breakpoints
  - Consider mobile-specific layout
- **Acceptance Criteria**:
  - Usable on mobile devices
  - Containers stack appropriately
  - Touch interactions working

#### TASK-014: Performance Testing
- **Priority**: Medium
- **Estimate**: 2 hours
- **Description**: Validate performance meets requirements
- **Metrics**:
  - Page load time < 3 seconds
  - WebSocket latency < 100ms
  - Smooth drag/resize operations
- **Acceptance Criteria**:
  - Performance metrics met
  - No memory leaks
  - Smooth user experience

#### TASK-015: Update Documentation
- **Priority**: Medium
- **Estimate**: 2 hours
- **Description**: Update user and developer documentation
- **Deliverables**:
  - Update README with new layout info
  - Document grid-stack configuration
  - Add troubleshooting guide
- **Acceptance Criteria**:
  - Documentation complete
  - Screenshots updated
  - Configuration documented

## Risk Mitigation
1. **Grid-Stack Compatibility**: Test early with existing libraries
2. **WebSocket Disruption**: Careful testing of real-time features
3. **Performance Impact**: Monitor bundle size and load times
4. **Browser Support**: Early cross-browser testing

## Definition of Done
- [ ] All tasks completed and tested
- [ ] Code review completed
- [ ] Unit tests written (where applicable)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Performance requirements met
- [ ] Deployed to staging environment
- [ ] Product owner approval received

## Sprint Metrics
- **Total Tasks**: 15
- **Story Points**: ~45
- **Team Capacity**: 2 developers
- **Sprint Duration**: 14 days

## Dependencies
- Polygon.io API access for Market Movers
- grid-stack.js library (already installed)
- app-gridstack.js controller (existing)
- Existing WebSocket infrastructure
- Current authentication/authorization system

## Notes
- Consider implementing user preferences for grid layout saving
- Future enhancement: Allow users to customize grid layout
- Consider adding more widgets in future sprints
- Monitor performance impact of multiple real-time widgets