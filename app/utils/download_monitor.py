import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """下载进度信息"""
    total_chapters: int = 0
    completed_chapters: int = 0
    failed_chapters: int = 0
    skipped_chapters: int = 0
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    
    # 质量统计
    high_quality_chapters: int = 0
    low_quality_chapters: int = 0
    
    # 错误统计
    error_details: List[str] = field(default_factory=list)
    
    # 性能统计
    total_bytes: int = 0
    average_speed: float = 0.0  # bytes per second

    @property
    def progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return (self.completed_chapters + self.failed_chapters + self.skipped_chapters) / self.total_chapters * 100

    @property
    def success_rate(self) -> float:
        """获取成功率"""
        total_processed = self.completed_chapters + self.failed_chapters + self.skipped_chapters
        if total_processed == 0:
            return 0.0
        return self.completed_chapters / total_processed * 100

    @property
    def elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        return time.time() - self.start_time

    @property
    def estimated_remaining_time(self) -> float:
        """估算剩余时间（秒）"""
        if self.progress_percentage == 0:
            return 0.0
        
        elapsed = self.elapsed_time
        progress = self.progress_percentage / 100
        
        if progress == 0:
            return 0.0
            
        total_estimated_time = elapsed / progress
        return total_estimated_time - elapsed

    @property
    def average_chapter_time(self) -> float:
        """平均每章耗时（秒）"""
        processed = self.completed_chapters + self.failed_chapters + self.skipped_chapters
        if processed == 0:
            return 0.0
        return self.elapsed_time / processed

    def update_speed(self, bytes_downloaded: int):
        """更新下载速度"""
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        if time_diff > 0:
            self.average_speed = bytes_downloaded / time_diff
            self.last_update_time = current_time

    def add_error(self, error_msg: str):
        """添加错误信息"""
        self.error_details.append(f"{time.strftime('%H:%M:%S')}: {error_msg}")
        # 只保留最近的20个错误
        if len(self.error_details) > 20:
            self.error_details = self.error_details[-20:]

    def get_summary(self) -> str:
        """获取下载摘要"""
        return (
            f"下载进度: {self.progress_percentage:.1f}% "
            f"({self.completed_chapters + self.failed_chapters + self.skipped_chapters}/{self.total_chapters}) "
            f"成功率: {self.success_rate:.1f}% "
            f"耗时: {self.elapsed_time:.1f}s "
            f"剩余: {self.estimated_remaining_time:.1f}s"
        )


class DownloadMonitor:
    """下载监控器"""

    def __init__(self):
        """初始化下载监控器"""
        self.progress = DownloadProgress()
        self.chapter_stats: Dict[str, Dict] = {}
        self.start_time = time.time()

    def start_download(self, total_chapters: int):
        """开始下载"""
        self.progress = DownloadProgress(total_chapters=total_chapters)
        self.chapter_stats.clear()
        logger.info(f"开始下载，共 {total_chapters} 章")

    def chapter_started(self, chapter_title: str, chapter_url: str):
        """章节开始下载"""
        self.chapter_stats[chapter_title] = {
            "url": chapter_url,
            "start_time": time.time(),
            "status": "downloading"
        }

    def chapter_completed(self, chapter_title: str, content_length: int, quality_score: float = 0.0):
        """章节下载完成"""
        if chapter_title in self.chapter_stats:
            self.chapter_stats[chapter_title].update({
                "end_time": time.time(),
                "status": "completed",
                "content_length": content_length,
                "quality_score": quality_score
            })
        
        self.progress.completed_chapters += 1
        self.progress.total_bytes += content_length
        
        if quality_score >= 0.8:
            self.progress.high_quality_chapters += 1
        else:
            self.progress.low_quality_chapters += 1
        
        self._log_progress()

    def chapter_failed(self, chapter_title: str, error_msg: str):
        """章节下载失败"""
        if chapter_title in self.chapter_stats:
            self.chapter_stats[chapter_title].update({
                "end_time": time.time(),
                "status": "failed",
                "error": error_msg
            })
        
        self.progress.failed_chapters += 1
        self.progress.add_error(f"章节失败: {chapter_title} - {error_msg}")
        self._log_progress()

    def chapter_skipped(self, chapter_title: str, reason: str):
        """章节被跳过"""
        if chapter_title in self.chapter_stats:
            self.chapter_stats[chapter_title].update({
                "end_time": time.time(),
                "status": "skipped",
                "reason": reason
            })
        
        self.progress.skipped_chapters += 1
        self._log_progress()

    def _log_progress(self):
        """记录进度"""
        summary = self.progress.get_summary()
        logger.info(summary)

    def get_detailed_stats(self) -> Dict:
        """获取详细统计信息"""
        completed_chapters = [
            title for title, stats in self.chapter_stats.items()
            if stats.get("status") == "completed"
        ]
        
        failed_chapters = [
            title for title, stats in self.chapter_stats.items()
            if stats.get("status") == "failed"
        ]
        
        skipped_chapters = [
            title for title, stats in self.chapter_stats.items()
            if stats.get("status") == "skipped"
        ]
        
        # 计算平均质量评分
        quality_scores = [
            stats.get("quality_score", 0)
            for stats in self.chapter_stats.values()
            if stats.get("status") == "completed"
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            "progress": {
                "total_chapters": self.progress.total_chapters,
                "completed_chapters": self.progress.completed_chapters,
                "failed_chapters": self.progress.failed_chapters,
                "skipped_chapters": self.progress.skipped_chapters,
                "progress_percentage": self.progress.progress_percentage,
                "success_rate": self.progress.success_rate,
                "elapsed_time": self.progress.elapsed_time,
                "estimated_remaining_time": self.progress.estimated_remaining_time,
                "average_chapter_time": self.progress.average_chapter_time,
            },
            "quality": {
                "high_quality_chapters": self.progress.high_quality_chapters,
                "low_quality_chapters": self.progress.low_quality_chapters,
                "average_quality_score": avg_quality,
            },
            "performance": {
                "total_bytes": self.progress.total_bytes,
                "average_speed": self.progress.average_speed,
            },
            "errors": self.progress.error_details,
            "completed_chapters": completed_chapters,
            "failed_chapters": failed_chapters,
            "skipped_chapters": skipped_chapters,
        }

    def get_final_report(self) -> str:
        """获取最终报告"""
        stats = self.get_detailed_stats()
        
        report = [
            "=" * 60,
            "下载完成报告",
            "=" * 60,
            f"总章节数: {stats['progress']['total_chapters']}",
            f"成功章节: {stats['progress']['completed_chapters']}",
            f"失败章节: {stats['progress']['failed_chapters']}",
            f"跳过章节: {stats['progress']['skipped_chapters']}",
            f"成功率: {stats['progress']['success_rate']:.1f}%",
            f"总耗时: {stats['progress']['elapsed_time']:.1f}秒",
            f"平均每章耗时: {stats['progress']['average_chapter_time']:.1f}秒",
            f"高质量章节: {stats['quality']['high_quality_chapters']}",
            f"低质量章节: {stats['quality']['low_quality_chapters']}",
            f"平均质量评分: {stats['quality']['average_quality_score']:.2f}",
            f"总下载字节: {stats['performance']['total_bytes']:,}",
            f"平均速度: {stats['performance']['average_speed']:.1f} B/s",
        ]
        
        if stats['errors']:
            report.extend([
                "",
                "错误详情:",
                "-" * 20,
            ])
            for error in stats['errors'][-10:]:  # 只显示最近10个错误
                report.append(f"  {error}")
        
        return "\n".join(report)