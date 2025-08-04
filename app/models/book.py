import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Book(BaseModel):
    """小说详情模型"""

    title: str
    author: str
    intro: str = ""
    cover: str = ""
    status: str = ""
    category: str = ""
    word_count: str = ""
    update_time: str = ""
    latest_chapter: str = ""
    toc_url: str = ""
    source_id: int = 0
    source_name: str = ""
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
            logger.warning(f"Book序列化失败: {str(e)}")
            return {
                'title': getattr(self, 'title', ''),
                'author': getattr(self, 'author', ''),
                'intro': getattr(self, 'intro', ''),
                'cover': getattr(self, 'cover', ''),
                'status': getattr(self, 'status', ''),
                'category': getattr(self, 'category', ''),
                'word_count': getattr(self, 'word_count', ''),
                'update_time': getattr(self, 'update_time', ''),
                'latest_chapter': getattr(self, 'latest_chapter', ''),
                'toc_url': getattr(self, 'toc_url', ''),
                'source_id': getattr(self, 'source_id', 0),
                'source_name': getattr(self, 'source_name', ''),
                'bookName': getattr(self, 'bookName', getattr(self, 'title', ''))
            }
