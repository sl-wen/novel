#!/usr/bin/env python3
"""
完整系统测试脚本
验证所有改进功能：并发控制、重试机制、内容验证、监控等
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.novel_service import NovelService
from app.utils.content_validator import ContentValidator, ChapterValidator
from app.utils.download_monitor import DownloadMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_content_validator():
    """测试内容验证器"""
    print("=" * 60)
    print("测试内容验证器")
    print("=" * 60)
    
    validator = ContentValidator()
    
    # 测试用例
    test_cases = [
        {
            "name": "正常内容",
            "content": "这是一个正常的章节内容。\n\n第二段内容也很正常。\n\n第三段内容同样正常。",
            "expected": True
        },
        {
            "name": "内容过短",
            "content": "内容太短",
            "expected": False
        },
        {
            "name": "包含广告",
            "content": "这是正常内容。\n\n一秒记住【文学巴士】，精彩无弹窗免费阅读！\n\n更多正常内容。",
            "expected": False
        },
        {
            "name": "包含错误信息",
            "content": "获取章节内容失败",
            "expected": False
        },
        {
            "name": "空内容",
            "content": "",
            "expected": False
        }
    ]
    
    for case in test_cases:
        is_valid, error_msg = validator.validate_chapter_content(case["content"])
        status = "✅" if is_valid == case["expected"] else "❌"
        print(f"{status} {case['name']}: {is_valid} - {error_msg}")
    
    print()


async def test_download_monitor():
    """测试下载监控器"""
    print("=" * 60)
    print("测试下载监控器")
    print("=" * 60)
    
    monitor = DownloadMonitor()
    
    # 模拟下载过程
    monitor.start_download(10)
    
    # 模拟章节下载
    monitor.chapter_started("第1章", "http://example.com/1")
    await asyncio.sleep(0.1)
    monitor.chapter_completed("第1章", 1000, 0.9)
    
    monitor.chapter_started("第2章", "http://example.com/2")
    await asyncio.sleep(0.1)
    monitor.chapter_failed("第2章", "网络错误")
    
    monitor.chapter_started("第3章", "http://example.com/3")
    await asyncio.sleep(0.1)
    monitor.chapter_completed("第3章", 800, 0.7)
    
    # 获取统计信息
    stats = monitor.get_detailed_stats()
    
    print("下载统计:")
    print(f"  总章节: {stats['progress']['total_chapters']}")
    print(f"  成功: {stats['progress']['completed_chapters']}")
    print(f"  失败: {stats['progress']['failed_chapters']}")
    print(f"  成功率: {stats['progress']['success_rate']:.1f}%")
    print(f"  平均质量评分: {stats['quality']['average_quality_score']:.2f}")
    
    print()
    print("最终报告:")
    print(monitor.get_final_report())
    print()


async def test_chapter_validator():
    """测试章节验证器"""
    print("=" * 60)
    print("测试章节验证器")
    print("=" * 60)
    
    validator = ChapterValidator()
    
    # 测试质量评分
    test_contents = [
        ("高质量内容", "这是一个高质量的章节内容。\n\n包含多个段落，内容丰富。\n\n有合理的中文字符和标点符号。\n\n内容结构完整，没有广告。"),
        ("低质量内容", "内容很短。"),
        ("包含广告", "正常内容。\n\n一秒记住【文学巴士】。\n\n更多内容。"),
    ]
    
    for title, content in test_contents:
        is_valid, error_msg = validator.validate_chapter(title, content)
        quality_score = validator.get_chapter_quality_score(content)
        
        status = "✅" if is_valid else "❌"
        print(f"{status} {title}:")
        print(f"  有效性: {is_valid}")
        print(f"  质量评分: {quality_score:.2f}")
        print(f"  错误信息: {error_msg}")
        print()
    
    print()


async def test_complete_download():
    """测试完整下载流程"""
    print("=" * 60)
    print("测试完整下载流程")
    print("=" * 60)
    
    novel_service = NovelService()
    
    # 测试用的URL
    test_urls = [
        "http://www.xbiqugu.la/0_1/",  # 测试小说1
        "https://www.biquge.com.cn/book/1/",  # 测试小说2
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n测试 {i}: {url}")
        print("-" * 40)
        
        try:
            print("开始下载...")
            start_time = time.time()
            
            file_path = await novel_service.download(url, 1, "txt")
            
            end_time = time.time()
            duration = end_time - start_time
            
            if file_path and Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                print(f"✅ 下载完成: {file_path}")
                print(f"   耗时: {duration:.1f}秒")
                print(f"   文件大小: {len(content)} 字符")
                print(f"   章节数: {content.count('第') + content.count('章')}")
                
                # 分析内容质量
                validator = ContentValidator()
                stats = validator.get_content_stats(content)
                print(f"   中文字符: {stats['chinese_chars']}")
                print(f"   段落数: {stats['paragraphs']}")
                print(f"   广告比例: {stats['ad_ratio']:.1%}")
                
            else:
                print("❌ 下载失败或文件不存在")
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            
        print("\n" + "=" * 60)


async def test_system_performance():
    """测试系统性能"""
    print("=" * 60)
    print("测试系统性能")
    print("=" * 60)
    
    novel_service = NovelService()
    
    # 测试并发性能
    print("测试并发下载性能...")
    
    # 获取一个简单的目录进行测试
    try:
        url = "http://www.xbiqugu.la/0_1/"  # 使用测试URL
        toc = await novel_service.get_toc(url, 1)
        
        if toc:
            # 只测试前10章
            test_toc = toc[:10]
            print(f"测试前 {len(test_toc)} 章...")
            
            start_time = time.time()
            chapters = await novel_service._download_chapters_with_retry(test_toc, novel_service.sources[1])
            end_time = time.time()
            
            duration = end_time - start_time
            success_count = len([c for c in chapters if c and len(c.content) > 50])
            
            print(f"✅ 性能测试完成:")
            print(f"   总耗时: {duration:.1f}秒")
            print(f"   成功章节: {success_count}/{len(test_toc)}")
            print(f"   平均每章: {duration/len(test_toc):.1f}秒")
            print(f"   成功率: {success_count/len(test_toc)*100:.1f}%")
            
        else:
            print("❌ 无法获取目录")
            
    except Exception as e:
        print(f"❌ 性能测试失败: {str(e)}")
    
    print()


async def main():
    """主函数"""
    print("完整系统测试")
    print("=" * 60)
    
    print("请选择测试模式:")
    print("1. 测试内容验证器")
    print("2. 测试下载监控器")
    print("3. 测试章节验证器")
    print("4. 测试完整下载流程")
    print("5. 测试系统性能")
    print("6. 运行所有测试")
    
    choice = input("请选择 (1-6): ").strip()
    
    if choice == "1":
        await test_content_validator()
    elif choice == "2":
        await test_download_monitor()
    elif choice == "3":
        await test_chapter_validator()
    elif choice == "4":
        await test_complete_download()
    elif choice == "5":
        await test_system_performance()
    elif choice == "6":
        print("运行所有测试...")
        await test_content_validator()
        await test_download_monitor()
        await test_chapter_validator()
        await test_system_performance()
        await test_complete_download()
    else:
        print("无效选择")


if __name__ == "__main__":
    asyncio.run(main())