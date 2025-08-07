
"""
增强错误处理器
提供更好的错误处理和恢复机制
"""
import logging
import traceback
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class EnhancedErrorHandler:
    """增强错误处理器"""
    
    @staticmethod
    def handle_request_error(error: Exception, url: str, context: str = "") -> None:
        """处理请求错误
        
        Args:
            error: 异常对象
            url: 请求URL
            context: 上下文信息
        """
        error_msg = str(error)
        
        # 根据错误类型进行分类处理
        if "timeout" in error_msg.lower():
            logger.warning(f"请求超时 {context}: {url}")
        elif "connection" in error_msg.lower():
            logger.warning(f"连接失败 {context}: {url}")
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            logger.warning(f"访问被拒绝 {context}: {url}")
        elif "404" in error_msg:
            logger.warning(f"页面不存在 {context}: {url}")
        elif "ssl" in error_msg.lower():
            logger.warning(f"SSL证书问题 {context}: {url}")
        else:
            logger.error(f"未知错误 {context}: {url} - {error_msg}")
    
    @staticmethod
    def handle_parse_error(error: Exception, source_name: str, context: str = "") -> None:
        """处理解析错误
        
        Args:
            error: 异常对象
            source_name: 书源名称
            context: 上下文信息
        """
        error_msg = str(error)
        
        if "beautifulsoup" in error_msg.lower():
            logger.warning(f"HTML解析错误 {context}: {source_name}")
        elif "selector" in error_msg.lower():
            logger.warning(f"选择器错误 {context}: {source_name}")
        else:
            logger.error(f"解析错误 {context}: {source_name} - {error_msg}")
    
    @staticmethod
    def safe_execute(func: Callable, *args, **kwargs) -> Optional[Any]:
        """安全执行函数
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值，失败返回None
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数执行失败: {func.__name__} - {str(e)}")
            return None
    
    @staticmethod
    def get_error_summary() -> dict:
        """获取错误统计
        
        Returns:
            错误统计信息
        """
        # 这里可以实现错误统计功能
        return {
            "total_errors": 0,
            "request_errors": 0,
            "parse_errors": 0,
            "timeout_errors": 0
        }
