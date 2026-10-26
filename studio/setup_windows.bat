@echo off
cd /d "%~dp0"
echo Cai dat cac thu vien cho Chrome Profile, hoc thao tac va luu mat khau proxy...
py -3 -m pip install -r requirements_gui.txt
if errorlevel 1 (echo Loi cai thu vien. & pause & exit /b 1)
py -3 -m playwright install chromium
if errorlevel 1 (echo Loi cai Chromium. & pause & exit /b 1)
echo Hoan thanh. Chay start_windows.bat de mo phan mem.
pause
