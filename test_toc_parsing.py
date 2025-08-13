#!/usr/bin/env python3
"""
目录解析测试脚本

用于测试书源的目录解析功能，特别是针对章节数量不匹配问题的修复效果。
"""

import asyncio
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.core.source import Source
from app.parsers.toc_parser import TocParser


async def test_toc_parsing(source_id: int, url: str, detailed: bool = True) -> Dict[str, Any]:
    """测试目录解析"""
    result = {
        "source_id": source_id,
        "url": url,
        "success": False,
        "error": None,
        "stats": {},
        "chapters": []
    }
    
    if detailed:
        print(f"\n=== 测试书源 {source_id} 的目录解析 ===")
        print(f"URL: {url}")
    
    start_time = time.time()
    
    try:
        # 创建书源和解析器
        source = Source(source_id)
        parser = TocParser(source)
        
        result["source_name"] = source.name
        result["source_url"] = source.rule.get('url', '')
        
        if detailed:
            print(f"书源名称: {source.name}")
            print(f"书源配置: {source.rule.get('url', '')}")
        
        # 获取目录URL
        toc_url = parser._get_toc_url(url)
        result["toc_url"] = toc_url
        
        if detailed:
            print(f"目录URL: {toc_url}")
            print("\n开始解析目录...")
        
        # 解析目录
        chapters = await parser.parse(url)
        
        # 统计信息
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
        
        # 检查重复编号
        duplicates = {k: v for k, v in number_distribution.items() if v > 1}
        
        result.update({
            "success": True,
            "stats": {
                "total_chapters": len(chapters),
                "chapters_with_numbers": chapters_with_numbers,
                "chapters_without_numbers": chapters_without_numbers,
                "duplicate_numbers": duplicates,
                "total_duplicates": sum(v - 1 for v in duplicates.values()),
                "parsing_time": round(time.time() - start_time, 2)
            },
            "chapters": [
                {
                    "order": chapter.order,
                    "title": chapter.title,
                    "url": chapter.url,
                    "chapter_number": parser._extract_chapter_number(chapter.title)
                }
                for chapter in chapters
            ]
        })
        
        if detailed:
            print(f"\n=== 解析结果 ===")
            print(f"总章节数: {len(chapters)}")
            print(f"有编号章节: {chapters_with_numbers}")
            print(f"无编号章节: {chapters_without_numbers}")
            print(f"解析耗时: {result['stats']['parsing_time']}秒")
            
            if duplicates:
                print(f"重复编号: {duplicates}")
            else:
                print("无重复编号")
            
            if chapters:
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
            else:
                print("未获取到任何章节！")
            
            print(f"\n=== 测试完成 ===")
        
    except Exception as e:
        result.update({
            "success": False,
            "error": str(e),
            "stats": {
                "parsing_time": round(time.time() - start_time, 2)
            }
        })
        
        if detailed:
            print(f"测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return result


async def batch_test(test_cases: List[Dict[str, Any]], output_file: str = None):
    """批量测试多个书源"""
    print("\n批量测试开始")
    print("=" * 50)
    
    results = []
    total_start_time = time.time()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] 测试: {test_case.get('description', '未知')}")
        
        result = await test_toc_parsing(
            test_case['source_id'],
            test_case['url'],
            detailed=False  # 批量测试时简化输出
        )
        
        results.append(result)
        
        # 简化输出
        status = "✅ 成功" if result['success'] else "❌ 失败"
        chapters_count = result['stats'].get('total_chapters', 0)
        parsing_time = result['stats'].get('parsing_time', 0)
        
        print(f"   {status} | 章节数: {chapters_count:3d} | 耗时: {parsing_time:5.2f}s")
        
        if not result['success']:
            print(f"   错误: {result['error']}")
    
    total_time = time.time() - total_start_time
    
    # 生成汇总报告
    print(f"\n批量测试完成 (总耗时: {total_time:.2f}秒)")
    print("=" * 50)
    
    successful_tests = [r for r in results if r['success']]
    failed_tests = [r for r in results if not r['success']]
    
    print(f"总测试数: {len(results)}")
    print(f"成功: {len(successful_tests)}")
    print(f"失败: {len(failed_tests)}")
    
    if successful_tests:
        total_chapters = sum(r['stats']['total_chapters'] for r in successful_tests)
        avg_chapters = total_chapters / len(successful_tests)
        avg_time = sum(r['stats']['parsing_time'] for r in successful_tests) / len(successful_tests)
        
        print(f"平均章节数: {avg_chapters:.1f}")
        print(f"平均解析时间: {avg_time:.2f}秒")
    
    if failed_tests:
        print(f"\n失败的测试:")
        for result in failed_tests:
            print(f"  - 书源{result['source_id']}: {result['error']}")
    
    # 保存详细结果到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total_tests": len(results),
                    "successful_tests": len(successful_tests),
                    "failed_tests": len(failed_tests),
                    "total_time": total_time,
                    "average_chapters": avg_chapters if successful_tests else 0,
                    "average_time": avg_time if successful_tests else 0
                },
                "results": results
            }, f, ensure_ascii=False, indent=2)
        print(f"\n详细结果已保存到: {output_file}")


async def main():
    """主函数"""
    # 默认测试用例
    default_test_cases = [
        {
            "source_id": 4,
            "url": "http://wap.99xs.info/124310/",
            "description": "书源4 - 鸟书网测试"
        }
    ]
    
    # 扩展测试用例（如果有更多书源）
    extended_test_cases = [
        {
            "source_id": 4,
            "url": "http://wap.99xs.info/124310/",
            "description": "书源4 - 鸟书网 - 测试小说1"
        },
        # 可以添加更多测试用例
        # {
        #     "source_id": 1,
        #     "url": "http://example.com/book/123/",
        #     "description": "书源1 - 示例网站"
        # },
    ]
    
    print("目录解析测试工具")
    print("================")
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print("使用方法:")
            print("  python test_toc_parsing.py                           # 运行默认测试")
            print("  python test_toc_parsing.py <source_id> <url>         # 测试指定书源和URL")
            print("  python test_toc_parsing.py --batch                   # 批量测试")
            print("  python test_toc_parsing.py --batch --output <file>   # 批量测试并保存结果")
            print("")
            print("示例:")
            print("  python test_toc_parsing.py 4 'http://wap.99xs.info/124310/'")
            print("  python test_toc_parsing.py --batch --output results.json")
            return
        
        elif sys.argv[1] == "--batch":
            # 批量测试模式
            output_file = None
            if "--output" in sys.argv:
                output_index = sys.argv.index("--output")
                if output_index + 1 < len(sys.argv):
                    output_file = sys.argv[output_index + 1]
            
            await batch_test(extended_test_cases, output_file)
            return
        
        elif len(sys.argv) >= 3:
            # 单个测试
            try:
                source_id = int(sys.argv[1])
                url = sys.argv[2]
                await test_toc_parsing(source_id, url)
                return
            except ValueError:
                print("错误: source_id 必须是数字")
                sys.exit(1)
    
    # 运行默认测试用例
    for test_case in default_test_cases:
        await test_toc_parsing(
            test_case["source_id"], 
            test_case["url"]
        )
        print("\n" + "="*50)


if __name__ == "__main__":
    asyncio.run(main())