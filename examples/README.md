# Examples

This folder contains example scripts that demonstrate various TickStock functionality, including potentially dangerous operations that should not be used in production.

## Security Examples

### `disable_auth_temp_DANGEROUS.py`
⚠️ **DANGEROUS - DO NOT USE IN PRODUCTION** ⚠️

Example script showing how to temporarily disable Flask-Login authentication for development purposes.
- Disables all `@login_required` decorators
- Makes all routes publicly accessible
- Creates security vulnerabilities
- Only for local development debugging

### `restore_auth_companion.py`
Companion script to restore authentication after using the disable script.
- Restores `@login_required` decorators
- Companion to the dangerous disable script above

## Usage

These are **example scripts only**. They demonstrate concepts but should not be used in production environments.

**Security Warning**: The auth bypass scripts create serious security vulnerabilities and should never be deployed to production servers.