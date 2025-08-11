import asyncio
import json
import logging
import os
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
    """下载配置"""

    max_concurrent: int = 3  # 降低并发数以提高稳定性
    retry_times: int = 5  # 增加重试次数
    retry_delay: float = 2.0
    batch_delay: float = 1.5  # 增加批次间延迟
    timeout: int = 500  # 增加超时时间
    enable_recovery: bool = True  # 启用恢复机制
    progress_callback: Optional[callable] = None


class EnhancedCrawler:
    """增强版爬虫，提供更稳定的下载功能"""

    def __init__(self, config=None):
        """初始化增强版爬虫

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

            # 5. 下载章节（增强版）
            chapters = await self._download_chapters_enhanced(
                toc, source_id, existing_chapters, download_dir, task_id
            )

            logger.info(f"成功下载 {len(chapters)} 个章节")

            # 6. 生成最终文件
            file_path = await self._generate_final_file(
                book, chapters, download_dir, format
            )

            # 验证文件是否成功生成
            if not file_path or not file_path.exists():
                error_msg = f"文件生成失败: 路径为空或文件不存在 ({file_path})"
                logger.error(error_msg)
                if task_id:
                    progress_tracker.complete_task(task_id, False, error_msg)
                raise Exception(error_msg)

            # 6.1 记录生成文件路径
            if task_id:
                progress_tracker.set_file_path(task_id, str(file_path))
                logger.info(f"设置文件路径: {task_id} -> {file_path}")

            # 7. 清理临时文件
            await self._cleanup_temp_files(download_dir)

            end_time = time.time()
            logger.info(f"下载完成，耗时 {end_time - start_time:.2f} 秒")

            # 完成任务进度跟踪
            if task_id:
                progress_tracker.complete_task(task_id, True)
                logger.info(f"任务标记为完成: {task_id}")

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
                chapter_title = file_path.stem
                existing[chapter_title] = str(file_path)
        return existing

    async def _download_chapters_enhanced(
        self,
        toc: List[ChapterInfo],
        source_id: int,
        existing_chapters: Dict[str, str],
        download_dir: Path,
        task_id: Optional[str] = None,
    ) -> List[Chapter]:
        """增强版章节下载"""
        self.monitor.start_download(len(toc))

        source = Source(source_id)
        parser = ChapterParser(source)
        # 使用字典按order存储章节，确保顺序正确
        chapters_dict = {}
        self.failed_chapters = []

        # 创建临时目录（按书籍隔离，避免内容混淆）
        temp_dir = Path(download_dir) / "temp"
        temp_dir.mkdir(exist_ok=True)

        logger.info(
            f"开始下载 {len(toc)} 章，最大并发数: {self.download_config.max_concurrent}"
        )

        # 使用有界并发控制（不按批次，持续投递任务），提升总吞吐
        semaphore = asyncio.Semaphore(self.download_config.max_concurrent)

        async def download_one(chapter_info: ChapterInfo) -> Optional[Chapter]:
            if chapter_info.title in existing_chapters:
                logger.info(f"跳过已存在章节: {chapter_info.title}")
                return None
            async with semaphore:
                result = await self._download_single_chapter_enhanced(
                    parser, chapter_info, temp_dir
                )
                if result:
                    # 使用字典存储，保证按order排序
                    chapters_dict[chapter_info.order] = result
                    # 更新进度
                    if self.download_config.progress_callback:
                        self.download_config.progress_callback(len(chapters_dict), len(toc))
                    if task_id:
                        from app.utils.progress_tracker import progress_tracker

                        progress_tracker.update_progress(
                            task_id,
                            len(chapters_dict),
                            result.title,
                            len(self.failed_chapters),
                        )
                return result

        tasks = [download_one(ch) for ch in toc]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 处理失败的章节
        if self.failed_chapters:
            logger.info(f"重试失败的 {len(self.failed_chapters)} 个章节")
            retry_chapters = await self._retry_failed_chapters(parser, temp_dir)
            # 将重试成功的章节也按order存储
            for chapter in retry_chapters:
                if chapter.order:
                    chapters_dict[chapter.order] = chapter

        # 从现有文件加载章节，需要找到对应的order
        for title, file_path in existing_chapters.items():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 在toc中查找对应的order
                    chapter_order = None
                    for chapter_info in toc:
                        if chapter_info.title == title:
                            chapter_order = chapter_info.order
                            break
                    
                    if chapter_order is None:
                        # 如果找不到对应的order，使用一个大的数字放在最后
                        chapter_order = len(toc) + len(existing_chapters)
                    
                    chapter = Chapter(title=title, content=content, order=chapter_order)
                    chapters_dict[chapter_order] = chapter
            except Exception as e:
                logger.warning(f"加载已存在章节失败 {title}: {str(e)}")

        # 按order顺序转换为列表
        chapters = [chapters_dict[order] for order in sorted(chapters_dict.keys())]

        return chapters

    async def _download_single_chapter_enhanced(
        self, parser: ChapterParser, chapter_info: ChapterInfo, temp_dir: Path
    ) -> Optional[Chapter]:
        """增强版单章节下载"""
        chapter_file = temp_dir / f"{chapter_info.title}.txt"

        for attempt in range(self.download_config.retry_times):
            try:
                self.monitor.chapter_started(chapter_info.title, chapter_info.url)

                # 下载章节
                chapter = await parser.parse(
                    chapter_info.url, chapter_info.title, chapter_info.order
                )

                if not chapter or not chapter.content:
                    raise ValueError("章节内容为空")

                # 验证内容质量
                if len(chapter.content) < settings.MIN_CHAPTER_LENGTH:
                    raise ValueError(f"章节内容过短: {len(chapter.content)} 字符")

                quality_score = self.validator.get_chapter_quality_score(
                    chapter.content
                )
                if quality_score < 0.3:  # 质量阈值
                    raise ValueError(f"章节质量过低: {quality_score}")

                # 保存到临时文件
                with open(chapter_file, "w", encoding="utf-8") as f:
                    f.write(chapter.content)

                # 设置章节顺序
                chapter.order = chapter_info.order

                self.monitor.chapter_completed(
                    chapter_info.title, len(chapter.content), quality_score
                )

                logger.debug(
                    f"章节下载成功: {chapter.title} ({len(chapter.content)} 字符)"
                )
                return chapter

            except Exception as e:
                error_msg = str(e)
                logger.warning(
                    f"章节下载失败 (尝试 {attempt + 1}): {chapter_info.title} - {error_msg}"
                )

                if attempt < self.download_config.retry_times - 1:
                    await asyncio.sleep(
                        self.download_config.retry_delay * (attempt + 1)
                    )
                else:
                    # 记录失败章节
                    self.failed_chapters.append(chapter_info)
                    self.monitor.chapter_failed(chapter_info.title, error_msg)

        return None

    async def _retry_failed_chapters(
        self, parser: ChapterParser, temp_dir: Path
    ) -> List[Chapter]:
        """重试失败的章节"""
        retry_chapters = []

        for chapter_info in self.failed_chapters:
            try:
                logger.info(f"重试章节: {chapter_info.title}")

                # 使用更长的超时时间
                chapter = await asyncio.wait_for(
                    parser.parse(chapter_info.url, chapter_info.title, chapter_info.order),
                    timeout=self.download_config.timeout * 2,
                )

                if chapter and chapter.content:
                    # 确保order字段正确设置
                    chapter.order = chapter_info.order
                    retry_chapters.append(chapter)

                    # 保存到临时文件
                    chapter_file = temp_dir / f"{chapter_info.title}.txt"
                    with open(chapter_file, "w", encoding="utf-8") as f:
                        f.write(chapter.content)

                    logger.info(f"重试成功: {chapter.title}")

            except Exception as e:
                logger.error(f"重试失败: {chapter_info.title} - {str(e)}")

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
            # 确保章节按order排序
            sorted_chapters = sorted(chapters, key=lambda x: x.order or 0)
            
            with open(file_path, "w", encoding="utf-8") as f:
                # 写入书籍信息
                f.write(f"书名：{book.title}\n")
                f.write(f"作者：{book.author}\n")
                if book.intro:
                    f.write(f"简介：{book.intro}\n")
                f.write(f"章节数：{len(sorted_chapters)}\n")
                f.write("=" * 50 + "\n\n")

                # 写入章节内容，按正确顺序
                for chapter in sorted_chapters:
                    f.write(f"第{chapter.order}章 {chapter.title}\n")
                    f.write("-" * 30 + "\n")
                    f.write(chapter.content)
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
        safe_filename = FileUtils.get_safe_filename(f"{book.title}_{book.author}")
        epub_path = download_dir / f"{safe_filename}.epub"

        def generate_epub():
            generator = EPUBGenerator()
            return generator.generate(book, chapters, str(epub_path))

        # 在线程池中执行EPUB生成以避免阻塞
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            result_path = await loop.run_in_executor(executor, generate_epub)

        logger.info(f"EPUB文件生成完成: {result_path}")
        return Path(result_path)

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
