# Generate Project Structure Command

## Command
```bash
python ./scripts/dev_tools/util_proj_gen_structure_detailed.py
```

## Description
Generates a comprehensive markdown file documenting the TickStock project structure with focus on technical architecture and data flow.

## Output Location
The script will generate output in: `docs/new/project_structure.md`

## What It Does
- Scans the entire project directory structure
- Analyzes Python files using AST parsing to extract:
  - Classes and their methods
  - Functions and their signatures
  - Import dependencies
  - Architectural components
- Categorizes components by type:
  - Real-time pipeline components
  - WebSocket layer
  - Data providers
  - Event detectors
  - Universe managers
  - Analytics services
  - Database models
- Generates detailed documentation including:
  - Project overview
  - Architectural components inventory
  - Data flow diagrams
  - Configuration section
  - Dependency matrix
  - Quick reference index

## Files Ignored
The script automatically excludes:
- `venv`, `__pycache__`, `.git`
- `migrations`, `logs`, `docs`
- `build`, `dist`
- `static`, `templates`
- `web`
- Test files (matching `test_*.py`)
- Utility files (matching `util_*.py`)

## Alternative Commands

### For Basic Structure (less detailed)
```bash
python ./scripts/dev_tools/util_proj_gen_structure.py
```

### For Documentation-Focused Structure
```bash
python ./scripts/dev_tools/util_proj_gen_structure_docs.py
```

## Usage in Development
When you need to:
- Review the current project architecture
- Generate updated documentation after structural changes
- Analyze component dependencies
- Create a quick reference for the development team
- Document the data flow pipeline

Simply run: `/generate_project_structure`