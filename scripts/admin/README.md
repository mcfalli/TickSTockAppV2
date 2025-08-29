# Admin Scripts

This folder contains production-ready admin utilities for TickStock's role-based administration system.

## User Management Scripts

### `add_admin_system.py`
Interactive script to add role-based access control to the system and promote users to admin.
- Adds `role` column to users table
- Shows all users and lets you choose which to make admin
- Sets user as verified/active/terms accepted

### `simple_admin_setup.py` 
Quick admin setup script that automatically makes the first user in the database an admin.
- Non-interactive version of `add_admin_system.py`
- Good for automated setups or Docker containers

### `quick_admin_setup.py`
Specifically sets up `test@example.com` as an admin user.
- Hardcoded for the test user
- Used during development

### `reset_password.py`
Reset password for any user account.
- Interactive script
- Prompts for email and new password
- Updates password hash in database

### `upgrade_to_super.py` ⭐ **NEW**
Upgrade existing admin users to 'super' role for full system access.
- Shows current admin/super users
- Interactive user selection
- Upgrades admin → super for full access to both regular and admin pages
- **Recommended**: Upgrade your admin account to super for complete access

## Usage

All scripts use the DATABASE_URI from your .env file. Run them from the project root:

```bash
# Interactive admin setup
python scripts/admin/add_admin_system.py

# Quick setup for first user  
python scripts/admin/simple_admin_setup.py

# Upgrade admin to super (RECOMMENDED)
python scripts/admin/upgrade_to_super.py

# Reset a password
python scripts/admin/reset_password.py
```

## Role System Overview

| Role | Access Level | Description |
|------|-------------|-------------|
| `user` | Regular Pages | Dashboard, account, market data |
| `moderator` | Regular Pages | Future use (currently same as user) |
| `admin` | Admin Pages Only | User mgmt, historical data, health monitor |
| `super` | **Full Access** | Both regular AND admin pages |

**Recommended**: Use `upgrade_to_super.py` to convert your admin account to super for complete system access.

## Security Note

These scripts have direct database access and should only be run by authorized administrators.