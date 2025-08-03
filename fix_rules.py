#!/usr/bin/env python3
"""
修复规则文件，添加缺失的 URL 字段
"""

import json
import os
from pathlib import Path


def fix_rule_file(rule_file_path):
    """修复单个规则文件"""
    try:
        with open(rule_file_path, "r", encoding="utf-8") as f:
            rule_data = json.load(f)

        # 检查搜索部分是否存在且缺少 url 字段
        if "search" in rule_data and "name" in rule_data["search"]:
            search_config = rule_data["search"]

            # 如果缺少 url 字段，使用 name 字段的选择器
            if "url" not in search_config or not search_config["url"]:
                name_selector = search_config.get("name", "")
                if name_selector:
                    search_config["url"] = name_selector
                    print(
                        f"修复 {rule_file_path.name}: 添加 url 字段 '{name_selector}'"
                    )

                    # 写回文件
                    with open(rule_file_path, "w", encoding="utf-8") as f:
                        json.dump(rule_data, f, ensure_ascii=False, indent=2)
                    return True

        return False
    except Exception as e:
        print(f"处理 {rule_file_path.name} 时出错: {e}")
        return False


def main():
    """主函数"""
    rules_dir = Path("rules")
    fixed_count = 0

    for rule_file in rules_dir.glob("rule-*.json"):
        if fix_rule_file(rule_file):
            fixed_count += 1

    print(f"\n修复完成！共修复了 {fixed_count} 个规则文件。")


if __name__ == "__main__":
    main()
