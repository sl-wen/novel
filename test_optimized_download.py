#!/usr/bin/env python3
"""
优化的下载测试
"""

import requests
import time
import json

def test_optimized_download():
    """优化的下载测试"""
    print("🚀 优化的下载测试...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试单个书源搜索
    print("1. 测试单个书源搜索...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "maxResults": 1},
            timeout=60  # 增加超时时间
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
                
                # 2. 测试下载
                print("\n2. 测试下载...")
                download_response = requests.get(
                    f"{base_url}/api/novels/download",
                    params={
                        "url": result.get("url"),
                        "sourceId": result.get("source_id"),
                        "format": "txt"
                    },
                    timeout=300,  # 下载超时5分钟
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
                    filename = "test_download_fixed.txt"
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
                        return True
                    else:
                        print("   ❌ 下载的文件为空")
                        return False
                else:
                    print(f"   ❌ 下载失败: {download_response.text}")
            else:
                print("   ❌ 没有搜索结果")
        else:
            print(f"   ❌ 搜索失败: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⚠️  请求超时，可能需要更长时间")
    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
    
    return False

if __name__ == "__main__":
    test_optimized_download()