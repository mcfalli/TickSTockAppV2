#!/usr/bin/env python3
"""
Update integration logging configuration to use environment variables from .env
"""

import os

def update_app_to_use_env():
    """Update app.py to read integration logging config from environment."""

    app_path = "C:/Users/McDude/TickStockAppV2/src/app.py"

    # Read the file
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace the import from integration_logging file to use os.getenv
    old_code = """        # Initialize integration logging
        try:
            from src.core.services.integration_logger import configure_integration_logging
            from src.config.integration_logging import (
                INTEGRATION_LOGGING_ENABLED,
                INTEGRATION_LOG_FILE,
                INTEGRATION_LOG_LEVEL
            )

            flow_logger = configure_integration_logging(
                enabled=INTEGRATION_LOGGING_ENABLED,
                log_file=INTEGRATION_LOG_FILE,
                log_level=INTEGRATION_LOG_LEVEL
            )

            logger.info(f"STARTUP: Integration logging configured (enabled={INTEGRATION_LOGGING_ENABLED})")
        except ImportError:
            logger.warning("STARTUP: Integration logging not available")"""

    new_code = """        # Initialize integration logging from environment
        try:
            from src.core.services.integration_logger import configure_integration_logging
            import os

            # Get settings from environment variables (via .env)
            integration_enabled = os.getenv('INTEGRATION_LOGGING_ENABLED', 'true').lower() == 'true'
            integration_log_file = os.getenv('INTEGRATION_LOG_FILE', 'false').lower() == 'true'
            integration_log_level = os.getenv('INTEGRATION_LOG_LEVEL', 'INFO')

            flow_logger = configure_integration_logging(
                enabled=integration_enabled,
                log_file=integration_log_file,
                log_level=integration_log_level
            )

            logger.info(f"STARTUP: Integration logging configured (enabled={integration_enabled})")
        except ImportError:
            logger.warning("STARTUP: Integration logging not available")"""

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[OK] Updated app.py to use environment variables")
    else:
        print("[INFO] app.py already updated or pattern not found")

    return True


def update_config_manager():
    """Update config_manager.py to include integration logging defaults."""

    config_path = "C:/Users/McDude/TickStockAppV2/src/core/services/config_manager.py"

    # Read the file
    with open(config_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find where to add the integration logging config
    insert_index = None
    for i, line in enumerate(lines):
        if "'LOG_FILE_PRODUCTION_MODE': False," in line:
            insert_index = i + 1
            break

    if insert_index:
        # Check if already added
        content = ''.join(lines)
        if 'INTEGRATION_LOGGING_ENABLED' not in content:
            integration_lines = [
                "\n",
                "        # Integration Logging Configuration\n",
                "        'INTEGRATION_LOGGING_ENABLED': True,\n",
                "        'INTEGRATION_LOG_FILE': False,\n",
                "        'INTEGRATION_LOG_LEVEL': 'INFO',\n",
            ]

            for j, new_line in enumerate(integration_lines):
                lines.insert(insert_index + j, new_line)

            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            print("[OK] Updated config_manager.py with integration logging defaults")
        else:
            print("[INFO] config_manager.py already has integration logging config")
    else:
        print("[ERROR] Could not find insertion point in config_manager.py")

    return True


def verify_env_file():
    """Verify .env file has integration logging settings."""

    env_path = "C:/Users/McDude/TickStockAppV2/.env"

    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'INTEGRATION_LOGGING_ENABLED' in content:
        print("[OK] .env file has integration logging configuration")
        return True
    else:
        print("[ERROR] .env file missing integration logging configuration")
        return False


def main():
    """Update all configuration files."""
    print("=" * 60)
    print("Updating Integration Logging to use .env configuration")
    print("=" * 60)

    # Verify .env has the settings
    if not verify_env_file():
        print("\nPlease add these lines to your .env file:")
        print("INTEGRATION_LOGGING_ENABLED=true")
        print("INTEGRATION_LOG_FILE=false")
        print("INTEGRATION_LOG_LEVEL=INFO")
        return

    # Update app.py
    update_app_to_use_env()

    # Update config_manager.py
    update_config_manager()

    print("\n" + "=" * 60)
    print("[SUCCESS] Configuration updated to use environment variables!")
    print("=" * 60)
    print("\nIntegration logging can now be toggled via .env file:")
    print("  INTEGRATION_LOGGING_ENABLED=true/false")
    print("\nNo need to restart the app - just update .env and restart.")


if __name__ == "__main__":
    main()