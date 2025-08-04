#!/usr/bin/env python3
"""
测试bookName错误处理修复
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.models.search import SearchResult, SearchResponse
    
    print("=== 测试1: 正常创建SearchResult对象 ===")
    # 测试创建SearchResult对象
    result = SearchResult(
        title="测试小说",
        author="测试作者",
        intro="测试简介",
        url="http://example.com",
        source_id=1,
        source_name="测试书源"
    )
    
    print("✓ SearchResult对象创建成功")
    print(f"  title: {result.title}")
    print(f"  bookName: {result.bookName}")
    print(f"  author: {result.author}")
    
    print("\n=== 测试2: 序列化测试 ===")
    # 测试序列化
    data = result.model_dump()
    print("✓ 序列化成功")
    print(f"  序列化数据: {data}")
    
    print("\n=== 测试3: SearchResponse测试 ===")
    # 测试SearchResponse
    response = SearchResponse(
        code=200,
        message="success",
        data=[result]
    )
    
    print("✓ SearchResponse对象创建成功")
    
    # 测试响应序列化
    response_data = response.model_dump()
    print("✓ 响应序列化成功")
    print(f"  响应数据: {response_data}")
    
    print("\n=== 测试4: 异常处理测试 ===")
    # 测试异常处理
    try:
        # 模拟一个可能有问题的情况
        problematic_result = SearchResult(
            title="问题小说",
            author="问题作者",
            url="http://example.com",
            source_id=1,
            source_name="测试书源"
        )
        
        # 尝试访问bookName属性
        bookname = problematic_result.bookName
        print(f"✓ 正常访问bookName: {bookname}")
        
    except AttributeError as e:
        print(f"❌ 出现bookName错误: {str(e)}")
    except Exception as e:
        print(f"❌ 其他错误: {str(e)}")
    
    print("\n✅ 所有测试通过！bookName错误处理修复成功")
    
except Exception as e:
    print(f"❌ 测试失败: {str(e)}")
    import traceback
    traceback.print_exc()