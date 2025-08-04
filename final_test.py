#!/usr/bin/env python3
"""
最终测试脚本
验证修复后的API功能
"""

import time

import requests


def test_api_endpoints():
    """测试API端点"""
    print("🚀 最终API功能测试")
    print("=" * 50)

    base_url = "http://localhost:8000/api/novels"

    # 1. 测试搜索功能
    print("1. 测试搜索功能...")
    try:
        response = requests.get(
            f"{base_url}/search",
            params={"keyword": "斗破苍穹", "maxResults": 3},
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 搜索成功，找到 {len(data.get('data', []))} 条结果")
            if data.get("data"):
                first_result = data["data"][0]
                book_url = first_result.get("url")
                source_id = first_result.get("source_id")
                print(
                    f"   - 书名: {first_result.get('title', first_result.get('bookName'))}"
                )
                print(f"   - 作者: {first_result.get('author')}")
        else:
            print(f"   ❌ 搜索失败，状态码: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ 搜索请求异常: {str(e)}")
        return False

    # 2. 测试书源功能
    print("\n2. 测试书源功能...")
    try:
        response = requests.get(f"{base_url}/sources", timeout=30)
        if response.status_code == 200:
            data = response.json()
            sources = data.get("data", [])
            print(f"   ✅ 获取书源成功，共 {len(sources)} 个书源")
        else:
            print(f"   ❌ 获取书源失败，状态码: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ❌ 书源请求异常: {str(e)}")

    # 3. 测试目录功能（如果有搜索结果）
    if "book_url" in locals() and book_url and "source_id" in locals() and source_id:
        print("\n3. 测试目录功能...")
        try:
            response = requests.get(
                f"{base_url}/toc",
                params={"url": book_url, "sourceId": source_id, "start": 1, "end": 5},
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                toc = data.get("data", [])
                print(f"   ✅ 获取目录成功，找到 {len(toc)} 章")
                if toc:
                    print("   - 章节预览:")
                    for i, chapter in enumerate(toc[:3]):
                        print(f"     {i+1}. {chapter.get('title', '无标题')}")
                else:
                    print("   - ⚠️  目录为空（可能是网站结构变化）")
            else:
                print(f"   ❌ 获取目录失败，状态码: {response.status_code}")
                print(f"   响应: {response.text}")
        except Exception as e:
            print(f"   ❌ 目录请求异常: {str(e)}")

    print("\n" + "=" * 50)
    print("🎊 测试完成！")
    print("\n💡 说明:")
    print("- 如果搜索和书源功能正常，说明核心功能已修复")
    print("- 目录功能依赖于外部网站，可能因网站变化而受影响")
    print("- 这是正常现象，不影响API的整体功能")

    return True


if __name__ == "__main__":
    print("请确保API服务正在运行...")
    print(
        "启动命令: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    )
    print()

    # 等待用户确认
    input("按回车键开始测试...")

    test_api_endpoints()
