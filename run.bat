@echo off
setlocal
cd /d "%~dp0"

echo Iniciando HabitaRD...
echo.
echo Mantenga abiertas ambas ventanas mientras utiliza la aplicación.
echo Si cierra una ventana, se desconectará esa parte de la aplicación.
echo.

start "HabitaRD API" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"
start "HabitaRD Web" cmd /k "cd /d frontend && npm run dev -- --host 127.0.0.1"

echo Servidor:  http://127.0.0.1:8000
echo Sitio web: http://127.0.0.1:5173
echo.
echo Abra la dirección del sitio web en su navegador.
pause
