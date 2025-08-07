
"""
增强章节解析器
提供更好的内容解析和错误处理
"""
import asyncio
import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.chapter import Chapter
from app.utils.content_validator import ContentValidator
from app.utils.enhanced_http_client import EnhancedHttpClient

logger = logging.getLogger(__name__)


class EnhancedChapterParser:
    """增强章节解析器，提供更好的内容解析和错误处理"""

    def __init__(self, source: Source):
        """初始化增强章节解析器

        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("chapter", {}).get(
            "timeout", settings.DEFAULT_TIMEOUT
        )
        self.chapter_rule = source.rule.get("chapter", {})
        self.content_validator = ContentValidator()

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
            logger.error(
                f"书源 {self.source.rule.get('name', self.source.id)} "
                f"获取章节内容失败: {url}"
            )
            return Chapter(
                url=url, title=title, content="获取章节内容失败", order=order
            )

        # 解析章节内容
        content = self._parse_chapter_content(html, title)

        # 创建章节对象
        chapter = Chapter(url=url, title=title, content=content, order=order)

        return chapter

    async def _fetch_html(self, url: str) -> Optional[str]:
        """获取HTML页面

        Args:
            url: 页面URL

        Returns:
            HTML页面内容，失败返回None
        """
        referer = self.source.rule.get("url", "")
        return await EnhancedHttpClient.fetch_html_with_retry(url, self.timeout, referer)

    def _parse_chapter_content(self, html: str, title: str = "未知章节") -> str:
        """解析章节内容

        Args:
            html: HTML页面内容

        Returns:
            章节内容
        """
        # 获取章节内容规则
        content_selectors = self.chapter_rule.get("content", "").split(",")
        ad_patterns = self.chapter_rule.get("ad_patterns", [])

        if not content_selectors:
            logger.warning("章节规则中缺少content选择器")
            return "无法获取章节内容：缺少内容选择器"

        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")

        # 尝试多个选择器获取章节内容
        content = None
        for selector in content_selectors:
            selector = selector.strip()
            if not selector:
                continue
                
            content_element = soup.select_one(selector)
            if content_element:
                content = content_element.get_text(separator="\n", strip=True)
                if content and len(content) > settings.MIN_CONTENT_LENGTH:  # 确保内容足够长
                    logger.debug(f"使用选择器 {selector} 成功获取内容")
                    break
                else:
                    logger.warning(f"选择器 {selector} 获取的内容过短")
                    content = None

        if not content:
            logger.warning(f"未找到有效的章节内容")
            return "无法获取章节内容：内容元素不存在"

        # 使用内容验证器清理和验证内容
        content = self.content_validator.clean_content(content)
        
        # 验证内容质量
        is_valid, error_msg = self.content_validator.validate_chapter_content(content, title)
        if not is_valid:
            logger.warning(f"章节内容质量不佳: {title} - {error_msg}")
            content = f"（本章获取失败：{error_msg}）"

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
                content = re.sub(pattern, "", content, flags=re.IGNORECASE)
            except re.error:
                logger.warning(f"无效的正则表达式: {pattern}")
                continue

        # 移除常见的广告内容
        common_ad_patterns = [
            r"看最新章节请到.+",
            r"本书最新章节请到.+",
            r"更新最快的.+",
            r"天才一秒记住.+",
            r"天才壹秒記住.+",
            r"一秒记住.+",
            r"记住.+，为您提供精彩小说阅读。",
            r"手机用户请访问.+",
            r"手机版阅读网址.+",
            r"推荐都市大神老施新书.+",
            r"\(本章完\)",
            r"章节错误[，,].*?举报",
            r"内容严重缺失[，,].*?举报",
            r"笔趣阁.+",
            r"新笔趣阁.+",
            r"香书小说.+",
            r"文学巴士.+",
            r"高速全文字在线阅读.+",
            r"天才一秒记住本站地址.+",
            r"手机用户请浏览阅读.+",
            r"天才壹秒記住.+為您提供精彩小說閱讀.+",
            r"一秒记住【.+?】",
            r"天才一秒记住.+?",
            r"天才壹秒記住.+?",
            r"看最新章节请到.+?",
        ]

        for pattern in common_ad_patterns:
            try:
                content = re.sub(pattern, "", content, flags=re.IGNORECASE)
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
        if not content:
            return "（本章获取失败）"

        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 移除空行
        lines = content.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        # 重新组合
        content = '\n'.join(lines)
        
        return content
