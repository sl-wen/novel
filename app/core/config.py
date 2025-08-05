import logging
import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # 项目信息
    PROJECT_NAME: str = "小说聚合搜索与下载API"
    PROJECT_DESCRIPTION: str = "提供小说搜索和下载功能的RESTful API服务"
    VERSION: str = "0.1.0"

    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # API设置
    API_PREFIX: str = "/api"

    # 下载设置
    DOWNLOAD_PATH: str = str(ROOT_DIR / "downloads")

    # 书源设置
    RULES_PATH: str = str(ROOT_DIR / "rules")
    DEFAULT_SOURCE_ID: int = 1

    # 并发设置
    MAX_THREADS: int = os.cpu_count() * 2 if os.cpu_count() else 8
    MAX_CONCURRENT_REQUESTS: int = 5  # 最大并发请求数
    
    # 下载设置
    DOWNLOAD_CONCURRENT_LIMIT: int = 5  # 下载并发限制
    DOWNLOAD_RETRY_TIMES: int = 3  # 下载重试次数
    DOWNLOAD_RETRY_DELAY: float = 2.0  # 下载重试延迟（秒）
    DOWNLOAD_BATCH_DELAY: float = 1.0  # 批次间延迟（秒）
    MIN_CHAPTER_LENGTH: int = 50  # 最小章节长度（字符数）
    MIN_CONTENT_LENGTH: int = 100  # 最小内容长度（字符数）
    
    # 搜索设置
    MAX_SEARCH_PAGES: int = 3  # 最大搜索页数
    MAX_SEARCH_RESULTS: int = 20  # 最大搜索结果数

    # 文件格式
    SUPPORTED_FORMATS: List[str] = ["txt", "epub"]
    DEFAULT_FORMAT: str = "txt"

    # HTTP设置
    DEFAULT_TIMEOUT: int = 300  # 秒
    REQUEST_RETRY_TIMES: int = 3  # 请求重试次数
    REQUEST_RETRY_DELAY: float = 2.0  # 请求重试延迟（秒）
    DEFAULT_HEADERS: dict = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    # 内容过滤设置
    ENABLE_CONTENT_FILTER: bool = True  # 是否启用内容过滤
    MIN_CHAPTER_LENGTH: int = 50  # 最小章节长度（字符数）

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建设置实例
settings = Settings()

# 确保下载目录存在
os.makedirs(settings.DOWNLOAD_PATH, exist_ok=True)

# 如果是调试模式，设置更详细的日志级别
if settings.DEBUG:
    logging.getLogger("app.services.novel_service").setLevel(logging.DEBUG)
    logging.getLogger("app.parsers").setLevel(logging.DEBUG)
