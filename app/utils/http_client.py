"""
HTTP客户端工具类，提供统一的HTTP请求处理
"""
import asyncio
import logging
from typing import Optional, Dict, Any

import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


class HttpClient:
    """HTTP客户端工具类，处理各种HTTP请求问题"""
    
    @staticmethod
    async def fetch_html(url: str, timeout: int = None, referer: str = None) -> Optional[str]:
        """获取HTML页面内容，自动处理压缩和编码问题
        
        Args:
            url: 页面URL
            timeout: 超时时间（秒）
            referer: Referer头
            
        Returns:
            HTML页面内容，失败返回None
        """
        if timeout is None:
            timeout = settings.DEFAULT_TIMEOUT
            
        # 多种请求策略，按优先级尝试
        strategies = [
            # 策略1: 支持所有压缩格式（包括Brotli）
            {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                'description': '完整压缩支持'
            },
            # 策略2: 不支持Brotli压缩（fallback）
            {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                'description': '不支持Brotli'
            },
            # 策略3: 最简单的请求
            {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                },
                'description': '基本请求'
            }
        ]
        
        # 添加Referer头（如果提供）
        if referer:
            for strategy in strategies:
                strategy['headers']['Referer'] = referer
        
        for i, strategy in enumerate(strategies):
            try:
                logger.debug(f"尝试获取HTML (策略 {i+1}/{len(strategies)} - {strategy['description']}): {url}")
                
                # 创建连接器
                connector = aiohttp.TCPConnector(
                    limit=settings.MAX_CONCURRENT_REQUESTS,
                    ssl=False,  # 跳过SSL证书验证
                    use_dns_cache=True,
                    ttl_dns_cache=300,
                )
                
                # 创建超时设置
                client_timeout = aiohttp.ClientTimeout(
                    total=timeout,
                    connect=10,
                    sock_read=30
                )
                
                async with aiohttp.ClientSession(
                    timeout=client_timeout,
                    connector=connector,
                    headers=strategy['headers']
                ) as session:
                    async with session.get(url) as response:
                        logger.debug(f"响应状态码: {response.status} (策略: {strategy['description']})")
                        
                        if response.status == 200:
                            html = await response.text()
                            logger.info(f"获取HTML成功，长度: {len(html)} (使用策略: {strategy['description']})")
                            return html
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
                    if i < len(strategies) - 1:
                        logger.info(f"检测到连接问题，尝试下一个策略...")
                        continue
                
                # 如果不是最后一个策略，继续尝试
                if i < len(strategies) - 1:
                    continue
        
        # 所有策略都失败了
        logger.error(f"所有请求策略都失败了: {url}")
        return None
    
    @staticmethod
    async def post_data(url: str, data: Dict[str, Any], timeout: int = None, referer: str = None) -> Optional[str]:
        """发送POST请求获取HTML内容
        
        Args:
            url: 请求URL
            data: POST数据
            timeout: 超时时间（秒）
            referer: Referer头
            
        Returns:
            HTML页面内容，失败返回None
        """
        if timeout is None:
            timeout = settings.DEFAULT_TIMEOUT
            
        strategies = [
            {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                'description': '完整压缩支持'
            },
            {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                'description': '不支持Brotli'
            }
        ]
        
        if referer:
            for strategy in strategies:
                strategy['headers']['Referer'] = referer
        
        for i, strategy in enumerate(strategies):
            try:
                logger.debug(f"尝试POST请求 (策略 {i+1}/{len(strategies)} - {strategy['description']}): {url}")
                
                connector = aiohttp.TCPConnector(
                    limit=settings.MAX_CONCURRENT_REQUESTS,
                    ssl=False,
                    use_dns_cache=True,
                    ttl_dns_cache=300,
                )
                
                client_timeout = aiohttp.ClientTimeout(
                    total=timeout,
                    connect=10,
                    sock_read=30
                )
                
                async with aiohttp.ClientSession(
                    timeout=client_timeout,
                    connector=connector,
                    headers=strategy['headers']
                ) as session:
                    async with session.post(url, data=data) as response:
                        logger.debug(f"POST响应状态码: {response.status} (策略: {strategy['description']})")
                        
                        if response.status == 200:
                            html = await response.text()
                            logger.info(f"POST请求成功，长度: {len(html)} (使用策略: {strategy['description']})")
                            return html
                        else:
                            logger.warning(f"POST请求失败: {url}, 状态码: {response.status} (策略: {strategy['description']})")
                            
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"POST请求异常 (策略 {i+1} - {strategy['description']}): {url}, 错误: {error_msg}")
                
                if 'brotli' in error_msg.lower() or 'br' in error_msg.lower() or 'content-encoding' in error_msg.lower():
                    logger.info(f"检测到压缩问题，尝试下一个策略...")
                    continue
                
                if i < len(strategies) - 1:
                    continue
        
        logger.error(f"所有POST策略都失败了: {url}")
        return None