import axios, { AxiosInstance, AxiosError } from 'axios';
import * as cheerio from 'cheerio';
import { INovelSource, NovelInfo, ChapterInfo, NovelDetail, SearchResult as SourceSearchResult } from '../types/source';
import { RuleConfig, NovelSource, BookInfo, ChapterContent, Chapter, SearchResult } from '../types/rule';
import https from 'https';
import { SocksProxyAgent } from 'socks-proxy-agent';
import { HttpsProxyAgent } from 'https-proxy-agent';
import fetch from 'node-fetch';
import iconv from 'iconv-lite';

const DEFAULT_RETRY_TIMES = 3;
const DEFAULT_TIMEOUT = 30000;
const DEFAULT_RETRY_DELAY = 1000;

export type ProxyConfig = {
  protocol: 'http' | 'socks5';
  host: string;
  port: number;
  auth?: {
    username: string;
    password: string;
  };
};

export type SourceOptions = {
  timeout?: number;
  retries?: number;
  userAgent?: string;
  encoding?: string;
};

export class BaseNovelSource implements NovelSource {
  protected http: AxiosInstance;
  public readonly config: RuleConfig;
  public name: string;
  public baseUrl: string;
  protected options: Required<SourceOptions>;
  protected proxy?: ProxyConfig;

  constructor(config: RuleConfig, options?: SourceOptions, proxy?: ProxyConfig) {
    this.config = config;
    this.name = config.name;
    this.baseUrl = config.baseUrl;
    this.proxy = proxy;

    this.options = {
      timeout: options?.timeout || DEFAULT_TIMEOUT,
      retries: options?.retries || DEFAULT_RETRY_TIMES,
      userAgent: options?.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      encoding: options?.encoding || config.encoding || 'utf-8'
    };

    let agent;
    if (proxy) {
      const proxyUrl = proxy.auth
        ? `${proxy.protocol}://${proxy.auth.username}:${proxy.auth.password}@${proxy.host}:${proxy.port}`
        : `${proxy.protocol}://${proxy.host}:${proxy.port}`;

      agent = proxy.protocol === 'socks5'
        ? new SocksProxyAgent(proxyUrl)
        : new HttpsProxyAgent(proxyUrl);
    } else {
      agent = new https.Agent({
        rejectUnauthorized: false, // 允许自签名证书
        keepAlive: true,
        timeout: 30000 // 30秒超时
      });
    }

    this.http = axios.create({
      timeout: this.options.timeout,
      headers: {
        'User-Agent': this.options.userAgent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      },
      httpsAgent: agent,
      proxy: false, // 使用自定义代理代替 axios 的代理
      maxRedirects: 5,
      validateStatus: function (status) {
        return status >= 200 && status < 300;
      }
    });
  }

  protected async fetchWithRetry<T>(
    fn: () => Promise<T>,
    retryTimes = this.options.retries
  ): Promise<T> {
    let lastError: Error | null = null;
    
    for (let i = 0; i < retryTimes; i++) {
      try {
        // 每次重试增加一些随机延迟，防止被网站识别为爬虫
        if (i > 0) {
          const delay = DEFAULT_RETRY_DELAY * (i + 1) * (1 + Math.random()) + Math.random() * 5000;
          console.log(`重试前等待 ${delay.toFixed(0)}ms`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
        
        // 使用最大超时时间，避免一直等待
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error('Timeout exceeded')), 
            this.options.timeout * (1 + i * 0.5)); // 每次重试增加超时时间
        });
        
        // 使用Promise.race确保请求不会一直等待
        return await Promise.race([fn(), timeoutPromise]);
      } catch (error: any) {
        lastError = error as Error;
        const errorMsg = error.message || '';
        
        // 处理HTTP/HTTPS协议问题
        if (errorMsg.includes('Protocol "http:" not supported')) {
          console.warn(`HTTP协议不支持，尝试转换为HTTPS: ${errorMsg}`);
          try {
            // 动态修改协议为HTTPS并重试
            if (typeof fn.toString === 'function' && fn.toString().includes('http:')) {
              const newFn = async () => {
                const originalFn = fn.toString();
                // 创建一个新的函数，替换http:为https:
                const newFnStr = originalFn.replace(/http:/g, 'https:');
                return await eval(`(${newFnStr})()`) as Promise<T>;
              };
              
              console.log(`尝试使用HTTPS协议重试...`);
              return await newFn();
            }
          } catch (httpsError: any) {
            console.warn(`转换为HTTPS后仍然失败: ${httpsError.message}`);
          }
        }
        
        // 对不同类型的错误使用不同的重试策略
        if (error instanceof AxiosError && error.code === 'ECONNABORTED') {
          console.warn(`请求超时，正在进行第 ${i + 1} 次重试`);
          // 超时错误，增加更长的延迟
          await new Promise(resolve => setTimeout(resolve, 3000 + Math.random() * 2000));
        } else if (errorMsg.includes('Client network socket disconnected') || 
                   errorMsg.includes('socket hang up') ||
                   errorMsg.includes('ECONNRESET')) {
          console.warn(`TLS连接/Socket问题，正在进行第 ${i + 1} 次重试，将尝试不同的TLS版本`);
          
          // TLS连接问题需要特殊处理，我们将创建一个降级连接函数
          if (typeof fn === 'function' && i < retryTimes - 1) {
            try {
              // 等待更长时间
              await new Promise(resolve => setTimeout(resolve, 8000 + Math.random() * 4000));
              
              // 尝试使用纯HTTP版本的URL，不进行TLS验证
              const fnStr = fn.toString();
              if (fnStr.includes('https:')) {
                const httpFn = async () => {
                  // 尝试回退到HTTP版本
                  const httpStr = fnStr.replace(/https:/g, 'http:');
                  return await eval(`(${httpStr})()`) as Promise<T>;
                };
                
                console.log(`尝试降级到HTTP协议...`);
                try {
                  return await httpFn();
                } catch (httpError: any) {
                  console.warn(`HTTP降级失败: ${httpError.message}`);
                }
              }
            } catch (tlsError: any) {
              console.warn(`TLS降级处理失败: ${tlsError.message}`);
            }
          }
          
          // 标准等待
          await new Promise(resolve => setTimeout(resolve, 7000 + Math.random() * 3000));
        } else if (errorMsg.includes('certificate has expired') || errorMsg.includes('self signed certificate')) {
          console.warn(`SSL证书问题，正在进行第 ${i + 1} 次重试`);
          // 证书问题，尝试使用不同的请求库
        } else if (errorMsg.includes('status: 520') || errorMsg.includes('status: 521') || errorMsg.includes('status: 522')) {
          console.warn(`Cloudflare或Web服务器错误 (${errorMsg})，正在进行第 ${i + 1} 次重试`);
          // Cloudflare错误，增加更长的延迟
          await new Promise(resolve => setTimeout(resolve, 10000 + Math.random() * 5000));
        } else {
          console.warn(`请求失败：${errorMsg}，正在进行第 ${i + 1} 次重试`);
          // 普通错误，使用标准延迟
        }
      }
    }
    
    throw new Error(`请求失败，已重试 ${retryTimes} 次：${lastError?.message || '未知错误'}`);
  }

  protected async fetchHtml(url: string): Promise<any> {
    return this.fetchWithRetry(async () => {
      try {
        console.log(`正在请求: ${url}`);
        // 尝试使用axios
        const response = await this.http.get(url);
        return cheerio.load(response.data);
      } catch (error: any) {
        console.log(`axios请求失败，尝试使用fetch: ${error.message}`);
        // 如果axios失败，尝试使用fetch
        return this.fetchAndParse(url);
      }
    });
  }

  protected normalizeUrl(url: string): string {
    if (url.startsWith('http')) return url;
    return new URL(url, this.baseUrl).toString();
  }

  public isSupported(url: string): boolean {
    return url.includes(this.baseUrl);
  }

  public getSourceId(): string {
    return this.name.toLowerCase().replace(/\s+/g, '-');
  }

  async search(keyword: string): Promise<SearchResult[]> {
    const url = this.config.searchRule.url.replace('{keyword}', encodeURIComponent(keyword));
    const $ = await this.fetchHtml(url);
    
    const results: SearchResult[] = [];
    $(this.config.searchRule.list).each((_: number, el: any) => {
      const $item = $(el);
      const result: SearchResult = {
        title: $item.find(this.config.searchRule.item.title).text().trim(),
        author: $item.find(this.config.searchRule.item.author).text().trim(),
        url: this.normalizeUrl($item.find(this.config.searchRule.item.link).attr('href') || ''),
      };
      
      if (this.config.searchRule.item.latest) {
        result.latest = $item.find(this.config.searchRule.item.latest).text().trim();
      }
      
      results.push(result);
    });

    return results;
  }

  async getBookInfo(url: string): Promise<BookInfo> {
    const $ = await this.fetchHtml(url);
    
    const chapters: Chapter[] = [];
    $(this.config.bookRule.chapters.list).each((_: number, el: any) => {
      const $item = $(el);
      chapters.push({
        title: $item.find(this.config.bookRule.chapters.item.title).text().trim(),
        url: this.normalizeUrl($item.find(this.config.bookRule.chapters.item.link).attr('href') || ''),
      });
    });

    const info: BookInfo = {
      title: $(this.config.bookRule.title).text().trim(),
      author: $(this.config.bookRule.author).text().trim(),
      chapters,
    };

    if (this.config.bookRule.intro) {
      info.intro = $(this.config.bookRule.intro).text().trim();
    }

    if (this.config.bookRule.cover) {
      const coverUrl = $(this.config.bookRule.cover).attr('src');
      if (coverUrl) {
        info.cover = this.normalizeUrl(coverUrl);
      }
    }

    return info;
  }

  async getChapterContent(url: string): Promise<ChapterContent> {
    const $ = await this.fetchHtml(url);
    let content = $(this.config.chapterRule.content).html() || '';

    // 应用清理规则
    if (this.config.chapterRule.cleanupRules) {
      const { remove, replace } = this.config.chapterRule.cleanupRules;
      
      // 移除不需要的元素
      if (remove) {
        remove.forEach(selector => {
          $(selector).remove();
        });
        content = $(this.config.chapterRule.content).html() || '';
      }

      // 替换内容
      if (replace) {
        replace.forEach(({ pattern, replacement }) => {
          content = content.replace(new RegExp(pattern, 'g'), replacement);
        });
      }
    }

    return {
      title: $(this.config.chapterRule.title).text().trim(),
      content: content.trim(),
    };
  }

  protected async fetchAndParse(url: string): Promise<any> {
    console.log(`使用fetch获取页面: ${url}`);
    
    // 存储原始URL，以便在需要时恢复
    const originalUrl = url;
    let usedHttps = false;
    
    // 如果是HTTP协议，我们先尝试原始URL，如果失败再尝试HTTPS
    if (url.startsWith('http:')) {
      // 在开发环境中保持HTTP，在生产环境中尝试HTTPS
      if (process.env.NODE_ENV === 'production') {
        console.log(`尝试使用HTTPS协议替代HTTP`);
        url = url.replace('http:', 'https:');
        usedHttps = true;
      }
    }
    
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.options.timeout);
    
    try {
      const fetchOptions: any = {
        headers: {
          'User-Agent': this.options.userAgent,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        },
        signal: controller.signal,
      };
      
      // 添加TLS配置选项
      const tlsOptions = {
        rejectUnauthorized: false, // 允许自签名证书
        keepAlive: true,
        timeout: this.options.timeout,
        minVersion: 'TLSv1' as any,
        maxVersion: 'TLSv1.3' as any,
        secureOptions: 0, // 禁用所有SSL检查
        ciphers: 'ALL', // 允许所有加密算法
      };
      
      // 在Node环境中添加agent选项
      if (typeof window === 'undefined') {
        fetchOptions.agent = () => new https.Agent(tlsOptions);
      }
      
      // 准备多个备选方案
      const attemptFetch = async (attemptUrl: string, options: any): Promise<Response> => {
        try {
          return await fetch(attemptUrl, options);
        } catch (error: any) {
          if (error.message?.includes('socket disconnected') || 
              error.message?.includes('TLS') || 
              error.message?.includes('SSL') ||
              error.message?.includes('certificate')) {
            
            console.log(`尝试使用不同的TLS配置...`);
            // 尝试使用不同的TLS配置
            const altOptions = { ...options };
            if (typeof window === 'undefined') {
              altOptions.agent = () => new https.Agent({
                ...tlsOptions,
                minVersion: undefined,
                maxVersion: undefined,
                secureOptions: 0
              });
            }
            
            return await fetch(attemptUrl, altOptions);
          }
          throw error;
        }
      };
      
      // 尝试多种方式获取内容
      let response;
      try {
        response = await attemptFetch(url, fetchOptions);
      } catch (error: any) {
        // 如果使用HTTPS失败但原始URL是HTTP
        if (usedHttps && error.message && 
            (error.message.includes('socket disconnected') || 
             error.message.includes('certificate') || 
             error.message.includes('SSL'))) {
          // 恢复使用HTTP协议，某些站点可能只支持HTTP
          console.log(`HTTPS连接失败，尝试回退到HTTP: ${originalUrl}`);
          
          // 创建新的特殊agent，忽略TLS错误
          const httpFetchOptions = { ...fetchOptions };
          if (typeof window === 'undefined') {
            httpFetchOptions.agent = () => new https.Agent({
              ...tlsOptions,
              rejectUnauthorized: false,
              secureOptions: 0 // 完全禁用SSL检查
            });
          }
          
          try {
            // 尝试使用原始HTTP URL
            response = await attemptFetch(originalUrl, httpFetchOptions);
          } catch (httpError: any) {
            console.error(`HTTP协议也失败: ${httpError.message}`);
            throw httpError;
          }
        } else if (error.message && error.message.includes('Protocol "http:" not supported')) {
          // 如果HTTP协议不支持，尝试转换为HTTPS
          const httpsUrl = originalUrl.replace('http:', 'https:');
          console.log(`HTTP协议不支持，尝试使用HTTPS: ${httpsUrl}`);
          response = await attemptFetch(httpsUrl, fetchOptions);
        } else {
          throw error;
        }
      }
      
      // 处理非2xx响应
      if (!response.ok) {
        const status = response.status;
        
        // 特殊处理Cloudflare错误
        if (status === 520 || status === 521 || status === 522) {
          console.warn(`发现Cloudflare错误: ${status}`);
          throw new Error(`Cloudflare错误 ${status}: 源站可能不可用`);
        }
        
        // 特殊处理403错误
        if (status === 403) {
          console.warn(`访问被拒绝(403)，可能需要绕过反爬虫措施`);
          // 可以在这里添加绕过方法
        }
        
        throw new Error(`HTTP error! status: ${status}`);
      }
      
      let html = await response.text();
      
      // 检查编码
      if (this.options.encoding !== 'utf-8' && typeof iconv.decode === 'function') {
        try {
          const buffer = Buffer.from(html);
          html = iconv.decode(buffer, this.options.encoding);
        } catch (error: any) {
          console.warn(`iconv解码失败: ${error.message}`);
        }
      }
      
      return cheerio.load(html);
    } catch (error: any) {
      console.error(`fetch请求失败: ${error.message}`);
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  protected resolveUrl(path: string): string {
    if (path.startsWith('http')) {
      return path;
    }
    return new URL(path, this.baseUrl).toString();
  }
} 