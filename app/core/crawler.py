import asyncio
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import time

from app.models.search import SearchResult
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.core.config import settings
from app.core.source import Source
from app.parsers.search_parser import SearchParser
from app.parsers.book_parser import BookParser
from app.parsers.toc_parser import TocParser
from app.parsers.chapter_parser import ChapterParser
from app.utils.file import FileUtils


class Crawler:
    """爬虫类，提供小说搜索、获取详情、获取目录和下载功能"""
    
    def __init__(self, config=None):
        """初始化爬虫
        
        Args:
            config: 配置信息，默认使用settings
        """
        self.config = config or settings
        self.book_dir = None
    
    async def search(self, keyword: str) -> List[SearchResult]:
        """搜索小说
        
        Args:
            keyword: 搜索关键词（书名或作者名）
            
        Returns:
            搜索结果列表
        """
        print(f"<== 正在搜索: {keyword}...")
        start_time = time.time()
        
        # 获取所有可搜索的书源
        sources = self._get_searchable_sources()
        
        # 创建任务列表
        tasks = []
        for source in sources:
            search_parser = SearchParser(source)
            tasks.append(search_parser.parse(keyword))
        
        # 并发执行搜索
        results = await asyncio.gather(*tasks)
        
        # 合并结果
        flat_results = []
        for result_list in results:
            flat_results.extend(result_list)
        
        # 排序结果
        sorted_results = self._sort_search_results(flat_results, keyword)
        
        end_time = time.time()
        print(f"<== 搜索到 {len(sorted_results)} 条记录，耗时 {end_time - start_time:.2f} 秒")
        
        return sorted_results
    
    async def get_book_detail(self, url: str, source_id: int) -> Book:
        """获取小说详情
        
        Args:
            url: 小说详情页URL
            source_id: 书源ID
            
        Returns:
            小说详情
        """
        source = Source(source_id)
        book_parser = BookParser(source)
        return await book_parser.parse(url)
    
    async def get_toc(self, url: str, source_id: int, start: int = 1, end: int = None) -> List[ChapterInfo]:
        """获取小说目录
        
        Args:
            url: 小说详情页URL
            source_id: 书源ID
            start: 起始章节，从1开始
            end: 结束章节，默认为None表示全部章节
            
        Returns:
            章节列表
        """
        source = Source(source_id)
        toc_parser = TocParser(source)
        return await toc_parser.parse(url, start, end or float('inf'))
    
    async def download(self, url: str, source_id: int, format: str = "txt") -> str:
        """下载小说
        
        Args:
            url: 小说详情页URL
            source_id: 书源ID
            format: 下载格式，支持txt、epub
            
        Returns:
            下载文件路径
        """
        # 获取小说详情
        book = await self.get_book_detail(url, source_id)
        
        # 获取小说目录
        toc = await self.get_toc(url, source_id)
        
        # 创建下载目录
        self.book_dir = FileUtils.sanitize_filename(f"{book.bookName}({book.author}) {format.upper()}")
        download_dir = Path(self.config.DOWNLOAD_PATH) / self.book_dir
        os.makedirs(download_dir, exist_ok=True)
        
        # 创建任务列表
        tasks = []
        source = Source(source_id)
        chapter_parser = ChapterParser(source)
        
        for chapter in toc:
            tasks.append(chapter_parser.parse(chapter.url, chapter.title, chapter.order))
        
        # 并发获取章节内容
        chapters = await asyncio.gather(*tasks)
        
        # 生成文件
        file_path = self._generate_file(book, chapters, format, download_dir)
        
        return file_path
    
    def _get_searchable_sources(self) -> List[Source]:
        """获取所有可搜索的书源
        
        Returns:
            可搜索的书源列表
        """
        # 这里应该实现从配置中获取所有可搜索的书源
        # 目前仅返回默认书源
        return [Source(self.config.DEFAULT_SOURCE_ID)]
    
    def _sort_search_results(self, results: List[SearchResult], keyword: str) -> List[SearchResult]:
        """排序搜索结果
        
        Args:
            results: 搜索结果列表
            keyword: 搜索关键词
            
        Returns:
            排序后的搜索结果列表
        """
        # 这里应该实现根据关键词对搜索结果进行排序
        # 目前仅返回原结果
        return results
    
    def _generate_file(self, book: Book, chapters: List[Chapter], format: str, download_dir: Path) -> str:
        """生成文件
        
        Args:
            book: 小说详情
            chapters: 章节列表
            format: 下载格式
            download_dir: 下载目录
            
        Returns:
            文件路径
        """
        # 生成文件名
        filename = f"{book.bookName}_{book.author}.{format}"
        file_path = download_dir / filename
        
        # 根据格式生成文件
        if format == "txt":
            return self._generate_txt(book, chapters, file_path)
        elif format == "epub":
            return self._generate_epub(book, chapters, file_path)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def _generate_txt(self, book: Book, chapters: List[Chapter], file_path: Path) -> str:
        """生成TXT文件
        
        Args:
            book: 小说详情
            chapters: 章节列表
            file_path: 文件路径
            
        Returns:
            文件路径
        """
        with open(file_path, "w", encoding="utf-8") as f:
            # 写入小说信息
            f.write(f"书名: {book.bookName}\n")
            f.write(f"作者: {book.author}\n")
            f.write(f"简介: {book.intro}\n\n")
            
            # 写入章节内容
            for chapter in chapters:
                f.write(f"\n{chapter.title}\n\n")
                f.write(f"{chapter.content}\n")
        
        return str(file_path)
    
    def _generate_epub(self, book: Book, chapters: List[Chapter], file_path: Path) -> str:
        """生成EPUB文件
        
        Args:
            book: 小说详情
            chapters: 章节列表
            file_path: 文件路径
            
        Returns:
            文件路径
        """
        # 这里应该实现生成EPUB文件的逻辑
        # 目前仅生成TXT文件代替
        return self._generate_txt(book, chapters, file_path.with_suffix(".txt"))
    