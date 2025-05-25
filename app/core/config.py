from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # 项目信息
    PROJECT_NAME: str = "小说聚合搜索与下载API"
    PROJECT_DESCRIPTION: str = "提供小说搜索和下载功能的RESTful API服务"
    VERSION: str = "0.1.0"
    
    # API设置
    API_PREFIX: str = "/api"
    
    # 下载设置
    DOWNLOAD_PATH: str = str(ROOT_DIR / "downloads")
    
    # 书源设置
    RULES_PATH: str = str(ROOT_DIR / "resources" / "rule" / "new")
    DEFAULT_SOURCE_ID: int = 1
    
    # 并发设置
    MAX_THREADS: int = os.cpu_count() * 2 if os.cpu_count() else 8
    
    # 文件格式
    SUPPORTED_FORMATS: List[str] = ["txt", "epub", "pdf"]
    DEFAULT_FORMAT: str = "txt"
    
    # HTTP设置
    DEFAULT_TIMEOUT: int = 10  # 秒
    DEFAULT_HEADERS: dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建设置实例
settings = Settings()

# 确保下载目录存在
os.makedirs(settings.DOWNLOAD_PATH, exist_ok=True)