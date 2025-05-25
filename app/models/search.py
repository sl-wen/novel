from pydantic import BaseModel
from typing import Optional, List


class SearchResult(BaseModel):
    """搜索结果模型，对应Java项目中的SearchResult类"""
    sourceId: int
    sourceName: str
    url: str
    bookName: str
    author: Optional[str] = None
    chapterCount: Optional[int] = None
    latestChapter: Optional[str] = None
    lastUpdateTime: Optional[str] = None
    status: Optional[str] = None


class SearchResponse(BaseModel):
    """搜索响应模型"""
    code: int = 200
    message: str = "success"
    data: List[SearchResult]