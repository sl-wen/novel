"""
HTTP客户端工具类，提供统一的HTTP请求处理
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from app.core.config import settings
from app.utils.enhanced_http_client import http_client

logger = logging.getLogger(__name__)


class HttpClient:
    """HTTP客户端工具类，处理各种HTTP请求问题"""

    @staticmethod
    async def fetch_html(
        url: str, timeout: int = None, referer: str = None
    ) -> Optional[str]:
        """获取HTML页面内容（委托到增强HTTP客户端，复用连接、自动UA轮换、重试与退避）"""
        if timeout is None:
            timeout = settings.DEFAULT_TIMEOUT
        return await http_client.fetch_html(url, referer=referer, timeout=timeout)

    @staticmethod
    async def post_data(
        url: str, data: Dict[str, Any], timeout: int = None, referer: str = None
    ) -> Optional[str]:
        """发送POST请求（委托到增强HTTP客户端）"""
        if timeout is None:
            timeout = settings.DEFAULT_TIMEOUT
        headers = {"Referer": referer} if referer else {}
        return await http_client.post_data(url, data=data, headers=headers)
