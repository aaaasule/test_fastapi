#!/bin/bash

PORT=8000
SCRIPT="main.py"
LOGFILE="nohup.out"

echo "[$(date)] 正在终止占用端口 $PORT 的进程..."

# 判断操作系统类型（Linux 或 macOS）
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux: 使用 fuser 或 lsof
    if command -v fuser &> /dev/null; then
        sudo fuser -k ${PORT}/tcp 2>/dev/null || true
    elif command -v lsof &> /dev/null; then
        PID=$(lsof -ti:${PORT})
        if [ -n "$PID" ]; then
            kill -9 $PID
            echo "已终止 PID: $PID"
        fi
    else
        echo "警告：未找到 fuser 或 lsof，无法自动 kill 端口 $PORT"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS: 使用 lsof
    if command -v lsof &> /dev/null; then
        PID=$(lsof -ti:${PORT})
        if [ -n "$PID" ]; then
            kill -9 $PID
            echo "已终止 PID: $PID"
        fi
    else
        echo "错误：macOS 上未安装 lsof（可通过 brew install gnu-lsof 安装）"
        exit 1
    fi
else
    echo "不支持的操作系统"
    exit 1
fi

echo "[$(date)] 启动 $SCRIPT ..."

# 启动 Python 脚本（确保 main.py 在当前目录或提供完整路径）
nohup python3 -u "$SCRIPT" > "$LOGFILE" 2>&1 &
APP_PID=$!

echo "[$(date)] 已在后台启动，PID: $APP_PID，日志输出到 $LOGFILE"
