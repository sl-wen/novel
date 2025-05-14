import { initSources } from '@/lib/novel/sources/init';
import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// 添加导出配置以标记这是一个动态路由
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const keyword = searchParams.get('keyword');

    if (!keyword) {
      return NextResponse.json({ error: '搜索关键词不能为空' }, { status: 400 });
    }

    console.log('开始搜索:', keyword);
    
    // 检查规则目录是否存在
    const rulesDir = path.join(process.cwd(), 'src', 'lib', 'novel', 'sources', 'rules');
    console.log('规则目录路径:', rulesDir);
    
    if (!fs.existsSync(rulesDir)) {
      console.error('规则目录不存在:', rulesDir);
      console.log('当前工作目录:', process.cwd());
      try {
        // 尝试列出当前目录结构以帮助调试
        const baseDir = process.cwd();
        console.log('基础目录内容:', fs.readdirSync(baseDir));
        
        if (fs.existsSync(path.join(baseDir, 'src'))) {
          console.log('src目录内容:', fs.readdirSync(path.join(baseDir, 'src')));
          
          if (fs.existsSync(path.join(baseDir, 'src', 'lib'))) {
            console.log('src/lib目录内容:', fs.readdirSync(path.join(baseDir, 'src', 'lib')));
            
            if (fs.existsSync(path.join(baseDir, 'src', 'lib', 'novel'))) {
              console.log('src/lib/novel目录内容:', fs.readdirSync(path.join(baseDir, 'src', 'lib', 'novel')));
              
              if (fs.existsSync(path.join(baseDir, 'src', 'lib', 'novel', 'sources'))) {
                console.log('src/lib/novel/sources目录内容:', fs.readdirSync(path.join(baseDir, 'src', 'lib', 'novel', 'sources')));
              }
            }
          }
        }
      } catch (err) {
        console.error('列出目录结构失败:', err);
      }
      
      return NextResponse.json({ error: '规则目录不存在，无法进行搜索' }, { status: 500 });
    }
    
    const manager = initSources();
    
    try {
      // 使用searchAll方法进行并发搜索
      console.log('调用manager.searchAll...');
      
      // 先输出所有可用源
      const sources = manager.getAllSources();
      console.log('可用书源数量:', sources.length);
      sources.forEach(source => {
        console.log(`- 书源: ${source.name}, baseUrl: ${source.config.baseUrl}`);
      });
      
      if (sources.length === 0) {
        return NextResponse.json({ error: '未找到可用的书源，请检查规则文件' }, { status: 500 });
      }
      
      const results = await manager.searchAll(keyword);
      console.log('搜索结果:', JSON.stringify(results).slice(0, 200) + '...');
      
      return NextResponse.json(results);
    } catch (error) {
      console.error('搜索过程出错:', error);
      return NextResponse.json({ error: '搜索过程出错: ' + (error instanceof Error ? error.message : String(error)) }, { status: 500 });
    }
  } catch (error) {
    console.error('搜索失败:', error);
    return NextResponse.json({ error: '搜索失败: ' + (error instanceof Error ? error.message : String(error)) }, { status: 500 });
  }
} 