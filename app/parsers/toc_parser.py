import asyncio
import logging
import re
import time
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.chapter import ChapterInfo
from app.utils.http_client import HttpClient

logger = logging.getLogger(__name__)


class TocParsingStats:
    """目录解析统计信息"""
    
    def __init__(self):
        self.start_time = time.time()
        self.phases = {}
        self.current_phase = None
        self.current_phase_start = None
    
    def start_phase(self, phase_name: str):
        """开始一个解析阶段"""
        if self.current_phase:
            self.end_phase()
        
        self.current_phase = phase_name
        self.current_phase_start = time.time()
        logger.debug(f"开始阶段: {phase_name}")
    
    def end_phase(self):
        """结束当前解析阶段"""
        if self.current_phase and self.current_phase_start:
            duration = time.time() - self.current_phase_start
            self.phases[self.current_phase] = duration
            logger.debug(f"结束阶段: {self.current_phase} (耗时: {duration:.2f}s)")
            self.current_phase = None
            self.current_phase_start = None
    
    def get_total_time(self) -> float:
        """获取总耗时"""
        return time.time() - self.start_time
    
    def get_stats_summary(self) -> dict:
        """获取统计摘要"""
        if self.current_phase:
            self.end_phase()
        
        return {
            "total_time": round(self.get_total_time(), 2),
            "phases": {k: round(v, 2) for k, v in self.phases.items()}
        }


class TocParser:
    """目录解析器，用于解析小说目录页面"""

    def __init__(self, source: Source):
        """初始化目录解析器

        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("toc", {}).get(
            "timeout", settings.DEFAULT_TIMEOUT
        )
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", ""),
        }
        self.toc_rule = source.rule.get("toc", {})
        self.base_url = source.rule.get("url", "")

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
        # 初始化性能统计
        stats = TocParsingStats()
        stats.start_phase("初始化")
        
        logger.info(f"开始解析目录: {url}")
        
        # 获取目录URL
        toc_url = self._get_toc_url(url)
        logger.info(f"构建的目录URL: {toc_url}")
        
        stats.start_phase("获取页面内容")
        
        # 多策略获取目录
        chapters = await self._parse_toc_with_strategies(toc_url)
        
        if not chapters:
            stats.start_phase("备用解析")
            logger.warning(f"所有策略都未能获取到目录，尝试备用方法")
            chapters = await self._fallback_toc_parsing(url, toc_url)
            if not chapters:
                logger.error(f"从书源 {self.source.rule.get('name', self.source.id)} 获取目录失败: {toc_url}")
                stats.end_phase()
                logger.info(f"解析统计: {stats.get_stats_summary()}")
                return []

        stats.start_phase("处理分页")
        
        # 处理分页
        if self.toc_rule.get("has_pages", False) or self.toc_rule.get("pagination", False):
            logger.info("处理目录分页...")
            additional_chapters = await self._handle_pagination(toc_url)
            # 重新分配章节顺序以确保连续性
            current_order = len(chapters) + 1
            for chapter in additional_chapters:
                chapter.order = current_order
                current_order += 1
            chapters.extend(additional_chapters)

        stats.start_phase("数据清洗")
        
        # 数据清洗和验证
        chapters = self._clean_and_validate_chapters(chapters)
        
        stats.start_phase("智能排序")
        
        # 智能排序章节（在去重之后进行）
        chapters = self._smart_sort_chapters(chapters)

        stats.start_phase("结果处理")
        
        # 截取指定范围的章节
        start_idx = max(0, start - 1)
        if end == float("inf"):
            end_idx = len(chapters)
        else:
            end_idx = min(len(chapters), int(end))

        result_chapters = chapters[start_idx:end_idx]
        
        # 结束统计
        stats.end_phase()
        stats_summary = stats.get_stats_summary()

        logger.info(
            f"书源 {self.source.rule.get('name', self.source.id)} "
            f"获取到 {len(result_chapters)} 个章节（总共 {len(chapters)} 个）"
        )
        logger.info(f"解析性能统计: 总耗时 {stats_summary['total_time']}s, 各阶段: {stats_summary['phases']}")
        
        return result_chapters

    def _get_toc_url(self, url: str) -> str:
        """获取目录URL

        Args:
            url: 小说详情页URL

        Returns:
            目录URL
        """
        # 检查是否有URL转换规则
        url_transform = self.toc_rule.get("url_transform", {})
        if url_transform:
            pattern = url_transform.get("pattern", "")
            replacement = url_transform.get("replacement", "")
            if pattern and replacement:
                import re
                toc_url = re.sub(pattern, replacement, url)
                logger.info(f"URL转换: {url} -> {toc_url}")
                return toc_url
        
        # 检查是否有URL模板
        url_template = self.toc_rule.get("url_template", "")
        if url_template:
            # 替换占位符
            toc_url = url_template.replace("{book_url}", url).replace("{url}", url)
            logger.info(f"URL模板: {url_template} -> {toc_url}")
            return toc_url
        
        # 如果配置了目录URL模板（旧格式），使用模板构建
        toc_url_template = self.toc_rule.get("url", "")
        if toc_url_template and toc_url_template.startswith("http"):
            # 替换占位符
            toc_url = toc_url_template.replace("{url}", url)
            return toc_url

        # 否则直接使用详情页URL
        return url

    def _get_toc_page_url(self, toc_url: str, page: int) -> str:
        """获取分页目录URL

        Args:
            toc_url: 目录URL
            page: 页码

        Returns:
            分页目录URL
        """
        # 如果URL包含页码占位符，替换占位符
        if "{page}" in toc_url:
            return toc_url.replace("{page}", str(page))

        # 否则在URL后添加页码参数
        separator = "&" if "?" in toc_url else "?"
        return f"{toc_url}{separator}page={page}"

    async def _fetch_html(self, url: str) -> Optional[str]:
        """获取HTML页面

        Args:
            url: 页面URL

        Returns:
            HTML页面内容，失败返回None
        """
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                result = await HttpClient.fetch_html(url, self.timeout, self.source.rule.get("url", ""))
                if result:
                    if attempt > 0:
                        logger.info(f"第 {attempt + 1} 次尝试成功获取页面: {url}")
                    return result
                
                if attempt == 0:
                    logger.warning(f"第一次请求失败，准备重试: {url}")
                
            except asyncio.TimeoutError:
                logger.warning(f"请求超时（第 {attempt + 1} 次）: {url}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # 指数退避
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    await asyncio.sleep(delay)
                
            except aiohttp.ClientError as e:
                logger.warning(f"网络错误（第 {attempt + 1} 次）: {url} - {str(e)}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"未知错误（第 {attempt + 1} 次）: {url} - {str(e)}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        logger.error(f"获取页面最终失败（共 {max_retries} 次尝试）: {url}")
        return None

    async def _fetch_html_single(self, url: str) -> Optional[str]:
        """获取单个HTML页面（用于分页请求）

        Args:
            url: 页面URL

        Returns:
            HTML页面内容，失败返回None
        """
        # 使用统一的HTTP客户端
        referer = self.source.rule.get("url", "")
        return await HttpClient.fetch_html(url, self.timeout, referer)

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

    async def _parse_toc_with_strategies(self, toc_url: str) -> List[ChapterInfo]:
        """使用多种策略解析目录"""
        strategies = [
            ("标准解析", self._parse_standard),
            ("智能选择器", self._parse_with_smart_selectors),
            ("正则表达式", self._parse_with_regex),
            ("JavaScript处理", self._parse_with_js_processing)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"尝试策略: {strategy_name}")
                chapters = await strategy_func(toc_url)
                if chapters:
                    logger.info(f"策略 {strategy_name} 成功，获取到 {len(chapters)} 个章节")
                    return chapters
                else:
                    logger.warning(f"策略 {strategy_name} 未获取到章节")
            except Exception as e:
                logger.warning(f"策略 {strategy_name} 失败: {str(e)}")
                continue
        
        return []

    async def _parse_standard(self, toc_url: str) -> List[ChapterInfo]:
        """标准解析方法"""
        html = await self._fetch_html(toc_url)
        if not html:
            return []
        
        return self._parse_toc(html, toc_url)

    async def _parse_with_smart_selectors(self, toc_url: str) -> List[ChapterInfo]:
        """使用智能选择器解析"""
        html = await self._fetch_html(toc_url)
        if not html:
            return []
        
        # 尝试多种常见的目录选择器
        smart_selectors = [
            self.toc_rule.get("list", ""),
            self.toc_rule.get("item", ""),
            ".catalog a", ".chapter-list a", ".list-chapter a",
            ".book-chapter a", ".content a", "ul li a",
            ".section-list a", ".chapter a", ".mulu a",
            "dd a", "dt a", ".box a", ".list a"
        ]
        
        soup = BeautifulSoup(html, "html.parser")
        
        for selector in smart_selectors:
            if not selector.strip():
                continue
                
            try:
                elements = soup.select(selector)
                if elements and len(elements) > 5:  # 至少要有5个章节才认为是有效的
                    logger.info(f"智能选择器 '{selector}' 找到 {len(elements)} 个元素")
                    chapters = self._extract_chapters_from_elements(elements, toc_url)
                    if chapters:
                        return chapters
            except Exception as e:
                logger.debug(f"选择器 '{selector}' 解析失败: {str(e)}")
                continue
        
        return []

    async def _parse_with_regex(self, toc_url: str) -> List[ChapterInfo]:
        """使用正则表达式解析"""
        html = await self._fetch_html(toc_url)
        if not html:
            return []
        
        # 常见的章节链接正则模式
        patterns = [
            r'<a[^>]*href="([^"]*)"[^>]*>([^<]*第\s*\d+\s*章[^<]*)</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>([^<]*章节[^<]*)</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>([^<]*\d+[^<]*)</a>',
            r'href="([^"]*)"[^>]*>([^<]*第.*?章[^<]*)',
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                if matches and len(matches) > 5:
                    logger.info(f"正则模式找到 {len(matches)} 个匹配")
                    chapters = []
                    for i, (href, title) in enumerate(matches):
                        if href and title:
                            full_url = urljoin(toc_url, href)
                            chapter = ChapterInfo(
                                title=title.strip(),
                                url=full_url,
                                order=i + 1
                            )
                            chapters.append(chapter)
                    
                    if chapters:
                        return chapters
            except Exception as e:
                logger.debug(f"正则模式解析失败: {str(e)}")
                continue
        
        return []

    async def _parse_with_js_processing(self, toc_url: str) -> List[ChapterInfo]:
        """处理包含JavaScript的目录页面"""
        html = await self._fetch_html(toc_url)
        if not html:
            return []
        
        # 检查是否包含JavaScript处理逻辑
        js_rule = self.toc_rule.get("list", "")
        if "@js:" in js_rule:
            try:
                # 简单的JavaScript处理（主要是字符串替换）
                js_code = js_rule.split("@js:")[1]
                # 这里可以添加更复杂的JavaScript执行逻辑
                # 目前只处理简单的字符串操作
                if "replace" in js_code:
                    # 执行简单的字符串替换
                    html = self._execute_simple_js(html, js_code)
                
                # 重新解析处理后的HTML
                soup = BeautifulSoup(html, "html.parser")
                item_selector = self.toc_rule.get("item", "a")
                elements = soup.select(item_selector)
                
                if elements:
                    return self._extract_chapters_from_elements(elements, toc_url)
                    
            except Exception as e:
                logger.warning(f"JavaScript处理失败: {str(e)}")
        
        return []

    def _execute_simple_js(self, html: str, js_code: str) -> str:
        """执行简单的JavaScript代码（主要是字符串操作）"""
        try:
            # 处理简单的replace操作
            if "replace" in js_code:
                import re
                # 提取replace操作
                replace_pattern = r'r\.replace\(([^,]+),\s*([^)]+)\)'
                matches = re.findall(replace_pattern, js_code)
                
                for pattern_str, replacement_str in matches:
                    # 清理引号
                    pattern_str = pattern_str.strip('\'"')
                    replacement_str = replacement_str.strip('\'"')
                    
                    # 执行替换
                    html = re.sub(pattern_str, replacement_str, html, flags=re.DOTALL)
            
            return html
        except Exception as e:
            logger.warning(f"JavaScript执行失败: {str(e)}")
            return html

    async def _fallback_toc_parsing(self, detail_url: str, toc_url: str) -> List[ChapterInfo]:
        """备用目录解析方法"""
        logger.info("尝试备用目录解析方法")
        
        # 尝试在详情页直接查找目录链接
        html = await self._fetch_html(detail_url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            
            # 查找可能的目录区域
            toc_areas = soup.find_all(['div', 'ul', 'ol'], 
                                     class_=re.compile(r'(catalog|chapter|list|mulu|content)', re.I))
            
            for area in toc_areas:
                links = area.find_all('a', href=True)
                if len(links) > 5:  # 至少5个链接才认为是目录
                    chapters = self._extract_chapters_from_elements(links, detail_url)
                    if chapters:
                        logger.info(f"备用方法在详情页找到 {len(chapters)} 个章节")
                        return chapters
        
        return []

    def _extract_chapters_from_elements(self, elements, base_url: str) -> List[ChapterInfo]:
        """从HTML元素中提取章节信息"""
        chapters = []
        
        for i, element in enumerate(elements):
            try:
                # 获取链接
                if element.name == 'a':
                    href = element.get('href', '')
                    title = element.get_text(strip=True)
                else:
                    link = element.find('a')
                    if not link:
                        continue
                    href = link.get('href', '')
                    title = link.get_text(strip=True)
                
                if not href or not title:
                    continue
                
                # 过滤无效链接
                if href in ['#', 'javascript:void(0)', 'javascript:;']:
                    continue
                
                # 过滤目录类项与范围链接
                if any(k in title for k in ['目录', '查看完整目录']):
                    continue
                import re as _re
                if _re.search(r'第\s*\d+\s*[-—]+\s*\d+\s*章', title):
                    continue
                if _re.search(r'(?:/list/|chapternum)', href):
                    continue
                
                # 构建完整URL
                full_url = urljoin(base_url, href)
                
                # 验证URL有效性
                if not self._is_valid_chapter_url(full_url):
                    continue
                
                # 清理标题
                clean_title = self._clean_title(title)
                if not clean_title or len(clean_title) < 2:
                    continue
                
                chapter = ChapterInfo(
                    title=clean_title,
                    url=full_url,
                    order=i + 1
                )
                chapters.append(chapter)
                
            except Exception as e:
                logger.debug(f"解析章节元素失败: {str(e)}")
                continue
        
        return chapters

    def _clean_title(self, title: str) -> str:
        """清理章节标题"""
        if not title:
            return ""
        
        # 移除多余的空白字符
        title = re.sub(r'\s+', ' ', title.strip())
        
        # 移除常见的无用文本
        useless_patterns = [
            r'\[.*?\]',  # 移除方括号内容
            r'【.*?】',   # 移除中文方括号内容
            r'\(.*?\)',  # 移除圆括号内容
            r'（.*?）',   # 移除中文圆括号内容
            r'更新时间.*',
            r'字数.*',
            r'VIP.*',
        ]
        
        for pattern in useless_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        return title.strip()

    def _is_valid_chapter_url(self, url: str) -> bool:
        """验证章节URL是否有效"""
        try:
            parsed = urlparse(url)
            
            # 必须是http或https协议
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # 必须有域名
            if not parsed.netloc:
                return False
            
            # 路径不能为空或只是根路径
            if not parsed.path or parsed.path == '/':
                return False
            
            # 排除一些明显不是章节的URL
            invalid_patterns = [
                r'\.(?:jpg|jpeg|png|gif|css|js|ico)$',  # 图片、样式、脚本文件
                r'/(?:index|home|main)(?:\.|$)',        # 主页
                r'/(?:search|login|register)(?:\.|$)',  # 搜索、登录页面
            ]
            
            for pattern in invalid_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return False
            
            return True
            
        except Exception:
            return False

    def _clean_and_validate_chapters(self, chapters: List[ChapterInfo]) -> List[ChapterInfo]:
        """清洗和验证章节列表"""
        if not chapters:
            return []
        
        logger.info(f"开始清洗章节列表，原始章节数: {len(chapters)}")
        
        # 第一步：基本验证，过滤掉明显无效的章节
        valid_chapters = []
        for chapter in chapters:
            if (len(chapter.title) >= 2 and 
                not re.match(r'^[\s\-_\.]*$', chapter.title) and
                self._is_valid_chapter_url(chapter.url)):
                valid_chapters.append(chapter)
        
        logger.info(f"基本验证后剩余章节数: {len(valid_chapters)}")
        
        # 第二步：智能去重 - 处理重复章节
        deduplicated_chapters = self._smart_deduplication(valid_chapters)
        
        logger.info(f"去重后剩余章节数: {len(deduplicated_chapters)}")
        
        # 第三步：重新排序
        for i, chapter in enumerate(deduplicated_chapters):
            chapter.order = i + 1
        
        logger.info(f"章节清洗完成：原始 {len(chapters)} 个，最终 {len(deduplicated_chapters)} 个")
        return deduplicated_chapters

    def _smart_deduplication(self, chapters: List[ChapterInfo]) -> List[ChapterInfo]:
        """智能去重处理
        
        处理策略：
        1. 基于URL的严格去重
        2. 基于标题的智能去重（考虑章节编号）
        3. 保留质量更好的章节（URL更完整、标题更规范）
        """
        if not chapters:
            return []
        
        # 基于URL去重
        url_seen = {}
        url_deduplicated = []
        
        for chapter in chapters:
            if chapter.url not in url_seen:
                url_seen[chapter.url] = chapter
                url_deduplicated.append(chapter)
            else:
                # 如果URL重复，保留标题更好的那个
                existing = url_seen[chapter.url]
                if self._is_better_chapter(chapter, existing):
                    # 替换为更好的章节
                    url_seen[chapter.url] = chapter
                    # 在列表中也替换
                    for i, c in enumerate(url_deduplicated):
                        if c.url == chapter.url:
                            url_deduplicated[i] = chapter
                            break
        
        logger.info(f"URL去重完成: {len(chapters)} -> {len(url_deduplicated)}")
        
        # 基于标题的智能去重
        title_deduplicated = self._deduplicate_by_title(url_deduplicated)
        
        return title_deduplicated
    
    def _is_better_chapter(self, chapter1: ChapterInfo, chapter2: ChapterInfo) -> bool:
        """判断章节1是否比章节2更好
        
        判断标准：
        1. 标题更规范（包含章节编号）
        2. URL更完整
        3. 标题更长（更详细）
        """
        # 检查标题是否包含章节编号
        number1 = self._extract_chapter_number(chapter1.title)
        number2 = self._extract_chapter_number(chapter2.title)
        
        if number1 > 0 and number2 == 0:
            return True
        if number2 > 0 and number1 == 0:
            return False
        
        # 检查URL完整性
        if len(chapter1.url) > len(chapter2.url):
            return True
        if len(chapter2.url) > len(chapter1.url):
            return False
        
        # 检查标题长度
        return len(chapter1.title) > len(chapter2.title)
    
    def _deduplicate_by_title(self, chapters: List[ChapterInfo]) -> List[ChapterInfo]:
        """基于标题的智能去重"""
        if not chapters:
            return []
        
        # 提取所有章节的编号和标题
        chapter_info = []
        for chapter in chapters:
            number = self._extract_chapter_number(chapter.title)
            normalized_title = self._normalize_title(chapter.title)
            chapter_info.append((number, normalized_title, chapter))
        
        # 基于章节编号去重
        number_seen = {}
        result = []
        
        for number, normalized_title, chapter in chapter_info:
            if number > 0:  # 有明确章节编号的
                if number not in number_seen:
                    number_seen[number] = chapter
                    result.append(chapter)
                else:
                    # 如果章节编号重复，保留更好的那个
                    existing = number_seen[number]
                    if self._is_better_chapter(chapter, existing):
                        number_seen[number] = chapter
                        # 在结果中替换
                        for i, c in enumerate(result):
                            if self._extract_chapter_number(c.title) == number:
                                result[i] = chapter
                                break
            else:
                # 没有明确章节编号的，基于标题去重
                title_exists = False
                for existing_chapter in result:
                    existing_normalized = self._normalize_title(existing_chapter.title)
                    if self._titles_are_similar(normalized_title, existing_normalized):
                        title_exists = True
                        break
                
                if not title_exists:
                    result.append(chapter)
        
        logger.info(f"标题去重完成: {len(chapters)} -> {len(result)}")
        return result
    
    def _normalize_title(self, title: str) -> str:
        """标准化章节标题，用于比较"""
        if not title:
            return ""
        
        # 移除常见的前缀后缀
        title = re.sub(r'^第\s*\d+\s*章\s*', '', title)  # 移除"第X章"
        title = re.sub(r'^\d+[\.\-\s]+', '', title)      # 移除"123. "或"123-"
        title = re.sub(r'\s*\(.*?\)\s*$', '', title)     # 移除结尾的括号内容
        title = re.sub(r'\s*【.*?】\s*$', '', title)      # 移除结尾的中文括号内容
        
        # 标准化空白字符
        title = re.sub(r'\s+', ' ', title.strip())
        
        return title.lower()
    
    def _titles_are_similar(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """判断两个标题是否相似"""
        if not title1 or not title2:
            return False
        
        if title1 == title2:
            return True
        
        # 简单的相似度计算
        shorter = min(len(title1), len(title2))
        longer = max(len(title1), len(title2))
        
        if shorter == 0:
            return False
        
        # 计算公共子串长度
        common = 0
        for i in range(shorter):
            if i < len(title1) and i < len(title2) and title1[i] == title2[i]:
                common += 1
        
        similarity = common / longer
        return similarity >= threshold

    async def _handle_pagination(self, toc_url: str) -> List[ChapterInfo]:
        """处理目录分页"""
        additional_chapters = []
        
        try:
            # 获取第一页HTML来分析分页信息
            html = await self._fetch_html(toc_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, "html.parser")
            
            # 获取总页数
            total_pages = self._get_total_pages_enhanced(soup)
            logger.info(f"检测到目录总页数: {total_pages}")
            
            if total_pages > 1:
                # 并发获取其他页的目录
                tasks = []
                for page in range(2, min(total_pages + 1, 10)):  # 限制最多处理10页
                    page_url = self._get_toc_page_url(toc_url, page)
                    tasks.append(self._fetch_and_parse_page(page_url))
                
                if tasks:
                    other_chapters = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # 合并结果
                    for result in other_chapters:
                        if isinstance(result, Exception):
                            logger.warning(f"获取分页失败: {str(result)}")
                            continue
                        if result:
                            additional_chapters.extend(result)
            
        except Exception as e:
            logger.warning(f"处理分页失败: {str(e)}")
        
        return additional_chapters

    def _get_total_pages_enhanced(self, soup: BeautifulSoup) -> int:
        """获取总页数（增强版）"""
        try:
            # 尝试多种分页选择器
            page_selectors = [
                self.toc_rule.get("nextPage", ""),
                ".page a", ".pagination a", ".pager a",
                "a[href*='page']", "a[href*='p=']",
                "select option", ".page-select option"
            ]
            
            max_page = 1
            
            for selector in page_selectors:
                if not selector.strip():
                    continue
                
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        # 从链接中提取页码
                        href = element.get('href', '')
                        text = element.get_text(strip=True)
                        
                        # 从URL中提取页码
                        import re
                        page_matches = re.findall(r'(?:page|p)=(\d+)', href)
                        if page_matches:
                            page_num = int(page_matches[-1])
                            max_page = max(max_page, page_num)
                        
                        # 从文本中提取页码
                        if text.isdigit():
                            page_num = int(text)
                            max_page = max(max_page, page_num)
                        
                except Exception as e:
                    logger.debug(f"解析分页选择器失败 '{selector}': {str(e)}")
                    continue
            
            return min(max_page, 50)  # 限制最大页数
            
        except Exception as e:
            logger.warning(f"获取总页数失败: {str(e)}")
            return 1

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
            element: BeautifulSoup元素
            selector: CSS选择器

        Returns:
            提取的文本内容
        """
        if not selector:
            return ""

        try:
            target_element = element.select_one(selector)
            if target_element:
                return target_element.get_text(strip=True)
        except Exception as e:
            logger.warning(f"提取文本失败: {selector}, 错误: {str(e)}")

        return ""

    def _extract_attr(self, element: BeautifulSoup, selector: str, attr: str) -> str:
        """提取属性值

        Args:
            element: BeautifulSoup元素
            selector: CSS选择器
            attr: 属性名

        Returns:
            提取的属性值
        """
        if not selector:
            return ""

        try:
            target_element = element.select_one(selector)
            if target_element:
                return target_element.get(attr, "")
        except Exception as e:
            logger.warning(f"提取属性失败: {selector}.{attr}, 错误: {str(e)}")

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

            # 获取总页数选择器
            total_pages_selector = self.toc_rule.get("total_pages", "")
            if not total_pages_selector:
                return 1

            # 提取总页数
            total_pages_element = soup.select_one(total_pages_selector)
            if total_pages_element:
                total_pages_text = total_pages_element.get_text(strip=True)
                # 尝试提取数字
                import re

                numbers = re.findall(
                    r"\d+", total_pages_text
                )
                if numbers:
                    return int(numbers[-1])  # 取最后一个数字

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
        html = await self._fetch_html_single(url)
        if not html:
            return []

        return self._parse_toc(html, url)

    def _filter_latest_chapters(self, chapters: List[ChapterInfo]) -> List[ChapterInfo]:
        """过滤最新章节，只保留正文目录
        
        修改：根据用户要求，完全禁用最新章节过滤功能
        如果目录页有重复章节，将通过重新下载和排序来处理
        """
        logger.info(f"跳过最新章节过滤，保留所有 {len(chapters)} 个章节")
        return chapters
    
    def _extract_chapter_number(self, title: str) -> int:
        """从章节标题中提取章节编号"""
        if not title:
            return 0
        
        # 常见的章节编号模式
        patterns = [
            r'第\s*(\d+)\s*章',           # 第123章
            r'第\s*([一二三四五六七八九十百千万]+)\s*章',  # 第一章
            r'chapter\s*(\d+)',          # chapter 123
            r'ch\s*(\d+)',               # ch 123
            r'^(\d+)[\s\.\-]',           # 123. 或 123-
            r'(\d+)$',                   # 结尾的数字
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    number_str = match.group(1)
                    # 处理中文数字
                    if re.match(r'^[一二三四五六七八九十百千万]+$', number_str):
                        return self._chinese_to_number(number_str)
                    else:
                        return int(number_str)
                except (ValueError, IndexError):
                    continue
        
        return 0
    
    def _chinese_to_number(self, chinese_num: str) -> int:
        """将中文数字转换为阿拉伯数字（简单实现）"""
        chinese_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '百': 100, '千': 1000, '万': 10000
        }
        
        if chinese_num == '十':
            return 10
        
        result = 0
        temp = 0
        
        for char in chinese_num:
            if char in chinese_map:
                value = chinese_map[char]
                if value >= 10:
                    if temp == 0:
                        temp = 1
                    result += temp * value
                    temp = 0
                else:
                    temp = value
        
        result += temp
        return result if result > 0 else 0
    
    def _find_main_content_start(self, chapter_numbers: List[tuple]) -> int:
        """找到正文目录的开始位置
        
        Args:
            chapter_numbers: [(索引, 章节号, 章节对象), ...]
            
        Returns:
            正文目录开始的索引位置，0表示从头开始
        
        修改：使检测逻辑更加保守，减少误判
        """
        if len(chapter_numbers) <= 15:  # 提高阈值
            return 0
        
        # 策略1：寻找章节号为1的位置（更严格的条件）
        for i, (idx, number, chapter) in enumerate(chapter_numbers):
            if number == 1:
                # 检查这个位置之前是否有更大的章节号（表明前面是最新章节）
                if i > 5:  # 提高位置要求，至少要在第6个位置之后
                    prev_numbers = [num for _, num, _ in chapter_numbers[:i] if num > 0]
                    if prev_numbers and max(prev_numbers) > 20:  # 提高章节号差异要求
                        # 还要检查前面的章节是否真的像"最新章节"
                        prev_titles = [chapter.title for _, _, chapter in chapter_numbers[:i]]
                        latest_keywords = ['最新', '更新', '新增', 'latest', 'new', 'update']
                        has_latest_keywords = any(any(keyword in title.lower() for keyword in latest_keywords) 
                                                for title in prev_titles)
                        
                        if has_latest_keywords or len(prev_numbers) <= 8:  # 最新章节部分不应该太长
                            logger.info(f"在索引 {i} 找到第1章，前面有最新章节（最大章节号：{max(prev_numbers)}）")
                            return i
                
                # 如果第1章在前面几个位置，可能整个都是正文
                if i <= 3:  # 降低阈值，更保守
                    return 0
        
        # 策略2：寻找章节号重置点（从大数字突然跳到小数字）- 更严格的条件
        for i in range(1, len(chapter_numbers)):
            curr_number = chapter_numbers[i][1]
            prev_number = chapter_numbers[i-1][1]
            
            if (curr_number > 0 and prev_number > 0 and 
                curr_number < prev_number and 
                prev_number - curr_number > 100 and  # 提高章节号差异要求
                i <= 10):  # 重置点应该在前面部分
                logger.info(f"在索引 {i} 检测到章节号重置：{prev_number} -> {curr_number}")
                return i
        
        # 策略3：检测章节标题模式的变化 - 更严格的条件
        if len(chapter_numbers) > 20:  # 只对较长的章节列表应用
            title_patterns = []
            for _, _, chapter in chapter_numbers:
                pattern = self._get_title_pattern(chapter.title)
                title_patterns.append(pattern)
            
            # 寻找模式变化点
            for i in range(5, min(len(title_patterns), 15)):  # 缩小搜索范围
                # 检查前面5个和后面10个的模式
                prev_patterns = set(title_patterns[max(0, i-5):i])
                next_patterns = set(title_patterns[i:min(len(title_patterns), i+10)])
                
                # 如果模式发生显著变化，可能是从最新章节转到正文目录
                if (len(prev_patterns & next_patterns) == 0 and 
                    len(next_patterns) == 1 and 
                    "第X章" in next_patterns):  # 确保后面是标准章节格式
                    logger.info(f"在索引 {i} 检测到标题模式变化")
                    return i
        
        # 策略4：如果前面的章节标题包含"最新"、"更新"等关键词 - 更严格的条件
        latest_keywords = ['最新', '更新', '新增', 'latest', 'new', 'update']
        latest_section_end = 0
        
        for i, (_, _, chapter) in enumerate(chapter_numbers[:10]):  # 只检查前10个
            title_lower = chapter.title.lower()
            if any(keyword in title_lower for keyword in latest_keywords):
                latest_section_end = i + 1
            else:
                break  # 遇到非"最新"章节就停止
        
        if latest_section_end > 0 and latest_section_end <= 8:  # 最新章节部分不应该太长
            logger.info(f"在索引 {latest_section_end} 检测到最新章节区域结束")
            return latest_section_end
        
        return 0  # 未检测到最新章节，从头开始
    
    def _get_title_pattern(self, title: str) -> str:
        """获取章节标题的模式"""
        if not title:
            return "empty"
        
        # 简化的模式识别
        if re.search(r'第\s*\d+\s*章', title):
            return "第X章"
        elif re.search(r'第\s*[一二三四五六七八九十百千万]+\s*章', title):
            return "第X章_中文"
        elif re.search(r'chapter\s*\d+', title, re.IGNORECASE):
            return "chapter_X"
        elif re.search(r'^\d+[\.\-\s]', title):
            return "数字开头"
        else:
            return "其他"

    def _smart_sort_chapters(self, chapters: List[ChapterInfo]) -> List[ChapterInfo]:
        """智能排序章节
        
        修改：在不过滤章节的情况下，更好地排序所有章节
        优先使用章节标题中的编号进行排序，如果没有编号则保持原始顺序
        """
        if not chapters:
            return chapters
        
        logger.info(f"开始智能排序 {len(chapters)} 个章节")
        
        # 分析章节编号分布
        chapters_with_numbers = []
        chapters_without_numbers = []
        
        for chapter in chapters:
            chapter_number = self._extract_chapter_number(chapter.title)
            if chapter_number > 0:
                chapters_with_numbers.append((chapter_number, chapter.order, chapter))
            else:
                chapters_without_numbers.append(chapter)
        
        logger.info(f"有编号的章节: {len(chapters_with_numbers)}, 无编号的章节: {len(chapters_without_numbers)}")
        
        # 对有编号的章节进行排序
        chapters_with_numbers.sort(key=lambda x: (x[0], x[1]))  # 先按章节号，再按原始顺序
        
        # 重新组合章节列表
        sorted_chapters = []
        
        # 如果大部分章节都有编号，按编号排序
        if len(chapters_with_numbers) >= len(chapters) * 0.7:
            # 添加排序后的有编号章节
            for chapter_number, original_order, chapter in chapters_with_numbers:
                sorted_chapters.append(chapter)
            
            # 将无编号的章节插入到合适的位置或添加到末尾
            if chapters_without_numbers:
                # 简单策略：将无编号章节添加到末尾
                sorted_chapters.extend(chapters_without_numbers)
                logger.info("无编号章节已添加到末尾")
        else:
            # 如果大部分章节都没有编号，保持原始顺序
            logger.info("大部分章节无编号，保持原始顺序")
            sorted_chapters = chapters
        
        # 重新分配order
        for i, chapter in enumerate(sorted_chapters):
            chapter.order = i + 1
        
        # 验证排序结果
        self._validate_chapter_order(sorted_chapters)
        
        logger.info(f"章节智能排序完成")
        return sorted_chapters
    
    def _validate_chapter_order(self, chapters: List[ChapterInfo]):
        """验证章节排序结果"""
        if len(chapters) < 5:
            return
        
        # 检查前几个章节是否符合预期
        first_few_numbers = []
        for chapter in chapters[:10]:
            number = self._extract_chapter_number(chapter.title)
            if number > 0:
                first_few_numbers.append(number)
        
        if first_few_numbers:
            # 检查是否基本有序
            is_ascending = all(first_few_numbers[i] <= first_few_numbers[i+1] 
                             for i in range(len(first_few_numbers)-1))
            
            if is_ascending:
                logger.info(f"章节排序验证通过，前几章编号：{first_few_numbers[:5]}")
            else:
                logger.warning(f"章节排序可能有问题，前几章编号：{first_few_numbers[:5]}")
        
        # 输出前几个章节标题用于调试
        logger.debug("排序后前几个章节：")
        for i, chapter in enumerate(chapters[:5]):
            logger.debug(f"  {i+1}. {chapter.title}")
