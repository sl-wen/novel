# 小说聚合搜索与下载API

## 项目简介

本项目是一个基于Python的小说聚合搜索和下载API，提供RESTful接口，允许前端通过书名或作者名搜索小说并提供下载功能。项目重构自Java项目`so-novel`，保留了其核心功能，并以API形式提供服务。

## 技术栈

- **后端框架**：FastAPI
- **HTTP客户端**：requests
- **HTML解析**：BeautifulSoup4
- **并发处理**：asyncio
- **文档生成**：Swagger UI (FastAPI内置)

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
├── rules/                  # 资源文件
│   └── rule-1.json         # 示例书源规则
├── .gitignore
├── requirements.txt        # 依赖
└── README.md               # 项目说明
```

## API接口设计

### 1. 搜索小说

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

### 2. 获取小说详情

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

### 3. 获取小说目录

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

### 4. 下载小说

```
GET /api/novels/download?url={url}&sourceId={sourceId}&format={format}
```

**参数**：
- `url`: 小说详情页URL
- `sourceId`: 书源ID
- `format`: 下载格式，支持txt、epub，默认txt

**响应**：
文件下载流

## 启动项目

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 启动服务
```bash
uvicorn app.main:app --reload
```

3. 访问API文档
```
http://localhost:8000/docs
```

## 开发计划

- [x] 项目基础结构搭建
- [ ] 书源规则解析实现
- [ ] 小说搜索API实现
- [ ] 小说详情API实现
- [ ] 小说目录API实现
- [ ] 小说下载API实现
- [ ] 多书源聚合搜索
- [ ] 异步并发下载
- [ ] 文件格式转换（TXT、EPUB）