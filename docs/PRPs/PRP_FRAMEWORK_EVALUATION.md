# PRP Framework Evaluation Prompt

> Use this prompt in a new Claude Code chat session to evaluate the PRP framework's effectiveness, completeness, and quality.

---

## Evaluation Prompt

```
I have a Product Requirement Prompt (PRP) framework for AI-assisted software development.

Please analyze, score, and evaluate the PRP framework located in this codebase.

EVALUATION CRITERIA:

1. CONCEPT & PHILOSOPHY (20 points)
   - Does the framework solve a real problem?
   - Is the philosophy sound and well-articulated?
   - Is there clear differentiation from traditional PRDs?
   - Are the three AI-critical layers (Context, Implementation, Validation) well-defined?

2. TEMPLATE QUALITY (25 points)
   - Are templates comprehensive and actionable?
   - Do templates include TickStock-specific context?
   - Is there clear guidance for NEW vs CHANGE scenarios?
   - Are validation gates (4-5 levels) well-structured?
   - Do templates pass the "No Prior Knowledge" test?

3. SUPPORT RESOURCES (20 points)
   - Framework Pattern Library completeness
   - Decision Tree usability and clarity
   - Validation tooling effectiveness
   - Documentation quality and accessibility

4. REAL-WORLD EVIDENCE (20 points)
   - Sprint 44 case study analysis
   - Time savings quantification
   - One-pass success rate improvement
   - AMENDMENT feedback loop effectiveness

5. USABILITY & WORKFLOW (15 points)
   - Slash command integration (/prp-new-create, /prp-new-execute, etc.)
   - Workflow clarity (creation → execution → documentation)
   - Decision support (when to use/skip PRPs)
   - Continuous improvement mechanisms

TOTAL: 100 points

ANALYSIS REQUIREMENTS:

For each criterion:
- Assign a score (0-max points for that criterion)
- Provide 2-3 sentence justification
- Identify 1-2 specific strengths
- Identify 1-2 specific gaps or improvements

Overall Assessment:
- Total score /100
- Letter grade (A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: <60)
- 1-paragraph executive summary
- Top 3 strengths
- Top 3 improvement opportunities
- Comparison to industry-standard approaches (if applicable)

DELIVERABLE FORMAT:

Provide a comprehensive evaluation report with:
1. Criterion-by-criterion scoring and analysis
2. Overall score and letter grade
3. Executive summary (3-5 sentences)
4. Strengths and weaknesses
5. Recommendations for improvement
6. Industry comparison (if relevant patterns exist)

START YOUR ANALYSIS HERE:

Begin by reading the following key files:
1. docs/PRPs/README.md - PRP concept and organization
2. docs/PRPs/templates/prp-new.md - NEW feature template
3. docs/PRPs/templates/prp-change.md - CHANGE template
4. docs/PRPs/DECISION_TREE.md - Decision support
5. docs/PRPs/ai_docs/flask_patterns.md - Pattern library example
6. docs/PRPs/ai_docs/redis_patterns.md - Pattern library example
7. docs/planning/sprints/sprint44/health-check-enhancement.md - Real PRP example
8. docs/planning/sprints/sprint44/health-check-enhancement-AMENDMENT.md - Feedback loop example
9. scripts/prp_validator.py - Validation tooling
10. docs/PRPs/ENHANCEMENTS_SUMMARY.md - Enhancement overview

After reading these files, provide your comprehensive evaluation.
```

---

## Expected Analysis Output

The evaluating AI should produce a structured report like this:

```markdown
# PRP Framework Evaluation Report

**Evaluator**: Claude Code (Fresh Instance)
**Date**: [Current Date]
**Framework Version**: 2.0 (Enhanced)

---

## Criterion-by-Criterion Analysis

### 1. Concept & Philosophy (X/20 points)

**Score**: X/20

**Justification**:
[2-3 sentence analysis of whether the framework solves the "80% stall problem,"
articulates a sound philosophy, differentiates from PRDs, and defines the three layers]

**Strengths**:
- [Specific strength 1]
- [Specific strength 2]

**Gaps/Improvements**:
- [Specific gap or improvement 1]
- [Specific gap or improvement 2]

### 2. Template Quality (X/25 points)

**Score**: X/25

**Justification**:
[Analysis of template comprehensiveness, TickStock-specific context, NEW vs CHANGE
differentiation, validation gates, and "No Prior Knowledge" test]

**Strengths**:
- [Specific strength 1]
- [Specific strength 2]

**Gaps/Improvements**:
- [Specific gap or improvement 1]
- [Specific gap or improvement 2]

### 3. Support Resources (X/20 points)

**Score**: X/20

**Justification**:
[Analysis of pattern library (Flask, Redis), Decision Tree, validation script,
and documentation quality]

**Strengths**:
- [Specific strength 1]
- [Specific strength 2]

**Gaps/Improvements**:
- [Specific gap or improvement 1]
- [Specific gap or improvement 2]

### 4. Real-World Evidence (X/20 points)

**Score**: X/20

**Justification**:
[Analysis of Sprint 44 case study, time savings data (~60 min), one-pass success
improvement, and AMENDMENT feedback effectiveness]

**Strengths**:
- [Specific strength 1]
- [Specific strength 2]

**Gaps/Improvements**:
- [Specific gap or improvement 1]
- [Specific gap or improvement 2]

### 5. Usability & Workflow (X/15 points)

**Score**: X/15

**Justification**:
[Analysis of slash commands, workflow clarity, decision support, and continuous
improvement mechanisms]

**Strengths**:
- [Specific strength 1]
- [Specific strength 2]

**Gaps/Improvements**:
- [Specific gap or improvement 1]
- [Specific gap or improvement 2]

---

## Overall Assessment

**Total Score**: X/100
**Letter Grade**: [A/B/C/D/F]

### Executive Summary

[3-5 sentence overall assessment covering: problem addressed, solution approach,
effectiveness based on evidence, key innovations, and overall recommendation]

### Top 3 Strengths

1. **[Strength 1 Title]**: [1-2 sentence explanation]
2. **[Strength 2 Title]**: [1-2 sentence explanation]
3. **[Strength 3 Title]**: [1-2 sentence explanation]

### Top 3 Improvement Opportunities

1. **[Opportunity 1 Title]**: [1-2 sentence explanation + suggested action]
2. **[Opportunity 2 Title]**: [1-2 sentence explanation + suggested action]
3. **[Opportunity 3 Title]**: [1-2 sentence explanation + suggested action]

### Industry Comparison

[2-3 paragraphs comparing to:
- Traditional PRDs
- Agile user stories
- BDD (Behavior-Driven Development) specifications
- Other prompt engineering frameworks
- Software specification best practices]

**Key Differentiators**:
- [Differentiator 1]
- [Differentiator 2]
- [Differentiator 3]

---

## Detailed Findings

### Template Comprehensiveness Check

**prp-new.md Analysis**:
- Required sections: [X/Y present]
- TickStock-specific sections: [X/Y present]
- Validation gates: [X/Y levels defined]
- "No Prior Knowledge" test: [Pass/Fail with explanation]

**prp-change.md Analysis**:
- Required sections: [X/Y present]
- Dependency analysis: [Adequate/Inadequate]
- Impact analysis: [Adequate/Inadequate]
- Regression testing: [Level 5 present: Yes/No]

### Pattern Library Assessment

**Coverage**:
- Flask patterns: [X topics covered, gaps: Y]
- Redis patterns: [X topics covered, gaps: Y]
- Missing frameworks: [List any critical gaps]

**Quality**:
- Working examples: [Adequate/Inadequate]
- Line-number references: [Present/Absent]
- TickStock-specific gotchas: [Well-documented/Poorly-documented]

### Decision Tree Effectiveness

**Clarity**: [Score 1-10]
**Completeness**: [Covers X/Y common scenarios]
**ROI Calculator**: [Accurate/Inaccurate based on Sprint 44 data]
**Scoring Matrix**: [Objective/Subjective]

### Validation Tooling

**Functionality**: [Works as expected: Yes/No]
**Coverage**: [Validates X/Y critical aspects]
**Usability**: [Easy/Moderate/Difficult to use]
**Output Quality**: [Actionable/Vague]

---

## Recommendations

### Immediate Actions (High Priority)

1. **[Recommendation 1]**
   - Why: [Justification]
   - Impact: [Expected improvement]
   - Effort: [Low/Medium/High]

2. **[Recommendation 2]**
   - Why: [Justification]
   - Impact: [Expected improvement]
   - Effort: [Low/Medium/High]

3. **[Recommendation 3]**
   - Why: [Justification]
   - Impact: [Expected improvement]
   - Effort: [Low/Medium/High]

### Medium-Term Enhancements

[List 3-5 medium-priority improvements with brief justifications]

### Long-Term Vision

[1-2 paragraphs on how the framework could evolve to maximize value]

---

## Conclusion

**Is this framework production-ready?** [Yes/No with explanation]

**Would you recommend using this framework?** [Yes/No with conditions]

**Overall Verdict**: [1-paragraph final assessment]

---

**Evaluator Signature**: Claude Code (Fresh Instance)
**Evaluation Methodology**: Comprehensive file analysis, evidence-based scoring, industry comparison
**Confidence Level**: [High/Medium/Low based on information available]
```

---

## Evaluation Calibration

### Scoring Guidance

**90-100 (Grade A)**: Exceptional framework, production-ready, minimal gaps, strong real-world evidence
**80-89 (Grade B)**: Strong framework, mostly production-ready, some gaps, adequate evidence
**70-79 (Grade C)**: Functional framework, needs improvements, significant gaps, limited evidence
**60-69 (Grade D)**: Weak framework, major gaps, insufficient evidence, not production-ready
**<60 (Grade F)**: Fundamentally flawed, unusable, critical gaps, no evidence

### What "Good" Looks Like

**Concept & Philosophy (18-20/20)**:
- Clearly articulates the "80% stall problem"
- Three layers (Context, Implementation, Validation) are distinct and necessary
- Philosophy is backed by research or empirical evidence
- Differentiates from PRDs with concrete examples

**Template Quality (22-25/25)**:
- All required sections present and comprehensive
- TickStock-specific context (component roles, Redis channels, performance targets)
- "No Prior Knowledge" test explicitly validated
- Validation gates have project-specific commands
- prp-change includes Level 5 regression testing

**Support Resources (18-20/20)**:
- Pattern library covers 2+ frameworks with 5+ patterns each
- Decision Tree includes ROI calculator with real data
- Validation script catches 8+ issue types with severity levels
- Documentation is accessible and actionable

**Real-World Evidence (18-20/20)**:
- At least 1 complete case study (Sprint 44)
- Quantified time savings with before/after comparison
- AMENDMENT documents show feedback loop working
- Success metrics show improvement (confidence score, debug iterations)

**Usability & Workflow (13-15/15)**:
- Slash commands for creation and execution
- Clear 4-5 step workflow (decide → create → validate → execute → document)
- Decision tree prevents over/under-use
- Templates are self-improving via AMENDMENT loop

---

## Usage Instructions

1. **Start new Claude Code chat session** (ensures unbiased evaluation)

2. **Paste the Evaluation Prompt** from the top of this document

3. **Allow AI to read all referenced files** (10 files total)

4. **Review the comprehensive evaluation report** produced by the AI

5. **Compare evaluation to self-assessment**:
   - Does external evaluator confirm internal assessment?
   - Are there blind spots in original design?
   - Do scores align with expected quality (80-90/100)?

6. **Action on recommendations**:
   - Prioritize "Immediate Actions" from evaluation
   - Plan "Medium-Term Enhancements"
   - Consider "Long-Term Vision" for roadmap

---

## Expected Baseline Score (Self-Assessment)

Based on current implementation (Framework Version 2.0):

| Criterion | Expected Score | Reasoning |
|-----------|---------------|-----------|
| Concept & Philosophy | 18-20/20 | Strong articulation, clear three layers, real problem |
| Template Quality | 20-23/25 | Comprehensive, TickStock-specific, some YAML inconsistencies |
| Support Resources | 17-19/20 | Strong pattern library + decision tree + validation, minor gaps (SQLAlchemy, Testing patterns) |
| Real-World Evidence | 16-18/20 | Sprint 44 solid case study, 1 data point (need more sprints for confidence) |
| Usability & Workflow | 13-14/15 | Slash commands good, workflow clear, validation easy |
| **TOTAL** | **84-94/100** | **Grade: A- to B+** |

**Expected Letter Grade**: **B+ to A-** (85-92/100)

**Predicted Strengths**:
1. TickStock-specific context (component roles, channels, gotchas)
2. Four-level validation gates with project-specific commands
3. Pattern library addressing Sprint 44 gaps (Flask context, Redis pub-sub)

**Predicted Weaknesses**:
1. Single case study (Sprint 44) - need more data points
2. Pattern library gaps (SQLAlchemy, Testing, Database migrations)
3. YAML formatting inconsistencies in templates

---

## Evaluation Changelog

**Version 1.0** (2025-10-19):
- Initial evaluation prompt created
- Baseline self-assessment: 84-94/100 (B+ to A-)
- Calibrated against Sprint 44 evidence

**Future Versions**:
- Update baseline as more sprints complete
- Refine scoring criteria based on evaluation results
- Add industry benchmarks as they emerge

---

## Notes for Evaluator

### Critical Questions to Answer

1. **Does this framework solve the "80% stall problem"?**
   - Look for: Context completeness, implementation patterns, validation gates

2. **Would you use this framework yourself?**
   - Consider: Overhead vs value, decision support, pattern library quality

3. **Is the Sprint 44 evidence convincing?**
   - Analyze: Time savings (60 min), debug iterations (3 → 0-1 expected), AMENDMENT quality

4. **Are the templates production-ready?**
   - Check: "No Prior Knowledge" test, TickStock-specific sections, validation commands

5. **Does the pattern library prevent Sprint 44-type gaps?**
   - Verify: Flask context pattern documented, Redis gotchas covered, working examples

### Red Flags to Watch For

- ❌ Template placeholders not filled in (e.g., `[Specific, measurable...]`)
- ❌ Generic references without file:line specificity
- ❌ Missing validation commands or project-specific gates
- ❌ No real-world evidence or quantified time savings
- ❌ Pattern library missing critical frameworks (Flask, Redis for TickStock)
- ❌ Decision tree leads to analysis paralysis or PRP over-use
- ❌ No continuous improvement mechanism (AMENDMENT loop)

### Green Flags to Look For

- ✅ "No Prior Knowledge" test explicitly validated
- ✅ Working code examples with file:line references
- ✅ TickStock architecture context (component roles, channels, targets)
- ✅ Quantified time savings with before/after comparison
- ✅ AMENDMENT documents feeding back into templates
- ✅ Validation script catches real issues (demonstrated with Sprint 44 PRP)
- ✅ Decision tree prevents both under-use AND over-use

---

## Success Criteria for Evaluation

**Evaluation is successful if:**

1. ✅ External evaluator confirms framework is production-ready (score ≥80/100)
2. ✅ Identified gaps align with known weaknesses (pattern library gaps, single case study)
3. ✅ Recommendations are actionable and prioritized
4. ✅ Industry comparison validates uniqueness of approach
5. ✅ Evaluation provides new insights not captured in self-assessment

**Evaluation requires iteration if:**

1. ⚠️ Score <80/100 (not production-ready)
2. ⚠️ Critical gaps not identified in self-assessment
3. ⚠️ Recommendations are vague or impractical
4. ⚠️ Industry comparison shows framework is duplicative
5. ⚠️ Evaluation misses obvious strengths/weaknesses

---

**Document Version**: 1.0
**Last Updated**: 2025-10-19
**Maintained By**: TickStock Development Team
**Next Review**: After Sprint 45-46 (2+ additional case studies)
