import { NovelFormat } from './types';
import { NovelDetail, ChapterInfo } from './types/source';
import * as fs from 'fs';
import * as path from 'path';
import EpubGenerator from 'epub-gen';
import { initSources } from './sources/init';

// 获取SourceManager实例
const manager = initSources();

// 确保downloads目录存在
try {
  const downloadDir = path.join(process.cwd(), 'downloads');
  if (!fs.existsSync(downloadDir)) {
    console.log('创建下载目录:', downloadDir);
    fs.mkdirSync(downloadDir, { recursive: true });
  }
} catch (error) {
  console.error('创建下载目录失败:', error);
}

export async function downloadNovel(url: string, format: NovelFormat = 'epub'): Promise<{ url: string }> {
  // 获取适合该URL的源
  const source = manager.getSourceForUrl(url);
  if (!source) {
    throw new Error('不支持的小说源');
  }

  // 获取小说详情
  const novel = await manager.getNovelDetail(url);
  if (!novel) {
    throw new Error('获取小说信息失败');
  }
  
  if (!novel.chapters?.length) {
    throw new Error('未找到章节');
  }

  // 创建下载目录
  const downloadDir = path.join(process.cwd(), 'downloads');
  if (!fs.existsSync(downloadDir)) {
    fs.mkdirSync(downloadDir, { recursive: true });
  }

  // 下载所有章节
  console.log(`开始下载 ${novel.title} 的 ${novel.chapters.length} 个章节`);
  
  // 使用限制并发的下载方式，避免同时请求过多导致被封
  const MAX_CONCURRENT = 5; // 最大并发下载数
  const RETRY_ATTEMPTS = 3; // 失败重试次数
  
  // 分批下载章节
  const chapters = [];
  let failedChapters = 0;
  
  for (let i = 0; i < novel.chapters.length; i += MAX_CONCURRENT) {
    const batch = novel.chapters.slice(i, i + MAX_CONCURRENT);
    const chapterPromises = batch.map(async (chapter, batchIndex) => {
      const chapterIndex = i + batchIndex;
      const retryDownloadChapter = async (retries: number): Promise<{title: string, data: string}> => {
        try {
          console.log(`下载章节 ${chapterIndex+1}/${novel.chapters.length}: ${chapter.title}`);
          const content = await manager.getChapterContent(chapter.url);
          
          // 随机延迟，避免请求过于频繁
          await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000));
          
          return {
            title: chapter.title,
            data: content?.content || ''
          };
        } catch (error: any) {
          if (retries > 0) {
            const delayTime = 2000 + Math.random() * 3000;
            console.warn(`下载章节 ${chapter.title} 失败: ${error.message}, 将在 ${(delayTime/1000).toFixed(1)}秒后重试(${retries}次重试机会)`);
            await new Promise(resolve => setTimeout(resolve, delayTime));
            return retryDownloadChapter(retries - 1);
          }
          
          console.error(`下载章节 ${chapter.title} 最终失败: ${error.message}`);
          failedChapters++;
          return {
            title: chapter.title,
            data: `[获取失败] ${chapter.title}\n该章节下载失败，可能是网络问题或内容已被移除。\n错误信息：${error.message}`
          };
        }
      };
      
      return retryDownloadChapter(RETRY_ATTEMPTS);
    });
    
    // 等待当前批次完成
    const batchResults = await Promise.all(chapterPromises);
    chapters.push(...batchResults);
    
    // 每批次下载完添加额外延迟，降低被检测风险
    if (i + MAX_CONCURRENT < novel.chapters.length) {
      const batchDelay = 1000 + Math.random() * 2000;
      console.log(`批次 ${Math.floor(i/MAX_CONCURRENT) + 1} 下载完成，等待 ${(batchDelay/1000).toFixed(1)}秒...`);
      await new Promise(resolve => setTimeout(resolve, batchDelay));
    }
  }
  
  if (failedChapters > 0) {
    console.warn(`警告: ${failedChapters} 章节下载失败`);
  }
  
  console.log(`所有章节下载完成，成功: ${novel.chapters.length - failedChapters}，失败: ${failedChapters}`);

  const filename = `${novel.title}_${novel.author}`.replace(/[\\\/\:\*\?\"\<\>\|]/g, '_') || '_';
  const outputPath = path.join(downloadDir, filename);

  switch (format) {
    case 'epub':
      console.log(`生成EPUB文件: ${outputPath}.epub`);
      await new EpubGenerator({
        title: novel.title,
        author: novel.author,
        cover: novel.description,  // 使用描述替代封面
        content: chapters
      }, `${outputPath}.epub`).promise;
      return { url: `${outputPath}.epub` };

    case 'txt':
      console.log(`生成TXT文件: ${outputPath}.txt`);
      const content = chapters
        .map(chapter => `${chapter.title}\n\n${chapter.data}\n\n`)
        .join('\n');
      fs.writeFileSync(`${outputPath}.txt`, content);
      return { url: `${outputPath}.txt` };

    case 'html':
      console.log(`生成HTML文件: ${outputPath}.html`);
      const html = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>${novel.title}</title>
          <style>
            body { max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { text-align: center; }
            .chapter { margin-bottom: 30px; }
          </style>
        </head>
        <body>
          <h1>${novel.title}</h1>
          ${chapters.map(chapter => `
            <div class="chapter">
              <h2>${chapter.title}</h2>
              ${chapter.data}
            </div>
          `).join('')}
        </body>
        </html>
      `;
      fs.writeFileSync(`${outputPath}.html`, html);
      return { url: `${outputPath}.html` };

    default:
      throw new Error('不支持的格式');
  }
} 