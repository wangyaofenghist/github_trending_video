import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """应用配置类"""

    # 基础配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///github_trending.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # LLM API 配置 - 支持多模型切换
    # 模型类型：qwen / anthropic / openai / custom
    LLM_MODEL_TYPE = os.getenv('LLM_MODEL_TYPE', 'qwen')

    # 千问大模型配置
    QWEN_API_KEY = os.getenv('QWEN_API_KEY', '')
    QWEN_BASE_URL = os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    QWEN_MODEL_NAME = os.getenv('QWEN_MODEL_NAME', 'qwen-plus')

    # Anthropic 配置
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    ANTHROPIC_MODEL_NAME = os.getenv('ANTHROPIC_MODEL_NAME', 'claude-sonnet-4-5-20250929')

    # OpenAI 兼容接口配置（用于其他兼容 OpenAI API 的模型）
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    OPENAI_MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o')

    # 自定义模型配置
    CUSTOM_API_KEY = os.getenv('CUSTOM_API_KEY', '')
    CUSTOM_BASE_URL = os.getenv('CUSTOM_BASE_URL', '')
    CUSTOM_MODEL_NAME = os.getenv('CUSTOM_MODEL_NAME', '')

    # 视频输出目录
    VIDEO_OUTPUT_DIR = os.getenv('VIDEO_OUTPUT_DIR', './videos')

    # LLM 并发控制配置
    LLM_MAX_WORKERS = int(os.getenv('LLM_MAX_WORKERS', '5'))  # 批量调用最大并发数
    LLM_MAX_RETRIES = int(os.getenv('LLM_MAX_RETRIES', '2'))  # 失败重试次数
    LLM_REQUEST_TIMEOUT = int(os.getenv('LLM_REQUEST_TIMEOUT', '120'))  # 单次请求超时（秒）

    # 抓取配置
    GITHUB_TRENDING_URL = 'https://github.com/trending'
    GITHUB_BASE_URL = 'https://github.com'

    # 请求头（模拟浏览器）
    REQUEST_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    def get_llm_config(self):
        """获取当前选中的 LLM 配置"""
        model_type = self.LLM_MODEL_TYPE.lower()

        if model_type == 'qwen':
            return {
                'type': 'qwen',
                'api_key': self.QWEN_API_KEY,
                'base_url': self.QWEN_BASE_URL,
                'model_name': self.QWEN_MODEL_NAME
            }
        elif model_type == 'anthropic':
            return {
                'type': 'anthropic',
                'api_key': self.ANTHROPIC_API_KEY,
                'model_name': self.ANTHROPIC_MODEL_NAME
            }
        elif model_type == 'openai':
            return {
                'type': 'openai',
                'api_key': self.OPENAI_API_KEY,
                'base_url': self.OPENAI_BASE_URL,
                'model_name': self.OPENAI_MODEL_NAME
            }
        elif model_type == 'custom':
            return {
                'type': 'custom',
                'api_key': self.CUSTOM_API_KEY,
                'base_url': self.CUSTOM_BASE_URL,
                'model_name': self.CUSTOM_MODEL_NAME
            }
        else:
            # 默认使用千问
            return {
                'type': 'qwen',
                'api_key': self.QWEN_API_KEY,
                'base_url': self.QWEN_BASE_URL,
                'model_name': self.QWEN_MODEL_NAME
            }
