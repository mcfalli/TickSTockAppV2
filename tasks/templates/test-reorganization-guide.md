# Test Directory Reorganization Guide

## 🎯 **New Test Organization by Functional Area**

### **Why This Change?**
- **Easy Navigation**: Find all tests for a specific feature in one place
- **Sprint Traceability**: Clearly see which Sprint created which tests
- **Component Grouping**: Related functionality tests grouped together
- **Scalability**: Structure scales well as the project grows

### **New Directory Structure**

```
tests/
├── event_processing/           # Event Processing & Detection
│   ├── sprint_107/            # Sprint 107: Event Processing Refactor
│   │   ├── test_event_processor_refactor.py
│   │   ├── test_multi_source_integration.py
│   │   └── test_existing_functionality_preservation.py
│   ├── detectors/             # Event detector component tests
│   │   ├── test_highlow_detector.py
│   │   ├── test_trend_detector.py
│   │   └── test_surge_detector.py
│   └── events/                # Event model tests
│       ├── test_base_events.py
│       └── test_event_creation.py
│
├── data_processing/            # Data Processing & Channels
│   ├── sprint_105/            # Sprint 105: Core Channel Infrastructure
│   │   ├── test_base_channel.py
│   │   ├── test_channel_router.py
│   │   └── test_channel_metrics.py
│   ├── sprint_106/            # Sprint 106: Data Type Handlers
│   │   ├── test_data_types.py
│   │   ├── test_tick_channel.py
│   │   └── test_multi_channel_integration.py
│   └── providers/             # Data provider tests
│       ├── test_polygon_provider.py
│       └── test_synthetic_provider.py
│
├── websocket_communication/    # WebSocket & Real-time Communication
├── market_data/               # Market Data Processing
├── infrastructure/            # Infrastructure & External Systems
├── user_management/           # User & Authentication
└── system_integration/        # End-to-End System Tests
```

### **Migration Examples**

#### **Sprint 107 Tests (Event Processing)**
```bash
# OLD Location
tests/pipeline/test_event_processor_refactor.py
tests/pipeline/test_multi_source_integration.py
tests/pipeline/test_existing_functionality_preservation.py

# NEW Location  
tests/event_processing/sprint_107/test_event_processor_refactor.py
tests/event_processing/sprint_107/test_multi_source_integration.py
tests/event_processing/sprint_107/test_existing_functionality_preservation.py
```

#### **Sprint 105 Tests (Data Processing)**
```bash
# OLD Location
tests/pipeline/test_base_channel.py
tests/pipeline/test_channel_router.py
tests/pipeline/test_channel_metrics.py

# NEW Location
tests/data_processing/sprint_105/test_base_channel.py
tests/data_processing/sprint_105/test_channel_router.py
tests/data_processing/sprint_105/test_channel_metrics.py
```

### **Command Examples**

#### **Run All Tests for a Functional Area**
```bash
pytest tests/event_processing/ -v        # All event processing tests
pytest tests/data_processing/ -v         # All data processing tests
pytest tests/websocket_communication/ -v # All WebSocket tests
```

#### **Run Sprint-Specific Tests**
```bash
pytest tests/event_processing/sprint_107/ -v  # Sprint 107 only
pytest tests/data_processing/sprint_105/ -v   # Sprint 105 only
pytest tests/data_processing/sprint_106/ -v   # Sprint 106 only
```

#### **Run Component-Specific Tests**
```bash
pytest tests/event_processing/detectors/ -v  # All detector tests
pytest tests/event_processing/events/ -v     # All event model tests
pytest tests/data_processing/providers/ -v   # All provider tests
```

### **Benefits for Development**

#### **For Developers**
- **Quick Navigation**: "Where are all the event processing tests?" → `tests/event_processing/`
- **Sprint History**: "What did Sprint 105 test?" → `tests/data_processing/sprint_105/`
- **Feature Focus**: "All WebSocket tests" → `tests/websocket_communication/`

#### **For Testing**
- **Functional Testing**: Test entire functional areas independently
- **Sprint Validation**: Validate specific Sprint deliverables
- **Component Testing**: Test related components together

#### **For Maintenance**
- **Clear Ownership**: Each Sprint's tests are clearly identified
- **Easy Updates**: Update all tests for a feature in one location
- **Consistent Structure**: Predictable organization across all features

### **Implementation Steps**

#### **1. Create New Directory Structure**
```bash
mkdir -p tests/event_processing/sprint_107
mkdir -p tests/data_processing/sprint_105
mkdir -p tests/data_processing/sprint_106
# ... other directories as needed
```

#### **2. Move Existing Tests**
```bash
# Move Sprint 107 tests
mv tests/pipeline/test_event_processor_refactor.py tests/event_processing/sprint_107/
mv tests/pipeline/test_multi_source_integration.py tests/event_processing/sprint_107/
mv tests/pipeline/test_existing_functionality_preservation.py tests/event_processing/sprint_107/

# Move Sprint 105 tests
mv tests/pipeline/test_base_channel.py tests/data_processing/sprint_105/
mv tests/pipeline/test_channel_router.py tests/data_processing/sprint_105/

# Move Sprint 106 tests
mv tests/pipeline/test_data_types.py tests/data_processing/sprint_106/
mv tests/pipeline/test_tick_channel.py tests/data_processing/sprint_106/
```

#### **3. Update Test Commands in Documentation**
Update `CLAUDE.md`, task templates, and Sprint instructions to use new structure.

#### **4. Update CI/CD Pipelines** (if applicable)
Update any automated test runners to use new directory structure.

### **Future Sprint Guidelines**

#### **For New Sprints**
1. **Identify Functional Area**: Determine which functional area your Sprint targets
2. **Create Sprint Subfolder**: `tests/<functional_area>/sprint_<number>/`
3. **Follow Naming Convention**: `test_<component>_<type>.py`
4. **Update Documentation**: Update task-introduction.md with specific location

#### **Example for Future Sprint 108**
If Sprint 108 focuses on performance optimization across multiple areas:
```
tests/system_integration/sprint_108/
├── test_performance_benchmarks.py
├── test_end_to_end_performance.py
└── test_system_load_testing.py
```

### **Backward Compatibility**

#### **Legacy Support**
- Keep `tests/pipeline/` for current Sprint work until migration complete
- Gradually migrate existing tests to new structure
- Update documentation to show both old and new paths during transition

#### **Migration Timeline**
- **Phase 1**: Create new structure, copy current tests
- **Phase 2**: Update documentation and templates
- **Phase 3**: Remove old `tests/pipeline/` structure
- **Phase 4**: Full adoption of new functional area structure

This new organization makes it much easier to find, run, and maintain tests while providing clear traceability of Sprint deliverables! 🚀