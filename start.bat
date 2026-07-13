@echo off
chcp 65001 >nul
echo ========================
echo   WeChat AI Companion
echo   Port: 53065
echo ========================
echo.
pip install -r requirements.txt --quiet 2>nul
python main.py
pause
