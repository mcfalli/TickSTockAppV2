#!/usr/bin/env python3
"""
Simple runner for database integrity checks
==========================================

Quick way to run integrity checks with proper configuration.
"""

import sys

from db_config import get_database_config
from util_test_db_integrity import DatabaseIntegrityChecker


def main():
    """Run Sprint 23 integrity check with guided setup"""

    print("🔍 TickStockAppV2 Database Integrity Checker")
    print("=" * 50)

    # Get configuration (hardcoded from .env file)
    config = get_database_config()

    # Initialize and run checker
    checker = DatabaseIntegrityChecker(config)

    if not checker.connect():
        print("❌ Failed to connect to database. Check your configuration.")
        sys.exit(1)

    try:
        print("\n🎯 Running Sprint 23 integrity checks...")

        # Run Sprint 23 specific checks
        results = checker.run_all_checks(sprint_filter="23")

        # Summary
        passed = len([r for r in results if r.passed])
        total = len(results)

        print(f"\n📊 Results: {passed}/{total} checks passed")

        if passed < total:
            print("\n❌ Some checks failed. Generating fix report...")
            fix_file = checker.save_fix_report(results, "sprint23_fixes.md")
            print(f"📝 Review the fix report: {fix_file}")
            print("\n🔧 Next steps:")
            print("1. Apply the suggested SQL fixes in PGAdmin")
            print("2. Run this script again to verify fixes")
            print("3. Apply TimescaleDB optimizations if desired")
        else:
            print("\n✅ All checks passed! Your Sprint 23 database setup is perfect.")
            print("\n🚀 Ready for:")
            print("• Phase 2: TickStockAppV2 Backend Services")
            print("• TimescaleDB optimizations (optional)")
            print("• Phase 3: TickStockPL handoff")

        sys.exit(0 if passed == total else 1)

    except KeyboardInterrupt:
        print("\n⏹️  Check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
    finally:
        checker.disconnect()

if __name__ == "__main__":
    main()
