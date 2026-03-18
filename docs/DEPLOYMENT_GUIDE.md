# GitHub Trending 视频生成系统 - 部署运维文档

## 1. 环境要求

### 1.1 系统要求

| 系统 | 版本 | 说明 |
|------|------|------|
| Python | 3.12+ | 推荐使用 pyenv 或 venv 管理虚拟环境 |
| pip | 23.0+ | Python 包管理工具 |
| Git | 2.x+ | 版本控制 |

### 1.2 硬件要求

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核+ |
| 内存 | 2GB | 4GB+ |
| 存储 | 10GB | 50GB+（视频文件存储） |

### 1.3 外部依赖

| 服务 | 用途 | 必需 |
|------|------|------|
| LLM API | 项目分析和文案生成 | 是（至少配置一个） |
| GitHub | 抓取 Trending 项目 | 是（需可访问） |

---

## 2. 快速开始

### 2.1 克隆项目

```bash
git clone https://github.com/wangyaofenghist/github_trending_video.git
cd github_trending_video
```

### 2.2 创建虚拟环境

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

### 2.4 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，配置必要的 API Key
```

### 2.5 初始化数据库

```bash
python run.py init-db
```

### 2.6 启动服务

```bash
python run.py
```

访问 http://localhost:5001 查看应用

---

## 3. 配置说明

### 3.1 环境变量文件 (.env)

```bash
# LLM 模型类型：qwen / anthropic / openai / custom
LLM_MODEL_TYPE=qwen

# 千问大模型配置（推荐）
QWEN_API_KEY=your_qwen_api_key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL_NAME=qwen-plus

# Anthropic 配置（备选）
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL_NAME=claude-sonnet-4-5-20250929

# OpenAI 配置（备选）
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o

# Flask 配置
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key_here

# 数据库配置
DATABASE_URL=sqlite:///github_trending.db

# 视频输出目录
VIDEO_OUTPUT_DIR=./videos

# LLM 并发控制（可选）
LLM_MAX_WORKERS=5
LLM_MAX_RETRIES=2
LLM_REQUEST_TIMEOUT=120
```

### 3.2 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_MODEL_TYPE` | 选择使用的 LLM 类型 | `qwen` |
| `QWEN_API_KEY` | 通义千问 API Key | - |
| `QWEN_BASE_URL` | 通义千问 API 地址 | 阿里云 DashScope |
| `QWEN_MODEL_NAME` | 模型名称 | `qwen-plus` |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `ANTHROPIC_MODEL_NAME` | Claude 模型名 | `claude-sonnet-4-5-20250929` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_BASE_URL` | OpenAI API 地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL_NAME` | GPT 模型名 | `gpt-4o` |
| `FLASK_DEBUG` | 调试模式 | `True` |
| `SECRET_KEY` | Flask 密钥 | 请修改为随机值 |
| `DATABASE_URL` | 数据库连接字符串 | SQLite 本地文件 |
| `LLM_MAX_WORKERS` | LLM 并发数 | `5` |
| `LLM_MAX_RETRIES` | 重试次数 | `2` |
| `LLM_REQUEST_TIMEOUT` | 请求超时（秒） | `120` |

---

## 4. 获取 API Key

### 4.1 通义千问（推荐）

1. 访问 https://dashscope.console.aliyun.com/
2. 登录阿里云账号
3. 开通 DashScope 服务
4. 创建 API Key
5. 复制到 `.env` 文件的 `QWEN_API_KEY`

**推荐模型**:
- `qwen-plus`: 性价比高，适合大多数场景
- `qwen-max`: 最强性能，适合复杂任务

### 4.2 Anthropic Claude

1. 访问 https://console.anthropic.com/
2. 注册/登录账号
3. 创建 API Key
4. 复制到 `.env` 文件的 `ANTHROPIC_API_KEY`

### 4.3 OpenAI GPT

1. 访问 https://platform.openai.com/api-keys
2. 登录/注册账号
3. 创建新的 API Key
4. 复制到 `.env` 文件的 `OPENAI_API_KEY`

---

## 5. 运维命令

### 5.1 数据抓取

```bash
# 手动抓取（使用当前日期）
python run.py crawl

# 指定日期抓取
python run.py crawl --date 2024-01-15
```

### 5.2 数据库管理

```bash
# 初始化数据库
python run.py init-db

# 进入数据库 Shell（需要安装 flask-shell）
flask shell
```

### 5.3 日志查看

应用日志输出到标准输出，可使用以下方式查看：

```bash
# 开发环境
python run.py 2>&1 | tee app.log

# 查看日志
tail -f app.log
```

### 5.4 定时任务配置

使用 cron 配置每日抓取任务：

```bash
# 编辑 crontab
crontab -e

# 添加每日抓取任务（每天早上 9 点）
0 9 * * * cd /path/to/github_trending_video && .venv/bin/python run.py crawl >> /var/log/trending_crawl.log 2>&1
```

---

## 6. 生产环境部署

### 6.1 使用 Gunicorn

```bash
# 安装 gunicorn
pip install gunicorn

# 启动服务
gunicorn -w 4 -b 0.0.0.0:5001 run:app
```

### 6.2 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /videos/ {
        alias /path/to/github_trending_video/videos/;
        expires 7d;
    }
}
```

### 6.3 使用 systemd 管理服务

```ini
# /etc/systemd/system/trending-video.service
[Unit]
Description=GitHub Trending Video Generator
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/github_trending_video
Environment="PATH=/path/to/.venv/bin"
ExecStart=/path/to/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5001 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 启动服务
sudo systemctl start trending-video
sudo systemctl enable trending-video
```

---

## 7. 目录结构说明

```
github_trending_video/
├── app/                      # 应用主目录
│   ├── routes/               # 路由定义
│   ├── services/             # 业务服务
│   ├── templates/            # HTML 模板
│   ├── __init__.py           # 应用工厂
│   └── models.py             # 数据模型
├── videos/                   # 视频输出目录（自动生成）
│   └── temp/                 # 临时文件目录
├── instance/                 # Flask 实例目录（自动生成）
│   └── github_trending.db    # SQLite 数据库
├── docs/                     # 文档目录
├── config.py                 # 配置文件
├── run.py                    # 启动入口
├── requirements.txt          # Python 依赖
├── .env                      # 环境变量（不提交 git）
└── .env.example              # 环境变量模板
```

---

## 8. 数据备份

### 8.1 数据库备份

```bash
# 备份 SQLite 数据库
cp instance/github_trending.db instance/github_trending.db.bak.$(date +%Y%m%d)

# 定期备份（crontab）
0 2 * * * cp /path/to/instance/github_trending.db /backup/github_trending_$(date +\%Y\%m\%d).db
```

### 8.2 视频文件备份

```bash
# 备份视频文件
tar -czf videos_backup_$(date +%Y%m%d).tar.gz videos/
```

---

## 9. 故障排查

### 9.1 常见问题

**问题 1: 无法抓取 GitHub**

```
错误：Connection timeout
原因：网络无法访问 GitHub
解决：配置代理或使用国内镜像
```

**问题 2: LLM API 调用失败**

```
错误：401 Unauthorized
原因：API Key 配置错误
解决：检查 .env 文件中的 API Key 是否正确
```

**问题 3: 数据库锁定**

```
错误：database is locked
原因：SQLite 并发写入
解决：减少并发请求，或迁移到 PostgreSQL
```

**问题 4: 视频生成失败**

```
错误：FFmpeg not found
原因：系统未安装 FFmpeg
解决：brew install ffmpeg (macOS) 或 apt install ffmpeg (Linux)
```

### 9.2 调试模式

开发环境开启调试模式：

```bash
# .env
FLASK_DEBUG=True
```

生产环境务必关闭：

```bash
FLASK_DEBUG=False
```

---

## 10. 性能优化建议

### 10.1 并发控制

根据 API 配额调整并发参数：

```bash
# 高配额账户
LLM_MAX_WORKERS=10

# 低配额账户
LLM_MAX_WORKERS=3
```

### 10.2 数据库优化

数据量大时考虑迁移到 PostgreSQL：

```bash
# 安装 PostgreSQL 适配器
pip install psycopg2-binary

# 修改 DATABASE_URL
DATABASE_URL=postgresql://user:password@localhost/github_trending
```

### 10.3 缓存策略

使用 Redis 缓存热点数据：

```bash
# 安装 Redis
pip install redis flask-caching

# 配置缓存
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
```
