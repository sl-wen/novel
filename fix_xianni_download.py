#!/usr/bin/env python3
"""
《仙逆》下载问题修复脚本
专门解决章节获取失败和内容不正确的问题
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.source import Source
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.parsers.book_parser import BookParser
from app.parsers.chapter_parser import ChapterParser
from app.parsers.toc_parser import TocParser

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XianNiDownloader:
    """《仙逆》专用下载器"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def fetch_html(self, url: str, retries: int = 3) -> Optional[str]:
        """获取HTML内容"""
        for attempt in range(retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content
                    else:
                        logger.warning(f"HTTP {response.status}: {url}")
                        
            except Exception as e:
                logger.warning(f"请求失败 (第{attempt + 1}次): {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    
        return None
    
    async def get_book_info(self, url: str) -> Optional[Book]:
        """获取书籍信息"""
        html = await self.fetch_html(url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 尝试多种选择器获取书名
        title_selectors = [
            "meta[property='og:novel:book_name']",
            "meta[name='og:novel:book_name']",
            "h1",
            ".bookname h1",
            "#info h1",
            ".book-title",
        ]
        
        title = None
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True) or element.get("content", "")
                if title:
                    break
        
        # 尝试多种选择器获取作者
        author_selectors = [
            "meta[property='og:novel:author']",
            "meta[name='og:novel:author']",
            "#info p:first-child",
            ".book-author",
            "p:contains('作者')",
        ]
        
        author = None
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get_text(strip=True) or element.get("content", "")
                if author:
                    break
        
        # 尝试多种选择器获取简介
        intro_selectors = [
            "meta[property='og:description']",
            "meta[name='og:description']",
            "#intro",
            ".book-intro",
            ".intro",
        ]
        
        intro = None
        for selector in intro_selectors:
            element = soup.select_one(selector)
            if element:
                intro = element.get_text(strip=True) or element.get("content", "")
                if intro:
                    break
        
        return Book(
            title=title or "仙逆",
            author=author or "耳根",
            intro=intro or "",
            url=url
        )
    
    async def get_toc(self, url: str) -> List[ChapterInfo]:
        """获取目录"""
        html = await self.fetch_html(url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 尝试多种目录选择器
        toc_selectors = [
            "#list dd a",
            ".listmain dd a",
            "#chapter-list a",
            ".chapter-list a",
            "dl dd a",
            ".list a",
        ]
        
        chapters = []
        for selector in toc_selectors:
            links = soup.select(selector)
            if links:
                for i, link in enumerate(links, 1):
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    
                    if title and href:
                        # 处理相对URL
                        if href.startswith("/"):
                            base_url = "/".join(url.split("/")[:3])
                            full_url = base_url + href
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            full_url = url.rstrip("/") + "/" + href.lstrip("/")
                        
                        chapters.append(ChapterInfo(
                            title=title,
                            url=full_url,
                            order=i
                        ))
                
                if chapters:
                    logger.info(f"找到 {len(chapters)} 章")
                    break
        
        return chapters
    
    async def get_chapter_content(self, url: str, title: str) -> Optional[Chapter]:
        """获取章节内容"""
        html = await self.fetch_html(url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 尝试多种内容选择器
        content_selectors = [
            "#content",
            ".content",
            ".chapter-content",
            "#chapter-content",
            ".text",
            "#text",
        ]
        
        content = None
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator="\n", strip=True)
                if content and len(content) > 100:  # 确保内容足够长
                    break
        
        if not content:
            return None
        
        # 清理内容
        content = self._clean_content(content)
        
        return Chapter(
            title=title,
            content=content,
            url=url,
            order=0
        )
    
    def _clean_content(self, content: str) -> str:
        """清理章节内容"""
        if not content:
            return ""
        
        # 移除广告和垃圾内容
        ad_patterns = [
            r"一秒记住【.+?】",
            r"天才一秒记住.+?",
            r"天才壹秒記住.+?",
            r"看最新章节请到.+?",
            r"本书最新章节请到.+?",
            r"更新最快的.+?",
            r"手机用户请访问.+?",
            r"手机版阅读网址.+?",
            r"推荐都市大神.+?",
            r"\(本章完\)",
            r"章节错误.+?举报",
            r"内容严重缺失.+?举报",
            r"笔趣阁.+?",
            r"新笔趣阁.+?",
            r"香书小说.+?",
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)
        
        # 移除多余空行
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)
        
        # 移除行首行尾空格
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        
        return "\n".join(lines)
    
    async def download_xianni(self, url: str, output_file: str = None) -> str:
        """下载《仙逆》"""
        print(f"开始下载《仙逆》: {url}")
        
        # 获取书籍信息
        book = await self.get_book_info(url)
        if not book:
            raise Exception("无法获取书籍信息")
        
        print(f"✅ 书籍信息: {book.title} - {book.author}")
        
        # 获取目录
        toc = await self.get_toc(url)
        if not toc:
            raise Exception("无法获取目录")
        
        print(f"✅ 目录获取: {len(toc)} 章")
        
        # 设置输出文件
        if not output_file:
            output_file = f"仙逆_{book.author}.txt"
        
        # 下载章节内容
        print("开始下载章节内容...")
        chapters = []
        failed_chapters = []
        
        for i, chapter_info in enumerate(toc, 1):
            print(f"下载第 {i}/{len(toc)} 章: {chapter_info.title}")
            
            try:
                chapter = await self.get_chapter_content(chapter_info.url, chapter_info.title)
                if chapter and len(chapter.content) > 50:
                    chapters.append(chapter)
                    print(f"  ✅ 成功 ({len(chapter.content)} 字符)")
                else:
                    failed_chapters.append(chapter_info.title)
                    print(f"  ❌ 失败 (内容过短或无内容)")
            except Exception as e:
                failed_chapters.append(chapter_info.title)
                print(f"  ❌ 失败: {str(e)}")
            
            # 添加延迟避免被封
            await asyncio.sleep(1)
        
        print(f"\n下载完成: 成功 {len(chapters)} 章，失败 {len(failed_chapters)} 章")
        
        if failed_chapters:
            print("失败的章节:")
            for title in failed_chapters[:10]:  # 只显示前10个
                print(f"  - {title}")
        
        # 生成TXT文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"书名: {book.title}\n")
            f.write(f"作者: {book.author}\n")
            f.write(f"简介: {book.intro}\n")
            f.write(f"分类: 仙侠小说\n")
            f.write(f"最新章节: \n")
            f.write(f"更新时间: \n")
            f.write(f"状态: 已完结\n")
            f.write(f"字数: \n")
            f.write("\n" + "=" * 50 + "\n\n")
            
            for chapter in chapters:
                f.write(f"\n\n{chapter.title}\n\n")
                f.write(chapter.content)
        
        print(f"✅ 文件生成成功: {output_file}")
        print(f"   文件大小: {os.path.getsize(output_file)} 字节")
        
        return output_file


async def main():
    """主函数"""
    print("《仙逆》专用下载器")
    print("=" * 50)
    
    # 预设的《仙逆》URL列表
    xianni_urls = [
        "http://www.xbiqugu.la/0_1/",
        "https://www.xbiquge.la/0_1/",
        "https://www.biquge.com.cn/book/1/",
        "https://www.biquge.tv/0_1/",
    ]
    
    print("可用的《仙逆》URL:")
    for i, url in enumerate(xianni_urls, 1):
        print(f"{i}. {url}")
    
    print("\n请选择URL (输入数字) 或直接输入URL:")
    choice = input("选择: ").strip()
    
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(xianni_urls):
            url = xianni_urls[idx]
        else:
            print("❌ 无效选择")
            return
    else:
        url = choice
    
    async with XianNiDownloader() as downloader:
        try:
            output_file = await downloader.download_xianni(url)
            print(f"\n🎉 下载完成: {output_file}")
        except Exception as e:
            print(f"❌ 下载失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())