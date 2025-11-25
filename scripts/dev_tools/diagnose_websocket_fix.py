"""
Diagnostic script to verify the admin WebSocket fix was applied correctly.
Run this to check if the null-safety code is in place.
"""

import sys

# Read the admin_websockets.py file
with open('src/api/rest/admin_websockets.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check for the fix markers
checks = {
    'Null check for market_service': 'if market_service is not None:',
    'AttributeError handler': 'except AttributeError:',
    'Default connection_id': 'tick["connection_id"] = "connection_1"',
    'Debug logging for null service': 'market_service not initialized',
    'Metrics null check': 'if market_service is None:',
    'Metrics skip continue': 'skipping metrics broadcast',
}

print("=" * 70)
print("ADMIN WEBSOCKET FIX DIAGNOSTIC")
print("=" * 70)
print()

all_checks_passed = True

for check_name, check_string in checks.items():
    if check_string in content:
        print(f"✅ {check_name}: FOUND")
    else:
        print(f"❌ {check_name}: MISSING")
        all_checks_passed = False

print()
print("=" * 70)

if all_checks_passed:
    print("✅ ALL CHECKS PASSED - Fix is correctly applied in the code")
    print()
    print("If you're still seeing errors:")
    print("  1. Make sure you restarted TickStockAppV2")
    print("  2. Check you're running from the correct directory")
    print("  3. Verify no cached .pyc files (delete __pycache__ folders)")
else:
    print("❌ SOME CHECKS FAILED - Fix may not be fully applied")
    print()
    print("This should not happen. Please:")
    print("  1. Check if file was saved correctly")
    print("  2. Verify you're in the right directory")
    print("  3. Re-apply the fix")

print("=" * 70)
