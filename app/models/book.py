from pydantic import BaseModel, HttpUrl
from typing import Optional


class Book(BaseModel):
    """书籍模型，对应Java项目中的Book类"""
    url: str
    bookName: str
    author: Optional[str] = None
    intro: Optional[str] = None
    category: Optional[str] = None
    coverUrl: Optional[str] = None
    latestChapter: Optional[str] = None
    lastUpdateTime: Optional[str] = None
    status: Optional[str] = None
    wordCount: Optional[str] = None