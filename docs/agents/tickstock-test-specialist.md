# TickStock Test Specialist Agent

**Agent File**: `.claude/agents/tickstock-test-specialist.md`  
**Status**: Active  
**Last Updated**: 2025-08-22

## Overview

The TickStock Test Specialist is an automated testing agent that provides comprehensive test generation and quality assurance for TickStock's real-time financial data processing system.

## Purpose & Impact

**Problem Solved**: Manual test creation bottleneck during sprint development  
**Solution**: Automated, domain-expert test generation following TickStock standards  
**Impact**: Accelerated sprint velocity while maintaining "Quality First" principles

## Key Features

- **Automatic Invocation**: Triggered when creating features, fixing bugs, or modifying core components
- **Functional Organization**: Places tests in correct business domain areas with sprint subfolders
- **Comprehensive Coverage**: Generates 30+ unit, 15+ integration, 20+ regression tests per sprint
- **Performance Focus**: Validates sub-millisecond processing and zero event loss requirements
- **Domain Expertise**: Deep knowledge of Pull Model architecture and event boundaries

## Development Benefits

### Sprint Acceleration
- Parallel test development while you focus on feature implementation
- Consistent adherence to testing standards without manual overhead
- Reduced sprint completion time through automated quality gates

### Quality Assurance
- Enforces TickStock's performance benchmarks (<100ms latency, <1ms detection)
- Validates Pull Model architecture integrity and zero event loss
- Comprehensive error handling and edge case coverage

### Organizational Intelligence
- Smart functional area selection (event_processing, data_processing, etc.)
- Proactive suggestion of new functional areas when needed
- Sprint-specific test organization with proper subfolder structure

## Usage Patterns

### Automatic (Recommended)
Agent is invoked automatically when:
- Creating new features
- Fixing bugs
- Modifying core processing components

### Explicit Invocation
```bash
> Use tickstock-test-specialist to create tests for surge detection
> Have the test specialist analyze failing performance benchmarks
> Ask the testing agent to validate WebSocket publisher changes
```

## Integration Points

- **CLAUDE.md**: Referenced in Testing Framework and Sprint Management sections
- **unit_testing.md**: Follows all standards and organizational requirements
- **Sprint Workflow**: Integrated into development lifecycle for quality gates

## Test Output Structure

```
tests/[functional_area]/sprint_[number]/
├── test_[component]_refactor.py     # 30+ unit tests
├── test_[feature]_integration.py    # 15+ integration tests  
├── test_[feature]_preservation.py   # 20+ regression tests
└── test_[component]_performance.py  # 5+ performance tests
```

## Performance Standards Enforced

- **Detection Speed**: <1ms per event detection
- **End-to-End Latency**: <100ms tick-to-display
- **Memory Management**: Zero leak validation
- **Scalability**: 4,000+ ticker load testing

This agent ensures no feature is complete without comprehensive tests while maintaining TickStock's critical real-time performance requirements.