#!/usr/bin/env python3
"""
Fix final Unicode issues in app.py startup messages.
"""

def fix_app_unicode():
    """Remove emojis from app.py startup messages."""

    file_path = "C:/Users/McDude/TickStockAppV2/src/app.py"

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace emoji characters with ASCII equivalents
    replacements = [
        ('🚀 TICKSTOCK APPLICATION STARTING (Simplified)', '[STARTUP] TICKSTOCK APPLICATION STARTING (Simplified)'),
        ('✅ TICKSTOCK APPLICATION READY', '[SUCCESS] TICKSTOCK APPLICATION READY'),
        ('📊 Data Source:', '[INFO] Data Source:'),
        ('🔧 Redis:', '[INFO] Redis:'),
        ('🌐 SocketIO:', '[INFO] SocketIO:'),
    ]

    changes_made = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            changes_made += 1
            print(f"[OK] Replaced emoji with: {new}")

    if changes_made > 0:
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n[SUCCESS] Fixed {changes_made} Unicode issues in app.py")
    else:
        print("[INFO] No Unicode issues found or already fixed")

    return True


def main():
    """Run the fix."""
    print("=" * 60)
    print("Fixing Final Unicode Issues")
    print("=" * 60)

    if fix_app_unicode():
        print("\nAll Unicode issues resolved!")
        print("The application should now run without encoding errors.")


if __name__ == "__main__":
    main()