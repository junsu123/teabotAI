@echo off
cd /d "%~dp0"
py -3 browser_listing.py watch --seconds 15
pause
