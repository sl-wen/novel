import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.chapter import Chapter
from app.utils.content_validator import ChapterValidator
from app.utils.http_client import HttpClient

logger = logging.getLogger(__name__)


class ChapterParser:
    """章节解析器，用于解析小说章节内容页面"""

    def __init__(self, source: Source):
        """初始化章节解析器

        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("chapter", {}).get(
            "timeout", settings.DEFAULT_TIMEOUT
        )
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", ""),
        }
        self.chapter_rule = source.rule.get("chapter", {})
        self.content_validator = ChapterValidator()

    async def parse(self, url: str, title: str = "未知章节", order: int = 1) -> Chapter:
        """解析章节内容

        Args:
            url: 章节URL
            title: 章节标题
            order: 章节序号

        Returns:
            章节对象
        """
        logger.debug(f"开始解析章节: {title} - {url}")
        
        # 多策略获取章节内容
        content = await self._parse_content_with_strategies(url, title)
        
        if not content:
            logger.warning(f"所有策略都未能获取章节内容: {title}")
            content = "获取章节内容失败"

        # 创建章节对象
        chapter = Chapter(url=url, title=title, content=content, order=order)
        
        logger.debug(f"章节解析完成: {title} ({len(content)} 字符)")
        return chapter

    async def _parse_content_with_strategies(self, url: str, title: str) -> str:
        """使用多种策略解析章节内容"""
        strategies = [
            ("标准解析", self._parse_standard_content),
            ("智能内容提取", self._parse_with_smart_extraction),
            ("正则表达式提取", self._parse_with_regex_extraction),
            ("JavaScript处理", self._parse_with_js_processing),
            ("备用提取方法", self._parse_with_fallback_methods)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.debug(f"尝试策略: {strategy_name} - {title}")
                content = await strategy_func(url)
                
                if content and len(content.strip()) >= settings.MIN_CHAPTER_LENGTH:
                    # 验证内容质量
                    quality_score = self.content_validator.get_chapter_quality_score(content)
                    if quality_score >= 0.3:  # 质量阈值
                        logger.debug(f"策略 {strategy_name} 成功，内容长度: {len(content)}")
                        return self._clean_content(content)
                    else:
                        logger.debug(f"策略 {strategy_name} 内容质量过低: {quality_score}")
                else:
                    logger.debug(f"策略 {strategy_name} 内容过短或为空")
                    
            except Exception as e:
                logger.warning(f"策略 {strategy_name} 失败: {str(e)}")
                continue
        
        return ""

    async def _parse_standard_content(self, url: str) -> str:
        """标准内容解析"""
        html = await self._fetch_html(url)
        if not html:
            return ""
        
        return self._parse_chapter_content(html)

    async def _parse_with_smart_extraction(self, url: str) -> str:
        """智能内容提取"""
        html = await self._fetch_html(url)
        if not html:
            return ""
        
        soup = BeautifulSoup(html, "html.parser")
        
        # 尝试多种内容选择器
        content_selectors = [
            self.chapter_rule.get("content", ""),
            "#content", ".content", "#chapter-content", ".chapter-content",
            ".book-content", "#book-content", ".novel-content", "#novel-content",
            ".text", "#text", ".chapter", "#chapter", ".main-content",
            "article", ".article", "#article", ".post-content", ".entry-content"
        ]
        
        for selector in content_selectors:
            if not selector.strip():
                continue
                
            try:
                element = soup.select_one(selector)
                if element:
                    # 移除广告和无关元素
                    self._remove_unwanted_elements(element)
                    
                    content = element.get_text(separator="\n", strip=True)
                    if content and len(content) >= settings.MIN_CHAPTER_LENGTH:
                        logger.debug(f"智能选择器 '{selector}' 提取成功")
                        return content
                        
            except Exception as e:
                logger.debug(f"选择器 '{selector}' 提取失败: {str(e)}")
                continue
        
        return ""

    async def _parse_with_regex_extraction(self, url: str) -> str:
        """使用正则表达式提取内容"""
        html = await self._fetch_html(url)
        if not html:
            return ""
        
        # 常见的内容提取正则模式
        patterns = [
            r'<div[^>]*(?:class|id)="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*(?:class|id)="[^"]*chapter[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
            r'<p[^>]*>(.*?)</p>',  # 提取所有段落
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if matches:
                    # 合并匹配的内容
                    content_parts = []
                    for match in matches:
                        # 清理HTML标签
                        clean_text = re.sub(r'<[^>]+>', '', match)
                        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                        if clean_text and len(clean_text) > 20:  # 过滤太短的片段
                            content_parts.append(clean_text)
                    
                    if content_parts:
                        content = '\n\n'.join(content_parts)
                        if len(content) >= settings.MIN_CHAPTER_LENGTH:
                            logger.debug(f"正则表达式提取成功，内容长度: {len(content)}")
                            return content
                            
            except Exception as e:
                logger.debug(f"正则表达式提取失败: {str(e)}")
                continue
        
        return ""

    async def _parse_with_js_processing(self, url: str) -> str:
        """处理包含JavaScript的章节内容"""
        html = await self._fetch_html(url)
        if not html:
            return ""
        
        # 检查是否包含JavaScript处理逻辑
        content_rule = self.chapter_rule.get("content", "")
        if "@js:" in content_rule:
            try:
                # 执行JavaScript处理
                js_code = content_rule.split("@js:")[1]
                processed_html = self._execute_content_js(html, js_code)
                
                # 重新解析处理后的HTML
                soup = BeautifulSoup(processed_html, "html.parser")
                
                # 提取内容
                content_selector = content_rule.split("@js:")[0].strip()
                if content_selector:
                    element = soup.select_one(content_selector)
                    if element:
                        self._remove_unwanted_elements(element)
                        return element.get_text(separator="\n", strip=True)
                
            except Exception as e:
                logger.warning(f"JavaScript处理失败: {str(e)}")
        
        return ""

    async def _parse_with_fallback_methods(self, url: str) -> str:
        """备用内容提取方法"""
        html = await self._fetch_html(url)
        if not html:
            return ""
        
        soup = BeautifulSoup(html, "html.parser")
        
        # 移除明显的非内容元素
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # 查找最可能包含内容的元素
        content_candidates = []
        
        # 查找包含大量文本的div元素
        divs = soup.find_all('div')
        for div in divs:
            text = div.get_text(strip=True)
            if len(text) > 200:  # 至少200字符
                content_candidates.append((len(text), text))
        
        # 查找所有段落
        paragraphs = soup.find_all('p')
        if len(paragraphs) > 3:  # 至少3个段落
            paragraph_texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            if paragraph_texts:
                combined_text = '\n\n'.join(paragraph_texts)
                if len(combined_text) > 200:
                    content_candidates.append((len(combined_text), combined_text))
        
        # 选择最长的内容
        if content_candidates:
            content_candidates.sort(key=lambda x: x[0], reverse=True)
            return content_candidates[0][1]
        
        return ""

    def _execute_content_js(self, html: str, js_code: str) -> str:
        """执行内容相关的JavaScript代码"""
        try:
            # 处理base64解码
            if "qsbs.bb" in js_code:
                # 查找base64编码的内容
                import base64
                
                pattern = r"qsbs\.bb\('([^']+)'\)"
                matches = re.findall(pattern, html)
                
                for match in matches:
                    try:
                        decoded = base64.b64decode(match).decode('utf-8')
                        html = html.replace(f"qsbs.bb('{match}')", decoded)
                    except Exception:
                        continue
            
            # 处理其他字符串替换
            if "replace" in js_code:
                replace_patterns = re.findall(r'r\.replace\(([^,]+),\s*([^)]+)\)', js_code)
                for pattern_str, replacement_str in replace_patterns:
                    pattern_str = pattern_str.strip('\'"')
                    replacement_str = replacement_str.strip('\'"')
                    html = re.sub(pattern_str, replacement_str, html, flags=re.DOTALL)
            
            return html
            
        except Exception as e:
            logger.warning(f"JavaScript执行失败: {str(e)}")
            return html

    def _remove_unwanted_elements(self, element):
        """移除不需要的元素"""
        # 移除广告、导航等元素
        unwanted_selectors = [
            'script', 'style', 'nav', 'header', 'footer', 'aside',
            '.ad', '.advertisement', '.banner', '.nav', '.navigation',
            '.sidebar', '.menu', '.breadcrumb', '.pagination',
            '[class*="ad"]', '[id*="ad"]', '[class*="banner"]'
        ]
        
        for selector in unwanted_selectors:
            try:
                for unwanted in element.select(selector):
                    unwanted.decompose()
            except Exception:
                continue

    def _clean_content(self, content: str) -> str:
        """清理章节内容"""
        if not content:
            return ""
        
        # 移除广告文本
        ad_patterns = self.chapter_rule.get("ad_patterns", [])
        for pattern in ad_patterns:
            try:
                content = re.sub(pattern, "", content, flags=re.IGNORECASE | re.MULTILINE)
            except Exception as e:
                logger.debug(f"广告过滤失败: {pattern}, 错误: {str(e)}")
        
        # 通用清理
        content = self._generic_content_cleaning(content)
        
        return content.strip()

    def _generic_content_cleaning(self, content: str) -> str:
        """通用内容清理"""
        if not content:
            return ""
        
        # 移除多余的空白字符
        content = re.sub(r'\n\s*\n', '\n\n', content)  # 多个空行变为两个
        content = re.sub(r'[ \t]+', ' ', content)      # 多个空格变为一个
        
        # 移除常见的无用文本
        useless_patterns = [
            r'手机用户请浏览.*?更优质的阅读体验。?',
            r'天才一秒记住.*?手机版阅读网址：.*?',
            r'一秒记住.*?，精彩无弹窗免费阅读！',
            r'喜欢.*?请大家收藏：.*?更新速度全网最快。?',
            r'本小章还未完，请点击下一页继续阅读.*?',
            r'小主，这个章节后面还有哦.*?',
            r'这章没有结束，请点击下一页继续阅读.*?',
            r'请勿开启浏览器阅读模式.*?',
            r'\(本章完\)',
            r'章节错误,点此举报.*?',
            r'推荐阅读：.*?',
            # 新增：站点导航/目录列表/SEO提示等
            r'^\s*零点小说.*$',
            r'^\s*首页\s*书库\s*排行.*$',
            r'^\s*最新章节目录.*$',
            r'^\s*作者：.*?更新时间：.*$',
            r'^第[一二三四五六七八九十百千0-9]+章.*目录.*$',
            r'^如遇到内容无法显示或者显示不全.*$',
            r'^.*请更换谷歌浏览器.*$',
            r'^上一章$|^下一章$|^返回目录$|^加入书签$'
        ]
        
        # 行级清理：逐行删除匹配的垃圾行
        lines = content.split('\n')
        cleaned_lines = []
        chapter_header_regex = re.compile(r'^第[一二三四五六七八九十百千0-9]+章')
        chapter_header_count = 0
        for line in lines:
            drop = False
            for pattern in useless_patterns:
                try:
                    if re.search(pattern, line, flags=re.IGNORECASE):
                        drop = True
                        break
                except Exception:
                    continue
            if drop:
                continue
            if chapter_header_regex.search(line):
                chapter_header_count += 1
            cleaned_lines.append(line)
        content = '\n'.join([l for l in cleaned_lines if l.strip()])
        
        # 若检测到大量“第X章”标题，认为混入目录，进一步剔除这些行
        if chapter_header_count >= 5:
            content = '\n'.join([l for l in content.split('\n') if not chapter_header_regex.search(l)])
        
        # 合并连续空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content

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

    async def _fetch_html_single(self, url: str) -> Optional[str]:
        """获取HTML页面（单次请求）

        Args:
            url: 页面URL

        Returns:
            HTML页面内容，失败返回None
        """
        # 使用统一的HTTP客户端
        referer = self.source.rule.get("url", "")
        return await HttpClient.fetch_html(url, self.timeout, referer)

    def _parse_chapter_content(self, html: str, title: str = "未知章节") -> str:
        """解析章节内容（标准方法）

        Args:
            html: HTML页面内容
            title: 章节标题

        Returns:
            章节内容
        """
        # 获取章节内容规则
        content_selectors = self.chapter_rule.get("content", "").split(",")

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
                # 移除不需要的元素
                self._remove_unwanted_elements(content_element)
                
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
