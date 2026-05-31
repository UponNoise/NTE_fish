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
echo [4/5] 检查虚拟手柄驱动 (ViGEmBus) ...
echo.

set DRIVER_INSTALLED=0
:: 方式1: 检查设备管理器中的 ViGEmBus
pnputil /enum-drivers 2>nul | findstr /i "ViGEmBus" >nul && set DRIVER_INSTALLED=1
:: 方式2: 检查注册表
reg query "HKLM\SYSTEM\CurrentControlSet\Services\ViGEmBus" >nul 2>&1 && set DRIVER_INSTALLED=1
:: 方式3: 检查驱动文件
if exist "C:\Windows\System32\drivers\ViGEmBus.sys" set DRIVER_INSTALLED=1
if exist "C:\Program Files\Nefarius Software Solutions\ViGEmBus\ViGEmBusUpdater.exe" set DRIVER_INSTALLED=1

if %DRIVER_INSTALLED% equ 1 (
    echo [✓] ViGEmBus 驱动已安装
) else (
    echo [!] ViGEmBus 驱动未安装！
    echo.
    echo     虚拟手柄功能需要 ViGEmBus 驱动程序。
    echo     下载地址: https://github.com/nefarius/ViGEmBus/releases
    echo     请下载最新的 .exe 安装包并安装后重新运行本脚本。
    echo.
    echo     安装步骤:
    echo       1. 打开上述链接
    echo       2. 下载 ViGEmBus_Setup_*.exe
    echo       3. 以管理员身份运行安装
    echo       4. 重启电脑（如提示）
    echo.
)

echo.
echo ──────────────────────────────────────────
echo          检查结果汇总
echo ──────────────────────────────────────────
echo   Python  : 已安装
echo   虚拟环境: venv\
echo   依赖    : 已安装
if %DRIVER_INSTALLED% equ 1 (
    echo   驱动    : ViGEmBus 已安装 [✓]
) else (
    echo   驱动    : ViGEmBus 未安装 [✗ 请手动安装]
)
echo ──────────────────────────────────────────
echo.

echo [5/5] 部署完成！
echo.
echo 启动方式:
echo   call venv\Scripts\activate
echo   python main.py
echo.

pause
