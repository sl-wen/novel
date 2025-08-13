#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书源配置文件优化工具
参考 freeok/so-novel 项目的 main-rules.json 优化现有书源配置
"""

import json
import os
import re
from typing import Dict, List, Any, Union
from pathlib import Path

class BookSourceOptimizer:
    """书源配置优化器"""
    
    def __init__(self):
        self.common_selectors = {
            "book_info": {
                "name": [
                    "meta[property=\"og:novel:book_name\"]",
                    "meta[property=\"og:title\"]",
                    "h1.book-title",
                    "#info h1",
                    ".book-name",
                    "title"
                ],
                "author": [
                    "meta[property=\"og:novel:author\"]",
                    "meta[name=\"author\"]",
                    ".book-author",
                    "#info .author",
                    ".author"
                ],
                "intro": [
                    "meta[name=\"description\"]",
                    "meta[property=\"og:description\"]",
                    "#intro",
                    ".book-intro",
                    ".summary"
                ],
                "category": [
                    "meta[property=\"og:novel:category\"]",
                    ".book-category",
                    "#info .type",
                    ".category"
                ],
                "cover": [
                    "meta[property=\"og:image\"]",
                    "#fmimg img",
                    ".book-cover img",
                    "#info img"
                ]
            },
            "chapter_content": [
                "#content",
                ".content",
                ".read-content",
                "#chapter-content",
                ".chapter-content",
                ".book-content",
                "#book-content",
                ".novel-content",
                "#novel-content",
                ".text",
                "#text",
                "article",
                ".article",
                ".post-content",
                ".entry-content"
            ]
        }
        
        self.enhanced_ad_patterns = [
            "\\(本章完\\)",
            "^首页.*书库.*排行.*$",
            "^最新章节目录.*$",
            "^作者：.*?更新时间：.*$",
            "^如遇到内容无法显示或者显示不全.*$",
            "^.*请更换谷歌浏览器.*$",
            "(推广|广告|下载APP|\\bVIP\\b).{0,10}?(立即|扫码|点击)",
            ".*?(记住|收藏).*?(网址|地址).*?",
            ".*?手机.*?(版|端).*?",
            ".*?更新.*?最快.*?",
            ".*?无弹窗.*?",
            ".*?免费.*?阅读.*?",
            "喜欢.*?请.*?收藏.*?",
            "天才一秒记住.*?",
            "一秒记住.*?",
            "手机用户请.*?",
            "支持.*?分享.*?",
            "搜.*?免费看.*?"
        ]
    
    def load_rule(self, file_path: str) -> Dict[str, Any]:
        """加载书源规则文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载规则文件失败 {file_path}: {e}")
            return {}
    
    def save_rule(self, rule: Dict[str, Any], file_path: str) -> bool:
        """保存书源规则文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(rule, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存规则文件失败 {file_path}: {e}")
            return False
    
    def enhance_selectors(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """增强选择器 - 添加备用选择器"""
        # 处理书籍信息选择器
        if "book" in rule:
            book_section = rule["book"]
            for field, selectors in self.common_selectors["book_info"].items():
                if field in book_section:
                    current = book_section[field]
                    if isinstance(current, str) and current:
                        # 将单个选择器转换为数组，并添加备用选择器
                        enhanced = [current]
                        for fallback in selectors:
                            if fallback != current and fallback not in enhanced:
                                enhanced.append(fallback)
                        book_section[field] = enhanced
        
        # 处理章节内容选择器
        if "chapter" in rule and "content" in rule["chapter"]:
            current_content = rule["chapter"]["content"]
            if isinstance(current_content, str):
                # 合并当前选择器和通用选择器
                enhanced_content = [current_content]
                for selector in self.common_selectors["chapter_content"]:
                    if selector != current_content and selector not in enhanced_content:
                        enhanced_content.append(selector)
                rule["chapter"]["content"] = enhanced_content
        
        return rule
    
    def add_performance_config(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """添加性能配置"""
        # 添加版本和基础配置
        rule["version"] = "2.0"
        if "timeout" not in rule:
            rule["timeout"] = 15000
        if "retry_count" not in rule:
            rule["retry_count"] = 3
        
        # 添加用户代理和请求头
        if "user_agent" not in rule:
            rule["user_agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        if "headers" not in rule:
            rule["headers"] = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        
        # 添加缓存配置
        if "cache" not in rule:
            rule["cache"] = {
                "enabled": True,
                "ttl": 3600,
                "preload_next": True
            }
        
        # 添加并发限制
        if "concurrent_limit" not in rule:
            rule["concurrent_limit"] = 3
        
        return rule
    
    def enhance_ad_filtering(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """增强广告过滤"""
        if "chapter" in rule:
            chapter_section = rule["chapter"]
            
            # 合并现有广告模式和增强模式
            existing_patterns = chapter_section.get("ad_patterns", [])
            enhanced_patterns = existing_patterns.copy()
            
            for pattern in self.enhanced_ad_patterns:
                if pattern not in enhanced_patterns:
                    enhanced_patterns.append(pattern)
            
            chapter_section["ad_patterns"] = enhanced_patterns
            
            # 添加内容过滤配置
            if "filter" not in chapter_section:
                chapter_section["filter"] = {
                    "remove_tags": ["script", "style", "iframe", "form", "input", "button"],
                    "remove_attrs": ["onclick", "onload", "style"],
                    "clean_html": True
                }
            
            # 添加格式化配置
            if "format" not in chapter_section:
                chapter_section["format"] = {
                    "paragraph_spacing": True,
                    "remove_empty_lines": True,
                    "trim_whitespace": True,
                    "fix_encoding": True
                }
        
        return rule
    
    def add_css_injection(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """添加CSS注入功能"""
        if "css_inject" not in rule:
            rule["css_inject"] = {
                "enabled": True,
                "styles": "body { font-family: 'Microsoft YaHei', '微软雅黑', serif; line-height: 1.8; text-align: justify; padding: 0 5%; } p { margin: 0.8em 0; text-indent: 2em; } img { max-width: 100%; height: auto; }"
            }
        return rule
    
    def add_error_handling(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """添加错误处理配置"""
        if "error_handling" not in rule:
            rule["error_handling"] = {
                "ignore_ssl_errors": True,
                "follow_redirects": True,
                "max_redirects": 5,
                "handle_404": "skip",
                "handle_timeout": "retry"
            }
        return rule
    
    def optimize_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """优化单个规则"""
        if not rule:
            return rule
        
        print(f"正在优化书源: {rule.get('name', 'Unknown')}")
        
        # 应用各种优化
        rule = self.add_performance_config(rule)
        rule = self.enhance_selectors(rule)
        rule = self.enhance_ad_filtering(rule)
        rule = self.add_css_injection(rule)
        rule = self.add_error_handling(rule)
        
        return rule
    
    def optimize_directory(self, rules_dir: str, output_dir: str = None) -> List[str]:
        """优化整个目录的规则文件"""
        if output_dir is None:
            output_dir = rules_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        optimized_files = []
        rules_path = Path(rules_dir)
        
        for rule_file in rules_path.glob("rule-*.json"):
            print(f"\n处理文件: {rule_file.name}")
            
            # 加载原始规则
            original_rule = self.load_rule(str(rule_file))
            if not original_rule:
                continue
            
            # 优化规则
            optimized_rule = self.optimize_rule(original_rule)
            
            # 生成输出文件名
            output_file = Path(output_dir) / f"optimized-{rule_file.name}"
            
            # 保存优化后的规则
            if self.save_rule(optimized_rule, str(output_file)):
                optimized_files.append(str(output_file))
                print(f"✓ 优化完成: {output_file.name}")
            else:
                print(f"✗ 优化失败: {rule_file.name}")
        
        return optimized_files
    
    def generate_report(self, original_dir: str, optimized_files: List[str]) -> str:
        """生成优化报告"""
        report = []
        report.append("# 书源配置优化报告\n")
        report.append(f"优化时间: {os.popen('date').read().strip()}\n")
        report.append(f"原始文件目录: {original_dir}")
        report.append(f"优化文件数量: {len(optimized_files)}\n")
        
        report.append("## 优化功能\n")
        report.append("1. **增强选择器** - 为关键元素添加多个备用选择器")
        report.append("2. **性能优化** - 添加缓存、并发控制、超时设置")
        report.append("3. **广告过滤** - 增强广告模式匹配和内容清理")
        report.append("4. **CSS注入** - 改善阅读体验的样式")
        report.append("5. **错误处理** - 增强错误恢复机制")
        report.append("6. **格式化** - 自动格式化和编码处理\n")
        
        report.append("## 优化文件列表\n")
        for file_path in optimized_files:
            file_name = os.path.basename(file_path)
            report.append(f"- {file_name}")
        
        report.append("\n## 使用说明\n")
        report.append("1. 备份原始配置文件")
        report.append("2. 使用优化后的配置文件替换原文件")
        report.append("3. 测试书源功能是否正常")
        report.append("4. 根据实际情况调整配置参数")
        
        return "\n".join(report)

def main():
    """主函数"""
    optimizer = BookSourceOptimizer()
    
    # 设置路径
    rules_dir = "rules/"
    
    print("开始优化书源配置文件...")
    print(f"规则目录: {rules_dir}")
    
    # 优化所有规则文件
    optimized_files = optimizer.optimize_directory(rules_dir)
    
    # 生成报告
    report = optimizer.generate_report(rules_dir, optimized_files)
    
    # 保存报告
    report_file = "/optimization_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n优化完成！")
    print(f"优化文件数量: {len(optimized_files)}")
    print(f"报告文件: {report_file}")

if __name__ == "__main__":
    main()
