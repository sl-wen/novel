# 小说聚合搜索与下载API使用说明

## 项目简介

这是一个基于FastAPI的小说聚合搜索与下载API服务，支持从多个书源搜索小说并提供下载功能。

## 功能特性

- ✅ 多书源支持（20个预配置书源）
- ✅ 小说搜索功能（每个书源最多返回2条结果，降低重复与噪声）
- ✅ 书籍详情获取 / 章节目录获取
- ✅ 小说下载（支持TXT、EPUB），支持异步任务与进度查询
- ✅ 异步并发处理、连接池、UA 轮换
- ✅ 错误重试、指数退避、结果缓存
- ✅ 优化版 API：性能监控、健康检查、缓存管理
- ✅ 完善的日志记录

## 安装和启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python run.py
```

服务将在 http://localhost:8000 启动

### 3. 查看API文档

访问 http://localhost:8000/docs 查看Swagger UI文档

## API接口说明

### 1. 根目录 - 服务状态检查

**接口地址：** `GET /`

**响应示例：**
```json
{
  "code": 200,
  "message": "小说聚合搜索与下载API服务正在运行",
  "data": {
    "version": "0.1.0",
    "docs": "/docs"
  }
}
```

### 2. 获取书源列表

**接口地址：** `GET /api/novels/sources`

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "rule": {
        "id": 1,
        "name": "香书小说",
        "url": "http://www.xbiqugu.la/",
        "enabled": true,
        "type": "html",
        "language": "zh_CN"
      }
    }
  ]
}
```

### 3. 搜索小说（标准版）

**接口地址：** `GET /api/novels/search`

**请求参数：**
- `keyword` (必需): 搜索关键词（书名或作者名）
- `maxResults` (可选): 最大返回结果数，默认30，范围1-100

说明：每个书源最多返回2条结果（内置策略），实际返回不超过 `maxResults`。

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "sourceId": 1,
      "sourceName": "香书小说",
      "url": "https://example.com/book/123",
      "title": "斗破苍穹",
      "author": "天蚕土豆",
      "category": "玄幻",
      "latestChapter": "第一千章 大结局",
      "lastUpdateTime": "2023-12-25 12:00:00",
      "status": "已完结",
      "wordCount": "300万字"
    }
  ]
}
```

### 4. 获取书籍详情

**接口地址：** `GET /api/novels/detail`

**请求参数：**
- `url` (必需): 小说详情页URL
- `sourceId` (可选): 书源ID，默认为1

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "url": "https://example.com/book/123",
    "title": "斗破苍穹",
    "author": "天蚕土豆",
    "intro": "这里是小说简介...",
    "category": "玄幻",
    "coverUrl": "https://example.com/cover.jpg",
    "latestChapter": "第一千章 大结局",
    "lastUpdateTime": "2023-12-25 12:00:00",
    "status": "已完结",
    "wordCount": "300万字"
  }
}
```

### 5. 获取章节目录

**接口地址：** `GET /api/novels/toc`

**请求参数：**
- `url` (必需): 小说详情页URL
- `sourceId` (可选): 书源ID，默认为1

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "url": "https://example.com/chapter/1",
      "title": "第一章 废物",
      "order": 1
    },
    {
      "url": "https://example.com/chapter/2",
      "title": "第二章 觉醒",
      "order": 2
    }
  ]
}
```

### 6. 下载小说（标准版）

**接口地址：** `GET /api/novels/download`

**请求参数：**
- `url` (必需): 小说详情页URL
- `sourceId` (可选): 书源ID，默认为1
- `format` (可选): 下载格式，支持txt、epub，默认为txt

**响应：** 直接返回文件流进行下载

#### 异步下载任务（推荐用于长文本）
- 启动任务：`POST /api/novels/download/start`（返回 `task_id`）
- 查询进度：`GET /api/novels/download/progress?task_id=...`
- 拉取结果：`GET /api/novels/download/result?task_id=...`（完成后返回文件流）

进度数据包含任务状态、完成章节数、错误信息、生成文件路径等。

---

## 优化版 API（/api/optimized）

引入缓存、并发优化、性能监控与健康检查。

### 1. 搜索小说（优化版）
**接口地址：** `GET /api/optimized/search`

**请求参数：**
- `keyword` (必需)
- `maxResults` (可选，默认30，范围1-100)

说明：每个书源最多返回2条结果；响应包含 `meta` 字段（耗时、是否命中缓存等）。

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": [ /* 同标准版 */ ],
  "meta": { "duration_ms": 123.4, "total_results": 10, "cached": false }
}
```

### 2. 获取书籍详情（优化版）
`GET /api/optimized/detail?url=...&sourceId=1`

返回结构同标准版，额外包含 `meta.duration_ms`、`meta.source_id`。

### 3. 获取章节目录（优化版）
`GET /api/optimized/toc?url=...&sourceId=1`

返回结构同标准版，额外包含 `meta.duration_ms`、`meta.total_chapters`。

### 4. 下载小说（优化版）
`GET /api/optimized/download?url=...&sourceId=1&format=txt`

直接返回文件流，响应头包含：`X-Download-Duration-MS`、`X-File-Size`、`X-Task-ID`。

### 5. 获取书源列表（优化版）
`GET /api/optimized/sources`

返回结构同标准版，额外包含 `meta`（耗时、总书源数）。

### 6. 性能统计
`GET /api/optimized/performance`

返回性能监控摘要、缓存统计、HTTP 客户端统计、最近慢操作列表。

### 7. 清理缓存
`POST /api/optimized/cache/clear`

返回清理条目数与时间戳。

### 8. 健康检查
`GET /api/optimized/health`

返回 `status`（healthy/warning/unhealthy）、`health_score`、关键指标汇总。

## 错误响应格式

当API发生错误时，返回格式如下：

```json
{
  "code": 500,
  "message": "错误描述",
  "data": null
}
```

## 配置说明

主要配置项在 `app/core/config.py` 中：

- `DEFAULT_SOURCE_ID`: 默认书源ID
- `MAX_SEARCH_RESULTS`: 最大搜索结果数
- `DEFAULT_TIMEOUT`: 默认请求超时时间
- `REQUEST_RETRY_TIMES`: 请求重试次数
- `MAX_CONCURRENT_REQUESTS`: 最大并发请求数

说明：系统内置“每书源最多2条搜索结果”的限制以提升相关性与稳定性，该策略优先于 `MAX_SEARCH_RESULTS`。

## 书源规则

书源规则文件位于 `rules` 目录下，采用JSON格式配置各个网站的爬取规则。

### 规则文件结构示例

```json
{
  "id": 1,
  "name": "书源名称",
  "url": "https://example.com/",
  "enabled": true,
  "type": "html",
  "language": "zh_CN",
  "search": {
    "url": "搜索接口URL",
    "method": "get",
    "list": "CSS选择器-结果列表",
    "name": "CSS选择器-书名",
    "author": "CSS选择器-作者"
  },
  "book": {
    "name": "CSS选择器-书名",
    "author": "CSS选择器-作者",
    "intro": "CSS选择器-简介"
  },
  "toc": {
    "list": "CSS选择器-章节列表",
    "title": "CSS选择器-章节标题",
    "url": "CSS选择器-章节链接"
  },
  "chapter": {
    "title": "CSS选择器-章节标题",
    "content": "CSS选择器-章节内容",
    "ad_patterns": ["广告过滤正则表达式"]
  }
}
```

## 注意事项

1. **反爬虫限制**: 部分网站可能有反爬虫机制，返回403错误属于正常现象
2. **并发控制**: API内置了并发控制机制，避免对目标网站造成过大压力
3. **内容过滤**: 自动过滤广告和无用内容
4. **文件格式**: EPUB需要额外的依赖库支持

## 技术架构

- **Web框架**: FastAPI
- **异步处理**: aiohttp + asyncio
- **HTML解析**: BeautifulSoup4
- **文件生成**: ebooklib (EPUB)
- **配置管理**: pydantic-settings

## 开发和扩展

### 添加新书源

1. 在 `/rules` 目录下创建新的规则文件
2. 参考现有规则文件格式编写规则
3. 重启服务即可生效

### 自定义解析器

可以在 `app/parsers/` 目录下扩展或修改解析器逻辑。

## 许可证

本项目仅供学习和研究使用，请遵守相关网站的使用条款和robots.txt协议。 