#!/usr/bin/env python3
"""
Database Integrity Checker for TickStockAppV2
=============================================

Validates database schema, objects, and data integrity across sprints.
Generates corrective SQL when issues are found.

Usage:
    python util_test_db_integrity.py --sprint 23
    python util_test_db_integrity.py --all
    python util_test_db_integrity.py --generate-fixes

Author: TickStock Development Team
Date: 2025-09-06
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

from src.core.services.config_manager import get_config

# Get configuration
try:
    config = get_config()
except:
    config = None

@dataclass
class IntegrityCheck:
    """Represents a single integrity check"""
    name: str
    category: str
    sprint: str
    sql_query: str
    expected_result: any
    fix_sql: str | None = None
    description: str = ""

@dataclass
class CheckResult:
    """Result of an integrity check"""
    check_name: str
    passed: bool
    actual_result: any
    expected_result: any
    error_message: str | None = None
    fix_sql: str | None = None

class DatabaseIntegrityChecker:
    """Main class for database integrity checking"""

    def __init__(self, connection_params: dict[str, str]):
        """Initialize with database connection parameters"""
        self.connection_params = connection_params
        self.connection = None
        self.checks: list[IntegrityCheck] = []
        self._register_sprint23_checks()

    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            self.connection.autocommit = True
            print(f"✅ Connected to database: {self.connection_params['database']}")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("🔌 Database connection closed")

    def _register_sprint23_checks(self):
        """Register all Sprint 23 integrity checks"""

        # Phase 1A: Market Conditions Table Checks
        self.checks.extend([
            IntegrityCheck(
                name="market_conditions_table_exists",
                category="tables",
                sprint="23",
                sql_query="""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'market_conditions' 
                        AND table_schema = 'public'
                    );
                """,
                expected_result=True,
                fix_sql="-- Run: docs/planning/sprints/sprint23/sql/sprint23_phase1_market_conditions_table.sql",
                description="Market conditions table must exist for pattern correlation analysis"
            ),

            IntegrityCheck(
                name="market_conditions_columns",
                category="schema",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = 'market_conditions' 
                    AND column_name IN (
                        'id', 'timestamp', 'market_volatility', 'overall_volume', 
                        'market_trend', 'session_type', 'day_of_week', 
                        'advancing_count', 'declining_count', 'sp500_change'
                    );
                """,
                expected_result=10,
                fix_sql="ALTER TABLE market_conditions ADD COLUMN [missing_column] [type];",
                description="Market conditions table must have all required columns"
            ),

            IntegrityCheck(
                name="market_conditions_view_exists",
                category="views",
                sprint="23",
                sql_query="""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.views 
                        WHERE table_name = 'v_current_market_conditions'
                    );
                """,
                expected_result=True,
                fix_sql="-- Recreate view from sprint23_phase1_market_conditions_table.sql",
                description="Current market conditions view for easy data access"
            ),
        ])

        # Phase 1B: Cache Tables Checks
        self.checks.extend([
            IntegrityCheck(
                name="cache_tables_exist",
                category="tables",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name IN (
                        'pattern_correlations_cache',
                        'temporal_performance_cache', 
                        'advanced_metrics_cache'
                    );
                """,
                expected_result=3,
                fix_sql="-- Run: docs/planning/sprints/sprint23/sql/sprint23_phase1_performance_indexes.sql",
                description="All three cache tables must exist for performance optimization"
            ),

            IntegrityCheck(
                name="materialized_views_exist",
                category="views",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) FROM pg_matviews 
                    WHERE matviewname IN (
                        'mv_active_patterns_summary',
                        'mv_pattern_correlation_summary'
                    );
                """,
                expected_result=2,
                fix_sql="-- Run: docs/planning/sprints/sprint23/sql/sprint23_phase1_performance_indexes.sql",
                description="Materialized views for ultra-fast analytics queries"
            ),

            IntegrityCheck(
                name="materialized_view_refresh_works",
                category="functions",
                sprint="23",
                sql_query="""
                    SELECT refresh_analytics_views();
                """,
                expected_result="Materialized views refreshed successfully",
                fix_sql="-- Run: docs/planning/sprints/sprint23/sql/sprint23_phase1_script2_fixes.sql",
                description="Materialized view refresh function must work without errors"
            ),
        ])

        # Phase 1C: Analytics Functions Checks
        self.checks.extend([
            IntegrityCheck(
                name="analytics_functions_exist",
                category="functions",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) FROM information_schema.routines 
                    WHERE routine_name IN (
                        'calculate_pattern_correlations',
                        'analyze_temporal_performance',
                        'analyze_pattern_market_context',
                        'calculate_advanced_pattern_metrics',
                        'compare_pattern_performance',
                        'generate_pattern_prediction_signals'
                    ) AND routine_type = 'FUNCTION';
                """,
                expected_result=6,
                fix_sql="-- Run corrected: docs/planning/sprints/sprint23/sql/sprint23_phase1_analytics_functions.sql",
                description="All 6 advanced analytics functions must exist"
            ),

            IntegrityCheck(
                name="cache_management_functions_exist",
                category="functions",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) FROM information_schema.routines 
                    WHERE routine_name IN (
                        'refresh_correlations_cache',
                        'refresh_temporal_cache',
                        'refresh_advanced_metrics_cache',
                        'refresh_all_analytics_cache'
                    ) AND routine_type = 'FUNCTION';
                """,
                expected_result=4,
                fix_sql="-- Run: docs/planning/sprints/sprint23/sql/sprint23_phase1_performance_indexes.sql",
                description="Cache management functions for automated refresh"
            ),
        ])

        # Performance and Index Checks
        self.checks.extend([
            IntegrityCheck(
                name="market_conditions_indexes",
                category="indexes",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) FROM pg_indexes 
                    WHERE tablename = 'market_conditions' 
                    AND indexname LIKE 'idx_market_conditions%';
                """,
                expected_result=5,
                fix_sql="-- Check and recreate indexes from sprint23_phase1_market_conditions_table.sql",
                description="Market conditions table must have performance indexes"
            ),

            IntegrityCheck(
                name="cache_table_indexes",
                category="indexes",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) >= 8 FROM pg_indexes 
                    WHERE indexname LIKE '%cache%' 
                    AND tablename IN (
                        'pattern_correlations_cache',
                        'temporal_performance_cache',
                        'advanced_metrics_cache'
                    );
                """,
                expected_result=True,  # At least 8 cache indexes required
                fix_sql="-- Recreate cache indexes from sprint23_phase1_performance_indexes.sql",
                description="Cache tables must have performance indexes (minimum 8)"
            ),
        ])

        # TimescaleDB Checks (Optional but valuable)
        self.checks.extend([
            IntegrityCheck(
                name="timescaledb_extension_available",
                category="extensions",
                sprint="23",
                sql_query="""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_available_extensions 
                        WHERE name = 'timescaledb'
                    );
                """,
                expected_result=True,
                fix_sql="-- Install TimescaleDB extension: CREATE EXTENSION IF NOT EXISTS timescaledb;",
                description="TimescaleDB extension should be available for hypertables"
            ),

            IntegrityCheck(
                name="hypertables_created",
                category="timescaledb",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) FROM _timescaledb_catalog.hypertable 
                    WHERE table_name IN (
                        'pattern_correlations_cache',
                        'temporal_performance_cache', 
                        'advanced_metrics_cache'
                    );
                """,
                expected_result=3,
                fix_sql="-- Run TimescaleDB sections from sprint23_phase1_script2_fixes.sql",
                description="Cache tables should be converted to hypertables for performance"
            ),
        ])

        # Data Validation Checks
        self.checks.extend([
            IntegrityCheck(
                name="market_conditions_sample_data",
                category="data",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) >= 5 FROM market_conditions;
                """,
                expected_result=True,
                fix_sql="-- Insert sample data from sprint23_phase1_market_conditions_table.sql",
                description="Market conditions should have sample data for testing"
            ),

            IntegrityCheck(
                name="app_readwrite_permissions",
                category="permissions",
                sprint="23",
                sql_query="""
                    SELECT COUNT(*) FROM information_schema.table_privileges 
                    WHERE grantee = 'app_readwrite' 
                    AND table_name IN ('market_conditions', 'pattern_correlations_cache')
                    AND privilege_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE');
                """,
                expected_result=8,  # 4 permissions × 2 tables minimum
                fix_sql="-- Run GRANT statements from all Sprint 23 SQL scripts",
                description="app_readwrite user must have proper permissions"
            ),
        ])

    def run_check(self, check: IntegrityCheck) -> CheckResult:
        """Execute a single integrity check"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(check.sql_query)
            result = cursor.fetchone()

            if result is None:
                actual_result = None
            elif len(result) == 1:
                actual_result = result[0]
            else:
                actual_result = result

            passed = actual_result == check.expected_result

            return CheckResult(
                check_name=check.name,
                passed=passed,
                actual_result=actual_result,
                expected_result=check.expected_result,
                fix_sql=check.fix_sql if not passed else None
            )

        except Exception as e:
            return CheckResult(
                check_name=check.name,
                passed=False,
                actual_result=None,
                expected_result=check.expected_result,
                error_message=str(e),
                fix_sql=check.fix_sql
            )

    def run_all_checks(self, sprint_filter: str | None = None) -> list[CheckResult]:
        """Run all integrity checks, optionally filtered by sprint"""
        checks_to_run = self.checks
        if sprint_filter:
            checks_to_run = [c for c in self.checks if c.sprint == sprint_filter]

        print(f"\n🔍 Running {len(checks_to_run)} integrity checks...")

        results = []
        for check in checks_to_run:
            result = self.run_check(check)
            results.append(result)

            status = "✅" if result.passed else "❌"
            print(f"{status} {check.name}: {result.actual_result}")

            if not result.passed and result.error_message:
                print(f"   Error: {result.error_message}")

        return results

    def generate_fix_report(self, results: list[CheckResult]) -> str:
        """Generate a detailed fix report"""
        failed_results = [r for r in results if not r.passed]

        if not failed_results:
            return "🎉 All integrity checks passed! Database is in perfect condition."

        report = f"""
# Database Integrity Fix Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Failed Checks: {len(failed_results)} / {len(results)}

## Issues Found

"""

        for i, result in enumerate(failed_results, 1):
            report += f"""
### {i}. {result.check_name.replace('_', ' ').title()}

**Problem**: Expected `{result.expected_result}`, got `{result.actual_result}`
"""
            if result.error_message:
                report += f"**Error**: {result.error_message}\n"

            if result.fix_sql:
                report += f"""
**Fix**:
```sql
{result.fix_sql}
```
"""

        report += """
## Recommended Actions

1. Review each failed check above
2. Execute the suggested SQL fixes in PGAdmin
3. Re-run this integrity checker to verify fixes
4. For TimescaleDB checks, ensure extension is installed

## Re-run Command
```bash
python scripts/dev_tools/util_test_db_integrity.py --sprint 23
```
"""

        return report

    def save_fix_report(self, results: list[CheckResult], filename: str):
        """Save fix report to file"""
        report = self.generate_fix_report(results)

        fix_file = Path("scripts/dev_tools") / filename
        fix_file.write_text(report, encoding='utf-8')

        print(f"\n📝 Fix report saved to: {fix_file}")
        return fix_file

def get_db_connection_params() -> dict[str, str]:
    """Get database connection parameters from TickStockAppV2 .env file"""
    # Using hardcoded values from .env DATABASE_URI
    # config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')
    return {
        'host': 'localhost',
        'port': '5432',
        'database': 'tickstock',
        'user': 'app_readwrite',
        'password': 'PASSWORD_PLACEHOLDER'
    }

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='TickStock Database Integrity Checker')
    parser.add_argument('--sprint', type=str, help='Check specific sprint (e.g., 23)')
    parser.add_argument('--all', action='store_true', help='Check all sprints')
    parser.add_argument('--generate-fixes', action='store_true', help='Generate fix report')
    parser.add_argument('--timescaledb', action='store_true', help='Include TimescaleDB checks')

    args = parser.parse_args()

    # Get database connection parameters (hardcoded from .env file)
    connection_params = get_db_connection_params()

    # Initialize checker
    checker = DatabaseIntegrityChecker(connection_params)

    # Connect to database
    if not checker.connect():
        sys.exit(1)

    try:
        # Run checks
        sprint_filter = args.sprint if args.sprint else None
        results = checker.run_all_checks(sprint_filter)

        # Print summary
        passed = len([r for r in results if r.passed])
        total = len(results)

        print(f"\n📊 Summary: {passed}/{total} checks passed")

        # Generate fix report if requested or if there are failures
        if args.generate_fixes or passed < total:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"db_integrity_report_{timestamp}.md"
            checker.save_fix_report(results, filename)

        # Exit with error code if checks failed
        sys.exit(0 if passed == total else 1)

    finally:
        checker.disconnect()

if __name__ == "__main__":
    main()
