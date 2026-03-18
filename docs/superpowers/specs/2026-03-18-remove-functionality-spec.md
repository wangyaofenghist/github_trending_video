# 移除功能产品文档

## 2026-03-18 功能实现说明

### 功能概述

为视频库、审核页面和首页添加了移除/删除功能，允许用户删除视频任务和项目。

---

## 一、后端 API 接口

### 1.1 删除视频任务

**接口**: `DELETE /api/video/<task_id>`

**功能**: 删除单个视频任务，包括关联的视频文件

**实现位置**: `app/routes/video.py`

**处理逻辑**:
1. 查找指定的 VideoTask 记录
2. 如果视频文件存在，删除视频文件
3. 删除数据库记录

**返回格式**:
```json
{
  "success": true,
  "message": "视频任务已删除"
}
```

**错误处理**:
- 404: 任务不存在
- 500: 删除失败（如文件权限问题）

---

### 1.2 删除项目

**接口**: `DELETE /api/project/<project_id>`

**功能**: 删除项目及其所有关联数据（文案、分析、视频任务、图片）

**实现位置**: `app/routes/video.py`

**处理逻辑**:
1. 查找指定的 TrendingProject 记录
2. 删除关联的视频文件（如果存在）
3. 删除关联的图片文件（如果存在）
4. 删除项目记录（级联删除关联的文案、分析等）

**返回格式**:
```json
{
  "success": true,
  "message": "项目已删除"
}
```

---

## 二、前端页面改动

### 2.1 视频库页面 (`app/templates/videos.html`)

**改动内容**:
1. 在每个视频项添加"移除"按钮
2. 实现 `deleteVideo(taskId)` 函数

**UI 位置**: 视频项操作区域，与"查看视频"并列

**交互流程**:
```
用户点击"移除"
  → 弹出确认对话框
  → 用户确认
  → 调用 DELETE /api/video/<id>
  → 显示成功/失败提示
  → 刷新列表
```

**代码示例**:
```javascript
async function deleteVideo(taskId) {
    if (!confirm('确定要删除这个视频任务吗？这将同时删除视频文件。')) return;

    const response = await fetch(`/api/video/${taskId}`, { method: 'DELETE' });
    const result = await response.json();

    if (result.success) {
        showToast('已删除', 'success');
        loadVideoList();
    }
}
```

---

### 2.2 审核页面 (`app/templates/review.html`)

**改动内容**:
1. 在项目列表项添加"移除"按钮
2. 实现 `deleteProject(projectId)` 函数

**UI 位置**: 项目详情区域，与"查看详情"按钮并列

---

### 2.3 首页 (`app/templates/index.html`)

**改动内容**:
1. 在项目列表项添加"移除"按钮
2. 实现 `deleteProject(projectId)` 函数
3. 增强状态标记样式（徽章样式）

**状态标记样式**:
| 状态 | 样式 |
|------|------|
| 已分析 | 绿色徽章 |
| 深度分析 | 紫色徽章 |
| 有文案 | 蓝色徽章 |
| 视频完成 | 绿色徽章 |
| 待审核 | 黄色徽章 |
| 无视频 | 灰色徽章 |

---

## 三、验证清单

### 3.1 后端验证

- [x] 路由正确注册 (`DELETE /api/video/<id>`)
- [x] 路由正确注册 (`DELETE /api/project/<id>`)
- [x] 文件删除逻辑正确
- [x] 数据库级联删除

### 3.2 前端验证

- [x] 视频库页面删除功能正常 (2026-03-18 验证)
- [x] 删除后列表自动刷新
- [x] Toast 提示正常显示
- [ ] 审核页面删除功能正常 (待用户验证)
- [ ] 首页删除功能正常 (待用户验证)
- [ ] 确认对话框正常显示

### 3.3 边界情况验证

- [ ] 删除不存在的项目（应返回 404）
- [ ] 删除不存在的视频（应返回 404）
- [ ] 删除正在生成中的视频任务
- [ ] 删除没有视频文件的项目
- [ ] 删除包含多个关联数据的项目

---

## 四、测试结果

### 2026-03-18 测试记录

**测试环境**:
- macOS
- Python 3.12.0
- Flask 开发服务器

**测试用例**:

| 测试项 | 输入 | 预期结果 | 实际结果 | 状态 |
|--------|------|----------|----------|------|
| 删除视频任务 | `DELETE /api/video/2` | 返回 success=true, 任务被删除 | 返回 `{"success": true, "message": "视频任务已删除"}` | ✅ 通过 |
| 视频文件访问 | `GET /videos/*.mp4` | 返回 200, Content-Type: video/mp4 | HTTP 200, Content-Type: video/mp4 | ✅ 通过 |
| 路由注册检查 | - | 显示 3 个 DELETE 路由 | `/api/images/<id>`, `/api/video/<id>`, `/api/project/<id>` | ✅ 通过 |

---

## 五、已知问题

### 问题 1: 需要重启服务器

**现象**: 新增的路由在代码修改后需要重启服务器才能生效

**原因**: Flask 开发服务器虽然有 debug 模式，但某些情况下不会自动重载所有模块

**解决方案**:
1. 修改代码后手动重启服务器
2. 或使用 `kill -9` 停止后重新启动

**验证命令**:
```bash
# 检查路由是否正确注册
.venv/bin/python -c "from app import create_app; app = create_app(); print([r.rule for r in app.url_map.iter_rules() if 'DELETE' in r.methods])"

# 测试删除 API
curl -X DELETE http://localhost:5001/api/video/<id>
```

---

## 六、相关问题

### 视频播放问题 (Task #20)

**现象**: 用户反馈"观看视频"在浏览器无法观看

**根本原因**: 视频没有音频轨道

**验证**:
```bash
# 检查音频轨道
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name videos/video_*.mp4
# 结果：无音频流
```

**详细分析**:
- 视频文件存在且可访问 (HTTP 200)
- 视频编码：h264 1080p（浏览器支持）
- **问题**: 视频生成时没有 TTS 语音，也没有烧录字幕
- 视频生成服务 (`video_generator.py`) 只生成画面，没有音频轨道

**解决方案**: 需要新增
1. TTS 语音合成功能
2. 字幕烧录到视频（`-vf subtitles=subtitle.srt`）

---

## 七、部署注意事项

1. **生产环境**: 确保有适当的权限管理，删除操作应该是管理员权限
2. **备份策略**: 建议在删除前备份重要数据
3. **日志记录**: 建议添加删除操作的审计日志
4. **软删除**: 考虑将硬删除改为软删除（添加 `deleted_at` 字段）

---

## 八、后续优化建议

1. **批量删除**: 支持在审核页面批量删除项目
2. **回收站**: 删除后进入回收站，支持恢复
3. **操作确认**: 对于有视频的项目，要求二次确认
4. **删除进度**: 对于大量数据的删除，显示进度条
5. **权限控制**: 添加删除权限验证
