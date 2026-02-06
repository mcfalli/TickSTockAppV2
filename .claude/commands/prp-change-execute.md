# Execute CHANGE PRP

## PRP File: $ARGUMENTS

## Mission: Safe Modification Without Breaking Changes

CHANGE PRPs enable safe code modifications through:

- **Current Implementation Understanding**: Know what exists before changing it
- **Dependency Awareness**: Understand what depends on the code being modified
- **Impact Mitigation**: Anticipate and prevent breakage
- **Regression Prevention**: Ensure existing functionality preserved
- **Progressive Validation**: 5-level gates catch regressions early
- Read docs/PRPs/README.md to understand PRP concepts

**Your Goal**: Transform the PRP into working changes that pass all validation gates WITHOUT breaking existing functionality.

## Execution Process

1. **Load PRP**
   - Read the specified CHANGE PRP file completely
   - Absorb current implementation analysis, dependency maps, impact assessment
   - Review BEFORE/AFTER code examples thoroughly
   - Trust the PRP's analysis - it's designed to prevent breaking changes
   - If needed do additional verification of current implementation

2. **ULTRATHINK & Plan**
   - Create comprehensive modification plan following the PRP's change tasks
   - **CRITICAL**: Review "PRESERVE" notes in each task - what must NOT change
   - Break down into clear todos using TodoWrite tool
   - Use subagents for parallel work when beneficial (always create prp-inspired prompts)
   - Follow BEFORE/AFTER patterns from PRP exactly
   - Verify understanding of current implementation before modifying
   - Never guess - always verify current code matches PRP's analysis

3. **Pre-Modification Baseline**
   - **MANDATORY**: Document current state BEFORE making changes
   - Run all tests and verify they pass: `python run_tests.py`
   - **Capture performance metrics** (if performance-related change):
     ```bash
     # Database query timing
     psql -U app_readwrite -d tickstock -c "\timing on" -c "SELECT ..."
     # Record: Current query time = XXms

     # API endpoint timing
     curl -w "@curl-timing.txt" http://localhost:5000/api/endpoint
     # Record: Current response time = XXms

     # Redis operation timing
     redis-cli --latency-history
     # Record: Current latency = XXms average
     ```
   - Take screenshots/output samples of current behavior if user-facing
   - Create git branch: `git checkout -b change/{feature-name}`

4. **Execute Modification**
   - Follow the PRP's Change Tasks sequence precisely
   - For each task:
     - Read CURRENT implementation first
     - Verify it matches PRP's "CURRENT" description
     - Make changes following "CHANGE" instructions
     - Respect "PRESERVE" constraints (don't modify these parts)
     - Check "GOTCHA" warnings (edge cases to avoid)
   - Use BEFORE/AFTER code patterns from PRP
   - Update affected tests alongside code changes
   - Apply naming conventions from CLAUDE.md

5. **Progressive Validation (5 Levels for Changes)**

   **Execute the level validation system from the PRP:**
   - **Level 1**: Run syntax & style validation (ruff)
   - **Level 2**: Execute unit test validation (pytest unit tests)
   - **Level 3**: Run integration testing (python run_tests.py)
   - **Level 4**: Execute TickStock-specific validation (architecture, performance)
   - **Level 5**: **REGRESSION TESTING** (verify old functionality still works)

   **Each level must pass before proceeding to the next.**

   **Level 5 is CRITICAL for changes** - ensures no breaking changes introduced.

6. **Regression Verification (MANDATORY for Changes)**
   - **Test unchanged functionality**: Verify features NOT modified still work
   - **Test dependent features**: Verify components that depend on modified code still work
   - **Test edge cases**: Verify edge cases handled correctly (not broken by change)
   - **Performance comparison**: Compare before/after metrics (no degradation)
   - **Backward compatibility**: Verify old API contracts still work (if applicable)

7. **Completion Verification**
   - Work through the Final Validation Checklist in the PRP
   - Verify all Success Criteria from "What Changes" section are met
   - Verify all "PRESERVE" constraints were respected
   - Confirm all Anti-Patterns were avoided
   - Verify no breaking changes introduced (or migration path provided if intentional)
   - Changes are ready and working correctly

**Failure Protocol**:
- When validation fails, use the impact analysis and gotchas from PRP to fix issues
- Re-run validation until passing
- If breakage occurs, check if it was identified in impact analysis (expected vs unexpected)
- Document unexpected breakage in AMENDMENT file

## Post-Execution Documentation

After successful implementation, create sprint documentation:

### 1. Implementation Results (Required)
**File**: `docs/planning/sprints/sprint{N}/{change-name}-RESULTS.md`

**Contents**:
- ✅ Success criteria met (reference PRP "What Changes" section)
- ⏱️ Implementation time (actual vs estimated)
- 🎯 Performance metrics achieved (before vs after comparison)
- ✅ Validation results (all 5 levels including regression testing)
- 📝 Manual testing results
- 🔄 Regression test results (confirm no breaking changes)
- 📊 Before/After metrics comparison
- 🔗 Related commits/PRs

### 2. Lessons Learned (If Applicable)
**File**: `docs/planning/sprints/sprint{N}/{change-name}-AMENDMENT.md`

**Create if**:
- PRP had gaps in current implementation analysis
- Unexpected dependencies discovered during modification
- Required debugging iterations beyond initial implementation
- Unforeseen breakage occurred (document cause and fix)
- Impact analysis missed something important

**Contents**:
- What was missing from PRP (current implementation gaps)
- Unexpected dependencies found during implementation
- How many debugging iterations required
- Breakage that occurred and how it was fixed
- Correct modification patterns discovered
- Recommendations for PRP change template improvements

### 3. Migration Guide (If Breaking Changes)
**File**: `docs/planning/sprints/sprint{N}/{change-name}-MIGRATION.md`

**Create if**:
- Change introduced breaking changes
- Deprecated old API/function
- Changed database schema
- Modified Redis message format
- Updated WebSocket event structure

**Contents**:
- What changed and why
- Who is affected (developers, frontend, TickStockPL, etc.)
- Migration steps (with code examples)
- Timeline (deprecation → removal schedule)
- Backward compatibility period (if any)

### 4. Update Sprint Tracking
- Update sprint README or tracking document
- Mark change as complete
- Link to PRP and results documents
- Note any deferred work for backlog
- Document any breaking changes and migration timeline

## Change-Specific Execution Checklist

During execution, continuously verify:

- [ ] I am reading CURRENT implementation before modifying
- [ ] I am following BEFORE → AFTER patterns from PRP
- [ ] I am respecting PRESERVE constraints in each task
- [ ] I am updating affected tests alongside code changes
- [ ] I am running validation after each significant modification
- [ ] I am checking for unintended side effects
- [ ] I am documenting any unexpected breakage
- [ ] I am comparing performance metrics before/after
- [ ] I am testing regression scenarios (old functionality)
- [ ] I am verifying backward compatibility (if required)

## Regression Testing Requirements (Level 5)

**CRITICAL for all changes** - ensure existing functionality preserved:

```bash
# 1. Run full integration test suite (must all pass)
python run_tests.py

# 2. Test specific regression scenarios from PRP
python tests/integration/test_{feature}_regression.py -v

# 3. Manual regression verification
# - Test features that depend on modified code
# - Test edge cases that might be affected
# - Verify error handling still works correctly

# 4. Performance comparison (if applicable)
# Compare before/after metrics:
# - Database query times (EXPLAIN ANALYZE)
# - Redis operation latency
# - WebSocket delivery times
# - API response times

# 5. Backward compatibility verification (if applicable)
# Test old API contracts:
curl -X GET http://localhost:5000/api/old_endpoint
# Expected: Still works (or graceful deprecation warning)

# Test new functionality:
curl -X GET http://localhost:5000/api/new_endpoint
# Expected: New behavior works correctly
```

## Common Change Pitfalls to Avoid

**During Execution:**

- ❌ **Don't modify before understanding current implementation**
  - Always read current code first
  - Verify it matches PRP's analysis
  - If mismatch, update understanding before changing

- ❌ **Don't ignore PRESERVE constraints**
  - Each task lists what must stay the same
  - Changing these will break dependencies
  - Violation leads to cascading failures

- ❌ **Don't skip regression testing**
  - Old functionality must still work
  - Test dependent features
  - Verify edge cases not broken

- ❌ **Don't assume "nobody uses this"**
  - PRP lists all dependencies for a reason
  - Unexpected callers exist
  - Breaking them causes production issues

- ❌ **Don't change tests to make them pass**
  - If test fails, either:
    - Fix implementation (test is correct, code is wrong)
    - OR update test (behavior intentionally changed, documented in PRP)
  - Never hide failing tests by deleting or commenting them out

**Success Indicators:**

✅ All 5 validation levels pass (including regression testing)
✅ Current behavior preserved (where intended)
✅ New behavior working correctly
✅ Performance not degraded (metrics comparison)
✅ No unexpected breakage (all breakage anticipated in PRP)
✅ Tests updated and passing (old + new)
✅ Backward compatibility maintained (or migration guide provided)
