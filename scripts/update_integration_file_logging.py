#!/usr/bin/env python3
"""
Update integration logger to support file logging to logs/ folder.
"""

import os

def update_integration_logger():
    """Update the integration logger to support file logging."""

    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/integration_logger.py"

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update the configure_integration_logging function
    old_function = """def configure_integration_logging(enabled: bool = True,
                                 log_file: bool = True,
                                 log_level: str = 'INFO'):
    \"\"\"
    Configure integration logging settings.

    Args:
        enabled: Enable/disable integration logging
        log_file: Write to separate log file
        log_level: Logging level (INFO, DEBUG, WARNING)
    \"\"\"
    flow_logger.set_enabled(enabled)

    # Set log level
    integration_logger.setLevel(getattr(logging, log_level.upper()))

    # Configure file logging
    if not log_file:
        # Remove file handler if exists
        for handler in integration_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                integration_logger.removeHandler(handler)

    return flow_logger"""

    new_function = """def configure_integration_logging(enabled: bool = True,
                                 log_file: bool = True,
                                 log_level: str = 'INFO'):
    \"\"\"
    Configure integration logging settings.

    Args:
        enabled: Enable/disable integration logging
        log_file: Write to separate log file in logs/ folder
        log_level: Logging level (INFO, DEBUG, WARNING)
    \"\"\"
    flow_logger.set_enabled(enabled)

    # Set log level
    integration_logger.setLevel(getattr(logging, log_level.upper()))

    # Configure file logging
    if log_file:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create log file with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file_path = os.path.join(logs_dir, f'integration_{timestamp}.log')

        # Remove existing file handlers
        for handler in integration_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                integration_logger.removeHandler(handler)

        # Add new file handler
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        integration_logger.addHandler(file_handler)

        integration_logger.info(f"Integration logging to file: {log_file_path}")
    else:
        # Remove file handler if exists
        for handler in integration_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                integration_logger.removeHandler(handler)

    return flow_logger"""

    if old_function in content:
        content = content.replace(old_function, new_function)

        # Also add os import at the top if not present
        if "import os" not in content:
            content = content.replace("import logging", "import logging\nimport os")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("[OK] Updated integration logger with file logging support")
        print("    - Logs will be saved to logs/integration_YYYYMMDD_HHMMSS.log")
        print("    - Set INTEGRATION_LOG_FILE=true in .env to enable")
        return True
    else:
        print("[INFO] Could not find function to update or already updated")

        # Try alternative update approach
        return update_alternative()


def update_alternative():
    """Alternative approach - add file handler configuration directly."""

    file_path = "C:/Users/McDude/TickStockAppV2/src/core/services/integration_logger.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the configure function
    for i, line in enumerate(lines):
        if "def configure_integration_logging" in line:
            # Look for the flow_logger.set_enabled line
            for j in range(i, min(i+30, len(lines))):
                if "flow_logger.set_enabled(enabled)" in lines[j]:
                    # Insert file logging code after this line
                    insert_index = j + 4  # After the setLevel line

                    file_logging_code = """
    # Configure file logging
    if log_file:
        # Create logs directory if it doesn't exist
        import os
        from datetime import datetime

        logs_dir = 'logs'
        os.makedirs(logs_dir, exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file_path = os.path.join(logs_dir, f'integration_{timestamp}.log')

        # Remove existing file handlers
        for handler in integration_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                integration_logger.removeHandler(handler)

        # Add new file handler
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        integration_logger.addHandler(file_handler)

        integration_logger.info(f"Integration logging to file: {log_file_path}")
    else:
"""
                    # Check if already has file logging
                    content = ''.join(lines)
                    if "logs_dir" not in content:
                        lines[insert_index] = lines[insert_index].replace(
                            "    # Configure file logging\n",
                            file_logging_code
                        )

                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)

                        print("[OK] Added file logging support via alternative method")
                        return True
                    else:
                        print("[INFO] File logging already configured")
                        return True

    print("[ERROR] Could not update integration logger")
    return False


def main():
    """Run the update."""
    print("=" * 60)
    print("Updating Integration Logger for File Logging")
    print("=" * 60)

    if update_integration_logger():
        print("\n[SUCCESS] Integration logger updated!")
        print("\nTo enable file logging:")
        print("  1. Set INTEGRATION_LOG_FILE=true in .env")
        print("  2. Restart the application")
        print("  3. Logs will appear in logs/integration_YYYYMMDD_HHMMSS.log")
    else:
        print("\n[WARNING] Manual update may be required")


if __name__ == "__main__":
    main()