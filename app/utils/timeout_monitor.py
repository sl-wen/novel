"""
超时监控和告警系统
提供实时监控和预警功能
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable
from collections import deque

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TimeoutAlert:
    """超时告警"""
    task_id: str
    operation_name: str
    alert_level: AlertLevel
    message: str
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    retry_count: int = 0


@dataclass
class MonitorConfig:
    """监控配置"""
    warning_threshold: float = 60.0      # 警告阈值（秒）
    error_threshold: float = 180.0       # 错误阈值（秒）
    critical_threshold: float = 300.0    # 严重阈值（秒）
    heartbeat_timeout: float = 30.0      # 心跳超时（秒）
    check_interval: float = 10.0         # 检查间隔（秒）
    max_alerts_per_task: int = 10        # 每个任务最大告警数
    alert_cooldown: float = 60.0         # 告警冷却时间（秒）


class TimeoutMonitor:
    """超时监控器"""
    
    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.monitored_tasks: Dict[str, Dict] = {}
        self.alerts: Dict[str, List[TimeoutAlert]] = {}
        self.alert_callbacks: List[Callable[[TimeoutAlert], None]] = []
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._last_alert_time: Dict[str, float] = {}
    
    async def start_monitoring(self):
        """启动监控"""
        if self._monitor_task and not self._monitor_task.done():
            return
        
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("超时监控器已启动")
    
    async def stop_monitoring(self):
        """停止监控"""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("超时监控器已停止")
    
    async def register_task(
        self,
        task_id: str,
        operation_name: str,
        expected_duration: Optional[float] = None,
        custom_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        注册需要监控的任务
        
        Args:
            task_id: 任务ID
            operation_name: 操作名称
            expected_duration: 预期持续时间（秒）
            custom_thresholds: 自定义阈值
        """
        async with self._lock:
            thresholds = custom_thresholds or {
                "warning": self.config.warning_threshold,
                "error": self.config.error_threshold,
                "critical": self.config.critical_threshold,
            }
            
            self.monitored_tasks[task_id] = {
                "operation_name": operation_name,
                "start_time": time.time(),
                "last_heartbeat": time.time(),
                "expected_duration": expected_duration,
                "thresholds": thresholds,
                "status": "running",
                "retry_count": 0,
            }
            
            self.alerts[task_id] = []
        
        logger.info(f"注册监控任务: {task_id} ({operation_name})")
    
    async def unregister_task(self, task_id: str):
        """取消任务监控"""
        async with self._lock:
            self.monitored_tasks.pop(task_id, None)
            self.alerts.pop(task_id, None)
            self._last_alert_time.pop(task_id, None)
        
        logger.info(f"取消监控任务: {task_id}")
    
    async def update_heartbeat(self, task_id: str):
        """更新任务心跳"""
        async with self._lock:
            if task_id in self.monitored_tasks:
                self.monitored_tasks[task_id]["last_heartbeat"] = time.time()
                logger.debug(f"更新任务心跳: {task_id}")
    
    async def update_task_status(self, task_id: str, status: str, retry_count: int = 0):
        """更新任务状态"""
        async with self._lock:
            if task_id in self.monitored_tasks:
                self.monitored_tasks[task_id]["status"] = status
                self.monitored_tasks[task_id]["retry_count"] = retry_count
    
    def add_alert_callback(self, callback: Callable[[TimeoutAlert], None]):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[TimeoutAlert], None]):
        """移除告警回调函数"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def _monitor_loop(self):
        """监控循环"""
        while True:
            try:
                await asyncio.sleep(self.config.check_interval)
                await self._check_all_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环出错: {str(e)}")
    
    async def _check_all_tasks(self):
        """检查所有任务"""
        current_time = time.time()
        
        async with self._lock:
            tasks_to_check = list(self.monitored_tasks.items())
        
        for task_id, task_info in tasks_to_check:
            await self._check_single_task(task_id, task_info, current_time)
    
    async def _check_single_task(self, task_id: str, task_info: Dict, current_time: float):
        """检查单个任务"""
        start_time = task_info["start_time"]
        last_heartbeat = task_info["last_heartbeat"]
        operation_name = task_info["operation_name"]
        thresholds = task_info["thresholds"]
        status = task_info["status"]
        
        # 计算运行时间和心跳间隔
        elapsed_time = current_time - start_time
        heartbeat_gap = current_time - last_heartbeat
        
        # 检查心跳超时
        if heartbeat_gap > self.config.heartbeat_timeout and status == "running":
            await self._create_alert(
                task_id,
                operation_name,
                AlertLevel.WARNING,
                f"任务心跳超时 ({heartbeat_gap:.1f}s 无响应)",
                elapsed_time
            )
        
        # 检查运行时间超时
        if status == "running":
            if elapsed_time > thresholds["critical"]:
                await self._create_alert(
                    task_id,
                    operation_name,
                    AlertLevel.CRITICAL,
                    f"任务运行时间严重超时 ({elapsed_time:.1f}s)",
                    elapsed_time
                )
            elif elapsed_time > thresholds["error"]:
                await self._create_alert(
                    task_id,
                    operation_name,
                    AlertLevel.ERROR,
                    f"任务运行时间超时 ({elapsed_time:.1f}s)",
                    elapsed_time
                )
            elif elapsed_time > thresholds["warning"]:
                await self._create_alert(
                    task_id,
                    operation_name,
                    AlertLevel.WARNING,
                    f"任务运行时间较长 ({elapsed_time:.1f}s)",
                    elapsed_time
                )
    
    async def _create_alert(
        self,
        task_id: str,
        operation_name: str,
        level: AlertLevel,
        message: str,
        duration: float
    ):
        """创建告警"""
        # 检查告警冷却
        last_alert_key = f"{task_id}_{level.value}"
        current_time = time.time()
        
        if last_alert_key in self._last_alert_time:
            if current_time - self._last_alert_time[last_alert_key] < self.config.alert_cooldown:
                return  # 在冷却期内，跳过告警
        
        # 检查告警数量限制
        if len(self.alerts.get(task_id, [])) >= self.config.max_alerts_per_task:
            return  # 超过最大告警数，跳过
        
        # 创建告警
        alert = TimeoutAlert(
            task_id=task_id,
            operation_name=operation_name,
            alert_level=level,
            message=message,
            duration=duration,
            retry_count=self.monitored_tasks.get(task_id, {}).get("retry_count", 0)
        )
        
        # 记录告警
        if task_id not in self.alerts:
            self.alerts[task_id] = []
        self.alerts[task_id].append(alert)
        
        # 更新最后告警时间
        self._last_alert_time[last_alert_key] = current_time
        
        # 记录日志
        log_func = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }.get(level, logger.info)
        
        log_func(f"超时告警 [{level.value.upper()}] {task_id}: {message}")
        
        # 执行回调
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"告警回调执行失败: {str(e)}")
    
    def get_task_alerts(self, task_id: str) -> List[TimeoutAlert]:
        """获取任务的所有告警"""
        return self.alerts.get(task_id, [])
    
    def get_all_alerts(self) -> Dict[str, List[TimeoutAlert]]:
        """获取所有告警"""
        return self.alerts.copy()
    
    def get_recent_alerts(self, minutes: int = 30) -> List[TimeoutAlert]:
        """获取最近的告警"""
        cutoff_time = time.time() - (minutes * 60)
        recent_alerts = []
        
        for alerts_list in self.alerts.values():
            for alert in alerts_list:
                if alert.timestamp > cutoff_time:
                    recent_alerts.append(alert)
        
        # 按时间排序
        recent_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        return recent_alerts
    
    def get_monitor_stats(self) -> Dict:
        """获取监控统计信息"""
        current_time = time.time()
        
        active_tasks = 0
        total_alerts = 0
        alert_by_level = {level.value: 0 for level in AlertLevel}
        
        for task_id, task_info in self.monitored_tasks.items():
            if task_info["status"] == "running":
                active_tasks += 1
            
            task_alerts = self.alerts.get(task_id, [])
            total_alerts += len(task_alerts)
            
            for alert in task_alerts:
                alert_by_level[alert.alert_level.value] += 1
        
        return {
            "active_tasks": active_tasks,
            "total_monitored_tasks": len(self.monitored_tasks),
            "total_alerts": total_alerts,
            "alerts_by_level": alert_by_level,
            "monitor_uptime": current_time - getattr(self, '_start_time', current_time),
        }


# 全局超时监控器实例
timeout_monitor = TimeoutMonitor()

# 启动监控器
async def start_timeout_monitoring():
    """启动超时监控"""
    await timeout_monitor.start_monitoring()

# 添加默认告警回调
def default_alert_callback(alert: TimeoutAlert):
    """默认告警回调"""
    level_emoji = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨",
    }
    
    emoji = level_emoji.get(alert.alert_level, "❓")
    logger.info(
        f"{emoji} 超时告警: {alert.task_id} - {alert.message} "
        f"(持续: {alert.duration:.1f}s, 重试: {alert.retry_count})"
    )

timeout_monitor.add_alert_callback(default_alert_callback)