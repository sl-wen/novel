import asyncio
import logging
import time
import threading
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Deque
import statistics
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        """获取毫秒级持续时间"""
        return self.duration * 1000


@dataclass
class OperationStats:
    """操作统计信息"""
    operation_name: str
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    durations: Deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    recent_errors: Deque[str] = field(default_factory=lambda: deque(maxlen=50))
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count * 100
    
    @property
    def average_duration(self) -> float:
        """平均持续时间"""
        if self.total_count == 0:
            return 0.0
        return self.total_duration / self.total_count
    
    @property
    def average_duration_ms(self) -> float:
        """平均持续时间（毫秒）"""
        return self.average_duration * 1000
    
    @property
    def median_duration(self) -> float:
        """中位数持续时间"""
        if not self.durations:
            return 0.0
        return statistics.median(self.durations)
    
    @property
    def percentile_95_duration(self) -> float:
        """95分位数持续时间"""
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * 0.95)
        return sorted_durations[min(index, len(sorted_durations) - 1)]


class PerformanceMonitor:
    """性能监控器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化性能监控器"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.stats: Dict[str, OperationStats] = defaultdict(lambda: OperationStats(""))
        self.active_operations: Dict[str, float] = {}
        self.slow_query_threshold = 5.0  # 慢查询阈值（秒）
        self.alert_threshold = 10.0  # 告警阈值（秒）
        
        # 性能数据存储
        self.metrics_history: Deque[PerformanceMetric] = deque(maxlen=10000)
        self.slow_operations: Deque[PerformanceMetric] = deque(maxlen=1000)
        
        # 监控配置
        self.enable_detailed_logging = True
        self.enable_slow_query_logging = True
        self.enable_alerts = True
        
        # 回调函数
        self.slow_query_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        
        # 统计数据锁
        self.stats_lock = threading.Lock()
        
        # 启动定期报告任务
        self._start_periodic_reporting()
    
    def _start_periodic_reporting(self):
        """启动定期报告任务"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._periodic_reporting())
        except RuntimeError:
            # 没有运行中的事件循环，稍后启动
            pass
    
    async def _periodic_reporting(self):
        """定期性能报告"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟报告一次
                self._generate_performance_report()
            except Exception as e:
                logger.error(f"定期性能报告出错: {str(e)}")
    
    def _generate_performance_report(self):
        """生成性能报告"""
        try:
            with self.stats_lock:
                if not self.stats:
                    return
                
                logger.info("=== 性能监控报告 ===")
                
                # 按平均响应时间排序
                sorted_stats = sorted(
                    self.stats.items(),
                    key=lambda x: x[1].average_duration,
                    reverse=True
                )
                
                for operation_name, stats in sorted_stats[:10]:  # 只显示前10个最慢的操作
                    logger.info(
                        f"操作: {operation_name} | "
                        f"总数: {stats.total_count} | "
                        f"成功率: {stats.success_rate:.1f}% | "
                        f"平均耗时: {stats.average_duration_ms:.1f}ms | "
                        f"最大耗时: {stats.max_duration * 1000:.1f}ms | "
                        f"95分位数: {stats.percentile_95_duration * 1000:.1f}ms"
                    )
                
                # 报告慢查询
                if self.slow_operations:
                    recent_slow = [op for op in self.slow_operations if time.time() - op.end_time < 300]
                    if recent_slow:
                        logger.warning(f"最近5分钟内有 {len(recent_slow)} 个慢查询")
                
        except Exception as e:
            logger.error(f"生成性能报告失败: {str(e)}")
    
    @asynccontextmanager
    async def monitor_operation(self, operation_name: str, metadata: Dict[str, Any] = None):
        """监控操作的上下文管理器
        
        使用示例:
        async with performance_monitor.monitor_operation("search_novels", {"keyword": "斗破苍穹"}):
            results = await search_novels(keyword)
        """
        start_time = time.time()
        operation_id = f"{operation_name}_{start_time}_{id(asyncio.current_task())}"
        
        with self.stats_lock:
            self.active_operations[operation_id] = start_time
        
        success = True
        error_message = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            # 清理活动操作
            with self.stats_lock:
                self.active_operations.pop(operation_id, None)
            
            # 记录指标
            metric = PerformanceMetric(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=success,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            self._record_metric(metric)
    
    def _record_metric(self, metric: PerformanceMetric):
        """记录性能指标"""
        try:
            with self.stats_lock:
                # 更新统计信息
                stats = self.stats[metric.operation_name]
                if not stats.operation_name:
                    stats.operation_name = metric.operation_name
                
                stats.total_count += 1
                stats.total_duration += metric.duration
                stats.durations.append(metric.duration)
                
                if metric.success:
                    stats.success_count += 1
                else:
                    stats.failure_count += 1
                    if metric.error_message:
                        stats.recent_errors.append(metric.error_message)
                
                # 更新最小最大值
                stats.min_duration = min(stats.min_duration, metric.duration)
                stats.max_duration = max(stats.max_duration, metric.duration)
                
                # 添加到历史记录
                self.metrics_history.append(metric)
                
                # 检查慢查询
                if metric.duration >= self.slow_query_threshold:
                    self.slow_operations.append(metric)
                    
                    if self.enable_slow_query_logging:
                        logger.warning(
                            f"慢查询检测: {metric.operation_name} "
                            f"耗时 {metric.duration_ms:.1f}ms"
                        )
                    
                    # 执行慢查询回调
                    for callback in self.slow_query_callbacks:
                        try:
                            callback(metric)
                        except Exception as e:
                            logger.error(f"慢查询回调执行失败: {str(e)}")
                
                # 检查告警阈值
                if metric.duration >= self.alert_threshold:
                    if self.enable_alerts:
                        logger.error(
                            f"性能告警: {metric.operation_name} "
                            f"耗时 {metric.duration_ms:.1f}ms 超过告警阈值"
                        )
                    
                    # 执行告警回调
                    for callback in self.alert_callbacks:
                        try:
                            callback(metric)
                        except Exception as e:
                            logger.error(f"告警回调执行失败: {str(e)}")
                
                # 详细日志
                if self.enable_detailed_logging and metric.duration > 1.0:
                    logger.info(
                        f"操作完成: {metric.operation_name} | "
                        f"耗时: {metric.duration_ms:.1f}ms | "
                        f"状态: {'成功' if metric.success else '失败'}"
                    )
        
        except Exception as e:
            logger.error(f"记录性能指标失败: {str(e)}")
    
    def get_operation_stats(self, operation_name: str) -> Optional[OperationStats]:
        """获取指定操作的统计信息"""
        with self.stats_lock:
            return self.stats.get(operation_name)
    
    def get_all_stats(self) -> Dict[str, OperationStats]:
        """获取所有操作的统计信息"""
        with self.stats_lock:
            return dict(self.stats)
    
    def get_slow_operations(self, limit: int = 100) -> List[PerformanceMetric]:
        """获取慢操作列表"""
        with self.stats_lock:
            return list(self.slow_operations)[-limit:]
    
    def get_recent_metrics(self, limit: int = 100) -> List[PerformanceMetric]:
        """获取最近的性能指标"""
        with self.stats_lock:
            return list(self.metrics_history)[-limit:]
    
    def get_active_operations(self) -> Dict[str, float]:
        """获取当前活动的操作"""
        current_time = time.time()
        with self.stats_lock:
            return {
                op_id: current_time - start_time 
                for op_id, start_time in self.active_operations.items()
            }
    
    def add_slow_query_callback(self, callback: Callable[[PerformanceMetric], None]):
        """添加慢查询回调函数"""
        self.slow_query_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[PerformanceMetric], None]):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)
    
    def set_thresholds(self, slow_query_threshold: float = None, alert_threshold: float = None):
        """设置性能阈值"""
        if slow_query_threshold is not None:
            self.slow_query_threshold = slow_query_threshold
        if alert_threshold is not None:
            self.alert_threshold = alert_threshold
    
    def export_stats_to_json(self, file_path: str = None) -> str:
        """导出统计信息到JSON文件"""
        try:
            if file_path is None:
                file_path = f"performance_stats_{int(time.time())}.json"
            
            with self.stats_lock:
                export_data = {
                    "timestamp": time.time(),
                    "stats": {},
                    "slow_operations_count": len(self.slow_operations),
                    "total_metrics_count": len(self.metrics_history)
                }
                
                for operation_name, stats in self.stats.items():
                    export_data["stats"][operation_name] = {
                        "total_count": stats.total_count,
                        "success_count": stats.success_count,
                        "failure_count": stats.failure_count,
                        "success_rate": stats.success_rate,
                        "average_duration_ms": stats.average_duration_ms,
                        "min_duration_ms": stats.min_duration * 1000,
                        "max_duration_ms": stats.max_duration * 1000,
                        "median_duration_ms": stats.median_duration * 1000,
                        "percentile_95_duration_ms": stats.percentile_95_duration * 1000,
                        "recent_errors": list(stats.recent_errors)
                    }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"性能统计已导出到: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"导出性能统计失败: {str(e)}")
            return ""
    
    def reset_stats(self):
        """重置所有统计信息"""
        with self.stats_lock:
            self.stats.clear()
            self.metrics_history.clear()
            self.slow_operations.clear()
            self.active_operations.clear()
        
        logger.info("性能统计已重置")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能监控摘要"""
        with self.stats_lock:
            total_operations = sum(stats.total_count for stats in self.stats.values())
            total_successful = sum(stats.success_count for stats in self.stats.values())
            
            return {
                "total_operations": total_operations,
                "total_successful": total_successful,
                "overall_success_rate": (total_successful / max(total_operations, 1)) * 100,
                "unique_operation_types": len(self.stats),
                "slow_operations_count": len(self.slow_operations),
                "active_operations_count": len(self.active_operations),
                "slow_query_threshold_ms": self.slow_query_threshold * 1000,
                "alert_threshold_ms": self.alert_threshold * 1000
            }


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()


# 装饰器形式的性能监控
def monitor_performance(operation_name: str = None, metadata: Dict[str, Any] = None):
    """性能监控装饰器
    
    使用示例:
    @monitor_performance("search_novels")
    async def search_novels(keyword: str):
        # 搜索逻辑
        pass
    """
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with performance_monitor.monitor_operation(operation_name, metadata):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_message = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_message = str(e)
                    raise
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    metric = PerformanceMetric(
                        operation_name=operation_name,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        success=success,
                        error_message=error_message,
                        metadata=metadata or {}
                    )
                    
                    performance_monitor._record_metric(metric)
            
            return sync_wrapper
    return decorator