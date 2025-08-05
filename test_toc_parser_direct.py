#!/usr/bin/env python3
"""
直接测试目录解析器
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.source import Source
from app.parsers.toc_parser import TocParser
import asyncio
import logging

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)

async def test_toc_parser_direct():
    """直接测试目录解析器"""
    print("🔍 直接测试目录解析器...")
    
    # 1. 加载书源
    print("1. 加载书源...")
    try:
        source = Source(11)  # 加载ID为11的书源
        print(f"   - 书源名称: {source.rule.get('name', 'Unknown')}")
        print(f"   - 书源URL: {source.rule.get('url', 'Unknown')}")
        
        # 显示目录规则
        toc_rule = source.rule.get('toc', {})
        print(f"   - 目录选择器: {toc_rule.get('list', 'Unknown')}")
        print(f"   - 标题选择器: {toc_rule.get('title', 'Unknown')}")
        print(f"   - URL选择器: {toc_rule.get('url', 'Unknown')}")
        
    except Exception as e:
        print(f"   ❌ 加载书源失败: {str(e)}")
        return
    
    # 2. 创建目录解析器
    print("\n2. 创建目录解析器...")
    try:
        parser = TocParser(source)
        print("   ✅ 目录解析器创建成功")
    except Exception as e:
        print(f"   ❌ 创建目录解析器失败: {str(e)}")
        return
    
    # 3. 测试目录解析
    print("\n3. 测试目录解析...")
    try:
        url = "https://www.0xs.net/txt/1.html"
        chapters = await parser.parse(url)
        print(f"   - 解析结果: {len(chapters)} 个章节")
        
        if chapters:
            print("   - 前5个章节:")
            for i, chapter in enumerate(chapters[:5]):
                print(f"     {i+1}. {chapter.title} -> {chapter.url}")
        else:
            print("   ❌ 没有解析到章节")
            
    except Exception as e:
        print(f"   ❌ 目录解析失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_toc_parser_direct())