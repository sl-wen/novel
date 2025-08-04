from typing import List

from pydantic import BaseModel, Field


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
    bookName: str = Field(default="", alias="bookName")

    def __init__(self, **data):
        super().__init__(**data)
        # 确保bookName字段与title保持同步
        if not self.bookName and self.title:
            self.bookName = self.title

    @property
    def bookName_property(self) -> str:
        """向后兼容的属性，映射到title字段"""
        return self.title


class SearchResponse(BaseModel):
    """搜索响应模型"""

    code: int = 200
    message: str = "success"
    data: List[SearchResult] = []
