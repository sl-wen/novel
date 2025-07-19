#!/bin/bash

# 快速部署脚本 - 一键部署小说搜索下载API

echo "🚀 开始快速部署小说搜索下载API..."

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "❌ 请不要使用root用户运行此脚本"
    exit 1
fi

# 更新系统
echo "📦 更新系统包..."
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
echo "🔧 安装基础依赖..."
sudo apt install -y python3 python3-pip python3-venv nginx git curl wget

# 创建项目目录
echo "📁 创建项目目录..."
sudo mkdir -p /var/www/novel-api
sudo chown -R $USER:$USER /var/www/novel-api

# 进入项目目录
cd /var/www/novel-api

# 如果目录为空，提示用户
if [ ! -f "requirements.txt" ]; then
    echo "⚠️  请将项目文件复制到 /var/www/novel-api 目录"
    echo "或者运行: git clone <your-repo-url> ."
    exit 1
fi

# 创建虚拟环境
echo "🐍 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
echo "📚 安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建必要目录
echo "📂 创建必要目录..."
mkdir -p downloads logs

# 创建systemd服务
echo "⚙️  配置systemd服务..."
sudo tee /etc/systemd/system/novel-api.service > /dev/null <<EOF
[Unit]
Description=Novel Search API
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/var/www/novel-api
Environment=PATH=/var/www/novel-api/venv/bin
ExecStart=/var/www/novel-api/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd
sudo systemctl daemon-reload

# 启动服务
echo "🚀 启动API服务..."
sudo systemctl start novel-api
sudo systemctl enable novel-api

# 检查服务状态
if sudo systemctl is-active --quiet novel-api; then
    echo "✅ API服务启动成功"
else
    echo "❌ API服务启动失败"
    sudo systemctl status novel-api
    exit 1
fi

# 配置Nginx
echo "🌐 配置Nginx..."
sudo tee /etc/nginx/sites-available/novel-api > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # 支持大文件下载
        proxy_max_temp_file_size 0;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
EOF

# 启用站点
sudo ln -sf /etc/nginx/sites-available/novel-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
sudo nginx -t

# 重启Nginx
sudo systemctl reload nginx

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 健康检查
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "🎉 部署成功！"
    echo ""
    echo "📋 服务信息："
    echo "   API地址: http://localhost:8000"
    echo "   Nginx地址: http://localhost"
    echo "   API文档: http://localhost:8000/docs"
    echo ""
    echo "🔧 管理命令："
    echo "   查看状态: sudo systemctl status novel-api"
    echo "   重启服务: sudo systemctl restart novel-api"
    echo "   查看日志: sudo journalctl -u novel-api -f"
    echo ""
    echo "📁 文件位置："
    echo "   项目目录: /var/www/novel-api"
    echo "   下载目录: /var/www/novel-api/downloads"
    echo "   日志目录: /var/www/novel-api/logs"
else
    echo "❌ 部署失败，请检查日志"
    sudo systemctl status novel-api
    exit 1
fi 