#!/usr/bin/env python3
"""
TEMPORARY: Disable authentication for testing admin interface
⚠️  DO NOT USE IN PRODUCTION - SECURITY RISK
"""

import os
import sys

# Backup the current app.py
import shutil
app_file = 'src/app.py'
backup_file = 'src/app.py.backup'

print("Creating backup of app.py...")
shutil.copy(app_file, backup_file)

# Read the current app.py
with open(app_file, 'r') as f:
    content = f.read()

# Replace @login_required with a comment
modified_content = content.replace('@login_required', '# @login_required  # TEMP DISABLED')

# Write the modified version
with open(app_file, 'w') as f:
    f.write(modified_content)

print("✅ Authentication temporarily disabled")
print("⚠️  ALL ROUTES ARE NOW PUBLIC - DO NOT USE IN PRODUCTION")
print("🔧 Start your Flask app and visit: http://localhost:5000/admin/historical-data")
print("")
print("To restore authentication:")
print("  python restore_auth.py")