#!/usr/bin/env python3
"""
简单的API测试脚本
"""

import requests
import json

def test_api():
    """测试API基本功能"""
    print("🔍 测试API基本功能...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试根路径
    print("1. 测试根路径...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"   - 状态码: {response.status_code}")
        print(f"   - 响应: {response.text}")
    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
    
    # 2. 测试搜索API
    print("\n2. 测试搜索API...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "maxResults": 1},
            timeout=30
        )
        print(f"   - 状态码: {response.status_code}")
        print(f"   - 响应: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
    
    # 3. 测试API文档
    print("\n3. 测试API文档...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=10)
        print(f"   - 状态码: {response.status_code}")
        print(f"   - 响应长度: {len(response.text)}")
    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")

if __name__ == "__main__":
    test_api()