#!/usr/bin/env python3
"""
测试搜索API功能
"""

import asyncio
import aiohttp
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_search_api():
    """测试搜索API"""
    print("🔍 开始测试搜索API...")
    
    # API基础URL
    base_url = "http://localhost:8000"
    
    # 测试参数
    keyword = "斗破苍穹"
    max_results = 5
    
    try:
        async with aiohttp.ClientSession() as session:
            # 构建搜索URL - 添加/api前缀
            search_url = f"{base_url}/api/novels/search"
            params = {
                "keyword": keyword,
                "maxResults": max_results
            }
            
            print(f"📡 发送请求到: {search_url}")
            print(f"🔍 搜索关键词: {keyword}")
            print(f"📊 最大结果数: {max_results}")
            
            # 发送GET请求
            async with session.get(search_url, params=params) as response:
                print(f"📋 响应状态码: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print("✅ API请求成功！")
                    print(f"📊 响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                    # 分析结果
                    if data.get("code") == 200:
                        results = data.get("data", [])
                        print(f"\n📚 找到 {len(results)} 条搜索结果:")
                        
                        for i, result in enumerate(results, 1):
                            print(f"\n结果 {i}:")
                            print(f"  书名: {result.get('title', 'N/A')}")
                            print(f"  作者: {result.get('author', 'N/A')}")
                            print(f"  来源: {result.get('source_name', 'N/A')}")
                            print(f"  得分: {result.get('score', 0):.3f}")
                            if result.get('intro'):
                                print(f"  简介: {result.get('intro', '')[:50]}...")
                    else:
                        print(f"❌ API返回错误: {data.get('message', 'Unknown error')}")
                else:
                    print(f"❌ HTTP请求失败，状态码: {response.status}")
                    text = await response.text()
                    print(f"响应内容: {text}")
                    
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_api())