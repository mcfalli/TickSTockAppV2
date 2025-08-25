# Sync Testing Documentation

**Purpose**: Analyze the current tests/ folder structure and update testing documentation to reflect actual project state

**Usage**: `/sync-testing-docs`

## What This Command Does

1. **Analyzes Current Test Structure**
   - Scans the `tests/` directory for actual organization
   - Identifies test file patterns and naming conventions
   - Discovers test markers and fixtures in use
   - Reviews pytest configuration (pytest.ini)

2. **Updates Documentation Files**
   - `docs/instructions/unit_testing.md` - Core testing standards and setup
   - `.claude/agents/tickstock-test-specialist.md` - Testing agent configuration

3. **Ensures Consistency**
   - Test organization matches documentation
   - Coverage targets are aligned
   - Command examples reflect actual structure
   - Agent knows correct test locations and patterns

## Analysis Process

### Test Structure Analysis
- Directory structure under `tests/`
- Test file naming patterns (test_*.py)
- Test class and function patterns
- Fixture usage and organization

### Configuration Analysis
- pytest.ini settings and markers
- Coverage configuration and targets
- Test command patterns in use
- Dependencies and requirements

### Documentation Synchronization
- Update test organization examples
- Sync coverage targets and standards
- Align test execution commands
- Update agent test location guidance

## Implementation

When executed, this command will:

1. **Scan Tests Directory**
   ```
   tests/
   ├── conftest.py (if exists)
   ├── unit/ (scan for structure)
   ├── integration/ (scan for structure)
   └── fixtures/ (scan for utilities)
   ```

2. **Analyze Pytest Configuration**
   - Check for pytest.ini or pyproject.toml config
   - Identify configured markers
   - Review coverage settings

3. **Update Unit Testing Guide**
   - Sync test structure examples
   - Update command examples to match reality
   - Align coverage targets with actual config
   - Update best practices based on current patterns

4. **Update Testing Agent**
   - Sync test organization guidance
   - Update test location recommendations
   - Align agent behavior with actual structure
   - Update test pattern examples

## Automated Updates

### Test Structure Synchronization
- If tests use different organization than documented, update docs to match
- If new test types are found, add them to documentation
- If markers are used differently, sync the documentation

### Command Synchronization
- Update pytest command examples to match actual usage
- Sync coverage commands with actual configuration
- Update test filtering examples based on actual markers

### Agent Behavior Alignment
- Update agent to recommend correct test locations
- Sync agent test creation patterns with actual structure
- Align agent quality standards with project reality

## Manual Review Prompts

After automated updates, the command will prompt for manual review of:
- Coverage targets (are they realistic for current project?)
- Test organization (does it match development workflow?)
- Quality standards (appropriate for project maturity?)
- Agent guidance (helpful for actual development needs?)

This ensures testing documentation stays current and useful as the project evolves.