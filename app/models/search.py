import logging
from typing import List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """搜索结果模型"""

    title: str
    author: str
    intro: str = ""
    cover: str = ""
    url: str = ""
    category: str = ""
    status: str = ""
    word_count: str = ""
    update_time: str = ""
    latest_chapter: str = ""
    source_id: int = 0
    source_name: str = ""
    score: float = 0.0
    bookName: str = Field(default="", description="书名，与title字段同步")

    def __init__(self, **data):
        super().__init__(**data)
        # 确保bookName字段与title保持同步
        try:
            if not self.bookName and self.title:
                self.bookName = self.title
        except AttributeError:
            # 如果bookName属性不存在，跳过同步
            pass

    @property
    def bookName_property(self) -> str:
        """向后兼容的属性，映射到title字段"""
        return self.title

    def model_dump(self, **kwargs):
        """自定义序列化方法，确保bookName字段正确输出"""
        try:
            data = super().model_dump(**kwargs)
            # 确保bookName字段存在且与title同步
            if not data.get('bookName') and data.get('title'):
                data['bookName'] = data['title']
            return data
        except Exception as e:
            # 如果序列化失败，返回基本数据
            logger.warning(f"SearchResult序列化失败: {str(e)}")
            return {
                'title': getattr(self, 'title', ''),
                'author': getattr(self, 'author', ''),
                'intro': getattr(self, 'intro', ''),
                'cover': getattr(self, 'cover', ''),
                'url': getattr(self, 'url', ''),
                'category': getattr(self, 'category', ''),
                'status': getattr(self, 'status', ''),
                'word_count': getattr(self, 'word_count', ''),
                'update_time': getattr(self, 'update_time', ''),
                'latest_chapter': getattr(self, 'latest_chapter', ''),
                'source_id': getattr(self, 'source_id', 0),
                'source_name': getattr(self, 'source_name', ''),
                'score': getattr(self, 'score', 0.0),
                'bookName': getattr(self, 'bookName', getattr(self, 'title', ''))
            }


class SearchResponse(BaseModel):
    """搜索响应模型"""

    code: int = 200
    message: str = "success"
    data: List[SearchResult] = []
