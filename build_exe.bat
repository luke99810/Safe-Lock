@echo off
chcp 65001 > nul
echo ====================================
echo   SafeLock 打包为 EXE
echo ====================================
echo.

pip install pyinstaller Pillow pystray keyboard mouse -q

pyinstaller --onefile --windowed --noconsole ^
    --name SafeLock ^
    --icon=NONE ^
    safe_lock.py

echo.
echo ✅ 打包完成！EXE 文件在 dist\SafeLock.exe
pause
