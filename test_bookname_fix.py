#!/usr/bin/env python3
"""
测试SearchResult的bookName属性
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_search_result():
    """测试SearchResult模型"""
    print("🔍 测试SearchResult模型...")
    
    try:
        from app.models.search import SearchResult
        
        # 创建SearchResult对象
        result = SearchResult(
            title="斗破苍穹",
            author="天蚕土豆",
            url="http://example.com/book/1",
            source_id=1,
            source_name="测试书源"
        )
        
        print(f"✅ SearchResult创建成功")
        print(f"   - title: {result.title}")
        print(f"   - author: {result.author}")
        
        # 测试bookName属性访问
        try:
            book_name = result.bookName
            print(f"✅ bookName属性访问成功: {book_name}")
        except AttributeError as e:
            print(f"❌ bookName属性访问失败: {str(e)}")
            return False
        
        # 测试序列化
        try:
            data = result.model_dump()
            print(f"✅ 序列化成功")
            print(f"   - bookName在序列化数据中: {'bookName' in data}")
            if 'bookName' in data:
                print(f"   - bookName值: {data['bookName']}")
        except Exception as e:
            print(f"❌ 序列化失败: {str(e)}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        print(f"详细错误:\n{traceback.format_exc()}")
        return False

async def test_search_service():
    """测试搜索服务"""
    print("\n🔍 测试搜索服务...")
    
    try:
        from app.services.novel_service import NovelService
        
        service = NovelService()
        results = await service.search("斗破苍穹", max_results=3)
        print(f"✅ 搜索成功，找到 {len(results)} 条结果")
        
        if results:
            first_result = results[0]
            print(f"   - 第一个结果类型: {type(first_result)}")
            
            # 测试属性访问
            try:
                title = first_result.title
                print(f"   - ✅ title: {title}")
            except AttributeError as e:
                print(f"   - ❌ title访问失败: {str(e)}")
            
            try:
                book_name = first_result.bookName
                print(f"   - ✅ bookName: {book_name}")
            except AttributeError as e:
                print(f"   - ❌ bookName访问失败: {str(e)}")
                return False
            
            try:
                author = first_result.author
                print(f"   - ✅ author: {author}")
            except AttributeError as e:
                print(f"   - ❌ author访问失败: {str(e)}")
        
        return True
    except Exception as e:
        print(f"❌ 搜索服务测试失败: {str(e)}")
        import traceback
        print(f"详细错误:\n{traceback.format_exc()}")
        return False

async def main():
    """主函数"""
    print("🚀 SearchResult bookName属性测试")
    print("=" * 50)
    
    # 测试模型
    model_ok = test_search_result()
    
    # 测试搜索服务
    service_ok = await test_search_service()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结:")
    print(f"  模型测试: {'✅ 通过' if model_ok else '❌ 失败'}")
    print(f"  搜索服务: {'✅ 通过' if service_ok else '❌ 失败'}")
    
    if model_ok and service_ok:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  存在问题，请检查错误信息")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
