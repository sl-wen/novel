# 小说聚合搜索与下载API

## 项目简介

本项目是一个基于Python的小说聚合搜索和下载API，提供RESTful接口，允许前端通过书名或作者名搜索小说并提供下载功能。项目重构自Java项目`so-novel`，保留了其核心功能，并以API形式提供服务。

## 技术栈

- **后端框架**：FastAPI
- **HTTP客户端**：requests, aiohttp
- **HTML解析**：BeautifulSoup4
- **并发处理**：asyncio
- **文档生成**：Swagger UI (FastAPI内置)
- **文件格式**：TXT, EPUB, PDF

## 项目结构

```
novel/
├── app/                    # 应用主目录
│   ├── __init__.py
│   ├── main.py             # 应用入口
│   ├── api/                # API路由
│   │   ├── __init__.py
│   │   └── endpoints/      # API端点
│   │       ├── __init__.py
│   │       └── novels.py   # 小说相关API
│   ├── core/               # 核心功能
│   │   ├── __init__.py
│   │   ├── config.py       # 配置
│   │   ├── crawler.py      # 爬虫
│   │   └── source.py       # 书源
│   ├── models/             # 数据模型
│   │   ├── __init__.py
│   │   ├── book.py         # 书籍模型
│   │   ├── chapter.py      # 章节模型
│   │   └── search.py       # 搜索结果模型
│   ├── parsers/            # 解析器
│   │   ├── __init__.py
│   │   ├── book_parser.py  # 书籍解析
│   │   ├── search_parser.py # 搜索解析
│   │   ├── toc_parser.py   # 目录解析
│   │   └── chapter_parser.py # 章节解析
│   ├── services/           # 服务层
│   │   ├── __init__.py
│   │   └── novel_service.py # 小说服务
│   └── utils/              # 工具函数
│       ├── __init__.py
│       ├── http.py         # HTTP工具
│       └── file.py         # 文件工具
├── resources/              # 资源文件
│   └── rule/               # 书源规则
│       └── new/            # 新规则目录
│           ├── rule-01.json # 书源规则1
│           └── ...          # 更多规则
├── downloads/              # 下载目录
├── tests/                  # 测试
│   └── __init__.py
├── start_api.py            # API启动脚本
├── test_api.py             # API测试脚本
├── .gitignore
├── requirements.txt        # 依赖
└── README.md               # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

**方式一：使用启动脚本（推荐）**
```bash
python start_api.py
```

**方式二：直接启动**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 测试API

**方式一：使用测试脚本**
```bash
python test_api.py
```

**方式二：手动测试**
```bash
# 健康检查
curl http://localhost:8000/api/novels/health

# 搜索小说
curl "http://localhost:8000/api/novels/search?keyword=斗破苍穹"

# 获取书源列表
curl http://localhost:8000/api/novels/sources
```

### 4. 访问API文档

打开浏览器访问：http://localhost:8000/docs

## API接口设计

### 1. 健康检查

```
GET /api/novels/health
```

**响应**：
```json
{
  "code": 200,
  "message": "API服务正常运行",
  "data": {
    "status": "healthy",
    "sources_count": 20,
    "external_connectivity": "connected",
    "timestamp": 1703123456.789
  }
}
```

### 2. 搜索小说

```
GET /api/novels/search?keyword={keyword}
```

**参数**：
- `keyword`: 搜索关键词（书名或作者名）

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "sourceId": 1,
      "sourceName": "书源名称",
      "url": "小说详情页URL",
      "bookName": "小说名",
      "author": "作者",
      "chapterCount": 100,
      "latestChapter": "最新章节",
      "lastUpdateTime": "最后更新时间",
      "status": "连载/完结"
    }
  ]
}
```

### 3. 获取小说详情

```
GET /api/novels/detail?url={url}&sourceId={sourceId}
```

**参数**：
- `url`: 小说详情页URL
- `sourceId`: 书源ID

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "url": "小说详情页URL",
    "bookName": "小说名",
    "author": "作者",
    "intro": "简介",
    "category": "分类",
    "coverUrl": "封面URL",
    "latestChapter": "最新章节",
    "lastUpdateTime": "最后更新时间",
    "status": "连载/完结",
    "wordCount": "字数"
  }
}
```

### 4. 获取小说目录

```
GET /api/novels/toc?url={url}&sourceId={sourceId}
```

**参数**：
- `url`: 小说详情页URL
- `sourceId`: 书源ID

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "url": "章节URL",
      "title": "章节标题",
      "order": 1
    }
  ]
}
```

### 5. 下载小说

```
GET /api/novels/download?url={url}&sourceId={sourceId}&format={format}
```

**参数**：
- `url`: 小说详情页URL
- `sourceId`: 书源ID
- `format`: 下载格式，支持txt、epub、pdf，默认txt

**响应**：
文件下载流

### 6. 获取书源列表

```
GET /api/novels/sources
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "rule": {
        "name": "书源名称",
        "url": "书源URL",
        "enabled": true
      }
    }
  ]
}
```

## 配置说明

### 超时设置

项目已优化超时处理，支持以下配置：

- `DEFAULT_TIMEOUT`: 15秒（总超时时间）
- `CONNECT_TIMEOUT`: 10秒（连接超时）
- `READ_TIMEOUT`: 30秒（读取超时）
- `REQUEST_RETRY_TIMES`: 3次（重试次数）
- `REQUEST_RETRY_DELAY`: 2秒（重试延迟）

### 搜索设置

- `MAX_SEARCH_RESULTS`: 20（最大搜索结果数）
- `MAX_SEARCH_PAGES`: 3（最大搜索页数）

## 故障排除

### 1. 外部API超时问题

如果遇到外部API超时，项目已实现以下优化：

- 增加了超时时间配置
- 实现了重试机制
- 添加了更详细的错误日志
- 支持异步并发请求

### 2. 网络连接问题

- 检查网络连接
- 确认防火墙设置
- 尝试使用代理（如需要）

### 3. 书源规则问题

- 检查 `resources/rule/new/` 目录下的规则文件
- 确保规则文件格式正确
- 查看日志获取详细错误信息

## 开发计划

- [x] 项目基础结构搭建
- [x] 书源规则解析实现
- [x] 小说搜索API实现
- [x] 小说详情API实现
- [x] 小说目录API实现
- [x] 小说下载API实现
- [x] 多书源聚合搜索
- [x] 异步并发下载
- [x] 文件格式转换（TXT、EPUB、PDF）
- [x] 健康检查端点
- [x] 超时和重试优化
- [x] 测试脚本
- [ ] 缓存机制
- [ ] 用户认证
- [ ] 下载进度跟踪
- [ ] 更多书源支持

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。