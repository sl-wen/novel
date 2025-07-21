import asyncio
import aiohttp
import logging
from typing import List, Optional
from bs4 import BeautifulSoup

from app.models.chapter import ChapterInfo
from app.core.source import Source
from app.core.config import settings

logger = logging.getLogger(__name__)


class TocParser:
    """目录解析器，用于解析小说目录页面"""
    
    def __init__(self, source: Source):
        """初始化目录解析器
        
        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("toc", {}).get("timeout", settings.DEFAULT_TIMEOUT)
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", "")
        }
        self.toc_rule = source.rule.get("toc", {})
    
    async def parse(self, url: str, start: int = 1, end: float = float('inf')) -> List[ChapterInfo]:
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
            logger.error(f"从书源 {self.source.rule.get('name', self.source.id)} 获取目录失败: {toc_url}")
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
                
                # 合并结果
                for page_chapters in other_chapters:
                    chapters.extend(page_chapters)
        
        # 排序章节
        chapters.sort(key=lambda x: x.order)
        
        # 截取指定范围的章节
        start_idx = max(0, start - 1)
        if end == float('inf'):
            end_idx = len(chapters)
        else:
            end_idx = min(len(chapters), int(end))
        
        result_chapters = chapters[start_idx:end_idx]
        
        logger.info(f"书源 {self.source.rule.get('name', self.source.id)} 获取到 {len(result_chapters)} 个章节")
        return result_chapters
    
    def _get_toc_url(self, url: str) -> str:
        """获取目录URL
        
        Args:
            url: 小说详情页URL
            
        Returns:
            目录URL
        """
        # 如果目录规则中有URL，则使用目录规则中的URL
        toc_url = self.toc_rule.get("url", "")
        if toc_url:
            # 处理%s占位符：从书籍URL中提取书籍ID
            if "%s" in toc_url:
                # 从URL中提取书籍ID（通常在URL的最后部分）
                import re
                # 尝试从URL中提取数字ID
                match = re.search(r'/(\d+)/?$', url)
                if match:
                    book_id = match.group(1)
                    toc_url = toc_url.replace("%s", book_id)
                else:
                    logger.warning(f"无法从URL中提取书籍ID: {url}")
                    return url
            else:
                # 替换{bookUrl}为小说详情页URL
                toc_url = toc_url.replace("{bookUrl}", url)
            
            # 如果URL不是以http开头，则添加baseUri
            if not toc_url.startswith("http"):
                base_uri = self.source.rule.get("url", "")
                toc_url = f"{base_uri.rstrip('/')}/{toc_url.lstrip('/')}"
            
            return toc_url
        
        # 否则使用小说详情页URL作为目录URL
        return url
    
    def _get_toc_page_url(self, toc_url: str, page: int) -> str:
        """获取目录分页URL
        
        Args:
            toc_url: 目录URL
            page: 页码
            
        Returns:
            目录分页URL
        """
        # 获取分页URL规则
        page_url = self.toc_rule.get("page_url", "")
        if not page_url:
            return toc_url
        
        # 替换{tocUrl}为目录URL，{page}为页码
        page_url = page_url.replace("{tocUrl}", toc_url)
        page_url = page_url.replace("{page}", str(page))
        
        # 如果URL不是以http开头，则添加baseUri
        if not page_url.startswith("http"):
            base_uri = self.source.rule.get("url", "")
            page_url = f"{base_uri.rstrip('/')}/{page_url.lstrip('/')}"
        
        return page_url
    
    async def _fetch_html(self, url: str) -> Optional[str]:
        """获取HTML页面
        
        Args:
            url: 页面URL
            
        Returns:
            HTML页面内容，失败返回None
        """
        for attempt in range(settings.REQUEST_RETRY_TIMES):
            try:
                result = await self._fetch_html_single(url)
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
    
    async def _fetch_html_single(self, url: str) -> Optional[str]:
        """获取HTML页面（单次请求）
        
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
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 获取目录失败: {url}, 错误: {str(e)}")
            return None
    
    def _parse_toc(self, html: str, toc_url: str) -> List[ChapterInfo]:
        """解析目录
        
        Args:
            html: HTML页面内容
            toc_url: 目录URL
            
        Returns:
            章节列表
        """
        chapters = []
        
        try:
        # 获取目录规则
            list_selector = self.toc_rule.get("list", "")
            title_selector = self.toc_rule.get("title", "")
            # 注意：toc.url是目录页面URL模板，不是CSS选择器
            # 章节URL应该从<a>元素的href属性直接获取
            
            logger.info(f"目录解析规则 - list: {list_selector}, title: {title_selector}")
            
            if not list_selector:
                logger.warning("目录规则中缺少list选择器")
                return chapters
        
            # 解析HTML
            soup = BeautifulSoup(html, "html.parser")
        
            # 获取章节列表
            items = soup.select(list_selector)
            logger.info(f"找到 {len(items)} 个章节元素")
            
            # 如果没有找到元素，打印HTML片段用于调试
            if len(items) == 0:
                logger.warning(f"未找到章节元素，HTML片段（前500字符）: {html[:500]}")
        
            for i, item in enumerate(items):
                try:
                # 获取章节标题
                    title = ""
                if title_selector:
                        title_element = item.select_one(title_selector)
                        if title_element:
                title = title_element.get_text().strip()
                        else:
                            title = item.get_text().strip()
                    else:
                        # 如果没有指定标题选择器，直接获取元素文本
                        title = item.get_text().strip()
                    
                    # 获取章节URL - 直接从href属性获取
                    chapter_url = item.get("href", "")
                
                # 如果URL不是以http开头，则添加baseUri
                    if chapter_url and not chapter_url.startswith("http"):
                        base_uri = self.source.rule.get("url", "")
                        chapter_url = f"{base_uri.rstrip('/')}/{chapter_url.lstrip('/')}"
                
                    if title and chapter_url:
                # 创建章节对象
                chapter = ChapterInfo(
                            url=chapter_url,
                    title=title,
                    order=i + 1
                )
                        chapters.append(chapter)
                
            except Exception as e:
                    logger.error(f"解析章节异常: {str(e)}")
                continue
            
        except Exception as e:
            logger.error(f"解析目录异常: {str(e)}")
        
        return chapters
    
    def _get_total_pages(self, html: str) -> int:
        """获取总页数
        
        Args:
            html: HTML页面内容
            
        Returns:
            总页数
        """
        # 获取分页规则
        page_selector = self.toc_rule.get("page_selector", "")
        page_pattern = self.toc_rule.get("page_pattern", "")
        
        if not page_selector or not page_pattern:
            return 1
        
        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # 获取分页元素
        page_element = soup.select_one(page_selector)
        if not page_element:
            return 1
        
        # 获取分页文本
        page_text = page_element.get_text()
        
        # 使用正则表达式提取总页数
        import re
        match = re.search(page_pattern, page_text)
        if match and match.group(1):
            try:
                return int(match.group(1))
            except ValueError:
                return 1
        
        return 1
    
    async def _fetch_and_parse_page(self, url: str) -> List[ChapterInfo]:
        """获取并解析页面
        
        Args:
            url: 页面URL
            
        Returns:
            章节列表
        """
        html = await self._fetch_html(url)
        if not html:
            return []
        
        return self._parse_toc(html, url)