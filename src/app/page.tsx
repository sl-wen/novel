'use client';

import { useState } from 'react';
import { NovelInfo } from '@/lib/novel/types/source';
import { SearchResult } from '@/lib/novel/types/source';
import { useEffect } from 'react';

export default function Home() {
  const [keyword, setKeyword] = useState('');
  const [sourceResults, setSourceResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<string | null>(null);
  const [allNovels, setAllNovels] = useState<NovelInfo[]>([]);
  const [downloadFormat, setDownloadFormat] = useState<'txt' | 'epub'>('txt');

  const handleSearch = async () => {
    if (!keyword.trim()) {
      setError('请输入搜索关键词');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSourceResults([]);
    setActiveSource(null);
    setAllNovels([]);

    try {
      console.log('开始搜索:', keyword);
      const response = await fetch(`/api/novel/search?keyword=${encodeURIComponent(keyword)}`);
      console.log('搜索响应:', response.status);
      
      if (!response.ok) {
        throw new Error(`搜索失败: ${response.status}`);
      }

      const data: SearchResult[] = await response.json();
      console.log('搜索结果:', data);
      
      if ('error' in data) {
        throw new Error(data.error as string);
      }

      setSourceResults(data);
      
      // 合并所有小说结果
      const novels: NovelInfo[] = [];
      data.forEach((source, sourceIndex) => {
        if (source.novels && source.novels.length > 0) {
          source.novels.forEach(novel => {
            // 确保类型兼容
            const novelWithSource: NovelInfo = {
              title: novel.title,
              author: novel.author,
              sourceUrl: novel.sourceUrl,
              description: novel.description,
              source: source.source,
              score: novel.score,
              sourceId: sourceIndex + 1 // 使用书源索引作为书源ID
            };
            novels.push(novelWithSource);
          });
        }
      });
      setAllNovels(novels);
      
      // 默认显示第一个有结果的书源
      const firstSourceWithResults = data.find(source => source.novels && source.novels.length > 0);
      if (firstSourceWithResults) {
        setActiveSource(firstSourceWithResults.source);
      }
    } catch (error) {
      console.error('搜索失败:', error);
      setError(error instanceof Error ? error.message : '搜索失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleDownload = async (url: string) => {
    if (downloading) return;
    
    setDownloading(url);
    try {
      const response = await fetch(`/api/novel/download?url=${encodeURIComponent(url)}&format=${downloadFormat}`);
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status}`);
      }
      const data = await response.json();
      if (data.url) {
        // 创建隐藏的a标签进行下载
        const link = document.createElement('a');
        link.href = data.url;
        link.download = data.url.split('/').pop() || 'novel';
        link.click();
      }
      console.log('下载成功:', data);
    } catch (error) {
      console.error('下载失败:', error);
      setError(error instanceof Error ? error.message : '下载失败，请稍后重试');
    } finally {
      setDownloading(null);
    }
  };

  // 获取当前系统时间，模拟上次更新时间
  const getUpdateTime = (index: number) => {
    const date = new Date();
    date.setDate(date.getDate() - (index % 30)); // 随机的过去时间
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  };

  // 模拟章节数据
  const getChapterCount = (index: number) => {
    return (1000 + (index * 113) % 2000); // 模拟章节数，在1000-3000之间
  };

  // 模拟最新章节
  const getLatestChapter = (novel: NovelInfo, index: number) => {
    if (novel.description && novel.description.length > 5) {
      return novel.description;
    }
    const templates = [
      "第%d章 终章",
      "第%d章 大结局",
      "第%d章 新的开始",
      "第%d章 %s",
      "第%d卷 %s"
    ];
    
    const chapterNum = getChapterCount(index);
    const template = templates[index % templates.length];
    const titles = ["冒险开始", "命运转折", "最终对决", "喜然回首(结尾)", "逆转未来"];
    const title = titles[index % titles.length];
    
    return template.replace("%d", chapterNum.toString()).replace("%s", title);
  };

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-center mb-8">小说下载</h1>
      
      <div className="mb-8">
        <div className="mb-2">聚合搜索:</div>
        <div className="flex gap-2">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="请输入书名或作者"
            className="flex-1 px-4 py-2 border rounded"
          />
          <button
            onClick={handleSearch}
            disabled={loading || !keyword.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            聚合搜索
          </button>
          <button className="px-6 py-2 bg-gray-200 text-black rounded hover:bg-gray-300">
            书源一览
          </button>
          <button className="px-6 py-2 bg-gray-200 text-black rounded hover:bg-gray-300">
            遨游码生成
          </button>
        </div>
      </div>

      {error && (
        <div className="text-red-500 text-center mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center mb-4">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
        </div>
      )}

      {/* 搜索结果 */}
      {allNovels.length > 0 ? (
        <div className="mb-8">
          <h2 className="text-xl font-bold mb-4">搜索结果</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-4 py-2 text-center">序号</th>
                  <th className="border border-gray-300 px-4 py-2 text-center">书名</th>
                  <th className="border border-gray-300 px-4 py-2 text-center">作者</th>
                  <th className="border border-gray-300 px-4 py-2 text-center">章节数</th>
                  <th className="border border-gray-300 px-4 py-2 text-center">最新章节</th>
                  <th className="border border-gray-300 px-4 py-2 text-center">最后更新时间</th>
                  <th className="border border-gray-300 px-4 py-2 text-center">书源ID+书源</th>
                  <th className="border border-gray-300 px-4 py-2 text-center">下载</th>
                </tr>
              </thead>
              <tbody>
                {allNovels.length > 0 ? (
                  allNovels.map((novel, index) => (
                    <tr key={`${novel.sourceUrl}-${index}`}>
                      <td className="border border-gray-300 px-4 py-2 text-center">{index + 1}</td>
                      <td className="border border-gray-300 px-4 py-2">{novel.title}</td>
                      <td className="border border-gray-300 px-4 py-2">{novel.author || '-'}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{getChapterCount(index)}</td>
                      <td className="border border-gray-300 px-4 py-2">{getLatestChapter(novel, index)}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{getUpdateTime(index)}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{novel.sourceId || index % 20 + 1}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">
                        <button
                          onClick={() => handleDownload(novel.sourceUrl)}
                          disabled={downloading === novel.sourceUrl}
                          className="px-4 py-1 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                        >
                          下载
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="border border-gray-300 px-4 py-2 text-center">
                      请搜索小说
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          
          {/* 下载选项 */}
          <div className="mt-4 flex gap-4 items-center">
            <span>下载格式:</span>
            <div className="flex gap-2">
              <label className="flex items-center">
                <input 
                  type="radio" 
                  name="format" 
                  value="txt" 
                  checked={downloadFormat === 'txt'} 
                  onChange={() => setDownloadFormat('txt')} 
                />
                <span className="ml-1">TXT</span>
              </label>
              <label className="flex items-center ml-4">
                <input 
                  type="radio" 
                  name="format" 
                  value="epub" 
                  checked={downloadFormat === 'epub'} 
                  onChange={() => setDownloadFormat('epub')} 
                />
                <span className="ml-1">EPUB</span>
              </label>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-8 border border-gray-300 rounded">
          请搜索小说
        </div>
      )}

      {/* 书源结果统计 */}
      {sourceResults.length > 0 && (
        <div className="mb-8 mt-8">
          <h2 className="text-xl font-bold mb-4">各源搜索状态</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-4 py-2">书源</th>
                  <th className="border border-gray-300 px-4 py-2">结果数</th>
                  <th className="border border-gray-300 px-4 py-2">状态</th>
                </tr>
              </thead>
              <tbody>
                {sourceResults.map((source) => (
                  <tr key={source.source}>
                    <td className="border border-gray-300 px-4 py-2">{source.source}</td>
                    <td className="border border-gray-300 px-4 py-2">{source.novels?.length || 0}</td>
                    <td className="border border-gray-300 px-4 py-2">
                      {source.error ? (
                        <span className="text-red-500">请求失败，已重试 3 次: {source.error.substring(0, 50)}...</span>
                      ) : source.novels?.length > 0 ? (
                        <span className="text-green-500">成功</span>
                      ) : (
                        <span className="text-orange-500">无结果</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
