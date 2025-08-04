#!/usr/bin/env python3
"""
测试改进后的下载功能
验证并发控制、重试机制和错误处理
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.novel_service import NovelService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_download():
    """测试下载功能"""
    print("=" * 60)
    print("测试改进后的下载功能")
    print("=" * 60)
    
    novel_service = NovelService()
    
    # 测试用的URL列表
    test_urls = [
        "http://www.xbiqugu.la/0_1/",  # 仙逆
        "https://www.biquge.com.cn/book/1/",  # 仙逆
        "https://www.xbiquge.la/0_1/",  # 仙逆
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n测试 {i}: {url}")
        print("-" * 40)
        
        try:
            # 测试下载
            print("开始下载...")
            file_path = await novel_service.download(url, 1, "txt")
            
            if file_path and Path(file_path).exists():
                # 检查文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                print(f"✅ 下载成功: {file_path}")
                print(f"   文件大小: {len(content)} 字符")
                
                # 统计章节数
                chapter_count = content.count("第") + content.count("章")
                print(f"   估计章节数: {chapter_count}")
                
                # 检查内容质量
                if len(content) > 10000:
                    print("   ✅ 内容质量良好")
                else:
                    print("   ⚠️  内容可能不完整")
                    
            else:
                print("❌ 下载失败或文件不存在")
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            
        print("\n" + "=" * 60)


async def test_specific_book():
    """测试特定书籍的下载"""
    print("\n" + "=" * 60)
    print("测试特定书籍下载")
    print("=" * 60)
    
    novel_service = NovelService()
    
    # 让用户输入URL
    url = input("请输入要测试的小说URL: ").strip()
    
    if not url:
        print("❌ 未提供URL")
        return
    
    try:
        print(f"\n开始下载: {url}")
        
        # 获取书籍详情
        book = await novel_service.get_book_detail(url, 1)
        print(f"✅ 书籍信息: {book.title} - {book.author}")
        
        # 获取目录
        toc = await novel_service.get_toc(url, 1)
        print(f"✅ 目录获取: {len(toc)} 章")
        
        if len(toc) < 10:
            print("⚠️  警告: 章节数较少")
        
        # 下载
        file_path = await novel_service.download(url, 1, "txt")
        
        if file_path and Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"✅ 下载完成: {file_path}")
            print(f"   文件大小: {len(content)} 字符")
            print(f"   章节数: {content.count('第') + content.count('章')}")
            
        else:
            print("❌ 下载失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")


async def main():
    """主函数"""
    print("改进后的下载功能测试")
    print("请选择测试模式:")
    print("1. 自动测试多个URL")
    print("2. 测试特定书籍")
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        await test_download()
    elif choice == "2":
        await test_specific_book()
    else:
        print("无效选择")


if __name__ == "__main__":
    asyncio.run(main())