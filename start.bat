@echo off
chcp 65001 >nul
title WeChat AI Companion

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║     WeChat AI Companion v1.8.1        ║
echo  ║     https://github.com/LP45621/ExBot  ║
echo  ╚═══════════════════════════════════════╝
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

:: 检查.env文件
if not exist .env (
    echo [WARN] .env file not found, creating from template...
    if exist .env.example (
        copy .env.example .env >nul
        echo [INFO] Please edit .env with your API keys
        echo.
    ) else (
        echo [ERROR] .env.example not found!
        pause
        exit /b 1
    )
)

:: 安装依赖
echo [1/3] Checking dependencies...
pip install -r requirements.txt --quiet 2>nul
if errorlevel 1 (
    echo [WARN] Some dependencies may have failed, continuing...
)
echo [OK] Dependencies ready
echo.

:: 检查数据库
echo [2/3] Checking databases...
if not exist chat.db (
    echo [INFO] Creating chat.db...
)
if not exist human_memory.db (
    echo [INFO] Creating human_memory.db...
)
echo [OK] Databases ready
echo.

:: 启动服务
echo [3/3] Starting server...
echo.
echo  ╔═══════════════════════════════════════╗
echo  ║  Local:  http://127.0.0.1:53065/chat  ║
echo  ║  Test:   http://127.0.0.1:53065/test  ║
echo  ║  Health: http://127.0.0.1:53065/health ║
echo  ╚═══════════════════════════════════════╝
echo.
echo  Press Ctrl+C to stop
echo.

python main.py

pause
