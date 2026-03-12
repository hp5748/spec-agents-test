#!/bin/bash
echo "========================================"
echo "  智能客服 Agent Demo 启动脚本"
echo "========================================"
echo

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "[!] 未找到 .env 文件"
    echo "[*] 正在从 .env.example 创建 .env..."
    cp .env.example .env
    echo "[!] 请编辑 .env 文件，填入你的 DASHSCOPE_API_KEY"
    echo
    exit 1
fi

# 切换到 src 目录并启动
cd src
echo "[*] 启动服务..."
python main.py
