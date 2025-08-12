#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书源配置测试工具
测试优化后的书源配置文件的功能
"""

import json
import requests
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BookSourceTester:
    """书源配置测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
        self.test_results = []
    
    def load_rule(self, file_path: str) -> Dict[str, Any]:
        """加载书源规则文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载规则文件失败 {file_path}: {e}")
            return {}
    
    def extract_with_selectors(self, soup: BeautifulSoup, selectors: List[str], attr: str = 'text') -> Optional[str]:
        """使用多个选择器提取内容"""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    if attr == 'text':
                        text = elements[0].get_text(strip=True)
                        if text:
                            return text
                    elif attr == 'href':
                        href = elements[0].get('href')
                        if href:
                            return href
                    else:
                        value = elements[0].get(attr)
                        if value:
                            return value
            except Exception as e:
                logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        return None
    
    def test_website_accessibility(self, rule: Dict[str, Any]) -> Tuple[bool, str]:
        """测试网站可访问性"""
        try:
            url = rule.get('url', '')
            if not url:
                return False, "缺少URL配置"
            
            timeout = rule.get('timeout', 15000) / 1000  # 转换为秒
            response = self.session.get(url, timeout=timeout)
            
            if response.status_code == 200:
                return True, f"网站可访问 (状态码: {response.status_code})"
            else:
                return False, f"HTTP错误 (状态码: {response.status_code})"
                
        except requests.exceptions.Timeout:
            return False, "请求超时"
        except requests.exceptions.ConnectionError:
            return False, "连接失败"
        except Exception as e:
            return False, f"访问失败: {str(e)}"
    
    def test_search_function(self, rule: Dict[str, Any]) -> Tuple[bool, str, List[Dict]]:
        """测试搜索功能"""
        search_config = rule.get('search', {})
        if not search_config:
            return False, "缺少搜索配置", []
        
        try:
            # 使用测试关键词
            test_keywords = ["斗破苍穹", "完美世界", "遮天", "凡人修仙传"]
            
            for keyword in test_keywords:
                try:
                    # 构造搜索请求
                    search_url = search_config.get('url', '')
                    if not search_url:
                        continue
                    
                    # 处理搜索URL
                    if '%s' in search_url:
                        search_url = search_url.replace('%s', keyword)
                    
                    method = search_config.get('method', 'get').lower()
                    data = search_config.get('data', '')
                    
                    if method == 'post':
                        # 处理POST数据
                        if data:
                            data = data.replace('%s', keyword)
                            # 简单解析数据格式
                            try:
                                if data.startswith('{') and data.endswith('}'):
                                    # JSON格式
                                    data = json.loads(data.replace('{', '{"').replace(': ', '": "').replace(', ', '", "').replace('}', '"}'))
                                else:
                                    # 表单格式
                                    data = {data.split(':')[0]: keyword}
                            except:
                                data = {'searchkey': keyword}
                        
                        response = self.session.post(search_url, data=data, timeout=10)
                    else:
                        response = self.session.get(search_url, timeout=10)
                    
                    if response.status_code != 200:
                        continue
                    
                    # 解析搜索结果
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 获取搜索结果列表
                    list_selectors = search_config.get('list', [])
                    if isinstance(list_selectors, str):
                        list_selectors = [list_selectors]
                    
                    results = []
                    for selector in list_selectors:
                        try:
                            items = soup.select(selector)
                            if items:
                                for item in items[:3]:  # 只取前3个结果
                                    result = {}
                                    
                                    # 提取书名
                                    name_selectors = search_config.get('name', [])
                                    if isinstance(name_selectors, str):
                                        name_selectors = [name_selectors]
                                    
                                    name = self.extract_with_selectors(BeautifulSoup(str(item), 'html.parser'), name_selectors)
                                    if name:
                                        result['name'] = name
                                    
                                    # 提取作者
                                    author_selectors = search_config.get('author', [])
                                    if isinstance(author_selectors, str):
                                        author_selectors = [author_selectors]
                                    
                                    if author_selectors:
                                        author = self.extract_with_selectors(BeautifulSoup(str(item), 'html.parser'), author_selectors)
                                        if author:
                                            result['author'] = author
                                    
                                    if result:
                                        results.append(result)
                                
                                if results:
                                    return True, f"搜索功能正常，找到 {len(results)} 个结果", results
                        except Exception as e:
                            logger.debug(f"解析搜索结果失败: {e}")
                            continue
                
                except Exception as e:
                    logger.debug(f"搜索 {keyword} 失败: {e}")
                    continue
            
            return False, "搜索功能无法正常工作", []
            
        except Exception as e:
            return False, f"搜索测试失败: {str(e)}", []
    
    def test_book_info(self, rule: Dict[str, Any]) -> Tuple[bool, str]:
        """测试书籍详情功能"""
        try:
            # 这里简化测试，主要检查配置完整性
            book_config = rule.get('book', {})
            if not book_config:
                return False, "缺少书籍详情配置"
            
            required_fields = ['name', 'author']
            missing_fields = []
            
            for field in required_fields:
                if field not in book_config or not book_config[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return False, f"缺少必要字段: {', '.join(missing_fields)}"
            
            return True, "书籍详情配置完整"
            
        except Exception as e:
            return False, f"书籍详情测试失败: {str(e)}"
    
    def test_toc_function(self, rule: Dict[str, Any]) -> Tuple[bool, str]:
        """测试目录功能"""
        try:
            toc_config = rule.get('toc', {})
            if not toc_config:
                return False, "缺少目录配置"
            
            required_fields = ['list', 'title', 'url']
            missing_fields = []
            
            for field in required_fields:
                if field not in toc_config or not toc_config[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return False, f"缺少必要字段: {', '.join(missing_fields)}"
            
            return True, "目录配置完整"
            
        except Exception as e:
            return False, f"目录测试失败: {str(e)}"
    
    def test_chapter_function(self, rule: Dict[str, Any]) -> Tuple[bool, str]:
        """测试章节功能"""
        try:
            chapter_config = rule.get('chapter', {})
            if not chapter_config:
                return False, "缺少章节配置"
            
            required_fields = ['title', 'content']
            missing_fields = []
            
            for field in required_fields:
                if field not in chapter_config or not chapter_config[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return False, f"缺少必要字段: {', '.join(missing_fields)}"
            
            # 检查广告过滤配置
            ad_patterns = chapter_config.get('ad_patterns', [])
            if not ad_patterns:
                return True, "章节配置完整，但建议添加广告过滤规则"
            
            return True, f"章节配置完整，包含 {len(ad_patterns)} 个广告过滤规则"
            
        except Exception as e:
            return False, f"章节测试失败: {str(e)}"
    
    def test_single_source(self, rule_file: str) -> Dict[str, Any]:
        """测试单个书源"""
        logger.info(f"开始测试书源: {rule_file}")
        
        rule = self.load_rule(rule_file)
        if not rule:
            return {
                'file': rule_file,
                'name': 'Unknown',
                'status': 'failed',
                'error': '无法加载配置文件',
                'tests': {}
            }
        
        source_name = rule.get('name', 'Unknown')
        result = {
            'file': rule_file,
            'name': source_name,
            'status': 'unknown',
            'tests': {},
            'search_results': []
        }
        
        # 1. 测试网站可访问性
        logger.info(f"  测试网站可访问性...")
        accessible, access_msg = self.test_website_accessibility(rule)
        result['tests']['accessibility'] = {
            'status': 'passed' if accessible else 'failed',
            'message': access_msg
        }
        
        # 2. 测试搜索功能
        logger.info(f"  测试搜索功能...")
        search_ok, search_msg, search_results = self.test_search_function(rule)
        result['tests']['search'] = {
            'status': 'passed' if search_ok else 'failed',
            'message': search_msg
        }
        result['search_results'] = search_results
        
        # 3. 测试书籍详情
        logger.info(f"  测试书籍详情配置...")
        book_ok, book_msg = self.test_book_info(rule)
        result['tests']['book_info'] = {
            'status': 'passed' if book_ok else 'failed',
            'message': book_msg
        }
        
        # 4. 测试目录功能
        logger.info(f"  测试目录配置...")
        toc_ok, toc_msg = self.test_toc_function(rule)
        result['tests']['toc'] = {
            'status': 'passed' if toc_ok else 'failed',
            'message': toc_msg
        }
        
        # 5. 测试章节功能
        logger.info(f"  测试章节配置...")
        chapter_ok, chapter_msg = self.test_chapter_function(rule)
        result['tests']['chapter'] = {
            'status': 'passed' if chapter_ok else 'failed',
            'message': chapter_msg
        }
        
        # 计算总体状态
        passed_tests = sum(1 for test in result['tests'].values() if test['status'] == 'passed')
        total_tests = len(result['tests'])
        
        if passed_tests == total_tests:
            result['status'] = 'passed'
        elif passed_tests > 0:
            result['status'] = 'partial'
        else:
            result['status'] = 'failed'
        
        result['score'] = f"{passed_tests}/{total_tests}"
        
        return result
    
    def test_all_sources(self, rules_dir: str, pattern: str = "optimized-rule-*.json") -> List[Dict[str, Any]]:
        """测试所有书源"""
        rules_path = Path(rules_dir)
        rule_files = list(rules_path.glob(pattern))
        
        logger.info(f"找到 {len(rule_files)} 个书源配置文件")
        
        results = []
        for rule_file in sorted(rule_files):
            try:
                result = self.test_single_source(str(rule_file))
                results.append(result)
                
                # 添加延迟避免请求过于频繁
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"测试 {rule_file} 时出错: {e}")
                results.append({
                    'file': str(rule_file),
                    'name': 'Unknown',
                    'status': 'error',
                    'error': str(e),
                    'tests': {}
                })
        
        self.test_results = results
        return results
    
    def generate_test_report(self, results: List[Dict[str, Any]]) -> str:
        """生成测试报告"""
        report = []
        report.append("# 书源配置测试报告\n")
        report.append(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"测试书源数量: {len(results)}\n")
        
        # 统计信息
        passed = sum(1 for r in results if r['status'] == 'passed')
        partial = sum(1 for r in results if r['status'] == 'partial')
        failed = sum(1 for r in results if r['status'] == 'failed')
        error = sum(1 for r in results if r['status'] == 'error')
        
        report.append("## 测试统计\n")
        report.append(f"- ✅ 完全通过: {passed} ({passed/len(results)*100:.1f}%)")
        report.append(f"- ⚠️  部分通过: {partial} ({partial/len(results)*100:.1f}%)")
        report.append(f"- ❌ 测试失败: {failed} ({failed/len(results)*100:.1f}%)")
        report.append(f"- 🔥 运行错误: {error} ({error/len(results)*100:.1f}%)\n")
        
        # 详细结果
        report.append("## 详细测试结果\n")
        
        for result in results:
            status_icon = {
                'passed': '✅',
                'partial': '⚠️',
                'failed': '❌',
                'error': '🔥',
                'unknown': '❓'
            }.get(result['status'], '❓')
            
            report.append(f"### {status_icon} {result['name']} ({result.get('score', 'N/A')})\n")
            report.append(f"**文件**: `{Path(result['file']).name}`\n")
            
            if 'tests' in result and result['tests']:
                report.append("**测试详情**:")
                for test_name, test_result in result['tests'].items():
                    test_icon = '✅' if test_result['status'] == 'passed' else '❌'
                    test_name_cn = {
                        'accessibility': '网站可访问性',
                        'search': '搜索功能',
                        'book_info': '书籍详情',
                        'toc': '目录功能',
                        'chapter': '章节功能'
                    }.get(test_name, test_name)
                    
                    report.append(f"- {test_icon} {test_name_cn}: {test_result['message']}")
            
            # 显示搜索结果示例
            if result.get('search_results'):
                report.append(f"\n**搜索结果示例** (共{len(result['search_results'])}个):")
                for i, search_result in enumerate(result['search_results'][:2], 1):
                    name = search_result.get('name', 'N/A')
                    author = search_result.get('author', 'N/A')
                    report.append(f"  {i}. 《{name}》 - {author}")
            
            if 'error' in result:
                report.append(f"\n**错误信息**: {result['error']}")
            
            report.append("")
        
        # 建议和总结
        report.append("## 优化建议\n")
        
        # 统计各类问题
        accessibility_issues = sum(1 for r in results if r.get('tests', {}).get('accessibility', {}).get('status') == 'failed')
        search_issues = sum(1 for r in results if r.get('tests', {}).get('search', {}).get('status') == 'failed')
        
        if accessibility_issues > 0:
            report.append(f"1. **网站可访问性问题** ({accessibility_issues}个书源)")
            report.append("   - 检查网站是否正常运行")
            report.append("   - 确认URL配置正确")
            report.append("   - 考虑使用代理或更换域名\n")
        
        if search_issues > 0:
            report.append(f"2. **搜索功能问题** ({search_issues}个书源)")
            report.append("   - 验证搜索URL和参数配置")
            report.append("   - 检查网站搜索接口是否变更")
            report.append("   - 更新选择器规则\n")
        
        report.append("## 使用说明\n")
        report.append("1. 优先使用 ✅ 完全通过的书源")
        report.append("2. ⚠️ 部分通过的书源可以使用，但可能存在功能限制")
        report.append("3. ❌ 失败的书源需要进一步调试和修复")
        report.append("4. 定期重新测试以确保书源持续可用")
        
        return "\n".join(report)

def main():
    """主函数"""
    tester = BookSourceTester()
    
    # 设置路径
    rules_dir = "/workspace/rules"
    
    print("开始测试优化后的书源配置...")
    print(f"规则目录: {rules_dir}")
    
    # 测试所有优化后的书源
    results = tester.test_all_sources(rules_dir)
    
    # 生成测试报告
    report = tester.generate_test_report(results)
    
    # 保存报告
    report_file = "/workspace/book_source_test_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n测试完成！")
    print(f"测试书源数量: {len(results)}")
    
    # 显示简要统计
    passed = sum(1 for r in results if r['status'] == 'passed')
    partial = sum(1 for r in results if r['status'] == 'partial')
    failed = sum(1 for r in results if r['status'] == 'failed')
    
    print(f"✅ 完全通过: {passed}")
    print(f"⚠️ 部分通过: {partial}")
    print(f"❌ 测试失败: {failed}")
    print(f"📄 测试报告: {report_file}")

if __name__ == "__main__":
    main()