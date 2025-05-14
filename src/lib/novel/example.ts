import { sourceManager } from './sources/init';
import { SearchResult } from './types/source';

async function example() {
    try {
        // 搜索小说
        console.log('搜索小说...');
        const searchResults = await sourceManager.searchAll('诡秘之主');
        console.log('搜索结果:', searchResults);

        // 如果有搜索结果，获取第一个小说的详情
        if (searchResults.length > 0) {
            const firstSource = searchResults[0] as SearchResult;
            if (firstSource.novels && firstSource.novels.length > 0) {
                const firstNovel = firstSource.novels[0];
                console.log('获取小说详情...');
                const novelDetail = await sourceManager.getNovelDetail(firstNovel.sourceUrl);
                console.log('小说详情:', novelDetail);

                // 如果有章节，获取第一章内容
                if (novelDetail && novelDetail.chapters.length > 0) {
                    console.log('获取第一章内容...');
                    const firstChapter = await sourceManager.getChapterContent(novelDetail.chapters[0].url);
                    console.log('第一章内容:', firstChapter);
                }
            } else {
                console.log('未找到匹配的小说');
            }
        } else {
            console.log('搜索结果为空');
        }
    } catch (error) {
        console.error('发生错误:', error);
    }
}

// 运行示例
example().catch(console.error); 