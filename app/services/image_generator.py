"""
图片生成服务 - 为视频生成准备素材图片
"""
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models import ImageAsset
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ImageGenerator:
    """图片生成器"""

    def __init__(self, config):
        self.config = config
        self.client = LLMClient(config)
        self.output_dir = config.get('VIDEO_OUTPUT_DIR', './videos')

    def generate_prompts(self, project):
        """为项目生成图片描述和 AI 绘画提示词"""
        if not project.analysis:
            raise ValueError("请先完成基础分析")

        # 构建提示词生成 prompt
        prompt = self._build_image_prompts_prompt(project)

        try:
            response = self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )

            # 解析返回的图片提示词
            prompts_data = self._parse_prompts_result(response)

            return prompts_data

        except Exception as e:
            logger.error(f"生成图片提示词失败 {project.full_name}: {e}")
            raise

    def _build_image_prompts_prompt(self, project):
        """构建图片提示词生成 prompt"""
        analysis = project.analysis

        return f"""
你是一个专业的视觉设计师。请根据以下 GitHub 项目信息，生成 3-5 个适合用于视频制作的图片描述和 AI 绘画提示词。

项目信息:
- 名称：{project.full_name}
- 描述：{project.description or 'N/A'}
- 适用范围：{analysis.use_cases or 'N/A'}
- 主要用途：{analysis.purpose or 'N/A'}
- 核心特色：{analysis.features or 'N/A'}

请生成 3-5 个图片创意，每个包含:
1. 图片类型 (screenshot/架构图/流程图/宣传图)
2. 图片描述 (中文，描述图片要展示的内容)
3. AI 绘画提示词 (英文，用于 DALL-E/Midjourney 等工具生成图片)

以 JSON 数组格式返回:
[
    {{
        "type": "screenshot",
        "description": "项目主界面截图风格",
        "prompt": "A clean modern software interface screenshot, dark theme, code editor with syntax highlighting, data visualization charts, professional UI design, high quality --ar 16:9"
    }},
    {{
        "type": "architecture",
        "description": "系统架构示意图",
        "prompt": "Software architecture diagram, layered design, clean lines, modern tech style, blue and purple gradient, minimalist --ar 16:9"
    }}
]

要求:
1. 图片类型从以下选择：screenshot(界面截图)、architecture(架构图)、flowchart(流程图)、promo(宣传图)
2. description 用中文简洁描述
3. prompt 用英文，要详细具体，适合 AI 绘画工具使用
"""

    def _parse_prompts_result(self, text):
        """解析提示词结果"""
        try:
            import re
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []
        except json.JSONDecodeError:
            logger.warning(f"JSON 解析失败：{text[:200]}")
            return []

    def save_image_record(self, project_id, image_type, description, prompt, is_generated=False):
        """保存图片记录"""
        image = ImageAsset(
            project_id=project_id,
            image_type=image_type,
            image_path='',
            image_url='',
            description=description,
            prompt=prompt,
            is_generated=is_generated
        )
        return image

    def generate_image_with_ai(self, prompt, image_type):
        """
        使用 AI 绘画 API 生成图片
        这里预留接口，可以对接 DALL-E、Midjourney、Stable Diffusion 等
        """
        logger.info(f"生成图片：{image_type}, prompt: {prompt[:100]}...")

        # TODO: 对接实际的 AI 绘画 API
        # 例如使用 OpenAI DALL-E:
        # from openai import OpenAI
        # client = OpenAI(api_key=...)
        # response = client.images.generate(prompt=prompt, n=1, size="1024x1024")
        # image_url = response.data[0].url

        # 暂时返回占位符
        return {
            'success': False,
            'message': 'AI 绘画接口待实现',
            'image_url': None
        }

    def generate_prompts_batch(self, projects, max_workers=None, max_retries=None, timeout=None):
        """批量为项目生成图片提示词（并发执行）

        Args:
            projects: 项目列表
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
            try:
                prompts = self.generate_prompts(project)
                return {'project_id': project.id, 'success': True, 'prompts': prompts}
            except Exception as e:
                return {'project_id': project.id, 'success': False, 'error': str(e)}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_project = {executor.submit(_generate_single, p): p for p in projects}
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                results.append(future.result())

        return results
