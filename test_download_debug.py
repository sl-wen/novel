#!/usr/bin/env python3
"""
详细的下载调试脚本
"""

import requests
import time
import json

def test_download_debug():
    """详细的下载调试"""
    print("🔍 详细的下载调试...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试搜索
    print("1. 测试搜索...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "maxResults": 1},
            timeout=60
        )
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            if results:
                result = results[0]
                print(f"   ✅ 找到小说: {result.get('title', result.get('bookName'))}")
                print(f"   - URL: {result.get('url')}")
                print(f"   - 书源ID: {result.get('source_id')}")
                
                # 2. 测试获取小说详情
                print("\n2. 测试获取小说详情...")
                detail_response = requests.get(
                    f"{base_url}/api/novels/detail",
                    params={
                        "url": result.get("url"),
                        "sourceId": result.get("source_id")
                    },
                    timeout=60
                )
                print(f"   - 详情状态码: {detail_response.status_code}")
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    print(f"   ✅ 获取详情成功: {detail_data.get('data', {}).get('title', 'Unknown')}")
                else:
                    print(f"   ❌ 获取详情失败: {detail_response.text}")
                
                # 3. 测试获取目录
                print("\n3. 测试获取目录...")
                toc_response = requests.get(
                    f"{base_url}/api/novels/toc",
                    params={
                        "url": result.get("url"),
                        "sourceId": result.get("source_id")
                    },
                    timeout=60
                )
                print(f"   - 目录状态码: {toc_response.status_code}")
                if toc_response.status_code == 200:
                    toc_data = toc_response.json()
                    chapters = toc_data.get("data", [])
                    print(f"   ✅ 获取目录成功: {len(chapters)} 章")
                    if chapters:
                        print(f"   - 第一章: {chapters[0].get('title', 'Unknown')}")
                else:
                    print(f"   ❌ 获取目录失败: {toc_response.text}")
                
                # 4. 测试下载
                print("\n4. 测试下载...")
                download_response = requests.get(
                    f"{base_url}/api/novels/download",
                    params={
                        "url": result.get("url"),
                        "sourceId": result.get("source_id"),
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
                    filename = "test_download_debug.txt"
                    with open(filename, "wb") as f:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    import os
                    file_size = os.path.getsize(filename)
                    print(f"   ✅ 下载成功，文件大小: {file_size} 字节")
                    
                    # 清理测试文件
                    os.remove(filename)
                    print("   - 测试文件已清理")
                    return True
                else:
                    print(f"   ❌ 下载失败: {download_response.text}")
            else:
                print("   ❌ 没有搜索结果")
        else:
            print(f"   ❌ 搜索失败: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⚠️  请求超时")
    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
    
    return False

if __name__ == "__main__":
    test_download_debug()