import { initSources } from '@/lib/novel/sources/init';
import { downloadNovel } from '@/lib/novel/download';
import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';

// 添加导出配置以标记这是一个动态路由
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const url = searchParams.get('url');
    const format = searchParams.get('format') || 'txt';

    if (!url) {
      return NextResponse.json({ error: '下载链接不能为空' }, { status: 400 });
    }

    console.log('开始下载:', url, '格式:', format);
    
    try {
      // 确保下载目录存在
      const downloadDir = path.join(process.cwd(), 'downloads');
      if (!fs.existsSync(downloadDir)) {
        fs.mkdirSync(downloadDir, { recursive: true });
      }
      
      // 使用下载模块处理下载
      const result = await downloadNovel(url, format as any);
      console.log('下载完成:', result);
      
      // 返回文件URL或内容
      if (result && result.url) {
        // 检查文件是否存在
        if (fs.existsSync(result.url)) {
          const fileName = path.basename(result.url);
          const fileContent = fs.readFileSync(result.url);
          
          // 根据格式设置正确的MIME类型
          let contentType = 'text/plain';
          if (format === 'epub') {
            contentType = 'application/epub+zip';
          } else if (format === 'html') {
            contentType = 'text/html';
          } else if (format === 'pdf') {
            contentType = 'application/pdf';
          }
          
          // 返回文件内容供下载
          return new Response(fileContent, {
            headers: {
              'Content-Type': contentType,
              'Content-Disposition': `attachment; filename="${encodeURIComponent(fileName)}"`,
            },
          });
        } else {
          console.error('文件不存在:', result.url);
          return NextResponse.json({ error: '文件生成失败' }, { status: 500 });
        }
      } else {
        return NextResponse.json({ error: '下载处理失败' }, { status: 500 });
      }
    } catch (error) {
      console.error('下载处理错误:', error);
      return NextResponse.json({ error: '下载处理错误: ' + (error instanceof Error ? error.message : String(error)) }, { status: 500 });
    }
  } catch (error) {
    console.error('下载失败:', error);
    return NextResponse.json({ error: '下载失败: ' + (error instanceof Error ? error.message : String(error)) }, { status: 500 });
  }
} 