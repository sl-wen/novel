import { RuleConfig } from './rule';

export interface NovelInfo {
  title: string;
  author: string;
  sourceUrl: string;
  description?: string;
  source?: string;     // 来源名称
  score?: number;      // 搜索匹配评分
}

export interface ChapterInfo {
  title: string;
  url: string;
  content?: string;
}

export interface SearchResult {
  source: string;
  novels: NovelInfo[];
  error?: string;
}

export interface NovelDetail extends NovelInfo {
  chapters: ChapterInfo[];
}

export interface INovelSource {
  name: string;
  baseUrl: string;
  
  // 核心方法
  search(keyword: string): Promise<SearchResult>;
  getDetail(url: string): Promise<NovelDetail>;
  getChapter(url: string): Promise<ChapterInfo>;
  
  // 工具方法
  isSupported(url: string): boolean;
  getSourceId(): string;
}

export type SourceOptions = {
  timeout?: number;
  retries?: number;
  userAgent?: string;
  encoding?: string;
} 