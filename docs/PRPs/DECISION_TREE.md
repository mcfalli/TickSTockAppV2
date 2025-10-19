# PRP Decision Tree: When to Use PRPs

> A practical decision guide for determining when Product Requirement Prompts (PRPs) provide value

## Quick Decision

**Ask yourself:** _"Will I touch 3+ files OR modify architecture-sensitive code?"_

- **YES** → Use PRP workflow (high ROI)
- **NO** → Use traditional workflow (PRP overhead not justified)

---

## Detailed Decision Tree

```
START: "I need to..."
│
├─ Is this a NEW feature or MODIFICATION?
│  ├─ NEW → Continue to "NEW Feature Assessment"
│  └─ MODIFICATION → Continue to "CHANGE Assessment"
│
│
├─ NEW FEATURE ASSESSMENT
│  │
│  ├─ How many files will this touch?
│  │  ├─ 1 file → ⚠️ Probably NO PRP (unless...)
│  │  ├─ 2 files → 🤔 Maybe PRP (check complexity)
│  │  └─ 3+ files → ✅ USE PRP (high value)
│  │
│  ├─ Does it involve TickStock architecture?
│  │  ├─ Redis pub-sub → ✅ USE PRP
│  │  ├─ WebSocket integration → ✅ USE PRP
│  │  ├─ Cross-component (AppV2 ↔ PL) → ✅ USE PRP
│  │  ├─ Database schema changes → ✅ USE PRP
│  │  └─ Simple CRUD endpoint → ⚠️ Probably NO PRP
│  │
│  ├─ What's the complexity?
│  │  ├─ >100 lines new code → ✅ USE PRP
│  │  ├─ 50-100 lines → 🤔 Maybe PRP
│  │  └─ <50 lines → ⚠️ Probably NO PRP
│  │
│  ├─ Are there performance requirements?
│  │  ├─ <1ms, <10ms, <50ms, <100ms targets → ✅ USE PRP
│  │  └─ No specific targets → ⚠️ Probably NO PRP
│  │
│  └─ Is this copying an existing feature?
│     ├─ Yes, exact pattern exists → ⚠️ NO PRP (copy pattern)
│     └─ No, novel implementation → ✅ USE PRP
│
│
└─ CHANGE/MODIFICATION ASSESSMENT
   │
   ├─ How many files will change?
   │  ├─ 1 file, <50 lines → ⚠️ NO PRP (simple fix)
   │  ├─ 1 file, >50 lines → 🤔 Maybe PRP
   │  └─ 2+ files → ✅ USE PRP
   │
   ├─ What are you modifying?
   │  ├─ Typo/comment fix → ⚠️ NO PRP
   │  ├─ Simple refactoring (same behavior) → ⚠️ NO PRP
   │  ├─ Performance optimization → ✅ USE PRP
   │  ├─ Bug fix (complex logic) → ✅ USE PRP
   │  ├─ Deprecation/migration → ✅ USE PRP
   │  └─ Enhancing existing feature → 🤔 Check impact
   │
   ├─ How many dependencies?
   │  ├─ No callers, isolated code → ⚠️ NO PRP
   │  ├─ 1-2 callers, clear impact → 🤔 Maybe PRP
   │  └─ 3+ callers, complex dependencies → ✅ USE PRP
   │
   ├─ Is there breaking change risk?
   │  ├─ API contract changes → ✅ USE PRP
   │  ├─ Database schema changes → ✅ USE PRP
   │  ├─ Redis message format changes → ✅ USE PRP
   │  ├─ WebSocket event changes → ✅ USE PRP
   │  └─ Internal logic only → ⚠️ Maybe NO PRP
   │
   └─ Is this urgent?
      ├─ Hotfix, production down → ⚠️ NO PRP (speed critical)
      └─ Normal priority → ✅ USE PRP


LEGEND:
✅ USE PRP - High ROI, worth the investment
🤔 Maybe PRP - Marginal case, use judgment
⚠️ NO PRP - Overhead not justified
```

---

## Decision Table

### Use PRP When (High ROI)

| Scenario | Why PRP is Valuable | Template |
|----------|---------------------|----------|
| **Multi-file feature** (3+ files) | Context completeness prevents missing integration points | `prp-new.md` |
| **Redis pub-sub integration** | Channel patterns, message formats, gotchas documented | `prp-new.md` |
| **WebSocket feature** | SocketIO patterns, room management, broadcast gotchas | `prp-new.md` |
| **Database schema changes** | Migration scripts, dependency analysis, rollback plans | `prp-new.md` or `prp-change.md` |
| **Cross-component integration** (AppV2 ↔ PL) | Component roles, loose coupling enforcement | `prp-new.md` |
| **Performance-critical code** (<1ms, <10ms targets) | Benchmarking, optimization patterns, measurement | `prp-change.md` |
| **Complex refactoring** (3+ files) | Dependency mapping, impact analysis, regression testing | `prp-change.md` |
| **API contract changes** | Breaking change analysis, migration paths, backward compatibility | `prp-change.md` |
| **Deprecation/migration** | Multi-phase rollout, caller updates, removal timeline | `prp-change.md` |
| **Architecture-sensitive** | Role boundaries, consumer/producer enforcement | Either template |

### Skip PRP When (Low ROI)

| Scenario | Why PRP is Overkill | Alternative |
|----------|---------------------|-------------|
| **Typo/comment fixes** | Single-file, trivial change | Direct edit |
| **Simple bug fixes** (<50 lines, 1 file, clear cause) | Debugging effort > PRP creation effort | Direct fix + test |
| **Copying existing pattern** | Working example already exists | Copy and adapt |
| **Configuration changes** (.env, constants) | No code logic changes | Direct edit |
| **Log message updates** | No behavior changes | Direct edit |
| **Simple CRUD endpoint** (exact pattern exists) | Blueprint pattern is well-established | Copy tier_patterns.py pattern |
| **Urgent hotfixes** | Speed critical, no time for PRP | Fix immediately, retrospective PRP optional |
| **Documentation updates** | No code changes | Direct edit |
| **Test additions** (no code changes) | Test patterns are established | Follow existing test structure |

---

## ROI Calculator

### Time Investment

**PRP Creation Time** (varies by complexity):
- Simple feature: 30-60 minutes (research + template filling)
- Medium feature: 1-2 hours (deeper research, multiple patterns)
- Complex feature: 2-4 hours (extensive research, impact analysis)

**PRP Execution Time Saved**:
- Debugging iterations avoided: 30-90 minutes per iteration
- Context switching reduced: 15-30 minutes
- Rework avoided: 1-4 hours (if architecture violation caught early)

**Break-Even Point**: PRP pays for itself if it saves ≥1 debugging iteration

### Historical Data (Sprint 44)

| Metric | Without PRP (Estimated) | With PRP (Actual) | Savings |
|--------|-------------------------|-------------------|---------|
| Research time | 30 min | Included in PRP | - |
| Implementation time | 60 min | 45 min | 15 min |
| Debugging iterations | 5-7 iterations | 3 iterations | 45-60 min |
| **Total Time** | **~2 hours** | **~1.25 hours** | **~45 min** |
| **Success Rate** | 60-70% first attempt | 90% with PRP | +30% |

**Note**: Sprint 44 PRP had gaps (Flask context pattern missing), yet still saved significant time.

---

## Edge Cases & Judgment Calls

### When PRP Might Seem Optional But Is Actually Valuable

**Scenario 1: "It's only 2 files, but..."**
- ✅ USE PRP if: Files are in different layers (API + service + database)
- ✅ USE PRP if: Integration involves Redis, WebSocket, or cross-component
- ⚠️ SKIP if: Two files are tightly coupled (e.g., test + implementation)

**Scenario 2: "It's simple code, but..."**
- ✅ USE PRP if: Performance targets are strict (<10ms)
- ✅ USE PRP if: Touching architecture-sensitive code (pub-sub, Worker boundaries)
- ⚠️ SKIP if: Exact pattern exists and you're just copying

**Scenario 3: "I know the codebase well, but..."**
- ✅ USE PRP if: Feature is for someone else to implement (knowledge transfer)
- ✅ USE PRP if: Complex enough you might forget details in 2 weeks
- ⚠️ SKIP if: You're the only developer and it's a quick fix

**Scenario 4: "It's a bug fix, but..."**
- ✅ USE PRP if: Root cause unclear, requires investigation
- ✅ USE PRP if: Fix involves refactoring multiple files
- ✅ USE PRP if: Bug is in architecture-sensitive code (race conditions, Worker boundaries)
- ⚠️ SKIP if: Bug is obvious typo or off-by-one error

**Scenario 5: "It's urgent, but..."**
- ✅ USE PRP if: Urgency is "this sprint" (time to plan)
- ⚠️ SKIP if: Urgency is "production down" (fix first, retrospective PRP later)

---

## Workflow Selection Guide

### Recommended Workflows by Task Type

```yaml
task_type: NEW_REST_API_ENDPOINT
├─ complexity: SIMPLE (copies tier_patterns.py)
│  └─ workflow: Traditional (copy blueprint pattern)
└─ complexity: COMPLEX (new integration, performance targets)
   └─ workflow: PRP (prp-new.md)

task_type: NEW_REDIS_INTEGRATION
└─ workflow: PRP (prp-new.md) - ALWAYS
   reason: Channel patterns, message formats, Worker boundaries

task_type: NEW_WEBSOCKET_FEATURE
└─ workflow: PRP (prp-new.md) - ALWAYS
   reason: SocketIO gotchas, room management, broadcast patterns

task_type: DATABASE_QUERY_OPTIMIZATION
└─ workflow: PRP (prp-change.md) - RECOMMENDED
   reason: Performance benchmarking, regression testing, EXPLAIN ANALYZE

task_type: REFACTORING
├─ scope: SINGLE_FILE
│  └─ workflow: Traditional (direct refactor + tests)
└─ scope: MULTI_FILE
   └─ workflow: PRP (prp-change.md)

task_type: BUG_FIX
├─ severity: CRITICAL_HOTFIX
│  └─ workflow: Traditional (fix immediately, retrospective PRP optional)
├─ complexity: SIMPLE (<50 lines, 1 file)
│  └─ workflow: Traditional
└─ complexity: COMPLEX (multi-file, unclear root cause)
   └─ workflow: PRP (prp-change.md)

task_type: DEPRECATION
└─ workflow: PRP (prp-change.md) - ALWAYS
   reason: Multi-phase rollout, migration paths, caller updates

task_type: FEATURE_ENHANCEMENT
├─ existing_feature: WELL_DOCUMENTED
│  └─ workflow: Traditional (follow existing pattern)
└─ existing_feature: POORLY_DOCUMENTED
   └─ workflow: PRP (prp-change.md) - document while enhancing
```

---

## Quick Reference Checklist

**Before starting ANY task, ask:**

- [ ] Will I modify 3+ files? → ✅ PRP
- [ ] Does it involve Redis, WebSocket, or database schema? → ✅ PRP
- [ ] Are there strict performance requirements? → ✅ PRP
- [ ] Is there breaking change risk? → ✅ PRP
- [ ] Am I unsure which files to touch? → ✅ PRP
- [ ] Is this a well-established pattern I've done 5+ times? → ⚠️ Maybe skip PRP
- [ ] Is this a typo or <10 line fix? → ⚠️ Skip PRP
- [ ] Is production down and I need to fix NOW? → ⚠️ Skip PRP (but retrospective PRP recommended)

**If 2+ boxes checked:** → **Use PRP workflow**

**If 0-1 boxes checked:** → **Use traditional workflow**

---

## Templates by Task Type

| Task Type | Template | Command |
|-----------|----------|---------|
| NEW feature (greenfield) | `prp-new.md` | `/prp-new-create "feature-name"` |
| MODIFY existing code | `prp-change.md` | `/prp-change-create "change-description"` |
| PLANNING/PRD generation | `prp-planning.md` | Manual (not slash command) |

---

## Anti-Patterns

### ❌ When NOT to Use PRPs

**Analysis Paralysis**
- ❌ Creating PRP for changing a typo
- ❌ Spending 2 hours on PRP for 15-minute fix
- ❌ Using PRP for every single commit

**Over-Engineering**
- ❌ PRP with 50 tasks for 3-file change
- ❌ Documenting every possible edge case
- ❌ Research that exceeds implementation time

**Misapplication**
- ❌ Using `prp-new.md` for modifying existing code (use `prp-change.md`)
- ❌ Using `prp-change.md` for greenfield features (use `prp-new.md`)
- ❌ Skipping PRP for Redis integration (ALWAYS use PRP)

### ✅ When PRPs Shine

**Context Completeness**
- ✅ Multi-component integration (AppV2 ↔ PL)
- ✅ Framework-specific patterns (Flask context, SocketIO, Redis pub-sub)
- ✅ Performance-critical paths (<1ms, <10ms targets)

**Architecture Enforcement**
- ✅ Consumer/Producer role boundaries
- ✅ Read-only database enforcement
- ✅ Worker boundary typed event gotchas

**Knowledge Transfer**
- ✅ Features someone else will implement
- ✅ Documenting tribal knowledge
- ✅ Onboarding new developers

---

## Summary Decision Matrix

| Criteria | Weight | Score Calculation |
|----------|--------|-------------------|
| **Files Modified** | 3x | 1 file = 0, 2 files = 3, 3+ files = 9 |
| **Architecture Sensitivity** | 4x | None = 0, Redis/WebSocket/DB = 12 |
| **Performance Requirements** | 2x | None = 0, Strict targets = 6 |
| **Complexity (LOC)** | 1x | <50 = 0, 50-100 = 1, >100 = 3 |
| **Breaking Changes** | 3x | None = 0, API/schema changes = 9 |
| **Urgency** | -2x | Critical = -6, Normal = 0 |

**Score Interpretation**:
- **≥15 points**: ✅ USE PRP (high ROI)
- **8-14 points**: 🤔 MAYBE PRP (use judgment)
- **<8 points**: ⚠️ SKIP PRP (overhead not justified)

**Example Calculations**:

```
Health Check Enhancement (Sprint 44):
- Files: 2 (app.py + test) = 3
- Architecture: Redis integration = 12
- Performance: <50ms target = 6
- Complexity: ~100 LOC = 3
- Breaking: None = 0
- Urgency: Normal = 0
= 24 points → ✅ USE PRP (correct decision)

Simple Typo Fix:
- Files: 1 = 0
- Architecture: None = 0
- Performance: None = 0
- Complexity: 1 line = 0
- Breaking: None = 0
- Urgency: Normal = 0
= 0 points → ⚠️ SKIP PRP (correct)

Production Hotfix:
- Files: 3 = 9
- Architecture: Redis = 12
- Performance: Critical = 6
- Complexity: 50 lines = 1
- Breaking: None = 0
- Urgency: CRITICAL = -6
= 22 points → 🤔 JUDGMENT CALL
  → Fix immediately, create retrospective PRP for learnings
```

---

## Continuous Improvement

### Retrospective Questions

After completing a task, ask:

**If you used PRP:**
- Did PRP save time vs traditional workflow?
- Were there PRP gaps that caused debugging iterations?
- Did PRP prevent architecture violations?
- Would you use PRP for similar tasks in future?

**If you skipped PRP:**
- How many debugging iterations were required?
- Did you encounter architecture violations?
- Would PRP have saved time in hindsight?
- Should this task type use PRP in future?

### Calibration

Track PRP ROI over time:
- **High ROI tasks**: Always use PRP
- **Medium ROI tasks**: Use judgment based on context
- **Low ROI tasks**: Skip PRP, use traditional workflow

Update this decision tree based on empirical data.

---

## Final Recommendation

**When in doubt, err on the side of creating a PRP.**

Why?
- ✅ Captures knowledge for future reference
- ✅ Prevents architecture violations (expensive to fix)
- ✅ Faster implementation (90% vs 60-70% first-pass success)
- ✅ Self-improving through AMENDMENT feedback loop

The time invested in PRP creation pays dividends through:
- Reduced debugging iterations
- Prevented rework
- Knowledge transfer to team
- Template improvements for future PRPs

**Exception**: Production hotfixes (fix immediately, retrospective PRP optional)
