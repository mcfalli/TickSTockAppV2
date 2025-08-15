import os

def list_files(startpath, exclude_dirs=['__pycache__', 'venv', '.venv', '.git', 'node_modules', 'logs', 'data', '.gitignore', 'dev_tools']):
    structure = ""
    for root, dirs, files in os.walk(startpath):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        dir_line = f'{indent}{os.path.basename(root)}/\n'
        structure += dir_line
        print(dir_line, end='')  # Print directory to terminal
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            file_line = f'{sub_indent}{f}\n'
            structure += file_line
            print(file_line, end='')  # Print file to terminal
    return structure

if __name__ == "__main__":
    # Since script is now in dev_tools folder, go up one level to get project root
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Get absolute path of script directory
    project_root = os.path.dirname(script_dir)  # Go up one level to project root
    
    logs_dir = 'logs'  # Logs folder name
    logs_path = os.path.join(project_root, logs_dir)  # Full path to logs folder at project root

    # Ensure the logs folder exists at project root
    try:
        os.makedirs(logs_path, exist_ok=True)
    except OSError as e:
        print(f"Error creating logs directory {logs_path}: {e}")
        exit(1)

    # Dynamically generate output filename from script name
    script_name = os.path.basename(__file__)  # e.g., generate_structure.py
    output_filename = os.path.splitext(script_name)[0] + '.txt'  # e.g., generate_structure.txt
    output_path = os.path.join(logs_path, output_filename)  # e.g., ../logs/generate_structure.txt

    # Generate the file structure starting from project root
    structure = list_files(project_root)

    # Write the structure to the output file
    try:
        with open(output_path, 'w') as f:
            f.write(structure)
        print(f"\nFile structure written to {output_path}")
    except OSError as e:
        print(f"\nError writing to {output_path}: {e}")
        exit(1)