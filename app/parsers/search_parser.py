import asyncio
import aiohttp
import re
import json
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from app.models.search import SearchResult
from app.core.source import Source
from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchParser:
    """搜索解析器，用于解析搜索结果页面"""
    
    def __init__(self, source: Source):
        """初始化搜索解析器
        
        Args:
            source: 书源对象
        """
        self.source = source
        self.timeout = source.rule.get("search", {}).get("timeout", settings.DEFAULT_TIMEOUT)
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", "")
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
            html = await self._fetch_html_with_retry(search_url, method=method, data=request_data)
            if not html:
                logger.warning(f"从书源 {self.source.rule.get('name', self.source.id)} 获取搜索结果失败")
                return []
            
            # 解析搜索结果
            results = self._parse_search_results(html, keyword)
            
            # 限制结果数量
            if len(results) > settings.MAX_SEARCH_RESULTS:
                results = results[:settings.MAX_SEARCH_RESULTS]
            
            logger.info(f"从书源 {self.source.rule.get('name', self.source.id)} 获取到 {len(results)} 条搜索结果")
            return results
        except Exception as e:
            logger.error(f"书源 {self.source.rule.get('name', self.source.id)} 搜索异常: {str(e)}")
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
            
            # 处理 key=value 格式
            if "=" in data_str:
                try:
                    parts = data_str.split("=", 1)
                    key = parts[0].strip()
                    value = parts[1].strip()
                    return {key: value}
                except Exception:
                    pass
            
            # 默认返回字符串
            return data_str
    
    def _build_search_url(self, keyword: str, page: int = 1) -> str:
        """构建搜索URL
        
        Args:
            keyword: 搜索关键词
            page: 页码，默认为1
            
        Returns:
            搜索URL
        """
        import urllib.parse
        
        search_url = self.search_rule.get("url", "")
        
        # URL编码关键词，处理中文字符
        encoded_keyword = urllib.parse.quote(keyword, safe='')
        
        # 替换关键词和页码
        search_url = search_url.replace("{keyword}", encoded_keyword)
        search_url = search_url.replace("%s", encoded_keyword)
        search_url = search_url.replace("{page}", str(page))
        
        # 如果URL不是以http开头，则添加baseUri
        if not search_url.startswith("http"):
            search_url = f"{self.source.rule.get('url', '').rstrip('/')}/{search_url.lstrip('/')}"
        
        return search_url
    
    async def _fetch_html_with_retry(self, url: str, method: str = "get", data: Any = None) -> Optional[str]:
        """带重试机制的获取HTML页面
        
        Args:
            url: 页面URL
            method: 请求方法 (get或post)
            data: POST请求体数据
            
        Returns:
            HTML页面内容，失败返回None
        """
        last_error = None
        
        for attempt in range(settings.REQUEST_RETRY_TIMES):
            try:
                result = await self._fetch_html(url, method, data)
                if result:
                    return result
                
                # 如果是第一次尝试失败，记录警告
                if attempt == 0:
                    logger.warning(f"第一次请求失败，准备重试: {url}")
                    
            except Exception as e:
                last_error = e
                if attempt < settings.REQUEST_RETRY_TIMES - 1:
                    logger.warning(f"请求失败（第 {attempt + 1} 次），{settings.REQUEST_RETRY_DELAY} 秒后重试: {str(e)}")
                    await asyncio.sleep(settings.REQUEST_RETRY_DELAY)
                else:
                    logger.error(f"请求最终失败（共 {settings.REQUEST_RETRY_TIMES} 次尝试）: {str(e)}")
        
        return None
    
    async def _fetch_html(self, url: str, method: str = "get", data: Any = None) -> Optional[str]:
        """获取HTML页面
        
        Args:
            url: 页面URL
            method: 请求方法 (get或post)
            data: POST请求体数据
            
        Returns:
            HTML页面内容，失败返回None
        """
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=aiohttp.TCPConnector(limit=settings.MAX_CONCURRENT_REQUESTS)
            ) as session:
                if method == "post" and data is not None:
                    headers = self.headers.copy()
                    if isinstance(data, dict):
                        # 表单数据
                        async with session.post(url, data=data, headers=headers) as response:
                            if response.status == 200:
                                # 尝试检测编码
                                content = await response.read()
                                return self._decode_content(content, response.charset)
                            else:
                                logger.error(f"请求失败: {url}, 状态码: {response.status}")
                                return None
                    elif isinstance(data, str):
                        # 字符串数据
                        headers["Content-Type"] = "application/x-www-form-urlencoded"
                        async with session.post(url, data=data.encode('utf-8'), headers=headers) as response:
                            if response.status == 200:
                                content = await response.read()
                                return self._decode_content(content, response.charset)
                            else:
                                logger.error(f"请求失败: {url}, 状态码: {response.status}")
                                return None
                    else:
                        # JSON数据
                        headers["Content-Type"] = "application/json"
                        async with session.post(url, json=data, headers=headers) as response:
                            if response.status == 200:
                                content = await response.read()
                                return self._decode_content(content, response.charset)
                            else:
                                logger.error(f"请求失败: {url}, 状态码: {response.status}")
                                return None
                else:
                    # GET请求
                    async with session.get(url, headers=self.headers) as response:
                        if response.status == 200:
                            content = await response.read()
                            return self._decode_content(content, response.charset)
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
            logger.error(f"请求异常: {url}, 错误: {str(e)}")
            return None
    
    def _decode_content(self, content: bytes, charset: Optional[str]) -> str:
        """解码网页内容，处理字符编码问题
        
        Args:
            content: 原始字节内容
            charset: 响应头中的字符编码
            
        Returns:
            解码后的字符串
        """
        # 尝试的编码列表
        encodings_to_try = []
        
        # 首先尝试响应头中指定的编码
        if charset:
            encodings_to_try.append(charset)
        
        # 然后尝试常见的编码
        encodings_to_try.extend(['utf-8', 'gb2312', 'gbk', 'gb18030', 'big5'])
        
        for encoding in encodings_to_try:
            try:
                decoded_text = content.decode(encoding)
                # 检查解码结果是否包含过多替换字符
                if decoded_text.count('') < len(decoded_text) * 0.05:  # 替换字符少于5%
                    return decoded_text
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 如果所有编码都失败，使用utf-8并忽略错误
        return content.decode('utf-8', errors='ignore')
    
    def _parse_search_results(self, html: str, keyword: str) -> List[SearchResult]:
        """解析搜索结果
        
        Args:
            html: HTML页面内容
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        results = []
        
        try:
            # 获取搜索结果规则
            list_selector = self.search_rule.get("list", "")
            name_selector = self.search_rule.get("name", "")
            author_selector = self.search_rule.get("author", "")
            category_selector = self.search_rule.get("category", "")
            latest_selector = self.search_rule.get("latest", "")
            update_selector = self.search_rule.get("update", "")
            status_selector = self.search_rule.get("status", "")
            word_count_selector = self.search_rule.get("word_count", "")
            
            if not list_selector:
                logger.warning("搜索规则中缺少list选择器")
                return results
            
            # 解析HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # 获取搜索结果列表
            items = soup.select(list_selector)
            
            for item in items:
                try:
                    # 获取书名和URL
                    book_name = ""
                    book_url = ""
                    if name_selector:
                        name_element = item.select_one(name_selector)
                        if name_element:
                            book_name = name_element.get_text().strip()
                            book_url = name_element.get("href", "")
                            if book_url and not book_url.startswith("http"):
                                book_url = f"{self.source.rule.get('url', '').rstrip('/')}/{book_url.lstrip('/')}"
                    
                    if not book_name:
                        continue
                
2                    # 获取作者
                    author = ""
                    if author_selector:
                        author_element = item.select_one(author_selector)
                        if author_element:
                            author = author_element.get_text().strip()
                    
                    # 获取分类
                    category = ""
                    if category_selector:
                        category_element = item.select_one(category_selector)
                        if category_element:
                            category = category_element.get_text().strip()
                    
                    # 获取最新章节
                    latest_chapter = ""
                    if latest_selector:
                        latest_element = item.select_one(latest_selector)
                        if latest_element:
                            latest_chapter = latest_element.get_text().strip()
                    
                    # 获取更新时间
                    update_time = ""
                    if update_selector:
                        update_element = item.select_one(update_selector)
                        if update_element:
                            update_time = update_element.get_text().strip()
                    
                    # 获取状态
                    status = ""
                    if status_selector:
                        status_element = item.select_one(status_selector)
                        if status_element:
                            status = status_element.get_text().strip()
                    
                    # 获取字数
                    word_count = ""
                    if word_count_selector:
                        word_count_element = item.select_one(word_count_selector)
                        if word_count_element:
                            word_count = word_count_element.get_text().strip()
                    
                    # 创建搜索结果对象
                    result = SearchResult(
                        sourceId=self.source.id,
                        sourceName=self.source.rule.get("name", f"书源{self.source.id}"),
                        url=book_url,
                        bookName=book_name,
                        author=author or None,
                        category=category or None,
                        latestChapter=latest_chapter or None,
                        lastUpdateTime=update_time or None,
                        status=status or None,
                        wordCount=word_count or None
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"解析搜索结果项异常: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"解析搜索结果异常: {str(e)}")
        
        return results