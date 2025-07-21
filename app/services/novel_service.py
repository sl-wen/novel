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

        # 过滤和排序搜索结果
        filtered_results = self._filter_and_sort_results(all_results, keyword)

        end_time = time.time()
        logger.info(f"搜索完成: 原始结果 {len(all_results)} 条，过滤后 {len(filtered_results)} 条，耗时 {end_time - start_time:.2f} 秒")

        return filtered_results
    
    def _filter_and_sort_results(self, results: List[SearchResult], keyword: str) -> List[SearchResult]:
        """过滤和排序搜索结果
        
        Args:
            results: 原始搜索结果
            keyword: 搜索关键词
            
        Returns:
            过滤和排序后的结果
        """
        if not results:
            logger.info("没有原始搜索结果")
            return results
            
        logger.info(f"开始过滤 {len(results)} 条原始搜索结果")
        
        valid_results = []
        filtered_count = 0
        low_relevance_count = 0
        
        for i, result in enumerate(results):
            logger.debug(f"处理结果 {i+1}: 书名='{result.bookName}', 作者='{result.author}', URL='{result.url}'")
            
            # 1. 过滤明显异常的结果
            if not self._is_valid_result(result):
                filtered_count += 1
                logger.debug(f"过滤无效结果: {result.bookName} - {result.url}")
                continue
                
            # 2. 计算相关性得分
            relevance_score = self._calculate_relevance_score(result, keyword)
            logger.debug(f"结果 '{result.bookName}' 的相关性得分: {relevance_score:.3f}")
            
            # 3. 只保留相关性得分大于阈值的结果 (进一步降低阈值)
            if relevance_score > 0.01:  # 进一步降低阈值从0.05到0.01
                # 将得分存储在结果中用于排序
                result.score = relevance_score
                valid_results.append(result)
                logger.debug(f"保留结果: {result.bookName} (得分: {relevance_score:.3f})")
            else:
                low_relevance_count += 1
                logger.debug(f"过滤低相关性结果: {result.bookName} (得分: {relevance_score:.3f})")
        
        logger.info(f"结果过滤统计 - 原始: {len(results)}, 无效: {filtered_count}, 低相关性: {low_relevance_count}, 保留: {len(valid_results)}")
        
        # 4. 按相关性得分降序排序
        valid_results.sort(key=lambda x: x.score or 0, reverse=True)
        
        # 5. 限制返回结果数量
        final_results = valid_results[:settings.MAX_SEARCH_RESULTS]
        logger.info(f"最终返回 {len(final_results)} 条结果")
        
        return final_results
    
    def _is_valid_result(self, result: SearchResult) -> bool:
        """判断搜索结果是否有效
        
        Args:
            result: 搜索结果
            
        Returns:
            是否为有效结果
        """
        # 检查书名是否有效
        if not result.bookName or len(result.bookName.strip()) < 1:
            logger.debug(f"书名无效: '{result.bookName}'")
            return False
            
        # 暂时禁用乱码检测，因为逻辑有问题
        # TODO: 改进乱码检测逻辑
        # invalid_chars = result.bookName.count('?') + result.bookName.count('')
        # if invalid_chars > len(result.bookName) * 0.7:
        #     logger.debug(f"包含过多乱码字符: '{result.bookName}' (乱码字符比例: {invalid_chars/len(result.bookName):.1%})")
        #     return False
            
        # 检查URL是否有效
        if not result.url:
            logger.debug(f"URL为空: '{result.bookName}'")
            return False
        
        # 检查URL格式
        url_lower = result.url.lower()
        if not any(indicator in url_lower for indicator in ['http', '.com', '.net', '.org', '.cn', '/']):
            logger.debug(f"URL格式无效: '{result.url}'")
            return False
            
        return True
    
    def _calculate_relevance_score(self, result: SearchResult, keyword: str) -> float:
        """计算搜索结果的相关性得分 (改进版)
        
        Args:
            result: 搜索结果
            keyword: 搜索关键词
            
        Returns:
            相关性得分 (0-1之间)
        """
        score = 0.0
        keyword_clean = self._clean_text(keyword)
        
        # 1. 书名匹配得分 (权重: 0.6)
        if result.bookName:
            book_name_clean = self._clean_text(result.bookName)
            
            # 完全匹配 - 最高分
            if keyword_clean == book_name_clean:
                score += 0.6
            # 包含关键词 - 高分
            elif keyword_clean in book_name_clean:
                # 根据匹配长度给分
                match_ratio = len(keyword_clean) / len(book_name_clean)
                score += 0.4 + (0.2 * match_ratio)
            # 关键词包含在书名中
            elif book_name_clean in keyword_clean:
                score += 0.3
            # 部分匹配 - 使用相似度算法
            else:
                similarity = self._calculate_similarity(keyword_clean, book_name_clean)
                if similarity > 0.3:  # 只有相似度较高才给分
                    score += similarity * 0.4
        
        # 2. 作者匹配得分 (权重: 0.3)
        if result.author:
            author_clean = self._clean_text(result.author)
            
            # 完全匹配
            if keyword_clean == author_clean:
                score += 0.3
            # 包含关键词
            elif keyword_clean in author_clean or author_clean in keyword_clean:
                score += 0.2
            # 部分匹配
            else:
                similarity = self._calculate_similarity(keyword_clean, author_clean)
                if similarity > 0.5:  # 作者匹配要求更高相似度
                    score += similarity * 0.15
        
        # 3. 分类匹配得分 (权重: 0.1)
        if result.category:
            category_clean = self._clean_text(result.category)
            if keyword_clean in category_clean:
                score += 0.1
        
        # 4. 额外加分项
        # 如果书名很短且匹配度高，给额外分数
        if result.bookName and len(self._clean_text(result.bookName)) <= 6:
            if keyword_clean in self._clean_text(result.bookName):
                score += 0.1
        
        return min(score, 1.0)  # 确保得分不超过1
    
    def _clean_text(self, text: str) -> str:
        """清理文本，用于匹配比较
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 转换为小写
        text = text.lower().strip()
        
        # 移除常见的标点符号和空格
        import re
        text = re.sub(r'[，。！？；：""''（）【】《》\s\-_\[\]()]+', '', text, flags=re.UNICODE)
        
        return text
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算两个字符串的相似度 (改进版)
        
        Args:
            str1: 字符串1
            str2: 字符串2
            
        Returns:
            相似度 (0-1之间)
        """
        if not str1 or not str2:
            return 0.0
        
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        # 1. 如果完全相等
        if str1 == str2:
            return 1.0
        
        # 2. 如果一个字符串包含另一个
        if str1 in str2 or str2 in str1:
            return 0.8
        
        # 3. 计算编辑距离相似度 (简化版Levenshtein距离)
        edit_distance = self._levenshtein_distance(str1, str2)
        max_len = max(len(str1), len(str2))
        
        if max_len == 0:
            return 0.0
        
        edit_similarity = 1.0 - (edit_distance / max_len)
        
        # 4. 计算字符集交集相似度
        set1 = set(str1)
        set2 = set(str2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        jaccard_similarity = intersection / union if union > 0 else 0
        
        # 5. 综合相似度 (编辑距离权重更高)
        final_similarity = edit_similarity * 0.7 + jaccard_similarity * 0.3
        
        return max(0.0, min(1.0, final_similarity))
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串的编辑距离
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            编辑距离
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

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

        # 预处理所有章节内容和书籍信息，确保不是None
        safe = lambda v, d: v if isinstance(v, str) and v.strip() else d
        book.bookName = safe(getattr(book, 'bookName', None), '未知书名')
        book.author = safe(getattr(book, 'author', None), '未知作者')
        book.intro = safe(getattr(book, 'intro', None), '')
        book.category = safe(getattr(book, 'category', None), '')
        book.latestChapter = safe(getattr(book, 'latestChapter', None), '')
        book.lastUpdateTime = safe(getattr(book, 'lastUpdateTime', None), '')
        book.status = safe(getattr(book, 'status', None), '')
        book.wordCount = safe(getattr(book, 'wordCount', None), '')
        for chapter in chapters:
            chapter.title = safe(getattr(chapter, 'title', None), '无标题')
            chapter.content = safe(getattr(chapter, 'content', None), '（本章获取失败）')

        if format == "txt":
            return self._generate_txt(book, chapters, file_path)
        elif format == "epub":
            return self._generate_epub(book, chapters, file_path)
        elif format == "pdf":
            return self._generate_pdf(book, chapters, file_path)
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

    def _generate_epub(self, book: Book, chapters: List[Chapter], file_path: Path) -> Path:
        """生成EPUB文件

        Args:
            book: 小说详情
            chapters: 章节列表
            file_path: 文件路径

        Returns:
            文件路径
        """
        try:
            from ebooklib import epub
            
            chapters.sort(key=lambda x: x.order)
            
            # 创建EPUB书籍
            epub_book = epub.EpubBook()
            
            # 设置元数据
            epub_book.set_identifier('novel_' + str(hash(book.bookName)))
            epub_book.set_title(book.bookName or "未知书名")
            epub_book.set_language('zh')
            
            if book.author:
                epub_book.add_author(book.author)
                
            if book.intro:
                epub_book.add_metadata('DC', 'description', book.intro)
            
            # 添加章节
            epub_chapters = []
            for chapter in chapters:
                epub_chapter = epub.EpubHtml(
                    title=chapter.title,
                    file_name=f"chapter_{chapter.order}.xhtml"
                )
                epub_chapter.content = f"""
                <html xmlns="http://www.w3.org/1999/xhtml">
                <head><title>{chapter.title}</title></head>
                <body>
                <h1>{chapter.title}</h1>
                <div>{chapter.content.replace(chr(10), '<br/>')}</div>
                </body>
                </html>
                """
                epub_book.add_item(epub_chapter)
                epub_chapters.append(epub_chapter)
            
            # 添加默认的NCX和Nav文件
            epub_book.add_item(epub.EpubNcx())
            epub_book.add_item(epub.EpubNav())
            
            # 设置spine
            epub_book.spine = ['nav'] + epub_chapters
            
            # 写入文件
            epub.write_epub(str(file_path), epub_book, {})
            logger.info(f"EPUB文件生成成功: {file_path}")
            return file_path
            
        except ImportError:
            logger.warning("ebooklib未安装，使用TXT格式代替EPUB")
            return self._generate_txt(book, chapters, file_path.with_suffix(".txt"))
        except Exception as e:
            logger.error(f"生成EPUB文件失败: {str(e)}")
            return self._generate_txt(book, chapters, file_path.with_suffix(".txt"))

    def _generate_pdf(self, book: Book, chapters: List[Chapter], file_path: Path) -> Path:
        """生成PDF文件

        Args:
            book: 小说详情
            chapters: 章节列表
            file_path: 文件路径

        Returns:
            文件路径
        """
        try:
            from weasyprint import HTML, CSS
            
            chapters.sort(key=lambda x: x.order)
            
            # 生成HTML内容
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{book.bookName}</title>
                <style>
                    body {{ font-family: "Microsoft YaHei", SimSun, serif; font-size: 14px; line-height: 1.6; }}
                    h1 {{ color: #333; text-align: center; }}
                    h2 {{ color: #666; margin-top: 2em; }}
                    .book-info {{ text-align: center; margin-bottom: 3em; }}
                    .chapter {{ page-break-before: auto; margin-bottom: 2em; }}
                    .chapter-title {{ font-size: 18px; font-weight: bold; margin-bottom: 1em; }}
                    .chapter-content {{ text-indent: 2em; }}
                </style>
            </head>
            <body>
                <div class="book-info">
                    <h1>{book.bookName or "未知书名"}</h1>
                    <p>作者：{book.author or "未知作者"}</p>
                    <p>分类：{book.category or "未分类"}</p>
                    {f'<p>简介：{book.intro}</p>' if book.intro else ''}
                </div>
            """
            
            for chapter in chapters:
                html_content += f"""
                <div class="chapter">
                    <div class="chapter-title">{chapter.title}</div>
                    <div class="chapter-content">{chapter.content.replace(chr(10), '</p><p>')}</div>
                </div>
                """
            
            html_content += "</body></html>"
            
            # 生成PDF
            html_doc = HTML(string=html_content)
            html_doc.write_pdf(str(file_path))
            
            logger.info(f"PDF文件生成成功: {file_path}")
            return file_path
            
        except ImportError:
            logger.warning("weasyprint未安装，使用TXT格式代替PDF")
            return self._generate_txt(book, chapters, file_path.with_suffix(".txt"))
        except Exception as e:
            logger.error(f"生成PDF文件失败: {str(e)}")
            return self._generate_txt(book, chapters, file_path.with_suffix(".txt"))

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