
"""
增强HTTP客户端工具类
提供更好的网络请求处理和错误恢复
"""
import asyncio
import logging
import random
from typing import Optional, Dict, Any, List

import aiohttp
from aiohttp import ClientTimeout, TCPConnector

from app.core.config import settings

logger = logging.getLogger(__name__)


class EnhancedHttpClient:
    """增强HTTP客户端，提供更好的网络请求处理"""
    
    # 用户代理池
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    ]
    
    # 请求策略
    REQUEST_STRATEGIES = [
        {
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            },
            'description': '完整压缩支持'
        },
        {
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'description': '不支持Brotli'
        },
        {
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'User-Agent': 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
            },
            'description': 'IE兼容模式'
        }
    ]
    
    @staticmethod
    async def fetch_html_with_retry(
        url: str, 
        timeout: int = None, 
        referer: str = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[str]:
        """带重试的HTML获取
        
        Args:
            url: 页面URL
            timeout: 超时时间（秒）
            referer: Referer头
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            HTML页面内容，失败返回None
        """
        if timeout is None:
            timeout = settings.DEFAULT_TIMEOUT
        
        for attempt in range(max_retries):
            try:
                result = await EnhancedHttpClient._fetch_html_single(url, timeout, referer)
                if result:
                    logger.info(f"获取HTML成功 (尝试 {attempt + 1}/{max_retries}): {url}")
                    return result
                
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"获取HTML失败，{delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {url}")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(f"获取HTML异常，{delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"获取HTML最终失败 (共 {max_retries} 次尝试): {str(e)}")
        
        return None
    
    @staticmethod
    async def _fetch_html_single(url: str, timeout: int, referer: str = None) -> Optional[str]:
        """单次HTML获取"""
        # 随机选择用户代理
        user_agent = random.choice(EnhancedHttpClient.USER_AGENTS)
        
        for i, strategy in enumerate(EnhancedHttpClient.REQUEST_STRATEGIES):
            try:
                logger.debug(f"尝试获取HTML (策略 {i+1}/{len(EnhancedHttpClient.REQUEST_STRATEGIES)} - {strategy['description']}): {url}")
                
                # 创建连接器
                connector = TCPConnector(
                    limit=settings.MAX_CONCURRENT_REQUESTS,
                    ssl=False,  # 跳过SSL证书验证
                    use_dns_cache=True,
                    ttl_dns_cache=300,
                    enable_cleanup_closed=True,
                )
                
                # 创建超时设置
                client_timeout = ClientTimeout(
                    total=timeout,
                    connect=10,
                    sock_read=30
                )
                
                # 准备请求头
                headers = strategy['headers'].copy()
                headers['User-Agent'] = user_agent
                
                if referer:
                    headers['Referer'] = referer
                
                async with aiohttp.ClientSession(
                    timeout=client_timeout,
                    connector=connector,
                    headers=headers
                ) as session:
                    async with session.get(url) as response:
                        logger.debug(f"响应状态码: {response.status} (策略: {strategy['description']})")
                        
                        if response.status == 200:
                            html = await response.text()
                            logger.info(f"获取HTML成功，长度: {len(html)} (使用策略: {strategy['description']})")
                            return html
                        elif response.status == 403:
                            logger.warning(f"访问被拒绝 (403): {url}")
                            # 对于403错误，尝试下一个策略
                            continue
                        else:
                            logger.warning(f"请求失败: {url}, 状态码: {response.status} (策略: {strategy['description']})")
                            
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"请求异常 (策略 {i+1} - {strategy['description']}): {url}, 错误: {error_msg}")
                
                # 如果是Brotli相关错误，继续尝试下一个策略
                if 'brotli' in error_msg.lower() or 'br' in error_msg.lower() or 'content-encoding' in error_msg.lower():
                    logger.info(f"检测到压缩问题，尝试下一个策略...")
                    continue
                
                # 如果是连接相关错误，也尝试下一个策略
                if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
                    if i < len(EnhancedHttpClient.REQUEST_STRATEGIES) - 1:
                        logger.info(f"检测到连接问题，尝试下一个策略...")
                        continue
                
                # 如果不是最后一个策略，继续尝试
                if i < len(EnhancedHttpClient.REQUEST_STRATEGIES) - 1:
                    continue
        
        # 所有策略都失败了
        logger.error(f"所有请求策略都失败了: {url}")
        return None
