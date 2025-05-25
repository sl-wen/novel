from pydantic import BaseModel
from typing import Optional


class Chapter(BaseModel):
    """章节模型，对应Java项目中的Chapter类"""
    url: str
    title: str
    content: Optional[str] = None
    order: Optional[int] = None


class ChapterInfo(BaseModel):
    """章节信息模型，不包含内容，用于目录列表"""
    url: str
    title: str
    order: Optional[int] = None