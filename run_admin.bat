@echo off
:: 以管理员权限重新启动自身
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在请求管理员权限...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo ========================================
echo   NTE 异环钓鱼自动化 v2.0 (管理员模式)
echo ========================================
echo.

call .\venv\Scripts\activate.bat
python main.py

pause
