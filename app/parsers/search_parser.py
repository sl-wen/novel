import asyncio
import aiohttp
import re
import json # 导入json模块
import logging # 导入logging模块
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from app.models.search import SearchResult
from app.core.source import Source
from app.core.config import settings

logger = logging.getLogger(__name__) # 获取logger实例


class SearchParser:
    """搜索解析器，用于解析搜索结果页面"""
    
    def __init__(self, source: Source):
        """初始化搜索解析器
        
        Args:
            source: 书源对象
        """
        self.source = source
        # 从书源规则中获取超时时间，如果不存在则使用默认配置
        self.timeout = source.rule.get("search", {}).get("timeout", settings.DEFAULT_TIMEOUT)
        self.headers = {
            "User-Agent": settings.DEFAULT_HEADERS["User-Agent"],
            "Referer": source.rule.get("url", "") # 使用书源的url作为Referer
        }
        self.search_rule = source.rule.get("search", {}) # 获取搜索规则
    
    async def parse(self, keyword: str) -> List[SearchResult]:
        """解析搜索结果
        
        Args:
            keyword: 搜索关键词（书名或作者名）
            
        Returns:
            搜索结果列表
        """
        # 构建搜索URL
        search_url = self._build_search_url(keyword)
        
        # 获取请求方法和数据
        method = self.search_rule.get("method", "get").lower()
        data_template = self.search_rule.get("data", "")
        # 检查data_template是否包含%s，如果包含则替换，否则直接使用
        data = data_template.replace("%s", keyword) if "%s" in data_template else data_template
        
        # 发送请求获取搜索结果页面
        html = await self._fetch_html(search_url, method=method, data=data)
        if not html:
            logger.warning(f"<== 从书源 {self.source.name} ({self.source.id}) 获取搜索结果失败") # 修改日志
            return []
        
        # 解析搜索结果
        results = self._parse_search_results(html, keyword)
        
        # 处理分页
        if self.search_rule.get("has_pages", False):
            # 获取总页数
            total_pages = self._get_total_pages(html)
            
            # 获取其他页的搜索结果
            if total_pages > 1:
                tasks = []
                for page in range(2, min(total_pages + 1, settings.MAX_SEARCH_PAGES + 1)):
                    page_url = self._build_search_url(keyword, page)
                    # 注意：分页请求通常也是GET，但为了通用性，这里可以根据需要调整
                    tasks.append(self._fetch_and_parse_page(page_url, keyword, method="get", data=None)) # 假设分页是GET请求
                
                # 并发获取其他页的搜索结果
                other_results = await asyncio.gather(*tasks)
                
                # 合并结果
                for page_results in other_results:
                    results.extend(page_results)
        
        logger.info(f"<== 从书源 {self.source.name} ({self.source.id}) 获取到 {len(results)} 条搜索结果") # 修改日志
        return results
    
    def _build_search_url(self, keyword: str, page: int = 1) -> str:
        """构建搜索URL
        
        Args:
            keyword: 搜索关键词
            page: 页码，默认为1
            
        Returns:
            搜索URL
        """
        search_url = self.search_rule.get("url", "")
        
        # 替换关键词和页码
        search_url = search_url.replace("{keyword}", keyword)
        search_url = search_url.replace("{page}", str(page))
        
        # 如果URL不是以http开头，则添加baseUri
        if not search_url.startswith("http"):
            # 使用书源的url作为baseUri
            search_url = f"{self.source.rule.get('url', '').rstrip('/')}/{search_url.lstrip('/')}"
        
        return search_url
    
    async def _fetch_html(self, url: str, method: str = "get", data: Optional[str] = None) -> Optional[str]:
        """获取HTML页面
        
        Args:
            url: 页面URL
            method: 请求方法 (get或post)
            data: POST请求体数据
            
        Returns:
            HTML页面内容，失败返回None
        """
        logger.info(f"正在请求: {method.upper()} {url}, 数据: {data}") # 添加日志
        try:
            async with aiohttp.ClientSession() as session:
                if method == "post":
                    # 对于POST请求，如果data是JSON字符串，需要设置content-type
                    headers = self.headers.copy()
                    request_data = data
                    content_type = "application/x-www-form-urlencoded"
                    try:
                        json_data = json.loads(data) # 尝试解析为JSON
                        headers["Content-Type"] = "application/json"
                        request_data = json_data # 发送JSON对象
                        content_type = "application/json"
                    except (json.JSONDecodeError, TypeError):
                        # 如果不是JSON，按普通表单数据处理
                        # 检查数据格式是否为 key=value&key2=value2
                        if isinstance(data, str) and "=" in data and "&" in data:
                             # 假设是 x-www-form-urlencoded 格式，直接使用字符串
                             request_data = data.encode('utf-8') if data else None
                             headers["Content-Type"] = "application/x-www-form-urlencoded"
                             content_type = "application/x-www-form-urlencoded"
                        elif isinstance(data, str):
                             # 尝试解析为简单的 key=value 格式
                             parts = data.split("=", 1)
                             if len(parts) == 2:
                                 request_data = {parts[0]: parts[1]}
                                 headers["Content-Type"] = "application/x-www-form-urlencoded"
                                 content_type = "application/x-www-form-urlencoded"
                             else:
                                 logger.warning(f"无法识别的POST数据格式: {data}")
                                 request_data = data.encode('utf-8') if data else None
                                 headers["Content-Type"] = "application/x-www-form-urlencoded"
                                 content_type = "application/x-www-form-urlencoded"
                        else:
                             logger.warning(f"无法识别的POST数据类型: {type(data)}")
                             request_data = data
                             headers["Content-Type"] = "application/x-www-form-urlencoded"
                             content_type = "application/x-www-form-urlencoded"

                    logger.info(f"POST请求头: {headers}, 请求体: {request_data}, Content-Type: {content_type}") # 添加日志
                    async with session.post(url, headers=headers, data=request_data, timeout=self.timeout) as response:
                        logger.info(f"POST请求响应状态码: {response.status}") # 添加日志
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.error(f"<== POST请求失败: {url}, 状态码: {response.status}") # 修改日志
                            return None
                else: # 默认为GET请求
                    async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                        logger.info(f"GET请求响应状态码: {response.status}") # 添加日志
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.warning(f"<== GET请求失败: {url}, 状态码: {response.status}") # 修改日志
                            return None
        except Exception as e:
            logger.warning(f"<== 请求异常: {url}, 错误: {str(e)}", exc_info=True) # 修改日志，包含堆栈信息
            return None
    
    def _parse_search_results(self, html: str, keyword: str) -> List[SearchResult]:
        """解析搜索结果
        
        Args:
            html: HTML页面内容
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        results = []
        
        # 获取搜索规则
        list_selector = self.search_rule.get("list", "")
        name_selector = self.search_rule.get("name", "")
        author_selector = self.search_rule.get("author", "")
        # url_selector = self.search_rule.get("url", "") # 移除错误的url_selector
        latest_selector = self.search_rule.get("latest", "")
        
        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # 获取搜索结果列表
        items = soup.select(list_selector)
        
        logger.info(f"使用选择器 '{list_selector}' 找到 {len(items)} 个搜索结果项") # 添加日志
        # logger.debug(f"原始HTML内容:\n{html[:1000]}...") # 调试时可以打印部分HTML
        
        for item in items:
            try:
                # 获取书名和URL
                name_element = item.select_one(name_selector)
                if not name_element:
                    logger.warning(f"未找到书名元素，跳过该项") # 添加日志
                    continue
                book_name = name_element.get_text().strip()
                url = name_element.get("href", "") # 从书名元素中提取URL
                
                # 如果URL不是以http开头，则添加baseUri
                if url and not url.startswith("http"):
                    # 使用书源的url作为baseUri
                    url = f"{self.source.rule.get('url', '').rstrip('/')}/{url.lstrip('/')}"
                
                # 获取作者
                author = ""
                if author_selector:
                    author_element = item.select_one(author_selector)
                    if author_element:
                        author = author_element.get_text().strip()
                
                # 获取最新章节
                latest_chapter = ""
                if latest_selector:
                    latest_element = item.select_one(latest_selector)
                    if latest_element:
                        latest_chapter = latest_element.get_text().strip()
                
                # 创建搜索结果对象
                result = SearchResult(
                    sourceId=self.source.id,
                    sourceName=self.source.rule.get('name', ''), # 从rule中获取书源名称
                    url=url, # 使用提取到的正确URL
                    bookName=book_name,
                    author=author,
                    latestChapter=latest_chapter
                )
                
                results.append(result)
            except Exception as e:
                logger.error(f"解析单个搜索结果项异常: {str(e)}", exc_info=True) # 修改日志，包含堆栈信息
                continue
        
        return results
    
    def _get_total_pages(self, html: str) -> int:
        """获取总页数
        
        Args:
            html: HTML页面内容
            
        Returns:
            总页数
        """
        # 获取分页规则
        page_selector = self.search_rule.get("page_selector", "")
        page_pattern = self.search_rule.get("page_pattern", "")
        
        if not page_selector or not page_pattern:
            return 1
        
        soup = BeautifulSoup(html, "html.parser")
        page_element = soup.select_one(page_selector)
        
        if page_element:
            text = page_element.get_text()
            match = re.search(page_pattern, text)
            if match:
                try:
                    return int(match.group(1)) # 假设第一个捕获组是总页数
                except (ValueError, IndexError):
                    pass
        
        return 1 # 默认总页数为1
    
    async def _fetch_and_parse_page(self, url: str, keyword: str, method: str = "get", data: Optional[str] = None) -> List[SearchResult]:
        """获取并解析单个分页的搜索结果
        
        Args:
            url: 页面URL
            keyword: 搜索关键词
            method: 请求方法
            data: 请求体数据
            
        Returns:
            搜索结果列表
        """
        html = await self._fetch_html(url, method=method, data=data)
        if not html:
            return []
        return self._parse_search_results(html, keyword)