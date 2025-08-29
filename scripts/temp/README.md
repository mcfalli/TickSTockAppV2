# Temporary Development Scripts

This folder contains temporary scripts created during development and debugging sessions.

## Contents

### `debug_routes.py`
Debug script for testing Flask route registration.
- Used to troubleshoot route registration issues
- Can be deleted after development

### `test_login_*.py`
Various test scripts for debugging Flask-Login configuration.
- `test_login_config.py` - Tests Flask-Login setup
- `test_login_route.py` - Tests login route accessibility
- Used during authentication troubleshooting

### `test_environment.py`
Environment and dependency testing script.

### `test_phase10_validation.py`
Sprint 10 phase validation testing.

## Cleanup

These scripts can be safely deleted once development is complete. They were created for specific debugging sessions and are not part of the production system.

To clean up:
```bash
rm -rf scripts/temp/
```