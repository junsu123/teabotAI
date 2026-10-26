@echo off
cd /d "%~dp0"
py -3 main.py daemon --minutes 240
pause
