#!/usr/bin/env python3
"""
Properly add integration logging to app.py without breaking syntax.
"""

import os

def fix_app_integration_logging():
    """Fix the app.py integration logging initialization."""

    file_path = "C:/Users/McDude/TickStockAppV2/src/app.py"

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the line with 'logger.error("STARTUP: LOGIN-MANAGER not found in extensions!")'
    insert_index = None
    for i, line in enumerate(lines):
        if 'logger.error("STARTUP: LOGIN-MANAGER not found in extensions!")' in line:
            insert_index = i + 1
            break

    if insert_index is None:
        print("[ERROR] Could not find insertion point in app.py")
        return False

    # Integration logging code to insert
    integration_code = [
        "\n",
        "        # Initialize integration logging\n",
        "        try:\n",
        "            from src.core.services.integration_logger import configure_integration_logging\n",
        "            from src.config.integration_logging import (\n",
        "                INTEGRATION_LOGGING_ENABLED,\n",
        "                INTEGRATION_LOG_FILE,\n",
        "                INTEGRATION_LOG_LEVEL\n",
        "            )\n",
        "\n",
        "            flow_logger = configure_integration_logging(\n",
        "                enabled=INTEGRATION_LOGGING_ENABLED,\n",
        "                log_file=INTEGRATION_LOG_FILE,\n",
        "                log_level=INTEGRATION_LOG_LEVEL\n",
        "            )\n",
        "\n",
        "            logger.info(f\"STARTUP: Integration logging configured (enabled={INTEGRATION_LOGGING_ENABLED})\")\n",
        "        except ImportError:\n",
        "            logger.warning(\"STARTUP: Integration logging not available\")\n",
    ]

    # Check if integration logging is already there
    content = ''.join(lines)
    if 'Integration logging configured' in content:
        print("[OK] Integration logging already in app.py")
        return True

    # Insert the code
    for i, code_line in enumerate(integration_code):
        lines.insert(insert_index + i, code_line)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print("[OK] Added integration logging to app.py")
    return True

if __name__ == "__main__":
    fix_app_integration_logging()