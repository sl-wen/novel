import asyncio
import aiohttp
import logging
from typing import Optional
from bs4 import BeautifulSoup

from app.models.book import Book
from app.core.source import Source
from app.core.config import settings

logger = logging.getLogger(__name__)


class BookParser:
    """书籍详情解析器，用于解析小说详情页面"""
    
    def __init__(self, source: Source):
        """初始化书籍详情解析器
        
        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("book", {}).get("timeout", settings.DEFAULT_TIMEOUT)
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", "")
        }
        self.book_rule = source.rule.get("book", {})

    async def parse(self, url: str) -> Optional[Book]:
        """解析书籍详情
        
        Args:
            url: 书籍详情页URL
            
        Returns:
            书籍详情对象，失败返回None
        """
        try:
            # 发送请求获取书籍详情页面
            html = await self._fetch_html_with_retry(url)
            if not html:
                logger.error(f"从书源 {self.source.rule.get('name', self.source.id)} 获取书籍详情失败: {url}")
                return None
            
            # 解析书籍详情
            book = self._parse_book_detail(html, url)
            
            return book
        except Exception as e:
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 解析书籍详情异常: {str(e)}")
            return None

    async def _fetch_html_with_retry(self, url: str) -> Optional[str]:
        """带重试机制的获取HTML页面
        
        Args:
            url: 页面URL
            
        Returns:
            HTML页面内容，失败返回None
        """
        for attempt in range(settings.REQUEST_RETRY_TIMES):
            try:
                result = await self._fetch_html(url)
                if result:
                    return result
                
                if attempt == 0:
                    logger.warning(f"第一次请求失败，准备重试: {url}")
                    
            except Exception as e:
                if attempt < settings.REQUEST_RETRY_TIMES - 1:
                    logger.warning(f"请求失败（第 {attempt + 1} 次），{settings.REQUEST_RETRY_DELAY} 秒后重试: {str(e)}")
                    await asyncio.sleep(settings.REQUEST_RETRY_DELAY)
                else:
                    logger.error(f"请求最终失败（共 {settings.REQUEST_RETRY_TIMES} 次尝试）: {str(e)}")
        
        return None
    
    async def _fetch_html(self, url: str) -> Optional[str]:
        """获取HTML页面
        
        Args:
            url: 页面URL
            
        Returns:
            HTML页面内容，失败返回None
        """
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=aiohttp.TCPConnector(limit=settings.MAX_CONCURRENT_REQUESTS)
            ) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.error(f"请求失败: {url}, 状态码: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"请求超时: {url}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP客户端错误: {url}, 错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 获取书籍详情失败: {url}, 错误: {str(e)}")
            return None
    def _parse_book_detail(self, html: str, url: str) -> Book:
        """解析书籍详情
        
        Args:
            html: HTML页面内容
            url: 书籍详情页URL
            
        Returns:
            书籍详情对象
        """
        try:
            # 获取书籍详情规则
            name_selector = self.book_rule.get("name", "")
            author_selector = self.book_rule.get("author", "")
            intro_selector = self.book_rule.get("intro", "")
            category_selector = self.book_rule.get("category", "")
            cover_selector = self.book_rule.get("cover", "")
            latest_selector = self.book_rule.get("latest", "")
            update_selector = self.book_rule.get("update", "")
            status_selector = self.book_rule.get("status", "")
            word_count_selector = self.book_rule.get("word_count", "")
            
            # 解析HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # 获取书名
            book_name = ""
            if name_selector:
                name_element = soup.select_one(name_selector)
                if name_element:
                    # 如果是meta标签，获取content属性
                    if name_element.name == 'meta':
                        book_name = name_element.get("content", "").strip()
                    else:
                        book_name = name_element.get_text().strip()
            
            # 获取作者
            author = ""
            if author_selector:
                author_element = soup.select_one(author_selector)
                if author_element:
                    if author_element.name == 'meta':
                        author = author_element.get("content", "").strip()
                    else:
                        author = author_element.get_text().strip()
            
            # 获取简介
            intro = ""
            if intro_selector:
                intro_element = soup.select_one(intro_selector)
                if intro_element:
                    if intro_element.name == 'meta':
                        intro = intro_element.get("content", "").strip()
                    else:
                        intro = intro_element.get_text().strip()
            
            # 获取分类
            category = ""
            if category_selector:
                category_element = soup.select_one(category_selector)
                if category_element:
                    if category_element.name == 'meta':
                        category = category_element.get("content", "").strip()
                    else:
                        category = category_element.get_text().strip()
            
            # 获取封面
            cover_url = ""
            if cover_selector:
                cover_element = soup.select_one(cover_selector)
                if cover_element:
                    if cover_element.name == 'meta':
                        cover_url = cover_element.get("content", "").strip()
                    else:
                        cover_url = cover_element.get("src", "")
                        
                    if cover_url and not cover_url.startswith("http"):
                        base_uri = self.source.rule.get("url", "")
                        cover_url = f"{base_uri.rstrip('/')}/{cover_url.lstrip('/')}"
            
            # 获取最新章节
            latest_chapter = ""
            if latest_selector:
                latest_element = soup.select_one(latest_selector)
                if latest_element:
                    latest_chapter = latest_element.get_text().strip()
            
            # 获取更新时间
            update_time = ""
            if update_selector:
                update_element = soup.select_one(update_selector)
                if update_element:
                    update_time = update_element.get_text().strip()
            
            # 获取状态
            status = ""
            if status_selector:
                status_element = soup.select_one(status_selector)
                if status_element:
                    status = status_element.get_text().strip()
            
            # 获取字数
            word_count = ""
            if word_count_selector:
                word_count_element = soup.select_one(word_count_selector)
                if word_count_element:
                    word_count = word_count_element.get_text().strip()
            
            # 创建并返回Book对象
            return Book(
                url=url,
                bookName=book_name or "未知书名",
                author=author or None,
                intro=intro or None,
                category=category or None,
                coverUrl=cover_url or None,
                latestChapter=latest_chapter or None,
                lastUpdateTime=update_time or None,
                status=status or None,
                wordCount=word_count or None
            )
        except Exception as e:
            logger.error(f"解析书籍详情异常: {str(e)}")
            # 返回基础的Book对象
            return Book(
                url=url,
                bookName="解析失败",
                author=None,
                intro="书籍信息解析失败",
                category=None,
                coverUrl=None,
                latestChapter=None,
                lastUpdateTime=None,
                status=None,
                wordCount=None
            )