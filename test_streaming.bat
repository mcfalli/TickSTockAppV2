@echo off
echo ============================================================
echo MOCK STREAMING TEST
echo ============================================================
echo.
echo This will publish simulated streaming events to Redis
echo Keep your browser on the Live Streaming page to see updates
echo.
echo Press Ctrl+C to stop
echo ============================================================
echo.

venv\Scripts\python.exe tests\manual\mock_streaming_publisher.py 60
