#!/usr/bin/env python3
"""
Cleanup and organize scripts folder
Moves test files to tests folder and archives/deletes one-time fix scripts.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Define script categories and their purposes
SCRIPT_CATEGORIES = {
    # Fix scripts - These were one-time fixes that have been applied
    "fix_scripts_completed": [
        "fix_all_unicode_issues.py",           # Unicode character fixes - COMPLETED
        "fix_app_integration_logging.py",      # Integration logging setup - COMPLETED
        "fix_duplicate_integration_logs.py",   # Duplicate log prevention - COMPLETED
        "fix_final_unicode_issues.py",         # Final Unicode cleanup - COMPLETED
        "fix_integration_syntax.py",           # Syntax fixes - COMPLETED
        "fix_pattern_event_handling.py",       # Pattern event fixes - COMPLETED
        "fix_redis_cache_serialization.py",    # Redis serialization - COMPLETED
        "fix_remaining_runtime_errors.py",     # Runtime error fixes - COMPLETED
        "fix_runtime_errors.py",               # Runtime fixes - COMPLETED
        "fix_syntax_error.py",                 # Syntax fixes - COMPLETED
        "fix_tickstockapp_errors.py",          # App error fixes - COMPLETED
        "fix_unicode_issues.py",               # Unicode fixes - COMPLETED
    ],

    # Test scripts to keep in scripts folder (integration/system tests)
    "keep_in_scripts": [
        "test_full_integration.py",            # Full system integration test - KEEP
        "test_integration_monitoring.py",      # Integration monitoring test - KEEP
        "test_system_health.py",               # System health check - KEEP
        "diagnose_integration.py",             # Integration diagnostics - KEEP
        "monitor_system_health.py",            # Health monitoring - KEEP (renamed)
        "monitor_patterns.py",                  # Pattern monitoring - KEEP
    ],

    # Test scripts to move to tests folder
    "move_to_tests": [
        "test_database_integration_logging.py",  # Database logging test
        "test_integration_logging.py",           # Integration logging test
        "test_pattern_event.py",                 # Pattern event test
        "test_pattern_event_structure.py",       # Pattern structure test
        "test_redis_integration_fix.py",         # Redis integration test
        "sprint23_test_integration.py",          # Sprint 23 specific test
    ],

    # Utility scripts to keep
    "keep_utilities": [
        "test_runner.py",                      # Test runner utility - KEEP
        "add_integration_logging.py",          # Add logging utility - KEEP
        "complete_integration_logging.py",     # Complete logging utility - KEEP
        "create_tickstockpl_instructions.py",  # Create instructions - KEEP
        "update_integration_env_config.py",    # Update config - KEEP
        "update_integration_file_logging.py",  # Update file logging - KEEP
    ]
}

def create_archive_folder():
    """Create archive folder for completed fix scripts."""
    archive_path = Path("scripts/archive_completed_fixes")
    archive_path.mkdir(exist_ok=True)

    # Create README in archive
    readme_content = f"""# Archived Fix Scripts
These scripts were one-time fixes that have been successfully applied.
Archived on: {datetime.now().strftime('%Y-%m-%d')}

These scripts fixed:
- Unicode encoding issues
- Integration logging implementation
- Pattern event handling
- Redis serialization issues
- Runtime errors
- Syntax errors

The fixes have been applied to the codebase and these scripts are kept for historical reference only.
"""

    (archive_path / "README.md").write_text(readme_content)
    return archive_path

def organize_scripts(dry_run=True):
    """Organize scripts into appropriate folders."""
    print(f"{'DRY RUN' if dry_run else 'EXECUTING'} - Script Organization")
    print("=" * 60)

    scripts_dir = Path("scripts")
    tests_dir = Path("tests/integration")
    tests_dir.mkdir(parents=True, exist_ok=True)

    archive_dir = create_archive_folder()

    actions = []

    # Process completed fix scripts
    print("\n1. ARCHIVING COMPLETED FIX SCRIPTS:")
    for script in SCRIPT_CATEGORIES["fix_scripts_completed"]:
        src = scripts_dir / script
        if src.exists():
            dst = archive_dir / script
            actions.append(("ARCHIVE", src, dst))
            print(f"  ARCHIVE: {script} -> archive_completed_fixes/")

    # Process test scripts to move
    print("\n2. MOVING TEST SCRIPTS TO TESTS FOLDER:")
    for script in SCRIPT_CATEGORIES["move_to_tests"]:
        src = scripts_dir / script
        if src.exists():
            dst = tests_dir / script
            actions.append(("MOVE", src, dst))
            print(f"  MOVE: {script} -> tests/integration/")

    # List scripts to keep
    print("\n3. KEEPING IN SCRIPTS FOLDER:")
    for script in SCRIPT_CATEGORIES["keep_in_scripts"]:
        if (scripts_dir / script).exists():
            print(f"  KEEP: {script}")

    for script in SCRIPT_CATEGORIES["keep_utilities"]:
        if (scripts_dir / script).exists():
            print(f"  KEEP: {script}")

    # Check for unknown scripts
    print("\n4. UNKNOWN SCRIPTS (review manually):")
    all_known = set()
    for category in SCRIPT_CATEGORIES.values():
        all_known.update(category)

    for script in scripts_dir.glob("*.py"):
        if script.name not in all_known and script.name != "cleanup_scripts_folder.py":
            print(f"  UNKNOWN: {script.name}")

    if not dry_run:
        print("\n" + "=" * 60)
        print("EXECUTING CLEANUP...")

        for action, src, dst in actions:
            try:
                if action == "ARCHIVE":
                    shutil.move(str(src), str(dst))
                    print(f"  Archived: {src.name}")
                elif action == "MOVE":
                    shutil.move(str(src), str(dst))
                    print(f"  Moved: {src.name} to tests/")
            except Exception as e:
                print(f"  ERROR: Failed to {action.lower()} {src.name}: {e}")

        print("\nCLEANUP COMPLETE!")

        # Summary
        remaining = list(scripts_dir.glob("*.py"))
        print(f"\nRemaining scripts in folder: {len(remaining)}")
        print("These are actively used utilities and monitoring scripts.")

    else:
        print("\n" + "=" * 60)
        print("This was a DRY RUN. No files were moved.")
        print("Run with --execute flag to perform the cleanup.")

    return actions

def main():
    """Main cleanup function."""
    import sys

    dry_run = "--execute" not in sys.argv
    auto_confirm = "--auto" in sys.argv

    print("TickStockAppV2 Scripts Folder Cleanup")
    print("=" * 60)

    if dry_run:
        print("Running in DRY RUN mode (no files will be moved)")
        print("Use '--execute' flag to perform actual cleanup\n")
    else:
        if not auto_confirm:
            try:
                response = input("This will reorganize the scripts folder. Continue? (y/n): ")
                if response.lower() != 'y':
                    print("Cleanup cancelled.")
                    return
            except EOFError:
                print("Running in automated mode, proceeding with cleanup...")
        else:
            print("Auto-confirm mode, proceeding with cleanup...")

    organize_scripts(dry_run)

    if dry_run:
        print("\nTo execute cleanup, run:")
        print("  python scripts/cleanup_scripts_folder.py --execute")

if __name__ == "__main__":
    main()