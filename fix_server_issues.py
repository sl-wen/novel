#!/usr/bin/env python3
"""
服务器问题修复脚本
解决服务器上的异步和属性访问问题
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fix_async_issues():
    """修复异步相关问题"""
    print("🔧 修复异步相关问题...")

    # 1. 修复 novel_service.py 中的 get_sources 方法
    novel_service_path = Path("app/services/novel_service.py")
    if novel_service_path.exists():
        with open(novel_service_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否已经修复
        if "async def get_sources(self):" in content:
            print("✅ novel_service.py 中的 get_sources 方法已经是异步的")
        else:
            print("❌ 需要修复 novel_service.py 中的 get_sources 方法")
            return False

    # 2. 修复 API 端点中的调用
    novels_endpoint_path = Path("app/api/endpoints/novels.py")
    if novels_endpoint_path.exists():
        with open(novels_endpoint_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "await novel_service.get_sources()" in content:
            print("✅ API端点中的 get_sources 调用已经是正确的")
        else:
            print("❌ 需要修复 API端点中的 get_sources 调用")
            return False

    return True


def fix_search_result_issues():
    """修复搜索结果相关问题"""
    print("🔧 修复搜索结果相关问题...")

    # 检查 SearchResult 模型
    search_model_path = Path("app/models/search.py")
    if search_model_path.exists():
        with open(search_model_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "bookName: str" in content:
            print("✅ SearchResult 模型包含 bookName 属性")
        else:
            print("❌ SearchResult 模型缺少 bookName 属性")
            return False

    return True


def check_python_version():
    """检查Python版本"""
    print("🔍 检查Python版本...")
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python版本过低，建议使用Python 3.8+")
        return False
    else:
        print("✅ Python版本符合要求")
        return True


def check_dependencies():
    """检查依赖包"""
    print("🔍 检查依赖包...")

    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "requests",
        "aiohttp",
        "beautifulsoup4",
        "asyncio",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - 未安装")

    if missing_packages:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False

    return True


def create_debug_script():
    """创建调试脚本"""
    print("🔧 创建调试脚本...")

    debug_script = '''#!/usr/bin/env python3
"""
调试脚本 - 用于诊断服务器问题
"""

import asyncio
import sys
import traceback
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_novel_service():
    """测试小说服务"""
    try:
        from app.services.novel_service import NovelService
        
        print("🔍 测试 NovelService 初始化...")
        service = NovelService()
        print(f"✅ 服务初始化成功，书源数量: {len(service.sources)}")
        
        print("🔍 测试 get_sources 方法...")
        sources = await service.get_sources()
        print(f"✅ get_sources 成功，返回 {len(sources)} 个书源")
        
        print("🔍 测试搜索功能...")
        results = await service.search("斗破苍穹")
        print(f"✅ 搜索成功，找到 {len(results)} 条结果")
        
        if results:
            first_result = results[0]
            print(f"✅ 第一个结果: {first_result.bookName} - {first_result.author}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False

async def test_models():
    """测试数据模型"""
    try:
        from app.models.search import SearchResult
        
        print("🔍 测试 SearchResult 模型...")
        result = SearchResult(
            sourceId=1,
            sourceName="测试书源",
            url="http://example.com",
            bookName="测试小说",
            author="测试作者"
        )
        print(f"✅ SearchResult 创建成功: {result.bookName}")
        return True
    except Exception as e:
        print(f"❌ 模型测试失败: {str(e)}")
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False

async def main():
    """主函数"""
    print("🚀 开始调试测试")
    print("=" * 50)
    
    # 测试模型
    model_ok = await test_models()
    print()
    
    # 测试服务
    service_ok = await test_novel_service()
    print()
    
    # 总结
    print("=" * 50)
    print("📊 测试总结:")
    print(f"  模型测试: {'✅ 通过' if model_ok else '❌ 失败'}")
    print(f"  服务测试: {'✅ 通过' if service_ok else '❌ 失败'}")
    
    if model_ok and service_ok:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  存在问题，请检查错误信息")

if __name__ == "__main__":
    asyncio.run(main())
'''

    with open("debug_server.py", "w", encoding="utf-8") as f:
        f.write(debug_script)

    print("✅ 调试脚本已创建: debug_server.py")


def main():
    """主函数"""
    print("🔧 服务器问题修复工具")
    print("=" * 50)

    # 检查Python版本
    if not check_python_version():
        return

    print()

    # 检查依赖
    if not check_dependencies():
        return

    print()

    # 修复异步问题
    if not fix_async_issues():
        print("❌ 异步问题修复失败")
        return

    print()

    # 修复搜索结果问题
    if not fix_search_result_issues():
        print("❌ 搜索结果问题修复失败")
        return

    print()

    # 创建调试脚本
    create_debug_script()

    print()
    print("🎉 修复完成！")
    print("📋 建议执行以下步骤:")
    print("1. 运行调试脚本: python debug_server.py")
    print("2. 重启API服务: python start_api.py")
    print("3. 测试API: python test_api.py")


if __name__ == "__main__":
    main()
