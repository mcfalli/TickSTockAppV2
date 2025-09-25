# Sprint Task Introduction Template

**Use this template when creating task-introduction.md for new Sprints**

---

**Important**: This will be provided over prompt as link used to instruct actions for the current sprint/PRD.  

# Sprint Introduction and PRD Overview
This document serves as your entry point to understand the defined work, objectives, and deliverables for this iteration.

# Sprint PRD Number
[SPRINT_NUMBER]

## Introduction
Please see the following markdown documents to fully understand the goals of this Sprint/PRD.  
The focus for this sprint is [SPRINT_NUMBER], see Primary References below.  
We just finalized related sprints [PREVIOUS_SPRINTS] the reference information below.

## Primary References
tasks\active\[SPRINT_NUMBER]-prd-[SPRINT_NAME].md
tasks\active\[SPRINT_NUMBER]-tasks-[SPRINT_NAME].md

## Supporting Design Documents, Sprint Summaries, Documentation References
docs\project_structure.md (overall codebase organization)
tasks\active\Design (design documents)
tasks\active\Summaries (sprint summary documents)

## Test Location For This Sprint
tests\[FUNCTIONAL_AREA]\sprint_[SPRINT_NUMBER]\ - Sprint [SPRINT_NUMBER] [BRIEF_DESCRIPTION] tests

### 📂 **Functional Area Selection**
Choose the appropriate functional area for your Sprint:

| **Functional Area** | **Use For** | **Examples** |
|-------------------|-------------|-------------|
| `event_processing/` | Event processing, detection, event models | EventProcessor, detectors, event creation |
| `data_processing/` | Data channels, providers, data types | Channels, routers, OHLCV/FMV data |
| `websocket_communication/` | WebSocket publishers, clients, protocols | WebSocket publisher, real-time communication |
| `market_data/` | Market data services, aggregation, analytics | MarketDataService, analytics, aggregation |
| `infrastructure/` | Database, caching, external APIs | Database integration, Redis, Polygon API |
| `user_management/` | Authentication, preferences, sessions | User auth, preferences, session management |
| `system_integration/` | End-to-end, performance, regression | System-wide tests, performance benchmarks |

**For this Sprint:** `tests\[FUNCTIONAL_AREA]\sprint_[SPRINT_NUMBER]\`

### 📋 **Required Test Coverage**
Create comprehensive test suites with the following structure:

#### **Test File Requirements**
1. **Unit/Refactor Tests**: `test_<component>_refactor.py`
   - Test individual component functionality
   - Test new methods and interfaces  
   - Test initialization and configuration
   - **Target**: 30+ test methods

2. **Integration Tests**: `test_<feature>_integration.py`
   - Test end-to-end feature workflows
   - Test component interactions
   - Test external system integrations
   - **Target**: 15+ test methods

3. **Regression Tests**: `test_<feature>_preservation.py`
   - Test backward compatibility preservation
   - Test existing functionality unchanged
   - Test performance has not regressed
   - **Target**: 20+ test methods

4. **Performance Tests**: `test_<component>_performance.py` (if applicable)
   - Test processing speed requirements
   - Test memory usage patterns
   - Test scalability characteristics
   - **Target**: 5+ test methods

#### 🎯 **Test Quality Standards**
- **Coverage**: Comprehensive coverage of new functionality
- **Compatibility**: Verify all existing functionality preserved
- **Performance**: Validate performance meets existing benchmarks
- **Error Handling**: Test error scenarios and edge cases
- **Documentation**: All test classes and complex methods documented

#### ⚡ **Quick Test Commands**
```bash
# Run all Sprint tests
pytest tests/[FUNCTIONAL_AREA]/sprint_[SPRINT_NUMBER]/ -v

# Run by test type within Sprint
pytest tests/[FUNCTIONAL_AREA]/sprint_[SPRINT_NUMBER]/test_*_refactor.py     # Unit tests
pytest tests/[FUNCTIONAL_AREA]/sprint_[SPRINT_NUMBER]/test_*_integration.py  # Integration tests
pytest tests/[FUNCTIONAL_AREA]/sprint_[SPRINT_NUMBER]/test_*_preservation.py # Regression tests

# Run all tests in functional area (all Sprints + components)
pytest tests/[FUNCTIONAL_AREA]/ -v                  # All [FUNCTIONAL_AREA] tests
```

## Technical Debt Backlog
tasks\active\Support\technical-debt-backlog.md

## Architectural Decisions
tasks\active\Support\architectural_decisions.md

## Related Past Sprints 
### Related Sprint PRDs Completed
[LIST_PREVIOUS_PRD_FILES]

### Related Sprint PRD Tasks Completed
[LIST_PREVIOUS_TASK_FILES]

## Related Future Sprints 
### Related Future Sprint PRDs
[LIST_FUTURE_PRD_FILES]

### Related Future Sprint PRD Tasks
[LIST_FUTURE_TASK_FILES]

# When wrapping up the sprint
Create a completion summary in the task\active\ folder.

## 📚 Additional Resources
- **Detailed Testing Patterns**: See `CLAUDE.md` Testing Framework section
- **Template Guidelines**: See `tasks\templates\test-guidelines-template.md`
- **Test Organization**: See `tasks\templates\test-reorganization-guide.md`

---

## 🔧 **Template Usage Instructions:**

### **Replace These Placeholders:**
- `[SPRINT_NUMBER]` - Sprint number (e.g., 108, 109)
- `[SPRINT_NAME]` - Sprint name (e.g., integration-testing, performance-optimization)
- `[FUNCTIONAL_AREA]` - Functional area (e.g., event_processing, data_processing, market_data)
- `[BRIEF_DESCRIPTION]` - Brief description of Sprint focus
- `[PREVIOUS_SPRINTS]` - List of completed related Sprints
- `[LIST_PREVIOUS_PRD_FILES]` - List previous PRD markdown files
- `[LIST_PREVIOUS_TASK_FILES]` - List previous task markdown files
- `[LIST_FUTURE_PRD_FILES]` - List future PRD markdown files
- `[LIST_FUTURE_TASK_FILES]` - List future task markdown files

### **Functional Area Selection Guide:**
- **Event Processing**: EventProcessor changes, detector modifications, event model updates
- **Data Processing**: Channel work, data type handlers, provider changes, routing
- **WebSocket Communication**: WebSocket publisher changes, client modifications, protocol updates
- **Market Data**: MarketDataService changes, analytics, aggregation, market state
- **Infrastructure**: Database changes, caching, external API integration
- **User Management**: Authentication, user preferences, session management
- **System Integration**: End-to-end testing, performance optimization, system-wide changes