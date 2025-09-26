# TickStockPL Database Connection Issue

**Date**: 2025-09-26
**Sprint**: 33 Phase 4
**Issue**: API Server startup failure
**Error**: `psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: fe_sendauth: no password supplied`

## Problem Description

The TickStockPL HTTP API server (`start_api_server.py`) is starting but immediately crashing with a database authentication error. The error indicates that no password is being supplied to PostgreSQL, even though the `.env` file contains the correct `DATABASE_URI`.

## Current Configuration

**TickStockPL `.env` file contains:**
```bash
DATABASE_URI=postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock
```

This URI format should include the password (`LJI48rUEkUpe6e`), but the error suggests it's not being parsed or passed correctly.

## Suggested Investigation Steps

### 1. Environment Loading Issue
**Check if `.env` file is being loaded:**
- Verify that `python-dotenv` is installed: `pip list | grep dotenv`
- Ensure the API server code calls `load_dotenv()` before accessing environment variables
- Check if the `.env` file path is correct relative to where the script runs

### 2. Database Connection Code Review
**Examine how DATABASE_URI is being used:**
```python
# Look for code like this in the API server:
import os
database_uri = os.getenv('DATABASE_URI')  # This might be None

# Or check if using a config manager:
from some_config import get_database_uri
```

### 3. URI Parsing Issue
**The URI format should be parsed correctly:**
```python
# Expected format:
postgresql://username:password@host:port/database
postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock

# Common parsing issues:
- Special characters in password not URL-encoded
- Colon/at-symbol parsing errors
- Missing parts of the connection string
```

## Suggested Fixes

### Option 1: Debug Environment Loading
Add debug logging to the API server startup:
```python
import os
from dotenv import load_dotenv

# Explicit .env loading
load_dotenv()

# Debug logging
database_uri = os.getenv('DATABASE_URI')
print(f"DEBUG: DATABASE_URI = {database_uri}")

if not database_uri:
    print("ERROR: DATABASE_URI not found in environment")
    exit(1)
```

### Option 2: Verify psycopg2 Connection
Test the connection string manually:
```python
import psycopg2

# Test connection directly
try:
    conn = psycopg2.connect(
        "postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock"
    )
    print("Database connection successful")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
```

### Option 3: Use Individual Connection Parameters
Instead of URI parsing, use individual parameters:
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="tickstock",
    user="app_readwrite",
    password="LJI48rUEkUpe6e"
)
```

### Option 4: Check Working Directory
Ensure the API server runs from the correct directory where `.env` exists:
```bash
cd /path/to/TickStockPL
python start_api_server.py
```

## Quick Test Commands

### Test 1: Environment Variables
```bash
cd C:/Users/McDude/TickStockPL
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DATABASE_URI:', os.getenv('DATABASE_URI'))"
```

### Test 2: Direct Database Connection
```bash
cd C:/Users/McDude/TickStockPL
python -c "import psycopg2; psycopg2.connect('postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock')"
```

### Test 3: Check Dependencies
```bash
pip list | grep -E "(psycopg2|dotenv|aiohttp)"
```

## Expected Outcome

After fixing the environment loading issue, the API server should:
1. Start successfully on `http://localhost:8080`
2. Respond to health checks: `curl http://localhost:8080/health`
3. Accept API calls from TickStockAppV2
4. Publish Redis events during processing

## Integration Impact

**This is the last blocker for Sprint 33 Phase 4 completion!**

Once the database connection is fixed:
- ✅ TickStockAppV2 HTTP API client is ready
- ✅ Redis event subscriber is listening
- ✅ Database table exists for processing history
- ✅ Admin dashboard updated to use real integration

The entire integration will be functional as soon as TickStockPL can start its API server successfully.