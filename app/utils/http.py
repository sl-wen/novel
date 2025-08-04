import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP客户端工具类，提供重试、超时等功能"""

    def __init__(self):
        self.session = self._create_session()
        self.async_session = None

    def _create_session(self) -> requests.Session:
        """创建带有重试机制的requests session"""
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=settings.REQUEST_RETRY_TIMES,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=settings.REQUEST_RETRY_DELAY,
        )

        # 配置适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 设置默认headers
        session.headers.update(settings.DEFAULT_HEADERS)

        return session

    async def _get_async_session(self) -> aiohttp.ClientSession:
        """获取异步session"""
        if self.async_session is None or self.async_session.closed:
            timeout = aiohttp.ClientTimeout(
                total=settings.DEFAULT_TIMEOUT,
                connect=settings.CONNECT_TIMEOUT,
                sock_read=settings.READ_TIMEOUT,
            )
            self.async_session = aiohttp.ClientSession(
                timeout=timeout, headers=settings.DEFAULT_HEADERS
            )
        return self.async_session

    def get(self, url: str, **kwargs) -> requests.Response:
        """同步GET请求"""
        try:
            timeout = kwargs.pop(
                "timeout", (settings.CONNECT_TIMEOUT, settings.READ_TIMEOUT)
            )
            response = self.session.get(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时: {url}, 错误: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {url}, 错误: {str(e)}")
            raise

    async def async_get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """异步GET请求"""
        session = await self._get_async_session()
        try:
            timeout = kwargs.pop(
                "timeout",
                aiohttp.ClientTimeout(
                    total=settings.DEFAULT_TIMEOUT,
                    connect=settings.CONNECT_TIMEOUT,
                    sock_read=settings.READ_TIMEOUT,
                ),
            )
            async with session.get(url, timeout=timeout, **kwargs) as response:
                response.raise_for_status()
                return response
        except asyncio.TimeoutError as e:
            logger.error(f"异步请求超时: {url}, 错误: {str(e)}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"异步请求失败: {url}, 错误: {str(e)}")
            raise

    async def async_get_text(self, url: str, **kwargs) -> str:
        """异步GET请求并返回文本内容"""
        response = await self.async_get(url, **kwargs)
        return await response.text()

    async def async_get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """异步GET请求并返回JSON内容"""
        response = await self.async_get(url, **kwargs)
        return await response.json()

    def close(self):
        """关闭session"""
        if self.session:
            self.session.close()

    async def aclose(self):
        """关闭异步session"""
        if self.async_session and not self.async_session.closed:
            await self.async_session.close()


# 全局HTTP客户端实例
http_client = HTTPClient()
