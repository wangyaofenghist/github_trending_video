"""
项目分析服务 - 使用 LLM 分析 README
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models import ProjectAnalysis
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ProjectAnalyzer:
    """项目分析器"""

    def __init__(self, config):
        self.config = config
        self.client = LLMClient(config)

    def analyze_readme(self, project):
        """分析单个项目的 README"""
        if not project.readme_raw:
            raise ValueError("README 内容为空")

        # 构建分析提示词
        prompt = self._build_analysis_prompt(project)

        try:
            # 调用 LLM API
            response = self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )

            analysis_text = response

            # 解析分析结果
            analysis_data = self._parse_analysis_result(analysis_text)

            # 保存到数据库 - 需要序列化的字段转为 JSON 字符串
            official_docs = analysis_data.get('official_docs', '')
            if isinstance(official_docs, list):
                official_docs = json.dumps(official_docs, ensure_ascii=False)

            analysis = ProjectAnalysis(
                project_id=project.id,
                use_cases=analysis_data.get('use_cases', ''),
                features=json.dumps(analysis_data.get('features', []), ensure_ascii=False),
                purpose=analysis_data.get('purpose', ''),
                install_command=analysis_data.get('install_command', ''),
                quick_start=analysis_data.get('quick_start', ''),
                official_docs=official_docs,
                analysis_raw=analysis_text
            )

            return analysis

        except Exception as e:
            logger.error(f"分析项目 {project.full_name} 失败：{e}")
            raise

    def _build_analysis_prompt(self, project):
        """构建分析提示词"""
        return f"""
你是一个专业的软件项目分析师。请分析以下 GitHub 项目的 README 内容，提取关键信息。

项目信息:
- 名称：{project.full_name}
- 描述：{project.description or 'N/A'}
- 语言：{project.language or 'N/A'}
- Stars: {project.stars}

README 内容:
---
{project.readme_raw[:15000]}  # 限制长度避免超出 token
---

请以 JSON 格式返回分析结果，包含以下字段:
{{
    "use_cases": "适用范围和使用场景描述",
    "features": [
        {{"name": "特色名称", "description": "特色描述"}}
    ],
    "purpose": "项目的主要用途",
    "install_command": "安装命令 (如有)",
    "quick_start": "快速开始示例 (如有)",
    "official_docs": "官方文档链接 (如有)"
}}

要求:
1. use_cases 用简洁的中文描述
2. features 列出 3-5 个核心特色
3. purpose 用一句话概括
4. 如果没有相关信息，字段留空字符串或空数组
"""

    def _parse_analysis_result(self, text):
        """解析 LLM 返回的分析结果"""
        try:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except json.JSONDecodeError:
            logger.warning(f"JSON 解析失败，返回空结果：{text[:200]}")
            return {}

    def analyze_batch(self, projects, max_workers=None, max_retries=None, timeout=None):
        """批量分析项目（并发执行）

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

        def _analyze_single(project):
            try:
                analysis = self.analyze_readme(project)
                return {'project_id': project.id, 'success': True, 'analysis': analysis}
            except Exception as e:
                return {'project_id': project.id, 'success': False, 'error': str(e)}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_project = {executor.submit(_analyze_single, p): p for p in projects}
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                results.append(future.result())

        return results
