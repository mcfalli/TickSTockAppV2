@echo off
REM Quick ETF test using curl and Massive API
REM Usage: test_etfs_curl.bat

setlocal enabledelayedexpansion

REM Read API key from .env
for /f "tokens=2 delims==" %%a in ('findstr /i "MASSIVE_API_KEY" .env 2^>nul') do set API_KEY=%%a

if "%API_KEY%"=="" (
    echo ERROR: MASSIVE_API_KEY not found in .env
    exit /b 1
)

REM Test date (recent trading day)
set TEST_DATE=2025-11-18

echo ======================================================================
echo MASSIVE API - ETF QUICK TEST
echo ======================================================================
echo API Key: *****%API_KEY:~-4%
echo Test Date: %TEST_DATE%
echo ======================================================================
echo.

REM ETFs to test
set ETFS=SPY QQQ XLF XLE XLK XLV XLI GLD TLT

for %%E in (%ETFS%) do (
    echo Testing %%E...
    curl -s "https://api.massive.com/v1/open-close/%%E/%TEST_DATE%?adjusted=true&apiKey=%API_KEY%" > temp_%%E.json

    REM Check if response contains error
    findstr /i "error" temp_%%E.json >nul
    if errorlevel 1 (
        REM No error - extract close price
        for /f "tokens=2 delims=:" %%a in ('findstr "close" temp_%%E.json') do (
            echo   [OK] %%E - %%a
        )
    ) else (
        REM Error found
        echo   [X] %%E - ERROR
    )

    del temp_%%E.json
)

echo.
echo ======================================================================
echo Test complete
echo ======================================================================
