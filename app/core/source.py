import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import settings


class Source:
    """书源类，对应Java项目中的Source类"""

    def __init__(self, source_id: int, rule_data: Optional[Dict[str, Any]] = None):
        """初始化书源

        Args:
            source_id: 书源ID
            rule_data: 可选的规则数据字典，如果提供则直接使用，否则根据source_id加载文件
        """
        self.id = source_id # 添加id属性
        self.source_id = source_id
        if rule_data is not None:
            self.rule = rule_data
        else:
            self.rule = self._load_rule(source_id)
        self._apply_default_rule()

    def _load_rule(self, source_id: int) -> Dict[str, Any]:
        """加载书源规则

        Args:
            source_id: 书源ID

        Returns:
            书源规则
        """
        # 注意：这个方法现在主要用于没有直接提供rule_data的情况
        # 如果规则文件命名方式是 rule-XX.json，这里可能需要调整加载逻辑
        rule_path = Path(settings.RULES_PATH) / f"rule-{source_id}.json"

        if not rule_path.exists():
            raise FileNotFoundError(f"书源规则文件不存在: {rule_path}")

        with open(rule_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _apply_default_rule(self):
        """应用默认规则，设置缺失的配置项"""
        # 设置baseUri默认值
        if "search" in self.rule and not self.rule["search"].get("baseUri"):
            self.rule["search"]["baseUri"] = self.rule.get("url", "")
            
        if "book" in self.rule and not self.rule["book"].get("baseUri"):
            self.rule["book"]["baseUri"] = self.rule.get("url", "")
            
        if "toc" in self.rule and not self.rule["toc"].get("baseUri"):
            self.rule["toc"]["baseUri"] = self.rule.get("url", "")
            
        if "chapter" in self.rule and not self.rule["chapter"].get("baseUri"):
            self.rule["chapter"]["baseUri"] = self.rule.get("url", "")
        
        # 设置timeout默认值
        if "search" in self.rule and not self.rule["search"].get("timeout"):
            self.rule["search"]["timeout"] = 10
            
        if "book" in self.rule and not self.rule["book"].get("timeout"):
            self.rule["book"]["timeout"] = 10
            
        if "toc" in self.rule and not self.rule["toc"].get("timeout"):
            self.rule["toc"]["timeout"] = 15
            
        if "chapter" in self.rule and not self.rule["chapter"].get("timeout"):
            self.rule["chapter"]["timeout"] = 10