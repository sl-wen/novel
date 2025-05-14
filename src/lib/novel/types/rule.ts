export interface RuleConfig {
  id?: number;                  // 源的唯一标识（可选）
  name: string;                 // 源的名称
  baseUrl: string;             // 源的基础 URL
  encoding?: string;           // 源的编码方式，默认 utf-8
  searchRule: {
    url: string;              // 搜索 URL 模板
    list: string;             // 搜索结果列表选择器
    item: {                   // 搜索结果项选择器
      title: string;          // 标题选择器
      author: string;         // 作者选择器
      link: string;          // 链接选择器
      latest?: string;       // 最新章节选择器（可选）
    };
  };
  bookRule: {
    title: string;           // 书籍标题选择器
    author: string;          // 作者选择器
    intro?: string;          // 简介选择器
    cover?: string;          // 封面图片选择器
    chapters: {
      list: string;         // 章节列表选择器
      item: {
        title: string;      // 章节标题选择器
        link: string;       // 章节链接选择器
      };
    };
  };
  chapterRule: {
    title: string;          // 章节标题选择器
    content: string;        // 章节内容选择器
    cleanupRules?: {        // 内容清理规则（可选）
      remove?: string[];    // 需要移除的选择器
      replace?: Array<{     // 需要替换的内容
        pattern: string;
        replacement: string;
      }>;
    };
  };
}

export interface NovelSource {
  name: string;
  config: RuleConfig;
  search(keyword: string): Promise<SearchResult[]>;
  getBookInfo(url: string): Promise<BookInfo>;
  getChapterContent(url: string): Promise<ChapterContent>;
}

export interface SearchResult {
  title: string;
  author: string;
  url: string;
  latest?: string;
}

export interface BookInfo {
  title: string;
  author: string;
  intro?: string;
  cover?: string;
  chapters: Chapter[];
}

export interface Chapter {
  title: string;
  url: string;
}

export interface ChapterContent {
  title: string;
  content: string;
} 