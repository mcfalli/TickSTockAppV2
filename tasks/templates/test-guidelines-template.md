# Sprint Test Guidelines Template

## Test Location For This Sprint
`tests\<functional_area>\sprint_<number>\` - Sprint tests organized by functional area

### Determine Your Functional Area
Choose the appropriate functional area for your Sprint work:

- **`tests\event_processing\`** - Event processing, detection, and event models
- **`tests\data_processing\`** - Data channels, providers, and data type handling
- **`tests\websocket_communication\`** - WebSocket publishers, clients, and protocols
- **`tests\market_data\`** - Market data services, aggregation, and analytics
- **`tests\infrastructure\`** - Database, caching, and external API integration
- **`tests\user_management\`** - Authentication, preferences, and sessions
- **`tests\system_integration\`** - End-to-end, performance, and regression tests

### Sprint Folder Structure
Create your Sprint subfolder within the functional area:
```
tests/
└── <functional_area>/
    ├── sprint_<number>/          # Your Sprint tests go here
    │   ├── test_<component>_refactor.py
    │   ├── test_<feature>_integration.py
    │   └── test_<feature>_preservation.py
    ├── <component_group>/        # Related component tests
    └── <other_sprint_folders>/   # Other Sprint work in same area
```

**Example for Sprint 107 (Event Processing):**
```
tests/event_processing/sprint_107/
├── test_event_processor_refactor.py
├── test_multi_source_integration.py
└── test_existing_functionality_preservation.py
```

### Required Test Files
Create the following test files for comprehensive coverage:

#### 1. Unit/Refactor Tests
**File**: `test_<main_component>_refactor.py`
- Test individual component functionality
- Test new methods and interfaces
- Test component initialization
- Test error handling and edge cases
- **Example**: `test_event_processor_refactor.py`

#### 2. Integration Tests  
**File**: `test_<feature_name>_integration.py`
- Test end-to-end feature functionality
- Test component interactions
- Test data flow through multiple components
- Test external system integrations
- **Example**: `test_multi_source_integration.py`

#### 3. Regression/Preservation Tests
**File**: `test_<feature_name>_preservation.py` 
- Test backward compatibility
- Test existing functionality is unchanged  
- Test existing interfaces are preserved
- Test performance has not regressed
- **Example**: `test_existing_functionality_preservation.py`

#### 4. Performance Tests (if applicable)
**File**: `test_<component>_performance.py`
- Test processing speed benchmarks
- Test memory usage patterns
- Test scalability characteristics
- Test load handling capabilities

### Test Coverage Requirements
- **Unit Tests**: 30+ test methods covering all new components
- **Integration Tests**: 15+ test methods covering end-to-end workflows  
- **Regression Tests**: 20+ test methods verifying backward compatibility
- **Performance Tests**: 5+ test methods validating performance characteristics

### Test Naming Conventions
- **Classes**: `Test<ComponentName><TestType>`
  - Example: `TestEventProcessorRefactor`, `TestMultiSourceIntegration`
- **Methods**: `test_<specific_functionality>`
  - Example: `test_handle_multi_source_data_with_tick_data`
- **Fixtures**: `<component_type>_<data_type>` or `mock_<component>`
  - Example: `sample_tick_data`, `mock_event_manager`

### Test Organization Within Files
```python
class Test<ComponentName><TestType>:
    """Test suite for <component> <test type>"""
    
    @pytest.fixture
    def setup_fixture(self):
        """Setup test fixtures"""
        pass
    
    def test_basic_functionality(self):
        """Test basic component functionality"""
        pass
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        pass
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        pass
    
    def test_performance_characteristics(self):
        """Test performance requirements"""
        pass
```

### Test Execution Commands
```bash
# Run all Sprint tests (replace <functional_area> and <sprint_number>)
pytest tests/<functional_area>/sprint_<sprint_number>/ -v

# Examples:
pytest tests/event_processing/sprint_107/ -v        # Sprint 107 event processing
pytest tests/data_processing/sprint_105/ -v         # Sprint 105 data processing

# Run specific test types within Sprint
pytest tests/<functional_area>/sprint_<number>/test_*_refactor.py     # Unit/refactor tests
pytest tests/<functional_area>/sprint_<number>/test_*_integration.py  # Integration tests  
pytest tests/<functional_area>/sprint_<number>/test_*_preservation.py # Regression tests

# Run all tests in functional area (includes all Sprints and components)
pytest tests/<functional_area>/ -v

# Examples:
pytest tests/event_processing/ -v                   # All event processing tests
pytest tests/data_processing/ -v                    # All data processing tests

# Run specific test file
pytest tests/<functional_area>/sprint_<number>/test_<component>_<type>.py -v
```

### Documentation Requirements
- Each test class must have comprehensive docstring
- Complex test methods must include inline comments
- Test fixtures must be documented with purpose and usage
- Performance tests must document expected benchmarks