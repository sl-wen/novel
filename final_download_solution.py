#!/usr/bin/env python3
"""
最终的下载解决方案
"""

import requests
import json
import time

def final_download_solution():
    """最终的下载解决方案"""
    print("🎯 最终的下载解决方案...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试所有书源
    print("1. 测试所有书源...")
    try:
        # 获取所有书源
        sources_response = requests.get(f"{base_url}/api/novels/sources", timeout=10)
        if sources_response.status_code == 200:
            sources_data = sources_response.json()
            sources = sources_data.get("data", [])
            print(f"   - 可用书源数量: {len(sources)}")
            
            # 测试每个书源
            working_sources = []
            for source in sources:
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
                            print(f"   - 书源 {source_name} (ID: {source_id}): 搜索成功")
                            
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
                                print(f"     - 目录章节数: {len(chapters)}")
                                
                                if chapters:
                                    print(f"     ✅ 书源 {source_name} 完全可用")
                                    working_sources.append({
                                        'id': source_id,
                                        'name': source_name,
                                        'url': result.get("url"),
                                        'chapters': len(chapters)
                                    })
                                else:
                                    print(f"     ⚠️  书源 {source_name} 目录为空")
                            else:
                                print(f"     ❌ 书源 {source_name} 目录API失败")
                        else:
                            print(f"     ❌ 书源 {source_name} 搜索无结果")
                    else:
                        print(f"     ❌ 书源 {source_name} 搜索API失败")
                        
                except Exception as e:
                    print(f"     ❌ 书源 {source_name} 测试异常: {str(e)}")
                    continue
            
            print(f"\n   - 找到 {len(working_sources)} 个可用书源")
            for source in working_sources:
                print(f"     - {source['name']} (ID: {source['id']}): {source['chapters']} 章")
            
            # 2. 测试下载功能
            if working_sources:
                print("\n2. 测试下载功能...")
                best_source = working_sources[0]  # 使用第一个可用书源
                
                try:
                    download_response = requests.get(
                        f"{base_url}/api/novels/download",
                        params={
                            "url": best_source["url"],
                            "sourceId": best_source["id"],
                            "format": "txt"
                        },
                        timeout=300,
                        stream=True
                    )
                    
                    print(f"   - 下载状态码: {download_response.status_code}")
                    if download_response.status_code == 200:
                        # 检查响应头
                        content_type = download_response.headers.get("content-type", "")
                        content_disposition = download_response.headers.get("content-disposition", "")
                        print(f"   - Content-Type: {content_type}")
                        print(f"   - Content-Disposition: {content_disposition}")
                        
                        # 保存测试文件
                        filename = "final_test_download.txt"
                        with open(filename, "wb") as f:
                            for chunk in download_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        import os
                        file_size = os.path.getsize(filename)
                        print(f"   ✅ 下载成功，文件大小: {file_size} 字节")
                        
                        # 检查文件内容
                        if file_size > 0:
                            with open(filename, "r", encoding="utf-8") as f:
                                content = f.read(500)  # 读取前500字符
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
                        
                except Exception as e:
                    print(f"   ❌ 下载异常: {str(e)}")
                    return False
            else:
                print("   ❌ 没有找到可用的书源")
                return False
                
        else:
            print(f"   ❌ 获取书源失败: {sources_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试失败: {str(e)}")
        return False
    
    return False

def create_alternative_solution():
    """创建备用解决方案"""
    print("\n3. 创建备用解决方案...")
    
    solution = '''
🔧 备用解决方案：

1. 修复当前书源
   - 检查网站是否使用JavaScript动态加载
   - 尝试使用不同的CSS选择器
   - 添加请求延迟和重试机制

2. 使用其他书源
   - 测试所有20个书源
   - 找到可用的书源
   - 更新书源规则

3. 实现降级机制
   - 创建本地测试数据
   - 提供模拟下载功能
   - 实现错误恢复

4. 优化网络请求
   - 添加更多请求头
   - 实现请求轮换
   - 添加代理支持
'''
    print(solution)

if __name__ == "__main__":
    success = final_download_solution()
    if not success:
        create_alternative_solution()