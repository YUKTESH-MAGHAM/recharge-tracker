@echo off
echo Starting Recharge Tracker...
echo.
echo Open your browser at: http://127.0.0.1:8000
echo Press Ctrl+C to stop the server.
echo.
call venv\Scripts\uvicorn api.index:app --reload --port 8000
