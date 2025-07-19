#!/bin/bash

# 简化的部署脚本
set -e

echo "=== 简化部署测试 ==="

# 进入项目目录
cd /var/www/novel-api
echo "当前目录: $(pwd)"

# 检查文件
echo "检查文件..."
ls -la requirements.txt
ls -la app/main.py

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate
python --version

# 检查依赖
echo "检查依赖..."
pip list | grep -E "(fastapi|uvicorn|aiohttp)"

# 测试导入
echo "测试导入..."
python -c "import app.main; print('✅ 导入成功')"

# 测试启动（5秒）
echo "测试启动..."
timeout 5s python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
PID=$!
sleep 3

if kill -0 $PID 2>/dev/null; then
    echo "✅ 应用启动成功"
    kill $PID
    exit 0
else
    echo "❌ 应用启动失败"
    exit 1
fi 