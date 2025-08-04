#!/usr/bin/env python3
"""
测试修复后的API
参考test_actual_search.py的测试方式
"""

import json
import time

import requests


def test_api():
    """测试API功能"""
    base_url = "http://localhost:8000"

    print("🔍 测试健康检查...")
    try:
        response = requests.get(f"{base_url}/api/novels/health", timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"健康检查失败: {str(e)}")

    print("\n🔍 测试书源获取...")
    try:
        response = requests.get(f"{base_url}/api/novels/sources", timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"书源数量: {len(data.get('data', []))}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"书源获取失败: {str(e)}")

    print("\n🔍 测试搜索功能...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search?keyword=斗破苍穹", timeout=30
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            print(f"搜索结果数量: {len(results)}")
            if results:
                first_result = results[0]
                print(
                    f"第一个结果: {first_result.get('bookName')} - {first_result.get('author')}"
                )
                print(f"URL: {first_result.get('url')}")
                print(f"最新章节: {first_result.get('latestChapter')}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"搜索失败: {str(e)}")


if __name__ == "__main__":
    print("📚 测试修复后的API")
    print("=" * 50)
    test_api()
    print("\n✅ 测试完成")
