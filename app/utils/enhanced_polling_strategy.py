"""
增强的轮询策略管理器
提供指数退避、自适应间隔和智能重试机制
"""
import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Callable, Any, List
from collections import deque

logger = logging.getLogger(__name__)


class PollingStrategy(Enum):
    """轮询策略枚举"""
    FIXED_INTERVAL = "fixed_interval"          # 固定间隔
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数退避
    ADAPTIVE = "adaptive"                      # 自适应
    SMART_POLLING = "smart_polling"            # 智能轮询


@dataclass
class PollingConfig:
    """轮询配置"""
    strategy: PollingStrategy = PollingStrategy.SMART_POLLING
    base_interval: float = 1.0              # 基础间隔（秒）
    max_interval: float = 60.0              # 最大间隔（秒）
    min_interval: float = 0.5               # 最小间隔（秒）
    backoff_multiplier: float = 2.0         # 退避倍数
    jitter_factor: float = 0.1              # 抖动因子
    max_attempts: int = 100                 # 最大尝试次数
    success_reset_threshold: int = 3        # 成功重置阈值
    adaptive_window_size: int = 10          # 自适应窗口大小
    timeout_increase_factor: float = 1.2    # 超时增长因子
    fast_poll_threshold: float = 0.1        # 快速轮询阈值（完成度）
    slow_poll_threshold: float = 0.9        # 慢速轮询阈值（完成度）


@dataclass
class PollingState:
    """轮询状态"""
    current_interval: float = 1.0
    attempt_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=10))
    total_elapsed_time: float = 0.0
    start_time: float = field(default_factory=time.time)


class EnhancedPollingStrategy:
    """增强的轮询策略管理器"""
    
    def __init__(self, config: Optional[PollingConfig] = None):
        self.config = config or PollingConfig()
        self.polling_states: Dict[str, PollingState] = {}
        self._lock = asyncio.Lock()
    
    async def poll_until_complete(
        self,
        task_name: str,
        check_function: Callable[[], Any],
        completion_check: Callable[[Any], bool],
        progress_callback: Optional[Callable[[Any], None]] = None,
        heartbeat_callback: Optional[Callable[[str], None]] = None,
    ) -> Any:
        """
        轮询直到任务完成
        
        Args:
            task_name: 任务名称
            check_function: 检查函数，返回当前状态
            completion_check: 完成检查函数，判断是否完成
            progress_callback: 进度回调函数
            heartbeat_callback: 心跳回调函数
            
        Returns:
            最终结果
            
        Raises:
            asyncio.TimeoutError: 超过最大尝试次数
            Exception: 其他异常
        """
        # 初始化轮询状态
        await self._init_polling_state(task_name)
        
        logger.info(f"开始轮询任务: {task_name}")
        
        try:
            while True:
                state = self.polling_states[task_name]
                
                # 检查是否超过最大尝试次数
                if state.attempt_count >= self.config.max_attempts:
                    raise asyncio.TimeoutError(f"轮询任务 {task_name} 超过最大尝试次数")
                
                # 执行检查
                start_check_time = time.time()
                try:
                    # 执行心跳回调
                    if heartbeat_callback:
                        try:
                            if asyncio.iscoroutinefunction(heartbeat_callback):
                                await heartbeat_callback(task_name)
                            else:
                                heartbeat_callback(task_name)
                        except Exception as e:
                            logger.warning(f"心跳回调失败: {str(e)}")
                    
                    # 执行状态检查
                    if asyncio.iscoroutinefunction(check_function):
                        result = await check_function()
                    else:
                        result = check_function()
                    
                    check_duration = time.time() - start_check_time
                    
                    # 记录成功检查
                    await self._record_check_success(task_name, check_duration)
                    
                    # 执行进度回调
                    if progress_callback:
                        try:
                            if asyncio.iscoroutinefunction(progress_callback):
                                await progress_callback(result)
                            else:
                                progress_callback(result)
                        except Exception as e:
                            logger.warning(f"进度回调失败: {str(e)}")
                    
                    # 检查是否完成
                    if completion_check(result):
                        logger.info(f"轮询任务 {task_name} 完成，共尝试 {state.attempt_count} 次")
                        return result
                    
                    # 计算下次轮询间隔
                    next_interval = await self._calculate_next_interval(task_name, result)
                    
                    logger.debug(
                        f"轮询任务 {task_name} 第 {state.attempt_count} 次检查完成，"
                        f"下次间隔: {next_interval:.1f}s"
                    )
                    
                    # 等待下次轮询
                    await asyncio.sleep(next_interval)
                    
                except Exception as e:
                    check_duration = time.time() - start_check_time
                    await self._record_check_failure(task_name, str(e), check_duration)
                    
                    # 计算重试间隔
                    retry_interval = await self._calculate_retry_interval(task_name)
                    
                    logger.warning(
                        f"轮询任务 {task_name} 检查失败: {str(e)}，"
                        f"{retry_interval:.1f}s后重试"
                    )
                    
                    await asyncio.sleep(retry_interval)
        
        finally:
            # 清理轮询状态
            await self._cleanup_polling_state(task_name)
    
    async def _init_polling_state(self, task_name: str):
        """初始化轮询状态"""
        async with self._lock:
            self.polling_states[task_name] = PollingState(
                current_interval=self.config.base_interval
            )
    
    async def _cleanup_polling_state(self, task_name: str):
        """清理轮询状态"""
        async with self._lock:
            self.polling_states.pop(task_name, None)
    
    async def _record_check_success(self, task_name: str, duration: float):
        """记录检查成功"""
        async with self._lock:
            state = self.polling_states[task_name]
            state.attempt_count += 1
            state.consecutive_successes += 1
            state.consecutive_failures = 0
            state.last_success_time = time.time()
            state.recent_durations.append(duration)
            state.total_elapsed_time = time.time() - state.start_time
    
    async def _record_check_failure(self, task_name: str, error_msg: str, duration: float):
        """记录检查失败"""
        async with self._lock:
            state = self.polling_states[task_name]
            state.attempt_count += 1
            state.consecutive_failures += 1
            state.consecutive_successes = 0
            state.last_failure_time = time.time()
            state.recent_durations.append(duration)
            state.total_elapsed_time = time.time() - state.start_time
    
    async def _calculate_next_interval(self, task_name: str, current_result: Any) -> float:
        """
        计算下次轮询间隔
        
        Args:
            task_name: 任务名称
            current_result: 当前检查结果
            
        Returns:
            下次轮询间隔（秒）
        """
        state = self.polling_states[task_name]
        
        if self.config.strategy == PollingStrategy.FIXED_INTERVAL:
            return self.config.base_interval
        
        elif self.config.strategy == PollingStrategy.EXPONENTIAL_BACKOFF:
            return self._calculate_exponential_backoff(state)
        
        elif self.config.strategy == PollingStrategy.ADAPTIVE:
            return self._calculate_adaptive_interval(state)
        
        elif self.config.strategy == PollingStrategy.SMART_POLLING:
            return self._calculate_smart_interval(state, current_result)
        
        else:
            return self.config.base_interval
    
    def _calculate_exponential_backoff(self, state: PollingState) -> float:
        """计算指数退避间隔"""
        interval = self.config.base_interval * (
            self.config.backoff_multiplier ** state.consecutive_failures
        )
        
        # 添加抖动
        jitter = random.uniform(
            -interval * self.config.jitter_factor,
            interval * self.config.jitter_factor
        )
        
        final_interval = max(
            self.config.min_interval,
            min(self.config.max_interval, interval + jitter)
        )
        
        return final_interval
    
    def _calculate_adaptive_interval(self, state: PollingState) -> float:
        """计算自适应间隔"""
        if not state.recent_durations:
            return self.config.base_interval
        
        # 基于最近的响应时间调整间隔
        avg_duration = sum(state.recent_durations) / len(state.recent_durations)
        
        # 如果响应时间较长，增加轮询间隔
        if avg_duration > 5.0:
            multiplier = 2.0
        elif avg_duration > 2.0:
            multiplier = 1.5
        else:
            multiplier = 1.0
        
        # 基于连续成功/失败调整
        if state.consecutive_successes > self.config.success_reset_threshold:
            multiplier *= 0.8  # 连续成功，减少间隔
        elif state.consecutive_failures > 0:
            multiplier *= (1.0 + state.consecutive_failures * 0.2)  # 连续失败，增加间隔
        
        interval = self.config.base_interval * multiplier
        
        return max(
            self.config.min_interval,
            min(self.config.max_interval, interval)
        )
    
    def _calculate_smart_interval(self, state: PollingState, current_result: Any) -> float:
        """计算智能轮询间隔"""
        # 基础间隔计算
        base_interval = self._calculate_adaptive_interval(state)
        
        # 尝试从结果中提取进度信息
        progress_percentage = self._extract_progress_percentage(current_result)
        
        if progress_percentage is not None:
            # 基于进度调整间隔
            if progress_percentage < self.config.fast_poll_threshold * 100:
                # 刚开始，使用较短间隔
                multiplier = 0.5
            elif progress_percentage > self.config.slow_poll_threshold * 100:
                # 接近完成，使用较长间隔
                multiplier = 2.0
            else:
                # 中间阶段，使用标准间隔
                multiplier = 1.0
            
            base_interval *= multiplier
        
        # 添加智能抖动
        jitter = random.uniform(
            -base_interval * self.config.jitter_factor,
            base_interval * self.config.jitter_factor
        )
        
        final_interval = max(
            self.config.min_interval,
            min(self.config.max_interval, base_interval + jitter)
        )
        
        return final_interval
    
    def _extract_progress_percentage(self, result: Any) -> Optional[float]:
        """从结果中提取进度百分比"""
        try:
            if hasattr(result, 'progress_percentage'):
                return result.progress_percentage
            elif isinstance(result, dict):
                if 'progress_percentage' in result:
                    return result['progress_percentage']
                elif 'data' in result and isinstance(result['data'], dict):
                    return result['data'].get('progress_percentage')
            return None
        except Exception:
            return None
    
    async def _calculate_retry_interval(self, task_name: str) -> float:
        """计算重试间隔"""
        state = self.polling_states[task_name]
        
        # 使用指数退避
        interval = self.config.base_interval * (
            self.config.backoff_multiplier ** state.consecutive_failures
        )
        
        # 添加抖动以避免雷群效应
        jitter = random.uniform(0, interval * self.config.jitter_factor)
        
        final_interval = max(
            self.config.min_interval,
            min(self.config.max_interval, interval + jitter)
        )
        
        return final_interval
    
    def get_polling_stats(self, task_name: str) -> Optional[Dict]:
        """获取轮询统计信息"""
        state = self.polling_states.get(task_name)
        if not state:
            return None
        
        avg_duration = (
            sum(state.recent_durations) / len(state.recent_durations)
            if state.recent_durations else 0
        )
        
        return {
            "task_name": task_name,
            "current_interval": state.current_interval,
            "attempt_count": state.attempt_count,
            "consecutive_failures": state.consecutive_failures,
            "consecutive_successes": state.consecutive_successes,
            "average_check_duration": round(avg_duration, 3),
            "total_elapsed_time": round(state.total_elapsed_time, 2),
            "last_success_time": state.last_success_time,
            "last_failure_time": state.last_failure_time,
        }


class AdvancedPollingManager:
    """高级轮询管理器"""
    
    def __init__(self):
        self.strategy_manager = EnhancedPollingStrategy()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def start_polling_task(
        self,
        task_id: str,
        check_function: Callable,
        completion_check: Callable[[Any], bool],
        config: Optional[PollingConfig] = None,
        progress_callback: Optional[Callable] = None,
        heartbeat_callback: Optional[Callable] = None,
    ) -> str:
        """
        启动轮询任务
        
        Args:
            task_id: 任务ID
            check_function: 状态检查函数
            completion_check: 完成检查函数
            config: 轮询配置
            progress_callback: 进度回调
            heartbeat_callback: 心跳回调
            
        Returns:
            任务ID
        """
        if config:
            strategy_manager = EnhancedPollingStrategy(config)
        else:
            strategy_manager = self.strategy_manager
        
        async def polling_task():
            try:
                result = await strategy_manager.poll_until_complete(
                    task_id,
                    check_function,
                    completion_check,
                    progress_callback,
                    heartbeat_callback
                )
                
                async with self._lock:
                    self.task_results[task_id] = result
                
                logger.info(f"轮询任务 {task_id} 成功完成")
                return result
                
            except Exception as e:
                logger.error(f"轮询任务 {task_id} 失败: {str(e)}")
                async with self._lock:
                    self.task_results[task_id] = {"error": str(e)}
                raise
            finally:
                # 清理任务
                async with self._lock:
                    self.active_tasks.pop(task_id, None)
        
        # 启动轮询任务
        async with self._lock:
            if task_id in self.active_tasks:
                # 取消现有任务
                self.active_tasks[task_id].cancel()
            
            task = asyncio.create_task(polling_task())
            self.active_tasks[task_id] = task
        
        logger.info(f"轮询任务 {task_id} 已启动")
        return task_id
    
    async def get_task_result(self, task_id: str, wait: bool = False, timeout: float = None) -> Any:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            wait: 是否等待任务完成
            timeout: 等待超时时间
            
        Returns:
            任务结果
        """
        if wait:
            task = self.active_tasks.get(task_id)
            if task and not task.done():
                try:
                    if timeout:
                        await asyncio.wait_for(task, timeout=timeout)
                    else:
                        await task
                except asyncio.TimeoutError:
                    logger.warning(f"等待任务 {task_id} 结果超时")
                except Exception as e:
                    logger.error(f"等待任务 {task_id} 失败: {str(e)}")
        
        return self.task_results.get(task_id)
    
    async def cancel_task(self, task_id: str):
        """取消轮询任务"""
        async with self._lock:
            task = self.active_tasks.get(task_id)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            self.active_tasks.pop(task_id, None)
            self.task_results.pop(task_id, None)
        
        logger.info(f"轮询任务 {task_id} 已取消")
    
    def get_active_tasks(self) -> List[str]:
        """获取活跃任务列表"""
        return list(self.active_tasks.keys())
    
    def get_task_stats(self, task_id: str) -> Optional[Dict]:
        """获取任务统计信息"""
        return self.strategy_manager.get_polling_stats(task_id)
    
    async def wait_for_completion(self, task_id: str) -> Any:
        """
        等待轮询任务完成并返回结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果
            
        Raises:
            ValueError: 任务不存在
            Exception: 任务执行失败
        """
        async with self._lock:
            task = self.active_tasks.get(task_id)
            if not task:
                # 检查是否已有结果
                if task_id in self.task_results:
                    result = self.task_results[task_id]
                    if isinstance(result, dict) and "error" in result:
                        raise Exception(result["error"])
                    return result
                raise ValueError(f"轮询任务不存在: {task_id}")
        
        # 等待任务完成
        try:
            result = await task
            return result
        except Exception as e:
            logger.error(f"等待轮询任务 {task_id} 完成时失败: {str(e)}")
            raise


# 全局轮询管理器实例
polling_manager = AdvancedPollingManager()