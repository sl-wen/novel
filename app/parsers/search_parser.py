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

            # 限制结果数量
            if len(results) > settings.MAX_SEARCH_RESULTS:
                results = results[: settings.MAX_SEARCH_RESULTS]

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
            # 处理 {key: value} 格式
            if data_str.startswith("{") and data_str.endswith("}"):
                try:
                    # 移除花括号并分割
                    content = data_str.strip("{}")
                    if ":" in content:
                        parts = content.split(":", 1)
                        key = parts[0].strip()
                        value = parts[1].strip()
                        return {key: value}
                except Exception:
                    pass

            # 处理表单数据格式
            if "=" in data_str:
                try:
                    data_dict = {}
                    pairs = data_str.split("&")
                    for pair in pairs:
                        if "=" in pair:
                            key, value = pair.split("=", 1)
                            data_dict[key.strip()] = value.strip()
                    return data_dict
                except Exception:
                    pass

            # 返回原始字符串
            return data_str

    def _build_search_url(self, keyword: str, page: int = 1) -> str:
        """构建搜索URL

        Args:
            keyword: 搜索关键词
            page: 页码，默认为1

        Returns:
            搜索URL
        """
        url_template = self.search_rule.get("url", "")
        if not url_template:
            return ""

        # 替换关键词占位符
        url = url_template.replace("%s", keyword)

        # 替换页码占位符
        if "%p" in url:
            url = url.replace("%p", str(page))

        # 构建完整URL
        base_url = self.source.rule.get("url", "")
        if not url.startswith(("http://", "https://")):
            url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"

        return url

    async def _fetch_html_with_retry(
        self, url: str, method: str = "get", data: Any = None
    ) -> Optional[str]:
        """带重试机制的获取HTML页面

        Args:
            url: 页面URL
            method: 请求方法
            data: 请求数据

        Returns:
            HTML页面内容，失败返回None
        """
        for attempt in range(settings.REQUEST_RETRY_TIMES):
            try:
                result = await self._fetch_html(url, method, data)
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
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=aiohttp.TCPConnector(limit=settings.MAX_CONCURRENT_REQUESTS),
            ) as session:
                if method == "post":
                    async with session.post(
                        url, headers=self.headers, data=data
                    ) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.error(
                                f"POST请求失败: {url}, 状态码: {response.status}"
                            )
                            return None
                else:
                    async with session.get(url, headers=self.headers) as response:
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

        for element in result_elements:
            try:
                result = self._parse_single_result(element, keyword)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"解析单个搜索结果失败: {str(e)}")
                continue

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

            # 获取封面
            cover_selector = self.search_rule.get("cover", "")
            cover = self._extract_attr(element, cover_selector, "src")

            # 获取详情页URL
            url_selector = self.search_rule.get("url", "")
            url = self._extract_attr(element, url_selector, "href")

            # 获取分类
            category_selector = self.search_rule.get("category", "")
            category = self._extract_text(element, category_selector)

            # 获取状态
            status_selector = self.search_rule.get("status", "")
            status = self._extract_text(element, status_selector)

            # 获取字数
            word_count_selector = self.search_rule.get("word_count", "")
            word_count = self._extract_text(element, word_count_selector)

            # 获取最后更新时间
            update_time_selector = self.search_rule.get("update_time", "")
            update_time = self._extract_text(element, update_time_selector)

            # 获取最新章节
            latest_chapter_selector = self.search_rule.get("latest_chapter", "")
            latest_chapter = self._extract_text(element, latest_chapter_selector)

            # 构建完整URL
            if url and not url.startswith(("http://", "https://")):
                base_url = self.source.rule.get("url", "")
                url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"

            if cover and not cover.startswith(("http://", "https://")):
                base_url = self.source.rule.get("url", "")
                cover = f"{base_url.rstrip('/')}/{cover.lstrip('/')}"

            try:
                return SearchResult(
                    title=title or "未知标题",
                    author=author or "未知作者",
                    intro=intro or "",
                    cover=cover or "",
                    url=url or "",
                    category=category or "",
                    status=status or "未知",
                    word_count=word_count or "",
                    update_time=update_time or "",
                    latest_chapter=latest_chapter or "",
                    source_id=self.source.id,
                    source_name=self.source.rule.get("name", self.source.id),
                )
            except AttributeError as e:
                # 如果出现bookName相关错误，记录并返回None
                logger.warning(f"SearchResult创建失败（bookName相关）: {str(e)}")
                return None
            except Exception as e:
                logger.warning(f"解析搜索结果失败: {str(e)}")
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

    def _decode_content(self, content: bytes, charset: Optional[str]) -> str:
        """解码内容

        Args:
            content: 字节内容
            charset: 字符编码

        Returns:
            解码后的字符串
        """
        if not content:
            return ""

        try:
            if charset:
                return content.decode(charset)
            else:
                # 尝试自动检测编码
                import chardet

                detected = chardet.detect(content)
                return content.decode(detected["encoding"] or "utf-8")
        except Exception as e:
            logger.warning(f"解码内容失败: {str(e)}")
            # 尝试使用utf-8解码
            try:
                return content.decode("utf-8")
            except Exception:
                return content.decode("utf-8", errors="ignore")
