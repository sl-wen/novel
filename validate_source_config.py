#!/usr/bin/env python3
"""
书源配置验证工具

用于验证书源配置文件的正确性和完整性。
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


class SourceConfigValidator:
    """书源配置验证器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.suggestions = []
    
    def validate_source_config(self, config: Dict[str, Any], source_id: int) -> bool:
        """验证书源配置"""
        self.errors.clear()
        self.warnings.clear()
        self.suggestions.clear()
        
        # 基本字段验证
        self._validate_basic_fields(config, source_id)
        
        # 搜索配置验证
        if 'search' in config:
            self._validate_search_config(config['search'])
        
        # 书籍详情配置验证
        if 'book' in config:
            self._validate_book_config(config['book'])
        
        # 目录配置验证
        if 'toc' in config:
            self._validate_toc_config(config['toc'])
        
        # 章节配置验证
        if 'chapter' in config:
            self._validate_chapter_config(config['chapter'])
        
        # 高级配置验证
        self._validate_advanced_config(config)
        
        return len(self.errors) == 0
    
    def _validate_basic_fields(self, config: Dict[str, Any], source_id: int):
        """验证基本字段"""
        required_fields = ['id', 'name', 'url', 'enabled', 'type']
        
        for field in required_fields:
            if field not in config:
                self.errors.append(f"缺少必需字段: {field}")
        
        # 验证ID匹配
        if 'id' in config and config['id'] != source_id:
            self.errors.append(f"配置文件中的ID ({config['id']}) 与文件名不匹配 ({source_id})")
        
        # 验证URL格式
        if 'url' in config:
            url = config['url']
            if not url.startswith(('http://', 'https://')):
                self.errors.append(f"URL格式错误: {url}")
        
        # 验证类型
        if 'type' in config:
            valid_types = ['html', 'json', 'xml']
            if config['type'] not in valid_types:
                self.warnings.append(f"未知的类型: {config['type']}, 支持的类型: {valid_types}")
    
    def _validate_search_config(self, search_config: Dict[str, Any]):
        """验证搜索配置"""
        if 'url' not in search_config:
            self.errors.append("搜索配置缺少url字段")
        
        if 'list' not in search_config:
            self.errors.append("搜索配置缺少list选择器")
        
        required_selectors = ['name', 'author']
        for selector in required_selectors:
            if selector not in search_config or not search_config[selector]:
                self.warnings.append(f"搜索配置缺少{selector}选择器")
    
    def _validate_book_config(self, book_config: Dict[str, Any]):
        """验证书籍详情配置"""
        important_fields = ['name', 'author', 'intro']
        
        for field in important_fields:
            if field not in book_config or not book_config[field]:
                self.warnings.append(f"书籍配置缺少{field}字段")
        
        # 验证选择器格式
        for field, selectors in book_config.items():
            if isinstance(selectors, list):
                for selector in selectors:
                    if not self._is_valid_css_selector(selector):
                        self.warnings.append(f"可能无效的CSS选择器: {field}.{selector}")
    
    def _validate_toc_config(self, toc_config: Dict[str, Any]):
        """验证目录配置"""
        if 'list' not in toc_config:
            self.errors.append("目录配置缺少list选择器")
        else:
            # 检查是否有多个备用选择器
            list_selector = toc_config['list']
            if ',' not in list_selector:
                self.suggestions.append("建议为目录list选择器添加备用选项，用逗号分隔")
        
        if 'title' not in toc_config:
            self.warnings.append("目录配置缺少title选择器")
        
        if 'url' not in toc_config:
            self.warnings.append("目录配置缺少url选择器")
        
        # 验证URL转换规则
        if 'url_transform' in toc_config:
            transform = toc_config['url_transform']
            if 'pattern' not in transform or 'replacement' not in transform:
                self.errors.append("url_transform配置不完整，需要pattern和replacement字段")
            else:
                try:
                    re.compile(transform['pattern'])
                except re.error as e:
                    self.errors.append(f"url_transform正则表达式错误: {e}")
    
    def _validate_chapter_config(self, chapter_config: Dict[str, Any]):
        """验证章节配置"""
        if 'content' not in chapter_config:
            self.errors.append("章节配置缺少content选择器")
        else:
            content_selectors = chapter_config['content']
            if isinstance(content_selectors, list):
                if len(content_selectors) < 3:
                    self.suggestions.append("建议为章节content选择器添加更多备用选项")
            elif isinstance(content_selectors, str):
                if ',' not in content_selectors:
                    self.suggestions.append("建议为章节content选择器添加备用选项，用逗号分隔")
        
        # 验证广告过滤模式
        if 'ad_patterns' in chapter_config:
            ad_patterns = chapter_config['ad_patterns']
            for pattern in ad_patterns:
                try:
                    re.compile(pattern)
                except re.error as e:
                    self.errors.append(f"广告过滤正则表达式错误: {pattern} - {e}")
    
    def _validate_advanced_config(self, config: Dict[str, Any]):
        """验证高级配置"""
        # 验证超时设置
        if 'timeout' in config:
            timeout = config['timeout']
            if timeout < 5000 or timeout > 60000:
                self.warnings.append(f"超时设置可能不合理: {timeout}ms，建议范围: 5000-60000ms")
        
        # 验证重试次数
        if 'retry_count' in config:
            retry_count = config['retry_count']
            if retry_count < 1 or retry_count > 5:
                self.warnings.append(f"重试次数可能不合理: {retry_count}，建议范围: 1-5")
        
        # 验证并发限制
        if 'concurrent_limit' in config:
            concurrent_limit = config['concurrent_limit']
            if concurrent_limit < 1 or concurrent_limit > 10:
                self.warnings.append(f"并发限制可能不合理: {concurrent_limit}，建议范围: 1-10")
        
        # 验证User-Agent
        if 'user_agent' not in config:
            self.suggestions.append("建议添加user_agent配置")
        
        # 验证请求头
        if 'headers' not in config:
            self.suggestions.append("建议添加headers配置")
    
    def _is_valid_css_selector(self, selector: str) -> bool:
        """简单的CSS选择器有效性检查"""
        if not selector or not isinstance(selector, str):
            return False
        
        # 基本的CSS选择器格式检查
        invalid_patterns = [
            r'^\s*$',  # 空白
            r'^[0-9]',  # 以数字开头
            r'[<>]',    # 包含HTML标签符号
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, selector):
                return False
        
        return True
    
    def get_report(self) -> str:
        """生成验证报告"""
        report = []
        
        if self.errors:
            report.append("❌ 错误:")
            for error in self.errors:
                report.append(f"  - {error}")
        
        if self.warnings:
            report.append("\n⚠️  警告:")
            for warning in self.warnings:
                report.append(f"  - {warning}")
        
        if self.suggestions:
            report.append("\n💡 建议:")
            for suggestion in self.suggestions:
                report.append(f"  - {suggestion}")
        
        if not self.errors and not self.warnings and not self.suggestions:
            report.append("✅ 配置验证通过，未发现问题")
        
        return "\n".join(report)


def validate_single_source(source_file: Path) -> bool:
    """验证单个书源文件"""
    print(f"\n验证书源文件: {source_file.name}")
    print("=" * 50)
    
    try:
        # 从文件名提取书源ID
        source_id = int(source_file.stem.split("-")[1])
        
        # 读取配置文件
        with open(source_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 验证配置
        validator = SourceConfigValidator()
        is_valid = validator.validate_source_config(config, source_id)
        
        # 输出报告
        print(validator.get_report())
        
        return is_valid
        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {source_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def validate_all_sources(rules_dir: Path) -> Dict[str, bool]:
    """验证所有书源文件"""
    print("批量验证所有书源配置")
    print("=" * 50)
    
    results = {}
    rule_files = list(rules_dir.glob("rule-*.json"))
    
    if not rule_files:
        print("未找到任何书源配置文件")
        return results
    
    valid_count = 0
    
    for rule_file in sorted(rule_files):
        is_valid = validate_single_source(rule_file)
        results[rule_file.name] = is_valid
        if is_valid:
            valid_count += 1
    
    print(f"\n批量验证完成")
    print("=" * 50)
    print(f"总文件数: {len(rule_files)}")
    print(f"验证通过: {valid_count}")
    print(f"存在问题: {len(rule_files) - valid_count}")
    
    if valid_count < len(rule_files):
        print(f"\n存在问题的文件:")
        for filename, is_valid in results.items():
            if not is_valid:
                print(f"  - {filename}")
    
    return results


def main():
    """主函数"""
    print("书源配置验证工具")
    print("================")
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("使用方法:")
        print("  python validate_source_config.py                    # 验证所有书源")
        print("  python validate_source_config.py <source_id>        # 验证指定书源")
        print("  python validate_source_config.py <rule_file>        # 验证指定文件")
        print("")
        print("示例:")
        print("  python validate_source_config.py 4")
        print("  python validate_source_config.py rules/rule-04.json")
        return
    
    rules_dir = Path("rules")
    if not rules_dir.exists():
        print("❌ rules目录不存在")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        # 如果是数字，验证指定书源ID
        if arg.isdigit():
            source_id = int(arg)
            rule_file = rules_dir / f"rule-{source_id:02d}.json"
            if not rule_file.exists():
                rule_file = rules_dir / f"rule-{source_id}.json"
            
            if rule_file.exists():
                validate_single_source(rule_file)
            else:
                print(f"❌ 找不到书源{source_id}的配置文件")
        
        # 如果是文件路径，验证指定文件
        elif arg.endswith('.json'):
            rule_file = Path(arg)
            if rule_file.exists():
                validate_single_source(rule_file)
            else:
                print(f"❌ 文件不存在: {arg}")
        
        else:
            print(f"❌ 无效的参数: {arg}")
    
    else:
        # 验证所有书源
        validate_all_sources(rules_dir)


if __name__ == "__main__":
    main()