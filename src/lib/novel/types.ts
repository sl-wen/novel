export interface NovelInfo {
  title: string;
  author: string;
  description: string;
  coverUrl?: string;
  sourceUrl: string;
  source: string;
  chapters?: Chapter[];
  latest?: string;        // 最新章节
  chapterCount?: number;  // 章节数
  lastUpdate?: string;    // 最后更新时间
}

export interface Chapter {
  title: string;
  url: string;
  content?: string;
}

export interface NovelSource {
  name: string;
  search(keyword: string): Promise<NovelInfo[]>;
  getDetail(url: string): Promise<NovelInfo>;
  getChapter(url: string): Promise<Chapter>;
}

export type NovelFormat = 'epub' | 'txt' | 'html' | 'pdf'; 