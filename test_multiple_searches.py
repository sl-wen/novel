#!/usr/bin/env python3
"""
测试多个搜索关键词
"""

import asyncio
import aiohttp
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_multiple_searches():
    """测试多个搜索关键词"""
    print("🔍 开始测试多个搜索关键词...")
    
    # API基础URL
    base_url = "http://localhost:8000"
    
    # 测试关键词列表
    keywords = [
        "斗破苍穹",
        "遮天",
        "完美世界",
        "凡人修仙传",
        "诛仙"
    ]
    
    try:
        async with aiohttp.ClientSession() as session:
            for keyword in keywords:
                print(f"\n{'='*50}")
                print(f"🔍 搜索关键词: {keyword}")
                print(f"{'='*50}")
                
                # 构建搜索URL
                search_url = f"{base_url}/api/novels/search"
                params = {
                    "keyword": keyword,
                    "maxResults": 3
                }
                
                try:
                    async with session.get(search_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get("code") == 200:
                                results = data.get("data", [])
                                print(f"✅ 找到 {len(results)} 条结果:")
                                
                                for i, result in enumerate(results, 1):
                                    print(f"  {i}. {result.get('title', 'N/A')} - {result.get('author', 'N/A')} ({result.get('source_name', 'N/A')})")
                            else:
                                print(f"❌ 搜索失败: {data.get('message', 'Unknown error')}")
                        else:
                            print(f"❌ HTTP请求失败，状态码: {response.status}")
                            
                except Exception as e:
                    print(f"❌ 搜索 '{keyword}' 时出错: {str(e)}")
                
                # 等待一下，避免请求过于频繁
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_multiple_searches())