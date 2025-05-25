import asyncio
import aiohttp
from typing import List, Optional
from bs4 import BeautifulSoup

from app.models.chapter import ChapterInfo
from app.core.source import Source
from app.core.config import settings


class TocParser:
    """目录解析器，用于解析小说目录页面"""
    
    def __init__(self, source: Source):
        """初始化目录解析器
        
        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.toc_timeout or settings.DEFAULT_TIMEOUT
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.base_uri
        }
    
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
        
        # 发送请求获取目录页面
        html = await self._fetch_html(toc_url)
        if not html:
            print(f"<== 从 {self.source.name} 获取目录失败: {toc_url}")
            return []
        
        # 解析目录
        chapters = self._parse_toc(html, toc_url)
        
        # 处理分页
        if self.source.toc_rule.get("has_pages", False):
            # 获取总页数
            total_pages = self._get_total_pages(html)
            
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
        end_idx = min(len(chapters), int(end))
        
        result_chapters = chapters[start_idx:end_idx]
        
        # print(f"<== 从 {self.source.name} 获取到 {len(result_chapters)} 个章节") # 移除旧的打印语句
        logger.info(f"书源 {self.source.rule.get('name', self.source.id)} 获取到 {len(result_chapters)} 个章节") # 添加日志
        return result_chapters
    
    def _get_toc_url(self, url: str) -> str:
        """获取目录URL
        
        Args:
            url: 小说详情页URL
            
        Returns:
            目录URL
        """
        # 如果目录规则中有URL，则使用目录规则中的URL
        toc_url = self.source.toc_rule.get("url", "")
        if toc_url:
            # 替换{bookUrl}为小说详情页URL
            toc_url = toc_url.replace("{bookUrl}", url)
            
            # 如果URL不是以http开头，则添加baseUri
            if not toc_url.startswith("http"):
                toc_url = f"{self.source.base_uri.rstrip('/')}/{toc_url.lstrip('/')}"
            
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
        page_url = self.source.toc_rule.get("page_url", "")
        if not page_url:
            return toc_url
        
        # 替换{tocUrl}为目录URL，{page}为页码
        page_url = page_url.replace("{tocUrl}", toc_url)
        page_url = page_url.replace("{page}", str(page))
        
        # 如果URL不是以http开头，则添加baseUri
        if not page_url.startswith("http"):
            page_url = f"{self.source.base_uri.rstrip('/')}/{page_url.lstrip('/')}"
        
        return page_url
    
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
            # print(f"<== 从 {self.source.name} 获取目录失败: {toc_url}") # 移除旧的打印语句
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 获取目录失败: {toc_url}, 错误: {str(e)}") # 添加日志
            return []

    async def parse(self, url: str, start: int, end: int) -> List[ChapterInfo]:
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
        
        # 发送请求获取目录页面
        html = await self._fetch_html(toc_url)
        if not html:
            print(f"<== 从 {self.source.name} 获取目录失败: {toc_url}")
            return []
        
        # 解析目录
        chapters = self._parse_toc(html, toc_url)
        
        # 处理分页
        if self.source.toc_rule.get("has_pages", False):
            # 获取总页数
            total_pages = self._get_total_pages(html)
            
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
        end_idx = min(len(chapters), int(end))
        
        result_chapters = chapters[start_idx:end_idx]
        
        # print(f"<== 从 {self.source.name} 获取到 {len(result_chapters)} 个章节") # 移除旧的打印语句
        logger.info(f"书源 {self.source.rule.get('name', self.source.id)} 获取到 {len(result_chapters)} 个章节") # 添加日志
        return result_chapters
    
    def _get_toc_url(self, url: str) -> str:
        """获取目录URL
        
        Args:
            url: 小说详情页URL
            
        Returns:
            目录URL
        """
        # 如果目录规则中有URL，则使用目录规则中的URL
        toc_url = self.source.toc_rule.get("url", "")
        if toc_url:
            # 替换{bookUrl}为小说详情页URL
            toc_url = toc_url.replace("{bookUrl}", url)
            
            # 如果URL不是以http开头，则添加baseUri
            if not toc_url.startswith("http"):
                toc_url = f"{self.source.base_uri.rstrip('/')}/{toc_url.lstrip('/')}"
            
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
        page_url = self.source.toc_rule.get("page_url", "")
        if not page_url:
            return toc_url
        
        # 替换{tocUrl}为目录URL，{page}为页码
        page_url = page_url.replace("{tocUrl}", toc_url)
        page_url = page_url.replace("{page}", str(page))
        
        # 如果URL不是以http开头，则添加baseUri
        if not page_url.startswith("http"):
            page_url = f"{self.source.base_uri.rstrip('/')}/{page_url.lstrip('/')}"
        
        return page_url
    
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
            print(f"<== 请求异常: {url}, 错误: {str(e)}")
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
        
        # 获取目录规则
        list_selector = self.source.toc_rule.get("list", "")
        title_selector = self.source.toc_rule.get("title", "")
        url_selector = self.source.toc_rule.get("url", "")
        
        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # 获取章节列表
        items = soup.select(list_selector)
        
        for i, item in enumerate(items):
            try:
                # 获取章节标题
                title_element = item
                if title_selector:
                    title_element = item.select_one(title_selector) or item
                
                title = title_element.get_text().strip()
                
                # 获取章节URL
                url = ""
                url_element = item
                if url_selector:
                    url_element = item.select_one(url_selector) or item
                
                url = url_element.get("href", "")
                
                # 如果URL不是以http开头，则添加baseUri
                if url and not url.startswith("http"):
                    url = f"{self.source.base_uri.rstrip('/')}/{url.lstrip('/')}"
                
                # 创建章节对象
                chapter = ChapterInfo(
                    url=url,
                    title=title,
                    order=i + 1
                )
                
                chapters.append(chapter)
            except Exception as e:
                print(f"<== 解析章节异常: {str(e)}")
                continue
        
        return chapters
    
    def _get_total_pages(self, html: str) -> int:
        """获取总页数
        
        Args:
            html: HTML页面内容
            
        Returns:
            总页数
        """
        # 获取分页规则
        page_selector = self.source.toc_rule.get("page_selector", "")
        page_pattern = self.source.toc_rule.get("page_pattern", "")
        
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