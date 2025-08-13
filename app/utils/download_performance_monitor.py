"""
下载性能监控器

实时跟踪和分析下载性能，提供优化建议
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_chapters: int = 0
    downloaded_chapters: int = 0
    failed_chapters: int = 0
    avg_download_time: float = 0.0
    download_speed: float = 0.0  # 章节/秒
    success_rate: float = 0.0
    current_concurrent: int = 0
    peak_concurrent: int = 0
    total_download_time: float = 0.0
    estimated_remaining_time: float = 0.0


class DownloadPerformanceMonitor:
    """下载性能监控器"""
    
    def __init__(self):
        self.start_time = None
        self.metrics = PerformanceMetrics()
        self.chapter_times = deque(maxlen=100)  # 最近100个章节的下载时间
        self.concurrent_counts = deque(maxlen=1000)  # 并发数历史
        self.lock = Lock()
        
        # 性能分析
        self.slow_chapters = []  # 慢速章节记录
        self.error_patterns = defaultdict(int)  # 错误模式统计
        
        # 实时监控
        self.current_downloads = {}  # 当前下载的章节
        self.performance_history = deque(maxlen=60)  # 1分钟的性能历史（每秒一个点）
        
        # 启动监控任务
        self._monitor_task = None
        self._start_monitoring()
    
    def _start_monitoring(self):
        """启动监控任务"""
        try:
            loop = asyncio.get_running_loop()
            self._monitor_task = loop.create_task(self._monitor_performance())
        except RuntimeError:
            # 没有运行中的事件循环
            pass
    
    async def _monitor_performance(self):
        """性能监控任务"""
        while True:
            try:
                await asyncio.sleep(1)  # 每秒收集一次数据
                self._collect_performance_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"性能监控任务出错: {str(e)}")
    
    def _collect_performance_data(self):
        """收集性能数据"""
        with self.lock:
            current_time = time.time()
            
            # 计算当前指标
            if self.start_time:
                elapsed = current_time - self.start_time
                self.metrics.total_download_time = elapsed
                
                if self.metrics.downloaded_chapters > 0:
                    self.metrics.download_speed = self.metrics.downloaded_chapters / elapsed
                
                # 估算剩余时间
                remaining_chapters = self.metrics.total_chapters - self.metrics.downloaded_chapters
                if self.metrics.download_speed > 0 and remaining_chapters > 0:
                    self.metrics.estimated_remaining_time = remaining_chapters / self.metrics.download_speed
            
            # 记录性能历史
            performance_point = {
                'timestamp': current_time,
                'downloaded': self.metrics.downloaded_chapters,
                'concurrent': self.metrics.current_concurrent,
                'speed': self.metrics.download_speed,
                'success_rate': self.metrics.success_rate
            }
            self.performance_history.append(performance_point)
    
    def start_download(self, total_chapters: int):
        """开始下载"""
        with self.lock:
            self.start_time = time.time()
            self.metrics.total_chapters = total_chapters
            logger.info(f"开始性能监控，总章节数: {total_chapters}")
    
    def chapter_started(self, chapter_title: str, chapter_url: str):
        """章节下载开始"""
        with self.lock:
            chapter_id = f"{chapter_title}_{id(chapter_url)}"
            self.current_downloads[chapter_id] = {
                'title': chapter_title,
                'url': chapter_url,
                'start_time': time.time()
            }
            
            self.metrics.current_concurrent = len(self.current_downloads)
            self.metrics.peak_concurrent = max(self.metrics.peak_concurrent, self.metrics.current_concurrent)
            self.concurrent_counts.append(self.metrics.current_concurrent)
    
    def chapter_completed(self, chapter_title: str, content_length: int, quality_score: float = 1.0):
        """章节下载完成"""
        with self.lock:
            chapter_id = f"{chapter_title}_{id(chapter_title)}"
            
            if chapter_id in self.current_downloads:
                download_info = self.current_downloads.pop(chapter_id)
                download_time = time.time() - download_info['start_time']
                
                self.chapter_times.append(download_time)
                self.metrics.downloaded_chapters += 1
                
                # 记录慢速章节
                if download_time > 10.0:  # 超过10秒的章节
                    self.slow_chapters.append({
                        'title': chapter_title,
                        'download_time': download_time,
                        'content_length': content_length,
                        'quality_score': quality_score
                    })
                
                # 更新平均下载时间
                if self.chapter_times:
                    self.metrics.avg_download_time = sum(self.chapter_times) / len(self.chapter_times)
                
                # 更新成功率
                total_processed = self.metrics.downloaded_chapters + self.metrics.failed_chapters
                if total_processed > 0:
                    self.metrics.success_rate = self.metrics.downloaded_chapters / total_processed
            
            self.metrics.current_concurrent = len(self.current_downloads)
    
    def chapter_failed(self, chapter_title: str, error_message: str):
        """章节下载失败"""
        with self.lock:
            chapter_id = f"{chapter_title}_{id(chapter_title)}"
            
            if chapter_id in self.current_downloads:
                self.current_downloads.pop(chapter_id)
            
            self.metrics.failed_chapters += 1
            
            # 记录错误模式
            error_type = self._classify_error(error_message)
            self.error_patterns[error_type] += 1
            
            # 更新成功率
            total_processed = self.metrics.downloaded_chapters + self.metrics.failed_chapters
            if total_processed > 0:
                self.metrics.success_rate = self.metrics.downloaded_chapters / total_processed
            
            self.metrics.current_concurrent = len(self.current_downloads)
    
    def _classify_error(self, error_message: str) -> str:
        """分类错误类型"""
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower:
            return 'connection'
        elif 'content' in error_lower or 'empty' in error_lower:
            return 'content'
        elif 'quality' in error_lower:
            return 'quality'
        else:
            return 'other'
    
    def get_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        with self.lock:
            return self.metrics
    
    def get_detailed_stats(self) -> Dict:
        """获取详细统计信息"""
        with self.lock:
            stats = {
                'metrics': {
                    'total_chapters': self.metrics.total_chapters,
                    'downloaded_chapters': self.metrics.downloaded_chapters,
                    'failed_chapters': self.metrics.failed_chapters,
                    'success_rate': f"{self.metrics.success_rate:.1%}",
                    'avg_download_time': f"{self.metrics.avg_download_time:.2f}s",
                    'download_speed': f"{self.metrics.download_speed:.2f} 章/秒",
                    'current_concurrent': self.metrics.current_concurrent,
                    'peak_concurrent': self.metrics.peak_concurrent,
                    'total_download_time': f"{self.metrics.total_download_time:.2f}s",
                    'estimated_remaining_time': f"{self.metrics.estimated_remaining_time:.2f}s"
                },
                'performance_analysis': {
                    'slow_chapters_count': len(self.slow_chapters),
                    'error_patterns': dict(self.error_patterns),
                    'avg_concurrent': sum(self.concurrent_counts) / len(self.concurrent_counts) if self.concurrent_counts else 0,
                },
                'current_downloads': list(self.current_downloads.keys()),
            }
            
            # 添加最慢的章节
            if self.slow_chapters:
                slowest = sorted(self.slow_chapters, key=lambda x: x['download_time'], reverse=True)[:5]
                stats['performance_analysis']['slowest_chapters'] = [
                    f"{ch['title']} ({ch['download_time']:.2f}s)" for ch in slowest
                ]
            
            return stats
    
    def get_optimization_suggestions(self) -> List[str]:
        """获取优化建议"""
        suggestions = []
        
        with self.lock:
            # 基于成功率的建议
            if self.metrics.success_rate < 0.8:
                suggestions.append("成功率较低，建议降低并发数或增加重试次数")
            
            # 基于平均下载时间的建议
            if self.metrics.avg_download_time > 5.0:
                suggestions.append("平均下载时间较长，建议检查网络连接或目标服务器响应")
            
            # 基于错误模式的建议
            if self.error_patterns.get('timeout', 0) > self.metrics.total_chapters * 0.1:
                suggestions.append("超时错误较多，建议增加超时时间")
            
            if self.error_patterns.get('connection', 0) > self.metrics.total_chapters * 0.1:
                suggestions.append("连接错误较多，建议检查网络稳定性")
            
            # 基于并发数的建议
            avg_concurrent = sum(self.concurrent_counts) / len(self.concurrent_counts) if self.concurrent_counts else 0
            if avg_concurrent < self.metrics.peak_concurrent * 0.5:
                suggestions.append("平均并发数较低，可能存在性能瓶颈")
            
            # 基于慢速章节的建议
            if len(self.slow_chapters) > self.metrics.total_chapters * 0.2:
                suggestions.append("慢速章节较多，建议优化内容解析或增加超时时间")
        
        return suggestions
    
    def stop_monitoring(self):
        """停止监控"""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()


# 全局性能监控器实例
performance_monitor = DownloadPerformanceMonitor()