import { RuleConfig } from '../types/rule';
import fs from 'fs';
import path from 'path';

// 尝试多个可能的规则目录路径
const POSSIBLE_RULE_DIRS = [
    path.join(process.cwd(), 'src', 'lib', 'novel', 'sources', 'rules'), // 开发环境路径
    path.join(process.cwd(), 'public', 'rules'), // 生产环境通过copy-rules复制的路径
    path.join(process.cwd(), '.next', 'server', 'app', 'api', 'novel', 'search') // Next.js生产环境可能的路径
];

// 加载规则文件
export function loadRules(): RuleConfig[] {
    console.log('开始加载规则文件...');
    
    // 尝试所有可能的路径
    for (const rulesDir of POSSIBLE_RULE_DIRS) {
        console.log(`尝试从目录加载规则: ${rulesDir}`);
        
        try {
            // 确认目录是否存在
            if (!fs.existsSync(rulesDir)) {
                console.log(`规则目录不存在: ${rulesDir}`);
                continue; // 尝试下一个目录
            }
            
            console.log(`找到规则目录: ${rulesDir}`);
            const rules: RuleConfig[] = [];
            const files = fs.readdirSync(rulesDir);
            console.log(`发现 ${files.length} 个文件`);
            
            for (const file of files) {
                if (file.endsWith('.json') && !file.includes('template') && !file.includes('unavailable')) {
                    const filePath = path.join(rulesDir, file);
                    console.log(`加载规则文件: ${file}`);
                    
                    try {
                        const content = fs.readFileSync(filePath, 'utf-8');
                        const rule = JSON.parse(content);
                        rules.push(rule);
                        console.log(`成功加载规则: ${rule.name || '未命名'}`);
                    } catch (error) {
                        console.error(`解析规则文件 ${file} 出错:`, error);
                    }
                }
            }
            
            if (rules.length > 0) {
                console.log(`成功从 ${rulesDir} 加载了 ${rules.length} 个规则`);
                return rules;
            }
        } catch (error) {
            console.error(`尝试从 ${rulesDir} 加载规则时出错:`, error);
        }
    }
    
    // 所有路径都尝试失败
    console.error('所有可能的规则目录都尝试失败');
    
    // 尝试列出当前工作目录内容帮助调试
    console.log('当前工作目录:', process.cwd());
    try {
        const contents = fs.readdirSync(process.cwd());
        console.log('当前工作目录内容:', contents);
        
        if (fs.existsSync(path.join(process.cwd(), 'public'))) {
            console.log('public目录内容:', fs.readdirSync(path.join(process.cwd(), 'public')));
        }
    } catch (err) {
        console.error('无法列出当前工作目录内容:', err);
    }
    
    return [];
}

export function getRuleById(id: number): RuleConfig | undefined {
    const rules = loadRules();
    return rules.find(rule => rule.id === id);
}

export function getRuleByName(name: string): RuleConfig | undefined {
    const rules = loadRules();
    return rules.find(rule => rule.name === name);
}

export function getAllRules(): RuleConfig[] {
    return loadRules();
} 