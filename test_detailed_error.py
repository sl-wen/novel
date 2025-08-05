#!/usr/bin/env python3
"""
详细的错误诊断
"""

import requests
import json

def test_detailed_error():
    """详细的错误诊断"""
    print("🔍 详细的错误诊断...")
    
    base_url = "http://localhost:8000"
    
    # 测试直接访问网站
    print("1. 测试直接访问网站...")
    try:
        import urllib.request
        import urllib.parse
        
        url = "https://www.0xs.net/txt/1.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
            print(f"   ✅ 网站访问成功，HTML长度: {len(html)}")
            
            # 检查meta标签
            if 'meta[property="og:novel:book_name"]' in html:
                print("   ✅ 找到meta标签")
            else:
                print("   ❌ 未找到meta标签")
                
            # 检查标题
            if '斗破苍穹' in html:
                print("   ✅ 找到标题")
            else:
                print("   ❌ 未找到标题")
                
    except Exception as e:
        print(f"   ❌ 网站访问失败: {str(e)}")
    
    # 测试API详情
    print("\n2. 测试API详情...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/detail",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11
            },
            timeout=60
        )
        
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 500:
            error_data = response.json()
            print(f"   - 错误信息: {error_data.get('message', 'Unknown error')}")
            
            # 分析错误
            error_msg = error_data.get('message', '')
            if "'NoneType' object has no attribute 'title'" in error_msg:
                print("   💡 问题分析: Book对象为None，可能是解析失败")
            elif "获取小说详情失败" in error_msg:
                print("   💡 问题分析: 网络请求或解析失败")
        else:
            print(f"   - 响应: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ❌ API调用失败: {str(e)}")
    
    # 检查书源规则
    print("\n3. 检查书源规则...")
    try:
        import json
        with open("rules/rule-11.json", "r", encoding="utf-8") as f:
            rule = json.load(f)
        
        book_rule = rule.get("book", {})
        print(f"   - 书源名称: {rule.get('name', 'Unknown')}")
        print(f"   - 书源URL: {rule.get('url', 'Unknown')}")
        print(f"   - 标题选择器: {book_rule.get('name', 'None')}")
        print(f"   - 作者选择器: {book_rule.get('author', 'None')}")
        print(f"   - 简介选择器: {book_rule.get('intro', 'None')}")
        
    except Exception as e:
        print(f"   ❌ 读取书源规则失败: {str(e)}")
    
    # 建议解决方案
    print("\n4. 建议解决方案:")
    print("   🔧 可能的解决方案:")
    print("   - 检查网站是否可访问")
    print("   - 验证meta标签选择器是否正确")
    print("   - 尝试使用不同的书源")
    print("   - 增加网络请求重试机制")
    print("   - 添加更详细的错误日志")

if __name__ == "__main__":
    test_detailed_error()