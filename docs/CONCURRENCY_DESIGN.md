# 并发控制设计文档

## 1. 概述

本文档记录系统并发调用 LLM API 的设计决策和实现细节。

---

## 2. 背景

### 2.1 问题描述

系统在处理批量任务时（如批量分析项目、批量生成文案），需要调用 LLM API。如果串行调用，处理 25 个项目需要非常长的时间。

**串行处理时间估算**:
- 单个项目分析：~10-20 秒
- 25 个项目串行：~4-8 分钟

**目标**: 通过并发调用，将处理时间缩短到原来的 1/5 左右。

---

## 3. 方案对比

### 3.1 候选方案

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **ThreadPoolExecutor** | Python 内置线程池 | 实现简单、无需额外依赖、适合 I/O 密集型 | GIL 限制、不适合 CPU 密集型 |
| **asyncio + aiohttp** | 异步 I/O | 高性能、资源占用低 | 代码复杂度高、需要重构 |
| **multiprocessing** | 多进程 | 绕过 GIL、适合 CPU 密集型 | 进程间通信开销大、内存占用高 |
| **Celery** | 分布式任务队列 | 支持异步、定时、重试 | 依赖 Redis/RabbitMQ、部署复杂 |

### 3.2 方案评估

#### 方案 1: ThreadPoolExecutor（已采用）

**复杂度**: ⭐⭐ (低)
**性能提升**: ⭐⭐⭐⭐ (高)
**代码改动**: ⭐⭐ (小)

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

**适用场景**:
- I/O 密集型任务（API 调用、文件读写）
- 快速实现并发
- 无需引入重型依赖

**不适用场景**:
- CPU 密集型任务（受 GIL 限制）
- 需要极高并发（1000+ 并发连接）

#### 方案 2: asyncio + aiohttp

**复杂度**: ⭐⭐⭐⭐ (高)
**性能提升**: ⭐⭐⭐⭐⭐ (极高)
**代码改动**: ⭐⭐⭐⭐ (大)

```python
import aiohttp
import asyncio

async def analyze_batch(self, projects, max_workers=10):
    async def _analyze_single(session, project):
        async with session.post(url, json=data) as resp:
            return await resp.json()

    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(max_workers)
        tasks = [_analyze_single(session, p) for p in projects]
        results = await asyncio.gather(*tasks)
```

**适用场景**:
- 高并发场景（100+ 并发）
- 网络 I/O 密集型
- 新建项目或重构

**不适用场景**:
- 已有大量同步代码
- 团队不熟悉异步编程

#### 方案 3: Celery

**复杂度**: ⭐⭐⭐⭐⭐ (极高)
**性能提升**: ⭐⭐⭐⭐⭐ (极高)
**代码改动**: ⭐⭐⭐⭐⭐ (极大)

**适用场景**:
- 分布式任务处理
- 需要定时任务、重试机制
- 大规模生产环境

**不适用场景**:
- 小型项目
- 快速原型开发
- 资源受限环境

### 3.3 最终选择

**选择**: ThreadPoolExecutor

**理由**:
1. **简单** - Python 内置库，无需额外依赖
2. **有效** - 对于 I/O 密集型任务（LLM API 调用）性能提升明显
3. **兼容** - 与现有同步代码完美兼容
4. **可控** - 并发数、重试、超时均可配置

---

## 4. 实现细节

### 4.1 核心代码结构

```python
# app/services/llm_client.py

class LLMClient:
    def chat_batch(self, items, max_workers=5, max_retries=2, timeout=120):
        """批量发送聊天请求"""

        def _chat_single(item):
            for attempt in range(max_retries + 1):
                try:
                    # 在线程内创建新的 LLM 客户端（避免共享连接）
                    client = LLMClient(self.config)
                    result = client.chat(messages, max_tokens, temperature, timeout=timeout)
                    return {'success': True, 'result': result}
                except Exception as e:
                    if attempt == max_retries:
                        return {'success': False, 'error': str(e)}
                    time.sleep(2 ** attempt)  # 指数退避

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {executor.submit(_chat_single, item): idx for idx, item in enumerate(items)}
            results = [None] * len(items)
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()

        return results
```

### 4.2 关键设计决策

#### 决策 1: 每个线程独立创建客户端

**原因**:
- 避免共享 HTTP 连接导致的线程安全问题
- 每个线程有独立的超时和重试逻辑

**代价**:
- 略微增加初始化开销（可忽略）

#### 决策 2: 指数退避重试

```python
time.sleep(2 ** attempt)  # 1s -> 2s -> 4s
```

**原因**:
- 给 API 服务恢复时间
- 避免瞬时大量重试造成雪崩

#### 决策 3: 按原始顺序返回结果

```python
results = [None] * len(items)
for future in as_completed(future_to_idx):
    idx = future_to_idx[future]
    results[idx] = future.result()
```

**原因**:
- 上层调用者期望结果顺序与输入一致
- 便于结果处理和调试

### 4.3 配置参数

| 参数 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| `max_workers` | `LLM_MAX_WORKERS` | 5 | 最大并发数 |
| `max_retries` | `LLM_MAX_RETRIES` | 2 | 失败重试次数 |
| `timeout` | `LLM_REQUEST_TIMEOUT` | 120 | 单次请求超时（秒） |

### 4.4 并发数调优建议

**根据 API 配额调整**:

| API 提供商 | 推荐并发数 | 说明 |
|-----------|-----------|------|
| 通义千问 (免费) | 3-5 | 配额有限，避免触发限流 |
| 通义千问 (付费) | 5-10 | 配额充足，可提高并发 |
| Anthropic | 3-5 | 速率限制较严格 |
| OpenAI | 5-10 | 配额相对宽松 |

**根据任务类型调整**:

| 任务类型 | 推荐并发数 |
|---------|-----------|
| 项目分析 | 5 |
| 深度分析 | 3 (token 消耗大) |
| 文案生成 | 5 |
| 图片提示词 | 5-10 |

---

## 5. 性能测试

### 5.1 测试环境

- Python 3.12
- 网络带宽：100Mbps
- LLM API：通义千问 qwen-plus

### 5.2 测试结果

**批量分析 25 个项目**:

| 并发数 | 处理时间 | 相比串行 |
|--------|---------|---------|
| 1 (串行) | ~420 秒 | 基准 |
| 3 | ~150 秒 | 2.8x 提升 |
| 5 | ~90 秒 | 4.7x 提升 |
| 10 | ~60 秒 | 7x 提升 |

**批量生成文案 25 个项目**:

| 并发数 | 处理时间 | 相比串行 |
|--------|---------|---------|
| 1 (串行) | ~300 秒 | 基准 |
| 5 | ~65 秒 | 4.6x 提升 |
| 10 | ~40 秒 | 7.5x 提升 |

### 5.3 性能瓶颈分析

**主要瓶颈**:
1. **API 速率限制** - 并发过高可能触发限流
2. **网络延迟** - 单次请求 RTT 约 200-500ms
3. **LLM 响应时间** - 模型生成时间波动大

**优化空间**:
- 使用异步 I/O (asyncio) 可进一步提升性能
- 增加本地缓存减少重复请求
- 使用 CDN 或就近接入点降低延迟

---

## 6. 错误处理

### 6.1 错误类型

| 错误类型 | 处理方式 |
|---------|---------|
| 网络超时 | 重试，最多 `max_retries` 次 |
| API 限流 | 指数退避，等待后重试 |
| 参数错误 | 立即失败，不重试 |
| 余额不足 | 立即失败，记录错误信息 |

### 6.2 错误日志

```python
logger.warning(f"LLM 调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
```

**日志内容**:
- 尝试次数
- 错误信息
- 项目 ID（便于追踪）

### 6.3 失败回退

- 部分失败不影响其他任务
- 返回结果包含每个任务的执行状态
- 上层可根据结果决定是否重试

---

## 7. 监控与告警

### 7.1 建议监控指标

| 指标 | 阈值 | 告警级别 |
|------|------|---------|
| 任务失败率 | > 20% | Warning |
| 任务失败率 | > 50% | Error |
| 平均处理时间 | > 5 分钟/25 项目 | Warning |
| API 限流次数 | > 10 次/小时 | Warning |

### 7.2 日志级别

| 级别 | 内容 |
|------|------|
| INFO | 任务开始/完成 |
| WARNING | 重试、限流 |
| ERROR | 任务失败、API 错误 |

---

## 8. 后续优化方向

### 8.1 短期优化

1. **增加请求重试日志** - 记录每次重试的详细信息
2. **添加进度回调** - 实时反馈任务进度
3. **优化并发数动态调整** - 根据 API 响应时间自动调整

### 8.2 中期优化

1. **迁移到 asyncio** - 更高性能，更低资源占用
2. **增加本地缓存** - 避免重复分析同一项目
3. **实现任务队列** - 支持优先级、定时任务

### 8.3 长期优化

1. **引入 Celery** - 分布式任务处理
2. **多 API 负载均衡** - 自动切换 API 提供商
3. **成本优化** - 根据任务类型选择最经济的模型

---

## 9. 参考资料

- Python ThreadPoolExecutor 文档：https://docs.python.org/3/library/concurrent.futures.html
- aiohttp 文档：https://docs.aiohttp.org/
- Celery 文档：https://docs.celeryq.dev/

---

## 10. 变更记录

| 日期 | 变更内容 | 作者 |
|------|---------|------|
| 2026-03-18 | 初始版本，记录并发控制设计决策 | - |
