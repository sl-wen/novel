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
        try:
            return {
                "task_id": str(self.task_id) if self.task_id else "",
                "status": self.status.value if self.status else "pending",
                "progress_percentage": round(float(self.progress_percentage), 2) if self.progress_percentage is not None else 0.0,
                "completed_chapters": int(self.completed_chapters) if self.completed_chapters is not None else 0,
                "total_chapters": int(self.total_chapters) if self.total_chapters is not None else 0,
                "failed_chapters": int(self.failed_chapters) if self.failed_chapters is not None else 0,
                "current_chapter": str(self.current_chapter) if self.current_chapter else "",
                "start_time": float(self.start_time) if self.start_time is not None else 0.0,
                "end_time": float(self.end_time) if self.end_time else None,
                "elapsed_time": round(float(self.elapsed_time), 2) if self.elapsed_time is not None else 0.0,
                "estimated_remaining_time": round(float(self.estimated_remaining_time), 2) if self.estimated_remaining_time else None,
                "average_speed": round(float(self.average_speed), 4) if self.average_speed is not None else 0.0,
                "error_message": str(self.error_message) if self.error_message else "",
                "file_path": str(self.file_path) if self.file_path else None,
            }
        except Exception as e:
            # 如果序列化失败，返回最小的安全数据
            logger.error(f"进度信息序列化失败: {str(e)}")
            return {
                "task_id": str(self.task_id) if self.task_id else "",
                "status": "error",
                "progress_percentage": 0.0,
                "completed_chapters": 0,
                "total_chapters": 0,
                "failed_chapters": 0,
                "current_chapter": "",
                "start_time": 0.0,
                "end_time": None,
                "elapsed_time": 0.0,
                "estimated_remaining_time": None,
                "average_speed": 0.0,
                "error_message": f"序列化失败: {str(e)}",
                "file_path": None,
            }


class ProgressTracker:
    """下载进度跟踪器"""
    
    def __init__(self):
        self._tasks: Dict[str, ProgressInfo] = {}
        self._lock = Lock()
        self._callbacks: Dict[str, List[Callable[[ProgressInfo], None]]] = {}
    
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
                progress.progress_percentage = 100.0
            
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


# 全局进度跟踪器实例
progress_tracker = ProgressTracker()