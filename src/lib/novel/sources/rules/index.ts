import * as fs from 'fs';
import * as path from 'path';
import { RuleConfig } from '../../types/rule';

let cachedRules: RuleConfig[] = [];

// 尝试加载规则文件
export function loadRules(): RuleConfig[] {
  if (cachedRules.length > 0) {
    return cachedRules;
  }

  try {
    // 加载规则文件列表
    const rulesDir = path.join(process.cwd(), 'src', 'lib', 'novel', 'sources', 'rules');
    console.log('规则目录路径:', rulesDir);
    
    // 读取规则文件
    const ruleFiles = fs.readdirSync(rulesDir)
      .filter(file => file.endsWith('.json'));
    
    console.log(`找到 ${ruleFiles.length} 个规则文件`);
    
    // 加载所有规则
    let rules: RuleConfig[] = [];
    for (const file of ruleFiles) {
      try {
        const filePath = path.join(rulesDir, file);
        const content = fs.readFileSync(filePath, 'utf8');
        const fileRules = JSON.parse(content) as RuleConfig[];
        rules = rules.concat(fileRules);
      } catch (error) {
        console.error(`加载规则文件 ${file} 失败:`, error);
      }
    }
    
    console.log(`共加载了 ${rules.length} 条规则`);
    
    // 修复占位符问题
    rules = rules.map(fixRulePlaceholders);
    
    // 缓存规则
    cachedRules = rules;
    return rules;
  } catch (error) {
    console.error('加载规则文件失败:', error);
    return [];
  }
}

// 获取所有规则
export function getAllRules(): RuleConfig[] {
  if (cachedRules.length === 0) {
    return loadRules();
  }
  return cachedRules;
}

// 修复规则中的占位符问题
function fixRulePlaceholders(rule: RuleConfig): RuleConfig {
  const fixedRule = { ...rule };
  
  // 修复搜索URL中的占位符
  if (fixedRule.searchRule?.url) {
    // 将%s替换为{keyword}
    fixedRule.searchRule.url = fixedRule.searchRule.url.replace(/%s/g, '{keyword}');
  } else if (fixedRule.search?.url) {
    // 兼容旧格式
    fixedRule.search.url = fixedRule.search.url.replace(/%s/g, '{keyword}');
  }
  
  // 其他可能需要修复的地方
  // ...
  
  return fixedRule;
}

// 默认导出
export default {
  loadRules,
  getAllRules
}; 