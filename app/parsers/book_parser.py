import asyncio
import logging
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.book import Book

logger = logging.getLogger(__name__)


class BookParser:
    """书籍详情解析器，用于解析小说详情页面"""

    def __init__(self, source: Source):
        """初始化书籍详情解析器

        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("book", {}).get(
            "timeout", settings.DEFAULT_TIMEOUT
        )
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", ""),
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
                logger.error(
                    f"从书源 {self.source.rule.get('name', self.source.id)} "
                    f"获取书籍详情失败: {url}"
                )
                return None

            # 解析书籍详情
            book = self._parse_book_detail(html, url)

            return book
        except Exception as e:
            logger.error(
                f"书源 {self.source.rule.get('name', self.source.id)} "
                f"解析书籍详情异常: {str(e)}"
            )
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
                    logger.warning(
                        f"请求失败（第 {attempt + 1} 次），"
                        f"{settings.REQUEST_RETRY_DELAY} 秒后重试: {str(e)}"
                    )
                    await asyncio.sleep(settings.REQUEST_RETRY_DELAY)
                else:
                    logger.error(
                        f"请求最终失败（共 {settings.REQUEST_RETRY_TIMES} 次尝试）: "
                        f"{str(e)}"
                    )

        return None

    async def _fetch_html(self, url: str) -> Optional[str]:
        """获取HTML页面

        Args:
            url: 页面URL

        Returns:
            HTML页面内容，失败返回None
        """
        try:
            # 创建SSL上下文，跳过证书验证
            connector = aiohttp.TCPConnector(
                limit=settings.MAX_CONCURRENT_REQUESTS,
                ssl=False,  # 跳过SSL证书验证
                use_dns_cache=True,
                ttl_dns_cache=300,
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=10,
                sock_read=30
            )
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self.headers
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.error(f"请求失败: {url}, 状态码: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"请求异常: {url}, 错误: {str(e)}")
            return None

    def _parse_book_detail(self, html: str, url: str) -> Book:
        """解析书籍详情

        Args:
            html: HTML页面内容
            url: 页面URL

        Returns:
            书籍详情对象
        """
        soup = BeautifulSoup(html, "html.parser")

        # 获取书籍标题
        title_selector = self.book_rule.get("name", "")
        title = self._extract_text(soup, title_selector)

        # 获取作者
        author_selector = self.book_rule.get("author", "")
        author = self._extract_text(soup, author_selector)

        # 获取简介
        intro_selector = self.book_rule.get("intro", "")
        intro = self._extract_text(soup, intro_selector)

        # 获取封面图片
        cover_selector = self.book_rule.get("cover", "")
        cover = self._extract_attr(soup, cover_selector, "src")
        if cover and not cover.startswith(("http://", "https://")):
            cover = self._build_full_url(cover, url)

        # 获取状态
        status_selector = self.book_rule.get("status", "")
        status = self._extract_text(soup, status_selector)

        # 获取分类
        category_selector = self.book_rule.get("category", "")
        category = self._extract_text(soup, category_selector)

        # 获取字数
        word_count_selector = self.book_rule.get("word_count", "")
        word_count = self._extract_text(soup, word_count_selector)

        # 获取最后更新时间
        update_time_selector = self.book_rule.get("update_time", "")
        update_time = self._extract_text(soup, update_time_selector)

        # 获取目录URL
        toc_url_selector = self.book_rule.get("toc_url", "")
        toc_url = self._extract_attr(soup, toc_url_selector, "href")
        if toc_url and not toc_url.startswith(("http://", "https://")):
            toc_url = self._build_full_url(toc_url, url)

        return Book(
            title=title or "未知标题",
            author=author or "未知作者",
            intro=intro or "",
            cover=cover or "",
            status=status or "未知",
            category=category or "",
            word_count=word_count or "",
            update_time=update_time or "",
            toc_url=toc_url or url,
            source_id=self.source.id,
            source_name=self.source.rule.get("name", self.source.id),
        )

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """提取文本内容

        Args:
            soup: BeautifulSoup对象
            selector: CSS选择器

        Returns:
            提取的文本内容
        """
        if not selector:
            return ""

        try:
            # 处理meta标签选择器
            if selector.startswith("meta["):
                # 解析meta选择器，例如: meta[property="og:novel:book_name"]
                import re
                match = re.search(r'meta\[([^\]]+)\]', selector)
                if match:
                    attr_part = match.group(1)
                    # 解析属性，例如: property="og:novel:book_name"
                    attr_match = re.search(r'([^=]+)="([^"]+)"', attr_part)
                    if attr_match:
                        attr_name = attr_match.group(1).strip()
                        attr_value = attr_match.group(2)
                        
                        # 查找对应的meta标签
                        meta_tag = soup.find("meta", {attr_name: attr_value})
                        if meta_tag:
                            return meta_tag.get("content", "")
            
            # 处理普通CSS选择器
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
            
            return ""
        except Exception as e:
            logger.warning(f"提取文本失败: {selector}, 错误: {str(e)}")
            return ""

    def _extract_attr(self, soup: BeautifulSoup, selector: str, attr: str) -> str:
        """提取属性值

        Args:
            soup: BeautifulSoup对象
            selector: CSS选择器
            attr: 属性名

        Returns:
            提取的属性值
        """
        if not selector:
            return ""

        try:
            # 处理meta标签选择器
            if selector.startswith("meta["):
                import re
                match = re.search(r'meta\[([^\]]+)\]', selector)
                if match:
                    attr_part = match.group(1)
                    attr_match = re.search(r'([^=]+)="([^"]+)"', attr_part)
                    if attr_match:
                        attr_name = attr_match.group(1).strip()
                        attr_value = attr_match.group(2)
                        
                        meta_tag = soup.find("meta", {attr_name: attr_value})
                        if meta_tag:
                            return meta_tag.get("content", "")
            
            # 处理普通CSS选择器
            element = soup.select_one(selector)
            if element:
                return element.get(attr, "")
            
            return ""
        except Exception as e:
            logger.warning(f"提取属性失败: {selector}.{attr}, 错误: {str(e)}")
            return ""

    def _build_full_url(self, relative_url: str, base_url: str) -> str:
        """构建完整URL

        Args:
            relative_url: 相对URL
            base_url: 基础URL

        Returns:
            完整URL
        """
        if not relative_url:
            return ""

        try:
            from urllib.parse import urljoin

            return urljoin(base_url, relative_url)
        except Exception as e:
            logger.warning(f"构建URL失败: {relative_url}, {base_url}, 错误: {str(e)}")
            return relative_url
