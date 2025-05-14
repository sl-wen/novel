'use client';

import { useState } from 'react';
import { SearchResult } from '@/lib/novel/types/source';

export default function RuleTestPage() {
  const [keyword, setKeyword] = useState('');
  const [sourceResults, setSourceResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!keyword.trim()) {
      setError('请输入搜索关键词');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSourceResults([]);
    setActiveSource(null);

    try {
      console.log('开始搜索:', keyword);
      const response = await fetch(`/api/novel/search?keyword=${encodeURIComponent(keyword)}`);
      console.log('搜索响应:', response.status);
      
      if (!response.ok) {
        throw new Error(`搜索失败: ${response.status}`);
      }

      const data = await response.json();
      console.log('搜索结果:', data);
      
      if (data.error) {
        throw new Error(data.error);
      }

      setSourceResults(Array.isArray(data) ? data : []);
      
      // 默认显示第一个有结果的书源
      const firstSourceWithResults = (Array.isArray(data) ? data : []).find(source => source.novels && source.novels.length > 0);
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

  // 获取当前活跃书源的小说列表
  const activeSourceNovels = sourceResults.find(source => source.source === activeSource)?.novels || [];

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-center mb-8">规则测试页面</h1>
      
      <div className="flex gap-2 mb-8">
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
          {loading ? '搜索中...' : '搜索'}
        </button>
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

      {/* 书源一览 */}
      {sourceResults.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-bold mb-4">书源一览</h2>
          <div className="flex flex-wrap gap-2 mb-4">
            {sourceResults.map((source) => (
              <button
                key={source.source}
                onClick={() => setActiveSource(source.source)}
                className={`px-4 py-2 rounded ${
                  activeSource === source.source 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-gray-200 hover:bg-gray-300'
                }`}
              >
                {source.source} ({source.novels?.length || 0})
              </button>
            ))}
          </div>
          
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
                  <tr key={source.source} className={activeSource === source.source ? 'bg-blue-50' : ''}>
                    <td className="border border-gray-300 px-4 py-2">{source.source}</td>
                    <td className="border border-gray-300 px-4 py-2">{source.novels?.length || 0}</td>
                    <td className="border border-gray-300 px-4 py-2">
                      {source.error ? (
                        <span className="text-red-500">{source.error}</span>
                      ) : (
                        <span className="text-green-500">成功</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 搜索结果表格 */}
      {activeSourceNovels.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-bold mb-4">
            {activeSource} 搜索结果 ({activeSourceNovels.length}本)
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-4 py-2">序号</th>
                  <th className="border border-gray-300 px-4 py-2">书名</th>
                  <th className="border border-gray-300 px-4 py-2">作者</th>
                  <th className="border border-gray-300 px-4 py-2">简介</th>
                  <th className="border border-gray-300 px-4 py-2">链接</th>
                </tr>
              </thead>
              <tbody>
                {activeSourceNovels.map((novel, index) => (
                  <tr key={`${novel.sourceUrl}-${index}`}>
                    <td className="border border-gray-300 px-4 py-2">{index + 1}</td>
                    <td className="border border-gray-300 px-4 py-2">{novel.title}</td>
                    <td className="border border-gray-300 px-4 py-2">{novel.author}</td>
                    <td className="border border-gray-300 px-4 py-2">{novel.description}</td>
                    <td className="border border-gray-300 px-4 py-2">
                      <a 
                        href={novel.sourceUrl} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline"
                      >
                        查看
                      </a>
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