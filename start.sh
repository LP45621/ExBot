#!/bin/bash

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     WeChat AI Companion v1.8.1        ║"
echo "  ║     https://github.com/LP45621/ExBot  ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found! Please install Python 3.8+"
    exit 1
fi

# 检查.env文件
if [ ! -f .env ]; then
    echo "[WARN] .env file not found, creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[INFO] Please edit .env with your API keys"
        echo ""
    else
        echo "[ERROR] .env.example not found!"
        exit 1
    fi
fi

# 安装依赖
echo "[1/3] Checking dependencies..."
pip3 install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt --quiet 2>/dev/null
echo "[OK] Dependencies ready"
echo ""

# 检查数据库
echo "[2/3] Checking databases..."
[ ! -f chat.db ] && echo "[INFO] Creating chat.db..."
[ ! -f human_memory.db ] && echo "[INFO] Creating human_memory.db..."
echo "[OK] Databases ready"
echo ""

# 启动服务
echo "[3/3] Starting server..."
echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║  Local:  http://127.0.0.1:53065/chat  ║"
echo "  ║  Test:   http://127.0.0.1:53065/test  ║"
echo "  ║  Health: http://127.0.0.1:53065/health ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

python3 main.py || python main.py
