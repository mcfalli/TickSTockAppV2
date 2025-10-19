#!/usr/bin/env python3
"""
PRP Validation Script

Validates Product Requirement Prompts (PRPs) for completeness, correctness, and quality.

Usage:
    python scripts/prp_validator.py <prp-file>
    python scripts/prp_validator.py docs/planning/sprints/sprint44/health-check-enhancement.md

    # Validate all PRPs in a sprint
    python scripts/prp_validator.py docs/planning/sprints/sprint44/*.md

    # Validate all sprint PRPs
    python scripts/prp_validator.py --all-sprints
"""

import argparse
import re
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class Severity(Enum):
    """Validation issue severity levels."""
    ERROR = "ERROR"  # Must fix - PRP is incomplete
    WARNING = "WARNING"  # Should fix - PRP quality issue
    INFO = "INFO"  # Nice to have - PRP improvement suggestion


@dataclass
class ValidationIssue:
    """Represents a validation issue found in PRP."""
    severity: Severity
    section: str
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Results of PRP validation."""
    prp_file: Path
    template_type: Optional[str] = None  # "prp-new", "prp-change", "unknown"
    issues: List[ValidationIssue] = field(default_factory=list)
    score: int = 100  # Start at 100, deduct for issues

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def infos(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.INFO]

    @property
    def passed(self) -> bool:
        """PRP passes validation if no errors."""
        return len(self.errors) == 0

    def calculate_score(self):
        """Calculate quality score based on issues."""
        self.score = 100
        for issue in self.issues:
            if issue.severity == Severity.ERROR:
                self.score -= 20
            elif issue.severity == Severity.WARNING:
                self.score -= 5
            elif issue.severity == Severity.INFO:
                self.score -= 1
        self.score = max(0, self.score)


class PRPValidator:
    """Validates PRP files for completeness and quality."""

    def __init__(self, prp_file: Path):
        self.prp_file = prp_file
        self.content = ""
        self.lines = []
        self.result = ValidationResult(prp_file=prp_file)

    def validate(self) -> ValidationResult:
        """Run all validations on PRP file."""
        if not self.prp_file.exists():
            self.result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                section="File",
                message=f"PRP file does not exist: {self.prp_file}"
            ))
            self.result.calculate_score()
            return self.result

        # Read file
        try:
            self.content = self.prp_file.read_text(encoding='utf-8')
            self.lines = self.content.split('\n')
        except Exception as e:
            self.result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                section="File",
                message=f"Failed to read PRP file: {e}"
            ))
            self.result.calculate_score()
            return self.result

        # Detect template type
        self._detect_template_type()

        # Run validations
        self._validate_required_sections()
        self._validate_goal_section()
        self._validate_context_section()
        self._validate_implementation_tasks()
        self._validate_validation_gates()
        self._validate_references()
        self._validate_yaml_format()
        self._validate_antipatterns()
        self._validate_file_references()

        # Calculate final score
        self.result.calculate_score()

        return self.result

    def _detect_template_type(self):
        """Detect which template (prp-new or prp-change) this PRP uses."""
        if "## Current Implementation Analysis" in self.content:
            self.result.template_type = "prp-change"
        elif "## Implementation Blueprint" in self.content or "Desired Codebase tree" in self.content:
            self.result.template_type = "prp-new"
        else:
            self.result.template_type = "unknown"
            self.result.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                section="Template",
                message="Cannot detect template type (prp-new or prp-change)",
                suggestion="Ensure PRP follows standard template structure"
            ))

    def _validate_required_sections(self):
        """Validate all required sections are present."""
        required_sections_common = [
            "## Goal",
            "## Why",
            "## What",
            "## All Needed Context",
            "## Validation Loop",
            "## Final Validation Checklist",
            "## Anti-Patterns to Avoid"
        ]

        required_sections_new = [
            "## Implementation Blueprint",
            "### Implementation Tasks"
        ]

        required_sections_change = [
            "## Current Implementation Analysis",
            "## Impact Analysis",
            "### Change Tasks"
        ]

        # Check common sections
        for section in required_sections_common:
            if section not in self.content:
                self.result.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    section=section.replace("## ", ""),
                    message=f"Missing required section: {section}"
                ))

        # Check template-specific sections
        if self.result.template_type == "prp-new":
            for section in required_sections_new:
                if section not in self.content:
                    self.result.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        section=section.replace("### ", "").replace("## ", ""),
                        message=f"Missing required section for prp-new: {section}"
                    ))

        elif self.result.template_type == "prp-change":
            for section in required_sections_change:
                if section not in self.content:
                    self.result.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        section=section.replace("### ", "").replace("## ", ""),
                        message=f"Missing required section for prp-change: {section}"
                    ))

    def _validate_goal_section(self):
        """Validate Goal section completeness."""
        goal_pattern = r'## Goal\s*\n\s*\*\*Feature Goal\*\*:|## Goal\s*\n\s*\*\*Change Type\*\*:'
        if not re.search(goal_pattern, self.content):
            self.result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                section="Goal",
                message="Goal section missing **Feature Goal** or **Change Type**"
            ))

        # Check for placeholders
        if "[Specific" in self.content or "[What the system" in self.content:
            self.result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                section="Goal",
                message="Goal section contains template placeholders - must be filled in",
                suggestion="Replace all [placeholder] text with actual content"
            ))

        # Check for Success Definition
        if "**Success Definition**:" not in self.content:
            self.result.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                section="Goal",
                message="Missing **Success Definition** in Goal section",
                suggestion="Add concrete success criteria"
            ))

    def _validate_context_section(self):
        """Validate All Needed Context section."""
        # Check for Context Completeness Check
        if "Context Completeness Check" not in self.content:
            self.result.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                section="Context",
                message="Missing Context Completeness Check section",
                suggestion='Add "No Prior Knowledge" test validation'
            ))

        # Check for TickStock Architecture Context YAML
        if "```yaml\ntickstock_architecture:" not in self.content:
            self.result.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                section="Context",
                message="Missing TickStock Architecture Context YAML",
                suggestion="Add tickstock_architecture YAML block with component roles, channels, etc."
            ))

        # Check for Documentation & References
        if "### Documentation & References" not in self.content:
            self.result.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                section="Context",
                message="Missing Documentation & References section",
                suggestion="Add URLs, file references, and gotchas"
            ))

    def _validate_implementation_tasks(self):
        """Validate Implementation Tasks section."""
        if self.result.template_type == "prp-new":
            if "### Implementation Tasks" not in self.content:
                self.result.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    section="Implementation Tasks",
                    message="Missing Implementation Tasks section"
                ))
            else:
                # Check for dependency-ordered tasks
                if "```yaml" not in self.content or "Task 1:" not in self.content:
                    self.result.issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        section="Implementation Tasks",
                        message="Tasks should be in YAML format with dependency ordering",
                        suggestion="Use 'Task 1:', 'Task 2:', etc. in YAML block"
                    ))

        elif self.result.template_type == "prp-change":
            if "### Change Tasks" not in self.content:
                self.result.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    section="Change Tasks",
                    message="Missing Change Tasks section"
                ))

    def _validate_validation_gates(self):
        """Validate Validation Loop section."""
        required_levels = [
            "### Level 1: Syntax & Style",
            "### Level 2: Unit Tests",
            "### Level 3: Integration Testing",
            "### Level 4:"  # TickStock-Specific or Project-Specific
        ]

        for level in required_levels:
            if level not in self.content:
                self.result.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    section="Validation Loop",
                    message=f"Missing validation level: {level}",
                    suggestion="All 4 validation levels are required"
                ))

        # Check for Level 5 (Regression Testing) in prp-change
        if self.result.template_type == "prp-change":
            if "### Level 5: Regression Testing" not in self.content:
                self.result.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    section="Validation Loop",
                    message="prp-change template should include Level 5: Regression Testing",
                    suggestion="Add regression testing validation level"
                ))

        # Check for project-specific commands
        if "python run_tests.py" not in self.content:
            self.result.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                section="Validation Loop",
                message="Missing TickStock-specific integration test command",
                suggestion="Include 'python run_tests.py' in Level 3 validation"
            ))

    def _validate_references(self):
        """Validate file references and URLs."""
        # Find all file references
        file_pattern = r'(?:file:|File:)\s*([^\s\n]+\.py)'
        file_refs = re.findall(file_pattern, self.content)

        project_root = Path(__file__).parent.parent
        for file_ref in file_refs:
            # Normalize path
            file_path = project_root / file_ref.replace("src/", "src/")

            if not file_path.exists():
                self.result.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    section="References",
                    message=f"Referenced file may not exist or path incorrect: {file_ref}",
                    suggestion="Verify file path is correct relative to project root"
                ))

        # Find all URLs
        url_pattern = r'https?://[^\s\)\"\'<>]+'
        urls = re.findall(url_pattern, self.content)

        # Check for URLs without section anchors (best practice)
        generic_urls = [u for u in urls if '#' not in u and 'github.com' not in u]
        if len(generic_urls) > 3:
            self.result.issues.append(ValidationIssue(
                severity=Severity.INFO,
                section="References",
                message=f"Found {len(generic_urls)} URLs without section anchors",
                suggestion="Use URL anchors for precision (e.g., #section-name)"
            ))

    def _validate_yaml_format(self):
        """Validate YAML blocks are properly formatted."""
        yaml_blocks = re.findall(r'```yaml\n(.*?)\n```', self.content, re.DOTALL)

        for i, block in enumerate(yaml_blocks):
            # Check for proper indentation (2 or 4 spaces)
            lines = block.split('\n')
            for line_num, line in enumerate(lines):
                if line.strip() and not line.startswith(' ') and ':' in line and line_num > 0:
                    # Check if it's a top-level key (should not be indented)
                    if not re.match(r'^[a-z_]+:', line):
                        self.result.issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            section="YAML Format",
                            message=f"YAML block {i+1} may have inconsistent indentation",
                            suggestion="Use consistent 2-space or 4-space indentation"
                        ))
                        break

    def _validate_antipatterns(self):
        """Validate Anti-Patterns section."""
        if "## Anti-Patterns to Avoid" not in self.content:
            self.result.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                section="Anti-Patterns",
                message="Missing Anti-Patterns to Avoid section"
            ))
        else:
            # Check for TickStock-specific anti-patterns
            tickstock_antipatterns = [
                "Consumer/Producer",
                "Redis",
                "OHLCV"
            ]

            antipatterns_section = self.content.split("## Anti-Patterns to Avoid")[1].split("##")[0]

            missing_antipatterns = []
            for pattern in tickstock_antipatterns:
                if pattern not in antipatterns_section:
                    missing_antipatterns.append(pattern)

            if len(missing_antipatterns) > 0:
                self.result.issues.append(ValidationIssue(
                    severity=Severity.INFO,
                    section="Anti-Patterns",
                    message=f"Consider adding TickStock-specific anti-patterns: {', '.join(missing_antipatterns)}",
                    suggestion="Reference TickStock architecture constraints in anti-patterns"
                ))

    def _validate_file_references(self):
        """Check if referenced files include line numbers."""
        # Pattern: file.py without line number
        file_no_line_pattern = r'(?:file:|File:)\s*([^\s\n]+\.py)(?!\s*(?:line|lines|\d))'
        matches = re.findall(file_no_line_pattern, self.content)

        if len(matches) > 3:
            self.result.issues.append(ValidationIssue(
                severity=Severity.INFO,
                section="References",
                message=f"Found {len(matches)} file references without line numbers",
                suggestion="Include line numbers for precision (e.g., 'src/app.py:526')"
            ))


def format_validation_result(result: ValidationResult, verbose: bool = False) -> str:
    """Format validation result for display."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append(f"PRP Validation Report: {result.prp_file.name}")
    lines.append("=" * 80)

    # Template type
    if result.template_type:
        lines.append(f"Template Type: {result.template_type}")
    lines.append("")

    # Summary
    lines.append(f"Score: {result.score}/100")
    lines.append(f"Status: {'✅ PASS' if result.passed else '❌ FAIL'}")
    lines.append(f"Errors: {len(result.errors)}")
    lines.append(f"Warnings: {len(result.warnings)}")
    lines.append(f"Info: {len(result.infos)}")
    lines.append("")

    # Issues
    if result.errors:
        lines.append("❌ ERRORS (must fix):")
        lines.append("-" * 80)
        for issue in result.errors:
            lines.append(f"  [{issue.section}] {issue.message}")
            if verbose and issue.suggestion:
                lines.append(f"    💡 Suggestion: {issue.suggestion}")
        lines.append("")

    if result.warnings:
        lines.append("⚠️  WARNINGS (should fix):")
        lines.append("-" * 80)
        for issue in result.warnings:
            lines.append(f"  [{issue.section}] {issue.message}")
            if verbose and issue.suggestion:
                lines.append(f"    💡 Suggestion: {issue.suggestion}")
        lines.append("")

    if verbose and result.infos:
        lines.append("ℹ️  INFO (nice to have):")
        lines.append("-" * 80)
        for issue in result.infos:
            lines.append(f"  [{issue.section}] {issue.message}")
            if issue.suggestion:
                lines.append(f"    💡 Suggestion: {issue.suggestion}")
        lines.append("")

    # Quality assessment
    lines.append("-" * 80)
    if result.score >= 90:
        lines.append("✅ Quality: EXCELLENT - PRP is comprehensive and ready for execution")
    elif result.score >= 75:
        lines.append("🟢 Quality: GOOD - Minor improvements recommended")
    elif result.score >= 60:
        lines.append("🟡 Quality: FAIR - Several issues should be addressed")
    else:
        lines.append("🔴 Quality: POOR - Significant gaps must be fixed before execution")

    lines.append("=" * 80)
    lines.append("")

    return '\n'.join(lines)


def validate_prp_file(prp_file: Path, verbose: bool = False) -> ValidationResult:
    """Validate a single PRP file."""
    validator = PRPValidator(prp_file)
    result = validator.validate()

    print(format_validation_result(result, verbose=verbose))

    return result


def validate_all_sprints(verbose: bool = False) -> List[ValidationResult]:
    """Validate all PRPs in sprint folders."""
    project_root = Path(__file__).parent.parent
    sprints_dir = project_root / "docs" / "planning" / "sprints"

    results = []

    if not sprints_dir.exists():
        print(f"❌ Sprints directory not found: {sprints_dir}")
        return results

    # Find all PRP files (exclude AMENDMENT, RESULTS, NOTES)
    for sprint_dir in sorted(sprints_dir.glob("sprint*")):
        if not sprint_dir.is_dir():
            continue

        for prp_file in sprint_dir.glob("*.md"):
            # Skip auxiliary files
            if any(suffix in prp_file.name for suffix in ['-AMENDMENT', '-RESULTS', '-NOTES', '-MIGRATION', 'SPRINT', 'README', 'PLAN']):
                continue

            print(f"\n📄 Validating: {prp_file.relative_to(project_root)}")
            result = validate_prp_file(prp_file, verbose=verbose)
            results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total PRPs validated: {len(results)}")
    print(f"Passed: {len([r for r in results if r.passed])}")
    print(f"Failed: {len([r for r in results if not r.passed])}")
    print(f"Average Score: {sum(r.score for r in results) / len(results):.1f}/100" if results else "N/A")
    print("=" * 80)

    return results


def main():
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(
        description="Validate Product Requirement Prompts (PRPs) for completeness and quality"
    )
    parser.add_argument(
        'prp_files',
        nargs='*',
        help='PRP files to validate'
    )
    parser.add_argument(
        '--all-sprints',
        action='store_true',
        help='Validate all PRPs in sprint folders'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed suggestions for all issue types'
    )

    args = parser.parse_args()

    if args.all_sprints:
        results = validate_all_sprints(verbose=args.verbose)
        # Exit with error code if any PRPs failed
        sys.exit(0 if all(r.passed for r in results) else 1)

    elif args.prp_files:
        results = []
        for prp_file_str in args.prp_files:
            prp_file = Path(prp_file_str)
            if not prp_file.exists():
                print(f"❌ File not found: {prp_file}")
                continue

            result = validate_prp_file(prp_file, verbose=args.verbose)
            results.append(result)

        # Exit with error code if any PRPs failed
        sys.exit(0 if all(r.passed for r in results) else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
