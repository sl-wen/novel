import asyncio
import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

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

logger = logging.getLogger(__name__)

class NovelService:
    """小说服务类，提供小说搜索、获取详情、获取目录和下载功能"""

    def __init__(self):
        """初始化服务"""
        self.sources = {}
        self._load_sources()

    def _load_sources(self):
        """加载所有书源，只加载本地规则目录下的规则文件"""
        rules_path = Path(settings.RULES_PATH)
        if not rules_path.exists():
            logger.warning(f"本地书源规则目录不存在: {rules_path}")
            return

        for rule_file in rules_path.glob("rule-*.json"):
            try:
                with open(rule_file, 'r', encoding='utf-8') as f:
                    rule = json.load(f)
                    if rule.get('enabled', True):
                        source_id_str = rule_file.stem.replace("rule-", "")
                        try:
                            source_id = int(source_id_str)
                            self.sources[source_id] = Source(source_id, rule_data=rule)
                            logger.info(f"成功加载本地规则: {rule_file.name} (ID: {source_id})")
                        except ValueError:
                            logger.error(f"无效的规则文件名格式，无法提取ID: {rule_file.name}")

            except Exception as e:
                logger.error(f"加载本地书源规则失败: {rule_file}, 错误: {str(e)}")

    def _convert_rule_format(self, rule_data: dict) -> dict:
        """转换规则格式，将so-novel的规则格式转换为当前项目的格式

        Args:
            rule_data: so-novel项目的规则数据

        Returns:
            转换后的规则数据
        """
        converted_rule = {
            "id": rule_data.get("id", 0),
            "name": rule_data.get("name", ""),
            "url": rule_data.get("url", ""),
            "enabled": True,
            "type": rule_data.get("type", "html"),
            "language": rule_data.get("language", "zh_CN")
        }

        if "search" in rule_data:
            converted_rule["search"] = {
                "url": rule_data["search"].get("url", ""),
                "method": rule_data["search"].get("method", "get"),
                "data": rule_data["search"].get("data", "{}"),
                "list": rule_data["search"].get("result", ""),
                "name": rule_data["search"].get("bookName", ""),
                "author": rule_data["search"].get("author", ""),
                "category": rule_data["search"].get("category", ""),
                "latest": rule_data["search"].get("latestChapter", ""),
                "update": rule_data["search"].get("lastUpdateTime", ""),
                "status": rule_data["search"].get("status", ""),
                "word_count": rule_data["search"].get("wordCount", "")
            }

        if "book" in rule_data:
            converted_rule["book"] = {
                "name": rule_data["book"].get("bookName", ""),
                "author": rule_data["book"].get("author", ""),
                "intro": rule_data["book"].get("intro", ""),
                "category": rule_data["book"].get("category", ""),
                "cover": rule_data["book"].get("coverUrl", ""),
                "latest": rule_data["book"].get("latestChapter", ""),
                "update": rule_data["book"].get("lastUpdateTime", ""),
                "status": rule_data["book"].get("status", ""),
                "word_count": rule_data["book"].get("wordCount", "")
            }

        if "toc" in rule_data:
            converted_rule["toc"] = {
                "list": rule_data["toc"].get("item", ""),
                "title": rule_data["toc"].get("title", ""),
                "url": rule_data["toc"].get("url", ""),
                "has_pages": rule_data["toc"].get("pagination", False),
                "next_page": rule_data["toc"].get("nextPage", "")
            }

        if "chapter" in rule_data:
            converted_rule["chapter"] = {
                "title": rule_data["chapter"].get("title", ""),
                "content": rule_data["chapter"].get("content", ""),
                "ad_patterns": rule_data["chapter"].get("filterTxt", "").split("|") if rule_data["chapter"].get("filterTxt") else []
            }

        return converted_rule

    async def search(self, keyword: str) -> List[SearchResult]:
        """搜索小说

        Args:
            keyword: 搜索关键词（书名或作者名）

        Returns:
            搜索结果列表
        """
        logger.info(f"开始搜索: {keyword}")
        start_time = time.time()

        tasks = []
        searchable_sources = [source for source in self.sources.values() if source.rule.get("search")]

        if not searchable_sources:
            logger.warning("没有找到可用的搜索书源规则")
            return []

        async def search_single_source(source: Source, keyword: str):
            """搜索单个书源并处理结果或异常"""
            try:
                search_parser = SearchParser(source)
                results = await search_parser.parse(keyword)
                logger.info(f"书源 {source.rule.get('name', source.id)} 搜索成功，找到 {len(results)} 条结果")
                return results
            except Exception as e:
                logger.error(f"书源 {source.rule.get('name', source.id)} 搜索失败: {str(e)}")
                return [] # 搜索失败时返回空列表

        for source in searchable_sources:
            tasks.append(search_single_source(source, keyword))

        results_from_sources = await asyncio.gather(*tasks)

        all_results = []
        for source_results in results_from_sources:
            all_results.extend(source_results)

        all_results.sort(key=lambda x: x.bookName)

        end_time = time.time()
        logger.info(f"搜索完成: 找到 {len(all_results)} 条结果，耗时 {end_time - start_time:.2f} 秒")

        return all_results

    async def get_book_detail(self, url: str, source_id: int) -> Book:
        """获取小说详情

        Args:
            url: 小说详情页URL
            source_id: 书源ID

        Returns:
            小说详情
        """
        source = self.sources.get(source_id)
        if not source:
            raise ValueError(f"无效的书源ID: {source_id}")
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
        source = self.sources.get(source_id)
        if not source:
            raise ValueError(f"无效的书源ID: {source_id}")
        toc_parser = TocParser(source)
        return await toc_parser.parse(url, start, end or float('inf'))

    async def download(self, url: str, source_id: int, format: str = "txt") -> str:
        """下载小说

        Args:
            url: 小说详情页URL
            source_id: 书源ID
            format: 下载格式，支持txt、epub、pdf

        Returns:
            下载文件路径
        """
        source = self.sources.get(source_id)
        if not source:
            raise ValueError(f"无效的书源ID: {source_id}")

        book = await self.get_book_detail(url, source_id)

        toc = await self.get_toc(url, source_id)

        book_folder_name = FileUtils.sanitize_filename(f"{book.bookName} ({book.author})")
        download_dir = Path(settings.DOWNLOAD_PATH) / book_folder_name
        os.makedirs(download_dir, exist_ok=True)

        chapter_parser = ChapterParser(source)

        tasks = []
        for chapter in toc:
            tasks.append(chapter_parser.parse(chapter.url, chapter.title, chapter.order))

        chapters = await asyncio.gather(*tasks)

        file_path = self._generate_file(book, chapters, format, download_dir)

        return str(file_path)

    def _generate_file(self, book: Book, chapters: List[Chapter], format: str, download_dir: Path) -> Path:
        """生成文件

        Args:
            book: 小说详情
            chapters: 章节列表
            format: 下载格式
            download_dir: 下载目录

        Returns:
            文件路径
        """
        filename = f"{FileUtils.sanitize_filename(book.bookName)}_{FileUtils.sanitize_filename(book.author)}.{format}"
        file_path = download_dir / filename

        if format == "txt":
            return self._generate_txt(book, chapters, file_path)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def _generate_txt(self, book: Book, chapters: List[Chapter], file_path: Path) -> Path:
        """生成TXT文件

        Args:
            book: 小说详情
            chapters: 章节列表
            file_path: 文件路径

        Returns:
            文件路径
        """
        chapters.sort(key=lambda x: x.order)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"书名: {book.bookName}\n")
            f.write(f"作者: {book.author}\n")
            f.write(f"简介: {book.intro}\n")
            f.write(f"分类: {book.category}\n")
            f.write(f"最新章节: {book.latestChapter}\n")
            f.write(f"更新时间: {book.lastUpdateTime}\n")
            f.write(f"状态: {book.status}\n")
            f.write(f"字数: {book.wordCount}\n")
            f.write("\n" + "="*50 + "\n\n")

            for chapter in chapters:
                f.write(f"\n\n{chapter.title}\n\n")
                f.write(chapter.content)

        logger.info(f"TXT文件生成成功: {file_path}")
        return file_path

    async def get_sources(self):
        """获取所有可用书源

        Returns:
            书源列表
        """
        sources_list = []
        for source_id, source in self.sources.items():
            sources_list.append({
                "id": source_id,
                "rule": source.rule
            })
        return sources_list