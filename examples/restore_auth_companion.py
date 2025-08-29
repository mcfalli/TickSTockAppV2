#!/usr/bin/env python3
"""
Restore authentication after temporary disable
"""

import os
import shutil

app_file = 'src/app.py'
backup_file = 'src/app.py.backup'

if os.path.exists(backup_file):
    print("Restoring original app.py...")
    shutil.copy(backup_file, app_file)
    os.remove(backup_file)
    print("✅ Authentication restored")
else:
    # Fallback: manually restore @login_required
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Restore @login_required
    modified_content = content.replace('# @login_required  # TEMP DISABLED', '@login_required')
    
    with open(app_file, 'w') as f:
        f.write(modified_content)
    
    print("✅ Authentication restored (manual method)")

print("🔒 Authentication is now active again")