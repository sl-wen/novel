import uvicorn
import os
from app.core.config import settings


def main():
    """启动API服务"""
    # 确保下载目录存在
    os.makedirs(settings.DOWNLOAD_PATH, exist_ok=True)

    # 启动服务
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
