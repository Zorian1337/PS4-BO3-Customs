@echo off
cd /d "%~dp0"
python tools\project_session.py test
if errorlevel 1 exit /b 1
python tools\console_diagnostics\test_console_logs.py
if errorlevel 1 exit /b 1
python tools\test_project_session.py
pause
