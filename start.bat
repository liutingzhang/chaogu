@echo off
chcp 65001 >nul
title ths_trade 交易服务

set "PYTHON=C:\Users\huazuo\AppData\Local\Programs\Python\Python310\python.exe"
set "APP=D:\ths_trade\app.py"
set "XIA_DAN=D:\同花顺\xiadan.exe"

echo ========================================
echo   ths_trade 同花顺自动化交易服务
echo ========================================
echo.

:: 检查同花顺是否在运行
tasklist /FI "IMAGENAME eq xiadan.exe" 2>NUL | find /I "xiadan.exe" >NUL
if errorlevel 1 (
    echo [警告] 未检测到同花顺交易客户端运行！
    echo.
    echo 请先手动打开同花顺交易客户端（xiadan.exe）并登录，
    echo 确保窗口可见、不要最小化，然后按任意键继续...
    echo.
    pause >nul
)

:: 检查配置文件中路径是否正确
echo [提示] 当前配置的同花顺路径: %XIA_DAN%
echo        如果路径不正确，请修改 D:\ths_trade\applications\API_Config.py
echo.

:: 启动服务
echo [启动] 正在启动交易服务...
echo.

cd /d D:\ths_trade
"%PYTHON%" "%APP%"

pause