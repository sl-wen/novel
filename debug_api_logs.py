#!/usr/bin/env python3
"""
启用详细日志的API调试
"""

import requests
import json
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

def debug_api_logs():
    """调试API日志"""
    print("🔍 调试API日志...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试API状态
    print("1. 测试API状态...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=10)
        print(f"   - API状态: {'✅ 运行中' if response.status_code == 200 else '❌ 未运行'}")
    except Exception as e:
        print(f"   - API状态: ❌ 连接失败 - {str(e)}")
        return
    
    # 2. 测试搜索功能
    print("\n2. 测试搜索功能...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "sourceId": 11},
            timeout=30
        )
        print(f"   - 搜索状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            print(f"   - 搜索结果数量: {len(results)}")
            if results:
                print(f"   - 第一个结果: {results[0].get('title', 'Unknown')}")
        else:
            print(f"   - 搜索失败: {response.text}")
    except Exception as e:
        print(f"   - 搜索错误: {str(e)}")
    
    # 3. 测试目录功能（带详细日志）
    print("\n3. 测试目录功能...")
    try:
        # 设置详细的请求日志
        import urllib3
        urllib3.disable_warnings()
        
        response = requests.get(
            f"{base_url}/api/novels/toc",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11
            },
            timeout=60,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Connection': 'keep-alive'
            }
        )
        
        print(f"   - 目录状态码: {response.status_code}")
        print(f"   - 响应头: {dict(response.headers)}")
        print(f"   - 响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            chapters = data.get("data", [])
            print(f"   - 章节数量: {len(chapters)}")
            
            if chapters:
                print("   - 前3个章节:")
                for i, chapter in enumerate(chapters[:3]):
                    print(f"     {i+1}. {chapter.get('title', 'Unknown')}")
            else:
                print("   ❌ 目录为空")
        else:
            print(f"   ❌ 目录请求失败: {response.text}")
            
    except Exception as e:
        print(f"   ❌ 目录错误: {str(e)}")
    
    # 4. 检查API进程
    print("\n4. 检查API进程...")
    try:
        import subprocess
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'uvicorn' in result.stdout:
            print("   ✅ 发现uvicorn进程")
            lines = result.stdout.split('\n')
            for line in lines:
                if 'uvicorn' in line:
                    print(f"     {line}")
        else:
            print("   ❌ 未发现uvicorn进程")
    except Exception as e:
        print(f"   - 进程检查失败: {str(e)}")

if __name__ == "__main__":
    debug_api_logs()