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

## 工具和脚本

### 1. 目录解析测试工具
`test_toc_parsing.py` - 用于测试和调试目录解析功能

**基本使用**：
```bash
# 运行默认测试
python test_toc_parsing.py

# 测试指定书源和URL
python test_toc_parsing.py 4 'http://wap.99xs.info/124310/'

# 批量测试多个书源
python test_toc_parsing.py --batch

# 批量测试并保存结果
python test_toc_parsing.py --batch --output results.json
```

**功能特性**：
- 单个书源测试和批量测试
- 详细的章节分析和统计
- 性能监控和耗时统计
- 重复章节检测
- 结果导出为JSON格式

### 2. 书源配置验证工具
`validate_source_config.py` - 用于验证书源配置文件的正确性

**基本使用**：
```bash
# 验证所有书源配置
python validate_source_config.py

# 验证指定书源
python validate_source_config.py 4

# 验证指定配置文件
python validate_source_config.py rules/rule-04.json
```

**验证内容**：
- 基本字段完整性检查
- CSS选择器有效性验证
- 正则表达式语法检查
- 配置参数合理性分析
- 提供优化建议

### 3. API调试接口
通过HTTP接口进行实时调试和诊断

**调试目录解析**：
```bash
curl "http://localhost:8000/api/novels/debug/toc?url=http://wap.99xs.info/124310/&source_id=4"
```

**返回信息**：
- 书源配置信息
- URL转换过程
- 章节解析统计
- 性能分析数据
- 重复章节检测
- 详细的章节列表

## 新增功能特性

### 1. 完全禁用最新章节过滤
- 不再尝试区分"最新章节"和"正文目录"
- 保留所有从目录页面解析到的章节
- 通过智能去重处理重复内容

### 2. 智能去重系统
**三层去重策略**：
1. **URL去重**：相同URL只保留一个，选择标题更规范的版本
2. **编号去重**：相同章节编号只保留一个
3. **标题去重**：基于标题相似度算法去除重复章节

**质量评估标准**：
- 标题包含章节编号的优先级更高
- URL更完整的版本优先
- 标题更详细的版本优先

### 3. 改进的错误处理和重试机制
**指数退避重试**：
- 网络请求失败时自动重试（最多3次）
- 采用指数退避策略（1s, 2s, 4s）
- 区分不同类型的错误（超时、网络错误、其他错误）

**详细错误日志**：
- 记录每次重试的具体原因
- 提供详细的失败诊断信息
- 支持调试模式下的详细输出

### 4. 性能监控和统计
**分阶段性能统计**：
- 初始化阶段
- 获取页面内容阶段
- 处理分页阶段
- 数据清洗阶段
- 智能排序阶段
- 结果处理阶段

**性能指标**：
- 总解析时间
- 各阶段耗时分布
- 平均每章节解析时间
- 解析速度（章节/秒）

### 5. 增强的书源配置
**书源4优化**：
```json
{
  "toc": {
    "list": "dd > a, .list-chapter a, .chapter-list a, .catalog a, ul li a, .mulu a"
  }
}
```
- 添加了6个备用选择器
- 提高解析成功率和稳定性
- 适应不同的页面结构变化

## 使用建议和最佳实践

### 1. 问题诊断流程
当遇到章节数量不匹配时：

1. **使用调试接口快速诊断**：
   ```bash
   curl "http://localhost:8000/api/novels/debug/toc?url=YOUR_URL&source_id=SOURCE_ID"
   ```

2. **分析调试结果**：
   - 检查 `chapter_analysis.total_chapters` 是否符合预期
   - 查看 `duplicate_analysis` 了解重复章节情况
   - 检查 `performance_analysis` 确认解析性能

3. **使用测试工具进一步分析**：
   ```bash
   python test_toc_parsing.py SOURCE_ID 'YOUR_URL'
   ```

### 2. 书源配置优化
1. **验证配置文件**：
   ```bash
   python validate_source_config.py SOURCE_ID
   ```

2. **根据验证结果优化**：
   - 添加备用选择器
   - 修复正则表达式错误
   - 优化超时和重试设置

3. **测试优化效果**：
   ```bash
   python test_toc_parsing.py --batch --output results.json
   ```

### 3. 性能优化建议
1. **监控解析性能**：
   - 关注总解析时间
   - 识别性能瓶颈阶段
   - 优化慢速选择器

2. **配置合理的参数**：
   - 超时时间：5-15秒
   - 重试次数：2-3次
   - 并发限制：2-5个

3. **定期维护**：
   - 使用批量测试检查所有书源
   - 及时更新失效的选择器
   - 监控错误日志和性能指标

### 4. 故障排除
**常见问题及解决方案**：

1. **解析到的章节数量为0**：
   - 检查目录选择器是否正确
   - 验证URL转换规则
   - 查看网络连接和目标网站状态

2. **章节数量少于预期**：
   - 使用调试接口查看重复章节情况
   - 检查是否有分页需要处理
   - 验证章节过滤逻辑（现已禁用）

3. **解析速度过慢**：
   - 检查网络延迟和超时设置
   - 优化选择器复杂度
   - 考虑减少重试次数

4. **重复章节问题**：
   - 查看去重统计信息
   - 检查章节编号提取逻辑
   - 验证标题相似度算法

## 监控和维护

### 1. 日常监控
- 使用批量测试定期检查所有书源状态
- 关注错误日志中的警告信息
- 监控解析性能变化趋势

### 2. 配置维护
- 定期验证书源配置文件
- 根据网站变化更新选择器
- 优化性能参数设置

### 3. 问题反馈
- 收集用户反馈的章节数量不匹配问题
- 使用调试工具分析具体原因
- 及时修复和优化相关配置 