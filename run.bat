@echo off
setlocal
cd /d "%~dp0"

echo Starting Property Marketplace...
echo.
echo Keep both server windows open while using the app.
echo Closing either window will disconnect that part of the app.
echo.

start "Property Marketplace API" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"
start "Property Marketplace Frontend" cmd /k "cd /d frontend && npm run dev -- --host 127.0.0.1"

echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
echo.
echo Open the Frontend address in your browser.
pause
