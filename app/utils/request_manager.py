import asyncio
import logging
import random
import time
from typing import Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestManager:
    """请求管理器，提供更好的网络请求控制和错误处理"""

    def __init__(self):
        """初始化请求管理器"""
        self.session: Optional[ClientSession] = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        ]

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._close_session()

    async def _create_session(self):
        """创建HTTP会话"""
        connector = TCPConnector(
            limit=settings.MAX_CONCURRENT_REQUESTS,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout = ClientTimeout(total=settings.DEFAULT_TIMEOUT, connect=10)
        
        self.session = ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self._get_default_headers()
        )

    async def _close_session(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None

    def _get_default_headers(self) -> dict:
        """获取默认请求头"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _get_headers_with_referer(self, referer: str) -> dict:
        """获取带Referer的请求头"""
        headers = self._get_default_headers()
        headers["Referer"] = referer
        return headers

    async def get(self, url: str, referer: str = None, retries: int = None) -> Optional[str]:
        """发送GET请求

        Args:
            url: 请求URL
            referer: Referer头
            retries: 重试次数，默认使用配置值

        Returns:
            响应内容，失败返回None
        """
        if retries is None:
            retries = settings.REQUEST_RETRY_TIMES

        headers = self._get_headers_with_referer(referer) if referer else self._get_default_headers()

        for attempt in range(retries):
            try:
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        if content and len(content) > 100:
                            return content
                        else:
                            logger.warning(f"页面内容过短: {url}")
                            return None
                    else:
                        logger.warning(f"HTTP {response.status}: {url}")

            except Exception as e:
                if attempt < retries - 1:
                    delay = settings.REQUEST_RETRY_DELAY * (2 ** attempt)  # 指数退避
                    logger.warning(f"请求失败 (第{attempt + 1}次): {str(e)}, {delay}秒后重试")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"请求最终失败: {str(e)}")

        return None

    async def post(self, url: str, data: dict = None, referer: str = None, retries: int = None) -> Optional[str]:
        """发送POST请求

        Args:
            url: 请求URL
            data: POST数据
            referer: Referer头
            retries: 重试次数，默认使用配置值

        Returns:
            响应内容，失败返回None
        """
        if retries is None:
            retries = settings.REQUEST_RETRY_TIMES

        headers = self._get_headers_with_referer(referer) if referer else self._get_default_headers()

        for attempt in range(retries):
            try:
                async with self.session.post(url, data=data, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        if content and len(content) > 100:
                            return content
                        else:
                            logger.warning(f"页面内容过短: {url}")
                            return None
                    else:
                        logger.warning(f"HTTP {response.status}: {url}")

            except Exception as e:
                if attempt < retries - 1:
                    delay = settings.REQUEST_RETRY_DELAY * (2 ** attempt)  # 指数退避
                    logger.warning(f"请求失败 (第{attempt + 1}次): {str(e)}, {delay}秒后重试")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"请求最终失败: {str(e)}")

        return None

    async def batch_get(self, urls: list, referer: str = None, max_concurrent: int = None) -> list:
        """批量GET请求

        Args:
            urls: URL列表
            referer: Referer头
            max_concurrent: 最大并发数，默认使用配置值

        Returns:
            响应内容列表
        """
        if max_concurrent is None:
            max_concurrent = settings.DOWNLOAD_CONCURRENT_LIMIT

        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(url):
            async with semaphore:
                return await self.get(url, referer)

        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量请求失败: {urls[i]}, 错误: {str(result)}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results


class RateLimiter:
    """速率限制器，控制请求频率"""

    def __init__(self, max_requests: int = 10, time_window: float = 60.0):
        """初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def acquire(self):
        """获取请求许可"""
        now = time.time()
        
        # 清理过期的请求记录
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        # 检查是否超过限制
        if len(self.requests) >= self.max_requests:
            # 等待最早的请求过期
            wait_time = self.time_window - (now - self.requests[0])
            if wait_time > 0:
                logger.info(f"速率限制，等待 {wait_time:.2f} 秒")
                await asyncio.sleep(wait_time)
        
        # 记录当前请求
        self.requests.append(time.time())