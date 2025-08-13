import logging
import re
from typing import List, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class ContentValidator:
    """内容质量检测器"""

    def __init__(self):
        """初始化内容质量检测器"""
        # 广告模式列表
        self.ad_patterns = [
            r"一秒记住【.+?】",
            r"天才一秒记住.+?",
            r"天才壹秒記住.+?",
            r"看最新章节请到.+?",
            r"本书最新章节请到.+?",
            r"更新最快的.+?",
            r"手机用户请访问.+?",
            r"手机版阅读网址.+?",
            r"推荐都市大神.+?",
            r"\(本章完\)",
            r"章节错误.+?举报",
            r"内容严重缺失.+?举报",
            r"笔趣阁.+",
            r"新笔趣阁.+",
            r"香书小说.+",
            r"文学巴士.+",
            r"高速全文字在线阅读.+",
            r"天才一秒记住本站地址.+",
            r"手机用户请浏览阅读.+",
            r"天才壹秒記住.+為您提供精彩小說閱讀.+",
        ]

        # 无效内容模式
        self.invalid_patterns = [
            r"获取章节内容失败",
            r"无法获取章节内容",
            r"内容不存在",
            r"章节已删除",
            r"404",
            r"页面不存在",
        ]

        # 最小有效内容长度
        self.min_valid_length = settings.MIN_CONTENT_LENGTH

        # 最小章节长度
        self.min_chapter_length = settings.MIN_CHAPTER_LENGTH

    def validate_chapter_content(
        self, content: str, title: str = ""
    ) -> Tuple[bool, str]:
        """验证章节内容质量

        Args:
            content: 章节内容
            title: 章节标题

        Returns:
            (是否有效, 错误信息)
        """
        if not content or not isinstance(content, str):
            return False, "内容为空或格式错误"

        # 检查内容长度
        if len(content.strip()) < self.min_chapter_length:
            return False, f"内容过短 ({len(content.strip())} 字符)"

        # 检查是否包含无效内容
        for pattern in self.invalid_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"包含无效内容: {pattern}"

        # 检查广告内容比例
        ad_ratio = self._calculate_ad_ratio(content)
        if ad_ratio > 0.3:  # 广告内容超过30%
            return False, f"广告内容过多 ({ad_ratio:.1%})"

        # 检查内容结构
        if not self._has_valid_structure(content):
            return False, "内容结构不合理"

        return True, "内容质量良好"

    def _calculate_ad_ratio(self, content: str) -> float:
        """计算广告内容比例

        Args:
            content: 内容

        Returns:
            广告内容比例 (0-1)
        """
        if not content:
            return 0.0

        total_length = len(content)
        ad_length = 0

        for pattern in self.ad_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                ad_length += len(match)

        return ad_length / total_length if total_length > 0 else 0.0

    def _has_valid_structure(self, content: str) -> bool:
        """检查内容结构是否合理

        Args:
            content: 内容

        Returns:
            结构是否合理
        """
        if not content:
            return False

        # 检查段落数量
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        if len(paragraphs) < 2:
            return False

        # 检查是否有足够的中文字符
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
        if chinese_chars < 50:
            return False

        # 检查是否有合理的标点符号
        punctuation_count = len(re.findall(r'[，。！？；：""' "（）]", content))
        if punctuation_count < 5:
            return False

        return True

    def clean_content(self, content: str) -> str:
        """清理内容，移除广告和垃圾内容

        Args:
            content: 原始内容

        Returns:
            清理后的内容
        """
        if not content:
            return ""

        import html
        
        # 解码HTML实体
        content = html.unescape(content)

        # 移除广告内容
        for pattern in self.ad_patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)

        # 移除多余的空行
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        # 移除行首行尾空格
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        # 重新组合内容
        return "\n".join(lines)

    def extract_main_content(self, content: str) -> str:
        """提取主要内容

        Args:
            content: 原始内容

        Returns:
            主要内容
        """
        if not content:
            return ""

        import html
        
        # 先解码HTML实体
        content = html.unescape(content)

        # 移除HTML标签
        content = re.sub(r"<[^>]+>", "", content)

        # 移除多余的空白字符
        content = re.sub(r"\s+", " ", content)

        # 移除广告内容
        content = self.clean_content(content)

        return content.strip()

    def get_content_stats(self, content: str) -> dict:
        """获取内容统计信息

        Args:
            content: 内容

        Returns:
            统计信息字典
        """
        if not content:
            return {
                "length": 0,
                "chinese_chars": 0,
                "paragraphs": 0,
                "ad_ratio": 0.0,
                "punctuation_count": 0,
            }

        # 基本统计
        length = len(content)
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
        paragraphs = len([p for p in content.split("\n") if p.strip()])
        punctuation_count = len(re.findall(r'[，。！？；：""' "（）]", content))
        ad_ratio = self._calculate_ad_ratio(content)

        return {
            "length": length,
            "chinese_chars": chinese_chars,
            "paragraphs": paragraphs,
            "ad_ratio": ad_ratio,
            "punctuation_count": punctuation_count,
        }

    def is_high_quality_content(self, content: str) -> bool:
        """判断是否为高质量内容

        Args:
            content: 内容

        Returns:
            是否为高质量内容
        """
        is_valid, _ = self.validate_chapter_content(content)
        if not is_valid:
            return False

        stats = self.get_content_stats(content)

        # 高质量内容的标准
        return (
            stats["length"] >= self.min_valid_length
            and stats["chinese_chars"] >= 100
            and stats["paragraphs"] >= 3
            and stats["ad_ratio"] < 0.1  # 广告内容少于10%
            and stats["punctuation_count"] >= 10
        )


class ChapterValidator:
    """章节验证器"""

    def __init__(self):
        """初始化章节验证器"""
        self.content_validator = ContentValidator()

    def validate_chapter(
        self, chapter_title: str, chapter_content: str
    ) -> Tuple[bool, str]:
        """验证章节

        Args:
            chapter_title: 章节标题
            chapter_content: 章节内容

        Returns:
            (是否有效, 错误信息)
        """
        # 验证标题
        if not chapter_title or len(chapter_title.strip()) < 2:
            return False, "章节标题无效"

        # 验证内容
        return self.content_validator.validate_chapter_content(
            chapter_content, chapter_title
        )

    def get_chapter_quality_score(self, chapter_content: str) -> float:
        """获取章节质量评分

        Args:
            chapter_content: 章节内容

        Returns:
            质量评分 (0-1)
        """
        if not chapter_content:
            return 0.0

        stats = self.content_validator.get_content_stats(chapter_content)

        # 计算质量评分
        length_score = min(stats["length"] / 1000, 1.0)  # 长度评分
        chinese_score = min(stats["chinese_chars"] / 500, 1.0)  # 中文字符评分
        paragraph_score = min(stats["paragraphs"] / 10, 1.0)  # 段落评分
        ad_score = 1.0 - stats["ad_ratio"]  # 广告评分（反向）
        punctuation_score = min(stats["punctuation_count"] / 50, 1.0)  # 标点符号评分

        # 综合评分
        total_score = (
            length_score * 0.2
            + chinese_score * 0.3
            + paragraph_score * 0.2
            + ad_score * 0.2
            + punctuation_score * 0.1
        )

        return total_score

    def clean_content(self, content: str) -> str:
        """清理章节内容（委托给 ContentValidator）"""
        return self.content_validator.clean_content(content)
