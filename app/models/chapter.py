from pydantic import BaseModel


class Chapter(BaseModel):
    """章节内容模型"""

    title: str
    content: str
    url: str = ""
    order: int = 0
    word_count: str = ""
    update_time: str = ""
    source_id: int = 0
    source_name: str = ""


class ChapterInfo(BaseModel):
    """章节信息模型（用于目录）"""

    title: str
    url: str
    order: int
    word_count: str = ""
    update_time: str = ""
    source_id: int = 0
    source_name: str = ""
