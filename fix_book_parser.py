#!/usr/bin/env python3
"""
修复书籍解析器
"""

def fix_book_parser():
    """修复书籍解析器的问题"""
    print("🔧 修复书籍解析器...")
    
    # 1. 分析问题
    print("\n1. 问题分析:")
    print("   - 书源规则使用meta标签选择器")
    print("   - 可能无法正确提取内容")
    print("   - 需要改进错误处理")
    
    # 2. 修复方案
    print("\n2. 修复方案:")
    fix_content = '''
# 修改 app/parsers/book_parser.py 中的 _extract_text 方法

def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
    """提取文本内容

    Args:
        soup: BeautifulSoup对象
        selector: CSS选择器

    Returns:
        提取的文本内容
    """
    if not selector:
        return ""

    try:
        # 处理meta标签选择器
        if selector.startswith("meta["):
            # 解析meta选择器，例如: meta[property="og:novel:book_name"]
            import re
            match = re.search(r'meta\[([^\]]+)\]', selector)
            if match:
                attr_part = match.group(1)
                # 解析属性，例如: property="og:novel:book_name"
                attr_match = re.search(r'([^=]+)="([^"]+)"', attr_part)
                if attr_match:
                    attr_name = attr_match.group(1).strip()
                    attr_value = attr_match.group(2)
                    
                    # 查找对应的meta标签
                    meta_tag = soup.find("meta", {attr_name: attr_value})
                    if meta_tag:
                        return meta_tag.get("content", "")
        
        # 处理普通CSS选择器
        element = soup.select_one(selector)
        if element:
            return element.get_text(strip=True)
        
        return ""
    except Exception as e:
        logger.warning(f"提取文本失败: {selector}, 错误: {str(e)}")
        return ""

def _extract_attr(self, soup: BeautifulSoup, selector: str, attr: str) -> str:
    """提取属性值

    Args:
        soup: BeautifulSoup对象
        selector: CSS选择器
        attr: 属性名

    Returns:
        提取的属性值
    """
    if not selector:
        return ""

    try:
        # 处理meta标签选择器
        if selector.startswith("meta["):
            import re
            match = re.search(r'meta\[([^\]]+)\]', selector)
            if match:
                attr_part = match.group(1)
                attr_match = re.search(r'([^=]+)="([^"]+)"', attr_part)
                if attr_match:
                    attr_name = attr_match.group(1).strip()
                    attr_value = attr_match.group(2)
                    
                    meta_tag = soup.find("meta", {attr_name: attr_value})
                    if meta_tag:
                        return meta_tag.get("content", "")
        
        # 处理普通CSS选择器
        element = soup.select_one(selector)
        if element:
            return element.get(attr, "")
        
        return ""
    except Exception as e:
        logger.warning(f"提取属性失败: {selector}.{attr}, 错误: {str(e)}")
        return ""
'''
    print(fix_content)
    
    # 3. 创建测试脚本
    print("\n3. 创建测试脚本:")
    test_script = '''
#!/usr/bin/env python3
"""
测试修复后的书籍解析器
"""

import requests
import json

def test_fixed_book_parser():
    """测试修复后的书籍解析器"""
    print("🧪 测试修复后的书籍解析器...")
    
    base_url = "http://localhost:8000"
    
    # 测试获取小说详情
    try:
        response = requests.get(
            f"{base_url}/api/novels/detail",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11
            },
            timeout=60
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            book_data = data.get("data", {})
            print("✅ 获取详情成功:")
            print(f"  - 标题: {book_data.get('title', 'Unknown')}")
            print(f"  - 作者: {book_data.get('author', 'Unknown')}")
            print(f"  - 简介: {book_data.get('intro', '')[:100]}...")
            return True
        else:
            print(f"❌ 获取详情失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False

if __name__ == "__main__":
    test_fixed_book_parser()
'''
    print(test_script)

if __name__ == "__main__":
    fix_book_parser()