#!/usr/bin/env python3
"""
API Key 验证脚本
用于验证阿里云百炼 API Key 是否有效
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def test_api_key(api_key: str, base_url: str, model_name: str) -> bool:
    """测试 API Key 是否有效"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)

        # 测试聊天接口
        response = client.chat.completions.create(
            model=model_name,
            messages=[{'role': 'user', 'content': 'Hello, this is a test.'}],
            max_tokens=20
        )
        return True, response.choices[0].message.content
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 60)
    print("阿里云百炼 API Key 验证工具")
    print("=" * 60)

    # 获取配置
    api_key = os.getenv('QWEN_API_KEY', '')
    base_url = os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    model_name = os.getenv('QWEN_MODEL_NAME', 'qwen-plus')

    print(f"\n当前配置:")
    print(f"  LLM_MODEL_TYPE: {os.getenv('LLM_MODEL_TYPE', 'not set')}")
    print(f"  QWEN_API_KEY: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else '(too short)'}")
    print(f"  QWEN_BASE_URL: {base_url}")
    print(f"  QWEN_MODEL_NAME: {model_name}")

    if not api_key or api_key.startswith('your_') or api_key.endswith('_here'):
        print("\n[错误] QWEN_API_KEY 未配置或使用默认值")
        print("\n请按以下步骤获取有效的 API Key:")
        print("  1. 访问 https://bailian.console.aliyun.com/")
        print("  2. 登录阿里云账号")
        print("  3. 进入「API-KEY 管理」页面")
        print("  4. 点击「创建新的 API-KEY」")
        print("  5. 将生成的 API Key 复制到 .env 文件的 QWEN_API_KEY 字段")
        return 1

    print(f"\n正在测试 API Key...")
    success, result = test_api_key(api_key, base_url, model_name)

    if success:
        print(f"\n[成功] API Key 有效!")
        print(f"测试响应：{result[:100]}...")
        return 0
    else:
        print(f"\n[失败] API Key 无效!")
        print(f"错误信息：{result}")
        print("\n可能的原因:")
        print("  1. API Key 已过期或被禁用")
        print("  2. API Key 复制不完整或包含多余字符")
        print("  3. API Key 不是阿里云百炼的 Key（应以 sk- 开头）")
        print("\n解决方案:")
        print("  1. 访问 https://bailian.console.aliyun.com/")
        print("  2. 重新创建或更新 API Key")
        print("  3. 确保 .env 文件中没有多余的空格或字符")
        return 1


if __name__ == '__main__':
    sys.exit(main())
