@echo off
cd /d "%~dp0"
python tools\console_diagnostics\console_logs.py capture --until-stopped
pause
