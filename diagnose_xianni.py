#!/usr/bin/env python3
"""
《仙逆》下载问题诊断脚本
用于分析章节获取失败和内容不正确的问题
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.source import Source
from app.models.book import Book
from app.models.chapter import ChapterInfo
from app.parsers.book_parser import BookParser
from app.parsers.chapter_parser import ChapterParser
from app.parsers.toc_parser import TocParser
from app.services.novel_service import NovelService

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def diagnose_xianni():
    """诊断《仙逆》下载问题"""
    print("=" * 60)
    print("《仙逆》下载问题诊断")
    print("=" * 60)
    
    # 初始化服务
    novel_service = NovelService()
    
    # 测试用的《仙逆》URL（需要根据实际情况调整）
    test_urls = [
        "http://www.xbiqugu.la/0_1/",  # 香书小说
        "https://www.biquge.com.cn/book/1/",  # 笔趣阁
        "https://www.xbiquge.la/0_1/",  # 新笔趣阁
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n测试书源 {i}: {url}")
        print("-" * 40)
        
        try:
            # 测试书源1
            source = novel_service.sources.get(1)
            if not source:
                print("❌ 书源1未找到")
                continue
                
            print(f"✅ 使用书源: {source.rule.get('name', '未知')}")
            
            # 测试获取书籍详情
            print("\n1. 测试获取书籍详情...")
            try:
                book_parser = BookParser(source)
                book = await book_parser.parse(url)
                print(f"✅ 书籍详情获取成功:")
                print(f"   书名: {book.title}")
                print(f"   作者: {book.author}")
                print(f"   简介: {book.intro[:100]}..." if book.intro else "   简介: 无")
            except Exception as e:
                print(f"❌ 书籍详情获取失败: {str(e)}")
                continue
            
            # 测试获取目录
            print("\n2. 测试获取目录...")
            try:
                toc_parser = TocParser(source)
                toc = await toc_parser.parse(url)
                print(f"✅ 目录获取成功，共 {len(toc)} 章")
                
                if len(toc) < 10:
                    print(f"⚠️  警告: 章节数较少 ({len(toc)} 章)")
                
                # 显示前5章信息
                print("   前5章:")
                for i, chapter in enumerate(toc[:5], 1):
                    print(f"   {i}. {chapter.title}")
                    
            except Exception as e:
                print(f"❌ 目录获取失败: {str(e)}")
                continue
            
            # 测试获取章节内容
            print("\n3. 测试获取章节内容...")
            if toc:
                test_chapter = toc[0]  # 测试第一章
                try:
                    chapter_parser = ChapterParser(source)
                    chapter = await chapter_parser.parse(
                        test_chapter.url, 
                        test_chapter.title, 
                        test_chapter.order
                    )
                    
                    print(f"✅ 章节内容获取成功:")
                    print(f"   标题: {chapter.title}")
                    print(f"   内容长度: {len(chapter.content)} 字符")
                    print(f"   内容预览: {chapter.content[:200]}...")
                    
                    if len(chapter.content) < 100:
                        print(f"⚠️  警告: 章节内容过短 ({len(chapter.content)} 字符)")
                        
                except Exception as e:
                    print(f"❌ 章节内容获取失败: {str(e)}")
                    
            # 测试下载功能
            print("\n4. 测试下载功能...")
            try:
                file_path = await novel_service.download(url, 1, "txt")
                print(f"✅ 下载成功: {file_path}")
                
                # 检查文件内容
                if Path(file_path).exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(f"   文件大小: {len(content)} 字符")
                        print(f"   文件内容预览:")
                        print(f"   {content[:500]}...")
                        
                        # 统计章节数
                        chapter_count = content.count("第") + content.count("章")
                        print(f"   估计章节数: {chapter_count}")
                        
            except Exception as e:
                print(f"❌ 下载失败: {str(e)}")
                
        except Exception as e:
            print(f"❌ 整体测试失败: {str(e)}")
            
        print("\n" + "=" * 60)


async def test_specific_url():
    """测试特定的《仙逆》URL"""
    print("\n" + "=" * 60)
    print("测试特定URL")
    print("=" * 60)
    
    # 这里需要您提供具体的《仙逆》URL
    specific_url = input("请输入《仙逆》的具体URL: ").strip()
    
    if not specific_url:
        print("❌ 未提供URL")
        return
        
    novel_service = NovelService()
    
    try:
        print(f"\n测试URL: {specific_url}")
        
        # 获取书籍详情
        book = await novel_service.get_book_detail(specific_url, 1)
        print(f"✅ 书籍详情: {book.title} - {book.author}")
        
        # 获取目录
        toc = await novel_service.get_toc(specific_url, 1)
        print(f"✅ 目录获取: {len(toc)} 章")
        
        # 测试前3章内容
        for i, chapter_info in enumerate(toc[:3], 1):
            print(f"\n测试第{i}章: {chapter_info.title}")
            try:
                chapter = await novel_service.get_chapter_content(chapter_info.url, 1)
                print(f"   内容长度: {len(chapter.content)} 字符")
                if len(chapter.content) < 100:
                    print(f"   ⚠️  内容过短")
            except Exception as e:
                print(f"   ❌ 获取失败: {str(e)}")
                
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")


async def main():
    """主函数"""
    print("《仙逆》下载问题诊断工具")
    print("请选择诊断模式:")
    print("1. 自动测试多个书源")
    print("2. 测试特定URL")
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        await diagnose_xianni()
    elif choice == "2":
        await test_specific_url()
    else:
        print("无效选择")


if __name__ == "__main__":
    asyncio.run(main())