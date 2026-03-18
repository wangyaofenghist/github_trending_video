# GitHub Trending 视频生成系统 - API 接口文档

## 1. API 概述

### 1.1 基础信息

- **基础路径**: `http://localhost:5001`
- **数据格式**: JSON
- **字符编码**: UTF-8

### 1.2 响应格式

**成功响应**:
```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... }
}
```

**错误响应**:
```json
{
  "success": false,
  "message": "错误描述信息",
  "error": "详细错误信息（可选）"
}
```

### 1.3 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 2. 抓取相关 API

### 2.1 触发抓取

**请求**:
```
POST /api/crawl
Content-Type: application/json

{
  "date": "2024-01-15"  // 可选，默认当天
}
```

**响应**:
```json
{
  "success": true,
  "message": "抓取完成",
  "data": {
    "crawled_count": 25,
    "crawl_date": "2024-01-15"
  }
}
```

### 2.2 获取项目列表

**请求**:
```
GET /api/projects?date=2024-01-15&status=pending_analysis&page=1&per_page=25
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `date` | string | 抓取日期 (YYYY-MM-DD) |
| `status` | string | 状态筛选：`pending_analysis`/`pending_script`/`pending_video` |
| `page` | int | 页码，默认 1 |
| `per_page` | int | 每页数量，默认 25 |

**响应**:
```json
{
  "success": true,
  "data": {
    "projects": [
      {
        "id": 1,
        "crawl_date": "2024-01-15",
        "rank": 1,
        "owner": "owner-name",
        "name": "repo-name",
        "full_name": "owner-name/repo-name",
        "description": "项目描述",
        "language": "Python",
        "stars": 1500,
        "forks": 200,
        "topics": ["topic1", "topic2"],
        "has_analysis": true,
        "has_deep_analysis": false,
        "has_script": false,
        "video_status": null
      }
    ],
    "total": 25,
    "page": 1,
    "per_page": 25,
    "pages": 1
  }
}
```

### 2.3 获取项目详情

**请求**:
```
GET /api/projects/<project_id>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "full_name": "owner/repo",
    "description": "项目描述",
    "readme_raw": "# README 内容",
    "analysis": { ... },
    "deep_analysis": { ... },
    "script": { ... },
    "video_task": { ... },
    "images": [...]
  }
}
```

---

## 3. 分析相关 API

### 3.1 项目分析

**请求**:
```
POST /api/analyze
Content-Type: application/json

{
  "project_id": 1
}
```

**响应**:
```json
{
  "success": true,
  "message": "分析完成",
  "data": {
    "id": 1,
    "project_id": 1,
    "use_cases": "适用场景",
    "features": [...],
    "purpose": "项目用途",
    "install_command": "pip install xxx",
    "quick_start": "快速开始示例",
    "official_docs": "https://..."
  }
}
```

### 3.2 批量分析

**请求**:
```
POST /api/analyze/batch
Content-Type: application/json

{
  "project_ids": [1, 2, 3],
  "max_workers": 5,      // 可选
  "max_retries": 2,      // 可选
  "timeout": 120         // 可选
}
```

**响应**:
```json
{
  "success": true,
  "message": "批量分析完成，成功 3/3",
  "data": {
    "total": 3,
    "success_count": 3,
    "failed_count": 0,
    "results": [
      {"project_id": 1, "success": true, "analysis": {...}},
      {"project_id": 2, "success": true, "analysis": {...}},
      {"project_id": 3, "success": false, "error": "错误信息"}
    ]
  }
}
```

### 3.3 深度分析

**请求**:
```
POST /api/analyze/deep
Content-Type: application/json

{
  "project_id": 1
}
```

**响应**:
```json
{
  "success": true,
  "message": "深度分析完成",
  "data": {
    "id": 1,
    "analysis_id": 1,
    "use_case_scenarios": "详细使用场景",
    "team_info": "团队信息",
    "market_prospects": "市场前景",
    "tech_stack": "技术栈",
    "competitors": "竞品分析",
    "summary": "综合总结"
  }
}
```

### 3.4 批量深度分析

**请求**:
```
POST /api/analyze/deep/batch
Content-Type: application/json

{
  "project_ids": [1, 2, 3]
}
```

---

## 4. 文案相关 API

### 4.1 生成文案

**请求**:
```
POST /api/script/generate
Content-Type: application/json

{
  "project_id": 1,
  "style": "tech_review",    // 可选，默认 tech_review
  "duration": 60             // 可选，默认 60（秒）
}
```

**响应**:
```json
{
  "success": true,
  "message": "文案生成完成",
  "data": {
    "id": 1,
    "project_id": 1,
    "script_title": "视频标题",
    "script_content": "文案内容",
    "hook_opening": "开场 Hook",
    "key_highlights": [...],
    "call_to_action": "行动号召",
    "word_count": 500,
    "estimated_duration": 60
  }
}
```

### 4.2 批量生成文案

**请求**:
```
POST /api/script/generate/batch
Content-Type: application/json

{
  "project_ids": [1, 2, 3],
  "style": "tech_review",
  "duration": 60,
  "max_workers": 5
}
```

### 4.3 获取文案

**请求**:
```
GET /api/script/<script_id>
```

### 4.4 更新文案

**请求**:
```
PUT /api/script/<script_id>
Content-Type: application/json

{
  "script_content": "新的文案内容",
  "script_title": "新标题",
  "hook_opening": "新开场",
  "key_highlights": [...],
  "call_to_action": "新号召"
}
```

---

## 5. 视频相关 API

### 5.1 加入审核队列

**请求**:
```
POST /api/video/queue
Content-Type: application/json

{
  "project_id": 1
}
```

**响应**:
```json
{
  "success": true,
  "message": "已加入审核队列",
  "data": {
    "id": 1,
    "project_id": 1,
    "script_id": 1,
    "status": "pending",
    "created_at": "2024-01-15T10:00:00"
  }
}
```

### 5.2 获取视频列表

**请求**:
```
GET /api/video/list?page=1&page_size=20&status=all
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码 |
| `page_size` | int | 每页数量 |
| `status` | string | 状态筛选：`all`/`generating`/`completed`/`failed` |

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "task_id": 1,
        "project_id": 1,
        "project_name": "owner/repo",
        "status": "completed",
        "progress": 100,
        "video_url": "/videos/video_1.mp4",
        "video_path": "/path/to/video.mp4",
        "completed_at": "2024-01-15T12:00:00"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20
  }
}
```

### 5.3 批量生成视频

**请求**:
```
POST /api/video/generate/batch
Content-Type: application/json

{
  "project_ids": [1, 2, 3],
  "max_workers": 3
}
```

### 5.4 审核通过

**请求**:
```
POST /api/video/approve
Content-Type: application/json

{
  "project_ids": [1, 2, 3],
  "auto_generate": true
}
```

### 5.5 审核拒绝

**请求**:
```
POST /api/video/reject
Content-Type: application/json

{
  "project_ids": [1, 2, 3],
  "reason": "质量不符合要求"
}
```

### 5.6 获取视频状态

**请求**:
```
GET /api/video/status/<task_id>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "generating",
    "progress": 50,
    "project_name": "owner/repo",
    "error_message": null
  }
}
```

### 5.7 删除视频任务

**请求**:
```
DELETE /api/video/<task_id>
```

**响应**:
```json
{
  "success": true,
  "message": "视频任务已删除"
}
```

### 5.8 删除项目

**请求**:
```
DELETE /api/project/<project_id>
```

**响应**:
```json
{
  "success": true,
  "message": "项目已删除"
}
```

---

## 6. 图片相关 API

### 6.1 获取图片列表

**请求**:
```
GET /api/images?project_id=1&image_type=cover&page=1&page_size=20
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `project_id` | int | 项目 ID |
| `image_type` | string | 图片类型筛选 |
| `is_generated` | string | 是否已生成：`true`/`false` |
| `page` | int | 页码 |
| `page_size` | int | 每页数量 |

### 6.2 获取图片详情

**请求**:
```
GET /api/images/<image_id>
```

### 6.3 更新图片

**请求**:
```
PUT /api/images/<image_id>
Content-Type: application/json

{
  "image_type": "cover",
  "description": "图片描述",
  "prompt": "AI 绘画提示词",
  "is_generated": true
}
```

### 6.4 删除图片

**请求**:
```
DELETE /api/images/<image_id>
```

**响应**:
```json
{
  "success": true,
  "message": "图片已删除"
}
```

### 6.5 上传图片

**请求**:
```
POST /api/images/upload
Content-Type: multipart/form-data

FormData:
- file: [图片文件]
- project_id: 1
- image_type: "cover"
- description: "图片描述"
```

### 6.6 生成图片提示词

**请求**:
```
POST /api/analyze/images
Content-Type: application/json

{
  "project_id": 1
}
```

### 6.7 批量生成图片提示词

**请求**:
```
POST /api/analyze/images/batch
Content-Type: application/json

{
  "project_ids": [1, 2, 3]
}
```

### 6.8 生成图片

**请求**:
```
POST /api/images/generate
Content-Type: application/json

{
  "image_ids": [1, 2, 3]
}
```

---

## 7. 分析/文案编辑 API

### 7.1 更新基础分析

**请求**:
```
PUT /api/analysis/<analysis_id>
Content-Type: application/json

{
  "use_cases": "新的适用场景",
  "purpose": "新的用途",
  "features": [...],
  "install_command": "新的安装命令",
  "quick_start": "新的快速开始",
  "official_docs": "新的文档链接"
}
```

### 7.2 更新深度分析

**请求**:
```
PUT /api/deep-analysis/<deep_id>
Content-Type: application/json

{
  "use_case_scenarios": "...",
  "team_info": "...",
  "market_prospects": "...",
  "tech_stack": "...",
  "competitors": "...",
  "summary": "..."
}
```

---

## 8. 错误码说明

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误（缺少必需参数、参数格式错误） |
| 404 | 资源不存在（项目、文案、视频任务等） |
| 500 | 服务器内部错误（LLM API 调用失败、文件操作失败等） |

### 常见错误信息

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| "缺少 project_id 参数" | 请求体缺少 project_id | 添加 project_id 参数 |
| "该项目已分析过" | 项目已有分析记录 | 使用 PUT 接口更新分析 |
| "该项目没有 README 内容" | 抓取时未获取到 README | 重新抓取或手动补充 |
| "请先生成文案" | 视频任务需要文案 | 先调用文案生成接口 |
| "LLM 调用失败" | API Key 无效或余额不足 | 检查 API Key 配置 |

---

## 9. 限流说明

当前 API 无严格限流，但建议：

- 批量接口控制并发数（`max_workers` 参数）
- 单次请求项目数不超过 25 个
- 视频生成接口避免同时触发过多任务

---

## 10. 示例代码

### Python 示例

```python
import requests

BASE_URL = 'http://localhost:5001'

# 触发抓取
response = requests.post(f'{BASE_URL}/api/crawl', json={})
print(response.json())

# 获取项目列表
response = requests.get(f'{BASE_URL}/api/projects?per_page=25')
projects = response.json()['data']['projects']

# 分析项目
response = requests.post(f'{BASE_URL}/api/analyze', json={'project_id': 1})
print(response.json())

# 生成文案
response = requests.post(f'{BASE_URL}/api/script/generate', json={'project_id': 1})
script = response.json()['data']

# 加入视频队列
response = requests.post(f'{BASE_URL}/api/video/queue', json={'project_id': 1})

# 获取视频列表
response = requests.get(f'{BASE_URL}/api/video/list?status=completed')
videos = response.json()['data']['items']
```

### JavaScript 示例

```javascript
const BASE_URL = 'http://localhost:5001';

// 触发抓取
async function triggerCrawl() {
  const response = await fetch(`${BASE_URL}/api/crawl`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return response.json();
}

// 获取项目列表
async function getProjects() {
  const response = await fetch(`${BASE_URL}/api/projects?per_page=25`);
  const result = await response.json();
  return result.data.projects;
}

// 分析项目
async function analyzeProject(projectId) {
  const response = await fetch(`${BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId })
  });
  return response.json();
}
```
