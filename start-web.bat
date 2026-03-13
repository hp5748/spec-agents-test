@echo off
chcp 65001 >nul
title 智能客服 Agent - 前端界面

echo.
echo ╔══════════════════════════════════════════════╗
echo ║         智能客服 Agent - 前端界面            ║
echo ╠══════════════════════════════════════════════╣
echo ║  正在启动服务...                             ║
echo ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

:: 启动后端服务（后台运行）
echo [1/2] 启动后端服务...
start /b "" cmd /c "cd src && python main.py > ..\server.log 2>&1"

:: 等待服务启动
echo [2/2] 等待服务就绪...
set /a count=0
:wait_loop
timeout /t 1 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    set /a count+=1
    if !count! geq 15 (
        echo [ERROR] 服务启动超时，请检查 server.log
        pause
        exit /b 1
    )
    goto wait_loop
)

echo.
echo ╔══════════════════════════════════════════════╗
echo ║  服务已启动!                                 ║
echo ╠══════════════════════════════════════════════╣
echo ║  前端地址: http://localhost:8000/chat        ║
echo ║  API文档:  http://localhost:8000/docs        ║
echo ╚══════════════════════════════════════════════╝
echo.

:: 自动打开浏览器
echo 正在打开浏览器...
start http://localhost:8000/chat

echo.
echo 按 Ctrl+C 停止服务
echo 日志文件: %~dp0server.log
echo.

:: 保持运行，显示日志
type server.log 2>nul
echo.
echo ----------------------------------------
echo 服务运行中，按 Ctrl+C 停止...
echo ----------------------------------------

:: 实时显示日志
:log_loop
timeout /t 2 /nobreak >nul
:: 可以在这里添加更多逻辑
goto log_loop
