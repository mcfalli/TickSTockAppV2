@echo off
echo Starting TickStockAppV2...
echo.

REM Activate virtual environment and start the application
call .\venv\Scripts\activate.bat
python start_app.py

pause