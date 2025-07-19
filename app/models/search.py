from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SearchResult(BaseModel):
    """搜索结果模型"""
    sourceId: int = Field(..., description="书源ID")
    sourceName: str = Field(..., description="书源名称")
    url: str = Field(..., description="小说详情页URL")
    bookName: str = Field(..., description="小说名称")
    author: Optional[str] = Field(None, description="作者名")
    category: Optional[str] = Field(None, description="小说分类")
    intro: Optional[str] = Field(None, description="小说简介")
    coverUrl: Optional[str] = Field(None, description="封面图片URL")
    chapterCount: Optional[int] = Field(None, description="章节总数")
    latestChapter: Optional[str] = Field(None, description="最新章节")
    lastUpdateTime: Optional[str] = Field(None, description="最后更新时间")
    status: Optional[str] = Field(None, description="小说状态，如：连载中、已完结")
    wordCount: Optional[str] = Field(None, description="字数")
    score: Optional[float] = Field(None, description="评分")

    class Config:
        json_schema_extra = {
            "example": {
                "sourceId": 1,
                "sourceName": "某某小说网",
                "url": "https://example.com/book/123",
                "bookName": "斗破苍穹",
                "author": "天蚕土豆",
                "category": "玄幻",
                "intro": "这是一个描述...",
                "coverUrl": "https://example.com/cover/123.jpg",
                "chapterCount": 1000,
                "latestChapter": "第一千章 大结局",
                "lastUpdateTime": "2023-12-25 12:00:00",
                "status": "已完结",
                "wordCount": "300万字",
                "score": 9.5
            }
        }


class SearchResponse(BaseModel):
    """搜索响应模型"""
    code: int = Field(200, description="响应状态码")
    message: str = Field("success", description="响应消息")
    data: List[SearchResult] = Field(..., description="搜索结果列表")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "success",
                "data": [
                    {
                        "sourceId": 1,
                        "sourceName": "某某小说网",
                        "url": "https://example.com/book/123",
                        "bookName": "斗破苍穹",
                        "author": "天蚕土豆"
                    }
                ]
            }
        }