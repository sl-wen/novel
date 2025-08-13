"""
智能限流器

根据响应时间和成功率动态调整请求速率，避免过载目标服务器
"""

import asyncio
import logging
import time
from collections import deque
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class AdaptiveRateLimiter:
    """自适应限流器"""
    
    def __init__(self):
        self.host_stats = {}  # 每个主机的统计信息
        self.global_lock = asyncio.Lock()
        
    async def acquire(self, url: str) -> None:
        """获取请求许可"""
        host = self._get_host(url)
        
        async with self.global_lock:
            if host not in self.host_stats:
                self.host_stats[host] = HostStats()
            
            host_stats = self.host_stats[host]
            
            # 检查是否需要限流
            delay = host_stats.get_required_delay()
            if delay > 0:
                logger.debug(f"限流延迟 {delay:.2f}s for {host}")
                await asyncio.sleep(delay)
            
            host_stats.record_request_start()
    
    def record_success(self, url: str, response_time: float) -> None:
        """记录成功请求"""
        host = self._get_host(url)
        if host in self.host_stats:
            self.host_stats[host].record_success(response_time)
    
    def record_failure(self, url: str) -> None:
        """记录失败请求"""
        host = self._get_host(url)
        if host in self.host_stats:
            self.host_stats[host].record_failure()
    
    def _get_host(self, url: str) -> str:
        """提取主机名"""
        try:
            return urlparse(url).netloc
        except:
            return "unknown"
    
    def get_stats(self) -> Dict[str, dict]:
        """获取统计信息"""
        stats = {}
        for host, host_stats in self.host_stats.items():
            stats[host] = host_stats.get_stats()
        return stats


class HostStats:
    """单个主机的统计信息"""
    
    def __init__(self):
        self.request_times = deque(maxlen=100)  # 最近100次请求的响应时间
        self.success_count = 0
        self.failure_count = 0
        self.last_request_time = 0
        self.current_delay = 0.0  # 当前延迟
        self.min_delay = 0.05     # 最小延迟
        self.max_delay = 2.0      # 最大延迟
        
    def record_request_start(self):
        """记录请求开始"""
        self.last_request_time = time.time()
    
    def record_success(self, response_time: float):
        """记录成功请求"""
        self.request_times.append(response_time)
        self.success_count += 1
        self._adjust_delay(success=True, response_time=response_time)
    
    def record_failure(self):
        """记录失败请求"""
        self.failure_count += 1
        self._adjust_delay(success=False)
    
    def _adjust_delay(self, success: bool, response_time: float = 0):
        """动态调整延迟"""
        if success:
            # 成功请求，根据响应时间调整
            if response_time < 1.0:  # 响应快，可以减少延迟
                self.current_delay = max(self.min_delay, self.current_delay * 0.9)
            elif response_time > 3.0:  # 响应慢，增加延迟
                self.current_delay = min(self.max_delay, self.current_delay * 1.2)
        else:
            # 失败请求，增加延迟
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
    
    def get_required_delay(self) -> float:
        """获取需要的延迟时间"""
        # 基于成功率调整
        total_requests = self.success_count + self.failure_count
        if total_requests > 10:
            success_rate = self.success_count / total_requests
            if success_rate < 0.8:  # 成功率低于80%，增加延迟
                return min(self.max_delay, self.current_delay * 1.5)
        
        return self.current_delay
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total_requests = self.success_count + self.failure_count
        avg_response_time = (
            sum(self.request_times) / len(self.request_times)
            if self.request_times else 0
        )
        
        return {
            "total_requests": total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_count / max(total_requests, 1),
            "avg_response_time": avg_response_time,
            "current_delay": self.current_delay,
        }


# 全局限流器实例
rate_limiter = AdaptiveRateLimiter()