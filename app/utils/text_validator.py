import re
import unicodedata
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class TextValidator:
    """文本验证器 - 提供乱码检测、文本质量评估等功能"""
    
    # 常见的乱码字符模式
    GARBLED_PATTERNS = [
        r'[？]{2,}',  # 连续问号
        r'[□]{2,}',  # 连续方框
        r'[�]{1,}',  # Unicode替换字符
        r'[ï¿½]{1,}',  # UTF-8解码错误
        r'[????]{2,}',  # 其他乱码模式
    ]
    
    # 无意义的标题模式
    MEANINGLESS_PATTERNS = [
        r'^[0-9\s\-_\.]+$',  # 纯数字、空格、符号
        r'^[a-zA-Z\s\-_\.]{1,3}$',  # 过短的英文
        r'^[\W_]+$',  # 纯符号
        r'^测试.*',  # 测试内容
        r'^demo.*',  # 演示内容
        r'^sample.*',  # 示例内容
    ]
    
    # 高质量中文字符范围
    CJK_RANGES = [
        (0x4E00, 0x9FFF),  # CJK统一汉字
        (0x3400, 0x4DBF),  # CJK扩展A
        (0x20000, 0x2A6DF),  # CJK扩展B
        (0x2A700, 0x2B73F),  # CJK扩展C
        (0x2B740, 0x2B81F),  # CJK扩展D
        (0x2B820, 0x2CEAF),  # CJK扩展E
    ]
    
    @classmethod
    def is_cjk_character(cls, char: str) -> bool:
        """判断字符是否为中日韩字符"""
        if not char:
            return False
        
        code_point = ord(char)
        return any(start <= code_point <= end for start, end in cls.CJK_RANGES)
    
    @classmethod
    def calculate_text_quality_score(cls, text: str) -> float:
        """
        计算文本质量得分 (0-1)
        
        Args:
            text: 待评估的文本
            
        Returns:
            质量得分，1.0为最高质量，0.0为最低质量
        """
        if not text or not text.strip():
            return 0.0
        
        text = text.strip()
        score = 1.0
        
        # 1. 检查乱码字符 (权重: -0.4)
        garbled_ratio = cls._calculate_garbled_ratio(text)
        if garbled_ratio > 0:
            score -= min(0.4, garbled_ratio * 0.8)
        
        # 2. 检查字符多样性 (权重: -0.2)
        diversity_score = cls._calculate_character_diversity(text)
        if diversity_score < 0.3:
            score -= 0.2 * (0.3 - diversity_score) / 0.3
        
        # 3. 检查长度合理性 (权重: -0.1)
        length_score = cls._calculate_length_score(text)
        score -= 0.1 * (1.0 - length_score)
        
        # 4. 检查无意义模式 (权重: -0.3)
        if cls._has_meaningless_pattern(text):
            score -= 0.3
        
        return max(0.0, score)
    
    @classmethod
    def _calculate_garbled_ratio(cls, text: str) -> float:
        """计算乱码字符比例"""
        if not text:
            return 0.0
        
        garbled_count = 0
        total_chars = len(text)
        
        # 检查乱码模式
        for pattern in cls.GARBLED_PATTERNS:
            matches = re.findall(pattern, text)
            garbled_count += sum(len(match) for match in matches)
        
        # 检查不可显示字符
        for char in text:
            if unicodedata.category(char) in ['Cc', 'Cf', 'Co', 'Cs']:  # 控制字符等
                garbled_count += 1
        
        return garbled_count / total_chars if total_chars > 0 else 0.0
    
    @classmethod
    def _calculate_character_diversity(cls, text: str) -> float:
        """计算字符多样性得分"""
        if not text:
            return 0.0
        
        unique_chars = len(set(text))
        total_chars = len(text)
        
        if total_chars == 0:
            return 0.0
        
        # 多样性比例，但要考虑文本长度
        diversity_ratio = unique_chars / total_chars
        
        # 对于较短的文本，适当降低多样性要求
        if total_chars < 10:
            diversity_ratio *= 1.2  # 给短文本一些容忍度
        
        return min(1.0, diversity_ratio)
    
    @classmethod
    def _calculate_length_score(cls, text: str) -> float:
        """计算长度合理性得分"""
        length = len(text.strip())
        
        if length == 0:
            return 0.0
        elif length < 2:
            return 0.3  # 太短
        elif length < 5:
            return 0.6  # 较短但可接受
        elif length <= 50:
            return 1.0  # 理想长度
        elif length <= 100:
            return 0.9  # 稍长但可接受
        else:
            return 0.8  # 很长但仍可接受
    
    @classmethod
    def _has_meaningless_pattern(cls, text: str) -> bool:
        """检查是否包含无意义模式"""
        text_lower = text.lower().strip()
        
        for pattern in cls.MEANINGLESS_PATTERNS:
            if re.match(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def is_valid_title(cls, title: str, min_quality_score: float = 0.6) -> Tuple[bool, float, str]:
        """
        验证标题是否有效
        
        Args:
            title: 待验证的标题
            min_quality_score: 最低质量得分要求
            
        Returns:
            (是否有效, 质量得分, 失败原因)
        """
        if not title or not title.strip():
            return False, 0.0, "标题为空"
        
        title = title.strip()
        quality_score = cls.calculate_text_quality_score(title)
        
        if quality_score < min_quality_score:
            reason = cls._get_quality_issue_reason(title, quality_score)
            return False, quality_score, reason
        
        return True, quality_score, ""
    
    @classmethod
    def _get_quality_issue_reason(cls, text: str, score: float) -> str:
        """获取质量问题的具体原因"""
        reasons = []
        
        if cls._calculate_garbled_ratio(text) > 0.1:
            reasons.append("包含乱码字符")
        
        if cls._calculate_character_diversity(text) < 0.3:
            reasons.append("字符多样性不足")
        
        if cls._has_meaningless_pattern(text):
            reasons.append("包含无意义模式")
        
        if len(text.strip()) < 2:
            reasons.append("标题过短")
        
        return "; ".join(reasons) if reasons else f"质量得分过低 ({score:.2f})"
    
    @classmethod
    def is_valid_content(cls, content: str, min_length: int = 50) -> Tuple[bool, float, str]:
        """
        验证内容是否有效
        
        Args:
            content: 待验证的内容
            min_length: 最小长度要求
            
        Returns:
            (是否有效, 质量得分, 失败原因)
        """
        if not content or not content.strip():
            return False, 0.0, "内容为空"
        
        content = content.strip()
        
        if len(content) < min_length:
            return False, 0.0, f"内容过短 ({len(content)} < {min_length})"
        
        quality_score = cls.calculate_text_quality_score(content[:200])  # 只检查前200字符
        
        if quality_score < 0.5:
            reason = cls._get_quality_issue_reason(content[:200], quality_score)
            return False, quality_score, reason
        
        return True, quality_score, ""
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        """清理文本，移除乱码和无用字符"""
        if not text:
            return ""
        
        # 移除控制字符
        text = ''.join(char for char in text if unicodedata.category(char) not in ['Cc', 'Cf'])
        
        # 移除乱码模式
        for pattern in cls.GARBLED_PATTERNS:
            text = re.sub(pattern, '', text)
        
        # 标准化空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()