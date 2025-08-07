#!/usr/bin/env python3
"""
增强下载优化器
改进HTTP客户端、错误处理和重试机制
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedDownloadOptimizer:
    """增强下载优化器"""
    
    def __init__(self):
        self.optimizations = {
            'http_client': self.optimize_http_client,
            'toc_parser': self.optimize_toc_parser,
            'chapter_parser': self.optimize_chapter_parser,
            'error_handling': self.optimize_error_handling,
            'retry_mechanism': self.optimize_retry_mechanism
        }
    
    def optimize_http_client(self):
        """优化HTTP客户端"""
        logger.info("优化HTTP客户端...")
        
        http_client_content = '''
"""
增强HTTP客户端工具类
提供更好的网络请求处理和错误恢复
"""
import asyncio
import logging
import random
from typing import Optional, Dict, Any, List

import aiohttp
from aiohttp import ClientTimeout, TCPConnector

from app.core.config import settings

logger = logging.getLogger(__name__)


class EnhancedHttpClient:
    """增强HTTP客户端，提供更好的网络请求处理"""
    
    # 用户代理池
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    ]
    
    # 请求策略
    REQUEST_STRATEGIES = [
        {
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            },
            'description': '完整压缩支持'
        },
        {
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'description': '不支持Brotli'
        },
        {
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'User-Agent': 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
            },
            'description': 'IE兼容模式'
        }
    ]
    
    @staticmethod
    async def fetch_html_with_retry(
        url: str, 
        timeout: int = None, 
        referer: str = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[str]:
        """带重试的HTML获取
        
        Args:
            url: 页面URL
            timeout: 超时时间（秒）
            referer: Referer头
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            HTML页面内容，失败返回None
        """
        if timeout is None:
            timeout = settings.DEFAULT_TIMEOUT
        
        for attempt in range(max_retries):
            try:
                result = await EnhancedHttpClient._fetch_html_single(url, timeout, referer)
                if result:
                    logger.info(f"获取HTML成功 (尝试 {attempt + 1}/{max_retries}): {url}")
                    return result
                
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"获取HTML失败，{delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {url}")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(f"获取HTML异常，{delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"获取HTML最终失败 (共 {max_retries} 次尝试): {str(e)}")
        
        return None
    
    @staticmethod
    async def _fetch_html_single(url: str, timeout: int, referer: str = None) -> Optional[str]:
        """单次HTML获取"""
        # 随机选择用户代理
        user_agent = random.choice(EnhancedHttpClient.USER_AGENTS)
        
        for i, strategy in enumerate(EnhancedHttpClient.REQUEST_STRATEGIES):
            try:
                logger.debug(f"尝试获取HTML (策略 {i+1}/{len(EnhancedHttpClient.REQUEST_STRATEGIES)} - {strategy['description']}): {url}")
                
                # 创建连接器
                connector = TCPConnector(
                    limit=settings.MAX_CONCURRENT_REQUESTS,
                    ssl=False,  # 跳过SSL证书验证
                    use_dns_cache=True,
                    ttl_dns_cache=300,
                    enable_cleanup_closed=True,
                )
                
                # 创建超时设置
                client_timeout = ClientTimeout(
                    total=timeout,
                    connect=10,
                    sock_read=30
                )
                
                # 准备请求头
                headers = strategy['headers'].copy()
                headers['User-Agent'] = user_agent
                
                if referer:
                    headers['Referer'] = referer
                
                async with aiohttp.ClientSession(
                    timeout=client_timeout,
                    connector=connector,
                    headers=headers
                ) as session:
                    async with session.get(url) as response:
                        logger.debug(f"响应状态码: {response.status} (策略: {strategy['description']})")
                        
                        if response.status == 200:
                            html = await response.text()
                            logger.info(f"获取HTML成功，长度: {len(html)} (使用策略: {strategy['description']})")
                            return html
                        elif response.status == 403:
                            logger.warning(f"访问被拒绝 (403): {url}")
                            # 对于403错误，尝试下一个策略
                            continue
                        else:
                            logger.warning(f"请求失败: {url}, 状态码: {response.status} (策略: {strategy['description']})")
                            
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"请求异常 (策略 {i+1} - {strategy['description']}): {url}, 错误: {error_msg}")
                
                # 如果是Brotli相关错误，继续尝试下一个策略
                if 'brotli' in error_msg.lower() or 'br' in error_msg.lower() or 'content-encoding' in error_msg.lower():
                    logger.info(f"检测到压缩问题，尝试下一个策略...")
                    continue
                
                # 如果是连接相关错误，也尝试下一个策略
                if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
                    if i < len(EnhancedHttpClient.REQUEST_STRATEGIES) - 1:
                        logger.info(f"检测到连接问题，尝试下一个策略...")
                        continue
                
                # 如果不是最后一个策略，继续尝试
                if i < len(EnhancedHttpClient.REQUEST_STRATEGIES) - 1:
                    continue
        
        # 所有策略都失败了
        logger.error(f"所有请求策略都失败了: {url}")
        return None
'''
        
        # 写入文件
        with open('app/utils/enhanced_http_client.py', 'w', encoding='utf-8') as f:
            f.write(http_client_content)
        
        logger.info("HTTP客户端优化完成")
    
    def optimize_toc_parser(self):
        """优化目录解析器"""
        logger.info("优化目录解析器...")
        
        toc_parser_content = '''
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

                # 合并结果
                for page_chapters in other_chapters:
                    chapters.extend(page_chapters)

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
'''
        
        # 写入文件
        with open('app/parsers/enhanced_toc_parser.py', 'w', encoding='utf-8') as f:
            f.write(toc_parser_content)
        
        logger.info("目录解析器优化完成")
    
    def optimize_chapter_parser(self):
        """优化章节解析器"""
        logger.info("优化章节解析器...")
        
        chapter_parser_content = '''
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
                content = content_element.get_text(separator="\\n", strip=True)
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
            r"\\(本章完\\)",
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
        content = re.sub(r'\\s+', ' ', content)
        
        # 移除空行
        lines = content.split('\\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        # 重新组合
        content = '\\n'.join(lines)
        
        return content
'''
        
        # 写入文件
        with open('app/parsers/enhanced_chapter_parser.py', 'w', encoding='utf-8') as f:
            f.write(chapter_parser_content)
        
        logger.info("章节解析器优化完成")
    
    def optimize_error_handling(self):
        """优化错误处理"""
        logger.info("优化错误处理...")
        
        error_handler_content = '''
"""
增强错误处理器
提供更好的错误处理和恢复机制
"""
import logging
import traceback
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class EnhancedErrorHandler:
    """增强错误处理器"""
    
    @staticmethod
    def handle_request_error(error: Exception, url: str, context: str = "") -> None:
        """处理请求错误
        
        Args:
            error: 异常对象
            url: 请求URL
            context: 上下文信息
        """
        error_msg = str(error)
        
        # 根据错误类型进行分类处理
        if "timeout" in error_msg.lower():
            logger.warning(f"请求超时 {context}: {url}")
        elif "connection" in error_msg.lower():
            logger.warning(f"连接失败 {context}: {url}")
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            logger.warning(f"访问被拒绝 {context}: {url}")
        elif "404" in error_msg:
            logger.warning(f"页面不存在 {context}: {url}")
        elif "ssl" in error_msg.lower():
            logger.warning(f"SSL证书问题 {context}: {url}")
        else:
            logger.error(f"未知错误 {context}: {url} - {error_msg}")
    
    @staticmethod
    def handle_parse_error(error: Exception, source_name: str, context: str = "") -> None:
        """处理解析错误
        
        Args:
            error: 异常对象
            source_name: 书源名称
            context: 上下文信息
        """
        error_msg = str(error)
        
        if "beautifulsoup" in error_msg.lower():
            logger.warning(f"HTML解析错误 {context}: {source_name}")
        elif "selector" in error_msg.lower():
            logger.warning(f"选择器错误 {context}: {source_name}")
        else:
            logger.error(f"解析错误 {context}: {source_name} - {error_msg}")
    
    @staticmethod
    def safe_execute(func: Callable, *args, **kwargs) -> Optional[Any]:
        """安全执行函数
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值，失败返回None
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数执行失败: {func.__name__} - {str(e)}")
            return None
    
    @staticmethod
    def get_error_summary() -> dict:
        """获取错误统计
        
        Returns:
            错误统计信息
        """
        # 这里可以实现错误统计功能
        return {
            "total_errors": 0,
            "request_errors": 0,
            "parse_errors": 0,
            "timeout_errors": 0
        }
'''
        
        # 写入文件
        with open('app/utils/enhanced_error_handler.py', 'w', encoding='utf-8') as f:
            f.write(error_handler_content)
        
        logger.info("错误处理优化完成")
    
    def optimize_retry_mechanism(self):
        """优化重试机制"""
        logger.info("优化重试机制...")
        
        retry_mechanism_content = '''
"""
增强重试机制
提供更智能的重试策略
"""
import asyncio
import logging
import random
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


class EnhancedRetryMechanism:
    """增强重试机制"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """初始化重试机制
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Optional[Any]:
        """带重试的函数执行
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值，失败返回None
        """
        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                if result:
                    logger.debug(f"函数执行成功 (尝试 {attempt + 1}/{self.max_retries})")
                    return result
                
                if attempt < self.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"函数返回空结果，{delay}秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"函数执行异常，{delay}秒后重试 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"函数执行最终失败 (共 {self.max_retries} 次尝试): {str(e)}")
        
        return None
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算延迟时间
        
        Args:
            attempt: 当前尝试次数
            
        Returns:
            延迟时间（秒）
        """
        # 指数退避 + 随机抖动
        delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0, 0.1 * delay)
        return delay + jitter
    
    @staticmethod
    def should_retry(error: Exception) -> bool:
        """判断是否应该重试
        
        Args:
            error: 异常对象
            
        Returns:
            是否应该重试
        """
        error_msg = str(error).lower()
        
        # 可重试的错误
        retryable_errors = [
            "timeout",
            "connection",
            "temporary",
            "rate limit",
            "too many requests"
        ]
        
        # 不可重试的错误
        non_retryable_errors = [
            "404",
            "not found",
            "forbidden",
            "unauthorized",
            "invalid"
        ]
        
        for retryable in retryable_errors:
            if retryable in error_msg:
                return True
        
        for non_retryable in non_retryable_errors:
            if non_retryable in error_msg:
                return False
        
        # 默认重试
        return True
'''
        
        # 写入文件
        with open('app/utils/enhanced_retry_mechanism.py', 'w', encoding='utf-8') as f:
            f.write(retry_mechanism_content)
        
        logger.info("重试机制优化完成")
    
    def apply_all_optimizations(self):
        """应用所有优化"""
        logger.info("开始应用所有优化...")
        
        for name, optimization in self.optimizations.items():
            try:
                logger.info(f"应用优化: {name}")
                optimization()
            except Exception as e:
                logger.error(f"应用优化 {name} 失败: {str(e)}")
        
        logger.info("所有优化应用完成！")

def main():
    """主函数"""
    optimizer = EnhancedDownloadOptimizer()
    optimizer.apply_all_optimizations()

if __name__ == "__main__":
    main()