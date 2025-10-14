import os


def list_files(startpath, exclude_dirs=None, include_hidden=False):
    """
    List all folders and files starting from startpath, excluding specified directories.
    Only includes subdirectories and their contents, skipping root-level files.
    
    Args:
        startpath (str): The root directory to start listing from.
        exclude_dirs (list): List of directory names to exclude (default: None).
        include_hidden (bool): Whether to include hidden files/directories (default: False).
    
    Returns:
        str: The formatted directory structure as a string.
    """
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', 'venv', '.venv', '.git', 'node_modules', 'docs', 'tasks', 'scripts', 'docker', 'logs', 'migrations', '.claude', '.claude-code-docs', 'htmlcov', 'requirements' 'tasks']

    structure = f"{os.path.basename(startpath)}/\n"
    print(structure, end='')  # Print root directory to terminal

    try:
        for root, dirs, files in os.walk(startpath, onerror=lambda err: print(f"Error accessing {err.filename}: {err}")):
            # Skip the root directory's files
            if root == startpath:
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in exclude_dirs] if not include_hidden else [d for d in dirs if d not in exclude_dirs]
                continue

            # Filter directories
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in exclude_dirs]
            else:
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

            # Calculate indentation level
            rel_path = os.path.relpath(root, startpath)
            level = rel_path.count(os.sep)
            indent = ' ' * 4 * level

            # Print and store directory
            dir_name = os.path.basename(root)
            dir_line = f'{indent}{dir_name}/\n'
            structure += dir_line
            print(dir_line, end='')  # Print directory to terminal

            # Filter files
            if not include_hidden:
                files = [f for f in files if not f.startswith('.')]

            # Print and store files
            sub_indent = ' ' * 4 * (level + 1)
            for f in sorted(files):  # Sort files for consistent output
                file_line = f'{sub_indent}{f}\n'
                structure += file_line
                print(file_line, end='')  # Print file to terminal

    except Exception as e:
        print(f"Error traversing directory {startpath}: {e}")
        return structure

    return structure

if __name__ == "__main__":
    # Define the project root explicitly
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    # Define logs directory at project root
    logs_dir = 'docs'
    logs_path = os.path.join(project_root, logs_dir)

    # Ensure the logs folder exists
    try:
        os.makedirs(logs_path, exist_ok=True)
    except OSError as e:
        print(f"Error creating logs directory {logs_path}: {e}")
        exit(1)

    # Generate output filename
    script_name = os.path.basename(__file__)
    #output_filename = os.path.splitext(script_name)[0] + '.md'
    output_filename = os.path.splitext('project_structure')[0] + '.md'
    output_path = os.path.join(logs_path, output_filename)

    # Generate the file structure
    structure = list_files(project_root, include_hidden=False)

    # Write the structure to the output file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(structure)
        print(f"\nFile structure written to {output_path}")
    except OSError as e:
        print(f"\nError writing to {output_path}: {e}")
        exit(1)
