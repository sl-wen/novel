import asyncio
import time
from pathlib import Path
from typing import List
import os

from app.core.config import settings
from app.core.source import Source
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.models.search import SearchResult
from app.parsers.book_parser import BookParser
from app.parsers.chapter_parser import ChapterParser
from app.parsers.search_parser import SearchParser
from app.parsers.toc_parser import TocParser
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
        self.digit_count = 0

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
        print(
            f"<== 搜索到 {len(sorted_results)} 条记录，"
            f"耗时 {end_time - start_time:.2f} 秒"
        )

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

    async def get_toc(
        self, url: str, source_id: int, start: int = 1, end: int = None
    ) -> List[ChapterInfo]:
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
        return await toc_parser.parse(url, start, end or float("inf"))

    async def download(self, url: str, source_id: int, format: str = "txt") -> str:
        """下载小说

        Args:
            url: 小说详情页URL
            source_id: 书源ID
            format: 下载格式，支持txt、epub

        Returns:
            下载文件路径
        """
        print(f"<== 开始下载小说: {url}")
        start_time = time.time()

        # 获取小说详情
        book = await self.get_book_detail(url, source_id)
        if not book:
            raise ValueError("获取小说详情失败")

        print(f"<== 获取到小说: {book.title}")

        # 获取目录
        toc = await self.get_toc(url, source_id)
        if not toc:
            raise ValueError("获取小说目录失败")

        print(f"<== 获取到 {len(toc)} 个章节")

        # 设置数字位数和目录名
        self.digit_count = len(str(len(toc)))
        
        # 创建下载目录，格式：书名 (作者) 格式
        safe_title = FileUtils.sanitize_filename(book.title)
        safe_author = FileUtils.sanitize_filename(book.author)
        self.book_dir = f"{safe_title} ({safe_author}) {format.upper()}"
        
        download_base_dir = Path(self.config.DOWNLOAD_PATH)
        book_download_dir = download_base_dir / self.book_dir
        
        # 创建目录
        os.makedirs(book_download_dir, exist_ok=True)
        
        if not book_download_dir.exists():
            raise ValueError(f"创建下载目录失败: {book_download_dir}")

        print(f"<== 下载目录: {book_download_dir}")

        # 并发下载章节
        max_concurrent = self.config.DOWNLOAD_CONCURRENT_LIMIT
        source = Source(source_id)
        chapter_parser = ChapterParser(source)
        
        print(f"<== 开始下载 {len(toc)} 章，最大并发数: {max_concurrent}")
        
        # 分批处理章节
        chapters = []
        for i in range(0, len(toc), max_concurrent):
            batch = toc[i:i + max_concurrent]
            print(f"<== 处理第 {i+1}-{min(i+max_concurrent, len(toc))} 章")
            
            # 并发下载当前批次
            tasks = []
            for chapter_info in batch:
                task = self._download_single_chapter(chapter_parser, chapter_info)
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for j, result in enumerate(batch_results):
                chapter_info = batch[j]
                if isinstance(result, Exception):
                    print(f"<== 章节下载失败: {chapter_info.title}, 错误: {str(result)}")
                elif result:
                    chapters.append(result)
                    print(f"<== 章节下载成功: {result.title}")
            
            # 批次间延迟
            if i + max_concurrent < len(toc):
                await asyncio.sleep(0.5)

        print(f"<== 成功下载 {len(chapters)} 个章节")

        # 生成最终文件
        if format == "txt":
            file_path = self._generate_txt_file(book, chapters, book_download_dir)
        elif format == "epub":
            file_path = self._generate_epub_file(book, chapters, book_download_dir)
        else:
            raise ValueError(f"不支持的格式: {format}")

        end_time = time.time()
        print(f"<== 下载完成，耗时 {end_time - start_time:.2f} 秒")

        return str(file_path)

    async def _download_single_chapter(
        self, chapter_parser: ChapterParser, chapter_info: ChapterInfo
    ) -> Chapter:
        """下载单个章节

        Args:
            chapter_parser: 章节解析器
            chapter_info: 章节信息

        Returns:
            章节对象
        """
        try:
            chapter = await chapter_parser.parse(chapter_info.url)
            if chapter:
                # 保存章节到文件
                self._save_chapter_file(chapter)
            return chapter
        except Exception as e:
            print(f"<== 章节下载异常: {chapter_info.title}, 错误: {str(e)}")
            return None

    def _save_chapter_file(self, chapter: Chapter):
        """保存章节到文件

        Args:
            chapter: 章节对象
        """
        try:
            # 生成文件路径
            file_path = self._generate_chapter_path(chapter)
            
            # 确保目录存在
            os.makedirs(file_path.parent, exist_ok=True)
            
            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(chapter.content)
                
        except Exception as e:
            print(f"<== 保存章节文件失败: {chapter.title}, 错误: {str(e)}")

    def _generate_chapter_path(self, chapter: Chapter) -> Path:
        """生成章节文件路径

        Args:
            chapter: 章节对象

        Returns:
            文件路径
        """
        download_base_dir = Path(self.config.DOWNLOAD_PATH)
        book_download_dir = download_base_dir / self.book_dir
        
        # 文件名下划线前的数字前补零
        order_str = str(chapter.order).zfill(self.digit_count)
        
        # 生成文件名
        safe_title = FileUtils.sanitize_filename(chapter.title)
        filename = f"{order_str}_{safe_title}.txt"
        
        return book_download_dir / filename

    def _generate_txt_file(
        self, book: Book, chapters: List[Chapter], download_dir: Path
    ) -> Path:
        """生成TXT文件

        Args:
            book: 小说信息
            chapters: 章节列表
            download_dir: 下载目录

        Returns:
            文件路径
        """
        # 生成文件名
        safe_title = FileUtils.sanitize_filename(book.title)
        safe_author = FileUtils.sanitize_filename(book.author)
        filename = f"{safe_title}_{safe_author}.txt"
        file_path = download_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            # 写入小说信息
            f.write(f"书名：{book.title}\n")
            f.write(f"作者：{book.author}\n")
            f.write(f"简介：{book.intro}\n")
            f.write(f"状态：{book.status}\n")
            f.write(f"分类：{book.category}\n")
            f.write(f"字数：{book.word_count}\n")
            f.write(f"更新时间：{book.update_time}\n")
            f.write("=" * 50 + "\n\n")

            # 按章节顺序排序
            chapters.sort(key=lambda x: x.order)
            
            # 写入章节内容
            for chapter in chapters:
                f.write(f"{chapter.title}\n")
                f.write("-" * 30 + "\n")
                f.write(f"{chapter.content}\n\n")

        return file_path

    def _generate_epub_file(
        self, book: Book, chapters: List[Chapter], download_dir: Path
    ) -> Path:
        """生成EPUB文件

        Args:
            book: 小说信息
            chapters: 章节列表
            download_dir: 下载目录

        Returns:
            文件路径
        """
        try:
            from ebooklib import epub

            # 生成文件名
            safe_title = FileUtils.sanitize_filename(book.title)
            safe_author = FileUtils.sanitize_filename(book.author)
            filename = f"{safe_title}_{safe_author}.epub"
            file_path = download_dir / filename

            # 确保章节按顺序排列
            chapters.sort(key=lambda x: x.order or 0)
            
            # 创建EPUB书籍
            epub_book = epub.EpubBook()
            epub_book.set_title(book.title)
            epub_book.set_language("zh-CN")
            epub_book.add_author(book.author)

            # 添加章节
            chapters_epub = []
            for chapter in chapters:
                chapter_epub = epub.EpubHtml(
                    title=chapter.title,
                    file_name=f"chapter_{chapter.order}.xhtml",
                    content=(f"<h1>{chapter.title}</h1><p>{chapter.content}</p>"),
                )
                epub_book.add_item(chapter_epub)
                chapters_epub.append(chapter_epub)

            # 设置目录
            epub_book.toc = chapters_epub
            epub_book.spine = ["nav"] + chapters_epub

            # 生成EPUB文件
            epub.write_epub(str(file_path), epub_book)

            return file_path
        except ImportError:
            raise ValueError("生成EPUB文件需要安装ebooklib库")
        except Exception as e:
            raise ValueError(f"生成EPUB文件失败: {e}")

    def _get_searchable_sources(self) -> List[Source]:
        """获取所有可搜索的书源

        Returns:
            书源列表
        """
        sources = []
        rules_dir = Path(self.config.RULES_PATH)

        if not rules_dir.exists():
            print(f"<== 警告: 规则目录不存在: {rules_dir}")
            return sources

        for rule_file in rules_dir.glob("rule-*.json"):
            try:
                source = Source.from_rule_file(rule_file)
                if source.rule.get("search"):
                    sources.append(source)
            except Exception as e:
                print(f"<== 加载书源失败 {rule_file}: {e}")

        return sources

    def _sort_search_results(
        self, results: List[SearchResult], keyword: str
    ) -> List[SearchResult]:
        """排序搜索结果

        Args:
            results: 搜索结果列表
            keyword: 搜索关键词

        Returns:
            排序后的搜索结果
        """

        def score_result(result: SearchResult) -> int:
            score = 0
            title = result.title.lower()
            author = result.author.lower()
            keyword_lower = keyword.lower()

            # 标题完全匹配
            if keyword_lower in title:
                score += 100
            # 作者匹配
            if keyword_lower in author:
                score += 50
            # 标题开头匹配
            if title.startswith(keyword_lower):
                score += 30

            return score

        return sorted(results, key=score_result, reverse=True)
