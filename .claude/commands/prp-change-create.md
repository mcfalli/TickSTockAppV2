# Create CHANGE PRP

## Feature/Change: $ARGUMENTS

## PRP Creation Mission

Create a comprehensive CHANGE PRP that enables **one-pass modification success** through systematic analysis of current implementation, dependency mapping, and impact assessment.

**Critical Understanding**: The executing AI agent only receives:

- Start by reading and understanding the prp concepts docs/PRPs/README.md
- The PRP content you create (including current implementation analysis)
- Its training data knowledge
- Access to codebase files (but needs guidance on which ones to read AND modify)

**Therefore**: Your research on CURRENT implementation and dependency analysis directly determines modification success. Incomplete context = breaking changes.

## Research Process for Changes

> During the research process, create clear tasks and spawn as many agents and subagents as needed using the batch tools. For modifications, understanding the CURRENT implementation is critical - optimize for correctness, not speed.

1. **Current Implementation Analysis (CRITICAL)**
   - Create clear todos and spawn subagents to analyze existing code being modified
   - **FIND ALL CALLERS**: Search for every function/class that calls the code being changed
   - **FIND ALL DEPENDENCIES**: What does the current code depend on (database, Redis, external APIs)
   - **DOCUMENT CURRENT BEHAVIOR**: What does the code do NOW (before changes)
   - **IDENTIFY GOTCHAS**: Edge cases, workarounds, undocumented behaviors
   - Use batch tools to spawn subagents for thorough current implementation analysis

2. **Dependency Mapping (MANDATORY for Changes)**
   - **Upstream Dependencies**: What calls the code being modified
   - **Downstream Dependencies**: What the code being modified calls
   - **Database Dependencies**: Schema, tables, columns affected
   - **Redis Dependencies**: Channels, message formats affected
   - **WebSocket Dependencies**: Event types, message structures affected
   - **External API Dependencies**: TickStockPL endpoints, contracts affected
   - Use batch tools to spawn subagents to map all dependencies comprehensively
   - **Dependency Analysis Tools:**
     ```bash
     # Find all callers of function/class being modified
     rg "function_name\(" src/ tests/
     rg "ClassName" src/ tests/

     # Find database table dependencies
     rg "table_name" src/

     # Find Redis channel usage
     rg "tickstock:channel:pattern" src/

     # Find WebSocket event usage
     rg "event_name" src/ web/

     # Check for dynamic usage (imports, eval)
     rg "import.*module_name" src/
     rg "getattr.*function_name" src/
     ```

3. **Impact Analysis**
   - **Breakage Points**: What could break as a result of this change
   - **Performance Impact**: Will performance improve, degrade, or stay same
   - **Backward Compatibility**: Are there breaking changes? Migration needed?
   - **Test Impact**: Which tests need updating? New tests needed?
   - Use batch tools to spawn subagents for comprehensive impact analysis

4. **Codebase Pattern Analysis**
   - Search for SIMILAR changes made previously in the codebase
   - Identify refactoring patterns used in similar modifications
   - Note successful modification strategies and failed approaches
   - Use batch tools to find examples of similar successful changes

5. **External Research**
   - Create clear todos and spawn subagents for deep research on modification best practices
   - Library documentation for refactoring patterns (include specific URLs)
   - For critical libraries add .md file to PRPs/ai_docs and reference in PRP
   - Best practices for the type of change (performance, refactoring, enhancement, etc.)
   - Use batch tools to spawn subagents for parallel external research

6. **User Clarification**
   - Ask for clarification on change requirements if needed
   - Confirm breaking changes are acceptable (if any identified)
   - Verify performance degradation thresholds

## PRP Generation Process

### Step 1: Choose Template

Use `docs/PRPs/templates/prp-change.md` as your template structure - it contains all sections for modification PRPs.

### Step 2: Context Completeness Validation

Before writing, apply the **"No Prior Knowledge" test** for changes:
_"If someone knew nothing about this codebase OR the current implementation, would they have everything needed to make this change successfully WITHOUT breaking anything?"_

**Additional validation for changes:**
- Have I documented CURRENT behavior thoroughly?
- Have I identified ALL dependencies (upstream and downstream)?
- Have I analyzed ALL potential breakage points?
- Have I provided BEFORE and AFTER code examples?

### Step 3: Research Integration

Transform your research findings into the template sections:

**Goal Section**: Define CURRENT vs DESIRED behavior, change type, breaking changes status
**Current Implementation Analysis**: Document files to modify with current patterns and gotchas
**Dependency Analysis**: Map upstream/downstream dependencies, database/Redis/WebSocket impacts
**Impact Analysis**: List breakage points, performance impact, backward compatibility
**Context Section**: Populate YAML with current implementation references, BEFORE/AFTER patterns
**Change Tasks**: Create dependency-ordered MODIFY/UPDATE/REFACTOR tasks with PRESERVE notes
**Validation Gates**: Add Level 5 regression testing for changes

### Step 4: Information Density Standards

Ensure every reference is **specific and actionable** with CURRENT STATE documented:

- Current implementation file paths with LINE NUMBERS showing what exists now
- BEFORE and AFTER code examples (not just AFTER)
- All callers identified with specific file:line references
- Dependency analysis complete (not "probably nothing depends on this")
- Impact analysis with specific breakage scenarios (not "should be fine")
- Performance baseline documented (current metrics BEFORE change)

### Step 5: ULTRATHINK Before Writing

After research completion, create comprehensive PRP writing plan using TodoWrite tool:

- Plan how to structure current implementation analysis
- Plan how to document dependencies comprehensively
- Plan how to write BEFORE/AFTER code patterns
- Identify gaps in impact analysis that need more research
- Create systematic approach to documenting regression testing needs

## Output

**Ask user for current sprint number if not clear from context.**

Save as: `docs/planning/sprints/sprint{N}/{change-name}.md`

Where `{N}` is the current sprint number (e.g., sprint44, sprint45).

**Related Documentation Pattern**:
- Main PRP: `docs/planning/sprints/sprint{N}/{change-name}.md`
- Amendment/lessons learned: `docs/planning/sprints/sprint{N}/{change-name}-AMENDMENT.md` (create if PRP gaps found)
- Implementation results: `docs/planning/sprints/sprint{N}/{change-name}-RESULTS.md` (REQUIRED - create post-execution)
- Additional notes: `docs/planning/sprints/sprint{N}/{change-name}-NOTES.md` (optional)
- **Migration guide**: `docs/planning/sprints/sprint{N}/{change-name}-MIGRATION.md` (REQUIRED if breaking changes = Yes)
  - Breaking change criteria:
    - Function signature changes (parameters added/removed/reordered)
    - API endpoint request/response format changes
    - Database schema changes requiring data backfill
    - Redis message format changes affecting subscribers
    - WebSocket event structure changes affecting frontend
    - Configuration variable renames or type changes

## PRP Quality Gates

### Context Completeness Check (Change-Specific)

- [ ] Passes "No Prior Knowledge" test from template
- [ ] Current implementation documented with line numbers
- [ ] ALL callers identified (not just "probably no other callers")
- [ ] Dependency analysis complete (upstream AND downstream)
- [ ] Impact analysis identifies specific breakage scenarios
- [ ] BEFORE and AFTER code examples provided
- [ ] Performance baseline documented (current metrics)
- [ ] Backward compatibility analyzed (breaking changes listed OR confirmed none)

### Template Structure Compliance

- [ ] All required template sections completed
- [ ] Goal section has Current vs Desired behavior, change type, breaking changes status
- [ ] Current Implementation Analysis section complete with file paths and line numbers
- [ ] Dependency Analysis section maps all dependencies
- [ ] Impact Analysis section identifies breakage points and performance impact
- [ ] Change Tasks use MODIFY/UPDATE/REFACTOR verbs with PRESERVE notes
- [ ] Level 5 Regression Testing added to validation

### Information Density Standards (Change-Specific)

- [ ] No assumptions - all dependencies verified
- [ ] Current code patterns documented with examples
- [ ] BEFORE/AFTER comparisons for all modified code
- [ ] Specific line numbers for current implementation
- [ ] All callers found and listed
- [ ] Performance metrics baselined
- [ ] Test update requirements identified

## Success Metrics

**Confidence Score**: Rate 1-10 for one-pass modification success likelihood

**Validation**: The completed PRP should enable an AI agent unfamiliar with the codebase to modify the code successfully WITHOUT breaking anything, using only the PRP content and codebase access.

## Change-Specific Checklist

Before finalizing PRP, verify:

- [ ] I have READ the current implementation code
- [ ] I have SEARCHED for all callers of modified functions/classes
- [ ] I have IDENTIFIED all dependencies (database, Redis, WebSocket, etc.)
- [ ] I have ANALYZED potential breakage points
- [ ] I have DOCUMENTED current behavior in BEFORE examples
- [ ] I have SPECIFIED what must be PRESERVED during changes
- [ ] I have LISTED which tests need updating
- [ ] I have PLANNED regression testing approach
- [ ] I have ASSESSED backward compatibility (breaking changes Y/N)
- [ ] I have BASELINED performance metrics (if performance-related change)
