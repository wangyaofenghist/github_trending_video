# GitHub Trending 视频生成系统 - 技术架构文档

## 1. 系统架构

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层 (Templates)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  首页    │  │ 审核页面  │  │ 视频库    │  │  项目详情页      │ │
│  │  index   │  │  review  │  │  videos  │  │  project_detail  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API 层 (Routes)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  抓取    │  │ 分析      │  │ 文案      │  │  视频            │ │
│  │  /crawl  │  │  /analyze│  │  /script │  │  /video          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        服务层 (Services)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Crawler  │  │ Analyzer │  │ScriptGenerator│ │VideoGenerator│ │
│  └──────────┘  └──────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                   │
│  │LLMClient │  │DeepAnalyzer│ │ImageGenerator│                   │
│  └──────────┘  └──────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据层 (Models)                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ TrendingProject  │  │  ProjectAnalysis │  │ DeepAnalysis  │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │   VideoScript    │  │     VideoTask    │  │  ImageAsset   │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 技术栈

### 2.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 主要开发语言 |
| Flask | 3.0.0 | Web 框架 |
| SQLAlchemy | 2.0.23 | ORM 框架 |
| Flask-SQLAlchemy | 3.1.1 | Flask 数据库扩展 |
| Flask-CORS | 4.0.0 | 跨域支持 |

### 2.2 数据抓取

| 技术 | 版本 | 用途 |
|------|------|------|
| requests | 2.31.0 | HTTP 请求 |
| beautifulsoup4 | 4.12.2 | HTML 解析 |
| lxml | 4.9.3 | XML/HTML 解析器 |

### 2.3 AI/LLM

| 技术 | 版本 | 用途 |
|------|------|------|
| openai | >=1.0.0 | LLM 客户端（兼容多厂商） |
| anthropic | 0.18.0 | Claude AI 客户端 |
| aiohttp | 3.9.1 | 异步 HTTP 请求 |

### 2.4 工具库

| 技术 | 版本 | 用途 |
|------|------|------|
| python-dotenv | 1.0.0 | 环境变量管理 |

---

## 3. 核心模块设计

### 3.1 LLM 客户端 (`app/services/llm_client.py`)

**设计目标**: 统一接口，支持多模型切换

**支持的模型**:
- 通义千问 (Qwen)
- Anthropic Claude
- OpenAI GPT
- 自定义兼容接口

**核心方法**:
```python
class LLMClient:
    def chat(self, messages, max_tokens=2000, temperature=0.7, timeout=120)
    """单次聊天请求"""

    def chat_batch(self, items, max_workers=5, max_retries=2, timeout=120)
    """批量并发聊天请求"""

    def get_model_info(self)
    """获取当前模型信息"""
```

**并发实现**:
- 使用 `ThreadPoolExecutor` 实现并发
- 每个线程独立创建 LLM 客户端实例（避免共享连接）
- 支持指数退避重试机制

### 3.2 分析服务 (`app/services/analyzer.py`)

**职责**: 分析项目 README，提取关键信息

**核心流程**:
1. 构建分析提示词（包含项目信息和 README 内容）
2. 调用 LLM API 进行分析
3. 解析 LLM 返回的 JSON 结果
4. 保存到数据库

**批量分析**:
- 使用 `ThreadPoolExecutor` 并发处理多个项目
- 并发数由 `LLM_MAX_WORKERS` 控制

### 3.3 文案生成服务 (`app/services/script_generator.py`)

**职责**: 基于项目分析结果生成视频文案

**生成内容**:
- 视频标题
- Hook Opening（开场钩子）
- 主体内容
- Key Highlights（核心亮点）
- Call to Action（行动号召）

### 3.4 视频生成服务 (`app/services/video_generator.py`)

**职责**: 将文案转换为视频

**当前实现**:
- 根据文案内容生成视频画面
- 使用 Pillow 生成图片素材
- 使用 FFmpeg 合成视频

**待实现**:
- TTS 语音合成
- 字幕烧录

### 3.5 图片生成服务 (`app/services/image_generator.py`)

**职责**: 生成和管理视频图片素材

**图片类型**:
- 封面图（Cover）
- 架构图（Architecture）
- 流程图（Flowchart）
- 宣传图（Promo）

---

## 4. 数据模型设计

### 4.1 实体关系图

```
┌─────────────────────┐
│  TrendingProject    │
│  - id               │
│  - full_name        │
│  - description      │
│  - language         │
│  - stars, forks     │
│  - readme_raw       │
└─────────────────────┘
          │
          │ 1:1 (cascade delete)
          ▼
┌─────────────────────┐       ┌─────────────────────┐
│  ProjectAnalysis    │──────>│   DeepAnalysis      │
│  - use_cases        │  1:1  │  - use_case_scenarios│
│  - features         │       │  - team_info        │
│  - purpose          │       │  - market_prospects │
│  - install_command  │       │  - tech_stack       │
│  - quick_start      │       └─────────────────────┘
└─────────────────────┘
          │
          │ 1:1 (cascade delete)
          ▼
┌─────────────────────┐
│   VideoScript       │
│  - script_title     │
│  - script_content   │
│  - hook_opening     │
│  - key_highlights   │
└─────────────────────┘
          │
          │ 1:1 (cascade delete)
          ▼
┌─────────────────────┐       ┌─────────────────────┐
│    VideoTask        │       │   ImageAsset        │
│  - status           │       │  - image_type       │
│  - video_path       │       │  - image_path       │
│  - video_url        │       │  - description      │
└─────────────────────┘       └─────────────────────┘
```

### 4.2 模型说明

| 模型 | 说明 | 关键字段 |
|------|------|----------|
| `TrendingProject` | GitHub 项目 | `full_name`, `readme_raw`, `stars` |
| `ProjectAnalysis` | 项目分析 | `use_cases`, `features`, `purpose` |
| `DeepAnalysis` | 深度分析 | `use_case_scenarios`, `tech_stack` |
| `VideoScript` | 视频文案 | `script_content`, `hook_opening` |
| `VideoTask` | 视频任务 | `status`, `video_path` |
| `ImageAsset` | 图片素材 | `image_type`, `image_path` |

---

## 5. API 设计

### 5.1 RESTful API 规范

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 获取项目列表 |
| POST | `/api/crawl` | 触发抓取 |
| POST | `/api/analyze` | 项目分析 |
| POST | `/api/analyze/deep` | 深度分析 |
| POST | `/api/script/generate` | 生成文案 |
| POST | `/api/video/queue` | 加入视频队列 |
| DELETE | `/api/video/<id>` | 删除视频任务 |
| DELETE | `/api/project/<id>` | 删除项目 |
| DELETE | `/api/images/<id>` | 删除图片 |

### 5.2 响应格式

**成功响应**:
```json
{
  "success": true,
  "data": { ... }
}
```

**错误响应**:
```json
{
  "success": false,
  "error": "错误描述信息"
}
```

---

## 6. 并发控制设计

### 6.1 并发策略

系统采用 `ThreadPoolExecutor` 实现并发调用 LLM API：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def analyze_batch(self, projects, max_workers=5):
    def _analyze_single(project):
        return self.analyze_readme(project)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_project = {
            executor.submit(_analyze_single, p): p
            for p in projects
        }
        for future in as_completed(future_to_project):
            results.append(future.result())
```

### 6.2 配置参数

| 参数 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| 最大并发数 | `LLM_MAX_WORKERS` | 5 | 同时发起的最大请求数 |
| 最大重试次数 | `LLM_MAX_RETRIES` | 2 | 失败后重试次数 |
| 请求超时 | `LLM_REQUEST_TIMEOUT` | 120 | 单次请求超时时间（秒） |

### 6.3 并发方案对比

| 方案 | 复杂度 | 性能 | 适用场景 |
|------|--------|------|----------|
| **ThreadPoolExecutor** | 低 | 中 | I/O 密集型（当前方案） |
| asyncio + aiohttp | 中 | 高 | 高并发场景 |
| multiprocessing | 中 | 高 | CPU 密集型 |
| Celery | 高 | 高 | 分布式任务队列（重型） |

**当前选择理由**:
- 无需引入重型依赖
- 代码改动最小
- 满足当前并发需求（批量分析 25 个项目）

---

## 7. 文件结构

```
github_trending_video/
├── app/
│   ├── __init__.py           # Flask 应用工厂
│   ├── models.py             # 数据模型
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── crawl.py          # 抓取路由
│   │   ├── analysis.py       # 分析路由
│   │   ├── script.py         # 文案路由
│   │   ├── video.py          # 视频路由
│   │   └── pages.py          # 页面路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── crawler.py        # 抓取服务
│   │   ├── analyzer.py       # 分析服务
│   │   ├── deep_analyzer.py  # 深度分析服务
│   │   ├── script_generator.py # 文案生成服务
│   │   ├── image_generator.py # 图片生成服务
│   │   ├── video_generator.py # 视频生成服务
│   │   └── llm_client.py     # LLM 客户端
│   └── templates/
│       ├── base.html         # 基础模板
│       ├── index.html        # 首页
│       ├── review.html       # 审核页面
│       ├── videos.html       # 视频库
│       └── project_detail.html # 项目详情
├── config.py                 # 配置文件
├── requirements.txt          # 依赖列表
├── run.py                    # 启动入口
└── docs/                     # 文档目录
    ├── README.md
    ├── PRODUCT_GUIDE.md
    ├── TECHNICAL_ARCHITECTURE.md
    ├── DEPLOYMENT_GUIDE.md
    └── API_REFERENCE.md
```

---

## 8. 设计亮点

### 8.1 工厂模式创建应用

```python
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    # ...
    return app
```

**优势**:
- 支持多环境配置
- 便于测试（可创建测试应用实例）
- 避免循环导入

### 8.2 Blueprint 模块化

```python
app.register_blueprint(crawl_bp, url_prefix='/api')
app.register_blueprint(analysis_bp, url_prefix='/api')
```

**优势**:
- 代码组织清晰
- 路由管理集中
- 便于维护和扩展

### 8.3 统一 LLM 接口

```python
class LLMClient:
    def _init_client(self):
        # 根据配置自动选择客户端
        if model_type == 'anthropic':
            self.client = Anthropic(...)
        else:
            self.client = OpenAI(...)
```

**优势**:
- 屏蔽不同厂商 API 差异
- 支持热切换模型
- 降低上层代码耦合

### 8.4 SQLAlchemy 级联删除

```python
images = db.relationship(
    'ImageAsset',
    backref='project',
    cascade='all, delete-orphan'
)
```

**优势**:
- 自动清理关联数据
- 避免孤儿记录
- 简化删除逻辑
