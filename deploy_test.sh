#!/bin/bash

# 简化的部署测试脚本
set -e

echo "=== 开始部署测试 ==="

# 检查系统依赖
echo "检查系统依赖..."
which python3 || echo "Python3未安装"
which git || echo "Git未安装"
which pip3 || echo "Pip3未安装"

# 检查目录
echo "检查项目目录..."
if [ -d "/var/www/novel-api" ]; then
    echo "项目目录存在"
    cd /var/www/novel-api
    pwd
    ls -la
else
    echo "项目目录不存在，创建中..."
    sudo mkdir -p /var/www/novel-api
    sudo chown $USER:$USER /var/www/novel-api
    cd /var/www/novel-api
fi

# 检查Git仓库
echo "检查Git仓库..."
if [ -d ".git" ]; then
    echo "Git仓库存在"
    git status
else
    echo "Git仓库不存在，初始化中..."
    git init
    git remote add origin git@github.com:your-username/your-repo.git
fi

# 检查虚拟环境
echo "检查虚拟环境..."
if [ -d "venv" ]; then
    echo "虚拟环境存在"
    source venv/bin/activate
    python --version
    pip list | head -10
else
    echo "虚拟环境不存在，创建中..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# 检查服务状态
echo "检查服务状态..."
sudo systemctl status novel-api --no-pager || echo "服务未运行"

# 检查端口
echo "检查端口监听..."
netstat -tlnp | grep 8000 || echo "端口8000未监听"

# 测试API
echo "测试API连接..."
curl -f http://localhost:8000/ && echo "API连接成功" || echo "API连接失败"

echo "=== 部署测试完成 ===" 