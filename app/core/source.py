import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings


class Source:
    """书源类，对应Java项目中的Source类"""

    def __init__(
        self, source_id: int, rule_data: Optional[Dict[str, Any]] = None
    ):
        """初始化书源

        Args:
            source_id: 书源ID
            rule_data: 可选的规则数据字典，如果提供则直接使用，
                      否则根据source_id加载文件
        """
        self.id = source_id  # 添加id属性
        self.source_id = source_id
        if rule_data is not None:
            self.rule = rule_data
        else:
            self.rule = self._load_rule(source_id)
        # 从rule中获取书源名称
        self.name = self.rule.get("name", f"书源{source_id}")
        self._apply_default_rule()

    def _load_rule(self, source_id: int) -> Dict[str, Any]:
        """加载书源规则

        Args:
            source_id: 书源ID

        Returns:
            书源规则
        """
        # 尝试不同的文件名格式：先尝试零填充格式，再尝试普通格式
        rules_path = Path(settings.RULES_PATH)
        
        # 尝试零填充格式 (rule-05.json)
        rule_path = rules_path / f"rule-{source_id:02d}.json"
        if rule_path.exists():
            with open(rule_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # 尝试普通格式 (rule-5.json)
        rule_path = rules_path / f"rule-{source_id}.json"
        if rule_path.exists():
            with open(rule_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        raise FileNotFoundError(f"书源规则文件不存在: {rules_path}/rule-{source_id:02d}.json 或 {rules_path}/rule-{source_id}.json")

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

        # 设置timeout默认值 (调整为更合理的值)
        if "search" in self.rule and not self.rule["search"].get("timeout"):
            self.rule["search"]["timeout"] = 8

        if "book" in self.rule and not self.rule["book"].get("timeout"):
            self.rule["book"]["timeout"] = 8

        if "toc" in self.rule and not self.rule["toc"].get("timeout"):
            self.rule["toc"]["timeout"] = 10

        if "chapter" in self.rule and not self.rule["chapter"].get("timeout"):
            self.rule["chapter"]["timeout"] = 8

    @classmethod
    def from_rule_file(cls, rule_file: Path) -> "Source":
        """从规则文件创建书源实例

        Args:
            rule_file: 规则文件路径

        Returns:
            书源实例
        """
        with open(rule_file, "r", encoding="utf-8") as f:
            rule_data = json.load(f)

        # 从文件名提取书源ID
        source_id = int(rule_file.stem.split("-")[1])
        return cls(source_id, rule_data)
