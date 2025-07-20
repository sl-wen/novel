#!/usr/bin/env python3
"""
检查部署状态
"""

import requests
import json
import sys
from urllib.parse import quote

def check_server_status():
    """检查服务器状态"""
    
    print("=== 服务器状态检查 ===")
    
    # 检查主页面
    print("1. 检查主页面...")
    try:
        response = requests.get("https://slwen.cn/", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ 主页面正常")
        else:
            print(f"   ❌ 主页面异常: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 主页面检查失败: {e}")
    
    # 检查端口8000
    print("2. 检查端口8000...")
    try:
        response = requests.get("https://slwen.cn:8000/", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ 端口8000服务正常")
        else:
            print(f"   ❌ 端口8000服务异常: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 端口8000检查失败: {e}")
    
    # 检查Nginx配置
    print("3. 检查Nginx配置...")
    try:
        response = requests.get("https://slwen.cn/api/novels/sources", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Nginx路由正常")
        else:
            print(f"   ❌ Nginx路由异常: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Nginx配置检查失败: {e}")

def test_direct_api():
    """直接测试API"""
    
    print("\n=== 直接API测试 ===")
    
    # 测试书源API
    print("1. 测试书源API...")
    try:
        response = requests.get("https://slwen.cn/api/novels/sources", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ 书源API正常")
            try:
                data = response.json()
                print(f"   返回数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   响应内容: {response.text[:200]}...")
        else:
            print(f"   ❌ 书源API异常: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 书源API测试失败: {e}")
    
    # 测试搜索API
    print("2. 测试搜索API...")
    try:
        url = "https://slwen.cn/api/novels/search?keyword=修真"
        response = requests.get(url, timeout=30)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ 搜索API正常")
            try:
                data = response.json()
                print(f"   返回数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   响应内容: {response.text[:200]}...")
        else:
            print(f"   ❌ 搜索API异常: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ 搜索API测试失败: {e}")

def check_nginx_config():
    """检查Nginx配置"""
    
    print("\n=== Nginx配置检查 ===")
    
    # 检查不同的路径
    paths = [
        "/api/novels/sources",
        "/api/novels/search?keyword=test",
        "/novel/health",
        "/novel/docs",
        "/"
    ]
    
    for path in paths:
        print(f"检查路径: {path}")
        try:
            url = f"https://slwen.cn{path}"
            response = requests.get(url, timeout=10)
            print(f"   状态码: {response.status_code}")
            print(f"   内容类型: {response.headers.get('content-type', 'N/A')}")
            if response.status_code == 200:
                print("   ✅ 路径可访问")
            else:
                print(f"   ❌ 路径不可访问")
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
        print()

if __name__ == "__main__":
    print("开始检查部署状态...")
    print()
    
    check_server_status()
    test_direct_api()
    check_nginx_config()
    
    print("检查完成！") 