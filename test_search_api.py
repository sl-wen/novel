#!/usr/bin/env python3
"""
测试搜索API功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.novel_service import NovelService

async def test_search():
    """测试搜索功能"""
    print("🔍 开始测试搜索功能...")
    
    # 创建服务实例
    service = NovelService()
    
    # 检查书源加载情况
    print(f"📚 已加载 {len(service.sources)} 个书源")
    for source_id, source in service.sources.items():
        print(f"  - 书源 {source_id}: {source.rule.get('name', 'Unknown')}")
    
    # 测试搜索
    keyword = "斗破苍穹"
    print(f"\n🔎 搜索关键词: {keyword}")
    
    try:
        results = await service.search(keyword, max_results=5)
        print(f"✅ 搜索成功，找到 {len(results)} 条结果")
        
        for i, result in enumerate(results, 1):
            print(f"\n结果 {i}:")
            print(f"  书名: {result.title}")
            print(f"  作者: {result.author}")
            print(f"  简介: {result.intro[:50]}..." if result.intro else "  简介: 无")
            print(f"  来源: {result.source_name}")
            print(f"  得分: {result.score:.3f}")
            
    except Exception as e:
        print(f"❌ 搜索失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())