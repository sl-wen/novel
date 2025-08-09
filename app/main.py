import logging  # 导入logging模块

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.endpoints import novels, optimized_novels
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

# 注册路由
app.include_router(novels.router, prefix="/api")
app.include_router(optimized_novels.router, prefix="/api")


@app.on_event("startup")
async def on_startup():
    """应用启动时触发书源验证"""
    try:
        from app.services.novel_service import NovelService

        service = NovelService()
        await service._validate_sources_async()
    except Exception as e:
        logger.warning(f"启动时验证书源失败: {str(e)}")


# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")  # 添加日志
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


# 通用异常处理
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"通用异常: {str(exc)}", exc_info=True)  # 添加日志，包含堆栈信息
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": f"内部服务器错误: {str(exc)}", "data": None},
    )


# 根路由
@app.get("/")
async def root():
    return {
        "code": 200,
        "message": "小说聚合搜索与下载API服务正在运行",
        "data": {"version": settings.VERSION, "docs": "/docs"},
    }


@app.on_event("shutdown")
async def on_shutdown():
    """应用关闭时优雅清理 HTTP 资源"""
    try:
        from app.utils.enhanced_http_client import http_client

        await http_client.shutdown()
    except Exception as e:
        logger.warning(f"关闭HTTP客户端时发生异常: {e}")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
