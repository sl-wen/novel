"""
增强的超时管理器
提供动态超时调整、心跳机制和熔断器功能
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Callable, Any
from collections import deque

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class TimeoutConfig:
    """超时配置"""
    base_timeout: float = 30.0          # 基础超时时间（秒）
    max_timeout: float = 300.0          # 最大超时时间（秒）
    min_timeout: float = 10.0           # 最小超时时间（秒）
    adaptive_factor: float = 1.5        # 自适应因子
    heartbeat_interval: float = 5.0     # 心跳间隔（秒）
    circuit_failure_threshold: int = 5  # 熔断器失败阈值
    circuit_recovery_timeout: float = 60.0  # 熔断器恢复超时（秒）
    circuit_test_requests: int = 3      # 半开状态测试请求数


@dataclass
class OperationStats:
    """操作统计"""
    success_count: int = 0
    failure_count: int = 0
    total_time: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=10))
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None


class TimeoutManager:
    """增强的超时管理器"""
    
    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self.operation_stats: Dict[str, OperationStats] = {}
        self.circuit_states: Dict[str, CircuitState] = {}
        self.circuit_failure_counts: Dict[str, int] = {}
        self.circuit_last_failure_time: Dict[str, float] = {}
        self.active_operations: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def execute_with_timeout(
        self,
        operation_name: str,
        coro_func: Callable,
        *args,
        heartbeat_callback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        执行带超时控制的异步操作
        
        Args:
            operation_name: 操作名称
            coro_func: 协程函数
            heartbeat_callback: 心跳回调函数
            *args, **kwargs: 传递给协程函数的参数
            
        Returns:
            操作结果
            
        Raises:
            asyncio.TimeoutError: 操作超时
            Exception: 其他异常
        """
        # 检查熔断器状态
        if not await self._check_circuit_breaker(operation_name):
            raise Exception(f"操作 {operation_name} 被熔断器阻止")
        
        # 计算动态超时时间
        timeout = self._calculate_dynamic_timeout(operation_name)
        
        start_time = time.time()
        operation_id = f"{operation_name}_{start_time}"
        
        try:
            # 创建心跳任务
            heartbeat_task = None
            if heartbeat_callback:
                heartbeat_task = asyncio.create_task(
                    self._heartbeat_loop(operation_id, heartbeat_callback)
                )
            
            # 执行主操作
            try:
                result = await asyncio.wait_for(
                    coro_func(*args, **kwargs),
                    timeout=timeout
                )
                
                # 记录成功
                await self._record_success(operation_name, time.time() - start_time)
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"操作 {operation_name} 超时 ({timeout}s)")
                await self._record_failure(operation_name, "timeout")
                raise
            except Exception as e:
                logger.error(f"操作 {operation_name} 失败: {str(e)}")
                await self._record_failure(operation_name, str(e))
                raise
            finally:
                # 清理心跳任务
                if heartbeat_task and not heartbeat_task.done():
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                
                # 移除活跃操作记录
                self.active_operations.pop(operation_id, None)
        
        except Exception as e:
            # 更新熔断器状态
            await self._update_circuit_breaker(operation_name, False)
            raise
    
    def _calculate_dynamic_timeout(self, operation_name: str) -> float:
        """
        计算动态超时时间
        
        Args:
            operation_name: 操作名称
            
        Returns:
            超时时间（秒）
        """
        stats = self.operation_stats.get(operation_name)
        if not stats or not stats.recent_times:
            return self.config.base_timeout
        
        # 计算平均时间
        avg_time = sum(stats.recent_times) / len(stats.recent_times)
        
        # 动态调整超时时间
        dynamic_timeout = avg_time * self.config.adaptive_factor
        
        # 限制在最小和最大值之间
        timeout = max(
            self.config.min_timeout,
            min(self.config.max_timeout, dynamic_timeout)
        )
        
        logger.debug(f"操作 {operation_name} 动态超时: {timeout:.1f}s (平均: {avg_time:.1f}s)")
        return timeout
    
    async def _heartbeat_loop(self, operation_id: str, callback: Callable):
        """
        心跳循环
        
        Args:
            operation_id: 操作ID
            callback: 心跳回调函数
        """
        try:
            while True:
                await asyncio.sleep(self.config.heartbeat_interval)
                
                # 检查操作是否仍在进行
                if operation_id not in self.active_operations:
                    break
                
                # 执行心跳回调
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(operation_id)
                    else:
                        callback(operation_id)
                except Exception as e:
                    logger.warning(f"心跳回调失败: {str(e)}")
                    
        except asyncio.CancelledError:
            logger.debug(f"心跳任务被取消: {operation_id}")
    
    async def _check_circuit_breaker(self, operation_name: str) -> bool:
        """
        检查熔断器状态
        
        Args:
            operation_name: 操作名称
            
        Returns:
            是否允许执行操作
        """
        async with self._lock:
            state = self.circuit_states.get(operation_name, CircuitState.CLOSED)
            
            if state == CircuitState.CLOSED:
                return True
            elif state == CircuitState.OPEN:
                # 检查是否可以进入半开状态
                last_failure = self.circuit_last_failure_time.get(operation_name, 0)
                if time.time() - last_failure > self.config.circuit_recovery_timeout:
                    self.circuit_states[operation_name] = CircuitState.HALF_OPEN
                    logger.info(f"熔断器 {operation_name} 进入半开状态")
                    return True
                return False
            elif state == CircuitState.HALF_OPEN:
                return True
        
        return False
    
    async def _update_circuit_breaker(self, operation_name: str, success: bool):
        """
        更新熔断器状态
        
        Args:
            operation_name: 操作名称
            success: 操作是否成功
        """
        async with self._lock:
            state = self.circuit_states.get(operation_name, CircuitState.CLOSED)
            
            if success:
                if state == CircuitState.HALF_OPEN:
                    # 半开状态成功，恢复到关闭状态
                    self.circuit_states[operation_name] = CircuitState.CLOSED
                    self.circuit_failure_counts[operation_name] = 0
                    logger.info(f"熔断器 {operation_name} 恢复到关闭状态")
            else:
                # 增加失败计数
                failure_count = self.circuit_failure_counts.get(operation_name, 0) + 1
                self.circuit_failure_counts[operation_name] = failure_count
                self.circuit_last_failure_time[operation_name] = time.time()
                
                if failure_count >= self.config.circuit_failure_threshold:
                    if state != CircuitState.OPEN:
                        self.circuit_states[operation_name] = CircuitState.OPEN
                        logger.warning(f"熔断器 {operation_name} 进入开启状态 (失败 {failure_count} 次)")
    
    async def _record_success(self, operation_name: str, duration: float):
        """记录成功操作"""
        async with self._lock:
            if operation_name not in self.operation_stats:
                self.operation_stats[operation_name] = OperationStats()
            
            stats = self.operation_stats[operation_name]
            stats.success_count += 1
            stats.total_time += duration
            stats.recent_times.append(duration)
            stats.last_success_time = time.time()
            
            # 更新熔断器
            await self._update_circuit_breaker(operation_name, True)
    
    async def _record_failure(self, operation_name: str, error_msg: str):
        """记录失败操作"""
        async with self._lock:
            if operation_name not in self.operation_stats:
                self.operation_stats[operation_name] = OperationStats()
            
            stats = self.operation_stats[operation_name]
            stats.failure_count += 1
            stats.last_failure_time = time.time()
            
            # 更新熔断器
            await self._update_circuit_breaker(operation_name, False)
    
    def get_stats(self, operation_name: str) -> Optional[Dict]:
        """获取操作统计信息"""
        stats = self.operation_stats.get(operation_name)
        if not stats:
            return None
        
        total_operations = stats.success_count + stats.failure_count
        success_rate = (stats.success_count / total_operations * 100) if total_operations > 0 else 0
        avg_time = (stats.total_time / stats.success_count) if stats.success_count > 0 else 0
        
        return {
            "operation_name": operation_name,
            "success_count": stats.success_count,
            "failure_count": stats.failure_count,
            "success_rate": round(success_rate, 2),
            "average_time": round(avg_time, 2),
            "circuit_state": self.circuit_states.get(operation_name, CircuitState.CLOSED).value,
            "last_success_time": stats.last_success_time,
            "last_failure_time": stats.last_failure_time,
        }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有操作的统计信息"""
        return {name: self.get_stats(name) for name in self.operation_stats.keys()}


# 全局超时管理器实例
timeout_manager = TimeoutManager()