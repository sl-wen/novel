from typing import List

from pydantic import BaseModel


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


class SearchResponse(BaseModel):
    """搜索响应模型"""

    code: int = 200
    message: str = "success"
    data: List[SearchResult] = []
