@echo off
chcp 65001 >nul
echo ========================================
echo   智能客服 Agent Demo 启动脚本
echo ========================================
echo.

REM 检查 .env 文件
if not exist .env (
    echo [!] 未找到 .env 文件
    echo [*] 正在从 .env.example 创建 .env...
    copy .env.example .env >nul
    echo [!] 请编辑 .env 文件，填入你的 DASHSCOPE_API_KEY
    echo.
    pause
    exit /b 1
)

REM 切换到 src 目录并启动
cd src
echo [*] 启动服务...
python main.py
