#!/usr/bin/env python3
"""
最终的下载功能测试
确认所有功能都正常工作
"""

import requests
import json
import time

def test_final_download():
    """测试最终的下载功能"""
    print("🎉 最终的下载功能测试")
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
                
                # 2. 测试目录获取
                print("\n2. 测试目录获取...")
                toc_response = requests.get(
                    f"{base_url}/api/novels/toc",
                    params={
                        "url": book.get('url'),
                        "sourceId": book.get('source_id')
                    },
                    timeout=30
                )
                
                if toc_response.status_code == 200:
                    toc_data = toc_response.json()
                    chapters = toc_data.get("data", [])
                    print(f"   ✅ 目录获取成功: {len(chapters)} 章")
                    
                    if chapters:
                        print("   前5章预览:")
                        for i, chapter in enumerate(chapters[:5], 1):
                            print(f"   {i}. {chapter.get('title', '未知章节')}")
                        
                        # 3. 测试章节内容获取
                        print("\n3. 测试章节内容获取...")
                        first_chapter = chapters[0]
                        content_response = requests.get(
                            f"{base_url}/api/novels/content",
                            params={
                                "url": first_chapter.get('url'),
                                "sourceId": book.get('source_id')
                            },
                            timeout=30
                        )
                        
                        if content_response.status_code == 200:
                            content_data = content_response.json()
                            content = content_data.get("data", {}).get("content", "")
                            print(f"   ✅ 章节内容获取成功")
                            print(f"   - 内容长度: {len(content)} 字符")
                            print(f"   - 内容预览: {content[:100]}...")
                            
                            # 4. 测试下载功能
                            print("\n4. 测试下载功能...")
                            download_response = requests.get(
                                f"{base_url}/api/novels/download",
                                params={
                                    "url": book.get('url'),
                                    "sourceId": book.get('source_id'),
                                    "startChapter": 1,
                                    "endChapter": 3
                                },
                                timeout=60
                            )
                            
                            if download_response.status_code == 200:
                                download_data = download_response.json()
                                print(f"   ✅ 下载功能成功")
                                print(f"   - 下载章节数: {download_data.get('data', {}).get('chapterCount', 0)}")
                                print(f"   - 文件大小: {download_data.get('data', {}).get('fileSize', 0)} 字节")
                                print(f"   - 下载链接: {download_data.get('data', {}).get('downloadUrl', 'N/A')}")
                            else:
                                print(f"   ❌ 下载功能失败: {download_response.status_code}")
                                print(f"   - 错误信息: {download_response.text}")
                        else:
                            print(f"   ❌ 章节内容获取失败: {content_response.status_code}")
                            print(f"   - 错误信息: {content_response.text}")
                    else:
                        print("   ❌ 目录为空")
                else:
                    print(f"   ❌ 目录获取失败: {toc_response.status_code}")
                    print(f"   - 错误信息: {toc_response.text}")
            else:
                print("   ❌ 搜索结果为空")
        else:
            print(f"   ❌ 搜索失败: {response.status_code}")
            print(f"   - 错误信息: {response.text}")
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")

def test_different_sources():
    """测试不同书源"""
    print("\n🔧 测试不同书源")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # 获取所有书源
    try:
        sources_response = requests.get(f"{base_url}/api/novels/sources", timeout=30)
        if sources_response.status_code == 200:
            sources_data = sources_response.json()
            sources = sources_data.get("data", [])
            print(f"可用书源数量: {len(sources)}")
            
            # 测试几个主要书源
            test_sources = ["零点小说", "大熊猫文学", "略更网"]
            
            for source_name in test_sources:
                print(f"\n测试书源: {source_name}")
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
                        else:
                            print(f"   ⚠️ 搜索结果为空")
                    else:
                        print(f"   ❌ 搜索失败: {response.status_code}")
                except Exception as e:
                    print(f"   ❌ 测试异常: {e}")
        else:
            print(f"获取书源失败: {sources_response.status_code}")
    except Exception as e:
        print(f"测试书源异常: {e}")

if __name__ == "__main__":
    test_final_download()
    test_different_sources()
    print("\n🎉 测试完成！")