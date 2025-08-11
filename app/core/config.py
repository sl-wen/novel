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
    DEFAULT_SOURCE_ID: int = 2  # 改为书源2，因为书源1无法访问

    # 并发设置
    MAX_THREADS: int = 50
    MAX_CONCURRENT_REQUESTS: int = 50  # 最大并发请求数

    # 下载设置
    DOWNLOAD_CONCURRENT_LIMIT: int = 50  # 下载并发限制
    DOWNLOAD_RETRY_TIMES: int = 2  # 下载重试次数
    DOWNLOAD_RETRY_DELAY: float = 2.0  # 下载重试延迟（秒）
    DOWNLOAD_BATCH_DELAY: float = 1.0  # 批次间延迟（秒）
    MIN_CONTENT_LENGTH: int = 100  # 最小内容长度（字符数）

    # 搜索设置
    MAX_SEARCH_PAGES: int = 3  # 最大搜索页数
    MAX_SEARCH_RESULTS: int = 20  # 最大搜索结果数
    MAX_RESULTS_PER_SOURCE: int = 3  # 每个书源最大结果数

    # 文件格式
    SUPPORTED_FORMATS: List[str] = ["txt", "epub"]
    DEFAULT_FORMAT: str = "txt"

    # HTTP设置
    DEFAULT_TIMEOUT: int = 180  # 增加到180秒，适应更长的下载时间
    REQUEST_RETRY_TIMES: int = 3  # 增加重试次数
    REQUEST_RETRY_DELAY: float = 3.0  # 增加重试延迟（秒）
    
    # 分层超时设置
    SEARCH_TIMEOUT: int = 30      # 搜索超时
    BOOK_DETAIL_TIMEOUT: int = 45 # 书籍详情超时
    TOC_TIMEOUT: int = 60        # 目录获取超时
    CHAPTER_TIMEOUT: int = 90    # 单章节下载超时
    DOWNLOAD_TOTAL_TIMEOUT: int = 3600  # 总下载超时（1小时）
    
    # 增强超时设置
    POLLING_BASE_TIMEOUT: float = 60.0   # 增加轮询基础超时（秒）
    POLLING_MAX_TIMEOUT: float = 600.0   # 增加轮询最大超时（秒）
    POLLING_MIN_TIMEOUT: float = 15.0    # 增加轮询最小超时（秒）
    POLLING_HEARTBEAT_INTERVAL: float = 10.0  # 增加心跳间隔（秒）
    POLLING_MAX_ATTEMPTS: int = 360      # 增加轮询最大尝试次数（6小时）
    
    # 熔断器设置
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 8  # 增加熔断器失败阈值
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: float = 120.0  # 增加熔断器恢复超时（秒）
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
