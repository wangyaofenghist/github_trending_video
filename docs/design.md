# GitHub Trending 视频生成系统 - 设计文档

## 1. 系统概述

自动抓取 GitHub Trending 页面，对每个项目进行 AI 深度解读，生成介绍文案，经 Web 审核后自动生成介绍视频。

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Trending 视频生成系统                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   1. 抓取层   │ → │   2. 分析层   │ → │   3. 文案层   │        │
│  │  Trending    │   │  README+LLM  │   │  结构化描述   │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│         ↓                  ↓                  ↓                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │ 6. 存储层     │ → │ 4. Web 审核页  │ → │ 5. 视频层     │        │
│  │  数据持久化   │   │  筛选/编辑    │   │  剪映自动化   │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│         ↓                                                      │
│  ┌──────────────┐                                              │
│  │ 7. 调度层     │                                              │
│  │  定时任务     │                                              │
│  └──────────────┘                                              │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 数据库设计

### 3.1 trending_projects - 抓取项目表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增 ID |
| `crawl_date` | DATE | 抓取日期（用于去重） |
| `rank` | INTEGER | Trending 排名 |
| `owner` | VARCHAR(100) | 作者/组织名 |
| `name` | VARCHAR(200) | 项目名 |
| `full_name` | VARCHAR(300) | 完整名 (owner/name) |
| `description` | TEXT | GitHub 短描述 |
| `language` | VARCHAR(50) | 主要语言 |
| `stars` | INTEGER | Star 数 |
| `forks` | INTEGER | Fork 数 |
| `topics` | TEXT (JSON) | 标签列表 |
| `readme_raw` | LONGTEXT | README 原始内容 |
| `readme_url` | VARCHAR(500) | README URL |
| `html_url` | VARCHAR(300) | 项目 HTML 地址 |
| `created_at` | DATETIME | 记录创建时间 |

### 3.2 project_analysis - 项目分析表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增 ID |
| `project_id` | INTEGER (FK) | 关联 project 表 |
| `use_cases` | TEXT | 适用范围/场景 |
| `features` | TEXT (JSON) | 核心特色列表 |
| `purpose` | TEXT | 主要用途 |
| `install_command` | VARCHAR(500) | 安装命令（如有） |
| `quick_start` | TEXT | 快速开始示例 |
| `official_docs` | VARCHAR(500) | 官方文档链接 |
| `analysis_raw` | TEXT | LLM 原始分析结果 |
| `analyzed_at` | DATETIME | 分析时间 |

### 3.3 video_scripts - 视频文案表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增 ID |
| `project_id` | INTEGER (FK) | 关联 project 表 |
| `script_title` | VARCHAR(300) | 文案标题 |
| `script_content` | TEXT | 口播文案正文 |
| `hook_opening` | TEXT | 开场钩子（吸引注意力） |
| `key_highlights` | TEXT (JSON) | 核心亮点列表 |
| `call_to_action` | TEXT | 结尾引导语 |
| `word_count` | INTEGER | 字数 |
| `estimated_duration` | INTEGER | 预计时长 (秒) |
| `generated_at` | DATETIME | 生成时间 |

### 3.4 video_tasks - 视频任务表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增 ID |
| `project_id` | INTEGER (FK) | 关联 project 表 |
| `script_id` | INTEGER (FK) | 关联 script 表 |
| `status` | VARCHAR(50) | pending/approved/rejected/generating/completed/failed |
| `video_path` | VARCHAR(500) | 输出视频路径 |
| `video_url` | VARCHAR(500) | 视频访问 URL |
| `error_message` | TEXT | 错误信息（如有） |
| `approved_at` | DATETIME | 审核通过时间 |
| `completed_at` | DATETIME | 完成时间 |
| `created_at` | DATETIME | 创建时间 |

## 4. API 接口协议

### 4.1 抓取相关接口

#### POST /api/crawl - 手动触发抓取

```json
// Request
{
  "date": "2026-03-18"
}

// Response
{
  "success": true,
  "message": "抓取完成",
  "data": {
    "crawled_count": 25,
    "crawl_date": "2026-03-18"
  }
}
```

#### GET /api/projects - 获取项目列表

```
GET /api/projects?date=2026-03-18&status=pending
```

```json
// Response
{
  "success": true,
  "data": {
    "projects": [
      {
        "id": 1,
        "rank": 1,
        "owner": "anthropics",
        "name": "claude-code",
        "full_name": "anthropics/claude-code",
        "description": "AI 命令行工具",
        "language": "Python",
        "stars": 15000,
        "has_analysis": true,
        "has_script": true,
        "video_status": "pending"
      }
    ],
    "total": 25
  }
}
```

### 4.2 分析相关接口

#### POST /api/analyze - 触发单个项目分析

```json
// Request
{
  "project_id": 1
}

// Response
{
  "success": true,
  "message": "分析完成",
  "data": {
    "project_id": 1,
    "use_cases": "...",
    "features": [...],
    "purpose": "..."
  }
}
```

#### POST /api/analyze/batch - 批量分析

```json
// Request
{
  "project_ids": [1, 2, 3, 4, 5]
}

// Response
{
  "success": true,
  "message": "批量分析任务已提交",
  "data": {
    "total": 5,
    "success_count": 4,
    "failed_count": 1
  }
}
```

### 4.3 文案相关接口

#### POST /api/script/generate - 生成文案

```json
// Request
{
  "project_id": 1,
  "style": "tech_review",
  "duration": 60
}

// Response
{
  "success": true,
  "data": {
    "script_id": 1,
    "script_title": "claude-code: AI 驱动的代码编辑器",
    "script_content": "...",
    "word_count": 280,
    "estimated_duration": 65
  }
}
```

#### PUT /api/script/{id} - 更新文案

```json
// Request
{
  "script_content": "修改后的文案内容...",
  "hook_opening": "新的开场白..."
}

// Response
{
  "success": true,
  "message": "文案已更新"
}
```

### 4.4 审核与视频任务接口

#### GET /api/review/list - 获取审核列表

```
GET /api/review/list?status=pending&page=1&page_size=20
```

```json
// Response
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "project_name": "anthropics/claude-code",
        "rank": 1,
        "script_preview": "今天给大家介绍一个超好用的 AI 编程工具...",
        "word_count": 280,
        "status": "pending",
        "created_at": "2026-03-18 10:30:00"
      }
    ],
    "total": 25,
    "page": 1,
    "page_size": 20
  }
}
```

#### POST /api/video/approve - 审核通过（触发视频生成）

```json
// Request
{
  "project_ids": [1, 2, 3]
}

// Response
{
  "success": true,
  "message": "已加入视频生成队列",
  "data": {
    "queued_count": 3,
    "task_ids": [101, 102, 103]
  }
}
```

#### POST /api/video/reject - 审核拒绝（跳过）

```json
// Request
{
  "project_ids": [4, 5],
  "reason": "文案质量不佳"
}

// Response
{
  "success": true,
  "message": "已跳过指定项目"
}
```

#### GET /api/video/status/{task_id} - 查询视频生成状态

```json
// Response
{
  "success": true,
  "data": {
    "task_id": 101,
    "project_name": "anthropics/claude-code",
    "status": "completed",
    "progress": 100,
    "video_url": "/videos/2026-03-18/claude-code.mp4",
    "error_message": null
  }
}
```

## 5. Web 页面路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页 - 抓取项目管理面板 |
| `/review` | GET | 审核页面 - 文案审核与视频生成 |
| `/projects/{id}` | GET | 项目详情 - 完整信息展示 |
| `/scripts/{id}/edit` | GET | 文案编辑页面 |
| `/videos` | GET | 视频库 - 已生成视频列表 |

## 6. 数据结构定义

### 6.1 Project 完整结构

```typescript
interface Project {
  id: number;
  crawl_date: string;
  rank: number;
  owner: string;
  name: string;
  full_name: string;
  description: string;
  language: string;
  stars: number;
  forks: number;
  topics: string[];
  readme_raw: string;
  readme_url: string;
  html_url: string;
  created_at: string;
  analysis?: ProjectAnalysis;
  script?: VideoScript;
  video_task?: VideoTask;
}
```

### 6.2 分析结果结构

```typescript
interface ProjectAnalysis {
  use_cases: string;
  features: Feature[];
  purpose: string;
  install_command?: string;
  quick_start?: string;
  official_docs?: string;
}

interface Feature {
  name: string;
  description: string;
}
```

### 6.3 文案结构

```typescript
interface VideoScript {
  script_title: string;
  script_content: string;
  hook_opening: string;
  key_highlights: Highlight[];
  call_to_action: string;
  word_count: number;
  estimated_duration: number;
}

interface Highlight {
  title: string;
  description: string;
}
```

## 7. 技术栈

| 组件 | 技术方案 |
|------|----------|
| 后端框架 | Flask |
| 数据库 | SQLite |
| ORM | SQLAlchemy |
| 爬虫 | requests + BeautifulSoup |
| LLM | Claude API |
| 前端 | HTML + TailwindCSS + HTMX |
| 调度 | cron |

## 8. 目录结构

```
github_trending_video/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── crawl.py
│   │   ├── analysis.py
│   │   ├── script.py
│   │   └── video.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── crawler.py
│   │   ├── analyzer.py
│   │   ├── script_generator.py
│   │   └── video_generator.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── review.html
│   │   ├── project_detail.html
│   │   └── script_edit.html
│   └── static/
│       ├── css/
│       └── js/
├── scripts/
│   ├── daily_crawl.py
│   └── install_cron.sh
├── videos/
├── docs/
├── config.py
├── requirements.txt
└── run.py
```
