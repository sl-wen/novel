import { Biquge22Source } from '../biquge22';

describe('笔趣阁22源测试', () => {
  const source = new Biquge22Source();
  jest.setTimeout(120000);

  describe('搜索测试', () => {
    const keyword = '诡秘之主';
    let novelUrl = '';

    test('搜索小说', async () => {
      const result = await source.search(keyword);
      console.log('搜索结果:', result);
      expect(result.source).toBe('笔趣阁22');
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
      const detail = await source.getDetail(novelUrl);
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
      const detail = await source.getDetail(novelUrl);
      if (detail.chapters.length === 0) {
        console.log('跳过章节测试：没有可用的章节');
        return;
      }
      const chapter = await source.getChapter(detail.chapters[0].url);
      console.log('章节内容:', {
        title: chapter.title,
        contentLength: chapter.content?.length
      });
      expect(chapter).toHaveProperty('title');
      expect(chapter).toHaveProperty('content');
      expect(chapter.content?.length).toBeGreaterThan(0);
    }, 120000);
  });
}); 