# Sprint Folder Template & Prompt

**Use this template to create consistent, comprehensive sprint documentation for TickStockAppV2.**

## Sprint Folder Structure Template

```
docs/planning/sprints/sprint{XX}/
├── sprint{XX}_{feature_name}.md           # Main sprint specification document
├── sprint{XX}_definition_of_done.md       # Complete success criteria and validation
├── implementation_guide.md                # Optional: Detailed implementation steps
├── api_specifications.md                  # Optional: Detailed API documentation
└── technical_design.md                    # Optional: Deep technical architecture
```

## Required Files

### 1. **Main Sprint Document**: `sprint{XX}_{feature_name}.md`
**Template Structure:**
```markdown
# Sprint {XX}: {Feature Name}

**Priority**: {CRITICAL|HIGH|MEDIUM|LOW}  
**Duration**: {X weeks}  
**Status**: {Planning|In Progress|Complete}  
**Prerequisites**: {Previous sprints that must be complete}

## Sprint Objectives
{2-3 sentences describing the main goals}

## {Feature} Architecture
{High-level architecture diagram or description}

## Implementation Components

### {X.1} {Component Group 1}
**Core Services:**
```python
src/path/to/service.py    # Description
```
**Features:**
- {Feature 1}
- {Feature 2}

### {X.2} {Component Group 2}
{Similar structure}

## WebSocket Integration
{Reference to core architecture - do NOT re-implement}
This feature integrates with the core WebSocket architecture documented in `docs/architecture/websocket-scalability-architecture.md`.

### {Feature} WebSocket Integration
```python
class {Feature}WebSocketIntegration:
    # Integration pattern example
```

## API Endpoints
**New API Endpoints:**
- `GET /api/{feature}/{endpoint}` - Description
- `POST /api/{feature}/{endpoint}` - Description

## Implementation Timeline
### Week 1: {Focus Area}
1. **Day 1-2**: {Specific tasks}
2. **Day 3**: {Specific tasks}
3. **Day 4-5**: {Specific tasks}

### Week 2: {Focus Area}
{Similar daily breakdown}

## Success Criteria
- [ ] **{Criterion 1}**: {Measurable success definition}
- [ ] **{Criterion 2}**: {Measurable success definition}

## Testing Strategy
### Unit Tests
### Integration Tests  
### Performance Tests

## Risk Mitigation
### Technical Risks
### User Experience Risks
```

### 2. **Definition of Done**: `sprint{XX}_definition_of_done.md`
**Template Structure:**
```markdown
# Sprint {XX}: Definition of Done & Success Criteria

**Sprint**: {XX} - {Feature Name}  
**Date**: {Date}  
**Duration**: {X weeks}  
**Status**: Definition Complete - Ready for Implementation  
**Prerequisites**: {Previous sprints required}

## Sprint Completion Checklist

### ✅ {Component Group 1} (Week 1)
- [ ] **{Specific Deliverable}**: {Measurable completion criteria}
- [ ] **{Specific Deliverable}**: {Measurable completion criteria}
- [ ] **Unit Tests Pass**: 95%+ coverage for {component group}

### ✅ {Component Group 2} (Week 2)
- [ ] **{Specific Deliverable}**: {Measurable completion criteria}
- [ ] **Integration Tests Pass**: End-to-end {feature} flow validated

## Functional Requirements Verification
### {Feature Area 1}
- [ ] **{Requirement}**: {Specific validation criteria}

### {Feature Area 2}
- [ ] **{Requirement}**: {Specific validation criteria}

## Performance Validation
### {Performance Area}
- [ ] **{Metric}**: {Target} (e.g., <100ms response time)
- [ ] **{Capacity}**: {Target} (e.g., 1000+ concurrent users)

## Quality Gates
### {Quality Area}
- [ ] **{Quality Standard}**: {Measurable criteria}

## Risk Mitigation Validation
### Technical Risks
- [ ] **{Risk}**: {Mitigation validation}

### User Experience Risks
- [ ] **{Risk}**: {Mitigation validation}

## Success Metrics
### Quantitative Metrics
- [ ] **{Metric}**: {Target percentage/time/count}

### Qualitative Metrics
- [ ] **{Metric}**: {Subjective success criteria}

## API Endpoint Validation
- [ ] **{Endpoint}**: {Response time and functionality validation}

## WebSocket Integration Validation
- [ ] **{Event Type}**: {Real-time functionality validation}

## Sprint Review Deliverables
### Demonstration Materials
- [ ] **{Demo Type}**: {Specific demo requirements}

### Documentation Deliverables
- [ ] **{Doc Type}**: {Documentation completion requirements}

### Handoff Materials
- [ ] **{Material Type}**: {Handoff completion requirements}

## Definition of Done Statement

**Sprint {XX} is considered DONE when:**

1. **{Major Achievement 1}**
2. **{Major Achievement 2}**
3. **{Performance/Quality Achievement}**

**Acceptance Criteria**: {Single paragraph describing Product Owner validation scenario}
```

## Optional Files (Use When Needed)

### 3. **Implementation Guide**: `implementation_guide.md`
Use when sprint needs detailed step-by-step implementation instructions.

### 4. **API Specifications**: `api_specifications.md`
Use when sprint introduces complex API endpoints requiring detailed documentation.

### 5. **Technical Design**: `technical_design.md`
Use when sprint involves complex technical architecture requiring deep design documentation.

---

# Sprint Creation Prompt Template

## Prompt for Creating New Sprint Documentation

**Use this prompt to create consistent sprint documentation:**

```
Create comprehensive sprint documentation for TickStockAppV2 using the established template structure:

**Sprint Details:**
- Sprint Number: {XX}
- Feature Name: {Feature Name}
- Priority: {CRITICAL|HIGH|MEDIUM|LOW}
- Duration: {X weeks}
- Prerequisites: {Required previous sprints}

**Feature Requirements:**
{2-3 paragraphs describing the feature objectives, user value, and technical scope}

**Architecture Integration:**
- Must integrate with core WebSocket architecture (docs/architecture/websocket-scalability-architecture.md)
- Must reference but NOT re-implement scalable WebSocket patterns
- Must include specific WebSocket integration class example
- Must maintain performance targets: <100ms delivery, <50ms API responses

**Documentation Requirements:**
1. Create main sprint document (sprint{XX}_{feature_name}.md) with:
   - Complete implementation component breakdown
   - Week-by-week implementation timeline with daily tasks
   - WebSocket integration patterns (reference core architecture)
   - API endpoint specifications
   - Success criteria with measurable targets
   - Risk mitigation strategies

2. Create definition of done document (sprint{XX}_definition_of_done.md) with:
   - Detailed completion checklists (50+ items)
   - Functional requirements verification
   - Performance validation criteria with specific metrics
   - Quality gates with measurable standards
   - Success metrics (quantitative and qualitative)
   - Sprint review deliverables
   - Clear Definition of Done statement with Acceptance Criteria

**Technical Standards:**
- All code examples in Python/JavaScript
- File paths must follow established TickStockAppV2 structure
- Performance targets must be specific and measurable
- Integration patterns must reference existing architecture
- Testing strategies must include unit, integration, and performance tests

**Quality Standards:**
- Each deliverable must be measurable and verifiable
- Success criteria must include both technical and user experience metrics
- Risk mitigation must address technical, UX, and business risks
- Documentation must provide sufficient detail for independent implementation

**Output Format:**
Provide both markdown files ready for immediate use, following the exact template structure and maintaining consistency with existing TickStockAppV2 sprint documentation.
```

## Usage Instructions

### For New Sprints:
1. **Copy the prompt template** above
2. **Fill in the {placeholder} values** with your specific sprint details
3. **Add your feature-specific requirements** in the Feature Requirements section
4. **Use the prompt** to generate comprehensive sprint documentation
5. **Review and adjust** generated content for TickStockAppV2 consistency

### For Consistency:
- **Always use the folder structure** specified in the template
- **Always include both required files** (main sprint + definition of done)
- **Always reference WebSocket architecture** instead of re-implementing
- **Always include measurable success criteria** with specific metrics
- **Always follow the established naming conventions**

### Quality Checklist:
- [ ] Sprint document includes week-by-week implementation timeline
- [ ] Definition of Done has 50+ measurable completion criteria
- [ ] WebSocket integration references core architecture document
- [ ] Performance targets are specific (e.g., <100ms, not "fast")
- [ ] Success criteria are measurable and verifiable
- [ ] Risk mitigation addresses technical, UX, and business concerns
- [ ] Documentation sufficient for independent implementation by new developer

This template ensures consistency across all sprint documentation and provides the comprehensive detail needed for successful sprint execution and handoff between development sessions.

---

# Sprint Implementation Kickoff Prompt Template

## Prompt for Starting Sprint Implementation

**Use this prompt to begin sprint implementation with proper context and requirements:**

```
I'm starting Sprint {XX} implementation for TickStockAppV2 - "{Feature Name}". 

Please review the complete sprint documentation in docs/planning/sprints/sprint{XX}/ and begin Week 1 Phase 1 implementation focusing on the {CRITICAL FOUNDATION|PRIORITY} components that must be built in {strict dependency order|established sequence}:

**Week 1 Priority Sequence ({NON-NEGOTIABLE|REQUIRED}):**
1. Day 1: {Primary Component} ({foundation description})
2. Day 2: {Secondary Component} ({dependency description})
3. Day 3: {Third Component} ({integration description})
4. Day 4: {Fourth Component} ({coordination description})
5. Day 5: {Integration Component} ({wrapper description})

**Critical Requirements:**
- Follow the {architecture document} architecture in docs/architecture/{architecture-file}.md
- Maintain TickStockAppV2 {consumer|integration} role ({role description})
- Target {performance target} with {delivery target}
- Each component must be fully tested before proceeding to next dependency

**Key Implementation Files:**
- src/{path}/{primary_service}.py
- src/{path}/{secondary_service}.py  
- src/{path}/{integration_service}.py
- src/{path}/{wrapper_service}.py

Please start with Day 1: {Primary Component} implementation and use the mandatory agent workflow ({primary agent} first, then {testing agent} for comprehensive testing).

Reference the Definition of Done checklist for validation criteria as we progress.
```

## Sprint 25 Example Implementation Prompt

**Actual example from Sprint 25 Tier-Specific Event Handling:**

```
I'm starting Sprint 25 implementation for TickStockAppV2 - "Tier-Specific Event Handling & Multi-Tier Dashboard". 

Please review the complete sprint documentation in docs/planning/sprints/sprint25/ and begin Week 1 Phase 1 implementation focusing on the CRITICAL FOUNDATION components that must be built in strict dependency order:

**Week 1 Priority Sequence (NON-NEGOTIABLE):**
1. Day 1: UniversalWebSocketManager core service (foundation for everything)
2. Day 2: SubscriptionIndexManager for <5ms user filtering 
3. Day 3: ScalableBroadcaster with batching and rate limiting
4. Day 4: EventRouter for intelligent message routing
5. Day 5: TierPatternWebSocketIntegration wrapper

**Critical Requirements:**
- Follow the WebSocket scalability architecture in docs/architecture/websocket-scalability-architecture.md
- Maintain TickStockAppV2 consumer role (consume TickStockPL Redis events only)
- Target 500+ concurrent users with <100ms WebSocket delivery
- Each component must be fully tested before proceeding to next dependency

**Key Implementation Files:**
- src/core/services/websocket_subscription_manager.py
- src/infrastructure/websocket/scalable_broadcaster.py  
- src/infrastructure/websocket/event_router.py
- src/core/services/tier_pattern_websocket_integration.py

Please start with Day 1: UniversalWebSocketManager implementation and use the mandatory agent workflow (architecture-validation-specialist first, then tickstock-test-specialist for comprehensive testing).

Reference the Definition of Done checklist for validation criteria as we progress.
```

## Implementation Prompt Customization Guide

### For {placeholder} Replacement:

1. **{XX}**: Sprint number (e.g., 25, 26, 27)
2. **{Feature Name}**: Full feature name from sprint title
3. **{CRITICAL FOUNDATION|PRIORITY}**: Urgency level of Week 1 components
4. **{strict dependency order|established sequence}**: Description of implementation constraints
5. **{NON-NEGOTIABLE|REQUIRED}**: Compliance level for sequence requirements
6. **{Primary Component}**: Day 1 foundational component name
7. **{Secondary Component}**: Day 2 dependent component name
8. **{performance target}**: Specific performance requirement (e.g., "500+ concurrent users")
9. **{delivery target}**: Specific delivery requirement (e.g., "<100ms WebSocket delivery")
10. **{architecture document}**: Reference architecture name (e.g., "WebSocket scalability")
11. **{architecture-file}**: Architecture file name (e.g., "websocket-scalability-architecture")
12. **{consumer|integration} role**: TickStockAppV2's architectural role
13. **{primary agent}**: First mandatory agent (e.g., "architecture-validation-specialist")
14. **{testing agent}**: Testing agent (e.g., "tickstock-test-specialist")
15. **src/{path}/**: Actual implementation file paths from sprint documentation

### Usage Instructions:

1. **Review Sprint Documentation**: Always reference the complete sprint documentation first
2. **Identify Critical Path**: Determine the Week 1 foundation components and their dependencies
3. **Extract File Paths**: Use actual file paths from the sprint implementation components section
4. **Set Performance Targets**: Include specific, measurable performance requirements
5. **Reference Architecture**: Always include the relevant architecture document reference
6. **Specify Agent Workflow**: Include the mandatory specialized agent requirements

### Quality Checklist for Implementation Prompts:

- [ ] References complete sprint documentation location
- [ ] Includes Week 1 daily breakdown with specific components
- [ ] Specifies critical dependency order and constraints
- [ ] Lists actual implementation file paths from sprint docs
- [ ] Includes specific performance targets and validation criteria
- [ ] References appropriate architecture documentation
- [ ] Specifies mandatory agent workflow requirements
- [ ] Includes Definition of Done reference for validation

This implementation prompt template ensures consistent sprint kickoffs with proper context, requirements, and quality gates for successful development execution.