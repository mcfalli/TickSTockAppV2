# TickStock Trace System Testing Documentation

## Overview

The TickStock trace testing suite provides comprehensive validation of the real-time event processing pipeline. Developed through Sprints 28-31, the suite ensures system reliability, performance, and observability with 14 specialized tests achieving 93% component coverage.

## ⚠️ CRITICAL: Capturing Trace Data Before Testing

**Before running any trace tests, you MUST first capture trace data from the running application:**

### Step 1: Enable Tracing in Configuration
Ensure your `.env` or configuration has:
```
TRACE_ENABLED=true
TRACE_TICKERS=["NVDA", "TSLA", "AAPL"]  # Add your test tickers
TRACE_LEVEL=VERBOSE  # or NORMAL/CRITICAL
```

### Step 2: Start the Application
```bash
python app.py
```

### Step 3: Access the Debug Trace Panel
1. Navigate to: **http://localhost:5000/trace/ScoobyDoo123**
2. Login if required (trace panel requires authentication)

### Step 4: Generate Event Data
1. Let the application run until all event grids show events:
   - High/Low events
   - Surge events  
   - Trend events (if functioning)
   - Other event types
2. Monitor the grids on the trace panel to ensure events are being captured

### Step 5: Export Trace Data
1. **IMPORTANT:** Once all grids show events, click the **"EXPORT ALL"** button
2. This will generate trace files in `./logs/trace/` directory
3. Files will be named: `{TICKER}_{TIMESTAMP}_trace.json`
4. The primary test file `trace_all.json` will be created

### Step 6: Verify Export
Check that trace files were created:
```bash
ls -la ./logs/trace/
# Should see files like:
# NVDA_20250807_143022_trace.json
# trace_all.json
```

---

## System Architecture

### Event Flow Pipeline
```
tick_created → tick_received → process_start → universe_check →
detection_start → event_detected → event_queued → events_collected →
event_ready_for_emission → event_emitted
```

### Key Metrics
- **Raw Efficiency**: 100% (67 detected → 67 emitted)
- **Adjusted Efficiency**: 124.1% (accounting for pre-user events)
- **System Throughput**: 8,681 traces/second
- **Trace Overhead**: 0.127ms per call
- **Component Coverage**: 93% (Grade A)

## Test Categories

### Validation Tests (Critical)

#### Format Validator
- **Purpose**: Ensure trace files meet JSON schema requirements
- **Checks**: Structure validation, data type verification, pre-flight deployment readiness
- **Key Features**: 
  - Detects truncated files
  - Validates timestamp ordering
  - Checks for string/integer type consistency
  - Pre-flight deployment checklist

#### Flow Validation
- **Purpose**: Verify event pipeline integrity
- **Analysis**:
  - Stage-to-stage transition efficiency
  - Event ID tracking through pipeline
  - User connection timing impact
  - Bottleneck identification
- **Metrics**: Raw vs adjusted efficiency calculations

### Coverage & Quality Tests

#### Coverage Analysis
- **Current Score**: 93% (13/14 components traced)
- **Missing**: DataProvider (using SyntheticDataGenerator instead)
- **Grades**: A (90%+), B (80-89%), C (70-79%), D (60-69%), F (<60%)
- **Identifies**: Missing critical traces, incomplete components

#### Statistical Analysis
- **Techniques**:
  - Z-score anomaly detection (|z| > 3)
  - Pattern recognition (3-gram sequences)
  - Trend analysis with linear regression
  - Throughput pattern detection
- **Findings**: 4 slow operations, high timing variability

### Performance Tests

#### Emission Timing
- **Metrics**:
  - 78 emission cycles detected
  - Average cycle duration: 3.5ms
  - Perfect consistency: 67 events per cycle
  - No orphaned events

#### System Health
- **Tests**:
  - Unit tests: Event normalization, deduplication, thread safety
  - Integration tests: End-to-end flow, multi-ticker isolation
  - Performance tests: Overhead, throughput, memory usage
- **Results**: 100% pass rate, excellent health

### Event-Specific Tests

#### HighLow Analysis
- **Detected**: 10 highs, 17 lows
- **Issues**: 13 rapid-fire detections (<1s gap)
- **Missing**: Session-specific detection
- **Recommendations**: Implement throttling, add session awareness

#### Surge Analysis
- **Performance**: 40 surges detected successfully
- **Efficiency**: 0 cooldown blocks, 0 buffer overflows
- **Status**: Optimally configured, well-calibrated thresholds

#### Trend Analysis
- **Status**: Not functioning (0 trends detected)
- **Issue**: TrendDetector only initializing, not detecting
- **Priority**: High - core functionality missing

## Test Infrastructure

### Directory Structure
```
/tests/
├── test_trace_*.py              # 14 individual test scripts
├── test_trace_orchestrator.py   # Runs all tests in sequence
├── test_trace_run_all_tests.py  # Framework validation
├── trace_component_definitions.py # Centralized component definitions
├── util_trace_dump_utility.py   # Trace data analysis tool
├── test_utilities.py            # Shared test utilities
└── trace_analyzer_base.py       # Base analysis classes
```

### Centralized Definitions
`trace_component_definitions.py` maintains:
- Component requirements (critical/expected actions)
- Expected trace flow stages
- Event type definitions
- User connection actions

## Key Findings

### Performance Insights
1. **WorkerPool Operations**: ~511ms batch processing (slow but acceptable)
2. **First Event Latency**: 6-8 seconds for initial events
3. **Event Loss**: 13 events before user connection (expected behavior)
4. **Memory Efficiency**: 363.5KB for 1000 traces

### System Strengths
- Perfect event delivery after user connection
- Excellent surge detection with no false positives
- Minimal trace overhead (<0.2ms)
- Robust error handling and recovery

### Areas for Improvement
1. **Trend Detection**: Not functioning (bug to fix)
2. **Session Events**: Add session-specific high/low detection
3. **Event Throttling**: Implement for rapid-fire detections
4. **User Disconnection**: Missing trace in WebSocketManager

## Running Tests

### Prerequisites
⚠️ **You must have captured trace data first!** See "CRITICAL: Capturing Trace Data Before Testing" section above.

### Individual Test Execution
```bash
# Run specific test
python tests/test_trace_[name].py trace_all.json

# With custom path
python tests/test_trace_[name].py trace_all.json /custom/path/

# With ticker filter (where supported)
python tests/test_trace_[name].py trace_all.json ./logs/trace/ NVDA
```

### Orchestrated Analysis
```bash
# Full analysis with HTML report
python tests/test_trace_orchestrator.py trace_all.json

# Specific modules only
python tests/test_trace_orchestrator.py trace_all.json --modules flow coverage surge
```

### Visualization
The HTML visualization provides:
- Event flow pipeline charts
- Component performance metrics
- Efficiency comparisons by event type
- Interactive Chart.js visualizations

## Best Practices

### Pre-Deployment Validation
1. Capture fresh trace data via debug panel
2. Run format validator for pre-flight checks
3. Verify coverage is above 90%
4. Check adjusted efficiency > 95%
5. Review orchestrator summary for issues

### Continuous Monitoring
1. Capture trace data daily/weekly via debug panel
2. Run orchestrator on captured data
3. Monitor for new anomaly patterns
4. Track efficiency trends
5. Review HTML reports for visual insights

### Issue Resolution Priority
1. **Critical**: Fix trend detection
2. **High**: Optimize WorkerPool performance
3. **Medium**: Implement event throttling
4. **Low**: Add session-specific detection

## Troubleshooting

### Common Issues

#### No Trace Data Available
- **Symptom**: Tests fail with "file not found" errors
- **Fix**: Ensure you've run the debug panel and clicked "EXPORT ALL" after events appear

#### Unicode Encoding Errors (Windows)
- **Symptom**: UnicodeEncodeError with checkmark characters
- **Fix**: Replace Unicode characters with ASCII equivalents

#### Missing Module Errors
- **Symptom**: ModuleNotFoundError
- **Fix**: Remove unused imports or install required packages

#### Blank Visualizations
- **Symptom**: HTML report shows no data
- **Fix**: Ensure trace file contains expected event_detected/event_emitted actions

### Debug Commands
```bash
# Dump trace structure
python tests/util_trace_dump_utility.py trace_all.json

# Check specific component
python tests/util_trace_dump_utility.py trace_all.json --component TrendDetector

# Export component-action mapping
python tests/util_trace_dump_utility.py trace_all.json --export
```

### Trace Panel Troubleshooting
If the trace panel (`/trace/ScoobyDoo123`) isn't working:
1. Verify `TRACE_ENABLED=true` in configuration
2. Check that user is logged in (authentication required)
3. Ensure tickers are specified in `TRACE_TICKERS`
4. Verify trace level is set (`TRACE_LEVEL=VERBOSE` for maximum detail)
5. Check browser console for JavaScript errors
6. Verify WebSocket connection is established

## Complete Testing Workflow

### Full Test Cycle
1. **Configure**: Set `TRACE_ENABLED=true` and specify tickers
2. **Start**: Launch application with `python app.py`
3. **Access**: Navigate to `http://localhost:5000/trace/ScoobyDoo123`
4. **Monitor**: Wait for all event grids to populate with data
5. **Export**: Click "EXPORT ALL" button to capture trace data
6. **Verify**: Check `./logs/trace/` for generated JSON files
7. **Test**: Run individual tests or orchestrator
8. **Analyze**: Review HTML report and console output
9. **Iterate**: Fix issues and repeat as needed

## Conclusion

The Sprint 31 trace testing suite provides comprehensive validation of TickStock's event processing pipeline. With 93% coverage and 100% event delivery efficiency, the system demonstrates excellent reliability. The standardized test framework enables continuous quality monitoring and rapid issue identification, ensuring production readiness and maintainability.

**Remember**: Always capture fresh trace data through the debug panel before running tests to ensure you're testing the current system behavior!