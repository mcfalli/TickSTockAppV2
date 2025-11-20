# Sprint 50: Polygon → Massive Rebrand

**Priority**: MEDIUM
**Duration**: 1-2 days
**Status**: Planning
**Prerequisites**: None

## Sprint Objectives

Polygon.io has rebranded to Massive.com (announced January 2025). This sprint systematically renames all references throughout the TickStockAppV2 codebase to reflect the new branding while maintaining backward compatibility where necessary and ensuring zero functional regression.

**Goals:**
1. Update all code references from `polygon` to `massive` (classes, modules, variables)
2. Update all documentation and comments
3. Update configuration references and environment variables
4. Maintain backward compatibility for external integrations (if needed)
5. Ensure zero functional regression through comprehensive testing

**Reference**: https://massive.com/blog/polygon-is-now-massive

## Affected Components Analysis

### Critical File Categories

**100+ files identified containing "polygon" references:**

#### 1. Core Infrastructure (`src/infrastructure/data_sources/polygon/`)
- `src/infrastructure/data_sources/polygon/__init__.py`
- `src/infrastructure/data_sources/polygon/provider.py`
- `src/infrastructure/data_sources/polygon/api.py`
- `src/infrastructure/data_sources/factory.py`
- `src/infrastructure/data_sources/adapters/realtime_adapter.py`

**Action**: Rename directory to `src/infrastructure/data_sources/massive/`

#### 2. WebSocket Client
- `src/presentation/websocket/polygon_client.py`

**Action**: Rename to `massive_client.py`, update class names

#### 3. Configuration & Services
- `src/core/services/config_manager.py`
- `src/core/services/market_data_service.py`
- `config/logging_config.py`
- `.env.example`

**Action**: Update configuration keys, maintain backward compatibility

#### 4. Jobs & Schedulers
- `src/jobs/enterprise_production_scheduler.py`
- `src/jobs/historical_data_scheduler.py`

**Action**: Update class/function references

#### 5. Data Processing
- `src/data/etf_universe_manager.py`
- `src/data/historical_loader.py`
- `src/data/eod_processor.py`
- `src/data/bulk_universe_seeder.py`

**Action**: Update provider references

#### 6. Domain Models
- `src/core/domain/market/tick.py`
- `src/shared/types/frequency.py`

**Action**: Update documentation and comments

#### 7. API Endpoints
- `src/api/rest/admin_historical_data.py`
- `web/templates/admin/historical_data_dashboard.html`

**Action**: Update UI labels and API response fields

#### 8. Tests (50+ test files)
- All files in `tests/` referencing polygon
- Test fixtures in `tests/fixtures/market_data_fixtures.py`
- `tests/conftest.py`

**Action**: Update test names, assertions, and mock data

#### 9. Documentation (30+ files)
- `docs/architecture/README.md`
- `docs/guides/configuration.md`
- `docs/guides/quickstart.md`
- `docs/api/endpoints.md`
- Sprint history documents
- `CLAUDE.md`
- `README.md`

**Action**: Update all narrative references

#### 10. Development Scripts
- `scripts/dev_tools/test_polygon_api_check.py`
- `scripts/dev_tools/test_polygon_comprehensive_api_config.py`
- `scripts/dev_tools/test_etf_historical_loader.py`

**Action**: Rename scripts and update internal references

## Implementation Strategy

### Phase 1: Preparation & Analysis (1 hour)

1. **Create Backup Branch**
   ```bash
   git checkout -b feature/sprint50-polygon-to-massive
   ```

2. **Comprehensive Search Analysis**
   ```bash
   # Find all case variations
   rg -i "polygon" --stats > sprint50_polygon_references.txt
   rg "POLYGON" --stats >> sprint50_polygon_references.txt
   rg "Polygon" --stats >> sprint50_polygon_references.txt

   # Identify patterns
   rg -i "polygon" -t py --no-heading -o > sprint50_patterns.txt
   ```

3. **Identify External Dependencies**
   - Check if any external systems reference "polygon" in API calls
   - Verify environment variable usage across deployments
   - Document any third-party integrations

### Phase 2: Code Refactoring (2-3 hours)

**Order of Operations (Dependency-Aware):**

1. **Step 1: Rename Core Directory Structure**
   ```bash
   # Rename polygon directory to massive
   git mv src/infrastructure/data_sources/polygon src/infrastructure/data_sources/massive
   ```

2. **Step 2: Update Module Imports**
   - Update all `from ...polygon...` imports to `...massive...`
   - Update all `import ...polygon...` statements
   - Files to update: All Python files importing from the renamed directory

3. **Step 3: Rename Core Classes & Functions**
   - `PolygonProvider` → `MassiveProvider`
   - `PolygonAPI` → `MassiveAPI`
   - `PolygonClient` → `MassiveClient`
   - `polygon_client.py` → `massive_client.py`
   - All function names containing `polygon` → `massive`

4. **Step 4: Update Configuration Keys**

   **Environment Variables** (`.env.example`):
   ```bash
   # NEW (preferred)
   MASSIVE_API_KEY=your_api_key
   MASSIVE_API_URL=https://api.massive.com
   MASSIVE_WEBSOCKET_URL=wss://socket.massive.com

   # DEPRECATED (backward compatibility - optional)
   POLYGON_API_KEY=${MASSIVE_API_KEY}
   POLYGON_API_URL=${MASSIVE_API_URL}
   ```

   **Config Manager** (`src/core/services/config_manager.py`):
   ```python
   # Add fallback logic
   def get_massive_api_key(self):
       """Get Massive API key with backward compatibility."""
       return os.getenv('MASSIVE_API_KEY') or os.getenv('POLYGON_API_KEY')
   ```

5. **Step 5: Update String Literals**
   - Log messages
   - Error messages
   - UI labels
   - Documentation strings

6. **Step 6: Update Test Files**
   - Rename test classes
   - Update test file names (if appropriate)
   - Update assertions and mock names
   - Update test fixtures

### Phase 3: Documentation Updates (1 hour)

1. **Update Core Documentation**
   - `CLAUDE.md` (5 references)
   - `README.md` (multiple references)
   - `docs/guides/configuration.md`
   - `docs/guides/quickstart.md`
   - `docs/api/endpoints.md`

2. **Update Architecture Documentation**
   - `docs/architecture/README.md`
   - `docs/architecture/configuration.md`
   - `docs/architecture/websockets-integration.md`

3. **Update Sprint History**
   - Add note to affected sprint documents explaining historical context
   - **Do NOT rewrite history** - just add clarification notes

4. **Update Development Scripts**
   - Rename `test_polygon_*.py` scripts
   - Update script internal logic

### Phase 4: Testing & Validation (1-2 hours)

1. **Syntax Validation**
   ```bash
   ruff check . --fix
   ```

2. **Unit Tests**
   ```bash
   pytest tests/data_source/unit/test_data_providers.py -v
   pytest tests/fixtures/ -v
   ```

3. **Integration Tests**
   ```bash
   python run_tests.py
   ```

4. **Manual Verification Checklist**
   - [ ] WebSocket connection establishes successfully
   - [ ] Historical data load works
   - [ ] Real-time tick processing functional
   - [ ] Configuration loads without errors
   - [ ] No "polygon" references in error logs
   - [ ] UI displays "Massive" branding correctly

5. **Regression Testing**
   - Run full test suite: `pytest tests/`
   - Verify no new failures introduced
   - Check performance benchmarks unchanged

## Backward Compatibility Strategy

### Option A: Full Cut-Over (Recommended)
- Complete rename with no backward compatibility
- Update deployment configurations simultaneously
- Clean break, simpler codebase

### Option B: Deprecation Period (If External Dependencies Exist)
- Support both `POLYGON_*` and `MASSIVE_*` environment variables for 1 sprint
- Log deprecation warnings when old variables used
- Remove in Sprint 51

**Decision Point**: Determine if any external systems depend on "polygon" naming

## Risk Mitigation

### Technical Risks

1. **Risk**: Missed references cause runtime errors
   - **Mitigation**: Comprehensive regex search with multiple case variations
   - **Validation**: Run integration tests multiple times

2. **Risk**: Configuration deployment mismatch
   - **Mitigation**: Update `.env.example` and deployment docs simultaneously
   - **Validation**: Test with fresh environment setup

3. **Risk**: External API calls reference old naming
   - **Mitigation**: Search for all API endpoint strings
   - **Validation**: Monitor production logs for errors

4. **Risk**: Test fixtures break due to renamed mocks
   - **Mitigation**: Update conftest.py and all fixtures first
   - **Validation**: Run test suite after each phase

### User Experience Risks

1. **Risk**: Confusion about "Polygon" vs "Massive" in UI
   - **Mitigation**: Update all UI labels consistently
   - **Validation**: Visual review of all admin pages

2. **Risk**: Documentation references outdated naming
   - **Mitigation**: Search all markdown files
   - **Validation**: Documentation review pass

## Implementation Timeline

### Day 1: Core Code Refactoring (4-5 hours)

**Morning (2-3 hours):**
1. **Hour 1**: Preparation & search analysis
2. **Hour 2**: Rename directory structure and core classes
3. **Hour 3**: Update imports and configuration

**Afternoon (2 hours):**
4. **Hour 4**: Update tests and fixtures
5. **Hour 5**: Run test suite and fix errors

### Day 2: Documentation & Validation (2-3 hours)

**Morning (1-2 hours):**
1. **Hour 1**: Update all documentation
2. **Hour 2**: Update development scripts

**Afternoon (1 hour):**
3. **Hour 3**: Final validation and integration testing

## Success Criteria

- [ ] **Zero "polygon" references in code**: All active code uses "massive" naming
- [ ] **Zero "Polygon" references in UI**: All user-facing text updated
- [ ] **All tests passing**: `python run_tests.py` completes successfully
- [ ] **Documentation updated**: No outdated references remain
- [ ] **Configuration migrated**: `.env.example` and config files updated
- [ ] **Backward compatibility working** (if Option B chosen)
- [ ] **No functional regression**: All features work identically

## Testing Strategy

### Automated Testing
```bash
# Full test suite
pytest tests/ -v

# Integration tests (MANDATORY)
python run_tests.py

# Specific data provider tests
pytest tests/data_source/ -v

# WebSocket tests
pytest tests/integration/test_streaming_phase5.py -v
```

### Manual Testing Checklist
1. Start all services: `python start_all_services.py`
2. Verify WebSocket connection in UI
3. Trigger historical data load
4. Monitor logs for any "polygon" references
5. Check admin dashboard displays "Massive" correctly
6. Verify configuration loads from `MASSIVE_API_KEY`

## Post-Sprint Actions

1. **Update Deployment Configuration**
   - Update production `.env` files
   - Update Docker configurations
   - Update CI/CD environment variables

2. **Notify Stakeholders**
   - Internal team notification about rebrand
   - Update any external documentation/APIs

3. **Monitor Production**
   - Watch for configuration errors
   - Monitor API call success rates
   - Check for unexpected "polygon" errors in logs

## Rollback Plan

If critical issues arise:
1. **Immediate**: Revert to previous commit
2. **Short-term**: Add backward compatibility layer
3. **Long-term**: Debug specific issue and re-apply rename

**Rollback Command**:
```bash
git revert HEAD
# or
git checkout main
```

## Definition of Done

Sprint 50 is considered **DONE** when:

1. **All code references updated** from "polygon" to "massive"
2. **All tests passing** (`python run_tests.py` success)
3. **Documentation complete** with no outdated references
4. **Functional equivalence verified** - no feature regression
5. **Configuration deployed** to all environments
6. **Code merged to main** with proper commit message

**Acceptance Criteria**:
A developer new to the codebase should find zero references to "Polygon" in active code/documentation (excluding historical sprint documents for archival purposes), and all market data functionality should work identically to pre-rename state.

---

**Sprint Start Date**: TBD
**Sprint End Date**: TBD
**Assigned To**: TBD

See `sprint50_definition_of_done.md` for detailed validation checklist.
