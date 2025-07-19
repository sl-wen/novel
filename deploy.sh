#!/bin/bash

# 小说搜索下载API部署脚本
# 使用方法: ./deploy.sh [production|docker]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_message "检查系统依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 未安装"
        exit 1
    fi
    
    # 检查git
    if ! command -v git &> /dev/null; then
        print_error "git 未安装"
        exit 1
    fi
    
    print_message "系统依赖检查完成"
}

# 生产环境部署
deploy_production() {
    print_message "开始生产环境部署..."
    
    # 创建项目目录
    sudo mkdir -p /var/www/novel-api
    sudo mkdir -p /var/log/novel-api
    
    # 设置权限
    sudo chown -R $USER:$USER /var/www/novel-api
    sudo chown -R $USER:$USER /var/log/novel-api
    
    # 进入项目目录
    cd /var/www/novel-api
    
    # 克隆代码（如果目录为空）
    if [ ! -d ".git" ]; then
        print_message "克隆项目代码..."
        git clone https://github.com/your-username/novel-api.git .
    else
        print_message "更新项目代码..."
        git pull origin main
    fi
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        print_message "创建Python虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖
    print_message "安装Python依赖..."
    pip install -r requirements.txt
    
    # 创建必要目录
    mkdir -p downloads logs
    
    # 创建systemd服务
    print_message "配置systemd服务..."
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
    print_message "启动API服务..."
    sudo systemctl start novel-api
    sudo systemctl enable novel-api
    
    # 检查服务状态
    if sudo systemctl is-active --quiet novel-api; then
        print_message "API服务启动成功"
    else
        print_error "API服务启动失败"
        sudo systemctl status novel-api
        exit 1
    fi
    
    print_message "生产环境部署完成！"
    print_message "API地址: http://localhost:8000"
    print_message "服务状态: sudo systemctl status novel-api"
}

# Docker部署
deploy_docker() {
    print_message "开始Docker部署..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi
    
    # 构建并启动服务
    print_message "构建Docker镜像..."
    docker-compose build
    
    print_message "启动Docker服务..."
    docker-compose up -d
    
    # 等待服务启动
    print_message "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    if curl -f http://localhost:8000/ > /dev/null 2>&1; then
        print_message "Docker部署成功！"
        print_message "API地址: http://localhost:8000"
        print_message "Nginx地址: http://localhost:80"
    else
        print_error "Docker部署失败"
        docker-compose logs
        exit 1
    fi
}

# 主函数
main() {
    print_message "小说搜索下载API部署脚本"
    print_message "=========================="
    
    # 检查依赖
    check_dependencies
    
    # 根据参数选择部署方式
    case "${1:-production}" in
        "production")
            deploy_production
            ;;
        "docker")
            deploy_docker
            ;;
        *)
            print_error "未知的部署方式: $1"
            print_message "使用方法: $0 [production|docker]"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 