import asyncio
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.core.source import Source
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.models.search import SearchResult
from app.parsers.book_parser import BookParser
from app.parsers.chapter_parser import ChapterParser
from app.parsers.search_parser import SearchParser
from app.parsers.toc_parser import TocParser
from app.utils.cache_manager import CacheManager
from app.utils.content_validator import ChapterValidator
from app.utils.download_monitor import DownloadMonitor
from app.utils.enhanced_http_client import EnhancedHttpClient
from app.utils.file import FileUtils

logger = logging.getLogger(__name__)


class NovelService:
    """小说服务类，提供高性能的搜索、获取详情、获取目录和下载功能"""

    def __init__(self):
        """初始化服务"""
        self.sources = {}
        self._load_sources()
        self.monitor = DownloadMonitor()
        self.chapter_validator = ChapterValidator()
        self.cache_manager = CacheManager()
        self.http_client = EnhancedHttpClient()

        # 性能优化配置
        self.search_timeout = 15  # 搜索超时时间（秒）
        self.max_concurrent_sources = 8  # 最大并发书源数
        self.max_concurrent_chapters = 10  # 最大并发章节下载数

        # 连接池和会话管理
        self.session_pool = {}
        self.session_lock = threading.Lock()

        # 验证书源可用性（仅在有事件循环时启动）
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._validate_sources_async())
        except RuntimeError:
            # 无运行中的事件循环，稍后由应用启动事件触发
            pass

    def _load_sources(self):
        """加载书源配置"""
        rules_path = Path(settings.RULES_PATH)
        if not rules_path.exists():
            logger.warning(f"书源规则目录不存在: {rules_path}")
            return

        for rule_file in rules_path.glob("*.json"):
            try:
                with open(rule_file, "r", encoding="utf-8") as f:
                    rule_data = json.load(f)

                source_id = rule_data.get("id")
                if source_id:
                    self.sources[source_id] = Source(source_id, rule_data)
                    logger.info(
                        f"加载书源: {rule_data.get('name', f'Source-{source_id}')} (ID: {source_id})"
                    )
            except Exception as e:
                logger.error(f"加载书源规则失败 {rule_file}: {str(e)}")

        logger.info(f"总共加载了 {len(self.sources)} 个书源")

    async def _validate_sources_async(self):
        """异步验证书源可用性"""
        try:
            await self._validate_sources()
        except Exception as e:
            logger.error(f"验证书源可用性时出错: {str(e)}")

    async def _validate_sources(self):
        """验证所有书源的可用性（优化版）"""
        import aiohttp

        logger.info("开始验证书源可用性...")

        async def check_source(source_id, source):
            """检查单个书源的可用性"""
            try:
                url = source.rule.get("url", "")
                if not url:
                    return source_id, False, "未配置URL"

                # 使用优化的HTTP客户端
                timeout = aiohttp.ClientTimeout(total=5, connect=3)  # 更短的超时时间
                connector = aiohttp.TCPConnector(ssl=False, limit=2)

                async with aiohttp.ClientSession(
                    timeout=timeout, connector=connector
                ) as session:
                    async with session.head(url) as response:
                        if response.status < 400:
                            return source_id, True, f"状态码: {response.status}"
                        else:
                            return source_id, False, f"状态码: {response.status}"
            except Exception as e:
                return source_id, False, str(e)

        # 限制并发数量以避免过多连接
        semaphore = asyncio.Semaphore(self.max_concurrent_sources)

        async def check_with_semaphore(source_id, source):
            async with semaphore:
                return await check_source(source_id, source)

        # 并发检查所有书源
        tasks = [
            check_with_semaphore(sid, source) for sid, source in self.sources.items()
        ]
        results = await asyncio.gather(*tasks)

        available_sources = []
        unavailable_sources = []

        for result in results:

            source_id, is_available, message = result
            source_name = self.sources[source_id].rule.get("name", f"书源{source_id}")

            if is_available:
                available_sources.append(source_id)
                logger.info(f"{source_name} (ID: {source_id}) 可用 - {message}")
            else:
                unavailable_sources.append(source_id)
                logger.warning(f"{source_name} (ID: {source_id}) 不可用 - {message}")

        logger.info(
            f"书源验证完成: {len(available_sources)} 个可用, {len(unavailable_sources)} 个不可用"
        )

    async def search(
        self, keyword: str, max_results: int = 30
    ) -> List[SearchResult]:
        """搜索小说

        优化点:
        1. 使用缓存减少重复搜索
        2. 并发限制和超时控制
        3. 智能书源选择
        4. 结果去重和排序优化

        Args:
            keyword: 搜索关键词（书名或作者名）
            max_results: 最大返回结果数
        Returns:
            搜索结果列表
        """
        logger.info(f"开始优化搜索: {keyword}, max_results={max_results}")
        start_time = time.time()

        # 1. 检查缓存
        cache_key = self.cache_manager._generate_cache_key(
            "search", keyword, max_results
        )
        cached_results = await self.cache_manager.get_search_results(cache_key)
        if cached_results:
            logger.info(f"搜索缓存命中: {keyword}")
            return cached_results

        # 2. 获取可搜索的书源（优先选择快速和可靠的书源）
        searchable_sources = self._get_prioritized_search_sources()
        if not searchable_sources:
            logger.warning("没有找到可用的搜索书源规则")
            return []

        # 3. 限制并发搜索数量
        search_semaphore = asyncio.Semaphore(self.max_concurrent_sources)

        async def search_single_source_optimized(source: Source, keyword: str):
            """优化版单书源搜索"""
            async with search_semaphore:
                try:
                    # 设置超时
                    search_task = self._search_source_with_timeout(source, keyword)
                    results = await asyncio.wait_for(
                        search_task, timeout=self.search_timeout
                    )

                    logger.info(
                        f"书源 {source.rule.get('name', source.id)} "
                        f"搜索成功，找到 {len(results)} 条结果"
                    )
                    return results
                except asyncio.TimeoutError:
                    logger.warning(
                        f"书源 {source.rule.get('name', source.id)} 搜索超时"
                    )
                    return []
                except Exception as e:
                    logger.error(
                        f"书源 {source.rule.get('name', source.id)} 搜索失败: {str(e)}"
                    )
                    return []

        # 4. 并发搜索所有书源
        tasks = [
            search_single_source_optimized(source, keyword)
            for source in searchable_sources
        ]
        results_from_sources = await asyncio.gather(*tasks, return_exceptions=True)

        # 5. 处理结果（仅保留成功返回的列表）
        all_results: List[SearchResult] = []
        source_stats: Dict[str, int] = {}

        for i, source_result in enumerate(results_from_sources):
            if isinstance(source_result, Exception):
                continue
            if not isinstance(source_result, list):
                continue
            source_name = searchable_sources[i].rule.get(
                "name", f"Source-{searchable_sources[i].id}"
            )
            try:
                source_stats[source_name] = len(source_result)
            except Exception:
                source_stats[source_name] = 0
            all_results.extend(source_result)

        # 6. 优化版过滤和排序
        filtered_results = self._filter_and_sort_results_optimized(
            all_results, keyword, max_results=max_results
        )

        capped_results: List[SearchResult] = []
        
        # 按书源分组处理结果
        source_groups: Dict[int, List[SearchResult]] = {}
        for res in filtered_results:
            sid = getattr(res, "source_id", None)
            if sid is not None:
                try:
                    sid_int = int(sid)
                    if sid_int not in source_groups:
                        source_groups[sid_int] = []
                    source_groups[sid_int].append(res)
                except Exception:
                    continue
        
        for sid, results in source_groups.items():
            capped_results.extend(results)
            # 如果总结果数达到上限，停止添加
            if len(capped_results) >= max_results:
                break

        # 7. 缓存结果
        await self.cache_manager.set_search_results(cache_key, capped_results)

        end_time = time.time()
        logger.info(
            f"优化搜索完成: 共 {len(searchable_sources)} 个书源，"
            f"原始结果 {len(all_results)} 条，"
            f"过滤后 {len(filtered_results)} 条，"
            f"耗时 {end_time - start_time:.2f} 秒"
        )
        return capped_results

    def _get_prioritized_search_sources(self) -> List[Source]:
        """获取优先级排序的搜索书源"""
        searchable_sources = [
            source for source in self.sources.values() if source.rule.get("search")
        ]

        # 根据书源的历史性能和可靠性排序
        # 这里可以添加更复杂的优先级逻辑
        return sorted(searchable_sources, key=lambda s: s.id)

    def _filter_and_sort_results_optimized(
        self, results: List[SearchResult], keyword: str, max_results: int = 30
    ) -> List[SearchResult]:
        """优化版过滤和排序搜索结果"""
        if not results:
            return results

        # 使用集合进行快速去重
        seen_urls: Set[str] = set()
        valid_results = []

        # 预计算关键词的小写版本，避免重复转换
        keyword_lower = keyword.lower()

        for result in results:
            # 快速去重检查
            if result.url in seen_urls:
                continue

            # 基本有效性检查
            if not self._is_valid_result_fast(result):
                continue

            seen_urls.add(result.url)

            # 计算相关性得分（优化版）
            relevance_score = self._calculate_relevance_score_fast(
                result, keyword_lower
            )
            # 统一使用 SearchResult.score 字段存储相关性得分
            result.score = relevance_score

            if relevance_score > 0.1:  # 最低相关性阈值
                valid_results.append(result)

        # 按相关性得分排序
        valid_results.sort(key=lambda x: (x.score or 0), reverse=True)

        # 返回指定数量的结果
        return valid_results[:max_results]

    def _is_valid_result_fast(self, result: SearchResult) -> bool:
        """快速结果有效性检查"""
        if not result or not result.title or not result.url:
            return False

        if len(result.title.strip()) < 2:
            return False

        if not result.url.startswith(("http://", "https://")):
            return False

        return True

    def _calculate_relevance_score_fast(
        self, result: SearchResult, keyword_lower: str
    ) -> float:
        """快速计算相关性得分"""
        score = 0.0
        title_lower = result.title.lower() if result.title else ""
        author_lower = result.author.lower() if result.author else ""

        # 标题匹配
        if keyword_lower in title_lower:
            if keyword_lower == title_lower:
                score += 1.0  # 完全匹配
            elif title_lower.startswith(keyword_lower):
                score += 0.8  # 前缀匹配
            else:
                score += 0.6  # 包含匹配

        # 作者匹配
        if keyword_lower in author_lower:
            score += 0.4

        # 标题长度惩罚（过长的标题通常不太相关）
        if len(title_lower) > 50:
            score *= 0.9

        return score

    async def _search_source_with_timeout(self, source: Source, keyword: str) -> List[SearchResult]:
        """在指定书源中搜索（带超时控制）

        Args:
            source: 书源对象
            keyword: 搜索关键词

        Returns:
            搜索结果列表
        """
        try:
            search_parser = SearchParser(source)
            results = await search_parser.parse(keyword)
            return results
        except Exception as e:
            logger.error(f"书源 {source.rule.get('name', source.id)} 搜索异常: {str(e)}")
            return []

    async def download(
        self,
        url: str,
        source_id: int,
        format: str = "txt",
        task_id: Optional[str] = None,
    ) -> str:
        """下载小说

        优化点:
        1. 智能并发控制
        2. 章节缓存和断点续传
        3. 失败重试和备用书源
        4. 内存优化和流式处理

        Args:
            url: 小说详情页URL
            source_id: 书源ID
            format: 下载格式
            task_id: 任务ID

        Returns:
            下载文件路径
        """
        logger.info(f"开始下载: {url}")
        start_time = time.time()

        try:
            # 使用爬虫
            from app.core.crawler import Crawler

            # 创建下载配置
            download_config = self._create_download_config()
            # 使用全局 settings 作为通用配置（包含 DOWNLOAD_PATH 等路径）
            crawler = Crawler(settings)
            # 覆盖下载相关配置到 crawler
            crawler.download_config = download_config

            return await crawler.download(url, source_id, format, task_id)

        except Exception as e:
            logger.error(f"优化下载失败: {str(e)}")
            raise

    def _create_download_config(self):
        """创建下载配置"""
        from app.core.crawler import DownloadConfig

        config = DownloadConfig()
        # 提升并发与整体吞吐
        config.max_concurrent = max(
            self.max_concurrent_chapters, settings.DOWNLOAD_CONCURRENT_LIMIT
        )
        config.retry_times = max(settings.DOWNLOAD_RETRY_TIMES, 3)
        config.retry_delay = min(settings.DOWNLOAD_RETRY_DELAY, 1.0)
        config.batch_delay = 0.2  # 减少批次/间隔延迟
        config.timeout = 90  # 合理的章节超时
        config.enable_recovery = True

        return config

    async def get_sources(self) -> List[Dict[str, Any]]:
        """获取所有书源信息（优化版）"""
        # 检查缓存
        cached_sources = await self.cache_manager.get("sources_list")
        if cached_sources:
            return cached_sources

        sources_data = []
        for source_id, source in self.sources.items():
            rule = source.rule
            source_info = {
                "id": source_id,
                "name": rule.get("name", f"书源{source_id}"),
                "url": rule.get("url", ""),
                "enabled": rule.get("enabled", True),
                "search_enabled": bool(rule.get("search")),
                "download_enabled": bool(rule.get("book") and rule.get("toc")),
            }
            sources_data.append(source_info)

        # 缓存结果
        await self.cache_manager.set("sources_list", sources_data, ttl=3600)

        return sources_data

    async def get_book_detail(self, url: str, source_id: int) -> Optional[Book]:
        """获取小说详情（优化版）"""
        # 检查缓存
        cache_key = self.cache_manager._generate_cache_key(
            "book_detail", url, source_id
        )
        cached_book = await self.cache_manager.get_book_detail(cache_key)
        if cached_book:
            return cached_book

        if source_id not in self.sources:
            logger.error(f"书源 {source_id} 不存在")
            return None

        try:
            source = self.sources[source_id]
            parser = BookParser(source)
            book = await parser.parse(url)

            if book:
                # 缓存结果
                await self.cache_manager.set_book_detail(cache_key, book)

            return book
        except Exception as e:
            logger.error(f"获取小说详情失败: {str(e)}")
            return None

    async def get_toc(self, url: str, source_id: int) -> List[ChapterInfo]:
        """获取小说目录（优化版）"""
        # 检查缓存
        cache_key = self.cache_manager._generate_cache_key("toc", url, source_id)
        cached_toc = await self.cache_manager.get_toc(cache_key)
        if cached_toc:
            return cached_toc

        if source_id not in self.sources:
            logger.error(f"书源 {source_id} 不存在")
            return []

        try:
            source = self.sources[source_id]
            parser = TocParser(source)
            toc = await parser.parse(url)

            if toc:
                # 缓存结果
                await self.cache_manager.set_toc(cache_key, toc)

            return toc or []
        except Exception as e:
            logger.error(f"获取小说目录失败: {str(e)}")
            return []
