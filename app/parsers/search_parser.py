import asyncio
import json
import logging
from typing import Any, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.search import SearchResult

logger = logging.getLogger(__name__)


class SearchParser:
    """搜索解析器，用于解析搜索结果页面"""

    def __init__(self, source: Source):
        """初始化搜索解析器

        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("search", {}).get(
            "timeout", settings.DEFAULT_TIMEOUT
        )
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", ""),
        }
        self.search_rule = source.rule.get("search", {})

    async def parse(self, keyword: str) -> List[SearchResult]:
        """解析搜索结果

        Args:
            keyword: 搜索关键词（书名或作者名）

        Returns:
            搜索结果列表
        """
        try:
            # 构建搜索URL
            search_url = self._build_search_url(keyword)

            # 获取请求方法和数据
            method = self.search_rule.get("method", "get").lower()
            data_template = self.search_rule.get("data", "")

            # 处理POST数据
            request_data = None
            if method == "post" and data_template:
                request_data = self._process_post_data(data_template, keyword)

            # 发送请求获取搜索结果页面
            html = await self._fetch_html_with_retry(
                search_url, method=method, data=request_data
            )
            if not html:
                logger.warning(
                    f"从书源 {self.source.rule.get('name', self.source.id)} "
                    f"获取搜索结果失败"
                )
                return []

            # 解析搜索结果
            results = self._parse_search_results(html, keyword)

            # 限制每个书源的结果数量
            if len(results) > settings.MAX_RESULTS_PER_SOURCE:
                results = results[: settings.MAX_RESULTS_PER_SOURCE]

            logger.info(
                f"从书源 {self.source.rule.get('name', self.source.id)} "
                f"获取到 {len(results)} 条搜索结果"
            )
            return results
        except Exception as e:
            logger.error(
                f"书源 {self.source.rule.get('name', self.source.id)} "
                f"搜索异常: {str(e)}"
            )
            return []

    def _process_post_data(self, data_template: str, keyword: str) -> Any:
        """处理POST请求数据

        Args:
            data_template: 数据模板
            keyword: 搜索关键词

        Returns:
            处理后的请求数据
        """
        # 替换关键词占位符
        data_str = data_template.replace("%s", keyword)

        try:
            # 尝试解析为JSON
            return json.loads(data_str)
        except json.JSONDecodeError:
            # 如果不是JSON，尝试解析为表单数据
            try:
                # 处理类似 "{searchkey: %s}" 的格式
                if data_str.startswith("{") and data_str.endswith("}"):
                    # 移除大括号，分割键值对
                    content = data_str[1:-1]
                    pairs = content.split(",")
                    data_dict = {}
                    for pair in pairs:
                        if ":" in pair:
                            key, value = pair.split(":", 1)
                            key = key.strip().strip('"').strip("'")
                            value = value.strip().strip('"').strip("'")
                            data_dict[key] = value
                    return data_dict
                else:
                    # 作为字符串返回
                    return data_str
            except Exception:
                # 如果都失败了，返回原始字符串
                return data_str

    def _build_search_url(self, keyword: str, page: int = 1) -> str:
        """构建搜索URL

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            搜索URL
        """
        url_template = self.search_rule.get("url", "")
        if not url_template:
            logger.error("未配置搜索URL模板")
            return ""

        # 替换关键词占位符
        url = url_template.replace("%s", keyword)
        
        # 处理分页
        if "%d" in url:
            url = url.replace("%d", str(page))

        return url

    async def _fetch_html_with_retry(
        self, url: str, method: str = "get", data: Any = None
    ) -> Optional[str]:
        """带重试的HTML获取

        Args:
            url: 页面URL
            method: 请求方法
            data: 请求数据

        Returns:
            HTML页面内容，失败返回None
        """
        for attempt in range(settings.REQUEST_RETRY_TIMES + 1):
            try:
                html = await self._fetch_html(url, method=method, data=data)
                if html:
                    return html
            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次请求失败: {url}, 错误: {str(e)}")
                if attempt < settings.REQUEST_RETRY_TIMES:
                    await asyncio.sleep(settings.REQUEST_RETRY_DELAY)
                else:
                    logger.error(f"所有重试都失败了: {url}")
                    return None
        return None

    async def _fetch_html(
        self, url: str, method: str = "get", data: Any = None
    ) -> Optional[str]:
        """获取HTML页面

        Args:
            url: 页面URL
            method: 请求方法
            data: 请求数据

        Returns:
            HTML页面内容，失败返回None
        """
        try:
            # 创建SSL上下文，跳过证书验证
            connector = aiohttp.TCPConnector(
                limit=settings.MAX_CONCURRENT_REQUESTS,
                ssl=False,  # 跳过SSL证书验证
                use_dns_cache=True,
                ttl_dns_cache=300,
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=10,
                sock_read=30
            )
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self.headers
            ) as session:
                if method == "post":
                    async with session.post(url, data=data) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.error(
                                f"POST请求失败: {url}, 状态码: {response.status}"
                            )
                            return None
                else:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.error(
                                f"GET请求失败: {url}, 状态码: {response.status}"
                            )
                            return None
        except Exception as e:
            logger.error(f"请求异常: {url}, 错误: {str(e)}")
            return None

    def _parse_search_results(self, html: str, keyword: str) -> List[SearchResult]:
        """解析搜索结果

        Args:
            html: HTML页面内容
            keyword: 搜索关键词

        Returns:
            搜索结果列表
        """
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # 获取结果列表选择器
        list_selector = self.search_rule.get("list", "")
        if not list_selector:
            logger.warning("未配置搜索结果列表选择器")
            return results

        # 获取结果列表
        result_elements = soup.select(list_selector)
        logger.info(f"找到 {len(result_elements)} 个搜索结果元素")

        # 解析所有结果
        all_results = []
        for element in result_elements:
            try:
                result = self._parse_single_result(element, keyword)
                if result:
                    all_results.append(result)
            except Exception as e:
                logger.warning(f"解析单个搜索结果失败: {str(e)}")
                continue

        # 如果结果数量超过限制，按相关性排序并选择最佳结果
        if len(all_results) > settings.MAX_RESULTS_PER_SOURCE:
            # 计算相关性得分
            for result in all_results:
                result.score = self._calculate_relevance_score(result, keyword)
            
            # 按得分降序排序
            all_results.sort(key=lambda x: getattr(x, 'score', 0), reverse=True)
            
            # 只取前N个最相关的结果
            results = all_results[:settings.MAX_RESULTS_PER_SOURCE]
            logger.info(f"从 {len(all_results)} 个结果中选择了最相关的 {len(results)} 个")
        else:
            results = all_results

        return results

    def _parse_single_result(
        self, element: BeautifulSoup, keyword: str
    ) -> Optional[SearchResult]:
        """解析单个搜索结果

        Args:
            element: 结果元素
            keyword: 搜索关键词

        Returns:
            搜索结果对象，失败返回None
        """
        try:
            # 获取书名
            title_selector = self.search_rule.get("name", "")
            title = self._extract_text(element, title_selector)

            # 获取作者
            author_selector = self.search_rule.get("author", "")
            author = self._extract_text(element, author_selector)

            # 获取简介
            intro_selector = self.search_rule.get("intro", "")
            intro = self._extract_text(element, intro_selector)

            # 获取分类
            category_selector = self.search_rule.get("category", "")
            category = self._extract_text(element, category_selector)

            # 获取状态
            status_selector = self.search_rule.get("status", "")
            status = self._extract_text(element, status_selector)

            # 获取字数
            word_count_selector = self.search_rule.get("word_count", "")
            word_count = self._extract_text(element, word_count_selector)

            # 获取最新章节
            latest_selector = self.search_rule.get("latest", "")
            latest_chapter = self._extract_text(element, latest_selector)

            # 获取更新时间
            update_selector = self.search_rule.get("update", "")
            update_time = self._extract_text(element, update_selector)

            # 获取封面
            cover_selector = self.search_rule.get("cover", "")
            cover = self._extract_attr(element, cover_selector, "src")

            # 获取详情页URL
            url_selector = self.search_rule.get("name", "")
            url = self._extract_attr(element, url_selector, "href")

            # 如果URL是相对路径，转换为绝对路径
            if url and not url.startswith(("http://", "https://")):
                base_url = self.source.rule.get("url", "")
                if base_url:
                    if url.startswith("/"):
                        url = base_url.rstrip("/") + url
                    else:
                        url = base_url.rstrip("/") + "/" + url

            # 验证必要字段
            if not title or not url:
                return None

            return SearchResult(
                title=title,
                author=author,
                intro=intro,
                cover=cover,
                url=url,
                category=category,
                status=status,
                word_count=word_count,
                update_time=update_time,
                latest_chapter=latest_chapter,
                source_id=self.source.id,
                source_name=self.source.rule.get("name", ""),
            )
        except Exception as e:
            logger.warning(f"解析搜索结果失败: {str(e)}")
            return None

    def _extract_text(self, element: BeautifulSoup, selector: str) -> str:
        """提取文本内容

        Args:
            element: 元素
            selector: CSS选择器

        Returns:
            提取的文本
        """
        if not selector:
            return ""

        try:
            target = element.select_one(selector)
            if target:
                return target.get_text(strip=True)
        except Exception as e:
            logger.debug(f"提取文本失败: {selector}, 错误: {str(e)}")

        return ""

    def _extract_attr(self, element: BeautifulSoup, selector: str, attr: str) -> str:
        """提取属性值

        Args:
            element: 元素
            selector: CSS选择器
            attr: 属性名

        Returns:
            提取的属性值
        """
        if not selector:
            return ""

        try:
            target = element.select_one(selector)
            if target:
                return target.get(attr, "")
        except Exception as e:
            logger.debug(f"提取属性失败: {selector}.{attr}, 错误: {str(e)}")

        return ""

    def _calculate_relevance_score(self, result: SearchResult, keyword: str) -> float:
        """计算搜索结果的相关性得分

        Args:
            result: 搜索结果
            keyword: 搜索关键词

        Returns:
            相关性得分（0-1之间）
        """
        score = 0.0
        keyword_lower = keyword.lower()
        
        # 书名匹配度（权重最高）
        if result.title:
            title_lower = result.title.lower()
            if keyword_lower == title_lower:
                score += 1.0  # 完全匹配
            elif keyword_lower in title_lower:
                score += 0.8  # 包含关键词
            elif any(word in title_lower for word in keyword_lower.split()):
                score += 0.6  # 包含关键词的部分
        
        # 作者匹配度（权重中等）
        if result.author:
            author_lower = result.author.lower()
            if keyword_lower == author_lower:
                score += 0.5  # 作者完全匹配
            elif keyword_lower in author_lower:
                score += 0.3  # 作者包含关键词
        
        # 简介匹配度（权重较低）
        if result.intro:
            intro_lower = result.intro.lower()
            if keyword_lower in intro_lower:
                score += 0.1  # 简介包含关键词
        
        return min(score, 1.0)  # 确保得分不超过1.0

    def _decode_content(self, content: bytes, charset: Optional[str]) -> str:
        """解码内容

        Args:
            content: 字节内容
            charset: 字符集

        Returns:
            解码后的字符串
        """
        if not charset:
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return content.decode("gbk")
                except UnicodeDecodeError:
                    return content.decode("utf-8", errors="ignore")
        else:
            try:
                return content.decode(charset)
            except UnicodeDecodeError:
                return content.decode("utf-8", errors="ignore")
