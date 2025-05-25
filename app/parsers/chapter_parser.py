import asyncio
import aiohttp
from typing import Optional
from bs4 import BeautifulSoup

from app.models.chapter import Chapter
from app.core.source import Source
from app.core.config import settings


class ChapterParser:
    """章节解析器，用于解析小说章节内容页面"""
    
    def __init__(self, source: Source):
        """初始化章节解析器
        
        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.chapter_timeout or settings.DEFAULT_TIMEOUT
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.base_uri
        }
    
    async def parse(self, url: str, title: str, order: int) -> Chapter:
        """解析章节内容
        
        Args:
            url: 章节URL
            title: 章节标题
            order: 章节序号
            
        Returns:
            章节对象
        """
        # 发送请求获取章节内容页面
        html = await self._fetch_html(url)
        if not html:
            print(f"<== 从 {self.source.name} 获取章节内容失败: {url}")
            return Chapter(url=url, title=title, content="获取章节内容失败", order=order)
        
        # 解析章节内容
        content = self._parse_chapter_content(html)
        
        # 创建章节对象
        chapter = Chapter(
            url=url,
            title=title,
            content=content,
            order=order
        )
        
        return chapter
    
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
            # print(f"<== 从 {self.source.name} 获取章节内容失败: {url}") # 移除旧的打印语句
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 获取章节内容失败: {url}, 错误: {str(e)}") # 添加日志
            return None

    async def parse(self, url: str) -> Optional[Chapter]:
        """解析章节内容
        
        Args:
            url: 章节URL
            title: 章节标题
            order: 章节序号
            
        Returns:
            章节对象
        """
        # 发送请求获取章节内容页面
        html = await self._fetch_html(url)
        if not html:
            print(f"<== 从 {self.source.name} 获取章节内容失败: {url}")
            return Chapter(url=url, title=title, content="获取章节内容失败", order=order)
        
        # 解析章节内容
        content = self._parse_chapter_content(html)
        
        # 创建章节对象
        chapter = Chapter(
            url=url,
            title=title,
            content=content,
            order=order
        )
        
        return chapter
    
    def _parse_chapter_content(self, html: str) -> str:
        """解析章节内容
        
        Args:
            html: HTML页面内容
            
        Returns:
            章节内容
        """
        # 获取章节内容规则
        content_selector = self.source.chapter_rule.get("content", "")
        
        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # 获取章节内容
        content = ""
        if content_selector:
            content_element = soup.select_one(content_selector)
            if content_element:
                # 移除所有script和style标签
                for script in content_element.find_all(["script", "style"]):
                    script.decompose()
                
                # 获取文本内容
                content = content_element.get_text("\n").strip()
                
                # 处理内容
                content = self._process_content(content)
        
        return content or "章节内容为空"
    
    def _process_content(self, content: str) -> str:
        """处理章节内容
        
        Args:
            content: 原始章节内容
            
        Returns:
            处理后的章节内容
        """
        # 移除广告和无用内容
        ad_patterns = self.source.chapter_rule.get("ad_patterns", [])
        for pattern in ad_patterns:
            import re
            content = re.sub(pattern, "", content)
        
        # 替换特定字符
        content = content.replace("\r\n", "\n")
        content = content.replace("\r", "\n")
        
        # 移除连续的空行
        import re
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content