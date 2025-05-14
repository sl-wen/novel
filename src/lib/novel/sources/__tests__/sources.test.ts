import { BiqugeSource } from '../biquge';
import { SourceManager } from '../manager';
import { getAllRules } from '../rules';
import { ProxyConfig } from '../base';

describe('小说源测试', () => {
  const proxy: ProxyConfig = {
    protocol: 'http',
    host: 'localhost',
    port: 7890
  };

  const manager = SourceManager.getInstance();
  const biquge = new BiqugeSource(proxy);
  jest.setTimeout(120000);

  beforeAll(() => {
    // 注册所有源
    manager.registerSource(biquge);
  });

  afterAll(async () => {
    // 清理所有挂起的请求
    await new Promise(resolve => setTimeout(resolve, 1000));
  });

  describe('笔趣阁源测试', () => {
    const keyword = '诡秘之主';
    let novelUrl = '';

    test('搜索小说', async () => {
      const result = await biquge.search(keyword);
      console.log('搜索结果:', result);
      expect(result.source).toBe('笔趣阁');
      expect(Array.isArray(result.novels)).toBe(true);
      if (result.novels.length > 0) {
        expect(result.novels[0]).toHaveProperty('title');
        expect(result.novels[0]).toHaveProperty('author');
        expect(result.novels[0]).toHaveProperty('url');
        novelUrl = result.novels[0].url;
      }
    }, 120000);

    test('获取小说详情', async () => {
      if (!novelUrl) {
        console.log('跳过详情测试：没有可用的小说URL');
        return;
      }
      const detail = await biquge.getDetail(novelUrl);
      console.log('小说详情:', detail);
      expect(detail).toHaveProperty('title');
      expect(detail).toHaveProperty('author');
      expect(detail).toHaveProperty('description');
      expect(Array.isArray(detail.chapters)).toBe(true);
      if (detail.chapters.length > 0) {
        expect(detail.chapters[0]).toHaveProperty('title');
        expect(detail.chapters[0]).toHaveProperty('url');
      }
    }, 120000);

    test('获取章节内容', async () => {
      if (!novelUrl) {
        console.log('跳过章节测试：没有可用的小说URL');
        return;
      }
      const detail = await biquge.getDetail(novelUrl);
      if (detail.chapters.length === 0) {
        console.log('跳过章节测试：没有可用的章节');
        return;
      }
      const chapter = await biquge.getChapter(detail.chapters[0].url);
      console.log('章节内容:', {
        title: chapter.title,
        contentLength: chapter.content?.length
      });
      expect(chapter).toHaveProperty('title');
      expect(chapter).toHaveProperty('content');
      expect(chapter.content?.length).toBeGreaterThan(0);
    }, 120000);
  });

  describe('源管理器测试', () => {
    test('获取所有规则', () => {
      const rules = getAllRules();
      expect(rules.length).toBeGreaterThan(0);
      rules.forEach(rule => {
        expect(rule).toHaveProperty('name');
        expect(rule).toHaveProperty('url');
        expect(rule).toHaveProperty('search');
        expect(rule).toHaveProperty('detail');
        expect(rule).toHaveProperty('chapter');
      });
    });

    test('通过URL获取源', () => {
      const url = 'https://www.biquge.com.cn/book/1234';
      const source = manager.getSourceForUrl(url);
      expect(source).toBeDefined();
      expect(source?.name).toBe('笔趣阁');
    });

    test('并发搜索', async () => {
      const results = await manager.searchAll('修真');
      console.log('并发搜索结果:', results);
      expect(results.length).toBeGreaterThan(0);
      results.forEach(result => {
        expect(result).toHaveProperty('source');
        expect(result).toHaveProperty('novels');
        if ('error' in result) {
          console.warn(`源 ${result.source} 搜索失败:`, result.error);
        }
      });
    }, 120000);
  });
}); 