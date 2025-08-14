"""
增强HTTP客户端工具类
提供更好的网络请求处理和错误恢复
"""

import asyncio
import logging
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from app.core.config import settings

logger = logging.getLogger(__name__)


class EnhancedHttpClient:
    """增强版HTTP客户端，提供连接池、会话复用和性能优化"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式，确保全局只有一个HTTP客户端实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化HTTP客户端"""
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self.sessions: Dict[str, ClientSession] = {}
        self.session_lock = asyncio.Lock()
        self.connection_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "session_reuses": 0,
        }
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown: bool = False

        # 性能优化配置
        self.max_sessions_per_host = 3
        self.session_timeout = 500  # 会话超时时间（秒）
        self.connection_timeout = getattr(settings, "CONNECTION_TIMEOUT", 15)
        self.read_timeout = getattr(settings, "READ_TIMEOUT", 120)
        self.socket_timeout = getattr(settings, "SOCKET_TIMEOUT", 30)
        self.max_retries = 3
        self.retry_delay = 1.0

        # 会话缓存
        self.session_cache = {}
        self.session_last_used = {}

        # 用户代理池
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        ]

        # 启动清理任务
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """启动定期清理任务"""
        try:
            loop = asyncio.get_running_loop()
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = loop.create_task(self._periodic_cleanup())
        except RuntimeError:
            # 没有运行中的事件循环，稍后启动
            pass

    async def _periodic_cleanup(self):
        """定期清理过期会话"""
        while not self._shutdown:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                # 任务被取消，优雅退出
                break
            except Exception as e:
                logger.error(f"会话清理任务出错: {str(e)}")

    async def _cleanup_expired_sessions(self):
        """清理过期的会话"""
        current_time = time.time()
        expired_keys = []

        async with self.session_lock:
            for key, last_used in self.session_last_used.items():
                if current_time - last_used > self.session_timeout:
                    expired_keys.append(key)

            for key in expired_keys:
                if key in self.session_cache:
                    session = self.session_cache[key]
                    await session.close()
                    del self.session_cache[key]
                    del self.session_last_used[key]
                    logger.debug(f"清理过期会话: {key}")

        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 个过期会话")

    def _get_session_key(self, url: str) -> str:
        """生成会话键"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    async def _get_or_create_session(self, url: str) -> ClientSession:
        """获取或创建会话"""
        session_key = self._get_session_key(url)

        async with self.session_lock:
            # 检查是否有可用的会话
            if session_key in self.session_cache:
                session = self.session_cache[session_key]
                if not session.closed:
                    self.session_last_used[session_key] = time.time()
                    self.connection_stats["session_reuses"] += 1
                    return session
                else:
                    # 会话已关闭，删除缓存
                    del self.session_cache[session_key]
                    if session_key in self.session_last_used:
                        del self.session_last_used[session_key]

            # 创建新会话（提高并发上限，参照下载并发配置）
            overall_limit = max(
                getattr(settings, "DOWNLOAD_CONCURRENT_LIMIT", 10) * 4, 20
            )
            per_host_limit = max(getattr(settings, "DOWNLOAD_CONCURRENT_LIMIT", 10), 10)

            connector = TCPConnector(
                limit=overall_limit,
                limit_per_host=per_host_limit,
                ttl_dns_cache=300,
                use_dns_cache=True,
                ssl=False,  # 跳过SSL验证以提高速度
                enable_cleanup_closed=True,
            )

            timeout = ClientTimeout(
                total=self.read_timeout,
                connect=self.connection_timeout,
                sock_read=self.socket_timeout,
                sock_connect=self.connection_timeout,
            )

            session = ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_optimized_headers(),
            )

            self.session_cache[session_key] = session
            self.session_last_used[session_key] = time.time()

            logger.debug(f"创建新会话: {session_key}")
            return session

    def _get_optimized_headers(self) -> Dict[str, str]:
        """获取优化的请求头"""
        import random

        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "DNT": "1",
        }

    async def fetch_html(
        self, url: str, referer: str = None, timeout: int = None, retries: int = None
    ) -> Optional[str]:
        """获取HTML页面内容（优化版）

        Args:
            url: 页面URL
            referer: Referer头
            timeout: 超时时间（秒）
            retries: 重试次数

        Returns:
            HTML页面内容，失败返回None
        """
        if timeout is None:
            timeout = self.read_timeout
        if retries is None:
            retries = self.max_retries

        self.connection_stats["total_requests"] += 1

        for attempt in range(retries):
            try:
                session = await self._get_or_create_session(url)

                # 设置请求头
                headers = {}
                if referer:
                    headers["Referer"] = referer

                async with session.get(url, headers=headers) as response:
                    logger.debug(f"HTTP响应: {response.status} - {url}")

                    if response.status == 200:
                        content = await response.text()
                        if content and len(content) > 100:
                            self.connection_stats["successful_requests"] += 1
                            return content
                        else:
                            logger.warning(
                                f"响应内容过短: {len(content) if content else 0} 字符"
                            )

                    elif response.status in [301, 302, 303, 307, 308]:
                        # 处理重定向
                        redirect_url = response.headers.get("Location")
                        if redirect_url:
                            logger.info(f"重定向: {url} -> {redirect_url}")
                            return await self.fetch_html(
                                redirect_url,
                                referer=url,
                                timeout=timeout,
                                retries=retries - 1,
                            )

                    else:
                        logger.warning(f"HTTP错误状态码: {response.status} - {url}")
                        if response.status >= 500 and attempt < retries - 1:
                            # 服务器错误，可以重试
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue

            except asyncio.TimeoutError:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{retries}): {url} (超时设置: 连接={self.connection_timeout}s, 读取={self.socket_timeout}s)")
                if attempt < retries - 1:
                    # 超时后使用指数退避策略
                    backoff_delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(min(backoff_delay, 10))  # 最大延迟10秒
                    continue

            except Exception as e:
                error_type = type(e).__name__
                logger.error(
                    f"请求失败 (尝试 {attempt + 1}/{retries}): {url} - {error_type}: {str(e)}"
                )
                if attempt < retries - 1:
                    # 其他异常使用线性退避
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue

        self.connection_stats["failed_requests"] += 1
        logger.error(f"所有重试失败: {url}")
        return None

    async def fetch_json(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """获取JSON数据"""
        try:
            session = await self._get_or_create_session(url)

            async with session.get(url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"JSON请求失败: {response.status} - {url}")
                    return None

        except Exception as e:
            logger.error(f"JSON请求异常: {url} - {str(e)}")
            return None

    async def post_data(
        self, url: str, data: Any = None, json: Any = None, **kwargs
    ) -> Optional[str]:
        """发送POST请求"""
        try:
            session = await self._get_or_create_session(url)

            async with session.post(url, data=data, json=json, **kwargs) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"POST请求失败: {response.status} - {url}")
                    return None

        except Exception as e:
            logger.error(f"POST请求异常: {url} - {str(e)}")
            return None

    async def batch_fetch(
        self, urls: List[str], max_concurrent: int = 10
    ) -> List[Optional[str]]:
        """批量获取HTML内容

        Args:
            urls: URL列表
            max_concurrent: 最大并发数

        Returns:
            HTML内容列表，失败的项目为None
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(url: str) -> Optional[str]:
            async with semaphore:
                return await self.fetch_html(url)

        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"批量请求异常: {str(result)}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results

    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            **self.connection_stats,
            "active_sessions": len(self.session_cache),
            "success_rate": (
                self.connection_stats["successful_requests"]
                / max(self.connection_stats["total_requests"], 1)
                * 100
            ),
        }

    async def close_all_sessions(self):
        """关闭所有会话"""
        # 停止后台清理任务
        self._shutdown = True
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=1)
            except Exception:
                pass

        async with self.session_lock:
            for session in self.session_cache.values():
                if not session.closed:
                    await session.close()

            self.session_cache.clear()
            self.session_last_used.clear()

        logger.info("已关闭所有HTTP会话")

    async def shutdown(self):
        """对外统一的关闭方法（别名）"""
        await self.close_all_sessions()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_all_sessions()


# 全局HTTP客户端实例
http_client = EnhancedHttpClient()
