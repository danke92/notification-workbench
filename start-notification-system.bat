@echo off
chcp 65001 >nul
title 通知工作台系统

echo ========================================
echo    通知工作台系统 - 快速启动
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.7+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检查Python环境...
python --version
echo.

REM 检查依赖包
echo [2/3] 检查依赖包...
pip show selenium >nul 2>&1
if errorlevel 1 (
    echo [提示] 首次使用，正在安装依赖包...
    pip install selenium webdriver-manager beautifulsoup4
    if errorlevel 1 (
        echo [错误] 依赖包安装失败
        pause
        exit /b 1
    )
) else (
    echo [完成] 依赖包已安装
)
echo.

REM 启动通知收集器
echo [3/3] 启动通知收集器...
echo.
echo ========================================
echo    提示：
echo    - 收集完成后，通知会保存在 notifications.json
echo    - 在浏览器中打开 personal-website/notifications.html 查看通知
echo    - 按 Ctrl+C 可以终止程序
echo ========================================
echo.
echo 正在启动 Python 脚本...
python notification-collector.py

if errorlevel 1 (
    echo.
    echo [错误] 脚本执行失败
    echo 请检查：
    echo   1. 教务系统账号密码是否正确
    echo   2. 网络连接是否正常
    echo   3. 教务系统页面结构是否变化
    echo.
)

pause
