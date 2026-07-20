#!/bin/bash

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     WeChat AI - DEBUG MODE            ║"
echo "  ║     Hot-reload + Debug logging        ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# 检查Python
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python not found! Please install Python 3.8+"
    exit 1
fi

# 检查.env文件
if [ ! -f .env ]; then
    echo "[WARN] .env file not found!"
    if [ -f .env.example ]; then
        echo "[INFO] Creating .env from template..."
        cp .env.example .env
        echo "[INFO] Please edit .env with your API keys"
        echo ""
    fi
fi

# 安装依赖
echo "[1/2] Checking dependencies..."
pip3 install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt --quiet 2>/dev/null
echo "[OK] Dependencies ready"
echo ""

# 启动调试服务
echo "[2/2] Starting DEBUG server..."
echo ""
echo "  ╔═══════════════════════════════════════════════╗"
echo "  ║  🌐 Chat:    http://127.0.0.1:53065/chat      ║"
echo "  ║  🧪 Test:    http://127.0.0.1:53065/test      ║"
echo "  ║  📊 Health:  http://127.0.0.1:53065/health    ║"
echo "  ║  🐛 Debug:   http://127.0.0.1:53065/debug     ║"
echo "  ╠═══════════════════════════════════════════════╣"
echo "  ║  ⚡ Hot-reload: ON (edit code → auto restart) ║"
echo "  ║  📝 Log level:  DEBUG                         ║"
echo "  ║  🔄 Press Ctrl+C to stop                      ║"
echo "  ╚═══════════════════════════════════════════════╝"
echo ""

# 使用 uvicorn 启动，开启热重载和调试日志
$PYTHON_CMD -m uvicorn main:app --reload --host 127.0.0.1 --port 53065 --log-level debug
