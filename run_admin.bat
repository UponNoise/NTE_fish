@echo off
:: ????????????
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ?????????...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo ========================================
echo   NTE ??????? v2.0 (?????)
echo ========================================
echo.

.\venv\Scripts\python.exe main.py

pause
