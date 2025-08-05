#!/usr/bin/env python3
"""
下载功能诊断测试
"""

import requests
import time
import json

def test_download_diagnostic():
    """诊断下载问题"""
    print("🔍 下载功能诊断测试...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试API服务状态
    print("1. 测试API服务状态...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("   ✅ API服务正常运行")
        else:
            print(f"   ❌ API服务异常: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ API服务连接失败: {str(e)}")
        return
    
    # 2. 测试搜索API（短超时）
    print("\n2. 测试搜索API（短超时）...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "maxResults": 1},
            timeout=10  # 缩短超时时间
        )
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"   - 响应: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⚠️  搜索API超时（可能是网络问题）")
    except Exception as e:
        print(f"   ❌ 搜索API错误: {str(e)}")
    
    # 3. 测试书源列表
    print("\n3. 测试书源列表...")
    try:
        response = requests.get(f"{base_url}/api/novels/sources", timeout=10)
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - 书源数量: {len(data.get('data', []))}")
            for source in data.get('data', [])[:3]:  # 只显示前3个
                print(f"     - {source.get('name', 'Unknown')} (ID: {source.get('id')})")
        else:
            print(f"   - 响应: {response.text}")
    except Exception as e:
        print(f"   ❌ 书源列表错误: {str(e)}")
    
    # 4. 检查下载目录
    print("\n4. 检查下载目录...")
    import os
    from pathlib import Path
    
    download_path = Path("downloads")
    if download_path.exists():
        items = list(download_path.iterdir())
        print(f"   - 下载目录存在，包含 {len(items)} 项")
        for item in items[:5]:
            print(f"     - {item.name}")
    else:
        print("   - 下载目录不存在")
    
    # 5. 分析问题
    print("\n5. 问题分析...")
    print("   💡 可能的问题:")
    print("   - 书源网站访问超时")
    print("   - 网络连接问题")
    print("   - 书源规则配置问题")
    print("   - 并发请求限制")
    
    print("\n   🔧 建议解决方案:")
    print("   - 增加超时时间")
    print("   - 减少并发请求数")
    print("   - 检查书源规则配置")
    print("   - 使用代理或VPN")

if __name__ == "__main__":
    test_download_diagnostic()