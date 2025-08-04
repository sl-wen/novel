from pydantic import BaseModel


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

    @property
    def bookName(self) -> str:
        """向后兼容的属性，映射到title字段"""
        return self.title
