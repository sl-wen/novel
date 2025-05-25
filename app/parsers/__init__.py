# 解析器模块初始化文件
from app.parsers.search_parser import SearchParser
from app.parsers.book_parser import BookParser
from app.parsers.toc_parser import TocParser
from app.parsers.chapter_parser import ChapterParser

__all__ = ['SearchParser', 'BookParser', 'TocParser', 'ChapterParser']