# Post-Sprint Completion Checklist

## Purpose
This checklist ensures consistent sprint closure, comprehensive documentation, and nothing is left outstanding. Execute these steps at the end of EVERY sprint.

## Sprint Completion Checklist

### 1. Code & Testing Verification
- [ ] Run full integration test suite: `python run_tests.py`
- [ ] Verify all tests pass (2 tests, ~30 seconds)
- [ ] Check for any hardcoded credentials or secrets
- [ ] Ensure no mock/stub endpoints remain in production code
- [ ] Verify performance targets met (<100ms WebSocket, <50ms API)

### 2. Outstanding Work Review
- [ ] Review all TODO comments in code: `rg "TODO|FIXME|HACK" src/`
- [ ] Check for incomplete error handling
- [ ] Verify all promised features are implemented
- [ ] Document any deferred work in BACKLOG.md
- [ ] Answer: **"Is there anything else outstanding?"**

### 3. Documentation Updates
- [ ] Create sprint summary in `/docs/planning/sprints/sprint{N}/SPRINT{N}_COMPLETE.md`
- [ ] Update `/docs/planning/sprints/BACKLOG.md` with:
  - Any deferred items
  - New issues discovered
  - Future enhancements identified
- [ ] Update relevant architecture docs if system design changed
- [ ] Update API documentation if endpoints modified

### 4. CLAUDE.md Updates
- [ ] Update "Current Sprint Context" section
- [ ] Add any new common commands discovered
- [ ] Update "Common Pitfalls & Solutions" if new issues found
- [ ] Update "Current Implementation Status" section
- [ ] Add new agent triggers if patterns identified
- [ ] Update performance metrics with latest measurements

### 5. Sprint Summary Creation
Create summary with these sections:
```markdown
# Sprint {N} Completion Summary

## Objectives Completed
- List all completed objectives

## Key Implementations
- Major features added
- Patterns/indicators implemented
- Performance improvements

## Technical Debt Addressed
- Refactoring completed
- Code quality improvements

## Issues Encountered & Resolutions
- Problems faced and how solved

## Performance Metrics
- Current vs target performance
- Any degradations noted

## Database Changes
- Schema modifications
- New tables/columns
- Migration scripts run

## Outstanding Items
- Deferred to next sprint
- Blocked items
- Items needing further discussion

## Lessons Learned
- What worked well
- What could improve
- Process improvements

## Next Sprint Recommendations
- Priority items
- Technical debt to address
- Suggested focus areas
```

### 6. Git Commit Message Preparation
Prepare the following commit message for the user:
```
Sprint {N} Completion - {Brief Sprint Title}

Completed Features:
- List main features implemented
- Include pattern/indicator additions
- Note performance improvements

Technical Changes:
- Database schema updates
- Configuration changes
- Dependency additions

Bug Fixes:
- List any bugs resolved

Documentation:
- Updated files/sections

Outstanding Items:
- Any deferred work noted in BACKLOG.md
```

### 7. Communication & Handoff
- [ ] Update team on sprint completion
- [ ] Document any configuration changes needed
- [ ] Note any new dependencies added
- [ ] Update deployment instructions if changed

### 8. Metrics Collection
- [ ] Record final test coverage percentage
- [ ] Document lines of code added/removed
- [ ] Note number of bugs fixed
- [ ] Count features implemented

### 9. Environment Cleanup
- [ ] Clean up test data
- [ ] Remove temporary files
- [ ] Clear unnecessary logs
- [ ] Reset development database if needed

### 10. Final Verification Questions
Ask and answer these questions:
1. **"Is there anything else outstanding?"**
2. "Are all acceptance criteria met?"
3. "Would a new developer understand what was done?"
4. "Can the next sprint start cleanly?"
5. "Are there any security concerns?"

## Automation Reminders

### For Claude/AI Assistants
When completing a sprint, ALWAYS:
1. Run through this entire checklist
2. Create the completion summary
3. Update CLAUDE.md
4. Ask "Is there anything else outstanding?" before finalizing
5. Do NOT mark sprint complete until all items checked

### Location References
- Sprint summaries: `/docs/planning/sprints/sprint{N}/`
- Backlog: `/docs/planning/sprints/BACKLOG.md`
- CLAUDE.md: `/CLAUDE.md`
- Test results: `/logs/test-results/`
- Performance metrics: Check integration test output

## Template Usage

Copy this template to each sprint folder as `sprint{N}_checklist.md` and check off items as completed.

---
*This checklist is mandatory for sprint completion. No sprint is considered done until all items are verified.*