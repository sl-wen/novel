import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.source import Source
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.parsers.book_parser import BookParser
from app.parsers.chapter_parser import ChapterParser
from app.parsers.toc_parser import TocParser
from app.utils.file import FileUtils
from app.utils.download_monitor import DownloadMonitor
from app.utils.content_validator import ChapterValidator

logger = logging.getLogger(__name__)


@dataclass
class DownloadConfig:
    """下载配置"""
    max_concurrent: int = 3  # 降低并发数以提高稳定性
    retry_times: int = 5  # 增加重试次数
    retry_delay: float = 2.0
    batch_delay: float = 1.5  # 增加批次间延迟
    timeout: int = 60  # 增加超时时间
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
        
    async def download(self, url: str, source_id: int, format: str = "txt") -> str:
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
            # 1. 获取小说详情
            book = await self._get_book_detail_with_retry(url, source_id)
            if not book:
                raise ValueError("获取小说详情失败")
            
            logger.info(f"获取到小说: {book.title} - {book.author}")
            
            # 2. 获取目录（带重试和多种策略）
            toc = await self._get_toc_with_retry(url, source_id)
            if not toc:
                raise ValueError("获取小说目录失败")
            
            logger.info(f"获取到 {len(toc)} 个章节")
            
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
                toc, source_id, existing_chapters
            )
            
            logger.info(f"成功下载 {len(chapters)} 个章节")
            
            # 6. 生成最终文件
            file_path = await self._generate_final_file(
                book, chapters, download_dir, format
            )
            
            # 7. 清理临时文件
            await self._cleanup_temp_files(download_dir)
            
            end_time = time.time()
            logger.info(f"下载完成，耗时 {end_time - start_time:.2f} 秒")
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"下载失败: {str(e)}")
            raise
        finally:
            # 清理会话池
            await self._cleanup_sessions()
    
    async def _get_book_detail_with_retry(self, url: str, source_id: int) -> Optional[Book]:
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
                    await asyncio.sleep(self.download_config.retry_delay * (attempt + 1))
        
        return None
    
    async def _get_toc_with_retry(self, url: str, source_id: int) -> List[ChapterInfo]:
        """带重试和多策略的获取目录"""
        source = Source(source_id)
        parser = TocParser(source)
        
        # 策略1: 标准解析
        for attempt in range(self.download_config.retry_times):
            try:
                toc = await parser.parse(url)
                if toc:
                    logger.info(f"标准解析成功，获取到 {len(toc)} 个章节")
                    return toc
            except Exception as e:
                logger.warning(f"标准目录解析失败 (尝试 {attempt + 1}): {str(e)}")
                if attempt < self.download_config.retry_times - 1:
                    await asyncio.sleep(self.download_config.retry_delay * (attempt + 1))
        
        # 策略2: 尝试不同的选择器
        alternative_selectors = [
            ".catalog li a",
            ".chapter-list a",
            ".list-chapter a",
            ".book-chapter a",
            "ul li a",
            ".content li a"
        ]
        
        for selector in alternative_selectors:
            try:
                logger.info(f"尝试备用选择器: {selector}")
                toc = await self._parse_toc_with_selector(url, source, selector)
                if toc:
                    logger.info(f"备用选择器成功，获取到 {len(toc)} 个章节")
                    return toc
            except Exception as e:
                logger.warning(f"备用选择器 {selector} 失败: {str(e)}")
        
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
        existing_chapters: Dict[str, str]
    ) -> List[Chapter]:
        """增强版章节下载"""
        self.monitor.start_download(len(toc))
        
        source = Source(source_id)
        parser = ChapterParser(source)
        chapters = []
        self.failed_chapters = []
        
        # 创建临时目录
        temp_dir = Path(self.config.DOWNLOAD_PATH) / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        logger.info(f"开始下载 {len(toc)} 章，最大并发数: {self.download_config.max_concurrent}")
        
        # 分批处理
        for i in range(0, len(toc), self.download_config.max_concurrent):
            batch = toc[i:i + self.download_config.max_concurrent]
            batch_start = i + 1
            batch_end = min(i + self.download_config.max_concurrent, len(toc))
            
            logger.info(f"处理第 {batch_start}-{batch_end} 章")
            
            # 并发下载当前批次
            tasks = []
            for chapter_info in batch:
                # 检查是否已存在
                if chapter_info.title in existing_chapters:
                    logger.info(f"跳过已存在章节: {chapter_info.title}")
                    continue
                
                task = self._download_single_chapter_enhanced(
                    parser, chapter_info, temp_dir
                )
                tasks.append(task)
            
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"章节下载异常: {str(result)}")
                        continue
                    
                    if result:
                        chapters.append(result)
                        # 更新进度
                        if self.download_config.progress_callback:
                            self.download_config.progress_callback(
                                len(chapters), len(toc)
                            )
            
            # 批次间延迟
            if batch_end < len(toc):
                await asyncio.sleep(self.download_config.batch_delay)
        
        # 处理失败的章节
        if self.failed_chapters:
            logger.info(f"重试失败的 {len(self.failed_chapters)} 个章节")
            retry_chapters = await self._retry_failed_chapters(parser, temp_dir)
            chapters.extend(retry_chapters)
        
        # 从现有文件加载章节
        for title, file_path in existing_chapters.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    chapter = Chapter(title=title, content=content, order=0)
                    chapters.append(chapter)
            except Exception as e:
                logger.warning(f"加载已存在章节失败 {title}: {str(e)}")
        
        # 按顺序排序
        chapters.sort(key=lambda x: x.order or 0)
        
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
                chapter = await parser.parse(chapter_info.url)
                
                if not chapter or not chapter.content:
                    raise ValueError("章节内容为空")
                
                # 验证内容质量
                if len(chapter.content) < settings.MIN_CHAPTER_LENGTH:
                    raise ValueError(f"章节内容过短: {len(chapter.content)} 字符")
                
                quality_score = self.validator.get_chapter_quality_score(chapter.content)
                if quality_score < 0.3:  # 质量阈值
                    raise ValueError(f"章节质量过低: {quality_score}")
                
                # 保存到临时文件
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    f.write(chapter.content)
                
                # 设置章节顺序
                chapter.order = chapter_info.order
                
                self.monitor.chapter_completed(
                    chapter_info.title, len(chapter.content), quality_score
                )
                
                logger.debug(f"章节下载成功: {chapter.title} ({len(chapter.content)} 字符)")
                return chapter
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"章节下载失败 (尝试 {attempt + 1}): {chapter_info.title} - {error_msg}")
                
                if attempt < self.download_config.retry_times - 1:
                    await asyncio.sleep(self.download_config.retry_delay * (attempt + 1))
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
                    parser.parse(chapter_info.url),
                    timeout=self.download_config.timeout * 2
                )
                
                if chapter and chapter.content:
                    chapter.order = chapter_info.order
                    retry_chapters.append(chapter)
                    
                    # 保存到临时文件
                    chapter_file = temp_dir / f"{chapter_info.title}.txt"
                    with open(chapter_file, 'w', encoding='utf-8') as f:
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
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入书籍信息
                f.write(f"书名：{book.title}\n")
                f.write(f"作者：{book.author}\n")
                if book.intro:
                    f.write(f"简介：{book.intro}\n")
                f.write(f"章节数：{len(chapters)}\n")
                f.write("=" * 50 + "\n\n")
                
                # 写入章节内容
                for chapter in chapters:
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
        # TODO: 实现EPUB生成
        # 这里先生成TXT文件作为替代
        logger.warning("EPUB格式暂未实现，使用TXT格式替代")
        return await self._generate_txt_file_async(book, chapters, download_dir)
    
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
            "average_speed": progress.average_speed
        }