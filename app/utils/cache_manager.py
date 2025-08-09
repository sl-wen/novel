import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
import logging
import pickle

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器 - 提供内存和磁盘缓存功能"""
    
    def __init__(self, cache_dir: str = "cache", max_memory_items: int = 1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 内存缓存
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.max_memory_items = max_memory_items
        
        # 缓存配置
        self.default_ttl = 3600  # 1小时
        self.search_cache_ttl = 1800  # 搜索结果缓存30分钟
        self.toc_cache_ttl = 7200  # 目录缓存2小时
        self.chapter_cache_ttl = 86400  # 章节内容缓存24小时
        
        # 初始化缓存目录结构
        self._init_cache_dirs()
    
    def _init_cache_dirs(self):
        """初始化缓存目录结构"""
        (self.cache_dir / "search").mkdir(exist_ok=True)
        (self.cache_dir / "toc").mkdir(exist_ok=True)
        (self.cache_dir / "chapters").mkdir(exist_ok=True)
        (self.cache_dir / "books").mkdir(exist_ok=True)
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 将参数转换为字符串并排序
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        
        # 添加关键字参数
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        
        # 生成MD5哈希
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_expired(self, timestamp: float, ttl: int) -> bool:
        """检查缓存是否过期"""
        return time.time() - timestamp > ttl
    
    def _cleanup_memory_cache(self):
        """清理内存缓存，保持在限制范围内"""
        if len(self.memory_cache) <= self.max_memory_items:
            return
        
        # 按时间戳排序，删除最旧的项目
        sorted_items = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1]['timestamp']
        )
        
        # 删除最旧的项目直到达到限制
        items_to_remove = len(self.memory_cache) - self.max_memory_items + 100
        for i in range(min(items_to_remove, len(sorted_items))):
            key = sorted_items[i][0]
            del self.memory_cache[key]
        
        logger.info(f"清理内存缓存，删除了 {items_to_remove} 个项目")
    
    async def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """获取缓存项"""
        ttl = ttl or self.default_ttl
        
        # 1. 检查内存缓存
        if key in self.memory_cache:
            item = self.memory_cache[key]
            if not self._is_expired(item['timestamp'], ttl):
                logger.debug(f"内存缓存命中: {key}")
                return item['data']
            else:
                # 过期，删除
                del self.memory_cache[key]
        
        # 2. 检查磁盘缓存
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    item = pickle.load(f)
                
                if not self._is_expired(item['timestamp'], ttl):
                    # 加载到内存缓存
                    self.memory_cache[key] = item
                    self._cleanup_memory_cache()
                    
                    logger.debug(f"磁盘缓存命中: {key}")
                    return item['data']
                else:
                    # 过期，删除文件
                    cache_file.unlink()
            except Exception as e:
                logger.warning(f"读取磁盘缓存失败 {key}: {str(e)}")
                if cache_file.exists():
                    cache_file.unlink()
        
        return None
    
    async def set(self, key: str, data: Any, ttl: Optional[int] = None, 
                  disk_cache: bool = True) -> bool:
        """设置缓存项"""
        try:
            ttl = ttl or self.default_ttl
            timestamp = time.time()
            
            item = {
                'data': data,
                'timestamp': timestamp,
                'ttl': ttl
            }
            
            # 设置内存缓存
            self.memory_cache[key] = item
            self._cleanup_memory_cache()
            
            # 设置磁盘缓存
            if disk_cache:
                cache_file = self.cache_dir / f"{key}.cache"
                with open(cache_file, 'wb') as f:
                    pickle.dump(item, f)
            
            logger.debug(f"设置缓存: {key}")
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存项"""
        try:
            # 删除内存缓存
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            # 删除磁盘缓存
            cache_file = self.cache_dir / f"{key}.cache"
            if cache_file.exists():
                cache_file.unlink()
            
            logger.debug(f"删除缓存: {key}")
            return True
            
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {str(e)}")
            return False
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """清理缓存"""
        cleared_count = 0
        
        try:
            # 清理内存缓存
            if pattern:
                keys_to_remove = [k for k in self.memory_cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self.memory_cache[key]
                    cleared_count += 1
            else:
                cleared_count += len(self.memory_cache)
                self.memory_cache.clear()
            
            # 清理磁盘缓存
            for cache_file in self.cache_dir.glob("*.cache"):
                if pattern is None or pattern in cache_file.stem:
                    cache_file.unlink()
                    cleared_count += 1
            
            logger.info(f"清理缓存完成，删除了 {cleared_count} 个项目")
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理缓存失败: {str(e)}")
            return cleared_count
    
    async def cleanup_expired(self) -> int:
        """清理过期缓存"""
        cleared_count = 0
        current_time = time.time()
        
        try:
            # 清理内存缓存中的过期项
            expired_keys = []
            for key, item in self.memory_cache.items():
                if self._is_expired(item['timestamp'], item.get('ttl', self.default_ttl)):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
                cleared_count += 1
            
            # 清理磁盘缓存中的过期项
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        item = pickle.load(f)
                    
                    if self._is_expired(item['timestamp'], item.get('ttl', self.default_ttl)):
                        cache_file.unlink()
                        cleared_count += 1
                        
                except Exception:
                    # 无法读取的文件也删除
                    cache_file.unlink()
                    cleared_count += 1
            
            if cleared_count > 0:
                logger.info(f"清理过期缓存完成，删除了 {cleared_count} 个项目")
            
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {str(e)}")
            return cleared_count
    
    # 便捷方法
    
    async def cache_search_results(self, keyword: str, source_ids: List[int], 
                                 results: List[Dict]) -> bool:
        """缓存搜索结果"""
        key = self._generate_cache_key("search", keyword, *sorted(source_ids))
        return await self.set(key, results, ttl=self.search_cache_ttl)
    
    async def get_search_results(self, cache_key: str) -> Optional[List[Any]]:
        """获取缓存的搜索结果（通过缓存键）"""
        return await self.get(cache_key, ttl=self.search_cache_ttl)
    
    async def set_search_results(self, cache_key: str, results: List[Any]) -> bool:
        """设置缓存的搜索结果"""
        return await self.set(cache_key, results, ttl=self.search_cache_ttl)
    
    async def cache_toc(self, url: str, source_id: int, toc: List[Dict]) -> bool:
        """缓存目录信息"""
        key = self._generate_cache_key("toc", url, source_id)
        return await self.set(key, toc, ttl=self.toc_cache_ttl)
    
    async def get_toc(self, cache_key: str) -> Optional[List[Any]]:
        """获取缓存的目录信息（通过缓存键）"""
        return await self.get(cache_key, ttl=self.toc_cache_ttl)
    
    async def set_toc(self, cache_key: str, toc: List[Any]) -> bool:
        """设置缓存的目录信息"""
        return await self.set(cache_key, toc, ttl=self.toc_cache_ttl)
    
    async def cache_chapter(self, chapter_url: str, source_id: int, 
                          chapter_data: Dict) -> bool:
        """缓存章节内容"""
        key = self._generate_cache_key("chapter", chapter_url, source_id)
        return await self.set(key, chapter_data, ttl=self.chapter_cache_ttl)
    
    async def get_chapter(self, chapter_url: str, source_id: int) -> Optional[Dict]:
        """获取缓存的章节内容"""
        key = self._generate_cache_key("chapter", chapter_url, source_id)
        return await self.get(key, ttl=self.chapter_cache_ttl)
    
    async def cache_book_info(self, url: str, source_id: int, book_data: Dict) -> bool:
        """缓存书籍信息"""
        key = self._generate_cache_key("book", url, source_id)
        return await self.set(key, book_data, ttl=self.toc_cache_ttl)
    
    async def get_book_info(self, url: str, source_id: int) -> Optional[Dict]:
        """获取缓存的书籍信息"""
        key = self._generate_cache_key("book", url, source_id)
        return await self.get(key, ttl=self.toc_cache_ttl)
    
    async def get_book_detail(self, cache_key: str) -> Optional[Any]:
        """获取缓存的书籍详情（通过缓存键）"""
        return await self.get(cache_key, ttl=self.toc_cache_ttl)
    
    async def set_book_detail(self, cache_key: str, book: Any) -> bool:
        """设置缓存的书籍详情"""
        return await self.set(cache_key, book, ttl=self.toc_cache_ttl)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        disk_cache_count = len(list(self.cache_dir.glob("*.cache")))
        
        # 计算缓存大小
        cache_size = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_size += cache_file.stat().st_size
        
        return {
            "memory_cache_items": len(self.memory_cache),
            "disk_cache_items": disk_cache_count,
            "cache_size_mb": round(cache_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }


# 全局缓存管理器实例
cache_manager = CacheManager()