import { initSources } from './sources/init';
import { NovelInfo } from './types/source';

// 获取源管理器实例
const manager = initSources();

export async function searchNovel(keyword: string): Promise<NovelInfo[]> {
  console.log(`开始搜索: "${keyword}"`);
  
  try {
    // 分词处理，提取搜索关键词
    const keywords = splitKeywords(keyword);
    console.log(`关键词分词结果: ${keywords.join(', ')}`);
    
    // 使用源管理器搜索所有源
    const searchResults = await manager.searchAll(keyword);
    console.log(`搜索完成，共有 ${searchResults.length} 个源返回结果`);
    
    // 合并所有源的结果
    const allNovels: NovelInfo[] = [];
    let successfulSources = 0;
    let totalNovelCount = 0;
    
    for (const result of searchResults) {
      if (result.novels && result.novels.length > 0) {
        // 将每个源的结果添加到总结果中
        allNovels.push(...result.novels.map(novel => ({
          ...novel,
          source: result.source  // 添加来源信息
        })));
        successfulSources++;
        totalNovelCount += result.novels.length;
      } else if (result.error) {
        console.warn(`源 ${result.source} 搜索出错: ${result.error.length > 100 ? result.error.substring(0, 100) + '...' : result.error}`);
      }
    }
    
    console.log(`共有 ${successfulSources}/${searchResults.length} 个源成功返回结果，总共找到 ${totalNovelCount} 本小说`);
    
    // 对结果进行评分排序和去重
    const scoredNovels = scoreAndRankNovels(allNovels, keywords);
    console.log(`评分排序后剩余 ${scoredNovels.length} 本小说`);
    
    return scoredNovels;
  } catch (error) {
    console.error('搜索过程中出错:', error);
    return [];
  }
}

// 分词处理函数，将搜索关键词分解成多个关键词
function splitKeywords(keyword: string): string[] {
  // 去除特殊字符
  const cleanKeyword = keyword.replace(/[^\w\s\u4e00-\u9fa5]/g, ' ').trim();
  
  // 分词逻辑：按空格拆分，并过滤掉太短的词
  const keywords = cleanKeyword
    .split(/\s+/)
    .filter(k => k.length >= 2 || /[\u4e00-\u9fa5]/.test(k)); // 保留中文单字和长度>=2的词
  
  // 如果分词后没有关键词，返回原始关键词
  if (keywords.length === 0) {
    return [cleanKeyword];
  }
  
  return keywords;
}

// 对小说结果进行评分、排序和去重
function scoreAndRankNovels(novels: NovelInfo[], keywords: string[]): NovelInfo[] {
  // 使用Map根据标题和作者组合去重
  const uniqueNovels = new Map<string, {novel: NovelInfo, score: number}>();
  
  for (const novel of novels) {
    if (!novel.title) continue;
    
    const key = `${novel.title}|${novel.author || ''}`.toLowerCase();
    const score = calculateScore(novel, keywords);
    
    // 只添加不存在的小说或替换评分更高的小说
    if (!uniqueNovels.has(key) || uniqueNovels.get(key)!.score < score) {
      uniqueNovels.set(key, {novel, score});
    }
  }
  
  // 将Map转换回数组并按评分排序
  const result = Array.from(uniqueNovels.values())
    .sort((a, b) => b.score - a.score) // 按评分降序
    .map(item => item.novel);
  
  return result;
}

// 计算小说与搜索关键词的匹配评分
function calculateScore(novel: NovelInfo, keywords: string[]): number {
  let score = 0;
  const title = novel.title?.toLowerCase() || '';
  const author = novel.author?.toLowerCase() || '';
  const description = novel.description?.toLowerCase() || '';
  
  // 计算每个关键词的匹配情况
  for (const keyword of keywords) {
    const keywordLower = keyword.toLowerCase();
    
    // 标题完全匹配（基准分100）
    if (title === keywordLower) {
      score += 100;
      continue;
    }
    
    // 标题包含关键词（基准分50）
    if (title.includes(keywordLower)) {
      // 计算匹配度：关键词长度占标题长度的比例
      const matchRatio = keywordLower.length / title.length;
      score += 50 * matchRatio;
    }
    
    // 作者匹配（基准分30）
    if (author === keywordLower) {
      score += 30;
    } else if (author.includes(keywordLower)) {
      score += 20;
    }
    
    // 描述匹配（基准分10）
    if (description.includes(keywordLower)) {
      score += 10;
    }
  }
  
  // 添加一些随机因素，避免评分完全相同时结果总是相同顺序
  score += Math.random() * 0.1;
  
  return score;
} 