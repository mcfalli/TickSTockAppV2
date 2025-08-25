# Sprint Documentation Tasks

*Checklist for documenting sprints to ensure consistent and thorough record-keeping for development teams.*

**Version:** 1.0  
**Date:** 2025-08-21  

## Purpose
Provide a concise documentation checklist to accompany sprint instructions for development teams or AI executing sprints.

## Audience
Development teams or AI systems responsible for executing and documenting sprints.

## Quick Reference
- **Sprint Summary Template**: See `docs/sprints/sprint-108-completion-summary.md`
- **ADR Template**: See existing ADRs in `docs/architecture/architectural_decisions.md`
- **Documentation Index**: `docs/docs-index.md` for all reference materials
- **Goal**: Ensure TickStock's architectural evolution is properly documented for future development teams.

## Pre-Sprint Documentation Tasks
### Review Phase
- Read relevant documentation sections (reference `docs/docs-index.md`).
- Check `docs/architecture/architectural_decisions.md` for relevant Architectural Decision Records (ADRs).
- Identify any technical debt items that impact the current sprint.

### Optional
- Review previous sprint summaries for architectural context.

## During Sprint Documentation Tasks
### As Decisions Are Made
- Document major architectural decisions as draft ADRs.
- Add new technical debt items to the backlog as identified.
- Update design documents if implementation deviates from the original plan.

### As Features Are Built
- Create feature documentation for significant new capabilities.
- Document new integration patterns or approaches.

## Post-Sprint Documentation Tasks
### Required Sprint Completion
- **Create Sprint Summary**: `docs/sprints/sprint-[NUMBER]-completion-summary.md`
  - Goals achieved (use ✅ checklist format).
  - Technical deliverables and architecture changes.
  - Integration points with the existing system.
  - Testing coverage and results.
  - Files created/modified list.
  - Future considerations.
- **Finalize ADRs**: Complete any draft architectural decisions.
- **Update Technical Debt**: Move resolved items to archive, add new debt.
- **Update Documentation Index**: Add any new documents created.
- **Link Sprint Summary**: Update `docs/docs-index.md` if a new document structure is created.

### Conditional Updates (if applicable)
- **Feature Docs**: Document new features in `docs/features/[feature-name].md`.