import asyncio
import aiohttp
from typing import Optional
from bs4 import BeautifulSoup

from app.models.book import Book
from app.core.source import Source
from app.core.config import settings


class BookParser:
    """书籍详情解析器，用于解析小说详情页面"""
    
    def __init__(self, source: Source):
        """初始化书籍详情解析器
        
        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.book_timeout or settings.DEFAULT_TIMEOUT
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.base_uri
        }
    
    async def parse(self, url: str) -> Optional[Book]:
        """解析书籍详情
        
        Args:
            url: 书籍详情页URL
            
        Returns:
            书籍详情对象，失败返回None
        """
        # 发送请求获取书籍详情页面
        html = await self._fetch_html(url)
        if not html:
            print(f"<== 从 {self.source.name} 获取书籍详情失败: {url}")
            return None
        
        # 解析书籍详情
        book = self._parse_book_detail(html, url)
        
        return book
    
    async def _fetch_html(self, url: str) -> Optional[str]:
        """获取HTML页面
        
        Args:
            url: 页面URL
            
        Returns:
            HTML页面内容，失败返回None
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        print(f"<== 请求失败: {url}, 状态码: {response.status}")
                        return None
        except Exception as e:
            # print(f"<== 从 {self.source.name} 获取书籍详情失败: {url}") # 移除旧的打印语句
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 获取书籍详情失败: {url}, 错误: {str(e)}") # 添加日志
            return None

    async def parse(self, url: str) -> Optional[Book]:
        """解析书籍详情
        
        Args:
            url: 书籍详情页URL
            
        Returns:
            书籍详情对象，失败返回None
        """
        # 发送请求获取书籍详情页面
        html = await self._fetch_html(url)
        if not html:
            print(f"<== 从 {self.source.name} 获取书籍详情失败: {url}")
            return None
        
        # 解析书籍详情
        book = self._parse_book_detail(html, url)
        
        return book
    
    def _parse_book_detail(self, html: str, url: str) -> Book:
        """解析书籍详情
        
        Args:
            html: HTML页面内容
            url: 书籍详情页URL
            
        Returns:
            书籍详情对象
        """
        # 获取书籍详情规则
        name_selector = self.source.book_rule.get("name", "")
        author_selector = self.source.book_rule.get("author", "")
        intro_selector = self.source.book_rule.get("intro", "")
        category_selector = self.source.book_rule.get("category", "")
        cover_selector = self.source.book_rule.get("cover", "")
        latest_selector = self.source.book_rule.get("latest", "")
        update_selector = self.source.book_rule.get("update", "")
        status_selector = self.source.book_rule.get("status", "")
        word_count_selector = self.source.book_rule.get("word_count", "")
        
        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # 获取书名
        book_name = ""
        if name_selector:
            name_element = soup.select_one(name_selector)
            if name_element:
                book_name = name_element.get_text().strip()
        
        # 获取作者
        author = ""
        if author_selector:
            author_element = soup.select_one(author_selector)
            if author_element:
                author = author_element.get_text().strip()
                # 移除