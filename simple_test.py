#!/usr/bin/env python3
"""
简化的测试脚本
"""

import requests
import json

def simple_test():
    """简化的测试"""
    print("🧪 简化的测试...")
    
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
                print(f"   ✅ 搜索成功: {result.get('title', result.get('bookName'))}")
                print(f"   - URL: {result.get('url')}")
                print(f"   - 书源ID: {result.get('source_id')}")
                
                # 2. 测试目录
                print("\n2. 测试目录...")
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
                    print(f"   - 目录章节数: {len(chapters)}")
                    
                    if chapters:
                        print("   ✅ 目录解析成功")
                        
                        # 3. 测试下载
                        print("\n3. 测试下载...")
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
                            # 保存测试文件
                            filename = "simple_test_download.txt"
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
                            print("   🎉 下载功能完全修复！")
                            return True
                        else:
                            print(f"   ❌ 下载失败: {download_response.text}")
                    else:
                        print("   ❌ 目录为空")
                else:
                    print(f"   ❌ 目录API失败: {toc_response.text}")
            else:
                print("   ❌ 搜索无结果")
        else:
            print(f"   ❌ 搜索失败: {response.text}")
            
    except Exception as e:
        print(f"   ❌ 测试异常: {str(e)}")
    
    return False

if __name__ == "__main__":
    simple_test()