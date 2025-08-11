import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, List, Callable
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressInfo:
    """进度信息"""
    task_id: str
    status: TaskStatus
    progress_percentage: float = 0.0
    completed_chapters: int = 0
    total_chapters: int = 0
    failed_chapters: int = 0
    current_chapter: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    error_message: str = ""
    file_path: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)
    timeout_warnings: int = 0
    polling_interval: float = 1.0
    
    @property
    def elapsed_time(self) -> float:
        """已用时间（秒）"""
        end = self.end_time or time.time()
        return max(0, end - self.start_time)
    
    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """预估剩余时间（秒）"""
        if self.progress_percentage <= 0:
            return None
        
        elapsed = self.elapsed_time
        if elapsed <= 0:
            return None
        
        remaining_percentage = 100 - self.progress_percentage
        if remaining_percentage <= 0:
            return 0
        
        return (elapsed / self.progress_percentage) * remaining_percentage
    
    @property
    def average_speed(self) -> float:
        """平均速度（章节/秒）"""
        elapsed = self.elapsed_time
        if elapsed <= 0:
            return 0
        return self.completed_chapters / elapsed
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress_percentage": round(self.progress_percentage, 2),
            "completed_chapters": self.completed_chapters,
            "total_chapters": self.total_chapters,
            "failed_chapters": self.failed_chapters,
            "current_chapter": self.current_chapter,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_time": round(self.elapsed_time, 2),
            "estimated_remaining_time": round(self.estimated_remaining_time, 2) if self.estimated_remaining_time else None,
            "average_speed": round(self.average_speed, 4),
            "error_message": self.error_message,
            "file_path": self.file_path,
        }


class ProgressTracker:
    """下载进度跟踪器"""
    
    def __init__(self):
        self._tasks: Dict[str, ProgressInfo] = {}
        self._lock = Lock()
        self._callbacks: Dict[str, List[Callable[[ProgressInfo], None]]] = {}
        self._timeout_monitor_task: Optional[asyncio.Task] = None
        self._start_timeout_monitor()
    
    def create_task(self, total_chapters: int = 0, task_id: Optional[str] = None) -> str:
        """
        创建新的下载任务
        
        Args:
            total_chapters: 总章节数
            task_id: 任务ID，如果不提供则自动生成
            
        Returns:
            任务ID
        """
        if not task_id:
            task_id = str(uuid.uuid4())
        
        with self._lock:
            progress = ProgressInfo(
                task_id=task_id,
                status=TaskStatus.PENDING,
                total_chapters=total_chapters
            )
            self._tasks[task_id] = progress
            self._callbacks[task_id] = []
        
        logger.info(f"创建下载任务: {task_id}, 总章节数: {total_chapters}")
        return task_id
    
    def start_task(self, task_id: str):
        """开始任务"""
        with self._lock:
            if task_id in self._tasks:
                # 防止重新启动已完成的任务
                current_status = self._tasks[task_id].status
                if current_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    logger.warning(f"尝试启动已完成的任务: {task_id}, 当前状态: {current_status.value}")
                    return
                
                self._tasks[task_id].status = TaskStatus.RUNNING
                self._tasks[task_id].start_time = time.time()
                self._notify_callbacks(task_id)
                logger.info(f"开始下载任务: {task_id}")
    
    def update_progress(self, task_id: str, completed_chapters: int, 
                       current_chapter: str = "", failed_chapters: int = 0):
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            completed_chapters: 已完成章节数
            current_chapter: 当前章节名称
            failed_chapters: 失败章节数
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: {task_id}")
                return
            
            progress = self._tasks[task_id]
            
            # 防止更新已完成的任务进度
            if progress.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                logger.warning(f"尝试更新已完成任务的进度: {task_id}, 状态: {progress.status.value}")
                return
            
            progress.completed_chapters = completed_chapters
            progress.failed_chapters = failed_chapters
            progress.current_chapter = current_chapter
            
            if progress.total_chapters > 0:
                progress.progress_percentage = (completed_chapters / progress.total_chapters) * 100
            
            self._notify_callbacks(task_id)
    
    def set_file_path(self, task_id: str, file_path: str):
        """设置任务生成的文件路径"""
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: {task_id}")
                return
            self._tasks[task_id].file_path = file_path
            self._notify_callbacks(task_id)
    
    def update_total_chapters(self, task_id: str, total_chapters: int):
        """
        更新任务的总章节数
        
        Args:
            task_id: 任务ID
            total_chapters: 总章节数
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"更新总章节数：任务不存在: {task_id}")
                return
            
            progress = self._tasks[task_id]
            old_total = progress.total_chapters
            progress.total_chapters = total_chapters
            
            # 重新计算进度百分比
            if total_chapters > 0:
                progress.progress_percentage = (progress.completed_chapters / total_chapters) * 100
            
            logger.info(f"更新任务总章节数: {task_id}, {old_total} -> {total_chapters}")
            self._notify_callbacks(task_id)
    
    def complete_task(self, task_id: str, success: bool = True, error_message: str = ""):
        """
        完成任务
        
        Args:
            task_id: 任务ID
            success: 是否成功
            error_message: 错误消息（如果失败）
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: {task_id}")
                return
            
            progress = self._tasks[task_id]
            progress.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            progress.end_time = time.time()
            progress.error_message = error_message
            
            if success:
                # 确保成功的任务进度始终为100%，无论total_chapters是否为0
                progress.progress_percentage = 100.0
                logger.info(f"任务完成: {task_id}, 最终进度: {progress.progress_percentage}%")
            else:
                logger.error(f"任务失败: {task_id}, 错误: {error_message}")
            
            self._notify_callbacks(task_id)
            logger.info(f"任务{'完成' if success else '失败'}: {task_id}")
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.CANCELLED
                self._tasks[task_id].end_time = time.time()
                self._notify_callbacks(task_id)
                logger.info(f"取消下载任务: {task_id}")
    
    def pause_task(self, task_id: str):
        """暂停任务"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.PAUSED
                self._notify_callbacks(task_id)
                logger.info(f"暂停下载任务: {task_id}")
    
    def resume_task(self, task_id: str):
        """恢复任务"""
        with self._lock:
            if task_id in self._tasks:
                # 防止恢复已完成的任务
                current_status = self._tasks[task_id].status
                if current_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    logger.warning(f"尝试恢复已完成的任务: {task_id}, 当前状态: {current_status.value}")
                    return
                
                self._tasks[task_id].status = TaskStatus.RUNNING
                self._notify_callbacks(task_id)
                logger.info(f"恢复下载任务: {task_id}")
    
    def get_progress(self, task_id: str) -> Optional[ProgressInfo]:
        """获取任务进度"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, ProgressInfo]:
        """获取所有任务"""
        with self._lock:
            return self._tasks.copy()
    
    def remove_task(self, task_id: str):
        """移除任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                if task_id in self._callbacks:
                    del self._callbacks[task_id]
                logger.info(f"移除下载任务: {task_id}")
    
    def add_callback(self, task_id: str, callback: Callable[[ProgressInfo], None]):
        """
        添加进度回调函数
        
        Args:
            task_id: 任务ID
            callback: 回调函数，接收ProgressInfo参数
        """
        with self._lock:
            if task_id not in self._callbacks:
                self._callbacks[task_id] = []
            self._callbacks[task_id].append(callback)
    
    def remove_callback(self, task_id: str, callback: Callable[[ProgressInfo], None]):
        """移除进度回调函数"""
        with self._lock:
            if task_id in self._callbacks:
                try:
                    self._callbacks[task_id].remove(callback)
                except ValueError:
                    pass
    
    def _notify_callbacks(self, task_id: str):
        """通知回调函数"""
        if task_id in self._callbacks and task_id in self._tasks:
            progress = self._tasks[task_id]
            for callback in self._callbacks[task_id]:
                try:
                    callback(progress)
                except Exception as e:
                    logger.error(f"进度回调执行失败: {str(e)}")
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        with self._lock:
            tasks_to_remove = []
            for task_id, progress in self._tasks.items():
                if progress.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if current_time - progress.start_time > max_age_seconds:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                self.remove_task(task_id)
            
            if tasks_to_remove:
                logger.info(f"清理了 {len(tasks_to_remove)} 个旧任务")
    
    def _start_timeout_monitor(self):
        """启动超时监控"""
        try:
            loop = asyncio.get_running_loop()
            self._timeout_monitor_task = loop.create_task(self._timeout_monitor_loop())
        except RuntimeError:
            # 没有运行的事件循环，稍后启动
            pass
    
    async def _timeout_monitor_loop(self):
        """超时监控循环"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                await self._check_timeouts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"超时监控出错: {str(e)}")
    
    async def _check_timeouts(self):
        """检查超时任务"""
        current_time = time.time()
        timeout_threshold = 300  # 5分钟无心跳视为超时
        
        with self._lock:
            for task_id, progress in self._tasks.items():
                if progress.status == TaskStatus.RUNNING:
                    # 检查心跳超时
                    if current_time - progress.last_heartbeat > timeout_threshold:
                        progress.timeout_warnings += 1
                        logger.warning(
                            f"任务 {task_id} 可能超时 (无心跳 {current_time - progress.last_heartbeat:.1f}s)，"
                            f"警告次数: {progress.timeout_warnings}"
                        )
                        
                        # 如果超时警告过多，标记为失败
                        if progress.timeout_warnings >= 3:
                            progress.status = TaskStatus.FAILED
                            progress.error_message = "任务超时：长时间无响应"
                            progress.end_time = current_time
                            logger.error(f"任务 {task_id} 因超时被标记为失败")
                            self._notify_callbacks(task_id)
    
    def heartbeat(self, task_id: str):
        """更新任务心跳"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].last_heartbeat = time.time()
                # 重置超时警告计数
                if self._tasks[task_id].timeout_warnings > 0:
                    self._tasks[task_id].timeout_warnings = 0
                    logger.debug(f"任务 {task_id} 心跳恢复，重置超时警告")
    
    def update_polling_interval(self, task_id: str, interval: float):
        """更新轮询间隔"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].polling_interval = interval

    def validate_task_status(self, task_id: str) -> bool:
        """
        验证任务状态的一致性
        
        Args:
            task_id: 任务ID
            
        Returns:
            True if status is consistent, False otherwise
        """
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            progress = self._tasks[task_id]
            
            # 检查已完成任务的一致性
            if progress.status == TaskStatus.COMPLETED:
                if progress.progress_percentage != 100.0:
                    logger.warning(f"已完成任务进度不为100%: {task_id}, 进度: {progress.progress_percentage}%")
                    progress.progress_percentage = 100.0
                    return False
                
                if not progress.end_time:
                    logger.warning(f"已完成任务缺少结束时间: {task_id}")
                    progress.end_time = time.time()
                    return False
            
            return True

    def force_complete_task(self, task_id: str, file_path: str = None):
        """
        强制完成任务（用于修复状态异常的任务）
        
        Args:
            task_id: 任务ID
            file_path: 文件路径（可选）
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"强制完成：任务不存在: {task_id}")
                return False
            
            progress = self._tasks[task_id]
            
            # 如果任务已经是完成状态，不需要修改
            if progress.status == TaskStatus.COMPLETED:
                logger.info(f"任务已经是完成状态: {task_id}")
                return True
            
            # 强制设置为完成状态
            progress.status = TaskStatus.COMPLETED
            progress.end_time = time.time()
            progress.progress_percentage = 100.0
            
            if file_path:
                progress.file_path = file_path
            
            self._notify_callbacks(task_id)
            logger.info(f"强制完成任务: {task_id}")
            return True


# 全局进度跟踪器实例
progress_tracker = ProgressTracker()