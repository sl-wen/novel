#!/usr/bin/env python3
"""
目录解析器修复脚本
解决章节标题和URL提取问题
"""

import json
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TocParserFixer:
    """目录解析器修复器"""
    
    def __init__(self):
        self.fixes = {
            # 香书小说 - 修复目录解析
            1: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 书海阁小说网 - 修复目录解析
            2: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 梦书中文 - 修复目录解析
            3: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 鸟书网 - 修复目录解析
            4: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 新天禧小说 - 修复目录解析
            5: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 全本小说网 - 修复目录解析
            6: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 69书吧1 - 修复目录解析
            7: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 大熊猫文学 - 修复目录解析
            8: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 笔趣阁22 - 修复目录解析
            9: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 笔尖中文 - 修复目录解析
            10: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 零点小说 - 修复目录解析
            11: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 得奇小说网 - 修复目录解析
            12: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 新笔趣阁6 - 修复目录解析
            13: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 略更网 - 修复目录解析
            14: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 96读书 - 修复目录解析
            15: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 速读谷 - 修复目录解析
            16: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 八一中文网 - 修复目录解析
            17: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 悠久小说网 - 修复目录解析
            18: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 阅读库 - 修复目录解析
            19: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            },
            # 顶点小说 - 修复目录解析
            20: {
                'toc': {
                    'list': 'dd > a',
                    'title': 'text',
                    'url': 'href'
                }
            }
        }
    
    def apply_fixes(self):
        """应用修复到书源规则文件"""
        logger.info("开始应用目录解析修复...")
        
        for source_id, fix in self.fixes.items():
            try:
                self.apply_single_fix(source_id, fix)
            except Exception as e:
                logger.error(f"修复书源 {source_id} 失败: {str(e)}")
        
        logger.info("目录解析修复完成")
    
    def apply_single_fix(self, source_id: int, fix: dict):
        """应用单个书源的修复"""
        # 读取原始规则文件
        rules_path = Path("rules")
        rule_file = rules_path / f"rule-{source_id:02d}.json"
        
        if not rule_file.exists():
            logger.warning(f"书源规则文件不存在: {rule_file}")
            return
        
        with open(rule_file, 'r', encoding='utf-8') as f:
            rule_data = json.load(f)
        
        # 应用修复
        if 'toc' in fix:
            if 'toc' not in rule_data:
                rule_data['toc'] = {}
            
            rule_data['toc'].update(fix['toc'])
            logger.info(f"修复书源 {source_id} 的目录配置")
        
        # 写回文件
        with open(rule_file, 'w', encoding='utf-8') as f:
            json.dump(rule_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"书源 {source_id} 修复完成")

def main():
    """主函数"""
    fixer = TocParserFixer()
    
    # 应用修复
    fixer.apply_fixes()
    
    logger.info("所有书源规则修复完成！")

if __name__ == "__main__":
    main()