#!/usr/bin/env python3
"""
带详细日志的目录解析器调试
"""

import requests
import json
import logging

def debug_toc_logs():
    """带详细日志的目录解析器调试"""
    print("🔍 带详细日志的目录解析器调试...")
    
    # 设置详细日志
    logging.basicConfig(level=logging.DEBUG)
    
    base_url = "http://localhost:8000"
    
    # 1. 测试目录API并查看详细响应
    print("1. 测试目录API...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/toc",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11
            },
            timeout=60
        )
        
        print(f"   - 状态码: {response.status_code}")
        print(f"   - 响应头: {dict(response.headers)}")
        print(f"   - 响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            chapters = data.get("data", [])
            print(f"   - 章节数量: {len(chapters)}")
            
            if chapters:
                print("   - 前5个章节:")
                for i, chapter in enumerate(chapters[:5]):
                    print(f"     {i+1}. {chapter.get('title', 'Unknown')} -> {chapter.get('url', 'Unknown')}")
            else:
                print("   ❌ 没有章节")
                
    except Exception as e:
        print(f"   ❌ API调用失败: {str(e)}")
    
    # 2. 测试直接访问目录URL
    print("\n2. 测试直接访问目录URL...")
    try:
        import urllib.request
        import ssl
        
        # 创建SSL上下文
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # 测试目录URL
        toc_url = "https://www.0xs.net/txt/1.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(toc_url, headers=headers)
        with urllib.request.urlopen(req, context=context, timeout=30) as response:
            html = response.read().decode('utf-8')
            print(f"   ✅ 直接访问成功，HTML长度: {len(html)}")
            
            # 检查HTML内容
            if 'catalog' in html:
                print("   ✅ HTML包含catalog元素")
            else:
                print("   ❌ HTML不包含catalog元素")
                
            if '.catalog li a' in html:
                print("   ✅ HTML包含选择器相关元素")
            else:
                print("   ❌ HTML不包含选择器相关元素")
                
    except Exception as e:
        print(f"   ❌ 直接访问失败: {str(e)}")
    
    # 3. 测试不同的书源
    print("\n3. 测试不同的书源...")
    try:
        # 获取所有书源
        sources_response = requests.get(f"{base_url}/api/novels/sources", timeout=10)
        if sources_response.status_code == 200:
            sources_data = sources_response.json()
            sources = sources_data.get("data", [])
            print(f"   - 可用书源数量: {len(sources)}")
            
            # 测试前3个书源
            for i, source in enumerate(sources[:3]):
                source_id = source.get("id")
                source_name = source.get("name", "Unknown")
                print(f"   - 测试书源 {i+1}: {source_name} (ID: {source_id})")
                
                # 搜索测试
                search_response = requests.get(
                    f"{base_url}/api/novels/search",
                    params={"keyword": "斗破苍穹", "maxResults": 1},
                    timeout=30
                )
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    results = search_data.get("data", [])
                    if results:
                        result = results[0]
                        print(f"     ✅ 搜索成功: {result.get('title', 'Unknown')}")
                        
                        # 测试目录
                        toc_response = requests.get(
                            f"{base_url}/api/novels/toc",
                            params={
                                "url": result.get("url"),
                                "sourceId": source_id
                            },
                            timeout=30
                        )
                        
                        if toc_response.status_code == 200:
                            toc_data = toc_response.json()
                            chapters = toc_data.get("data", [])
                            print(f"     - 目录章节数: {len(chapters)}")
                            
                            if chapters:
                                print(f"     ✅ 书源 {source_name} 目录解析成功")
                                break
                            else:
                                print(f"     ❌ 书源 {source_name} 目录解析失败")
                        else:
                            print(f"     ❌ 书源 {source_name} 目录API失败")
                    else:
                        print(f"     ❌ 书源 {source_name} 搜索失败")
                else:
                    print(f"     ❌ 书源 {source_id} 搜索API失败")
                    
    except Exception as e:
        print(f"   ❌ 测试书源失败: {str(e)}")
    
    # 4. 生成修复建议
    print("\n4. 生成修复建议...")
    print("   💡 可能的解决方案:")
    print("   - 检查目录解析器的网络请求")
    print("   - 验证CSS选择器是否正确")
    print("   - 尝试使用不同的书源")
    print("   - 添加更详细的错误日志")
    print("   - 检查网站反爬虫机制")

if __name__ == "__main__":
    debug_toc_logs()