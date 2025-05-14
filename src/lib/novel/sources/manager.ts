import { INovelSource, SearchResult, NovelDetail, ChapterInfo } from '../types/source';
import { BaseNovelSource } from './base';
import { NovelSource, RuleConfig } from '../types/rule';
import { loadRules, getAllRules } from './rules';

export class SourceManager {
  private static instance: SourceManager;
  private sources: Map<string, BaseNovelSource> = new Map();

  private constructor() {
    // 初始化时加载所有源
    try {
      console.log('SourceManager构造函数: 开始初始化源...');
      this.initializeSources();
      console.log('SourceManager构造函数: 源初始化完成');
    } catch (error) {
      console.error('SourceManager构造函数: 初始化源时出错', error);
    }
  }

  public static getInstance(): SourceManager {
    if (!SourceManager.instance) {
      console.log('创建SourceManager实例...');
      SourceManager.instance = new SourceManager();
      console.log('SourceManager实例创建完成');
    }
    return SourceManager.instance;
  }

  private initializeSources() {
    try {
      console.log('initializeSources: 开始加载规则...');
      const rules = loadRules();
      console.log(`initializeSources: 加载了 ${rules.length} 个规则`);
      
      let registeredCount = 0;
      // 使用同步方式加载配置
      rules.forEach(config => {
        try {
          if (config.id && config.id > 0) {
            // 规则兼容性处理
            const normalizedConfig = this.normalizeRuleConfig(config);
            
            if (normalizedConfig.name && normalizedConfig.baseUrl) {
              console.log(`initializeSources: 尝试加载规则 ${normalizedConfig.name}`);
              const source = new BaseNovelSource(normalizedConfig);
              this.registerSource(source);
              console.log(`initializeSources: 成功注册规则 ${normalizedConfig.name}`);
              registeredCount++;
            } else {
              console.warn(`规则 ${config.id} 格式不正确，缺少name或baseUrl`);
            }
          }
        } catch (error) {
          const ruleName = config.name || config.id?.toString() || "未知";
          console.error(`initializeSources: 加载规则 ${ruleName} 失败`, error);
        }
      });
      
      console.log(`initializeSources: 总共注册了 ${registeredCount} / ${rules.length} 个源`);
    } catch (error) {
      console.error('initializeSources: 加载规则时出错', error);
    }
  }

  // 规则配置标准化，将不同格式的规则统一转换为标准格式
  private normalizeRuleConfig(config: any): RuleConfig {
    // 创建一个新对象，避免修改原始配置
    const normalizedConfig: any = { ...config };
    
    // 处理baseUrl字段
    if (!normalizedConfig.baseUrl && normalizedConfig.url) {
      normalizedConfig.baseUrl = normalizedConfig.url;
    }
    
    // 处理搜索规则
    if (!normalizedConfig.searchRule && normalizedConfig.search) {
      normalizedConfig.searchRule = {
        url: normalizedConfig.search.url || "",
        list: normalizedConfig.search.result || "",
        item: {
          title: normalizedConfig.search.bookName || "",
          author: normalizedConfig.search.author || "",
          link: normalizedConfig.search.bookName || "",
          latest: normalizedConfig.search.latestChapter || ""
        }
      };
    }
    
    // 处理书籍规则
    if (!normalizedConfig.bookRule && normalizedConfig.book) {
      normalizedConfig.bookRule = {
        title: normalizedConfig.book.bookName || "",
        author: normalizedConfig.book.author || "",
        intro: normalizedConfig.book.intro || "",
        cover: normalizedConfig.book.coverUrl || "",
        chapters: {
          list: normalizedConfig.toc?.item || "",
          item: {
            title: "a",
            link: "a"
          }
        }
      };
    }
    
    // 处理章节规则
    if (!normalizedConfig.chapterRule && normalizedConfig.chapter) {
      normalizedConfig.chapterRule = {
        title: normalizedConfig.chapter.title || "",
        content: normalizedConfig.chapter.content || "",
        cleanupRules: {
          remove: [],
          replace: []
        }
      };
      
      // 处理过滤规则
      if (normalizedConfig.chapter.filterTag) {
        normalizedConfig.chapterRule.cleanupRules.remove = 
          normalizedConfig.chapter.filterTag.split(" ");
      }
      
      if (normalizedConfig.chapter.filterTxt) {
        normalizedConfig.chapterRule.cleanupRules.replace = [
          {
            pattern: normalizedConfig.chapter.filterTxt,
            replacement: ""
          }
        ];
      }
    }
    
    return normalizedConfig as RuleConfig;
  }

  public registerSource(source: BaseNovelSource) {
    console.log(`registerSource: 注册源 ${source.name}`);
    this.sources.set(source.name, source);
  }

  getSource(name: string): BaseNovelSource | undefined {
    return this.sources.get(name);
  }

  getAllSources(): BaseNovelSource[] {
    const sources = Array.from(this.sources.values());
    console.log(`getAllSources: 返回 ${sources.length} 个源`);
    return sources;
  }

  async loadSourceFromConfig(config: RuleConfig): Promise<BaseNovelSource> {
    console.log(`loadSourceFromConfig: 加载配置 ${config.name}`);
    const source = new BaseNovelSource(config);
    this.registerSource(source);
    return source;
  }

  async loadSourcesFromConfigs(configs: RuleConfig[]): Promise<void> {
    console.log(`loadSourcesFromConfigs: 加载 ${configs.length} 个配置`);
    for (const config of configs) {
      try {
        await this.loadSourceFromConfig(config);
      } catch (error) {
        console.error(`loadSourcesFromConfigs: 加载配置 ${config.name} 失败`, error);
      }
    }
  }

  getSourceForUrl(url: string): BaseNovelSource | undefined {
    for (const source of this.sources.values()) {
      if (url.includes(source.baseUrl)) {
        return source;
      }
    }
    return undefined;
  }

  async searchAll(keyword: string): Promise<SearchResult[]> {
    console.log(`searchAll: 开始搜索 "${keyword}"`);
    const sources = this.getAllSources();
    console.log(`searchAll: 使用 ${sources.length} 个源进行搜索`);
    
    const searchPromises = sources.map(async (source) => {
      try {
        console.log(`searchAll: 使用源 ${source.name} 搜索...`);
        const result = await source.search(keyword);
        console.log(`searchAll: 源 ${source.name} 返回 ${result.length} 个结果`);
        
        return {
          source: source.name,
          novels: result.map(novel => ({
            title: novel.title,
            author: novel.author,
            sourceUrl: novel.url,
            description: novel.latest || ''
          }))
        };
      } catch (error) {
        console.error(`searchAll: 源 ${source.name} 搜索失败`, error);
        return {
          source: source.name,
          novels: [],
          error: error instanceof Error ? error.message : String(error)
        };
      }
    });

    const results = await Promise.all(searchPromises);
    console.log(`searchAll: 完成搜索，总共 ${results.length} 个源返回结果`);
    return results;
  }

  public async getNovelDetail(url: string): Promise<NovelDetail | null> {
    const source = this.getSourceForUrl(url);
    if (!source) return null;
    
    try {
      const bookInfo = await source.getBookInfo(url);
      
      // 转换为NovelDetail格式
      const detail: NovelDetail = {
        title: bookInfo.title,
        author: bookInfo.author,
        sourceUrl: url,
        description: bookInfo.intro || '',
        chapters: bookInfo.chapters.map(chapter => ({
          title: chapter.title,
          url: chapter.url
        }))
      };
      
      return detail;
    } catch (error) {
      console.error('获取小说详情失败:', error);
      return null;
    }
  }

  public async getChapterContent(url: string): Promise<ChapterInfo | null> {
    const source = this.getSourceForUrl(url);
    if (!source) return null;
    
    try {
      const content = await source.getChapterContent(url);
      
      // 转换为ChapterInfo格式
      return {
        title: content.title,
        url: url,
        content: content.content
      };
    } catch (error) {
      console.error('获取章节内容失败:', error);
      return null;
    }
  }
} 