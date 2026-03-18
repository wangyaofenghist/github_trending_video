# GitHub Trending 视频生成系统

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

自动化抓取 GitHub Trending 项目，使用 AI 大模型分析并生成短视频的完整系统。

---

## ✨ 特性

- 🚀 **自动化抓取** - 自动获取 GitHub Trending Top 25 项目
- 🧠 **AI 智能分析** - 支持多种大模型（通义千问/Claude/GPT）
- 📝 **文案自动生成** - 基于项目分析结果创作视频文案
- 🎬 **视频生成** - 自动合成视频（待完善：TTS + 字幕）
- 🖼️ **图片管理** - 支持上传和管理视频素材
- 📊 **并发处理** - 支持批量并发调用 LLM，效率提升 5-7 倍
- 🗑️ **删除功能** - 支持删除项目、视频任务和图片

---

## 📦 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置 API Key
```

### 3. 初始化数据库

```bash
python run.py init-db
```

### 4. 启动服务

```bash
python run.py
```

访问 http://localhost:5001

---

## 📚 文档

完整文档位于 [`docs/`](./docs/) 目录：

### 核心文档

| 文档 | 说明 |
|------|------|
| [产品使用文档](./docs/PRODUCT_GUIDE.md) | 功能介绍、操作流程、注意事项 |
| [技术架构文档](./docs/TECHNICAL_ARCHITECTURE.md) | 系统架构、技术栈、模块设计 |
| [部署运维文档](./docs/DEPLOYMENT_GUIDE.md) | 环境部署、配置说明、运维指南 |
| [API 接口文档](./docs/API_REFERENCE.md) | 完整 API 接口参考 |

### 设计文档

| 文档 | 说明 |
|------|------|
| [并发控制设计](./docs/CONCURRENCY_DESIGN.md) | LLM 并发调用方案对比与实现细节 |

---

## 🛠️ 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 主要开发语言 |
| Flask | 3.0.0 | Web 框架 |
| SQLAlchemy | 2.0.23 | ORM 框架 |
| Flask-SQLAlchemy | 3.1.1 | 数据库扩展 |
| Flask-CORS | 4.0.0 | 跨域支持 |

### 数据抓取

| 技术 | 版本 | 用途 |
|------|------|------|
| requests | 2.31.0 | HTTP 请求 |
| beautifulsoup4 | 4.12.2 | HTML 解析 |
| lxml | 4.9.3 | XML/HTML 解析器 |

### AI/LLM

| 技术 | 版本 | 用途 |
|------|------|------|
| openai | >=1.0.0 | LLM 客户端（兼容多厂商） |
| anthropic | 0.18.0 | Claude AI 客户端 |

### 并发处理

| 技术 | 用途 |
|------|------|
| ThreadPoolExecutor | 线程池并发调用 LLM |
| aiohttp | 异步 HTTP（预留） |

---

## 📁 项目结构

```
github_trending_video/
├── app/
│   ├── __init__.py           # Flask 应用工厂
│   ├── models.py             # 数据模型
│   ├── routes/               # 路由定义
│   │   ├── crawl.py          # 抓取路由
│   │   ├── analysis.py       # 分析路由
│   │   ├── script.py         # 文案路由
│   │   ├── video.py          # 视频路由
│   │   └── pages.py          # 页面路由
│   ├── services/             # 业务服务
│   │   ├── crawler.py        # 抓取服务
│   │   ├── analyzer.py       # 分析服务
│   │   ├── deep_analyzer.py  # 深度分析服务
│   │   ├── script_generator.py # 文案生成服务
│   │   ├── image_generator.py # 图片生成服务
│   │   ├── video_generator.py # 视频生成服务
│   │   └── llm_client.py     # LLM 客户端
│   └── templates/            # HTML 模板
├── docs/                     # 文档目录
├── config.py                 # 配置文件
├── run.py                    # 启动入口
└── requirements.txt          # 依赖列表
```

---

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_MODEL_TYPE` | 模型类型：qwen/anthropic/openai | `qwen` |
| `QWEN_API_KEY` | 通义千问 API Key | - |
| `QWEN_BASE_URL` | 通义千问 API 地址 | 阿里云 DashScope |
| `QWEN_MODEL_NAME` | 模型名称 | `qwen-plus` |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `ANTHROPIC_MODEL_NAME` | Claude 模型名 | `claude-sonnet-4-5-20250929` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_BASE_URL` | OpenAI API 地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL_NAME` | GPT 模型名 | `gpt-4o` |
| `LLM_MAX_WORKERS` | 并发数 | `5` |
| `LLM_MAX_RETRIES` | 重试次数 | `2` |
| `LLM_REQUEST_TIMEOUT` | 请求超时（秒） | `120` |
| `FLASK_DEBUG` | 调试模式 | `True` |

完整配置见 [部署运维文档](./docs/DEPLOYMENT_GUIDE.md)。

---

## 📊 API 并发性能

使用 ThreadPoolExecutor 实现 LLM 并发调用，批量处理 25 个项目：

| 并发数 | 分析时间 | 提升倍数 |
|--------|---------|---------|
| 1 (串行) | ~420 秒 | - |
| 5 | ~90 秒 | 4.7x |
| 10 | ~60 秒 | 7x |

详细设计见 [并发控制设计文档](./docs/CONCURRENCY_DESIGN.md)。

---

## ⚠️ 已知问题

### 视频播放问题

当前版本生成的视频**没有音频轨道**，导致浏览器无法播放。

**原因**: 视频生成服务只生成画面，没有 TTS 语音合成和字幕烧录。

**解决方案**:
1. 添加 TTS 语音合成
2. 使用 FFmpeg 烧录字幕到视频

此问题已记录，将在后续版本修复。

---

## 📝 开发计划

- [ ] TTS 语音合成
- [ ] 字幕烧录到视频
- [ ] 支持更多视频平台（B 站、抖音）
- [ ] 定时任务支持
- [ ] 视频模板系统

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- GitHub Trending - https://github.com/trending
- 通义千问 - https://tongyi.aliyun.com/
- Flask - https://flask.palletsprojects.com/
