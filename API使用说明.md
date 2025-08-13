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



## API 接口说明（/api/optimized）

引入缓存、并发优化、性能监控与健康检查。

### 1. 搜索小说
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

### 2. 获取书籍详情
`GET /api/optimized/detail?url=...&sourceId=1`

返回结构同标准版，额外包含 `meta.duration_ms`、`meta.source_id`。

### 3. 获取章节目录
`GET /api/optimized/toc?url=...&sourceId=1`

返回结构同标准版，额外包含 `meta.duration_ms`、`meta.total_chapters`。

### 4. 下载小说

#### 同步下载
`GET /api/optimized/download?url=...&sourceId=1&format=txt`

直接返回文件流，响应头包含：`X-Download-Duration-MS`、`X-File-Size`、`X-Task-ID`。

#### 异步下载（推荐用于长文本）
- 启动任务：`POST /api/optimized/download/start`（返回 `task_id`）
- 查询进度：`GET /api/optimized/download/progress?task_id=...`
- 拉取结果：`GET /api/optimized/download/result?task_id=...`（完成后返回文件流）

### 5. 获取书源列表
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

## 常见问题及解决方案

### 问题1：目录页显示30章，但下载只有18章

**原因分析**：
1. 章节过滤逻辑过于激进，误删了正常章节
2. 目录选择器不够准确，未能获取所有章节
3. 书源的URL转换规则有问题

**解决方案**：

#### 方法1：使用调试接口诊断
```bash
# 不跳过过滤，查看正常解析结果
curl "http://localhost:8000/api/novels/debug/toc?url=http://wap.99xs.info/124310/&source_id=4"

# 跳过过滤，查看原始解析结果
curl "http://localhost:8000/api/novels/debug/toc?url=http://wap.99xs.info/124310/&source_id=4&skip_filter=true"
```

#### 方法2：检查书源配置
查看 `rules/rule-04.json` 文件中的配置：
- `toc.list`: 目录选择器是否正确
- `toc.url_transform`: URL转换规则是否正确
- `toc.has_pages`: 是否需要处理分页

#### 方法3：优化建议
1. **更保守的过滤策略**：已修改过滤逻辑，提高阈值，减少误删
2. **更好的目录选择器**：已为书源4添加多个备用选择器
3. **调试功能**：新增调试接口，方便排查问题

### 修改内容说明

#### 1. 章节过滤逻辑优化
- 提高过滤阈值：从10章提升到15章
- 更严格的验证：保留章节比例至少70%
- 限制过滤数量：最多只过滤12个章节
- 更保守的检测：提高各种检测条件的阈值

#### 2. 书源4配置改进
- 添加多个备用目录选择器
- 保持原有URL转换规则不变

#### 3. 新增调试功能
- 提供详细的解析诊断信息
- 支持跳过过滤查看原始结果
- 显示书源配置和解析过程

### 使用建议

1. **遇到章节数量不匹配时**：
   - 首先使用调试接口检查原始解析结果
   - 对比跳过过滤和正常过滤的结果差异
   - 根据调试信息调整书源配置

2. **优化书源配置**：
   - 确保目录选择器能准确匹配章节链接
   - 验证URL转换规则的正确性
   - 适当调整分页处理设置

3. **监控和维护**：
   - 定期检查书源的有效性
   - 根据网站变化更新选择器
   - 关注日志中的警告信息 