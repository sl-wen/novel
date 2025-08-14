import re
import logging
from typing import List, Optional
from app.models.chapter import ChapterInfo, Chapter

logger = logging.getLogger(__name__)


class ChapterFormatter:
    """章节标题格式化工具，用于处理缺少章节序号的小说"""
    
    def __init__(self):
        # 常见的章节标题模式
        self.chapter_patterns = [
            r'^第[一二三四五六七八九十百千万0-9]+章',
            r'^第[0-9]+话',
            r'^第[0-9]+节',
            r'^Chapter\s*[0-9]+',
            r'^[0-9]+\.',
            r'^\([0-9]+\)',
            r'^【[0-9]+】',
        ]
        
        # 数字转换映射
        self.chinese_numbers = {
            '零': '0', '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
            '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
            '百': '100', '千': '1000', '万': '10000'
        }
    
    def format_chapter_list(self, chapters: List[ChapterInfo], 
                          add_chapter_numbers: bool = True,
                          chapter_prefix: str = "第",
                          chapter_suffix: str = "章") -> List[ChapterInfo]:
        """格式化章节列表，为缺少序号的章节添加序号
        
        Args:
            chapters: 章节信息列表
            add_chapter_numbers: 是否添加章节序号
            chapter_prefix: 章节序号前缀
            chapter_suffix: 章节序号后缀
            
        Returns:
            格式化后的章节列表
        """
        if not chapters:
            return chapters
        
        logger.info(f"开始格式化 {len(chapters)} 个章节标题")
        
        formatted_chapters = []
        
        for i, chapter in enumerate(chapters):
            formatted_chapter = chapter.copy()
            
            # 检查是否已有章节序号
            if add_chapter_numbers and not self._has_chapter_number(chapter.title):
                # 添加章节序号
                chapter_number = i + 1
                new_title = f"{chapter_prefix}{chapter_number}{chapter_suffix} {chapter.title}".strip()
                formatted_chapter.title = new_title
                logger.debug(f"格式化章节标题: '{chapter.title}' -> '{new_title}'")
            else:
                # 清理现有标题
                formatted_chapter.title = self._clean_title(chapter.title)
            
            formatted_chapters.append(formatted_chapter)
        
        logger.info(f"章节标题格式化完成")
        return formatted_chapters
    
    def format_chapter_content(self, chapter: Chapter,
                             add_chapter_number: bool = True,
                             chapter_prefix: str = "第",
                             chapter_suffix: str = "章") -> Chapter:
        """格式化单个章节内容，添加章节标题
        
        Args:
            chapter: 章节对象
            add_chapter_number: 是否添加章节序号
            chapter_prefix: 章节序号前缀
            chapter_suffix: 章节序号后缀
            
        Returns:
            格式化后的章节对象
        """
        formatted_chapter = chapter.copy()
        
        # 格式化标题
        if add_chapter_number and not self._has_chapter_number(chapter.title):
            chapter_number = chapter.order if chapter.order > 0 else 1
            new_title = f"{chapter_prefix}{chapter_number}{chapter_suffix} {chapter.title}".strip()
            formatted_chapter.title = new_title
        else:
            formatted_chapter.title = self._clean_title(chapter.title)
        
        # 在内容开头添加章节标题（如果内容中没有）
        content = chapter.content.strip()
        if content and not content.startswith(formatted_chapter.title):
            formatted_chapter.content = f"{formatted_chapter.title}\n\n{content}"
        
        return formatted_chapter
    
    def _has_chapter_number(self, title: str) -> bool:
        """检查标题是否已包含章节序号
        
        Args:
            title: 章节标题
            
        Returns:
            是否包含章节序号
        """
        if not title:
            return False
        
        for pattern in self.chapter_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        
        return False
    
    def _clean_title(self, title: str) -> str:
        """清理章节标题
        
        Args:
            title: 原始标题
            
        Returns:
            清理后的标题
        """
        if not title:
            return "未命名章节"
        
        # 移除多余的空白字符
        title = re.sub(r'\s+', ' ', title.strip())
        
        # 移除常见的无用前后缀
        useless_patterns = [
            r'^正文\s*',  # 移除"正文"前缀
            r'\s*正文$',  # 移除"正文"后缀
            r'^\d+\.\s*',  # 移除数字序号前缀（如果不是章节格式）
            r'^\([0-9]+\)\s*',  # 移除括号序号
            r'^【.*?】\s*',  # 移除方括号标记
            r'\s*\(完\)$',  # 移除"(完)"后缀
            r'\s*\[完\]$',  # 移除"[完]"后缀
        ]
        
        for pattern in useless_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # 如果清理后标题为空，使用默认标题
        if not title.strip():
            title = "未命名章节"
        
        return title.strip()
    
    def detect_chapter_numbering_style(self, chapters: List[ChapterInfo]) -> dict:
        """检测章节编号风格
        
        Args:
            chapters: 章节列表
            
        Returns:
            检测结果字典，包含编号风格信息
        """
        if not chapters:
            return {"has_numbering": False, "style": "none", "pattern": None}
        
        # 统计各种编号模式的出现次数
        pattern_counts = {}
        
        for chapter in chapters[:20]:  # 只检查前20章
            title = chapter.title
            for pattern in self.chapter_patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                    break
        
        # 找出最常见的模式
        if pattern_counts:
            most_common_pattern = max(pattern_counts.items(), key=lambda x: x[1])
            if most_common_pattern[1] >= len(chapters) * 0.5:  # 至少50%的章节使用该模式
                return {
                    "has_numbering": True,
                    "style": "existing",
                    "pattern": most_common_pattern[0],
                    "coverage": most_common_pattern[1] / len(chapters)
                }
        
        return {
            "has_numbering": False,
            "style": "none",
            "pattern": None,
            "coverage": 0
        }
    
    def suggest_formatting_options(self, chapters: List[ChapterInfo]) -> dict:
        """建议格式化选项
        
        Args:
            chapters: 章节列表
            
        Returns:
            建议的格式化选项
        """
        if not chapters:
            return {"add_numbers": False, "prefix": "第", "suffix": "章"}
        
        numbering_info = self.detect_chapter_numbering_style(chapters)
        
        # 如果大部分章节没有编号，建议添加
        if not numbering_info["has_numbering"]:
            return {
                "add_numbers": True,
                "prefix": "第",
                "suffix": "章",
                "reason": "检测到大部分章节缺少序号"
            }
        else:
            return {
                "add_numbers": False,
                "prefix": "第",
                "suffix": "章",
                "reason": f"检测到现有编号模式: {numbering_info['pattern']}"
            }
    
    def batch_format_for_download(self, chapters: List[Chapter],
                                 format_options: Optional[dict] = None) -> List[Chapter]:
        """批量格式化章节用于下载
        
        Args:
            chapters: 章节列表
            format_options: 格式化选项
            
        Returns:
            格式化后的章节列表
        """
        if not chapters:
            return chapters
        
        # 使用默认选项或提供的选项
        options = format_options or {"add_numbers": True, "prefix": "第", "suffix": "章"}
        
        logger.info(f"批量格式化 {len(chapters)} 个章节用于下载")
        
        formatted_chapters = []
        
        for chapter in chapters:
            formatted_chapter = self.format_chapter_content(
                chapter,
                add_chapter_number=options.get("add_numbers", True),
                chapter_prefix=options.get("prefix", "第"),
                chapter_suffix=options.get("suffix", "章")
            )
            formatted_chapters.append(formatted_chapter)
        
        logger.info("批量格式化完成")
        return formatted_chapters


# 全局实例
chapter_formatter = ChapterFormatter()