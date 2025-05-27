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
import logging
from ebooklib import epub
from weasyprint import HTML, CSS


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
            format: 下载格式，支持txt、epub、pdf
            
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
        sources = []
        rules_path = Path(self.config.RULES_PATH)
        if not rules_path.is_dir():
            logging.error(f"Rules path {rules_path} is not a directory.")
            return sources

        for rule_file in rules_path.glob("rule-*.json"):
            source_id = rule_file.stem.split("-")[-1]
            try:
                source = Source(source_id)
                # Ensure the source is searchable, if such a flag exists in rule
                # For now, we assume all rules define searchable sources
                # if source.rule.get("isSearchable", True): # Example check
                sources.append(source)
            except FileNotFoundError:
                logging.error(f"Rule file for source_id {source_id} not found at {rule_file}")
            except Exception as e:
                logging.error(f"Failed to load source from {rule_file}: {e}")
        
        if not sources:
            logging.warning(f"No searchable sources found in {rules_path}. Returning empty list.")

        return sources

    def _sort_search_results(self, results: List[SearchResult], keyword: str) -> List[SearchResult]:
        """排序搜索结果
        
        Args:
            results: 搜索结果列表
            keyword: 搜索关键词
            
        Returns:
            排序后的搜索结果列表
        """
        keyword_lower = keyword.lower()

        def sort_key(result: SearchResult):
            book_name_lower = result.bookName.lower()
            author_lower = result.author.lower() if result.author else ""

            if keyword_lower == book_name_lower:
                return (0, book_name_lower)  # Exact book name match
            if keyword_lower in book_name_lower:
                return (1, book_name_lower)  # Keyword in book name
            if author_lower and keyword_lower == author_lower:
                return (2, author_lower)  # Exact author match
            if author_lower and keyword_lower in author_lower:
                return (3, author_lower)  # Keyword in author
            return (4, book_name_lower)  # No match or partial match, sort by book name

        # Create a new sorted list instead of sorting in-place if results is used elsewhere
        # or if the original order of sub-priorities needs to be stable.
        # Python's sort is stable, so items with the same primary key will maintain their relative order.
        sorted_results = sorted(results, key=sort_key)
        return sorted_results
    
    async def _generate_file(self, book: Book, chapters: List[Chapter], format: str, download_dir: Path) -> str:
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
            return await asyncio.to_thread(self._generate_txt, book, chapters, file_path)
        elif format == "epub":
            return await asyncio.to_thread(self._generate_epub, book, chapters, file_path)
        elif format == "pdf":
            return await asyncio.to_thread(self._generate_pdf, book, chapters, file_path)
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
        try:
            epub_book = epub.EpubBook()

            # Set Metadata
            epub_book.set_identifier(f"{book.bookName}-{book.author}-{str(file_path.name)}")
            epub_book.set_title(book.bookName)
            epub_book.set_language('zh')  # Assuming Chinese, adjust if necessary
            if book.author:
                epub_book.add_author(book.author)
            epub_book.add_metadata('DC', 'description', book.intro if book.intro else 'No description available')

            # Sort chapters by order
            # Ensure chapter.order is not None, provide a default if it can be
            sorted_chapters = sorted(chapters, key=lambda c: c.order if c.order is not None else float('inf'))

            epub_chapters = []
            for i, chapter in enumerate(sorted_chapters):
                # Use chapter.order if available and unique, otherwise use index as fallback for file_name
                # Ensure chapter.order is an int if used directly in f-string formatting for numbers
                order_for_filename = chapter.order if chapter.order is not None else i
                
                # Ensure content is not None
                chapter_content = chapter.content if chapter.content is not None else ""
                
                epub_chap = epub.EpubHtml(
                    title=chapter.title,
                    file_name=f'chap_{order_for_filename:04d}.xhtml',
                    lang='zh'
                )
                epub_chap.content = f"<h1>{chapter.title}</h1><p>{chapter_content.replace(chr(10), '<br/>')}</p>"
                
                epub_book.add_item(epub_chap)
                epub_chapters.append(epub_chap)

            # Define Table of Contents (TOC)
            epub_book.toc = tuple(epub_chapters)

            # Add Navigation Files
            epub_book.add_item(epub.EpubNcx())
            epub_book.add_item(epub.EpubNav())

            # Define Spine
            # The 'nav' item is standard for the navigation document.
            # epub_book.spine = ['nav'] + epub_chapters # This order is typical
            # Let ebooklib handle the default spine or set it explicitly if needed after understanding its behavior.
            # For now, let's try with a common setup.
            spine_items = ['nav']
            spine_items.extend(epub_chapters)
            epub_book.spine = spine_items


            # Write the EPUB file
            epub.write_epub(str(file_path), epub_book, {})
            
            logging.info(f"EPUB file generated successfully at {file_path}")
            return str(file_path)

        except Exception as e:
            logging.error(f"Failed to generate EPUB file for {book.bookName} at {file_path}: {e}", exc_info=True)
            # Depending on requirements, either re-raise or return an error indicator
            # For now, returning a message, but raising might be better for the caller to handle.
            # raise e 
            return f"Error generating EPUB: {e}"

    def _generate_pdf(self, book: Book, chapters: List[Chapter], file_path: Path) -> str:
        """生成PDF文件
        
        Args:
            book: 小说详情
            chapters: 章节列表
            file_path: 文件路径
            
        Returns:
            文件路径
        """
        try:
            # Ensure chapters are sorted
            sorted_chapters = sorted(chapters, key=lambda c: c.order if c.order is not None else float('inf'))

            # Generate HTML Content
            html_content = f"<html><head><meta charset='UTF-8'><title>{book.bookName}</title>"
            # Basic CSS for better layout and potential font handling.
            # Using a generic sans-serif font for now.
            html_content += """
            <style>
                body { font-family: sans-serif; line-height: 1.6; }
                h1, h2, h3 { text-align: center; margin-bottom: 0.5em; }
                h1 { font-size: 2em; }
                h2 { font-size: 1.5em; color: #333; }
                h3 { font-size: 1.2em; color: #555; margin-top: 2em; }
                p { text-indent: 2em; margin-bottom: 1em; }
                .intro { font-style: italic; color: #666; }
                hr { border: 0; border-top: 1px solid #eee; margin: 2em 0; }
            </style>
            """
            html_content += "</head><body>"
            
            html_content += f"<h1>{book.bookName}</h1>"
            if book.author:
                html_content += f"<h2>{book.author}</h2>"
            
            if book.intro:
                intro_html = book.intro.replace(chr(10), "<br/>")
                html_content += f"<p class='intro'><strong>简介:</strong> {intro_html}</p><hr/>"

            for chapter in sorted_chapters:
                chap_title = chapter.title if chapter.title is not None else "Untitled Chapter"
                chap_content = chapter.content if chapter.content is not None else ""
                
                html_content += f"<h3>{chap_title}</h3>"
                # Replace newlines with <br/> for HTML display
                content_html = chap_content.replace(chr(10), "<br/>")
                html_content += f"<p>{content_html}</p><hr/>"
            
            html_content += "</body></html>"

            # Convert HTML to PDF
            html_doc = HTML(string=html_content)
            
            # Attempt without custom fonts first as per instructions.
            # If specific character sets (e.g., CJK) are an issue, stylesheets with font declarations would be needed.
            # For example:
            # cjk_css = CSS(string='''
            #     @font-face { font-family: "Noto Sans CJK SC"; src: url("https://fonts.gstatic.com/s/notosanscjksc/v27/ নজরpVZsdPWs3hvX7q1wYdDBGMmQ.otf"); } 
            #     body { font-family: "Noto Sans CJK SC", sans-serif; }
            # ''')
            # html_doc.write_pdf(str(file_path), stylesheets=[cjk_css])
            html_doc.write_pdf(str(file_path))
            
            logging.info(f"PDF file generated successfully at {file_path}")
            return str(file_path)

        except Exception as e:
            logging.error(f"Failed to generate PDF file for {book.bookName} at {file_path}: {e}", exc_info=True)
            return f"Error generating PDF: {e}"