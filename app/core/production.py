"""
生产环境配置
"""
import os
from app.core.config import settings

class ProductionSettings:
    """生产环境设置"""
    
    # 基础配置
    DEBUG = False
    HOST = "0.0.0.0"
    PORT = 8000
    
    # 数据库配置（如果需要）
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    
    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FILE = "/var/log/novel/app.log"
    
    # 文件路径配置
    DOWNLOAD_PATH = "/var/www/novel/downloads"
    
    # 安全配置
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALLOWED_HOSTS = ["*"]  # 生产环境应该限制具体域名
    
    # 缓存配置
    CACHE_TTL = 3600  # 1小时
    
    # 并发配置
    MAX_CONCURRENT_REQUESTS = 50
    REQUEST_TIMEOUT = 30
    REQUEST_RETRY_TIMES = 3
    REQUEST_RETRY_DELAY = 2
    
    # 下载配置
    DEFAULT_FORMAT = "txt"
    SUPPORTED_FORMATS = ["txt", "epub"]
    MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024  # 100MB
    
    # 书源配置
    DEFAULT_SOURCE_ID = 1
    
    # 用户代理
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    } 