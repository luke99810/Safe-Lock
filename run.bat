@echo off
chcp 65001 > nul
echo ====================================
echo   SafeLock 安装与启动脚本
echo ====================================
echo.

echo [1/2] 安装依赖...
pip install pystray Pillow keyboard mouse -q
if %errorlevel% neq 0 (
    echo 安装失败，请检查 Python 环境
    pause
    exit /b 1
)

echo [2/2] 启动 SafeLock...
echo.
echo SafeLock 已启动，请查看系统托盘（右下角）
echo 右键托盘图标可锁屏或修改密码
echo.
python safe_lock.py
pause
