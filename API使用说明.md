# API使用说明

## 概述

本文档详细介绍了小说下载API的使用方法和特性。

## 核心特性

### 🚀 异步下载系统
- **轮询机制**：支持进度查询和状态跟踪
- **智能重试**：自动处理网络异常和临时错误
- **并发控制**：优化下载速度和系统资源使用
- **文件就绪检查**：确保文件完全生成后才返回下载链接

### 📊 文件就绪机制（新增）
为解决轮询到100%后文件未准备好的问题，系统引入了智能文件就绪检查：

#### 核心功能
- **存在性验证**：确认文件已创建
- **完整性检查**：验证文件大小稳定且可读
- **智能重试**：根据文件大小动态调整重试策略
- **性能监控**：跟踪文件就绪检查的性能指标

#### 重试策略
| 文件大小 | 重试次数 | 重试间隔 | 适用场景 |
|---------|---------|---------|----------|
| 未知/0字节 | 5次 | 0.5秒 | 默认策略 |
| < 1MB | 3次 | 0.2秒 | 小文件快速检查 |
| 1-10MB | 5次 | 0.5秒 | 中等文件标准检查 |
| 10-50MB | 8次 | 1.0秒 | 大文件延长检查 |
| > 50MB | 12次 | 2.0秒 | 超大文件长时间检查 |

#### 检查过程
1. **文件存在性**：确认文件路径有效
2. **大小稳定性**：两次检查文件大小一致
3. **可读性验证**：尝试读取文件头部数据
4. **完整性确认**：验证文件格式正确

## API端点详解

### 1. 异步下载流程

#### 启动下载任务
```http
POST /api/optimized/download/start
```

**请求参数：**
- `url` (string): 小说详情页URL
- `sourceId` (int): 书源ID，默认为1
- `format` (string): 下载格式，支持 `txt` 或 `epub`

**响应示例：**
```json
{
  "code": 202,
  "message": "accepted",
  "data": {
    "task_id": "uuid-string"
  }
}
```

#### 查询下载进度
```http
GET /api/optimized/download/progress?task_id={task_id}
```

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "uuid-string",
    "status": "running",
    "progress_percentage": 75.5,
    "completed_chapters": 151,
    "total_chapters": 200,
    "failed_chapters": 2,
    "current_chapter": "第151章 标题",
    "elapsed_time": 45.2,
    "estimated_remaining_time": 15.1,
    "average_speed": 3.34,
    "file_path": null
  }
}
```

#### 获取下载结果
```http
GET /api/optimized/download/result?task_id={task_id}
```

**功能增强：**
- **智能等待**：自动检测文件是否完全生成
- **重试机制**：根据文件大小调整等待策略
- **状态反馈**：提供详细的文件准备状态

**响应类型：**

1. **任务进行中**：
```json
{
  "code": 200,
  "message": "running",
  "data": {
    "status": "running",
    "progress_percentage": 85.0
  }
}
```

2. **文件准备中**：
```json
{
  "code": 500,
  "message": "文件不存在或尚未生成完成",
  "data": {
    "status": "completed",
    "progress_percentage": 100.0
  }
}
```

3. **文件就绪**：
```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename*=UTF-8''小说名称.txt
Content-Length: 1234567
X-Task-ID: uuid-string

[文件内容]
```

### 2. 直接下载（同步）
```http
GET /api/optimized/download?url={url}&sourceId={sourceId}&format={format}
```

## 使用示例

### JavaScript/前端示例
```javascript
async function downloadNovel(url, sourceId = 1, format = 'txt') {
    try {
        // 1. 启动下载任务
        const startResponse = await fetch('/api/optimized/download/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, sourceId, format })
        });
        
        const { data: { task_id } } = await startResponse.json();
        console.log('下载任务已启动:', task_id);
        
        // 2. 轮询进度
        let progress;
        do {
            await new Promise(resolve => setTimeout(resolve, 2000)); // 等待2秒
            
            const progressResponse = await fetch(
                `/api/optimized/download/progress?task_id=${task_id}`
            );
            const progressData = await progressResponse.json();
            progress = progressData.data;
            
            console.log(`下载进度: ${progress.progress_percentage}%`);
            
        } while (progress.status === 'running');
        
        // 3. 获取结果文件
        if (progress.status === 'completed') {
            // 新的文件就绪机制会自动处理文件准备状态
            const resultResponse = await fetch(
                `/api/optimized/download/result?task_id=${task_id}`
            );
            
            if (resultResponse.ok) {
                // 文件已就绪，开始下载
                const blob = await resultResponse.blob();
                const filename = getFilenameFromHeaders(resultResponse.headers);
                downloadBlob(blob, filename);
                console.log('下载完成');
            } else {
                // 文件尚未就绪，系统会自动重试
                const error = await resultResponse.json();
                console.log('文件准备中，请稍后重试:', error.message);
            }
        } else {
            console.error('下载失败:', progress.error_message);
        }
        
    } catch (error) {
        console.error('下载出错:', error);
    }
}

function getFilenameFromHeaders(headers) {
    const disposition = headers.get('Content-Disposition');
    if (disposition) {
        const match = disposition.match(/filename\*=UTF-8''(.+)/);
        return match ? decodeURIComponent(match[1]) : 'download.txt';
    }
    return 'download.txt';
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
```

### Python示例
```python
import requests
import time

def download_novel(url, source_id=1, format='txt'):
    """下载小说的完整流程"""
    base_url = 'http://localhost:8000/api/optimized'
    
    # 1. 启动下载任务
    start_response = requests.post(f'{base_url}/download/start', 
                                 json={'url': url, 'sourceId': source_id, 'format': format})
    task_id = start_response.json()['data']['task_id']
    print(f'下载任务已启动: {task_id}')
    
    # 2. 轮询进度
    while True:
        time.sleep(2)  # 等待2秒
        
        progress_response = requests.get(f'{base_url}/download/progress', 
                                       params={'task_id': task_id})
        progress = progress_response.json()['data']
        
        print(f"下载进度: {progress['progress_percentage']}% "
              f"({progress['completed_chapters']}/{progress['total_chapters']})")
        
        if progress['status'] != 'running':
            break
    
    # 3. 获取结果文件
    if progress['status'] == 'completed':
        # 文件就绪检查会自动处理
        result_response = requests.get(f'{base_url}/download/result', 
                                     params={'task_id': task_id})
        
        if result_response.status_code == 200:
            # 文件已就绪
            filename = get_filename_from_headers(result_response.headers)
            with open(filename, 'wb') as f:
                f.write(result_response.content)
            print(f'下载完成: {filename}')
        else:
            # 文件尚未就绪
            error = result_response.json()
            print(f'文件准备中: {error["message"]}')
    else:
        print(f'下载失败: {progress.get("error_message", "未知错误")}')

def get_filename_from_headers(headers):
    """从响应头获取文件名"""
    disposition = headers.get('Content-Disposition', '')
    if 'filename*=UTF-8' in disposition:
        import urllib.parse
        filename = disposition.split("filename*=UTF-8''")[1]
        return urllib.parse.unquote(filename)
    return 'download.txt'
```

## 性能监控

### 文件就绪检查指标
系统自动跟踪以下指标：
- **成功率**：文件就绪检查成功的比例
- **平均耗时**：文件就绪检查的平均时间
- **重试次数**：平均重试次数统计
- **失败原因**：详细的失败分类统计

### 健康检查端点
```http
GET /api/novels/health
```

返回包含文件就绪检查性能的系统健康状态。

## 最佳实践

### 1. 轮询间隔建议
- **小说下载**：建议2-3秒轮询一次
- **大型文档**：可适当延长到5秒
- **避免过频**：不建议少于1秒轮询

### 2. 错误处理
- **网络错误**：实现指数退避重试
- **任务失败**：检查错误消息，可能需要更换书源
- **文件未就绪**：系统会自动处理，无需客户端特殊处理

### 3. 性能优化
- **并发限制**：避免同时启动过多下载任务
- **资源清理**：完成下载后及时清理本地缓存
- **监控指标**：定期检查健康状态端点

## 常见问题

### Q: 为什么进度100%后还需要等待？
A: 系统引入了文件就绪检查机制，确保文件完全生成后才返回。这解决了之前"第一次下载失败，第二次才成功"的问题。

### Q: 文件就绪检查需要多长时间？
A: 通常在0.1-2秒内完成，具体取决于文件大小：
- 小文件（<1MB）：约0.2秒
- 中等文件（1-10MB）：约0.5秒  
- 大文件（>10MB）：1-2秒

### Q: 如何判断是否需要重试？
A: 新系统会自动处理重试，客户端无需特殊处理。如果返回错误，说明确实遇到了无法自动恢复的问题。

### Q: 支持的最大文件大小？
A: 理论上无限制，但超大文件（>100MB）可能需要更长的处理时间。系统会根据文件大小自动调整超时和重试策略。 