# Product Requirement Prompt (PRP) Concept

"Over-specifying what to build while under-specifying the context, and how to build it, is why so many AI-driven coding attempts stall at 80%. A Product Requirement Prompt (PRP) fixes that by fusing the disciplined scope of a classic Product Requirements Document (PRD) with the “context-is-king” mindset of modern prompt engineering."

## What is a PRP?

Product Requirement Prompt (PRP)
A PRP is a structured prompt that supplies an AI coding agent with everything it needs to deliver a vertical slice of working software—no more, no less.

### How it differs from a PRD

A traditional PRD clarifies what the product must do and why customers need it, but deliberately avoids how it will be built.

A PRP keeps the goal and justification sections of a PRD yet adds three AI-critical layers:

### Context

- Precise file paths and content, library versions and library context, code snippets examples. LLMs generate higher-quality code when given direct, in-prompt references instead of broad descriptions. Usage of a ai_docs/ directory to pipe in library and other docs.

### Implementation Details and Strategy

- In contrast of a traditional PRD, a PRP explicitly states how the product will be built. This includes the use of API endpoints, test runners, or agent patterns (ReAct, Plan-and-Execute) to use. Usage of typehints, dependencies, architectural patterns and other tools to ensure the code is built correctly.

### Validation Gates

- Deterministic checks such as pytest, ruff, or static type passes “Shift-left” quality controls catch defects early and are cheaper than late re-work.
  Example: Each new funtion should be individaully tested, Validation gate = all tests pass.

### PRP Layer Why It Exists

- The PRP folder is used to prepare and pipe PRPs to the agentic coder.

## Why context is non-negotiable

Large-language-model outputs are bounded by their context window; irrelevant or missing context literally squeezes out useful tokens

The industry mantra “Garbage In → Garbage Out” applies doubly to prompt engineering and especially in agentic engineering: sloppy input yields brittle code

## In short

A PRP is PRD + curated codebase intelligence + agent/runbook—the minimum viable packet an AI needs to plausibly ship production-ready code on the first pass.

The PRP can be small and focusing on a single task or large and covering multiple tasks.
The true power of PRP is in the ability to chain tasks together in a PRP to build, self-validate and ship complex features.

## PRP Organization & Sprint Workflow

### Directory Structure

```
docs/
├── PRPs/
│   ├── templates/          # PRP templates (prp-new.md, prp-change.md, prp-planning.md)
│   ├── ai_docs/           # Supplemental documentation for PRPs
│   └── README.md          # This file (PRP concepts)
│
└── planning/
    └── sprints/
        └── sprint{N}/     # Sprint-specific PRPs and implementation docs
            ├── {feature-name}.md              # Main PRP (created via /prp-new-create)
            ├── {feature-name}-AMENDMENT.md    # Lessons learned (if PRP had gaps)
            ├── {feature-name}-RESULTS.md      # Implementation outcomes (required)
            └── {feature-name}-NOTES.md        # Additional notes (optional)
```

### Workflow

#### NEW Feature Workflow (prp-new)

**1. PRP Creation**
**Command**: `/prp-new-create "{feature-name}"`

- Agent performs deep codebase analysis and external research
- Creates comprehensive PRP with context, patterns, and validation gates
- Saves to: `docs/planning/sprints/sprint{N}/{feature-name}.md`
- Agent asks for sprint number if not clear from context

**Example**: `/prp-new-create "health-check-enhancement"` creates `docs/planning/sprints/sprint44/health-check-enhancement.md`

**2. PRP Execution**
**Command**: `/prp-new-execute "docs/planning/sprints/sprint{N}/{feature-name}.md"`

- Agent loads PRP and creates implementation plan
- Executes code changes following PRP patterns and context
- Runs 4-level validation (syntax, unit tests, integration, project-specific)
- Each validation level must pass before proceeding

**Example**: `/prp-new-execute "docs/planning/sprints/sprint44/health-check-enhancement.md"`

---

#### CODE MODIFICATION Workflow (prp-change)

**1. Change PRP Creation**
**Command**: `/prp-change-create "{change-description}"`

- Agent analyzes CURRENT implementation being modified
- Maps ALL dependencies (upstream callers, downstream dependencies)
- Performs impact analysis (what could break, performance effects)
- Documents BEFORE/AFTER code patterns
- Creates comprehensive PRP with regression testing requirements
- Saves to: `docs/planning/sprints/sprint{N}/{change-name}.md`

**Example**: `/prp-change-create "optimize-database-query-performance"` creates `docs/planning/sprints/sprint45/optimize-database-query-performance.md`

**2. Change PRP Execution**
**Command**: `/prp-change-execute "docs/planning/sprints/sprint{N}/{change-name}.md"`

- Agent creates pre-modification baseline (current metrics, test results)
- Executes modifications following BEFORE → AFTER patterns
- Respects PRESERVE constraints (what must NOT change)
- Updates affected tests alongside code changes
- Runs 5-level validation (adds regression testing as Level 5)
- Verifies no breaking changes introduced

**Example**: `/prp-change-execute "docs/planning/sprints/sprint45/optimize-database-query-performance.md"`

**Key Difference**: Change PRPs include Level 5 regression testing to ensure existing functionality preserved

#### 3. Post-Implementation Documentation

**Required: Implementation Results**
- File: `{feature-name}-RESULTS.md` OR `{change-name}-RESULTS.md`
- Contains: Success criteria verification, performance metrics, validation results, manual testing outcomes
- **For changes**: Include before/after metrics comparison, regression test results

**Conditional: Amendment (if needed)**
- File: `{feature-name}-AMENDMENT.md` OR `{change-name}-AMENDMENT.md`
- Create when: PRP had gaps, debugging iterations required, requirements changed
- Contains: Missing context, debugging iterations, correct patterns, PRP improvements
- **For changes**: Document unexpected dependencies, unforeseen breakage, impact analysis gaps

**Conditional: Migration Guide (for breaking changes)**
- File: `{change-name}-MIGRATION.md`
- Create when: Change introduced breaking changes, deprecated APIs, schema modifications
- Contains: What changed, who is affected, migration steps, timeline, backward compatibility period
- Example: Deprecated function → replacement function migration path

**Optional: Additional Notes**
- File: `{feature-name}-NOTES.md` OR `{change-name}-NOTES.md`
- Contains: Implementation details, edge cases, future considerations

#### 4. Sprint Tracking Update
- Mark feature complete in sprint README
- Link to PRP and results documents
- Note any deferred work for backlog

### Sprint Folder Naming Convention

- **Format**: `sprint{N}` where N is sequential integer
- **Current Sprint**: `sprint44` (Health Check Enhancement)
- **Recent Sprints**:
  - `sprint42` - OHLCV Realignment (architectural cleanup)
  - `sprint43` - Pattern Display Delay Fix (5-8min → 1-2min)
  - `sprint44` - Health Check Enhancement (Redis status + auth)

### PRP Templates

Located in `docs/PRPs/templates/`:

- **prp-new.md** - Standard NEW feature implementation template
- **prp-change.md** - Code MODIFICATION template (enhancements, refactoring, bug fixes)
- **prp-planning.md** - Planning/PRD generation with diagrams

### PRP Support Resources

**Framework Pattern Library** (`docs/PRPs/ai_docs/`):
- **flask_patterns.md** - Flask-specific patterns (application context, blueprints, SocketIO, auth, error handling, database connections)
- **redis_patterns.md** - Redis pub-sub patterns (subscribers, message parsing, WebSocket broadcasting, connection management, channel patterns)
- **subagents.md** - Claude Code subagent documentation and examples

**Decision Support**:
- **DECISION_TREE.md** - Comprehensive guide for when to use PRPs vs traditional workflow (includes ROI calculator, decision table, and scoring matrix)

**Validation Tools**:
- **scripts/prp_validator.py** - Automated PRP validation script (checks completeness, correctness, and quality)

Usage:
```bash
# Validate single PRP
python scripts/prp_validator.py docs/planning/sprints/sprint44/health-check-enhancement.md

# Validate all sprint PRPs
python scripts/prp_validator.py --all-sprints

# Verbose output with suggestions
python scripts/prp_validator.py --all-sprints --verbose
```

### Choosing the Right Template

**Use prp-new.md when:**
- Creating NEW features from scratch
- Adding NEW components (files, classes, services)
- Building NEW integrations (Redis channels, WebSocket events, API endpoints)
- Example: Adding a new health check endpoint (Sprint 44)

**Use prp-change.md when:**
- MODIFYING existing code (enhancements, refactoring, bug fixes)
- CHANGING existing behavior or functionality
- OPTIMIZING performance of existing features
- DEPRECATING old code paths
- Example: Refactoring database query for performance, enhancing error handling, fixing bugs

**Key Differences:**

| Aspect | prp-new.md | prp-change.md |
|--------|-------------|---------------|
| Focus | What to BUILD | What to CHANGE |
| Task Verbs | CREATE, ADD, IMPLEMENT | MODIFY, UPDATE, REFACTOR, ENHANCE |
| Context | Desired codebase tree | Current implementation analysis |
| Critical Section | Implementation patterns | Dependency analysis + impact analysis |
| Validation | 4 levels (syntax, unit, integration, project) | 5 levels (adds regression testing) |
| Risk | Greenfield implementation | Breaking existing functionality |

### Best Practices

**Universal Best Practices (Both Templates)**
1. **One Change Per PRP** - Keep PRPs focused on single, cohesive feature or modification
2. **Deep Context** - Include specific file paths, line numbers, and working examples
3. **Cross-Reference Working Code** - Point to similar features/changes that already work
4. **Validate Incrementally** - Use validation gates to catch issues early
5. **Document Learnings** - Create AMENDMENT files when PRP gaps are found
6. **Update Templates** - Feed learnings back into PRP templates for continuous improvement

**NEW Feature Best Practices (prp-new)**
1. **Research Existing Patterns** - Find similar features in codebase and follow their patterns
2. **Specify Exact File Locations** - Use "Desired Codebase Tree" to show where files should be created
3. **Include Working Examples** - Reference existing code that uses similar patterns
4. **4-Level Validation** - Syntax → Unit → Integration → Project-specific

**CHANGE Best Practices (prp-change)**
1. **Understand Current Implementation FIRST** - Read and document existing code before modifying
2. **Map ALL Dependencies** - Find every caller, every dependency, every integration point
3. **Create Regression Baseline** - Document current behavior in tests BEFORE changing code
4. **Document BEFORE/AFTER** - Show current code and desired code side-by-side
5. **Identify PRESERVE Constraints** - Specify what must NOT change (API contracts, behavior, etc.)
6. **5-Level Validation** - Syntax → Unit → Integration → Project-specific → **Regression Testing**
7. **Measure Performance Impact** - Baseline metrics before change, compare after
8. **Plan for Breakage** - Identify what COULD break and how to mitigate
9. **Provide Migration Path** - If breaking changes required, document migration steps

### Examples

#### Example 1: Sprint 44 Health Check Enhancement (NEW Feature - prp-new)

```
docs/planning/sprints/sprint44/
├── health-check-enhancement.md          # Main PRP (prp-new template)
├── health-check-enhancement-AMENDMENT.md # Lessons learned (Flask context patterns)
└── health-check-enhancement-RESULTS.md   # Implementation outcomes
```

**Template Used**: `prp-new.md` (adding NEW /health endpoint)
**Outcome**: Feature implemented with 3 debugging iterations (Flask context pattern gap)
**Value**: Saved ~60 minutes vs starting from scratch
**Learnings**: Added Flask application context patterns to prp-new template

**Why prp-new**: Adding a NEW health check endpoint (didn't exist before)

---

#### Example 2: Hypothetical Database Query Optimization (CHANGE - prp-change)

```
docs/planning/sprints/sprint45/
├── optimize-pattern-query.md          # Main PRP (prp-change template)
├── optimize-pattern-query-RESULTS.md  # Before/after metrics comparison
└── optimize-pattern-query-NOTES.md    # Performance tuning details
```

**Template Used**: `prp-change.md` (modifying EXISTING query)
**Scenario**: Existing pattern query takes 80ms, target <50ms
**Key Sections**:
- Current Implementation: Shows current SQL query with N+1 problem
- Dependency Analysis: Lists 3 API endpoints and 2 services that call this query
- Impact Analysis: Performance improvement, no breaking changes
- BEFORE/AFTER: Shows current query vs optimized batch query
- Regression Testing: Verify same results returned, just faster

**Why prp-change**: Modifying EXISTING database query (not creating new one)

---

#### Example 3: When to Use Each Template

| Scenario | Template | Reasoning |
|----------|----------|-----------|
| Add new WebSocket event type | prp-new | NEW event type (doesn't exist) |
| Enhance existing error handling | prp-change | MODIFYING existing error handling logic |
| Create new API endpoint | prp-new | NEW endpoint (doesn't exist) |
| Refactor service class for performance | prp-change | MODIFYING existing service class |
| Add new database table | prp-new | NEW table (schema addition) |
| Optimize existing database query | prp-change | MODIFYING existing query |
| Deprecate old function | prp-change | MODIFYING existing code path (deprecation) |
| Build new Redis subscriber | prp-new | NEW subscriber component |
| Fix bug in existing function | prp-change | MODIFYING existing function to fix bug |
| Add new feature flag | prp-new | NEW configuration option |