#!/usr/bin/env python3
"""
修复目录解析器
"""

def fix_toc_parser():
    """修复目录解析器的问题"""
    print("🔧 修复目录解析器...")
    
    # 1. 分析问题
    print("\n1. 问题分析:")
    print("   - 目录规则中的title和url选择器为空")
    print("   - 无法提取章节标题和URL")
    print("   - 需要修复书源规则配置")
    
    # 2. 修复方案
    print("\n2. 修复方案:")
    fix_content = '''
# 修复 rules/rule-11.json 中的目录配置

{
  "toc": {
    "list": ".catalog > div > ul > ul > li > a",
    "title": "text",  # 使用元素文本作为标题
    "url": "href",    # 使用href属性作为URL
    "has_pages": false,
    "next_page": ""
  }
}

# 修改 app/parsers/toc_parser.py 中的 _parse_single_chapter 方法

def _parse_single_chapter(
    self, element: BeautifulSoup, toc_url: str, order: int
) -> Optional[ChapterInfo]:
    """解析单个章节"""
    try:
        # 获取章节标题
        title_selector = self.toc_rule.get("title", "")
        if title_selector == "text":
            # 直接使用元素文本
            title = element.get_text(strip=True)
        else:
            title = self._extract_text(element, title_selector)

        # 获取章节URL
        url_selector = self.toc_rule.get("url", "")
        if url_selector == "href":
            # 直接使用href属性
            url = element.get("href", "")
        else:
            url = self._extract_attr(element, url_selector, "href")

        # 构建完整URL
        if url and not url.startswith(("http://", "https://")):
            base_url = self.source.rule.get("url", "")
            url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"

        # 获取章节字数（可选）
        word_count_selector = self.toc_rule.get("word_count", "")
        word_count = self._extract_text(element, word_count_selector)

        # 获取更新时间（可选）
        update_time_selector = self.toc_rule.get("update_time", "")
        update_time = self._extract_text(element, update_time_selector)

        return ChapterInfo(
            title=title or f"第{order}章",
            url=url or "",
            order=order,
            word_count=word_count or "",
            update_time=update_time or "",
            source_id=self.source.id,
            source_name=self.source.rule.get("name", self.source.id),
        )
    except Exception as e:
        logger.warning(f"解析章节失败: {str(e)}")
        return None
'''
    print(fix_content)
    
    # 3. 创建测试脚本
    print("\n3. 创建测试脚本:")
    test_script = '''
#!/usr/bin/env python3
"""
测试修复后的目录解析器
"""

import requests
import json

def test_fixed_toc_parser():
    """测试修复后的目录解析器"""
    print("🧪 测试修复后的目录解析器...")
    
    base_url = "http://localhost:8000"
    
    # 测试获取目录
    try:
        response = requests.get(
            f"{base_url}/api/novels/toc",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11
            },
            timeout=60
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            chapters = data.get("data", [])
            print(f"✅ 获取目录成功: {len(chapters)} 章")
            
            if chapters:
                print("前5章:")
                for i, chapter in enumerate(chapters[:5]):
                    print(f"  {i+1}. {chapter.get('title', 'Unknown')}")
                    print(f"     URL: {chapter.get('url', 'Unknown')}")
            else:
                print("❌ 没有找到章节")
                
        else:
            print(f"❌ 获取目录失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 错误: {str(e)}")

if __name__ == "__main__":
    test_fixed_toc_parser()
'''
    print(test_script)

if __name__ == "__main__":
    fix_toc_parser()