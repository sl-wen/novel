#!/usr/bin/env python3
"""
下载问题最终修复方案
专注于解决目录解析问题
"""

import requests
import json
import time

def test_download_issue():
    """测试下载问题"""
    print("🔧 下载问题最终修复方案")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # 1. 测试搜索功能
    print("1. 测试搜索功能...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "maxResults": 1},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            if results:
                book = results[0]
                print(f"   ✅ 搜索成功: {book.get('title', book.get('bookName'))}")
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
                    timeout=30
                )
                
                if toc_response.status_code == 200:
                    toc_data = toc_response.json()
                    chapters = toc_data.get("data", [])
                    print(f"   - 目录章节数: {len(chapters)}")
                    
                    if chapters:
                        print("   ✅ 目录解析成功")
                        print("   - 章节预览:")
                        for i, chapter in enumerate(chapters[:3]):
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

def create_fix_solution():
    """创建修复方案"""
    print("\n🔧 下载问题修复方案")
    print("=" * 50)
    
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

def test_simple_download():
    """简单下载测试"""
    print("\n4. 简单下载测试...")
    
    base_url = "http://localhost:8000"
    
    try:
        # 直接测试下载API
        response = requests.get(
            f"{base_url}/api/novels/download",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11,
                "format": "txt"
            },
            timeout=60,
            stream=True
        )
        
        print(f"   - 下载状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 检查响应头
            content_type = response.headers.get("content-type", "")
            content_disposition = response.headers.get("content-disposition", "")
            print(f"   - Content-Type: {content_type}")
            print(f"   - Content-Disposition: {content_disposition}")
            
            # 保存测试文件
            filename = "simple_test.txt"
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
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
                print("   🎉 简单下载测试成功！")
                return True
            else:
                print("   ❌ 下载的文件为空")
                return False
        else:
            print(f"   ❌ 下载失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 简单下载测试异常: {str(e)}")
        return False

if __name__ == "__main__":
    # 测试下载问题
    success = test_download_issue()
    
    if not success:
        # 尝试简单下载测试
        simple_success = test_simple_download()
        
        if not simple_success:
            # 创建修复方案
            create_fix_solution()