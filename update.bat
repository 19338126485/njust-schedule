@echo off & chcp 65001 >nul
cd /d %~dp0
where python >nul 2>&1 || (echo 未找到 Python，请确认已安装并加入 PATH & pause & exit /b 1)
python update.py
pause
