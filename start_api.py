#!/usr/bin/env python3
"""
API启动脚本
提供便捷的API启动方式，包含配置检查和状态监控
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def check_dependencies():
    """检查依赖是否安装"""
    print("🔍 检查依赖...")
    required_packages = [
        "fastapi",
        "uvicorn",
        "requests",
        "beautifulsoup4",
        "aiohttp",
        "pydantic",
        "pydantic-settings",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - 未安装")

    if missing_packages:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False

    print("✅ 所有依赖已安装")
    return True


def check_configuration():
    """检查配置文件"""
    print("\n🔍 检查配置...")

    # 检查书源规则目录
    rules_path = Path("resources/rule/new")
    if rules_path.exists():
        rule_files = list(rules_path.glob("rule-*.json"))
        print(f"✅ 书源规则目录存在，找到 {len(rule_files)} 个规则文件")
        for rule_file in rule_files[:5]:  # 显示前5个
            print(f"   📄 {rule_file.name}")
        if len(rule_files) > 5:
            print(f"   ... 还有 {len(rule_files) - 5} 个文件")
    else:
        print("❌ 书源规则目录不存在: resources/rule/new")
        return False

    # 检查下载目录
    download_path = Path("downloads")
    if not download_path.exists():
        download_path.mkdir(parents=True, exist_ok=True)
        print("✅ 创建下载目录: downloads")
    else:
        print("✅ 下载目录存在: downloads")

    return True


def start_api():
    """启动API服务"""
    print("\n🚀 启动API服务...")

    # 检查是否已经在运行
    try:
        response = requests.get("http://localhost:8000/", timeout=2)
        if response.status_code == 200:
            print("⚠️  API服务已经在运行 (http://localhost:8000)")
            print("   访问 http://localhost:8000/docs 查看API文档")
            return True
    except:
        pass

    # 启动服务
    try:
        print("正在启动 uvicorn...")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload",
            ]
        )

        # 等待服务启动
        print("等待服务启动...")
        for i in range(30):  # 最多等待30秒
            try:
                response = requests.get("http://localhost:8000/", timeout=2)
                if response.status_code == 200:
                    print("✅ API服务启动成功!")
                    print("📚 API文档: http://localhost:8000/docs")
                    print("🔍 健康检查: http://localhost:8000/api/novels/health")
                    print(
                        "🔍 搜索测试: http://localhost:8000/api/novels/search?keyword=斗破苍穹"
                    )
                    print("\n按 Ctrl+C 停止服务")
                    return True
            except:
                time.sleep(1)
                print(f"等待中... ({i+1}/30)")

        print("❌ 服务启动超时")
        return False

    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
        return True
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("📚 小说API启动工具")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        return

    # 检查配置
    if not check_configuration():
        return

    # 启动API
    start_api()


if __name__ == "__main__":
    main()
