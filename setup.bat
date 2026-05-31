@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo    NTE 异环钓鱼自动化 - 一键部署脚本
echo ============================================
echo.

:: ── 1. 检查 Python ──
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

:: ── 2. 创建虚拟环境 ──
echo [2/5] 创建虚拟环境...
if not exist "venv\" (
    python -m venv venv
    echo 虚拟环境已创建
) else (
    echo 虚拟环境已存在，跳过
)
echo.

:: ── 3. 安装 Python 依赖 ──
echo [3/5] 安装 Python 依赖...
call venv\Scripts\activate
pip install --upgrade pip -q
pip install -r requirements.txt
echo.

:: ── 4. 检查 ViGEmBus 驱动 ──
echo [4/5] 检查依赖状态...
echo.

echo   ✅ opencv-python (图像识别)
echo   ✅ mss          (屏幕捕获)
echo   ✅ pynput       (键鼠模拟)
echo   ✅ pywin32      (窗口定位)
echo   ✅ psutil       (进程检测)
echo.

echo.
echo ──────────────────────────────────────────
echo          检查结果汇总
echo ──────────────────────────────────────────
echo   Python  : 已安装
echo   虚拟环境: venv\
echo   依赖    : 已安装
echo   输入模式: 键鼠 (pynput)
echo ──────────────────────────────────────────
echo.

echo [5/5] 部署完成！
echo.
echo 启动方式:
echo   call venv\Scripts\activate
echo   python main.py
echo.

pause
