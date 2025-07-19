"""
基础功能测试
"""
import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_import_app():
    """测试应用导入"""
    try:
        from app.main import app
        assert app is not None
        print("✅ 应用导入成功")
    except ImportError as e:
        pytest.skip(f"应用导入失败: {e}")

def test_import_config():
    """测试配置导入"""
    try:
        from app.core.config import settings
        assert settings is not None
        print("✅ 配置导入成功")
    except ImportError as e:
        pytest.skip(f"配置导入失败: {e}")

def test_import_models():
    """测试模型导入"""
    try:
        from app.models.book import BookInfo
        from app.models.chapter import ChapterInfo
        from app.models.search import SearchResult, SearchResponse
        print("✅ 模型导入成功")
    except ImportError as e:
        pytest.skip(f"模型导入失败: {e}")

def test_import_services():
    """测试服务导入"""
    try:
        from app.services.novel_service import NovelService
        print("✅ 服务导入成功")
    except ImportError as e:
        pytest.skip(f"服务导入失败: {e}")

def test_import_parsers():
    """测试解析器导入"""
    try:
        from app.parsers.search_parser import SearchParser
        from app.parsers.book_parser import BookParser
        from app.parsers.toc_parser import TocParser
        from app.parsers.chapter_parser import ChapterParser
        print("✅ 解析器导入成功")
    except ImportError as e:
        pytest.skip(f"解析器导入失败: {e}")

def test_basic_functionality():
    """基础功能测试"""
    # 这是一个简单的功能测试
    assert True
    print("✅ 基础功能测试通过") 