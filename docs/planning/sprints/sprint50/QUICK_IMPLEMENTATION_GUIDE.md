# Sprint 50: Quick Implementation Guide

**Massive → Massive Rebrand - Fast Track**

## Pre-Flight Checklist

```bash
# 1. Create feature branch
git checkout -b feature/sprint50-polygon-to-massive

# 2. Run current tests (baseline)
python run_tests.py

# 3. Catalog all references
rg -i "polygon" --stats > sprint50_baseline.txt
```

## Step-by-Step Execution

### Step 1: Rename Directory Structure (5 min)

```bash
# Rename core directory
git mv src/infrastructure/data_sources/polygon src/infrastructure/data_sources/massive

# Rename WebSocket client
git mv src/presentation/websocket/polygon_client.py src/presentation/websocket/massive_client.py

# Rename test scripts
git mv scripts/dev_tools/test_polygon_api_check.py scripts/dev_tools/test_massive_api_check.py
git mv scripts/dev_tools/test_polygon_comprehensive_api_config.py scripts/dev_tools/test_massive_comprehensive_api_config.py
```

### Step 2: Global Find & Replace (30 min)

**CRITICAL: Do these in ORDER to prevent cascading errors**

```bash
# Class names
rg -l "MassiveProvider" | xargs sed -i 's/MassiveProvider/MassiveProvider/g'
rg -l "MassiveAPI" | xargs sed -i 's/MassiveAPI/MassiveAPI/g'
rg -l "MassiveClient" | xargs sed -i 's/MassiveClient/MassiveClient/g'

# Import statements
rg -l "from.*polygon" | xargs sed -i 's/from.*polygon/from massive/g'
rg -l "import.*polygon" | xargs sed -i 's/import polygon/import massive/g'

# Environment variables
rg -l "POLYGON_API" | xargs sed -i 's/MASSIVE_API_KEY/MASSIVE_API_KEY/g'
rg -l "POLYGON_API" | xargs sed -i 's/MASSIVE_API_URL/MASSIVE_API_URL/g'
rg -l "POLYGON_WEBSOCKET" | xargs sed -i 's/MASSIVE_WEBSOCKET_URL/MASSIVE_WEBSOCKET_URL/g'

# Function names
rg -l "polygon_" | xargs sed -i 's/polygon_/massive_/g'

# String literals (manual review recommended)
rg -l '"polygon"' | xargs sed -i 's/"polygon"/"massive"/g'
rg -l "'polygon'" | xargs sed -i "s/'polygon'/'massive'/g"

# Comments and docstrings
rg -l "Massive" | xargs sed -i 's/Massive\.io/Massive.com/g'
rg -l "Massive" | xargs sed -i 's/Massive API/Massive API/g'
```

### Step 3: Configuration Updates (10 min)

**Update `.env.example`:**
```bash
# Replace all environment variables
sed -i 's/POLYGON_/MASSIVE_/g' .env.example
```

**Update `src/core/services/config_manager.py`:**
Add backward compatibility method:
```python
def get_massive_api_key(self):
    """Get Massive API key with backward compatibility."""
    return os.getenv('MASSIVE_API_KEY') or os.getenv('MASSIVE_API_KEY')

def get_massive_api_url(self):
    """Get Massive API URL with backward compatibility."""
    return os.getenv('MASSIVE_API_URL') or os.getenv('MASSIVE_API_URL', 'https://api.massive.com')
```

### Step 4: Test Updates (20 min)

```bash
# Update test fixtures
sed -i 's/polygon/massive/g' tests/conftest.py
sed -i 's/polygon/massive/g' tests/fixtures/market_data_fixtures.py

# Update test class names
rg -l "TestMassive" tests/ | xargs sed -i 's/TestMassive/TestMassive/g'

# Update test function names
rg -l "test_polygon" tests/ | xargs sed -i 's/test_polygon/test_massive/g'
```

### Step 5: Documentation Updates (30 min)

**Core files to manually review and update:**
1. `CLAUDE.md` - Update all references
2. `README.md` - Update provider references
3. `docs/guides/configuration.md` - Update env var examples
4. `docs/guides/quickstart.md` - Update setup instructions
5. `docs/api/endpoints.md` - Update API response examples

**Architecture docs:**
```bash
# Bulk update in docs
find docs/ -name "*.md" -not -path "*/sprint_history/*" -exec sed -i 's/Massive\.io/Massive.com/g' {} +
find docs/ -name "*.md" -not -path "*/sprint_history/*" -exec sed -i 's/Massive API/Massive API/g' {} +
```

**Sprint history (add context notes only):**
Add note to relevant sprint documents:
```markdown
> **Historical Note**: This document references "Massive.com", which rebranded to "Massive.com" in January 2025 (Sprint 50). The original naming is preserved for historical accuracy.
```

### Step 6: Validation (30 min)

```bash
# 1. Syntax check
ruff check . --fix

# 2. Search for remaining references
rg -i "polygon" src/ tests/ --ignore-case
# Expected: Only historical comments/docstrings if any

# 3. Run unit tests
pytest tests/data_source/unit/ -v

# 4. Run integration tests (CRITICAL)
python run_tests.py
# Expected: 2 tests passing, ~30 seconds

# 5. Manual service check
python start_all_services.py
# Verify: Services start without errors
```

### Step 7: Commit & Review (15 min)

```bash
# Stage changes
git add -A

# Create commit
git commit -m "refactor: Rebrand Massive to Massive across codebase

- Rename src/infrastructure/data_sources/polygon/ to massive/
- Update all class names (Provider, API, Client)
- Update environment variables (POLYGON_* to MASSIVE_*)
- Update configuration with backward compatibility
- Update all tests and fixtures
- Update documentation and guides
- Add context notes to sprint history

Refs: Sprint 50
See: https://massive.com/blog/polygon-is-now-massive"

# Push for review
git push origin feature/sprint50-polygon-to-massive
```

## Quick Validation Checklist

Before marking sprint complete:

- [ ] `rg -i "polygon" src/` returns ZERO active code hits
- [ ] `python run_tests.py` passes (2 tests, ~30s)
- [ ] Services start: `python start_all_services.py` works
- [ ] UI shows "Massive" (check admin dashboard)
- [ ] Configuration loads without errors
- [ ] Git commit follows standards (no "Generated by Claude")

## Rollback Command (If Needed)

```bash
# Emergency rollback
git reset --hard origin/main
git checkout main
```

## Expected Completion Time

- **Minimum**: 2 hours (experienced developer, no issues)
- **Typical**: 3-4 hours (includes testing and validation)
- **Maximum**: 8 hours (includes documentation deep review)

## Common Pitfalls

1. **Don't forget backward compatibility** in config_manager.py
2. **Don't rewrite sprint history** - add notes only
3. **Don't skip integration tests** - MANDATORY validation
4. **Don't bulk replace in binary files** - only text files
5. **Don't commit with AI attribution** - clean commit messages

## Files Requiring Manual Review

These files may need careful manual updates:

1. `src/core/services/config_manager.py` - Add fallback logic
2. `src/core/services/market_data_service.py` - Verify logger messages
3. `config/logging_config.py` - Check log format strings
4. `web/templates/admin/historical_data_dashboard.html` - UI labels
5. `src/api/rest/admin_historical_data.py` - API response field names

## Post-Completion

1. Create `SPRINT50_COMPLETE.md` using POST_SPRINT_CHECKLIST.md
2. Update CLAUDE.md with sprint completion
3. Notify team of environment variable changes
4. Update deployment documentation

---

**Quick Start**: `git checkout -b feature/sprint50-polygon-to-massive && rg -i "polygon" --stats`

**Reference**: Full details in `sprint50_polygon_to_massive_rebrand.md`
