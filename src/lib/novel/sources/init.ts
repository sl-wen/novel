import { SourceManager } from './manager';
import { getAllRules } from './rules';

// 初始化源管理器
console.log('初始化SourceManager...');
const sourceManager = SourceManager.getInstance();
console.log('SourceManager初始化完成');

export {
    sourceManager,
    SourceManager
};

export * from '../types/rule';
export * from './base';

export function initSources() {
  console.log('调用initSources函数...');
  const manager = SourceManager.getInstance();
  
  // 确保manager有源
  const sources = manager.getAllSources();
  console.log(`initSources: 当前有${sources.length}个源`);
  
  if (sources.length === 0) {
    console.log('没有找到任何源，尝试手动加载规则文件...');
    const rules = getAllRules();
    console.log(`找到${rules.length}个规则文件`);
    
    // 手动创建源
    rules.forEach(rule => {
      if (rule.id && rule.id > 0 && rule.name && rule.baseUrl) {
        try {
          console.log(`尝试从规则创建源: ${rule.name}`);
          const source = new (require('./base').BaseNovelSource)(rule);
          manager.registerSource(source);
          console.log(`成功注册源: ${rule.name}`);
        } catch (error) {
          console.error(`初始化书源失败: ${rule.name}`, error);
        }
      }
    });
    
    console.log(`手动加载后，现在有${manager.getAllSources().length}个源`);
  }
  
  return manager;
}

export default initSources; 