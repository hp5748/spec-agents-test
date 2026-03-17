@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title 智能客服 Agent

echo.
echo ╔══════════════════════════════════════════════╗
echo ║           智能客服 Agent 启动脚本            ║
echo ╚══════════════════════════════════════════════╝
echo.

REM 切换到项目根目录
cd /d "%~dp0.."

:: 1. 检查 Python 环境
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 2. 检查 .env 文件
echo [2/4] 检查配置文件...
if not exist .env (
    echo [!] 未找到 .env 文件
    if exist .env.example (
        copy .env.example .env >nul
        echo [*] 已从 .env.example 创建 .env
        echo [!] 请编辑 .env 文件，填入你的 API Key
        pause
        exit /b 1
    ) else (
        echo [ERROR] 未找到 .env.example 文件
        pause
        exit /b 1
    )
)

:: 3. 启动后端服务
echo [3/4] 启动服务...
start /b "" cmd /c "cd src && python main.py > ..\server.log 2>&1"

:: 4. 等待服务就绪
echo [4/4] 等待服务就绪...
set /a count=0
:wait_loop
timeout /t 1 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    set /a count+=1
    if !count! geq 15 (
        echo [ERROR] 服务启动超时，请检查 server.log
        type server.log 2>nul
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
echo ----------------------------------------
echo 服务运行中，按 Ctrl+C 停止...
echo 日志文件: %~dp0..\server.log
echo ----------------------------------------
echo.

:: 显示初始日志
type server.log 2>nul

:: 保持运行
:keep_alive
timeout /t 60 /nobreak >nul
goto keep_alive
