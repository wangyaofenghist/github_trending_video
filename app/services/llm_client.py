"""
统一 LLM 客户端 - 支持多模型切换
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """统一 LLM 客户端，支持千问、Anthropic、OpenAI 等模型"""

    def __init__(self, config):
        # 处理 Flask config 字典和 Config 对象两种情况
        if hasattr(config, 'get_llm_config'):
            # Config 对象
            self.config = config
            self.llm_config = config.get_llm_config()
        else:
            # Flask config 字典
            self.config = None
            self.llm_config = self._extract_llm_config(config)
        self.client = None
        self._init_client()

    def _extract_llm_config(self, flask_config):
        """从 Flask config 字典中提取 LLM 配置"""
        model_type = flask_config.get('LLM_MODEL_TYPE', 'qwen').lower()

        if model_type == 'qwen':
            return {
                'type': 'qwen',
                'api_key': flask_config.get('QWEN_API_KEY', ''),
                'base_url': flask_config.get('QWEN_BASE_URL', ''),
                'model_name': flask_config.get('QWEN_MODEL_NAME', 'qwen-plus')
            }
        elif model_type == 'anthropic':
            return {
                'type': 'anthropic',
                'api_key': flask_config.get('ANTHROPIC_API_KEY', ''),
                'model_name': flask_config.get('ANTHROPIC_MODEL_NAME', 'claude-sonnet-4-5-20250929')
            }
        elif model_type == 'openai':
            return {
                'type': 'openai',
                'api_key': flask_config.get('OPENAI_API_KEY', ''),
                'base_url': flask_config.get('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                'model_name': flask_config.get('OPENAI_MODEL_NAME', 'gpt-4o')
            }
        elif model_type == 'custom':
            return {
                'type': 'custom',
                'api_key': flask_config.get('CUSTOM_API_KEY', ''),
                'base_url': flask_config.get('CUSTOM_BASE_URL', ''),
                'model_name': flask_config.get('CUSTOM_MODEL_NAME', '')
            }
        else:
            # 默认使用千问
            return {
                'type': 'qwen',
                'api_key': flask_config.get('QWEN_API_KEY', ''),
                'base_url': flask_config.get('QWEN_BASE_URL', ''),
                'model_name': flask_config.get('QWEN_MODEL_NAME', 'qwen-plus')
            }

    def _init_client(self):
        """初始化客户端"""
        model_type = self.llm_config['type']
        api_key = self.llm_config.get('api_key', '')

        if not api_key:
            logger.warning(f"{model_type} API Key 未配置")
            return

        if model_type in ('qwen', 'openai', 'custom'):
            base_url = self.llm_config.get('base_url', '')
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url if base_url else None
            )
            logger.info(f"LLM 客户端已初始化：{model_type} @ {self.llm_config['model_name']}")
        elif model_type == 'anthropic':
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            logger.info(f"LLM 客户端已初始化：anthropic @ {self.llm_config['model_name']}")
        else:
            logger.warning(f"未知的模型类型：{model_type}")

    def chat(self, messages, max_tokens=2000, temperature=0.7, timeout=120, **kwargs):
        """
        发送聊天请求

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "xxx"}]
            max_tokens: 最大 token 数
            temperature: 温度参数
            timeout: 请求超时时间（秒）

        Returns:
            str: 模型返回的文本内容
        """
        if not self.client:
            raise ValueError("LLM 客户端未初始化，请检查 API Key 配置")

        model_type = self.llm_config['type']
        model_name = self.llm_config.get('model_name', '')

        try:
            if model_type == 'anthropic':
                # Anthropic API 格式
                response = self.client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    messages=messages,
                    timeout=timeout
                )
                return response.content[0].text
            else:
                # OpenAI 兼容格式（千问、OpenAI、自定义）
                response = self.client.chat.completions.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                    timeout=timeout
                )
                return response.choices[0].message.content
        except TimeoutError:
            logger.error(f"LLM 请求超时（{timeout}秒）")
            raise TimeoutError(f"LLM 请求超过 {timeout} 秒")
        except Exception as e:
            logger.error(f"LLM 调用失败：{e}")
            raise

    def get_model_info(self):
        """获取当前模型信息"""
        return {
            'type': self.llm_config['type'],
            'model_name': self.llm_config.get('model_name', 'unknown'),
            'configured': self.client is not None
        }

    def chat_batch(self, items, max_workers=5, max_retries=2, timeout=120):
        """
        批量发送聊天请求（并发执行）

        Args:
            items: 列表，每个元素包含 {"messages": [...], "max_tokens": 2000, "temperature": 0.7}
            max_workers: 最大并发数
            max_retries: 最大重试次数
            timeout: 单次请求超时时间（秒）

        Returns:
            list: [{"success": True, "result": "..."}, {"success": False, "error": "..."}]
        """
        results = []

        def _chat_single(item):
            for attempt in range(max_retries + 1):
                try:
                    messages = item.get('messages', [])
                    max_tokens = item.get('max_tokens', 2000)
                    temperature = item.get('temperature', 0.7)

                    # 在线程内创建新的 LLM 客户端（避免共享连接）
                    client = LLMClient(self.config)
                    result = client.chat(messages, max_tokens, temperature, timeout=timeout)

                    logger.info(f"LLM 调用成功 (尝试 {attempt + 1}/{max_retries + 1})")
                    return {'success': True, 'result': result}
                except TimeoutError as e:
                    logger.warning(f"LLM 请求超时 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt == max_retries:
                        return {'success': False, 'error': f'请求超时 ({timeout}秒)'}
                    time.sleep(2 ** attempt)  # 指数退避
                except Exception as e:
                    logger.warning(f"LLM 调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt == max_retries:
                        return {'success': False, 'error': str(e)}
                    time.sleep(2 ** attempt)  # 指数退避

            return {'success': False, 'error': '未知错误'}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {executor.submit(_chat_single, item): idx
                             for idx, item in enumerate(items)}
            # 按原始顺序返回结果
            results = [None] * len(items)
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()

        return results
