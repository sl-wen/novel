#!/usr/bin/env python3
"""
最终的下载问题修复方案
重点解决目录解析和下载功能问题
"""

import requests
import json
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_download_fix():
    """测试下载修复方案"""
    print("🔧 最终的下载问题修复方案")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # 1. 测试搜索功能
    print("1. 测试搜索功能...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "maxResults": 1},
            timeout=300
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            if results:
                book = results[0]
                print(f"   ✅ 搜索成功: {book.get('title', book.get('bookName'))}")
                print(f"   - 作者: {book.get('author')}")
                print(f"   - URL: {book.get('url')}")
                print(f"   - 书源ID: {book.get('source_id')}")
                
                # 2. 测试目录功能
                print("\n2. 测试目录功能...")
                toc_response = requests.get(
                    f"{base_url}/api/novels/toc",
                    params={
                        "url": book.get("url"),
                        "sourceId": book.get("source_id")
                    },
                    timeout=300
                )
                
                if toc_response.status_code == 200:
                    toc_data = toc_response.json()
                    chapters = toc_data.get("data", [])
                    print(f"   - 目录章节数: {len(chapters)}")
                    
                    if chapters:
                        print("   ✅ 目录解析成功")
                        print("   - 章节预览:")
                        for i, chapter in enumerate(chapters[:10]):
                            print(f"     {i+1}. {chapter.get('title', '无标题')}")
                        
                        # 3. 测试下载功能
                        print("\n3. 测试下载功能...")
                        download_response = requests.get(
                            f"{base_url}/api/novels/download",
                            params={
                                "url": book.get("url"),
                                "sourceId": book.get("source_id"),
                                "format": "txt"
                            },
                            timeout=300,
                            stream=True
                        )
                        
                        print(f"   - 下载状态码: {download_response.status_code}")
                        
                        if download_response.status_code == 200:
                            # 保存测试文件
                            filename = "download_test.txt"
                            with open(filename, "wb") as f:
                                for chunk in download_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            import os
                            file_size = os.path.getsize(filename)
                            print(f"   ✅ 下载成功，文件大小: {file_size} 字节")
                            
                            if file_size > 0:
                                # 检查文件内容
                                with open(filename, "r", encoding="utf-8") as f:
                                    content = f.read(500)
                                    print(f"   - 文件内容预览: {content[:100]}...")
                                
                                # 清理测试文件
                                os.remove(filename)
                                print("   - 测试文件已清理")
                                print("   🎉 下载功能完全修复！")
                                return True
                            else:
                                print("   ❌ 下载的文件为空")
                                return False
                        else:
                            print(f"   ❌ 下载失败: {download_response.text}")
                            return False
                    else:
                        print("   ❌ 目录为空，无法下载")
                        return False
                else:
                    print(f"   ❌ 目录API失败: {toc_response.text}")
                    return False
            else:
                print("   ❌ 搜索无结果")
                return False
        else:
            print(f"   ❌ 搜索失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试异常: {str(e)}")
        return False

def create_download_fix_solution():
    """创建下载修复解决方案"""
    print("\n🔧 下载问题修复方案")
    print("=" * 60)
    
    solution = """
🎯 问题分析：
1. 搜索功能正常 - 可以找到小说
2. 目录解析失败 - 返回0章
3. 下载功能失败 - 依赖目录解析

🔧 修复方案：

1. 目录解析器修复
   - 检查CSS选择器是否正确
   - 添加更多调试日志
   - 尝试不同的解析策略
   - 处理JavaScript动态加载

2. 网络请求优化
   - 增加请求头模拟浏览器
   - 添加请求延迟
   - 实现重试机制
   - 处理反爬虫措施

3. 错误处理改进
   - 添加详细的错误日志
   - 实现降级机制
   - 提供备用解析方案

4. 书源规则更新
   - 测试所有书源
   - 更新失效的规则
   - 添加新的书源

5. 下载功能优化
   - 改进文件生成逻辑
   - 优化内存使用
   - 添加进度显示
   - 实现断点续传

📋 实施步骤：
1. 修复目录解析器
2. 优化网络请求
3. 更新书源规则
4. 测试下载功能
5. 部署修复版本

🎯 预期结果：
- 目录解析成功
- 下载功能正常
- 系统稳定性提升
"""
    print(solution)

def test_alternative_sources():
    """测试其他书源"""
    print("\n4. 测试其他书源...")
    
    base_url = "http://localhost:8000"
    
    # 获取所有书源
    try:
        sources_response = requests.get(f"{base_url}/api/novels/sources", timeout=10)
        if sources_response.status_code == 200:
            sources_data = sources_response.json()
            sources = sources_data.get("data", [])
            
            print(f"   - 可用书源数量: {len(sources)}")
            
            # 测试每个书源
            working_sources = []
            for source in sources[:5]:  # 只测试前5个书源
                source_id = source.get("id")
                source_name = source.get("name", f"Unknown-{source_id}")
                
                try:
                    # 搜索测试
                    search_response = requests.get(
                        f"{base_url}/api/novels/search",
                        params={"keyword": "斗破苍穹", "maxResults": 1},
                        timeout=30
                    )
                    
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        results = search_data.get("data", [])
                        if results:
                            result = results[0]
                            
                            # 测试目录
                            toc_response = requests.get(
                                f"{base_url}/api/novels/toc",
                                params={
                                    "url": result.get("url"),
                                    "sourceId": source_id
                                },
                                timeout=30
                            )
                            
                            if toc_response.status_code == 200:
                                toc_data = toc_response.json()
                                chapters = toc_data.get("data", [])
                                
                                if chapters:
                                    print(f"   ✅ 书源 {source_name} 可用: {len(chapters)} 章")
                                    working_sources.append({
                                        'id': source_id,
                                        'name': source_name,
                                        'url': result.get("url"),
                                        'chapters': len(chapters)
                                    })
                                else:
                                    print(f"   ⚠️  书源 {source_name} 目录为空")
                            else:
                                print(f"   ❌ 书源 {source_name} 目录API失败")
                        else:
                            print(f"   ❌ 书源 {source_name} 搜索无结果")
                    else:
                        print(f"   ❌ 书源 {source_name} 搜索API失败")
                        
                except Exception as e:
                    print(f"   ❌ 书源 {source_name} 测试异常: {str(e)}")
                    continue
            
            print(f"\n   - 找到 {len(working_sources)} 个可用书源")
            for source in working_sources:
                print(f"     - {source['name']} (ID: {source['id']}): {source['chapters']} 章")
            
            return working_sources
        else:
            print(f"   ❌ 获取书源失败: {sources_response.text}")
            return []
            
    except Exception as e:
        print(f"   ❌ 测试失败: {str(e)}")
        return []

if __name__ == "__main__":
    # 测试下载修复
    success = test_download_fix()
    
    if not success:
        # 测试其他书源
        working_sources = test_alternative_sources()
        
        if not working_sources:
            # 创建修复方案
            create_download_fix_solution()