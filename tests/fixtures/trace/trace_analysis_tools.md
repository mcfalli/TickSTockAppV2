Trace Test Commands Quick Reference
# TickStock Trace Test Commands

## Overview
The trace test suite provides 14 comprehensive tests to validate system performance, event flow integrity, and trace quality. Tests can be run individually or orchestrated together for complete analysis.

## Individual Test Commands


# 1. Format Validator
python tests/test_trace_format_validator.py trace_all.json
# Expected: JSON validation, structure analysis, pre-flight checks

# 2. Flow Validation  
python tests/test_trace_flow_validation.py trace_all.json
# Expected: Flow integrity, event sequences, efficiency metrics

# 3. Coverage Analysis
python tests/test_trace_coverage.py trace_all.json
# Expected: Component coverage percentages, missing traces

# 4. Emission Timing
python tests/test_trace_emission_timing.py trace_all.json
# Expected: Timing analysis, latency statistics

# 5. Emission Gap
python tests/test_trace_emission_gap.py trace_all.json
# Expected: Gap detection, emission delays

# 6. Lost Events
python tests/test_trace_lost_events.py trace_all.json
# Expected: Lost event analysis, drop points

# 7. User Connections
python tests/test_trace_user_connections.py trace_all.json
# Expected: User timing impact, adjusted efficiency

# 8. Statistical Analysis
python tests/test_trace_statistical.py trace_all.json
# Expected: Anomalies, patterns, trends

# 9. HighLow Analysis
python tests/test_trace_highlow_analysis.py trace_all.json
# Expected: High/low patterns, price statistics

# 10. Surge Analysis
python tests/test_trace_surge_analysis.py trace_all.json
# Expected: Surge patterns, cooldown analysis

# 11. Trend Analysis
python tests/test_trace_trend_analysis.py trace_all.json
# Expected: Trend detection, momentum analysis

# 12. Diagnostics
python tests/test_trace_diagnostics.py trace_all.json
# Expected: Comprehensive diagnostics, recommendations

# 13. System Health (needs fix)
python tests/test_trace_system_health.py  # No file argument
# Expected: Unit/integration/performance tests

# 14. Visualization
python tests/test_trace_visualization.py trace_all.json
# Expected: HTML report generation

# BATCH - Just test the jobs basic functionality no real trace value
python tests\test_trace_run_all_tests.py > logs/trace/analysis/test_trace_results.txt 2>&1

# BATCH - full run of 1 through 14 with output 
python tests/test_trace_orchestrator.py trace_all.json




