#!/usr/bin/env python3
"""
目录解析测试脚本

用于测试书源的目录解析功能，特别是针对章节数量不匹配问题的修复效果。
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.core.source import Source
from app.parsers.toc_parser import TocParser


async def test_toc_parsing(source_id: int, url: str):
    """测试目录解析"""
    print(f"\n=== 测试书源 {source_id} 的目录解析 ===")
    print(f"URL: {url}")
    
    try:
        # 创建书源和解析器
        source = Source(source_id)
        parser = TocParser(source)
        
        print(f"书源名称: {source.name}")
        print(f"书源配置: {source.rule.get('url', '')}")
        
        # 获取目录URL
        toc_url = parser._get_toc_url(url)
        print(f"目录URL: {toc_url}")
        
        # 解析目录
        print("\n开始解析目录...")
        chapters = await parser.parse(url)
        
        print(f"\n=== 解析结果 ===")
        print(f"总章节数: {len(chapters)}")
        
        if not chapters:
            print("未获取到任何章节！")
            return
        
        # 分析章节编号分布
        chapters_with_numbers = 0
        chapters_without_numbers = 0
        number_distribution = {}
        
        for chapter in chapters:
            number = parser._extract_chapter_number(chapter.title)
            if number > 0:
                chapters_with_numbers += 1
                number_distribution[number] = number_distribution.get(number, 0) + 1
            else:
                chapters_without_numbers += 1
        
        print(f"有编号章节: {chapters_with_numbers}")
        print(f"无编号章节: {chapters_without_numbers}")
        
        # 检查重复编号
        duplicates = {k: v for k, v in number_distribution.items() if v > 1}
        if duplicates:
            print(f"重复编号: {duplicates}")
        else:
            print("无重复编号")
        
        # 显示前10个和后10个章节
        print(f"\n=== 前10个章节 ===")
        for i, chapter in enumerate(chapters[:10]):
            number = parser._extract_chapter_number(chapter.title)
            print(f"{i+1:2d}. [{number:3d}] {chapter.title}")
        
        if len(chapters) > 10:
            print(f"\n=== 后10个章节 ===")
            for i, chapter in enumerate(chapters[-10:], len(chapters)-9):
                number = parser._extract_chapter_number(chapter.title)
                print(f"{i:2d}. [{number:3d}] {chapter.title}")
        
        print(f"\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    # 默认测试用例
    test_cases = [
        {
            "source_id": 4,
            "url": "http://wap.99xs.info/124310/",
            "description": "书源4 - 鸟书网测试"
        }
    ]
    
    print("目录解析测试工具")
    print("================")
    
    # 如果有命令行参数，使用命令行参数
    if len(sys.argv) >= 3:
        try:
            source_id = int(sys.argv[1])
            url = sys.argv[2]
            await test_toc_parsing(source_id, url)
        except ValueError:
            print("错误: source_id 必须是数字")
            sys.exit(1)
    else:
        # 运行默认测试用例
        for test_case in test_cases:
            await test_toc_parsing(
                test_case["source_id"], 
                test_case["url"]
            )
            print("\n" + "="*50)


if __name__ == "__main__":
    # 使用说明
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("使用方法:")
        print("  python test_toc_parsing.py                    # 运行默认测试")
        print("  python test_toc_parsing.py <source_id> <url>  # 测试指定书源和URL")
        print("")
        print("示例:")
        print("  python test_toc_parsing.py 4 'http://wap.99xs.info/124310/'")
        sys.exit(0)
    
    asyncio.run(main())