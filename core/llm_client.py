"""
LLM 客户端封装
使用 OpenAI SDK + 自定义 base_url 调用 DeepSeek API
"""

import os
import time
import json
from openai import OpenAI

from config import Config


class LLMClient:
    """DeepSeek API 客户端（兼容 OpenAI 格式）"""

    def __init__(self, model=None, temperature=None, max_tokens=None):
        self.client = OpenAI(
            api_key=Config.DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY"),
            base_url=Config.BASE_URL,
        )
        self.model = model or Config.MODEL
        self.temperature = temperature if temperature is not None else Config.TEMPERATURE
        self.max_tokens = max_tokens or Config.MAX_TOKENS

    def chat(self, prompt, system="", json_mode=False, max_retries=3) -> str:
        """
        调用 LLM API，返回文本响应。

        Args:
            prompt: 用户提示词（主要输入）
            system: 系统提示词（可选的系统角色设定）
            json_mode: 是否强制要求 JSON 格式输出
            max_retries: 最大重试次数

        Returns:
            str: API 返回的文本内容
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        elif json_mode:
            messages.append({
                "role": "system",
                "content": "你只输出合法的JSON格式，不要输出其他任何文字。"
            })

        messages.append({"role": "user", "content": prompt})

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("API 返回了空响应")
                return content.strip()

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"  ⚠️  API 调用失败（{e}），{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"  ❌ API 调用最终失败（{e}）")
                    raise

    def chat_json(self, prompt, system="", max_retries=3) -> dict:
        """
        调用 LLM API 并解析 JSON 响应。

        Args:
            prompt: 用户提示词
            system: 系统提示词
            max_retries: 最大重试次数

        Returns:
            dict: 解析后的 JSON 对象
        """
        for attempt in range(max_retries):
            try:
                content = self.chat(
                    prompt=prompt,
                    system=system,
                    json_mode=True,
                    max_retries=2,
                )
                # 尝试提取 JSON（LLM 可能在代码块中返回）
                return self._parse_json(content)
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠️  JSON 解析失败，重试中... ({e})")
                else:
                    print(f"  ❌ JSON 解析最终失败")
                    raise

    @staticmethod
    def _parse_json(text: str) -> dict:
        """
        从 LLM 输出中提取并解析 JSON。
        处理 markdown 代码块包裹的情况。
        """
        text = text.strip()

        # 尝试提取 ```json ... ``` 或 ``` ... ``` 中的内容
        if "```" in text:
            for delimiter in ["```json\n", "```json\r\n", "```\n", "```\r\n"]:
                if delimiter in text:
                    text = text.split(delimiter, 1)[1]
                    text = text.rsplit("```", 1)[0]
                    text = text.strip()
                    break

        # 尝试查找第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

        return json.loads(text)
