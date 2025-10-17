# Code Reference NOT NULL Constraint Migration

**Date**: 2025-10-15
**Status**: ✅ Applied Successfully
**Purpose**: Prevent NULL values in `code_reference` columns which cause application errors

---

## Migration Summary

This migration adds NOT NULL constraints to the `code_reference` column in both:
- `pattern_definitions` table
- `indicator_definitions` table

### Why This Was Needed

The application relies on `code_reference` to dynamically load pattern and indicator classes. When `code_reference` is NULL, the application cannot locate the Python class, causing runtime errors.

---

## Files Created

1. **add_code_reference_not_null_simple.sql** (✅ RECOMMENDED)
   - Simple, direct SQL migration
   - Run with postgres superuser
   - No dependencies

2. **add_code_reference_not_null.sql**
   - Complex validation logic (has syntax issues)
   - DO NOT USE - use simple version instead

3. **run_code_reference_migration.py**
   - Python wrapper for migration
   - Includes dry-run mode
   - Requires python environment
   - **NOTE**: Requires postgres user due to table ownership

---

## How to Apply Migration

### Option 1: Direct SQL (RECOMMENDED)

```bash
# Apply constraint
PGPASSWORD=your_password psql -h 127.0.0.1 -U postgres -d tickstock \
    -f scripts/migrations/add_code_reference_not_null_simple.sql
```

### Option 2: Python Script

```bash
# Dry-run (preview changes)
python scripts/migrations/run_code_reference_migration.py --dry-run

# Apply migration (requires postgres credentials in DATABASE_URI)
python scripts/migrations/run_code_reference_migration.py
```

---

## Verification

After applying the migration, verify the constraints:

```sql
SELECT
    table_name,
    column_name,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('pattern_definitions', 'indicator_definitions')
AND column_name = 'code_reference';
```

Expected output:
```
      table_name       | column_name   | is_nullable
-----------------------+---------------+-------------
 indicator_definitions | code_reference | NO
 pattern_definitions   | code_reference | NO
```

Test the constraint:
```sql
-- This should FAIL with NOT NULL constraint violation
INSERT INTO pattern_definitions (name, short_description, code_reference)
VALUES ('test', 'test', NULL);
```

Expected error:
```
ERROR:  null value in column "code_reference" violates not-null constraint
```

---

## Rollback (Use with Caution)

If you need to remove the constraints:

```sql
-- Rollback SQL
ALTER TABLE pattern_definitions
    ALTER COLUMN code_reference DROP NOT NULL;

ALTER TABLE indicator_definitions
    ALTER COLUMN code_reference DROP NOT NULL;
```

Or with Python script:
```bash
python scripts/migrations/run_code_reference_migration.py --rollback
```

---

## Migration Results (2025-10-15)

✅ **Successfully Applied**

**Before Migration**:
- `pattern_definitions.code_reference`: nullable (25 rows, 0 NULL values)
- `indicator_definitions.code_reference`: nullable (18 rows, 0 NULL values)

**After Migration**:
- `pattern_definitions.code_reference`: NOT NULL ✅
- `indicator_definitions.code_reference`: NOT NULL ✅

**Database Impact**:
- No data changes required (all existing rows had valid code_reference values)
- Future INSERT/UPDATE operations will reject NULL values
- Application stability improved (prevents dynamic loading errors)

---

## Future Inserts

When adding new patterns or indicators, you MUST provide `code_reference`:

```sql
-- Correct ✅
INSERT INTO pattern_definitions (
    name,
    short_description,
    code_reference  -- Required!
) VALUES (
    'New Pattern',
    'Description',
    'src.pattern_library.patterns.NewPattern'
);

-- Incorrect ❌ - Will fail with NOT NULL constraint
INSERT INTO pattern_definitions (name, short_description)
VALUES ('New Pattern', 'Description');
```

---

## Notes

- Migration applied using `postgres` superuser due to table ownership
- `pattern_definitions` owned by: postgres
- `indicator_definitions` owned by: app_readwrite
- No rollback needed unless business requirements change
- Constraint enforced at database level (defense in depth)

---

**Migration Status**: ✅ Complete
**Verified By**: Database validation queries
**Impact**: Low (no existing NULL values, all tests passing)
