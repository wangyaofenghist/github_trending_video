"""
深度分析服务 - 生成使用场景、团队信息、市场前景等
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models import DeepAnalysis
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class DeepAnalyzer:
    """深度分析器"""

    def __init__(self, config):
        self.config = config
        self.client = LLMClient(config)

    def analyze(self, project):
        """生成深度分析报告"""
        if not project.readme_raw:
            raise ValueError("README 内容为空")

        if not project.analysis:
            raise ValueError("请先完成基础分析")

        # 构建深度分析提示词
        prompt = self._build_deep_analysis_prompt(project)

        try:
            # 调用 LLM API
            response = self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000
            )

            analysis_text = response

            # 解析分析结果
            analysis_data = self._parse_analysis_result(analysis_text)

            # 保存到数据库 - 需要序列化为 JSON 字符串
            deep_analysis = DeepAnalysis(
                analysis_id=project.analysis.id,
                use_case_scenarios=self._serialize_if_list(analysis_data.get('use_case_scenarios', '')),
                team_info=self._serialize_if_list(analysis_data.get('team_info', '')),
                market_prospects=self._serialize_if_list(analysis_data.get('market_prospects', '')),
                tech_stack=self._serialize_if_list(analysis_data.get('tech_stack', '')),
                competitors=self._serialize_if_list(analysis_data.get('competitors', '')),
                summary=self._serialize_if_list(analysis_data.get('summary', '')),
                analysis_raw=analysis_text
            )

            return deep_analysis

        except Exception as e:
            logger.error(f"深度分析项目 {project.full_name} 失败：{e}")
            raise

    def _serialize_if_list(self, value):
        """如果值是列表/字典，序列化为 JSON 字符串"""
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return value if value else ''

    def _build_deep_analysis_prompt(self, project):
        """构建深度分析提示词"""
        analysis = project.analysis

        return f"""
你是一个专业的科技行业分析师。请根据以下 GitHub 项目的 README 和基础分析信息，生成一份深度分析报告。

项目信息:
- 名称：{project.full_name}
- 描述：{project.description or 'N/A'}
- 语言：{project.language or 'N/A'}
- Stars: {project.stars}
- Forks: {project.forks}

基础分析:
- 适用范围：{analysis.use_cases or 'N/A'}
- 主要用途：{analysis.purpose or 'N/A'}
- 核心特色：{analysis.features or 'N/A'}
- 安装命令：{analysis.install_command or 'N/A'}

README 内容 (部分):
---
{project.readme_raw[:12000]}
---

请以 JSON 格式返回深度分析报告，包含以下字段:
{{
    "use_case_scenarios": "详细的使用场景描述，包括目标用户群体、典型应用场景、解决的问题等",
    "team_info": "开源团队/维护者信息分析，如项目背景、社区活跃度、贡献者数量等",
    "market_prospects": "市场前景和趋势分析，包括技术趋势、采用率增长预测等",
    "tech_stack": "技术栈分析，包括使用的核心技术、架构特点、技术选型理由等",
    "competitors": "竞品分析，列出 2-3 个类似项目并对比优劣势",
    "summary": "综合总结，200 字以内的项目评价"
}}

要求:
1. 所有内容使用中文
2. 分析要客观、专业、有深度
3. 如果没有相关信息，字段留空字符串
4. use_case_scenarios 要具体，列出 3-5 个典型场景
5. market_prospects 要结合当前技术趋势分析
"""

    def _parse_analysis_result(self, text):
        """解析 LLM 返回的分析结果"""
        try:
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except json.JSONDecodeError:
            logger.warning(f"JSON 解析失败，返回空结果：{text[:200]}")
            return {}

    def analyze_batch(self, projects, max_workers=None, max_retries=None, timeout=None):
        """批量深度分析项目（并发执行）

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
                deep_analysis = self.analyze(project)
                return {'project_id': project.id, 'success': True, 'analysis': deep_analysis}
            except Exception as e:
                return {'project_id': project.id, 'success': False, 'error': str(e)}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_project = {executor.submit(_analyze_single, p): p for p in projects}
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                results.append(future.result())

        return results
