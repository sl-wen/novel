
"""
增强目录解析器
提供更好的章节解析和错误处理
"""
import asyncio
import logging
from typing import List, Optional

from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.chapter import ChapterInfo
from app.utils.enhanced_http_client import EnhancedHttpClient

logger = logging.getLogger(__name__)


class EnhancedTocParser:
    """增强目录解析器，提供更好的章节解析和错误处理"""

    def __init__(self, source: Source):
        """初始化增强目录解析器

        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("toc", {}).get(
            "timeout", settings.DEFAULT_TIMEOUT
        )
        self.toc_rule = source.rule.get("toc", {})

    async def parse(
        self, url: str, start: int = 1, end: float = float("inf")
    ) -> List[ChapterInfo]:
        """解析目录

        Args:
            url: 小说详情页URL
            start: 起始章节，从1开始
            end: 结束章节，默认为无穷大表示全部章节

        Returns:
            章节列表
        """
        # 获取目录URL
        toc_url = self._get_toc_url(url)
        logger.info(f"构建的目录URL: {toc_url}")

        # 发送请求获取目录页面
        html = await self._fetch_html(toc_url)
        if not html:
            logger.error(
                f"从书源 {self.source.rule.get('name', self.source.id)} "
                f"获取目录失败: {toc_url}"
            )
            return []

        logger.info(f"目录页面HTML长度: {len(html)}")

        # 解析目录
        chapters = self._parse_toc(html, toc_url)

        # 处理分页
        if self.toc_rule.get("has_pages", False):
            logger.info("处理目录分页...")
            # 获取总页数
            total_pages = self._get_total_pages(html)
            logger.info(f"总页数: {total_pages}")

            # 获取其他页的目录
            if total_pages > 1:
                tasks = []
                for page in range(2, total_pages + 1):
                    page_url = self._get_toc_page_url(toc_url, page)
                    tasks.append(self._fetch_and_parse_page(page_url))

                # 并发获取其他页的目录
                other_chapters = await asyncio.gather(*tasks)

                # 合并结果并重新分配顺序
                current_order = len(chapters) + 1
                for page_chapters in other_chapters:
                    for chapter in page_chapters:
                        chapter.order = current_order
                        current_order += 1
                        chapters.append(chapter)

        # 排序章节
        chapters.sort(key=lambda x: x.order)

        # 截取指定范围的章节
        start_idx = max(0, start - 1)
        if end == float("inf"):
            end_idx = len(chapters)
        else:
            end_idx = min(len(chapters), int(end))

        result_chapters = chapters[start_idx:end_idx]

        logger.info(
            f"书源 {self.source.rule.get('name', self.source.id)} "
            f"获取到 {len(result_chapters)} 个章节"
        )

        return result_chapters

    def _get_toc_url(self, url: str) -> str:
        """构建目录URL

        Args:
            url: 小说详情页URL

        Returns:
            目录URL
        """
        # 如果URL以.html结尾，替换为目录页
        if url.endswith('.html'):
            return url.replace('.html', '/')
        return url

    def _get_toc_page_url(self, toc_url: str, page: int) -> str:
        """构建分页目录URL

        Args:
            toc_url: 目录URL
            page: 页码

        Returns:
            分页目录URL
        """
        if toc_url.endswith('/'):
            return f"{toc_url}index_{page}.html"
        else:
            return f"{toc_url}_p{page}.html"

    async def _fetch_html(self, url: str) -> Optional[str]:
        """获取HTML页面

        Args:
            url: 页面URL

        Returns:
            HTML页面内容，失败返回None
        """
        referer = self.source.rule.get("url", "")
        return await EnhancedHttpClient.fetch_html_with_retry(url, self.timeout, referer)

    async def _fetch_html_single(self, url: str) -> Optional[str]:
        """获取单个HTML页面（用于分页请求）

        Args:
            url: 页面URL

        Returns:
            HTML页面内容，失败返回None
        """
        referer = self.source.rule.get("url", "")
        return await EnhancedHttpClient.fetch_html_with_retry(url, self.timeout, referer)

    def _parse_toc(self, html: str, toc_url: str) -> List[ChapterInfo]:
        """解析目录

        Args:
            html: HTML页面内容
            toc_url: 目录URL

        Returns:
            章节列表
        """
        logger.info(f"开始解析目录，HTML长度: {len(html)}")
        
        soup = BeautifulSoup(html, "html.parser")
        chapters = []

        # 获取章节列表选择器
        list_selectors = self.toc_rule.get("list", "").split(",")
        if not list_selectors:
            logger.warning("未配置章节列表选择器")
            return chapters

        # 尝试多个选择器获取章节列表
        chapter_elements = []
        for selector in list_selectors:
            selector = selector.strip()
            if not selector:
                continue
                
            elements = soup.select(selector)
            logger.info(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
            if elements:
                chapter_elements = elements
                break
        
        if not chapter_elements:
            logger.warning("未找到任何章节元素")
            return chapters

        logger.info(f"开始解析 {len(chapter_elements)} 个章节元素")
        
        for index, element in enumerate(chapter_elements, 1):
            try:
                chapter = self._parse_single_chapter(element, toc_url, index)
                if chapter:
                    chapters.append(chapter)
                    logger.debug(f"成功解析章节 {index}: {chapter.title}")
                else:
                    logger.warning(f"解析章节 {index} 失败")
            except Exception as e:
                logger.warning(f"解析单个章节失败: {str(e)}")
                continue

        logger.info(f"目录解析完成，成功解析 {len(chapters)} 个章节")
        return chapters

    def _parse_single_chapter(
        self, element: BeautifulSoup, toc_url: str, order: int
    ) -> Optional[ChapterInfo]:
        """解析单个章节

        Args:
            element: 章节元素
            toc_url: 目录URL
            order: 章节序号

        Returns:
            章节信息对象，失败返回None
        """
        try:
            # 获取章节标题
            title_selector = self.toc_rule.get("title", "")
            if title_selector == "text":
                # 直接使用元素文本
                title = element.get_text(strip=True)
            else:
                title = self._extract_text(element, title_selector)

            # 获取章节URL
            url_selector = self.toc_rule.get("url", "")
            if url_selector == "href":
                # 直接使用href属性
                url = element.get("href", "")
            else:
                url = self._extract_attr(element, url_selector, "href")

            # 构建完整URL
            if url and not url.startswith(("http://", "https://")):
                base_url = self.source.rule.get("url", "")
                url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"

            # 获取章节字数（可选）
            word_count_selector = self.toc_rule.get("word_count", "")
            word_count = self._extract_text(element, word_count_selector)

            # 获取更新时间（可选）
            update_time_selector = self.toc_rule.get("update_time", "")
            update_time = self._extract_text(element, update_time_selector)

            # 验证必要字段
            if not title or not url:
                logger.warning(f"章节 {order} 缺少必要字段: title='{title}', url='{url}'")
                return None

            return ChapterInfo(
                title=title or f"第{order}章",
                url=url or "",
                order=order,
                word_count=word_count or "",
                update_time=update_time or "",
                source_id=self.source.id,
                source_name=self.source.rule.get("name", self.source.id),
            )
        except Exception as e:
            logger.warning(f"解析章节失败: {str(e)}")
            return None

    def _extract_text(self, element: BeautifulSoup, selector: str) -> str:
        """提取文本内容

        Args:
            element: 元素
            selector: 选择器

        Returns:
            文本内容
        """
        if not selector:
            return ""
        
        try:
            target_element = element.select_one(selector)
            if target_element:
                return target_element.get_text(strip=True)
        except Exception as e:
            logger.warning(f"提取文本失败: {str(e)}")
        
        return ""

    def _extract_attr(self, element: BeautifulSoup, selector: str, attr: str) -> str:
        """提取属性值

        Args:
            element: 元素
            selector: 选择器
            attr: 属性名

        Returns:
            属性值
        """
        if not selector:
            return ""
        
        try:
            target_element = element.select_one(selector)
            if target_element:
                return target_element.get(attr, "")
        except Exception as e:
            logger.warning(f"提取属性失败: {str(e)}")
        
        return ""

    def _get_total_pages(self, html: str) -> int:
        """获取总页数

        Args:
            html: HTML页面内容

        Returns:
            总页数
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # 尝试多种分页选择器
            page_selectors = [
                ".pagination a",
                ".page a", 
                ".pages a",
                "a[href*='page']",
                "a[href*='p']"
            ]
            
            for selector in page_selectors:
                elements = soup.select(selector)
                if elements:
                    # 提取页码
                    page_numbers = []
                    for element in elements:
                        try:
                            text = element.get_text(strip=True)
                            if text.isdigit():
                                page_numbers.append(int(text))
                        except:
                            continue
                    
                    if page_numbers:
                        return max(page_numbers)
            
            return 1
        except Exception as e:
            logger.warning(f"获取总页数失败: {str(e)}")
            return 1

    async def _fetch_and_parse_page(self, url: str) -> List[ChapterInfo]:
        """获取并解析分页

        Args:
            url: 分页URL

        Returns:
            章节列表
        """
        try:
            html = await self._fetch_html_single(url)
            if html:
                return self._parse_toc(html, url)
        except Exception as e:
            logger.warning(f"获取分页失败: {str(e)}")
        
        return []
