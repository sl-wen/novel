
"""
增强重试机制
提供更智能的重试策略
"""
import asyncio
import logging
import random
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


class EnhancedRetryMechanism:
    """增强重试机制"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """初始化重试机制
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Optional[Any]:
        """带重试的函数执行
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值，失败返回None
        """
        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                if result:
                    logger.debug(f"函数执行成功 (尝试 {attempt + 1}/{self.max_retries})")
                    return result
                
                if attempt < self.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"函数返回空结果，{delay}秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"函数执行异常，{delay}秒后重试 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"函数执行最终失败 (共 {self.max_retries} 次尝试): {str(e)}")
        
        return None
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算延迟时间
        
        Args:
            attempt: 当前尝试次数
            
        Returns:
            延迟时间（秒）
        """
        # 指数退避 + 随机抖动
        delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0, 0.1 * delay)
        return delay + jitter
    
    @staticmethod
    def should_retry(error: Exception) -> bool:
        """判断是否应该重试
        
        Args:
            error: 异常对象
            
        Returns:
            是否应该重试
        """
        error_msg = str(error).lower()
        
        # 可重试的错误
        retryable_errors = [
            "timeout",
            "connection",
            "temporary",
            "rate limit",
            "too many requests"
        ]
        
        # 不可重试的错误
        non_retryable_errors = [
            "404",
            "not found",
            "forbidden",
            "unauthorized",
            "invalid"
        ]
        
        for retryable in retryable_errors:
            if retryable in error_msg:
                return True
        
        for non_retryable in non_retryable_errors:
            if non_retryable in error_msg:
                return False
        
        # 默认重试
        return True
