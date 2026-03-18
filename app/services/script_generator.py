"""
视频文案生成服务
"""
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models import VideoScript
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ScriptGenerator:
    """视频文案生成器"""

    def __init__(self, config):
        self.config = config
        self.client = LLMClient(config)

    def generate_script(self, project, style='tech_review', duration=60):
        """生成视频文案"""
        if not project.analysis:
            raise ValueError("项目尚未分析")

        # 构建生成提示词
        prompt = self._build_script_prompt(project, style, duration)

        try:
            response = self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500
            )

            script_text = response

            # 解析文案结果
            script_data = self._parse_script_result(script_text)

            # 创建文案记录
            script = VideoScript(
                project_id=project.id,
                script_title=script_data.get('script_title', f'{project.full_name} 介绍'),
                script_content=script_data.get('script_content', ''),
                hook_opening=script_data.get('hook_opening', ''),
                key_highlights=json.dumps(script_data.get('key_highlights', []), ensure_ascii=False),
                call_to_action=script_data.get('call_to_action', ''),
                word_count=len(script_data.get('script_content', '')),
                estimated_duration=duration
            )

            return script

        except Exception as e:
            logger.error(f"生成文案失败 {project.full_name}: {e}")
            raise

    def _build_script_prompt(self, project, style, duration):
        """构建文案生成提示词"""
        analysis = project.analysis

        style_desc = {
            'tech_review': '科技评测风格，专业但易懂',
            'tutorial': '教程风格，循序渐进',
            'quick_intro': '快速介绍风格，简洁有力'
        }.get(style, '科技评测风格')

        return f"""
你是一个专业的科技视频博主。请根据以下项目信息，生成一段{duration}秒的视频文案。

项目信息:
- 名称：{project.full_name}
- 描述：{project.description or 'N/A'}
- 适用范围：{analysis.use_cases or 'N/A'}
- 主要用途：{analysis.purpose or 'N/A'}
- 核心特色：{analysis.features or 'N/A'}
- 安装命令：{analysis.install_command or 'N/A'}

文案要求:
1. 风格：{style_desc}
2. 时长：约{duration}秒 (约{duration * 3}字)
3. 结构:
   - 开场钩子：15 字以内，吸引注意力
   - 正文：介绍项目特色、用途
   - 结尾：引导行动 (点赞/关注/尝试)

请以 JSON 格式返回:
{{
    "script_title": "视频标题",
    "hook_opening": "开场钩子",
    "script_content": "完整文案正文",
    "key_highlights": [
        {{"title": "亮点 1", "description": "描述"}}
    ],
    "call_to_action": "结尾引导语"
}}
"""

    def _parse_script_result(self, text):
        """解析文案结果"""
        try:
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {
                'script_title': '项目介绍',
                'script_content': text,
                'hook_opening': '',
                'key_highlights': [],
                'call_to_action': ''
            }
        except json.JSONDecodeError:
            logger.warning(f"文案 JSON 解析失败：{text[:200]}")
            return {
                'script_title': '项目介绍',
                'script_content': text,
                'hook_opening': '',
                'key_highlights': [],
                'call_to_action': ''
            }

    def generate_script_batch(self, projects, style='tech_review', duration=60,
                              max_workers=None, max_retries=None, timeout=None):
        """批量生成视频文案（并发执行）

        Args:
            projects: 项目列表
            style: 文案风格 ('tech_review', 'tutorial', 'quick_intro')
            duration: 视频时长（秒）
            max_workers: 最大并发数（默认使用配置 LLM_MAX_WORKERS）
            max_retries: 最大重试次数（默认使用配置 LLM_MAX_RETRIES）
            timeout: 请求超时时间（默认使用配置 LLM_REQUEST_TIMEOUT）
        """
        # 使用配置默认值
        if max_workers is None:
            max_workers = getattr(self.config, 'LLM_MAX_WORKERS', 5)
        if max_retries is None:
            max_retries = getattr(self.config, 'LLM_MAX_RETRIES', 2)
        if timeout is None:
            timeout = getattr(self.config, 'LLM_REQUEST_TIMEOUT', 120)

        results = []

        def _generate_single(project):
            for attempt in range(max_retries + 1):
                try:
                    # 在线程内创建新的 LLM 客户端（避免共享连接）
                    client = LLMClient(self.config)

                    # 构建生成提示词
                    prompt = self._build_script_prompt(project, style, duration)

                    # 调用 LLM API
                    response = client.chat(
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1500,
                        timeout=timeout
                    )

                    # 解析文案结果
                    script_data = self._parse_script_result(response)

                    # 创建文案记录（不保存到数据库，由调用方统一保存）
                    script = VideoScript(
                        project_id=project.id,
                        script_title=script_data.get('script_title', f'{project.full_name} 介绍'),
                        script_content=script_data.get('script_content', ''),
                        hook_opening=script_data.get('hook_opening', ''),
                        key_highlights=json.dumps(script_data.get('key_highlights', []), ensure_ascii=False),
                        call_to_action=script_data.get('call_to_action', ''),
                        word_count=len(script_data.get('script_content', '')),
                        estimated_duration=duration
                    )

                    logger.info(f"文案生成成功 (尝试 {attempt + 1}/{max_retries + 1}): {project.full_name}")
                    return {'project_id': project.id, 'success': True, 'script': script}

                except Exception as e:
                    logger.warning(f"文案生成失败 (尝试 {attempt + 1}/{max_retries + 1}) {project.full_name}: {e}")
                    if attempt == max_retries:
                        return {'project_id': project.id, 'success': False, 'error': str(e)}
                    time.sleep(2 ** attempt)  # 指数退避

            return {'project_id': project.id, 'success': False, 'error': '未知错误'}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_project = {executor.submit(_generate_single, p): p for p in projects}
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                results.append(future.result())

        return results
