import asyncio
import logging
import re
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.chapter import Chapter

logger = logging.getLogger(__name__)


class EnhancedChapterParser:
    """增强的章节解析器，专门处理《仙逆》等小说的解析问题"""

    def __init__(self, source: Source):
        """初始化增强章节解析器

        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("chapter", {}).get(
            "timeout", settings.DEFAULT_TIMEOUT
        )
        self.retry_times = source.rule.get("chapter", {}).get("retry_times", 3)
        self.retry_delay = source.rule.get("chapter", {}).get("retry_delay", 2.0)
        
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
            "Referer": source.rule.get("url", ""),
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
            logger.error(
                f"书源 {self.source.rule.get('name', self.source.id)} "
                f"获取章节内容失败: {url}"
            )
            return Chapter(
                url=url, title=title, content="获取章节内容失败", order=order
            )

        # 解析章节内容
        content = self._parse_chapter_content(html)

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
        for attempt in range(self.retry_times):
            try:
                result = await self._fetch_html_single(url)
                if result:
                    return result

                if attempt == 0:
                    logger.warning(f"第一次请求失败，准备重试: {url}")

            except Exception as e:
                if attempt < self.retry_times - 1:
                    logger.warning(
                        f"请求失败（第 {attempt + 1} 次），"
                        f"{self.retry_delay} 秒后重试: {str(e)}"
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"请求最终失败（共 {self.retry_times} 次尝试）: "
                        f"{str(e)}"
                    )

        return None

    async def _fetch_html_single(self, url: str) -> Optional[str]:
        """获取HTML页面（单次请求）

        Args:
            url: 页面URL

        Returns:
            HTML页面内容，失败返回None
        """
        try:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout, connect=10)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content
                    else:
                        logger.warning(f"HTTP {response.status}: {url}")
                        return None

        except Exception as e:
            logger.error(f"请求失败: {str(e)}")
            return None

    def _parse_chapter_content(self, html: str) -> str:
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
                if content and len(content) > 100:  # 确保内容足够长
                    logger.info(f"使用选择器 {selector} 成功获取内容")
                    break
                else:
                    logger.warning(f"选择器 {selector} 获取的内容过短")
                    content = None

        if not content:
            logger.warning(f"未找到有效的章节内容")
            return "无法获取章节内容：内容元素不存在"

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
        if not isinstance(content, str) or not content.strip():
            return "（本章获取失败）"

        # 移除多余的空行
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        # 移除行首行尾空格
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        # 重新组合内容，每段之间加空行
        formatted_lines = []
        for line in lines:
            if line:
                formatted_lines.append(line)
                formatted_lines.append("")  # 空行分隔段落

        # 移除最后的空行
        if formatted_lines and formatted_lines[-1] == "":
            formatted_lines.pop()

        return "\n".join(formatted_lines)

    async def parse_with_fallback(self, url: str, title: str, order: int) -> Chapter:
        """带备用方案的章节解析

        Args:
            url: 章节URL
            title: 章节标题
            order: 章节序号

        Returns:
            章节对象
        """
        # 首先尝试正常解析
        chapter = await self.parse(url, title, order)
        
        # 如果内容太短，尝试备用方案
        if len(chapter.content) < 100:
            logger.warning(f"章节内容过短，尝试备用方案: {title}")
            
            # 尝试不同的URL格式
            fallback_urls = self._generate_fallback_urls(url)
            
            for fallback_url in fallback_urls:
                try:
                    fallback_chapter = await self.parse(fallback_url, title, order)
                    if len(fallback_chapter.content) > len(chapter.content):
                        logger.info(f"备用URL成功: {fallback_url}")
                        return fallback_chapter
                except Exception as e:
                    logger.warning(f"备用URL失败: {fallback_url}, 错误: {str(e)}")
                    continue
        
        return chapter

    def _generate_fallback_urls(self, original_url: str) -> List[str]:
        """生成备用URL列表

        Args:
            original_url: 原始URL

        Returns:
            备用URL列表
        """
        fallback_urls = []
        
        # 尝试不同的域名
        domains = [
            "www.xbiqugu.la",
            "www.xbiquge.la", 
            "www.biquge.com.cn",
            "www.biquge.tv",
            "www.biquge.cc",
        ]
        
        # 提取路径部分
        path = "/".join(original_url.split("/")[3:])
        
        for domain in domains:
            fallback_url = f"https://{domain}/{path}"
            if fallback_url != original_url:
                fallback_urls.append(fallback_url)
        
        return fallback_urls