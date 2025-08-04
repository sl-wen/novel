#!/usr/bin/env python3
"""
服务器问题诊断脚本
详细诊断服务器上的问题
"""

import sys
import os
import asyncio
import traceback
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def check_python_environment():
    """检查Python环境"""
    print("🔍 检查Python环境...")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"项目路径: {Path(__file__).parent}")
    
    # 检查虚拟环境
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 运行在虚拟环境中")
    else:
        print("⚠️  未检测到虚拟环境")

def check_imports():
    """检查关键模块导入"""
    print("\n🔍 检查模块导入...")
    
    modules_to_test = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "BaseModel"),
        ("pydantic_settings", "BaseSettings"),
        ("requests", "requests"),
        ("aiohttp", "aiohttp"),
        ("bs4", "BeautifulSoup"),
        ("asyncio", "asyncio"),
    ]
    
    for module_name, import_name in modules_to_test:
        try:
            module = __import__(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {str(e)}")

def test_models():
    """测试数据模型"""
    print("\n🔍 测试数据模型...")
    
    try:
        from app.models.search import SearchResult
        
        # 测试创建SearchResult对象
        result = SearchResult(
            sourceId=1,
            sourceName="测试书源",
            url="http://example.com",
            bookName="测试小说",
            author="测试作者"
        )
        
        print(f"✅ SearchResult 创建成功")
        print(f"   - 类型: {type(result)}")
        print(f"   - 书名: {result.bookName}")
        print(f"   - 作者: {result.author}")
        
        # 测试属性访问
        try:
            book_name = result.bookName
            print(f"✅ 属性访问正常: {book_name}")
        except AttributeError as e:
            print(f"❌ 属性访问失败: {str(e)}")
        
        return True
    except Exception as e:
        print(f"❌ 模型测试失败: {str(e)}")
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False

async def test_novel_service():
    """测试小说服务"""
    print("\n🔍 测试小说服务...")
    
    try:
        from app.services.novel_service import NovelService
        
        # 测试服务初始化
        print("  初始化 NovelService...")
        service = NovelService()
        print(f"✅ 服务初始化成功")
        print(f"   - 书源数量: {len(service.sources)}")
        
        # 测试get_sources方法
        print("  测试 get_sources 方法...")
        sources = await service.get_sources()
        print(f"✅ get_sources 成功")
        print(f"   - 返回书源数量: {len(sources)}")
        
        if sources:
            first_source = sources[0]
            print(f"   - 第一个书源: ID={first_source.get('id')}, 名称={first_source.get('rule', {}).get('name', 'N/A')}")
        
        # 测试搜索功能
        print("  测试搜索功能...")
        results = await service.search("斗破苍穹")
        print(f"✅ 搜索成功")
        print(f"   - 搜索结果数量: {len(results)}")
        
        if results:
            first_result = results[0]
            print(f"   - 第一个结果: {first_result.bookName} - {first_result.author}")
        
        return True
    except Exception as e:
        print(f"❌ 服务测试失败: {str(e)}")
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False

async def test_api_endpoints():
    """测试API端点"""
    print("\n🔍 测试API端点...")
    
    try:
        import requests
        
        base_url = "http://localhost:8000"
        
        # 测试健康检查
        print("  测试健康检查端点...")
        response = requests.get(f"{base_url}/api/novels/health", timeout=10)
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"   - 错误响应: {response.text}")
        
        # 测试书源端点
        print("  测试书源端点...")
        response = requests.get(f"{base_url}/api/novels/sources", timeout=10)
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - 书源数量: {len(data.get('data', []))}")
        else:
            print(f"   - 错误响应: {response.text}")
        
        # 测试搜索端点
        print("  测试搜索端点...")
        response = requests.get(f"{base_url}/api/novels/search?keyword=斗破苍穹", timeout=30)
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - 搜索结果数量: {len(data.get('data', []))}")
        else:
            print(f"   - 错误响应: {response.text}")
        
        return True
    except Exception as e:
        print(f"❌ API端点测试失败: {str(e)}")
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False

def check_file_structure():
    """检查文件结构"""
    print("\n🔍 检查文件结构...")
    
    required_files = [
        "app/main.py",
        "app/api/endpoints/novels.py",
        "app/services/novel_service.py",
        "app/models/search.py",
        "app/core/config.py",
        "app/core/source.py",
        "resources/rule/new"
    ]
    
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            if path.is_dir():
                files = list(path.glob("*"))
                print(f"✅ {file_path} (目录，包含 {len(files)} 个文件)")
            else:
                print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 不存在")

def check_rule_files():
    """检查规则文件"""
    print("\n🔍 检查规则文件...")
    
    rules_path = Path("resources/rule/new")
    if rules_path.exists():
        rule_files = list(rules_path.glob("rule-*.json"))
        print(f"✅ 找到 {len(rule_files)} 个规则文件")
        
        for rule_file in rule_files[:3]:  # 只显示前3个
            try:
                with open(rule_file, "r", encoding="utf-8") as f:
                    rule_data = json.load(f)
                print(f"   - {rule_file.name}: {rule_data.get('name', 'N/A')}")
            except Exception as e:
                print(f"   - {rule_file.name}: 解析失败 - {str(e)}")
    else:
        print("❌ 规则目录不存在")

async def main():
    """主函数"""
    print("🚀 服务器问题诊断工具")
    print("=" * 60)
    
    # 检查Python环境
    check_python_environment()
    
    # 检查模块导入
    check_imports()
    
    # 检查文件结构
    check_file_structure()
    
    # 检查规则文件
    check_rule_files()
    
    # 测试数据模型
    model_ok = test_models()
    
    # 测试小说服务
    service_ok = await test_novel_service()
    
    # 测试API端点
    api_ok = await test_api_endpoints()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 诊断总结:")
    print(f"  数据模型: {'✅ 正常' if model_ok else '❌ 异常'}")
    print(f"  小说服务: {'✅ 正常' if service_ok else '❌ 异常'}")
    print(f"  API端点: {'✅ 正常' if api_ok else '❌ 异常'}")
    
    if model_ok and service_ok and api_ok:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  发现问题，请检查上述错误信息")
        print("\n💡 建议:")
        print("1. 检查Python版本是否为3.8+")
        print("2. 确保所有依赖已正确安装")
        print("3. 检查规则文件格式是否正确")
        print("4. 重启API服务")

if __name__ == "__main__":
    asyncio.run(main()) 