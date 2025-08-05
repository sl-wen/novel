#!/usr/bin/env python3
"""
修复目录解析器
"""

def fix_toc_parser():
    """修复目录解析器的问题"""
    print("🔧 修复目录解析器...")
    
    # 1. 分析问题
    print("\n1. 问题分析:")
    print("   - 本地模拟成功，可以找到15个章节")
    print("   - API返回空数组")
    print("   - 问题在于目录解析器的网络请求或错误处理")
    
    # 2. 修复方案
    print("\n2. 修复方案:")
    fix_content = '''
# 修复 app/parsers/toc_parser.py 中的问题

# 1. 添加更详细的日志
import logging
logger = logging.getLogger(__name__)

# 2. 修复 _fetch_html 方法，添加更多错误处理
async def _fetch_html(self, url: str) -> Optional[str]:
    """获取HTML页面"""
    try:
        logger.info(f"开始获取HTML: {url}")
        
        # 创建SSL上下文，跳过证书验证
        connector = aiohttp.TCPConnector(
            limit=settings.MAX_CONCURRENT_REQUESTS,
            ssl=False,  # 跳过SSL证书验证
            use_dns_cache=True,
            ttl_dns_cache=300,
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=10,
            sock_read=30
        )
        
        # 添加更多请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=headers
        ) as session:
            async with session.get(url) as response:
                logger.info(f"响应状态码: {response.status}")
                if response.status == 200:
                    html = await response.text()
                    logger.info(f"获取HTML成功，长度: {len(html)}")
                    return html
                else:
                    logger.error(f"请求失败: {url}, 状态码: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"请求异常: {url}, 错误: {str(e)}")
        return None

# 3. 修复 _parse_toc 方法，添加更多调试信息
def _parse_toc(self, html: str, toc_url: str) -> List[ChapterInfo]:
    """解析目录"""
    logger.info(f"开始解析目录，HTML长度: {len(html)}")
    
    soup = BeautifulSoup(html, "html.parser")
    chapters = []

    # 获取章节列表选择器
    list_selectors = self.toc_rule.get("list", "").split(",")
    if not list_selectors:
        logger.warning("未配置章节列表选择器")
        return chapters

    # 尝试多个选择器获取章节列表
    chapter_elements = []
    for selector in list_selectors:
        selector = selector.strip()
        if not selector:
            continue
            
        elements = soup.select(selector)
        logger.info(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
        if elements:
            chapter_elements = elements
            break
    
    if not chapter_elements:
        logger.warning("未找到任何章节元素")
        return chapters

    logger.info(f"开始解析 {len(chapter_elements)} 个章节元素")
    
    for index, element in enumerate(chapter_elements, 1):
        try:
            chapter = self._parse_single_chapter(element, toc_url, index)
            if chapter:
                chapters.append(chapter)
                logger.debug(f"成功解析章节 {index}: {chapter.title}")
            else:
                logger.warning(f"解析章节 {index} 失败")
        except Exception as e:
            logger.warning(f"解析单个章节失败: {str(e)}")
            continue

    logger.info(f"目录解析完成，成功解析 {len(chapters)} 个章节")
    return chapters

# 4. 修复 _parse_single_chapter 方法
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

        # 验证必要字段
        if not title or not url:
            logger.warning(f"章节 {order} 缺少必要字段: title='{title}', url='{url}'")
            return None

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
                
                # 测试下载
                print("\\n测试下载...")
                download_response = requests.get(
                    f"{base_url}/api/novels/download",
                    params={
                        "url": "https://www.0xs.net/txt/1.html",
                        "sourceId": 11,
                        "format": "txt"
                    },
                    timeout=300,
                    stream=True
                )
                
                print(f"下载状态码: {download_response.status_code}")
                if download_response.status_code == 200:
                    # 保存测试文件
                    filename = "test_fixed_download.txt"
                    with open(filename, "wb") as f:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    import os
                    file_size = os.path.getsize(filename)
                    print(f"✅ 下载成功，文件大小: {file_size} 字节")
                    
                    # 清理测试文件
                    os.remove(filename)
                    print("测试文件已清理")
                    return True
                else:
                    print(f"❌ 下载失败: {download_response.text}")
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