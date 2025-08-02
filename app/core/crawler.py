import asyncio
import time
from pathlib import Path
from typing import List

from app.core.config import settings
from app.core.source import Source
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.models.search import SearchResult
from app.parsers.book_parser import BookParser
from app.parsers.chapter_parser import ChapterParser
from app.parsers.search_parser import SearchParser
from app.parsers.toc_parser import TocParser


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

        # 获取章节内容
        source = Source(source_id)
        chapter_parser = ChapterParser(source)

        chapters = []
        for i, chapter_info in enumerate(toc):
            print(f"<== 正在获取第 {i+1}/{len(toc)} 章: {chapter_info.title}")
            chapter = await chapter_parser.parse(chapter_info.url)
            if chapter:
                chapters.append(chapter)

        print(f"<== 成功获取 {len(chapters)} 个章节内容")

        # 生成文件
        download_dir = Path(self.config.DOWNLOAD_PATH)
        file_path = self._generate_file(book, chapters, format, download_dir)

        end_time = time.time()
        print(f"<== 下载完成，耗时 {end_time - start_time:.2f} 秒")

        return file_path

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

    def _generate_file(
        self, book: Book, chapters: List[Chapter], format: str, download_dir: Path
    ) -> str:
        """生成下载文件

        Args:
            book: 小说信息
            chapters: 章节列表
            format: 文件格式
            download_dir: 下载目录

        Returns:
            文件路径
        """
        # 生成文件名
        safe_title = "".join(
            c for c in book.title if c.isalnum() or c in (" ", "-", "_")
        )
        safe_author = "".join(
            c for c in book.author if c.isalnum() or c in (" ", "-", "_")
        )
        filename = f"{safe_title}_{safe_author}.{format}"

        file_path = download_dir / filename

        if format == "txt":
            return self._generate_txt(book, chapters, file_path)
        elif format == "epub":
            return self._generate_epub(book, chapters, file_path)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def _generate_txt(
        self, book: Book, chapters: List[Chapter], file_path: Path
    ) -> str:
        """生成TXT文件

        Args:
            book: 小说信息
            chapters: 章节列表
            file_path: 文件路径

        Returns:
            文件路径
        """
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

            # 写入章节内容
            for chapter in chapters:
                f.write(f"{chapter.title}\n")
                f.write("-" * 30 + "\n")
                f.write(f"{chapter.content}\n\n")

        return str(file_path)

    def _generate_epub(
        self, book: Book, chapters: List[Chapter], file_path: Path
    ) -> str:
        """生成EPUB文件

        Args:
            book: 小说信息
            chapters: 章节列表
            file_path: 文件路径

        Returns:
            文件路径
        """
        try:
            from ebooklib import epub

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
                    file_name=f"chapter_{len(chapters_epub)}.xhtml",
                    content=(f"<h1>{chapter.title}</h1><p>{chapter.content}</p>"),
                )
                epub_book.add_item(chapter_epub)
                chapters_epub.append(chapter_epub)

            # 设置目录
            epub_book.toc = chapters_epub
            epub_book.spine = ["nav"] + chapters_epub

            # 生成EPUB文件
            epub.write_epub(str(file_path), epub_book)

            return str(file_path)
        except ImportError:
            raise ValueError("生成EPUB文件需要安装ebooklib库")
        except Exception as e:
            raise ValueError(f"生成EPUB文件失败: {e}")
