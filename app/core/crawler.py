import asyncio
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.parsers.book_parser import BookParser
from app.parsers.chapter_parser import ChapterParser
from app.parsers.toc_parser import TocParser
from app.utils.content_validator import ChapterValidator
from app.utils.download_monitor import DownloadMonitor
from app.utils.file import FileUtils

logger = logging.getLogger(__name__)


@dataclass
class DownloadConfig:
    """下载配置（优化版）"""

    max_concurrent: int = 15  # 增加并发数
    retry_times: int = 3  # 减少重试次数
    retry_delay: float = 0.5  # 大幅减少重试延迟
    batch_delay: float = 0.1  # 大幅减少批次间延迟
    timeout: int = 30  # 减少超时时间
    enable_recovery: bool = True  # 启用恢复机制
    progress_callback: Optional[callable] = None
    
    # 新增性能优化选项
    enable_batch_write: bool = True  # 启用批量写入
    batch_write_size: int = 10  # 批量写入大小
    skip_quality_check: bool = False  # 跳过质量检查以提高速度
    connection_pool_size: int = 50  # 连接池大小


class Crawler:
    """爬虫，提供稳定的下载功能"""

    def __init__(self, config=None):
        """初始化爬虫

        Args:
            config: 下载配置
        """
        self.config = config or settings
        self.download_config = DownloadConfig()
        self.monitor = DownloadMonitor()
        self.validator = ChapterValidator()
        self.session_pool = {}  # 会话池
        self.failed_chapters = []  # 失败章节记录

    async def download(
        self,
        url: str,
        source_id: int,
        format: str = "txt",
        task_id: Optional[str] = None,
    ) -> str:
        """下载小说（增强版）

        Args:
            url: 小说详情页URL
            source_id: 书源ID
            format: 下载格式

        Returns:
            下载文件路径
        """
        logger.info(f"开始增强版下载: {url}")
        start_time = time.time()

        try:
            # 初始化进度跟踪
            from app.utils.progress_tracker import progress_tracker

            # 1. 获取小说详情（带重试和多源支持）
            book = await self._get_book_detail_with_fallback(url, source_id)
            if not book:
                if task_id:
                    progress_tracker.complete_task(task_id, False, "获取小说详情失败")
                raise ValueError("获取小说详情失败")

            logger.info(f"获取到小说: {book.title} - {book.author}")

            # 2. 获取目录（带重试和多种策略）
            toc = await self._get_toc_with_fallback(url, source_id)
            if not toc:
                if task_id:
                    progress_tracker.complete_task(task_id, False, "获取小说目录失败")
                raise ValueError("获取小说目录失败")

            logger.info(f"获取到 {len(toc)} 个章节")

            # 初始化或更新进度跟踪
            if task_id:
                progress_tracker.update_progress(task_id, 0, "开始下载", 0)
                # 更新总章节数
                progress = progress_tracker.get_progress(task_id)
                if progress:
                    progress.total_chapters = len(toc)

            # 3. 创建下载目录
            download_dir = await self._create_download_directory(book, format)

            # 4. 检查是否有未完成的下载
            if self.download_config.enable_recovery:
                existing_chapters = self._check_existing_chapters(download_dir)
                logger.info(f"发现已下载章节: {len(existing_chapters)} 个")
            else:
                existing_chapters = {}

            # 5. 下载章节
            chapters = await self._download_chapters(
                toc, source_id, existing_chapters, download_dir, task_id
            )

            logger.info(f"成功下载 {len(chapters)} 个章节")

            # 6. 生成最终文件
            file_path = await self._generate_final_file(
                book, chapters, download_dir, format
            )

            # 6.1 验证文件完整性
            await self._verify_file_integrity(file_path)

            # 6.1.5 对于EPUB文件，进行额外的就绪检查
            if format.lower() == "epub":
                await self._ensure_epub_file_ready(file_path)

            # 6.2 记录生成文件路径
            if task_id:
                progress_tracker.set_file_path(task_id, str(file_path))

            # 7. 清理临时文件
            await self._cleanup_temp_files(download_dir)

            end_time = time.time()
            logger.info(f"下载完成，耗时 {end_time - start_time:.2f} 秒")

            # 完成任务进度跟踪
            if task_id:
                progress_tracker.complete_task(task_id, True)

            return str(file_path)

        except Exception as e:
            logger.error(f"下载失败: {str(e)}")
            # 标记任务失败
            if task_id:
                progress_tracker.complete_task(task_id, False, str(e))
            raise
        finally:
            # 清理会话池
            await self._cleanup_sessions()

    async def _get_book_detail_with_fallback(
        self, url: str, source_id: int
    ) -> Optional[Book]:
        """带备用源的获取书籍详情"""
        # 首先尝试指定的书源
        book = await self._get_book_detail_with_retry(url, source_id)
        if book:
            return book

        # 如果失败，尝试其他可用书源
        logger.warning(f"书源 {source_id} 获取详情失败，尝试其他书源")

        # 这里可以添加书源切换逻辑
        # 暂时返回None，让上层处理
        return None

    async def _get_book_detail_with_retry(
        self, url: str, source_id: int
    ) -> Optional[Book]:
        """带重试的获取书籍详情"""
        for attempt in range(self.download_config.retry_times):
            try:
                source = Source(source_id)
                parser = BookParser(source)
                book = await parser.parse(url)
                if book:
                    return book
            except Exception as e:
                logger.warning(f"获取书籍详情失败 (尝试 {attempt + 1}): {str(e)}")
                if attempt < self.download_config.retry_times - 1:
                    await asyncio.sleep(
                        self.download_config.retry_delay * (attempt + 1)
                    )

        return None

    async def _get_toc_with_fallback(
        self, url: str, source_id: int
    ) -> List[ChapterInfo]:
        """带备用源的获取目录"""
        # 首先尝试指定的书源
        toc = await self._get_toc_with_retry(url, source_id)
        if toc:
            return toc

        # 如果失败，尝试其他可用书源
        logger.warning(f"书源 {source_id} 获取目录失败，尝试其他书源")

        # 这里可以添加书源切换逻辑
        return []

    async def _get_toc_with_retry(self, url: str, source_id: int) -> List[ChapterInfo]:
        """带重试和多策略的获取目录"""
        source = Source(source_id)
        parser = TocParser(source)

        # 多次尝试获取目录
        for attempt in range(self.download_config.retry_times):
            try:
                toc = await parser.parse(url)
                if toc:
                    logger.info(f"目录解析成功，获取到 {len(toc)} 个章节")
                    return toc
            except Exception as e:
                logger.warning(f"目录解析失败 (尝试 {attempt + 1}): {str(e)}")
                if attempt < self.download_config.retry_times - 1:
                    await asyncio.sleep(
                        self.download_config.retry_delay * (attempt + 1)
                    )

        return []

    async def _parse_toc_with_selector(
        self, url: str, source: Source, selector: str
    ) -> List[ChapterInfo]:
        """使用指定选择器解析目录"""
        # 临时修改书源规则
        original_rule = source.rule.get("toc", {}).copy()
        source.rule["toc"]["list"] = selector

        try:
            parser = TocParser(source)
            return await parser.parse(url)
        finally:
            # 恢复原始规则
            source.rule["toc"] = original_rule

    async def _create_download_directory(self, book: Book, format: str) -> Path:
        """创建下载目录"""
        safe_title = FileUtils.sanitize_filename(book.title)
        safe_author = FileUtils.sanitize_filename(book.author)
        dir_name = f"{safe_title} ({safe_author}) {format.upper()}"

        download_dir = Path(self.config.DOWNLOAD_PATH) / dir_name
        download_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"下载目录: {download_dir}")
        return download_dir

    def _check_existing_chapters(self, download_dir: Path) -> Dict[str, str]:
        """检查已存在的章节文件"""
        existing = {}
        temp_dir = download_dir / "temp"
        if temp_dir.exists():
            for file_path in temp_dir.glob("*.txt"):
                # 文件名是经过sanitize的，需要映射回原始标题
                safe_filename = file_path.stem
                existing[safe_filename] = str(file_path)
        return existing

    async def _download_chapters(
        self,
        toc: List[ChapterInfo],
        source_id: int,
        existing_chapters: Dict[str, str],
        download_dir: Path,
        task_id: Optional[str] = None,
    ) -> List[Chapter]:
        """章节下载（高性能优化版）"""
        self.monitor.start_download(len(toc))
        
        # 性能统计
        start_time = time.time()
        download_stats = {
            "total_chapters": len(toc),
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "batch_writes": 0
        }

        source = Source(source_id)
        parser = ChapterParser(source)
        chapters = []
        self.failed_chapters = []

        # 创建临时目录
        temp_dir = Path(download_dir) / "temp"
        temp_dir.mkdir(exist_ok=True)

        logger.info(
            f"开始高性能下载 {len(toc)} 章，最大并发数: {self.download_config.max_concurrent}"
        )

        # 批量写入队列
        write_queue = []
        write_lock = asyncio.Lock()

        async def batch_write_chapters():
            """批量写入章节到文件"""
            nonlocal write_queue
            if not write_queue:
                return
            
            async with write_lock:
                current_batch = write_queue.copy()
                write_queue.clear()
                
                # 并发写入多个文件
                write_tasks = []
                for chapter_data in current_batch:
                    write_tasks.append(self._write_chapter_file(chapter_data, temp_dir))
                
                await asyncio.gather(*write_tasks, return_exceptions=True)
                download_stats["batch_writes"] += 1
                logger.debug(f"批量写入 {len(current_batch)} 个章节")

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(self.download_config.max_concurrent)

        async def download_one(chapter_info: ChapterInfo) -> Optional[Chapter]:
            safe_filename = FileUtils.sanitize_filename(chapter_info.title)
            
            # 检查是否已存在
            if safe_filename in existing_chapters:
                logger.debug(f"跳过已存在章节: {chapter_info.title}")
                download_stats["skipped"] += 1
                return None
            
            async with semaphore:
                try:
                    # 下载章节内容
                    chapter = await self._download_single_chapter_optimized(
                        parser, chapter_info
                    )
                    
                    if chapter:
                        # 添加到批量写入队列
                        async with write_lock:
                            write_queue.append({
                                'chapter': chapter,
                                'filename': safe_filename,
                                'chapter_info': chapter_info
                            })
                        
                        # 当队列达到批量大小时，执行批量写入
                        if len(write_queue) >= self.download_config.batch_write_size:
                            await batch_write_chapters()
                        
                        chapters.append(chapter)
                        download_stats["downloaded"] += 1
                        
                        # 更新进度
                        if task_id:
                            from app.utils.progress_tracker import progress_tracker
                            progress_tracker.update_progress(
                                task_id,
                                len(chapters),
                                chapter.title,
                                len(self.failed_chapters),
                            )
                    else:
                        download_stats["failed"] += 1
                        self.failed_chapters.append(chapter_info)
                    
                    return chapter
                    
                except Exception as e:
                    logger.warning(f"下载章节失败: {chapter_info.title} - {str(e)}")
                    download_stats["failed"] += 1
                    self.failed_chapters.append(chapter_info)
                    return None

        # 并发下载所有章节
        tasks = [download_one(ch) for ch in toc]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 写入剩余的章节
        if write_queue:
            await batch_write_chapters()

        # 处理失败的章节（减少重试次数）
        if self.failed_chapters and len(self.failed_chapters) < len(toc) * 0.3:  # 只有失败率低于30%时才重试
            logger.info(f"重试失败的 {len(self.failed_chapters)} 个章节")
            retry_chapters = await self._retry_failed_chapters_optimized(parser, temp_dir)
            chapters.extend(retry_chapters)
            download_stats["downloaded"] += len(retry_chapters)

        # 从现有文件加载章节
        for safe_filename, file_path in existing_chapters.items():
            try:
                chapter = await self._load_existing_chapter(file_path, safe_filename, toc)
                if chapter:
                    chapters.append(chapter)
            except Exception as e:
                logger.warning(f"加载已存在章节失败 {safe_filename}: {str(e)}")

        # 按顺序排序
        chapters.sort(key=lambda x: x.order or 0)

        # 输出性能统计
        end_time = time.time()
        download_time = end_time - start_time
        
        logger.info(f"下载完成统计: 总章节={download_stats['total_chapters']}, "
                   f"下载={download_stats['downloaded']}, 跳过={download_stats['skipped']}, "
                   f"失败={download_stats['failed']}, 批量写入次数={download_stats['batch_writes']}, "
                   f"耗时={download_time:.2f}s, 速度={download_stats['downloaded']/max(download_time, 1):.2f}章/s")

        return chapters

    async def _download_single_chapter_optimized(
        self, parser: ChapterParser, chapter_info: ChapterInfo
    ) -> Optional[Chapter]:
        """优化版单章节下载（不写文件，只返回内容）"""
        for attempt in range(self.download_config.retry_times):
            try:
                self.monitor.chapter_started(chapter_info.title, chapter_info.url)

                # 下载章节
                chapter = await asyncio.wait_for(
                    parser.parse(chapter_info.url, chapter_info.title, chapter_info.order),
                    timeout=self.download_config.timeout
                )

                if not chapter or not chapter.content:
                    if attempt < self.download_config.retry_times - 1:
                        await asyncio.sleep(self.download_config.retry_delay)
                        continue
                    return None

                # 快速内容验证（可选）
                if not self.download_config.skip_quality_check:
                    if len(chapter.content) < settings.MIN_CHAPTER_LENGTH:
                        if attempt < self.download_config.retry_times - 1:
                            await asyncio.sleep(self.download_config.retry_delay)
                            continue
                        return None

                # 设置章节顺序
                chapter.order = chapter_info.order

                self.monitor.chapter_completed(
                    chapter_info.title, len(chapter.content), 1.0  # 跳过质量评分以提高速度
                )

                return chapter

            except asyncio.TimeoutError:
                logger.warning(f"章节下载超时: {chapter_info.title} (尝试 {attempt + 1}/{self.download_config.retry_times})")
                if attempt < self.download_config.retry_times - 1:
                    await asyncio.sleep(self.download_config.retry_delay)
                    continue

            except Exception as e:
                logger.warning(f"章节下载异常: {chapter_info.title} - {str(e)} (尝试 {attempt + 1}/{self.download_config.retry_times})")
                if attempt < self.download_config.retry_times - 1:
                    await asyncio.sleep(self.download_config.retry_delay * (attempt + 1))
                    continue

        return None

    async def _write_chapter_file(self, chapter_data: dict, temp_dir: Path):
        """异步写入章节文件"""
        try:
            chapter = chapter_data['chapter']
            filename = chapter_data['filename']
            chapter_file = temp_dir / f"{filename}.txt"
            
            # 使用线程池进行文件I/O，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: chapter_file.write_text(chapter.content, encoding='utf-8')
            )
        except Exception as e:
            logger.error(f"写入章节文件失败: {filename} - {str(e)}")

    async def _load_existing_chapter(self, file_path: str, safe_filename: str, toc: List[ChapterInfo]) -> Optional[Chapter]:
        """异步加载已存在的章节文件"""
        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None,
                lambda: Path(file_path).read_text(encoding='utf-8')
            )
            
            # 从toc中找到对应章节的正确order和原始标题
            correct_order = 0
            original_title = safe_filename
            for toc_chapter in toc:
                if FileUtils.sanitize_filename(toc_chapter.title) == safe_filename:
                    correct_order = toc_chapter.order
                    original_title = toc_chapter.title
                    break
            
            return Chapter(
                title=original_title,
                content=content,
                order=correct_order
            )
        except Exception as e:
            logger.warning(f"加载已存在章节失败 {safe_filename}: {str(e)}")
            return None

    async def _retry_failed_chapters_optimized(
        self, parser: ChapterParser, temp_dir: Path
    ) -> List[Chapter]:
        """优化版失败章节重试"""
        retry_chapters = []
        
        # 减少重试的并发数，提高成功率
        retry_semaphore = asyncio.Semaphore(max(self.download_config.max_concurrent // 2, 3))
        
        async def retry_one(chapter_info: ChapterInfo) -> Optional[Chapter]:
            async with retry_semaphore:
                # 增加重试间隔
                await asyncio.sleep(self.download_config.retry_delay * 2)
                return await self._download_single_chapter_optimized(parser, chapter_info)
        
        tasks = [retry_one(ch) for ch in self.failed_chapters[:10]]  # 限制重试数量
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Chapter):
                retry_chapters.append(result)
        
        # 批量写入重试成功的章节
        if retry_chapters:
            write_tasks = []
            for chapter in retry_chapters:
                safe_filename = FileUtils.sanitize_filename(chapter.title)
                chapter_data = {
                    'chapter': chapter,
                    'filename': safe_filename,
                    'chapter_info': None
                }
                write_tasks.append(self._write_chapter_file(chapter_data, temp_dir))
            
            await asyncio.gather(*write_tasks, return_exceptions=True)
            logger.info(f"重试成功 {len(retry_chapters)} 个章节")
        
        return retry_chapters

    async def _generate_final_file(
        self, book: Book, chapters: List[Chapter], download_dir: Path, format: str
    ) -> Path:
        """生成最终文件"""
        if format == "txt":
            return await self._generate_txt_file_async(book, chapters, download_dir)
        elif format == "epub":
            return await self._generate_epub_file_async(book, chapters, download_dir)
        else:
            raise ValueError(f"不支持的格式: {format}")

    async def _generate_txt_file_async(
        self, book: Book, chapters: List[Chapter], download_dir: Path
    ) -> Path:
        """异步生成TXT文件"""
        filename = f"{FileUtils.sanitize_filename(book.title)}.txt"
        file_path = download_dir / filename

        def write_file():
            # 确保章节按顺序排列
            chapters.sort(key=lambda x: x.order or 0)

            with open(file_path, "w", encoding="utf-8") as f:
                # 写入书籍信息
                f.write(f"书名：{book.title}\n")
                f.write(f"作者：{book.author}\n")
                if book.intro:
                    f.write(f"简介：{book.intro}\n")
                f.write(f"章节数：{len(chapters)}\n")
                f.write("=" * 50 + "\n\n")

                # 写入章节内容
                for chapter in chapters:
                    # 清理章节标题，移除冗余信息
                    title = self._clean_chapter_title(chapter.title)
                    
                    f.write(f"{title}\n")
                    f.write("-" * 30 + "\n")
                    
                    # 清理章节内容
                    content = self._clean_chapter_content_for_output(chapter.content)
                    f.write(content)
                    f.write("\n\n")

        # 在线程池中执行文件写入
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, write_file)

        logger.info(f"TXT文件生成完成: {file_path}")
        return file_path

    async def _generate_epub_file_async(
        self, book: Book, chapters: List[Chapter], download_dir: Path
    ) -> Path:
        """异步生成EPUB文件"""
        from app.utils.epub_generator import EPUBGenerator

        # 生成安全的文件名
        safe_filename = FileUtils.sanitize_filename(f"{book.title}_{book.author}")
        epub_path = download_dir / f"{safe_filename}.epub"

        def generate_epub():
            generator = EPUBGenerator()
            return generator.generate(book, chapters, str(epub_path))

        # 在线程池中执行EPUB生成以避免阻塞
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            result_path = await loop.run_in_executor(executor, generate_epub)

        # 额外的文件就绪检查
        result_path_obj = Path(result_path)
        max_wait_attempts = 10
        for attempt in range(max_wait_attempts):
            try:
                # 检查文件是否存在且可读
                if result_path_obj.exists() and result_path_obj.stat().st_size > 0:
                    # 尝试打开文件确保完全可用
                    with open(result_path, "rb") as f:
                        header = f.read(4)
                        if header == b'PK\x03\x04':
                            logger.info(f"EPUB文件生成完成: {result_path}")
                            return result_path_obj
                
                # 如果文件还没就绪，稍等片刻
                await asyncio.sleep(0.1)
                
            except Exception as e:
                if attempt < max_wait_attempts - 1:
                    logger.warning(f"EPUB文件检查失败 (尝试 {attempt + 1}): {str(e)}")
                    await asyncio.sleep(0.1)
                    continue
                else:
                    logger.error(f"EPUB文件最终检查失败: {str(e)}")
                    raise
        
        # 如果所有尝试都失败了
        raise ValueError(f"EPUB文件生成后验证失败: {result_path}")

    async def _verify_file_integrity(self, file_path: Path):
        """验证文件完整性"""
        try:
            # 检查文件是否存在
            if not file_path.exists():
                raise ValueError("文件不存在")
            
            # 检查文件大小
            file_size = file_path.stat().st_size
            if file_size == 0:
                raise ValueError("文件大小为0")
            
            # 根据文件类型进行不同的验证
            if file_path.suffix.lower() == '.txt':
                # TXT文件验证
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 检查文件是否为空
                    if not content.strip():
                        raise ValueError("文件内容为空")
                    # 检查文件是否包含基本的书籍信息
                    if "书名：" not in content:
                        raise ValueError("文件缺少书名信息")
            elif file_path.suffix.lower() == '.epub':
                # EPUB文件验证 - 简单检查文件头
                with open(file_path, "rb") as f:
                    # EPUB文件应该是ZIP格式，检查ZIP文件头
                    header = f.read(4)
                    if header != b'PK\x03\x04':
                        raise ValueError("EPUB文件格式无效")
            
            logger.info(f"文件完整性验证通过: {file_path} (大小: {file_size} 字节)")
            
        except Exception as e:
            logger.error(f"文件完整性验证失败: {file_path} - {str(e)}")
            raise

    async def _ensure_epub_file_ready(self, file_path: Path):
        """确保EPUB文件完全就绪"""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                # 检查文件大小是否稳定
                initial_size = file_path.stat().st_size
                await asyncio.sleep(0.2)  # 等待稍长时间
                final_size = file_path.stat().st_size
                
                if initial_size == final_size and final_size > 0:
                    # 尝试读取文件确保完整性
                    with open(file_path, "rb") as f:
                        header = f.read(4)
                        if header == b'PK\x03\x04':
                            # 尝试读取更多内容
                            f.read(1024)
                            logger.info(f"EPUB文件就绪检查通过: {file_path}")
                            return
                        else:
                            raise ValueError("EPUB文件头无效")
                else:
                    if attempt < max_attempts - 1:
                        logger.warning(f"EPUB文件大小不稳定 (尝试 {attempt + 1}): {initial_size} -> {final_size}")
                        await asyncio.sleep(0.3)
                        continue
                    else:
                        raise ValueError("EPUB文件大小不稳定")
                        
            except Exception as e:
                if attempt < max_attempts - 1:
                    logger.warning(f"EPUB文件就绪检查失败 (尝试 {attempt + 1}): {str(e)}")
                    await asyncio.sleep(0.3)
                    continue
                else:
                    logger.error(f"EPUB文件最终就绪检查失败: {str(e)}")
                    raise

    async def _cleanup_temp_files(self, download_dir: Path):
        """清理临时文件"""
        temp_dir = download_dir / "temp"
        if temp_dir.exists():
            try:
                import shutil

                shutil.rmtree(temp_dir)
                logger.info("临时文件清理完成")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")

    async def _cleanup_sessions(self):
        """清理会话池"""
        for session in self.session_pool.values():
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"关闭会话失败: {str(e)}")
        self.session_pool.clear()

    def get_download_progress(self) -> Dict[str, Any]:
        """获取下载进度信息"""
        progress = self.monitor.get_progress()
        return {
            "total_chapters": progress.total_chapters,
            "completed_chapters": progress.completed_chapters,
            "failed_chapters": progress.failed_chapters,
            "progress_percentage": progress.progress_percentage,
            "success_rate": progress.success_rate,
            "elapsed_time": progress.elapsed_time,
            "average_speed": progress.average_speed,
        }

    def _clean_chapter_title(self, title: str) -> str:
        """清理章节标题，移除冗余信息"""
        if not title:
            return "未知章节"
        
        # 移除常见的元数据信息
        patterns_to_remove = [
            r"\s*小说：.*?作者：.*?字数：.*?更新时间.*?$",
            r"\s*作者：.*?字数：\d+.*?更新时间.*?$",
            r"\s*字数：\d+.*?更新时间.*?$",
            r"\s*更新时间\s*[:：]\s*\d{4}-\d{2}-\d{2}.*?$",
            r"\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}.*?$",
        ]
        
        cleaned_title = title
        for pattern in patterns_to_remove:
            cleaned_title = re.sub(pattern, "", cleaned_title, flags=re.IGNORECASE)
        
        # 移除多余的空白字符
        cleaned_title = re.sub(r"\s+", " ", cleaned_title).strip()
        
        return cleaned_title if cleaned_title else "未知章节"
    
    def _clean_chapter_content_for_output(self, content: str) -> str:
        """清理章节内容用于输出"""
        if not content:
            return ""
        
        import html
        
        # 解码HTML实体
        content = html.unescape(content)
        
        # 移除开头可能存在的章节标题重复信息
        lines = content.split('\n')
        cleaned_lines = []
        
        skip_first_lines = True
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 跳过前面几行中的元数据信息
            if skip_first_lines and i < 5:
                # 如果这行包含元数据信息，跳过
                if re.search(r"小说：|作者：|字数：|更新时间", line):
                    continue
                # 如果是章节标题重复，跳过
                if re.search(r"^第[一二三四五六七八九十百千0-9]+章", line):
                    continue
                # 如果是分隔符行，跳过
                if re.match(r"^[-=_]{3,}$", line):
                    continue
                # 如果遇到实际内容，停止跳过
                if line and len(line) > 10 and not re.search(r"^(第|章节|目录)", line):
                    skip_first_lines = False
            
            if line:
                cleaned_lines.append(line)
        
        # 重新组合内容
        cleaned_content = '\n'.join(cleaned_lines)
        
        # 确保段落间有适当的间距
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        return cleaned_content
