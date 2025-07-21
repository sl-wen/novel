import asyncio
import aiohttp
import logging
import re
from typing import Optional, List
from bs4 import BeautifulSoup

from app.models.chapter import Chapter
from app.core.source import Source
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChapterParser:
    """章节解析器，用于解析小说章节内容页面"""
    
    def __init__(self, source: Source):
        """初始化章节解析器
        
        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("chapter", {}).get("timeout", settings.DEFAULT_TIMEOUT)
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", "")
        }
        self.chapter_rule = source.rule.get("chapter", {})
    
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
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 获取章节内容失败: {url}")
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
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 获取章节内容失败: {url}, 错误: {str(e)}")
            return None
    
    def _parse_chapter_content(self, html: str) -> str:
        """解析章节内容
        
        Args:
            html: HTML页面内容
            
        Returns:
            章节内容
        """
        # 获取章节内容规则
        content_selector = self.chapter_rule.get("content", "")
        title_selector = self.chapter_rule.get("title", "")
        ad_patterns = self.chapter_rule.get("ad_patterns", [])
        
        if not content_selector:
            logger.warning("章节规则中缺少content选择器")
            return "无法获取章节内容：缺少内容选择器"
        
        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # 获取章节内容
        content_element = soup.select_one(content_selector)
        if not content_element:
            logger.warning(f"未找到章节内容元素: {content_selector}")
            return "无法获取章节内容：内容元素不存在"
        
        # 提取文本内容
        content = content_element.get_text(separator='\n', strip=True)
        if not isinstance(content, str) or not content.strip():
            content = "（本章获取失败）"
        
        # 过滤广告和垃圾内容
        content = self._filter_content(content, ad_patterns)
        
        # 格式化内容
        content = self._format_content(content)
        
        return content
    
    def _filter_content(self, content: str, ad_patterns: List[str]) -> str:
        """过滤广告和垃圾内容
        
        Args:
            content: 原始内容
            ad_patterns: 广告正则表达式列表
            
        Returns:
            过滤后的内容
        """
        if not isinstance(content, str) or not content.strip():
            return "（本章获取失败）"
        
        # 应用广告过滤规则
        for pattern in ad_patterns:
            try:
                content = re.sub(pattern, '', content, flags=re.IGNORECASE)
            except re.error:
                logger.warning(f"无效的正则表达式: {pattern}")
                continue
        
        # 移除常见的广告内容
        common_ad_patterns = [
            r'看最新章节请到.+',
            r'本书最新章节请到.+',
            r'更新最快的.+',
            r'天才一秒记住.+',
            r'天才壹秒記住.+',
            r'一秒记住.+',
            r'记住.+，为您提供精彩小说阅读。',
            r'手机用户请访问.+',
            r'手机版阅读网址.+',
            r'推荐都市大神老施新书.+',
            r'\(本章完\)',
            r'章节错误[，,].*?举报',
            r'内容严重缺失[，,].*?举报'
        ]
        
        for pattern in common_ad_patterns:
            try:
                content = re.sub(pattern, '', content, flags=re.IGNORECASE)
            except re.error:
                continue
        
        return content
    
    def _format_content(self, content: str) -> str:
        """格式化内容
        
        Args:
            content: 原始内容
            
        Returns:
            格式化后的内容
        """
        if not isinstance(content, str) or not content.strip():
            return "（本章获取失败）"
        
        # 移除多余的空行
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # 移除行首行尾空格
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # 重新组合内容，每段之间加空行
        formatted_lines = []
        for line in lines:
            if line:
                formatted_lines.append(line)
                formatted_lines.append('')  # 空行分隔段落
        
        # 移除最后的空行
        if formatted_lines and formatted_lines[-1] == '':
            formatted_lines.pop()
        
        return '\n'.join(formatted_lines)