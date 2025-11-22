@echo off
REM Quick Massive API Testing Batch Script
REM Usage: test_massive_quick.bat [option]
REM
REM Options:
REM   etf         - Test common ETFs data availability
REM   etf-all     - Search and test all ETFs (takes longer)
REM   websocket   - Test single WebSocket connection
REM   websocket-3 - Test 3 concurrent WebSocket connections
REM   explorer    - Run API explorer (list ETFs)
REM   snapshot    - Get market snapshot for common ETFs
REM   endpoints   - Test all API endpoints

SET OPTION=%1

IF "%OPTION%"=="" (
    echo.
    echo ============================================================
    echo Massive API Quick Testing
    echo ============================================================
    echo.
    echo Usage: test_massive_quick.bat [option]
    echo.
    echo Available options:
    echo   etf         - Test common ETFs data availability
    echo   etf-all     - Search and test all ETFs ^(takes longer^)
    echo   websocket   - Test single WebSocket connection
    echo   websocket-3 - Test 3 concurrent WebSocket connections
    echo   explorer    - Run API explorer ^(list ETFs^)
    echo   snapshot    - Get market snapshot for common ETFs
    echo   endpoints   - Test all API endpoints
    echo.
    echo Example: test_massive_quick.bat etf
    echo.
    goto :END
)

IF "%OPTION%"=="etf" (
    echo Testing common ETFs data availability...
    python scripts\dev_tools\util_massive_etf_discovery.py
    goto :END
)

IF "%OPTION%"=="etf-all" (
    echo Searching and testing all available ETFs...
    python scripts\dev_tools\util_massive_etf_discovery.py --search --verbose
    goto :END
)

IF "%OPTION%"=="websocket" (
    echo Testing single WebSocket connection ^(30 seconds^)...
    python scripts\dev_tools\util_massive_websocket_test.py --duration 30
    goto :END
)

IF "%OPTION%"=="websocket-3" (
    echo Testing 3 concurrent WebSocket connections ^(60 seconds^)...
    python scripts\dev_tools\util_massive_websocket_test.py --connections 3 --duration 60
    goto :END
)

IF "%OPTION%"=="explorer" (
    echo Listing available ETFs via API...
    python scripts\dev_tools\util_massive_api_explorer.py --list-etfs --limit 50
    goto :END
)

IF "%OPTION%"=="snapshot" (
    echo Getting market snapshot for common ETFs...
    python scripts\dev_tools\util_massive_api_explorer.py --market-snapshot
    goto :END
)

IF "%OPTION%"=="endpoints" (
    echo Testing all API endpoints with SPY...
    python scripts\dev_tools\util_massive_api_explorer.py --test-endpoints
    goto :END
)

echo Unknown option: %OPTION%
echo Run without arguments to see available options.

:END
